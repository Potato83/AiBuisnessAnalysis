"""День 2: правила, trace, происхождение bank_view и HTTP-адаптер без сети."""

from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from backend.agent import generate_insights
from backend.agent.llm import (
    LLMConfigurationError, LLMResponseError, LLMTransportError, APIMiraClient,
)
from backend.agent.mock import MockClient
from backend.agent.models import CompanyProfile, InsightInput, InsightResult, NewsItem
from backend.agent.ranking import rank_news


FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "data/synthetic/agent_day2.json").read_text(encoding="utf-8"))


class Day2Tests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict("os.environ", {"AGENT_MODE": "mock"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.companies = deepcopy(FIXTURE["companies"])
        self.news = deepcopy(FIXTURE["news"])

    def result(self, company=0, **kwargs):
        return generate_insights(self.companies[company], self.news, [], **kwargs)

    def test_eight_news_are_ranked_differently_for_two_companies(self):
        first, second = self.result(), self.result(1)
        self.assertEqual(first["total"], 8)
        self.assertEqual(second["total"], 8)
        self.assertNotEqual(first["trace"]["ranked_news_ids"], second["trace"]["ranked_news_ids"])
        for result in (first, second):
            scores = [item["relevance_score"] for item in result["items"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual([item["rank"] for item in result["items"]], list(range(1, 9)))
            InsightResult.model_validate_json(json.dumps(result, allow_nan=False))

    def test_same_news_has_personalized_interpretations(self):
        first, second = self.result(), self.result(1)
        a = next(item for item in first["items"] if item["event_id"] == "demo-news-rate")
        b = next(item for item in second["items"] if item["event_id"] == "demo-news-rate")
        self.assertGreater(a["relevance_score"], b["relevance_score"])
        self.assertNotEqual(a["impact"], b["impact"])
        self.assertNotEqual(a["why_relevant"], b["why_relevant"])
        self.assertIsNone(a["bank_view"])
        self.assertIsNone(b["bank_view"])

    def test_industry_region_counterparty_and_foreign_trade_contribute(self):
        items = {item["event_id"]: item for item in self.result()["items"]}
        self.assertEqual(items["demo-news-machinery"]["relevance_score"], 35)
        self.assertEqual(items["demo-news-tula"]["relevance_score"], 40)
        self.assertEqual(items["demo-news-supplier"]["relevance_score"], 50)
        self.assertEqual(items["demo-news-fx"]["relevance_score"], 35)
        self.assertEqual(items["demo-news-rate"]["relevance_score"], 50)
        rate_trace = items["demo-news-rate"]["trace"]
        self.assertEqual(rate_trace["company_fields"]["debt_rub"], "12000000000")
        self.assertFalse(rate_trace["company_fields"]["has_deposits"])

    def test_trace_contains_actual_input_values_and_cited_sources(self):
        for item in self.result()["items"]:
            trace = item["trace"]
            for name, value in trace["company_fields"].items():
                self.assertEqual(value, self.companies[0][name])
            self.assertEqual(trace["source_ids"], item["source_ids"])
            self.assertEqual(trace["bank_source_ids"], [])
            self.assertIn("rank_news", trace["steps"])
            self.assertIn("generate_mock", trace["steps"])

    def test_equal_scores_keep_input_order(self):
        news = [NewsItem(id=id_, title="Test", text="Fixture") for id_ in ("b", "a")]
        ranked = rank_news(CompanyProfile(id="x"), news)
        self.assertEqual([item.event_id for item in ranked], ["b", "a"])
        self.assertTrue(all(item.level == "unknown" for item in ranked))

    def test_unknown_financial_data_is_distinct_from_false(self):
        event = [self.news[0]]
        unknown = generate_insights({"id": "x"}, event, [])["items"][0]
        absent = generate_insights({"id": "x", "has_loans": False, "has_deposits": False}, event, [])["items"][0]
        self.assertEqual(unknown["relevance"], "unknown")
        self.assertEqual(absent["relevance"], "low")
        self.assertFalse(absent["trace"]["company_fields"]["has_loans"])

    def test_positive_debt_can_be_used_when_product_flag_is_unknown(self):
        item = generate_insights({"id": "x", "debt_rub": "100"}, [self.news[0]], [])["items"][0]
        self.assertEqual(item["relevance"], "high")
        self.assertIn("debt_rub", item["reasons"][0]["company_fields"])

    def test_scores_are_capped_and_zero_revenue_does_not_divide(self):
        event = NewsItem(id="e", title="Fixture", text="Fixture", event_type="key_rate_unchanged",
                         company_ids=["x"], industry_codes=["28"], regions=["Москва"])
        company = CompanyProfile(id="x", industry_code="28.29", region="Москва", has_loans=True,
                                 has_deposits=True, debt_rub="100", revenue_rub="0")
        self.assertEqual(rank_news(company, [event])[0].score, 100)

    def test_bank_view_requires_confirmation_url_and_real_material(self):
        base = {"id": "bank", "title": "Unit fixture", "text": "Supplied excerpt", "url": "https://example.org/bank",
                "related_news_ids": [self.news[0]["id"]]}
        for changes in ({}, {"verified": True, "is_synthetic": True}, {"verified": True, "url": None}):
            with self.subTest(changes=changes):
                result = generate_insights(self.companies[0], [self.news[0]], [{**base, **changes}])
                self.assertIsNone(result["items"][0]["bank_view"])
                self.assertEqual(result["trace"]["excluded_bank_source_ids"], ["bank"])

    def test_confirmed_bank_excerpt_is_copied_verbatim(self):
        # Имитируем аттестацию Data-компонентом; это не реальная позиция банка.
        bank = {"id": "bank", "title": "Unit fixture", "text": "Supplied exact excerpt", "verified": True,
                "url": "https://example.org/bank", "related_news_ids": [self.news[0]["id"]]}
        result = generate_insights(self.companies[0], [self.news[0]], [bank])
        self.assertEqual(result["items"][0]["bank_view"], "Unit fixture: Supplied exact excerpt")
        self.assertEqual(result["items"][0]["trace"]["bank_source_ids"], ["bank"])

    def test_unconfirmed_bank_material_is_not_sent_to_client(self):
        class ObservingClient:
            mode, model_name = "llm", APIMiraClient.model_name

            def generate(self, request):
                self.request = request
                return MockClient().generate(request)

        client = ObservingClient()
        bank = {"id": "bank", "title": "Fixture", "text": "Unconfirmed", "related_news_ids": [self.news[0]["id"]]}
        generate_insights(self.companies[0], [self.news[0]], [bank], client=client)
        self.assertEqual(client.request.bank_sources, [])

    def test_missing_key_fails_without_explicit_fallback(self):
        with patch.dict("os.environ", {"APIMIRA_API_KEY": ""}):
            with self.assertRaises(LLMConfigurationError):
                self.result(mode="llm")

    def test_explicit_fallback_is_marked_everywhere(self):
        with patch.dict("os.environ", {"APIMIRA_API_KEY": ""}):
            result = self.result(mode="llm", fallback_to_mock=True)
        self.assertEqual(result["mode"], "mock")
        self.assertIsNone(result["model"])
        self.assertEqual(result["trace"]["attempted_mode"], "llm")
        self.assertEqual(result["trace"]["fallback_reason"], "LLMConfigurationError")
        self.assertTrue(all(item["is_mock"] for item in result["items"]))
        self.assertTrue(all("fallback_mock" in item["trace"]["steps"] for item in result["items"]))
        self.assertTrue(any("FALLBACK" in warning for warning in result["warnings"]))

    def test_invalid_llm_json_can_use_explicit_fallback(self):
        class BadJSONClient:
            mode, model_name = "llm", APIMiraClient.model_name

            def generate(self, request):
                return "not-json"

        result = self.result(client=BadJSONClient(), fallback_to_mock=True)
        self.assertEqual(result["mode"], "mock")
        self.assertEqual(result["trace"]["fallback_reason"], "ValidationError")

    def test_prohibited_model_is_not_a_fallback_trigger(self):
        class ProhibitedClient:
            mode, model_name = "llm", "unapproved"

            def generate(self, request):
                raise AssertionError("This client must never run")

        with self.assertRaisesRegex(ValueError, "appendix 3"):
            self.result(client=ProhibitedClient(), fallback_to_mock=True)

    def test_json_contains_every_insight_field_in_api_contract(self):
        contract = (Path(__file__).resolve().parents[1] / "docs/API_CONTRACT.md").read_text(encoding="utf-8")
        example = json.loads(contract.split("```json", 1)[1].split("```", 1)[0])
        for item in self.result()["items"]:
            self.assertTrue(set(example["insight"]) <= set(item))
            for field in ("headline", "why_relevant", "impact", "ai_interpretation"):
                self.assertIsInstance(item[field], str)
            for field in ("risks", "opportunities", "sources"):
                self.assertIsInstance(item[field], list)


class FakeResponse:
    def __init__(self, data):
        self.data = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


class APIMiraTests(unittest.TestCase):
    def setUp(self):
        self.request = InsightInput(company_profile=FIXTURE["companies"][0], news=FIXTURE["news"], bank_sources=[])
        self.request.rankings = rank_news(self.request.company_profile, self.request.news)
        drafts = MockClient().generate(self.request)
        self.response = {
            "model": APIMiraClient.model_id,
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"items": [item.model_dump() for item in drafts]})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        }
        self.client = APIMiraClient("unit-test-key")

    def test_http_adapter_and_usage(self):
        with patch("backend.agent.llm.urlopen", return_value=FakeResponse(self.response)) as send:
            batch = self.client.generate(self.request)
        self.assertEqual(len(batch.items), 8)
        self.assertEqual(batch.usage.total_tokens, 300)
        http_request = send.call_args.args[0]
        payload = json.loads(http_request.data)
        self.assertEqual(http_request.full_url, APIMiraClient.endpoint)
        self.assertEqual(payload["model"], "deepseek/deepseek-v4.1-flash")
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["top_p"], 1)
        self.assertNotIn("reasoning_effort", payload)
        self.assertNotIn("response_format", payload)
        self.assertEqual(payload["max_tokens"], 6000)
        self.assertFalse(payload["stream"])
        self.assertEqual(http_request.get_header("Authorization"), "Bearer unit-test-key")
        self.assertNotIn("models", payload)
        self.assertEqual(send.call_args.kwargs["timeout"], 180)

    def test_http_errors_and_timeouts_are_explicit(self):
        failures = [HTTPError(self.client.endpoint, code, "Fixture", {}, None) for code in (401, 429, 503)]
        failures += [URLError("fixture"), TimeoutError("fixture")]
        for error in failures:
            with self.subTest(error=type(error).__name__):
                with patch("backend.agent.llm.urlopen", side_effect=error):
                    with self.assertRaises(LLMTransportError) as raised:
                        self.client.generate(self.request)
                    self.assertNotIn("unit-test-key", str(raised.exception))

    def test_invalid_responses_are_rejected(self):
        wrong_model = {**self.response, "model": "unapproved-model"}
        truncated = deepcopy(self.response)
        truncated["choices"][0]["finish_reason"] = "length"
        empty_choices = {**self.response, "choices": []}
        not_json = deepcopy(self.response)
        not_json["choices"][0]["message"]["content"] = "invalid JSON"
        extra_field = deepcopy(self.response)
        extra_field["choices"][0]["message"]["content"] = '{"items":[],"bank_view":"invented"}'
        for data in (b"invalid", wrong_model, truncated, empty_choices, not_json, extra_field):
            with self.subTest(data=str(data)[:50]):
                with patch("backend.agent.llm.urlopen", return_value=FakeResponse(data)):
                    with self.assertRaises(LLMResponseError):
                        self.client.generate(self.request)

    def test_large_input_is_rejected_before_sending(self):
        self.request.news[0].text = "x" * 60001
        with patch("backend.agent.llm.urlopen") as send:
            with self.assertRaises(LLMConfigurationError):
                self.client.generate(self.request)
            send.assert_not_called()

    def test_usage_is_kept_in_run_trace(self):
        with patch("backend.agent.llm.urlopen", return_value=FakeResponse(self.response)):
            result = generate_insights(FIXTURE["companies"][0], FIXTURE["news"], [], client=self.client)
        self.assertEqual(result["mode"], "llm")
        self.assertEqual(result["trace"]["usage"]["total_tokens"], 300)
        self.assertEqual(result["trace"]["provider_model"], APIMiraClient.model_id)
        self.assertEqual(result["model"], "DeepSeek-V4.1-Flash")

    def test_reasoning_is_not_exposed_in_result(self):
        self.response["choices"][0]["message"]["reasoning_content"] = "Internal test reasoning"
        with patch("backend.agent.llm.urlopen", return_value=FakeResponse(self.response)):
            result = generate_insights(FIXTURE["companies"][0], FIXTURE["news"], [], client=self.client)
        self.assertNotIn("Internal test reasoning", json.dumps(result))

    def test_http_429_fallback_is_explicit(self):
        error = HTTPError(self.client.endpoint, 429, "Fixture", {}, None)
        with patch("backend.agent.llm.urlopen", side_effect=error):
            result = generate_insights(FIXTURE["companies"][0], FIXTURE["news"], [],
                                       client=self.client, fallback_to_mock=True)
        self.assertEqual(result["mode"], "mock")
        self.assertEqual(result["trace"]["fallback_reason"], "LLMTransportError")

    def test_empty_news_does_not_call_http(self):
        with patch("backend.agent.llm.urlopen") as send:
            result = generate_insights(FIXTURE["companies"][0], [], [], client=self.client)
        send.assert_not_called()
        self.assertEqual(result["total"], 0)


if __name__ == "__main__":
    unittest.main()

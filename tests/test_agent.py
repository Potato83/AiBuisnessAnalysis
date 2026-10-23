"""Contract tests use synthetic fixtures only; no DB, network or LLM is called."""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.agent import generate_insights
from backend.agent.examples import BANK_SOURCES, COMPANIES, NEWS
from backend.agent.mock import MockClient
from backend.agent.models import ALLOWED_MODELS, InsightResult


class AgentTests(unittest.TestCase):
    def setUp(self):
        # Тесты не должны зависеть от локального выбора AGENT_MODE=llm.
        self.environment = patch.dict("os.environ", {"AGENT_MODE": "mock"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_same_news_has_different_company_interpretations(self):
        borrower = generate_insights(COMPANIES[0], NEWS, BANK_SOURCES)
        depositor = generate_insights(COMPANIES[1], NEWS, BANK_SOURCES)
        first, second = borrower["items"][0], depositor["items"][0]
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["relevance"], "high")
        self.assertEqual(second["relevance"], "medium")
        self.assertNotEqual(first["impact"], second["impact"])
        self.assertTrue(second["opportunities"])
        self.assertIn("has_loans", first["reasons"][0]["company_fields"])

    def test_json_round_trip_and_explicit_mock(self):
        result = generate_insights(COMPANIES[0], NEWS, BANK_SOURCES)
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        parsed = InsightResult.model_validate_json(encoded)
        self.assertEqual(parsed.total, len(parsed.items))
        self.assertEqual(parsed.mode, "mock")
        self.assertIsNone(parsed.model)
        self.assertTrue(parsed.items[0].is_mock)
        self.assertTrue(parsed.items[0].ai_interpretation.startswith("MOCK"))
        self.assertEqual(parsed.items[0].confidence, "low")
        self.assertIsNotNone(parsed.generated_at.utcoffset())

    def test_sources_and_bank_text_are_from_supplied_materials(self):
        # Имитируем подтверждение Data-компонентом только внутри unit-теста.
        bank = [{**BANK_SOURCES[0], "verified": True, "is_synthetic": False}]
        item = generate_insights(COMPANIES[0], NEWS, bank)["items"][0]
        self.assertEqual(item["facts"], [NEWS[0]["text"]])
        self.assertIn(BANK_SOURCES[0]["text"], item["bank_view"])
        self.assertEqual({s["id"] for s in item["sources"]}, {NEWS[0]["id"], BANK_SOURCES[0]["id"]})
        self.assertEqual(item["sources"][1]["kind"], "bank_analysis")

    def test_missing_bank_is_explicit_not_invented(self):
        result = generate_insights(COMPANIES[0], NEWS, [])
        self.assertIsNone(result["items"][0]["bank_view"])
        self.assertTrue(any("позиция банка отсутствует" in text for text in result["warnings"]))

    def test_unassociated_bank_material_is_not_cited(self):
        bank = deepcopy(BANK_SOURCES)
        bank[0]["related_news_ids"] = []
        item = generate_insights(COMPANIES[0], NEWS, bank)["items"][0]
        self.assertIsNone(item["bank_view"])
        self.assertEqual(item["source_ids"], [NEWS[0]["id"]])

    def test_incomplete_company_is_unknown_not_false(self):
        item = generate_insights({"id": "unknown-context"}, NEWS, [])["items"][0]
        self.assertEqual(item["relevance"], "unknown")
        self.assertEqual(item["reasons"][0]["company_fields"], [])

    def test_explicit_no_credit_or_deposit_has_low_relevance(self):
        profile = {"id": "no-products", "has_loans": False, "has_deposits": False}
        item = generate_insights(profile, NEWS, [])["items"][0]
        self.assertEqual(item["relevance"], "low")

    def test_unknown_news_is_not_treated_as_rate_event(self):
        news = deepcopy(NEWS)
        news[0].pop("event_type")
        item = generate_insights(COMPANIES[0], news, [])["items"][0]
        self.assertEqual(item["relevance"], "unknown")
        self.assertEqual(item["risks"], [])

    def test_empty_news_is_valid(self):
        result = generate_insights(COMPANIES[0], [], [])
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total"], 0)

    def test_multiple_news_keep_their_own_sources(self):
        second = {**NEWS[0], "id": "other-news", "event_type": "other"}
        items = generate_insights(COMPANIES[0], [NEWS[0], second], BANK_SOURCES)["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1]["source_ids"], ["other-news"])
        self.assertIsNone(items[1]["bank_view"])

    def test_inputs_are_not_modified(self):
        profile, news, bank = deepcopy((COMPANIES[0], NEWS, BANK_SOURCES))
        before = deepcopy((profile, news, bank))
        generate_insights(profile, news, bank)
        self.assertEqual((profile, news, bank), before)

    def test_invalid_inputs_fail_validation(self):
        cases = [
            ({"id": " "}, NEWS, []),
            ({"id": "x", "has_loans": "false"}, NEWS, []),
            ({"id": "x", "revenue_rub": 20.5}, NEWS, []),
            ({"id": "x", "revenue_rub": "-1"}, NEWS, []),
            ({"id": "x", "misspelled_field": True}, NEWS, []),
            (COMPANIES[0], [{**NEWS[0], "url": "not-a-url"}], []),
            (COMPANIES[0], [{**NEWS[0], "published_at": "2026-10-01T12:00:00"}], []),
            (COMPANIES[0], [NEWS[0], NEWS[0]], []),
            (COMPANIES[0], NEWS, [{**BANK_SOURCES[0], "id": NEWS[0]["id"]}]),
            (COMPANIES[0], NEWS, [{**BANK_SOURCES[0], "related_news_ids": ["missing"]}]),
        ]
        for profile, news, bank in cases:
            with self.subTest(profile=profile, news=news, bank=bank):
                with self.assertRaises(ValidationError):
                    generate_insights(profile, news, bank)

    def test_disallowed_model_is_rejected_before_client_call(self):
        class UnapprovedClient:
            mode = "llm"
            model_name = "not-in-the-case"

            def generate(self, request):
                raise AssertionError("Must not call an unapproved model")

        with self.assertRaisesRegex(ValueError, "appendix 3"):
            generate_insights(COMPANIES[0], NEWS, [], client=UnapprovedClient())

    def test_client_error_never_silently_falls_back_to_mock(self):
        class FailingClient:
            mode = "llm"
            model_name = ALLOWED_MODELS[0]

            def generate(self, request):
                raise RuntimeError("Provider unavailable (test double)")

        with self.assertRaisesRegex(RuntimeError, "Provider unavailable"):
            generate_insights(COMPANIES[0], NEWS, [], client=FailingClient())

    def test_json_provider_response_is_parsed(self):
        # An adapter test double, NOT a verified connection to the named LLM.
        class JsonClient:
            mode = "llm"
            model_name = ALLOWED_MODELS[0]

            def generate(self, request):
                drafts = MockClient().generate(request)
                return json.dumps([draft.model_dump(mode="json") for draft in drafts])

        result = generate_insights(COMPANIES[0], NEWS, [], client=JsonClient())
        self.assertEqual(result["mode"], "llm")
        self.assertEqual(result["model"], ALLOWED_MODELS[0])

    def test_bad_provider_results_are_rejected(self):
        class BrokenClient:
            mode = "mock"
            model_name = None

            def __init__(self, mutation):
                self.mutation = mutation

            def generate(self, request):
                drafts = [draft.model_dump() for draft in MockClient().generate(request)]
                return self.mutation(drafts)

        def replace_field(drafts, field, value):
            drafts[0][field] = value
            return drafts

        def bad_reason(drafts, field, value):
            drafts[0]["reasons"][0][field] = value
            return drafts

        mutations = [
            lambda drafts: [],
            lambda drafts: [*drafts, drafts[0]],
            lambda drafts: replace_field(drafts, "event_id", "invented"),
            lambda drafts: replace_field(drafts, "source_ids", ["invented"]),
            lambda drafts: replace_field(drafts, "source_ids", [NEWS[0]["id"], NEWS[0]["id"]]),
            lambda drafts: bad_reason(drafts, "source_ids", ["invented"]),
            lambda drafts: bad_reason(drafts, "company_fields", ["invented_field"]),
            lambda drafts: bad_reason(drafts, "company_fields", ["counterparty_ids"]),
            lambda drafts: "invalid JSON",
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises((ValueError, ValidationError)):
                    generate_insights(COMPANIES[0], NEWS, [], client=BrokenClient(mutation))


if __name__ == "__main__":
    unittest.main()

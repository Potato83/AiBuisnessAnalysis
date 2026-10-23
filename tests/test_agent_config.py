"""Загрузка .env, приоритет окружения и настройка API Mira; без настоящего API."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.agent import generate_insights
from backend.agent.config import read_settings
from backend.agent.llm import LLMConfigurationError, APIMiraClient


class AgentConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.env_path = Path(temporary.name) / ".env"
        path_patch = patch("backend.agent.config.ENV_FILE", self.env_path)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def write_env(self, content):
        self.env_path.write_text(content, encoding="utf-8-sig")

    def test_file_loads_model_and_generation_settings_without_environment_mutation(self):
        self.write_env(
            '# Local configuration\nAGENT_MODE=llm\nAPIMIRA_API_KEY="test-${LITERAL}-key"\n'
            'APIMIRA_MODEL=deepseek/deepseek-v4.1-flash\nAPIMIRA_BASE_URL=https://apimira.com/v1/\n'
            'AGENT_LLM_TIMEOUT_SECONDS=90\nAGENT_LLM_MAX_TOKENS=4096\n'
            'AGENT_LLM_TEMPERATURE=0.3\nAGENT_LLM_TOP_P=0.9\n'
        )
        client = APIMiraClient.from_env()
        self.assertEqual(client._api_key, "test-${LITERAL}-key")
        self.assertEqual((client.timeout, client.max_tokens), (90, 4096))
        self.assertEqual((client.temperature, client.top_p), (0.3, 0.9))
        self.assertEqual(read_settings()["AGENT_MODE"], "llm")
        self.assertNotIn("APIMIRA_API_KEY", os.environ)

    def test_process_environment_overrides_file_and_empty_key_is_respected(self):
        self.write_env("AGENT_MODE=llm\nAPIMIRA_API_KEY=test-file-key\n")
        with patch.dict(os.environ, {"AGENT_MODE": "mock", "APIMIRA_API_KEY": ""}):
            self.assertEqual(read_settings()["AGENT_MODE"], "mock")
            with patch("backend.agent.llm.urlopen") as send:
                with self.assertRaises(LLMConfigurationError):
                    APIMiraClient.from_env()
                send.assert_not_called()

    def test_default_mode_uses_file_and_missing_key_does_not_call_api(self):
        self.write_env("AGENT_MODE=llm\nAPIMIRA_API_KEY=\n")
        with patch("backend.agent.llm.urlopen") as send:
            with self.assertRaisesRegex(LLMConfigurationError, "APIMIRA_API_KEY"):
                generate_insights({"id": "test"}, [], [])
            send.assert_not_called()

    def test_explicit_mock_overrides_file(self):
        self.write_env("AGENT_MODE=llm\nAPIMIRA_API_KEY=\n")
        with patch("backend.agent.llm.urlopen") as send:
            result = generate_insights({"id": "test"}, [], [], mode="mock")
            send.assert_not_called()
        self.assertEqual(result["mode"], "mock")

    def test_absent_file_defaults_to_mock(self):
        result = generate_insights({"id": "test"}, [], [])
        self.assertEqual(result["mode"], "mock")

    def test_invalid_provider_settings_fail_before_http(self):
        for setting in (
            "APIMIRA_MODEL=another-model", "APIMIRA_BASE_URL=https://example.org/v1",
            "AGENT_LLM_TIMEOUT_SECONDS=invalid", "AGENT_LLM_TIMEOUT_SECONDS=0",
            "AGENT_LLM_MAX_TOKENS=0", "AGENT_LLM_TEMPERATURE=1.1",
            "AGENT_LLM_TOP_P=-0.1", "AGENT_LLM_TEMPERATURE=nan",
        ):
            with self.subTest(setting=setting):
                self.write_env("APIMIRA_API_KEY=test-only-key\n" + setting + "\n")
                with patch("backend.agent.llm.urlopen") as send:
                    with self.assertRaises(LLMConfigurationError):
                        APIMiraClient.from_env()
                    send.assert_not_called()

    def test_sample_placeholder_is_not_a_key(self):
        self.write_env("APIMIRA_API_KEY=$APIMIRA_API_KEY\n")
        with self.assertRaises(LLMConfigurationError):
            APIMiraClient.from_env()


if __name__ == "__main__":
    unittest.main()

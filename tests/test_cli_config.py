import unittest
from unittest.mock import patch, MagicMock
from src.config import (
    config,
    clean_api_url,
    mask_secret,
    save_config_to_env,
    update_runtime_config,
    SUPPORTED_PROVIDERS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OLLAMA_MODELS,
)
from src.llm import get_llm_provider, OfflineRuleProvider, GeminiProvider, OllamaProvider
from src.client import backend_client
from src.ui.cli import prompt_configuration_wizard, print_status_summary


class TestCliConfigAndWizard(unittest.TestCase):

    def test_mask_secret(self):
        self.assertEqual(mask_secret(""), "(未設定 / Empty)")
        self.assertEqual(mask_secret(None), "(未設定 / Empty)")
        self.assertEqual(mask_secret("your_gemini_api_key_here"), "(範例佔位符 / 未設定)")
        self.assertEqual(mask_secret("short"), "****")
        self.assertEqual(mask_secret("1234567890"), "1234...7890")
        self.assertEqual(mask_secret("custom_test_secret_key_1234567890"), "cust...7890")

    def test_clean_api_url(self):
        self.assertEqual(clean_api_url("https://api.eva-virtual.com/"), "https://api.eva-virtual.com")
        self.assertEqual(clean_api_url("https://api.eva-virtual.com/api"), "https://api.eva-virtual.com")
        self.assertEqual(clean_api_url("https://api.eva-virtual.com/api/"), "https://api.eva-virtual.com")
        self.assertEqual(clean_api_url("http://localhost:3000/api"), "http://localhost:3000")
        self.assertEqual(clean_api_url(""), "https://api.eva-virtual.com")

    def test_update_runtime_config(self):
        update_runtime_config({
            "LLM_PROVIDER": "offline",
            "GEMINI_MODEL": "gemini-3.5-flash-lite",
            "BRVA_API_BASE_URL": "https://api.eva-virtual.com/api"
        }, persist_to_env=False)

        self.assertEqual(config.LLM_PROVIDER, "offline")
        self.assertEqual(config.GEMINI_MODEL, "gemini-3.5-flash-lite")
        self.assertEqual(config.BRVA_API_BASE_URL, "https://api.eva-virtual.com")

    def test_provider_test_connection(self):
        offline_p = OfflineRuleProvider()
        ok, msg = offline_p.test_connection()
        self.assertTrue(ok)
        self.assertIn("OFFLINE", msg)

        gemini_p = GeminiProvider(api_key="")
        g_ok, g_msg = gemini_p.test_connection()
        self.assertFalse(g_ok)
        self.assertIn("未設定", g_msg)

    @patch("builtins.input")
    def test_prompt_configuration_wizard_gemini(self, mock_input):
        # Simulated user inputs:
        # 1: Choose Gemini [1]
        # 2: Gemini API Key ["AIzaSyTestKey1234567890"]
        # 3: Choose Gemini Model [1] -> gemini-3.5-flash-lite
        # 4: BRVA Base URL ["https://api.eva-virtual.com"]
        # 5: BRVA Agent Key ["brva_sk_live_testkey"]
        # 6: Save to .env [n] (do not overwrite during test)
        mock_input.side_effect = [
            "1",                                  # Provider: Gemini
            "mock_gemini_api_key_sample_12345",   # Gemini API Key
            "1",                                  # Model: gemini-3.5-flash-lite
            "https://api.eva-virtual.com", # Base URL
            "brva_sk_live_testkey",        # Agent Key
            "n"                            # Save to .env: No
        ]

        agent = prompt_configuration_wizard()
        self.assertIsNotNone(agent)
        self.assertEqual(config.LLM_PROVIDER, "gemini")
        self.assertEqual(config.GEMINI_API_KEY, "mock_gemini_api_key_sample_12345")
        self.assertEqual(config.GEMINI_MODEL, "gemini-3.5-flash-lite")
        self.assertEqual(config.BRVA_API_BASE_URL, "https://api.eva-virtual.com")
        self.assertEqual(config.BRVA_AGENT_API_KEY, "brva_sk_live_testkey")

    @patch("builtins.input")
    def test_prompt_configuration_wizard_ollama(self, mock_input):
        # Simulated user inputs:
        # 1: Choose Ollama [2]
        # 2: Ollama Base URL ["http://192.168.1.100:11434"]
        # 3: Choose Ollama Model [2] -> qwen2.5
        # 4: BRVA Base URL [""] (keep default)
        # 5: BRVA Agent Key [""] (keep default)
        # 6: Save to .env [n]
        mock_input.side_effect = [
            "2",                           # Provider: Ollama
            "http://192.168.1.100:11434",  # Ollama URL
            "2",                           # Model: qwen2.5
            "",                            # Base URL: keep
            "",                            # Agent Key: keep
            "n"                            # Save to .env: No
        ]

        agent = prompt_configuration_wizard()
        self.assertIsNotNone(agent)
        self.assertEqual(config.LLM_PROVIDER, "ollama")
        self.assertEqual(config.OLLAMA_BASE_URL, "http://192.168.1.100:11434")
        self.assertEqual(config.OLLAMA_MODEL, "qwen2.5")

    @patch("builtins.input")
    def test_prompt_configuration_wizard_offline(self, mock_input):
        mock_input.side_effect = [
            "3",                           # Provider: Offline
            "",                            # Base URL: keep
            "",                            # Agent Key: keep
            "n"                            # Save to .env: No
        ]

        agent = prompt_configuration_wizard()
        self.assertIsNotNone(agent)
        self.assertEqual(config.LLM_PROVIDER, "offline")


if __name__ == "__main__":
    unittest.main()

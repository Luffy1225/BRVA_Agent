import unittest
from unittest.mock import patch, MagicMock
from src.llm import (
    BaseLLMProvider,
    LLMResponse,
    OllamaProvider,
    GeminiProvider,
    OfflineRuleProvider,
    get_llm_provider,
)
from src.agent import AeroAgent

class TestLLMProviders(unittest.TestCase):

    def test_offline_provider(self):
        provider = OfflineRuleProvider()
        self.assertEqual(provider.provider_name, "offline")
        self.assertTrue(provider.is_available())

        resp = provider.generate("今天天氣如何？")
        self.assertIsInstance(resp, LLMResponse)
        self.assertIn("簽派", resp.content)
        self.assertEqual(resp.provider, "offline")

    def test_gemini_provider_without_key(self):
        provider = GeminiProvider(api_key="")
        self.assertEqual(provider.provider_name, "gemini")
        self.assertFalse(provider.is_available())

        resp = provider.generate("哈囉")
        self.assertIn("未設定", resp.content)

    def test_ollama_provider_unreachable(self):
        # Point to an unreachable address
        provider = OllamaProvider(base_url="http://127.0.0.1:59999", timeout=0.5)
        self.assertEqual(provider.provider_name, "ollama")
        self.assertFalse(provider.is_available())

        # Generation should gracefully return an alert message without crashing
        resp = provider.generate("測試")
        self.assertTrue(resp.content.startswith("⚠️"))

    @patch("requests.post", side_effect=Exception("Connection refused"))
    def test_ollama_provider_connection_error(self, mock_post):
        provider = OllamaProvider(base_url="http://192.168.1.99:11434")
        resp = provider.generate("測試")
        self.assertIn("無法連線", resp.content)

    @patch("requests.get")
    @patch("requests.post")
    def test_ollama_provider_mocked_success(self, mock_post, mock_get):
        # Mock GET /api/tags
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [{"name": "llama3:latest"}, {"name": "qwen2.5:latest"}]
        }

        # Mock POST /api/chat
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "model": "llama3",
            "message": {"role": "assistant", "content": "收到，為機長設定起落航線。"},
            "done": True
        }

        provider = OllamaProvider(base_url="http://192.168.1.100:11434", model_name="llama3")
        self.assertTrue(provider.is_available())
        models = provider.list_local_models()
        self.assertIn("llama3:latest", models)

        resp = provider.chat([{"role": "user", "content": "報告起落航線"}])
        self.assertEqual(resp.content, "收到，為機長設定起落航線。")
        self.assertEqual(resp.provider, "ollama")
        self.assertEqual(resp.model, "llama3")

    def test_factory_offline(self):
        provider = get_llm_provider("offline")
        self.assertIsInstance(provider, OfflineRuleProvider)

    def test_factory_fallback_when_ollama_down(self):
        # When Ollama is specified but service is unreachable, falls back to OfflineRuleProvider
        with patch.object(OllamaProvider, "is_available", return_value=False):
            provider = get_llm_provider("ollama")
            self.assertIsInstance(provider, OfflineRuleProvider)

    def test_agent_integration_with_mock_llm(self):
        class MockLLM(BaseLLMProvider):
            @property
            def provider_name(self) -> str:
                return "mock_lan_ollama"
            def is_available(self) -> bool:
                return True
            def generate(self, prompt: str, system_prompt=None) -> LLMResponse:
                return LLMResponse(content="我是區網內的 Llama3 副駕駛！", model="llama3", provider="ollama")
            def chat(self, messages, system_prompt=None) -> LLMResponse:
                return self.generate(messages[-1]["content"])

        agent = AeroAgent(llm_provider=MockLLM(model_name="llama3"))
        resp = agent.run("今天吃什麼", verbose=False)
        self.assertIn("我是區網內的 Llama3 副駕駛", resp)

if __name__ == "__main__":
    unittest.main()

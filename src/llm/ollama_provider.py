import logging
from typing import List, Dict, Optional
import requests
from src.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """
    Local LLM Provider for Ollama (http://localhost:11434).
    Supports models such as Llama 3, Qwen 2.5, DeepSeek-R1, Mistral, etc.
    Zero external heavy libraries required; uses standard HTTP requests.
    """

    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        **kwargs
    ):
        super().__init__(model_name=model_name, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        """
        Pings Ollama daemon via GET /api/tags.
        Returns True if reachable and returns HTTP 200, False otherwise.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=min(2.0, self.timeout))
            return resp.status_code == 200
        except Exception:
            return False

    def test_connection(self) -> tuple[bool, str]:
        """Validates connection to Ollama server and lists installed models."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=min(2.5, self.timeout))
            if resp.status_code == 200:
                models = self.list_local_models()
                m_count = len(models)
                return True, f"連線成功 ({self.base_url}，在線模型: {m_count} 個)"
            return False, f"Ollama 回應異常 (HTTP {resp.status_code})"
        except Exception as e:
            return False, f"無法連線主機 ({self.base_url})"

    def list_local_models(self) -> List[str]:
        """Returns list of models currently pulled in the local Ollama instance."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=min(3.0, self.timeout))
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"[OllamaProvider] Failed to list models: {e}")
        return []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Calls Ollama /api/generate endpoint."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("response", "").strip()
                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=data
                )
            else:
                err_msg = f"Ollama HTTP {resp.status_code}: {resp.text}"
                logger.error(f"[OllamaProvider] {err_msg}")
                return LLMResponse(
                    content=f"⚠️ 本地 Ollama 呼叫失敗 ({err_msg})",
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=resp.text
                )
        except Exception as e:
            logger.error(f"[OllamaProvider] Connection error: {e}")
            return LLMResponse(
                content=f"⚠️ 無法連線至本地 Ollama 服務 ({self.base_url})。請確認 `ollama serve` 已啟動。",
                model=self.model_name,
                provider=self.provider_name
            )

    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> LLMResponse:
        """Calls Ollama /api/chat endpoint."""
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": False
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "").strip()
                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=data
                )
            else:
                err_msg = f"Ollama HTTP {resp.status_code}: {resp.text}"
                logger.error(f"[OllamaProvider] {err_msg}")
                return LLMResponse(
                    content=f"⚠️ 本地 Ollama 呼叫失敗 ({err_msg})",
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=resp.text
                )
        except Exception as e:
            logger.error(f"[OllamaProvider] Connection error: {e}")
            return LLMResponse(
                content=f"⚠️ 無法連線至本地 Ollama 服務 ({self.base_url})。請確認 `ollama serve` 已啟動。",
                model=self.model_name,
                provider=self.provider_name
            )

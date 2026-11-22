import logging
from typing import List, Dict, Optional
from src.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """
    Cloud LLM Provider for Google Gemini API.
    Supports official Google GenAI SDK (google-genai) and legacy google-generativeai.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        **kwargs
    ):
        super().__init__(model_name=model_name, **kwargs)
        self.api_key = api_key.strip() if api_key else ""
        self._client = None
        self._legacy_model = None
        self._init_sdk()

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _init_sdk(self):
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return

        # Attempt modern google.genai first
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return
        except Exception as e:
            logger.debug(f"[GeminiProvider] google.genai unavailable: {e}")

        # Fallback to google.generativeai
        try:
            import google.generativeai as gai
            gai.configure(api_key=self.api_key)
            self._legacy_model = gai.GenerativeModel(model_name=self.model_name)
        except Exception as e:
            logger.warning(f"[GeminiProvider] Failed to configure Gemini SDK: {e}")

    def is_available(self) -> bool:
        return bool(self.api_key and (self._client is not None or self._legacy_model is not None))

    def update_credentials(self, api_key: str, model_name: Optional[str] = None):
        """Dynamically reconfigures API key and model name, reinitializing SDK."""
        self.api_key = api_key.strip() if api_key else ""
        if model_name:
            self.model_name = model_name
        self._client = None
        self._legacy_model = None
        self._init_sdk()

    def test_connection(self) -> tuple[bool, str]:
        """Validates credentials against Gemini API with a lightweight test call."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return False, "Gemini API Key 未設定或為預設佔位符"
        if not self.is_available():
            return False, "Gemini SDK 初始化失敗 (請檢查套件依賴)"
        try:
            if self._client:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents="Hi"
                )
                if resp and hasattr(resp, "text"):
                    return True, f"連線成功 ({self.model_name})"
            elif self._legacy_model:
                resp = self._legacy_model.generate_content("Hi")
                if resp and hasattr(resp, "text"):
                    return True, f"連線成功 ({self.model_name})"
            return False, "無法取得 Gemini 回應"
        except Exception as e:
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg:
                return False, "Gemini API Key 無效 (API_KEY_INVALID)"
            elif "403" in err_msg or "Forbidden" in err_msg:
                return False, f"存取被拒 (403 Forbidden: 請確認模型名稱或金鑰權限)"
            elif "404" in err_msg or "NOT_FOUND" in err_msg:
                return False, f"模型不存在或無法存取 ({self.model_name})"
            return False, f"連線失敗 ({err_msg[:60]})"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                content="⚠️ Gemini API Key 未設定或無效。",
                model=self.model_name,
                provider=self.provider_name
            )

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            if self._client:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                return LLMResponse(
                    content=resp.text.strip(),
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=resp
                )
            elif self._legacy_model:
                resp = self._legacy_model.generate_content(full_prompt)
                return LLMResponse(
                    content=resp.text.strip(),
                    model=self.model_name,
                    provider=self.provider_name,
                    raw_response=resp
                )
        except Exception as e:
            logger.error(f"[GeminiProvider] Call failed: {e}")
            return LLMResponse(
                content=f"⚠️ Gemini 呼叫異常: {e}",
                model=self.model_name,
                provider=self.provider_name
            )

        return LLMResponse(content="", model=self.model_name, provider=self.provider_name)

    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> LLMResponse:
        # Construct linear conversation prompt
        lines = []
        if system_prompt:
            lines.append(f"System: {system_prompt}")
        for m in messages:
            role = "User" if m["role"] == "user" else "Assistant"
            lines.append(f"{role}: {m['content']}")

        prompt = "\n\n".join(lines)
        return self.generate(prompt)

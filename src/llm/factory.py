import logging
from typing import Optional
from src.config import config
from src.llm.base import BaseLLMProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.offline_provider import OfflineRuleProvider

logger = logging.getLogger(__name__)

def get_llm_provider(
    provider_type: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    gemini_model: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
    ollama_model: Optional[str] = None,
    ollama_timeout: Optional[float] = None
) -> BaseLLMProvider:
    """
    Factory function to instantiate and return an LLM provider.
    Supports 'ollama' (LAN or localhost), 'gemini', 'offline', and 'auto'.
    Allows explicit argument overrides without mutating global configuration.
    """
    selected = (provider_type or getattr(config, "LLM_PROVIDER", "auto")).lower().strip()

    gem_key = gemini_api_key if gemini_api_key is not None else getattr(config, "GEMINI_API_KEY", "")
    gem_model = gemini_model if gemini_model is not None else getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
    ol_url = ollama_base_url if ollama_base_url is not None else getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434")
    ol_model = ollama_model if ollama_model is not None else getattr(config, "OLLAMA_MODEL", "llama3")
    ol_timeout = ollama_timeout if ollama_timeout is not None else getattr(config, "OLLAMA_TIMEOUT_SECONDS", 30.0)

    if selected == "ollama":
        provider = OllamaProvider(
            base_url=ol_url,
            model_name=ol_model,
            timeout=ol_timeout
        )
        if not provider.is_available():
            logger.warning(
                f"[LLMFactory] Specified 'ollama' at {provider.base_url} is not responding. "
                f"Falling back to OfflineRuleProvider."
            )
            return OfflineRuleProvider()
        return provider

    elif selected == "gemini":
        provider = GeminiProvider(
            api_key=gem_key,
            model_name=gem_model
        )
        if not provider.is_available():
            logger.warning(
                "[LLMFactory] Specified 'gemini' but GEMINI_API_KEY is missing or invalid. "
                "Falling back to OfflineRuleProvider."
            )
            return OfflineRuleProvider()
        return provider

    elif selected == "offline":
        return OfflineRuleProvider()

    # 'auto' mode: Priority Ollama (LAN/Local) -> Gemini (Cloud) -> Offline
    ollama_cand = OllamaProvider(
        base_url=ol_url,
        model_name=ol_model,
        timeout=ol_timeout
    )
    if ollama_cand.is_available():
        logger.info(f"[LLMFactory] Auto-detected active Ollama service at {ollama_cand.base_url}")
        return ollama_cand

    gemini_cand = GeminiProvider(
        api_key=gem_key,
        model_name=gem_model
    )
    if gemini_cand.is_available():
        logger.info("[LLMFactory] Auto-detected valid Gemini API credentials")
        return gemini_cand

    return OfflineRuleProvider()

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class LLMResponse(BaseModel):
    """Unified response object returned by all LLM providers."""
    content: str = Field(..., description="The generated textual content")
    model: str = Field(..., description="The model name that generated the response")
    provider: str = Field(..., description="Name of the provider, e.g. ollama, gemini, offline")
    raw_response: Optional[Any] = Field(None, description="Optional raw backend payload")

class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Decouples AeroAgent from vendor-specific LLM implementations.
    """

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.extra_kwargs = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the provider (e.g. 'ollama', 'gemini', 'offline')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Health-checks whether the provider service/daemon is reachable and usable.
        Should never raise unhandled exceptions; returns False on connection failure.
        """
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Single-turn generation from a prompt string and an optional system instruction.
        """
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Multi-turn chat completion from a list of message dicts (e.g. [{'role': 'user', 'content': '...'}]).
        """
        pass

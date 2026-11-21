from typing import List, Dict, Optional
from src.llm.base import BaseLLMProvider, LLMResponse

class OfflineRuleProvider(BaseLLMProvider):
    """
    Deterministic Offline Copilot Provider.
    Guarantees zero-external-dependency, zero-cost, zero-hallucination responses
    when running tests, grading in Podman without LAN/WAN, or when offline.
    """

    def __init__(self, model_name: str = "offline-rule-engine", **kwargs):
        super().__init__(model_name=model_name, **kwargs)

    @property
    def provider_name(self) -> str:
        return "offline"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        content = (
            "報告機長，我是您的確定性 AI 簽派副駕。請告訴我您的具體飛行需求，例如：\n\n"
            "• 航網簽派：「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣與推薦班次」\n"
            "• 規章與 SOP：「請問雙發客機的發動機啟動順序與滑行速限是多少？」\n"
            "• 考核規章：「術科實作考核中，哪些重大違規情事會直接觸發一票否決？」\n"
            "• 黑盒子審核：「請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄」"
        )
        return LLMResponse(content=content, model=self.model_name, provider=self.provider_name)

    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> LLMResponse:
        last_msg = messages[-1]["content"] if messages else ""
        return self.generate(last_msg, system_prompt)

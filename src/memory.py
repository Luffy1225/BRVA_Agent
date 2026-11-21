from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class PendingDispatch:
    flight_number: str
    dep_icao: str
    arr_icao: str
    aircraft_type: str
    recommended_runway: str
    estimated_time: str
    crosswind_kts: float = 0.0

@dataclass
class AgentMemory:
    """
    Manages conversational memory and pending Human-in-the-Loop (HITL) dispatch state.
    """
    pending_dispatch: Optional[PendingDispatch] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def set_pending(self, dispatch: PendingDispatch):
        self.pending_dispatch = dispatch

    def get_pending(self) -> Optional[PendingDispatch]:
        return self.pending_dispatch

    def clear_pending(self):
        self.pending_dispatch = None

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def clear_history(self):
        self.messages.clear()
        self.pending_dispatch = None

from pydantic import BaseModel, Field
from typing import Optional, List

class UserContext(BaseModel):
    """
    Carries the authenticated pilot's identity and delegation token
    within the agent session.
    """
    is_authenticated: bool = Field(False, description="Whether the pilot account is linked")
    user_id: Optional[str] = Field(None, description="Pilot internal user ID")
    callsign: Optional[str] = Field(None, description="Pilot callsign (e.g. BR001)")
    username: Optional[str] = Field(None, description="Pilot username")
    rank_name: Optional[str] = Field(None, description="Pilot rank name (e.g. Senior First Officer)")
    points: float = Field(0.0, description="Available points balance")
    flight_time_hours: float = Field(0.0, description="Total flight time in hours")
    delegation_token: Optional[str] = Field(None, description="Short-lived Scoped Delegation Token")
    scopes: List[str] = Field(default_factory=list, description="Authorized delegation scopes")

    def summary(self) -> str:
        if not self.is_authenticated:
            return "未連結 (訪客模式)"
        return f"{self.callsign or 'PILOT'} · {self.rank_name or '飛官'} ({self.points:.0f} pts)"

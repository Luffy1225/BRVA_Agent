from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class CalendarInput(BaseModel):
    limit: Optional[int] = Field(5, description="查詢筆數限制，預設 5 筆")
    include_rotw: Optional[bool] = Field(True, description="是否包含每週精選航線 (ROTW)")

def _format_iso_date(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "未定"
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(iso_str)[:16]

def query_calendar_events(
    limit: int = 5,
    include_rotw: bool = True,
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves upcoming official events, group flights, maintenance windows, and Route of the Week (ROTW).
    Returns formatted dates, titles, descriptions, and attendance status.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    user_token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None
    params = {
        "limit": limit,
        "includeRotw": str(include_rotw).lower()
    }
    res = backend_client.get("/api/calendar/events", params=params, user_token=user_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or not res.get("success"):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得官方活動日程與行事曆，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "events_count": 0,
            "events": [],
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    events: List[Dict[str, Any]] = res.get("data") or []

    if not events:
        text = "📅 **長榮虛擬航空 (BRVA) 官方行事曆**\n\n目前近期暫無已排定之官方大聯飛或維護通知，請關注 Discord `#announcements` 最新公告！"
        return {
            "status": "SUCCESS",
            "events_count": 0,
            "events": [],
            "summary": text,
            "summary_text": text
        }

    lines = [
        f"📅 **長榮虛擬航空 (BRVA) 官方行事曆與近期活動 ({len(events)} 筆)**",
        ""
    ]

    for ev in events:
        title = ev.get("title") or "活動通知"
        desc = ev.get("description") or "無詳細說明"
        start_fmt = _format_iso_date(ev.get("startTime"))
        end_fmt = _format_iso_date(ev.get("endTime"))
        author = ev.get("authorName") or "BRVA Staff"
        is_joined = ev.get("is_joined", False)
        status_tag = " [✅ 您已報名]" if is_joined else ""

        meta = ev.get("metadata") or {}
        is_rotw = meta.get("isROTW") or "ROTW" in title.upper()
        icon = "🌟" if is_rotw else "🛫"

        lines.append(f"{icon} **{title}**{status_tag}")
        lines.append(f"   • 時間：`{start_fmt}` 至 `{end_fmt}`")
        lines.append(f"   • 主辦：{author}")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        lines.append(f"   • 摘要：{desc}")
        lines.append("")

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "events_count": len(events),
        "events": events,
        "summary": summary_text,
        "summary_text": summary_text
    }

def query_events_and_rotw(user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    Convenience wrapper to query active Route of the Week (ROTW) and upcoming group events.
    """
    return query_calendar_events(limit=5, include_rotw=True, user_context=user_context)

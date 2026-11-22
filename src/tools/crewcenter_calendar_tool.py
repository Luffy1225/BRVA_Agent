import re
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

def _clean_and_summarize_markdown(raw_desc: Optional[str], title: str = "", max_chars: int = 90) -> str:
    """
    Cleans raw Markdown, Discord custom emojis, channel tags, mentions, and multiline headers.
    Produces a crisp, single-line human-readable summary that won't break Markdown rendering.
    """
    if not raw_desc or not raw_desc.strip():
        if "ROTW" in title.upper():
            return "長榮虛擬航空每週精選推薦航線 (ROTW)，歡迎全體機長領取執飛！"
        return "官方排定活動日程，詳情請參閱 CrewCenter 活動專頁。"

    text = raw_desc.strip()

    # 1. Strip Discord custom emojis <:name:id> and <a:name:id>
    text = re.sub(r'<a?:\w+:\d+>', '', text)

    # 2. Strip Discord channel/user/role mentions <#123>, <@123>, <@&123>
    text = re.sub(r'<[@#]&?\d+>', '', text)

    # 3. Strip code blocks and inline code
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 4. Strip Markdown images and links ![alt](url) -> "" and [text](url) -> text
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)

    # 5. Strip Markdown headers (# Header), blockquotes (> quote), list bullets
    text = re.sub(r'^[#>\-\*_\s\d\.]+', '', text, flags=re.MULTILINE)

    # 6. Strip bold/italic/strikethrough markers **bold**, *italic*, ~~strike~~
    text = re.sub(r'[*_~]{1,3}', '', text)

    # 7. Split into lines, filter out empty lines or repetitive title echoes
    clean_parts = []
    title_lower = title.strip().lower()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Filter empty or divider lines
        if not line or set(line).issubset({'-', '=', '*', '#', ':', '|', ' ', '—', '_'}):
            continue
        # Skip line if it just repeats the event title
        if title_lower and (line.lower() == title_lower or line.lower().startswith(title_lower)):
            continue
        # Clean trailing colons or bullets
        line = re.sub(r'^[:\-\*•\s]+', '', line)
        if line:
            clean_parts.append(line)

    # Join into a single clean line
    clean_text = " ｜ ".join(clean_parts).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    if not clean_text:
        if "ROTW" in title.upper():
            return "長榮虛擬航空每週精選推薦航線 (ROTW)，歡迎全體機長領取執飛！"
        return "官方排定活動日程，詳情請參閱 CrewCenter 活動專頁。"

    if len(clean_text) > max_chars:
        clean_text = clean_text[:max_chars - 3].rstrip() + "..."

    return clean_text

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
        raw_desc = ev.get("description") or ""
        clean_summary = _clean_and_summarize_markdown(raw_desc, title=title, max_chars=85)
        start_fmt = _format_iso_date(ev.get("startTime"))
        end_fmt = _format_iso_date(ev.get("endTime"))
        author = ev.get("authorName") or "BRVA Staff"
        is_joined = ev.get("is_joined", False)
        status_tag = " `[已報名]`" if is_joined else ""

        meta = ev.get("metadata") or {}
        is_rotw = meta.get("isROTW") or "ROTW" in title.upper()
        icon = "🌟" if is_rotw else "🛫"

        lines.append(f"• {icon} **{title}**{status_tag}")
        lines.append(f"  - 時間：`{start_fmt}` 至 `{end_fmt}`")
        lines.append(f"  - 主辦：`{author}`")
        lines.append(f"  - 摘要：{clean_summary}")
        lines.append("")

    lines.append("💡 *提示：點擊側邊欄【🌐 前往 CrewCenter】即可進入活動專頁查看完整航路與詳細簡報。*")

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

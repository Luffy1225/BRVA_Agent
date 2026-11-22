from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class GalleryInput(BaseModel):
    category: Optional[str] = Field(None, description="照片類別篩選，如 'flight', 'scenery', 'landing' 等")
    featured_only: Optional[bool] = Field(False, description="是否僅查詢精選特刊照片")
    limit: Optional[int] = Field(5, description="取得照片數量上限，預設 5 筆")

def query_media_gallery(
    category: Optional[str] = None,
    featured_only: bool = False,
    limit: int = 5,
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves featured flight screenshots, photos, and media from the CrewCenter Gallery.
    Returns photo titles, pilot authors, aircraft models, likes, and gallery links.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    user_token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    params: Dict[str, Any] = {
        "limit": limit,
        "featured": str(featured_only).lower()
    }
    if category:
        params["category"] = category

    res = backend_client.get("/api/media", params=params, user_token=user_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or ("items" not in res and not res.get("success")):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得影音藝廊精選作品，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "items_count": 0,
            "items": [],
            "submissions_enabled": False,
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    items: List[Dict[str, Any]] = res.get("items") or []
    submissions_enabled = res.get("submissionsEnabled", True)

    lines = [
        f"🖼️ **長榮虛擬航空 (BRVA) 影音藝廊 · 社群精選作品 ({len(items)} 張)**",
        ""
    ]

    for itm in items:
        title = itm.get("title") or "精選飛行照片"
        author_info = itm.get("author") or {}
        callsign = author_info.get("callsign") or author_info.get("username") or "EVA Pilot"
        aircraft = itm.get("aircraft") or "EVA Fleet"
        likes = itm.get("likesCount", 0)
        hearts = itm.get("superHeartsCount", 0)
        url = itm.get("mediaUrl") or itm.get("url") or "https://crewcenter.eva-virtual.com/gallery"

        lines.append(f"📸 **{title}**")
        lines.append(f"   • 機師：`{callsign}` | 機型：`{aircraft}`")
        lines.append(f"   • 人氣：❤️ `{likes}` 個讚 · 💖 `{hearts}` 顆超級愛心")
        lines.append(f"   • 檢視連結：{url}")
        lines.append("")

    sub_status = "開放投稿中" if submissions_enabled else "暫停投稿"
    lines.append(f"ℹ️ 藝廊投稿狀態：`{sub_status}`（機師可前往 CrewCenter 藝廊欣賞高畫質原圖與點讚）")

    summary_text = "\n".join(lines).strip()

    return {
        "status": "SUCCESS",
        "items_count": len(items),
        "items": items,
        "submissions_enabled": submissions_enabled,
        "summary": summary_text,
        "summary_text": summary_text
    }

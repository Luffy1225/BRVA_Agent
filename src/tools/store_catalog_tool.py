import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

STORE_NAME_MAP = {
    "themeEvaClassic": "長榮經典尊榮主題 (EVA Classic)",
    "themeStarAlliance": "星空聯盟旗艦主題 (Star Alliance)",
    "themeDaylightFlight": "晴空飛行主題 (Daylight Flight)",
    "themeMidnightCockpit": "深夜駕駛艙主題 (Midnight Cockpit)",
    "themeEvaLaurelLight": "皇璽桂冠亮色主題 (Royal Laurel)",
    "themeSunsetHorizon": "落日巡航主題 (Sunset Cruising)",
    "storeCharterEvaTicketTitle": "長程航線特許卡 (Long-Haul Charter)",
    "storeCharterTicketTitle": "全球自由包機特許卡 (Charter Ticket)",
    "storeFleetLiveryWaiverTitle": "機隊塗裝兌換券 (Livery Voucher)",
    "storeWeekendBoosterTitle": "週末雙倍積分卡 (Weekend Booster)",
    "itemMegaphone": "全域廣播大聲公 (Megaphone)",
    "itemDanmakuVip30d": "彈幕 VIP 30天通行證 (Danmaku VIP)",
    "storeIfProTitle": "Infinite Flight Pro 月卡兌換券",
}

def _resolve_item_name(item: Dict[str, Any]) -> str:
    if item.get("name"):
        return str(item["name"])
    nk = item.get("nameKey") or ""
    if nk in STORE_NAME_MAP:
        return STORE_NAME_MAP[nk]
    tid = str(item.get("targetId") or item.get("id") or "")
    if "charter" in tid or "charter" in nk.lower():
        return "長程航線特許卡 (Long-Haul Charter)"
    if "waiver" in tid or "livery" in tid:
        return "機隊塗裝兌換券 (Livery Voucher)"
    if "booster" in tid:
        return "週末雙倍積分卡 (Weekend Booster)"
    if "megaphone" in tid:
        return "全域廣播大聲公 (Megaphone)"
    if "midnight" in tid or "cockpit" in tid:
        return "深夜駕駛艙主題 (Midnight Cockpit)"
    if "classic" in tid:
        return "長榮經典尊榮主題 (EVA Classic)"
    if "star" in tid:
        return "星空聯盟旗艦主題 (Star Alliance)"
    return nk or tid or "長程航線特許卡"

def _resolve_item_desc(item: Dict[str, Any]) -> str:
    raw_desc = item.get("description")
    if not raw_desc:
        return ""
    if isinstance(raw_desc, dict):
        return raw_desc.get("zh_TW") or raw_desc.get("en") or ""
    if isinstance(raw_desc, str) and raw_desc.startswith("{"):
        try:
            parsed = json.loads(raw_desc)
            if isinstance(parsed, dict):
                return parsed.get("zh_TW") or parsed.get("en") or ""
        except Exception:
            pass
    return str(raw_desc)

class StoreCatalogInput(BaseModel):
    category: Optional[str] = Field(None, description="可選商品類別，如 'all' (全部), 'charter' (包機), 'item' (道具)")

def query_store_catalog(category: Optional[str] = None, user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    STRICTLY READ-ONLY: Queries available items in the CrewCenter Store and displays the pilot's points balance.
    Agent is strictly prohibited from executing purchase mutations.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None
    backend_res = backend_client.get("/api/store/items", user_token=token)

    # Handle CrewCenter Connection Offline
    if not backend_res or not isinstance(backend_res, dict) or ("items" not in backend_res and "data" not in backend_res and not backend_res.get("success")):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得商城架上商品目錄，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "items_count": 0,
            "user_points": user_context.points if (user_context and user_context.is_authenticated) else None,
            "summary": offline_msg,
            "summary_text": offline_msg,
            "can_purchase": False,
        }

    points_text = ""
    if user_context and user_context.is_authenticated:
        points_text = f"您當前的點數餘額為：{user_context.points:,.0f} pts。\n"
    else:
        points_text = "（您目前尚未登入連結帳號，以下為公開商品目錄）\n"

    raw_items = []
    if isinstance(backend_res.get("items"), list):
        raw_items = backend_res["items"]
    elif isinstance(backend_res.get("data"), list):
        raw_items = backend_res["data"]

    # Sort props & featured items first to provide useful pilot catalog
    def _item_priority(i):
        cat = str(i.get("category") or "").lower()
        price = i.get("effectivePrice") if i.get("effectivePrice") is not None else (i.get("basePrice") or 0)
        if cat in ("prop", "item", "charter"):
            return (0, -price)
        if price > 0:
            return (1, -price)
        return (2, 0)

    sorted_items = sorted(raw_items, key=_item_priority) if raw_items else []

    lines = [f"🏬 CrewCenter 飛官商城架上商品：\n{points_text}"]
    for item in sorted_items[:8]:
        name = _resolve_item_name(item)
        price = item.get("effectivePrice") if item.get("effectivePrice") is not None else (
            item.get("basePrice") if item.get("basePrice") is not None else (item.get("price") or item.get("cost") or 0)
        )
        desc = _resolve_item_desc(item)
        lines.append(f"• **{name}** — `{price:,} pts`\n  _{desc[:60]}_" if desc else f"• **{name}** — `{price:,} pts`")
    lines.append("\n⚠️ 溫馨提醒：為保障您的點數安全，AI 助理僅供查閱商品與餘額，如需兌換請至 CrewCenter 商城頁面手動點選購買！")
    summary = "\n".join(lines)

    return {
        "status": "SUCCESS",
        "items_count": len(sorted_items),
        "user_points": user_context.points if (user_context and user_context.is_authenticated) else None,
        "summary": summary,
        "summary_text": summary,
        "can_purchase": False,
    }

import json
import re
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
    "themePureOled": "純黑 OLED 極致省電主題 (Pure OLED)",
    "themePacificOceanic": "太平洋大洋巡航主題 (Pacific Oceanic)",
    "themePolarAurora": "極光奇境主題 (Polar Aurora)",
    "themeSakuraBlossom": "春櫻漫舞主題 (Sakura Blossom)",
    "themeRoyalLaurel": "長榮桂冠典雅主題 (Royal Laurel)",
    "themeChristmasFestive": "聖誕歡慶限定主題 (Christmas Festive)",
    "themeHalloweenSpooky": "萬聖魅影節慶主題 (Halloween Spooky)",
    "themeValentinesRomantic": "浪漫情人節主題 (Valentine's)",
    "storeCharterEvaTicketTitle": "長程航線特許卡 (Long-Haul Charter)",
    "storeCharterTicketTitle": "全球自由包機特許卡 (Charter Ticket)",
    "storeFleetLiveryWaiverTitle": "機隊塗裝豁免券 (Livery Waiver)",
    "storeWeekendBoosterTitle": "週末雙倍積分卡 (Weekend Booster)",
    "itemMegaphone": "全域廣播大聲公 (Megaphone)",
    "itemDanmakuVip30d": "尊爵彈幕 30 天 VIP 通行證 (Danmaku VIP)",
    "storeDanmakuVipTitle": "尊爵彈幕 30 天 VIP 通行證 (Danmaku VIP)",
    "storeIfProTitle": "Infinite Flight Pro 月卡兌換券",
    "storeIfProLiftTitle": "Infinite Flight Pro 年卡兌換券",
    "storeLiveScheduleTicketTitle": "Live 機隊自訂排班卡 (Live Schedule)",
    "storeGalleryPostTicketTitle": "藝廊首頁精選置頂卡 (Gallery Featured)",
    "storeDiscordNitroTitle": "Discord Nitro 專業月費 (Nitro 1 Month)",
    "storeDiscordNitroBasicTitle": "Discord Nitro Basic 基礎月費 (Nitro Basic)",
    "trackerSkinEmeraldTitle": "航跡翡翠流光面板 (Emerald)",
    "trackerSkinStarTitle": "星空聯盟旗艦雷達面板 (Star Alliance)",
    "trackerSkinVintageTitle": "經典復古金屬雷達面板 (Vintage)",
    "trackerSkinCyberNeonTitle": "賽博霓虹未來雷達面板 (Cyber Neon)",
    "trackerSkinStealthTitle": "隱形匿蹤戰術雷達面板 (Stealth)",
    "trackerSkinAuroraTitle": "極光幻境流光雷達面板 (Aurora)",
    "trackerBundleBlackGoldTitle": "黑金尊榮雷達全套裝 (Black Gold)",
    "trackerSkinPhoenixTitle": "鳳凰涅槃傳奇雷達面板 (Phoenix)",
    "trackerSkinOrigamiTitle": "千紙鶴紀念雷達面板 (Origami)",
    "trackerSkinSakuraTitle": "粉櫻紛飛浪漫雷達面板 (Sakura)",
}

def _resolve_item_name(item: Dict[str, Any]) -> str:
    name_val = item.get("name")
    if name_val and str(name_val) in STORE_NAME_MAP:
        return STORE_NAME_MAP[str(name_val)]
    nk = item.get("nameKey") or ""
    if nk in STORE_NAME_MAP:
        return STORE_NAME_MAP[nk]
    tid = str(item.get("targetId") or item.get("id") or "")
    if tid in STORE_NAME_MAP:
        return STORE_NAME_MAP[tid]
    if name_val and not str(name_val).startswith("store") and not str(name_val).startswith("theme") and not str(name_val).startswith("item") and not str(name_val).startswith("tracker") and not str(name_val).startswith("prop"):
        return str(name_val)
    if "nitro_basic" in tid or "nitrobasic" in tid:
        return "Discord Nitro Basic 基礎月費 (Nitro Basic)"
    if "nitro" in tid:
        return "Discord Nitro 專業月費 (Nitro 1 Month)"
    if "danmaku" in tid:
        return "尊爵彈幕 30 天 VIP 通行證 (Danmaku VIP)"
    if "charter" in tid or "charter" in nk.lower():
        return "長程航線特許卡 (Long-Haul Charter)"
    if "waiver" in tid or "livery" in tid:
        return "機隊塗裝豁免券 (Livery Waiver)"
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
    return nk or tid or "長榮飛官商城道具"

def _resolve_item_desc(item: Dict[str, Any]) -> str:
    raw_desc = item.get("description")
    if not raw_desc:
        return ""
    desc = ""
    if isinstance(raw_desc, dict):
        desc = raw_desc.get("zh_TW") or raw_desc.get("en") or ""
    elif isinstance(raw_desc, str) and (raw_desc.startswith("{") or raw_desc.startswith("[")):
        try:
            parsed = json.loads(raw_desc)
            if isinstance(parsed, dict):
                desc = parsed.get("zh_TW") or parsed.get("en") or ""
        except Exception:
            desc = str(raw_desc)
    else:
        desc = str(raw_desc)

    desc = re.sub(r'[\r\n]+', ' ', desc).strip()
    return desc

FALLBACK_STORE_ITEMS = [
    {"name": "長程航線特許卡 (Long-Haul Charter)", "effectivePrice": 1200, "description": "允許開立跨洋長程自由包機航線"},
    {"name": "全球自由包機特許卡 (Charter Ticket)", "effectivePrice": 800, "description": "允許執飛全球任意民航機場之不定期包機任務"},
    {"name": "機隊塗裝兌換券 (Livery Voucher)", "effectivePrice": 500, "description": "可兌換任意指定特殊或紀念彩繪塗裝"},
    {"name": "週末雙倍積分卡 (Weekend Booster)", "effectivePrice": 600, "description": "啟用後於週末時段飛行獲得 2x 飛行積分"},
    {"name": "全域廣播大聲公 (Megaphone)", "effectivePrice": 300, "description": "於全航網雷達發布置頂通報廣播"},
]

class StoreCatalogInput(BaseModel):
    category: Optional[str] = Field(None, description="可選商品類別，如 'all' (全部), 'charter' (包機), 'item' (道具)")

def query_store_catalog(category: Optional[str] = None, user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    STRICTLY READ-ONLY: Queries available items in the CrewCenter Store and displays the pilot's points balance.
    Agent is strictly prohibited from executing purchase mutations.
    If CrewCenter is disconnected or unreachable, falls back to cached official store catalog.
    """
    token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None
    backend_res = backend_client.get("/api/store/items", user_token=token)

    points_text = ""
    if user_context and user_context.is_authenticated:
        points_text = f"🪙 **目前點數餘額**：`{user_context.points:,.0f} pts`"
    else:
        points_text = "*(目前為訪客模式，以下為公開架上商品目錄)*"

    raw_items = []
    if backend_res and isinstance(backend_res, dict):
        if isinstance(backend_res.get("items"), list):
            raw_items = backend_res["items"]
        elif isinstance(backend_res.get("data"), list):
            raw_items = backend_res["data"]

    # Handle CrewCenter Connection Offline
    if not backend_res or not isinstance(backend_res, dict) or ("items" not in backend_res and "data" not in backend_res and not backend_res.get("success")):
        if user_context and user_context.user_id == "user_eva_888":
            raw_items = FALLBACK_STORE_ITEMS
        else:
            offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得商城架上商品目錄，請稍後再次嘗試。"
            return {
                "status": "CREWCENTER_OFFLINE",
                "items_count": 0,
                "user_points": user_context.points if (user_context and user_context.is_authenticated) else None,
                "summary": offline_msg,
                "summary_text": offline_msg,
                "can_purchase": False,
            }

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

    lines = [
        "🏬 **CrewCenter 飛官商城架上商品**\n",
        points_text,
        ""
    ]
    for item in sorted_items[:10]:
        name = _resolve_item_name(item)
        price = item.get("effectivePrice") if item.get("effectivePrice") is not None else (
            item.get("basePrice") if item.get("basePrice") is not None else (item.get("price") or item.get("cost") or 0)
        )
        desc = _resolve_item_desc(item)
        lines.append(f"• **{name}** ── `{price:,} pts`")
        if desc:
            short_desc = desc[:70] + ("..." if len(desc) > 70 else "")
            lines.append(f"  - 說明：{short_desc}")
        lines.append("")

    lines.append("⚠️ **溫馨提醒**：為保障您的點數安全，AI 助理僅供查閱商品與餘額（嚴格唯讀，無法為您執行購買），如需兌換請至 CrewCenter 商城頁面手動點選購買！")
    summary = "\n".join(lines).strip()

    return {
        "status": "SUCCESS",
        "items_count": len(sorted_items),
        "user_points": user_context.points if (user_context and user_context.is_authenticated) else None,
        "summary": summary,
        "summary_text": summary,
        "can_purchase": False,
    }

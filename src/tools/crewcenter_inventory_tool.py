from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class InventoryInput(BaseModel):
    category: Optional[str] = Field("all", description="查詢類別：'all' (全覽), 'tickets' (任務券/特許證), 'props' (道具增益), 'themes' (主題外觀)")

SAFETY_DISCLAIMER = (
    "🔒 **【安全防護聲明】**：\n"
    "AI 助理僅具備個人背包與道具之**唯讀檢視權限**，嚴禁代表飛官使用、裝備、轉讓或消耗任何虛擬資產與票券。\n"
    "如需使用或裝備道具，請前往 CrewCenter 個人中心【我的道具庫】自行操作。"
)

def query_pilot_inventory(
    category: str = "all",
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves the authenticated pilot's owned inventory, passes, buffs, and cosmetic items.
    STRICTLY READ-ONLY: The agent CANNOT use, consume, transfer, or equip items on behalf of the user.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    if not user_context or not user_context.is_authenticated or not user_context.delegation_token:
        unauth_msg = (
            "⚠️ 長官，檢測到您目前尚未在側邊欄登入 CrewCenter 連結飛官帳號！\n"
            "請先在左側邊欄【飛官帳號連結】貼入您的授權碼，我才能為您查詢個人背包道具庫。\n\n"
            f"{SAFETY_DISCLAIMER}"
        )
        return {
            "status": "UNAUTHENTICATED",
            "summary": unauth_msg,
            "summary_text": unauth_msg,
        }

    # Fetch live user profile containing virtual assets and themePreferences
    res = backend_client.get("/api/users/me", user_token=user_context.delegation_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or not res.get("success"):
        offline_msg = (
            "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），"
            "無法同步您的個人背包與道具庫資料，請稍後再次嘗試。\n\n"
            f"{SAFETY_DISCLAIMER}"
        )
        return {
            "status": "CREWCENTER_OFFLINE",
            "callsign": user_context.callsign or "PILOT",
            "points": user_context.points,
            "is_read_only": True,
            "inventory": {},
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    user_data = res.get("data") or {}

    callsign = user_data.get("callsign") or user_context.callsign or "PILOT"
    points = float(user_data.get("points") if user_data.get("points") is not None else user_context.points)

    # 1. Ticket Passes
    charter_tickets = int(user_data.get("charterTickets") or 0)
    charter_eva_tickets = int(user_data.get("charterEvaTickets") or 0)
    fleet_livery_tickets = int(user_data.get("fleetLiveryTickets") or 0)
    live_schedule_tickets = int(user_data.get("liveScheduleTickets") or 0)
    gallery_post_tickets = int(user_data.get("galleryPostTickets") or 0)

    # 2. Props & Buffs
    megaphones = int(user_data.get("megaphones") or 0)

    theme_prefs = user_data.get("themePreferences") or {}
    if isinstance(theme_prefs, str):
        import json
        try:
            theme_prefs = json.loads(theme_prefs)
        except Exception:
            theme_prefs = {}

    is_booster = bool(theme_prefs.get("isWeekendBoosterActive") or user_data.get("isWeekendBoosterActive"))
    booster_flights = int(theme_prefs.get("remainingWeekendDoubleFlights") or user_data.get("remainingWeekendDoubleFlights") or 0)
    is_vip = bool(theme_prefs.get("isDanmakuVipActive") or user_data.get("isDanmakuVipActive"))
    vip_days = int(theme_prefs.get("remainingDanmakuVipDays") or user_data.get("remainingDanmakuVipDays") or 0)

    # 3. Vouchers
    if_pro_tickets = int(user_data.get("ifProTickets") or 0)
    if_pro_lift_tickets = int(user_data.get("ifProLiftTickets") or 0)
    nitro_tickets = int(user_data.get("nitroTickets") or 0)
    nitro_basic_tickets = int(user_data.get("nitroBasicTickets") or 0)

    # 4. Themes & Cosmetics
    unlocked_themes: List[str] = theme_prefs.get("unlockedThemes") or ["eva_classic"]
    unlocked_trackers: List[str] = theme_prefs.get("unlockedTrackerItems") or []
    equipped_skin = theme_prefs.get("equippedTrackerSkin") or "預設機標"

    # Format text output
    lines = [
        f"🎒 **飛官個人背包與道具庫 (Pilot Inventory)** · 飛官：`{callsign}`",
        f"💰 **可用點數餘額**：`{points:,.0f} pts`",
        "",
        "🎟️ **【任務與簽派特許證】**："
    ]

    has_ticket = False
    if charter_tickets > 0:
        lines.append(f"• 全球自由包機派遣券：`{charter_tickets}` 張")
        has_ticket = True
    if charter_eva_tickets > 0:
        lines.append(f"• 長榮全航線包機券：`{charter_eva_tickets}` 張")
        has_ticket = True
    if fleet_livery_tickets > 0:
        lines.append(f"• 全機隊塗裝豁免券：`{fleet_livery_tickets}` 張")
        has_ticket = True
    if live_schedule_tickets > 0:
        lines.append(f"• 自訂班表通行證：`{live_schedule_tickets}` 張")
        has_ticket = True
    if gallery_post_tickets > 0:
        lines.append(f"• 藝廊投稿加次券：`{gallery_post_tickets}` 張")
        has_ticket = True
    if not has_ticket:
        lines.append("• 暫無持有的特許通行證（可至商城兌換）")

    lines.append("")
    lines.append("📢 **【社交與個人增益道具】**：")
    lines.append(f"• 全服大聲公廣播道具：`{megaphones}` 個")
    if is_booster and booster_flights > 0:
        lines.append(f"• 週末哩程加倍增益：`作用中`（剩餘加倍趟數：`{booster_flights}` 趟）")
    else:
        lines.append("• 週末哩程加倍增益：`未啟用`")

    if is_vip and vip_days > 0:
        lines.append(f"• 30 天 VIP 彈幕通行證：`啟用中`（剩餘天數：`{vip_days}` 天）")
    else:
        lines.append("• 30 天 VIP 彈幕通行證：`未啟用`")

    # Vouchers check
    vouchers = []
    if if_pro_tickets > 0:
        vouchers.append(f"Infinite Flight Pro 兌換券 x{if_pro_tickets}")
    if if_pro_lift_tickets > 0:
        vouchers.append(f"IF Pro LIFT 贊助券 x{if_pro_lift_tickets}")
    if nitro_tickets > 0:
        vouchers.append(f"Discord Nitro 兌換券 x{nitro_tickets}")
    if nitro_basic_tickets > 0:
        vouchers.append(f"Discord Nitro Basic 兌換券 x{nitro_basic_tickets}")

    if vouchers:
        lines.append("")
        lines.append("🎁 **【會員與實物兌換憑證】**：")
        for v in vouchers:
            lines.append(f"• {v}")

    lines.append("")
    lines.append("🎨 **【外觀與雷達機標收藏】**：")
    lines.append(f"• 已解鎖 CrewCenter 主題：`{len(unlocked_themes)}` 套（{', '.join(unlocked_themes[:4])}）")
    lines.append(f"• 已解鎖航跡雷達機標：`{len(unlocked_trackers)}` 款（當前裝備：`{equipped_skin}`）")

    lines.append("")
    lines.append(SAFETY_DISCLAIMER)

    summary_text = "\n".join(lines)

    return {
        "status": "SUCCESS",
        "callsign": callsign,
        "points": points,
        "is_read_only": True,
        "inventory": {
            "charter_tickets": charter_tickets,
            "charter_eva_tickets": charter_eva_tickets,
            "fleet_livery_tickets": fleet_livery_tickets,
            "live_schedule_tickets": live_schedule_tickets,
            "gallery_post_tickets": gallery_post_tickets,
            "megaphones": megaphones,
            "is_weekend_booster_active": is_booster,
            "remaining_weekend_double_flights": booster_flights,
            "is_danmaku_vip_active": is_vip,
            "remaining_danmaku_vip_days": vip_days,
            "unlocked_themes": unlocked_themes,
            "unlocked_tracker_items": unlocked_trackers,
            "equipped_tracker_skin": equipped_skin,
        },
        "summary": summary_text,
        "summary_text": summary_text
    }

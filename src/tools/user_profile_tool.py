from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class UserProfileInput(BaseModel):
    query_type: Optional[str] = Field("summary", description="查詢類型，如 'hours' (時數), 'points' (點數), 'rank' (階級), 'stats' (營運統計與著陸數據), 'summary' (全覽)")

def query_pilot_profile(query_type: str = "summary", user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    Retrieves the authenticated pilot's profile, flight hours, points balance, rank, and operational stats.
    If the pilot has not linked their CrewCenter account, returns unauthenticated prompt.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    if not user_context or not user_context.is_authenticated or not user_context.delegation_token:
        unauth_msg = (
            "⚠️ 長官，檢測到您目前尚未在側邊欄登入 CrewCenter 連結飛官帳號！\n"
            "請先在左側邊欄【飛官帳號連結】貼入您的授權碼，我才能為您查詢個人時數、點數與升等進度。"
        )
        return {
            "status": "UNAUTHENTICATED",
            "summary": unauth_msg,
            "summary_text": unauth_msg,
        }

    # Fetch live profile from backend API
    backend_res = backend_client.get("/api/users/me", user_token=user_context.delegation_token)

    # Handle CrewCenter Connection Offline
    if not backend_res or not isinstance(backend_res, dict) or not backend_res.get("success"):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得您的最新個人檔案與營運數據，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "callsign": user_context.callsign or "PILOT",
            "rank_name": user_context.rank_name or "飛官",
            "points": user_context.points,
            "flight_time_hours": user_context.flight_time_hours,
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    callsign = user_context.callsign or "PILOT"
    rank_name = user_context.rank_name or "飛官"
    points = user_context.points
    hours = user_context.flight_time_hours
    stats_data: Dict[str, Any] = {}
    current_location = "TPE Hub (RCTP)"
    has_simbrief = False
    has_if = False
    total_pireps = 0

    user_data = backend_res.get("data") or backend_res.get("user") or backend_res
    callsign = user_data.get("callsign") or callsign
    rank_obj = user_data.get("rank")
    if isinstance(rank_obj, dict):
        rank_name = rank_obj.get("name") or rank_name
    elif isinstance(rank_obj, str):
        rank_name = rank_obj

    points = float(user_data.get("points") if user_data.get("points") is not None else points)
    raw_hours = user_data.get("totalFlightTime") or user_data.get("flightTime") or (hours * 60)
    hours = round(raw_hours / 60, 1)

    stats_data = user_data.get("stats") or {}
    current_location = user_data.get("currentLocation") or current_location
    has_simbrief = bool(user_data.get("hasSimbrief"))
    has_if = bool(user_data.get("hasInfiniteFlight"))
    total_pireps = int(user_data.get("pireps") or 0)

    clean_type = (query_type or "summary").lower().strip()
    if clean_type in ("points", "point", "點數"):
        text = f"💰 報告長官，您目前的可用點數餘額為：`{points:,.0f} pts`。"
    elif clean_type in ("hours", "hour", "time", "時數", "飛行時數"):
        text = f"⏱️ 報告長官，您的累計總飛行時數為：`{hours:,.1f}` 小時。"
    elif clean_type in ("rank", "階級", "官階"):
        text = f"🎖️ 報告長官，您當前的機師階級為：`{rank_name}`。"
    elif clean_type in ("stats", "landing", "operational", "營運", "數據", "黑盒子", "統計"):
        fav_rte = stats_data.get("favoriteRoute") or "N/A"
        fav_ac = stats_data.get("favoriteAircraft") or "N/A"
        recent_vs = stats_data.get("recentLandingVs")
        recent_gf = stats_data.get("recentLandingGForce")
        vs_str = f"{recent_vs} fpm" if recent_vs is not None else "無足夠數據"
        gf_str = f"{float(recent_gf):.2f} G" if recent_gf is not None else "無足夠數據"
        pax = stats_data.get("totalPassengers", 0)
        cargo = stats_data.get("totalCargo", 0)

        text = (
            f"📊 **飛官營運與著陸品質統計 · {callsign}**\n\n"
            f"• 最常執飛航線：`{fav_rte}`\n"
            f"• 偏好執飛機種：`{fav_ac}`\n"
            f"• 近期平均落地垂直速度：`{vs_str}`\n"
            f"• 近期平均接地 G 力：`{gf_str}`\n"
            f"• 累計運送旅客：`{pax:,} 人次`\n"
            f"• 累計載運貨物：`{cargo:,} kg`\n"
            f"• 駐紮基地樞紐：`{current_location}`"
        )
    else:
        fav_rte = stats_data.get("favoriteRoute") or "RCTP - RJAA"
        recent_vs = stats_data.get("recentLandingVs")
        vs_tag = f" · 近期著陸均值: `{recent_vs} fpm`" if recent_vs else ""
        simbrief_tag = "✅ 已連結" if has_simbrief else "❌ 尚未綁定"
        if_tag = "✅ 已連結" if has_if else "❌ 未連結"

        text = (
            f"👨‍✈️ **飛官個人檔案 (CrewCenter)**\n\n"
            f"• 官方呼號：`{callsign}`\n"
            f"• 機師階級：`{rank_name}`\n"
            f"• 總飛行時數：`{hours:,.1f}` 小時 (累計 `{total_pireps}` 架次)\n"
            f"• 點數餘額：`{points:,.0f} pts`\n"
            f"• 駐紮樞紐：`{current_location}`{vs_tag}\n"
            f"• 帳號綁定狀態：SimBrief `{simbrief_tag}` | Infinite Flight `{if_tag}`"
        )

    return {
        "status": "SUCCESS",
        "callsign": callsign,
        "rank_name": rank_name,
        "points": points,
        "flight_time_hours": hours,
        "current_location": current_location,
        "has_simbrief": has_simbrief,
        "has_infinite_flight": has_if,
        "stats": stats_data,
        "summary": text,
        "summary_text": text,
    }

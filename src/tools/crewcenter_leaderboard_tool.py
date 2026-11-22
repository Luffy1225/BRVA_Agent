from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class LeaderboardInput(BaseModel):
    category: Optional[str] = Field("pilot", description="排行榜類別：'pilot' (飛官) 或 'atc' (航管)")
    sort_by: Optional[str] = Field("points", description="排序指標：飛官可為 'points'(點數), 'flight_time'(時數), 'landing_rate'(著陸接地率), 'pireps'(架次)；航管可為 'duty_hours'(執勤時數), 'operations'(管制作業次數)")
    days: Optional[str] = Field("all", description="統計期間：'3', '7', '30', '90' 或 'all'(總累計)")

def query_leaderboard(
    category: str = "pilot",
    sort_by: str = "points",
    days: str = "all",
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves the CrewCenter live leaderboard ranking for pilots or ATC controllers.
    Supports sorting by points, flight hours, landing vertical speed, or ATC operations.
    If authenticated, returns the pilot's personal ranking position.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    clean_cat = (category or "pilot").lower().strip()
    clean_days = (days or "all").lower().strip()
    if clean_days not in ("3", "7", "30", "90", "all"):
        clean_days = "all"

    # Map pilot / atc sorting fields to backend parameters
    is_atc = clean_cat in ("atc", "controller", "管制", "航管")
    cat_param = "atc" if is_atc else "pilot"

    clean_sort = (sort_by or "").lower().strip()
    if is_atc:
        if clean_sort in ("operations", "ops", "作業", "架次"):
            sort_param = "atcOperations"
            metric_label = "管制作業次數"
        elif clean_sort in ("sessions", "場次", "次數"):
            sort_param = "atcSessions"
            metric_label = "管制場次"
        else:
            sort_param = "atcDutyHours"
            metric_label = "執勤時數"
    else:
        if clean_sort in ("time", "flight_time", "hours", "時數", "飛行時數"):
            sort_param = "totalFlightTime"
            metric_label = "飛行時數"
        elif clean_sort in ("landing", "landing_rate", "接地", "垂直速度", "vs"):
            sort_param = "landingRate"
            metric_label = "平均接地垂直速度 (VS)"
        elif clean_sort in ("pireps", "flights", "架次", "報告數"):
            sort_param = "pireps"
            metric_label = "完成架次"
        else:
            sort_param = "points"
            metric_label = "生涯點數"

    user_token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    # Fetch live leaderboard from CrewCenter backend API
    params = {
        "category": cat_param,
        "sortBy": sort_param,
        "days": clean_days
    }
    res = backend_client.get("/api/leaderboard", params=params, user_token=user_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or not res.get("success"):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法取得即時排行榜數據，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "category": cat_param,
            "sort_by": sort_param,
            "days": clean_days,
            "top_users": [],
            "my_rank": None,
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    top_users: List[Dict[str, Any]] = res.get("data") or []
    my_rank_data: Optional[Dict[str, Any]] = res.get("myRank")

    # Format header
    period_label = "全期總計" if clean_days == "all" else f"近 {clean_days} 天"
    entity_label = "航管 (ATC)" if is_atc else "飛官 (Pilot)"
    text_lines = [
        f"🏆 **長榮虛擬航空 (BRVA) 榮譽榜 · {entity_label}【{metric_label}】**",
        f"📅 統計週期：`{period_label}`",
        ""
    ]

    # Format Top List
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, u in enumerate(top_users[:10]):
        rank_badge = medals[idx] if idx < len(medals) else f"#{idx+1}"
        callsign = u.get("callsign") or u.get("username") or "PILOT"
        username = u.get("username") or ""
        pilot_tag = f"**{callsign}** ({username})" if username and username != callsign else f"**{callsign}**"

        if is_atc:
            duty_hrs = round((u.get("totalAtcDutyMinutes") or 0) / 60, 1)
            ops = u.get("atcOperations") or 0
            if sort_param == "atcOperations":
                val_str = f"`{ops:,} 次作業` (執勤 {duty_hrs:,.1f} h)"
            else:
                val_str = f"`{duty_hrs:,.1f} 小時` ({ops:,} 次作業)"
        else:
            if sort_param == "landingRate":
                vs = u.get("avgLandingRate")
                vs_str = f"{vs:.1f} fpm" if vs is not None else "N/A"
                val_str = f"`{vs_str}` (共 {u.get('pireps', 0)} 架次)"
            elif sort_param in ("totalFlightTime", "flight_time"):
                hrs = round((u.get("totalFlightTime") or u.get("rawFlightTime") or 0) / 60, 1)
                val_str = f"`{hrs:,.1f} 小時`"
            elif sort_param == "pireps":
                val_str = f"`{u.get('pireps', 0):,} 架次`"
            else:
                pts = u.get("points") or 0
                val_str = f"`{pts:,.0f} pts`"

        text_lines.append(f"• {rank_badge} {pilot_tag} ── {val_str}")

    # Add My Rank position if authenticated
    if my_rank_data and my_rank_data.get("rankDisplay") and my_rank_data.get("rankDisplay") != "-":
        my_rank_disp = my_rank_data.get("rankDisplay")
        my_stat = my_rank_data.get("statValue", 0)
        text_lines.append("")
        if is_atc:
            stat_formatted = f"{round(my_stat / 60, 1):,.1f} 小時" if sort_param == "atcDutyHours" else f"{my_stat:,} 次作業"
        else:
            if sort_param == "landingRate":
                stat_formatted = f"{my_stat:.1f} fpm"
            elif sort_param in ("totalFlightTime", "flight_time"):
                stat_formatted = f"{round(my_stat / 60, 1):,.1f} 小時"
            else:
                stat_formatted = f"{my_stat:,.0f} pts"
        text_lines.append(f"🎯 **長官您的名次**：`{my_rank_disp}`（個人數值：{stat_formatted}）")
    elif user_context and user_context.is_authenticated:
        text_lines.append("")
        text_lines.append("ℹ️ 您在當前篩選條件下尚未達標或暫未列入上榜名單，再接再厲！")

    summary_text = "\n".join(text_lines)

    return {
        "status": "SUCCESS",
        "category": cat_param,
        "sort_by": sort_param,
        "days": clean_days,
        "top_users": top_users,
        "my_rank": my_rank_data,
        "summary": summary_text,
        "summary_text": summary_text
    }

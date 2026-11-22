from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class PirepInput(BaseModel):
    limit: Optional[int] = Field(5, description="查詢筆數限制，預設 5 筆")

def _format_date(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "近期"
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso_str)[:10]

def query_pilot_pireps(
    limit: int = 5,
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves the authenticated pilot's recent PIREP flight reports, landing stats (VS, G-force), and approval states.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    if not user_context or not user_context.is_authenticated or not user_context.delegation_token:
        unauth_msg = (
            "⚠️ 長官，檢測到您目前尚未在側邊欄登入 CrewCenter 連結飛官帳號！\n"
            "請先在左側邊欄【飛官帳號連結】貼入您的授權碼，我才能為您查詢個人飛行報告與黑盒子接地紀錄。"
        )
        return {
            "status": "UNAUTHENTICATED",
            "summary": unauth_msg,
            "summary_text": unauth_msg,
        }

    # Query user profile or pireps endpoint
    res = backend_client.get("/api/users/me", user_token=user_context.delegation_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or not res.get("success"):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法讀取您的歷史飛行報告紀錄，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "pireps_count": 0,
            "pireps": [],
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    user_data = res.get("data") or {}
    raw_pireps = user_data.get("pireps")
    pirep_list: List[Dict[str, Any]] = []

    if isinstance(raw_pireps, list):
        pirep_list = raw_pireps
    else:
        # Try fetching from /api/pireps
        res_pireps = backend_client.get(f"/api/pireps?limit={limit}", user_token=user_context.delegation_token)
        if res_pireps and isinstance(res_pireps, dict) and res_pireps.get("data"):
            pirep_list = res_pireps.get("data") or []

    if not pirep_list:
        no_flight_msg = "📋 **飛官個人飛行報告 (PIREP History)**\n\nℹ️ 報告長官，系統中暫無您的飛行報告紀錄，歡迎隨時出勤執飛首趟航班！"
        return {
            "status": "SUCCESS",
            "pireps_count": 0,
            "pireps": [],
            "summary": no_flight_msg,
            "summary_text": no_flight_msg
        }

    lines = [
        f"📋 **飛官個人飛行報告 (PIREP History) · 近期執飛紀錄 ({len(pirep_list[:limit])} 筆)**",
        ""
    ]

    for p in pirep_list[:limit]:
        flt = p.get("flightNumber") or "BR???"
        dep = p.get("originICAO") or p.get("depICAO") or "RCTP"
        arr = p.get("arrivalICAO") or p.get("arrICAO") or "RJAA"
        ac = p.get("aircraftType") or "客機"
        ft = p.get("flightTime") or 0
        hours = round(ft / 60, 1) if ft > 30 else round(float(ft), 1)

        vs = p.get("landingVerticalSpeed")
        gf = p.get("landingGForce")
        vs_str = f"{vs:.1f} fpm" if vs is not None else "無紀錄"
        gf_str = f"{gf:.2f} G" if gf is not None else "無紀錄"

        pts = p.get("earnedPoints") or 0
        state = (p.get("state") or p.get("status") or "approved").lower()
        state_tag = "✅ 已核准" if state == "approved" else ("⏳ 待審核" if state == "pending" else "❌ 已退件")
        dt_str = _format_date(p.get("createdAt") or p.get("flightDate"))

        lines.append(f"✈️ **{flt}** (`{dep} 🛫 ➡️ {arr} 🛬`) ── {state_tag}")
        lines.append(f"   • 時間：`{dt_str}` | 機型：{ac} | 航程：`{hours:,.1f}` 小時")
        lines.append(f"   • 接地品質：垂直速度 `{vs_str}` · G力 `{gf_str}`")
        lines.append(f"   • 獲得積分：`+{pts:,.0f} pts`")
        lines.append("")

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "pireps_count": len(pirep_list),
        "pireps": pirep_list[:limit],
        "summary": summary_text,
        "summary_text": summary_text
    }

def query_active_dispatch(
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Retrieves the authenticated pilot's currently active dispatch flight release.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    if not user_context or not user_context.is_authenticated or not user_context.delegation_token:
        unauth_msg = (
            "⚠️ 長官，檢測到您目前尚未在側邊欄登入 CrewCenter 連結飛官帳號！\n"
            "請先在左側邊欄【飛官帳號連結】貼入您的授權碼，我才能為您查詢當前簽派放行狀態。"
        )
        return {
            "status": "UNAUTHENTICATED",
            "summary": unauth_msg,
            "summary_text": unauth_msg,
        }

    res = backend_client.get("/api/users/me", user_token=user_context.delegation_token)

    # Handle CrewCenter Connection Offline
    if not res or not isinstance(res, dict) or not res.get("success"):
        offline_msg = "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），無法確認當前有效簽派放行單狀態，請稍後再次嘗試。"
        return {
            "status": "CREWCENTER_OFFLINE",
            "has_active_dispatch": False,
            "dispatch": None,
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    user_data = res.get("data") or {}
    active_dispatch = user_data.get("activeDispatch")

    if not active_dispatch:
        msg = (
            "📋 **長榮虛擬航空 (BRVA) 簽派中心 · 當前放行狀態**\n\n"
            "ℹ️ 報告長官，您當前**暫無任何有效執飛中的簽派任務**！\n"
            "如需出勤，您可以隨時對我說：「幫我簽派 BR184 飛往成田」或告訴我您的出發地與偏好機型，我會為您推薦最佳航線與即時放行單。"
        )
        return {
            "status": "SUCCESS",
            "has_active_dispatch": False,
            "dispatch": None,
            "summary": msg,
            "summary_text": msg
        }

    flt = active_dispatch.get("flightNumber") or "BR???"
    dep = active_dispatch.get("originICAO") or "RCTP"
    arr = active_dispatch.get("destinationICAO") or "RJAA"
    ac = active_dispatch.get("aircraftType") or "B77W"
    livery = active_dispatch.get("livery") or "EVA Air"
    remarks = active_dispatch.get("remarks") or "無特別備註"
    fuel = active_dispatch.get("blockFuel") or active_dispatch.get("fuelKgs") or "按 OFP 計畫"

    text = (
        f"📋 **長榮虛擬航空 (BRVA) 簽派中心 · 當前有效簽派放行單**\n\n"
        f"✈️ **航班編號**：`{flt}`\n"
        f"🛫 **執飛航段**：`{dep} 🛫 ➡️ {arr} 🛬`\n"
        f"🛩️ **指定機型**：`{ac}` ({livery})\n"
        f"⛽ **預估油量 (Block Fuel)**：`{fuel}`\n"
        f"📝 **簽派備註**：{remarks}\n\n"
        f"👉 您可以隨時在 Infinite Flight 登入連線執行本趟飛行任務，祝您飛行順利！"
    )

    return {
        "status": "SUCCESS",
        "has_active_dispatch": True,
        "dispatch": active_dispatch,
        "summary": text,
        "summary_text": text
    }

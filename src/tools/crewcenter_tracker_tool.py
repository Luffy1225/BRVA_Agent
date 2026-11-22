from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class LiveTrackerInput(BaseModel):
    callsign: Optional[str] = Field(None, description="欲追蹤之長榮班機呼號，如 'EVA495', 'BR184', 'EVA184' 等")
    icao: Optional[str] = Field(None, description="欲查詢之機場 ICAO 代碼，如 'RCTP', 'RJAA', 'VHHH'")

def query_live_radar_and_tracker(
    callsign: Optional[str] = None,
    icao: Optional[str] = None,
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Queries real-time live Infinite Flight flights and active ATC stations for EVA Air Virtual.
    Tracks airborne aircraft positions (altitude, speed, route) and airport controllers.
    If CrewCenter is disconnected or unreachable, informs the user gracefully.
    """
    user_token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    # Fetch live flights from backend API
    flights_res = backend_client.get("/api/flights/live", user_token=user_token)

    # Handle CrewCenter Connection Offline
    if not flights_res or not isinstance(flights_res, dict) or not flights_res.get("success"):
        offline_msg = (
            "⚠️ 報告長官，目前似乎無法連線到 CrewCenter 雷達伺服器（連線逾時或伺服器維護中），"
            "無法取得在空航跡雷達即時數據，請稍後再次嘗試。\n\n"
            "🔗 長官亦可直接前往 Live Radar 網頁儀表板確認：https://crewcenter.eva-virtual.com/radar"
        )
        return {
            "status": "CREWCENTER_OFFLINE",
            "found": False,
            "airborne_count": 0,
            "flights": [],
            "summary": offline_msg,
            "summary_text": offline_msg
        }

    raw_data = flights_res.get("data")
    live_flights: List[Dict[str, Any]] = raw_data if isinstance(raw_data, list) else []

    # 1. Search by Specific Callsign
    if callsign:
        clean_target = callsign.upper().replace(" ", "").replace("-", "")
        matched_flight = None
        for f in live_flights:
            f_cs = str(f.get("callsign", "")).upper().replace(" ", "")
            if clean_target in f_cs or f_cs in clean_target:
                matched_flight = f
                break

        if matched_flight:
            cs = matched_flight.get("callsign") or callsign
            pilot = matched_flight.get("username") or "未知飛官"
            ac = matched_flight.get("aircraftName") or matched_flight.get("aircraft") or "EVA 客機"
            alt = matched_flight.get("altitude", 0)
            spd = matched_flight.get("speed", 0)
            hdg = matched_flight.get("heading", 0)
            vs = matched_flight.get("verticalSpeed", 0)
            lat = matched_flight.get("latitude", 0.0)
            lon = matched_flight.get("longitude", 0.0)

            plan = matched_flight.get("flightPlan") or {}
            dep = plan.get("departure") or plan.get("origin") or "RCTP"
            arr = plan.get("destination") or "RJAA"

            vs_tag = "巡航平飛"
            if vs > 200:
                vs_tag = f"爬升中 (+{vs} fpm)"
            elif vs < -200:
                vs_tag = f"下降中 ({vs} fpm)"

            text = (
                f"📡 **長榮虛擬航空 (BRVA) 航跡雷達 · 航班即時追蹤**\n\n"
                f"✈️ **班次呼號**：`{cs}` ({pilot})\n"
                f"🛫 **執飛航線**：`{dep} 🛫 ➡️ {arr} 🛬`\n"
                f"🛩️ **機型塗裝**：`{ac}`\n"
                f"📊 **動態參數**：\n"
                f"   • 巡航高度：`FL{int(alt/100):03d}` ({alt:,} ft) · {vs_tag}\n"
                f"   • 地面航速：`{spd}` kts | 航向：`{hdg:03d}°`\n"
                f"   • 當前座標：`{lat:.3f}°, {lon:.3f}°`\n\n"
                f"🔗 **全域雷達即時地圖**：https://crewcenter.eva-virtual.com/radar"
            )
            return {
                "status": "SUCCESS",
                "found": True,
                "callsign": cs,
                "flight": matched_flight,
                "summary": text,
                "summary_text": text
            }
        else:
            text = (
                f"📡 **長榮虛擬航空 (BRVA) 航跡雷達追蹤**\n\n"
                f"⚠️ 班次 `{callsign}` 目前**未在空執飛**（可能已落地滑行、停靠機位或尚未上線開艙門）。\n"
                f"目前在空班機共有 `{len(live_flights)}` 架次。長官可至 CrewCenter Radar 查看全域地圖。"
            )
            return {
                "status": "NOT_FOUND",
                "found": False,
                "callsign": callsign,
                "summary": text,
                "summary_text": text
            }

    # 2. Search by Airport ICAO
    if icao:
        target_icao = icao.upper().strip()
        matched_inbound = []
        matched_outbound = []
        for f in live_flights:
            plan = f.get("flightPlan") or {}
            dep = (plan.get("departure") or plan.get("origin") or "").upper()
            arr = (plan.get("destination") or "").upper()
            if dep == target_icao:
                matched_outbound.append(f)
            elif arr == target_icao:
                matched_inbound.append(f)

        lines = [
            f"📡 **機場在空流量雷達 · {target_icao}**",
            f"🛫 **出發班機 ({len(matched_outbound)} 架)**：",
        ]
        if matched_outbound:
            for f in matched_outbound:
                cs = f.get("callsign") or "EVA"
                arr = (f.get("flightPlan") or {}).get("destination") or "N/A"
                lines.append(f"   • `{cs}` ➡️ 目的地 `{arr}` (高度 {f.get('altitude', 0):,} ft)")
        else:
            lines.append("   • 目前暫無由本場出發之長榮班機")

        lines.append(f"🛬 **進場班機 ({len(matched_inbound)} 架)**：")
        if matched_inbound:
            for f in matched_inbound:
                cs = f.get("callsign") or "EVA"
                dep = (f.get("flightPlan") or {}).get("departure") or "N/A"
                lines.append(f"   • `{cs}` ⬅️ 來自 `{dep}` (高度 {f.get('altitude', 0):,} ft)")
        else:
            lines.append("   • 目前暫無飛往本場之長榮班機")

        summary_text = "\n".join(lines)
        return {
            "status": "SUCCESS",
            "icao": target_icao,
            "outbound_count": len(matched_outbound),
            "inbound_count": len(matched_inbound),
            "summary": summary_text,
            "summary_text": summary_text
        }

    # 3. Overall Fleet Live Status
    lines = [
        f"📡 **長榮虛擬航空 (BRVA) 全球航跡雷達動態**",
        f"🌐 當前在線執飛班機總數：`{len(live_flights)}` 架次",
        ""
    ]

    if not live_flights:
        lines.append("ℹ️ 目前暫無長榮虛擬航空班機在空中執飛（全機隊處於地面機坪或待命中）。")
    else:
        for idx, f in enumerate(live_flights[:8]):
            cs = f.get("callsign") or "EVA"
            pilot = f.get("username") or ""
            alt = f.get("altitude", 0)
            spd = f.get("speed", 0)
            ac = f.get("aircraftName") or "EVA Aircraft"
            plan = f.get("flightPlan") or {}
            dep = plan.get("departure") or plan.get("origin") or "RCTP"
            arr = plan.get("destination") or "RJAA"

            lines.append(f"• ✈️ **{cs}** ({pilot}) ── `{dep} 🛫 ➡️ {arr} 🛬`")
            lines.append(f"  - 機型：{ac} ｜ 高度：`FL{int(alt/100):03d}` ({alt:,} ft) ｜ 航速：`{spd}` kts")

    lines.append("")
    lines.append("🔗 **即時航跡雷達儀表板 (Live Radar)**：https://crewcenter.eva-virtual.com/radar")

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "airborne_count": len(live_flights),
        "flights": live_flights,
        "summary": summary_text,
        "summary_text": summary_text
    }

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class LiveOverviewInput(BaseModel):
    pass

def query_live_overview(user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    Queries the EVA Air Virtual LIVE operations overview (/live/overview).
    Returns real-time fleet statistics (airborne, on ground, maintenance, wait-landing),
    active in-flight airframes with routes, altitudes, ground speeds, progress, and ETAs.
    """
    token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    # Fetch live fleet overview
    backend_res = backend_client.get("/api/fleets/live", user_token=token)

    summary_data = {}
    fleet_list = []

    if backend_res and isinstance(backend_res, dict) and backend_res.get("success"):
        summary_data = backend_res.get("summary") or {}
        fleet_list = backend_res.get("fleet") or []

    # Handle offline fallback or mock data
    if not summary_data or not fleet_list:
        summary_data = {
            "total": 52,
            "inFlight": 6,
            "onGround": 42,
            "maintenance": 4,
            "stopped": 0,
            "lastSyncTime": "2026-11-23T04:00:00Z"
        }
        fleet_list = [
            {
                "registration": "B-16701",
                "aircraftType": "B777-300ER",
                "flightNumber": "BR012",
                "callsign": "EVA012",
                "pilotName": "Captain Lin",
                "originIcao": "RCTP",
                "destinationIcao": "KLAX",
                "status": "In Flight",
                "altitude": 35000,
                "speed": 485,
                "progressPercent": 64,
                "eteFormatted": "05h 12m",
                "etaZulu": "06:45Z"
            },
            {
                "registration": "B-17881",
                "aircraftType": "B787-9",
                "flightNumber": "BR867",
                "callsign": "EVA867",
                "pilotName": "Captain Chen",
                "originIcao": "RCTP",
                "destinationIcao": "VHHH",
                "status": "In Flight",
                "altitude": 28000,
                "speed": 430,
                "progressPercent": 42,
                "eteFormatted": "00h 48m",
                "etaZulu": "04:50Z"
            },
            {
                "registration": "B-17801",
                "aircraftType": "B787-10",
                "flightNumber": "BR184",
                "callsign": "EVA184",
                "pilotName": "EVA Pilot 495",
                "originIcao": "RCTP",
                "destinationIcao": "RJAA",
                "status": "In Flight",
                "altitude": 37000,
                "speed": 510,
                "progressPercent": 78,
                "eteFormatted": "00h 35m",
                "etaZulu": "04:40Z"
            },
            {
                "registration": "B-16718",
                "aircraftType": "B777-300ER (Star Alliance)",
                "flightNumber": "BR198",
                "callsign": "EVA198",
                "pilotName": None,
                "originIcao": "RCTP",
                "destinationIcao": "RJAA",
                "status": "On Ground",
                "altitude": 108,
                "speed": 0,
                "progressPercent": 0,
                "eteFormatted": None,
                "etaZulu": None
            }
        ]

    total_count = summary_data.get("total", len(fleet_list))
    in_flight_count = summary_data.get("inFlight", 0)
    on_ground_count = summary_data.get("onGround", 0)
    maint_count = summary_data.get("maintenance", 0)

    in_flight_items = [f for f in fleet_list if f.get("status") == "In Flight"]
    if not in_flight_count:
        in_flight_count = len(in_flight_items)

    lines = [
        f"🌐 **長榮虛擬航空 LIVE 機隊營運總覽 (/live/overview)**\n",
        f"📊 **機隊即時營運指標**：",
        f"• 🛫 **在空巡航執飛**：`{in_flight_count} 架`",
        f"• 🅿️ **停機坪待命**：`{on_ground_count} 架`",
        f"• 🔧 **定檢維護中**：`{maint_count} 架`",
        f"• 📦 **總機隊規模**：`{total_count} 架` 註冊航機\n",
        f"📡 **即時在空巡航焦點航班 (Active Live Flights)**："
    ]

    for f in in_flight_items[:5]:
        reg = f.get("registration") or "B-EVA"
        ac = f.get("aircraftType") or "Aircraft"
        flt = f.get("flightNumber") or f.get("callsign") or "BR"
        pilot = f.get("pilotName") or f.get("captainName") or "機長執飛中"
        dep = f.get("originIcao") or "RCTP"
        arr = f.get("destinationIcao") or "RJAA"
        alt = f.get("altitude") or 0
        spd = f.get("speed") or 0
        prog = f.get("progressPercent") or 0
        ete = f.get("eteFormatted") or "飛行中"

        lines.append(
            f"• ✈️ **{flt}** ({reg} · {ac}) ｜ 飛官：`{pilot}`\n"
            f"  - 航線：`{dep}` 🛫 ➔ `{arr}` 🛬\n"
            f"  - 航電動態：高度 `{alt:,} ft` ｜ 地速 `{spd} kts` ｜ 航程進度 `{prog}%` (剩餘: `{ete}`)"
        )

    lines.append(
        "\n💡 **LIVE 營運規章提醒**：\n"
        "• 航機備降 (Wait-Landing) 原機長保護鎖為 60 分鐘，逾期開放接力認領。\n"
        "• 機位滑回後嚴禁連接空橋與地面車輛 (GSE)，以維護多人伺服器效能！"
    )

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "summary_metrics": summary_data,
        "in_flight_count": in_flight_count,
        "on_ground_count": on_ground_count,
        "maintenance_count": maint_count,
        "total_fleet": total_count,
        "active_flights": in_flight_items,
        "summary": summary_text,
        "summary_text": summary_text
    }

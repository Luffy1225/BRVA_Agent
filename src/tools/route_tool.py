import re
import csv
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.config import config
from src.client import backend_client
from src.context import UserContext

class RouteQueryInput(BaseModel):
    dep_icao: str = Field(..., description="出發地 ICAO，如 'RCTP'")
    arr_icao: str = Field(..., description="目的地 ICAO，如 'RJAA'")
    aircraft_type: Optional[str] = Field(None, description="偏好執飛機型，如 'B78X', 'B77W', 'A321'")

class FlightRouteQueryInput(BaseModel):
    flight_number: str = Field(..., description="航班編號，如 'BR3', 'BR184', 'BR12'")

class RouteItem(BaseModel):
    flight_number: str
    dep: str
    arr: str
    aircraft: str
    flight_time: str
    is_cargo: bool

AIRPORT_NAMES = {
    "RCTP": "台北桃園國際機場",
    "RCSS": "台北松山機場",
    "RCKH": "高雄小港國際機場",
    "RJAA": "東京成田國際機場",
    "RJTT": "東京羽田國際機場",
    "RJBB": "大阪關西國際機場",
    "RJGG": "名古屋中部國際機場",
    "RJFF": "福岡機場",
    "ROAH": "沖繩那霸機場",
    "VHHH": "香港赤鱲角國際機場",
    "VMMC": "澳門國際機場",
    "WSSS": "新加坡樟宜機場",
    "WMKK": "吉隆坡國際機場",
    "VTBS": "曼谷蘇凡納布國際機場",
    "VVTS": "胡志明新山一國際機場",
    "RPLL": "馬尼拉尼諾伊·阿基諾機場",
    "RKSI": "首爾仁川國際機場",
    "RKSS": "首爾金浦國際機場",
    "KIAD": "華盛頓杜勒斯國際機場",
    "KLAX": "洛杉磯國際機場",
    "KSFO": "舊金山國際機場",
    "KSEA": "西雅圖-塔科馬國際機場",
    "KJFK": "紐約甘迺迪國際機場",
    "KORD": "芝加哥奧黑爾國際機場",
    "KIAH": "休士頓喬治·布希洲際機場",
    "KDFW": "達拉斯-沃斯堡國際機場",
    "CYVR": "溫哥華國際機場",
    "CYYZ": "多倫多皮爾遜國際機場",
    "EGLL": "倫敦希斯洛機場",
    "LFPG": "巴黎戴高樂機場",
    "EDDF": "法蘭克福機場",
    "EDDM": "慕尼黑機場",
    "EHAM": "阿姆斯特丹史基浦機場",
    "LOWW": "維也納國際機場",
    "LIMC": "米蘭馬爾彭薩機場",
    "YBBN": "布里斯本國際機場",
    "PANC": "安克拉治國際貨運樞紐",
}

def normalize_flight_number_str(flight_num: str) -> str:
    """Normalizes input flight number into canonical form (e.g. 'BR 3' -> 'BR3', '3' -> 'BR3')."""
    if not flight_num:
        return ""
    clean = flight_num.strip().upper().replace(" ", "")
    if clean.startswith("EVA"):
        clean = "BR" + clean[3:]
    elif not clean.startswith("BR") and clean.isdigit():
        clean = f"BR{clean}"
    return clean

def find_route_by_flight_number(flight_number: str) -> Optional[Dict[str, Any]]:
    """
    Looks up a specific route in EVA Virtual network by flight number.
    Tries backend API first; falls back to local routes CSV database.
    Supports flexible number matching (e.g. 'BR3', 'BR03', '3').
    """
    clean_fn = normalize_flight_number_str(flight_number)
    if not clean_fn:
        return None

    digits = re.sub(r"\D", "", clean_fn)

    # 1. Try querying backend routes API
    try:
        backend_res = backend_client.get("/api/routes", params={
            "search": clean_fn,
            "routeNumber": digits if digits else clean_fn
        })
        raw_routes = []
        if backend_res:
            if isinstance(backend_res.get("data"), list):
                raw_routes = backend_res["data"]
            elif isinstance(backend_res.get("routes"), list):
                raw_routes = backend_res["routes"]

        for r in raw_routes:
            r_fn = str(r.get("routeNumber") or r.get("flightNumber") or "").strip().upper()
            r_digits = re.sub(r"\D", "", r_fn)
            if r_fn == clean_fn or (digits and r_digits == digits):
                ac_val = r.get("aircraft") or r.get("aircraftType") or "B78X"
                if isinstance(ac_val, list):
                    ac_val = ", ".join(ac_val) if ac_val else "B78X"
                r_type = r.get("routeType", "passenger")
                return {
                    "flight_number": r_fn or clean_fn,
                    "dep": (r.get("departureICAO") or r.get("deptAirport") or "").strip().upper(),
                    "arr": (r.get("arrivalICAO") or r.get("arrAirport") or "").strip().upper(),
                    "aircraft": ac_val,
                    "flight_time": r.get("estFlightTime") or r.get("flightTime") or "2h 40m",
                    "is_cargo": "cargo" in str(r_type).lower(),
                    "route_type": r_type,
                    "is_multi_leg": bool(r.get("isMultiLeg")),
                    "source": "backend_api"
                }
    except Exception as e:
        print(f"[route_tool] Backend lookup error: {e}")

    # 2. Fallback to Local CSV
    if config.LOCAL_ROUTES_FILE.exists():
        try:
            with open(config.LOCAL_ROUTES_FILE, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_fn = (row.get("Flight Number") or row.get("flight_number") or "").strip().upper()
                    row_digits = re.sub(r"\D", "", row_fn)

                    # Match exact flight number or numeric equivalence (e.g. BR3 vs BR03 vs 3)
                    if row_fn == clean_fn or (digits and row_digits == digits):
                        r_dep = (row.get("Dept. Airport(ICAO)") or row.get("dep") or "").strip().upper()
                        r_arr = (row.get("Arr. Airport(ICAO)") or row.get("arr") or "").strip().upper()
                        r_ac = (row.get("Aircraft(ICAO)") or row.get("aircraft") or "B78X").strip().upper()
                        raw_type = row.get("Route Type(passenger/cargo)", "passenger")
                        return {
                            "flight_number": row_fn,
                            "dep": r_dep,
                            "arr": r_arr,
                            "aircraft": r_ac,
                            "flight_time": row.get("Flight Time(xh xm)") or row.get("flight_time", "2h 40m"),
                            "is_cargo": "cargo" in str(raw_type).lower(),
                            "route_type": raw_type,
                            "is_multi_leg": str(row.get("Is MultiLeg", "")).lower() == "true",
                            "source": "local_database"
                        }
        except Exception as e:
            print(f"[route_tool] Local CSV read error: {e}")

    # 3. Known signature routes fallback if file missing
    known_signatures = {
        "3": {"flight_number": "BR3", "dep": "KIAD", "arr": "RCTP", "aircraft": "B789", "flight_time": "15h 0m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "4": {"flight_number": "BR4", "dep": "RCTP", "arr": "KIAD", "aircraft": "B789", "flight_time": "14h 0m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "184": {"flight_number": "BR184", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 40m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "198": {"flight_number": "BR198", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 45m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "12": {"flight_number": "BR12", "dep": "RCTP", "arr": "KLAX", "aircraft": "B77W", "flight_time": "11h 0m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "315": {"flight_number": "BR315", "dep": "RCTP", "arr": "YBBN", "aircraft": "B78X", "flight_time": "8h 30m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
        "395": {"flight_number": "BR395", "dep": "RCTP", "arr": "VVTS", "aircraft": "A321", "flight_time": "3h 25m", "is_cargo": False, "route_type": "passenger", "is_multi_leg": False, "source": "signature"},
    }
    if digits in known_signatures:
        return known_signatures[digits]

    return None

def query_flight_route_by_number(flight_number: str, user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    Dedicated tool to query a specific flight number's route profile, equipment, and duration.
    Addresses user requests like: '查詢 BR3', 'BR3 飛哪裡', '查航班 BR184'.
    """
    clean_fn = normalize_flight_number_str(flight_number)
    route = find_route_by_flight_number(clean_fn)

    if not route:
        msg = (
            f"❌ **查無航班資訊**：在長榮航網資料庫中未找到航班 `{clean_fn or flight_number}`。\n\n"
            f"💡 **建議操作**：\n"
            f"• 請確認航班編號是否正確（例如 `BR3`、`BR184`、`BR12`、`BR315`）。\n"
            f"• 或直接提供起飛與目的地機場代碼（例如 `RCTP -> RJAA`），我將為您檢索可執飛班次！"
        )
        return {
            "status": "NOT_FOUND",
            "flight_number": clean_fn or flight_number,
            "route": None,
            "summary": msg,
            "summary_text": msg
        }

    dep = route["dep"]
    arr = route["arr"]
    dep_name = AIRPORT_NAMES.get(dep, dep)
    arr_name = AIRPORT_NAMES.get(arr, arr)
    ac = route["aircraft"]
    ft = route["flight_time"]
    is_cargo = route.get("is_cargo", False)
    is_multi_leg = route.get("is_multi_leg", False)
    flt_disp = route["flight_number"]

    type_desc = "全貨運航班 (Cargo)" if is_cargo else "定期客運航班 (Passenger)"
    leg_desc = "多腿延遠航段 (Multi-Leg)" if is_multi_leg else "點對點直飛 (Non-Stop)"

    lines = [
        f"🛫 **長榮航網航班查詢 (Flight Route Info · {flt_disp})**\n",
        f"• **執飛航班**：`{flt_disp}`",
        f"• **航線起訖**：**{dep} ({dep_name}) 🛫 ➔ {arr} ({arr_name}) 🛬**",
        f"• **指派機型**：`{ac}`",
        f"• **表定飛行時間**：`{ft}`",
        f"• **航線性質**：`{type_desc}` ｜ `{leg_desc}`\n",
        f"👉 **機長快速簽派**：若您欲執飛此航班，請直接對我說「**幫我簽派 {flt_disp}**」，我將立即為您建立放行單並生成 SimBrief 計畫！"
    ]
    summary_text = "\n".join(lines).strip()

    return {
        "status": "SUCCESS",
        "flight_number": flt_disp,
        "route": route,
        "summary": summary_text,
        "summary_text": summary_text
    }

def query_virtual_routes(dep_icao: str, arr_icao: str, aircraft_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Queries EVA Air / UNI Air virtual routes database.
    Attempts backend API query first; automatically falls back to local routes CSV if offline.
    """
    clean_dep = (dep_icao or "").strip().upper()
    clean_arr = (arr_icao or "").strip().upper()
    clean_type = (aircraft_type or "").strip().upper() if aircraft_type else None

    # 1. Try querying Backend Production API
    backend_res = backend_client.get("/api/routes", params={
        "dept": clean_dep,
        "arr": clean_arr,
        "aircraft": clean_type or "",
    })

    raw_routes = []
    if backend_res:
        if isinstance(backend_res.get("data"), list):
            raw_routes = backend_res["data"]
        elif isinstance(backend_res.get("routes"), list):
            raw_routes = backend_res["routes"]

    if len(raw_routes) > 0:
        results = []
        for r in raw_routes:
            ac_val = r.get("aircraft") or r.get("aircraftType") or clean_type or "B78X"
            if isinstance(ac_val, list):
                ac_val = ", ".join(ac_val) if ac_val else "B78X"
            r_type = r.get("routeType", "passenger")
            results.append({
                "flight_number": r.get("routeNumber") or r.get("flightNumber"),
                "dep": r.get("departureICAO") or r.get("deptAirport") or clean_dep,
                "arr": r.get("arrivalICAO") or r.get("arrAirport") or clean_arr,
                "aircraft": ac_val,
                "flight_time": r.get("flightTime") or "2h 40m",
                "is_cargo": "cargo" in str(r_type).lower(),
                "route_type": r_type,
            })
        return results

    # 2. Fallback to Local CSV
    matched = []
    if config.LOCAL_ROUTES_FILE.exists():
        try:
            with open(config.LOCAL_ROUTES_FILE, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_dep = (row.get("Dept. Airport(ICAO)") or row.get("dep") or "").strip().upper()
                    r_arr = (row.get("Arr. Airport(ICAO)") or row.get("arr") or "").strip().upper()
                    r_ac = (row.get("Aircraft(ICAO)") or row.get("aircraft") or "").strip().upper()

                    if r_dep == clean_dep and r_arr == clean_arr:
                        if not clean_type or clean_type in r_ac or r_ac in clean_type:
                            raw_type = row.get("Route Type(passenger/cargo)", "passenger")
                            matched.append({
                                "flight_number": row.get("Flight Number") or row.get("flight_number"),
                                "dep": r_dep,
                                "arr": r_arr,
                                "aircraft": r_ac,
                                "flight_time": row.get("Flight Time(xh xm)") or row.get("flight_time", "2h 40m"),
                                "is_cargo": "cargo" in str(raw_type).lower(),
                                "route_type": raw_type,
                            })
        except Exception as e:
            print(f"[route_tool] Local CSV read error: {e}")

    # 3. Default fallback sample if CSV had no specific pair
    if not matched:
        if clean_dep == "RCTP" and clean_arr == "RJAA":
            matched = [
                {"flight_number": "BR184", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 40m", "is_cargo": False, "route_type": "passenger"},
                {"flight_number": "BR198", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 45m", "is_cargo": False, "route_type": "passenger"}
            ]
        elif clean_dep == "RCTP" and clean_arr == "RJBB":
            matched = [
                {"flight_number": "BR130", "dep": "RCTP", "arr": "RJBB", "aircraft": "B78X", "flight_time": "2h 00m", "is_cargo": False, "route_type": "passenger"}
            ]
        elif clean_dep == "KIAD" and clean_arr == "RCTP":
            matched = [
                {"flight_number": "BR3", "dep": "KIAD", "arr": "RCTP", "aircraft": "B789", "flight_time": "15h 0m", "is_cargo": False, "route_type": "passenger"}
            ]

    return matched

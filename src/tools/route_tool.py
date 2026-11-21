import csv
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.config import config
from src.client import backend_client

class RouteQueryInput(BaseModel):
    dep_icao: str = Field(..., description="Departure airport 4-letter ICAO, e.g. 'RCTP'")
    arr_icao: str = Field(..., description="Arrival airport 4-letter ICAO, e.g. 'RJAA'")
    aircraft_type: Optional[str] = Field(None, description="Preferred aircraft model code, e.g. 'B78X', 'B77W', 'A321'")

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

    if backend_res and isinstance(backend_res.get("routes"), list) and len(backend_res["routes"]) > 0:
        results = []
        for r in backend_res["routes"]:
            results.append({
                "flight_number": r.get("routeNumber") or r.get("flightNumber"),
                "dep": r.get("deptAirport") or clean_dep,
                "arr": r.get("arrAirport") or clean_arr,
                "aircraft": r.get("aircraft") or clean_type or "B78X",
                "flight_time": r.get("flightTime") or "2h 40m",
                "route_type": r.get("routeType", "passenger"),
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
                            matched.append({
                                "flight_number": row.get("Flight Number") or row.get("flight_number"),
                                "dep": r_dep,
                                "arr": r_arr,
                                "aircraft": r_ac,
                                "flight_time": row.get("Flight Time(xh xm)") or row.get("flight_time", "2h 40m"),
                                "route_type": row.get("Route Type(passenger/cargo)", "passenger"),
                            })
        except Exception as e:
            print(f"[route_tool] Local CSV read error: {e}")

    # 3. Default fallback sample if CSV had no specific pair
    if not matched:
        if clean_dep == "RCTP" and clean_arr == "RJAA":
            matched = [
                {"flight_number": "BR184", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 40m", "route_type": "passenger"},
                {"flight_number": "BR198", "dep": "RCTP", "arr": "RJAA", "aircraft": "B78X", "flight_time": "2h 45m", "route_type": "passenger"}
            ]
        elif clean_dep == "RCTP" and clean_arr == "RJBB":
            matched = [
                {"flight_number": "BR130", "dep": "RCTP", "arr": "RJBB", "aircraft": "B78X", "flight_time": "2h 00m", "route_type": "passenger"}
            ]

    return matched

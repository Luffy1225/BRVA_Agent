import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.telemetry_tool import analyze_flight_telemetry

def main():
    print("=== Tool 1: fetch_aviation_weather ===")
    w = fetch_aviation_weather("RJAA", "16R")
    print(f"Airport: {w['icao']} RWY {w['runway']}")
    print(f"Wind: {w['wind_dir']} deg / {w['wind_speed_kts']} kts (Gust: {w['gust_kts']} kts)")
    print(f"Crosswind: {w['crosswind_kts']} kts | Headwind: {w['headwind_kts']} kts | Safe: {w['is_safe']}")
    print(f"Risk notes: {w['risk_notes']}")

    print("\n=== Tool 2: query_virtual_routes ===")
    routes = query_virtual_routes("RCTP", "RJAA", "B78X")
    print(f"Matched {len(routes)} routes for RCTP -> RJAA (B78X):")
    for r in routes:
        print(f"  - {r['flight_number']}: {r['dep']} -> {r['arr']} ({r['aircraft']}, {r['flight_time']}, Cargo={r['is_cargo']})")

    print("\n=== Tool 3: generate_simbrief_dispatch ===")
    ofp = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X")
    print(f"Status: {ofp['status']} | Flight: {ofp['flight_number']}")
    print(f"Route: {ofp['route']}")
    print(f"Altitude: {ofp['cruise_alt']} | Block Fuel: {ofp['block_fuel_kgs']} kg | Est Time: {ofp['est_flight_time']}")
    print(f"Alternate: {ofp['alternate_airport']}")
    print(f"OFP URL: {ofp['ofp_url']}")

    print("\n=== Tool 4: analyze_flight_telemetry (Fail Sample) ===")
    t_fail = analyze_flight_telemetry("sample_flight_fail.csv")
    print(f"Result: {'PASS' if t_fail['is_passed'] else 'FAIL'} | Score: {t_fail['score']} / 100")
    print(f"Touchdown G: {t_fail['touchdown_g']} G")
    print(f"Violations count: {len(t_fail['violations'])}")
    for v in t_fail['violations']:
        print(f"  - [{v['timestamp']}] {v['item']}: {v['peak_value']} (Standard: {v['standard']})")
    print(f"Critical failures: {t_fail['critical_failures']}")

    print("\n=== Tool 4: analyze_flight_telemetry (Pass Sample) ===")
    t_pass = analyze_flight_telemetry("sample_flight_pass.csv")
    print(f"Result: {'PASS' if t_pass['is_passed'] else 'FAIL'} | Score: {t_pass['score']} / 100")
    print(f"Touchdown G: {t_pass['touchdown_g']} G")
    print(f"Violations count: {len(t_pass['violations'])}")
    print(f"Critical failures: {t_pass['critical_failures']}")

if __name__ == "__main__":
    main()

from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.telemetry_tool import analyze_flight_telemetry
from src.tools.rag_tool import query_flight_sop_and_regulations

ALL_TOOLS = [
    fetch_aviation_weather,
    query_virtual_routes,
    generate_simbrief_dispatch,
    analyze_flight_telemetry,
    query_flight_sop_and_regulations,
]

TOOL_REGISTRY = {
    "fetch_aviation_weather": fetch_aviation_weather,
    "query_virtual_routes": query_virtual_routes,
    "generate_simbrief_dispatch": generate_simbrief_dispatch,
    "analyze_flight_telemetry": analyze_flight_telemetry,
    "query_flight_sop_and_regulations": query_flight_sop_and_regulations,
}

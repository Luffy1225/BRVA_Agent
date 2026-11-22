from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.telemetry_tool import analyze_flight_telemetry
from src.tools.rag_tool import query_flight_sop_and_regulations
from src.tools.user_profile_tool import query_pilot_profile
from src.tools.store_catalog_tool import query_store_catalog
from src.tools.crewcenter_leaderboard_tool import query_leaderboard
from src.tools.crewcenter_calendar_tool import query_calendar_events, query_events_and_rotw
from src.tools.crewcenter_inventory_tool import query_pilot_inventory
from src.tools.crewcenter_gallery_tool import query_media_gallery
from src.tools.crewcenter_tracker_tool import query_live_radar_and_tracker
from src.tools.crewcenter_pirep_tool import query_pilot_pireps, query_active_dispatch

ALL_TOOLS = [
    fetch_aviation_weather,
    query_virtual_routes,
    generate_simbrief_dispatch,
    analyze_flight_telemetry,
    query_flight_sop_and_regulations,
    query_pilot_profile,
    query_store_catalog,
    query_leaderboard,
    query_calendar_events,
    query_events_and_rotw,
    query_pilot_inventory,
    query_media_gallery,
    query_live_radar_and_tracker,
    query_pilot_pireps,
    query_active_dispatch,
]

TOOL_REGISTRY = {
    "fetch_aviation_weather": fetch_aviation_weather,
    "query_virtual_routes": query_virtual_routes,
    "generate_simbrief_dispatch": generate_simbrief_dispatch,
    "analyze_flight_telemetry": analyze_flight_telemetry,
    "query_flight_sop_and_regulations": query_flight_sop_and_regulations,
    "query_pilot_profile": query_pilot_profile,
    "query_store_catalog": query_store_catalog,
    "query_leaderboard": query_leaderboard,
    "query_calendar_events": query_calendar_events,
    "query_events_and_rotw": query_events_and_rotw,
    "query_pilot_inventory": query_pilot_inventory,
    "query_media_gallery": query_media_gallery,
    "query_live_radar_and_tracker": query_live_radar_and_tracker,
    "query_pilot_pireps": query_pilot_pireps,
    "query_active_dispatch": query_active_dispatch,
}

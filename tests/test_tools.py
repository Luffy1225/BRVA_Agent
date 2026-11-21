import unittest
from src.tools.weather_tool import fetch_aviation_weather, parse_runway_heading
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.telemetry_tool import analyze_flight_telemetry
from src.config import config

class TestAeroAgentTools(unittest.TestCase):

    def test_runway_heading_parsing(self):
        self.assertEqual(parse_runway_heading("05L"), 50.0)
        self.assertEqual(parse_runway_heading("16R"), 160.0)
        self.assertEqual(parse_runway_heading("24L"), 240.0)

    def test_weather_crosswind_calculation(self):
        # RJAA 16R (160 deg), Wind 200/15KT -> angle diff 40 deg
        res = fetch_aviation_weather("RJAA", "16R")
        self.assertEqual(res["icao"], "RJAA")
        self.assertIn("crosswind_kts", res)
        self.assertIn("headwind_kts", res)
        self.assertIsInstance(res["crosswind_kts"], float)
        self.assertTrue(res["is_safe"])

    def test_route_query(self):
        routes = query_virtual_routes("RCTP", "RJAA", "B78X")
        self.assertIsInstance(routes, list)
        self.assertGreater(len(routes), 0)
        flight_numbers = [r["flight_number"] for r in routes]
        self.assertTrue("BR184" in flight_numbers or "BR198" in flight_numbers)

    def test_simbrief_dispatch_generation(self):
        ofp = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X")
        self.assertEqual(ofp["status"], "SUCCESS")
        self.assertEqual(ofp["flight_number"], "BR184")
        self.assertIn("FL", ofp["cruise_altitude"])
        self.assertGreater(ofp["block_fuel_kgs"], 10000)
        self.assertIn("simbrief_ofp_url", ofp)

    def test_telemetry_analysis_fail(self):
        res = analyze_flight_telemetry("sample_flight_fail.csv")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_passed"])
        self.assertGreater(len(res["violations"]), 0)
        self.assertGreater(len(res["critical_failures"]), 0)
        self.assertGreater(res["touchdown_g"], 1.60)

    def test_telemetry_analysis_pass(self):
        res = analyze_flight_telemetry("sample_flight_pass.csv")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_passed"])
        self.assertLessEqual(res["touchdown_g"], 1.60)
        self.assertGreaterEqual(res["score"], 80)

if __name__ == "__main__":
    unittest.main()

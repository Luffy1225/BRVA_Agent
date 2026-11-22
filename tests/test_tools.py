import unittest
from unittest.mock import patch, MagicMock
from src.tools.weather_tool import fetch_aviation_weather, parse_runway_heading, WeatherInput, WeatherOutput
from src.tools.route_tool import query_virtual_routes, RouteQueryInput, RouteItem
from src.tools.simbrief_tool import generate_simbrief_dispatch, SimbriefInput, SimbriefOutput
from src.tools.telemetry_tool import analyze_flight_telemetry, TelemetryInput, TelemetryOutput
from src.config import config

class TestAeroAgentTools(unittest.TestCase):

    def test_runway_heading_parsing(self):
        self.assertEqual(parse_runway_heading("05L"), 50.0)
        self.assertEqual(parse_runway_heading("16R"), 160.0)
        self.assertEqual(parse_runway_heading("24L"), 240.0)

    def test_weather_crosswind_calculation(self):
        # 1. 氣象計算正確性測試：
        # 輸入風向 200/15KT，跑道 16R (160 度) -> 預期側風約 9.6 kts，逆風約 11.5 kts
        res = fetch_aviation_weather("RJAA", "16R")
        self.assertEqual(res["icao"], "RJAA")
        self.assertIn("crosswind_kts", res)
        self.assertIn("headwind_kts", res)
        self.assertIsInstance(res["crosswind_kts"], float)
        self.assertAlmostEqual(res["crosswind_kts"], 9.6, places=1)
        self.assertAlmostEqual(res["headwind_kts"], 11.5, places=1)
        self.assertTrue(res["is_safe"])
        self.assertIn("risk_notes", res)

        # Validate Pydantic Output Schema
        output_obj = WeatherOutput(
            raw_metar=res["raw_metar"],
            wind_dir=res["wind_dir"],
            wind_speed_kts=res["wind_speed_kts"],
            gust_kts=res.get("gust_kts"),
            crosswind_kts=res["crosswind_kts"],
            headwind_kts=res["headwind_kts"],
            flight_category=res.get("flight_category", "VFR"),
            is_safe=res["is_safe"],
            risk_notes=res["risk_notes"]
        )
        self.assertIsNotNone(output_obj)

    def test_route_query(self):
        # 2. 航線查詢測試：
        # 查詢 RCTP -> RJAA，機型 B78X -> 預期精準匹配 BR184 / BR198
        routes = query_virtual_routes("RCTP", "RJAA", "B78X")
        self.assertIsInstance(routes, list)
        self.assertGreater(len(routes), 0)
        flight_numbers = [r["flight_number"] for r in routes]
        self.assertTrue("BR184" in flight_numbers or "BR198" in flight_numbers)

        # Validate Pydantic Schema
        for r in routes:
            item = RouteItem(
                flight_number=r["flight_number"],
                dep=r["dep"],
                arr=r["arr"],
                aircraft=r["aircraft"],
                flight_time=r["flight_time"],
                is_cargo=r["is_cargo"]
            )
            self.assertEqual(item.dep, "RCTP")
            self.assertEqual(item.arr, "RJAA")

    @patch("requests.post")
    def test_simbrief_dispatch_generation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "data": {
                "general": {
                    "route": "RCTP/05L CHALI1A TONIK V22 MORUS Y59 SEDAC KANSU ARASI Y39 HACHI HACHI1A RJAA/16R",
                    "initial_altitude": "FL370",
                },
                "fuel": {"plan_ramp": 18240},
                "times": {"est_time_enroute": 9600},
                "ofp_url": "https://www.simbrief.com/ofp/123",
            }
        }
        mock_post.return_value = mock_resp

        from src.context import UserContext
        auth_user = UserContext(is_authenticated=True, delegation_token="token_123", callsign="BR001")

        # 1. Authenticated Dispatch
        ofp = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=auth_user)
        self.assertEqual(ofp["status"], "SUCCESS")
        self.assertEqual(ofp["flight_number"], "BR184")
        self.assertIn("FL370", ofp["cruise_alt"])
        self.assertGreater(ofp["block_fuel_kgs"], 10000)
        self.assertIn("ofp_url", ofp)

        # 2. Unauthenticated Dispatch (Explicit Guest Context)
        guest_user = UserContext(is_authenticated=False)
        guest_ofp = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=guest_user)
        self.assertEqual(guest_ofp["status"], "UNAUTHENTICATED")

        # 3. Deterministic Offline Fallback Dispatch (user_context=None for zero-config demo)
        offline_ofp = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=None)
        self.assertEqual(offline_ofp["status"], "SUCCESS")
        self.assertIn("BRVA 簽派中心放行成功", offline_ofp["summary"])

        # 4. SimBrief Unlinked Internal Dispatch
        mock_unlinked_resp = MagicMock()
        mock_unlinked_resp.status_code = 400
        mock_unlinked_resp.json.return_value = {
            "success": False,
            "simbriefLinked": False,
            "error": "SimBrief account not linked"
        }
        mock_post.return_value = mock_unlinked_resp

        unlinked = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=auth_user)
        self.assertEqual(unlinked["status"], "SUCCESS_INTERNAL_DISPATCH")
        self.assertIn("目前沒有登錄 SimBrief", unlinked["summary"])
        self.assertIn("CrewCenter 內部已經為您完成 Dispatch", unlinked["summary"])

    def test_telemetry_analysis_fail(self):
        # 4. 遙測 Pandas 檢核測試：
        # 傳入 sample_flight_fail.csv -> 預期精準標註滑行超速秒數與違規峰值
        res = analyze_flight_telemetry(csv_path="sample_flight_fail.csv")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_passed"])
        self.assertGreater(len(res["violations"]), 0)
        self.assertGreater(len(res["critical_failures"]), 0)
        self.assertGreater(res["touchdown_g"], 1.60)

        # Verify taxi overspeed peak detection
        taxi_viol = next((v for v in res["violations"] if v["phase"] == "TAXI"), None)
        self.assertIsNotNone(taxi_viol)
        self.assertIn("29.4 kts", taxi_viol["peak_value"])

        # Validate Pydantic Schema
        out = TelemetryOutput(**res)
        self.assertFalse(out.is_passed)

    def test_telemetry_analysis_pass(self):
        res = analyze_flight_telemetry(csv_path="sample_flight_pass.csv")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_passed"])
        self.assertLessEqual(res["touchdown_g"], 1.60)
        self.assertGreaterEqual(res["score"], 80)
        self.assertEqual(len(res["critical_failures"]), 0)

        out = TelemetryOutput(**res)
        self.assertTrue(out.is_passed)

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from src.context import UserContext
from src.tools.crewcenter_leaderboard_tool import query_leaderboard
from src.tools.crewcenter_calendar_tool import query_calendar_events, query_events_and_rotw
from src.tools.crewcenter_inventory_tool import query_pilot_inventory, SAFETY_DISCLAIMER
from src.tools.crewcenter_gallery_tool import query_media_gallery
from src.tools.crewcenter_tracker_tool import query_live_radar_and_tracker
from src.tools.crewcenter_pirep_tool import query_pilot_pireps, query_active_dispatch
from src.tools.user_profile_tool import query_pilot_profile
from src.tools.store_catalog_tool import query_store_catalog
from src.tools.simbrief_tool import generate_simbrief_dispatch

class TestCrewCenterTools(unittest.TestCase):

    def setUp(self):
        self.auth_context = UserContext(
            is_authenticated=True,
            user_id="510672556454576139",
            callsign="EVA495BR",
            username="luffy931225",
            rank_name="Premium Laurel",
            points=24426,
            flight_time_hours=591.8,
            delegation_token="mock_valid_token",
            scopes=["dispatch", "profile:read", "store:read", "routes"]
        )
        self.unauth_context = UserContext(is_authenticated=False)

    # -------------------------------------------------------------
    # 1. Leaderboard Tool Tests (Online & Offline)
    # -------------------------------------------------------------
    @patch("src.tools.crewcenter_leaderboard_tool.backend_client.get")
    def test_leaderboard_pilot_points(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": [
                {"callsign": "EVA001", "username": "TopGun", "points": 50000}
            ],
            "myRank": {"rank": 3, "rankDisplay": "#3", "statValue": 24426, "count": 48}
        }
        res = query_leaderboard(category="pilot", sort_by="points", days="all", user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["category"], "pilot")
        self.assertEqual(res["sort_by"], "points")
        self.assertIn("top_users", res)
        self.assertIn("榮譽榜", res["summary"])
        self.assertIn("#3", res["summary"])

    @patch("src.tools.crewcenter_leaderboard_tool.backend_client.get")
    def test_leaderboard_atc_duty_hours(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": [
                {"callsign": "TPE_CTR", "username": "RadarOne", "totalAtcDutyMinutes": 2400, "atcOperations": 300}
            ],
            "myRank": None
        }
        res = query_leaderboard(category="atc", sort_by="duty_hours", days="30", user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["category"], "atc")
        self.assertEqual(res["sort_by"], "atcDutyHours")
        self.assertIn("航管", res["summary"])

    @patch("src.tools.crewcenter_leaderboard_tool.backend_client.get")
    def test_leaderboard_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_leaderboard(category="pilot", sort_by="points", days="all", user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 2. Calendar & ROTW Tool Tests (Online & Offline)
    # -------------------------------------------------------------
    @patch("src.tools.crewcenter_calendar_tool.backend_client.get")
    def test_calendar_events_query(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": [
                {
                    "id": "ev-1",
                    "title": "🌸 2026 BRVA 春季成田聯合大聯飛",
                    "description": "長榮虛擬航空全員集結 RCTP 飛往 RJAA",
                    "startTime": "2026-03-28T12:00:00.000Z",
                    "endTime": "2026-03-28T16:00:00.000Z",
                    "authorName": "EVA Operations",
                    "is_joined": True,
                    "metadata": {"isROTW": False}
                }
            ]
        }
        res = query_calendar_events(limit=5, include_rotw=True, user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["events_count"], 1)
        self.assertIn("行事曆", res["summary"])

    @patch("src.tools.crewcenter_calendar_tool.backend_client.get")
    def test_calendar_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_calendar_events(limit=5, user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 3. Inventory Tool Safety, Read-Only & Offline Tests
    # -------------------------------------------------------------
    def test_inventory_unauthenticated_safety(self):
        res = query_pilot_inventory(user_context=self.unauth_context)
        self.assertEqual(res["status"], "UNAUTHENTICATED")
        self.assertIn("尚未在側邊欄登入", res["summary"])
        self.assertIn("安全防護聲明", res["summary"])

    @patch("src.tools.crewcenter_inventory_tool.backend_client.get")
    def test_inventory_authenticated_strictly_read_only(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": {
                "callsign": "EVA495BR",
                "points": 24426,
                "charterTickets": 3,
                "charterEvaTickets": 1,
                "fleetLiveryTickets": 2,
                "liveScheduleTickets": 1,
                "galleryPostTickets": 5,
                "megaphones": 7,
                "themePreferences": {
                    "unlockedThemes": ["eva_classic", "star_alliance"],
                    "unlockedTrackerItems": ["tracker_special_gold"],
                    "equippedTrackerSkin": "tracker_special_gold",
                    "isWeekendBoosterActive": True,
                    "remainingWeekendDoubleFlights": 4,
                    "isDanmakuVipActive": True,
                    "remainingDanmakuVipDays": 15
                }
            }
        }
        res = query_pilot_inventory(user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["is_read_only"], "Agent inventory tool must be strictly read-only!")
        self.assertIn("安全防護聲明", res["summary"])
        self.assertEqual(res["inventory"]["charter_tickets"], 3)
        self.assertEqual(res["inventory"]["megaphones"], 7)
        self.assertTrue(res["inventory"]["is_weekend_booster_active"])
        self.assertEqual(res["inventory"]["remaining_weekend_double_flights"], 4)
        self.assertEqual(res["inventory"]["equipped_tracker_skin"], "tracker_special_gold")

    @patch("src.tools.crewcenter_inventory_tool.backend_client.get")
    def test_inventory_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_pilot_inventory(user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 4. Media Gallery Tool Tests (Online & Offline)
    # -------------------------------------------------------------
    @patch("src.tools.crewcenter_gallery_tool.backend_client.get")
    def test_gallery_query(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "items": [
                {
                    "id": "media-1",
                    "title": "晨曦成田",
                    "author": {"callsign": "EVA495BR"},
                    "aircraft": "Boeing 777-300ER",
                    "likesCount": 25,
                    "superHeartsCount": 3,
                    "mediaUrl": "https://crewcenter.eva-virtual.com/media/1.jpg"
                }
            ],
            "submissionsEnabled": True
        }
        res = query_media_gallery(limit=5, featured_only=False, user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["items_count"], 1)
        self.assertIn("影音藝廊", res["summary"])

    @patch("src.tools.crewcenter_gallery_tool.backend_client.get")
    def test_gallery_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_media_gallery(limit=5, user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 5. Live Radar & Aircraft Tracker Tool Tests (Online & Offline)
    # -------------------------------------------------------------
    @patch("src.tools.crewcenter_tracker_tool.backend_client.get")
    def test_live_tracker_general_fleet(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": [
                {
                    "callsign": "EVA495",
                    "username": "luffy931225",
                    "aircraftName": "Boeing 777-300ER (EVA Air)",
                    "altitude": 35000,
                    "speed": 480,
                    "heading": 55,
                    "flightPlan": {"departure": "RCTP", "destination": "RJAA"}
                }
            ]
        }
        res = query_live_radar_and_tracker(user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["airborne_count"], 1)
        self.assertIn("航跡雷達", res["summary"])

    @patch("src.tools.crewcenter_tracker_tool.backend_client.get")
    def test_live_tracker_by_callsign_found(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": [
                {
                    "callsign": "EVA495",
                    "username": "luffy931225",
                    "aircraftName": "Boeing 777-300ER (EVA Air)",
                    "altitude": 35000,
                    "speed": 480,
                    "heading": 55,
                    "latitude": 28.5,
                    "longitude": 126.3,
                    "verticalSpeed": 0,
                    "flightPlan": {"departure": "RCTP", "destination": "RJAA"}
                }
            ]
        }
        res = query_live_radar_and_tracker(callsign="EVA495", user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["found"])
        self.assertEqual(res["callsign"], "EVA495")
        self.assertIn("FL350", res["summary"])

    @patch("src.tools.crewcenter_tracker_tool.backend_client.get")
    def test_live_tracker_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_live_radar_and_tracker(user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 6. PIREP History & Active Dispatch Tests (Online & Offline)
    # -------------------------------------------------------------
    def test_pireps_unauthenticated(self):
        res = query_pilot_pireps(user_context=self.unauth_context)
        self.assertEqual(res["status"], "UNAUTHENTICATED")

    @patch("src.tools.crewcenter_pirep_tool.backend_client.get")
    def test_pireps_authenticated_online(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": {
                "pireps": [
                    {
                        "flightNumber": "BR184",
                        "originICAO": "RCTP",
                        "arrivalICAO": "RJAA",
                        "aircraftType": "B77W",
                        "flightTime": 160,
                        "landingVerticalSpeed": -135.0,
                        "landingGForce": 1.10,
                        "earnedPoints": 450,
                        "state": "approved"
                    }
                ]
            }
        }
        res = query_pilot_pireps(limit=5, user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["pireps_count"], 1)
        self.assertIn("飛行報告", res["summary"])

    @patch("src.tools.crewcenter_pirep_tool.backend_client.get")
    def test_pireps_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_pilot_pireps(limit=5, user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    @patch("src.tools.crewcenter_pirep_tool.backend_client.get")
    def test_active_dispatch_online(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": {
                "activeDispatch": {
                    "flightNumber": "BR184",
                    "originICAO": "RCTP",
                    "destinationICAO": "RJAA",
                    "aircraftType": "B78X",
                    "livery": "EVA Air 787-10",
                    "blockFuel": "18,400 kg",
                    "remarks": "Standard ETOPS Routing"
                }
            }
        }
        res = query_active_dispatch(user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_active_dispatch"])
        self.assertIn("BR184", res["summary"])

    @patch("src.tools.crewcenter_pirep_tool.backend_client.get")
    def test_active_dispatch_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_active_dispatch(user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 7. Enhanced Profile Stats & Offline Tests
    # -------------------------------------------------------------
    @patch("src.tools.user_profile_tool.backend_client.get")
    def test_profile_stats_query_online(self, mock_get):
        mock_get.return_value = {
            "success": True,
            "data": {
                "callsign": "EVA495BR",
                "username": "luffy931225",
                "points": 24426,
                "totalFlightTime": 35508,
                "rank": {"name": "Premium Laurel"},
                "currentLocation": "TPE Hub (RCTP)",
                "stats": {
                    "favoriteRoute": "RCTP - RJAA",
                    "favoriteAircraft": "B77W",
                    "recentLandingVs": -138,
                    "recentLandingGForce": 1.10,
                    "totalPassengers": 15400,
                    "totalCargo": 62000
                }
            }
        }
        res = query_pilot_profile(query_type="stats", user_context=self.auth_context)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("RCTP - RJAA", res["summary"])
        self.assertIn("-138 fpm", res["summary"])
        self.assertIn("1.10 G", res["summary"])

    @patch("src.tools.user_profile_tool.backend_client.get")
    def test_profile_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_pilot_profile(query_type="summary", user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    # -------------------------------------------------------------
    # 8. Store Catalog & SimBrief Offline Tests
    # -------------------------------------------------------------
    @patch("src.tools.store_catalog_tool.backend_client.get")
    def test_store_catalog_offline_handling(self, mock_get):
        mock_get.return_value = None  # CrewCenter down
        res = query_store_catalog(user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

    @patch("src.tools.simbrief_tool.backend_client.post")
    def test_simbrief_dispatch_offline_handling(self, mock_post):
        mock_post.return_value = None  # CrewCenter down
        res = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=self.auth_context)
        self.assertEqual(res["status"], "CREWCENTER_OFFLINE")
        self.assertIn("目前似乎無法連線到 CrewCenter", res["summary"])

if __name__ == "__main__":
    unittest.main()

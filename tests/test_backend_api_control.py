import unittest
from unittest.mock import patch, MagicMock
from src.client import BackendClient
from src.context import UserContext
from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.user_profile_tool import query_pilot_profile
from src.tools.store_catalog_tool import query_store_catalog

class TestBackendApiControl(unittest.TestCase):
    """
    Test suite for BRVA_Agent <-> Backend API Control & User Delegation:
    Verifies x-agent-key transmission, user delegation headers, 503 killswitch,
    unauthenticated prompts, SimBrief unlinked prompt handling, and read-only store access.
    """

    def setUp(self):
        self.client = BackendClient(base_url="https://api.eva-virtual.com", api_key="brva_sk_live_test_secret_key_123")
        self.auth_user = UserContext(
            is_authenticated=True,
            user_id="user_12345",
            callsign="BR001",
            username="TestCaptain",
            rank_name="Senior First Officer",
            points=1450.0,
            flight_time_hours=320.5,
            delegation_token="test_delegation_jwt_token_abc"
        )
        self.guest_user = UserContext(is_authenticated=False)

    def test_headers_include_agent_key_and_user_token(self):
        """1. Verify that configured api_key and user_token are sent via proper headers."""
        headers = self.client._headers(user_token="my_user_jwt_token")
        self.assertIn("x-agent-key", headers)
        self.assertEqual(headers["x-agent-key"], "brva_sk_live_test_secret_key_123")
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer my_user_jwt_token")
        self.assertEqual(headers["User-Agent"], "BRVA-Agent/1.0")

    def test_headers_without_agent_key(self):
        """2. Verify client headers when no api_key is provided."""
        empty_client = BackendClient(base_url="https://api.eva-virtual.com", api_key="")
        headers = empty_client._headers()
        self.assertNotIn("x-agent-key", headers)
        self.assertNotIn("Authorization", headers)

    @patch("requests.get")
    def test_backend_killswitch_503_handling(self, mock_get):
        """3. Master Killswitch: When backend admin disables agent, returns 503."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = '{"error":"AI Agent service is currently disabled by administrator"}'
        mock_get.return_value = mock_resp

        res = self.client.get("/api/weather/metar", params={"icao": "RCTP"})
        self.assertIsNone(res, "Should safely return None when backend disabled via killswitch")

    @patch("requests.get")
    def test_backend_unauthorized_401_handling(self, mock_get):
        """4. Unauthorized / Revoked: Backend returns 401 when key revoked or invalid."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error":"Invalid, expired, or revoked Agent API key"}'
        mock_get.return_value = mock_resp

        res = self.client.get("/api/routes", params={"dept": "RCTP", "arr": "RJAA"})
        self.assertIsNone(res, "Should safely return None when key rejected with 401")

    @patch("requests.get")
    def test_backend_rate_limited_429_handling(self, mock_get):
        """5. Rate Limit: Backend returns 429 when exceeding 60 requests/minute."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = '{"error":"Agent API rate limit exceeded (maximum 60 requests/minute)"}'
        mock_get.return_value = mock_resp

        res = self.client.get("/api/routes")
        self.assertIsNone(res, "Should safely return None when rate limited")

    @patch("requests.get")
    def test_backend_success_200(self, mock_get):
        """6. Success: Backend returns 200 with JSON payload."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "routes": [{"flight_number": "BR184"}]}
        mock_get.return_value = mock_resp

        res = self.client.get("/api/routes")
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["routes"][0]["flight_number"], "BR184")

    def test_simbrief_unauthenticated_prompts_link(self):
        """7. Unauthenticated Dispatch: When guest attempts dispatch, prompts for account link."""
        res = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=self.guest_user)
        self.assertEqual(res["status"], "UNAUTHENTICATED")
        self.assertIn("尚未登入 CrewCenter 連結個人帳號", res["summary"])

    @patch("requests.post")
    def test_simbrief_unlinked_account_internal_dispatch(self, mock_post):
        """8. SimBrief Unlinked: Backend indicates SimBrief not linked, dispatches internally with requested wording."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "success": False,
            "simbriefLinked": False,
            "error": "SimBrief account not linked"
        }
        mock_post.return_value = mock_resp

        res = generate_simbrief_dispatch("BR184", "RCTP", "RJAA", "B78X", user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS_INTERNAL_DISPATCH")
        self.assertFalse(res["simbrief_linked"])
        self.assertIn("目前沒有登錄 SimBrief", res["summary"])
        self.assertIn("CrewCenter 內部已經為您完成 Dispatch", res["summary"])
        self.assertIn("BR184", res["summary"])

    def test_user_profile_unauthenticated(self):
        """9. Unauthenticated Profile Query: Prompts to link account."""
        res = query_pilot_profile("points", user_context=self.guest_user)
        self.assertEqual(res["status"], "UNAUTHENTICATED")
        self.assertIn("尚未在側邊欄登入 CrewCenter", res["summary"])

    @patch("requests.get")
    def test_user_profile_authenticated(self, mock_get):
        """10. Authenticated Profile Query: Returns callsign, hours, and points."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "user": {
                "callsign": "BR001",
                "rank": {"name": "Senior First Officer"},
                "points": 1450.0,
                "totalFlightTime": 19230
            }
        }
        mock_get.return_value = mock_resp

        res = query_pilot_profile("points", user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("1,450 pts", res["summary"])

    @patch("requests.get")
    def test_store_catalog_strictly_read_only(self, mock_get):
        """11. Store Catalog: Returns available items, strictly forbids purchase."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "items": [
                {"name": "長程航線特許卡", "price": 100, "description": "允許執飛跨洋航線"}
            ]
        }
        mock_get.return_value = mock_resp

        res = query_store_catalog(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(res["can_purchase"])
        self.assertIn("僅供查閱商品與餘額", res["summary"])
        self.assertIn("長程航線特許卡", res["summary"])

    @patch("requests.get")
    def test_verify_token_client(self, mock_get):
        """12. BackendClient.verify_token: calls /api/agent/token with token."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "valid": True, "user": {"callsign": "BR001"}}
        mock_get.return_value = mock_resp

        res = self.client.verify_token("test_token_123")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("valid"))
        self.assertEqual(res.get("user", {}).get("callsign"), "BR001")

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from src.client import BackendClient
from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes

class TestBackendApiControl(unittest.TestCase):
    """
    Test suite for BRVA_Agent <-> Backend API Control:
    Verifies x-agent-key transmission, 503 killswitch response handling,
    401 unauthorized handling, 429 rate limit handling, and graceful offline fallback.
    """

    def setUp(self):
        self.client = BackendClient(base_url="https://api.eva-virtual.com", api_key="brva_sk_live_test_secret_key_123")

    def test_headers_include_agent_key(self):
        """1. Verify that configured api_key is sent via x-agent-key header."""
        headers = self.client._headers()
        self.assertIn("x-agent-key", headers)
        self.assertEqual(headers["x-agent-key"], "brva_sk_live_test_secret_key_123")
        self.assertEqual(headers["User-Agent"], "BRVA-Agent/1.0")

    def test_headers_without_agent_key(self):
        """2. Verify client headers when no api_key is provided."""
        empty_client = BackendClient(base_url="https://api.eva-virtual.com", api_key="")
        headers = empty_client._headers()
        self.assertNotIn("x-agent-key", headers)

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

    @patch("requests.get")
    def test_weather_tool_fallback_on_backend_killswitch(self, mock_get):
        """7. Tool Fallback: When backend returns 503, weather tool falls back to realistic METAR calculation."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_get.return_value = mock_resp

        # Tool should not crash; must fall back to local computation
        weather = fetch_aviation_weather("RCTP", "05L")
        self.assertEqual(weather["icao"], "RCTP")
        self.assertIn("crosswind_kts", weather)
        self.assertIn("headwind_kts", weather)
        self.assertTrue(weather["is_safe"])

    @patch("requests.get")
    def test_route_tool_fallback_on_backend_killswitch(self, mock_get):
        """8. Tool Fallback: When backend returns 503, route tool falls back to local routes CSV database."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_get.return_value = mock_resp

        routes = query_virtual_routes("RCTP", "RJAA", "B78X")
        self.assertIsInstance(routes, list)
        self.assertGreater(len(routes), 0)
        self.assertTrue(any(r["flight_number"] in ("BR184", "BR198") for r in routes))

if __name__ == "__main__":
    unittest.main()

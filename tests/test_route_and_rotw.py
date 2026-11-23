import unittest
from src.agent import AeroAgent
from src.memory import AgentMemory
from src.context import UserContext
from src.llm import OfflineRuleProvider
from src.tools.route_tool import find_route_by_flight_number, query_flight_route_by_number
from src.tools.crewcenter_codeshare_tool import recommend_routes_and_codeshares

class TestRouteAndROTW(unittest.TestCase):
    def setUp(self):
        self.memory = AgentMemory()
        self.agent = AeroAgent(memory=self.memory, llm_provider=OfflineRuleProvider())
        self.auth_user = UserContext(
            is_authenticated=True,
            user_id="user_eva_888",
            callsign="EVA001",
            rank_name="Senior Captain",
            points=2500,
            delegation_token="valid_delegation_jwt"
        )

    def test_find_route_by_flight_number_br3(self):
        # BR3 should resolve to KIAD -> RCTP with B789, NOT RCTP -> RJAA!
        route = find_route_by_flight_number("BR3")
        self.assertIsNotNone(route)
        self.assertEqual(route["dep"], "KIAD")
        self.assertEqual(route["arr"], "RCTP")
        self.assertEqual(route["aircraft"], "B789")
        self.assertIn("15h", route["flight_time"])

    def test_find_route_by_flight_number_numeric_equivalence(self):
        # 3 or BR03 or EVA3 should resolve to BR3
        r1 = find_route_by_flight_number("3")
        self.assertIsNotNone(r1)
        self.assertEqual(r1["dep"], "KIAD")
        self.assertEqual(r1["arr"], "RCTP")

        r2 = find_route_by_flight_number("EVA 3")
        self.assertIsNotNone(r2)
        self.assertEqual(r2["dep"], "KIAD")
        self.assertEqual(r2["arr"], "RCTP")

    def test_find_route_by_flight_number_br184(self):
        route = find_route_by_flight_number("BR184")
        self.assertIsNotNone(route)
        self.assertEqual(route["dep"], "RCTP")
        self.assertEqual(route["arr"], "RJAA")
        self.assertIn("B78", route["aircraft"])

    def test_find_route_unknown_flight(self):
        route = find_route_by_flight_number("BR9999")
        self.assertIsNone(route)

    def test_query_flight_route_by_number_success(self):
        res = query_flight_route_by_number("BR3", user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["route"]["dep"], "KIAD")
        self.assertEqual(res["route"]["arr"], "RCTP")
        self.assertIn("KIAD", res["summary"])
        self.assertIn("RCTP", res["summary"])
        self.assertIn("B789", res["summary"])

    def test_query_flight_route_by_number_not_found(self):
        res = query_flight_route_by_number("BR9999", user_context=self.auth_user)
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertIn("查無航班資訊", res["summary"])
        self.assertIn("BR9999", res["summary"])

    def test_rotw_route_recommendation(self):
        res = recommend_routes_and_codeshares(category="rotw", user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["recommended_count"] >= 2)
        self.assertIn("ROTW", res["summary"])
        self.assertIn("2.0x", res["summary"])
        self.assertIn("雙倍哩程", res["summary"])

    def test_general_recommendation_includes_rotw(self):
        res = recommend_routes_and_codeshares(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("ROTW", res["summary"])
        self.assertIn("2.0x", res["summary"])

    def test_agent_dispatch_br3_correct_city_pair(self):
        # Dispatching BR3 MUST NOT default to RCTP -> RJAA
        resp, trace = self.agent.run("簽派 BR3", user_context=self.auth_user, return_trace=True)
        self.assertIn("KIAD", resp)
        self.assertIn("RCTP", resp)
        self.assertNotIn("RJAA 🛬", resp)
        tool_calls = [s for s in trace if s.get("type") == "tool_call"]
        self.assertEqual(len(tool_calls), 2)
        tool_names = [s.get("tool") for s in tool_calls]
        self.assertIn("query_flight_route_by_number", tool_names)
        self.assertTrue(any(t in ("generate_dispatch", "generate_simbrief_dispatch") for t in tool_names))
        call_repr = " ".join(str(s.get("args") or s.get("content") or "") for s in tool_calls)
        self.assertIn("KIAD", call_repr)
        self.assertIn("RCTP", call_repr)
        self.assertIn("B789", call_repr)

    def test_agent_dispatch_unknown_flight_no_false_fallback(self):
        # Dispatching an unlisted flight must NOT falsely dispatch RCTP -> RJAA!
        resp, trace = self.agent.run("幫我簽派 BR9999", user_context=self.auth_user, return_trace=True)
        self.assertIn("查無航班編號", resp)
        self.assertIn("BR9999", resp)
        self.assertNotIn("ACTIVE DISPATCH", resp)
        self.assertNotIn("RJAA 🛬", resp)

    def test_agent_query_flight_route_intent(self):
        resp, trace = self.agent.run("查詢 BR3 航班航線與指派機型", user_context=self.auth_user, return_trace=True)
        self.assertIn("KIAD", resp)
        self.assertIn("RCTP", resp)
        self.assertIn("B789", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("query_flight_route_by_number", tool_names)

    def test_agent_rotw_recommendation_intent(self):
        resp, trace = self.agent.run("推薦本週 ROTW 每週精選雙倍哩程航線", user_context=self.auth_user, return_trace=True)
        self.assertIn("ROTW", resp)
        self.assertIn("2.0x", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("recommend_routes_and_codeshares", tool_names)

if __name__ == "__main__":
    unittest.main()

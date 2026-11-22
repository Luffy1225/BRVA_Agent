import unittest
from unittest.mock import patch, MagicMock
from src.agent import AeroAgent
from src.memory import AgentMemory
from src.context import UserContext
from src.llm import OfflineRuleProvider
from src.tools.user_profile_tool import search_pilot_user
from src.tools.crewcenter_atc_tool import query_atc_status, query_atc_mentoring_eligibility
from src.tools.crewcenter_live_tool import query_live_overview
from src.tools.crewcenter_codeshare_tool import query_codeshare_partners, recommend_routes_and_codeshares

class TestCrewCenterExtendedTools(unittest.TestCase):
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

    def test_search_pilot_user(self):
        # 1. Search existing callsign
        res1 = search_pilot_user("EVA001", user_context=self.auth_user)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertTrue(res1["count"] >= 1)
        self.assertIn("EVA001", res1["summary"])
        self.assertIn("Senior Captain", res1["summary"])

        # 2. Search pilot 495
        res2 = search_pilot_user("EVA495BR", user_context=self.auth_user)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertIn("EVA495BR", res2["summary"])

        # 3. Empty keyword
        res3 = search_pilot_user("", user_context=self.auth_user)
        self.assertEqual(res3["status"], "INVALID_KEYWORD")

    def test_query_atc_status(self):
        res = query_atc_status(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("認證航管員", res["current_rank"])
        self.assertIn("資深航管員", res["next_rank"])
        self.assertTrue(res["progress_percent"] > 0)
        self.assertTrue(res["duty_hours_remaining"] >= 0)
        self.assertTrue(res["operations_remaining"] >= 0)
        self.assertIn("ATC Status", res["summary"])

    def test_query_atc_mentoring_eligibility(self):
        res = query_atc_mentoring_eligibility(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("criteria", res)
        self.assertEqual(len(res["criteria"]), 5) # 5 Verified Criteria
        self.assertIn("/atc/mentoring", res["summary"])
        self.assertIn("五大審核條件", res["summary"])

    def test_query_live_overview(self):
        res = query_live_overview(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["total_fleet"] > 0)
        self.assertTrue(res["in_flight_count"] >= 0)
        self.assertIn("/live/overview", res["summary"])
        self.assertIn("在空巡航執飛", res["summary"])

    def test_query_codeshare_partners(self):
        res = query_codeshare_partners(user_context=self.auth_user)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["total_codeshare_partners"] >= 5)
        self.assertIn("全日空", res["summary"])
        self.assertIn("聯合航空", res["summary"])
        self.assertIn("新加坡航空", res["summary"])

    def test_recommend_routes_and_codeshares(self):
        # 1. Recommend codeshare
        res1 = recommend_routes_and_codeshares(category="codeshare", user_context=self.auth_user)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertTrue(res1["recommended_count"] >= 1)
        self.assertIn("Codeshare", res1["summary"])

        # 2. Filter by ANA
        res2 = recommend_routes_and_codeshares(airline="ANA", user_context=self.auth_user)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertIn("NH", res2["summary"])

    def test_agent_intent_dispatch_search_pilot(self):
        resp, trace = self.agent.run("搜尋飛官 EVA001 的資料與飛行檔案", user_context=self.auth_user, return_trace=True)
        self.assertIn("EVA001", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("search_pilot_user", tool_names)

    def test_agent_intent_dispatch_atc_rank_gap(self):
        resp, trace = self.agent.run("查詢我的 ATC rank 與距離下一個等級還多久", user_context=self.auth_user, return_trace=True)
        self.assertIn("航管等級", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("query_atc_status", tool_names)

    def test_agent_intent_dispatch_mentoring_eligibility(self):
        resp, trace = self.agent.run("檢查我是否滿足 /atc/mentoring 的培訓條件？", user_context=self.auth_user, return_trace=True)
        self.assertIn("mentoring", resp.lower())
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("query_atc_mentoring_eligibility", tool_names)

    def test_agent_intent_dispatch_live_overview(self):
        resp, trace = self.agent.run("查詢 /live/overview Live 模式機隊總覽與營運狀態", user_context=self.auth_user, return_trace=True)
        self.assertIn("live", resp.lower())
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("query_live_overview", tool_names)

    def test_agent_intent_dispatch_codeshares_count(self):
        resp, trace = self.agent.run("長榮航空現在有幾個 codeshare 合作夥伴？有哪些航空公司？", user_context=self.auth_user, return_trace=True)
        self.assertIn("Codeshare", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("query_codeshare_partners", tool_names)

    def test_agent_intent_dispatch_recommend_codeshare_routes(self):
        resp, trace = self.agent.run("推薦幾條 ANA Codeshare 聯營航線", user_context=self.auth_user, return_trace=True)
        self.assertIn("推薦", resp)
        tool_names = [s.get("tool") for s in trace if s.get("type") == "tool_call"]
        self.assertIn("recommend_routes_and_codeshares", tool_names)

if __name__ == "__main__":
    unittest.main()

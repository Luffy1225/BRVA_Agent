import os
import unittest
from unittest.mock import patch, MagicMock
from src.agent import AeroAgent
from src.memory import AgentMemory
from src.context import UserContext
from src.llm import OfflineRuleProvider

class TestAgentTrace(unittest.TestCase):

    def setUp(self):
        self.memory = AgentMemory()
        self.agent = AeroAgent(memory=self.memory, llm_provider=OfflineRuleProvider())
        self.auth_user = UserContext(
            is_authenticated=True,
            user_id="user_123",
            callsign="BR001",
            rank_name="Senior First Officer",
            points=1200,
            delegation_token="valid_delegation_jwt"
        )

    @patch("requests.post")
    def test_two_turn_dispatch_flow(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "data": {
                "general": {
                    "route": "RCTP/05L CHALI1A TONIK V22 MORUS RJAA/16R",
                    "initial_altitude": "FL370",
                },
                "fuel": {"plan_ramp": 18200},
                "times": {"est_time_enroute": 9600},
                "ofp_url": "https://www.simbrief.com/ofp/123",
            }
        }
        mock_post.return_value = mock_resp

        # Turn 1: Flight and Weather Query
        user_turn_1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"
        resp_1 = self.agent.run(user_turn_1, user_context=self.auth_user, verbose=False)

        self.assertIn("BR184", resp_1)
        self.assertIn("側風", resp_1)
        self.assertIn("是否直接為您簽派", resp_1)
        self.assertIsNotNone(self.memory.get_pending())
        self.assertEqual(self.memory.get_pending().flight_number, "BR184")

        # Turn 2: Pilot Confirmation (Human-in-the-Loop)
        user_turn_2 = "好的，幫我直接簽派！"
        resp_2 = self.agent.run(user_turn_2, user_context=self.auth_user, verbose=False)

        self.assertIn("BRVA 簽派中心放行成功", resp_2)
        self.assertIn("FL370", resp_2)
        self.assertIn("ACTIVE DISPATCH", resp_2)
        self.assertIsNone(self.memory.get_pending())

    @patch("requests.post")
    def test_unlinked_simbrief_flow(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "success": False,
            "simbriefLinked": False,
            "error": "SimBrief account not linked"
        }
        mock_post.return_value = mock_resp

        # Turn 1: Flight and Weather Query
        user_turn_1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣與推薦班次。"
        resp_1 = self.agent.run(user_turn_1, user_context=self.auth_user, verbose=False)
        self.assertIsNotNone(self.memory.get_pending())

        # Simulate SimBrief Unlinked Response from Backend
        user_turn_2 = "確認簽派"
        resp_2 = self.agent.run(user_turn_2, user_context=self.auth_user, verbose=False)

        self.assertIn("目前沒有登錄 SimBrief", resp_2)
        self.assertIn("CrewCenter 內部已經為您完成 Dispatch", resp_2)

    def test_telemetry_audit_flow(self):
        user_query = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"
        resp = self.agent.run(user_query, verbose=False)

        self.assertIn("黑盒子飛行紀錄", resp)
        self.assertIn("不合格", resp)
        self.assertIn("硬著陸", resp)

    def test_greeting_flow(self):
        resp = self.agent.run("你好", verbose=False)
        self.assertIn("機長您好", resp)
        self.assertIn("簽派", resp)
        self.assertNotIn("BR184", resp)

    def test_fallback_guidance_flow(self):
        resp = self.agent.run("今天吃什麼", verbose=False)
        self.assertIn("我是您的 AI 簽派副駕", resp)
        self.assertNotIn("BR184", resp)

if __name__ == "__main__":
    unittest.main()

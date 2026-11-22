import os
import unittest
from src.agent import AeroAgent
from src.memory import AgentMemory
from src.llm import OfflineRuleProvider

class TestAgentTrace(unittest.TestCase):

    def setUp(self):
        self.memory = AgentMemory()
        self.agent = AeroAgent(memory=self.memory, llm_provider=OfflineRuleProvider())

    def test_two_turn_dispatch_flow(self):
        # Turn 1: Flight and Weather Query
        user_turn_1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"
        resp_1 = self.agent.run(user_turn_1, verbose=False)

        self.assertIn("BR184", resp_1)
        self.assertIn("側風", resp_1)
        self.assertIn("是否直接為您簽派", resp_1)
        self.assertIsNotNone(self.memory.get_pending())
        self.assertEqual(self.memory.get_pending().flight_number, "BR184")

        # Turn 2: Pilot Confirmation (Human-in-the-Loop)
        user_turn_2 = "好的，幫我直接簽派！"
        resp_2 = self.agent.run(user_turn_2, verbose=False)

        self.assertIn("BRVA 簽派中心放行成功", resp_2)
        self.assertIn("FL370", resp_2)
        self.assertIn("ACTIVE DISPATCH", resp_2)
        self.assertNotIn("https://www.simbrief.com", resp_2)
        self.assertIsNone(self.memory.get_pending())

    def test_unlinked_simbrief_flow(self):
        # Turn 1: Flight and Weather Query
        user_turn_1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣與推薦班次。"
        resp_1 = self.agent.run(user_turn_1, verbose=False)
        self.assertIsNotNone(self.memory.get_pending())

        # Simulate Pilot Not Having Linked SimBrief
        os.environ["SIMBRIEF_ACCOUNT_LINKED"] = "false"
        try:
            user_turn_2 = "確認簽派"
            resp_2 = self.agent.run(user_turn_2, verbose=False)

            self.assertIn("SimBrief 帳號尚未綁定", resp_2)
            self.assertIn("簽派中心", resp_2)
            self.assertNotIn("https://www.simbrief.com", resp_2)
        finally:
            os.environ.pop("SIMBRIEF_ACCOUNT_LINKED", None)

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

import unittest
from src.tools.rag_tool import rag_engine, query_flight_sop_and_regulations, RAGQueryInput, RAGOutput
from src.agent import AeroAgent
from src.memory import AgentMemory

class TestAviationRAG(unittest.TestCase):
    """
    Test suite for Retrieval-Augmented Generation (RAG) tool:
    Verifies indexing of official SOP, Live Rules, and Practical Flight Exam manuals,
    precision BM25 & semantic retrieval, and agent integration.
    """

    def test_rag_engine_loading(self):
        """Verifies that knowledge base files are properly loaded and indexed."""
        self.assertGreater(len(rag_engine.chunks), 10, "Should have indexed at least 10 knowledge chunks")
        self.assertGreater(len(rag_engine.doc_freqs), 50, "Should have built a comprehensive token dictionary")
        self.assertGreater(rag_engine.avg_doc_len, 10, "Average chunk length should be reasonable")

        # Verify sources are captured
        sources = {c.source for c in rag_engine.chunks}
        self.assertIn("SOP 手冊", sources)
        self.assertIn("LIVE 營運手冊", sources)
        self.assertIn("術科考核手冊", sources)

    def test_query_twin_jet_engine_start(self):
        """Test 1: Twin-jet engine start sequence (2 -> 1)."""
        res = query_flight_sop_and_regulations("請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序是什麼？")
        self.assertTrue(res["success"])
        self.assertGreater(res["results_count"], 0)

        ans = res["direct_answer"]
        self.assertIn("2", ans)
        self.assertIn("1", ans)
        self.assertIn("右", ans)
        self.assertIn("左", ans)
        self.assertIn("SOP 手冊", ans)

    def test_query_taxi_speed_limits(self):
        """Test 2: Strict taxiway speed caps and breakaway thrust limit."""
        res = query_flight_sop_and_regulations("地面滑行空速限制與起步推力上限是多少？")
        self.assertTrue(res["success"])
        ans = res["direct_answer"]
        self.assertIn("26", ans)  # 26 kts straightaway & 26% N1
        self.assertIn("12", ans)  # 12 kts ramp
        self.assertIn("10", ans)  # 10 kts turns
        self.assertIn("26% N1", ans)
        self.assertIn("方向舵腳煞車", ans)

    def test_query_stabilized_approach_and_go_around(self):
        """Test 3: Stabilized approach gate and mandatory go-around criteria."""
        res = query_flight_sop_and_regulations("最終進場放輪時機與穩定進場強制重飛 (Go-Around) 門檻？")
        self.assertTrue(res["success"])
        ans = res["direct_answer"]
        self.assertIn("2,500", ans)
        self.assertIn("7", ans)
        self.assertIn("1 個圓點", ans)
        self.assertIn("重飛", ans)

    def test_query_practical_exam_disqualifiers(self):
        """Test 4: Practical flight exam automatic failure items."""
        res = query_flight_sop_and_regulations("術科實作檢定有哪些重大違規會觸發一票否決 (Automatic Fail)？及格標準是多少？")
        self.assertTrue(res["success"])
        ans = res["direct_answer"]
        self.assertIn("80%", ans)
        self.assertIn("1.6G", ans)
        self.assertIn("EVA 000BR", ans)
        self.assertIn("一票否決", ans)

    def test_query_traffic_pattern_work(self):
        """Test 5: Traffic pattern departure phraseology and pattern altitude."""
        res = query_flight_sop_and_regulations("起落航線 (Traffic Pattern) 離場必須通報什麼管制呼號？高度限制是多少？")
        self.assertTrue(res["success"])
        ans = res["direct_answer"]
        self.assertIn("remaining in the pattern", ans)
        self.assertIn("1,500", ans)
        self.assertIn("觸地重飛", ans)

    def test_query_live_rules_and_crash_notification(self):
        """Test 6: Live fleet booking limit and mandatory 3-hour crash notification."""
        res = query_flight_sop_and_regulations("LIVE 機隊每位機師最多可以預約幾架飛機？若發生墜機事故多久內要通報？")
        self.assertTrue(res["success"])
        ans = res["direct_answer"]
        self.assertIn("3 架", ans)
        self.assertIn("3 小時", ans)
        self.assertIn("Wait Landing", ans)

    def test_rag_agent_e2e_integration(self):
        """Test 7: AeroAgent end-to-end integration with RAG query."""
        agent = AeroAgent(memory=AgentMemory())
        user_query = "機長你好，請幫我查詢官方手冊：雙發噴射客機發動機啟動順序與滑行速限規範是什麼？"
        resp = agent.run(user_query, verbose=False)

        self.assertIn("官方規章檢索結果", resp)
        self.assertIn("2 -> 1", resp)
        self.assertIn("26", resp)
        self.assertIn("SOP 手冊", resp)

    def test_pydantic_schema_validation(self):
        """Test 8: Validates Pydantic I/O models."""
        input_data = RAGQueryInput(query="測試查詢", top_k=2, category="sop")
        self.assertEqual(input_data.category, "sop")

        res = query_flight_sop_and_regulations("起步推力上限")
        output_obj = RAGOutput(
            query=res["query"],
            results_count=res["results_count"],
            top_chunks=res["top_chunks"],
            direct_answer=res["direct_answer"]
        )
        self.assertEqual(output_obj.query, "起步推力上限")
        self.assertGreaterEqual(output_obj.results_count, 1)

if __name__ == "__main__":
    unittest.main()

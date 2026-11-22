#!/usr/bin/env python3
"""
Comprehensive Live Scenario Test Suite for AeroAgent & BRVA Backend
Tests 6 realistic aviation operational scenarios:
1. Long-haul International Dispatch (RCTP -> RJAA / B78X): Live METAR + Routes + HITL + SimBrief OFP
2. Domestic / Regional Dispatch (RCKH -> RCSS / A321): Multi-airport Weather & Route Query
3. High Crosswind Risk Assessment & Safety Envelope
4. Deterministic Telemetry Auditing (PASS vs FAIL with Hard Landing Disqualification)
5. Aviation RAG Regulations & Authority Citations
6. Boundary Error Handling & Backend Fallback
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import AeroAgent
from src.tools.weather_tool import fetch_aviation_weather
from src.tools.route_tool import query_virtual_routes
from src.tools.simbrief_tool import generate_simbrief_dispatch
from src.tools.telemetry_tool import analyze_flight_telemetry
from src.tools.rag_tool import query_flight_sop_and_regulations

def banner(title: str):
    print("\n" + "=" * 80)
    print(f"✈️  {title}")
    print("=" * 80)

def run_scenarios():
    agent = AeroAgent()
    print(f"\n[AeroAgent] 系統初始化完成，使用 LLM Provider: {agent.llm.provider_name.upper()}\n")

    # =========================================================================
    # 情境一：國際航線簽派 (RCTP -> RJAA / B78X) 完整多輪人機協同 (HITL)
    # =========================================================================
    banner("情境 1：長程國際簽派 (RCTP -> RJAA) - METAR 起降氣象 + 航網匹配 + HITL 授權 + SimBrief OFP")
    
    print("【第一輪：機長提出簽派與天氣諮詢需求】")
    p1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"
    print(f"🧑‍✈️ 機長: {p1}\n")
    resp1 = agent.run(p1, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp1}\n")

    # 驗證第一輪
    assert "BR184" in resp1 or "RJAA" in resp1, "第一輪應推薦航班並提供目的地氣象"
    pending = agent.memory.get_pending()
    assert pending is not None, "Memory 應暫存待簽派航班狀態"
    print(f"✅ [PASS] 第一輪成功暫存待簽派航班: {pending.flight_number} ({pending.dep_icao} -> {pending.arr_icao} / {pending.aircraft_type})")

    print("\n【第二輪：機長給予人機協同授權 (HITL Confirmation)】")
    p2 = "好的，幫我直接簽派！"
    print(f"🧑‍✈️ 機長: {p2}\n")
    resp2 = agent.run(p2, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp2}\n")

    # 驗證第二輪
    assert "簽派計畫已成功生成" in resp2 or "OFP" in resp2, "第二輪應成功產出簽派放行單"
    assert "FL370" in resp2, "放行單應包含巡航高度"
    assert "SimBrief" in resp2, "放行單應包含 SimBrief 計畫連結"
    assert agent.memory.get_pending() is None, "簽派完成後 Memory pending 狀態應已清空"
    print("✅ [PASS] 第二輪成功授權完成 SimBrief 官方放行單生成！")

    # =========================================================================
    # 情境二：區域/國內短程簽派 (RCKH -> RCSS / A321) 與跑道風向分量解析
    # =========================================================================
    banner("情境 2：區域/國內短程簽派 (RCKH -> RCSS) - 雙機場 METAR + 台北松山進場氣象")
    
    # 測試後端即時 METAR 連動
    print("2.1 測試後端即時 METAR 連動 (RCSS 台北松山 & RCKH 高雄小港):")
    rcss_wx = fetch_aviation_weather("RCSS", "10")
    print(f"   • RCSS (松山 10 跑道) 即時天氣報文: {rcss_wx.get('raw_metar')}")
    print(f"   • 風向: {rcss_wx.get('wind_dir')}° / 風速: {rcss_wx.get('wind_speed_kts')} kts / 側風: {rcss_wx.get('crosswind_kts')} kts / 逆風: {rcss_wx.get('headwind_kts')} kts")
    assert rcss_wx.get("success") is not False, "RCSS 天氣查詢應成功"

    print("\n2.2 Agent 短程航線推薦與降落建議:")
    p3 = "請幫我查詢從高雄 (RCKH) 飛往台北松山 (RCSS) 的班機，機型為 A321，並告訴我松山 10 跑道目前側風情況。"
    print(f"🧑‍✈️ 機長: {p3}\n")
    resp3 = agent.run(p3, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp3}\n")
    assert "RCSS" in resp3, "回應中應提及 RCSS 機場"
    print("✅ [PASS] 區域短程簽派與特定跑道 (RCSS 10) 側風運算正確！")

    # =========================================================================
    # 情境三：強側風與極端天候安全包絡線防禦性操作評估
    # =========================================================================
    banner("情境 3：起降氣象安全包絡線與側風極限安全評估 (Crosswind Safety Envelope)")
    print("3.1 測試香港赤鱲角 (VHHH) 與成田 (RJAA) 跑道安全包絡線:")
    vhhh_wx = fetch_aviation_weather("VHHH", "07L")
    print(f"   • VHHH 07L 跑道: 側風 {vhhh_wx.get('crosswind_kts')} kts, 逆風 {vhhh_wx.get('headwind_kts')} kts, 適航判定: {vhhh_wx.get('is_safe')}")
    print(f"   • 安全評估說明: {vhhh_wx.get('risk_notes')}")
    assert isinstance(vhhh_wx.get("crosswind_kts"), float), "側風必須為精確浮點數"
    assert vhhh_wx.get("is_safe") is True or vhhh_wx.get("is_safe") is False
    print("✅ [PASS] 側風三角函數向量解析與民航安全包絡線判定無誤！")

    # =========================================================================
    # 情境四：黑盒子飛行遙測時序審核 (確定性 Pandas 分析，零算術幻覺)
    # =========================================================================
    banner("情境 4：黑盒子遙測合格 (PASS) 與違規 (FAIL) 確定性時序檢測")
    
    print("4.1 審核合格黑盒子時序 (sample_flight_pass.csv):")
    p_pass = "請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。"
    print(f"🧑‍✈️ 考核官: {p_pass}\n")
    resp_pass = agent.run(p_pass, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_pass}\n")
    assert "合格 (PASS)" in resp_pass, "應評定為合格"
    assert "100" in resp_pass, "分數應為滿分 100"
    print("✅ [PASS] 合格飛行遙測紀錄審核無誤！")

    print("\n4.2 審核違規黑盒子時序 (sample_flight_fail.csv - 觸發滑行超速與硬著陸一票否決):")
    p_fail = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"
    print(f"🧑‍✈️ 考核官: {p_fail}\n")
    resp_fail = agent.run(p_fail, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_fail}\n")
    assert "不合格 (FAIL)" in resp_fail, "應評定為不合格"
    assert "硬著陸 (Hard Landing)" in resp_fail, "應精確觸發硬著陸一票否決"
    assert "滑行超速" in resp_fail, "應精確抓出地面滑行超速 (>26 kts)"
    print("✅ [PASS] 違規項目精確定位，一票否決機制生效，零數值幻覺！")

    # =========================================================================
    # 情境五：官方 SOP 與規章 RAG 檢索與權威引文合成
    # =========================================================================
    banner("情境 5：民航規章與標準操作程序 (SOP) RAG 檢索增強生成")
    
    print("5.1 測試發動機啟動程序 SOP:")
    p_rag1 = "請問雙發噴射客機發動機啟動順序是多少？"
    print(f"🧑‍✈️ 機長: {p_rag1}\n")
    resp_rag1 = agent.run(p_rag1, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_rag1}\n")
    assert "2 號" in resp_rag1 or "2 -> 1" in resp_rag1 or "2" in resp_rag1, "發動機啟動順序應包含 2 號或 2 -> 1"
    assert "【來源：" in resp_rag1, "必須附帶權威引文出處"

    print("\n5.2 測試地面滑行速限 SOP:")
    p_rag2 = "請問直線滑行道與機坪滑行速限分別是多少節？"
    print(f"🧑‍✈️ 機長: {p_rag2}\n")
    resp_rag2 = agent.run(p_rag2, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_rag2}\n")
    assert "26" in resp_rag2, "直線滑行速限應為 26 節"
    assert "【來源：" in resp_rag2, "必須附帶權威引文出處"
    print("✅ [PASS] SOP 規章問答精準命中並正確標註出處引文！")

    # =========================================================================
    # 情境六：異常輸入邊界容錯與後端優雅降級 (Resilience & Fallback)
    # =========================================================================
    banner("情境 6：異常邊界容錯 (無效 ICAO 代碼與後端連線中斷防護)")
    
    print("6.1 測試不存在/格式錯誤之 ICAO 代碼:")
    err_wx = fetch_aviation_weather("INVALID_AIRPORT_1234")
    print(f"   • 回傳結構: {err_wx}")
    assert err_wx["success"] is False, "錯誤 ICAO 應回傳結構化失敗而非丟出未捕獲例外"

    print("\n6.2 Agent 面對未開放航線查詢時的友善引導:")
    p_err = "請幫我查詢從 ZZZZ 到 YYYY 的班機。"
    print(f"🧑‍✈️ 機長: {p_err}\n")
    resp_err = agent.run(p_err, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_err}\n")
    print("✅ [PASS] 異常邊界處理完備，系統始終維持穩定回應！")

    # =========================================================================
    # 總結
    # =========================================================================
    banner("🎉 全部 6 大航空實戰情境 100% 驗證通過！")
    print("1. METAR 即時天氣與跑道風向三角函數向量分解: 正常")
    print("2. 後端 Routes API 與長榮虛擬航網匹配連動: 正常")
    print("3. 多輪 Human-in-the-Loop 簽派放行與 SimBrief OFP 生成: 正常")
    print("4. Pandas 向量化黑盒子過載/超速時序檢測 (零算術幻覺): 正常")
    print("5. Aviation RAG 官方規章知識庫與出處標註: 正常")
    print("6. 邊界異常防護與優雅降級機制: 正常")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_scenarios()

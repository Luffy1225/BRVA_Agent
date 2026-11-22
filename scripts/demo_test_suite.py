import os
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

def separator(title: str):
    print("\n" + "=" * 75)
    print(f"✈️  {title}")
    print("=" * 75)

def run_e2e_tests():
    agent = AeroAgent()

    # -------------------------------------------------------------
    # 測試情境一：航線推薦 + 天氣分析 + 側風評估 (第一輪)
    # -------------------------------------------------------------
    separator("測試 1：簽派航線推薦與起降側風分析 (第一輪對話)")
    prompt_1 = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"
    print(f"🧑 機長輸入: {prompt_1}\n")
    resp_1 = agent.run(prompt_1, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_1}")

    # 驗證狀態
    pending = agent.memory.get_pending()
    assert pending is not None, "Memory 應該成功暫存待簽派航班！"
    assert pending.flight_number == "BR184", f"預期待簽派航班為 BR184，實際為 {pending.flight_number}"
    print("\n✅ [PASS] 第一輪成功暫存待簽派狀態 (BR184 / RCTP -> RJAA / B78X)")

    # -------------------------------------------------------------
    # 測試情境二：人機協同授權 -> 自動生成 SimBrief 簽派 (第二輪)
    # -------------------------------------------------------------
    separator("測試 2：人機協同授權 (Human-in-the-Loop) -> 自動 SimBrief 簽派")
    prompt_2 = "好的，幫我直接簽派！"
    print(f"🧑 機長輸入: {prompt_2}\n")
    resp_2 = agent.run(prompt_2, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_2}")

    # 驗證狀態已清除
    assert agent.memory.get_pending() is None, "簽派完成後 Memory 應清空 pending 狀態！"
    assert "BRVA 簽派中心放行成功" in resp_2, "回應中應包含簽派成功訊息！"
    assert "FL370" in resp_2, "應包含巡航高度！"
    assert "ACTIVE DISPATCH" in resp_2, "應包含簽派中心放行狀態！"
    assert "https://www.simbrief.com" not in resp_2, "不應包含外部 SimBrief 網頁連結！"
    print("\n✅ [PASS] 第二輪成功授權並產出完整 BRVA Dispatch Center OFP 放行計畫（無外部雜質連結）！")

    # -------------------------------------------------------------
    # 測試情境三：黑盒子遙測合格紀錄檢測 (PASS)
    # -------------------------------------------------------------
    separator("測試 3：黑盒子遙測紀錄審查 - 合格案例 (sample_flight_pass.csv)")
    prompt_3 = "請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。"
    print(f"🧑 教官輸入: {prompt_3}\n")
    resp_3 = agent.run(prompt_3, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_3}")

    assert "合格 (PASS)" in resp_3, "應評定為合格！"
    assert "合規 ≤1.6G" in resp_3, "接地 G 值應合規！"
    print("\n✅ [PASS] 合格紀錄評審無誤，符合 SOP 標準！")

    # -------------------------------------------------------------
    # 測試情境四：黑盒子遙測違規紀錄檢測 (FAIL: 滑行超速 + 硬著陸一票否決)
    # -------------------------------------------------------------
    separator("測試 4：黑盒子遙測紀錄審查 - 違規案例 (sample_flight_fail.csv)")
    prompt_4 = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"
    print(f"🧑 教官輸入: {prompt_4}\n")
    resp_4 = agent.run(prompt_4, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_4}")

    assert "不合格 (FAIL)" in resp_4, "應評定為不合格！"
    assert "硬著陸 (Hard Landing)" in resp_4, "應精確觸發硬著陸一票否決條款！"
    assert "滑行超速" in resp_4, "應精確抓出地面滑行超速！"
    assert "00:04:12" in resp_4, "應附帶違規發生秒數時間戳！"
    print("\n✅ [PASS] 違規案例精確揪出超速秒數與硬著陸一票否決，零算術幻覺！")

    # -------------------------------------------------------------
    # 測試情境五：異常邊界容錯 (Error Handling & Fallback)
    # -------------------------------------------------------------
    separator("測試 5：邊界容錯測試 (無效 ICAO 代碼與不存在的檔案)")
    print("5.1 測試無效 ICAO 查詢:")
    err_weather = fetch_aviation_weather("INVALID_ICAO")
    print(f"結果: {err_weather}")
    assert err_weather["success"] is False, "無效 ICAO 應回傳結構化錯誤"

    print("\n5.2 測試不存在之黑盒子 CSV:")
    err_telemetry = analyze_flight_telemetry("non_existent_file.csv")
    print(f"結果: {err_telemetry}")
    assert err_telemetry["success"] is False, "檔案不存在應優雅報錯不崩潰"
    print("\n✅ [PASS] 異常邊界處理防護完備，無未捕獲例外！")

    # -------------------------------------------------------------
    # 測試情境六：官方 SOP / 術科考核 / Live 規章 RAG 檢索驗證
    # -------------------------------------------------------------
    separator("測試 6：官方 SOP、術科考核與 Live 機隊規章 RAG 檢索測試")

    # 6.1 SOP 引擎啟動順序與滑行速限
    print("6.1 測試 RAG 檢索雙發噴射客機發動機啟動順序與滑行速限:")
    prompt_6_1 = "請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限規範是多少？"
    print(f"🧑 機師提問: {prompt_6_1}\n")
    resp_6_1 = agent.run(prompt_6_1, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_6_1}")
    assert "2 -> 1" in resp_6_1 or ("2 號" in resp_6_1 and "1 號" in resp_6_1), "應檢索出先啟動 2 號再啟動 1 號！"
    assert "26" in resp_6_1, "應包含直線滑行道 26 節速限！"
    assert "26% N1" in resp_6_1, "應包含起步推力上限 26% N1！"
    assert "SOP 手冊" in resp_6_1, "應清楚引用長榮虛擬航空 SOP 手冊來源章節！"
    print("\n✅ [PASS] 6.1 SOP 引擎啟動順序 (2->1) 與滑行速限 (26/12/10 kts, 26% N1) 精確檢索！")

    # 6.2 術科實作考核一票否決失格標準
    print("\n6.2 測試 RAG 檢索術科實作檢定考核及格標準與一票否決條款:")
    prompt_6_2 = "請問術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？及格門檻是多少？"
    print(f"🧑 考生提問: {prompt_6_2}\n")
    resp_6_2 = agent.run(prompt_6_2, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_6_2}")
    assert "80%" in resp_6_2, "應包含 80% 最低及格門檻！"
    assert "1.6G" in resp_6_2, "應包含接地過載 > 1.6G 一票否決！"
    assert "彈跳落地" in resp_6_2 or "Bounced" in resp_6_2, "應包含彈跳落地一票否決！"
    assert "EVA 000BR" in resp_6_2, "應明確包含考核專屬呼號 EVA 000BR！"
    print("\n✅ [PASS] 6.2 術科檢定及格標準 (80%) 與重大違規一票否決 (1.6G, 彈跳, 衝出跑道) 精確檢索！")

    # 6.3 LIVE 機隊預約上限與 3 小時墜機通報時限
    print("\n6.3 測試 RAG 檢索 LIVE 機隊航機預約上限、Wait Landing 與墜機通報時限:")
    prompt_6_3 = "請問 LIVE 機隊每位機師最多可以預約幾架飛機？若發生墜機事故需要在多久內通報？"
    print(f"🧑 機長提問: {prompt_6_3}\n")
    resp_6_3 = agent.run(prompt_6_3, verbose=True)
    print(f"\n🤖 Agent 回應:\n{resp_6_3}")
    assert "3 架" in resp_6_3, "應包含最多預約 3 架航機席位！"
    assert "3 小時" in resp_6_3, "應包含事故後 3 小時內通報！"
    assert "Wait Landing" in resp_6_3, "應包含 Wait Landing 斷線落地保護機制！"
    print("\n✅ [PASS] 6.3 LIVE 機隊認領上限 (3 架) 與墜機 3 小時通報時限精確檢索！")

    separator("🎉 全部 6 大測試情境 100% 通過！ReAct + 4大工具 + 官方規章 RAG 運作完全正常！")

if __name__ == "__main__":
    run_e2e_tests()

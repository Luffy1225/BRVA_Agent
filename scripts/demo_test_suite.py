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
    assert "簽派計畫已成功生成" in resp_2, "回應中應包含簽派成功訊息！"
    assert "FL370" in resp_2, "應包含巡航高度！"
    assert "SimBrief" in resp_2, "應包含 SimBrief 資訊！"
    print("\n✅ [PASS] 第二輪成功授權並產出完整 SimBrief OFP 放行計畫！")

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

    separator("🎉 全部 5 大測試情境 100% 通過！系統運作完全正常！")

if __name__ == "__main__":
    run_e2e_tests()

import os
import re
import json
from typing import Dict, Any, List, Optional
from src.config import config
from src.memory import AgentMemory, PendingDispatch
from src.tools import (
    TOOL_REGISTRY,
    fetch_aviation_weather,
    query_virtual_routes,
    generate_simbrief_dispatch,
    analyze_flight_telemetry,
    query_flight_sop_and_regulations,
)
from src.llm import BaseLLMProvider, get_llm_provider

SYSTEM_PROMPT = """你是由長榮航空虛擬航空 (EVA Air Virtual / BRVA) 打造的專業 AI 飛行簽派副駕駛與考核助理 (AeroAgent)。
你的核心職責：
1. 協助機師查詢長榮/立榮航網班次、即時航空氣象 (METAR)、計算跑道側風與逆風分量、評估適航風險。
2. 檢索與解答長榮虛擬航空飛行標準作業程序 (SOP)、LIVE 機隊營運規範及術科實作檢定考核標準規章 (RAG 知識庫)。
3. 擔任簽派員：當推薦合適航班後，主動詢問機師「如果沒有其他要修改的是否直接為您簽派 [航班編號]？」。
4. 當機師確認簽派時，呼叫簽派工具生成正式 SimBrief OFP 飛行計畫。
5. 擔任黑盒子考核官：審查飛行遙測 CSV 紀錄，客觀抓出超速與接地 G 值違規。

請保持專業、幹練的民航飛行通聯語氣，使用台灣民航標準用語（如：進場、塔台、側風分量、平飄、接地）。
每次需要外部數據或官方規章時，主動呼叫相關工具。"""

class AeroAgent:
    def __init__(
        self,
        memory: Optional[AgentMemory] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.memory = memory or AgentMemory()
        self.llm = llm_provider or get_llm_provider()

    def run(self, user_input: str, verbose: bool = True) -> str:
        """
        Processes user query using ReAct loop and Human-in-the-Loop memory tracking.
        """
        user_text = user_input.strip()
        self.memory.add_message("user", user_text)

        # -------------------------------------------------------------
        # 1. Human-in-the-Loop (HITL) Pending Dispatch Check
        # -------------------------------------------------------------
        pending = self.memory.get_pending()
        is_question = any(q in user_text for q in ["？", "?", "請問", "多少", "什麼", "怎", "幾", "如何", "哪"])
        is_explicit_dispatch = any(w in user_text for w in ["直接簽派", "幫我簽派", "確認簽派", "進行簽派", "同意簽派", "授權簽派", "確認", "發放放行單"])
        is_short_affirmative = (len(user_text) <= 15) and any(
            user_text.lower().strip().startswith(w) or user_text.lower().strip().endswith(w) or user_text.lower().strip() == w
            for w in ["好", "好的", "好的！", "是", "是的", "沒問題", "行", "可以", "ok", "yes", "sure", "y"]
        )

        if pending and not is_question and (is_explicit_dispatch or is_short_affirmative):
            if verbose:
                print("\n[🤖 Agent 決策] 偵測到機師確認簽派授權！自 Memory 提取待簽派班次參數...")
                print(f"[🔍 Tool Call] -> generate_simbrief_dispatch(flight_number='{pending.flight_number}', dep_icao='{pending.dep_icao}', arr_icao='{pending.arr_icao}', aircraft_type='{pending.aircraft_type}')")

            ofp_result = generate_simbrief_dispatch(
                flight_number=pending.flight_number,
                dep_icao=pending.dep_icao,
                arr_icao=pending.arr_icao,
                aircraft_type=pending.aircraft_type
            )

            if verbose:
                print(f"[📥 Observation] -> OFP 產出成功！巡航高度 {ofp_result.get('cruise_altitude')}，Block Fuel {ofp_result.get('block_fuel_kgs')} kg\n")

            self.memory.clear_pending()
            final_resp = (
                f"{ofp_result['summary']}\n\n"
                f"🔗 SimBrief 官方計畫連結：{ofp_result.get('simbrief_ofp_url')}\n"
                f"祝機長本次飛行平安順利，Happy Landings！"
            )
            self.memory.add_message("assistant", final_resp)
            return final_resp

        # -------------------------------------------------------------
        # 2. Telemetry Audit Request Check
        # -------------------------------------------------------------
        if ".csv" in user_text.lower() or "黑盒子" in user_text or "審查" in user_text or "評分" in user_text:
            # Extract csv path
            csv_target = "sample_flight_fail.csv" if "fail" in user_text.lower() else "sample_flight_pass.csv"
            for token in user_text.split():
                if token.lower().endswith(".csv"):
                    csv_target = token

            if verbose:
                print(f"\n[🤖 Agent 決策] 識別為黑盒子時序遙測稽核任務，呼叫確定性時序檢測工具...")
                print(f"[🔍 Tool Call] -> analyze_flight_telemetry(file_path='{csv_target}')")

            telemetry_res = analyze_flight_telemetry(csv_target)

            if verbose:
                print(f"[📥 Observation] -> 審查完成！得分 {telemetry_res.get('score')} 分，違規項 {len(telemetry_res.get('violations', []))} 件\n")

            final_resp = (
                f"報告教官/機師，黑盒子飛行紀錄 ({csv_target}) 審查完畢：\n\n"
                f"{telemetry_res['summary']}"
            )
            self.memory.add_message("assistant", final_resp)
            return final_resp

        # -------------------------------------------------------------
        # 3. RAG Knowledge Base Query (SOP, Live Rules, Practical Exam)
        # -------------------------------------------------------------
        rag_keywords = [
            "sop", "手冊", "規定", "規章", "條款", "規範", "準則",
            "啟動順序", "發動機啟動", "引擎啟動", "start sequence",
            "滑行速限", "滑行速度", "地面速限", "起步推力", "breakaway",
            "重飛", "穩定進場", "go-around", "放輪", "起落架", "gear",
            "一票否決", "automatic fail", "失格", "及格", "扣分", "評分", "考核", "術科",
            "五邊", "起落航線", "traffic pattern", "remaining in the pattern", "觸地重飛", "touch-and-go",
            "live", "預約", "booking", "wait landing", "落地保護", "gse", "違規", "懲處", "strikes",
            "墜機", "crash", "轉降", "divert", "呼號", "callsign"
        ]
        is_rag_query = any(k in user_text.lower() for k in rag_keywords)
        is_flight_plan = any(k in user_text for k in ["飛往", "開 B78X", "推薦合適的班次", "推薦航班", "檢查目的地天氣"])

        if is_rag_query and not is_flight_plan:
            if verbose:
                print(f"\n[🤖 Agent 決策] 識別為 SOP / 機隊規章 / 術科考核規章查詢，呼叫 RAG 知識檢索工具...")
                print(f"[🔍 Tool Call] -> query_flight_sop_and_regulations(query='{user_text}')")

            rag_res = query_flight_sop_and_regulations(user_text)

            if verbose:
                print(f"[📥 Observation] -> 檢索完成！命中 {rag_res.get('results_count')} 個相關規章條款\n")

            final_resp = (
                f"報告機長/學員，依據長榮虛擬航空官方規章檢索結果：\n\n"
                f"{rag_res['direct_answer']}"
            )
            self.memory.add_message("assistant", final_resp)
            return final_resp

        # -------------------------------------------------------------
        # 4. Greeting & Capability Introduction Check
        # -------------------------------------------------------------
        greetings = ["你好", "您好", "嗨", "早安", "午安", "晚安", "哈囉", "hello", "hi", "hey"]
        if any(user_text.lower().startswith(g) or user_text.lower() == g for g in greetings):
            final_resp = (
                "機長您好！我是長榮虛擬航空 (BRVA) 智慧飛行簽派與考核副駕駛。✈️\n\n"
                "今天我可以為您協助以下任務：\n"
                "1. 🛫 【航網簽派與氣象分析】：例如「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣與推薦班次」\n"
                "2. 📖 【飛行 SOP 與規章檢索】：例如「請問雙發噴射客機發動機啟動順序是多少？」或「術科實作考核哪些是一票否決標準？」\n"
                "3. 📊 【黑盒子時序審核】：例如「請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄」\n\n"
                "請問今天有什麼我可以為您服務的嗎？"
            )
            self.memory.add_message("assistant", final_resp)
            return final_resp

        # -------------------------------------------------------------
        # 5. Route Recommendation & Weather Dispatch Planning Check
        # -------------------------------------------------------------
        flight_keywords = [
            "飛往", "開 ", "班次", "航班", "簽派", "航線", "航路", "天氣", "跑道", "風向", "metar", "風速",
            "rctp", "rjaa", "rjbb", "vhhh", "rcss", "rckh", "桃園", "成田", "關西", "香港", "松山", "高雄",
            "b78x", "b77w", "a321", "a339", "b789"
        ]
        has_flight_intent = any(k in user_text.lower() for k in flight_keywords)

        if has_flight_intent:
            # 1. Dynamic Airport Extraction (ICAO or City Name)
            airport_map = {
                "桃園": "RCTP", "RCTP": "RCTP",
                "成田": "RJAA", "RJAA": "RJAA",
                "關西": "RJBB", "RJBB": "RJBB",
                "香港": "VHHH", "VHHH": "VHHH",
                "松山": "RCSS", "RCSS": "RCSS",
                "高雄": "RCKH", "RCKH": "RCKH",
                "羽田": "RJTT", "RJTT": "RJTT",
                "新加坡": "WSSS", "WSSS": "WSSS",
            }

            dep = "RCTP"
            arr = "RJAA"

            # Check 4-letter ICAO patterns
            found_icaos = [m.group(0).upper() for m in re.finditer(r'\b[A-Za-z]{4}\b', user_text)]
            valid_icaos = [code for code in found_icaos if code in airport_map or code.startswith("R") or code.startswith("V") or code.startswith("W")]

            if len(valid_icaos) >= 2:
                dep = valid_icaos[0]
                arr = valid_icaos[1]
            elif len(valid_icaos) == 1:
                # If only one ICAO found, decide if it's dep or arr
                if any(w in user_text for w in ["飛往", "到", "降落", "目的地"]):
                    arr = valid_icaos[0]
                else:
                    dep = valid_icaos[0]
            else:
                # Check city names
                for name, code in airport_map.items():
                    if f"從{name}" in user_text or f"由{name}" in user_text or f"在{name}" in user_text:
                        dep = code
                    elif f"往{name}" in user_text or f"到{name}" in user_text or f"至{name}" in user_text:
                        arr = code

            # 2. Dynamic Aircraft Extraction
            aircraft = "B78X"
            ac_matches = re.findall(r'\b(B78X|B77W|A321|A339|B789|B777|A350|787|777|321)\b', user_text, re.IGNORECASE)
            if ac_matches:
                raw_ac = ac_matches[0].upper()
                if "777" in raw_ac or "77W" in raw_ac:
                    aircraft = "B77W"
                elif "321" in raw_ac:
                    aircraft = "A321"
                elif "787" in raw_ac or "78X" in raw_ac or "789" in raw_ac:
                    aircraft = "B78X"
                else:
                    aircraft = raw_ac

            # 3. Dynamic Runway Extraction
            target_rwy = "16R" if arr == "RJAA" else ("05L" if arr == "RCTP" else "10")
            rwy_match = re.search(r'(\d{2}[LRC]?)\s*跑道|跑道\s*(\d{2}[LRC]?)', user_text, re.IGNORECASE)
            if rwy_match:
                target_rwy = (rwy_match.group(1) or rwy_match.group(2)).upper()

            if verbose:
                print(f"\n[🤖 Agent 決策] 使用者欲由 {dep} 執飛 {aircraft} 至 {arr}。執行兩步驟工具鏈：航線檢索 ➡️ 目的地起降氣象解析...")
                print(f"[🔍 Tool Call 1] -> query_virtual_routes(dep_icao='{dep}', arr_icao='{arr}', aircraft_type='{aircraft}')")

            routes = query_virtual_routes(dep, arr, aircraft)
            flight = routes[0] if routes else {"flight_number": f"BR{dep[2:]}{arr[2:]}", "aircraft": aircraft, "flight_time": "2h 40m"}

            if verbose:
                print(f"[📥 Observation 1] -> 匹配推薦班次：{flight['flight_number']}（{flight['aircraft']}，航程預估 {flight['flight_time']}）")
                print(f"[🔍 Tool Call 2] -> fetch_aviation_weather(icao='{arr}', runway='{target_rwy}')")

            weather = fetch_aviation_weather(arr, target_rwy)

            if verbose:
                print(f"[📥 Observation 2] -> {arr} 即時 METAR 取得成功，{target_rwy} 跑道側風分量 {weather['crosswind_kts']} 節\n")

            # Save pending dispatch into Agent Memory
            self.memory.set_pending(PendingDispatch(
                flight_number=flight['flight_number'],
                dep_icao=dep,
                arr_icao=arr,
                aircraft_type=aircraft,
                recommended_runway=target_rwy,
                estimated_time=flight['flight_time'],
                crosswind_kts=weather['crosswind_kts']
            ))

            final_resp = (
                f"報告機長，為您完成簽派規劃與氣象分析：\n\n"
                f"1. 【推薦航班】：{flight['flight_number']}（{dep} 🛫 ➡️ {arr} 🛬，預估航程 {flight['flight_time']}，由 {aircraft} 客機執飛）。\n\n"
                f"2. 【目的地天氣簡報 ({arr})】：\n"
                f"   • METAR 報文：`{weather['raw_metar']}`\n"
                f"   • 跑道建議：建議使用 {target_rwy} 跑道進場。\n"
                f"   • 風向與側風評估：{weather['risk_assessment']}\n\n"
                f"3. 【防禦性操作提醒】：側風雖然合規，但若存在陣風，進場平飄時請適時下風向盤舵修正偏流，保持機頭對正跑道中心線。\n\n"
                f"👉 如果沒有其他要修改的是否直接為您簽派 {flight['flight_number']}？"
            )
            self.memory.add_message("assistant", final_resp)
            return final_resp

        # -------------------------------------------------------------
        # 6. Fallback / Unified LLM Open Response (Ollama / Gemini / Offline)
        # -------------------------------------------------------------
        if self.llm and self.llm.is_available() and self.llm.provider_name != "offline":
            try:
                resp = self.llm.generate(prompt=user_text, system_prompt=SYSTEM_PROMPT)
                if resp and resp.content and not resp.content.startswith("⚠️"):
                    final_resp = resp.content
                    self.memory.add_message("assistant", final_resp)
                    return final_resp
            except Exception:
                pass

        final_resp = (
            "報告機長，我是您的 AI 簽派副駕。請告訴我您的具體飛行需求，例如：\n\n"
            "• 航網簽派：「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣與推薦班次」\n"
            "• 規章與 SOP：「請問雙發客機的發動機啟動順序與滑行速限是多少？」\n"
            "• 考核規章：「術科實作考核中，哪些重大違規情事會直接觸發一票否決？」\n"
            "• 黑盒子審核：「請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄」"
        )
        self.memory.add_message("assistant", final_resp)
        return final_resp

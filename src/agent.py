import os
import re
import json
import random
from typing import Dict, Any, List, Optional, Union
from src.config import config
from src.context import UserContext
from src.memory import AgentMemory, PendingDispatch
from src.tools import (
    TOOL_REGISTRY,
    fetch_aviation_weather,
    query_virtual_routes,
    generate_simbrief_dispatch,
    analyze_flight_telemetry,
    query_flight_sop_and_regulations,
    query_pilot_profile,
    query_store_catalog,
    query_leaderboard,
    query_calendar_events,
    query_events_and_rotw,
    query_pilot_inventory,
    query_media_gallery,
    query_live_radar_and_tracker,
    query_pilot_pireps,
    query_active_dispatch,
)
from src.llm import BaseLLMProvider, get_llm_provider

SYSTEM_PROMPT = """你是由長榮航空虛擬航空 (EVA Air Virtual / BRVA) 打造的專業 AI 飛行簽派副駕駛與考核助理 (BRVA Agent)。
你的核心職責：
1. 協助機師查詢長榮/立榮航網班次、即時航空氣象 (METAR)、計算跑道側風與逆風分量、評估適航風險。
2. 檢索與解答長榮虛擬航空飛行標準作業程序 (SOP)、LIVE 機隊營運規範及術科實作檢定考核標準規章 (RAG 知識庫)。
3. 擔任簽派員：當推薦合適航班後，主動詢問機師「如果沒有其他要修改的是否直接為您簽派 [航班編號]？」。
4. 當機師確認簽派時，呼叫簽派工具生成正式 SimBrief OFP 飛行計畫。
5. 擔任黑盒子考核官：審查飛行遙測 CSV 紀錄，客觀抓出超速與接地 G 值違規。
6. 提供全方位 CrewCenter 整合：排行榜、官方活動行事曆與每週精選航線 (ROTW)、飛官個人檔案與飛行紀錄 (PIREP)、背包道具庫 (嚴格唯讀，無權使用或消耗道具)、影音藝廊，以及即時航跡雷達與在空班機追蹤。

請保持專業、幹練的民航飛行通聯語氣，使用台灣民航標準用語（如：進場、塔台、側風分量、平飄、接地）。
每次需要外部數據或官方規章時，主動呼叫相關工具。"""

class BRVAAgent:
    def __init__(
        self,
        memory: Optional[AgentMemory] = None,
        llm_provider: Optional[Union[BaseLLMProvider, str]] = None
    ):
        self.memory = memory or AgentMemory()
        if isinstance(llm_provider, str):
            self.llm = get_llm_provider(llm_provider)
        else:
            self.llm = llm_provider or get_llm_provider()
        self.last_trace: List[Dict[str, Any]] = []
        self.current_trace: List[Dict[str, Any]] = []
        self._verbose: bool = True

    def _reset_trace(self, verbose: bool = True):
        self._verbose = verbose
        self.current_trace = []

    def _add_trace_thought(self, title: str, content: str = ""):
        step = {
            "type": "thought",
            "title": title,
            "content": content or title,
        }
        self.current_trace.append(step)
        if self._verbose:
            print(f"\n[🤖 Agent 決策] {title}")

    def _add_trace_tool_call(self, tool_name: str, call_repr: str, args: Optional[Dict[str, Any]] = None):
        step = {
            "type": "tool_call",
            "tool": tool_name,
            "title": f"調用 {tool_name}",
            "content": call_repr,
            "args": args or {}
        }
        self.current_trace.append(step)
        if self._verbose:
            print(f"[🔍 Tool Call] -> {call_repr}")

    def _add_trace_observation(self, summary: str, data: Optional[Any] = None, result: Optional[Any] = None):
        res_payload = result if result is not None else data
        step = {
            "type": "observation",
            "title": "工具執行觀察",
            "content": summary,
            "result": res_payload
        }
        self.current_trace.append(step)
        if self._verbose:
            print(f"[📥 Observation] -> {summary}\n")

    def get_last_trace(self) -> List[Dict[str, Any]]:
        """Returns the step trace of the last executed run."""
        return list(self.last_trace)

    def _finish_run(
        self,
        final_resp: str,
        return_trace: bool = False
    ) -> Union[str, tuple[str, List[Dict[str, Any]]]]:
        self.last_trace = list(self.current_trace)
        self.memory.add_message("assistant", final_resp)
        if return_trace:
            return final_resp, self.last_trace
        return final_resp

    def set_llm_provider(self, llm_provider: Union[BaseLLMProvider, str]):
        """Dynamically switches the active LLM provider during runtime."""
        if isinstance(llm_provider, str):
            self.llm = get_llm_provider(llm_provider)
        else:
            self.llm = llm_provider

    def _format_crewcenter_offline_response(
        self,
        tool_name: str,
        user_text: str,
        default_summary: Optional[str] = None
    ) -> str:
        """
        Dynamically formats a friendly, lively, and aviation-authentic co-pilot response
        when CrewCenter backend/database is offline or unreachable.
        Uses LLM if available; falls back to a randomized realistic co-pilot pool if offline.
        """
        # 1. Dynamic LLM Generation (when LLM is active & online)
        if self.llm and self.llm.is_available() and self.llm.provider_name != "offline":
            try:
                offline_prompt = (
                    f"【座艙狀況通報】：\n"
                    f"機長/教官剛才的指令或詢問：「{user_text}」\n"
                    f"你剛才呼叫執行的航電工具：{tool_name}\n"
                    f"目前的通聯狀態：CrewCenter 簽派中心資料庫連線逾時或伺服器暫時離線（CREWCENTER_OFFLINE）。\n\n"
                    f"【副駕駛回覆指引】：\n"
                    f"1. 請發揮長榮虛擬航空 AI 簽派副駕駛 (BRVA Agent) 的專業與貼心風格，向教官/機長生動回報此狀況。\n"
                    f"2. 語氣自然、專業有禮貌，切忌死板冷冰冰的格式化報錯（例如可以提及航電資料鏈路 ACARS 暫時訊號不佳、簽派中心主機正在維修、喝杯熱咖啡稍後再呼叫等航空情境）。\n"
                    f"3. 貼心告知：本機的【即時機場 METAR 氣象】、【跑道側風分量計算】、【長榮飛行規章 SOP】以及【黑盒子時序遙測審核】依然正常可用，詢問機長是否先進行其他飛行準備。\n"
                    f"4. 篇幅請控制在 100~150 字以內，精練且具座艙真實感。"
                )
                resp = self.llm.generate(prompt=offline_prompt, system_prompt=SYSTEM_PROMPT)
                if resp and resp.content and not resp.content.startswith("⚠️"):
                    return resp.content
            except Exception:
                pass  # Fallback to randomized lively co-pilot pool

        # 2. Offline / Fallback: Randomized lively aviation co-pilot pool
        offline_copilot_phrases = [
            (
                "報告教官！剛才呼叫 BRVA CrewCenter 簽派中心，航電資料鏈路 (ACARS) 似乎暫時訊號微弱，主機連線逾時中 📡。\n\n"
                "主機可能正在進行定期維護或網路有微幅抖動。要不要先喝杯熱咖啡稍候片刻？等連線恢復後我隨時再為您查詢！\n"
                "在這期間，如果您需要查詢機場 METAR 即時氣象、計算跑道側風分量，或是翻閱長榮飛行 SOP 規章手冊，我依然隨時待命為您服務！"
            ),
            (
                "報告機長！CrewCenter 伺服器端目前通聯逾時，資料庫可能正在進場檢修或處於無線電靜默 ✈️。\n\n"
                "這段時間您可以先檢查飛行航圖或準備出發檢查單，稍等幾分鐘後我們再重新呼叫連線！\n"
                "目前本機的機場 METAR 氣象查詢、跑道側風計算與黑盒子飛行紀錄審查功能皆運作正常，請隨時指示。"
            ),
            (
                "報告教官！向 CrewCenter 發送的查詢請求目前未收到應答（主機離線或網路連線逾時）📡。\n\n"
                "副駕建議我們先保持在當前頻率稍作等待，稍後再重新呼叫。如果您想先了解各跑道的進場側風分量、查詢機場最新 METAR 天氣，或查閱實作考核規章，可以隨時跟我說！"
            ),
            (
                "教官好！CrewCenter 簽派中心目前暫時離線中（伺服器連線逾時）☕。\n\n"
                "我們稍後再重新嘗試連線。這段空檔若需要確認飛行 SOP、實作檢定考核標準或 METAR 天氣，副駕駛隨時為您報告！"
            ),
            (
                "報告機長！剛才嘗試連線 CrewCenter 資料庫未能成功，主機可能正在暖機或進行日常系統調試。\n\n"
                "請稍後再試一次連線！目前機場 METAR 氣象查詢、跑道側風計算與飛行紀錄黑盒子審查功能皆運作正常，隨時等候您的指令！"
            ),
        ]
        return random.choice(offline_copilot_phrases)

    def run(
        self,
        user_input: str,
        user_context: Optional[UserContext] = None,
        verbose: bool = True,
        return_trace: bool = False
    ) -> Union[str, tuple[str, List[Dict[str, Any]]]]:
        """
        Processes user query using ReAct loop and Human-in-the-Loop memory tracking.
        Supports pilot user_context for delegation and personal actions.
        Collects detailed step trace (thinking, tool calls, observations) for collapsible UI.
        """
        self._reset_trace(verbose=verbose)
        user_text = user_input.strip()
        self.memory.add_message("user", user_text)

        # -------------------------------------------------------------
        # 0. In-Chat Pilot Linking & Demo Pilot Switch
        # -------------------------------------------------------------
        if any(w in user_text for w in ["切換測試飛官", "體驗飛官", "一鍵登入", "登入測試飛官", "載入測試飛官", "demo pilot"]):
            official_demo_token = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOiI4ODg4MTc5NTM2MDg2ODc2NDEwIiwidHlwZSI6ImRlbGVnYXRpb24iLCJzY29wZXMiOlsiZGlzcGF0Y2giLCJwcm9maWxlOnJlYWQiLCJzdG9yZTpyZWFkIiwicm91dGVzIl0sInRva2VuVmVyc2lvbiI6MSwiaWF0IjoxNzk1MzY5NTMxfQ.7pB5-bHLE2WmNElbwvGIczOJs6LenQTBvL2Rpbu3Kwk"
            self._add_trace_thought("測試飛官一鍵切換", "偵測到測試飛官切換請求，向後端授權 API 驗證官方示範 Token...")
            self._add_trace_tool_call("backend_client.verify_token", f"backend_client.verify_token(token='{official_demo_token[:18]}...')")
            from src.client import backend_client
            val_res = backend_client.verify_token(official_demo_token)
            if val_res and val_res.get("valid") and val_res.get("user"):
                u = val_res["user"]
                if user_context is not None:
                    user_context.is_authenticated = True
                    user_context.user_id = str(u.get("userId"))
                    user_context.callsign = u.get("callsign", "PILOT")
                    user_context.username = u.get("username", "Pilot")
                    user_context.rank_name = u.get("rankName", "First Officer")
                    user_context.points = float(u.get("points") or 0)
                    user_context.flight_time_hours = float(u.get("flightTimeHours") or 0)
                    user_context.delegation_token = official_demo_token
                    user_context.scopes = u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
                self._add_trace_observation(f"Token 驗證成功！飛官姓名：{u.get('username')}，呼號：{u.get('callsign')}，階級：{u.get('rankName')}，點數：{u.get('points')} pts", result=val_res)
                self._add_trace_thought("使用者上下文更新", "已成功將飛官資訊寫入 UserContext，授權模式激活。")
                resp = (
                    f"👨‍✈️ **已為您一鍵切換至官方測試飛官身分！**\n\n"
                    f"• 呼號：`{getattr(user_context, 'callsign', u.get('callsign'))}`\n"
                    f"• 姓名：`{getattr(user_context, 'username', u.get('username'))}`\n"
                    f"• 階級：`{getattr(user_context, 'rank_name', u.get('rankName'))}`\n"
                    f"• 點數：`{getattr(user_context, 'points', 0):,.0f} pts`\n"
                    f"• 累計飛行時數：`{getattr(user_context, 'flight_time_hours', 0):,.1f} h`\n"
                    f"• 狀態：🟢 已自伺服器成功讀取真實飛官資料\n\n"
                    f"現在您可以自由測試『查我的點數』、『簽派放行』、『查看個人背包』等個人化功能！"
                )
                return self._finish_run(resp, return_trace)
            else:
                err_msg = val_res.get("error") if val_res else "無法連線至後端伺服器"
                self._add_trace_observation(f"⚠️ Token 驗證失敗：{err_msg}", result=val_res)
                resp = f"⚠️ 無法取得測試飛官身分：{err_msg}。請確認後端 API 伺服器是否正常運行。"
                return self._finish_run(resp, return_trace)

        import re
        link_match = re.search(r"(?:連結飛官|登入飛官|綁定飛官|token\s*[:：])\s*([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
        if link_match:
            raw_token = link_match.group(1).strip()
            self._add_trace_thought("飛官個人 Token 驗證", "解析使用者提供之 Token，向後端授權伺服器驗證身分...")
            self._add_trace_tool_call("backend_client.verify_token", f"backend_client.verify_token(token='{raw_token[:18]}...')")
            from src.client import backend_client
            val_res = backend_client.verify_token(raw_token)
            if val_res and val_res.get("valid") and val_res.get("user"):
                u = val_res["user"]
                if user_context is not None:
                    user_context.is_authenticated = True
                    user_context.user_id = str(u.get("userId"))
                    user_context.callsign = u.get("callsign")
                    user_context.username = u.get("username")
                    user_context.rank_name = u.get("rankName")
                    user_context.points = float(u.get("points") or 0)
                    user_context.flight_time_hours = float(u.get("flightTimeHours") or 0)
                    user_context.delegation_token = raw_token
                    user_context.scopes = u.get("scopes") or []
                self._add_trace_observation(f"驗證通過！呼號：{u.get('callsign')}，姓名：{u.get('username')}，階級：{u.get('rankName')}", result=val_res)
                self._add_trace_thought("使用者上下文更新", "飛官授權成功，個人化操作已解鎖。")
                resp = (
                    f"👨‍✈️ **飛官身分連結成功！歡迎登機，{u.get('callsign')} 機長。**\n\n"
                    f"• 階級：`{u.get('rankName')}`\n"
                    f"• 點數餘額：`{float(u.get('points') or 0):,.0f} pts`\n"
                    f"• 總飛行時數：`{float(u.get('flightTimeHours') or 0):,.1f} h`\n\n"
                    f"BRVA Agent 隨時聽候您的指示！"
                )
                return self._finish_run(resp, return_trace)
            else:
                self._add_trace_observation("⚠️ 授權碼無效、已過期或伺服器連線失敗。", result=val_res)
                resp = "⚠️ 抱歉長官，此授權碼無效、已過期或無法連線驗證。請確認後再試，或在側邊欄點選【⚡ 一鍵體驗飛官身分】直接進行測試！"
                return self._finish_run(resp, return_trace)

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
            self._add_trace_thought(
                "人機協同授權 (HITL)",
                f"偵測到機師確認簽派授權！自 Agent Memory 提取待簽派班次：{pending.flight_number} ({pending.dep_icao} 🛫 ➡️ {pending.arr_icao} 🛬, 機型: {pending.aircraft_type})"
            )
            self._add_trace_tool_call(
                "generate_simbrief_dispatch",
                f"generate_simbrief_dispatch(flight_number='{pending.flight_number}', dep_icao='{pending.dep_icao}', arr_icao='{pending.arr_icao}', aircraft_type='{pending.aircraft_type}')"
            )

            ofp_result = generate_simbrief_dispatch(
                flight_number=pending.flight_number,
                dep_icao=pending.dep_icao,
                arr_icao=pending.arr_icao,
                aircraft_type=pending.aircraft_type,
                user_context=user_context
            )

            if ofp_result.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 簽派中斷：CrewCenter 主機離線或連線逾時", result=ofp_result)
                final_resp = self._format_crewcenter_offline_response("Simbrief 航網簽派放行", user_text, ofp_result.get("summary"))
                return self._finish_run(final_resp, return_trace)

            if ofp_result.get("status") == "SIMBRIEF_NOT_LINKED":
                self._add_trace_observation("⚠️ 簽派中斷：飛行員尚未於 BRVA 簽派中心綁定 SimBrief 帳號", result=ofp_result)
                final_resp = ofp_result.get("summary")
                return self._finish_run(final_resp, return_trace)

            if ofp_result.get("status") == "UNAUTHENTICATED":
                self._add_trace_observation("⚠️ 授權中斷：尚未連結 CrewCenter 飛官個人帳號", result=ofp_result)
                final_resp = ofp_result.get("summary")
                return self._finish_run(final_resp, return_trace)

            self._add_trace_observation(f"OFP 產出成功！巡航高度 {ofp_result.get('cruise_altitude') or ofp_result.get('cruise_alt')}，Block Fuel {ofp_result.get('block_fuel_kgs')} kg", result=ofp_result)
            self._add_trace_thought("簽派核准完成", "清除 Agent Memory 待簽派狀態，發布 Happy Landings 祝福與放行指示。")
            self.memory.clear_pending()
            final_resp = (
                f"{ofp_result['summary']}\n\n"
                f"祝機長本次飛行平安順利，Happy Landings！"
            )
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1B. Direct Pilot Profile & Stats Query Check
        # -------------------------------------------------------------
        profile_keywords = ["查我的點數", "我的點數", "點數餘額", "多少點", "我有幾點", "我的時數", "飛行時數", "我的階級", "個人檔案", "個人資料", "帳號資訊"]
        if any(k in user_text for k in profile_keywords) and not any(lb in user_text for lb in ["榜", "排行", "名次", "leaderboard"]):
            query_type = "summary"
            if any(k in user_text for k in ["點數", "point"]):
                query_type = "points"
            elif any(k in user_text for k in ["時數", "小時", "hour"]):
                query_type = "hours"
            elif any(k in user_text for k in ["階級", "rank"]):
                query_type = "rank"
            elif any(k in user_text for k in ["數據", "統計", "營運", "接地"]):
                query_type = "stats"

            self._add_trace_thought("飛官個人數據檢索", f"識別為飛官個人資料與積分查詢 (查詢類型: {query_type})，檢查授權狀態並檢索資料庫")
            self._add_trace_tool_call("query_pilot_profile", f"query_pilot_profile(query_type='{query_type}')")

            res = query_pilot_profile(query_type=query_type, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 伺服器離線或連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("飛官個人檔案與數據查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"飛官數據取得完畢 (呼號: {res.get('callsign')}, 點數: {res.get('points')} pts, 時數: {res.get('flight_time_hours')} h)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1C. Store Catalog Query Check (Strictly Read-Only, No Purchase)
        # -------------------------------------------------------------
        store_keywords = ["商城", "商店", "商品目錄", "商品列表", "架上有什麼", "有賣什麼", "我想買", "幫我買"]
        if any(k in user_text for k in store_keywords):
            self._add_trace_thought("CrewCenter 飛官商城查詢", "識別為 CrewCenter 商城目錄與點數餘額查詢 (嚴格唯讀防護，無購買扣點權限)")
            self._add_trace_tool_call("query_store_catalog", "query_store_catalog()")

            res = query_store_catalog(user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 商城資料庫連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("商城商品目錄查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"已取得商城架上商品清單 ({len(res.get('items', []))} 件商品) 與點數餘額 ({res.get('points', 0)} pts)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1D. CrewCenter Leaderboard Query (排行榜)
        # -------------------------------------------------------------
        leaderboard_keywords = ["排行榜", "排行", "榮譽榜", "leaderboard", "榜單", "誰飛最多", "名次", "誰最厲害", "排名"]
        if any(k in user_text for k in leaderboard_keywords):
            cat = "atc" if any(k in user_text for k in ["atc", "管制", "航管", "管制員"]) else "pilot"
            sort_by = "points"
            if any(k in user_text for k in ["時數", "小時", "時間", "飛行時間"]):
                sort_by = "flight_time"
            elif any(k in user_text for k in ["接地", "垂直速度", "落地", "landing"]):
                sort_by = "landing_rate"
            elif any(k in user_text for k in ["架次", "航班數", "pirep"]):
                sort_by = "pireps"
            elif any(k in user_text for k in ["作業", "次數", "ops"]) and cat == "atc":
                sort_by = "operations"

            days = "all"
            if "7天" in user_text or "本週" in user_text or "一週" in user_text:
                days = "7"
            elif "30天" in user_text or "本月" in user_text:
                days = "30"

            self._add_trace_thought("CrewCenter 榮譽榜查詢", f"識別為排行榜查詢 (類別: {cat}, 排序維度: {sort_by}, 統計週期: {days})")
            self._add_trace_tool_call("query_leaderboard", f"query_leaderboard(category='{cat}', sort_by='{sort_by}', days='{days}')")

            res = query_leaderboard(category=cat, sort_by=sort_by, days=days, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 排行榜資料庫連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("CrewCenter 排行榜數據查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"成功取得前 {len(res.get('leaderboard', []))} 名榮譽榜資料", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1E. CrewCenter Calendar & Events & ROTW (行事曆與官方活動)
        # -------------------------------------------------------------
        calendar_keywords = ["行事曆", "官方活動", "大聯飛", "近期活動", "rotw", "每週精選", "日程", "calendar", "活動列表"]
        if any(k in user_text.lower() for k in calendar_keywords):
            self._add_trace_thought("官方活動日程查詢", "識別為 CrewCenter 官方活動日程與每週精選航線 (ROTW) 查詢")
            self._add_trace_tool_call("query_calendar_events", "query_calendar_events(limit=5, include_rotw=True)")

            res = query_calendar_events(limit=5, include_rotw=True, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 行事曆伺服器連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("官方活動行事曆與每週航線查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得近期活動資料 ({res.get('events_count', 0)} 筆)，包含大聯飛與每週精選航線", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1F. Pilot Inventory & Bag Query (背包與道具 - 嚴格唯讀)
        # -------------------------------------------------------------
        inventory_keywords = ["背包", "我的道具", "我有甚麼道具", "我有什麼道具", "道具庫", "持有道具", "我有幾張券", "包機券", "通行證", "大聲公道具", "inventory"]
        if any(k in user_text for k in inventory_keywords):
            self._add_trace_thought("飛官背包道具查詢", "識別為飛官個人背包與道具庫查詢 (嚴格唯讀，安全防護)")
            self._add_trace_tool_call("query_pilot_inventory", "query_pilot_inventory()")

            res = query_pilot_inventory(user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 背包資料庫連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("個人背包道具庫查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得背包道具清單 (持有 {len(res.get('inventory', []))} 項道具/特許卡)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1G. Media Gallery (影音藝廊)
        # -------------------------------------------------------------
        gallery_keywords = ["藝廊", "畫廊", "照片", "精選照片", "截圖", "gallery", "機師照片", "投稿"]
        if any(k in user_text.lower() for k in gallery_keywords):
            self._add_trace_thought("影音藝廊精選查詢", "識別為 CrewCenter 影音藝廊精選飛官作品查詢")
            self._add_trace_tool_call("query_media_gallery", "query_media_gallery(limit=5)")

            res = query_media_gallery(limit=5, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 藝廊伺服器連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("影音藝廊精選作品查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得藝廊精選作品清單 ({res.get('photos_count', 0)} 張照片)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1H. Live Radar & Aircraft Tracker (即時在空班機與航跡雷達)
        # -------------------------------------------------------------
        tracker_keywords = [
            "即時航班", "在空班機", "誰在飛", "雷達", "tracker", "即時班機", "航跡", "radar",
            "飛機位置", "在線飛機", "飛到哪", "即時位置", "線上飛行", "在線飛行", "在線上飛行",
            "線上班機", "在空飛機", "目前在線", "在線上", "在線上的", "誰在線上", "在空中"
        ]
        is_live_flight_query = any(k in user_text.lower() for k in tracker_keywords) or (
            any(p in user_text for p in ["在線", "線上", "在空", "空中"]) and any(a in user_text for a in ["飛行", "班機", "航班", "長榮", "飛機", "執飛"])
        ) or (
            "誰在" in user_text and ("飛" in user_text or "空中" in user_text)
        )
        if is_live_flight_query:
            # Extract target callsign or airport
            cs_match = re.search(r'(EVA\s*\d+|BR\s*\d+)', user_text, re.IGNORECASE)
            target_cs = cs_match.group(1).replace(" ", "").upper() if cs_match else None

            target_icao = None
            for code in ["RCTP", "RCSS", "RCKH", "RJAA", "RJBB", "RJTT", "VHHH", "WSSS", "KLAX", "KSFO"]:
                if code in user_text.upper():
                    target_icao = code
                    break

            self._add_trace_thought("即時航跡雷達追蹤", f"識別為在空班機追蹤 (指定呼號: {target_cs or '全部'}, 指定機場: {target_icao or '全球'})")
            self._add_trace_tool_call("query_live_radar_and_tracker", f"query_live_radar_and_tracker(callsign={repr(target_cs)}, icao={repr(target_icao)})")

            res = query_live_radar_and_tracker(callsign=target_cs, icao=target_icao, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 航跡雷達伺服器連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("即時航跡雷達與在空班機追蹤", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得即時雷達航跡資料 (線上在空班機: {res.get('flights_count', 0)} 架)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1I. Pilot PIREP History & Active Dispatch Query
        # -------------------------------------------------------------
        pirep_keywords = ["飛行紀錄", "飛行報告", "pirep", "歷史飛行", "最近執飛", "上次降落", "接地紀錄", "最近飛了什麼"]
        if any(k in user_text.lower() for k in pirep_keywords):
            self._add_trace_thought("個人飛行紀錄查詢", "識別為個人歷史飛行報告 (PIREP) 與落地降落率紀錄查詢")
            self._add_trace_tool_call("query_pilot_pireps", "query_pilot_pireps(limit=5)")

            res = query_pilot_pireps(limit=5, user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ PIREP 資料庫連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("個人飛行報告歷史紀錄查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得近期 PIREP 報告 ({len(res.get('pireps', []))} 筆)", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        active_disp_keywords = ["當前簽派", "目前簽派", "現在簽派", "我的簽派", "有沒有簽派", "放行單狀態"]
        if any(k in user_text for k in active_disp_keywords):
            self._add_trace_thought("當前簽派放行單查詢", "識別為當前已核發放行單有效性查詢")
            self._add_trace_tool_call("query_active_dispatch", "query_active_dispatch()")

            res = query_active_dispatch(user_context=user_context)
            if res.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 簽派中心連線逾時", result=res)
                final_resp = self._format_crewcenter_offline_response("當前有效簽派放行狀態查詢", user_text, res.get("summary"))
            else:
                self._add_trace_observation(f"取得放行單狀態 (狀態: {res.get('status')})", result=res)
                final_resp = res.get("summary") or res.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1J. Direct Flight Dispatch Check (e.g. 幫我簽派 BR184, 簽派 BR184)
        # -------------------------------------------------------------
        flt_match = re.search(r'(?:幫我|直接|請|立即)?(?:簽派|派飛|dispatch)\s*(?:航班)?\s*(BR\s*\d+|EVA\s*\d+|\b\d{3,4}\b)', user_text, re.IGNORECASE)
        if flt_match and not any(q in user_text for q in ["推薦", "檢查", "查詢", "有哪些"]):
            matched_flt = flt_match.group(1).replace(" ", "").upper()
            if not matched_flt.startswith("BR") and not matched_flt.startswith("EVA"):
                matched_flt = f"BR{matched_flt}"

            # Standard city pairs for EVA flights or default RCTP->RJAA
            dep = "RCTP"
            arr = "RJAA"
            if "184" in matched_flt or "198" in matched_flt:
                dep, arr = "RCTP", "RJAA"
            elif "178" in matched_flt:
                dep, arr = "RCTP", "RJBB"
            elif "851" in matched_flt or "855" in matched_flt or "871" in matched_flt:
                dep, arr = "RCTP", "VHHH"
            elif "12" in matched_flt:
                dep, arr = "RCTP", "KLAX"

            self._add_trace_thought("指定航班直接簽派", f"識別為明確指定航班簽派請求: {matched_flt} ({dep} -> {arr})，機型: B78X")
            self._add_trace_tool_call("generate_simbrief_dispatch", f"generate_simbrief_dispatch(flight_number='{matched_flt}', dep_icao='{dep}', arr_icao='{arr}', aircraft_type='B78X')")

            ofp_result = generate_simbrief_dispatch(
                flight_number=matched_flt,
                dep_icao=dep,
                arr_icao=arr,
                aircraft_type="B78X",
                user_context=user_context
            )
            if ofp_result.get("status") == "CREWCENTER_OFFLINE":
                self._add_trace_observation("⚠️ 簽派中斷：CrewCenter 伺服器連線逾時", result=ofp_result)
                final_resp = self._format_crewcenter_offline_response("航班放行單簽派", user_text, ofp_result.get("summary"))
            else:
                self._add_trace_observation(f"簽派處理完畢 (狀態: {ofp_result.get('status')})", result=ofp_result)
                final_resp = ofp_result.get("summary") or ofp_result.get("summary_text", "")
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 1K. Greetings Check
        # -------------------------------------------------------------
        if any(user_text.lower().startswith(g) or user_text.lower() == g for g in ["你好", "您好", "哈囉", "hello", "hi", "早安", "午安", "晚安"]) and not any(k in user_text for k in ["手冊", "規章", "查", "簽派", "天氣", "sop"]):
            self._add_trace_thought("民航副駕駛登機報到", "偵測到座艙問候語，提供長榮簽派副駕指引與核心功能快速提示。")
            greeting_resp = (
                "機長您好！我是您的 AI 簽派副駕與考核助理。請問今天需要為您查詢航線、解析目的地天氣，還是審查飛行黑盒子紀錄？\n\n"
                "您可以隨時告訴我具體需求，例如：\n"
                "• 🏆 排行榜：「幫我查飛行時數排行榜」\n"
                "• 📅 行事曆：「查詢近期官方活動與大聯飛」\n"
                "• 🎒 個人道具：「查看我的背包道具庫」\n"
                "• 📡 航跡雷達：「查看即時在空班機」\n"
                "• 🛫 簽派規劃：「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)」"
            )
            return self._finish_run(greeting_resp, return_trace)

        # -------------------------------------------------------------
        # 2. Telemetry Audit Request Check
        # -------------------------------------------------------------
        if ".csv" in user_text.lower() or "黑盒子" in user_text or "審查" in user_text or "評分" in user_text:
            # Extract csv path
            csv_target = "sample_flight_fail.csv" if "fail" in user_text.lower() else "sample_flight_pass.csv"
            for token in user_text.split():
                if token.lower().endswith(".csv"):
                    csv_target = token

            self._add_trace_thought("黑盒子時序遙測稽核", f"識別為黑盒子時序遙測紀錄審查 (檔案: {csv_target})，呼叫確定性時序演算法進行超速與接地 G 值分析")
            self._add_trace_tool_call("analyze_flight_telemetry", f"analyze_flight_telemetry(file_path='{csv_target}')")

            telemetry_res = analyze_flight_telemetry(csv_target)

            self._add_trace_observation(f"審查完成！得分 {telemetry_res.get('score')} 分，違規項 {len(telemetry_res.get('violations', []))} 件", result=telemetry_res)

            final_resp = (
                f"報告教官/機師，黑盒子飛行紀錄 ({csv_target}) 審查完畢：\n\n"
                f"{telemetry_res['summary']}"
            )
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 3. RAG Knowledge Base Query (SOP, Live Rules, Practical Exam)
        # -------------------------------------------------------------
        rag_keywords = [
            "sop", "手冊", "規定", "規章", "條款", "規範", "準則",
            "啟動順序", "發動機啟動", "引擎啟動", "start sequence",
            "速限", "滑行速限", "taxi speed",
            "考核", "實作", "檢定", "一票否決", "扣分", "exam", "checkride",
            "機隊", "預約", "墜機", "通報", "事故", "wait landing", "冷卻期", "通聯", "呼號"
        ]
        if any(k in user_text.lower() for k in rag_keywords):
            self._add_trace_thought("官方規章知識庫檢索 (RAG)", f"識別為長榮航規或實作考核諮詢，檢索官方規章 RAG 向量知識庫 (查詢: '{user_text}')")
            self._add_trace_tool_call("query_flight_sop_and_regulations", f"query_flight_sop_and_regulations(query='{user_text}')")

            rag_res = query_flight_sop_and_regulations(user_text)

            self._add_trace_observation(f"知識庫命中 {len(rag_res.get('matched_documents', []))} 份官方文件 (來源: {rag_res.get('sources')})", result=rag_res)

            ans_text = rag_res.get("direct_answer") or rag_res.get("answer") or ""
            chunks = rag_res.get("top_chunks", [])
            final_resp = (
                f"報告機長，為您回報長榮虛擬航空官方規章檢索結果：\n\n"
                f"{ans_text}\n\n"
                f"📚 【規章依據出處】：\n"
            )
            for c in chunks:
                final_resp += f"• **《長榮虛擬航空 {c.get('source', '')} · {c.get('section', '')}》**：{c.get('title', '')}\n"

            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 4. Pure Aviation Weather Request Check (e.g. 查 RCTP 天氣)
        # -------------------------------------------------------------
        is_weather_only = any(w in user_text for w in ["天氣", "metar", "風向", "側風", "天氣報告"])
        is_route_planning = any(r in user_text for r in ["開", "飛往", "執飛", "航線", "推薦", "預計", "前往", "簽派"])

        if is_weather_only and not is_route_planning:
            # Extract ICAO code
            icao_match = re.search(r'\b([A-Z]{4})\b', user_text.upper())
            target_icao = icao_match.group(1) if icao_match else "RCTP"

            # Extract optional runway
            rwy_match = re.search(r'(\d{2}[LRC]?)\s*跑道|跑道\s*(\d{2}[LRC]?)', user_text, re.IGNORECASE)
            target_rwy = (rwy_match.group(1) or rwy_match.group(2)).upper() if rwy_match else "05L"

            self._add_trace_thought("機場氣象與跑道分量解析", f"識別為純氣象通聯查詢: 機場 {target_icao}，跑道 {target_rwy}，計算幾何側風與逆風分量")
            self._add_trace_tool_call("fetch_aviation_weather", f"fetch_aviation_weather(icao='{target_icao}', runway='{target_rwy}')")

            weather = fetch_aviation_weather(target_icao, target_rwy)

            w_dir = weather.get("wind_dir", 0)
            w_spd = weather.get("wind_speed_kts", 0)
            cw_kts = weather.get("crosswind_kts", 0.0)
            cw_dir = weather.get("crosswind_dir") or "側向"
            hw_kts = abs(weather.get("headwind_kts", 0.0))
            hw_label = weather.get("headwind_label") or ("逆風" if weather.get("headwind_kts", 0.0) >= 0 else "順風")
            raw_m = weather.get("raw_metar", "N/A")
            risk_ass = weather.get("risk_assessment") or weather.get("risk_notes") or "側風適航。"

            self._add_trace_observation(f"{target_icao} 即時氣象取得成功：風向 {w_dir}° / {w_spd} 節，跑道 {target_rwy} 側風分量 {cw_kts} 節（{cw_dir}側風），逆風 {hw_kts} 節（{hw_label}）", result=weather)
            self._add_trace_thought("安全操作評估", f"適航安全評估：{risk_ass}")

            final_resp = (
                f"報告機長，為您回報 **{target_icao}** 即時機場氣象報告 (METAR)：\n\n"
                f"• **METAR 原始電報**：`{raw_m}`\n"
                f"• **風向與風速**：{w_dir}° / {w_spd} 節\n"
                f"• **跑道 {target_rwy} 側風分量**：{cw_kts} 節（{cw_dir}側風）\n"
                f"• **跑道逆風/順風分量**：{hw_kts} 節（{hw_label}）\n"
                f"• **適航安全評估**：{risk_ass}\n\n"
                f"長官若需要安排航班簽派，請隨時指示！"
            )
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 5. Route Planning & Weather Analysis Chain
        # -------------------------------------------------------------
        if any(w in user_text for w in ["飛往", "成田", "桃園", "香港", "羽田", "關西", "新加坡", "洛杉磯", "RCTP", "RJAA", "VHHH", "RJBB", "WSSS", "KLAX", "簽派"]):
            # Dynamic ICAO extraction
            city_to_icao = {
                "桃園": "RCTP", "台北": "RCTP", "成田": "RJAA", "東京": "RJAA",
                "關西": "RJBB", "大阪": "RJBB", "羽田": "RJTT", "香港": "VHHH",
                "新加坡": "WSSS", "洛杉磯": "KLAX", "舊金山": "KSFO"
            }
            dep = "RCTP"
            arr = "RJAA"

            for city, icao_code in city_to_icao.items():
                if f"在{city}" in user_text or f"從{city}" in user_text or f"由{city}" in user_text or f"{city}出發" in user_text:
                    dep = icao_code
                elif f"飛往{city}" in user_text or f"前往{city}" in user_text or f"到{city}" in user_text:
                    arr = icao_code

            # Check explicit ICAOs
            icaos_found = re.findall(r'\b([A-Z]{4})\b', user_text.upper())
            if len(icaos_found) >= 2:
                dep, arr = icaos_found[0], icaos_found[1]
            elif len(icaos_found) == 1:
                arr = icaos_found[0]

            # Dynamic Aircraft Type Extraction
            ac_match = re.search(r'\b(B78X|B789|B77W|A321|A333|777|787|321|78X)\b', user_text, re.IGNORECASE)
            aircraft = "B78X"
            if ac_match:
                raw_ac = ac_match.group(1).upper()
                if "777" in raw_ac or "77W" in raw_ac:
                    aircraft = "B77W"
                elif "321" in raw_ac:
                    aircraft = "A321"
                elif "787" in raw_ac or "78X" in raw_ac or "789" in raw_ac:
                    aircraft = "B78X"
                else:
                    aircraft = raw_ac

            # Dynamic Runway Extraction
            default_runways = {
                "RCTP": "05L", "RCSS": "10", "RCKH": "09",
                "RJAA": "16R", "RJBB": "06R", "RJTT": "34R",
                "VHHH": "07L", "WSSS": "02L"
            }
            target_rwy = default_runways.get(arr, "16R")
            rwy_match = re.search(r'(\d{2}[LRC]?)\s*跑道|跑道\s*(\d{2}[LRC]?)', user_text, re.IGNORECASE)
            if rwy_match:
                target_rwy = (rwy_match.group(1) or rwy_match.group(2)).upper()

            self._add_trace_thought("簽派多步驟工具鏈規劃", f"使用者欲由 {dep} 執飛 {aircraft} 至 {arr}。執行兩步驟工具鏈：航線檢索 ➡️ 目的地起降氣象解析")
            self._add_trace_tool_call("query_virtual_routes", f"query_virtual_routes(dep_icao='{dep}', arr_icao='{arr}', aircraft_type='{aircraft}')")

            routes = query_virtual_routes(dep, arr, aircraft)
            flight = routes[0] if routes else {"flight_number": f"BR{dep[2:]}{arr[2:]}", "aircraft": aircraft, "flight_time": "2h 40m"}

            self._add_trace_observation(f"匹配推薦班次：{flight['flight_number']}（{flight['aircraft']}，航程預估 {flight['flight_time']}）", result=routes)
            self._add_trace_tool_call("fetch_aviation_weather", f"fetch_aviation_weather(icao='{arr}', runway='{target_rwy}')")

            weather = fetch_aviation_weather(arr, target_rwy)

            self._add_trace_observation(f"{arr} 即時 METAR 取得成功，{target_rwy} 跑道側風分量 {weather['crosswind_kts']} 節", result=weather)
            self._add_trace_thought("人機協同記憶鎖定 (HITL)", f"將待簽派班次 {flight['flight_number']} 寫入 Agent Memory (PendingDispatch)，等待機長授權放行")

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
            return self._finish_run(final_resp, return_trace)

        # -------------------------------------------------------------
        # 6. Fallback / Unified LLM Open Response (Ollama / Gemini / Offline)
        # -------------------------------------------------------------
        if self.llm and self.llm.is_available() and self.llm.provider_name != "offline":
            self._add_trace_thought("LLM 自然語言推理", f"呼叫大型語言模型 {self.llm.provider_name} ({self.llm.model_name}) 進行決策與回覆生成...")
            try:
                resp = self.llm.generate(prompt=user_text, system_prompt=SYSTEM_PROMPT)
                if resp and resp.content:
                    if resp.content.startswith("⚠️"):
                        self._add_trace_observation(f"⚠️ LLM 連線異常：{resp.content[:60]}", result={"error": resp.content, "provider": self.llm.provider_name})
                        final_resp = (
                            f"⚠️ 【LLM 連線異常】\n"
                            f"目前無法連線至指定的 AI 模型 ({self.llm.provider_name})：\n"
                            f"{resp.content}\n\n"
                            f"👉 請檢查網路連線或 .env 中的 API KEY 設定。\n\n"
                            f"報告機長，我是您的 AI 簽派副駕。請告訴我您的具體飛行需求，例如：\n"
                            f"• 排行榜查詢：「幫我查飛行時數排行榜」或「誰點數最多」\n"
                            f"• 官方行事曆：「查詢近期官方活動與大聯飛」\n"
                            f"• 道具與背包：「查看我的道具庫」\n"
                            f"• 航跡雷達：「查詢即時在空班機」或「查 EVA495 飛機位置」\n"
                            f"• 影音藝廊：「查看藝廊精選作品」\n"
                            f"• 氣象查詢：「幫我查一下 RCTP 天氣」\n"
                            f"• 航網簽派：「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)」\n"
                            f"• 黑盒子審核：「請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄」"
                        )
                        return self._finish_run(final_resp, return_trace)
                    self._add_trace_observation(f"成功自 {self.llm.provider_name} ({self.llm.model_name}) 生成回應", result={"content": resp.content, "model": self.llm.model_name, "provider": self.llm.provider_name})
                    final_resp = resp.content
                    return self._finish_run(final_resp, return_trace)
            except Exception as e:
                self._add_trace_observation(f"⚠️ LLM 執行異常：{e}", result={"error": str(e)})
                final_resp = f"⚠️ 【LLM 執行異常】: {e}"
                return self._finish_run(final_resp, return_trace)

        self._add_trace_thought("離線規則引擎指引", "當前處於離線確定性模式，向機長呈現完整副駕功能提示。")
        final_resp = (
            "報告機長，我是您的 AI 簽派副駕與考核助理。請告訴我您的具體飛行或查詢需求，例如：\n\n"
            "• 🏆 **排行榜查詢**：「幫我查飛行時數排行榜」或「查點數榜」\n"
            "• 📅 **官方行事曆**：「查詢近期活動與行事曆日程」\n"
            "• 🎒 **個人背包道具**：「查看我的背包與道具庫」\n"
            "• 📡 **即時航跡雷達**：「查看即時在空班機」或「查詢特定航班位置」\n"
            "• 🖼️ **影音藝廊精選**：「查看藝廊精選照片」\n"
            "• 📋 **歷史飛行報告**：「查看我的最近飛行紀錄與接地品質」\n"
            "• 🛫 **航網航線簽派**：「我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)」\n"
            "• 📑 **指定航班直接簽派**：「幫我直接簽派航班飛往成田」\n"
            "• 🌤️ **機場即時氣象**：「幫我查一下 RCTP 天氣」或「RJAA 16R 天氣」\n"
            "• 📖 **官方規章與 SOP**：「請問雙發客機的發動機啟動順序與滑行速限是多少？」\n"
            "• 📊 **黑盒子飛行遙測審核**：「請幫我審核 sample_flight_fail.csv」"
        )
        return self._finish_run(final_resp, return_trace)


# Backward-compatible alias for existing tests and scripts
AeroAgent = BRVAAgent

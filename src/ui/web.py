import os
import html
import streamlit as st
from src.agent import BRVAAgent, AeroAgent
from src.context import UserContext
from src.client import backend_client
from src.config import (
    config,
    mask_secret,
    update_runtime_config,
    load_secret_file,
    parse_secret_string,
    save_config_to_secret_file,
    SUPPORTED_PROVIDERS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OLLAMA_MODELS,
)
from src.llm import get_llm_provider

# Official Test Pilot Delegation Token (Loaded dynamically from sercet.txt or environment)
OFFICIAL_TEST_TOKEN = config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", "")

st.set_page_config(
    page_title="BRVA Agent · 智慧簽派與遙測考核系統",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ BRVA Agent：智慧飛行簽派與遙測考核系統")
st.caption("長榮虛擬航空 (EVA Air Virtual, BRVA) · 基於多工具協作與身分委託授權之專業領域 AI Agent")

# Initialize Agent & UserContext in session state
if "agent" not in st.session_state:
    st.session_state.agent = BRVAAgent()

if "user_context" not in st.session_state:
    st.session_state.user_context = UserContext()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "機長您好！我是長榮虛擬航空官方 AI 簽派副駕駛 BRVA Agent。請問今天需要為您查詢航線、解析目的地天氣、查看排行榜/行事曆，還是審查飛行黑盒子紀錄？"
        }
    ]

# Sidebar
with st.sidebar:
    st.header("🔐 核心連線金鑰與參數 (Secrets & API)")
    st.caption("🛡️ 公開儲存庫防護：機敏參數由 `sercet.txt` 自動載入，亦可在此直接配置。")

    top_api_server = st.text_input(
        "🌐 API 伺服器網址 (API Server)",
        value=config.BRVA_API_BASE_URL,
        help="BRVA 後端 API 伺服器端點 (例如 https://api.eva-virtual.com 或 http://localhost:3000)",
        key="top_api_server_input"
    )

    top_crewcenter_token = st.text_input(
        "🔑 CrewCenter 授權碼 / Token",
        value=config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", ""),
        type="password",
        help="CrewCenter 飛官委託授權碼 (由 sercet.txt 自動載入，亦可在此貼入個人授權碼)",
        key="top_crewcenter_token_input"
    )

    top_llm_key = st.text_input(
        "🧠 LLM API 金鑰 (Gemini Key)",
        value=config.GEMINI_API_KEY,
        type="password",
        help="Google Gemini 模型 API 金鑰 (由 sercet.txt 自動載入或在此設定)",
        key="top_llm_key_input"
    )

    col_import, col_test = st.columns(2)
    with col_import:
        import_clicked = st.button("📥 匯入 sercet", use_container_width=True, key="cfg_import_btn", help="從專案根目錄的 sercet.txt 自動載入並套用參數")
    with col_test:
        test_clicked = st.button("🔍 連線測試", type="primary", use_container_width=True, key="cfg_test_btn", help="依序測試 API Server、CrewCenter 飛官身分與 LLM")

    uploaded_secret = st.file_uploader(
        "📂 選擇 sercet.txt 檔案匯入參數",
        type=["txt", "env"],
        key="sercet_file_picker",
        help="選取本機 sercet.txt 或 secret.txt，系統將自動解析 API Server、CrewCenter 授權碼與 LLM 金鑰"
    )

    # 處理檔案選取上傳匯入
    if uploaded_secret is not None:
        file_bytes = uploaded_secret.getvalue()
        file_str = file_bytes.decode("utf-8", errors="ignore")
        file_sig = f"{uploaded_secret.name}_{len(file_bytes)}"
        if st.session_state.get("_last_uploaded_sig") != file_sig:
            st.session_state._last_uploaded_sig = file_sig
            parsed = parse_secret_string(file_str)
            if parsed:
                updates = {}
                if "BRVA_API_BASE_URL" in parsed:
                    st.session_state.top_api_server_input = parsed["BRVA_API_BASE_URL"]
                    updates["BRVA_API_BASE_URL"] = parsed["BRVA_API_BASE_URL"]
                if "OFFICIAL_TEST_TOKEN" in parsed:
                    st.session_state.top_crewcenter_token_input = parsed["OFFICIAL_TEST_TOKEN"]
                    updates["OFFICIAL_TEST_TOKEN"] = parsed["OFFICIAL_TEST_TOKEN"]
                if "GEMINI_API_KEY" in parsed:
                    st.session_state.top_llm_key_input = parsed["GEMINI_API_KEY"]
                    updates["GEMINI_API_KEY"] = parsed["GEMINI_API_KEY"]
                if updates:
                    update_runtime_config(updates, persist_to_env=False, persist_to_secret=False)
                    backend_client.configure(base_url=config.BRVA_API_BASE_URL)
                    new_prov = get_llm_provider(
                        provider_type=config.LLM_PROVIDER,
                        gemini_api_key=config.GEMINI_API_KEY,
                        gemini_model=config.GEMINI_MODEL,
                        ollama_base_url=config.OLLAMA_BASE_URL,
                        ollama_model=config.OLLAMA_MODEL,
                    )
                    st.session_state.agent = BRVAAgent(llm_provider=new_prov)
                st.success(f"✅ 已成功從檔案 `{uploaded_secret.name}` 匯入參數！")
                st.rerun()

    # 處理點擊「📥 匯入 sercet」按鈕
    if import_clicked:
        loaded = load_secret_file()
        if loaded:
            updates = {}
            if "BRVA_API_BASE_URL" in loaded:
                st.session_state.top_api_server_input = loaded["BRVA_API_BASE_URL"]
                updates["BRVA_API_BASE_URL"] = loaded["BRVA_API_BASE_URL"]
            if "OFFICIAL_TEST_TOKEN" in loaded:
                st.session_state.top_crewcenter_token_input = loaded["OFFICIAL_TEST_TOKEN"]
                updates["OFFICIAL_TEST_TOKEN"] = loaded["OFFICIAL_TEST_TOKEN"]
            if "GEMINI_API_KEY" in loaded:
                st.session_state.top_llm_key_input = loaded["GEMINI_API_KEY"]
                updates["GEMINI_API_KEY"] = loaded["GEMINI_API_KEY"]
            if updates:
                update_runtime_config(updates, persist_to_env=False, persist_to_secret=False)
                backend_client.configure(base_url=config.BRVA_API_BASE_URL)
                new_prov = get_llm_provider(
                    provider_type=config.LLM_PROVIDER,
                    gemini_api_key=config.GEMINI_API_KEY,
                    gemini_model=config.GEMINI_MODEL,
                    ollama_base_url=config.OLLAMA_BASE_URL,
                    ollama_model=config.OLLAMA_MODEL,
                )
                st.session_state.agent = BRVAAgent(llm_provider=new_prov)
            st.success("✅ 已成功從專案 `sercet.txt` 載入並套用參數！")
            st.rerun()
        else:
            st.warning("⚠️ 未在專案目錄找到 `sercet.txt` 或 `secret.txt`，請使用上方的檔案選擇器選取檔案。")

    with st.expander("⚙️ 進階模型選型 (LLM Model Selection)", expanded=False):
        provider_options = ["gemini", "ollama", "offline", "auto"]
        curr_provider = config.LLM_PROVIDER if config.LLM_PROVIDER in provider_options else "auto"
        selected_provider = st.selectbox(
            "🤖 LLM 核心模型選型",
            provider_options,
            index=provider_options.index(curr_provider),
            format_func=lambda x: {
                "gemini": "Google Gemini (推薦，雲端高性能)",
                "ollama": "Ollama (本機 / 區網主機)",
                "offline": "Offline (確定性離線規則，免金鑰)",
                "auto": "Auto (自動依優先度偵測)"
            }.get(x, x),
            key="cfg_provider_select"
        )

        gemini_model_options = ["gemini-3.5-flash-lite", "自訂模型 (Custom)..."]
        curr_g_idx = 0 if config.GEMINI_MODEL == "gemini-3.5-flash-lite" else 1
            
        selected_g_model = st.selectbox(
            "🎯 Gemini 模型版本",
            gemini_model_options,
            index=curr_g_idx,
            key="cfg_gemini_model_select"
        )
        if selected_g_model == "自訂模型 (Custom)...":
            gemini_model_val = st.text_input(
                "自訂 Gemini 模型名稱",
                value=config.GEMINI_MODEL if config.GEMINI_MODEL != "gemini-3.5-flash-lite" else "gemini-2.5-flash",
                key="cfg_gemini_custom_model_input"
            )
        else:
            gemini_model_val = selected_g_model

        ollama_url_val = config.OLLAMA_BASE_URL
        ollama_model_val = config.OLLAMA_MODEL
        if selected_provider in ("ollama", "auto"):
            ollama_url_val = st.text_input(
                "🌐 Ollama 主機網址",
                value=config.OLLAMA_BASE_URL,
                help="例如 http://localhost:11434 或區網 http://192.168.1.x:11434",
                key="cfg_ollama_url_input"
            )
            ollama_model_options = SUPPORTED_OLLAMA_MODELS + ["自訂模型 (Custom)..."]
            curr_o_idx = 0
            if config.OLLAMA_MODEL in SUPPORTED_OLLAMA_MODELS:
                curr_o_idx = SUPPORTED_OLLAMA_MODELS.index(config.OLLAMA_MODEL)
            else:
                curr_o_idx = len(SUPPORTED_OLLAMA_MODELS)
                
            selected_o_model = st.selectbox(
                "🎯 Ollama 模型",
                ollama_model_options,
                index=curr_o_idx,
                key="cfg_ollama_model_select"
            )
            if selected_o_model == "自訂模型 (Custom)...":
                ollama_model_val = st.text_input(
                    "自訂 Ollama 模型名稱",
                    value=config.OLLAMA_MODEL if config.OLLAMA_MODEL not in SUPPORTED_OLLAMA_MODELS else "llama3",
                    key="cfg_ollama_custom_model_input"
                )
            else:
                ollama_model_val = selected_o_model

        save_to_secret = st.checkbox("💾 同步儲存至 sercet.txt / .env", value=True, key="cfg_save_secret_checkbox")

    if test_clicked:
        # 同步更新執行時期設定
        updates = {
            "BRVA_API_BASE_URL": top_api_server.strip(),
            "OFFICIAL_TEST_TOKEN": top_crewcenter_token.strip(),
            "GEMINI_API_KEY": top_llm_key.strip(),
            "LLM_PROVIDER": selected_provider,
            "GEMINI_MODEL": gemini_model_val.strip(),
            "OLLAMA_BASE_URL": ollama_url_val.strip(),
            "OLLAMA_MODEL": ollama_model_val.strip(),
        }
        update_runtime_config(updates, persist_to_env=save_to_secret, persist_to_secret=save_to_secret)
        backend_client.configure(base_url=top_api_server.strip())

        with st.spinner("連線健康檢測中..."):
            # 1. 測試 API Server
            from src.client import BackendClient
            temp_client = BackendClient(base_url=top_api_server.strip())
            b_ok, b_msg = temp_client.test_connection()

            # 2. 測試 CrewCenter Pilot 身分
            curr_ctx = st.session_state.user_context
            target_token = top_crewcenter_token.strip() or config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", "")
            pilot_token_to_test = st.session_state.get("pilot_manual_token_box", "").strip() or target_token

            pilot_status = "guest"
            pilot_user = None
            pilot_err = None

            if curr_ctx and curr_ctx.is_authenticated:
                pilot_status = "already_linked"
                pilot_user = {
                    "callsign": curr_ctx.callsign,
                    "username": curr_ctx.username,
                    "rankName": curr_ctx.rank_name,
                    "points": curr_ctx.points,
                    "flightTimeHours": curr_ctx.flight_time_hours,
                }
            elif pilot_token_to_test:
                val_res = temp_client.verify_token(pilot_token_to_test)
                if val_res and val_res.get("valid") and val_res.get("user"):
                    pilot_status = "valid"
                    pilot_user = val_res["user"]
                else:
                    pilot_status = "invalid"
                    pilot_err = val_res.get("error") if val_res else "無法連線至 API 伺服器或授權碼無效"
            else:
                pilot_status = "guest"

            # 3. 測試 LLM
            temp_prov = get_llm_provider(
                provider_type=selected_provider,
                gemini_api_key=top_llm_key.strip(),
                gemini_model=gemini_model_val.strip(),
                ollama_base_url=ollama_url_val.strip(),
                ollama_model=ollama_model_val.strip(),
            )
            p_ok, p_msg = temp_prov.test_connection()
            st.session_state.agent = BRVAAgent(llm_provider=temp_prov)

        st.markdown("##### 🩺 三合一連線測試報告")

        # 報告 1: API Server
        if b_ok:
            st.success(f"🟢 **1. API Server (BRVA 伺服器)**\n\n{b_msg}")
        else:
            st.warning(f"🟡 **1. API Server (BRVA 伺服器)**\n\n{b_msg}")

        # 報告 2: CrewCenter Pilot 身分
        if pilot_status == "already_linked":
            u_cs = pilot_user.get("callsign") or "N/A"
            u_name = pilot_user.get("username") or "Pilot"
            st.success(
                f"🟢 **2. CrewCenter Pilot 身分 (已於會話連結)**\n\n"
                f"飛官身分：`{u_cs}` 機長 (`{u_name}`)\n\n"
                f"• 階級：`{pilot_user.get('rankName', 'Senior Captain')}` ｜ 點數：`{float(pilot_user.get('points') or 0):,.0f} pts` ｜ 總時數：`{float(pilot_user.get('flightTimeHours') or 0):,.1f} h`"
            )
        elif pilot_status == "valid":
            u_cs = pilot_user.get("callsign") or "N/A"
            u_name = pilot_user.get("username") or config.TEST_PILOT_USERNAME or "Pilot"
            st.success(
                f"🟢 **2. CrewCenter Pilot 身分**\n\n"
                f"成功讀取到飛官資訊：`{u_cs}` 機長 (`{u_name}`)\n\n"
                f"• 階級：`{pilot_user.get('rankName', 'Senior Captain')}` ｜ 點數：`{float(pilot_user.get('points') or 0):,.0f} pts` ｜ 總時數：`{float(pilot_user.get('flightTimeHours') or 0):,.1f} h`\n\n"
                f"*(點擊下方【⚡ 一鍵使用測試帳號】即可套用至會話)*"
            )
        elif pilot_status == "invalid":
            st.error(
                f"🔴 **2. CrewCenter Pilot 身分**\n\n"
                f"授權碼驗證失敗：{pilot_err}。請檢查 CrewCenter 授權碼是否正確或過期。"
            )
        else:
            st.info(
                "🟡 **2. CrewCenter Pilot 身分**\n\n"
                "目前為 **訪客模式 (未輸入授權碼)**。\n\n"
                "💡 **提示**：未連結帳號也能 **100% 正常使用** 公開航網班次、即時氣象 (METAR)、側風分量計算、飛行員排行榜與民航規章 SOP！"
            )

        # 報告 3: LLM
        if p_ok:
            st.success(f"🟢 **3. LLM (AI 模型 · {temp_prov.provider_name.upper()})**\n\n{p_msg}")
        else:
            st.error(f"🔴 **3. LLM (AI 模型 · {temp_prov.provider_name.upper()})**\n\n{p_msg}")

    st.divider()

    st.header("👨‍✈️ 飛官帳號連結 (CrewCenter Link)")
    
    # Mode B: Token input linking
    ctx = st.session_state.user_context

    if ctx.is_authenticated:
        st.success(
            f"🟢 **已連結飛官：{ctx.callsign} ({ctx.username})**\n\n"
            f"• 階級：`{ctx.rank_name}` ｜ 點數：`{ctx.points:,.0f} pts`\n\n"
            f"• 總飛行時數：`{ctx.flight_time_hours:,.1f} h`"
        )
        if st.button("🚪 切換回訪客模式 (Unlink)", use_container_width=True):
            st.session_state.user_context = UserContext()
            st.info("已解除帳號連結，恢復訪客模式。")
            st.rerun()
    else:
        st.caption("👤 目前為訪客模式 (可直接查公開航網、氣象、規章與排行榜)")

        if st.button("⚡ 一鍵使用測試帳號", use_container_width=True, type="primary"):
            target_token = top_crewcenter_token.strip() or config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", "")
            if not target_token:
                st.error("❌ 尚未在 sercet.txt 或上方輸入框設定 CrewCenter 授權碼，請先填入測試授權碼。")
            else:
                with st.spinner("向伺服器驗證並載入官方測試帳號..."):
                    val_res = backend_client.verify_token(target_token)
                    if val_res and val_res.get("valid") and val_res.get("user"):
                        u = val_res["user"]
                        u_cs = u.get("callsign") or "N/A"
                        u_name = u.get("username") or config.TEST_PILOT_USERNAME or "Pilot"
                        st.session_state.user_context = UserContext(
                            is_authenticated=True,
                            user_id=str(u.get("userId")),
                            callsign=u_cs,
                            username=u_name,
                            rank_name=u.get("rankName", "Senior Captain"),
                            points=float(u.get("points") or 0.0),
                            flight_time_hours=float(u.get("flightTimeHours") or 0.0),
                            delegation_token=target_token,
                            scopes=u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
                        )
                        st.success(f"✅ 成功一鍵連結飛官：{u_cs} ({u_name})！")
                        st.rerun()
                    else:
                        err = val_res.get("error") if val_res else "無法連線至 BRVA API 伺服器"
                        st.error(f"❌ 授權碼驗證失敗：{err}。請確認後端連線狀態與帳號權限。")

        # Advanced Manual Token Input (Collapsible by default so normal users won't see it directly)
        with st.expander("🛠️ 進階：手動輸入授權碼", expanded=False):
            token_input = st.text_input(
                "🔑 CrewCenter 授權碼 / Token",
                value="",
                type="password",
                key="pilot_manual_token_box",
                help="若您擁有個人 CrewCenter 授權碼，可在此手動輸入並點擊下方按鈕驗證連結。"
            )
            if st.button("🔗 驗證並連結", use_container_width=True):
                if not token_input.strip():
                    st.error("請先輸入授權碼！")
                else:
                    with st.spinner("驗證中..."):
                        val_res = backend_client.verify_token(token_input.strip())
                        if val_res and val_res.get("valid") and val_res.get("user"):
                            u = val_res["user"]
                            u_cs = u.get("callsign") or "N/A"
                            u_name = u.get("username") or config.TEST_PILOT_USERNAME or "Pilot"
                            st.session_state.user_context = UserContext(
                                is_authenticated=True,
                                user_id=str(u.get("userId")),
                                callsign=u_cs,
                                username=u_name,
                                rank_name=u.get("rankName", "Senior Captain"),
                                points=float(u.get("points") or 0.0),
                                flight_time_hours=float(u.get("flightTimeHours") or 0.0),
                                delegation_token=token_input.strip(),
                                scopes=u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
                            )
                            st.success(f"✅ 成功連結飛官：{u_cs} ({u_name})！")
                            st.rerun()
                        else:
                            err = val_res.get("error") if val_res else "無法連線至後端伺服器或授權碼無效"
                            st.error(f"❌ 授權碼驗證失敗：{err}")

    # CrewCenter Intro & Direct Link
    st.markdown("---")
    st.markdown("#### 🌐 CrewCenter 飛官中心")
    st.markdown(
        "我為 Infinite Flight 的長榮虛擬航空所做的網頁，裡面包含各種社群以及遊戲內的擴充功能。\n\n"
        "點擊下方按鈕進入查看："
    )
    st.link_button("🌐 前往 CrewCenter", "https://crewcenter.eva-virtual.com", use_container_width=True)

    st.divider()

    st.checkbox(
        "💭 預設展開思考歷程與工具調用",
        value=False,
        key="cfg_auto_expand_trace",
        help="勾選後預設自動展開每則對話上方的思考歷程與工具呼叫；未勾選則保持 Antigravity 式折疊，可隨時點擊展開。"
    )

    st.header("🛠️ 快速測試案例 (Demo Presets)")
    
    tab_dispatch, tab_crewcenter = st.tabs(["✈️ 簽派與考核", "🌐 CrewCenter 資訊"])

    with tab_dispatch:
        if st.button("🛫 RCTP -> RJAA 推薦簽派", use_container_width=True):
            st.session_state.prompt_input = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

        if st.button("📑 直接簽派航班 (BR184)", use_container_width=True):
            st.session_state.prompt_input = "幫我簽派 BR184 飛往成田"

        if st.button("📊 黑盒子遙測超速檢測", use_container_width=True):
            st.session_state.prompt_input = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"

        if st.button("📖 SOP 啟動順序與速限", use_container_width=True):
            st.session_state.prompt_input = "請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？"

        if st.button("🌦️ 桃園機場 (RCTP) 天氣", use_container_width=True):
            st.session_state.prompt_input = "幫我查一下 RCTP 05L 即時天氣與側風"

    with tab_crewcenter:
        if st.button("🏆 查詢時數與點數排行榜", use_container_width=True):
            st.session_state.prompt_input = "幫我查飛行員時數排行榜與名次"

        if st.button("🎒 查看我的背包道具庫 (唯讀)", use_container_width=True):
            st.session_state.prompt_input = "幫我看一下我的道具庫與持有的通行證"

        if st.button("📅 查詢官方活動與行事曆", use_container_width=True):
            st.session_state.prompt_input = "查詢近期官方活動、大聯飛與每週精選航線"

        if st.button("📡 查看即時在空班機雷達", use_container_width=True):
            st.session_state.prompt_input = "查詢目前有哪些長榮班機在線上飛行？"

        if st.button("📋 查詢個人歷史飛行報告", use_container_width=True):
            st.session_state.prompt_input = "查看我最近的飛行紀錄與落地接地垂直速度"

        if st.button("🖼️ 瀏覽影音藝廊精選照片", use_container_width=True):
            st.session_state.prompt_input = "幫我看看藝廊目前有什麼精選照片"

        if st.button("🏬 查看商城上架商品目錄", use_container_width=True):
            st.session_state.prompt_input = "幫我看一下商城目前架上有什麼商品"

        if st.button("💰 查詢點數餘額與個人檔案", use_container_width=True):
            st.session_state.prompt_input = "幫我查我的點數與個人檔案"

# Main Page Notice if Gemini is selected but key is missing
if config.LLM_PROVIDER == "gemini" and (not config.GEMINI_API_KEY or "your_gemini" in config.GEMINI_API_KEY):
    st.warning("⚠️ **尚未設定 Google Gemini API Key**：目前模型選型為 Google Gemini，請於左側側邊欄「⚙️ 參數設定與模型選型」輸入您的 API Key，或切換為 Offline 離線免金鑰模式！")

def render_trace_expander(trace: list, expanded: bool = False):
    if not trace:
        return

    num_tools = sum(1 for s in trace if s.get("type") == "tool_call")
    num_thoughts = sum(1 for s in trace if s.get("type") == "thought")

    badge_items = []
    if num_thoughts > 0:
        badge_items.append(f"{num_thoughts} 步思考")
    if num_tools > 0:
        badge_items.append(f"{num_tools} 次工具調用")
    badge_str = " · ".join(badge_items) if badge_items else "執行歷程"

    expander_title = f"💭 思考過程與工具調用 (Thinking & Tools · {badge_str})"

    with st.expander(expander_title, expanded=expanded):
        thought_idx = 1
        for step in trace:
            s_type = step.get("type", "thought")
            title = step.get("title", "")
            content = step.get("content", "")

            if s_type == "thought":
                safe_title = html.escape(title)
                safe_content = html.escape(content).replace("\n", "<br/>")
                st.markdown(
                    f"<div style='border-left: 3px solid #3b82f6; padding-left: 10px; margin-top: 6px; margin-bottom: 8px;'>"
                    f"<span style='color: #60a5fa; font-weight: 600; font-size: 0.9em;'>💭 思考 #{thought_idx} · {safe_title}</span><br/>"
                    f"<span style='font-size: 0.88em; opacity: 0.9; line-height: 1.4;'>{safe_content}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                thought_idx += 1
            elif s_type == "tool_call":
                tool_name = step.get("tool", "tool")
                safe_tool = html.escape(tool_name)
                st.markdown(
                    f"<div style='border-left: 3px solid #10b981; padding-left: 10px; margin-top: 6px; margin-bottom: 4px;'>"
                    f"<span style='color: #34d399; font-weight: 600; font-size: 0.9em;'>🔧 調用工具 · <code>{safe_tool}</code></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.code(content, language="python")
            elif s_type == "observation":
                safe_obs = html.escape(content).replace("\n", "<br/>")
                st.markdown(
                    f"<div style='border-left: 3px solid #a855f7; padding-left: 10px; margin-top: 4px; margin-bottom: 12px;'>"
                    f"<span style='color: #c084fc; font-weight: 600; font-size: 0.9em;'>📥 執行觀察 (Observation)</span><br/>"
                    f"<span style='font-size: 0.88em; opacity: 0.88; line-height: 1.4;'>{safe_obs}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

# Display conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("trace"):
            render_trace_expander(msg["trace"], expanded=st.session_state.get("cfg_auto_expand_trace", False))
        if msg["role"] == "assistant" and msg["content"].startswith("⚠️"):
            st.error(msg["content"])
        else:
            st.markdown(msg["content"])

# User input box
default_prompt = getattr(st.session_state, "prompt_input", "")
user_prompt = st.chat_input("請輸入您的飛行簽派需求或遙測檔案路徑...") or default_prompt

if user_prompt:
    if hasattr(st.session_state, "prompt_input"):
        del st.session_state.prompt_input

    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Agent response
    with st.chat_message("assistant"):
        with st.spinner("🤖 BRVA Agent 正在規劃工具鏈與分析中..."):
            response = st.session_state.agent.run(
                user_prompt,
                user_context=st.session_state.user_context,
                verbose=False
            )
            trace = st.session_state.agent.get_last_trace()

        render_trace_expander(trace, expanded=st.session_state.get("cfg_auto_expand_trace", False))
        if response.startswith("⚠️"):
            st.error(response)
        else:
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response, "trace": trace})

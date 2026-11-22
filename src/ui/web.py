import streamlit as st
from src.agent import AeroAgent
from src.context import UserContext
from src.client import backend_client
from src.config import (
    config,
    mask_secret,
    update_runtime_config,
    SUPPORTED_PROVIDERS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OLLAMA_MODELS,
)
from src.llm import get_llm_provider

st.set_page_config(
    page_title="AeroAgent · BRVA 智慧簽派與遙測考核系統",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ AeroAgent：BRVA 智慧簽派與飛行實操考核系統")
st.caption("長榮虛擬航空 (EVA Air Virtual) · 基於多工具協作與身分委託授權之專業領域 AI Agent")

# Initialize Agent & UserContext in session state
if "agent" not in st.session_state:
    st.session_state.agent = AeroAgent()

if "user_context" not in st.session_state:
    st.session_state.user_context = UserContext()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "機長您好！我是 BRVA 智慧飛行簽派與考核副駕駛。請問今天需要為您查詢航線、解析目的地天氣、查看排行榜/行事曆，還是審查飛行黑盒子紀錄？"
        }
    ]

# Sidebar
with st.sidebar:
    st.header("⚙️ 參數設定與模型選型 (Config & Model)")

    gem_key_missing = (not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("your_"))
    expand_config = gem_key_missing and config.LLM_PROVIDER in ("gemini", "auto")

    with st.expander("🛠️ 調整模型選型與 API 參數", expanded=expand_config):
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

        gemini_key_val = config.GEMINI_API_KEY
        gemini_model_val = config.GEMINI_MODEL
        ollama_url_val = config.OLLAMA_BASE_URL
        ollama_model_val = config.OLLAMA_MODEL

        if selected_provider in ("gemini", "auto"):
            gemini_key_val = st.text_input(
                "🔑 Google Gemini API Key",
                value=config.GEMINI_API_KEY,
                type="password",
                help="Google Cloud / AI Studio 之 Gemini API Key",
                key="cfg_gemini_key_input"
            )
            
            gemini_model_options = SUPPORTED_GEMINI_MODELS + ["自訂模型 (Custom)..."]
            curr_g_idx = 0
            if config.GEMINI_MODEL in SUPPORTED_GEMINI_MODELS:
                curr_g_idx = SUPPORTED_GEMINI_MODELS.index(config.GEMINI_MODEL)
            else:
                curr_g_idx = len(SUPPORTED_GEMINI_MODELS)
                
            selected_g_model = st.selectbox(
                "🎯 Gemini 模型版本",
                gemini_model_options,
                index=curr_g_idx,
                key="cfg_gemini_model_select"
            )
            if selected_g_model == "自訂模型 (Custom)...":
                gemini_model_val = st.text_input(
                    "自訂 Gemini 模型名稱",
                    value=config.GEMINI_MODEL if config.GEMINI_MODEL not in SUPPORTED_GEMINI_MODELS else "gemini-3.5-flash-lite",
                    key="cfg_gemini_custom_model_input"
                )
            else:
                gemini_model_val = selected_g_model

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

        # Backend Connection
        st.markdown("---")
        brva_url_val = st.text_input(
            "🌐 BRVA API 伺服器網址",
            value=config.BRVA_API_BASE_URL,
            help="線上正式站: https://api.eva-virtual.com | 本機開發: http://localhost:3000 (結尾有無 /api 皆自動相容)",
            key="cfg_brva_url_input"
        )
        brva_key_val = st.text_input(
            "🛡️ BRVA Agent 機器金鑰 (x-agent-key)",
            value=config.BRVA_AGENT_API_KEY,
            type="password",
            help="伺服器端授權金鑰 (x-agent-key)",
            key="cfg_brva_key_input"
        )

        save_to_env = st.checkbox("💾 同步儲存至 .env 檔案", value=True, key="cfg_save_env_checkbox")

        col_apply, col_test = st.columns(2)
        with col_apply:
            apply_clicked = st.button("💾 套用重啟", type="primary", use_container_width=True, key="cfg_apply_btn")
        with col_test:
            test_clicked = st.button("🔍 連線檢驗", use_container_width=True, key="cfg_test_btn")

        if apply_clicked:
            updates = {
                "LLM_PROVIDER": selected_provider,
                "GEMINI_API_KEY": gemini_key_val.strip(),
                "GEMINI_MODEL": gemini_model_val.strip(),
                "OLLAMA_BASE_URL": ollama_url_val.strip(),
                "OLLAMA_MODEL": ollama_model_val.strip(),
                "BRVA_API_BASE_URL": brva_url_val.strip(),
                "BRVA_AGENT_API_KEY": brva_key_val.strip(),
            }
            update_runtime_config(updates, persist_to_env=save_to_env)
            
            # Rebuild LLM provider and agent
            new_prov = get_llm_provider(
                provider_type=selected_provider,
                gemini_api_key=gemini_key_val.strip(),
                gemini_model=gemini_model_val.strip(),
                ollama_base_url=ollama_url_val.strip(),
                ollama_model=ollama_model_val.strip(),
            )
            st.session_state.agent = AeroAgent(llm_provider=new_prov)
            backend_client.configure(
                base_url=brva_url_val.strip(),
                api_key=brva_key_val.strip()
            )
            st.success("✅ 設定已成功套用並重啟！")
            st.rerun()

        if test_clicked:
            with st.spinner("連線健康檢測中..."):
                temp_prov = get_llm_provider(
                    provider_type=selected_provider,
                    gemini_api_key=gemini_key_val.strip(),
                    gemini_model=gemini_model_val.strip(),
                    ollama_base_url=ollama_url_val.strip(),
                    ollama_model=ollama_model_val.strip(),
                )
                p_ok, p_msg = temp_prov.test_connection()
                
                from src.client import BackendClient
                temp_client = BackendClient(base_url=brva_url_val.strip(), api_key=brva_key_val.strip())
                b_ok, b_msg = temp_client.test_connection()

            st.markdown("##### 🩺 連線檢驗報告")
            if p_ok:
                st.success(f"🟢 **AI 模型 ({temp_prov.provider_name.upper()})**\n\n{p_msg}")
            else:
                st.error(f"🔴 **AI 模型 ({temp_prov.provider_name.upper()})**\n\n{p_msg}")

            if b_ok:
                st.success(f"🟢 **BRVA 後端**\n\n{b_msg}")
            else:
                st.warning(f"🟡 **BRVA 後端**\n\n{b_msg}")

    st.divider()

    st.header("🔑 飛官帳號連結 (CrewCenter Link)")
    
    # Mode B: Token input linking
    ctx = st.session_state.user_context
    if ctx.is_authenticated:
        st.success(
            f"🟢 **已連結飛官：{ctx.callsign}**\n\n"
            f"• 階級：`{ctx.rank_name}`\n\n"
            f"• 點數：`{ctx.points:,.0f} pts`\n\n"
            f"• 總飛行時數：`{ctx.flight_time_hours:,.1f} h`"
        )
        if st.button("🚪 解除連結 (Unlink)", use_container_width=True):
            st.session_state.user_context = UserContext()
            st.info("已解除帳號連結，恢復訪客模式。")
            st.rerun()
    else:
        st.warning("🔴 **未連結飛官帳號 (訪客模式)**\n\n訪客可查詢公開航網、氣象、排行榜與行事曆；如需簽派或查詢個人時數點數背包，請貼入授權碼。")
        token_input = st.text_input("CrewCenter 授權碼 / Token", type="password", key="pilot_token_box", placeholder="貼上 CrewCenter 授權碼...")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔗 驗證並連結", use_container_width=True):
                if not token_input.strip():
                    st.error("請先輸入授權碼！")
                else:
                    with st.spinner("驗證中..."):
                        val_res = backend_client.verify_token(token_input.strip())
                        if val_res and val_res.get("valid") and val_res.get("user"):
                            u = val_res["user"]
                            st.session_state.user_context = UserContext(
                                is_authenticated=True,
                                user_id=str(u.get("userId")),
                                callsign=u.get("callsign"),
                                username=u.get("username"),
                                rank_name=u.get("rankName"),
                                points=float(u.get("points") or 0),
                                flight_time_hours=float(u.get("flightTimeHours") or 0),
                                delegation_token=token_input.strip(),
                                scopes=u.get("scopes") or []
                            )
                            st.success(f"✅ 成功連結飛官：{u.get('callsign')}！")
                            st.rerun()
                        elif val_res is None or val_res.get("_offline") or val_res.get("_status_code") in (500, 502, 503, 504):
                            st.error("⚠️ 目前似乎無法連線到 CrewCenter 伺服器（連線逾時或伺服器維護中），請稍後再次嘗試。")
                        else:
                            st.error("❌ 授權碼無效或已過期，請確認後重試。")
        with col2:
            st.link_button("🌐 前往 CrewCenter", "https://crewcenter.eva-virtual.com", use_container_width=True)

    st.divider()

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

    st.divider()
    st.markdown("### 📋 系統狀態")
    provider_name = getattr(st.session_state.agent.llm, "provider_name", "unknown").upper()
    model_name = getattr(st.session_state.agent.llm, "model_name", "default")
    st.markdown(f"• **LLM 核心選型**：`{provider_name}` (`{model_name}`)")
    st.markdown(f"• **Gemini Key**：`{mask_secret(config.GEMINI_API_KEY)}`")
    st.markdown(f"• **BRVA 伺服器**：`{config.BRVA_API_BASE_URL}`")
    st.markdown(f"• **BRVA Agent Key**：`{mask_secret(config.BRVA_AGENT_API_KEY)}`")
    st.info("✅ ReAct 決策引擎：就緒\n\n✅ 身分委託授權鏈：就緒\n\n✅ 14 大航空與 CrewCenter 工具鏈：就緒\n\n✅ 官方規章與 SOP 知識庫：就緒")

# Main Page Notice if Gemini is selected but key is missing
if config.LLM_PROVIDER == "gemini" and (not config.GEMINI_API_KEY or "your_gemini" in config.GEMINI_API_KEY):
    st.warning("⚠️ **尚未設定 Google Gemini API Key**：目前模型選型為 Google Gemini，請於左側側邊欄「⚙️ 參數設定與模型選型」輸入您的 API Key，或切換為 Offline 離線免金鑰模式！")

# Display conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
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
        with st.spinner("🤖 AeroAgent 正在規劃工具鏈與分析中..."):
            response = st.session_state.agent.run(
                user_prompt,
                user_context=st.session_state.user_context,
                verbose=False
            )
            if response.startswith("⚠️"):
                st.error(response)
            else:
                st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

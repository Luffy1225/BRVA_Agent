import streamlit as st
from src.agent import BRVAAgent, AeroAgent
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

        # Backend Connection (Advanced Selectbox / Collapsed by default)
        with st.expander("🛠️ 進階伺服器連線設定 (非必要免填)", expanded=False):
            url_options = [
                "https://api.eva-virtual.com",
                "http://localhost:3000",
                "自訂網址 (Custom)..."
            ]
            curr_url = config.BRVA_API_BASE_URL.rstrip("/")
            if curr_url == "http://localhost:3000":
                curr_url_idx = 1
            elif curr_url in ("https://api.eva-virtual.com", ""):
                curr_url_idx = 0
            else:
                curr_url_idx = 2

            selected_url_choice = st.selectbox(
                "🌐 BRVA API 伺服器網址",
                url_options,
                index=curr_url_idx,
                format_func=lambda x: {
                    "https://api.eva-virtual.com": "1. 線上正式站 (https://api.eva-virtual.com)",
                    "http://localhost:3000": "2. 本地開發端 (http://localhost:3000)",
                    "自訂網址 (Custom)...": "3. 自訂網址 (手動輸入)"
                }.get(x, x),
                key="cfg_brva_url_select"
            )
            if selected_url_choice == "自訂網址 (Custom)...":
                brva_url_val = st.text_input(
                    "自訂後端網址",
                    value=config.BRVA_API_BASE_URL,
                    key="cfg_brva_custom_url_input"
                )
            else:
                brva_url_val = selected_url_choice

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
            st.session_state.agent = BRVAAgent(llm_provider=new_prov)
            backend_client.configure(
                base_url=brva_url_val.strip()
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
                temp_client = BackendClient(base_url=brva_url_val.strip())
                b_ok, b_msg = temp_client.test_connection()

            st.markdown("##### 🩺 三合一連線檢驗報告")
            if p_ok:
                st.success(f"🟢 **1. AI 模型 ({temp_prov.provider_name.upper()})**\n\n{p_msg}")
            else:
                st.error(f"🔴 **1. AI 模型 ({temp_prov.provider_name.upper()})**\n\n{p_msg}")

            if b_ok:
                st.success(f"🟢 **2. BRVA API 伺服器**\n\n{b_msg}")
            else:
                st.warning(f"🟡 **2. BRVA API 伺服器**\n\n{b_msg}")

            curr_ctx = st.session_state.user_context
            if curr_ctx and curr_ctx.is_authenticated:
                st.success(
                    f"🟢 **3. 飛官身分 (CrewCenter)**\n\n"
                    f"成功讀取到飛官資訊：`{curr_ctx.callsign}` 機長 (`{curr_ctx.username}`)\n\n"
                    f"• 階級：`{curr_ctx.rank_name}` ｜ 點數：`{curr_ctx.points:,.0f} pts` ｜ 總時數：`{curr_ctx.flight_time_hours:,.1f} h`"
                )
            else:
                pilot_token_to_test = st.session_state.get("pilot_token_box", OFFICIAL_TEST_TOKEN)
                val_res = temp_client.verify_token(pilot_token_to_test) if pilot_token_to_test else None
                if val_res and val_res.get("valid") and val_res.get("user"):
                    u = val_res["user"]
                    st.success(
                        f"🟢 **3. 飛官身分 (CrewCenter)**\n\n"
                        f"成功讀取到飛官資訊：`{u.get('callsign', 'PILOT')}` 機長 (`{u.get('username', 'Pilot')}`)\n\n"
                        f"• 階級：`{u.get('rankName', 'First Officer')}` ｜ 點數：`{float(u.get('points') or 0):,.0f} pts` ｜ 總時數：`{float(u.get('flightTimeHours') or 0):,.1f} h`\n\n"
                        f"*(點擊下方【⚡ 一鍵引用】或【🔗 驗證並連結】即可套用至會話)*"
                    )
                else:
                    st.info(
                        "🟡 **3. 飛官身分 (CrewCenter)**\n\n"
                        "目前為 **訪客模式 (未連結飛官帳號)**。\n\n"
                        "💡 **提示**：未連結帳號也能 **100% 正常使用** 公開航網班次、即時氣象 (METAR)、側風分量計算、飛行員排行榜與民航規章 SOP！"
                    )

    st.divider()

    st.header("👨‍✈️ 飛官帳號連結 (CrewCenter Link)")
    
    # Mode B: Token input linking
    ctx = st.session_state.user_context
    OFFICIAL_TEST_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOiI4ODg4MTc5NTM2MDg2ODc2NDEwIiwidHlwZSI6ImRlbGVnYXRpb24iLCJzY29wZXMiOlsiZGlzcGF0Y2giLCJwcm9maWxlOnJlYWQiLCJzdG9yZTpyZWFkIiwicm91dGVzIl0sInRva2VuVmVyc2lvbiI6MSwiaWF0IjoxNzk1MzY5NTMxfQ.7pB5-bHLE2WmNElbwvGIczOJs6LenQTBvL2Rpbu3Kwk"

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

        if st.button("⚡ 一鍵引用官方測試授權碼 (免手動複製)", use_container_width=True, type="primary"):
            with st.spinner("向伺服器驗證並載入官方測試帳號..."):
                val_res = backend_client.verify_token(OFFICIAL_TEST_TOKEN)
                if val_res and val_res.get("valid") and val_res.get("user"):
                    u = val_res["user"]
                    st.session_state.user_context = UserContext(
                        is_authenticated=True,
                        user_id=str(u.get("userId")),
                        callsign=u.get("callsign", "PILOT"),
                        username=u.get("username", "Pilot"),
                        rank_name=u.get("rankName", "First Officer"),
                        points=float(u.get("points") or 0.0),
                        flight_time_hours=float(u.get("flightTimeHours") or 0.0),
                        delegation_token=OFFICIAL_TEST_TOKEN,
                        scopes=u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
                    )
                    st.success(f"✅ 成功一鍵連結飛官：{u.get('callsign')} ({u.get('username')})！")
                    st.rerun()
                else:
                    err = val_res.get("error") if val_res else "無法連線至 BRVA API 伺服器"
                    st.error(f"❌ 授權碼驗證失敗：{err}。請確認後端連線狀態與帳號權限。")

        token_input = st.text_input(
            "🔑 CrewCenter 授權碼 / Token",
            value=OFFICIAL_TEST_TOKEN,
            type="password",
            key="pilot_token_box",
            help="系統已為您預先填入官方測試授權碼，點擊下方【🔗 驗證並連結】即可直接登入；亦可手動貼入您個人的授權碼。"
        )
        
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
                                callsign=u.get("callsign", "PILOT"),
                                username=u.get("username", "Pilot"),
                                rank_name=u.get("rankName", "First Officer"),
                                points=float(u.get("points") or 0.0),
                                flight_time_hours=float(u.get("flightTimeHours") or 0.0),
                                delegation_token=token_input.strip(),
                                scopes=u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
                            )
                            st.success(f"✅ 成功連結飛官：{u.get('callsign')} ({u.get('username')})！")
                            st.rerun()
                        else:
                            err = val_res.get("error") if val_res else "無法連線至後端伺服器或授權碼無效"
                            st.error(f"❌ 授權碼驗證失敗：{err}")
        with col2:
            st.link_button("🌐 前往 CrewCenter", "https://crewcenter.eva-virtual.com", use_container_width=True)

    # CrewCenter Test Credentials Card & 20-Point Overview
    st.markdown("---")
    st.markdown("#### 🌐 CrewCenter 飛官中心入口")
    st.link_button("🚀 直接進入 CrewCenter 登入首頁", "https://crewcenter.eva-virtual.com", use_container_width=True)
    st.info(
        "👨‍✈️ **官方測試機長帳號：**\n\n"
        "• 測試帳號 (Username)：`AgenticTesting`\n\n"
        "• 測試密碼 (Password)：`!1TestAgent`"
    )

    with st.expander("💡 什麼是 CrewCenter 飛官中心？ (20 大特色速覽)", expanded=False):
        st.markdown("""
1. **飛行員營運中樞**：CrewCenter 是長榮虛擬航空 (EVA Air Virtual) 核心的數位化航務與飛行員管理平台。
2. **專屬個人座艙**：每位長榮虛擬機長均擁有獨立的飛行檔案，記錄完整的航空職涯數據。
3. **國際級 SimBrief 整合**：一鍵向 SimBrief 與簽派中心發起航班，自動產出專業民航標準 OFP 飛行計畫。
4. **全航網即時在空雷達**：整合 Live Radar，隨時在地圖上追蹤全球正在執飛的長榮與立榮機隊航跡。
5. **黑盒子 PIREP 自動審核**：飛行結束後系統自動解析遙測數據，嚴格評審接地垂直速度 (fpm) 與過載 G 值。
6. **完整飛行生涯履歷**：精確記錄總飛行時數、起降架次、安全飛行率以及歷史飛行航線。
7. **階級考核晉升體系**：涵蓋從二副 (Second Officer) 到資深機長 (Senior Captain) 的嚴謹升等考核指標。
8. **機長專屬飛行商城**：可用執飛累積的哩程飛行積分 (Points) 兌換全球自由包機特許卡與彩繪機塗裝。
9. **官方每週精選航線 (ROTW)**：每週推出 Route of the Week 與多人聯飛活動行事曆，豐富航網探索。
10. **飛行員影音藝廊**：供全體機組人員上傳分享高空巡航美景與降落進場的精采航空寫真。
11. **全域時數與點數排行榜**：即時更新月度與年度飛官榜單，打造高水準的虛擬民航社群良性競賽。
12. **LIVE 機隊預約保護**：每位機師最多可保留 3 架航機席位，並具備智慧調機與航班指派機制。
13. **斷線落地保護機制 (Wait Landing)**：遭遇網路異常時自動觸發 60~300 分鐘機長保護鎖，守護飛行成果。
14. **2D 線上航管管制中心**：提供即時 ATC 席位狀態（地面 GND、塔臺 TWR、進場 APP、離場 DEP）。
15. **全球機場 METAR 即時氣象**：自動計算起降跑道之正逆風與側風分量，提供超限操作預警。
16. **AI 身分委託授權憑證 (Token)**：支援生成永久密鑰，委託 BRVA Agent 代理機長查詢資料與快速簽派。
17. **銀行級資安與版本控管**：採用 JWT 身分鑑權與 TokenVersion 機制，保障飛官帳號與點數資產絕對安全。
18. **Discord SSO 快速單一簽入**：與官方社群身分組全面連動，即時同步考驗及職級榮譽標籤。
19. **跨平台極致響應式體驗**：全面適配桌上型電腦、平板與手機瀏覽器，隨時掌握長榮機隊脈動。
20. **AI Agent 的最強數據大腦**：作為 BRVA Agent 核心後端數據庫，為 AI 副駕駛提供毫秒級的權威航務數據！
        """)

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
        with st.spinner("🤖 BRVA Agent 正在規劃工具鏈與分析中..."):
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

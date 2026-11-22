import streamlit as st
from src.agent import AeroAgent
from src.context import UserContext
from src.client import backend_client

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
    st.markdown(f"• **LLM 核心引擎**：`{provider_name}` (`{model_name}`)")
    st.info("✅ ReAct 決策引擎：就緒\n\n✅ 身分委託授權鏈：就緒\n\n✅ 14 大航空與 CrewCenter 工具鏈：就緒\n\n✅ 官方規章與 SOP 知識庫：就緒")

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

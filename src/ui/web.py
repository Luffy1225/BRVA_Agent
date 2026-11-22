import streamlit as st
from src.agent import AeroAgent

st.set_page_config(
    page_title="AeroAgent · BRVA 智慧簽派與遙測考核系統",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ AeroAgent：BRVA 智慧簽派與飛行實操考核系統")
st.caption("長榮虛擬航空 (EVA Air Virtual) · 基於多工具協作與 ReAct 決策循環之專業領域 AI Agent")

# Initialize Agent in session state
if "agent" not in st.session_state:
    st.session_state.agent = AeroAgent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "機長您好！我是 BRVA 智慧飛行簽派與考核副駕駛。請問今天需要為您查詢航線、解析目的地天氣，還是審查飛行黑盒子紀錄？"
        }
    ]

# Sidebar with quick test prompts
with st.sidebar:
    st.header("🛠️ 快速測試案例 (Demo Presets)")
    if st.button("🛫 情境一：RCTP -> RJAA 簽派推薦"):
        st.session_state.prompt_input = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

    if st.button("📑 情境二：確認簽派授權 (HITL)"):
        st.session_state.prompt_input = "好的，如果沒有問題就幫我直接簽派 BR184 吧！"

    if st.button("📊 情境三：黑盒子遙測超速與硬著陸檢測"):
        st.session_state.prompt_input = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"

    if st.button("📖 情境四 (RAG)：SOP 引擎啟動順序與滑行速限"):
        st.session_state.prompt_input = "請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？"

    if st.button("⚠️ 情境五 (RAG)：術科考核一票否決標準"):
        st.session_state.prompt_input = "請問術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？"

    if st.button("🛑 情境六 (RAG)：LIVE 機隊預約上限與墜機通報"):
        st.session_state.prompt_input = "請問 LIVE 機隊機師認領預約上限是幾架？若發生墜機事故需要在多久內通報？"

    st.divider()
    st.markdown("### 📋 系統狀態")
    provider_name = getattr(st.session_state.agent.llm, "provider_name", "unknown").upper()
    model_name = getattr(st.session_state.agent.llm, "model_name", "default")
    st.markdown(f"• **LLM 核心引擎**：`{provider_name}` (`{model_name}`)")
    st.info("✅ ReAct 決策引擎：就緒\n\n✅ 5 大航空工具鏈 (含 RAG)：就緒\n\n✅ 官方 SOP 知識庫：就緒\n\n✅ Podman 容器規範：符合")

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
        with st.spinner("🤖 AeroAgent 正在規劃工具鏈與分析氣象中..."):
            response = st.session_state.agent.run(user_prompt, verbose=False)
            if response.startswith("⚠️"):
                st.error(response)
            else:
                st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

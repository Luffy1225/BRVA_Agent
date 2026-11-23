import os
import time
import html
import json
import inspect
from typing import Optional, Dict, Any, List
import streamlit as st

# Streamlit 1.67+ deprecation: use_container_width is replaced with width='stretch' / 'content'
# Provide seamless backward compatibility for older Streamlit versions without deprecation warnings
if "width" not in inspect.signature(st.button).parameters:
    _orig_st_button = st.button
    def _compat_button(*args, **kwargs):
        if "width" in kwargs:
            w = kwargs.pop("width")
            kwargs["use_container_width"] = (w == "stretch")
        return _orig_st_button(*args, **kwargs)
    st.button = _compat_button

    _orig_st_link_button = st.link_button
    def _compat_link_button(*args, **kwargs):
        if "width" in kwargs:
            w = kwargs.pop("width")
            kwargs["use_container_width"] = (w == "stretch")
        return _orig_st_link_button(*args, **kwargs)
    st.link_button = _compat_link_button

    _orig_st_image = st.image
    def _compat_image(*args, **kwargs):
        if "width" in kwargs:
            w = kwargs.pop("width")
            kwargs["use_container_width"] = (w == "stretch")
        return _orig_st_image(*args, **kwargs)
    st.image = _compat_image

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

def _auto_link_pilot(token: str) -> bool:
    """Helper to verify token and immediately link pilot context."""
    if not token or not token.strip():
        return False
    val_res = backend_client.verify_token(token.strip())
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
            delegation_token=token.strip(),
            scopes=u.get("scopes") or ["dispatch", "profile:read", "store:read", "routes"]
        )
        return True
    return False

if "user_context" not in st.session_state:
    st.session_state.user_context = UserContext()
    # Auto-link if OFFICIAL_TEST_TOKEN is already loaded in config
    target_init_token = config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", "")
    if target_init_token:
        _auto_link_pilot(target_init_token)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "機長您好！我是長榮虛擬航空官方 AI 簽派副駕駛 BRVA Agent。請問今天需要為您查詢航線、解析目的地天氣、查看排行榜/行事曆，還是審查飛行黑盒子紀錄？"
        }
    ]

# Pre-initialize session_state keys for configuration widgets
if "top_api_server_input" not in st.session_state:
    st.session_state.top_api_server_input = config.BRVA_API_BASE_URL

if "top_crewcenter_token_input" not in st.session_state:
    st.session_state.top_crewcenter_token_input = config.OFFICIAL_TEST_TOKEN or os.getenv("OFFICIAL_TEST_TOKEN", "")

if "top_llm_key_input" not in st.session_state:
    st.session_state.top_llm_key_input = config.GEMINI_API_KEY


def on_import_secret_clicked():
    """Callback executed before widgets instantiate, safely updating session_state."""
    loaded = load_secret_file()
    if loaded:
        if "BRVA_API_BASE_URL" in loaded:
            st.session_state.top_api_server_input = loaded["BRVA_API_BASE_URL"]
        if "OFFICIAL_TEST_TOKEN" in loaded:
            st.session_state.top_crewcenter_token_input = loaded["OFFICIAL_TEST_TOKEN"]
        if "GEMINI_API_KEY" in loaded:
            st.session_state.top_llm_key_input = loaded["GEMINI_API_KEY"]

        update_runtime_config(loaded, persist_to_env=False, persist_to_secret=False)
        backend_client.configure(base_url=config.BRVA_API_BASE_URL)
        new_prov = get_llm_provider(
            provider_type=config.LLM_PROVIDER,
            gemini_api_key=config.GEMINI_API_KEY,
            gemini_model=config.GEMINI_MODEL,
            ollama_base_url=config.OLLAMA_BASE_URL,
            ollama_model=config.OLLAMA_MODEL,
        )
        st.session_state.agent = BRVAAgent(llm_provider=new_prov)

        # Auto-link pilot on import so users can use immediately without extra manual steps
        token = loaded.get("OFFICIAL_TEST_TOKEN") or st.session_state.get("top_crewcenter_token_input", "")
        if token and token.strip():
            linked = _auto_link_pilot(token.strip())
            if linked:
                ctx = st.session_state.user_context
                st.session_state["_secret_import_msg"] = ("success", f"✅ 成功載入 `sercet.txt` 並自動連結飛官：`{ctx.callsign}` ({ctx.username})！")
            else:
                st.session_state["_secret_import_msg"] = ("success", "✅ 已成功從 `sercet.txt` 載入並套用參數！")
        else:
            st.session_state["_secret_import_msg"] = ("success", "✅ 已成功從 `sercet.txt` 載入並套用參數！")
    else:
        st.session_state["_secret_import_msg"] = ("warning", "⚠️ 未在專案根目錄找到 `sercet.txt` 或 `secret.txt`。")


# Sidebar
with st.sidebar:
    st.header("🔐 核心連線金鑰與參數 (Secrets & API)")
    st.caption("🛡️ 公開儲存庫防護：機敏參數由 `sercet.txt` 自動載入，亦可在此直接配置。")

    top_api_server = st.text_input(
        "🌐 API 伺服器網址 (API Server)",
        key="top_api_server_input",
        help="BRVA 後端 API 伺服器端點 (例如 https://api.eva-virtual.com 或 http://localhost:3000)"
    )

    top_crewcenter_token = st.text_input(
        "🔑 CrewCenter 授權碼 / Token",
        type="password",
        key="top_crewcenter_token_input",
        help="CrewCenter 飛官委託授權碼 (由 sercet.txt 自動載入，亦可在此貼入個人授權碼)"
    )

    top_llm_key = st.text_input(
        "🧠 LLM API 金鑰 (Gemini Key)",
        type="password",
        key="top_llm_key_input",
        help="Google Gemini 模型 API 金鑰 (由 sercet.txt 自動載入或在此設定)"
    )

    col_import, col_test = st.columns(2)
    with col_import:
        st.button(
            "📥 匯入 sercet",
            on_click=on_import_secret_clicked,
            width="stretch",
            key="cfg_import_btn",
            help="從專案根目錄的 sercet.txt 自動載入並套用參數"
        )
    with col_test:
        test_clicked = st.button(
            "🔍 連線測試",
            type="primary",
            width="stretch",
            key="cfg_test_btn",
            help="依序測試 API Server、CrewCenter 飛官身分與 LLM"
        )

    if "_secret_import_msg" in st.session_state:
        msg_type, msg_text = st.session_state.pop("_secret_import_msg")
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)

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

    # Pilot Identity Status Indicator
    ctx = st.session_state.user_context
    if ctx.is_authenticated:
        st.success(
            f"👨‍✈️ **已連結飛官：{ctx.callsign} ({ctx.username})**\n\n"
            f"• 階級：`{ctx.rank_name}` ｜ 點數：`{ctx.points:,.0f} pts` ｜ 總時數：`{ctx.flight_time_hours:,.1f} h`"
        )
    else:
        st.caption("👤 目前為訪客模式（點擊上方【📥 匯入 sercet】自動連結飛官）")

    # Advanced Manual Account Management (Collapsible)
    with st.expander("🛠️ 進階：手動管理飛官帳號與授權碼", expanded=False):
        if ctx.is_authenticated:
            st.markdown(
                f"• **呼號 (Callsign)**：`{ctx.callsign}`\n\n"
                f"• **飛官姓名**：`{ctx.username}`\n\n"
                f"• **階級等級**：`{ctx.rank_name}`\n\n"
                f"• **點數餘額**：`{ctx.points:,.0f} pts`\n\n"
                f"• **累計時數**：`{ctx.flight_time_hours:,.1f} h`"
            )
            if st.button("🚪 切換回訪客模式 (Unlink)", width="stretch"):
                st.session_state.user_context = UserContext()
                st.info("已解除帳號連結，恢復訪客模式。")
                st.rerun()
        else:
            token_input = st.text_input(
                "🔑 手動輸入 CrewCenter 授權碼 / Token",
                value="",
                type="password",
                key="pilot_manual_token_box",
                help="若欲手動切換至其他飛官帳號，可在此貼入授權碼。"
            )
            if st.button("🔗 驗證並手動連結", width="stretch"):
                if not token_input.strip():
                    st.error("請先輸入授權碼！")
                else:
                    with st.spinner("驗證中..."):
                        if _auto_link_pilot(token_input.strip()):
                            st.success("✅ 成功手動連結飛官帳號！")
                            st.rerun()
                        else:
                            st.error("❌ 授權碼驗證失敗或無法連線至伺服器。")
            if top_crewcenter_token.strip():
                if st.button("⚡ 快速連結上方金鑰框之授權碼", width="stretch"):
                    with st.spinner("向伺服器驗證中..."):
                        if _auto_link_pilot(top_crewcenter_token.strip()):
                            st.success("✅ 成功連結飛官帳號！")
                            st.rerun()
                        else:
                            st.error("❌ 授權碼驗證失敗。")

    # CrewCenter Intro & Direct Link
    st.markdown("---")
    st.markdown("#### 🌐 CrewCenter 飛官中心")
    st.markdown(
        "我為 Infinite Flight 的長榮虛擬航空所做的網頁，裡面包含各種社群以及遊戲內的擴充功能。\n\n"
        "點擊下方按鈕進入查看："
    )
    st.link_button("🌐 前往 CrewCenter", "https://crewcenter.eva-virtual.com", width="stretch")

    st.divider()

    st.header("🛠️ 快速測試案例 (Demo Presets)")
    
    tab_dispatch, tab_sop, tab_pilot, tab_atc = st.tabs([
        "🛫 簽派氣象",
        "📖 規章遙測",
        "👨‍✈️ 飛官中心",
        "🎙️ 航管機隊",
    ])

    with tab_dispatch:
        if st.button("🛫 航線推薦與起降側風分析 (RCTP ➔ RJAA)", width="stretch"):
            st.session_state.prompt_input = "我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

        if st.button("📑 直接簽派航班 (BR184)", width="stretch"):
            st.session_state.prompt_input = "幫我簽派 BR184 飛往成田"

        if st.button("📡 查詢生效中簽派單 (Active Dispatch)", width="stretch"):
            st.session_state.prompt_input = "查詢我目前是否有生效中的簽派放行單 (Active Dispatch)？"

        if st.button("🌦️ 桃園機場 (RCTP 05L) 即時天氣與側風", width="stretch"):
            st.session_state.prompt_input = "幫我查一下 RCTP 05L 即時天氣與側風"

        if st.button("🗺️ 星空聯盟聯營航線推薦 (ANA / Codeshare)", width="stretch"):
            st.session_state.prompt_input = "請推薦我幾條適合執飛的 ANA 星空聯盟 Codeshare 聯營航線"

    with tab_sop:
        if st.button("📖 發動機啟動順序 (2->1) 與滑行速限", width="stretch"):
            st.session_state.prompt_input = "請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？"

        if st.button("⚠️ 術科考核重大違規一票否決條款", width="stretch"):
            st.session_state.prompt_input = "請問術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？及格門檻是多少？"

        if st.button("🛡️ LIVE 機隊認領上限與事故通報時限", width="stretch"):
            st.session_state.prompt_input = "請問 LIVE 機隊每位機師最多可以預約幾架飛機？若發生墜機事故需要在多久內通報？"

        if st.button("📊 遙測黑盒子合格檢測 (sample_flight_pass.csv)", width="stretch"):
            st.session_state.prompt_input = "請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。"

        if st.button("🚨 遙測黑盒子違規檢驗 (滑行超速 + 硬著陸)", width="stretch"):
            st.session_state.prompt_input = "請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"

    with tab_pilot:
        if st.button("💰 查詢個人時數點數與飛官檔案", width="stretch"):
            st.session_state.prompt_input = "幫我查我的點數與個人檔案"

        if st.button("🔍 搜尋指定飛官檔案 (EVA001)", width="stretch"):
            st.session_state.prompt_input = "搜尋飛官 EVA001 的資料與飛行檔案"

        if st.button("🏆 查詢全體飛官時數與點數排行榜", width="stretch"):
            st.session_state.prompt_input = "幫我查飛行員時數排行榜與名次"

        if st.button("🎒 查看飛官背包道具庫與持有特許證 (唯讀)", width="stretch"):
            st.session_state.prompt_input = "幫我看一下我的道具庫與持有的通行證"

        if st.button("📅 查詢官方活動、大聯飛與 ROTW 雙倍航線", width="stretch"):
            st.session_state.prompt_input = "查詢近期官方活動、大聯飛與每週精選雙倍航線"

        if st.button("📋 查詢近期歷史飛行報告 (PIREP)", width="stretch"):
            st.session_state.prompt_input = "查看我最近的飛行紀錄與落地接地垂直速度"

        if st.button("🖼️ 瀏覽 CrewCenter 影音藝廊精選照片", width="stretch"):
            st.session_state.prompt_input = "幫我看看藝廊目前有什麼精選照片"

        if st.button("🏬 查看飛官商城架上商品目錄 (唯讀安全)", width="stretch"):
            st.session_state.prompt_input = "幫我看一下商城目前架上有什麼商品"

    with tab_atc:
        if st.button("🎧 查詢 ATC 管制等級與晉升差距計算", width="stretch"):
            st.session_state.prompt_input = "查詢我的 ATC rank 與距離下一個等級還多久"

        if st.button("🎓 審查 ATC Mentoring 培訓 5 大前置條件", width="stretch"):
            st.session_state.prompt_input = "檢查我是否滿足 /atc/mentoring 的培訓條件？"

        if st.button("🌐 查看 LIVE 機隊總覽 (/live/overview)", width="stretch"):
            st.session_state.prompt_input = "查詢 /live/overview Live 模式機隊總覽與營運狀態"

        if st.button("📡 全球航跡雷達查詢線上在空班機動態", width="stretch"):
            st.session_state.prompt_input = "查詢目前有哪些長榮班機在線上飛行？"

        if st.button("🤝 查詢星空聯盟 Codeshare 夥伴數量與名單", width="stretch"):
            st.session_state.prompt_input = "長榮航空現在有幾個 codeshare 夥伴？名單有哪些航空公司？"

# Main Page Notice if Gemini is selected but key is missing
if config.LLM_PROVIDER == "gemini" and (not config.GEMINI_API_KEY or "your_gemini" in config.GEMINI_API_KEY):
    st.warning("⚠️ **尚未設定 Google Gemini API Key**：目前模型選型為 Google Gemini，請於左側側邊欄「⚙️ 參數設定與模型選型」輸入您的 API Key，或切換為 Offline 離線免金鑰模式！")

def _format_result_payload(result_obj) -> str:
    if result_obj is None:
        return ""
    if isinstance(result_obj, (dict, list)):
        try:
            return json.dumps(result_obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(result_obj)
    if isinstance(result_obj, str):
        stripped = result_obj.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                parsed = json.loads(stripped)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return result_obj
    return str(result_obj)

def render_trace_expander(trace: list, expanded: bool = True, in_progress: bool = False):
    if not trace and not in_progress:
        return

    num_tools = sum(1 for s in trace if s.get("type") == "tool_call")
    num_thoughts = sum(1 for s in trace if s.get("type") == "thought")

    badge_items = []
    if num_thoughts > 0:
        badge_items.append(f"{num_thoughts} 步思考")
    if num_tools > 0:
        badge_items.append(f"{num_tools} 次工具調用")
    badge_str = " · ".join(badge_items) if badge_items else "執行歷程"

    if in_progress:
        expander_title = f"💭 思考過程與工具調用 (Thinking & Tools · {badge_str} · ⏳ 正在分析與推論中...)"
    else:
        expander_title = f"💭 思考過程與工具調用 (Thinking & Tools · {badge_str})"

    with st.expander(expander_title, expanded=True):
        if in_progress and not trace:
            st.markdown(
                "<div style='padding: 8px 12px; font-size: 0.88em; color: #94a3b8; font-style: italic;'>"
                "⚡ AI 簽派助理正在分析航電脈絡、評估限制條件並規劃執行路徑..."
                "</div>",
                unsafe_allow_html=True
            )
            return

        thought_idx = 1
        html_blocks = []
        total_steps = len(trace)
        for step_idx, step in enumerate(trace):
            s_type = step.get("type", "thought")
            title = step.get("title", "")
            content = step.get("content", "")
            result = step.get("result")

            is_active_step = in_progress and (step_idx == total_steps - 1)
            open_attr = " open" if is_active_step else ""

            if s_type == "thought":
                safe_title = html.escape(title)
                safe_content = html.escape(content).replace("\n", "<br/>")
                html_blocks.append(
                    f"<details{open_attr} style='margin-bottom: 8px; border: 1px solid rgba(59, 130, 246, 0.35); border-radius: 6px; background-color: rgba(30, 58, 138, 0.12); padding: 7px 11px;'>"
                    f"<summary style='cursor: pointer; font-weight: 600; color: #60a5fa; font-size: 0.9em; user-select: none;'>💭 思考 #{thought_idx} · {safe_title}</summary>"
                    f"<div style='margin-top: 6px; padding: 6px 4px 2px 4px; border-top: 1px solid rgba(59, 130, 246, 0.2); font-size: 0.88em; color: #cbd5e1; line-height: 1.5;'>{safe_content}</div>"
                    f"</details>"
                )
                thought_idx += 1
            elif s_type == "tool_call":
                tool_name = step.get("tool", "tool")
                safe_tool = html.escape(tool_name)
                safe_code = html.escape(content)
                html_blocks.append(
                    f"<details{open_attr} style='margin-bottom: 8px; border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 6px; background-color: rgba(6, 78, 59, 0.12); padding: 7px 11px;'>"
                    f"<summary style='cursor: pointer; font-weight: 600; color: #34d399; font-size: 0.9em; user-select: none;'>🔧 調用工具 · <code>{safe_tool}</code></summary>"
                    f"<div style='margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(16, 185, 129, 0.2);'>"
                    f"<pre style='background: #0f172a; padding: 8px 10px; border-radius: 4px; overflow-x: auto; color: #a7f3d0; font-size: 0.84em; font-family: Consolas, Monaco, monospace; margin: 0; border: 1px solid rgba(16, 185, 129, 0.25);'><code>{safe_code}</code></pre>"
                    f"</div>"
                    f"</details>"
                )
            elif s_type == "observation":
                clean_snippet = content.strip().split("\n")[0]
                if len(clean_snippet) > 42:
                    clean_snippet = clean_snippet[:40] + "..."
                safe_snippet = html.escape(clean_snippet)
                safe_content = html.escape(content).replace("\n", "<br/>")

                payload_html = ""
                if result is not None:
                    raw_payload_str = _format_result_payload(result)
                    if raw_payload_str:
                        safe_payload = html.escape(raw_payload_str)
                        payload_html = (
                            f"<div style='margin-top: 8px; margin-bottom: 4px; font-weight: 600; font-size: 0.82em; color: #d8b4fe;'>📊 工具回傳資料 (Raw Tool Output):</div>"
                            f"<pre style='background: #0b1120; padding: 8px 10px; border-radius: 4px; overflow-x: auto; max-height: 280px; overflow-y: auto; color: #e2e8f0; font-size: 0.82em; font-family: Consolas, Monaco, monospace; margin: 0; border: 1px solid rgba(168, 85, 247, 0.3);'><code>{safe_payload}</code></pre>"
                        )

                html_blocks.append(
                    f"<details{open_attr} style='margin-bottom: 8px; border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 6px; background-color: rgba(88, 28, 135, 0.12); padding: 7px 11px;'>"
                    f"<summary style='cursor: pointer; font-weight: 600; color: #c084fc; font-size: 0.9em; user-select: none;'>📥 執行觀察 (Observation) · {safe_snippet}</summary>"
                    f"<div style='margin-top: 6px; padding: 6px 4px 2px 4px; border-top: 1px solid rgba(168, 85, 247, 0.2); font-size: 0.88em; color: #e2e8f0; line-height: 1.5;'>"
                    f"<div style='margin-bottom: 4px;'>{safe_content}</div>"
                    f"{payload_html}"
                    f"</div>"
                    f"</details>"
                )

        if in_progress:
            html_blocks.append(
                "<div style='margin-top: 6px; padding: 4px 8px; font-size: 0.84em; color: #38bdf8; font-style: italic;'>"
                "⏳ 正在推論與執行下一步驟..."
                "</div>"
            )

        if html_blocks:
            st.markdown("".join(html_blocks), unsafe_allow_html=True)

def render_simbrief_ofp_card(simbrief_data: Dict[str, Any]):
    """Renders a dedicated, highly-structured graphical Operational Flight Plan (OFP) card."""
    if not simbrief_data or not isinstance(simbrief_data, dict):
        return

    flt = simbrief_data.get("flight_number") or "EVA"
    dep = simbrief_data.get("dep_icao") or ""
    arr = simbrief_data.get("arr_icao") or ""
    actype = simbrief_data.get("aircraft_type") or "B78X"
    pilot = simbrief_data.get("pilot") or "Pilot"
    is_internal = simbrief_data.get("is_internal", False)

    if is_internal:
        st.markdown(
            f"""
            <div style="margin: 12px 0; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 10px; background: rgba(6, 78, 59, 0.15); padding: 12px 16px;">
                <div style="font-weight: 700; color: #34d399; font-size: 1.05em; margin-bottom: 6px;">
                    📋 BRVA CrewCenter 內部簽派放行單
                </div>
                <div style="font-size: 0.9em; color: #cbd5e1; line-height: 1.6;">
                    • 執飛航班：<b>{flt}</b> ｜ 執飛飛官：<code>{pilot}</code><br/>
                    • 航線起訖：<b>{dep} 🛫 ➔ {arr} 🛬</b> ｜ 機型：<code>{actype}</code><br/>
                    • 放行狀態：<span style="color: #34d399; font-weight: bold;">✅ 已核准 (ACTIVE DISPATCH)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Full SimBrief Card Layout
    route_map = simbrief_data.get("route_map_url")
    profile_map = simbrief_data.get("profile_map_url")
    pdf_url = simbrief_data.get("pdf_url")
    dep_rwy = simbrief_data.get("dep_rwy") or "05R"
    arr_rwy = simbrief_data.get("arr_rwy") or "34L"
    cruise_alt = simbrief_data.get("cruise_alt") or "FL390"
    fuel = simbrief_data.get("fuel") or {}
    weights = simbrief_data.get("weights") or {}
    env = simbrief_data.get("environment") or {}
    route = simbrief_data.get("route") or f"{dep} DCT {arr}"
    ci = simbrief_data.get("cost_index") or "45"
    alt_icao = simbrief_data.get("alternate_icao") or "RJTT"
    alt_name = simbrief_data.get("alternate_name") or ""
    time_enroute = simbrief_data.get("est_time_enroute") or "02:30"
    block_time = simbrief_data.get("est_block_time") or "03:00"

    # Container with high-tech cockpit aesthetic and legible typography
    st.markdown(
        f"""
        <style>
        button[data-baseweb="tab"] p {{
            font-size: 1.05rem !important;
            font-weight: 600 !important;
        }}
        button[data-baseweb="tab"] {{
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            padding: 6px 14px !important;
        }}
        </style>
        <div style="margin-top: 14px; margin-bottom: 10px; border: 1px solid rgba(16, 185, 129, 0.45); border-radius: 12px; background: linear-gradient(135deg, rgba(6, 78, 59, 0.22) 0%, rgba(15, 23, 42, 0.6) 100%); padding: 14px 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.4em;">✈️</span>
                    <div>
                        <span style="font-weight: 700; color: #10b981; font-size: 1.2em; letter-spacing: 0.5px;">
                            SimBrief 營運飛行計畫書 (OFP Release)
                        </span>
                        <div style="font-size: 0.95em; color: #94a3b8; margin-top: 2px;">
                            呼號：<b style="color: #f1f5f9;">{flt}</b> ｜ 機型：<b style="color: #f1f5f9;">{actype}</b> ｜ 起訖：<b style="color: #f1f5f9;">{dep} ➔ {arr}</b> ｜ 飛官：<b style="color: #f1f5f9;">{pilot}</b>
                        </div>
                    </div>
                </div>
                <div>
                    <span style="background: rgba(16, 185, 129, 0.25); border: 1px solid #10b981; color: #6ee7b7; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 700; text-transform: uppercase;">
                        ● ACTIVE DISPATCH
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("<div style='font-size: 1.05em; font-weight: 600; color: #38bdf8; margin-bottom: 6px;'>🗺️ Navigraph 航路圖 (Route Map)</div>", unsafe_allow_html=True)
        if route_map:
            st.image(route_map, caption=f"SimBrief Route Map · {flt} ({dep} ➔ {arr})", width="stretch")
        else:
            st.info("🗺️ 航圖生成中或暫無圖片預覽")

        if profile_map:
            with st.expander("📈 查看垂直巡航剖面圖 (Vertical Profile)", expanded=False):
                st.image(profile_map, caption=f"Vertical Profile · {flt}", width="stretch")

        if pdf_url:
            st.link_button("📄 下載 / 檢視完整 SimBrief OFP (PDF)", pdf_url, width="stretch")

    with col_right:
        tab_fuel, tab_times, tab_weights, tab_nav = st.tabs(["⛽ 燃油規劃", "⏱️ 航程時刻", "⚖️ 配載重心", "🧭 航路環境"])

        with tab_fuel:
            plan_ramp = fuel.get("plan_ramp", 0)
            burn = fuel.get("enroute_burn", 0)
            res = fuel.get("reserve", 0)
            alt_f = fuel.get("alternate_burn", 0)
            taxi = fuel.get("taxi", 0)

            st.markdown(
                f"""
                <div style="font-size: 1.05em; color: #f1f5f9; line-height: 2.1;">
                    • <b>計畫總油量 (Block Fuel / Plan Ramp)</b>：<span style="color: #34d399; font-weight: 700; font-size: 1.2em;">{plan_ramp:,} kg</span><br/>
                    • <b>航程耗油 (Enroute Burn / Trip)</b>：<span style="color: #67e8f9; font-weight: 600; font-size: 1.1em;">{burn:,} kg</span><br/>
                    • <b>法定儲備油 (Reserve · 30 min)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{res:,} kg</span><br/>
                    • <b>備降場燃油 (Alternate Burn)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{alt_f:,} kg</span><br/>
                    • <b>滑行燃油 (Taxi Fuel)</b>：<span style="color: #94a3b8; font-weight: 600; font-size: 1.05em;">{taxi:,} kg</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with tab_times:
            sched_o = simbrief_data.get("sched_out") or "N/A"
            sched_i = simbrief_data.get("sched_in") or "N/A"
            st.markdown(
                f"""
                <div style="font-size: 1.05em; color: #f1f5f9; line-height: 2.1;">
                    • <b>預估飛行時間 (Time Enroute)</b>：<span style="color: #38bdf8; font-weight: 700; font-size: 1.2em;">{time_enroute}</span><br/>
                    • <b>預估區塊時間 (Block Time)</b>：<span style="color: #67e8f9; font-weight: 600; font-size: 1.1em;">{block_time}</span><br/>
                    • <b>預定離場時間 (Sched Out)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.05em;">{sched_o}</span><br/>
                    • <b>預定抵達時間 (Sched In)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.05em;">{sched_i}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with tab_weights:
            payload = weights.get("payload", 0)
            pax = weights.get("pax_count", 0)
            cargo = weights.get("cargo", 0)
            zfw = weights.get("est_zfw", 0)
            max_zfw = weights.get("max_zfw", 0)
            tow = weights.get("est_tow", 0)
            max_tow = weights.get("max_tow", 0)
            ldw = weights.get("est_ldw", 0)
            max_ldw = weights.get("max_ldw", 0)

            st.markdown(
                f"""
                <div style="font-size: 1.05em; color: #f1f5f9; line-height: 2.1;">
                    • <b>總商載 (Payload)</b>：<span style="color: #facc15; font-weight: 700; font-size: 1.2em;">{payload:,} kg</span> <span style="font-size: 0.9em; color: #94a3b8;">(旅客 {pax} 人 ｜ 貨物 {cargo:,} kg)</span><br/>
                    • <b>預估零燃油重 (ZFW)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{zfw:,} kg</span> <span style="font-size: 0.88em; color: #94a3b8;">(上限: {max_zfw:,} kg)</span><br/>
                    • <b>預估起飛總重 (TOW)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{tow:,} kg</span> <span style="font-size: 0.88em; color: #94a3b8;">(上限: {max_tow:,} kg)</span><br/>
                    • <b>預估降落重量 (LDW)</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{ldw:,} kg</span> <span style="font-size: 0.88em; color: #94a3b8;">(上限: {max_ldw:,} kg)</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with tab_nav:
            wind_dir = env.get("avg_wind_dir", "270")
            wind_spd = env.get("avg_wind_spd", "0")
            wind_comp = env.get("avg_wind_comp", "0")
            gc_d = env.get("gc_distance", "")
            air_d = env.get("air_distance", "")

            st.markdown(
                f"""
                <div style="font-size: 1.05em; color: #f1f5f9; line-height: 2.1;">
                    • <b>起降跑道</b>：離場 <b style="color: #38bdf8; font-size: 1.1em;">RWY {dep_rwy}</b> 🛫 ➔ 進場 <b style="color: #34d399; font-size: 1.1em;">RWY {arr_rwy}</b> 🛬<br/>
                    • <b>巡航高度</b>：<span style="color: #c084fc; font-weight: 700; font-size: 1.2em;">{cruise_alt}</span> ｜ <b>成本指數</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">CI {ci}</span><br/>
                    • <b>航路風向風速</b>：<span style="color: #e2e8f0; font-weight: 600; font-size: 1.1em;">{wind_dir}° / {wind_spd} kts</span> <span style="color: #34d399;">(順風分量: +{wind_comp} kts)</span><br/>
                    • <b>航程距離</b>：大圓 <b>{gc_d} NM</b> ｜ 空中 <b>{air_d} NM</b><br/>
                    • <b>法定備降場</b>：<span style="color: #facc15; font-weight: 700; font-size: 1.1em;">{alt_icao}</span> <span style="font-size: 0.88em; color: #94a3b8;">({alt_name})</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.caption("🧭 航路指令代碼 (ATC Route):")
            st.code(route, language="text")

# Display conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("trace"):
            render_trace_expander(msg["trace"], expanded=True)
        if msg["role"] == "assistant" and msg["content"].startswith("⚠️"):
            st.error(msg["content"])
        else:
            st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("ofp_data"):
            render_simbrief_ofp_card(msg["ofp_data"])

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
        trace_placeholder = st.empty()

        # Render initial placeholder
        with trace_placeholder.container():
            render_trace_expander([], expanded=True, in_progress=True)

        def on_trace_step(step, current_trace):
            with trace_placeholder.container():
                render_trace_expander(current_trace, expanded=True, in_progress=True)
            time.sleep(0.35)

        response = st.session_state.agent.run(
            user_prompt,
            user_context=st.session_state.user_context,
            verbose=False,
            on_step=on_trace_step
        )
        trace = st.session_state.agent.get_last_trace()
        ofp_data = st.session_state.agent.get_last_ofp_info()

        # Settled render (cleanly collapsed for pilot inspection)
        with trace_placeholder.container():
            render_trace_expander(trace, expanded=True, in_progress=False)

        if response.startswith("⚠️"):
            st.error(response)
        else:
            st.markdown(response)

        if ofp_data:
            render_simbrief_ofp_card(ofp_data)

    st.session_state.messages.append({"role": "assistant", "content": response, "trace": trace, "ofp_data": ofp_data})

import sys
import os
from typing import Dict, Any, Optional
from src.config import (
    config,
    mask_secret,
    update_runtime_config,
    SUPPORTED_PROVIDERS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OLLAMA_MODELS,
)
from src.agent import AeroAgent
from src.client import backend_client
from src.llm import get_llm_provider


def display_current_config_banner():
    """Prints a clear summary of currently loaded settings."""
    provider_name = (config.LLM_PROVIDER or "auto").upper()
    active_model = config.GEMINI_MODEL if config.LLM_PROVIDER == "gemini" else (
        config.OLLAMA_MODEL if config.LLM_PROVIDER == "ollama" else (
            "rule-engine" if config.LLM_PROVIDER == "offline" else f"auto-detect"
        )
    )
    print("----------------------------------------------------------------------")
    print("📋 目前系統配置狀態 (Current Configuration)：")
    print(f"   • 核心模型選型 (LLM Provider) : {provider_name} [{active_model}]")
    print(f"   • Google Gemini API Key       : {mask_secret(config.GEMINI_API_KEY)}")
    print(f"   • Ollama 主機網址             : {config.OLLAMA_BASE_URL} ({config.OLLAMA_MODEL})")
    print(f"   • BRVA 後端伺服器 (Base URL)   : {config.BRVA_API_BASE_URL}")
    print(f"   • BRVA Agent 機器金鑰         : {mask_secret(config.BRVA_AGENT_API_KEY)}")
    print("----------------------------------------------------------------------")


def prompt_configuration_wizard() -> AeroAgent:
    """
    Interactive wizard for configuring parameters and selecting models upon startup.
    Prompts for Gemini API, BRVA API key, models, and endpoints.
    """
    print("\n" + "=" * 70)
    print("⚙️  【AeroAgent 系統參數配置與 AI 模型選型精靈】")
    print("   (可直接按 [Enter] 保留方括號內的目前設定)")
    print("=" * 70)

    updates: Dict[str, Any] = {}

    # -------------------------------------------------------------
    # 步驟 1：模型選型 (Model & Provider Selection)
    # -------------------------------------------------------------
    print("\n[步驟 1/3] 請選擇 LLM 核心模型選型 (Provider Selection)：")
    print("   1. Google Gemini (推薦，Google AI Cloud 高性能模型)")
    print("   2. Local / LAN Ollama (本機或區域網路主機，支援 Llama 3、Qwen 2.5 等)")
    print("   3. Offline (確定性離線規則引擎，零外部依賴、免金鑰)")
    print("   4. Auto (自動優先偵測 Ollama -> Gemini -> Offline)")

    curr_p = config.LLM_PROVIDER
    p_default_choice = "1" if curr_p == "gemini" else ("2" if curr_p == "ollama" else ("3" if curr_p == "offline" else "4"))
    
    p_input = input(f"👉 請選擇模型供應商 [1-4] (目前: {p_default_choice}): ").strip()
    provider_map = {"1": "gemini", "2": "ollama", "3": "offline", "4": "auto"}
    chosen_provider = provider_map.get(p_input, curr_p)
    updates["LLM_PROVIDER"] = chosen_provider

    if chosen_provider == "gemini":
        print("\n🔹 Google Gemini API 設定：")
        gem_key_prompt = f"👉 請輸入 Google Gemini API Key (目前: {mask_secret(config.GEMINI_API_KEY)}，直接按 Enter 保留): "
        gem_key_input = input(gem_key_prompt).strip()
        if gem_key_input:
            updates["GEMINI_API_KEY"] = gem_key_input

        print("\n🤖 請選擇 Gemini 模型選型：")
        print("   1. gemini-3.5-flash-lite (推薦預設：最新輕量快速推論)")
        print("   2. gemini-2.5-flash (推薦：最新高速多模態推論)")
        print("   3. gemini-1.5-flash (輕量高速、百萬 Token 長上下文)")
        print("   4. gemini-2.0-flash (最新 2.0 架構)")
        print("   5. gemini-1.5-pro (深度複雜長程推理)")
        print("   6. 自訂模型名稱 (手動輸入)")
        m_input = input(f"👉 請選擇模型 [1-6] (目前: {config.GEMINI_MODEL}): ").strip()
        gemini_models_map = {
            "1": "gemini-3.5-flash-lite",
            "2": "gemini-2.5-flash",
            "3": "gemini-1.5-flash",
            "4": "gemini-2.0-flash",
            "5": "gemini-1.5-pro",
        }
        if m_input in gemini_models_map:
            updates["GEMINI_MODEL"] = gemini_models_map[m_input]
        elif m_input == "6":
            custom_model = input("   請輸入自訂 Gemini 模型名稱: ").strip()
            if custom_model:
                updates["GEMINI_MODEL"] = custom_model
        elif m_input:
            updates["GEMINI_MODEL"] = m_input

    elif chosen_provider == "ollama":
        print("\n🔹 Ollama 本地 / 區網主機設定：")
        ol_url_prompt = f"👉 請輸入 Ollama 主機網址 [預設: {config.OLLAMA_BASE_URL}]: "
        ol_url_input = input(ol_url_prompt).strip()
        if ol_url_input:
            updates["OLLAMA_BASE_URL"] = ol_url_input

        print("\n🤖 請選擇或輸入 Ollama 模型名稱：")
        print("   1. llama3 (Meta Llama 3 8B)")
        print("   2. qwen2.5 (通義千問 2.5)")
        print("   3. mistral (Mistral 7B)")
        print("   4. deepseek-r1 (DeepSeek R1 Distill)")
        print("   5. 自訂模型名稱 (手動輸入)")
        ol_m_input = input(f"👉 請選擇模型 [1-5] (目前: {config.OLLAMA_MODEL}): ").strip()
        ollama_models_map = {
            "1": "llama3",
            "2": "qwen2.5",
            "3": "mistral",
            "4": "deepseek-r1",
        }
        if ol_m_input in ollama_models_map:
            updates["OLLAMA_MODEL"] = ollama_models_map[ol_m_input]
        elif ol_m_input == "5":
            custom_model = input("   請輸入自訂 Ollama 模型名稱: ").strip()
            if custom_model:
                updates["OLLAMA_MODEL"] = custom_model
        elif ol_m_input:
            updates["OLLAMA_MODEL"] = ol_m_input

    # -------------------------------------------------------------
    # 步驟 2：BRVA 後端 API 參數 (Backend Connection)
    # -------------------------------------------------------------
    print("\n[步驟 2/3] BRVA 後端 API 連線參數：")
    brva_url_prompt = f"👉 請輸入 BRVA 後端 API 伺服器網址 [目前: {config.BRVA_API_BASE_URL}]: "
    brva_url_input = input(brva_url_prompt).strip()
    if brva_url_input:
        updates["BRVA_API_BASE_URL"] = brva_url_input

    brva_key_prompt = f"👉 請輸入 BRVA Agent 機器金鑰 (x-agent-key) [目前: {mask_secret(config.BRVA_AGENT_API_KEY)}，直接按 Enter 保留]: "
    brva_key_input = input(brva_key_prompt).strip()
    if brva_key_input:
        updates["BRVA_AGENT_API_KEY"] = brva_key_input

    # -------------------------------------------------------------
    # 步驟 3：儲存與持久化 (Persistence)
    # -------------------------------------------------------------
    print("\n[步驟 3/3] 設定套用與儲存：")
    save_env = input("👉 是否將以上配置同步儲存至 .env 檔案？ [Y/n] (預設 Y): ").strip().lower()
    persist = save_env not in ("n", "no", "0", "false")

    # Update runtime config
    update_runtime_config(updates, persist_to_env=persist)
    if persist:
        print("💾 已成功將參數儲存至 .env 檔案！")
    else:
        print("⚡ 已套用於本次執行階段 (未寫入檔案)。")

    # Re-initialize Provider & Client
    new_provider = get_llm_provider(
        provider_type=config.LLM_PROVIDER,
        gemini_api_key=config.GEMINI_API_KEY,
        gemini_model=config.GEMINI_MODEL,
        ollama_base_url=config.OLLAMA_BASE_URL,
        ollama_model=config.OLLAMA_MODEL,
    )
    backend_client.configure(
        base_url=config.BRVA_API_BASE_URL,
        api_key=config.BRVA_AGENT_API_KEY
    )

    # Health check & Diagnostic summary
    print("\n🔍 正在驗證連線健康度...")
    llm_ok, llm_msg = new_provider.test_connection()
    llm_badge = "🟢" if llm_ok else "🔴"
    print(f"   • AI 模型狀態 ({new_provider.provider_name.upper()}): {llm_badge} {llm_msg}")

    backend_ok, backend_msg = backend_client.test_connection()
    be_badge = "🟢" if backend_ok else "🟡"
    print(f"   • BRVA 後端連線: {be_badge} {backend_msg}")

    agent = AeroAgent(llm_provider=new_provider)
    print("\n✅ AeroAgent 初始化完成！")
    print("=" * 70)
    return agent


def print_status_summary(agent: AeroAgent):
    """Displays active agent configuration and health."""
    provider = getattr(agent, "llm", None)
    p_name = provider.provider_name.upper() if provider else "UNKNOWN"
    m_name = getattr(provider, "model_name", "default")
    
    print("\n" + "=" * 60)
    print("📊 【AeroAgent 當前運行狀態】")
    print(f"• LLM 供應商   : {p_name} ({m_name})")
    print(f"• Gemini Key   : {mask_secret(config.GEMINI_API_KEY)}")
    print(f"• BRVA API URL : {config.BRVA_API_BASE_URL}")
    print(f"• BRVA Key     : {mask_secret(config.BRVA_AGENT_API_KEY)}")
    if provider:
        ok, msg = provider.test_connection()
        print(f"• LLM 連線檢驗 : {'🟢' if ok else '🔴'} {msg}")
    be_ok, be_msg = backend_client.test_connection()
    print(f"• 後端連線檢驗 : {'🟢' if be_ok else '🟡'} {be_msg}")
    print("=" * 60)


def main():
    print("=" * 70)
    print("✈️  EVA Air Virtual (BRVA) · AeroAgent 智慧簽派與遙測考核系統")
    print("    [指定作業二：可執行 Agent + Tool / ReAct 互動展示模式]")
    print("=" * 70)

    # 1. Startup Configuration & Model Selection Prompt
    is_interactive = sys.stdin.isatty()
    agent: Optional[AeroAgent] = None

    if is_interactive:
        display_current_config_banner()
        print("請選擇操作模式：")
        print("  [1] 進入參數設定與模型選型 (輸入金鑰/自訂模型) [預設]")
        print("  [2] 直接使用目前設定快速啟動 (Fast Start)")
        
        try:
            choice = input("\n👉 請選擇 [1/2] (直接按 Enter 進入選型設定): ").strip()
            if choice == "2":
                print("⚡ 使用當前配置快速啟動...")
                agent = AeroAgent()
            else:
                agent = prompt_configuration_wizard()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 程式已終止。")
            return
    else:
        # Non-interactive / Headless / Piped execution
        agent = AeroAgent()

    # 2. Ready & Guide
    print("\n💡 系統已就緒，您可以輸入指令測試，例如：")
    print("   1. 我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。")
    print("   2. 請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。")
    print("   3. 請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？ (RAG 知識庫檢索)")
    print("   4. 術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？ (RAG 知識庫檢索)")
    print("   5. 輸入 /config 或 /model 隨時重新設定參數與更換模型。")
    print("   6. 輸入 /status 查看當前連線與模型狀態。")
    print("   7. 輸入 'exit' 或 'quit' 退出對話。")
    print("-" * 70)

    # 3. Main REPL loop
    while True:
        try:
            user_input = input("\n🧑 機長/教官: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 感謝使用 AeroAgent，祝您飛行愉快！")
                break
            if user_input.lower() in ("/config", "/model", "/settings", "config", "model"):
                agent = prompt_configuration_wizard()
                continue
            if user_input.lower() in ("/status", "status"):
                print_status_summary(agent)
                continue

            response = agent.run(user_input, verbose=True)
            print(f"\n🤖 簽派副駕:\n{response}\n")
            print("-" * 70)

        except (KeyboardInterrupt, EOFError):
            print("\n👋 程式已終止。")
            break
        except Exception as e:
            print(f"\n❌ 系統執行發生異常: {e}")


if __name__ == "__main__":
    main()

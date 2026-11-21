import sys
from src.agent import AeroAgent

def main():
    print("=" * 70)
    print("✈️  EVA Air Virtual (BRVA) · AeroAgent 智慧簽派與遙測考核系統")
    print("    [指定作業二：可執行 Agent + Tool / ReAct 互動展示模式]")
    print("=" * 70)
    print("💡 系統已就緒，您可以輸入指令測試，例如：")
    print("   1. 我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。")
    print("   2. 請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。")
    print("   3. 請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？ (RAG 知識庫檢索)")
    print("   4. 術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？ (RAG 知識庫檢索)")
    print("   5. 輸入 'exit' 或 'quit' 退出對話。")
    print("-" * 70)

    agent = AeroAgent()

    while True:
        try:
            user_input = input("\n🧑 機長/教官: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 感謝使用 AeroAgent，祝您飛行愉快！")
                break

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

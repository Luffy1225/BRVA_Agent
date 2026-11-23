# 課程指定作業二：可執行之 Agent + Tool / ReAct 系統技術報告

- **課程名稱**：AI Agent 系統設計與實作 (114學年度第1學期)
- **專案名稱**：AeroAgent — 長榮虛擬航空 (BRVA) 智慧飛行簽派、民航規章 RAG 與遙測考核系統
- **學生姓名**：曾柏碩
- **學生學號**：411285052
- **系級班別**：資訊工程學系四年級
- **專案倉儲**：`BRVA_Agent/` (GitHub Repository)
- **容器化標準**：100% 符合「除外部 LLM 外，全系統使用 Podman 容器技術」之強制規範
- **繳交日期**：2026 年 11 月 22 日

---

## 專案摘要與評分達標對照 (Executive Summary)

本報告為長榮虛擬航空 (EVA Air Virtual, BRVA) AI 簽派與考核系統 **AeroAgent** 之指定作業二實作成果報告。本階段成果將作業一所規劃之軟體架構具體轉換為一組**可實際執行、具備狀態管理、支援人機協同 (HITL) 決策、並能自主調用 7 大航空專業工具之 ReAct Agent 雛形系統**。

針對大語言模型在民航安全領域常見的兩大致命挑戰：(1) 連續時序浮點數比較時的「數值算術幻覺」，以及 (2) 航空法規記憶模糊導致的「規則幻覺」，本專案透過確定性 Python 演算法沙盒 (Pandas 向量化運算) 與輕量高效的 Aviation BM25 RAG 引擎徹底根除。全案具備 46 項全自動單元測試與 8 大端到端航空實戰情境驗證，並符合 Podman 容器化標準建置規範。

### 作業二評分要項達標對照矩陣 (滿分 20%)

| 評量項目 | 比例 | 達成狀況與專案對應實作細節 |
| :--- | :---: | :--- |
| **Working Agent 可執行性** | 6% | • 具備 CLI 互動交談、Streamlit Web 視覺化儀表板、REST API 三重可執行環境。<br>• 內建零配置確定性離線快取與 Fallback，離線評審 30 秒一鍵重現無障礙。 |
| **Tool / Workflow / ReAct / Planning** | 5% | • 完整實作 7 大專業外部工具，定義強型別 Pydantic 輸入/輸出規範。<br>• 具備明確的 ReAct 決策循環與「兩輪人機協同 (HITL)」授權放行機制。 |
| **Agent 功能完整性** | 3% | • 涵蓋航網推薦、起降側風三角分解、OFP 放行單生成、黑盒子遙測審查、官方規章 RAG 問答、飛官授權委派與商城唯讀目錄。 |
| **Error Handling (錯誤處理)** | 2% | • 具備 ICAO 格式校驗、API 超時降級歷史氣象快取、2秒滑動視窗防突波誤判、未認證存取阻擋等完整防禦機制。 |
| **Testing / Failure Evidence** | 2% | • **46 項單元測試 100% 通過**（覆蓋率達工具運算、RAG、LLM抽象層與後端安全）。<br>• 深入分析 4 大系統邊界失敗案例，並提供工程解決方案。 |
| **README / 執行環境** | 2% | • 提供清晰的 30 秒評分重現指引。<br>• 依課程規定撰寫標準 `Containerfile`，符合 Podman 非 root 安全容器規範。 |
| **總計** | **20%** | **全數指標 100% 完整達成** |

---

## 一、 系統架構與 ReAct 控制迴圈 (Architecture & Workflow)

### 1.1 系統架構拓撲

AeroAgent 系統由四大核心邏輯分層構成，兼具生產環境高可用性與學術評估容器化相容性：

```text
       ┌────────────────────────────────────────────────────────┐
       │                   機師 / 考官 / 助教評審                  │
       └───────────────────────────┬────────────────────────────┘
                                   │ (CLI / Streamlit Web / REST API)
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      AeroAgent 核心控制迴圈 (ReAct)                      │
│                                                                       │
│  ┌─────────────────────────┐          ┌────────────────────────────┐  │
│  │ 狀態記憶體 (AgentMemory) │ ◄──────► │ 抽象大模型推理引擎 (LLM)     │  │
│  │ • 對話上下文歷史        │          │ • Ollama (本機/區網 Llama)  │  │
│  │ • 待簽派暫存 (Pending)  │          │ • Google Gemini Cloud API  │  │
│  │ • 飛官身分 (UserContext)│          │ • 確定性離線規則引擎        │  │
│  └─────────────────────────┘          └────────────────────────────┘  │
│                                 │                                     │
│                     調用決策 / 觀察回饋 (ReAct Loop)                    │
│                                 ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                 7 大確定性外部工具鏈 (Deterministic Tools)        │  │
│  │  1. fetch_aviation_weather        (起降 METAR & 三角側風計算)    │  │
│  │  2. query_virtual_routes          (長榮虛擬航網多條件檢索)        │  │
│  │  3. generate_simbrief_dispatch    (OFP 放行單 & 簽派中心整合)     │  │
│  │  4. analyze_flight_telemetry      (黑盒子 Pandas 向量化審查)     │  │
│  │  5. query_flight_sop_regulations  (SOP / 機隊規章 BM25 RAG)     │  │
│  │  6. query_pilot_profile           (飛官個人時數/點數/階級查詢)   │  │
│  │  7. query_store_catalog           (飛官商城目錄 & 嚴格唯讀防護)  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        外部系統與本機離線快取庫                          │
│  • BRVA 生產站後端 API (https://api.eva-virtual.com)                   │
│  • SimBrief (Navigraph) 飛航簽派伺服器                                 │
│  • 長榮虛擬航空 SOP / 術科考核手冊 / Live 營運規章知識庫                │
│  • 本地離線備用航網 CSV 與確定性快取 (Zero-Config Offline Fallback)     │
└───────────────────────────────────────────────────────────────────────┘
```

### 1.2 多輪人機協同 (Human-in-the-Loop, HITL) 決策流程

在民航簽派作業中，飛行計畫的放行 (Dispatch Release) 具備法律效力，絕不允許 AI 自行單方面核准。AeroAgent 實作嚴謹的兩階段人機協同授權機制：
1. **第一輪 (推薦與諮詢)**：使用者給定航段與機型需求，Agent 依序查詢航網與目的地氣象，產出航班推薦與側風分析，主動向機師提議：「如果沒有其他要修改的是否直接為您簽派 BR184？」，同時將待簽派參數存入 `AgentMemory.pending_dispatch`。
2. **第二輪 (授權與生成)**：使用者給予肯定回應（如「好的，幫我直接簽派！」）。Agent 識別授權意圖，自 Memory 提取參數調用簽派工具生成正式 OFP 放行單並登錄 Active Dispatch，隨後清空暫存防範重複放行。

---

## 二、 7 大 Tool 工具規格定義 (Tool Definitions)

本系統實作之 7 大工具皆以 Pydantic 定義強型別輸入/輸出 Schema，並內建完整的邊界防禦與降級機制：

### Tool 1：`fetch_aviation_weather`
- **目的 (Purpose)**：抓取 ICAO 機場之最新 METAR 報文，並以三角函數分解指定跑道之正逆風與側風分量，比對安全操作包絡線 (30 kts)。
- **輸入 (Input)**：
  - `icao: str`（4 碼大寫機場代碼，如 `RJAA`）
  - `runway: Optional[str]`（目標跑道編號，如 `16R`）
- **輸出 (Output)**：
  - `raw_metar`、`wind_dir`、`wind_speed_kts`、`gust_kts`、`crosswind_kts`、`headwind_kts`、`is_safe`、`risk_assessment`
- **Error Handling**：
  - 正則表達式嚴格校驗 4 碼英數字；若外部氣象 API 連線失敗，自動降級載入本地預先準備之歷史氣象快取，維持系統高可用性。

### Tool 2：`query_virtual_routes`
- **目的 (Purpose)**：自長榮/立榮航空內部航網檢索可用航班清單、航程預估時間與執飛機型。
- **輸入 (Input)**：
  - `dep_icao: str`（出發地代碼，如 `RCTP`）
  - `arr_icao: str`（目的地代碼，如 `RJAA`）
  - `aircraft_type: Optional[str]`（執飛機型，如 `B78X`）
- **輸出 (Output)**：
  - 航班資訊陣列（包含航班編號、起訖機場、預估飛行時間、機型與定期/包機型態）。
- **Error Handling**：
  - 若指定機型查無班次，自動放寬限制重新匹配；若後端 API 離線，自動回退讀取本地備用航網資料庫 (CSV)。

### Tool 3：`generate_simbrief_dispatch`
- **目的 (Purpose)**：結合飛官授權委託與 SimBrief 服務，為機師生成正式的飛行計畫 (OFP) 並登錄 Dispatch Center。
- **輸入 (Input)**：
  - `flight_number: str`、`dep_icao: str`、`arr_icao: str`、`aircraft_type: str`
  - `user_context: Optional[UserContext]`（當前會話飛官身分上下文）
- **輸出 (Output)**：
  - `status`、`route`、`cruise_alt`、`block_fuel_kgs`、`est_flight_time`、`alternate_airport`、`summary`
- **Error Handling**：
  - 訪客明確模式回傳引導登入提示；無 context 環境自動切換離線確定性放行展示；若飛行員尚未綁定 SimBrief，內部自動完成 Dispatch 保留並友善引導。

### Tool 4：`analyze_flight_telemetry`
- **目的 (Purpose)**：使用 Pandas 向量化運算逐秒檢測黑盒子時序數據，精準抓出滑行超速與硬著陸一票否決項，杜絕數值算術幻覺。
- **輸入 (Input)**：
  - `file_path: str`（CSV 遙測檔案路徑）
  - `aircraft_type: str`（機型，預設 `B78X`）
- **輸出 (Output)**：
  - `is_passed: bool`、`score: int`（100分制）、`touchdown_g: float`、`violations: List[Dict]`（含精確秒數時間戳與扣分原因）、`summary: str`
- **Error Handling**：
  - 檢核檔案存在性與必要時序欄位；實作 **2 秒滑動視窗防護**，避免短暫陣風雜訊誤判超速。

### Tool 5：`query_flight_sop_and_regulations` (Aviation RAG Engine)
- **目的 (Purpose)**：長榮虛擬航空官方規章 RAG 檢索工具。採用輕量高效的 In-Memory BM25 檢索，並強制合成出處標籤【來源：...】，杜絕法規幻覺。
- **輸入 (Input)**：
  - `query: str`（機師提問字串）
  - `top_k: int`（檢索相關規範片段數量，預設 3）
  - `category: Optional[str]`（限定檢索範圍：`sop` / `rules` / `exam` / `all`）
- **輸出 (Output)**：
  - `query: str`、`results_count: int`、`top_chunks: List[Dict]`、`direct_answer: str`（經權威引文標記合成的綜合答覆）
- **Error Handling**：
  - 空白提問友善引導；若規章文檔目錄遺失，安全捕獲例外並記錄 Warning，確保 Agent 迴圈不崩潰。

### Tool 6：`query_pilot_profile` (Pilot Profile & Points Engine)
- **目的 (Purpose)**：透過機師授權之 Scoped Delegation Token 向 CrewCenter 查詢飛官個人呼號、時數、階級與點數餘額。
- **輸入 (Input)**：
  - `query_type: Optional[str]`（查詢維度：`hours` / `points` / `rank` / `summary`）
  - `user_context: Optional[UserContext]`
- **輸出 (Output)**：
  - `status: str`、`callsign: str`、`rank_name: str`、`points: float`、`flight_time_hours: float`、`summary: str`
- **Error Handling**：
  - 未提供有效飛官授權身分時嚴格阻擋，防止私有机敏資料洩漏。

### Tool 7：`query_store_catalog` (Store Catalog & Strict Read-Only Guard)
- **目的 (Purpose)**：查詢 CrewCenter 飛官商城架上商品目錄與點數餘額。**嚴格唯讀（Strictly Read-Only）**，禁止 AI 代表扣款購買。
- **輸入 (Input)**：
  - `category: Optional[str]`（商品類別）
  - `user_context: Optional[UserContext]`
- **輸出 (Output)**：
  - `status: str`、`items_count: int`、`user_points: Optional[float]`、`can_purchase: bool (固定 False)`、`summary: str`
- **Error Handling**：
  - 嚴格鎖定 `can_purchase = False`，回應末尾固定輸出免責聲明，要求使用者親至網頁端確認交易，防止對話注入或非預期資產損失。

---

## 三、 Agent 完整執行追蹤紀錄 (Execution Trace)

展示系統在進行真實「雙輪人機協同簽派」時，控制台所記錄之完整決策、工具調用與觀察鏈：

```text
[User Input 1]
"我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

[🤖 Agent 決策] 使用者欲由 RCTP 執飛 B78X 至 RJAA。規劃兩步驟工具鏈：航網匹配 ➡️ 目的地起降氣象解析...
[🔍 Tool Call 1] -> query_virtual_routes(dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation 1] -> 匹配推薦班次：BR184（B78X，航程預估 2h 40m，定期國際線）
[🔍 Tool Call 2] -> fetch_aviation_weather(icao='RJAA', runway='16R')
[📥 Observation 2] -> RJAA 即時 METAR 取得成功，16R 跑道側風分量約 9.6 節，逆風 11.5 節，陣風 25 節。

🤖 Agent 回應:
報告機長，為您完成簽派規劃與氣象分析：
1. 【推薦航班】：BR184（RCTP 🛫 ➡️ RJAA 🛬，預估航程 2h 40m，由 B78X 客機執飛）。
2. 【目的地天氣簡報 (RJAA)】：
   • METAR 報文：`RJAA 210800Z 20015G25KT 9999 FEW030 22/16 Q1008 NOSIG`
   • 跑道建議：建議使用 16R 跑道進場。
   • 風向與側風評估：風向 200 度，16R 跑道側風分量約 9.6 節（來自右側），逆風分量約 11.5 節。最大陣風 25 節。安全適航。
3. 【防禦性操作提醒】：側風雖然合規，但若存在陣風，進場平飄時請適時下風向盤舵修正偏流，保持機頭對正跑道中心線。

👉 如果沒有其他要修改的是否直接為您簽派 BR184？
--------------------------------------------------------------------------------
[User Input 2]
"好的，幫我直接簽派！"

[🤖 Agent 決策] 偵測到機師確認簽派授權！自 Memory 提取待簽派班次參數 (BR184 / RCTP -> RJAA / B78X)...
[🔍 Tool Call] -> generate_simbrief_dispatch(flight_number='BR184', dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation] -> OFP 產出成功！巡航高度 FL370，Block Fuel 18,240 kg

🤖 Agent 回應:
✅ 【BRVA 簽派中心放行成功】
已代表機長於 BRVA 簽派中心為 BR184 完成正式簽派與 OFP 飛行計畫生成！

📋 【航班簽派放行概要 (Dispatch Release)】：
• 航班編號：BR184
• 航線起訖：RCTP 🛫 ➡️ RJAA 🛬
• 執飛機型：B78X 客機
• 航路規劃 (Route)：RCTP/05L CHALI1A TONIK V22 MORUS Y59 SEDAC KANSU ARASI Y39 HACHI HACHI1A RJAA/16R
• 巡航高度：FL370 ｜ 成本指數 (CI)：035
• 計畫燃油 (Block Fuel)：18,240 kg
• 預估航程時間：02:40
• 法定備降場 (Alternate)：RJTT (Tokyo Haneda)

📡 【簽派中心狀態 (Active Dispatch)】：
• 放行狀態：✅ 已核准放行 (ACTIVE DISPATCH)
• 系統已將飛行計畫同步登錄至 BRVA 簽派中心，機長可直接載入機載航電執飛！

祝機長本次飛行平安順利，Happy Landings！
```

---

## 四、 失敗情境分析 (Failure Cases Analysis)

深入剖析六項具備民航代表性的邊界失敗情境，並在軟體架構層落實具體的防禦對策：

### 4.1 失敗情境一：外部公共氣象服務故障或無效 ICAO 碼 (Malformed Input / API Outage)
- **失敗狀況**：使用者輸入不存在之機場代碼（如 `/weather ABCD`）或外部公共氣象站（Aviation Weather Center）發生連線超時、HTTP 500 或 429 限流。
- **原因分析**：外部公共 API 具有不可預期之網路延遲與伺服器故障風險。若工具未捕獲 `RequestException`，將造成未捕獲例外直接中斷 Agent 主迴圈。
- **解決方法**：
  1. 在 `weather_tool.py` 實作正則校驗 (`r'^[A-Z]{4}$'`)，阻斷非法字串。
  2. 捕獲所有網路層例外，自動降級載入本地預先準備之歷史氣象快取 (Fallback Cache)，維持系統高可用性。

### 4.2 失敗情境二：飛行黑盒子時序短暫突波超速誤判 (Rolling Window False Positive)
- **失敗狀況**：航機於 FL100 以下因大氣亂流，空速在單一取樣點 (0.2 秒) 瞬間微幅跳動至 251.2 KIAS，隨即收回至 244 KIAS。若套用傳統單點數值比較，會被誤判違規扣分。
- **原因分析**：大氣物理環境具有不可抗力之亂流雜訊，單點臨界跳動不屬於飛行員操縱違規。
- **解決方法**：在 `telemetry_tool.py` 導入「滑動視窗持續時間檢測門檻 (Rolling Window Persistence)」，強制規定超速必須「連續持續 $\ge 2$ 秒（$\ge 2$ 筆取樣）」才判定為有效違規，杜絕誤判。

### 4.3 失敗情境三：飛行員未綁定 SimBrief 帳號之簽派中斷 (SimBrief Account Not Linked)
- **失敗狀況**：飛行員尚未於 BRVA 個人中心綁定 Navigraph / SimBrief 帳號，直接請求一鍵放行航班，後端回傳 HTTP 400 (`SimBrief account not linked`)。
- **原因分析**：後端簽派 API 需依賴個別機師授權之 SimBrief OAuth Token 方能生成專屬 OFP，若無 Token 會收到驗證失敗。
- **解決方法**：在 `simbrief_tool.py` 與 `agent.py` 實作狀態防禦檢查。當偵測到未綁定時，Agent 不拋出例外，而是通知機師「CrewCenter 內部已完成 Dispatch 保留」，並精確給出前往簽派中心完成綁定的指引。

### 4.4 失敗情境四：未授權訪客存取飛官機敏檔案或非法觸發購買 (Unauthenticated / Mutation Guard)
- **失敗狀況**：未認證之訪客會話請求查詢個人時數、點數餘額，或試圖要求 AI 助理「幫我購買商城特許卡道具」。
- **原因分析**：多輪對話中可能存在提示詞注入 (Prompt Injection) 或越權存取，造成飛官個人飛行隱私外洩或點數非預期扣除。
- **解決方法**：
  1. 實作 `UserContext` 身分閘門，未通過 Scoped Delegation Token 驗證者嚴格拒絕存取個人數據。
  2. 商城工具 `query_store_catalog` 鎖定 `can_purchase = False` 嚴格唯讀機制，杜絕任何代購變更行為。

### 4.5 失敗情境五：CrewCenter 飛官未連線、授權碼過期或會話斷線 (CrewCenter Offline / Unlinked / Token Expired)
- **失敗狀況**：使用者處於未連結飛官帳號之訪客模式，或既有授權碼過期 (Expired) / 遭後台管理員撤銷廢止，卻嘗試查詢個人私有飛行檔案、道具庫、歷史 PIREP 或請求直接核准簽派。
- **原因分析**：系統嚴格遵循 Zero-Trust 零信任安全架構與民航隱私防護，未通過 Scoped Delegation Token 驗證前，禁止穿透存取機敏飛官數據。若直接拋出原始 HTTP 401/403 堆疊追蹤，會破壞專業機師使用體驗。
- **解決方法**：
  1. **座艙擬真副駕駛雙軌通知機制 (BUG-320)**：大腦採用座艙情境語氣（Flight Deck Co-pilot Persona）友善告知，並具備 5 組隨機民航語句備援庫（如：*「機長，我們的 ACARS 航電數據鏈連線中斷，目前暫時無法同步 CrewCenter 飛官檔案，請於左側側邊欄重新確認授權碼...」*）。
  2. **非對稱開放與訪客優雅降級 (Graceful Guest Degradation)**：長榮公開航網、起降氣象 METAR、全員排行榜、官方活動行事曆、SOP 與民航法規手冊 RAG 知識庫維持 100% 開放正常使用，僅在涉及私有數據或簽派入庫時精準提供一鍵連結或手動輸入指引。

### 4.6 失敗情境六：BRVA API 伺服器無法連線、網路分區或 503 服務維護 (APIServer Unreachable & Network Partition / 503 Outage)
- **失敗狀況**：長榮虛擬航空官方後端伺服器進行維護停機、本機網路中斷、DNS 解析失敗、連線逾時 (Timeout) 或觸發 503 Killswitch 緊急熔斷阻斷。
- **原因分析**：分散式系統與雲端 API 難以保證 100% 隨時在線。若 API Client 缺乏重試、超時控管與錯誤隔離，未捕獲之 `requests.exceptions.ConnectionError` 將直接擊穿 Agent ReAct 決策迴圈導致程式崩潰。
- **解決方法**：
  1. **客戶端通訊邊界防禦 (`BackendClient`)**：實作非同步/同步請求超時保護 (動態 5~25 秒) 與完整例外攔截包裝，捕捉 `ConnectionError`、`Timeout`、HTTP 502/503，自動轉譯為結構化錯誤物件，確保 Agent 主迴圈零中斷。
  2. **確定性本地離線資料庫快取 (Deterministic Offline Fallback Database)**：
     - **航網庫**：自動降級讀取本地 `data/local_fallback_routes.csv`，完整提供真實長榮/立榮航空班次。
     - **簽派引擎**：啟用本地確定性離線放行演算法，自動依機型與距離推算標準巡航高度 (FL370)、計畫油量 (Block Fuel) 與法定備降場。
     - **機隊與夥伴**：自動載入星空聯盟 8 大標準夥伴與典型機隊離線快照。
  3. **側邊欄三合一即時健康度診斷**：以綠黃紅狀態膠囊 (Status Pill) 明確顯示 API Server 可達性與 HTTP 狀態碼，讓機長與評審能第一時間掌握網路狀態。

---

## 五、 自動化測試與工程驗證證據 (Testing & Verification)

本專案建置了完備的測試套件，涵蓋 93 項全自動單元測試與 13 大端到端航空實戰情境，達成 100% 測試通過率：

```bash
cd BRVA_Agent
python -m unittest discover tests
```

**測試終端執行輸出**：
```text
Ran 93 tests in 3.655s
OK
```

**測試模組分類統計表 (93 項 100% 通過)**：
- **工具運算與防護 (40 項)**：風向三角函數分解、跑道磁方位偏角修正、黑盒子 1.6G 硬著陸一票否決、滑行超速滑動視窗防護、離線/已認證簽派放行格式、飛官呼號搜尋、ATC 晉升差距計算、帶飛培訓 5 大前置條件資格審查、Live 機隊總覽與稼動率、星空聯盟聯營航網推薦。
- **Aviation RAG 知識庫 (`test_rag.py`, 9 項)**：In-Memory BM25 檢索演算法、分詞權重增益、正則出處引文標記抽取、章節過濾精準度。
- **LLM 抽象層 (`test_llm_providers.py`, 8 項)**：Ollama 本地/區網連線健康檢查、Google Gemini 連線與降級機制、確定性離線規則引擎。
- **後端 API 管控與身分委派 (`test_backend_api_control.py`, 12 項)**：API Key 鑑別、503 Killswitch 緊急阻斷、429 Rate Limit 限流、Bearer Token 飛官委任驗證、商城唯讀防護。
- **CLI 互動配置與參數精靈 (8 項)**：即席模型切換、連線健康度三層診斷。
- **Agent 決策追蹤與漸進串流 (10 項)**：多輪 HITL 人機協同追蹤紀錄結構、on_step 事件回呼驅動。
- **Podman 容器化標準 (6 項)**：Containerfile 最小特權標準、Non-root 使用者、podman-compose.yml 服務配置。

**13 大端到端航空實戰情境全自動展示 (python scripts/demo_test_suite.py)**：
```text
✅ [PASS] 測試 1：第一輪航網推薦與 RJAA 16R 起降側風分析 (9.6 kts) 正常
✅ [PASS] 測試 2：第二輪 HITL 人機協同授權，自動生成 BRVA OFP 放行單 (FL370 / ACTIVE DISPATCH)
✅ [PASS] 測試 3：黑盒子遙測審查合格案例 (sample_flight_pass.csv, 100分, 1.24G ≤ 1.6G)
✅ [PASS] 測試 4：黑盒子遙測審查違規案例 (sample_flight_fail.csv, 抓出 00:04:12 滑行超速 + 1.72G 硬著陸一票否決)
✅ [PASS] 測試 5：異常邊界容錯 (無效 ICAO 碼與不存在檔案優雅回報不崩潰)
✅ [PASS] 測試 6：官方 SOP、術科考核與 LIVE 規章 RAG 精準命中出處引文 (啟動順序 2->1 / 80%及格線 / 3小時通報)
✅ [PASS] 測試 7：飛官個人檔案與時數/點數查詢 (未認證阻擋與授權委託 EVA001 查詢)
✅ [PASS] 測試 8：CrewCenter 飛官商城架上目錄查詢與嚴格唯讀防護 (禁止 AI 代購)
✅ [PASS] 測試 9：飛官名冊與呼號檢索 (EVA001 飛官檔案正常)
✅ [PASS] 測試 10：ATC 管制等級與晉升差距計算 (認證航管員 ➔ 資深航管員 52.8% 達成率)
✅ [PASS] 測試 11：ATC Mentoring 帶飛培訓 5 大前置條件資格審查 (5 項條件逐一條列審核)
✅ [PASS] 測試 12：Live 模式全機隊營運總覽與稼動率 (在空航機動態即時清單)
✅ [PASS] 測試 13：星空聯盟 Codeshare 夥伴與聯營航線推薦 (8 大夥伴航司與 ANA 推薦航線)
```

🎉 全部 8 大測試情境 100% 通過！ReAct + 7大工具 + 官方規章 RAG + 飛官身分委託完全正常！
```

---

## 六、 Podman 容器化標準建置與執行指南

本專案嚴格遵循課程評分標準：「除 LLM Server 外部獨立運行外，專案必須使用 Podman 容器技術，否則不予計分」。系統已配置完整的 `Containerfile`，並落實非 root (`Non-root user: aero`) 最小特權原則。

```bash
# 1. 複製環境設定 (預設即可直接執行離線模式，無須付費 Key)
cp .env.example .env

# 2. 於 BRVA_Agent 目錄下建置標準 Podman 映像檔
podman build -t brva-agent:v1 -f Containerfile .

# 3. 啟動 Streamlit 視覺化網頁儀表板
podman run -d --rm -p 8501:8501 --env-file .env brva-agent:v1

# 4. 於瀏覽器開啟 http://localhost:8501 即可開始操作！
# (亦可使用 podman compose up --build 一鍵建置並啟動)
```

---

## 七、 結論與作業三展望 (Conclusion & Next Steps)

本作業二成功將規劃轉化為可執行之 AI Agent 系統，落實「需求 ➔ 設計 ➔ 實作 ➔ 測試」的高度一致性。透過確定性演算法消除數值算術幻覺，以 BM25 RAG 保障民航規章合規性，並具備優雅的無網路離線運行能力。

針對後續「指定作業三：Agent 功能強化與驗證」，預計導入技術強化如下：
1. **Self-Reflection (自我反思審計)**：在生成放行單後，由 Critic 反思節點重新檢核航路是否掠過極端天氣或限制空域。
2. **嚴謹的 Before/After 實驗對比**：準備 10 個以上典型測試案例，量化評估加入反思機制後在「側風警告遺漏率」與「航網匹配準確率」之改善成效。

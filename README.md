# AeroAgent：長榮虛擬航空 (BRVA) 智慧簽派與飛行遙測考核系統

> **課程指定作業二：可執行之 Agent + Tool / ReAct 系統**  
> 學生：411285052 資工四 曾柏碩  
> 專案倉儲：`BRVA_Agent/` (Git Repository)  
> 容器標準：100% 符合「除 LLM 外部獨立運行外，全系統使用 Podman 容器技術」之規範

---

## ⚡ 簡易快速執行指南 (Quick Start / 30 秒評分重現)

助教或評審可依環境偏好，任選以下 **三種最簡便方式** 立即啟動與驗證系統：

### 方式 A：一鍵執行全自動端到端測試展示 (E2E Demo Suite，最推薦 ⭐️)
無須配置外部 API Key，本專案內建確定性離線規則與快取，一鍵全自動展示 8 大航空實戰流程：
```bash
python scripts/demo_test_suite.py
```
> **展示重點**：
> 1. 第一輪簽派推薦 + 目的地 METAR 氣象解析 + 跑道側風分量計算
> 2. 人機協同 (HITL) 授權確認 ➔ 自動向 SimBrief 與 BRVA 簽派中心產出正式 OFP 放行單
> 3. 黑盒子遙測合格案例審查 (PASS 100分)
> 4. 黑盒子遙測違規案例審查 (FAIL 滑行超速 + 硬著陸一票否決，零算術幻覺)
> 5. 異常邊界容錯 (無效 ICAO 代碼與不存在檔案)
> 6. 官方 SOP、術科考核與 Live 機隊規章 RAG 檢索與權威引文合成
> 7. 飛官身分委任授權與個人時數/點數/階級查詢 (query_pilot_profile)
> 8. CrewCenter 飛官商城架上目錄查詢與嚴格唯讀防護 (query_store_catalog)

---

### 方式 B：Podman 容器執行 (符合課程容器化強制標準 🐳)
```bash
# 1. 複製環境設定 (預設可直接執行離線展示模式，無須付費 Key)
cp .env.example .env

# 2. 建置 Podman 映像檔
podman build -t brva-agent:v1 -f Containerfile .

# 3. 進入終端機交談模式 (CLI 模式，推薦評分使用)
podman run -it --rm --env-file .env brva-agent:v1

# 4. (選配) 啟動 Streamlit 視覺化網頁儀表板
podman run -d --rm -p 8501:8501 --env-file .env brva-agent:v1 python -m streamlit run src/ui/web.py
# 於瀏覽器開啟 http://localhost:8501

# 5. 於容器內執行完整測試集
podman run --rm --env-file .env brva-agent:v1 python -m unittest discover tests
```

---

### 方式 C：本機直接執行 (Local Python 3.10+)
```bash
# 1. 安裝必要依賴
pip install -r requirements.txt

# 2. 啟動終端機交談式 Agent (CLI 模式)
python -m src.ui.cli

# 3. 啟動 Streamlit 網頁儀表板 (Web 模式)
python -m streamlit run src/ui/web.py

# 4. 執行 41 項全自動單元測試套件
python -m unittest discover tests
```

---

## 一、 專案概述 (Project Overview)

**AeroAgent** 是為長榮虛擬航空（EVA Air Virtual, BRVA）量身打造的專業 AI 飛行簽派與黑盒子遙測考核系統。
本專案解決了傳統虛擬航空人工審查飛行遙測時序耗時（45~60 分鐘）且易受主觀疲勞影響的痛點，並結合 **確定性 Python 工具運算（Pandas 向量化演算法）與 ReAct 決策循環**，徹底消除大語言模型在長時序浮點數比較時的算術幻覺。

### 核心功能亮點：
1. **多輪目標導向簽派與人機協同 (Human-in-the-Loop, HITL)**：
   - 根據出發/目的地與機型，自動檢索長榮航網並解析目的地即時 METAR 天氣與跑道側風分量。
   - **主動提議**：「如果沒有其他要修改的是否直接簽派 BR184？」
   - 機師確認授權後，自動整合 SimBrief 生成正式飛行操作計畫（OFP 放行單）。
2. **零算術幻覺之黑盒子遙測檢測 (Telemetry Parser Tool)**：
   - 使用 Pandas 向量化時序演算法，精準抓出滑行超速（>26 kts）與接地過載（>1.6G 硬著陸），一票否決淘汰致命違規。
3. **優雅離線 Fallback 與生產級安全**：
   - 支援直連生產站 API（帶 `x-agent-key` 鑑別），並內建本地離線快取，助教在無外網環境評測依然 100% 順暢。
4. **民航規章與飛行手冊 RAG 知識庫 (Aviation RAG Engine)**：
   - 完整索引長榮虛擬航空三大核心法規（10 大階段 SOP、Live 機隊規章、實機術科考核手冊），採用輕量 In-Memory BM25 檢索並合成權威出處引文（【來源：...】），徹底杜絕規則幻覺。
5. **多供應商 LLM 抽象層與啟動即席選型精靈 (Unified LLM & Startup Configuration Wizard)**：
   - 抽象化底層模型供應商，原生支援雲端 **Google Gemini**（gemini-3.5-flash-lite / gemini-2.5-flash / gemini-1.5-flash / gemini-2.0-flash / gemini-1.5-pro）、區域網路內/本機 **Ollama**（Llama 3、Qwen 2.5、DeepSeek 等）與 **離線確定性規則引擎 (Offline)**。
   - **啟動即席參數設定與模型選型 (Startup Interactive Wizard)**：
     - **CLI 模式**：執行一進去立即引導進行模型選型（[1] Gemini、[2] Ollama、[3] Offline、[4] Auto），動態輸入 Gemini API Key、模型版本、BRVA API Key (`x-agent-key`) 與後端網址，支援自動健康檢查，交談中隨時輸入 `/config` 或 `/model` 切換，輸入 `/status` 檢視連線狀態。
     - **Web 模式 (Streamlit)**：側邊欄頂部具備專屬「⚙️ 參數設定與模型選型」面板，支援即時切換模型、輸入 API Key、連線健康度檢測，並支援一鍵同步寫入 `.env`。
   - 支援透過環境變數 `OLLAMA_BASE_URL` 連線至區網伺服器（例如 `http://192.168.1.100:11434`），具備主動健康檢查與自動優雅降級。

---

## 二、 Tool 工具定義 (Tool Definitions)

本系統依作業二與民航飛行安全規範實作 7 大專業工具，全數定義具體的 Pydantic 輸入/輸出規範與例外處理：

### Tool 1：`fetch_aviation_weather`
- **目的 (Purpose)**：抓取 ICAO 機場之最新 METAR 天氣報文，並以三角函數精確計算指定跑道的正逆風與側風分量，評估起降風險。
- **輸入 (Input)**：
  - `icao: str`（4 碼大寫機場代碼，如 `RJAA`）
  - `runway: Optional[str]`（目標跑道編號，如 `16R`）
- **輸出 (Output)**：
  - `raw_metar`、`wind_dir`、`wind_speed_kts`、`gust_kts`、`crosswind_kts`、`headwind_kts`、`is_safe`、`risk_assessment`
- **Error Handling**：
  - 若 ICAO 代碼長度不符或輸入錯誤，回傳結構化錯誤訊息；若外部天氣 API 連線失敗，自動回退使用本地典型歷史天氣快取，保證 Agent 不崩潰。

### Tool 2：`query_virtual_routes`
- **目的 (Purpose)**：自長榮/立榮航空航網庫檢索可用航班。
- **輸入 (Input)**：
  - `dep_icao: str`（出發地，如 `RCTP`）
  - `arr_icao: str`（目的地，如 `RJAA`）
  - `aircraft_type: Optional[str]`（執飛機型，如 `B78X`）
- **輸出 (Output)**：符合條件之航班清單（含班號、航程預估時間、機型與航線型態）。
- **Error Handling**：若無精確匹配機型，自動放寬篩選條件或回退讀取本地備用航網庫。

### Tool 3：`generate_simbrief_dispatch`
- **目的 (Purpose)**：呼叫 SimBrief 與 BRVA 簽派中心服務，為機師生成正式的飛行計畫（OFP 放行單）並建立 Active Dispatch。
- **輸入 (Input)**：`flight_number`、`dep_icao`、`arr_icao`、`aircraft_type`、`user_context` (可選飛官身份委派)。
- **輸出 (Output)**：航路、巡航高度（如 FL370）、計畫燃油 (Block Fuel)、法定備降場與放行單摘要。
- **Error Handling**：若外部服務連線異常，自動回退使用確定性離線航路簽派庫；若飛官尚未綁定 SimBrief，通知內部已完成 Dispatch 放行並提示機師領取。

### Tool 4：`analyze_flight_telemetry`
- **目的 (Purpose)**：以 Pandas 演算法逐秒檢測飛行黑盒子時序紀錄，杜絕純 LLM 的數值算術幻覺。
- **輸入 (Input)**：`file_path: str`（CSV 遙測檔案路徑）、`aircraft_type: str`。
- **輸出 (Output)**：`is_passed`、`score`（百分制）、`touchdown_g`、違規時間戳記清單、一票否決項目。
- **Error Handling**：檢查檔案路徑與必要欄位，並實作 **2 秒滑動視窗防護**，避免短暫陣風雜訊誤判超速。

### Tool 5：`query_flight_sop_and_regulations` (Aviation RAG Engine)
- **目的 (Purpose)**：長榮虛擬航空 (BRVA) 官方飛行文件檢索增強生成 (RAG) 工具。整合三大核心飛行規範（10 大飛行階段標準操作程序 SOP、Live 聯網飛行機隊規章、實機術科考核評分手冊），採用輕量高效的 In-Memory BM25 + 正則權重增益演算法與嚴格的引文合成機制，杜絕 LLM 規則幻覺。
- **輸入 (Input)**：
  - `query: str`（機師提問，例如「滑行速度限制與引擎啟動順序」或「術科考核幾分及格？嚴重違規扣分標準？」）
  - `top_k: int`（檢索相關規範片段數量，預設 3）
  - `category: Optional[str]`（限定檢索範圍：`sop` / `rules` / `exam` / `all`）
- **輸出 (Output)**：
  - `query: str`、`results_count: int`、`top_chunks: List[Dict]`（含章節標題、關聯性分數、文檔來源標籤）、`direct_answer: str`（經權威引文標記合成的綜合答覆）。
- **Error Handling**：
  - 若提問為空或查無符合之航法規章，回傳結構化引導提示，避免拋出未捕獲例外；若文檔目錄不存在，安全回退並記錄 Warning。

### Tool 6：`query_pilot_profile` (Pilot Profile & Points Engine)
- **目的 (Purpose)**：經由機師授權之短效 Scoped Delegation Token，向 CrewCenter 查詢飛官個人呼號、時數、階級與點數餘額。
- **輸入 (Input)**：
  - `query_type: Optional[str]`（查詢維度：`hours` 時數、`points` 點數、`rank` 階級、`summary` 全覽）
  - `user_context: Optional[UserContext]`（當前會話授權上下文）
- **輸出 (Output)**：
  - `status: str`、`callsign: str`、`rank_name: str`、`points: float`、`flight_time_hours: float`、`summary: str`
- **Error Handling**：
  - 若未傳入有效飛官授權上下文，安全阻斷並回傳引導提示，避免私有飛行數據外洩。

### Tool 7：`query_store_catalog` (Store Catalog & Strict Read-Only Guard)
- **目的 (Purpose)**：查詢 CrewCenter 飛官商城架上商品目錄與兌換點數，**嚴格唯讀（Strictly Read-Only）**，禁止 AI 代表扣款購買。
- **輸入 (Input)**：
  - `category: Optional[str]`（可選分類篩選）
  - `user_context: Optional[UserContext]`（可選當前飛官點數對照）
- **輸出 (Output)**：
  - `status: str`、`items_count: int`、`user_points: Optional[float]`、`can_purchase: bool (固定 False)`、`summary: str`
- **Error Handling**：
  - 嚴格鎖定 `can_purchase = False`，於回應末尾固定輸出安全聲明，要求使用者親至網頁端確認交易，防止對話注入或非預期資產損失。

---

## 三、 Agent 完整執行追蹤 (Execution Trace)

展示典型的多輪 ReAct 推理與人機協同 (HITL) 流程：

```text
[User Input 1]
"我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

[🤖 Agent 決策] 使用者欲由 RCTP 執飛 B78X 至 RJAA。執行兩步驟工具鏈：航線檢索 ➡️ 目的地起降氣象解析...
[🔍 Tool Call 1] -> query_virtual_routes(dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation 1] -> 匹配推薦班次：BR184（B78X，航程預估 2h 40m）
[🔍 Tool Call 2] -> fetch_aviation_weather(icao='RJAA', runway='16R')
[📥 Observation 2] -> RJAA 即時 METAR 取得成功，16R 跑道側風分量 9.6 節

🤖 簽派副駕:
報告機長，為您完成簽派規劃與氣象分析：
1. 【推薦航班】：BR184（RCTP 🛫 ➡️ RJAA 🛬，預估航程 2h 40m，由 B78X 客機執飛）。
2. 【目的地天氣簡報 (RJAA)】：
   • METAR 報文：`RJAA 210800Z 20015G25KT 9999 FEW030 22/16 Q1008 NOSIG`
   • 跑道建議：建議使用 16R 跑道進場。
   • 風向與側風評估：風向 200 度，16R 跑道側風分量約 9.6 節（來自右側），逆風分量約 11.5 節。最大陣風達 25 節。側風在安全操作包絡線 (30 kts) 內，適航。
3. 【防禦性操作提醒】：側風雖然合規，但若存在陣風，進場平飄時請適時下風向盤舵修正偏流，保持機頭對正跑道中心線。

👉 如果沒有其他要修改的是否直接為您簽派 BR184？

----------------------------------------------------------------------

[User Input 2]
"好的，幫我直接簽派！"

[🤖 Agent 決策] 偵測到機師確認簽派授權！自 Memory 提取待簽派班次參數...
[🔍 Tool Call] -> generate_simbrief_dispatch(flight_number='BR184', dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation] -> OFP 產出成功！巡航高度 FL370，Block Fuel 18,240 kg

🤖 簽派副駕:
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

符合評分標準必備之兩大失敗情境與工程應對策略：

### 失敗情境一：外部網路超時或無效 ICAO 輸入 (External API Outage / Malformed Input)
- **失敗狀況**：使用者輸入不存在的機場代碼（如 `/weather ABCD`）或外部氣象服務發生 HTTP 500 / 429 限流。
- **原因分析**：外部公共氣象伺服器離線，若工具未實作防護將導致未捕獲例外（Unhandled Exception）中斷 Agent 控制迴圈。
- **解決對策**：
  1. 在 `weather_tool.py` 實作正則表達式防護，強制校驗 4 碼合法性。
  2. 捕獲 `requests.exceptions.RequestException`，並自動降級載入本地典型的備用歷史氣象快取（Fallback Cache），回傳 `is_safe` 與警告註記，確保 Agent 始終給出結構化安全提示而不崩潰。

### 失敗情境二：飛行遙測時序短暫突波超速誤判 (Sensor Noise / Rolling Window False Positive)
- **失敗狀況**：在 FL100 以下因大氣亂流，空速在單一取樣點（0.2 秒）瞬間微幅超出 250 KIAS（如 251.2 KIAS），隨即被飛行員油門收回至 244 KIAS。若套用傳統單點數值比較，會被誤判違規並扣除 10 分，引發考核不公。
- **原因分析**：大氣物理環境具有不可抗力的亂流噪聲，單點臨界跳動不屬於操作違規。
- **解決對策**：在 `telemetry_tool.py` 內導入 **滑動視窗持續時間檢測門檻（Rolling Window Persistence）**，規定物理超速必須「連續持續 $\ge 2$ 秒（$\ge 2$ 筆取樣）」才被計為有效違規事件，大幅提升客觀性與容錯率。

### 失敗情境三：飛行員未綁定 SimBrief 帳號之簽派中斷 (SimBrief Account Not Linked)
- **失敗狀況**：飛行員尚未於 BRVA 個人中心綁定 Navigraph / SimBrief 帳號，直接請求一鍵放行航班。
- **原因分析**：後端簽派 API 需依賴個別機師授權之 SimBrief OAuth Token 方能建立個人化航圖與 OFP，若無 Token 會收到 HTTP 400（`SimBrief account not linked`）。
- **解決對策**：在 `simbrief_tool.py` 與 `agent.py` 內建置帳號狀態防禦檢查。當偵測到未綁定時，Agent 不拋出例外亦不盲目輸出無效連結，而是精確告知內部 Dispatch 已為其保留，並指示機師前往 BRVA 簽派中心完成授權登錄。

### 失敗情境四：未授權訪客存取飛官機敏檔案或非法觸發購買 (Unauthenticated / Mutation Guard)
- **失敗狀況**：訪客或未帶授權 Token 之會話請求查詢個人時數、點數餘額，或試圖要求 AI「幫我買商城商品」。
- **原因分析**：多輪對話中可能存在提示詞注入（Prompt Injection）或未認證惡意調用，造成飛官隱私洩漏或非預期資產消耗。
- **解決對策**：
  1. 實作 `UserContext` 鑑別閘門，未通過 Scoped Delegation Token 驗證者嚴格拒絕存取個人數據。
  2. 商城工具 `query_store_catalog` 鎖定 `can_purchase = False` 嚴格唯讀機制，杜絕任何代購變更行為。

---

## 五、 自動化測試證據 (Verification Evidence)

本專案具備完整的自動化單元測試，涵蓋三角函數計算、航線匹配、OFP 產生、黑盒子超速/硬著陸、RAG 知識庫檢索與權威引文合成、多供應商 LLM 抽象層 (Ollama/Gemini/Offline)、後端 API Key 與 Master Killswitch 管控、飛官身分委派授權驗證，以及 Podman 容器化標準建置檢測：

```bash
python -m unittest discover tests
```

**測試執行結果**：
```text
..............................................
----------------------------------------------------------------------
Ran 46 tests in 1.060s

OK
```
**46 項單元測試 100% 全數通過**：
- 工具運算與防護：18 項測試（風向三角函數、黑盒子過載/超速滑動視窗、離線/已認證簽派）
- Aviation RAG 知識庫：9 項測試（BM25 檢索、引文標籤生成、章節過濾）
- LLM 多供應商抽象層：8 項測試（Ollama、Gemini、Offline 確定性回退）
- 後端 API 安全管控與飛官授權委派：11 項測試（API Key 鑑別、503 Killswitch、429 Rate Limit、Token 驗證、個人檔案查詢、商城唯讀防護）

---

## 六、 專案目錄結構 (Project Structure)

```text
BRVA_Agent/
├── Containerfile              # Podman 容器建置規範檔
├── podman-compose.yml         # 容器化編排設定
├── requirements.txt           # Python 必要依賴清單
├── README.md                  # 專案說明與作業評分規格文件
├── .env.example               # 環境變數範本檔
├── data/                      # 測試遙測數據與民航規章知識庫
│   ├── sample_flight_pass.csv # 考試合格遙測樣本 (100分)
│   ├── sample_flight_fail.csv # 考試違規遙測樣本 (超速/硬著陸)
│   ├── local_fallback_routes.csv # 離線備用長榮航網庫
│   └── knowledge/             # SOP、Live 規章與術科檢定手冊
├── documents/                 # 作業技術規格與架構規劃書
│   └── BRVA_Agent_Assignment2_Report.md # 作業二正式技術報告文件
├── scripts/
│   ├── demo_test_suite.py     # 一鍵全自動 8 大實戰流程展示腳本
│   └── test_comprehensive_scenarios.py # 完整綜合實戰測試套件
├── src/
│   ├── agent.py               # ReAct 決策循環與 Human-in-the-Loop
│   ├── client.py              # 後端 API 通訊客戶端 (支援 x-agent-key 與 Bearer Token)
│   ├── config.py              # 全域參數與環境變數載入
│   ├── context.py             # 飛官身分與授權上下文 (UserContext)
│   ├── memory.py              # 多輪對話與待簽派狀態記憶體
│   ├── llm/                   # 抽象層 (Ollama / Gemini / Offline)
│   ├── tools/                 # 7 大確定性航空專業工具
│   │   ├── weather_tool.py    # 起降氣象與側風運算
│   │   ├── route_tool.py      # 長榮虛擬航網查詢
│   │   ├── simbrief_tool.py   # OFP 飛行放行單生成
│   │   ├── telemetry_tool.py  # 黑盒子 Pandas 向量化檢驗
│   │   ├── rag_tool.py        # 民航法規 RAG 檢索增強
│   │   ├── user_profile_tool.py # 飛官個人檔案與時數點數
│   │   └── store_catalog_tool.py # 飛官商城唯讀目錄
│   └── ui/                    # CLI 與 Streamlit Web 雙模式介面
└── tests/                     # 46 項自動化單元測試套件
│   └── ui/                    # CLI 與 Streamlit Web 雙模式介面
└── tests/                     # 41 項自動化測試套件
```

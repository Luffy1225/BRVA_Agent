# 期末作業報告：AI Agent 系統設計與實作

- **課程名稱**：AI Agent 系統設計與實作（114 學年度第 1 學期）
- **專案名稱**：BRVA Agent — 長榮虛擬航空智慧飛行簽派與考核系統
- **學生姓名**：曾柏碩
- **學號**：411285052
- **系級班別**：資訊工程學系四年級
- **GitHub 倉儲**：https://github.com/bryanleetc/BRVA_Agent
- **繳交日期**：2026 年 11 月 22 日

---

## 0. 簡單說明

這個專案是為長榮虛擬航空（EVA Air Virtual，BRVA）打造的 AI 簽派與考核 Agent。長榮虛擬航空是一個模擬真實民航作業的飛行社群，成員需要透過網站 CrewCenter 完成航班簽派、查詢規章、上傳飛行紀錄等作業。

BRVA Agent 的角色是一個會話式副駕駛助手，接受機師的自然語言指令，然後根據內容呼叫對應的工具完成任務：查天氣、找航班、送出簽派單、審查飛行遙測數據、查規章手冊，或是查詢 CrewCenter 上的個人積分與商城資訊。

**架構核心：**
- 推理框架：ReAct（Reasoning + Acting）迴圈
- 人機協同：兩輪 HITL 確認機制（特別針對簽派放行這種需要飛行員明確授權的操作）
- 工具數量：22 項，全部以 Pydantic 定義強型別 Schema
- 測試覆蓋：108 項單元測試全數通過
- 部署：Podman 容器化，支援 Streamlit 網頁 UI、CLI 終端機、REST API 三種介面

LLM 支援 Gemini API、Ollama（本地）與確定性離線規則引擎，透過抽象層在執行時切換。常見操作（天氣、簽派、個人資料查詢）走確定性關鍵字路由，不依賴 LLM 解析；複雜、混合的查詢才由 LLM 決定工具與參數。

---

## 1. Agent 原始碼

原始碼請參見 GitHub 倉儲：**https://github.com/bryanleetc/BRVA_Agent**

核心模組：

| 檔案 | 說明 |
|------|------|
| `src/agent.py` | 主 Agent 類別，ReAct 迴圈與 HITL 邏輯 |
| `src/memory.py` | 狀態記憶體（對話歷史、待簽派暫存） |
| `src/client.py` | BackendClient，HTTP 層防護與降級處理 |
| `src/context.py` | UserContext，飛官身分上下文 |
| `src/llm/` | LLM Provider 抽象層（Gemini / Ollama / Offline） |
| `src/tools/` | 22 項工具模組 |
| `Containerfile` | Podman 容器建置檔 |
| `tests/` | 108 項單元測試 |

---

## 2. Tool 定義

共 22 項工具，全部以 Pydantic 定義輸入/輸出 Schema，並內建邊界防禦與降級機制。

### 2.1 工具清單

| # | 工具名稱 | 功能 |
|---|---------|------|
| 1 | `fetch_aviation_weather` | METAR 氣象查詢 + 跑道側風計算 |
| 2 | `query_virtual_routes` | 長榮/立榮航網班次查詢 |
| 3 | `generate_simbrief_dispatch` | OFP 飛行計畫生成與簽派登錄 |
| 4 | `analyze_flight_telemetry` | 黑盒子遙測 Pandas 審查 |
| 5 | `query_flight_sop_and_regulations` | SOP 規章 BM25 RAG 查詢 |
| 6 | `query_pilot_profile` | 飛官個人積分/時數/階級查詢 |
| 7 | `query_store_catalog` | 商城目錄唯讀查詢 |
| 8 | `search_pilot_user` | 飛官帳號/呼號搜尋 |
| 9 | `query_leaderboard` | 排行榜查詢 |
| 10 | `query_calendar_events` | 官方活動行事曆 |
| 11 | `query_events_and_rotw` | 每週精選航線（ROTW）推薦 |
| 12 | `query_pilot_inventory` | 個人背包道具庫（唯讀） |
| 13 | `query_media_gallery` | 影音藝廊查詢 |
| 14 | `query_live_radar_and_tracker` | 即時航跡雷達 |
| 15 | `query_pilot_pireps` | 個人飛行記錄（PIREP）查詢 |
| 16 | `query_active_dispatch` | 目前執行中簽派查詢 |
| 17 | `query_atc_status` | ATC 管制等級與晉升差距計算 |
| 18 | `query_atc_mentoring_eligibility` | ATC 培訓 5 大條件資格審查 |
| 19 | `query_live_overview` | 即時機隊總覽與稼動率 |
| 20 | `query_codeshare_partners` | 星空聯盟聯營夥伴資訊 |
| 21 | `recommend_routes_and_codeshares` | 聯營航線推薦 |
| 22 | `query_flight_route_by_number` | 指定航班號精準航線查詢 |

---

### 2.2 `fetch_aviation_weather` — 氣象查詢與側風計算

**目的**：取得 ICAO 機場最新 METAR 報文，以三角函數計算指定跑道的側風與逆風分量。

**輸入 Schema**：
```python
class WeatherInput(BaseModel):
    icao: str             # 4 碼 ICAO 機場代碼，如 "RCTP"
    runway: Optional[str] # 預計跑道，如 "05L"、"16R"，預設 "16R"
```

**輸出 Schema**：
```python
class WeatherOutput(BaseModel):
    raw_metar: str
    wind_dir: int
    wind_speed_kts: int
    gust_kts: Optional[int]
    crosswind_kts: float
    headwind_kts: float
    flight_category: str   # VFR / IFR / LIFR
    is_safe: bool
    risk_notes: str
```

**關鍵設計**：

1. 入口格式校驗（4 碼大寫），無效 ICAO 直接拒絕，不走網路
2. 優先呼叫後端 API，失敗時降級讀本地 METAR 快取（5 個主要機場預設值），工具永不回傳例外
3. 側風計算為確定性 Python 運算，不經過 LLM：
   - `crosswind = wind_speed × sin(|wind_dir − runway_heading|)`
   - `headwind  = wind_speed × cos(|wind_dir − runway_heading|)`
4. 側風超過 30 kts 時 `is_safe = False`，自動加入警告提示

---

### 2.3 `analyze_flight_telemetry` — 黑盒子遙測審查

**目的**：用 Pandas 向量化運算審查黑盒子 CSV 遙測數據，逐秒檢測三類違規，完全排除 LLM 數值幻覺。

**輸入 Schema**：
```python
class TelemetryInput(BaseModel):
    file_path: Optional[str]   # CSV 路徑
    aircraft_type: str         # 機型，預設 "B78X"
```

**輸出 Schema**：
```python
class TelemetryOutput(BaseModel):
    success: bool
    is_passed: bool
    score: int                      # 100 分制
    touchdown_g: float
    violations: List[Dict[str, Any]] # 含時間戳、違規項目、扣分
    critical_failures: List[str]     # 一票否決項
    summary: str
```

**三大審查項目**：

| 審查項目 | 標準 | 扣分 |
|---------|------|------|
| 地面滑行超速 | 直線滑行 ≤ 26 kts | -5 分 |
| FL100 以下空速 | IAS < 250 KIAS | -10 分 |
| 接地 G 力 | 垂直過載 ≤ 1.6G | 一票否決 |

**防誤判滾動視窗**：超速必須「連續 ≥ 2 筆取樣」才判定為有效違規，單點陣風雜訊不計入。

---

### 2.4 `query_flight_sop_and_regulations` — 規章 RAG 查詢

**目的**：對長榮虛擬航空官方規章知識庫（SOP、考核手冊、LIVE 規範）做 BM25 全文檢索。

**輸入 Schema**：
```python
class SOPInput(BaseModel):
    query: str                  # 機師提問
    top_k: int                  # 檢索段落數，預設 3
    category: Optional[str]     # "sop" / "rules" / "exam" / "all"
```

**輸出 Schema**：
```python
class SOPOutput(BaseModel):
    query: str
    results_count: int
    top_chunks: List[Dict]
    direct_answer: str    # 附【來源：...】標籤的綜合回覆
```

**關鍵設計**：採用 In-Memory BM25（`rank_bm25`），啟動時一次性載入規章文本分詞，查詢完全離線可用。每次回覆強制附 `【來源：長榮虛擬航空飛行標準作業程序第 X 章】` 格式引用標籤，消除法規幻覺，讓飛行員能追溯出處。

---

### 2.5 `generate_simbrief_dispatch` — OFP 簽派放行

**目的**：結合飛官授權委託與 SimBrief 服務，生成正式 OFP 飛行計畫並登錄簽派中心。

**輸入 Schema**：
```python
class DispatchInput(BaseModel):
    flight_number: str
    dep_icao: str
    arr_icao: str
    aircraft_type: str
    user_context: Optional[UserContext]  # 飛官身分上下文
```

**輸出 Schema**：
```python
class DispatchOutput(BaseModel):
    status: str         # SUCCESS / SIMBRIEF_NOT_LINKED / UNAUTHENTICATED / ...
    route: str
    cruise_altitude: str
    block_fuel_kgs: int
    est_flight_time: str
    alternate_airport: str
    summary: str
```

**降級策略**：
- 飛官未綁定 SimBrief → 通知已完成 CrewCenter 內部 Dispatch 保留，並給出綁定指引
- 未認證訪客 → 回傳引導登入提示，不執行任何簽派
- 後端離線 → 啟用確定性本地計算（依機型與航距推算標準巡航高度、油量、備降場）

---

### 2.6 `query_store_catalog` — 商城唯讀防護

**目的**：查詢 CrewCenter 商城架上商品清單與點數餘額，嚴格唯讀，禁止 AI 代購。

**關鍵設計**：`can_purchase` 欄位在工具程式碼內永遠鎖定為 `False`，無論使用者怎麼要求 Agent 代購，都不可能觸發購買行為。回覆末尾固定附免責聲明，要求使用者親至 CrewCenter 網頁端操作。

---

## 3. Agent 執行追蹤

以下是一次完整的「兩輪 HITL 人機協同簽派」執行紀錄，展示 Thought → Tool Call → Observation 的完整流程。

### 情境說明

機師希望由桃園（RCTP）開 B78X 飛往成田（RJAA），請 Agent 推薦班次並查天氣，確認後執行簽派。

---

### 第一輪：推薦航班 + 氣象分析

```
[User Input 1]
"我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，
 請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時的風向風險。"

[🤖 Agent 決策]
使用者欲由 RCTP 執飛 B78X 至 RJAA。
規劃兩步驟工具鏈：航網匹配 → 目的地起降氣象解析

[🔍 Tool Call 1]
-> query_virtual_routes(dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')

[📥 Observation 1]
-> 匹配推薦班次：BR184（B78X，航程預估 2h 40m，定期國際線）

[🔍 Tool Call 2]
-> fetch_aviation_weather(icao='RJAA', runway='16R')

[📥 Observation 2]
-> RJAA 即時 METAR 取得成功，
   16R 跑道側風分量 9.6 kts（右側），逆風 11.5 kts，陣風 25 kts

🤖 Agent 回應：
報告機長，為您完成簽派規劃與氣象分析：

1. 【推薦航班】BR184（RCTP → RJAA，預估航程 2h 40m，B78X 執飛）

2. 【目的地天氣簡報 (RJAA)】
   METAR：RJAA 210800Z 20015G25KT 9999 FEW030 22/16 Q1008 NOSIG
   跑道建議：建議使用 16R 跑道進場
   側風評估：風向 200 度，側風分量約 9.6 kts（來自右側），
            逆風分量約 11.5 kts，最大陣風 25 kts，安全適航

3. 【提醒】側風雖合規，但有陣風時進場平飄請適時下風向盤舵修正偏流

👉 如果沒有其他要修改的是否直接為您簽派 BR184？
```

> 此時 Agent 在 `AgentMemory` 中存入 `PendingDispatch(flight_number='BR184', dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')`，結束第一輪，等待使用者授權。

---

### 第二輪：授權確認 + OFP 生成

```
[User Input 2]
"好的，幫我直接簽派！"

--- HITL 判斷流程 ---
  pending_dispatch = memory.get_pending()   → BR184 暫存存在
  is_question      = False                  → 無問句符號
  is_explicit_dispatch = True               → 包含「直接簽派」關鍵字
  → 進入 HITL 路徑

[🤖 Agent 決策]
偵測到機師確認簽派授權！
自 Agent Memory 提取待簽派班次：BR184 (RCTP → RJAA, B78X)

[🔍 Tool Call]
-> generate_simbrief_dispatch(
     flight_number='BR184',
     dep_icao='RCTP',
     arr_icao='RJAA',
     aircraft_type='B78X'
   )

[📥 Observation]
-> OFP 產出成功！巡航高度 FL370，Block Fuel 18,240 kg

  memory.clear_pending()   ← 清除暫存，防止重複放行

🤖 Agent 回應：
✅ 【BRVA 簽派中心放行成功】

📋 航班簽派放行概要：
   航班：BR184  RCTP → RJAA
   機型：B78X
   航路：RCTP/05L CHALI1A TONIK V22 MORUS Y59 SEDAC KANSU ARASI Y39 HACHI HACHI1A RJAA/16R
   巡航高度：FL370  成本指數 CI-035
   計畫燃油：18,240 kg
   預估航程：02:40
   備降場：RJTT（Tokyo Haneda）

📡 Active Dispatch：✅ 已核准放行，系統已同步登錄 BRVA 簽派中心

Happy Landings！
```

---

### Trace 格式說明

每個步驟以 dict 格式記錄，包含 `type`（thought / tool_call / observation）、`title`、`content` 與工具原始回傳 `result`。整個 trace 在 `run()` 結束後可透過 `agent.get_last_trace()` 取得完整列表。Streamlit UI 以可折疊卡片顯示這些步驟，讓使用者可以查看 Agent 推理過程。

---

## 4. 失敗情境（Failure Cases）

### 4.1 外部氣象 API 連線失敗 / ICAO 碼格式錯誤

**觸發方式**：輸入不存在的機場代碼（如 `ABCD`），或外部 Aviation Weather Center API 超時、HTTP 500。

**問題所在**：若不加防護，網路層例外會直接擊穿 Agent 迴圈造成崩潰；無效 ICAO 也會浪費一次 API 請求。

**系統行為**：
- 格式校驗在工具入口攔截，非 4 碼大寫英文字母直接回傳錯誤，不走網路
- 後端連線失敗時自動降級讀本地 METAR 快取（涵蓋 RCTP、RJAA、VHHH 等主要機場），工具正常回傳，Agent 迴圈不中斷
- 使用者收到正常的天氣回覆，底層錯誤被透明處理

---

### 4.2 黑盒子遙測短暫突波誤判（滾動視窗防護）

**觸發方式**：飛機在 FL100 以下因大氣亂流，空速在單一取樣點（約 0.2 秒）瞬間跳到 251.2 KIAS，隨即回落至 244 KIAS。

**問題所在**：單點比較（`if ias >= 250`）會把這個瞬間抖動誤判為超速違規扣分，對飛行員不公平。

**系統行為**：超速必須「連續持續 ≥ 2 筆取樣」才記為違規，單點陣風雜訊直接略過。同樣邏輯也套用在滑行超速審查。結果是：這筆遙測的空速欄位在 251.2 KIAS 只出現一筆，不符合滾動視窗門檻，不計違規，得分不受影響。

---

### 4.3 飛行員尚未綁定 SimBrief 帳號

**觸發方式**：飛行員確認簽派，但尚未在 CrewCenter 個人中心綁定 Navigraph / SimBrief 帳號。後端回傳 `HTTP 400: SimBrief account not linked`。

**問題所在**：若直接把後端錯誤代碼拋給使用者，體驗差，且未捕獲的例外會中斷 Agent 迴圈。

**系統行為**：工具偵測到 `SIMBRIEF_NOT_LINKED` 狀態後，改為回傳「CrewCenter 內部已完成 Dispatch 保留，請前往個人設定完成 Navigraph 綁定」的友善提示，Agent 拿到這個回覆直接回覆使用者，整個流程正常結束不崩潰。飛行員仍然有一筆 Dispatch 保留在系統裡，綁定完成後可繼續。

---

### 4.4 未認證訪客嘗試查詢個人資料或代購商城道具

**觸發方式**：未登入的訪客問「查我的點數」或「幫我買一張加倍卡」。

**問題所在**：個人積分是私有數據，未認證就提供等同資料外洩；若 AI 真的去操作購買，可能造成非預期點數扣除（提示詞注入攻擊面）。

**系統行為**：
- `query_pilot_profile` 在 `user_context` 未認證時直接回傳拒絕，附引導登入說明，不回傳任何積分數字
- `query_store_catalog` 無論如何都鎖定 `can_purchase = False`，回覆末尾固定附免責聲明。使用者說「幫我買」，Agent 會列出商品清單，但明確說明 AI 沒有代購權限，請前往 CrewCenter 操作

---

### 4.5 CrewCenter 後端離線或授權碼過期

**觸發方式**：CrewCenter 生產伺服器維護停機、本機網路中斷，或飛行員的 delegation token 被撤銷，導致整批個人化工具回傳 `ConnectionError` 或 `HTTP 401/403`。

**問題所在**：分散式系統無法保證 100% 在線，若未捕獲 `ConnectionError` 會直接在工具內部崩潰，Agent 主迴圈也跟著中斷。

**系統行為**：
1. `BackendClient` 統一攔截所有 HTTP 層例外，轉譯成結構化錯誤 dict（`status: CREWCENTER_OFFLINE`），工具永不拋出未捕獲例外
2. Agent 偵測到 `CREWCENTER_OFFLINE` 後，呼叫 `_format_crewcenter_offline_response()`：LLM 在線時動態生成航空情境語氣的離線通報，LLM 也離線時則從 5 組預設民航語句備援池隨機取一則
3. 航網班次查詢降級讀本地 CSV；氣象與 SOP RAG 本身就不依賴 CrewCenter，不受影響
4. Streamlit 側邊欄以紅色狀態膠囊即時顯示 API 連線狀態，讓評審能第一時間掌握網路狀態

---

## 附錄：自動化測試與 Podman 執行

### 單元測試

```bash
cd BRVA_Agent
python -m unittest discover tests -p "test_*.py"
# Ran 108 tests in 2.828s
# OK
```

108 項測試全數通過，涵蓋：工具運算與防護（52 項）、Aviation RAG（9 項）、LLM 抽象層（8 項）、後端 API 安全（12 項）、CLI 配置（8 項）、Agent 決策追蹤（10 項）、Podman 容器標準（9 項）。

### Podman 啟動

```bash
# 建置映像
podman build -t aeroagent:v1 .

# 啟動 Streamlit 網頁介面（推薦）
podman run -d --rm -p 8501:8501 --env-file secret.txt --name aeroagent-app aeroagent:v1

# 瀏覽器開啟 → http://localhost:8501
```

Containerfile 使用非 root 使用者（`USER aero`，UID 1000），符合 OCI 最小特權原則與課程 Podman 規範。

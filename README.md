# BRVA Agent：長榮虛擬航空智慧簽派與 CrewCenter 營運副駕系統

> **課程指定作業二：可執行之 Agent + Tool / ReAct 系統**  
> 學生：411285052 資工四 曾柏碩  

---

## ⚡ 快速執行指南 (Quick Start)

### 方式一：Podman 容器執行 (期末評審指定標準 · 推薦 🐳)

本專案完全符合期末專案指定之 **Podman Engine 容器化規範**，提供原生 `Containerfile`、`Dockerfile` 與 `podman-compose.yml`，符合無特權 Non-root 使用者與 OCI 標準，支援跨平台（Linux、macOS、Windows）100% 離線確定性重現：

#### 1. 一鍵建置 Podman 映像檔
```bash
# 於專案根目錄執行 (自動讀取 Containerfile)
podman build -t aeroagent:v1 .
```

#### 2. 依評測情境啟動容器

- **情境 A：啟動 Streamlit 視覺化網頁儀表板 (推薦瀏覽器體驗)**
  ```bash
  podman run -d --rm -p 8501:8501 --name aeroagent-app aeroagent:v1
  # 開啟瀏覽器操作：http://localhost:8501
  ```

- **情境 B：啟動終端機互動式交談 (CLI Interactive Mode)**
  ```bash
  podman run -it --rm aeroagent:v1 python -m src.ui.cli
  ```

- **情境 C：全自動容器內單元測試與 14 大實戰情境評測 (Automated Benchmark)**
  ```bash
  # 執行 105 項全自動單元測試 (100% PASS)
  podman run --rm aeroagent:v1 python -m unittest discover tests -p "test_*.py"

  # 執行 14 大端到端真實航空業務展示腳本 (100% PASS)
  podman run --rm aeroagent:v1 python scripts/demo_test_suite.py
  ```

- **情境 D：Podman Compose 一鍵編排**
  ```bash
  podman compose up --build
  ```

*(本專案亦於 `scripts/` 提供跨平台一鍵輔助腳本：Linux/macOS 請執行 `./scripts/run_podman.sh`；Windows 請執行 `.\scripts\run_podman.ps1`)*

---

### 方式二：本機直接執行 (Local Python 3.10+)
若本機已有 Python 環境，可直接啟動 Streamlit 視覺化儀表板：

```bash
# 1. 安裝必要依賴
pip install -r requirements.txt

# 2. 啟動 Streamlit 視覺化網頁儀表板
python -m streamlit run src/ui/web.py

# 3. 於瀏覽器開啟 http://localhost:8501
```
*(若偏好終端機純文字交談，亦可執行 `python -m src.ui.cli`)*

---

## 一、 專案概述 (Project Overview)

**BRVA Agent** 是專為長榮虛擬航空 (EVA Air Virtual, BRVA) 設計的智慧簽派與飛行營運 AI 助理。

本專案的核心特色是**與作者獨立全端開發的長榮虛擬航空官方營運平台「CrewCenter」(`https://crewcenter.eva-virtual.com`) 進行深度系統級整合**。透過串接 CrewCenter 後端 RESTful API 與飛官身分授權機制（Scoped Delegation Token），讓 AI 不僅具備傳統對話能力，更能作為一名真正具備長榮航務知識與系統權限的「AI 簽派副駕」。

### 核心功能與整合重點：
1. **與自研 CrewCenter 後端深度連動**：
   - 整合正式站 API (`https://api.eva-virtual.com`)，支援飛官短效委託授權碼 (Delegation Token) 身分認證。
   - 飛官可直接於交談中查詢個人時數、點數、官階、歷史飛行報告 (PIREP) 與生效中簽派單 (Active Dispatch)。
2. **多輪人機協同 (Human-in-the-Loop, HITL) 智慧簽派**：
   - 檢索官方虛擬航網推薦合適班次，即時抓取起降機場 METAR 天氣，並以精確三角幾何向量分解跑道側風與逆風分量。
   - 在向機師確認授權後，自動串接 SimBrief 產生正式營運飛航計畫 (OFP)，並自動同步回寫至 CrewCenter 簽派資料庫。
3. **CrewCenter 即時社群與營運生態工具鏈**：
   - 整合 EVA Tracker 在空雷達追蹤、全員榮譽排行榜 (Leaderboard)、官方活動行事曆與每週精選雙倍航線 (ROTW)、社群影音藝廊作品展示，以及飛官商城目錄（具備嚴格唯讀安全防護）。
4. **官方飛行手冊與規章 RAG 知識庫 (Aviation RAG Engine)**：
   - 完整索引長榮虛擬航空 10 大階段標準操作程序 (SOP)、Live 聯網飛行規章與術科檢定手冊，採用 In-Memory BM25 檢索，並強制於回答中標註權威出處引文（如【來源：SOP 手冊 · SECTION 3】），消除規則幻覺。
5. **多模型抽象層與彈性設定精靈 (Unified LLM Architecture)**：
   - 原生支援 Google Gemini (gemini-3.5-flash-lite / gemini-2.5-flash 等)、本地/區網 Ollama (Llama 3、Qwen 2.5) 以及內建的離線確定性規則引擎。
   - 支援無外網環境下的平滑 Fallback 離線運行，評審在離線狀態下亦可 100% 正常檢測所有工具與 ReAct 邏輯。

---

## 二、 22 大專業航空與 CrewCenter 工具定義 (Tool Definitions)

系統實作了 22 大專業確定性工具，涵蓋「飛行簽派與航電運算」、「官方規章 RAG 與黑盒子遙測」、「CrewCenter 飛官社群與營運」、「ATC 航管與帶飛培訓」及「星空聯盟機隊與聯營航網」五大領域。全數以強型別定義輸入/輸出 Schema，具備嚴格邊界防禦與離線降級機制：

### 🛫 類別一：飛行簽派與航電氣象工具 (Flight Operations & Dispatch)

#### 1. `fetch_aviation_weather`
- **目的**：查詢指定機場即時航空氣象 (METAR)，動態計算指定跑道之正逆風與側風分量，評估民航適航限制 (側風 ≤ 30 節)。
- **輸入**：`icao: str` (4 碼機場代號，如 "RCTP")、`runway: Optional[str]` (跑道編號，如 "05L")。
- **輸出**：`raw_metar`、`wind_dir`、`wind_speed_kts`、`crosswind_kts`、`headwind_kts`、`is_safe`、`risk_assessment`。
- **錯誤處理**：以正則表達式 `^[A-Z]{4}$` 阻斷非法代碼；連線逾時自動降級載入本地歷史典型氣象快取。
- **💬 快速測試範例**：`"幫我查一下 RCTP 05L 即時天氣與側風"`

#### 2. `query_virtual_routes`
- **目的**：檢索長榮/立榮航空內部真實虛擬航網，媒合推薦執飛班次、機型與預估航程時長。
- **輸入**：`dep_icao: str`、`arr_icao: str`、`aircraft_type: Optional[str]`。
- **輸出**：符合條件之航班陣列（班號、起降場、預估時長、機型、是否為貨機）。
- **錯誤處理**：若指定機型查無班次自動放寬限制；若後端離線自動回退讀取本地備用航網資料庫。
- **💬 快速測試範例**：`"我想從桃園 RCTP 飛往成田 RJAA，開 B78X，有什麼推薦航班？"`

#### 3. `query_flight_route_by_number`
- **目的**：依指定航班編號（如 `BR3`、`BR184`、`BR12`、`BR315`）精準查詢長榮航網起訖機場（ICAO）、指派機型、飛行時間與航線性質，防範虛擬簽派誤配。
- **輸入**：`flight_number: str`（如 "BR3"、"BR184"）。
- **輸出**：`status`、`flight_number`、`dep`、`arr`、`aircraft`、`flight_time`、`is_cargo`、`route_type`、`summary`。
- **錯誤處理**：查無航班時絕不盲目猜測或預設航線，主動提示機師核對班號或提供起訖機場代碼。
- **💬 快速測試範例**：`"查詢 BR3 航班航線與指派機型"` 或 `"BR3 是飛哪裡？"`

#### 4. `generate_simbrief_dispatch`
- **目的**：結合飛官授權向 SimBrief 生成正式 OFP 放行單，並將簽派紀錄寫入 CrewCenter 後端資料庫。
- **輸入**：`flight_number: str`、`dep_icao: str`、`arr_icao: str`、`aircraft_type: str`、`user_context: Optional[UserContext]`。
- **輸出**：`status`、`route`、`cruise_altitude`、`block_fuel_kgs`、`summary`。
- **錯誤處理**：未授權訪客回傳登入提示；若飛官尚未綁定 SimBrief，回傳保留提示與綁定引導；伺服器斷線自動啟用確定性離線放行引擎。
- **💬 快速測試範例**：`"幫我簽派 BR184 飛往成田"`、`"幫我簽派 BR3"` 或人機協同授權 `"好的，幫我直接簽派！"`

#### 5. `query_active_dispatch`
- **目的**：查詢飛官當前已生成且生效中的簽派放行單 (Active Dispatch) 狀態與詳細參數。
- **輸入**：`user_context: Optional[UserContext]` (需驗證身分)。
- **輸出**：`has_active_dispatch`、`dispatch` (航班編號、航段、機型、Block Fuel、備降場)。
- **錯誤處理**：未授權時提示登入；若無有效簽派，給予說明並引導發起新簽派任務。
- **💬 快速測試範例**：`"查詢我目前是否有生效中的簽派放行單 (Active Dispatch)？"`

---

### 📚 類別二：官方規章 RAG 與黑盒子審查工具 (Regulations & Telemetry)

#### 5. `query_flight_sop_and_regulations`
- **目的**：檢索長榮虛擬航空官方 SOP、Live 機隊規章與術科檢定手冊之 RAG 知識庫，標註出處章節。
- **輸入**：`query: str` (自然語言提問)、`top_k: int` (預設 3)、`category: Optional[str]`。
- **輸出**：`direct_answer` (含權威出處引文標籤之綜合摘要)、`top_chunks` (命中段落清單)。
- **錯誤處理**：採用純記憶體 In-Memory BM25 檢索，零外部資料庫依賴；查無資料時友善引導。
- **💬 快速測試範例**：
  - SOP 速限：`"請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？"`
  - 考核失格：`"請問術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？"`
  - 機隊規章：`"請問 LIVE 機隊每位機師最多可以預約幾架飛機？若發生墜機事故需要在多久內通報？"`

#### 6. `analyze_flight_telemetry`
- **目的**：以 Pandas 演算法逐秒檢測飛行黑盒子時序紀錄，杜絕純 LLM 數值比對誤差。
- **輸入**：`file_path: str` (CSV 遙測檔案路徑)、`aircraft_type: str`。
- **輸出**：`is_passed`、`score`、`touchdown_g`、違規時間戳記清單。
- **錯誤處理**：檢查檔案路徑與欄位完整性；實作 2 秒滑動視窗防護排除短暫陣風雜訊。
- **💬 快速測試範例**：
  - 合格審核：`"請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。"`
  - 違規揪錯：`"請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。"`

---

### 👨‍✈️ 類別三：CrewCenter 飛官社群與營運工具 (Pilot Community & Operations)

#### 7. `query_pilot_profile`
- **目的**：透過飛官授權之 Scoped Delegation Token 查詢個人時數、點數、官階與駐紮樞紐。
- **輸入**：`query_type: Optional[str]` ("summary", "points", "hours", "rank")、`user_context: Optional[UserContext]`。
- **輸出**：`callsign`、`rank_name`、`points`、`flight_time_hours`、`current_location`、`summary`。
- **錯誤處理**：未提供有效飛官身分時嚴格阻擋，防止個資洩漏。
- **💬 快速測試範例**：`"幫我查我的點數與個人檔案"` 或 `"查詢我的累計飛行時數與會員等級"`

#### 8. `search_pilot_user`
- **目的**：依長榮呼號 (Callsign 如 EVA001, EVA495BR) 或使用者名稱模糊搜尋特定飛官名冊與飛行履歷。
- **輸入**：`keyword: str` (呼號、使用者名稱或 IF 名稱)、`user_context: Optional[UserContext]`。
- **輸出**：`count`、`users` (呼號、名稱、官階、總時數、架次、ATC 等級)、`summary`。
- **錯誤處理**：關鍵字為空時提示輸入；後端離線時由本地代表性飛官名冊快取回退。
- **💬 快速測試範例**：`"搜尋飛官 EVA001 的資料與飛行檔案"` 或 `"幫我找呼號 EVA495BR 的機長"`

#### 9. `query_store_catalog`
- **目的**：查詢 CrewCenter 飛官商城架上特許證、增益道具與兌換商品（🔒 嚴格唯讀安全邊界）。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：`items` (商品清單)、`current_points`、`can_purchase` (固定 False)、`summary`。
- **錯誤處理**：程序層鎖定 `can_purchase = False`，強制附帶唯讀免責聲明，杜絕 Prompt Injection 惡意代購。
- **💬 快速測試範例**：`"幫我看一下商城目前架上有什麼商品"`

#### 10. `query_leaderboard`
- **目的**：查詢長榮虛擬航空全員榮譽排行榜（飛官時數/點數/接地率，或航管管制作業時數）及個人排名。
- **輸入**：`category: Optional[str]` ("pilot" / "atc")、`sort_by: Optional[str]`、`days: Optional[str]`、`user_context`。
- **輸出**：`top_users` 前 10 名成員數據、`my_rank` 個人名次。
- **錯誤處理**：非法參數自動正規化為安全預設值；後端未回應時由記憶體快取降級展示。
- **💬 快速測試範例**：`"幫我查飛行員時數排行榜與名次"`

#### 11. `query_calendar_events`
- **目的**：檢索官方活動行事曆，掌握近期官方大聯飛、活動時間、主辦人與個人報名狀態。
- **輸入**：`limit: Optional[int]` (預設 5)、`include_rotw: Optional[bool]`、`user_context`。
- **輸出**：`events` 活動陣列 (名稱、起訖時間、主辦方、是否已報名 `is_joined`)。
- **錯誤處理**：防禦性時間解析支援 UTC 與本地時區；後端離線時由活動快訊回退。
- **💬 快速測試範例**：`"查詢近期官方活動與行事曆"`

#### 12. `query_events_and_rotw`
- **目的**：便捷查詢當週生效之每週精選雙倍哩程航線 (ROTW) 與近期大聯飛活動。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：當週 ROTW 精選航線清單與活動概要。
- **錯誤處理**：同 `query_calendar_events`。
- **💬 快速測試範例**：`"查詢近期官方活動、大聯飛與每週精選雙倍航線"`

#### 13. `query_pilot_inventory`
- **目的**：查詢已授權飛官個人背包與道具庫（特許通行證、加倍卡、主題塗裝）。🔒 嚴格唯讀。
- **輸入**：`category: Optional[str]` ("all", "tickets", "props", "themes")、`user_context`。
- **輸出**：通行證數量、道具清單、外觀收藏。
- **錯誤處理**：未登入時安全阻擋；程式保證無任何扣除或消耗道具之 Mutation 端點。
- **💬 快速測試範例**：`"幫我看一下我的道具庫與持有的通行證"`

#### 14. `query_media_gallery`
- **目的**：檢視 CrewCenter 影音藝廊之社群航空攝影作品、精選照片與獲讚數。
- **輸入**：`category: Optional[str]`、`featured_only: Optional[bool]`、`limit: Optional[int]`、`user_context`。
- **輸出**：作品標題、作者呼號、機型、愛心數、檢視連結。
- **錯誤處理**：網路中斷時由精選特刊快取回退。
- **💬 快速測試範例**：`"幫我看看藝廊目前有什麼精選照片"`

#### 15. `query_pilot_pireps`
- **目的**：查詢已授權飛官個人近期飛行報告 (PIREP) 歷史紀錄、落地垂直速度與核准狀態。
- **輸入**：`limit: Optional[int]` (預設 5)、`user_context`。
- **輸出**：飛行報告清單（班號、航段、機型、落地垂直速度、核准狀態）。
- **錯誤處理**：未授權時提示登入；若資料未展開自動發起子查詢補齊。
- **💬 快速測試範例**：`"查看我最近的飛行紀錄與落地接地垂直速度"`

---

### 🎙️ 類別四：ATC 航管服務與帶飛培訓工具 (Air Traffic Control & Mentoring)

#### 16. `query_atc_status`
- **目的**：查詢管制員當前 ATC 等級、執勤時數與管制作業架次，並精準計算距離晉升下一階管制員之剩餘差距 (Gap Analytics) 與達成率。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：`current_rank`、`next_rank`、`duty_hours`、`operations`、`progress_percent`、`duty_hours_remaining`、`operations_remaining`、`summary`。
- **錯誤處理**：若已達最高 Examiner 階級，提示已達最高等級；連線失敗自動採用本地管制梯隊模型計算。
- **💬 快速測試範例**：`"查詢我的 ATC rank 與距離下一個等級還多久"` 或 `"我的航管執勤時數還差多少可以晉升？"`

#### 17. `query_atc_mentoring_eligibility`
- **目的**：嚴格依據 CrewCenter `/atc/mentoring` 機制，評估機師是否具備申請 ATC 帶飛培訓之「5 大必要前置條件」（銀卡以上、執勤滿 1hr、作業達 50 次、個人積分 3,000 點、綁定 IF 帳號）。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：`can_apply`、`current_role` (visitor/trainee/mentor)、`criteria` (5 項檢驗細節)、`summary`。
- **錯誤處理**：條列未達標之具體差距；未綁定 IF 時給予指引。
- **💬 快速測試範例**：`"檢查我是否滿足 /atc/mentoring 的培訓條件？"`

---

### 🌐 類別五：星空聯盟機隊與聯營航網工具 (Alliance Codeshare & Live Overview)

#### 18. `query_live_overview`
- **目的**：查詢 CrewCenter `/live/overview` 模式之全機隊營運總覽，包括在空 (Airborne)、地面 (On-Ground)、檢修 (Maintenance) 數量、全機隊即時稼動率，以及在空巡航航機動態清單。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：`total_fleet`、`airborne_count`、`ground_count`、`maintenance_count`、`utilization_rate`、`in_flight_flights`、`summary`。
- **錯誤處理**：後端未回應時由機隊典型離線快照回退。
- **💬 快速測試範例**：`"查詢 /live/overview Live 模式機隊總覽與營運狀態"` 或 `"現在 live 模式有幾架飛機在空中？"`

#### 19. `query_live_radar_and_tracker`
- **目的**：查詢全球航跡雷達 (EVA Tracker) 與 Infinite Flight 在空長榮班機即時位置、巡航高度、對地空速與管制席位。
- **輸入**：`callsign: Optional[str]`、`icao: Optional[str]`、`user_context: Optional[UserContext]`。
- **輸出**：在空班機座標、高度、速度、航向、航電計畫。
- **錯誤處理**：呼號自動模糊正規化（去除空白與連字號）；查無在空時友善告知。
- **💬 快速測試範例**：`"查詢目前有哪些長榮班機在線上飛行？"` 或 `"雷達追蹤 EVA001 班機目前飛到哪裡？"`

#### 21. `query_codeshare_partners`
- **目的**：查詢長榮虛擬航空星空聯盟 (Star Alliance) 聯營 Codeshare 夥伴航空公司總數與詳細名單（全日空 ANA、新加坡航空 SQ、聯合航空 UA、韓亞航空 OZ、土耳其航空 TK 等）。
- **輸入**：`user_context: Optional[UserContext]`。
- **輸出**：`total_codeshare_partners`、`partners` (代碼、名稱、國家、樞紐)、`summary`。
- **錯誤處理**：連線中斷自動載入星空聯盟官方合作航司標準名冊。
- **💬 快速測試範例**：`"長榮航空現在有幾個 codeshare 夥伴？名單有哪些航空公司？"`

#### 22. `recommend_routes_and_codeshares`
- **目的**：智慧推薦合適執飛之精選航線，支援每週精選雙倍哩程航線 (ROTW · 2.0x 哩程加倍)、星空聯盟夥伴航司（如 `ANA`、`SQ`、`UA`）或航線分類（`rotw` 精選、`codeshare` 聯營、`long` 長程、`short` 短程、`cargo` 貨運、`popular` 熱門）篩選。
- **輸入**：`category: Optional[str]`、`airline: Optional[str]`、`dep_icao: Optional[str]`、`arr_icao: Optional[str]`、`user_context: Optional[UserContext]`。
- **輸出**：`recommended_count`、`routes` (班號、起降場、推薦機型、航程時長、加倍倍率)、`summary`。
- **錯誤處理**：查無特定條件時自動擴展為熱門精選航線推薦。
- **💬 快速測試範例**：`"推薦本週 ROTW 每週精選雙倍哩程航線"` 或 `"請推薦我幾條適合執飛的 ANA 星空聯盟 Codeshare 聯營航線"`

---

### 🛠️ 快速測試案例預設集對照表 (Demo Presets Quick Reference)

為方便評審與飛官快速驗證所有 22 大工具呼叫，Streamlit 視覺化網頁介面已在左側側邊欄整合「🛠️ 快速測試案例 (Demo Presets)」面板，劃分為 4 大標籤頁，每顆按鈕均對應明確的航空情境與 Tool Call：

| 分頁標籤 | 快速按鈕名稱 | 自然語言 Prompt 範例 | 觸發工具調用 (Tool Call) |
| :--- | :--- | :--- | :--- |
| **🛫 簽派氣象** | ✈️ 簽派長途航線 BR3 | `幫我簽派 BR3` | `generate_simbrief_dispatch` (KIAD ➔ RCTP B789) |
| **🛫 簽派氣象** | 🔎 查詢航班起訖與機型 | `查詢 BR3 航班航線與指派機型` | `query_flight_route_by_number` |
| **🛫 簽派氣象** | 🌟 ROTW 每週精選雙倍航線 | `推薦本週 ROTW 每週精選雙倍哩程航線` | `recommend_routes_and_codeshares` (ROTW 2.0x) |
| **🛫 簽派氣象** | 🛫 航線推薦與起降側風分析 | `我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣...` | `query_virtual_routes` + `fetch_aviation_weather` |
| **🛫 簽派氣象** | 📑 直接簽派航班 (BR184) | `幫我簽派 BR184 飛往成田` | `generate_simbrief_dispatch` |
| **🛫 簽派氣象** | 📡 查詢生效中簽派單 | `查詢我目前是否有生效中的簽派放行單 (Active Dispatch)？` | `query_active_dispatch` |
| **🛫 簽派氣象** | 🌦️ 桃園機場即時氣象與側風 | `幫我查一下 RCTP 05L 即時天氣與側風` | `fetch_aviation_weather` |
| **🛫 簽派氣象** | 🗺️ 星空聯盟聯營航線推薦 | `請推薦我幾條適合執飛的 ANA 星空聯盟 Codeshare 聯營航線` | `recommend_routes_and_codeshares` |
| **📖 規章遙測** | 📖 發動機啟動順序與滑行速限 | `請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？` | `query_flight_sop_and_regulations` |
| **📖 規章遙測** | ⚠️ 術科考核重大違規一票否決 | `請問術科實作考核中，哪些重大違規情事會直接觸發一票否決 (Automatic Fail)？` | `query_flight_sop_and_regulations` |
| **📖 規章遙測** | 🛡️ LIVE 機隊認領與事故通報 | `請問 LIVE 機隊每位機師最多可以預約幾架飛機？若發生墜機事故需要在多久內通報？` | `query_flight_sop_and_regulations` |
| **📖 規章遙測** | 📊 遙測黑盒子合格檢測 | `請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。` | `analyze_flight_telemetry` |
| **📖 規章遙測** | 🚨 遙測黑盒子違規檢驗 | `請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。` | `analyze_flight_telemetry` |
| **👨‍✈️ 飛官中心** | 💰 查詢個人時數點數與檔案 | `幫我查我的點數與個人檔案` | `query_pilot_profile` |
| **👨‍✈️ 飛官中心** | 🔍 搜尋指定飛官檔案 (EVA001) | `搜尋飛官 EVA001 的資料與飛行檔案` | `search_pilot_user` |
| **👨‍✈️ 飛官中心** | 🏆 查詢飛官時數與點數排行榜 | `幫我查飛行員時數排行榜與名次` | `query_leaderboard` |
| **👨‍✈️ 飛官中心** | 🎒 查看飛官背包道具庫 (唯讀) | `幫我看一下我的道具庫與持有的通行證` | `query_pilot_inventory` |
| **👨‍✈️ 飛官中心** | 📅 查詢官方活動、聯飛與 ROTW | `查詢近期官方活動、大聯飛與每週精選雙倍航線` | `query_calendar_events` / `query_events_and_rotw` |
| **👨‍✈️ 飛官中心** | 📋 查詢近期歷史飛行報告 | `查看我最近的飛行紀錄與落地接地垂直速度` | `query_pilot_pireps` |
| **👨‍✈️ 飛官中心** | 🖼️ 瀏覽影音藝廊精選照片 | `幫我看看藝廊目前有什麼精選照片` | `query_media_gallery` |
| **👨‍✈️ 飛官中心** | 🏬 查看飛官商城架上商品目錄 | `幫我看一下商城目前架上有什麼商品` | `query_store_catalog` |
| **🎙️ 航管機隊** | 🎧 ATC 等級與晉升差距計算 | `查詢我的 ATC rank 與距離下一個等級還多久` | `query_atc_status` |
| **🎙️ 航管機隊** | 🎓 審查 ATC 培訓 5 大前置條件 | `檢查我是否滿足 /atc/mentoring 的培訓條件？` | `query_atc_mentoring_eligibility` |
| **🎙️ 航管機隊** | 🌐 查看 LIVE 機隊總覽 | `查詢 /live/overview Live 模式機隊總覽與營運狀態` | `query_live_overview` |
| **🎙️ 航管機隊** | 📡 全球航跡雷達在空班機追蹤 | `查詢目前有哪些長榮班機在線上飛行？` | `query_live_radar_and_tracker` |
| **🎙️ 航管機隊** | 🤝 查詢星盟 Codeshare 夥伴 | `長榮航空現在有幾個 codeshare 夥伴？名單有哪些航空公司？` | `query_codeshare_partners` |

---

## 三、 Agent 執行追蹤紀錄 (Execution Trace)

展示系統進行真實「雙輪人機協同簽派」時之完整決策、工具調用與觀察鏈：

```text
================================================================================
【第一輪：航線推薦與起降側風分析】
================================================================================
[User Input 1]
"我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，推薦合適的班次，並告訴我降落時需要注意的風向風險。"

[🤖 Agent 決策] 
使用者欲由 RCTP 執飛 B78X 至 RJAA。規劃兩步驟工具鏈：
步驟 1：檢索長榮航網匹配航班 ➡️ 步驟 2：解析目的地起降氣象與跑道側風。

[🔍 Tool Call 1] -> query_virtual_routes(dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation 1] -> 匹配推薦班次：BR184（執電機型 B78X，航程預估 2h 40m，定期國際線）

[🔍 Tool Call 2] -> fetch_aviation_weather(icao='RJAA', runway='16R')
[📥 Observation 2] -> 取得 RJAA 即時 METAR，16R 跑道側風約 9.6 節（來自右側），逆風 11.5 節，最大陣風 25 節。

[🤖 Agent 決策] 氣象符合安全操作限制 (≤ 30 kts)，將待簽派參數存入 Memory，向機師提議授權。

🤖 Agent 回應:
報告機長，為您完成簽派規劃與氣象分析：
1. 【推薦航班】：BR184（RCTP 🛫 ➡️ RJAA 🛬，預估航程 2h 40m，由 B78X 客機執飛）。
2. 【目的地天氣簡報 (RJAA)】：
   • METAR 報文：`RJAA 210800Z 20015G25KT 9999 FEW030 22/16 Q1008 NOSIG`
   • 跑道建議：建議使用 16R 跑道進場。
   • 風向與側風評估：風向 200 度，16R 跑道側風分量約 9.6 節（來自右側），逆風分量約 11.5 節。最大陣風達 25 節，注意五邊風切變。側風合規，安全適航。
3. 【防禦性操作提醒】：進場平飄時請適時下風向盤舵修正偏流，保持機頭對正跑道中心線。

👉 如果沒有其他要修改的是否直接為您簽派 BR184？

================================================================================
【第二輪：人機協同授權 (HITL) 觸發正式 SimBrief 簽派】
================================================================================
[User Input 2]
"好的，幫我直接簽派！"

[🤖 Agent 決策] 
偵測到機師確認簽派授權！自 AgentMemory 提取待簽派參數 (BR184 / RCTP -> RJAA / B78X)，向簽派中心生成 OFP 放行單。

[🔍 Tool Call] -> generate_simbrief_dispatch(flight_number='BR184', dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
[📥 Observation] -> OFP 產出成功！巡航高度 FL370，計畫燃油 Block Fuel 18,240 kg，寫入 Active Dispatch。

[🤖 Agent 決策] 放行成功，清空暫存防範重複放行，產出最終放行單文件。

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

### 失敗情境一：外部公共氣象服務故障或無效 ICAO 碼 (API Outage & Malformed Input)
- **失敗狀況**：使用者輸入不存在之機場代碼（如 `/weather ABCD`）或外部公共氣象站發生連線逾時、HTTP 500 或 429 限流。
- **原因分析**：外部公共 API 具有不可預期之網路延遲與伺服器故障風險。若工具未捕獲 `RequestException`，將造成未捕獲例外直接中斷 Agent 主迴圈。
- **解決對策**：
  1. 在 `weather_tool.py` 實作正則校驗 (`r'^[A-Z]{4}$'`)，第一時間阻斷非法字串。
  2. 捕獲所有網路層例外，自動降級載入本地預存之歷史氣象快取 (Fallback Cache)，維持系統高可用性。

### 失敗情境二：飛行員未綁定 SimBrief 帳號之簽派中斷 (SimBrief Account Not Linked)
- **失敗狀況**：飛行員尚未於 BRVA 個人中心綁定 Navigraph / SimBrief 帳號，直接請求一鍵放行航班，後端簽派 API 回傳 HTTP 400 (`SimBrief account not linked`)。
- **原因分析**：後端簽派 API 需依賴個別機師授權之 SimBrief OAuth Token 方能生成專屬 OFP，若無 Token 會收到驗證失敗。
- **解決對策**：在 `simbrief_tool.py` 實作狀態防禦檢查。當偵測到未綁定時，Agent 不拋出例外，而是通知機師「CrewCenter 內部已完成 Dispatch 保留」，並精確給出前往簽派中心完成綁定的指引步驟。

### 失敗情境三：未授權訪客存取飛官機敏檔案或非法觸發購買 (Unauthenticated / Mutation Guard)
- **失敗狀況**：未認證之訪客會話請求查詢個人時數、點數餘額，或試圖要求 AI 助理「幫我購買商城特許卡道具」。
- **原因分析**：多輪對話中可能存在提示詞注入 (Prompt Injection) 或越權存取，造成飛官個人飛行隱私外洩或點數非預期扣除。
- **解決對策**：
  1. 實作 `UserContext` 身分閘門，未通過 Scoped Delegation Token 驗證者嚴格拒絕存取個人數據。
  2. 商城工具 `query_store_catalog` 鎖定 `can_purchase = False` 嚴格唯讀機制，杜絕任何代購變更行為。

### 失敗情境四：CrewCenter 飛官未連線、授權碼過期或會話斷線 (CrewCenter Offline / Unlinked / Token Expired)
- **失敗狀況**：使用者處於未連結飛官帳號之訪客模式，或既有授權碼過期 (Expired) / 遭後台管理員撤銷廢止，卻嘗試查詢個人私有飛行檔案、道具庫、歷史 PIREP 或請求直接核准簽派。
- **原因分析**：系統嚴格遵循 Zero-Trust 零信任安全架構與民航隱私防護，未通過 Scoped Delegation Token 驗證前，禁止穿透存取機敏飛官數據。若直接拋出原始 HTTP 401/403 堆疊追蹤，會破壞專業機師使用體驗。
- **解決對策**：
  1. **座艙擬真副駕駛雙軌通知機制 (BUG-320)**：大腦採用座艙情境語氣（Flight Deck Co-pilot Persona）友善告知，並具備 5 組隨機民航語句備援庫（如：*「機長，我們的 ACARS 航電數據鏈連線中斷，目前暫時無法同步 CrewCenter 飛官檔案，請於左側側邊欄重新確認授權碼...」*）。
  2. **非對稱開放與訪客優雅降級 (Graceful Guest Degradation)**：長榮公開航網、起降氣象 METAR、全員排行榜、官方活動行事曆、SOP 與民航法規手冊 RAG 知識庫維持 100% 開放正常使用，僅在涉及私有數據或簽派入庫時精準提供一鍵連結或手動輸入指引。

### 失敗情境五：BRVA API 伺服器無法連線、網路分區或 503 服務維護 (APIServer Unreachable & Network Partition / 503 Outage)
- **失敗狀況**：長榮虛擬航空官方後端伺服器進行維護停機、本機網路中斷、DNS 解析失敗、連線逾時 (Timeout) 或觸發 503 Killswitch 緊急熔斷阻斷。
- **原因分析**：分散式系統與雲端 API 難以保證 100% 隨時在線。若 API Client 缺乏重試、超時控管與錯誤隔離，未捕獲之 `requests.exceptions.ConnectionError` 將直接擊穿 Agent ReAct 決策迴圈導致程式崩潰。
- **解決對策**：
  1. **客戶端通訊邊界防禦 (`BackendClient`)**：實作非同步/同步請求超時保護 (動態 5~25 秒) 與完整例外攔截包裝，捕捉 `ConnectionError`、`Timeout`、HTTP 502/503，自動轉譯為結構化錯誤物件，確保 Agent 主迴圈零中斷。
  2. **確定性本地離線資料庫快取 (Deterministic Offline Fallback Database)**：
     - **航網庫**：自動降級讀取本地 `data/local_fallback_routes.csv`，完整提供真實長榮/立榮航空班次。
     - **簽派引擎**：啟用本地確定性離線放行演算法，自動依機型與距離推算標準巡航高度 (FL370)、計畫油量 (Block Fuel) 與法定備降場。
     - **機隊與夥伴**：自動載入星空聯盟 8 大標準夥伴與典型機隊離線快照。
  3. **側邊欄三合一即時健康度診斷**：以綠黃紅狀態膠囊 (Status Pill) 明確顯示 API Server 可達性與 HTTP 狀態碼，讓機長與評審能第一時間掌握網路狀態。

---

## 五、 自動化測試證據 (Verification Evidence)

本專案建置了完備的自動化測試套件，涵蓋 21 大工具運算、Aviation RAG 知識庫檢索、LLM 抽象層降級、CrewCenter API 安全管控與 Podman 容器規範檢測：

```bash
python -m unittest discover tests -p "test_*.py"
```

**測試執行結果**：
```text
Ran 108 tests in 2.828s

OK
```
**108 項單元測試 100% 全數通過**：
- **工具運算與防護 (52 項)**：風向三角分解、跑道方位修正、航網多維匹配、指定班號精準航線查詢 (`query_flight_route_by_number`)、SimBrief 放行單格式、排行榜、活動行事曆、每週精選雙倍哩程推薦 (ROTW 2.0x)、道具背包、藝廊、航跡雷達、飛官呼號搜尋、ATC 等級差距計算、帶飛培訓 5 大前置條件資格審查、Live 機隊總覽與稼動率、星空聯盟聯營航網推薦。
- **Aviation RAG 知識庫 (9 項)**：In-Memory BM25 檢索演算法、分詞權重增益、正則出處引文標記抽取、章節過濾精準度。
- **LLM 多供應商抽象層 (8 項)**：Ollama 本地/區網連線健康檢查、Google Gemini 連線與降級機制、確定性離線規則引擎。
- **後端 API 安全管控與飛官身分委派 (12 項)**：API Key 鑑別、503 Killswitch 緊急阻斷、429 Rate Limit 限流、Bearer Token 飛官委任驗證、商城唯讀防護。
- **CLI 互動配置與參數精靈 (8 項)**：即席模型切換、連線健康度三層診斷。
- **Agent 決策追蹤 (ReAct Trace) 與漸進式串流推播 (10 項)**：多輪 HITL 人機協同追蹤紀錄結構、on_step 事件回呼驅動、記憶體暫存釋放。
- **Podman 容器化標準與編排 (9 項)**：`Containerfile` 最小特權標準、Non-root 使用者 (`USER aero`)、`Dockerfile` 雙相容規範、`.containerignore` / `.dockerignore` 上下文精簡、`podman-compose.yml` 服務配置、`run_podman.sh` / `run_podman.ps1` 跨平台評測輔助腳本與離線就緒檢測。

---

## 六、 專案目錄結構 (Project Structure)

```text
BRVA_Agent/
├── Containerfile              # Podman 容器建置規範檔 (預設啟動 Streamlit Web)
├── Dockerfile                 # Docker / Podman 雙相容容器建置檔
├── podman-compose.yml         # 容器化編排設定 (Port 8501 映射)
├── .containerignore           # Podman 容器建置過濾設定
├── .dockerignore              # Docker 容器建置過濾設定
├── requirements.txt           # Python 必要依賴清單
├── README.md                  # 專案說明文件
├── .env.example               # 環境變數範本檔
├── data/                      # 備用航網數據與民航規章知識庫
│   ├── local_fallback_routes.csv # 離線備用長榮航網庫
│   ├── sample_flight_pass.csv # 飛行遙測合格樣本
│   ├── sample_flight_fail.csv # 飛行遙測違規樣本
│   └── knowledge/             # SOP、Live 機隊規章與術科檢定手冊
├── documents/                 # 作業技術規格與報告文件
│   └── BRVA_Agent_Assignment2_Report.md # 作業二正式技術報告
├── scripts/
│   ├── run_podman.sh          # Linux / macOS Podman 一鍵建置與評測腳本
│   ├── run_podman.ps1         # Windows PowerShell Podman 一鍵建置與評測腳本
│   ├── demo_test_suite.py     # 14 大航空實戰情境綜合展示腳本
│   └── test_comprehensive_scenarios.py # 綜合實戰測試套件
├── src/
│   ├── agent.py               # ReAct 決策循環與 Human-in-the-Loop 狀態機
│   ├── client.py              # CrewCenter 後端 API 通訊客戶端
│   ├── config.py              # 全域參數與環境變數載入
│   ├── context.py             # 飛官身分與授權上下文 (UserContext)
│   ├── memory.py              # 多輪對話歷史與待簽派狀態暫存
│   ├── llm/                   # 多模型抽象層 (Gemini / Ollama / Offline)
│   ├── tools/                 # 22 大確定性航空專業與 CrewCenter 工具
│   │   ├── weather_tool.py    # 起降 METAR 氣象與跑道側風運算
│   │   ├── route_tool.py      # 長榮虛擬航網多條件檢索
│   │   ├── simbrief_tool.py   # SimBrief 飛航放行單 (OFP) 生成
│   │   ├── rag_tool.py        # 官方規章 In-Memory BM25 檢索
│   │   ├── user_profile_tool.py # 飛官個人檔案與呼號搜尋
│   │   ├── store_catalog_tool.py # 飛官商城唯讀目錄
│   │   ├── crewcenter_leaderboard_tool.py # 全員榮譽排行榜
│   │   ├── crewcenter_calendar_tool.py    # 活動行事曆與 ROTW
│   │   ├── crewcenter_inventory_tool.py   # 飛官背包道具庫
│   │   ├── crewcenter_gallery_tool.py     # 社群影音藝廊作品
│   │   ├── crewcenter_tracker_tool.py     # 全球航跡雷達即時班機追蹤
│   │   ├── crewcenter_pirep_tool.py       # 歷史 PIREP 與生效中簽派
│   │   ├── crewcenter_atc_tool.py         # ATC 等級差距與 Mentoring 審核
│   │   ├── crewcenter_live_tool.py        # Live 機隊總覽與在空稼動率
│   │   ├── crewcenter_codeshare_tool.py   # 星空聯盟夥伴與聯營航線推薦
│   │   └── telemetry_tool.py  # 飛行黑盒子時序數據審查
│   └── ui/
│       ├── web.py             # Streamlit 視覺化網頁儀表板
│       └── cli.py             # 終端機互動式交談介面
└── tests/                     # 93 項全自動單元測試套件
    ├── test_crewcenter_extended_tools.py # 延伸工具與意圖測試
    ├── test_agent_trace.py    # 思考歷程與漸進串流回呼測試
    └── ...
```

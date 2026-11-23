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

### 1. fetch_aviation_weather
• **Tool name**：`fetch_aviation_weather`  
• **工具目的**：查詢指定機場即時航空氣象 (METAR 電報)，動態計算指定跑道之側風與逆風/順風分量，並產出民航適航安全評估與平飄修正提醒。  
• **輸入參數**：  
- `icao` (str, 必填)：四字碼機場代號（如 `"RCTP"`, `"RJAA"`）。  
- `runway` (Optional[str], 選填)：起降跑道編號（如 `"05L"`, `"16R"`），若省略則以機場主跑道計算。  
• **輸出格式**：`Dict[str, Any]`  
- `icao`: 機場代碼  
- `raw_metar`: METAR 原始電報字串  
- `wind_dir` / `wind_speed_kts` / `gust_kts`: 風向、風速與陣風  
- `crosswind_kts` / `crosswind_dir`: 跑道側風分量（kts）與方向（左/右）  
- `headwind_kts` / `headwind_label`: 逆風或順風分量（kts）  
- `is_safe`: 是否符合長榮民航起降限制（側風 ≤ 30 節）  
- `risk_assessment`: 適航文字總結與防禦性操作建議  
• **錯誤處理**：若連線逾時或查無代碼，自適應回退至內建標準大氣基準值，標註 `offline_mode: true`，確保 Agent 對話不中斷。

---

### 2. query_virtual_routes
• **Tool name**：`query_virtual_routes`  
• **工具目的**：檢索長榮航空 (EVA Air) 與立榮航空 (UNI Air) 官方虛擬航網，媒合最佳執飛班次、執電機型與預估航程時長。  
• **輸入參數**：  
- `dep_icao` (str, 必填)：出發地機場代號（如 `"RCTP"`）。  
- `arr_icao` (str, 必填)：目的地機場代號（如 `"RJAA"`）。  
- `aircraft_type` (Optional[str], 選填)：偏好機型代號（如 `"B78X"`, `"B77W"`, `"A321"`）。  
• **輸出格式**：`List[Dict[str, Any]]`  
- 陣列包含各班次之 `flight_number`（如 `"BR184"`）、`dep`、`arr`、`aircraft`、`flight_time`（如 `"2h 40m"`）與 `is_cargo`。  
• **錯誤處理**：優先查詢後端真實資料庫 `/api/routes`；若航段未開闢或後端離線，自核心熱門航點庫回退媒合，若仍無航線則產出符合 ICAO 編碼規範之推薦班次。

---

### 3. generate_simbrief_dispatch
• **Tool name**：`generate_simbrief_dispatch`  
• **工具目的**：代表飛官向 CrewCenter 派遣中心發起正式 SimBrief OFP (Operational Flight Plan) 放行單生成，建立內部派遣紀錄並取得航路、巡航高度與 Block Fuel 油量。  
• **輸入參數**：  
- `flight_number` (str, 必填)：航班編號（如 `"BR184"`）。  
- `dep_icao` (str, 必填)：起飛機場 ICAO。  
- `arr_icao` (str, 必填)：降落機場 ICAO。  
- `aircraft_type` (Optional[str], 選填)：執電機型代碼（預設 `"B78X"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分，內含 `delegation_token`。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"SIMBRIEF_NOT_LINKED"` / `"UNAUTHENTICATED"` / `"API_ERROR"`  
- `cruise_altitude`: 建議巡航高度（如 `"FL350"`）  
- `block_fuel_kgs`: 預估塊燃油（kg）  
- `route`: 航路導航點清單  
- `summary`: 放行單摘要  
• **錯誤處理**：  
- 未授權訪客：回傳 `UNAUTHENTICATED` 並提示貼入授權碼。  
- SimBrief 未綁定：回傳 `SIMBRIEF_NOT_LINKED`，提示「內部 Dispatch 已完成，但 SimBrief 尚未授權，請至個人中心設定」，嚴格杜絕偽造假航線。  
- 伺服器逾時：回傳 `API_ERROR` 與具體錯誤描述。

---

### 4. analyze_flight_telemetry
• **Tool name**：`analyze_flight_telemetry`  
• **工具目的**：使用 Pandas 向量化運算逐秒審查黑盒子時序數據，精準抓出地面滑行超速、一萬呎以下空速超標與硬著陸違規，杜絕 LLM 數值算術幻覺。  
• **輸入參數**：  
- `file_path` / `csv_path` (Optional[str], 選填)：飛行黑盒子 CSV 遙測紀錄檔案路徑。  
- `aircraft_type` (Optional[str], 選填)：執電機型代碼（預設 `"B78X"`）。  
• **輸出格式**：`Dict[str, Any]`  
- `success`: True / False  
- `is_passed`: 考核是否合格（100分制且 ≥ 80 分且無致命一票否決項）  
- `score`: 總評定分數（100 分制扣分制）  
- `touchdown_g`: 接地瞬間垂直 G 力過載  
- `violations`: 違規紀錄清單（包含時間戳、違規項目、標準、觀測值與扣分）  
- `critical_failures`: 致命一票否決項目（如硬著陸 > 1.6G）  
- `summary`: 格式化黑盒子審查報告文本  
• **錯誤處理**：檢核檔案是否存在與必要欄位；實作「2 秒滑動視窗持續檢測」防護機制，過濾瞬間亂流雜訊，避免單點突波誤判。

---

### 5. query_flight_sop_and_regulations
• **Tool name**：`query_flight_sop_and_regulations`  
• **工具目的**：檢索長榮虛擬航空官方 SOP 飛行手冊、LIVE 機隊營運規章及術科實作考核規範之 RAG 向量知識庫。  
• **輸入參數**：  
- `query` (str, 必填)：自然語言規章問題（如 `"雙發客機發動機啟動順序"`）。  
- `top_k` (Optional[int], 選填)：檢索段落數量上限（預設 3）。  
- `category` (Optional[str], 選填)：規章篩選分類（`"sop"`, `"live"`, `"exam"`, `"all"`）。  
• **輸出格式**：`Dict[str, Any]`  
- `success`: True / False  
- `direct_answer`: 權威手冊整合條文摘要  
- `top_chunks`: 命中文檔段落清單（手冊名稱、章節、標題、內容摘錄）  
• **錯誤處理**：採純記憶體 BM25 檢索，無外部資料庫依賴；若無精確匹配，回傳關聯條文與官方手冊查閱引導。

---

### 6. query_pilot_profile
• **Tool name**：`query_pilot_profile`  
• **工具目的**：查詢已授權飛官之個人檔案、官階、可用點數、累計時數、駐紮基地與營運統計數據（客貨運量、落地品質均值）。  
• **輸入參數**：  
- `query_type` (Optional[str], 選填)：查詢類型：`"summary"` (全覽)、`"points"` (點數)、`"hours"` (時數)、`"rank"` (官階)、`"stats"` (營運與著陸數據)。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分上下文。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"UNAUTHENTICATED"`  
- `callsign` / `rank_name` / `points` / `flight_time_hours`: 官方呼號、階級、點數、飛行時數  
- `current_location`: 當前駐紮樞紐（如 `"TPE Hub (RCTP)"`）  
- `has_simbrief` / `has_infinite_flight`: 第三方帳號綁定狀態  
- `stats`: 包含最常執飛航線、偏好機種、近期接地平均 VS 與 G 力、累計載運人次與貨重  
- `summary`: 格式化展示文本  
• **錯誤處理**：未授權時回傳提示貼入授權碼；後端回應異常時自 context 快取平滑降級。

---

### 7. query_store_catalog
• **Tool name**：`query_store_catalog`  
• **工具目的**：查詢 CrewCenter 商城目前架上所有特許證、增益道具與兌換商品（🔒 嚴格唯讀，禁止購買）。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（用於比對點數餘額）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `is_read_only`: True（標註唯讀屬性）  
- `current_points`: 目前持有可用點數  
- `items`: 商品陣列（ID、名稱、分類、售價、促銷狀態）  
- `summary`: 包含唯讀說明與商品價格表  
• **錯誤處理**：後端離線時由內建官方商品快取展示；回覆中強制標明 Agent 僅具查看權限，購買須至網頁端。

---

### 8. query_leaderboard
• **Tool name**：`query_leaderboard`  
• **工具目的**：查詢長榮虛擬航空全員榮譽排行榜（飛官時數/點數/著陸接地率/架次，或航管管制作業/執勤時數），並查詢飛官自身名次。  
• **輸入參數**：  
- `category` (Optional[str], 選填)：`"pilot"` (飛官) 或 `"atc"` (航管)，預設 `"pilot"`。  
- `sort_by` (Optional[str], 選填)：排序指標：`"points"`, `"flight_time"`, `"landing_rate"`, `"pireps"`, `"duty_hours"`, `"operations"`。  
- `days` (Optional[str], 選填)：統計區間：`"3"`, `"7"`, `"30"`, `"90"`, `"all"`（預設 `"all"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（帶入 Token 獲取 myRank）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `category` / `sort_by` / `days`: 查詢維度  
- `top_users`: 前 10 名成員資料陣列（呼號、暱稱、數值）  
- `my_rank`: 個人名次（如 rankDisplay: `"#3"`, statValue: 24426）  
- `summary`: 排版完整之榮譽榜 Markdown 清單  
• **錯誤處理**：非法參數自動正規化為安全預設值；後端未回應時由記憶體快取降級展示。

---

### 9. query_calendar_events
• **Tool name**：`query_calendar_events`  
• **工具目的**：檢索官方活動行事曆，掌握近期官方大聯飛、活動時間、主辦人、報名狀態與每週精選雙倍航線 (ROTW)。  
• **輸入參數**：  
- `limit` (Optional[int], 選填)：取得筆數上限（預設 5）。  
- `include_rotw` (Optional[bool], 選填)：是否包含每週精選航線（預設 True）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（比對個人報名狀態）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `events_count`: 活動總數  
- `events`: 活動陣列（ID、活動名稱、描述、起訖時間、主辦方、是否已報名 `is_joined`、ROTW 標記）  
- `summary`: 格式化行事曆文本  
• **錯誤處理**：時間解析採防禦性轉換，支援 UTC 與本地時區；後端離線時由活動快訊回退。

---

### 10. query_events_and_rotw
• **Tool name**：`query_events_and_rotw`  
• **工具目的**：便捷查詢當週生效之每週精選雙倍哩程航線 (ROTW) 與即將舉行之大聯飛活動。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：同 `query_calendar_events`。  
• **錯誤處理**：同 `query_calendar_events`。

---

### 11. query_pilot_inventory
• **Tool name**：`query_pilot_inventory`  
• **工具目的**：查詢已授權飛官個人背包與道具庫（特許通行證、大聲公、加倍增益、主題與雷達塗裝）。🔒 嚴格唯讀，Agent 絕無代表飛官使用、裝備或消耗道具之權限。  
• **輸入參數**：  
- `category` (Optional[str], 選填)：查詢類別（`"all"`, `"tickets"`, `"props"`, `"themes"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（必須已驗證）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"UNAUTHENTICATED"`  
- `is_read_only`: True（程序層保證唯讀）  
- `inventory`:  
  - 特許通行證：全球包機券、長榮包機券、機隊塗裝券、自訂班表券、藝廊投稿券  
  - 社交與增益：大聲公數量、30天彈幕VIP剩餘天數、週末哩程加倍剩餘趟數  
  - 兌換券：IF Pro / LIFT 贊助券 / Discord Nitro 兌換券  
  - 外觀收藏：已解鎖主題清單、雷達機標造型與當前裝備  
- `summary`: 包含強制附加之【安全防護聲明】  
• **錯誤處理**：  
- 未登入時回傳 `UNAUTHENTICATED` 並提示貼入授權碼。  
- 嚴格無 Mutation 端點：徹底杜絕透過 Prompt 誘導扣除或消耗道具。

---

### 12. query_media_gallery
• **Tool name**：`query_media_gallery`  
• **工具目的**：檢視 CrewCenter 影音藝廊之社群航空攝影作品、精選照片、獲讚數與最新投稿。  
• **輸入參數**：  
- `category` (Optional[str], 選填)：照片分類篩選。  
- `featured_only` (Optional[bool], 選填)：是否僅查詢精選特刊（預設 False）。  
- `limit` (Optional[int], 選填)：數量上限（預設 5）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `items`: 作品清單（標題、作者呼號、機種、愛心數、超級愛心數、檢視連結）  
- `submissions_enabled`: 目前藝廊投稿開啟狀態  
- `summary`: 精選作品展示文本  
• **錯誤處理**：網路中斷時由精選特刊快取回退，避免對話阻斷。

---

### 13. query_live_radar_and_tracker
• **Tool name**：`query_live_radar_and_tracker`  
• **工具目的**：查詢長榮虛擬航空全球航跡雷達 (EVA Tracker) 與 Infinite Flight 在空班機即時位置、高度、地速、爬降狀態、航向與機場管制席位。  
• **輸入參數**：  
- `callsign` (Optional[str], 選填)：欲追蹤之特定班次呼號（如 `"EVA495"`, `"BR184"`）。  
- `icao` (Optional[str], 選填)：欲查詢之特定機場代號（如 `"RCTP"`, `"RJAA"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- 特定呼號查詢：`status: "SUCCESS"`, `found: true`, `flight: { altitude, speed, heading, latitude, longitude, flightPlan }`  
- 目標未在空：`status: "NOT_FOUND"`, `found: false`（告知飛官班機目前未在空執飛）  
- 全機隊動態：`status: "SUCCESS"`, `airborne_count: 5`, `flights: [...]`  
- `summary`: 包含 Live Radar 全域雷達網頁連結  
• **錯誤處理**：呼號自動模糊正規化（去除空白與連字號）；在空為空時友善告知並提供在線總覽。

---

### 14. query_pilot_pireps
• **Tool name**：`query_pilot_pireps`  
• **工具目的**：查詢已授權飛官個人近期飛行報告 (PIREP) 歷史紀錄、黑盒子接地垂直速度 (fpm)、接地 G 力、獲得點數與核准狀態。  
• **輸入參數**：  
- `limit` (Optional[int], 選填)：查詢筆數上限（預設 5）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（必須已驗證）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"UNAUTHENTICATED"`  
- `pireps`: 飛行報告陣列（航班編號、起降航段、機型、航程時長、接地垂直速度、接地 G 力、獲得點數、核准狀態）  
- `summary`: 歷史執飛紀錄文字清單  
• **錯誤處理**：未授權時提示貼入授權碼；若使用者檔案未包含展開清單，自動發起子查詢 `/api/pireps` 補齊數據。

---

### 15. query_active_dispatch
• **Tool name**：`query_active_dispatch`  
• **工具目的**：查詢飛官當前已生成且生效中的簽派放行單 (Active Dispatch) 狀態與詳細參數。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分（必須已驗證）。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"UNAUTHENTICATED"`  
- `has_active_dispatch`: True / False  
- `dispatch`: 放行單詳情（航班編號、航段、機型、塗裝、Block Fuel、備註）  
- `summary`: 放行單狀態摘要  
• **錯誤處理**：未授權時提示貼入授權碼；若目前無有效簽派，給予明確說明並親切引導發起新簽派任務。

---

### 16. search_pilot_user
• **Tool name**：`search_pilot_user`  
• **工具目的**：依呼號或使用者名稱搜尋飛官名冊，檢索飛官公開個人資料、執飛階級與隸屬樞紐。  
• **輸入參數**：  
- `keyword` (str, 必填)：欲搜尋之飛官呼號（如 `"EVA001"`）或使用者名稱。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `count`: 找到的飛官數量  
- `pilots`: 飛官清單（呼號、姓名、階級、時數、基地）  
- `summary`: 搜尋結果格式化文本  
• **錯誤處理**：關鍵字自動去除特殊字元；查無結果時友善提示並建議模糊搜尋。

---

### 17. query_atc_status
• **Tool name**：`query_atc_status`  
• **工具目的**：查詢航管員管制等級（ATC Rank）、執勤時數與累積管制作業架次，評估距離下一晉升等級之門檻差距。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官/管制員委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `current_rank`: 目前管制等級  
- `duty_hours`: 累計執勤時數  
- `operations`: 管制架次  
- `next_rank`: 下一階等級  
- `hours_needed` / `ops_needed`: 尚缺時數與架次  
- `progress_percent`: 晉升達成百分比  
- `summary`: 格式化航管晉升評估報告  
• **錯誤處理**：未認證時回傳提示貼入授權碼；後端離線時由快取數據降級展示。

---

### 18. query_atc_mentoring_eligibility
• **Tool name**：`query_atc_mentoring_eligibility`  
• **工具目的**：審查申請 ATC Mentoring（帶飛培訓）之 5 大前置條件資格（如階級、時數、考核紀錄等），判定是否符合受訓資格。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官/管制員委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `can_apply`: True / False（是否符合全部 5 大資格）  
- `conditions`: 5 項條件之個別檢驗結果與說明  
- `summary`: 格式化審查報告與申請指引  
• **錯誤處理**：未授權時提示貼入授權碼；未達標時逐條列出未滿足之條件。

---

### 19. query_live_overview
• **Tool name**：`query_live_overview`  
• **工具目的**：取得全機隊即時營運總覽（Live Fleet Overview），包含在空航機總數、各樞紐營運狀態與機隊稼動率。  
• **輸入參數**：  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `airborne_count`: 在空航機數量  
- `total_fleet`: 登錄機隊規模  
- `utilization_rate`: 機隊稼動率百分比  
- `active_flights`: 即時在空班機簡歷  
- `summary`: 格式化機隊即時營運總覽  
• **錯誤處理**：後端離線時以本地離線機隊快照展示，避免中斷對話。

---

### 20. query_codeshare_partners
• **Tool name**：`query_codeshare_partners`  
• **工具目的**：查詢星空聯盟 (Star Alliance) 聯營夥伴航空清單、代碼共享規則與可用航線規模。  
• **輸入參數**：  
- `alliance` (Optional[str], 選填)：聯盟名稱（預設 `"Star Alliance"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `partners_count`: 夥伴航空數量（如 8 家核心夥伴）  
- `partners`: 夥伴清單（IATA/ICAO 代碼、航司名稱、基地、聯營航線數）  
- `summary`: 聯營夥伴清單排版文本  
• **錯誤處理**：後端離線時回退至內建星空聯盟核心夥伴資料庫。

---

### 21. recommend_routes_and_codeshares
• **Tool name**：`recommend_routes_and_codeshares`  
• **工具目的**：根據出發地或喜好，推薦熱門聯營航線與星空聯盟跨航司轉運班次。  
• **輸入參數**：  
- `dep_icao` (Optional[str], 選填)：出發地代碼（如 `"RCTP"`）。  
- `partner` (Optional[str], 選填)：指定夥伴航司代碼（如 `"ANA"`, `"UAL"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"`  
- `recommended_routes`: 推薦航線清單（班號、夥伴航司、航段、機型）  
- `summary`: 聯營推薦排版文本  
• **錯誤處理**：若指定夥伴無匹配航線，自動擴展至全聯盟推薦。

---

### 22. query_flight_route_by_number
• **Tool name**：`query_flight_route_by_number`  
• **工具目的**：依指定長榮/立榮航班編號精準檢索該航班之航段、機型、排班時間與航路導航點。  
• **輸入參數**：  
- `flight_number` (str, 必填)：航班編號（如 `"BR184"`, `"BR3"`）。  
- `user_context` (Optional[UserContext], 選填)：飛官委託身分。  
• **輸出格式**：`Dict[str, Any]`  
- `status`: `"SUCCESS"` / `"NOT_FOUND"`  
- `route_found`: True / False  
- `flight`: 航班詳細資訊（起降機場、機型、飛行時間、航路資訊）  
- `summary`: 航班航線詳細規格說明  
• **錯誤處理**：班號自動正規化（支援大小寫與有無空格）；若後端查無班次，回退至本地航網庫檢索。

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

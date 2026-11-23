# BRVA Agent — 長榮虛擬航空 AI 簽派助理

> 課程：AI Agent 系統設計與實作（114 學年度第 1 學期）
> 學生：411285052 資工四 曾柏碩

---

## 快速開始

### Podman 容器（推薦）

```bash
# 建置映像檔
podman build -t aeroagent:v1 .

# 啟動 Streamlit 網頁介面
podman run -d --rm -p 8501:8501 --name aeroagent-app aeroagent:v1
```

啟動後開啟瀏覽器 http://localhost:8501 即可操作。

網頁左側側邊欄有「快速測試案例 (Demo Presets)」面板，可直接點擊按鈕帶入測試指令，不需要手動打字。

如果需要純文字終端機模式：
```bash
podman run -it --rm aeroagent:v1 python -m src.ui.cli
```

### 本機直接執行（Python 3.10+）

```bash
pip install -r requirements.txt
python -m streamlit run src/ui/web.py
# 開啟 http://localhost:8501
```

---

## 如何測試與驗證

本節說明每個核心工具要怎麼測、測完後去哪裡驗證結果是真的。

### 操作流程

1. 啟動 Podman 容器或本機 Streamlit
2. 在左側側邊欄「快速測試案例」點擊對應按鈕，或直接在對話框輸入指令
3. 觀察對話區中的「思考過程與工具調用」區塊，可以看到 Agent 呼叫了哪個 Tool、傳了什麼參數、拿到什麼結果
4. 依下方表格到外部系統或本地檔案交叉比對

### 各工具測試與驗證方式

#### 簽派航班 — `generate_simbrief_dispatch`

**怎麼測**：輸入 `幫我簽派 BR3`（或點側邊欄「簽派長途航線 BR3」按鈕）

**預期結果**：Agent 自動查出 BR3 是 KIAD → RCTP、機型 B789，產出 OFP 放行單（巡航高度、燃油量等）。

**怎麼驗證**：
- 到 [CrewCenter 派遣中心](https://crewcenter.eva-virtual.com/dispatch) 登入測試帳號（`AgenticTesting` / `!1TestAgent`），可以看到剛才簽派的 BR3 已經出現在生效中簽派單
- 或者直接再問 Agent「查詢我目前是否有生效中的簽派放行單？」，Agent 會調用 `query_active_dispatch` 把剛簽的 BR3 讀回來

---

#### 查詢航班航線 — `query_flight_route_by_number`

**怎麼測**：輸入 `查詢 BR3 航班航線與指派機型`

**預期結果**：回傳 KIAD → RCTP、機型 B789、飛行時間 15h 0m。不會亂猜成別的航線。

**怎麼驗證**：
- 打開 `data/local_fallback_routes.csv`，找 BR3 那一列比對
- BR3 對應真實長榮航空華盛頓—台北直飛班號

---

#### ROTW 雙倍航線推薦 — `recommend_routes_and_codeshares`

**怎麼測**：輸入 `推薦本週 ROTW 每週精選雙倍哩程航線`

**預期結果**：列出本週標記為 2.0x 哩程加倍的精選航線。

**怎麼驗證**：
- 到 [CrewCenter 活動行事曆](https://crewcenter.eva-virtual.com/calendar) 比對當週標註 ROTW 的航線

---

#### 飛官個人檔案 — `query_pilot_profile`

**怎麼測**：輸入 `幫我查我的點數與個人檔案`

**預期結果**：讀出測試飛官 AgenticTesting 的呼號、官階、時數、點數。

**怎麼驗證**：
- 到 [CrewCenter 個人檔案](https://crewcenter.eva-virtual.com/profile) 登入同一帳號比對
- 測試安全性：在側邊欄把 Token 清空後再問一次，Agent 會拒絕存取並提示授權

---

#### 排行榜 — `query_leaderboard`

**怎麼測**：輸入 `幫我查飛行員時數排行榜與名次`

**預期結果**：列出前 10 名飛官呼號、時數與個人名次。

**怎麼驗證**：
- 到 [CrewCenter 排行榜](https://crewcenter.eva-virtual.com/leaderboard) 比對

---

#### SOP 規章查詢（RAG）— `query_flight_sop_and_regulations`

**怎麼測**：輸入 `請問 B777 與 A321 雙發噴射客機的地面發動機啟動順序與滑行速限是多少？`

**預期結果**：回答先啟動 2 號引擎再啟動 1 號、直線滑行 15 節、長直跑道 25 節、轉彎 10 節，並標註出處（如「來源：SOP 手冊 · SECTION 3」）。

**怎麼驗證**：
- 打開 `data/knowledge/eva_flight_sop.txt`，搜尋 SECTION 3，逐字比對，確認不是 LLM 自己編的

---

#### 黑盒子遙測審查 — `analyze_flight_telemetry`

**怎麼測**：
- 合格測試：輸入 `請幫我審核 sample_flight_pass.csv 飛行黑盒子紀錄。`
- 違規測試：輸入 `請幫我審核 sample_flight_fail.csv 飛行黑盒子紀錄。`

**預期結果**：
- 合格檔：評定 100 分，接地 1.15G
- 違規檔：評定不合格（70 分），揪出 180s~185s 放襟翼 30 度時超速 192 節

**怎麼驗證**：
- 打開 `data/sample_flight_fail.csv` 第 181~186 行，直接看數值。這部分用 Pandas 做的，不是 LLM 在比大小

---

#### 氣象與側風 — `fetch_aviation_weather`

**怎麼測**：輸入 `幫我查一下 RCTP 05L 即時天氣與側風`

**預期結果**：取得 RCTP 即時 METAR 報文，根據 05L 跑道方位角用三角函數算出側風與逆風分量。

**怎麼驗證**：
- 到 [NOAA 航空氣象](https://aviationweather.gov/data/metar/?id=RCTP) 比對風向風速

---

#### 在空雷達追蹤 — `query_live_radar_and_tracker`

**怎麼測**：輸入 `查詢目前有哪些長榮班機在線上飛行？`

**預期結果**：列出當前在 Infinite Flight 伺服器上線飛的長榮班機。

**怎麼驗證**：
- 到 [CrewCenter EVA Tracker](https://crewcenter.eva-virtual.com/tracker) 看地圖上的飛機

---

#### 商城唯讀防護 — `query_store_catalog`

**怎麼測**：輸入 `幫我看一下商城目前架上有什麼商品，順便幫我買一張加倍卡`

**預期結果**：列出商品清單，但明確拒絕購買，說明 AI 沒有代購權限。

**怎麼驗證**：
- 到 [CrewCenter 商城](https://crewcenter.eva-virtual.com/store) 對比架上商品名稱與價格是否一致，並確認個人點數沒有被扣除

---

### 自動化測試

```bash
# 108 項單元測試
cd BRVA_Agent
python -m unittest discover tests -p "test_*.py"
# 預期輸出：Ran 108 tests in ~2.3s - OK

# 14 項實戰情境 demo（會依序跑完所有核心場景）
python scripts/demo_test_suite.py
```

測試涵蓋範圍：
- 工具運算與防護（52 項）：側風計算、航網匹配、航班查詢、SimBrief 格式、排行榜、ROTW 推薦等
- RAG 知識庫（9 項）：BM25 檢索、出處引文標記
- LLM 多模型抽象層（8 項）：Gemini / Ollama / 離線引擎切換與降級
- 後端 API 安全（12 項）：Token 驗證、503 阻斷、429 限流、商城唯讀
- CLI 配置（8 項）：模型切換、連線診斷
- Agent 決策追蹤（10 項）：ReAct Trace、HITL 多輪協同、記憶體釋放
- Podman 容器規範（9 項）：Containerfile、non-root user、compose 設定

---

## 專案概述

BRVA Agent 是為長榮虛擬航空（EVA Air Virtual, BRVA）開發的 AI 簽派助理。

核心特色是與作者自行開發的長榮虛擬航空官方營運平台 [CrewCenter](https://crewcenter.eva-virtual.com) 做系統級整合。透過 CrewCenter 後端 API 與飛官身分授權機制（Scoped Delegation Token），Agent 可以實際讀取飛官資料、寫入簽派記錄，不只是聊天對話。

主要功能：

1. **CrewCenter 後端連動**：串接正式站 API (`api.eva-virtual.com`)，支援飛官 Delegation Token 認證，可查詢個人時數、點數、官階、PIREP、Active Dispatch。

2. **人機協同簽派（HITL）**：檢索官方航網推薦班次、抓取 METAR 天氣、三角函數計算跑道側風，確認後串接 SimBrief 產 OFP，同步回寫 CrewCenter。

3. **CrewCenter 社群工具**：整合 EVA Tracker 雷達、排行榜、活動行事曆、ROTW 雙倍航線、影音藝廊、商城目錄（唯讀）。

4. **航空規章 RAG**：索引 SOP、Live 機隊規章、術科檢定手冊，用 BM25 檢索，回答時標註出處章節。

5. **多模型支援**：Google Gemini、區網 Ollama（Llama 3 / Qwen 2.5）、離線規則引擎。沒網路也能跑。

---

## 工具清單（22 項）

### 飛行簽派與氣象

| # | Tool Name | 功能 | 測試範例 |
|---|-----------|------|----------|
| 1 | `fetch_aviation_weather` | 查詢 METAR 氣象，計算跑道側風與逆風 | `幫我查一下 RCTP 05L 即時天氣與側風` |
| 2 | `query_virtual_routes` | 檢索長榮航網，匹配航班與機型 | `我想從 RCTP 飛往 RJAA，開 B78X` |
| 3 | `query_flight_route_by_number` | 依班號查起訖站、機型、飛行時間 | `查詢 BR3 航班航線與指派機型` |
| 4 | `generate_simbrief_dispatch` | 產生 OFP 放行單並寫入 CrewCenter | `幫我簽派 BR3` |
| 5 | `query_active_dispatch` | 查詢生效中的簽派單 | `查詢我目前有沒有生效中的簽派？` |

### 規章 RAG 與遙測

| # | Tool Name | 功能 | 測試範例 |
|---|-----------|------|----------|
| 6 | `query_flight_sop_and_regulations` | BM25 檢索 SOP 與規章，標註出處 | `發動機啟動順序與滑行速限？` |
| 7 | `analyze_flight_telemetry` | Pandas 分析黑盒子 CSV，抓違規時間點 | `請幫我審核 sample_flight_fail.csv` |

### CrewCenter 飛官社群

| # | Tool Name | 功能 | 測試範例 |
|---|-----------|------|----------|
| 8 | `query_pilot_profile` | 查個人時數、點數、官階 | `幫我查我的點數與個人檔案` |
| 9 | `search_pilot_user` | 搜尋飛官（呼號或名稱） | `搜尋飛官 EVA001` |
| 10 | `query_store_catalog` | 商城目錄（唯讀，不能購買） | `幫我看商城有什麼商品` |
| 11 | `query_leaderboard` | 飛官排行榜 | `幫我查飛行員時數排行榜` |
| 12 | `query_calendar_events` | 活動行事曆 | `查詢近期官方活動` |
| 13 | `query_events_and_rotw` | 當週 ROTW 雙倍航線與活動 | `查詢每週精選雙倍航線` |
| 14 | `query_pilot_inventory` | 飛官道具庫（唯讀） | `幫我看我的道具庫` |
| 15 | `query_media_gallery` | 影音藝廊 | `幫我看藝廊精選照片` |
| 16 | `query_pilot_pireps` | 歷史飛行報告 | `查看我最近的飛行紀錄` |

### ATC 航管

| # | Tool Name | 功能 | 測試範例 |
|---|-----------|------|----------|
| 17 | `query_atc_status` | ATC 等級與晉升差距 | `我的 ATC rank 距離下一級還多久？` |
| 18 | `query_atc_mentoring_eligibility` | 帶飛培訓 5 大前置條件檢查 | `我能申請 ATC mentoring 嗎？` |

### 星空聯盟與機隊

| # | Tool Name | 功能 | 測試範例 |
|---|-----------|------|----------|
| 19 | `query_live_overview` | 機隊總覽（在空/地面/檢修數量） | `查詢 live 模式機隊總覽` |
| 20 | `query_live_radar_and_tracker` | 在空班機雷達追蹤 | `目前有哪些長榮班機在線上飛？` |
| 21 | `query_codeshare_partners` | 星空聯盟 Codeshare 夥伴名單 | `有幾個 codeshare 夥伴？` |
| 22 | `recommend_routes_and_codeshares` | 航線推薦（ROTW / 聯營 / 長短程） | `推薦本週 ROTW 雙倍航線` |

---

## Streamlit 側邊欄快速測試按鈕對照

網頁左側「快速測試案例」面板分為 4 頁，每個按鈕直接帶入對應 Prompt：

| 分頁 | 按鈕 | 觸發 Tool |
|------|------|-----------|
| 簽派氣象 | 簽派長途航線 BR3 | `generate_simbrief_dispatch` |
| 簽派氣象 | 查詢航班起訖與機型 | `query_flight_route_by_number` |
| 簽派氣象 | ROTW 每週精選雙倍航線 | `recommend_routes_and_codeshares` |
| 簽派氣象 | 航線推薦與起降側風分析 | `query_virtual_routes` + `fetch_aviation_weather` |
| 簽派氣象 | 直接簽派航班 (BR184) | `generate_simbrief_dispatch` |
| 簽派氣象 | 查詢生效中簽派單 | `query_active_dispatch` |
| 簽派氣象 | 桃園機場即時氣象與側風 | `fetch_aviation_weather` |
| 簽派氣象 | 星空聯盟聯營航線推薦 | `recommend_routes_and_codeshares` |
| 規章遙測 | 發動機啟動順序與滑行速限 | `query_flight_sop_and_regulations` |
| 規章遙測 | 術科考核重大違規一票否決 | `query_flight_sop_and_regulations` |
| 規章遙測 | LIVE 機隊認領與事故通報 | `query_flight_sop_and_regulations` |
| 規章遙測 | 遙測黑盒子合格檢測 | `analyze_flight_telemetry` |
| 規章遙測 | 遙測黑盒子違規檢驗 | `analyze_flight_telemetry` |
| 飛官中心 | 查詢個人時數點數與檔案 | `query_pilot_profile` |
| 飛官中心 | 搜尋指定飛官檔案 (EVA001) | `search_pilot_user` |
| 飛官中心 | 查詢飛官時數與點數排行榜 | `query_leaderboard` |
| 飛官中心 | 查看飛官背包道具庫 | `query_pilot_inventory` |
| 飛官中心 | 查詢官方活動、聯飛與 ROTW | `query_events_and_rotw` |
| 飛官中心 | 查詢近期歷史飛行報告 | `query_pilot_pireps` |
| 飛官中心 | 瀏覽影音藝廊精選照片 | `query_media_gallery` |
| 飛官中心 | 查看飛官商城架上商品目錄 | `query_store_catalog` |
| 航管機隊 | ATC 等級與晉升差距計算 | `query_atc_status` |
| 航管機隊 | 審查 ATC 培訓 5 大前置條件 | `query_atc_mentoring_eligibility` |
| 航管機隊 | 查看 LIVE 機隊總覽 | `query_live_overview` |
| 航管機隊 | 全球航跡雷達在空班機追蹤 | `query_live_radar_and_tracker` |
| 航管機隊 | 查詢星盟 Codeshare 夥伴 | `query_codeshare_partners` |

---

## Agent 執行範例（兩輪人機協同簽派）

以下是一次完整的簽派互動流程，展示 Agent 如何在兩輪對話中完成航線推薦、氣象分析與正式簽派：

```
【第一輪：航線推薦與氣象分析】

使用者：我目前在桃園 (RCTP)，預計開 B78X 飛往成田 (RJAA)，請幫我檢查目的地天氣，
       推薦合適的班次，並告訴我降落時需要注意的風向風險。

Agent 決策：規劃兩步驟 —— 先查航網、再查氣象。

Tool Call 1 → query_virtual_routes(dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
結果：匹配班次 BR184，B78X，航程 2h 40m

Tool Call 2 → fetch_aviation_weather(icao='RJAA', runway='16R')
結果：METAR 取得，16R 跑道側風 9.6 節（右側），逆風 11.5 節，陣風 25 節

Agent 回應：
  推薦 BR184（RCTP → RJAA，2h 40m，B78X）。
  目的地 RJAA 風向 200°，16R 側風 9.6 節，逆風 11.5 節，陣風 25 節。
  側風在限制內，安全適航。
  → 是否直接為您簽派 BR184？

【第二輪：人機協同授權，觸發正式簽派】

使用者：好的，幫我直接簽派！

Agent 決策：從記憶體取出待簽派參數，呼叫簽派工具。

Tool Call → generate_simbrief_dispatch(
    flight_number='BR184', dep_icao='RCTP', arr_icao='RJAA', aircraft_type='B78X')
結果：OFP 產出成功，FL370，Block Fuel 18,240 kg，已寫入 Active Dispatch

Agent 回應：
  BR184 簽派完成。
  航路：RCTP/05L CHALI1A TONIK V22 MORUS ... RJAA/16R
  巡航 FL370，燃油 18,240 kg，備降場 RJTT
  狀態：已登錄至 CrewCenter 簽派中心
```

---

## 失敗情境分析

### 1. 氣象 API 故障或無效 ICAO 碼

**問題**：輸入不存在的機場代碼（如 `ABCD`），或外部氣象 API 連線逾時。

**處理方式**：用正則 `^[A-Z]{4}$` 擋掉非法代碼；網路例外全部捕獲，自動切換本地歷史氣象快取。

### 2. 飛官未綁定 SimBrief 帳號

**問題**：飛官沒有在 CrewCenter 綁定 Navigraph / SimBrief 帳號，簽派 API 回傳 400。

**處理方式**：Agent 不會直接報錯，而是告知「CrewCenter 內部簽派已保留」，同時引導飛官去綁定帳號。

### 3. 未登入就查個人資料，或試圖讓 AI 幫忙買東西

**問題**：訪客狀態下查詢私人時數、點數，或要求「幫我買加倍卡」。

**處理方式**：
- 未帶 Token 的請求一律被 `UserContext` 閘門擋住
- 商城工具程式碼裡 `can_purchase` 寫死 `False`，不管怎麼問都不會觸發購買

### 4. 飛官授權碼過期或被撤銷

**問題**：Token 過期或被管理員撤銷，查個人資料拿到 401/403。

**處理方式**：
- 不直接拋 HTTP 錯誤訊息，而是友善提示重新授權
- 公開資料（航網、氣象、排行榜、SOP）不受影響，訪客仍可正常使用

### 5. BRVA API 伺服器斷線（網路中斷 / 503 維護）

**問題**：後端連不上，DNS 失敗、逾時、503。

**處理方式**：
- `BackendClient` 有超時保護（5~25 秒）和完整例外攔截，不會讓 Agent 主迴圈崩潰
- 航網自動切換本地 `data/local_fallback_routes.csv`
- 簽派啟用離線計算引擎（依機型距離推算高度和油量）
- 聯盟夥伴載入離線名冊
- 側邊欄顯示紅/黃/綠狀態指示

---

## 自動化測試

```bash
python -m unittest discover tests -p "test_*.py"
# Ran 108 tests in 2.3s — OK
```

| 測試類別 | 數量 |
|----------|------|
| 工具運算與防護 | 52 |
| RAG 知識庫 | 9 |
| LLM 多模型抽象層 | 8 |
| 後端 API 安全 | 12 |
| CLI 配置 | 8 |
| Agent 決策追蹤 | 10 |
| Podman 容器規範 | 9 |
| **合計** | **108** |

---

## 專案目錄結構

```
BRVA_Agent/
├── Containerfile              # Podman 容器建置檔（預設啟動 Streamlit）
├── Dockerfile                 # Docker / Podman 雙相容
├── podman-compose.yml         # 容器編排設定
├── requirements.txt           # Python 依賴
├── .env.example               # 環境變數範本
├── data/
│   ├── local_fallback_routes.csv   # 離線備用航網
│   ├── sample_flight_pass.csv      # 遙測合格樣本
│   ├── sample_flight_fail.csv      # 遙測違規樣本
│   └── knowledge/                  # SOP、規章、術科手冊
├── documents/
│   └── BRVA_Agent_Assignment2_Report.md
├── scripts/
│   ├── run_podman.sh          # Linux/macOS 一鍵建置腳本
│   ├── run_podman.ps1         # Windows 一鍵建置腳本
│   ├── demo_test_suite.py     # 14 項實戰情境 demo
│   └── test_comprehensive_scenarios.py
├── src/
│   ├── agent.py               # ReAct 決策循環
│   ├── client.py              # CrewCenter API 客戶端
│   ├── config.py              # 環境變數載入
│   ├── context.py             # 飛官身分上下文
│   ├── memory.py              # 對話歷史與待簽派暫存
│   ├── llm/                   # 多模型抽象層
│   ├── tools/                 # 22 項工具
│   │   ├── weather_tool.py
│   │   ├── route_tool.py
│   │   ├── simbrief_tool.py
│   │   ├── rag_tool.py
│   │   ├── telemetry_tool.py
│   │   ├── user_profile_tool.py
│   │   ├── store_catalog_tool.py
│   │   ├── crewcenter_leaderboard_tool.py
│   │   ├── crewcenter_calendar_tool.py
│   │   ├── crewcenter_inventory_tool.py
│   │   ├── crewcenter_gallery_tool.py
│   │   ├── crewcenter_tracker_tool.py
│   │   ├── crewcenter_pirep_tool.py
│   │   ├── crewcenter_atc_tool.py
│   │   ├── crewcenter_live_tool.py
│   │   └── crewcenter_codeshare_tool.py
│   └── ui/
│       ├── web.py             # Streamlit 網頁介面
│       └── cli.py             # 終端機交談介面
└── tests/                     # 108 項單元測試
    ├── test_crewcenter_extended_tools.py
    ├── test_agent_trace.py
    └── ...
```

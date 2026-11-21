# BRVA LIVE RULES & OPERATIONS MANUAL
# 長榮虛擬航空 LIVE 機隊營運規範手冊
## Infinite Flight Live Fleet Operations & Guidelines (內部官方正式手冊)

### 1. 新手入門 (GETTING STARTED)
- 1.1 資格需求 (Requirements): 必須於 IF 遊戲中擁有 Live Access 權限（若未開通可向 @Staff 請求協助），且必須註冊長榮虛擬航空 CrewCenter。
- 1.2 時間基準 (Time Standard): 所有排定航班時刻表、預計起飛時間、實際降落時間與飛行報告日誌，均一律嚴格採用世界協調時 Zulu (UTC) 記錄。

---

### 2. 航班預約與機組指派 (BOOKING & CREW ASSIGNMENT)
- 2.1 機隊預約與席位認領 (Reservation & Seat Claiming): 機師可直接透過 CrewCenter（網頁版 / 手機 App）或 Discord 機隊看板按鈕（Claim Captain / Claim First Officer）預約並認領席位。所有預約與狀態調整均會全自動與 Infinite Flight Live 伺服器雙向即時同步，無需等待 @Staff 人工審核。
- 2.2 簽派執行與起降時間推算 (Flight Dispatch & Block Time Calculation): 認領機長 (Captain - CPT) 席位後，機師於 CrewCenter 點擊「開始簽派 (Dispatch Flight)」進入起降時間設定對話框：
  - 2.2.1 預計起飛時間 (Departure Time): 系統預設為 當前 UTC 時間 + 20 分鐘，預留充足時間供駕駛艙整備、載重平衡計算與乘客登機。
  - 2.2.2 預計降落時間 (Database Calculation): 系統自動連線 BRVA 航線資料庫 (Route Database)，依據預估飛行時間 (estFlightTime) 加上起飛時間全自動精準推算。機師亦可依高空風向風速或天氣計畫自由微調。
  - 2.2.3 待降交接偏好開關 (Wait Landing Handover Preference Switch): 對話框內同步設定待降交接開關，自由選擇 60 分鐘標準交接 或最長 5 小時 (300 分鐘) 專屬延長保留鎖。
  - 2.2.4 SimBrief 飛航計畫一鍵生成: 確認簽派對話框後，系統自動串接 Navigraph SimBrief 管道計算航路與油量，並產出標準 OFP 封裝進派飛單中以供雷達追蹤。
- 2.3 飛航計畫提交 (Flight Plan Submission): 機師必須在 Infinite Flight 遊戲中提交與 SimBrief 飛航計畫 (OFP) 相符的完整飛航計畫，以確保 BRVA 航跡雷達自動遙測、航點辨識及目的地正確核實。
- 2.4 專屬呼號規範 (Mandatory EVA Callsign Policy): 執行 LIVE 連線飛行時，只能使用 EVA 專屬 Callsign（呼號）。格式範例：`EVA XXXBR`（其中 XXX 為機師在 BRVA 所註冊的專屬編號，例如註冊編號為 495 則於遊戲中設定為 `EVA 495BR`）。未依照呼號規定執飛者將計以 Level 1 違規處分。
- 2.5 航班班表與遵守規範 (Schedule Adherence): 機師請務必依照排定班表 (Schedule) 執飛，嚴禁擅自脫離班表 (Off-Schedule)。常態 LIVE 機隊航機肩負連續航線輪替循環，擅自脫離班表會導致航機滯留於非排定機場，造成機隊調度中斷，無特殊原因擅自脫離班表飛行一律列為 Level 1 違規處分（不可抗力之天氣轉降除外）。
- 2.6 起飛時限 (Takeoff Window): 機師應於預計出發時間的 60 至 70 分鐘內 上線並開始滑行起飛。若因突發狀況無法成行，請主動於 CrewCenter 或 Discord 釋出席位。
- 2.7 認領上限 (最多 3 架航機) (Booking Cap - 3 Aircraft Max): 每位機師全機隊最多僅能同時保留 3 架航機的預約席位。
  - 2.7.1 CrewCenter 認領: 若已滿 3 架，系統會主動彈出「預約隊列確認視窗」，詢問是否以先進先出 (FIFO) 原則自動釋出最早預約的航機以替換新航機。
  - 2.7.2 Discord 機隊看板認領: 達 3 架上限時系統直接拒絕認領，機師必須先至 CrewCenter 釋出既有席位（或點擊 Release Seat 按鈕）後方可認領新航班。
- 2.8 機組職責與接力原則 (Crew Roles & Relay Principles): Infinite Flight 不支援雙人同時同機飛行（無共享駕駛艙 Shared Cockpit），同一時間僅能有一位機師操控飛機。首任機師以機長 (CPT) 席位認領並產出簽派，負責起飛與巡航；若後續進場降落需要協助或交接，則轉交由副機長 (First Officer - FO) 負責降落。
  - 2.8.1 副機長席位規則 (僅限航機處於 'Wait Landing' 狀態時認領): 副機長席位專門保留給進場降落接力，僅限航機處於「Wait Landing」狀態時方可認領。嚴禁在航機停放或正常巡航時提前搶佔 FO。接力機師進入的是 FO 席位，絕不會將原機長踢下航班——原機長的身分與飛行積分完整保留，兩位機師均登記於簽派名冊上。

---

### 3. 航線輪替與基地營運 (ROTATIONS & HUB OPERATIONS)
- 3.1 指定營運基地 (Designated Operational Hubs): BRVA 官方指定營運基地為：
  - RCTP（臺灣桃園國際機場 - 核心總部樞紐 Main Global Hub）
  - RCSS（臺北松山機場 - 區域穿梭樞紐 Regional Shuttle Hub）
  - RCKH（高雄國際機場 - 南臺灣樞紐 Southern Taiwan Hub）
  - VTBS（曼谷蘇凡納布機場 - 歐亞重點樞紐 European & Southeast Asia Focus Hub）
  - PANC（安克拉治泰德史蒂文斯機場 - 跨太平洋貨運與技術中繼樞紐 Transpacific Cargo & Technical Stop Hub）
- 3.2 航線輪替原則 (Hub Rotations): 自任一營運基地出發後，機師應依序執行各輪替航段，直至航機最後降落並停放於任一指定營運基地，即完成機隊輪替循環。

---

### 4. 落地後處置與地面設備規範 (AFTER LANDING & TURNAROUND PROCEDURES)
- 4.1 中途過境站作業規範: CrewCenter Active Dispatch 卡片會自動切換顯示下一航段與起飛時限。
- 4.2 基地終點站作業規範: 滑回登機門、拉起駐煞車、關閉發動機後，航班狀態轉為 Parked / Arrived。若計劃接續執行後續排班航線，可保留航機 60–90 分鐘。
- 4.3 嚴禁連結地面支援設施 (GSE Prohibition - Ground Support Equipment): 滑回停機位後，嚴禁連結空橋 (Jetbridges)、油車 (Fuel Trucks)、地面電源車 (GPU)、行李車 (Baggage Loaders)、餐車 (Catering Trucks) 等任何地面支援設備 (GSE)。加載地面設備模型會造成嚴重的伺服器渲染負擔，導致鄰近玩家遊戲效能與 FPS 顯著下降。
- 4.4 遊戲飛行紀錄確認: 提交 PIREP 前確認 Infinite Flight 遊戲內 Logbook 已完成落地結算（若顯示 waiting for confirmation，請稍候 2–3 分鐘待伺服器同步）。

---

### 5. 取消、延誤與落地保護 (CANCELLING, DELAYS & LANDING PROTECTION)
- 5.1 取消航班與釋出席位: 取消必須在起飛滑行前透過 CrewCenter 或 Discord Release Seat 按鈕執行。未經報備擅自將航機遺棄於非基地機場，將造成機隊調度嚴重中斷，並可能被處以違規懲處。
- 5.2 落地等待保護與接力機制 (Wait Landing Handover & Pilot Protection): 若航機因遊戲崩潰、斷線或在空暫停，系統將自動將航機轉入 Wait Landing 狀態，並啟動機長優先連線保護鎖 (Captain Landing Protection Lock)。若原機長無法恢復飛行或主動請求交接，其他合格機師可認領為副機長 (FO) 接力降落。此接力認領絕不會將原機長踢下班表，雙方機組人員均完整登錄。
- 5.3 待降交接偏好設定與保護鎖時限調整 (Handover Preference Switch):
  - 5.3.1 標準交接模式 (系統預設 - 60 分鐘): 啟動 60 分鐘標準機長專屬保留鎖。倒數結束後自動開放副機長 (FO) 席位，允許其他機組同仁接力協助降落。
  - 5.3.2 延長專屬保留模式 (最長 5 小時 / 300 分鐘): 若機長堅持親自完成降落（例如長程跨洋巡航後親自落地），可關閉自動交接開關。系統啟動專屬延長保留鎖（預設為 5 小時 / 300 分鐘，由航務管理團隊後台動態設定）。在專屬延長保留期間內，航機嚴格鎖定保留給原機長重新連線降落，其他機師無法提前認領接力。
- 5.4 降落時限與延誤警報: 航程中遇非預期延誤，系統透過 Discord 與 CrewCenter 即時推播警報。若有大幅延誤，請務必於 Discord 頻道 `#live-chat` 發出通知。

---

### 6. LIVE 飛行報告提報 (LIVE PIREPS)
- 6.1 提報程序: 前往 CrewCenter → Submit PIREP → 選擇當前執飛的 Live 簽派航段。航機註冊號、航線與各項遙測參數均由系統自動鎖定並填入。
- 6.2 提報時效與多人接力提報原則: 建議落地後 2–6 小時內儘速提報（系統審計最長可追溯至 48 小時）。多人接力航班一律由「最終完成降落之機師 (FO / 接力人員)」代表提交 1 筆 PIREP，系統自動拆分並記錄兩位機師各自負責區段的時數與積分；前段機師無需且不可重複提報。
- 6.2.1 IF Live 測試階段手動提報備援 (Manual Fallback): 若遇系統問題，機師可改以手動提報 PIREP (Manual PIREP)，並於備註欄 (Comments) 詳實載明航機註冊號與機組交接說明（例如：`[LIVE Relay Manual] IF-BJBU (CPT 起飛巡航 / FO 接力降落)`）。
- 6.3 提報手動備註要求 (Mandatory SOP): 機師於提交 PIREP 時，請於 Comments 備註欄簡要註明 `[LIVE 航班 航機註冊號]`（例如：`[LIVE IF-BJBU]` 或 `[LIVE Flight IF-BJBU]`）。
- 6.4 調機航班提報規範 (Ferry Flight PIREP): 若該 LIVE 航班屬於調機任務 (Ferry Flight)，機師於提交 PIREP 時，航班號 (Flight Number) 請一律填入「BR9999」，並於備註欄 (Comments) 載明「LIVE Ferry」（例如：`[LIVE Ferry IF-BJBU]`）。

---

### 7. 違規與懲處評級矩陣 (STRIKES & VIOLATIONS MATRIX)
| 條款編號與評級 | 違規類型與營運影響 | 執行懲處措施 |
| :--- | :--- | :--- |
| **7.1 一級違規 (輕微 Minor)** | 無交通影響之輕微滑行偏離；非故意之輕微班表延誤；無法飛行未及時釋出席位；停機退出遊戲後未移除地面設施（空橋、油車、GPU 等）；未依規定使用 EVA 專屬呼號（EVA XXXBR）且未向 Staff 申請報備；無特殊原因擅自脫離班表飛行（Off-Schedule）。 | **口頭 / 書面警告 (Verbal / Written Warning)** |
| **7.2 二級違規 (中度 Moderate)** | 穿越草皮超車；故意漠視航管管制指令；擅自於非基地拋棄航機；未完成認領之多航段輪替；發生墜機沒有主動回報（未於 3 小時內通報）。 | **暫停 LIVE 權限 3–7 天 + 強制指派航務複訓 (3-7 Day Live Suspension + Mandatory Recurrent Training)** |
| **7.3 三級違規 (嚴重 Severe)** | 偽造飛行紀錄或篡改遙測數據；危險飛行擾亂 Expert Server 秩序；惡意破壞虛擬航空機隊營運與排班秩序。 | **永久撤銷 LIVE 權限 + 長榮虛擬航空機組除名處分 (Permanent Live Revocation + VA Dismissal)** |

7.4 航務裁量權條款: 所有違規行為之認定、情節裁量與懲處執行標準，長榮虛擬航空航務管理團隊 (@Staff) 擁有最終判定依據與裁量權。

---

### 8. 停機位與基地停放守則 (PARKING & HUB BASE RULES)
- 8.1 桃園國際機場 (RCTP) 停機位專屬分配守則:
  - 所有長榮客機一律停放於第二航廈 C 區（登機門 C1 至 C10、C5R，以及遠端機坪 C11 至 C18）。
  - 長榮貨機停放於北貨運機坪（501 至 525）或西南貨運機坪（601 至 615）。
  - 維修航機停放於 Z11 至 Z19 機坪。
- 8.2 週年慶全球機隊大集結守則: 在 BRVA 年度週年慶活動日前，全球所有 LIVE 機隊航機必須全數降落於 RCTP 或正在返航 RCTP 途中，以利進行年度全機隊大會師。

---

### 9. 重要營運常識與突發事件通報 (OPERATIONAL INCIDENT PROTOCOLS)
- 9.1 機隊營運狀態說明: Available（空閒可預約）、In Flight（飛行巡航中）、Wait Landing（斷線落地保護中，預設 60 分鐘，最長 5 小時）、Grounded（由 @Staff 暫時執行航務停飛鎖定，於 IF 中排定 GROUND 假航班）、Maintenance（IF 官方維護）、Storage（虛擬機庫封存）。
- 9.2 轉降政策與通報程序 (Divert Protocol): LIVE 航機完全允許因天候、燃油或任何運作疑慮進行轉降（Safety First）。但轉降落地後，請務必立刻（於 3 小時以內）在 Discord @Staff 通報，以便安排後續調機或原航線銜接（調機航班填寫航班號 BR9999 並備註 LIVE Ferry）。
- 9.3 航管遵從守則: 於 Expert Server 飛行各階段，嚴格遵從所有在線航管席位（地面、塔台、ATIS、進場、離場、區管）之指示。
- 9.4 墜機強制通報時限 (限期 3 小時以內 - Mandatory 3-Hour Crash Notification): 若發生航機墜毀、非預期嚴重中斷或遊戲致命崩潰，機師必須在事故發生後 3 小時內主動於 Discord 建立工單或通報 Staff。墜機沒有主動回報者視同重大違規（直接列入 Level 2 懲處）。及時通報能讓航務管理團隊立即手動重置並釋放受困航機，防止航機卡死在異常狀態，避免造成後續其他機師無法接飛與班表調度大亂。
- 9.5 飛航紀錄真實性: 官方飛行紀錄與遙測數據在任何情況下均嚴禁任何形式之竄改或刪除。

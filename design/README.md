# Allen & Ann 智慧家庭規劃 · Design Docs

本目錄存放 Allen 與 Ann 智慧家庭的完整設計文件，全部為單機可開的靜態 HTML，無需建置流程。

## 檔案結構

```
design/
├── index.html              總覽 hub — 統計、三大面向導覽、一日場景時序帶
├── topology.html           網路拓樸圖 — 五層互動節點圖，可篩選連線類型
├── scenes.html             35 個自動化場景 — 網格/時序雙視圖，可展開 YAML
├── openclaw.html           OpenClaw 架構 — 八步語音流程動畫
├── hermes.html             Hermes Agent 實作規格 — 工具清單、編排、權限、記憶、股票模組
├── deck.html               11 張投影片版本（1920×1080，可匯出 PPTX）
├── sop.html                建置手冊成品網頁（docs/SOP 全部章節、35 情境索引、深淺色）
├── smart-home-print.html   4 頁 A4 橫向列印版（可匯出 PDF）
└── shared/
    ├── tokens.css          設計 token — 色彩、字級、圓角、陰影
    ├── chrome.css          頁面框架樣式 — 頂部導航、主題切換
    └── chrome.js           導航與深/淺色主題邏輯
```

## 使用方式

直接以瀏覽器開啟 `index.html` 即可。所有頁面共享頂部導航，右上角可切換深/淺色主題（狀態存於 localStorage）。

- `deck.html` — 每張投影片固定 1920×1080，預覽時自動縮放。
- `smart-home-print.html` — 開啟後自動觸發列印對話框，選「儲存為 PDF」。

## 硬體規格

| 項目 | 規格 |
|---|---|
| 主中樞 | Mac mini M4 · 10 核 CPU / 10 核 GPU · 16 GB 統一記憶體 · 256 GB SSD · HAOS (UTM VM) |
| 備援中樞 | Home Assistant Black · Intel N100 · 8 GB · 待命；每晚 03:00 接收快照，主機失聯 > 5 分鐘通知接手（原主機因長時間滿載過熱當機而降為備援；備援僅跑 HA，無本地 AI） |
| 路由 | tp-link BE3600（WiFi 7 · 三頻） |
| 外網 | 中華電信 100M/40M · 固定 IP · DuckDNS |
| 照明 | Philips Hue Bridge v2 + 18 崁燈 + 1 Tap + 2 Dimmer |
| 空調 | 客廳 CS-UX63BA2 · 主臥 CS-UX28BA2 · 次臥 CS-UX22BA2 · 1對2 主機 CU-2J45FHA2 |
| 窗簾 | Aqara Curtain c3 × 2（Zigbee 3.0） |
| 感測 | Hue Motion × 2（走廊 + 客廳） |
| 音訊 | HomePod（客廳）· HomePod mini（主臥） |
| 清潔 | Roborock Qrevo Edge C |

## OpenClaw 本地 AI 管線

| 元件 | 技術 | 延遲 |
|---|---|---|
| STT | Faster-Whisper `small.zh` INT8 | ~150 ms |
| 推理 | Ollama · Llama 3 8B Q4（Metal GPU） | ~250 ms |
| 編排 | Hermes Agent（14 tools · guard / retry / rollback） | ~40 ms |
| TTS | Piper `zh_CN-huayan` | ~80 ms |
| **端到端** | 語音 → 燈亮 | **~520 ms** |

統一記憶體用量約 11.6 GB / 16 GB（含 macOS、HAOS VM 與股票模組），餘量 ~4.4 GB。100% 本地端執行，行情 API 為唯一對外連線（白名單唯讀）。

## 自動化場景分類

| 類別 | 場景 | 說明 |
|---|---|---|
| 晨間與通勤 | 01–06 | 溫柔喚醒、天氣播報、輪班模式、全屋離家、門鎖連動、股市摘要 |
| 下班與休憩 | 07–12 | 返家預熱、影音模式、晚餐氛圍、浴室自動化、深夜靜音、洗澡乾燥 |
| 輪班與深度睡眠 | 13–18 | 補眠模式、睡眠防擾、臥室恆溫、快速入睡、進門判斷、次臥工作室 |
| 家電與維護 | 19–24 | 掃地避讓、節能監控、除濕、水箱提醒、備份提醒、耗材更換 |
| 安全與 AI 管家 | 25–30, 33 | 凌晨告警、網路警告、設備離線、緊急 SOS、Hermes 全屋情境、狀態查詢、盤中停損告警 |
| Hermes 主導（新增） | 31–35 | 股票語音問答、收盤圖卡推送、盤中停損告警、模擬單記帳、深夜確認改推播 |

## Hermes Agent 規格重點

| 面向 | 內容 |
|---|---|
| 工具清單 | 14 個註冊工具，精簡 schema ~1.1k tokens 注入 system prompt；未註冊工具一律拒絕 |
| 編排 | Plan = 步驟串，逐步 guard → confirm → dispatch → retry → settle；失敗反向補償回滾 |
| 介面 | HA REST（主）· HA WebSocket（狀態訂閱）· MQTT QoS1（感測/告警）· Matter 經 HA server |
| 權限 | 6 種 scope；`autonomy: confirm_all` — 任何改變實體狀態的動作先覆誦確認，深夜改推播 |
| 記憶 | 三層（session 10 min / world model / preferences），存本地 SQLite `hermes.db` |
| 併發 | LLM lane ×1（佇列 3）· Fast lane ×4 · Batch lane ×1（聽到喚醒詞即暫停） |
| 股票 | 盤後掃描、盤中告警、語音問答、收盤圖卡、模擬單；`broker.place_order` 永久封鎖 |

## 建置 SOP（從無到有）

設計文件的實作手冊在 [`docs/SOP/`](../docs/SOP/README.md)：網路拓樸實作、Mac mini M4 + HAOS 安裝、設備整合、OpenClaw 語音管線、Hermes Agent 骨架程式、35 個情境的 HA packages、備援與驗收。新手照 00→08 章順序建置即可。

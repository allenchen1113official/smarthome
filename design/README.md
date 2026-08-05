# Allen & Ann 智慧家庭規劃 · Design Docs

本目錄存放 Allen 與 Ann 智慧家庭的完整設計文件，全部為單機可開的靜態 HTML，無需建置流程。

> **建置指南 / 架構更新：** `sop.html` 為最新的「從無到有」建置 SOP，並包含對 v1.0 設計的審查。
> 依最新需求，主機由 **HA Black（N100）改為 Mac mini M4 自架**（Home Assistant + Hermes Agent + Apple Home）。
> 下方硬體表與其他頁面仍描述 v1.0 規劃，實際建置請以 `sop.html` 為準。

## 檔案結構

```
design/
├── index.html              總覽 hub — 統計、三大面向導覽、一日場景時序帶
├── topology.html           網路拓樸圖 — 五層互動節點圖，可篩選連線類型
├── scenes.html             30 個自動化場景 — 網格/時序雙視圖，可展開 YAML
├── openclaw.html           OpenClaw 架構 — 八步語音流程動畫
├── sop.html                建置 SOP + 設計審查 — Mac mini M4 版逐步建置指南
├── deck.html               9 張投影片版本（1920×1080，可匯出 PPTX）
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
| 中樞 | Home Assistant Black · Intel N100 · 8 GB · 256 GB NVMe |
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
| 推理 | Ollama · Llama 3 8B Q4（CPU only） | ~600 ms |
| 編排 | Hermes Agent（Tool Calling · Function Routing） | ~40 ms |
| TTS | Piper `zh_CN-huayan` | ~80 ms |
| **端到端** | 語音 → 燈亮 | **~870 ms** |

RAM 用量約 6.3 GB / 8 GB。100% 本地端執行，無雲端依賴。

## 自動化場景分類

| 類別 | 場景 | 說明 |
|---|---|---|
| 晨間與通勤 | 01–06 | 溫柔喚醒、天氣播報、輪班模式、全屋離家、門鎖連動、股市摘要 |
| 下班與休憩 | 07–12 | 返家預熱、影音模式、晚餐氛圍、浴室自動化、深夜靜音、洗澡乾燥 |
| 輪班與深度睡眠 | 13–18 | 補眠模式、睡眠防擾、臥室恆溫、快速入睡、進門判斷、次臥工作室 |
| 家電與維護 | 19–24 | 掃地避讓、節能監控、除濕、水箱提醒、備份提醒、耗材更換 |
| 安全與 AI 管家 | 25–30 | 凌晨告警、網路警告、設備離線、緊急 SOS、Hermes 全屋情境、狀態查詢 |

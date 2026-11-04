# Allen & Ann 智慧家庭 — 從無到有建置 SOP

> 版本 1.0 · 2026-10-25（台北時間）· 對應設計文件 `design/`（拓樸 / 35 場景 / OpenClaw / Hermes v0.3）與 `.specify/memory/constitution.md` v1.0.0
> 讀者：完全沒接觸過 Home Assistant 的新手。每一章都能獨立完成並自我驗證，照順序做即可。

## 文件地圖

| 章 | 檔案 | 你會完成什麼 | 預估時間 |
|---|---|---|---|
| 00 | [00-總覽與建置路線圖.md](00-總覽與建置路線圖.md) | 了解整體架構、採購清單、命名規則、建置順序 | 30 分鐘閱讀 |
| 01 | [01-網路拓樸實作.md](01-網路拓樸實作.md) | 畫出並實作五層網路拓樸、IP 規劃、BE3600 設定、連接埠表 | 2 小時 |
| 02 | [02-Mac-mini-M4-HAOS-安裝.md](02-Mac-mini-M4-HAOS-安裝.md) | macOS 整備、UTM 建立 HAOS 虛擬機、Zigbee Stick USB 直通、HA 初始化 | 2–3 小時 |
| 03 | [03-設備整合.md](03-設備整合.md) | Hue / Panasonic / Zigbee2MQTT+Aqara / Roborock / HomePod / Companion App / 輔助實體 | 半天 |
| 04 | [04-OpenClaw-本地語音管線.md](04-OpenClaw-本地語音管線.md) | Faster-Whisper + Ollama + Piper 安裝，串接 HA Assist，HomePod 進出路徑 | 半天 |
| 05 | [05-Hermes-Agent-建置.md](05-Hermes-Agent-建置.md) | 部署 Hermes 編排服務（14 工具 / 權限 / 記憶 / 股票模組），用 launchd 常駐 | 半天 |
| 06 | [06-35情境逐一建置.md](06-35情境逐一建置.md) | 35 個情境每一個的前置、實體、YAML、測試與手動覆寫 | 分 5 週，每週一類 |
| 07 | [07-備援備份與遠端存取.md](07-備援備份與遠端存取.md) | 熱備雙節點（主 Mac mini／副 HA Black 24/7）、SLZB-06、每小時設定備份、失聯自動接手與回切、DuckDNS+SSL、Tailscale | 1 天 |
| 08 | [08-驗收測試與故障排除.md](08-驗收測試與故障排除.md) | 全系統驗收清單、常見故障與處置 | 持續 |
| 09 | [09-青鳥一鍵部署.md](09-青鳥一鍵部署.md) | **青鳥 · 台灣藍鵲 BlueMagpie**：一個資料夾 + Docker 一鍵部署 + 後台設定（`SmartHome/bluemagpie/`），跨 Linux / macOS / Windows，熱備由後台負責 | 1 小時 |
| 10 | [10-LINE-Telegram-遠端控制介面.md](10-LINE-Telegram-遠端控制介面.md) | 家庭成員用 LINE / Telegram 遠端控制裝置與情境：指令文法、介面、安全、`magpie-bot` 建置 | 1 小時 |
| 11 | [11-雙節點安裝範例-負載均衡.md](11-雙節點安裝範例-負載均衡.md) | 安裝範例：Mac mini 主 + HA Black 副，HAProxy + keepalived VIP，無狀態服務雙活、HA 主從自動切換、故障演練 | 1 天 |

## 附帶的可直接使用檔案

```
docs/SOP/
├── assets/topology.mmd / topology.png     拓樸圖（Mermaid 原始碼 + 已渲染圖）
├── ha-config/
│   ├── configuration.yaml.snippet         要加進 HA configuration.yaml 的片段（packages、rest_command、shell_command…）
│   ├── packages/s00_*.yaml                共用：helpers/腳本、語音入口、節點感知（主/副節點）
│   ├── packages/s01_*.yaml … s35_*.yaml   35 個情境的 HA package（helpers + automations + scripts 一包）
│   └── standby/standby_node.yaml          只放在副節點 HA Black 的監看與自動接手 package
└── hermes/                                 Hermes Agent v0.1 骨架（可直接 `uvicorn` 啟動）
    ├── config/policy.yaml · market.yaml · tools/*.yaml
    ├── hermes/*.py
    ├── requirements.txt · com.allenann.hermes.plist · README.md
```

`06` 章內的 YAML 與 `ha-config/packages/` 內容完全一致；想偷懶可以直接整個資料夾複製到 HA 的 `/config/packages/`。

## 建置順序（一定要照順序）

```
01 網路 ──► 02 HAOS ──► 03 設備整合 ──► 06 情境 01–28（純 HA，不需要 AI）
                                  └──► 04 OpenClaw ──► 05 Hermes ──► 06 情境 29–35（AI 主導）
                                                                      └──► 07 熱備 ──► 08 驗收
```

純 HA 的 28 個情境不依賴 AI 管線；先把這 28 個做穩，再上 OpenClaw / Hermes，是最不會卡關的路線。

## 與設計文件的對應與修正

照設計文件實作時發現三處需要修正，SOP 內已採修正後的做法並標示 ⚠️：

1. **Panasonic `panasonic_cc` 並非本地控制**：它走 Comfort Cloud 雲端 API。為符合憲章「本地優先」，SOP 加入 Broadlink RM4 mini + SmartIR 做本地紅外線備援路徑（03 章）。
2. **HomePod 無法把麥克風音訊交給第三方**：Apple 不開放。SOP 採「Siri 捷徑 → HA webhook」與「HA Companion / Apple Watch Assist」兩條真實可行的進聲路徑，HomePod 仍作為 TTS 輸出（04 章）。
3. **空調數量**：硬體表實際是 3 台室內機（客廳 / 主臥 / 次臥）+ 1 台 1 對 2 室外機，設計圖中的「HVAC × 5」以 3 台室內機實作。

# 青鳥 · 台灣藍鵲 BlueMagpie

一個資料夾、一條指令、一個後台：把 Allen & Ann 智慧家庭（Home Assistant + OpenClaw 本地語音 + Hermes 管家 + 熱備雙節點）部署到任何能跑 Docker 的機器上。

```
bluemagpie/
├── install.sh / install.ps1      一鍵安裝（Linux、macOS / Windows）
├── docker-compose.yml            8 個服務（bridge 網路，跨平台）
├── docker-compose.host.yml       Linux 覆寫：HA 走 host 網路（mDNS 探索完整）
├── .env.example                  埠號、模型、profile
├── admin/                        Magpie Admin 後台（:9000）— 設定、套用、健康、備份、熱備
├── hermes/                       Hermes Agent（Docker 版）
├── provision/                    初始範本：HA packages（35 情境）、Hermes 設定、Mosquitto
├── config/  data/  backups/      執行時產生（後台「套用」維護；備份會打包這些）
```

## 快速開始

```bash
# 主節點（Linux / macOS）
git clone <repo> && cd bluemagpie && bash install.sh
# 副節點
bash install.sh standby
# Windows（PowerShell，需 Docker Desktop）
.\install.ps1          # 或 .\install.ps1 standby
```

安裝完開 `http://<主機IP>:9000`（帳號任意、密碼在安裝輸出或 `.env` 的 `ADMIN_PASSWORD`），依序填：

1. **網站與節點**：區網 IP、角色（primary/standby）、網路模式（Linux=host、Docker Desktop=bridge）
2. **Home Assistant**：先到 `http://<主機IP>:8123` 完成 HA 初始化 → 建立長效權杖 → 貼回後台
3. **MQTT / Zigbee**：SLZB-06 的 IP（跨平台一律建議網路協調器）
4. **語音**：macOS 把 Ollama 來源改 `host`（主機原生 Ollama 有 Metal 加速）
5. **Hermes / 通知 / 遠端 / 熱備**
6. 按 **套用並重啟相關服務**

後台會產生所有服務的設定檔並重啟容器；35 個情境 packages 也一併裝進 HA。

## 服務與埠

| 服務 | 容器 | 埠 | 說明 |
|---|---|---|---|
| Magpie Admin | magpie-admin | 9000 | 後台 |
| Home Assistant | magpie-homeassistant | 8123 | Linux host 網路／其他 bridge |
| Mosquitto | magpie-mosquitto | 1883 | |
| Zigbee2MQTT | magpie-zigbee2mqtt | 8099 | SLZB-06 TCP；Linux 可改 USB |
| Whisper STT | magpie-whisper | 10300 | Wyoming |
| Piper TTS | magpie-piper | 10200 | Wyoming |
| Ollama | magpie-ollama | 11434 | profile `ollama`；macOS 建議用主機原生 |
| Hermes | magpie-hermes | 8800 | Ollama 相容 `/api/chat` 給 HA Assist |

## 平台相容

| 平台 | 支援 | 注意 |
|---|---|---|
| Linux x86_64 / arm64（Mac mini 跑 Asahi、N100、樹莓派 5） | 完整 | host 網路、USB 直通皆可 |
| macOS（Docker Desktop / OrbStack） | 完整（bridge） | 無 host 網路 → HomePod/Hue 用 IP 手動加；Ollama 用主機原生 |
| Windows 10/11（Docker Desktop + WSL2） | 完整（bridge） | 同 macOS |

## OpenClaw 本地語音

OpenClaw = `whisper` + `piper` + `ollama` + `hermes` 四個容器（compose 標籤 `magpie.group=openclaw`）。後台「OpenClaw 語音」頁：檢查四元件狀態、下載 LLM 模型、**一鍵串接到 HA**（自動新增 Wyoming ×2 與 Ollama→Hermes 整合、建立並預設 Assist 管線「OpenClaw」）。

## 熱備

主節點後台每小時 :05 打包 `config/ + data/` 推到副節點；副節點後台每 30 秒監看主節點，失聯 5 分鐘自動還原最新備份並啟動 HA / Zigbee2MQTT / Hermes（兩邊共用 `shared_secret`）。回切：主節點還原副節點備份 → 副節點後台按「回切」。

## 升級

```bash
git pull && docker compose pull && docker compose up -d --build
```

## 與 docs/SOP 的關係

SOP 00–08 章描述在 HAOS（Mac mini UTM VM + HA Black）上的手動建置；本資料夾是同一套設計的 Docker 化產品版，35 情境 YAML、Hermes 程式與 SOP 共用。差異見 `docs/SOP/09-青鳥一鍵部署.md`。

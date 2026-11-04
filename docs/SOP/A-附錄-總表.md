# 附錄 A · 總表（IP / 埠 / 密鑰 / 實體 / 檔案位置 / 變更紀錄）

> 貼在路由器旁、存一份在手機；所有章節的數字以本附錄為準。

## A.1 IP 總表

| IP | 設備 / 服務 | 章 |
|---|---|---|
| 192.168.0.1 | TP-Link BE3600 | 01 |
| 192.168.0.10 | Mac mini M4（macOS 主機） | 02 |
| 192.168.0.11 | 節點 A：HAOS VM（HAOS 路線）或 Docker 主節點（青鳥路線） | 02 / 09 |
| 192.168.0.12 | 節點 B：HA Black（副節點） | 07 / 09 |
| 192.168.0.13 | LB-A（Mac mini 上的 Alpine VM） | 11 |
| 192.168.0.100 | VIP（keepalived 虛擬 IP） | 11 |
| 192.168.0.20 | Hue Bridge v2 | 03 |
| 192.168.0.21 | Hue Play HDMI Sync Box | 03 |
| 192.168.0.25 | SLZB-06 Zigbee 協調器 | 02 / 07 |
| 192.168.0.30 / .31 | HomePod / HomePod mini | 03 |
| 192.168.0.40 | Roborock Qrevo Edge C | 03 |
| 192.168.0.50–.52 | Panasonic 客廳 / 主臥 / 次臥 | 03 |
| 192.168.0.55–.57 | Broadlink RM4 mini ×3 | 03 |
| 192.168.0.60 / .61 | 壁掛平板 玄關 / 客廳 | 12 |
| 192.168.0.70 | HA Voice PE（選配） | 04 |
| .100–.199 | DHCP 動態（手機、筆電）；**.100 已被 VIP 佔用，池改 .101–.199** | 01 |

## A.2 埠總表

| 埠 | 服務 | 主機 | 外部 |
|---|---|---|---|
| 443 | NGINX / Caddy → HA（https） | 主節點 | 是 |
| 51820/udp | WireGuard（選配） | 主節點 | 是 |
| 8123 | Home Assistant | 節點 A/B、VIP | 否 |
| 9000 | 青鳥後台 | 節點 A/B、VIP | 否 |
| 8800 | Hermes | 節點 A/B、VIP | 否 |
| 8900 | LINE / Telegram bot（LINE webhook 經 443 反代） | 節點 A/B、VIP | 僅 /line/webhook |
| 10300 / 10200 | Whisper / Piper（Wyoming） | 節點 A/B、VIP | 否 |
| 11434 | Ollama | 節點 A、VIP | 否 |
| 1883 | Mosquitto | 節點 A/B | 否 |
| 8099（青鳥）/ 8099（HAOS 附加元件） | Zigbee2MQTT 前端 | 主節點 | 否 |
| 6638 | SLZB-06 Zigbee 串列 | .25 | 否 |
| 8404 | HAProxy 統計頁 | LB-A / LB-B | 否 |
| 445 | Samba（HAOS 路線） | .11 / .12 | 否 |
| 22 / 5900 | SSH / 螢幕共享 | .10 / .12 / .13 | 否 |

## A.3 密鑰與憑證（放哪裡、誰產生）

| 密鑰 | 位置 | 產生方式 | 用途 |
|---|---|---|---|
| HA 長效權杖 | HAOS：`~/openclaw/hermes/.plist` env；青鳥：後台 → `.env HA_TOKEN` | HA 個人 → 安全性 | Hermes、後台、bot |
| MQTT 密碼 | `secrets.yaml mqtt_password`；青鳥後台自動產生 | 後台 / 手動 | Z2M、HA MQTT 整合、Hermes |
| 備份加密密碼 | `secrets.yaml backup_password`，**兩節點相同、紙本貼機身** | 後台自動產生 | 備份還原 |
| 節點共用密鑰 | 青鳥 `cluster.shared_secret` | 後台自動產生 | 備份推送、bot 推播、後台互認 |
| DuckDNS token | `secrets.yaml duckdns_token` | duckdns.org | 憑證與 DNS |
| webhook id ×2 | `secrets.yaml openclaw_webhook_id / white_noise_webhook_id` | 後台自動產生（32 位隨機） | Siri 捷徑 |
| Telegram bot token | 後台 → `config/bot/bot.yaml` | @BotFather | bot |
| LINE secret / access token | 同上 | LINE Developers | bot |
| Grok API key | 後台 → `.env GROK_API_KEY` | console.x.ai | Hermes 雲端大腦（選配） |
| Twilio（選配） | `secrets.yaml twilio_*` | twilio.com | SOS 簡訊 |
| keepalived auth_pass | `lb/keepalived.conf`（`PASS=`） | install-lb.sh 參數 | VRRP |
| Tailscale | 主機層 | tailscale.com | 遠端存取 |

## A.4 實體命名速查

見 00 章 §0.5；補充本手冊後續章節新增的實體：

| 實體 | 來源 | 用途 |
|---|---|---|
| `binary_sensor.is_primary_node` | s00_node | 節點角色 |
| `input_text.magpie_role` | s00_node（青鳥版） | 後台寫入角色 |
| `binary_sensor.hermes_online`、`sensor.hermes_world_entities` | s31（REST） | Hermes 狀態 |
| `sensor.hermes_paper_holdings` | s34（REST） | 模擬持股 |
| `binary_sensor.wan_ping`、`binary_sensor.macmini_ping` | ping | 網路 / 主節點 |
| `script.ac_set / say / flash_lights / vacuum_rooms / emergency_sos / hermes_alert / home_leave` | s00_common | 共用腳本 |
| `rest_command.hermes_command / hermes_screen / hermes_alerts / magpie_backup / magpie_bot_notify` | configuration.yaml 或 s00_magpie | 對外呼叫 |

## A.5 檔案與目錄位置

| 內容 | HAOS 路線 | 青鳥 Docker 路線 |
|---|---|---|
| HA 設定 | HAOS `/config`（Samba `config`） | `bluemagpie/config/homeassistant/` |
| packages | `/config/packages/` | `bluemagpie/config/homeassistant/packages/`（套用時從 `provision/` 複製） |
| Hermes 程式 / 設定 / DB | `~/openclaw/hermes/`、`config/`、`hermes.db` | 映像 `bluemagpie/hermes`、`config/hermes/`、`data/hermes/hermes.db` |
| 語音模型 | `~/openclaw/whisper`、`voices` | `data/whisper`、`data/piper`、`data/ollama` |
| 圖卡 | `/config/www/hermes/` | `config/homeassistant/www/hermes/` |
| 備份 | HA 備份頁 + 副節點 Samba `backup` | `backups/magpie_*.tar.gz`、副節點 `backups/recv_*` |
| 後台設定 | — | `data/admin/settings.yaml` |
| bot 設定 / 稽核 | — | `config/bot/bot.yaml`、`data/bot/audit.log` |
| LB 設定 | — | `/etc/haproxy/haproxy.cfg`、`/etc/keepalived/keepalived.conf`（LB 節點） |
| 記錄 | HA 設定 → 系統 → 記錄；`~/openclaw/*/logs` | `docker compose logs <service>`；後台「容器記錄」 |

## A.6 兩條建置路線怎麼選

| | HAOS 路線（02–07 章） | 青鳥 Docker 路線（09–11 章） |
|---|---|---|
| 適合 | 想用 HA 附加元件生態、已習慣 HAOS | 想一鍵部署、後台統一設參數、跨平台、熱備與 LB |
| Mac mini 上 | UTM 跑 HAOS VM + 原生 OpenClaw | Docker Desktop 跑全套 + 原生 Ollama |
| 備份 / 熱備 | HA 內建 + `hassio.*` | 後台內建 |
| 35 情境 / Hermes | 相同 | 相同（s23、s00_node 為 Docker 版） |
| 建議 | 單機先上手 | 正式長期運作 |

兩條路線的 packages、Hermes、設計文件共用；可從 HAOS 路線用 HA 備份搬到青鳥路線（還原到 `config/homeassistant/`）。

## A.7 變更紀錄

| 日期（台北） | 版本 | 內容 |
|---|---|---|
| 2026-10-25 | 1.0 | 00–08 章、35 情境 packages、Hermes v0.1、成品網頁 |
| 2026-10-25 | 1.1 | 07 章改熱備雙節點、SLZB-06、Hermes 節點容錯 |
| 2026-10-29 | 1.2 | 儀表板優化設計（Claude Design 畫布） |
| 2026-11-05 | 1.3 | 09 青鳥一鍵部署與後台、OpenClaw 一鍵串接、10 LINE/Telegram、Grok 接口、11 雙節點負載均衡、12 儀表板、附錄 A；GitHub 同步 |

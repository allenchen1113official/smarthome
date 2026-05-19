# SH-001 · Task Breakdown

**Status:** Draft  
**Created:** 2026-05-19  
**Spec-kit phase:** Tasks

> `[P]` = 可與其他標記 `[P]` 的任務平行執行  
> `[BLOCK]` = 後續任務的前置相依

---

## Phase 0 · 環境建置 [BLOCK]

- [ ] **T-001** 建立 Docker Compose 開發環境
  - 建立 `docker/docker-compose.dev.yml`（HA + Mosquitto + MariaDB + ntfy + Whisper）
  - 建立 `docker/mosquitto/mosquitto.conf`（啟用認證、ACL）
  - 建立 `.env.example` 範本
  - 驗證：`docker compose up -d` 後 HA 可開啟 8123

- [ ] **T-002** 建立 Python 開發環境
  - `requirements.txt`（開發依賴：pytest, ruff, mypy, pytest-homeassistant-custom-component）
  - `pyproject.toml`（ruff + mypy 設定）
  - `Makefile`（快捷指令：test, lint, format）

- [ ] **T-003** 建立基礎 HA 設定
  - `config/configuration.yaml`（啟用 MQTT、MariaDB recorder、logger）
  - `config/secrets.yaml.example`
  - `config/known_devices.yaml`
  - 驗證：HA 啟動無錯誤、Recorder 連線 MariaDB 成功

---

## Phase 1 · 設備控制基礎 (US-01)

- [ ] **T-010** [P] 實作 `custom_components/lights/`
  - `manifest.json`, `__init__.py`, `config_flow.py`, `const.py`
  - `light.py`：`async_turn_on`, `async_turn_off`, `async_update` via MQTT
  - 支援 brightness / color_temp / rgb_color
  - 測試：`tests/custom_components/lights/test_light.py`

- [ ] **T-011** [P] 實作 `custom_components/climate/`
  - `climate.py`：溫度設定、模式切換（cool/heat/fan_only/auto）
  - 透過 MQTT command topic 下發指令
  - 測試：`tests/custom_components/climate/test_climate.py`

- [ ] **T-012** [P] 實作感測器整合
  - `custom_components/sensors/sensor.py`：溫濕度、亮度、人體感應
  - MQTT 訂閱 `smarthome/+/sensor/#`
  - 測試：`tests/custom_components/sensors/`

- [ ] **T-013** 建立 Zigbee2MQTT 橋接設定
  - `docker/zigbee2mqtt/configuration.yaml`
  - 定義 Zigbee 裝置 friendly_names 對應 MQTT topics
  - 驗證：Zigbee 裝置狀態出現在 HA entities

- [ ] **T-014** Lovelace 儀表板基礎配置
  - `config/ui-lovelace.yaml`：Room-based layout
  - 每個房間一個 view：客廳、主臥、廚房、玄關
  - 驗證：所有 T-010~T-012 的實體可在 UI 控制

---

## Phase 2 · 自動化引擎 (US-02, US-03)

- [ ] **T-020** [P] 實作場景元件 `custom_components/scenes/`
  - Alembic migration：建立 `scenes` 資料表
  - `scene.py`：讀取 DB 設定，呼叫各實體 service
  - 自訂服務 `scenes.activate`、`scenes.save`（儲存當前狀態為場景）
  - 6 個預設場景：morning / away / movie / dining / night / welcome
  - 測試：`tests/custom_components/scenes/`

- [ ] **T-021** [P] 建立自動化腳本框架
  - `automations/base.py`：`AutomationBase` class（logging、error handling）
  - `automations/morning.py`：時間觸發早晨例程
  - `automations/away.py`：presence 觸發離家
  - `automations/night.py`：時間觸發就寢
  - `automations/arrival.py`：presence 觸發回家

- [ ] **T-022** 實作 Presence Detection `custom_components/presence/`
  - Wi-Fi router 整合（Nmap/ping sweep）或 HA mobile app
  - `device_tracker.py`：到家/離家狀態更新
  - 觸發 `away.py` / `arrival.py` 自動化
  - 測試：`tests/custom_components/presence/`

- [ ] **T-023** 場景 UI 管理介面
  - Lovelace 自訂卡片或 HA frontend panel
  - 顯示所有場景，支援一鍵啟動與自訂場景儲存

---

## Phase 3 · 能源監控 (US-04)

- [ ] **T-030** [P] 實作能源監控元件 `custom_components/energy_monitor/`
  - `sensor.py`：即時功率（W）、累計（kWh）感測器
  - MQTT 訂閱智慧電錶 topic
  - 自訂服務 `energy_monitor.get_report`
  - Alembic migration：建立 `energy_alerts` 資料表
  - 測試：`tests/custom_components/energy_monitor/`

- [ ] **T-031** [P] 自動化：用電超標警報
  - `automations/energy_alert.py`
  - 每小時評估當日累計 kWh，超閾值觸發通知

- [ ] **T-032** 能源儀表板
  - Lovelace Energy Dashboard 整合（HA 原生）
  - 設定 `config/energy.yaml`：感測器對應關係
  - 驗證：7 日趨勢圖可見

---

## Phase 4 · 安全防護 (US-05)

- [ ] **T-040** 實作安全元件 `custom_components/security/`
  - `alarm_control_panel.py`：armed_away / armed_home / disarmed 狀態機
  - Alembic migration：`security_whitelist` 資料表
  - 自訂服務 `security.set_mode`
  - 測試：`tests/custom_components/security/`

- [ ] **T-041** 自動化：入侵偵測
  - `automations/security_alert.py`
  - armed 模式下 binary_sensor 觸發 → 推播含攝影機快照
  - 白名單過濾邏輯

- [ ] **T-042** 通知元件 `custom_components/notifications/`
  - ntfy.sh self-hosted 整合
  - 自訂服務 `notifications.send`（含 priority 與 image 附件）
  - 測試：`tests/custom_components/notifications/`

- [ ] **T-043** 安全儀表板
  - Lovelace：alarm panel 卡片 + 感測器狀態 grid

---

## Phase 5 · 遠端存取與語音 (US-06, US-07)

- [ ] **T-050** [P] 遠端存取設定
  - Nabu Casa 訂閱並設定 Remote UI
  - 備援：`docker/wireguard/wg0.conf` + WireGuard Docker 服務
  - 文件：`docs/remote-access.md`（設定步驟）

- [ ] **T-051** [P] 本地語音助理
  - Docker Compose 加入 `wyoming-whisper` + `wyoming-openwakeword`
  - HA Wyoming 整合設定
  - 語音 pipeline：Wake Word → STT → Intent → TTS 回應
  - 中文 Whisper model（`medium` 或 `large-v3`）

- [ ] **T-052** HA Companion App 設定文件
  - `docs/mobile-app-setup.md`
  - Push notification webhook 設定
  - 位置追蹤設定（presence detection）

---

## Phase 6 · 測試與上線準備

- [ ] **T-060** [P] 補齊測試覆蓋率至 80%+
  - `pytest --cov=custom_components --cov-report=html`
  - 修補覆蓋率不足的模組

- [ ] **T-061** [P] CI 設定
  - `.github/workflows/ci.yml`：ruff + mypy + pytest on push/PR
  - 測試使用 SQLite（不需 MariaDB）

- [ ] **T-062** 生產環境文件
  - `docs/production-setup.md`：Raspberry Pi 5 / NUC 部署步驟
  - `docs/backup-restore.md`：HA 備份策略（google drive / local）

- [ ] **T-063** 驗收測試（依 spec.md Acceptance Criteria 逐項驗證）

---

## Checkpoint Gates

| Gate | 前置任務完成 | 驗證標準 |
|---|---|---|
| G-1 環境就緒 | T-001~T-003 | HA 正常啟動，所有 Docker 服務健康 |
| G-2 設備可控 | T-010~T-014 | 至少 1 盞燈、1 個感測器在 UI 可見且可操作 |
| G-3 自動化運作 | T-020~T-023 | 離家自動化在測試中正確觸發 |
| G-4 監控上線 | T-030~T-032 | 能源圖表顯示 24h 歷史資料 |
| G-5 安全防護 | T-040~T-043 | 測試入侵偵測推播在 30 秒內送達 |
| G-6 遠端可用 | T-050~T-052 | 4G 環境下 UI 操作成功 |
| G-7 上線就緒 | T-060~T-063 | 覆蓋率 ≥ 80%，CI 綠燈，驗收測試全過 |

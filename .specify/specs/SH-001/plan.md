# SH-001 · Technical Plan

**Status:** Draft  
**Created:** 2026-05-19  
**Spec-kit phase:** Plan

---

## Technology Stack Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Core Platform | **Home Assistant** (latest stable) | 最成熟的開源智慧家庭平台，Python 原生，龐大整合生態 |
| Language | **Python 3.11+** | HA 官方語言；asyncio 原生支援設備 I/O |
| MQTT Broker | **Mosquitto 2.x** | 輕量、穩定、HA 官方推薦 |
| Zigbee Gateway | **Zigbee2MQTT + USB dongle** | 無需雲端、支援 1000+ 設備、MQTT 橋接 |
| Database | **MariaDB 10.11** (prod) / SQLite (dev) | HA Recorder 歷史資料；Alembic 管理 schema |
| Container | **Docker Compose** | 本地開發環境標準化 |
| Remote Access | **Nabu Casa** (首選) / WireGuard VPN (自架) | 安全、零配置；VPN 作為備援 |
| Notifications | **ntfy.sh** (self-hosted) + HA Notify | 支援 iOS/Android push、無需 Firebase |
| Voice (local) | **Wyoming Protocol + Whisper** | 完全本地、中文支援 |
| Testing | **pytest + pytest-homeassistant-custom-component** | 官方測試框架 |
| Lint/Format | **ruff + mypy** | 快速、嚴格 |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     使用者介面層                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Lovelace UI │  │ HA Companion │  │  Voice (Local) │  │
│  │ (Browser)   │  │ App iOS/Andr │  │  Whisper+Wake  │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
└─────────┼───────────────┼──────────────────┼────────────┘
          │ WebSocket/REST│                  │ Wyoming
┌─────────▼───────────────▼──────────────────▼────────────┐
│                  Home Assistant Core                      │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Event Bus │  │ State Machine│  │ Automation Engine │  │
│  └─────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│        │               │                   │              │
│  ┌─────▼───────────────▼───────────────────▼──────────┐  │
│  │              Integration Layer (Python)              │  │
│  │  custom_components/lights/  custom_components/       │  │
│  │  custom_components/climate/ security/  energy/       │  │
│  └──────────────────────┬──────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌──────▼───────┐
│  MQTT Broker │  │ Zigbee2MQTT  │  │  HTTP Devices │
│  (Mosquitto) │  │  (Zigbee USB)│  │  (REST/LAN)   │
└───────┬──────┘  └───────┬──────┘  └──────┬────────┘
        │                 │                 │
┌───────▼─────────────────▼─────────────────▼────────┐
│                    實體設備層                         │
│  燈光  插座  門鎖  感測器  攝影機  空調  窗簾  能源錶  │
└─────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Custom Components (`custom_components/`)

| Component | Domain | 功能 |
|---|---|---|
| `lights` | `light` | 燈光控制，支援亮度/色溫/RGB |
| `climate` | `climate` | 空調/暖氣，含排程節能 |
| `security` | `alarm_control_panel` | 安全模式、感測器整合 |
| `energy_monitor` | `sensor` | 用電量讀取、kWh 累計 |
| `presence` | `device_tracker` | 到家/離家偵測（Wi-Fi + BLE） |
| `scenes` | `scene` | 場景管理（含自訂場景 CRUD） |
| `notifications` | `notify` | 多通道推播（ntfy + mobile） |

每個 component 結構：
```
custom_components/<name>/
├── __init__.py          # async_setup_entry, async_unload_entry
├── manifest.json        # domain, version, dependencies
├── config_flow.py       # UI 設定流程
├── const.py             # 常數定義
├── coordinator.py       # DataUpdateCoordinator（若需輪詢）
└── <platform>.py        # sensor.py / switch.py / light.py …
```

### 2. Automation Scripts (`automations/`)

```
automations/
├── morning.py           # 早晨例程：窗簾、燈光、空調
├── away.py              # 離家：安全模式、關閉非必要設備
├── night.py             # 就寢：漸暗燈光、鎖門確認
├── arrival.py           # 回家：歡迎燈光、空調預冷/預熱
├── energy_alert.py      # 用電超標通知
└── security_alert.py    # 入侵偵測、攝影機快照推播
```

### 3. MQTT Topic Schema

```
smarthome/
├── <room>/
│   ├── <device>/
│   │   ├── state        # 裝置回報狀態（subscribe）
│   │   ├── command      # HA 下發指令（publish）
│   │   └── attributes   # 附加屬性 JSON
│   └── sensor/
│       └── <type>       # temperature, humidity, motion, door
└── system/
    ├── status           # broker 心跳
    └── log              # 系統事件
```

---

## Data Flow: Key Scenarios

### 燈光開啟
```
User taps UI
  → HA calls light.turn_on service
    → custom_components/lights async_turn_on()
      → mqtt.async_publish("smarthome/living/lamp/command", "ON")
        → Device receives MQTT command
          → Device publishes "smarthome/living/lamp/state" = "ON"
            → HA MQTT subscription updates entity state
              → UI reflects new state
```

### 人體感應自動開燈
```
PIR sensor → MQTT publish motion = "detected"
  → HA MQTT integration updates binary_sensor state
    → Automation trigger fires (state change)
      → automations/arrival.py evaluates conditions
        → Calls light.turn_on with brightness 80%
          → (same as above flow)
```

---

## Infrastructure: Docker Compose Services

```yaml
services:
  homeassistant:   # port 8123
  mosquitto:       # port 1883 (MQTT), 9001 (WebSocket)
  zigbee2mqtt:     # depends on mosquitto
  mariadb:         # port 3306
  ntfy:            # port 8080 (self-hosted push)
  wyoming-whisper: # port 10300 (local STT)
```

---

## Research References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Zigbee2MQTT supported devices](https://www.zigbee2mqtt.io/supported-devices/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
- [ntfy self-hosted push](https://ntfy.sh/docs/install/)
- [Wyoming Protocol for local voice](https://www.home-assistant.io/integrations/wyoming/)

---

## Open Decisions

| # | Question | Status |
|---|---|---|
| 1 | Nabu Casa 雲端 vs 自架 WireGuard？ | 待決定（建議先用 Nabu Casa） |
| 2 | Zigbee USB dongle 型號？ | 建議 SONOFF Zigbee 3.0 USB Dongle Plus |
| 3 | 攝影機整合：Frigate NVR vs HA 原生？ | 待決定（v2 考慮 Frigate） |

# SH-001 · Data Model

**Status:** Draft  
**Created:** 2026-05-19

---

## HA Recorder Schema (MariaDB)

Home Assistant 使用自有 Recorder 元件將實體狀態歷史寫入資料庫。以下為核心資料表（HA 自動管理，無需手動 migration）：

```sql
-- 實體狀態快照
states
  id            BIGINT PK
  entity_id     VARCHAR(255)     -- e.g. light.living_room_lamp
  state         VARCHAR(255)     -- e.g. "on", "23.5"
  attributes    LONGTEXT JSON
  last_changed  DATETIME(6)
  last_updated  DATETIME(6)
  created       DATETIME(6)

-- 事件日誌
events
  id            BIGINT PK
  event_type    VARCHAR(64)      -- e.g. "state_changed", "automation_triggered"
  event_data    LONGTEXT JSON
  origin        VARCHAR(32)
  time_fired    DATETIME(6)

-- 統計資料（能源監控）
statistics
  id            BIGINT PK
  metadata_id   BIGINT FK → statistics_meta.id
  start         DATETIME(6)
  mean          DOUBLE
  min           DOUBLE
  max           DOUBLE
  last_reset    DATETIME(6)
  state         DOUBLE
  sum           DOUBLE           -- 累計 kWh

statistics_meta
  id            BIGINT PK
  statistic_id  VARCHAR(255)     -- e.g. "sensor.energy_meter_total"
  source        VARCHAR(32)
  unit_of_measurement VARCHAR(255)
```

---

## Custom Tables (Alembic managed)

以下為本專案額外建立的資料表，由 `custom_components/` 透過 Alembic 管理 schema 版本：

```sql
-- 自訂場景
scenes (
  id          UUID          PK DEFAULT gen_random_uuid()
  name        VARCHAR(100)  NOT NULL
  icon        VARCHAR(50)
  room        VARCHAR(50)
  config      JSON          NOT NULL   -- { entity_id: { state, attributes } }
  created_by  VARCHAR(50)
  created_at  TIMESTAMP     DEFAULT NOW()
  updated_at  TIMESTAMP
)

-- 自動化規則（補充 HA YAML 的複雜規則）
automation_rules (
  id          UUID          PK
  name        VARCHAR(100)  NOT NULL
  enabled     BOOLEAN       DEFAULT TRUE
  trigger     JSON          NOT NULL   -- { type, entity_id, to, from, ... }
  conditions  JSON                     -- 可選條件陣列
  actions     JSON          NOT NULL   -- 動作陣列
  script_path VARCHAR(255)             -- 若指向 Python 腳本
  last_run    TIMESTAMP
  run_count   INTEGER       DEFAULT 0
)

-- 設備登記（補充 HA 設備登錄）
devices (
  id            UUID          PK
  ha_entity_id  VARCHAR(255)  UNIQUE NOT NULL
  room          VARCHAR(50)   NOT NULL
  device_type   VARCHAR(50)   NOT NULL   -- light, switch, sensor, lock, climate...
  protocol      VARCHAR(20)   NOT NULL   -- mqtt, zigbee, wifi
  mqtt_topic    VARCHAR(255)             -- NULL if non-MQTT
  manufacturer  VARCHAR(100)
  model         VARCHAR(100)
  registered_at TIMESTAMP     DEFAULT NOW()
)

-- 能源警報閾值
energy_alerts (
  id          UUID      PK
  entity_id   VARCHAR(255) NOT NULL
  threshold_w DECIMAL(8,2) NOT NULL     -- 功率警報閾值 (W)
  threshold_kwh DECIMAL(8,2)            -- 日用電量閾值 (kWh)
  notify_to   VARCHAR(255)              -- ntfy topic / mobile notify target
  enabled     BOOLEAN   DEFAULT TRUE
)

-- 安全白名單（免警報的已知裝置/人員）
security_whitelist (
  id          UUID      PK
  name        VARCHAR(100) NOT NULL
  type        VARCHAR(20)  NOT NULL     -- device_mac, person_entity
  identifier  VARCHAR(255) NOT NULL
  added_at    TIMESTAMP DEFAULT NOW()
)
```

---

## Entity Naming Convention

```
<domain>.<room>_<device>_<property>

Examples:
  light.living_room_ceiling_lamp
  switch.kitchen_coffee_machine
  sensor.bedroom_temperature
  sensor.bedroom_humidity
  binary_sensor.front_door_contact
  lock.front_door_lock
  climate.master_bedroom_ac
  sensor.living_room_energy_meter_power       -- 即時功率 (W)
  sensor.living_room_energy_meter_total       -- 累計 (kWh)
  alarm_control_panel.home_security
  device_tracker.person_owner
```

---

## MQTT Payload Schemas

### 設備狀態回報 (Device → HA)
```json
// smarthome/<room>/<device>/state
{
  "state": "on" | "off" | "<numeric>",
  "brightness": 0-255,
  "color_temp": 153-500,
  "rgb_color": [0-255, 0-255, 0-255]
}

// smarthome/<room>/sensor/<type>
{
  "value": 23.5,
  "unit": "°C",
  "battery": 85,
  "rssi": -65
}
```

### HA 下發指令 (HA → Device)
```json
// smarthome/<room>/<device>/command
{
  "command": "turn_on" | "turn_off" | "set",
  "brightness": 200,
  "color_temp": 300,
  "transition": 1.5
}
```

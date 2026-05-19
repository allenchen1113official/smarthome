# SH-001 · API Contracts

**Status:** Draft  
**Created:** 2026-05-19

> Home Assistant 提供完整的 REST API 與 WebSocket API。本文件記錄本專案使用的核心端點與自訂服務介面。

---

## Home Assistant REST API (built-in)

Base URL: `http://homeassistant.local:8123/api`  
Auth: `Authorization: Bearer <long-lived-access-token>`

### 取得實體狀態
```
GET /api/states/<entity_id>

Response 200:
{
  "entity_id": "light.living_room_ceiling_lamp",
  "state": "on",
  "attributes": {
    "brightness": 200,
    "color_temp": 300,
    "friendly_name": "客廳主燈"
  },
  "last_changed": "2026-05-19T10:30:00+08:00",
  "last_updated": "2026-05-19T10:30:01+08:00"
}
```

### 呼叫服務
```
POST /api/services/<domain>/<service>

Body:
{
  "entity_id": "light.living_room_ceiling_lamp",
  "brightness": 180,
  "transition": 2
}

Response 200: [ { ...updated state... } ]
```

### 觸發自動化
```
POST /api/services/automation/trigger
Body: { "entity_id": "automation.morning_routine" }
```

---

## Home Assistant WebSocket API (built-in)

URL: `ws://homeassistant.local:8123/api/websocket`

### 訂閱狀態變更
```json
→ { "id": 1, "type": "subscribe_events", "event_type": "state_changed" }
← { "id": 1, "type": "result", "success": true }
← {
    "id": 1,
    "type": "event",
    "event": {
      "event_type": "state_changed",
      "data": {
        "entity_id": "sensor.bedroom_temperature",
        "old_state": { "state": "22.1" },
        "new_state": { "state": "22.8" }
      }
    }
  }
```

---

## 自訂服務介面 (Custom Components)

### `scenes.activate`
啟動預設或自訂場景。

```
POST /api/services/scenes/activate
{
  "scene_id": "<uuid>",          // 自訂場景 UUID，或
  "scene_name": "movie_mode"     // 預設場景名稱
}
```

預設場景名稱：`morning` | `away` | `movie` | `dining` | `night` | `welcome`

---

### `security.set_mode`
切換安全模式。

```
POST /api/services/security/set_mode
{
  "mode": "armed_away" | "armed_home" | "disarmed",
  "code": "1234"                // 解除警報時需要
}
```

---

### `energy_monitor.get_report`
取得用電報告（自訂 Python 服務，回傳非 HA 標準格式）。

```
POST /api/services/energy_monitor/get_report
{
  "entity_id": "sensor.living_room_energy_meter_total",
  "period": "day" | "week" | "month",
  "start_date": "2026-05-01"     // 選填，預設為今日
}

Response (透過 hass.bus.async_fire event 回傳):
event_type: energy_monitor_report
event_data: {
  "entity_id": "...",
  "period": "week",
  "total_kwh": 45.7,
  "daily_breakdown": [
    { "date": "2026-05-13", "kwh": 6.2 },
    ...
  ],
  "peak_power_w": 3200,
  "average_power_w": 270
}
```

---

### `notifications.send`
多通道推播（ntfy + mobile）。

```
POST /api/services/notifications/send
{
  "title": "安全警報",
  "message": "前門感測器觸發",
  "priority": "high" | "normal" | "low",
  "image_url": "http://...",      // 選填：攝影機快照
  "targets": ["mobile_app_iphone", "ntfy_home"]   // 選填，預設全部
}
```

---

## MQTT 服務介面

由 `custom_components/` 透過 `mqtt.async_publish` 呼叫，非直接 HTTP。

| Topic | Direction | Schema |
|---|---|---|
| `smarthome/<room>/<device>/command` | HA → Device | `{ command, ...params }` |
| `smarthome/<room>/<device>/state` | Device → HA | `{ state, ...attributes }` |
| `smarthome/<room>/sensor/<type>` | Device → HA | `{ value, unit, battery }` |
| `smarthome/system/status` | Broker → All | `{ status: "online"\|"offline" }` |

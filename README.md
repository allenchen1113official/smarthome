# smarthome

以 **Home Assistant** 為核心、**Python** 驅動的智慧家庭系統。

## 快速開始

```bash
cp .env.example .env          # 填入設定值
docker compose -f docker/docker-compose.dev.yml up -d
# Home Assistant: http://localhost:8123
```

## 文件

- [CLAUDE.md](./CLAUDE.md) — 開發指引與架構說明
- [.specify/memory/constitution.md](./.specify/memory/constitution.md) — 專案治理原則
- [.specify/specs/SH-001/spec.md](./.specify/specs/SH-001/spec.md) — 功能規格
- [.specify/specs/SH-001/plan.md](./.specify/specs/SH-001/plan.md) — 技術架構計畫
- [.specify/specs/SH-001/tasks.md](./.specify/specs/SH-001/tasks.md) — 實作任務清單
- [.specify/specs/SH-001/data-model.md](./.specify/specs/SH-001/data-model.md) — 資料模型
- [.specify/specs/SH-001/contracts/rest-api.md](./.specify/specs/SH-001/contracts/rest-api.md) — API 規格

## 技術棧

Home Assistant · Python 3.11+ · MQTT (Mosquitto) · Zigbee2MQTT · MariaDB · Docker

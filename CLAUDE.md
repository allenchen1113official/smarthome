# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Smart Home** system built on **Home Assistant** with **Python** custom integrations and automations. The project follows **Spec-Driven Development** (spec-kit methodology) — all feature planning lives under `.specify/` before implementation begins.

## Tech Stack

| Layer | Technology |
|---|---|
| Core Platform | Home Assistant (Python 3.11+) |
| Custom Components | Python (asyncio, aiohttp) |
| Device Protocol | MQTT (Mosquitto broker) |
| Automation | Python scripts + YAML |
| Database | MariaDB (production) / SQLite (dev) |
| Message Bus | Home Assistant Event Bus + MQTT |
| API | REST + WebSocket (HA built-in) |
| Secrets | `.env` + `secrets.yaml` (never committed) |

## Repository Layout

```
.specify/              # Spec-kit planning artifacts (specs before code)
│ ├── memory/          # constitution.md — project governance
│ └── specs/SH-XXX/   # per-feature: spec, plan, tasks, data-model, contracts/
custom_components/     # Python HA integrations (one folder per integration)
automations/           # Python/YAML automation scripts
scripts/               # Utility and setup scripts
tests/                 # pytest test suite mirroring custom_components/
config/                # Home Assistant YAML configuration
docker/                # Docker Compose for local dev stack
```

## Development Commands

### Environment Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/secrets.yaml.example config/secrets.yaml   # fill in your values
```

### Running Home Assistant (dev)
```bash
docker compose -f docker/docker-compose.dev.yml up -d   # HA + Mosquitto + MariaDB
hass --config config/ --debug                            # or run HA directly
```

### Tests
```bash
pytest                                    # full suite
pytest tests/custom_components/lights/   # single component
pytest -k "test_automation"              # filter by name
pytest --cov=custom_components --cov-report=term-missing
```

### Lint & Type Check
```bash
ruff check .
ruff format .
mypy custom_components/
```

### MQTT Debugging
```bash
mosquitto_sub -h localhost -t '#' -v     # watch all MQTT topics
```

## Architecture: How It Fits Together

### Home Assistant Core + Custom Components
Custom integrations live in `custom_components/<name>/`. Each must have `manifest.json`, `__init__.py`, `config_flow.py` (for UI setup), and at least one platform file (e.g. `sensor.py`, `switch.py`). HA discovers them at startup via the manifest.

### Automation Flow
```
Physical Device → MQTT → HA Event Bus → Automation Rule → Action (service call)
```
Automations can be:
- **YAML** (`config/automations.yaml`) — declarative, simple triggers/actions
- **Python scripts** (`automations/`) — complex logic using HA's Python scripting API (`hass` object injected at runtime)

### State Machine
All device states are managed by HA's central state machine (`hass.states`). Custom components write states; automations and the UI read them. Never store mutable state outside the HA state machine.

### MQTT Integration Pattern
Devices publish to `smarthome/<room>/<device>/<property>` (e.g. `smarthome/living_room/lamp/state`). Custom MQTT components subscribe via `mqtt.async_subscribe()` and translate payloads into HA entity states.

### Secrets & Config
- `config/secrets.yaml` — API keys, passwords (git-ignored)
- `config/configuration.yaml` — main HA config (committed, no secrets)
- `.env` — used by Docker Compose for service credentials (git-ignored)

## Spec-Driven Development Workflow

All features follow the spec-kit phases before any code is written:

1. **Constitution** — `.specify/memory/constitution.md` (project-wide, one-time)
2. **Spec** — `.specify/specs/SH-XXX/spec.md` — what & why (user stories, acceptance criteria)
3. **Plan** — `.specify/specs/SH-XXX/plan.md` — how (architecture, stack decisions)
4. **Tasks** — `.specify/specs/SH-XXX/tasks.md` — ordered task list with dependencies
5. **Implement** — write code, then commit

Spec IDs follow `SH-XXX` (e.g. `SH-001` = Core Platform Setup).

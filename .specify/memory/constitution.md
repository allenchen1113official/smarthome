# Smart Home Project Constitution

> Governing principles for all development decisions in this repository.

## 1. Core Philosophy

- **Home Assistant First** — Leverage HA's built-in capabilities before building custom solutions. Custom components exist only when HA's existing integrations cannot cover the requirement.
- **Async by Default** — All I/O in custom components must use Python's `asyncio`. Blocking calls in the event loop are forbidden.
- **State Lives in HA** — The Home Assistant state machine is the single source of truth. No component stores mutable state in memory or a separate cache.
- **MQTT as Device Layer** — All physical devices communicate exclusively over MQTT. Direct TCP/HTTP polling of devices is a last resort and must be justified in the spec.

## 2. Code Quality Standards

- **Python version:** 3.11+ with full type hints (`mypy --strict` must pass).
- **Formatting:** `ruff format` (line length 88).
- **Linting:** `ruff check` with no ignored rules unless explicitly justified in a comment.
- **Test coverage:** Minimum 80% for `custom_components/`. All public service calls must have at least one integration test using `pytest-homeassistant-custom-component`.
- **No global state** outside `hass.data[DOMAIN]` storage pattern.

## 3. Security Principles

- Secrets (tokens, passwords, API keys) are **never hardcoded** — they go in `config/secrets.yaml` (git-ignored) or environment variables.
- All external API communication uses TLS. Self-signed certs are acceptable in dev only.
- MQTT topics follow least-privilege ACL: each device publishes only to its own subtopic.
- User-facing input that reaches service calls must be validated with `voluptuous` schemas.

## 4. Architecture Constraints

- One Python package per `custom_components/<name>/` directory.
- Automations with more than three conditions or two action branches must be Python scripts, not YAML.
- Database migrations use Alembic. Schema changes without a migration are rejected.
- Docker Compose is the only supported local dev environment.

## 5. UX & Dashboard Consistency

- Room-based navigation: every UI card is scoped to a room, then a device type.
- Entity naming convention: `<domain>.<room>_<device>_<property>` (e.g. `sensor.living_room_temperature`).
- Automations must provide feedback (notification or state change) within 2 seconds of trigger.

## 6. Performance Expectations

- Custom component setup (`async_setup_entry`) must complete in under 5 seconds.
- MQTT message round-trip (publish → state update in HA) target: < 500 ms on LAN.
- Dashboard initial load: < 3 seconds on a Raspberry Pi 4.

## 7. Dependency Policy

- Prefer libraries already bundled with Home Assistant (`aiohttp`, `voluptuous`, `attrs`).
- Any new `pip` dependency requires justification in `plan.md` and a pinned version in `requirements.txt`.
- Do not pin HA itself — always target the latest stable release.

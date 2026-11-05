<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0 (2026-11-05, 台北)
Modified principles:
  - I. Local-First Processing — 明訂雲端 LLM（Grok）為選配、預設關閉、僅送文字
  - III. Privacy by Design — 新增「金鑰不進 GitHub」與推送前掃描
Added principles:
  - VI. Energy & Carbon Minimization（節能省碳最高目標；單一 AI 助理決策）
Previous: [TEMPLATE] → 1.0.0 (initial ratification)
Added sections (1.0.0):
  - Core Principles (5 principles)
  - Smart Home Technology Stack
  - Automation Design Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (no principle-specific stale references)
  - .specify/templates/spec-template.md ✅ (no principle-specific stale references)
  - .specify/templates/tasks-template.md ✅ (no principle-specific stale references)
Deferred TODOs: none
-->

# Allen & Ann SmartHome Constitution

## Core Principles

### I. Local-First Processing

All automation logic, voice recognition, and AI inference MUST run on-premises hardware by default.
Cloud services MAY be used only for data that is non-sensitive and where a local equivalent is
unavailable or significantly inferior. The OpenClaw local AI voice stack is the canonical reference
implementation of this principle.

- Home Assistant instance MUST be self-hosted on a local server/NAS.
- Voice assistant pipelines MUST use local STT/TTS engines (e.g., Whisper, Piper).
- Automations MUST NOT depend on third-party cloud APIs as a single point of failure.
- The Hermes LLM provider MUST default to the local Ollama model. A cloud LLM (e.g., xAI Grok) is
  optional, disabled by default, MUST be enabled explicitly by a resident in the admin UI, and MUST
  receive text context only — never audio, recordings, presence history, or energy data.
- Presence, sleep state, energy usage and voice transcripts MUST be stored only in Home Assistant and
  the Hermes local database; messaging bots (LINE/Telegram) relay commands and replies only.

### II. Reliability & Graceful Degradation

Every automation MUST define a safe fallback state for when devices, integrations, or network
segments are unavailable. The home MUST remain livable and safe even if the automation platform fails.

- Critical lighting, climate, and security automations MUST include manual override paths.
- Automations MUST be tested against device-offline scenarios before production deployment.
- Any automation touching security (locks, cameras, alarms) MUST have a documented recovery procedure.

### III. Privacy by Design

Resident data — voice recordings, presence patterns, energy usage, and camera feeds — MUST NOT leave
the home network unless explicitly consented to and documented in the feature spec.

- No cloud logging of voice queries is permitted by default.
- External integrations (e.g., weather APIs) MUST use anonymous or minimal-data endpoints.
- All credentials and API tokens MUST be stored in Home Assistant Secrets (`secrets.yaml`), the
  BlueMagpie `.env`, or launchd environment variables — never hardcoded in configuration files,
  automation YAML, documentation, or dashboards.
- No credential, key, or token MAY be committed to this GitHub repository. `bluemagpie/.env`,
  `bluemagpie/config/`, `bluemagpie/data/` and `bluemagpie/backups/` are git-ignored and MUST NOT be
  force-added. `tools/check_secrets.py` MUST pass (0 findings) before every push
  (`git config core.hooksPath .githooks` enables the pre-push hook). Documentation examples MUST use
  obvious placeholders (`xai-...`, `<token>`).

### IV. Two-Resident Usability

All interfaces, automations, and dashboards MUST be usable by both Allen and Ann without
requiring technical knowledge. Complexity MUST be hidden behind intuitive UX.

- Lovelace dashboards MUST be reviewed with both residents before finalizing.
- Automation trigger conditions MUST account for both residents' schedules and preferences.
- Every automation that changes a resident's environment MUST expose a one-tap override in the UI.
- Onboarding documentation MUST be written in Traditional Chinese (繁體中文) for resident reference.

### V. Documentation-Before-Deployment

No automation scenario, device integration, or configuration change MAY be deployed to the live
Home Assistant instance without a corresponding specification entry under `specs/`.

- Each of the 30 automation scenarios MUST have a spec.md defining triggers, conditions, and actions.
- Device wiring diagrams and network topology MUST be kept current in the project repository.
- After any deployment, the relevant spec MUST be updated to reflect the as-built state.

### VI. Energy & Carbon Minimization

Energy saving and carbon reduction is the highest-priority design goal for every automation scenario.
Exactly ONE AI assistant — the Hermes energy manager (`hermes/energy.py`) — makes all energy
decisions, so residents can relax or tighten saving for the whole home with a single instruction.

- Every plan that changes climate, lighting, or appliances MUST pass through the Hermes energy guard
  (`energy.clamp`) before execution. The guard MAY only tighten (raise cooling set-points, cap
  brightness, prefer dehumidify/fan), never loosen; safety scenarios (locks, alarms, SOS) are exempt.
- The default energy mode MUST be `eco` (cooling set-point ≥ 27 °C, lights ≤ 70 %, ≤ 40 % in
  daylight, idle-off after 20 min). `normal`/`comfort` MUST revert to `eco` automatically by timer.
- Home Assistant MUST measure whole-home and per-appliance energy locally and provide only
  measurement and reflex actions (idle-off, window-open-off, peak-tariff notice); it MUST NOT hold
  competing energy policies.
- Every scenario spec MUST state its behaviour in `eco` mode (docs/SOP/13 §13.6) in the Constitution
  Check before a plan is opened.
- Residents MUST receive a daily energy/carbon report; the Taipower carbon factor
  (`input_number.energy_carbon_factor`) MUST be reviewed yearly.

## Smart Home Technology Stack

**Core Platform**: Home Assistant (self-hosted, latest stable)

**Voice Assistant**: OpenClaw local AI voice stack — Whisper (STT), local LLM (intent), Piper (TTS)

**Energy**: Shelly EM whole-home metering + Aqara metering plugs (local); Hermes energy manager as the single decision point

**Hardware Layer**: Zigbee/Z-Wave for sensors and switches; MQTT broker (Mosquitto) as the message bus

**Networking**: Dedicated IoT VLAN isolated from the main resident network; Wireguard VPN for
remote access

**Storage & Backup**: Weekly automated snapshot of Home Assistant config to network-attached storage;
configuration files version-controlled in this Git repository

**Constraints**:
- Automations MUST be expressed as declarative YAML (Home Assistant automation format) or
  Node-RED flows — no opaque scripts that cannot be reviewed.
- Python scripts used in automations MUST be stored under `config/python_scripts/` and documented.

## Automation Design Workflow

1. **Specify** — Create `specs/[###-scenario-name]/spec.md` using `/speckit-specify`.
2. **Clarify** — Resolve ambiguities with `/speckit-clarify` before any YAML is written.
3. **Plan** — Generate implementation plan with `/speckit-plan`, including device dependencies and
   fallback states.
4. **Review** — Both residents confirm the automation behavior matches their intent.
5. **Implement** — Deploy to a Home Assistant test environment (separate instance or staging area)
   first; validate all acceptance scenarios.
6. **Deploy** — Merge to production HA instance; commit updated config to this repo.
7. **Document** — Update spec to as-built state; photograph any physical wiring changes.

## Governance

- This constitution supersedes all informal conventions or undocumented practices.
- Amendments MUST increment `CONSTITUTION_VERSION` per semantic versioning and record the change
  in the Sync Impact Report comment at the top of this file.
- Any new automation scenario added to the 30-scenario roadmap MUST be reviewed against all six
  Core Principles before a spec is opened.
- Compliance review SHOULD occur at each `/speckit-plan` gate (Constitution Check section).
- The primary runtime guidance document is `CLAUDE.md` at the project root; it MUST reference the
  current constitution version.

**Version**: 1.1.0 | **Ratified**: 2026-05-25 | **Last Amended**: 2026-11-05

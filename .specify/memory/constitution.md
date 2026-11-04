<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: N/A (first version)
Added sections:
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
- All credentials and API tokens MUST be stored in Home Assistant Secrets (`secrets.yaml`), never
  hardcoded in configuration files or automation YAML.

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

## Smart Home Technology Stack

**Core Platform**: Home Assistant (self-hosted, latest stable)

**Voice Assistant**: OpenClaw local AI voice stack — Whisper (STT), local LLM (intent), Piper (TTS)

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
- Any new automation scenario added to the 30-scenario roadmap MUST be reviewed against all five
  Core Principles before a spec is opened.
- Compliance review SHOULD occur at each `/speckit-plan` gate (Constitution Check section).
- The primary runtime guidance document is `CLAUDE.md` at the project root; it MUST reference the
  current constitution version.

**Version**: 1.0.0 | **Ratified**: 2026-05-25 | **Last Amended**: 2026-05-25

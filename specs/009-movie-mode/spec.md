# Feature Specification: 電影模式 (Movie Mode)

**Feature Branch**: `009-movie-mode`

**Created**: 2026-05-26

**Status**: Draft

**Input**: User description: "電影模式"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 一鍵啟動電影院環境 One-Tap Cinema Environment Activation (Priority: P1)

Either resident can activate Movie Mode with a single tap on the dashboard or a voice command
— instantly transforming the living room into a cinema-like environment: lights dim to a warm
low level, window blinds close, and non-essential home notifications are silenced — so Allen
and Ann can start watching without interrupting the mood to adjust multiple devices one by one.

**Why this priority**: The entire value of Movie Mode is the seamless single-action experience.
If residents have to adjust lights, blinds, and AC separately, they would simply do it
manually. One-tap scene activation is what makes this a smart home feature.

**Independent Test**: Tap the Movie Mode button on the dashboard. Within 10 seconds confirm:
(a) living room lights dim to ≤ 15% warm brightness, (b) window blinds close fully, (c) a
"電影模式已啟動" notification confirms activation, and (d) no further smart home automation
notifications arrive during the session.

**Acceptance Scenarios**:

1. **Given** a resident taps the Movie Mode button or says the configured voice command,
   **When** activation completes, **Then** within 10 seconds: living room lights dim to the
   configured movie brightness (default ≤ 15%), window blinds close fully, and non-essential
   home automation notifications are silenced.
2. **Given** Movie Mode is activating and a device (light or blind) is unresponsive, **When**
   the sequence runs, **Then** all reachable devices still execute correctly, the mode is
   considered active, and a brief note lists any devices that could not be reached.
3. **Given** Movie Mode is already active, **When** a resident attempts to activate it again,
   **Then** no duplicate actions occur and the dashboard confirms the mode is already on.

---

### User Story 2 - 電影結束自動恢復環境 Auto-Restore Environment After Movie (Priority: P2)

When a resident ends Movie Mode — by pressing "結束電影模式" on the dashboard, issuing a voice
command, or after a configured maximum session duration — the home automatically restores the
environment to its pre-movie state: lights return to their previous brightness, blinds re-open
if it is still daytime, and home notifications resume — so neither resident has to manually
undo every change the mode made.

**Why this priority**: Without automatic restoration, Movie Mode creates a chore: every time
a movie ends, residents must manually re-open blinds and restore lights. Auto-restore is what
makes the feature feel complete rather than one-directional.

**Independent Test**: Activate Movie Mode, then tap "結束電影模式". Within 15 seconds confirm
lights return to their pre-movie brightness, blinds open (if daytime), and the next home
automation notification arrives normally.

**Acceptance Scenarios**:

1. **Given** Movie Mode is active, **When** a resident taps "結束電影模式" or issues the exit
   voice command, **Then** within 15 seconds lights return to their pre-movie brightness and
   colour temperature, blinds return to their pre-movie position (open if previously open),
   and home notifications resume.
2. **Given** Movie Mode has been active for the configured maximum session duration (default:
   4 hours), **When** the duration expires, **Then** the mode automatically ends, the
   environment restores, and both residents receive a notification that the session has ended.
3. **Given** Movie Mode ends while it is night-time (post-sunset), **When** restoration runs,
   **Then** blinds are NOT forced open (they remain in whatever position they were before
   Movie Mode started, which was likely closed at night).
4. **Given** a device that was changed by Movie Mode is now offline when restoration runs,
   **When** the restore sequence executes, **Then** all reachable devices restore correctly
   and a notification lists any that could not be reached.

---

### User Story 3 - 個人化電影場景設定 Personalised Movie Scene Configuration (Priority: P3)

Either resident can customise exactly what Movie Mode does — which lights dim and to what
level, whether blinds close, whether the AC adjusts to a "cinema comfort" temperature, and
which notification categories are silenced — so the mode reflects their personal viewing
preferences rather than a fixed preset.

**Why this priority**: A fixed preset suits casual use but quickly feels wrong for residents
with different preferences (e.g., Allen prefers complete darkness while Ann wants a dim floor
lamp on). Customisation makes the mode genuinely personalised.

**Independent Test**: Configure Movie Mode to keep one floor lamp at 30% and not close the
kitchen blinds. Activate the mode and confirm the floor lamp stays at 30% and kitchen blinds
remain open while the living room blinds close.

**Acceptance Scenarios**:

1. **Given** a resident opens Movie Mode settings on the dashboard, **When** they adjust
   which lights are included and their target brightness, **Then** the next Movie Mode
   activation uses the updated configuration.
2. **Given** a resident enables the AC adjustment option in Movie Mode settings, **When**
   Movie Mode activates, **Then** the AC sets to the configured cinema comfort temperature
   (default: 25°C) in addition to the lighting and blind actions.
3. **Given** a resident configures which notification categories are silenced, **When** Movie
   Mode is active, **Then** only the configured categories are suppressed; critical alerts
   (security, smoke, water leak) are NEVER silenced regardless of configuration.
4. **Given** the household has a shared Movie Mode config, **When** either resident modifies
   it, **Then** the change applies to the shared household Movie Mode; per-resident profiles
   are out of scope for v1.

---

### Edge Cases

- What if Movie Mode is activated while the bedtime automation countdown (spec 006) is also
  running? (Movie Mode cancels any pending bedtime automation for the session duration; when
  Movie Mode ends, bedtime automation resumes its normal schedule.)
- What if a security alert (intruder, smoke, water) fires during Movie Mode? (Security alerts
  are NEVER suppressed; they trigger immediately with full lights-on and notifications
  regardless of Movie Mode state.)
- What if the blinds are already closed before Movie Mode activates (e.g., evening)? (The
  system records the pre-movie state as "closed" and does not reopen them on restore.)
- What if the resident pauses the movie and wants temporary normal lighting without ending
  the mode? (Out of scope for v1; residents can manually adjust lights and Movie Mode will
  restore them when the mode ends.)
- What if Movie Mode is active when a presence-based automation fires (e.g., second resident
  arrives home and welcome lights trigger)? (Welcome lights from spec 005 are suppressed
  during Movie Mode to avoid disrupting the viewing environment; the arriving resident
  receives a "電影模式進行中" notification instead.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST activate Movie Mode from a single dashboard tap or configured
  voice command, completing all device actions within 10 seconds.
- **FR-002**: Activation MUST dim or turn off all configured living area lights to the
  resident-configured movie brightness level (default: ≤ 15% warm white).
- **FR-003**: Activation MUST close the configured window blinds fully.
- **FR-004**: Activation MUST silence non-essential home automation notifications for the
  duration of the session; critical safety alerts (security, smoke, water) MUST always fire.
- **FR-005**: The system MUST record the pre-movie state of all affected devices before
  changing them, so restoration can return each device to its exact prior state.
- **FR-006**: The system MUST restore all affected devices to their pre-movie state when Movie
  Mode ends, within 15 seconds of the exit trigger.
- **FR-007**: The system MUST automatically end Movie Mode and restore the environment after
  the configurable maximum session duration (default: 4 hours).
- **FR-008**: Blinds MUST restore to their pre-movie position on exit; they MUST NOT be
  forced open if they were closed before the mode started or if it is currently night-time.
- **FR-009**: Residents MUST be able to customise the Movie Mode scene configuration from the
  dashboard — including which lights, target brightness, blind control, AC temperature, and
  notification suppression categories.
- **FR-010**: During Movie Mode, the welcome arrival lighting automation (spec 005) MUST be
  suppressed; arriving residents receive a notification that Movie Mode is active instead.
- **FR-011**: If any device fails to respond during activation or restoration, all reachable
  devices MUST still complete their actions and the resident MUST be notified of any failures.

### Key Entities

- **MovieModeConfig**: Household scene configuration — included light list with target
  brightness per light, blind list, AC cinema temperature (optional), notification suppression
  categories, maximum session duration.
- **MovieModeSession**: A single Movie Mode session — start timestamp, activation source
  (dashboard/voice), pre-movie device snapshot (light states, blind positions), end timestamp,
  end trigger (manual/timeout), restoration outcome.
- **DeviceSnapshot**: Pre-movie state of a single device — device identifier, type, state
  (brightness %, blind position %, AC setpoint) captured at activation time, used for
  restoration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Movie Mode activation completes all device actions within 10 seconds on 95%
  of activations.
- **SC-002**: Movie Mode restoration returns all devices to their pre-movie state within 15
  seconds of exit on 95% of sessions.
- **SC-003**: Zero security or safety alerts are suppressed during Movie Mode, verified across
  all test scenarios.
- **SC-004**: Both residents report after 2 weeks that activating Movie Mode requires no
  additional manual device adjustments on at least 9 out of 10 sessions.
- **SC-005**: Both residents report that ending Movie Mode restores the home to a comfortable
  state without any manual corrections needed on at least 9 out of 10 sessions.

## Assumptions

- Movie Mode is a household-shared scene in v1; a single configuration applies to both
  residents. Per-resident Movie Mode profiles are a future enhancement.
- The "pre-movie state" snapshot captures only the devices that Movie Mode will change.
  Devices not included in the Movie Mode configuration are not recorded or affected.
- "Critical safety alerts" that are never suppressed include: door/window security sensor
  alerts, smoke detector, water leak detector, and any alert tagged as priority "urgent"
  in the home automation platform.
- AC adjustment during Movie Mode is optional and off by default; residents opt in via
  settings. When enabled, it creates a short-duration override that ends when Movie Mode ends.
- This feature interacts with spec 006 (bedtime lights-off) and spec 005 (arrive-home lights):
  Movie Mode suppresses both for the session duration. The exact interaction precedence is
  confirmed at planning time.
- "Window blinds" refers to motorised blinds already integrated with the platform. If no
  motorised blinds are available, the blind-related steps are skipped automatically.
- The voice command phrase for activation and exit is configured by the resident; OpenClaw
  handles voice recognition per the constitution.

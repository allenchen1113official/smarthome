# Feature Specification: 離家自動關燈 (Auto Turn Off Lights When Leaving Home)

**Feature Branch**: `004-leave-home-lights-off`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "離家自動關燈"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 全員離家自動熄燈 All Residents Left — Auto Lights Off (Priority: P1)

When the last resident leaves the home, all lights in the house turn off automatically within
2 minutes, so Allen and Ann never waste electricity or worry about lights being left on while
nobody is home.

**Why this priority**: This is the core daily-use scenario and the direct value of the feature.
It covers the majority of real-world use cases and requires no interaction from residents.

**Independent Test**: With both residents at home, have the last resident leave. Confirm that
all lights turn off within 2 minutes of the home detecting the last resident's departure, and
that a confirmation notification is sent.

**Acceptance Scenarios**:

1. **Given** both residents are home and all lights are on, **When** the last resident leaves
   and the home detects no occupants, **Then** all lights turn off within 2 minutes and both
   residents receive a push notification confirming "已離家，燈光已關閉".
2. **Given** the last resident has left and lights have been turned off, **When** either
   resident returns home within the same day, **Then** the lights do NOT automatically turn
   back on (re-entry lighting is a separate feature outside this spec's scope).
3. **Given** the system detects departure but a light fails to turn off (device unresponsive),
   **Then** the notification includes the names of any lights that could not be turned off,
   so the resident is aware.

---

### User Story 2 - 單人外出不影響在家者 One Resident Leaves — No Change (Priority: P2)

When only one resident leaves the home while the other remains, all lights stay exactly as
they are, so the resident at home experiences no unexpected changes to their environment.

**Why this priority**: Without per-resident presence tracking, the automation would incorrectly
turn off lights whenever either resident goes out. Correct two-person presence handling is
essential to avoid false triggers.

**Independent Test**: With both residents home and lights on, have one resident leave while
the other stays. Verify that no lights change state after the departure.

**Acceptance Scenarios**:

1. **Given** both residents are home, **When** Allen leaves but Ann remains, **Then** no
   lights change state.
2. **Given** only Ann is home and lights are on, **When** Allen (who was already out) comes
   and goes again, **Then** no lights change state while Ann remains inside.
3. **Given** Ann is the last resident and leaves, **When** the home detects zero occupants,
   **Then** the lights-off sequence triggers as in User Story 1.

---

### User Story 3 - 離家前緩衝提醒 Departure Buffer with Cancellation (Priority: P3)

When the system detects the last resident has left, it waits a configurable buffer period
(default 2 minutes) before turning off the lights, and sends a pre-action notification
so the resident can cancel if they stepped out briefly (e.g., collecting mail, taking out
rubbish) and are about to return.

**Why this priority**: Immediate light-off on departure could be disruptive for brief exits.
A short buffer plus a cancellation option prevents false positives without reducing the
feature's energy-saving value for genuine departures.

**Independent Test**: Configure a 2-minute buffer. Have the last resident leave, then return
within 90 seconds. Confirm the lights were NOT turned off.

**Acceptance Scenarios**:

1. **Given** the last resident leaves and the buffer period begins, **When** the resident
   returns before the buffer expires, **Then** the lights-off action is cancelled and no
   notification is sent.
2. **Given** the pre-action notification is sent during the buffer period, **When** the
   resident taps "取消" (Cancel) on the notification, **Then** the lights-off action is
   cancelled for this departure event.
3. **Given** the buffer period expires with no return and no cancellation, **When** the
   system executes the lights-off action, **Then** all lights turn off and a confirmation
   notification is sent as in User Story 1.

---

### Edge Cases

- What if presence detection is uncertain (e.g., phone GPS still shows home after departure)?
  (A 2-minute buffer mitigates this; the system uses the configured buffer before acting.)
- What if a resident's phone is left at home while the resident is out? (Assumed that phone
  presence is used as a proxy for resident presence; residents MUST carry their phones for
  the automation to work correctly — documented in Assumptions.)
- What if all smart lights are offline when departure is detected? (Notification is sent
  noting all lights were unreachable; no action is taken for offline devices.)
- What if a guest is at home alone (no registered resident present)? (Guest presence is not
  tracked; if both residents' phones are absent, the system treats the home as unoccupied.
  Guest handling is out of scope for v1.)
- What if a resident disables the automation via the dashboard? (No automatic action occurs
  until re-enabled; this is an explicit override.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect when the last registered resident has left the home and
  trigger the lights-off sequence only when zero registered residents are present.
- **FR-002**: The lights-off sequence MUST turn off all lights in the home within 2 minutes
  of the buffer period expiring.
- **FR-003**: The system MUST NOT trigger the lights-off sequence while at least one
  registered resident remains at home.
- **FR-004**: The system MUST send a push notification to both residents when the lights-off
  action completes, listing any lights that could not be turned off.
- **FR-005**: The system MUST support a configurable departure buffer period (default: 2
  minutes) before executing the lights-off action, during which an automatic cancellation
  occurs if a resident returns.
- **FR-006**: During the buffer period, the system MUST send a pre-action notification to
  both residents allowing them to cancel the lights-off action with a single tap.
- **FR-007**: Either resident MUST be able to enable, disable, or configure the buffer
  duration from the dashboard without technical assistance.
- **FR-008**: If any light fails to turn off (device unresponsive), the system MUST continue
  turning off all reachable lights and include the names of failed lights in the notification.
- **FR-009**: The automation MUST operate correctly in all cases: both residents out, one
  resident out, one resident returns during buffer, and manual cancellation.

### Key Entities

- **ResidentPresence**: Tracks the at-home/away status of each registered resident — resident
  identity, current status (home/away), last-seen timestamp, detection method.
- **OccupancyState**: The household-level occupancy derived from all resident presences —
  occupied/unoccupied, resident count, timestamp of last change.
- **LightsOffConfig**: Automation configuration — enabled/disabled, buffer duration (minutes),
  notification preferences.
- **LightsOffEvent**: A log of each automation execution — trigger timestamp, buffer expiry
  time, action taken (executed/cancelled), lights turned off, lights failed, cancellation
  reason if applicable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lights turn off within 2 minutes of the buffer expiry on 95% of genuine
  whole-household departures over a 2-week measurement period.
- **SC-002**: Zero false triggers occur when only one resident leaves while the other remains
  home, measured over 2 weeks of normal use.
- **SC-003**: Both residents receive the departure confirmation notification within 30 seconds
  of the lights-off action completing.
- **SC-004**: When a resident returns during the buffer period, the lights-off action is
  cancelled 100% of the time (no false light-offs on brief exits).
- **SC-005**: Both residents report after 2 weeks that they have not once returned home to
  unexpectedly dark conditions caused by this automation.

## Assumptions

- Resident presence is determined by the location/presence detection already configured in
  the home automation platform (e.g., phone GPS geofencing or device tracker). The specific
  detection mechanism is decided at planning time; this spec requires only that the platform
  can reliably distinguish "resident at home" from "resident away".
- Registered residents are Allen and Ann only; guest or visitor presence is not tracked and
  does not affect the automation.
- Residents are assumed to carry their phones when leaving the home; phone absence is treated
  as resident absence. If a resident leaves their phone at home, the automation will not fire
  (this is acceptable behaviour, documented here so residents understand the limitation).
- "All lights" means all smart lights registered in the home automation platform. Non-smart
  (dumb) lights are not affected and are out of scope.
- Re-entry lighting (auto turn-on when arriving home) is a separate feature outside this
  spec's scope.
- The buffer period default is 2 minutes; residents may adjust this between 0 and 10 minutes
  from the dashboard.
- This automation applies at all times of day and all days of the week by default; a
  time-window restriction (e.g., only active at night) is a future enhancement.

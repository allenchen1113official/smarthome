# Feature Specification: 空調自動調節 (Smart AC Control)

**Feature Branch**: `007-smart-ac-control`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "空調自動調節"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 室內溫度自動維持 Auto-Maintain Indoor Comfort Temperature (Priority: P1)

When the home is occupied, the air conditioning system automatically adjusts to keep the
indoor temperature within the residents' configured comfort range — so Allen and Ann always
feel comfortable at home without manually operating the AC remote or app.

**Why this priority**: Automatic comfort maintenance is the core daily value of smart AC
control. It eliminates constant manual adjustments and ensures the home is always at a
pleasant temperature whenever residents are present.

**Independent Test**: Set a target comfort range of 24–26°C. Raise room temperature above 26°C
and confirm the AC activates in cooling mode; lower it below 24°C and confirm heating mode
activates (or AC turns off in cooling season). Verify the AC turns off once the target is
reached.

**Acceptance Scenarios**:

1. **Given** the home is occupied and indoor temperature rises above the configured upper
   comfort threshold, **When** the automation evaluates the temperature, **Then** the AC
   activates in cooling mode set to the target temperature within 3 minutes.
2. **Given** the home is occupied and indoor temperature falls below the configured lower
   comfort threshold, **When** the automation evaluates, **Then** the AC switches to heating
   mode or turns off (depending on season setting) within 3 minutes.
3. **Given** the indoor temperature is within the comfort range, **When** the automation
   evaluates, **Then** the AC is not activated and no unnecessary adjustments are made.
4. **Given** a resident manually overrides the AC temperature via the remote or dashboard,
   **When** the override occurs, **Then** the automation pauses for a configurable hold
   period (default 2 hours) before resuming automatic control.

---

### User Story 2 - 到家前預先調溫 Pre-Condition Home Before Arrival (Priority: P2)

The AC starts automatically a configurable time before a registered resident is expected to
arrive home — based on their estimated arrival — so the home has already reached a comfortable
temperature when they walk through the door, eliminating the wait on hot summer or cold winter
days.

**Why this priority**: Pre-conditioning turns reactive automation into proactive comfort. In
Taiwan's hot climate, walking into a room that is already cool is a meaningful quality-of-life
improvement that distinguishes smart home control from a simple timer.

**Independent Test**: Set departure location and estimated travel time. Confirm the AC activates
the correct number of minutes before estimated arrival, reaching the target temperature by
the time the resident arrives.

**Acceptance Scenarios**:

1. **Given** a resident's estimated arrival is within the configured pre-conditioning lead
   time (default 30 minutes), **When** the trigger fires, **Then** the AC turns on to the
   target comfort temperature and both residents receive a "正在為您預冷/預熱" notification.
2. **Given** the AC has started pre-conditioning, **When** the resident's arrival is cancelled
   or significantly delayed (departure not detected within 30 minutes of expected arrival),
   **Then** the AC turns off to avoid wasting energy and a notification is sent.
3. **Given** a resident is already home when the pre-conditioning would trigger for the
   arriving resident, **When** the trigger evaluates, **Then** no pre-conditioning action is
   taken (AC is already managed by Story 1's comfort maintenance).

---

### User Story 3 - 依天氣與時段智慧調整設定點 Weather & Time-of-Day Adaptive Setpoint (Priority: P3)

The AC's target temperature setpoint automatically adjusts based on current outdoor temperature
and time of day — for example, setting a slightly warmer target on mild days to save energy,
or shifting to a warmer sleep setpoint at night — so comfort is maintained intelligently
without residents needing to reprogram settings seasonally.

**Why this priority**: Fixed setpoints waste energy on mild days and feel wrong seasonally.
Adaptive setpoints make the automation context-aware, balancing comfort and efficiency
automatically throughout the year.

**Independent Test**: On a day with outdoor temperature below 28°C, confirm the AC's daytime
cooling setpoint is automatically adjusted 1–2°C warmer than the hot-day default. At the
configured sleep time, confirm the setpoint shifts to the sleep temperature.

**Acceptance Scenarios**:

1. **Given** outdoor temperature is below a mild-day threshold (default: 28°C), **When** the
   system calculates the adjusted setpoint, **Then** the cooling target is set 1–2°C warmer
   than the standard hot-day setpoint, reducing unnecessary cooling.
2. **Given** it is within the configured sleep time window, **When** the system applies the
   sleep setpoint, **Then** the AC adjusts to the sleep temperature (default: 1°C warmer than
   the daytime setpoint) to support comfortable sleep without overcooling.
3. **Given** a resident has manually set the temperature within the past 2 hours (hold period
   from Story 1), **When** the adaptive setpoint would update, **Then** the adaptive
   adjustment is deferred until the hold period expires.

---

### Edge Cases

- What if the AC unit is offline or unresponsive? (The automation logs the failure, sends a
  notification, and retries once after 5 minutes before giving up for that cycle.)
- What if indoor and outdoor temperature sensors disagree significantly? (Indoor sensor takes
  precedence for comfort control; outdoor sensor is used only for adaptive setpoint
  adjustments in Story 3.)
- What if the home has multiple AC units in different rooms? (Each unit is controlled
  independently based on its zone's temperature sensor. Zone configuration is set up during
  onboarding.)
- What if the temperature sensor is offline? (AC automation pauses for that zone; a
  notification alerts residents. The last known temperature is not used as a fallback to
  prevent unsafe conditions.)
- What if a resident sets the AC to a temperature outside the configured comfort range?
  (The manual override hold period applies; the automation resumes after the hold period
  and returns to the comfort range.)
- What if both residents have different preferred temperatures? (A shared household comfort
  range is used in v1; per-resident zone preferences are a future enhancement.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically activate and adjust the AC to maintain indoor
  temperature within the configured comfort range whenever the home is occupied.
- **FR-002**: The system MUST NOT activate the AC when the home is unoccupied (unless
  pre-conditioning for an imminent arrival per FR-006).
- **FR-003**: The system MUST switch the AC between cooling and heating modes based on the
  relationship between the current indoor temperature and the comfort range target.
- **FR-004**: When a resident manually overrides the AC setpoint, the system MUST suspend
  automatic control for a configurable hold period (default: 2 hours) before resuming.
- **FR-005**: All automatic AC state changes MUST be logged and visible to residents on the
  dashboard with a reason for each action.
- **FR-006**: The system MUST support pre-conditioning — automatically starting the AC a
  configurable lead time (default: 30 minutes) before a resident's estimated arrival.
- **FR-007**: If a pre-conditioning trigger fires but the resident's arrival is cancelled or
  significantly delayed, the system MUST turn off the pre-conditioning and notify residents.
- **FR-008**: The system MUST support time-of-day setpoint profiles — at minimum a daytime
  comfort setpoint and a sleep setpoint, each configurable by the residents.
- **FR-009**: The system MUST adjust the setpoint based on outdoor temperature on mild days
  to reduce unnecessary cooling or heating, within the resident-configured comfort range
  boundaries.
- **FR-010**: All comfort range settings, setpoint profiles, hold duration, and pre-conditioning
  lead time MUST be configurable from the dashboard without technical assistance.

### Key Entities

- **ACZoneConfig**: Per-zone configuration — zone name, linked AC unit, indoor temperature
  sensor, comfort range (lower/upper °C), daytime setpoint, sleep setpoint, hold duration,
  pre-conditioning lead time, enabled/disabled.
- **ACState**: Current AC state — zone, mode (cooling/heating/off/fan), current setpoint,
  current indoor temperature, control source (automatic/manual/pre-conditioning), hold expiry
  timestamp.
- **AdaptiveSetpointRule**: A rule for weather/time-based adjustment — condition type (outdoor
  temp threshold, time window), adjustment direction and amount (°C), priority.
- **ACActionLog**: A log entry for each AC state change — timestamp, zone, action taken,
  trigger reason, indoor temperature at time of action, outcome (success/failed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Indoor temperature stays within the configured comfort range for at least 90%
  of occupied time, measured over a 2-week period.
- **SC-002**: The AC does not activate in any unoccupied period (between departure and
  pre-conditioning trigger), measured over 2 weeks with zero false activations.
- **SC-003**: Pre-conditioning reaches the target comfort temperature within 5 minutes of
  the resident's actual arrival on 85% of pre-conditioned arrivals.
- **SC-004**: Both residents report after 2 weeks that they have not needed to manually
  adjust the AC more than once per day on average.
- **SC-005**: Energy usage during mild-weather days (outdoor temp < 28°C) is measurably
  lower than during hot days, confirming the adaptive setpoint is reducing unnecessary
  cooling.

## Assumptions

- The home has at least one smart AC unit with remote control capability integrated into the
  home automation platform. Multi-zone support (multiple units) is handled by repeating the
  configuration per zone; this spec covers the logic that applies to each zone equally.
- Indoor temperature sensors are installed in each controlled zone and integrated with the
  platform. If a zone has no sensor, that zone's AC is not under automatic control.
- Outdoor temperature data is sourced from the weather forecast feature (spec 003-weather-
  forecast); no separate outdoor sensor is required.
- Resident presence/occupancy is determined by the same presence detection mechanism used in
  specs 004 and 005 (phone geofencing). The AC automation uses the same occupied/unoccupied
  state.
- "Occupied" means at least one registered resident is at home. The AC does not attempt to
  detect which specific resident is in which zone in v1; per-resident zone preferences are a
  future enhancement.
- Pre-conditioning arrival estimation is based on detected departure from a known location
  combined with a configurable travel-time estimate. Dynamic ETA from mapping services is out
  of scope for v1.
- All temperatures are in °C. The default comfort range is 24–26°C for cooling season; the
  sleep setpoint default is 26°C. Residents may adjust all defaults.
- AC seasonal mode (cooling vs heating) follows a resident-configured seasonal calendar or
  is set manually; automatic season detection based on outdoor temperature is a future
  enhancement.

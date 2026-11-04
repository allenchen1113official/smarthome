# Feature Specification: 回家自動開燈 (Auto Turn On Lights When Arriving Home)

**Feature Branch**: `005-arrive-home-lights-on`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "回家自動開燈"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 夜間回家自動迎賓亮燈 Night-Time Arrival Welcome Lighting (Priority: P1)

When a resident arrives home after dark or when indoor ambient light is insufficient, the
entrance hallway and living area lights turn on automatically to a comfortable brightness
before the resident steps inside — so Allen and Ann never walk into a dark home or fumble
for a light switch.

**Why this priority**: This is the core daily-use scenario and the direct counterpart to spec
004-leave-home-lights-off. It delivers immediate safety and comfort value every evening
without any manual interaction.

**Independent Test**: With the home unoccupied and all lights off, have a resident arrive home
in the evening. Confirm that the hallway and living area lights turn on within 1 minute of
the resident's arrival being detected, at the configured welcome brightness.

**Acceptance Scenarios**:

1. **Given** the home is unoccupied and it is after sunset (or indoor light level is below the
   configured threshold), **When** a registered resident arrives home, **Then** the hallway
   and living area lights turn on within 1 minute at the configured welcome brightness and
   colour temperature.
2. **Given** one resident is already home when the second resident arrives, **When** the
   second resident's arrival is detected, **Then** the welcome lighting does NOT trigger again
   (lights are already on and should not be disrupted).
3. **Given** a light fails to turn on (device unresponsive) during an arrival, **When** other
   lights in the welcome set are reachable, **Then** reachable lights still turn on and the
   resident receives a notification listing any lights that could not be reached.

---

### User Story 2 - 白天回家不自動開燈 Daytime Arrival — No Auto Lights (Priority: P2)

When a resident arrives home during daylight hours with sufficient natural light, the
welcome lighting does NOT trigger — so the home feels natural and no electricity is wasted
turning on lights that are not needed.

**Why this priority**: Without daylight awareness the automation would turn on lights on
bright afternoons, wasting energy and feeling unnatural. This story makes the feature
context-aware and energy-efficient.

**Independent Test**: Have a resident arrive home at midday with all window blinds open and
confirm no lights turn on automatically.

**Acceptance Scenarios**:

1. **Given** a resident arrives home and either (a) it is before sunset, or (b) the indoor
   light sensor reads above the configured brightness threshold, **When** arrival is detected,
   **Then** no lights turn on automatically.
2. **Given** a resident arrives home just before sunset when light levels are borderline,
   **When** the indoor light level is below the threshold, **Then** the welcome lights turn
   on; when above, they do not.
3. **Given** the light sensor is offline, **When** a resident arrives home, **Then** the
   system falls back to time-of-day (sunset) to decide whether to trigger welcome lighting,
   and logs the sensor fault.

---

### User Story 3 - 個人化迎賓燈光場景 Personalised Welcome Lighting Scene (Priority: P3)

Each resident can configure their own preferred welcome lighting scene — which lights turn
on, at what brightness, and at what colour temperature — so Allen and Ann can each arrive
home to a lighting environment that suits their personal preference.

**Why this priority**: A shared household may have different preferences; Allen may prefer
bright cool-white light on arrival while Ann prefers warm dimmed light. Personalisation turns
a functional feature into a genuinely pleasant one.

**Independent Test**: Configure different scenes for Allen and Ann. Have each arrive home
separately and confirm the correct scene activates for each individual.

**Acceptance Scenarios**:

1. **Given** Allen and Ann each have a different welcome scene configured, **When** Allen
   arrives home alone, **Then** Allen's configured scene activates.
2. **Given** Allen and Ann each have a different welcome scene configured, **When** Ann
   arrives home alone, **Then** Ann's configured scene activates.
3. **Given** both residents arrive home at the same time (within a 2-minute window),
   **When** both arrivals are detected, **Then** the first-detected resident's scene activates
   and the second does not re-trigger a scene change.
4. **Given** a resident has not configured a personal scene, **When** they arrive home,
   **Then** the household default welcome scene is used as a fallback.

---

### Edge Cases

- What if the same resident's presence is detected as "arrived" multiple times in rapid
  succession (e.g., GPS bounce near the geofence)? (A 5-minute cooldown per resident prevents
  duplicate triggers for the same arrival event.)
- What if a resident arrives home immediately after leaving (e.g., forgot something and turned
  back)? (The 5-minute cooldown applies; the lights-on automation does not re-fire within the
  cooldown window.)
- What if a resident's arrival is detected while the home is already occupied and all lights
  are already on? (No action is taken; the home is already lit.)
- What if the welcome scene includes a light that was manually turned off by the resident
  already inside? (The arriving resident's scene activates only the lights in their scene
  configuration; it does not override manually set states of lights outside their welcome set.)
- What if the automation is triggered during a "do not disturb" period set by the resident
  inside? (Do not disturb mode is out of scope for v1; interaction with sleep/DND modes is a
  future enhancement.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect when a registered resident arrives home and trigger the
  welcome lighting sequence only when the ambient light condition warrants it (after sunset or
  indoor light below threshold).
- **FR-002**: The welcome lighting sequence MUST turn on the configured welcome lights within
  1 minute of arrival detection.
- **FR-003**: The system MUST NOT trigger welcome lighting if at least one resident is already
  home (lights assumed already on or set by the resident inside).
- **FR-004**: The system MUST NOT trigger welcome lighting during daytime when the indoor
  light level is at or above the configured brightness threshold.
- **FR-005**: If the light sensor is unavailable, the system MUST fall back to sunset/sunrise
  time to determine whether to trigger welcome lighting.
- **FR-006**: Each resident MUST be able to configure a personal welcome lighting scene
  (which lights, brightness, colour temperature) from the dashboard.
- **FR-007**: The system MUST use the arriving resident's personal scene if configured, or
  the household default scene if not.
- **FR-008**: A per-resident 5-minute arrival cooldown MUST prevent duplicate triggers from
  repeated presence detection events for the same arrival.
- **FR-009**: If any light in the welcome scene fails to turn on, the system MUST still turn
  on all reachable lights and notify the resident of any unresponsive lights.
- **FR-010**: The household default welcome scene and per-resident scenes MUST be configurable
  from the dashboard without technical assistance.

### Key Entities

- **WelcomeLightingConfig**: Household-level configuration — enabled/disabled, ambient light
  threshold (lux), fallback to sunset/sunrise if sensor unavailable.
- **ResidentWelcomeScene**: Per-resident scene definition — resident identity, list of lights
  to activate, brightness (%), colour temperature (K), scene name.
- **ArrivalEvent**: A detected resident arrival — resident identity, detection timestamp,
  home-was-occupied flag, light-trigger decision (triggered/skipped), reason for skip if
  applicable.
- **WelcomeLightingRun**: Log of each welcome lighting execution — trigger timestamp,
  resident, scene applied, lights turned on, lights failed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Welcome lights turn on within 1 minute of arrival detection on 95% of qualifying
  evening arrivals over a 2-week measurement period.
- **SC-002**: Zero false triggers occur during daytime arrivals when indoor light is
  sufficient, measured over 2 weeks of normal use.
- **SC-003**: Zero duplicate trigger events occur within the 5-minute arrival cooldown window,
  measured over 2 weeks.
- **SC-004**: Both residents confirm after 2 weeks that the welcome lighting activates their
  preferred scene correctly at least 9 times out of 10 arrivals.
- **SC-005**: Both residents report that they have not once walked into a dark home during
  evening hours since the feature was activated.

## Assumptions

- Resident presence detection uses the same mechanism established in spec
  004-leave-home-lights-off (phone geofencing or device tracker). Arrival is detected when
  a resident transitions from "away" to "home".
- "After dark" is determined by local sunset time (derived from the home's geographic
  location, already configured for weather in spec 003-weather-forecast) unless an indoor
  light sensor is available, in which case sensor data takes precedence.
- The indoor light sensor, if present, is already integrated with the home automation
  platform. If absent, the system falls back to sunset/sunrise time automatically.
- The "welcome lights" default set covers hallway and living area; this default is
  configurable per scene.
- Per-resident scene personalisation requires each resident's phone presence to be
  identifiable individually — the platform must distinguish Allen's arrival from Ann's
  arrival, not just detect "a resident arrived".
- Re-entry after brief departure (e.g., within 5 minutes) is handled by the cooldown;
  this is acceptable behaviour documented in Assumptions.
- Interaction with sleep/DND modes, party mode, or other environmental scenes is out of
  scope for v1 and will be addressed in a dedicated scene-management spec.
- This feature is the direct complement to spec 004-leave-home-lights-off; the two specs
  together form the complete presence-based lighting lifecycle.

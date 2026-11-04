# Feature Specification: 睡前自動關燈 (Bedtime Auto Lights Off)

**Feature Branch**: `006-bedtime-lights-off`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "睡前自動關燈"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 定時睡前關公共區域燈 Scheduled Bedtime — Common Area Lights Off (Priority: P1)

At a configured bedtime, all common area lights (living room, kitchen, corridors, bathrooms)
turn off automatically, leaving bedroom lights unaffected so each resident can finish their
bedtime routine at their own pace — without needing to walk through the home checking every
switch.

**Why this priority**: A scheduled lights-off for non-bedroom areas is the minimum daily-use
scenario. It eliminates the most common oversight (leaving the living room or kitchen lights
on overnight) without intruding on each resident's personal sleep timing.

**Independent Test**: Set a bedtime of 23:00. At 23:00 confirm that living room, kitchen, and
corridor lights turn off while any bedroom lights remain unaffected.

**Acceptance Scenarios**:

1. **Given** a bedtime schedule is configured and the time arrives, **When** the automation
   triggers, **Then** all common area lights turn off within 1 minute and both residents
   receive a "睡前燈光已關閉" notification.
2. **Given** the bedtime automation triggers, **When** a resident is still in a common area
   (presence detected), **Then** the automation still executes but the notification includes
   a reminder that a resident was detected in the area — it does not silently suppress the
   action.
3. **Given** a common area light fails to turn off (device unresponsive), **When** the
   automation runs, **Then** all reachable common area lights turn off and the notification
   lists any lights that could not be reached.

---

### User Story 2 - 「晚安」一鍵觸發全屋熄燈 Goodnight Trigger — Whole-Home Lights Off (Priority: P2)

Either resident can say a "晚安" (goodnight) voice command or tap a goodnight button on the
dashboard to immediately trigger the whole-home lights-off sequence — including bedroom lights
— with a short countdown so the resident has time to reach their bed before the room goes
dark.

**Why this priority**: The scheduled automation handles forgetting; the goodnight trigger
handles intentional sleep initiation. Together they cover both passive and active use cases.
The countdown prevents the frustrating experience of being plunged into darkness mid-motion.

**Independent Test**: Tap the goodnight button and confirm a 60-second countdown notification
appears, all lights (including bedroom) turn off after the countdown, and a confirmation
notification is sent.

**Acceptance Scenarios**:

1. **Given** a resident triggers the goodnight sequence, **When** the trigger fires, **Then**
   a countdown notification is sent to both residents indicating lights will turn off in the
   configured countdown duration (default 60 seconds).
2. **Given** the goodnight countdown is in progress, **When** either resident taps "取消"
   (Cancel) within the countdown window, **Then** the whole-home lights-off is cancelled and
   lights remain in their current state.
3. **Given** the countdown expires without cancellation, **When** the lights-off executes,
   **Then** all lights in the home — common areas and bedrooms — turn off and a brief
   confirmation notification is sent.
4. **Given** the goodnight sequence has been triggered by one resident, **When** the other
   resident is still awake and cancels within the countdown, **Then** only the shared common
   area lights turn off; bedroom lights are left for each resident to manage individually.

---

### User Story 3 - 漸進式調暗提示睡眠 Gradual Dimming Sleep Cue (Priority: P3)

In the 30 minutes before the configured bedtime, common area lights gradually dim from their
current brightness to a low warm level, providing a natural visual cue that bedtime is
approaching — helping both residents wind down without an abrupt lights-off event.

**Why this priority**: Gradual dimming signals sleep time naturally, supporting circadian
rhythm and making the scheduled lights-off feel less abrupt. It enhances the quality of the
bedtime experience beyond simple on/off automation.

**Independent Test**: With common area lights on at full brightness, observe the 30 minutes
before the configured bedtime and confirm lights dim progressively, reaching a low warm level
by bedtime, then turn off at the scheduled time.

**Acceptance Scenarios**:

1. **Given** 30 minutes remain before the configured bedtime, **When** the pre-dimming phase
   begins, **Then** common area lights begin gradually dimming toward a warm low-brightness
   level (≤ 20% brightness, ≥ 2700K colour temperature), reaching the minimum by bedtime.
2. **Given** the pre-dimming phase is active, **When** a resident manually adjusts a light's
   brightness, **Then** the dimming sequence pauses for that light only and resumes from the
   resident's set level on the next scheduled pre-dim cycle.
3. **Given** the pre-dimming feature is enabled, **When** the scheduled bedtime arrives,
   **Then** the fully dimmed lights turn off as per User Story 1 (no separate action needed).
4. **Given** a resident does not want pre-dimming on a particular night, **When** they disable
   the pre-dim from the dashboard or voice command, **Then** the lights remain at their
   current brightness until the scheduled bedtime cutoff.

---

### Edge Cases

- What if a resident is watching a movie or has manually set lights to full brightness near
  bedtime? (The pre-dimming sequence respects manual overrides per light; see Story 3
  Scenario 2. The scheduled lights-off at bedtime still executes unless cancelled.)
- What if the goodnight trigger fires while the scheduled bedtime automation countdown is also
  running? (The goodnight trigger takes precedence and resets the countdown timer.)
- What if both residents trigger the goodnight sequence simultaneously? (The first trigger
  starts the countdown; the second is ignored as a duplicate within the same cooldown window.)
- What if the bedtime is set later than the actual time residents go to sleep? (Residents use
  the goodnight button for earlier-than-scheduled sleep; the schedule is a safety net for
  forgotten lights.)
- What if no bedtime is configured? (The scheduled automation does not run; only the manual
  goodnight trigger is available.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a configurable nightly bedtime schedule that
  automatically turns off all common area lights at the specified time.
- **FR-002**: The bedtime schedule MUST distinguish between common area lights (turned off
  automatically) and bedroom lights (left unaffected by the schedule).
- **FR-003**: Either resident MUST be able to trigger a whole-home goodnight lights-off
  sequence from the dashboard or via a configured voice command.
- **FR-004**: The goodnight sequence MUST display a configurable countdown (default 60
  seconds) before turning off all lights, with a cancellation option available throughout.
- **FR-005**: When the goodnight countdown expires, ALL lights in the home MUST turn off,
  including bedroom lights.
- **FR-006**: Either resident MUST be able to cancel the goodnight sequence during the
  countdown with a single tap; cancellation MUST stop all pending light-off actions.
- **FR-007**: The system MUST support a gradual pre-dimming phase in the configurable period
  before bedtime (default 30 minutes), smoothly reducing common area lights to a low warm
  level.
- **FR-008**: Pre-dimming MUST respect manual light adjustments made by residents during the
  dimming phase — pausing the dim sequence for individually adjusted lights.
- **FR-009**: Both residents MUST receive a push notification when the scheduled bedtime
  lights-off executes, listing any lights that could not be turned off.
- **FR-010**: All bedtime settings (schedule time, pre-dim duration, countdown duration,
  common-area vs bedroom light groupings) MUST be configurable from the dashboard without
  technical assistance.

### Key Entities

- **BedtimeConfig**: Household configuration — scheduled bedtime, pre-dim duration (minutes),
  countdown duration (seconds), common area light group, bedroom light group, enabled/disabled.
- **LightGroup**: A named collection of lights — group name (e.g., "公共區域", "臥室"), list
  of member light identifiers, used to scope automation actions.
- **GoodnightEvent**: A log of each goodnight trigger — trigger source (schedule/voice/button),
  trigger timestamp, countdown duration, outcome (executed/cancelled), lights turned off,
  lights failed.
- **PreDimSession**: A log of each pre-dimming phase — start time, target bedtime, per-light
  dimming progress, any manual overrides applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Common area lights turn off within 1 minute of the scheduled bedtime on 95% of
  nights over a 2-week measurement period.
- **SC-002**: Both residents receive the bedtime notification within 30 seconds of the
  lights-off action completing.
- **SC-003**: The goodnight countdown cancellation works 100% of the time when either resident
  taps cancel within the countdown window, measured over 20 test cancellations.
- **SC-004**: Both residents report after 2 weeks that they have not once discovered common
  area lights left on the following morning.
- **SC-005**: Both residents report after 2 weeks that the gradual pre-dimming cue feels
  natural and has not disrupted their evening activities.

## Assumptions

- "Common area lights" and "bedroom lights" are organised into named groups in the home
  automation platform. Group membership is configurable from the dashboard; the initial
  grouping is set up during onboarding.
- The goodnight voice command trigger relies on the OpenClaw local voice assistant (per the
  constitution); the exact wake-word phrase is configured during integration setup.
- The pre-dimming feature requires smart lights that support brightness and colour temperature
  control. Lights that support only on/off are turned off at bedtime without pre-dimming.
- Weekday and weekend bedtimes share one configurable schedule in v1; separate weekday/weekend
  bedtimes are a future enhancement.
- The scheduled bedtime automation and the goodnight manual trigger are complementary: the
  schedule is a safety net for forgetting, the goodnight button is for intentional early sleep.
- This feature shares the light grouping concept with spec 004-leave-home-lights-off and spec
  005-arrive-home-lights-on; a unified light group management approach is decided at planning
  time.

# Feature Specification: 輪班模式 (Shift Work Mode)

**Feature Branch**: `008-shift-mode`

**Created**: 2026-05-26

**Status**: Draft

**Input**: User description: "輪班模式"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 一鍵切換班別自動調整全屋時程 One-Tap Shift Switch Updates All Schedules (Priority: P1)

Either resident can switch to a pre-configured shift profile (e.g., 日班, 夜班, 大夜班) from
the dashboard with a single tap — and all time-based home automations (wake-up alarm, morning
briefings, bedtime lights, AC pre-conditioning) immediately update to the schedules stored
in that shift profile — so the home fits the resident's actual work rhythm without manually
changing every automation separately.

**Why this priority**: Without a unified shift switch, a resident changing from day shift to
night shift would need to adjust 5–7 different automation schedules individually. A single
profile switch is the core value that makes this feature worthwhile.

**Independent Test**: Define a "夜班" profile with wake time 16:00 and bedtime 08:00. Activate
it from the dashboard and confirm that the wake-up automation (001), morning summary (002),
bedtime lights-off (006), and AC pre-conditioning (007) all reflect the new times within 1
minute — without changing the other resident's schedules.

**Acceptance Scenarios**:

1. **Given** a resident selects a shift profile from the dashboard, **When** the profile is
   activated, **Then** all time-based automations linked to that resident update to the
   profile's configured times within 1 minute, and a confirmation notification is sent to
   that resident.
2. **Given** Resident A activates a shift profile, **When** the profile takes effect, **Then**
   Resident B's automation schedules are NOT affected — each resident's schedules are
   independent.
3. **Given** a shift profile is active, **When** a resident switches to a different profile or
   back to their default schedule, **Then** all affected automations revert to the newly
   selected profile's times within 1 minute.

---

### User Story 2 - 自訂班別時間表設定 Define Custom Shift Profiles (Priority: P2)

Each resident can create, name, and configure their own shift profiles — specifying the
wake time, bedtime, and any other schedule-sensitive automation times — so the profiles
precisely match their actual shift patterns rather than relying on generic presets.

**Why this priority**: Shift patterns vary widely by workplace and role. Generic presets (日/夜)
may not match a resident's actual schedule (e.g., a 14:00–22:00 evening shift). Custom
profiles ensure the feature is genuinely useful rather than a rough approximation.

**Independent Test**: Create a new profile called "小夜班" with wake time 11:00, bedtime
02:00, and AC pre-conditioning disabled. Activate it and confirm each setting takes effect
correctly.

**Acceptance Scenarios**:

1. **Given** a resident navigates to shift profile settings, **When** they create a new
   profile with a name and configured times, **Then** the new profile appears in the shift
   selector and can be activated immediately.
2. **Given** a resident edits an existing shift profile, **When** the edit is saved, **Then**
   if that profile is currently active, all linked automations update immediately to reflect
   the new times; if inactive, the change takes effect when the profile is next activated.
3. **Given** a resident deletes a shift profile, **When** the deletion is confirmed, **Then**
   if the deleted profile was active, the system automatically reverts the resident to their
   default schedule and sends a notification.

---

### User Story 3 - 輪班行事曆自動排程 Rotating Shift Calendar Auto-Switch (Priority: P3)

A resident can programme a rotating shift calendar — specifying which profile is active on
which dates — so the home automatically switches shift modes on schedule without the resident
needing to remember to change it manually each rotation.

**Why this priority**: Shift rotations are regular and predictable; requiring a manual switch
every rotation defeats the "smart" home premise. Auto-switching eliminates the risk of
forgetting to switch and waking up to the wrong automation schedule.

**Independent Test**: Programme a schedule: 日班 for dates 1–15, 夜班 for dates 16–30.
Confirm the correct profile activates automatically at midnight on the 16th without any
manual action.

**Acceptance Scenarios**:

1. **Given** a resident has programmed a shift calendar, **When** a new shift period begins
   at midnight (or a configured transition time), **Then** the corresponding shift profile
   activates automatically and both residents receive a notification that the mode has changed.
2. **Given** the calendar auto-switch is about to occur, **When** the previous shift period
   ends, **Then** a reminder notification is sent to the resident the evening before,
   confirming the upcoming schedule change.
3. **Given** a resident manually overrides the active shift profile mid-period, **When** the
   manual override is in effect, **Then** the calendar auto-switch resumes at the next
   scheduled transition date (the manual override applies only until the next calendar event).

---

### Edge Cases

- What if both residents are on shift work simultaneously with different schedules? (Each
  resident has independent profiles and an independent active profile selection; their
  schedules do not interfere.)
- What if a shared household automation (e.g., bedtime lights-off for the whole home) is
  linked to both residents with different bedtimes? (The shared automation uses the earlier
  of the two active bedtimes, or a household consensus setting; the decision rule is
  configurable and defaults to "earliest bedtime wins" for energy saving.)
- What if no shift profile is active? (The resident's default schedule — as configured in
  each individual automation — applies. Shift mode is always opt-in.)
- What if a resident changes a shift profile while the calendar auto-switch is also pending?
  (Manual changes take precedence until the next calendar transition.)
- What if a resident has no shift calendar set up but activates a profile manually? (Manual
  activation persists indefinitely until manually changed or a calendar entry overrides it.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow each resident to define multiple named shift profiles,
  each storing a complete set of schedule overrides for all time-based automations.
- **FR-002**: Each shift profile MUST support configuring, at minimum: wake time, morning
  briefing time, bedtime, and AC pre-conditioning lead time.
- **FR-003**: Either resident MUST be able to activate a shift profile with a single tap from
  the dashboard, with all linked automations updating within 1 minute.
- **FR-004**: Activating one resident's shift profile MUST NOT modify the other resident's
  automation schedules.
- **FR-005**: The system MUST support a per-resident rotating shift calendar that automatically
  activates the correct shift profile on scheduled dates without manual intervention.
- **FR-006**: The system MUST send a reminder notification the evening before a calendar-
  scheduled shift transition occurs.
- **FR-007**: A manual profile activation MUST override the calendar schedule until the next
  calendar transition date, at which point the calendar resumes.
- **FR-008**: When a shared household automation (e.g., bedtime lights-off) is affected by
  two residents with different active profiles, the system MUST apply a configurable
  resolution rule (default: earliest scheduled time wins).
- **FR-009**: Deleting an active shift profile MUST automatically revert that resident to
  their default schedule and send a notification.
- **FR-010**: All shift profile creation, editing, deletion, manual activation, and calendar
  programming MUST be accessible from the dashboard without technical assistance.

### Key Entities

- **ShiftProfile**: A named schedule configuration per resident — profile name, resident,
  wake time, morning briefing time, bedtime, AC pre-conditioning enabled/duration, any
  additional automation-specific overrides.
- **ActiveShiftState**: Current shift state per resident — resident identity, active profile
  (or "default"), activation source (manual/calendar), activation timestamp, next calendar
  transition date.
- **ShiftCalendarEntry**: A single calendar entry — resident, start date, end date, linked
  shift profile, auto-switch enabled.
- **SharedScheduleConflict**: A resolution record for shared automations — automation name,
  resident A active time, resident B active time, resolved time, resolution rule applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a resident activates a shift profile, all linked automation schedules
  update within 1 minute on 100% of activations.
- **SC-002**: Both residents can create a new shift profile and activate it in under 3
  minutes without assistance.
- **SC-003**: Calendar auto-switches fire at the correct time on 100% of programmed
  transitions over a 4-week measurement period.
- **SC-004**: Zero cross-resident schedule contamination occurs — activating one resident's
  profile never modifies the other's schedules, verified over 20 activation tests.
- **SC-005**: Both residents report after one full shift rotation that they did not need to
  manually adjust any individual automation schedule during the rotation.

## Assumptions

- "Time-based automations" in scope for shift profile overrides are: wake-up automation (001),
  morning stock summary (002), morning weather briefing (003 voice), bedtime lights-off (006),
  and AC pre-conditioning (007). Other automations that are purely presence-based (004, 005)
  are not time-scheduled and therefore unaffected by shift profiles.
- Each resident has one "default schedule" which is their baseline when no shift profile is
  active. The default schedule is defined in each individual automation's settings.
- Shift profiles override times only — they do not enable or disable individual automations
  (except AC pre-conditioning which can be toggled per profile). Enabling/disabling individual
  automations is handled in each automation's own settings.
- The "earliest bedtime wins" conflict resolution default for shared automations (e.g., whole-
  home bedtime lights) is the starting default; residents may change this to "latest bedtime"
  or a manually fixed household time from the dashboard.
- A resident with no shift profiles defined sees no shift mode UI beyond a prompt to create
  their first profile; shift mode is entirely opt-in.
- Shift calendar dates are based on the home's local time zone (Taiwan, UTC+8).
- This feature acts as an orchestration layer on top of the individual automation specs
  (001–007); it does not replace any of their individual configuration but overrides their
  scheduled times when a shift profile is active.

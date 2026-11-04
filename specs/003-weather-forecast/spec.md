# Feature Specification: 天氣預報 (Weather Forecast)

**Feature Branch**: `003-weather-forecast`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "天氣預報"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 天氣儀表板卡片 Weather Dashboard Card (Priority: P1)

The home dashboard displays current weather conditions and today's forecast for the home
location at all times, so Allen and Ann can see the weather at a glance whenever they pass
the shared display or check their phones — without opening a separate weather app.

**Why this priority**: Always-visible weather information is the most fundamental weather
feature in a smart home. It requires no automation trigger and delivers immediate daily value
to both residents.

**Independent Test**: Open the home dashboard at any time of day and confirm a weather card
shows current temperature, weather condition (e.g., 晴天/陰天/雨天), humidity, and today's
high/low temperatures, with data no older than 30 minutes.

**Acceptance Scenarios**:

1. **Given** a resident opens the home dashboard, **When** the weather card is viewed, **Then**
   it displays: current temperature (°C), current weather condition with an icon, current
   humidity (%), today's high and low temperatures, and the time the data was last updated.
2. **Given** the weather data is more than 30 minutes old, **When** the card is viewed, **Then**
   the card shows a visible staleness indicator so the resident knows the data may not be
   current.
3. **Given** the weather data source is unreachable, **When** the card is viewed, **Then** the
   card shows the last known data with a clear "無法更新" (unable to update) label rather than
   showing an empty card.

---

### User Story 2 - 晨間天氣語音播報 Morning Weather Voice Announcement (Priority: P2)

During the morning routine, the home announces today's weather forecast and any notable
conditions (rain, extreme heat, air quality alerts) so Allen and Ann can plan their day —
what to wear, whether to carry an umbrella — without looking at a screen.

**Why this priority**: Voice delivery during the morning routine maximises the value of weather
data when decisions are being made (outerwear, commute planning). This builds naturally on the
data pipeline from Story 1.

**Independent Test**: Trigger the morning announcement manually and confirm it reads current
temperature, today's high/low, weather condition, and a rain advisory if today's precipitation
probability is ≥ 50%.

**Acceptance Scenarios**:

1. **Given** the morning announcement is triggered (via schedule or chained from morning
   wake-up automation), **When** the announcement plays, **Then** it states in Traditional
   Chinese: today's date, current temperature, high/low temperatures, weather condition, and
   humidity.
2. **Given** today's precipitation probability is ≥ 50%, **When** the announcement plays,
   **Then** it includes a reminder to bring an umbrella (帶傘提醒).
3. **Given** today's temperature high exceeds 35°C, **When** the announcement plays, **Then**
   it includes a heat advisory reminding residents to stay hydrated.
4. **Given** a voice speaker is offline at announcement time, **When** the announcement would
   play, **Then** the system skips voice delivery gracefully and displays the weather summary
   as a dashboard notification instead.

---

### User Story 3 - 天氣觸發智慧自動化 Weather-Triggered Smart Automations (Priority: P3)

The home automatically adjusts devices and sends reminders based on current or forecasted
weather conditions — for example, closing windows before rain, adjusting the air conditioner
target temperature on very hot days, or alerting residents to bring in laundry — so the home
responds to weather proactively without the residents needing to monitor forecasts themselves.

**Why this priority**: Weather-responsive automation is what differentiates a smart home from
a weather app. It delivers hands-free convenience but requires Stories 1 and 2 (data pipeline
and morning awareness) as a foundation.

**Independent Test**: Configure a "close windows if rain probability ≥ 70%" rule, set today's
forecast to simulate rain, trigger a weather data refresh, and confirm the smart windows close
and a notification is sent within 5 minutes.

**Acceptance Scenarios**:

1. **Given** a weather-triggered rule is configured (e.g., "close windows when rain probability
   ≥ 70%"), **When** the weather data updates and the condition is met, **Then** the specified
   device action executes within 5 minutes and the resident receives a brief notification
   explaining why the action was taken.
2. **Given** a weather-triggered action fires, **When** either resident manually overrides the
   device within 10 minutes, **Then** the automation respects the override and does not
   re-trigger on the same weather event.
3. **Given** a resident opens the weather automation settings on the dashboard, **When** they
   create, edit, or delete a weather trigger rule, **Then** the change takes effect within
   1 minute without requiring a system restart.

---

### Edge Cases

- What if location data is unavailable or misconfigured? (System shows an error on the
  dashboard card and does not trigger voice announcement until location is set.)
- What if two weather triggers fire simultaneously (e.g., close windows AND turn on AC)?
  (Both actions execute independently; each sends its own notification.)
- What if a triggered device (e.g., smart window) is offline? (The notification still fires
  with a note that the device could not be reached; other triggered devices still execute.)
- What if precipitation probability fluctuates around the threshold repeatedly? (Each rule
  fires at most once per weather data refresh cycle to avoid repeated triggering on the same
  event.)
- What if it is a typhoon warning day? (Out of scope for v1; a typhoon alert story is
  deferred to a future spec.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display current weather conditions for the home location on the
  dashboard at all times, refreshing data at least every 30 minutes.
- **FR-002**: The dashboard weather card MUST show, at minimum: current temperature (°C),
  weather condition with icon, humidity (%), today's high and low temperatures, and the
  last-updated timestamp.
- **FR-003**: The system MUST indicate clearly when displayed weather data is stale (older than
  30 minutes) or when the data source is unreachable.
- **FR-004**: The system MUST support a scheduled morning weather voice announcement in
  Traditional Chinese, covering current conditions, today's high/low, and any rain or heat
  advisories.
- **FR-005**: The morning announcement MUST include a 帶傘提醒 (umbrella reminder) when
  today's precipitation probability is ≥ 50%.
- **FR-006**: The morning announcement MUST include a heat advisory when today's high
  temperature exceeds 35°C.
- **FR-007**: The system MUST allow residents to create weather-triggered automation rules
  from the dashboard, specifying a weather condition threshold and a device action.
- **FR-008**: Weather-triggered rules MUST execute the configured device action within 5
  minutes of the condition being met, based on the latest fetched weather data.
- **FR-009**: Each weather-triggered action MUST fire at most once per weather data refresh
  cycle for the same condition, preventing repeated triggers on fluctuating values.
- **FR-010**: Residents MUST receive a notification whenever a weather-triggered automation
  fires, explaining the condition that caused it and the action taken.
- **FR-011**: All weather automation rules and the morning announcement schedule MUST be
  configurable from the dashboard without technical assistance.

### Key Entities

- **WeatherConfig**: Home location setting, morning announcement schedule, data refresh
  interval, announcement enabled/disabled.
- **WeatherSnapshot**: A single fetched data record — temperature, condition code, condition
  label, humidity, precipitation probability, today's high/low, fetch timestamp, data age.
- **WeatherTriggerRule**: A resident-defined automation rule — condition type (temperature,
  precipitation probability, condition code), threshold value, comparison operator, target
  device, action, last-fired timestamp.
- **WeatherAnnouncementRun**: Log of each morning announcement — trigger time, conditions
  read, advisories included, voice delivery status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The dashboard weather card displays data no older than 30 minutes on 95% of
  checks throughout the day.
- **SC-002**: Both Allen and Ann can read the current weather from the dashboard in under
  5 seconds at any time of day.
- **SC-003**: The morning voice announcement completes within 45 seconds of its scheduled
  trigger time on 95% of weekday mornings.
- **SC-004**: Weather-triggered automation rules execute their device actions within 5 minutes
  of the threshold condition being met, measured across 20 test triggers.
- **SC-005**: Both residents confirm after 2 weeks that the weather feature has at least once
  helped them make a practical decision (umbrella, clothing, window) without checking their
  phones.

## Assumptions

- The home is located in Taiwan; weather data is fetched for a single fixed location
  (configured during setup). Multi-location weather is out of scope for v1.
- Weather data is sourced from a publicly accessible service; this is non-personal data and
  cloud fetching is permitted under the constitution (Principle I exception).
- Air quality index (AQI/PM2.5) data is out of scope for v1; a dedicated air quality
  spec may follow.
- Typhoon warnings and severe weather alerts are out of scope for v1.
- The morning weather announcement may be chained after the morning wake-up automation
  (spec 001) or run on its own schedule; the chaining decision is made at planning time.
- Smart windows referenced in Story 3 are assumed to be installed and integrated; if not
  present, the resident can configure the trigger to control other compatible devices
  (e.g., sending a reminder notification instead of a physical action).
- Weather condition icons on the dashboard use a standard set; exact icon design is a
  UI/implementation detail decided at planning time.
- Residents use °C for temperature; Fahrenheit is not required.

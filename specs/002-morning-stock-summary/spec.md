# Feature Specification: 晨間股市摘要 (Morning Stock Market Summary)

**Feature Branch**: `002-morning-stock-summary`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "晨間股市摘要"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 自動語音股市簡報 Automated Voice Market Briefing (Priority: P1)

On weekday mornings at a configured time, the home announces a concise stock market summary
through the household speakers — covering major Taiwan and US market indices and a personal
watchlist — so Allen and Ann receive a market briefing hands-free during their morning routine
without unlocking any device.

**Why this priority**: Voice delivery is the primary value of a smart home integration; it turns
passive morning time (getting dressed, making coffee) into informed time. All other stories
depend on the data pipeline established here.

**Independent Test**: Trigger the summary manually and verify that a voice announcement plays
within 30 seconds, reading at least the Taiwan Weighted Index change, NASDAQ change, and any
configured watchlist items, with correct directional language (上漲/下跌).

**Acceptance Scenarios**:

1. **Given** it is a weekday and the configured summary time arrives, **When** the automation
   triggers, **Then** a voice announcement begins within 30 seconds, covering: (a) Taiwan
   Weighted Index (台灣加權指數) daily change, (b) at least one major US index (NASDAQ or S&P 500)
   previous close change, and (c) each stock/ETF on the personal watchlist with its change
   percentage and direction.
2. **Given** market data for one watchlist item is unavailable, **When** the announcement plays,
   **Then** the system skips that item, announces the rest normally, and appends a brief note
   that data for the missing item was unavailable.
3. **Given** either resident manually stops playback mid-announcement, **When** playback stops,
   **Then** the announcement does not restart and the system does not re-trigger until the next
   scheduled time.

---

### User Story 2 - 儀表板摘要卡片 Dashboard Summary Card (Priority: P2)

A summary card on the home dashboard displays the morning market data visually throughout the
day so either resident can glance at it on the shared display or their phone at any time after
the briefing runs.

**Why this priority**: Residents may miss the voice announcement; a persistent visual card
provides a secondary reference without requiring another voice trigger.

**Independent Test**: After the morning summary runs, navigate to the home dashboard and confirm
a card shows each index and watchlist item with its daily change, percentage, direction
indicator (▲/▼), and the data timestamp — all without any manual refresh.

**Acceptance Scenarios**:

1. **Given** the morning summary has run, **When** a resident opens the home dashboard,
   **Then** the summary card displays each configured index and watchlist item with: name,
   daily change amount, daily change percentage, direction (up/down), and the time the data
   was last fetched.
2. **Given** the dashboard card is displayed, **When** a resident taps a watchlist item on the
   card, **Then** no navigation or external app is opened — the card is read-only (out of scope
   to link to external brokerage apps in v1).
3. **Given** it is a weekend or the morning summary has not yet run today, **When** a resident
   views the dashboard, **Then** the card shows the most recent available data with a visible
   "as of [date]" label so the resident is not misled by stale data.

---

### User Story 3 - 個人觀察清單設定 Personal Watchlist Configuration (Priority: P3)

Either resident can add, remove, or reorder stocks and ETFs on the personal watchlist from the
home dashboard, so the morning briefing covers exactly the securities they care about.

**Why this priority**: The default indices are useful but the personal watchlist makes the
feature meaningfully personalised. This is a configuration story, not a daily-use story.

**Independent Test**: Add a new stock symbol to the watchlist via the dashboard, trigger the
morning summary manually, and confirm the new symbol appears in both the voice announcement
and the dashboard card.

**Acceptance Scenarios**:

1. **Given** a resident navigates to the watchlist settings on the dashboard, **When** they add
   a valid stock or ETF symbol, **Then** the symbol appears in the watchlist within 5 seconds
   and is included in the next morning summary run.
2. **Given** a resident enters an invalid or unrecognised symbol, **When** they attempt to save
   it, **Then** the system rejects the entry with a clear error message and does not add the
   symbol to the watchlist.
3. **Given** a resident removes a symbol from the watchlist, **When** the next morning summary
   runs, **Then** that symbol is absent from both the voice announcement and the dashboard card.

---

### Edge Cases

- What if the market data source is unreachable at announcement time? (System announces indices
  that are available and notes any unavailable data; announcement still plays.)
- What if the scheduled summary time falls on a market holiday? (Taiwan and US holiday calendars
  differ; data shows previous trading day's close with a "市場休市" label.)
- What if the summary is triggered before Taiwan market opens (pre-9:00 am)? (Shows previous
  day's close for Taiwan indices; US overnight futures data is out of scope for v1.)
- What if the watchlist is empty? (Announcement covers indices only; no error.)
- What if the voice speaker is offline at announcement time? (Dashboard card still updates;
  voice delivery fails gracefully with a resident notification.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically trigger the stock market summary at the configured
  weekday time without manual input.
- **FR-002**: The summary MUST include, at minimum, the Taiwan Weighted Index (台灣加權指數) and
  at least one major US index (NASDAQ Composite or S&P 500), showing daily change amount and
  percentage with directional language.
- **FR-003**: The summary MUST include all symbols on the resident-configured personal watchlist,
  each with its daily change and percentage.
- **FR-004**: The voice announcement MUST be delivered in Traditional Chinese (繁體中文).
- **FR-005**: The dashboard summary card MUST update automatically after each summary run and
  display the data timestamp.
- **FR-006**: Either resident MUST be able to add, remove, and reorder watchlist symbols from
  the dashboard without technical assistance.
- **FR-007**: The system MUST validate watchlist symbols before saving and reject unrecognised
  entries with a clear error message.
- **FR-008**: If any data source is unavailable, the system MUST still deliver the announcement
  for available items and clearly indicate which items are missing.
- **FR-009**: The summary MUST NOT trigger on weekends or public holidays (Taiwan calendar);
  on those days the dashboard card displays data from the most recent trading day with a
  staleness label.
- **FR-010**: Residents MUST be able to configure the summary trigger time from the dashboard.

### Key Entities

- **MarketSummaryConfig**: The persistent configuration record — scheduled trigger time,
  watchlist of symbols, enabled/disabled status.
- **WatchlistItem**: A single security entry — symbol code, display name, market (TW/US),
  resident-defined sort order.
- **MarketDataSnapshot**: The fetched market data at a point in time — symbol, price, daily
  change amount, daily change percentage, direction, fetch timestamp, trading status
  (open/closed/holiday).
- **MorningSummaryRun**: A log of each summary execution — trigger time, list of symbols
  included, list of symbols with data errors, voice delivery status, dashboard update status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The voice announcement begins within 30 seconds of the scheduled trigger time on
  95% of weekday mornings.
- **SC-002**: Both Allen and Ann can add or remove a watchlist item in under 2 minutes without
  assistance.
- **SC-003**: The dashboard card reflects updated market data within 1 minute of the summary
  run completing.
- **SC-004**: When a data source is unavailable, the announcement still plays for all available
  symbols — partial failure rate of zero for the available items.
- **SC-005**: After 2 weeks of use, both residents confirm the briefing covers the information
  they need for their morning investment awareness.

## Assumptions

- Market data is fetched from a publicly accessible data source; this data is non-personal and
  non-sensitive, so cloud fetching is permitted under the constitution (Principle I exception).
- Taiwan Weighted Index and NASDAQ Composite are the two fixed default indices; the watchlist
  is for additional resident-chosen symbols.
- US market data shown in the morning briefing reflects the previous US trading day's closing
  figures (due to Taiwan/US time zone difference); real-time US data is out of scope for v1.
- The briefing covers price change only — no earnings reports, news headlines, or analyst
  ratings in v1.
- Voice announcement language is Traditional Chinese (繁體中文) throughout; English ticker
  symbols are read as individual letters or by their Chinese names where known.
- The feature is triggered independently from (or optionally chained after) the morning
  wake-up automation (spec 001-morning-wake-up); the exact chaining is decided at planning time.
- Both residents share a single watchlist; per-resident watchlists are out of scope for v1.
- Taiwan public holiday calendar is used to determine non-trading days; the system does not
  need to track US market holidays for v1 (US data shows previous close regardless).

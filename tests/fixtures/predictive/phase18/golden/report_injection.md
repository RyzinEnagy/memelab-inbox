# Predictive research report (research only, not advice)

Separate from the opportunity score: nothing here changes the 100-point score, the fatal flags, the status, the watchlist or the scout lists, and it never sets a size.

## At a glance

- Probabilities shown: 0 of 21 target forecasts; abstentions 21; refused documents 0.
- No probability is shown: every target abstains or was refused. The reasons are named per target below.
- Reasons named across the targets: INSUFFICIENT_HISTORY 21, UNCALIBRATED 21, SOURCE_STALE 21, MODEL_NOT_SELECTED 21.
- T1 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 7; with a veto: 0; snapshots verified against the lab database: 7 of 7; events not attempted: 0.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes | Inputs |
|---|---|---|---|---|---|---|---|
| tmpevilpath | `solana:38ihiGtLeQoTqTGHbosHcWftMxpeP88saUmFScXqJWZf` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:6pi28KYmyz5GvN5WSo91ugA8JqMhWXVwK2ktjXxho4Qa` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:82TeexxktGLaL7532BoZC7thAaGh691iCQ7TaS42YYu` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:9evwDxCiNAaszjuP581MoGjR9dcaof6n6MRyp5KazkUe` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| line1line2 | `solana:EkwEd3uGWATNPVdSY4qwVABzUjqR1WtQsFzZagBmU8b6` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| abc | `solana:HNm7ydhn1jE22tyFmkyZkQRtPUUXrV4QqNBaCoYzRNec` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| scriptxscript | `solana:JEEoMXjzYnyE6rsPz8XxC84DcZHJoHVBcBjbXjEcaUrP` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |

## System status

- FACT: predictive flag on; integration version integration-1; report version report-1; passes in the state: 1, last pass c7c73f3b4f18
- FACT: model registry OK, log sha256 <varies>
- FACT: backtesting BACKTEST_NOT_AVAILABLE: the backtesting module is not installed on this line; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- FACT: state check: 0 problems; lab database GIVEN
- FACT: T1 24 h: registry mode NO_VIABLE_CHAMPION (pin <varies>; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T1b 6 h: registry mode NO_VIABLE_CHAMPION (pin <varies>; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_CALIBRATION_FAILED+RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T2 24 h: registry mode NO_VIABLE_CHAMPION (pin <varies>; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BELOW_MINIMUM+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- UNKNOWN: frozen model and reference cards become MODEL_STALE for decisions after 2026-10-31T00:00:00Z

## Target definitions

| Target | Event | Horizon | Positive | Negative | Version | Scope |
|---|---|---|---|---|---|---|
| T1 24 h (`price_path_target_before_invalidation_24h`) | the price rises 25% before it falls 15% | 24 hours | TARGET_FIRST | INVALIDATION_FIRST, AMBIGUOUS_BAR, NEITHER, NO_TRADES_AFTER_ENTRY | 1 | solana |
| T1b 6 h (`price_path_target_before_invalidation_6h`) | the price rises 25% before it falls 15% | 6 hours | TARGET_FIRST | INVALIDATION_FIRST, AMBIGUOUS_BAR, NEITHER, NO_TRADES_AFTER_ENTRY | 1 | solana |
| T2 24 h (`price_path_severe_drawdown_or_halt_24h`) | the price falls to half or trading halts | 24 hours | DRAWDOWN_50, TRADING_HALT | NO_SEVERE_EVENT | 1 | solana |

- Tie rule: a candle touching both barriers resolves to AMBIGUOUS_BAR, counted negative (conservative); no 1-minute refinement in v1.
- Price source: GeckoTerminal public OHLCV of the reference pool, minute timeframe aggregate 5, currency usd, empty intervals omitted.
- Caveats on every primary target: PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH: a price path is not proceeds, and no executable depth history exists.
- Not attempted (registered, not primary):
  - `exit_adjusted_target_before_invalidation_24h`: BLOCKED_NO_HISTORICAL_DEPTH, 24 hours; kept in contract.py (its wording names trade steps)
  - `liquidity_degradation_24h`: DEFERRED_FORWARD_COLLECTION, 24 hours; needs pool reserves or quotes at decision and decision + 24 h for every decision; existing snapshots give 29 of 278 thinned 24 h events, all from tokens the scheduled runs kept analysing; a scheduled collector needs Elving's approval
  - `failed_breakout_6h`: DEFERRED_PHASE_08, 6 hours; eligibility needs the m14 breakout class as of the decision; it is not exported and must be recomputed from backfilled candles
  - `catalyst_followthrough_24h_7d`: BLOCKED_NO_DATA, 24 hours; catalyst tables are not exported; every scheduled session starts empty
  - `distribution_event_24h`: BLOCKED_NO_DATA, 24 hours; holders and wallet transactions are not exported after 2026-10-07
  - `price_path_target_before_invalidation_7d`: EXPLORATORY, 168 hours; 136 matured events over 9 decision days; reported, never a primary claim
  - `launch_cohort_collapse_24h`: EXPLORATORY, 24 hours; 1,422 launches first seen inside one 22 h window (2026-10-08T13:45Z to 2026-10-09T11:57Z): no temporal out-of-sample split

## Carried constraints

- FACT: no number is shown for an abstention; a probability needs a SHADOW or VALIDATED_EXPERIMENTAL model with a CALIBRATED Phase 13 card, enough support and a point inside the display range (Phase 13 rule 12)
- FACT: a document is never shown without its abstention record and its request record (Phase 13 m4, PI-D-068)
- FACT: a FORECAST's number must equal the point recomputed from the raw number kept in the request record (Phase 13 m3, verify_point) and its cards must resolve from the registry
- FACT: a calibration available after the decision abstains (CALIBRATION_AFTER_DECISION, PI-D-070)
- FACT: the retrospective holdout is spent: its results are exploratory and can only make a statement more conservative
- FACT: token text (symbol, chain, labels, file names) is shown as letters, digits, dot, dash and underscore, at most 24 characters, and withheld when it carries a trading or forecast word (Phase 17 m3); no local path is shown (m8)
- INFERENCE: any interval is conditional on exchangeability of the event rate, which is neither established nor refuted (PI-D-070)
- HEURISTIC: CURRENT_VENDOR_LIST decisions abstain (no point-in-time pool); a live capture records its pool

## tmpevilpath `solana:38ihiGtLeQoTqTGHbosHcWftMxpeP88saUmFScXqJWZf`

### Identity and snapshot

- FACT: exact identity solana:38ihiGtLeQoTqTGHbosHcWftMxpeP88saUmFScXqJWZf; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 90b16ca8f5221924, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 82c479d35374 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 346853d3c4f7 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 047ddd290237 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 4, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_ec5019c3728ef44e89ff4b5aa7793eff`, record 82c479d35374, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_6d63b5954008dc33d126308556d3897f`, record 346853d3c4f7, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_eeeec861226fa06bb386d1bc96004adc`, record 047ddd290237, registry pin <varies>, data none, features none
- Token report: 20261027_0750__tmp_evil_pa_38ihiG.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## withheld `solana:6pi28KYmyz5GvN5WSo91ugA8JqMhWXVwK2ktjXxho4Qa`

### Identity and snapshot

- FACT: exact identity solana:6pi28KYmyz5GvN5WSo91ugA8JqMhWXVwK2ktjXxho4Qa; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 8e5cc32004c4f3a8, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- UNKNOWN: the lab's status: kept in the lab's token report (its label uses trade wording)

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 61e1fa7e1251 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | fabf56feda59 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 6479eacbcea4 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 0, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_837fe241249c446c745814e4e65f1b28`, record 61e1fa7e1251, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_f67a54f5e5b4a2c4676e117ca589c3fa`, record fabf56feda59, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_525477deee9fff4d631d26ec734aa9d0`, record 6479eacbcea4, registry pin <varies>, data none, features none
- Token report: withheld (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## withheld `solana:82TeexxktGLaL7532BoZC7thAaGh691iCQ7TaS42YYu`

### Identity and snapshot

- FACT: exact identity solana:82TeexxktGLaL7532BoZC7thAaGh691iCQ7TaS42YYu; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 9a658bdf4e20a64f, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | c102ae1c62c6 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | cc2cca05ab91 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 8dd92f605490 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 6, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_83c379b2f7b9c2d66e841880e0dae3fc`, record c102ae1c62c6, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_81406917532b65d291432ac9f491ead3`, record cc2cca05ab91, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_3a3a59f93cc9e72c4930061302a07088`, record 8dd92f605490, registry pin <varies>, data none, features none
- Token report: withheld (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## withheld `solana:9evwDxCiNAaszjuP581MoGjR9dcaof6n6MRyp5KazkUe`

### Identity and snapshot

- FACT: exact identity solana:9evwDxCiNAaszjuP581MoGjR9dcaof6n6MRyp5KazkUe; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot e69343d4de43d256, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | ee0b06c89e54 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | bbacbd0d2604 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 7cbbd82d1f0f |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 1, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_1a42f33e6780b1d8abe939e2da53c636`, record ee0b06c89e54, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_cdfbdbbb49d0da3a28b3bae3405f3733`, record bbacbd0d2604, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_b8d827ce9098419f7d250fa62895f2df`, record 7cbbd82d1f0f, registry pin <varies>, data none, features none
- Token report: withheld (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## line1line2 `solana:EkwEd3uGWATNPVdSY4qwVABzUjqR1WtQsFzZagBmU8b6`

### Identity and snapshot

- FACT: exact identity solana:EkwEd3uGWATNPVdSY4qwVABzUjqR1WtQsFzZagBmU8b6; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 44541081997588e7, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | db2347ce870f |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 82ce8e313714 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 1d6c5b57f49c |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 3, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_585d7d8fbb78e4e273b6a84f7ecaf451`, record db2347ce870f, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_8504ddf1a7c4dc9a2877e3fdf31d6e41`, record 82ce8e313714, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_00709365285f7dc285dc833f79a1d7e8`, record 1d6c5b57f49c, registry pin <varies>, data none, features none
- Token report: 20261027_0750_line1line2_EkwEd3.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## abc `solana:HNm7ydhn1jE22tyFmkyZkQRtPUUXrV4QqNBaCoYzRNec`

### Identity and snapshot

- FACT: exact identity solana:HNm7ydhn1jE22tyFmkyZkQRtPUUXrV4QqNBaCoYzRNec; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 94e62a14f31ce51a, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | ad6589291e43 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 3d5848f1f2a5 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | d68d82a8d7f0 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 2, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_a3f635841e7e809ad4601c1357b4cf5f`, record ad6589291e43, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_cfff2b569a4097fd2640d325035d61aa`, record 3d5848f1f2a5, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_7ca19ad8a7341cf844e4f2ee6682b5aa`, record d68d82a8d7f0, registry pin <varies>, data none, features none
- Token report: 20261027_0750_abc_HNm7yd.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## scriptxscript `solana:JEEoMXjzYnyE6rsPz8XxC84DcZHJoHVBcBjbXjEcaUrP`

### Identity and snapshot

- FACT: exact identity solana:JEEoMXjzYnyE6rsPz8XxC84DcZHJoHVBcBjbXjEcaUrP; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot f263ae893ecebf0f, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 60; fatal flags: none (unchanged by this report)
- FACT: the lab's status: WATCH

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label fx and structure label fx at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 71f70a0715f2 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | bd1e4ea53980 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 555273c8189b |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- FACT: T1 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 events, 7 days); prospective NOT_YET_MATURED
- FACT: T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 NOT_DISTINGUISHABLE_FROM_BASE_RATE (68 events, 7 days); prospective NOT_YET_MATURED
- FACT: T2 24 h: registry NO_VIABLE_CHAMPION, pin matches the committed index; references (never published): base_rate B0 is the skill reference; simple_model B2 INSUFFICIENT_EVENTS (59 events, 6 days); prospective NOT_YET_MATURED
- INFERENCE: no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); the retrospective holdout is spent, so these verdicts are exploratory

### Execution and stress

- FACT: fatal-flag veto: none recorded by the lab
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 5, pass c7c73f3b4f18)
- T1 24 h: forecast `fc_dc55d4c3fa7c02cee9fa241867f65265`, record 71f70a0715f2, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_bebbfc0502e72422319d60ae8c2394ca`, record bd1e4ea53980, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_4d11a5e9c4cdb51e3b0cdaeca61c2897`, record 555273c8189b, registry pin <varies>, data none, features none
- Token report: 20261027_0750_scriptx_s_JEEoMX.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## Events not attempted

- None.

## Units and times

- Times are UTC in ISO 8601 with Z. Ages are in minutes, hours or days as written. Horizons are in hours. Amounts are USD.
- Percentages appear only in target definitions (barriers), in measured market changes between two attempts of a token (the event line, labelled "measured market changes since the previous attempt, not probabilities"), and in a verified FORECAST (point and interval, whole percents).
- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the JSON view has them in full).
- Buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), UNKNOWN (missing; earns nothing).

# Predictive research report (research only, not advice)

Separate from the opportunity score: nothing here changes the 100-point score, the fatal flags, the status, the watchlist or the scout lists, and it never sets a size.

## At a glance

- Probabilities shown: 0 of 15 target forecasts; abstentions 15; refused documents 0.
- No probability is shown: every target abstains or was refused. The reasons are named per target below.
- Reasons named across the targets: INSUFFICIENT_HISTORY 15, UNCALIBRATED 15, OUT_OF_SCOPE_CHAIN 3, TARGET_NOT_FEASIBLE 3, SOURCE_STALE 15, MODEL_NOT_SELECTED 15.
- T1 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 5; with a veto: 1; snapshots verified against the lab database: 5 of 5; events not attempted: 2.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes | Inputs |
|---|---|---|---|---|---|---|---|
| EVMX | `base:0x2a9fd3e5254a3c480891ad6005c40e682bdeb3e7` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| NOPOOL | `solana:2Rq9sGhqm5kDmdD3hep8dFK89imF9zXEGPPSP6AQbydw` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| OLDX | `solana:3PvVEv2pkoSLnMxC8z72c5bnsFVebrrvJG6nSvoDZDi6` | 2026-10-24T08:00:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| GOMOX | `solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | CANNOT_EXIT_5K | FRESH |
| ABC | `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |

## System status

- FACT: predictive flag on; integration version integration-1; report version report-1; passes in the state: 1, last pass c1a575dc7f3e
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

## EVMX `base:0x2a9fd3e5254a3c480891ad6005c40e682bdeb3e7`

### Identity and snapshot

- FACT: exact identity base:0x2a9fd3e5254a3c480891ad6005c40e682bdeb3e7; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot fe5d8859fd5cf88a, row sha256 <varies>
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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, OUT_OF_SCOPE_CHAIN, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | f6676bb1d660 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, OUT_OF_SCOPE_CHAIN, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | b8540ac01aff |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, OUT_OF_SCOPE_CHAIN, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 1c6dd0453c47 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the target is defined for Solana decisions only; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - OUT_OF_SCOPE_CHAIN: the targets are defined for Solana only; another chain needs a change control and its own evidence.
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

- Request record <varies> (request 4, pass c1a575dc7f3e)
- T1 24 h: forecast `fc_f8cb2ae8f000f7c1729ea9e2857c254a`, record f6676bb1d660, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_666eb56e83e45da163e1cd22d4adc4cb`, record b8540ac01aff, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_77e3a2e5adc20200838ef862effb613b`, record 1c6dd0453c47, registry pin <varies>, data none, features none
- Token report: 20261027_0750_EVMX_0x2a9f.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## NOPOOL `solana:2Rq9sGhqm5kDmdD3hep8dFK89imF9zXEGPPSP6AQbydw`

### Identity and snapshot

- FACT: exact identity solana:2Rq9sGhqm5kDmdD3hep8dFK89imF9zXEGPPSP6AQbydw; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot aa80e3a855f2e399, row sha256 <varies>
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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | a5b97fc9ffbd |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | c100aa37f3e2 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 795a604a2cf4 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: no point-in-time pool on the registered price route at the decision; the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - TARGET_NOT_FEASIBLE: a point-in-time pool recorded at the capture on the registered price route.
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

- Request record <varies> (request 2, pass c1a575dc7f3e)
- T1 24 h: forecast `fc_e4df550ad254e38d27bc78de607ea405`, record a5b97fc9ffbd, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_61a05af0cdefb607c09dcd626f5d675b`, record c100aa37f3e2, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_845ad778f766ad467f1b9eaea7d8877c`, record 795a604a2cf4, registry pin <varies>, data none, features none
- Token report: 20261027_0750_NOPOOL_2Rq9sG.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## OLDX `solana:3PvVEv2pkoSLnMxC8z72c5bnsFVebrrvJG6nSvoDZDi6`

### Identity and snapshot

- FACT: exact identity solana:3PvVEv2pkoSLnMxC8z72c5bnsFVebrrvJG6nSvoDZDi6; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot f4abd5db40720640, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-24T08:00:00Z (collector-run start, PI-D-011); age at capture 3.0 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot -16.0 hours (vendor's first pool time 2026-10-25T00:00:00Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | ecdb1973ec77 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 169d8fc0ee21 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 9b91b7392070 |

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

- Request record <varies> (request 3, pass c1a575dc7f3e)
- T1 24 h: forecast `fc_a87dca00576839d54709c64f19d82d2c`, record ecdb1973ec77, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_7eb0d8a2aa5518b33b11ed3592104ece`, record 169d8fc0ee21, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_38141e3fac8adb61499a0a7d37d1bf38`, record 9b91b7392070, registry pin <varies>, data none, features none
- Token report: 20261024_0800_OLDX_3PvVEv.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## GOMOX `solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32`

### Identity and snapshot

- FACT: exact identity solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot bd84b3b58cdb37c0, row sha256 <varies>
- FACT: decision time 2026-10-27T08:00:00Z (CAPTURE_TIME); capture 2026-10-27T08:00:00Z
- FACT: inputs observed 2026-10-27T07:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.3 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 0; fatal flags: CANNOT_EXIT_5K (unchanged by this report)
- FACT: the lab's status: REJECTED

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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 6b57848b1ca6 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | e138cddc48c9 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | c909d556642a |

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

- FACT: fatal-flag veto: CANNOT_EXIT_5K; no forecast clears it
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record <varies> (request 1, pass c1a575dc7f3e)
- T1 24 h: forecast `fc_311d6ee2c8de428f709991dba312ffe5`, record 6b57848b1ca6, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_a36615d5d18de917107c0516c55dfd01`, record e138cddc48c9, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_ab2c6a0e3b89aaec7f6c0b4be46eb5d5`, record c909d556642a, registry pin <varies>, data none, features none
- Token report: 20261027_0750_GOMOX_3p12Jy.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## ABC `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS`

### Identity and snapshot

- FACT: exact identity solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 129284393ccf133f, row sha256 <varies>
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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 2633d3db07f1 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 974434296119 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | c0ce355a3313 |

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

- Request record <varies> (request 0, pass c1a575dc7f3e)
- T1 24 h: forecast `fc_b7e95d9e95a0124bd088728ab690daea`, record 2633d3db07f1, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_a0da288088c371b3c5392f60a07c9b38`, record 974434296119, registry pin <varies>, data none, features none
- T2 24 h: forecast `fc_818addbf03c8c45c1cb5caae1287b06a`, record c0ce355a3313, registry pin <varies>, data none, features none
- Token report: 20261027_0750_ABC_Ebjh5R.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## Events not attempted

| Event | Exact chain:mint | Capture (UTC) | Covered by a report above | Request | Detail |
|---|---|---|---|---|---|
| NO_DECISION_SNAPSHOT | `solana:DFEq9TW2UqdHo73qxmcfy3r31VDDwmgbt8exaEr2q6pE` | 2026-10-27T08:00:00Z | no | <varies> | none |
| NOT_EXACT_IDENTITY | `solana:not-an-exact-address` | 2026-10-27T08:00:00Z | no | <varies> | none |

## Units and times

- Times are UTC in ISO 8601 with Z. Ages are in minutes, hours or days as written. Horizons are in hours. Amounts are USD.
- Percentages appear only in target definitions (barriers) and in a verified FORECAST (point and interval, whole percents).
- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the JSON view has them in full).
- Buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), UNKNOWN (missing; earns nothing).

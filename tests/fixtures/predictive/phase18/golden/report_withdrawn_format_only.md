FORMAT-ONLY FIXTURE: invented data, not a forecast

# Predictive research report (research only, not advice)

Separate from the opportunity score: nothing here changes the 100-point score, the fatal flags, the status, the watchlist or the scout lists, and it never sets a size.

## At a glance

- Probabilities shown: 1 of 6 target forecasts; abstentions 5; refused documents 0.
- Reasons named across the targets: INSUFFICIENT_HISTORY 5, UNCALIBRATED 5, SOURCE_STALE 3, MODEL_NOT_SELECTED 5.
- T1 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 2; with a veto: 1; snapshots verified against the lab database: 2 of 2; events not attempted: 0.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes | Inputs |
|---|---|---|---|---|---|---|---|
| FXA | `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS` | 2026-10-30T00:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| FXC | `solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32` | 2026-10-29T23:50:00Z | FORECAST 83% (41% to 100%) FORMAT-ONLY FIXTURE overridden by veto | ABSTAIN (no number) | ABSTAIN (no number) | CANNOT_EXIT_5K | FRESH |

## System status

- FACT: predictive flag on; integration version integration-1; report version report-1; passes in the state: 2, last pass eaf658683d84
- FACT: model registry OK, log sha256 <varies>
- FACT: backtesting BACKTEST_NOT_AVAILABLE: the backtesting module is not installed on this line; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- FACT: state check: 0 problems; lab database GIVEN
- FACT: T1 24 h: registry mode NO_VIABLE_CHAMPION (pin <varies>; FIXTURE_ROLLBACK, no earlier usable champion: abstain with the references); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T1b 6 h: registry mode NO_VIABLE_CHAMPION (pin none; NO_PIN); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T2 24 h: registry mode NO_VIABLE_CHAMPION (pin none; NO_PIN); Phase 13 calibration UNCALIBRATED at level ABSTAIN
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

## FXA `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS`

### Identity and snapshot

- FACT: exact identity solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS; event MATERIAL_CHANGE (served changed; last attempt 3600 s ago)
- FACT: snapshot 8bff908229fd15d2, row sha256 <varies>
- FACT: decision time 2026-10-30T01:00:00Z (CAPTURE_TIME); capture 2026-10-30T01:00:00Z
- FACT: inputs observed 2026-10-30T00:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 5.0 days (vendor's first pool time 2026-10-25T00:00:00Z)

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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 654a9980749f |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 53d776c7135a |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | bc0922e13ab5 |

- No probability for T1 24 h, T1b 6 h, T2 24 h, from the abstention records: the price source or route failed or is unknown at the decision; the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - SOURCE_STALE: a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.

### Historical prediction and its out-of-sample record

- UNKNOWN: out-of-sample record: REGISTRY_INDEX_NOT_AVAILABLE (the committed registry index is not available)

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

- Request record <varies> (request 2, pass eaf658683d84); previous attempt <varies>
- T1 24 h: forecast `fc_4c59ca70dcae9640209c7100d3b9fd5f`, record 654a9980749f, registry pin <varies>, data none, features none
- T1b 6 h: forecast `fc_994a21ac56a7f8b1d48e4cce578a2332`, record 53d776c7135a, registry pin none, data none, features none
- T2 24 h: forecast `fc_dfa9ac930dfeaeecaa65f0b61e8dc0a8`, record bc0922e13ab5, registry pin none, data none, features none
- Token report: 20261030_0050_FXA_Ebjh5R.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## FXC `solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32`

### Identity and snapshot

- FACT: exact identity solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot cc7aac863600b9c0, row sha256 <varies>
- FACT: decision time 2026-10-30T00:00:00Z (CAPTURE_TIME); capture 2026-10-30T00:00:00Z
- FACT: inputs observed 2026-10-29T23:50:00Z (collector-run start, PI-D-011); age at capture 10 minutes: FRESH
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 5.0 days (vendor's first pool time 2026-10-25T00:00:00Z)

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 62; fatal flags: CANNOT_EXIT_5K (unchanged by this report)
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
| T1 24 h | 24 hours | FORECAST 83% (41% to 100%) FORMAT-ONLY FIXTURE overridden by veto | none | support 60 calibration events (32 positive); base rate 29% | B2:price_path_target_before_invalidation_24h (sha 79cc70276e3d) | 2026-10-17T00:00:00Z | 069a84021b5f |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 1177d10dd9b9 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | e05eeadef4d0 |

- No probability for T1b 6 h, T2 24 h, from the abstention records: the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.
- T1 24 h (24 hours, +25% before -15%): research estimate at level SHADOW (VENN_ABERS), 83% with interval 41% to 100%; base rate 29%; support 60 calibration events; calibration card de11c57f1781; price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS). FORMAT-ONLY FIXTURE: invented data, not a forecast.
  - Overridden: this snapshot carries a veto (below); the lab's fatal-flag override applies unchanged and the estimate is not usable for any decision on it.
  - Caveats: PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, INTERVAL_EXCLUDES_UNMODELED_RISK, SHADOW_RESEARCH_ONLY, COHORT_ESTIMATE_NOT_TOKEN_HISTORY.

### Historical prediction and its out-of-sample record

- UNKNOWN: out-of-sample record: REGISTRY_INDEX_NOT_AVAILABLE (the committed registry index is not available)

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

- Request record <varies> (request 1, pass 1a5e8693623a)
- T1 24 h: forecast `fc_888f96c6898657d100ed6c319b87cf30`, record 069a84021b5f, registry pin <varies>, data f59d9650953b, features 90781ad72ac1
- T1b 6 h: forecast `fc_78f6ef5539986c3a58c505a2bf2ef347`, record 1177d10dd9b9, registry pin none, data none, features none
- T2 24 h: forecast `fc_db431fb132477f5d8f792c6d87fdd70a`, record e05eeadef4d0, registry pin none, data none, features none
- Token report: 20261029_2350_FXC_3p12Jy.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: COHORT_ESTIMATE_NOT_TOKEN_HISTORY, INTERVAL_EXCLUDES_UNMODELED_RISK, NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS, SHADOW_RESEARCH_ONLY.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## Events not attempted

- None.

## Units and times

- Times are UTC in ISO 8601 with Z. Ages are in minutes, hours or days as written. Horizons are in hours. Amounts are USD.
- Percentages appear only in target definitions (barriers) and in a verified FORECAST (point and interval, whole percents).
- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the JSON view has them in full).
- Buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), UNKNOWN (missing; earns nothing).

FORMAT-ONLY FIXTURE: invented data, not a forecast

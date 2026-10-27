# Predictive research report (research only, not advice)

Separate from the opportunity score: nothing here changes the 100-point score, the fatal flags, the status, the watchlist or the scout lists, and it never sets a size.

## At a glance

- Probabilities shown: 0 of 24 target forecasts; abstentions 24; refused documents 0.
- No probability is shown: every target abstains or was refused. The reasons are named per target below.
- Reasons named across the targets: INSUFFICIENT_HISTORY 24, UNCALIBRATED 24, TARGET_NOT_FEASIBLE 6, SOURCE_STALE 24, MODEL_NOT_SELECTED 24.
- T1 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 8; with a veto: 3; snapshots verified against the lab database: 8 of 8; events not attempted: 16.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes | Inputs |
|---|---|---|---|---|---|---|---|
| slopcannon | `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | WASH_TRADING_HIGH | INPUT_STALE |
| STONK | `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| DARK | `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| PAID | `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| GOMO | `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | CANNOT_EXIT_5K | INPUT_STALE |
| HIGGS | `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | WASH_TRADING_HIGH | INPUT_STALE |
| ZCAT | `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| baton | `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |

## System status

- FACT: predictive flag on; integration version integration-1; report version report-1; passes in the state: 3, last pass 9453713c91c9
- FACT: model registry OK, log sha256 f02548bd8470
- FACT: backtesting BACKTEST_NOT_AVAILABLE: the backtesting module is not installed on this line; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- FACT: state check: 0 problems; lab database GIVEN
- FACT: T1 24 h: registry mode NO_VIABLE_CHAMPION (pin 7cb1c8b292f8; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T1b 6 h: registry mode NO_VIABLE_CHAMPION (pin 4efd53b196ee; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_CALIBRATION_FAILED+RETROSPECTIVE_BSS_BELOW_0+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
- FACT: T2 24 h: registry mode NO_VIABLE_CHAMPION (pin b9e82db1db19; NO_ENTRY_AT_SHADOW_OR_ABOVE, PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE, B2_RETROSPECTIVE_BELOW_MINIMUM+NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION, NO_ENSEMBLE); Phase 13 calibration UNCALIBRATED at level ABSTAIN
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

## slopcannon `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW`

### Identity and snapshot

- FACT: exact identity solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot b6f9f499178e9563, row sha256 4d9ab9345a2b396a
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 10.7 days (vendor's first pool time 2026-09-26T07:43:08Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 61; fatal flags: WASH_TRADING_HIGH (unchanged by this report)
- FACT: the lab's status: REJECTED

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label UPTREND at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 93dc9c6611ad |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | f5fdcbdd4aa1 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 0407fbe872df |

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

- FACT: fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record 3a38ec90d378 (request 7, pass c4177dd69a9a)
- T1 24 h: forecast `fc_1d986e48f143c75857ce3c7d4db96fdb`, record 93dc9c6611ad, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_c8af13e622bd29d7818d5360482c5388`, record f5fdcbdd4aa1, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_c83b9de1fc29b09355baadb7c5c0fc04`, record 0407fbe872df, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_slopcannon_55Vr2V.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## STONK `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx`

### Identity and snapshot

- FACT: exact identity solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 771e6521fb6cef2b, row sha256 c6f37aeb34721ba0
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 75.2 days (vendor's first pool time 2026-07-23T19:06:57Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 68; fatal flags: none (unchanged by this report)
- FACT: the lab's status: SETUP DEVELOPING

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label UPTREND at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | f4c7bd4ab869 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 9ca155e5a811 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 597474ede808 |

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

- Request record 68f1dd5894a1 (request 1, pass c4177dd69a9a)
- T1 24 h: forecast `fc_ccad62cc1909943bea081a7182205f0d`, record f4c7bd4ab869, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_64d9ab982b777c44c0797b201a92e23e`, record 9ca155e5a811, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_a5a434fe440da22b3a98b099c2dca931`, record 597474ede808, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_STONK_6GmAFS.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## DARK `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3`

### Identity and snapshot

- FACT: exact identity solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot c1c7dae80d324251, row sha256 17557aa48d31d335
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 5.3 days (vendor's first pool time 2026-10-01T17:36:20Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 67; fatal flags: none (unchanged by this report)
- FACT: the lab's status: OVEREXTENDED

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label TRANSITION at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 62f9941333ad |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | eb9f56bd98b4 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | ac22ffe2e332 |

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

- Request record 8d7f6719fc8c (request 2, pass c4177dd69a9a)
- T1 24 h: forecast `fc_d622d750d9386d58aa66e07ea295ef22`, record 62f9941333ad, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_ac281f4480875a7b8e8501a27f19e4aa`, record eb9f56bd98b4, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_2f23b8eca7ec4d60eb26d5a6955dd836`, record ac22ffe2e332, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_DARK_7KEPAp.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## PAID `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump`

### Identity and snapshot

- FACT: exact identity solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 744ef961b24239b9, row sha256 c1e9be0395aaeaf8
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 21.2 days (vendor's first pool time 2026-09-15T19:20:20Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 66; fatal flags: none (unchanged by this report)
- FACT: the lab's status: SETUP DEVELOPING

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label TRANSITION at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 9b6f5ea44886 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | b613485b0c6e |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | e1ba86352e9f |

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

- Request record 4d018efcaab0 (request 0, pass c4177dd69a9a)
- T1 24 h: forecast `fc_88a159bbca5022c5a4cce38e1f0b1e3e`, record 9b6f5ea44886, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_056d079872cc2cb85d0811785767c6c0`, record b613485b0c6e, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_c0a2cacb1684a9071f3b3e5a95697517`, record e1ba86352e9f, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_PAID_98kfF7.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## GOMO `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump`

### Identity and snapshot

- FACT: exact identity solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 599dbfcdf78eba2e, row sha256 585254e3f8673d72
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.1 days (vendor's first pool time 2026-10-04T21:47:51Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 62; fatal flags: CANNOT_EXIT_5K (unchanged by this report)
- FACT: the lab's status: REJECTED

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label UPTREND at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 6a9008ec0f63 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | a721a1b45878 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 89d13f4d828c |

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

- Request record 4be5035a5738 (request 3, pass c4177dd69a9a)
- T1 24 h: forecast `fc_662a6b96fbb373e06e52aafcd6f4f1ee`, record 6a9008ec0f63, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_6282902f34d915a8a8206b7631d395c4`, record a721a1b45878, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_bab97c34063a433bdeccf952ad6d8b5b`, record 89d13f4d828c, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_GOMO_9XKzy4.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## HIGGS `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump`

### Identity and snapshot

- FACT: exact identity solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 94125012eafce70e, row sha256 41f559ead534d889
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 2.5 days (vendor's first pool time 2026-10-04T12:26:34Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 48; fatal flags: WASH_TRADING_HIGH (unchanged by this report)
- FACT: the lab's status: REJECTED

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label DISTRIBUTION and structure label TRANSITION at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | dd342b3bc46a |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | eb365e0b95a8 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | f7326821cb26 |

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

- FACT: fatal-flag veto: WASH_TRADING_HIGH; no forecast clears it
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- Request record 8819bd2c0318 (request 4, pass c4177dd69a9a)
- T1 24 h: forecast `fc_1ac9dc27b46f32451b78402401dab3a3`, record dd342b3bc46a, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_c5946a0b85e3602099b2afe53109056a`, record eb365e0b95a8, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_4ae10a38a1bdf144edd4f6e2bc260735`, record f7326821cb26, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_HIGGS_DoVAVz.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## ZCAT `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR`

### Identity and snapshot

- FACT: exact identity solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 7b982f14be1d1a8b, row sha256 615ce37bd8b4b252
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 37.0 days (vendor's first pool time 2026-08-30T23:29:55Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 50; fatal flags: none (unchanged by this report)
- FACT: the lab's status: DISTRIBUTION RISK

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label DISTRIBUTION and structure label TRANSITION at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 412cae0fa66a |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 1f202eb362f3 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, TARGET_NOT_FEASIBLE, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | eafe28bbabfd |

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

- Request record 485b667ad593 (request 5, pass c4177dd69a9a)
- T1 24 h: forecast `fc_e14bd8825239a14190a449287b0fcd9e`, record 412cae0fa66a, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_68f5014d8ac20e437e99f92cb071bce8`, record 1f202eb362f3, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_f9d4454c77be985fad29f6b5520fa04b`, record eafe28bbabfd, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_ZCAT_HcRLc9.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## baton `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump`

### Identity and snapshot

- FACT: exact identity solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 3299be006a2bb1ac, row sha256 426233ac81402d25
- FACT: decision time 2026-10-27T10:39:49Z (CAPTURE_TIME); capture 2026-10-27T10:39:49Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.4 days: INPUT_STALE
- FACT: the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)
- HEURISTIC: token age at the snapshot 27.2 days (vendor's first pool time 2026-09-09T20:32:11Z)
- UNKNOWN: current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE

### Structural research (the lab's)

- FACT: the lab's 100-point score at this snapshot: 66; fatal flags: none (unchanged by this report)
- FACT: the lab's status: THESIS INVALIDATED

### Technical and chart thesis (the lab's)

- HEURISTIC: the lab's lifecycle label BROAD_ATTENTION and structure label UPTREND at this snapshot (rule labels, not a forecast)
- UNKNOWN: zones, levels and thesis text stay in the lab's token report

### Catalyst evidence

- FACT: exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): 0
- HEURISTIC: ticker or name links: 0; context only, never identity (PI-D-007)
- UNKNOWN: whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)

### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 8d4f5d8e101a |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 39b1f00fd34a |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | e158286f83ac |

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

- Request record df7057503e9c (request 6, pass c4177dd69a9a)
- T1 24 h: forecast `fc_85d9c112b8a290bfe1d59a4d49f2f6b9`, record 8d4f5d8e101a, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_6401689109b32e408eddf9028c5f6589`, record 39b1f00fd34a, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_f508499212bdcdfc84ead6a4199d95be`, record e158286f83ac, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_baton_Hg5Ja5.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

## Events not attempted

| Event | Exact chain:mint | Capture (UTC) | Covered by a report above | Request | Detail |
|---|---|---|---|---|---|
| DUPLICATE | `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump` | 2026-10-27T10:39:51Z | yes | 2c57ef475540 | none |
| DUPLICATE | `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` | 2026-10-27T10:39:51Z | yes | 2cb2c274c3f7 | none |
| DUPLICATE | `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3` | 2026-10-27T10:39:51Z | yes | d255a3cae67d | none |
| DUPLICATE | `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump` | 2026-10-27T10:39:51Z | yes | a9ecab925a8c | none |
| DUPLICATE | `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump` | 2026-10-27T10:39:51Z | yes | fe270ad5d2ec | none |
| DUPLICATE | `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR` | 2026-10-27T10:39:51Z | yes | 1270ce742bf5 | none |
| DUPLICATE | `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump` | 2026-10-27T10:39:51Z | yes | f97c528f3bf7 | none |
| DUPLICATE | `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW` | 2026-10-27T10:39:51Z | yes | 3ed37db76591 | none |
| DUPLICATE | `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump` | 2026-10-27T10:39:55Z | yes | 70746ca92d60 | none |
| DUPLICATE | `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` | 2026-10-27T10:39:55Z | yes | e7024422b2d0 | none |
| DUPLICATE | `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3` | 2026-10-27T10:39:55Z | yes | 51d47afc1f0b | none |
| DUPLICATE | `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump` | 2026-10-27T10:39:55Z | yes | 6d0ac5a17271 | none |
| DUPLICATE | `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump` | 2026-10-27T10:39:55Z | yes | 32b597d8961e | none |
| DUPLICATE | `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR` | 2026-10-27T10:39:55Z | yes | 35b878a384f8 | none |
| DUPLICATE | `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump` | 2026-10-27T10:39:55Z | yes | 51efc9b06f72 | none |
| DUPLICATE | `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW` | 2026-10-27T10:39:55Z | yes | 55529074f6ca | none |

## Units and times

- Times are UTC in ISO 8601 with Z. Ages are in minutes, hours or days as written. Horizons are in hours. Amounts are USD.
- Percentages appear only in target definitions (barriers) and in a verified FORECAST (point and interval, whole percents).
- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the JSON view has them in full).
- Buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), UNKNOWN (missing; earns nothing).

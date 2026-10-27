# Example reports (Phase 18, report-1 and alerts-rules-1)

Two kinds of example are here. The real ones come from the recorded runs at the repair code `31ada29` (CP18-2) on real data in a sandbox (the committed inbox bodies, the `71fc50e` state export, `unshare -n`): every real target abstains, so the real report shows no probability. The format-only ones come from fixture worlds (a fixture champion with a fixture calibration card, fixed clocks) and exist only to show the layout of a validated forecast; every one of them carries the line "FORMAT-ONLY FIXTURE: invented data, not a forecast". No fixture number is a research estimate.

Full files: `../real/REAL_SCOUT_REPORT.md`, `../real/REAL_REPLAY_REPORT.md`, `../real/REAL_ALERTS_SCOUT_DRY_RUN.txt`, `../real/REAL_ALERTS_REPLAY_DRY_RUN.txt`; golden fixtures in `tests/fixtures/predictive/phase18/golden/` (there an id that depends on the temporary test folder is written as a placeholder; below it reads temp-id). Rule matrix: `ALERT_RULE_MATRIX.md`. Missing data: `MISSING_DATA_UX.md`.

## How to produce them

```text
python -m memelab.predictive.reports report --state-dir STATE --config CONFIG [--lab-db LAB_DB] [--out FILE] [--json]
python -m memelab.predictive.reports alerts --state-dir STATE --config CONFIG [--alert-db DB] [--lab-db LAB_DB] [--as-of EPOCH]
python -m memelab.predictive.reports alerts-state --config CONFIG [--alert-db DB]
```

With `predictive.enabled` not the JSON value true, each command prints FLAG_OFF and writes nothing. An output path inside the repository is refused unless it is under `data/private/`. `--send` is refused: alerts are previews in a local outbox only.

## How to read them

- Order: at a glance, system status, target definitions, carried constraints, then one block per opportunity (identity and snapshot; the lab's structural research; the lab's technical labels; catalyst evidence; predictive research; historical prediction and its out-of-sample record; execution and stress; behavioral scenarios; sources and ids; limitations), then the events not attempted, then units and times.
- Every line is in one of the lab's buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), UNKNOWN (missing; it earns nothing). The renderer is the lab's own `memelab.report._ev`.
- Times are UTC in ISO 8601 with Z; alerts add the America/New_York local time. Ages are in minutes, hours or days; horizons in hours; amounts in USD. Percentages appear only in the target definitions (barriers) and in a verified FORECAST.
- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the `--json` view has them in full). Codes such as NO_ENTRY_AT_SHADOW_OR_ABOVE (no registry entry at SHADOW or above) and NO_TRADES_AFTER_ENTRY (a label outcome) are the registry's and the contract's frozen codes, not trade steps.
- Never shown: a probability, base rate, cohort number or reference-model number for an abstaining target; a number from a document that fails a check; a size; a trade step; a local path; token text carrying a trading or forecast word.

## Real report, sandbox scout state: at a glance

```text
## At a glance

- Probabilities shown: 0 of 24 target forecasts; abstentions 24; refused documents 0.
- No probability is shown: every target abstains or was refused. The reasons are named per target below.
- Reasons named across the targets: INSUFFICIENT_HISTORY 24, UNCALIBRATED 24, TARGET_NOT_FEASIBLE 6, SOURCE_STALE 24, MODEL_NOT_SELECTED 24.
- T1 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 8; with a veto: 3; snapshots verified against the lab database: 8 of 8; events not attempted: 16.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes and risk flags | Inputs |
|---|---|---|---|---|---|---|---|
| slopcannon | `solana:55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | WASH_TRADING_HIGH | INPUT_STALE |
| STONK | `solana:6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| DARK | `solana:7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| PAID | `solana:98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| GOMO | `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | CANNOT_EXIT_5K | INPUT_STALE |
| HIGGS | `solana:DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | WASH_TRADING_HIGH | INPUT_STALE |
| ZCAT | `solana:HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |
| baton | `solana:Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump` | 2026-10-07T00:16:35Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | INPUT_STALE |

```

## Real report: one opportunity with a fatal-flag veto (GOMO)

The inputs are the committed inbox bodies from 2026-10-07, so they are 20 days old at the capture (INPUT_STALE) and every target abstains SOURCE_STALE as well as MODEL_NOT_SELECTED, UNCALIBRATED and INSUFFICIENT_HISTORY. The request record line is left out here (its id changes with every run).

```text
## GOMO `solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump`

### Identity and snapshot

- FACT: exact identity solana:9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump; event DISCOVERY (first attempt for this chain and mint)
- FACT: snapshot 599dbfcdf78eba2e, row sha256 cffc92fbd52b2549
- FACT: decision time 2026-10-27T12:00:47Z (CAPTURE_TIME); capture 2026-10-27T12:00:47Z
- FACT: inputs observed 2026-10-07T00:16:35Z (collector-run start, PI-D-011); age at capture 20.5 days: INPUT_STALE
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
| T1 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 6ad536e47156 |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | dbc74ce04462 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | a399486d4dc7 |

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
- FACT: risks that override any forecast on this snapshot: fatal flags CANNOT_EXIT_5K
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

### Behavioral scenarios

- FACT: behavioral simulation SIMULATION_NOT_AVAILABLE: MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language model or Zep use is approved, so no simulation runs
- UNKNOWN: no behavioral scenario was run for this snapshot

### Sources and ids

- T1 24 h: forecast `fc_662a6b96fbb373e06e52aafcd6f4f1ee`, record 6ad536e47156, registry pin 7cb1c8b292f8, data none, features none
- T1b 6 h: forecast `fc_6282902f34d915a8a8206b7631d395c4`, record dbc74ce04462, registry pin 4efd53b196ee, data none, features none
- T2 24 h: forecast `fc_bab97c34063a433bdeccf952ad6d8b5b`, record a399486d4dc7, registry pin b9e82db1db19, data none, features none
- Token report: 20261007_0016_GOMO_9XKzy4.md (the lab's report of this snapshot; its sections are unchanged)

### Limitations

- Caveats: NO_HISTORICAL_EXECUTABLE_DEPTH, PRICE_PATH_NOT_PROCEEDS.
- Registered targets not attempted: `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH; `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION; `failed_breakout_6h` DEFERRED_PHASE_08; `catalyst_followthrough_24h_7d` BLOCKED_NO_DATA; `distribution_event_24h` BLOCKED_NO_DATA; `price_path_target_before_invalidation_7d` EXPLORATORY; `launch_cohort_collapse_24h` EXPLORATORY.
- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.

```

## Real dry-run alerts

On the scout state: no alert. The three tokens with a fatal flag are suppressed SOURCE_STALE (inputs from 2026-10-07); the report still shows the flags.

```text
Alert run 1 (dry_run), 2026-10-27 08:01 EDT (2026-10-27 12:01 UTC), policy predictive-alerts-policy-1 e2a17738fc6c
Outcome: evaluated
Candidates 0, new alerts 0, deduped 0, suppressed 3
No alerts today.
  suppressed risk_override slopcannon on solana (55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW): SOURCE_STALE (the inputs or the request are too old for an alert; the report still shows the flag)
  suppressed risk_override GOMO on solana (9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump): SOURCE_STALE (the inputs or the request are too old for an alert; the report still shows the flag)
  suppressed risk_override HIGGS on solana (DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump): SOURCE_STALE (the inputs or the request are too old for an alert; the report still shows the flag)
Dry run: previews only. Nothing was sent.

(no preview)
```

On the export-replay state, at its newest capture plus 60 s: 8 risk_override previews and 15 candidates suppressed SOURCE_STALE; no other policy fired because no target has a verified forecast. One preview:

```text
memelab predictive research alert, WARNING: risk override
symbol not verified on bsc (0x389cb330e4eaa0cce969759f01a416448fed6666)
Why: Risk flag on this snapshot: fatal flags TRANSFER_FEE_GT_5PCT, NO_SELL_ROUTE. No forecast clears it; the lab's fatal-flag override applies unchanged.
Evidence bucket: FACT
Forecasts on this snapshot: T1 24 h ABSTAIN; T1b 6 h ABSTAIN; T2 24 h ABSTAIN
Freshness: inputs observed 2026-10-26 06:09 EDT (2026-10-26 10:09 UTC), captured 2026-10-26 06:23 EDT (2026-10-26 10:23 UTC)
Contract: bsc:0x389cb330e4eaa0cce969759f01a416448fed6666
Sources: request d49b96e187e7, pass 9eb1f4ee36d1, snapshot 7c33bbc1b861a53f, records 5af891ad2ab5, ad11332004ef, 7ca6cf6e9919
Alert 1, dedupe a0cc13bfc0b0, policy predictive-alerts-policy-1 e2a17738fc6c, rules alerts-rules-1
Research only. Not a trade instruction, not a score, not a watchlist change.
----- alert_000002.txt
```

## Format-only: a hypothetical validated forecast and a strong forecast with an impossible exit

FXA is clean; FXC carries the fatal flag CANNOT_EXIT_5K. Both T1 attempts come from a fixture champion with a fixture SHADOW calibration card; the other targets abstain. FXA shows its fixture number; FXC shows FORECAST OVERRIDDEN and no number, because any risk flag (a veto, a liquidity fall of 20% or more, or liquidity that became unknown) overrides an estimate.

```text
## At a glance

- Probabilities shown: 1 of 6 target forecasts; abstentions 4; refused documents 0.
- Reasons named across the targets: INSUFFICIENT_HISTORY 4, UNCALIBRATED 4, MODEL_NOT_SELECTED 4.
- T1 24 h: registry CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T1b 6 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- T2 24 h: registry NO_VIABLE_CHAMPION, committed Phase 13 calibration UNCALIBRATED.
- Backtesting: BACKTEST_NOT_AVAILABLE. Behavioral simulation: SIMULATION_NOT_AVAILABLE.
- Opportunities: 2; with a veto: 1; snapshots verified against the lab database: 2 of 2; events not attempted: 0.

| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes and risk flags | Inputs |
|---|---|---|---|---|---|---|---|
| FXC | `solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32` | 2026-10-29T23:50:00Z | FORECAST OVERRIDDEN by risk (number withheld) FORMAT-ONLY FIXTURE | ABSTAIN (no number) | ABSTAIN (no number) | CANNOT_EXIT_5K | FRESH |
| FXA | `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS` | 2026-10-29T23:50:00Z | FORECAST 47% (41% to 65%) FORMAT-ONLY FIXTURE | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |

```

FXA, predictive research:

```text
### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | FORECAST 47% (41% to 65%) FORMAT-ONLY FIXTURE | none | support 60 calibration events (32 positive); base rate 29% | B2:price_path_target_before_invalidation_24h (sha 79cc70276e3d) | 2026-10-17T00:00:00Z | 2486c8e2362b |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 8d74b7461dd8 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | ea91e94aee17 |

- No probability for T1b 6 h, T2 24 h, from the abstention records: the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.
- T1 24 h (24 hours, +25% before -15%): research estimate at level SHADOW (VENN_ABERS), 47% with interval 41% to 65%; base rate 29%; support 60 calibration events; calibration card de11c57f1781; price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS). FORMAT-ONLY FIXTURE: invented data, not a forecast.
  - Caveats: PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, INTERVAL_EXCLUDES_UNMODELED_RISK, SHADOW_RESEARCH_ONLY, COHORT_ESTIMATE_NOT_TOKEN_HISTORY.

```

FXC, predictive research and execution: the veto overrides the estimate, the number is withheld, and the price path is not proceeds.

```text
### Predictive research

| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |
|---|---|---|---|---|---|---|---|
| T1 24 h | 24 hours | FORECAST OVERRIDDEN by risk (number withheld) FORMAT-ONLY FIXTURE | none | withheld: overridden by risk | B2:price_path_target_before_invalidation_24h (sha 79cc70276e3d) | 2026-10-17T00:00:00Z | 069a84021b5f |
| T1b 6 h | 6 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | 1177d10dd9b9 |
| T2 24 h | 24 hours | ABSTAIN (no number) | INSUFFICIENT_HISTORY, UNCALIBRATED, MODEL_NOT_SELECTED | not shown: no model selected | not_selected (sha none) | none | e05eeadef4d0 |

- No probability for T1b 6 h, T2 24 h, from the abstention records: the model has not reached SHADOW or VALIDATED_EXPERIMENTAL; no champion model exists for this target; no calibration of this model has passed the frozen check; too few out-of-sample outcomes to fit a calibration; too few independent outcomes to check a calibration; too few calibration outcomes near this model number.
- What would unblock each named reason:
  - INSUFFICIENT_HISTORY: at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set.
  - UNCALIBRATED: a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence.
  - MODEL_NOT_SELECTED: a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence.
- T1 24 h (24 hours, +25% before -15%): a verified research estimate exists for this snapshot (level SHADOW), but a risk overrides it (fatal flags CANNOT_EXIT_5K); the number is withheld and the lab's fatal-flag override applies unchanged. FORMAT-ONLY FIXTURE: invented data, not a forecast.
  - Caveats: PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, INTERVAL_EXCLUDES_UNMODELED_RISK, SHADOW_RESEARCH_ONLY, COHORT_ESTIMATE_NOT_TOKEN_HISTORY.

### Execution and stress

- FACT: fatal-flag veto: CANNOT_EXIT_5K; no forecast clears it
- FACT: backtest: BACKTEST_NOT_AVAILABLE (installed state BACKTEST_NOT_AVAILABLE)
- FACT: size basis EXECUTION_DATA_MISSING; depth COLLECTOR_NOT_AVAILABLE; size taken from a forecast: none
- FACT: price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS); a predicted price path never shows realizable exit
- FACT: risks that override any forecast on this snapshot: fatal flags CANNOT_EXIT_5K
- UNKNOWN: execution and stress assessment: BACKTEST_NOT_AVAILABLE; unblocked by the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; until then no execution or stress assessment exists
- UNKNOWN: exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it

```

FXC and FXA, dry-run alerts in a fixture run: the warning comes first; the re-evaluation notice for FXC is suppressed RISK_OVERRIDES_FORECAST; FXA gets a notice that may prompt re-evaluation only.

```text
----- alert_000001.txt
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
memelab predictive research alert, WARNING: risk override
FXC on solana (3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32)
Why: Risk flag on this snapshot: fatal flags CANNOT_EXIT_5K. No forecast clears it; the lab's fatal-flag override applies unchanged. The research estimate on this snapshot is overridden.
Evidence bucket: FACT
Forecasts on this snapshot: T1 24 h FORECAST; T1b 6 h ABSTAIN; T2 24 h ABSTAIN
Freshness: inputs observed 2026-10-29 19:50 EDT (2026-10-29 23:50 UTC), captured 2026-10-29 20:00 EDT (2026-10-30 00:00 UTC)
Contract: solana:3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32
Sources: request temp-id, pass 1a5e8693623a, snapshot cc7aac863600b9c0, records 069a84021b5f, 1177d10dd9b9, e05eeadef4d0
Alert 1, dedupe 2d31d9709707, policy predictive-alerts-policy-1 e2a17738fc6c, rules alerts-rules-1
Research only. Not a trade instruction, not a score, not a watchlist change.
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
----- alert_000002.txt
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
memelab predictive research alert, NOTICE: reevaluate
FXA on solana (Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS)
Why: A verified research estimate (SHADOW) for 24 hours, +25% before -15%: 47%, interval 41% to 65%, above the base rate 29%. It may prompt re-evaluation only; it changes no score, status or list. Price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS).
Evidence bucket: INFERENCE
Forecasts on this snapshot: T1 24 h FORECAST; T1b 6 h ABSTAIN; T2 24 h ABSTAIN
Freshness: inputs observed 2026-10-29 19:50 EDT (2026-10-29 23:50 UTC), captured 2026-10-29 20:00 EDT (2026-10-30 00:00 UTC)
Contract: solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS
Sources: request temp-id, pass 1a5e8693623a, snapshot fe7ebe35903b3f49, records 2486c8e2362b, 8d74b7461dd8, ea91e94aee17
Alert 2, dedupe 1a3f8c86765d, policy predictive-alerts-policy-1 e2a17738fc6c, rules alerts-rules-1
Research only. Not a trade instruction, not a score, not a watchlist change.
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
Alert run 1 (dry_run), 2026-10-29 20:01 EDT (2026-10-30 00:01 UTC), policy predictive-alerts-policy-1 e2a17738fc6c
FIXTURE DEMO: invented data, not live alerts.
Outcome: evaluated
Candidates 2, new alerts 2, deduped 0, suppressed 1
  suppressed reevaluate FXC on solana (3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32): RISK_OVERRIDES_FORECAST (the snapshot carries a risk: the risk warning stands instead)
Dry run: previews only. Nothing was sent.
```

## Format-only: a withdrawn forecast

The fixture champion is rolled back; the next attempt of FXA abstains, and the alert says the earlier estimate is withdrawn.

```text
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
memelab predictive research alert, NOTICE: forecast withdrawn
FXA on solana (Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS)
Why: The research estimate for T1 24 h shown at the previous attempt is withdrawn: the target now shows ABSTAIN (INSUFFICIENT_HISTORY, UNCALIBRATED, SOURCE_STALE, MODEL_NOT_SELECTED).
Evidence bucket: FACT
Forecasts on this snapshot: T1 24 h ABSTAIN; T1b 6 h ABSTAIN; T2 24 h ABSTAIN
Freshness: inputs observed 2026-10-29 20:50 EDT (2026-10-30 00:50 UTC), captured 2026-10-29 21:00 EDT (2026-10-30 01:00 UTC)
Contract: solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS
Sources: request temp-id, pass eaf658683d84, snapshot 8bff908229fd15d2, records 654a9980749f, 53d776c7135a, bc0922e13ab5
Alert 2, dedupe 08b2ac79e52c, policy predictive-alerts-policy-1 e2a17738fc6c, rules alerts-rules-1
Research only. Not a trade instruction, not a score, not a watchlist change.
FORMAT-ONLY FIXTURE: invented data, not a forecast; not a live alert.
```

## Format-only: a forged number is refused

An adversary edits the FORECAST probability of FXA and re-seals every record id, file sha and the pass chain, so the state still loads; the request record still holds the point recomputed from the raw number. The report refuses the document and shows no number.

```text
- Reasons named across the targets: INSUFFICIENT_HISTORY 4, UNCALIBRATED 4, MODEL_NOT_SELECTED 4, DOCUMENT_REFUSED 1.
| FXA | `solana:Ebjh5RZR799aVdZR9yePMNmEVmGibvjM3Zqr4kEegSbS` | 2026-10-29T23:50:00Z | REFUSED (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| T1 24 h | 24 hours | REFUSED (no number) | DOCUMENT_REFUSED | not shown | not shown | not shown | none |
- T1 24 h (24 hours, +25% before -15%): DOCUMENT_REFUSED: the document failed a check: it is not shown and no number is shown. Failed checks: probability differs from the point stored with the raw number.
```

## Format-only: token text that tries to inject

Symbols BUY-NOW, "## 99% chance", a|b|c, a symbol with a line break, a local path, a script tag and pump.fun; the first token's lab status is NEAR ENTRY. Symbols with a trading or forecast word are withheld; the rest are reduced to letters, digits, dot, dash and underscore; the lab status with trade wording is not printed. Since CP18-2 the check runs on the joined letters of the token text, so run-together forms such as SELLNOW, BUYNOW, TAKEPROFIT and 100X are withheld too (tests m4 in tests/test_predictive_reports.py).

```text
| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes and risk flags | Inputs |
|---|---|---|---|---|---|---|---|
| tmpevilpath | `solana:38ihiGtLeQoTqTGHbosHcWftMxpeP88saUmFScXqJWZf` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:6pi28KYmyz5GvN5WSo91ugA8JqMhWXVwK2ktjXxho4Qa` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:82TeexxktGLaL7532BoZC7thAaGh691iCQ7TaS42YYu` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| withheld | `solana:9evwDxCiNAaszjuP581MoGjR9dcaof6n6MRyp5KazkUe` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| line1line2 | `solana:EkwEd3uGWATNPVdSY4qwVABzUjqR1WtQsFzZagBmU8b6` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| abc | `solana:HNm7ydhn1jE22tyFmkyZkQRtPUUXrV4QqNBaCoYzRNec` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
| scriptxscript | `solana:JEEoMXjzYnyE6rsPz8XxC84DcZHJoHVBcBjbXjEcaUrP` | 2026-10-27T07:50:00Z | ABSTAIN (no number) | ABSTAIN (no number) | ABSTAIN (no number) | none | FRESH |
- UNKNOWN: the lab's status: kept in the lab's token report (its label uses trade wording)
```

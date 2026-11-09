# Model limits and out-of-sample evidence

What the engine can and cannot say on 2026-11-09, with the file behind each statement. Nothing here is a claim of skill, edge, calibration or profit. Paths are relative to `audits/predictive-intelligence/`.

## What is deployed

- The deployed state is the registry (`phase_16/registry/`, read through `memelab/predictive/registry.py`, registry-1). It holds 69 entries. Every primary target is pinned NO_VIABLE_CHAMPION; B0 (training base rate) and B2 (simple logistic on as-of liquidity, volume, age and lab risk flags) are references only (ABSTAIN, REFERENCE_ONLY_NEVER_PUBLISHED); every other card is NO_GO. Source: `phase_16/registry/REGISTRY_LOG.jsonl` (75 events), `phase_16/PHASE_16_EVIDENCE.md`, PI-D-085, PI-D-087.
- Every forecast document the engine writes is ABSTAIN. No probability is shown for any target. Source: `phase_21/evidence/release_checks/e2e/smoke_summary/REAL_PATH_SMOKE.json` (this phase, 24 documents, 0 forecast lines) and `phase_18/` reports.
- At 2026-11-09 every one of the 69 entries is MODEL_STALE (frozen cutoff 2026-10-17T00:00:00Z, stale after 2026-10-31T00:00:00Z) and no target resolves to a champion: `phase_21/evidence/release_checks/chronology_audit.json` (C1) and `phase_21/evidence/doc_commands/docs_demo.json`.
- No ensemble (NO_ENSEMBLE for all three targets, `phase_16/ensemble/ENSEMBLE_ABLATION.json`).

## Targets (frozen, `phase_01/architecture/TARGET_REGISTRY.md`)

| Short | Name | Question |
|---|---|---|
| T1 | `price_path_target_before_invalidation_24h` | does the 5-minute price path touch +25% before -15% within 24 h after entry? |
| T1b | `price_path_target_before_invalidation_6h` | the same within 6 h |
| T2 | `price_path_severe_drawdown_or_halt_24h` | within 24 h, does the price fall to half, or does trading stop and stay stopped (confirmed over 48 h)? |

These are price-path events on vendor candles. None of them is a profit, a fill or an exit: historical executable depth does not exist (NO_HISTORICAL_EXECUTABLE_DEPTH, EXECUTION_DATA_MISSING).

## Out-of-sample evidence, per target

| Evidence | T1 24 h | T1b 6 h | T2 24 h | File |
|---|---|---|---|---|
| Retrospective holdout 2026-10-17 to 10-24 (opened once, now spent, PI-D-065): B2 against B0 | NOT_DISTINGUISHABLE_FROM_BASE_RATE (66 rows, 15 events, BSS -0.024) | NOT_DISTINGUISHABLE_FROM_BASE_RATE (68, 12, -0.083) | INSUFFICIENT_EVENTS (59, 7, +0.292, 7 below the minimum 10) | `phase_12/validation/FINAL_HOLDOUT_RESULTS.md`, `PRIMARY_RESULTS.json` |
| Selection correction over the search (N_search 130, sensitivity 169) | no row survives | no row survives | no row survives | `phase_12/validation/FULL_EXPERIMENT_LEDGER_CORRECTED.csv`, `phase_16/experiments/SEARCH_LEDGER.csv` |
| Calibration | UNCALIBRATED (no chronologically valid set reaches the gate) | UNCALIBRATED | UNCALIBRATED | `phase_13/artifacts/<target>/CALIBRATION_CARD.json`, PI-D-069 |
| Prospective window 2026-10-24 to 10-26 (frozen cards, predictions committed before any label read) | INSUFFICIENT_DAYS (22 rows, 5 events, 3 days) | INSUFFICIENT_DAYS (24, 3, 3 days) | INSUFFICIENT_DAYS (15, 3, 2 days; 7 more PENDING, see below) | `phase_19/monitoring/PRIMARY_RESULTS.json`, `PROSPECTIVE_REPORT.md` |
| Sensitivity (seed, mint grouping, first and last day dropped, route, static baselines) | no reading gives a lower bound above 0 | the same | the same | `phase_20/evidence/oos_sensitivity.json`, rerun in this phase: `phase_21/evidence/release_checks/oos_sensitivity.json` |
| Independent recalculation (own code, no lab module) | 61 of 61 Phase 19 outcomes, 40 of 40 Phase 06 labels, 168 of 168 reference numbers, 2 real traces | | | `phase_20/evidence/independent_recalc.json`, rerun: `phase_21/evidence/release_checks/independent_recalc.json` |

The minimums that a claim needs (frozen in Phase 01 ACCEPTANCE): at least 5 decision days, at least 50 events with 10 per class per target, a lower confidence bound above 0 after the selection correction. No target meets them. The B2 against B0 point estimates above are descriptive and must not be cited as skill.

## The 7 PENDING T2 outcomes

The 7 T2 outcomes of the 2026-10-26 decisions matured on 2026-10-28 at 10:43Z. The frozen Phase 19 commands were run on 2026-11-09 (`phase_21/evidence/maturity/`): `fetch_labels.py fetch` planned 0 new reads, because every one of the 28 planned decisions already has a mapped read (taken at the T1 boundary), and `run_prospective.py outcomes` appended 0 entries. The 7 stay PENDING. Maturing them needs a change to `fetch_labels.py` (re-read a mapped decision whose read ends before a newly matured target's boundary), which is a code change under change control and was not made (open item OI21-1). It cannot change a verdict: T2 would have at most 3 decision days, below the minimum of 5.

## Limits that no setting removes

- Three prospective decision days and about 30 Solana decisions; one regime label in development (QUIET, RISK_OFF); no crash day. No regime or cohort claim is possible (P21).
- EVM decisions are out of scope (OUT_OF_SCOPE_CHAIN); Solana only.
- Catalyst and social tables are not exported to any store this engine reads (CATALYST_TABLES_NOT_EXPORTED, SOCIAL_TABLES_NOT_EXPORTED): no catalyst or social forecast exists.
- No forward depth data (COLLECTOR_NOT_DEPLOYED): every size or exit question is EXECUTION_DATA_MISSING.
- Backtesting is not merged on this branch: BACKTEST_NOT_AVAILABLE; no combined prediction plus stress result exists (`phase_17/integration/REQUEST_FLOW.md`).
- Behavioral simulation: MIROFISH_NO_GO, INSUFFICIENT_VALIDATION (0 eligible independently dated catalyst events; `phase_15/PHASE_15_EVIDENCE.md`, PI-D-081). The module stays OFF and research-optional; with it unavailable the core runs unchanged (SIMULATION_NOT_AVAILABLE, P30).
- The persisted state is hash-chained, not signed: a coordinated rewrite of inputs, numbers and documents with a reseal is caught only by a signature (no key approved, PI-D-005).
- A flag-on run makes no vendor call: a reference-price read happens only for a served champion (none exists) and the scout and analyze hooks pass no reader; eligibility is NOT_ASSESSED, or INPUT_STALE for inputs older than 2 hours.

## Release reading (NO_GO_DECISION_TREE)

- Complex model does not beat prevalence or the simple logistic: NO_INCREMENTAL_PREDICTIVE_EDGE; ship the abstention engine.
- No historical executable depth: no net trading claim (NO_NET_TRADING_EDGE is not even testable).
- MiroFish weak or unscorable: MIROFISH_NO_GO, OFF.
- Backtesting not installed: BACKTEST_NOT_AVAILABLE.
- Paid LLM, Zep or robots blocked: optional module OFF.

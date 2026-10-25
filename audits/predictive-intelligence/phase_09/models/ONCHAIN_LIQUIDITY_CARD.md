# On-chain, liquidity and authority model card (Phase 09)

Status: PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046), `revision_check_claimed: false`. Every model here is MODEL_NOT_PROMOTED. No number is a published probability. Research only: no forecast is an order, a size or a profit claim.

Pre-registration: `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-054 in `3079af1` (22:37:55Z), before any on-chain feature on a labelled row and before any fit. Code `15bc5b5` (22:54:36Z), runner repairs `a52233c` and `18bd243`; recorded run 3 at `18bd243` from 22:57:03Z (`evidence/run_log.json`).

## Honest data sufficiency (the gate of this phase)

| Question the phase asks | Answer on the lab's data |
|---|---|
| Historical pool reserves or executable depth at the decision or later | None after 2026-10-08 (Phase 00); backtesting PROVENANCE.md: reserves, ticks, bins and LP changes SOURCE_BLOCKED. Never substituted by a modern quote |
| Historical sell quotes at a size | None for these decisions (the lab DB holds 498 quotes of 33 thesis rows read 2026-10-06 to 07, before the development decisions) |
| Forward depth and quotes | Approved (PI-D-044), collector pushed on `feature/backtesting`, not deployed: 0 rows. This checkout: COLLECTOR_NOT_AVAILABLE (`evidence/collector_state.json`) |
| Swaps, wallet flows, creator transfers, holder history | Not exported after 2026-10-07; wallet history SOURCE_BLOCKED; the lab DB's 3,774 swaps of 6 mints (Oct 5 to 7) carry 10-character signature prefixes only |
| Authority, Token-2022, transfer fee, LP risk and lock, holder concentration, clusters, wash level, route at the decision | Yes: the lab's own readings inside every exported thesis and token row, available at the export commit (PI-D-015). These are onchain-1 |
| Can `liquidity_drawdown` or exit capacity be labelled | No. Both stay DEFERRED_FORWARD_COLLECTION and BLOCKED_NO_HISTORICAL_DEPTH; proposals only (`LIQUIDITY_TARGET_PROPOSALS.md`), adapter tested on fixtures (TEST_ONLY) |
| Can `distribution_event` be labelled | No (BLOCKED_NO_DATA): no swap history with wallet roles exists for the decisions; requirements and the movement rules are written and fixture-tested |
| Which frozen targets can use on-chain inputs | T2 (half the price or a halt in 24 h), T1 and T1b, as price-path targets; none carries size, depth or proceeds (PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH) |

## Feature set onchain-1 (`memelab/predictive/onchain.py`)

25 values per decision from the decision row and the previous decision of the same chain and mint, read through `features.AsOfView.decisions_of` at the decision time (audited); availability = the export commit of the row read; evidence LAB_RECORDED; every missing reason AS_OF. Definitions in `ACCEPTANCE_CHECKLIST.md`; feature-set sha in `evidence/run_log.json`.

Real coverage (925 Solana decisions of the Phase 05 store, 17 decision days, `experiments/PARSE_COVERAGE_BY_DAY.csv`): 0 UNPARSEABLE values (every rationale line of every day matched a known m24 format), 0 INCONSISTENT_TIME rows. Among the 240 labelled development decisions (`experiments/ONCHAIN_FEATURES_DEVELOPMENT.csv`, `ONCHAIN_COVERAGE.csv`):

- structural fatal flag 65, distribution flag 24, no sell route 4; LP risk LOW 46, MODERATE 108, HIGH 86; Token-2022 148, SPL 91, unknown 1;
- mint authority active 0 and freeze authority active 0 (no variance: the authority features cannot inform any model on this data), authority switch 0 of 137 decisions with a previous one;
- every model's required inputs are present on every labelled row (131 of 131 T2, 136 of 136 T1, 224 of 224 T1b); optional gaps: LP lock 6, exit share 10 to 13, largest holder 2; change features need a previous decision (35 of 131 on T2);
- capture delay (decision time minus the snapshot's own collector time): median 1,046 s, 90th percentile 2,523 s, maximum 77,840 s (21.6 h): the on-chain reading behind a decision is not fresh; it is the reading the lab had.

Version 2 consistency: adjusted top-10, ln(1 + liquidity) and ln(1 + exit capacity) equal the stored snapshots on 240 of 240 decisions (`evidence/v2_consistency.json`).

## Models and results (development, retrospective, provider mode)

Folds are Phase 07's (split fingerprints equal; B0 and B2 out-of-sample numbers equal at 6 decimals on 76 of 76 rows, `evidence/phase07_equality.json`). Unlike Phase 08, every on-chain model passes the training gate in every fold (inputs exist on every row): T2 1 fold (104 training rows, 27 positive), T1 3 folds, T1b 5 folds (`evidence/folds.json`). The binding limit is the out-of-sample set: T2 8 rows with 1 positive on 1 day, T1 24 with 8 on 3 days, T1b 44 with 3 on 5 days.

| Target | Model | Reference | Rows | Positives | Days | Brier | Brier ref | Skill | Mint interval | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| T2_24h | R1_OC_RULE | B0 | 8 | 1 | 1 | 0.125 | 0.127 | 0.016 | -0.112 to 0.308 | INSUFFICIENT_DAYS |
| T2_24h | M1_OC_LOGIT | B0 | 8 | 1 | 1 | 0.109 | 0.127 | 0.143 | -0.121 to 0.738 | INSUFFICIENT_DAYS |
| T2_24h | M2_OC_LOGIT_B2 | B0 | 8 | 1 | 1 | 0.131 | 0.127 | -0.031 | -1.484 to 0.857 | INSUFFICIENT_DAYS |
| T2_24h | M3_OC_LOGIT_TREND | B0 | 8 | 1 | 1 | 0.184 | 0.127 | -0.442 | -1.752 to 0.991 | INSUFFICIENT_DAYS |
| T2_24h | M2_OC_LOGIT_B2 | B2 | 8 | 1 | 1 | 0.131 | 0.153 | 0.138 | -0.399 to 0.193 | INSUFFICIENT_DAYS |
| T2_24h | M1_OC_LOGIT | R1_OC_RULE | 8 | 1 | 1 | 0.109 | 0.125 | 0.130 | -0.256 to 0.685 | INSUFFICIENT_DAYS |
| T2_24h | M2_OC_LOGIT_B2 | R1_OC_RULE | 8 | 1 | 1 | 0.131 | 0.125 | -0.048 | -1.355 to 0.793 | INSUFFICIENT_DAYS |
| T1_24h | R1_OC_RULE | B0 | 24 | 8 | 3 | 0.225 | 0.230 | 0.021 | -0.010 to 0.053 | INSUFFICIENT_DAYS |
| T1_24h | M2_OC_LOGIT_B2 | B0 | 24 | 8 | 3 | 0.245 | 0.230 | -0.068 | -0.365 to 0.176 | INSUFFICIENT_DAYS |
| T1_24h | M2_OC_LOGIT_B2 | R1_OC_RULE | 24 | 8 | 3 | 0.245 | 0.225 | -0.092 | -0.404 to 0.167 | INSUFFICIENT_DAYS |
| T1b_6h | R1_OC_RULE | B0 | 44 | 3 | 5 | 0.068 | 0.067 | -0.027 | -0.210 to 0.050 | INSUFFICIENT_EVENTS |
| T1b_6h | M2_OC_LOGIT_B2 | B0 | 44 | 3 | 5 | 0.065 | 0.067 | 0.018 | -0.443 to 0.203 | INSUFFICIENT_EVENTS |
| T1b_6h | M2_OC_LOGIT_B2 | R1_OC_RULE | 44 | 3 | 5 | 0.065 | 0.068 | 0.044 | -0.253 to 0.199 | INSUFFICIENT_EVENTS |

Every comparison, view and reference is in `experiments/ONCHAIN_METRICS.csv` (252 model rows plus 18 NC1-OC rows); every verdict there is INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS. Reading: no on-chain model can be called better or worse than the base rate, than B2 or than the simple on-chain rule. The positive point skills on T2 (M1 0.143 over 8 rows with 1 positive) are the arithmetic of one event on one day, not skill. A1 (B2 on M2's rows) equals B2 on every row because M2's rows are B2's rows; M2 against A1 is therefore the same comparison as M2 against B2. NC1-OC (shuffled labels, 20 seeds): mean skill -0.119 (T2), -0.160 (T1), -0.132 (T1b), uninformative under `nc1_verdict` at this size.

## Model against the simple on-chain rules (`experiments/RULES_VS_MODEL.csv`, `EARLY_WARNING.csv`)

R0, the hard structural veto read as an alarm (no probability), on the out-of-sample rows: T2 0 hits, 1 miss, 1 false alarm, 6 correct rejections; T1 3 hits, 5 misses, 6 false alarms, 10 correct rejections (lead times 1.2 h, 3.4 h, 11.8 h); T1b 2 hits, 1 miss, 16 false alarms, 25 correct rejections. Every count is below 20 events per cell: counts only, no rate. Every alarm is raised at the decision, before the label window opens (checked: a negative lead time raises). False alarms are counted, not priced: the targets carry no size, so no money value exists for them. Misses are the unseen risks: on T2 the one event out of sample had no structural flag. Cohort tables by route, liquidity, launch age, token program, LP risk, structural flag, week and day are in `EARLY_WARNING_COHORTS.csv`.

## Execution-risk semantics (phase step 5)

- `onchain.decision_support` places a forecast beside the lab's fatal flags: every fatal flag is a veto (the existing overrides), structural ones listed apart, and `veto_overrides_forecast` is true whenever a flag is present or the flag list is unreadable (VETO_UNKNOWN is not a pass). The forecast is not an input to the veto (tests with probabilities 0.001 to 0.999, mutation "forecast clears the veto" caught).
- `onchain.size_cap_usd` comes from depth only: the largest quoted size whose OK sell quote returns at least 1 - max_loss of the size; no quote gives EXECUTION_DATA_MISSING (P44). It has no probability argument (test), so a classifier cannot raise or lower it. On this data every decision is EXECUTION_DATA_MISSING.
- Reported liquidity is not exit capacity (P08): `oc_exit_cap_share` keeps them apart; the adapter labels reserves REPORTED_RESERVE_NOT_EXIT_CAPACITY and never computes proceeds from them.

## Real cross-checks (`evidence/crosschecks.json`)

- Authority: the lab DB's 33 authority reads (8 mints, Oct 6 to 7, source merged) and the nearest later export decision agree on mint and freeze authority 33 of 33 (all revoked). They disagree on the token program for one mint (`6GmAFSYs...`, 5 reads): the lab DB says Token-2022, the export's token row says SPL Token. Both are the lab's own records; which is right is UNKNOWN without a chain read. `oc_token2022` enters no model.
- Swaps against movements: all 3,774 lab DB rows are GeckoTerminal trades (buy 2,018, sell 1,756), i.e. swaps against a pool, none a transfer. Summed per 5-minute bucket against the decision pool's candles: one mint agrees (median ratio 1.007, 5 of 5 buckets within 10%); four mints show ratios of 0.13 to 0.70 and one has no point-in-time pool. The trades' pool is not recorded and these mints have 4 to 18 pools on several DEXes, so the gap is consistent with venue fragmentation (P02) and with the trades endpoint returning only the latest trades of one pool. No signature is complete (10 characters), so no transaction is verified on chain; this is the closest real historical example available.
- Holder classes: 19 lab-classified exchange holders (MEXC, Gate.io) map to CUSTODY_OR_EXCHANGE with insider false, 0 with the lab's insider flag (P19).
- Developer wallets: of 186 token rows with a dev wallet, one (`55Vr2VpS...`) names `HBYzRF...pump`, an address with the pump.fun mint suffix: DEV_LABEL_SUSPECT, not an observed developer (the developer-wallet misclassification case).

## Traps and checks (`evidence/traps.json`, `trace/`, `sklearn_crosscheck.json`, `mutation_onchain.json`, `determinism.json`)

NC2-OC (the next decision's value of the same mint, declared at its availability) refused 170 of 170 by the allowlist and 170 of 170 by `validate_rows`; P13-OC 15 of 15 holdout-start cards refused on a development decision; P36-OC a snapshot time 60 s after the decision refuses all 25 values; CX-09 a collector read captured 420 s after the decision is not visible at the decision and refused as a feature (fixture, TEST_ONLY). Forecast trace (T2, decision `6070e736...`, mint `2j5SaS7x...`, 2026-10-14T10:17:43Z) recomputed independently: 25 values, 13 inputs, 7 model numbers, 0 differences; four invalid inputs refused. Oracle: newton-cholesky within 1.75e-11 on 48 real logistic designs (folds and holdout cards), `stats.Prep` within 5.8e-15. Mutation probe 55 of 55 caught. Two runs: identical except the run log and the trace's latency field.

## Frozen for Phase 12

R1, M1, M2, M3 and A1 per primary target, trained through the gate on all development labels as of 2026-10-17T00:00Z (`artifacts/<target>/`, all fitted: T2 131 rows with 28 positive, T1 136 with 34, T1b 224 with 26). MODEL_STALE after 2026-10-31. The cumulative search ledger for Phase 12 is `experiments/SEARCH_LEDGER.csv` (Phase 08's rows first, then Phase 09's, including three real-data debug runs).

## Limits

The on-chain readings are the lab's module outputs at its collector time, not chain reads at the decision; rationale text is version dependent; authority features have no variance in development; T2 has one out-of-sample day; every result is provisional until Phase 06's 48 h re-read; the adapter, the proposals and the movement rules are fixture-only (TEST_ONLY) until forward rows exist.

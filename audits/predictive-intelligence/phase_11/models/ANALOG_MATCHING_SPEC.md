# Analog matching spec (analog-1)

Phase 11 deliverable (repaired in pass 2 after the independent skeptic, PI-D-063). Code: `memelab/predictive/analog.py` (numpy and the standard library, flag OFF, imported by no existing module). Tests: `tests/test_predictive_analog.py` (63). Pre-registration: `../ACCEPTANCE_CHECKLIST.md`, `../experiments/EXPERIMENT_REGISTRY.csv`, PI-D-061 (commit `46afc85`, before any cohort on a labelled row). Frozen code: `0482a60`, repaired at `b0fbf80`. Recorded run: `../probes/run_analog.py` at `b0fbf80`.

Everything here is research only. A cohort number is never a published probability: it carries `publishable: false`, the label COHORT_ESTIMATE_NOT_TOKEN_HISTORY, NO_HISTORICAL_EXECUTABLE_DEPTH and PRICE_PATH_NOT_PROCEEDS, and in a forecast document it is an ABSTAIN with UNCALIBRATED and MODEL_NOT_SELECTED.

## What an analog is

| Rule | Implementation | Why |
|---|---|---|
| Pool at `as_of` = exactly the rows `labels.training_labels(dev, as_of, target)` gives, joined by `baselines.join` | `run_analog.aex_at`, `analog.check_pool` | labels decided before and matured by `as_of`; no outcome a decision could not know (P05, P43) |
| Each pool row decided before `as_of`, label matured by it, token first seen by it | `check_pool` raises FutureUniverseError | future-issued tokens and future labels never enter (P43, NC2-AC) |
| Every input available at its own decision | `check_asof` through `features.validate_rows` | P36 |
| No current token list, vendor list or later export | the module has no such input; tests check the signature | survivorship (P09) |
| Same chain and exact mint = token history, never an analog | `_excluded`, `token_history` | similarity is never identity (P01) |
| Every row in a group that holds the target's mint or the target's creator wallet is excluded | `_excluded` over `groups` | same-deployer leakage (P14), over every creator ever recorded for the mint |
| One analog per group: a group is a connected component over (chain, mint) and every creator wallet recorded for that mint in the pool (union-find), so a mint whose rows carry different creator values is one group | `groups`, `regroup`, `KnnIndex.nearest_clusters`, newest row per group in AC1 | an analog is an independent token or deployer, not a duplicate window (CX-S11: the first pass keyed each row by its own creator field and could count one mint twice) |
| Leave one campaign out (same narrative tag) | `select(..., loco=True)` | sensitivity |

## Cohort models

| Id | Selection | Out of distribution |
|---|---|---|
| AC1_STRATA | the cell (launch age bucket, liquidity bucket) of `labels.cohort_of` at the decision; newest row per cluster | target bucket UNKNOWN (MISSING_INPUT); empty cell (CELL_UNSEEN) |
| AC2_KNN | 30 nearest clusters; distance over z-scored ln(1 + liquidity), ln(1 + market cap), ln(1 + 24 h volume), ln(1 + token age in days) (pool mean, population sd, sd 0 counts 1) plus 1 per mismatch of launchpad class (PUMP_FUN, OTHER_LAUNCHPAD, NONE_RECORDED) and token program (`oc_token2022`); Euclidean; ties by decision key | missing target input (MISSING_INPUT); K-th distance above the 95th percentile of the pool rows' own K-th other-cluster distances (FAR_FROM_ANALOGS) |
| AC3_KNN_REGIME (primary) | AC2 restricted to pool rows whose own regime label equals the target's label at T | WARMUP or UNKNOWN target regime (REGIME_UNKNOWN); no pool row in that label (REGIME_UNSEEN); OOD threshold from the restricted pool |

Gates after selection: the pool passes the training gate (100 events, 20 per class) else INSUFFICIENT_HISTORY; G (distinct groups among the analogs; not an effective sample size) at least 20 and analog days at least 5, else ANALOGS_TOO_FEW. Number = (analog positives + 20 x pool prevalence) / (G + 20); raw rate and Wilson 95% interval on G beside it; older and newer halves of the analogs with Wilson intervals, TIME_UNSTABLE when they do not overlap. Beside G every answer reports the pool's day ICC (one-way ANOVA of the pool labels by decision day), the design-effect N `n_eff_icc = G / (1 + (G / day Kish ESS - 1) x ICC)` and a Wilson interval on it; the Wilson interval on G assumes independent analogs and says so. No gate uses the ICC N.

## Regime label at T

From the Solana decisions visible at T (decision time and availability at or before T): activity = median ln(1 + 24 h volume) and tone = share of constructive lab statuses (WATCH, SETUP DEVELOPING, NEAR ENTRY, ENTRY CONDITIONS MET) of the decisions in (T - 24 h, T]; each compared with the median of the same quantity over the export instants strictly before T. Labels ACTIVE or QUIET by RISK_ON or RISK_OFF; WARMUP with fewer than 5 earlier export instants. Every record carries CHAIN_WIDE_DATA_NOT_AVAILABLE and CATALYST_TABLES_NOT_EXPORTED. `regime_as_of` raises LeakageError on any later row; `regime_series` equals `regime_as_of` on the rows visible at each instant (checked at all 79 development instants). Activity is a lab-universe proxy (what the lab exported), not a chain-wide market measure.

Counterexample CX-11 (`regime_full_sample`, a trap kept for tests only): full-sample medians relabel 32 of the 74 non-warmup development instants and fail the truncation check at 37 instants.

## Router

`cohort_forecast`: TOKEN_HISTORY when at least 20 matured rows of the exact mint exist (none in development); else the AC3 cohort, labelled COHORT_ESTIMATE_NOT_TOKEN_HISTORY with `new_mint`; else ABSTAIN with TOKEN_HISTORY_TOO_SHORT and AC3's reasons. A position size calls `onchain.size_cap_usd` and, with no quotes, adds EXECUTION_DATA_MISSING (P44). With a cohort number, the divergence flags are added.

## Divergence flags (phase prompt step 5)

For the target against its selected analogs: `OC_MINT_AUTHORITY_ACTIVE`, `OC_FREEZE_AUTHORITY_ACTIVE`, `OC_TRANSFER_FEE_PRESENT`, `OC_TOKEN2022` give `_DIFFERS_FROM_ANALOGS` when fewer than half of the analogs with a known value share the target's value, `_UNKNOWN` when the target's value is missing; `oc_exit_cap_share` and `oc_round_trip_friction_pct` outside the analogs' 10th to 90th percentile give EXIT_CAP_SHARE_DIFFERS and FRICTION_DIFFERS. No historical executable depth exists (NO_HISTORICAL_EXECUTABLE_DEPTH on every answer); the exit-capacity share is the lab's stale snapshot context, not depth at the decision. On the recorded run the flags appear on many answers (`../experiments/DIVERGENCE_FLAGS.csv`): see the file for the counts of the repaired run.

## Reproducible cohort query

```
python -B audits/predictive-intelligence/phase_11/probes/cohort_query.py --target T1_24h --decision-key <key> --as-of 2026-10-15T00:00:00Z
```

Builds the pool exactly as the runner does and prints every model's answer (analogs with distances, G, days, day Kish ESS, number or states), the router's answer and the divergence flags; the decision's own label is never printed. `../probes/postrun_checks.py` shows it reproduces the three traced answers and every AC2 and AC3 number in `OOS_PREDICTIONS.csv`.

## Limits

- Development covers 9 to 10 decision days, and the export instants cluster on 2026-10-08 to 10-10 (hourly exports). The analogs of an out-of-sample decision come from few days: of 92 answers with a number, 58 have a day Kish ESS below 5 and the largest single-day share reaches 63% (`../evidence/postrun_checks.json`). The frozen rule counts days (at least 5), not the day Kish ESS; G (groups) overstates independence when days are batched; the ICC N is below 20 for 8 of them (all T1b AC2, minimum 15.7).
- 115 of 925 Solana decisions have no creator in their token row; a group joins only the creators that were recorded, so a deployer never recorded is not caught. Dev wallets are not used.
- Regime labels rest on the lab's own exports and statuses (version dependent, PI-D-008); the expanding median is dominated by the hourly export days, and the activity half also moves with the lab's decision mix (first decisions of a mint are 11% of the hourly days and 60% of the daily days, with lower volume). ACTIVE/QUIET and RISK_ON/RISK_OFF are lab-universe names, not market risk appetite.
- No historical depth, quotes or chain-wide data exist; no catalyst row exists (PI-D-058).

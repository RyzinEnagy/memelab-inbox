# Technical model card (Phase 08)

Status of every number here: PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Phase 06's frozen 48 h revision re-read has not run; if it changes any development label, `../probes/run_technical.py` is rerun at the Phase 08 code (`d9b2a9c`) and these outputs are superseded, never edited. Nothing here claims the revision check.

Research only. No number here is a published probability (no holdout calibration exists: Phase 12 and 13; no champion: Phase 16). The targets are price-path targets with no execution data (PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, BACKTEST_NOT_AVAILABLE). Every model here is MODEL_NOT_PROMOTED.

Pre-registration: `../ACCEPTANCE_CHECKLIST.md`, `../experiments/EXPERIMENT_REGISTRY.csv` and PI-D-050, committed in `8599318` (2026-10-25T21:06:04Z) before any technical feature was computed on a labelled decision. Code: `d290384` (21:22:26Z), before recorded run 1; runner repair `d9b2a9c` (21:24:03Z), recorded run 2 at 21:24:03Z (see "Runs").

## Answer in one paragraph

The technical models were built, trained where the frozen gate allows, and compared with Phase 07's B0 and B2 on the same frozen folds, and none of them can be called better or worse than the training base rate. Technical inputs exist only for decisions with a point-in-time pool whose history covers the 24 h window (154 of 240 labelled development decisions; never for the CURRENT_VENDOR_LIST route). On those rows the training sets of T1 (24 h) and T2 (24 h) never reach the frozen minimum of 100 events with 20 per class (T1 at most 76 with 22 positive inside the walk-forward, 87 with 26 at the holdout start; T2 61 with 13, and 83 with 14), so every T1 and T2 technical model is INSUFFICIENT_HISTORY. On T1b (6 h) the gate is first met in the last fold (138 rows, exactly 20 positive), whose out-of-sample day holds 6 scored rows and 0 positive events: INSUFFICIENT_DAYS. The large Brier skill on those 6 rows (M2 0.729 against B0) is the arithmetic of six negatives scored by a model whose numbers are lower than the training prevalence; it is not evidence of skill. This is the result stated in advance in the checklist. The engine stays at ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED); the T1b cards trained at the holdout start are frozen for Phase 12.

## Inputs

| Input | What was used |
|---|---|
| Labels | `labels.training_labels(dev, as_of, target, mode="provider")` on `/home/claude/pi_research/p06/dev_store.sqlite` (read-only, sha256 unchanged by the run); label version `labels-1`, registry `4b4aabce...`; the same label sets as Phase 07 (label-set sha in `../experiments/TECHNICAL_METRICS.csv` rows through the split fingerprints) |
| Export-row features (B0, B2 and M2's B2 columns) | stored provider-mode version 2 snapshots through `features.training_view`, exactly as Phase 07 |
| Technical features | tech-1 from `memelab/predictive/technical.py`, computed through `features.AsOfView(fs, T, "provider")` on `/home/claude/pi_research/p05/predictive_store.sqlite` at each decision's own time, point-in-time pool only (PI-D-050); feature-set sha `8c18262b0bd90e3aaa49017e14dfec13ae05dceda478867b05a25d961ec30188` (includes version 2's `90781ad7...`) |
| Not used | the sealed holdout (never opened), Phase 04 bake-off labels (refused), the vendor's current pool list as a feature source, opens, highs and lows, any network (0 socket events, 0 vendor calls) |

## tech-1 (closes and volumes only)

Fifteen features in four families (definitions in `../ACCEPTANCE_CHECKLIST.md` and `technical.DEFINITIONS`): momentum (ln returns over 1 h, 6 h, 24 h), volatility (realized variation 1 h and 6 h, ln close range 6 h and 24 h), volume (relative 1 h volume, ln(1 + candles in 24 h), ln(1 + minutes since the last close)), structure (breakout of the prior 23 h high inside the last hour, failed breakout, retest of the prior 18 h high within 3%, distance from the 24 h high, pullback from the 6 h high).

Interval edge: a candle is used only when it has ended at or before T and is available at T (end plus the 300 s provider lag, or the lab's read if earlier). The store refuses a candle served while still in progress (`outcomes_core` future-dated rule, test), and tech-1 also drops any candle whose end is after T if a view ever served one (test, mutation caught). Over the 240 labelled decisions, 248 candles of the decision pools had started before T but were not available at T (94 holding or ending after T, 154 closed but inside the provider lag); none was used (`../evidence/unavailable_candles.json`: inputs used after T 0; store candles ending after their availability 0).

Consistency with version 2: for all 240 labelled development decisions, the restated values (returns 1 h, 6 h, 24 h; rv 6 h; range 24 h; distance from the 24 h high) equal the stored snapshots exactly and the derived ones (candle count, last-close age, relative volume) within 1e-9 relative; missing reasons agree (`../evidence/v2_consistency.json`: 0 inconsistent).

Coverage (`../experiments/TECH_COVERAGE.csv`): at the holdout start T1 87 of 136 rows complete, T1b 144 of 224, T2 83 of 131; the rest OOD with NO_POOL_AT_DECISION (34, 65, 33: all CURRENT_VENDOR_LIST decisions) or CENSORED_RETRIEVAL with OUTSIDE_FETCHED_WINDOW (15 each, PIT route). Nothing is imputed. Technical models therefore describe the PIT_RECORDED route only.

## Models (one configuration each, fixed before the run)

| Id | Model | Inputs |
|---|---|---|
| M1 `T_LOGIT` | L2 logistic, C = 1, numpy Newton, training-only standardisation | 15 tech-1 features |
| M2 `T_LOGIT_B2` (primary) | L2 logistic, C = 1 | B2's columns plus the 15 tech-1 features |
| M3 `T_STUMPS` | gradient-boosted depth-1 stumps, 100 rounds, learning rate 0.1, at least 10 rows per leaf, Newton leaf values | 15 tech-1 features |
| A1 to A4 | M2 without momentum, volatility, volume or structure, on M2's rows | |
| A5 `T_B2_TC` | B2's columns fitted on M2's rows | |
| NC1-T | M2 on training labels permuted inside each fold, seeds 0 to 19 | |

A fit happens only when the model's own rows reach 100 events and 20 per class.

## Folds and training rows (same frozen folds as Phase 07)

Split fingerprints equal Phase 07's (T1 `0ab64525...`, T1b `aa16e7ad...`, T2 `82a1c33b...`), and Phase 07's B0 and B2 refitted here give identical out-of-sample numbers on all 76 rows (0 differences at 6 decimals, `../evidence/phase07_equality.json`). The fold audit is valid for every fold.

| Target | Fold cutoff | All training rows (positive) | Technical rows (positive) | Technical models | Out-of-sample rows (positive), scored by M2 |
|---|---|---|---|---|---|
| T1 24 h | 10-13 | 104 (25) | 61 (18) | INSUFFICIENT_HISTORY | 11 (4), 0 |
| T1 24 h | 10-14 | 112 (26) | 68 (19) | INSUFFICIENT_HISTORY | 8 (1), 0 |
| T1 24 h | 10-15 | 123 (30) | 76 (22) | INSUFFICIENT_HISTORY | 5 (3), 0 |
| T1b 6 h | 10-12 | 180 (23) | 111 (17) | INSUFFICIENT_HISTORY | 8 (1), 0 |
| T1b 6 h | 10-13 | 188 (24) | 118 (18) | INSUFFICIENT_HISTORY | 11 (1), 0 |
| T1b 6 h | 10-14 | 199 (25) | 126 (19) | INSUFFICIENT_HISTORY | 8 (0), 0 |
| T1b 6 h | 10-15 | 207 (25) | 133 (19) | INSUFFICIENT_HISTORY | 7 (1), 0 |
| T1b 6 h | 10-16 | 214 (26) | 138 (20) | fitted | 10 (0), 6 (4 OOD) |
| T2 24 h | 10-14 | 104 (27) | 61 (13) | INSUFFICIENT_HISTORY | 8 (1), 0 |

## Results (pooled out-of-sample, ALL view; full table `../experiments/TECHNICAL_METRICS.csv`)

| Target | Model | Reference | n (positive) | Days | Brier | Reference Brier | BSS | Verdict |
|---|---|---|---|---|---|---|---|---|
| T1 24 h | B2 (Phase 07) | B0 | 24 (8) | 3 | 0.2449 | 0.2297 | -0.066 | INSUFFICIENT_DAYS |
| T1 24 h | M1, M2, M3, A1 to A5 | B0 and B2 | 0 | | | | | INSUFFICIENT_HISTORY |
| T1b 6 h | B2 (Phase 07) | B0 | 44 (3) | 5 | 0.0595 | 0.0667 | 0.108 | INSUFFICIENT_EVENTS |
| T1b 6 h | M1 | B0 | 6 (0) | 1 | 0.0046 | 0.0148 | 0.690 | INSUFFICIENT_DAYS |
| T1b 6 h | M2 (primary) | B0 | 6 (0) | 1 | 0.0040 | 0.0148 | 0.729 | INSUFFICIENT_DAYS |
| T1b 6 h | M3 | B0 | 6 (0) | 1 | 0.0050 | 0.0148 | 0.664 | INSUFFICIENT_DAYS |
| T1b 6 h | M2 | B2 | 6 (0) | 1 | 0.0040 | 0.0122 | 0.672 | INSUFFICIENT_DAYS |
| T1b 6 h | A5 (B2 columns on M2's rows) | B0 | 6 (0) | 1 | 0.0145 | 0.0148 | 0.018 | INSUFFICIENT_DAYS |
| T2 24 h | B2 (Phase 07) | B0 | 8 (1) | 1 | 0.1526 | 0.1275 | -0.197 | INSUFFICIENT_DAYS |
| T2 24 h | M1, M2, M3, A1 to A5 | B0 and B2 | 0 | | | | | INSUFFICIENT_HISTORY |

How to read the T1b rows: six out-of-sample rows on one day (2026-10-16), all negative. With no positive event, the Brier score only rewards numbers close to 0, and any model whose numbers sit below the training prevalence (0.12) beats B0; the day interval is undefined (fewer than 5 days) and no positive exists to test whether the model ranks events. ROC AUC and average precision are not defined. The verdict rule (Phase 07, unchanged) stops at INSUFFICIENT_DAYS. No view changes a verdict (`NEW_MINTS`, `NEW_CREATORS`, `NEW_NARRATIVES`: 3 or 4 rows; `PIT_ONLY`: 6; `NO_KEY_CONFLICT`: 4).

Ablation per family (`../experiments/ABLATIONS.csv`, T1b, same 6 rows): M2 0.0040; without momentum 0.0039, without volatility 0.0038, without volume 0.0068, without structure 0.0051, B2 columns only 0.0145 (B0 0.0148). On six negatives these differences say only how low each variant's numbers are; no family can be credited.

NC1-T (shuffled labels): T1 and T2 INSUFFICIENT_HISTORY (no fit), T1b INSUFFICIENT_DAYS (`../experiments/NC1T_SEEDS.csv`); uninformative at this size.

Hit and miss at the fold's training prevalence (`../experiments/HIT_MISS_COHORTS.csv`, by route, liquidity bucket, launch-age bucket, week, day): M2 on T1b raised no alert on its 6 rows (6 correct rejections, 0 hits, 0 misses, 0 false alarms; liquidity 100k to 1m 5 rows, 20k to 100k 1; launch age 7 to 30 days 2, 30 days or more 2, unknown 2; one week, 2026-W42). No rate is claimed below 20 events and no regime statement is possible (P21).

Degeneracy: no model's out-of-sample numbers are constant (P11). Calibration is not assessed (no positive).

## Negative controls, traps and invalid inputs

| Check | Result |
|---|---|
| NC2-T, future feature: the next-hour return after the decision (tech-1 at T + 1 h), declared at its true availability | 98 of 154 complete decisions have such a value (the rest have no later candle in the store); 98 refused by the allowlist and 98 by `validate_rows`; 0 accepted; smallest delay 3,071 s |
| P06-T, the cutoff moved to T + 600 s | 1,758 values that would use a candle not available at T, all refused; 12 values change only because the query time moved (the last close's age, sliding windows over inputs available at T), correctly accepted |
| P13-T, a holdout-start card on the earliest development decision | 9 of 9 cards refused (ModelTrainedAfterDecision) |
| CX-08, window-dependent opens, highs and lows | tech-1 never reads them (source test); stores with different opens, highs and lows, and a later read that revises only them, give identical features (tests); 0 such revisions on these 80 pools in the Phase 05 store |
| Contract | an ABSTAIN document from each M2 card passes `contract.validate`; a FORECAST with a probability is refused (no holdout calibration, and P13) |

## Forecast traces (`../evidence/trace/`)

1. Pre-registered row: T1b, decision `efa03ae4...` (mint `1zJX5gRnjLgmTpq5sVwkq69mNDQkCemqoasyjaPW6jm`, 2026-10-12T10:18:37Z), fold 0. Technical models abstain (INSUFFICIENT_HISTORY); B0 0.1278, B2 0.0265. 102 candles read in the last 25 h, the newest ending 10:10:00Z and available 10:15:00Z; the candle ending 10:15:00Z (available 10:20:00Z) was not read.
2. Second trace, added after recorded run 1 because the pre-registered fold had no fitted technical model: the earliest row where M2 has a number, T1b decision of 2026-10-16T10:42:06Z, fold 4: M1 0.0927, M2 0.1204, M3 0.1529, B0 0.1215, B2 0.1670 (outcome 0).

`../probes/verify_trace.py` recomputes both from the SQLite tables with plain SQL and Python (no `technical.py`, no `features.py`) and from the cards' JSON numbers: no difference. Rejected inputs in both traces: a value using the candle that closes at T (P06, P36), a store row available 1 s after T (the view's audit), a non-finite feature (no number, OOD; a fit refuses it, P38), and the holdout-start card on the development decision (P13). Latency of one forecast from the store (tech-1 at T plus the three cards): median 0.014 s and 0.048 s.

## Train-only artifacts (frozen for Phase 12)

Fitted through the gate on all development labels as of 2026-10-17T00:00:00Z; JSON read by numpy code, no pickle; each card carries model sha, tech-1 sha, version 2 sha, training cutoff, label-set and data-snapshot sha, PROVISIONAL, `revision_check_claimed: false`, `publishable: false`, MODEL_NOT_PROMOTED. MODEL_STALE for decisions after 2026-10-31.

| Target | Card | Rows used (positive) | State | Model sha (first 12) |
|---|---|---|---|---|
| T1 24 h | M1, M2, M3 | 87 (26) | INSUFFICIENT_HISTORY | `c5ae485a7bc2`, `821e8700879b`, `3ba11decbbaa` |
| T1b 6 h | M1, M2, M3 | 144 (20) | fitted | `be8fff758ca8`, `eefba4b0e68a`, `30931dd6a5bf` |
| T2 24 h | M1, M2, M3 | 83 (14) | INSUFFICIENT_HISTORY | `d1a8bc767760`, `ef43deb01467`, `6b7d77225d32` |

File sha256 and the round-trip, tamper and `runtime.verify_artifact` results: `../evidence/serialization_smoke.json`. Fold cards: `../artifacts/folds/<target>.json`.

## Engine and oracle agreement

`memelab/predictive/technical.py` (numpy and the standard library only, flag OFF, imported by no existing module). Oracles in the research venv (`../probes/sklearn_crosscheck_tech.py`, scikit-learn 1.9.1): the stumps equal GradientBoostingClassifier(max_depth=1, n_estimators=100, learning_rate=0.1, min_samples_leaf=10) within 3.3e-16 in probability on the real T1b fold-4 design and 10 synthetic designs, with the same split in every round (scikit-learn takes thresholds in float32, compared at that precision). The logistic differs from scikit-learn's lbfgs by up to 1.13e-6 in a coefficient on the real T1b fold-4 M1 design, above the pre-registered 1e-6; `../probes/logit_solver_diagnosis.py` shows lbfgs stopping with a gradient of 7.2e-6 while the numpy fit's gradient is 2.2e-15, and scikit-learn's exact Newton solvers agree with numpy within 7.1e-14 (newton-cholesky) and 6.1e-16 (newton-cg). The diagnosis and the second solvers were added after the result and are disclosed as such. Mutation probe: 28 of 28 mutations of `technical.py` caught by `tests/test_predictive_technical.py` (40 tests).

## Runs and cost

| Run | Code | What it was |
|---|---|---|
| features-only probe | before `d290384` | tech-1 and the version 2 consistency on the 240 decisions; label rows read for keys only; no fit |
| recorded run 1 | `d290384` | every registered configuration; same numbers as run 2; its P06-T probe counted a clock-only change as a trap (1 of 154 accepted); outputs overwritten |
| recorded run 2 | `d9b2a9c` | the outputs here; 26.6 s wall, 26.1 s CPU, 79 MB, 0 socket events, 0 vendor calls, stores unchanged |
| run 3 | `d9b2a9c` | determinism: 28 generated files identical except the two wall-clock latency fields of the traces |

All are rows of `../experiments/SEARCH_LEDGER.csv` (Phase 07's 520 rows plus 613 Phase 08 rows: every model, reference and view, each NC1-T seed, B0 references and the debug runs) for Phase 12's selection correction (P22).

## What these numbers do not support

Any claim that technical features help or hurt on any target; any per-family, per-cohort or per-regime statement; any probability shown to a user; any statement about the CURRENT_VENDOR_LIST route (no technical input exists there); any trading, proceeds or fill statement; any use of the cards for decisions before 2026-10-17 (DATA_TIME_CONTRACT).

## Rerun

```
python -B audits/predictive-intelligence/phase_08/probes/run_technical.py audits/predictive-intelligence/phase_08 --npz <scratch>/arrays08.npz
python -B audits/predictive-intelligence/phase_08/probes/verify_trace.py audits/predictive-intelligence/phase_08/evidence/trace/FORECAST_TRACE.json
python -B audits/predictive-intelligence/phase_08/probes/verify_trace.py audits/predictive-intelligence/phase_08/evidence/trace/second/FORECAST_TRACE.json
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_08/probes/sklearn_crosscheck_tech.py <scratch>/arrays08.npz audits/predictive-intelligence/phase_08/evidence/sklearn_crosscheck.json
/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_08/probes/logit_solver_diagnosis.py <scratch>/arrays08.npz audits/predictive-intelligence/phase_08/evidence/logit_solver_diagnosis.json
python -B audits/predictive-intelligence/phase_08/probes/mutation_technical.py audits/predictive-intelligence/phase_08/evidence/mutation_technical.json
```

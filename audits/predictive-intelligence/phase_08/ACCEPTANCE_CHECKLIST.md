# Phase 08 acceptance checklist and pre-registration (written before any model fit or technical feature on a labelled row)

Written 2026-10-25 from 21:05Z by the Phase 08 agent, after the entry gate at `1139575` (`1 failed, 1179 passed in 165.18s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261025_2058_BRETT_0x532f.md` removed by hand; `check_seal.py` exit 0 with `"problems": []`), after reading the package (checksums OK), the phase prompt, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, FORECAST_OUTPUT_SCHEMA, every PI-D entry (PI-D-001 to PI-D-049), Phase 07's BASELINE_SPEC, metrics, search ledger, frozen cards and runner, and `memelab/predictive/*.py`. This file, `experiments/EXPERIMENT_REGISTRY.csv` and PI-D-050 are committed before any technical feature is computed on a labelled decision and before any model is fitted on real data (PI-D-045 item 5).

What was looked at before writing it: the missing-value counts of the stored version 2 candle features among the labelled development decisions (no label value, no class split, no feature value): 71 of the labelled decision keys have NO_POOL_AT_DECISION (no point-in-time pool in the export), 4 to 15 more OUTSIDE_FETCHED_WINDOW depending on the window; per target the 24 h-window features are missing for 49 of 136 (T1), 80 of 224 (T1b) and 48 of 131 (T2). The development class counts printed by Phase 06 were already public. From these counts alone the technical models are expected to fall below the frozen training minimum of 100 events on T1 and T2 in every fold and to be close to it on T1b; this is stated here so the result cannot be read as a surprise.

## Status rules carried in

- PROVISIONAL (PI-D-046): Phase 06's 48 h revision re-read is still owed (not before 2026-10-26T13:49Z). Every Phase 08 number, card and verdict carries `PROVISIONAL_PENDING_REVISION_REREAD` and `revision_check_claimed: false`; if the re-read changes any development label, `probes/run_technical.py` is rerun at the Phase 08 code commit and the outputs are superseded, never edited.
- Phase 08 never opens `phase_06/sealed/` (Phase 12 only); the development store goes through `labels.training_labels` only.
- Verdicts use Phase 07's frozen functions unchanged: `baselines.evaluate`, `baselines.verdict`, `baselines.evaluation_gate` (PI-D-049), Holm across the three primary targets per model. No new verdict code.

## Inputs (fixed)

| Input | Rule |
|---|---|
| Labels | `labels.training_labels(dev_con, as_of, target, mode="provider")` on `/home/claude/pi_research/p06/dev_store.sqlite` only, opened read-only; registry `4b4aabce...`, label version `labels-1` |
| Export-row features | stored provider-mode version 2 snapshots of `/home/claude/pi_research/p05/predictive_store.sqlite` through `features.training_view` (B0 and B2 inputs, exactly as Phase 07) |
| Technical features | new feature set `tech-1`, computed by `memelab/predictive/technical.py` through `features.AsOfView(con, T, "provider")` on the Phase 05 store at each decision's own decision time T, on the decision's point-in-time pool only (PI-D-050) |
| Join | `baselines.join` (chain, mint byte for byte, decision time, decision key) plus the same identity check for every technical snapshot |
| Folds | Phase 07's frozen day walk-forward on the same development label set; split fingerprints must equal Phase 07's (`0ab64525...`, `aa16e7ad...`, `82a1c33b...`) |

## Technical feature set tech-1 (closes and volumes only)

Candles: the 5-minute candles of the point-in-time pool visible at T in provider mode (latest version with `available_at <= T`, which is end plus the 300 s provider lag or the lab's read if earlier; vanished positions removed), through `AsOfView.candles`, audited by `replay_core.Audit`. Opens, highs and lows are never read (they depend on the request window, PI-D-037). `px(x)` is the close of the newest visible candle ending at or before x; `win(w)` is the visible candles ending in (T - w, T]; `last` is the newest visible candle. Coverage and missing reasons follow `features._candle_values` exactly (series status, `cover_from`, OUTSIDE_FETCHED_WINDOW as RETRIEVAL, NO_POOL_AT_DECISION as AS_OF, NO_CANDLE_AVAILABLE as HEURISTIC).

| Family | Feature | Definition |
|---|---|---|
| momentum | `tech_log_ret_1h`, `tech_log_ret_6h`, `tech_log_ret_24h` | ln(last close / px(T - w)) |
| volatility | `tech_rv_1h`, `tech_rv_6h` | sqrt of the sum of squared ln close changes from px(T - w) through win(w) |
| volatility | `tech_log_range_6h`, `tech_log_range_24h` | ln(max close / min close) over px(T - w) and win(w) |
| volume | `tech_log_rel_vol_1h` | ln((volume of win(1 h) + 1) / (volume of win(24 h) / 24 + 1)), USD |
| volume | `tech_log1p_candles_24h` | ln(1 + number of candles in win(24 h)) |
| volume | `tech_log1p_last_close_age_min` | ln(1 + (T - end of last) / 60) |
| structure | `tech_log_breakout_1h` | ln(RH / PH): PH = max close over px(T - 24 h) and candles ending in (T - 24 h, T - 1 h]; RH = max close over px(T - 1 h) and win(1 h). Above 0 means a new 23 h high inside the last hour |
| structure | `tech_failed_breakout_1h` | 1 when RH > PH and last close < PH, else 0 |
| structure | `tech_retest_6h` | PH6 = max close over px(T - 24 h) and candles ending in (T - 24 h, T - 6 h]; 1 when a close in win(6 h) is above PH6 and abs(ln(last close / PH6)) <= ln(1.03), else 0 |
| structure | `tech_log_dist_24h_high` | ln(last close / max close over px(T - 24 h) and win(24 h)) (distance from the 24 h high) |
| structure | `tech_log_pullback_6h` | ln(last close / max close over px(T - 6 h) and win(6 h)) (exhaustion from the 6 h high) |

Consistency rule: where tech-1 restates a version 2 value (returns 1 h, 6 h, 24 h; rv 6 h; range 24 h; distance from the 24 h high = `cdl_log_drawdown_24h`; candle count, last close age and relative volume from `cdl_candles_24h`, `cdl_last_close_age_s`, `cdl_vol_usd_1h`, `cdl_vol_usd_24h`), the recomputation must equal the stored snapshot value at 10 significant digits for every labelled development decision, else the run stops.

Missing values: a row whose technical feature is missing for any reason is not imputed. AS_OF missingness (NO_POOL_AT_DECISION and others) gives the row OOD for every technical model; RETRIEVAL missingness gives CENSORED_RETRIEVAL (censoring, never a model input, PI-D-037); HEURISTIC gives OOD. Coverage per target, view and cohort is reported.

## Candidate models (one configuration each, no tuning)

Every model is fitted on each fold's training rows only, on the rows that carry every required input; a fit happens only when those rows reach 100 events and 20 per class (ACCEPTANCE), else the card abstains with INSUFFICIENT_HISTORY. Every fitted object is a JSON card read by numpy code (no pickle) with model sha, feature-set sha (tech-1 and version 2), training cutoff, label-set and data-snapshot sha.

| Id | Model | Inputs | Fixed settings |
|---|---|---|---|
| M1 `T_LOGIT` | L2 logistic regression, numpy Newton, intercept unpenalised | the 15 tech-1 features (all required) | C = 1.0; training-only preprocessing of `stats.Prep` (drop constant columns, standardise) |
| M2 `T_LOGIT_B2` (primary) | L2 logistic regression | B2's columns (liquidity, market cap, 24 h volume, fatal flag required; token age optional with median fill and missing indicator, AS_OF missingness only) plus the 15 tech-1 features (required) | C = 1.0, `stats.Prep` |
| M3 `T_STUMPS` | gradient-boosted depth-1 regression stumps on the logistic loss, numpy | the 15 tech-1 features (required) | 100 rounds, learning rate 0.1, at least 10 training rows per leaf, thresholds at midpoints of consecutive distinct training values, initial score the training log-odds, leaf value sum of residuals over sum of p(1 - p) (Newton step, the scikit-learn GradientBoostingClassifier convention), no subsampling, ties broken by first feature then first threshold |
| A1 to A4 | M2 without one family: momentum, volatility, volume, structure | as M2 minus the family | as M2 |
| A5 `T_B2_TC` | B2's columns only, fitted on M2's training rows (rows with every tech-1 feature) | B2's columns | as B2 |
| NC1-T | M2 refitted on training labels permuted inside each fold's training rows | as M2 | seeds 0 to 19 |
| B0, B2 | Phase 07's B0 and B2, refitted by `baselines.fit_b0` and `fit_b2` in the same folds | as Phase 07 | their out-of-sample numbers must equal Phase 07's `OOS_PREDICTIONS.csv` at 6 decimals |

No other model, feature set, hyperparameter, threshold or calibration variant is run. Sequence or time-series models are not run: with these sample sizes their improvement cannot be tested (phase prompt step 2).

## Comparisons, metrics and verdicts (fixed)

| Item | Rule |
|---|---|
| Primary | M2 against B0 (Brier skill score, the frozen primary score), on the out-of-sample rows where M2 has a number; verdict by `baselines.verdict` with Holm across the three primary targets |
| Secondary | M1 and M3 against B0 (same rule, Holm per model); every model against B2 on the same rows (`baselines.evaluate(reference="B2")`, the ACCEPTANCE "champion over B2" direction), verdict reported with the same function; ablations A1 to A5 against M2's B0 rows (descriptive) |
| Views | ALL, NEW_MINTS, NEW_CREATORS, NEW_NARRATIVES, PIT_ONLY, NO_KEY_CONFLICT (Phase 07's six) |
| Scores and intervals | Brier, Brier skill score, log loss (clip 1e-6), ROC AUC and average precision only with 10 events per class; day and mint bootstrap 2,000 replicates, seed 20261025, wider governs, day interval undefined below 5 days; out-of-sample count gate 50 events and 10 per class (PI-D-049) |
| Hit and miss | per cohort (token age bucket, liquidity bucket, route, week, day): hits, misses, false alarms and correct rejections at the fold's own B0 value as the threshold (a prediction above the training prevalence is an alert); no rate below 20 events |
| Degeneracy (P11, P38) | a model whose out-of-sample numbers have zero variance is flagged DEGENERATE; a non-finite or out-of-range number raises |
| Coverage and unavailable candles | per target: rows with every technical feature, OOD and CENSORED_RETRIEVAL counts with reasons; candles of the decision pools ending after T - 300 s that the as-of view excluded, and the count of them used (must be 0) |
| Cost | wall and CPU time per run and per forecast, 0 network calls (audit hook), 0 vendor calls |
| Promotion | none: every model is MODEL_NOT_PROMOTED; the best case on development data is SKILL_INDICATED_DEVELOPMENT_ONLY, which is never a promotion |

## Train-only artifacts

M1, M2 and M3 per primary target fitted on all development labels as of 2026-10-17T00:00Z (the holdout start) through the gate, or an abstain card where the gate fails; frozen for Phase 12, MODEL_STALE after 2026-10-31.

## Forecast trace (selection rule fixed here)

The trace decision is the earliest out-of-sample row of T1b (then T1, then T2, if T1b has none) by decision time, then mint, among rows with every tech-1 feature present. The trace lists every candle read at T with start, end, `available_at`, `retrieved_at`, close and volume, the candles excluded because they were not yet available, each feature, the fold card used (sha, cutoff) and the number or abstention. `probes/verify_trace.py` recomputes it independently from the SQLite tables with plain SQL and Python (no `technical.py`, no `features.py`) and from the card's JSON numbers. Invalid inputs that must be rejected: a candle that closes after T planted into the trace (P06, P36), a non-finite feature (P38), and the holdout-start card applied to the development decision (P13).

## Checklist

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| G1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` | a line not OK |
| G2 | Entry gate | suite at `1139575`, `check_seal.py` | anything but `1 failed, 1179 passed` with the known failure, or seal problems |
| G3 | Pre-registration before any fit | this file, the registry and PI-D-050 committed before `evidence/run_log.json` start time | a run before the commit |
| G4 | Numpy core with tests | `memelab/predictive/technical.py` numpy and standard library only (test); tests in `tests/test_predictive_technical.py` | a third-party import or an untested rule |
| G5 | As-of technical features | every tech-1 value from candles available at T in provider mode (audit), closes and volumes only; a candle 1 s after availability absent; the candle holding T never used (P06); opens, highs and lows changed in the store change no feature (CX-08) | any later candle or any o, h, l read |
| G6 | Version 2 consistency | recomputed overlap features equal the stored snapshots for every labelled development decision | one difference |
| G7 | Same frozen folds as Phase 07 | split fingerprints equal; B0 and B2 out-of-sample numbers equal Phase 07's at 6 decimals | a difference |
| G8 | Gate use and identity | training rows only from `training_labels` at each cutoff; identity join on every row; sealed and bake-off paths refused | a row from anywhere else |
| G9 | Count gates | no model fitted below 100 events or 20 per class on its own used rows | a fit below the minimum |
| G10 | Metrics and verdicts | `experiments/TECHNICAL_METRICS.csv` per target, model, reference and view, with counts, intervals, verdict and PROVISIONAL; Phase 07's verdict function unchanged | a missing count or verdict, or a claim under the minimums |
| G11 | Negative controls and traps | NC1-T under `nc1_verdict`; NC2-T (a future 1 h return declared at its true availability) refused on every row by the allowlist and `validate_rows`; P06 trap (cutoff moved past the candle holding T) shows the values that would change and they are refused; P13 trap refused | a trap accepted |
| G12 | Ablation per family | A1 to A5 reported beside M2 | missing |
| G13 | Hit and miss, coverage, cost | tables present, no rate below 20 | missing |
| G14 | Artifacts | cards written, read back, numbers identical, model sha recomputed, tampering refused, `runtime.verify_artifact` on the files | a mismatch or a pickle |
| G15 | Contract | an ABSTAIN document from each M2 card passes `contract.validate`; a FORECAST with a probability is refused | a probability accepted |
| G16 | Oracles | scikit-learn in the research venv only: logistic coefficients within 1e-6 on every real fold design; stumps against GradientBoostingClassifier(max_depth=1, n_estimators=100, learning_rate=0.1, min_samples_leaf=10) within 1e-9 on fold designs, ties disclosed | a larger difference without a tie explanation |
| G17 | Determinism and isolation | two runs into two folders give identical sha256; 0 network calls; stores unchanged; nothing written under tracked `data/`, `inbox/`, `state/` | any difference or write |
| G18 | Synthetic fixture | a seeded fixture with a known technical signal: M1 beats B0, NC1-T does not, outputs carry NO_REAL_HISTORICAL_EVIDENCE | flag missing |
| G19 | Forecast trace | trace written, independently recomputed equal, three invalid inputs rejected | a difference or an acceptance |
| G20 | Search ledger | `experiments/SEARCH_LEDGER.csv` = Phase 07's ledger plus every Phase 08 configuration, view, ablation, NC1 seed and any debug run | an unlogged run |
| G21 | Adversarial scenarios | tests for P06, P10, P11, P13, P20, P21, P22, P36, P38, P43 and the new counterexample CX-08 (window-dependent opens, highs and lows) caught by a test; mutation probe catches every listed mutation | a scenario without a test or a surviving mutation |
| G22 | Flag and imports | flag OFF; no existing module imports the new code (existing test); score and fatal flags unchanged | a change |
| G23 | Suite, guard and audits after the commit | full suite (no new failure), `python -m memelab social guard`, `python tools/release_audit.py --history` on a single-branch clone, `check_seal.py`; `git status` clean | any new failure |

## Expected result, stated in advance

The technical models need rows that have every tech-1 feature, which removes the decisions without a point-in-time pool and those outside the fetched window. On T1 and T2 the training sets will very likely stay below 100 events in every fold and at the holdout start (INSUFFICIENT_HISTORY); on T1b they may pass the event minimum but may miss 20 positives. Where a fold does fit, the out-of-sample set is at most Phase 07's (44 events, 3 positive on T1b), below the frozen out-of-sample minimums, so the verdict cannot be better than INSUFFICIENT_EVENTS. The phase gate is met by real trained models where the gate allows, or by this explicit no-go: MODEL_NOT_PROMOTED for every model.

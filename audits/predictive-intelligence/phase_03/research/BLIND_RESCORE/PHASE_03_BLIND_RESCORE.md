# Phase 03 blind rescore (second reviewer)

Independent re-score of the seven repositories in `research/BLIND_RESCORE_PACKET.md` against the locked 100-point rubric (`references/GRADING_RUBRIC.md`), written 2026-10-24 by the orchestrator's second reviewer. Numbers are in `PHASE_03_BLIND_RESCORE.csv` beside this file (same values; a copy named `RESCORE.csv` is in the blind working copy `/home/claude/pi_orchestration/rescore/blind/`).

## Result

| Repository (pinned SHA) | Temporal 18 | Outcomes 14 | Calibration 12 | Features 10 | Decision 10 | Code 8 | Integration 8 | Reproducibility 8 | Cost 5 | License 7 | Total | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| scikit-learn/scikit-learn (`59106029`) | 5 | 8 | 7 | 3 | 3 | 8 | 8 | 5 | 5 | 6 | 58 | none |
| eslazarev/purged-cross-validation (`07692dd8`) | 14 | 3 | 0 | 1 | 4 | 7 | 8 | 6 | 5 | 6 | 54 | none |
| scikit-learn-contrib/MAPIE (`f1cc3d07`) | 3 | 3 | 8 | 0 | 6 | 6 | 7 | 3 | 4 | 6 | 46 | none |
| statsmodels/statsmodels (`aa61cc14`) | 1 | 7 | 3 | 2 | 2 | 7 | 6 | 4 | 5 | 6 | 43 | LEAKAGE_FAIL and RESEARCH_ONLY, both scoped to MarkovRegression |
| interpretml/interpret (`d82ea62a`) | 1 | 7 | 1 | 3 | 2 | 7 | 7 | 4 | 5 | 5 | 42 | RESEARCH_ONLY scoped to the `survival_cox` objective |
| online-ml/river (`b674b758`) | 6 | 7 | 2 | 4 | 2 | 4 | 5 | 4 | 4 | 4 | 42 | LEAKAGE_FAIL scoped to model state after a `simulate_qa` replay |
| soda-inria/hazardous (`1504934e`) | 1 | 9 | 5 | 2 | 0 | 3 | 3 | 2 | 3 | 4 | 32 | REJECT scoped to the PyPI 0.2.0 wheel and sdist |

No repository earns skill points: every model metric in the smokes comes from the synthetic challenge and is treated as a format or behaviour check only. The challenge's 14.6 h "embargo" band earned and cost nothing.

## How the blindness was kept

- Built the working copy with the lead's `verify/make_blind_copy.sh` into `/home/claude/pi_orchestration/rescore/blind/` (section 6 removed from every review; script read before running; it writes only to the target).
- Not opened: `SCORECARD.csv`, `SCORE_ITEMS.csv`, `RUBRIC_ITEMS.csv`, `RANKED_TOP10.md`, `CATEGORY_WINNERS.md`, `REVIEW_VERIFICATION.md`, `INDEPENDENT_RESCORE.md`, `verify/sensitivity.json`, `verify/score_inputs.py`, `PHASE_03_EVIDENCE.md`, `PHASE_03_RESULTS.json`, `docs/predictive-intelligence/HANDOFF.md` or `ROADMAP.md`. A directory listing showed their names only. No `git log` or `git show` on the Phase 03 commit (one `git log -1 --format=%H` printed the repo HEAD hash, no message).
- Read: the packet, the rubric, the Phase 03 prompt, Phase 01 `TARGET_REGISTRY.md`, `ACCEPTANCE_METRICS.md`, `PLANNED_SEAMS.md`, `GAP_MATRIX.csv`, review sections 1 to 5, 7 and 8, the raw smoke outputs, and the lead's re-execution outputs in `blind/evidence/` (no scores in the parts read).
- Pinned source fetched myself (`git init; git fetch --depth 1 <url> <sha>; git checkout FETCH_HEAD`) into `/home/claude/pi_orchestration/rescore/src/<owner>__<repo>`; all seven HEADs equal the pins. Tags `1.9.1` (scikit-learn) and `v0.15.0` (statsmodels) fetched shallowly for diffs only.
- Nothing written inside `/home/claude/memelab-inbox`. One venv was created in `/tmp/hazardous` by a shell grouping mistake and deleted at once; it was rebuilt under `rescore/venvs/`.

## My item split of the locked rubric

Each criterion is split into items written before scoring. A point needs a pinned `path:line`, a raw smoke output field, or one of my reruns. A capability seen only in pinned source (with its own tests) can earn points; README or docstring text earns nothing; an unanswered item scores 0. Synthetic metric values neither earn nor lose points; structural behaviour (an exception, a NaN, a non-monotone curve, a definition mismatch) can.

| Criterion (max) | Items (max) |
|---|---|
| Temporal integrity (18) | T1 time-aware splitting or evaluation (4: timestamp folds built in; 3: ordered folds plus timestamp purge; 2: ordered by rows or online delayed evaluation; 1: time path for another target type only; 0 none). T2 label-maturity handling (5: purge by label windows confirmed by an independent checker; 3: delayed label release confirmed, with a caveat; 1: caller-supplied maturity-respecting splits accepted and confirmed). T3 time-based embargo (2). T4 feature-availability enforcement (3). T5 strict as-of configuration confirmed (2). T6 chronology and temporal-assumption checks, group separation (2) |
| Transferable outcomes (14) | O1 binary event probabilities confirmed (4). O2 survival or competing risks with censoring (3: competing risks confirmed; 2: with a structural defect or single event; 1: source only or unreleased). O3 other outcome types (1). O4 multi-token evaluation (2). O5 discrimination or time-dependent evaluation in the library (2). O6 censored or pending label handling (2) |
| Calibration and uncertainty (12) | K1 proper scores in the library (2). K2 post-hoc calibration usable on a later window (3). K3 calibration diagnostics (2). K4 intervals, standard errors, conformal sets (3). K5 abstention or selective prediction (2) |
| Features (10) | F1 structured covariates and missing values (3). F2 irregular timestamps (3). F3 wallet or on-chain specific handling (2). F4 cross-token or per-key features (2) |
| Decision and stress (10) | D1 no false confidence (3: flags or abstains; 2: bounded with a built-in correction; 1: bounded, no correction, or a confirmed degenerate tail; 0: confirmed invalid output without warning). D2 decision thresholds or risk control (3). D3 hooks for capacity or fees: weights, custom risks or losses (2). D4 stress behaviour: loud failure, abstention, shift detection (2) |
| Code quality (8) | Q1 tests green at the pin (2). Q2 release history and pin to release parity (2). Q3 dependencies (2). Q4 smoke without library defects (2) |
| Integration fit (8) | I1 Python 3.13 and lab runtime (numpy 2, pandas 3.0.5), wheels incl. Windows (2). I2 clean, composable API (2). I3 isolation, no host side effects (2). I4 fills a Phase 01 gap cell without duplicating lab code (2) |
| Reproducibility (8) | R1 determinism (2). R2 persistence (2: identical round trip with a supported non-executable format; 1: pickle only). R3 lineage and audit records (2). R4 metrics or run audit (2) |
| Cost and reliability (5) | L1 offline, no paid calls (2). L2 latency inside the ACCEPTANCE limits (2). L3 loud failure on bad input (1) |
| Licensing and security (7) | S1 license at the pin (3). S2 transitive licenses and notices (1). S3 data and weight rights (1). S4 safe install, no secrets, no network in the core path (1). S5 non-pickle persistence (1) |

## My reruns

All offline (`unshare -n`), `OMP_NUM_THREADS=1`, Python 3.13.17, venvs under `/home/claude/pi_orchestration/rescore/venvs/`. Scripts and outputs in `/home/claude/pi_orchestration/rescore/reruns/`.

| Output | What it checks | Exit and key lines |
|---|---|---|
| `rr_purgedcv.out.txt` (sha256 `83b800d829db61c6...`) | purgedcv from the pinned tree: the review's hand case, my own 6 h case, GroupLeakageError, monotonic check, challenge folds against my own overlap counter | 0; purge kept [0, 1, 5] and [0, 6] as expected; PurgedKFold, WalkForwardSplit and PurgedGroupKFold 0 overlapping rows per fold; scikit-learn TimeSeriesSplit(5, 280) [90, 102, 110, 111, 91]; 0 shared mints |
| `rr_purgedcv_tests.out.txt` (sha256 `651117c285efce1a...`) | purgedcv suite at the pin | non-e2e: 461 passed in 8.30 s; one e2e test (`tests/e2e/test_e2e_prose_gate.py`) fails only because the dev tool `textstat` is not installed |
| `rr_mapie.out.txt` (sha256 `c355498d0460ee3b...`) | MAPIE from the pinned tree | 0; Venn-Abers probe above the calibration max: MAPIE p1 0.5000, isotonic definition 1.0000 (probe inside range: equal); NaN score returns [0.5278, 0.4722] without error; Pipeline with `cv="prefit"` changes the caller's base predictions by up to 0.01056; LAC at 0.90 coverage 0.9184, 0 of 17 positives covered, 29 empty sets; risk controller `best_predict_param` None with a warning; Spiegelhalter p 0.6215 |
| `rr_statsmodels.out.txt` (sha256 `67a107b63650d06a...`) | statsmodels 0.15.0 wheel; `tsa/regime_switching` is identical at the pin (`git diff --stat v0.15.0 HEAD` lists no file there) | 0; own seeded series: filter with train-window parameters, train-only versus extended series, max diff 0.0; smoothing with the same parameters differs by 0.2487; out-of-sample `predict` raises NotImplementedError; Holm [0.036, 0.06, 0.06] |
| `rr_hazardous.out.txt` (sha256 `b3223e254ad27546...`) | hazardous from the pinned tree, `n_iter=10` | 0; 252 NaN training rows accepted; fit 8.8 s; cumulative incidence of event 1 decreases somewhere for 627 of 634 holdout rows (largest drop 0.0576); predict_proba (634, 2), rows sum to 1; pickle identical; IBS 0.01487 |
| `wheel_parity.out.txt` (sha256 `a7492c2a47c9bb6c...`) | PyPI wheels against the pins (downloaded, never installed for this check) | purgedcv 0.1.11: 18 of 18 `.py` identical; MAPIE 1.6.0: 95 of 95 identical; hazardous 0.2.0 wheel (sha256 prefix `0c25c1b2f76f14bf`) holds `hazardous/data/seer_cancer_cardio_raw_data.txt` (213,846,118 bytes), the METABRIC table, `.ipynb_checkpoints` and `_negative_log_likelihood.py`, none in the pinned tree |

Other checks: dependency licenses from installed metadata in my four venvs (all BSD, MIT, Apache-2.0, PSF, MPL-2.0 for tqdm and hypothesis); `lifelines-0.30.3` METADATA `Requires-Dist: pandas<3.0,>=2.1`; the lab's system Python has numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1; PyPI release histories (JSON API).

## Per repository scores and evidence

Paths are at the pin, relative to the repository root. "raw" means the review's smoke output under `research/SMOKES/<owner>__<repo>/`.

### eslazarev/purged-cross-validation, 54

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 14/18 | T1 3: `WalkForwardSplit` `src/purgedcv/_walk_forward.py:18`, `PurgedKFold` `_purged_kfold.py:20`, `CombinatorialPurgedCV` `_cpcv.py:26`, times bound at `_base.py:52-107`; folds are row-count blocks (`_walk_forward.py:66`), so day folds need the public `purge` on custom indices. T2 5: `_purge.py:19-80`, `_intervals.py:68-98` half-open overlap; my hand cases and 0 overlaps per fold (rr_purgedcv). T3 2: `_embargo.py:74-140`; hand case embargo kept [0, 1]. T4 0: no feature input; raw S1 trap Brier 0.00325. T5 2: `evaluation_times` = `label_matures_at` enforces the "label matured by the cutoff" rule (rr_purgedcv). T6 2: monotonic check `_base.py:107`, NaT and inverted-time errors (raw input validation), `GroupLeakageError` via `_base.py:173-174` (rr_purgedcv) |
| Outcomes | 3/14 | O1, O2, O3, O5 0: a splitter produces no predictions; `_metrics.py:76,197` are Sharpe statistics, not outcome scores. O4 2: `PurgedGroupKFold` `_purged_kfold.py:125`, 0 shared mints per fold (rr_purgedcv). O6 1: label windows `[prediction_time, evaluation_time)` `_base.py:75-79` |
| Calibration | 0/12 | no probability, score, calibration, interval or abstention code in `src/purgedcv` (module list) |
| Features | 1/10 | F2 1: irregular decision gaps 0 to 6,694 s with a duplicate time accepted (raw). Others 0 |
| Decision | 4/10 | D1 2: PBO `_pbo.py:279`, noise 0.609 against 0.000 with a real effect (raw P22). D2 1: deflated Sharpe and minimum track record `_metrics.py:197,385`, source only, needs return series the lab does not have. D3 0. D4 1: loud refusal of unordered, NaT and inverted times (raw) |
| Code | 7/8 | Q1 2: 461 passed (rr_purgedcv_tests). Q2 1: 24 PyPI releases since 2026-05-16, one author, 0.x, subclass interface declared unstable `_base.py:45-49`; wheel equals pin (wheel_parity). Q3 2: numpy, pandas, scikit-learn, scipy `pyproject.toml:60-65`. Q4 2: no defect found (no `groups` on `WalkForwardSplit`, `_walk_forward.py:46-59`, is a limitation) |
| Integration | 8/8 | I1 2: pure wheel, `requires-python >=3.11` `pyproject.toml:10`, ran with pandas 3.1.0. I2 2: scikit-learn split protocol `_base.py:148`, public `purge` and `apply_embargo`. I3 2: no network code (grep), offline runs. I4 2: fills HIST_MARKET:MODEL_TRAINING (MISSING) and SOCIAL_REPLAY:MODEL_TRAINING ("single split, no walk-forward") without duplicating `replay_core.LabelGate` |
| Reproducibility | 6/8 | R1 2: no randomness, identical folds after reload (raw S5). R2 1: pickle only. R3 2: `audit_splitter` `diagnostics.py:133`, per-fold rows removed by purge and embargo (raw table). R4 1: PBO for the experiment ledger; no run registry |
| Cost | 5/5 | L1 2 offline. L2 2: folds 17 to 153 ms, PBO 43.65 s (raw). L3 1: ValueError on bad times |
| License | 6/7 | S1 3: MIT, `LICENSE` sha256 `554e85fd...` (checked). S2 1: dependency metadata BSD and MIT. S3 1: no weights or data. S4 1: hatchling, no install scripts. S5 0: pickle |

### interpretml/interpret, 42

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 1/18 | T5 1: `fit(..., sample_weight, bags)` `python/interpret-core/interpret/glassbox/_ebm.py:471-477`, bag codes `:487`; time-ordered bags ran (raw `smoke_output_pin.txt` S1_internal_validation); default is a random 15% validation per bag (raw defaults). T4 0: the leak became the top term (2.69) but was not refused (raw). Others 0 |
| Outcomes | 7/14 | O1 4: `predict_proba` `_ebm.py:3145`; shape (527, 2), rows sum to 1, pin and 0.7.8 identical (raw). O2 1: `survival_cox` `_ebm.py:4141` exists only at the pin (not in a release); Harrell C ran (raw `smoke_output_pin_cox.txt`), output is a log relative hazard with no P(event by horizon). O3 1: `EBMRegressor`. O5 1: ROC and PR explainers `interpret/perf/_curve.py:16,108`. O4, O6 0 |
| Calibration | 1/12 | K4 1: `standard_deviations_` across outer bags `_ebm.py:454,1639` (spread of shape functions, not a predictive interval). Others 0: no calibration method (raw `built_in_calibration: false`) |
| Features | 3/10 | F1 3: native missing bin, 252 NaN training rows (raw S3); interaction terms (raw term list). Others 0 |
| Decision | 2/10 | D1 1: bounded probabilities, terms readable, no correction path. D3 1: `sample_weight` `_ebm.py:475`, `monotone_constraints` `:1040`. D2, D4 0 |
| Code | 7/8 | Q1 2: `test_cox.py` 26 passed (raw). Q2 1: 50 releases since 2019, last 2026-03-17; the pin is 249 files past v0.7.8 with the same version string. Q3 2: numpy, pandas, scikit-learn, joblib. Q4 2: no library defect in the smoke |
| Integration | 7/8 | I1 2: wheel with native libraries for Linux, macOS and Windows x64 (review section 2; Python 3.13 run). I2 2: scikit-learn estimator. I3 2: fit and predict offline (raw `network_attempts: []`); unpkg JS `interpret/provider/_visualize.py:18` and the Dash server are visualisation only. I4 1: MODEL_TRAINING is MISSING but this overlaps the scikit-learn B2 role; survival unreleased |
| Reproducibility | 4/8 | R1 2: same seed identical (raw determinism). R2 1: pickle identical; JSON export reloads only through `UNTESTED_from_jsonable` `_ebm.py:1970`, format beta `_ebm_core/_json.py:332`. R3 1: full JSON model description and term importances. R4 0 |
| Cost | 5/5 | L1 2. L2 2: default fit 22.5 to 32.6 s, single row 0.15 ms (raw S6). L3 1: no silent failure seen |
| License | 5/7 | S1 2: MIT root, Apache-2.0 `shared/libebm/GaussianDistribution.hpp:2-4` compiled into libebm, notice obligation; wheel has no license metadata (review section 2). S2 1. S3 1. S4 1: network code only in visualisation. S5 0 |

### online-ml/river, 42

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 6/18 | T1 2: `simulate_qa` `river/stream/qa.py:213-242`, `progressive_val_score` `river/evaluate/progressive_validation.py:298`; input order assumed, not checked. T2 3: answers released only when `t_expire <= t` (`qa.py:224`), mementos ordered by `t_expire` (`qa.py:33-34`); 0 released before maturity (`blind/evidence/rerun_river.out.txt`); caveat: the final loop `qa.py:244` releases all 108 pending answers (raw `simulate_qa_end_flush`). T5 1: delay from `label_matures_at` configures maturity, but the flush needs a wrapper filter. T3, T4, T6 0 (raw S1 trap) |
| Outcomes | 7/14 | O1 3: `predict_proba_one` `river/linear_model/log_reg.py:97`, 527 finite values in [0.010, 0.165] (raw S2), no calibrator. O3 1: regressors. O5 2: `ROCAUC` `river/metrics/roc_auc.py:10`, `RollingROCAUC` `rolling_roc_auc.py:9`. O6 1: delayed release with the flush caveat. O2, O4 0 |
| Calibration | 2/12 | K1 1: `LogLoss` `river/metrics/log_loss.py:10`, no Brier. K4 1: `RegressionJackknife` `river/conf/jackknife.py:13`, regression only. Others 0 |
| Features | 4/10 | F1 1: dict features, omitted keys tolerated by the linear model; NaN corrupts weights (raw S3); `StatImputer` imputes `None` only `river/preprocessing/impute.py:224`. F2 2: irregular per-event moments (raw), `TimeRolling` `river/utils/rolling.py:133` (source). F4 1: `Agg`, `TargetAgg` by key `river/feature_extraction/agg.py:14,221` (source). F3 0 |
| Decision | 2/10 | D1 0: NaN prediction and non-finite weights without an error (raw S3). D3 1: weight `w` in `learn_one` `river/linear_model/base.py:182`. D4 1: ADWIN and PageHinkley found the log-liquidity shift with no train false alarm; the error-stream ADWIN missed calibration drift (raw). D2 0 |
| Code | 4/8 | Q1 2: 161 passed, 39 skipped (raw). Q2 1: 30 releases since 2021; the pin is 99 files past 0.26.1 and needs a Rust build. Q3 1: numpy, scipy, narwhals plus Rust crates at build; pandas extra capped below 3. Q4 0: NaN silently corrupts weights, `StatImputer` passes NaN, `compose.Select` KeyError on an omitted key `river/compose/select.py:136` (raw S3) |
| Integration | 5/8 | I1 1: release wheels exist, the pin needs a Rust toolchain. I2 1: dict-per-row API, not scikit-learn. I3 1: `rust-toolchain.toml` makes rustup install toolchain targets when cargo runs in the tree (file checked; effect per review section 2). I4 2: DRIFT_MONITORING is MISSING for HIST_MARKET and DECISION_RECORDS; ADWIN `river/drift/adwin.py:7`, PageHinkley `page_hinkley.py:7` |
| Reproducibility | 4/8 | R1 2: repeat run identical over 125 values (`blind/evidence/repeat_runs.json`). R2 1: pickle, Rust state round trip (raw S5). R4 1: progressive validation checkpoints. R3 0 |
| Cost | 4/5 | L1 2. L2 2: 12.9 and 4.5 microseconds per row (raw S6). L3 0: silent NaN |
| License | 4/7 | S1 3: BSD-3, `LICENSE` sha256 `e87f2c8f...` (checked). S2 0: Rust crates `Cargo.toml:28-35` not license-checked by anyone. S3 1. S4 0: toolchain side effect and crate downloads when building the pin. S5 0 |

### scikit-learn-contrib/MAPIE, 46

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 3/18 | T1 1: `TimeSeriesRegressor` (EnbPI, ACI) `mapie/regression/time_series_regression.py:20`, `BlockBootstrap` `mapie/subsample.py:104`, regression only, source only; `train_conformalize_test_split` shuffles by default `mapie/utils.py:35`. T5 1: prefit mode takes the wrapper's purged calibration rows (rr_mapie), but a Pipeline with `cv="prefit"` refits the caller's transformers on calibration rows (`mapie/calibration.py:992` before `:1000`; rr_mapie max change 0.01056). T6 1: exchangeability permutation test `mapie/exchangeability_testing/permutations.py:270` ran without false alarm, missed the shift (raw p 0.8905, 0.7264). T2, T3, T4 0 |
| Outcomes | 3/14 | O1 2: Venn-Abers probabilities (raw S4), with p1 wrong above the calibration max (rr_mapie 0.5000 against 1.0000; loop `mapie/_venn_abers.py:104-122`). O3 1: regression conformal. Others 0 |
| Calibration | 8/12 | K1 0: no Brier or log loss under `mapie/metrics/`. K2 2: `VennAbersCalibrator` `mapie/calibration.py:636`, defect above. K3 2: ECE `mapie/metrics/calibration.py:105`, Spiegelhalter `:826,878`, KS `:499,604`, Kuiper `:659,770`; Spiegelhalter p 0.6215 reproduced. K4 2: `SplitConformalClassifier` `mapie/classification.py:49`, marginal coverage 0.9184 at 0.90 reproduced, LAC only for binary (`mapie/conformity_scores/utils.py:123`), the rare class is never in a set (0 of 17). K5 2: `BinaryClassificationController` returns None when no threshold is valid (`mapie/risk_control/_base_controller.py:150-151`, rr_mapie), 29 empty sets |
| Features | 0/10 | defers to the wrapped estimator (raw S3) |
| Decision | 6/10 | D1 1: empty sets as abstention, but a NaN score returns a probability without error (rr_mapie) and the p1 defect. D2 3: Learn-then-Test risk control `mapie/risk_control/binary_classification.py:24`, abstains when invalid (rr_mapie). D3 1: custom risks `mapie/risk_control/risks.py:417` (source). D4 1: abstains with 16 calibration positives |
| Code | 6/8 | Q1 2: 234 passed (raw). Q2 2: 40 releases since 2021; 1.6.0 wheel equals pin (wheel_parity). Q3 2: numpy, scipy, scikit-learn. Q4 0: two confirmed defects (Venn-Abers p1; Pipeline prefit mutates the caller's estimator) plus one shared default estimator instance `mapie/classification.py:124` |
| Integration | 7/8 | I1 2: pure wheel, Python 3.10+. I2 1: scikit-learn style, but the prefit Pipeline mutation. I3 2: no network code (grep). I4 2: CALIBRATION_SCORING cells MISSING; conformal sets and risk control are not in scikit-learn |
| Reproducibility | 3/8 | R1 2: repeat run identical over 120 values (`repeat_runs.json`). R2 1: pickle. R3 0: the calibrator silently changes the frozen base model's preprocessing, breaking its lineage. R4 0 |
| Cost | 4/5 | L1 2. L2 2: microseconds per row (raw S6). L3 0: NaN score handled silently |
| License | 6/7 | S1 3: BSD-3, `LICENSE` sha256 `92372faa...` (checked). S2 1: `THIRD_PARTY_NOTICES.md` MIT notices for confseq and conditional-conformal. S3 1. S4 1. S5 0 |

### scikit-learn/scikit-learn, 58

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 5/18 | T1 2: `TimeSeriesSplit` `sklearn/model_selection/_split.py:1104`, gap counts rows `:1292-1296`; overlap [90, 102, 110, 111, 91] with test_size 280 (rr_purgedcv), [102, 106, 93, 99, 107] at gap 0 (raw S1_splitters). T2 1: custom split iterables `_split.py:2621,2674`; a day walk-forward ran with 0 maturity violations in 19 folds (raw). T5 2: `FrozenEstimator` `sklearn/frozen/_frozen.py:27`, `calibration.py:476-477`; calibration on the later window ran (raw S4). T6 0: `groups` ignored with a warning `_split.py:1247-1251`; GroupKFold put 1,834 to 1,842 later rows in training (raw). T3, T4 0 |
| Outcomes | 8/14 | O1 4: `predict_proba` `_logistic.py:1881`, HGB `gradient_boosting.py:2148`; (527, 2), rows sum to 1 (raw S2). O3 1: `QuantileRegressor` `sklearn/linear_model/_quantile.py:20`. O4 1: group-aware CV exists, not temporal. O5 2: `roc_auc_score` `sklearn/metrics/_ranking.py:508`, `average_precision_score` `:128`. O2, O6 0 |
| Calibration | 7/12 | K1 2: `brier_score_loss` `sklearn/metrics/_classification.py:3708`, `log_loss` `:3318`, `d2_brier_score` `:3988`. K2 3: `CalibratedClassifierCV` `calibration.py:179` with sigmoid `:1107`, isotonic `:842`, temperature `:1162`; frozen path ran (raw S4). K3 1: `calibration_curve` `:1328` without bin counts (raw). K4 1: quantile losses for regression only; no classification interval (raw). K5 0 |
| Features | 3/10 | F1 3: HGB missing-value bin `gradient_boosting.py:616-618`, 77 NaN holdout rows finite (raw S3); logistic raises on NaN. Others 0 |
| Decision | 3/10 | D1 1: isotonic gave exact 0.0 probabilities (raw S4 `min_p: 0.0`), a calibration path exists. D2 1: `TunedThresholdClassifierCV` `sklearn/model_selection/_classification_threshold.py:499`, cost-sensitive threshold, no guarantee (source). D3 1: `sample_weight` and `class_weight`. D4 0 |
| Code | 8/8 | Q1 2: 137 passed, 138 skipped (raw). Q2 2: 76 releases since 2011; pin `1.10.dev0` (`sklearn/__init__.py:45`), `calibration.py` changed since 1.9.1 (checked). Q3 2. Q4 2 |
| Integration | 8/8 | I1 2: the lab's system Python already imports scikit-learn 1.9.1; Windows cp313 wheels (review). I2 2. I3 2: network only in dataset fetchers (grep), raw `network_attempts: []`. I4 2: MODEL_TRAINING and CALIBRATION_SCORING MISSING; B2 and B3 in ACCEPTANCE_METRICS need exactly this |
| Reproducibility | 5/8 | R1 2: identical predictions (raw). R2 1: pickle and joblib identical, bytes differ across fits (raw S5). R3 1: version stamp `sklearn/base.py:517`, mismatch warning `:523-529`. R4 1: per-fold scores from `cross_validate` `_validation.py:101` (raw fold Brier list) |
| Cost | 5/5 | L1 2. L2 2: fits 0.0074 and 0.19 s, single row 0.82 to 1.91 ms (raw S6). L3 1: ValueError on NaN |
| License | 6/7 | S1 3: `COPYING` BSD-3 (checked). S2 1: vendored MIT and BSD notices. S3 1. S4 1: meson build. S5 0: pickle; skops is a separate package |

### soda-inria/hazardous, 32

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 1/18 | T5 1: `recalibrate_survival_function` `hazardous/metrics/_km_calibration.py:221` ran with the later val split (raw S4). Others 0 (raw S1) |
| Outcomes | 9/14 | O1 3: `predict_proba(X, time_horizon)` `hazardous/_survival_boost.py:467`, (634, 2) rows sum to 1 (rr_hazardous). O2 2: competing risks `_survival_boost.py:171` with IPCW `hazardous/_ipcw.py:11,166`, maps onto the T1 race; each time is predicted separately (`:508`) and the curve is not monotone (raw 634 of 634, rr_hazardous 627 of 634). O5 2: `concordance_index_incidence` `metrics/_concordance_index.py:11`, `accuracy_in_time` `metrics/_accuracy_in_time.py:8`. O6 2: censored rows kept as censored, not negatives (raw). O3, O4 0 |
| Calibration | 5/12 | K1 2: `integrated_brier_score_incidence` `metrics/_brier_score.py:500` and survival `:328` (rr_hazardous IBS 0.01487). K2 1: marginal, unclipped recalibration. K3 2: `aj_calibration_per_event` `_aj_calibration.py:109`, `km_calibration` `_km_calibration.py:142` (raw). K4, K5 0 |
| Features | 2/10 | F1 2: `check_array(..., ensure_all_finite="allow-nan")` `_survival_boost.py:379`, 252 NaN rows accepted (rr_hazardous). Others 0 |
| Decision | 0/10 | D1 0: non-monotone incidence curves (structural); another seed moves P by up to 0.169 (raw). D3 0: `fit(X, y, times=None)` has no weights `_survival_boost.py:350`. D2, D4 0 |
| Code | 3/8 | Q1 2: 104 passed (raw). Q2 0: two releases; 0.2.0 artifacts differ from any commit (wheel_parity); TODO on defaults and convergence `_survival_boost.py:318-322`. Q3 1: lifelines pulls about 30 packages (matplotlib, autograd) and caps pandas below 3. Q4 0: the package's own metric rejects the documented dict `y` (raw first run); incidence docstring contradicted by non-monotone output |
| Integration | 3/8 | I1 0: `lifelines` requires `pandas<3.0` while the lab runs pandas 3.0.5 (both checked). I2 1. I3 1: offline, but a PyPI install drops 214 MB of third-party data. I4 1: a comparator for the T1 race; the EVENT_LABELS gap is a label builder, not a model |
| Reproducibility | 2/8 | R1 1: same seed identical, other seed up to 0.169 (raw). R2 1: pickle identical (rr_hazardous). R3 0: release artifacts not traceable to source. R4 0 |
| Cost | 3/5 | L1 2. L2 1: predict 0.052 ms per row; default fit 253.8 s under load (raw), 8.8 s at 10 iterations (rr_hazardous). L3 0 |
| License | 4/7 | S1 3: MIT at the pin. S2 1: lifelines MIT, tqdm MPL-2.0 and MIT. S3 0: SEER and METABRIC files in 0.2.0 without terms; the loader points to a gated download page `hazardous/data/_seer.py:139-141`. S4 0: artifacts differ from the source tree. S5 0 |

### statsmodels/statsmodels, 43

| Criterion | Score | Items and evidence |
|---|---:|---|
| Temporal | 1/18 | T5 1: filtering with train-window parameters is truncation invariant (raw 0.0; rr_statsmodels 0.0); default `predict` uses smoothed probabilities `statsmodels/tsa/regime_switching/markov_switching.py:816`. Others 0: irregular DatetimeIndex ignored (raw ValueWarning) |
| Outcomes | 7/14 | O1 4: `Logit` `statsmodels/discrete/discrete_model.py:2620`, matches GLM within 6.1e-16 (raw S2). O2 1: `PHReg` `statsmodels/duration/hazard_regression.py:340` with `baseline_cumulative_hazard` `:1414,1854`, tests `duration/tests/test_phreg.py`, not smoked. O3 1. O4 1: `GEE` `statsmodels/genmod/generalized_estimating_equations.py:489`, `MixedLM` `statsmodels/regression/mixed_linear_model.py:648` (source). O5, O6 0 |
| Calibration | 3/12 | K4 3: coefficient standard errors and per-row mean intervals (raw S2, S4); `proportion_confint` Wilson `statsmodels/stats/proportion.py:114` within 9.0e-06 of the lab's `alpha_core.wilson` (raw); Holm `statsmodels/stats/multitest.py:100` (raw and rr_statsmodels). Others 0 |
| Features | 2/10 | F1 2: exog and formula covariates, `exog_tvtp` `markov_regression.py:96`; default refuses NaN `statsmodels/base/data.py:61`. F2, F3, F4 0: positions only, one series per model (raw) |
| Decision | 2/10 | D1 0: quasi-separation gave p down to 2.7e-23 with no warning (raw S1). D3 1: `freq_weights`, `var_weights` `statsmodels/genmod/generalized_linear_model.py:287-288`. D4 1: ConvergenceWarning at small N, MissingDataError by default (raw). D2 0 |
| Code | 7/8 | Q1 2: 507 passed (raw). Q2 2: 41 releases since 2012; `tsa/regime_switching` unchanged since v0.15.0 (checked). Q3 2: patsy BSD-2, formulaic MIT, pandas 3 works. Q4 1: `predict` docstring promises out-of-sample forecasting (`markov_switching.py:763`) but raises NotImplementedError (`:806-807`; rr_statsmodels) |
| Integration | 6/8 | I1 2: 0.15.0 cp313 Windows wheels on PyPI (checked). I2 1: not the scikit-learn API. I3 2: network only in `statsmodels/datasets/utils.py`. I4 1: Holm fills a need; Wilson duplicates `alpha_core.wilson` (PLANNED_SEAMS intervals row); Logit overlaps the B2 role |
| Reproducibility | 4/8 | R1 2. R2 1: pickle `statsmodels/base/model.py:2452`, unsafe-load warning `:2486`; identical (raw S5). R3 1: results keep standard errors and convergence records. R4 0 |
| Cost | 5/5 | L1 2. L2 2: Logit fit 0.002 s, Markov 1.3 s (raw S6). L3 1: MissingDataError by default |
| License | 6/7 | S1 3: `LICENSE.txt` BSD-3 (checked). S2 1. S3 1. S4 1. S5 0 |

## Flags

| Repository | Flag | Basis |
|---|---|---|
| statsmodels | LEAKAGE_FAIL, scoped to `MarkovRegression` | default `predict` uses smoothed probabilities and full-sample parameters (`markov_switching.py:816`); out-of-sample `predict` is not implemented (`:806-807`), so as-of regime features need custom code (fit on the training window, then `filter`). Logit, GLM, Holm and Wilson are not flagged |
| statsmodels | RESEARCH_ONLY, scoped to regime states | latent regimes are not testable events; ACCEPTANCE_METRICS allows no regime claim on 17 days |
| river | LEAKAGE_FAIL, scoped to model state after a replay | `progressive_val_score` learns every answer `simulate_qa` yields (`progressive_validation.py:133-157`), including the end-of-stream flush of answers not matured by the last decision (`qa.py:244`; 108 in the smoke). No option turns the flush off, so a model artifact saved after a replay has learned labels from after its cutoff (P13) unless custom code stops the stream. Drift detectors and predictions made during the replay are unaffected |
| interpret | RESEARCH_ONLY, scoped to `survival_cox` | exists only at the pin, not in any release, and returns a log relative hazard with no baseline hazard |
| hazardous | REJECT, scoped to the PyPI 0.2.0 wheel and sdist | bundled SEER registry file (214 MB) and METABRIC table with no data-use terms, and contents that differ from the source tree (wheel_parity). The pinned MIT source is not rejected |
| purgedcv, scikit-learn, MAPIE | none | a splitter is not a forecasting model, so RESEARCH_ONLY does not apply to purgedcv; scikit-learn and MAPIE can be run strictly as of through their own APIs (custom iterables, FrozenEstimator, prefit); feature availability is the lab's job for every repository here |

No repository is NOT_REALTIME: inference is under 2 ms per row everywhere; hazardous and interpret fits are offline batch jobs.

## Review claims I found false, imprecise or missing

- interpret, S4 "has_term_standard_deviations false": the smoke probed `term_standard_deviations_` (`SMOKES/interpretml__interpret/smoke_interpret.py:288`), but the attribute is `standard_deviations_` (`_ebm.py:454`, set at `:1639`). Per-term uncertainty across bags exists. Small effect (1 point under K4).
- MAPIE, S3 "Venn-Abers core returns [0.5, 0.5] for a NaN score": with my calibration set it returned [0.5278, 0.4722]. The value depends on the calibration set; the finding that matters (a probability and no error) holds.
- MAPIE, "63 test files": I count 62 `test_*.py` files at the pin. Immaterial.
- statsmodels: the review left `PHReg` unscored; the pin has a baseline cumulative hazard (`hazard_regression.py:1414,1854`) and tests, so P(event by horizon) is available from source. I gave it 1 source-only point.
- scikit-learn: the review does not mention `TunedThresholdClassifierCV` or quantile losses; I credit them from source (D2 1, O3 1, K4 1).
- river: the review says "Not LEAKAGE_FAIL". I disagree for the replay-trained model state (see Flags) because `progressive_val_score` itself learns the flushed answers; the review's containment (filter the flush) is exactly the custom code the flag describes.
- Every other load-bearing claim I checked held: purgedcv purge, embargo, input validation and wheel parity; MAPIE p1 defect, Pipeline mutation, LAC coverage and the controller's abstention; statsmodels truncation test and `NotImplementedError`; hazardous release contents, NaN acceptance and non-monotone curves; river release rule and flush; licenses and their hashes.

## Limits of this rescore

- scikit-learn, interpret and river were not rebuilt from the pin (4 to 5 minute builds, a Rust toolchain side effect); their behaviour items rest on the reviewers' raw outputs from pin builds plus my source reading. My statsmodels rerun used the 0.15.0 wheel, which is identical to the pin only for `tsa/regime_switching`.
- Item weights inside each criterion are my reading of the rubric; another reasonable split moves a criterion by a point or two, not a total by 10.
- Where my scores could differ most from the lead's: purgedcv earns almost nothing outside temporal integrity because it makes no predictions; hazardous loses heavily on release artifacts and runtime fit; the two scoped LEAKAGE_FAIL flags.

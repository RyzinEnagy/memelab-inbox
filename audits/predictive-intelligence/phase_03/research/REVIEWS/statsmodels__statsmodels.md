# Source review: statsmodels/statsmodels

Reviewer R1, Phase 03. Smoke data are the shared synthetic challenge (`challenge.csv`, sha256 `18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d`): format and behaviour only, never memecoin predictive value. Holdout scored rows 527 (17 positives), 107 censored rows excluded, training prevalence B0 = 0.04238. The Markov smoke uses the `ret_1h` column in decision-time order (3,000 irregularly spaced points with a mean shift in the holdout), not 5-minute candles.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | statsmodels/statsmodels, https://github.com/statsmodels/statsmodels |
| Pinned SHA | `aa61cc148b820898247052008652b4dc4bda665e` |
| Commit date | 2026-10-23T16:15:38+01:00 ("Merge pull request #10467 from shan3520/bug-7978-mixedlm-missing") |
| How fetched | `git init; git fetch --depth 1 https://github.com/statsmodels/statsmodels.git <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/statsmodels__statsmodels` (67 MB) |
| Review time (UTC) | 2026-10-24T04:33Z to 06:00Z |
| Version tested | built from the pinned source (`uv pip install <clone>`, meson-python and Cython, 5 min 28 s, exit 0) into `/home/claude/pi_research/venvs/statsmodels__statsmodels` (Python 3.13.17, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0, patsy 1.0.3, formulaic 1.2.2). Reported version `0.1.dev1+gaa61cc148`: setuptools_scm on a shallow clone cannot count commits since the last tag, but the local part carries the pin hash. Latest release 0.15.0 (2026-08-27) differs from the pin in 192 files, including `discrete/discrete_model.py` (97 lines: Logit log-likelihood now uses a stable `log(1+exp)`, `_log_1pexp` at `discrete_model.py:2732,2765`) and `stats/multitest.py` (59 lines: p-values and alpha are now range-checked). `tsa/regime_switching/` is unchanged since 0.15.0 |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | `LICENSE.txt` at the pin: BSD-3-Clause (copyright Jonathan E. Taylor, Scipy Developers, statsmodels Developers) |
| Nested | `statsmodels/stats/libqsturng/LICENSE.txt` BSD-3-Clause, `statsmodels/multivariate/factor_rotation/LICENSE.txt` BSD-3-Clause with `COPYRIGHTS.txt`, `tsa/statespace/tests/results/frbny_nowcast/Nowcasting/LICENSE` BSD-3-Clause (test data) |
| Runtime deps | numpy, scipy, pandas, patsy (BSD), formulaic (MIT), packaging |
| Model weights | none |
| Build scripts | meson build; nothing network-related beyond fetching build requirements from PyPI |
| Network | none observed (0 connect attempts at import, fit, predict, save, load). Network code exists only in dataset helpers: `statsmodels/datasets/utils.py:228` (`urlopen` for `get_rdataset`) |
| Telemetry | none found |
| Persistence safety | `results.save` writes a pickle (`statsmodels/base/model.py:2452-2477`); the docstring itself warns "Loading pickled models is not secure against erroneous or maliciously constructed data" (`:2486-2487`) |

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Logit | `statsmodels/discrete/discrete_model.py:2620` Logit, `:2646` cdf, `:2701` loglike, `:2890` fit; `:561` BinaryModel.predict; perfect-prediction check `:231-244` (warns PerfectSeparationWarning only when fitted values equal the labels exactly) |
| GLM Binomial | `statsmodels/genmod/generalized_linear_model.py` (`get_prediction` gives a mean CI per row) |
| Missing data | `statsmodels/base/data.py:61` default `missing="none"`, `:686` handle_missing |
| Holm and FDR | `statsmodels/stats/multitest.py:100` multipletests, `:343` fdrcorrection |
| Wilson interval | `statsmodels/stats/proportion.py:114` proportion_confint, `:296` wilson branch |
| Regime model (N07) | `statsmodels/tsa/regime_switching/markov_regression.py:13` MarkovRegression, `:96` init (`exog_tvtp` for time-varying transitions); `markov_switching.py:492` MarkovSwitching, `:759` predict, `:806-807` `if out_of_sample > 0: raise NotImplementedError`, `:816` default weighting = smoothed probabilities, `:884` filter, `:1009` smooth, `:1179` fit |
| Survival (not smoked) | `statsmodels/duration/hazard_regression.py:340` PHReg (Cox proportional hazards with censoring) exists; not tested here, so not scored |
| Serialization | `statsmodels/base/model.py:2452` save, `:2480` load, `statsmodels/iolib/smpickle.py` |
| Tests | 296 `test_*.py` files. Subset at the pin: `pytest --pyargs statsmodels.tsa.regime_switching.tests.test_markov_regression statsmodels.stats.tests.test_multi`: 507 passed, exit 0, 11 s (`SMOKES/statsmodels__statsmodels/repo_tests_subset.txt`) |

## 4. Smoke results

Script `SMOKES/statsmodels__statsmodels/smoke_statsmodels.py`, output `smoke_output.txt`, run line `smoke_run.txt`: `OMP_NUM_THREADS=1 <venv>/bin/python -I smoke_statsmodels.py challenge.csv <scratch>`, exit 0, wall 3.4 s, peak RSS 180.2 MB.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (library stops nothing) | Logit with train-median imputation and standardisation: BSS 0.0095, AUC 0.696 without the trap; BSS 0.9788, AUC 1.000 with it; leak coefficient 10.6; minimum holdout probability 2.7e-23; no PerfectSeparationWarning (separation is quasi, not exact) |
| S2 probability shape | PASS | Logit and GLM Binomial agree to 6.1e-16; probabilities finite, in [0, 1]; Brier 0.031022 vs B0 0.031320, log loss 0.1385 vs 0.1439; coefficients with standard errors (e.g. log volume 0.573, SE 0.127) |
| Small N (120 rows, 2 positives) | FAIL as expected | `ConvergenceWarning: Maximum Likelihood optimization failed to converge`; probabilities down to 1.8e-14; BSS -0.0084 |
| S3 missing covariates | FAIL by default | default `missing="none"`: `MissingDataError: exog contains inf or nans`. `missing="drop"`: fit used 1,494 of 1,746 rows, and predict returned NaN for all 77 holdout rows with a missing feature (P38: a NaN probability would reach a display unless the wrapper checks). Imputation is the wrapper's job |
| S4 uncertainty | PASS for its scope | Holm on p = (0.012, 0.030, 0.041): adjusted (0.036, 0.060, 0.060), equal to a hand computation; an out-of-range p-value now raises `ValueError: p-values must be in the range [0, 1]` (new at the pin). `proportion_confint(method="wilson")` matches the lab's `alpha_core.wilson` (memelab/social/alpha_core.py:125) within 9.0e-06 over all k for n in {5, 20, 50, 58, 100, 300} (the lab uses z = 1.96, statsmodels the exact quantile). GLM mean CI per row: median width 0.034, max 0.336. No calibration, conformal or abstention method |
| S5 persistence | PASS (unsafe format) | `save`/`load` pickle 129,077 bytes, identical predictions; with `remove_data=True` 3,268 bytes, identical predictions |
| Markov regime (role-specific) | PASS with LEAKAGE by default | 2-regime switching mean and variance, fit 1.3 s on 3,000 points. Full-sample fit: holdout 87.2% in the high-mean regime vs train 0.5%, val 0.0% (the regime is defined by holdout data). Truncation test on the 1,746 training-window points: filtered probabilities with parameters fit on the training window alone are identical whether or not later data are present (max abs diff 0.0); filtered probabilities with full-sample parameters differ by up to 0.728; smoothed vs filtered differ by up to 0.919. Train-only parameters (p00 0.077, p10 0.318) describe a different, fast-switching regime split than the full-sample fit (p00 0.9997). `predict` beyond the sample: `NotImplementedError`. A DatetimeIndex with irregular spacing raises `ValueWarning: A date index has been provided, but it has no associated frequency information`: time stamps are ignored, only positions count. One series per model, so no panel of many short token series |
| S6 cost | PASS | Logit fit 0.002 s, GLM 0.005 s, single-row predict 0.005 ms; Markov 1.3 s; offline; 0.15.0 has `cp313-win_amd64` and `cp313-win_arm64` wheels |

## 5. Claims the code does not support (P42)

- UNSUPPORTED: `MarkovSwitching.predict` docstring "In-sample prediction and out-of-sample forecasting" (`markov_switching.py:763`, parameters `start`/`end` "at which to start forecasting"); the code raises `NotImplementedError` for any out-of-sample point (`:806-807`), confirmed in the smoke.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity (18) | 3 | Filtered regime probabilities with training-window parameters pass a truncation test (diff 0.0); but `predict` defaults to smoothed (future-using) probabilities, full-sample fits move training-window states by up to 0.728, no splitters or availability concept, leak passed through |
| Transferable predictive outcomes (14) | 6 | Logit and GLM probabilities with standard errors; quasi-separation not flagged; small N fails to converge; survival model exists but was not tested |
| Calibration and uncertainty (12) | 6 | Holm verified and range-checked, Wilson equal to the lab's within 9e-6, per-row mean CIs; no calibration, conformal or abstention |
| Catalyst, social, on-chain features (10) | 2 | Regime state features for one series (N07), time-varying transition covariates (`exog_tvtp`); irregular timestamps ignored, no panel, NaN not handled |
| Decision and execution compatibility (10) | 1 | Offsets and weights in GLM; nothing execution-related |
| Code quality, maintenance, tests (8) | 6 | 296 test files, 507 relevant tests pass at the pin, recent numerical-stability and validation fixes; releases are infrequent (0.14.6 on 2025-12-05, 0.15.0 on 2026-08-27) |
| Integration fit (8) | 6 | cp313 and Windows wheels, depends on numpy, scipy, pandas already near the lab; pulls pandas 3.x and formula libraries |
| Reproducibility and audit (8) | 5 | Deterministic fits, results pickles reload exactly, readable summaries with standard errors; no run ledger |
| Cost, latency, reliability (5) | 5 | Millisecond fits and predictions, 180 MB, offline |
| Licensing, security, data rights (7) | 6 | BSD-3-Clause verified; pickle persistence (documented warning); network only in dataset helpers; no telemetry |
| Total | 46 | |

## 7. Flags and adversarial scenarios

- LEAKAGE_FAIL for MarkovRegression as configured by default (smoothed probabilities in `predict`, parameters fit on the whole series). Containment that passed the truncation test: fit parameters on the training window only, then run `filter` forward; never use `smoothed_marginal_probabilities` or full-sample parameters as features.
- RESEARCH_ONLY for regime states: 17 days of one market regime (ACCEPTANCE_METRICS "no regime claim"); the smoke shows a train-only fit finds a different regime structure than the full-sample fit.
- P13 and P36: the regime truncation test is the executable catch (0.0 vs 0.728 vs 0.919 differences).
- P38: `missing="drop"` produces NaN probabilities at predict time; wrapper must impute or abstain (OOD).
- P10 and P24: the small-N Logit failed to converge and produced 1e-14 probabilities; the display clip and count gates are needed.
- P42: the out-of-sample forecasting docstring above.

## 8. Proposed role and integration decision

- Role: B2 cross-check with standard errors (Logit), Holm adjustment across T1, T1b, T2, and Wilson intervals (already equal to `alpha_core.wilson`); MarkovRegression only as an isolated research feature generator with the train-window-then-filter rule.
- INTEGRATION_DECISION: INSTALL (Logit, multipletests, proportion_confint); MarkovRegression ISOLATED_RESEARCH.
- Gap cells addressed: DECISION_RECORDS:MODEL_TRAINING, HIST_MARKET:MODEL_TRAINING (N01), HIST_MARKET:CALIBRATION_SCORING, TRADE_OUTCOMES:CALIBRATION_SCORING (N03, Holm and Wilson); N07 regime states for REGIME_NARRATIVE:MODEL_TRAINING only as research.

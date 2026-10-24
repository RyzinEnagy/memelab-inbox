# Source review: bashtage/arch (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | bashtage/arch, https://github.com/bashtage/arch |
| Pinned SHA | `5db69b011f6291dc46eadfcde57a1f7c9041d85a` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-10-22T08:45:08+01:00 |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/bashtage__arch`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:18Z |
| Version tested | built from the pinned source with meson-python and Cython (`SETUPTOOLS_SCM_PRETEND_VERSION=8.0.0+pin5db69b01`, because the version comes from `arch/_build/git_version.py` via setuptools_scm and the shallow clone has no tags); both Cython extensions compiled (`arch/bootstrap/_samplers`, `arch/univariate/recursions`); build took 23 s. Venv `/home/claude/pi_research/venvs/bashtage__arch`, Python 3.13.17, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0, statsmodels 0.15.0 |
| Relation to PyPI | the pin is unreleased development code: the latest release, 8.0.0 (sdist 2025-10-21, sha256 `5e9895c2354b9475...`), differs in 73 of its 111 `.py` files, including `arch/bootstrap/base.py`, `multiple_comparison.py` and `__init__.py`. Results apply to the pin, not to 8.0.0 |

## 2. License and security

- Root `LICENSE.md`: permissive University of Illinois/NCSA-style text ("Copyright (c) 2017 Kevin Sheppard", "to deal with the Software", plus the three BSD-style conditions), sha256 `c6e622bd89db4e13315f4e91605ff96fcbb9012d78ee74e429855870b203eed6` (matches Phase 02). `pyproject.toml` declares `license = "NCSA"`; Phase 02 recorded MIT with the flag LICENSE_NCSA_STYLE. Either way permissive; obligation: keep the notice and the disclaimers, do not use the author's name for endorsement.
- Vendored code: `arch/vendor/_decorators.py` holds docstring decorators taken from pandas (its comment says "Typing variables from pandas"; pandas is BSD-3) with no separate license header; imported by `arch/covariance` and `arch/unitroot`, not by `arch/bootstrap`. Phase 02's scan found no different license header.
- Runtime dependencies: numpy, pandas, scipy, statsmodels, packaging (BSD and Apache-2.0); build needs Cython, meson-python and a C compiler. Licenses: `SMOKES/bashtage__arch/raw_dep_licenses.txt`.
- Model weights: none. Install-time scripts: meson build only; `arch/_build/git_version.py` calls setuptools_scm. The scripts under `arch/unitroot/critical_values/simulation/` use `os.system("color")` and `pickle.load`, but they are offline research scripts for generating critical values and are not imported at runtime.
- Network: no network code in the package (grep); smoke ran inside `unshare -n`. No telemetry.
- Secrets: none. Persistence: bootstrap state is the seed plus the data; pickle not required.

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Bootstraps | `arch/bootstrap/base.py:458` IIDBootstrap, `:762` conf_int (basic, percentile, studentized, norm, bc, bca), `:1729` CircularBlockBootstrap, `:1914` StationaryBootstrap, `:2031` MovingBlockBootstrap, `:152` optimal_block_length (Politis and White) | several arrays can be resampled jointly with the same indices, so paired model and baseline losses stay aligned |
| Samplers | `arch/bootstrap/_samplers.pyx` (compiled) with a Python fallback `arch/bootstrap/_samplers_python.py:6` | |
| Multiple comparison | `arch/bootstrap/multiple_comparison.py:286` MCS, `:621` StepM, `:796` SPA, `:1310` RealityCheck | block bootstrap of loss differentials |
| Volatility models | `arch/univariate/mean.py:3203` `arch_model`; convergence handling `arch/univariate/base.py:1252` (ConvergenceWarning) | GARCH family, forecasts |
| Group / cluster bootstrap | none | resampling whole days or mints needs per-cluster aggregation by the caller (done in the smoke with IIDBootstrap) |
| Time handling | block bootstraps assume a regularly ordered series; no timestamps | |
| Tests | 84 test files | ran `arch/tests/bootstrap/test_block_length.py`, `test_samplers.py`, `test_bootstrap_fixes.py`, `test_multiple_comparison.py`: 186 passed in 33.24 s, exit 0 (`SMOKES/bashtage__arch/raw_repo_tests_arch.txt`) |

## 4. Smoke results

Script `SMOKES/bashtage__arch/smoke_arch.py` inside `unshare -n`; exit 0, wall 10.07 s, peak RSS 174.4 MB; raw output `SMOKES/bashtage__arch/raw_smoke_arch.txt`. Inputs: per-row Brier loss of the shared base model and of the train-prevalence baseline on the 527 labeled holdout rows in decision-time order (17 positives, 107 censored excluded; base holdout hash `cc58f5135049e5ed`, same as the calibration reviews); holdout covers 6 UTC days (47, 108, 87, 116, 112, 57 rows), 254 mints, 120 symbols.

Block bootstrap of the Brier score and the Brier skill score (point: Brier 0.03089, BSS 0.0123; 2000 resamples, seed 20261024, 95% percentile intervals):

| Method | Brier interval | Width | BSS interval | Includes 0 |
|---|---|---:|---|---|
| IID | 0.01818 to 0.04478 | 0.02659 | -0.0408 to 0.0561 | yes |
| IID BCa | 0.01921 to 0.04612 | 0.02691 | -0.0326 to 0.0646 | yes |
| Stationary, mean block 2.39 (optimal_block_length) | 0.01710 to 0.04576 | 0.02865 | -0.0408 to 0.0577 | yes |
| Stationary, mean block 97 (about one day of rows) | 0.02195 to 0.04073 | 0.01878 | -0.0195 to 0.0418 | yes |
| Moving block, block 97 | 0.02022 to 0.04159 | 0.02137 | -0.0160 to 0.0518 | yes |
| Circular block, block 3 (optimal) | 0.01702 to 0.04559 | 0.02857 | -0.0400 to 0.0594 | yes |
| Cluster over 6 UTC days (IIDBootstrap on day sums) | 0.01857 to 0.04264 | 0.02407 | -0.0430 to 0.0379 | yes |
| Cluster over 254 exact mints | 0.01759 to 0.04606 | 0.02847 | -0.0429 to 0.0621 | yes |
| Cluster over 120 symbols (identity trap, merges mints) | 0.01690 to 0.04648 | 0.02958 | -0.0383 to 0.0571 | yes |

A one-day block on 527 rows leaves about 5 blocks, and its interval came out narrower than the IID one; the day-cluster interval rests on 6 clusters. Neither is trustworthy at this size (P23, P24); the optimal-block and mint-cluster intervals are the honest ones here.

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | not a guard (by design) | leaky model BSS 0.9452 with a stationary 95% interval 0.9095 to 0.9767: a bootstrap measures sampling noise and cannot detect look-ahead |
| S2 probability shape | SKIPPED | arch produces no classifier probabilities; Brier inputs came from the shared base model |
| S3 missing values | FAIL (silent in conf_int) | one NaN in the loss series: `conf_int` returns `[nan, nan]` without an error; `optimal_block_length` raises `ValueError: x must be an array of finite numbers` |
| S4 interval coverage | PASS | Monte Carlo, clustered binary series (Markov, P(1 after 1) 0.5, P(1 after 0) 0.02, true mean 0.0385, n 500), 200 simulations of 399 resamples, nominal 90%: IID coverage 0.715, stationary with optimal block 0.875, stationary block 25 0.865 (5.7 s) |
| S5 persistence | PASS | pickled bootstrap (13,664 bytes) gives the identical interval after reload; same seed twice identical, different seed differs |
| S6 cost | PASS | 2000-resample stationary bootstrap on 527 rows 0.05 s; peak RSS 174 MB; offline. Release 8.0.0 has cp313 wheels for Linux, macOS and win_amd64; the pin needs a C compiler (or the meson `no-binary` option) to build. File list: `SMOKES/bashtage__arch/raw_pypi_files_r2.txt` |
| Role: model comparison (P22) | PASS | SPA, benchmark train prevalence vs base LR, score100-only LR and a noise model: p-values 0.306 (lower), 0.306 (consistent), 0.377 (upper), so no model beats the baseline. MCS at 90%: keeps prevalence, base LR and score100-only LR; drops the noise model |
| Role: volatility models | PASS with a caution | GARCH(1,1) on 2016 simulated 5-minute returns (true 0.02, 0.10, 0.85): estimates 0.015, 0.078, 0.878, standard errors 0.004, 0.013, 0.021, 17 ms. On 60 returns (5 hours of candles): 0.001, 0.0, 1.0 (alpha at 0, beta at 1, a degenerate fit) with convergence flag 0 and no warning |

## 5. Claims the code does not support (P42)

- None found UNSUPPORTED for the bootstrap and multiple-comparison claims tested.
- Caution: a GARCH fit on a short series returns a boundary solution with `convergence_flag = 0` and no warning; nothing in the output says the estimate is unusable.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 1 | block bootstraps keep serial dependence when intervals are computed over time-ordered rows (S4 coverage 0.875 vs IID 0.715); nothing about feature cutoffs, purging or label maturity (S1) |
| Transferable measurable predictive outcomes (14) | 2 | volatility forecasting for return series (role row); degenerate on 60 observations; no event classification |
| Calibration, uncertainty and abstention (12) | 6 | block, stationary and BCa intervals for Brier and BSS with joint resampling (table), verified coverage gain (S4), SPA and MCS for model comparison; it quantifies metric uncertainty, not probability calibration; NaN gives a silent NaN interval |
| Catalyst, social and on-chain features (10) | 0 | volatility is a market covariate and needs long regular series; memelab tokens are young and candles have gaps |
| Decision and execution compatibility (10) | 1 | variance forecasts could inform risk; the silent degenerate GARCH fit is a false-confidence risk (role row) |
| Code quality, maintenance and tests (8) | 7 | 84 test files, 186 bootstrap tests pass; maintained since 2014, commit two days before the pin was taken; typed; compiled code with a Python fallback |
| Integration fit and extensibility (8) | 5 | numpy, scipy, pandas, statsmodels; release wheels for 3.13 and Windows (S6); the pin itself needs a compiler; group bootstrap by day or mint needs caller-side aggregation |
| Experiment reproducibility and audit (8) | 4 | seeded Generator, identical intervals on rerun and after pickle (S5); no lineage |
| Cost, latency and operational reliability (5) | 5 | 0.05 s per 2000 resamples, 174 MB, offline (S6) |
| Licensing, security and data rights (7) | 7 | NCSA-style permissive license, no network, no runtime install hooks; research scripts with pickle are not imported (section 2) |
| **Total** | **38** | |

## 7. Flags and adversarial scenarios

- Flags: none.
- P22: SPA and MCS give the "one lucky model among many" check on the frozen holdout; here they correctly found nothing beating the base rate.
- P23 and P24: a one-day block on 527 rows and a 6-day cluster bootstrap produce intervals that look tight but rest on 5 or 6 units; the lab should print the number of blocks or clusters next to every interval.
- P14 and P01: cluster resampling by exact mint is done by the caller; grouping by symbol merges 254 mints into 120 groups (shown), which the library cannot detect.
- P38: NaN loss gives a NaN interval without an error; the wrapper must refuse non-finite inputs.
- New wrong-but-plausible case found: "longer blocks are always safer" fails at this sample size; the day-length block gave a narrower interval than IID because only about 5 blocks exist; caught by comparing widths across block lengths and against the coverage simulation.

## 8. Proposed role and integration decision

Offline evaluation for Phase 12: the 95% interval on Brier skill by stationary bootstrap with the optimal block length, a cluster bootstrap by exact mint and by decision day (per-cluster sums with IIDBootstrap, as in the smoke), and SPA or MCS over the experiment ledger's candidate models. Not in the forecast path. Volatility models are not recommended for young tokens.

Candidate INTEGRATION_DECISION: ADAPTER (offline only; prefer the released wheel over building the pin, and record the exact version used). Phase 01 gap cells addressed: HIST_MARKET:CALIBRATION_SCORING (MISSING) and TRADE_OUTCOMES:CALIBRATION_SCORING (PARTIAL), for the interval and model-comparison parts. License obligation if code is copied: the NCSA-style notice and disclaimers.

# Source review: lorentzenchr/model-diagnostics (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | lorentzenchr/model-diagnostics, https://github.com/lorentzenchr/model-diagnostics |
| Pinned SHA | `d0d8eec5f7188b8184fb5222e9c17786c07a1cc3` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-04-26T18:26:05+02:00 |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/lorentzenchr__model-diagnostics`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:16Z |
| Version tested | 1.5.0 (`src/model_diagnostics/__about__.py`) built from the pinned source with hatchling, venv `/home/claude/pi_research/venvs/lorentzenchr__model-diagnostics`, Python 3.13.17, polars 2.0.0 (with polars-runtime-32 2.0.0), matplotlib 3.11.2, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pandas 3.1.0 |
| Relation to PyPI | the 35 `.py` files of `model_diagnostics-1.5.0-py3-none-any.whl` (2026-04-25, sha256 `155042d758fd0a0c...`) are byte-identical to the pin |

## 2. License and security

- Root `LICENSE`: MIT ("Copyright (c) 2022 Christian Lorentzen"), sha256 `45620685cb77a014792bedebed40488f505a9ed0241a0a1f8001bda1fefcf929` (matches Phase 02). No vendored code found.
- Runtime dependencies: matplotlib (PSF-style), numpy, packaging, polars (MIT, binary runtime in polars-runtime-32, MIT), scikit-learn, scipy. Installed licenses: `SMOKES/lorentzenchr__model-diagnostics/raw_dep_licenses.txt` (BSD, MIT, PSF, MIT-CMU for pillow, Apache-2.0).
- Model weights: none. Install-time scripts: none (hatchling build).
- Network: no network code (grep). The smoke, including matplotlib rendering with `MPLCONFIGDIR` in scratch, ran inside `unshare -n`. No telemetry in this package; polars_cloud is an optional extra and was not installed.
- Secrets: none. Persistence: not applicable (stateless functions).
- Phase 02 flagged SERVER_STACK in the dependency scan; nothing server-like is imported by the package; plotly is an optional plot backend (not installed).

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Score decomposition | `src/model_diagnostics/scoring/_scoring.py:701` `decompose`; recalibration by scikit-learn isotonic regression for the mean (`:846`) | score = miscalibration - discrimination + uncertainty (CORP) |
| Scoring functions | `_scoring.py:252` SquaredError, `:339` LogLoss, `:410` HomogeneousQuantileScore, `:581` ElementaryScore | strictly consistent scores for mean, quantile and expectile |
| Conditional calibration | `src/model_diagnostics/calibration/_compute.py:21` `compute_bias` (t-test p-values, `:340` to `:343`; p set to 0 when the standard error is 0), `:381` `compute_marginal` | bias per feature bin with standard error |
| Reliability diagram | `calibration/_plots.py:29` `plot_reliability_diagram` (isotonic, optional `scipy.stats.bootstrap` bands, `:178`) | no fixed bins; `n_bootstrap` is annotated `Optional[str]` but is an int |
| Isotonic regression | `src/model_diagnostics/_utils/isotonic.py:280` | internal PAV for quantile and expectile functionals |
| Time handling | none | no notion of time or availability |
| Output types | polars DataFrames | callers using pandas or numpy convert |
| Tests | 13 test files | ran `calibration/tests/test_compute.py`, `scoring/tests/test_scoring.py`, `_utils/tests/test_isotonic.py`: 294 passed, 4 failed, 11 skipped, exit 1 (`SMOKES/lorentzenchr__model-diagnostics/raw_repo_tests_model_diagnostics.txt`). All 4 failures are `ImportError: pyarrow is required` for pandas categorical and string feature inputs; pyarrow is in the project's test environment, not in its runtime dependencies. I did not install pyarrow |

## 4. Smoke results

Script `SMOKES/lorentzenchr__model-diagnostics/smoke_model_diagnostics.py` inside `unshare -n`; exit 0, wall 2.83 s, peak RSS 241.6 MB; raw output `SMOKES/lorentzenchr__model-diagnostics/raw_smoke_model_diagnostics.txt`; plot `SMOKES/lorentzenchr__model-diagnostics/reliability_base_vs_leaky.png`. Shared base model and purged splits as in the other calibration reviews (holdout 527 rows, 17 positives, 107 censored excluded; base holdout hash `cc58f5135049e5ed`).

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | not a guard (by design) | the leaky model's discrimination term is 0.03122 vs 0.00117 for the base; the library scores whatever it is given |
| S2 scores | PASS | library Brier and log loss equal own computation exactly (max difference 0.00e+00). Brier decomposition (MCB, DSC, UNC, score): train prevalence 0.00006, 0.0, 0.031217, 0.031277; base 0.000845, 0.00117, 0.031217, 0.030893; leaky 0.001714, 0.031217, 0.031217, 0.001714. Log-loss decomposition: prevalence 0.000834, 0.0, 0.142506, 0.14334; base 0.00882, 0.013692, 0.142506, 0.137634 |
| S3 missing values | PARTIAL | `decompose` raises `ValueError: Input X contains NaN` for a NaN prediction and `Input y contains NaN` for a NaN outcome (good); calling `SquaredError()(y, p)` directly with a NaN returns `nan` silently. In `compute_bias`, NaN feature values form their own bin |
| S4 calibration | PASS with one caution | reliability by isotonic recalibration (PAV blocks, base model): [0.0008, 0.0015] n 8, recal 0.0000; [0.0016, 0.0142] n 134, 0.0075; [0.0142, 0.0263] n 137, 0.0146; [0.0263, 0.0458] n 118, 0.0339; [0.0465, 0.0699] n 70, 0.0571; [0.0701, 0.1149] n 41, 0.0732; [0.1177, 0.1489] n 10, 0.1000; [0.1570, 0.3235] n 9, 0.2222. Own fixed bins for comparison: 10 uniform bins ECE 0.00331, 5 quantile bins ECE 0.00617, all quantile bins inside Wilson 95%. Reliability diagrams with 200 bootstrap resamples rendered offline in 1.01 s. `compute_bias` overall: bias 0.003314, standard error 0.007662, p 0.666. By liq_usd quartile: three bins with p 0.36, 0.36, 0.54; the null-liq bin (30 rows, 0 positives) reports bias 0.0330, p 2.2e-7, although 0 positives in 30 rows at mean p 0.033 has probability 0.362. The t-test uses the spread of p - y only, so rare-event bins can show spurious significance |
| S5 persistence | SKIPPED | stateless functions, nothing to persist; repeated call returned an identical DataFrame |
| S6 cost | PASS | `decompose` 1.49 ms for one model, 12.1 ms for three; peak RSS 242 MB (polars plus matplotlib); offline. PyPI ships a `py3-none-any` wheel, Python 3.13 declared and tested; polars and matplotlib have Windows wheels |

## 5. Claims the code does not support (P42)

- None found UNSUPPORTED. The README's "score decomposition into miscalibration, discrimination and uncertainty" was reproduced exactly against own Brier and log loss.
- Caution, not a claim: `compute_bias` p-values are labelled as a 2-sided t-test; for binary outcomes in small bins with no positives they overstate significance (S4).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 0 | no time or availability notion (S1) |
| Transferable measurable predictive outcomes (14) | 2 | evaluates mean, quantile and expectile predictions with strictly consistent scores (S2); produces no outcome model |
| Calibration, uncertainty and abstention (12) | 7 | exact decomposition (S2), isotonic reliability with bootstrap bands, conditional bias by feature with standard errors (S4); minus the misleading rare-event p-values; no recalibration method or abstention |
| Catalyst, social and on-chain features (10) | 0 | none |
| Decision and execution compatibility (10) | 0 | none |
| Code quality, maintenance and tests (8) | 6 | 13 test files, 294 of 298 selected tests pass, the 4 failures are a missing test-only dependency; ruff and mypy configured; author is a scikit-learn core developer; last commit 2026-04-26, single main maintainer |
| Integration fit and extensibility (8) | 4 | pure Python and Python 3.13 (S6), but adds polars and matplotlib (242 MB RSS) and returns polars DataFrames to a numpy/pandas codebase |
| Experiment reproducibility and audit (8) | 3 | deterministic stateless outputs (S5) and audit-friendly decomposition tables; no lineage; bootstrap bands depend on scipy's RNG (not seeded in my test) |
| Cost, latency and operational reliability (5) | 4 | millisecond computations, offline (S6); heavy import and memory for what it does |
| Licensing, security and data rights (7) | 7 | MIT, permissive dependencies, no network, no persistence needed (section 2) |
| **Total** | **33** | |

## 7. Flags and adversarial scenarios

- Flags: none.
- P23: reports Brier and log loss decompositions side by side with counts possible; useful when the two disagree.
- P24: the conditional-bias p-value in a 30-row, 0-positive bin (p 2.2e-7) is the kind of false precision the lab must not print; report Wilson intervals on counts instead.
- P38: NaN predictions are rejected by `decompose`, not by the bare scoring function.
- P31: MIT; pass.
- New wrong-but-plausible case found: a "significant" miscalibration in a small bin with zero events (p 2.2e-7) that is consistent with chance (probability 0.362); caught by computing the exact chance of zero events in that bin.

## 8. Proposed role and integration decision

The CORP decomposition (miscalibration, discrimination, uncertainty) maps directly onto the ACCEPTANCE_METRICS reports, and it is about 20 lines with scikit-learn's isotonic regression; the smoke showed the library's numbers equal own Brier and log loss. Keep the package in the research venv as a cross-check for Phase 08 to 12 reports rather than adding polars and matplotlib to the lab.

Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION (decomposition and reliability in-house, this package as an offline oracle). Phase 01 gap cells addressed: DECISION_RECORDS:CALIBRATION_SCORING (MISSING), HIST_MARKET:CALIBRATION_SCORING (MISSING), SOCIAL_REPLAY:CALIBRATION_SCORING (PARTIAL). License obligation if code is copied: MIT notice.

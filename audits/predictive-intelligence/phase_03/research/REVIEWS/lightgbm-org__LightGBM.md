# Source review: lightgbm-org/LightGBM

Reviewer R1, Phase 03. Smoke data are the shared synthetic challenge (`challenge.csv`, sha256 `18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d`): format and behaviour only, never memecoin predictive value. Holdout scored rows 527 (17 positives, prevalence 0.0323), 107 censored rows excluded, training prevalence B0 = 0.04238.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | lightgbm-org/LightGBM (renamed from microsoft/LightGBM, Phase 02 seed rename), https://github.com/lightgbm-org/LightGBM |
| Pinned SHA | `064a6db10c080e23f3aebc41d5a75dec00426b8a` |
| Commit date | 2026-10-23T20:12:45-05:00 ("[c++] hide symbols that aren't in the C API (#7496)") |
| How fetched | `git init; git fetch --depth 1 https://github.com/lightgbm-org/LightGBM.git <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/lightgbm-org__LightGBM` (27 MB, submodules not fetched) |
| Review time (UTC) | 2026-10-24T04:35Z to 05:50Z |
| Version tested | PyPI wheel `lightgbm==4.7.0` (`lightgbm-4.7.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`, released 2026-07-18) in `/home/claude/pi_research/venvs/lightgbm-org__LightGBM` (Python 3.13.17, scikit-learn 1.9.1 for the sklearn API). This is NOT the pin: `VERSION.txt` at the pin reads `4.7.0.99`. `git diff --stat v4.7.0 HEAD`: 143 files; `python-package/` 7 files (1,960 insertions, 506 deletions, in `sklearn.py` mostly docstrings moved inline, plus `dask.py`), `src/` and `include/` 31 files. The pin was not built (needs five submodules and CMake); results describe 4.7.0 |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | `LICENSE` at the pin: MIT, "Copyright (c) Microsoft Corporation, Copyright (c) The LightGBM developers" |
| Nested | `R-package/LICENSE` (R package only, not used) |
| Code compiled into the library | git submodules: Eigen (gitlab.com/libeigen/eigen), fmt, fast_double_parser, boost compute, arrow-nanoarrow (`.gitmodules`). `CMakeLists.txt:119-124` compiles Eigen with `-DEIGEN_MPL2_ONLY` (MPL-2.0 parts only). The 4.7.0 wheel's `lib_lightgbm.so` contains Eigen symbols (21 `strings` matches) but the wheel ships only LightGBM's own MIT `LICENSE` (`lightgbm-4.7.0.dist-info/licenses/LICENSE`): third-party notices for compiled-in code are missing from the wheel. A distribution concern only; use is not restricted |
| Native runtime | `lib_lightgbm.so` links system `libgomp.so.1` (GCC runtime, GPL with the runtime exception), `libstdc++` |
| Python deps | numpy, scipy, narwhals (MIT); scikit-learn optional |
| Model weights | none |
| Install scripts | binary wheel; no install-time code run |
| Network | none observed (0 connect attempts at import, fit, predict). Sockets exist only in `python-package/lightgbm/dask.py:73-75` (distributed training ports) |
| Telemetry | none found |
| Persistence safety | native text model (`Booster.save_model`, `basic.py:4550`) is parsed by C++, no code execution; pickle of the sklearn wrapper executes code on load |
| Secrets | none |

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| sklearn API | `python-package/lightgbm/sklearn.py:385` LGBMModel, `:825` fit, `:1757` LGBMClassifier, `:1944` fit, `:2232` predict_proba |
| Training and CV | `python-package/lightgbm/engine.py:108` train, `:639` cv with defaults `stratified=True`, `shuffle=True` (`:645-646`), `:526` `_make_n_folds`: custom `folds` iterable or splitter accepted (`:540-553`), otherwise `_LGBMStratifiedKFold(shuffle=shuffle, random_state=seed)` (`:568-572`, = sklearn StratifiedKFold per `compat.py:104`) |
| Booster and serialization | `python-package/lightgbm/basic.py:3670` Booster, `:3830`/`:3839` getstate/setstate, `:4550` save_model, `:4623` model_from_string, `:4660` model_to_string, `:4724` dump_model |
| Parameters | `include/LightGBM/config.h:271` `deterministic = false` default, `:716` `use_missing = true`, `:720` `zero_as_missing = false`, `:935` `is_unbalance`, `:942` `scale_pos_weight` |
| Time handling | none: no timestamp, availability or maturity concept anywhere in the Python package |
| Calibration | none (no calibration module; `predict_proba` is the raw sigmoid of the boosted score) |
| Tests | 13 `test_*.py` under `tests/` (12 in `tests/python_package_test`: test_sklearn 69, test_engine 137, test_basic 49 test functions) and 12 C++ test sources in `tests/cpp_tests`. Subset of the pin's tests run against the 4.7.0 wheel: `test_sklearn.py -k "binary or probability or predict_proba"`: 29 passed, 22 skipped, exit 0, 6.8 s (`SMOKES/lightgbm-org__LightGBM/repo_tests_subset.txt`) |

## 4. Smoke results

Script `SMOKES/lightgbm-org__LightGBM/smoke_lightgbm.py`, output `smoke_output.txt`, run line `smoke_run.txt`: `OMP_NUM_THREADS=1 <venv>/bin/python -I smoke_lightgbm.py challenge.csv <scratch>`, exit 0, wall 6.1 s, peak RSS 182.4 MB. Parameters: 200 trees, learning rate 0.03, 15 leaves, `deterministic=True`, `force_row_wise=True`, `n_jobs=1`, seed 7.

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (library stops nothing) | holdout BSS -0.0085, AUC 0.633 without the trap; BSS 0.8932, AUC 1.000 with it |
| S1 cv | FAIL by default, PASS with custom folds | `lgb.cv` defaults (stratified, shuffled) ran without complaint; rebuilding the same StratifiedKFold(shuffle=True, random_state=7) indices puts 1,834 to 1,842 later rows into each training fold. A 19-fold custom day walk-forward iterable was accepted |
| S2 probability shape | PASS | shape (527, 2), rows sum to 1, finite, in [0, 1]; Brier 0.031585 vs B0 0.031320, log loss 0.1562 vs 0.1439 (worse than base rate) |
| S2 imbalance switches | FAIL for calibration | `is_unbalance=True`: mean p 0.0994 vs holdout prevalence 0.0323, BSS -0.8104. `scale_pos_weight=10`: mean p 0.0735, BSS -0.4055 |
| Small N (300 rows, 13 positives) | FAIL at defaults | default params BSS -0.1313, AUC 0.493; shrunk (4 leaves, 40 per leaf, lambda 5, 100 trees) BSS -0.0282, AUC 0.626 |
| S3 missing covariates | PASS | 252 training and 77 holdout rows with NaN; native handling (`use_missing=True`), all probabilities finite |
| S4 calibration | FAIL (none) | raw probabilities: 1 of 3 quantile bins inside the Wilson 95% interval (bin means 0.0020, 0.0078, 0.0582 vs observed 0.0114, 0.0455, 0.0400). No interval for class probabilities (quantile objective is regression only) |
| S5 persistence | PASS | native text model 349,142 bytes, reload via `Booster(model_file=...)` gives identical predictions (max abs diff 0.0); text sha256 `51e72e0c...` identical across two separate runs (`smoke_output_run1.txt` and `smoke_output.txt`); pickle round trip identical |
| Determinism | PASS | same seed twice: identical trees; `n_jobs=1` vs `n_jobs=2`: identical trees and probabilities (environment had `OMP_NUM_THREADS=1`; actual thread use not measured) |
| S6 cost | PASS | fit 0.075 s; batch predict 0.012 ms per row; single row 0.46 ms via sklearn wrapper, 0.036 ms via Booster; offline; Windows wheel `lightgbm-4.7.0-py3-none-win_amd64.whl` (Python-version independent, so Python 3.13 is covered) |

## 5. Claims the code does not support (P42)

- None used for scoring. The `deterministic` parameter documentation was checked by experiment (identical trees) rather than taken on trust.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity (18) | 3 | Accepts custom fold iterables (19 walk-forward folds ran); defaults shuffle across time (1,834 to 1,842 later rows per training fold); no availability or maturity concept; leak trap passed through (BSS 0.8932) |
| Transferable predictive outcomes (14) | 5 | Binary probabilities with correct shape, regression and quantile objectives exist; at 300 rows the default model was worse than base rate (BSS -0.131, AUC 0.49); no survival or censoring |
| Calibration and uncertainty (12) | 1 | Only the log-loss metric; raw probabilities 1 of 3 bins inside Wilson; imbalance switches inflate mean p threefold; no intervals or abstention |
| Catalyst, social, on-chain features (10) | 2 | Native NaN and categorical handling; nothing time- or event-aware |
| Decision and execution compatibility (10) | 2 | Sample weights, custom objectives and monotone constraints (`monotone_constraints` in the model dump); no execution or cost hooks |
| Code quality, maintenance, tests (8) | 6 | 13 Python and 12 C++ test files, relevant subset passes; active commits; 17 months between 4.6.0 (2025-02-15) and 4.7.0 (2026-07-18); repo moved organisation |
| Integration fit (8) | 6 | Python-agnostic wheels incl. Windows, small deps, sklearn API; adds an OpenMP runtime dependency |
| Reproducibility and audit (8) | 6 | `deterministic=True` reproduces trees exactly; human-readable text model with stable sha256 and embedded parameters; no run ledger |
| Cost, latency, reliability (5) | 5 | 0.075 s fit, 0.036 ms single-row booster inference, 182 MB, offline |
| Licensing, security, data rights (7) | 6 | MIT verified; Eigen limited to MPL-2.0; text model load executes no code; wheel omits third-party notices for compiled-in code |
| Total | 42 | Scores rest on the 4.7.0 wheel, not on a build of the pin |

## 7. Flags and adversarial scenarios

- Flags: none of REJECT, NOT_REALTIME. Not LEAKAGE_FAIL (custom folds work), but `lgb.cv` defaults must be banned in the wrapper. Its probabilities need an external calibration layer before any display (ACCEPTANCE_METRICS calibration tolerance).
- P10 and P11 (low base rate, degenerate output): `is_unbalance` and `scale_pos_weight` move mean predictions far above the observed rate; they must stay off in the lab.
- P13 and P20: default CV mixes future rows into training; only the custom walk-forward iterable is acceptable.
- P22 (one lucky fit among many): many hyperparameters at 100 to 300 events; every configuration must go to the Phase 12 ledger.
- P42: version 4.7.0 tested, not the pin; scores say so.

## 8. Proposed role and integration decision

- Role: the "complex model" comparator for Phase 08 (must beat B2 by a Brier difference with a lower bound above 0), trained only through the lab's walk-forward iterable, shrunk hyperparameters, `deterministic=True`, then calibrated with scikit-learn on a later window. Not a default engine at the lab's sample sizes.
- INTEGRATION_DECISION: INSTALL (research comparator only; text model format for artifacts; pin the wheel version).
- Gap cells addressed: DECISION_RECORDS:MODEL_TRAINING, HIST_MARKET:MODEL_TRAINING (need N01).

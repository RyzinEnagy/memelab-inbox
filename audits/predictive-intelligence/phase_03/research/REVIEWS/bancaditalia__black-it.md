# bancaditalia/black-it (reviewer R5)

Black-box calibration of agent-based models: it searches simulator parameters so that simulated time series match an observed one. "Calibration" here means parameter estimation, not probability calibration; the rubric's calibration criterion is about probabilities and is scored that way. Reviewed as the fitting step for an LLM-free behavioral comparator (see `mesa__mesa.md`).

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | bancaditalia/black-it, https://github.com/bancaditalia/black-it |
| Pinned SHA | `6577b3cc12d26be0eff1924694dd58ede7a5ae6e` ("docs: update release history with version 0.3.3"), equal to the remote HEAD and `main` at review time |
| Commit date | 2025-11-17T10:21:33+01:00 (2025-11-17T09:21:33Z); no commit in the 11 months since |
| How fetched | `git fetch --depth 1 origin <sha>` into `/home/claude/pi_research/src/bancaditalia__black-it` (38 MB), 2026-10-24T04:33Z; tag `v0.3.3` (`8019ea97`, "chore: bump version to 0.3.3") also fetched |
| Review time (UTC) | 2026-10-24T04:54Z to 05:35Z |
| Version tested | the pinned tree on `PYTHONPATH`, with dependencies from the PyPI `black-it==0.3.3` wheel resolution (Python 3.12.3). `git diff 8019ea97 HEAD -- black_it pyproject.toml` is empty, so PyPI 0.3.3 (uploaded 2025-11-17) carries the same package code as the pin. First test run with scikit-learn 1.9.1 and scipy 1.17.1; then scikit-learn 1.6.1, scipy 1.13.1, joblib 1.5.2 (the `poetry.lock` values) for the second test run and both smokes (`SMOKES/bancaditalia__black-it/venv_freeze.txt`) |
| Venv and clone | venv `/home/claude/pi_research/venvs/bancaditalia__black-it` (793 MB) deleted after the review; clone kept at `/home/claude/pi_research/src/bancaditalia__black-it`; `venv_freeze.txt` in SMOKES lists the final installed versions |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | GNU AGPL version 3, `LICENSE` 661 lines, sha256 `d6e088f2fc2918a7e29eb8ec4dcc9fa28608a730f272785be49819169113e33f` (matches Phase 02); `pyproject.toml` and file headers say AGPL-3.0-or-later ("Copyright (C) 2021-2024 Banca d'Italia", `black_it/calibrator.py:1-15`) |
| AGPL obligations | copying any black-it code into memelab is forbidden by PI-D-005 and would make memelab (public, no LICENSE file) a covered work (P31). Importing it in-process from memelab code that is conveyed is, on the FSF reading, a combined work (INFERENCE, not legal advice). Running it privately in its own venv and process on files memelab writes keeps the obligations to notices. Section 13 matters only if a modified copy is offered to others over a network, which no plan here does |
| Transitive licenses | numpy, pandas, scipy, scikit-learn, statsmodels, h5py, seaborn, ipywidgets: BSD; xgboost 1.7.6: Apache-2.0; gymnasium 0.27.1: MIT; matplotlib: PSF-based. No other copyleft found |
| Model weights | none |
| Install-time scripts | none: all dependencies from wheels (`--only-binary :all:`), source from the clone |
| Network | no `requests`, `urllib`, `socket` or `subprocess` use in `black_it/`; tests and smokes ran inside a loopback-only namespace |
| Telemetry | none found |
| Unsafe deserialization | checkpoints store the scheduler and the loss function as pickles (`black_it/utils/json_pandas_checkpointing.py:180` dump, `:62-65` `pickle.load`, marked `# nosec B301`; the SQLite variant `sqlite3_checkpointing.py:254-255` uses `pickle.loads`); `Calibrator.restore_from_checkpoint` (`calibrator.py:246`) loads them. A checkpoint from an untrusted source can run code. The repo ships two example pickles (`examples/saving_folder/*.pickle`) |
| Resource default | `n_jobs=None` becomes `multiprocessing.cpu_count()` (`calibrator.py:141`) |

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Calibration loop | `black_it/calibrator.py:51` `Calibrator(BaseSeedable)`, `:56-100` constructor (loss, `real_data`, `model(theta, N, seed)`, bounds, precision, `ensemble_size`, samplers or scheduler, `random_state`, `n_jobs`), `:345` `calibrate(n_batches)` returns parameters and losses sorted by loss |
| Simulation calls | `:319` `simulate_model`: each parameter repeated `ensemble_size` times, `joblib.Parallel` over `model(param, N, seed)` with seeds drawn from the calibrator's generator (`:335`, `utils/seedable.py:77`) |
| Seeding | `utils/seedable.py:29` `BaseSeedable`; samplers re-seeded per batch from the calibrator seed (`calibrator.py:176-182`) |
| Losses | `loss_functions/msm.py:55` `MethodOfMomentsLoss` (18 moments from `utils/time_series.py`, including autocorrelations), plus Fourier, GSL-div, likelihood and Minkowski losses |
| Missing values | `utils/time_series.py:87` `np.nan_to_num(avg_vec_mom, copy=False)`: NaN moments become 0 without a warning |
| Samplers | Halton, R-sequence, random uniform, best batch, random forest, XGBoost, Gaussian process, particle swarm, CORS (`samplers/`); schedulers round robin and an epsilon-greedy bandit (`schedulers/`) |
| Time handling | none: `real_data` is a plain array; no timestamps, cut-off or availability concept |
| Uncertainty | none for parameters: point estimates ranked by loss; `ensemble_size` only averages simulator noise |
| Persistence | `create_checkpoint` (`calibrator.py:482`): `calibration_params.json`, `calibration_results.csv`, `series_samp.h5`, two pickles |
| Tests | 47 Python files under `tests/` (CI matrix: Linux, macOS, Windows; Python 3.9 to 3.12). Offline subset (calibrator, losses, samplers, search space, utils): 71 passed, 6 failed, exit 1, 58 s (`SMOKES/bancaditalia__black-it/blackit_pytest_offline.txt`). The 6 failures are golden-value checks (`test_calibrator_calibrate[1]`, `[2]`, `test_best_batch_2d`, `test_random_forest_2d`, `test_xgboost_2d`, `test_clip_losses`); they fail the same way with the locked scikit-learn, scipy and joblib versions (`blackit_pytest_offline_locked_sklearn.txt`) and with or without pytest-randomly, so they are deterministic here but do not match the stored values. The tests already carry a separate win32 expectation (`tests/test_calibrator.py:85`, `:104`, `:181-186`, issue 49). Cause on this machine: UNKNOWN |

## 4. Smoke results

`SMOKES/bancaditalia__black-it/smoke_blackit_calibrate.py`: a vectorised numpy trader-reaction model (momentum share `m`, price impact `a`, 50 traders, one fictional catalyst shock at step 20) returns a 120-step synthetic return series. The target series comes from known parameters (a 0.02, m 0.6, seed 123); black-it with Halton and best-batch samplers (6 batches of 8, ensemble 3, 144 model runs) must recover them. Inside a loopback-only namespace; exit 0, 3 s wall (`smoke_blackit_output.txt` raw, `smoke_blackit_summary.json`).

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (nothing stops it) | `real_data` is accepted as given; a series that runs past a decision cut-off is calibrated without complaint (`S1_series_past_cutoff_accepted`). The wrapper must cut the series at the decision time |
| S2 probability shape | SKIPPED | black-it outputs parameters and losses, not probabilities |
| S3 missing values | FAIL (silent) | one NaN in a 100-step target series: calibration runs, no warning, losses change from [2.563, 3.474, 5.275, 8.968] to [5.440, 5.840, 6.274, 7.850] for the same sampled parameters (`smoke_blackit_nan_output.json`), because NaN moments are set to 0 (`time_series.py:87`) |
| S4 calibration or uncertainty | none offered | parameter recovery: best (a, m) = (0.017, 0.73) with random_state 1 and (0.023, 0.54) with random_state 2 against the true (0.02, 0.60); top five with seed 1 span a 0.013 to 0.018 and m 0.55 to 0.73. The library gives no interval for that spread |
| S5 persistence and determinism | PASS with a security caveat | same random_state: byte-identical parameters and losses; different random_state: different results. Checkpoint files: `calibration_params.json`, `calibration_results.csv`, `series_samp.h5`, `loss_function_pickled.pickle`, `scheduler_pickled.pickle` (pickle on restore) |
| S6 cost | PASS | 0.60 s and 0.58 s per calibration of 144 model runs (about 4 ms per run including overhead), peak RSS 164.8 MB, no network. Python 3.13 not supported (`python >=3.9,<3.13`, PyPI `requires_python <3.13,>=3.9`) and numpy pinned below 1.27, so it cannot be installed into memelab's Python 3.13 and numpy 2 environment; pure-Python wheel, Windows in CI |
| Role: ABM parameter fitting | PASS (feasibility) | recovers the right region of a 2-parameter trader model from 120 points in under a second; with only 17 days of real decisions, identifiability on real data would be weak |

## 5. README or docs claims the code does not support (P42)

None found that the code contradicts. README and `docs/description.md` describe samplers and losses that exist at the pin. The word "calibration" must not be read as probability calibration.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 2 | No pretrained knowledge; results depend only on the supplied series and seed (S5); no cut-off or availability mechanism, a series past the cut-off is accepted (S1) |
| Transferable measurable predictive outcomes (14) | 2 | Fits parameters of a simulator that can then produce testable events; no outcome model of its own (S4 recovery numbers) |
| Calibration, uncertainty and abstention (12) | 1 | `ensemble_size` averaging of simulator noise only; no parameter intervals, no probability calibration |
| Catalyst/social/on-chain features (10) | 1 | Time-series moment, Fourier and divergence losses (`loss_functions/`); no event covariates |
| Decision/execution and stress compatibility (10) | 0 | Nothing relevant |
| Code quality, maintenance and tests (8) | 4 | 47 test files, CI on three operating systems, release 0.3.3; 6 golden-value tests not reproduced here; no commit in 11 months; pickle checkpoints |
| Integration fit and extensibility (8) | 2 | Clean `model(theta, N, seed)` interface; Python <3.13 and numpy <1.27 rule out memelab's environment; AGPL keeps it in a separate venv and process |
| Experiment reproducibility and audit (8) | 5 | Seeded end to end with identical reruns (S5); checkpoints record parameters, losses, series, batch and sampler per point; results differ across environments (section 3 tests) |
| Cost, latency and operational reliability (5) | 4 | Under a second for 144 runs of a small model, 165 MB, offline; default `n_jobs` takes every CPU; cost is dominated by the user's simulator |
| Licensing, security and data rights (7) | 3 | AGPL-3.0-or-later verified; permissive dependencies; no network; pickle-based checkpoint restore |
| **Total** | **24** | |

## 7. Flags

- RESEARCH_ONLY: produces parameter estimates, not forecasts; a fitted behavioral model still needs out-of-sample evidence in Phase 15.
- Not LEAKAGE_FAIL: it reads only what it is given, so a cut series gives a strict as-of fit; S1 shows it will not enforce the cut.
- Not NOT_REALTIME for small models, but it is an offline fitting step by design.
- P13: fitting on a window that includes post-decision data and replaying earlier decisions with those parameters is a model trained on the future; nothing in the library prevents it.
- P31: AGPL; keep out of the repo and out of memelab's process.
- P32: no install scripts; the pickle restore path is the code-execution risk.

## 8. Proposed role and integration decision

- Role: offline parameter fitting for the LLM-free behavioral comparator (`mesa__mesa.md`), fitted only on series that end before each training cut-off, walk-forward, with parameter spread across several random states reported instead of a single point.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH (own Python 3.12 venv, separate process, inputs and outputs as files, never imported by memelab, never copied). If the comparator only needs two or three parameters, a plain grid or Halton search in numpy inside memelab (INSPIRED_IMPLEMENTATION, no AGPL code) does the same job; the smoke needed 144 model runs.
- Gap cells: N13 (PLANNED_SEAMS "Behavioral simulation"); proxy cells CATALYST:MODEL_TRAINING and SOCIAL_SIGNALS:MODEL_TRAINING for the Phase 15 test.

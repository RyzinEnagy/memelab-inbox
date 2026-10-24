# evidentlyai/evidently

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | evidentlyai/evidently |
| URL | https://github.com/evidentlyai/evidently |
| Pinned SHA | 34771fe41c08ca074d96a52aaf4a45cd640cbaf5 |
| Commit date | 2026-09-11T00:58:56+02:00 ("Update version of pypa/gh-action-pypi-publish to 1.14.2 (#1925)") |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/evidentlyai__evidently (60 MB) |
| Review time (UTC) | 2026-10-24T04:34Z to 04:44Z (venv deleted after the run, 709 MB; clone kept) |
| Version tested | 0.7.22, built from the pinned tree (`uv pip install ./src/evidentlyai__evidently`, hatchling, no build hooks). `src/evidently/_version.py` at the pin says 0.7.22. PyPI has no 0.7.22 file; its nearest release is 0.7.23 (uploaded 2026-09-11T09:01Z), which was not tested. So the tested code is the pin itself. |
| Python | 3.13.17 venv at /home/claude/pi_research/venvs/evidentlyai__evidently |
| Dependency set tested | `SMOKES/evidentlyai__evidently/freeze_tested.txt` (81 packages, 656 MB site-packages; pandas 2.3.3, numpy 2.5.4, scikit-learn 1.9.1, scipy 1.18.1) |

## 2. License and security

- Root license: Apache-2.0. `LICENSE` text read at the pin (Apache License 2.0, January 2004), sha256 379054a067cbe8e134e084287550e9391d2804636687c4723f80a2c58a463f0e, same hash as Phase 02 LICENSE_SCAN.csv.
- Per-file licenses: Phase 02 found MIT grants in three bundled UI JavaScript files (`src/evidently/ui/service/assets/static/js/Pie-lc8No2Ny.js`, `.../index-BVvVAX8f.js`, `src/evidently/legacy/ui/assets/static/js/index-jazVifCz.js`). They ship in the wheel (pyproject `shared-data`). MIT is compatible with use; notices must be kept if redistributed.
- Key transitive licenses (from the installed set, not audited per file): pandas BSD-3, numpy BSD-3, scipy BSD-3, scikit-learn BSD-3, statsmodels BSD-3, plotly MIT, litestar MIT, uvicorn BSD-3, nltk Apache-2.0, iterative-telemetry Apache-2.0. No copyleft dependency seen in the base set. The `llm` extra (transformers, torch, litellm, faiss) was not installed and not reviewed.
- Model weights: none downloaded by the drift and classification paths. Text descriptors call `nltk.download(...)` at runtime (`src/evidently/descriptors/text_match.py:51`, `src/evidently/legacy/features/words_feature.py:80`), which fetches NLTK corpora from the network; not used by memelab's tabular role.
- Install-time scripts: none. Build backend is hatchling with `[tool.hatch.build.targets.wheel]` only; no `hatch_build.py`, no setup.py.
- Telemetry (FACT, measured): 
  - `src/evidently/telemetry.py:48-54` creates an `IterativeTelemetryLogger` that posts to `http://35.232.253.5:8000/api/v1/s2s/event?ip_policy=strict` (plain HTTP, raw IP) with a hard-coded vendor token (`telemetry.py:18`), enabled unless env `DO_NOT_TRACK` is set (any value). iterative_telemetry also honours `ITERATIVE_DO_NOT_TRACK`. Sending runs in a detached subprocess (`iterative_telemetry/__init__.py:220` `subprocess.Popen`).
  - The local UI service sends events on API calls (`src/evidently/ui/service/components/telemetry.py:18-37`, `enabled: bool = True`; calls such as `log_event("list_projects")` at `src/evidently/ui/service/api/projects.py:103`). The legacy collector does the same (`src/evidently/legacy/collector/app.py:193-196`, prints a notice).
  - `src/evidently/legacy/_config.py:3-4` defines a second address and `EVIDENTLY_DISABLE_TELEMETRY`; no code reads them at the pin (grep), so that switch does nothing.
  - Measured under `unshare -n` plus `strace -f -e connect`: plain `import evidently`, a drift Report, `save_json` and a local file `Workspace.add_run` made 0 inet connects with telemetry left on (`telemetry_core_switch_on.meta.json`), and the telemetry modules were not imported. Building the UI app and calling `GET /api/projects` with no switch made 1 connect to 35.232.253.5:8000 and wrote a user id file `evidentlyai/telemetry` under XDG_CONFIG_HOME (`telemetry_ui_switch_on.*`). With `DO_NOT_TRACK=1` the same calls made 0 connects and wrote no file (`telemetry_ui_switch_off.*`).
  - README does not mention telemetry (grep of README.md for telemetry or privacy finds nothing).
- Other network: `evidently ui` CLI checks `requests.get(f"{base_url}/api/version")` on the local service (`src/evidently/cli/ui.py:49`); `CloudWorkspace` talks to Evidently Cloud only when constructed.
- Secrets: the only token in source is the vendor's telemetry write token. A local UI secret is read from env (`EVIDENTLY_SECRET_ENV`, `ui/service/app.py`).

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Fit/train path | none; Evidently does not train models |
| Drift preset | `src/evidently/presets/drift.py:24` `DataDriftPreset` |
| Default test choice | `src/evidently/legacy/calculations/stattests/registry.py:137` `_get_default_stattest`: reference <= 1000 rows uses K-S (p < 0.05) for numeric, chi2 or z for categorical; reference > 1000 rows uses normed Wasserstein (threshold 0.1) or Jensen-Shannon |
| Per-column drift and NaN | `src/evidently/legacy/calculations/data_drift.py:139-149` drops NaN and inf from both columns before testing |
| PSI binning | `src/evidently/legacy/calculations/stattests/utils.py:33` `np.histogram_bin_edges(combined, bins="sturges")` equal-width bins |
| Probability metrics | `src/evidently/metrics/classification.py:646` `RocAuc`, `:692` `LogLoss`, `:977` `DummyLogLoss`; no Brier in the classification metrics (Brier appears only in `src/evidently/llm/optimization/scorers.py`) |
| Time handling | `src/evidently/core/datasets.py:397` `DataDefinition.timestamp` is a column role only; `src/evidently/core/report.py:956` snapshot time defaults to `datetime.now()` unless `timestamp=` is passed. No availability time, no feature cutoff, no splitter |
| Calibration/uncertainty | none for probabilities; drift tests return a score and a threshold |
| Serialization | `src/evidently/core/report.py:658` `save_json`, `:673` `dumps`, `:709` `load`, `:722` `loads` (pydantic JSON, no pickle) |
| Tests | 155 `test_*.py` files under `tests/`. Subset run offline: `tests/stattests tests/calculations/test_data_drift.py tests/test_preset/test_data_drift_preset.py`, 78 passed in 3.36 s, exit 0 (`repo_tests_subset.*`) |

## 4. Smoke results

All smokes ran offline (`unshare -n`) with `DO_NOT_TRACK=1`, Python 3.13.17, raw output in `SMOKES/evidentlyai__evidently/`. Main run: `smoke_evidently.*`, exit 0, wall 21.7 s, peak RSS 307 MB.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| Install and import | FAIL with the default dependency resolution, PASS with pandas<3 | `pandas[parquet]>=1.3.5` has no upper bound; pandas 3.1.0 resolves and `import evidently` fails (`ImportError: cannot import name 'infer_dtype_from_object'`, from `legacy/tests/data_integrity_tests.py:11`). memelab's Python 3.13 runtime has pandas 3.0.5, so the pin cannot be imported there without a downgrade | `import_default_resolution.*`, `import_pandas2.*` |
| S1 leak trap | FAIL (no protection) | Holdout matured rows n=527, 17 positives. Baseline logistic model: Evidently RocAuc 0.696, LogLoss 0.138. Same model with `leak_future_ret`: RocAuc 1.000, LogLoss 0.0070. Evidently has no availability-time concept; nothing flagged the trap. The wrapper must exclude it | `smoke_evidently.out.txt` RESULT S1_leak |
| S2 probability shape | PASS for rejection, FAIL for censored rows | Evidently LogLoss and RocAuc equal sklearn exactly on matured rows (0.13826, 0.69562; train-prevalence baseline log loss 0.14388, Brier 0.03132 vs model 0.03099). A probability of 1.5 raises `ValueError: y_prob contains values greater than 1`; NaN raises `Input contains NaN` (P38 caught, through sklearn). Holdout with 107 censored rows (label NaN) raises `Classification metrics can't handle a mix of binary and continuous targets`: no censoring support, the wrapper must drop PENDING rows (P05) | RESULT S2_probs |
| S3 missing covariates | PASS (silent drop) | liq_usd NaN: 87 train, 36 holdout. Drift score with NaN 0.843 equals the score after `dropna` 0.843: NaN rows are dropped without a warning in the result | RESULT S3_nan |
| S4 calibration/uncertainty | FAIL (not offered) | No recalibration, no reliability diagram, no Brier, no intervals for probabilities | RESULT S4_calibration |
| S5 persistence | PASS | JSON snapshot (pydantic model, no pickle) 375,783 bytes full dump; `Snapshot.loads(dumps())` gives an identical metrics dict | RESULT S5_persist |
| S6 cost | PASS | Drift report, 6 columns, 1,746 reference rows vs 634 current: 0.40 s; one column 0.05 s; import about 7 s; peak RSS 307 MB; offline import, report and save work with no network. Wheel is py3-none-any, requires-python >=3.10, classifier up to 3.13; ran on 3.13. Windows not tested (pure-Python wheel; `uvicorn[standard]` extras are marker-guarded) | RESULT S6_cost, `import_pandas2.meta.json` |
| Role: holdout drift detection | PASS (default and K-S), FAIL (PSI) | Default (normed Wasserstein, threshold 0.1): train vs holdout flags exactly liq_usd (0.843) and ret_1h (0.399); 4 of 4 holdout chunks of 150 rows flag both. K-S: same two flagged. PSI (Sturges equal-width bins): flags ret_1h (0.192) but misses liq_usd (0.029) because equal-width bins on the raw heavy-tailed column put almost all mass in one bin | RESULT ROLE_drift_* |
| Role: false alarms train vs val | FAIL at small windows | No shift exists between train and val. Default: train vs val flags 1 of 6 columns (ret_1h 0.112 vs 0.1); train halves 0 of 6. Chunked monitoring (val in 3 chunks of 150 rows vs train): 9 false column flags out of 18 (default and PSI), 4 of 18 with K-S. The default switches to a distance threshold when the reference exceeds 1,000 rows, regardless of current window size, so small windows alarm often | RESULT ROLE_drift_* |
| Telemetry (not a smoke) | n/a, finding | See section 2: UI service phones home by default, core library does not | `telemetry_*` |

## 5. README or docs claims the code does not support (P42)

- README line 33 "100+ built-in metrics": not counted, not scored.
- README line 35 "Both offline evals and live monitoring": offline core use is supported and measured; the live UI service sends usage events by default, which README does not disclose. Recorded as a documentation gap, not a capability claim.
- No claim was found that Evidently enforces time-correct data; none is credited.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 1 | Caller-defined reference and current windows plus an explicit snapshot `timestamp` (`core/report.py:956`) support windowed monitoring; no availability time, cutoff or splitter; S1 trap passed through untouched |
| Transferable measurable predictive outcomes | 14 | 1 | Evaluates binary classification outcomes (RocAuc and LogLoss equal sklearn, S2); produces no predictions; no survival or censoring (censored rows raise, S2) |
| Calibration, uncertainty and abstention | 12 | 2 | Proper score log loss with a dummy baseline (`metrics/classification.py:692`, `:977`); invalid probabilities raise (S2, P38); no Brier, reliability or recalibration (S4) |
| Catalyst/social/on-chain features | 10 | 0 | No support for event covariates, irregular timestamps or cross-token features; generic column drift only |
| Decision/execution and stress compatibility | 10 | 2 | Per-column drift tests with FAIL status (`include_tests=True`) can drive a degrade or ABSTAIN rule (P39); nothing on execution or costs |
| Code quality, maintenance and tests | 8 | 5 | 155 test files, 78 of 78 subset tests pass; active (pin 2026-09-11, releases through 0.7.23); but no pandas upper bound breaks import under pandas 3 (measured), legacy and new APIs coexist, dead `EVIDENTLY_DISABLE_TELEMETRY` switch |
| Integration fit and extensibility | 8 | 2 | Clean Report API with JSON output, but 81 packages and 656 MB including a web server stack, and it cannot import in memelab's pandas 3.0.5 runtime; would need its own venv |
| Experiment reproducibility and audit | 8 | 5 | JSON snapshots round-trip identically (S5); drift tests deterministic; local file Workspace stores runs; timestamp defaults to wall clock unless passed |
| Cost, latency and operational reliability | 5 | 4 | 0.40 s per 6-column report, 307 MB peak, works fully offline for core use, Python 3.13 runs; import about 7 s |
| Licensing, security and data rights | 7 | 4 | Apache-2.0 verified; no install scripts; UI telemetry on by default to a raw-IP HTTP endpoint with a user id file, off with `DO_NOT_TRACK`; core path makes no network calls (measured); undisclosed in README |
| Total | 100 | 26 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable as a forecaster; it is a monitoring tool and is scored as one.
- NOT_REALTIME: no (sub-second reports).
- LEAKAGE_FAIL: not applicable to a monitor (no training path), but S1 shows it gives no protection; any use must receive already as-of filtered windows from the memelab wrapper.
- Adversarial scenarios: P05 (censored labels raise instead of being treated as PENDING: wrapper must filter), P38 (out-of-range and NaN probabilities raise: caught), P39 (drift detected on the holdout shift; false alarms on small windows), P32 (no install scripts; telemetry subprocess found and measured), P42 (README metric count not credited).

## 8. Proposed role and integration decision

- Role: reference design for Phase 19 drift monitoring (default test choice by sample size, per-column drift tests with statuses, JSON snapshots). The measured weaknesses (equal-width PSI bins on heavy tails, a distance threshold applied to small windows) are exactly what a memelab implementation should avoid: quantile bins from the reference, log-scaled money columns, window-size-aware tests.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION. Optional ISOLATED_RESEARCH use for offline HTML drift reports in a separate venv with `DO_NOT_TRACK=1` set and pandas<3; never imported by the memelab package (pandas 3 conflict, server stack).
- Gap cells addressed: DECISION_RECORDS:DRIFT_MONITORING, HIST_MARKET:DRIFT_MONITORING, REGIME_NARRATIVE:DRIFT_MONITORING (all MISSING in GAP_MATRIX.csv).

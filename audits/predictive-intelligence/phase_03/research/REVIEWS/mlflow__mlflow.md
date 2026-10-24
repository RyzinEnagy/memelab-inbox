# mlflow/mlflow

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | mlflow/mlflow |
| URL | https://github.com/mlflow/mlflow |
| Pinned SHA | cd19153f5ed36f40724c22d7798e65ad1c4dd7bc |
| Commit date | 2026-10-23T18:11:17+00:00 ("Speed up protobuf JSON serialization with one-pass int64 conversion") |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/mlflow__mlflow (711 MB; deleted after review) |
| Review time (UTC) | 2026-10-24T04:58Z to 05:10Z |
| Versions tested | (a) the pin, built from source (`uv pip install ./src/mlflow__mlflow`, setuptools), version string `3.17.3.dev0`, Python 3.13.17, 86 packages, 558 MB site-packages (`freeze_pin_full.txt`); (b) the latest release `mlflow==3.17.2` from PyPI (2026-10-21; installs mlflow, mlflow-skinny and mlflow-tracing 3.17.2), 87 packages, 619 MB, used only for the telemetry default because dev builds switch telemetry off (`freeze_release_3.17.2.txt`); (c) `mlflow-skinny==3.17.2` plus scikit-learn, pandas and skops, 54 packages, 341 MB, for the file-store path (`freeze_skinny_3.17.2_plus_sklearn.txt`). `mlflow/telemetry/` is byte-identical between the pin and the 3.17.2 wheel (`diff -r -q`, no output). |

## 2. License and security

- Root license: Apache-2.0, `LICENSE.txt` ("Copyright 2018 Databricks, Inc." then the Apache License 2.0 text), sha256 6395355de6f391afff35996a30fb41b189b4991a4cb54993ace35ab69a0bfa28 (matches Phase 02). Phase 02 found BSD and MIT headers in TypeScript utilities and examples (`libs/typescript/core/src/core/utils/json-bigint/*`); these are not in the Python wheel. A git submodule `https://github.com/mlflow/skills` is referenced; not fetched, not reviewed.
- Key transitive licenses (declared): Flask BSD-3, FastAPI MIT, SQLAlchemy MIT, alembic MIT, pandas and numpy BSD-3, scikit-learn BSD-3, pyarrow Apache-2.0, databricks-sdk Apache-2.0, docker Apache-2.0, gitpython BSD-3, skops MIT, cloudpickle BSD-3, gunicorn MIT, opentelemetry Apache-2.0. No copyleft seen.
- Model weights: none.
- Install-time scripts: setuptools build of the pinned tree; no custom build step ran (the JavaScript UI is not built from source, so the tracking server UI is absent in the pin install; not needed here).
- Telemetry (FACT, source and measurement):
  - Created at import: `mlflow/__init__.py:454-456` `set_telemetry_client()`. Disabled when `MLFLOW_DISABLE_TELEMETRY` is true (`mlflow/environment_variables.py:1636`), when `DO_NOT_TRACK` equals the string `true`, in CI (`PYTEST_CURRENT_TEST`, `CI`, `GITHUB_ACTIONS` and others), or for any dev version (`mlflow/telemetry/utils.py:144-158`). On the first tracked call it fetches `https://config.mlflow-telemetry.io/<version>.json` and then posts batches to the `ingestion_url` from that config (`mlflow/telemetry/constant.py:8-11`, `mlflow/telemetry/client.py:184-218`, `:274-310`), and writes an installation id to `$XDG_CONFIG_HOME/mlflow/telemetry.json` (`mlflow/telemetry/installation_id.py:64-88`).
  - Measured under `unshare -n` plus strace, sqlite tracking, one run: release 3.17.2 with no switch made 1 outbound connect (to the HTTPS proxy, the config fetch) and wrote `mlflow/telemetry.json`; with `MLFLOW_DISABLE_TELEMETRY=true` or `DO_NOT_TRACK=true`: 0 connects, no file. With `DO_NOT_TRACK=1` (the value evidently accepts) telemetry stayed ON: 1 connect and the id file (`telemetry_release_dnt_equals_1.*`). The pin (3.17.3.dev0) made 0 connects with no switch because dev builds are excluded (`telemetry_pin_on.*`). The full lineage smoke at the pin made 0 inet connects.
  - Disclosed in `docs/docs/community/usage-tracking.mdx`, not in README.
- Other side effects: run metadata stores the OS user (`mlflow.user`) and script path (`mlflow.source.name`); `MLFLOW_LOG_UV_FILES` defaults to true and logs `uv.lock` and `pyproject.toml` with a model when run inside a uv project (`environment_variables.py:1999`).
- Secrets: none in the code paths used; Databricks and cloud credentials are read from env only when those URIs are used.
- Serialization: default sklearn format is skops (`mlflow/sklearn/__init__.py:110-115`), which refuses unknown types unless listed; cloudpickle and pickle remain options.

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Run registry client | `mlflow/tracking/client.py:245` `MlflowClient`, `:4685` `create_model_version`, `:5130` `get_model_version`, `:5379` `set_model_version_tag` |
| Registry store (sqlite) | `mlflow/store/model_registry/sqlalchemy_store.py:95` `SqlAlchemyStore`, `:982` `create_model_version` |
| Default backend | `mlflow/tracking/_tracking_service/utils.py:54-58`: `sqlite:///mlflow.db` in the working directory unless `./mlruns` already has data |
| File store | `mlflow/store/tracking/file_store.py:238-249` raises unless `MLFLOW_ALLOW_FILE_STORE=true` (`environment_variables.py:2007`) |
| Dataset lineage | `mlflow/data/digest_utils.py:9` `MAX_ROWS = 10000`, `:12-43` digest = 8-character truncated md5 over the first 10,000 rows, the row count and column names |
| Model metadata | `mlflow/models/model.py:124-146` (artifact_path, model_uuid, utc_time_created); MLmodel written at the pin has no hash field |
| Evaluation | `mlflow/models/evaluation/evaluators/classifier.py:496` log_loss, `:301` calibration curve plot; no Brier |
| Time handling | none beyond run start and end times and whatever params the caller logs |
| Tests | 899 `test_*.py` files. Offline subset: `tests/data/test_pandas_dataset.py tests/data/test_numpy_dataset.py` 28 passed, 2 errors (pyspark not installed); `tests/telemetry/test_utils.py tests/telemetry/test_installation_id.py` 44 passed, exit 0 (`repo_tests_subset.*`, `repo_tests_telemetry.*`) |

## 4. Smoke results

Pin build, Python 3.13.17, pandas 3.1.0, numpy 2.5.4, offline (`unshare -n` plus strace, 0 inet connects). Main run `smoke_mlflow_pin.*`: exit 0, wall 17.1 s, peak RSS 419 MB. Raw output in `SMOKES/mlflow__mlflow/`.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| Role: local run registry and lineage without a server | PASS with wrapper work | sqlite file store plus local artifacts: run params kept `feature_set` (6 names) and `training_label_cutoff_epoch` 1791641376; dataset input `train_matured` with digest `d9b337fb` (8 characters); signature input names equal the feature set; registered model version 1 points to the run (`run_id` match true). MLmodel fields: artifact_path, flavors, mlflow_version, model_id, model_size_bytes, model_uuid, run_id, signature, utc_time_created; no sha256 of the model file. The wrapper added `model_sha256` and `challenge_sha256` as version tags (works). Log plus register took 7.0 s on a new database | RESULT LINEAGE, LINEAGE_tags, DATASET_DIGEST |
| Role: plain file store | PASS only with opt-in | At the pin `file://.../mlruns` raises "filesystem tracking backend ... is in maintenance mode" unless `MLFLOW_ALLOW_FILE_STORE=true`. With mlflow-skinny 3.17.2, opt-in, telemetry off: run, dataset digest, model log, registry version and identical reload all worked, 26 small files, 0 connects (`smoke_skinny_filestore.*`); skinny needs skops installed by hand for the default sklearn format (`attempt1_skinny_no_skops.*`) | RESULT FILE_STORE, SKINNY_FILESTORE |
| S1 leak trap | FAIL (no protection) | The trap model logged and registered as version 2 like any other: holdout AUC 1.000 and Brier 0.0016 vs 0.696 and 0.0310 for the legitimate model. MLflow stores the feature list it is given and has no availability-time concept | RESULT S1_leak |
| S2 probability shape | PASS with configuration | sklearn pyfunc returns class labels by default; with `pyfunc_predict_fn="predict_proba"` it returns shape (527, 2), all finite, in [0, 1]. Matured holdout Brier 0.03099 vs train-prevalence baseline 0.03132, log loss 0.1383 vs 0.1439 (scores computed by the harness) | RESULT S2_probs |
| S3 missing covariates | PASS (schema) | Signature enforcement accepts NaN in a float column (prediction 0.0476 for the row), rejects a missing column (`Failed to enforce schema`), and silently accepts an extra column | RESULT S3_schema |
| S4 calibration and uncertainty | PASS (diagnostic only: log loss and a calibration plot) | `mlflow.models.evaluate` logs log_loss 0.13826, roc_auc 0.69562, precision_recall_auc 0.0846 and a calibration curve plot; no Brier, no recalibration, no intervals | RESULT S4_evaluate |
| S5 persistence | PASS after a fix | Default skops format first FAILED on a plain SimpleImputer, StandardScaler, LogisticRegression pipeline ("Untrusted types found in the file: ['numpy.dtype']", `attempt1_default_skops.*`). With `skops_trusted_types=["numpy.dtype"]`: reload through `models:/pi_r4_baseline/1` gives predictions identical to the in-memory model; load 0.03 s | RESULT S5_persist |
| S6 cost | PASS | Import 1.2 to 1.8 s; pyfunc predict 2.7 ms for one row, 2.0 ms for 527 rows; sqlite file 1.0 MB after 3 runs; peak RSS 419 MB; 86 packages (pin full) or 54 (skinny plus sklearn and skops); Python 3.13 and pandas 3.1 work. Windows wheels: pure-Python wheel; `waitress` replaces gunicorn on Windows (pyproject markers); not tested | RESULT S6_cost |
| Telemetry (not a smoke) | n/a, finding | Release default ON (config fetch on the first tracked call, id file); off with `MLFLOW_DISABLE_TELEMETRY=true` or `DO_NOT_TRACK=true`, not with `DO_NOT_TRACK=1` | `telemetry_*` |

## 5. README or docs claims the code does not support (P42)

- README line 125 "full lineage tracking" (prompts): for models, lineage is run params, an 8-character dataset digest over at most 10,000 rows and a run id; there is no model file hash. Recorded as PARTIAL, not credited beyond the measured smoke.
- README line 291 "vendor-neutral": the base install pulls `databricks-sdk`, and telemetry is on by default in releases. Not scored as a capability.
- README examples point at a tracking server (`http://localhost:5000`); the server-less sqlite path works (measured) but the file store needs an opt-in at the pin.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 2 | Can store the training cutoff, feature set and dataset digest per run and version (LINEAGE), which a P13 check could read; enforces nothing; the trap model registered without complaint (S1) |
| Transferable measurable predictive outcomes | 14 | 1 | Generic tracking; `evaluate` reproduces sklearn classification metrics; no outcome modelling |
| Calibration, uncertainty and abstention | 12 | 2 | log loss and a calibration curve plot in `evaluate` (`classifier.py:496`, `:301`); no Brier, recalibration or intervals |
| Catalyst/social/on-chain features | 10 | 0 | None |
| Decision/execution and stress compatibility | 10 | 1 | Registry versions and tags give a champion and rollback handle (Phase 16); nothing on execution |
| Code quality, maintenance and tests | 8 | 6 | 899 test files, 72 of 74 subset tests pass offline (2 need pyspark); commits daily, weekly releases; but fast API churn (file store now raises by default, default skops format refuses a standard sklearn pipeline) |
| Integration fit and extensibility | 8 | 3 | Runs on Python 3.13 with pandas 3 and numpy 2.5; clean client API; but 86 packages including Flask, FastAPI, gunicorn, docker and databricks-sdk for what PLANNED_SEAMS plans as a files-with-sha256 registry: a duplicate subsystem; the lighter skinny path needs an opt-in to a maintenance-mode store |
| Experiment reproducibility and audit | 8 | 6 | Params, metrics, dataset digest, signature, run-linked model versions, identical reload (S5); weak 8-character digest over at most 10,000 rows and no model hash unless the wrapper tags one; user name and script path stored |
| Cost, latency and operational reliability | 5 | 3 | 2.7 ms per pyfunc call, 419 MB, fully offline once telemetry is off; 7 s first log plus register; 558 MB install |
| Licensing, security and data rights | 7 | 4 | Apache-2.0 verified; skops default is the safer format; telemetry ON by default in releases with an installation id file, and `DO_NOT_TRACK=1` does not stop it (measured); disclosed only in docs |
| Total | 100 | 28 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable (infrastructure).
- NOT_REALTIME: no for inference; the registry is an offline tool.
- LEAKAGE_FAIL: not applicable as a model; it records but does not check chronology.
- Adversarial scenarios: P13 (the registry can hold training cutoff and data hash so a replay can refuse a model trained after the decision, but only if the wrapper writes and checks them), P46 (signature enforcement rejects a missing feature column but accepts an extra one: partial), P32 (no install scripts; telemetry found in source and measured; dev builds hide it, so a pin-only test would miss it), P42 (lineage claim only partly supported).

## 8. Proposed role and integration decision

- Role: reference for the Phase 16 model registry fields (signature with feature names, run id, creation time, model size, input example) plus the two fields memelab must add itself: sha256 of the model file and the training label cutoff. Optional offline experiment ledger during Phases 07 to 13.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION for the registry (files with sha256 and a model card, as planned). ISOLATED_RESEARCH if the team wants a tracking UI during research: separate venv, `MLFLOW_DISABLE_TELEMETRY=true` (not `DO_NOT_TRACK=1`), sqlite file outside the repo, `skops_trusted_types` set explicitly, never imported by `memelab/predictive/`.
- Gap cells addressed: DECISION_RECORDS:MODEL_REGISTRY, HIST_MARKET:MODEL_REGISTRY, SOCIAL_REPLAY:MODEL_REGISTRY (PARTIAL or MISSING).

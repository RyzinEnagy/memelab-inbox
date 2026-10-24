# unionai-oss/pandera

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | unionai-oss/pandera (pyproject URLs still say pandera-dev/pandera; same code) |
| URL | https://github.com/unionai-oss/pandera |
| Pinned SHA | edb0d8b2a92d193f86ec51eff7e8c8f2268af04b |
| Commit date | 2026-10-23T17:52:52-07:00 ("fix(polars): exclude explicit columns from regex alias selectors (#2343)") |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/unionai-oss__pandera (8.1 MB) |
| Review time (UTC) | 2026-10-24T05:18Z to 05:26Z |
| Version tested | Built from the pinned tree (`uv pip install "./src/unionai-oss__pandera[pandas,io]"`); setuptools_scm on the shallow clone sets `0.1.dev1+gedb0d8b2a`. Latest PyPI release 0.34.1 (2026-10-06) predates the pin and was not tested. |
| Python | 3.13.17 venv at /home/claude/pi_research/venvs/unionai-oss__pandera |
| Dependency set tested | `SMOKES/unionai-oss__pandera/freeze_tested.txt`: 16 packages, 109 MB site-packages (pandas 3.1.0, numpy 2.5.4, pydantic 2.14.1, typeguard, pyyaml). scikit-learn was added only for the harness model in S1 |

## 2. License and security

- Root license: MIT, "Copyright (c) 2018 Niels Bantilan". `LICENSE.txt` read at the pin, sha256 142d0a4e2b2ade63e1d3f85d8289865f729397aafeec9afced01877826c54640 (matches Phase 02). No per-file licenses found by Phase 02.
- Transitive (base and pandas extra): pandas, numpy BSD-3; pydantic MIT; typeguard MIT; typing-inspect MIT; pyyaml MIT; packaging Apache-2.0 or BSD. No copyleft.
- Model weights: none.
- Install-time scripts: `setup.py` is a bare `setup()`; setuptools with setuptools_scm.
- Network and telemetry: none (grep finds no telemetry or HTTP client in `pandera/`). Measured: smoke under `unshare -n` plus strace, 0 inet connects.
- YAML schemas load with `yaml.safe_load` (`pandera/io/pandas_io.py:517-519`).
- Import side effects (FACT, measured): `import pandera.pandas` re-adds numpy aliases removed in numpy 2 (`np.NaN`, `np.float_`, `np.string_`, `np.unicode_`; `pandera/_patch_numpy2.py`, called at `pandera/pandas.py:25-27`), and sets `SPARK_LOCAL_IP=127.0.0.1` and `PYARROW_IGNORE_TIMEZONE=1` in the process environment when unset (`pandera/external_config.py`, called at `pandera/pandas.py:93`). Measured before and after import: `hasattr(np, "NaN")` False then True; both env vars None then set. These change global state for every other module in the process.
- Secrets: none.

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Schema and validation | `pandera/api/pandas/container.py:24` `DataFrameSchema`; generic base `pandera/api/dataframe/container.py:45`; checks `pandera/api/checks.py:18` `Check` |
| Custom checks | `pandera/api/extensions.py:156` `register_check_method(statistics=..., supported_types=...)` |
| Check execution | `pandera/backends/pandas/container.py:327` `run_checks`; an exception inside a check becomes a schema failure (`:356-361`, fail-closed); `strict="filter"` drops undeclared columns (`:646` `strict_filter_columns`) |
| Serialization | `pandera/api/pandas/container.py:352` `from_yaml`, `:358` `to_yaml`, `:376` `from_json`; unregistered checks are skipped with a UserWarning (`pandera/schema_statistics/common.py:158`) |
| Statistical checks | `pandera/api/hypotheses.py:182` `two_sample_ttest`, `:293` `one_sample_ttest` (scipy) |
| Time handling | dtype checks only; any as-of rule must be written as a check (done in the smoke) |
| Tests | 168 `test_*.py` files. Offline subset `tests/pandas/test_checks.py tests/pandas/test_extensions.py tests/pandas/test_from_to_format_conversions.py`: 56 passed, 4 skipped, exit 0 (`repo_tests_subset.*`) |

## 4. Smoke results

Offline (`unshare -n` plus strace, 0 inet connects), Python 3.13.17, pandas 3.1.0. Main run `smoke_pandera.*`: exit 0, wall 4.0 s, peak RSS 189 MB. Raw output in `SMOKES/unionai-oss__pandera/`. The schemas use two registered checks: `available_before_decision` (every `*_available_at` column present, not null, and `<= decision_time`, row-wise) and `label_only_when_matured` (label present iff `label_matures_at <= as_of`, with `as_of` fixed at the challenge cutoff 1792592000), plus `strict` column control.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| S1 leak trap (as-of gate, P36) | PASS (blocks when written) | Feature table with `leak_future_ret` and its `leak_available_at` (decision + 6 h): invalid, all 3,000 rows flagged from index 0 (29,559 failure cases across columns). Legitimate features with `*_available_at = decision_time - 300`: valid. One row made available 1 s after its decision: invalid, row 17 reported. One row with missing availability: invalid, row 5 reported (null and dtype failures too). Trap column with no availability metadata: `strict="filter"` silently drops it and validates (output has the 6 features only); `strict=True` refuses it (`column_in_schema`). For scale, the same trap lifts holdout ROC AUC from 0.696 to 1.000 and cuts Brier from 0.0310 to 0.0016 in the harness model | RESULT S1_asof_gate |
| S2 probability shape (P38) | PASS | Forecast table schema: valid rows pass; 1.5, -0.1, NaN and inf in `probability` each fail with the named check (in_range, not_nullable, finite); a lower bound above the point fails `interval_contains_point` at row 1. Lazy mode collects every failure with row indices | RESULT S2_forecast_schema |
| P05 label maturity | PASS | Challenge labels valid (107 censored rows have no label and mature after the cutoff). Giving one PENDING row a label of 0 fails `label_only_when_matured` at index 2893 | RESULT P05_label_maturity |
| S3 missing covariates | PASS | 156 NaN in nullable `liq_usd` accepted; one NaN in non-nullable `age_h` rejected at row 3 | RESULT S3_nullable |
| S4 calibration/uncertainty | SKIPPED | Not offered (validation library); `hypotheses.two_sample_ttest` exists but was not exercised | n/a |
| S5 persistence (schema) | PASS for registered checks, FAIL for lambda checks | YAML round trip of the feature schema (933 bytes) keeps the registered check and gives the same result. Lambda checks are dropped on `to_yaml` with only a UserWarning ("Only registered checks may be serialized ... will be skipped"): the reloaded forecast schema no longer catches the interval violation and loses the `finite` check (inf still caught by `in_range`). A stored schema can silently be weaker than the code that wrote it | RESULT S5_schema_io |
| S6 cost | PASS | Import 0.2 s; validating 30,000 feature rows 0.036 s; one forecast record 3.3 ms; 189 MB RSS with sklearn loaded; offline; Python 3.13 runs (classifiers to 3.14); pure-Python wheel, Windows not tested | RESULT S6_cost |
| Fail-closed behaviour (not a smoke) | n/a, observed | A bug in my first registered check (wrong output shape) made every validation fail with "Error while executing check function: AssertionError" rather than pass (`attempt1_shape_bug.*`) | attempt1 files |

## 5. README or docs claims the code does not support (P42)

- README "light-weight" (pyproject description): supported for the pandas path (16 packages, 0.2 s import), but the import mutates numpy and the process environment, which a light-weight library should not do. Recorded, not scored as a claim.
- No accuracy or time-safety claims; nothing else to mark UNSUPPORTED.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 8 | With registered checks it enforced `available_at <= decision_time` per row (trap blocked, a 1-second-late row found), refused undeclared columns with `strict=True`, and enforced label maturity (P05); no splitter, no replay, and every rule must be written by memelab |
| Transferable measurable predictive outcomes | 14 | 1 | Label contracts only (values in {0, 1}, maturity) |
| Calibration, uncertainty and abstention | 12 | 2 | Forecast output contract (finite, [0, 1], interval contains point) blocks invalid probabilities (P38); no calibration |
| Catalyst/social/on-chain features | 10 | 1 | Typed, ranged and nullable checks for any feature table; nothing domain-specific |
| Decision/execution and stress compatibility | 10 | 3 | Validation gate before publishing forecasts or training; lazy failure cases with row indices; nothing on costs |
| Code quality, maintenance and tests | 8 | 6 | 168 test files, 56 subset tests pass; commit the day before review, release two weeks earlier; fail-closed check execution; but silent loss of unregistered checks on YAML export and import-time global side effects |
| Integration fit and extensibility | 8 | 6 | 16 packages; the system Python 3.13 used for memelab already imports pandas, numpy, pydantic, pyyaml and dateutil, and lacks only typeguard, typing-inspect and mypy-extensions (checked by import); works on Python 3.13 with pandas 3.1 and numpy 2.5; but import mutates numpy and sets env vars, and forecast-record validation overlaps `memelab/predictive/contract.py:328` `validate` |
| Experiment reproducibility and audit | 8 | 5 | Schemas versionable as YAML (safe_load) with registered checks; failure cases with row indices form an audit trail; lambda checks lost on export |
| Cost, latency and operational reliability | 5 | 5 | 0.036 s for 30,000 rows, 3.3 ms per record, 0.2 s import, offline |
| Licensing, security and data rights | 7 | 6 | MIT verified; no network or telemetry (0 connects); safe YAML loading; import side effects on numpy and env |
| Total | 100 | 43 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable (validation library).
- NOT_REALTIME: no.
- LEAKAGE_FAIL: no; it is the one library in this set that can enforce strict as-of data, provided memelab writes the checks as registered checks and validates before every fit and every forecast.
- Adversarial scenarios: P36 (feature after available_at refused), P05 (labelled PENDING row refused), P38 (out-of-range, NaN and inf probabilities refused), P46 (a schema exported to YAML can silently lose checks: export only registered checks and test the round trip), P32 (no install scripts or network; global import side effects found and measured), new case for the lead: a trap column with no availability metadata passes silently under `strict="filter"` because it is dropped, so a pipeline that reads the original frame instead of the validated output would still train on it; use `strict=True`.

## 8. Proposed role and integration decision

- Role: the batch validator for the Phase 05 point-in-time feature table and the Phase 06 label table: every feature carries `*_available_at`, the table must satisfy `available_at <= decision_time` row by row, undeclared columns are refused, labels exist only once matured. The per-record forecast validator already exists in `memelab/predictive/contract.py` and does not need pandera.
- Candidate INTEGRATION_DECISION: ADAPTER: a small `schemas` module inside `memelab/predictive/` that imports pandera lazily (only when validating, to contain the numpy and env side effects), uses registered checks only, `strict=True`, `lazy=True`, and a test that the YAML round trip keeps every check. If the lead prefers no new dependency, INSPIRED_IMPLEMENTATION in plain pandas is about 30 lines and loses only the failure-case report format.
- Gap cells addressed: HIST_MARKET:POINT_IN_TIME_FEATURES, REGIME_NARRATIVE:POINT_IN_TIME_FEATURES (PARTIAL), and the validation half of the MODEL_REGISTRY cells listed in Phase 02 (schema versions stored with a model card).

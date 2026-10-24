# probabl-ai/skore

Reviewer: R4 (Phase 03 parallel source review). Proposed scores only; the Phase 03 lead applies the rubric across all reviews.

## 1. Identity

| Field | Value |
|---|---|
| Canonical repo | probabl-ai/skore |
| URL | https://github.com/probabl-ai/skore |
| Pinned SHA | 73a26b4528a39694e577000dcbfd17e097095ec4 |
| Commit date | 2026-10-21T12:13:44+00:00 ("chore(deps): Bump the pip group across 11 directories with 1 update (#3340)") |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into /home/claude/pi_research/src/probabl-ai__skore (6.5 MB) |
| Review time (UTC) | 2026-10-24T05:09Z to 05:20Z |
| Version tested | Built from the pinned tree (`uv pip install ./src/probabl-ai__skore/skore`, hatchling). The hatch metadata hook (`skore/hatch/metadata.py`, read first) sets the version from a CI-written `VERSION.txt`, so the pin builds as `0.0.0+unknown`. Nearest PyPI release 0.28.0 (2026-10-14) predates the pin and was not tested. |
| Python | 3.13.17 venv at /home/claude/pi_research/venvs/probabl-ai__skore |
| Dependency set tested | `SMOKES/probabl-ai__skore/freeze_tested.txt`: 44 packages, 361 MB site-packages (pandas 3.1.0, numpy 2.5.4, scikit-learn 1.9.1, skrub 0.11.0, textual 8.2.8, plotly 7.1.0, skore-skills 0.8.0) |

## 2. License and security

- Root license: MIT, "Copyright (c) 2024-2026 Probabl". `LICENSE` read at the pin, sha256 1a326199b9ac664dde233b97d2ce34789693444b87f15ce218dd48c06b22360b (matches Phase 02).
- Vendored: `skore/src/skore/_externals/docscrape.py` header "License: BSD-2-Clause, Copyright (C) 2008-2023 Stefan van der Walt" (Phase 02 recorded it as BSD; the header says BSD-2-Clause). Compatible; keep the notice if copied.
- Key transitive licenses (declared): scikit-learn, pandas, numpy BSD-3; skrub BSD-3; matplotlib PSF-based; seaborn BSD-3; plotly MIT; textual MIT; rich MIT; joblib BSD-3; narwhals MIT; skore-skills BSD-3 (PyPI metadata). No copyleft seen.
- Model weights: none.
- Install-time scripts: the hatch metadata hook only copies `../LICENSE`, reads README and an optional `VERSION.txt`.
- Telemetry: none in the library (grep for telemetry, analytics, posthog, sentry, segment finds none; `rich.segment` is unrelated). Measured: the full smoke under `unshare -n` plus strace made 0 inet connects (`smoke_skore.meta.json`).
- Network code exists only behind explicit use: Skore Hub client (`_plugins/hub/`, httpx), hub URL discovery in the CLI (`_cli/skore.py:14-24`), skill catalog download from GitHub (`_cli/skills/catalog.py:50-60`), and CLI harnesses that launch coding agents (`_cli/harnesses/claude.py`, `codex.py` and others). None runs on import or in reports.
- Local side effects: `git` subprocess calls at report creation to record the commit (`_project/git.py:29`, `:51`, `:101`). The local workspace defaults to `<git repo root>/skore` when run inside a repository (`_plugins/local/project.py` `find_workspace`), with its own `.gitignore` of `*`; inside memelab, `SKORE_WORKSPACE` must be set to keep files out of the repo tree.
- Persistence is pickle and joblib (`_plugins/local/project.py` writes `estimator.pickle`, `estimator_.pickle`, `learner_.pickle`, `metrics/registry.pickle`, `metrics/cache.pickle`; loads at `:344-388`). Load only workspaces you wrote.

## 3. Code paths inspected at the pin

| Area | Anchor (under `skore/src/skore/`) |
|---|---|
| Report construction and fit | `_reports/estimator/report.py:99` `EstimatorReport`, `:238` `__init__` (fits when not fitted, `:271-277`); `_reports/cross_validation/report.py:195` `CrossValidationReport(splitter=...)` accepts any sklearn splitter |
| Probability metrics | `_metrics/metrics.py:692` `brier_score`; log loss and ROC AUC in the default summary; `_reports/estimator/inspection.py:367` `calibration_curve` |
| Leakage and time checks | `_checks/skd011_golden_feature.py:87-108` (refits on single features; severity `tip`); `_checks/skd013_train_test_time_overlap.py:14-80` (flags datetime columns where max train time >= min test time; severity `issue`); `_checks/skd009_worse_than_baseline.py` (HistGradientBoosting baseline) |
| Lineage metadata | `_reports/base.py:174-181` (`id` uuid7, `skore-version`, `creation-date` UTC, `git_commit`); `_project/git.py:61-94` `git_commit`; data references by `joblib.hash` content hash (`_plugins/local/project.py:403-410`); CV split indices written as text (`:136-137`) |
| Time handling | only SKD013 and whatever splitter the caller passes; no feature availability time, no label maturity |
| Serialization | `_plugins/local/project.py` `_write_estimators`, `_write_metrics` (pickle), `_get_data_ref` (joblib) |
| Tests | 183 `test_*.py` files under `skore/tests`. Offline subset (`tests/unit/checks/test_skd011_golden_feature.py`, `test_skd013_train_test_time_overlap.py`, `test_skd004_high_class_imbalance.py`): 34 passed, 2 skipped, exit 0. It first failed at collection because the pytest config filters warnings by `sqlalchemy` (an mlflow extra) and `tests/conftest.py` imports `keyring` (hub extra); the run overrides `filterwarnings` and installs the hub extra (`repo_tests_subset.*`) |

## 4. Smoke results

Offline (`unshare -n` plus strace, 0 inet connects), Python 3.13.17, pandas 3.1.0. Main run `smoke_skore.*`: exit 0, wall 165.6 s (most of it in checks), peak RSS 234 MB. Raw output in `SMOKES/probabl-ai__skore/`.

| Smoke | Result | Numbers | Raw output |
|---|---|---|---|
| S1 leak trap | PASS for detection (advisory tip), FAIL for blocking | Holdout (527 matured, 17 positives): legitimate pipeline ROC AUC 0.696, Brier 0.0310, log loss 0.1383; with `leak_future_ret` ROC AUC 1.000, Brier 0.0016. `report.checks` on the trap model: SKD011 "A model trained on feature(s) ['num__leak_future_ret'] alone has similar performance to a model trained on the target itself ... This likely means the target is present among the features" (severity tip). On the legitimate model SKD011 was skipped because SKD002 judged it underfitting. Nothing refuses the model | RESULT S1_leak_and_checks |
| Role: time-ordered CV and overlap check | PASS | Train plus val matured rows with a `decision_ts` column (dropped by the pipeline): shuffled `KFold(4)` gets SKD013 issue "Datetime column(s) ['decision_ts'] contain training timestamps that are after the earliest test timestamp"; `TimeSeriesSplit(4, gap=50)` passes SKD013. The check is max-train vs min-test only: no embargo length, no per-feature availability | RESULT ROLE_time_overlap_check |
| S2 probability shape | PASS for scores, FAIL for censored rows | Brier 0.03099 and log loss 0.13826 equal the harness values (train-prevalence baseline 0.03132 and 0.14388). With the 107 censored rows (label NaN) in `y_test`, every metric is NaN with no error; filling them as negatives gives Brier 0.0261 (looks better, the P05 bias) | RESULT S2_probs, `skore_censored_probe.*` |
| S3 missing covariates | PASS (passes through sklearn) | No native handling: a pipeline without an imputer raises sklearn's `ValueError: Input X contains NaN`; with an imputer it works | RESULT S3_nan |
| S4 calibration and uncertainty | PASS (diagnostic only: Brier, log loss, reliability bins) | `inspection.calibration_curve()` returns 9 reliability bins; Brier and log loss in the summary; SKD004 warns on class imbalance; SKD009 compares with a HistGradientBoosting baseline. No recalibration, intervals or conformal sets | RESULT S4_calibration |
| S5 persistence | PASS (pickle) | Local project put and get by report id; reloaded estimator predictions identical | RESULT S5_persist |
| Role: local lineage without a server | PASS with gaps | 23 files: `metadata.json` (uuid7 id, UTC creation date, skore version, learner repr, ml task, name, `git_commit`), data references by content hash for train and test X and y (`joblib.hash`, stored once under `datasets/`), metrics CSV, checks CSV, pickles. No model file hash and no training-cutoff field (a `user/` directory is provided for notes). Outside a git repository `git_commit` is recorded as the string "None (working tree dirty)", a bug | RESULT LINEAGE |
| S6 cost | PASS for reports, FAIL for checks on the discovery path | Import 1.7 to 6.9 s; report fit plus summary 0.05 s; `checks.summarize()` 22 to 30 s for one EstimatorReport (SKD011 refits per feature and SKD009 fits a gradient-boosting baseline) and 99 s for a 4-fold shuffled CrossValidationReport; 234 MB RSS; offline; Python 3.13 and pandas 3 work; wheel py3-none-any with Windows classifiers (not tested) | RESULT S6_cost |

## 5. README or docs claims the code does not support (P42)

- README line 47 "methodological guidance": supported by the checks registry (16 checks, two exercised here with the expected outcome). Credited only for SKD011 and SKD013 as measured.
- README line 18 "Track Your Data Science": local tracking works; lineage lacks a model hash and has the `git_commit` bug outside repositories. PARTIAL.

## 6. Proposed rubric scores

| Criterion | Max | Score | Evidence |
|---|---:|---:|---|
| Temporal integrity and leakage safeguards | 18 | 5 | SKD013 flags a shuffled split and passes a time split (ROLE); SKD011 named the trap column as likely target leakage (S1); any sklearn splitter including `TimeSeriesSplit(gap=)`; but checks are advisory, there is no feature availability time or label maturity, and NaN labels give silent NaN metrics |
| Transferable measurable predictive outcomes | 14 | 2 | Evaluation reports for any sklearn classifier or regressor; produces no outcome models of its own |
| Calibration, uncertainty and abstention | 12 | 5 | Brier, log loss, calibration curve, class-imbalance and baseline checks (S2, S4); no recalibration or intervals |
| Catalyst/social/on-chain features | 10 | 0 | None |
| Decision/execution and stress compatibility | 10 | 1 | Check severities (issue, tip) could gate a model card; nothing on costs or execution |
| Code quality, maintenance and tests | 8 | 5 | 183 test files, 34 subset tests pass; commits this week and roughly monthly releases; but Alpha status, test config depends on optional extras, `git_commit` bug, source build version `0.0.0+unknown` |
| Integration fit and extensibility | 8 | 4 | Works on Python 3.13 with pandas 3.1 and numpy 2.5, sklearn-native API; 44 packages including a TUI (textual) and plotting stacks; workspace defaults to the repo root |
| Experiment reproducibility and audit | 8 | 6 | uuid7 ids, UTC dates, content-hashed train and test data, saved CV split indices, metrics and checks CSV, identical reload; no model hash or cutoff field; pickle storage |
| Cost, latency and operational reliability | 5 | 3 | Fast reports, but checks take 22 s to 99 s on 1,746 to 2,300 rows; fully offline (0 connects) |
| Licensing, security and data rights | 7 | 6 | MIT verified; BSD-2 vendored file; no telemetry (measured); network only in hub and CLI features; pickle persistence |
| Total | 100 | 37 | |

## 7. Flags

- REJECT: no.
- RESEARCH_ONLY: not applicable (evaluation tool).
- NOT_REALTIME: yes for the checks (tens of seconds); reports themselves are fast. Offline research use only.
- LEAKAGE_FAIL: not applicable as a model; its checks catch two leakage forms heuristically but do not enforce as-of data.
- Adversarial scenarios: P36 and P13 (SKD011 named the post-decision trap feature; advisory only), P20 (SKD013 catches overlap but has no purge or embargo length), P05 (NaN labels give NaN metrics; scoring censored rows as negatives would flatter Brier from 0.0310 to 0.0261), P10 (SKD004 warns that accuracy is misleading at 3.8 percent prevalence), P32 (hatch hook inspected; no telemetry; 0 connects), P42 (guidance claim credited only where measured).

## 8. Proposed role and integration decision

- Role: a second-opinion evaluation layer for Phases 07 to 13: Brier, log loss and reliability bins per model, plus two checks memelab should copy into its own validator as hard gates rather than tips: a golden-feature test (a single feature that matches a target-trained model means leakage) and a train-test time-overlap test extended with an embargo and per-feature `available_at`.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION for the two checks and the report layout. The library itself is installable in memelab's Python 3.13 and pandas 3 runtime and could be an ISOLATED_RESEARCH tool with `SKORE_WORKSPACE` set outside the repo; not a dependency of `memelab/predictive/`.
- Gap cells addressed: DECISION_RECORDS:CALIBRATION_SCORING, HIST_MARKET:CALIBRATION_SCORING, SOCIAL_REPLAY:CALIBRATION_SCORING (MISSING or PARTIAL); partly the MODEL_REGISTRY cells (report lineage, not a registry).

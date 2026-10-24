# Source review: ip200/venn-abers (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | ip200/venn-abers, https://github.com/ip200/venn-abers |
| Pinned SHA | `60767e4160609246bdc14face3f11d0848fcf1b4` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-09-02T05:15:45+01:00 |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/ip200__venn-abers`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:14Z |
| Version tested | 1.5.4 built from the pinned source on Python 3.13.17 (venv `/home/claude/pi_research/venvs/ip200__venn-abers`; numpy 2.5.4, scikit-learn 1.9.1, pandas 3.1.0). `setup.py` imports `distutils.core`, removed from the 3.12+ standard library; the build worked because setuptools in the isolated build environment provides the distutils shim |
| Relation to PyPI | PyPI has only an sdist, `venn_abers-1.5.4.tar.gz` (2026-08-12, sha256 `a6bf5383e618ce42...`); its 2 `.py` files are byte-identical to the pin. PyPI declares no Python version or 3.13 classifier; it installs and runs on 3.13 here |

## 2. License and security

- Root `LICENSE.TXT`: MIT text ("Copyright (c) 2023 Ivan Petej"), sha256 `232ce5b45cb001df231b9f25315f4437fca0262d29a59030fe356fb13dc62ac9` (matches Phase 02). No vendored code.
- Runtime dependencies: numpy, scikit-learn, pandas (BSD-3). Installed licenses: `SMOKES/ip200__venn-abers/raw_dep_licenses.txt`.
- Model weights: none. Install-time scripts: `setup.py` with `distutils.core.setup`, no custom commands (inspected before building).
- Network: no network code (grep); smoke ran inside `unshare -n`. No telemetry.
- Secrets: none.
- Persistence: pickle only.

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| IVAP core | `src/venn_abers.py:14` `calc_p0p1`, `:220` `calc_probs`, `:462` `VennAbers` | classification branch sets `p1[-1, 1] = 1.0` (`:118`), the 1.5.4 fix for scores above every calibration score. `calc_probs` looks p0 up with `searchsorted(..., 'right')` and p1 with `'left'` and has no NaN check, so a NaN score is treated as larger than every calibration score |
| Calibrator | `:1102` `VennAbersCalibrator` (`shuffle=True` default at `:1218`), `:1235` fit, `:1280` predict_proba with a manual mode (`p_cal`, `y_cal`, `p_test`) for pre-fitted models | in estimator mode it clones and refits the estimator on all rows and on a `train_test_split` proper-training part (`VennAbersCV.fit`, `:669` to `:700`); the split shuffles by default |
| Inductive / cross mode | `:568` `VennAbersCV` (docstring says `shuffle` default True, code default False at `:646`), `:890` `VennAbersMultiClass` | doc and code disagree on the default |
| Input handling | `:297` `adjust_categorical_train`, `:324` `adjust_categorical_test` | every input goes through `pandas.get_dummies`, also for numeric arrays |
| Regression | `:1412` `VennAbersRegressor` | not tested |
| Time handling | none | no notion of time; ordering depends on `shuffle` |
| Serialization | none | pickle |
| Tests | 4 test files | ran all: 18 passed, 6 warnings, 1.99 s, exit 0 (`SMOKES/ip200__venn-abers/raw_repo_tests_venn_abers.txt`) |

## 4. Smoke results

Script `SMOKES/ip200__venn-abers/smoke_venn_abers.py` inside `unshare -n`; exit 0, wall 3.35 s, peak RSS 158.9 MB; raw output `SMOKES/ip200__venn-abers/raw_smoke_venn_abers.txt`. Same shared base model and purged splits as the other calibration reviews (calibration 511 rows with 16 positives; holdout 527 with 17 positives; 107 censored excluded); base holdout hash `cc58f5135049e5ed`.

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (no guard in the library) | trap available after the decision in 3000 of 3000 rows; Venn-Abers on the leaky model keeps BSS 0.9221 (base 0.0123) |
| S2 probability shape | PASS | output shape (527, 2), rows sum to 1, finite, in [0, 1] (min 0.0099, max 0.6250) |
| S3 missing covariates | FAIL (silent) | a NaN calibration score is accepted without a warning; a NaN test score returns `[0.375, 0.625]` (it is treated as above every calibration score). In estimator mode NaN features work when the estimator imputes |
| S4 calibration and uncertainty | PASS for correctness, weak on 16 positives | merged probability: Brier 0.03368 vs baseline 0.03128 (BSS -0.0768), log loss 0.14123 vs 0.14334; ECE 10 uniform bins 0.01382, 5 quantile bins 0.01583, all 5 quantile bins inside Wilson 95%; calibration in the large mean p 0.0428 vs prevalence 0.0323, inside Wilson (0.0202, 0.0510). Interval p1 - p0: median 0.0075, p90 0.0210, max 0.6000; mean p0 0.0286 and mean p1 0.0479 bracket the observed 0.0323. Definition check against an isotonic refit with the test score appended (530 probe scores incl. 2 above and 1 below the calibration range): max difference 0 for both p0 and p1 (above the range p1 = 1.0000, MAPIE's port gives 0.6000). Manual mode equals the `VennAbers` class |
| S4c time-ordered inductive mode | FAIL by default | estimator mode on time-ordered train plus val rows, `cal_size=0.2`: with the default `shuffle=True` all 433 calibration rows have a later proper-training row (future rows train the scorer that scores the past); with `shuffle=False` none do (holdout Brier 0.03616 vs 0.03513). Even with `shuffle=False` there is no purge gap between proper-training labels and calibration decisions |
| S5 persistence | PASS | pickle 20,806 bytes; identical output after reload |
| S6 cost | PASS | fit on 511 scores 7.9 to 11.3 ms; predict 0.23 us per row; peak RSS 159 MB; offline. sdist only on PyPI (pure Python, builds on any OS with setuptools); runs on 3.13 although undeclared. File list: `SMOKES/ip200__venn-abers/raw_pypi_files_r2.txt` |

Reliability bins of the merged Venn-Abers probability, 10 uniform bins (n, mean p, observed, positives): [0.0, 0.1) 512, 0.0323, 0.0293, 15; [0.1, 0.2) 5, 0.1713, 0.0000, 0; [0.3, 0.4) 3, 0.3769, 0.6667, 2; [0.5, 0.6) 3, 0.5000, 0.0000, 0; [0.6, 0.7) 4, 0.6250, 0.0000, 0. The four rows at 0.6250 are the holdout scores above every calibration score; all four are negatives. MAPIE's defective port gives them 0.5000, which scores better here by accident; a correct calibrator cannot be chosen by holdout score on 17 positives.

## 5. Claims the code does not support (P42)

- UNSUPPORTED: `VennAbersCV` docstring "shuffle : bool, default=True"; the code default is False (`:646`). `VennAbersCalibrator` does default to True.
- The README example (`VennAbersCalibrator(estimator=clf, inductive=True, cal_size=0.2, random_state=101)`) is correct for exchangeable data but shuffles time-ordered rows (S4c); the README does not mention ordering.
- README "fully compatible natively with the scikit-learn ecosystem": the repo's `check_estimator` tests pass (18 passed); not contradicted.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 0 | no time notion; estimator mode shuffles time by default (S4c); trap accepted (S1) |
| Transferable measurable predictive outcomes (14) | 3 | calibrates binary and multiclass probabilities and has a regression variant (S2, S4; regression not tested); no outcome model of its own |
| Calibration, uncertainty and abstention (12) | 7 | exact match to the IVAP definition on 530 probes including outside the calibration range (S4); the [p0, p1] width is a direct uncertainty signal; minus: NaN scores silently produce 0.625 (S3), no abstention output |
| Catalyst, social and on-chain features (10) | 0 | none |
| Decision and execution compatibility (10) | 0 | none |
| Code quality, maintenance and tests (8) | 4 | 4 test files, 18 pass; changelog with real fixes (1.5.4); one maintainer; deprecated `distutils` in `setup.py`; doc and code default mismatch |
| Integration fit and extensibility (8) | 6 | manual mode needs only score arrays; small; runs on 3.13 (S6); pandas `get_dummies` on every input and scikit-learn dependency |
| Experiment reproducibility and audit (8) | 3 | deterministic manual mode, `random_state` for split modes, pickle identical (S5); no lineage |
| Cost, latency and operational reliability (5) | 5 | about 10 ms fit, sub-microsecond prediction, offline (S6) |
| Licensing, security and data rights (7) | 6 | MIT, no network, no vendored code; fitted state only as pickle |
| **Total** | **34** | |

## 7. Flags and adversarial scenarios

- Flags: none.
- P24: with 16 calibration positives the merged probabilities scored worse than the base model (BSS -0.0768) while the interval stayed narrow for most rows; the [p0, p1] width alone does not reveal the small calibration set.
- P38: NaN in, 0.625 out, no error (S3); the wrapper must reject non-finite scores before calling it.
- P13 and P36: no checks; wrapper must enforce.
- P31: MIT; MAPIE's port of this code is a separate reimplementation under BSD-3 with attribution to this repo.
- New wrong-but-plausible case found: two calibrators that agree on every in-range score and differ only above the calibration range; caught only by the definition oracle with probes outside the range, never by holdout Brier on 17 positives.

## 8. Proposed role and integration decision

Reference oracle and candidate calibrator for Phase 08/09: use the manual mode (`p_cal`, `y_cal`, `p_test`) on scores from the lab's own as-of pipeline, never the estimator mode with its shuffled split. The IVAP core is about 100 lines; a numpy reimplementation in `memelab/predictive/` checked against this package and against the isotonic definition is simpler than a dependency on scikit-learn plus pandas.

Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION (with this pinned package kept in the research venv as a test oracle). Phase 01 gap cells addressed: DECISION_RECORDS:CALIBRATION_SCORING (MISSING), HIST_MARKET:CALIBRATION_SCORING (MISSING), SOCIAL_REPLAY:CALIBRATION_SCORING (PARTIAL), TRADE_OUTCOMES:CALIBRATION_SCORING (PARTIAL). License obligation if code is copied: MIT notice.

# Source review: henrikbostrom/crepes (reviewer R2)

Synthetic challenge only. Every number below is a format and behaviour check on `challenge.csv` (sha256 `18fda40c...d5f23d`), never evidence of memecoin edge.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | henrikbostrom/crepes, https://github.com/henrikbostrom/crepes |
| Pinned SHA | `88a0dfacabb2fcbd918f0e3c3f0bf885422e70f4` (Phase 02 SHORTLIST.csv) |
| Commit date | 2026-07-08T10:07:38+02:00 |
| How fetched | shallow fetch of the pinned SHA at 2026-10-24T04:33Z into `/home/claude/pi_research/src/henrikbostrom__crepes`; HEAD verified equal to the pin |
| Review time (UTC) | 2026-10-24T04:33Z to 05:12Z |
| Version tested | 0.9.1 built from the pinned source (`setup.py` and `pyproject.toml` inspected first: plain setuptools, no custom commands), venv `/home/claude/pi_research/venvs/henrikbostrom__crepes`, Python 3.13.17, numpy 2.5.4, pandas 3.1.0, scipy 1.18.1; scikit-learn 1.9.1 added only for the shared base model |
| Relation to PyPI | the 4 `.py` files of the PyPI wheel `crepes-0.9.1-py3-none-any.whl` (2026-06-12, sha256 `d1e0c4c212c72883...`) are byte-identical to the pin |

## 2. License and security

- Root `LICENSE`: BSD-3-Clause text ("Copyright 2026 Henrik Boström"), sha256 `3bed289f17251cce33c559c66ed6cd240c518f721c62cfde4ab1aaeb264eabeb` (matches Phase 02). No vendored code, no per-file licenses (4 source files).
- Runtime dependencies: numpy, pandas, scipy (BSD-3). The package does not import scikit-learn. Installed licenses: `SMOKES/henrikbostrom__crepes/raw_dep_licenses.txt`.
- Model weights: none. Install-time scripts: a plain `setuptools.setup()` with no custom commands.
- Network: no network code in `src/crepes` (grep). The smoke ran inside `unshare -n` and completed. No telemetry.
- Secrets: none handled.
- Side effect to know: seeded calls save the global numpy RNG state, call `np.random.seed`, and restore it afterwards (`base.py:3544` and `:3576`, likewise `:2201`/`:2597`, `:2882`/`:2965`). Not thread-safe with other users of the global RNG.
- Persistence: pickle only (no save format); fitted state is small (calibration scores).

## 3. Code paths inspected at the pin

| Area | Anchor | Observation |
|---|---|---|
| Wrapper | `src/crepes/base.py:3314` `WrapClassifier`, `:3335` fit, `:3416` predict_proba (passes the learner's output through), `:3450` calibrate, `:3579` predict_p, `:3691` predict_set, `:3828` evaluate | a learner fitted outside can be wrapped and calibrated directly |
| Conformal classifier | `base.py:51` `ConformalClassifier`, `:64` fit, `:125` predict_p, `:193` predict_p_online, `:270` predict_set | Mondrian categories through `bins`; class-conditional when `class_cond=True` |
| Scores and categories | `src/crepes/extras.py:24` hinge, `:82` margin, `:147` binning, `:254` MondrianCategorizer | user-defined category functions accepted |
| Exchangeability / drift | `src/crepes/martingales.py:224` SimpleJumper, `:336` SleeperStayer, `:580` CompositeMartingale, `:678` semi_online_p_values | conformal test martingales over a time-ordered sequence |
| Time handling | `predict_p_online` / `predict_set_online` (semi-online calibration, `base.py:193`, `:347`) | calibration set grows in time order; no feature-availability check, no purge |
| Probability calibration | none | grep for isotonic, Venn, Platt or sigmoid in `src/crepes` finds nothing |
| Serialization | none | pickle |
| Tests | 0 test files at the pin | no repo tests to run; recorded as SKIPPED |

## 4. Smoke results

Script `SMOKES/henrikbostrom__crepes/smoke_crepes.py` (with `common.py`, `runner.py`) inside `unshare -n`; exit 0, wall 5.38 s, peak RSS 241.0 MB; raw output `SMOKES/henrikbostrom__crepes/raw_smoke_crepes.txt`. Same shared base model and purged splits as the other calibration reviews (fit rows 1,650 after purging 96; calibration 511 rows with 16 positives; holdout 527 with 17 positives; 107 censored excluded). Base holdout prediction hash `cc58f5135049e5ed`, identical to the MAPIE, venn-abers, model-diagnostics and arch smokes.

| ID | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (no guard in the library) | trap available after the decision in 3000 of 3000 rows; with the trap the holdout BSS is 0.9452 (base 0.0123); crepes calibrated it without complaint (90% sets: coverage 0.9279, positives 2 of 17) |
| S2 probability shape | PASS (pass-through) | `predict_proba` shape (527, 2), identical to the base model; Brier 0.03089 vs baseline 0.03128 (BSS 0.0123), log loss 0.13763 vs 0.14334; crepes adds p-values and sets, not recalibrated probabilities |
| S3 missing covariates | PASS (defers to the learner) | bare LogisticRegression raises on NaN; with SimpleImputer inside the learner, crepes returns sets for all 527 rows |
| S4 conformal sets and p-values | PARTIAL | standard (hinge), confidence 0.90: coverage 0.9184, positives 0 of 17, negatives 0.9490, sets 498 `{0}` and 29 empty; 0.95: 0.9431, positives 0 of 17. Class-conditional (Mondrian by label), 0.90: coverage 0.9336, positives 16 of 17 (0.9412), negatives 0.9333, sets 84 `{0}`, 37 `{1}`, 406 `{0,1}`; 0.95: 0.9526, positives 0.9412, 487 of 527 sets are `{0,1}`. Smallest non-smoothed p-value for label 1 is 0.0588 = 1/(16+1), so with 16 calibration positives label 1 can never be excluded at 95%. `evaluate` KS test of p-value uniformity on the holdout: p = 0.00062 (standard) and 0.00114 (class-conditional), consistent with the holdout covariate shift. Mondrian by fatal_flag: 454 and 57 calibration rows; holdout coverage 0.9136 (n 463) and 0.9375 (n 64) |
| S5 persistence | PASS | pickle 6,038 bytes; identical p-values after reload with the same seed. Seeded calls are deterministic |
| S6 cost | PASS | calibrate 2.9 ms; predict_set 107.7 us per row; peak RSS 241 MB including scikit-learn; offline. PyPI ships one `py3-none-any` wheel, Python 3.13 declared and tested; Windows uses the same wheel |
| Role: drift / exchangeability | PASS | conformal test martingales (threshold 100, so a false alarm has probability at most 1/100 under exchangeability) on time-ordered sequences. No alarm on train then val (2,302 rows) or val only (556 rows) for either sequence. Val then holdout, raw log1p(liq_usd): alarm at index 619 (SimpleJumper), 637 (SleeperStayer), 622 (Composite); the first holdout row is index 556, so the shift is flagged about 63 to 81 rows after it starts. On the label-free p(positive) sequence no alarm (shift too weak in the model output) |
| Repo tests | SKIPPED | no test files at the pin |

## 5. Claims the code does not support (P42)

- None found UNSUPPORTED. The README promises "well-calibrated p-values ... with coverage guarantees" under exchangeability and points to `crepes.martingales` for testing that assumption; the smoke matched that: marginal coverage held on the holdout, the KS test reported non-uniform p-values under the shift, and the martingale flagged the shift.
- Note: "coverage guarantees" are marginal or per Mondrian category; with 16 calibration positives the class-conditional sets are mostly `{0,1}` (uninformative), which the README does not claim otherwise.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 4 | conformal test martingales detected the holdout shift within 63 to 81 rows with no false alarm on 2,302 and 556 in-distribution rows (role row); semi-online calibration in time order (`base.py:193`); no feature-time check (S1), no purge |
| Transferable measurable predictive outcomes (14) | 3 | conformal classifiers, regressors and predictive systems around any learner (S2, S4; regressors and predictive systems not tested); produces no outcome model itself |
| Calibration, uncertainty and abstention (12) | 6 | marginal, class-conditional and Mondrian coverage verified, p-values with a uniformity test (S4); class-conditional sets reach 0.94 positive coverage; no probability recalibration for classifiers (grep) |
| Catalyst, social and on-chain features (10) | 0 | none |
| Decision and execution compatibility (10) | 0 | none |
| Code quality, maintenance and tests (8) | 3 | no tests at the pin; single maintainer; detailed changelog and docs; recent release (0.9.1, 2026-06-12); global RNG save and restore |
| Integration fit and extensibility (8) | 6 | four files, numpy/pandas/scipy only, no scikit-learn needed, Python 3.13 works, any `predict_proba` or a raw score array can be used (S2, S6) |
| Experiment reproducibility and audit (8) | 3 | seed parameter gives identical outputs, pickle reload identical (S5); no lineage or run metadata |
| Cost, latency and operational reliability (5) | 5 | millisecond calibration, about 0.1 ms per row prediction, offline (S6) |
| Licensing, security and data rights (7) | 6 | BSD-3, no vendored code, no network (section 2); fitted state only as pickle |
| **Total** | **36** | |

## 7. Flags and adversarial scenarios

- Flags: none.
- P10 and P24: with 16 calibration positives, standard sets cover 0 of 17 positives and class-conditional sets are mostly `{0,1}`; the p-value floor 1/17 is explicit and auditable, which is the honest form of "not enough events".
- P39: the martingale is a usable drift monitor (alarm after the shift, none before).
- P36 and P13: no availability or artifact-cutoff check; the wrapper must refuse the trap.
- P31: BSD-3, no copied code found. P32: no install scripts.
- New wrong-but-plausible case found: a drift monitor run on the model's output alone (p(positive)) stays silent while the input feature has shifted; caught by running the same martingale on the raw feature sequence.

## 8. Proposed role and integration decision

Two roles: (1) drift and exchangeability monitoring for Phase 19 (martingales over time-ordered feature and score sequences, run offline on each day's export); (2) optional class-conditional conformal sets as an abstention signal once there are enough positives. It is not a probability calibrator.

Candidate INTEGRATION_DECISION: ADAPTER (offline monitoring and evaluation, called on arrays from the lab's own as-of pipeline; pin the version). Phase 01 gap cells addressed: HIST_MARKET:DRIFT_MONITORING, DECISION_RECORDS:DRIFT_MONITORING, SOCIAL_REPLAY:DRIFT_MONITORING (all MISSING), and the CALIBRATION_SCORING cells named in Phase 02 (DECISION_RECORDS, HIST_MARKET, SOCIAL_REPLAY, TRADE_OUTCOMES) for set-valued abstention only. License obligation if code is copied: BSD-3 notice.

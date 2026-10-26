# Calibration card (Phase 13, calibration-1 and abstention-1)

Rules: `ACCEPTANCE_CHECKLIST.md` (frozen before any code, commit `0fdf698`) and PI-D-067; self-review repair PI-D-068; repair pass 2 after the independent skeptic PI-D-070; G7 decision PI-D-071. Code: `memelab/predictive/calibration.py`, `memelab/predictive/abstention.py`. Run: `probes/run_calibration.py` at `075026d` (repair pass 2). Against the first recorded run (`5a3c582`, `2e1488a`) no status, count, number, reason or verdict changed: the cards gained availability and evidence fields (new card sha256), every FLAG_OFF condition now names the config, the matrix gained the CALIBRATION_AFTER_DECISION row (0 everywhere) and `EXCHANGEABILITY.json` gained Holm, first-day and route-rate entries (`evidence/rerun_rp2_diff.json`). Machine-readable artifacts: `artifacts/<target>/CALIBRATION_CARD.json`.

Format note: a calibration card says whether a probability may be published and why. It is not a claim of predictive skill.

## Result in one line

No primary target can be calibrated: the only chronologically valid calibration rows are the champion B2's development out-of-sample rows, 24 (T1), 44 (T1b) and 8 (T2), with 8, 3 and 1 positive, far below the frozen gate of 100 events with 20 per class over 5 days. Status UNCALIBRATED, level ABSTAIN, publishable false, for all three. Every forecast request on development, on the opened holdout and on today's prospective decisions ends ABSTAIN with named reasons. Publication coverage is 0%. This is what PI-D-067 stated in advance.

## The calibration artifacts

| Target | Calibration set (n, positives, days) | Fit gate shortfalls | Calibrator | Evidence | Status | Level | Card sha256 |
|---|---|---|---|---|---|---|---|
| T1 24 h (`price_path_target_before_invalidation_24h`) | 24, 8, 3 | events 24 < 100; per class 8 < 20; days 3 < 5 | none | prospective holdout, NOT_YET_MATURED | UNCALIBRATED | ABSTAIN | `21384176...` |
| T1b 6 h (`price_path_target_before_invalidation_6h`) | 44, 3, 5 | events 44 < 100; per class 3 < 20 | none | prospective holdout, NOT_YET_MATURED | UNCALIBRATED | ABSTAIN | `bd199528...` |
| T2 24 h (`price_path_severe_drawdown_or_halt_24h`) | 8, 1, 1 | events 8 < 100; per class 1 < 20; days 1 < 5 | none | prospective holdout, NOT_YET_MATURED | UNCALIBRATED | ABSTAIN | `ddaa581c...` |

Each card names its champion (the frozen Phase 07 B2 card at 2026-10-17T00:00Z, by default and not by evidence, PI-D-064), the calibration rows (sha), the fit gate, the method rule (Venn-Abers from 200 events with 40 per class, else Platt, else none), the support bins, the degeneracy check (no target is flat), the evidence rule (50 events, 10 per class, prospective only) and the interval rule. No larger valid calibration set exists: the first fold needs 100 training events, so at most 36 (T1), 124 (T1b) and 31 (T2) development rows could ever be scored out of sample, and T1b has only 26 positives in all of development. Even a gate at the holdout minimums (50 events, 10 per class) would fail for all three.

Calibration sets are re-derived by the runner from the Phase 07 fold cards through `labels.training_labels`: fold card sha256 equal to the committed fold artifacts (3, 5 and 1 folds), out-of-sample B2 and B0 numbers equal to `phase_07/experiments/OOS_PREDICTIONS.csv` within its 6-decimal rounding (largest difference 5.0e-7).

## Reliability of the raw champion numbers (descriptive; these are not calibrated probabilities)

From `calibration/RELIABILITY_COVERAGE.csv` (Wilson 95%, the frozen ACCEPTANCE tolerance; under 40 events in the large only):

| Target | View | n | Positives | Mean B2 | Observed | Wilson | Inside | Training base rate at H |
|---|---|---|---|---|---|---|---|---|
| T1 | development out of sample | 24 | 8 | 0.230 | 0.333 | 0.180 to 0.533 | yes | 0.250 |
| T1b | development out of sample | 44 | 3 | 0.111 | 0.068 | 0.023 to 0.182 | yes | 0.116 |
| T1b | bin 0 / bin 1 | 22 / 22 | 0 / 3 | 0.047 / 0.175 | 0.000 / 0.136 | 0.000 to 0.149 / 0.047 to 0.333 | yes / yes | |
| T2 | development out of sample | 8 | 1 | 0.176 | 0.125 | 0.022 to 0.471 | yes | 0.214 |
| T1 | retrospective holdout, POST_OPENING | 66 | 15 | 0.193 | 0.227 | 0.143 to 0.342 | yes | 0.250 |
| T1b | retrospective holdout, POST_OPENING | 68 | 12 | 0.082 | 0.176 | 0.104 to 0.284 | no | 0.116 |
| T2 | retrospective holdout, POST_OPENING | 59 | 7 | 0.119 | 0.119 | 0.059 to 0.225 | yes | 0.214 |

"Inside" on a handful of rows is not calibration: with 8 or 24 rows almost any mean falls inside a Wilson interval that wide. Per-fold rows (one decision day each, 5 to 11 rows) are in the CSV with "n below 20 gives no rate claim". The holdout rows equal Phase 12's `CALIBRATION_BINS.csv` (checked by the runner).

## Scores on the development out-of-sample rows (P10, P23)

`calibration/SCORE_REPORT_DEV.json`, B2 against the fold training prevalence (B0), both scores always reported with counts:

| Target | n (positives, days) | Brier B2 / B0 | Log loss B2 / B0 | Brier skill (governing interval) | Log-loss skill | Flag |
|---|---|---|---|---|---|---|
| T1 | 24 (8, 3) | 0.245 / 0.230 | 0.719 / 0.655 | -0.066 (day: -0.613 to 0.094) | -0.097 | |
| T1b | 44 (3, 5) | 0.059 / 0.067 | 0.217 / 0.266 | 0.108 (mint: -0.127 to 0.219) | 0.184 | |
| T2 | 8 (1, 1) | 0.153 / 0.127 | 0.419 / 0.432 | -0.197 (mint: -2.049 to 0.914) | +0.029 | BRIER_LOGLOSS_CONFLICT |

No AUC or average precision is reported (fewer than 10 per class everywhere). T2 shows the P23 case on real rows: Brier says worse than the base rate, log loss says slightly better, on 8 rows with 1 positive; neither supports a claim.

## Event-rate uncertainty and exchangeability (rules 10, 11)

`calibration/BASE_RATE_UNCERTAINTY.csv` (all development labels at H, 20,000 replicates) and `calibration/EXCHANGEABILITY.json` (20,000 label permutations):

| Target | Base rate (n) | Wilson | Day block | Mint block | Governing width / Wilson | Day heterogeneity p (Holm of 6) | Without 2026-10-07 | Route heterogeneity p (Holm of 6) | Event rate PIT_RECORDED / CURRENT_VENDOR_LIST |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 0.250 (136) | 0.185 to 0.329 | 0.187 to 0.333 | 0.178 to 0.329 | 1.04 | 0.249 (0.305) | 0.400 | 0.021 (0.098) | 31/102, 3/34 |
| T1b | 0.116 (224) | 0.080 to 0.165 | 0.075 to 0.191 | 0.068 to 0.172 | 1.38 | 0.023 (0.098) | 0.949 | 0.011 (0.065) | 24/159, 2/65 |
| T2 | 0.214 (131) | 0.152 to 0.292 | 0.095 to 0.306 | 0.144 to 0.295 | 1.51 | 0.020 (0.098) | 0.188 | 0.152 (0.305) | 24/98, 4/33 |

Reading, corrected in repair pass 2 (PI-D-070, skeptic m2): heterogeneity of the event rate is suggested but not significant after Holm over the six tests (smallest adjusted p 0.065). The day signal rests on the first decision day, 2026-10-07: without it T1b's day p is 0.95 and T2's 0.19; the skeptic also found T1b's day effect gone under a mint-cluster permutation (p 0.15) while T2's stayed (p 0.014). The route effect is a label-route effect, not a time trend: decisions labelled on the CURRENT_VENDOR_LIST route (no point-in-time pool) have much lower event rates (T1 3/34, T1b 2/65) than PIT_RECORDED ones (31/102, 24/159), and both routes span every day. So exchangeability is neither established nor clearly refuted: Venn-Abers validity and any conformal guarantee assume it, it cannot be tested across regimes (one out-of-sample regime label in development, Phase 11), and the block intervals of the base rate are 1.04 to 1.51 times the independent-row Wilson width. This is a reason for caution, not a finding to build on; no later phase should treat it as a regime claim.

## What an interval would look like at today's support (P23, P24; descriptive, below the gate)

`calibration/BELOW_GATE_DESCRIPTIVE.json` fits Venn-Abers and Platt on the development out-of-sample rows only to show widths on real data; neither is a calibrator and neither is publishable. At the median raw B2 number the hull interval (Venn-Abers [p0, p1] with the Wilson interval of the support bin) is 0.180 to 0.533 (T1, support 24 with 8 positive), 0.000 to 0.149 (T1b, support bin of 22 with 0 positive; 0.000 to 0.333 at the 75th percentile, bin of 22 with 3) and 0.000 to 0.471 (T2, support 8, below the support minimum of 20). These widths are the honest uncertainty from calibration sampling alone. On T1 the descriptive Platt slope is positive (the raw number moves against the outcome on these 24 rows).

Forward over the folds (fit only on rows matured by each fold cutoff): T1 has one usable fold (fit 11 rows, mean p0 to p1 0.23 to 0.52, observed 0.60 on 5 rows, outside); T1b four folds (observed inside mean p0 to p1 in 3 of 4, widths 0.10 to 0.30); T2 none.

## Retrospective holdout: POST_OPENING description only

The holdout is spent (PI-D-065). `calibration/HOLDOUT_POST_OPENING.json` is computed from committed Phase 12 files, logged (`calibration/POST_OPENING_LOG.json`, time in `evidence/run_log.json`), never fitted on, and combined with `evaluation.conservative_status`.

- The development-fitted descriptive Venn-Abers applied to the holdout B2 numbers fails the frozen check in the large for all three targets (T1 mean 0.364 against observed 0.227; T1b 0.095 against 0.176; T2 0.246 against 0.119) and its mean [p0, p1] misses the observed rate for T1 (0.283 to 0.417) and T1b (0.022 to 0.119). Combined state FAILS_SELECTION_CORRECTION for all three: more conservative, never a claim.
- Prevalence shift, development against holdout (permutation p): T1 0.250 to 0.227 (p 0.73), T1b 0.116 to 0.176 (p 0.22), T2 0.214 to 0.119 (p 0.15). The development day-block intervals of the base rate cover the holdout rates of all three (description only).
- The abstention layer on the 66, 68 and 59 scored holdout rows: all ABSTAIN.

## Abstention and coverage

`calibration/ABSTENTION_MATRIX.csv` (and `.md`) lists all 29 conditions (28 pre-registered, 1 added by PI-D-070) with their contract reason and counts. Development (76 requests): every request has FLAG_OFF, MODEL_NOT_PROMOTED, NO_CALIBRATOR, CALIBRATION_SET_TOO_SMALL, CALIBRATION_EVIDENCE_TOO_SMALL and CALIBRATION_EVIDENCE_PENDING; also POOL_NOT_POINT_IN_TIME on 17 (the CURRENT_VENDOR_LIST route), LOW_SUPPORT on 60, SCORE_OUTSIDE_CALIBRATION_RANGE on 4 and FEATURE_OUT_OF_RANGE on 1. Holdout POST_OPENING (193 requests) the same standing conditions, plus POOL_NOT_POINT_IN_TIME on 37, SCORE_OUTSIDE_CALIBRATION_RANGE on 16 and LOW_SUPPORT on 65. Coverage: raw model number 100% of requests, calibrated number 0%, published probability 0%.

Today (`calibration/TODAY_STATUS.json`, as of 2026-10-26T20:00:00Z): every target is ABSTAIN with FLAG_OFF, MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY and NOT_YET_MATURED. The 10 prospective decisions in the development store also carry OOD (their features are not in the Phase 05 store) and SOURCE_STALE (no price read); one carries TARGET_NOT_FEASIBLE (no point-in-time pool). No label of them was read. The champion cards are MODEL_STALE for decisions after 2026-10-31T00:00:00Z.

## What the layer refuses (each with a test that fails without it)

- Calibration rows that are in sample, decided at or after the cutoff, immature, from the holdout window (also when relabelled as development) or non-finite; evidence that is not prospective, overlaps the fit set or is immature; a behavioral simulation as a calibration source (P27). CX-13 (Platt fitted and checked on the spent holdout, then published) is refused at every step, on fixtures and on the real holdout rows (`calibration/REPLAY_CHECKS.json`).
- Non-finite or out-of-range raw or calibrated numbers (P38); flat predictions (P11); a 0.9 model on a 2% class; an always-negative model on a 1% event (P10); a confident number on a 30-event set (P24).
- With the flag OFF in the config, any FORECAST, whatever the caller says (PI-D-070, M1). A calibration card whose recorded gate, method, evidence, status, details or availability is not what its own counts allow, whose evidence is not the prospective holdout, whose rows lie in the holdout window, or which gives itself VALIDATED_EXPERIMENTAL (M2; the skeptic's forged cards A2, A2b, A2c, A7b). A calibration card or evidence available after the decision (CALIBRATION_AFTER_DECISION, M3). Flat evidence, and request scores outside the evidence's score range (M4, CX-S13).
- A FORECAST whose `calibration_reference` has a key outside the allowlist, a number that differs from the stored card, a support that is not a stored bin, an interval narrower than the support's Wilson interval, a base rate other than the card's, a level other than SHADOW or VALIDATED_EXPERIMENTAL, a missing SHADOW_RESEARCH_ONLY, INTERVAL_EXCLUDES_UNMODELED_RISK or COHORT_ESTIMATE_NOT_TOKEN_HISTORY caveat, or any probability-like number in scenarios or cohort (P27).

## What any interval leaves out

Execution (no historical executable depth, size gives EXECUTION_DATA_MISSING), fees and slippage, liquidity collapse, rug and authority events not in the inputs, catalysts (no catalyst rows exist), regime changes beyond the development days, vendor revisions, and model misspecification. A published interval would carry INTERVAL_EXCLUDES_UNMODELED_RISK for that reason.

## Limits and what later phases must do

- The publication path (FORECAST) is TEST_ONLY: it is proved on fixtures; no real card is calibrated.
- G7 failed as registered and stays recorded so: scikit-learn `_sigmoid_calibration` differs from the numpy Platt by 1.5e-6 (T1b) and 9.4e-6 (T2) on the descriptive sets because its lbfgs stops early. Closed by the orchestrator's decision PI-D-071: the numpy Platt equals a 60-digit Newton solution within 1e-15 (skeptic), scikit-learn with tight tolerances converges to it, and PI-D-053 had already frozen newton-cholesky (5.3e-15 here) as the reference; the Platt fit is now pinned by `test_rp2_numpy_platt_equals_a_60_digit_newton_solution` (within 1e-9 of an independent decimal Newton solve, gradient below 1e-10). No output depends on these fits.
- Level authenticity needs the Phase 16 registry: a card cannot give itself VALIDATED_EXPERIMENTAL (refused until then), and SHADOW always carries SHADOW_RESEARCH_ONLY.
- Open for Phase 17 (skeptic m3, m4): a forged point inside a wide interval and reasons dropped from a document that travels without its record cannot be detected from the document alone; Phase 17 recomputes the point from the raw number it keeps and validates every document with its persisted record.
- The document alone cannot prove the published point equals the calibrator's output for the raw number (the contract has no raw-number field); Phase 17 keeps the raw number in its request record and recomputes the point before publishing.
- Only the prospective holdout (Phase 19, at least 50 matured events and 10 per class per target, not the fit set) can be calibration evidence; Phase 16 decides levels; a card reaches publication only through both.

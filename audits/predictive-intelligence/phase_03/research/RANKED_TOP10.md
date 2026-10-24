# Ranked top ten (Phase 03)

Status: final after the repair pass that folds in the orchestrator's blind second rescore (INDEPENDENT_RESCORE.md) and the independent skeptic (`../skeptic/PHASE_03_SKEPTIC.md`). Scores are the lead's, applied uniformly from `RUBRIC_ITEMS.csv` under the application rules of PI-D-026 and PI-D-029; the reviewers' proposed totals stay beside them and the blind rescorer's totals are in INDEPENDENT_RESCORE.md. Nothing here is evidence of memecoin predictive value: every smoke ran on the synthetic challenge (`SMOKES/_challenge/NOTE.md`), so the ranking measures fitness for the lab's pipeline (time discipline, outputs, calibration tools, licensing, cost), not forecast skill.

## How the numbers were made

- Locked weights from the package's `references/GRADING_RUBRIC.md` (18, 14, 12, 10, 10, 8, 8, 8, 5, 7). Each criterion is split into all-or-nothing items in `RUBRIC_ITEMS.csv` (50 items, sha256 `cb4b0a21...`), written and hashed at 05:51Z before any repository was scored; the items of a criterion sum to its locked weight. The item file is unchanged in the repair pass; how items are applied changed by change control CP03-1 (PI-D-029).
- `SCORE_ITEMS.csv` holds every repository x item (1,500 rows): points 0 or the item's full value, an evidence reference for every point and the verification checks that back it. Unanswered = 0.
- `SCORECARD.csv` recomputes from the items; reviewers' per-criterion proposals are parsed from section 6 of each review.
- Eligible = not under a hard-veto REJECT for its recommended route. 29 of 30 are eligible; `baobach/mlfinpy` is REJECT (BSD-3 mlfinlab code without its notice in the module the role runs, snippet rights UNKNOWN; LEAKAGE_FAIL purge; MF-1, MF-2). Route-level REJECTs do not remove a repository: TabPFN's default weights, hazardous's PyPI 0.2.0 artifacts, OASIS's bundled Twitter pickles and MiroFish's in-process or served use are rejected, but each has a permitted research route.
- Sort: total descending; ties broken by the criteria in descending locked weight (temporal, outcomes, calibration, features, decision, code, integration, reproducibility, license, cost), then name. Reproduce: `python3 verify/build_scorecard.py && python3 verify/check_scorecard.py` (problems 0).

## Table

| Rank | Repository | Lead total | Reviewer total | T 18 | O 14 | C 12 | F 10 | D 10 | Q 8 | I 8 | R 8 | K 5 | L 7 | Integration decision | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | scikit-learn/scikit-learn | 51 | 53 | 3 | 5 | 5 | 2 | 3 | 8 | 8 | 5 | 5 | 7 | INSTALL | none |
| 2 | interpretml/interpret | 50 | 45 | 2 | 8 | 2 | 2 | 3 | 8 | 8 | 5 | 5 | 7 | INSTALL (classification) | RESEARCH_ONLY survival |
| 3 | online-ml/river | 49 | 49 | 5 | 5 | 0 | 3 | 5 | 7 | 8 | 4 | 5 | 7 | ADAPTER (drift) | RESEARCH_ONLY learners; LEAKAGE_FAIL replay model state |
| 4 | statsmodels/statsmodels | 49 | 46 | 3 | 5 | 2 | 2 | 5 | 8 | 8 | 4 | 5 | 7 | INSTALL (Logit, Holm, Wilson) | LEAKAGE_FAIL Markov defaults |
| 5 | eslazarev/purged-cross-validation | 48 | 51 | 9 | 0 | 0 | 3 | 2 | 8 | 8 | 6 | 5 | 7 | ADAPTER (WalkForwardSplit) | none |
| 6 | lightgbm-org/LightGBM | 45 | 42 | 0 | 5 | 2 | 2 | 3 | 8 | 8 | 5 | 5 | 7 | INSTALL | none |
| 7 | unionai-oss/pandera | 44 | 43 | 5 | 0 | 0 | 3 | 2 | 8 | 8 | 6 | 5 | 7 | ADAPTER | none |
| 8 | CamDavidsonPilon/lifelines | 44 | 47 | 2 | 8 | 2 | 0 | 3 | 6 | 7 | 4 | 5 | 7 | ADAPTER | none |
| 9 | scikit-learn-contrib/MAPIE | 44 | 39 | 0 | 0 | 7 | 0 | 6 | 7 | 8 | 4 | 5 | 7 | ADAPTER | none |
| 10 | soda-inria/hazardous | 43 | 41 | 2 | 8 | 4 | 2 | 0 | 7 | 7 | 4 | 4 | 5 | ISOLATED_RESEARCH | REJECT PyPI 0.2.0 artifacts |

Next rows: 11 `sktime/sktime` 41 and 12 `probabl-ai/skore` 41 (tie broken by temporal 3 versus 3, outcomes 2 versus 0), then crepes, stumpy, venn-abers and arch at 40. The full order is in SCORECARD.csv.

## What changed in the repair pass

| Repository | First pass | Final | Change and evidence |
|---|---|---|---|
| scikit-learn-contrib/MAPIE | 49 (5th) | 44 (9th) | O1 -5: its only probability output is the Venn-Abers port that fails the definition (MA-1; the lead's rerun MA-4 gives p1 0.5 where the definition gives 1.0), so the verified-finding veto now covers O1 as it already covered C2 (skeptic M2). D1 stays 3 but now rests on MAPIE's own `BinaryRisk` custom per-row risk consumed by its controller (MA-5), not on `sample_weight` passed through to the wrapped estimator (pass-through rule, the same rule that leaves crepes at 0, CR-3). New finding: a fitted Pipeline passed with `cv="prefit"` has its transformers refit on the calibration rows, changing the caller's predictions by up to 0.0176 (MA-4, found by the blind rescorer) |
| eslazarev/purged-cross-validation | 50 (2nd) | 48 (5th) | O5 -2: `PurgedGroupKFold` by mint has training folds of 0, 0, 45, 179 and 397 rows on the challenge (PC-3, skeptic M3). Temporal points now rest on `WalkForwardSplit` only, whose folds train on 1,403 to 2,522 earlier rows with 0 rows decided after the test start. `PurgedKFold` and CPCV report 0 overlaps but train on up to 2,091 and 1,739 later rows, so they are for labelled sensitivity or PBO only, never for a model used in replay |
| soda-inria/hazardous | 48 (6th) | 43 (10th) | O3 -2: the cumulative incidence decreases in time for 634 of 634 rows (HZ-2), so the competing-risk race output fails its definition (veto, skeptic m4). C2 -3: `recalibrate_survival_function` subtracts the absolute calibration error, so it moves survival away from the Kaplan-Meier curve when the model under-states survival, and its output leaves [0, 1] (to -0.27) in the mirror case (HZ-3, lead probe) |
| sktime/sktime | 46 (8th) | 41 (11th) | O1 -5: its own panel classifiers raised on the unequal-length panel; the only probabilities came from `DummyClassifier(prior)` (one constant) and from scikit-learn's LogisticRegression inside `SklearnClassifierPipeline` (ST-4). Wrapper rule: probabilities of a wrapped third-party estimator do not count (the same rule that leaves crepes at 0; skeptic m5). O5 now rests on the 289-instance panel model, not on `InstanceSplitter`, which trains on up to 1,966 later rows (ST-3) |
| interpretml/interpret | 48 (7th) | 50 (2nd) | C5 +2: the review's "has_term_standard_deviations false" probed a wrong attribute name; the pinned EBM sets `standard_deviations_`, one finite array per term (IN-5, lead rerun after the blind rescorer's correction) |
| online-ml/river | 49 | 49 | no point change; new scoped flag LEAKAGE_FAIL for model state after a `simulate_qa` or `progressive_val_score` replay, because the end-of-stream flush of unmatured answers is learned (qa.py:244, progressive_validation.py:138-155; RV-4, blind rescore). L2 now rests on the lead's crate check: the 34 Rust crates in the normal closure are permissive (RV-5) |

Evidence strings were also tightened without changing points: 35 cells now quote a token found in the raw file they cite, generic items cite the lead's generic checks, and five cells that rested on review prose for items that need raw output now cite the raw file (PI-D-029).

## Role, decisive evidence and limits of each entry

1. **scikit-learn** (`59106029`). Role: baseline B2 (logistic regression), Platt calibration of the 100-point score and of any later model fitted on a training window and calibrated on a later one (FrozenEstimator, `method="sigmoid"`), Brier and log loss. Evidence: `TimeSeriesSplit` trains only on earlier rows (min 483, SK-7) but purges by rows, leaving up to 110 training labels that mature after the test start (SK-2, SK-7); sigmoid calibration on the later window ran (SK-4); identical metrics across two runs (SK-3). Limits: no availability concept (S1 trap BSS 0.0104 to 0.9494), default `CalibratedClassifierCV(cv=None)` is not temporal, pickle only.
2. **interpret** (`d82ea62a`). Role: glassbox comparator in Phase 08 (a leak shows up as the top term), per-term spread across bags as a transparency check; survival research once `survival_cox` is released. Evidence: pin Cox fit kept 107 censored rows censored, Harrell C 0.6749 above the permutation range (IN-1, IN-2); release and pin give identical probabilities and JSON export (IN-3); `standard_deviations_` finite for every term (IN-5). Limits: no calibration method; survival objective unreleased; libebm compiles an Apache-2.0 file whose notice must travel with any redistribution (LICENSE_AND_SECURITY_GATE.md).
3. **river** (`b674b758`). Role: Phase 19 drift detectors (ADWIN, PageHinkley) behind a NaN-refusing wrapper, and the delayed question-and-answer pattern reimplemented for matured-label replays. Evidence: lead rerun, 0 answers released before maturity during the stream (RV-1); the end-of-stream flush of 108 unmatured answers is learned by `progressive_val_score` (RV-2, RV-4). Limits: LEAKAGE_FAIL for any model state kept after such a replay; NaN silently corrupts weights (RV-3); online learners miscalibrated here.
4. **statsmodels** (`aa61cc14`). Role: Logit cross-check with standard errors, Holm across T1, T1b, T2, Wilson intervals (equal to `alpha_core.wilson` within 9e-6). MarkovRegression only as research with training-window parameters and `filter()`. Evidence: lead rerun, filtered state unchanged when later rows are appended, smoothed state changes by 0.0186 (SM-2); out-of-sample predict raises although documented (SM-1, P42). Limits: LEAKAGE_FAIL for Markov defaults; no recalibration.
5. **purged-cross-validation** (`07692dd8`). Role: `WalkForwardSplit` with `label_matures_at` as the evaluation time for every model trained in Phases 07 to 12 and used in replay; PBO for the experiment ledger. Evidence: 0 overlapping training rows by the lead's interval-union checker (PC-1) and, per fold, 1,403 to 2,522 training rows, 0 decided after the test start and 0 labels maturing after it (PC-3). Limits: no feature availability (trap passes); row-count test blocks; `PurgedKFold` and CPCV train on later rows (sensitivity and PBO only); `PurgedGroupKFold` is unusable on this data shape (empty folds); young project (0.1.x, one maintainer).
6. **LightGBM** (`064a6db1`, tested on the 4.7.0 wheel). Role: the Phase 08 complex-model comparator, trained only through walk-forward folds with `deterministic=True`, text model files. Evidence: native text model sha256 identical across two runs, same-seed trees identical (LG-2); native NaN gives finite probabilities (LG-4). Limits: no time handling, defaults shuffle across time, raw probabilities miscalibrated; 300-row default worse than the base rate.
7. **pandera** (`edb0d8b2`). Role: batch validator for the Phase 05 point-in-time feature table and the Phase 06 label table with registered checks and `strict=True`. Evidence: the lead's registered as-of check refused the 3,000 trap rows and a single 1-second-late row, `strict=True` refused an undeclared column, a check that raises fails closed (PA-1). Limits: the as-of rule is the lab's own code that pandera enforces; it fails closed only when the availability column is non-nullable (pandera's default) or the check handles missing values itself: with `nullable=True` a column check passes a row whose availability time is missing (`../skeptic/p03/skeptic_pandera_nan.out.txt`), so the Phase 05 adapter must declare availability columns non-nullable. Import mutates numpy aliases and two environment variables (PA-2).
8. **lifelines** (`7a8fc34a`). Role: event-time baselines (Cox, Weibull AFT, Aalen-Johansen) for the T1 race, the first event-time model to try in the bake-off. Evidence: censor-aware concordance on 634 rows with 107 censored, identical metrics on pandas 3.0.5 (LL-2). Limits: declares `pandas<3.0` (LL-1, I2 0) so it needs `--no-deps` or an override; `k_fold_cross_validation` shuffles rows (LL-1); competing risks marginal only; last commit more than six months old.
9. **MAPIE** (`f1cc3d07`). Role: offline evaluation only: split conformal coverage checks, Spiegelhalter and KS calibration tests, `BinaryClassificationController` with custom risks for alert thresholds (it abstained on 16 positives, the honest answer). Evidence: MA-2 (LAC 0.90 coverage 0.9184 with 0 of 17 positives covered; controller abstains), MA-5 (custom risk consumed by the controller). Limits: never its Venn-Abers port (MA-1, MA-4) and never a fitted Pipeline with `cv="prefit"` (MA-4); no Brier or log loss function.
10. **hazardous** (`1504934e`, pinned source only). Role: research comparator for the T1 barrier race and for its censor-aware IBS and AJ-calibration metrics. Evidence: competing-risk fit with censored rows kept as censored (HZ-2); lead timing rerun 14.7 s at `n_iter=10` (HZ-T). Limits: cumulative incidence non-monotone for 634 of 634 rows (HZ-2); its recalibration function moves the wrong way and is unclipped (HZ-3); the PyPI 0.2.0 wheel and sdist ship a 213,846,118-byte SEER file and other content absent from the source tree (HZ-1), so that route is REJECT; depends on lifelines with `pandas<3.0`.

## Sensitivity of the cut at ten

`verify/sensitivity.py` (output `verify/sensitivity.json`) recomputes the order under contested readings, under the reviewers' totals and under the blind rescorer's scores for the seven repositories it scored. Seven repositories are in the top ten under every reading: scikit-learn, interpret, river, statsmodels, purged-cross-validation, LightGBM and lifelines. Places 8 to 10 rotate among pandera, MAPIE, hazardous, sktime and crepes:

| Reading | Enters | Leaves |
|---|---|---|
| A: a calibrator's output does not count as an event probability (O1; venn-abers only now) | none | none |
| B: a rule the lab writes and the library enforces does not count as a library mechanism (pandera T3, T4a) | sktime | pandera |
| C: only repeat runs done by the reviewers count for R1 (not the lead's re-runs) | none | none |
| A, B and C together | crepes | pandera |
| G: a wrapped third-party estimator's probabilities count (sktime O1) | sktime | hazardous |
| H: Q2 read strictly, every component of the reviewed role covered by the tests that ran (nine repositories lose Q2; `verify/prose_audit.json`) | sktime | hazardous |
| F: the blind rescorer's totals replace the lead's for its seven repositories | sktime | hazardous |
| D: reviewers' proposed totals | sktime | MAPIE |

The lead keeps the written rules (PI-D-026, PI-D-029) and records the alternatives here rather than choosing the reading that gives a preferred order.

## What the ranking does not say

- No entry has shown memecoin forecast skill; on the challenge most models were within noise of the base rate (17 holdout positives).
- A top-ten place is a role, not an engine: the adoption bundle in CATEGORY_WINNERS.md uses several of these as small tools, several only as designs to reimplement, and keeps time discipline in the lab's own as-of view (no library refused the S1 trap by itself except where the lab declares availability: feast and pandera).
- The challenge's short embargo band cannot inflate a metric through label overlap on this generator (each label depends only on its own row); differences of up to about 0.002 Brier between purged and unpurged fits are sample-size noise (logistic purge 0.0001, placebo up to 0.0004; HistGradientBoosting purge 0.0009, placebo up to 0.0023; `SMOKES/_challenge/NOTE.md`). No point rests on such a metric.
- MiroFish is not in the top ten (8 of 100); its separate section is MIROFISH.md.

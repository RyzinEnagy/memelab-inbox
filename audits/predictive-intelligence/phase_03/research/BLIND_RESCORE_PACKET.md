# Blind rescore packet (Phase 03, for the orchestrator's second reviewer)

The package asks for two reviewers to score the top five independently and for any difference above 10 points to be investigated with evidence, never averaged. This packet gives the second reviewer what is needed to score seven repositories without seeing the lead's scores or order.

## The seven repositories

The lead's top five plus two controls, listed alphabetically by canonical path. Which five are the top five, and their order, are deliberately not stated.

| Repository | Pinned SHA | Review | Smoke folder | Pinned clone (read-only) |
|---|---|---|---|---|
| eslazarev/purged-cross-validation | `07692dd862d37a988233e190706afb18c5101948` | `REVIEWS/eslazarev__purged-cross-validation.md` | `SMOKES/eslazarev__purged-cross-validation/` | `/home/claude/pi_research/src/eslazarev__purged-cross-validation` |
| interpretml/interpret | `d82ea62a0ed4e3969079904a383ca885d2352e63` | `REVIEWS/interpretml__interpret.md` | `SMOKES/interpretml__interpret/` | `/home/claude/pi_research/src/interpretml__interpret` |
| online-ml/river | `b674b758518341bc5c343ca113f34903ba55020a` | `REVIEWS/online-ml__river.md` | `SMOKES/online-ml__river/` | `/home/claude/pi_research/src/online-ml__river` |
| scikit-learn-contrib/MAPIE | `f1cc3d07460b2d7198f557d40d60cd563c51822b` | `REVIEWS/scikit-learn-contrib__MAPIE.md` | `SMOKES/scikit-learn-contrib__MAPIE/` | `/home/claude/pi_research/src/scikit-learn-contrib__MAPIE` |
| scikit-learn/scikit-learn | `59106029d483678e79825f753bde67f8ade4332b` | `REVIEWS/scikit-learn__scikit-learn.md` | `SMOKES/scikit-learn__scikit-learn/` | `/home/claude/pi_research/src/scikit-learn__scikit-learn` |
| soda-inria/hazardous | `1504934e6d886820ca5fcd9e8ccaefd49cc2dd78` | `REVIEWS/soda-inria__hazardous.md` | `SMOKES/soda-inria__hazardous/` | `/home/claude/pi_research/src/soda-inria__hazardous` |
| statsmodels/statsmodels | `aa61cc148b820898247052008652b4dc4bda665e` | `REVIEWS/statsmodels__statsmodels.md` | `SMOKES/statsmodels__statsmodels/` | `/home/claude/pi_research/src/statsmodels__statsmodels` |

Paths in the Review and Smoke columns are relative to `audits/predictive-intelligence/phase_03/research/`. The reviewers' venvs are under `/home/claude/pi_research/venvs/<owner>__<repo>` where they still exist.

## Staying blind

1. Build a working copy outside the repository: `bash audits/predictive-intelligence/phase_03/research/verify/make_blind_copy.sh <target_dir>`. It copies the seven reviews with section 6 (the original reviewer's proposed scores) removed, the seven smoke folders, the synthetic challenge and its note, the lead's verification and re-execution outputs (evidence only, no scores) and the locked rubric.
2. Before you have written your scores, do not open these files in the repository: `research/SCORECARD.csv`, `research/SCORE_ITEMS.csv`, `research/RUBRIC_ITEMS.csv`, `research/RANKED_TOP10.md`, `research/CATEGORY_WINNERS.md`, `research/verify/sensitivity.json`, `research/verify/score_inputs.py`, `research/REVIEW_VERIFICATION.md`, `PHASE_03_EVIDENCE.md`, `PHASE_03_RESULTS.json`, and the Phase 03 entries in `docs/predictive-intelligence/`. `RUBRIC_ITEMS.csv` is the lead's split of each criterion into items; it is withheld so that your reading of the rubric is your own.
3. Treat the reviews as claims. Their section 7 flags and section 8 roles remain; check what matters to you against the pinned source or the raw smoke output.

## The rubric to apply

The locked rubric is the package's `references/GRADING_RUBRIC.md` (copied into the blind working copy). Criteria and maxima: temporal integrity and leakage safeguards 18; transferable measurable predictive outcomes 14; calibration, uncertainty and abstention 12; catalyst, social and on-chain features 10; decision, execution and stress compatibility 10; code quality, maintenance and tests 8; integration fit and extensibility 8; experiment reproducibility and audit 8; cost, latency and operational reliability 5; licensing, security and data rights 7. Total 100.

Rules that bind every score: each criterion is scored 0 to its maximum; every point needs a source or experiment reference (pinned `path:line`, a raw smoke output file and field, or a re-execution you ran); a question without an answer scores 0, never a midpoint; README or documentation text earns nothing (P42); a synthetic-challenge metric is a format check, not skill; the challenge's 14.6 h "embargo" band against 24 h labels could not move any metric (see `SMOKES/_challenge/NOTE.md`) and must not earn or lose points; the needs the tools are judged against are in `audits/predictive-intelligence/phase_01/architecture/` (TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, PLANNED_SEAMS.md, GAP_MATRIX.csv).

## What to return

Write `RESCORE.csv` in your working copy (outside the repository) with one row per repository and the columns `repo, temporal_integrity, transferable_outcomes, calibration_uncertainty, features, decision_execution, code_quality, integration_fit, reproducibility, cost_latency, license_security, total`, and `RESCORE_NOTES.md` with the evidence for each criterion score and any review claim you found false. The lead then folds both into `INDEPENDENT_RESCORE.md`: per repository and criterion, the two scores and the difference; every total difference above 10 points investigated against the evidence and resolved by the evidence (a score changes only when one side cites something the other missed or misread), never by averaging.

## Correction after the rescore (repair pass)

The rule above says the embargo band "could not move any metric". That overstated the lead's evidence, which was one logistic draw (largest difference 0.0001 Brier). The skeptic's placebo test shows that differences up to about 0.002 Brier between purged and unpurged fits are sample-size noise on this generator, and that label overlap cannot inflate a metric because each label depends only on its own row (`SMOKES/_challenge/NOTE.md`). The instruction that the band must not earn or lose points is unchanged, and the blind rescore followed it ("earned and cost nothing"), so the correction does not affect its scores. The text above is left as the rescorer received it.

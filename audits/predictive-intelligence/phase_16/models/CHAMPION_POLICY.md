# Champion policy (registry-1)

Rules: `../ACCEPTANCE_CHECKLIST.md` (rules 1 to 3, 8 to 11) and PI-D-085. Code: `memelab/predictive/registry.py`. Registry: `../registry/`. Research only; no number here is a trading signal.

## The state today, in one paragraph

There is no champion for any target. Every primary target (T1 24 h, T1b 6 h, T2 24 h) is pinned NO_VIABLE_CHAMPION: every request abstains and every document shows model `not_selected`. B0 (training prevalence) and B2 (the simple logistic baseline) are pinned beside each target as references for the prospective comparison of Phase 19. They are not forecasts, they are never published as a probability, and B2 is not a champion: Phase 12 named it champion only by default, because no candidate earned `champion_over_B2` on development data, not because it showed skill. No frozen model shows out-of-sample value over the training base rate, none survives the selection correction, none is calibrated, and no ensemble is used.

## Why each target is NO_VIABLE_CHAMPION

| Target | Phase 12 first opening, B2 against B0 | Phase 13 calibration | B2 level and reasons |
|---|---|---|---|
| T1 24 h | 66 events, 15 positive, BSS -0.024 (governing mint interval -0.156 to +0.134), NOT_DISTINGUISHABLE_FROM_BASE_RATE; calibration bins passed | UNCALIBRATED: 24 calibration rows, 8 positive, 3 days against 100, 20, 5 | ABSTAIN: RETROSPECTIVE_BSS_BELOW_0, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |
| T1b 6 h | 68 events, 12 positive, BSS -0.083 (day interval -0.174 to -0.020, governing mint interval to +0.002), NOT_DISTINGUISHABLE_FROM_BASE_RATE; calibration in the large failed (mean 0.082 against 0.176) | UNCALIBRATED: 44 rows, 3 positive, 5 days | ABSTAIN: RETROSPECTIVE_CALIBRATION_FAILED, RETROSPECTIVE_BSS_BELOW_0, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |
| T2 24 h | 59 events, 7 positive: INSUFFICIENT_EVENTS (minimum 10 per class); the BSS point +0.292 is not evidence of skill (interval to -0.026, Holm p 0.1003 on the primary family (the entry's facts read the PRIMARY_HOLDOUT row since CP16-2; before it they had kept the secondary row's 1.0), possible partial T2 contact PI-D-045) | UNCALIBRATED: 8 rows, 1 positive, 1 day | ABSTAIN: RETROSPECTIVE_BELOW_MINIMUM, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |

The other 63 entries per the three targets (B1, B3, B3F, B4, the tech-1, onchain-1, socialcat-1 and analog-1 cards) are NO_GO with NO_INCREMENTAL_PREDICTIVE_EDGE: none reaches the SHADOW criteria on the first-opening evaluation, none has a calibration card, none survives the selection correction (Phase 12: 116 rows NO_UNCORRECTED_SKILL, 13 FAILS_SELECTION_CORRECTION, 0 survive; the smallest max-T p against B2 is 0.638). Six tech-1 cards are not fitted (INSUFFICIENT_HISTORY) and three have no holdout evaluation (no candles under the Phase 05 seal).

## The rule

1. Candidates are the 69 frozen holdout-start cards, as committed (file sha256 and model sha checked through each family's loader); nothing is refit or tuned here.
2. The Phase 12 development rule (B2 unless a candidate earned `champion_over_B2` on development data) is restated from `CANDIDATES.json` and checked against `evaluation.champion` on the committed development rows. The registry's `select_champion` refuses any row with a holdout or post-opening marker: the opened holdout never chooses.
3. A level is computed from an entry's facts by `promotion_decision`, never given:
   - SHADOW: leakage, provenance and contract tests pass; training counts at the minimums (100 events, 20 per class); a FIRST_OPENING retrospective evaluation with at least 50 events and 10 per class, calibration in the large and in every bin passed and BSS point at least 0 (frozen ACCEPTANCE); and a CALIBRATED calibration card of the same model on admissible prospective evidence (at least 50 events and 10 per class, not the fit set), because the opened retrospective holdout can no longer support a promotion on its own (PI-D-065, PI-D-069). A POST_OPENING fact can only block.
   - VALIDATED_EXPERIMENTAL: SHADOW plus a BSS lower 95% bound above 0 after Holm on the retrospective and on the prospective holdout (at least 50 events), Brier not worse than B2, selection status SURVIVES_SELECTION_CORRECTION over the cumulative search (N_search 130, 169 in the sensitivity count); a model other than B2 also needs the lower bound of its improvement over B2 above 0.
   - Otherwise ABSTAIN for B0 and B2 (references) and NO_GO for every other candidate.
4. A target's deployed mode is CHAMPION only for an entry at SHADOW or VALIDATED_EXPERIMENTAL; otherwise NO_VIABLE_CHAMPION with the two references. A pin of a lower entry is refused when it is written and when it is resolved.
5. A champion is pinned and used only after the registry itself rebuilds its facts from the committed Phase 12 and 13 files and finds them equal (`check_facts`, run inside `pin_event`, `rollback_event` and `serve`; CP16-2, no caller-supplied verifier), its recorded code files are unchanged, the caller's recomputed inference rows give its pinned hash, and `serve` finds no other blocking state (below); a champion that fails is rolled back.
6. Probabilities come only from promoted, calibrated models through `abstention.forecast_result` and `validate_publication`; with NO_VIABLE_CHAMPION the document is ABSTAIN with MODEL_NOT_SELECTED. A backtest reference appears only when backtesting is VERIFIED (today BACKTEST_NOT_AVAILABLE). Behavioral scenarios stay in their own list, empty while MIROFISH_NO_GO.

## Target selection per opportunity

| Opportunity | Outcomes attempted | What happens |
|---|---|---|
| Solana decision, point-in-time pool | T1 24 h, T1b 6 h, T2 24 h | each gets a document; today every one is ABSTAIN (MODEL_NOT_SELECTED plus abstention-1's conditions: FLAG_OFF, UNCALIBRATED, INSUFFICIENT_HISTORY, and missing inputs or route as they apply) |
| Solana decision on the CURRENT_VENDOR_LIST route | the same three | ABSTAIN with POOL_NOT_POINT_IN_TIME (TARGET_NOT_FEASIBLE) as well |
| Any decision, BLOCKED, DEFERRED or EXPLORATORY targets (exit-adjusted, liquidity degradation, failed breakout, catalyst follow-through, distribution, 7 d, launch-cohort collapse) | none | TARGET_NOT_FEASIBLE, listed, never attempted |
| EVM or other chains | the three are attempted and abstain | OUT_OF_SCOPE_CHAIN |
| A position size is asked | the three | ABSTAIN with EXECUTION_DATA_MISSING (no historical executable depth) |

## Model states and thresholds

| State | Threshold | Effect | Retrain requirement |
|---|---|---|---|
| RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF | decision before the training cutoff | not used (P13) | none: use a model trained by then |
| MODEL_STALE | decision more than 1,209,600 s (14 days) after the cutoff; for every frozen card, after 2026-10-31T00:00:00Z | not used; rollback | RETRAIN_PLAN_REQUIRED: a new frozen card from a plan committed before its evaluation data are read |
| DRIFT_ALERT | a Page-Hinkley alarm (delta 0.005, threshold 2.0, at least 30 observations, increase only, on matured champion Brier loss minus B0 loss) at or before the decision | not used; rollback; earlier records kept (P39) | RETRAIN_AND_HUMAN_REVIEW |
| MODEL_NOT_PROMOTED | level not SHADOW or VALIDATED_EXPERIMENTAL | never published | none until the promotion evidence exists |
| OUT_OF_DISTRIBUTION | per request: MISSING_REQUIRED_INPUT, FEATURE_OUT_OF_RANGE (standardised input beyond 4), SCORE_OUTSIDE_CALIBRATION_RANGE (abstention-1, contract reason OOD) | that request abstains | none |
| FEATURE_SCHEMA_MISMATCH | the request's feature set sha or version differs from the model's | that request abstains | recompute the inputs or retrain |
| MODEL_INCOMPATIBLE_RETRAIN_REQUIRED | the running code's feature set, family version, target registry or labels version differs from the entry's | not used; rollback | RETRAIN_REQUIRED_BEFORE_ANY_USE |
| INFERENCE_MISMATCH | the recomputed identical-inference hash differs from the pinned one | not used; rollback | ROLLBACK_AND_INVESTIGATE |
| INFERENCE_NOT_CHECKED | `serve` was given no recomputed inference rows | that request abstains | recompute the probe outputs |
| MODEL_INCOMPATIBLE_RETRAIN_REQUIRED (code) | a recorded code file (features, baselines, stats, contract, labels, family module) changed, even without a version bump | not used; rollback | retrain or re-register after review |
| FIXTURE_IN_REAL_REGISTRY | a fixture champion outside a fixture run | not used | ROLLBACK_AND_INVESTIGATE |
| FACTS_NOT_VERIFIED, FACTS_MISMATCH | `serve` was given no repository root, or the registry's own rebuild of the facts from the committed files differs | not used; rollback | ROLLBACK_AND_INVESTIGATE |

Retraining is never automatic: no scheduled job is approved (PI-D-005). A retrained card is a new entry that starts at ABSTAIN and inherits no level.

## Rollback

On DRIFT_ALERT, INFERENCE_MISMATCH, MODEL_INCOMPATIBLE_RETRAIN_REQUIRED or a refused entry, `rollback_event` appends a ROLLBACK that pins the most recent earlier champion that is still usable and was not itself rolled back, else NO_VIABLE_CHAMPION with the references. Earlier events are never touched; resolving a decision before the rollback still gives the pin then in force. Shown on fixtures (`../evidence/ROLLBACK_TEST.json`: a fixture model at VALIDATED_EXPERIMENTAL rolled back on drift to the fixture B2 baseline at SHADOW, then on an inference mismatch to NO_VIABLE_CHAMPION; history preserved) and on a temporary copy of the real log (each target stays NO_VIABLE_CHAMPION). The fixture branch is TEST_ONLY: no real entry can be pinned as a champion today.

## Ensembles

NO_ENSEMBLE for every target (`ENSEMBLE_ABLATION.md`): nothing beats the base rate, the development out-of-fold rows are too few for any verdict, the chronological stack never clears its training gate, and two configurations that would count the lab's fatal flags twice are refused.

## What would change the state, and what cannot

- The frozen promotion table asks for a FIRST_OPENING retrospective evaluation. The retrospective holdout (2026-10-17 to 2026-10-24) is spent: a model with a later cutoff has that window inside its training data, and a model that keeps the 2026-10-17 cutoff meets the same spent evaluation, so under the frozen table no model can reach SHADOW or VALIDATED_EXPERIMENTAL. Orchestrator decision (PI-D-091): no change to ACCEPTANCE now; changing the table is Elving's decision, and the honest route is the prospective holdout of Phase 19 (an untouched prospective window in place of the spent retrospective one, registered before any prospective label is read, with the rest of the SHADOW conjunction kept).
- Even then a promotion needs admissible prospective evidence: at least 50 matured events and 10 per class per target, not the fit set (Phase 19), a CALIBRATED card, and for VALIDATED_EXPERIMENTAL the selection correction over the whole search.
- `calibration.verify_card` keeps refusing a self-given VALIDATED_EXPERIMENTAL card. The change control that lifts it must make it depend on a registry entry whose recomputed level is VALIDATED_EXPERIMENTAL.
- The frozen cards are MODEL_STALE for decisions after 2026-10-31T00:00:00Z, so Phase 19's prospective comparison of the references needs retrained reference cards (a new plan) for decisions after that date.
- No level ever implies a trading edge: every target is price-path only, with no historical executable depth (NO_NET_TRADING_EDGE_CLAIMABLE).

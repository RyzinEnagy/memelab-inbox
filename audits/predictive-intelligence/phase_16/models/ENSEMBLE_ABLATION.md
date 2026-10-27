# Ensemble ablation and decision (Phase 16)

Rule: `../ACCEPTANCE_CHECKLIST.md` rule 12 (registered before any computation). Outputs: `../ensemble/ENSEMBLE_ABLATION.json` and `.csv`, `../ensemble/STABILITY.json`, `../ensemble/LATENCY.json`, `../ensemble/POST_OPENING_LOG.json`. Recorded run at the frozen code `d2038a7`, repeated at the CP16-0 code `8cd19bd` (every number and decision equal).

## Decision: NO_ENSEMBLE for all three targets

Nothing beats the base rate (Phase 12: no frozen card survives the selection correction; B2 is not distinguishable from B0), the chronological out-of-fold rows are too few for any verdict, the stack never clears its training gate, and the two configurations that would have combined on-chain or social models with B2 count the lab's fatal flags twice and are refused. An ensemble of models without skill would add parameters, inference cost and a second source of instability without evidence of value.

## What was tried (9 configurations, counted in N_search; 9 traps, not configurations)

| Configuration | Members | Rule | Development out of fold (vs B0, vs B2) |
|---|---|---|---|
| ENS_MEAN_B0_B2 | B0, B2 | equal-weight mean; B0 reads no input | T1 24 rows, 8 positive, 3 days: INSUFFICIENT_DAYS both; T1b 44, 3, 5 days: INSUFFICIENT_EVENTS both; T2 8, 1, 1 day: INSUFFICIENT_DAYS both |
| ENS_MEAN_B2_S1 | B2, S1_SC_LOGIT | equal-weight mean; S1 reads the lab's attention proxies only | T1 13 rows with both, 4 positive, 2 days: INSUFFICIENT_DAYS; T1b 37, 3, 5 days: INSUFFICIENT_EVENTS; T2 0 rows (S1 abstains on every T2 row): INSUFFICIENT_HISTORY |
| STACK_CHRONO_B2_S1 | B2, S1 logits | logistic stack fitted on earlier folds' out-of-fold rows; gate 100 events, 20 per class, 5 days | never fitted: at most 33 fit rows with 3 positives over 4 days (T1b, last fold); INSUFFICIENT_HISTORY on every target |

Every member number is a committed out-of-fold number (Phase 07 and Phase 10 `OOS_PREDICTIONS.csv`), from the fold card trained at the row's fold cutoff and decided after it; every label was checked against `labels.training_labels` on the development store. A member that abstains makes the ensemble abstain (no partial mean). The frozen `baselines.evaluate` and `verdict` were used, Holm across the three targets; below 5 decision days or the out-of-sample minimums (50 events, 10 per class) no direction is stated.

## Traps (each must be refused, each was)

| Trap | Refused with |
|---|---|
| ENS_MEAN_B2_M1_S1 | DOUBLE_COUNTED_EVIDENCE: B2's `thesis_fatal_present` and M1's `oc_structural_fatal`, `oc_distribution_fatal` all read the lab's fatal flags |
| ENS_MEAN_B2_M2_S2 | DOUBLE_COUNTED_EVIDENCE: M2 and S2 each contain all of B2's inputs |
| STACK_IN_SAMPLE | IN_SAMPLE_STACKING: the stack fitted on the rows it is scored on |

## Opened holdout, POST_OPENING description only

Computed from the committed `phase_12/validation/HOLDOUT_SCORED.csv` (no sealed file read), logged, never a choice and never a claim; it can only make a statement more conservative.

| Target | ENS_MEAN_B0_B2 vs B0 | vs B2 | ENS_MEAN_B2_S1 vs B0 | vs B2 |
|---|---|---|---|---|
| T1 24 h | 66 events, BSS +0.010, NOT_DISTINGUISHABLE | +0.033, NOT_DISTINGUISHABLE | 56, +0.016, NOT_DISTINGUISHABLE | +0.051, NOT_DISTINGUISHABLE |
| T1b 6 h | 68, -0.030, NOT_DISTINGUISHABLE | +0.049, NOT_DISTINGUISHABLE | 57, -0.051, NOT_DISTINGUISHABLE | +0.014, NOT_DISTINGUISHABLE |
| T2 24 h | 59, 7 positive, INSUFFICIENT_EVENTS | INSUFFICIENT_EVENTS | 52, 7 positive, INSUFFICIENT_EVENTS | INSUFFICIENT_EVENTS |

The mean of B0 and B2 sits between its two members, as any average with the base rate does; no interval excludes 0, and a pattern found after the opening is not evidence.

## Complexity, cost, latency, stability

| Item | ENS_MEAN_B0_B2 | ENS_MEAN_B2_S1 | STACK_CHRONO_B2_S1 |
|---|---|---|---|
| Members | 2 | 2 | 2 |
| Parameters (members + extra) | 7 + 0 | 13 + 0 | 13 + 3 (not fitted) |
| CPU per decision, sum of members (descriptive, this machine) | about 14 to 15 microseconds | about 18 to 19 microseconds | not fitted |
| External calls, spend | 0 | 0 | 0 |

The analog cards cost about 0.7 to 1.5 ms per decision and the logistic and rule cards about 4 to 21 microseconds (`LATENCY.json`, machine dependent). Stability of the members (`STABILITY.json`, fold cards against the frozen card on the 176 holdout decisions' inputs): T1 B2 numbers move by up to 0.43 (median 0.02 to 0.04) between training cutoffs one to four days apart (104 to 123 training rows); T1b B2 up to 0.08 (median 0.003 to 0.009); T1 S1 up to 0.19; T1b S1 up to 0.04. With so few training days, the simplest models are themselves unstable on T1, so a more complex combination has nothing stable to build on.

## Limitations

- The evidence-source map rests on the column definitions in the family modules. The lab's derived classifiers (lifecycle, manipulation screen, narrative strength) may themselves read market data; the map treats them as distinct sources from the thesis market row, which is an assumption.
- In the first recorded run (`9eebb8d`) CPU-time fields were also copied into `ENSEMBLE_ABLATION.json`; CP16-0 (PI-D-086) moved them to `LATENCY.json` only, so the ablation file now repeats byte for byte (`../evidence/rerun_cp16_0_diff.json`).
- Analog and tech-1 cards were not ensemble members: analog numbers are cohort estimates that Phase 11 said are never a probability, and tech-1 has no holdout inputs and few development rows.

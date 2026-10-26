# Final retrospective holdout results (Phase 12)

Updated in repair pass 2 (PI-D-066): the selection-correction text, the corrected ledger, the post-opening computations and the honour-based seal; no number or verdict changed.

The sealed retrospective holdout (decisions 2026-10-17T00:00Z to 2026-10-24T00:00Z) was opened once, at 2026-10-26T17:33:27Z from commit `d58de61`, after the plan (`79d30f5`), the frozen code (`3ea7030`) and every holdout prediction (`d58de61`) were committed, and after `check_seal.py` reported no problem with the three pinned hashes (`OPENING_LOG.json`). Every number below comes from the frozen cards trained at 2026-10-17T00:00Z; nothing was refitted, tuned or selected after the labels were read. Tables are copied from `PRIMARY_RESULTS.json`, `HOLDOUT_METRICS.csv`, `SENSITIVITY.csv`, `SHIFT_BREAKDOWN.csv`, `HOLDOUT_NEGATIVE_CONTROLS.json` and `HOLDOUT_COUNTS.json` (rounded here; full precision in the files). The prospective holdout (from 2026-10-24) was not read.

These are price-path targets: no fill, size, depth or proceeds is implied, and no statement here is a trading signal (PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, BACKTEST_NOT_AVAILABLE).

## Empirical validity: what the data supports

1. No frozen model is distinguishable from the training base rate on the retrospective holdout. The champion (B2, chosen by the development rule because no candidate earned anything on development data) has a negative Brier skill point estimate on T1 and T1b, and T2 does not reach the frozen minimum of 10 positive events.
2. On T1b the champion is borderline worse than the base rate: the day interval lies entirely below 0 and only the wider (governing) mint interval reaches +0.002; with the contacted decision included, or on the point-in-time route alone, the same code returns WORSE_THAN_BASE_RATE. Its probabilities are miscalibrated in the large (mean 0.082 against an observed 0.176).
3. T2's positive point estimate (+0.29) rests on 7 positive events on 6 days and mostly reflects a lower holdout prevalence (0.119) than the training prevalence B0 carries (0.214). It is INSUFFICIENT_EVENTS, it is not a claim, and it carries the PI-D-045 item 6 note (possible partial contact with the T2 holdout through first-pass public call counts; nobody computed the bound).
4. Shuffled-label controls trained on the same rows score as well as the real champion in 45% (T1) and 85% (T1b) of seeds: the champion's inputs carry no detectable information on this holdout.
5. Of the 63 fitted frozen cards (54 card and target pairs with numbers against B0, 51 against B2), none shows skill after the selection correction. The recorded run computed the max-T correction against B0 only; the max-T against B2 was computed after the opening (POST_OPENING, repair pass 2, PI-D-066; smallest p 0.638), so this now holds for the comparisons against B2 too. One descriptive pattern is recorded below (T1, the lab-status prevalence B1 against B0); it fails the max-T correction and is therefore not even a hypothesis under the frozen rule.
6. Consequence (phase prompt step 5, NO_GO_DECISION_TREE "complex model underperforms"): prefer the base rate or abstention; every complex model stays MODEL_NOT_PROMOTED; nothing reaches SHADOW (Phase 12 promotes nothing, and the champion fails the SHADOW criteria on every target: negative skill on T1 and T1b, the count gate on T2, calibration on T1b). The prospective holdout (Phase 19) is the only remaining out-of-sample test, and the expected outcome stated in Phase 01 ("not distinguishable from the base rate, or insufficient") is what happened.

## Primary family: champion B2 against B0 (Holm across the three targets)

| Target | N (positives) | Days, mints | Holdout prevalence (Wilson 95%) | Training prevalence (B0) | Brier B2 / B0 | BSS | Day interval | Mint interval | Governing | p one-sided | Holm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 24 h | 66 (15) | 7, 57 | 0.227 (0.143 to 0.342) | 0.250 | 0.1804 / 0.1761 | -0.024 | -0.159 to 0.080 | -0.156 to 0.134 | mint | 0.627 | 1.000 | NOT_DISTINGUISHABLE_FROM_BASE_RATE |
| T1b 6 h | 68 (12) | 7, 57 | 0.176 (0.104 to 0.284) | 0.116 | 0.1614 / 0.1490 | -0.083 | -0.174 to -0.020 | -0.168 to 0.002 | mint | 0.972 | 1.000 | NOT_DISTINGUISHABLE_FROM_BASE_RATE |
| T2 24 h | 59 (7) | 6, 52 | 0.119 (0.059 to 0.225) | 0.214 | 0.0804 / 0.1136 | +0.292 | -0.026 to 0.674 | -0.002 to 0.571 | day | 0.033 | 0.100 | INSUFFICIENT_EVENTS (7 < 10 positives) |

Bootstrap: 20,000 replicates of whole days and of whole mints, seed 20261025, percentile 95%, the wider governs (protocol 5). Coverage: B2 had every input for every scored decision (66 of 66, 68 of 68, 59 of 59). Creator-group intervals (P14, beside, not governing): T1 -0.158 to 0.134, T1b -0.164 to -0.001, T2 -0.007 to 0.580.

| Target | Log loss B2 / B0 | ROC AUC | Average precision (AUCPR) | Calibration in the large (mean pred, observed, Wilson) | Quantile bins (n, positives, mean pred, observed, ok) | ECE (descriptive) |
|---|---|---|---|---|---|---|
| T1 24 h | 0.563 / 0.537 | 0.550 | 0.309 | ok (0.193, 0.227, 0.143 to 0.342) | (22, 3, 0.087, 0.136, ok); (22, 7, 0.179, 0.318, ok); (22, 5, 0.313, 0.227, ok) | 0.092 |
| T1b 6 h | 0.578 / 0.482 | 0.518 | 0.203 | FAILED (0.082, 0.176, 0.104 to 0.284) | (23, 3, 0.023, 0.130, fail); (23, 5, 0.060, 0.217, fail); (22, 4, 0.168, 0.182, ok) | 0.094 |
| T2 24 h | 0.262 / 0.395 | not defined (fewer than 10 positives) | not defined | ok (0.119, 0.119, 0.059 to 0.225) | (30, 1, 0.009, 0.033, ok); (29, 6, 0.233, 0.207, ok) | 0.025 |

What was not scored, by target (`HOLDOUT_COUNTS.json`; 176 holdout decisions per target, 95 Solana): T1 81 OUT_OF_SCOPE_CHAIN, 9 NO_SNAPSHOT_PRICE, 12 MARKET_INACTIVE, 5 VENDOR_OR_ROUTE_GAP (censored), 2 THINNED, 1 labelled contacted decision excluded; T1b the same except 0 thinned; T2 also 7 PENDING at the Phase 06 read (never scored, P05). Of the two contacted decisions, one is labelled for each target and was excluded; the other has no label.

## Sensitivities (champion against B0; descriptive, outside the Holm family)

| View | T1 24 h | T1b 6 h | T2 24 h |
|---|---|---|---|
| Contacted decision included | 67 (16), -0.025, NOT_DISTINGUISHABLE | 69 (13), -0.096, WORSE_THAN_BASE_RATE | 60 (7), +0.297, INSUFFICIENT_EVENTS |
| Without KEY_CONFLICT decisions | 66 (15), -0.024, NOT_DISTINGUISHABLE (no KEY_CONFLICT decision in the holdout) | 68 (12), -0.083, NOT_DISTINGUISHABLE | 59 (7), +0.292, INSUFFICIENT_EVENTS |
| New mints only (absent from training labels) | 38 (11), -0.091, INSUFFICIENT_EVENTS | 37 (9), -0.139, INSUFFICIENT_EVENTS | 33 (5), +0.209, INSUFFICIENT_EVENTS |
| New creators only | 29 (7), -0.177, INSUFFICIENT_EVENTS | 28 (6), -0.150, INSUFFICIENT_EVENTS | 25 (5), +0.193, INSUFFICIENT_EVENTS |
| Point-in-time route only | 54 (15), -0.080, NOT_DISTINGUISHABLE | 54 (11), -0.089, WORSE_THAN_BASE_RATE | 48 (7), +0.235, INSUFFICIENT_EVENTS |
| Conservative lens (censored counted T1 and T1b negative, T2 positive) | 70 (15), -0.018, NOT_DISTINGUISHABLE | 72 (12), -0.082, NOT_DISTINGUISHABLE | 63 (11), +0.139, NOT_DISTINGUISHABLE |

## Dataset shift (P21; frozen verdict code per cohort)

- Prior shift: the training prevalence lies inside the holdout's Wilson interval on every target (T1 0.250 in 0.143 to 0.342; T1b 0.116 in 0.104 to 0.284; T2 0.214 in 0.059 to 0.225, close to the edge).
- Every cohort of every breakdown (decision day, launch month, pool type, route, liquidity bucket, launch-age bucket) is INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS, except the point-in-time route above. No cohort supports a claim.
- Regime and crash days cannot be tested on this holdout: every holdout decision carries the as-of regime label QUIET/RISK_OFF (a lab-universe proxy, PI-D-063 m2) and no decision day is a CRASH_DAY_AS_OF day (median change since the prior lab decision never below log 0.5). Whether a model holds in another regime is unknown.

## Secondary family and the selection correction (P22)

- 129 secondary comparisons (every fitted card other than B0 against B0, every fitted card other than B0 and B2 against B2; 24 rows are cards with no number on the holdout: the six Phase 08 cards that abstain at H, the three fitted Phase 08 T1b cards, whose tech-1 inputs do not exist for holdout decisions (62 NOT_FETCHED_SEALED, 33 NO_POOL_AT_DECISION), and AC1_STRATA, which abstains on every decision).
- 17 of 129 have an uncorrected one-sided p below 0.05; after Holm over the 129, one row stays below 0.05; after the max-T day-block correction, none; after the full-search Bonferroni (N_search 118), one. The frozen rule needs all three. In the recorded run the max-T existed only for the 66 rows against B0 (54 with numbers), so the 63 rows against B2 (51 with numbers) could not have passed whatever the data (skeptic CX-S12); the max-T against B2, computed POST_OPENING, gives a smallest p of 0.638. With it every secondary row has all three corrections: 13 FAIL (every row with an uncorrected skill verdict), 116 have no uncorrected skill, 0 survive (`POST_OPENING_CORRECTIONS.csv`). The `verdict` column of the secondary rows in `HOLDOUT_METRICS.csv` and `FULL_EXPERIMENT_LEDGER.csv` applies the Holm adjustment only and is not a claim; `FULL_EXPERIMENT_LEDGER_CORRECTED.csv` carries `selection_status` and `claim` beside it.
- The one row that passes Holm and Bonferroni: T1, B1 (training prevalence by lab status group, shrunk to B0) against B0, 66 events, BSS +0.016 (day interval 0.012 to 0.021, mint 0.008 to 0.022), p 0.0002, Holm 0.032, Bonferroni 0.029 (0.032 with the 9 rule configurations added, N 127, POST_OPENING), max-T 0.991. Recorded as a descriptive pattern only: the improvement is small, the day interval rests on 7 day groups, and the pre-registered max-T fails. Under the frozen rule it is not a hypothesis and it cannot become the champion now.
- On T1b, nine cards (B1, B3, B3F, B4, onchain M1 and R1, socialcat R2, analog AC2 and AC3) have lower Brier than B2 with an uncorrected p below 0.05 against B2, consistent with B2's poor calibration there; none passes Holm (smallest 0.147) or the post-opening max-T against B2 (smallest 0.638), and none is distinguishable from B0 after correction.
- No secondary comparison is WORSE_THAN_BASE_RATE before correction; T2 rows are all INSUFFICIENT_EVENTS.

## Negative controls and traps

| Control | Result |
|---|---|
| NC1, B2 refitted on development labels shuffled inside training (20 seeds), scored on the holdout | T1 mean BSS -0.056, NC1_DEGRADES_OR_EQUAL, 45% of seeds above the real champion; T1b -0.022, NC1_DEGRADES_OR_EQUAL, 85%; T2 -0.023, INSUFFICIENT_EVENTS |
| NC2, one input available 1 s after the decision (B2, onchain M2, socialcat S2, analog AC3, tech-1 M2; 95 decisions per family and target) | 1,425 of 1,425 refused; a column outside each family allowlist refused 15 of 15 |
| NC3, same-ticker join on the real scored rows | 8, 8 and 6 same-symbol rows tried, all refused (IdentityJoinError) |
| P13, every holdout-start card on development decisions; a cutoff moved after a holdout decision; a training label maturing after the cutoff | 69 of 69, 69 of 69 raise RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF; 69 of 69 refused (TRAINING_LABEL_AFTER_CUTOFF) |
| B2 refitted at H through the training gate | equal to the frozen B2 card on all three targets |

## Engineering validation (separate from the empirical result)

- Protected holdout: one FIRST_OPENING entry in `OPENING_LOG.json` (time, HEAD `d58de61`, the three seal hashes, the label file sha256 read, the prediction manifest sha256, the output hashes); predictions fixed and committed before the opening and checked against `PREOPEN_MANIFEST.json` by the opener and by `tests/test_predictive_phase12_outputs.py`.
- Exact reproducibility: a REPRODUCTION of the opening run (17:47:58Z to 17:58:41Z) wrote ten output files byte-equal to the recorded ones; two `predict` runs byte-equal; an independent check without `memelab` (`probes/independent_label_check.py`) finds the same scored rows and labels (66, 68, 59; 15, 12, 7 positive; 0 mismatches); scikit-learn 1.9.1 recomputes 572 Brier, log loss, AUC and AP values within 1.1e-16.
- No future-trained replay: `REPLAY_AUDIT.json`, 0 violations over the 380 development out-of-sample rows of Phases 07 to 11 and the 12,255 holdout prediction rows (cutoff 2026-10-17T00:00Z, at most 6.43 days before any decision, never MODEL_STALE).

## Limitations

- 7 decision days, one export batch per day: the day bootstrap resamples 7 groups; intervals are approximate and the "day interval entirely below 0" on T1b rests on 7 groups.
- The technical (tech-1) family could not be evaluated: no holdout candle was read under the Phase 05 seal and no new read was made (protocol 3). Its evaluation moves to the prospective data (capture mode).
- The pre-registered max-T uses the centred, not the studentized, BSS. It is very conservative for low-variance candidates such as B1 (dominated by high-variance candidates); a studentized version would be a change control registered before any prospective read.
- `CALIBRATION_BINS.csv` lists the champion's bins twice (as the primary row and as the secondary B2-against-B0 row); the two copies are identical.
- The retrospective holdout is now opened: any further use of it is EXPLORATORY and cannot select or promote a model (ACCEPTANCE "reuse voids it").
- T2: possible partial contact (PI-D-045 item 6).
- The seal is honour-based. The sealed label file is a tracked file in a public repository and any script can read it without a log entry; the single-opening claim rests on the commit order (plan, code and predictions committed before the logged opening), on a champion rule that no look could have changed, and on honesty. The repository cannot prove that nothing looked earlier. For the prospective holdout (Phase 19) the labels must stay out of any file the runner can read until the plan and the predictions are committed.
- Every computation on holdout outcomes after the opening is labelled POST_OPENING and logged (`POST_OPENING_LOG.json`); it can only make a result more conservative (PI-D-066).

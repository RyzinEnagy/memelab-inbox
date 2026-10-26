# Walk-forward protocol and the frozen holdout evaluation plan (Phase 12)

Written 2026-10-26 from 16:40Z by the Phase 12 agent and committed with `../ACCEPTANCE_CHECKLIST.md`, `../experiments/EXPERIMENT_REGISTRY.csv` and PI-D-064 before any Phase 12 code exists, before any holdout prediction is computed and before `phase_06/sealed/` is opened. Every rule below is fixed now. After the seal is opened nothing here changes; a later change is recorded as change control and makes the affected result EXPLORATORY.

What was looked at before writing this, with no label read: the 69 frozen cards (their state, counts and hashes, table below); the five committed development metric files (verdict counts only); the cumulative search ledger of Phase 11; and, for the 95 Solana decisions of the Phase 05 store inside the holdout window, their version 2 feature values (7 to 9 decisions miss a B2 input), their decision days (one export batch near 10:00Z on each of the 7 days 2026-10-17 to 10-23) and their tech-1 state (62 CENSORED_RETRIEVAL with NOT_FETCHED_SEALED, 33 NO_POOL_AT_DECISION). No holdout label, class, count of classes, prevalence or outcome was read; the sealed folder was only hashed by `check_seal.py`.

## 1. What is fixed from earlier phases (not changed here)

- Targets T1 (`price_path_target_before_invalidation_24h`), T1b (`..._6h`) and T2 (`price_path_severe_drawdown_or_halt_24h`), registry fingerprint `4b4aabce...`, ACCEPTANCE inside it (PI-D-014, PI-D-021, PI-D-040).
- Feature sets: version 2 (`features.py`), tech-1, onchain-1, socialcat-1, analog-1, each with its pinned definitions hash as recorded in its card.
- Development walk-forward (Phases 07 to 11, PI-D-048): expanding window by UTC decision day, first fold trained through 2026-10-11 and extended by whole days to 100 events, validation day after the last training label matured (embargo = horizon + confirmation + 900 s), every fit through `labels.training_labels` at the fold cutoff, fold audit (`stats.fold_audit`) fails closed on training rows after the cutoff or labels maturing after it. Split fingerprints T1 `0ab64525...`, T1b `aa16e7ad...`, T2 `82a1c33b...`, the same in every phase. Development out-of-sample sets: T1 24 rows on 3 days, T1b 44 on 5, T2 8 on 1; every development verdict is INSUFFICIENT_HISTORY, INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS (1,104 metric rows over the five phases, 0 directional).
- Final models: the frozen holdout-start cards of Phases 07 to 11, each trained once through the gate on all development labels as of 2026-10-17T00:00:00Z (the holdout start H), which is also its training cutoff. Phase 12 refits none of them and tunes nothing.
- Holdout: decisions in [2026-10-17T00:00Z, 2026-10-24T00:00Z), labels sealed in `phase_06/sealed/holdout_labels.jsonl.gz` (sha256 `e695500d...`), seal digest `d5059bae...`, `SEAL.json` sha256 `f362ca12...` (PI-D-041, PI-D-045). The prospective holdout (decisions from 2026-10-24T00:00Z) belongs to Phase 19 and is not scored, read or counted here.

## 2. Purge and embargo between development and the holdout (P20, P43)

Every candidate card must carry `training_cutoff` = H, `max_train_decision_time` < H and `max_train_label_matures_at` <= H; every holdout decision is at or after H. A card that fails any of these is refused before prediction (`RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF` or `TRAINING_LABEL_AFTER_CUTOFF`). The first holdout export batch (2026-10-17 near 10:00Z) is about 10 h after H; a development label maturing after H is purged by the development rule (never moved into training).

## 3. Candidates (69 frozen cards, all at H)

All 69 cards below are evaluated, each exactly as committed (file sha256 and model sha checked by the family's own `loads`, which refuses a mismatch). Six Phase 08 cards abstain at H (INSUFFICIENT_HISTORY) and are reported with coverage 0. The three fitted Phase 08 T1b cards need tech-1 inputs, which do not exist for any holdout decision (the Phase 05 seal left their candles unread: NOT_FETCHED_SEALED, or no point-in-time pool); they are scored as they are (expected coverage 0, CENSORED_RETRIEVAL or OOD) and no candle is read for them in Phase 12 (a new vendor read in the sealed-evaluation phase would be a new data path chosen after the cards were frozen). Phase 12 makes no network call.

| Card | Phase | Target | State at the holdout start | n used (positives) | model_sha (first 12) | file sha256 (first 12) |
|---|---|---|---|---|---|---|
| `phase_07/artifacts/T1_24h/B0.json` | 07 | T1_24h | fitted | 136 (34) | `6aad694e5cc3` | `d89ab4a62fba` |
| `phase_07/artifacts/T1_24h/B1.json` | 07 | T1_24h | fitted | 136 (34) | `122f1da80c16` | `f84066700ca6` |
| `phase_07/artifacts/T1_24h/B2.json` | 07 | T1_24h | fitted | 136 (34) | `e04172636be8` | `451a38b2dbc0` |
| `phase_07/artifacts/T1_24h/B3.json` | 07 | T1_24h | fitted | 136 (34) | `e55cf42b3ba3` | `f9a18b453224` |
| `phase_07/artifacts/T1_24h/B3F.json` | 07 | T1_24h | fitted | 136 (34) | `89e9d2bd6167` | `cd28cf657ebf` |
| `phase_07/artifacts/T1_24h/B4.json` | 07 | T1_24h | fitted | 136 (34) | `ac441b8a0abc` | `ea96d08e5a83` |
| `phase_07/artifacts/T1b_6h/B0.json` | 07 | T1b_6h | fitted | 224 (26) | `58e20e75c8f6` | `232f38edfb5e` |
| `phase_07/artifacts/T1b_6h/B1.json` | 07 | T1b_6h | fitted | 224 (26) | `a3cfb5ad33fa` | `f8d1f830870c` |
| `phase_07/artifacts/T1b_6h/B2.json` | 07 | T1b_6h | fitted | 224 (26) | `440927a9afea` | `412db87d6ffb` |
| `phase_07/artifacts/T1b_6h/B3.json` | 07 | T1b_6h | fitted | 224 (26) | `f928a479036c` | `d4b3bbdfaec3` |
| `phase_07/artifacts/T1b_6h/B3F.json` | 07 | T1b_6h | fitted | 224 (26) | `be2a443887e3` | `cb23b7dbe791` |
| `phase_07/artifacts/T1b_6h/B4.json` | 07 | T1b_6h | fitted | 224 (26) | `1c604f48e1b9` | `5ef325adcdcf` |
| `phase_07/artifacts/T2_24h/B0.json` | 07 | T2_24h | fitted | 131 (28) | `582bb2242872` | `ba7f22958de4` |
| `phase_07/artifacts/T2_24h/B1.json` | 07 | T2_24h | fitted | 131 (28) | `7a4ad854d8c8` | `3431edd2bb96` |
| `phase_07/artifacts/T2_24h/B2.json` | 07 | T2_24h | fitted | 131 (28) | `d045d9d7a409` | `412d4bce917b` |
| `phase_07/artifacts/T2_24h/B3.json` | 07 | T2_24h | fitted | 131 (28) | `9e57e07d8106` | `cc5d58a8b07c` |
| `phase_07/artifacts/T2_24h/B3F.json` | 07 | T2_24h | fitted | 131 (28) | `7c9f2dd420c8` | `e05576ae3a74` |
| `phase_07/artifacts/T2_24h/B4.json` | 07 | T2_24h | fitted | 131 (28) | `290cdc7d4614` | `0010b258c19e` |
| `phase_08/artifacts/T1_24h/M1_T_LOGIT.json` | 08 | T1_24h | ABSTAIN INSUFFICIENT_HISTORY | 87 (26) | `c5ae485a7bc2` | `483276fced3f` |
| `phase_08/artifacts/T1_24h/M2_T_LOGIT_B2.json` | 08 | T1_24h | ABSTAIN INSUFFICIENT_HISTORY | 87 (26) | `821e8700879b` | `a52ca9199bf2` |
| `phase_08/artifacts/T1_24h/M3_T_STUMPS.json` | 08 | T1_24h | ABSTAIN INSUFFICIENT_HISTORY | 87 (26) | `3ba11decbbaa` | `3ce64a6ec727` |
| `phase_08/artifacts/T1b_6h/M1_T_LOGIT.json` | 08 | T1b_6h | fitted | 144 (20) | `be8fff758ca8` | `463391012c72` |
| `phase_08/artifacts/T1b_6h/M2_T_LOGIT_B2.json` | 08 | T1b_6h | fitted | 144 (20) | `eefba4b0e68a` | `09fa06e812c3` |
| `phase_08/artifacts/T1b_6h/M3_T_STUMPS.json` | 08 | T1b_6h | fitted | 144 (20) | `30931dd6a5bf` | `f2a6c75bdb0c` |
| `phase_08/artifacts/T2_24h/M1_T_LOGIT.json` | 08 | T2_24h | ABSTAIN INSUFFICIENT_HISTORY | 83 (14) | `d1a8bc767760` | `0df064f77bde` |
| `phase_08/artifacts/T2_24h/M2_T_LOGIT_B2.json` | 08 | T2_24h | ABSTAIN INSUFFICIENT_HISTORY | 83 (14) | `ef43deb01467` | `e2480a97cb2d` |
| `phase_08/artifacts/T2_24h/M3_T_STUMPS.json` | 08 | T2_24h | ABSTAIN INSUFFICIENT_HISTORY | 83 (14) | `6b7d77225d32` | `34e480ed1a09` |
| `phase_09/artifacts/T1_24h/A1_OC_B2_TC.json` | 09 | T1_24h | fitted | 136 (34) | `6d2c43adec56` | `f0c041adfc96` |
| `phase_09/artifacts/T1_24h/M1_OC_LOGIT.json` | 09 | T1_24h | fitted | 136 (34) | `934782c5bc37` | `8eaf15575399` |
| `phase_09/artifacts/T1_24h/M2_OC_LOGIT_B2.json` | 09 | T1_24h | fitted | 136 (34) | `1ba2aef1faef` | `6fc65eee7592` |
| `phase_09/artifacts/T1_24h/M3_OC_LOGIT_TREND.json` | 09 | T1_24h | fitted | 136 (34) | `ab75899751a1` | `94c14d046882` |
| `phase_09/artifacts/T1_24h/R1_OC_RULE.json` | 09 | T1_24h | fitted | 136 (34) | `e3491c366961` | `0d4ca221b2b3` |
| `phase_09/artifacts/T1b_6h/A1_OC_B2_TC.json` | 09 | T1b_6h | fitted | 224 (26) | `bcfc3b94d020` | `d33f731cce3f` |
| `phase_09/artifacts/T1b_6h/M1_OC_LOGIT.json` | 09 | T1b_6h | fitted | 224 (26) | `82c72bda532c` | `326c969a7276` |
| `phase_09/artifacts/T1b_6h/M2_OC_LOGIT_B2.json` | 09 | T1b_6h | fitted | 224 (26) | `69caa50402cc` | `9fb8949ddcd3` |
| `phase_09/artifacts/T1b_6h/M3_OC_LOGIT_TREND.json` | 09 | T1b_6h | fitted | 224 (26) | `865df8bc9b00` | `3d518796c04f` |
| `phase_09/artifacts/T1b_6h/R1_OC_RULE.json` | 09 | T1b_6h | fitted | 224 (26) | `bd3a323bfa1b` | `05f5cb2a0d9e` |
| `phase_09/artifacts/T2_24h/A1_OC_B2_TC.json` | 09 | T2_24h | fitted | 131 (28) | `7ddaeff1b9c6` | `7407de8e2a0d` |
| `phase_09/artifacts/T2_24h/M1_OC_LOGIT.json` | 09 | T2_24h | fitted | 131 (28) | `efa6b18dd213` | `96e4751e94d1` |
| `phase_09/artifacts/T2_24h/M2_OC_LOGIT_B2.json` | 09 | T2_24h | fitted | 131 (28) | `abfbd30a4f1c` | `ece506d97267` |
| `phase_09/artifacts/T2_24h/M3_OC_LOGIT_TREND.json` | 09 | T2_24h | fitted | 131 (28) | `89d9704d4674` | `b275183936ad` |
| `phase_09/artifacts/T2_24h/R1_OC_RULE.json` | 09 | T2_24h | fitted | 131 (28) | `2888abbf7d17` | `e971ff6c4838` |
| `phase_10/artifacts/T1_24h/A2_SC_B2_TC.json` | 10 | T1_24h | fitted | 129 (33) | `cc549a4bce9c` | `5619019c580b` |
| `phase_10/artifacts/T1_24h/G1_SC_STUMPS_B2.json` | 10 | T1_24h | fitted | 129 (33) | `ba83a862456a` | `ee7c935ea676` |
| `phase_10/artifacts/T1_24h/R2_SC_RULE.json` | 10 | T1_24h | fitted | 136 (34) | `9d6d954bf60c` | `f348c4ba14ae` |
| `phase_10/artifacts/T1_24h/S1_SC_LOGIT.json` | 10 | T1_24h | fitted | 129 (33) | `02c524e3d828` | `42b9e05e6c3e` |
| `phase_10/artifacts/T1_24h/S2_SC_LOGIT_B2.json` | 10 | T1_24h | fitted | 129 (33) | `82e1e32233dc` | `22e0547e3c55` |
| `phase_10/artifacts/T1_24h/S3_SC_LOGIT_TREND.json` | 10 | T1_24h | fitted | 129 (33) | `99c5c3c2f08b` | `d20c565612b3` |
| `phase_10/artifacts/T1b_6h/A2_SC_B2_TC.json` | 10 | T1b_6h | fitted | 210 (25) | `ff7e0b469ec9` | `5cfdf54bbb8e` |
| `phase_10/artifacts/T1b_6h/G1_SC_STUMPS_B2.json` | 10 | T1b_6h | fitted | 210 (25) | `0213815d0abe` | `6a5d698d0fd5` |
| `phase_10/artifacts/T1b_6h/R2_SC_RULE.json` | 10 | T1b_6h | fitted | 224 (26) | `6e85b93541ca` | `291fc029ac21` |
| `phase_10/artifacts/T1b_6h/S1_SC_LOGIT.json` | 10 | T1b_6h | fitted | 210 (25) | `bcf39870ecbf` | `76b04ac3bb45` |
| `phase_10/artifacts/T1b_6h/S2_SC_LOGIT_B2.json` | 10 | T1b_6h | fitted | 210 (25) | `0d66dfa7643f` | `c57b7f302054` |
| `phase_10/artifacts/T1b_6h/S3_SC_LOGIT_TREND.json` | 10 | T1b_6h | fitted | 210 (25) | `3f893f7c2d7b` | `e4ad26ca296f` |
| `phase_10/artifacts/T2_24h/A2_SC_B2_TC.json` | 10 | T2_24h | fitted | 124 (26) | `f54ef7501580` | `54bfda82e726` |
| `phase_10/artifacts/T2_24h/G1_SC_STUMPS_B2.json` | 10 | T2_24h | fitted | 124 (26) | `9a24f3a267ee` | `546c0b50f91b` |
| `phase_10/artifacts/T2_24h/R2_SC_RULE.json` | 10 | T2_24h | fitted | 131 (28) | `e4336ebba476` | `15d07f409380` |
| `phase_10/artifacts/T2_24h/S1_SC_LOGIT.json` | 10 | T2_24h | fitted | 124 (26) | `c1a5bb8090a0` | `becf7a485b8d` |
| `phase_10/artifacts/T2_24h/S2_SC_LOGIT_B2.json` | 10 | T2_24h | fitted | 124 (26) | `5848abf9b551` | `72225f61a848` |
| `phase_10/artifacts/T2_24h/S3_SC_LOGIT_TREND.json` | 10 | T2_24h | fitted | 124 (26) | `92f900a26c0c` | `0fc45e785560` |
| `phase_11/artifacts/T1_24h/AC1_STRATA.json` | 11 | T1_24h | fitted | 136 (34) | `c88205d37329` | `7e5bb0860e94` |
| `phase_11/artifacts/T1_24h/AC2_KNN.json` | 11 | T1_24h | fitted | 136 (34) | `0f9da07ec06f` | `fb81866f5883` |
| `phase_11/artifacts/T1_24h/AC3_KNN_REGIME.json` | 11 | T1_24h | fitted | 136 (34) | `d1e2f31c40f7` | `4d1517cbc1d1` |
| `phase_11/artifacts/T1b_6h/AC1_STRATA.json` | 11 | T1b_6h | fitted | 224 (26) | `113e6c7e4efa` | `03657fdccbc4` |
| `phase_11/artifacts/T1b_6h/AC2_KNN.json` | 11 | T1b_6h | fitted | 224 (26) | `58e79d928b41` | `05828d94c0fa` |
| `phase_11/artifacts/T1b_6h/AC3_KNN_REGIME.json` | 11 | T1b_6h | fitted | 224 (26) | `f4fc5b1244be` | `7a1dbd91cc33` |
| `phase_11/artifacts/T2_24h/AC1_STRATA.json` | 11 | T2_24h | fitted | 131 (28) | `f7b75f0ecd8f` | `766af93144d1` |
| `phase_11/artifacts/T2_24h/AC2_KNN.json` | 11 | T2_24h | fitted | 131 (28) | `9e21f86e42be` | `da1607436c9b` |
| `phase_11/artifacts/T2_24h/AC3_KNN_REGIME.json` | 11 | T2_24h | fitted | 131 (28) | `2b87089aa860` | `04a766b8c82d` |

Ablation variants that never had a frozen card (Phase 08 A1 to A5, Phase 09 A-rows other than A1, AC3_LOCO, NC controls of earlier phases) are not candidates.

## 4. Champion-selection rule (development data only, fixed before the seal is opened)

For each primary target the champion is the Phase 07 B2 card (the simple model a complex one must beat, ACCEPTANCE baselines and SCIENTIFIC_VALIDATION baseline 2), unless a frozen candidate earned the frozen promotion rule "champion_over_B2" on development data: a development verdict SKILL_INDICATED_DEVELOPMENT_ONLY against reference B2 in view ALL in its phase's committed metric file (Phase 08 `TECHNICAL_METRICS.csv`, Phase 09 `ONCHAIN_METRICS.csv`, Phase 10 `SOCIAL_METRICS.csv`, Phase 11 `ANALOG_METRICS.csv`). If more than one does, the one with the lowest development Brier among them. If B2 abstains at H, there is no champion and the primary test is INSUFFICIENT_HISTORY. The rule is applied by code (`evaluation.champion`) to the committed files before any holdout prediction; on those files no candidate has any directional development verdict, so the expected champion is B2 for all three targets, chosen by default and not by any evidence of skill. The champion is not selected by its development score, so there is no winner's curse inside the primary family (see 7).

## 5. Primary family, score and verdict

- Primary comparison: champion against B0 (the training prevalence at H, Phase 07 card B0) on the primary holdout set, rows where both have a number.
- Primary score: Brier score; headline Brier skill score (BSS) against B0.
- Intervals: bootstrap of whole decision days and, separately, of whole mints, 20,000 replicates each, seed 20261025, percentile 95%; the wider of the two governs; the day interval is undefined below 5 days. ACCEPTANCE sets 2,000 as the minimum number of replicates; 20,000 is used for every holdout evaluation so that the smallest attainable one-sided p (1/20,001) leaves the full-search correction in 7 attainable. One-sided p = (1 + replicates with BSS <= 0) / (replicates + 1) on the governing unit.
- Holm across the three primary targets (an undefined p counts as 1).
- Verdict order (Phase 07's frozen `baselines.verdict` and `evaluation_gate`, unchanged): no number INSUFFICIENT_HISTORY; fewer than 5 days or no governing interval INSUFFICIENT_DAYS; among the rows with a number fewer than 50 events or fewer than 10 per class INSUFFICIENT_EVENTS; governing upper bound below 0 WORSE_THAN_BASE_RATE; lower bound above 0 with Holm-adjusted p below 0.05 SKILL_INDICATED_RETROSPECTIVE_HOLDOUT (the holdout name of Phase 07's SKILL_INDICATED_DEVELOPMENT_ONLY); otherwise NOT_DISTINGUISHABLE_FROM_BASE_RATE.
- Also reported for each primary comparison: N, positives, prevalence with its Wilson 95% interval beside the training prevalence of B0, days, mints, coverage and abstain reasons, Brier of both, log loss of both (clip 1e-6), ROC AUC and average precision (AUCPR) when each class has at least 10 events and the prediction is not constant, calibration bins (quantile, at least 20 events, at most 5 bins, in the large only below 40 events) with counts, mean prediction, observed rate and Wilson interval, ECE (descriptive), the design-effect N per unit, and whether every SHADOW criterion of ACCEPTANCE holds on this holdout (counts, calibration in the large and every bin, BSS point at least 0). Phase 12 promotes nothing: SHADOW and champion status are Phase 13 and Phase 16 decisions, VALIDATED_EXPERIMENTAL needs the prospective holdout (Phase 19).
- T2 results carry the note of PI-D-045 item 6 (possible partial contact with the T2 holdout through first-pass public call counts; nobody computed the bound).

## 6. Secondary family (every frozen candidate)

Every fitted candidate other than B0 against B0, and every fitted candidate other than B0 and B2 against B2, on the primary holdout set, with the same metrics and verdict code. These results are descriptive. No secondary result can change the champion, promote a model or enter Phase 12's conclusions as a claim of skill; at most a secondary candidate that survives all three corrections in 7 is named as a hypothesis for the prospective holdout (Phase 19).

## 7. Selection-bias correction

- Primary family: the champion was fixed by a rule that did not rank candidates by score, so the only multiplicity is the three targets: Holm across the three.
- Secondary family, applied together: (a) Holm across every secondary (candidate, target, reference) test; (b) a single-step max-T correction against B0: the day-block bootstrap (20,000 replicates, seed 20261025, the same resampled days for all targets) of the centred statistic BSS* - BSS for every fitted candidate and target, adjusted p_j = (1 + replicates with max over candidates of (BSS* - BSS) >= BSS_j) / (replicates + 1); (c) full-search Bonferroni: p times N_search, where N_search is the number of candidate configurations ever tried on real data (below). A secondary candidate is "skill indicated after selection correction" only if its own verdict would be SKILL and (a), (b) and (c) are all below 0.05.
- Search ledger totals (P22), from `phase_11/experiments/SEARCH_LEDGER.csv`, the cumulative ledger through Phase 11, counted by code (`evaluation.ledger_totals`): 2,896 rows (Phase 04 31, Phase 07 488, Phase 08 616, Phase 09 670, Phase 10 703, Phase 11 388); 87 distinct candidate model configurations on real development data (target and candidate; B0 and B2 refits of later phases counted once; ablations, rules, the leave-one-campaign-out sensitivity included); 31 Phase 04 bake-off configurations (26 BAKEOFF_ONLY rows over two targets, two environments and the approaches, and the 5 files of the run before the token-age fix); 306 negative-control fits (seed level); 15 debug runs on real data. N_search = 87 + 31 = 118. Phase 12 adds no candidate configuration (it fits only the 60 NC1 controls in 8) and writes every evaluation, control, trap and sensitivity as a ledger row in `FULL_EXPERIMENT_LEDGER.csv`.

## 8. Negative controls and traps on the holdout

- NC1 (shuffled outcome inside training only): B2 refitted at H on the development training labels permuted with seeds 0 to 19 (`numpy.random.default_rng(seed).permutation`), predictions computed before the seal is opened, scored like the champion; `baselines.nc1_verdict` on the mean BSS; the share of seeds whose BSS is above the real B2's.
- NC2 (future-feature trap, must fail): for every holdout decision and every fitted family (B2, onchain M2, socialcat S2, analog AC3, and a technical card), one model input's availability moved 1 s after the decision must be refused by the family's own as-of check; a column outside the family allowlist must be refused. One acceptance stops the run (exit 1).
- NC3 (same-ticker join trap, must fail): every primary holdout label row whose token symbol is also carried by another mint in the decision table is joined to that other mint's feature row through `baselines.join_by_symbol`; `IdentityJoinError` must be raised every time.
- P13 replay trap (must fail): every holdout-start card applied to a development decision decided before H must raise RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF (Phase 07 cards through `evaluation.score`, the others through their own `predict` and `evaluation.score`); a card whose cutoff is moved after a holdout decision must raise the same.
- P05: holdout rows that are PENDING, censored, not LABELED, or whose `label_observed_at` is before `label_matures_at` never enter (counted).

## 9. Exclusions, sensitivities and dataset shift (descriptive, outside the Holm family)

- Primary holdout set: sealed rows with split HOLDOUT (recomputed from the decision time), state LABELED, censored 0, label 0 or 1, target and label versions equal to the registry's, a feature row of the same decision (decision key, chain, mint, decision time equal), and not one of the two contacted decisions of ACCEPTANCE `holdout_contacted` (`CnPL1x...` 2026-10-17T10:20:42Z, `Tm2iq...` 2026-10-19T10:34:05Z; PI-D-021 item 4); the row's own `holdout_contacted` flag must agree with that list, else the run stops.
- Sensitivities for the champion and B0: CONTACTED_INCLUDED, NO_KEY_CONFLICT, NEW_MINTS (mint absent from the target's training labels at H), NEW_CREATORS (creator absent from them), PIT_ONLY route, the conservative lens (censored decisions counted T1 and T1b negative, T2 positive, where the champion has a number), and a creator-group bootstrap interval (creator, else mint; P14) reported beside the governing interval (not governing).
- Dataset shift breakdowns of the champion against B0 (P21; frozen verdict code per cohort, so below the minimums they are INSUFFICIENT): decision day; launch month (year and month of the token row's `first_pool_at`, UNKNOWN when missing); pool type (analog-1 launchpad class of the decision's own token row); label route; regime label at T (`analog.regime_as_of` over the Solana decisions visible at T); liquidity bucket and launch-age bucket (`labels.cohort_of`); crash day as of T (CRASH_DAY_AS_OF when the median `hist_log_price_change_since_prior` of that day's decisions with a value is below log 0.5, else NORMAL_DAY, UNKNOWN when no value); and prior shift (holdout prevalence with its Wilson interval against B0's training prevalence).

## 10. The opening, once

1. Before the seal: the code, this plan, the candidate and champion file and every holdout prediction (all cards and NC1) are committed; the prediction files' sha256 are written in `PREOPEN_MANIFEST.json` in the same commit.
2. Opening run (`probes/run_holdout.py open`), at that commit with a clean tree: run `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` and require exit 0, `"problems": []` and the three hashes equal to the values pinned in DECISIONS (PI-D-041, PI-D-045) and in `evaluation.SEAL_PINS`; require that `validation/OPENING_LOG.json` does not exist; write the opening log (UTC time, HEAD commit, the three hashes, the sha256 of the bytes about to be read, the prediction manifest sha256) before decompressing; read the label file once, check its sha256 again on the bytes read; verify every prediction file against the manifest; score everything in this plan in that one run; append the output hashes to the log.
3. Any later read of the holdout labels is logged. A rerun of the same committed program on the same inputs (the determinism check, the orchestrator's skeptic) is a REPRODUCTION and adds no analysis; any analysis not in this plan is EXPLORATORY, recorded with its time and reason, and cannot change a verdict, a champion or a promotion.

## 11. Replay discipline (step 4 of the phase prompt)

Every historical prediction must come from a model trained, as of its decision, on matured labels and available inputs only: (a) every row of the committed development `OOS_PREDICTIONS.csv` of Phases 07 to 11 has its fold cutoff at or before its decision time, and the fold's cards in `artifacts/folds/` carry that cutoff; (b) every holdout prediction comes from a card with cutoff H at or before the decision and at most 14 days before it (MODEL_STALE otherwise); (c) the traps of 8 raise. The audit is `REPLAY_AUDIT.json`; a failed check stops the run.

## 12. Expected result, stated in advance (Phase 01)

On this data volume the expected honest outcome is "not distinguishable from the base rate" or INSUFFICIENT_EVENTS: about 60 to 67 labelled holdout events per target before eligibility of the champion's inputs, on 7 days, and in development the positive share was 25% (T1), 12% (T1b) and 21% (T2), so T1b in particular may fall below 10 positives. Phase 01's design arithmetic gave about 24% power for a true BSS of 0.10 at 50 independent events, less with day clustering. Whatever the result, the report says exactly what the data supports, empirical validity is stated apart from engineering validation, and if there is no reliable out-of-sample value the engine prefers the baseline or abstention and marks the complex models not promoted.

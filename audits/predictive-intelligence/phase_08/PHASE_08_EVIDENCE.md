# Phase 08 evidence: technical market-state predictors

Status: NEEDS_REVIEW after repair pass 2 (PI-D-052), for one item only: checklist item G16 (logistic within 1e-6 of scikit-learn lbfgs) failed as registered and is explained as lbfgs's stopping point; every other gate item holds. The independent skeptic found no material failure (8 minor findings, CX-S08), all folded in. Every number is PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046). Deliverables: `models/TECHNICAL_MODEL_CARD.md`, `memelab/predictive/technical.py`, `probes/run_technical.py` (train and predict runner), `evidence/run_log.json` (run manifest), `experiments/TECHNICAL_METRICS.csv`, `ABLATIONS.csv`, `HIT_MISS_COHORTS.csv` (out-of-sample against baseline tables), `tests/test_predictive_technical.py` (adverse forecast fixture tests), `evidence/trace/` (timestamp-by-timestamp traces).

## Where and when

| Item | Value |
|---|---|
| Branch | `feature/predictive-intelligence` |
| HEAD before | `1139575` (Phase 07 records, pushed) |
| Pre-registration | `8599318` 2026-10-25T21:06:04Z: checklist, experiment registry (99 rows), PI-D-050 |
| Code before recorded run 1 | `d290384` 2026-10-25T21:22:26Z |
| Runner repair before recorded run 2 | `d9b2a9c` 2026-10-25T21:24:03Z |
| Recorded run 2 | 2026-10-25T21:24:03Z to 21:24:29Z at `d9b2a9c` (`evidence/run_log.json`) |
| Outputs and records | `fc6b990` 2026-10-25T21:35:12Z; post-commit records `0656b7c` |
| Repair pass 2 code | `e81ee46` 2026-10-25T22:12:48Z (tests, probes, skeptic copy) |
| Repair pass 2 outputs and records | the commit after `e81ee46` (hash in HANDOFF.md) |
| Python, numpy | 3.13, the lab's numpy; scikit-learn 1.9.1 only in `/home/claude/pi_research/venvs/p04_bundle` |

## Entry gate (re-run independently)

| Command | Exit | Result |
|---|---|---|
| `sha256sum -c SHA256SUMS.txt` (package) | 0 | all OK |
| `python -m pytest tests -q -p no:cacheprovider` at `1139575` | 1 | `1 failed, 1179 passed in 165.18s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261025_2058_BRETT_0x532f.md` removed by hand |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []`, holdout labels `e695500d...`, seal `d5059bae...`, SEAL.json `f362ca12...` |
| `PHASE_07_RESULTS.json` | | status PASS, head_after `d539a26`, next 08 (provisional under PI-D-046) |

## Commands of this phase

| Command | Exit | Result |
|---|---|---|
| features-only probe (scratch script: `run_technical.tech_snapshots` on the real stores) | 0 | 240 labelled development decisions, 0 inconsistent with version 2; 154 complete, 71 OOD, 15 CENSORED_RETRIEVAL; 0 inputs after T |
| `python -m pytest tests/test_predictive_technical.py -q` | 0 | 39 passed at `d290384`; 40 passed with the ledger test added with the outputs |
| `python -B probes/run_technical.py audits/predictive-intelligence/phase_08` at `d290384` (recorded run 1) | 0 | all outputs; P06-T probe defect (see iteration log) |
| `python -B probes/run_technical.py audits/predictive-intelligence/phase_08 --npz <scratch>/arrays08.npz` at `d9b2a9c` (recorded run 2) | 0 | `{"targets": OK x3, "outputs": 34, "socket_events": 0, "stores_unchanged": true, "ledger_missing": 0}` |
| same at `d9b2a9c` into a scratch folder (run 3) | 0 | 28 generated files identical except the traces' latency field (`evidence/determinism.json`) |
| `python -B probes/verify_trace.py evidence/trace/FORECAST_TRACE.json` | 0 | no difference |
| `python -B probes/verify_trace.py evidence/trace/second/FORECAST_TRACE.json` | 0 | no difference |
| `<venv>/python -B probes/sklearn_crosscheck_tech.py <scratch>/arrays08.npz evidence/sklearn_crosscheck.json` | 1 | stumps within 3.3e-16, same split in all rounds; logistic lbfgs up to 1.13e-6 (pre-registered 1e-6) |
| `<venv>/python -B probes/logit_solver_diagnosis.py <scratch>/arrays08.npz evidence/logit_solver_diagnosis.json` | 0 | lbfgs gradient up to 7.2e-6 against 2.2e-15 for numpy; newton-cholesky and newton-cg within 7.1e-14 of numpy |
| `python -B probes/mutation_technical.py evidence/mutation_technical.json` | 0 | 28 of 28 caught |
| `python -m pytest tests -q -p no:cacheprovider` before the outputs commit | 1 | `1 failed, 1218 passed in 165.93s` (known failure only) |

Sources: no web source was used; the phase uses the package files, the repository, the two private stores and the research venv. Cost: 0 Firecrawl credits, 0 vendor calls, 0 network calls (audit hook); COST_LEDGER.md unchanged.

## Results in short

| Target | Technical models (M1, M2, M3, A1 to A5) | B2 (Phase 07, same folds) |
|---|---|---|
| T1 24 h | INSUFFICIENT_HISTORY in every fold (technical rows at most 76 with 22 positive; at the holdout start 87 with 26) | 24 (8), 3 days, BSS -0.066, INSUFFICIENT_DAYS |
| T1b 6 h | fitted only in fold 4 (138 rows, 20 positive); 6 scored rows, 0 positive, 1 day: INSUFFICIENT_DAYS (M2 BSS 0.729 against B0, 0.672 against B2: arithmetic of six negatives, not skill) | 44 (3), 5 days, BSS 0.108, INSUFFICIENT_EVENTS |
| T2 24 h | INSUFFICIENT_HISTORY in every fold (61 with 13; at the holdout start 83 with 14) | 8 (1), 1 day, BSS -0.197, INSUFFICIENT_DAYS |

Every model: MODEL_NOT_PROMOTED. Train-only cards at the holdout start: T1b M1, M2, M3 fitted (144 rows, 20 positive); T1 and T2 abstain (INSUFFICIENT_HISTORY). Details and the reading: `models/TECHNICAL_MODEL_CARD.md`.

## Acceptance checklist results

| Id | Result |
|---|---|
| G1 | pass |
| G2 | pass |
| G3 | pass: `8599318` (21:06:04Z) before the code (21:22:26Z) and every real-label run; the features-only probe before the code commit read label rows for their keys only (ledger row) |
| G4 | pass: numpy and the standard library only (test); 40 tests in the first pass, 50 after repair pass 2 |
| G5 | pass: 248 candles not yet available at T, 0 used; store holds 0 candles ending after their availability; CX-08 tests |
| G6 | pass: 240 of 240 consistent |
| G7 | pass: split fingerprints equal; 0 differences in 76 B0 and B2 numbers |
| G8 | pass: training rows only from `training_labels` (WalkForwardMismatch otherwise), identity checked in `attach` and `technical_as_of`, sealed and bake-off paths refused |
| G9 | pass: fits only at 100 events and 20 per class on each model's own rows (`evidence/folds.json` used counts) |
| G10 | pass: `experiments/TECHNICAL_METRICS.csv` (234 comparison rows: 13 per target and view over 6 views, plus 18 NC1-T rows), Phase 07 verdict code unchanged |
| G11 | pass: NC1-T uninformative (INSUFFICIENT_HISTORY or INSUFFICIENT_DAYS), NC2-T 98 of 98 refused, P06-T 1,758 of 1,758 refused (after the probe repair), P13-T 9 of 9 refused |
| G12 | pass: A1 to A5 reported |
| G13 | pass: hit and miss, coverage, cost |
| G14 | pass |
| G15 | pass |
| G16 | FAILED as registered: logistic against lbfgs up to 2.08e-6 (1.13e-6 fold 4, 2.08e-6 the M2 holdout-start design), above 1e-6. Explained: lbfgs stops with gradients of 1.0e-6 to 7.2e-6; numpy at most 3.3e-15; newton-cholesky within 9.0e-12. Stumps pass (3.3e-16); `stats.Prep` equals scikit-learn within 2.1e-14 (repair pass 2) |
| G17 | pass (apart from the traces' wall-clock latency field) |
| G18 | pass (fixture: M1, M2, M3 beat B0, NC1-T does not, NO_REAL_HISTORICAL_EVIDENCE) |
| G19 | pass (both traces) |
| G20 | pass: 1,135 ledger rows after repair pass 2 (Phase 07's 520 plus 615, the debug rows now listing run 3 and the repair rerun) |
| G21 | pass after repair pass 2: tests for P06, P10, P11, P13, P20, P21, P22, P36, P38, P43, CX-08 and CX-S08; 39 of 39 mutations caught (28 plus the skeptic's 11 non-equivalent survivors; 1 equivalent recorded) |
| G22 | pass: no existing module imports the new code (existing test), flag OFF, score and fatal flags untouched |
| G23 | pass: suite (known failure only), guard, seal check and single-branch release audit after the commit, below |

## Iteration log

1. Pass 1 (inspect and pre-register): read the package, records, Phase 05 to 07 code and outputs; counted stored version 2 candle-feature missingness on the labelled decisions (no label value); wrote and committed the checklist, registry and PI-D-050.
2. Pass 2 (build and test): `technical.py`, 37 then 39 tests; the mutation probe first caught 25 of 28 (survivors: the coverage boundary, a missing value filled with 0 in `attach`, the 6 h range computed over 24 h); three tests added; 28 of 28. Oracle on synthetic designs: stumps equal scikit-learn once thresholds are compared at float32 (scikit-learn casts to float32).
3. Pass 3 (run and attack, own pass, not independent): recorded run 1 at `d290384`. Own attack found the P06-T probe counting a value that changed only because the query time moved (the last close's age) as a trap: 1 of 154 "accepted". The probe now separates values that use a candle not available at T (1,758, all refused) from clock-only changes (12, correctly accepted). The pre-registered trace row fell in a fold without a fitted technical model, so a second trace with a primary-model number was added (disclosed). Runner repaired in `d9b2a9c`; recorded run 2; run 3 for determinism. Oracle on the real fold-4 design: lbfgs differs by 1.13e-6; diagnosis probe added. Ledger test added with the outputs.

## Own adversarial pass (not independent)

- Counterexample CX-08 (new, wrong but plausible): a breakout or range feature built on candle highs and lows, which GeckoTerminal computes from the request window (PI-D-037): two reads of the same pool would give different features for the same decision. Caught by `test_cx08_opens_highs_and_lows_never_change_a_feature`, `test_cx08_a_later_read_that_only_moves_opens_highs_and_lows_changes_nothing`, `test_tech_reads_closes_and_volumes_only` and the mutation "breakout reads highs".
- In-progress candles: version 2's `_candle_values` does not itself drop a candle that ends after T; it relies on the store refusing a candle served before it closed (`store.ingest_gt_response` through `outcomes_core.normalize_observation`, tolerance 0). tech-1 drops such a candle itself as well. The store holds 0 such candles. Phase 17 (live capture) must keep every live read on that ingest path.
- Pool choice: the 71 labelled decisions without a point-in-time pool (all CURRENT_VENDOR_LIST) get no technical value; the label route's pool, read on 2026-10-24, is never a feature source (PI-D-050 item 4, test).
- The T1b fold-4 numbers rest on six negative rows; the model card says so plainly and no verdict uses them.
- Not done: the registry target `failed_breakout_6h` stays DEFERRED (PI-D-050 item 5).

## Independent skeptic and repair pass 2

The orchestrator's skeptic reviewed `0656b7c` in its own clone with copies of the stores (`skeptic/PHASE_08_SKEPTIC.md`, scripts and outputs beside it). It reproduced every number with its own code (tech-1 from the checklist text, labels and folds by SQL, models by scikit-learn), the folds and B0 and B2 equality, the determinism, the pre-registration timing, the lbfgs diagnosis, CX-08 on a store copy with every open, high and low rewritten (240 of 240 snapshots unchanged), and the suite, guard, seal and audit. No material failure; 8 minor findings.

Counterexample CX-S08 (score-time re-standardisation): a scorer that keeps the card's columns but standardises the rows being scored with their own mean and sd makes each forecast depend on the other rows of the batch, some decided later. On the first-pass code it passed all 40 tests and the runner; the T1b M2 Brier would move from 0.0040 to 0.0436 with the verdict unchanged. What catches it now: `test_cx_s08_a_number_does_not_depend_on_the_other_rows_scored_with_it` and `test_scoring_uses_the_cards_training_mean_and_sd` (both fail under the mutation, which is in the mutation probe as "S: CX-S08"), besides `verify_trace.py` on the second trace.

| Finding | Verified | Repair |
|---|---|---|
| m1 young pools labelled CENSORED_RETRIEVAL | yes: 12 of 15 pools younger than 24 h at T, 3 older with short history (`probes/young_pools.py`, `evidence/young_pools.json`) | disclosed in the model card, PI-D-052 and HANDOFF; label kept (version 2 rule, no number moves); tech-1 cannot score pools under about 24 h 5 min |
| m2 12 mutations survive the tests | yes (11 real gaps, 1 equivalent) | 10 tests added (50); mutation probe 39 of 39 |
| m3 runner exits 0 on a failed trap | yes | runner exits 1 naming the trap; shown with the availability mutation on a tree copy (`evidence/runner_exit_check.json`) |
| m4 probe time | yes: about 21:16Z | corrected in the ledger, PI-D-052, model card |
| m5 P06-T description | yes: `tech_log_ret_1h` of `55257a0b...` | corrected; the repaired rule named as a reinterpretation made after the result |
| m6 oracle scope | yes | oracle covers `stats.Prep` (2.1e-14) and the holdout-start cards; newton-cholesky reported; G16 kept failed as registered |
| m7 20-positive fragility | yes: 138 (20) and 144 (20) | stated in the model card, PI-D-052 and HANDOFF |
| m8 PI-D-051 wording | yes | reworded |

Repair pass 2 commands:

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_predictive_technical.py -q -p no:cacheprovider` | 0 | 50 passed |
| `python -B probes/mutation_technical.py evidence/mutation_technical.json` | 0 | 39 of 39 caught; equivalent mutation recorded |
| `python -B probes/young_pools.py evidence/young_pools.json` | 0 | 15 censored: 12 young pools, 3 short history |
| `python -B probes/run_technical.py audits/predictive-intelligence/phase_08 --npz <scratch>/arrays08r.npz` at `e81ee46` | 0 | outputs identical to recorded run 2 apart from the run log, the traces' latency field and the ledger's debug rows |
| the same on a tree copy with the availability mutation | 1 | `{"FAILED": ["NC2T"]}` |
| `python -B probes/verify_trace.py` on both traces | 0 | no difference |
| `<venv>/python -B probes/sklearn_crosscheck_tech.py <scratch>/arrays08r.npz evidence/sklearn_crosscheck.json` | 1 | stumps 3.3e-16; Prep 2.1e-14; newton-cholesky 9.0e-12; lbfgs 2.08e-6 (G16 rule, failed as registered) |
| `<venv>/python -B probes/logit_solver_diagnosis.py <scratch>/arrays08r.npz evidence/logit_solver_diagnosis.json` | 0 | lbfgs gradients 1.0e-6 to 7.2e-6, numpy at most 3.3e-15 |

## Post-commit results

On the committed tree at `fc6b990` (files in `postcommit/`):

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 1219 passed in 174.62s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261025_2135_BRETT_0x532f.md` removed by hand |
| `python -m memelab social guard` | 0 | `"violations": []` |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| `python tools/release_audit.py --history` on a single-branch clone of `feature/predictive-intelligence` at `fc6b990` with `origin/main` (`e245d91`) | 0 | "Needs action: no." |

`git status` clean after removing the stray report.

## Artifacts

<!-- artifacts:start -->
| Path | sha256 |
|---|---|
| `audits/predictive-intelligence/phase_08/ACCEPTANCE_CHECKLIST.md` | `e42d70a321dc2e52ccf245400880a3223a5abab012e884d4a8d0bb27c4e06ad4` |
| `audits/predictive-intelligence/phase_08/SKEPTIC_PACKET.md` | `8aade18ee41992e2ab90a4369565873fd5d7e397067d621da62baae8e5a58495` |
| `audits/predictive-intelligence/phase_08/artifacts/T1_24h/M1_T_LOGIT.json` | `483276fced3fda3f041ab8e611929f263c5d241a5a4770cdc2ed83f12710b7e6` |
| `audits/predictive-intelligence/phase_08/artifacts/T1_24h/M2_T_LOGIT_B2.json` | `a52ca9199bf23ee050bfb805b92981d6a5d4a59a031be26989dd7b7cbccbc5e1` |
| `audits/predictive-intelligence/phase_08/artifacts/T1_24h/M3_T_STUMPS.json` | `3ce64a6ec727176716458d98fb9bb3acc8d0a3262bb3bfb31df329f00a897b1b` |
| `audits/predictive-intelligence/phase_08/artifacts/T1b_6h/M1_T_LOGIT.json` | `463391012c729b0c21c307c91891eccfe6cae16b451c3194350b7f64b3b7bec0` |
| `audits/predictive-intelligence/phase_08/artifacts/T1b_6h/M2_T_LOGIT_B2.json` | `09fa06e812c383c72305872ebf309d961129e5e23334d22f509795ab7981fbf0` |
| `audits/predictive-intelligence/phase_08/artifacts/T1b_6h/M3_T_STUMPS.json` | `f2a6c75bdb0c8484c157147ff770084ee8470e0e35eecdfa8478db8b93b422bb` |
| `audits/predictive-intelligence/phase_08/artifacts/T2_24h/M1_T_LOGIT.json` | `0df064f77bde68fa338a28d0ea8f9194e07098f962aa9a180a3daddd14129a59` |
| `audits/predictive-intelligence/phase_08/artifacts/T2_24h/M2_T_LOGIT_B2.json` | `e2480a97cb2d90104d0f13d52f5b5f6ea6e60504897508af4e45d358484f7ea8` |
| `audits/predictive-intelligence/phase_08/artifacts/T2_24h/M3_T_STUMPS.json` | `34e480ed1a0913e9ad39554a9aa0017bae45b48f8b6e523af2404a40af9b3031` |
| `audits/predictive-intelligence/phase_08/artifacts/folds/T1_24h.json` | `cb45115daf8d660560897cb1e5a128236ab08ddf208b18d5610031348ac2dec6` |
| `audits/predictive-intelligence/phase_08/artifacts/folds/T1b_6h.json` | `abf5fedbb2aee303935d7497b4dd65ea8a40e54287fff9e511b6ddaeb73294fe` |
| `audits/predictive-intelligence/phase_08/artifacts/folds/T2_24h.json` | `2713cdf3776cd9fb9ad1e761e33df17151d3e5e73c701305e7087d29db24457a` |
| `audits/predictive-intelligence/phase_08/evidence/determinism.json` | `eb83e58e40db533e4521a3c48fc5f1a426539bda962a4bf8a66cd5699bee7c91` |
| `audits/predictive-intelligence/phase_08/evidence/folds.json` | `f30a35127c31a319db486d4e33ef3356cf567ec22c1a033db6aad073b917edb7` |
| `audits/predictive-intelligence/phase_08/evidence/logit_solver_diagnosis.json` | `bca2f41b8168d9179396f4a2f37bf4e66656da0bb6b07c0084454f7967591a27` |
| `audits/predictive-intelligence/phase_08/evidence/mutation_technical.json` | `c548b02afc7c183363eb5b1b3772d452cd800fa4ce15e95a97659e9121016dd9` |
| `audits/predictive-intelligence/phase_08/evidence/phase07_equality.json` | `c9169da7ef0a0271061bc8a9000ab96f4cc4b3bd412bc19dbc7fc853008f851b` |
| `audits/predictive-intelligence/phase_08/evidence/run_log.json` | `088778594bd437f03be5251db4f038dce94d5db8d053905f8806f396b790e975` |
| `audits/predictive-intelligence/phase_08/evidence/runner_exit_check.json` | `2ca5f239e220fdbc7a1f3c66bf16d98dacd8ee0fb4c7e0cb172b64d8f58eaed5` |
| `audits/predictive-intelligence/phase_08/evidence/serialization_smoke.json` | `f91cbd57e37c3670a6de8ce74afc416b7249d702afdb9706162fb87825b516a4` |
| `audits/predictive-intelligence/phase_08/evidence/sklearn_crosscheck.json` | `78d14cbc635914bde85fa77aa4e1db851a8b533ebb1e4d37700531f1c1988ef3` |
| `audits/predictive-intelligence/phase_08/evidence/trace/FORECAST_TRACE.json` | `539e97695d58b94c4a2e1c8b9d03a62f8ce9ddc4e633c2f24c405d176c6a8adc` |
| `audits/predictive-intelligence/phase_08/evidence/trace/FORECAST_TRACE.md` | `fbf9fd0d4147dd793fd9af2a3fd10a15c95f565aa5482f60dcb03759e522628c` |
| `audits/predictive-intelligence/phase_08/evidence/trace/second/FORECAST_TRACE.json` | `ab85bfedd3d896547f37c8b03270e89d8d8bef9789d410b65d422c5188423d65` |
| `audits/predictive-intelligence/phase_08/evidence/trace/second/FORECAST_TRACE.md` | `eb5589fb5fffa8ec3e76c27260557a92be44a4a5604e4230f469d7c2c5795468` |
| `audits/predictive-intelligence/phase_08/evidence/trace/second/verify_trace.json` | `7b3c0d7076d385e174f025f833f51eed7dd1f7348743d13ee65d1e9a5b684cb6` |
| `audits/predictive-intelligence/phase_08/evidence/trace/verify_trace.json` | `017dd92cf1888d3fb62940bf16528564c786a6d721b1a8d441f65539a836ffe2` |
| `audits/predictive-intelligence/phase_08/evidence/traps.json` | `c0b8e8c7027cfe6a7ddd2d994084234c5bede5f4304a48f1cb50a0cc76b6f921` |
| `audits/predictive-intelligence/phase_08/evidence/unavailable_candles.json` | `69196e18a2c75a371ce3ee038ce91d3cc9fbe181bd76e36fa79c994df19e4ebd` |
| `audits/predictive-intelligence/phase_08/evidence/v2_consistency.json` | `027c4dc2c06933e43e81966bcccc3900c6c7ec6629a406d26504a898adc59949` |
| `audits/predictive-intelligence/phase_08/evidence/young_pools.json` | `a4b06e68b8f69186ce139a30c040dd47d5d1ebeef8a3ea188f9ab84a69cc825a` |
| `audits/predictive-intelligence/phase_08/experiments/ABLATIONS.csv` | `5a87ea3e52ad01c107facc263d2332731dfc8acf525d04dac938860db815fe20` |
| `audits/predictive-intelligence/phase_08/experiments/EXPERIMENT_REGISTRY.csv` | `e7d2048664c3ee28f763d8e7a7df66a3f4f5800385d8faca502c62ffc5eee6f4` |
| `audits/predictive-intelligence/phase_08/experiments/HIT_MISS_COHORTS.csv` | `9b5806de6a97b83093581ececdff76a057a14933d53b5a384fa532644cea1e3d` |
| `audits/predictive-intelligence/phase_08/experiments/NC1T_SEEDS.csv` | `9d34aca23704446ef3860addea76ee97360e0402a5c93f56ded168c9de5be3b5` |
| `audits/predictive-intelligence/phase_08/experiments/OOS_PREDICTIONS.csv` | `26366297dab3b8b3c5624f1077d1857bea98c5c4fa590a40c49b2ee932ec5b09` |
| `audits/predictive-intelligence/phase_08/experiments/SEARCH_LEDGER.csv` | `0771137e6a5fea0077bcd0dde476a1af9c7b521b2a5257c4832dbf3cc5c36389` |
| `audits/predictive-intelligence/phase_08/experiments/TECHNICAL_METRICS.csv` | `3b2ff0d9ac1ca8811e7b4101769099a3fc3bd8ab9d4f6c8f14cefd3aad6e12b9` |
| `audits/predictive-intelligence/phase_08/experiments/TECH_COVERAGE.csv` | `91dfe36cd2df08f015cabd2adb27b9f0cc145b0ffe16e5c7bd99bcf699964e87` |
| `audits/predictive-intelligence/phase_08/experiments/TECH_FEATURES_DEVELOPMENT.csv` | `264052ededc81d8aba426f16bf4a3f85a3dc36ee2525d80b4f0d10c8877b1e0b` |
| `audits/predictive-intelligence/phase_08/models/TECHNICAL_MODEL_CARD.md` | `7de49fd8cd03d35a60a1fc1fb77700f3cb0da8859d46c1eeddfd497536dc04ba` |
| `audits/predictive-intelligence/phase_08/postcommit/pytest_summary.txt` | `a05d46b445f060adf925beb94a93b03d17892be0974d7ab05d5b95965b188b87` |
| `audits/predictive-intelligence/phase_08/postcommit/release_audit_history.summary.txt` | `8ab707b934d444e046e034d4440d0c4f37f4d019510965e57291a7920c13bfb8` |
| `audits/predictive-intelligence/phase_08/postcommit/seal_check.json` | `6dde396517fd7335c3d056f69995d848a05b106776668a3c3e1ecef22f708c2d` |
| `audits/predictive-intelligence/phase_08/postcommit/social_guard.out.txt` | `65ef17a84f4147ebf9f20004c35973272ef6b04c2696806a055c17804042084c` |
| `audits/predictive-intelligence/phase_08/probes/logit_solver_diagnosis.py` | `d0ba468be5cd142f9d7d2e0fef3835a6053e1533a873fcb863549f46a38d1369` |
| `audits/predictive-intelligence/phase_08/probes/mutation_technical.py` | `263c8ca59f61b0cb205161179341d607655fef3104575d4077efcb77131d8328` |
| `audits/predictive-intelligence/phase_08/probes/run_technical.py` | `378d1e5d29cd377ac95e4f68ead082dd3aca50b1650f69745173f232b9637e3d` |
| `audits/predictive-intelligence/phase_08/probes/sklearn_crosscheck_tech.py` | `1df176049c12c9cd018992d9ee082185bc5df1e846da09865d011cefa22e42dc` |
| `audits/predictive-intelligence/phase_08/probes/verify_trace.py` | `073b83a0aab67e1720c3ddf3d104f10bd31d7e2ebbd1d4099a30ff32c621589e` |
| `audits/predictive-intelligence/phase_08/probes/write_results.py` | `8bb699cdc954b2ad1e4bdaa8fedc9a93e2365ec48aedcbc8ff0e73144cbb1e28` |
| `audits/predictive-intelligence/phase_08/probes/young_pools.py` | `e73ec751f1b5b3a06b0241577da427a5c63ba98a52912c9e3f705097760b115d` |
| `audits/predictive-intelligence/phase_08/skeptic/PHASE_08_SKEPTIC.md` | `845d09e286c733977f5e15d488d2c9e7974f57c5bb519ab30aaaa0434d7c9872` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_counterexample.py` | `c6bae09a68c5ccd883022a720187c02a2ece3889197a07e283768cd10bd0d0e1` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_counterexample_out.json` | `6b92e2b01f52f1778873caa1354a0354d5d1290bb1615fd086af03b163e5d711` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_independent.py` | `9fd612a30899c005427b0e39fff0cbd28aefb89eb6a5d83f776248a26b276a1a` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_independent_out.json` | `6bc82428b2cfae6aba0ba5c13a95ff55fc5296d9d2b70147974e9321ca99d0ce` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_lbfgs_check.py` | `4cbe812656e3d944cae84316fcdf939058dd76cfa3c639eae1387c32e4228cf7` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_lbfgs_check_out.json` | `8afb418922853af6977ff3899e10469b282d31c2a02dd800161e728202f5823a` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_own_mutations.json` | `ce98b77782055556993347d70c3d6c38ab6d3f53305db5d2c10dbbd05fef136b` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_own_mutations.py` | `2971bd8def436c815e94a7c60897456b052b3c2124c65696f1dfbc1414b1f074` |
| `audits/predictive-intelligence/phase_08/skeptic/p08_p06t_check.py` | `0874564626835f31fbf88c7bb7d3cbdc503a955c8707439da53e3512537775e0` |
| `memelab/predictive/technical.py` | `cf84a7ab499e1f47665ad0b7141ffece18557a145eaea6b02c709e9ff495040f` |
| `tests/test_predictive_technical.py` | `0efccdeb38361f35c79a053239479df1409c09b855bb3d6b27263eb2f4527a08` |
<!-- artifacts:end -->

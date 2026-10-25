# Phase 07 evidence: transparent baselines

Status: PASS after repair pass 2 (the orchestrator's independent skeptic folded in, PI-D-049), PROVISIONAL: every result is PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046) because Phase 06's frozen 48 h revision re-read has not run, and no output here claims it. If the re-read changes a development label, the pipeline is rerun at the repair code `f977aab` and its outputs supersede these.

| Item | Value |
|---|---|
| Branch | `feature/predictive-intelligence` |
| HEAD before | `b0275c6dd0434a8d8e62d60de77821a7175a1ec9` (Phase 06 records, pushed) |
| Pre-registration commit | `74183c93807e39bdb315b6308bff7bf43abd6d38`, 2026-10-25T19:51:19Z: `ACCEPTANCE_CHECKLIST.md`, `experiments/EXPERIMENT_REGISTRY.csv` (87 rows), PI-D-046, PI-D-047 |
| Frozen code commit | `667244731771386df74290ffa8afd16a14ec4393`, 2026-10-25T20:05:44Z: `stats.py`, `baselines.py`, tests, probes |
| Recorded run | 2026-10-25T20:05:50Z to 20:06:18Z at HEAD `6672447` (`evidence/run_log.json`) |
| Outputs commit | `ccee7ad4188bd52dff70476fbb31eca84ae75863`, 2026-10-25T20:14:19Z (outputs, cards, spec, evidence, PI-D-048, records); a records commit on top adds the post-commit results |
| Entry-gate exception | Phase 06 NEEDS_REVIEW (48 h re-read open); Phase 07 runs on Elving's instruction of 2026-10-25 15:40 New York time (PI-D-046) |

## Entry gate (re-run here)

| Check | Command | Exit | Result |
|---|---|---|---|
| Package checksums | `sha256sum -c SHA256SUMS.txt` in the package folder | 0 | all OK |
| Full suite at `b0275c6` | `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 1124 passed in 220.79s`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known, clock dependent); stray `data/reports/20261025_1942_BRETT_0x532f.md` removed by hand |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []`, holdout labels `e695500d...`, seal `d5059bae...`, SEAL.json `f362ca12...` (equal to PI-D-045) |

## Sources read

Package (read-only, checksums OK): START_HERE, EXECUTION_RULES, PHASE_INDEX, ORCHESTRATOR, `phases/PHASE_07_transparent_predictive_baselines.md`, references SCIENTIFIC_VALIDATION, FORECAST_OUTPUT_SCHEMA, NO_GO_DECISION_TREE, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT. Records: HANDOFF, ROADMAP, EXECUTION, ORCHESTRATION, DECISIONS (all PI-D entries). Phase 01 `architecture/ACCEPTANCE_METRICS.md` (frozen block), Phase 04 `adoption/BAKEOFF.md`, `BAKEOFF_RESULTS.json` (approach names only, for the search ledger), `prototypes/core_numpy.py` and `prototypes/test_core_numpy.py`, Phase 05 `data/FEATURE_STORE_CONTRACT.md`, Phase 06 labels and gate (`memelab/predictive/labels.py`). `origin/feature/backtesting` at `12f278b` (fetched 2026-10-25): `memelab/backtest/strategies/baselines.py`, `outcomes.py`, `sources/gecko.py`, `validation.py`, `strategies/labstatus.py`, and a search for Brier, log loss, prevalence, logistic and calibration; finding recorded as PI-D-047 (no duplicate baseline, loader or outcome ledger; nothing imported). No web source was needed; no vendor call was made.

## Commands and exit codes (first pass)

| Step | Command | Exit | Result |
|---|---|---|---|
| New tests | `python -m pytest tests/test_predictive_stats.py tests/test_predictive_baselines.py -q -p no:cacheprovider` | 0 | `43 passed` (20 stats, 23 baselines) |
| All predictive tests | `python -m pytest tests/test_predictive_*.py -q -p no:cacheprovider` | 0 | `382 passed` |
| Recorded run | `python -B audits/predictive-intelligence/phase_07/probes/run_baselines.py audits/predictive-intelligence/phase_07 --npz <scratchpad>/p07_arrays.npz` | 0 | 32 output files, 0 socket events, both stores' sha256 unchanged (`run_log.json`), wall 28.1 s, CPU 26.9 s, peak RSS 71.5 MB |
| Determinism | the same runner into `<scratchpad>/p07_run2` | 0 | all 32 generated files identical by sha256 (`evidence/determinism.json`) |
| Oracle | `/home/claude/pi_research/venvs/p04_bundle/bin/python -B audits/predictive-intelligence/phase_07/probes/sklearn_crosscheck.py <npz> evidence/sklearn_crosscheck.json` | 0 | scikit-learn 1.9.1, numpy 2.5.3: coefficients within 3.03e-7, probabilities within 1.09e-7 over 9 real fold designs; Brier, log loss, AUC, AP within 5.6e-17; ties within 1.1e-16 over 50 cases |
| Mutations | `python -B audits/predictive-intelligence/phase_07/probes/mutation_baselines.py evidence/mutation_baselines.json` | 0 | 29 of 29 mutations caught (clean exit 0) |
| Full suite before the outputs commit | `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 1167 passed in 169.21s`, the known failure only; the stray `data/reports/20261025_2008_BRETT_0x532f.md` removed by hand |

## Commands and exit codes (repair pass 2, code `f977aab`)

| Step | Command | Exit | Result |
|---|---|---|---|
| Phase 07 and as-of tests | `python -m pytest tests/test_predictive_stats.py tests/test_predictive_baselines.py tests/test_predictive_asof_features.py -q -p no:cacheprovider` | 0 | `81 passed` (20 stats, 34 baselines, 27 as-of features) |
| All predictive tests | `python -m pytest tests/test_predictive_*.py -q -p no:cacheprovider` | 0 | `394 passed` |
| Mutations | `python -B probes/mutation_baselines.py evidence/mutation_baselines.json` | 0 | 42 of 42 caught |
| Skeptic's mutations | `python -B skeptic/p07_mutations.py <repo> <out>` | 0 | 19 of 20 caught (redundant guard survives) |
| CX-S07 | `python -B skeptic/p07_counterexample.py <repo>` | 1 | verdict INSUFFICIENT_EVENTS (exit 1 means not awarded) |
| Rerun | `python -B probes/run_baselines.py audits/predictive-intelligence/phase_07 --npz <scratch>` and a second run into the scratchpad | 0 | 33 of 33 generated files identical; stores unchanged; 0 socket events |
| Oracle | `sklearn_crosscheck.py` | 0 | unchanged (coefficients 3.0e-7, metrics 5.6e-17) |
| m3 check | `training_view` at the holdout start, old and new code, both modes | 0 | identical rows (`evidence/m3_training_view_check.json`) |

## Checklist results

| Id | Result | Evidence |
|---|---|---|
| G1 | pass | package checksums OK |
| G2 | pass | entry suite and seal check above |
| G3 | pass | PI-D-046 and PI-D-047 in `74183c9` |
| G4 | pass | `74183c9` (19:51:19Z) precedes every fit: `stats.py` and `baselines.py` did not exist at that commit; every real-data run, debug runs included, came after it (iteration log) |
| G5 | pass | `memelab/predictive/stats.py`; all nine prototype tests ported to synthetic data plus 11 new tests (`tests/test_predictive_stats.py`); import test: numpy and standard library only |
| G6 | pass | `evidence/sklearn_crosscheck.json` (pass true) |
| G7 | pass | every fold's training rows come from `training_labels(dev, cutoff)`; WalkForwardMismatch never raised; the gate refuses the sealed and bake-off paths (runner calls `labels.refuse_sealed` and `runtime.refuse_bakeoff_labels` on both store paths first) |
| G8 | pass | `fit_all` and `predict` run `check_asof` (allowlist plus `features.validate_rows`) on every row; NC2 refused everywhere |
| G9 | pass | `evidence/folds.json`: every fold valid with the target's maturity lag; mint overlap reported (T1 4, 5, 2; T1b 2, 4, 5, 4, 5; T2 4) |
| G10 | pass | every fold and every artifact passed the gate (T1 104 to 136 events with 25 to 34 positive; T1b 180 to 224 with 23 to 26; T2 104 to 131 with 27 to 28); `test_count_gate_abstains_below_the_frozen_minimums` |
| G11 | pass (repair pass 2: count gate) | `experiments/BASELINE_METRICS.csv` (144 rows: 3 targets x 6 views x 7 baselines including B4C, and 18 NC1 summary rows), verdicts by the frozen rule; no claim on fewer than 5 days |
| G12 | pass (repair pass 2) | NC1 under the baseline rules is uninformative at this size (T1 and T2 INSUFFICIENT_DAYS, T1b INSUFFICIENT_EVENTS; mean skill -0.033, -0.033, +0.022; shuffled fits beating the real B2: 0.70, 0.00, 0.95); NC2 136 of 136 refused; NC3 8 of 8 refused |
| G13 | pass | `evidence/serialization_smoke.json`: 18 of 18 cards round trip identical, 18 of 18 tampered copies refused, `runtime.verify_artifact` on every file |
| G14 | pass | per target an ABSTAIN document is valid; the FORECAST variant is refused (`calibration_reference needs holdout_n >= 50`, and P13 because it was built on a development decision) |
| G15 | pass | determinism above; 0 socket events; stores unchanged; `git status` shows only Phase 07 files before the commit |
| G16 | pass | `test_fixture_b2_beats_b0_nc1_does_not_and_everything_says_no_real_evidence` (fixture cards carry NO_REAL_HISTORICAL_EVIDENCE) |
| G17 | pass (repair pass 2: 520 rows) | `experiments/SEARCH_LEDGER.csv`: 520 rows (108 baseline views, 18 B4C description views, 360 NC1 seed views, 26 Phase 04 bake-off configurations, 5 Phase 04 pre-fix run files, 2 Phase 07 debug runs; the traps are in `evidence/traps.json`, they are checks, not runs) |
| G18 | pass | flag untouched; `test_no_existing_module_imports_the_predictive_package` passes; no change to the score, fatal flags or any existing module |
| G19 | pass | tests named for P10, P11, P13, P20, P21, P23, P24, P38, P43, P01, P05 and CX-07 in `tests/test_predictive_baselines.py` and `tests/test_predictive_stats.py` |
| G20 | pass | post-commit section below |

## Results (key lines)

Pooled out-of-sample, ALL view, Brier skill against B0 (governing interval; full table `experiments/BASELINE_METRICS.csv`, explanation `models/BASELINE_SPEC.md`):

- T1 24 h: 3 folds, 24 events (8 positive), 3 days. B2 Brier 0.2449 against B0 0.2297, skill -0.066 (mint interval -0.246 to 0.106; day interval undefined below 5 days); B3 0.039; B4 0.070. Verdict INSUFFICIENT_DAYS for every baseline.
- T1b 6 h: 5 folds, 44 events (3 positive), 5 days. B2 Brier 0.0595 against 0.0667, skill 0.108 (day -0.022 to 0.206, mint -0.127 to 0.219, governing mint, Holm p 0.28); B1 0.004; B3 -0.097 (day -0.189 to -0.059, mint -0.493 to 0.028); B3F 0.006; B4 0.017. Verdict INSUFFICIENT_EVENTS for every baseline (44 events and 3 positives are below the frozen out-of-sample minimums of 50 and 10; first pass: NOT_DISTINGUISHABLE_FROM_BASE_RATE). AUC and AP not computed (fewer than 10 positives).
- T2 24 h: 1 fold, 8 events (1 positive), 1 day. B2 skill -0.197; verdict INSUFFICIENT_DAYS for every baseline.
- Development prevalence at 2026-10-17T00:00Z: T1 0.250 (0.185 to 0.329, n 136), T1b 0.116 (0.080 to 0.165, n 224), T2 0.214 (0.152 to 0.292, n 131).
- Engine status after Phase 07 for every target: ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED); NO_NET_TRADING_EDGE_CLAIMABLE (price-path targets, no execution data).

## Artifacts (sha256)

Every file of the phase with its sha256 at the commit that adds it (generated by `probes/write_results.py`; the results file and this file are not listed, they hold the table), plus the new code and tests.

<!-- artifacts:start -->
| Path | sha256 |
|---|---|
| `audits/predictive-intelligence/phase_07/ACCEPTANCE_CHECKLIST.md` | `32fd9d0047d5b35f605ac0eb0297eef1b5ed61e8253bffdeaa476a9fe153b5d8` |
| `audits/predictive-intelligence/phase_07/SKEPTIC_PACKET.md` | `cac49f9b2ae97720898e7a95fb1bd0772ff6674d8c179f353d86a9756a945998` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B0.json` | `d89ab4a62fba636ea6a225856f786547b2a6e5cad1668d70410509f8a64cbde0` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B1.json` | `f84066700ca67ff7c3d4ff9ae9cf2a949803cd3007d8404c9fc418cb27ed1d8c` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B2.json` | `451a38b2dbc0d65e20f676c7aeaa5ccf3486fd991222e4f89053dc44a16796f4` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B3.json` | `f9a18b45322416eced63cc038ea8070143b589ca53c56cf0b14a2d4e62668ff8` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B3F.json` | `cd28cf657ebfd7ac0909f0190bd0b882c1b80579ed6052c0d0e7538b65e21de7` |
| `audits/predictive-intelligence/phase_07/artifacts/T1_24h/B4.json` | `ea96d08e5a8372c5042db6b72b98523ad186b858e7ded1510d531af8278940ed` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B0.json` | `232f38edfb5e63c414dee5de5cc6bf5209d9484f7244c9847516c1f1bd4df06e` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B1.json` | `f8d1f830870c4ebed7748bf76b53268a6a44b1005ccb0f0bf546f81f5dae06ed` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B2.json` | `412db87d6ffb60115dbc8fd6bf717bb1de3462df077b6cbf39ff8e3aa43e461c` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B3.json` | `d4b3bbdfaec3f83a8eea1b05c0101d74bd9ab526bd22b01628cf16c68eed4acc` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B3F.json` | `cb23b7dbe791d5b85748c0e5147a742f7e6faea1ec9ecb23fdee3fd7188cf2e8` |
| `audits/predictive-intelligence/phase_07/artifacts/T1b_6h/B4.json` | `5ef325adcdcfbb125222de0d522ee0cc2726095f283f822ee238d438d9e6cbbc` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B0.json` | `ba7f22958de4c3314e6d991bd4d1f050f34ef8f10df03b2a1adf3e2acd3b7863` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B1.json` | `3431edd2bb961c0af5a4456dba9d4c0bd5fed5c01162c959ea128206a7d1ab7f` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B2.json` | `412d4bce917b2ab3619edd8f9c257ffc446603004c5eeefd25c2571dee047488` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B3.json` | `cc5d58a8b07c98b63d56dd1a8784bf6d12841519b680347f441887a41c9dc8af` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B3F.json` | `e05576ae3a74b85c51462162d9b2a76af2385ec04f284a5f15b89642091edd14` |
| `audits/predictive-intelligence/phase_07/artifacts/T2_24h/B4.json` | `0010b258c19e5ff73dd4c88ec064fc0d8094d9d41abaee9a1a72d107662200cf` |
| `audits/predictive-intelligence/phase_07/artifacts/folds/T1_24h.json` | `9394b60c3652b25f402445336ff5a70f9a29a955b0f3eab0ad400e6d6821dae4` |
| `audits/predictive-intelligence/phase_07/artifacts/folds/T1b_6h.json` | `1cc753177d4fc2b1e21304043b246583bb2dd24e84168ece0e2f2f40958b1ce4` |
| `audits/predictive-intelligence/phase_07/artifacts/folds/T2_24h.json` | `ecee1ad616143d29e4abad6d9f6be0fbb98c68af66a384e71b5863e8c0896ac8` |
| `audits/predictive-intelligence/phase_07/evidence/determinism.json` | `2a233c059b6209d081590cf59c45eaff74bb1484fbd540ec93344431ef3c4bef` |
| `audits/predictive-intelligence/phase_07/evidence/folds.json` | `7938433ba07dd7bf8f41ad491023a394f8b00a0346ae28921cbcf0ca0869bbdd` |
| `audits/predictive-intelligence/phase_07/evidence/label_sets.json` | `3fcbcbb145808f8d2d980ca948738112a0183230a94f2812e46516c2ac12cf9f` |
| `audits/predictive-intelligence/phase_07/evidence/m3_training_view_check.json` | `6d399aeea1dc7cd71f801af81ee8d6112979ef9ab6dd17cfbacd6afe91c4a4e6` |
| `audits/predictive-intelligence/phase_07/evidence/mutation_baselines.json` | `6f0b8f84974b8efae786abf8888ec49f8fc8d9d0968b5401b086261d40ed94c0` |
| `audits/predictive-intelligence/phase_07/evidence/run_log.json` | `f00fadb34c3295e40658a24b518b2345a682e6ee469dcf8c9a9460531c5fd5a3` |
| `audits/predictive-intelligence/phase_07/evidence/serialization_smoke.json` | `a056f27ee1de09eb70a261de6d342d6a86235f231f1bc085792adcdc8599e0dd` |
| `audits/predictive-intelligence/phase_07/evidence/sklearn_crosscheck.json` | `3f4bfa31ec7a03154cfa2c70314d146fa90109c5c76a47366c194a0a330b5f01` |
| `audits/predictive-intelligence/phase_07/evidence/traps.json` | `6f9518fabadba865e2c8df359688a68e67978029dbb41d3a53c11df360e2a6e3` |
| `audits/predictive-intelligence/phase_07/evidence/verdict_changes_repair2.json` | `c3f054610b43ef78a461c48add1cb49e014963dce733336374a9ecd8a8cd4332` |
| `audits/predictive-intelligence/phase_07/experiments/BASELINE_METRICS.csv` | `d3213bc450efccd2f73e7ffb4fbe51be495b1c3e569bc0983786f29def02f7ea` |
| `audits/predictive-intelligence/phase_07/experiments/CALIBRATION_BINS.csv` | `f46052f72e0c4750a8b16d6511a28e4fe7405e7967a7aceeecda588db07b0ade` |
| `audits/predictive-intelligence/phase_07/experiments/EXPERIMENT_REGISTRY.csv` | `b60c05fc3f72aab1cfe741687908c292460b17729aaea315f4c7457b829b309e` |
| `audits/predictive-intelligence/phase_07/experiments/FEATURE_COVERAGE.csv` | `40202ca7d9be8720e06428e9abe8312a6c9b8849c8884d8b8ee6e12ecf52d653` |
| `audits/predictive-intelligence/phase_07/experiments/NC1_SEEDS.csv` | `1d031379c01e8fc64d5fa4a716629d918599beb497b009a62d8b6ef822ebfa3e` |
| `audits/predictive-intelligence/phase_07/experiments/OOS_COHORTS.csv` | `4dd1e59a6e99f55c53f9b23cdb7bb8f85cc95eb9da7bcd1be67439cc317f9ee7` |
| `audits/predictive-intelligence/phase_07/experiments/OOS_PREDICTIONS.csv` | `c2130761d983745e81ebbee112f49b680a3ab8a1535eb7e748868c5604ca2fca` |
| `audits/predictive-intelligence/phase_07/experiments/SEARCH_LEDGER.csv` | `d29c1ad01a678580850bbcc01737b410a313b78f0fcc16421f3dd776be7240f9` |
| `audits/predictive-intelligence/phase_07/experiments/TRAINING_PREVALENCE.csv` | `e4a2a3b33fc3983c883fc365393fcf8750f3723bcae74fb35258fd207673b248` |
| `audits/predictive-intelligence/phase_07/models/BASELINE_SPEC.md` | `d5f7037fbbe0ec18bb1b3f0cc7447eab4e1cf815515ed3c2548b6de1fc7ba1e1` |
| `audits/predictive-intelligence/phase_07/postcommit/pytest_summary.txt` | `afbcab3e36ad2bce3b9edb893dafa37b9f1f1a3d1c30409f688472ff0bcf7b64` |
| `audits/predictive-intelligence/phase_07/postcommit/release_audit_history.summary.txt` | `a1848ae10a5741c49190a491c3a446e38b826a803ac3ccc8cf26fb9aea559e05` |
| `audits/predictive-intelligence/phase_07/postcommit/seal_check.json` | `6dde396517fd7335c3d056f69995d848a05b106776668a3c3e1ecef22f708c2d` |
| `audits/predictive-intelligence/phase_07/postcommit/social_guard.out.txt` | `b47fdc90c55036ed6e075bb975fd9ed5679306efd8c39033b5be7d785b57eb4b` |
| `audits/predictive-intelligence/phase_07/probes/mutation_baselines.py` | `8d547483a0d1c2fd0249db851d522ae8840b899bd562b09f3aa50629624a6df1` |
| `audits/predictive-intelligence/phase_07/probes/run_baselines.py` | `300af6e9f3764ce0ea5361f00e8a7809bdaefb56f5714bb1643336c787a92bff` |
| `audits/predictive-intelligence/phase_07/probes/sklearn_crosscheck.py` | `4e59764ad6c099537e024a21abbb1fd015cfa32658ad4f26826ddf50903ae97d` |
| `audits/predictive-intelligence/phase_07/probes/write_results.py` | `5f82187b5e0649c28d630466a265480d526f40628215033f675bf9df088ade1e` |
| `audits/predictive-intelligence/phase_07/skeptic/PHASE_07_SKEPTIC.md` | `c5eed75f7067b53ac4b50c8e5688b9b3b66c3341e215e019e4b8e6cf61944332` |
| `audits/predictive-intelligence/phase_07/skeptic/PHASE_07_mutations.json` | `c8f92ea35a9d52de13d32113db8831c42d11d1d7281cc0128f46fe76e0bd1b2c` |
| `audits/predictive-intelligence/phase_07/skeptic/PHASE_07_mutations_after_repair2.json` | `480a5539391ae61fcb151bdf6442d6e743666903a370636d0d3dafb74f20a6f0` |
| `audits/predictive-intelligence/phase_07/skeptic/p07_counterexample.py` | `ebb38bf502ca3792206b0947f4ca53784775783e16d860b5b874b295bcf278b8` |
| `audits/predictive-intelligence/phase_07/skeptic/p07_independent.py` | `0cb187b37bcc4dbe5174ec4bbf671f7499709fcff7ab3e5c521eff3b12f00aa7` |
| `audits/predictive-intelligence/phase_07/skeptic/p07_mutations.py` | `ea30b0c6b9157af30d4cee7f5967cb54b13afc1b05f95cb8feac87b6e2e7a1fd` |
| `memelab/predictive/stats.py` | `e249d9d99e0d69e3f55d80e9a3d42b3a4efaf44c6488c04c4f318d576895096a` |
| `memelab/predictive/baselines.py` | `3be1306a4137b7db6bdffac9541278c1703843fe1ccb75c58b99be35d6858b71` |
| `tests/test_predictive_stats.py` | `666085f4facb54ddfe3d33c5bf1703a808946f28289484d3fd6b65d53eb8a2af` |
| `tests/test_predictive_baselines.py` | `488d40c57a955807a03317b406dc1aacea97379ceb5108d7745fff6ff077b51b` |
<!-- artifacts:end -->

## Iteration log (bounded loop)

Pass 1 (this pass):

1. INSPECT: read the package, records and code; wrote and committed the checklist and the experiment registry (`74183c9`) before writing any baseline code.
2. DO: wrote `stats.py` (port plus additions) and `baselines.py`; ran a synthetic smoke (seeded fixture, no real label); wrote the runner.
3. CHECK, with disclosure: between `74183c9` and `6672447` the runner was run twice on the real development data at 200 bootstrap replicates into the scratchpad (debugging), and its tables were looked at. Changes made after those debug runs, none to a baseline definition, setting, seed, split or verdict threshold: (a) NC1 evaluations skip the bootstrap (speed; NC1 was never pre-registered with intervals); (b) the Holm convention was changed from "leave undefined tests out of the family" to "count an undefined test as p = 1 in the family of three" (more conservative; it raised T1b B2's Holm p from about 0.09 to 0.28; no verdict changed, all were already NOT_DISTINGUISHABLE or INSUFFICIENT_DAYS); (c) the cohort table moved into `baselines.cohort_table`; (d) the fixture evidence flag and the schema and label versions were added to the cards; (e) tests and the mutation probe (2 surviving mutations at first, negative token age and AUC ties, each closed by a new test; then 29 of 29 caught). The recorded run used the committed code.
4. ATTACK (own pass, not independent): looked for look-ahead in the join (CX-07, below), training rows past the cutoff (fit refuses, test), a gate bypass (the walk-forward index must equal the gate), contemporaneous outcomes entering a forecaster (B4C kept out of verdicts and cards), Holm anti-conservatism (fixed, item b), a day interval on too few days (UNDEFINED below 5 days), ESS above n (explained in the spec, not used for any decision), identity by letter case (test), fixture outputs without the flag (test), store writes (sha256 unchanged), network (audit hook), and claims beyond the data (verdict function, spec wording).
5. FIX AND RECHECK: items above; suite and checks rerun.

New wrong-but-plausible counterexample CX-07: a training join keyed by mint that takes the mint's newest stored feature snapshot (a natural "latest features per token" join) attaches a later decision's features, available after the label's decision, to an earlier label. On the real development labels it would affect 250 of 491 label rows. `baselines.join` and `check_identity` refuse it (decision key and decision time must match); `test_cx07_join_by_mint_with_its_latest_snapshot_is_refused` and the mutation "identity join ignores the decision time" show the check bites; `evidence/traps.json` holds the real-data count.

Independent skeptic: done (orchestrator, 2026-10-25 around 20:30Z), review and scripts in `skeptic/`. See repair pass 2 below.

Pass 2 (repair pass 2, after the independent skeptic; PI-D-049). Each finding verified first:

| Finding | Verified | Change | Caught by |
|---|---|---|---|
| M1 interval and verdict rules untested | yes: the skeptic's 20 mutations, 11 survived (9 real gaps, 2 redundant guards) | tests for the 95% percentile, wider interval governing, mint grouping, population standardisation, unseen status, log-loss clip, one-sided p at 0, B4C window, WORSE below 0, chain check | the skeptic's 20 mutations now 19 caught (`skeptic/PHASE_07_mutations_after_repair2.json`; the survivor is the redundant maturity loop in `fit_all`, which `validate_rows` also enforces); the phase's probe 42 of 42 |
| m1 and CX-S07 skill on one positive | yes: `skeptic/p07_counterexample.py` exit 0 on the first-pass code (verdict awarded) | `baselines.evaluation_gate`: the frozen out-of-sample minimums (50 events, 10 per class) behind every directional verdict, INSUFFICIENT_EVENTS below them | `test_cx_s07_one_positive_over_five_days_never_earns_a_skill_verdict` (fails on the first-pass code); the counterexample script now exits 1 (verdict INSUFFICIENT_EVENTS) |
| m2 NC1 verdicts on fewer than 5 days | yes | `baselines.nc1_verdict` with the same rules; share of shuffles beating B2 reported | `test_nc1_verdicts_follow_the_same_minimums` |
| m3 unknown availability on the read path | yes, and 362 stored values already had no availability time, all zeros from no input row | `features.training_view` refuses a value with no availability unless it is a zero from no input row; identical rows before and after in both modes (`evidence/m3_training_view_check.json`) | `tests/test_predictive_asof_features.py::test_training_view_refuses_a_value_with_no_availability_time_except_a_zero_from_no_input` |
| m4 ledger incomplete | yes | 8 rows added (2 debug runs, 5 Phase 04 pre-fix files, total 520) | ledger file |
| m5 Holm change after debug runs | disclosed already | none | |
| m6 full-clone audit hit | yes: the backtesting branch's `tools/release_audit.py` line 64 lists that path and rule as reviewed (an environment variable name, SOLTRADE_PRIVATE_KEY, D-BT-016) | evidence corrected below | |
| m7 days are export batches | yes: one decision instant per out-of-sample day | stated in the spec | |
| m8 missing-feature coverage | yes | `experiments/FEATURE_COVERAGE.csv` | |

Rerun of the frozen pipeline at the repair code `f977aab` (`python -B probes/run_baselines.py audits/predictive-intelligence/phase_07 --npz <scratch>`, exit 0; a second run into the scratchpad gives 33 of 33 files identical; oracle unchanged): no number, fold, card or prediction changed (only the verdict column and the new NC1 count columns of `BASELINE_METRICS.csv`, the NC1 seed table, the ledger and the new coverage table). Verdict changes, all toward less claim (`evidence/verdict_changes_repair2.json`, 48 rows): T1b B1, B2, B3, B3F, B4 in six views from NOT_DISTINGUISHABLE_FROM_BASE_RATE to INSUFFICIENT_EVENTS (30); NC1 from DEGRADES or FINDING to INSUFFICIENT_DAYS (12) or INSUFFICIENT_EVENTS (6). T1 and T2 baseline verdicts unchanged (INSUFFICIENT_DAYS).

## Limitations

- PROVISIONAL until the Phase 06 48 h re-read is folded in (PI-D-046); a changed development label means a full rerun.
- Development only, retrospective reconstruction (labels and candle availability in provider mode; every label was read on 2026-10-24); the cards are not as-of models for any decision before 2026-10-17.
- Out-of-sample support is tiny: 24, 44 and 8 events with 8, 3 and 1 positives over 3, 5 and 1 days; one market regime and one ISO week for T1b. The day bootstrap on 5 days is unstable (day ESS above n).
- AUC and average precision were never computable (fewer than 10 positives out of sample).
- B4 in ACCEPTANCE was worded as "at the same decision time"; the as-of form is the forecaster and the contemporaneous form is description only (PI-D-048).
- Narrative ids exist for about 8% of decisions; creator wallets for about 86%.
- NC1 on T2 has a positive mean skill (finding on 8 rows).

## Post-commit results (committed tree at `ccee7ad`)

Run by the phase agent on 2026-10-25 after the outputs commit (summaries in `postcommit/`):

- `python -m pytest tests -q -p no:cacheprovider`: exit 1, `1 failed, 1167 passed in 174.38s (0:02:54)`; the only failure is the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; the stray `data/reports/20261025_2014_BRETT_0x532f.md` was removed by hand.
- `python -m memelab social guard`: exit 0, `"violations": []`.
- `python tools/release_audit.py --history` on a single-branch clone of `feature/predictive-intelligence` (with `origin/main`): exit 0, "Needs action: no."
- The same audit on the full local clone: exit 1, one history finding in blob `acbc9c9016` (`audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt` line 42, rule key_material_field), reachable only from `origin/feature/backtesting`, which this phase fetched to read it (PI-D-047); 0 objects of it are reachable from this branch. It is a reviewed false positive on that branch: the matched string is the environment variable name SOLTRADE_PRIVATE_KEY quoted by a static scan, and that branch's own `tools/release_audit.py` (line 64) lists this path and rule as reviewed (D-BT-016); only this branch's audit lacks the entry (skeptic m6).
- `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py`: exit 0, `"problems": []`.
- `git status --short`: clean after removing the stray.

## Blockers and approvals

Blockers: none for this phase beyond the open Phase 06 item. Approvals needed: none new (no spend, no package installed into the lab, no scheduled job).

## Next eligible phase

08, with every Phase 07 result PROVISIONAL until the Phase 06 48 h re-read is folded in (PI-D-046; a changed development label means a rerun at `f977aab` before Phase 08 relies on the cards or tables).

PHASE 07: PASS (PROVISIONAL under PI-D-046). STOP.

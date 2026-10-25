# Phase 07 evidence: transparent baselines

Status: NEEDS_REVIEW (first pass complete; the orchestrator's independent skeptic is pending, PI-D-013). Every result is PROVISIONAL_PENDING_REVISION_REREAD (PI-D-046): Phase 06's frozen 48 h revision re-read has not run, and no output here claims it.

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
| G11 | pass | `experiments/BASELINE_METRICS.csv` (144 rows: 3 targets x 6 views x 7 baselines including B4C, and 18 NC1 summary rows), verdicts by the frozen rule; no claim on fewer than 5 days |
| G12 | pass with a finding | NC1 mean skill -0.033 (T1), -0.033 (T1b), +0.022 (T2, 8 rows with 1 positive: finding recorded); NC2 136 of 136 refused; NC3 8 of 8 refused |
| G13 | pass | `evidence/serialization_smoke.json`: 18 of 18 cards round trip identical, 18 of 18 tampered copies refused, `runtime.verify_artifact` on every file |
| G14 | pass | per target an ABSTAIN document is valid; the FORECAST variant is refused (`calibration_reference needs holdout_n >= 50`, and P13 because it was built on a development decision) |
| G15 | pass | determinism above; 0 socket events; stores unchanged; `git status` shows only Phase 07 files before the commit |
| G16 | pass | `test_fixture_b2_beats_b0_nc1_does_not_and_everything_says_no_real_evidence` (fixture cards carry NO_REAL_HISTORICAL_EVIDENCE) |
| G17 | pass | `experiments/SEARCH_LEDGER.csv`: 512 rows (108 baseline views, 18 B4C description views, 360 NC1 seed views, 26 Phase 04 bake-off configurations; the traps are in `evidence/traps.json`, they are checks, not runs) |
| G18 | pass | flag untouched; `test_no_existing_module_imports_the_predictive_package` passes; no change to the score, fatal flags or any existing module |
| G19 | pass | tests named for P10, P11, P13, P20, P21, P23, P24, P38, P43, P01, P05 and CX-07 in `tests/test_predictive_baselines.py` and `tests/test_predictive_stats.py` |
| G20 | pass | post-commit section below |

## Results (key lines)

Pooled out-of-sample, ALL view, Brier skill against B0 (governing interval; full table `experiments/BASELINE_METRICS.csv`, explanation `models/BASELINE_SPEC.md`):

- T1 24 h: 3 folds, 24 events (8 positive), 3 days. B2 Brier 0.2449 against B0 0.2297, skill -0.066 (mint interval -0.246 to 0.106; day interval undefined below 5 days); B3 0.039; B4 0.070. Verdict INSUFFICIENT_DAYS for every baseline.
- T1b 6 h: 5 folds, 44 events (3 positive), 5 days. B2 Brier 0.0595 against 0.0667, skill 0.108 (day -0.022 to 0.206, mint -0.127 to 0.219, governing mint, Holm p 0.28); B1 0.004; B3 -0.097 (day -0.189 to -0.059, mint -0.493 to 0.028); B3F 0.006; B4 0.017. Verdict NOT_DISTINGUISHABLE_FROM_BASE_RATE for every baseline. AUC and AP not computed (fewer than 10 positives).
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
| `audits/predictive-intelligence/phase_07/evidence/determinism.json` | `16b66250d6d15bba1cfc7fe794880302c930918cebbdea3457dc21ea59897af1` |
| `audits/predictive-intelligence/phase_07/evidence/folds.json` | `7938433ba07dd7bf8f41ad491023a394f8b00a0346ae28921cbcf0ca0869bbdd` |
| `audits/predictive-intelligence/phase_07/evidence/label_sets.json` | `3fcbcbb145808f8d2d980ca948738112a0183230a94f2812e46516c2ac12cf9f` |
| `audits/predictive-intelligence/phase_07/evidence/mutation_baselines.json` | `f5b41c664a0de0df667669af35e6071dea3d9b4e663adf37a70f066336cbefec` |
| `audits/predictive-intelligence/phase_07/evidence/run_log.json` | `633eda002cdd40448f3ada918e92a6d90fb1725d47703ba2fcbb49bf94221325` |
| `audits/predictive-intelligence/phase_07/evidence/serialization_smoke.json` | `a056f27ee1de09eb70a261de6d342d6a86235f231f1bc085792adcdc8599e0dd` |
| `audits/predictive-intelligence/phase_07/evidence/sklearn_crosscheck.json` | `3f4bfa31ec7a03154cfa2c70314d146fa90109c5c76a47366c194a0a330b5f01` |
| `audits/predictive-intelligence/phase_07/evidence/traps.json` | `6f9518fabadba865e2c8df359688a68e67978029dbb41d3a53c11df360e2a6e3` |
| `audits/predictive-intelligence/phase_07/experiments/BASELINE_METRICS.csv` | `6369e877ea68fadfac6c5b4145d877b1a6a0f08a407dd8868c6571a43c5de0bb` |
| `audits/predictive-intelligence/phase_07/experiments/CALIBRATION_BINS.csv` | `f46052f72e0c4750a8b16d6511a28e4fe7405e7967a7aceeecda588db07b0ade` |
| `audits/predictive-intelligence/phase_07/experiments/EXPERIMENT_REGISTRY.csv` | `b60c05fc3f72aab1cfe741687908c292460b17729aaea315f4c7457b829b309e` |
| `audits/predictive-intelligence/phase_07/experiments/NC1_SEEDS.csv` | `14cfd7c92cd93db71f22dd91530fbc1656442035cab7017b5dadd6332c8ee6f7` |
| `audits/predictive-intelligence/phase_07/experiments/OOS_COHORTS.csv` | `4dd1e59a6e99f55c53f9b23cdb7bb8f85cc95eb9da7bcd1be67439cc317f9ee7` |
| `audits/predictive-intelligence/phase_07/experiments/OOS_PREDICTIONS.csv` | `c2130761d983745e81ebbee112f49b680a3ab8a1535eb7e748868c5604ca2fca` |
| `audits/predictive-intelligence/phase_07/experiments/SEARCH_LEDGER.csv` | `a0e729ed1e20cdee3b3d837865b6601d3cbb618411422937506cb3e18e8b98ca` |
| `audits/predictive-intelligence/phase_07/experiments/TRAINING_PREVALENCE.csv` | `e4a2a3b33fc3983c883fc365393fcf8750f3723bcae74fb35258fd207673b248` |
| `audits/predictive-intelligence/phase_07/models/BASELINE_SPEC.md` | `d011306d0e59874ae01d87edc3eee9cf3ad44c3aabe654c5e32143950c917b65` |
| `audits/predictive-intelligence/phase_07/postcommit/pytest_summary.txt` | `afbcab3e36ad2bce3b9edb893dafa37b9f1f1a3d1c30409f688472ff0bcf7b64` |
| `audits/predictive-intelligence/phase_07/postcommit/release_audit_history.summary.txt` | `a1848ae10a5741c49190a491c3a446e38b826a803ac3ccc8cf26fb9aea559e05` |
| `audits/predictive-intelligence/phase_07/postcommit/seal_check.json` | `6dde396517fd7335c3d056f69995d848a05b106776668a3c3e1ecef22f708c2d` |
| `audits/predictive-intelligence/phase_07/postcommit/social_guard.out.txt` | `b47fdc90c55036ed6e075bb975fd9ed5679306efd8c39033b5be7d785b57eb4b` |
| `audits/predictive-intelligence/phase_07/probes/mutation_baselines.py` | `b8ad3164808af7fdde50032a2af68ba3b6fafc75395d017d0c8ff37c2efa5105` |
| `audits/predictive-intelligence/phase_07/probes/run_baselines.py` | `68381d76a250d44f4b1fb5fbb2ed52f0297063aa6154d2ccc09bd53c53163dac` |
| `audits/predictive-intelligence/phase_07/probes/sklearn_crosscheck.py` | `4e59764ad6c099537e024a21abbb1fd015cfa32658ad4f26826ddf50903ae97d` |
| `audits/predictive-intelligence/phase_07/probes/write_results.py` | `409643f8000ede99fc4f3697f93ee1c04e3ab724e3326a99fc7043ca93f479d9` |
| `memelab/predictive/stats.py` | `e249d9d99e0d69e3f55d80e9a3d42b3a4efaf44c6488c04c4f318d576895096a` |
| `memelab/predictive/baselines.py` | `9ae44a4b66753d84b1366b3bf80af7bf038397202805d319cf16b20f4b5f2399` |
| `tests/test_predictive_stats.py` | `666085f4facb54ddfe3d33c5bf1703a808946f28289484d3fd6b65d53eb8a2af` |
| `tests/test_predictive_baselines.py` | `7d1bcf3c4d8bff81bb9853942db69b732dbe9d662ddbe1a6816880e052de0c68` |
<!-- artifacts:end -->

## Iteration log (bounded loop)

Pass 1 (this pass):

1. INSPECT: read the package, records and code; wrote and committed the checklist and the experiment registry (`74183c9`) before writing any baseline code.
2. DO: wrote `stats.py` (port plus additions) and `baselines.py`; ran a synthetic smoke (seeded fixture, no real label); wrote the runner.
3. CHECK, with disclosure: between `74183c9` and `6672447` the runner was run twice on the real development data at 200 bootstrap replicates into the scratchpad (debugging), and its tables were looked at. Changes made after those debug runs, none to a baseline definition, setting, seed, split or verdict threshold: (a) NC1 evaluations skip the bootstrap (speed; NC1 was never pre-registered with intervals); (b) the Holm convention was changed from "leave undefined tests out of the family" to "count an undefined test as p = 1 in the family of three" (more conservative; it raised T1b B2's Holm p from about 0.09 to 0.28; no verdict changed, all were already NOT_DISTINGUISHABLE or INSUFFICIENT_DAYS); (c) the cohort table moved into `baselines.cohort_table`; (d) the fixture evidence flag and the schema and label versions were added to the cards; (e) tests and the mutation probe (2 surviving mutations at first, negative token age and AUC ties, each closed by a new test; then 29 of 29 caught). The recorded run used the committed code.
4. ATTACK (own pass, not independent): looked for look-ahead in the join (CX-07, below), training rows past the cutoff (fit refuses, test), a gate bypass (the walk-forward index must equal the gate), contemporaneous outcomes entering a forecaster (B4C kept out of verdicts and cards), Holm anti-conservatism (fixed, item b), a day interval on too few days (UNDEFINED below 5 days), ESS above n (explained in the spec, not used for any decision), identity by letter case (test), fixture outputs without the flag (test), store writes (sha256 unchanged), network (audit hook), and claims beyond the data (verdict function, spec wording).
5. FIX AND RECHECK: items above; suite and checks rerun.

New wrong-but-plausible counterexample CX-07: a training join keyed by mint that takes the mint's newest stored feature snapshot (a natural "latest features per token" join) attaches a later decision's features, available after the label's decision, to an earlier label. On the real development labels it would affect 250 of 491 label rows. `baselines.join` and `check_identity` refuse it (decision key and decision time must match); `test_cx07_join_by_mint_with_its_latest_snapshot_is_refused` and the mutation "identity join ignores the decision time" show the check bites; `evidence/traps.json` holds the real-data count.

Independent skeptic: pending (the orchestrator runs it with `SKEPTIC_PACKET.md`).

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
- The same audit on the full local clone: exit 1, one history finding in blob `acbc9c9016` (`audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt` line 42, rule key_material_field), reachable only from `origin/feature/backtesting`, which this phase fetched to read it (PI-D-047); 0 objects of it are reachable from this branch. As with PI-D-045 item 7, that branch's owner should review it; nothing on this branch is affected.
- `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py`: exit 0, `"problems": []`.
- `git status --short`: clean after removing the stray.

## Blockers and approvals

Blockers: none for this phase beyond the open Phase 06 item. Approvals needed: none new (no spend, no package installed into the lab, no scheduled job).

## Next eligible phase

None until the orchestrator's skeptic is folded in and the Phase 06 re-read is resolved; then Phase 08.

PHASE 07: NEEDS_REVIEW. STOP.

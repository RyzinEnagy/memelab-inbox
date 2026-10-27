# Phase 15 evidence: incremental predictive value of behavioral simulation

- Branch `feature/predictive-intelligence`; HEAD before `b0243b4` (Phase 14 TEST_ONLY, equal to origin); Phase 15 commits `b274cbc` to `3135060`, then the records commit and a post-commit record on top (hashes in `PHASE_15_RESULTS.json` and HANDOFF).
- Work 2026-10-27 from 00:41Z (entry suite) to the post-commit record. The first Phase 15 agent's session ended while it was writing the records (after `3135060`, with `SKEPTIC_PACKET.md`, `GO_NO_GO.md` and `INCREMENTAL_VALUE_RESULTS.md` uncommitted). A second agent finished the records from 01:22Z without rerunning or changing any frozen code or recorded output: it checked the three documents against the committed outputs (every number matched; one section on the named adversarial tests was added to `INCREMENTAL_VALUE_RESULTS.md`), then wrote this file, RESULTS.json and the records.
- Status: **TEST_ONLY** after repair pass 2 (PI-D-082, PI-D-083): the comparison that can be made without spend is valid and the decision conservative, but the simulation path was never tested live, so the phase cannot be a release-complete PASS. Decision: **INSUFFICIENT_VALIDATION**, **MIROFISH_NO_GO**, **RULES_NOT_PROMOTED**, unchanged by the repair. First pass NEEDS_REVIEW at `08e8670` (pushed); the independent skeptic found no material failure, 7 minor findings and CX-S15.

## Entry gate (G1, G2), at `b0243b4`

From `evidence/entry/entry_summary.json` (first agent):

| Check | Command | Exit | Result |
|---|---|---|---|
| package checksums | `sha256sum -c SHA256SUMS.txt` | 0 | 41 OK, 0 failed |
| full suite | `python -m pytest tests -q -p no:cacheprovider` (from 00:41:31Z) | 1 | `1 failed, 1807 passed, 1 skipped, 1 warning in 211.13s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261027_0041_BRETT_0x532f.md` removed by hand |
| seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| Phase 14 key tests | `python -m pytest tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py -q -p no:cacheprovider` | 0 | 211 passed, 1 skipped |
| Phase 14 seed rebuild | `python -B audits/predictive-intelligence/phase_14/probes/build_seeds.py <scratchpad>/entry_p14` | 0 | `SEEDS_DEV.jsonl` byte-equal (830 seeds, 0 refused, sha256 `a0c61817...`), no label call, no socket |

Phase 14 is TEST_ONLY, not PASS. The orchestrator admitted Phase 15 anyway (PI-D-078, restated in PI-D-081 item 1).

## Pre-registration and commit order (G3)

`git show --name-only` per commit:

| Commit | Content |
|---|---|
| `b274cbc` | `ACCEPTANCE_CHECKLIST.md`, `behavioral/EXPERIMENT_PROTOCOL.md`, `experiments/EXPERIMENT_REGISTRY.csv` (28 rows), entry evidence, PI-D-078, PI-D-079; no code |
| `9ab0160` | frozen coding code: `memelab/predictive/scenario_eval.py` (scenario-eval-1), `tests/test_predictive_scenario_eval.py` (31 tests), `probes/code_scenarios.py` |
| `7b787bf` | recorded blind coding outputs: `CODING_LOG.json`, `SCENARIO_CODING.csv`, `CONTROL_CODING.csv`, `EVENT_SET.csv`, `HOLDOUT_RULE_SCENARIOS.jsonl` |
| `0abffd5` | frozen scoring code: `probes/score_scenarios.py`, `probes/mutation_scenario_eval.py`, three tests added (34) |
| `01e535d` | first recorded scoring outputs at `0abffd5` (run 01:08:27Z to 01:08:33Z) |
| `de41d26` | change control CP15-0 (PI-D-080): scorer adds outputs only; `probes/oracle_recompute.py`; `tests/test_predictive_phase15_outputs.py` (5 tests) |
| `3135060` | repeated scoring outputs at `de41d26` (run 01:12:41Z to 01:12:48Z), `evidence/rerun_cp15_0_diff.json`, oracle and mutation evidence |

`git diff --stat 9ab0160 HEAD -- memelab/` is empty: `scenario_eval.py` is unchanged since the coding freeze. `git diff --stat b0243b4 HEAD -- inbox state data memelab/predictive/behavioral.py` is empty.

## What was built

- `memelab/predictive/scenario_eval.py`: blind mechanical coder (`check_blind`, `code_document`, `warnings_of`), file verification by committed hash, day-stratified permutation, warning metrics and gates, Holm, A_WARN (training-only warned and not-warned rates shrunk toward the training prevalence, m 20) with card verification, development selection status and the frozen decision rule `decide`. Imports: standard library, numpy, `memelab.predictive` `baselines`, `contract`, `evaluation`, `stats` only; no other `memelab` module imports it (only a `__pycache__` file names it).
- Probes in `phase_15/probes/`: `code_scenarios.py` (blind coding run; label access, sealed opens and sockets raise), `score_scenarios.py` (E1, E2, E3, controls, examples, decision, ledger), `oracle_recompute.py` (standard-library recompute), `mutation_scenario_eval.py`, `rerun_diff.py`.

## Recorded runs

- Coding at `9ab0160`, 00:59:06Z to 00:59:46Z: 830 development and 95 holdout-window documents CODED; 830 development documents recomputed equal to Phase 14's (0 differences, 0 validation errors); `label_calls` [], `forbidden_opens` [], `socket_events` []; feature store sha256 unchanged before and after; warnings T1 none, T1b 66 and 8, T2 537 and 45 (development, holdout window). Two debug runs logged (dbg1, dbg2 twin byte-equal).
- Scoring at `0abffd5` (first) and at `de41d26` (repeat): every first-run value equal; 102 keys added under the CP15-0 prefixes and three POST_OPENING ledger rows; the ledger counts that grow by three are the only changed values (`rerun_cp15_0_diff.json`, `"ok": true`); `sockets` [], `sealed_opens` []. Three scoring debug runs logged (tolerance of the restated-number check only).
- Oracle recompute: `"differences": []`, `"warning_mismatches": 0`. Mutation probe: 45 of 45 caught, survivors [] (the first probe's four survivors led to the three tests in `0abffd5`).

## Checks made while finishing the records (no rerun of a recorded step)

| Check | Command or input | Exit or result |
|---|---|---|
| coding outputs equal their logged hashes | sha256 of the four files against `CODING_LOG.json` and `INCREMENTAL_VALUE_RESULTS.json` `coding_outputs_sha256` | 4 of 4 equal |
| scoring outputs equal their logged hashes | sha256 of six files against `evidence/score_run_log.json` | 6 of 6 equal |
| ledger head | first 3,207 lines of `phase_15/experiments/SEARCH_LEDGER.csv` against `phase_13/experiments/SEARCH_LEDGER.csv` | equal; 33 Phase 15 rows after |
| Phase 15 tests | `python -m pytest tests/test_predictive_scenario_eval.py tests/test_predictive_phase15_outputs.py -q -p no:cacheprovider` | exit 0, `39 passed in 11.48s` (34 and 5) |
| Phase 14 key tests | `python -m pytest tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py -q -p no:cacheprovider` | `211 passed, 1 skipped in 27.09s` |
| documents against outputs | every number in `INCREMENTAL_VALUE_RESULTS.md` and `GO_NO_GO.md` against `INCREMENTAL_VALUE_RESULTS.json`, `CODING_LOG.json`, `SCENARIO_CODING.csv` (227 development NO_GROUNDED_SCENARIO documents) | all equal |

## Result

- Eligible independently dated catalyst events: **0** of 100 (`EVENT_SET.csv`: 925 decision snapshots with CATALYST_TABLES_NOT_EXPORTED; 27 inbox candidate items, none eligible: 1 listing state, 1 paid-boost list, 25 ticker or name searches, all read once before the first decision export).
- Comparators: A RAN; B BLOCKED_NO_APPROVED_LLM_SPEND; C NO_CALIBRATED_CLASSIFIER (uncalibrated stand-ins B2, R2_SC_RULE, S2_SC_LOGIT_B2 restated equal to Phase 10); D BLOCKED_NO_APPROVED_LLM_OR_ZEP_SPEND.
- E1 (as-of, out of sample): A_WARN INSUFFICIENT_DAYS (T1 24 rows, equal to B0; T2 8 rows) and INSUFFICIENT_EVENTS (T1b 44 rows, skill vs B0 +0.0026, interval -0.019 to 0.027, Holm 1.0); NO_UNCORRECTED_SKILL on every target.
- E2 (descriptive only): T1 NO_WARNINGS; T1b 24 warned, 4 hits, precision 0.167 against 0.116, Holm p 0.382; T2 75 warned, 22 hits, 0.293 against 0.214, Holm p 0.198; both DESCRIPTIVE_NOT_DISTINGUISHABLE. The per-label rows are noise: MANUFACTURED_ATTENTION_DUMP on T2 (raw p 0.0045) does not replicate on the opened holdout (1 hit in 14, indistinguishable from the prevalence of 0.119); ORGANIC on T1b looks favourable on the holdout (4 of 8 against 0.176) below the warning gate; ATTENTION_EXHAUSTION on T2 points the wrong way on development (2 of 32 against 0.214).
- Controls: NCB VERIFIED raw p 0.032, not flagged only through a padded Holm family of three (0.096); judged alone (repair pass 2) FLAGGED by the decision null, NOT_FLAGGED by the conservative mint-block p (0.120); NCB UNVERIFIED 426 of 426 unscorable; NCS skill 0, -0.017, -0.011; P28 830 of 830 refused for both traps.
- E3 (POST_OPENING): NO_UNCORRECTED_SKILL on every target; sealed folder not opened.
- Cost 0 USD, 0 LLM calls, no socket. Ledger N_search 118 to 121 (primary); sensitivity 160 (121 plus 39 rule and description configurations).
- Decision by `scenario_eval.decide`: validation INSUFFICIENT_VALIDATION, MiroFish MIROFISH_NO_GO, rules RULES_NOT_PROMOTED, reasons ELIGIBLE_EVENTS_BELOW_100, D_NOT_RUN, B_NOT_RUN; no probability, no live capability.

Details: `behavioral/INCREMENTAL_VALUE_RESULTS.md`, `behavioral/GO_NO_GO.md`.

## Gate items

| Item | Status | Evidence |
|---|---|---|
| G1 checksums | holds | entry table |
| G2 entry gate | holds | entry table; Phase 14 TEST_ONLY admitted by PI-D-078 |
| G3 order | holds | commit table |
| G4 isolation | holds | imports listed above; `test_scenario_eval_imports_numpy_stdlib_and_lab_predictive_modules_only`, `test_no_other_memelab_module_imports_scenario_eval` |
| G5 event count | holds | `EVENT_SET.csv`, N = 0 against 100 |
| G6 blind coding | holds | `CODING_LOG.json` (no label call, open or socket); coding committed in `7b787bf` before the scoring code; `test_verify_file_refuses_a_file_that_is_not_the_committed_one`, `test_coding_was_committed_before_the_scoring_code_and_outputs` |
| G7 coding rules | holds | tests for each rule in `test_predictive_scenario_eval.py`; `test_the_mirofish_probe_outputs_of_phase_14_are_not_codable` |
| G8 rules reproduce | holds | 830 documents equal to Phase 14's; twin coding runs byte-equal (debug dbg1 and dbg2, commit message `7b787bf`) |
| G9 label join | holds | E2 labelled counts 136, 224, 131; `test_fit_warn_refuses_rows_not_decided_before_and_matured_by_the_cutoff` |
| G10 E1 | holds | `E1`, `E1_restated_equal_to_phase10` all equal |
| G11 E2 | holds | permutation seed 20261025, 2000 reps; `test_permutation_is_within_day_and_reproducible` |
| G12 controls | holds | `controls`, `controls_coding` |
| G13 E3 | holds | `POST_OPENING_LOG.json`, `conservative_status` per target |
| G14 not compared | holds | `not_compared`; adversarial-test table in `INCREMENTAL_VALUE_RESULTS.md` |
| G15 examples | holds | `examples`, from the frozen rule (protocol 9) |
| G16 decision | holds | `decision`; tests for the no-event branch, the GO-candidate fixture and every NO_GO reason |
| G17 tests bite | holds | 45 of 45 |
| G18 ledger | holds (closed by a recorded mapping in repair pass 2) | Phase 13 rows unchanged; totals equal `ledger_totals`. `experiments/REGISTRY_LEDGER_MAP.csv` maps all 47 registry rows (28 plus 19 of the addition): 41 to the same ledger id, 6 non-configuration rows (COUNT, BLIND_CODING x2, NOT_RUN x2, DECISION) to the record that holds them; and all 53 Phase 15 ledger rows (33 plus 20): 41 to the same registry id, 3 A_WARN_H_POST_OPENING to protocol 6, 3 per-label POST_OPENING to PI-D-080, 6 debug runs as logged runs (test `test_registry_and_ledger_map_covers_both_directions`) |
| G19 deliverables | holds after this commit | the five named files, this file, RESULTS.json, skeptic packet, ROADMAP, DECISIONS (PI-D-081), HANDOFF |
| G20 post-commit | recorded below | `postcommit/` (first pass and repair pass 2) |

## Iteration log (bounded loop, not independent)

1. Pass 1, coding: two debug runs at uncommitted code (dbg1; dbg2 twin byte-equal), freeze `9ab0160`, recorded run `7b787bf`.
2. Pass 2, scoring: three debug runs (tolerance of the restated Phase 10 numbers from 5e-7 to 1e-5, because the Phase 10 CSV holds 6 decimals; no rule or verdict changed); first mutation probe left four survivors, three tests added; freeze `0abffd5`; recorded run `01e535d`.
3. Pass 3, self-review CP15-0 (PI-D-080): per-label holdout descriptions and independence counts added so the one tempting development subgroup is never shown without its holdout counterpart and the effective sample is visible; oracle probe and output tests; freeze `de41d26`; repeated run `3135060`, every first-run value equal.
4. Pass 4, records (second agent after the first session ended): documents checked against the outputs, adversarial-test table added, records written; no code or output changed.

## Own adversarial pass (not independent; the orchestrator's skeptic follows)

- CX-15 (named in the checklist before any code): a scorer that counts a bogus planted catalyst's statements as hits when T1 is positive and reports recall as accuracy. Caught: precision is always shown with the prevalence of the same rows and the day-stratified permutation; NCB VERIFIED reaches recall 0.588 and raw p 0.032 but is not flagged after Holm (0.096); recall is printed beside coverage (0.478).
- The bogus control's raw p below 0.05 shows that raw permutation p values on this sample are not evidence on their own.
- The T2 subgroup MANUFACTURED_ATTENTION_DUMP reads `sc_attention_suspect`, the input Phase 10's R2 and S models already used; it does not replicate on the holdout.
- The permutation exchanges decisions, not mints: T1b has 96 rows sharing a mint and a day, so its p values are optimistic; none is used for a verdict.

## Artifacts

Full sha256 digests in `PHASE_15_RESULTS.json`.

## Skeptic

The orchestrator's independent skeptic reviewed `08e8670` (`skeptic/PHASE_15_SKEPTIC.md`, scripts beside it): no material failure; the decision reproduced; coding and scoring reruns byte-equal; own A_WARN, E2 and E3 recomputes equal; 7 minor findings (m1 to m7) and the counterexample **CX-S15**: an outcome-independent warning assigned per mint, scored with the frozen decision-level permutation, rejects at p < 0.05 (either side) in 13.6% of 1,000 salts on T1b against 5.4% for the same warning assigned per decision (one-sided up to 7.3%). Nothing in the first pass caught it, because the bogus control was planted per decision.

What catches CX-S15 now: `tests/test_predictive_scenario_eval.py::test_cx_s15_mint_planted_null_warnings_fool_the_decision_null_not_the_mint_block_null` (fails on the first-pass code: the mint-block null does not exist there), and on the real data the recorded calibration check in `behavioral/MINT_CLUSTERED_NULL.json` with `tests/test_predictive_phase15_outputs.py::test_mint_clustered_null_addition_is_more_conservative_and_calibrated` (fails on the first-pass outputs: the file does not exist). The decision-level null exceeds its bound on T1b (p down share 0.0975 against 0.0718 at 400 salts), which reproduces CX-S15; the conservative p holds on every target.

## Post-commit at the first-pass records commit `cda97c3`

| Check | Command | Exit | Result |
|---|---|---|---|
| full suite | `python -m pytest tests -q -p no:cacheprovider` (from 01:26:34Z) | 1 | `1 failed, 1846 passed, 1 skipped, 1 warning in 292.16s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (1807 at entry plus the 39 Phase 15 tests); strays `data/reports/20261027_0126_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand |
| social guard | `python -m memelab social guard` | 0 | `"violations": []`, 2,440 files scanned |
| seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| release audit | `python tools/release_audit.py --history` on a single-branch clone at `cda97c3` | 0 | "Needs action: no." |

Files: `postcommit/pytest_summary.txt`, `social_guard.out.txt`, `seal_check.json`, `release_audit_history.summary.txt`. `git status` clean after the follow-up commit that records them.

## Repair pass 2 (after the independent skeptic, PI-D-082, PI-D-083)

Every finding was checked against the code first: the skeptic's CX-S15 output and own-mutation results were read, and a scratchpad prototype on a synthetic clustered fixture showed the same pattern before any repair code was written.

| Finding | What was done | Where |
|---|---|---|
| m1, CX-S15 (decision null optimistic for mint-level warnings) | mint-block nulls (`mint_block_permutation`, `clustered_metrics`; conservative p = largest of the decision, mint-within-day and whole-sample p), recorded as an addition beside the frozen outputs; calibration on 400 per-mint salts per target; unit test on a synthetic clustered fixture | `behavioral/MINT_CLUSTERED_NULL.json`, `probes/mint_null.py` |
| m2 (NCB passes through a padded Holm family) | controls judged as single tests (`control_own_level`); the recorded control is FLAGGED by the decision null and NOT_FLAGGED by the conservative p; a per-mint bogus control on each target is NOT_FLAGGED by both | same file; prose in `INCREMENTAL_VALUE_RESULTS.md` |
| m3 (blindness guard narrower than the wording) | blinding basis stated as it is (code path, seed contents, equality with Phase 14's documents; the guard does not block the Phase 05 feature store or the lab DB) | `INCREMENTAL_VALUE_RESULTS.md`, PI-D-082 item 7 |
| m4 (one-sided subgroup prose) | "does not replicate" instead of "reverses"; ORGANIC 4 of 8 on the holdout and ATTENTION_EXHAUSTION 2 of 32 on development named, all three as noise | `INCREMENTAL_VALUE_RESULTS.md`, `GO_NO_GO.md`, this file, ROADMAP |
| m5 (three surviving mutations; order test passes on a shallow tree) | tests for X2, X3, X13; the order test checks `--is-shallow-repository` and the pinned commits and fails on a depth-1 clone (checked); mutation probe 56 of 56; the skeptic's own 14 mutations rerun: 14 of 14 caught | `evidence/mutation_scenario_eval_rp2.json`, `skeptic/rp2_own_mutations_recheck.json` |
| m6 (RULES_CANDIDATE unreachable; sensitivity N not stated) | N_search primary 121 and sensitivity 160 stated; the scorer's missing max-T p is stricter than protocol 6 and is left, carried to any later phase that could promote a rule | `MINT_CLUSTERED_NULL.json` `n_search`, PI-D-082 item 5 |
| m7 and G18 (registry and ledger gaps both ways) | recorded mapping in both directions, with an output test | `experiments/REGISTRY_LEDGER_MAP.csv` |

Commits: repair code `869d597` (frozen before the recorded run of the addition; one debug run logged, `P15:DEBUG:RP2:0`), recorded addition `aea95f0`, records on top.

| Check at `869d597` | Command | Exit | Result |
|---|---|---|---|
| addition | `python -B audits/predictive-intelligence/phase_15/probes/mint_null.py audits/predictive-intelligence/phase_15` (02:14:36Z to 02:16:50Z) | 0 | every decision-level p equal to the recorded one; no socket, no sealed open |
| twin | same into the scratchpad | 0 | three outputs byte-equal; log differs only in `end_utc` |
| coding repeated | `python -B .../probes/code_scenarios.py <scratchpad>/rp2c` | 0 | four coding outputs byte-equal; log differs only in times and head |
| scoring repeated | `python -B .../probes/score_scenarios.py <scratchpad>/rp2s` | 0 | six scoring outputs byte-equal; log differs only in times and head |
| comparison | `python -B .../probes/rerun_rp2_diff.py <rp2c> <rp2s> <twin> .../evidence/rerun_rp2_diff.json` | 0 | `"ok": true` |
| mutation probe | `python -B .../probes/mutation_scenario_eval.py .../evidence/mutation_scenario_eval_rp2.json` | 0 | 56 of 56 caught |
| skeptic's own mutations | `python -I .../skeptic/p15_own_mutations.py /home/claude/memelab-inbox <scratchpad>/sk_own_mut_rp2.json` | 0 | 14 of 14 caught (first pass: 11) |
| Phase 15 tests | `python -m pytest tests/test_predictive_scenario_eval.py tests/test_predictive_phase15_outputs.py -q -p no:cacheprovider` | 0 | 46 passed (39 and 7) |
| shallow clone | the order test on a `--depth 1` clone | 1 | fails as intended |

No number, verdict or decision changed. The only status change is NEEDS_REVIEW to TEST_ONLY.

Disagreements with the skeptic: none on substance. One precision: CX-S15's 13.6% is the either-side share against a nominal 10% for two one-sided tests at 0.05; the one-sided shares (7.3% up, 6.3% down at 1,000 salts) are the inflation against 5%. Both readings show the decision null is optimistic; the conclusion is the same.

## Post-commit at the repair pass 2 records commit `e59d9d9`

| Check | Command | Exit | Result |
|---|---|---|---|
| full suite | `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 1853 passed, 1 skipped, 1 warning in 267.69s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (1846 plus the 7 repair tests); strays `data/reports/20261027_0225_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand |
| social guard | `python -m memelab social guard` | 0 | `"violations": []`, 2,461 files scanned |
| seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| release audit | `python tools/release_audit.py --history` on a single-branch clone at `e59d9d9` | 0 | "Needs action: no." |

Files: `postcommit/rp2_pytest_summary.txt`, `rp2_social_guard.out.txt`, `rp2_seal_check.json`, `rp2_release_audit_history.summary.txt`. `git status` clean after the follow-up commit that records them.

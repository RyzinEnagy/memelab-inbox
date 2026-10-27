# Phase 15 evidence: incremental predictive value of behavioral simulation

- Branch `feature/predictive-intelligence`; HEAD before `b0243b4` (Phase 14 TEST_ONLY, equal to origin); Phase 15 commits `b274cbc` to `3135060`, then the records commit and a post-commit record on top (hashes in `PHASE_15_RESULTS.json` and HANDOFF).
- Work 2026-10-27 from 00:41Z (entry suite) to the post-commit record. The first Phase 15 agent's session ended while it was writing the records (after `3135060`, with `SKEPTIC_PACKET.md`, `GO_NO_GO.md` and `INCREMENTAL_VALUE_RESULTS.md` uncommitted). A second agent finished the records from 01:22Z without rerunning or changing any frozen code or recorded output: it checked the three documents against the committed outputs (every number matched; one section on the named adversarial tests was added to `INCREMENTAL_VALUE_RESULTS.md`), then wrote this file, RESULTS.json and the records.
- Status: **NEEDS_REVIEW**, pending the orchestrator's independent skeptic. Decision: **INSUFFICIENT_VALIDATION**, **MIROFISH_NO_GO**, **RULES_NOT_PROMOTED**. Expected status after review: TEST_ONLY (checklist status rule, protocol 12, PI-D-078).

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
- E2 (descriptive only): T1 NO_WARNINGS; T1b 24 warned, 4 hits, precision 0.167 against 0.116, Holm p 0.382; T2 75 warned, 22 hits, 0.293 against 0.214, Holm p 0.198; both DESCRIPTIVE_NOT_DISTINGUISHABLE. The per-label subgroup MANUFACTURED_ATTENTION_DUMP on T2 (raw p 0.0045) gives 1 hit in 14 on the opened holdout.
- Controls: NCB VERIFIED not flagged (raw p 0.032, Holm 0.096); NCB UNVERIFIED 426 of 426 unscorable; NCS skill 0, -0.017, -0.011; P28 830 of 830 refused for both traps.
- E3 (POST_OPENING): NO_UNCORRECTED_SKILL on every target; sealed folder not opened.
- Cost 0 USD, 0 LLM calls, no socket. Ledger N_search 118 to 121.
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
| G18 ledger | holds, with a wording note | Phase 13 rows unchanged; every registry row of a search kind (SIMPLE_ATTENTION_RULE, DESCRIPTION_ONLY, NEGATIVE_CONTROL, POST_OPENING_CHECK, TRAP_OR_CHECK) is in the ledger and totals equal `ledger_totals`. Six registry rows are not search configurations and have no ledger row: P15:EVENT_COUNT (COUNT), P15:CODING_DEV and P15:CODING_HOLDOUT (BLIND_CODING), P15:B_EVIDENCE_ONLY_LLM and P15:D_MIROFISH (NOT_RUN), P15:DECISION (DECISION). The checklist says "every registry row present"; the protocol 11 list of ledger kinds and the output test read it as every configuration row. Flagged for the skeptic |
| G19 deliverables | holds after this commit | the five named files, this file, RESULTS.json, skeptic packet, ROADMAP, DECISIONS (PI-D-081), HANDOFF |
| G20 post-commit | recorded below | `postcommit/` |

## Iteration log (bounded loop, not independent)

1. Pass 1, coding: two debug runs at uncommitted code (dbg1; dbg2 twin byte-equal), freeze `9ab0160`, recorded run `7b787bf`.
2. Pass 2, scoring: three debug runs (tolerance of the restated Phase 10 numbers from 5e-7 to 1e-5, because the Phase 10 CSV holds 6 decimals; no rule or verdict changed); first mutation probe left four survivors, three tests added; freeze `0abffd5`; recorded run `01e535d`.
3. Pass 3, self-review CP15-0 (PI-D-080): per-label holdout descriptions and independence counts added so the one tempting development subgroup is never shown without its holdout counterpart and the effective sample is visible; oracle probe and output tests; freeze `de41d26`; repeated run `3135060`, every first-run value equal.
4. Pass 4, records (second agent after the first session ended): documents checked against the outputs, adversarial-test table added, records written; no code or output changed.

## Own adversarial pass (not independent; the orchestrator's skeptic follows)

- CX-15 (named in the checklist before any code): a scorer that counts a bogus planted catalyst's statements as hits when T1 is positive and reports recall as accuracy. Caught: precision is always shown with the prevalence of the same rows and the day-stratified permutation; NCB VERIFIED reaches recall 0.588 and raw p 0.032 but is not flagged after Holm (0.096); recall is printed beside coverage (0.478).
- The bogus control's raw p below 0.05 shows that raw permutation p values on this sample are not evidence on their own.
- The T2 subgroup MANUFACTURED_ATTENTION_DUMP reads `sc_attention_suspect`, the input Phase 10's R2 and S models already used; it reverses on the holdout.
- The permutation exchanges decisions, not mints: T1b has 96 rows sharing a mint and a day, so its p values are optimistic; none is used for a verdict.

## Artifacts

Full sha256 digests in `PHASE_15_RESULTS.json`.

## Skeptic

Pending: the orchestrator runs the independent skeptic on `SKEPTIC_PACKET.md`.

## Post-commit at the records commit

Recorded in the follow-up commit (`postcommit/`).

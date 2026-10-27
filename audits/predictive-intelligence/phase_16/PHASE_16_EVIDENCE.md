# Phase 16 evidence: champion selection, ensemble decision and model registry

Status: **NEEDS_REVIEW** (first pass complete; the orchestrator's independent skeptic has not reviewed it yet). Branch `feature/predictive-intelligence`; HEAD before `576f99d`; work 2026-10-27 from 02:38Z. Package 41 of 41 checksums OK. Spend 0 (no vendor, Firecrawl, WebSearch, WebFetch or language-model call; audit hook, 0 socket events).

## Result in plain words

There is no champion for any target. All three primary targets are pinned NO_VIABLE_CHAMPION: every request abstains and every document says model `not_selected`. B0 (training prevalence) and B2 (the simple logistic baseline) are pinned beside each target as references for the prospective comparison; they are never published as a probability. Phase 12's "champion B2" was a default, not evidence, and the registry says so in every pin (PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE). 69 immutable entries: B0 and B2 ABSTAIN on every target (6), every other card NO_GO with NO_INCREMENTAL_PREDICTIVE_EDGE (63), 0 SHADOW, 0 VALIDATED_EXPERIMENTAL, 0 publishable. No ensemble: nothing beats the base rate, the development out-of-fold rows give no verdict, the stack never clears its gate, and two combinations that would count the lab's fatal flags twice are refused. Under the frozen promotion table no model can reach SHADOW after the retrospective holdout was opened; that needs a change control decided by Elving or the orchestrator.

## Entry gate (G2)

| Check | Command | Result |
|---|---|---|
| Full suite at `576f99d` | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` | exit 1, `1 failed, 1853 passed, 1 skipped in 265.03s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays `data/reports/20261027_0240_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []`, the three pinned hashes (`evidence/entry/seal_check.json`) |
| Phase 15 key tests | `python -m pytest tests/test_predictive_scenario_eval.py tests/test_predictive_phase15_outputs.py -q` | `46 passed` |
| Phase 15 status | `PHASE_15_RESULTS.json` | TEST_ONLY; admission by the orchestrator recorded as PI-D-084 |
| Stores | sha256 | `data/memelab.sqlite` `068287c0...`, p05 `2525f0c4...`, p06 `d2a5a7c6...`, equal to the Phase 12 run logs |

## Commits

| Commit | What |
|---|---|
| `8af3cd4` | pre-registration: checklist (27 items, CX-16), experiment registry (32 rows), PI-D-084, PI-D-085, entry evidence |
| `d2038a7` | frozen code: `registry.py`, 42 tests, fixture, runner, mutation probe; pre-freeze suite `1 failed, 1895 passed, 1 skipped in 283.56s` (known failure only) |
| `9eebb8d` | first recorded run at `d2038a7`, output tests, determinism repeat, mutation probe 73 of 73 |
| `8cd19bd` | change control CP16-0 (PI-D-086, self-review): facts tied to their sources; frozen before the repeat |
| `72488dd` | recorded run repeated at `8cd19bd`; `evidence/rerun_cp16_0_diff.json` |
| `ffcedb4` | records: this file, RESULTS.json, SKEPTIC_PACKET.md, the three model documents, ROADMAP, DECISIONS (PI-D-087), HANDOFF, cost ledger row |
| `d74a16f` | change control CP16-1 (PI-D-088): the post-commit suite at `ffcedb4` found the content guard's social-only key `members` in two output files; the runner writes `member_models` and `member_count` |
| `b669615` | recorded run repeated at `d74a16f`; `evidence/rerun_cp16_1_diff.json` |
| records update and post-commit record | this update; post-commit checks recorded in `postcommit/` |

## Recorded runs

| Run | Command | Exit | Output line |
|---|---|---|---|
| first, 2026-10-27T03:21:50Z to 03:22:13Z, code `d2038a7` | `python -B audits/predictive-intelligence/phase_16/probes/build_registry.py audits/predictive-intelligence/phase_16` | 0 | `{"entries": 69, "levels": {"ABSTAIN": 6, "NO_GO": 63}, "events": 75, "inference_equal": 69, "ensemble": {... "NO_ENSEMBLE" x3}, "n_search": 130, "failures": [], "stores_unchanged": true}` |
| determinism repeat into the scratchpad, same code | same with a scratch folder | 0 | 82 of 85 files byte-equal; run log and latency skipped; `ENSEMBLE_ABLATION.json` differed only in CPU-time fields (`evidence/determinism_repeat.json`) |
| repeat at the CP16-0 code `8cd19bd`, 2026-10-27T03:37:43Z to 03:38:05Z | same | 0 | same line; facts and sources verified for 69 of 69 entries (`run_log.json`) |
| second repeat at `8cd19bd` into the scratchpad | same | 0 | 83 of 83 compared files byte-equal (run log and latency excluded) |
| repeat at the CP16-1 code `d74a16f`, 2026-10-27T03:51:18Z to 03:51:41Z, and a second repeat into the scratchpad | same | 0 | same line; only `ENSEMBLE_ABLATION.json` and `LATENCY.json` changed (renamed keys; equal after renaming back) and the run log; second repeat 83 of 83 byte-equal |

Debug runs on real data before the frozen code, all into the scratchpad and listed in the runner and the ledger (4): dbg1 stopped while taking the before-state of `phase_06/sealed/` (it had computed the sha256 of four sealed-folder files, as `check_seal.py` does; nothing decompressed, parsed, printed or stored; replaced by size and mtime); dbg2 stopped in `run_holdout.load_cards`; dbg3 stopped at the T2 in-sample stacking trap (no rows); dbg4 complete.

Each run: no socket (audit hook), 3 `training_labels` calls (development labels, to check the committed out-of-fold rows), stores unchanged, the sealed folder never opened (stat only).

## What was checked, by checklist item

| Item | Evidence | Result |
|---|---|---|
| G1 package | `sha256sum -c` | 41 OK |
| G3 order | `git log` | checklist and registry `8af3cd4` before code `d2038a7`; output test `test_pre_registration_was_committed_before_the_registry_code` |
| G4 frozen code | run log `head` | `d2038a7` for the first run, `8cd19bd` for the repeat; four debug runs logged |
| G5 candidates | runner `load_candidates` | 69 cards, file sha256 and model sha equal to CANDIDATES.json; the registry's canonical sha equals each family's model sha |
| G6 no re-selection | runner and `select_champion` | the Phase 12 champions restated from development rows equal CANDIDATES.json (B2 by default on all three); holdout or post-opening rows are refused (unit test) |
| G7 levels | entries, output tests | ABSTAIN 6 (B0, B2), NO_GO 63, publishable 0; every stored level equals `promotion_decision(facts)` |
| G8 no champion that implies skill | log, index, today | 3 PIN events, all NO_VIABLE_CHAMPION, champion null; 30 documents ABSTAIN, model `not_selected`, `base_rate` null, probability null; index statement "No champion ... not forecasts" |
| G9 entries | `read_entries`, unit tests | file name = id = sha; a one-byte change refuses; card, card bytes and calibration card checked |
| G10 log | `read_log`, unit tests | chained; changed, dropped, reordered, partial, non-canonical and out-of-order lines refused; pins resolve as of the decision time |
| G11 identical inference | `evidence/INFERENCE_CHECK.json` | 69 of 69 cards reproduce the committed `HOLDOUT_PREDICTIONS.csv` exactly (numbers by `repr`, reasons); 18 synthetic-probe hashes recompute in the output test |
| G12 P46 | `evidence/COMPATIBILITY_P46.json` | real runtime 0 incompatible; Phase 07 feature definitions changed: 18 of 18 refused; feature version bumped: 69 of 69; registry fingerprint changed: 69; request with another feature set: 69 FEATURE_SCHEMA_MISMATCH |
| G13 P39 | `registry/TODAY_STATUS.json`, unit tests | references not stale at 2026-10-31T00:00:00Z, MODEL_STALE at 00:00:01Z; DRIFT_ALERT from an alarm at or before the decision (synthetic alarm time in the demonstration); history byte-equal after alarms and rollbacks |
| G14 rollback | `evidence/ROLLBACK_TEST.json` | fixture (TEST_ONLY): model at VALIDATED_EXPERIMENTAL rolled back on drift to the fixture B2 at SHADOW, then on an inference mismatch to NO_VIABLE_CHAMPION, history preserved; real log copy: each target stays NO_VIABLE_CHAMPION |
| G15 P22 | unit test, ledger | the best of 1,000 null candidates fails Bonferroni and never reaches VALIDATED_EXPERIMENTAL; N_search 130, sensitivity 169 |
| G16 P24 | unit test | 30 calibration events cannot reach SHADOW; the document abstains |
| G17 P27 | unit tests | behavioral sources, simulation-named models, agent-share candidates and behavioral ensemble members refused |
| G18 P38 | unit tests | NaN without reason, infinity, -0.1, 1.1, duplicates, booleans and non-finite facts refused |
| G19 ensembles | `ensemble/`, `models/ENSEMBLE_ABLATION.md` | out-of-fold rows only (unit tests refuse in-sample and fold-mismatched rows); 3 traps refused on every target; stack never fitted; development verdicts INSUFFICIENT_DAYS, INSUFFICIENT_EVENTS or INSUFFICIENT_HISTORY; NO_ENSEMBLE x3 |
| G20 publication path | today documents, unit tests | `abstention.forecast_result` with what `serve` resolves; `validate_publication` returns no error for all 30; a FORECAST is impossible with any real entry (no pin above ABSTAIN); deferred and blocked targets TARGET_NOT_FEASIBLE |
| G21 holdout description only | `ensemble/POST_OPENING_LOG.json` | 6 POST_OPENING descriptions from committed Phase 12 files, labelled NOT_A_CLAIM_POST_OPENING; seal check after: `"problems": []` |
| G22 today | `registry/TODAY_STATUS.json` | 10 prospective decisions x 3 targets ABSTAIN with FLAG_OFF, MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY, SOURCE_STALE (and TARGET_NOT_FEASIBLE for the one CURRENT_VENDOR_LIST decision) |
| G23 ledger | `experiments/LEDGER_TOTALS.json` | 3,287 rows (Phase 15's 3,259 plus 28 Phase 16 rows: 9 ABLATION, 9 TRAP_OR_CHECK, 6 POST_OPENING_CHECK, 4 DEBUG_RUN_REAL_DATA); candidate configurations 90 to 99; N_search 121 to 130; sensitivity 160 to 169 |
| G24 determinism and isolation | repeats, run log | see above; 0 network calls; stores and sealed folder unchanged |
| G25 tests and mutation probe | `evidence/mutation_registry.json` (73 of 73 at `9eebb8d`), `evidence/mutation_registry_cp16_0.json` (81 mutations at `8cd19bd`) | every listed mutation caught; four survivors of the first probe (E1, C2, R4, N4) were closed by tests before the frozen code |
| G26 isolation and contract | unit tests | `registry.py` imports numpy, the standard library, `contract` and `stats`; no other lab module imports it; contract, ACCEPTANCE, the registry fingerprint and every earlier module unchanged |
| G27 post-commit | `postcommit/` | first attempt at `ffcedb4` failed (CP16-1); at `2f81759`: suite `1 failed, 1911 passed, 1 skipped in 283.32s` (known failure only, strays removed by hand), guard 0 violations, seal `"problems": []`, single-branch release audit exit 0 "Needs action: no." |

## Numbers behind the policy (from committed files, not recomputed)

| Target | B2 against B0 on the first opening | Phase 13 calibration set | B2 reasons |
|---|---|---|---|
| T1 24 h | 66, 15 positive, BSS -0.024, mint interval -0.156 to +0.134 | 24, 8, 3 days | RETROSPECTIVE_BSS_BELOW_0, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |
| T1b 6 h | 68, 12, BSS -0.083, calibration in the large failed | 44, 3, 5 days | RETROSPECTIVE_CALIBRATION_FAILED, RETROSPECTIVE_BSS_BELOW_0, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |
| T2 24 h | 59, 7, BSS +0.292 point, INSUFFICIENT_EVENTS | 8, 1, 1 day | RETROSPECTIVE_BELOW_MINIMUM, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION |

## Iteration log

1. Inspect: package, records PI-D-001 to PI-D-083, Phase 12, 13, 15 outputs, the frozen cards' columns, the module isolation tests (the registry core may not import evaluation, calibration, abstention or the family modules, and may not name the Phase 10 module), the backtesting branch (`memelab/backtest/strategies/registry.py` is a strategy registry, not a model registry: no duplicate). Pre-registration committed.
2. Build and check: `registry.py`, 42 tests; the isolation test caught a card key name that names the Phase 10 module, so module versions are passed by the caller; the first mutation probe left 4 survivors, closed by 4 tests; pre-freeze suite; frozen code; recorded run; determinism repeat; mutation probe 73 of 73.
3. Attack (self-review, not independent): a forged entry with edited facts and a recomputed id passed `verify_entry` and could have been pinned as a champion, because levels were recomputed from stored facts that nothing tied to their sources (Phase 13 had left calibration-fact authenticity to this registry). Fixed as CP16-0 (PI-D-086): `derive_facts`, `verify_facts`, `verify_sources`, source checks required by pins, rollbacks and `serve`; 81 mutations caught. The pre-registered expectation that the repeat would leave every entry byte-equal was wrong: the embedded retrain policy gained a trigger, so every entry id changed while every fact, level, hash, pin and decision stayed equal (`evidence/rerun_cp16_0_diff.json`).
4. Repeat at `8cd19bd`; second repeat byte-equal; records (`ffcedb4`).
5. Post-commit suite at `ffcedb4`: 4 failed (the known one plus three content-guard tests): `ENSEMBLE_ABLATION.json` and `LATENCY.json` used the JSON key `members`, which the content guard reserves for social content. The guard run before the outputs commit had passed only because it scans tracked files and the outputs were untracked then. Fixed as CP16-1 (PI-D-088): renamed keys, an output test that runs the guard on every Phase 16 JSON file tracked or not; repeat at `d74a16f`; post-commit checks redone.

## Counterexamples

- CX-16 (named before building): a registry that copies Phase 12's `champion: P07_B2` into the deployed slot and shows T2 B2's +0.29 BSS point as skill. Caught by `promotion_decision` (RETROSPECTIVE_BELOW_MINIMUM, NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION), `pin_event` (a champion needs SHADOW or VALIDATED_EXPERIMENTAL), `resolve` (a hand-written CHAMPION pin of an ABSTAIN entry is refused), `verify_entry` (a forged level is refused) and the output tests (`test_cx16_t2_b2_has_a_positive_point_but_stays_an_abstain_reference`, `test_every_target_is_pinned_no_viable_champion_with_its_own_references`).
- CX-16b (self-review, CP16-0): forged facts with a recomputed id. Caught by `verify_facts` against the committed files and by `pin_event` and `serve` needing that check (`test_cp16_0_forged_facts_pass_verify_entry_but_are_refused_against_their_sources_and_never_pinned`).
- The independent skeptic's counterexample: pending (orchestrator).

## Findings and limitations

- TEST_ONLY parts: SHADOW and VALIDATED_EXPERIMENTAL entries, CHAMPION pins, their use in `serve` and rollback from a champion exist only on fixtures; no real entry can reach them.
- The promotion path is closed under the frozen ACCEPTANCE table (FIRST_OPENING retrospective evaluation required; the retrospective holdout is spent and inside the training window of any later model). Reopening it is a change control for Elving or the orchestrator, registered before prospective labels are read.
- `calibration.verify_card` still refuses a self-given VALIDATED_EXPERIMENTAL; the change that lifts it must depend on a registry entry whose recomputed level is VALIDATED_EXPERIMENTAL (Phase 19 or later).
- The frozen cards are MODEL_STALE after 2026-10-31T00:00:00Z; the prospective comparison of the references after that date needs retrained reference cards from a new plan.
- Since Phase 13, `phase_12/probes/run_holdout.py plan` and `predict` no longer run as committed: `load_cards` globs `phase_*/artifacts/T*/*.json` and meets the Phase 13 calibration cards (KeyError '13'). Phase 16 loads the cards from CANDIDATES.json instead. Not fixed (Phase 12 code is frozen); a Phase 12 reproduction needs that glob narrowed.
- The evidence-source map of the ensemble rule is an assumption about the lab's derived classifiers (lifecycle, manipulation, narrative strength).
- The pre-opening test flags in the facts are taken from Phase 12's committed trap results and the cards' own hashes, not rerun here.
- Internal reference scores (shadow baseline mode) are defined and tested on fixtures; none were written (no prospective decision has features).
- The registry core's internal row key `members` (`out_of_fold_rows`, `fit_stack`) is a content-guard key; it is never written by the runner, and any later phase that writes those structures to JSON must rename it (PI-D-088).
- The release audit's report from the first post-commit attempt (exit 1 at `ffcedb4`, while the guard violations were present) was lost from the scratchpad before it was read; the attempt at `b669615` exits 0, "Needs action: no."

## Artifacts (sha256 at the records commit)

| Path | sha256 |
|---|---|
| ACCEPTANCE_CHECKLIST.md | 482462e39e69b5f6169a4f2c5666093057f1d0ee7db7cd8bfe3ef91339e52b60 |
| experiments/EXPERIMENT_REGISTRY.csv | 6aad91816603be894d76d3ade7ec652c9a2cecfa9e6bee290ae4c3526ef114a0 |
| registry/REGISTRY_LOG.jsonl | 6ee9226fc49bbdece175114d26fec968042ab637d3b3e07a9834b973f9d494b0 |
| registry/REGISTRY_INDEX.json | 551870baf698c8c0b001497d7872a9dccf2dfbfef8ce961f33a27d693a806697 |
| registry/TODAY_STATUS.json | b24bd229bf91d6a42fafaf7640b6f1ec71e67eb4861d56a034278e1705956ff3 |
| registry/TODAY_RESULTS.jsonl | 47a2a34666599f0cb8f5a25d37a0c5e2ded394c2de74b8263745fba50057b3bb |
| registry/TODAY_RECORDS.jsonl | 66dcf22346e0ef8167439e86be3050b244ffcddd471c0d5cb5f4ad5b317b89df |
| ensemble/ENSEMBLE_ABLATION.json | see RESULTS.json (rewritten by CP16-1) |
| ensemble/ENSEMBLE_ABLATION.csv | 0a8bcb5ef0bad0b5f3aaed18d0ce4d6ea85f516784a1ccaeeba0a842939cff42 |
| ensemble/STABILITY.json | 34b97dd5c7a03c6d8d49ac048a2378de30f6611f91b217226afad5cf298931da |
| ensemble/POST_OPENING_LOG.json | 39ecb7fecad1735ce6a4dad4d6082b4acabc4090518d98e65310f04a2516af68 |
| evidence/INFERENCE_CHECK.json | d8723a28b04420112bef94dfc783526d81b32f00940f80e420ee11d33f914629 |
| evidence/COMPATIBILITY_P46.json | b1311ef0595a95ac8fd162a15e5f2981c2ea7f53262dd0e71f800144d6b1be2a |
| evidence/ROLLBACK_TEST.json | a63ea6fdaa886d7c5be55e06dab3d345fca217ef685dde22e68d4d5aa36d1e60 |
| evidence/rerun_cp16_0_diff.json | b9abac04b380771ff4c418887188717ba7f42382d569fcac8774f87197eca12e |
| evidence/rerun_cp16_1_diff.json | see RESULTS.json |
| experiments/SEARCH_LEDGER.csv | c0bac44e26a709c84651ca3114f2c9421cb2dc484bedf6bd93ae052d01cab42a |
| experiments/LEDGER_TOTALS.json | 2e68d0f7522a155e0cffda6d7c649f8fa829b1fabaf7516a6f974c943fb55e30 |
| memelab/predictive/registry.py | ab6d71bc315397a68ee2fddef60adec084053ecc29711166b520acff22b87f43 |
| tests/test_predictive_registry.py | e4cc82683ac1591812aabd0e6e7c9d6b2610cd19cecd85caa45f1a36ca140d0d |
| tests/test_predictive_phase16_outputs.py | see RESULTS.json (CP16-1 added a test) |
| probes/build_registry.py | see RESULTS.json (changed by CP16-1) |

The model documents' hashes are in RESULTS.json. Sources: no external source was read in this phase; every input is a committed file of this repository or a private store listed in the run log.

PHASE 16: NEEDS_REVIEW (pending the orchestrator's independent skeptic). STOP.

# Phase 20 evidence: independent adversarial integration and scientific audit

Status: NEEDS_REVIEW (pending the orchestrator's independent skeptic, PI-D-013). Phase 19 stays NEEDS_REVIEW on G25 (PI-D-106); every statement here that rests on a Phase 19 outcome is PROVISIONAL_PENDING_REVISION_REREAD.

The auditor is the Phase 20 agent acting as a reviewer who did not build the pathway. Findings: `qa/INDEPENDENT_FINDINGS.md`. Scenario matrix: `qa/SCENARIO_MATRIX.csv`. End-to-end log: `qa/FULL_E2E_LOG.md`. Claims audit: `qa/SCIENTIFIC_CLAIMS_AUDIT.md`. Package checklist: `qa/COMPLETION_CHECKLIST_AUDIT.md`.

## Order of work (git)

| Step | Commit | Time (UTC) |
|---|---|---|
| HEAD before the phase | `e0bc906` | |
| Pre-registration (ACCEPTANCE_CHECKLIST.md, EXPERIMENT_REGISTRY.csv, PI-D-109) | `9e1f29d` | 16:14:44Z |
| Frozen audit code (probes, cross tests with strict xfails, checklist additions) | `0d66379` | before 17:07Z |
| Recorded audit runs at `0d66379` | outputs committed at `67acbc3` | 17:07:48Z to about 17:50Z |
| Change control CP20-1 written (PI-D-110) | `67acbc3` | before the code change |
| CP20-1 code and tests | `5ebce8a` | 17:59:07Z |
| Touched paths rerun at `5ebce8a` | records commit | 17:59:47Z to 18:26:48Z |

No lab or predictive module changed before `5ebce8a`; at `0d66379` every lab and predictive module is byte-identical to `e0bc906`.

## Gate items

| Item | Result | Evidence |
|---|---|---|
| G1 entry gate | held: suite 2 known failures, 2,200 passed; Phase 19 ledger verify ok, rebuild 0 differences, seal 0 problems | `ACCEPTANCE_CHECKLIST.md` header, PI-D-109 |
| G2 P01 to P48 | 48 of 48 own checks exit 0; 229 of 229 gating assertions; PASS 23, TEST_ONLY 12, PASS_EXPECTED_ERROR 10, PASS_WITH_PROBE_FINDING 3 (P41, P44, P46); 133 mapped test functions, 232 cases passed; same at `5ebce8a` (0 row differences) | `qa/SCENARIO_MATRIX.csv`, `qa/raw/`, `evidence/matrix_run.json`, `evidence/mapped_tests.txt`, `evidence/repair_rerun/` |
| G3 counterexamples | 39 of 39 caught at `0d66379` and at `5ebce8a`; 85 tests passed | `qa/COUNTEREXAMPLES.csv`, `evidence/cx_rerun.json`, `evidence/cx_raw/`, `evidence/repair_rerun/` |
| G4 cross-component | X01 to X06 with controls; at `0d66379` 13 passed, 6 strict xfails (X02, X03, X04 twice, X06, carried case); at `5ebce8a` 24 passed, 2 strict xfails (X04, F20-04) | `tests/test_predictive_phase20_cross.py`, `evidence/cross_component.json` |
| G5 reproductions | every entry point exit 0 at `0d66379`; differences only in named time fields (Phase 14 `scenario_ref` added to the named list after the run, checked in `evidence/phase14_mock_grid_check.json`) and the absolute path of F20-10; rerun at `5ebce8a` | `evidence/reproductions.json`, `evidence/repair_rerun/reproductions.json` |
| G6 end-to-end | release_e2e 78 of 78, 0 network attempts; real-path smoke all exits 0, flag-off byte-equal to `b0fad12`, flag-on equals base plus the section, 24 ABSTAIN, 0 FORECAST, rerun and retry DUPLICATE; same at `5ebce8a` (differences only in capture time, pass id, record ids and latencies) | `qa/FULL_E2E_LOG.md`, `evidence/e2e/`, `evidence/repair_rerun/e2e/` |
| G7 flag-off identity | 12 of 12 comparisons identical at `0d66379` and at `5ebce8a` | `evidence/flag_off_identity.json`, `evidence/repair_rerun/flag_off_identity.json` |
| G8 fresh environment | 1,372 passed, 8 skipped with reasons, 6 xfailed; 50 behavioral tests need loopback (F20-11) and pass with it (203 passed, 2 skipped) | `evidence/fresh_env.json`, `evidence/fresh_env/` |
| G9 release audit | single-branch clone, `--history`: exit 0, "Needs action: no." at `0d66379` and at `5ebce8a` | `evidence/e2e/release_audit_history.summary.txt`, `evidence/repair_rerun/e2e/` |
| G10 recalculation | own code: 61 of 61 prospective labels (T1 22, T1b 24, T2 15), 40 of 40 development labels, 28 decision keys, 168 of 168 reference numbers, 0 mismatches | `evidence/independent_recalc.json` |
| G11 two traces | every link holds | `evidence/real_event_traces.json` |
| G12 claims | no claim of skill, edge, calibration or profit without its evidence class; sensitivity changes no verdict | `qa/SCIENTIFIC_CLAIMS_AUDIT.md`, `evidence/oos_sensitivity.json` |
| G13 threats | 0 copyleft findings; every key, order and license hit explained; 0 credentials; no schedule; numpy only; locks pinned | `evidence/threat_scan.json`, `qa/INDEPENDENT_FINDINGS.md` |
| G14 operations | P33, P34, P35, P40, P46, P47, P48 hold; post-commit checks recorded | `evidence/operations.json`, `postcommit/` |
| G15 defect ledger | 0 CRITICAL; MATERIAL F20-02 and F20-06 repaired (CP20-1); 12 MINOR | `qa/INDEPENDENT_FINDINGS.md` |
| G16 package checklist | 20 items marked with evidence: 15 MET (item 6 after CP20-1), 2 MET_WITH_LIMIT (10, 17), 2 MET_TEST_ONLY (11, 15), 1 NOT_MET (20, Phase 21's release memo) | `qa/COMPLETION_CHECKLIST_AUDIT.md` |
| G17 records | search ledger rows (N_search 130, 169 unchanged), cost row (spend 0), PI-D-109 to PI-D-111, ROADMAP, HANDOFF, RESULTS.json, SKEPTIC_PACKET.md | the files |

## Change control CP20-1 (PI-D-110)

Written after the recorded runs and before the code change. What changed at `5ebce8a`:

1. F20-06 (MATERIAL): `registry.training_after_cutoff` (the rule of `evaluation.check_card_time`: a training decision at or after the cutoff, or a training label maturing after it). `pin_event` refuses such a champion (PinRefused, TRAINING_ROWS_AFTER_CUTOFF); `status_at` adds the state, so `serve` blocks a pin written by hand or by older code. The RETRAIN table is unchanged (entries carry it in their hash). 0 of the 69 committed entries are affected; the smallest margin between an entry's last training decision or maturity and its cutoff is 25,074 s (`repair/REAL_ENTRIES_SCAN.json`).
2. F20-02 (MATERIAL): `_process` refuses a token row whose mint or chain differs from the decision's before any pool, read or document (NOT_EXACT_IDENTITY, detail TOKEN_ROW_OF_ANOTHER_IDENTITY).
3. F20-03 (MINOR): `run_pass` checks the capture time with `store.epoch_seconds` first and returns CAPTURE_TIME_REFUSED with nothing read or written; `render` and `analyze_line` show it.
4. F20-08 (MINOR, carried Phase 18 minor 5): `integration.recompute_point` recomputes the raw number from the stored inputs with the registry-resolved card and the point and interval from the raw number with the calibration card; `reports._target_view` refuses the document on any difference. The audit also found, while writing the repair tests, that at `0d66379` a stored raw number or a stored input moved alone (point unchanged) was shown too; both are refused now. Residual: a coordinated rewrite of inputs, raw number, point and document with a reseal needs a signature (no key approved, PI-D-005).
5. `tests/fixtures/predictive/phase18/PINNED_SHA256.json`: the sha256 of `integration.py` and `registry.py` updated (the Phase 18 rule for a later phase that changes an existing module). `reports.py` is not in that list; its imports are unchanged.

Proof:

- Old-code check: the repaired cross-test file run against `0d66379` in a detached worktree: 12 failed, 12 passed, 2 xfailed; the two X06 controls fail there only because `training_after_cutoff` does not exist (`repair/OLD_CODE_CHECK.txt`).
- Phase 19 steps that import registry-1 (`run_prospective.py rollback` and `drift`), rerun with the repaired code: `ROLLBACK_DEMO.json` and `DRIFT_REPORT.json` byte-equal to the committed outputs (`repair/PHASE19_REGISTRY_PATHS.json`). The drift step appended four entries to the committed outcome ledger during that check; they were reverted (finding F20-14).
- Suite before the commit: 2 failed (the two known clock-dependent tests), 2,224 passed, 1 skipped, 2 xfailed.
- Touched paths rerun at `5ebce8a` (`evidence/repair_rerun/`, times in `run_times.txt` there): cross tests 24 passed, 2 xfailed; scenario matrix identical to the recorded one (48 rows, 0 differences in id, result, exit code, assertion counts, mapped tests); counterexamples 39 of 39 caught, 85 passed; flag-off identity 12 of 12 (a first rerun reported all_identical false only because the auditor's own uncommitted record edits were in the checkout at the end of the run; the edits were stashed and the rerun repeated with a clean checkout); release_e2e 78 of 78; real-path smoke equal to the recorded run apart from capture-time fields, pass id, record ids and latencies; single-branch release audit exit 0; reproductions as below.

Reproductions at `5ebce8a` (`evidence/repair_rerun/reproductions.json`, 17:59:47Z to 18:26:48Z, wall 1,620.4 s): every entry point exit 0 and `all_reproduced` true. Phase 05 truncation, recompute, traps and fresh exit 0; Phase 06 seal 0 problems; `tests/test_predictive_reproductions.py` (Phases 07, 12, 13, 16) 5 passed; Phases 08, 10, 11, 15, 18 identical (26, 36, 27, 6, 7 files); Phase 09 identical apart from the absolute path of F20-10; Phase 14 identical apart from the named time fields; Phase 17 export replay documents and records equal to the Phase 19 published copy; Phase 19 rebuild ok, `evaluate` identical apart from `ledger_head`, monitoring and outputs tests 55 passed.

## Probe edits after the recorded run (stated, not hidden)

- `probes/reproductions.py`: `scenario_ref` added to the named time fields of the Phase 14 `MOCK_GRID_RUNS.json` (it embeds a document hash that holds the creation time); checked by hand in `evidence/phase14_mock_grid_check.json` (18 refs, equal without the time fields).
- `probes/fresh_env.sh`: raises loopback with the new `probes/lo_up.py` before the tests (F20-11); the recorded fresh-environment run used the earlier form plus a separate loopback run.
- `probes/ledger.py`: one row per CP20-1 rerun and the P20:CROSS_X06 row.

## Search and cost ledgers

`experiments/SEARCH_LEDGER.csv` and `LEDGER_TOTALS.json`: the Phase 19 cumulative ledger plus one row per Phase 20 debug run, recorded run and CP20-1 rerun, each AUDIT_RUN_NOT_A_CONFIGURATION; N_search 130, sensitivity 169, unchanged. `COST_LEDGER.md`: spend 0; no vendor or language-model call; free PyPI downloads for the fresh environment only.

## Limits

- No champion, no calibrated card and no FORECAST exist on any real path; every FORECAST in this audit is a fixture (TEST_ONLY). The repairs close paths that no real target reaches today.
- The audit is by the same agent family that built the pathway, against the package's own scenario list; the orchestrator's skeptic is the independent check.
- Phase 19 numbers are provisional until G25 runs (from 2026-10-29T14:35Z).
- F20-04 (ledger token rule) waits for G25 because `monitoring.py` is on the frozen re-read path; F20-01, F20-05 and F20-07 change Phase 17 or 18 wording and wait for a change control that reruns their goldens.

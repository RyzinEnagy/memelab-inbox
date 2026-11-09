# Phase 20 evidence: independent adversarial integration and scientific audit

Status: PASS after repair pass 2 (2026-11-09, PI-D-114). The orchestrator's independent skeptic (PI-D-013) ran on 2026-11-09 and found 3 MATERIAL and 9 MINOR items (`skeptic/PHASE_20_SKEPTIC.md`); change control CP20-2 (PI-D-113) repaired every MATERIAL item and the MINOR items listed below (section "Independent skeptic and repair pass 2"). Phase 19 is PASS since G25 ran on 2026-10-29 (PI-D-112), so the PROVISIONAL_PENDING_REVISION_REREAD marking on statements here that rest on a Phase 19 outcome is lifted.

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
| Touched paths rerun at `5ebce8a` | records commit `0b24539` | 17:59:47Z to 18:26:48Z |
| Phase 19 G25 (orchestrator) | `b4d4768` | 2026-10-29 |
| Orchestrator's independent skeptic of Phase 20 | review at `b4d4768` | 2026-11-09 |
| Change control CP20-2 written (PI-D-113) | `f5a174b` | 2026-11-09, before the code change |
| CP20-2 code, tests and probe changes | `243cd32` | 2026-11-09 |
| Touched paths rerun at `243cd32` | records commit `18b907e` | 2026-11-09T21:30:45Z onward (`evidence/repair2_rerun/run_times.txt`) |

No lab or predictive module changed before `5ebce8a`; at `0d66379` every lab and predictive module is byte-identical to `e0bc906`.

## Gate items

| Item | Result | Evidence |
|---|---|---|
| G1 entry gate | held: suite 2 known failures, 2,200 passed; Phase 19 ledger verify ok, rebuild 0 differences, seal 0 problems | `ACCEPTANCE_CHECKLIST.md` header, PI-D-109 |
| G2 P01 to P48 | 48 of 48 own checks exit 0; 229 of 229 gating assertions; PASS 23, TEST_ONLY 12, PASS_EXPECTED_ERROR 10, PASS_WITH_PROBE_FINDING 3 (P41, P44, P46); 133 mapped test functions, 232 cases passed; same at `5ebce8a` (0 row differences); at `243cd32` 48 of 48 exit 0, 239 of 239 gating assertions (P05 +1, P41 +4, P44 +5: the former probe assertions of P41 and P44 now gate, with the CX-SK20 cases), PASS 25, TEST_ONLY 12, PASS_EXPECTED_ERROR 10, PASS_WITH_PROBE_FINDING 1 (P46, F20-07), 232 mapped cases passed, `unpatched_severity` filled (26 CRITICAL, 22 MATERIAL) | `qa/SCENARIO_MATRIX.csv`, `qa/raw/`, `evidence/matrix_run.json`, `evidence/mapped_tests.txt`, `evidence/repair_rerun/`, `evidence/repair2_rerun/matrix/` |
| G3 counterexamples | 39 of 39 caught at `0d66379`, at `5ebce8a` and at `243cd32`; 85 tests passed; the skeptic's new CX-SK20 is caught at `243cd32` by the cross tests and P41 (not in the 39 recorded ones) | `qa/COUNTEREXAMPLES.csv`, `evidence/cx_rerun.json`, `evidence/cx_raw/`, `evidence/repair_rerun/`, `evidence/repair2_rerun/cx/` |
| G4 cross-component | X01 to X06 with controls; at `0d66379` 13 passed, 6 strict xfails (X02, X03, X04 twice, X06, carried case); at `5ebce8a` 24 passed, 2 strict xfails (X04, F20-04); at `243cd32` 43 passed, 0 xfails (X04 repaired; S20-2, S20-8 and CX-SK20 tests added) | `tests/test_predictive_phase20_cross.py`, `evidence/cross_component.json` |
| G5 reproductions | rerun at `243cd32`: see the repair pass 2 section; every entry point exit 0 at `0d66379`; differences only in named time fields (Phase 14 `scenario_ref` added to the named list after the run, checked in `evidence/phase14_mock_grid_check.json`) and the absolute path of F20-10; rerun at `5ebce8a` | `evidence/reproductions.json`, `evidence/repair_rerun/reproductions.json` |
| G6 end-to-end | release_e2e 78 of 78, 0 network attempts; real-path smoke all exits 0, flag-off byte-equal to `b0fad12`, flag-on equals base plus the section, 24 ABSTAIN, 0 FORECAST, rerun and retry DUPLICATE; same at `5ebce8a` and at `243cd32` (differences only in capture time, pass id, record ids, latencies and the theses table hash, which holds the run's clock; no real symbol withheld by the CP20-2 rule) | `qa/FULL_E2E_LOG.md`, `evidence/e2e/`, `evidence/repair_rerun/e2e/`, `evidence/repair2_rerun/e2e/` |
| G7 flag-off identity | 12 of 12 comparisons identical at `0d66379`, at `5ebce8a` and at `243cd32` (the last run with the literal `HEAD` argument, now resolved to `243cd32` before the clone; commit check true) | `evidence/flag_off_identity.json`, `evidence/repair_rerun/flag_off_identity.json`, `evidence/repair2_rerun/flag_off_identity.json` |
| G8 fresh environment | 1,372 passed, 8 skipped with reasons, 6 xfailed; 50 behavioral tests need loopback (F20-11) and pass with it (203 passed, 2 skipped) | `evidence/fresh_env.json`, `evidence/fresh_env/` |
| G9 release audit | single-branch clone, `--history`: exit 0, "Needs action: no." at `0d66379`, at `5ebce8a` and at `243cd32` | `evidence/e2e/release_audit_history.summary.txt`, `evidence/repair_rerun/e2e/`, `evidence/repair2_rerun/e2e/` |
| G10 recalculation | own code: 61 of 61 prospective labels (T1 22, T1b 24, T2 15), 40 of 40 development labels, 28 decision keys, 168 of 168 reference numbers, 0 mismatches. Of the 168, 84 are the B0 constant read from the same card file on both sides; the independent content is 84 B2 numbers and 28 decision keys (S20-12). The skeptic's own recompute matched 61 of 61 labels and 36 of 36 B2 numbers | `evidence/independent_recalc.json` |
| G11 two traces | every link holds | `evidence/real_event_traces.json` |
| G12 claims | no claim of skill, edge, calibration or profit without its evidence class; sensitivity changes no verdict | `qa/SCIENTIFIC_CLAIMS_AUDIT.md`, `evidence/oos_sensitivity.json` |
| G13 threats | 0 copyleft findings; every key, order and license hit explained; 0 credentials; no schedule; numpy only; locks pinned | `evidence/threat_scan.json`, `qa/INDEPENDENT_FINDINGS.md` |
| G14 operations | P33, P34, P35, P40, P46, P47, P48 hold; post-commit suite, guard, seal check and single-branch release audit at the repair pass 2 records commit recorded in `postcommit/` (S20-10: the first pass named this folder but did not create it) | `evidence/operations.json`, `postcommit/` |
| G15 defect ledger | 0 CRITICAL; MATERIAL F20-02 and F20-06 repaired (CP20-1); after the skeptic, F20-01 reclassified MATERIAL and repaired with S20-1 (CX-SK20) and S20-2 (CP20-2); no MATERIAL open; MINOR open: F20-07, F20-10, F20-11, F20-13, F20-14 (records, environment or outside the initiative), F20-12 by design | `qa/INDEPENDENT_FINDINGS.md` |
| G16 package checklist | 20 items marked with evidence: 15 MET (item 6 after CP20-1), 2 MET_WITH_LIMIT (10, 17), 2 MET_TEST_ONLY (11, 15), 1 NOT_MET (20, Phase 21's release memo) | `qa/COMPLETION_CHECKLIST_AUDIT.md` |
| G17 records | search ledger rows (46 audit rows after CP20-2; N_search 130, 169 unchanged), cost rows (spend 0), PI-D-109 to PI-D-114, ROADMAP, HANDOFF, RESULTS.json, SKEPTIC_PACKET.md | the files |

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

## Independent skeptic and repair pass 2 (CP20-2, PI-D-113)

The review and its scripts are in `skeptic/` (copied from the orchestrator's folder). Every finding was checked against the code at `b4d4768` before PI-D-113 was committed (`f5a174b`); the code followed at `243cd32`.

Counterexample CX-SK20: a token named `100XGAIN` with the fatal flag CANNOT_EXIT_5K. At `b4d4768` the Phase 18 report printed `| 100XGAIN | ... | CANNOT_EXIT_5K |` and `## 1000XGEM`, the dry-run alert printed "100XGAIN on solana", and the scout section printed `100XGAIN`, because the multiplier pattern needed a non-letter after the X and `_ident` had no multiplier or run-together trading-word rule. What catches it now: `integration.unsafe_token_text` (through `_ident` and `reports._token_text`) and `reports.check_text`'s multiplier rule; tests `tests/test_predictive_phase20_cross.py::test_cx_sk20_*` (11 cases, all failing at `b4d4768`); P41 and P44 gating assertions (both exit 1 at `b4d4768`); the skeptic's own `skeptic/p20_cp20_attacks.py` passes 17 of 17 at `243cd32` (`repair2/SKEPTIC_ATTACKS_AT_243cd32.txt`).

What changed at `243cd32`:

1. S20-1, S20-3, F20-01 (reclassified MATERIAL), F20-05: one token-text rule in `integration` (`TOKEN_WORDS` moved from `reports`, list unchanged; `has_multiplier`, `unsafe_token_text`, `_mint_exempt`), used by `_ident` and `reports._token_text`; `reports.check_text` refuses multiplier claims (`text_multiplier`). The token's own mint and its six-character file-name prefix are exempt, so a real report name such as `..._GOMO_9XKzy4.md` is still shown. The Phase 17 test `test_rp2_m3` now expects MOONSHOT withheld (run-together MOON). The Phase 18 mutation probe's M4 names the old line in `reports.py`; its recorded output at its own commit stands.
2. S20-2: pool binding in `integration._process` and `_eligibility` (POOL_OF_ANOTHER_TOKEN refusal before any read when the token row's pool differs from the pool the decision's own result names; POOL_NOT_BOUND_TO_MINT, no read, when nothing but a replayed token row binds the pool). The pool in the request material is unchanged for the unbound case, so recorded export replays (no champion, no read) are unchanged. Deviation from PI-D-113 item 3, stated: a refusal because the lab store or another row of the pass also records the pool for another mint was implemented, broke the Phase 17 flag-on tests (the fixtures give three mints one pool) and was dropped before the commit; the lab's `pools` table keeps the first token a pair was seen under, quote side included, so it cannot say a pool belongs to another token.
3. S20-8: `registry.training_after_cutoff` and `evaluation.check_card_time` refuse a fitted card missing either maturity maximum (433 committed card records and 69 registry entries carry both; `repair2/REAL_ENTRIES_SCAN.json`).
4. F20-04 (S20-9): `monitoring.check_payload` requires exactly one `token` parameter equal to the mint; X04 markers removed; Phase 19 ledger verifies (`repair2/LEDGER_VERIFY.json`).
5. Probes: P05 and P43 require the refusal to name P05 or P43, P05 gains a matured control, P10 uses `stats.brier` and `stats.brier_skill`, P43 calls `labels.training_labels` on stored PROSPECTIVE rows; each fails under a mutant of the code it names (`repair2/PROBE_MUTANT_CHECKS.json`). P41 and P44's probe assertions became gating, with the CX-SK20 cases. `flag_off_identity.sh` resolves its commit argument before the clone; `flag_off_summary.py` checks the frozen commit (S20-4). `run_matrix.py` writes `unpatched_severity` (S20-11). `ledger.py` adds the CP20-2 rows.
6. `tests/fixtures/predictive/phase18/PINNED_SHA256.json`: `integration.py`, `registry.py`, `evaluation.py` updated.

Proof:

- Old-code check (`repair2/OLD_CODE_CHECK.txt`): the CP20-2 tests run against `b4d4768`: 18 failed, 3 passed (the three controls); the CX-SK20 control fails there by AttributeError, not behaviour.
- Suite before the code commit: `2243 passed, 1 skipped, 2 deselected` (the two known clock-dependent tests deselected).
- Touched paths rerun at `243cd32` (`evidence/repair2_rerun/`, `run_times.txt`): cross tests 43 passed; counterexamples 39 of 39 caught, 85 passed; scenario matrix 48 of 48 exit 0, 239 of 239 gating, 232 mapped cases passed; the rows that differ from the CP20-1 rerun are P05, P41 and P44 (assertion counts; P41 and P44 from PASS_WITH_PROBE_FINDING to PASS); flag-off identity 12 of 12 with commit check; release_e2e ok at `243cd32`; real-path smoke all exits 0, section identical to the CP20-1 rerun apart from capture time, pass id, record ids and latencies; single-branch release audit exit 0, "Needs action: no."; reproductions as below.
- Reproductions at `243cd32` (`evidence/repair2_rerun/reproductions.json`, 21:37:39Z to 21:50:13Z, wall 754.0 s): `all_reproduced` true, 19 entry points exit 0, no differing output apart from the named time fields (Phases 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17 export replay, 18 goldens, 19 rebuild, evaluate and tests). The scratch folder prefix in the copied run records is written as `SCRATCH/`, as in the CP20-1 rerun.

Disagreements with the review: none on substance. On S20-2 the repair is the positive binding the skeptic proposed as an alternative to a reader contract (no reader returns a pool's base token today); the reader contract itself is left to the first real reader.

Post-commit checks at the records commit `18b907e` (`postcommit/`): suite `2 failed, 2243 passed, 1 skipped, 1 warning in 234.19s` (the two known clock-dependent failures only; one stray report removed by hand), social guard exit 0 with 0 violations over 3,010 files, seal check exit 0 with `"problems": []`, single-branch release audit (3 refs) exit 0, "Needs action: no.".

## Probe edits after the recorded run (stated, not hidden)

- `probes/reproductions.py`: `scenario_ref` added to the named time fields of the Phase 14 `MOCK_GRID_RUNS.json` (it embeds a document hash that holds the creation time); checked by hand in `evidence/phase14_mock_grid_check.json` (18 refs, equal without the time fields).
- `probes/fresh_env.sh`: raises loopback with the new `probes/lo_up.py` before the tests (F20-11); the recorded fresh-environment run used the earlier form plus a separate loopback run.
- `probes/ledger.py`: one row per CP20-1 rerun and the P20:CROSS_X06 row.

## Search and cost ledgers

`experiments/SEARCH_LEDGER.csv` and `LEDGER_TOTALS.json`: the Phase 19 cumulative ledger plus one row per Phase 20 debug run, recorded run and CP20-1 rerun, each AUDIT_RUN_NOT_A_CONFIGURATION; N_search 130, sensitivity 169, unchanged. `COST_LEDGER.md`: spend 0; no vendor or language-model call; free PyPI downloads for the fresh environment only.

## Limits

- No champion, no calibrated card and no FORECAST exist on any real path; every FORECAST in this audit is a fixture (TEST_ONLY). The repairs close paths that no real target reaches today.
- The audit is by the same agent family that built the pathway, against the package's own scenario list; the orchestrator's skeptic is the independent check.
- G25 ran on 2026-10-29 (PI-D-112); Phase 19 numbers are no longer provisional.
- F20-07 (a wording fix in the request record) stays open for Phase 21. A pool bound only by a replayed token row is never read; a future real export replay with a champion needs the lab store or the result's identity to bind its pool.
- The CP20-2 token-text rule over-withholds (any symbol containing a trading word or a digit run joined to an x); the exact mint always identifies the token.

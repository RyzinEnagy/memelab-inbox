# Phase 20 full end-to-end log (G5, G6, G7, G8, G9)

Recorded runs of the frozen audit code `0d66379` (lab and predictive modules identical to `e0bc906`), 2026-10-27, times in UTC from `../evidence/run_times.txt` and `../evidence/e2e/e2e_runs.txt`. Every run used a sandbox (a clone or a copy), never the working checkout, and every sandbox was deleted after its outputs were copied. Every Phase 19-based statement is PROVISIONAL_PENDING_REVISION_REREAD (PI-D-106, G25 open). The rerun of the touched paths after the CP20-1 repair is recorded in `PHASE_20_EVIDENCE.md`.

## 1. Clean-clone release path (`tools/release_e2e.py`)

- Command: `bash probes/e2e.sh OUT` (stage 1), on a fresh clone of `0d66379`, 17:11:33Z to 17:15:48Z.
- Result: exit 0, 78 of 78 stages ok, 0 network attempts, `git status --porcelain` empty after the run, tracked database unchanged (`../evidence/e2e/release_e2e.json`, schema `memelab.release.e2e/1`, Python 3.13.17).

## 2. Predictive real-path smoke in a namespace without network (`unshare -n`)

- Command: `bash probes/e2e.sh OUT` (stage 2), 17:15:48Z to 17:16:54Z; the base `b0fad12` and the frozen code each in their own clone, on the latest real export (sha256 `3f44234e...`).
- Every exit code 0 (base off, frozen off, frozen on, rerun, retry, storm, research, analyze, the state checks and status reads).
- Flag OFF: the frozen code's scout output and its 9 token reports are byte-equal to `b0fad12`; the five lab tables (entries, rejections, theses, tokens, watchlist) have equal sha256 in base off, frozen off and frozen on.
- Flag ON: the scout output is the base output plus one appended section (24 ABSTAIN lines, 0 FORECAST lines); token reports byte-equal to the base.
- State: 8 attempts, 24 documents, all ABSTAIN with named reasons, 16 DUPLICATE events on the rerun and the retry, 0 errors, 0 completed forecasts; the storm run makes one attempt per mint; every state check reports 0 problems.
- Analyze: one line, `DISCOVERY ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED, SOURCE_STALE, UNCALIBRATED)`, research only. The lab's own analyze command rewrites one tracked report inside the sandbox (existing lab behaviour, same in the base); the sandbox's final status is clean.
- Evidence: `../evidence/e2e/REAL_PATH_SMOKE.json`, `../evidence/e2e/REAL_SCOUT_SECTION.md`.

## 3. Flag-off byte identity against `b0fad12` (G7)

- Command: `bash probes/flag_off_identity.sh OUT` then `python -B probes/flag_off_summary.py OUT`, 17:07:48Z to 17:10:18Z.
- 24 runs: two real exports (`efdaee9` and `71fc50e1...`), six configurations (no config, a malformed file, `"enabled": "true"` as a string, `"predictive": true` without a section, `"enabled": false`, `"enabled": 1`), base and frozen code each.
- 12 of 12 comparisons identical: exit code, stdout bytes, report bytes, lab tables, no predictive module imported, no private directory created, no tracked change (`../evidence/flag_off_identity.json`, `all_identical: true`).
- The malformed config makes the scout exit 1 in the base and the frozen code alike (F20-13, pre-existing lab behaviour); compared base against frozen per configuration.

## 4. Release audit with full history on a single-branch clone (G9)

- Command: `git clone --single-branch --branch feature/predictive-intelligence` at `0d66379` (3 refs), then `python tools/release_audit.py --history`, 17:17:27Z to 17:20:20Z.
- Result: exit 0, "Needs action: no." The full report quotes rule words and is not committed (PI-D-030); the summary is in `../evidence/e2e/release_audit_history.summary.txt`.

## 5. Fresh environment (G8)

- Command: `bash probes/fresh_env.sh OUT`, 17:11:31Z to 17:18:36Z: a clone, a new venv with numpy 2.5.3 and pytest 9.1.1 only (`../evidence/fresh_env/pip_freeze.txt`, 6 packages), the predictive tests under `unshare -m -n` with the private stores hidden by a tmpfs (0 stores visible inside).
- Result: 1,372 passed, 8 skipped (each with its reason: the store-dependent reproductions, the pinned MiroFish clone), 6 xfailed (the strict xfails of this phase's open findings), 50 failed.
- The 50 failures are all Phase 14 behavioral tests that start a loopback mock service; a new network namespace starts with the loopback interface down (`../evidence/fresh_env/failing_in_namespace_without_loopback.txt`). With loopback raised inside the same kind of namespace (an ioctl, still no route out), the behavioral file gives 203 passed, 2 skipped (no `jsonschema`, no IPv6 loopback), 17:19:34Z to 17:20:00Z (`pytest_behavioral_loopback_tail.txt`). Finding F20-11; `probes/lo_up.py` and the loopback step in `probes/fresh_env.sh` were added after the recorded run for the rerun.
- The log line `system_site True` in `fresh_env.log` reads the wrong flag (`sys.flags.no_site`); checked separately: `sys.prefix` differs from `sys.base_prefix` and SciPy is not importable in the venv, so the venv is isolated.

## 6. Phase reproduction entry points (G5)

- Command: `python -B probes/reproductions.py OUT` on a sandbox clone of `0d66379` with the private stores read-only, wall time 1,752.6 s (`../evidence/reproductions.json`).
- Every step exit 0:

| Step | Seconds | Result |
|---|---|---|
| 05 as-of fresh, recompute, traps, truncation | 0.9, 20.9, 61.0, 816.9 | exit 0; the truncation proof rewrites its own evidence file in the sandbox (timing fields) |
| 06 seal check, compare with Phase 05 | 0.1, 21.9 | 0 problems |
| 07, 12, 13, 16 (`tests/test_predictive_reproductions.py`) | 151.5 | 5 passed |
| 08 technical | 38.8 | 26 files identical |
| 09 on-chain | 76.3 | 34 identical, `collector_state.json` differs only in its absolute `path` (F20-10) |
| 10 social, 11 analog | 86.6, 54.1 | 36 and 27 identical |
| 14 seeds and behavioral grid (MiroFish skipped) | 16.6, 43.8 | 4 identical, 4 differ only in time fields; `MOCK_GRID_RUNS.json` differs only in time fields and `scenario_ref` (which embeds a time-dependent document hash); checked in `../evidence/phase14_mock_grid_check.json` (18 refs, equal without those fields) |
| 15 scenario scoring | 10.1 | 6 identical |
| 17 export replay | 14.1 | 156 documents, records equal to the Phase 19 published copy |
| 18 goldens | 2.8 | 7 of 7 identical |
| 19 evaluate, rebuild, monitoring and output tests | 297.7, 15.9, 20.7 | `PRIMARY_RESULTS.json` differs only in `ledger_head`; rebuild 156 records, 0 differences; 55 passed |

- `all_reproduced` is false in the JSON only because the recorded run's named-field list did not yet include `scenario_ref`; the list was extended after the run (`probes/reproductions.py`), stated in `PHASE_20_EVIDENCE.md`.

## 7. Scenario matrix, counterexamples, cross tests (G2, G3, G4)

- `python -B probes/run_matrix.py`, 17:07:56Z to 17:09:15Z: 48 of 48 exit 0; PASS 23, TEST_ONLY 12, PASS_EXPECTED_ERROR 10, PASS_WITH_PROBE_FINDING 3; 229 of 229 gating assertions; mapped tests 232 cases passed (`SCENARIO_MATRIX.csv`, `raw/`).
- `python -B probes/cx_rerun.py`, 17:09:15Z to 17:09:43Z: 39 of 39 counterexamples caught, 85 tests passed (`COUNTEREXAMPLES.csv`).
- `python -m pytest tests/test_predictive_phase20_cross.py`, 17:09:50Z to 17:10:04Z: 13 passed, 6 xfailed (`../evidence/cross_tests.txt`).

## 8. Disk and cleanup

Free disk before the runs about 12 GB, 9.5 GB at the end of the recorded runs with the outputs copied; every sandbox clone and venv deleted after use.

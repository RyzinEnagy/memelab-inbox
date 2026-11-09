# Rollback, uninstall and disaster recovery: proof

All runs below are Phase 21 runs from a fresh clone of the pushed branch fast-forwarded to `b048aac` (only `phase_21/` files added), under `env -i` and `unshare -n`, unless stated. Paths are relative to `audits/predictive-intelligence/phase_21/`.

## 1. Kill switch: flag off gives the original lab output

`evidence/release_checks/flag_off_identity.json` (from `phase_20/probes/flag_off_identity.sh` and `flag_off_summary.py`): the lab's scout on two real state exports (`71fc50e`, 2026-10-26, and `efdaee9`, 2026-10-24), each with six configs (no file, a malformed file, `"enabled": "true"` as a string, `"predictive": true`, `"enabled": false`, `"enabled": 1`), at the pre-Phase-17 code `b0fad12` and at `b048aac`:

- `all_identical`: true. Every report is byte-identical to the base run under the same config, the lab tables are equal, no predictive module is imported and no `data/private` folder is created (`private_dir no` in all 24 runs, `evidence/release_checks/flagoff/runs.txt`).
- `frozen_commit_is_the_requested_one_and_not_the_base`: true (the comparison is not base against base).
- The malformed config exits 1 at the base and at `b048aac` alike (F20-13, the lab's social research policy, pre-existing).

The real-path smoke shows the same on its own runs (`evidence/release_checks/e2e/smoke_summary/REAL_PATH_SMOKE.json`): `base_vs_frozen_off_all_reports_byte_equal` true, `lab_tables_equal_base_off_frozen_off_frozen_on` true, and with the flag on the scout body is the base body plus an appended section (`frozen_on_scout_is_base_plus_appended_section` true).

So rolling back is: remove `data/config.json` (or set `enabled` to false). Nothing else is needed for the lab to behave as before.

## 2. Uninstall

The predictive package is imported only by two helpers in `memelab/cli.py`, and only when the flag is the JSON value true (import trace in each flag-off run: no `memelab.predictive` module loaded). Its state lives in its own folder (default `data/private/predictive/`, or `state_dir`), its alert previews in `data/private/predictive_alerts/`; neither is a lab table. Deleting those folders removes everything the engine wrote. The lab tables are equal with the flag off and on (smoke), so there is nothing to undo in the lab database.

Removing the code itself (the `memelab/predictive/` package and the two helpers) is a code change that would go through a phase; it is not needed to turn the engine off.

## 3. Registry rollback

`evidence/doc_commands/docs_demo.json` (`probes/docs_demo.py`, on a copy of the committed log in a temporary folder): `registry.rollback_event` for a target with no champion falls back to NO_VIABLE_CHAMPION with the current references; `registry.append_events` appends it; the copy stays a valid chained log (75 events before, 76 after) and the committed log is unchanged. Earlier events are never edited (P39; the scenario matrix row P39 and `phase_19/monitoring/ROLLBACK_DEMO.json` show the drift response on a fixture registry). Today there is no champion to roll back from.

## 4. Disaster recovery

- The state is append-only with record ids and a chained pass log. `evidence/doc_commands/`: `integration check` on the smoke's state exits 0 (`problems: []`); on a copy with one byte of its documents file changed it exits 2 with `STATE_TAMPERED` ("DOCUMENTS.jsonl line 0: not JSON"). A damaged state is never repaired in place: keep it for inspection, start a fresh state folder (the next pass re-attempts every event), or restore a backup copy of the folder.
- A crash between appends also shows as STATE_TAMPERED and needs the same manual repair (Phase 17 constraint).
- The outcome ledger (`phase_19/monitoring/OUTCOME_LEDGER.jsonl`) and the registry log are tracked in git: recovery is `git checkout` of the committed file. `monitoring.verify` and `registry.read_log` refuse any edited, dropped or reordered line (chronology audit C1 and C3: both verify on 2026-11-09).
- The private research stores under `/home/claude/pi_research/` are rebuildable from the committed raw archives (`phase_05/raw/`, `phase_06/raw/`, `phase_19/raw/`) and `docs/predictive-intelligence/locks/`; without them, store-dependent tests skip with that reason (predictive tests with the stores hidden: 0 failures, `evidence/release_checks/suite_predictive_no_stores_tail.txt`).
- The lab itself does not depend on any predictive file: the flag-off runs above create none and read none.

## 5. What is not proven

- No rollback of a real champion: none was ever pinned (fixture rollbacks only, TEST_ONLY).
- No signed state: a coordinated rewrite with a reseal is not caught (no key approved).

# CM-3 evidence: spend-free maintenance (ED-3, ED-7, ED-9, ED-8 preparation)

Change control: PI-D-130 to PI-D-133 (`CHANGE_CONTROL.md`, committed before code at `bac9960`). Results: PI-D-134 to PI-D-136.
Approved by Elving on 2026-11-09 ("do everything that doesn't require spend"). Branch `maint/catalyst-export` from
`feature/predictive-intelligence` at `60eb729`. Local only; not pushed, not merged (the orchestrator merges, ED-6). Spend: 0.

Status: NEEDS_REVIEW (the orchestrator's skeptic reads `SKEPTIC_PACKET.md`).

## Commits

| Commit | What |
|---|---|
| `60eb729` | base (CM-1 post-commit record) |
| `bac9960` | change control PI-D-130 to PI-D-133 |
| `b99e139` | code and tests (44 tests), committed by the agent cut off by the session restart |
| `e822887` | repair after the restart: trader source ids hashed, stdout assertion corrected, key file name gitignored, identity probe |
| records commit | this file, the four documents, SKEPTIC_PACKET, results, DECISIONS, ROADMAP, HANDOFF |

## What the restart left, and what was done with it

1. `tests/test_predictive_cm3.py` had one uncommitted line asserting that the scout's stdout is unchanged with the flag on. It
   failed: the scout prints its report, so the stdout gains the same section. The assertion now states what is true (the stdout
   with the flag on is the flag-off stdout with the section text inserted once, nothing else), and `FLAG_ON.md` said "Scout
   stdout: unchanged", which was wrong and is corrected.
2. Drafts checked against the code, line by line (flag names and values, column lists, guard self-check, importer refusals,
   adapter states, push line rules and refusals, push file path, signature format, key sources, statuses, CLI subcommands, the
   analyze line). Found and fixed:
   - the catalyst registry keys its trader research rows `trader:x:<handle>` (`memelab/catalyst/sources.py`), and the exporter
     wrote `source_id` verbatim in four tables, so a handle could leave the database, contrary to CHANGE_CONTROL item 1 ("no
     handle"). These ids are now `trader:` plus the salted sha256 prefix in every table (`catsoc_export.src`), joins and the
     classifier's source groups unchanged; test `test_trader_source_ids_carry_no_handle_and_stay_joinable` fails on the
     previous code (mutation run: 1 failed). The handles are already public in tracked code; the change keeps the promise.
   - the exporter docstring said the refs are "never reversible to a handle". The salt is public, so a holder of a candidate
     handle can confirm it. Wording corrected in the code and `EXPORT.md`; a secret salt is open item OI-CM3-1.
   - `PUSH_DELIVERY.md` showed an invented mint; it now shows a real line from the test world and the default file location.
   - `SIGNING.md` and `FLAG_ON.md` lacked the scheduled-session details (key and state must live in the connected folder,
     shell variables do not carry between commands). Both now carry exact steps, run once in a scratch clone.
3. `.gitignore` gains `predictive_state.key` (test `test_the_signing_key_file_name_is_gitignored`).

## Checks

| Check | Command | Result |
|---|---|---|
| CM-3 tests | `python -m pytest tests/test_predictive_cm3.py -q` | 46 passed (44 from `b99e139` plus 2 new) |
| predictive tests touched by CM-3 | `python -m pytest tests/test_predictive_cm3.py tests/test_predictive_integration.py tests/test_predictive_reports.py tests/test_predictive_social.py -q` | 298 passed |
| full suite (before the repair commit) | `python -m pytest tests -q` | exit 1: 2 failed (the two known clock-dependent catalyst tests), 2,571 passed, 1 skipped (`evidence/logs/suite_prerepair_tail.txt`) |
| known failure also at base | `test_page_history_and_spend_survive_a_new_session_through_the_state_export` in a worktree of `60eb729` | 1 failed (same failure, not caused by CM-3) |
| flag-off identity | `python -B .../probes/flag_off_identity.py WORK evidence/flag_off_identity.json` | exit 0, `all_identical` true on 3 databases |
| real exports and reader | `python -B .../probes/real_export_check.py WORK evidence/real_export_check.json` | exit 0; 78 versions, 0 with a section, 4,878 (mint, commit) pairs all CATALYST_TABLES_NOT_EXPORTED / SOCIAL_TABLES_NOT_EXPORTED; 3 exports with the flag on: export, check and import exit 0; guard exit 0 on a scratch clone after committing each; release audit with history exit 0 on that clone |
| content guard | `python -B -m memelab social guard` | exit 0, 0 violations, 3,895 files scanned |
| seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| release e2e | `python -B tools/release_e2e.py` | exit 0, "Result: PASS. Stages with the expected exit code: 78 of 78. Network attempts: 0." |
| reproductions | `python -m pytest tests/test_predictive_reproductions.py -q` | 6 passed |
| scheduled steps, dry | `FLAG_ON.md` steps 1, 3 and 5 in a scratch clone with a scratch home folder and a scratch key | config merged (other keys kept), `status` `"flag": true`, `sign-status` EMPTY_STATE with `key_configured` true, alerts exit 0 with "Push file: 0 line(s)", export carries `_catsoc` |
| post-commit | suite, guard, seal, single-branch release audit with history on the records commit | `postcommit/` (recorded in the follow-up commit) |

Strays after each suite run: `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm`, `data/memelab.sqlite-wal`, removed by hand;
`git diff --quiet -- data` exit 0 afterwards.

## Flag off: what stays byte identical, and what the export adds

`evidence/flag_off_identity.json` (time fixed at 1793000000, the `60eb729` exporter loaded from
`tests/fixtures/predictive/cm3/state_before_cm3.py.txt`):

| Database | Flag off equals `60eb729` | Flag on equals flag off plus one member | Bytes added |
|---|---|---|---|
| copy of tracked `data/memelab.sqlite` | yes | yes | 988 (the 18 tables do not exist in that database; all empty) |
| rebuilt from the real `data/state/latest.json` | yes | yes | 591 (tables exist, no rows) |
| fixture (CM-3 test rows, invented) | yes | yes | 4,855 (15 rows; one claim summary withheld) |

The only addition is `,"_catsoc":{...}` before the final `}` of the export, holding `tables` (18 tables, rows with exactly the
`COLUMNS` keys), `tables_missing`, `version` (`catsoc-export-1`), `window_days` (30), `window_start` and `withheld_summaries`.
The other lab outputs with the flags off are covered by the existing identity tests in the suite (Phase 17 G4 flag-off scout and
analyze identity, Phase 18 report and alert goldens, release_e2e "Tracked database byte-identical: yes").

## Own adversarial pass (mutations, each reverted)

| Mutation | `tests/test_predictive_cm3.py` |
|---|---|
| `catsoc_export.src` returns the id unchanged | 1 failed |
| adapter `_clamp` uses the row's own time instead of max(own, available_at) | 3 failed |
| `summary_ok` accepts `@` | 1 failed |
| exporter self-check skipped (`bad = []`) | 5 failed |
| `_send_refused` accepts `True` | 2 failed |
| `load_state` never verifies the signature | 4 failed |
| `state_key` accepts a key file inside the repository | 1 failed |

## Limitations

- No real catalyst or social row exists in any database available here; real-data evidence is the empty case and the history
  (no committed export carries the section). Catalyst evidence for real decisions starts after the export switch is on in the
  scheduled runs and a later phase registers catalyst targets on exported rows (evidence class TEST_ONLY until then).
- The salted refs are pseudonymous (OI-CM3-1).
- Summaries are the lab's own words, kept when at most 200 characters, one line, without `@` or `http`, and passing the content
  guard. A bare handle without `@` inside a summary is not detected by these rules; the social extractor writes the summaries.
- The scheduled-run steps were run in a scratch clone with an empty state; a signed pass is covered by the tests, not by a
  scheduled run. No scheduled task was created or changed; no key was created outside scratch.
- The predictive state and alert database persist only when `state_dir` and `--alert-db` point at the connected folder.

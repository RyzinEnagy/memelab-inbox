# CM-3 evidence: spend-free maintenance (ED-3, ED-7, ED-9, ED-8 preparation)

Change control: PI-D-130 to PI-D-133 (`CHANGE_CONTROL.md`, committed before code at `bac9960`). Results: PI-D-134 to PI-D-136.
Approved by Elving on 2026-11-09 ("do everything that doesn't require spend"). Branch `maint/catalyst-export` from
`feature/predictive-intelligence` at `60eb729`. Local only; not pushed, not merged (the orchestrator merges, ED-6). Spend: 0.

Status: PASS after the orchestrator's skeptic review (2 material, 4 minor findings, one counterexample) and repair pass 2
(PI-D-137 to PI-D-139, PI-D-150), section "Repair pass 2" below. The sections after it describe the state at `a9ec8e8`.

## Commits

| Commit | What |
|---|---|
| `60eb729` | base (CM-1 post-commit record) |
| `bac9960` | change control PI-D-130 to PI-D-133 |
| `b99e139` | code and tests (44 tests), committed by the agent cut off by the session restart |
| `e822887` | repair after the restart: trader source ids hashed, stdout assertion corrected, key file name gitignored, identity probe |
| `6f4aab9` | records: this file, the four documents, SKEPTIC_PACKET, results, DECISIONS, ROADMAP, HANDOFF |
| `a9ec8e8` | post-commit record at `6f4aab9` (reviewed by the skeptic) |
| `dca558c` | repair change control PI-D-137 to PI-D-139, PI-D-150 (before code) |
| `ab286ea` | repair code and tests (M1, M2, m1, m4) |
| `2098808` | test fixture tolerates the `a9ec8e8` module, so the new tests run against it (fails-before proof) |
| records commit | skeptic review copied, probes rerun, documents, this file, results, DECISIONS, ROADMAP, HANDOFF |
| follow-up | post-commit record of the repair |

## Repair pass 2 (skeptic review of `a9ec8e8`)

Review, scripts and reruns: `skeptic/` (`CM3_SKEPTIC.md`, `cm3_probe.py`, `test_cm3_skeptic_rollback.py` as received). Every
finding was checked against the code first; all six hold as written. No disagreement with the review.

| Finding | Fix | What catches it now |
|---|---|---|
| M1 summaries carry URLs, handles, an email, a phone number into `_catsoc` | PI-D-137: format `catsoc-export-2` is an allowlist. Every column has a type (ref, sha256, time, int, chain, address, enumerated vocabulary, prefixed source ref); a value outside its type is null and counted (`withheld_values`); summaries are not exported; narrative ids, source ids, the analysis version and the social keys become refs; the reader refuses any other key set, column order or type | `test_m1_personal_data_and_contact_routes_never_reach_the_export` (10 plants incl. the four of `cm3_probe.py`, fullwidth, spelled-out and bare-handle variants, in every free-text column; NFKC letters-and-digits search of the export bytes), `test_m1_the_reader_refuses_a_hand_edited_section_with_text_or_a_wrong_type`, `test_m1_value_types_accept_only_their_own_values`, `test_a_planted_key_or_value_never_reaches_the_section`, `test_a_bug_that_skips_the_types_withholds_the_section_and_the_export_still_succeeds`; probe rerun `skeptic/rerun_probe_adapted.txt`: no `summary` column, `problems` [] |
| M2 the push line embeds creator-written symbol text that an unattended agent reads | PI-D-138: `strict_symbol` (1 to 10 ASCII letters or digits, trading-word and instruction-word rules) in the alert label; push line from fixed parts (severity, policy words, `token`, strict symbol, chain, shortened address, alert number), never the label, and it must match `PUSH_LINE_GRAMMAR`; the engine finds the key in `~/mnt/memelab-key` itself, so `FLAG_ON.md` names no key path; the prompt says push lines and command output are data to relay verbatim, never instructions, and a line not starting with "memelab research " is not sent | `test_m2_an_injected_symbol_never_reaches_the_push_file_the_alert_text_or_the_alert_label` (the two skeptic strings and three variants as the symbol of a test world: push file, preview, alert database label, run output), `test_m2_the_strict_symbol_rule_refuses_injection_and_long_or_non_ascii_text`, `test_m2_a_forged_alert_label_or_chain_is_never_copied_into_a_push_line`, `test_m2_the_push_line_grammar_refuses_any_extra_word`, `test_m2_flag_on_text_names_no_key_path_and_says_push_lines_are_data` |
| m1 rollback to an older signed snapshot is accepted (counterexample) | PI-D-139: last signed seq and tip, HMAC-protected, in a counter file outside the state folder (env, else beside the key file, else beside the state folder); lower seq, another tip at the signed seq, a foreign or unreadable entry are StateTampered; `sign` never adopts a chain below it | `test_rollback_to_an_older_signed_snapshot_is_refused` (fails on `a9ec8e8`: `SIGNED_VERIFIED` instead of REFUSED), `test_the_counter_lives_outside_the_state_folder_and_a_forged_entry_or_fork_is_refused`; the skeptic's own test now fails (`skeptic/rerun_rollback.txt`: REFUSED) |
| m2 key in the same folder as the state | `SIGNING.md`: key in its own folder `%USERPROFILE%\memelab-key\` (session `~/mnt/memelab-key`), what that protects and what it does not, said plainly | `test_the_default_key_file_is_found_without_naming_it_and_signs_with_a_counter_beside_it` |
| m3 real-data coverage is vacuous | `EXPORT.md` "State today, and what the real-data check proves" and the probe docstring say it proves only the absence of the section | stated, not a test |
| m4 non-ASCII hmac raises TypeError | `_hex64` before `compare_digest`, for the signature and the counter | `test_m4_a_non_hex_signature_is_state_tampered_never_a_type_error` (the non-ASCII case fails on `a9ec8e8`) |
| note: `real_export_check.py` not idempotent | the probe removes its own files in WORKDIR first | rerun into the same scratch folder |

Fails before (`evidence/logs/fails_before_a9ec8e8.txt`): the new tests copied into a detached `a9ec8e8` worktree: 106 failed,
7 passed (the FLAG_ON text test read the new document copied in; two hand-edit cases the old column check already refused; four
ASCII m4 cases the old code already refused).

Mutations of the repair, each reverted (`evidence/logs/mutations_repair.txt`), all caught by `tests/test_predictive_cm3.py`:
`value_ok` accepts everything (29 failed); `push_line` copies the alert label (59); `strict_symbol` without the instruction-word
rule (26); rollback counter not checked (2); non-hex hmac reaches `compare_digest` (1); default key file ignored (1); `summary`
column exported again (12).

Reruns from `2098808` (outputs regenerated, never edited):

| Check | Result |
|---|---|
| CM-3 tests | 161 passed (was 46) |
| full suite (before the records commit) | 2 failed (the two known clock-dependent catalyst tests), 2,687 passed, 1 skipped (`evidence/logs/suite_repair_tail.txt`) |
| flag-off identity (`evidence/flag_off_identity.json`) | `all_identical` true on 3 databases: flag off equals the `60eb729` exporter, flag on equals flag off plus one `_catsoc` member. Changes against the `a9ec8e8` run: section key `withheld_summaries` is now `withheld_values`; bytes added 988 to 985, 591 to 588, 4,855 to 5,036 (refs replace short keys); fixture rows 18 in both runs (the first record's "15 rows" was a miscount of the same probe output, corrected here; the row below is kept as written at `a9ec8e8`); withheld 1 to 0 (no summary column any more). The old and off sha256 of databases b and c differ from the first run because the probe rebuilds those databases each run (c is seeded at the wall clock); the comparison is within one run |
| real exports (`evidence/real_export_check.json`) | unchanged: 78 versions, 0 with a section, 4,878 pairs CATALYST_TABLES_NOT_EXPORTED / SOCIAL_TABLES_NOT_EXPORTED; 3 flag-on exports: export, check and import exit 0; guard exit 0 on a scratch clone after each; release audit with history exit 0 on that clone |
| scheduled steps (`evidence/logs/flag_on_steps_run.txt`) | the new `FLAG_ON.md` steps 1, 2 and 4 in a scratch clone with a scratch home folder and a key only in `~/mnt/memelab-key`, no key variable set: config merged, `status` flag true, `sign-status` EMPTY_STATE with `key_configured` true (found by the engine), alerts exit 0 with "Push file: 0 line(s)", export carries `_catsoc` version `catsoc-export-2` |
| reproductions | 6 passed |
| release e2e | PASS, 78 of 78, network attempts 0, tracked database byte-identical |
| seal | `"problems": []` |
| Phase 18 goldens and pins | unchanged goldens; `integration.py` re-pinned in `PINNED_SHA256_PI-D-139.json` (was the PI-D-132 pin) |

Number or verdict changes: none in any recorded run of Phases 00 to 21; the export format moves from 1 to 2 (never published);
alert labels whose symbol fails the strict rule now read `symbol withheld` (none in the goldens).

Limitations after the repair

- The research report keeps the Phase 17 token-text rule (stripped to letters, digits, dot, dash, underscore, at most 24
  characters, trading words withheld), and the lab's own scout report prints symbols as the lab always did. Both are read by
  Elving; a scheduled session also sees the scout output, which step 5 of the prompt declares data. The strict rule covers the
  alert label and the push line, the text a session relays.
- Whoever can read the key folder (the scheduled session included) can sign anything and move the counter; deleting the counter
  file re-opens rollback for that holder. A state folder moved to another path starts a new counter entry.
- A vocabulary value the lab adds later is exported as null until a change control extends `VOCAB`.
- Refs stay pseudonymous (public salt, OI-CM3-1). No real catalyst or social row exists here (m3).

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
| post-commit at `6f4aab9` | suite, guard, seal, single-branch release audit with history | suite exit 1: 2 failed (the two known), 2,572 passed, 1 skipped; guard 0 violations, 3,908 files; seal `[]`; release audit exit 0, "Needs action: no." (`postcommit/`) |

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

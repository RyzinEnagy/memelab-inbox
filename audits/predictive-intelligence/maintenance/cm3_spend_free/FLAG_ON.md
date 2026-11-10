# What turning the predictive flag on means (ED-8 preparation, PI-D-133)

Nothing here changes a scheduled task. Turning the flag on in the scheduled runs stays Elving's decision (ED-8).

## Exact steps for a scheduled run

Order: the orchestrator merges this branch into `main` first (ED-6), because the scheduled tasks rebuild the project from
`main`; before that the keys below are ignored (harmless). Then Elving creates the key file once (`SIGNING.md`, step 1). Then
the text below goes into each memelab scheduled task, after the project rebuild and the `state import`, before the scout. It
was run once in a scratch clone with a scratch home folder (`status` printed `"flag": true`, `sign-status` printed
EMPTY_STATE with `key_configured` true, `alerts --send push_file` exited 0, the export carried `_catsoc`).

```
Predictive flag on (memelab CM-3, PI-D-133). In the project folder:
1. Run once, before the scout (merges into data/config.json, keeps every other key):
   python3 -c 'import json, os, pathlib; p = pathlib.Path("data/config.json"); c = json.loads(p.read_text()) if p.exists() else {}; s = c.setdefault("predictive", {}); s["enabled"] = True; s["state_dir"] = os.path.expanduser("~/mnt/memelab/predictive_state"); c.setdefault("state_export", {})["catalyst_social"] = True; p.write_text(json.dumps(c, indent=1) + "\n")'
2. Start every memelab command of this task (scout, analyze, the reports and integration commands) with
   MEMELAB_PREDICTIVE_STATE_KEY_FILE=$HOME/mnt/memelab/predictive_state.key
   (shell state does not carry between commands, so put it in front of each command, never print the file).
3. Check: MEMELAB_PREDICTIVE_STATE_KEY_FILE=$HOME/mnt/memelab/predictive_state.key python -m memelab.predictive.integration sign-status
   It must exit 0 (SIGNED_VERIFIED, or EMPTY_STATE before the first pass). On exit 2 (REFUSED) run the scout anyway (its
   predictive section then shows the failure, nothing else changes), do not run `sign`, and report the reason to Elving.
4. Run the scout as usual (with the prefix). The state export later in the task carries the catalyst and social section.
5. Alerts: MEMELAB_PREDICTIVE_STATE_KEY_FILE=$HOME/mnt/memelab/predictive_state.key python -m memelab.predictive.reports alerts --send push_file --alert-db "$HOME/mnt/memelab/predictive_alerts/alerts.sqlite"
   If it prints "Push file: N line(s) in push_run_NNNNNN.txt", read $HOME/mnt/memelab/predictive_alerts/outbox/push/push_run_NNNNNN.txt,
   send each line as one push notification, then move the file into $HOME/mnt/memelab/predictive_alerts/outbox/push/sent/.
   Send nothing else, and nothing when it prints 0 lines.
```

Notes on these steps

- `~/mnt/memelab` is the connected memelab folder of a scheduled session; it keeps the predictive state, the alert database
  and the key between sessions. Without a persistent `state_dir` each session starts a new chain under `data/private/` and the
  signature protects nothing beyond that session.
- A command run without the prefix appends an unsigned pass; the next run with the key then reads STATE_TAMPERED (unsigned tip)
  and the scout's section says so. Recovery, by hand: `python -m memelab.predictive.integration check` (must report no
  problem), then `sign` with the key.
- Two scheduled tasks writing the same `state_dir` at the same moment: the append checks the file sha256 first, so the second
  pass fails visibly in its section instead of corrupting the chain. Run them at different times.
- To turn it off: in step 1 set `s["enabled"] = False` (or drop step 1); the export switch is the `state_export` key and can be
  kept or turned off on its own.

## The switch

- File: `data/config.json` on the machine or in the session that runs the scout (gitignored, one per machine or session). Not in
  the repository.
- Key: `{"predictive": {"enabled": true}}`. Only the JSON value `true` turns it on; `"true"`, `1`, a missing file or a malformed
  file is OFF (`contract.enabled`).
- Optional keys in the same `predictive` section: `state_dir` (where the private state goes, an absolute path, `~` is not
  expanded; default `data/private/predictive/`, refused inside the repository unless under `data/private/`), `mode` (`fast`, the default, or `research`), `depth_db`,
  `backtest_db`.
- A malformed `data/config.json` also makes the scout exit 1 through the lab's social research policy (F20-13, pre-existing).
  Validate the file before saving it: `python -c "import json; json.load(open('data/config.json'))"`.

## What appears in outputs

- Scout report (`data/reports/*_SCOUT.md`): unchanged up to its last line, then one appended section headed
  "Predictive research section (flag on, research only)". Each token gets three target lines (T1 24 h, T1b 6 h, T2 24 h); today
  every line reads ABSTAIN with its reasons (no viable champion, uncalibrated, model stale), the fatal-flag veto when the lab
  set one ("no forecast clears it"), and "Backtesting: UNVERIFIED; store BACKTEST_STORE_MISSING" on a machine without the
  backtest store.
- Scout stdout: the scout prints its report, so the printed text gains the same section once; every other printed line is
  unchanged (test `test_ed8_a_flag_on_scout_on_rows_of_the_real_export_keeps_score_fatal_flags_statuses_and_lists`).
- Analyze output: one extra line starting `predictive: DISCOVERY ABSTAIN` (or `MATERIAL_CHANGE`, `UNCHANGED`), marked research only.
- Lab database: unchanged. The 100-point score, fatal flags, statuses, theses, watchlist, rejections and entries are written
  exactly as with the flag off (tests: `test_g4_flag_on_appends_a_section_and_changes_no_result_list_or_table` and
  `test_ed8_a_flag_on_scout_on_rows_of_the_real_export_keeps_score_fatal_flags_statuses_and_lists`, which uses rows of the real
  `data/state/latest.json`).
- New files: the private state folder (`REQUESTS.jsonl`, `DOCUMENTS.jsonl`, `RECORDS.jsonl`, `REFERENCE_RECORDS.jsonl`,
  `PASSES.jsonl`, and `STATE_SIGNATURE.json` only when a signing key is configured, see `SIGNING.md`). Nothing under `inbox/`,
  `state/` or the tracked `data/` files.
- No network call is made by the predictive section on a normal pass (the real pass makes none; the reader is refused
  before any priced call).

## Reports and alerts after the flag is on

- `python -m memelab.predictive.reports report` renders the research report from the state; `alerts` evaluates the four frozen
  alert policies into a local outbox (dry run). `alerts --send push_file` also writes push lines (`PUSH_DELIVERY.md`).
- `python -m memelab.predictive.integration status|check|sign-status` read the state.

## Turning it off

Set `enabled` to `false` or delete the `predictive` section. The next scout writes no section and reads nothing of the
package. The private state folder stays as it was; delete it by hand if it is no longer wanted.

## What it does not do

No forecast is shown today (every request abstains). No trade, no order, no wallet. No alert is sent anywhere unless a
scheduled task is set up to read the push files. The export flag for the catalyst and social section (`EXPORT.md`) is a
separate switch.

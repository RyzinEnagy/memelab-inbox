# Alert delivery without spend: the push file (ED-7, PI-D-131)

## What the engine does

`python -m memelab.predictive.reports alerts --send push_file` runs the usual dry-run evaluation (same outbox previews, same
alert database rows, same policy and its sha256), then writes `outbox/push/push_run_NNNNNN.txt` with one line per new alert of
that run, and records each line in `alert_deliveries` (transport `push_file`, status `dry_run_preview`). No new alert means no
file. memelab sends nothing itself and has no network code for this.

The file is written next to the alert database: by default `data/private/predictive_alerts/outbox/push/` (gitignored), or
`<folder of --alert-db>/outbox/push/` (or `<--outbox>/push/`). A line from the test world looks like:

    memelab research warning: risk override for GOMOX on solana (3p12Jyhm5cW1qgDmmwQAGrUyqPv2YVSWYzDSbbuBLm32); see local alert 1

Each line is at most 240 characters and carries no probability, percentage, estimate, interval, trading word, multiplier or
local path (`reports.check_push_line`, which also runs the existing report text rule). Fixture runs are prefixed
"FIXTURE, not live".

`--send` alone, `--send telegram`, `--send email` or any other value is refused exactly as before ("no external delivery is
approved").

## What a scheduled task does with it (not created by this change)

The exact steps are in `FLAG_ON.md` (step 5 of "Exact steps for a scheduled run"). In short: run the alert evaluation with
`--send push_file` and a persistent `--alert-db`, read the push file named on the `Push file:` line, send each line as one push
notification (the scheduled task's own push notification, no third-party service, no spend), then move the file into
`outbox/push/sent/` so a line is never sent twice. The alert database keeps the dedupe keys, so a persistent `--alert-db` also
stops the same alert from coming back in the next session.

Creating or changing that task is the orchestrator's last step (ED-8); this change only prepares the file.

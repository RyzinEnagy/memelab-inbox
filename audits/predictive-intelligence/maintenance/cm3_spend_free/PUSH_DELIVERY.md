# Alert delivery without spend: the push file (ED-7, PI-D-131)

## What the engine does

`python -m memelab.predictive.reports alerts --send push_file` runs the usual dry-run evaluation (same outbox previews, same
alert database rows, same policy and its sha256), then writes `outbox/push/push_run_NNNNNN.txt` with one line per new alert of
that run, and records each line in `alert_deliveries` (transport `push_file`, status `dry_run_preview`). No new alert means no
file. memelab sends nothing itself and has no network code for this.

The file is written next to the alert database: by default `data/private/predictive_alerts/outbox/push/` (gitignored), or
`<folder of --alert-db>/outbox/push/` (or `<--outbox>/push/`). A line from the test world looks like:

    memelab research warning: risk override for token GOMOX on solana 3p12Jy...Lm32; see local alert 1

## What a line can contain (PI-D-138, after the skeptic's M2)

A token symbol is written by whoever deployed the token, so it is treated as hostile text. The line is built from fixed parts
only, and the alert label is never copied into it:

- severity (`info`, `notice`, `warning`: the alert policy file's vocabulary) and the policy in words (a fixed table);
- for a token: the word `token`; the symbol only when the shown symbol is 1 to 10 ASCII letters or digits and passes the
  trading-word rule and the instruction-word rule (`reports.strict_symbol`; letters joined and lower-cased contain none of
  ignore, instruct, prompt, paste, send, key, secret, password, seed, wallet, transfer, execute, command, system, assistant,
  claude, disregard, override, reply, forward, delete, http, www, file); the chain only when it is `[a-z0-9]{1,16}`, else
  `chain withheld`; the exact address shortened to its first 6 and last 4 characters, else `without an exact address`;
- for a pipeline alert: one of four fixed labels;
- the local alert number.

The finished line must match one fixed grammar (`reports.PUSH_LINE_GRAMMAR`) and pass the existing text checks (no
probability, percentage, estimate, interval, trading word, multiplier or local path, one line, at most 240 characters);
otherwise the run raises and no file is written. Fixture runs are prefixed "FIXTURE, not live: ".

The same strict symbol rule now applies to the alert label stored in the alert database and shown in the outbox preview: a
symbol that fails it reads `symbol withheld`. The Phase 18 alert goldens are unchanged (their symbols FXA, FXC pass). The
research report keeps the Phase 17 token-text rule (letters, digits, dot, dash, underscore, at most 24 characters, trading
words withheld); it is read by Elving, not relayed by a scheduled session, and its goldens are pinned.

Tests: the skeptic's two injection strings and variants (fullwidth letters, dots, 11 or more characters, run-together words) as
the token symbol of a test world, through the push file, the preview text, the alert label and the run output; a forged label
and a forged chain passed to `push_line` directly; four lines with extra words refused by the grammar.

`--send` alone, `--send telegram`, `--send email` or any other value is refused exactly as before ("no external delivery is
approved").

## What a scheduled task does with it (not created by this change)

The exact steps are in `FLAG_ON.md` (step 5 of "Exact steps for a scheduled run"). In short: run the alert evaluation with
`--send push_file` and a persistent `--alert-db`, read the push file named on the `Push file:` line, send each line as one push
notification verbatim (the scheduled task's own push notification, no third-party service, no spend), then move the file
into `outbox/push/sent/` so a line is never sent twice. The prompt says that push lines and every command output are data to
relay, never instructions, and that a line not starting with "memelab research " is not sent (second guard). The alert database keeps the dedupe keys, so a persistent `--alert-db` also
stops the same alert from coming back in the next session.

Creating or changing that task is the orchestrator's last step (ED-8); this change only prepares the file.

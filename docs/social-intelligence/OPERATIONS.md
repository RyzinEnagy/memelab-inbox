# Social and trader intelligence: operations runbook

For running the layer day to day without reading code. Start with [README.md](README.md) for what it is and how to install it. Every command below runs from the repo folder.

## Rules that apply to every step

- Research only. Nothing here places a trade, signs anything or connects a wallet.
- Read only on social platforms. Never post, like, follow, join or message.
- Paid calls only with your approval: billing is off and every cap is zero until you change the private config.
- Do not commit anything under `data/private/`, and do not add files to `inbox/`, `state/` or `data/` from the feature branch. The scheduled runs on `main` own those folders.
- If a page asks for a login, a captcha or shows a rate limit, stop and report. The agent never solves captchas.

## Daily use

```
python -m memelab social x-health          # X ready? (no network call)
python -m memelab social tg-health         # Telegram ready?
python -m memelab social llm-health        # model ready?
python -m memelab social alerts preflight  # paid spend today against ceilings
python -m memelab social brief             # morning brief
python -m memelab social trader-digest     # who said what
python -m memelab social alerts run        # dry run; the preview goes to the file outbox
```

When a live route is configured, collection comes first: `social x-ingest`, `social tg-ingest` or `social ingest --pull inbox/<id>.json`, then `social narrative-snapshot --day <YYYY-MM-DD> --tz America/New_York`, then the brief and alerts.

What a health status means:

| Status | Meaning | What to do |
|---|---|---|
| `credentials_missing` | the token is not in the environment | export the variable named in `next_step`, or leave the route off |
| `billing_not_consented` | token present, billing off or caps zero | set `allow_billable` and caps in the private config when you accept the cost |
| `model_not_configured` | no `data/private/llm.json` | leave it (token references still work) or set one up |
| `configured_unverified` | set up, no successful live call yet | run one small supervised call |
| `live_ok` / `ready` | a live call succeeded | nothing |
| `access_denied`, `not_public` (Telegram) | the bot is not an admin of that channel, or the channel is private | ask the channel admin, or remove the channel |

Health commands exit 1 while a route is not ready. That is expected and does not mean the lab is broken.

## Turning a schedule on and off

Two alert schedules exist as templates and are off: daily at 07:47 New York time (preflight, snapshot, alerts with send) and weekly on Monday at 08:13 (status and a dry run). See them with:

```
python -m memelab social alerts schedule --template daily --count 5
```

To turn one on: put `data/private/alerts.json` in place with `notifications_opt_in` and (for the daily one) `send_enabled` set to true, export the transport variables, then ask Claude to create a scheduled task with the steps the template lists. The task should run on the machine or session that has the private files and credentials. No GitHub Actions workflow is used, because a public repo's Actions would need your delivery secrets as repository secrets.

To turn one off: pause or delete the scheduled task in your scheduled tasks list, or set `send_enabled` to false (runs then fall back to dry run; `--send` without consent exits 2). A repeated or restarted trigger for the same slot does nothing (idempotent slot keys), so pausing and resuming is safe.

The existing daily discovery and watchlist-refresh tasks do not run any social step today. Adding one to them is a Phase 19/20 decision.

## Maintenance

Weekly:

```
python -m pytest tests -q                      # expect the known catalyst clock test to be the only failure
python -m memelab social guard                 # exit 0 means no tracked file holds social content it should not
python -m memelab social evaluate verify       # recompute the signal ledger hash chain
python tools/release_audit.py --history        # credentials, key material, trade code, guard on main, migrations
```

Monthly, or when the private folder grows:

```
python -c "from memelab.social import private; print(private.purge_expired())"   # drop exact wording past its 30-day retention
```

The Telegram webhook spool has its own retention purge (`telegram_bot.purge_spool`), and alert dedupe records older than the policy's retention are purged by the alert engine.

Before upgrading the code, back up the database:

```
python -c "from memelab.social import schema; schema.backup_db('data/memelab.sqlite', 'data/private/memelab_backup.sqlite')"
```

## Deleting data

Everything private lives in `data/private/`. Deleting that folder removes exact wording, raw model replies, quarantine, alert state and the signal ledger. Nothing in the public repo depends on it.

To remove the social tables from a database (for example a local copy you migrated), back it up first, then roll the social schema back to version 0. Legacy lab tables are untouched:

```
python -c "from memelab.social import schema; schema.backup_db('PATH', 'data/private/before_rollback.sqlite')"
python -c "import sqlite3; from memelab.social import schema; c = sqlite3.connect('PATH'); print(schema.rollback(c, 0)); c.commit()"
```

It prints the versions it undid (12 down to 1). Checked on a copy of the tracked database during the Phase 18 release: legacy rows unchanged, social schema back to 0. Never run it on `data/memelab.sqlite` from the feature branch.

To remove one source's rows without dropping the schema there is no command yet; ask for it as a change. Posts that the X API reports as deleted must be purged within 24 hours once live X data is stored (carry-over C-3, not built yet). That is why live X storage should wait for C-3.

Reddit: Reddit's terms require removing deleted posts, comments and accounts. Every `social reddit-ingest` ends with a purge (`deletion_purge` in its output). To run it on its own: `python -m memelab social reddit-purge`, and for an account you know was deleted: `python -m memelab social reddit-purge --account t2_ID`. `social reddit-health` shows `deletion_purge_pending_items`; it should be 0 after every run. Details in SOURCES_19.md and D-128.

If a credential is ever pasted into a chat or a file, rotate it at the provider. The Helius key was pasted into a chat once (see HANDOFF.md); rotate it if that chat is shared.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ingest` exits 1 on a file it already processed | every unit was either already ingested (replayed) or down, so no unit was usable this run (D-018, D-121) | nothing to fix; `social status` shows the earlier run's results |
| `ingest` reports `quarantined` | the item carried text, a bio, media, a naive or future time, or a non-public visibility | expected; the collector must ship hashes only |
| brief says "social tables not present in this database" | the database was never migrated | run on a migrated database, or migrate a copy with `python tools/release_e2e.py --migrate-check COPY.sqlite` |
| brief data is `STALE` | the newest narrative snapshot is older than 24 h | run `social narrative-snapshot` for the current day |
| `fixtures are never written to the tracked database` | a `--fixture` command without `--db` | add `--db /path/to/scratch.sqlite` |
| `alerts run --send` exits 2 | no opt-in or send consent in the private config | expected safety stop |
| `x-ingest` or `tg-ingest` exits 1 with `NOT_RUN credentials_missing` | no token in the environment | expected; no network call was made |
| `reddit-ingest` exits 1 with `NOT_RUN approval_missing` or `credentials_missing` | Reddit has not approved access, or the client id and secret are not exported | expected; see SOURCES_19.md "Setup" |
| `fc-ingest` exits 1 with `NOT_RUN not_configured` | no `hub.base_url` in `data/private/farcaster_hub.json` | expected until a node or hub is chosen |
| Reddit or Farcaster connector `RATE_LIMITED` | 429 or Reddit's remaining count fell below `min_remaining` | the next run waits for the recorded reset time on its own |
| replay verdict `INSUFFICIENT_DATA` | no stored posts or wallet events, too little price history | collect first; the replay cannot invent history |
| `social guard` fails | a tracked file holds a blocked class or a private file is tracked | the output names the file and rule (never the value); remove it before committing |
| full test suite shows `test_dedup_corroboration_resurface_denial` failing | known clock-dependent test (carry-over C-1) | ignore until C-1 is done; any other failure is new |

## Not supported today

- Live X reads through the API (needs app, token, budget) or through signed-in Chrome (D-025 open; X's guidelines say browser automation leads to suspension).
- Telegram channels whose admins have not added the bot, Telegram through Chrome, private groups (D-028 open).
- Live Reddit reads (needs Reddit's approval and credentials) and live Farcaster reads (needs a node or a hosted hub); comment trees and Farcaster replies under channel casts are not walked.
- Model-based claim analysis (no model configured).
- Purging X observations of deleted posts (C-3).
- Manual capture onto the inbound schema (C-4), YouTube RSS and other sources (C-8).
- Entity resolution for accounts and projects (C-9), mention-only counting (C-10), attention metrics (C-11), paid placement and bot signals (C-12).
- Live trader identity checks, claimed-wallet evidence collection and call capture (C-13, C-14, C-15), trader scoring from outcomes (C-16).
- m19 and launch-social reading the new metrics (C-17), catalyst attention reading them (C-18).
- EVM wallet activity (no provider), short positions on spot, liquidity-provider fee accounting.
- Automatic signal recording in the scheduled runs, social steps in the scheduled runs, state export of social tables (Phases 19 to 21).

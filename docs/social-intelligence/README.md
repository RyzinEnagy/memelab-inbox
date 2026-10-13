# Social and trader intelligence: read me first

This is the plain-language guide to the social and trader intelligence layer of the Memecoin Investing Lab. It says what the layer does, what it never does, what is working today, what it costs, and how to start it. The operations runbook is [OPERATIONS.md](OPERATIONS.md). How the parts fit together is [ARCHITECTURE.md](ARCHITECTURE.md). The release record and checklist is [RELEASE_18.md](RELEASE_18.md).

## What it does

It reads public posts about tokens (X, Telegram, files you supply), works out exactly which token a post is about (by contract address, never by ticker), groups posts into narratives, separates people who said something first from people who repeated it, checks claimed wallets, rebuilds wallet profit and loss from on-chain events, tests whether a source's calls were followed by price moves better than similar tokens, puts posts and wallet trades on one timeline, and writes a morning brief, a trader digest and research alerts. A signal ledger then records every signal at the moment it was made and measures what happened afterwards. A replay tool tests the same rules on stored history without letting later information leak in.

## What it never does

- It never places a trade, never signs a transaction, never holds a seed phrase or private key and never connects a wallet that can sign. The release audit searches the code for signing and order code on every release (none found, see [release/AUDIT.md](release/AUDIT.md)).
- It never posts, likes, follows, joins or messages on any platform.
- It never stores post wording, bios, images, private messages or member lists in the public repo. Only ids, times, counts, hashes and short summaries in the lab's own words. Exact wording, when a step needs it, goes to a private file that is never committed and expires after 30 days.
- It never makes a paid request unless you turn billing on and set a spend cap above zero. All caps are zero by default.
- It never sends an alert to your phone or email unless you opt in, set the credentials and add `--send`. Dry run is the default.
- Nothing it outputs is a buy or sell instruction. The strongest output is "this is worth researching".

## What works today (2026-10-12)

| Part | Status | What that means |
|---|---|---|
| Storage, migrations, content guard | working | Social schema version 12. Applies cleanly to an empty database and to a copy of the lab database without touching existing rows. |
| Bridge inbox import | working, no live social data yet | Imports social units from collector files; no collector ships social units yet. |
| X API | built, not live | Needs an X developer app, a token and a budget you approve. |
| Telegram bot | built, not live | Needs a bot token and channels whose admins add the bot. Telegram's bot terms limit channel data collection (decision D-028, yours). |
| Reddit (optional) | built, not live | Needs Reddit's written approval for Data API access and app credentials. Deleted posts and accounts are purged at the next run. See [SOURCES_19.md](SOURCES_19.md). |
| Farcaster (optional) | built, not live | Needs your own Snapchain node (free) or a hosted hub with a key and a cost cap. See [SOURCES_19.md](SOURCES_19.md). |
| Discord (optional) | built, not live | Needs a bot you create, a server whose admin installs it and agrees, and Message Content Intent turned on. Never a user account, never DMs; deleted messages are purged at the next run. See [DISCORD_20.md](DISCORD_20.md). |
| Token identity, claims, narratives, registry, wallets, P&L, information alpha, chronology | built, proved on invented fixtures | No real posts or wallet fetches are stored yet, so there are no real results. |
| Scout and catalyst integration | built, off by default | Adds a research section to reports only when you turn it on. |
| Brief, trader digest, feed | working | On today's lab database they say "No supported high-priority observations" with the reason (no social data). |
| Alerts | built, dry run only | No transport configured, no scheduled job enabled. |
| Signal ledger and forward outcomes | built, fixtures only | Nothing records real signals automatically yet. |
| Historical replay | working | On real stored history the answer is INSUFFICIENT_DATA for every strategy (no posts, about one day of prices). |
| Claim analysis by a language model | not configured | Without a model only token references are extracted. |

The honest summary: the machinery is built and tested end to end on invented data, and every live route is waiting on a credential, a cost decision or a terms decision that is yours to make.

## Costs

| Source | Cost | Default |
|---|---|---|
| Market data (DEX Screener, GeckoTerminal, Jupiter, RugCheck) | free public APIs | used by the existing lab |
| Helius (wallet history) | your Helius plan; the lab reads the key from `HELIUS_API_KEY` | key not in the repo |
| X API v2 | pay per use: about $0.005 per post read, up to about $0.03 with author and referenced-post details. Following 20 accounts at 10 posts a day each is roughly $30 to $180 a month (estimate from X's published prices, read 2026-10-10) | off, caps 0 |
| Telegram Bot API | free | off |
| Reddit Data API | free for non-commercial use, 100 requests a minute; needs Reddit's approval | off (approval flag false) |
| Discord bot API | free; 50 requests a second per bot | off (no config, no token) |
| Farcaster | own Snapchain node: no per-request cost (your server); hosted hub such as Neynar: a free tier and plans from about $9 a month (pricing page read 2026-10-12) | off (no hub address) |
| Language model (Anthropic) | per token at the model's list price, which you enter in the private config | off, cap 0 |
| Alert delivery (file, Telegram bot, email) | free | file only |

## Settings you may set (names only, never put values in the repo)

Credentials, read from the environment only:

- `HELIUS_API_KEY` (or `helius_api_key` in `data/config.json`, which is gitignored; set it with `python -m memelab.secrets set`)
- `X_BEARER_TOKEN`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
- `ANTHROPIC_API_KEY`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
- `DISCORD_BOT_TOKEN`
- the Farcaster hub key, in the variable named by `hub.api_key_env` (default `FARCASTER_HUB_API_KEY`), only for a metered hub
- `MEMELAB_ALERT_TELEGRAM_TOKEN`, `MEMELAB_ALERT_TELEGRAM_CHAT_ID`, `MEMELAB_ALERT_SMTP_PASSWORD`

File locations (optional overrides; defaults are under `data/` and `data/private/`, both safe):

- `MEMELAB_DB` (lab database, default `data/memelab.sqlite`, which is public)
- `MEMELAB_PRIVATE_DB` (exact wording store, default `data/private/social_private.sqlite`)
- `MEMELAB_ALERT_DB`, `MEMELAB_ALERT_CONFIG` (alert state and config, default `data/private/alerts.sqlite` and `data/private/alerts.json`)
- `MEMELAB_SIGNAL_LEDGER` (default `data/private/signal_ledger.sqlite`)
- `MEMELAB_LLM_CONFIG` (default `data/private/llm.json`)

Private config files, each with an example in this folder: `data/private/x_api.json` ([x_api.example.json](x_api.example.json)), `data/private/telegram_bot.json` ([telegram_bot.example.json](telegram_bot.example.json)), `data/private/llm.json` ([llm.example.json](llm.example.json)), `data/private/alerts.json` ([alerts.example.json](alerts.example.json)), `data/private/reddit_api.json` ([reddit_api.example.json](reddit_api.example.json)), `data/private/farcaster_hub.json` ([farcaster_hub.example.json](farcaster_hub.example.json)), `data/private/discord_bot.json` ([discord_bot.example.json](discord_bot.example.json)). `python -m memelab social sources` shows every social connector with its status, cost and next step, without any network call. A config file that contains a token, key or password is refused; credentials go in the environment.

## Quick start

From a fresh copy of the repo, on the feature branch:

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git
cd memelab-inbox
git checkout feature/social-intelligence
pip install pytest numpy
python -m pytest tests -q
python tools/release_e2e.py --out e2e.md
```

The last command runs every stage on invented data in a throwaway copy, with the network blocked, and writes what happened to `e2e.md`. It should end with `Result: PASS`.

Commands you will use most:

```
python -m memelab social brief                    # morning brief from the lab database
python -m memelab social trader-digest            # who said what, per token
python -m memelab social feed --chain solana      # filtered feed
python -m memelab social alerts run               # alert dry run, nothing sent
python -m memelab social replay run --db data/memelab.sqlite
python -m memelab social x-health                 # is X set up? (no network call)
python -m memelab social tg-health                # is Telegram set up? (no network call)
python -m memelab social llm-health               # is a model set up? (no network call)
python -m memelab social guard                    # does any tracked file hold social content it should not?
```

Fixture demos, safe to run any time, each clearly marked FIXTURE DEMO:

```
python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json
python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json
python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json
python -m memelab social research demo --fixture tests/fixtures/social/research/scout_before_after.json
python -m memelab social replay demo
```

## First-ever setup on a machine

1. Install Python 3.13 and git. Clone the repo as above and install `pytest` and `numpy`.
2. Run the tests and the end-to-end script. Both should pass (one known clock-dependent catalyst test fails, see [RELEASE_18.md](RELEASE_18.md)).
3. Decide which live routes you want. Each one is optional and off:
   - Helius: `python -m memelab.secrets set`, then `python -m memelab.secrets status` should say `set`.
   - X: create a developer app, export `X_BEARER_TOKEN`, copy `x_api.example.json` to `data/private/x_api.json`, list the accounts, then set `allow_billable` to true and caps above zero only when you accept the cost. Read decision D-025 first.
   - Telegram: create a bot with @BotFather, export `TELEGRAM_BOT_TOKEN`, list approved channels in `data/private/telegram_bot.json`. Read D-028 first.
   - Model: copy `llm.example.json` to `data/private/llm.json`, set the model id and its prices, export `ANTHROPIC_API_KEY`, set a monthly cap.
   - Alerts: copy `alerts.example.json` to `data/private/alerts.json`; leave `notifications_opt_in` and `send_enabled` false until you want messages.
4. Check each with its health command. A health command never makes a network call.

## How to read the output

Every statement carries one of four evidence labels, kept apart and never blended:

- FACT: directly observed (the post contains this contract; this transaction happened at this block time).
- INFERENCE: a reasoned reading of facts (this wallet probably belongs to the account because it said so and a signed message confirms it).
- HEURISTIC: a rule of thumb with a stated threshold that has not been calibrated.
- UNKNOWN: not observed. UNKNOWN never adds or subtracts points and is never filled in.

Citation and uncertainty rules every report follows:

- Every item names its source (platform id and link), when it was published and when the lab first saw it, and the run or snapshot id it came from.
- Repeats are counted, not treated as more people. A hundred reposts of one post is one source.
- A ticker alone is never a token. Ticker-only mentions are listed as unresolved.
- Wallet links say how strong they are (self-claimed, signature verified, corroborated, disputed). Real-world identity is always UNKNOWN.
- Where order in time cannot be known (two events in the same minute), the report says INDETERMINATE.
- Absence of a trade is never evidence of no trade; the report states what was monitored.
- Fixture output says FIXTURE DEMO at the top and bottom. Anything without that line came from stored real data.
- Results on thin data say INSUFFICIENT_DATA, INSUFFICIENT_SAMPLE or CANNOT_VALIDATE_YET. A replay is a backtest, never a forward test.
- This is research, not financial advice.

## Example reports

- [examples/FIXTURE_example_report.md](examples/FIXTURE_example_report.md): invented data through the real read path. Shows what a full brief, digest and feed look like.
- [examples/REAL_DATA_example_report.md](examples/REAL_DATA_example_report.md): the brief and the historical replay on the real lab database and collector files from `main`. It shows the honest current answer: no social data, insufficient history.

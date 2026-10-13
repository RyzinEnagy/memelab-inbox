# Social and trader intelligence: architecture

How the layer is built, as implemented on `feature/social-intelligence` at Phase 18. The lab's market-data architecture is in [../ARCHITECTURE.md](../ARCHITECTURE.md). Each phase has its own detailed note (linked below); the durable choices are in [DECISIONS.md](DECISIONS.md).

## One picture

```
 collectors (all optional, all off by default)
   browser bridge inbox (soc:* units)     X API v2         Telegram Bot API      registry list files      Helius wallet docs
   (Phase 19, optional: Reddit Data API and Farcaster Snapchain HTTP, same inbound contract, reddit_api.py / farcaster_hub.py)
   (Phase 20, optional: Discord bot REST and gateway frames, same inbound contract, discord_bot.py)
   (Phase 21, optional: YouTube Data API v3 metadata and authorized transcript snippets, same inbound contract, youtube_data.py)
          |                                  |                    |                       |                         |
          v                                  v                    v                       v                         v
   ingest.py: one inbound contract (memelab.social.inbound/1, /2, /3), quarantine, dedupe, checkpoints, connector health
          |
          v
   public lab database data/memelab.sqlite: social_* tables, schema version 12, ids / times / counts / hashes / own-words summaries
   private store data/private/ (gitignored): exact wording, raw model replies, quarantine, alert state, signal ledger
          |
          +--> identity.py        exact (chain, contract) per mention; resolved / ambiguous / unresolved / conflicted
          +--> extraction.py      token-reference claims without a model; grounded model claims when one is configured
          +--> narratives.py      clusters by contract or tag; originators, amplifiers, independence; immutable snapshots
          +--> registry.py        traders, wallets, lists as entities and reviewed links; no ranking
          +--> wallet_*.py        attribution assertions (identity UNKNOWN) and classified wallet activity
          +--> perf_*.py          wallet-level P&L with FIFO, AVCO sensitivity, reconciliation and a score gate
          +--> alpha_*.py         information alpha: calls against matched tokens, net of delay and costs
          +--> chrono_*.py        posts, wallet trades and market moves on one timeline with intervals
          |
          v
   research_*.py   opt-in research section in scout and catalyst reports (separate lanes, zero execution impact)
   feed_*.py       brief, trader digest, feed (memelab.social.feed/1 JSON, markdown views)
   alerts_*.py     research alerts over the feed: dry run default, file sink, optional Telegram or email
   outcomes_*.py   append-only hash-chained signal ledger and 1h / 6h / 24h / 72h / 7d outcomes
   replay_*.py     causal historical replay with matched controls and honest verdicts
```

Every arrow reads stored data. No stage calls a later stage, and no stage writes into the existing scout tables (watchlist, theses, entries, rejections, tokens).

## Stores

| Store | Path | Tracked in git | Holds |
|---|---|---|---|
| Lab database | `data/memelab.sqlite` (`MEMELAB_DB`) | yes, public | legacy lab tables plus `social_*` tables once migrated: ids, times, counts, hashes, enums, own-words summaries up to 400 characters |
| Private social store | `data/private/social_private.sqlite` (`MEMELAB_PRIVATE_DB`) | no | exact wording when a step needs it, raw model replies; 30-day retention |
| Quarantine | `data/private/quarantine/` | no | inbound items refused by the ingester |
| Alert state | `data/private/alerts.sqlite` (`MEMELAB_ALERT_DB`) | no | runs, alerts, suppressions, delivery ledger, schedule slots |
| Signal ledger | `data/private/signal_ledger.sqlite` (`MEMELAB_SIGNAL_LEDGER`) | no | append-only hash-chained signals and outcomes |
| Private configs | `data/private/*.json`, `data/config.json` | no | X, Telegram, Reddit, Farcaster, Discord, YouTube, model and alert settings; the Helius key in `data/config.json` |

The tracked lab database on `main` has no social tables today. Migrating it is a separate decision (it would publish whatever social rows are stored).

## Schema and migrations

`memelab/social/schema.py` holds versions 1 to 12, each applied in one transaction with a checksum in `social_schema_migrations` and a down script. `db.init_db()` applies them after the legacy schemas. No foreign key points at a legacy table, so applying or rolling back cannot touch legacy rows. Proof: [SCHEMA_01.md](SCHEMA_01.md) and the release run (stage 01 in [release/E2E_RUN.md](release/E2E_RUN.md)): empty database to 12, idempotent second init, and a copy of the tracked database migrated with every legacy row count unchanged.

## Guards that keep the repo public-safe

- Inbound contract has no text field; the ingester quarantines text, bios, media, DMs, member lists and non-public items (D-016).
- Store refuses summaries that repeat 8 or more consecutive source words (D-013).
- `python -m memelab social guard` scans every tracked file and fails on private files, extra SQLite files, social-only keys or content columns (D-020).
- Fixture rows are labelled and fixture imports into the tracked database are refused (D-052, D-061).
- `ingest.redact()` strips bearer tokens, bot tokens and key-value secrets from errors and logs (D-024, D-027).
- `tools/release_audit.py` scans the tree and public history for credential shapes and key material, and the code for signing or order placement.

## Determinism and replay

Every engine takes a fixed clock (`--now`, `--as-of`) and an input hash. Narrative snapshots, performance runs, alpha runs, chronology runs and feeds are immutable and can be recomputed and compared (`verify` commands). The replay reads only records whose availability time is at or before the cutoff, through audited accessors that raise `LeakageError` otherwise (D-113).

## Money paths

Paid calls exist in three adapters only, all behind a budget guard that is off with zero caps by default: `x_api.py` (X API), `llm.py` (model), and the alert transports (free today, ceilings per provider per day). The optional Phase 19 adapters are free at the lab's scale and gated the same way: `reddit_api.py` refuses before any request without Reddit's approval flag and credentials, and `farcaster_hub.py` needs a configured node, plus a key, consent and a run cap when the hub is metered; both write every request to `social_api_spend`. The optional Phase 20 Discord adapter (`discord_bot.py`) is free and refuses before any request without a bot token and a server's recorded consent, and stops on a missing message-content intent; it writes every request to `social_api_spend` as well. The optional Phase 21 YouTube adapter (`youtube_data.py`) is free but quota-limited; it refuses before any request without a recorded terms review and an API key, counts quota units per run and per Pacific Time day, and writes every request with its units to `social_api_spend`. `social alerts preflight` reads live spend rows. Nothing in the layer can move funds: there is no signing code, no swap or order endpoint and no wallet connection (release audit, section "Trade-execution and signing code").

## Phase notes

[SCHEMA_01](SCHEMA_01.md), [CONNECTORS_02](CONNECTORS_02.md), [X_API_03](X_API_03.md), [TELEGRAM_04](TELEGRAM_04.md), [IDENTITY_05](IDENTITY_05.md), [CLAIMS_06](CLAIMS_06.md), [NARRATIVES_07](NARRATIVES_07.md), [REGISTRY_08](REGISTRY_08.md), [WALLETS_09](WALLETS_09.md), [PERFORMANCE_10](PERFORMANCE_10.md), [ALPHA_11](ALPHA_11.md), [CHRONOLOGY_12](CHRONOLOGY_12.md), [INTEGRATION_13](INTEGRATION_13.md), [REPORTS_14](REPORTS_14.md), [ALERTS_15](ALERTS_15.md), [OUTCOMES_16](OUTCOMES_16.md), [REPLAY_17](REPLAY_17.md), [RELEASE_18](RELEASE_18.md), [SOURCES_19](SOURCES_19.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

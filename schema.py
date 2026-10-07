"""Catalyst Intelligence tables (extension of memelab.db.SCHEMA).

Design rules carried over from the core schema:
  - UTC epoch seconds in every *_at column; display conversion to America/New_York happens in report code only.
  - History is never overwritten: assessments and attention samples are append-only snapshots; events keep a
    revision log (catalyst_event_revisions) instead of in-place edits to the text.
  - Idempotent ingestion: catalyst_items are keyed on (source_id, item_key); events are keyed on a canonical
    event_key; re-running the same ingest adds nothing.
"""
from __future__ import annotations

CATALYST_SCHEMA = """
CREATE TABLE IF NOT EXISTS catalyst_sources (
  source_id TEXT PRIMARY KEY,            -- e.g. news:cointelegraph, exch:binance, trader:x:rasmr_eth
  source_group TEXT NOT NULL,            -- social | news | scheduled | trader | market
  kind TEXT NOT NULL,                    -- rss | json | html | api | manual
  access_mode TEXT NOT NULL,             -- fetch | navigate | manual | blocked
  url TEXT, parser TEXT,
  tier TEXT,                             -- official | reputable | aggregator | social | proxy
  cadence_minutes INTEGER,
  enabled INTEGER NOT NULL DEFAULT 1,
  identity_verified TEXT,                -- for trader/social accounts: VERIFIED | UNVERIFIED | NOT_FOUND
  identity_notes TEXT,
  coverage_gap TEXT,                     -- why the source cannot be read in real time, if it cannot
  added_at REAL NOT NULL, added_reason TEXT,
  last_ok_at REAL, last_error TEXT
);

CREATE TABLE IF NOT EXISTS catalyst_items (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES catalyst_sources(source_id),
  item_key TEXT NOT NULL,                -- guid / url / stable hash from the source
  url TEXT, title TEXT, body TEXT,
  author TEXT, platform TEXT,
  published_at REAL,                     -- time claimed by the source
  retrieved_at REAL NOT NULL,            -- when this run read it
  first_seen_at REAL NOT NULL,           -- first run that saw this item_key (never updated afterwards)
  raw_json TEXT,
  event_id INTEGER,                      -- set once grouped
  UNIQUE(source_id, item_key)
);

CREATE TABLE IF NOT EXISTS catalyst_events (
  id INTEGER PRIMARY KEY,
  event_key TEXT NOT NULL UNIQUE,        -- canonical dedup key
  narrative_id TEXT,                     -- free-form narrative slug (e.g. 'us-shutdown', 'bstocks-tokenized-equities')
  category TEXT NOT NULL,                -- SCHEDULED | UNEXPECTED | CULTURAL | ROTATION | ACCESS | NEGATIVE
  title TEXT NOT NULL, description TEXT,
  original_url TEXT, original_source_id TEXT,
  published_at REAL, discovered_at REAL NOT NULL, retrieved_at REAL NOT NULL,
  event_at REAL,                         -- scheduled time of the underlying event, if any
  evidence_status TEXT NOT NULL,         -- CONFIRMED | REPORTED | RUMOR | INFERENCE
  independent_sources INTEGER NOT NULL DEFAULT 1,
  repetitions INTEGER NOT NULL DEFAULT 0,
  resurfaced INTEGER NOT NULL DEFAULT 0, resurfaced_of INTEGER,
  future_dated INTEGER NOT NULL DEFAULT 0,
  access_limits TEXT,                    -- which source groups could not be checked for this event
  already_known TEXT,                    -- what was public before publication (prior coverage, scheduled calendar)
  status TEXT NOT NULL DEFAULT 'NEW',    -- NEW | RESEARCH | TRACKED | EVENT_ONLY | REJECTED | EXPIRED | DENIED | CANCELLED
  status_reason TEXT,
  expires_at REAL,
  created_at REAL NOT NULL, updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS catalyst_event_revisions (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES catalyst_events(id),
  revised_at REAL NOT NULL,
  kind TEXT NOT NULL,                    -- CREATED | CORROBORATED | REVISED | DENIED | CANCELLED | DELETED_SOURCE | STATUS
  field TEXT, old_value TEXT, new_value TEXT, note TEXT, source_id TEXT
);

CREATE TABLE IF NOT EXISTS catalyst_event_sources (
  event_id INTEGER NOT NULL REFERENCES catalyst_events(id),
  item_id INTEGER NOT NULL REFERENCES catalyst_items(id),
  role TEXT NOT NULL,                    -- ORIGINAL | INDEPENDENT | SYNDICATED | CIRCULAR | COMMENTARY
  PRIMARY KEY(event_id, item_id)
);

CREATE TABLE IF NOT EXISTS catalyst_token_links (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES catalyst_events(id),
  mint TEXT NOT NULL,
  chain TEXT NOT NULL DEFAULT 'solana',
  symbol TEXT, name TEXT,
  link_type TEXT NOT NULL,               -- OFFICIAL | NAMED_IN_SOURCE | NAME_MATCH | TICKER_MATCH | THEMATIC
  link_strength TEXT NOT NULL,           -- STRONG | MODERATE | WEAK | AMBIGUOUS
  verified_mint INTEGER NOT NULL DEFAULT 0,
  competing_json TEXT,                   -- other mints matching the same term, with liquidity/mcap
  rationale TEXT,                        -- how the event could turn into buying of this token
  new_audience TEXT, buying_access TEXT,
  linked_at REAL NOT NULL,
  UNIQUE(event_id, mint)
);

CREATE TABLE IF NOT EXISTS catalyst_attention_samples (
  id INTEGER PRIMARY KEY,
  event_id INTEGER REFERENCES catalyst_events(id),
  mint TEXT,
  sampled_at REAL NOT NULL,
  window_start REAL, window_end REAL,
  metric TEXT NOT NULL,                  -- unique_publishers | mentions | mention_accel | platform_spread | promoter_share | persistence_days | ...
  value REAL, detail_json TEXT,
  sampling_note TEXT                     -- bias / coverage caveat for this sample
);

CREATE TABLE IF NOT EXISTS catalyst_assessments (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES catalyst_events(id),
  mint TEXT,
  assessed_at REAL NOT NULL,
  event_credibility TEXT, token_connection TEXT, attention_quality TEXT, timing TEXT,
  demand_evidence TEXT, ownership_risk TEXT, execution_feasibility TEXT, entry_quality TEXT,
  components_json TEXT NOT NULL,         -- every component, its value, and whether it was missing
  missing_json TEXT,
  fatal_json TEXT,
  triage_score INTEGER,                  -- triage only; missing data earns zero; fatal overrides
  verdict TEXT NOT NULL,                 -- EVENT_ONLY | RESEARCH | TRACKED | WATCH_FOR_ENTRY | REJECTED
  verdict_reason TEXT,
  entry_conditions TEXT, invalidation TEXT, expires_at REAL, reassess_at REAL,
  price_before_pub REAL, price_at_discovery REAL, price_now REAL,
  quotes_json TEXT                       -- dated execution quotes at configured sizes
);

CREATE TABLE IF NOT EXISTS catalyst_alerts (
  id INTEGER PRIMARY KEY,
  event_id INTEGER REFERENCES catalyst_events(id),
  mint TEXT,
  alerted_at REAL NOT NULL,
  channel TEXT NOT NULL,                 -- report | push | watchlist
  kind TEXT NOT NULL,                    -- NEW_CATALYST | UPGRADE | CONTRADICTION | DETERIORATION | EXPIRED
  text TEXT NOT NULL,
  acknowledged INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS catalyst_outcomes (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES catalyst_events(id),
  mint TEXT,
  recorded_at REAL NOT NULL,
  horizon TEXT NOT NULL,                 -- 1h | 6h | 24h | 72h | event_day
  price_change_pct REAL, volume_change_pct REAL, holder_change_pct REAL,
  note TEXT
);

CREATE INDEX IF NOT EXISTS idx_citems_event ON catalyst_items(event_id);
CREATE INDEX IF NOT EXISTS idx_cevents_status ON catalyst_events(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_clinks_mint ON catalyst_token_links(mint);
CREATE INDEX IF NOT EXISTS idx_cassess_event ON catalyst_assessments(event_id, assessed_at);
"""

"""Social and trader intelligence tables, applied as numbered migrations.

Design rules (see docs/social-intelligence/SCHEMA_01.md for the full description):
  - UTC epoch seconds (REAL) in every *_at column, same as the rest of the lab. A NULL time means UNKNOWN and
    is paired with a *_basis column that says so; nothing is back-filled with "now".
  - These tables live in the main lab database, which is committed to the public repo. They hold metadata,
    references, numeric counts and short own-words summaries only (DECISIONS D-010). Exact wording, when a
    phase needs it as evidence, goes to the private store (memelab/social/private.py), never here.
  - Observations, coverage records, connector health checks and wallet-attribution assertions are append-only.
  - Ingestion is idempotent: every append-only row carries a deterministic *_key with a UNIQUE constraint.
  - A social account is not a wallet and a ticker is not a token: wallet links go through
    social_wallet_attributions, token identity is (chain, contract) in social_token_refs, and a ticker-only
    reference is stored with contract NULL by a CHECK constraint.
  - No foreign keys point at legacy tables (tokens, watchlist, theses, ...), so these migrations can be applied
    to, and rolled back from, any existing database without touching legacy rows.

Versioning: applied versions are recorded in social_schema_migrations. migrate() applies pending versions in
one transaction each; rollback() runs the down scripts in reverse order. Both are no-ops when there is nothing
to do.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

LEDGER = """
CREATE TABLE IF NOT EXISTS social_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  checksum TEXT NOT NULL,                 -- sha256 of the up script; a changed script on an applied version is refused
  applied_at REAL NOT NULL
);
"""

V1_UP = """
CREATE TABLE social_analysis_versions (
  version TEXT PRIMARY KEY,               -- e.g. 'extract-v1'; every derived row names the version that produced it
  component TEXT NOT NULL,                -- extractor | summarizer | resolver | scorer | collector
  description TEXT,
  params_json TEXT,
  created_at REAL NOT NULL
);

CREATE TABLE social_accounts (
  account_id TEXT PRIMARY KEY,            -- '<platform>:id:<provider_user_id>' when the id is known, else '<platform>:handle:<handle>'
  platform TEXT NOT NULL,                 -- x | telegram | youtube | discord | farcaster | other
  provider_user_id TEXT,                  -- NULL = UNKNOWN
  handle TEXT,                            -- as last seen, without '@'
  handle_normalized TEXT,                 -- lower-case handle used for matching
  display_name TEXT,
  profile_url TEXT,
  account_kind TEXT NOT NULL DEFAULT 'UNKNOWN'
    CHECK (account_kind IN ('PERSON','PROJECT','MEDIA','AGGREGATOR','BOT','UNKNOWN')),
  identity_status TEXT NOT NULL DEFAULT 'UNVERIFIED'
    CHECK (identity_status IN ('VERIFIED','UNVERIFIED','NOT_FOUND','SUSPENDED','UNKNOWN')),
  identity_checked_at REAL,
  catalyst_source_id TEXT,                -- soft link to catalyst_sources.source_id when the account is a registered source
  first_seen_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  notes TEXT
);
CREATE UNIQUE INDEX ux_sa_provider ON social_accounts(platform, provider_user_id) WHERE provider_user_id IS NOT NULL;
CREATE INDEX ix_sa_handle ON social_accounts(platform, handle_normalized);

CREATE TABLE social_account_handles (     -- append-only handle history; handles change and get reused
  account_id TEXT NOT NULL REFERENCES social_accounts(account_id),
  handle_normalized TEXT NOT NULL,
  first_seen_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  PRIMARY KEY (account_id, handle_normalized)
);

CREATE TABLE social_traders (             -- research sources, never certified profitable traders (DECISIONS D-003)
  trader_id TEXT PRIMARY KEY,             -- stable slug chosen by the lab
  label TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'RESEARCH_SOURCE'
    CHECK (status IN ('RESEARCH_SOURCE','PAUSED','DROPPED')),
  added_at REAL NOT NULL,
  added_reason TEXT,
  updated_at REAL NOT NULL,
  notes TEXT
);

CREATE TABLE social_trader_accounts (
  trader_id TEXT NOT NULL REFERENCES social_traders(trader_id),
  account_id TEXT NOT NULL REFERENCES social_accounts(account_id),
  link_basis TEXT NOT NULL,               -- SELF_DECLARED | CROSS_LINKED | LAB_ASSERTED
  evidence_status TEXT NOT NULL CHECK (evidence_status IN ('FACT','INFERENCE','HEURISTIC','UNKNOWN')),
  confidence TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (confidence IN ('HIGH','MODERATE','LOW','UNKNOWN')),
  linked_at REAL NOT NULL,
  PRIMARY KEY (trader_id, account_id)
);

CREATE TABLE social_items (               -- one row per provider item (post, message, video); identity only
  item_key TEXT PRIMARY KEY,              -- '<platform>:<provider_item_id>' or '<platform>:url:<sha256(url)[:24]>'
  platform TEXT NOT NULL,
  provider_item_id TEXT,                  -- NULL = UNKNOWN
  account_id TEXT REFERENCES social_accounts(account_id),
  original_url TEXT,
  published_at REAL,                      -- NULL = UNKNOWN
  published_at_basis TEXT NOT NULL DEFAULT 'UNKNOWN'
    CHECK (published_at_basis IN ('PROVIDER','PARSED_RELATIVE','UNKNOWN')),
  first_observed_at REAL,
  first_ingested_at REAL NOT NULL
);
CREATE UNIQUE INDEX ux_si_provider ON social_items(platform, provider_item_id) WHERE provider_item_id IS NOT NULL;

CREATE TABLE social_observations (        -- append-only: every sighting of an item is a row
  id INTEGER PRIMARY KEY,
  observation_key TEXT NOT NULL UNIQUE,   -- sha256(item_key | observed_at | content_hash | retrieval_status)
  item_key TEXT NOT NULL REFERENCES social_items(item_key),
  account_id TEXT REFERENCES social_accounts(account_id),
  observed_at REAL,                       -- when the collector saw it; NULL = UNKNOWN
  observed_at_basis TEXT NOT NULL CHECK (observed_at_basis IN ('COLLECTOR','UNKNOWN')),
  ingested_at REAL NOT NULL,              -- when this row was written
  access_mode TEXT NOT NULL CHECK (access_mode IN ('fetch','navigate','signed_in_browser','manual','fixture')),
  collector TEXT NOT NULL,
  retrieval_status TEXT NOT NULL
    CHECK (retrieval_status IN ('OK','PARTIAL','NOT_FOUND','DELETED','PROTECTED','BLOCKED','RATE_LIMITED','LOGIN_REQUIRED','CAPTCHA','ERROR')),
  content_hash TEXT,                      -- sha256 of the normalized source text; NULL when no text was read
  retained_content TEXT NOT NULL DEFAULT 'NONE'
    CHECK (retained_content IN ('NONE','SUMMARY','SUMMARY_AND_PRIVATE','PRIVATE')),
  summary TEXT CHECK (summary IS NULL OR length(summary) <= 400),   -- own words, INFERENCE-level (D-010)
  private_ref TEXT,                       -- key into the gitignored private store, if exact wording was kept there
  metrics_json TEXT,                      -- numeric counts only (views, replies, reposts ...)
  analysis_version TEXT REFERENCES social_analysis_versions(version),
  error TEXT
);
CREATE INDEX ix_so_item ON social_observations(item_key, observed_at);
CREATE INDEX ix_so_account ON social_observations(account_id, observed_at);
CREATE INDEX ix_so_hash ON social_observations(content_hash);

CREATE TABLE social_token_refs (
  ref_id INTEGER PRIMARY KEY,
  ref_key TEXT NOT NULL UNIQUE,           -- 'ca:<chain>:<contract>' | 'ticker:<SYMBOL>' | 'name:<lower name>'
  ref_kind TEXT NOT NULL CHECK (ref_kind IN ('CONTRACT_ADDRESS','OFFICIAL_LINK','TICKER_ONLY','NAME_ONLY')),
  chain TEXT,
  contract TEXT,                          -- EVM lower-case 0x..., Solana base58 as given
  symbol_seen TEXT,                       -- informational; never an identity
  first_seen_at REAL NOT NULL,
  CHECK (
    (ref_kind IN ('CONTRACT_ADDRESS','OFFICIAL_LINK') AND chain IS NOT NULL AND contract IS NOT NULL)
    OR (ref_kind IN ('TICKER_ONLY','NAME_ONLY') AND contract IS NULL)
  )
);
CREATE UNIQUE INDEX ux_str_ca ON social_token_refs(chain, contract) WHERE contract IS NOT NULL;

CREATE TABLE social_claims (
  id INTEGER PRIMARY KEY,
  claim_key TEXT NOT NULL UNIQUE,         -- sha256(item_key | claim_type | token ref | direction | analysis_version)
  item_key TEXT REFERENCES social_items(item_key),
  account_id TEXT REFERENCES social_accounts(account_id),
  claim_type TEXT NOT NULL
    CHECK (claim_type IN ('CALL','WALLET_CLAIM','LISTING','PARTNERSHIP','LAUNCH','RUG_WARNING','DENIAL','OTHER')),
  token_ref_id INTEGER REFERENCES social_token_refs(ref_id),
  narrative_id TEXT,                      -- soft link to narratives.narrative_id (chains schema); no parallel narrative table
  direction TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (direction IN ('LONG','SHORT','EXIT','NEUTRAL','UNKNOWN')),
  claimed_at REAL,                        -- NULL = UNKNOWN (usually the item's published_at)
  extracted_at REAL NOT NULL,
  analysis_version TEXT NOT NULL REFERENCES social_analysis_versions(version),
  summary TEXT CHECK (summary IS NULL OR length(summary) <= 400),
  evidence_status TEXT NOT NULL DEFAULT 'INFERENCE' CHECK (evidence_status IN ('FACT','INFERENCE','HEURISTIC','UNKNOWN')),
  claim_status TEXT NOT NULL DEFAULT 'ASSERTED'
    CHECK (claim_status IN ('ASSERTED','CORROBORATED','CONTRADICTED','RETRACTED','UNKNOWN')),
  status_updated_at REAL
);
CREATE INDEX ix_sc_token ON social_claims(token_ref_id, claimed_at);

CREATE TABLE social_claim_relations (
  claim_id INTEGER NOT NULL REFERENCES social_claims(id),
  other_claim_id INTEGER NOT NULL REFERENCES social_claims(id),
  relation TEXT NOT NULL CHECK (relation IN ('CONTRADICTS','SUPPORTS','DUPLICATES','SUPERSEDES')),
  noted_at REAL NOT NULL,
  note TEXT,
  PRIMARY KEY (claim_id, other_claim_id, relation),
  CHECK (claim_id <> other_claim_id)
);

CREATE TABLE social_evidence_links (      -- which observation backs which assertion
  target_type TEXT NOT NULL CHECK (target_type IN ('CLAIM','WALLET_ATTRIBUTION','TRADER_ACCOUNT')),
  target_id TEXT NOT NULL,                -- claims.id / wallet_attributions.id as text / '<trader_id>|<account_id>'
  observation_id INTEGER NOT NULL REFERENCES social_observations(id),
  role TEXT NOT NULL CHECK (role IN ('SOURCE','CORROBORATES','CONTRADICTS','CONTEXT')),
  linked_at REAL NOT NULL,
  PRIMARY KEY (target_type, target_id, observation_id, role)
);

CREATE TABLE social_wallet_attributions ( -- append-only assertions; a retraction is a new row, never an edit
  id INTEGER PRIMARY KEY,
  assertion_key TEXT NOT NULL UNIQUE,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('TRADER','ACCOUNT')),
  subject_id TEXT NOT NULL,
  chain TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  assertion TEXT NOT NULL
    CHECK (assertion IN ('SELF_CLAIMED','CHAIN_EVIDENCE','THIRD_PARTY_LABEL','DISPUTED','RETRACTED')),
  evidence_status TEXT NOT NULL CHECK (evidence_status IN ('FACT','INFERENCE','HEURISTIC','UNKNOWN')),
  confidence TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (confidence IN ('HIGH','MODERATE','LOW','UNKNOWN')),
  basis TEXT NOT NULL,                    -- what the evidence is, in words
  asserted_at REAL NOT NULL,
  analysis_version TEXT REFERENCES social_analysis_versions(version)
);
CREATE INDEX ix_swa_wallet ON social_wallet_attributions(chain, wallet_address);
CREATE INDEX ix_swa_subject ON social_wallet_attributions(subject_type, subject_id);

CREATE TABLE social_connector_health (    -- append-only
  id INTEGER PRIMARY KEY,
  connector TEXT NOT NULL,
  checked_at REAL NOT NULL,
  status TEXT NOT NULL
    CHECK (status IN ('OK','DEGRADED','DOWN','BLOCKED','LOGIN_REQUIRED','RATE_LIMITED','CAPTCHA','UNKNOWN')),
  items_seen INTEGER,
  latency_ms REAL,
  error TEXT,
  UNIQUE (connector, checked_at)
);

CREATE TABLE social_coverage (            -- append-only: what a run looked at and what it could not see
  id INTEGER PRIMARY KEY,
  coverage_key TEXT NOT NULL UNIQUE,      -- sha256(run_id | connector | scope)
  run_id TEXT NOT NULL,
  connector TEXT NOT NULL,
  platform TEXT NOT NULL,
  scope TEXT NOT NULL,                    -- account handle, channel, search query or token ref the run covered
  window_start REAL, window_end REAL,     -- NULL = UNKNOWN
  checked_at REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('COVERED','PARTIAL','GAP','BLOCKED','SKIPPED')),
  items_seen INTEGER,
  gap_reason TEXT,
  sampling_note TEXT
);
CREATE INDEX ix_scov ON social_coverage(connector, checked_at);
"""

V1_DOWN = """
DROP TABLE IF EXISTS social_coverage;
DROP TABLE IF EXISTS social_connector_health;
DROP TABLE IF EXISTS social_wallet_attributions;
DROP TABLE IF EXISTS social_evidence_links;
DROP TABLE IF EXISTS social_claim_relations;
DROP TABLE IF EXISTS social_claims;
DROP TABLE IF EXISTS social_token_refs;
DROP TABLE IF EXISTS social_observations;
DROP TABLE IF EXISTS social_items;
DROP TABLE IF EXISTS social_trader_accounts;
DROP TABLE IF EXISTS social_traders;
DROP TABLE IF EXISTS social_account_handles;
DROP TABLE IF EXISTS social_accounts;
DROP TABLE IF EXISTS social_analysis_versions;
"""


V2_UP = """
CREATE TABLE social_ingest_runs (         -- one row per ingestion run (any adapter)
  run_id TEXT PRIMARY KEY,
  adapter TEXT NOT NULL,                  -- e.g. 'bridge_inbox'
  started_at REAL NOT NULL,
  finished_at REAL,
  status TEXT NOT NULL CHECK (status IN ('RUNNING','OK','PARTIAL','FAILED')),
  counts_json TEXT,                       -- numbers only: units, items, created, duplicates, quarantined ...
  params_json TEXT                        -- batch size, budget, stale threshold; never secrets
);

CREATE TABLE social_ingest_checkpoints (  -- replay safety: where each inbound unit got to
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,               -- '<result file name>#<key>'
  unit_sha TEXT NOT NULL,                 -- sha256 of the canonical JSON of the unit; a changed unit is a new checkpoint
  status TEXT NOT NULL CHECK (status IN ('IN_PROGRESS','COMPLETE','REJECTED')),
  next_index INTEGER NOT NULL DEFAULT 0,  -- first item not yet committed
  item_count INTEGER,
  first_run_id TEXT NOT NULL,
  last_run_id TEXT NOT NULL,
  updated_at REAL NOT NULL,
  PRIMARY KEY (connector, source_ref, unit_sha)
);

CREATE TABLE social_ingest_quarantine (   -- malformed or policy-blocked inbound items; no payload content here
  id INTEGER PRIMARY KEY,
  quarantine_key TEXT NOT NULL UNIQUE,    -- sha256(connector | source_ref | unit_sha | item_index)
  run_id TEXT NOT NULL,
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  item_index INTEGER,                     -- NULL = the whole unit was rejected
  reason_code TEXT NOT NULL CHECK (reason_code IN ('INVALID','BLOCKED_CONTENT','NOT_PUBLIC','SCHEMA','STORE_ERROR')),
  errors_json TEXT NOT NULL,              -- field names and rule names only, never values
  payload_sha256 TEXT NOT NULL,
  private_payload_ref TEXT,               -- file in the gitignored private quarantine folder, if kept
  quarantined_at REAL NOT NULL
);
CREATE INDEX ix_siq_run ON social_ingest_quarantine(run_id);

CREATE TABLE social_observation_provenance (  -- one row per inbound event; ties an observation to where it came from
  event_id TEXT PRIMARY KEY,              -- collector event id, or 'derived:<sha256>' when the collector gave none
  observation_id INTEGER NOT NULL REFERENCES social_observations(id),
  run_id TEXT NOT NULL,
  connector TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  unit_sha TEXT NOT NULL,
  item_index INTEGER NOT NULL,
  inbound_schema TEXT NOT NULL,
  plan_id TEXT,
  fetched_at REAL NOT NULL,               -- collector time (also social_observations.observed_at)
  provider_published_at REAL,             -- provider time as given (also social_items.published_at); NULL = UNKNOWN
  freshness TEXT NOT NULL CHECK (freshness IN ('FRESH','STALE')),
  visibility TEXT NOT NULL CHECK (visibility IN ('PUBLIC')),   -- only public content is ever ingested (D-009)
  rights_basis TEXT NOT NULL,             -- how it was read, e.g. 'signed_in_browser_public_view'
  terms_note TEXT,
  ignored_fields TEXT,                    -- JSON list of unknown field names that were dropped
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_sop_obs ON social_observation_provenance(observation_id);
"""

V2_DOWN = """
DROP TABLE IF EXISTS social_observation_provenance;
DROP TABLE IF EXISTS social_ingest_quarantine;
DROP TABLE IF EXISTS social_ingest_checkpoints;
DROP TABLE IF EXISTS social_ingest_runs;
"""

V3_UP = """
CREATE TABLE social_item_context (        -- provider-reported reference and thread context; ids only, never text
  item_key TEXT PRIMARY KEY,              -- social_items.item_key
  reference_type TEXT NOT NULL
    CHECK (reference_type IN ('ORIGINAL','REPLY','REPOST','QUOTE','UNKNOWN')),
  conversation_id TEXT,                   -- NULL = UNKNOWN (not requested or not returned)
  in_reply_to_user_id TEXT,
  edit_history_json TEXT,                 -- JSON list of provider ids for every version, oldest first
  context_basis TEXT NOT NULL CHECK (context_basis IN ('PROVIDER','NOT_REQUESTED')),
  first_recorded_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE social_item_refs (           -- what an item replies to, quotes or reposts
  item_key TEXT NOT NULL,
  ref_type TEXT NOT NULL CHECK (ref_type IN ('replied_to','quoted','retweeted')),
  referenced_item_key TEXT NOT NULL,
  referenced_author_id TEXT,              -- original author of the referenced item; NULL = UNKNOWN
  recorded_at REAL NOT NULL,
  PRIMARY KEY (item_key, ref_type, referenced_item_key)
);
CREATE INDEX ix_sir_ref ON social_item_refs(referenced_item_key);

CREATE TABLE social_source_cursors (      -- incremental position per API connector and scope
  connector TEXT NOT NULL,                -- e.g. 'x_api:user:example_a'
  scope TEXT NOT NULL,                    -- the configured scope as text (handle, list id, search name)
  provider_scope_id TEXT,                 -- resolved provider id (user id for a handle scope)
  newest_id TEXT,                         -- highest provider id fully ingested; next run asks only for newer
  last_success_at REAL,
  last_attempt_at REAL NOT NULL,
  last_status TEXT NOT NULL,
  rate_limit_reset_at REAL,               -- do not call this scope again before this time
  updated_at REAL NOT NULL,
  PRIMARY KEY (connector, scope)
);

CREATE TABLE social_api_spend (           -- one row per paid-API request; estimates, the provider console is the bill
  id INTEGER PRIMARY KEY,
  connector TEXT NOT NULL,
  run_id TEXT,
  endpoint TEXT NOT NULL,                 -- path template, never the query string
  http_status INTEGER,
  billing_day TEXT NOT NULL,              -- UTC date (YYYY-MM-DD); providers dedupe per UTC day
  resources_json TEXT,                    -- counts by resource type returned, numbers only
  est_cost_usd REAL NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),   -- fixture rows never count as live spend or live evidence
  requested_at REAL NOT NULL
);
CREATE INDEX ix_sas_day ON social_api_spend(mode, billing_day);

CREATE TABLE social_api_billed_resources (   -- resources already charged on a UTC day (24 h billing dedupe)
  connector TEXT NOT NULL,
  billing_day TEXT NOT NULL,
  resource_type TEXT NOT NULL,            -- post | user
  resource_id TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),
  PRIMARY KEY (billing_day, resource_type, resource_id, mode)
);
"""

V3_DOWN = """
DROP TABLE IF EXISTS social_api_billed_resources;
DROP TABLE IF EXISTS social_api_spend;
DROP TABLE IF EXISTS social_source_cursors;
DROP TABLE IF EXISTS social_item_refs;
DROP TABLE IF EXISTS social_item_context;
"""

V4_UP = """
CREATE TABLE social_item_forwards (       -- where a forwarded item came from; ids only (Phase 04, Telegram forward_origin)
  item_key TEXT PRIMARY KEY,              -- social_items.item_key of the forward
  origin_type TEXT NOT NULL
    CHECK (origin_type IN ('channel','chat','user','hidden_user','unknown')),
  origin_chat_id TEXT,                    -- channel and chat origins only; user origins are private individuals, not recorded
  origin_message_id TEXT,                 -- channel origins only
  origin_item_key TEXT,                   -- item key of the original when its chat and message ids are known
  origin_published_at REAL,               -- provider time of the original; NULL = UNKNOWN
  is_automatic_forward INTEGER NOT NULL DEFAULT 0 CHECK (is_automatic_forward IN (0,1)),
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_sif_origin ON social_item_forwards(origin_item_key);

CREATE TABLE social_item_versions (       -- provider versions of an item that is edited in place (Telegram edit_date)
  item_key TEXT NOT NULL,
  provider_version_at REAL NOT NULL,      -- send time for the original, edit time for an edit (provider clock)
  version_kind TEXT NOT NULL CHECK (version_kind IN ('ORIGINAL','EDIT')),
  content_hash TEXT,                      -- sha256 of the normalized text of that version; NULL when it had no text
  poster_hash TEXT,                       -- sha256 of the provider's author signature; the name itself is never stored
  first_event_id TEXT NOT NULL,
  first_recorded_at REAL NOT NULL,
  PRIMARY KEY (item_key, provider_version_at)
);
"""

V4_DOWN = """
DROP TABLE IF EXISTS social_item_versions;
DROP TABLE IF EXISTS social_item_forwards;
"""

V5_UP = """
CREATE TABLE social_token_resolutions (   -- one row per (mention, evidence set, resolver version); append-only
  resolution_id INTEGER PRIMARY KEY,
  resolution_key TEXT NOT NULL UNIQUE,    -- sha256(item_key | mention_key | chain_hint | resolver_version | evidence_sha)
  item_key TEXT,                          -- soft link to social_items.item_key; NULL when resolved outside an ingested item
  mention_key TEXT NOT NULL,              -- 'ca:<value>' | 'link:<host>/<path>' | 'ticker:<SYMBOL>'
  mention_kind TEXT NOT NULL CHECK (mention_kind IN ('CONTRACT','LINK','TICKER')),
  mention_value TEXT NOT NULL,            -- the address, public link or ticker as found; never post text
  chain_hint TEXT,                        -- chain implied by a link or given by the caller; NULL = none
  chain_hint_basis TEXT CHECK (chain_hint_basis IS NULL OR chain_hint_basis IN ('LINK','CALLER')),
  status TEXT NOT NULL CHECK (status IN ('resolved','ambiguous','unresolved','conflicted')),
  reasons_json TEXT NOT NULL,             -- reason codes, e.g. ["symbol_only","multiple_candidates"]
  resolved_ref_id INTEGER REFERENCES social_token_refs(ref_id),
  resolved_chain TEXT,
  resolved_contract TEXT,
  asset_class TEXT,                       -- TOKEN | WRAPPED_NATIVE | STABLECOIN | UNKNOWN
  evidence_json TEXT NOT NULL,            -- list of {kind, provider, source_key, url, bucket}; ids and numbers only
  evidence_sha TEXT NOT NULL,
  resolver_version TEXT NOT NULL REFERENCES social_analysis_versions(version),
  resolved_at REAL NOT NULL,
  CHECK ((status = 'resolved') = (resolved_chain IS NOT NULL AND resolved_contract IS NOT NULL))
);
CREATE INDEX ix_str_item ON social_token_resolutions(item_key);
CREATE INDEX ix_str_resolved ON social_token_resolutions(resolved_chain, resolved_contract);

CREATE TABLE social_token_candidates (    -- every identity considered for a resolution, kept or rejected
  resolution_id INTEGER NOT NULL REFERENCES social_token_resolutions(resolution_id),
  rank INTEGER NOT NULL,
  chain TEXT,                             -- registry id; NULL when the provider named a chain the lab does not know
  provider_chain TEXT,                    -- chain id exactly as the provider gave it
  contract TEXT NOT NULL,
  symbol_seen TEXT,                       -- provider-reported; informational, never identity
  name_seen TEXT,
  support TEXT NOT NULL CHECK (support IN ('supported','unsupported')),
  verdict TEXT NOT NULL CHECK (verdict IN ('chosen','viable','rejected','near_match','successor','predecessor')),
  why TEXT NOT NULL,                      -- short reason code
  providers_json TEXT NOT NULL,           -- providers that reported this identity
  liquidity_usd_seen REAL,                -- largest provider-reported pool liquidity, for context only
  ref_id INTEGER REFERENCES social_token_refs(ref_id),
  PRIMARY KEY (resolution_id, rank)
);

CREATE TABLE social_token_relations (     -- trusted links between identities (migration, wrapping, bridging)
  from_chain TEXT NOT NULL,
  from_contract TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('MIGRATED_TO','WRAPS_NATIVE','BRIDGED_FROM')),
  to_chain TEXT NOT NULL,
  to_contract TEXT NOT NULL,
  basis TEXT NOT NULL CHECK (basis IN ('REGISTRY','OFFICIAL_SOURCE','PROVIDER')),
  source_url TEXT,
  effective_at REAL,                      -- NULL = UNKNOWN
  recorded_at REAL NOT NULL,
  PRIMARY KEY (from_chain, from_contract, relation, to_chain, to_contract)
);

CREATE TABLE social_market_facts (        -- append-only, versioned per series; one provider value per row
  fact_id INTEGER PRIMARY KEY,
  fact_key TEXT NOT NULL UNIQUE,          -- sha256(series_key | as_of | fetched_at | value)
  series_key TEXT NOT NULL,               -- sha256(chain | contract | provider | field | pair_id | size)
  fact_version INTEGER NOT NULL,          -- 1, 2, ... within the series
  supersedes_fact_id INTEGER REFERENCES social_market_facts(fact_id),
  chain TEXT NOT NULL,
  contract TEXT NOT NULL,
  ref_id INTEGER REFERENCES social_token_refs(ref_id),
  field TEXT NOT NULL,                    -- price | market_cap | fdv | circulating_supply | total_supply | liquidity_reported
                                          -- | volume_24h | pair | sell_quote_out | buy_quote_out | price_candle_open ...
  value_num REAL,
  value_str TEXT,                         -- ids only (pair address, NO_ROUTE status)
  unit TEXT NOT NULL,                     -- USD | token | SOL | <native symbol> | id | status
  quote_currency TEXT,                    -- currency the value is denominated in (USD for prices; SOL/WETH for raw quotes)
  supply_basis TEXT,                      -- valuation fields: circulating | total | NULL
  supply_basis_source TEXT,               -- where the denominator meaning comes from
  pair_id TEXT,
  size_usd REAL,                          -- executable quotes: notional asked
  provider TEXT NOT NULL,
  source_key TEXT,                        -- collector body key
  source_url TEXT,
  as_of REAL,                             -- the time the value describes; NULL = UNKNOWN
  as_of_kind TEXT NOT NULL CHECK (as_of_kind IN ('OBSERVED_AT_FETCH','HISTORICAL_CANDLE')),
  fetched_at REAL NOT NULL,
  valid_from REAL NOT NULL,
  valid_until REAL NOT NULL,
  bucket TEXT NOT NULL CHECK (bucket IN ('FACT','INFERENCE','HEURISTIC','UNKNOWN')),
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_smf_token ON social_market_facts(chain, contract, field, as_of);
CREATE INDEX ix_smf_series ON social_market_facts(series_key, fact_version);

CREATE TABLE social_market_context (      -- what one post's market context is, at posting time and at fetch time
  context_id INTEGER PRIMARY KEY,
  context_key TEXT NOT NULL UNIQUE,       -- sha256(resolution_id | fetched_at)
  resolution_id INTEGER NOT NULL REFERENCES social_token_resolutions(resolution_id),
  item_key TEXT,
  chain TEXT NOT NULL,
  contract TEXT NOT NULL,
  published_at REAL,                      -- NULL = UNKNOWN
  fetched_at REAL NOT NULL,
  observed_lag_seconds REAL,              -- fetched_at - published_at; how stale the observed facts are for the post
  posting_time_status TEXT NOT NULL
    CHECK (posting_time_status IN ('HISTORICAL_CANDLE','NO_HISTORY','PUBLISHED_AT_UNKNOWN','FETCHED_AT_POSTING')),
  posting_price_fact_id INTEGER REFERENCES social_market_facts(fact_id),
  observed_price_fact_id INTEGER REFERENCES social_market_facts(fact_id),
  market_status TEXT NOT NULL CHECK (market_status IN ('POOLS_FOUND','NO_POOL','NO_DATA')),
  notes_json TEXT NOT NULL,               -- reason codes and numeric spreads only
  recorded_at REAL NOT NULL
);
CREATE INDEX ix_smc_item ON social_market_context(item_key);
"""

V5_DOWN = """
DROP TABLE IF EXISTS social_market_context;
DROP TABLE IF EXISTS social_market_facts;
DROP TABLE IF EXISTS social_token_relations;
DROP TABLE IF EXISTS social_token_candidates;
DROP TABLE IF EXISTS social_token_resolutions;
"""

V6_UP = """
CREATE TABLE social_claim_extractions (   -- one row per (observation, extractor, model, prompt, extractor version); append-only
  extraction_id INTEGER PRIMARY KEY,
  extraction_key TEXT NOT NULL UNIQUE,    -- sha256(observation_id | extractor | provider | model | prompt_version | extractor_version)
  observation_id INTEGER NOT NULL REFERENCES social_observations(id),
  item_key TEXT NOT NULL,
  content_hash TEXT NOT NULL,             -- the observation's text hash; offsets in spans refer to that normalized text
  context_sha TEXT NOT NULL,              -- sha256 of the provenance context given to the extractor (reference type, refs)
  extractor TEXT NOT NULL CHECK (extractor IN ('deterministic','model')),
  provider TEXT,                          -- NULL for deterministic
  model TEXT,
  prompt_version TEXT,
  extractor_version TEXT NOT NULL,
  analysis_version TEXT NOT NULL REFERENCES social_analysis_versions(version),
  status TEXT NOT NULL CHECK (status IN ('ok','partial','analysis_unavailable','invalid_model_output')),
  unavailable_reason TEXT,                -- model_not_configured | credentials_missing | billing_not_consented | budget_exhausted
                                          -- | input_too_long | provider_error | text_unavailable
  cache_key TEXT,                         -- sha256(content_hash | context_sha | provider | model | prompt_version | output schema)
  cache_hit INTEGER NOT NULL DEFAULT 0 CHECK (cache_hit IN (0,1)),
  model_calls INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER, output_tokens INTEGER,
  est_cost_usd REAL,
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture','none')),
  output_json TEXT,                       -- validated structure: enums, ids, offsets, span hashes, own-words summaries; never quotes
  output_sha TEXT,
  errors_json TEXT NOT NULL DEFAULT '[]', -- validation and provider error codes only, never values
  flags_json TEXT NOT NULL DEFAULT '[]',  -- e.g. injection_suspected
  superseded_by INTEGER REFERENCES social_claim_extractions(extraction_id),
  extracted_at REAL NOT NULL
);
CREATE INDEX ix_sce_obs ON social_claim_extractions(observation_id);
CREATE INDEX ix_sce_cache ON social_claim_extractions(cache_key, extractor_version);
CREATE INDEX ix_sce_item ON social_claim_extractions(item_key);

CREATE TABLE social_claim_attributes (    -- the structured classification behind one social_claims row
  claim_id INTEGER PRIMARY KEY REFERENCES social_claims(id),
  extraction_id INTEGER NOT NULL REFERENCES social_claim_extractions(extraction_id),
  claim_index INTEGER NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('bullish','bearish','launch','catalyst','wallet','volume','liquidity','risk',
                                             'commentary','education','promotion','token_reference')),
  assertion_type TEXT NOT NULL CHECK (assertion_type IN ('claimed_fact','opinion','prediction','question','reference')),
  stance TEXT NOT NULL CHECK (stance IN ('positive','negative','neutral','mixed')),
  negated INTEGER NOT NULL CHECK (negated IN (0,1)),
  conditional INTEGER NOT NULL CHECK (conditional IN (0,1)),
  sarcasm_suspected INTEGER NOT NULL CHECK (sarcasm_suspected IN (0,1)),
  time_horizon TEXT NOT NULL CHECK (time_horizon IN ('intraday','days','weeks','months','long_term','unspecified')),
  author_position TEXT NOT NULL CHECK (author_position IN ('holds','no_position','sold','not_disclosed','not_applicable')),
  attribution TEXT NOT NULL CHECK (attribution IN ('author','quoted','reposted','unclear')),
  referenced_item_key TEXT,               -- the quoted or reposted item, from provider ids (social_item_refs / forwards)
  referenced_author_id TEXT,
  uncertainty TEXT NOT NULL CHECK (uncertainty IN ('low','medium','high')),
  uncertainty_reasons_json TEXT NOT NULL,
  verification TEXT NOT NULL CHECK (verification IN ('present_in_text','unverified_text_claim')),
  narrative_tags_json TEXT NOT NULL,
  tokens_json TEXT NOT NULL,              -- [{mention_id, mention_key, status, resolution_id, chain, contract}]
  UNIQUE (extraction_id, claim_index)
);

CREATE TABLE social_claim_spans (         -- anchored evidence: character offsets into the normalized post text, plus a hash
  claim_id INTEGER NOT NULL REFERENCES social_claims(id),
  span_index INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('claim','condition','position','attribution','token')),
  char_start INTEGER NOT NULL,
  char_end INTEGER NOT NULL,
  span_sha TEXT NOT NULL,                 -- sha256 of the span text; the wording itself is never stored here
  PRIMARY KEY (claim_id, span_index),
  CHECK (char_end > char_start AND char_start >= 0)
);
"""

V6_DOWN = """
DROP TABLE IF EXISTS social_claim_spans;
DROP TABLE IF EXISTS social_claim_attributes;
DROP TABLE IF EXISTS social_claim_extractions;
"""

V7_UP = """
CREATE TABLE social_narrative_runs (      -- one immutable snapshot of the narrative engine; a new run is a new row, never an edit
  run_id INTEGER PRIMARY KEY,
  snapshot_key TEXT NOT NULL UNIQUE,      -- sha256(engine_version | window_start | window_end | cutoff | tz | params_sha | input_sha); same inputs -> same run
  engine_version TEXT NOT NULL REFERENCES social_analysis_versions(version),
  window_label TEXT NOT NULL,             -- e.g. '2026-10-12 America/New_York' or 'custom'
  tz TEXT NOT NULL,                       -- IANA zone the window was cut in; all stored times stay UTC epoch seconds
  window_start REAL NOT NULL,             -- inclusive
  window_end REAL NOT NULL,               -- exclusive
  cutoff REAL NOT NULL,                   -- knowledge cutoff: min(window_end, clock). Nothing observed after it is used.
  window_complete INTEGER NOT NULL CHECK (window_complete IN (0,1)),
  params_json TEXT NOT NULL,
  params_sha TEXT NOT NULL,               -- sha256 of the parameters other than the window (runs are compared only when equal)
  input_sha TEXT NOT NULL,                -- sha256 of the canonical input rows (claims, items, references, accounts, coverage)
  input_claims INTEGER NOT NULL,
  cluster_count INTEGER NOT NULL,
  unassigned_json TEXT NOT NULL,          -- claims that joined no cluster, by reason code; ticker-only mentions listed by symbol
  contains_fixture INTEGER NOT NULL CHECK (contains_fixture IN (0,1)),
  prev_run_id INTEGER REFERENCES social_narrative_runs(run_id),
  summary_json TEXT NOT NULL,             -- change summary against prev_run_id (numbers, keys and change codes)
  created_at REAL NOT NULL
);
CREATE INDEX ix_snr_window ON social_narrative_runs(params_sha, tz, window_end);

CREATE TABLE social_narrative_clusters (
  run_id INTEGER NOT NULL REFERENCES social_narrative_runs(run_id),
  cluster_key TEXT NOT NULL,              -- 'ca:<chain>:<contract>' (identity) or 'tag:<tag>' (structured theme tag); never a ticker
  cluster_kind TEXT NOT NULL CHECK (cluster_kind IN ('CONTRACT','THEME')),
  label TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok','insufficient_coverage')),
  reasons_json TEXT NOT NULL,             -- why the status is insufficient_coverage (empty for ok)
  confidence TEXT NOT NULL CHECK (confidence IN ('HIGH','MODERATE','LOW','UNKNOWN')),
  freshness TEXT NOT NULL CHECK (freshness IN ('FRESH','STALE')),
  first_observed_at REAL,                 -- first time the collector saw an item in this cluster (not the first-ever mention)
  last_observed_at REAL,
  earliest_published_at REAL,             -- earliest provider publication time among observed items; NULL = UNKNOWN
  item_count INTEGER NOT NULL,            -- distinct items up to the cutoff
  window_mentions INTEGER NOT NULL,       -- distinct items whose event time is inside the window
  source_count INTEGER NOT NULL,          -- distinct attributable sources of any role
  independent_source_count INTEGER,       -- NULL when status is insufficient_coverage (not estimable)
  independent_group_count INTEGER,
  amplifier_count INTEGER NOT NULL,       -- reposts, forwards, quotes that repeat a claim
  dependent_count INTEGER NOT NULL,       -- replies, quote commentary and copies that depend on another item
  unobserved_origin_count INTEGER NOT NULL,
  edge_count INTEGER NOT NULL,
  conflicted INTEGER NOT NULL CHECK (conflicted IN (0,1)),
  stance_json TEXT NOT NULL,
  opinion_changes_json TEXT NOT NULL,
  windows_json TEXT NOT NULL,             -- trailing windows: current, previous, delta, pct change; plus peak sliding counts
  flags_json TEXT NOT NULL,               -- hypotheses (HEURISTIC) and data-quality flags
  dependencies_json TEXT NOT NULL,        -- shared originals and copy groups
  originators_json TEXT NOT NULL,
  linked_tokens_json TEXT NOT NULL,
  chains_json TEXT NOT NULL,
  coverage_json TEXT NOT NULL,
  explanation_json TEXT NOT NULL,
  PRIMARY KEY (run_id, cluster_key)
);

CREATE TABLE social_narrative_members (   -- provenance: every claim and observation behind a cluster
  run_id INTEGER NOT NULL REFERENCES social_narrative_runs(run_id),
  cluster_key TEXT NOT NULL,
  claim_id INTEGER NOT NULL REFERENCES social_claims(id),
  item_key TEXT NOT NULL,
  observation_id INTEGER REFERENCES social_observations(id),
  account_id TEXT,
  source_id TEXT,                         -- trader id when the account is linked to one, else the account id; NULL = unknown author
  role TEXT NOT NULL CHECK (role IN ('INDEPENDENT_ORIGINAL','UNVERIFIED_ORIGINAL','AMPLIFIER','DEPENDENT')),
  group_id TEXT NOT NULL,                 -- dependency group (shared original or copy set)
  event_time REAL,                        -- provider publication time when known, else collector time; NULL = UNKNOWN
  event_time_basis TEXT NOT NULL CHECK (event_time_basis IN ('PROVIDER','COLLECTOR','UNKNOWN')),
  in_window INTEGER NOT NULL CHECK (in_window IN (0,1)),
  source_state TEXT NOT NULL,             -- accessible | inaccessible:<retrieval status>
  stance TEXT,
  why TEXT NOT NULL,                      -- reason code for the role
  PRIMARY KEY (run_id, cluster_key, claim_id)
);
CREATE INDEX ix_snm_item ON social_narrative_members(item_key);

CREATE TABLE social_narrative_edges (     -- who repeats or depends on whom, inside a cluster
  run_id INTEGER NOT NULL REFERENCES social_narrative_runs(run_id),
  cluster_key TEXT NOT NULL,
  from_item_key TEXT NOT NULL,
  to_item_key TEXT NOT NULL,              -- 'unknown:<item_key>' when the provider gave no origin
  edge_type TEXT NOT NULL CHECK (edge_type IN ('repost','quote','reply','forward','identical_text')),
  to_observed INTEGER NOT NULL CHECK (to_observed IN (0,1)),
  PRIMARY KEY (run_id, cluster_key, from_item_key, to_item_key, edge_type)
);

CREATE TABLE social_narrative_changes (   -- what moved since the previous comparable run
  run_id INTEGER NOT NULL REFERENCES social_narrative_runs(run_id),
  prev_run_id INTEGER,
  cluster_key TEXT NOT NULL,
  change_type TEXT NOT NULL CHECK (change_type IN ('NEW','ACTIVITY_UP','ACTIVITY_DOWN','DORMANT','REVIVED',
                                                   'INDEPENDENCE_CHANGED','STANCE_SHIFT','CONFLICT_CHANGED','STATUS_CHANGED')),
  before_json TEXT NOT NULL,
  after_json TEXT NOT NULL,
  PRIMARY KEY (run_id, cluster_key, change_type)
);
"""

V7_DOWN = """
DROP TABLE IF EXISTS social_narrative_changes;
DROP TABLE IF EXISTS social_narrative_edges;
DROP TABLE IF EXISTS social_narrative_members;
DROP TABLE IF EXISTS social_narrative_clusters;
DROP TABLE IF EXISTS social_narrative_runs;
"""

# (version, name, up, down). Append only; never edit an applied entry (the checksum guard refuses it).
MIGRATIONS: list[tuple[int, str, str, str]] = [
    (1, "social intelligence core tables", V1_UP, V1_DOWN),
    (2, "ingestion runs, checkpoints, quarantine, provenance", V2_UP, V2_DOWN),
    (3, "item context, source cursors, paid-API spend ledger", V3_UP, V3_DOWN),
    (4, "item forwards and in-place versions", V4_UP, V4_DOWN),
    (5, "token identity resolution and timestamped market facts", V5_UP, V5_DOWN),
    (6, "structured claim extraction, attributes and anchored evidence spans", V6_UP, V6_DOWN),
    (7, "narrative snapshots: clusters, independence, provenance and change summaries", V7_UP, V7_DOWN),
]
LATEST = max(m[0] for m in MIGRATIONS)
ALL_VERSIONS = sorted(m[0] for m in MIGRATIONS)

SOCIAL_TABLES = [
    "social_analysis_versions", "social_accounts", "social_account_handles", "social_traders",
    "social_trader_accounts", "social_items", "social_observations", "social_token_refs", "social_claims",
    "social_claim_relations", "social_evidence_links", "social_wallet_attributions", "social_connector_health",
    "social_coverage", "social_ingest_runs", "social_ingest_checkpoints", "social_ingest_quarantine",
    "social_observation_provenance", "social_item_context", "social_item_refs", "social_source_cursors",
    "social_api_spend", "social_api_billed_resources", "social_item_forwards", "social_item_versions",
    "social_token_resolutions", "social_token_candidates", "social_token_relations", "social_market_facts",
    "social_market_context", "social_claim_extractions", "social_claim_attributes", "social_claim_spans",
    "social_narrative_runs", "social_narrative_clusters", "social_narrative_members", "social_narrative_edges",
    "social_narrative_changes",
]


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()


def current_version(con: sqlite3.Connection) -> int:
    con.executescript(LEDGER)
    row = con.execute("SELECT MAX(version) FROM social_schema_migrations").fetchone()
    return int(row[0] or 0)


def _run(con: sqlite3.Connection, script: str) -> None:
    """Run a script inside one explicit transaction; on any error roll back and re-raise."""
    try:
        con.executescript("BEGIN;\n" + script + "\nCOMMIT;")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise


def migrate(con: sqlite3.Connection, target: int | None = None, migrations=None) -> list[int]:
    """Apply pending migrations up to target (default: latest). Returns the versions applied."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = {r[0]: r[1] for r in con.execute("SELECT version, checksum FROM social_schema_migrations")}
    for v, _name, up, _down in migrations:
        if v in applied and applied[v] != _checksum(up):
            raise RuntimeError(f"social migration {v} changed after it was applied; add a new migration instead")
    done = []
    for v, name, up, _down in sorted(migrations):
        if v in applied or (target is not None and v > target):
            continue
        ledger = (f"INSERT INTO social_schema_migrations(version,name,checksum,applied_at) "
                  f"VALUES ({int(v)}, '{name.replace(chr(39), '')}', '{_checksum(up)}', {time.time()!r});")
        _run(con, up + "\n" + ledger)
        done.append(v)
    return done


def rollback(con: sqlite3.Connection, target: int = 0, migrations=None) -> list[int]:
    """Undo applied migrations above target, newest first. Drops social tables only; legacy tables are untouched.
    Take a backup first (backup_db) if the social rows matter: rollback deletes them."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = sorted((r[0] for r in con.execute("SELECT version FROM social_schema_migrations")), reverse=True)
    by_v = {m[0]: m for m in migrations}
    undone = []
    for v in applied:
        if v <= target:
            break
        if v not in by_v:
            raise RuntimeError(f"no down script for applied social migration {v}")
        _run(con, by_v[v][3] + f"\nDELETE FROM social_schema_migrations WHERE version={int(v)};")
        undone.append(v)
    return undone


def backup_db(src: Path | str, dest: Path | str) -> Path:
    """Consistent copy of a live database (sqlite backup API, safe with WAL). Use before migrate on a real DB
    and before any rollback. Recovery = copy the backup file back over the database while nothing has it open."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    s = sqlite3.connect(f"file:{Path(src)}?mode=ro", uri=True)
    d = sqlite3.connect(dest)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()
    return dest


if __name__ == "__main__":
    import sys
    from .. import db
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    with db.connect() as con:
        if cmd == "status":
            print("social schema version", current_version(con), "latest", max(m[0] for m in MIGRATIONS))
        elif cmd == "migrate":
            print("applied", migrate(con))
        elif cmd == "rollback":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
            b = backup_db(db.DB_PATH, db.DATA_DIR / "private" / "backups" / f"memelab_{stamp}.sqlite")
            print("backup", b, "rolled back", rollback(con, target))
        else:
            raise SystemExit("usage: python -m memelab.social.schema status|migrate|rollback [target]")

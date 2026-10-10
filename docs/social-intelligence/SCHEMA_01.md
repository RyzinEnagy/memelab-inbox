# Phase 01 schema: social intelligence persistence

Source of truth: `memelab/social/schema.py` (DDL and migrations), `memelab/social/store.py` (CRUD), `memelab/social/private.py` (private store). Tests: `tests/test_social_store.py`. The SQL below is copied from the code by script, so it is exact for schema version 1.

Related: [EXECUTION.md](EXECUTION.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md) (D-011 to D-014), [HANDOFF.md](HANDOFF.md).

## Where things live

- Main lab database `data/memelab.sqlite` (or `MEMELAB_DB`). This file is committed to the public repo, so the social tables hold metadata, references, numeric counts and short own-words summaries only (D-010). `db.init_db()` applies the social migrations after the existing catalyst, chains and launch schemas.
- Private store `data/private/social_private.sqlite` (or `MEMELAB_PRIVATE_DB`). Gitignored (`data/private/` and `*.sqlite*`). Holds exact wording only when a caller passes `keep_exact_reason`, keyed `sha256:<content_hash>`, with a retention deadline.
- Backups made by the rollback command go to `data/private/backups/` (gitignored).

## Reused, not duplicated

- Narratives: `narratives` from `memelab/chains/schema.py`. `social_claims.narrative_id` is a soft link to it.
- Source registry: `catalyst_sources`. `social_accounts.catalyst_source_id` is a soft link to a registered trader or social source.
- `social_snapshots` (core schema, written by `social-note`) is unchanged and still used for numeric per-mint social metrics.
- No foreign key points at a legacy table, so the social migration can be applied to or rolled back from any existing database without touching legacy rows.

## Conventions

- Times are UTC epoch seconds (REAL), like the rest of the lab. `store.to_utc()` accepts epoch seconds or milliseconds, aware datetimes and ISO strings with an offset; a naive datetime is refused.
- NULL means UNKNOWN. Time columns that can be unknown carry a `*_basis` column (`UNKNOWN`, `PROVIDER`, `COLLECTOR`, `PARSED_RELATIVE`). Nothing is back-filled with the ingestion time; `ingested_at` is recorded separately.
- Defaults are the cautious value: `identity_status` UNVERIFIED, `account_kind` UNKNOWN, `confidence` UNKNOWN, claim `evidence_status` INFERENCE, `retained_content` NONE.
- Append-only: `social_observations`, `social_wallet_attributions` (a retraction is a new RETRACTED row), `social_connector_health`, `social_coverage`, `social_account_handles` (handle history). Current state comes from "latest per key" queries, for example `store.current_wallet_view()`.
- Idempotency: each append-only row has a deterministic key with a UNIQUE constraint (`observation_key`, `assertion_key`, `claim_key`, `coverage_key`, `(connector, checked_at)`). Writes use INSERT OR IGNORE or ON CONFLICT; re-running a batch adds nothing.
- Identity: a token is `(chain, contract)`, validated and normalized per chain family (Solana base58 as given, EVM lower-case hex, Sui `0x..::module::NAME`). A ticker or name alone is a separate `TICKER_ONLY` / `NAME_ONLY` reference whose `contract` must be NULL (CHECK constraint). A wallet attribution needs a valid on-chain address and an existing trader or account as subject, so a handle or social id can never be stored as a wallet.
- Accounts are keyed `<platform>:id:<provider_user_id>` when the id is known, else `<platform>:handle:<handle>`. If the id is learned later the key stays stable and the id is filled in. A reused handle with a different provider id becomes a separate account.
- `db.connect()` does not enable `PRAGMA foreign_keys` (repo-wide behaviour, not changed here), so the store checks the references that matter (analysis version, wallet subject) in code.

## Content and retention policy

- Source text passed to `record_observation()` is hashed (`content_hash`, sha256 of whitespace- and NFC-normalized text) and not written to the main database.
- Summaries are at most 400 characters and are refused if they repeat 8 or more consecutive words of the source text.
- `metrics_json` takes numeric values only.
- Exact wording goes to the private store only with a stated reason. Default retention there is 30 days (`private.DEFAULT_RETENTION_DAYS`); `private.purge_expired()` deletes rows past `retain_until`.
- Metadata rows in the main database (observations, claims, attributions, coverage, health) are kept indefinitely. They are not added to the `state.py` export yet; that is decided in the scheduled-run integration phase.

## Reprocessing policy

- Every derived row names the `analysis_version` that produced it, and the version must be registered in `social_analysis_versions` first.
- Re-extracting with a new version writes new claim rows (the version is part of `claim_key`). Old rows stay, so results can be compared across versions. Consumers choose the version they read.
- Observations are never rewritten by reprocessing. A changed post seen again is a new observation with a new `content_hash`; the item row keeps the first known `published_at`, and a different later value is returned as a conflict instead of overwriting.

## Migrations and rollback

- Ledger table `social_schema_migrations(version, name, checksum, applied_at)`. `schema.migrate()` applies pending versions in order, each inside one explicit transaction together with its ledger row; a failure rolls the whole version back and leaves the database as it was. An applied version whose up script has changed is refused (checksum guard): add a new version instead.
- `schema.rollback(con, target)` runs down scripts newest first. Down scripts drop social tables only. Rollback deletes social rows, so take a backup first.
- Commands (operate on `MEMELAB_DB` or `data/memelab.sqlite`):
  - `python -m memelab.social.schema status`
  - `python -m memelab.social.schema migrate`
  - `python -m memelab.social.schema rollback [target]` (writes a backup to `data/private/backups/` before rolling back)
- Recovery: with nothing holding the database open, copy the backup file over the database and delete any `-wal` / `-shm` files next to it. `schema.backup_db()` uses the sqlite backup API, so it is safe on a live WAL database.

## Version 1 DDL

```sql
CREATE TABLE IF NOT EXISTS social_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  checksum TEXT NOT NULL,                 -- sha256 of the up script; a changed script on an applied version is refused
  applied_at REAL NOT NULL
);
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
```

## Version 1 down script

```sql
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
```

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

# (version, name, up, down). Append only; never edit an applied entry (the checksum guard refuses it).
MIGRATIONS: list[tuple[int, str, str, str]] = [
    (1, "social intelligence core tables", V1_UP, V1_DOWN),
]

SOCIAL_TABLES = [
    "social_analysis_versions", "social_accounts", "social_account_handles", "social_traders",
    "social_trader_accounts", "social_items", "social_observations", "social_token_refs", "social_claims",
    "social_claim_relations", "social_evidence_links", "social_wallet_attributions", "social_connector_health",
    "social_coverage",
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

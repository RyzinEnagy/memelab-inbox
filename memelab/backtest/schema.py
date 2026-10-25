"""Additive, versioned schema for the backtesting package (bt_* tables).

Rules:
- Only bt_* tables are created or dropped here. Legacy, catalyst, chains, launch and social tables are never touched.
- Every bt_* data table is append-only, enforced by triggers that abort UPDATE and DELETE. A correction is a new row
  that names the row it supersedes; history is never rewritten.
- All times are UTC epoch seconds (REAL). Names: event_time (when it happened), observed_at (when a collector saw it),
  available_at (earliest moment the lab could act on it), decision_time, execution_time.
- Migrations are checksummed: a changed script on an applied version is refused (add a new version instead).
- Take a backup (backup_db) before migrating a real database. Rollback drops bt_* tables only.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

LEDGER = """
CREATE TABLE IF NOT EXISTS bt_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  checksum TEXT NOT NULL,
  applied_at REAL NOT NULL
);
"""

V1_TABLES = {
    # asset identity, versioned (decimals / program can change only by a new observed version)
    "bt_asset_versions": """
CREATE TABLE IF NOT EXISTS bt_asset_versions (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL,
  symbol TEXT,                      -- display only, never a key
  decimals INTEGER, token_program TEXT,
  observed_at REAL NOT NULL, available_at REAL NOT NULL,
  source TEXT NOT NULL, raw_ref TEXT, content_hash TEXT NOT NULL,
  UNIQUE(chain, mint, content_hash)
);
CREATE INDEX IF NOT EXISTS bt_asset_versions_key ON bt_asset_versions(chain, mint, available_at);
""",
    "bt_pool_versions": """
CREATE TABLE IF NOT EXISTS bt_pool_versions (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, pool_address TEXT NOT NULL, mint TEXT NOT NULL,
  dex TEXT, dex_program TEXT,
  pool_type TEXT NOT NULL CHECK (pool_type IN ('CPMM','CLMM','DLMM','BONDING_CURVE','STABLE','UNKNOWN')),
  quote_mint TEXT, pool_created_at REAL,
  observed_at REAL NOT NULL, available_at REAL NOT NULL,
  source TEXT NOT NULL, raw_ref TEXT, content_hash TEXT NOT NULL,
  UNIQUE(chain, pool_address, content_hash)
);
CREATE INDEX IF NOT EXISTS bt_pool_versions_mint ON bt_pool_versions(chain, mint, available_at);
""",
    # generic immutable observation log (social, wallet, catalyst-derived, lifecycle, provider status ...)
    "bt_observations": """
CREATE TABLE IF NOT EXISTS bt_observations (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,               -- e.g. CATALYST_CLAIM, WALLET_TRANSFER, SWAP_SELL, SWAP_BUY, POST, POST_EDIT, POST_DELETED, PROVIDER_STATUS
  provider TEXT NOT NULL, raw_source_id TEXT, raw_payload_hash TEXT NOT NULL,
  chain TEXT, mint TEXT, pool_address TEXT, wallet TEXT, origin_group TEXT,
  event_time REAL, observed_at REAL NOT NULL, available_at REAL NOT NULL, validity_until REAL,
  slot INTEGER, block_time REAL,
  value_num REAL, value_text TEXT, value_json TEXT,
  value_state TEXT NOT NULL DEFAULT 'OBSERVED' CHECK (value_state IN ('OBSERVED','ZERO','MISSING','STALE','UNAVAILABLE','UNKNOWN_AS_OF')),
  confidence TEXT, raw_ref TEXT, ingest_version TEXT NOT NULL,
  supersedes_id INTEGER REFERENCES bt_observations(id),
  recorded_at REAL NOT NULL,
  CHECK (available_at >= observed_at),
  UNIQUE(provider, kind, raw_payload_hash)
);
CREATE INDEX IF NOT EXISTS bt_observations_key ON bt_observations(chain, mint, kind, available_at);
""",
    "bt_market_bars": """
CREATE TABLE IF NOT EXISTS bt_market_bars (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL, pool_address TEXT NOT NULL,
  timeframe_s INTEGER NOT NULL CHECK (timeframe_s > 0),
  start REAL NOT NULL, end REAL NOT NULL,
  o REAL NOT NULL, h REAL NOT NULL, l REAL NOT NULL, c REAL NOT NULL, volume_usd REAL,
  currency TEXT NOT NULL DEFAULT 'USD',
  observed_at REAL NOT NULL, available_at REAL NOT NULL,
  provider TEXT NOT NULL, quality_flags TEXT, raw_ref TEXT, content_hash TEXT NOT NULL,
  CHECK (end = start + timeframe_s), CHECK (available_at >= end), CHECK (h >= l AND h >= o AND h >= c AND l <= o AND l <= c AND l > 0),
  UNIQUE(provider, pool_address, timeframe_s, start, content_hash)
);
CREATE INDEX IF NOT EXISTS bt_market_bars_key ON bt_market_bars(chain, mint, pool_address, timeframe_s, start);
""",
    "bt_liquidity_states": """
CREATE TABLE IF NOT EXISTS bt_liquidity_states (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL, pool_address TEXT NOT NULL,
  asof REAL NOT NULL, available_at REAL NOT NULL,
  basis TEXT NOT NULL CHECK (basis IN ('OBSERVED_RESERVES','LIQ_SNAPSHOT','QUOTE_DERIVED')),
  reserve_base REAL, reserve_quote REAL, effective_quote_adj REAL, quote_mint TEXT,
  liquidity_usd REAL, fee_bps REAL, ticks_json TEXT,
  provider TEXT NOT NULL, raw_ref TEXT, content_hash TEXT NOT NULL,
  CHECK (available_at >= asof),
  UNIQUE(provider, pool_address, content_hash)
);
CREATE INDEX IF NOT EXISTS bt_liquidity_key ON bt_liquidity_states(chain, mint, pool_address, available_at);
""",
    "bt_execution_quotes": """
CREATE TABLE IF NOT EXISTS bt_execution_quotes (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL, side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
  usd_size REAL, from_mint TEXT, to_mint TEXT, input_raw TEXT, output_raw TEXT,
  quote_at REAL NOT NULL, available_at REAL NOT NULL, expiry REAL,
  route_json TEXT, fees_json TEXT, slot INTEGER, impact_frac REAL,
  provider TEXT NOT NULL, status TEXT NOT NULL, failed_paths TEXT, source_hash TEXT NOT NULL,
  CHECK (available_at >= quote_at),
  UNIQUE(provider, source_hash)
);
CREATE INDEX IF NOT EXISTS bt_quotes_key ON bt_execution_quotes(chain, mint, side, available_at);
""",
    # frozen discovery universe: who the lab saw, when, and what it concluded at that moment
    "bt_universe_members": """
CREATE TABLE IF NOT EXISTS bt_universe_members (
  id INTEGER PRIMARY KEY,
  universe_id TEXT NOT NULL,
  chain TEXT NOT NULL, mint TEXT NOT NULL, symbol TEXT,
  basis TEXT NOT NULL CHECK (basis IN ('THESIS','REJECTION','LAUNCH_COHORT','FIXTURE')),
  entered_at REAL NOT NULL,         -- lab observation time (thesis created_at / rejected_at / first_seen_at)
  available_at REAL NOT NULL,       -- when the lab could act on it (= entered_at for its own computation)
  committed_by REAL,                -- independent upper bound: git commit time of the export that holds it
  source_commit TEXT,
  status_at_entry TEXT, score_at_entry REAL, fatal_flags_json TEXT, snapshot_json TEXT, stage TEXT,
  content_hash TEXT NOT NULL,
  UNIQUE(universe_id, content_hash)
);
CREATE INDEX IF NOT EXISTS bt_universe_key ON bt_universe_members(universe_id, entered_at);
""",
    "bt_token_lifecycle": """
CREATE TABLE IF NOT EXISTS bt_token_lifecycle (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL,
  event TEXT NOT NULL CHECK (event IN ('BIRTH','FIRST_POOL','GRADUATION','LAST_TRADE','DELISTED','RUGGED','DEAD_LIQUIDITY')),
  event_time REAL, available_at REAL NOT NULL, source TEXT NOT NULL, evidence TEXT, content_hash TEXT NOT NULL,
  UNIQUE(chain, mint, event, content_hash)
);
""",
    "bt_experiment_runs": """
CREATE TABLE IF NOT EXISTS bt_experiment_runs (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,      -- sha256 of the canonical config below
  code_sha TEXT, dataset_hash TEXT NOT NULL, label_definition TEXT, universe_definition TEXT, discovery_rule TEXT,
  splits_json TEXT, embargo_policy TEXT, seed INTEGER, strategy_id TEXT, strategy_version TEXT,
  cost_model_version TEXT, engine_version TEXT NOT NULL, baseline TEXT, fees_json TEXT, concurrency_limit INTEGER,
  assumptions_json TEXT, config_json TEXT NOT NULL, trials_before INTEGER, created_at REAL NOT NULL
);
""",
    "bt_run_results": """
CREATE TABLE IF NOT EXISTS bt_run_results (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES bt_experiment_runs(run_id),
  status TEXT NOT NULL, result_json TEXT NOT NULL, result_hash TEXT NOT NULL, created_at REAL NOT NULL,
  UNIQUE(run_id, result_hash)
);
""",
    "bt_signals": """
CREATE TABLE IF NOT EXISTS bt_signals (
  id INTEGER PRIMARY KEY,
  run_id TEXT, signal_id TEXT NOT NULL, strategy_id TEXT NOT NULL, strategy_version TEXT NOT NULL,
  chain TEXT NOT NULL, mint TEXT NOT NULL,
  candidate_time REAL NOT NULL, decision_time REAL NOT NULL, earliest_execution_time REAL NOT NULL,
  based_on_json TEXT, features_json TEXT, params_json TEXT, confidence TEXT, invalidation_json TEXT,
  CHECK (decision_time >= candidate_time), CHECK (earliest_execution_time >= decision_time),
  UNIQUE(run_id, signal_id)
);
""",
    "bt_fills": """
CREATE TABLE IF NOT EXISTS bt_fills (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL, order_id TEXT NOT NULL, chain TEXT NOT NULL, mint TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('BUY','SELL')),
  decision_time REAL NOT NULL, submission_time REAL NOT NULL, fill_time REAL,
  requested_amount REAL NOT NULL, filled_amount REAL NOT NULL, price REAL, impact_frac REAL,
  fee_breakdown_json TEXT, source_basis TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('FILLED','PARTIAL','FAILED','CANCELED','EXPIRED')),
  reason TEXT,
  CHECK (submission_time >= decision_time), CHECK (fill_time IS NULL OR fill_time >= submission_time),
  UNIQUE(run_id, order_id, status)
);
""",
    "bt_assessments": """
CREATE TABLE IF NOT EXISTS bt_assessments (
  id INTEGER PRIMARY KEY,
  request_key TEXT NOT NULL,        -- sha256(chain, mint, snapshot hash, engine version, policy hash)
  chain TEXT NOT NULL, mint TEXT NOT NULL, snapshot_hash TEXT NOT NULL, engine_version TEXT NOT NULL,
  as_of REAL NOT NULL, stage TEXT NOT NULL CHECK (stage IN ('FAST','DEEP')),
  tier TEXT NOT NULL, state TEXT NOT NULL, result_json TEXT NOT NULL, result_hash TEXT NOT NULL, created_at REAL NOT NULL,
  UNIQUE(request_key, stage)
);
CREATE INDEX IF NOT EXISTS bt_assessments_mint ON bt_assessments(chain, mint, as_of);
""",
    "bt_assessment_events": """
CREATE TABLE IF NOT EXISTS bt_assessment_events (
  id INTEGER PRIMARY KEY,
  request_key TEXT NOT NULL, event TEXT NOT NULL, detail TEXT, wall_ms REAL, created_at REAL NOT NULL
);
""",
    "bt_outcomes": """
CREATE TABLE IF NOT EXISTS bt_outcomes (
  id INTEGER PRIMARY KEY,
  opportunity_id TEXT NOT NULL, chain TEXT NOT NULL, mint TEXT NOT NULL,
  decision_time REAL NOT NULL, horizon_s INTEGER NOT NULL, observed_asof REAL NOT NULL,
  state TEXT NOT NULL, realized_json TEXT, protocol_version TEXT NOT NULL,
  censored INTEGER NOT NULL DEFAULT 0, missing_reason TEXT, supersedes_id INTEGER REFERENCES bt_outcomes(id),
  content_hash TEXT NOT NULL, created_at REAL NOT NULL,
  CHECK (observed_asof >= decision_time),
  UNIQUE(opportunity_id, horizon_s, content_hash)
);
""",
    # provenance extension for crawler / robot captures; the capture itself lives in the catalyst tables
    "bt_capture_provenance": """
CREATE TABLE IF NOT EXISTS bt_capture_provenance (
  id INTEGER PRIMARY KEY,
  collector TEXT NOT NULL CHECK (collector IN ('EXISTING_COLLECTOR','FIRECRAWL','CRAWL4AI','MAXUN','FIXTURE','OTHER')),
  robot_id TEXT, run_id TEXT, robot_version TEXT, edition TEXT, extractor_version TEXT, run_status TEXT,
  source_url TEXT NOT NULL, canonical_origin TEXT NOT NULL, source_domain TEXT NOT NULL,
  content_hash TEXT NOT NULL, raw_ref TEXT,
  captured_at REAL NOT NULL, first_seen_at REAL NOT NULL,
  source_published_at REAL, published_confidence TEXT, source_edited_at REAL,
  available_at REAL NOT NULL,
  historical_asof_proof TEXT NOT NULL DEFAULT 'NONE' CHECK (historical_asof_proof IN ('NONE','CONTEMPORANEOUS_CAPTURE','INDEPENDENT_ARCHIVE','SIGNED_OBSERVATION')),
  origin_group TEXT, record_type TEXT, claim_state TEXT, extraction_status TEXT,
  chain TEXT, mint TEXT, mint_verified INTEGER NOT NULL DEFAULT 0,
  catalyst_item_id INTEGER, catalyst_page_fetch_id INTEGER,
  CHECK (available_at >= first_seen_at), CHECK (first_seen_at <= captured_at + 0.001),
  CHECK (mint IS NULL OR mint_verified = 1),
  UNIQUE(canonical_origin, content_hash)
);
""",
}

APPEND_ONLY = [t for t in V1_TABLES]


def _triggers(tables: list[str]) -> str:
    out = []
    for t in tables:
        out.append(f"CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t} BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;")
        out.append(f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t} BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;")
    return "\n".join(out)


V1_UP = "\n".join(V1_TABLES.values()) + "\n" + _triggers(APPEND_ONLY)
V1_DOWN = "\n".join(
    [f"DROP TRIGGER IF EXISTS {t}_no_update; DROP TRIGGER IF EXISTS {t}_no_delete;" for t in APPEND_ONLY]
    + [f"DROP TABLE IF EXISTS {t};" for t in reversed(APPEND_ONLY)]
)

# v2 (D-BT-034): forward depth collector. Additive: two new append-only tables; v1 tables are unchanged.
V2_TABLES = {
    # one row per lab decision (exact thesis row first visible in an export) the collector follows for 25 h
    "bt_depth_decisions": """
CREATE TABLE IF NOT EXISTS bt_depth_decisions (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL, pool_address TEXT,
  pool_source TEXT CHECK (pool_source IN ('EXPORT_PRIMARY_POOL','EXPORT_GRADUATED_POOL','VENDOR_TOP_POOL','NO_POOL','UNSUPPORTED_CHAIN')),
  pool_resolved_at REAL,
  export_commit TEXT NOT NULL, export_time REAL NOT NULL, export_path TEXT,
  created_at REAL NOT NULL, row_sha256 TEXT NOT NULL, status TEXT,
  recorded_at REAL NOT NULL, content_hash TEXT NOT NULL,
  UNIQUE(chain, mint, row_sha256)
);
CREATE INDEX IF NOT EXISTS bt_depth_decisions_time ON bt_depth_decisions(export_time);
""",
    # one row per pool read (kind POOL) or sell quote (kind QUOTE); captured_at is when the response arrived
    "bt_depth_snapshots": """
CREATE TABLE IF NOT EXISTS bt_depth_snapshots (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL, decision_id INTEGER NOT NULL REFERENCES bt_depth_decisions(id),
  chain TEXT NOT NULL, mint TEXT NOT NULL, pool_address TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('POOL','QUOTE')), provider TEXT NOT NULL,
  size_usd REAL, token_amount REAL, token_amount_raw TEXT, decimals INTEGER,
  request_url TEXT, captured_at REAL, http_status INTEGER, raw_sha256 TEXT, raw_ref TEXT,
  state TEXT NOT NULL, since_export_s REAL,
  reserve_usd REAL, price_usd REAL, out_usd REAL,
  price_impact REAL,                -- as the quote source returns it: a decimal ratio (0.01 is 1%)
  value_json TEXT,
  recorded_at REAL NOT NULL, content_hash TEXT NOT NULL,
  UNIQUE(content_hash)
);
CREATE INDEX IF NOT EXISTS bt_depth_snapshots_key ON bt_depth_snapshots(chain, mint, pool_address, kind, captured_at);
""",
}
V2_UP = "\n".join(V2_TABLES.values()) + "\n" + _triggers(list(V2_TABLES))
V2_DOWN = "\n".join(
    [f"DROP TRIGGER IF EXISTS {t}_no_update; DROP TRIGGER IF EXISTS {t}_no_delete;" for t in V2_TABLES]
    + [f"DROP TABLE IF EXISTS {t};" for t in reversed(list(V2_TABLES))]
)

MIGRATIONS = [(1, "backtesting core v1", V1_UP, V1_DOWN), (2, "forward depth collector", V2_UP, V2_DOWN)]
LATEST = max(m[0] for m in MIGRATIONS)
BT_TABLES = list(V1_TABLES) + list(V2_TABLES)


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()


def current_version(con: sqlite3.Connection) -> int:
    con.executescript(LEDGER)
    row = con.execute("SELECT MAX(version) FROM bt_schema_migrations").fetchone()
    return int(row[0] or 0)


def _run(con: sqlite3.Connection, script: str) -> None:
    try:
        con.executescript("BEGIN IMMEDIATE;\n" + script + "\nCOMMIT;")   # take the write lock first: a deferred read-then-write upgrade fails at once under WAL
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise


def migrate(con: sqlite3.Connection, target: int | None = None, migrations=None) -> list[int]:
    """Apply pending bt migrations. Idempotent. Never touches non-bt tables."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = {r[0]: r[1] for r in con.execute("SELECT version, checksum FROM bt_schema_migrations")}
    for v, _n, up, _d in migrations:
        if v in applied and applied[v] != _checksum(up):
            raise RuntimeError(f"backtest migration {v} changed after it was applied; add a new migration instead")
    done = []
    for v, name, up, _d in sorted(migrations):
        if v in applied or (target is not None and v > target):
            continue
        ledger = (f"INSERT INTO bt_schema_migrations(version,name,checksum,applied_at) "
                  f"VALUES ({int(v)}, '{name.replace(chr(39), '')}', '{_checksum(up)}', {time.time()!r});")
        try:
            _run(con, up + "\n" + ledger)
        except sqlite3.IntegrityError:
            # another connection applied the same version first (fresh database, concurrent first use); its whole
            # transaction won, ours rolled back. Accept only if the applied script is the same one.
            row = con.execute("SELECT checksum FROM bt_schema_migrations WHERE version=?", (int(v),)).fetchone()
            if row and row[0] == _checksum(up):
                continue
            raise
        done.append(v)
    return done


def rollback(con: sqlite3.Connection, target: int = 0, migrations=None) -> list[int]:
    """Drop bt migrations above target, newest first. Deletes bt rows: back up first."""
    migrations = migrations if migrations is not None else MIGRATIONS
    con.executescript(LEDGER)
    applied = sorted((r[0] for r in con.execute("SELECT version FROM bt_schema_migrations")), reverse=True)
    by_v = {m[0]: m for m in migrations}
    undone = []
    for v in applied:
        if v <= target:
            break
        _run(con, by_v[v][3] + f"\nDELETE FROM bt_schema_migrations WHERE version={int(v)};")
        undone.append(v)
    return undone


def backup_db(src: Path | str, dest: Path | str) -> Path:
    """Consistent copy of a live database using the sqlite backup API (safe with WAL)."""
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

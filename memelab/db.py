"""SQLite persistence for the Memecoin Investing Lab.

Every table that describes a changing quantity is append-only (snapshots), so history is preserved.
Current-state views are derived with "latest per token" queries rather than by overwriting rows.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("MEMELAB_DB", DATA_DIR / "memelab.sqlite"))

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS tokens (
  mint TEXT PRIMARY KEY,
  chain TEXT NOT NULL DEFAULT 'solana',
  name TEXT, symbol TEXT, decimals INTEGER,
  token_program TEXT,
  creator TEXT, dev_wallet TEXT,
  launchpad TEXT, graduated_pool TEXT, graduated_at TEXT,
  first_pool_at TEXT,
  website TEXT, twitter TEXT, telegram TEXT,
  identity_confidence TEXT,            -- HIGH / MODERATE / LOW / NOT VERIFIED
  identity_notes TEXT,
  first_seen_at REAL NOT NULL,
  last_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pools (
  pool_address TEXT PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  dex TEXT, pair_label TEXT, quote_mint TEXT, quote_symbol TEXT,
  pool_created_at TEXT,
  first_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  source TEXT NOT NULL,
  price_usd REAL, price_sol REAL,
  circ_supply REAL, total_supply REAL, max_supply REAL,
  market_cap REAL, fdv REAL,
  liquidity_usd REAL,
  vol_5m REAL, vol_1h REAL, vol_6h REAL, vol_24h REAL,
  buys_1h INTEGER, sells_1h INTEGER, buys_24h INTEGER, sells_24h INTEGER,
  buyers_1h INTEGER, sellers_1h INTEGER, buyers_24h INTEGER, sellers_24h INTEGER,
  buy_vol_24h REAL, sell_vol_24h REAL,
  organic_buy_vol_24h REAL, organic_sell_vol_24h REAL,
  net_buyers_1h INTEGER, net_buyers_24h INTEGER,
  holder_count INTEGER,
  chg_5m REAL, chg_1h REAL, chg_6h REAL, chg_24h REAL,
  raw_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_ms_mint_time ON market_snapshots(mint, observed_at);

CREATE TABLE IF NOT EXISTS pool_snapshots (
  id INTEGER PRIMARY KEY,
  pool_address TEXT NOT NULL REFERENCES pools(pool_address),
  observed_at REAL NOT NULL,
  source TEXT NOT NULL,
  reserve_usd REAL, base_reserve REAL, quote_reserve REAL,
  vol_24h REAL, buys_24h INTEGER, sells_24h INTEGER,
  price_usd REAL,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS liquidity_quotes (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  side TEXT NOT NULL,                  -- BUY or SELL
  usd_size REAL NOT NULL,
  in_amount REAL, out_amount REAL,
  in_mint TEXT, out_mint TEXT,
  effective_price_usd REAL,
  price_impact_pct REAL,
  route_json TEXT, n_pools INTEGER, n_hops INTEGER,
  status TEXT,                         -- OK / NO_ROUTE / ERROR
  error TEXT
);
CREATE INDEX IF NOT EXISTS ix_lq ON liquidity_quotes(mint, observed_at);

CREATE TABLE IF NOT EXISTS token_authorities (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  source TEXT NOT NULL,
  mint_authority TEXT, freeze_authority TEXT,
  token_program TEXT,
  extensions_json TEXT,
  transfer_fee_bps INTEGER, transfer_fee_max REAL, transfer_fee_authority TEXT,
  permanent_delegate TEXT,
  metadata_mutable INTEGER, update_authority TEXT,
  supply_raw TEXT, decimals INTEGER
);

CREATE TABLE IF NOT EXISTS holders (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  source TEXT NOT NULL,
  rank INTEGER,
  token_account TEXT, owner TEXT,
  amount REAL, pct REAL,
  classification TEXT,                 -- POOL / BURN / CEX / PROTOCOL / VESTING / TEAM / DEV / INVESTOR / UNKNOWN
  classification_basis TEXT,
  insider_flag INTEGER
);
CREATE INDEX IF NOT EXISTS ix_holders ON holders(mint, observed_at);

CREATE TABLE IF NOT EXISTS wallets (
  address TEXT PRIMARY KEY,
  first_seen_at REAL NOT NULL,
  label TEXT, label_source TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS wallet_clusters (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  cluster_key TEXT NOT NULL,
  members_json TEXT NOT NULL,
  combined_pct REAL,
  evidence_json TEXT,                  -- list of {fact, inference, confidence}
  confidence TEXT
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
  id INTEGER PRIMARY KEY,
  mint TEXT REFERENCES tokens(mint),
  pool_address TEXT,
  tx_hash TEXT, block_time TEXT, block_number INTEGER,
  wallet TEXT, kind TEXT,              -- buy / sell / transfer
  base_amount REAL, quote_amount REAL, usd REAL, price_usd REAL,
  source TEXT,
  UNIQUE(tx_hash, wallet, kind, base_amount)
);
CREATE INDEX IF NOT EXISTS ix_wtx ON wallet_transactions(mint, block_time);

CREATE TABLE IF NOT EXISTS social_snapshots (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  source TEXT NOT NULL,
  metric TEXT NOT NULL, value REAL, text_value TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS price_levels (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  observed_at REAL NOT NULL,
  timeframe TEXT, kind TEXT,           -- SUPPORT / RESISTANCE / SWING_HIGH / SWING_LOW / RANGE_HIGH / RANGE_LOW
  low REAL, high REAL,
  strength REAL, why TEXT
);

CREATE TABLE IF NOT EXISTS theses (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL REFERENCES tokens(mint),
  created_at REAL NOT NULL,
  lifecycle TEXT, structure TEXT,
  thesis_text TEXT, invalidation_text TEXT,
  score INTEGER, score_breakdown_json TEXT,
  fatal_flags_json TEXT,
  status TEXT,
  confidence TEXT,
  report_path TEXT,
  snapshot_json TEXT                   -- compact state for "what changed" diffs
);
CREATE INDEX IF NOT EXISTS ix_theses ON theses(mint, created_at);

CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  thesis_id INTEGER REFERENCES theses(id),
  mint TEXT NOT NULL,
  style TEXT,                          -- ANTICIPATION / CONFIRMATION / PULLBACK / BREAKOUT_RETEST
  condition TEXT, zone_low REAL, zone_high REAL,
  invalidation_level REAL, invalidation_text TEXT,
  expected_execution TEXT,
  rr_json TEXT
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL,
  opened_at REAL, closed_at REAL,
  paper INTEGER NOT NULL DEFAULT 1,
  entry_price REAL, size_usd REAL, tokens REAL,
  invalidation_price REAL, max_risk_usd REAL,
  setup_type TEXT, lifecycle_at_entry TEXT, score_at_entry INTEGER,
  regime TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS exits (
  id INTEGER PRIMARY KEY,
  position_id INTEGER NOT NULL REFERENCES positions(id),
  exited_at REAL, price REAL, tokens REAL, usd_realized REAL,
  reason TEXT, displayed_value_usd REAL, slippage_pct REAL
);

CREATE TABLE IF NOT EXISTS trade_reviews (
  id INTEGER PRIMARY KEY,
  position_id INTEGER NOT NULL REFERENCES positions(id),
  reviewed_at REAL,
  quadrant TEXT,                       -- GOOD_DECISION_GOOD_OUTCOME etc
  thesis_quality TEXT, entry_quality TEXT, sizing TEXT, execution TEXT,
  risk_mgmt TEXT, profit_taking TEXT, exit_quality TEXT,
  process_errors TEXT, missed_evidence TEXT, unexpected TEXT,
  mae_pct REAL, mfe_pct REAL, realized_pct REAL, displayed_pct REAL
);

CREATE TABLE IF NOT EXISTS rejections (
  id INTEGER PRIMARY KEY,
  mint TEXT NOT NULL,
  symbol TEXT,
  rejected_at REAL NOT NULL,
  stage TEXT,
  why_surfaced TEXT, why_failed TEXT, evidence TEXT,
  reconsider_if TEXT
);
CREATE INDEX IF NOT EXISTS ix_rej ON rejections(mint);

CREATE TABLE IF NOT EXISTS watchlist (
  mint TEXT PRIMARY KEY REFERENCES tokens(mint),
  added_at REAL NOT NULL,
  status TEXT NOT NULL,
  last_status_change REAL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS fetch_log (
  id INTEGER PRIMARY KEY,
  fetched_at REAL NOT NULL,
  plan_id TEXT, key TEXT, url TEXT, status INTEGER, bytes INTEGER, error TEXT
);
"""


def now() -> float:
    return time.time()


@contextmanager
def connect(path: Path | str | None = None):
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(path: Path | str | None = None) -> None:
    from .catalyst.schema import CATALYST_SCHEMA
    from .chains.schema import CHAINS_SCHEMA, migrate
    from .chains import registry
    with connect(path) as con:
        con.executescript(SCHEMA)
        con.executescript(CATALYST_SCHEMA)
        con.executescript(CHAINS_SCHEMA)
        migrate(con)
        from .launch.schema import LAUNCH_SCHEMA, migrate as launch_migrate
        con.executescript(LAUNCH_SCHEMA)
        launch_migrate(con)
        registry.sync(con)
        from .social.schema import migrate as social_migrate
        social_migrate(con)


def upsert_token(con: sqlite3.Connection, mint: str, **fields: Any) -> None:
    t = now()
    row = con.execute("SELECT mint FROM tokens WHERE mint=?", (mint,)).fetchone()
    clean = {k: v for k, v in fields.items() if v is not None}
    if row is None:
        cols = ["mint", "first_seen_at", "last_seen_at"] + list(clean)
        vals = [mint, t, t] + list(clean.values())
        con.execute(f"INSERT INTO tokens ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", vals)
    else:
        clean["last_seen_at"] = t
        sets = ",".join(f"{k}=?" for k in clean)
        con.execute(f"UPDATE tokens SET {sets} WHERE mint=?", list(clean.values()) + [mint])


def insert(con: sqlite3.Connection, table: str, row: dict[str, Any]) -> int:
    row = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
    cols = list(row)
    cur = con.execute(
        f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        list(row.values()),
    )
    return cur.lastrowid


def insert_many(con: sqlite3.Connection, table: str, rows: Iterable[dict[str, Any]]) -> None:
    for r in rows:
        insert(con, table, r)


def latest(con: sqlite3.Connection, table: str, mint: str, time_col: str = "observed_at") -> sqlite3.Row | None:
    return con.execute(
        f"SELECT * FROM {table} WHERE mint=? ORDER BY {time_col} DESC LIMIT 1", (mint,)
    ).fetchone()


def previous_thesis(con: sqlite3.Connection, mint: str) -> sqlite3.Row | None:
    return con.execute(
        "SELECT * FROM theses WHERE mint=? ORDER BY created_at DESC LIMIT 1", (mint,)
    ).fetchone()


def is_rejected(con: sqlite3.Connection, mint: str) -> sqlite3.Row | None:
    return con.execute(
        "SELECT * FROM rejections WHERE mint=? ORDER BY rejected_at DESC LIMIT 1", (mint,)
    ).fetchone()


if __name__ == "__main__":
    init_db()
    print(f"initialized {DB_PATH}")

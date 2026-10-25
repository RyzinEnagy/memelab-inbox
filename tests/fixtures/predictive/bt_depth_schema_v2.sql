-- Fixture: the documented schema of the backtesting forward depth collector, copied as text (not imported) from
-- memelab/backtest/schema.py (LEDGER and V2_TABLES, migration 2) at commit 12f278b of origin/feature/backtesting
-- (D-BT-034, D-BT-035; predictive PI-D-044, PI-D-054). Used only to build test databases for
-- memelab/predictive/depth_adapter.py. Append-only triggers of that migration are added by the test helper.
CREATE TABLE IF NOT EXISTS bt_schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  checksum TEXT NOT NULL,
  applied_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS bt_depth_decisions (
  id INTEGER PRIMARY KEY,
  chain TEXT NOT NULL, mint TEXT NOT NULL, pool_address TEXT,
  pool_source TEXT NOT NULL CHECK (pool_source IN ('EXPORT_PRIMARY_POOL','EXPORT_GRADUATED_POOL','NONE_IN_EXPORT','UNSUPPORTED_CHAIN')),
  export_commit TEXT NOT NULL, export_time REAL NOT NULL, export_path TEXT,
  created_at REAL NOT NULL, row_sha256 TEXT NOT NULL, status TEXT,
  recorded_at REAL NOT NULL, content_hash TEXT NOT NULL,
  UNIQUE(chain, mint, row_sha256)
);
CREATE INDEX IF NOT EXISTS bt_depth_decisions_time ON bt_depth_decisions(export_time);
CREATE TABLE IF NOT EXISTS bt_depth_pool_lookups (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL, decision_id INTEGER NOT NULL REFERENCES bt_depth_decisions(id),
  chain TEXT NOT NULL, mint TEXT NOT NULL, attempt INTEGER NOT NULL,
  request_url TEXT, captured_at REAL, http_status INTEGER, raw_sha256 TEXT, raw_ref TEXT,
  state TEXT NOT NULL, pool_address TEXT, value_json TEXT,
  recorded_at REAL NOT NULL, content_hash TEXT NOT NULL,
  UNIQUE(content_hash)
);
CREATE INDEX IF NOT EXISTS bt_depth_pool_lookups_dec ON bt_depth_pool_lookups(decision_id, state);
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
CREATE INDEX IF NOT EXISTS bt_depth_snapshots_run ON bt_depth_snapshots(run_id);

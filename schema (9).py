"""Multi-chain tables. All quantity tables are append-only snapshots; current state is "latest per key"."""

CHAINS_SCHEMA = """
CREATE TABLE IF NOT EXISTS chains (
  chain_id TEXT PRIMARY KEY,                -- solana / base / bsc / ethereum / ...
  name TEXT NOT NULL, tier INTEGER, family TEXT,
  evm_chain_id INTEGER, gt_network TEXT, llama_slug TEXT, cg_platform TEXT, cg_native_id TEXT, cg_meme_category TEXT, ds_chain TEXT,
  native_symbol TEXT, wrapped_native TEXT, router TEXT, rpc_url TEXT, goplus_id TEXT, explorer TEXT,
  launchpads_json TEXT, typical_gas_usd REAL, block_time_s REAL, token_standards_json TEXT, notes TEXT,
  status TEXT,                              -- ACTIVE / LOW-PRIORITY MONITORING / EMERGING / MONITOR
  status_reason TEXT,
  research_allocation TEXT,                 -- FULL / PARTIAL / WATCHLIST / NONE (set by the rotation engine)
  first_seen_at REAL, updated_at REAL
);

CREATE TABLE IF NOT EXISTS chain_snapshots (
  id INTEGER PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  tvl_usd REAL, tvl_chg_7d_pct REAL,
  dex_vol_24h REAL, dex_vol_7d_avg REAL, dex_vol_30d_avg REAL, dex_vol_chg_7d_pct REAL,
  stablecoin_mcap REAL, stablecoin_chg_7d_pct REAL,
  native_price_usd REAL, native_chg_24h REAL, native_chg_7d REAL,
  raw_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_cs ON chain_snapshots(chain_id, observed_at);

CREATE TABLE IF NOT EXISTS chain_dex_activity (
  id INTEGER PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  trending_pools INTEGER, new_pools_24h INTEGER, pools_over_100k_liq INTEGER,
  median_pool_vol_liq_ratio REAL, trending_vol_24h REAL, trending_tx_24h INTEGER, trending_unique_buyers_24h INTEGER,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS chain_meme_activity (
  id INTEGER PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  meme_mcap REAL, meme_mcap_chg_24h_pct REAL, meme_vol_24h REAL, meme_count INTEGER,
  meme_share_of_trending REAL, meme_gainers_24h INTEGER, meme_losers_24h INTEGER,
  boosted_tokens INTEGER, new_profiles INTEGER,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS chain_flows (
  id INTEGER PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  stablecoin_net_7d REAL, tvl_net_7d REAL, bridge_net_24h REAL,
  note TEXT, raw_json TEXT
);

CREATE TABLE IF NOT EXISTS chain_scores (
  id INTEGER PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  observed_at REAL NOT NULL,
  soi REAL NOT NULL,
  dex_activity REAL, meme_activity REAL, participation REAL, capital_flows REAL, attention REAL, opportunity_quality REAL,
  components_json TEXT, unknown_json TEXT,
  trend TEXT,                               -- RISING / FLAT / FALLING / UNKNOWN (vs previous score)
  rotation_statement TEXT, confidence TEXT, research_allocation TEXT
);
CREATE INDEX IF NOT EXISTS ix_csc ON chain_scores(chain_id, observed_at);

CREATE TABLE IF NOT EXISTS narratives (
  narrative_id TEXT PRIMARY KEY,
  name TEXT NOT NULL, source TEXT,          -- coingecko_category / keyword / catalyst
  keywords_json TEXT, cg_category_id TEXT,
  first_seen_at REAL NOT NULL, last_seen_at REAL NOT NULL,
  lifecycle TEXT,                           -- EMERGING / ACCELERATING / MATURE / MANIA / EXHAUSTING / DEAD / UNKNOWN
  lifecycle_reason TEXT
);

CREATE TABLE IF NOT EXISTS narrative_snapshots (
  id INTEGER PRIMARY KEY,
  narrative_id TEXT NOT NULL REFERENCES narratives(narrative_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  mcap REAL, mcap_chg_24h_pct REAL, vol_24h REAL, token_count INTEGER, top3_json TEXT,
  trending_mentions INTEGER, catalyst_events_7d INTEGER, chains_json TEXT,
  lifecycle TEXT, raw_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_ns ON narrative_snapshots(narrative_id, observed_at);

CREATE TABLE IF NOT EXISTS narrative_tokens (
  narrative_id TEXT NOT NULL REFERENCES narratives(narrative_id),
  chain_id TEXT, mint TEXT NOT NULL, symbol TEXT,
  basis TEXT, first_seen_at REAL NOT NULL, last_seen_at REAL NOT NULL,
  PRIMARY KEY (narrative_id, mint)
);

CREATE TABLE IF NOT EXISTS launchpads (
  launchpad_id TEXT PRIMARY KEY,
  chain_id TEXT NOT NULL REFERENCES chains(chain_id),
  name TEXT, dex_ids_json TEXT, notes TEXT, first_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS launchpad_snapshots (
  id INTEGER PRIMARY KEY,
  launchpad_id TEXT NOT NULL REFERENCES launchpads(launchpad_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL,
  new_pools_sample INTEGER, pools_in_trending INTEGER, sample_vol_24h REAL, sample_liq REAL, graduations_sample INTEGER,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS cross_chain_relative_strength (
  id INTEGER PRIMARY KEY,
  observed_at REAL NOT NULL,
  chain_id TEXT NOT NULL, mint TEXT NOT NULL, symbol TEXT,
  chg_24h REAL, chain_meme_median_24h REAL, global_meme_median_24h REAL, native_chg_24h REAL,
  rs_vs_chain REAL, rs_vs_global REAL, rs_vs_native REAL, rank_global INTEGER, note TEXT
);

CREATE TABLE IF NOT EXISTS regime_snapshots (
  id INTEGER PRIMARY KEY,
  observed_at REAL NOT NULL,
  regime TEXT NOT NULL,                     -- RISK-ON / NEUTRAL / RISK-OFF / HIGH-VOLATILITY SPECULATION / CAPITAL FLIGHT / UNKNOWN
  confidence TEXT, statement TEXT,
  btc_trend TEXT, eth_trend TEXT, sol_trend TEXT, bnb_trend TEXT,
  btc_vol_30d REAL, btc_dd_90d REAL, breadth_pct REAL, funding_avg REAL, oi_usd REAL,
  stable_mcap REAL, stable_chg_7d_pct REAL, total_mcap REAL, total_mcap_chg_24h REAL, btc_dominance REAL,
  components_json TEXT, unknown_json TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_baskets (
  id INTEGER PRIMARY KEY,
  observed_at REAL NOT NULL, bucket TEXT NOT NULL,   -- MICRO / SMALL / MID / LARGE
  members_json TEXT, median_chg_24h REAL, median_chg_7d REAL, n INTEGER
);

CREATE TABLE IF NOT EXISTS ecosystem_alerts (
  id INTEGER PRIMARY KEY,
  alerted_at REAL NOT NULL, kind TEXT NOT NULL,        -- EMERGING_CHAIN / ROTATION / NARRATIVE / DE_EMPHASIS / REGIME
  subject TEXT, level TEXT,                            -- MONITOR / BUILD PARTIAL / BUILD FULL / INFO
  text TEXT NOT NULL, evidence_json TEXT
);
"""

MIGRATIONS = [
    # tokens gain chain_id (alias of chain) and narrative_id; sqlite has no IF NOT EXISTS for columns, so guard in code
    ("tokens", "narrative_id", "ALTER TABLE tokens ADD COLUMN narrative_id TEXT"),
    ("tokens", "token_standard", "ALTER TABLE tokens ADD COLUMN token_standard TEXT"),
    ("tokens", "primary_pool", "ALTER TABLE tokens ADD COLUMN primary_pool TEXT"),
]


def migrate(con) -> None:
    for table, col, sql in MIGRATIONS:
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            con.execute(sql)

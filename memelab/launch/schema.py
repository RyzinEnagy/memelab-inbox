"""Pre-launch and new-launch tables. Observations, scores, wallet flags, monitor windows and cohort follow-ups are append-only."""

LAUNCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS upcoming_launches (
  launch_id TEXT PRIMARY KEY,               -- '<chain>:<contract>' once a contract exists, else 'ann:<slug>'
  project TEXT, symbol TEXT, chain TEXT,
  contract TEXT,                            -- NULL until publicly established
  contract_verified INTEGER NOT NULL DEFAULT 0,
  contract_source TEXT,                     -- which index established it (launchpad API, chain RPC, explorer)
  launchpad TEXT,
  state TEXT NOT NULL,                      -- A ANNOUNCED_NO_CONTRACT / B DEPLOYED_NOT_TRADING / C BONDING_CURVE / D LIQUIDITY_PENDING / E JUST_LAUNCHED
  phase TEXT NOT NULL DEFAULT 'PRE_LAUNCH', -- PRE_LAUNCH / NEW_LAUNCH_MONITOR / NORMAL_WATCHLIST / REJECTED
  scheduled_at REAL, created_at REAL, first_trade_at REAL, discovered_at REAL NOT NULL, updated_at REAL NOT NULL,
  source TEXT, sources_json TEXT, official_links_json TEXT,
  creator TEXT, narrative_id TEXT, pool TEXT, curve_pool TEXT,
  expected_valuation_usd REAL, expected_liquidity_usd REAL, valuation_basis TEXT,
  tokenomics_json TEXT, team_alloc_pct REAL, social_json TEXT, risk_flags_json TEXT,
  prelaunch_score REAL, completeness REAL, confidence TEXT,
  status TEXT, status_reason TEXT, entry_view TEXT,
  transitioned_at REAL, notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_ul_phase ON upcoming_launches(phase, status);
CREATE INDEX IF NOT EXISTS ix_ul_creator ON upcoming_launches(creator);

CREATE TABLE IF NOT EXISTS launch_observations (
  id INTEGER PRIMARY KEY,
  launch_id TEXT NOT NULL REFERENCES upcoming_launches(launch_id),
  observed_at REAL NOT NULL, source TEXT NOT NULL, state TEXT,
  price_usd REAL, mcap_usd REAL, fdv_usd REAL, liquidity_usd REAL,
  curve_progress_pct REAL, raised_quote REAL, quote_symbol TEXT,
  holders INTEGER, top10_pct REAL, dev_pct REAL, sniper_pct REAL,
  buyers INTEGER, sellers INTEGER, vol_usd REAL, replies INTEGER, is_live INTEGER,
  raw_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_lo ON launch_observations(launch_id, observed_at);

CREATE TABLE IF NOT EXISTS launch_scores (
  id INTEGER PRIMARY KEY,
  launch_id TEXT NOT NULL, scored_at REAL NOT NULL,
  score REAL, completeness REAL, confidence TEXT, status TEXT, status_reason TEXT, entry_view TEXT,
  components_json TEXT, fatal_json TEXT, verify_at_launch_json TEXT
);

CREATE TABLE IF NOT EXISTS deployer_history (
  id INTEGER PRIMARY KEY,
  deployer TEXT NOT NULL, chain TEXT, platform TEXT, observed_at REAL NOT NULL,
  launches INTEGER, launches_7d INTEGER, graduated INTEGER, best_ath_usd REAL, median_ath_usd REAL,
  abandoned INTEGER, flagged_rugs INTEGER, classification TEXT, evidence_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_dh ON deployer_history(deployer, observed_at);

CREATE TABLE IF NOT EXISTS launch_wallet_flags (
  id INTEGER PRIMARY KEY,
  launch_id TEXT NOT NULL, observed_at REAL NOT NULL,
  kind TEXT NOT NULL,                       -- PREPOSITION_CLUSTER / SNIPER_INVENTORY / DEV_SELLING / INSIDER_NETWORK / BUNDLED_LAUNCH
  wallets_json TEXT, pct_supply REAL, fact TEXT, inference TEXT, unknown TEXT
);

CREATE TABLE IF NOT EXISTS launchpad_stats (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL, chain TEXT, observed_at REAL NOT NULL,
  n INTEGER, graduation_rate REAL, median_ath_usd REAL, reach_100k_rate REAL, reach_1m_rate REAL,
  survival_24h REAL, survival_7d REAL, median_drawdown_pct REAL, rug_flag_rate REAL,
  quality_score REAL, basis TEXT
);

CREATE TABLE IF NOT EXISTS launch_cohort (
  mint TEXT PRIMARY KEY, chain TEXT, platform TEXT, symbol TEXT, creator TEXT,
  created_at REAL, start_mcap_usd REAL, first_seen_at REAL,
  last_checked REAL, mcap_usd REAL, ath_usd REAL, graduated INTEGER, last_trade_at REAL,
  mcap_24h REAL, mcap_7d REAL, mcap_30d REAL, rug_flag INTEGER,
  sample_basis TEXT                          -- 'newest' (unbiased cohort) or 'graduated' (survivorship-biased)
);

CREATE TABLE IF NOT EXISTS launch_monitor (
  id INTEGER PRIMARY KEY,
  launch_id TEXT NOT NULL, window TEXT NOT NULL,   -- 1m 5m 15m 1h 6h 24h
  observed_at REAL NOT NULL, age_minutes REAL, basis TEXT,   -- 'trades-reconstructed' or 'snapshot'
  metrics_json TEXT,
  UNIQUE(launch_id, window)
);

CREATE TABLE IF NOT EXISTS launch_alerts (
  id INTEGER PRIMARY KEY, launch_id TEXT, alerted_at REAL NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS launch_rejections (
  id INTEGER PRIMARY KEY, launch_id TEXT NOT NULL, rejected_at REAL NOT NULL,
  symbol TEXT, chain TEXT, contract TEXT, creator TEXT, reasons_json TEXT, evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS launch_transitions (
  id INTEGER PRIMARY KEY, launch_id TEXT NOT NULL, at REAL NOT NULL,
  from_phase TEXT, to_phase TEXT, reason TEXT, expected_json TEXT, actual_json TEXT, interpretation TEXT
);
"""


def migrate(con) -> None:
    """Add columns introduced after a database was first created."""
    have = {r[1] for r in con.execute("PRAGMA table_info(upcoming_launches)")}
    for col in ("pool", "curve_pool"):
        if col not in have:
            con.execute(f"ALTER TABLE upcoming_launches ADD COLUMN {col} TEXT")

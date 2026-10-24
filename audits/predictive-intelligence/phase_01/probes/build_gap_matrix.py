"""Phase 01: write architecture/GAP_MATRIX.csv (facility x need), each cell with a status and a checkable anchor.

Line anchors are found by keyword, so a line number always points at the cited code at this HEAD; check_gap_anchors.py
re-verifies every anchor independently. Read-only over the repo except the CSV it writes.

    python audits/predictive-intelligence/phase_01/probes/build_gap_matrix.py
"""
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv"
NEEDS = ("POINT_IN_TIME_FEATURES", "EVENT_LABELS", "MODEL_TRAINING", "CALIBRATION_SCORING", "MODEL_REGISTRY", "DRIFT_MONITORING",
         "COST_LATENCY_CONTROL", "REPORT_CONSUMERS")


def L(path, kw):
    for i, line in enumerate((ROOT / path).read_text().splitlines(), 1):
        if kw in line:
            return (f"{path}:{i}", "line", kw)
    raise SystemExit(f"keyword {kw!r} not in {path}")


def G(pattern):
    return (f"git grep -i -E over memelab/ (memelab/predictive excluded) finds nothing for: {pattern}", "grep0", pattern)


def D(key):
    return ("audits/predictive-intelligence/phase_01/probes/decision_universe_summary.json#" + key, "data", key)


def P(glob):
    return (f"no path matches {glob}", "nopath", glob)


NO_ML = G(r"sklearn|lightgbm|xgboost|statsmodels|torch|\.fit\(")
NO_CAL = G(r"brier|log[_ ]?loss|isotonic|platt|calibration_curve|reliability_diagram")
NO_REG = G(r"model_registry|model_sha|joblib|pickle\.dump")
NO_DRIFT = G(r"population_stability|ks_2samp|drift_alert|feature_drift")
rows = []


def add(fac, need, status, ev, note):
    rows.append({"facility": fac, "need": need, "status": status, "evidence": ev[0], "check_kind": ev[1], "check_value": ev[2], "note": note})


F = "HIST_MARKET"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/social/replay_sources.py", "PROVIDER_LAG = "), "candle availability = close + 300 s is HEURISTIC; collector OHLCV only 2026-10-06 to 10-08 (33 pools); market_snapshots and candles not exported (state.py TABLES); a thesis snapshot price has one time per thesis")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/social/outcomes_core.py", "def evaluate("), "endpoint returns with PENDING/MISSING/NON_EXECUTABLE and MFE/MAE; no first-touch barrier label; needs a sibling barrier function fed by a GeckoTerminal backfill")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "no ML library or fitted model anywhere")
add(F, "CALIBRATION_SCORING", "MISSING", NO_CAL, "no proper scoring or calibration code")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "no model artifacts or registry")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "no drift monitoring")
add(F, "COST_LATENCY_CONTROL", "CONFLICT", L("memelab/bridge/collector.js", "\"api.geckoterminal.com\": 2600"), "collector paces GeckoTerminal at 2.6 s (about 23 a minute); the current spec says about 10 a minute (PI-D-010); the Phase 01 probe got HTTP 429 on its 6th call at about 9 a minute")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/report.py", "def render_token_report"), "token and scout reports render market facts")
F = "HOLDERS"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/modules/m25_watchlist_monitor.py", "def compact_snapshot"), "thesis snapshot keeps holders, adj_top10, cluster_pct, dev_pct, insider_pct per thesis (version-dependent, PI-D-008); holders table stamped t and not exported")
add(F, "EVENT_LABELS", "MISSING", L("memelab/state.py", "TABLES = ["), "holders and wallet_transactions are not exported: no distribution label (distribution_event_24h BLOCKED_NO_DATA)")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", NO_CAL, "")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "PARTIAL", L("memelab/bridge/collector.js", "api.rugcheck.xyz"), "holder data come with the bundle (rugcheck paced 0.4 s); no per-forecast budget; inference reuses the fetched bundle")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/report.py", "## Ownership"), "ownership section in the token report")
F = "LP_DEPTH"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/modules/m06_executable_depth.py", "exit_capacity_usd_3pct"), "exit capacity at 3% impact kept once per thesis (stale by the decision lag); pool_snapshots and liquidity_quotes not exported after 2026-10-08")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/social/outcomes_core.py", "EXIT_LIQUIDITY_LOST"), "label logic for quotes and liquidity exists; historical depth data do not (exit-adjusted target BLOCKED; liquidity degradation needs forward collection)")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", NO_CAL, "")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "PARTIAL", L("memelab/bridge/plan.py", "self.add(f\"jq:BUY"), "Jupiter quotes fetched per deep plan; no budget exists for forward quote collection")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/report.py", "## Executable depth"), "executable depth section in the token report")
F = "SOCIAL_SIGNALS"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/social/market_context.py", "def observed_facts"), "versioned market facts at posting and fetch time; fixtures only; the social engine is rated NOT READY by its own audit")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/social/outcomes_core.py", "STATUSES = ("), "signal ledger PENDING/MEASURED/MISSING/NON_EXECUTABLE/INVALIDATED; the ledger is private and empty")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "PARTIAL", L("memelab/social/alpha_core.py", "def wilson("), "Wilson and order-statistic intervals; no proper score")
add(F, "MODEL_REGISTRY", "PARTIAL", L("memelab/social/outcomes_ledger.py", "ledger_no_update"), "append-only hash-chained ledger (UPDATE and DELETE refused): the pattern to reuse for forecast records; not a model registry")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "VERIFIED_PRESENT", L("memelab/social/schema.py", "CREATE TABLE social_api_spend"), "per-request spend rows for paid social APIs")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/report.py", "if social is not None"), "opt-in section appended after the unchanged scout body; byte-identical when off (tests/test_social_research.py)")
F = "SOCIAL_REPLAY"
add(F, "POINT_IN_TIME_FEATURES", "VERIFIED_PRESENT", L("memelab/social/replay_core.py", "class CutoffView"), "cutoff view with audited _avail and LeakageError; truncation-invariance proof (leakage_check); tested on fixtures")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/social/replay_core.py", "def outcome("), "reuses outcomes_core with a label clock per split; endpoint returns only")
add(F, "MODEL_TRAINING", "PARTIAL", L("memelab/social/replay_core.py", "class LabelGate"), "chronological 50/25/25 split, embargo, LabelGate (train-only tuning, frozen hash); single split, no walk-forward, no model fit")
add(F, "CALIBRATION_SCORING", "PARTIAL", L("memelab/social/replay_core.py", "def summarize("), "Wilson and Bonferroni-adjusted intervals; no Brier or log loss")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "run hashes only")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "VERIFIED_PRESENT", L("memelab/social/replay_core.py", "Pure engine: no I/O, no network"), "offline, no network")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/social/replay_core.py", "def render("), "plain-English replay report")
F = "CATALYST"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/catalyst/schema.py", "first_seen_at REAL NOT NULL"), "published_at, retrieved_at and first_seen_at kept apart; catalyst tables are not exported, every scheduled session starts empty")
add(F, "EVENT_LABELS", "CONFLICT", L("memelab/catalyst/monitor.py", "def record_outcomes"), "first market snapshot at or after the horizon with no maximum wait, keyed on TICKER_MATCH links (PI-D-007): conflicts with the label rules; not used")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", NO_CAL, "")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "VERIFIED_PRESENT", L("memelab/catalyst/firecrawl.py", "def cap_reason"), "Firecrawl credit cap checked before each call")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/catalyst/report.py", "def render("), "catalyst report")
F = "BACKTEST_V12"
for need in NEEDS:
    add(F, need, "MISSING", P("memelab/backtest*"), "Backtesting & Stress-Testing v1.2 is not installed on any branch: BACKTEST_NOT_AVAILABLE (PI-D-006, P34)")
F = "LAUNCH_COHORT"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", D("launch_cohort.first_seen_range"), "1,422 launches first seen inside one 22 h window (2026-10-08T13:45Z to 10-09T11:57Z); first_seen_at = collector t")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/launch/discover.py", "mcap_24h"), "market cap at 24 h, 7 d, 30 d read inside windows without a read time; filled for 19, 8, 2; rug_flag NULL everywhere")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", L("memelab/launch/cohort.py", "MIN_N = 20"), "sample-size gate MIN_N 20 only; no proper score")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "PARTIAL", L("memelab/bridge/collector.js", "const PACE"), "collector pacing only")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/launch/report.py", "def render("), "launch report")
F = "TRADE_OUTCOMES"
add(F, "POINT_IN_TIME_FEATURES", "MISSING", L("memelab/modules/m28_statistical_analysis.py", "def load_trades"), "positions, exits and trade_reviews are empty in every record")
add(F, "EVENT_LABELS", "PARTIAL", L("memelab/modules/m27_post_trade_review.py", "def _mae_mfe"), "MAE/MFE for closed real positions; no data")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "PARTIAL", L("memelab/modules/m28_statistical_analysis.py", "def bootstrap_diff_ci"), "bootstrap interval on an expectancy difference and n thresholds; no proper score")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "VERIFIED_PRESENT", L("memelab/modules/m28_statistical_analysis.py", "def stats("), "reads the lab DB only")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/modules/m27_post_trade_review.py", "def store_review"), "post-trade review stored and reported")
F = "DECISION_RECORDS"
add(F, "POINT_IN_TIME_FEATURES", "CONFLICT", L("memelab/db.py", "CREATE TABLE IF NOT EXISTS theses"), "created_at is the collector-run start and the row is written later (PI-D-011); no inputs or code version (PI-D-008); provable decision time = first export commit time, matched to GitHub push events (PI-D-015)")
add(F, "EVENT_LABELS", "MISSING", D("events_solana_priced.24h.matured_by_data_end"), "no label attached to any thesis; 252 thinned 24 h Solana decisions matured by 2026-10-23")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", L("memelab/modules/m16_risk_reward.py", "priors, not measured frequencies"), "score and R/R bands are not probabilities")
add(F, "MODEL_REGISTRY", "PARTIAL", L("memelab/state.py", "def export("), "the export commit SHA is the only version handle for stored scores (PI-D-008)")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "")
add(F, "COST_LATENCY_CONTROL", "VERIFIED_PRESENT", L("memelab/pipeline.py", "def run_modules"), "modules are pure functions of the fetched bundle; no network at scoring")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/report.py", "def render_scout_report"), "scout report with optional appended sections")
F = "REGIME_NARRATIVE"
add(F, "POINT_IN_TIME_FEATURES", "PARTIAL", L("memelab/chains/regime.py", "def compute("), "regime and narrative snapshots exported with observed_at (23 and 925 rows), 2026-10-07 to 10-23")
add(F, "EVENT_LABELS", "MISSING", L("memelab/chains/narrative.py", "def compute("), "lifecycle labels are rule states, not outcomes")
add(F, "MODEL_TRAINING", "MISSING", NO_ML, "")
add(F, "CALIBRATION_SCORING", "MISSING", NO_CAL, "")
add(F, "MODEL_REGISTRY", "MISSING", NO_REG, "")
add(F, "DRIFT_MONITORING", "MISSING", NO_DRIFT, "regime labels can stratify drift reports later")
add(F, "COST_LATENCY_CONTROL", "PARTIAL", L("memelab/bridge/collector.js", "api.coingecko.com"), "collector pacing only")
add(F, "REPORT_CONSUMERS", "VERIFIED_PRESENT", L("memelab/chains/report.py", "def render("), "cross-chain report")

if __name__ == "__main__":
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), dict(collections.Counter(r["status"] for r in rows)))

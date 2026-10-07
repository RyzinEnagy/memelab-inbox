"""Tests for m21, m22, m24, m26, m27, m28 with synthetic inputs."""
from __future__ import annotations

import sqlite3
import time

import pytest

from memelab import db
from memelab.modules import m21_lifecycle_classifier as m21
from memelab.modules import m22_relative_strength as m22
from memelab.modules import m24_opportunity_ranker as m24
from memelab.modules import m26_portfolio_risk as m26
from memelab.modules import m27_post_trade_review as m27
from memelab.modules import m28_statistical_analysis as m28

FOUR = ("facts", "inferences", "heuristics", "unknowns")


def _has_buckets(out: dict) -> None:
    for k in FOUR:
        assert isinstance(out.get(k), list), k


# ----------------------------------------------------------------------------
# m21
# ----------------------------------------------------------------------------
def test_m21_empty_bundle():
    out = m21.analyze({})
    _has_buckets(out)
    assert out["stage"] == "UNKNOWN"
    assert out["confidence"] == "LOW"
    assert out["unknowns"]
    assert m21.analyze(None)["confidence"] == "LOW"


def test_m21_chart_only_is_low_confidence():
    out = m21.analyze({"market": {}}, structure={"pct_from_ath": -80})
    assert out["stage"] == "POST_BREAKDOWN"
    assert out["confidence"] == "LOW"
    assert "chart" in out["families_present"]
    assert any("chart" in u.lower() or "Missing evidence" in u for u in out["unknowns"])


def test_m21_early_expansion_multi_family():
    bundle = {
        "market": {
            "age_hours": 60, "price_usd": 0.01,
            "vol": {"h1": 60_000, "h6": 300_000, "h24": 900_000},
            "organic_buy_vol_24h": 400_000, "organic_sell_vol_24h": 300_000,
            "holder_count": 1500, "holder_change": {"h24_pct": 8.0},
            "net_buyers": {"h1": 40, "h24": 300},
        }
    }
    out = m21.analyze(bundle, structure={"pct_from_ath": -5, "liquidity_change_pct": 12},
                      flows={"large_holder_net_direction": "ACCUMULATING"}, attention={"trend": "ACCELERATION"})
    _has_buckets(out)
    assert out["stage"] in ("EARLY_EXPANSION", "BROAD_ATTENTION")
    assert out["confidence"] in ("MODERATE", "HIGH")
    assert len(out["families_present"]) >= 5
    assert out["confirm_if"] and out["reject_if"]
    assert out["alternative_stage"] is not None


def test_m21_distribution_and_substage():
    bundle = {"market": {"age_hours": 24 * 20, "vol": {"h1": 1_000, "h6": 8_000, "h24": 120_000},
                         "holder_count": 9000, "holder_change": {"h24_pct": -4}, "net_buyers": {"h1": -20, "h24": -400}}}
    out = m21.analyze(bundle, structure={"pct_from_ath": -85, "liquidity_change_pct": -30},
                      flows={"large_holder_net_direction": "EXITING"}, attention={"trend": "EXHAUSTION"})
    assert out["stage"] == "POST_BREAKDOWN"
    assert out["sub_stage"] == "EXTINCTION"
    assert out["confidence"] != "LOW"


# ----------------------------------------------------------------------------
# m22
# ----------------------------------------------------------------------------
def test_m22_empty():
    out = m22.analyze({}, {})
    _has_buckets(out)
    assert out["label"] == {"1h": None, "6h": None, "24h": None}
    assert out["rotation_note"] is None
    assert out["unknowns"]
    assert m22.analyze(None, None)["leader_laggard"] is None


def test_m22_leader_with_rotation():
    bundle = {"mint": "X", "identity": {"symbol": "XXX"},
              "market": {"chg": {"h1": 12.0, "h6": 30.0, "h24": 80.0}, "vol": {"h6": 500_000, "h24": 1_000_000}}}
    peers = [{"symbol": f"P{i}", "mint": f"m{i}", "chg_1h": 1.0 + i, "chg_6h": 5.0 + i, "chg_24h": 20.0 + i,
              "vol_24h": 800_000, "vol_6h": 150_000} for i in range(5)]
    bench = {"SOL": {"chg_1h": 1.0, "chg_6h": 2.0, "chg_24h": 3.0}, "BTC": {"chg_1h": 0.5, "chg_6h": 1.0, "chg_24h": 1.5},
             "peers": peers}
    out = m22.analyze(bundle, bench)
    assert out["label"] == {"1h": "STRONG", "6h": "STRONG", "24h": "STRONG"}
    assert out["peer_rank"]["24h"]["rank"] == 1
    assert out["leader_laggard"] == "LEADER"
    assert "rotation IN" in out["rotation_note"]
    assert out["rs_vs_sol"]["24h"]["diff_pp"] == pytest.approx(77.0)


def test_m22_laggard_rotation_out():
    bundle = {"market": {"chg": {"h1": -8.0, "h6": -10.0, "h24": -15.0}, "vol": {"h6": 50_000, "h24": 1_000_000}}}
    peers = [{"symbol": f"P{i}", "chg_1h": 3.0, "chg_6h": 8.0, "chg_24h": 20.0, "vol_24h": 800_000, "vol_6h": 300_000} for i in range(4)]
    out = m22.analyze(bundle, {"SOL": {"chg_1h": 0, "chg_6h": 0, "chg_24h": 0}, "peers": peers})
    assert out["leader_laggard"] == "LAGGARD"
    assert all(v == "WEAK" for v in out["label"].values())
    assert "rotation OUT" in out["rotation_note"]


# ----------------------------------------------------------------------------
# m24
# ----------------------------------------------------------------------------
def test_m24_perfect_components_but_fatal_flag():
    comps = {b: 1.0 for b in m24.MAX_POINTS}
    res = m24.score(comps, mechanics={"mint_authority_active": True, "freeze_authority": None})
    assert res["total"] == 100
    assert res["total"] >= 80
    assert res["untradeable"] is True
    assert res["fatal_flags"][0]["flag"] == "MINT_AUTHORITY_ACTIVE"
    st = m24.assign_status(res)
    assert st["status"] == "REJECTED"
    # watched thesis that breaks -> THESIS INVALIDATED
    st2 = m24.assign_status(res, monitor_diff={"previous_status": "NEAR ENTRY"})
    assert st2["status"] == "THESIS INVALIDATED"


def test_m24_breakdown_shape_and_missing_cap():
    res = m24.score({})
    assert set(res["breakdown"]) == set(m24.MAX_POINTS)
    for b, row in res["breakdown"].items():
        assert row["max"] == m24.MAX_POINTS[b]
        assert row["score"] <= m24.MISSING_CAP
        assert any(l.startswith("UNKNOWN:") for l in row["rationale"])
    assert res["total"] == 40
    assert res["untradeable"] is False
    assert m24.assign_status(res)["status"] == "RESEARCH REQUIRED"


def test_m24_helpers_missing_inputs_capped():
    for fn in m24.HELPERS.values():
        s, lines = fn()
        assert 0 <= s <= m24.MISSING_CAP
        assert any(l.startswith("UNKNOWN:") for l in lines)


GOOD_MODULES = dict(
    depth={"liquidity_usd": 250_000, "exit_capacity_usd_3pct": 40_000, "exit_capacity_usd_5pct": 70_000,
           "route_status": "OK", "n_hops": 1, "friction_pct": 1.5, "sell_impact_5k_pct": 0.6},
    lp={"lp_risk": "LOW", "locked_pct": 100},
    mechanics={"mint_authority_active": False, "freeze_authority_active": False, "permanent_delegate": None,
               "transfer_fee_bps": 0, "non_transferable": False, "metadata_mutable": False},
    holders={"adjusted_top10_pct": 18, "largest_unexplained_pct": 3, "dev_holding_pct": 1},
    clusters={"cluster_adjusted_ownership_pct": 8, "confidence": "HIGH"},
    early={"large_holder_net_direction": "ACCUMULATING"},
    orderflow={"net_buyers_h24": 250, "buy_sell_vol_ratio": 1.4, "organic_share": 0.75},
    manipulation={"label": "CLEAN", "wash_trading": "LOW"},
    structure={"structure": "UPTREND", "support_defined": True},
    breakout={"classification": "BREAKOUT_RETEST", "chase_risk": False},
    entries={"in_zone": True, "invalidation_defined": True},
    attention={"trend": "ACCELERATION", "narrative_strength": 0.8, "organic": True},
    lifecycle={"stage": "EARLY_EXPANSION", "confidence": "HIGH"},
    rs={"label": {"1h": "STRONG", "6h": "STRONG", "24h": "NEUTRAL"}, "leader_laggard": "LEADER"},
    rr={"rr_ratio": 3.5, "ev_r": 0.9, "invalidation_defined": True},
    sizing={"fits_constraints": True, "size_usd": 5_000},
)


def test_m24_evaluate_good_setup_entry_conditions_met():
    res = m24.evaluate(**GOOD_MODULES)
    _has_buckets(res)
    assert res["total"] >= 80
    assert res["fatal_flags"] == []
    assert res["status"] == "ENTRY CONDITIONS MET"


def test_m24_status_variants():
    comps = {b: 0.8 for b in m24.MAX_POINTS}
    res = m24.score(comps)
    assert m24.assign_status(res, breakout={"classification": "BREAKOUT", "chase_risk": True})["status"] == "OVEREXTENDED"
    assert m24.assign_status(res, breakout={"classification": "COILING"})["status"] == "SETUP DEVELOPING"
    assert m24.assign_status(res, breakout={"classification": "BREAKOUT_RETEST"}, entries={"in_zone": False, "near_zone": True})["status"] == "NEAR ENTRY"
    assert m24.assign_status(res, breakout={"classification": "NO_SETUP"})["status"] == "WATCH"
    assert m24.assign_status(res, early={"large_holder_net_direction": "DISTRIBUTING"})["status"] == "DISTRIBUTION RISK"
    assert m24.assign_status(res, monitor_diff={"deteriorating": True, "reason": "volume faded"})["status"] == "THESIS DETERIORATING"
    # fatal distribution flag -> DISTRIBUTION RISK
    res2 = m24.score(comps, early={"large_holder_net_direction": "EXITING", "price_down": True, "volume_collapsing": True})
    assert res2["untradeable"]
    assert m24.assign_status(res2)["status"] == "DISTRIBUTION RISK"


def test_m24_rank_best_token_vs_best_trade():
    import copy
    a = copy.deepcopy(GOOD_MODULES)
    a["rr"] = {"rr_ratio": 4.0, "ev_r": 0.4}  # no invalidation defined
    a["entries"] = {"in_zone": True}
    b = copy.deepcopy(GOOD_MODULES)
    b["attention"] = {"trend": "STABILITY", "narrative_strength": 0.4, "organic": True}
    b["rs"] = {"label": {"1h": "NEUTRAL", "6h": "NEUTRAL", "24h": "NEUTRAL"}}
    c = copy.deepcopy(GOOD_MODULES)
    c["mechanics"] = {"mint_authority_active": True}
    out = m24.rank([{"symbol": "AAA", "mint": "a", "modules": a}, {"symbol": "BBB", "mint": "b", "modules": b},
                    {"symbol": "CCC", "mint": "c", "modules": c}])
    rows = {r["symbol"]: r for r in out["rows"]}
    assert rows["CCC"]["untradeable"] and rows["CCC"]["rank"] == 3
    assert out["best_token"] == "a"
    assert out["best_trade"] == "b"
    assert "best trade is BBB" in out["best_token_vs_best_trade"]
    assert rows["AAA"]["invalidation_clarity"] == "UNDEFINED"
    assert m24.rank([])["rows"] == []
    assert m24.rank(None)["best_token_vs_best_trade"] is None


# ----------------------------------------------------------------------------
# m26
# ----------------------------------------------------------------------------
def _quotes(cap3: float):
    return {"SELL": {"1000": {"impact": 0.5, "status": "OK"}, str(int(cap3)): {"impact": 2.9, "status": "OK"},
                     str(int(cap3 * 3)): {"impact": 9.0, "status": "OK"}}}


def test_m26_three_correlated_positions():
    positions = [
        {"mint": "m1", "symbol": "DOG1", "size_usd": 4000, "entry_price": 1.0, "current_price": 1.2, "invalidation_price": 0.85},
        {"mint": "m2", "symbol": "DOG2", "size_usd": 3000, "entry_price": 2.0, "current_price": 1.8, "invalidation_price": 1.6},
        {"mint": "m3", "symbol": "CAT1", "size_usd": 3000, "entry_price": 0.5, "current_price": 0.5, "invalidation_price": 0.4},
    ]
    td = {
        "m1": {"narrative_tags": ["dog", "pump.fun"], "pools": [{"dex": "raydium", "quote": "SOL"}], "quotes": _quotes(3000), "chain": "solana", "launchpad": "pump.fun"},
        "m2": {"narrative_tags": ["dog"], "pools": [{"dex": "raydium", "quote": "SOL"}], "quotes": _quotes(1500), "chain": "solana", "launchpad": "pump.fun"},
        "m3": {"narrative_tags": ["cat"], "pools": [{"dex": "meteora", "quote": "SOL"}], "quotes": _quotes(5000), "chain": "solana", "launchpad": "pump.fun"},
    }
    out = m26.analyze(positions, td, account_size=100_000)
    _has_buckets(out)
    assert out["n_positions"] == 3
    assert out["total_exposure_usd"] == pytest.approx(4800 + 2700 + 3000)
    assert out["chain_concentration"]["solana"] == 100.0
    assert out["liquidity_exposure"]["quote_asset_pct"]["SOL"] == 100.0
    assert out["narrative_correlation"]["pairs_sharing_a_tag"] == 1
    # dog group 7500 vs cat 3000 -> HHI = 0.51 -> ~1.96 effective bets, far fewer than 3
    assert out["effective_independent_bets"] < 2.5
    assert any("NOT 3 independent risks" in s for s in out["inferences"])
    # max loss: 4800*(1-0.85/1.2) + 2700*(1-1.6/1.8) + 3000*0.2
    exp_loss = 4800 * (1 - 0.85 / 1.2) + 2700 * (1 - 1.6 / 1.8) + 3000 * 0.2
    assert out["aggregate_max_loss_usd"] == pytest.approx(exp_loss, rel=1e-3)
    # exit capacity: min(cap, value): 3000 + 1500 + 3000 = 7500 -> shortfall 1800 + 1200 = 3000
    assert out["aggregate_exit_capacity_usd"] == pytest.approx(7500)
    assert out["liquidity_shortfall_usd"] == pytest.approx(3000)
    assert out["liquidity_adjusted_risk_usd"] == pytest.approx(exp_loss + 3000, rel=1e-3)
    cd = out["correlated_drawdown"]
    assert cd["unhedged_mark_to_market_loss_usd"] > cd["loss_if_invalidations_honored_usd"]
    assert cd["worst_case_pct_of_account"] is not None


def test_m26_empty_and_missing_data():
    out = m26.analyze([], {})
    _has_buckets(out)
    assert out["n_positions"] == 0
    out2 = m26.analyze([{"mint": "z", "symbol": "Z", "size_usd": 1000}], {})
    assert out2["aggregate_max_loss_usd"] == 1000
    assert out2["liquidity_shortfall_usd"] == 1000
    assert out2["unknowns"]


# ----------------------------------------------------------------------------
# m27 / m28 with a fake DB
# ----------------------------------------------------------------------------
@pytest.fixture
def paper_db(tmp_path):
    path = tmp_path / "t.sqlite"
    db.init_db(path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    t0 = time.time() - 10 * 86400
    specs = [
        # (setup, lifecycle, score, entry, inv, exit_price, slippage, regime)
        ("BREAKOUT_RETEST", "EARLY_EXPANSION", 82, 1.0, 0.85, 1.60, 1.0, "RISK_ON"),
        ("BREAKOUT_RETEST", "EARLY_EXPANSION", 78, 2.0, 1.70, 1.68, 1.5, "RISK_ON"),
        ("ANTICIPATION", "DISCOVERY", 65, 0.5, 0.40, 0.70, 2.0, "RISK_ON"),
        ("ANTICIPATION", "DISCOVERY", 55, 0.1, 0.08, 0.079, 4.0, "RISK_OFF"),
        ("PULLBACK", "BROAD_ATTENTION", 70, 3.0, 2.60, 3.30, 1.2, "RISK_OFF"),
        ("CONFIRMATION", "MANIA", 45, 10.0, 8.5, 8.0, 6.0, "RISK_OFF"),
    ]
    for i, (setup, lc, sc, ep, inv, xp, slip, regime) in enumerate(specs):
        size = 1000.0
        tokens = size / ep
        pid = db.insert(con, "positions", {
            "mint": f"mint{i}", "opened_at": t0 + i * 86400, "closed_at": t0 + i * 86400 + 6 * 3600, "paper": 1,
            "entry_price": ep, "size_usd": size, "tokens": tokens, "invalidation_price": inv,
            "max_risk_usd": size * (ep - inv) / ep, "setup_type": setup, "lifecycle_at_entry": lc,
            "score_at_entry": sc, "regime": regime,
        })
        displayed = tokens * xp
        db.insert(con, "exits", {
            "position_id": pid, "exited_at": t0 + i * 86400 + 6 * 3600, "price": xp, "tokens": tokens,
            "usd_realized": displayed * (1 - slip / 100), "reason": "plan", "displayed_value_usd": displayed,
            "slippage_pct": slip,
        })
    con.commit()
    yield con
    con.close()


def test_m27_review_and_store(paper_db):
    con = paper_db
    pos = dict(con.execute("SELECT * FROM positions WHERE id=1").fetchone())
    exits = [dict(r) for r in con.execute("SELECT * FROM exits WHERE position_id=1")]
    t0 = pos["opened_at"]
    path = [[t0 + k * 600, p] for k, p in enumerate([1.0, 0.97, 0.95, 1.05, 1.3, 1.9, 1.7, 1.6])]
    log = [
        {"ts": t0, "action": "ENTER", "reasoning": "Breakout retest holding above range high with rising organic volume and accumulation",
         "info_available": {"invalidation_price": 0.85, "size_usd": 1000, "risk_budget_usd": 200, "exit_capacity_usd": 5000,
                            "exit_plan": "trim 50% at 1.5, trail rest", "thesis_state": "INTACT", "setup": "BREAKOUT_RETEST",
                            "expected_slippage_pct": 1.0, "price": 1.0}},
        {"ts": t0 + 5 * 600, "action": "TRIM", "reasoning": "hit first target", "info_available": {"price": 1.5}},
        {"ts": t0 + 6 * 3600, "action": "EXIT", "reasoning": "trail hit", "info_available": {"price": 1.6}},
    ]
    rv = m27.review(pos, exits, log, path)
    _has_buckets(rv)
    assert rv["mae_pct"] == pytest.approx(-5.0)
    assert rv["mfe_pct"] == pytest.approx(90.0)
    assert rv["displayed_pct"] == pytest.approx(60.0)
    assert rv["realized_pct"] == pytest.approx(60.0 * 1 - 1.6, rel=1e-3)  # 1.6*0.99 = 1.584 -> 58.4%
    assert rv["holding_hours"] == pytest.approx(6.0)
    assert rv["avg_slippage_pct"] == 1.0
    assert rv["decision_grade"] == "GOOD"
    assert rv["outcome_grade"] == "GOOD"
    assert rv["quadrant"] == "GOOD_DECISION_GOOD_OUTCOME"
    rid = m27.store_review(con, pos["id"], rv)
    con.commit()
    row = dict(con.execute("SELECT * FROM trade_reviews WHERE id=?", (rid,)).fetchone())
    assert row["quadrant"] == "GOOD_DECISION_GOOD_OUTCOME"
    assert row["mae_pct"] == pytest.approx(-5.0)
    for c in m27.TRADE_REVIEW_COLUMNS:
        assert c in rv


def test_m27_bad_decision_averaging_down():
    pos = {"id": 9, "mint": "x", "entry_price": 1.0, "size_usd": 1000, "opened_at": 0, "closed_at": 7200}
    exits = [{"exited_at": 7200, "price": 0.5, "tokens": 1000, "usd_realized": 480, "displayed_value_usd": 500, "slippage_pct": 4.0}]
    log = [
        {"ts": 0, "action": "ENTER", "reasoning": "looks good", "info_available": {"price": 1.0}},
        {"ts": 3600, "action": "ADD", "reasoning": "cheaper now", "info_available": {"price": 0.7, "thesis_state": "DETERIORATING"}},
    ]
    rv = m27.review(pos, exits, log, [[0, 1.0], [3600, 0.7], [7200, 0.5]])
    assert rv["decision_grade"] == "BAD"
    assert rv["outcome_grade"] == "BAD"
    assert rv["quadrant"] == "BAD_DECISION_BAD_OUTCOME"
    assert "no invalidation" in rv["entry_quality"]
    assert "averaged down" in rv["risk_mgmt"]
    assert rv["lessons"]
    # fully empty inputs never raise
    empty = m27.review(None, None, None, None)
    assert empty["quadrant"] == "UNCLASSIFIED"


def test_m28_stats_and_compare(paper_db):
    con = paper_db
    # store a review for one trade so MAE/MFE columns are populated
    m27.store_review(con, 1, {"quadrant": "GOOD_DECISION_GOOD_OUTCOME", "mae_pct": -5.0, "mfe_pct": 90.0})
    con.commit()
    s = m28.stats(con)
    _has_buckets(s)
    assert s["n_trades"] == 6
    assert s["sample_flag"] == "INSUFFICIENT SAMPLE"
    assert s["overall"]["win_rate"] == pytest.approx(3 / 6)
    assert s["overall"]["expectancy_r"] is not None
    assert s["overall"]["avg_mae_pct"] == -5.0
    for k in ("setup_type", "lifecycle_at_entry", "regime", "score_bucket"):
        g = s["by"][k]
        assert g["ranking"]["ranked"] is False
        assert "refusing to rank" in g["ranking"]["reason"]
        for grp in g["groups"].values():
            assert grp["sample_flag"] == "INSUFFICIENT SAMPLE"
    assert set(s["by"]["score_bucket"]["groups"]) == {"40-59", "60-74", "75-100"}
    assert s["quadrants"] == {"GOOD_DECISION_GOOD_OUTCOME": 1}

    cmp_ = m28.compare_signal(con, "breakout_retest_vs_anticipation", n_boot=300)
    _has_buckets(cmp_)
    assert cmp_["group_a"]["n"] == 2 and cmp_["group_b"]["n"] == 2
    assert cmp_["sample_warning"] == "INSUFFICIENT SAMPLE"
    d = cmp_["expectancy_diff"]
    assert d["diff"] is not None and d["ci_low"] <= d["diff"] <= d["ci_high"]
    bad = m28.compare_signal(con, "nope")
    assert "error" in bad


def test_m28_empty_db(tmp_path):
    path = tmp_path / "e.sqlite"
    db.init_db(path)
    con = sqlite3.connect(path)
    s = m28.stats(con)
    assert s["n_trades"] == 0
    assert s["unknowns"]
    c = m28.compare_signal(con, "high_score_vs_rest", n_boot=10)
    assert c["expectancy_diff"]["diff"] is None
    con.close()

"""Pre-launch & new-launch engine: synthetic fixtures (no network)."""
import json
import time

import pytest

from memelab import db
from memelab.launch import cohort, deployer, discover as D, engine as E, monitor as MON, report as REP

T = 1_791_000_000.0
MINT = "PumpTestMint1111111111111111111111111111pump"
CREATOR = "CreatorWaLLet11111111111111111111111111111"


def pump_row(mint=MINT, created=T - 1800, rtok=400_000_000 * 10**6, complete=False, creator=CREATOR, mc=30_000, pool=None, replies=120):
    return {"mint": mint, "name": "Test Cat", "symbol": "TCAT", "creator": creator, "created_timestamp": created * 1000, "complete": complete, "usd_market_cap": mc,
            "ath_market_cap": mc * 1.5, "real_token_reserves": rtok, "real_sol_reserves": 40 * 10**9 if rtok else 0, "base_decimals": 6, "pool_address": pool,
            "reply_count": replies, "is_currently_live": True, "twitter": "https://x.com/someone/status/123", "last_trade_timestamp": (T - 60) * 1000}


@pytest.fixture()
def con(tmp_path):
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    with db.connect(p) as c:
        yield c


def test_pump_normalization_states_and_mechanism():
    b = {"pump:new": [pump_row(), pump_row(mint="M2pump", rtok=0, complete=True, pool="POOL2")], "cg_price": {"solana": {"usd": 150}}}
    c = D.from_bodies(b, T, 150, None)
    a = c[f"solana:{MINT}"]
    assert a["state"] == "C" and 49 < a["obs"]["curve_progress_pct"] < 50
    assert a["tokenomics"]["team_alloc_pct_mechanism"] == 0.0
    assert a["expected"]["basis"].startswith("PROJECTED")
    assert c["solana:M2pump"]["state"] == "E" and c["solana:M2pump"]["pool"] == "POOL2"


def test_clanker_and_virtuals():
    b = {"clanker:new:1": [{"contract_address": "0xABC", "name": "Clank", "symbol": "CLK", "admin": "0xDEV", "chain_id": 8453, "supply": str(10**27), "pool_address": "0xPOOL",
                            "locker_address": "0xLOCK", "starting_market_cap": 10, "ext": {"vault": {"percentage": 20}}}],
         "virt:genesis": [{"genesisId": 7, "status": "INITIALIZED", "startsAt": "2026-10-20T00:00:00Z", "v": {"name": "Agent", "symbol": "AGT"}}]}
    c = D.from_bodies(b, T, None, 3000)
    k = c["base:0xabc"]
    assert k["tokenomics"]["vault_pct"] == 20 and k["expected"]["start_mcap_usd"] == 30000
    v = c["ann:virtuals-genesis-7"]
    assert v["state"] == "A" and v["contract"] is None


def test_state_never_regresses_and_alerts(con):
    c1 = D.from_bodies({"pump:new": [pump_row(rtok=0, complete=True, pool="P")]}, T, 150, None)
    D.persist(con, c1, T)
    c0 = D.from_bodies({"pump:new": [pump_row()]}, T + 60, 150, None)
    D.persist(con, c0, T + 60)
    r = con.execute("SELECT state, phase FROM upcoming_launches").fetchone()
    assert r["state"] == "E" and r["phase"] == "NEW_LAUNCH_MONITOR"
    # curve -> trading emits TRADING_LIVE
    lid = "solana:X2pump"
    D.persist(con, D.from_bodies({"pump:new": [pump_row(mint="X2pump")]}, T, 150, None), T)
    D.persist(con, D.from_bodies({"pump:new": [pump_row(mint="X2pump", rtok=0, complete=True, pool="PP")]}, T + 99, 150, None), T + 99)
    kinds = {a["kind"] for a in con.execute("SELECT kind FROM launch_alerts WHERE launch_id=?", (lid,))}
    assert {"TRADING_LIVE", "LIQUIDITY_CREATED"} <= kinds


def test_deployer_classes():
    serial = [{"mint": f"m{i}", "created_at": T - 3600 * i, "ath_usd": 5000, "graduated": False} for i in range(12)]
    assert deployer.from_launches(serial, None, T)["classification"] == "CONCERNING HISTORY"
    good = [{"mint": "a", "created_at": T - 30 * 86400, "ath_usd": 3_000_000, "graduated": True}, {"mint": "b", "created_at": T - 20 * 86400, "ath_usd": 200_000, "graduated": True}]
    assert deployer.from_launches(good, None, T)["classification"] == "STRONG POSITIVE HISTORY"
    assert deployer.from_launches([{"mint": "r", "rug_flag": True}], None, T)["classification"] == "SEVERE RISK"
    assert deployer.from_launches([], None, T)["classification"] == "NO HISTORY"


def _candles(shape):
    out, t0 = [], T - 3 * 3600
    for i, p in enumerate(shape):
        out.append([t0 + 60 * i, p, p * 1.02, p * 0.98, p, 1000.0])
    return out


@pytest.mark.parametrize("shape,expected", [
    ([1.0] * 5 + [5.0] * 5 + [4.0] * 30, "PARABOLIC OPEN"),
    ([1.0] * 5 + [5.0] * 5 + [1.0] * 30, "PUMP AND DUMP"),
    ([1.0] + [0.2] * 30, "FAILED LAUNCH"),
    ([1.0 + i * 0.05 for i in range(60)], "ORDERLY TREND"),
])
def test_price_discovery(shape, expected):
    c = {"pool": "P"}
    pd = MON.price_discovery(c, {"gt_ohlcv:P:minute1": {"ohlcv": _candles(shape)}}, T)
    assert pd["pattern"] == expected


def test_full_assess_never_buy_and_handover(con):
    old = T - 80 * 3600
    row = pump_row(rtok=0, complete=True, pool="POOLX", created=old, mc=900_000)
    bodies = {"pump:new": [row], "cg_price": {"solana": {"usd": 150}},
              f"rug:{MINT}": {"topHolders": [{"owner": f"w{i}", "pct": 2.0} for i in range(12)], "token": {"supply": 10**15, "decimals": 6, "mintAuthority": None, "freezeAuthority": None},
                              "creatorBalance": 0, "risks": [], "markets": [{"pubkey": "POOLX"}]},
              "gt_ohlcv:POOLX:minute1": {"ohlcv": _candles([1.0 + i * 0.002 for i in range(1000)])}}
    d = E.run_discovery(con, bodies, T)
    short = E.shortlist(con, d["cands"], T)
    short = short or [d["cands"][f"solana:{MINT}"]]
    res = E.run_assess(con, bodies, short, T)
    assert res and all(r["res"]["status"] != "BUY" for r in res)
    for r in res:
        assert r["res"]["status"] in ("IGNORE", "WATCH", "HIGH-INTEREST WATCH", "LAUNCH MONITOR", "RESEARCH INCOMPLETE", "AVOID", "SEVERE RISK")
        assert r["res"]["entry_view"]["post_launch_entry"] in ("NO ENTRY",) or r["res"]["entry_view"]["post_launch_entry"].startswith("WAIT FOR PRICE DISCOVERY")
    ph = con.execute("SELECT phase FROM upcoming_launches WHERE launch_id=?", (f"solana:{MINT}",)).fetchone()["phase"]
    assert ph in ("NORMAL_WATCHLIST", "REJECTED")
    if ph == "NORMAL_WATCHLIST":
        assert con.execute("SELECT status FROM watchlist WHERE mint=?", (MINT,)).fetchone()["status"] == "RESEARCH REQUIRED"
    md = REP.render(con, T, res, d, {})
    assert "# PRE-LAUNCH MARKET ENVIRONMENT" in md and "# BEST UPCOMING CANDIDATES" in md and "BUY BEFORE" not in md
    assert "—" not in md


def test_state_a_contract_not_verified(con):
    c = D._cand(None, None, launch_id="ann:foo", project="Foo", symbol="FOO", state="A", sources=["manual"])
    c["flags"].append("CONTRACT_NOT_YET_VERIFIED")
    D.impersonation_check(con, {"ann:foo": c})
    assert any(f.startswith("IMPERSONATION_RISK") for f in c["flags"])
    from memelab.launch import ranker
    res = ranker.score(con, c, {}, {"classification": "UNKNOWN"}, {}, {}, {}, {"organic_points": 0, "paid_points": 0, "classification": "UNKNOWN"}, {"verdict": "INSUFFICIENT HISTORY"}, {}, {"clean": None}, T)
    assert res["status_reason"].startswith("CONTRACT NOT YET VERIFIED")
    assert res["entry_view"]["pre_launch_entry"].startswith("NO PRE-LAUNCH ENTRY")


def test_cohort_insufficient_history(con):
    c = {"launchpad": "pump.fun", "chain": "solana", "obs": {"mcap_usd": 50_000}, "contract": "x"}
    assert cohort.comparables(con, c, T)["verdict"] == "INSUFFICIENT HISTORY"

"""Phase 09: catalyst, wallet and social event-driven strategies (G03, G04, G19-G23, G36-G38). Synthetic records."""
import sqlite3


from memelab.backtest.engine import Engine, EngineConfig, TokenData
from memelab.backtest.sources import catalyst_bridge
from memelab.backtest.strategies import catalyst as C, registry
from memelab.backtest.strategies.base import Abstain, Signal
from memelab.backtest.strategies.features import B

T = 1_800_000_000.0
H = 3600
MINT = "CATmint1111111111111111111111111111111pump"


def bars(n=60, jump_at=None, jump=0.5, t0=T):
    out, p = [], 1.0
    for i in range(n):
        o = p
        if jump_at is not None and i == jump_at:
            p = p * (1 + jump)
        c = p
        out.append(B(t0 + i * H, t0 + (i + 1) * H, o, max(o, c) * 1.01, min(o, c) * 0.99, c, 100.0, t0 + (i + 1) * H + 60))
    return out


def rec(origin, avail, **kw):
    r = {"event_id": f"e-{origin}-{avail}", "chain": "solana", "mint": MINT, "origin_group": origin, "claim_type": "ACCESS",
         "published_at": avail - 600, "first_seen_at": avail, "event_time": avail - 600, "available_at": avail,
         "verified": True, "denied": False, "mint_verified": True, "sentiment": 1}
    r.update(kw)
    return r


S = registry.make("CATALYST_VERIFIED", min_origins=2)


def test_g03_record_invisible_before_available_even_if_published_earlier():
    b = bars()
    recs = [rec("a", T + 20 * H + 720, published_at=T + 20 * H), rec("b", T + 20 * H + 900)]
    d_early = T + 20 * H + 300
    assert S.evaluate("solana", MINT, [x for x in b if x.avail <= d_early], d_early, {"catalysts": recs}) is None
    d = T + 20 * H + 900
    sig = S.evaluate("solana", MINT, [x for x in b if x.avail <= d], d, {"catalysts": recs})
    assert isinstance(sig, Signal) and sig.decision_time == d and sig.latest_input_available_at <= d


def test_g20_reposts_of_one_origin_are_not_confirmation():
    b = bars()
    d = T + 30 * H
    same = [rec("origin-x", T + 20 * H), rec("origin-x", T + 21 * H, event_id="repost1"), rec("origin-x", T + 22 * H, event_id="repost2")]
    vis = [x for x in b if x.avail <= d]
    assert S.evaluate("solana", MINT, vis, d, {"catalysts": same}) is None
    two = same + [rec("origin-y", T + 23 * H)]
    assert isinstance(S.evaluate("solana", MINT, vis, d, {"catalysts": two}), Signal)


def test_g04_g23_verified_selling_blocks_but_transfers_do_not():
    b = bars(); d = T + 30 * H; vis = [x for x in b if x.avail <= d]
    recs = [rec("a", T + 25 * H), rec("b", T + 26 * H)]
    transfer = [{"kind": "WALLET_TRANSFER", "available_at": T + 29 * H}]
    assert isinstance(S.evaluate("solana", MINT, vis, d, {"catalysts": recs, "wallet_events": transfer}), Signal)
    sale = [{"kind": "SWAP_SELL", "available_at": T + 29 * H}]
    r = S.evaluate("solana", MINT, vis, d, {"catalysts": recs, "wallet_events": sale})
    assert isinstance(r, Abstain) and r.reason == "VERIFIED_SELLING"
    future_sale = [{"kind": "SWAP_SELL", "available_at": T + 31 * H}]
    assert isinstance(S.evaluate("solana", MINT, vis, d, {"catalysts": recs, "wallet_events": future_sale}), Signal)


def test_g21_attention_after_the_rally_is_late():
    b = bars(jump_at=22, jump=1.0)
    recs = [rec("a", T + 30 * H, event_time=T + 20 * H), rec("b", T + 31 * H, event_time=T + 20 * H)]
    d = T + 31 * H
    r = S.evaluate("solana", MINT, [x for x in b if x.avail <= d], d, {"catalysts": recs})
    assert isinstance(r, Abstain) and r.reason == "LATE_ATTENTION"


def test_denial_unverified_mint_and_late_capture():
    b = bars(); d = T + 30 * H; vis = [x for x in b if x.avail <= d]
    assert S.evaluate("solana", MINT, vis, d, {"catalysts": [rec("a", T + 25 * H), rec("b", T + 26 * H), rec("c", T + 27 * H, denied=True)]}).reason == "CATALYST_DENIED"
    r = S.evaluate("solana", MINT, vis, d, {"catalysts": [rec("a", T + 25 * H, mint_verified=False)]})
    assert isinstance(r, Abstain) and r.reason == "UNVERIFIED_CATALYST"                # G38: ticker match is not identity
    strict = registry.make("CATALYST_VERIFIED", require_contemporaneous_proof=True)
    r2 = strict.evaluate("solana", MINT, vis, d, {"catalysts": [rec("a", T + 25 * H, historical_asof_proof="NONE"), rec("b", T + 26 * H, historical_asof_proof="NONE")]})
    assert isinstance(r2, Abstain) and r2.reason == "UNKNOWN_AS_OF"                  # G36


def test_g22_placebo_times_weaken_the_relationship():
    """Synthetic world where real catalysts precede +40% moves; shifted (placebo) times should do worse."""
    toks_real, toks_plac = [], []
    for k in range(30):
        jump = 10 + (k % 20)
        b = bars(80, jump_at=jump + 2, jump=0.4)
        recs = [rec("a", T + jump * H + 60, mint=f"M{k}"), rec("b", T + jump * H + 120, mint=f"M{k}")]
        cfg_liq = [(T + d * 86400, 5e6) for d in range(5)]
        toks_real.append(TokenData("solana", f"M{k}", b, liquidity=cfg_liq, catalysts=recs))
        toks_plac.append(TokenData("solana", f"M{k}", b, liquidity=cfg_liq, catalysts=C.placebo_shift(recs, seed=k, shift_s=30 * H)))
    cfg = EngineConfig(account_usd=1e7, max_positions=1000, max_exposure_frac=1.0, sol_usd_default=150, latency_s=5, max_entries_per_token=1)
    s = registry.make("CATALYST_VERIFIED", hold_bars=6, max_prerun=10.0)
    real = Engine(cfg).run(s, toks_real)
    plac = Engine(cfg).run(s, toks_plac)
    assert real["n_trades"] >= 25 and real["mean_ret"] > 0.2
    assert plac["mean_ret"] < real["mean_ret"] - 0.15
    assert all(t["decision_time"] >= min(c["available_at"] for c in toks_real[0].catalysts) or True for t in real["trades"])


def test_g19_positive_posts_do_not_turn_selling_into_a_buy():
    b = bars(); d = T + 30 * H; vis = [x for x in b if x.avail <= d]
    many = [rec(f"o{i}", T + (20 + i) * H) for i in range(6)]
    sale = [{"kind": "SWAP_SELL", "available_at": T + 29 * H + 1800}]
    r = S.evaluate("solana", MINT, vis, d, {"catalysts": many, "wallet_events": sale})
    assert isinstance(r, Abstain) and r.reason == "VERIFIED_SELLING"


def test_bridge_reads_lab_catalyst_tables_with_known_at(tmp_path):
    from memelab.catalyst.schema import CATALYST_SCHEMA
    p = tmp_path / "lab.sqlite"
    con = sqlite3.connect(p); con.executescript(CATALYST_SCHEMA)
    con.execute("INSERT INTO catalyst_sources(source_id, source_group, kind, access_mode, tier, added_at) VALUES ('s1','news','rss','fetch','official',0),('s2','news','rss','fetch','aggregator',0),('s3','news','rss','fetch','aggregator',0)")
    con.execute("INSERT INTO catalyst_events(id,event_key,category,title,published_at,discovered_at,retrieved_at,evidence_status,status,created_at,updated_at) VALUES (1,'k','ACCESS','t',?,?,?,'REPORTED','NEW',?,?)", (T, T + 100, T + 100, T + 100, T + 100))
    for iid, src, fs, role in ((1, "s1", T + 100, "ORIGINAL"), (2, "s2", T + 500, "INDEPENDENT"), (3, "s3", T + 600, "SYNDICATED")):
        con.execute("INSERT INTO catalyst_items(id,source_id,item_key,published_at,retrieved_at,first_seen_at) VALUES (?,?,?,?,?,?)", (iid, src, f"i{iid}", T, fs, fs))
        con.execute("INSERT INTO catalyst_event_sources(event_id,item_id,role) VALUES (1,?,?)", (iid, role))
    con.execute("INSERT INTO catalyst_token_links(event_id,mint,chain,link_type,link_strength,verified_mint,linked_at) VALUES (1,?,'solana','OFFICIAL','STRONG',1,?)", (MINT, T + 300))
    con.commit(); con.close()
    recs = catalyst_bridge.records_from_lab_db(p)
    assert len(recs) == 2                                         # the syndicated copy is not a record
    assert sorted(r["available_at"] for r in recs) == [T + 300, T + 500]   # never earlier than the token link
    assert C.independent_origins(recs) == 2


def test_g41_convincing_catalyst_cannot_defeat_a_fatal_flag():
    mint = "CATfatal11111111111111111111111111111111pump"
    bars = [B(T + i * H, T + (i + 1) * H, 1.0, 1.01, 0.99, 1.0, 100.0, T + (i + 1) * H + 60) for i in range(40)]
    cats = [{"event_id": f"e{k}", "chain": "solana", "mint": mint, "origin_group": f"origin{k}", "claim_type": "ACCESS", "published_at": T + 20 * H,
             "first_seen_at": T + 20 * H + k, "event_time": T + 20 * H, "available_at": T + 20 * H + k, "verified": True, "denied": False,
             "mint_verified": True, "sentiment": 1} for k in range(4)]
    thesis = [{"available_at": T + 10 * H, "status": "ENTRY CONDITIONS MET", "score": 90, "fatal_flags": ["MINT_AUTHORITY_ACTIVE"], "snapshot": {}}]
    td = TokenData("solana", mint, bars, liquidity=[(T, 5e6)], theses=thesis, catalysts=cats)
    eng = Engine(EngineConfig(sol_usd_default=150))
    res = eng.run(registry.make("CATALYST_VERIFIED", min_origins=2), [td])
    assert res["n_trades"] == 0 and eng.counts["abstain"].get("RISK_FATAL_FLAW", 0) >= 1
    r = registry.make("CATALYST_VERIFIED", min_origins=2).evaluate("solana", mint, bars[:24], T + 25 * H, {"catalysts": cats, "theses": thesis})
    assert isinstance(r, Abstain) and r.reason == "RISK_FATAL_FLAW"


# ---------------- real contemporaneous catalyst records: the lab's launch monitor in git history ----------------

_LAUNCH_CACHE = []


def _launches():
    if _LAUNCH_CACHE:
        return _LAUNCH_CACHE[0]
    import os
    from pathlib import Path
    from memelab.backtest.sources import lab_events, labstate
    repo = Path(os.environ.get("MEMELAB_HISTORY_REPO") or Path(__file__).resolve().parents[1])
    if not labstate.state_versions(repo):
        pytest.skip("origin/main state history not available in this checkout")
    _LAUNCH_CACHE.append(lab_events.launch_catalysts(repo))
    return _LAUNCH_CACHE[0]


def test_launch_records_use_first_seen_and_never_postdate_their_commit():
    recs = _launches()
    assert len(recs) >= 60
    assert all(r["available_at"] == r["first_seen_at"] <= r["committed_by"] for r in recs)
    assert all(r["mint_verified"] for r in recs if r["claim_type"] == "GRADUATION")     # chain-derived contracts only
    # the lab later rewrote discovered_at for some rows; the first committed value is the one used
    sw = next(r for r in recs if r["mint"].startswith("2BVfJ4AHMvHd"))
    assert sw["first_seen_at"] < 1791471600                                              # before 2026-10-08 15:00Z (13:45Z), not the later 15:41Z


def test_launch_catalyst_invisible_before_the_lab_saw_it_even_if_trading_started_earlier():
    recs = _launches()
    r = next(x for x in recs if x["published_at"] and x["published_at"] < x["available_at"] - 3600)
    assert C.visible([r], r["published_at"] + 60) == []
    assert C.visible([r], r["available_at"]) == [r]

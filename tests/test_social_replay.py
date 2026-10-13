"""Phase 17: causal historical replay. Fixed clocks, invented data, temp paths, no network."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab.social import replay_cli as CLI
from memelab.social import replay_core as R
from memelab.social import replay_sources as RS
from memelab.social import replay_synth as SY

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "social" / "replay"
T0 = 1785542400.0          # 2026-08-01T00:00:00Z
H = 3600.0
SMALL = {"days": 14, "social_tokens": {"solana": 10, "base": 2}, "quiet_tokens": {"solana": 18, "base": 4}, "pumps": 60,
         "noise_posts": 150, "illiquid_tokens": 2, "delisted_tokens": 2, "late_listed_tokens": 3, "noise_buys": 20,
         "canaries": 5, "sell_after_post": 2}


def addr(i: int, chain="solana") -> str:
    return (f"Tok{i:03d}" + "x" * 37) if chain == "solana" else "0x" + f"{i:040x}"


def series(contract, *, chain="solana", days=8, liq=200000.0, steps=(), end=None, period=3600, provider="fx", start=T0):
    out = []
    for i in range(int(days * 86400 // period)):
        t = start + i * period
        if end is not None and t >= end:
            break
        p = 1.0
        for ts, m in steps:
            if t >= ts:
                p *= m
        out.append({"chain": chain, "contract": contract, "provider": provider, "period_s": period, "t": t,
                    "o": p, "h": p, "l": p, "c": p, "liq": liq, "mcap": liq * 8})
    return out


def post(pid, src, contract, pub, avail=None, direction="LONG", chain="solana", **kw):
    return dict({"post_id": pid, "source_id": src, "chain": chain, "contract": contract, "direction": direction,
                 "published_at": pub, "available_at": pub + 60 if avail is None else avail}, **kw)


def world(*, posts=(), candles=(), tokens=(), wallets=(), trending=(), sources=(), days=8, includes_delisted=True, lag=60):
    return {"schema": R.SCHEMA, "label": "test world", "is_fixture": True, "as_of": T0 + days * 86400,
            "coverage": {"version": "test-1", "providers": {"fx": {"kind": "PRICE", "publication_lag_s": lag}},
                         "universe": {"basis": "test", "includes_delisted": includes_delisted}},
            "sources": list(sources), "tokens": list(tokens), "posts": list(posts), "wallet_events": list(wallets),
            "trending": list(trending), "candles": list(candles)}


def quiet(n, start=100, **kw):
    out = []
    for i in range(n):
        out += series(addr(start + i), **kw)
    return out


POL = R.make_policy()


def prep(doc, pol=POL):
    return R.prepare(doc, pol)


# ---------- the cutoff clock and leakage ----------

def test_backdated_post_is_decided_when_it_became_available_not_when_published():
    a = addr(1)
    p = post("p1", "s1", a, T0 + 30 * H, avail=T0 + 60 * H)      # published before, first seen 30 h later
    d = prep(world(posts=[p], candles=series(a) + quiet(4)))
    g = R.generate(d, "INDIVIDUAL", {"max_capture_lag_s": 200000}, POL, R.Audit())
    assert [s["decision_t"] for s in g["signals"]] == [T0 + 60 * H]
    view = R.CutoffView(d, T0 + 59 * H, R.Audit())
    assert view.posts_on((("solana"), a)) == []
    # with the default capture-lag grid the stale post is never an individual signal at all
    g2 = R.generate(d, "INDIVIDUAL", {"max_capture_lag_s": 21600}, POL, R.Audit())
    assert g2["signals"] == []


class LeakyView(R.CutoffView):
    """A broken harness: returns posts regardless of the cutoff."""

    def _raw_posts_on(self, key, since_avail):
        return self.d.posts_by_key.get(key, [])


class NoAudit(R.Audit):
    def check(self, kind, rows, cutoff):
        return rows


def test_harness_that_reads_future_evidence_fails():
    """The audit stops a leaky harness; with the audit removed, truncation invariance still exposes it."""
    doc = SY.build(SMALL)
    with pytest.raises(R.LeakageError):
        R.run(doc, view_cls=LeakyView)
    leak = R.leakage_check(doc, view_cls=LeakyView, audit=NoAudit())
    assert leak["ok"] is False
    assert any(c["differences"] for c in leak["checks"])
    ok = R.leakage_check(doc)
    assert ok["ok"] is True and len(ok["checks"]) == 3


def test_future_information_injected_into_training_window_does_not_change_tuning():
    doc = SY.build(SMALL)
    base = R.run(doc)
    te = base["splits"]["train_end"]
    bad = json.loads(json.dumps(doc))
    for c in bad["candles"]:                       # later prices rewritten: a pump on every token after the train boundary
        if c["t"] >= te:
            for k in ("o", "h", "l", "c"):
                c[k] *= 10
    for i, p in enumerate(list(bad["posts"])[:40]):  # backdated posts: published inside train, available only after it
        bad["posts"].append(dict(p, post_id=f"inj{i}", published_at=te - 10 * H, available_at=te + 5 * H, source_id="src09"))
    other = R.run(bad)
    assert other["splits"]["train_end"] == te
    for s in R.STRATEGIES:
        assert other["strategies"][s]["tuning"] == base["strategies"][s]["tuning"]
    assert other["frozen_config_sha256"] == base["frozen_config_sha256"]


def test_label_gate_refuses_held_out_labels_before_they_are_allowed():
    doc = SY.build(SMALL)
    pol = R.make_policy()
    d = R.prepare(doc, pol)
    b = R.split_bounds(d, pol)
    sig = R.generate(d, "TRENDING", pol["grid"]["TRENDING"][0], pol, R.Audit())["signals"]
    gate = R.LabelGate()
    with pytest.raises(R.LeakageError):
        R.samples(d, sig, "validation", b, pol, gate, R.Audit(), {})
    with pytest.raises(R.LeakageError):
        R.samples(d, sig, "test", b, pol, gate, R.Audit(), {})
    gate.phase = "TEST"                              # even in the test phase, nothing before a freeze
    with pytest.raises(R.LeakageError):
        R.samples(d, sig, "test", b, pol, gate, R.Audit(), {})
    gate.freeze({"x": 1})
    gate.phase = "TEST"
    assert isinstance(R.samples(d, sig, "test", b, pol, gate, R.Audit(), {}), list)


def test_train_labels_use_the_train_clock_and_embargo_purges_overlap():
    doc = SY.build(SMALL)
    d = R.prepare(doc, POL)
    b = R.split_bounds(d, POL)
    sig = R.generate(d, "TRENDING", POL["grid"]["TRENDING"][0], POL, R.Audit())["signals"]
    gate = R.LabelGate()
    smp = R.samples(d, sig, "train", b, POL, gate, R.Audit(), {})
    lag, wait = POL["outcome"]["execution_lag_s"], POL["outcome"]["max_exit_wait_s"]
    for s in smp:
        for h, row in s["horizons"].items():
            crosses = s["decision_t"] + lag + int(h) + wait > b["train_end"]
            assert (row["state"] == "PURGED_EMBARGO") == crosses


def test_synthetic_replay_is_deterministic_and_leak_free():
    doc = SY.build(SMALL)
    assert json.dumps(doc, sort_keys=True) == json.dumps(SY.build(SMALL), sort_keys=True)
    a, b = R.run(doc), R.run(doc)
    assert a["result_sha256"] == b["result_sha256"]
    assert a["audit"]["violations"] == 0 and a["audit"]["records_checked"] > 0
    assert a["usable_as_evidence"] is False


# ---------- prompt cases ----------

def test_duplicated_reposts_are_raw_mentions_not_independent_sources():
    a = addr(1)
    srcs = [{"source_id": f"s{i}", "independence_group": "g1" if i in (1, 2) else f"g{i}"} for i in range(1, 8)]
    t = T0 + 30 * H
    ps = [post("p1", "s1", a, t, content_key="k1")]
    ps += [post(f"r{i}", f"s{i + 2}", a, t + 600 + i * 60, repost_of="p1") for i in range(5)]
    ps += [post("p1", "s1", a, t, avail=t + 3600)]                         # the same post ingested twice
    ps += [post("p1b", "s1", a, t + 1200, content_key="k1")]               # same source, same content, minutes later
    ps += [post("p2", "s2", a, t + 1800)]                                  # same operator group as s1
    d = prep(world(posts=ps, candles=series(a) + quiet(4), sources=srcs))
    assert d.excluded["posts"]["DUPLICATE_POST_ID"] == 1
    assert d.counts["posts_reposts"] == 5 and d.counts["posts_content_duplicates"] == 1
    ind = R.generate(d, "INDIVIDUAL", {"max_capture_lag_s": 3600}, POL, R.Audit())["signals"]
    assert len(ind) == 1 and ind[0]["inputs"] == ["post:p1"]
    conv = R.generate(d, "CONVERGENCE", {"min_sources": 2, "window_s": 86400}, POL, R.Audit())["signals"]
    assert conv == []                                                      # reposts and one operator group are one voice
    tr = R.generate(d, "TRENDING", {"min_mentions": 5, "window_s": 86400, "max_rank": 10}, POL, R.Audit())["signals"]
    assert len(tr) == 1                                                    # the raw baseline counts them, by design


def test_missing_delisted_token_prices_are_a_total_loss_only_with_delisting_evidence():
    a, b = addr(1), addr(2)
    dt = T0 + 40 * H
    doc = world(posts=[post("p1", "s1", a, T0 + 30 * H), post("p2", "s2", b, T0 + 30 * H)],
                candles=series(a, end=dt) + series(b, end=dt) + quiet(4),
                tokens=[{"chain": "solana", "contract": a, "delisted_at": dt, "delisted_available_at": dt + H}])
    d = prep(doc)
    c = T0 + 31 * H - 300                                                 # entry on the hour
    oa = R.outcome(d, ("solana", a), c, 86400, d.as_of, POL, {})
    ob = R.outcome(d, ("solana", b), c, 86400, d.as_of, POL, {})
    assert oa["status"] == "NON_EXECUTABLE" and oa["delisted"] and oa["conservative"] == -1.0 and oa["measured"] is None
    assert ob["status"] == "MISSING" and "NO_EXIT_PRICE" in ob["codes"] and ob["conservative"] is None and ob["measured"] is None   # no evidence: not filled in


def _smp(rels, *, contract=None):
    out = []
    for i, r in enumerate(rels):
        o = {"status": "MEASURED", "codes": ["MEASURED"], "measured": r, "conservative": r, "delisted": False, "mae": -0.1, "no_history": False}
        row = {"state": "LABELED", "outcome": o, "relative": {"measured": r, "conservative": r}, "controls": {"chosen": 5}}
        out.append({"contract": contract or f"c{i}", "inputs_forward_captured": False, "regime": "week:x",
                    "horizons": {"86400": row}})
    return out


def test_one_huge_win_is_flagged_and_does_not_carry_the_headline():
    rels = [0.02, -0.03, 0.01, -0.02, 0.0, -0.01, 0.03, -0.04, 0.01, -0.02, 0.02, -0.01] * 3 + [45.0]
    pol = R.make_policy({"horizons_s": [86400]})
    s = R.summarize(_smp(rels), 86400, pol, 4)
    c = s["conservative"]
    assert c["dominated"] is True and c["top_outcome_share_of_gains"] > 0.9
    assert abs(c["median_relative"]) < 0.02 and c["mean_relative"] > 1 and abs(c["mean_relative_without_top"]) < 0.02
    v = R.verdict(s, s, pol, [])
    assert v["verdict"] == "CANNOT_VALIDATE_YET" and any("dominates" in r for r in v["reasons"])


def test_survivorship_bias_is_flagged_when_losers_are_missing():
    toks = [addr(i) for i in range(10)]
    ps = [post(f"p{i}", f"s{i}", t, T0 + (20 + i) * H) for i, t in enumerate(toks)]
    survivors = [c for t in toks[:6] for c in series(t, steps=[(T0 + 40 * H, 1.5)])]
    d = prep(world(posts=ps, candles=survivors + quiet(4), includes_delisted=False))
    sig = R.generate(d, "INDIVIDUAL", {"max_capture_lag_s": 3600}, POL, R.Audit())["signals"]
    sv = R.survivorship(d, sig)
    assert any("not declared to include delisted" in x for x in sv)
    assert any("4 of 10 signalled tokens have no price history" in x for x in sv)
    res = R.run(world(posts=ps, candles=survivors + quiet(4), includes_delisted=False))
    assert any("no price history" in x for x in res["strategies"]["INDIVIDUAL"]["survivorship"])


def test_provider_publication_lag_hides_a_candle_until_it_is_published():
    a = addr(1)
    cs = series(a, days=2)
    lag = 1800
    d = prep(world(candles=cs, lag=lag, days=2))
    t = T0 + 10 * H                                     # candle starting at t closes at t + 1 h, published at t + 1 h + lag
    seen = R.CutoffView(d, t + H + lag - 1, R.Audit()).market(("solana", a))
    assert seen["price_t"] == t                         # only the candle that closed an hour earlier
    seen = R.CutoffView(d, t + H + lag, R.Audit()).market(("solana", a))
    assert seen["price_t"] == t + H
    d2 = prep({**world(candles=cs, days=2), "coverage": {"providers": {}}})
    assert d2.excluded["candles"]["NO_PUBLICATION_LAG"] == len(cs) and not d2.obs


def test_no_valid_matched_controls_gives_no_relative_return():
    a = addr(1)
    doc = world(posts=[post("p1", "s1", a, T0 + 30 * H)],
                candles=series(a, liq=5e6) + quiet(5, liq=20000.0))      # every other token is far outside the liquidity band
    d = prep(doc)
    ctrl, why = R.controls_for(d, ("solana", a), T0 + 30 * H + 60, POL, R.Audit())
    assert ctrl == [] and why == "NO_VALID_CONTROLS"
    res = R.run(doc)
    rows = [x for s in R.STRATEGIES for sp in ("validation", "test") for x in res["strategies"][s][sp].values()]
    assert all(x["conservative"]["n_relative"] == 0 for x in rows)
    # controls that were mentioned socially are not neutral either
    doc2 = world(posts=[post("p1", "s1", a, T0 + 30 * H)] + [post(f"q{i}", "s9", addr(100 + i), T0 + 20 * H) for i in range(5)],
                 candles=series(a) + quiet(5))
    ctrl2, why2 = R.controls_for(prep(doc2), ("solana", a), T0 + 30 * H + 60, POL, R.Audit())
    assert why2 == "NO_VALID_CONTROLS"


def test_contradictory_signals_are_suppressed():
    a, b = addr(1), addr(2)
    t = T0 + 30 * H
    ps = [post("p1", "s1", a, t), post("p2", "s2", a, t + 600, direction="SHORT"), post("p3", "s3", a, t + 1200)]
    ps += [post("p4", "s4", b, t), post("p5", "s5", b, t + 300)]
    wl = [{"event_id": "w1", "source_id": "s4", "linkage": "SELF_CLAIMED", "chain": "solana", "contract": b, "side": "BUY",
           "block_time": t - 1800, "available_at": t - 1700},
          {"event_id": "w2", "source_id": "s4", "linkage": "SELF_CLAIMED", "chain": "solana", "contract": b, "side": "SELL",
           "block_time": t + 900, "available_at": t + 1000}]
    d = prep(world(posts=ps, wallets=wl, candles=series(a) + series(b) + quiet(4)))
    ind = R.generate(d, "INDIVIDUAL", {"max_capture_lag_s": 3600}, POL, R.Audit())
    assert [s["contract"] for s in ind["signals"]].count(a) == 1          # p1 was fine when decided; p3 came after the SHORT
    assert {"key": ["solana", a], "decision_t": t + 1260, "reason": "CONFLICTING_DIRECTION"} in ind["suppressed"]
    sw = R.generate(d, "SOCIAL_WALLET", {"min_sources": 1, "wallet_window_s": 86400}, POL, R.Audit())
    assert any(x["reason"] == "LINKED_WALLET_SOLD" for x in sw["suppressed"])
    disputed = [dict(w, linkage="DISPUTED") for w in wl[:1]]
    d2 = prep(world(posts=ps, wallets=disputed, candles=series(a) + series(b) + quiet(4)))
    assert R.generate(d2, "SOCIAL_WALLET", {"min_sources": 1, "wallet_window_s": 86400}, POL, R.Audit())["signals"] == []


def test_no_tradable_depth_is_non_executable_not_a_return():
    a = addr(1)
    d = prep(world(posts=[post("p1", "s1", a, T0 + 30 * H)], candles=series(a, liq=3000.0, steps=[(T0 + 40 * H, 3.0)]) + quiet(4, liq=3000.0)))
    o = R.outcome(d, ("solana", a), T0 + 31 * H - 300, 86400, d.as_of, POL, {})
    assert o["status"] == "NON_EXECUTABLE" and "ILLIQUID_ENTRY" in o["codes"]
    assert o["measured"] is None and o["conservative"] is None              # a tripled price that could not be bought is no win


def test_insufficient_sample_is_said_plainly_and_nothing_is_estimated():
    a = addr(1)
    doc = world(posts=[post(f"p{i}", f"s{i}", addr(i), T0 + (10 + 20 * i) * H) for i in range(6)],
                candles=[c for i in range(6) for c in series(addr(i), steps=[(T0 + (12 + 20 * i) * H, 1.4)])] + quiet(6))
    res = R.run(doc)
    for s in R.STRATEGIES:
        assert res["strategies"][s]["verdict"]["verdict"] in ("INSUFFICIENT_SAMPLE", "INSUFFICIENT_DATA")
    md = R.render(res)
    assert "not shown:" in md and "BETTER_THAN" not in md and "WORSE_THAN" not in md
    empty = R.run(world())
    assert all(empty["strategies"][s]["verdict"]["verdict"] == "INSUFFICIENT_DATA" for s in R.STRATEGIES)
    assert "Nothing was estimated and nothing is extrapolated" in R.render(empty)


def test_harness_can_report_an_edge_when_one_exists():
    """Sixty tokens each rise 50% two hours after one post; matched quiet tokens stay flat. The harness must be able to say yes."""
    n = 60
    ps, cs = [], []
    for i in range(n):
        t = T0 + 24 * H + i * 10 * H - 300                 # decision at hh:55, entry on the hour
        ps.append(post(f"p{i}", f"s{i % 9}", addr(i), t - 60, avail=t))
        cs += series(addr(i), days=28, steps=[(t + 2 * H + 300, 1.5)])
    cs += quiet(12, start=200, days=28)
    doc = world(posts=ps, candles=cs, days=28)
    res = R.run(doc, {"min_test_n": 8, "min_report_n": 8})
    v = res["strategies"]["INDIVIDUAL"]["verdict"]
    assert v["verdict"] == "BETTER_THAN_CONTROLS_IN_REPLAY", v
    t = res["strategies"]["INDIVIDUAL"]["test"]["86400"]["conservative"]
    assert t["median_relative"] > 0.4 and t["median_relative_ci"][0] > 0 and t["precision"] == 1.0


def test_policy_refuses_trading_keys_and_bad_splits():
    with pytest.raises(R.ReplayError):
        R.make_policy({"execute_orders": True})
    with pytest.raises(R.ReplayError):
        R.make_policy({"split_fractions": [0.5, 0.5, 0.5]})
    with pytest.raises(R.ReplayError):
        R.make_policy({"primary_horizon_s": 7})
    assert R.make_policy()["trade_execution_impact"] == "none"


# ---------- real-data adapters (read-only) ----------

def test_tracked_database_has_no_social_history_and_gives_insufficient_data():
    db = ROOT / "data" / "memelab.sqlite"
    before = db.stat().st_mtime
    doc = RS.merge(RS.from_db(str(db)))
    inv = RS.inventory(doc)
    assert inv["posts"] == 0 and inv["wallet_events"] == 0
    res = R.run(doc) if doc["as_of"] else None
    if res:
        assert all(res["strategies"][s]["verdict"]["verdict"] == "INSUFFICIENT_DATA" for s in R.STRATEGIES)
    assert db.stat().st_mtime == before


def test_inbox_adapter_reads_candles_and_trending_lists_without_inventing_chains(tmp_path):
    at = "2026-10-07T17:14:55.000Z"
    t_at = 1791393295.0
    base, other = "BaseMint" + "z" * 36, "OtherMint" + "z" * 35
    body = {"_plan": "x", "_at": at,
            "gt_pools:solana:trending:1": {"s": 200, "body": {"pools": [{"pool": "PoolA", "net": "solana", "base": base, "price": 1.0, "reserve": 50000, "fdv": 4e5}]}},
            "gt_ohlcv:PoolA:hour1": {"s": 200, "body": {"ohlcv": [[t_at - 7200, 1, 1, 1, 1, 10], [t_at - 3600, 1, 1, 1, 1, 10], [t_at - 1000, 1, 1, 1, 1, 1]],
                                                       "meta": {"base": {"address": base}}}},
            "gt_ohlcv:PoolB:hour1": {"s": 200, "body": {"ohlcv": [[t_at - 7200, 1, 1, 1, 1, 10]], "meta": {"base": {"address": other}}}},
            "ds_boosts:latest": {"s": 200, "body": [{"chainId": "base", "tokenAddress": "0xAbC0000000000000000000000000000000000001"}]}}
    (tmp_path / "a.json").write_text(json.dumps(body))
    doc = RS.merge(RS.from_inbox(str(tmp_path)))
    assert len(doc["candles"]) == 3 and all(c["chain"] == "solana" and c["available_at"] == t_at for c in doc["candles"])
    assert any("could not be established" in n for n in doc["notes"])          # PoolB: no chain evidence, skipped
    assert len(doc["trending"]) == 2 and doc["coverage"]["universe"]["includes_delisted"] is False
    d = R.prepare(doc, POL)
    assert d.excluded["candles"]["UNFINISHED_CANDLE_AT_CAPTURE"] == 1        # the open candle was not finished at capture
    assert ("base", "0xabc0000000000000000000000000000000000001") in d.trend_by_key


def test_db_adapter_reads_social_calls_reposts_and_linked_wallets(tmp_path):
    from memelab.social import schema
    p = tmp_path / "lab.sqlite"
    con = sqlite3.connect(p)
    schema.migrate(con)
    a = addr(7)
    con.execute("INSERT INTO social_analysis_versions(version, component, created_at) VALUES ('v1','extractor',0)")
    for acc in ("x:id:1", "x:id:2"):
        con.execute("INSERT INTO social_accounts(account_id, platform, first_seen_at, last_seen_at) VALUES (?,?,0,0)", (acc, "x"))
    con.execute("INSERT INTO social_token_refs(ref_key, ref_kind, chain, contract, first_seen_at) VALUES (?,?,?,?,0)",
                (f"ca:solana:{a}", "CONTRACT_ADDRESS", "solana", a))
    for k, acc, pub in (("x:1", "x:id:1", T0 + 10 * H), ("x:2", "x:id:2", T0 + 11 * H)):
        con.execute("INSERT INTO social_items(item_key, platform, account_id, published_at, first_observed_at, first_ingested_at) VALUES (?,?,?,?,?,?)",
                    (k, "x", acc, pub, pub + 120, pub + 130))
        con.execute("INSERT INTO social_claims(claim_key, item_key, account_id, claim_type, token_ref_id, direction, claimed_at, extracted_at, analysis_version) "
                    "VALUES (?,?,?,?,1,'LONG',?,?, 'v1')", (k + "c", k, acc, "CALL", pub, pub + 200))
    con.execute("INSERT INTO social_item_refs(item_key, ref_type, referenced_item_key, recorded_at) VALUES ('x:2','retweeted','x:1',0)")
    con.commit()
    con.close()
    doc = RS.merge(RS.from_db(str(p)))
    assert len(doc["posts"]) == 2
    by = {x["post_id"]: x for x in doc["posts"]}
    assert all(x["available_at"] == x["published_at"] + 120 for x in doc["posts"])
    assert sum(1 for x in by.values() if x["repost_of"]) == 1
    assert "summary" not in json.dumps(doc) and "text" not in json.dumps(doc["posts"])


# ---------- CLI and the committed sample ----------

def test_cli_inventory_and_run_on_the_tracked_database(tmp_path):
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "replay", "inventory", "--db", "data/memelab.sqlite"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "posts 0" in r.stdout and "no social schema" in r.stdout
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "replay", "run", "--db", "data/memelab.sqlite"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "INSUFFICIENT_DATA" in r.stdout and "No leakage detected: yes" in r.stdout and "FIXTURE" not in r.stdout
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "replay", "run"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 2


def test_sample_report_is_reproduced_by_the_demo_command():
    md = CLI.demo_markdown()
    assert md == (FIX / "sample_report.md").read_text()
    assert md.count(CLI.WATERMARK) == 2 and "No leakage detected: yes" in md
    spec = json.loads((FIX / "synthetic_spec.json").read_text())
    assert spec == SY.DEFAULT_SPEC

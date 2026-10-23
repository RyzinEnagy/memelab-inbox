"""Phase 13: per-opportunity assessment hook (off by default; idempotent; never changes the lab's result).

Uses the repository's real collected inbox data (PAID token) for the analysis result, and synthetic variants of it
for the abstain paths (G01-G04 / G31 / G34 opportunities are assessed once or explicitly abstained)."""
import copy
import json
import time
from pathlib import Path

import pytest

from memelab import pipeline
from memelab.backtest import assess, hook, store
from memelab.bridge import ingest

INBOX = Path(__file__).resolve().parent.parent / "data" / "inbox"
IDS = ["disc01", "s2_01", "deep01a"]
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
ON = dict(assess.DEFAULT_POLICY, enabled=True, deep_stage="queue")

pytestmark = pytest.mark.skipif(not all((INBOX / f"{i}.result.json").exists() for i in IDS), reason="live inbox files not present")
_R = []


def real():
    if not _R:
        res = [ingest.load_result(INBOX / f"{i}.result.json") for i in IDS]
        bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
        _R.append(pipeline.analyze_token(PAID, bodies, sol_price=120.8, persist=False))
    return copy.deepcopy(_R[0])


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def test_off_by_default_returns_nothing_and_touches_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("MEMELAB_BACKTEST", raising=False)
    monkeypatch.setattr(assess, "POLICY_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(store, "BT_DB_PATH", tmp_path / "never.sqlite")
    r = real()
    before = copy.deepcopy(r)
    assert hook.maybe_assess(r) is None and hook.one_line(None) is None
    assert r == before and not (tmp_path / "never.sqlite").exists()


def test_enabled_assessment_is_idempotent_and_never_changes_the_lab_result(con):
    r = real()
    before = json.dumps({k: r[k] for k in ("score", "status", "report_md", "thesis")}, sort_keys=True, default=str)
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    b = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert a["cache"] == "MISS" and b["cache"] == "HIT" and a["request_key"] == b["request_key"]
    assert con.execute("SELECT COUNT(*) FROM bt_assessments WHERE stage='FAST'").fetchone()[0] == 1
    assert json.dumps({k: r[k] for k in ("score", "status", "report_md", "thesis")}, sort_keys=True, default=str) == before
    assert a["lab"]["score"] == r["score"]["total"] and a["lab"]["status"] == r["status"]["status"]
    assert a["snapshot"]["swap_fee"] == 0.0125 and a["snapshot"]["fee_basis"] == "ASSUMED_UPPER_OBSERVED_TIER"   # main pool is PumpSwap
    assert a["snapshot"]["fee_authority_active"] is False            # the all-zero key means no authority (real bundle value)
    assert "FEE_HIKE" not in {s["scenario"] for s in a["stress"]["scenarios"]}
    assert a["tier"] in ("SCENARIO_ONLY", "HISTORICAL_COHORT") and a["stress"]["probabilities"].startswith("NOT_ASSIGNED")


def test_a_changed_snapshot_is_a_new_request(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    r["bundle"]["market"]["liquidity_usd_total"] = r["bundle"]["market"]["liquidity_usd_total"] * 0.5
    r["bundle"]["pools"][0]["reserve_usd"] = r["bundle"]["pools"][0]["reserve_usd"] * 0.5
    c = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert c["request_key"] != a["request_key"] and c["cache"] == "MISS"


def _variant(kind):
    r = real()
    b = r["bundle"]
    if kind == "fatal":
        r["score"]["fatal_flags"] = [{"flag": "MINT_AUTHORITY_ACTIVE"}]
    elif kind == "invalid":
        r["mint"] = "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"           # the real corrupted copy found in the lab's exports (31 bytes)
    elif kind == "noprice":
        b["market"]["price_usd"] = None
    elif kind == "clmm":
        b["pools"] = [dict(b["pools"][0], dex="raydium-clmm")]
    elif kind == "new":
        b["ohlcv"]["hour1"] = b["ohlcv"]["hour1"][-5:]
    elif kind == "broken":
        r["modules"]["entries"] = {"entries": [{"invalidation_level": "not a number"}]}
    return r


@pytest.mark.parametrize("kind,state", [("fatal", "RISK_FATAL_FLAW"), ("invalid", "INVALID_TOKEN_ID"), ("noprice", "SOURCE_BLOCKED"),
                                        ("clmm", "UNSUPPORTED_POOL"), ("new", "INSUFFICIENT_HISTORY"), ("broken", "ERROR")])
def test_every_opportunity_is_assessed_once_or_explicitly_abstained(con, kind, state):
    r = _variant(kind)
    out = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert out["state"] == state
    assert con.execute("SELECT COUNT(*) FROM bt_assessments WHERE stage='FAST'").fetchone()[0] == 1   # recorded, not dropped
    if state == "RISK_FATAL_FLAW":
        assert out["stress"]["decision"] == "RISK_FATAL_FLAW"
    if state in ("INVALID_TOKEN_ID",):
        assert out["retriable"] is False
    if state in ("SOURCE_BLOCKED", "ERROR"):
        assert out["retriable"] is True


def test_stale_snapshot_abstains(con):
    r = real()
    out = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 3 * 3600)
    assert out["state"] == "STALE_DATA"


def test_hook_never_raises_and_reports_one_line(con, monkeypatch):
    bad = {"mint": PAID}
    assert hook.maybe_assess(bad, ON)["state"] == "ERROR"
    r = real()
    line = hook.one_line(assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60))
    assert line.startswith("backtest: ") and line.endswith("research only") and "buy" not in line.lower()
    monkeypatch.setattr(assess, "attach", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = hook.maybe_assess(r, ON)
    assert out["state"] == "ERROR" and "boom" in out["error"] and out["retriable"]


def test_catalyst_refresh_rules(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    t = a["as_of"] + 600
    base = {"chain": "solana", "mint": PAID, "origin_group": "solana.com/news/x", "content_hash": "h1", "available_at": t, "mint_verified": True}
    assert assess.on_catalyst(con, dict(base, mint_verified=False), a)["action"] == "IGNORED"            # ticker or name match only
    assert assess.on_catalyst(con, base, None)["action"] == "IGNORED"                                    # never analyzed yet
    assert assess.on_catalyst(con, dict(base, available_at=a["as_of"] - 1), a)["action"] == "IGNORED"    # already reflected
    assert assess.on_catalyst(con, dict(base, mint="So11111111111111111111111111111111111111112"), a)["action"] == "IGNORED"
    assert assess.on_catalyst(con, base, a)["action"] == "REFRESH_REQUESTED"
    assert assess.on_catalyst(con, base, a)["action"] == "IGNORED"                                       # same origin+content again


def test_deep_stage_and_observability(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert assess.pending_deep(con) == [a["request_key"]]
    d = assess.run_deep(con, a["request_key"])
    assert d["state"] in ("COMPLETE", "INSUFFICIENT_HISTORY") and d["cache"] == "MISS"
    assert assess.run_deep(con, a["request_key"])["cache"] == "HIT" and assess.pending_deep(con) == []
    assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    st = assess.stats(con)
    assert st["events"]["REQUESTED"]["n"] == 1 and st["events"]["CACHE_HIT"]["n"] == 1 and st["events"]["COMPLETED"]["avg_ms"] is not None


def test_fast_stage_benchmark(con):
    r = real()
    t0 = time.time()
    assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert time.time() - t0 < 2.0                                    # the scout is not held up


def test_scout_command_report_identical_with_hook_off_and_on(tmp_path, monkeypatch):
    from memelab import cli, db
    r = real()

    class A:
        def __init__(self, rd):
            self.__dict__.update(mints=[PAID], results=["fx"], stage1=None, min_score=55, social=False, social_policy=None,
                                 social_include_fixtures=False, report_dir=str(rd))

    def run(sub, enabled):
        monkeypatch.setattr(db, "DB_PATH", tmp_path / sub / "lab.sqlite")
        monkeypatch.setattr(db, "DATA_DIR", tmp_path / sub / "data")
        monkeypatch.setattr(store, "BT_DB_PATH", tmp_path / sub / "bt.sqlite")
        monkeypatch.setattr(assess, "POLICY_PATH", tmp_path / "absent.json")
        monkeypatch.setenv("MEMELAB_BACKTEST", "1" if enabled else "0")
        monkeypatch.setattr(cli, "_bodies", lambda ids: ({}, r["bundle"]["observed_at"]))
        monkeypatch.setattr(cli, "_sol_price", lambda b: 120.8)
        seen = []
        monkeypatch.setattr(cli.pipeline, "analyze_token", lambda mint, bodies, **k: seen.append(copy.deepcopy(r)) or seen[-1])
        rd = tmp_path / sub / "reports"
        rd.mkdir(parents=True, exist_ok=True)
        cli.cmd_scout(A(rd))
        return next(rd.glob("*_SCOUT.md")).read_text(), seen
    off, s_off = run("off", False)
    on, s_on = run("on", True)
    assert off == on                                                   # Phase 13 attaches; it renders nothing (Phase 14 does)
    assert "backtest_assessment" not in s_off[0] and not (tmp_path / "off" / "bt.sqlite").exists()
    assert s_on[0]["backtest_assessment"]["state"] in ("PARTIAL_WITH_LIMITATIONS", "COMPLETE", "INSUFFICIENT_HISTORY", "STALE_DATA")


def test_token_signals_use_only_closed_and_published_bars():
    r = real()
    h = r["bundle"]["ohlcv"]["hour1"]
    newest = max(float(x[0]) for x in h)
    r["bundle"]["observed_at"] = newest + 3600 + 100                  # newest bar closed, provider lag (300 s) not yet passed
    s = assess.token_signal_states(r, assess.DEFAULT_POLICY)
    assert s["dropped_unclosed"] == 1 and s["closed_bars"] == len(h) - 1
    r["bundle"]["observed_at"] = newest + 3600 + 300
    assert assess.token_signal_states(r, assess.DEFAULT_POLICY)["dropped_unclosed"] == 0


def test_deep_stage_never_reads_past_the_assessment_time(con, monkeypatch):
    from memelab.backtest import engine, runner
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    seen = []

    def spy(self, strat, tokens, until=None, **k):
        seen.append(until)
        return {"n_trades": 0, "mean_ret": None, "trades": []}
    monkeypatch.setattr(runner, "build_tokens", lambda c, uid, mints=None, **k: (["token"], []))
    monkeypatch.setattr(runner, "sol_usd_series", lambda c: None)
    monkeypatch.setattr(engine.Engine, "run", spy)
    d = assess.run_deep(con, a["request_key"])
    assert len(seen) == len(assess.DEFAULT_POLICY["ta_strategies"]) and all(u == a["as_of"] for u in seen)
    assert d["state"] == "INSUFFICIENT_HISTORY" and d["tier"] == "UNAVAILABLE"      # zero trades is not evidence


# ---- Phase 13 gate: G01-G04, G31, G34 opportunities are each assessed once or explicitly abstained ----
OTHER = "3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump"                  # a real, valid mint (the collapsed fixture token)


def test_g01_same_ticker_two_mints_are_two_assessments(con):
    a_r, b_r = real(), real()
    b_r["mint"] = OTHER                                                 # same symbol PAID, different mint
    assert a_r["bundle"]["identity"]["symbol"] == b_r["bundle"]["identity"]["symbol"]
    t = a_r["bundle"]["observed_at"] + 60
    a, b = assess.attach(a_r, ON, con=con, now=t), assess.attach(b_r, ON, con=con, now=t)
    assert a["request_key"] != b["request_key"] and (a["mint"], b["mint"]) == (PAID, OTHER)
    rows = con.execute("SELECT mint FROM bt_assessments WHERE stage='FAST' ORDER BY mint").fetchall()
    assert [x[0] for x in rows] == sorted([PAID, OTHER])
    rec = {"chain": "solana", "mint": OTHER, "origin_group": "x", "content_hash": "h", "available_at": t + 600, "mint_verified": True}
    assert assess.on_catalyst(con, rec, a)["action"] == "IGNORED"       # a record about B never refreshes A


def test_g02_main_pool_only_never_summed_across_pools(con):
    r = real()
    pools = r["bundle"]["pools"]
    assert len(pools) > 1
    snap, prov = assess.snapshot_from_result(r)
    main = max(pools, key=lambda p: p.get("reserve_usd") or 0)
    assert snap.liquidity_usd == main["reserve_usd"] < sum(p.get("reserve_usd") or 0 for p in pools)
    assert prov["main_pool"] == main["pool"] and snap.pool_type == "CPMM"


def test_g03_catalyst_timing_uses_availability_not_publication(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    base = {"chain": "solana", "mint": PAID, "origin_group": "news", "mint_verified": True}
    early_claim = dict(base, content_hash="c1", published_at=a["as_of"] - 3600, available_at=a["as_of"] + 720)   # posted 09:00, ingested later
    late_claim = dict(base, content_hash="c2", published_at=a["as_of"] + 3600, available_at=a["as_of"] - 1)
    assert assess.on_catalyst(con, early_claim, a)["action"] == "REFRESH_REQUESTED"
    assert assess.on_catalyst(con, late_claim, a)["action"] == "IGNORED"


def test_g04_wallet_transfer_is_carried_as_its_own_kind(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    rec = {"chain": "solana", "mint": PAID, "origin_group": "wallet:x", "content_hash": "t1", "available_at": a["as_of"] + 60,
           "mint_verified": True, "kind": "WALLET_TRANSFER"}
    out = assess.on_catalyst(con, rec, a)
    assert out["action"] == "REFRESH_REQUESTED" and out["claim_kind"] == "WALLET_TRANSFER"
    assert "SELL" not in json.dumps(a)                                   # the FAST stage reads no wallet flow and labels no sale


def test_g34_blocked_quote_provider_degrades_explicitly(con):
    r = real()
    for q in r["bundle"]["quotes"]["SELL"].values():
        q["status"] = "HTTP_429"
    out = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert out["state"] not in ("ERROR",) and out["tier"] != "TOKEN_SPECIFIC"
    assert all(s[3] == "HTTP_429" and s[1] is None for s in out["sell_quotes"])          # blocked, not fabricated
    assert con.execute("SELECT COUNT(*) FROM bt_assessments WHERE stage='FAST'").fetchone()[0] == 1


def test_new_evidence_rows_change_the_request(con):
    r = real()
    t = r["bundle"]["observed_at"] + 60
    a = assess.attach(r, ON, con=con, now=t)
    store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=OTHER, basis="THESIS", entered_at=t - 7200,
                                 status_at_entry="REJECTED")
    con.commit()
    b = assess.attach(r, ON, con=con, now=t)
    assert b["request_key"] != a["request_key"] and b["cache"] == "MISS"


def test_robot_outage_never_changes_the_verdict(con):
    r = real()
    a = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    rec = {"chain": "solana", "mint": PAID, "origin_group": "robot", "content_hash": "o1", "available_at": a["as_of"] + 60,
           "mint_verified": True, "source_status": "SOURCE_BLOCKED"}
    assert assess.on_catalyst(con, rec, a)["action"] == "IGNORED"
    assert con.execute("SELECT COUNT(*) FROM bt_assessment_events WHERE event='CATALYST_REFRESH'").fetchone()[0] == 0


def test_a_cached_answer_ages_out(con):
    r = real()
    t = r["bundle"]["observed_at"]
    a = assess.attach(r, ON, con=con, now=t + 60)
    late = assess.attach(r, ON, con=con, now=t + 3 * 3600)              # the same old analysis, asked for 3 h later
    assert a["state"] != "STALE_DATA" and late["state"] == "STALE_DATA" and late["cache"] == "HIT_STALE"
    assert late["stored_state"] == a["state"] and late["request_key"] == a["request_key"]
    assert con.execute("SELECT COUNT(*) FROM bt_assessments WHERE stage='FAST'").fetchone()[0] == 1


def test_severe_stress_is_a_flag_beside_the_score_never_a_score_change(con):
    r = real()
    r["modules"].setdefault("depth", {})["no_route"] = True                 # no sell route at decision time
    score, status = r["score"]["total"], r["status"]["status"]
    out = assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + 60)
    assert out["stress"]["decision"] == "STRUCTURALLY_UNTRADEABLE" and out["flags"] == ["BT_STRUCTURALLY_UNTRADEABLE"]
    assert (out["lab"]["score"], out["lab"]["status"]) == (score, status) == (r["score"]["total"], r["status"]["status"])
    assert "flags" not in r["score"] or "BT_STRUCTURALLY_UNTRADEABLE" not in json.dumps(r["score"])

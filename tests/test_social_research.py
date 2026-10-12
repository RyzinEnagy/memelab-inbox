"""Phase 13: social findings as research candidates beside the existing scout and catalyst workflows.

Invented data only (tests/fixtures/social/research/make_research.py builds the scout fixture; the end-to-end tests write
invented posts with the Phase 07 test builder). Temp databases, fixed clocks, no network.
"""
import copy
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import cli, db, report
from memelab.social import research_cli as RCLI, research_core as RC, research_store as RS, store

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "research"
DOC = json.loads((FX / "scout_before_after.json").read_text())
M = DOC["mints"]
AS_OF = DOC["as_of"]
POL = RC.make_policy({"include_fixtures": True}, source="test")

sys.path.insert(0, str(ROOT / "tests"))
import test_social_narratives as TN  # noqa: E402  (the Phase 07 builder: invented posts straight into the Phase 01 to 06 tables)


def build(findings=None, results=None, prior=None, policy=POL, as_of=AS_OF):
    results = DOC["results"] if results is None else results
    _, serious, _, _ = cli.scout_lists(results, {}, 55)
    ev = RS.evaluated_from_scout(results, [r["mint"] for r in serious], DOC["prior"] if prior is None else prior)
    return RC.build(DOC["findings"] if findings is None else findings, ev, policy, as_of=as_of)


def cand(res, mint):
    return next(c for c in res["candidates"] if c["contract"] == mint)


def finding(sym, **kw):
    f = copy.deepcopy(next(f for f in DOC["findings"] if f.get("contract") == M[sym]))
    f.update(kw)
    return f


# ---------- fixture and demo ----------

def test_fixture_file_matches_its_builder():
    spec = importlib.util.spec_from_file_location("make_research", FX / "make_research.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert json.loads(json.dumps(mod.build(), sort_keys=True)) == DOC


def test_before_after_report_enriches_one_candidate_and_leaves_rejections_alone():
    ba = RCLI.before_after(DOC, POL)
    assert ba["body_unchanged"] is True
    assert ba["after"].startswith(ba["before"]) and ba["after"] != ba["before"]
    assert ba["serious"] == [M["GOODCAT"]]
    assert M["OLDRUG"] in ba["rejected"] and M["HYPEDOG"] in ba["rejected"] and M["TOPPICK"] in ba["rejected"]
    for sym in ("OLDRUG", "HYPEDOG", "TOPPICK"):           # the rejected lines of the body are byte-identical
        line = next(l for l in ba["before"].splitlines() if M[sym] in l and l.startswith("- "))
        assert line in ba["after"]
    g = cand(ba["result"], M["GOODCAT"])
    assert g["research_state"] == "RESEARCH_CANDIDATE" and g["lanes"]["narrative_attention"]["level"] == "CORROBORATED"
    assert cand(ba["result"], M["OLDRUG"])["rejection_review"]["verdict"] == "STANDS"


def test_demo_cli_runs_and_writes_side_by_side(tmp_path):
    out = tmp_path / "ba.md"
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "research", "demo", "--fixture", str(FX / "scout_before_after.json"),
                        "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    md = out.read_text()
    assert "Report body unchanged by the social layer: yes." in md
    assert "## Before: social off" in md and "## After: social on" in md
    assert "| GOODCAT | 68 | WATCH | serious | same | same | CORROBORATED | RESEARCH_CANDIDATE |" in md
    assert "| OLDRUG | 0 | REJECTED | rejected | same | same | NONE | NO_SOCIAL_SIGNAL |" in md


# ---------- the prompt's test list ----------

def test_fatal_flag_override_high_hype_never_clears_a_fatal_flag():
    hype = finding("HYPEDOG", independent_source_count=50, confidence="HIGH")
    res = build([hype])
    c = cand(res, M["HYPEDOG"])
    assert c["research_state"] == "REJECTED_STRUCTURE"
    assert c["lanes"]["narrative_attention"]["level"] == "CORROBORATED"
    assert c["lanes"]["token_structure"] == {"verdict": "FATAL", "fatal_flags": ["MINT_AUTHORITY_ACTIVE"], "why": "existing fatal checks: MINT_AUTHORITY_ACTIVE"}
    assert c["lanes"]["executable_entry"]["verdict"] == "NOT_YET"
    assert c["in_tradable_ranking"] is False and c["existing_score"] == 0 and c["existing_status"] == "REJECTED"
    assert "narrative attention does not override a fatal flag" in c["notes"]
    assert c["promotional_risks"] and c["promotional_risks"][0]["bucket"] == "HEURISTIC"


def test_spoof_contract_with_the_same_symbol_inherits_nothing():
    res = build()
    spoof = cand(res, M["GOODCAT2"])
    real = cand(res, M["GOODCAT"])
    assert spoof["symbol"] == real["symbol"] == "GOODCAT"
    assert spoof["research_state"] == "NEEDS_STRUCTURAL_ANALYSIS" and spoof["identity_warning"] == "SYMBOL_COLLISION"
    assert spoof["lanes"]["token_structure"]["verdict"] == "NOT_EVALUATED" and spoof["in_tradable_ranking"] is False
    assert spoof["existing_score"] is None and spoof["existing_status"] is None
    assert real["lanes"]["narrative_attention"]["independent_sources"] == 3      # the spoof's source is not added to the real token
    assert real["identity_warning"] is None
    # the same address string on another chain is a different identity and never joins
    other_chain = finding("GOODCAT", chain="base")
    res2 = build([other_chain])
    assert {(c["chain"], c["research_state"]) for c in res2["candidates"] if c["contract"] == M["GOODCAT"]} == {("base", "NEEDS_STRUCTURAL_ANALYSIS")}


def test_social_top_pick_with_no_liquidity_stays_out_of_tradable_rankings():
    res = build([finding("TOPPICK", independent_source_count=12, confidence="HIGH")])
    c = cand(res, M["TOPPICK"])
    assert c["research_state"] == "REJECTED_STRUCTURE" and c["lanes"]["token_structure"]["fatal_flags"] == ["NO_SELL_ROUTE"]
    _, serious, near, rejected = cli.scout_lists(DOC["results"], {}, 55)
    assert M["TOPPICK"] not in [r["mint"] for r in serious] + [n["mint"] for n in near]
    assert M["TOPPICK"] in [x["mint"] for x in rejected]


def test_valid_candidate_with_credible_early_discussion_is_enriched_not_rescored():
    res = build()
    c = cand(res, M["GOODCAT"])
    a = c["lanes"]["narrative_attention"]
    assert c["research_state"] == "RESEARCH_CANDIDATE" and a["level"] == "CORROBORATED" and a["bucket"] == "INFERENCE"
    assert [o["source_id"] for o in a["originators"]] == ["fx_source_a", "fx_source_b", "fx_source_c"]
    assert a["first_observed_at"] == AS_OF - 20 * 3600 and a["age_hours"] == 2.0
    assert c["lanes"]["token_structure"]["verdict"] == "ACCEPTABLE" and c["lanes"]["executable_entry"]["verdict"] == "NOT_YET"
    assert c["existing_score"] == 68 and c["existing_status"] == "WATCH" and c["in_tradable_ranking"] is True
    assert c["attention_weight_bucket"] == "HEURISTIC" and c["trade_execution_impact"] == "none"
    assert any(p["kind"] == "narrative_snapshot" for p in c["provenance"]) and any(p["kind"] == "existing_evaluation" for p in c["provenance"])
    # ENTRY CONDITIONS MET comes from the existing status, never from attention
    res2 = build(results=[{**DOC["results"][0], "status": {"status": "NEAR ENTRY", "reasoning": "x"}}])
    assert cand(res2, M["GOODCAT"])["lanes"]["executable_entry"]["verdict"] == "ATTRACTIVE"


def test_no_social_data_is_an_explicit_no_op_and_the_report_is_unchanged():
    res = build([])
    assert res["state"] == "NO_OP" and res["candidates"] == [] and res["unresolved"] == []
    md = RC.render(res)
    assert "No-op: no social findings for this window" in md
    _, serious, near, rejected = cli.scout_lists(DOC["results"], {}, 55)
    env = {"k": "v"}
    plain = report.render_scout_report(env, serious, near, rejected, when=AS_OF)
    assert report.render_scout_report(env, serious, near, rejected, when=AS_OF, social=None) == plain
    assert report.render_scout_report(env, serious, near, rejected, when=AS_OF, social=res) == plain + "\n" + md


def test_no_op_when_the_social_store_is_missing_empty_or_unopenable(tmp_path):
    old = tmp_path / "old.sqlite"
    c = sqlite3.connect(old); c.execute("CREATE TABLE tokens(mint TEXT)"); c.commit(); c.close()
    res = RS.section(lambda: sqlite3.connect(old), as_of=AS_OF, policy=POL, evaluated=[])
    assert res["state"] == "NO_OP" and res["availability"]["status"] == "UNAVAILABLE" and "not present" in res["no_op_reason"]
    empty = tmp_path / "e.sqlite"; db.init_db(empty)
    res = RS.section(lambda: db.connect(empty), as_of=AS_OF, policy=POL, evaluated=[])
    assert res["state"] == "NO_OP" and res["availability"]["status"] == "AVAILABLE" and res["no_op_reason"] == "no narrative snapshot at or before as_of"

    def boom():
        raise OSError("disk not mounted")
    res = RS.section(boom, as_of=AS_OF, policy=POL, evaluated=[])
    assert res["state"] == "NO_OP" and "cannot open the social store" in res["no_op_reason"]


def test_stale_sources_are_labelled_and_earn_nothing():
    c = cand(build(), M["SLOWFROG"])
    assert c["lanes"]["narrative_attention"]["level"] == "STALE" and c["attention_weight"] == 0.0
    fresh = build([finding("GOODCAT")])
    later = build([finding("GOODCAT")], as_of=AS_OF + 60 * 3600)          # the same finding read 60 h later
    assert cand(fresh, M["GOODCAT"])["lanes"]["narrative_attention"]["level"] == "CORROBORATED"
    assert cand(later, M["GOODCAT"])["lanes"]["narrative_attention"]["level"] == "STALE"
    short = RC.make_policy({"include_fixtures": True, "max_age_hours": 1}, source="test")
    assert cand(build([finding("GOODCAT")], policy=short), M["GOODCAT"])["lanes"]["narrative_attention"]["level"] == "STALE"


def test_conflicting_narratives_are_shown_and_penalised_never_resolved():
    f = finding("GOODCAT", conflicted=1, stance={"negative": 2, "positive": 3})
    c = cand(build([f]), M["GOODCAT"])
    a = c["lanes"]["narrative_attention"]
    assert a["level"] == "CONFLICTED" and a["stance"] == {"negative": 2, "positive": 3} and "disagree" in a["why"]
    assert c["attention_weight"] == 3.0          # 3 sources + MODERATE 2 - conflicted 2
    assert c["research_state"] == "RESEARCH_CANDIDATE" and c["existing_status"] == "WATCH"


def test_insufficient_coverage_is_not_estimable():
    f = finding("GOODCAT", status="insufficient_coverage", reasons=["coverage_gap:x"], independent_source_count=None, confidence="UNKNOWN")
    a = cand(build([f]), M["GOODCAT"])["lanes"]["narrative_attention"]
    assert a["level"] == "NOT_ESTIMABLE" and a["bucket"] == "UNKNOWN" and "coverage_gap:x" in a["why"]


def test_repeated_ingest_of_the_same_findings_counts_once():
    one = build()
    twice = build(DOC["findings"] + copy.deepcopy(DOC["findings"]))
    assert one["candidates"] == twice["candidates"] and one["unresolved"] == twice["unresolved"]
    assert build()["result_sha256"] == one["result_sha256"]


def test_rejected_thesis_and_later_materially_changed_evidence():
    prior = {M["HYPEDOG"]: {"rejected_at": AS_OF - 86400, "stage": "deep", "fatal_flags": ["MINT_AUTHORITY_ACTIVE"]}}
    # social changed (more sources), structure did not: the rejection stands
    res = build([finding("HYPEDOG", independent_source_count=20)], prior=prior)
    rv = cand(res, M["HYPEDOG"])["rejection_review"]
    assert rv["verdict"] == "STANDS" and "new social evidence does not reopen a rejection" in rv["why"]
    # structure changed (authority revoked, so the existing checks no longer fire): reopened for review, status as computed
    fixed = copy.deepcopy(DOC["results"][1])
    fixed["score"].update({"fatal_flags": [], "untradeable": False, "total": 51})
    fixed["status"] = {"status": "RESEARCH REQUIRED", "reasoning": "authority revoked; rebuilding evidence"}
    res2 = build([finding("HYPEDOG")], results=[fixed], prior=prior)
    c2 = cand(res2, M["HYPEDOG"])
    assert c2["rejection_review"]["verdict"] == "REOPEN_FOR_REVIEW" and "MINT_AUTHORITY_ACTIVE" in c2["rejection_review"]["why"]
    assert c2["existing_status"] == "RESEARCH REQUIRED" and c2["research_state"] == "RESEARCH_CANDIDATE"
    # not analyzed again: social attention alone never reopens it
    res3 = RC.build([finding("HYPEDOG")], [], POL, as_of=AS_OF, prior=prior)
    rv3 = res3["candidates"][0]["rejection_review"]
    assert res3["candidates"][0]["research_state"] == "NEEDS_STRUCTURAL_ANALYSIS"
    assert rv3["verdict"] == "STANDS" and "social attention alone never reopens a rejection" in rv3["why"]


def test_prior_rejections_read_from_the_existing_tables(tmp_path):
    p = tmp_path / "t.sqlite"; db.init_db(p)
    with db.connect(p) as con:
        db.upsert_token(con, "MintA"); db.upsert_token(con, "MintB"); db.upsert_token(con, "MintC")
        con.execute("INSERT INTO theses(mint, created_at, status, fatal_flags_json, score) VALUES ('MintA', 100, 'REJECTED', ?, 0)",
                    (json.dumps([{"flag": "LP_UNLOCKED"}]),))
        con.execute("INSERT INTO rejections(mint, rejected_at, stage, why_failed, reconsider_if) VALUES ('MintA', 100, 'deep', 'fatal', 'LP locked')")
        con.execute("INSERT INTO theses(mint, created_at, status, fatal_flags_json, score) VALUES ('MintB', 100, 'REJECTED', '[]', 0)")
        con.execute("INSERT INTO theses(mint, created_at, status, fatal_flags_json, score) VALUES ('MintB', 200, 'WATCH', '[]', 60)")
        con.execute("INSERT INTO rejections(mint, rejected_at, stage, why_failed, reconsider_if) VALUES ('MintC', 150, 'structural', 'liquidity $900 below $30,000', 'x')")
        out = RS.prior_rejections(con, ["MintA", "MintB", "MintC"], before=300)
        assert out["MintA"]["fatal_flags"] == ["LP_UNLOCKED"] and out["MintA"]["reconsider_if"] == "LP locked"
        assert "MintB" not in out                                # a later non-rejected verdict supersedes
        assert out["MintC"]["stage"] == "structural"
        assert RS.prior_rejections(con, ["MintA"], before=100) == {}     # nothing at or after `before` is used


def test_ticker_only_mentions_stay_unresolved_and_out_of_every_list():
    res = build()
    assert res["unresolved"] == [{"symbol": "MOONX", "mentions": 14, "state": "UNRESOLVED", "bucket": "UNKNOWN",
                                  "why": "ticker only, no contract on a stated chain; never ranked and never joined to a token",
                                  "sources": [json.dumps({"engine_version": "narr-v1", "run_id": 1, "window": "fixture"}, sort_keys=True)]}]
    assert all(c["symbol"] != "MOONX" for c in res["candidates"])


# ---------- policy ----------

def test_policy_is_opt_in_versioned_and_refuses_anything_that_reaches_scoring_or_execution(tmp_path):
    d = RC.make_policy()
    assert d["enabled"] is False and d["trade_execution_impact"] == "none" and d["provenance"]["source"] == "default"
    with pytest.raises(RC.PolicyError):
        RC.make_policy({"trade_execution_impact": "size_up"})
    with pytest.raises(RC.PolicyError):
        RC.make_policy({"score_bonus": 5})
    with pytest.raises(RC.PolicyError):
        RC.make_policy({"weights": {"m24_total": 1}})
    with pytest.raises(RC.PolicyError):
        RC.make_policy({"max_age_hours": 0})
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"helius_api_key": "not-read-here", "social_research": {"enabled": True, "max_age_hours": 24}}))
    p = RS.load_policy(config_path=cfg)
    assert p["enabled"] is True and p["max_age_hours"] == 24 and p["provenance"]["source"] == "config" and "helius" not in json.dumps(p)
    pf = tmp_path / "pol.json"; pf.write_text(json.dumps({"policy_version": "elving-2", "weights": {"conflicted": -5}}))
    p2 = RS.load_policy(pf, config_path=cfg)
    assert p2["provenance"]["source"] == "config+file" and p2["weights"]["conflicted"] == -5 and p2["weights"]["per_risk_flag"] == -1.0
    assert p2["provenance"]["sha256"] != p["provenance"]["sha256"]
    assert RS.load_policy(config_path=tmp_path / "missing.json")["provenance"]["sha256"] == d["provenance"]["sha256"]


def test_weights_order_the_section_only():
    heavy = RC.make_policy({"include_fixtures": True, "weights": {"per_independent_source": 100}}, source="test")
    a, b = build(), build(policy=heavy)
    for x, y in zip(a["candidates"], b["candidates"]):
        assert (x["contract"], x["research_state"], x["existing_score"], x["existing_status"], x["in_tradable_ranking"]) == \
               (y["contract"], y["research_state"], y["existing_score"], y["existing_status"], y["in_tradable_ranking"])
    assert cand(b, M["GOODCAT"])["attention_weight"] > cand(a, M["GOODCAT"])["attention_weight"]


# ---------- integrated path: real narrative snapshot -> real scout command ----------

@pytest.fixture()
def snapdb(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p); c.row_factory = sqlite3.Row
    store.register_analysis_version(c, TN.EXTRACT_V, "extractor", "test builder", now=TN.D1)
    yield p, c
    c.close()


def _posts(c, mint):
    TN.cover(c)
    TN.post(c, "ga", "fx_orig_a", TN.D1 + TN.H, tokens=[TN.tok("solana", mint)])
    TN.post(c, "gb", "fx_orig_b", TN.D1 + 2 * TN.H, tokens=[TN.tok("solana", mint)])
    TN.post(c, "gr", "fx_amp", TN.D1 + 3 * TN.H, tokens=[TN.tok("solana", mint)], refs=[("retweeted", "x:ga")], text="invented post ga", attribution="reposted")
    TN.post(c, "tk", "fx_orig_c", TN.D1 + 4 * TN.H, tokens=[TN.tick("MOONX")])


def test_findings_from_a_real_snapshot_and_repeated_ingest(snapdb):
    p, c = snapdb
    mint = M["GOODCAT"]
    _posts(c, mint)
    TN.snap(c, now=TN.D1 + 20 * TN.H)
    c.commit()
    pol = RC.make_policy({"include_fixtures": True}, source="test")
    f1, av = RS.findings_from_db(c, as_of=TN.D1 + 21 * TN.H, policy=pol)
    assert av["status"] == "AVAILABLE"
    ca = next(f for f in f1 if f["kind"] == "CONTRACT")
    assert (ca["chain"], ca["contract"], ca["independent_source_count"], ca["amplifier_count"]) == ("solana", mint, 2, 1)
    assert [f for f in f1 if f["kind"] == "TICKER_ONLY"] == [{"kind": "TICKER_ONLY", "symbol": "MOONX", "mentions": 1, "is_fixture": True,
                                                            "source": {"run_id": 1, "engine_version": "narr-v1", "window": "2026-10-12 UTC"}}]
    # fixtures are ignored by default
    assert RS.findings_from_db(c, as_of=TN.D1 + 21 * TN.H, policy=RC.make_policy())[1]["reason"] == "no narrative snapshot at or before as_of"
    # a snapshot taken after as_of is never read
    assert RS.findings_from_db(c, as_of=TN.D1 + 19 * TN.H, policy=pol)[0] == []
    # repeated ingest of the same posts and a repeated snapshot change nothing
    for pid, acct, h, text in (("ga", "fx_orig_a", 1, None), ("gb", "fx_orig_b", 2, None), ("gr", "fx_amp", 3, "invented post ga"), ("tk", "fx_orig_c", 4, None)):
        acct_id = store.upsert_account(c, "x", handle=acct, provider_user_id=acct, now=TN.D1 + h * TN.H)
        store.record_observation(c, platform="x", access_mode="fixture", collector="narr_test", provider_item_id=pid,
                                 original_url=f"https://example.invalid/{pid}", account_id=acct_id, published_at=TN.D1 + h * TN.H,
                                 observed_at=TN.D1 + h * TN.H + 30, text=text or f"invented post {pid}", now=TN.D1 + h * TN.H + 30)
    again = TN.snap(c, now=TN.D1 + 20 * TN.H)[0]
    assert again["created"] is False and again["run_id"] == 1
    c.commit()
    f2, _ = RS.findings_from_db(c, as_of=TN.D1 + 21 * TN.H, policy=pol)
    assert f2 == f1
    r1 = RC.build(f1, [], pol, as_of=TN.D1 + 21 * TN.H)
    r2 = RC.build(f2 + f1, [], pol, as_of=TN.D1 + 21 * TN.H)
    assert r1["result_sha256"] == RC.build(f1, [], pol, as_of=TN.D1 + 21 * TN.H)["result_sha256"] and r1["candidates"] == r2["candidates"]
    # reading never writes
    n = c.total_changes
    RS.section(lambda: sqlite3.connect(p), as_of=TN.D1 + 21 * TN.H, policy=pol, evaluated=[])
    assert c.total_changes == n


class _A:
    def __init__(self, **kw):
        self.__dict__.update({"mints": [r["mint"] for r in DOC["results"]], "results": ["fx"], "stage1": None, "min_score": 55,
                              "social": False, "social_policy": None, "social_include_fixtures": False, "report_dir": None, **kw})


def _run_scout(monkeypatch, tmp_path, dbp, results, **kw):
    by = {r["mint"]: r for r in results}
    monkeypatch.setattr(db, "DB_PATH", dbp)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cli, "_bodies", lambda ids: ({}, TN.D1 + 21 * TN.H))
    monkeypatch.setattr(cli, "_sol_price", lambda b: 150.0)
    calls = []
    monkeypatch.setattr(cli.pipeline, "analyze_token", lambda mint, bodies, **k: calls.append(k) or copy.deepcopy(by[mint]))
    rd = tmp_path / "reports"; rd.mkdir(parents=True, exist_ok=True)
    cli.cmd_scout(_A(report_dir=str(rd), **kw))
    return next(rd.glob("*_SCOUT.md")).read_text(), calls


def test_scout_command_off_is_unchanged_and_on_attaches_from_the_real_snapshot(snapdb, monkeypatch, tmp_path, capsys):
    p, c = snapdb
    _posts(c, M["GOODCAT"])
    TN.snap(c, now=TN.D1 + 20 * TN.H)
    c.commit()
    off, calls = _run_scout(monkeypatch, tmp_path / "off", p, DOC["results"])
    assert "Social research candidates" not in off
    assert all(k["persist"] is True for k in calls)              # the scout still persists exactly as before
    ranked, serious, near, rejected = cli.scout_lists(DOC["results"], {}, 55)
    on, _ = _run_scout(monkeypatch, tmp_path / "on", p, DOC["results"], social=True, social_include_fixtures=True)
    assert on.startswith(off) and on != off
    tail = on[len(off):]
    assert f"GOODCAT `solana:{M['GOODCAT']}`" in tail and "CORROBORATED" in tail and "fx_orig_a" in tail
    assert "MOONX: 1 mention(s)" in tail
    assert "Contains fixture data" in tail
    # opt-in without fixtures on this fixture-only database: an explicit no-op line, body unchanged
    noop, _ = _run_scout(monkeypatch, tmp_path / "noop", p, DOC["results"], social=True)
    assert noop.startswith(off) and "No-op: no narrative snapshot at or before as_of" in noop[len(off):]


def test_scout_command_social_enabled_in_config_without_flag(snapdb, monkeypatch, tmp_path):
    p, _ = snapdb
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "config.json").write_text(json.dumps({"social_research": {"enabled": True}}))
    out, _ = _run_scout(monkeypatch, tmp_path, p, DOC["results"])
    assert "## Social research candidates (opt-in)" in out and "(config, " in out


def test_catalyst_report_social_section_is_opt_in(snapdb, monkeypatch, tmp_path, capsys):
    from memelab.catalyst import cli as ccli
    p, c = snapdb
    mint = M["GOODCAT"]
    _posts(c, mint)
    TN.snap(c, now=TN.D1 + 20 * TN.H)
    db.upsert_token(c, mint, chain="solana", symbol="GOODCAT")
    c.execute("INSERT INTO catalyst_events(id, event_key, category, title, discovered_at, retrieved_at, evidence_status, created_at, updated_at) "
              "VALUES (1, 'fx-event', 'CULTURAL', 'invented event', ?, ?, 'REPORTED', ?, ?)", (TN.D1,) * 4)
    c.execute("INSERT INTO catalyst_assessments(event_id, mint, assessed_at, components_json, fatal_json, triage_score, verdict) "
              "VALUES (1, ?, ?, '{}', '[]', 61, 'RESEARCH')", (mint, TN.D1 + 5 * TN.H))
    c.commit()
    monkeypatch.setattr(db, "DB_PATH", p)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(ccli.R, "render", lambda: "# Catalyst Intelligence report (stub)\n")
    monkeypatch.setattr(ccli.time, "time", lambda: TN.D1 + 21 * TN.H)

    class Args:
        print = True; social = False; social_policy = None
    ccli.cmd_report(Args())
    assert "Social research candidates" not in capsys.readouterr().out
    pf = tmp_path / "pol.json"; pf.write_text(json.dumps({"include_fixtures": True}))
    Args.social, Args.social_policy = True, str(pf)
    ccli.cmd_report(Args())
    out = capsys.readouterr().out
    assert "## Social research candidates (opt-in)" in out
    tail = out[out.index("## Social research candidates"):]
    assert f"GOODCAT `solana:{mint}`" in tail and "whose structure passed the existing checks" in tail
    assert "Existing workflow, unchanged: score 61, status RESEARCH." in tail
    with db.connect(p) as con:     # the catalyst tables are untouched by the social layer
        assert con.execute("SELECT COUNT(*) FROM catalyst_assessments").fetchone()[0] == 1


def test_no_trade_or_watchlist_side_effects():
    src = (ROOT / "memelab" / "social" / "research_core.py").read_text() + (ROOT / "memelab" / "social" / "research_store.py").read_text()
    for word in ("INSERT", "UPDATE ", "DELETE", "place_", "swap(", "sign(", "private_key", "seed"):
        assert word not in src, word
    res = build()
    assert res["trade_execution_impact"] == "none" and all(c["trade_execution_impact"] == "none" for c in res["candidates"])

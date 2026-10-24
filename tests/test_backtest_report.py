"""Phase 14: decision-oriented backtest reports, CLI and alert labels (G31, G34, G35 in Markdown and JSON).

The analysis result is the repository's real collected inbox data (PAID); degraded variants of it stand in for the
regression cases. Stored strategy runs are synthetic rows written through the real store functions."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import pipeline
from memelab.backtest import assess, hook, report as R, store
from memelab.backtest.sources import captures
from memelab.bridge import ingest

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data" / "inbox"
IDS = ["disc01", "s2_01", "deep01a"]
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
ON = dict(assess.DEFAULT_POLICY, enabled=True)
pytestmark = pytest.mark.skipif(not all((INBOX / f"{i}.result.json").exists() for i in IDS), reason="live inbox files not present")
_R = []


def real():
    if not _R:
        res = [ingest.load_result(INBOX / f"{i}.result.json") for i in IDS]
        bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
        _R.append(pipeline.analyze_token(PAID, bodies, observed_at=max(x.observed_at for x in res), sol_price=120.8, persist=False))
    return copy.deepcopy(_R[0])


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def assessed(con, r, now_s=60):
    return assess.attach(r, ON, con=con, now=r["bundle"]["observed_at"] + now_s)


def both(con, a, **k):
    doc = R.build(a, con=con, **k)
    assert R.validate(doc) == []
    doc2 = json.loads(json.dumps(doc, default=str))                    # JSON-serializable without loss of the checked fields
    return doc2, R.render_md(doc)


def add_run(con, sid, n, net, paper, ledger="L"):
    rid = store.register_run(con, {"strategy_id": sid, "strategy_version": "1", "params": {}, "universe_definition": "lab_state_history",
                                   "engine": {"fill_model": "LIQ_SNAPSHOT_APPROX"}, "mints": None, "label": "t"}, dataset_hash="D" + sid)
    store.record_result(con, rid, "COMPLETE", {"n_trades": n, "mean_ret": net, "mean_paper_ret_mid": paper, "ledger_hash": ledger + sid})
    con.commit()
    return rid


# ---------------------------------------------------------------- the real report

def test_real_report_traces_every_key_field(con):
    r = real()
    a = assessed(con, r)
    rid = add_run(con, "BREAKOUT_CLOSE", 47, -0.135, -0.03)
    doc, md = both(con, a)
    assert doc["token"]["mint"] == PAID and doc["token"]["chain"] == "solana" and doc["token"]["symbol"] == "PAID"
    assert doc["trace"]["request_key"] == a["request_key"] and a["request_key"][:16] in md
    row = con.execute("SELECT request_key FROM bt_assessments WHERE request_key=?", (doc["trace"]["request_key"],)).fetchone()
    assert row is not None                                              # the report points at a stored assessment
    run = doc["historical_evidence"]["strategies"]["runs"][0]
    assert run["run_id"] == rid and run["dataset_hash"] == "DBREAKOUT_CLOSE" and run["result_hash"] and rid[:10] in md
    assert doc["lab"]["score"] == r["score"]["total"] and doc["lab"]["status"] == r["status"]["status"]
    assert doc["execution_quote"]["quotes"] and doc["execution_quote"]["observed_at_utc"].endswith("UTC")
    assert doc["stress"]["probabilities"].startswith("NOT_ASSIGNED") and "no probabilities" in md
    ex = doc["stress"]["executable_vs_paper"]
    assert ex and all(x["executable_proceeds_usd"] < x["paper_value_mid_usd"] for x in ex)   # executable is below paper
    assert doc["headline"]["good_project"]["source"].startswith("lab") and doc["headline"]["good_entry"]["source"].startswith("execution")
    assert doc["catalysts"]["maxun_running"] is False and "NOT_ADOPTED" in md
    for word in ("buy now", "guaranteed", "chance to moon", "will pump"):
        assert word not in md.lower()
    assert "—" not in md and "“" not in md                          # plain punctuation


def test_report_has_no_single_combined_score(con):
    doc, md = both(con, assessed(con, real()))
    flat = json.dumps(doc)
    assert "probability_of" not in flat and "combined_score" not in flat and "%" not in doc["headline"]["label"]
    assert doc["lab"]["note"].startswith("the lab's 100-point score")


# ---------------------------------------------------------------- G31, G34, G35 in Markdown and JSON

def test_g31_new_token_never_claims_token_specific_history(con):
    r = real()
    r["bundle"]["ohlcv"]["hour1"] = r["bundle"]["ohlcv"]["hour1"][-5:]
    doc, md = both(con, assessed(con, r))
    assert doc["trace"]["assessment_state"] == "INSUFFICIENT_HISTORY" and doc["trace"]["assessment_tier"] != "TOKEN_SPECIFIC"
    assert doc["historical_evidence"]["token_specific"]["state"] in ("NONE", "NOT_RUN")
    assert any("fewer than 25 closed hourly bars" in x for x in doc["uncertainty"]["items"])
    assert "INSUFFICIENT_HISTORY" in md and "no token-specific backtest" in md and "TOKEN_SPECIFIC" not in md
    assert doc["headline"]["label"] in ("INCONCLUSIVE", "UNTESTED")


def test_g34_blocked_provider_degrades_without_blanking(con):
    r = real()
    for q in r["bundle"]["quotes"]["SELL"].values():
        q["status"] = "HTTP_429"
    doc, md = both(con, assessed(con, r))
    assert all(q["status"] == "HTTP_429" and q["proceeds_usd"] is None for q in doc["execution_quote"]["quotes"])
    assert "no quote (HTTP_429)" in md and "no usable sell quote" in md
    assert doc["lab"]["score"] == r["score"]["total"] and doc["token"]["symbol"] == "PAID"            # the candidate stays visible
    r2 = real()
    r2["bundle"]["market"]["price_usd"] = None                                                        # price provider out
    doc2, md2 = both(con, assessed(con, r2))
    assert doc2["headline"]["label"] == "UNTESTED" and doc2["trace"]["assessment_state"] == "SOURCE_BLOCKED" and doc2["trace"]["retriable"]
    assert doc2["stress"] is None and "Not assessed because: no price" in md2 and "PAID" in md2
    assert doc2["lab"]["score"] == r2["score"]["total"]


def test_g35_paper_profit_that_turns_negative_is_ranked_by_net(con):
    add_run(con, "PAPER_STAR", 40, -0.05, 0.40)                          # dramatic on paper, negative after exit costs
    add_run(con, "PLAIN", 35, 0.02, 0.03)
    add_run(con, "TINY", 3, 0.50, 0.55)                                  # too few trades to rank
    doc, md = both(con, assessed(con, real()))
    s = doc["historical_evidence"]["strategies"]
    by = {x["strategy"]: x for x in s["runs"]}
    assert by["PLAIN"]["rank_by_net"] == 1 and by["PAPER_STAR"]["rank_by_net"] == 2 and by["PAPER_STAR"]["rank_by_paper"] == 1
    assert by["PAPER_STAR"]["flag"] == "PAPER_ONLY_PROFIT" and s["paper_only_profit"] == ["PAPER_STAR"]
    assert by["TINY"]["rank_by_net"] is None and abs(by["PAPER_STAR"]["cost_drag"] - 0.45) < 1e-9
    assert "#1 PLAIN" in md and "#2 PAPER_STAR" in md and "not ranked TINY" in md
    assert "Profitable on paper but not after costs: PAPER_STAR" in md
    assert md.index("#1 PLAIN") < md.index("#2 PAPER_STAR")


# ---------------------------------------------------------------- integration regression

@pytest.mark.parametrize("case", ["missing_history", "missing_quote", "new_token", "disallowed_mint", "provider_outage", "high_status_mismatch",
                                  "fatal", "no_assessment"])
def test_every_degraded_case_gives_truthful_output(con, case):
    r = real()
    if case in ("missing_history", "new_token"):
        r["bundle"]["ohlcv"]["hour1"] = [] if case == "missing_history" else r["bundle"]["ohlcv"]["hour1"][-3:]
    elif case == "missing_quote":
        r["bundle"]["quotes"] = {}
    elif case == "disallowed_mint":
        r["mint"] = "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"
    elif case == "provider_outage":
        r["bundle"]["market"]["price_usd"] = None
    elif case == "high_status_mismatch":
        r["status"]["status"] = "ENTRY CONDITIONS MET"
        r["modules"].setdefault("depth", {})["no_route"] = True
    elif case == "fatal":
        r["score"]["fatal_flags"] = [{"flag": "FREEZE_AUTHORITY_ACTIVE"}]
    a = None if case == "no_assessment" else assessed(con, r)
    doc, md = both(con, a, lab=None if a else {"chain": "solana", "mint": PAID, "score": 64, "status": "WATCH", "fatal_flags": []})
    label = doc["headline"]["label"]
    expect = {"disallowed_mint": "UNTESTED", "provider_outage": "UNTESTED", "no_assessment": "UNTESTED", "high_status_mismatch": "BAD EXECUTION",
              "fatal": "FATAL FLAW"}
    if case in expect:
        assert label == expect[case], (case, label)
    else:
        assert label in ("INCONCLUSIVE", "BAD EXECUTION"), (case, label)
    assert label in md and doc["disclosure"] in md
    if case == "high_status_mismatch":
        assert doc["headline"]["mismatch"].startswith("HIGH_STATUS_MISMATCH") and "a good project is not a good entry" in md
        assert doc["lab"]["status"] == "ENTRY CONDITIONS MET"            # shown as the lab computed it, not rewritten
    if case == "fatal":
        assert doc["lab"]["fatal_flags"] == ["FREEZE_AUTHORITY_ACTIVE"] and not doc["lab"]["fatal_override_detected"]
    if case == "missing_quote":
        assert doc["execution_quote"]["quotes"] == [] and "no quote in the analysis bundle" in md


def test_fatal_flaw_override_is_detected(con):
    a = assessed(con, real())
    bad = copy.deepcopy(a)
    bad["lab"]["fatal_flags"] = ["MINT_AUTHORITY_ACTIVE"]              # a downstream record that kept a usable verdict despite the flag
    doc, md = both(con, bad)
    assert doc["lab"]["fatal_override_detected"] is True and doc["headline"]["label"] == "FATAL FLAW" and "Override detected: yes" in md


def test_missing_assessment_is_never_neutral_or_positive():
    assert R.alert_label(None)["label"] == "UNTESTED"
    assert R.alert_label({"state": "ERROR", "error": "x"})["label"] == "UNTESTED"
    assert R.alert_label({"state": "COMPLETE", "tier": "HISTORICAL_COHORT", "stress": {"decision": "NO_TRADE"}})["label"] == "BAD EXECUTION"
    assert R.alert_label({"state": "PARTIAL_WITH_LIMITATIONS", "tier": "SCENARIO_ONLY", "stress": {"decision": "RESEARCHABLE"}})["label"] == "INCONCLUSIVE"
    assert R.alert_label({"state": "COMPLETE", "tier": "HISTORICAL_COHORT", "stress": {"decision": "RESEARCHABLE"}}, ["X"])["label"] == "FATAL FLAW"


# ---------------------------------------------------------------- catalysts and collectors

def test_catalyst_provenance_late_crawl_and_collector_status(con):
    a = assessed(con, real())
    t = a["as_of"]
    captures.record_capture(con, collector="MAXUN", source_url="https://solana.com/news/x", text="claim", captured_at=t - 3600,
                            source_published_at=t - 30 * 3600, published_confidence="META", run_id="r1", run_status="OK",
                            chain="solana", mint=PAID, mint_verified=True, record_type="ARTICLE")
    con.commit()
    doc, md = both(con, a)
    c = doc["catalysts"]
    assert c["n"] == 1 and c["records"][0]["capture_method"] == "MAXUN" and c["maxun_running"] is False
    w = " ".join(c["records"][0]["warnings"])
    assert "LATE_CRAWL" in w and "LATE_CAPTURE" in w
    assert "MAXUN https://solana.com/news/x" in md and "first known" in md and "No Maxun robot runs" in md


# ---------------------------------------------------------------- alerts

def test_alert_context_off_is_none_and_on_labels_untested(tmp_path, monkeypatch, con):
    monkeypatch.setattr(assess, "POLICY_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(store, "BT_DB_PATH", tmp_path / "none.sqlite")
    monkeypatch.delenv("MEMELAB_BACKTEST", raising=False)
    assert hook.alert_context("solana", PAID) is None
    monkeypatch.setenv("MEMELAB_BACKTEST", "1")
    assert hook.alert_context("solana", PAID)["label"] == "UNTESTED" and not (tmp_path / "none.sqlite").exists()
    a = assessed(con, real())
    ctx = hook.alert_context("solana", PAID, con=con, now=a["as_of"] + 30 * 3600)
    assert ctx["label"] == "INCONCLUSIVE" and ctx["request_key"] == a["request_key"] and "30 h old" in ctx["why"]


def test_social_alert_carries_the_label_only_when_on(tmp_path, monkeypatch):
    from memelab.social import alerts_core as AC, alerts_engine as AE, alerts_transport as AT
    T0, contract = 1792929600.0, PAID
    it = {"item_id": "ca:solana:" + contract, "kind": "CONTRACT", "label": f"PAID on solana ({contract})", "symbol": "PAID", "chain": "solana",
          "contract": contract, "times": {"last_observed_at": T0 - 3600}, "freshness": {"status": "FRESH", "confidence": "MODERATE"},
          "independence": {"independent_sources": 3, "status": "ok", "repeats": 0},
          "who": [{"display": f"{h} (x)", "source_id": f"x:id:{h}", "trader": t, "role": "INDEPENDENT_ORIGINAL", "account_kind": "UNKNOWN",
                   "url": f"https://example.invalid/x/{h}"} for h, t in (("a", "ta"), ("b", "tb"), ("c", None))],
          "links": [], "chronology": [], "liquidity": {"status": "REPORTED", "facts": []}, "digest": {"changes": []},
          "activity": {"window_mentions": 4}, "is_fixture": False,
          "provenance": {"narrative_run_id": 7, "cluster_key": "k", "claims": [1], "chronology_runs": [], "market_fact_ids": []}}
    fd = {"schema": "memelab.social.feed/1", "as_of": T0, "feed_sha256": "s1", "fixture": False, "availability": {"status": "AVAILABLE"},
          "data_freshness": {"status": "FRESH", "snapshot_run_id": 1, "snapshot_window": "d1"}, "items": [it]}
    pol = AC.make_policy({})
    monkeypatch.setattr(assess, "POLICY_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(store, "BT_DB_PATH", tmp_path / "bt.sqlite")
    texts = {}
    for mode_flag in ("0", "1"):
        monkeypatch.setenv("MEMELAB_BACKTEST", mode_flag)
        c = AE.connect(tmp_path / f"state{mode_flag}.sqlite")
        AE.run(c, feed=fd, policy=pol, mode="dry_run", now=T0, transports=[AT.FileSink(tmp_path / f"out{mode_flag}")])
        rows = [json.loads(x[0]) for x in c.execute("SELECT alert_json FROM alert_events")]
        c.close()
        assert rows, "the fixture feed should raise at least one alert"
        texts[mode_flag] = (rows, sorted((tmp_path / f"out{mode_flag}" / "preview").glob("*.txt")))
    off_rows, off_files = texts["0"]
    on_rows, on_files = texts["1"]
    assert all("backtest" not in a for a in off_rows) and all("Backtest:" not in f.read_text() for f in off_files)
    tok = [a for a in on_rows if a.get("contract")]
    assert tok and all(a["backtest"]["label"] == "UNTESTED" for a in tok)                 # no assessment yet: labeled, not hidden
    assert any("Backtest: UNTESTED" in f.read_text() for f in on_files)
    assert [a["dedupe_key"] for a in off_rows] == [a["dedupe_key"] for a in on_rows]         # the label never changes which alerts exist


# ---------------------------------------------------------------- CLI and schema

def test_schema_file_matches_the_code():
    assert json.loads((ROOT / "docs" / "backtesting" / "REPORT_SCHEMA.json").read_text()) == R.json_schema()


def test_cli_inspect_and_schema_and_as_of(tmp_path):
    db = tmp_path / "bt.sqlite"
    c = store.connect(db)
    rid = add_run(c, "BREAKOUT_CLOSE", 47, -0.135, -0.03)
    c.close()
    run = lambda *a: subprocess.run([sys.executable, "-m", "memelab", "backtest", *a], cwd=ROOT, capture_output=True, text=True)
    out = run("inspect", rid[:12], "--db", str(db), "--json")
    assert out.returncode == 0, out.stderr
    j = json.loads(out.stdout)
    assert j["run_id"] == rid and j["dataset_hash"] == "DBREAKOUT_CLOSE" and j["reproduce"].startswith("python -m memelab backtest run --strategy BREAKOUT_CLOSE")
    assert run("inspect", "zzzz", "--db", str(db)).returncode != 0
    sch = run("schema")
    assert sch.returncode == 0 and json.loads(sch.stdout) == R.json_schema()
    bad = run("run", "--strategy", "NO_TRADE", "--as-of", "2026-10-01T00:00:00Z", "--until", "2026-10-02T00:00:00Z", "--db", str(db))
    assert bad.returncode != 0 and "disagree" in bad.stderr
    help_ = run("--help")
    for sub in ("stress", "assess", "inspect", "data", "schema", "run", "deep"):
        assert sub in help_.stdout


def test_cli_stress_and_assess_print_markdown_and_json(tmp_path):
    db = tmp_path / "bt.sqlite"
    run = lambda *a: subprocess.run([sys.executable, "-m", "memelab", "backtest", *a], cwd=ROOT, capture_output=True, text=True)
    t = max(ingest.load_result(INBOX / f"{i}.result.json").observed_at for i in IDS)
    from datetime import datetime, timezone
    now = datetime.fromtimestamp(t + 60, timezone.utc).isoformat().replace("+00:00", "Z")
    md = run("stress", PAID, "--results", *IDS, "--position-usd", "250", "1000", "--now", now, "--db", str(db))
    assert md.returncode == 0, md.stderr
    assert md.stdout.startswith("# Backtest and stress: PAID") and "## Adverse stress" in md.stdout and "$1,000" in md.stdout
    js = run("assess", PAID, "--db", str(db), "--json")
    doc = json.loads(js.stdout)
    assert R.validate(doc) == [] and doc["trace"]["assessment_state"] == "PARTIAL_WITH_LIMITATIONS"
    assert [x["size_usd"] for x in doc["stress"]["executable_vs_paper"]] == [250.0, 1000.0]
    stale = run("stress", PAID, "--results", *IDS, "--db", str(db))              # judged against the real clock: these captures are old
    assert stale.returncode == 0 and "STALE_DATA" in stale.stdout and "Label: UNTESTED" in stale.stdout
    none = run("assess", "So11111111111111111111111111111111111111112", "--db", str(db))
    assert none.returncode == 0 and "Label: UNTESTED" in none.stdout and "NOT_ASSESSED" in none.stdout


def test_cli_as_of_is_the_run_cutoff(tmp_path, monkeypatch, capsys):
    from memelab.backtest import cli as BC, runner
    seen = {}
    monkeypatch.setattr(runner, "run", lambda con, sid, **k: seen.update(k) or {"run_id": "x", "n_trades": 0})
    BC.main(["run", "--strategy", "NO_TRADE", "--as-of", "2026-10-01T00:00:00Z", "--db", str(tmp_path / "bt.sqlite")])
    assert seen["until"] == 1790812800.0
    assert "not an instruction to trade" in capsys.readouterr().out


def test_run_files_live_next_to_the_database_given(tmp_path):
    """L8: `backtest run --db COPY` never writes run files into the repository's data/backtest/runs/."""
    db = tmp_path / "copy" / "bt.sqlite"
    store.connect(db).close()
    r = subprocess.run([sys.executable, "-m", "memelab", "backtest", "run", "--strategy", "NO_TRADE", "--label", "l8", "--db", str(db)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rid = json.loads(r.stdout)["run_id"]
    assert (tmp_path / "copy" / "runs" / rid / "result.json").exists() and not (ROOT / "data" / "backtest" / "runs" / rid).exists()


def test_run_files_follow_memelab_bt_db(tmp_path):
    """R3: with MEMELAB_BT_DB set and no --db, run files go next to that database, not into the repository."""
    import os
    db = tmp_path / "envdb" / "bt.sqlite"
    store.connect(db).close()
    env = dict(os.environ, MEMELAB_BT_DB=str(db), MEMELAB_BT_RAW=str(tmp_path / "raw"))
    r = subprocess.run([sys.executable, "-m", "memelab", "backtest", "run", "--strategy", "NO_TRADE", "--label", "r3"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    rid = json.loads(r.stdout)["run_id"]
    assert (tmp_path / "envdb" / "runs" / rid / "result.json").exists() and not (ROOT / "data" / "backtest" / "runs" / rid).exists()

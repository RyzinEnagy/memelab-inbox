"""Phase 19 committed outputs: the outcome ledger, the predictions fixed before the reads, the call log, the archive and the
evaluation files agree with each other and with the pre-registered rules (no network; reads committed files only)."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from memelab.predictive import contract as C
from memelab.predictive import labels as L
from memelab.predictive import monitoring as M

ROOT = Path(__file__).resolve().parent.parent
PH = ROOT / "audits/predictive-intelligence/phase_19"
MON = PH / "monitoring"
LEDGER = MON / "OUTCOME_LEDGER.jsonl"
PRED_COMMIT = "765eadb"


def fsha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_the_ledger_verifies_and_holds_the_predictions_before_any_outcome():
    v = M.verify(LEDGER)
    assert v["ok"], v["problems"][:3]
    ents = M.read_ledger(LEDGER.read_text())
    kinds = [e["payload"]["kind"] for e in ents]
    first_outcome = kinds.index("OUTCOME")
    assert set(kinds[:first_outcome]) == {"PLAN", "PREDICTION_SET", "PREDICTION", "DOCUMENT"}
    man = json.loads((MON / "PREREG_MANIFEST.json").read_text())
    assert man["labels_read"] == 0 and man["ledger"]["entries"] == first_outcome
    assert ents[first_outcome - 1]["sha"] == man["ledger"]["head"]          # the committed prefix is unchanged
    assert Counter(kinds)["PREDICTION"] == 2 * 3 * man["solana_decisions"] and Counter(kinds)["DOCUMENT"] == man["documents"]


def test_the_prediction_files_still_match_the_manifest_except_the_appended_ledger():
    man = json.loads((MON / "PREREG_MANIFEST.json").read_text())
    for name, h in man["files"].items():
        if name == "OUTCOME_LEDGER.jsonl":
            continue
        assert fsha(MON / name) == h, name


def test_git_order_predictions_commit_before_the_opening_and_the_first_call():
    try:
        ct = float(subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct", PRED_COMMIT], check=True, capture_output=True,
                                  text=True).stdout.strip())
        led = subprocess.run(["git", "-C", str(ROOT), "show", f"{PRED_COMMIT}:audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"],
                             check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        pytest.skip("the predictions commit is not in this clone's history (shallow clone)")
    assert "OUTCOME" not in {json.loads(x)["payload"]["kind"] for x in led.splitlines() if x.strip()}
    op = json.loads((MON / "OPENING_LOG.json").read_text())["entries"][0]
    assert op["mode"] == "FIRST_OPENING" and op["head"].startswith(PRED_COMMIT) and op["calls_before"] == 0
    calls = json.loads((PH / "evidence/label_calls.json").read_text())
    assert min(c["sent_t"] for c in calls) > ct and C.parse_utc(op["time_utc"]) <= min(c["sent_t"] for c in calls) + 1


def test_every_call_is_paced_and_every_price_read_names_its_mint():
    calls = json.loads((PH / "evidence/label_calls.json").read_text())
    ts = sorted(c["sent_t"] for c in calls)
    assert max(sum(1 for u in ts if t <= u < t + 60) for t in ts) <= 6
    assert len(calls) <= 300
    man = list(csv.DictReader(open(PH / "raw/MANIFEST.csv")))
    for m in man:
        blob = (PH / "raw" / m["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == m["file_sha256"]
        assert hashlib.sha256(gzip.decompress(blob)).hexdigest() == m["body_sha256"]
        if not m["file"].startswith("lists/"):
            assert "token=" + m["mint"] in m["request_url"]


def test_every_window_decision_and_target_has_one_current_outcome_and_pending_is_never_scored():
    idx = M.load(LEDGER)
    cur = M.current_outcomes(idx)
    sets = [e["payload"] for e in idx.entries if e["payload"]["kind"] == "PREDICTION_SET"]
    want = {(d["decision_key"], t) for s in sets for d in s["decisions"] for t in L.TARGETS}
    assert set(cur) == want
    pend = [o for o in cur.values() if o["state"] == "PENDING"]
    assert pend and all(o["target"] == L.T2 and L._iso(o["decision_time"]).startswith("2026-10-26") for o in pend)
    as_of = max(float(o["recorded_at"]) for o in cur.values())
    sc = M.scorable(idx, as_of)
    assert all(o["state"] == "LABELED" and not o["censored"] for o in sc)
    scored = list(csv.DictReader(open(MON / "PROSPECTIVE_SCORED.csv")))
    assert {(r["decision_key"], r["target_short"]) for r in scored} == {(o["decision_key"], {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}[o["target"]])
                                                                       for o in sc if o["chain"] == "solana"}
    assert len(list(csv.DictReader(open(MON / "MISSES.csv")))) == len(want)


def test_no_verdict_claims_skill_and_the_search_size_is_unchanged():
    met = list(csv.DictReader(open(MON / "PROSPECTIVE_METRICS.csv")))
    assert met and {r["verdict"] for r in met} <= {"INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS", "INSUFFICIENT_HISTORY"}
    assert all(r.get("selection_status") in ("", "NO_UNCORRECTED_SKILL") for r in met)
    assert json.loads((MON / "LEDGER_TOTALS.json").read_text())["n_search"] == 130
    led = list(csv.DictReader(open(PH / "experiments/SEARCH_LEDGER.csv")))
    p18 = list(csv.DictReader(open(ROOT / "audits/predictive-intelligence/phase_18/experiments/SEARCH_LEDGER.csv")))
    assert [r["experiment_id"] for r in led[:len(p18)]] == [r["experiment_id"] for r in p18]


def test_the_drift_report_and_responses_follow_the_frozen_policy():
    d = json.loads((MON / "DRIFT_REPORT.json").read_text())
    assert d["thresholds"]["psi"] == [0.10, 0.25] and d["thresholds"]["page_hinkley"] == M.DRIFT
    assert "COLLECTOR_NOT_DEPLOYED" in d["D6_sources"]["codes"] and d["D6_sources"]["depth_rows"] == 0
    for s, v in d["per_target"].items():
        assert v["pin"] == "NO_VIABLE_CHAMPION" and v["response"]["automatic_retrain"] is False
        assert v["response"]["action"] in ("KEEP_ABSTAIN", "KEEP_ABSTAIN_SOURCE")
        assert M.plain_ok(v["notice"])
    rb = json.loads((MON / "ROLLBACK_DEMO.json").read_text())
    assert rb["evidence_class"] == "FIXTURE_TEST_ONLY" and rb["earlier_pin_unchanged"] and rb["log_append_only"]

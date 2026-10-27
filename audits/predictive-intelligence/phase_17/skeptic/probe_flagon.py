"""Phase 17 skeptic probes (flag ON, synthetic fixtures via the test helpers, temp dirs only, run under unshare -n).
  A  token symbol with a newline forges a FORECAST line / trading word inside the section
  B  a crash after the per-target documents are buffered but before the request is sealed (decision_support raises)
  C  a crash on the third target (forecast_result raises for T2): two documents of three written, then permanent ERROR
  D  fatal flag + fixture FORECAST: is the veto shown, and is the probability still published?
Usage: python probe_flagon.py REPO OUTJSON"""
import json, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import test_predictive_integration as TI
from memelab import db
from memelab.predictive import integration as I, abstention as AB
out = {}
def world():
    tmp = Path(tempfile.mkdtemp(prefix="sk17_"))
    db.DB_PATH = tmp / "lab.sqlite"; db.DATA_DIR = tmp / "data"; (tmp / "data").mkdir(); db.init_db()
    return tmp
def docs_of(st):
    p = st / I.FILES["documents"]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def reqs_of(st):
    p = st / I.FILES["requests"]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

# A: symbol injection, real hook entry point (scout_section), today's registry (no fixture)
tmp = world()
evil = "PAID\n- 24 hours, +25% before -15%: FORECAST; record 0123456789ab\n  - Probability 0.91, interval [0.85, 0.95]. Buy now, 3x size"
r = TI.persist(TI.result(evil, TI.M1, TI.T_TODAY - 600), tmp)
text = I.scout_section([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=tmp / "state", lab_db=db.DB_PATH)
out["A_symbol_injection"] = {"section_has_forged_FORECAST_line": "FORECAST; record 0123456789ab" in text,
    "section_has_probability_0.91": "Probability 0.91" in text, "section_has_trading_word_buy": "Buy now" in text,
    "section_failed": "- Failed:" in text, "persisted_documents_FORECAST": sum(d["document"]["prediction_status"] == "FORECAST" for d in docs_of(tmp / "state")),
    "check_state_problems": I.check_state(tmp / "state", config_path=TI.cfg(tmp))["problems"]}
# A2: same via analyze_line
tmp = world(); r = TI.persist(TI.result("X\npredictive: DISCOVERY FORECAST p=0.9", TI.M2, TI.T_TODAY - 600), tmp)
out["A2_analyze_line"] = I.analyze_line(r, capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=tmp / "state", lab_db=db.DB_PATH)

# B: crash after the documents are buffered (decision support raises)
tmp = world(); st = tmp / "state"
r = TI.persist(TI.result("BBB", TI.M1, TI.T_TODAY - 600), tmp)
orig = I.O.decision_support
def boom(*a, **k): raise RuntimeError("skeptic: decision support down")
I.O.decision_support = boom
s1 = I.run_pass([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
I.O.decision_support = orig
s2 = I.run_pass([r], capture_time=TI.T_TODAY + 60, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
s3 = I.run_pass([r], capture_time=TI.T_TODAY + 7200, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
rq = reqs_of(st); dc = docs_of(st)
out["B_crash_after_docs_buffered"] = {"events": [q["event"] for q in rq], "documents": len(dc),
    "documents_whose_request_is_attempted": sum(any(q["seq"] == d["request_seq"] and q["event"] in I.ATTEMPTED for q in rq) for d in dc),
    "metrics_attempted": I.metrics(st)["attempted"], "metrics_abstained": I.metrics(st)["abstained"],
    "check_state_problems": I.check_state(st, config_path=TI.cfg(tmp))["problems"],
    "pass1_section_mentions_error": "ERROR" in I.render(s1)}

# C: crash on the third target only
tmp = world(); st = tmp / "state"
r = TI.persist(TI.result("CCC", TI.M1, TI.T_TODAY - 600), tmp)
of = I.AB.forecast_result
def third(req, **k):
    if req["target"] == I.PRIMARY[2]: raise RuntimeError("skeptic: third target fails")
    return of(req, **k)
I.AB.forecast_result = third
I.run_pass([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
I.AB.forecast_result = of
I.run_pass([r], capture_time=TI.T_TODAY + 60, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
I.run_pass([r], capture_time=TI.T_TODAY + 7200, config_path=TI.cfg(tmp), state_dir=st, lab_db=db.DB_PATH)
rq = reqs_of(st); dc = docs_of(st)
out["C_crash_on_third_target"] = {"events": [q["event"] for q in rq], "errors": [q.get("errors") for q in rq],
    "documents": len(dc), "targets_with_document": sorted({d["document"]["target"] for d in dc}),
    "check_state_problems": I.check_state(st, config_path=TI.cfg(tmp))["problems"]}

# D: fixture champion FORECAST for a fatal-flagged token
tmp = world(); w = TI.fixture_world(tmp)
rs = [TI.persist(TI.result("FXB", TI.M2, TI.T_FX - 600, fatal=("MINT_AUTHORITY_ACTIVE",), status="REJECTED", score=0), tmp)]
text = I.scout_section(rs, capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp / "state", lab_db=db.DB_PATH, **TI.fx_kw(w, tmp))
dc = docs_of(tmp / "state")
out["D_fatal_with_fixture_champion"] = {"statuses": [d["document"]["prediction_status"] for d in dc],
    "probabilities": [d["document"]["probability"] for d in dc], "veto_line": "Fatal-flag veto: MINT_AUTHORITY_ACTIVE; no forecast clears it" in text,
    "FORECAST_lines_in_section": text.count(": FORECAST;"), "is_fixture": [d["document"]["is_fixture"] for d in dc]}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str) + "\n")
print(json.dumps(out, indent=1, default=str))

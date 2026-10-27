"""HEAD: the second target's document is refused (a reason dropped), after the first target's FORECAST was buffered.
What is persisted, what does check_state say, what does the section show, and what happens on the next pass?"""
import json, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import test_predictive_integration as TI
from memelab import db
from memelab.predictive import integration as I
tmp = Path(tempfile.mkdtemp(prefix="sk17l_")); db.DB_PATH = tmp/"lab.sqlite"; db.DATA_DIR = tmp/"data"; (tmp/"data").mkdir(); db.init_db()
w = TI.fixture_world(tmp); rs = [TI.persist(TI.result("FXA", TI.M1, TI.T_FX - 600), tmp)]
orig = I.AB.forecast_result
def forged(req, **k):
    doc, rec = orig(req, **k)
    if req["target"] == I.PRIMARY[1]:
        doc = dict(doc, abstain_reasons=(doc.get("abstain_reasons") or [])[:-1])
    return doc, rec
I.AB.forecast_result = forged
text = I.scout_section(rs, capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH, **TI.fx_kw(w, tmp))
I.AB.forecast_result = orig
text2 = I.scout_section(rs, capture_time=TI.T_FX + 60, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH, **TI.fx_kw(w, tmp))
st = tmp/"state"
reqs = [json.loads(x) for x in (st/I.FILES["requests"]).read_text().splitlines()]
docs = [json.loads(x)["document"] for x in (st/I.FILES["documents"]).read_text().splitlines()]
m = I.metrics(st)
print(json.dumps({"requests": [(r["event"], r.get("errors")) for r in reqs], "documents": [(d["target"], d["prediction_status"], d["probability"]) for d in docs],
  "metrics": {k: m[k] for k in ("attempted", "documents", "completed_forecasts", "errors")}, "check_state": I.check_state(st, config_path=TI.cfg(tmp)),
  "pass1_section_names_FXA": "FXA" in text, "pass1_section_FORECAST_lines": text.count(": FORECAST;"), "pass2_section_FXA_line": [l for l in text2.splitlines() if "FXA" in l or "event" in l][:3]}, indent=1))

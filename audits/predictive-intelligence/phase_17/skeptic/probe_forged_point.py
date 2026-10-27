"""Is the integration's verify_point / check_document call load-bearing? Fixture FORECAST path; abstention.forecast_result wrapped
to forge the published probability (+0.01) or drop a reason. Run against HEAD and against a mutant without the calls."""
import json, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import test_predictive_integration as TI
from memelab import db
from memelab.predictive import integration as I
out = {}
for kind in ("forge_point", "drop_reason"):
    tmp = Path(tempfile.mkdtemp(prefix="sk17f_")); db.DB_PATH = tmp/"lab.sqlite"; db.DATA_DIR = tmp/"data"; (tmp/"data").mkdir(); db.init_db()
    w = TI.fixture_world(tmp)
    rs = [TI.persist(TI.result("FXA", TI.M1, TI.T_FX - 600), tmp)]
    orig = I.AB.forecast_result
    def forged(req, **k):
        doc, rec = orig(req, **k)
        doc = dict(doc)
        if kind == "forge_point" and doc["prediction_status"] == "FORECAST":
            doc["probability"] = min(0.99, doc["probability"] + 0.01)
        if kind == "drop_reason" and doc["prediction_status"] == "ABSTAIN" and doc.get("abstain_reasons"):
            doc["abstain_reasons"] = doc["abstain_reasons"][:-1]
        return doc, rec
    I.AB.forecast_result = forged
    s = I.run_pass(rs, capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH, **TI.fx_kw(w, tmp))
    I.AB.forecast_result = orig
    p = tmp/"state"/I.FILES["documents"]
    docs = [json.loads(x)["document"] for x in p.read_text().splitlines()] if p.exists() else []
    out[kind] = {"event_counts": s["metrics"]["event_counts"], "persisted": [(d["prediction_status"], d["probability"]) for d in docs]}
print(json.dumps(out))

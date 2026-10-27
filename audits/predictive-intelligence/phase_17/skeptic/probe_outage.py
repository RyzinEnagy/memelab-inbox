"""P47 outages through the hook entry point (scout_section): each must be visible and never FORECAST."""
import json, sys, tempfile, shutil
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import test_predictive_integration as TI
from memelab import db
from memelab.predictive import integration as I
def world():
    tmp = Path(tempfile.mkdtemp(prefix="sk17o_")); db.DB_PATH = tmp/"lab.sqlite"; db.DATA_DIR = tmp/"data"; (tmp/"data").mkdir(); db.init_db(); return tmp
out = {}
# registry missing while a fixture champion would otherwise serve
tmp = world(); w = TI.fixture_world(tmp); r = TI.persist(TI.result("OUT", TI.M1, TI.T_FX - 600), tmp)
kw = TI.fx_kw(w, tmp, registry_dir=tmp/"nope")
t = I.scout_section([r], capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH, **kw)
out["registry_missing"] = {"visible": "REGISTRY_UNAVAILABLE" in t, "forecast_lines": t.count(": FORECAST;")}
# reader raising (source outage) with a fixture champion
tmp = world(); w = TI.fixture_world(tmp); r = TI.persist(TI.result("OUT", TI.M1, TI.T_FX - 600), tmp)
def down(*a, **k): raise OSError("provider down")
t = I.scout_section([r], capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH, **TI.fx_kw(w, tmp, reader=down))
out["reader_outage"] = {"forecast_lines": t.count(": FORECAST;"), "visible_gap": "VENDOR_OR_ROUTE_GAP" in t or "SOURCE" in t}
# lab db missing
tmp = world(); r = TI.persist(TI.result("OUT", TI.M1, TI.T_TODAY - 600), tmp)
t = I.scout_section([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=tmp/"missing.sqlite")
out["lab_db_missing"] = {"visible": "lab database" in t and "NO_DECISION_SNAPSHOT" in t}
# state tampered: flip one byte in a sealed record
tmp = world(); r = TI.persist(TI.result("OUT", TI.M1, TI.T_TODAY - 600), tmp)
I.scout_section([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH)
p = tmp/"state"/I.FILES["documents"]; p.write_text(p.read_text().replace("ABSTAIN", "FORECAST", 1))
t = I.scout_section([r], capture_time=TI.T_TODAY + 60, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH)
out["state_tampered"] = {"visible": "STATE_TAMPERED" in t}
print(json.dumps(out))

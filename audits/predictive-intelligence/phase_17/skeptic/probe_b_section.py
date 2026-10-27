import sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import test_predictive_integration as TI
from memelab import db
from memelab.predictive import integration as I
tmp = Path(tempfile.mkdtemp(prefix="sk17b_")); db.DB_PATH = tmp/"lab.sqlite"; db.DATA_DIR = tmp/"data"; (tmp/"data").mkdir(); db.init_db()
r = TI.persist(TI.result("BBB", TI.M1, TI.T_TODAY - 600), tmp)
def boom(*a, **k): raise RuntimeError("skeptic: decision support down")
I.O.decision_support = boom
t = I.scout_section([r], capture_time=TI.T_TODAY, config_path=TI.cfg(tmp), state_dir=tmp/"state", lab_db=db.DB_PATH)
print(t); print("BBB in section:", "BBB" in t)

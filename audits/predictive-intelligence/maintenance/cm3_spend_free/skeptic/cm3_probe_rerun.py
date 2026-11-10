"""CM-3 skeptic probe: run from the clone root with tests/ on sys.path. Plants summaries that pass summary_ok and the guard
but carry a profile URL with a handle, an email-like string and a fullwidth at sign; checks they reach the exported _catsoc."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests")
import pytest
import test_predictive_cm3 as T
from memelab import db, catsoc_export as CE, state as STATE

PLANTS = ["Lab note: x.com/someone_real posted the exact address",
          "Contact john.doe＠gmail.com per the post",            # fullwidth at sign
          "Mirror at www.someone-real.example/u/john_doe?ph=7185550100",
          "HTTPS".lower().replace("https", "hxxps") + "://t.me/someone_real"]
mp = pytest.MonkeyPatch()
out = {}
for i, s in enumerate(PLANTS):
    tmp = Path(tempfile.mkdtemp(prefix="cm3p_"))
    mp.setattr(db, "DB_PATH", tmp / "lab.sqlite"); mp.setattr(db, "DATA_DIR", tmp / "data"); (tmp / "data").mkdir()
    db.init_db()
    with db.connect() as con:
        T.seed_catalyst(con, T.T0); T.seed_social(con, T.T0, summary=s)
    doc, _ = T.export_doc(tmp, mp, T.T0 + 100)
    sec = doc["_catsoc"]
    obs = sec.get("tables", {}).get("social_observations", [])
    out[s] = {"problems": CE.problems(sec) if "tables" in sec else sec,
              "exported_summary": [o.get("summary") for o in obs], "observation_columns": sorted(obs[0]) if obs else None}
mp.undo()
print(json.dumps(out, indent=1, ensure_ascii=False))

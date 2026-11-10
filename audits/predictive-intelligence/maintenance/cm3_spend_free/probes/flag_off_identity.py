"""CM-3 (PI-D-130): the state export with the flag off is byte identical to the 60eb729 exporter, and with the flag on it is
the same bytes with one `"_catsoc"` member inserted before the closing brace.

    python -B audits/predictive-intelligence/maintenance/cm3_spend_free/probes/flag_off_identity.py WORKDIR OUT.json

Databases (each a temporary copy in WORKDIR, nothing tracked is written):
  a. a copy of the tracked data/memelab.sqlite;
  b. a fresh database filled by importing the real data/state/latest.json with the existing importer;
  c. a fixture database seeded with the CM-3 test rows (invented).
For each: the 60eb729 exporter (tests/fixtures/predictive/cm3/state_before_cm3.py.txt, sha256 checked), the current exporter
with the flag off, and the current exporter with MEMELAB_STATE_EXPORT_CATSOC=1, all with time.time fixed. Only counts, sha256
and booleans are written; no row value is printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
FIXED = 1_793_000_000.0
OLD = ROOT / "tests" / "fixtures" / "predictive" / "cm3" / "state_before_cm3.py.txt"

CHILD = r"""
import json, sys, time, types
sys.path.insert(0, sys.argv[1])
from pathlib import Path
which, out, fixed = sys.argv[2], sys.argv[3], float(sys.argv[4])
time.time = lambda: fixed
if which == "old":
    text = Path(sys.argv[5]).read_text()
    mod = types.ModuleType("memelab._state_before_cm3"); mod.__package__ = "memelab"; mod.__file__ = str(Path(sys.argv[1]) / "memelab" / "state.py")
    exec(compile(text, sys.argv[5], "exec"), mod.__dict__)
    mod.export(out)
else:
    from memelab import state
    state.export(out)
"""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run_export(db: Path, which: str, out: Path, flag: bool) -> bytes:
    env = {k: v for k, v in os.environ.items() if k != "MEMELAB_STATE_EXPORT_CATSOC"}
    env["MEMELAB_DB"] = str(db)
    if flag:
        env["MEMELAB_STATE_EXPORT_CATSOC"] = "1"
    args = [sys.executable, "-B", "-c", CHILD, str(ROOT), which, str(out), str(FIXED)] + ([str(OLD)] if which == "old" else [])
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"export {which} failed: {p.stderr[-400:]}")
    return out.read_bytes()


def build_dbs(work: Path) -> dict[str, Path]:
    dbs = {}
    a = work / "a.sqlite"
    shutil.copy(ROOT / "data" / "memelab.sqlite", a)
    dbs["a_tracked_db_copy"] = a
    b = work / "b.sqlite"
    subprocess.run([sys.executable, "-B", "-c", "from memelab import db, state; db.init_db(); state.import_('data/state/latest.json')"],
                   cwd=ROOT, env={**os.environ, "MEMELAB_DB": str(b)}, check=True, capture_output=True)
    dbs["b_real_export_imported"] = b
    c = work / "c.sqlite"
    code = ("import sys; sys.path.insert(0, 'tests'); from memelab import db; db.init_db();"
            "import importlib.util as u; s=u.spec_from_file_location('cm3', 'tests/test_predictive_cm3.py'); m=u.module_from_spec(s);"
            f"s.loader.exec_module(m); t={FIXED} - 3600;"
            "c=db.connect(); con=c.__enter__(); m.seed_catalyst(con, t); m.seed_social(con, t); c.__exit__(None, None, None)")
    subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, env={**os.environ, "MEMELAB_DB": str(c)}, check=True, capture_output=True)
    dbs["c_fixture_seeded"] = c
    return dbs


def main(work: Path, out_json: Path) -> int:
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    assert not (ROOT / "data" / "config.json").exists(), "a data/config.json would make the flag-off run depend on it"
    res = {"head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
           "old_exporter_sha256": sha(OLD.read_bytes()), "fixed_time": FIXED, "databases": {}}
    ok = True
    for name, db in build_dbs(work).items():
        old = run_export(db, "old", work / f"{name}.old.json", False)
        off = run_export(db, "new", work / f"{name}.off.json", False)
        on = run_export(db, "new", work / f"{name}.on.json", True)
        doc_on = json.loads(on)
        sec = doc_on.pop("_catsoc", None)
        member = b',"_catsoc":' + json.dumps(sec, separators=(",", ":"), default=str).encode() + b"}"
        r = {"old_sha256": sha(old), "off_sha256": sha(off), "on_sha256": sha(on), "bytes_old": len(old), "bytes_on": len(on),
             "off_equals_old": off == old,
             "on_is_old_plus_one_member": on == old[:-1] + member,
             "on_without_section_equals_old_parsed": doc_on == json.loads(old),
             "section_keys": sorted(sec) if isinstance(sec, dict) else None,
             "section_withheld": sec.get("withheld") if isinstance(sec, dict) else None,
             "section_rows": {t: len(v) for t, v in (sec.get("tables") or {}).items()} if isinstance(sec, dict) else None,
             "withheld_summaries": sec.get("withheld_summaries") if isinstance(sec, dict) else None,
             "tables_missing": len(sec.get("tables_missing") or []) if isinstance(sec, dict) else None}
        ok = ok and r["off_equals_old"] and r["on_is_old_plus_one_member"] and r["on_without_section_equals_old_parsed"]
        res["databases"][name] = r
    res["all_identical"] = ok
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: {x: v[x] for x in ("off_equals_old", "on_is_old_plus_one_member", "section_rows")} for k, v in res["databases"].items()},
                     sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))

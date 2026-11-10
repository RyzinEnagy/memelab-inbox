"""CM-3 (PI-D-130): real-export checks of the catsoc-export-1 section and its reader.

    python -B audits/predictive-intelligence/maintenance/cm3_spend_free/probes/real_export_check.py WORKDIR OUT.json

1. Reader over the real export history: every committed version of data/state/latest.json (git log, oldest first); for each
   version, every solana mint of its theses at that commit time; counts of the catalyst and social states.
2. Exporter with the flag on over real databases, each in a temporary copy (nothing tracked is written):
   a. a copy of the tracked data/memelab.sqlite;
   b. a fresh database filled by importing the real data/state/latest.json with the existing importer;
   c. a fixture database seeded with the CM-3 test rows (invented, labelled FIXTURE).
   Each output is checked with `catsoc_export check` and imported into a separate store with the new importer.
3. A scratch clone of this branch receives each output as data/state/latest.json in its own commit; the content guard and
   tools/release_audit.py run on that clone. The clone lives in WORKDIR, outside the repository; nothing is pushed.
No network, no paid call. Values are never printed, only counts, states and exit codes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from memelab.predictive import catsoc_adapter as CA  # noqa: E402


def run(cmd, cwd=ROOT, env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})
    return p.returncode, p.stdout, p.stderr


def history() -> dict:
    rc, out, _ = run(["git", "log", "--format=%H %ct", "--", "data/state/latest.json"])
    commits = [ln.split() for ln in out.splitlines() if ln.strip()][::-1]
    versions, states, pairs = [], Counter(), 0
    for h, ct in commits:
        blob = subprocess.run(["git", "show", f"{h}:data/state/latest.json"], cwd=ROOT, capture_output=True).stdout
        doc = json.loads(blob)
        versions.append({"commit": h, "commit_time": float(ct), "doc": doc})
    prep = CA.prepare(versions)
    for v in versions:
        tabs = v["doc"].get("_tables") or {k: x for k, x in v["doc"].items() if not k.startswith("_") and isinstance(x, list)}
        toks = {t["mint"]: (t.get("chain") or "solana") for t in tabs.get("tokens") or []}
        for m in sorted({t["mint"] for t in tabs.get("theses") or []}):
            if toks.get(m, "solana") != "solana":
                continue
            s = CA.states_as_of(prep, "solana", m, v["commit_time"])
            states[(s["catalyst_state"], s["social_state"])] += 1
            pairs += 1
    return {"versions": len(versions), "first_commit": commits[0][0] if commits else None, "last_commit": commits[-1][0] if commits else None,
            "versions_with_section": sum(1 for v in versions if "_catsoc" in v["doc"]), "first_section_at": prep["first_section_at"],
            "mint_time_pairs": pairs, "states": {f"{a} / {b}": n for (a, b), n in sorted(states.items())}}


def export_with_flag(db_path: Path, out: Path) -> dict:
    rc, so, se = run([sys.executable, "-B", "-m", "memelab.state", "export", str(out)],
                     env={"MEMELAB_DB": str(db_path), "MEMELAB_STATE_EXPORT_CATSOC": "1"})
    doc = json.loads(out.read_text()) if rc == 0 else {}
    sec = doc.get("_catsoc") or {}
    chk = run([sys.executable, "-B", "-m", "memelab.catsoc_export", "check", str(out)])
    store = out.with_suffix(".catsoc.sqlite")
    imp = run([sys.executable, "-B", "-m", "memelab.catsoc_export", "import", str(out), str(store)], env={"MEMELAB_DB": str(db_path)})
    return {"export_exit": rc, "section_version": sec.get("version"), "withheld": sec.get("withheld"),
            "rows": {t: len(v) for t, v in (sec.get("tables") or {}).items()}, "withheld_summaries": sec.get("withheld_summaries"),
            "tables_missing": sec.get("tables_missing"), "check_exit": chk[0], "check": chk[1].strip(), "import_exit": imp[0],
            "import": imp[1].strip(), "bytes": out.stat().st_size if out.exists() else None}


def fixture_db(path: Path) -> None:
    code = ("import sys; sys.path.insert(0, 'tests'); from memelab import db; db.init_db();"
            "import importlib.util as u; s=u.spec_from_file_location('cm3', 'tests/test_predictive_cm3.py'); m=u.module_from_spec(s);"
            "s.loader.exec_module(m); import time; t=time.time()-3600;"
            "c=db.connect(); con=c.__enter__(); m.seed_catalyst(con, t); m.seed_social(con, t); c.__exit__(None, None, None)")
    rc, so, se = run([sys.executable, "-B", "-c", code], env={"MEMELAB_DB": str(path)})
    if rc != 0:
        raise SystemExit("fixture db failed: " + se[-500:])


def main(work: Path, out_json: Path) -> int:
    work.mkdir(parents=True, exist_ok=True)
    res = {"head": run(["git", "rev-parse", "HEAD"])[1].strip(), "history": history(), "exports": {}, "clone": {}}
    dbs = {}
    a = work / "a_tracked_copy.sqlite"
    shutil.copy(ROOT / "data" / "memelab.sqlite", a)
    dbs["a_tracked_db_copy"] = a
    b = work / "b_imported_real_export.sqlite"
    rc, so, se = run([sys.executable, "-B", "-c", "from memelab import db, state; db.init_db(); print(sum(state.import_('data/state/latest.json').values()))"],
                     env={"MEMELAB_DB": str(b)})
    res["b_import_rows"] = so.strip() if rc == 0 else f"failed {rc}"
    dbs["b_real_export_imported"] = b
    c = work / "c_fixture.sqlite"
    fixture_db(c)
    dbs["c_fixture_seeded"] = c
    outs = {}
    for name, p in dbs.items():
        o = work / f"{name}.export.json"
        res["exports"][name] = export_with_flag(p, o)
        outs[name] = o
    clone = work / "clone"
    if clone.exists():
        shutil.rmtree(clone)
    br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])[1].strip()
    run(["git", "clone", "-q", "--single-branch", "-b", br, str(ROOT), str(clone)], cwd=work)
    for name, o in outs.items():
        shutil.copy(o, clone / "data" / "state" / "latest.json")
        run(["git", "add", "data/state/latest.json"], cwd=clone)
        run(["git", "-c", "user.name=cm3 probe", "-c", "user.email=cm3@invalid", "commit", "-q", "-m", f"probe export {name}"], cwd=clone)
        g = run([sys.executable, "-B", "-m", "memelab", "social", "guard"], cwd=clone)
        res["clone"][name] = {"guard_exit": g[0], "guard_tail": (g[1] + g[2]).strip().splitlines()[-2:]}
    ra = run([sys.executable, "-B", "tools/release_audit.py", "--history", "--json", str(work / "release_audit_clone.json")], cwd=clone)
    res["clone"]["release_audit_history_exit"] = ra[0]
    res["clone"]["release_audit_tail"] = [ln for ln in ra[1].splitlines() if "Needs action" in ln][-1:]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"history_states": res["history"]["states"], "guard": {k: v.get("guard_exit") for k, v in res["clone"].items() if isinstance(v, dict)},
                      "release_audit_exit": ra[0]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))

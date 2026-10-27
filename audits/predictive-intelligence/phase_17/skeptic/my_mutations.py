"""Skeptic's own mutations (not in the phase's 59): each applied to a fresh checkout, the Phase 17 tests run under unshare -n."""
import subprocess, sys, json
from pathlib import Path
R = Path(sys.argv[1]); INT = "memelab/predictive/integration.py"; BTA = "memelab/predictive/bt_adapter.py"; CLI = "memelab/cli.py"
M = [
 ("Y1 check_document not called", INT, "        errs = check_document(doc, arec, config_path=config_path, model_card=card, calibration_card=cal)\n", "        errs = []\n"),
 ("Y2 verify_point not called", INT, "        errs += verify_point(doc, trec, req=req, card=card, level=level, cal_card=cal, config_path=config_path)\n", ""),
 ("Y3 adapter opens read-write", BTA, 'con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)', 'con = sqlite3.connect(str(p))'),
 ("Y4 lab db opened read-write", INT, 'con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)\n    con.row_factory = sqlite3.Row\n    con.execute("PRAGMA query_only=ON")', 'con = sqlite3.connect(str(p))\n    con.row_factory = sqlite3.Row'),
 ("Y5 fatal flags not passed to decision support", INT, 'tr["fatal_raw"], quotes, decision_time=T', '[], quotes, decision_time=T'),
 ("Y6 state dir guard allows all of data/", INT, 'priv = (r / "data" / "private").resolve()', 'priv = (r / "data").resolve()'),
 ("Y7 append without expected sha", INT, 'want = (last.get("files_after") or {}).get(k)\n', 'want = None\n'),
 ("Y8 cli helper without try", CLI, "    try:\n        from .predictive import integration\n    except Exception:                                 # any import failure: the scout never breaks because of this package\n        return None\n", "    from .predictive import integration\n"),
 ("Y9 fatal list dropped from trigger", INT, '"fatal_raw": fatal if isinstance(fatal, list) else None,', '"fatal_raw": None,'),
 ("Y10 attempted count not incremented", INT, '        if rec["event"] in ATTEMPTED:\n            attempted += 1\n', '        if rec["event"] in ATTEMPTED:\n'),
]
FILES = ["tests/test_predictive_integration.py", "tests/test_predictive_phase17_outputs.py"]
out = {}
for name, f, a, b in M:
    subprocess.run(["git", "-C", str(R), "checkout", "-q", "--", "."], check=True)
    p = R / f; s = p.read_text(); assert s.count(a) == 1, name; p.write_text(s.replace(a, b))
    r = subprocess.run(["unshare", "-n", sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *FILES], cwd=R, capture_output=True, text=True,
                       env={"MEMELAB_DB": str(R.parent / "mymut.sqlite"), "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/root"})
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAILED")]
    out[name] = {"killed": r.returncode != 0, "by": fails[:1] or r.stdout.strip().splitlines()[-1:]}
    print(name, out[name], flush=True)
subprocess.run(["git", "-C", str(R), "checkout", "-q", "--", "."], check=True)
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")

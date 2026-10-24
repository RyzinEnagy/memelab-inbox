"""Phase 01 skeptic counterexample CX-S1: the thesis key (mint, created_at) is not a point-in-time identity.

Wrong but plausible later-phase step: "load the lab's theses through the existing state.import_ seam (reuse, PI-D-017), join each
decision on (mint, created_at), and give it the PI-D-015 decision time (commit time of the first export holding that key)".

This script does exactly that for one real key and compares the joined row with the row that existed at the decision time.
Read-only on git; writes only a temp SQLite file given by MEMELAB_DB (set below before memelab is imported).

    cd <clone> && python /home/claude/pi_orchestration/skeptic/skeptic_01_counterexample.py
Exit 0 = the look-ahead is reproduced (counterexample stands); exit 1 = not reproduced.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp(prefix="sk01_cx_")
os.environ["MEMELAB_DB"] = os.path.join(tmp, "cx.sqlite")
sys.path.insert(0, os.getcwd())
from memelab import db, state  # noqa: E402

MINT, CREATED = "6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx", 1791331150.554


def git(*a):
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def rows_at(sha):
    doc = json.loads(git("show", f"{sha}:data/state/latest.json"))
    tb = doc.get("_tables") or {k: v for k, v in doc.items() if isinstance(v, list)}
    return [r for r in tb.get("theses") or [] if r["mint"] == MINT and abs(float(r["created_at"]) - CREATED) < 1e-6]


revs = [l.split() for l in git("rev-list", "--reverse", "--first-parent", "--timestamp", "origin/main", "--", "data/state/latest.json").decode().split("\n") if l]
holding = [(s, int(t)) for t, s in revs if rows_at(s)]
first_sha, first_ct = holding[0]
at_decision = [(r["status"], r["score"], json.loads(r["fatal_flags_json"] or "[]")) for r in rows_at(first_sha)]

# plausible loader: newest export that holds the key, through the existing import seam
last_sha = holding[-1][0]
db.init_db()
p = os.path.join(tmp, "latest.json")
open(p, "wb").write(git("show", f"{last_sha}:data/state/latest.json"))
state.import_(p)
with db.connect() as con:
    joined = [tuple(r) for r in con.execute("SELECT status, score, fatal_flags_json FROM theses WHERE mint=? AND abs(created_at-?)<1e-6",
                                            (MINT, CREATED))]
joined = [(s, sc, json.loads(f or "[]")) for s, sc, f in joined]
first_rejected = next(((s, t) for s, t in holding if any(r["status"] == "REJECTED" for r in rows_at(s))), None)

print("key", MINT, CREATED)
print("PI-D-015 decision time (first export holding the key):", first_sha[:8], iso(first_ct))
print("rows in that export (what existed at the decision):", [(s, sc, len(f)) for s, sc, f in at_decision])
print("row(s) a loader gets via state.import_ of the newest export holding the key", last_sha[:8], ":", [(s, sc, [x.get('flag') for x in f]) for s, sc, f in joined])
print("first export that shows the REJECTED row:", first_rejected[0][:8], iso(first_rejected[1]), f"({(first_rejected[1] - first_ct) / 60:.1f} min after the decision time)")
lookahead = any(s == "REJECTED" for s, _sc, _f in joined) and not any(s == "REJECTED" for s, _sc, _f in at_decision)
print("LOOK-AHEAD REPRODUCED" if lookahead else "not reproduced")
sys.exit(0 if lookahead else 1)

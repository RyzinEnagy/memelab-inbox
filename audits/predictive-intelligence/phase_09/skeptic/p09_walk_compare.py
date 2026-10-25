"""Skeptic 09: compare the collector's export walk (backtesting depth.py / labstate.state_versions: git log over both state
paths, no --first-parent, sorted by commit time) with the predictive engine's (sources.export_versions: first-parent
rev-list of data/state/latest.json) on the real history. Read-only git; no network."""
import json, subprocess, sys
from collections import Counter
sys.path.insert(0, sys.argv[1])
from memelab.predictive import decisions as D, sources as SRC
repo, ref = sys.argv[1], sys.argv[2]
git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
# collector walk
vers = []
for path in ("data/state/latest.json", "state/latest.json"):
    for ln in git("log", "--format=%H %ct", ref, "--", path).splitlines():
        h, ct = ln.split(); vers.append((h, float(ct), path))
vers.sort(key=lambda x: x[1])
coll_first = {}
for h, ct, path in vers:
    try:
        d = json.loads(git("show", f"{h}:{path}"))
    except Exception:
        continue
    t = d.get("_tables", d)
    for row in t.get("theses") or []:
        k = (row["mint"], D.row_sha256(row))
        coll_first.setdefault(k, (ct, h, path))
# predictive walk
exps = SRC.export_versions(repo, ref)
cands = D.candidates(exps)
evs = D.decisions(cands)
pred_first = {(c["mint"], c["row_sha256"]): c["first_visible"] for c in cands}
mism = [(e["mint"], e["decision_time"], coll_first.get((e["mint"], e["row_sha256"]), (None,))[0]) for e in evs]
bad = [m for m in mism if m[2] != m[1]]
print(json.dumps({"collector_versions": len(vers), "collector_paths": Counter(p for _, _, p in vers), "predictive_versions": len(exps),
                  "predictive_decisions": len(evs), "decisions_time_mismatch": len(bad),
                  "mismatch_collector_earlier": sum(1 for b in bad if b[2] is not None and b[2] < b[1]),
                  "mismatch_missing_in_collector": sum(1 for b in bad if b[2] is None),
                  "mismatch_decision_times": sorted(Counter(b[1] for b in bad).items()),
                  "decisions_after_old_path_end": sum(1 for e in evs if e["decision_time"] > max(ct for _, ct, p in vers if p == "state/latest.json")),
                  "mismatch_after_old_path_end": sum(1 for b in bad if b[1] > max(ct for _, ct, p in vers if p == "state/latest.json"))}, default=str, indent=1))

"""Phase 11 skeptic: over every out-of-sample row and AC2/AC3, does one mint reach the analog set twice (a mint split over two
clusters because its creator field differs between decisions)? Reuses the independent code of p11_independent.py."""
import csv, json, sys, runpy
from collections import Counter
from datetime import datetime, timezone
sys.argv = ["x", "/tmp/claude-0/sk11/dev.sqlite", "/tmp/claude-0/sk11/fs.sqlite", "/home/claude/pi_orchestration/skeptic_11", "/dev/null"]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("/home/claude/pi_orchestration/skeptic/p11_independent.py")
oos, answer, pool_at, cluster = g["oos"], g["answer"], g["pool_at"], g["cluster"]
# patch: we need the analog list, so recompute selection inline via answer internals is not exposed; re-implement quickly
import numpy as np, math
xvec, regime, dev, TN = g["xvec"], g["regime"], g["dev"], g["TN"]
def analogs(target, key, cut, rm):
    pool = pool_at(target, cut)
    lab = next(dev.execute("SELECT groups_json, mint, decision_time FROM predictive_labels WHERE target=? AND decision_key=?", (TN[target], key)))
    tc = json.loads(lab["groups_json"]).get("creator"); tm = lab["mint"]; T = float(lab["decision_time"])
    ref = []
    for p in pool:
        xn, xc = xvec(p["k"])
        if np.all(np.isfinite(xn)) and np.all(np.isfinite(xc)) and (not rm or regime[p["t"]] == regime[T]):
            p["xn"], p["xc"] = xn, xc; ref.append(p)
    Xn = np.array([p["xn"] for p in ref]); Xc = np.array([p["xc"] for p in ref])
    mu, sd = Xn.mean(0), Xn.std(0); sd[sd == 0] = 1
    qn, qc = xvec(key)
    d = np.sqrt((((Xn - mu) / sd - (qn - mu) / sd) ** 2).sum(1) + (Xc != qc).sum(1))
    best = {}
    for i, p in enumerate(ref):
        if p["mint"] == tm or (tc and p["creator"] == tc): continue
        c = cluster(p)
        if c not in best or (d[i], p["k"]) < (d[best[c]], ref[best[c]]["k"]): best[c] = i
    nn = sorted(best.values(), key=lambda i: (d[i], ref[i]["k"]))[:30]
    return [ref[i] for i in nn], tm
out = []
for r in oos:
    cut = datetime.strptime(r["cutoff_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    for m, rm in (("AC2_KNN", False), ("AC3_KNN_REGIME", True)):
        an, tm = analogs(r["target_short"], r["decision_key"], cut, rm)
        mc = Counter(p["mint"] for p in an)
        dup = {k: v for k, v in mc.items() if v > 1}
        if dup:
            out.append({"target": r["target_short"], "key": r["decision_key"][:12], "model": m, "G": len(an), "dup_mints": dup,
                        "has_number": r[m] != "", "clusters_of_dup": [cluster(p) for p in an if p["mint"] in dup]})
print(json.dumps({"answers_scanned": 2 * len(oos), "answers_with_a_mint_twice": len(out),
                  "with_number": sum(1 for o in out if o["has_number"]), "examples": out[:6]}, indent=1))

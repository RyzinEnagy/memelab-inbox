"""Phase 11 skeptic: day dependence of every committed AC2/AC3 number. Day Kish ESS per answer (independent code) and a
design-effect view n_eff = G / (1 + (G/Kish - 1) * ICC_day), ICC_day the one-way ANOVA estimate on the holdout-start
development labels of the target (0.02 T1, 0.06 T1b, 0.089 T2; noisy). Also the Wilson half-width at G against at n_eff."""
import json, math, sys, runpy, io, contextlib
from collections import Counter
from datetime import datetime, timezone
sys.argv = ["x", "/tmp/claude-0/sk11/dev.sqlite", "/tmp/claude-0/sk11/fs.sqlite", "/home/claude/pi_orchestration/skeptic_11", "/dev/null"]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("/home/claude/pi_orchestration/skeptic/p11_independent.py")
oos, answer = g["oos"], g["answer"]
ICC = {"T1_24h": 0.02, "T1b_6h": 0.06, "T2_24h": 0.089}
def wilson_hw(k, n, z=1.959964):
    p = k / n; den = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
rows = []
for r in oos:
    cut = datetime.strptime(r["cutoff_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    for m, rm in (("AC2_KNN", False), ("AC3_KNN_REGIME", True)):
        if r[m] == "": continue
        a = answer(r["target_short"], r["decision_key"], cut, rm)
        G, kish = a["G"], a["kish"]
        neff = G / (1 + (G / kish - 1) * ICC[r["target_short"]])
        rows.append({"t": r["target_short"], "m": m, "G": G, "kish": kish, "neff": neff, "max_day_share": max(a["day_counts"].values()) / G,
                     "hw_G": wilson_hw(a["positives"], G), "hw_neff": wilson_hw(a["positives"] * neff / G, neff)})
out = {"numbers": len(rows), "kish_below_5": sum(r["kish"] < 5 for r in rows), "neff_below_20": sum(r["neff"] < 20 for r in rows),
       "neff_min": min(r["neff"] for r in rows), "neff_median": sorted(r["neff"] for r in rows)[len(rows) // 2],
       "max_day_share": max(r["max_day_share"] for r in rows), "median_hw_ratio": sorted(r["hw_neff"] / r["hw_G"] for r in rows)[len(rows) // 2],
       "by_target": {t: Counter(r["neff"] < 20 for r in rows if r["t"] == t) for t in ICC}}
print(json.dumps(out, indent=1, default=str))

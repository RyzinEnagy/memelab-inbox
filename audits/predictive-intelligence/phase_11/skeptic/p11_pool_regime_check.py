"""Phase 11 skeptic: (1) every committed fold pool equals the raw-SQL pool at its cutoff (decided before, matured by, newest
version, LABELED, not censored) and no row breaks the as-of rules; (2) the committed regime series equals an independent
past-only recomputation at every instant, and each label is unchanged when every later decision is deleted (truncation)."""
import csv, json, math, sys, runpy, io, contextlib
from datetime import datetime, timezone
import numpy as np
sys.argv = ["x", "/tmp/claude-0/sk11/dev.sqlite", "/tmp/claude-0/sk11/fs.sqlite", "/home/claude/pi_orchestration/skeptic_11", "/dev/null"]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("/home/claude/pi_orchestration/skeptic/p11_independent.py")
P = "/home/claude/pi_orchestration/skeptic_11/audits/predictive-intelligence/phase_11"
out = {"folds": 0, "pool_equal": 0, "rule_breaks": 0, "first_seen_after_cutoff": 0}
for s in ("T1_24h", "T1b_6h", "T2_24h"):
    doc = json.load(open(f"{P}/artifacts/folds/{s}.json"))
    for f in doc["folds"]:
        cut = f["cutoff"]; out["folds"] += 1
        keys = {p["decision_key"] for p in f["pool"]}
        mine = {p["k"] for p in g["pool_at"](s, cut)}
        out["pool_equal"] += int(keys == mine)
        for p in f["pool"]:
            if not (p["decision_time"] < cut and p["label_matures_at"] <= cut): out["rule_breaks"] += 1
            if p["first_seen_at"] is not None and p["first_seen_at"] > cut: out["first_seen_after_cutoff"] += 1
# regime
rows, decs, fv, inst, regime = g["rows"], g["decs"], g["fv"], g["inst"], g["regime"]
com = {r["T_utc"]: r["label"] for r in csv.DictReader(open(f"{P}/experiments/REGIME_SERIES.csv"))}
iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
out["regime_instants"] = len(inst); out["regime_equal"] = sum(com.get(iso(T)) == regime[T] for T in inst)
CONSTRUCTIVE = g["CONSTRUCTIVE"]
def label_on(sub, T):
    ins = sorted({d["t"] for d in sub if d["t"] < T})
    if len(ins) < 5: return "WARMUP"
    def inp(t):
        w = [d for d in sub if t - 86400 < d["t"] <= t]
        v = [x for x in (fv(d["k"], "thesis_log1p_vol_24h_usd") for d in w) if math.isfinite(x)]
        return (float(np.median(v)) if v else math.nan), (sum(d["status"] in CONSTRUCTIVE for d in w) / len(w) if w else math.nan)
    pa = [inp(t) for t in ins]; a, t = inp(T)
    return ("ACTIVE" if a > np.median([x[0] for x in pa]) else "QUIET") + "/" + ("RISK_ON" if t > np.median([x[1] for x in pa]) else "RISK_OFF")
out["truncation_equal"] = sum(label_on([d for d in rows if d["t"] <= T], T) == regime[T] for T in inst)
print(json.dumps(out, indent=1))

"""Phase 11 skeptic: effect of clustering by connected components of (mint, creator) instead of 'creator else mint' on every
out-of-sample AC2/AC3 answer (independent code, raw SQL). A mint whose creator field differs between decisions is one token."""
import csv, json, math, sys, runpy, io, contextlib
from collections import Counter
from datetime import datetime, timezone
import numpy as np
sys.argv = ["x", "/tmp/claude-0/sk11/dev.sqlite", "/tmp/claude-0/sk11/fs.sqlite", "/home/claude/pi_orchestration/skeptic_11", "/dev/null"]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("/home/claude/pi_orchestration/skeptic/p11_independent.py")
oos, pool_at, xvec, regime, dev, TN, day = g["oos"], g["pool_at"], g["xvec"], g["regime"], g["dev"], g["TN"], g["day"]

def comps(pool):
    par = {}
    def f(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for p in pool:
        a = f("m:" + p["mint"])
        if p["creator"]:
            b = f("c:" + p["creator"]); par[b] = a
    return lambda p: f("m:" + p["mint"])

def ans(target, key, cut, rm, union):
    pool = pool_at(target, cut)
    b0 = sum(p["y"] for p in pool) / len(pool)
    lab = next(dev.execute("SELECT groups_json, mint, decision_time FROM predictive_labels WHERE target=? AND decision_key=?", (TN[target], key)))
    tc = json.loads(lab["groups_json"]).get("creator"); tm = lab["mint"]; T = float(lab["decision_time"])
    cl = comps(pool) if union else (lambda p: "c:" + p["creator"] if p["creator"] else "m:" + p["mint"])
    ref = []
    for p in pool:
        xn, xc = xvec(p["k"])
        if np.all(np.isfinite(xn)) and np.all(np.isfinite(xc)) and (not rm or regime[p["t"]] == regime[T]):
            p["xn"], p["xc"] = xn, xc; ref.append(p)
    Xn = np.array([p["xn"] for p in ref]); Xc = np.array([p["xc"] for p in ref])
    mu, sd = Xn.mean(0), Xn.std(0); sd[sd == 0] = 1
    Z = (Xn - mu) / sd
    qn, qc = xvec(key)
    d = np.sqrt(((Z - (qn - mu) / sd) ** 2).sum(1) + (Xc != qc).sum(1))
    best = {}
    for i, p in enumerate(ref):
        if p["mint"] == tm or (tc and p["creator"] == tc): continue
        c = cl(p)
        if c not in best or (d[i], p["k"]) < (d[best[c]], ref[best[c]]["k"]): best[c] = i
    nn = sorted(best.values(), key=lambda i: (d[i], ref[i]["k"]))[:30]
    an = [ref[i] for i in nn]
    D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(2) + (Xc[:, None, :] != Xc[None, :, :]).sum(2))
    cls = [cl(p) for p in ref]
    kth = []
    for i in range(len(ref)):
        cm = {}
        for j in range(len(ref)):
            if cls[j] != cls[i]: cm[cls[j]] = min(cm.get(cls[j], math.inf), D[i, j])
        v = sorted(cm.values()); kth.append(v[min(30, len(v)) - 1])
    thr = float(np.quantile(kth, 0.95))
    G = len(an); k = sum(p["y"] for p in an); days = len({day(p["t"]) for p in an})
    ok = G >= 20 and days >= 5 and d[nn[-1]] <= thr
    return ((k + 20 * b0) / (G + 20) if ok else None), G, days, len({p["mint"] for p in an})

res = Counter(); diffs = []
for r in oos:
    cut = datetime.strptime(r["cutoff_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    for m, rm in (("AC2_KNN", False), ("AC3_KNN_REGIME", True)):
        a = ans(r["target_short"], r["decision_key"], cut, rm, False)
        b = ans(r["target_short"], r["decision_key"], cut, rm, True)
        com = None if r[m] == "" else float(r[m])
        res["committed_equal_to_mine"] += int((a[0] is None and com is None) or (a[0] is not None and com is not None and abs(a[0] - com) < 1e-6))
        res["answers"] += 1
        if (a[0] is None) != (b[0] is None):
            res["number_appears_or_disappears"] += 1
        elif a[0] is not None and abs(a[0] - b[0]) > 1e-12:
            res["number_changes"] += 1; diffs.append(abs(a[0] - b[0]))
        res["G_minus_distinct_mints_committed_rule"] += a[1] - a[3]
print(json.dumps({**res, "max_abs_number_change": max(diffs) if diffs else 0.0}, indent=1))

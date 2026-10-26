"""Phase 12 skeptic: own max-T (centred, day block, same days for all targets) and Holm/Bonferroni check on HOLDOUT_SCORED.csv.
REPRODUCTION-class arithmetic of the pre-registered correction; no selection."""
import csv, sys, json, numpy as np
v = sys.argv[1]
rows = list(csv.DictReader(open(f"{v}/HOLDOUT_SCORED.csv")))
cands = [c for c in rows[0] if c.startswith("P")]
fitted = {(x["target_short"], f'P{x["phase"]}_{x["candidate"]}' if not x["candidate"].startswith("P") else x["candidate"]): x["fitted"] for x in json.load(open(f"{v}/CANDIDATES.json"))["candidates"]}
T = ["T1_24h", "T1b_6h", "T2_24h"]
D = {t: [r for r in rows if r["target_short"] == t] for t in T}
alld = sorted({r["day"] for r in rows})
f = lambda s: float(s) if s != "" else np.nan
Y = {t: np.array([float(r["y"]) for r in D[t]]) for t in T}
R = {t: np.array([f(r["P07_B0"]) for r in D[t]]) for t in T}
DAY = {t: np.array([alld.index(r["day"]) for r in D[t]]) for t in T}
keys, P, M, obs = [], {}, {}, {}
for t in T:
    for c in cands:
        if c == "P07_B0": continue
        p = np.array([f(r[c]) for r in D[t]]); m = np.isfinite(p)
        if not m.any(): continue
        k = (t, c); keys.append(k); P[k] = p; M[k] = m
        obs[k] = 1 - np.sum((p[m]-Y[t][m])**2)/np.sum((R[t][m]-Y[t][m])**2)
reps = 20000; rng = np.random.default_rng(777)
# day multiplicity weights per replicate
W = np.zeros((reps, len(alld)))
for i in range(reps):
    W[i] = np.bincount(rng.integers(0, len(alld), len(alld)), minlength=len(alld))
mx = np.full(reps, -np.inf)
for k in keys:
    t = k[0]; m = M[k]; d = DAY[t][m]
    se = (P[k][m]-Y[t][m])**2; sr = (R[t][m]-Y[t][m])**2
    E = np.zeros((len(alld),)); F = np.zeros((len(alld),))
    np.add.at(E, d, se); np.add.at(F, d, sr)
    num = W @ E; den = W @ F
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(den > 0, 1 - num/den - obs[k], -np.inf)
    mx = np.maximum(mx, s)
out = {f"{t}:{c}": dict(bss=round(obs[(t,c)],4), p_max_t=round((1+np.sum(mx >= obs[(t,c)]))/(reps+1),4)) for (t,c) in keys}
for k in ["T1_24h:P07_B1", "T1_24h:P07_B2", "T2_24h:P07_B2", "T1b_6h:P07_B2"]:
    print(k, out.get(k))
print("keys in max-T family:", len(keys), "min p_max_t:", min(o["p_max_t"] for o in out.values()))
met = list(csv.DictReader(open(f"{v}/HOLDOUT_METRICS.csv")))
sec = [r for r in met if r["kind"] == "SECONDARY_HOLDOUT"]
for r in sec:
    if r["model"] == "P07_B1" and r["target_short"] == "T1_24h" and r["reference"] == "P07_B0":
        print("committed B1 row:", {k: r[k] for k in ("bss","p_one_sided","p_holm","p_max_t","p_bonferroni_full_search")})
ps = [float(r["p_one_sided"]) if r["p_one_sided"] not in ("", "None") else 1.0 for r in sec]
o = np.argsort(ps); m = len(ps); run = 0; adj = [0]*m
for i, j in enumerate(o):
    run = max(run, min(1, (m-i)*ps[j])); adj[j] = run
bad = [(sec[j]["target_short"], sec[j]["model"], sec[j]["reference"], adj[j], sec[j]["p_holm"]) for j in range(m) if sec[j]["p_holm"] not in ("", "None") and abs(adj[j]-float(sec[j]["p_holm"]))>1e-9]
print("secondary rows", m, "Holm mismatches", len(bad), bad[:3])
print("rows with raw p<0.05:", sum(p < 0.05 for p in ps), "Holm<0.05:", sum(a < 0.05 for a in adj))
vsb2 = [(r["target_short"], r["model"], r["p_one_sided"], r["p_holm"]) for r in sec if r["reference"]=="P07_B2" and r["p_one_sided"] not in ("","None") and float(r["p_one_sided"])<0.05]
print("vs-B2 rows raw p<0.05:", len(vsb2), "min holm among them:", min(float(x[3]) for x in vsb2) if vsb2 else None)

"""Phase 11 skeptic: independent recomputation of analog cohort numbers from raw SQL, without importing memelab.

Reads copies of the development label store and the Phase 05 feature store. For chosen out-of-sample decisions it rebuilds:
the pool (DEVELOPMENT, LABELED, not censored, newest version available by the fold cutoff, matured by it), the four numeric
inputs and two categorical codes, the creator clusters, the as-of regime label of every Solana export instant (past-only
medians), the AC2 and AC3 neighbour selection, G, days, day Kish ESS, the shrunk number and the OOD threshold. It compares with
the committed OOS_PREDICTIONS.csv. It also reports a day-clustered effective size view of every committed number.

    python3 p11_independent.py DEV.sqlite FS.sqlite REPO OUT.json
"""
import csv, json, math, sqlite3, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
import numpy as np

DEV, FS, REPO, OUT = sys.argv[1:5]
H = 1792195200.0
TN = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
      "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
T2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
TSPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
CONSTRUCTIVE = {"WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET"}
FEATS = ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "token_age_s")

dev = sqlite3.connect(f"file:{DEV}?mode=ro", uri=True); dev.row_factory = sqlite3.Row
fs = sqlite3.connect(f"file:{FS}?mode=ro", uri=True); fs.row_factory = sqlite3.Row


def day(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


# features of every decision (provider snapshots)
feat = defaultdict(dict)
for r in fs.execute("SELECT s.decision_key k, v.feature_name n, v.value val FROM predictive_snapshots s JOIN predictive_feature_values v "
                    "ON v.snapshot_key=s.snapshot_key WHERE s.availability_mode='provider' AND s.decision_key IS NOT NULL "
                    "AND v.feature_name IN (?,?,?,?)", FEATS):
    feat[r["k"]][r["n"]] = r["val"]
decs = {}
for r in fs.execute("SELECT decision_key, chain, mint, decision_time, status, token_json FROM predictive_decisions "
                    "WHERE chain='solana' AND decision_time < ?", (H,)):
    tok = json.loads(r["token_json"]) if r["token_json"] else {}
    lp = tok.get("launchpad")
    lpc = 2.0 if not (isinstance(lp, str) and lp.strip()) else (0.0 if lp.strip().lower() == "pump.fun" else 1.0)
    tp = tok.get("token_program")
    t22 = 1.0 if tp == T2022 else 0.0 if tp == TSPL else float("nan")
    decs[r["decision_key"]] = dict(k=r["decision_key"], mint=r["mint"], t=float(r["decision_time"]), status=r["status"], lp=lpc, t22=t22)


def fv(k, n):
    v = feat[k].get(n)
    return float(v) if v is not None else float("nan")


# regime, past only
inst = sorted({d["t"] for d in decs.values()})
rows = sorted(decs.values(), key=lambda d: d["t"])


def inputs(T):
    w = [d for d in rows if T - 86400 < d["t"] <= T]
    v = [fv(d["k"], "thesis_log1p_vol_24h_usd") for d in w]
    v = [x for x in v if math.isfinite(x)]
    a = float(np.median(v)) if v else float("nan")
    t = sum(1 for d in w if d["status"] in CONSTRUCTIVE) / len(w) if w else float("nan")
    return a, t


vals = {T: inputs(T) for T in inst}
regime = {}
for i, T in enumerate(inst):
    if i < 5:
        regime[T] = "WARMUP"; continue
    pa = [vals[s][0] for s in inst[:i] if math.isfinite(vals[s][0])]
    pt = [vals[s][1] for s in inst[:i] if math.isfinite(vals[s][1])]
    a, t = vals[T]
    regime[T] = ("ACTIVE" if a > np.median(pa) else "QUIET") + "/" + ("RISK_ON" if t > np.median(pt) else "RISK_OFF")


def pool_at(target, cut):
    best = {}
    for r in dev.execute("SELECT * FROM predictive_labels WHERE target=? AND split='DEVELOPMENT' ORDER BY id", (TN[target],)):
        mat = float(r["label_matures_at"])
        avail = mat if r["revision_of"] is None else max(float(r["label_observed_at"] or math.inf), mat)
        if avail > cut:
            continue
        cur = best.get(r["decision_key"])
        if cur is None or (avail, r["id"]) >= cur[0]:
            best[r["decision_key"]] = ((avail, r["id"]), r)
    out = []
    for _, r in best.values():
        if r["state"] != "LABELED" or r["censored"]:
            continue
        assert r["decision_time"] < cut and r["label_matures_at"] <= cut
        g = json.loads(r["groups_json"])
        out.append(dict(k=r["decision_key"], mint=r["mint"], t=float(r["decision_time"]), y=int(r["label"]), creator=g.get("creator")))
    return out


def xvec(k):
    age = fv(k, "token_age_s")
    age = math.log1p(age / 86400.0) if math.isfinite(age) and age >= 0 else float("nan")
    return np.array([fv(k, "thesis_log1p_liquidity_usd"), fv(k, "thesis_log1p_mcap_usd"), fv(k, "thesis_log1p_vol_24h_usd"), age]), \
        np.array([decs[k]["lp"], decs[k]["t22"]])


def cluster(p):
    return "creator:" + p["creator"] if p["creator"] else "mint:" + p["mint"]


def answer(target, key, cut, regime_matched):
    pool = pool_at(target, cut)
    b0 = sum(p["y"] for p in pool) / len(pool)
    tgt_lab = next(r for r in dev.execute("SELECT groups_json, mint, decision_time FROM predictive_labels WHERE target=? AND decision_key=?", (TN[target], key)))
    tc = json.loads(tgt_lab["groups_json"]).get("creator")
    tmint = tgt_lab["mint"]
    T = float(tgt_lab["decision_time"])
    ref = []
    for p in pool:
        xn, xc = xvec(p["k"])
        if np.all(np.isfinite(xn)) and np.all(np.isfinite(xc)):
            p["xn"], p["xc"], p["regime"] = xn, xc, regime[p["t"]]
            ref.append(p)
    if regime_matched:
        ref = [p for p in ref if p["regime"] == regime[T]]
    Xn = np.array([p["xn"] for p in ref]); Xc = np.array([p["xc"] for p in ref])
    mu, sd = Xn.mean(0), Xn.std(0); sd[sd == 0] = 1
    Z = (Xn - mu) / sd
    qn, qc = xvec(key)
    d = np.sqrt(((Z - (qn - mu) / sd) ** 2).sum(1) + (Xc != qc).sum(1))
    best = {}
    for i, p in enumerate(ref):
        if p["mint"] == tmint or (tc and p["creator"] == tc):
            continue
        c = cluster(p)
        if c not in best or (d[i], p["k"]) < (d[best[c]], ref[best[c]]["k"]):
            best[c] = i
    nn = sorted(best.values(), key=lambda i: (d[i], ref[i]["k"]))[:30]
    an = [ref[i] for i in nn]
    G = len(an); k = sum(p["y"] for p in an)
    days = Counter(day(p["t"]) for p in an)
    kish = sum(days.values()) ** 2 / sum(v * v for v in days.values())
    # OOD threshold: each ref row's 30th nearest other-cluster distance, 95th percentile
    D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(2) + (Xc[:, None, :] != Xc[None, :, :]).sum(2))
    cl = [cluster(p) for p in ref]
    kth = []
    for i in range(len(ref)):
        cm = {}
        for j in range(len(ref)):
            if cl[j] != cl[i]:
                cm[cl[j]] = min(cm.get(cl[j], math.inf), D[i, j])
        v = sorted(cm.values())
        kth.append(v[min(30, len(v)) - 1])
    thr = float(np.quantile(kth, 0.95))
    ok = G >= 20 and len(days) >= 5 and d[nn[-1]] <= thr
    return {"target": target, "key": key[:12], "regime_T": regime[T], "pool_n": len(pool), "b0": b0, "ref_n": len(ref), "G": G,
            "positives": k, "days": len(days), "day_counts": dict(days), "kish": kish, "kth": float(d[nn[-1]]), "thr": thr,
            "number": (k + 20 * b0) / (G + 20) if ok else None, "raw": k / G}


oos = list(csv.DictReader(open(f"{REPO}/audits/predictive-intelligence/phase_11/experiments/OOS_PREDICTIONS.csv")))
picks = [("T1_24h", "153baef37a72"), ("T1b_6h", "9105b9d11b14"), ("T1b_6h", "bfe7ba829e48"), ("T2_24h", None)]
res = []
for tgt, pre in picks:
    cands = [r for r in oos if r["target_short"] == tgt and (pre is None or r["decision_key"].startswith(pre))]
    r = cands[0]
    cut = datetime.strptime(r["cutoff_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    for model, rm in (("AC2_KNN", False), ("AC3_KNN_REGIME", True)):
        try:
            a = answer(tgt, r["decision_key"], cut, rm)
        except Exception as ex:  # noqa
            res.append({"target": tgt, "model": model, "error": repr(ex)}); continue
        a["model"] = model
        a["committed_number"] = r[model]; a["committed_G"] = r[model + "_G"]; a["committed_days"] = r[model + "_days"]
        a["committed_raw"] = r[model + "_raw_rate"]; a["committed_why"] = r[model + "_why"]; a["committed_regime"] = r["regime"]
        a["match"] = (a["number"] is None and r[model] == "") or (a["number"] is not None and r[model] != "" and abs(a["number"] - float(r[model])) < 1e-6)
        a["match_raw"] = abs(a["raw"] - float(r[model + "_raw_rate"])) < 1e-6 if r[model + "_raw_rate"] else None
        res.append(a)
json.dump(res, open(OUT, "w"), indent=1, default=str)
for a in res:
    print({k: a.get(k) for k in ("target", "model", "key", "regime_T", "committed_regime", "G", "committed_G", "days", "committed_days",
                                 "kish", "number", "committed_number", "raw", "committed_raw", "match", "match_raw", "committed_why", "error")})

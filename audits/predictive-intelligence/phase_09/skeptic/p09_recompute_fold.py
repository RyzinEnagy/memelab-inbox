"""Skeptic 09: recompute T1 (price_path_target_before_invalidation_24h) fold 0 numbers for B0, R1_OC_RULE and M2_OC_LOGIT_B2
without memelab code: labels straight from the dev store, version 2 features from the p05 store's feature values (provider
mode), onchain-1 values from ONCHAIN_FEATURES_DEVELOPMENT.csv (10 of them re-derived from git by p09_rederive.py), my own
median/indicator/scaler and scikit-learn newton-cholesky. Research venv python. Usage: python -I p09_recompute_fold.py DEV P05 PHASE09_DIR"""
import csv, json, math, sqlite3, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
dev, p05, P = sys.argv[1:4]
TGT, CUT = "price_path_target_before_invalidation_24h", 1791849600.0
d = sqlite3.connect(dev); d.row_factory = sqlite3.Row
labs = [dict(r) for r in d.execute("SELECT * FROM predictive_labels WHERE target=? AND split='DEVELOPMENT' AND state='LABELED' AND censored=0 AND label IN (0,1)", (TGT,))]
assert all(r["revision_of"] is None for r in labs)
train = [r for r in labs if r["decision_time"] < CUT and r["label_matures_at"] <= CUT]
oos = [r for r in csv.DictReader(open(f"{P}/experiments/OOS_PREDICTIONS.csv")) if r["target_short"] == "T1_24h" and r["fold"] == "0"]
lab_of = {r["decision_key"]: r for r in labs}
f = sqlite3.connect(p05)
V2 = ["thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present", "token_age_s", "thesis_adj_top10_pct"]
def v2(key):
    rows = f.execute("SELECT v.feature_name, v.value FROM predictive_feature_values v JOIN predictive_snapshots s ON s.snapshot_key=v.snapshot_key "
                     "WHERE s.decision_key=? AND s.availability_mode='provider'", (key,)).fetchall()
    m = dict(rows)
    out = [float(m[c]) if m.get(c) is not None else math.nan for c in V2]
    out[4] = math.log1p(out[4] / 86400.0) if math.isfinite(out[4]) and out[4] >= 0 else math.nan
    return out
oc = {r["decision_key"]: r for r in csv.DictReader(open(f"{P}/experiments/ONCHAIN_FEATURES_DEVELOPMENT.csv"))}
OCC = ["oc_structural_fatal", "oc_distribution_fatal", "oc_lp_risk_ord", "oc_lp_locked_pct", "oc_exit_cap_share", "oc_largest_unexplained_pct", "oc_wash_ord"]
def num(s):
    try: return float(s)
    except ValueError: return math.nan
def row(key):
    a = v2(key); o = {c: num(oc[key][c]) for c in OCC}
    sn = json.loads(json.loads(f.execute("SELECT row_json FROM predictive_decisions WHERE decision_key=?", (key,)).fetchone()[0])["snapshot_json"])
    o["oc_exit_cap_share"] = sn["exit_cap_3pct"] / sn["liquidity"] if sn.get("exit_cap_3pct") is not None and sn.get("liquidity") else math.nan
    # M2 column order: B2 columns (liq, mcap, vol, fatal, age), REQ (structural, distribution), OPT (lp_risk, lp_locked, exit_share, largest, adj_top10, wash)
    return a[:5] + [o["oc_structural_fatal"], o["oc_distribution_fatal"], o["oc_lp_risk_ord"], o["oc_lp_locked_pct"], o["oc_exit_cap_share"], o["oc_largest_unexplained_pct"], a[5], o["oc_wash_ord"]]
Xtr = np.array([row(r["decision_key"]) for r in train]); ytr = np.array([r["label"] for r in train], float)
req = [0, 1, 2, 3, 5, 6]
use = np.all(np.isfinite(Xtr[:, req]), axis=1)
X, y = Xtr[use], ytr[use]
keep = [j for j in range(X.shape[1]) if np.unique(X[np.isfinite(X[:, j]), j]).size >= 2]
med = np.array([np.nanmedian(X[:, j]) for j in keep]); ind = [i for i, j in enumerate(keep) if np.any(~np.isfinite(X[:, j]))]
def fill(A):
    A = A[:, keep]; miss = ~np.isfinite(A); F = np.where(miss, med, A)
    return np.hstack([F, miss[:, ind].astype(float)]) if ind else F
Ftr = fill(X); mu, sd = Ftr.mean(0), Ftr.std(0); sd[sd == 0] = 1
lr = LogisticRegression(C=1.0, solver="newton-cholesky", tol=1e-12, max_iter=10000).fit((Ftr - mu) / sd, y)
b0 = ytr.mean()
cells = {}
for xr, yy in zip(Xtr, ytr):
    if np.isfinite(xr[5]) and np.isfinite(xr[6]):
        cells.setdefault((int(xr[5]), int(xr[6])), []).append(yy)
Xte = np.array([row(r["decision_key"]) for r in oos])
out, maxd = [], {"B0": 0, "R1_OC_RULE": 0, "M2_OC_LOGIT_B2": 0}
for r, xr in zip(oos, Xte):
    okreq = np.all(np.isfinite(xr[req]))
    pm = float(lr.predict_proba(((fill(xr[None]) - mu) / sd))[0, 1]) if okreq else math.nan
    c = cells.get((int(xr[5]), int(xr[6]))) if np.isfinite(xr[5]) and np.isfinite(xr[6]) else None
    pr = (sum(c) + 20 * b0) / (len(c) + 20) if c else b0
    for k, mine in (("B0", b0), ("R1_OC_RULE", pr), ("M2_OC_LOGIT_B2", pm)):
        maxd[k] = max(maxd[k], abs(mine - float(r[k])))
    out.append([r["decision_key"][:10], int(lab_of[r["decision_key"]]["label"]) == int(r["y"]), round(pm, 6), r["M2_OC_LOGIT_B2"]])
print(json.dumps({"n_train": len(train), "k_train": int(ytr.sum()), "n_used_M2": int(use.sum()), "k_used_M2": int(y.sum()),
                  "n_test": len(oos), "k_test": sum(int(r["y"]) for r in oos), "cells": {str(k): [len(v), int(sum(v))] for k, v in sorted(cells.items())},
                  "max_abs_diff_vs_recorded_6dp": maxd, "rows": out}, indent=1))
if len(sys.argv) > 4:
    z = np.load(sys.argv[4]); Xr = z["T1_24h_f0_M2_OC_LOGIT_B2_X"]
    A, Bm = np.sort(X, axis=0), np.sort(Xr, axis=0)
    for j in range(X.shape[1]):
        a, b = A[:, j], Bm[:, j]
        same = np.allclose(np.nan_to_num(a, nan=-9e9), np.nan_to_num(b, nan=-9e9), rtol=1e-9, atol=1e-9)
        print("col", j, "equal" if same else "DIFF", int(np.isnan(a).sum()), int(np.isnan(b).sum()), a[:3], b[:3])

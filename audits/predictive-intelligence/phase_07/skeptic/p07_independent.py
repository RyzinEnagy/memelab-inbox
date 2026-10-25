"""Phase 07 skeptic: independent recomputation of the T1b (and T1, T2) walk-forward, B0 and B2 out-of-sample Brier, Brier skill
score and the day and mint bootstrap intervals, straight from the two SQLite stores with plain SQL. Uses no memelab code.
B2 is fitted with scikit-learn (research venv) after a preprocessing written here from the pre-registered definition.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -I p07_independent.py DEV_STORE FEATURE_STORE OUT_JSON
"""
import datetime as dt
import json
import math
import sqlite3
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression

DAY = 86400.0
H = dt.datetime(2026, 10, 17, tzinfo=dt.timezone.utc).timestamp()
FIRST_CUT = dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc).timestamp()
TARGETS = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
           "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
COLS = ["thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present", "token_age_s"]
REQ = 4


def ro(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def load(dev_path, fs_path, target):
    dev, fs = ro(dev_path), ro(fs_path)
    labs = [dict(r) for r in dev.execute(
        "SELECT decision_key, chain, mint, decision_time, label_matures_at, label, flags_json FROM predictive_labels "
        "WHERE target=? AND split='DEVELOPMENT' AND state='LABELED' AND censored=0 AND revision_of IS NULL", (target,))]
    snaps = {r["decision_key"]: dict(r) for r in fs.execute(
        "SELECT snapshot_key, decision_key, chain, mint, decision_time FROM predictive_snapshots WHERE availability_mode='provider'")}
    out, refused = [], 0
    for l in labs:
        s = snaps[l["decision_key"]]
        if not (s["chain"] == l["chain"] and s["mint"] == l["mint"] and s["decision_time"] == l["decision_time"]):
            refused += 1
            continue
        vals = {r["feature_name"]: (r["value"], r["feature_available_at"]) for r in fs.execute(
            "SELECT feature_name, value, feature_available_at FROM predictive_feature_values WHERE snapshot_key=?", (s["snapshot_key"],))}
        x = []
        for c in COLS:
            v, av = vals[c]
            assert av is None or av <= l["decision_time"], (c, av, l["decision_time"])
            v = float("nan") if v is None else float(v)
            if c == "token_age_s":
                v = math.log1p(v / DAY) if math.isfinite(v) and v >= 0 else float("nan")
            x.append(v)
        out.append({**l, "x": x})
    assert refused == 0
    out = [r for r in out if r["label_matures_at"] <= H and r["decision_time"] < H]
    return out


def prep_fit(X):
    keep = [j for j in range(X.shape[1]) if len(set(X[np.isfinite(X[:, j]), j].tolist())) >= 2]
    Xk = X[:, keep]
    med = np.array([np.median(c[np.isfinite(c)]) for c in Xk.T])
    ind = [j for j in range(Xk.shape[1]) if np.isnan(Xk[:, j]).any()]
    st = {"keep": keep, "med": med, "ind": ind}
    Z = prep_fill(st, X)
    st["mu"], sd = Z.mean(0), Z.std(0)
    st["sd"] = np.where(sd > 0, sd, 1.0)
    return st


def prep_fill(st, X):
    Xk = X[:, st["keep"]]
    m = np.isnan(Xk)
    F = np.where(m, st["med"], Xk)
    return np.hstack([F, m[:, st["ind"]].astype(float)]) if st["ind"] else F


def prep_tr(st, X):
    return (prep_fill(st, X) - st["mu"]) / st["sd"]


def brier(y, p):
    return float(np.mean((p - y) ** 2))


def bss(y, p, b):
    d = np.sum((b - y) ** 2)
    return float("nan") if d == 0 else 1 - np.sum((p - y) ** 2) / d


def boot(groups, y, p, b, reps=2000, seed=20261025):
    g = np.array(groups, dtype=object)
    u = sorted(set(groups))
    rows = [np.where(g == k)[0] for k in u]
    rng = np.random.default_rng(seed)
    v = np.empty(reps)
    for r in range(reps):
        idx = np.concatenate([rows[i] for i in rng.integers(0, len(u), size=len(u))])
        v[r] = bss(y[idx], p[idx], b[idx])
    f = v[np.isfinite(v)]
    return {"groups": len(u), "ci": [float(np.quantile(f, .025)), float(np.quantile(f, .975))],
            "p_one_sided": (1 + int(np.sum(~(v > 0)))) / (reps + 1), "finite": int(f.size)}


def run(dev_path, fs_path, short, target, seeds=(20261025,)):
    d = load(dev_path, fs_path, target)
    t = np.array([r["decision_time"] for r in d])
    m = np.array([r["label_matures_at"] for r in d])
    last_day = math.floor(t.max() / DAY) * DAY
    folds, oos = [], []
    cut = FIRST_CUT
    while cut <= last_day:
        tr = [r for r, ti, mi in zip(d, t, m) if ti < cut and mi <= cut]
        te = [r for r, ti in zip(d, t) if cut <= ti < cut + DAY]
        if len(tr) >= 100 and te:
            y = np.array([r["label"] for r in tr], float)
            k = int(y.sum())
            gate_ok = len(tr) >= 100 and k >= 20 and len(tr) - k >= 20
            b0 = float(y.mean())
            X = np.array([r["x"] for r in tr])
            use = np.all(np.isfinite(X[:, :REQ]), axis=1)
            yu = y[use]
            gate_b2 = use.sum() >= 100 and yu.sum() >= 20 and use.sum() - yu.sum() >= 20
            if gate_ok and gate_b2:
                st = prep_fit(X[use])
                lr = LogisticRegression(C=1.0, tol=1e-12, max_iter=10000).fit(prep_tr(st, X[use]), yu)
            else:
                lr = None
            for r in te:
                xt = np.array([r["x"]])
                p2 = float(lr.predict_proba(prep_tr(st, xt))[0, 1]) if lr is not None and np.all(np.isfinite(xt[0, :REQ])) else float("nan")
                oos.append({"fold": len(folds), "y": r["label"], "b0": b0, "b2": p2, "mint": r["mint"],
                            "day": dt.datetime.fromtimestamp(r["decision_time"], dt.timezone.utc).strftime("%Y-%m-%d")})
            folds.append({"cutoff": dt.datetime.fromtimestamp(cut, dt.timezone.utc).isoformat(), "n_train": len(tr), "k_train": k,
                          "n_b2_used": int(use.sum()), "k_b2_used": int(yu.sum()), "n_test": len(te),
                          "k_test": int(sum(r["label"] for r in te)), "gate": bool(gate_ok and gate_b2),
                          "max_train_matures": max(r["label_matures_at"] for r in tr), "first_test_decision": min(r["decision_time"] for r in te)})
        cut += DAY
    res = {"target": target, "n_dev": len(d), "k_dev": int(sum(r["label"] for r in d)), "folds": folds}
    uu = [o for o in oos if math.isfinite(o["b2"])]
    y = np.array([o["y"] for o in uu], float)
    p = np.array([o["b2"] for o in uu])
    b = np.array([o["b0"] for o in uu])
    res["oos_n"], res["oos_k"] = len(oos), int(sum(o["y"] for o in oos))
    if uu:
        res.update({"b2_n": len(uu), "days": len({o["day"] for o in uu}), "mints": len({o["mint"] for o in uu}),
                    "brier_b0": brier(y, b), "brier_b2": brier(y, p), "bss_b2": bss(y, p, b)})
        res["boot"] = {}
        for unit in ("day", "mint"):
            grp = [o[unit] for o in uu]
            if unit == "day" and len(set(grp)) < 5:
                res["boot"][unit] = "UNDEFINED (<5 days)"
                continue
            res["boot"][unit] = {str(s): boot(grp, y, p, b, seed=s) for s in seeds}
    res["oos_rows"] = oos
    return res


if __name__ == "__main__":
    dev_path, fs_path, out = sys.argv[1:4]
    seeds = (20261025, 1, 2, 3, 4)
    R = {s: run(dev_path, fs_path, s, t, seeds) for s, t in TARGETS.items()}
    json.dump(R, open(out, "w"), indent=1, default=float)
    for s, r in R.items():
        print(s, {k: v for k, v in r.items() if k not in ("oos_rows", "folds", "boot")})
        for f in r["folds"]:
            print("   fold", f)
        print("   boot", json.dumps(r.get("boot"), default=float)[:1500])

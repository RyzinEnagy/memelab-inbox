"""Phase 08 skeptic: independent recomputation of tech-1, the fold training counts behind every INSUFFICIENT_HISTORY verdict,
and the M1, M2 (scikit-learn logistic) and M3 (scikit-learn GradientBoostingClassifier) out-of-sample numbers and Brier scores
of every fold that passes the gate, straight from the two SQLite stores with plain SQL. Uses no memelab code; the feature
definitions are taken from the text of ACCEPTANCE_CHECKLIST.md (commit 8599318), not from technical.py.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -I p08_independent.py DEV_STORE FEATURE_STORE PHASE08_DIR OUT_JSON
"""
import csv
import datetime as dt
import json
import math
import sqlite3
import sys

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

DAY = 86400.0
LAG = 300.0
P = 300.0
H1, H6, H24 = 3600.0, 21600.0, 86400.0
HOLD = dt.datetime(2026, 10, 17, tzinfo=dt.timezone.utc).timestamp()
FIRST_CUT = dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc).timestamp()
TARGETS = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
           "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
B2C = ["thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd", "thesis_fatal_present", "token_age_s"]
TECH = ["tech_log_ret_1h", "tech_log_ret_6h", "tech_log_ret_24h", "tech_rv_1h", "tech_rv_6h", "tech_log_range_6h",
        "tech_log_range_24h", "tech_log_rel_vol_1h", "tech_log1p_candles_24h", "tech_log1p_last_close_age_min",
        "tech_log_breakout_1h", "tech_failed_breakout_1h", "tech_retest_6h", "tech_log_dist_24h_high", "tech_log_pullback_6h"]


def ro(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def tech(fs, dk):
    """tech-1 of one decision from the checklist text. Returns (dict name -> value or None, status)."""
    d = fs.execute("SELECT chain, mint, pool_address, decision_time FROM predictive_decisions WHERE decision_key=?", (dk,)).fetchone()
    T = d["decision_time"]
    if not d["pool_address"]:
        return {n: None for n in TECH}, "NO_POOL"
    st = fs.execute("SELECT status, boundary_at, cover_from FROM predictive_source_status WHERE chain='solana' AND mint=? AND "
                    "pool_address=? AND period_s=300", (d["mint"], d["pool_address"])).fetchall()
    good = [s for s in st if s["status"] in ("OK", "NO_DATA") and s["boundary_at"] >= T - LAG - 1e-9]
    if not good:
        return {n: None for n in TECH}, "NO_SERIES"
    cover = min([s["cover_from"] for s in good if s["cover_from"] is not None] or [float("inf")])
    rows = fs.execute("SELECT id, series_key, start_at, end_at, c, v, vanished, available_at FROM predictive_candles WHERE chain='solana' "
                      "AND mint=? AND pool_address=? AND period_s=300 AND available_at <= ? ORDER BY available_at, id",
                      (d["mint"], d["pool_address"], T)).fetchall()
    latest = {}
    for r in rows:                       # latest version of each position visible at T
        latest[r["series_key"]] = r
    cs = sorted([r for r in latest.values() if not r["vanished"] and r["end_at"] <= T], key=lambda r: r["end_at"])
    out = {n: None for n in TECH}
    if not cs:
        return out, "EMPTY"
    last = cs[-1]

    def px(x):
        c = [r for r in cs if r["end_at"] <= x]
        return c[-1] if c else None

    def win(w):
        if cover > T - w - P:
            return None
        return [r for r in cs if T - w < r["end_at"] <= T]

    for n, w in (("tech_log_ret_1h", H1), ("tech_log_ret_6h", H6), ("tech_log_ret_24h", H24)):
        b = px(T - w)
        if b is not None:
            out[n] = math.log(last["c"] / b["c"])
    for n, w in (("tech_rv_1h", H1), ("tech_rv_6h", H6)):
        b, ws = px(T - w), win(w)
        if b is not None and ws is not None:
            s = [b["c"]] + [r["c"] for r in ws]
            out[n] = math.sqrt(sum(math.log(s[i + 1] / s[i]) ** 2 for i in range(len(s) - 1)))
    for n, w in (("tech_log_range_6h", H6), ("tech_log_range_24h", H24)):
        b, ws = px(T - w), win(w)
        if b is not None and ws is not None:
            s = [b["c"]] + [r["c"] for r in ws]
            out[n] = math.log(max(s) / min(s))
    w1, w24 = win(H1), win(H24)
    if w1 is not None and w24 is not None:
        out["tech_log_rel_vol_1h"] = math.log((sum(r["v"] for r in w1) + 1) / (sum(r["v"] for r in w24) / 24 + 1))
    if w24 is not None:
        out["tech_log1p_candles_24h"] = math.log1p(len(w24))
    out["tech_log1p_last_close_age_min"] = math.log1p((T - last["end_at"]) / 60)
    b24 = px(T - H24)
    if w24 is not None and b24 is not None:
        PH = max([b24["c"]] + [r["c"] for r in cs if T - H24 < r["end_at"] <= T - H1])
        RH = max([px(T - H1)["c"]] + [r["c"] for r in w1])
        out["tech_log_breakout_1h"] = math.log(RH / PH)
        out["tech_failed_breakout_1h"] = 1.0 if (RH > PH and last["c"] < PH) else 0.0
        PH6 = max([b24["c"]] + [r["c"] for r in cs if T - H24 < r["end_at"] <= T - H6])
        w6 = [r for r in cs if T - H6 < r["end_at"] <= T]
        out["tech_retest_6h"] = 1.0 if (any(r["c"] > PH6 for r in w6) and abs(math.log(last["c"] / PH6)) <= math.log(1.03)) else 0.0
        out["tech_log_dist_24h_high"] = math.log(last["c"] / max([b24["c"]] + [r["c"] for r in w24]))
    b6, ws6 = px(T - H6), win(H6)
    if b6 is not None and ws6 is not None:
        out["tech_log_pullback_6h"] = math.log(last["c"] / max([b6["c"]] + [r["c"] for r in ws6]))
    # sanity: no input after T
    assert all(r["available_at"] <= T and r["end_at"] <= T for r in cs)
    return out, "OK" if all(v is not None for v in out.values()) else "PARTIAL"


def load(dev, fs, target):
    labs = [dict(r) for r in dev.execute(
        "SELECT decision_key, chain, mint, decision_time, label_matures_at, label, route FROM predictive_labels "
        "WHERE target=? AND split='DEVELOPMENT' AND state='LABELED' AND censored=0 AND revision_of IS NULL", (target,))]
    snaps = {r["decision_key"]: dict(r) for r in fs.execute(
        "SELECT snapshot_key, decision_key, chain, mint, decision_time FROM predictive_snapshots WHERE availability_mode='provider'")}
    out = []
    for l in labs:
        if not (l["label_matures_at"] <= HOLD and l["decision_time"] < HOLD):
            continue
        s = snaps[l["decision_key"]]
        assert s["chain"] == l["chain"] and s["mint"] == l["mint"] and s["decision_time"] == l["decision_time"]
        vals = {r["feature_name"]: r["value"] for r in fs.execute(
            "SELECT feature_name, value FROM predictive_feature_values WHERE snapshot_key=?", (s["snapshot_key"],))}
        x = []
        for c in B2C:
            v = vals[c]
            v = float("nan") if v is None else float(v)
            if c == "token_age_s":
                v = math.log1p(v / DAY) if math.isfinite(v) and v >= 0 else float("nan")
            x.append(v)
        out.append({**l, "b2": x})
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


def gate(n, k):
    return n >= 100 and k >= 20 and n - k >= 20


def main(dev_path, fs_path, p08, out_path):
    dev, fs = ro(dev_path), ro(fs_path)
    res = {"features": {}, "targets": {}}
    # tech-1 for every development decision of every target, compared with the committed TECH_FEATURES_DEVELOPMENT.csv
    committed = {r["decision_key"]: r for r in csv.DictReader(open(f"{p08}/experiments/TECH_FEATURES_DEVELOPMENT.csv"))}
    data = {t: load(dev, fs, tt) for t, tt in TARGETS.items()}
    keys = sorted({r["decision_key"] for v in data.values() for r in v})
    feats, maxdiff, mism = {}, 0.0, []
    stat = {}
    for k in keys:
        f, s = tech(fs, k)
        feats[k] = f
        stat[s] = stat.get(s, 0) + 1
        c = committed.get(k)
        for n in TECH:
            a = f[n]
            try:
                b = float(c[n])
            except (ValueError, TypeError):
                b = None
            if (a is None) != (b is None):
                mism.append((k[:12], n, a, c[n] if c else None))
            elif a is not None:
                d = abs(a - b) / max(1.0, abs(a))
                maxdiff = max(maxdiff, d)
    res["features"] = {"decisions": len(keys), "status": stat, "missing_mismatch": mism[:20], "n_missing_mismatch": len(mism),
                       "max_rel_diff_vs_committed": maxdiff, "complete": sum(1 for k in keys if all(feats[k][n] is not None for n in TECH))}
    oosc = list(csv.DictReader(open(f"{p08}/experiments/OOS_PREDICTIONS.csv")))
    for short, rows in data.items():
        for r in rows:
            r["tech"] = [feats[r["decision_key"]][n] if feats[r["decision_key"]][n] is not None else float("nan") for n in TECH]
        t = np.array([r["decision_time"] for r in rows])
        last_day = math.floor(t.max() / DAY) * DAY
        cut, folds, oos = FIRST_CUT, [], []
        while cut <= last_day:
            tr = [r for r in rows if r["decision_time"] < cut and r["label_matures_at"] <= cut]
            te = sorted([r for r in rows if cut <= r["decision_time"] < cut + DAY], key=lambda r: (r["decision_time"], r["mint"]))
            if len(tr) >= 100 and te:
                y = np.array([r["label"] for r in tr], float)
                b0 = float(y.mean())
                Xt = np.array([r["tech"] for r in tr])
                Xb = np.array([r["b2"] for r in tr])
                u1 = np.all(np.isfinite(Xt), 1)
                u2 = u1 & np.all(np.isfinite(Xb[:, :4]), 1)
                f = {"cutoff": dt.datetime.fromtimestamp(cut, dt.timezone.utc).isoformat()[:10], "n_train": len(tr), "k_train": int(y.sum()),
                     "m1_used": [int(u1.sum()), int(y[u1].sum())], "m2_used": [int(u2.sum()), int(y[u2].sum())],
                     "m1_gate": gate(int(u1.sum()), int(y[u1].sum())), "m2_gate": gate(int(u2.sum()), int(y[u2].sum())),
                     "n_test": len(te), "k_test": int(sum(r["label"] for r in te))}
                models = {}
                if f["m1_gate"]:
                    st1 = prep_fit(Xt[u1])
                    models["M1"] = ("lr", st1, LogisticRegression(C=1.0, tol=1e-12, max_iter=100000).fit(prep_tr(st1, Xt[u1]), y[u1]))
                    models["M1n"] = ("lr", st1, LogisticRegression(C=1.0, solver="newton-cholesky", tol=1e-14, max_iter=1000).fit(prep_tr(st1, Xt[u1]), y[u1]))
                    models["M3"] = ("gb", None, GradientBoostingClassifier(max_depth=1, n_estimators=100, learning_rate=0.1,
                                                                            min_samples_leaf=10, random_state=0).fit(Xt[u1], y[u1]))
                if f["m2_gate"]:
                    X2 = np.hstack([Xb, Xt])
                    st2 = prep_fit(X2[u2])
                    models["M2"] = ("lr", st2, LogisticRegression(C=1.0, solver="newton-cholesky", tol=1e-14, max_iter=1000).fit(prep_tr(st2, X2[u2]), y[u2]))
                for r in te:
                    o = {"fold": len(folds), "dk": r["decision_key"], "y": r["label"], "B0": b0, "day": f["cutoff"]}
                    xt = np.array([r["tech"]])
                    x2 = np.hstack([np.array([r["b2"]]), xt])
                    for m, (kind, st, mdl) in models.items():
                        if m in ("M1", "M1n", "M3") and np.all(np.isfinite(xt)):
                            o[m] = float(mdl.predict_proba(prep_tr(st, xt) if kind == "lr" else xt)[0, 1])
                        elif m == "M2" and np.all(np.isfinite(x2[0, 5:])) and np.all(np.isfinite(x2[0, :4])):
                            o[m] = float(mdl.predict_proba(prep_tr(st, x2))[0, 1])
                    oos.append(o)
                folds.append(f)
            cut += DAY
        # compare with committed OOS predictions
        cmp = {}
        cm = {(r["decision_key"]): r for r in oosc if r["target_short"] == short}
        for m, col in (("B0", "B0"), ("M1", "M1_T_LOGIT"), ("M1n", "M1_T_LOGIT"), ("M2", "M2_T_LOGIT_B2"), ("M3", "M3_T_STUMPS")):
            diffs, both, only_me, only_them = [], 0, 0, 0
            for o in oos:
                c = cm.get(o["dk"])
                theirs = float(c[col]) if c and c[col] != "" else None
                mine = o.get(m)
                if mine is None and theirs is None:
                    continue
                if mine is None or theirs is None:
                    only_me += mine is not None
                    only_them += theirs is not None
                    continue
                both += 1
                diffs.append(abs(mine - theirs))
            cmp[m] = {"both": both, "only_mine": only_me, "only_committed": only_them, "max_abs_diff": max(diffs) if diffs else None}
        sc = {}
        for m in ("M1", "M1n", "M2", "M3"):
            u = [o for o in oos if m in o]
            if u:
                yy = np.array([o["y"] for o in u], float)
                p = np.array([o[m] for o in u])
                b = np.array([o["B0"] for o in u])
                bm, bb = float(np.mean((p - yy) ** 2)), float(np.mean((b - yy) ** 2))
                sc[m] = {"n": len(u), "k": int(yy.sum()), "days": len({o["day"] for o in u}), "brier": bm, "brier_b0": bb,
                         "bss": 1 - bm / bb if bb > 0 else None}
        # holdout-start training counts
        trh = [r for r in rows if r["decision_time"] < HOLD and r["label_matures_at"] <= HOLD]
        yh = np.array([r["label"] for r in trh], float)
        u1 = np.array([all(math.isfinite(v) for v in r["tech"]) for r in trh])
        u2 = u1 & np.array([all(math.isfinite(v) for v in r["b2"][:4]) for r in trh])
        res["targets"][short] = {"n_dev": len(rows), "k_dev": int(sum(r["label"] for r in rows)), "folds": folds,
                                 "oos_n": len(oos), "compare_with_committed": cmp, "scores": sc,
                                 "holdout_start": {"n": len(trh), "k": int(yh.sum()), "m1_used": [int(u1.sum()), int(yh[u1].sum())],
                                                   "m2_used": [int(u2.sum()), int(yh[u2].sum())]}}
    json.dump(res, open(out_path, "w"), indent=1, default=float)
    print(json.dumps(res["features"], default=float))
    for s, r in res["targets"].items():
        print(s, r["n_dev"], r["k_dev"], "holdout", r["holdout_start"])
        for f in r["folds"]:
            print("   ", f)
        print("   compare", r["compare_with_committed"])
        print("   scores", json.dumps(r["scores"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])

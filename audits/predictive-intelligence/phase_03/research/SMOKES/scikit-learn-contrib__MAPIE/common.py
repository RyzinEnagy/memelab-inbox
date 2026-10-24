"""Shared helpers for reviewer R2 smokes (Phase 03). Synthetic challenge only; numbers are format and behaviour checks, never evidence of memecoin edge.

Base model shared by the calibration/conformal smokes: sklearn Pipeline(SimpleImputer(median), StandardScaler,
LogisticRegression(lbfgs, max_iter=2000)) on the six legitimate features (liq_usd and vol_24h as log1p).
Splits are strict as-of:
  fit set  = split 'train', not censored, label_matures_at <= first val decision_time (rows maturing later are purged)
  cal set  = split 'val',   not censored, label_matures_at <= first holdout decision_time (purged otherwise)
  holdout  = split 'holdout', not censored (censored rows are excluded, never scored as negatives)
"""
import hashlib
import io
import math
import resource
import sys
import time

import numpy as np
import pandas as pd

CHALLENGE = "/home/claude/pi_research/challenge/challenge.csv"
EXPECTED_SHA = "18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d"
FEATURES = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
TRAP = "leak_future_ret"
LOGCOLS = {"liq_usd", "vol_24h"}


def load():
    raw = open(CHALLENGE, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA:
        raise SystemExit(f"challenge.csv sha256 mismatch: {sha}")
    df = pd.read_csv(io.BytesIO(raw))
    return df, sha


def design(df, cols):
    out = []
    for c in cols:
        v = df[c].to_numpy(dtype=float)
        if c in LOGCOLS:
            v = np.log1p(v)
        out.append(v)
    return np.column_stack(out)


def splits(df):
    t_val0 = int(df.loc[df.split == "val", "decision_time"].min())
    t_hold0 = int(df.loc[df.split == "holdout", "decision_time"].min())
    lab = (df.censored == 0) & df.label.notna()
    assert int(((df.censored == 1) & df.label.notna()).sum()) == 0
    tr_all = (df.split == "train") & lab
    tr = tr_all & (df.label_matures_at <= t_val0)
    cal_all = (df.split == "val") & lab
    cal = cal_all & (df.label_matures_at <= t_hold0)
    ho = (df.split == "holdout") & lab
    info = {
        "t_val0": t_val0,
        "t_hold0": t_hold0,
        "train_labeled": int(tr_all.sum()),
        "train_purged_label_matures_after_val_start": int((tr_all & ~tr).sum()),
        "val_labeled": int(cal_all.sum()),
        "val_purged_label_matures_after_holdout_start": int((cal_all & ~cal).sum()),
        "holdout_labeled": int(ho.sum()),
        "holdout_censored_excluded": int(((df.split == "holdout") & (df.censored == 1)).sum()),
        "censored_total": int((df.censored == 1).sum()),
        "embargo_rows": int((df.split == "embargo").sum()),
    }
    return tr.to_numpy(), cal.to_numpy(), ho.to_numpy(), info


def base_pipeline():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000)),
    ])


def brier(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    return float(np.mean((p - y) ** 2))


def logloss(y, p, eps=1e-6):
    y = np.asarray(y, float)
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def reliability_uniform(y, p, nbins=10):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    edges = np.linspace(0, 1, nbins + 1)
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, nbins - 1)
    rows, ece = [], 0.0
    for b in range(nbins):
        m = idx == b
        n = int(m.sum())
        if n == 0:
            rows.append((edges[b], edges[b + 1], 0, float("nan"), float("nan"), 0, float("nan"), float("nan")))
            continue
        k = int(y[m].sum())
        mp, obs = float(p[m].mean()), k / n
        lo, hi = wilson(k, n)
        ece += n / len(y) * abs(obs - mp)
        rows.append((edges[b], edges[b + 1], n, mp, obs, k, lo, hi))
    return rows, ece


def reliability_quantile(y, p, nbins=5):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    order = np.argsort(p, kind="mergesort")
    rows, ece = [], 0.0
    for chunk in np.array_split(order, nbins):
        n = len(chunk)
        k = int(y[chunk].sum())
        mp, obs = float(p[chunk].mean()), k / n
        lo, hi = wilson(k, n)
        ece += n / len(y) * abs(obs - mp)
        rows.append((float(p[chunk].min()), float(p[chunk].max()), n, mp, obs, k, lo, hi, lo <= mp <= hi))
    return rows, ece


def pred_hash(p):
    return hashlib.sha256(np.round(np.asarray(p, float), 10).tobytes()).hexdigest()[:16]


def print_reliability(tag, y, p):
    rows, ece = reliability_uniform(y, p, 10)
    print(f"[{tag}] reliability, 10 uniform bins (lo, hi, n, mean_p, obs_rate, positives, wilson95_lo, wilson95_hi):")
    for r in rows:
        if r[2] == 0:
            print(f"   [{r[0]:.1f},{r[1]:.1f}) n=0")
        else:
            print(f"   [{r[0]:.1f},{r[1]:.1f}) n={r[2]:4d} mean_p={r[3]:.4f} obs={r[4]:.4f} pos={r[5]:3d} wilson=({r[6]:.4f},{r[7]:.4f})")
    print(f"[{tag}] ECE_uniform10 (count-weighted |obs-mean_p|) = {ece:.5f}")
    qrows, qece = reliability_quantile(y, p, 5)
    print(f"[{tag}] reliability, 5 quantile bins (ACCEPTANCE style; mean_p inside Wilson 95%?):")
    for r in qrows:
        print(f"   p in [{r[0]:.4f},{r[1]:.4f}] n={r[2]:4d} mean_p={r[3]:.4f} obs={r[4]:.4f} pos={r[5]:3d} wilson=({r[6]:.4f},{r[7]:.4f}) inside={r[8]}")
    print(f"[{tag}] ECE_quantile5 = {qece:.5f}; all quantile bins inside Wilson: {all(r[8] for r in qrows)}")
    k, n = int(np.sum(y)), len(y)
    lo, hi = wilson(k, n)
    mp = float(np.mean(p))
    print(f"[{tag}] calibration-in-the-large: mean_p={mp:.4f} prevalence={k/n:.4f} wilson95=({lo:.4f},{hi:.4f}) inside={lo <= mp <= hi}")
    return ece, qece


def score_block(tag, y, p, base_rate):
    from sklearn.metrics import average_precision_score, roc_auc_score

    p = np.asarray(p, float)
    finite = bool(np.all(np.isfinite(p)))
    inrange = bool(np.all((p >= 0) & (p <= 1)))
    b = brier(y, p)
    bb = brier(y, np.full(len(y), base_rate))
    ll = logloss(y, p)
    llb = logloss(y, np.full(len(y), base_rate))
    auc = roc_auc_score(y, p) if 0 < np.sum(y) < len(y) else float("nan")
    ap = average_precision_score(y, p) if 0 < np.sum(y) < len(y) else float("nan")
    print(f"[{tag}] n={len(y)} positives={int(np.sum(y))} shape={p.shape} finite={finite} in[0,1]={inrange} "
          f"min={p.min():.5f} max={p.max():.5f}")
    print(f"[{tag}] brier={b:.5f} baseline_brier={bb:.5f} BSS={1 - b / bb:.4f} logloss={ll:.5f} baseline_logloss={llb:.5f} "
          f"AUC={auc:.4f} AP={ap:.4f} pred_hash={pred_hash(p)}")
    return {"brier": b, "baseline_brier": bb, "bss": 1 - b / bb, "logloss": ll, "auc": auc, "ap": ap}


def peak_rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def asof_violations(df, feature_available_col, decision_col="decision_time"):
    v = df[feature_available_col].to_numpy() > df[decision_col].to_numpy()
    return int(v.sum()), len(v)


def venn_abers_bruteforce(s_cal, y_cal, s_test):
    """Definition of the inductive Venn-Abers predictor: for each test score, append it to the calibration
    scores with label 0 and with label 1, fit isotonic regression, read the fitted value at the test score."""
    from sklearn.isotonic import IsotonicRegression

    s_cal = np.asarray(s_cal, float)
    y_cal = np.asarray(y_cal, float)
    p0 = np.empty(len(s_test))
    p1 = np.empty(len(s_test))
    for i, s in enumerate(s_test):
        for lab, out in ((0.0, p0), (1.0, p1)):
            ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            ir.fit(np.append(s_cal, s), np.append(y_cal, lab))
            out[i] = ir.predict([s])[0]
    return p0, p1


def header(name):
    print(f"=== {name} | python {sys.version.split()[0]} | numpy {np.__version__} | pandas {pd.__version__}")

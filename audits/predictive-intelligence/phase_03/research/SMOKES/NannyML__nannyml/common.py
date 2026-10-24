"""Shared helpers for the R4 Phase 03 smokes (challenge loading, a plain baseline model, proper scores)."""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

CHALLENGE = "/home/claude/pi_research/challenge/challenge.csv"
CHALLENGE_SHA256 = "18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d"
FEATURES = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
TRAP = "leak_future_ret"
SEED = 20261024


def load():
    raw = open(CHALLENGE, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    assert got == CHALLENGE_SHA256, f"challenge sha256 mismatch {got}"
    df = pd.read_csv(CHALLENGE)
    return df


def matured(df):
    """Rows whose label exists (censored rows have an empty label and are never scored as negatives)."""
    return df[df["label"].notna()].copy()


def log_feats(df, cols):
    """log1p on the heavy-tailed money columns, NaN kept."""
    X = df[cols].astype(float).copy()
    for c in ("liq_usd", "vol_24h"):
        if c in X:
            X[c] = np.log1p(X[c])
    return X


def fit_baseline(train, cols):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000))
    m.fit(log_feats(train, cols), train["label"].astype(int))
    return m


def scores(y, p, prevalence_train):
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    base = np.full_like(p, prevalence_train)
    out = {
        "n": int(len(y)), "positives": int(y.sum()),
        "brier": float(brier_score_loss(y, p)), "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None,
        "baseline_brier": float(brier_score_loss(y, base)), "baseline_log_loss": float(log_loss(y, base, labels=[0, 1])),
        "p_min": float(p.min()), "p_max": float(p.max()), "all_finite": bool(np.isfinite(p).all()),
    }
    return out


def emit(name, obj):
    print(f"RESULT {name} " + json.dumps(obj, default=str, sort_keys=True))
    sys.stdout.flush()

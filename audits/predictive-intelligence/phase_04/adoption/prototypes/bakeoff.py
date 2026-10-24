"""Phase 04 bake-off: one approach on one common point-in-time dataset with the frozen day walk-forward folds.

Every approach sees the same rows and the same folds (core_numpy.day_walk_forward with label-maturity purge). It writes its
out-of-sample predictions and pooled metrics as JSON on stdout, so measure.py can time it, count network attempts and compare
the sha256 of two runs. The numbers measure behaviour, cost and correctness on a small development sample or a synthetic file;
they are not evidence of predictive edge.

    python bakeoff.py DATASET APPROACH [--first-last-train-day YYYY-MM-DD] [--min-train N]
DATASET: dev24 | dev6 | challenge.  APPROACH: B0 | LR_NUMPY | LR_SKLEARN | HGB_SKLEARN | LGBM | COX_LIFELINES |
         LR_NUMPY_PLATT | LR_SKLEARN_SIGMOID_FROZEN | LR_NUMPY_VENN_ABERS
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_numpy as K  # noqa: E402

DATA = HERE.parent / "data"
CHALLENGE = HERE.parents[2] / "phase_03" / "research" / "SMOKES" / "_challenge" / "challenge.csv"
DEV_FEATURES = ["log_liquidity", "log_mcap", "log_vol_24h", "log_age_h", "fatal_flag"]     # B2 of ACCEPTANCE_METRICS
CH_FEATURES = ["log_liq", "log_vol", "log_age", "score100", "fatal_flag", "ret_1h"]
HORIZON = {"dev24": 86400.0, "dev6": 21600.0, "challenge": 86400.0}


def _num(x: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def load(name: str) -> dict:
    if name in ("dev24", "dev6"):
        f = DATA / ("dev_t1_24h.csv" if name == "dev24" else "dev_t1b_6h.csv")
        rows = list(csv.DictReader(open(f)))
        X = np.array([[_num(r[c]) for c in DEV_FEATURES] for r in rows])
        return {"ids": [r["event_id"] for r in rows], "X": X, "y": np.array([int(r["y"]) for r in rows], float),
                "t": np.array([float(r["decision_time"]) for r in rows]), "m": np.array([float(r["label_matures_at"]) for r in rows]),
                "event_time": np.array([float(r["event_time_s"]) for r in rows]),
                "target_first": np.array([r["label_class"] == "TARGET_FIRST" for r in rows]), "features": DEV_FEATURES,
                "first_last_train_day": "2026-10-11", "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    rows = [r for r in csv.DictReader(open(CHALLENGE)) if r["label"] != ""]       # censored rows have no label: never negatives
    def lg(x):
        v = _num(x)
        return math.log10(v) if v > 0 else float("nan")
    X = np.array([[lg(r["liq_usd"]), lg(r["vol_24h"]), math.log10(_num(r["age_h"]) + 1), _num(r["score100"]), _num(r["fatal_flag"]),
                   _num(r["ret_1h"])] for r in rows])
    y = np.array([int(float(r["label"])) for r in rows], float)
    return {"ids": [r["decision_id"] for r in rows], "X": X, "y": y, "t": np.array([float(r["decision_time"]) for r in rows]),
            "m": np.array([float(r["label_matures_at"]) for r in rows]),
            "event_time": np.array([float(r["time_to_event_h"]) * 3600 for r in rows]), "target_first": y == 1,
            "features": CH_FEATURES, "first_last_train_day": "2026-09-27",
            "sha256": hashlib.sha256(CHALLENGE.read_bytes()).hexdigest()}


def later_window(tr: np.ndarray, t: np.ndarray, m: np.ndarray, share: float = 0.3) -> tuple[np.ndarray, np.ndarray]:
    """Split training rows by decision time: the model is fitted on the earlier rows whose labels matured before the first
    calibration decision, the calibrator on the later rows (all inside the fold's matured training set)."""
    order = tr[np.argsort(t[tr], kind="stable")]
    k = int(round(len(order) * (1 - share)))
    cal = order[k:]
    c0 = t[cal].min()
    fit = order[:k]
    fit = fit[m[fit] <= c0]
    return fit, cal


def predict_fold(approach: str, d: dict, tr: np.ndarray, te: np.ndarray, horizon: float) -> np.ndarray:
    X, y = d["X"], d["y"]
    if approach == "B0":
        return np.full(len(te), y[tr].mean())
    if approach in ("LR_NUMPY", "LR_SKLEARN"):
        prep = K.Prep().fit(X[tr])
        Ztr, Zte = prep.transform(X[tr]), prep.transform(X[te])
        if approach == "LR_NUMPY":
            return K.Logistic(C=1.0).fit(Ztr, y[tr]).predict_proba1(Zte)
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(C=1.0, tol=1e-10, max_iter=10000).fit(Ztr, y[tr])
        return lr.predict_proba(Zte)[:, 1]
    if approach == "HGB_SKLEARN":
        from sklearn.ensemble import HistGradientBoostingClassifier
        k = K.informative_columns(X[tr])
        m = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.05, max_leaf_nodes=8, min_samples_leaf=10,
                                           early_stopping=False, random_state=0).fit(X[tr][:, k], y[tr])
        return m.predict_proba(X[te][:, k])[:, 1]
    if approach == "LGBM":
        import lightgbm as lgb
        k = K.informative_columns(X[tr])
        m = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=8, min_child_samples=10, deterministic=True,
                               force_row_wise=True, num_threads=1, seed=0, verbose=-1).fit(X[tr][:, k], y[tr])
        return m.predict_proba(X[te][:, k])[:, 1]
    if approach == "COX_LIFELINES":
        import pandas as pd
        from lifelines import CoxPHFitter
        prep = K.Prep().fit(X[tr])
        cols = [f"x{j}" for j in range(prep.transform(X[tr[:1]]).shape[1])]
        # Complete follow-up to the horizon (every training label matured): a competing event keeps the row in the risk set
        # until the horizon, so 1 - S(horizon) is the cumulative incidence of the target (Fine-Gray without censoring).
        dur = np.where(d["target_first"][tr], d["event_time"][tr], horizon)
        df = pd.DataFrame(prep.transform(X[tr]), columns=cols)
        df["T"], df["E"] = np.maximum(dur, 1.0), d["target_first"][tr].astype(int)
        cph = CoxPHFitter(penalizer=0.1).fit(df, "T", "E")
        sf = cph.predict_survival_function(pd.DataFrame(prep.transform(X[te]), columns=cols), times=[horizon])
        return 1 - sf.to_numpy()[0]
    if approach in ("LR_NUMPY_PLATT", "LR_SKLEARN_SIGMOID_FROZEN", "LR_NUMPY_VENN_ABERS"):
        fit, cal = later_window(tr, d["t"], d["m"])
        prep = K.Prep().fit(X[fit])
        Zf, Zc, Zt = prep.transform(X[fit]), prep.transform(X[cal]), prep.transform(X[te])
        if approach == "LR_SKLEARN_SIGMOID_FROZEN":
            from sklearn.calibration import CalibratedClassifierCV
            from sklearn.frozen import FrozenEstimator
            from sklearn.linear_model import LogisticRegression
            lr = LogisticRegression(C=1.0, tol=1e-10, max_iter=10000).fit(Zf, y[fit])
            cc = CalibratedClassifierCV(FrozenEstimator(lr), method="sigmoid").fit(Zc, y[cal])
            return cc.predict_proba(Zt)[:, 1]
        lr = K.Logistic(C=1.0).fit(Zf, y[fit])
        if approach == "LR_NUMPY_PLATT":
            return K.Platt().fit(lr.decision_function(Zc), y[cal]).predict(lr.decision_function(Zt))
        return K.venn_abers(lr.decision_function(Zc), y[cal], lr.decision_function(Zt))[2]
    raise SystemExit(f"unknown approach {approach}")


def main() -> None:
    name, approach = sys.argv[1], sys.argv[2]
    min_train = int(sys.argv[sys.argv.index("--min-train") + 1]) if "--min-train" in sys.argv else 100
    d = load(name)
    first = d["first_last_train_day"]
    if "--first-last-train-day" in sys.argv:
        first = sys.argv[sys.argv.index("--first-last-train-day") + 1]
    fl = dt.datetime.fromisoformat(first + "T00:00:00+00:00").timestamp()
    folds = K.day_walk_forward(d["t"], d["m"], first_last_train_day=fl, min_train=min_train)
    audit = K.fold_audit(d["t"], d["m"], folds, len(d["y"]))
    preds, ys, b0, ids, fold_of = [], [], [], [], []
    for k, f in enumerate(folds):
        tr, te = f["train"], f["test"]
        p = np.asarray(predict_fold(approach, d, tr, te, HORIZON[name]), float)
        K._check_probs(p)
        preds.append(p); ys.append(d["y"][te]); b0.append(np.full(len(te), d["y"][tr].mean()))
        ids += [d["ids"][i] for i in te]; fold_of += [k] * len(te)
    out = {"dataset": name, "dataset_sha256": d["sha256"], "approach": approach, "features": d["features"],
           "rule": "day walk-forward, training labels matured by the cutoff (ACCEPTANCE walk_forward); min_train " + str(min_train),
           "first_last_train_day": first, "folds": len(folds), "fold_audit_valid": audit["valid_walk_forward"]}
    if folds:
        P, Y, B = np.concatenate(preds), np.concatenate(ys), np.concatenate(b0)
        bs, bb = K.brier(Y, P), K.brier(Y, B)
        lo, hi = K.wilson(int(Y.sum()), len(Y))
        out.update({"n_oos": int(len(Y)), "positives_oos": int(Y.sum()), "brier": round(bs, 6), "brier_b0_same_rows": round(bb, 6),
                    "bss_vs_b0": round(1 - bs / bb, 4) if bb > 0 else None, "log_loss": round(K.log_loss(Y, P), 6),
                    "mean_p": round(float(P.mean()), 6), "observed_rate": round(float(Y.mean()), 6),
                    "mean_p_inside_wilson95": bool(lo <= P.mean() <= hi), "p_min": round(float(P.min()), 6), "p_max": round(float(P.max()), 6),
                    "train_sizes": [int(len(f["train"])) for f in folds], "test_sizes": [int(len(f["test"])) for f in folds],
                    "predictions_sha256": hashlib.sha256(json.dumps([ids, fold_of, [round(float(x), 10) for x in P]]).encode()).hexdigest()})
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()

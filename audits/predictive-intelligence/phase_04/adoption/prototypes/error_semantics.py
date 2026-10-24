"""Phase 04 error semantics: how each bake-off component reacts to inputs the lab will meet (NaN or inf features, a training
window with one class, a two-row window, a NaN in a calibration score). RAISES is the safe answer when the wrapper turns the
exception into a visible state (runtime.guarded); SILENT means a number came out and a wrapper must check inputs first.

    python error_semantics.py      # bundle venv, offline
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_numpy as K  # noqa: E402

warnings.simplefilter("ignore")
rng = np.random.default_rng(7)
X = rng.normal(size=(200, 3))
y = (rng.random(200) < 0.3).astype(float)
CASES = {
    "nan_feature": (np.where(np.arange(600).reshape(200, 3) == 5, np.nan, X), y),
    "inf_feature": (np.where(np.arange(600).reshape(200, 3) == 5, np.inf, X), y),
    "all_missing_column": (np.column_stack([X[:, :2], np.full(200, np.nan)]), y),
    "constant_column": (np.column_stack([X[:, :2], np.ones(200)]), y),
    "one_class": (X, np.zeros(200)),
    "two_rows": (X[:2], np.array([0.0, 1.0])),
}


def outcome(fn):
    try:
        p = np.asarray(fn(), float)
        ok = p.size > 0 and bool(np.all(np.isfinite(p))) and bool(np.all((p >= 0) & (p <= 1)))
        return {"result": "SILENT_FINITE" if ok else "SILENT_NONFINITE_OR_OUT_OF_RANGE",
                "p_range": [float(np.nanmin(p)), float(np.nanmax(p))] if p.size else None}
    except Exception as e:  # noqa: BLE001
        return {"result": "RAISES", "error": type(e).__name__, "message": str(e)[:90]}


def lr_numpy(Xa, ya):
    prep = K.Prep().fit(Xa)
    return K.Logistic().fit(prep.transform(Xa), ya).predict_proba1(prep.transform(X[:5]))


def lr_numpy_raw(Xa, ya):
    return K.Logistic().fit(Xa, ya).predict_proba1(X[:5])


def lr_sklearn(Xa, ya):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression().fit(Xa, ya).predict_proba(X[:5])[:, 1]


def hgb(Xa, ya):
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=20, random_state=0).fit(Xa, ya).predict_proba(X[:5])[:, 1]


def lgbm(Xa, ya):
    import lightgbm as lgb
    return lgb.LGBMClassifier(n_estimators=20, deterministic=True, num_threads=1, verbose=-1).fit(Xa, ya).predict_proba(X[:5])[:, 1]


def cox(Xa, ya):
    import pandas as pd
    from lifelines import CoxPHFitter
    df = pd.DataFrame(Xa, columns=["a", "b", "c"])
    df["T"], df["E"] = np.where(ya > 0, 10.0, 24.0), ya.astype(int)
    m = CoxPHFitter(penalizer=0.1).fit(df, "T", "E")
    return 1 - m.predict_survival_function(pd.DataFrame(X[:5], columns=["a", "b", "c"]), times=[24.0]).to_numpy()[0]


def platt_numpy(Xa, ya):
    return K.Platt().fit(Xa[:, 2], ya).predict(X[:5, 2])


def venn_abers_numpy(Xa, ya):
    return K.venn_abers(Xa[:, 2], ya, X[:5, 2])[2]


def main() -> None:
    comps = {"LR_NUMPY (Prep + Logistic)": lr_numpy, "Logistic without Prep": lr_numpy_raw, "LR_SKLEARN": lr_sklearn,
             "HGB_SKLEARN": hgb, "LGBM": lgbm, "COX_LIFELINES": cox, "Platt numpy": platt_numpy, "Venn-Abers numpy": venn_abers_numpy}
    res = {c: {k: outcome(lambda f=f, a=a: f(*a)) for k, a in CASES.items()} for c, f in comps.items()}
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()

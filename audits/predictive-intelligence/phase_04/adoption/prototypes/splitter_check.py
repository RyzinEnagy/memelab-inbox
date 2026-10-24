"""Phase 04 splitter check: the lab's frozen day walk-forward (core_numpy) against purgedcv WalkForwardSplit, both put through
one independent fold audit (core_numpy.fold_audit: training rows decided after the test start, training labels maturing after
the test start, training share). Two negative controls must fail the audit: the lab rule with its maturity purge removed (a
mutation), and scikit-learn's TimeSeriesSplit (row-count folds, no label awareness), a default banned in Phase 03.

    python splitter_check.py            # bundle venv, offline
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bakeoff as B  # noqa: E402
import core_numpy as K  # noqa: E402


def lab_without_purge(t, m, first, min_train):
    """Mutation: the same day folds but training rows are every row decided before the cutoff (label maturity ignored)."""
    out = []
    for f in K.day_walk_forward(t, np.minimum(m, t), first_last_train_day=first, min_train=min_train):
        out.append(f)
    return out


def purgedcv_folds(t, m, n_splits, test_size, purge_horizon):
    import pandas as pd
    from purgedcv import WalkForwardSplit
    P = pd.Series(pd.to_datetime(t, unit="s", utc=True))
    E = pd.Series(pd.to_datetime(m, unit="s", utc=True))
    kw = {} if purge_horizon is None else {"purge_horizon": purge_horizon}
    cv = WalkForwardSplit(n_splits=n_splits, test_size=test_size, prediction_times=P, evaluation_times=E, **kw)
    return [{"train": tr, "test": te} for tr, te in cv.split(np.zeros((len(t), 1)))]


def main() -> None:
    import pandas as pd
    from sklearn.model_selection import TimeSeriesSplit
    res = {}
    for name in ("challenge", "dev24", "dev6"):
        try:
            d = B.load(name)
        except FileNotFoundError:
            res[name] = "dataset not built"
            continue
        t, m, n = d["t"], d["m"], len(d["t"])
        first = dt.datetime.fromisoformat(d["first_last_train_day"] + "T00:00:00+00:00").timestamp()
        min_train = 100 if name == "challenge" else 30
        lab = K.day_walk_forward(t, m, first_last_train_day=first, min_train=min_train)
        k = max(len(lab), 2)
        test_size = max(1, int(np.median([len(f["test"]) for f in lab])) if lab else n // 10)
        entry = {"rows": int(n), "lab_day_rule": K.fold_audit(t, m, lab, n),
                 "lab_without_maturity_purge_MUTATION": K.fold_audit(t, m, lab_without_purge(t, m, first, min_train), n),
                 "purgedcv_walkforward_purge_default": K.fold_audit(t, m, purgedcv_folds(t, m, k, test_size, None), n),
                 "purgedcv_walkforward_purge_0h": K.fold_audit(t, m, purgedcv_folds(t, m, k, test_size, pd.Timedelta(0)), n),
                 "sklearn_timeseriessplit_BANNED_DEFAULT": K.fold_audit(
                     t, m, [{"train": a, "test": b} for a, b in TimeSeriesSplit(n_splits=k).split(np.zeros((n, 1)))], n)}
        entry["summary"] = {key: {"valid": v["valid_walk_forward"], "folds": len(v["folds"]),
                                  "train_labels_maturing_after_test_start_total": sum(r["train_labels_maturing_after_test_start"] for r in v["folds"]),
                                  "train_labels_maturing_after_declared_cutoff_total": sum(r["train_labels_maturing_after_cutoff"] for r in v["folds"]),
                                  "min_train_share": v["min_train_share"]}
                            for key, v in entry.items() if isinstance(v, dict) and "folds" in v}
        res[name] = entry
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()

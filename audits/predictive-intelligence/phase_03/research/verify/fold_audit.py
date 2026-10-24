"""Phase 03 repair pass (lead): fold audit for every splitter that a temporal or group point rests on.

Added after the skeptic's counterexample (M3): a splitter certified "0 overlapping training rows" can still be
useless (empty training folds) or train on the future. Overlap counts alone do not show either, so for every fold
this script records the training and test sizes, label-window overlaps (half-open, as in rerun_purgedcv.py), training
rows decided after the first and after the last test decision, training labels that mature after the first test
decision (DATA_TIME_CONTRACT: label_matures_at <= training as-of) and, for group splits, shared groups.
check_scorecard.py reads every verify/fold_audit_*.out.txt and refuses a T1, T2, T3 or O5 point whose splitter has
an empty or small fold, or trains on the future (rule FOLD in check_scorecard.py).

Data: the shared challenge, labelled rows only (2,893), sorted by decision_time (stable), as in the skeptic's
skeptic_purgedcv.py. Suites run when their package imports, so the script is run once per venv:
  <purgedcv venv python> -I fold_audit.py challenge.csv purgedcv sklearn   > fold_audit_purgedcv.out.txt
  <sktime venv python>   -I fold_audit.py challenge.csv sktime             > fold_audit_sktime.out.txt
(both under unshare -n with OMP_NUM_THREADS=1). Keys are "<suite>.<splitter>", cited in evidence as
fold_audit:<suite>.<splitter>.
"""
import bisect, csv, json, sys
import numpy as np


def load(path):
    rows = [r for r in csv.DictReader(open(path)) if r["label"] not in ("", "nan", "NaN")]
    dec = np.array([int(float(r["decision_time"])) for r in rows], dtype=np.int64)
    order = np.argsort(dec, kind="mergesort")
    rows = [rows[i] for i in order]
    dec = dec[order]
    mat = np.array([int(float(r["label_matures_at"])) for r in rows], dtype=np.int64)
    mint = np.array([r["mint"] for r in rows])
    return dec, mat, mint


def union(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def overlaps(train, test, dec, mat):
    u = union([(int(dec[j]), int(mat[j])) for j in test])
    starts = [a for a, _ in u]
    bad = 0
    for i in train:
        s, e = int(dec[i]), int(mat[i])
        k = bisect.bisect_left(starts, e)
        if k > 0 and u[k - 1][1] > s:
            bad += 1
    return bad


def fold(train, test, dec, mat, groups=None):
    train = np.asarray(train, dtype=np.int64)
    test = np.asarray(test, dtype=np.int64)
    out = {"n_train": int(len(train)), "n_test": int(len(test))}
    if len(test) == 0:
        return out
    t_first, t_last = int(dec[test].min()), int(dec[test].max())
    out["overlap"] = overlaps(train, test, dec, mat) if len(train) else 0
    out["train_decided_after_first_test"] = int((dec[train] > t_first).sum()) if len(train) else 0
    out["train_decided_after_last_test"] = int((dec[train] > t_last).sum()) if len(train) else 0
    out["train_label_matures_after_first_test"] = int((mat[train] > t_first).sum()) if len(train) else 0
    if groups is not None:
        out["shared_groups"] = len(set(groups[train]) & set(groups[test]))
    return out


def summarize(folds):
    keys = ["overlap", "train_decided_after_first_test", "train_decided_after_last_test",
            "train_label_matures_after_first_test", "shared_groups"]
    s = {"folds": len(folds), "min_n_train": min(f["n_train"] for f in folds),
         "min_n_test": min(f["n_test"] for f in folds)}
    for k in keys:
        if any(k in f for f in folds):
            s["max_" + k] = max(f.get(k, 0) for f in folds)
    s["per_fold"] = folds
    return s


def suite_purgedcv(dec, mat, mint, out):
    import pandas as pd
    import purgedcv
    from purgedcv import WalkForwardSplit, PurgedKFold, CombinatorialPurgedCV, PurgedGroupKFold
    P = pd.Series(pd.to_datetime(dec, unit="s"))
    E = pd.Series(pd.to_datetime(mat, unit="s"))
    X = np.zeros((len(dec), 1))
    day = pd.Timedelta(hours=24)
    out["purgedcv.version"] = purgedcv.__version__
    out["purgedcv.WalkForwardSplit"] = summarize([fold(a, b, dec, mat) for a, b in WalkForwardSplit(
        n_splits=5, test_size=280, prediction_times=P, evaluation_times=E).split(X)])
    out["purgedcv.PurgedKFold"] = summarize([fold(a, b, dec, mat) for a, b in PurgedKFold(
        n_splits=5, prediction_times=P, evaluation_times=E, embargo=day).split(X)])
    out["purgedcv.CombinatorialPurgedCV"] = summarize([fold(a, b, dec, mat) for a, b in CombinatorialPurgedCV(
        n_splits=6, n_test_groups=2, prediction_times=P, evaluation_times=E, embargo=day).split(X)])
    out["purgedcv.PurgedGroupKFold"] = summarize([fold(a, b, dec, mat, mint) for a, b in PurgedGroupKFold(
        n_splits=5, prediction_times=P, evaluation_times=E, groups=mint).split(X)])


def suite_sklearn(dec, mat, mint, out):
    import sklearn
    from sklearn.model_selection import KFold, TimeSeriesSplit, GroupKFold
    X = np.zeros((len(dec), 1))
    out["sklearn.version"] = sklearn.__version__
    out["sklearn.KFold_control"] = summarize([fold(a, b, dec, mat) for a, b in KFold(5).split(X)])
    out["sklearn.TimeSeriesSplit"] = summarize([fold(a, b, dec, mat) for a, b in TimeSeriesSplit(5).split(X)])
    out["sklearn.TimeSeriesSplit_gap150"] = summarize([fold(a, b, dec, mat) for a, b in TimeSeriesSplit(5, gap=150).split(X)])
    out["sklearn.GroupKFold"] = summarize([fold(a, b, dec, mat, mint) for a, b in GroupKFold(5).split(X, groups=mint)])


def suite_sktime(dec, mat, mint, out):
    import pandas as pd
    import sktime
    from sktime.split import ExpandingWindowSplitter, ExpandingCutoffSplitter, InstanceSplitter
    from sklearn.model_selection import KFold
    idx = pd.DatetimeIndex(pd.to_datetime(dec, unit="s", utc=True))
    y = pd.Series(np.zeros(len(dec)), index=idx)
    out["sktime.version"] = sktime.__version__
    out["sktime.ExpandingWindowSplitter"] = summarize([fold(a, b, dec, mat) for a, b in ExpandingWindowSplitter(
        fh=list(range(1, 101)), initial_window=1000, step_length=400).split(y)])
    out["sktime.ExpandingCutoffSplitter"] = summarize([fold(a, b, dec, mat) for a, b in ExpandingCutoffSplitter(
        cutoff=idx[1500], fh=list(range(1, 101)), step_length=400).split(y)])
    # InstanceSplitter returns positions in the (mint, time)-sorted frame; map them back to decision order
    mi = pd.MultiIndex.from_arrays([mint, idx], names=["mint", "time"])
    ym = pd.DataFrame({"label": np.zeros(len(dec)), "pos": np.arange(len(dec))}, index=mi).sort_index()
    pos = ym["pos"].to_numpy()
    folds = []
    for a, b in InstanceSplitter(cv=KFold(n_splits=3)).split(ym[["label"]]):
        folds.append(fold(pos[np.asarray(a)], pos[np.asarray(b)], dec, mat, mint))
    out["sktime.InstanceSplitter_KFold3"] = summarize(folds)


if __name__ == "__main__":
    dec, mat, mint = load(sys.argv[1])
    out = {"rows": int(len(dec))}
    for s in sys.argv[2:]:
        try:
            {"purgedcv": suite_purgedcv, "sklearn": suite_sklearn, "sktime": suite_sktime}[s](dec, mat, mint, out)
        except Exception as e:
            out[s + ".error"] = type(e).__name__ + ": " + str(e)[:200]
    print("RESULTS_JSON " + json.dumps(out, sort_keys=True))

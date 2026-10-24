"""Phase 03 lead re-execution: purgedcv purge, embargo and group claims with the lead's own overlap checker.

Different algorithm from reviewer R2's leakcheck.py: test label windows are merged into a sorted union of
half-open intervals and each training window is tested against that union with bisect. The checker is first shown
to find leaks in a splitter that does not purge (scikit-learn KFold), so a zero is not vacuous.
Usage: <purgedcv venv python> -I rerun_purgedcv.py challenge.csv
"""
import bisect, json, sys
import numpy as np, pandas as pd
import purgedcv
from purgedcv import WalkForwardSplit, PurgedKFold, CombinatorialPurgedCV, PurgedGroupKFold
from sklearn.model_selection import KFold

def union(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out

def leaks(train, test, dec, mat):
    u = union([(int(dec[j]), int(mat[j])) for j in test])
    starts = [a for a, _ in u]
    bad = 0
    for i in train:
        s, e = int(dec[i]), int(mat[i])
        k = bisect.bisect_left(starts, e)  # candidate unions starting before e
        if k > 0 and u[k - 1][1] > s:      # half-open overlap [s,e) and [a,b): a < e and s < b
            bad += 1
    return bad

def embargo_bad(train, test, dec, mat, emb):
    t = np.sort(np.asarray(test)); runs = np.split(t, np.where(np.diff(t) > 1)[0] + 1); bad = set()
    for r in runs:
        end = int(mat[r].max())
        for i in train:
            if end <= int(dec[i]) <= end + emb:
                bad.add(int(i))
    return len(bad)

df = pd.read_csv(sys.argv[1])
d = df[df.label.notna()].sort_values("decision_time", kind="mergesort").reset_index(drop=True)
dec = d.decision_time.to_numpy(np.int64); mat = d.label_matures_at.to_numpy(np.int64)
P = pd.Series(pd.to_datetime(dec, unit="s")); E = pd.Series(pd.to_datetime(mat, unit="s"))
X = np.zeros((len(d), 1)); H = 3600
res = {"purgedcv_version": purgedcv.__version__, "rows": int(len(d))}
res["control_sklearn_KFold_leaks"] = [leaks(a, b, dec, mat) for a, b in KFold(5).split(X)]
res["WalkForwardSplit_leaks"] = [leaks(a, b, dec, mat) for a, b in WalkForwardSplit(n_splits=5, test_size=280, prediction_times=P, evaluation_times=E).split(X)]
pk = list(PurgedKFold(n_splits=5, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24)).split(X))
res["PurgedKFold_leaks"] = [leaks(a, b, dec, mat) for a, b in pk]
res["PurgedKFold_embargo_violations"] = [embargo_bad(a, b, dec, mat, 24 * H) for a, b in pk]
cp = list(CombinatorialPurgedCV(n_splits=6, n_test_groups=2, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24)).split(X))
res["CPCV_folds"] = len(cp); res["CPCV_leaks_max"] = max(leaks(a, b, dec, mat) for a, b in cp)
g = d.mint.to_numpy()
gk = list(PurgedGroupKFold(n_splits=5, prediction_times=P, evaluation_times=E, groups=g).split(X))
res["PurgedGroupKFold_shared_mints"] = [len(set(g[a]) & set(g[b])) for a, b in gk]
res["PurgedGroupKFold_leaks"] = [leaks(a, b, dec, mat) for a, b in gk]
# boundary: a training label maturing exactly at the first test decision is allowed (half-open), one second later is not
dec_h = np.array([0, 6, 12, 30, 36, 60]) * H; mat_h = dec_h + 24 * H
from purgedcv._purge import purge
res["hand_case_kept"] = purge(np.array([0, 1, 2, 4, 5]), np.array([3]), pd.Series(pd.to_datetime(dec_h, unit="s")), pd.Series(pd.to_datetime(mat_h, unit="s"))).tolist()
res["hand_case_lead_checker_leaks"] = leaks([0, 1, 2, 4, 5], [3], dec_h, mat_h)
print("RESULTS_JSON " + json.dumps(res, sort_keys=True))

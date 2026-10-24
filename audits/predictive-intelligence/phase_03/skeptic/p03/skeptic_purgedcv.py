"""Skeptic P03: independent re-check of purgedcv splits on the challenge, with a third overlap algorithm
(vectorized numpy, per training row: max over test windows of the half-open overlap condition), plus a check the
phase did not run: does any training row come AFTER the test rows (future training, P13/P43), and does any training
label mature after the earliest test decision (DATA_TIME_CONTRACT: label_matures_at <= training-as-of)?
Usage: <purgedcv venv python> -I skeptic_purgedcv.py challenge.csv
"""
import json, sys
import numpy as np, pandas as pd
import purgedcv
from purgedcv import WalkForwardSplit, PurgedKFold, CombinatorialPurgedCV, PurgedGroupKFold
from sklearn.model_selection import KFold

df = pd.read_csv(sys.argv[1])
d = df[df.label.notna()].sort_values("decision_time", kind="mergesort").reset_index(drop=True)
dec = d.decision_time.to_numpy(np.int64); mat = d.label_matures_at.to_numpy(np.int64)
P = pd.Series(pd.to_datetime(dec, unit="s")); E = pd.Series(pd.to_datetime(mat, unit="s")); X = np.zeros((len(d), 1))

def audit(train, test):
    train = np.asarray(train); test = np.asarray(test)
    ts, te = dec[test], mat[test]
    # overlap of [dec_i, mat_i) with any [ts_j, te_j): ts_j < mat_i and dec_i < te_j
    o = 0
    for i in train:
        if np.any((ts < mat[i]) & (dec[i] < te)): o += 1
    t0 = ts.min()
    return {"overlap": int(o),
            "train_rows_decided_after_last_test": int((dec[train] > ts.max()).sum()),
            "train_rows_label_matures_after_first_test_decision": int((mat[train] > t0).sum()),
            "n_train": int(len(train)), "n_test": int(len(test))}

out = {"purgedcv": purgedcv.__version__, "rows": int(len(d))}
def run(name, it):
    rows = [audit(a, b) for a, b in it]
    out[name] = {k: [r[k] for r in rows] for k in rows[0]}
run("control_KFold", KFold(5).split(X))
run("WalkForwardSplit", WalkForwardSplit(n_splits=5, test_size=280, prediction_times=P, evaluation_times=E).split(X))
run("PurgedKFold_emb24h", PurgedKFold(n_splits=5, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24)).split(X))
run("CPCV_6_2_emb24h", CombinatorialPurgedCV(n_splits=6, n_test_groups=2, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24)).split(X))
run("PurgedGroupKFold_mint", PurgedGroupKFold(n_splits=5, prediction_times=P, evaluation_times=E, groups=d.mint.to_numpy()).split(X))
for k, v in out.items():
    print(k, json.dumps(v) if isinstance(v, dict) else v)

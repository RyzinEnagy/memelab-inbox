# Second reviewer rerun: purgedcv at pin 07692dd. Independent hand case and challenge checks.
import sys, numpy as np, pandas as pd
import purgedcv
from purgedcv import purge, apply_embargo, PurgedKFold, WalkForwardSplit, PurgedGroupKFold
t0 = pd.Timestamp("2026-10-01")
h = pd.Timedelta(hours=1)
starts = [0, 6, 12, 30, 36, 60]
pred = pd.Series([t0 + s*h for s in starts]); ev = pred + 24*h
print("purge hand:", purge(np.array([0,1,2,4,5]), np.array([3]), pred, ev).tolist(), "expect [0,1,5]")
print("embargo 24h:", apply_embargo(np.array([0,1,5]), np.array([3]), pred, ev, pd.Timedelta(hours=24)).tolist(), "expect [0,1]")
# my own different case: 6 h labels, gap rows
pred2 = pd.Series([t0 + s*h for s in [0, 2, 5, 7, 8, 13, 14]]); ev2 = pred2 + 6*h
print("purge 6h case:", purge(np.array([0,1,2,5,6]), np.array([3,4]), pred2, ev2).tolist(), "expect [0,6] (row1 ends 8h touches test start 7h? no: row1 [2,8) overlaps [7,14) -> drop; row2 [5,11) drop; row5 [13,19) overlaps [7,14) drop; row6 [14,20) kept, row0 [0,6) kept)")
# group leakage error
try:
    from purgedcv.diagnostics import assert_groups_disjoint
    assert_groups_disjoint(np.array([0,1]), np.array([2]), np.array(["a","b","a"]))
    print("group check: no error (UNEXPECTED)")
except Exception as e:
    print("group check raises:", type(e).__name__)
# non-monotonic
try:
    PurgedKFold(n_splits=2, prediction_times=pred[::-1].reset_index(drop=True), evaluation_times=ev[::-1].reset_index(drop=True))
    print("nonmonotonic accepted (UNEXPECTED)")
except Exception as e:
    print("nonmonotonic:", type(e).__name__, str(e)[:80])
# challenge
df = pd.read_csv(sys.argv[1])
df = df[df.label.notna()] if "label" in df.columns else df
for c in ("decision_time","label_matures_at"):
    df[c] = pd.to_datetime(df[c], unit="s")
df = df.sort_values("decision_time", kind="stable").reset_index(drop=True)
p, e = df.decision_time, df.label_matures_at
def leaks(tr, te):
    s = p.values[tr]; en = e.values[tr]; ts = p.values[te]; tn = e.values[te]
    n = 0
    for a, b in zip(s, en):
        if np.any((ts < b) & (a < tn)): n += 1
    return n
cv = PurgedKFold(n_splits=5, prediction_times=p, evaluation_times=e, embargo=pd.Timedelta(hours=24))
print("rows", len(df), "PurgedKFold leaks per fold:", [leaks(tr, te) for tr, te in cv.split(df)])
wf = WalkForwardSplit(n_splits=5, test_size=280, prediction_times=p, evaluation_times=e)
print("WalkForward leaks per fold:", [leaks(tr, te) for tr, te in wf.split(df)])
from sklearn.model_selection import TimeSeriesSplit
print("sklearn TSS(5,280) leaks:", [leaks(tr, te) for tr, te in TimeSeriesSplit(5, test_size=280).split(df)])
gk = PurgedGroupKFold(n_splits=5, prediction_times=p, evaluation_times=e, groups=df["mint"].values) if "mint" in df.columns else None
if gk is not None:
    m = df["mint"].values
    print("PurgedGroupKFold shared mints per fold:", [len(set(m[tr]) & set(m[te])) for tr, te in gk.split(df)], "leaks:", [leaks(tr, te) for tr, te in gk.split(df)])

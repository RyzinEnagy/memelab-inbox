"""Phase 03 lead re-execution: mlfinpy PurgedKFold leaves overlapping label windows in training (LEAKAGE_FAIL driver).
Six 24 h labels, three contiguous folds; leaks counted by the lead's own pairwise check.
Usage: <mlfinpy venv python> -I rerun_mlfinpy.py
"""
import json
import numpy as np, pandas as pd
from mlfinpy.cross_validation.cross_validation import PurgedKFold
H = 3600
start = pd.to_datetime(np.array([0, 6, 12, 30, 36, 60]) * H, unit="s")
end = start + pd.Timedelta(hours=24)
info = pd.Series(end, index=start)
X = pd.DataFrame({"x": np.arange(6)}, index=start)
out = []
for tr, te in PurgedKFold(n_splits=3, samples_info_sets=info, pct_embargo=0.0).split(X):
    bad = [int(i) for i in tr if any(start[i] < end[j] and start[j] < end[i] for j in te)]
    out.append({"test": [int(j) for j in te], "train": [int(i) for i in tr], "overlapping_train_rows": bad})
print("RESULTS_JSON " + json.dumps({"folds": out, "total_overlapping_train_rows": sum(len(f["overlapping_train_rows"]) for f in out)}, sort_keys=True))

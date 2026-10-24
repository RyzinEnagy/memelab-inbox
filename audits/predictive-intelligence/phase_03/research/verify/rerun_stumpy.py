"""Phase 03 lead re-execution: stumpy's streaming left matrix profile (stumpi) uses only past subsequences (T5),
checked against the lead's own numpy z-normalized distance; the default self-join P_ is shown to change when only
future samples change (control). Seeded random walk, no challenge data. Usage: <stumpy venv python> -I rerun_stumpy.py
"""
import json, math
import numpy as np
import stumpy

rng = np.random.default_rng(20261024)
T = np.cumsum(rng.normal(0, 1, 260))
m = 12; excl = int(math.ceil(m / 4))
def zdist(a, b):
    a = (a - a.mean()) / a.std(); b = (b - b.mean()) / b.std()
    return float(np.sqrt(np.sum((a - b) ** 2)))
def left_profile_numpy(T, i):
    q = T[i:i + m]; best = np.inf
    for j in range(0, i - excl):
        best = min(best, zdist(q, T[j:j + m]))
    return best
init = 60
st = stumpy.stumpi(T[:init], m, egress=False)
for t in T[init:]:
    st.update(t)
lp = np.asarray(st.left_P_, dtype=float)
idx = [30, 75, 120, 180, 240]
diffs = [abs(lp[i] - left_profile_numpy(T, i)) for i in idx]
full = stumpy.stump(T, m)
T2 = T.copy(); T2[150:] += rng.normal(0, 3, len(T) - 150)
full2 = stumpy.stump(T2, m)
i0 = 100  # subsequence [100, 112) ends before 150
print("RESULTS_JSON " + json.dumps({
    "stumpy_version": stumpy.__version__,
    "stumpi_left_P_vs_lead_numpy_past_only_max_abs_diff": max(diffs),
    "checked_indices": idx,
    "self_join_P_at_100_changes_when_only_samples_after_150_change": bool(abs(float(full[i0, 0]) - float(full2[i0, 0])) > 1e-9),
    "self_join_left_I_at_100_unchanged": bool(int(full[i0, 2]) == int(full2[i0, 2])),
}, sort_keys=True))

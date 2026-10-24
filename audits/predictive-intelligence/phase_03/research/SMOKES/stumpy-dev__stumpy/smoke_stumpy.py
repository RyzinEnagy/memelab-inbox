"""R3 Phase 03 smoke for stumpy-dev/stumpy at pin 248e344 (installed from the pinned source, version string 1.14.1).
Synthetic seeded OHLCV-like paths (r3_common.seeded_paths, seed 20261026) plus a planted motif (seed 20261027).
Format and behaviour only."""
import os, sys, time, pickle, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
tm = C.Timer()
with tm("import_stumpy_s"):
    import stumpy
import numba

res = {"env": C.env_info(), "stumpy_version": stumpy.__version__, "stumpy_file": stumpy.__file__,
       "numba": numba.__version__, "numba_threads": numba.config.NUMBA_NUM_THREADS}
paths = C.seeded_paths()
m = 12

def dense_logret(p):
    """Returns on a dense 5-minute grid with NaN where the vendor omitted an interval (no trade)."""
    t = p["t"]; c = p["close"]
    idx = (t - t[0]) // 300
    grid = np.full(int(idx[-1]) + 1, np.nan); grid[idx] = np.log(c)
    r = np.diff(grid)
    return r

# S6a: JIT compile cost (first call) versus warm call
T = np.diff(np.log(paths[0]["close"]))
with tm("stump_first_call_s"):
    stumpy.stump(T, m)
with tm("stump_second_call_s"):
    mp = stumpy.stump(T, m)
Q = T[:m].copy()
with tm("mass_first_call_s"):
    stumpy.mass(Q, T)
with tm("mass_second_call_s"):
    stumpy.mass(Q, T)

# S1a: self-join matrix profile is not causal: P[i] changes when only data after i+m is edited
i = len(mp) // 3
T2 = T.copy(); T2[i + m + 1:] = np.random.default_rng(1).normal(0, 0.05, len(T2) - (i + m + 1))
mp2 = stumpy.stump(T2, m)
res["S1_selfjoin_future_dependence"] = {"i": int(i), "P_i_original": float(mp.P_[i]), "P_i_after_editing_only_future": float(mp2.P_[i]),
    "I_i_original": int(mp.I_[i]), "I_i_after": int(mp2.I_[i]), "changed": bool(mp.P_[i] != mp2.P_[i] or mp.I_[i] != mp2.I_[i]),
    "left_I_i_original": int(mp.left_I_[i]), "left_I_i_after": int(mp2.left_I_[i]), "left_index_unchanged": bool(mp.left_I_[i] == mp2.left_I_[i])}

# S1b: stumpi (incremental, egress=False) left profile is truncation-invariant: left_P_ after streaming to d equals the
# left profile computed from the full series (recomputed by mass over the past only) for every index <= d
long = max(paths, key=lambda q: len(q["t"]))
TL = np.diff(np.log(long["close"]))
d0 = 40
stream = stumpy.stumpi(TL[:d0], m, egress=False)
with tm("stumpi_updates_s"):
    for x in TL[d0:]:
        stream.update(x)
n_upd = len(TL) - d0
leftP = stream.left_P_.copy()
maxdiff = 0.0; checked = 0
for j in range(m, len(TL) - m + 1, 7):
    past = TL[: j + m - 1]  # every subsequence that starts before j, excluding the trivial zone
    excl = int(np.ceil(m / 4))
    if j - excl < 1:
        continue
    D = stumpy.mass(TL[j:j + m], TL[: j - excl + m - 1]) if j - excl + m - 1 >= m else None
    if D is None or len(D) == 0:
        continue
    ref = float(np.min(D))
    if np.isfinite(leftP[j]) and np.isfinite(ref):
        maxdiff = max(maxdiff, abs(ref - float(leftP[j]))); checked += 1
res["S1_stumpi_left_profile"] = {"path": long["mint"], "len": len(TL), "updates": n_upd, "indices_checked": checked,
    "max_abs_diff_left_P_vs_past_only_mass": maxdiff,
    "per_update_ms": round(1000 * tm.t["stumpi_updates_s"] / n_upd, 3)}

# Role: planted motif recovery with match() across many short paths
rng = np.random.default_rng(20261027)
motif = np.array([0.0, 0.02, 0.05, 0.08, 0.06, 0.01, -0.03, -0.06, -0.04, -0.01, 0.0, 0.01])
lib = []
planted = {}
for k, p in enumerate(paths[:120]):
    r = np.diff(np.log(p["close"])).copy()
    if k % 3 == 0 and len(r) > 3 * m:
        pos = int(rng.integers(0, len(r) - m))
        r[pos:pos + m] = motif * 3 + rng.normal(0, 0.003, m)
        planted[k] = pos
    lib.append(r)
hits = 0; false_hits = 0; s = time.perf_counter(); n_q = 0
for k, r in enumerate(lib):
    if len(r) < m:
        continue
    mt = stumpy.match(motif, r, max_distance=2.0, max_matches=1)
    n_q += 1
    if len(mt):
        pos = int(mt[0][1])
        if k in planted and abs(pos - planted[k]) <= 2:
            hits += 1
        elif k not in planted:
            false_hits += 1
match_s = time.perf_counter() - s
res["role_motif_match"] = {"library_paths": len(lib), "planted": len(planted), "recovered_within_2": hits,
    "matches_on_paths_without_motif": false_hits, "max_distance": 2.0, "queries": n_q,
    "per_path_match_ms": round(1000 * match_s / n_q, 3)}

# Role: analog search for one decision across a library of earlier paths (cost of one decision-time query)
query = lib[0][-m:] if len(lib[0]) >= m else motif
s = time.perf_counter(); best = []
for r in lib[1:]:
    if len(r) >= m:
        D = stumpy.mass(query, r)
        best.append(float(np.min(D)))
analog_s = time.perf_counter() - s
res["role_analog_query"] = {"library_paths": len(best), "candles_scanned": int(sum(len(r) for r in lib[1:])),
    "query_total_ms": round(1000 * analog_s, 2),
    "note": "cross-path time cutoff (only paths whose candles were available before the decision) is wrapper code; mass has no time argument"}

# S3: NaN for omitted intervals on a dense grid
G = dense_logret(max(paths, key=lambda q: q["n_dense"] - len(q["t"])))
mpg = stumpy.stump(G, m)
nan_windows = int(np.sum(~np.isfinite(mpg.P_)))
Dg = stumpy.mass(motif, G)
res["S3_nan"] = {"dense_len": len(G), "nan_values": int(np.isnan(G).sum()), "windows": len(mpg.P_),
    "windows_with_inf_profile": nan_windows, "mass_inf_distances": int(np.sum(~np.isfinite(Dg))),
    "raised": None, "behaviour": "subsequences containing NaN get distance inf; no imputation, no error"}

# S5: persistence
mp_dtype = str(np.asarray(mp).dtype)
try:
    np.save(io.BytesIO(), np.asarray(mp), allow_pickle=False); obj_save = "ok"
except Exception as e:
    obj_save = type(e).__name__ + ": " + str(e)[:120]
buf = io.BytesIO(); np.savez(buf, P=np.asarray(mp.P_, dtype=float), I=np.asarray(mp.I_, dtype=np.int64),
    left_I=np.asarray(mp.left_I_, dtype=np.int64), right_I=np.asarray(mp.right_I_, dtype=np.int64))
buf.seek(0); z = np.load(buf, allow_pickle=False)
try:
    blob = pickle.dumps(stream); s2 = pickle.loads(blob)
    s2.update(0.01); stream.update(0.01); stumpi_pickle = "ok"
    stumpi_equal = bool(np.allclose(s2.left_P_, stream.left_P_, equal_nan=True)); nbytes = len(blob)
except Exception as e:
    stumpi_pickle = type(e).__name__ + ": " + str(e)[:160]; stumpi_equal = None; nbytes = None
res["S5_persistence"] = {"mp_dtype": mp_dtype, "mp_np_save_allow_pickle_false": obj_save, "mp_shape": list(np.asarray(mp).shape),
    "split_columns_npz_reload_equal": bool(np.array_equal(z["P"], np.asarray(mp.P_, dtype=float)) and np.array_equal(z["I"], mp.I_.astype(np.int64))),
    "stumpi_pickle": stumpi_pickle, "stumpi_pickle_bytes": nbytes, "stumpi_after_reload_update_equal": stumpi_equal}

res["S6_cost"] = dict(tm.t)
res["S2"] = "SKIPPED: no probability output (distances and indices only)"
res["S4"] = "SKIPPED: no calibration or uncertainty API"
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_stumpy.result.json"))

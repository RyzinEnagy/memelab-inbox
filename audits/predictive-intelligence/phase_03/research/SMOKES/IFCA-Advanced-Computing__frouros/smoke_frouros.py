"""Phase 03 R4 smoke for frouros at the pin (run offline).

Role: drift detection (batch data drift per feature, streaming concept drift on an error stream).
"""
import os
import pickle
import sys
import tempfile
import time
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402

warnings.filterwarnings("ignore")
import frouros  # noqa: E402
from frouros.callbacks.batch import PermutationTestDistanceBased  # noqa: E402
from frouros.detectors.concept_drift import ADWIN, DDM, PageHinkley  # noqa: E402
from frouros.detectors.concept_drift import ADWINConfig, DDMConfig, PageHinkleyConfig  # noqa: E402
from frouros.detectors.data_drift import EMD, MMD, PSI, CVMTest, KSTest  # noqa: E402
from frouros.utils import persistence  # noqa: E402

F = C.FEATURES
NUMF = ["liq_usd", "vol_24h", "age_h", "score100", "ret_1h"]
df = C.load()
tr, va, ho = (df[df.split == s].copy() for s in ("train", "val", "holdout"))
C.emit("version", {"frouros_module_version": getattr(frouros, "__version__", None)})


def col(frame, c, log=True):
    x = frame[c].astype(float).values
    if log and c in ("liq_usd", "vol_24h"):
        x = np.log1p(x)
    return x[~np.isnan(x)]


def test_pvalue(det_cls, ref, cur):
    d = det_cls()
    d.fit(X=ref)
    res, _ = d.compare(X=cur)
    return float(res.p_value)


def dist_perm(det, ref, cur, seed=7, n=300):
    det.fit(X=ref)
    res, logs = det.compare(X=cur)
    pv = None
    for v in logs.values():
        if isinstance(v, dict) and "p_value" in v:
            pv = float(v["p_value"])
    return float(res.distance), pv


# ---- Role: batch data drift per feature (alpha 0.05) ----
role = {}
for name, fn in (("ks", KSTest), ("cvm", CVMTest)):
    out = {}
    for split_name, cur in (("val", va), ("holdout", ho), ("train_second_half", tr.iloc[len(tr) // 2:])):
        ref = tr if split_name != "train_second_half" else tr.iloc[: len(tr) // 2]
        out[split_name] = {c: round(test_pvalue(fn, col(ref, c), col(cur, c)), 5) for c in NUMF}
    flagged = {k: sorted(c for c, p in v.items() if p < 0.05) for k, v in out.items()}
    # chunked monitoring: val and holdout chunks of 150 vs the whole train reference
    chunk_flags = {"val": 0, "holdout_liq_and_ret": 0, "holdout_other": 0, "val_chunks": 0, "holdout_chunks": 0}
    for split_name, part in (("val", va), ("holdout", ho)):
        for i in range(0, len(part) - 149, 150):
            ch = part.iloc[i:i + 150]
            fl = [c for c in NUMF if test_pvalue(fn, col(tr, c), col(ch, c)) < 0.05]
            if split_name == "val":
                chunk_flags["val"] += len(fl)
                chunk_flags["val_chunks"] += 1
            else:
                chunk_flags["holdout_chunks"] += 1
                chunk_flags["holdout_liq_and_ret"] += int({"liq_usd", "ret_1h"} <= set(fl))
                chunk_flags["holdout_other"] += len(set(fl) - {"liq_usd", "ret_1h"})
    role[name] = {"p_values": out, "flagged_at_0.05": flagged, "chunks": chunk_flags}
    C.emit(f"ROLE_batch_{name}", role[name])

# distance-based with a permutation test (p-value) and PSI raw vs log
t0 = time.perf_counter()
dist = {}
for c in ("liq_usd", "ret_1h", "age_h"):
    for split_name, cur in (("val", va), ("holdout", ho)):
        e, pe = dist_perm(EMD(callbacks=[PermutationTestDistanceBased(num_permutations=300, random_state=7, num_jobs=1)]),
                          col(tr, c), col(cur, c))
        dist[f"{c}:{split_name}:emd"] = {"distance": round(e, 5), "perm_p": pe}
for c in ("liq_usd", "ret_1h"):
    for log in (False, True):
        for split_name, cur in (("val", va), ("holdout", ho)):
            d = PSI(num_bins=10)
            d.fit(X=col(tr, c, log))
            r, _ = d.compare(X=col(cur, c, log))
            dist[f"{c}:{split_name}:psi:{'log' if log else 'raw'}"] = round(float(r.distance), 5)
C.emit("ROLE_distance", {"seconds": round(time.perf_counter() - t0, 3), **dist})

# multivariate MMD with permutation test (numeric columns, rows with NaN dropped, standardized on train)
X_tr = tr[NUMF].astype(float).assign(liq_usd=lambda d: np.log1p(d.liq_usd), vol_24h=lambda d: np.log1p(d.vol_24h)).dropna().values
mu, sd = X_tr.mean(0), X_tr.std(0)
mm = {}
for split_name, part in (("val", va), ("holdout", ho)):
    X = part[NUMF].astype(float).assign(liq_usd=lambda d: np.log1p(d.liq_usd), vol_24h=lambda d: np.log1p(d.vol_24h)).dropna().values
    t0 = time.perf_counter()
    det = MMD(callbacks=[PermutationTestDistanceBased(num_permutations=100, random_state=7, num_jobs=1)])
    det.fit(X=(X_tr[:600] - mu) / sd)
    r, logs = det.compare(X=(X[:300] - mu) / sd)
    pv = [v["p_value"] for v in logs.values() if isinstance(v, dict) and "p_value" in v]
    mm[split_name] = {"mmd": round(float(r.distance), 6), "perm_p": float(pv[0]) if pv else None, "seconds": round(time.perf_counter() - t0, 3)}
C.emit("ROLE_mmd_multivariate", mm)

# ---- Role: streaming concept drift on the error stream of a fixed model (time-ordered) ----
trm = C.matured(tr)
prev = float(trm.label.mean())
model = C.fit_baseline(trm, F)
stream = C.matured(df[df.split.isin(["val", "holdout"])]).sort_values("decision_time")
p = model.predict_proba(C.log_feats(stream, F))[:, 1]
y = stream.label.astype(int).values
err01 = ((p >= 0.5).astype(int) != y).astype(int)
sq = (p - y) ** 2
n_val = int((stream.split == "val").sum())
stream_res = {"n_val": n_val, "n_holdout": int(len(stream) - n_val)}
for name, det, data in (("DDM_error01", DDM(config=DDMConfig()), err01),
                        ("ADWIN_brier", ADWIN(config=ADWINConfig(delta=0.002)), sq),
                        ("PageHinkley_brier", PageHinkley(config=PageHinkleyConfig()), sq)):
    hits = []
    for i, v in enumerate(data):
        det.update(value=float(v))
        if det.drift:
            hits.append(i)
            det.reset()
    stream_res[name] = {"drift_indices": hits[:20], "in_val": sum(1 for h in hits if h < n_val),
                        "in_holdout": sum(1 for h in hits if h >= n_val)}
C.emit("ROLE_streaming_concept", stream_res)

# ---- S1: leak trap: no mechanism; the leaked model's error stream shows nothing unusual ----
leak = C.fit_baseline(trm, F + [C.TRAP])
pl = leak.predict_proba(C.log_feats(stream, F + [C.TRAP]))[:, 1]
d1 = DDM(config=DDMConfig())
hits = 0
for v in ((pl >= 0.5).astype(int) != y).astype(int):
    d1.update(value=float(v))
    if d1.drift:
        hits += 1
        d1.reset()
C.emit("S1_leak", {"mechanism": "none (no availability time, no splitter)", "holdout_like_stream_brier_legit": float(np.mean(sq)),
                   "stream_brier_with_trap": float(np.mean((pl - y) ** 2)), "ddm_drifts_with_trap": hits})

# ---- S3: NaN handling ----
s3 = {}
for name, det in (("KSTest", KSTest()), ("PSI", PSI(num_bins=10)), ("EMD", EMD())):
    try:
        det.fit(X=tr.liq_usd.astype(float).values)
        r, _ = det.compare(X=ho.liq_usd.astype(float).values)
        s3[name] = {"raised": False, "result": str(r)[:120]}
    except Exception as e:  # noqa: BLE001
        s3[name] = {"raised": True, "error": f"{type(e).__name__}: {str(e)[:160]}"}
C.emit("S3_nan", s3)

# ---- S4: uncertainty offered ----
C.emit("S4_uncertainty", {"offered": "p-values from statistical tests and permutation-test p-values for distance detectors; no probability calibration"})

# ---- S5: persistence ----
det = KSTest()
det.fit(X=col(tr, "liq_usd"))
r1, _ = det.compare(X=col(ho, "liq_usd"))
work = tempfile.mkdtemp(prefix="fr_")
path = os.path.join(work, "ks.pkl")
persistence.save(det, path)
det2 = persistence.load(path)
r2, _ = det2.compare(X=col(ho, "liq_usd"))
C.emit("S5_persist", {"format": "pickle (frouros.utils.persistence)", "bytes": os.path.getsize(path),
                      "identical": bool(r1.statistic == r2.statistic and r1.p_value == r2.p_value)})

# ---- S6: cost ----
t0 = time.perf_counter()
for c in NUMF:
    test_pvalue(KSTest, col(tr, c), col(ho, c))
ks5 = time.perf_counter() - t0
d = ADWIN(config=ADWINConfig())
t0 = time.perf_counter()
for v in sq:
    d.update(value=float(v))
adw = (time.perf_counter() - t0) / len(sq)
C.emit("S6_cost", {"ks_5_columns_s": round(ks5, 4), "adwin_update_us": round(adw * 1e6, 2)})
print("DONE")

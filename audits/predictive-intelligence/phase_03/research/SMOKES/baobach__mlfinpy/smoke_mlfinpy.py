"""Phase 03 R2 smoke for baobach/mlfinpy at e21e4066 (installed from the pinned source with the 'optionals' extra, Python 3.12).
Checks PurgedKFold / CombinatorialPurgedKFold purge and embargo against the challenge's decision_time and label_matures_at,
and triple-barrier labels against a reference implementation of the memelab T1 rule (TARGET_REGISTRY.md, Phase 01).
Run: python -I smoke_mlfinpy.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
t_imp = time.perf_counter()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import leakcheck as L  # noqa: E402

with warnings.catch_warnings(record=True) as imp_w:
    warnings.simplefilter("always")
    import mlfinpy  # noqa: E402
    from mlfinpy.cross_validation.combinatorial import CombinatorialPurgedKFold  # noqa: E402
    from mlfinpy.cross_validation.cross_validation import PurgedKFold, ml_get_train_times  # noqa: E402
    from mlfinpy.labeling.labeling import add_vertical_barrier, get_bins, get_events  # noqa: E402
t_imp = time.perf_counter() - t_imp
C.header(f"mlfinpy {mlfinpy.__version__} from {mlfinpy.__file__}")
print(f"import time {t_imp:.2f} s; warnings at import: {len(imp_w)}")
H = 3600

print("\n=== PART A: purge and embargo ===")
print("--- A1 hand case: six 24 h labels, PurgedKFold(n_splits=3) ---")
dec_h = np.array([0, 6, 12, 30, 36, 60]) * H
mat_h = dec_h + 24 * H
info_h = pd.Series(pd.to_datetime(mat_h, unit="s"), index=pd.to_datetime(dec_h, unit="s"))
print(f"windows (h): {[(int(a/H), int(b/H)) for a, b in zip(dec_h, mat_h)]}")
hand_leaks = []
for k, (tr_i, te_i) in enumerate(PurgedKFold(n_splits=3, samples_info_sets=info_h, pct_embargo=0.0).split(pd.DataFrame(np.zeros((6, 1))))):
    lk = L.overlap_leaks(tr_i, te_i, dec_h, mat_h)
    hand_leaks.append(len(lk))
    print(f"  fold {k}: test {list(te_i)} train {list(tr_i)} -> rows still overlapping a test label window: {lk.tolist()}")
tt = pd.Series([pd.Timestamp(mat_h[3], unit="s")], index=[pd.Timestamp(dec_h[3], unit="s")])
kept = ml_get_train_times(info_h.drop(info_h.index[3]), tt)
print(f"  ml_get_train_times given the test window [30 h, 54 h] directly keeps decisions at hours {[int(t.value/1e9/H) for t in kept.index]} "
      "(expected [0, 60] with closed intervals: rows ending exactly at 30 h are also dropped)")
print("  PurgedKFold builds the test window as [label END of the first test row, label end of the last test row]:")
print("  cross_validation.py: test_times = pd.Series(index=[self.samples_info_sets.iloc[start_ix]], data=[self.samples_info_sets.iloc[end_ix - 1]])")

print("\n--- A2 challenge: PurgedKFold(5, pct_embargo=0.01) on decision_time / label_matures_at ---")
df, sha = C.load()
print("challenge sha256", sha)
d = df[df.label.notna()].sort_values("decision_time", kind="mergesort").reset_index(drop=True)
d = d.drop_duplicates("decision_time", keep="first").reset_index(drop=True)
dec = d.decision_time.to_numpy().astype(np.int64)
mat = d.label_matures_at.to_numpy().astype(np.int64)
info = pd.Series(pd.to_datetime(mat, unit="s"), index=pd.to_datetime(dec, unit="s"))
Xd = pd.DataFrame(C.design(d, C.FEATURES))
print(f"rows {len(d)} (labeled, one duplicate decision time dropped because the index lookup needs unique times)")
t0 = time.perf_counter()
folds = list(PurgedKFold(n_splits=5, samples_info_sets=info, pct_embargo=0.01).split(Xd))
dt = time.perf_counter() - t0
leaks = [len(L.overlap_leaks(a, b, dec, mat)) for a, b in folds]
print(f"  {len(folds)} folds in {dt:.2f} s; (train, test) sizes {[(len(a), len(b)) for a, b in folds]}")
print(f"  training rows whose label window overlaps a test window, per fold: {leaks}")
from sklearn.model_selection import KFold  # noqa: E402

print(f"  for scale, plain KFold(5) leaves {[len(L.overlap_leaks(a, b, dec, mat)) for a, b in KFold(5).split(Xd)]}")
n_emb = int(len(d) * 0.01)
emb = []
for a, b in folds:
    e_ix = int(np.max(b))
    emb.append(int(np.sum((np.asarray(a) > e_ix) & (np.asarray(a) <= e_ix + n_emb))))
print(f"  training rows inside the configured embargo (the {n_emb} row positions after each test block): {emb} (post-test side is over-purged, which is safe)")

print("\n--- A2b decisions sharing one timestamp (memelab decisions share an export commit time) ---")
dd = pd.concat([d, d], ignore_index=True).sort_values("decision_time", kind="mergesort").reset_index(drop=True)
dec2 = dd.decision_time.to_numpy().astype(np.int64)
mat2 = dd.label_matures_at.to_numpy().astype(np.int64)
info2 = pd.Series(pd.to_datetime(mat2, unit="s"), index=pd.to_datetime(dec2, unit="s"))
X2 = pd.DataFrame(C.design(dd, C.FEATURES))
try:
    f2 = list(PurgedKFold(n_splits=5, samples_info_sets=info2, pct_embargo=0.0).split(X2))
    kinds = sorted({type(x).__name__ for a, _ in f2 for x in a})
    print(f"  every decision time twice: PurgedKFold yields train entries of types {kinds} (expected integer positions)")
    try:
        lk2 = [len(L.overlap_leaks(np.concatenate([np.arange(x.start, x.stop) if isinstance(x, slice) else [x] for x in a]), b, dec2, mat2)) for a, b in f2]
        print(f"  after expanding slices, overlap leaks per fold: {lk2}")
    except Exception as e:
        print(f"  could not expand train entries: {type(e).__name__}: {e}")
except Exception as e:
    print(f"  PurgedKFold with shared timestamps: {type(e).__name__}: {str(e)[:140]}")

print("\n--- A3 CombinatorialPurgedKFold ---")
try:
    list(CombinatorialPurgedKFold(n_splits=6, n_test_splits=2, samples_info_sets=info, embargo=0).split(Xd))
    print("  unique decision times: ran")
except Exception as e:
    print(f"  unique decision times: {type(e).__name__}: {e} (combinatorial.py appends a scalar get_loc result, then np.concatenate fails)")
res = {}
for e in (0, 5):
    with warnings.catch_warnings(record=True) as ww:
        warnings.simplefilter("always")
        cv = CombinatorialPurgedKFold(n_splits=6, n_test_splits=2, samples_info_sets=info2, embargo=e)
        fl = []
        gen = cv.split(X2)
        try:
            for item in gen:
                fl.append(item)
        except Exception as ex:
            print(f"  every decision time twice, embargo={e}: generator raised after yielding {len(fl)} splits: "
                  f"{type(ex).__name__}: {str(ex)[:120]} (trailing code after the loop in combinatorial.py; list() or sklearn would fail)")
    res[e] = fl
    print(f"  every decision time twice, embargo={e}: {len(fl)} splits, attribute after split self.embargo={cv.embargo}; "
          f"warnings during split: {len(ww)} ({type(ww[0].message).__name__ + ': ' + str(ww[0].message)[:80] if ww else ''})")
same = all(np.array_equal(np.sort(a1), np.sort(a2)) for (a1, _), (a2, _) in zip(res[0], res[5]))
print(f"  training sets identical for embargo=0 and embargo=5: {same} (combinatorial.py sets self.embargo = 0 inside split)")
cp_leaks = [len(L.overlap_leaks(a, b, dec2, mat2)) for a, b in res[0]]
print(f"  CPCV overlap leaks per split (purge uses the test start correctly here): {cp_leaks}")

print("\n=== PART B: triple-barrier labels versus the memelab T1 rule ===")
STEP = 300


def lab_t1(cand, t_d, obs_end, up=1.25, dn=0.85, horizon=86400):
    """Reference of TARGET_REGISTRY T1: P0 = close of newest candle with end+300 <= t_d and end >= t_d-3600;
    t_entry = t_d + 300; path = candles with start >= t_entry and end <= t_entry + horizon; high >= U, low <= L;
    both in one candle = AMBIGUOUS_BAR (negative); PENDING until t_entry + horizon + 900 <= obs_end."""
    ends = cand.start + STEP
    ref = cand[(ends + 300 <= t_d) & (ends >= t_d - 3600)]
    if ref.empty:
        return "NO_REFERENCE", None
    p0 = float(ref.iloc[-1].close)
    t_entry = t_d + 300
    if obs_end < t_entry + horizon + 900:
        return "PENDING", None
    path = cand[(cand.start >= t_entry) & (cand.start + STEP <= t_entry + horizon)]
    if path.empty:
        return "NO_TRADES_AFTER_ENTRY", 0
    for _, c in path.iterrows():
        u, l_ = c.high >= up * p0, c.low <= dn * p0
        if u and l_:
            return "AMBIGUOUS_BAR", 0
        if u:
            return "TARGET_FIRST", 1
        if l_:
            return "INVALIDATION_FIRST", 0
    return "NEITHER", 0


def make(n_bars, edits, drop=None, base=100.0):
    rows = []
    for i in range(n_bars):
        o = h = l_ = c = base
        rows.append([i * STEP, o, h, l_, c])
    df_ = pd.DataFrame(rows, columns=["start", "open", "high", "low", "close"])
    for i, (h, l_, c) in edits.items():
        df_.loc[i, ["high", "low", "close"]] = [h, l_, c]
        df_.loc[i, "open"] = df_.loc[i - 1, "close"] if i > 0 else base
    if drop is not None:
        df_ = df_[~df_.index.isin(drop)]
    return df_.reset_index(drop=True)


R = 12  # reference bar index; decision exactly when its candle becomes available
N = 12 + 288 + 40
cases = {}
cases["A clean +30% rise"] = (make(N, {R + 10: (131, 100, 130), **{i: (130, 130, 130) for i in range(R + 11, N)}}), None)
cases["B -16% first, then +30%"] = (make(N, {R + 5: (100, 83, 84), R + 20: (131, 100, 130), **{i: (130, 130, 130) for i in range(R + 21, N)}}), None)
cases["C +26% wick only (close stays <= 105)"] = (make(N, {R + 8: (126, 100, 105), **{i: (100, 90, 90) for i in range(R + 100, N)}}), None)
cases["D one candle touches both barriers, then +26% close"] = (make(N, {R + 6: (130, 80, 100), **{i: (126, 126, 126) for i in range(R + 7, N)}}), None)
cases["E exactly +25.0%"] = (make(N, {**{i: (125.0, 125.0, 125.0) for i in range(R + 10, N)}}), None)
cases["F +28% inside the entry gap, flat after entry"] = (make(N, {R + 2: (129, 100, 128)}), None)
cases["G pending: +31% about 5.8 h after the decision, data end about 6.8 h after it"] = (make(R + 84, {R + 72: (131, 100, 131)}), None)
cases["H sparse: no candles from about 2 h to 40 h after the decision, then +31%"] = (make(12 + 480 + 10, {R + 480: (131, 100, 131)}, drop=list(range(R + 24, R + 480))), None)

rows = []
for name, (cand, _) in cases.items():
    t_d = int(cand.start.iloc[R] + STEP + 300)
    obs_end = int(cand.start.iloc[-1] + STEP)
    lab_cls, lab_y = lab_t1(cand, t_d, obs_end)
    close = pd.Series(cand.close.to_numpy(), index=pd.to_datetime(cand.start.to_numpy() + STEP, unit="s"))
    t_ev = pd.DatetimeIndex([close.index[R]])
    vb = add_vertical_barrier(t_ev, close, num_hours=24)
    trgt = pd.Series(0.25, index=close.index)
    out = {}
    for mode, side in (("side=None", None), ("side=+1", pd.Series(1.0, index=t_ev))):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ev = get_events(close, t_ev, pt_sl=[1, 0.6], target=trgt, min_ret=0.0, num_threads=1,
                            vertical_barrier_times=vb, side_prediction=side, verbose=False)
            bins = get_bins(ev, close)
        if len(bins) == 0:
            out[mode] = ("unlabeled", None)
        else:
            b = int(bins["bin"].iloc[0])
            t1h = (ev["t1"].iloc[0] - t_ev[0]).total_seconds() / H
            out[mode] = (f"bin={b} t1=+{t1h:.2f}h", 1 if b == 1 else 0)
    vb_h = (vb.iloc[0] - t_ev[0]).total_seconds() / H if len(vb) else float("nan")
    agree = [(out[m][1] == lab_y) if lab_y is not None else (out[m][1] is None) for m in out]
    rows.append((name, lab_cls, lab_y, out, vb_h, agree))
    print(f"  {name}: memelab T1 -> {lab_cls} (y={lab_y}) | mlfinpy {out['side=None'][0]} (pt_sl=[1,0.6] becomes symmetric +-25%) | "
          f"mlfinpy side=+1 {out['side=+1'][0]} (+25%/-15%) | vertical barrier at +{vb_h:.2f} h | agree None/+1: {agree}")
n_dis = sum(1 for r in rows for a in r[5] if not a)
print(f"  disagreements with the memelab rule: {n_dis} of {2*len(rows)} case-mode pairs")

print("\n--- B2 cost of labeling ---")
rng = np.random.default_rng(1)
nb = 5000
px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, nb)))
close = pd.Series(px, index=pd.to_datetime(np.arange(nb) * STEP + STEP, unit="s"))
t_ev = close.index[::25][:200]
vb = add_vertical_barrier(t_ev, close, num_hours=24)
trgt = pd.Series(0.25, index=close.index)
t0 = time.perf_counter()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ev = get_events(close, t_ev, pt_sl=[1, 0.6], target=trgt, min_ret=0.0, num_threads=1, vertical_barrier_times=vb,
                    side_prediction=pd.Series(1.0, index=t_ev), verbose=False)
    bins = get_bins(ev, close)
dt = time.perf_counter() - t0
print(f"  200 events on 5000 5-minute bars: {dt:.2f} s ({dt/200*1000:.1f} ms per event); labeled {len(bins)}")

print("\n--- S1 leak trap ---")
print("  mlfinpy has no feature-availability notion; its CV purges by samples_info_sets only (and PurgedKFold does so incorrectly, A1/A2)")

print("\n--- S5 persistence ---")
cv = PurgedKFold(n_splits=5, samples_info_sets=info, pct_embargo=0.01)
cv2 = pickle.loads(pickle.dumps(cv))
same = all(np.array_equal(a1, a2) for (a1, _), (a2, _) in zip(cv.split(Xd), cv2.split(Xd)))
print(f"  pickled PurgedKFold yields identical folds: {same}")
print(f"\npeak RSS {C.peak_rss_mb():.1f} MB")

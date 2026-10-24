"""Phase 04 drift check: river's PageHinkley and ADWIN against the numpy Page-Hinkley prototype on two streams, offline.

Streams (time order): the challenge's log liquidity and ret_1h, which carry a designed shift in the last 20% of rows (holdout
rows), and the development sample's log liquidity (no designed shift). For each detector: detection positions, false alarms
before the shift, delay after it, and what happens to a NaN input (river: accepted or refused; prototype: refused).

    python drift_check.py      # bundle venv
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bakeoff as B  # noqa: E402
import core_numpy as K  # noqa: E402


def streams() -> dict:
    rows = list(csv.DictReader(open(B.CHALLENGE)))
    rows.sort(key=lambda r: int(r["decision_time"]))
    shift_at = next(i for i, r in enumerate(rows) if r["split"] == "holdout")
    out = {}
    for name, f in (("challenge_log_liq", lambda r: math.log10(float(r["liq_usd"])) if r["liq_usd"] else float("nan")),
                    ("challenge_ret_1h", lambda r: float(r["ret_1h"]))):
        xs = [f(r) for r in rows]
        keep = [i for i, x in enumerate(xs) if math.isfinite(x)]
        out[name] = {"x": [xs[i] for i in keep], "shift_index": sum(1 for i in keep if i < shift_at), "nan_dropped": len(xs) - len(keep)}
    try:
        d = B.load("dev24")
        xs = [float(v) for v in d["X"][:, 0] if math.isfinite(v)]
        out["dev24_log_liquidity"] = {"x": xs, "shift_index": None, "nan_dropped": int(np.sum(~np.isfinite(d["X"][:, 0])))}
    except FileNotFoundError:
        pass
    return out


def run(det_factory, xs, kind):
    det, hits = det_factory(), []
    for i, x in enumerate(xs):
        if kind == "river":
            det.update(x)
            if det.drift_detected:
                hits.append(i)
        elif det.update(x):
            hits.append(i)
    return hits


def summarize(hits, shift):
    if shift is None:
        return {"detections": len(hits), "positions": hits[:10]}
    before = [h for h in hits if h < shift]
    after = [h for h in hits if h >= shift]
    return {"detections": len(hits), "false_alarms_before_shift": len(before), "first_after_shift": after[0] if after else None,
            "delay_rows": (after[0] - shift) if after else None, "positions": hits[:10]}


def main() -> None:
    from river import drift
    import river
    res = {"river": river.__version__, "streams": {}}
    for name, s in streams().items():
        # standardised by the mean and spread of the first 30% of the stream (a training window), so one threshold fits all
        raw = np.asarray(s["x"], float)
        w = raw[: max(30, int(0.3 * len(raw)))]
        xs, sh = [float(v) for v in (raw - w.mean()) / (w.std() or 1.0)], s["shift_index"]
        entry = {"rows": len(xs), "shift_index": sh, "nan_dropped_before_feeding": s["nan_dropped"]}
        same = True
        for thr in (25.0, 50.0):
            dets = {
                f"river_PageHinkley_t{int(thr)}": (lambda: drift.PageHinkley(threshold=thr), "river"),
                f"numpy_PageHinkley_t{int(thr)}": (lambda: K.PageHinkley(threshold=thr), "numpy"),
            }
            for dn, (fac, kind) in dets.items():
                entry[dn] = summarize(run(fac, xs, kind), sh)
            a, b = entry[f"river_PageHinkley_t{int(thr)}"], entry[f"numpy_PageHinkley_t{int(thr)}"]
            same = same and a == b
        entry["river_ADWIN"] = summarize(run(lambda: drift.ADWIN(), xs, "river"), sh)
        entry["page_hinkley_numpy_equals_river"] = same
        res["streams"][name] = entry
    # NaN behaviour
    ph = drift.PageHinkley()
    for x in [0.1] * 40:
        ph.update(x)
    try:
        ph.update(float("nan"))
        after = [ph.update(0.1) or ph.drift_detected for _ in range(200)]
        res["river_PageHinkley_nan"] = {"raised": False, "detections_in_next_200_constant_inputs": int(sum(after)),
                                        "mean_after": repr(ph._x_mean.get())}
    except Exception as e:  # noqa: BLE001
        res["river_PageHinkley_nan"] = {"raised": True, "error": type(e).__name__}
    ad = drift.ADWIN()
    for x in [0.1] * 40:
        ad.update(x)
    try:
        ad.update(float("nan"))
        res["river_ADWIN_nan"] = {"raised": False, "estimation_after": repr(ad.estimation)}
    except Exception as e:  # noqa: BLE001
        res["river_ADWIN_nan"] = {"raised": True, "error": type(e).__name__}
    try:
        K.PageHinkley().update(float("nan"))
        res["numpy_PageHinkley_nan"] = {"raised": False}
    except ValueError as e:
        res["numpy_PageHinkley_nan"] = {"raised": True, "error": str(e)[:80]}
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()

"""Phase 11 reproducible cohort query: the analog cohort of one development decision as of any time at or before it.

    python -B cohort_query.py --target T1_24h --decision-key KEY --as-of 2026-10-13T00:00:00Z [--model AC3_KNN_REGIME] [--loco]

Builds the pool exactly as the recorded run does (`labels.training_labels` at --as-of through `run_analog.aex_at`, with the
analog-1 inputs and the as-of regime labels), takes the decision's own inputs, and prints the cohort answer of `analog.select`
for every model (or one), the router's `cohort_forecast` and the divergence flags. The decision's own label is never printed or
used. Read-only; no network.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p11_run_analog", HERE / "run_analog.py")
RA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RA)
A, B, C, L, F = RA.A, RA.B, RA.C, RA.L, RA.F


def build(dev_store=None, feature_store=None):
    dev, fs = RA.P7.ro(dev_store or RA.P7.DEV_STORE), RA.P7.ro(feature_store or RA.P7.FEATURE_STORE)
    frows, snaps, info = RA.P7.load_inputs(dev, fs)
    decs = RA.decision_rows(fs)
    series = A.regime_series(RA.regime_rows(decs, frows))
    extras = RA.extras_of(fs, decs, frows, series)
    return dev, frows, snaps, info, extras


def query(ctx, target_short: str, decision_key: str, as_of: float, models=A.MODEL_IDS, loco: bool = False) -> dict:
    dev, frows, snaps, info, extras = ctx
    target = {v: k for k, v in RA.SHORT.items()}[target_short]
    allx = RA.aex_at(dev, target, RA.H, frows, snaps, info, extras)[0]
    tgt = next((e for e in allx if e.decision_key == decision_key), None)
    if tgt is None:
        raise SystemExit("not a labelled development decision of this target")
    pool = RA.aex_at(dev, target, as_of, frows, snaps, info, extras)[0]
    out = {"target": target, "decision_key": decision_key, "mint": tgt.mint, "decision_time_utc": B._iso(tgt.decision_time),
           "as_of_utc": B._iso(as_of), "regime": tgt.regime, "pool_n": len(pool), "answers": {}}
    for m in models:
        a = A.select(m, tgt, pool, as_of=as_of, loco=loco)
        a.pop("decision_time", None)
        out["answers"][m] = a
    f = A.cohort_forecast(tgt, pool, as_of=as_of)
    f.pop("cohort", None)
    out["router"] = f
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=sorted(RA.SHORT.values()))
    ap.add_argument("--decision-key", required=True)
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--model", default=None, choices=A.MODEL_IDS)
    ap.add_argument("--loco", action="store_true")
    a = ap.parse_args()
    res = query(build(), a.target, a.decision_key, C.parse_utc(a.as_of), models=(a.model,) if a.model else A.MODEL_IDS, loco=a.loco)
    print(json.dumps(res, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Phase 04 schema check: pandera (DataFrame schema with the lab's registered checks) against the lab's own fail-closed row
validator (core_numpy.validate_rows, plain Python over dict rows, as the lab stores data) on one clean table and four traps:
a feature available one second after its decision (P36), a missing availability time, an undeclared column (the challenge's
leak_future_ret), and a label that has not matured by the training cutoff (P05). Both must accept the clean table and refuse
every trap. Also records what importing pandera changes in the process (environment variables, numpy attributes).

    python schema_check.py      # bundle venv, offline
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bakeoff as B  # noqa: E402
import core_numpy as K  # noqa: E402

COLS = ["decision_time", "feature_available_at", "label_matures_at", "x0", "x1", "y"]


def table(name: str) -> tuple[list[dict], float]:
    d = B.load(name)
    rows = [{"decision_time": float(t), "feature_available_at": float(t), "label_matures_at": float(m),
             "x0": float(x[0]), "x1": float(x[1]), "y": float(y)} for t, m, x, y in zip(d["t"], d["m"], d["X"], d["y"])]
    return rows, float(max(d["m"]))


def traps(rows: list[dict], as_of: float) -> dict:
    out = {"clean": rows}
    r = copy.deepcopy(rows); r[len(r) // 2]["feature_available_at"] += 1.0; out["future_feature_1s"] = r
    r = copy.deepcopy(rows); r[3]["feature_available_at"] = float("nan"); out["missing_availability"] = r
    r = copy.deepcopy(rows); r[0]["leak_future_ret"] = 0.3
    for x in r[1:]:
        x["leak_future_ret"] = 0.0
    out["undeclared_column"] = r
    r = copy.deepcopy(rows); r[-1]["label_matures_at"] = as_of + 60.0; out["immature_label"] = r
    return out


def lab_check(rows, as_of):
    try:
        K.validate_rows(rows, columns=COLS, availability=["feature_available_at"], as_of=as_of)
        return "accepted"
    except K.AsOfError as e:
        return "refused: " + str(e)[:90]


def pandera_schema(pa, as_of):
    return pa.DataFrameSchema(
        {c: pa.Column(float, nullable=(c in ("x0", "x1"))) for c in COLS},
        checks=[pa.Check(lambda df: df["feature_available_at"] <= df["decision_time"], name="available_at_le_decision"),
                pa.Check(lambda df: df["y"].isna() | (df["label_matures_at"] <= as_of), name="label_only_when_matured")],
        strict=True)


def main() -> None:
    import pandas as pd
    env0, np0 = set(os.environ), set(dir(np))
    t0 = time.perf_counter()
    import pandera.pandas as pa
    import pandera
    import_s = time.perf_counter() - t0
    env_added = sorted(set(os.environ) - env0)
    np_added = sorted(set(dir(np)) - np0)
    timing = []
    res = {"pandera": pandera.__version__,
           "pandera_import_side_effects": {"environ_added": env_added, "numpy_attributes_added": np_added}, "datasets": {}}
    for name in ("challenge", "dev24"):
        try:
            rows, as_of = table(name)
        except FileNotFoundError:
            continue
        entry = {}
        for tname, r in traps(rows, as_of).items():
            t1 = time.perf_counter(); lab = lab_check(r, as_of); lab_s = time.perf_counter() - t1
            df = pd.DataFrame(r)
            t2 = time.perf_counter()
            try:
                pandera_schema(pa, as_of).validate(df, lazy=True)
                pv = "accepted"
            except (pa.errors.SchemaErrors, pa.errors.SchemaError) as e:
                pv = "refused: " + type(e).__name__
            pv_s = time.perf_counter() - t2
            entry[tname] = {"lab": lab, "pandera": pv}
            timing.append({"dataset": name, "trap": tname, "lab_ms": round(1000 * lab_s, 2), "pandera_ms": round(1000 * pv_s, 2)})
        entry["agree_and_correct"] = all((v["lab"] == "accepted") == (k == "clean") and (v["pandera"] == "accepted") == (k == "clean")
                                         for k, v in entry.items())
        entry["rows"] = len(rows)
        res["datasets"][name] = entry
    print(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps({"pandera_import_s_in_process": round(import_s, 3), "timing": timing}), file=sys.stderr)


if __name__ == "__main__":
    main()

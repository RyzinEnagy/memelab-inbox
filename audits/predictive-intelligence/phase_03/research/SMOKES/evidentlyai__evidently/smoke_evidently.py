"""Phase 03 R4 smoke for evidently at the pin (run offline, DO_NOT_TRACK=1).

Role: drift and monitoring. Also S1..S6 as far as they fit a monitoring library.
"""
import json
import os
import sys
import tempfile
import time
import warnings
from datetime import datetime

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

warnings.filterwarnings("ignore")
from evidently import BinaryClassification, DataDefinition, Dataset, Report  # noqa: E402
from evidently.core.report import Snapshot  # noqa: E402
from evidently.metrics import LogLoss, RocAuc, ValueDrift  # noqa: E402
from evidently.presets import DataDriftPreset  # noqa: E402

FIXED_TS = datetime(2026, 10, 24, 0, 0, 0)
F = C.FEATURES
df = C.load()
tr, va, ho = (df[df.split == s].copy() for s in ("train", "val", "holdout"))
C.emit("rows", {"train": len(tr), "val": len(va), "holdout": len(ho), "holdout_censored": int(ho.label.isna().sum())})


def drift(ref, cur, method=None):
    t0 = time.perf_counter()
    kw = {"num_method": method} if method == "ks" else {"method": method}
    snap = Report([DataDriftPreset(columns=F, **kw)], include_tests=True).run(cur[F], ref[F], timestamp=FIXED_TS)
    dt = time.perf_counter() - t0
    d = snap.dict()
    vals = {}
    for m in d["metrics"]:
        cfg = m["config"]
        if cfg["type"].endswith("ValueDrift"):
            vals[cfg["column"]] = {"score": round(float(m["value"]), 5), "method": cfg["method"], "threshold": cfg["threshold"]}
    for t in d["tests"]:
        if t["id"] == "drift":
            col = t["metric_config"]["params"]["column"]
            vals[col]["drift"] = t["status"] == "FAIL"
    flagged = sorted(c for c, v in vals.items() if v.get("drift"))
    return {"flagged": flagged, "per_column": vals, "seconds": round(dt, 3)}, snap


# ---- Role: drift detection and false alarms ----
role = {}
for method in (None, "psi", "ks"):
    key = method or "default"
    r_val, _ = drift(tr, va, method)
    r_ho, _ = drift(tr, ho, method)
    half = len(tr) // 2
    r_tt, _ = drift(tr.iloc[:half], tr.iloc[half:], method)
    # chunked monitoring: val and holdout in chunks of 150 rows against the full train reference
    chunks = []
    for name, part in (("val", va), ("holdout", ho)):
        for i in range(0, len(part) - 149, 150):
            r, _ = drift(tr, part.iloc[i:i + 150], method)
            chunks.append({"split": name, "start": i, "flagged": r["flagged"]})
    fa_val_chunks = sum(len(c["flagged"]) for c in chunks if c["split"] == "val")
    n_val_chunks = sum(1 for c in chunks if c["split"] == "val")
    ho_chunks = [c for c in chunks if c["split"] == "holdout"]
    role[key] = {
        "train_vs_val": r_val, "train_vs_holdout": r_ho, "train_first_half_vs_second_half": r_tt,
        "chunks": chunks,
        "false_alarm_columns_train_vs_val": len(r_val["flagged"]),
        "false_alarm_columns_train_halves": len(r_tt["flagged"]),
        "false_alarm_column_flags_in_val_chunks": f"{fa_val_chunks} flags over {n_val_chunks} chunks x 6 columns",
        "holdout_detected_expected": sorted(set(r_ho["flagged"]) & {"liq_usd", "ret_1h"}),
        "holdout_extra_flags": sorted(set(r_ho["flagged"]) - {"liq_usd", "ret_1h"}),
        "holdout_chunks_detecting_both": sum(1 for c in ho_chunks if {"liq_usd", "ret_1h"} <= set(c["flagged"])),
        "holdout_chunks": len(ho_chunks),
    }
    C.emit(f"ROLE_drift_{key}", {k: v for k, v in role[key].items() if k != "chunks"})

# ---- S3: NaN handling in drift ----
r_nan, _ = drift(tr, ho)
r_drop, _ = drift(tr.dropna(subset=["liq_usd"]), ho.dropna(subset=["liq_usd"]))
C.emit("S3_nan", {
    "train_nan_liq": int(tr.liq_usd.isna().sum()), "holdout_nan_liq": int(ho.liq_usd.isna().sum()),
    "score_with_nan": r_nan["per_column"]["liq_usd"]["score"], "score_after_dropna": r_drop["per_column"]["liq_usd"]["score"],
    "silently_dropped": r_nan["per_column"]["liq_usd"]["score"] == r_drop["per_column"]["liq_usd"]["score"],
})

# ---- S1: leak trap, evaluated with evidently classification metrics on matured holdout rows ----
trm, hom = C.matured(tr), C.matured(ho)
prev = float(trm.label.mean())
res = {}
for name, cols in (("legit", F), ("with_trap", F + [C.TRAP])):
    model = C.fit_baseline(trm, cols)
    p = model.predict_proba(C.log_feats(hom, cols))[:, 1]
    cur = pd.DataFrame({"label": hom.label.astype(int).values, "proba": p})
    dd = DataDefinition(classification=[BinaryClassification(target="label", prediction_probas="proba")],
                        numerical_columns=["proba"])
    snap = Report([RocAuc(), LogLoss()]).run(Dataset.from_pandas(cur, data_definition=dd), None, timestamp=FIXED_TS)
    ev = {m["metric_name"].split("(")[0]: m["value"] for m in snap.dict()["metrics"]}
    res[name] = {"evidently": ev, "sklearn": C.scores(hom.label, p, prev)}
C.emit("S1_leak", {**res, "note": "evidently has no availability-time or feature-cutoff concept; nothing stopped the trap column"})

# ---- S2: probability checks (P38) and censored labels (P05) ----
model = C.fit_baseline(trm, F)
p_all = model.predict_proba(C.log_feats(ho, F))[:, 1]
s2 = {"sklearn_matured": C.scores(hom.label, model.predict_proba(C.log_feats(hom, F))[:, 1], prev), "train_prevalence": prev}


def run_cls(frame):
    dd = DataDefinition(classification=[BinaryClassification(target="label", prediction_probas="proba")],
                        numerical_columns=["proba"])
    try:
        snap = Report([RocAuc(), LogLoss()]).run(Dataset.from_pandas(frame, data_definition=dd), None, timestamp=FIXED_TS)
        return {m["metric_name"].split("(")[0]: m["value"] for m in snap.dict()["metrics"]}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


base = pd.DataFrame({"label": ho.label.values, "proba": p_all})
s2["with_censored_rows_label_nan"] = run_cls(base)
s2["matured_only"] = run_cls(base[base.label.notna()].astype({"label": int}))
bad = base[base.label.notna()].astype({"label": int}).reset_index(drop=True)
bad.loc[0, "proba"] = 1.5
s2["proba_1_5_injected"] = run_cls(bad)
bad2 = base[base.label.notna()].astype({"label": int}).reset_index(drop=True)
bad2.loc[0, "proba"] = np.nan
s2["proba_nan_injected"] = run_cls(bad2)
C.emit("S2_probs", s2)

# ---- S4: calibration or uncertainty offered ----
C.emit("S4_calibration", {"offered": "none for probabilities (no Brier, no reliability curve, no recalibration); drift tests give a score and a fixed threshold, p-value tests give p-values"})

# ---- S5: persistence ----
r_ho, snap = drift(tr, ho)
work = tempfile.mkdtemp(prefix="ev_smoke_")
path = os.path.join(work, "snap.json")
snap.save_json(path)  # simplified dict
full = snap.dumps()
back = Snapshot.loads(full)
same = json.dumps(back.dict(), sort_keys=True, default=str) == json.dumps(snap.dict(), sort_keys=True, default=str)
C.emit("S5_persist", {"format": "JSON (pydantic SnapshotModel), no pickle", "full_dump_bytes": len(full),
                      "roundtrip_dict_identical": same, "simplified_json_bytes": os.path.getsize(path)})

# ---- S6: cost ----
t0 = time.perf_counter()
for _ in range(3):
    Report([DataDriftPreset(columns=F)]).run(ho[F], tr[F], timestamp=FIXED_TS)
per = (time.perf_counter() - t0) / 3
t0 = time.perf_counter()
Report([ValueDrift(column="liq_usd")]).run(ho[F], tr[F], timestamp=FIXED_TS)
one = time.perf_counter() - t0
C.emit("S6_cost", {"drift_report_6cols_1800ref_600cur_s": round(per, 3), "single_column_drift_s": round(one, 3)})
print("DONE")

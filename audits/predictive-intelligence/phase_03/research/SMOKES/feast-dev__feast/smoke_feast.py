# Phase 03 smoke harness (shared header, reviewer R1). Synthetic challenge data only:
# results show format and behaviour, never memecoin predictive value.
# Usage: python -I <script> <challenge.csv> <scratch_out_dir>
import csv
import hashlib
import json
import math
import os
import platform
import resource
import socket
import sys
import time
import warnings

import numpy as np

CHALLENGE = sys.argv[1]
SCRATCH = sys.argv[2]
os.makedirs(SCRATCH, exist_ok=True)
RESULTS = {"script": os.path.basename(__file__), "python": sys.version.split()[0],
           "platform": platform.platform(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

# Network guard: every AF_INET/AF_INET6 connect is recorded and refused, so any phone-home
# at import, fit or predict shows up as an attempt (and usually an exception).
NET_ATTEMPTS = []
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _guard_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        NET_ATTEMPTS.append(repr(address))
        raise OSError("network blocked by phase03 smoke guard: %r" % (address,))
    return _orig_connect(self, address)


def _guard_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        NET_ATTEMPTS.append(repr(address))
        return 111
    return _orig_connect_ex(self, address)


socket.socket.connect = _guard_connect
socket.socket.connect_ex = _guard_connect_ex

FEATURES = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
LOG_FEATURES = {"liq_usd", "vol_24h"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(v):
    return float("nan") if v == "" else float(v)


def load():
    with open(CHALLENGE, newline="") as fh:
        rows = list(csv.DictReader(fh))
    d = {}
    for col in rows[0].keys():
        vals = [r[col] for r in rows]
        if col in ("decision_id", "mint", "symbol", "split"):
            d[col] = np.array(vals)
        else:
            d[col] = np.array([fnum(v) for v in vals])
    order = np.argsort(d["decision_time"], kind="stable")
    for k in d:
        d[k] = d[k][order]
    return d


def matrix(d, idx, with_leak=False, log=True):
    cols = []
    names = []
    for f in FEATURES:
        x = d[f][idx].astype(float)
        if log and f in LOG_FEATURES:
            x = np.log(x)
        cols.append(x)
        names.append(("log_" + f) if (log and f in LOG_FEATURES) else f)
    if with_leak:
        cols.append(d["leak_future_ret"][idx])
        names.append("leak_future_ret")
    return np.column_stack(cols), names


def splits(d):
    s = d["split"]
    lab = ~np.isnan(d["label"])
    out = {k: np.where((s == k) & lab)[0] for k in ("train", "val", "holdout")}
    out["holdout_censored"] = int(((s == "holdout") & ~lab).sum())
    out["embargo"] = int((s == "embargo").sum())
    return out


def brier(y, p):
    return float(np.mean((p - y) ** 2))


def logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(y, p):
    # Mann-Whitney AUC with ties averaged, no library dependency
    y = np.asarray(y)
    p = np.asarray(p)
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sp = p[order]
    i = 0
    while i < len(sp):
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def score_block(y, p, base):
    p = np.asarray(p, dtype=float)
    b = brier(y, p)
    b0 = brier(y, np.full_like(p, base))
    return {"n": int(len(y)), "positives": int(y.sum()), "brier": round(b, 6), "brier_b0": round(b0, 6),
            "bss_vs_b0": round(1 - b / b0, 4) if b0 > 0 else None, "logloss": round(logloss(y, p), 6),
            "logloss_b0": round(logloss(y, np.full_like(p, base)), 6), "auc": round(auc(y, p), 4),
            "mean_p": round(float(p.mean()), 5), "min_p": float(p.min()), "max_p": float(p.max()),
            "finite": bool(np.all(np.isfinite(p))), "in_0_1": bool(np.all((p >= 0) & (p <= 1)))}


def reliability(y, p, n_bins=3):
    # quantile bins (the lab's rule: >= 20 events per bin, at most 5 bins), Wilson check per bin
    order = np.argsort(p, kind="stable")
    bins = np.array_split(order, n_bins)
    out = []
    for b in bins:
        k = int(y[b].sum())
        lo, hi = wilson(k, len(b))
        mp = float(p[b].mean())
        out.append({"n": int(len(b)), "mean_p": round(mp, 4), "obs": round(k / len(b), 4),
                    "wilson95": [round(lo, 4), round(hi, 4)], "inside": bool(lo <= mp <= hi)})
    return out


def maturity_violations(d, train_idx, test_idx):
    # training rows whose label matures after the first test decision: a look-ahead in labels
    t0 = d["decision_time"][test_idx].min()
    return int((d["label_matures_at"][train_idx] > t0).sum())


def day_walk_forward(d, idx, min_train=200):
    # the lab's rule (ACCEPTANCE_METRICS): expanding window by UTC decision day; each fold trains only on
    # labels matured by the first decision of the test day. Custom code, not a library feature.
    t = d["decision_time"][idx]
    mat = d["label_matures_at"][idx]
    days = np.floor(t / 86400).astype(int)
    out = []
    for day in np.unique(days):
        te = idx[days == day]
        start = t[days == day].min()
        tr = idx[mat <= start]
        if len(tr) >= min_train:
            out.append((tr, te))
    return out


def peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return r, time.perf_counter() - t


def single_row_latency(fn, X, reps=200):
    ts = []
    for i in range(reps):
        row = X[i % len(X):i % len(X) + 1]
        t = time.perf_counter()
        fn(row)
        ts.append(time.perf_counter() - t)
    return {"median_ms": round(1000 * float(np.median(ts)), 4), "p90_ms": round(1000 * float(np.percentile(ts, 90)), 4)}


def finish():
    RESULTS["network_attempts"] = NET_ATTEMPTS
    RESULTS["peak_rss_mb"] = peak_rss_mb()
    RESULTS["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("RESULTS_JSON " + json.dumps(RESULTS, sort_keys=True, default=str))


D = load()
SP = splits(D)
RESULTS["challenge_sha256"] = sha256_file(CHALLENGE)
RESULTS["counts"] = {"train": len(SP["train"]), "val": len(SP["val"]), "holdout_scored": len(SP["holdout"]),
                     "holdout_censored_excluded": SP["holdout_censored"], "embargo_rows_unused": SP["embargo"]}
YTR = D["label"][SP["train"]].astype(int)
YVA = D["label"][SP["val"]].astype(int)
YHO = D["label"][SP["holdout"]].astype(int)
BASE = float(YTR.mean())
RESULTS["train_prevalence_b0"] = round(BASE, 5)
# ---- end of shared header ----

# ---- feast body (point-in-time join semantics, local dask offline store, sqlite online store) ----
import logging
import shutil
from datetime import datetime, timedelta, timezone

import pandas as pd

t_imp0 = time.perf_counter()
import feast  # noqa: E402
from feast import Entity, FeatureStore, FeatureView, Field, FileSource  # noqa: E402
from feast.repo_config import RepoConfig  # noqa: E402
from feast.types import Float64, Int64  # noqa: E402

logging.getLogger("feast").setLevel(logging.ERROR)
RESULTS["library"] = {"feast": feast.__version__, "path": feast.__file__, "import_s": round(time.perf_counter() - t_imp0, 3)}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)

REPO = os.path.join(SCRATCH, "feast_repo")
shutil.rmtree(REPO, ignore_errors=True)
os.makedirs(os.path.join(REPO, "data"))


def ts(sec):
    return datetime.fromtimestamp(int(sec), tz=timezone.utc)


def store():
    cfg = RepoConfig(project="pi_smoke", provider="local", registry=os.path.join(REPO, "data", "registry.db"),
                     online_store={"type": "sqlite", "path": os.path.join(REPO, "data", "online.db")},
                     offline_store={"type": "dask"}, entity_key_serialization_version=3, repo_path=REPO)
    return FeatureStore(config=cfg)


mint = Entity(name="mint", join_keys=["mint"])

# ---- part A: exact semantics on a hand-built table ----
T = 1_790_000_000
semantic = pd.DataFrame({
    "mint": ["A", "A", "A", "B"],
    "symbol": ["SYM", "SYM", "SYM", "SYM"],
    "v": [1.0, 2.0, 99.0, 50.0],
    "available_at": [ts(T + 1000), ts(T + 2000), ts(T + 2000), ts(T + 1500)],
    "created_at": [ts(T + 1000), ts(T + 2000), ts(T + 5000), ts(T + 1500)],  # row 3 is a late revision of row 2
})
p_sem = os.path.join(REPO, "data", "semantic.parquet")
semantic.to_parquet(p_sem)
src_sem = FileSource(name="sem_src", path=p_sem, timestamp_field="available_at", created_timestamp_column="created_at")
fv_sem = FeatureView(name="sem", entities=[mint], ttl=timedelta(seconds=3600), schema=[Field(name="v", dtype=Float64)],
                     source=src_sem)
fs = store()
fs.apply([mint, fv_sem])
RESULTS["network_attempts_after_apply"] = list(NET_ATTEMPTS)
probe = pd.DataFrame({
    "mint": ["A", "A", "A", "A", "A", "B", "A", "A"],
    "event_timestamp": [ts(T + 999), ts(T + 1999), ts(T + 2000), ts(T + 5000), ts(T + 2000 + 3601), ts(T + 2000),
                        ts(T + 4000), ts(T + 4000)],
    "case": ["before_first", "one_s_before_second", "exactly_at_second", "after_revision_known",
             "beyond_ttl", "other_mint_same_symbol", "dup_entity_row_1", "dup_entity_row_2"],
})
out = {}
for flag in (False, True):
    df = fs.get_historical_features(entity_df=probe, features=["sem:v"], filter_by_created_timestamp=flag).to_df()
    key = "filter_by_created_timestamp_%s" % flag
    out[key] = {"rows_in": len(probe), "rows_out": len(df),
                "by_case": {str(c): (None if pd.isna(v) else float(v)) for c, v in zip(df["case"], df["v"])}}
    out[key]["output_order_same_as_input"] = list(df["case"]) == list(probe["case"])
    out[key]["cases_missing_from_output"] = sorted(set(probe["case"]) - set(df["case"]))
RESULTS["pit_semantics"] = out
RESULTS["pit_semantics_expected"] = {
    "before_first": None, "one_s_before_second": 1.0, "exactly_at_second": "2.0 if filter True (inclusive <=); 99.0 if the late revision wins",
    "after_revision_known": 99.0, "beyond_ttl": None, "other_mint_same_symbol": 50.0, "dup_entity_row": 99.0}

# ---- part B: challenge-derived tables, leak trap through availability time ----
ch = pd.DataFrame({"mint": D["mint"], "decision_id": D["decision_id"], "split": D["split"],
                   "decision_ts": [ts(x) for x in D["decision_time"]],
                   "leak_ts": [ts(x) for x in D["leak_available_at"]],
                   "liq_usd": D["liq_usd"], "vol_24h": D["vol_24h"], "ret_1h": D["ret_1h"],
                   "leak_future_ret": D["leak_future_ret"], "label": D["label"]})
p_feat = os.path.join(REPO, "data", "snap.parquet")
p_leak = os.path.join(REPO, "data", "leak.parquet")
ch[["mint", "decision_ts", "liq_usd", "vol_24h", "ret_1h"]].to_parquet(p_feat)
ch[["mint", "decision_ts", "leak_ts", "leak_future_ret"]].to_parquet(p_leak)
fv_snap = FeatureView(name="snap", entities=[mint], ttl=timedelta(hours=24),
                      schema=[Field(name="liq_usd", dtype=Float64), Field(name="vol_24h", dtype=Float64),
                              Field(name="ret_1h", dtype=Float64)],
                      source=FileSource(name="snap_src", path=p_feat, timestamp_field="decision_ts"))
fv_leak_ok = FeatureView(name="leak_by_availability", entities=[mint], ttl=timedelta(days=30),
                         schema=[Field(name="leak_future_ret", dtype=Float64)],
                         source=FileSource(name="leak_src_ok", path=p_leak, timestamp_field="leak_ts"))
fv_leak_bad = FeatureView(name="leak_by_decision_time", entities=[mint], ttl=timedelta(days=30),
                          schema=[Field(name="leak_future_ret", dtype=Float64)],
                          source=FileSource(name="leak_src_bad", path=p_leak, timestamp_field="decision_ts"))
fs.apply([fv_snap, fv_leak_ok, fv_leak_bad])
ent = ch[["mint", "decision_ts", "decision_id"]].rename(columns={"decision_ts": "event_timestamp"})
job, t_get = timed(lambda: fs.get_historical_features(
    entity_df=ent, features=["snap:liq_usd", "snap:vol_24h", "snap:ret_1h", "leak_by_availability:leak_future_ret",
                             "leak_by_decision_time:leak_future_ret"], full_feature_names=True).to_df())
missing_ids = sorted(set(ch["decision_id"]) - set(job["decision_id"]))
dup_out = int(job["decision_id"].duplicated().sum())
res = job.drop_duplicates("decision_id").set_index("decision_id").reindex(ch["decision_id"])
own = ch["leak_future_ret"].to_numpy()
ok = res["leak_by_availability__leak_future_ret"].to_numpy()
bad = res["leak_by_decision_time__leak_future_ret"].to_numpy()
hold = (ch["split"].to_numpy() == "holdout") & ~np.isnan(ch["label"].to_numpy())
yh = ch["label"].to_numpy()[hold].astype(int)


def auc_nan(y, x):
    m = ~np.isnan(x)
    return {"n_non_null": int(m.sum()), "auc": round(auc(y[m], x[m]), 4) if m.sum() > 1 else None}


ret_mask = ~ch["decision_id"].isin(missing_ids).to_numpy()
snap_equal = np.allclose(res["snap__liq_usd"].to_numpy()[ret_mask], ch["liq_usd"].to_numpy()[ret_mask], equal_nan=True)
RESULTS["S1_leak_trap"] = {
    "rows": len(ch), "rows_out": len(job), "wall_s_get_historical_features": round(t_get, 3),
    "entity_rows_missing_from_output": len(missing_ids), "missing_examples": missing_ids[:5],
    "duplicate_rows_in_output": dup_out,
    "snapshot_features_equal_own_row_on_returned_rows": bool(snap_equal),
    "timestamp_field_is_availability_time": {
        "rows_returning_own_future_value": int(np.sum(np.isclose(ok, own))),
        "rows_null": int(np.isnan(ok).sum()),
        "holdout_auc_of_joined_value_vs_label": auc_nan(yh, ok[hold])},
    "timestamp_field_is_decision_time_misconfigured": {
        "rows_returning_own_future_value": int(np.sum(np.isclose(bad, own))),
        "holdout_auc_of_joined_value_vs_label": auc_nan(yh, bad[hold])},
    "note": "Feast enforces event_timestamp <= entity timestamp; whether that equals availability depends on which column the source declares",
}
per_view = {}
first_feature_ts = ch.groupby("mint")["decision_ts"].transform("min")
first_leak_ts = ch.groupby("mint")["leak_ts"].transform("min")
for fref, first in (("snap:liq_usd", first_feature_ts), ("leak_by_availability:leak_future_ret", first_leak_ts),
                    ("leak_by_decision_time:leak_future_ret", first_feature_ts)):
    o = fs.get_historical_features(entity_df=ent, features=[fref]).to_df()
    expected_drop = int((ch["decision_ts"] < first).sum())
    per_view[fref] = {"rows_out": len(o), "rows_missing": len(ch) - o["decision_id"].nunique(),
                      "entity_rows_whose_mint_has_only_later_feature_rows": expected_drop}
RESULTS["S1_leak_trap"]["per_view_row_counts"] = per_view
RESULTS["S2_S5_model_smokes"] = "SKIPPED: Feast is a feature store, it fits no model and emits no probabilities"
RESULTS["S6_cost"] = {"get_historical_features_3000_rows_3_views_s": round(t_get, 3),
                      "repo_files": sorted(os.listdir(os.path.join(REPO, "data")))}
finish()

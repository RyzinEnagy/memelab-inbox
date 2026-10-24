"""Phase 03 R4 smoke for MLflow (run offline): local run registry and model lineage without a server.

Tracking store: sqlite file in a temp dir (MLflow's own default is sqlite:///mlflow.db in the cwd); artifacts on local disk.
"""
import hashlib
import json
import os
import sys
import tempfile
import time
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

t_imp = time.perf_counter()
import mlflow  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.models import infer_signature  # noqa: E402

IMPORT_S = time.perf_counter() - t_imp
warnings.filterwarnings("ignore")
work = tempfile.mkdtemp(prefix="mlf_")
C.emit("env", {"mlflow_version": mlflow.__version__, "import_s": round(IMPORT_S, 3),
               "default_tracking_uri_before_set": mlflow.get_tracking_uri(), "workdir": work})
mlflow.set_tracking_uri(f"sqlite:///{work}/mlflow.db")
mlflow.set_registry_uri(f"sqlite:///{work}/mlflow.db")
exp_id = mlflow.create_experiment("pi_r4_smoke", artifact_location=f"file://{work}/artifacts")

F = C.FEATURES
df = C.load()
tr, va, ho = (df[df.split == s].copy() for s in ("train", "val", "holdout"))
trm, hom = C.matured(tr), C.matured(ho)
prev = float(trm.label.mean())
CUTOFF = int(trm.label_matures_at.max())  # last label maturity time used in training


def log_one(name, cols):
    model = C.fit_baseline(trm, cols)
    Xtr = C.log_feats(trm, cols)
    Xho = C.log_feats(hom, cols)
    p = model.predict_proba(Xho)[:, 1]
    t0 = time.perf_counter()
    with mlflow.start_run(experiment_id=exp_id, run_name=name) as run:
        mlflow.log_params({"feature_set": json.dumps(cols), "training_label_cutoff_epoch": CUTOFF,
                           "train_rows": len(trm), "seed": C.SEED, "model": "logreg+median_impute"})
        ds = mlflow.data.from_pandas(trm[cols + ["label"]], targets="label", name="train_matured")
        mlflow.log_input(ds, context="training")
        mlflow.log_metrics({k: v for k, v in C.scores(hom.label, p, prev).items() if isinstance(v, float)})
        sig = infer_signature(Xtr, model.predict_proba(Xtr))
        info = mlflow.sklearn.log_model(model, name="model", signature=sig, input_example=Xtr.head(3),
                                        pyfunc_predict_fn="predict_proba", registered_model_name="pi_r4_baseline")
    log_s = time.perf_counter() - t0
    return model, run.info.run_id, info, log_s, ds


model, run_id, info, log_s, ds = log_one("legit", F)
client = MlflowClient()
mv = client.get_model_version("pi_r4_baseline", "1")
run = client.get_run(mv.run_id)
art_dir = mlflow.artifacts.download_artifacts(info.model_uri, dst_path=os.path.join(work, "dl"))
files = sorted(os.listdir(art_dir))
mlmodel = open(os.path.join(art_dir, "MLmodel")).read()
sha = {f: hashlib.sha256(open(os.path.join(art_dir, f), "rb").read()).hexdigest()[:16] for f in files if os.path.isfile(os.path.join(art_dir, f))}
C.emit("LINEAGE", {
    "model_version": mv.version, "model_version_run_id_matches": mv.run_id == run_id, "source": mv.source,
    "run_params": run.data.params,
    "dataset_inputs": [{"name": d.dataset.name, "digest": d.dataset.digest, "source_type": d.dataset.source_type,
                        "context": [t.value for t in d.tags]} for d in run.inputs.dataset_inputs],
    "signature_inputs": [c["name"] for c in json.loads(mlmodel.split("inputs: '")[1].split("'\n")[0])] if "inputs: '" in mlmodel else None,
    "artifact_files": files, "artifact_sha256_prefix_computed_by_reviewer": sha,
    "mlmodel_has_any_hash_field": any(k in mlmodel for k in ("sha256", "md5", "checksum", "hash")),
    "mlmodel_fields": [ln.split(":")[0] for ln in mlmodel.splitlines() if ln and not ln.startswith(" ")],
    "log_and_register_s": round(log_s, 3),
})
# wrapper-side lineage: tag the version with sha256 of the serialized model and the data file
model_file = [f for f in files if f.startswith("model.")][0]
model_sha = hashlib.sha256(open(os.path.join(art_dir, model_file), "rb").read()).hexdigest()
client.set_model_version_tag("pi_r4_baseline", "1", "model_sha256", model_sha)
client.set_model_version_tag("pi_r4_baseline", "1", "challenge_sha256", C.CHALLENGE_SHA256)
C.emit("LINEAGE_tags", client.get_model_version("pi_r4_baseline", "1").tags)

# digest weakness: change one value after row 10,000 is impossible here (1,746 rows); show digest changes with any value change
d1 = mlflow.data.from_pandas(trm[F + ["label"]], targets="label").digest
alt = trm[F + ["label"]].copy()
alt.iloc[-1, 0] = (alt.iloc[-1, 0] or 0) + 1
d2 = mlflow.data.from_pandas(alt, targets="label").digest
C.emit("DATASET_DIGEST", {"digest": d1, "len": len(d1), "changes_when_last_row_changes": d1 != d2,
                          "note": "8-character md5 over the first 10,000 rows plus row count and column names (mlflow/data/digest_utils.py)"})

# ---- S5: reload by registry URI, identical predictions ----
t0 = time.perf_counter()
loaded = mlflow.pyfunc.load_model("models:/pi_r4_baseline/1")
load_s = time.perf_counter() - t0
Xho = C.log_feats(hom, F)
pp = np.asarray(loaded.predict(Xho))
ref = model.predict_proba(Xho)
C.emit("S5_persist", {"model_file": model_file, "pyfunc_output_shape": list(pp.shape),
                      "identical_to_in_memory_predict_proba": bool(np.array_equal(pp, ref)), "load_s": round(load_s, 3)})

# ---- S2: probability output shape and range ----
p1 = pp[:, 1]
C.emit("S2_probs", {"pyfunc_predict_fn": "predict_proba", "columns": int(pp.shape[1]), "finite": bool(np.isfinite(pp).all()),
                    "in_0_1": bool(((pp >= 0) & (pp <= 1)).all()), "scores": C.scores(hom.label, p1, prev),
                    "default_pyfunc_predict_fn": "predict (class labels) unless pyfunc_predict_fn is set"})

# ---- S3: NaN in inputs against the logged signature ----
s3 = {}
x = Xho.head(5).copy()
x.iloc[0, x.columns.get_loc("liq_usd")] = np.nan
try:
    s3["nan_in_float_column"] = {"ok": True, "out": np.asarray(loaded.predict(x))[0].round(5).tolist()}
except Exception as e:  # noqa: BLE001
    s3["nan_in_float_column"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
x2 = Xho.head(5).copy()
x2["extra_col"] = 1.0
try:
    loaded.predict(x2)
    s3["extra_column"] = {"ok": True}
except Exception as e:  # noqa: BLE001
    s3["extra_column"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
x3 = Xho.head(5).drop(columns=["ret_1h"])
try:
    loaded.predict(x3)
    s3["missing_column"] = {"ok": True}
except Exception as e:  # noqa: BLE001
    s3["missing_column"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
C.emit("S3_schema", s3)

# ---- S1: leak trap: the trap model is logged and registered like any other ----
m2, run2, info2, _, _ = log_one("with_trap", F + [C.TRAP])
r2 = client.get_run(run2)
C.emit("S1_leak", {"registered_version": client.get_latest_versions("pi_r4_baseline")[0].version if hasattr(client, "get_latest_versions") else None,
                   "holdout_auc_legit": run.data.metrics.get("auc"), "holdout_auc_trap": r2.data.metrics.get("auc"),
                   "holdout_brier_trap": r2.data.metrics.get("brier"),
                   "note": "MLflow records the feature list we pass; it has no availability-time concept and accepted the trap model"})

# ---- S4: what evaluate() offers ----
s4 = {}
try:
    ev_df = Xho.copy()
    ev_df["label"] = hom.label.astype(int).values
    t0 = time.perf_counter()
    with mlflow.start_run(experiment_id=exp_id, run_name="evaluate"):
        res = mlflow.models.evaluate(model=info.model_uri, data=ev_df, targets="label", model_type="classifier",
                                     evaluators=["default"], evaluator_config={"log_model_explainability": False})
    s4["metrics"] = {k: round(float(v), 5) for k, v in res.metrics.items() if isinstance(v, (int, float))}
    s4["artifacts"] = sorted(res.artifacts.keys())
    s4["seconds"] = round(time.perf_counter() - t0, 3)
except Exception as e:  # noqa: BLE001
    s4["error"] = f"{type(e).__name__}: {str(e)[:300]}"
C.emit("S4_evaluate", s4)

# ---- file store check ----
fs = {}
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        mlflow.set_tracking_uri(f"file://{work}/mlruns")
        with mlflow.start_run():
            mlflow.log_param("x", 1)
        fs["file_store_ok"] = True
    except Exception as e:  # noqa: BLE001
        fs["file_store_ok"] = False
        fs["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    fs["warnings"] = sorted({f"{x.category.__name__}: {str(x.message)[:140]}" for x in w})[:5]
C.emit("FILE_STORE", fs)

# ---- S6: cost ----
mlflow.set_tracking_uri(f"sqlite:///{work}/mlflow.db")
row = Xho.head(1)
t0 = time.perf_counter()
for _ in range(200):
    loaded.predict(row)
one = (time.perf_counter() - t0) / 200
t0 = time.perf_counter()
loaded.predict(Xho)
batch = time.perf_counter() - t0
db_bytes = os.path.getsize(f"{work}/mlflow.db")
C.emit("S6_cost", {"pyfunc_predict_1row_ms": round(one * 1000, 3), "pyfunc_predict_527rows_ms": round(batch * 1000, 3),
                   "sqlite_db_bytes": db_bytes, "import_s": round(IMPORT_S, 3)})
print("telemetry client:", type(getattr(__import__("mlflow.telemetry.client", fromlist=["x"]), "_MLFLOW_TELEMETRY_CLIENT", None)).__name__)
print("DONE")

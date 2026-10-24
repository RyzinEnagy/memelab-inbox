"""mlflow-skinny with the plain file store (MLFLOW_ALLOW_FILE_STORE=true): lineage without sqlalchemy or a server."""
import json
import os
import sys
import tempfile
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402

warnings.filterwarnings("ignore")
import mlflow  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.models import infer_signature  # noqa: E402

work = tempfile.mkdtemp(prefix="mlf_sk_")
mlflow.set_tracking_uri(f"file://{work}/mlruns")
out = {"mlflow_version": mlflow.__version__, "allow_file_store": os.environ.get("MLFLOW_ALLOW_FILE_STORE")}
df = C.load()
trm = C.matured(df[df.split == "train"])
hom = C.matured(df[df.split == "holdout"])
model = C.fit_baseline(trm, C.FEATURES)
X = C.log_feats(trm, C.FEATURES)
try:
    with mlflow.start_run() as run:
        mlflow.log_params({"feature_set": json.dumps(C.FEATURES), "training_label_cutoff_epoch": int(trm.label_matures_at.max())})
        mlflow.log_input(mlflow.data.from_pandas(trm[C.FEATURES + ["label"]], targets="label", name="train"), context="training")
        info = mlflow.sklearn.log_model(model, name="model", signature=infer_signature(X, model.predict_proba(X)),
                                        pyfunc_predict_fn="predict_proba", skops_trusted_types=["numpy.dtype"])
    out["run_ok"] = True
    try:
        mv = mlflow.register_model(info.model_uri, "pi_r4_fs")
        out["register_ok"] = True
        out["model_version_run_id"] = mv.run_id == run.info.run_id
    except Exception as e:  # noqa: BLE001
        out["register_ok"] = False
        out["register_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    r = MlflowClient().get_run(run.info.run_id)
    out["params"] = r.data.params
    out["dataset_digest"] = [d.dataset.digest for d in r.inputs.dataset_inputs]
    m = mlflow.pyfunc.load_model(info.model_uri)
    Xh = C.log_feats(hom, C.FEATURES)
    out["reload_identical"] = bool(np.array_equal(np.asarray(m.predict(Xh)), model.predict_proba(Xh)))
    files = []
    for root, _, fs in os.walk(os.path.join(work, "mlruns")):
        files += [os.path.relpath(os.path.join(root, f), work) for f in fs]
    out["store_file_count"] = len(files)
    out["store_files_sample"] = sorted(files)[:12]
except Exception as e:  # noqa: BLE001
    out["run_ok"] = False
    out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
C.emit("SKINNY_FILESTORE", out)
print("DONE")

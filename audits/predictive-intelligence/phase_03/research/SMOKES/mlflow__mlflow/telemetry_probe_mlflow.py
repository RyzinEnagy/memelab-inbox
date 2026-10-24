"""Telemetry probe for MLflow (run under unshare -n plus strace). Default local use: sqlite tracking, one run, one param."""
import os
import sys
import tempfile
import time

import mlflow
import mlflow.telemetry.client as tc
from mlflow.telemetry.utils import is_telemetry_disabled

work = tempfile.mkdtemp(prefix="mlf_tel_")
print("mlflow", mlflow.__version__, "is_telemetry_disabled:", is_telemetry_disabled())
print("client after import:", type(tc.get_telemetry_client()).__name__)
mlflow.set_tracking_uri(f"sqlite:///{work}/mlflow.db")
exp = mlflow.create_experiment("probe", artifact_location=f"file://{work}/a")
with mlflow.start_run(experiment_id=exp):
    mlflow.log_param("x", 1)
    mlflow.log_metric("m", 0.5)
time.sleep(3)
c = tc.get_telemetry_client()
print("client after run:", type(c).__name__, "config:", getattr(c, "config", None) if c else None)
x = os.environ.get("XDG_CONFIG_HOME", "")
print("files under XDG_CONFIG_HOME:", sorted(os.path.relpath(os.path.join(r, f), x) for r, _, fs in os.walk(x) for f in fs) if x else None)
print("probe done")

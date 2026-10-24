"""Telemetry probe for NannyML at the pin. Run under `unshare -n` plus strace so nothing can leave.

Runs the default use path: import, UnivariateDriftCalculator fit and calculate, CBPE fit and estimate.
Also checks the import-time `load_dotenv()` side effect with a .env file in the working directory.
"""
import os
import sys
import time

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

with open(".env", "w") as fh:  # cwd is a fresh temp dir chosen by the caller
    fh.write("R4_DOTENV_PROBE=loaded_by_import\n")
print("before import R4_DOTENV_PROBE =", os.environ.get("R4_DOTENV_PROBE"))
import nannyml as nml  # noqa: E402
import pandas as pd  # noqa: E402

print("after import R4_DOTENV_PROBE =", os.environ.get("R4_DOTENV_PROBE"))
print("NML_DISABLE_USAGE_LOGGING set:", "NML_DISABLE_USAGE_LOGGING" in os.environ)
import segment.analytics as sa  # noqa: E402

print("segment host:", getattr(sa, "host", None), "write_key set:", bool(getattr(sa, "write_key", None)))
df = C.load()
df["ts"] = pd.to_datetime(df.decision_time, unit="s")
ref = df[df.split == "train"]
ana = df[df.split == "holdout"]
calc = nml.UnivariateDriftCalculator(column_names=["liq_usd", "ret_1h"], timestamp_column_name="ts", chunk_size=300)
calc.fit(ref)
calc.calculate(ana)
m = C.matured(df[df.split == "val"]).copy()
m["proba"] = 0.04
m["pred"] = 0
est = nml.CBPE(y_pred_proba="proba", y_pred="pred", y_true="label", metrics=["roc_auc"], chunk_size=200,
               problem_type="classification_binary")
try:
    est.fit(m)
except Exception as e:  # noqa: BLE001
    print("cbpe fit error (expected with constant proba):", type(e).__name__)
time.sleep(5)
print("probe done")

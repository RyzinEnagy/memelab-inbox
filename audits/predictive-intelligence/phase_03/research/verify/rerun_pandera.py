"""Phase 03 lead re-execution: pandera enforces a caller-declared as-of rule fail-closed (T4a), refuses an
undeclared column under strict=True, and fails closed when a check itself errors. Own check code and data.
Usage: <pandera venv python> -I rerun_pandera.py challenge.csv
"""
import json, sys
import pandas as pd
import pandera.pandas as pa
from pandera.api.extensions import register_check_method

@register_check_method(statistics=["dcol"], supported_types=pd.DataFrame)
def lead_asof(df, *, dcol):
    av = [c for c in df.columns if c.endswith("_available_at")]
    return df[av].le(df[dcol], axis=0).fillna(False).all(axis=1)

def lead_broken(df):
    raise RuntimeError("check bug")

d = pd.read_csv(sys.argv[1])
base = pd.DataFrame({"decision_time": d.decision_time.astype("int64"), "ret_1h": d.ret_1h.astype(float),
                     "ret_1h_available_at": (d.decision_time - 300).astype("int64")})
cols = {"decision_time": pa.Column("int64"), "ret_1h": pa.Column(float), "ret_1h_available_at": pa.Column("int64")}
schema = pa.DataFrameSchema(cols, checks=[pa.Check.lead_asof(dcol="decision_time")], strict=True)
out = {}
def failing_rows(frame, sch):
    try:
        sch.validate(frame, lazy=True); return []
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        return sorted({int(i) for i in fc["index"].dropna().tolist()})
    except Exception as e:  # noqa: BLE001
        return "ERROR " + type(e).__name__
out["legit_rows_failing"] = len(failing_rows(base, schema))
late = base.copy(); late.loc[41, "ret_1h_available_at"] = late.loc[41, "decision_time"] + 1
out["one_second_late_rows_failing"] = failing_rows(late, schema)
trap = base.copy(); trap["leak_future_ret"] = d.leak_future_ret; trap["leak_future_ret_available_at"] = d.leak_available_at.astype("int64")
cols_t = dict(cols, leak_future_ret=pa.Column(float), leak_future_ret_available_at=pa.Column("int64"))
schema_t = pa.DataFrameSchema(cols_t, checks=[pa.Check.lead_asof(dcol="decision_time")], strict=True)
ft = failing_rows(trap, schema_t)
out["trap_with_availability_rows_failing"] = len(ft) if isinstance(ft, list) else ft
undeclared = base.copy(); undeclared["leak_future_ret"] = d.leak_future_ret
try:
    schema.validate(undeclared); out["undeclared_column_strict_true"] = "accepted"
except (pa.errors.SchemaError, pa.errors.SchemaErrors) as e:
    out["undeclared_column_strict_true"] = "refused: " + type(e).__name__ + (" column_in_schema" if "column_in_schema" in str(e) else "")
broken = pa.DataFrameSchema(cols, checks=[pa.Check(lead_broken)])
try:
    broken.validate(base); out["check_that_raises"] = "passed (fail-open)"
except Exception as e:  # noqa: BLE001
    out["check_that_raises"] = "validation failed (fail-closed): " + type(e).__name__
print("RESULTS_JSON " + json.dumps(out, sort_keys=True))

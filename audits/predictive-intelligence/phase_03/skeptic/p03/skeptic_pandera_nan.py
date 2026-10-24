"""Skeptic P03: does pandera fail closed when an availability timestamp is MISSING (NaN), as the
DATA_TIME_CONTRACT requires (conservatively established available_at <= decision_time)?
Three natural ways to write the lab's as-of rule; the lead's PA-1 rerun used a DataFrame check with an explicit
fillna(False), which hides the library default. Usage: <pandera venv python> -I skeptic_pandera_nan.py"""
import json
import numpy as np, pandas as pd
import pandera.pandas as pa

df = pd.DataFrame({"decision_time": [1000, 1000, 1000],
                   "ret_1h": [0.1, 0.2, 0.3],
                   "ret_1h_available_at": [700.0, 1001.0, np.nan]})   # row 0 ok, row 1 one second late, row 2 unknown
out = {"pandera": pa.__version__ if hasattr(pa, "__version__") else __import__("pandera").__version__}

def rows_failing(schema):
    try:
        schema.validate(df, lazy=True); return []
    except pa.errors.SchemaErrors as e:
        return sorted({int(i) for i in e.failure_cases["index"].dropna().tolist()})

# A: wide check written without fillna (row-wise boolean with NaN comparisons -> False for NaN in pandas)
sA = pa.DataFrameSchema({"decision_time": pa.Column(int), "ret_1h": pa.Column(float), "ret_1h_available_at": pa.Column(float, nullable=True)},
                        checks=[pa.Check(lambda d: d["ret_1h_available_at"] <= d["decision_time"])])
out["A_dataframe_check_le"] = rows_failing(sA)
# B: column-level element check against a fixed decision time, default ignore_na=True
sB = pa.DataFrameSchema({"decision_time": pa.Column(int), "ret_1h": pa.Column(float),
                         "ret_1h_available_at": pa.Column(float, checks=pa.Check.le(1000), nullable=True)})
out["B_column_check_le_nullable"] = rows_failing(sB)
# C: same as B but nullable left at its default (False)
sC = pa.DataFrameSchema({"decision_time": pa.Column(int), "ret_1h": pa.Column(float),
                         "ret_1h_available_at": pa.Column(float, checks=pa.Check.le(1000))})
out["C_column_check_le_default_nullable"] = rows_failing(sC)
# D: wide check expressed as "not later than" (gt negated), a common way to write it
sD = pa.DataFrameSchema({"decision_time": pa.Column(int), "ret_1h": pa.Column(float), "ret_1h_available_at": pa.Column(float, nullable=True)},
                        checks=[pa.Check(lambda d: ~(d["ret_1h_available_at"] > d["decision_time"]))])
out["D_dataframe_check_not_gt"] = rows_failing(sD)
print(json.dumps(out))
print("row 2 (unknown availability) must fail under DATA_TIME_CONTRACT; rows listed are the ones pandera refused")

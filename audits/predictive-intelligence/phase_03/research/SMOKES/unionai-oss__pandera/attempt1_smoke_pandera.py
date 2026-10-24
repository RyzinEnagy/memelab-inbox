"""Phase 03 R4 smoke for pandera at the pin (run offline).

Schemas for (a) the as-of feature table: every *_available_at <= decision_time, typed and ranged features,
(b) the forecast output: probability finite in [0, 1], interval contains the point, and
(c) label maturity: a label exists only once label_matures_at <= as_of (P05).
"""
import os
import sys
import time
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

env_before = {k: os.environ.get(k) for k in ("SPARK_LOCAL_IP", "PYARROW_IGNORE_TIMEZONE")}
np_nan_alias_before = hasattr(np, "NaN")
t0 = time.perf_counter()
import pandera.pandas as pa  # noqa: E402
from pandera.api.extensions import register_check_method  # noqa: E402

IMPORT_S = time.perf_counter() - t0
C.emit("import_side_effects", {
    "import_s": round(IMPORT_S, 3),
    "env_before": env_before,
    "env_after": {k: os.environ.get(k) for k in ("SPARK_LOCAL_IP", "PYARROW_IGNORE_TIMEZONE")},
    "numpy_NaN_alias_before": np_nan_alias_before, "numpy_NaN_alias_after": hasattr(np, "NaN"),
    "numpy_version": np.__version__, "pandas_version": pd.__version__,
})
warnings.filterwarnings("ignore")

F = C.FEATURES
AS_OF = 1790000000 + 30 * 86400  # challenge cutoff (T0 + 30 days), fixed, no wall clock


@register_check_method(statistics=["decision_col"], supported_types=pd.DataFrame)
def available_before_decision(df, *, decision_col):
    """Element-wise: every column ending in _available_at must be <= decision_col (NaN availability fails)."""
    cols = [c for c in df.columns if c.endswith("_available_at")]
    ok = pd.DataFrame({c: df[c].notna() & (df[c] <= df[decision_col]) for c in cols}, index=df.index)
    return ok


@register_check_method(statistics=["as_of"], supported_types=pd.DataFrame)
def label_only_when_matured(df, *, as_of):
    """A label may exist only if label_matures_at <= as_of; a matured row must have a label."""
    matured = df["label_matures_at"] <= as_of
    return (matured & df["label"].notna()) | (~matured & df["label"].isna())


feature_schema = pa.DataFrameSchema(
    {
        "decision_id": pa.Column(str, unique=True),
        "mint": pa.Column(str, pa.Check.str_length(32, 44)),
        "decision_time": pa.Column("int64"),
        "liq_usd": pa.Column(float, pa.Check.ge(0), nullable=True),
        "vol_24h": pa.Column(float, pa.Check.ge(0), nullable=True),
        "age_h": pa.Column(float, pa.Check.ge(0), nullable=False),
        "score100": pa.Column("int64", pa.Check.in_range(0, 100)),
        "fatal_flag": pa.Column("int64", pa.Check.isin([0, 1])),
        "ret_1h": pa.Column(float, nullable=False),
        r".+_available_at$": pa.Column("int64", regex=True, required=False),
    },
    checks=[pa.Check.available_before_decision(decision_col="decision_time")],
    strict="filter",  # drop any column not declared (a trap value column without availability metadata cannot slip in)
    coerce=False,
)

label_schema = pa.DataFrameSchema(
    {"label": pa.Column(float, pa.Check.isin([0.0, 1.0]), nullable=True), "label_matures_at": pa.Column("int64")},
    checks=[pa.Check.label_only_when_matured(as_of=AS_OF)],
)

forecast_schema = pa.DataFrameSchema(
    {
        "decision_id": pa.Column(str, unique=True),
        "probability": pa.Column(float, [pa.Check.in_range(0.0, 1.0), pa.Check(lambda s: np.isfinite(s), element_wise=False, name="finite")], nullable=False),
        "lower": pa.Column(float, pa.Check.in_range(0.0, 1.0)),
        "upper": pa.Column(float, pa.Check.in_range(0.0, 1.0)),
    },
    checks=[pa.Check(lambda d: (d["lower"] <= d["probability"]) & (d["probability"] <= d["upper"]), name="interval_contains_point")],
)

df = C.load()


def run(schema, frame, lazy=True):
    t0 = time.perf_counter()
    try:
        out = schema.validate(frame, lazy=lazy)
        return {"valid": True, "seconds": round(time.perf_counter() - t0, 4), "columns_out": list(out.columns)}
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        return {"valid": False, "seconds": round(time.perf_counter() - t0, 4), "n_failure_cases": int(len(fc)),
                "checks_failed": sorted({str(x) for x in fc["check"].unique()}),
                "columns_failed": sorted({str(x) for x in fc["column"].unique()}),
                "first_failure_index": None if fc["index"].isna().all() else int(fc["index"].dropna().iloc[0])}
    except pa.errors.SchemaError as e:
        return {"valid": False, "lazy": False, "error": str(e)[:300]}


# ---- S1 / P36: the trap column carries its availability time; the as-of check refuses it ----
base_cols = ["decision_id", "mint", "decision_time"] + F
with_trap = df[base_cols + [C.TRAP, "leak_available_at"]]
legit = df[base_cols].copy()
for c in F:  # synthetic availability: candle close + 300 s, always before the decision in this fixture
    legit[f"{c}_available_at"] = legit["decision_time"] - 300
one_late = legit.copy()
one_late.loc[one_late.index[17], "liq_usd_available_at"] = int(one_late.loc[one_late.index[17], "decision_time"]) + 1
missing_avail = legit.copy()
missing_avail.loc[missing_avail.index[5], "ret_1h_available_at"] = np.nan
trap_no_meta = df[base_cols + [C.TRAP]].copy()
s1 = {
    "with_trap_and_its_available_at": run(feature_schema, with_trap),
    "legit_with_availability": run(feature_schema, legit),
    "one_row_available_1s_after_decision": run(feature_schema, one_late),
    "one_row_availability_missing": run(feature_schema, missing_avail.astype({"ret_1h_available_at": "float64"})),
    "trap_column_without_availability_metadata": run(feature_schema, trap_no_meta),
}
# the model-level effect, to show what the gate prevents
trm, hom = C.matured(df[df.split == "train"]), C.matured(df[df.split == "holdout"])
prev = float(trm.label.mean())
try:
    m_legit = C.fit_baseline(trm, F)
    m_trap = C.fit_baseline(trm, F + [C.TRAP])
    s1["model_effect"] = {"legit": C.scores(hom.label, m_legit.predict_proba(C.log_feats(hom, F))[:, 1], prev),
                          "with_trap": C.scores(hom.label, m_trap.predict_proba(C.log_feats(hom, F + [C.TRAP]))[:, 1], prev)}
except ImportError as e:
    s1["model_effect"] = f"SKIPPED: {e}"
C.emit("S1_asof_gate", s1)

# ---- S2 / P38: forecast output schema ----
good = pd.DataFrame({"decision_id": [f"f{i}" for i in range(5)], "probability": [0.01, 0.2, 0.5, 0.9, 0.99]})
good["lower"] = (good.probability - 0.05).clip(0, 1)
good["upper"] = (good.probability + 0.05).clip(0, 1)
s2 = {"valid_forecasts": run(forecast_schema, good)}
for name, val in (("p_1_5", 1.5), ("p_negative", -0.1), ("p_nan", np.nan), ("p_inf", np.inf)):
    bad = good.copy()
    bad.loc[2, "probability"] = val
    s2[name] = run(forecast_schema, bad)
bad = good.copy()
bad.loc[1, "lower"] = 0.3  # interval no longer contains the point
s2["interval_excludes_point"] = run(forecast_schema, bad)
C.emit("S2_forecast_schema", s2)

# ---- P05: label maturity ----
labels = df[["label", "label_matures_at"]].astype({"label": float})
s5a = {"challenge_labels": run(label_schema, labels)}
leak_label = labels.copy()
imm = leak_label.index[leak_label.label_matures_at > AS_OF][0]
leak_label.loc[imm, "label"] = 0.0  # a PENDING row scored as negative
s5a["pending_row_given_label_0"] = run(label_schema, leak_label)
C.emit("P05_label_maturity", s5a)

# ---- S3: missing covariates ----
nan_age = legit.copy()
nan_age.loc[nan_age.index[3], "age_h"] = np.nan
C.emit("S3_nullable", {"nan_in_nullable_liq_usd_rows": int(legit.liq_usd.isna().sum()), "legit_valid": s1["legit_with_availability"]["valid"],
                       "nan_in_non_nullable_age_h": run(feature_schema, nan_age)})

# ---- S5: schema persistence (YAML), registered checks included ----
try:
    y = feature_schema.to_yaml()
    back = pa.DataFrameSchema.from_yaml(y)
    r1, r2 = run(feature_schema, one_late), run(back, one_late)
    s5 = {"yaml_bytes": len(y), "roundtrip_same_result": (r1["valid"], r1.get("n_failure_cases")) == (r2["valid"], r2.get("n_failure_cases")),
          "yaml_mentions_registered_check": "available_before_decision" in y}
except Exception as e:  # noqa: BLE001
    s5 = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
try:
    forecast_schema.to_yaml()
    s5["lambda_checks_to_yaml"] = "serialized"
except Exception as e:  # noqa: BLE001
    s5["lambda_checks_to_yaml"] = f"refused {type(e).__name__}: {str(e)[:200]}"
C.emit("S5_schema_io", s5)

# ---- S6: cost ----
big = pd.concat([legit] * 10, ignore_index=True)
big["decision_id"] = [f"d{i}" for i in range(len(big))]
t0 = time.perf_counter()
feature_schema.validate(big, lazy=True)
t30k = time.perf_counter() - t0
t0 = time.perf_counter()
for _ in range(100):
    forecast_schema.validate(good.head(1))
one = (time.perf_counter() - t0) / 100
C.emit("S6_cost", {"validate_30000_rows_s": round(t30k, 3), "validate_1_forecast_ms": round(one * 1000, 3), "import_s": round(IMPORT_S, 3)})
print("DONE")

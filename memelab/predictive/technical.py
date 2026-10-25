"""Phase 08: technical market-state features (tech-1) and the technical predictors M1 to M3 (research only, flag OFF, imported
by no existing module). numpy and the standard library only; no network, no clock.

Pre-registration: audits/predictive-intelligence/phase_08/ACCEPTANCE_CHECKLIST.md and experiments/EXPERIMENT_REGISTRY.csv,
committed before any technical feature was computed on a labelled decision (PI-D-050). Model card:
audits/predictive-intelligence/phase_08/models/TECHNICAL_MODEL_CARD.md.

Features. `technical_as_of(con, chain, mint, T)` computes tech-1 at T for the decision's point-in-time pool through
`features.AsOfView` (the same candle visibility, revision rule and `replay_core.Audit` as version 2), from closes and volumes
only: a candle's open, and with it high and low, depends on the vendor's request window (PI-D-037). A candle is used only when
it has closed and is available at T (end <= T and available_at <= T: no same-candle entry, P06; no later input, P36). Coverage
and missing reasons follow `features._candle_values`; a missing technical input is never imputed: AS_OF and HEURISTIC
missingness give OOD, RETRIEVAL missingness CENSORED_RETRIEVAL (censoring, never a model input, PI-D-037).

Models. M1 (L2 logistic on tech-1), M2 (L2 logistic on B2's columns plus tech-1, primary), M3 (gradient-boosted depth-1 stumps
on tech-1), ablations A1 to A5 and the shuffled control NC1-T. Each is fitted on one fold's training rows only, on the rows that
carry its required inputs, and only when they reach the ACCEPTANCE minimums (100 events, 20 per class); otherwise its card
abstains with INSUFFICIENT_HISTORY. Cards are JSON read by numpy code (no pickle); model_sha is the sha256 of the canonical card
without it; a card trained after a decision cannot score that decision (P13). No number here is a published probability.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from . import baselines as B
from . import contract as C
from . import features as F
from . import labels as L
from . import sources as SRC
from . import stats as K
from . import store as S

PHASE = "08"
TECH_VERSION = "tech-1"
FEATURE_SET_NAME = "memelab.predictive.technical"
PROVISIONAL = B.PROVISIONAL
FIXTURE_FLAG = B.FIXTURE_FLAG
PERIOD_S = F.PERIOD_S
SIG = F.SIG
H1, H6, H24 = 3600.0, 21600.0, 86400.0
RETEST_TOL = math.log(1.03)
SPLIT_EPS = 1e-7                      # consecutive training values closer than this count as equal (scikit-learn's convention)

FAMILIES: dict[str, tuple[str, ...]] = {
    "momentum": ("tech_log_ret_1h", "tech_log_ret_6h", "tech_log_ret_24h"),
    "volatility": ("tech_rv_1h", "tech_rv_6h", "tech_log_range_6h", "tech_log_range_24h"),
    "volume": ("tech_log_rel_vol_1h", "tech_log1p_candles_24h", "tech_log1p_last_close_age_min"),
    "structure": ("tech_log_breakout_1h", "tech_failed_breakout_1h", "tech_retest_6h", "tech_log_dist_24h_high",
                  "tech_log_pullback_6h"),
}
TECH: tuple[str, ...] = tuple(c for cols in FAMILIES.values() for c in cols)
FAMILY_OF = {c: fam for fam, cols in FAMILIES.items() for c in cols}
DEFINITIONS = [
    ("tech_log_ret_1h", H1, "ln(last close / px(T - 1 h))"),
    ("tech_log_ret_6h", H6, "ln(last close / px(T - 6 h))"),
    ("tech_log_ret_24h", H24, "ln(last close / px(T - 24 h))"),
    ("tech_rv_1h", H1, "sqrt(sum of squared ln close changes) from px(T - 1 h) through win(1 h)"),
    ("tech_rv_6h", H6, "same over 6 h"),
    ("tech_log_range_6h", H6, "ln(max close / min close) over px(T - 6 h) and win(6 h)"),
    ("tech_log_range_24h", H24, "same over 24 h"),
    ("tech_log_rel_vol_1h", H24, "ln((volume of win(1 h) + 1) / (volume of win(24 h) / 24 + 1)), usd"),
    ("tech_log1p_candles_24h", H24, "ln(1 + candles in win(24 h))"),
    ("tech_log1p_last_close_age_min", None, "ln(1 + (T - end of last) / 60)"),
    ("tech_log_breakout_1h", H24, "ln(RH / PH): PH max close over px(T - 24 h) and candles ending in (T - 24 h, T - 1 h]; "
                                  "RH max close over px(T - 1 h) and win(1 h)"),
    ("tech_failed_breakout_1h", H24, "1 when RH > PH and last close < PH, else 0"),
    ("tech_retest_6h", H24, "PH6 max close over px(T - 24 h) and candles ending in (T - 24 h, T - 6 h]; 1 when a close in win(6 h) "
                            "is above PH6 and abs(ln(last close / PH6)) <= ln(1.03), else 0"),
    ("tech_log_dist_24h_high", H24, "ln(last close / max close over px(T - 24 h) and win(24 h))"),
    ("tech_log_pullback_6h", H6, "ln(last close / max close over px(T - 6 h) and win(6 h))"),
]
assert tuple(d[0] for d in DEFINITIONS) == TECH
# where tech-1 restates a stored version 2 value (consistency rule of PI-D-050 item 2)
V2_SAME = {"tech_log_ret_1h": "cdl_log_ret_1h", "tech_log_ret_6h": "cdl_log_ret_6h", "tech_log_ret_24h": "cdl_log_ret_24h",
           "tech_rv_6h": "cdl_rv_6h", "tech_log_range_24h": "cdl_log_range_24h", "tech_log_dist_24h_high": "cdl_log_drawdown_24h"}

MODEL_IDS = ("M1_T_LOGIT", "M2_T_LOGIT_B2", "M3_T_STUMPS")
ABLATION_IDS = ("A1_M2_minus_momentum", "A2_M2_minus_volatility", "A3_M2_minus_volume", "A4_M2_minus_structure", "A5_T_B2_TC")
ALL_IDS = MODEL_IDS + ABLATION_IDS
PRIMARY = "M2_T_LOGIT_B2"
C_L2 = 1.0
STUMP_ROUNDS, STUMP_LR, STUMP_MIN_LEAF = 100, 0.1, 10
M2_ROWS = tuple(B.B2_REQUIRED) + TECH            # the rows every M2-based model uses (identical rows across ablations)


def _spec(cols: Sequence[str], optional: Sequence[str] = ()) -> dict:
    return {"columns": list(cols) + list(optional), "optional": list(optional)}


SPECS: dict[str, dict] = {
    "M1_T_LOGIT": {"kind": "logit", "rows": list(TECH), **_spec(TECH)},
    "M2_T_LOGIT_B2": {"kind": "logit", "rows": list(M2_ROWS), **_spec(tuple(B.B2_REQUIRED) + TECH, B.B2_OPTIONAL)},
    "M3_T_STUMPS": {"kind": "stumps", "rows": list(TECH), **_spec(TECH)},
    "A5_T_B2_TC": {"kind": "logit", "rows": list(M2_ROWS), **_spec(B.B2_REQUIRED, B.B2_OPTIONAL)},
}
for _i, _fam in enumerate(FAMILIES, 1):
    SPECS[f"A{_i}_M2_minus_{_fam}"] = {"kind": "logit", "rows": list(M2_ROWS),
                                       **_spec(tuple(B.B2_REQUIRED) + tuple(c for c in TECH if FAMILY_OF[c] != _fam), B.B2_OPTIONAL)}
ALLOWED = frozenset(TECH) | B.ALLOWED_COLUMNS       # every column a Phase 08 model may read (NC2-T allowlist)


class TechnicalError(ValueError):
    pass


class ModelTrainedAfterDecision(TechnicalError):
    """A card whose training cutoff is after the decision it would score (P13: a later model applied to an earlier replay)."""


def feature_set_definitions() -> dict:
    return {"name": FEATURE_SET_NAME, "version": TECH_VERSION, "base_feature_version": F.FEATURE_VERSION,
            "base_feature_set_sha": F.feature_set_sha(), "period_s": PERIOD_S, "significant_digits": SIG,
            "inputs": "closes and volumes of visible 5-minute candles that ended at or before T; never open, high or low",
            "retest_tolerance_ln": RETEST_TOL, "families": {k: list(v) for k, v in FAMILIES.items()},
            "features": [{"name": n, "window_s": w, "definition": d} for n, w, d in DEFINITIONS],
            "missing": "never imputed: AS_OF and HEURISTIC give OOD, RETRIEVAL gives CENSORED_RETRIEVAL"}


def feature_set_sha() -> str:
    return S.sha(feature_set_definitions())


def _r(x: float) -> float:
    return float(f"{x:.{SIG}g}")


# ---------------------------------------------------------------- tech-1 at one decision time
def _value(v: float | None = None, reason: str | None = None, inputs: Sequence[dict] = ()) -> dict:
    if (v is None) == (reason is None):
        raise TechnicalError("exactly one of value or missing reason")
    if v is not None and not (isinstance(v, (int, float)) and math.isfinite(v)):
        raise TechnicalError(f"value {v!r} is not finite (P38)")
    if reason is not None and reason not in F.REASONS:
        raise TechnicalError(f"unknown missing reason {reason!r}")
    keys = sorted({c["obs_key"] for c in inputs})
    return {"value": _r(float(v)) if v is not None else None, "missing_reason": reason,
            "missing_basis": F.REASONS[reason] if reason else None,
            "available_at": (round(max(float(c["_avail"]) for c in inputs), 6) if (inputs and v is not None) else None),
            "n_inputs": len(keys), "input_fingerprint": S.sha(keys)}


def _values(view: F.AsOfView, dec: dict | None, T: float) -> dict[str, dict]:
    def all_missing(reason: str) -> dict[str, dict]:
        return {n: _value(reason=reason) for n in TECH}

    if dec is None:
        return all_missing("NOT_IN_UNIVERSE")
    if dec["chain"] != "solana":
        return all_missing("OUT_OF_SCOPE_CHAIN")
    pool = dec["pool_address"]
    if not pool:
        return all_missing("NO_POOL_AT_DECISION")
    lag = S._provider_lag()
    stats = [s for s in view.series_status("solana", pool) if s["mint"] == dec["mint"]]
    need_to = T - lag
    good = [s for s in stats if s["status"] in ("OK", "NO_DATA") and s["boundary_at"] >= need_to - 1e-9]
    if not good:
        bad = [s for s in stats if s["status"] in F.STATUS_REASON and s["boundary_at"] >= need_to - 1e-9]
        if bad:
            return all_missing(F.STATUS_REASON[bad[-1]["status"]])
        if view.mode == "capture" and not stats:
            return all_missing("NOT_RETRIEVED_BY_DECISION")
        scope = SRC.fetch_scope({"chain": dec["chain"], "pool_address": pool, "decision_time": dec["decision_time"]})
        return all_missing("NOT_FETCHED_SEALED" if scope == "NOT_FETCHED_SEALED" else "NOT_FETCHED")
    cover_from = min((s["cover_from"] for s in good if s["cover_from"] is not None), default=float("inf"))
    if all(s["status"] == "NO_DATA" for s in good):
        return all_missing("VENDOR_NO_DATA")
    # a close exists only once its candle has ended (P06): an in-progress candle is never read, whatever its availability
    cs = [c for c in view.candles("solana", dec["mint"], pool) if c["end_at"] <= T]
    if not cs:
        return all_missing("OUTSIDE_FETCHED_WINDOW")
    last = cs[-1]
    out: dict[str, dict] = {}

    def px(x: float) -> tuple[dict | None, str | None]:
        cand = [c for c in cs if c["end_at"] <= x]
        if cand:
            return cand[-1], None
        return None, ("OUTSIDE_FETCHED_WINDOW" if cover_from > x - PERIOD_S else "NO_CANDLE_AVAILABLE")

    def win(w: float) -> tuple[list[dict] | None, str | None]:
        if cover_from > T - w - PERIOD_S:
            return None, "OUTSIDE_FETCHED_WINDOW"
        return [c for c in cs if T - w < c["end_at"] <= T], None

    def between(a: float, b: float) -> list[dict]:
        return [c for c in cs if a < c["end_at"] <= b]

    def ln(a: float, b: float) -> float:
        return math.log(a / b)

    for name, w in (("tech_log_ret_1h", H1), ("tech_log_ret_6h", H6), ("tech_log_ret_24h", H24)):
        base, why = px(T - w)
        out[name] = _value(reason=why) if base is None else _value(ln(last["c"], base["c"]), inputs=[base, last])
    for name, w in (("tech_rv_1h", H1), ("tech_rv_6h", H6)):
        ws, why = win(w)
        base, why2 = px(T - w)
        if ws is None or base is None:
            out[name] = _value(reason=why or why2)
        else:
            seq = [base] + [c for c in ws if c is not base]
            rv = math.sqrt(sum(ln(b["c"], a["c"]) ** 2 for a, b in zip(seq, seq[1:])))
            out[name] = _value(rv, inputs=seq + [last])
    for name, w in (("tech_log_range_6h", H6), ("tech_log_range_24h", H24)):
        ws, why = win(w)
        base, why2 = px(T - w)
        if ws is None or base is None:
            out[name] = _value(reason=why or why2)
        else:
            closes = [base["c"]] + [c["c"] for c in ws]
            out[name] = _value(ln(max(closes), min(closes)), inputs=[base] + ws + [last])
    w1, why1 = win(H1)
    w24, why24 = win(H24)
    if w1 is None or w24 is None:
        out["tech_log_rel_vol_1h"] = _value(reason=why1 or why24)
        out["tech_log1p_candles_24h"] = _value(reason=why24)
    else:
        v1, v24 = sum(c["v"] for c in w1), sum(c["v"] for c in w24)
        out["tech_log_rel_vol_1h"] = _value(math.log((v1 + 1.0) / (v24 / 24.0 + 1.0)), inputs=w24)
        out["tech_log1p_candles_24h"] = _value(math.log1p(len(w24)), inputs=w24)
    out["tech_log1p_last_close_age_min"] = _value(math.log1p((T - last["end_at"]) / 60.0), inputs=[last])
    base24, whyb = px(T - H24)
    if w24 is None or base24 is None:
        for n in ("tech_log_breakout_1h", "tech_failed_breakout_1h", "tech_retest_6h", "tech_log_dist_24h_high"):
            out[n] = _value(reason=why24 or whyb)
    else:
        ph_set = [base24] + between(T - H24, T - H1)
        p1h, _ = px(T - H1)                       # exists: base24 ends at or before T - 24 h
        rh_set = [p1h] + (w1 or [])
        PH, RH = max(c["c"] for c in ph_set), max(c["c"] for c in rh_set)
        used = ph_set + rh_set + [last]
        out["tech_log_breakout_1h"] = _value(ln(RH, PH), inputs=used)
        out["tech_failed_breakout_1h"] = _value(1.0 if (RH > PH and last["c"] < PH) else 0.0, inputs=used)
        ph6_set = [base24] + between(T - H24, T - H6)
        PH6 = max(c["c"] for c in ph6_set)
        w6 = [c for c in cs if T - H6 < c["end_at"] <= T]
        broke = any(c["c"] > PH6 for c in w6)
        out["tech_retest_6h"] = _value(1.0 if (broke and abs(ln(last["c"], PH6)) <= RETEST_TOL) else 0.0,
                                       inputs=ph6_set + w6 + [last])
        hi = max([base24["c"]] + [c["c"] for c in w24])
        out["tech_log_dist_24h_high"] = _value(ln(last["c"], hi), inputs=[base24] + w24 + [last])
    ws6, why6 = win(H6)
    base6, why6b = px(T - H6)
    if ws6 is None or base6 is None:
        out["tech_log_pullback_6h"] = _value(reason=why6 or why6b)
    else:
        hi6 = max([base6["c"]] + [c["c"] for c in ws6])
        out["tech_log_pullback_6h"] = _value(ln(last["c"], hi6), inputs=[base6] + ws6 + [last])
    return {n: out[n] for n in TECH}


def technical_as_of(con: sqlite3.Connection, chain: str, mint: str, decision_time: float, *, mode: str = "provider",
                    decision_key: str | None = None) -> dict:
    """tech-1 of (chain, mint) at decision_time from the as-of view alone. With decision_key, the view's decision at that time
    must be that exact decision (identity, P01)."""
    S.check_address(chain, mint)
    if not (isinstance(decision_time, (int, float)) and math.isfinite(decision_time)):
        raise TechnicalError("decision_time must be a finite epoch time")
    T = float(decision_time)
    view = F.AsOfView(con, T, mode)
    decs = view.decisions_of(chain, mint)
    dec = decs[-1] if decs else None
    if decision_key is not None and (dec is None or dec["decision_key"] != decision_key or float(dec["decision_time"]) != T):
        raise B.IdentityJoinError("the as-of view's decision at T is not the requested decision (P01)")
    vals = _values(view, dec, T)
    for n, v in vals.items():
        if v["available_at"] is not None and v["available_at"] > T:
            raise F.LeakageError(f"{n} available at {v['available_at']} after the decision {T} (P36)")
    snap = {"decision_key": dec["decision_key"] if dec else None, "chain": chain, "mint": mint,
            "pool_address": dec["pool_address"] if dec else None, "decision_time": T, "mode": mode,
            "tech_version": TECH_VERSION, "feature_set_sha": feature_set_sha(), "values": vals,
            "rows_audited": view.audit.records}
    snap["tech_snapshot_sha"] = S.sha({"k": snap["decision_key"], "T": T, "mode": mode, "fs": snap["feature_set_sha"],
                                       "v": {n: [v["value"], v["missing_reason"], v["available_at"], v["input_fingerprint"]]
                                             for n, v in vals.items()}})
    return snap


def row_status(snap: dict, cols: Sequence[str] = TECH) -> str | None:
    """None when every column has a value; else CENSORED_RETRIEVAL when any missing one has a RETRIEVAL basis, else OOD."""
    miss = [snap["values"][c] for c in cols if snap["values"][c]["value"] is None]
    if not miss:
        return None
    return "CENSORED_RETRIEVAL" if any(m["missing_basis"] == F.RETRIEVAL for m in miss) else "OOD"


def v2_consistency(snap: dict, v2_row: dict) -> list[str]:
    """Differences between tech-1 and the stored version 2 snapshot of the same decision (PI-D-050 item 2). v2_row is a
    `features.training_view` row (values) with the stored missing reasons in v2_row['__reasons'] when given."""
    out = []
    vals = snap["values"]
    reasons = v2_row.get("__reasons", {})
    for t, v in V2_SAME.items():
        a, b = vals[t]["value"], v2_row.get(v)
        if (a is None) != (b is None) or (a is not None and a != b):
            out.append(f"{t}: tech {a!r} vs v2 {v} {b!r}")
        if a is None and v in reasons and reasons[v] != vals[t]["missing_reason"]:
            out.append(f"{t}: reason {vals[t]['missing_reason']} vs v2 {reasons[v]}")

    def derived(name: str, fn: Callable[[], float | None]) -> None:
        a = vals[name]["value"]
        try:
            b = fn()
        except (TypeError, ValueError):
            b = None
        if (a is None) != (b is None) or (a is not None and abs(a - _r(b)) > 1e-9 * max(1.0, abs(a))):
            out.append(f"{name}: tech {a!r} vs derived from v2 {b!r}")

    g = v2_row.get
    derived("tech_log1p_candles_24h", lambda: None if g("cdl_candles_24h") is None else math.log1p(g("cdl_candles_24h")))
    derived("tech_log1p_last_close_age_min",
            lambda: None if g("cdl_last_close_age_s") is None else math.log1p(g("cdl_last_close_age_s") / 60.0))
    derived("tech_log_rel_vol_1h", lambda: None if (g("cdl_vol_usd_1h") is None or g("cdl_vol_usd_24h") is None) else
            math.log((g("cdl_vol_usd_1h") + 1.0) / (g("cdl_vol_usd_24h") / 24.0 + 1.0)))
    return out


# ---------------------------------------------------------------- examples
@dataclass
class TExample(B.Example):
    tech_status: str | None = None             # None, OOD or CENSORED_RETRIEVAL (row_status of tech-1)
    tech_reasons: dict = field(default_factory=dict)
    tech_sha: str | None = None


def attach(examples: Sequence[B.Example], snaps: dict[str, dict]) -> list[TExample]:
    """Phase 07 examples (B2 inputs) with their tech-1 snapshot, joined by decision key with chain, mint and time checked."""
    out = []
    for e in examples:
        s = snaps.get(e.decision_key)
        if s is None:
            raise TechnicalError(f"no tech-1 snapshot for decision {e.decision_key[:12]}")
        if s["decision_key"] != e.decision_key or s["chain"] != e.chain or s["mint"] != e.mint or float(s["decision_time"]) != e.decision_time:
            raise B.IdentityJoinError("tech-1 snapshot of another decision (P01)")
        x, av = dict(e.x), dict(e.avail)
        for c in TECH:
            v = s["values"][c]
            x[c] = v["value"] if v["value"] is not None else float("nan")
            if v["value"] is None:
                av[c] = e.decision_time               # a missing value carries no input; it never reaches a fit
            elif v["available_at"] is not None:
                av[c] = v["available_at"]
            elif v["n_inputs"] == 0:
                av[c] = e.decision_time               # a value computed from no input row (an empty window)
            else:
                raise TechnicalError(f"{c}: a value from input rows without an availability time")
        reasons = {c: s["values"][c]["missing_reason"] for c in TECH if s["values"][c]["value"] is None}
        out.append(TExample(**{**e.__dict__, "x": x, "avail": av}, tech_status=row_status(s), tech_reasons=reasons,
                            tech_sha=s["tech_snapshot_sha"]))
    return out


def check_asof(examples: Sequence[B.Example], columns: Sequence[str], *, as_of: float | None, with_labels: bool) -> None:
    """Every column in the Phase 08 allowlist and available at or before its decision; decisions at or before as_of; labels
    matured by as_of when given (features.validate_rows; P36, P05, P43)."""
    bad = [c for c in columns if c not in ALLOWED]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 08 allowlist (NC2-T: only declared as-of inputs reach a fit)")
    rows = []
    for e in examples:
        r = {"decision_time": e.decision_time}
        for c in columns:
            r[c] = e.x.get(c)
            r[c + "__available_at"] = e.avail.get(c)
        if with_labels:
            r["y"], r["label_matures_at"] = e.y, e.label_matures_at
        rows.append(r)
    cols = ["decision_time"] + list(columns) + [c + "__available_at" for c in columns] + (["y", "label_matures_at"] if with_labels else [])
    F.validate_rows(rows, columns=cols, availability=[c + "__available_at" for c in columns], as_of=as_of)


def matrix(examples: Sequence[B.Example], columns: Sequence[str]) -> np.ndarray:
    bad = [c for c in columns if c not in ALLOWED]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 08 allowlist")
    return np.array([[e.x.get(c, float("nan")) for c in columns] for e in examples], dtype=float).reshape(len(examples), len(columns))


def complete(e: B.Example, cols: Sequence[str]) -> bool:
    return all(math.isfinite(B._num(e.x.get(c))) for c in cols)


def why_not(e: B.Example, cols: Sequence[str]) -> str:
    """Abstain reason of a row lacking a required input: CENSORED_RETRIEVAL when a missing technical input has a RETRIEVAL
    basis, else OOD."""
    if getattr(e, "tech_status", None) == "CENSORED_RETRIEVAL" and any(not math.isfinite(B._num(e.x.get(c))) for c in cols if c in TECH):
        return "CENSORED_RETRIEVAL"
    return "OOD"


# ---------------------------------------------------------------- gradient-boosted stumps (numpy)
class Stumps:
    """Gradient boosting of depth-1 regression trees on the logistic loss: initial score the training log-odds; each round fits
    a stump to the residuals y - p by least squares (thresholds at midpoints of consecutive distinct values, at least
    `min_leaf` rows per side, first feature then first threshold on ties) and sets each leaf to sum(residual) / sum(p (1 - p))."""

    def __init__(self, rounds: int = STUMP_ROUNDS, lr: float = STUMP_LR, min_leaf: int = STUMP_MIN_LEAF):
        self.rounds, self.lr, self.min_leaf = int(rounds), float(lr), int(min_leaf)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "Stumps":
        X, y = np.asarray(X, float), np.asarray(y, float)
        K.check_fit_inputs(X, y, "Stumps.fit")
        n, d = X.shape
        p0 = float(y.mean())
        self.init = math.log(p0 / (1 - p0))
        raw = np.full(n, self.init)
        orders = [np.argsort(X[:, j], kind="mergesort") for j in range(d)]
        self.trees: list[list[float]] = []
        for _ in range(self.rounds):
            p = K.sigmoid(raw)
            r = y - p
            best = None
            for j in range(d):
                o = orders[j]
                xs, rs = X[o, j], r[o]
                cs = np.cumsum(rs)
                tot = cs[-1]
                nl = np.arange(1, n, dtype=float)
                nr = n - nl
                ok = (xs[1:] > xs[:-1] + SPLIT_EPS) & (nl >= self.min_leaf) & (nr >= self.min_leaf)
                if not ok.any():
                    continue
                sl = cs[:-1]
                gain = np.where(ok, sl ** 2 / nl + (tot - sl) ** 2 / nr - tot ** 2 / n, -np.inf)
                k = int(np.argmax(gain))
                if best is None or gain[k] > best[0]:
                    thr = xs[k] / 2.0 + xs[k + 1] / 2.0
                    if thr == xs[k + 1] or not math.isfinite(thr):
                        thr = xs[k]
                    best = (float(gain[k]), j, float(thr))
            if best is None:
                break
            _, j, thr = best
            left = X[:, j] <= thr
            h = p * (1 - p)
            vals = []
            for side in (left, ~left):
                den = float(np.sum(h[side]))
                vals.append(float(np.sum(r[side])) / den if abs(den) >= 1e-150 else 0.0)
            raw = raw + self.lr * np.where(left, vals[0], vals[1])
            self.trees.append([int(j), thr, vals[0], vals[1]])
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, float)
        if not np.all(np.isfinite(X)):
            raise ValueError("Stumps: inputs must be finite (P38)")
        raw = np.full(X.shape[0], self.init)
        for j, thr, vl, vr in self.trees:
            raw = raw + self.lr * np.where(X[:, int(j)] <= thr, vl, vr)
        return raw

    def predict_proba1(self, X: np.ndarray) -> np.ndarray:
        return K.sigmoid(self.decision_function(X))

    def to_dict(self) -> dict:
        return {"rounds": self.rounds, "lr": self.lr, "min_leaf": self.min_leaf, "init": float(self.init),
                "trees": [[int(j), float(t), float(a), float(b)] for j, t, a, b in self.trees]}

    @classmethod
    def from_dict(cls, d: dict) -> "Stumps":
        o = cls(d["rounds"], d["lr"], d["min_leaf"])
        o.init, o.trees = float(d["init"]), [list(t) for t in d["trees"]]
        return o


# ---------------------------------------------------------------- cards
def _card(model_id: str, target: str, train: Sequence[B.Example], cutoff: float, body: dict, *, n_used: int, k_used: int,
          is_fixture: bool, meta: dict | None = None) -> dict:
    y = B.labels_of(train)
    card = {"phase": PHASE, "kind": model_id, "model_id": f"{model_id}:{target}", "targets": [target],
            "target_version": {target: C.TARGETS[target]["version"]}, "training_cutoff": float(cutoff),
            "training_cutoff_utc": B._iso(cutoff), "registry_sha": C.registry_sha256(),
            "feature_set_sha": feature_set_sha(), "tech_version": TECH_VERSION, "base_feature_set_sha": F.feature_set_sha(),
            "feature_version": F.FEATURE_VERSION, "labels_version": L.LABELS_VERSION, "store_schema": S.SCHEMA_VERSION,
            "label_mode": "provider", "n_train": int(len(train)), "k_train": int(y.sum()) if len(train) else 0,
            "n_used": int(n_used), "k_used": int(k_used),
            "label_set_sha": B.sha(sorted([e.label_key or e.decision_key, e.y] for e in train)),
            "data_snapshot_sha": B.sha(sorted([e.decision_key, e.snapshot_sha256, getattr(e, "tech_sha", None)] for e in train)),
            "status": PROVISIONAL, "revision_check_claimed": False, "publishable": False, "promotion": "MODEL_NOT_PROMOTED",
            "evidence_class": B.evidence_class(is_fixture),
            "max_train_decision_time": max((e.decision_time for e in train), default=None),
            "max_train_label_matures_at": max((e.label_matures_at for e in train), default=None)}
    card.update(meta or {})
    card["body"] = body
    card["model_sha"] = B.sha({k: v for k, v in card.items() if k != "model_sha"})
    return card


def verify_card(card: dict) -> dict:
    want = B.sha({k: v for k, v in card.items() if k != "model_sha"})
    if card.get("model_sha") != want:
        raise B.ModelHashMismatch(f"card {card.get('model_id')}: content does not match its model_sha (MODEL_HASH_MISMATCH)")
    if card.get("registry_sha") != C.registry_sha256():
        raise TechnicalError("card trained under another registry fingerprint")
    if card.get("feature_set_sha") != feature_set_sha() or card.get("tech_version") != TECH_VERSION:
        raise F.FeatureVersionError("FEATURE_SCHEMA_MISMATCH: tech-1 definitions differ from the card's (P46)")
    F.require_compatible(card["feature_version"], card["base_feature_set_sha"])
    return card


def dumps(card: dict) -> str:
    return B.dumps(card)


def loads(text: str) -> dict:
    import json
    return verify_card(json.loads(text))


def fit(model_id: str, target: str, train: Sequence[B.Example], cutoff: float, *, y_override: np.ndarray | None = None,
        is_fixture: bool = False, meta: dict | None = None, card_kind: str | None = None) -> dict:
    """One Phase 08 model on one training set (rows decided before and matured by the cutoff, checked)."""
    spec = SPECS[model_id]
    check_asof(train, sorted(ALLOWED & set(spec["columns"]) | set(spec["rows"])), as_of=cutoff, with_labels=True)
    for e in train:
        if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):
            raise B.BaselineError(f"training row {e.decision_key[:12]} is not decided before and matured by the cutoff (P05, P43)")
    y_all = B.labels_of(train) if y_override is None else np.asarray(y_override, float)
    use = [i for i, e in enumerate(train) if complete(e, spec["rows"])]
    y = y_all[use] if use else np.array([])
    kind = card_kind or model_id
    g = B.gate(len(use), int(y.sum()))
    if g:
        return _card(kind, target, train, cutoff, {"abstain": g, "spec": spec}, n_used=len(use), k_used=int(y.sum()),
                     is_fixture=is_fixture, meta=meta)
    X = matrix([train[i] for i in use], spec["columns"])
    if spec["kind"] == "logit":
        prep = K.Prep().fit(X)
        m = K.Logistic(C=C_L2).fit(prep.transform(X), y)
        body = {"spec": spec, "prep": prep.to_dict(), "logistic": m.to_dict()}
    else:
        m = Stumps().fit(X, y)
        body = {"spec": spec, "stumps": m.to_dict()}
    body["train_prediction_sd"] = float(np.std(predict_numbers({"kind": kind, "body": body}, [train[i] for i in use])[0]))
    return _card(kind, target, train, cutoff, body, n_used=len(use), k_used=int(y.sum()), is_fixture=is_fixture, meta=meta)


def predict_numbers(card: dict, examples: Sequence[B.Example]) -> tuple[np.ndarray, list[str | None]]:
    """Numbers and abstain reasons without the as-of guard (used for training-row checks and round trips only)."""
    body = card["body"]
    n = len(examples)
    if "abstain" in body:
        return np.full(n, np.nan), [body["abstain"]] * n
    spec = body["spec"]
    p, why = np.full(n, np.nan), [None] * n
    ok = [i for i, e in enumerate(examples) if complete(e, spec["rows"])]
    for i in set(range(n)) - set(ok):
        why[i] = why_not(examples[i], spec["rows"])
    if ok:
        X = matrix([examples[i] for i in ok], spec["columns"])
        if "logistic" in body:
            prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])
            p[ok] = lr.predict_proba1(prep.transform(X))
        elif "stumps" in body:
            p[ok] = Stumps.from_dict(body["stumps"]).predict_proba1(X)
        else:
            raise TechnicalError(f"unknown card body {sorted(body)}")
        K.check_probs(p[ok])
    return p, why


def predict(card: dict, examples: Sequence[B.Example]) -> tuple[np.ndarray, list[str | None]]:
    """Numbers for decisions at or after the card's training cutoff only (P13), each input available at its decision (P36)."""
    early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]
    if early:
        raise ModelTrainedAfterDecision(f"card {card['model_id']} trained to {card['training_cutoff_utc']} cannot score "
                                        f"{len(early)} earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)")
    spec = card["body"].get("spec")
    if examples and spec:
        cols = sorted(set(spec["columns"]) | set(spec["rows"]))
        check_asof(examples, cols, as_of=None, with_labels=False)
    return predict_numbers(card, examples)


def degenerate(p: Any) -> bool:
    """Zero variance across more than one number (P11, P38): flagged, never a forecast."""
    q = np.asarray(p, float)
    q = q[np.isfinite(q)]
    return bool(q.size > 1 and np.ptp(q) == 0)


# ---------------------------------------------------------------- the frozen walk-forward, same folds as Phase 07
def walk_forward(target: str, development: Sequence[TExample], train_at: Callable[[float], Sequence[TExample]], *,
                 nc1_seeds: Iterable[int] = range(20), is_fixture: bool = False, models: Sequence[str] = ALL_IDS) -> dict:
    dev = sorted(development, key=lambda e: (e.decision_time, e.mint))
    if not dev:
        return {"target": target, "folds": [], "oos": [], "audit": None, "status": "INSUFFICIENT_HISTORY",
                "evidence_class": B.evidence_class(is_fixture)}
    dt_ = np.array([e.decision_time for e in dev])
    mat = np.array([e.label_matures_at for e in dev])
    folds = K.day_walk_forward(dt_, mat, first_last_train_day=B.first_last_train_day(),
                               min_train=C.ACCEPTANCE["walk_forward"]["first_fold_min_events"])
    audit = K.fold_audit(dt_, mat, folds, len(dev), min_maturity_lag_s=B.maturity_lag(target), groups=[e.mint for e in dev])
    if folds and not audit["valid_walk_forward"]:
        raise B.BaselineError(f"{target}: fold audit failed: {audit['reasons']}")
    seeds = list(nc1_seeds)
    out_folds, oos = [], []
    for k, f in enumerate(folds):
        cut = float(f["cutoff"])
        train = list(train_at(cut))
        want = sorted(dev[i].decision_key for i in f["train"])
        got = sorted(e.decision_key for e in train)
        if want != got:
            raise B.WalkForwardMismatch(f"{target} fold {k}: walk-forward index ({len(want)}) and training gate ({len(got)}) differ")
        test = [dev[i] for i in f["test"]]
        B.check_asof(train, sorted(B.ALLOWED_COLUMNS), as_of=cut, with_labels=True)
        cards = {"B0": B.fit_b0(target, train, cut), "B2": B.fit_b2(target, train, cut)}
        for c in cards.values():
            c["evidence_class"] = B.evidence_class(is_fixture)
            c["model_sha"] = B.sha({kk: v for kk, v in c.items() if kk != "model_sha"})
        preds = {b: B.predict(cards[b], test) for b in ("B0", "B2")}
        for m in models:
            cards[m] = fit(m, target, train, cut, is_fixture=is_fixture)
            preds[m] = predict(cards[m], test)
        nc1 = {s: np.full(len(test), np.nan) for s in seeds}
        if PRIMARY in cards and "abstain" not in cards[PRIMARY]["body"]:
            for s in seeds:
                yy = np.random.default_rng(s).permutation(B.labels_of(train))
                cnc = fit(PRIMARY, target, train, cut, y_override=yy, is_fixture=is_fixture, meta={"nc1_seed": s},
                          card_kind="NC1T")
                nc1[s] = predict(cnc, test)[0]
        mints_tr = {e.mint for e in train}
        creators_tr = {e.creator for e in train if e.creator}
        narr_tr = {e.narrative for e in train if e.narrative}
        for j, e in enumerate(test):
            row = {"fold": k, "cutoff": cut, "example": e, "y": e.y, "new_mint": e.mint not in mints_tr,
                   "new_creator": (e.creator not in creators_tr) if e.creator else None,
                   "new_narrative": (e.narrative not in narr_tr) if e.narrative else None}
            for m in preds:
                row[m] = float(preds[m][0][j])
                row[m + "_why"] = preds[m][1][j]
            for s, v in nc1.items():
                row[f"NC1T_{s}"] = float(v[j])
            oos.append(row)
        out_folds.append({"fold": k, "cutoff": cut, "cutoff_utc": B._iso(cut), "n_train": len(train),
                          "k_train": int(B.labels_of(train).sum()), "n_test": len(test), "k_test": int(sum(e.y for e in test)),
                          "used": {m: [cards[m]["n_used"], cards[m]["k_used"], cards[m]["body"].get("abstain")] for m in models},
                          "test_day": B._iso(cut)[:10], "cards": cards,
                          "split_fingerprint": B.sha([target, cut, want, sorted(e.decision_key for e in test)])})
    return {"target": target, "folds": out_folds, "oos": oos, "audit": audit, "nc1_seeds": seeds,
            "evidence_class": B.evidence_class(is_fixture), "split_fingerprint": B.sha([f["split_fingerprint"] for f in out_folds]),
            "status": "OK" if out_folds else "INSUFFICIENT_HISTORY"}


def hit_miss(rows: Sequence[dict], model: str, key: Callable[[B.Example], Any]) -> list[dict]:
    """Per cohort value: hits, misses, false alarms and correct rejections of `model` at the fold's own B0 value (a number above
    the training prevalence is an alert). Counts only; no rate below 20 events (P21)."""
    out = []
    for v in sorted({str(key(r["example"]) or "UNKNOWN") for r in rows}):
        rr = [r for r in rows if str(key(r["example"]) or "UNKNOWN") == v and math.isfinite(r[model]) and math.isfinite(r["B0"])]
        alerts = [r[model] > r["B0"] for r in rr]
        ys = [r["y"] for r in rr]
        out.append({"value": v, "n_scored": len(rr), "positives": int(sum(ys)),
                    "hits": sum(1 for a, y in zip(alerts, ys) if a and y), "misses": sum(1 for a, y in zip(alerts, ys) if not a and y),
                    "false_alarms": sum(1 for a, y in zip(alerts, ys) if a and not y),
                    "correct_rejections": sum(1 for a, y in zip(alerts, ys) if not a and not y),
                    "brier": K.brier(ys, [r[model] for r in rr]) if rr else None,
                    "brier_b0": K.brier(ys, [r["B0"] for r in rr]) if rr else None,
                    "support_note": "n >= 20" if len(rr) >= C.ACCEPTANCE["min_bin_events"] else "n < 20: counts only, no rate claimed"})
    return out

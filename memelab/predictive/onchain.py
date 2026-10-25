"""Phase 09: point-in-time on-chain, liquidity and authority risk features (onchain-1), the on-chain models, the structural veto
beside a forecast, and the wallet-movement rules (research only, flag OFF, imported by no existing module). numpy and the
standard library only; no network, no clock.

Pre-registration: audits/predictive-intelligence/phase_09/ACCEPTANCE_CHECKLIST.md, experiments/EXPERIMENT_REGISTRY.csv and
PI-D-054 (committed before any feature on a labelled row and before any fit). Rules enforced here:
  - every value comes from the decision row of an export (the thesis row and its token row) or the previous decision of the same
    chain and mint, read only through `features.AsOfView.decisions_of(chain, mint)` at the decision time T, which audits every
    row (`replay_core.LeakageError` for anything available after T). A value is available at the export commit of the row it
    was read from (PI-D-015); evidence LAB_RECORDED: what the lab recorded at the decision, not a fresh chain read;
  - no historical reserve, quote, holder or wallet history exists for these decisions (SOURCE_BLOCKED), so none is used and
    nothing is substituted by a modern read (P08, DATA_TIME_CONTRACT);
  - rationale lines are produced by m24 and depend on its code version (PI-D-008): a line format this parser does not know is
    UNPARSEABLE, never guessed; every missing reason has the AS_OF basis (decided by what the export held);
  - a snapshot whose own collector time `t` is after the decision is INCONSISTENT_TIME and every value of the row is refused (P36);
  - models fit only through the Phase 07 gate (`labels.training_labels` rows joined by `baselines.join`) and the frozen minimums;
    every fitted object is a JSON card (no pickle); a card trained after a decision cannot score it (P13);
  - a forecast never clears a lab fatal flag (`decision_support`), and a size cap comes from depth only (step 5 of the phase);
  - a transfer is not a sale, an exchange or custody wallet is never an insider, a cluster link is inferred (P18, P19).
No number here is a published probability (Phase 13 calibration and a Phase 16 champion are needed first).
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from . import baselines as B
from . import contract as C
from . import depth_adapter as DA
from . import features as F
from . import labels as L
from . import stats as K
from . import store as S

PHASE = "09"
ONCHAIN_VERSION = "onchain-1"
FEATURE_SET_NAME = "memelab.predictive.onchain"
PROVISIONAL = B.PROVISIONAL
FIXTURE_FLAG = B.FIXTURE_FLAG
SIG = F.SIG
C_L2 = 1.0
M_SHRINK = 20.0
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
TOKEN_SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
EVIDENCE = "LAB_RECORDED"
AS_OF = F.AS_OF
REASONS = {r: AS_OF for r in ("NOT_IN_UNIVERSE", "OUT_OF_SCOPE_CHAIN", "UNPARSEABLE", "NOT_OBSERVED_BY_LAB", "ABSENT_IN_SNAPSHOT",
                              "NO_PRIOR_DECISION", "NO_TOKEN_ROW", "INCONSISTENT_TIME", "INCONSISTENT_RECORD", "NON_POSITIVE")}

# fatal flags by what they say (m24 fatal_flags); every one of them is a veto in the lab (existing overrides)
STRUCTURAL_FLAGS = frozenset({
    "MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE", "PERMANENT_DELEGATE", "TRANSFER_FEE_GT_5PCT", "TRANSFER_HOOK_UNKNOWN",
    "NON_TRANSFERABLE", "HONEYPOT", "CANNOT_BUY", "HIDDEN_OWNER", "EXTREME_TAX", "SIMULATION_FAILED", "AIRDROP_SCAM", "SELFDESTRUCT",
    "CREATOR_PRIOR_HONEYPOT", "PROXY_WITH_LIVE_OWNER", "TAX_MODIFIABLE_BY_OWNER", "LP_RISK_CRITICAL", "NO_SELL_ROUTE", "CANNOT_EXIT_5K"})
DISTRIBUTION_FLAGS = frozenset({"LARGEST_HOLDER_GT_15PCT", "TOP10_GT_50PCT", "DEV_WALLET_FARM", "CLUSTER_OWNERSHIP_GT_25PCT",
                                "INSIDER_DISTRIBUTION"})

LP_RISK = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0, "CRITICAL": 3.0}
CLUSTER_CONF = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0}
EARLY_DIR = {"ACCUMULATING": 0.0, "HOLDING": 1.0, "SCALING_OUT": 2.0, "DISTRIBUTING": 3.0, "EXITING": 4.0}
WASH = {"LOW": 0.0, "MODERATE": 1.0, "MEDIUM": 1.0, "HIGH": 2.0}
NUM = r"(-?[0-9][0-9,]*(?:\.[0-9]+)?)"
# (feature, bucket, pattern); the first group is the value
LINES = {
    "mech_clean": ("token_lp_safety", re.compile(r"^token mechanics clean\b")),
    "mech_issues": ("token_lp_safety", re.compile(r"^token mechanics ([0-9]+) critical issue\(s\)$")),
    "fee": ("token_lp_safety", re.compile(r"^transfer fee " + NUM + r"%$")),
    "lp_risk": ("token_lp_safety", re.compile(r"^LP risk ([A-Z_]+)$")),
    "lp_locked": ("token_lp_safety", re.compile(r"^LP locked/burned " + NUM + r"%$")),
    "route_ok": ("market_execution", re.compile(r"^route OK, ([0-9]+) hop\(s\)$")),
    "no_route": ("market_execution", re.compile(r"^no sell route \((.*)\)$")),
    "friction": ("market_execution", re.compile(r"^round-trip friction " + NUM + r"%$")),
    "largest": ("supply_ownership", re.compile(r"^largest unexplained holder " + NUM + r"%$")),
    "cluster": ("supply_ownership", re.compile(r"^cluster-adjusted ownership " + NUM + r"% \(confidence ([A-Za-z/_]+)\)$")),
    "early": ("supply_ownership", re.compile(r"^early wallets ([A-Za-z_/]+)$")),
    "wash": ("demand_order_flow", re.compile(r"^manipulation screen (.+) / wash ([A-Za-z/_]+)$")),
}


def _f(name, family, unit, transform, model_use=False):
    return {"name": name, "family": family, "unit": unit, "transform": transform, "evidence": EVIDENCE, "version": ONCHAIN_VERSION,
            "model_input": model_use}


DEFINITIONS = [
    _f("oc_structural_fatal", "veto", "0 or 1", "1 when a mechanics, liquidity or exitability fatal flag is present", True),
    _f("oc_distribution_fatal", "distribution", "0 or 1", "1 when an ownership or distribution fatal flag is present", True),
    _f("oc_mechanics_issues", "authority", "count", "token mechanics clean = 0; 'token mechanics N critical issue(s)' = N"),
    _f("oc_mint_authority_active", "authority", "0 or 1", "mechanics observed: MINT_AUTHORITY_ACTIVE flag present"),
    _f("oc_freeze_authority_active", "authority", "0 or 1", "mechanics observed: FREEZE_AUTHORITY_ACTIVE flag present"),
    _f("oc_transfer_fee_pct", "authority", "percent", "'transfer fee X%'"),
    _f("oc_token2022", "authority", "0 or 1", "token row program Token-2022 = 1, SPL Token = 0"),
    _f("oc_lp_risk_ord", "liquidity", "ordinal", "LP risk LOW 0, MODERATE 1, HIGH 2, CRITICAL 3", True),
    _f("oc_lp_locked_pct", "liquidity", "percent", "'LP locked/burned X%'", True),
    _f("oc_exit_cap_share", "liquidity", "ratio", "snapshot exit_cap_3pct / snapshot liquidity (P08)", True),
    _f("oc_no_sell_route", "liquidity", "0 or 1", "'no sell route' or NO_SELL_ROUTE = 1; 'route OK' = 0"),
    _f("oc_route_hops", "liquidity", "count", "'route OK, N hop(s)'"),
    _f("oc_round_trip_friction_pct", "liquidity", "percent", "'round-trip friction X%'"),
    _f("oc_largest_unexplained_pct", "holders", "percent", "'largest unexplained holder X%'", True),
    _f("oc_cluster_confidence_ord", "holders", "ordinal", "cluster confidence LOW 0, MODERATE 1, HIGH 2 (inferred clustering)"),
    _f("oc_early_wallet_dir_ord", "holders", "ordinal", "early wallets ACCUMULATING 0 .. EXITING 4"),
    _f("oc_wash_ord", "flow", "ordinal", "wash LOW 0, MODERATE 1, HIGH 2", True),
    _f("oc_capture_delay_s", "time", "s", "decision time - snapshot.t"),
    _f("oc_d_log1p_liquidity", "change", "ln ratio", "ln(1 + liquidity) - same at the previous decision", True),
    _f("oc_d_log1p_exit_cap", "change", "ln ratio", "ln(1 + exit_cap_3pct) - same at the previous decision", True),
    _f("oc_d_adj_top10_pp", "change", "pp", "adjusted top-10 now - at the previous decision", True),
    _f("oc_d_lp_locked_pp", "change", "pp", "LP locked or burned now - at the previous decision", True),
    _f("oc_authority_switch", "change", "0 or 1", "mint or freeze authority state differs from the previous decision"),
    _f("oc_fee_change_pp", "change", "pp", "transfer fee now - at the previous decision"),
    _f("oc_prior_gap_h", "change", "h", "hours since the previous decision of the mint"),
]
OC = [d["name"] for d in DEFINITIONS]
V2_REUSED = ("thesis_adj_top10_pct",)                       # read from the stored version 2 snapshot, never recomputed here
REQ = ("oc_structural_fatal", "oc_distribution_fatal")
OPT = ("oc_lp_risk_ord", "oc_lp_locked_pct", "oc_exit_cap_share", "oc_largest_unexplained_pct", "thesis_adj_top10_pct", "oc_wash_ord")
TREND = ("oc_d_log1p_liquidity", "oc_d_log1p_exit_cap", "oc_d_adj_top10_pp", "oc_d_lp_locked_pp")


def _spec(kind: str, columns: Sequence[str], rows: Sequence[str]) -> dict:
    return {"kind": kind, "columns": list(columns), "rows": list(rows)}


SPECS = {
    "R1_OC_RULE": _spec("rule", REQ, ()),
    "M1_OC_LOGIT": _spec("logit", REQ + OPT, REQ),
    "M2_OC_LOGIT_B2": _spec("logit", B.B2_COLUMNS + REQ + OPT, B.B2_REQUIRED + REQ),
    "M3_OC_LOGIT_TREND": _spec("logit", B.B2_COLUMNS + REQ + OPT + TREND, B.B2_REQUIRED + REQ),
    "A1_OC_B2_TC": _spec("logit", B.B2_COLUMNS, B.B2_REQUIRED + REQ),
}
MODEL_IDS = ("R1_OC_RULE", "M1_OC_LOGIT", "M2_OC_LOGIT_B2", "M3_OC_LOGIT_TREND", "A1_OC_B2_TC")
PRIMARY = "M2_OC_LOGIT_B2"
RULE = "R1_OC_RULE"
ALLOWED = frozenset(OC) | frozenset(V2_REUSED) | B.ALLOWED_COLUMNS     # every column a Phase 09 model may read (NC2-OC allowlist)


class OnchainError(ValueError):
    pass


class ModelTrainedAfterDecision(OnchainError):
    pass


def feature_set_definitions() -> dict:
    return {"name": FEATURE_SET_NAME, "version": ONCHAIN_VERSION, "definitions": DEFINITIONS, "reasons": REASONS,
            "structural_flags": sorted(STRUCTURAL_FLAGS), "distribution_flags": sorted(DISTRIBUTION_FLAGS),
            "lines": {k: [b, p.pattern] for k, (b, p) in LINES.items()}, "maps": {"lp": LP_RISK, "cluster": CLUSTER_CONF,
                                                                              "early": EARLY_DIR, "wash": WASH},
            "v2_reused": list(V2_REUSED), "base_feature_set_sha": F.feature_set_sha(), "significant_digits": SIG}


def feature_set_sha() -> str:
    return S.sha(feature_set_definitions())


def _r(x: float) -> float:
    return float(f"{float(x):.{SIG}g}")


def _numtxt(s: str) -> float | None:
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return None
    return v if math.isfinite(v) else None


# ---------------------------------------------------------------- parsing one decision row
def _json(x: Any) -> Any:
    if isinstance(x, (dict, list)):
        return x
    if x is None:
        return None
    try:
        return json.loads(x)
    except (TypeError, ValueError):
        return "UNPARSEABLE"


def parse_row(row: dict, token: dict | None) -> dict:
    """The lab's on-chain readings of one thesis row: {key: (value, reason)} plus the flags and the snapshot fields used.
    Pure function of the row (tested; the trace verifier re-implements it independently)."""
    out: dict[str, tuple] = {}
    flags_raw = _json(row.get("fatal_flags_json"))
    if isinstance(flags_raw, list) and all(isinstance(f, dict) for f in flags_raw):
        names = [str(f.get("flag")) for f in flags_raw]
        out["flags"] = (names, None)
    else:
        names = None
        out["flags"] = (None, "ABSENT_IN_SNAPSHOT" if flags_raw is None else "UNPARSEABLE")
    snap = _json(row.get("snapshot_json"))
    snap = snap if isinstance(snap, dict) else None
    out["snapshot"] = (snap, None if snap is not None else "UNPARSEABLE")
    bd = _json(row.get("score_breakdown_json"))
    lines: dict[str, list[str]] | None = None
    if isinstance(bd, dict):
        lines = {}
        for b, v in bd.items():
            if isinstance(v, dict) and isinstance(v.get("rationale"), list):
                lines[b] = [str(s) for s in v["rationale"]]

    def find(key: str) -> tuple[Any, str | None]:
        if lines is None:
            return None, "UNPARSEABLE" if bd not in (None,) else "ABSENT_IN_SNAPSHOT"
        bucket, pat = LINES[key]
        if bucket not in lines:
            return None, "ABSENT_IN_SNAPSHOT"
        for s in lines[bucket]:
            m = pat.match(s)
            if m:
                return m.groups() if m.groups() else (s,), None
        if any(s.startswith("UNKNOWN") for s in lines[bucket]):
            return None, "NOT_OBSERVED_BY_LAB"
        return None, "UNPARSEABLE"

    for key in LINES:
        out[key] = find(key)
    tok_prog = (token or {}).get("token_program") if token is not None else None
    out["token_program"] = (tok_prog, None if token is not None else "NO_TOKEN_ROW")
    return out


def current_values(p: dict) -> dict[str, tuple]:
    """Current-state onchain-1 values (value, reason) from a parsed row."""
    v: dict[str, tuple] = {}
    names, why = p["flags"]
    if names is None:
        v["oc_structural_fatal"] = v["oc_distribution_fatal"] = (None, why)
    else:
        v["oc_structural_fatal"] = (float(any(n in STRUCTURAL_FLAGS for n in names)), None)
        v["oc_distribution_fatal"] = (float(any(n in DISTRIBUTION_FLAGS for n in names)), None)
    clean, wc = p["mech_clean"]
    iss, wi = p["mech_issues"]
    if clean is not None:
        v["oc_mechanics_issues"] = (0.0, None)
    elif iss is not None:
        v["oc_mechanics_issues"] = (float(int(iss[0])), None)
    else:
        v["oc_mechanics_issues"] = (None, wi if wi == wc else (wi or wc))
    mi = v["oc_mechanics_issues"][0]
    for name, flag in (("oc_mint_authority_active", "MINT_AUTHORITY_ACTIVE"), ("oc_freeze_authority_active", "FREEZE_AUTHORITY_ACTIVE")):
        if mi is None:
            v[name] = (None, v["oc_mechanics_issues"][1])
        elif names is None:
            v[name] = (None, why)
        else:
            on = flag in names
            v[name] = (None, "INCONSISTENT_RECORD") if (on and mi == 0) else (float(on), None)
    fee, wf = p["fee"]
    v["oc_transfer_fee_pct"] = (_numtxt(fee[0]), None) if fee and _numtxt(fee[0]) is not None else (None, wf or "UNPARSEABLE")
    tp, wt = p["token_program"]
    v["oc_token2022"] = ((1.0, None) if tp == TOKEN_2022 else (0.0, None) if tp == TOKEN_SPL else
                         (None, wt or ("ABSENT_IN_SNAPSHOT" if tp is None else "UNPARSEABLE")))
    lr, wl = p["lp_risk"]
    v["oc_lp_risk_ord"] = (LP_RISK[lr[0]], None) if lr and lr[0] in LP_RISK else (None, wl or "NOT_OBSERVED_BY_LAB")
    lk, wk = p["lp_locked"]
    v["oc_lp_locked_pct"] = (_numtxt(lk[0]), None) if lk and _numtxt(lk[0]) is not None else (None, wk or "UNPARSEABLE")
    snap, ws = p["snapshot"]
    if snap is None:
        v["oc_exit_cap_share"] = (None, ws)
    else:
        cap, liq = snap.get("exit_cap_3pct"), snap.get("liquidity")
        if cap is None or liq is None:
            v["oc_exit_cap_share"] = (None, "ABSENT_IN_SNAPSHOT")
        elif not (S._num(cap) and S._num(liq)):
            v["oc_exit_cap_share"] = (None, "UNPARSEABLE")
        elif float(liq) <= 0 or float(cap) < 0:
            v["oc_exit_cap_share"] = (None, "NON_POSITIVE")
        else:
            v["oc_exit_cap_share"] = (float(cap) / float(liq), None)
    ok, wo = p["route_ok"]
    nr, wn = p["no_route"]
    if nr is not None or (names is not None and "NO_SELL_ROUTE" in names):
        v["oc_no_sell_route"] = (1.0, None)
    elif ok is not None:
        v["oc_no_sell_route"] = (0.0, None)
    else:
        v["oc_no_sell_route"] = (None, wo or wn)
    v["oc_route_hops"] = (float(int(ok[0])), None) if ok is not None else (None, "NOT_OBSERVED_BY_LAB" if nr is not None else wo)
    fr, wr = p["friction"]
    v["oc_round_trip_friction_pct"] = (_numtxt(fr[0]), None) if fr and _numtxt(fr[0]) is not None else (None, wr or "UNPARSEABLE")
    lg, wg = p["largest"]
    v["oc_largest_unexplained_pct"] = (_numtxt(lg[0]), None) if lg and _numtxt(lg[0]) is not None else (None, wg or "UNPARSEABLE")
    cl, wcl = p["cluster"]
    v["oc_cluster_confidence_ord"] = ((CLUSTER_CONF[cl[1].upper()], None) if cl and cl[1].upper() in CLUSTER_CONF else
                                      (None, wcl or "NOT_OBSERVED_BY_LAB"))
    ea, we = p["early"]
    v["oc_early_wallet_dir_ord"] = ((EARLY_DIR[ea[0].upper()], None) if ea and ea[0].upper() in EARLY_DIR else
                                    (None, we or "NOT_OBSERVED_BY_LAB"))
    wa, ww = p["wash"]
    v["oc_wash_ord"] = (WASH[wa[1].upper()], None) if wa and wa[1].upper() in WASH else (None, ww or "NOT_OBSERVED_BY_LAB")
    return v


def _aux(p: dict) -> dict:
    """Snapshot fields shared with version 2 (consistency check) and the raw inputs of the change features."""
    snap = p["snapshot"][0] or {}
    g = lambda k: float(snap[k]) if S._num(snap.get(k)) else None
    return {"liquidity": g("liquidity"), "exit_cap_3pct": g("exit_cap_3pct"), "adj_top10": g("adj_top10"), "t": g("t")}


# ---------------------------------------------------------------- the as-of snapshot
def _value(v: float | None, reason: str | None, avail: float | None, inputs: Sequence[str]) -> dict:
    if (v is None) == (reason is None):
        raise OnchainError("exactly one of value or missing reason")
    if v is not None and not math.isfinite(v):
        raise OnchainError(f"value {v!r} is not finite (P38)")
    if reason is not None and reason not in REASONS:
        raise OnchainError(f"unknown missing reason {reason!r}")
    return {"value": _r(v) if v is not None else None, "missing_reason": reason, "missing_basis": REASONS[reason] if reason else None,
            "available_at": float(avail) if (v is not None and avail is not None) else None, "evidence": EVIDENCE,
            "inputs": sorted(inputs) if v is not None else []}


def onchain_as_of(con: sqlite3.Connection, chain: str, mint: str, decision_time: float, *, decision_key: str | None = None) -> dict:
    """onchain-1 of one exact (chain, mint) at T from the store's decision rows visible at T (audited). Deterministic."""
    T = float(decision_time)
    view = F.AsOfView(con, T, "provider")
    decs = view.decisions_of(chain, mint)
    dec = None
    if decision_key is not None:
        dec = next((d for d in decs if d["decision_key"] == decision_key), None)
        if dec is None:
            raise OnchainError(f"decision {decision_key[:12]} is not visible at T for this chain and mint (P01, P43)")
        if float(dec["decision_time"]) != T:
            raise OnchainError("decision time differs from T")
    elif decs:
        dec = decs[-1]
    vals: dict[str, dict] = {}
    aux = {}
    if dec is None:
        vals = {n: _value(None, "NOT_IN_UNIVERSE", None, ()) for n in OC}
    elif chain != "solana":
        vals = {n: _value(None, "OUT_OF_SCOPE_CHAIN", None, ()) for n in OC}
    else:
        row = json.loads(dec["row_json"])
        tok = json.loads(dec["token_json"]) if dec["token_json"] else None
        p = parse_row(row, tok)
        aux = _aux(p)
        Td = float(dec["decision_time"])
        if aux["t"] is not None and aux["t"] > Td:
            vals = {n: _value(None, "INCONSISTENT_TIME", None, ()) for n in OC}
        else:
            cur = current_values(p)
            ins = ["decision:" + dec["decision_key"]]
            for n, (v, why) in cur.items():
                vals[n] = _value(v, why, Td, ins)
            vals["oc_capture_delay_s"] = (_value(Td - aux["t"], None, Td, ins) if aux["t"] is not None else
                                          _value(None, "ABSENT_IN_SNAPSHOT", None, ()))
            prior = [d for d in decs if float(d["decision_time"]) < Td]
            if not prior:
                for n in ("oc_d_log1p_liquidity", "oc_d_log1p_exit_cap", "oc_d_adj_top10_pp", "oc_d_lp_locked_pp",
                          "oc_authority_switch", "oc_fee_change_pp", "oc_prior_gap_h"):
                    vals[n] = _value(None, "NO_PRIOR_DECISION", None, ())
            else:
                pd = prior[-1]
                pp = parse_row(json.loads(pd["row_json"]), json.loads(pd["token_json"]) if pd["token_json"] else None)
                pa, pc = _aux(pp), current_values(pp)
                Tp = float(pd["decision_time"])
                pins = ins + ["decision:" + pd["decision_key"]]
                if pa["t"] is not None and pa["t"] > Tp:
                    pa, pc = {k: None for k in pa}, {k: (None, "INCONSISTENT_TIME") for k in pc}

                def diff(name, a, b, log1p=False):
                    if a is None or b is None:
                        vals[name] = _value(None, "ABSENT_IN_SNAPSHOT", None, ())
                    elif log1p and (a < 0 or b < 0):
                        vals[name] = _value(None, "NON_POSITIVE", None, ())
                    else:
                        vals[name] = _value((math.log1p(a) - math.log1p(b)) if log1p else (a - b), None, Td, pins)

                diff("oc_d_log1p_liquidity", aux["liquidity"], pa["liquidity"], True)
                diff("oc_d_log1p_exit_cap", aux["exit_cap_3pct"], pa["exit_cap_3pct"], True)
                diff("oc_d_adj_top10_pp", aux["adj_top10"], pa["adj_top10"])
                a, b = cur["oc_lp_locked_pct"][0], pc["oc_lp_locked_pct"][0]
                vals["oc_d_lp_locked_pp"] = (_value(a - b, None, Td, pins) if a is not None and b is not None else
                                             _value(None, cur["oc_lp_locked_pct"][1] or pc["oc_lp_locked_pct"][1] or "UNPARSEABLE", None, ()))
                st = [(cur[n][0], pc[n][0]) for n in ("oc_mint_authority_active", "oc_freeze_authority_active")]
                if all(x is not None and y is not None for x, y in st):
                    vals["oc_authority_switch"] = _value(float(any(x != y for x, y in st)), None, Td, pins)
                else:
                    vals["oc_authority_switch"] = _value(None, "NOT_OBSERVED_BY_LAB", None, ())
                a, b = cur["oc_transfer_fee_pct"][0], pc["oc_transfer_fee_pct"][0]
                vals["oc_fee_change_pp"] = (_value(a - b, None, Td, pins) if a is not None and b is not None else
                                            _value(None, "NOT_OBSERVED_BY_LAB", None, ()))
                vals["oc_prior_gap_h"] = _value((Td - Tp) / 3600.0, None, Td, pins)
    for n in OC:
        if n not in vals:
            raise OnchainError(f"{n} not computed")
    snap = {"chain": chain, "mint": mint, "decision_time": T, "decision_key": dec["decision_key"] if dec else None,
            "row_sha256": dec["row_sha256"] if dec else None, "onchain_version": ONCHAIN_VERSION,
            "feature_set_sha": feature_set_sha(), "values": {n: vals[n] for n in OC}, "aux": aux,
            "rows_audited": view.audit.records}
    snap["onchain_snapshot_sha"] = S.sha({k: snap[k] for k in ("chain", "mint", "decision_time", "decision_key", "row_sha256",
                                                                "onchain_version", "values")})
    return snap


def row_status(snap: dict, cols: Sequence[str]) -> str | None:
    """None when every listed onchain-1 column has a value, else OOD (every reason is AS_OF: no censoring here)."""
    return None if all(snap["values"][c]["value"] is not None for c in cols if c in snap["values"]) else "OOD"


def v2_consistency(snap: dict, v2_row: dict) -> list[str]:
    """Snapshot fields read here and by version 2 must agree at 10 significant digits (adjusted top-10, ln(1 + liquidity),
    ln(1 + exit capacity))."""
    out = []
    aux = snap.get("aux") or {}
    for mine, v2, fn in (("adj_top10", "thesis_adj_top10_pct", lambda x: x), ("liquidity", "thesis_log1p_liquidity_usd", math.log1p),
                         ("exit_cap_3pct", "thesis_log1p_exit_cap_3pct_usd", math.log1p)):
        a = aux.get(mine)
        b = v2_row.get(v2)
        if a is not None and a < 0:
            a = None
        a = None if a is None else _r(fn(a))
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9 * max(1.0, abs(a))):
            out.append(f"{mine}: onchain {a!r} vs v2 {v2} {b!r}")
    return out


# ---------------------------------------------------------------- examples
@dataclass
class OExample(B.Example):
    oc_reasons: dict = field(default_factory=dict)
    oc_sha: str | None = None
    row_sha256: str | None = None


def attach(examples: Sequence[B.Example], snaps: dict[str, dict], v2_rows: dict[str, dict]) -> list[OExample]:
    """Phase 07 examples with their onchain-1 snapshot and the reused version 2 columns, joined by decision key with chain,
    mint and decision time checked (P01)."""
    out = []
    for e in examples:
        s = snaps.get(e.decision_key)
        f = v2_rows.get(e.decision_key)
        if s is None or f is None:
            raise OnchainError(f"no onchain-1 snapshot or version 2 row for decision {e.decision_key[:12]}")
        if s["decision_key"] != e.decision_key or s["chain"] != e.chain or s["mint"] != e.mint or float(s["decision_time"]) != e.decision_time:
            raise B.IdentityJoinError("onchain-1 snapshot of another decision (P01)")
        B.check_identity({"chain": e.chain, "mint": e.mint, "decision_time": e.decision_time, "decision_key": e.decision_key}, f)
        x, av = dict(e.x), dict(e.avail)
        for c in OC:
            v = s["values"][c]
            x[c] = v["value"] if v["value"] is not None else float("nan")
            if v["value"] is None:
                av[c] = e.decision_time               # a missing value carries no input
            elif v["available_at"] is None:
                raise OnchainError(f"{c}: a value without an availability time")
            else:
                av[c] = v["available_at"]
        for c in V2_REUSED:
            x[c] = B._num(f.get(c))
            a = f.get(c + "__available_at")
            av[c] = a if a is not None else e.decision_time
        out.append(OExample(**{**e.__dict__, "x": x, "avail": av},
                            oc_reasons={c: s["values"][c]["missing_reason"] for c in OC if s["values"][c]["value"] is None},
                            oc_sha=s["onchain_snapshot_sha"], row_sha256=s["row_sha256"]))
    return out


def check_asof(examples: Sequence[B.Example], columns: Sequence[str], *, as_of: float | None, with_labels: bool) -> None:
    """Every column in the Phase 09 allowlist and available at or before its decision; decisions at or before as_of; labels
    matured by as_of when given (features.validate_rows; P36, P05, P43)."""
    bad = [c for c in columns if c not in ALLOWED]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 09 allowlist (NC2-OC: only declared as-of inputs reach a fit)")
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
        raise F.AsOfError(f"columns {bad} are not in the Phase 09 allowlist")
    return np.array([[e.x.get(c, float("nan")) for c in columns] for e in examples], dtype=float).reshape(len(examples), len(columns))


def complete(e: B.Example, cols: Sequence[str]) -> bool:
    return all(math.isfinite(B._num(e.x.get(c))) for c in cols)


# ---------------------------------------------------------------- cards
def _card(model_id: str, target: str, train: Sequence[B.Example], cutoff: float, body: dict, *, n_used: int, k_used: int,
          is_fixture: bool, meta: dict | None = None) -> dict:
    y = B.labels_of(train)
    card = {"phase": PHASE, "kind": model_id, "model_id": f"{model_id}:{target}", "targets": [target],
            "target_version": {target: C.TARGETS[target]["version"]}, "training_cutoff": float(cutoff),
            "training_cutoff_utc": B._iso(cutoff), "registry_sha": C.registry_sha256(), "feature_set_sha": feature_set_sha(),
            "onchain_version": ONCHAIN_VERSION, "base_feature_set_sha": F.feature_set_sha(), "feature_version": F.FEATURE_VERSION,
            "labels_version": L.LABELS_VERSION, "store_schema": S.SCHEMA_VERSION, "label_mode": "provider",
            "n_train": int(len(train)), "k_train": int(y.sum()) if len(train) else 0, "n_used": int(n_used), "k_used": int(k_used),
            "label_set_sha": B.sha(sorted([e.label_key or e.decision_key, e.y] for e in train)),
            "data_snapshot_sha": B.sha(sorted([e.decision_key, e.snapshot_sha256, getattr(e, "oc_sha", None)] for e in train)),
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
        raise OnchainError("card trained under another registry fingerprint")
    if card.get("feature_set_sha") != feature_set_sha() or card.get("onchain_version") != ONCHAIN_VERSION:
        raise F.FeatureVersionError("FEATURE_SCHEMA_MISMATCH: onchain-1 definitions differ from the card's (P46)")
    F.require_compatible(card["feature_version"], card["base_feature_set_sha"])
    return card


def dumps(card: dict) -> str:
    return B.dumps(card)


def loads(text: str) -> dict:
    return verify_card(json.loads(text))


def _cell(e: B.Example) -> str:
    a, b = B._num(e.x.get(REQ[0])), B._num(e.x.get(REQ[1]))
    if not (math.isfinite(a) and math.isfinite(b)):
        return "MISSING"
    return f"S{int(a)}D{int(b)}"


def fit(model_id: str, target: str, train: Sequence[B.Example], cutoff: float, *, y_override: np.ndarray | None = None,
        is_fixture: bool = False, meta: dict | None = None, card_kind: str | None = None) -> dict:
    """One Phase 09 model on one training set (rows decided before and matured by the cutoff, checked)."""
    spec = SPECS[model_id]
    check_asof(train, sorted(set(spec["columns"]) | set(spec["rows"])), as_of=cutoff, with_labels=True)
    for e in train:
        if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):
            raise B.BaselineError(f"training row {e.decision_key[:12]} is not decided before and matured by the cutoff (P05, P43)")
    y_all = B.labels_of(train) if y_override is None else np.asarray(y_override, float)
    kind = card_kind or model_id
    if spec["kind"] == "rule":
        g = B.gate(len(train), int(y_all.sum()))
        if g:
            return _card(kind, target, train, cutoff, {"abstain": g, "spec": spec}, n_used=len(train), k_used=int(y_all.sum()),
                         is_fixture=is_fixture, meta=meta)
        b0 = float(y_all.mean())
        groups: dict[str, list[int]] = {}
        for e, yy in zip(train, y_all):
            c = _cell(e)
            if c != "MISSING":
                groups.setdefault(c, []).append(int(yy))
        body = {"spec": spec, "b0": b0, "m": M_SHRINK,
                "cells": {g_: {"n": len(v), "k": int(sum(v)), "p": (sum(v) + M_SHRINK * b0) / (len(v) + M_SHRINK)} for g_, v in sorted(groups.items())}}
        return _card(kind, target, train, cutoff, body, n_used=len(train), k_used=int(y_all.sum()), is_fixture=is_fixture, meta=meta)
    use = [i for i, e in enumerate(train) if complete(e, spec["rows"])]
    y = y_all[use] if use else np.array([])
    g = B.gate(len(use), int(y.sum()))
    if g:
        return _card(kind, target, train, cutoff, {"abstain": g, "spec": spec}, n_used=len(use), k_used=int(y.sum()),
                     is_fixture=is_fixture, meta=meta)
    X = matrix([train[i] for i in use], spec["columns"])
    prep = K.Prep().fit(X)
    m = K.Logistic(C=C_L2).fit(prep.transform(X), y)
    body = {"spec": spec, "prep": prep.to_dict(), "logistic": m.to_dict()}
    body["train_prediction_sd"] = float(np.std(predict_numbers({"kind": kind, "body": body}, [train[i] for i in use])[0]))
    return _card(kind, target, train, cutoff, body, n_used=len(use), k_used=int(y.sum()), is_fixture=is_fixture, meta=meta)


def predict_numbers(card: dict, examples: Sequence[B.Example]) -> tuple[np.ndarray, list[str | None]]:
    body = card["body"]
    n = len(examples)
    if "abstain" in body:
        return np.full(n, np.nan), [body["abstain"]] * n
    spec = body["spec"]
    p, why = np.full(n, np.nan), [None] * n
    if spec["kind"] == "rule":
        for i, e in enumerate(examples):
            c = _cell(e)
            p[i] = body["cells"][c]["p"] if c in body["cells"] else body["b0"]
    else:
        ok = [i for i, e in enumerate(examples) if complete(e, spec["rows"])]
        for i in set(range(n)) - set(ok):
            why[i] = "OOD"
        if ok:
            X = matrix([examples[i] for i in ok], spec["columns"])
            prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])
            p[ok] = lr.predict_proba1(prep.transform(X))
    fin = p[np.isfinite(p)]
    if fin.size:
        K.check_probs(fin)
    return p, why


def predict(card: dict, examples: Sequence[B.Example]) -> tuple[np.ndarray, list[str | None]]:
    """Numbers for decisions at or after the card's training cutoff only (P13), each input available at its decision (P36)."""
    early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]
    if early:
        raise ModelTrainedAfterDecision(f"card {card['model_id']} trained to {card['training_cutoff_utc']} cannot score "
                                        f"{len(early)} earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)")
    spec = card["body"].get("spec")
    if examples and spec:
        check_asof(examples, sorted(set(spec["columns"]) | set(spec["rows"])), as_of=None, with_labels=False)
    return predict_numbers(card, examples)


def degenerate(p: Any) -> bool:
    q = np.asarray(p, float)
    q = q[np.isfinite(q)]
    return bool(q.size > 1 and np.ptp(q) == 0)


def veto_alarm(e: B.Example) -> bool | None:
    """R0: the hard structural veto as an alarm (not a probability). None when the flag is missing."""
    v = B._num(e.x.get("oc_structural_fatal"))
    return None if not math.isfinite(v) else bool(v == 1.0)


# ---------------------------------------------------------------- the frozen walk-forward, same folds as Phase 07
def walk_forward(target: str, development: Sequence[OExample], train_at: Callable[[float], Sequence[OExample]], *,
                 nc1_seeds: Iterable[int] = range(20), is_fixture: bool = False, models: Sequence[str] = MODEL_IDS) -> dict:
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
                cnc = fit(PRIMARY, target, train, cut, y_override=yy, is_fixture=is_fixture, meta={"nc1_seed": s}, card_kind="NC1OC")
                nc1[s] = predict(cnc, test)[0]
        mints_tr = {e.mint for e in train}
        creators_tr = {e.creator for e in train if e.creator}
        narr_tr = {e.narrative for e in train if e.narrative}
        for j, e in enumerate(test):
            row = {"fold": k, "cutoff": cut, "example": e, "y": e.y, "new_mint": e.mint not in mints_tr,
                   "new_creator": (e.creator not in creators_tr) if e.creator else None,
                   "new_narrative": (e.narrative not in narr_tr) if e.narrative else None, "R0_alarm": veto_alarm(e)}
            for m in preds:
                row[m] = float(preds[m][0][j])
                row[m + "_why"] = preds[m][1][j]
            for s, v in nc1.items():
                row[f"NC1OC_{s}"] = float(v[j])
            oos.append(row)
        out_folds.append({"fold": k, "cutoff": cut, "cutoff_utc": B._iso(cut), "n_train": len(train),
                          "k_train": int(B.labels_of(train).sum()), "n_test": len(test), "k_test": int(sum(e.y for e in test)),
                          "used": {m: [cards[m]["n_used"], cards[m]["k_used"], cards[m]["body"].get("abstain")] for m in models},
                          "test_day": B._iso(cut)[:10], "cards": cards,
                          "split_fingerprint": B.sha([target, cut, want, sorted(e.decision_key for e in test)])})
    return {"target": target, "folds": out_folds, "oos": oos, "audit": audit, "nc1_seeds": seeds,
            "evidence_class": B.evidence_class(is_fixture), "split_fingerprint": B.sha([f["split_fingerprint"] for f in out_folds]),
            "status": "OK" if out_folds else "INSUFFICIENT_HISTORY"}


def early_warning(rows: Sequence[dict], model: str, *, touch: dict[str, float | None]) -> dict:
    """Alarms of `model` (R0: the veto flag; otherwise a number above the fold's B0) on out-of-sample rows: hits, misses (unseen
    risks), false alarms (their count is the false-alarm cost; the targets carry no size, so no money value), correct
    rejections, and each hit's lead time from the decision to the label's first touch. An alarm is raised at the decision, which
    is before the label window opens (checked: a negative lead time raises)."""
    out = {"model": model, "scored": 0, "hits": 0, "misses": 0, "false_alarms": 0, "correct_rejections": 0, "lead_times_h": []}
    for r in rows:
        e = r["example"]
        if model == "R0_OC_VETO":
            a = r.get("R0_alarm")
            if a is None:
                continue
        else:
            if not (math.isfinite(r[model]) and math.isfinite(r["B0"])):
                continue
            a = r[model] > r["B0"]
        out["scored"] += 1
        y = r["y"]
        if a and y:
            out["hits"] += 1
            t = touch.get(e.decision_key)
            if t is not None:
                lead = float(t) - e.decision_time
                if lead < 0:
                    raise OnchainError(f"alarm after the event for {e.decision_key[:12]}: not an early warning")
                out["lead_times_h"].append(round(lead / 3600.0, 4))
        elif y:
            out["misses"] += 1
        elif a:
            out["false_alarms"] += 1
        else:
            out["correct_rejections"] += 1
    lt = out["lead_times_h"]
    out["lead_time_h_median"] = float(np.median(lt)) if lt else None
    out["support_note"] = "n >= 20" if out["scored"] >= C.ACCEPTANCE["min_bin_events"] else "n < 20: counts only, no rate claimed"
    return out


# ---------------------------------------------------------------- decision support: veto and size cap (phase step 5)
def structural_veto(fatal_flags: Sequence[Any] | None) -> dict:
    """Every lab fatal flag is a veto (the existing overrides); the structural ones are listed apart. A missing or unreadable
    flag list is not a pass: VETO_UNKNOWN."""
    if fatal_flags is None:
        return {"veto": None, "state": "VETO_UNKNOWN", "flags": [], "structural": []}
    names = [str(f.get("flag") if isinstance(f, dict) else f) for f in fatal_flags]
    return {"veto": bool(names), "state": "VETO" if names else "NO_FATAL_FLAG", "flags": names,
            "structural": [n for n in names if n in STRUCTURAL_FLAGS]}


def size_cap_usd(quotes: Sequence[dict], *, decision_time: float, pool_address: str, max_loss: float, max_age_s: float) -> dict:
    """Largest quoted size whose newest sell quote on the decision's pool, read at or before the decision and at most `max_age_s`
    old, is OK and returns at least (1 - max_loss) of the size. From depth only: no probability enters (independent of any
    classifier output). Rows of another pool (P02), rows captured after the decision (CX-09, CX-S09) and older reads of a size
    with a newer one are never used; nothing usable gives EXECUTION_DATA_MISSING (P44). `quotes` are depth_adapter observations."""
    if not (isinstance(max_loss, (int, float)) and 0 < max_loss < 1):
        raise OnchainError("max_loss must be in (0, 1)")
    if not (isinstance(max_age_s, (int, float)) and not isinstance(max_age_s, bool) and math.isfinite(max_age_s) and max_age_s > 0):
        raise OnchainError("max_age_s must be a positive number")
    T = float(decision_time)
    rows = [q for q in DA.visible_at(quotes, T) if q.get("kind") == "QUOTE" and q.get("pool_address") == pool_address
            and q.get("state") in DA.ANSWERED and q.get("size_usd") is not None]
    DA.assert_visible(rows, T)
    newest: dict[float, dict] = {}
    for q in sorted(rows, key=lambda q: (q["available_at"], q.get("id") or 0)):
        newest[float(q["size_usd"])] = q
    fresh = {s: q for s, q in newest.items() if T - q["available_at"] <= max_age_s}
    ok = {s: q for s, q in fresh.items() if q["state"] == "OK" and q.get("proceeds_ratio") is not None}
    if not ok:
        return {"size_cap_usd": None, "basis": "EXECUTION_DATA_MISSING", "pool_address": pool_address,
                "route_lost_sizes": sorted(s for s, q in fresh.items() if q["state"] in DA.ROUTE_LOST)}
    good = [s for s, q in ok.items() if q["proceeds_ratio"] >= 1 - max_loss]
    return {"size_cap_usd": max(good) if good else 0.0, "basis": "FORWARD_QUOTES_VISIBLE_AT_DECISION", "pool_address": pool_address,
            "quotes_used": len(ok), "oldest_used_age_s": max(T - q["available_at"] for q in ok.values()),
            "route_lost_sizes": sorted(s for s, q in fresh.items() if q["state"] in DA.ROUTE_LOST)}


def decision_support(forecast_doc: dict, fatal_flags: Sequence[Any] | None, quotes: Sequence[dict], *, decision_time: float,
                     pool_address: str | None, max_loss: float, max_age_s: float) -> dict:
    """The forecast beside the structural veto and a depth-only size cap at the decision on the decision's pool. The veto and the
    cap are computed without looking at the forecast; a forecast never clears a veto (`veto_overrides_forecast`)."""
    v = structural_veto(fatal_flags)
    if pool_address is None:
        cap = {"size_cap_usd": None, "basis": "EXECUTION_DATA_MISSING", "pool_address": None, "route_lost_sizes": []}
    else:
        cap = size_cap_usd(quotes, decision_time=decision_time, pool_address=pool_address, max_loss=max_loss, max_age_s=max_age_s)
    return {"forecast": forecast_doc, "structural_veto": v, "veto_overrides_forecast": v["veto"] is not False,
            "size_cap": cap, "position_usd_from_forecast": None,
            "note": "research only; a forecast is not an order; the lab's fatal flags and sizing rules apply unchanged"}


# ---------------------------------------------------------------- identity of a lab authority read (skeptic M1)
def metadata_mints(extensions: Any) -> set[str]:
    """Mint addresses named inside a Token-2022 extension list (tokenMetadata.mint, metadataPointer.metadataAddress)."""
    ext = _json(extensions)
    out: set[str] = set()
    if not isinstance(ext, list):
        return out
    for e in ext:
        st = e.get("state") if isinstance(e, dict) else None
        if not isinstance(st, dict):
            continue
        if e.get("extension") == "tokenMetadata" and isinstance(st.get("mint"), str):
            out.add(st["mint"])
        if e.get("extension") == "metadataPointer" and isinstance(st.get("metadataAddress"), str):
            out.add(st["metadataAddress"])
    return out


def authority_read_identity(mint: str, extensions: Any) -> str:
    """OK when every mint named in the read's own metadata is the row's mint (or none is named, NO_METADATA); else
    OTHER_MINT_METADATA: the row mixes two identities (P01) and is refused as a reference."""
    named = metadata_mints(extensions)
    if not named:
        return "NO_METADATA"
    return "OK" if named == {mint} else "OTHER_MINT_METADATA"


# ---------------------------------------------------------------- wallet movements (P18, P19, developer wallet)
MINT_SUFFIXES = ("pump",)                      # pump.fun ground mint addresses end in "pump": such an address is a likely mint


def wallet_role(address: str, *, token_row: dict | None, custody: Iterable[str] = (), cex_labels: dict | None = None,
                clusters: dict | None = None, known_mints: Iterable[str] = ()) -> dict:
    """Role of one address for distribution questions. Exchange or custody first (never an insider, P19); developer only when the
    address is the token row's creator or dev wallet and does not look like a mint (else DEV_LABEL_SUSPECT); a cluster link is
    INFERRED with its confidence (observed versus inferred clustering kept apart)."""
    cex_labels = cex_labels or {}
    if address in set(custody) or address in cex_labels:
        return {"role": "CUSTODY_OR_EXCHANGE", "basis": "LABELLED", "label": cex_labels.get(address), "insider": False}
    tr = token_row or {}
    if address and address in (tr.get("creator"), tr.get("dev_wallet")):
        if address.endswith(MINT_SUFFIXES) or address == tr.get("mint") or address in set(known_mints):
            return {"role": "DEV_LABEL_SUSPECT", "basis": "INFERENCE", "label": "address looks like a mint, not a wallet", "insider": None}
        return {"role": "DEV", "basis": "OBSERVED", "label": "creator or dev wallet of the token row", "insider": True}
    if clusters and address in clusters:
        return {"role": "CLUSTER_MEMBER_INFERRED", "basis": "INFERRED", "label": clusters[address], "insider": None}
    return {"role": "UNKNOWN", "basis": "UNKNOWN", "label": None, "insider": None}


def movement_class(movement: dict, role: dict) -> dict:
    """A movement is a sale only when it is a swap that sells the mint into a pool. A transfer is MOVEMENT_NOT_SALE whoever moves
    it (a whale transfer or a deposit to an exchange is not a sale, P18); only an OBSERVED developer's sale counts as insider
    distribution; an inferred cluster member's sale is counted apart, never as observed."""
    kind, direction = movement.get("kind"), movement.get("direction")
    is_sale = kind == "SWAP" and direction == "SELL" and bool(movement.get("counterparty_is_pool"))
    if kind == "TRANSFER":
        cls = "MOVEMENT_NOT_SALE"
    elif is_sale:
        cls = "SALE"
    elif kind == "SWAP" and direction == "BUY":
        cls = "BUY"
    else:
        cls = "UNKNOWN_MOVEMENT"
    return {"class": cls, "is_sale": is_sale,
            "counts_as_insider_distribution": bool(is_sale and role.get("role") == "DEV" and role.get("basis") == "OBSERVED"),
            "counts_as_inferred_distribution": bool(is_sale and role.get("role") == "CLUSTER_MEMBER_INFERRED"),
            "note": ("TRANSFER_TO_CUSTODY_SALE_UNOBSERVED" if kind == "TRANSFER" and movement.get("to_role") == "CUSTODY_OR_EXCHANGE"
                     else None)}

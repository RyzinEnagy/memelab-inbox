"""Phase 10: point-in-time social, narrative and catalyst evidence (socialcat-1), the social and catalyst models on the frozen
targets, the catalyst classifier, the read-only social evidence adapter and the unfrozen catalyst target proposals (research
only, flag OFF, imported by no existing module). numpy and the standard library only, plus two reused social-intel seams:
`memelab.social.replay_core` (Audit, LeakageError, through features.AsOfView and directly) and `memelab.social.alpha_core.wilson`.
No network, no clock, no language model.

Pre-registration: audits/predictive-intelligence/phase_10/ACCEPTANCE_CHECKLIST.md, experiments/EXPERIMENT_REGISTRY.csv and
PI-D-057 (committed before any feature on a labelled row and before any fit). Rules enforced here:
  - the real decision path reads only what the lab recorded at the decision: the thesis row and the token row stored with the
    decision (the export where the decision row first appears), the previous decision of the same chain and mint, and the
    `narratives` / `narrative_snapshots` tables of the export commit that is the decision (commit time equal to T and blob equal
    to the stored `export_blob`, else refused). A value is available at T (PI-D-015); evidence LAB_RECORDED. The newest export's
    token row is never used (counterexample CX-10: tags and channels are filled in later);
  - no social item or catalyst event exists for these decisions (none exported), so every real decision carries the states
    SOCIAL_TABLES_NOT_EXPORTED and CATALYST_TABLES_NOT_EXPORTED; nothing crawled today stands in for them (P04);
  - catalyst identity is an exact chain and mint link NAMED_IN_SOURCE or OFFICIAL / STRONG whose mint appears in a visible
    original or independent source item; a mint named only on a crawled page or a ticker or name match is not identity (PI-D-007,
    PI-D-012, the Phase 00 P41 finding); an unverified catalyst returns an explicit state and never a probability (P17, P45); a
    VERIFIED catalyst is available only from the time its last condition held (identity, CONFIRMED evidence, the official or
    second independent source), never from its first sighting (repair pass 2, CX-10b-A, PI-D-060);
  - social evidence: first-known original versions only (P03), deleted items excluded (P17), duplicates by content hash and by
    trader collapsed (P15), bot accounts and suspensions excluded and reported only when known at T (P16; an account label
    without a time is UNKNOWN at T in a replay, CX-10b-B, PI-D-060), ticker-only mentions never identity, claims extracted by a
    model excluded (P26), every row audited at T (P36);
  - models fit only through the Phase 07 gate (`labels.training_labels` rows joined by `baselines.join`) and the frozen minimums;
    every fitted object is a JSON card (no pickle); a card trained after a decision cannot score it (P13).
No number here is a published probability (Phase 13 calibration and a Phase 16 champion are needed first).
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from ..social import alpha_core as AC
from ..social import replay_core as RC
from . import baselines as B
from . import contract as C
from . import features as F
from . import labels as L
from . import stats as K
from . import store as S
from . import technical as T

PHASE = "10"
SOCIALCAT_VERSION = "socialcat-1"
FEATURE_SET_NAME = "memelab.predictive.socialcat"
PROVISIONAL = B.PROVISIONAL
SIG = F.SIG
C_L2 = 1.0
M_SHRINK = 20.0
EVIDENCE = "LAB_RECORDED"
AS_OF = F.AS_OF
REASONS = {r: AS_OF for r in ("NOT_IN_UNIVERSE", "OUT_OF_SCOPE_CHAIN", "UNPARSEABLE", "NOT_OBSERVED_BY_LAB", "ABSENT_IN_SNAPSHOT",
                              "NO_PRIOR_DECISION", "NO_TOKEN_ROW", "NO_NARRATIVE_TAG", "NO_NARRATIVE_SNAPSHOT", "INCONSISTENT_TIME",
                              "INCONSISTENT_RECORD", "CONTEXT_NOT_SUPPLIED")}
CATALYST_STATE_REAL = "CATALYST_TABLES_NOT_EXPORTED"
SOCIAL_STATE_REAL = "SOCIAL_TABLES_NOT_EXPORTED"

TREND = {"EXHAUSTION": 0.0, "STABILITY": 1.0, "ACCELERATION": 2.0}
MANIP = {"MOSTLY ORGANIC": 0.0, "MIXED / UNCERTAIN": 1.0, "LIKELY MANUFACTURED": 2.0, "SEVERELY MANIPULATED": 3.0}
LATE_STAGES = frozenset({"DISTRIBUTION", "BREAKDOWN", "POST_BREAKDOWN"})
EARLY_STAGES = frozenset({"LAUNCH", "DISCOVERY", "EARLY_EXPANSION", "BROAD_ATTENTION", "MANIA"})
CONF = {"LOW": 0.0, "MODERATE": 1.0, "HIGH": 2.0}
NARR_LC = {"DEAD": 0.0, "EXHAUSTING": 1.0, "MATURE": 2.0, "EMERGING": 3.0, "ACCELERATING": 4.0, "MANIA": 5.0}
CHANNEL_FIELDS = ("website", "twitter", "telegram")
SEARCH_RX = re.compile(r"/search\b|search\?|[?&]q=", re.I)
NUM = r"(-?[0-9][0-9,]*(?:\.[0-9]+)?)"
LINES = {
    "trend": ("attention_narrative", re.compile(r"^attention trend ([A-Z_]+)$")),
    "trend_unknown": ("attention_narrative", re.compile(r"^UNKNOWN: (attention trend missing|no attention module output)$")),
    "strength": ("attention_narrative", re.compile(r"^narrative strength " + NUM + r"$")),
    "strength_unknown": ("attention_narrative", re.compile(r"^UNKNOWN: (narrative strength missing|no attention module output)$")),
    "organic": ("attention_narrative", re.compile(r"^attention (organic|paid/boosted)$")),
    "organic_unknown": ("attention_narrative", re.compile(r"^UNKNOWN: (organic vs paid attention unknown|no attention module output)$")),
    "manip": ("demand_order_flow", re.compile(r"^manipulation screen (.+) / wash ([A-Za-z/_]+)$")),
    "lifecycle": ("lifecycle_relative_strength", re.compile(r"^lifecycle ([A-Z_/]+) \(confidence ([A-Z]+)\)$")),
}


def _f(name, family, unit, transform, model_use=False):
    return {"name": name, "family": family, "unit": unit, "transform": transform, "evidence": EVIDENCE, "version": SOCIALCAT_VERSION,
            "model_input": model_use}


DEFINITIONS = [
    _f("sc_attention_trend_ord", "attention", "ordinal", "'attention trend X': EXHAUSTION 0, STABILITY 1, ACCELERATION 2", True),
    _f("sc_narrative_strength", "attention", "0 to 1", "'narrative strength N' (the lab's m19 proxy)", True),
    _f("sc_attention_paid", "attention", "0 or 1", "'attention paid/boosted' 1, 'attention organic' 0"),
    _f("sc_manipulation_ord", "attention", "ordinal", "manipulation screen MOSTLY ORGANIC 0 .. SEVERELY MANIPULATED 3", True),
    _f("sc_attention_suspect", "attention", "0 or 1", "paid or manipulation >= 2 (P16 downgrade flag)", True),
    _f("sc_organic_acceleration", "attention", "0 or 1", "trend ACCELERATION and not suspect"),
    _f("sc_lifecycle_late", "lifecycle", "0 or 1", "snapshot lifecycle DISTRIBUTION, BREAKDOWN, POST_BREAKDOWN 1; earlier stages 0", True),
    _f("sc_lifecycle_conf_ord", "lifecycle", "ordinal", "'lifecycle X (confidence Y)': LOW 0, MODERATE 1, HIGH 2"),
    _f("sc_channels_n", "channels", "count", "token row website, twitter, telegram http links that are not search pages", True),
    _f("sc_channel_search_url", "channels", "0 or 1", "a channel field is a search page"),
    _f("sc_narrative_tagged", "narrative", "0 or 1", "token row of the decision's export carries a narrative id"),
    _f("sc_narrative_lifecycle_ord", "narrative", "ordinal", "newest narrative snapshot at or before T: DEAD 0 .. MANIA 5"),
    _f("sc_narrative_age_h", "narrative", "h", "T - narratives.first_seen_at"),
    _f("sc_narrative_catalyst_kw_7d", "narrative", "count", "narrative snapshot catalyst_events_7d (keyword matches, not identity)"),
    _f("sc_narrative_mcap_chg_24h_pct", "narrative", "percent", "narrative snapshot mcap_chg_24h_pct"),
    _f("sc_narrative_snapshot_age_h", "narrative", "h", "T - narrative snapshot observed_at"),
    _f("sc_d_attention_trend", "change", "ordinal diff", "trend now - trend at the previous decision", True),
    _f("sc_attention_reversal", "change", "0 or 1", "previous ACCELERATION or STABILITY and now EXHAUSTION", True),
    _f("sc_d_narrative_strength", "change", "diff", "narrative strength now - at the previous decision"),
]
SC = [d["name"] for d in DEFINITIONS]
S1_REQ = ("sc_attention_trend_ord", "sc_attention_suspect")
S1_OPT = ("sc_narrative_strength", "sc_manipulation_ord", "sc_lifecycle_late", "sc_channels_n")
S3_OPT = ("sc_d_attention_trend", "sc_attention_reversal")


def _spec(kind: str, columns: Sequence[str], rows: Sequence[str]) -> dict:
    return {"kind": kind, "columns": list(columns), "rows": list(rows)}


SPECS = {
    "R2_SC_RULE": _spec("rule", S1_REQ, ()),
    "S1_SC_LOGIT": _spec("logit", S1_REQ + S1_OPT, S1_REQ),
    "S2_SC_LOGIT_B2": _spec("logit", B.B2_COLUMNS + S1_REQ + S1_OPT, B.B2_REQUIRED + S1_REQ),
    "S3_SC_LOGIT_TREND": _spec("logit", B.B2_COLUMNS + S1_REQ + S1_OPT + S3_OPT, B.B2_REQUIRED + S1_REQ),
    "G1_SC_STUMPS_B2": _spec("stumps", B.B2_COLUMNS + S1_REQ + S1_OPT, B.B2_REQUIRED + S1_REQ),
    "A2_SC_B2_TC": _spec("logit", B.B2_COLUMNS, B.B2_REQUIRED + S1_REQ),
}
MODEL_IDS = ("R2_SC_RULE", "S1_SC_LOGIT", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND", "G1_SC_STUMPS_B2", "A2_SC_B2_TC")
PRIMARY = "S2_SC_LOGIT_B2"
RULE = "R2_SC_RULE"
ALARM = "R3_SC_AMPLIFICATION_ALARM"
ALLOWED = frozenset(SC) | B.ALLOWED_COLUMNS         # every column a Phase 10 model may read (NC2-SC allowlist)


class SocialCatError(ValueError):
    pass


class ContextRefused(SocialCatError):
    """Narrative tables that are not the decision's own export (P04, CX-10)."""


class ModelTrainedAfterDecision(SocialCatError):
    pass


def feature_set_definitions() -> dict:
    return {"name": FEATURE_SET_NAME, "version": SOCIALCAT_VERSION, "definitions": DEFINITIONS, "reasons": REASONS,
            "lines": {k: [b, p.pattern] for k, (b, p) in LINES.items()},
            "maps": {"trend": TREND, "manip": MANIP, "late": sorted(LATE_STAGES), "early": sorted(EARLY_STAGES), "conf": CONF,
                     "narrative_lifecycle": NARR_LC, "channels": list(CHANNEL_FIELDS), "search": SEARCH_RX.pattern},
            "base_feature_set_sha": F.feature_set_sha(), "significant_digits": SIG}


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


def _json(x: Any) -> Any:
    if isinstance(x, (dict, list)):
        return x
    if x is None:
        return None
    try:
        return json.loads(x)
    except (TypeError, ValueError):
        return "UNPARSEABLE"


def _set(v: Any) -> bool:
    return isinstance(v, str) and v.strip() not in ("", "None", "null", "NULL")


# ---------------------------------------------------------------- one decision row
def parse_row(row: dict) -> dict:
    """The lab's attention, manipulation and lifecycle readings of one thesis row: {key: (groups or None, reason or None)} plus the
    snapshot. Pure (the trace verifier re-implements it independently)."""
    out: dict[str, tuple] = {}
    snap = _json(row.get("snapshot_json"))
    out["snapshot"] = (snap if isinstance(snap, dict) else None, None if isinstance(snap, dict) else
                       ("ABSENT_IN_SNAPSHOT" if snap is None else "UNPARSEABLE"))
    bd = _json(row.get("score_breakdown_json"))
    lines: dict[str, list[str]] | None = None
    if isinstance(bd, dict):
        lines = {b: [str(s) for s in v["rationale"]] for b, v in bd.items() if isinstance(v, dict) and isinstance(v.get("rationale"), list)}

    def find(key: str, unknown_key: str | None) -> tuple[Any, str | None]:
        if lines is None:
            return None, "ABSENT_IN_SNAPSHOT" if bd is None else "UNPARSEABLE"
        bucket, pat = LINES[key]
        if bucket not in lines:
            return None, "ABSENT_IN_SNAPSHOT"
        for s in lines[bucket]:
            m = pat.match(s)
            if m:
                return m.groups(), None
        if unknown_key is not None and any(LINES[unknown_key][1].match(s) for s in lines[bucket]):
            return None, "NOT_OBSERVED_BY_LAB"
        if any(s.startswith("UNKNOWN") for s in lines[bucket]) and unknown_key is None:
            return None, "NOT_OBSERVED_BY_LAB"
        return None, "UNPARSEABLE"

    out["trend"] = find("trend", "trend_unknown")
    out["strength"] = find("strength", "strength_unknown")
    out["organic"] = find("organic", "organic_unknown")
    out["manip"] = find("manip", None)
    out["lifecycle"] = find("lifecycle", None)
    return out


def channel_values(token: dict | None) -> dict[str, tuple]:
    if token is None:
        return {n: (None, "NO_TOKEN_ROW") for n in ("sc_channels_n", "sc_channel_search_url", "sc_narrative_tagged")}
    n = srch = 0
    for k in CHANNEL_FIELDS:
        v = token.get(k)
        if not _set(v):
            continue
        if SEARCH_RX.search(v):
            srch = 1
        elif v.strip().lower().startswith(("http://", "https://")):
            n += 1
    return {"sc_channels_n": (float(n), None), "sc_channel_search_url": (float(srch), None),
            "sc_narrative_tagged": (1.0 if _set(token.get("narrative_id")) else 0.0, None)}


def current_values(p: dict) -> dict[str, tuple]:
    """Current-state socialcat-1 values (value, reason) of the thesis row's readings."""
    v: dict[str, tuple] = {}
    snap, ws = p["snapshot"]
    tr, wt = p["trend"]
    if tr is not None:
        word = tr[0]
        if word not in TREND:
            v["sc_attention_trend_ord"] = (None, "UNPARSEABLE")
        elif snap is not None and snap.get("attention") is not None and str(snap.get("attention")).upper() != word:
            v["sc_attention_trend_ord"] = (None, "INCONSISTENT_RECORD")
        else:
            v["sc_attention_trend_ord"] = (TREND[word], None)
    else:
        v["sc_attention_trend_ord"] = (None, wt)
    st, wst = p["strength"]
    sv = _numtxt(st[0]) if st else None
    v["sc_narrative_strength"] = (sv, None) if sv is not None else (None, wst or "UNPARSEABLE")
    og, wo = p["organic"]
    v["sc_attention_paid"] = ((1.0 if og[0] == "paid/boosted" else 0.0), None) if og else (None, wo)
    mp, wm = p["manip"]
    if mp is not None:
        lab = mp[0].strip().upper()
        v["sc_manipulation_ord"] = (MANIP[lab], None) if lab in MANIP else (None, "UNPARSEABLE")
    else:
        v["sc_manipulation_ord"] = (None, wm)
    paid, mo = v["sc_attention_paid"][0], v["sc_manipulation_ord"][0]
    if (paid == 1.0) or (mo is not None and mo >= 2.0):
        v["sc_attention_suspect"] = (1.0, None)
    elif paid == 0.0 and mo is not None:
        v["sc_attention_suspect"] = (0.0, None)
    else:
        v["sc_attention_suspect"] = (None, v["sc_attention_paid"][1] or v["sc_manipulation_ord"][1] or "NOT_OBSERVED_BY_LAB")
    t_, s_ = v["sc_attention_trend_ord"][0], v["sc_attention_suspect"][0]
    if t_ is None:
        v["sc_organic_acceleration"] = (None, v["sc_attention_trend_ord"][1])
    elif t_ != 2.0 or s_ == 1.0:
        v["sc_organic_acceleration"] = (0.0, None)
    elif s_ == 0.0:
        v["sc_organic_acceleration"] = (1.0, None)
    else:
        v["sc_organic_acceleration"] = (None, v["sc_attention_suspect"][1])
    if snap is None:
        v["sc_lifecycle_late"] = (None, ws)
    else:
        stage = snap.get("lifecycle")
        if stage is None:
            v["sc_lifecycle_late"] = (None, "ABSENT_IN_SNAPSHOT")
        elif str(stage) in LATE_STAGES:
            v["sc_lifecycle_late"] = (1.0, None)
        elif str(stage) in EARLY_STAGES:
            v["sc_lifecycle_late"] = (0.0, None)
        elif str(stage) == "UNKNOWN":
            v["sc_lifecycle_late"] = (None, "NOT_OBSERVED_BY_LAB")
        else:
            v["sc_lifecycle_late"] = (None, "UNPARSEABLE")
    lc, wl = p["lifecycle"]
    v["sc_lifecycle_conf_ord"] = (CONF[lc[1]], None) if lc and lc[1] in CONF else (None, wl or "UNPARSEABLE")
    return v


# ---------------------------------------------------------------- narrative context of the decision's own export
def narrative_values(context: dict | None, dec: dict, token: dict | None) -> dict[str, tuple]:
    """Narrative features from the `narratives` and `narrative_snapshots` tables of the export commit that is the decision.
    context: {"commit", "commit_time", "blob", "narratives": [...], "narrative_snapshots": [...]} as read from git by the caller.
    Raises ContextRefused when the tables are not that export's (P04: a later export is not what the lab had at T)."""
    names = ("sc_narrative_lifecycle_ord", "sc_narrative_age_h", "sc_narrative_catalyst_kw_7d", "sc_narrative_mcap_chg_24h_pct",
             "sc_narrative_snapshot_age_h")
    Td = float(dec["decision_time"])
    if context is None:
        return {n: (None, "CONTEXT_NOT_SUPPLIED") for n in names}
    if (context.get("commit") != dec.get("export_commit") or float(context.get("commit_time")) != Td
            or (dec.get("export_blob") and context.get("blob") != dec.get("export_blob"))):
        raise ContextRefused(f"narrative tables of commit {str(context.get('commit'))[:10]} are not the decision's export "
                             f"{str(dec.get('export_commit'))[:10]} at T (P04, CX-10)")
    if token is None:
        return {n: (None, "NO_TOKEN_ROW") for n in names}
    nid = token.get("narrative_id")
    if not _set(nid):
        return {n: (None, "NO_NARRATIVE_TAG") for n in names}
    rows = [r for r in context.get("narrative_snapshots") or [] if r.get("narrative_id") == nid]
    for r in rows:
        if not S._num(_numtxt(str(r.get("observed_at")))):
            raise SocialCatError("narrative snapshot without a numeric observed_at")
    later = [r for r in rows if float(r["observed_at"]) > Td]
    if later:
        return {n: (None, "INCONSISTENT_TIME") for n in names}
    out: dict[str, tuple] = {}
    meta = next((r for r in context.get("narratives") or [] if r.get("narrative_id") == nid), None)
    fs = _numtxt(str(meta.get("first_seen_at"))) if meta else None
    if fs is None:
        out["sc_narrative_age_h"] = (None, "ABSENT_IN_SNAPSHOT")
    elif fs > Td:
        out["sc_narrative_age_h"] = (None, "INCONSISTENT_TIME")
    else:
        out["sc_narrative_age_h"] = ((Td - fs) / 3600.0, None)
    if not rows:
        for n in names:
            out.setdefault(n, (None, "NO_NARRATIVE_SNAPSHOT"))
        return out
    s = max(rows, key=lambda r: (float(r["observed_at"]), int(_numtxt(str(r.get("id"))) or 0)))
    lc = str(s.get("lifecycle"))
    out["sc_narrative_lifecycle_ord"] = (NARR_LC[lc], None) if lc in NARR_LC else (None, "NOT_OBSERVED_BY_LAB" if lc == "UNKNOWN" else "UNPARSEABLE")
    kw = _numtxt(str(s.get("catalyst_events_7d")))
    out["sc_narrative_catalyst_kw_7d"] = (kw, None) if kw is not None else (None, "NOT_OBSERVED_BY_LAB")
    ch = _numtxt(str(s.get("mcap_chg_24h_pct")))
    out["sc_narrative_mcap_chg_24h_pct"] = (ch, None) if ch is not None else (None, "NOT_OBSERVED_BY_LAB")
    out["sc_narrative_snapshot_age_h"] = ((Td - float(s["observed_at"])) / 3600.0, None)
    return out


# ---------------------------------------------------------------- the as-of snapshot
def _value(v: float | None, reason: str | None, avail: float | None, inputs: Sequence[str]) -> dict:
    if (v is None) == (reason is None):
        raise SocialCatError("exactly one of value or missing reason")
    if v is not None and not math.isfinite(v):
        raise SocialCatError(f"value {v!r} is not finite (P38)")
    if reason is not None and reason not in REASONS:
        raise SocialCatError(f"unknown missing reason {reason!r}")
    return {"value": _r(v) if v is not None else None, "missing_reason": reason, "missing_basis": REASONS[reason] if reason else None,
            "available_at": float(avail) if (v is not None and avail is not None) else None, "evidence": EVIDENCE,
            "inputs": sorted(inputs) if v is not None else []}


def lab_event_classes(vals: dict) -> list[str]:
    """Event classes derivable from the lab's own readings at T (never a verified catalyst)."""
    out = []
    if vals["sc_organic_acceleration"]["value"] == 1.0:
        out.append("HIGH_ATTENTION_PROXY")
    if vals["sc_attention_reversal"]["value"] == 1.0:
        out.append("NARRATIVE_REVERSAL")
    return out


def socialcat_as_of(con: sqlite3.Connection, chain: str, mint: str, decision_time: float, *, decision_key: str | None = None,
                    context: dict | None = None) -> dict:
    """socialcat-1 of one exact (chain, mint) at T from the store's decision rows visible at T (audited) and the narrative tables
    of the decision's own export. Deterministic."""
    Tq = float(decision_time)
    view = F.AsOfView(con, Tq, "provider")
    decs = view.decisions_of(chain, mint)
    dec = None
    if decision_key is not None:
        dec = next((d for d in decs if d["decision_key"] == decision_key), None)
        if dec is None:
            raise SocialCatError(f"decision {decision_key[:12]} is not visible at T for this chain and mint (P01, P43)")
        if float(dec["decision_time"]) != Tq:
            raise SocialCatError("decision time differs from T")
    elif decs:
        dec = decs[-1]
    vals: dict[str, dict] = {}
    if dec is None:
        vals = {n: _value(None, "NOT_IN_UNIVERSE", None, ()) for n in SC}
    elif chain != "solana":
        vals = {n: _value(None, "OUT_OF_SCOPE_CHAIN", None, ()) for n in SC}
    else:
        row = json.loads(dec["row_json"])
        tok = json.loads(dec["token_json"]) if dec["token_json"] else None
        p = parse_row(row)
        Td = float(dec["decision_time"])
        snap = p["snapshot"][0] or {}
        t_snap = snap.get("t")
        if S._num(t_snap) and float(t_snap) > Td:
            vals = {n: _value(None, "INCONSISTENT_TIME", None, ()) for n in SC}
        else:
            ins = ["decision:" + dec["decision_key"]]
            cur = current_values(p)
            cur.update(channel_values(tok))
            nv = narrative_values(context, dec, tok)
            for n, (v, why) in {**cur, **nv}.items():
                vals[n] = _value(v, why, Td, ins + (["export:" + str(dec.get("export_commit"))] if n in nv and v is not None else []))
            prior = [d for d in decs if float(d["decision_time"]) < Td]
            names = ("sc_d_attention_trend", "sc_attention_reversal", "sc_d_narrative_strength")
            if not prior:
                for n in names:
                    vals[n] = _value(None, "NO_PRIOR_DECISION", None, ())
            else:
                pd = prior[-1]
                pp = parse_row(json.loads(pd["row_json"]))
                psnap = pp["snapshot"][0] or {}
                pc = current_values(pp)
                if S._num(psnap.get("t")) and float(psnap["t"]) > float(pd["decision_time"]):
                    pc = {k: (None, "INCONSISTENT_TIME") for k in pc}
                pins = ins + ["decision:" + pd["decision_key"]]
                a, b = cur["sc_attention_trend_ord"][0], pc["sc_attention_trend_ord"][0]
                if a is None or b is None:
                    why = cur["sc_attention_trend_ord"][1] or pc["sc_attention_trend_ord"][1]
                    vals["sc_d_attention_trend"] = _value(None, why, None, ())
                    vals["sc_attention_reversal"] = _value(None, why, None, ())
                else:
                    vals["sc_d_attention_trend"] = _value(a - b, None, Td, pins)
                    vals["sc_attention_reversal"] = _value(float(b >= 1.0 and a == 0.0), None, Td, pins)
                a, b = cur["sc_narrative_strength"][0], pc["sc_narrative_strength"][0]
                vals["sc_d_narrative_strength"] = (_value(a - b, None, Td, pins) if a is not None and b is not None else
                                                   _value(None, cur["sc_narrative_strength"][1] or pc["sc_narrative_strength"][1], None, ()))
    for n in SC:
        if n not in vals:
            raise SocialCatError(f"{n} not computed")
    snapd = {"chain": chain, "mint": mint, "decision_time": Tq, "decision_key": dec["decision_key"] if dec else None,
             "row_sha256": dec["row_sha256"] if dec else None, "export_commit": dec["export_commit"] if dec else None,
             "socialcat_version": SOCIALCAT_VERSION, "feature_set_sha": feature_set_sha(), "values": {n: vals[n] for n in SC},
             "catalyst_state": CATALYST_STATE_REAL, "social_state": SOCIAL_STATE_REAL, "rows_audited": view.audit.records}
    snapd["lab_event_classes"] = lab_event_classes(snapd["values"])
    snapd["socialcat_snapshot_sha"] = S.sha({k: snapd[k] for k in ("chain", "mint", "decision_time", "decision_key", "row_sha256",
                                                                     "socialcat_version", "values", "catalyst_state", "social_state")})
    return snapd


# ---------------------------------------------------------------- examples
@dataclass
class SExample(B.Example):
    sc_reasons: dict = field(default_factory=dict)
    sc_sha: str | None = None
    row_sha256: str | None = None


def attach(examples: Sequence[B.Example], snaps: dict[str, dict]) -> list[SExample]:
    """Phase 07 examples with their socialcat-1 snapshot, joined by decision key with chain, mint and decision time checked (P01)."""
    out = []
    for e in examples:
        s = snaps.get(e.decision_key)
        if s is None:
            raise SocialCatError(f"no socialcat-1 snapshot for decision {e.decision_key[:12]}")
        if s["decision_key"] != e.decision_key or s["chain"] != e.chain or s["mint"] != e.mint or float(s["decision_time"]) != e.decision_time:
            raise B.IdentityJoinError("socialcat-1 snapshot of another decision (P01)")
        x, av = dict(e.x), dict(e.avail)
        for c in SC:
            v = s["values"][c]
            x[c] = v["value"] if v["value"] is not None else float("nan")
            if v["value"] is None:
                av[c] = e.decision_time               # a missing value carries no input
            elif v["available_at"] is None:
                raise SocialCatError(f"{c}: a value without an availability time")
            else:
                av[c] = v["available_at"]
        out.append(SExample(**{**e.__dict__, "x": x, "avail": av},
                            sc_reasons={c: s["values"][c]["missing_reason"] for c in SC if s["values"][c]["value"] is None},
                            sc_sha=s["socialcat_snapshot_sha"], row_sha256=s["row_sha256"]))
    return out


def check_asof(examples: Sequence[B.Example], columns: Sequence[str], *, as_of: float | None, with_labels: bool) -> None:
    """Every column in the Phase 10 allowlist and available at or before its decision; decisions at or before as_of; labels
    matured by as_of when given (features.validate_rows; P36, P05, P43)."""
    bad = [c for c in columns if c not in ALLOWED]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 10 allowlist (NC2-SC: only declared as-of inputs reach a fit)")
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
        raise F.AsOfError(f"columns {bad} are not in the Phase 10 allowlist")
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
            "socialcat_version": SOCIALCAT_VERSION, "base_feature_set_sha": F.feature_set_sha(), "feature_version": F.FEATURE_VERSION,
            "labels_version": L.LABELS_VERSION, "store_schema": S.SCHEMA_VERSION, "label_mode": "provider",
            "n_train": int(len(train)), "k_train": int(y.sum()) if len(train) else 0, "n_used": int(n_used), "k_used": int(k_used),
            "label_set_sha": B.sha(sorted([e.label_key or e.decision_key, e.y] for e in train)),
            "data_snapshot_sha": B.sha(sorted([e.decision_key, e.snapshot_sha256, getattr(e, "sc_sha", None)] for e in train)),
            "status": PROVISIONAL, "revision_check_claimed": False, "publishable": False, "promotion": "MODEL_NOT_PROMOTED",
            "evidence_class": B.evidence_class(is_fixture), "catalyst_state": CATALYST_STATE_REAL, "social_state": SOCIAL_STATE_REAL,
            "llm_used": False,
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
        raise SocialCatError("card trained under another registry fingerprint")
    if card.get("feature_set_sha") != feature_set_sha() or card.get("socialcat_version") != SOCIALCAT_VERSION:
        raise F.FeatureVersionError("FEATURE_SCHEMA_MISMATCH: socialcat-1 definitions differ from the card's (P46)")
    F.require_compatible(card["feature_version"], card["base_feature_set_sha"])
    return card


def dumps(card: dict) -> str:
    return B.dumps(card)


def loads(text: str) -> dict:
    return verify_card(json.loads(text))


def _cell(e: B.Example) -> str:
    a, b = B._num(e.x.get(S1_REQ[0])), B._num(e.x.get(S1_REQ[1]))
    if not (math.isfinite(a) and math.isfinite(b)):
        return "MISSING"
    return f"T{int(a)}S{int(b)}"


def fit(model_id: str, target: str, train: Sequence[B.Example], cutoff: float, *, y_override: np.ndarray | None = None,
        is_fixture: bool = False, meta: dict | None = None, card_kind: str | None = None) -> dict:
    """One Phase 10 model on one training set (rows decided before and matured by the cutoff, checked)."""
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
    if spec["kind"] == "logit":
        m = K.Logistic(C=C_L2).fit(prep.transform(X), y)
        body = {"spec": spec, "prep": prep.to_dict(), "logistic": m.to_dict()}
    else:
        m = T.Stumps().fit(prep.transform(X), y)
        body = {"spec": spec, "prep": prep.to_dict(), "stumps": m.to_dict()}
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
            Z = K.Prep.from_dict(body["prep"]).transform(matrix([examples[i] for i in ok], spec["columns"]))
            if spec["kind"] == "logit":
                p[ok] = K.Logistic.from_dict(body["logistic"]).predict_proba1(Z)
            else:
                p[ok] = T.Stumps.from_dict(body["stumps"]).predict_proba1(Z)
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


def amplification_alarm(e: B.Example) -> bool | None:
    """R3: suspect (paid or manufactured) attention as an alarm, not a probability. None when the flag is missing."""
    v = B._num(e.x.get("sc_attention_suspect"))
    return None if not math.isfinite(v) else bool(v == 1.0)


def campaign(e: B.Example) -> str:
    """Event-level group for the campaign bootstrap: the token's narrative tag at the decision, else the mint."""
    return f"narrative:{e.narrative}" if e.narrative else f"mint:{e.mint}"


# ---------------------------------------------------------------- the frozen walk-forward, same folds as Phase 07
def walk_forward(target: str, development: Sequence[SExample], train_at: Callable[[float], Sequence[SExample]], *,
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
                cnc = fit(PRIMARY, target, train, cut, y_override=yy, is_fixture=is_fixture, meta={"nc1_seed": s}, card_kind="NC1SC")
                nc1[s] = predict(cnc, test)[0]
        mints_tr = {e.mint for e in train}
        creators_tr = {e.creator for e in train if e.creator}
        narr_tr = {e.narrative for e in train if e.narrative}
        for j, e in enumerate(test):
            row = {"fold": k, "cutoff": cut, "example": e, "y": e.y, "new_mint": e.mint not in mints_tr,
                   "new_creator": (e.creator not in creators_tr) if e.creator else None,
                   "new_narrative": (e.narrative not in narr_tr) if e.narrative else None, "R3_alarm": amplification_alarm(e),
                   "campaign": campaign(e)}
            for m in preds:
                row[m] = float(preds[m][0][j])
                row[m + "_why"] = preds[m][1][j]
            for s, v in nc1.items():
                row[f"NC1SC_{s}"] = float(v[j])
            oos.append(row)
        out_folds.append({"fold": k, "cutoff": cut, "cutoff_utc": B._iso(cut), "n_train": len(train),
                          "k_train": int(B.labels_of(train).sum()), "n_test": len(test), "k_test": int(sum(e.y for e in test)),
                          "used": {m: [cards[m]["n_used"], cards[m]["k_used"], cards[m]["body"].get("abstain")] for m in models},
                          "test_day": B._iso(cut)[:10], "cards": cards,
                          "split_fingerprint": B.sha([target, cut, want, sorted(e.decision_key for e in test)])})
    return {"target": target, "folds": out_folds, "oos": oos, "audit": audit, "nc1_seeds": seeds,
            "evidence_class": B.evidence_class(is_fixture), "split_fingerprint": B.sha([f["split_fingerprint"] for f in out_folds]),
            "status": "OK" if out_folds else "INSUFFICIENT_HISTORY"}


def alarm_counts(rows: Sequence[dict], model: str, *, touch: dict[str, float | None]) -> dict:
    """Alarms of `model` (R3: the suspect-attention flag; otherwise a number above the fold's B0) on out-of-sample rows: hits,
    misses, false alarms, correct rejections and each hit's lead time from the decision to the label's first touch. An alarm is
    raised at the decision, before the label window opens (a negative lead time raises)."""
    out = {"model": model, "scored": 0, "hits": 0, "misses": 0, "false_alarms": 0, "correct_rejections": 0, "lead_times_h": []}
    for r in rows:
        e = r["example"]
        if model == ALARM:
            a = r.get("R3_alarm")
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
                    raise SocialCatError(f"alarm after the event for {e.decision_key[:12]}: not an early warning")
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


# ================================================================ catalyst classifier (TEST_ONLY: no catalyst row is exported)
EVENT_TYPES = ("LISTING", "PARTNERSHIP", "RUMOR", "CODE_RELEASE", "TOKEN_MECHANIC_CHANGE", "BIG_TRADER_CLAIM", "HIGH_SOCIAL_ATTENTION",
               "NARRATIVE_REVERSAL", "OTHER")
TYPE_FROM_CLAIM = {"LISTING": "LISTING", "PARTNERSHIP": "PARTNERSHIP", "LAUNCH": "CODE_RELEASE", "CALL": "BIG_TRADER_CLAIM",
                   "WALLET_CLAIM": "BIG_TRADER_CLAIM"}
TYPE_FROM_CATEGORY = {"ACCESS": "LISTING", "ROTATION": "NARRATIVE_REVERSAL"}
INDEPENDENT_ROLES = frozenset({"ORIGINAL", "INDEPENDENT"})
STRONG_LINK_TYPES = frozenset({"NAMED_IN_SOURCE", "OFFICIAL"})     # match.py: OFFICIAL needs the event's own source to state the mint
WITHDRAW_KINDS = frozenset({"DENIED", "CANCELLED", "DELETED_SOURCE"})
CATALYST_STATES = ("VERIFIED", "UNVERIFIED_EVENT", "IDENTITY_UNVERIFIED", "NOT_AVAILABLE_AT_DECISION")


def _body_hash(it: dict) -> str | None:
    b = it.get("body")
    return S.sha(" ".join(str(b).split()).lower()) if _set(b) else None


def event_type(event: dict, *, claim_type: str | None, source_groups: Iterable[str], evidence_as_of: str | None,
               attention_only: bool) -> tuple[str, str]:
    """The fixed type of a catalyst from structured fields only (no headline taxonomy chosen after outcomes)."""
    if evidence_as_of == "RUMOR":
        return "RUMOR", "evidence_status RUMOR as of T"
    groups = set(source_groups)
    if claim_type in TYPE_FROM_CLAIM:
        t = TYPE_FROM_CLAIM[claim_type]
        if t == "BIG_TRADER_CLAIM" and not (groups & {"trader", "social"}):
            return "OTHER", f"claim {claim_type} without a trader or social source"
        return t, f"claim_type {claim_type}"
    cat = str(event.get("category") or "")
    if cat in TYPE_FROM_CATEGORY:
        return TYPE_FROM_CATEGORY[cat], f"category {cat}"
    if "token_mechanics" in groups:
        return "TOKEN_MECHANIC_CHANGE", "token-mechanics source"
    if attention_only:
        return "HIGH_SOCIAL_ATTENTION", "attention samples only"
    return "OTHER", "no structured type"


def evidence_as_of(event: dict, revisions: Sequence[dict], T: float) -> str:
    """Evidence status at T from the revision log; the mutable event row counts only when it was last updated by T."""
    ev = [r for r in revisions if r.get("field") == "evidence_status" and float(r["revised_at"]) <= T]
    if ev:
        return str(max(ev, key=lambda r: (float(r["revised_at"]), r.get("id") or 0))["new_value"])
    if event.get("updated_at") is not None and float(event["updated_at"]) <= T:
        return str(event.get("evidence_status"))
    return "UNKNOWN_AS_OF"


def confirmed_since(event: dict, revisions: Sequence[dict], T: float) -> float | None:
    """When the evidence status that holds at T became CONFIRMED: the first CONFIRMED revision after the last revision at or before
    T that set anything else; the mutable row's `updated_at` when no evidence revision exists and the row was last updated by T
    (conservative: the row may have been CONFIRMED earlier); None when the status at T is not CONFIRMED (repair pass 2, CX-10b-A)."""
    ev = sorted((r for r in revisions if r.get("field") == "evidence_status" and float(r["revised_at"]) <= T),
                key=lambda r: (float(r["revised_at"]), r.get("id") or 0))
    if ev:
        since = None
        for r in ev:
            if str(r.get("new_value")) == "CONFIRMED":
                since = float(r["revised_at"]) if since is None else since
            else:
                since = None
        return since
    if event.get("updated_at") is not None and float(event["updated_at"]) <= T and str(event.get("evidence_status")) == "CONFIRMED":
        return float(event["updated_at"])
    return None


def classify_catalyst(event: dict, items: Sequence[dict], roles: dict, revisions: Sequence[dict], links: Sequence[dict], *,
                      chain: str, mint: str, decision_time: float, page_facts: Sequence[dict] = (), claim_type: str | None = None,
                      source_groups: dict | None = None, official_sources: Iterable[str] = (), attention_only: bool = False) -> dict:
    """One catalyst event for one exact (chain, mint) at T. items: catalyst_items rows; roles: item id -> role from
    catalyst_event_sources; revisions: catalyst_event_revisions rows; links: catalyst_token_links rows of the event; page_facts:
    crawled pages {fetched_at, contracts}; source_groups: source_id -> group. Never returns a probability for anything but a
    VERIFIED event, and even then only `probability_allowed` (a calibrated model is a later phase).

    `available_at` of a VERIFIED event is the latest of: the first visible item's sighting, the strong links' `linked_at`, the
    sighting of the first independent item that names the mint, the time the evidence became CONFIRMED (`confirmed_since`) and
    the sighting that completed the source rule (the first official item that names the mint, or the second independent item).
    An item without a role in catalyst_event_sources is not independent (repair pass 2, m5)."""
    Tq = float(decision_time)
    audit = RC.Audit()
    source_groups = source_groups or {}
    vis = audit.check("catalyst_item", [dict(i, _avail=float(i["first_seen_at"])) for i in items if float(i["first_seen_at"]) <= Tq], Tq)
    revs = audit.check("catalyst_revision", [dict(r, _avail=float(r["revised_at"])) for r in revisions if float(r["revised_at"]) <= Tq], Tq)
    pages = audit.check("crawled_page", [dict(p, _avail=float(p["fetched_at"])) for p in page_facts if float(p["fetched_at"]) <= Tq], Tq)
    lnks = audit.check("token_link", [dict(k, _avail=float(k["linked_at"])) for k in links if float(k["linked_at"]) <= Tq], Tq)
    reasons: list[str] = []
    base = {"chain": chain, "mint": mint, "decision_time": Tq, "event_key": event.get("event_key"), "probability_allowed": False,
            "probability": None, "evidence_class": "TEST_ONLY", "rows_audited": audit.records}
    if not vis:
        return {**base, "state": "NOT_AVAILABLE_AT_DECISION", "event_type": None, "first_seen_at": None, "available_at": None,
                "independent_sources": 0, "reasons": ["NO_SOURCE_ITEM_SEEN_BY_T (P45)"]}
    first_seen = min(float(i["first_seen_at"]) for i in vis)
    live = list(vis)
    indep, seen_urls, seen_hash = [], set(), set()
    no_role = 0
    for i in sorted(live, key=lambda i: (float(i["first_seen_at"]), str(i.get("id")))):
        role = roles.get(i.get("id"))
        if role is None:
            no_role += 1
            continue
        if role not in INDEPENDENT_ROLES:
            continue
        u, h = i.get("url"), _body_hash(i)
        if (u and u in seen_urls) or (h and h in seen_hash):
            continue
        seen_urls.add(u)
        seen_hash.add(h)
        indep.append(i)
    ev_status = evidence_as_of(event, revisions, Tq)
    withdrawn = sorted({r["kind"] for r in revs if r.get("kind") in WITHDRAW_KINDS or (r.get("field") == "status" and r.get("new_value") in ("DENIED", "CANCELLED"))})
    if withdrawn:
        reasons.append("WITHDRAWN_BY_T:" + ",".join(withdrawn))
    if no_role:
        reasons.append(f"ITEMS_WITHOUT_ROLE_NOT_INDEPENDENT:{no_role}")
    # identity: exact chain and mint, NAMED_IN_SOURCE / STRONG, mint present in a visible original or independent item
    ident = "NO_LINK"
    mine = [k for k in lnks if k.get("mint") == mint and (k.get("chain") or "solana") == chain]
    strong = [k for k in mine if k.get("link_type") in STRONG_LINK_TYPES and k.get("link_strength") == "STRONG"]
    names = lambda i: mint in str(i.get("url") or "") or mint in str(i.get("body") or "")
    naming = [i for i in indep if names(i)]
    in_source = bool(naming)
    on_page = any(mint in (p.get("contracts") or []) for p in pages)
    if strong and in_source:
        ident = "EXACT_MINT_IN_SOURCE"
    elif strong and on_page:
        ident = "PAGE_NAMED_ONLY"
    elif strong:
        ident = "STRONG_LINK_WITHOUT_VISIBLE_SOURCE"
    elif mine:
        ident = "TICKER_OR_NAME_ONLY"
    groups = [source_groups.get(i.get("source_id"), "") for i in live]
    etype, basis = event_type(event, claim_type=claim_type, source_groups=groups, evidence_as_of=ev_status, attention_only=attention_only)
    off_set = set(official_sources)
    official_items = [i for i in naming if i.get("source_id") in off_set]      # an official item must itself name the mint (m5)
    official = bool(official_items)
    if official_items and len(indep) >= 2:
        rule_at = min(float(official_items[0]["first_seen_at"]), float(indep[1]["first_seen_at"]))
    elif official_items:
        rule_at = float(official_items[0]["first_seen_at"])
    elif len(indep) >= 2:
        rule_at = float(indep[1]["first_seen_at"])
    else:
        rule_at = None
    conf_at = confirmed_since(event, revisions, Tq)
    parts = [first_seen] + [float(k["linked_at"]) for k in strong] + ([float(naming[0]["first_seen_at"])] if naming else [])
    avail = max(parts + [conf_at, rule_at]) if (strong and naming and conf_at is not None and rule_at is not None) else None
    if ident != "EXACT_MINT_IN_SOURCE":
        state = "IDENTITY_UNVERIFIED"
        reasons.append(ident)
    elif withdrawn or ev_status == "RUMOR":
        state = "UNVERIFIED_EVENT"
        if ev_status == "RUMOR":
            reasons.append("RUMOR_AS_OF_T (P17)")
    elif ev_status != "CONFIRMED":
        state = "UNVERIFIED_EVENT"
        reasons.append(f"EVIDENCE_{ev_status}_AS_OF_T")
    elif not (official or len(indep) >= 2):
        state = "UNVERIFIED_EVENT"
        reasons.append("SINGLE_NON_OFFICIAL_SOURCE")
    else:
        state = "VERIFIED"
        if avail is None or avail > Tq:
            raise SocialCatError("a VERIFIED catalyst needs an availability at or before T")
    return {**base, "state": state, "event_type": etype, "type_basis": basis, "first_seen_at": first_seen,
            "available_at": avail if state == "VERIFIED" else None, "confirmed_since": conf_at, "source_rule_met_at": rule_at,
            "independent_sources": len(indep), "items_without_role": no_role, "evidence_as_of": ev_status,
            "identity": ident, "official_source": official, "probability_allowed": state == "VERIFIED", "reasons": reasons}


# ================================================================ social evidence adapter (TEST_ONLY: no social row exists here)
SOCIAL_TABLES = ("social_accounts", "social_items", "social_observations", "social_item_versions", "social_token_resolutions",
                 "social_claims", "social_claim_extractions", "social_trader_accounts", "social_token_refs",
                 "social_registry_entities", "social_registry_reviews")
OK_RETRIEVAL = frozenset({"OK", "PARTIAL"})
GONE_RETRIEVAL = frozenset({"DELETED", "NOT_FOUND"})
BOT_KINDS = frozenset({"BOT"})
UNKNOWN_AS_OF = "UNKNOWN_AS_OF"


def account_as_of(a: dict, T: float, *, reviews: Sequence[dict] = (), accounts_read_at: float | None = None) -> dict:
    """The kind and identity status of a social account as known at T (repair pass 2, CX-10b-B). `social_accounts` is updated in
    place (`registry.set_account_status` overwrites `identity_status` and `identity_checked_at`; `account_kind` has no time at all).
    With `accounts_read_at` at or before T (the accounts table was read by then, a live read), the row as read was known at T.
    Otherwise (a replay): the status counts only when it was recorded by T (its `identity_checked_at` and every ACCOUNT_STATUS
    review that set it at or before T), else it is UNKNOWN_AS_OF; a kind other than UNKNOWN has no time and is UNKNOWN_AS_OF."""
    status, kind = a.get("identity_status"), a.get("account_kind") or "UNKNOWN"
    if accounts_read_at is not None and float(accounts_read_at) <= float(T):
        return {"kind": kind, "status": status, "mode": "READ_BY_T"}
    known = [float(a["identity_checked_at"])] if a.get("identity_checked_at") is not None else []
    rec = [float(r["reviewed_at"]) for r in reviews if r.get("to_state") == status]
    st = status if (known and max(known + rec) <= float(T)) else UNKNOWN_AS_OF
    return {"kind": kind if kind == "UNKNOWN" else UNKNOWN_AS_OF, "status": st, "mode": "REPLAY"}


def connect_social_ro(path: str | Path) -> sqlite3.Connection:
    """Read-only connection to a social store. Refuses the tracked lab database and the predictive stores (they are not social
    stores and must never be opened through this path)."""
    p = Path(path).resolve()
    repo = Path(__file__).resolve().parents[2]
    if p == (repo / "data" / "memelab.sqlite").resolve():
        raise SocialCatError("the tracked lab database is not a social store")
    if p.name.startswith("predictive_store") or p.name in ("dev_store.sqlite", "sealed_store.sqlite") or "sealed" in p.parts:
        raise SocialCatError("a predictive store is not a social store")
    if not p.exists():
        raise FileNotFoundError(str(p))
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def read_social(con: sqlite3.Connection) -> dict[str, list[dict]]:
    have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {t: ([dict(r) for r in con.execute(f"SELECT * FROM {t}")] if t in have else []) for t in SOCIAL_TABLES}


def social_as_of(tables: dict[str, list[dict]], chain: str, mint: str, decision_time: float, *,
                 track_rows: Sequence[dict] = (), accounts_read_at: float | None = None) -> dict:
    """Social evidence for one exact (chain, mint) at T. track_rows: {trader_id, called_at, matured_at, hit} from the outcomes
    ledger (only calls before T whose outcome matured by T count). Every row used passes replay_core.Audit at T. Account kinds
    and suspensions count only as known at T (`account_as_of`); an exact-mint item whose account is BOT, PROJECT or SUSPENDED
    in the store but not known to be at T counts as an account of unknown kind and is reported in
    `counts["account_label_unknown_as_of"]` (repair pass 2, CX-10b-B)."""
    Tq = float(decision_time)
    audit = RC.Audit()
    acc = {a["account_id"]: a for a in tables.get("social_accounts") or []}
    ent_acct = {e["entity_id"]: e.get("account_id") for e in tables.get("social_registry_entities") or []
                if e.get("entity_kind") == "SOCIAL_ACCOUNT"}
    reviews_of: dict[str, list[dict]] = {}
    for r in tables.get("social_registry_reviews") or []:
        if r.get("target_type") == "ACCOUNT_STATUS" and ent_acct.get(r.get("target_id")):
            reviews_of.setdefault(ent_acct[r["target_id"]], []).append(r)
    obs_by: dict[str, list[dict]] = {}
    for o in tables.get("social_observations") or []:
        if o.get("ingested_at") is not None and float(o["ingested_at"]) <= Tq:
            obs_by.setdefault(o["item_key"], []).append(o)
    vers_by: dict[str, list[dict]] = {}
    for v in tables.get("social_item_versions") or []:
        vers_by.setdefault(v["item_key"], []).append(v)
    res_by: dict[str, list[dict]] = {}
    ticker_items: set[str] = set()
    for r in tables.get("social_token_resolutions") or []:
        if float(r["resolved_at"]) > Tq:
            continue
        if r.get("mention_kind") == "TICKER":
            ticker_items.add(r.get("item_key"))
            continue
        if r.get("status") == "resolved" and r.get("resolved_chain") == chain and r.get("resolved_contract") == mint:
            res_by.setdefault(r.get("item_key"), []).append(r)
    trader_of: dict[str, str] = {}
    for ta in tables.get("social_trader_accounts") or []:
        if float(ta["linked_at"]) <= Tq:
            trader_of[ta["account_id"]] = ta["trader_id"]
    counts = {"edited_without_original": 0, "deleted_before_t": 0, "bot_or_suspended": 0, "duplicates_collapsed": 0,
              "account_label_unknown_as_of": 0}
    originals: list[dict] = []
    seen_hash: set[str] = set()
    for it in sorted(tables.get("social_items") or [], key=lambda i: (i.get("first_ingested_at") or 0, i["item_key"])):
        k = it["item_key"]
        if k not in res_by:
            continue
        ob = [o for o in obs_by.get(k, [])]
        if not ob:
            continue
        audit.check("social_observation", [dict(o, _avail=float(o["ingested_at"])) for o in ob], Tq)
        audit.check("token_resolution", [dict(r, _avail=float(r["resolved_at"])) for r in res_by[k]], Tq)
        if any(o.get("retrieval_status") in GONE_RETRIEVAL for o in ob):
            counts["deleted_before_t"] += 1
            continue
        ok = sorted([o for o in ob if o.get("retrieval_status") in OK_RETRIEVAL], key=lambda o: (float(o["ingested_at"]), o.get("id") or 0))
        if not ok:
            continue
        vs = [v for v in vers_by.get(k, []) if float(v["first_recorded_at"]) <= Tq]
        if vs:                                          # versions recorded after T do not exist at T (m3: the truncated view)
            orig = [v for v in vs if v.get("version_kind") == "ORIGINAL"]
            if not orig:
                counts["edited_without_original"] += 1
                continue
            chash = orig[0].get("content_hash")
        else:
            chash = ok[0].get("content_hash")
        a = acc.get(it.get("account_id") or ok[0].get("account_id")) or {}
        st = account_as_of(a, Tq, reviews=reviews_of.get(a.get("account_id"), ()), accounts_read_at=accounts_read_at)
        if st["kind"] in BOT_KINDS or st["status"] == "SUSPENDED":
            counts["bot_or_suspended"] += 1
            continue
        if (a.get("account_kind") in BOT_KINDS | {"PROJECT"} and st["kind"] == UNKNOWN_AS_OF) or \
                (a.get("identity_status") == "SUSPENDED" and st["status"] == UNKNOWN_AS_OF):
            counts["account_label_unknown_as_of"] += 1
        if chash and chash in seen_hash:
            counts["duplicates_collapsed"] += 1
            continue
        if chash:
            seen_hash.add(chash)
        aid = a.get("account_id") or it.get("account_id")
        originals.append({"item_key": k, "account_id": aid, "source": trader_of.get(aid, f"account:{aid}"),
                          "trader_id": trader_of.get(aid), "platform": it.get("platform"), "available_at": float(ok[0]["ingested_at"]),
                          "verified": st["status"] == "VERIFIED" and a.get("identity_checked_at") is not None
                          and float(a["identity_checked_at"]) <= Tq, "official": st["kind"] == "PROJECT"})
    exact_keys = {o["item_key"] for o in originals}
    bot_total = counts["bot_or_suspended"]
    n_total = len(originals) + bot_total
    # claims: deterministic extraction only (P26), visible items only
    llm_ids = {x["extraction_id"] for x in tables.get("social_claim_extractions") or [] if x.get("extractor") == "model"}
    llm_items = {x["item_key"] for x in tables.get("social_claim_extractions") or [] if x.get("extractor") == "model"
                 and float(x["extracted_at"]) <= Tq}
    dirs = []
    llm_excluded = 0
    for c in tables.get("social_claims") or []:
        if c.get("item_key") not in exact_keys or float(c["extracted_at"]) > Tq:
            continue
        if c.get("item_key") in llm_items or c.get("extraction_id") in llm_ids:
            llm_excluded += 1
            continue
        if c.get("claim_type") == "CALL" and c.get("direction") in ("LONG", "SHORT", "EXIT"):
            dirs.append(c["direction"])
    sources = {o["source"] for o in originals}
    traders = {o["trader_id"] for o in originals if o["trader_id"]}
    vtraders = {o["trader_id"] for o in originals if o["trader_id"] and o["verified"]}
    lows = []
    for tid in sorted(traders):
        tr = [r for r in track_rows if r["trader_id"] == tid and float(r["called_at"]) < Tq and float(r["matured_at"]) <= Tq]
        if tr:
            lows.append(AC.wilson(sum(int(r["hit"]) for r in tr), len(tr))[0])
    n1 = sum(1 for o in originals if Tq - 3600 < o["available_at"] <= Tq)
    n6 = sum(1 for o in originals if Tq - 7 * 3600 < o["available_at"] <= Tq - 3600)
    by_src: dict[str, int] = {}
    for o in originals:
        by_src[o["source"]] = by_src.get(o["source"], 0) + 1
    refs_official = any(r.get("ref_kind") == "OFFICIAL_LINK" and r.get("chain") == chain and r.get("contract") == mint
                        and float(r["first_seen_at"]) <= Tq for r in tables.get("social_token_refs") or [])
    vals = {
        "sx_mentions_exact": float(len(originals)),
        "sx_ticker_only_mentions": float(len({k for k in ticker_items if k not in res_by})),
        "sx_distinct_sources": float(len(sources)),
        "sx_verified_traders": float(len(vtraders)),
        "sx_track_record_wilson_lo": float(np.mean(lows)) if lows else None,
        "sx_disagreement": (sum(1 for d in dirs if d in ("SHORT", "EXIT")) / len(dirs)) if dirs else None,
        "sx_volume_accel": math.log((n1 + 1.0) / (n6 / 6.0 + 1.0)) if originals else None,
        "sx_concentration": (max(by_src.values()) / len(originals)) if originals else None,
        "sx_novelty_h": ((Tq - min(o["available_at"] for o in originals)) / 3600.0) if originals else None,
        "sx_official_link": float(refs_official or any(o["official"] and o["verified"] for o in originals)),
        "sx_bot_share": (bot_total / n_total) if n_total else None,
        "sx_corroboration_platforms": float(len({o["platform"] for o in originals})),
        "sx_deleted_before_t": float(counts["deleted_before_t"]),
        "sx_llm_claims_excluded": float(llm_excluded),
    }
    for kk, v in vals.items():
        if v is not None and not math.isfinite(v):
            raise SocialCatError(f"{kk} is not finite (P38)")
    return {"chain": chain, "mint": mint, "decision_time": Tq, "values": vals, "counts": counts, "evidence_class": "TEST_ONLY",
            "rows_audited": audit.records, "llm_used": False,
            "account_labels": "READ_BY_T" if (accounts_read_at is not None and float(accounts_read_at) <= Tq) else "REPLAY_KNOWN_AT_T_ONLY",
            "attention_confidence": "LOW" if (vals["sx_bot_share"] or 0) > 0.5 else "NORMAL"}


# ================================================================ proposals (PROPOSED_NOT_FROZEN, TEST_ONLY; no default parameters)
PROPOSAL_STATUS = "PROPOSED_NOT_FROZEN"


def proposed_follow_through_label(candles: Sequence[dict], *, available_at: float, decision_time: float, provider_lag_s: float,
                                  up: float, down: float, horizon_s: float) -> dict:
    """Proposal: a catalyst VERIFIED at the decision (classified as of decision_time), its price path from the first candle that
    starts at or after max(available_at, decision_time) + provider_lag_s (entry rule: never before the decision, and never before
    the catalyst was verified; repair pass 2, CX-10b-A): `up` before `down` within horizon_s; a candle touching both is negative; a
    path shorter than the horizon is PENDING or CENSORED, never negative. candles: {t (start), close, high, low}, 5 minutes."""
    for k, v in (("provider_lag_s", provider_lag_s), ("up", up), ("down", down), ("horizon_s", horizon_s)):
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0):
            raise SocialCatError(f"{k} must be a positive number")
    for k, v in (("available_at", available_at), ("decision_time", decision_time)):
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)):
            raise SocialCatError(f"{k} must be a finite time")
    if float(available_at) > float(decision_time):
        raise SocialCatError("the catalyst was not available at the decision (available_at after decision_time)")
    start = max(float(available_at), float(decision_time)) + float(provider_lag_s)
    path = sorted((c for c in candles if float(c["t"]) >= start), key=lambda c: float(c["t"]))
    base = {"status": PROPOSAL_STATUS, "evidence_class": "TEST_ONLY"}
    if not path:
        return {**base, "label": None, "state": "CENSORED_NO_PRICE_AFTER_AVAILABILITY"}
    p0 = float(path[0]["close"])
    end = float(path[0]["t"]) + float(horizon_s)
    for c in path[1:]:
        if float(c["t"]) >= end:
            break
        hit_up, hit_dn = float(c["high"]) >= p0 * (1 + up), float(c["low"]) <= p0 * (1 - down)
        if hit_up and hit_dn:
            return {**base, "label": 0, "state": "AMBIGUOUS_BAR", "touch_t": float(c["t"])}
        if hit_up:
            return {**base, "label": 1, "state": "TARGET_FIRST", "touch_t": float(c["t"])}
        if hit_dn:
            return {**base, "label": 0, "state": "INVALIDATION_FIRST", "touch_t": float(c["t"])}
    if float(path[-1]["t"]) + 300 < end:
        return {**base, "label": None, "state": "PENDING_OR_CENSORED"}
    return {**base, "label": 0, "state": "NEITHER_WITHIN_HORIZON"}


def proposed_withdrawal_label(revisions: Sequence[dict], *, available_at: float, horizon_s: float, as_of: float) -> dict:
    """Proposal: a denial, cancellation or deleted source recorded after available_at and within horizon_s. Before the horizon has
    passed at as_of without one, the label is PENDING (never a negative)."""
    if not (isinstance(horizon_s, (int, float)) and not isinstance(horizon_s, bool) and math.isfinite(horizon_s) and horizon_s > 0):
        raise SocialCatError("horizon_s must be a positive number")
    a, end = float(available_at), float(available_at) + float(horizon_s)
    hits = sorted(float(r["revised_at"]) for r in revisions if r.get("kind") in WITHDRAW_KINDS and a < float(r["revised_at"]) <= min(end, float(as_of)))
    base = {"status": PROPOSAL_STATUS, "evidence_class": "TEST_ONLY"}
    if hits:
        return {**base, "label": 1, "state": "WITHDRAWN", "at": hits[0]}
    if float(as_of) < end:
        return {**base, "label": None, "state": "PENDING"}
    return {**base, "label": 0, "state": "NOT_WITHDRAWN_WITHIN_HORIZON"}

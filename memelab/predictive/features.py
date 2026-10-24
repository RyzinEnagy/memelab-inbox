"""Phase 05: point-in-time features over the evidence store (research only, flag OFF, imported by no existing module).

`features_as_of(con, chain, mint, decision_time, feature_version)` returns the feature snapshot of one exact (chain, mint) as
of one time, computed only from rows whose conservatively established availability is at or before that time. Every row
the computation reads passes through `replay_core.Audit`, which raises `replay_core.LeakageError` for anything later (the
cutoff clock of the social replay harness, reused). Same store and arguments give the same snapshot sha256.

Feature definitions are versioned as one set (FEATURE_VERSION and the sha256 of the definitions); a request for another
version raises FeatureVersionError, and a stored snapshot is never mixed with another version (P46). Missingness is explicit:
every value row holds either a number or a named reason with its basis, never a stand-in zero. A zero is a value only where
the covered vendor history shows no trade in the window (volume, candle count, realized variation).

Only closes and volumes of vendor candles are used. GeckoTerminal computes a candle's open from the request window (the
earliest candle of a response gets another open than the same candle read inside a longer window), and high or low move with
it: 80 of 57,584 candles read twice in Phase 05 differed only there (evidence/revision_check_p04.json).

Availability (DATA_TIME_CONTRACT, P04):
  - decision-row, token-row, history and universe features: the export commit time of the decision row (the row is inside
    the commit), evidence FACT;
  - vendor candles, mode "provider": the candle's stored available_at (end + provider lag, a HEURISTIC reconstruction, or the
    lab's read when that is earlier; a revision only from the read that showed it); mode "capture": the lab's first read of
    that version, so a backfill never counts for a decision before it was read.
Missing reasons have a basis: AS_OF (decided by what existed at the decision), HEURISTIC (decided by the vendor's history
under the provider-lag reconstruction) or RETRIEVAL (decided by what the lab fetched or the vendor served when read: not
fetched, sealed, read failed, vendor has no data). RETRIEVAL reasons are censoring, never a model input (P09).
"""
from __future__ import annotations

import json
import math
import sqlite3
from typing import Any, Sequence

from ..social import outcomes_core as OC
from ..social import replay_core as RC
from . import sources as SRC
from . import store as S

FEATURE_VERSION = "1"
FEATURE_SET_NAME = "memelab.predictive.features"
MODES = ("provider", "capture")
LeakageError = RC.LeakageError
PERIOD_S = 300
SIG = 10                                   # significant digits kept in stored values (platform-stable hashes)

AS_OF, HEURISTIC, RETRIEVAL = "AS_OF", "HEURISTIC", "RETRIEVAL"
REASONS = {
    "NOT_IN_UNIVERSE": AS_OF, "ABSENT_IN_SNAPSHOT": AS_OF, "NOT_NUMERIC": AS_OF, "NON_POSITIVE": AS_OF, "NEGATIVE": AS_OF,
    "UNPARSEABLE": AS_OF, "INCONSISTENT_TIME": AS_OF, "NO_PRIOR_DECISION": AS_OF, "NO_TOKEN_ROW": AS_OF,
    "OUT_OF_SCOPE_CHAIN": AS_OF, "NO_POOL_AT_DECISION": AS_OF,
    "NO_CANDLE_AVAILABLE": HEURISTIC, "BEFORE_FIRST_CANDLE": HEURISTIC,
    "NOT_FETCHED_SEALED": RETRIEVAL, "NOT_FETCHED": RETRIEVAL, "NOT_RETRIEVED_BY_DECISION": RETRIEVAL,
    "VENDOR_NO_DATA": RETRIEVAL, "VENDOR_READ_FAILED": RETRIEVAL, "VENDOR_BAD_BODY": RETRIEVAL, "CIRCUIT_OPEN": RETRIEVAL,
    "CALL_CAP_REACHED": RETRIEVAL, "OUTSIDE_FETCHED_WINDOW": RETRIEVAL, "VENDOR_IDENTITY_MISMATCH": RETRIEVAL,
}
STATUS_REASON = {"READ_FAILED": "VENDOR_READ_FAILED", "BAD_BODY": "VENDOR_BAD_BODY", "CIRCUIT_OPEN": "CIRCUIT_OPEN",
                 "CALL_CAP_REACHED": "CALL_CAP_REACHED", "IDENTITY_MISMATCH": "VENDOR_IDENTITY_MISMATCH"}


class FeatureVersionError(ValueError):
    pass


class SnapshotDriftError(RuntimeError):
    """A stored snapshot and a recomputation from the same store disagree: something leaked or a row changed."""


class AsOfError(ValueError):
    pass


def _f(name, group, source, unit, window_s, transform, evidence):
    return {"name": name, "group": group, "source_id": source, "unit": unit, "window_s": window_s, "transform": transform,
            "evidence": evidence, "version": FEATURE_VERSION}


_X, _G = S.SOURCE_EXPORT, S.SOURCE_GT
FEATURES: list[dict] = [
    _f("thesis_log_price_usd", "thesis", _X, "ln usd", None, "ln(snapshot.price); price <= 0 is NON_POSITIVE", "FACT"),
    _f("thesis_log1p_liquidity_usd", "thesis", _X, "ln usd", None, "ln(1 + snapshot.liquidity); negative is NEGATIVE", "FACT"),
    _f("thesis_log1p_mcap_usd", "thesis", _X, "ln usd", None, "ln(1 + snapshot.mcap)", "FACT"),
    _f("thesis_log1p_vol_24h_usd", "thesis", _X, "ln usd", None, "ln(1 + snapshot.vol_24h)", "FACT"),
    _f("thesis_log1p_exit_cap_3pct_usd", "thesis", _X, "ln usd", None, "ln(1 + snapshot.exit_cap_3pct); stale context, not depth now", "FACT"),
    _f("thesis_holders", "thesis", _X, "count", None, "snapshot.holders", "FACT"),
    _f("thesis_adj_top10_pct", "thesis", _X, "percent", None, "snapshot.adj_top10", "FACT"),
    _f("thesis_cluster_pct", "thesis", _X, "percent", None, "snapshot.cluster_pct", "FACT"),
    _f("thesis_dev_pct", "thesis", _X, "percent", None, "snapshot.dev_pct", "FACT"),
    _f("thesis_insider_pct", "thesis", _X, "percent", None, "snapshot.insider_pct", "FACT"),
    _f("thesis_net_buyers_24h", "thesis", _X, "count", None, "snapshot.net_buyers_24h (may be negative)", "FACT"),
    _f("thesis_score", "thesis", _X, "points", None, "row.score; version-dependent (PI-D-008): data_version names the export commit", "FACT"),
    _f("thesis_fatal_present", "thesis", _X, "0 or 1", None, "1 when row.fatal_flags_json is a non-empty list", "FACT"),
    _f("thesis_status_rejected", "thesis", _X, "0 or 1", None, "1 when row.status is REJECTED", "FACT"),
    _f("thesis_snapshot_age_s", "thesis", _X, "s", None, "query time - row.created_at (created_at as data, PI-D-011)", "FACT"),
    _f("token_age_s", "token", _X, "s", None, "query time - token.first_pool_at (provider claim recorded in the export)", "FACT"),
    _f("hist_prior_decisions", "history", _X, "count", None, "decision events of the same chain and mint before this one", "FACT"),
    _f("hist_seconds_since_prior_decision", "history", _X, "s", None, "decision time - previous decision time of the mint", "FACT"),
    _f("hist_log_price_change_since_prior", "history", _X, "ln ratio", None, "ln(price now / price at the previous decision)", "FACT"),
    _f("universe_decisions_24h", "universe", _X, "count", 86400, "decision events of the chain in (t - 24 h, t]", "FACT"),
    _f("universe_new_mints_24h", "universe", _X, "count", 86400, "mints of the chain whose first decision is in (t - 24 h, t]", "FACT"),
    _f("cdl_last_close_age_s", "candle", _G, "s", None, "t - end of the newest available candle of the point-in-time pool", "HEURISTIC"),
    _f("cdl_log_ret_1h", "candle", _G, "ln ratio", 3600, "ln(last close / close of the newest candle ending at or before t - 1 h)", "HEURISTIC"),
    _f("cdl_log_ret_6h", "candle", _G, "ln ratio", 21600, "same over 6 h", "HEURISTIC"),
    _f("cdl_log_ret_24h", "candle", _G, "ln ratio", 86400, "same over 24 h", "HEURISTIC"),
    _f("cdl_vol_usd_1h", "candle", _G, "usd", 3600, "sum of candle volume, candles ending in (t - 1 h, t] and available", "HEURISTIC"),
    _f("cdl_vol_usd_24h", "candle", _G, "usd", 86400, "same over 24 h", "HEURISTIC"),
    _f("cdl_candles_24h", "candle", _G, "count", 86400, "5-minute candles with trades ending in (t - 24 h, t]", "HEURISTIC"),
    _f("cdl_rv_6h", "candle", _G, "ln", 21600, "sqrt(sum of squared ln close-to-close changes) from the price at t - 6 h through the window", "HEURISTIC"),
    _f("cdl_log_drawdown_24h", "candle", _G, "ln ratio", 86400, "ln(last close / max close over the window and the price at t - 24 h); "
       "closes only: a candle's open, and with it high or low, depends on the request window", "HEURISTIC"),
    _f("cdl_log_range_24h", "candle", _G, "ln ratio", 86400, "ln(max close / min close) over the window and the price at t - 24 h; closes only",
       "HEURISTIC"),
    _f("xsrc_log_close_over_thesis_price", "cross", _G + "+" + _X, "ln ratio", None, "ln(last close / snapshot.price): pool route consistency (P02)", "HEURISTIC"),
]
NAMES = [f["name"] for f in FEATURES]
TRANSFORM_REVISION = "asof-1"              # bump with FEATURE_VERSION whenever a transform's code changes


def feature_set_definitions() -> dict:
    return {"name": FEATURE_SET_NAME, "feature_version": FEATURE_VERSION, "transform_revision": TRANSFORM_REVISION,
            "period_s": PERIOD_S, "significant_digits": SIG, "features": FEATURES, "reasons": REASONS}


def feature_set_sha() -> str:
    return S.sha(feature_set_definitions())


def require_compatible(feature_version: str, feature_set_sha_: str | None = None) -> None:
    """Feature versions are incompatible by default (P46): a request, a stored snapshot or a model card must name this exact
    version and, when given, this exact definitions hash."""
    if feature_version != FEATURE_VERSION:
        raise FeatureVersionError(f"feature version {feature_version!r} is not {FEATURE_VERSION!r}: versions never mix (P46)")
    if feature_set_sha_ is not None and feature_set_sha_ != feature_set_sha():
        raise FeatureVersionError("FEATURE_SCHEMA_MISMATCH: definitions hash differs from the code's (P46)")


def _r(x: float) -> float:
    return float(f"{x:.{SIG}g}")


def _t(x: Any) -> float | None:
    return None if x is None else round(float(x), 6)


# ---------------------------------------------------------------- the as-of view
class AsOfView:
    """Everything the feature code may read at `cutoff`. SQL filters by availability; every returned row is then audited by the
    replay harness's Audit, which raises LeakageError for any row available after the cutoff."""

    def __init__(self, con: sqlite3.Connection, cutoff: float, mode: str = "provider", audit: RC.Audit | None = None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if not S._num(cutoff):
            raise AsOfError("cutoff must be a finite time")
        self.con, self.cutoff, self.mode = con, float(cutoff), mode
        self.audit = audit or RC.Audit()

    def _check(self, kind: str, rows: list[dict]) -> list[dict]:
        return self.audit.check(kind, rows, self.cutoff)

    def decisions_of(self, chain: str, mint: str) -> list[dict]:
        rows = S.iter_rows(self.con, "SELECT * FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time <= ? "
                                     "ORDER BY decision_time, id", (chain, mint, self.cutoff))
        for r in rows:
            r["_avail"] = r["decision_time"]
        return self._check("decision", rows)

    def universe(self, chain: str, since: float) -> tuple[list[dict], list[dict]]:
        evs = S.iter_rows(self.con, "SELECT decision_key, mint, decision_time FROM predictive_decisions WHERE chain=? "
                                    "AND decision_time > ? AND decision_time <= ?", (chain, since, self.cutoff))
        firsts = S.iter_rows(self.con, "SELECT mint, MIN(decision_time) AS first_t FROM predictive_decisions WHERE chain=? "
                                       "AND decision_time <= ? GROUP BY mint HAVING MIN(decision_time) > ?",
                             (chain, self.cutoff, since))
        for r in evs:
            r["_avail"] = r["decision_time"]
        for r in firsts:
            r["_avail"] = r["first_t"]
        return self._check("universe", evs), self._check("universe", firsts)

    def export_response(self, response_key: str) -> dict:
        r = S.iter_rows(self.con, "SELECT response_key, body_sha256, retrieved_at FROM predictive_raw_responses "
                                  "WHERE response_key=?", (response_key,))
        return r[0] if r else {}

    def candles(self, chain: str, mint: str, pool: str) -> list[dict]:
        """Latest version of each candle position visible at the cutoff (outcomes_core.visible: a revision replaces the earlier
        version only from the moment it was available), vanished positions removed."""
        col = "available_at" if self.mode == "provider" else "retrieved_at"
        rows = S.iter_rows(self.con, f"SELECT * FROM predictive_candles WHERE chain=? AND mint=? AND pool_address=? "
                                     f"AND period_s = ? AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))
        obs = [{"chain": r["chain"], "contract": r["mint"], "available_at": r[col], "series_key": r["series_key"],
                "seq": r["id"], "t": r["start_at"], "kind": "CANDLE", "provider": r["source_id"], "_row": r} for r in rows]
        vis = OC.visible(obs, chain, mint, self.cutoff)
        out = []
        for o in vis:
            r = dict(o["_row"])
            r["_avail"] = r[col]
            if not r["vanished"]:
                out.append(r)
        out.sort(key=lambda r: r["end_at"])
        return self._check("candle", out)

    def series_status(self, chain: str, pool: str) -> list[dict]:
        """Fetch-series outcomes (retrieval metadata). In capture mode only series read by the cutoff exist."""
        q = "SELECT * FROM predictive_source_status WHERE chain=? AND pool_address=? AND period_s = ?"
        args: tuple = (chain, pool, PERIOD_S)
        if self.mode == "capture":
            q += " AND checked_at <= ?"
            args += (self.cutoff,)
        return S.iter_rows(self.con, q + " ORDER BY checked_at, id", args)


# ---------------------------------------------------------------- value records
def _val(name: str, value: float | None = None, reason: str | None = None, *, inputs: Sequence[dict] = (),
         export: dict | None = None, exports: Sequence[dict] = ()) -> dict:
    """One feature value with its provenance. inputs: candle rows used; export(s): {"decision": row, "response": row}."""
    spec = next(f for f in FEATURES if f["name"] == name)
    if (value is None) == (reason is None):
        raise AsOfError(f"{name}: exactly one of value or missing reason")
    if value is not None and not S._num(value):
        raise AsOfError(f"{name}: value {value!r} is not finite")
    if reason is not None and reason not in REASONS:
        raise AsOfError(f"{name}: unknown missing reason {reason!r}")
    keys, hashes, avs, rets, bases, srcs = set(), set(), [], [], set(), set()
    for ex in ([export] if export else []) + list(exports):
        d, resp = ex["decision"], ex.get("response") or {}
        keys.add("decision:" + d["decision_key"])
        if resp.get("body_sha256"):
            hashes.add(resp["body_sha256"])
        avs.append(float(d["decision_time"]))
        if resp.get("retrieved_at") is not None:
            rets.append(float(resp["retrieved_at"]))
        bases.add("EXPORT_COMMIT")
        srcs.add(S.SOURCE_EXPORT)
    for c in inputs:
        keys.add("candle:" + c["obs_key"])
        hashes.add(c["raw_sha256"])
        avs.append(float(c["_avail"]))
        rets.append(float(c["retrieved_at"]))
        bases.add(c["available_basis"])
        srcs.add(c["source_id"])
    if value is None:
        evidence = spec["evidence"]
    else:
        evidence = "HEURISTIC" if "PROVIDER_LAG_RECONSTRUCTION" in bases else "FACT"
    return {"feature_name": name, "feature_version": FEATURE_VERSION,
            "value": _r(value) if value is not None else None,
            "missing_reason": reason, "missing_basis": REASONS[reason] if reason else None,
            "feature_available_at": _t(max(avs)) if (avs and value is not None) else None,
            "available_basis": "+".join(sorted(bases)) if (bases and value is not None) else None,
            "evidence": evidence, "source_ids": sorted(srcs) or [spec["source_id"]], "raw_hashes": sorted(hashes),
            "source_record_count": len(keys), "retrieved_at": _t(max(rets)) if rets else None,
            "source_fingerprint": S.sha(sorted(keys))}


def _num_field(snap: dict, key: str, *, log1p: bool = False, log: bool = False, allow_negative: bool = False) -> tuple:
    if key not in snap or snap.get(key) is None:
        return None, "ABSENT_IN_SNAPSHOT"
    v = snap[key]
    if not S._num(v):
        return None, "NOT_NUMERIC"
    v = float(v)
    if log:
        return (math.log(v), None) if v > 0 else (None, "NON_POSITIVE")
    if v < 0 and not allow_negative:
        return None, "NEGATIVE"
    return (math.log1p(v), None) if log1p else (v, None)


def _iso(s: Any) -> float | None:
    if S._num(s):
        return float(s)
    if isinstance(s, str) and s:
        try:
            from datetime import datetime
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------- the computation
def _candle_values(view: AsOfView, dec: dict | None, T: float, thesis_price: float | None, export: dict | None) -> list[dict]:
    names = [f["name"] for f in FEATURES if f["group"] in ("candle", "cross")]

    def all_missing(reason: str) -> list[dict]:
        return [_val(n, reason=reason) for n in names]

    if dec is None:
        return all_missing("NOT_IN_UNIVERSE")
    if dec["chain"] != "solana":
        return all_missing("OUT_OF_SCOPE_CHAIN")
    pool = dec["pool_address"]
    if not pool:
        return all_missing("NO_POOL_AT_DECISION")
    lag = S._provider_lag()
    stats = [s for s in view.series_status("solana", pool) if s["mint"] == dec["mint"]]
    need_to = T - lag                     # every candle that can be available at T ends at or before this
    good = [s for s in stats if s["status"] in ("OK", "NO_DATA") and s["boundary_at"] >= need_to - 1e-9]
    if not good:
        bad = [s for s in stats if s["status"] in STATUS_REASON and s["boundary_at"] >= need_to - 1e-9]
        if bad:
            return all_missing(STATUS_REASON[bad[-1]["status"]])
        if view.mode == "capture" and not stats:
            return all_missing("NOT_RETRIEVED_BY_DECISION")
        scope = SRC.fetch_scope({"chain": dec["chain"], "pool_address": pool, "decision_time": dec["decision_time"]})
        return all_missing("NOT_FETCHED_SEALED" if scope == "NOT_FETCHED_SEALED" else "NOT_FETCHED")
    complete = any(s["cover_complete"] for s in good)
    cover_from = float("-inf") if complete else min((s["cover_from"] for s in good if s["cover_from"] is not None),
                                                    default=float("inf"))
    if all(s["status"] == "NO_DATA" for s in good):
        return all_missing("VENDOR_NO_DATA")
    cs = view.candles("solana", dec["mint"], pool)
    if not cs:
        return all_missing("NO_CANDLE_AVAILABLE" if complete else "OUTSIDE_FETCHED_WINDOW")
    last = cs[-1]

    def price_at(x: float) -> tuple[dict | None, str | None]:
        cand = [c for c in cs if c["end_at"] <= x]
        if cand:
            return cand[-1], None
        if complete:
            return None, "BEFORE_FIRST_CANDLE"
        return None, ("OUTSIDE_FETCHED_WINDOW" if cover_from > x - PERIOD_S else "NO_CANDLE_AVAILABLE")

    def window(w: float) -> tuple[list[dict] | None, str | None]:
        if cover_from > T - w - PERIOD_S:
            return None, "OUTSIDE_FETCHED_WINDOW"
        return [c for c in cs if T - w < c["end_at"] <= T], None

    out = [_val("cdl_last_close_age_s", T - last["end_at"], inputs=[last])]
    for name, w in (("cdl_log_ret_1h", 3600), ("cdl_log_ret_6h", 21600), ("cdl_log_ret_24h", 86400)):
        base, why = price_at(T - w)
        out.append(_val(name, reason=why) if base is None else _val(name, math.log(last["c"] / base["c"]), inputs=[base, last]))
    for name, w in (("cdl_vol_usd_1h", 3600), ("cdl_vol_usd_24h", 86400)):
        ws, why = window(w)
        out.append(_val(name, reason=why) if ws is None else _val(name, sum(c["v"] for c in ws), inputs=ws))
    ws, why = window(86400)
    out.append(_val("cdl_candles_24h", reason=why) if ws is None else _val("cdl_candles_24h", float(len(ws)), inputs=ws))
    ws, why = window(21600)
    base, why2 = price_at(T - 21600)
    if ws is None or base is None:
        out.append(_val("cdl_rv_6h", reason=why or why2))
    else:
        seq = [base] + [c for c in ws if c is not base]
        rv = math.sqrt(sum(math.log(b["c"] / a["c"]) ** 2 for a, b in zip(seq, seq[1:])))
        out.append(_val("cdl_rv_6h", rv, inputs=seq + ([last] if last not in seq else [])))
    ws, why = window(86400)
    base, why2 = price_at(T - 86400)
    if ws is None or base is None:
        out.append(_val("cdl_log_drawdown_24h", reason=why or why2))
        out.append(_val("cdl_log_range_24h", reason=why or why2))
    else:
        hi = max([base["c"]] + [c["c"] for c in ws])
        lo = min([base["c"]] + [c["c"] for c in ws])
        used = [base] + ws + ([last] if last not in ws else [])
        out.append(_val("cdl_log_drawdown_24h", math.log(last["c"] / hi), inputs=used))
        out.append(_val("cdl_log_range_24h", math.log(hi / lo), inputs=used))
    if thesis_price is None:
        out.append(_val("xsrc_log_close_over_thesis_price", reason="ABSENT_IN_SNAPSHOT"))
    else:
        out.append(_val("xsrc_log_close_over_thesis_price", math.log(last["c"] / thesis_price), inputs=[last], export=export))
    return out


def compute(view: AsOfView, chain: str, mint: str, T: float) -> dict:
    """The feature values of (chain, mint) at T from `view` alone."""
    decs = view.decisions_of(chain, mint)
    dec = decs[-1] if decs else None
    resp = view.export_response(dec["response_key"]) if dec else {}
    export = {"decision": dec, "response": resp} if dec else None
    vals: list[dict] = []
    if dec is None:
        vals += [_val(f["name"], reason="NOT_IN_UNIVERSE") for f in FEATURES if f["group"] in ("thesis", "token", "history")]
    else:
        row = json.loads(dec["row_json"])
        try:
            snap = row.get("snapshot_json")
            snap = snap if isinstance(snap, dict) else json.loads(snap or "{}")
            if not isinstance(snap, dict):
                raise ValueError
        except (TypeError, ValueError):
            snap = None
        spec = [("thesis_log_price_usd", "price", dict(log=True)), ("thesis_log1p_liquidity_usd", "liquidity", dict(log1p=True)),
                ("thesis_log1p_mcap_usd", "mcap", dict(log1p=True)), ("thesis_log1p_vol_24h_usd", "vol_24h", dict(log1p=True)),
                ("thesis_log1p_exit_cap_3pct_usd", "exit_cap_3pct", dict(log1p=True)), ("thesis_holders", "holders", {}),
                ("thesis_adj_top10_pct", "adj_top10", {}), ("thesis_cluster_pct", "cluster_pct", {}),
                ("thesis_dev_pct", "dev_pct", {}), ("thesis_insider_pct", "insider_pct", {}),
                ("thesis_net_buyers_24h", "net_buyers_24h", dict(allow_negative=True))]
        for name, key, kw in spec:
            v, why = (None, "UNPARSEABLE") if snap is None else _num_field(snap, key, **kw)
            vals.append(_val(name, v, why, export=export) if why is None else _val(name, reason=why))
        sc = row.get("score")
        vals.append(_val("thesis_score", float(sc), export=export) if S._num(sc) else
                    _val("thesis_score", reason="ABSENT_IN_SNAPSHOT" if sc is None else "NOT_NUMERIC"))
        try:
            ff = json.loads(row.get("fatal_flags_json") or "null")
            vals.append(_val("thesis_fatal_present", float(bool(ff)), export=export) if isinstance(ff, list) else
                        _val("thesis_fatal_present", reason="ABSENT_IN_SNAPSHOT" if ff is None else "UNPARSEABLE"))
        except (TypeError, ValueError):
            vals.append(_val("thesis_fatal_present", reason="UNPARSEABLE"))
        st = row.get("status")
        vals.append(_val("thesis_status_rejected", float(st == "REJECTED"), export=export) if isinstance(st, str) else
                    _val("thesis_status_rejected", reason="ABSENT_IN_SNAPSHOT"))
        vals.append(_val("thesis_snapshot_age_s", T - float(dec["created_at"]), export=export))
        tok = json.loads(dec["token_json"]) if dec["token_json"] else None
        if tok is None:
            vals.append(_val("token_age_s", reason="NO_TOKEN_ROW"))
        else:
            fp = _iso(tok.get("first_pool_at"))
            if fp is None:
                vals.append(_val("token_age_s", reason="ABSENT_IN_SNAPSHOT" if tok.get("first_pool_at") is None else "UNPARSEABLE"))
            elif fp > T:
                vals.append(_val("token_age_s", reason="INCONSISTENT_TIME"))
            else:
                vals.append(_val("token_age_s", T - fp, export=export))
        prior = [d for d in decs if d["decision_time"] < dec["decision_time"]]
        vals.append(_val("hist_prior_decisions", float(len(prior)), export=export))
        if not prior:
            vals.append(_val("hist_seconds_since_prior_decision", reason="NO_PRIOR_DECISION"))
            vals.append(_val("hist_log_price_change_since_prior", reason="NO_PRIOR_DECISION"))
        else:
            p = prior[-1]
            pexp = {"decision": p, "response": view.export_response(p["response_key"])}
            vals.append(_val("hist_seconds_since_prior_decision", dec["decision_time"] - p["decision_time"], export=export))
            try:
                ps = json.loads(json.loads(p["row_json"]).get("snapshot_json") or "{}")
                pp = ps.get("price") if isinstance(ps, dict) else None
            except (TypeError, ValueError):
                pp = None
            now_p = snap.get("price") if isinstance(snap, dict) else None
            if S._num(pp) and pp > 0 and S._num(now_p) and now_p > 0:
                vals.append(_val("hist_log_price_change_since_prior", math.log(now_p / pp), exports=[export, pexp]))
            else:
                vals.append(_val("hist_log_price_change_since_prior", reason="ABSENT_IN_SNAPSHOT"))
    evs, firsts = view.universe(chain, T - 86400)
    uni_fp = S.sha(sorted("decision:" + e["decision_key"] for e in evs))
    u1 = _val("universe_decisions_24h", float(len(evs)))
    u2 = _val("universe_new_mints_24h", float(len(firsts)))
    for u, rows in ((u1, evs), (u2, firsts)):
        u.update(feature_available_at=_t(max((r["_avail"] for r in rows), default=None)) if rows else None,
                 available_basis="EXPORT_COMMIT" if rows else None, source_ids=[S.SOURCE_EXPORT], evidence="FACT",
                 source_record_count=len(rows), source_fingerprint=uni_fp if u is u1 else S.sha(sorted(r["mint"] for r in rows)))
    vals += [u1, u2]
    thesis_price = None
    if dec is not None:
        try:
            sp = json.loads(json.loads(dec["row_json"]).get("snapshot_json") or "{}").get("price")
            thesis_price = float(sp) if S._num(sp) and sp > 0 else None
        except (TypeError, ValueError, AttributeError):
            thesis_price = None
    vals += _candle_values(view, dec, T, thesis_price, export)
    order = {n: i for i, n in enumerate(NAMES)}
    vals.sort(key=lambda v: order[v["feature_name"]])
    if [v["feature_name"] for v in vals] != NAMES:
        raise AsOfError("feature set incomplete")
    return {"decision": dec, "values": vals}


def values_sha(values: list[dict]) -> str:
    keep = ("feature_name", "feature_version", "value", "missing_reason", "missing_basis", "feature_available_at",
            "available_basis", "evidence", "source_fingerprint", "raw_hashes")
    return S.sha([{k: v.get(k) for k in keep} for v in values])


def features_as_of(con: sqlite3.Connection, chain: str, mint: str, decision_time: float, feature_version: str, *,
                   mode: str = "provider", persist: bool = False, now: float | None = None) -> dict:
    """The strict point-in-time feature API. Deterministic: same store and arguments, same snapshot_sha256."""
    require_compatible(feature_version)
    S.check_address(chain, mint)
    if not S._num(decision_time):
        raise AsOfError("decision_time must be a finite epoch time")
    T = float(decision_time)
    view = AsOfView(con, T, mode)
    res = compute(view, chain, mint, T)
    vals, dec = res["values"], res["decision"]
    for v in vals:
        if v["feature_available_at"] is not None and v["feature_available_at"] > T:
            raise LeakageError(f"{v['feature_name']} available at {v['feature_available_at']} after the cutoff {T} (P36)")
    status = source_status(vals)
    snap = {"snapshot_key": S.sha([chain, mint, _t(T), FEATURE_VERSION, mode]), "decision_key": dec["decision_key"] if dec else None,
            "chain": chain, "mint": mint, "pool_address": dec["pool_address"] if dec else None, "decision_time": T, "cutoff_at": T,
            "feature_version": FEATURE_VERSION, "feature_set_sha": feature_set_sha(), "availability_mode": mode,
            "data_version": S.sha(sorted({v["source_fingerprint"] for v in vals})), "source_status": status,
            "max_input_available_at": max((v["feature_available_at"] for v in vals if v["feature_available_at"] is not None),
                                          default=None),
            "snapshot_sha256": values_sha(vals), "values": vals, "rows_audited": view.audit.records}
    if persist:
        save_snapshot(con, snap, now=now if now is not None else 0.0)
    return snap


def source_status(vals: list[dict]) -> dict:
    """Per source: OK, or the RETRIEVAL reasons that left values missing (visible staleness and outages, P47)."""
    out: dict[str, Any] = {}
    for src, group in ((S.SOURCE_EXPORT, ("thesis", "token", "history", "universe")), (S.SOURCE_GT, ("candle", "cross"))):
        names = {f["name"] for f in FEATURES if f["group"] in group}
        rs = sorted({v["missing_reason"] for v in vals if v["feature_name"] in names and v["missing_basis"] == RETRIEVAL})
        out[src] = rs or "OK"
    return out


def save_snapshot(con: sqlite3.Connection, snap: dict, *, now: float) -> bool:
    """Write a snapshot and its values once. A second write of the same key must carry the same hash (else SnapshotDriftError);
    nothing is ever updated."""
    require_compatible(snap["feature_version"], snap["feature_set_sha"])
    old = con.execute("SELECT snapshot_sha256 FROM predictive_snapshots WHERE snapshot_key=?", (snap["snapshot_key"],)).fetchone()
    if old is not None:
        if old[0] != snap["snapshot_sha256"]:
            raise SnapshotDriftError(f"snapshot {snap['snapshot_key'][:12]} recomputed differently from the stored one")
        return False
    S._insert(con, "predictive_feature_sets", {"feature_set_sha": snap["feature_set_sha"], "feature_version": FEATURE_VERSION,
                                              "definitions_json": S.canon(feature_set_definitions()), "recorded_at": float(now)})
    S._insert(con, "predictive_snapshots", {
        "snapshot_key": snap["snapshot_key"], "decision_key": snap["decision_key"], "chain": snap["chain"], "mint": snap["mint"],
        "pool_address": snap["pool_address"], "decision_time": snap["decision_time"], "cutoff_at": snap["cutoff_at"],
        "feature_version": snap["feature_version"], "feature_set_sha": snap["feature_set_sha"],
        "availability_mode": snap["availability_mode"], "data_version": snap["data_version"],
        "source_status_json": S.canon(snap["source_status"]), "max_input_available_at": snap["max_input_available_at"],
        "snapshot_sha256": snap["snapshot_sha256"], "recorded_at": float(now)})
    for v in snap["values"]:
        S._insert(con, "predictive_feature_values", {
            "value_key": S.sha([snap["snapshot_key"], v["feature_name"]]), "snapshot_key": snap["snapshot_key"],
            "chain": snap["chain"], "mint": snap["mint"], "pool_address": snap["pool_address"],
            "decision_time": snap["decision_time"], "cutoff_at": snap["cutoff_at"], "feature_name": v["feature_name"],
            "feature_version": v["feature_version"], "value": v["value"], "missing_reason": v["missing_reason"],
            "missing_basis": v["missing_basis"], "feature_available_at": v["feature_available_at"],
            "available_basis": v["available_basis"], "evidence": v["evidence"], "source_ids_json": S.canon(v["source_ids"]),
            "raw_hashes_json": S.canon(v["raw_hashes"]), "source_record_count": v["source_record_count"],
            "retrieved_at": v["retrieved_at"], "source_fingerprint": v["source_fingerprint"], "recorded_at": float(now)})
    con.commit()
    return True


def stored_values(con: sqlite3.Connection, snapshot_key: str) -> list[dict]:
    order = {n: i for i, n in enumerate(NAMES)}
    rows = S.iter_rows(con, "SELECT * FROM predictive_feature_values WHERE snapshot_key=?", (snapshot_key,))
    for r in rows:
        r["raw_hashes"] = json.loads(r["raw_hashes_json"])
        r["source_ids"] = json.loads(r["source_ids_json"])
    return sorted(rows, key=lambda r: order.get(r["feature_name"], 1 << 30))


def stored_snapshot(con: sqlite3.Connection, snapshot_key: str) -> dict | None:
    r = S.iter_rows(con, "SELECT * FROM predictive_snapshots WHERE snapshot_key=?", (snapshot_key,))
    if not r:
        return None
    snap = r[0]
    snap["values"] = stored_values(con, snapshot_key)
    return snap


def build_snapshots(con: sqlite3.Connection, *, feature_version: str, mode: str = "provider", now: float,
                    decisions: list[dict] | None = None) -> dict:
    """One persisted snapshot per decision record at its own decision time. Records without a usable identity are counted."""
    require_compatible(feature_version)
    decs = decisions if decisions is not None else S.iter_rows(con, "SELECT * FROM predictive_decisions ORDER BY decision_time, id")
    done, skipped = 0, []
    for d in decs:
        if d["chain"] not in S.KNOWN_CHAINS:
            skipped.append({"decision_key": d["decision_key"], "reason": "NO_CHAIN" if d["chain"] is None else "UNKNOWN_CHAIN"})
            continue
        snap = features_as_of(con, d["chain"], d["mint"], d["decision_time"], feature_version, mode=mode)
        if snap["decision_key"] != d["decision_key"]:
            raise AsOfError(f"decision {d['decision_key'][:12]}: the view chose another decision at its own time")
        done += save_snapshot(con, snap, now=now)
    return {"snapshots_added": done, "skipped": skipped}


def recompute_matches(con: sqlite3.Connection, snapshot_key: str) -> bool:
    """A stored snapshot equals its recomputation from the store as it is now (late rows must not change it)."""
    s = stored_snapshot(con, snapshot_key)
    if s is None:
        raise KeyError(snapshot_key)
    again = features_as_of(con, s["chain"], s["mint"], s["decision_time"], s["feature_version"], mode=s["availability_mode"])
    return again["snapshot_sha256"] == s["snapshot_sha256"]


# ---------------------------------------------------------------- training view (P13, P43, P46)
def training_view(con: sqlite3.Connection, *, as_of: float, feature_version: str, mode: str = "provider") -> list[dict]:
    """Stored decision snapshots usable by a model trained as of `as_of`: decisions at or before as_of only, one feature
    version and definitions hash, one availability mode. Each row is checked by validate_rows."""
    require_compatible(feature_version)
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    rows = S.iter_rows(con, "SELECT * FROM predictive_snapshots WHERE decision_key IS NOT NULL ORDER BY decision_time, id")
    if any(r["feature_version"] != feature_version or r["feature_set_sha"] != feature_set_sha() for r in rows
           if r["decision_time"] <= as_of):
        raise FeatureVersionError("the store holds snapshots of another feature version or definitions hash: rebuild, never mix (P46)")
    out = []
    for r in rows:
        if r["availability_mode"] != mode or r["decision_time"] > as_of:
            continue
        vals = stored_values(con, r["snapshot_key"])
        row = {"decision_time": r["decision_time"], "decision_key": r["decision_key"], "chain": r["chain"], "mint": r["mint"]}
        for v in vals:
            row[v["feature_name"]] = v["value"]
            row[v["feature_name"] + "__available_at"] = (v["feature_available_at"] if v["feature_available_at"] is not None
                                                         else r["decision_time"])
        out.append(row)
    cols = ["decision_time", "decision_key", "chain", "mint"] + [n for n in NAMES] + [n + "__available_at" for n in NAMES]
    validate_rows(out, columns=cols, availability=[n + "__available_at" for n in NAMES], as_of=as_of)
    return out


def validate_rows(rows: list[dict], *, columns: Sequence[str], availability: Sequence[str], decision: str = "decision_time",
                  label: str = "y", matures: str = "label_matures_at", as_of: float | None = None) -> None:
    """The lab's as-of row rule, fail closed (ported from the Phase 04 prototype core_numpy.validate_rows, PI-D-031): exactly
    the declared columns; every availability column present, finite and at or before the decision; a decision at or before
    as_of; a label only when it has matured by as_of (P05, P36)."""
    want = set(columns)
    for i, r in enumerate(rows):
        if set(r) != want:
            raise AsOfError(f"row {i}: columns {sorted(set(r) ^ want)} differ from the declared set (strict)")
        d = r[decision]
        if not isinstance(d, (int, float)) or isinstance(d, bool) or not math.isfinite(d):
            raise AsOfError(f"row {i}: decision time missing")
        if as_of is not None and d > as_of:
            raise AsOfError(f"row {i}: decided at {d}, after the training as-of {as_of} (P13, P43)")
        for a in availability:
            v = r[a]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise AsOfError(f"row {i}: {a} missing: an unknown availability time is not available")
            if v > d:
                raise AsOfError(f"row {i}: {a} {v} is after the decision {d} (future feature, P36)")
        if as_of is not None and r.get(label) is not None:
            m = r.get(matures)
            if not isinstance(m, (int, float)) or isinstance(m, bool) or not math.isfinite(m) or m > as_of:
                raise AsOfError(f"row {i}: label not matured by {as_of} (P05)")


# ---------------------------------------------------------------- truncation proof (the replay harness's leakage_check idea)
def truncated_copy(con: sqlite3.Connection, T: float, mode: str = "provider") -> sqlite3.Connection:
    """A new in-memory store holding only what existed at T: decisions at or before T, candle versions available at or before
    T in this mode, and the retrieval metadata the mode allows; no snapshot. Features computed on it must equal the full store's."""
    src = next(r[2] for r in con.execute("PRAGMA database_list") if r[1] == "main")
    if not src:
        raise AsOfError("truncated_copy needs a file-backed store")
    out = sqlite3.connect(":memory:")
    out.row_factory = sqlite3.Row
    S.migrate(out)
    out.execute("ATTACH DATABASE ? AS src", (src,))
    col = "available_at" if mode == "provider" else "retrieved_at"
    out.execute("INSERT INTO main.predictive_raw_responses SELECT * FROM src.predictive_raw_responses"
                + ("" if mode == "provider" else " WHERE retrieved_at <= ? OR source_id = 'state-export'"),
                () if mode == "provider" else (T,))
    out.execute(f"INSERT INTO main.predictive_candles SELECT * FROM src.predictive_candles WHERE {col} <= ?", (T,))
    out.execute("INSERT INTO main.predictive_source_status SELECT * FROM src.predictive_source_status"
                + ("" if mode == "provider" else " WHERE checked_at <= ?"), () if mode == "provider" else (T,))
    out.execute("INSERT INTO main.predictive_decisions SELECT * FROM src.predictive_decisions WHERE decision_time <= ?", (T,))
    out.commit()
    out.execute("DETACH DATABASE src")
    return out


def truncation_check(con: sqlite3.Connection, targets: list[tuple[str, str, float]], mode: str = "provider") -> dict:
    """For each (chain, mint, T): features from the full store and from the store truncated at T must be identical."""
    diffs = []
    for chain, mint, T in targets:
        full = features_as_of(con, chain, mint, T, FEATURE_VERSION, mode=mode)
        cut_con = truncated_copy(con, T, mode)
        try:
            cut = features_as_of(cut_con, chain, mint, T, FEATURE_VERSION, mode=mode)
        finally:
            cut_con.close()
        if full["snapshot_sha256"] != cut["snapshot_sha256"]:
            diffs.append({"chain": chain, "mint": mint, "T": T,
                          "features": [a["feature_name"] for a, b in zip(full["values"], cut["values"])
                                       if values_sha([a]) != values_sha([b])]})
    return {"checked": len(targets), "differences": diffs, "ok": not diffs}

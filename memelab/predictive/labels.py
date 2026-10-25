"""Phase 06: outcome label registry and censoring (research only, flag OFF, imported by no existing module).

Labels the three pre-registered primary targets of contract.TARGETS (T1 24 h, T1b 6 h, T2 24 h, version 1) from GeckoTerminal
5-minute pool candles read with `token=<mint>` (PI-D-038). Human-readable schema:
audits/predictive-intelligence/phase_06/labels/TARGET_SCHEMA.md. Standard library only; no network, no clock.

These are PRICE-PATH labels. A touch of a barrier is a displayed candle high or low, not a fill at any size: every row carries
PRICE_PATH_NOT_PROCEEDS and NO_HISTORICAL_EXECUTABLE_DEPTH, no position size, and no field named after profit or proceeds
(P08, P25, P44).

Rules (TARGET_REGISTRY.md, DECISIONS PI-D-014 to PI-D-021, PI-D-034, PI-D-037 to PI-D-040):
  - One read per decision: eligibility, the reference price and every target of a decision come from one response, so targets
    never mix reads whose window-dependent opens, highs or lows can differ (CC-03 rule 4, counterexample CX-06).
  - Reference candle and path come from contract.reference_candle and contract.path_candles: the reference is available at the
    decision (end + 300 s), the path starts at t_entry = decision + 300 s and never uses the candle holding t_entry (P06).
  - A candle touching both barriers is AMBIGUOUS_BAR, a negative (frozen tie rule); `label_tie_positive` keeps the opposite
    resolution for the sensitivity report only.
  - Absence needs evidence (CC-03 rule 1, PI-D-039): NO_TRADES_AFTER_ENTRY and TRADING_HALT count only on a read whose boundary
    reaches the span end and that returned a candle starting before the span. Else UNVERIFIABLE_NO_VENDOR_HISTORY (censored).
  - Pending is not negative (P05): a label whose read came before label_matures_at is PENDING and is never computed.
  - Censored (VENDOR_OR_ROUTE_GAP, UNVERIFIABLE_NO_VENDOR_HISTORY) is counted, never dropped and never a favourable fill (P09,
    P37); the conservative lens counts it T1 negative and T2 positive.
  - The training gate returns only DEVELOPMENT, LABELED, uncensored rows matured by the as-of time, and refuses bake-off labels
    (PI-D-034) and the sealed holdout folder. The label table refuses HOLDOUT rows: holdout labels exist only in the sealed file.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import contract as C
from . import decisions as D
from . import runtime as R
from . import store as S

LABELS_VERSION = "labels-1"
PERIOD_S = 300
LIMIT = 1000
T1, T1B, T2 = ("price_path_target_before_invalidation_24h", "price_path_target_before_invalidation_6h",
               "price_path_severe_drawdown_or_halt_24h")
TARGETS = (T1, T1B, T2)
assert set(TARGETS) == set(C.PRIMARY), "labels cover exactly the registry's primary targets"
STATES = ("LABELED", "PENDING", "PURGED", "THINNED", "MARKET_INACTIVE", "VENDOR_OR_ROUTE_GAP", "UNVERIFIABLE_NO_VENDOR_HISTORY",
          "NO_SNAPSHOT_PRICE", "OUT_OF_SCOPE_CHAIN", "PROSPECTIVE", "NOT_READ")
CENSORED = ("VENDOR_OR_ROUTE_GAP", "UNVERIFIABLE_NO_VENDOR_HISTORY")
SPLITS = ("DEVELOPMENT", "PURGED", "HOLDOUT", "PROSPECTIVE")
ROUTES = ("PIT_RECORDED", "CURRENT_VENDOR_LIST")
CAVEATS = tuple(C.TARGETS[T1]["caveats"])
FORBIDDEN_NAME_WORDS = ("profit", "return", "exit", "executable", "pnl", "proceeds_usd")
SEALED_DIR = "audits/predictive-intelligence/phase_06/sealed"
NEEDS_OTHER_POOLS = "NEEDS_OTHER_POOLS"
LIST_FAILED = "LIST_FAILED"
# P0 against the decision's own snapshot price: outside this ratio range the row is flagged (a wrong-token read, CX-S06, would be
# thousands of times away; all 224 real T1b development ratios lie in 0.23 to 1.47). A flag, not a class: the registry decides classes.
P0_SNAPSHOT_RATIO = (0.1, 10.0)


class LabelError(ValueError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


# ---------------------------------------------------------------- time rules
def holdout_start() -> float:
    return C.parse_utc(C.ACCEPTANCE["holdout_window_utc"][0])


def prospective_start() -> float:
    return C.parse_utc(C.ACCEPTANCE["prospective_from_utc"])


def ceil_grid(t: float, period: int = PERIOD_S) -> float:
    return float(math.ceil(float(t) / period) * period)


def t_entry(decision_time: float) -> float:
    return float(decision_time) + C.TARGETS[T1]["execution_lag_s"]


def window_end(target: str, decision_time: float) -> float:
    """End of everything the label reads: t_entry + horizon (+ the T2 halt confirmation)."""
    tg = C.TARGETS[target]
    return t_entry(decision_time) + tg["horizon_s"] + tg.get("confirm_s", 0)


def needed_boundary(target: str, decision_time: float) -> float:
    """Request boundary a label read needs: the window end on the candle grid (a candle overlapping the end is served whole)."""
    return ceil_grid(window_end(target, decision_time))


def split_of(target: str, decision_time: float) -> str:
    h0, p0 = holdout_start(), prospective_start()
    if decision_time >= p0:
        return "PROSPECTIVE"
    if decision_time >= h0:
        return "HOLDOUT"
    return "DEVELOPMENT" if C.label_matures_at(target, decision_time) <= h0 else "PURGED"


def halt_span(decision_time: float) -> tuple[float, float]:
    te = t_entry(decision_time)
    tg = C.TARGETS[T2]
    return te + tg["halt_quiet_from_s"], te + tg["horizon_s"] + tg["confirm_s"]


# ---------------------------------------------------------------- one vendor read
@dataclass(frozen=True)
class Read:
    """The candles one GeckoTerminal response contributes, after the store's rules (identity, boundary, validity)."""
    pool: str
    mint: str
    url: str
    boundary: float
    retrieved_at: float
    http_status: int
    identity: str | None
    candles: tuple = ()               # ((start, o, h, l, c, v), ...) ascending, one per position
    cover_from: float | None = None   # earliest candle start kept
    raw_count: int = 0                # rows in the body before any filter (a full page has LIMIT)
    response_key: str | None = None
    body_sha256: str | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.http_status == 200 and self.detail is None and (self.identity or "").startswith("OK")


def read_from_body(body: bytes, *, mint: str, pool: str, url: str, boundary: float, retrieved_at: float, http_status: int,
                   response_key: str | None = None, period: int = PERIOD_S) -> Read:
    """Apply exactly the store's candle rules to one response (store.ingest_gt_response): the token parameter is read from the
    URL sent, the body's meta must show the mint (store.gt_identity), a candle ending after the boundary is dropped (PI-D-034),
    each candle passes outcomes_core.normalize_observation and positive finite prices, the first copy of a position is kept."""
    from ..social import outcomes_core as OC
    S.check_address("solana", mint)
    S.check_address("solana", pool, "pool")
    bsha = hashlib.sha256(body or b"").hexdigest()
    base = dict(pool=pool, mint=mint, url=url, boundary=float(boundary), retrieved_at=float(retrieved_at),
                http_status=int(http_status), response_key=response_key, body_sha256=bsha)
    if S.url_period(url) not in (None, period):
        return Read(identity=None, detail="WRONG_PERIOD", **base)
    if int(http_status) != 200:
        return Read(identity=None, detail=f"HTTP_{int(http_status)}", **base)
    try:
        rows = S.parse_gt_ohlcv(body)
    except (ValueError, S.StoreError) as e:
        return Read(identity=None, detail=f"BAD_BODY:{str(e)[:80]}", **base)
    ident = S.gt_identity(body, mint, S.url_token(url))
    if not ident.startswith("OK"):
        return Read(identity=ident, raw_count=len(rows), **base)
    kept: dict[float, tuple] = {}
    for r in rows:
        try:
            start = S.epoch_seconds(r[0], "candle start")
            o, h, l, c, v = (float(x) if x is not None else None for x in r[1:6])
        except (TypeError, ValueError, IndexError):
            continue
        if start + period > float(boundary) or start in kept:
            continue
        try:
            OC.normalize_observation({"kind": "CANDLE", "chain": "solana", "contract": mint, "t": start, "available_at": float(retrieved_at),
                                      "provider": S.SOURCE_GT, "pair": pool, "period_s": period, "o": o, "h": h, "l": l, "c": c},
                                     {"future_dated_tolerance_s": 0})
        except OC.OutcomeError:
            continue
        if not all(S._num(x) and x > 0 for x in (o, h, l, c)) or not (S._num(v) and v >= 0):
            continue
        kept[start] = (start, o, h, l, c, v)
    cs = tuple(kept[k] for k in sorted(kept))
    return Read(identity=ident, candles=cs, cover_from=cs[0][0] if cs else None, raw_count=len(rows), **base)


def read_from_store(con: sqlite3.Connection, response_key: str, period: int = PERIOD_S) -> Read:
    r = con.execute("SELECT * FROM predictive_raw_responses WHERE response_key=?", (response_key,)).fetchone()
    if r is None:
        raise LabelError(f"no stored response {response_key}")
    return read_from_body(S.stored_body(con, response_key) or b"", mint=r["mint"], pool=r["pool_address"], url=r["request_url"],
                          boundary=r["boundary_at"], retrieved_at=r["retrieved_at"], http_status=r["http_status"],
                          response_key=response_key, period=period)


def in_span(c: tuple, s: float, e: float, period: int = PERIOD_S) -> bool:
    return float(c[0]) < e and float(c[0]) + period > s


def absence_evidenced(read: Read | None, s: float, e: float) -> bool:
    """CC-03 rule 1: the read saw everything in [s, e): its boundary reaches the span end and it returned a candle starting before
    the span (the vendor answers newest first). An empty or short page alone is never evidence of no trade (PI-D-039)."""
    return (read is not None and read.ok and read.boundary >= ceil_grid(e) and read.cover_from is not None
            and read.cover_from < s)


# ---------------------------------------------------------------- eligibility and classes
def snapshot_price(dec: dict) -> float | None:
    p = (dec.get("snapshot") or {}).get("price")
    return float(p) if S._num(p) and p > 0 else None


def eligibility_of(dec: dict, read: Read | None) -> str:
    """contract.eligibility on the decision's own read. A failed or identity-refused read is VENDOR_OR_ROUTE_GAP."""
    ok = read is not None and read.ok
    return C.eligibility(list(read.candles) if ok else None, float(dec["decision_time"]), read_ok=ok,
                         pool=(read.pool if read is not None else None), route=dec["route"],
                         snapshot_vol_24h=(dec.get("snapshot") or {}).get("vol_24h"))


def _gaps(path: list, s: float, e: float, period: int = PERIOD_S) -> float:
    pts = [s] + [x for c in path for x in (float(c[0]), float(c[0]) + period)] + [e]
    return max((pts[i + 1] - pts[i] for i in range(0, len(pts) - 1, 2)), default=e - s)


def classify(target: str, decision_time: float, read: Read, other_reads: Any = None) -> dict:
    """Class of one matured, eligible, kept decision from its own read. Returns {"state", "label_class", "label", ...}.
    other_reads (T2 only): None when not fetched yet, LIST_FAILED, or a list of Read | None for up to 3 other vendor pools."""
    tg = C.TARGETS[target]
    if target not in TARGETS:
        raise LabelError(f"{target} is not a primary target")
    ref = C.reference_candle(list(read.candles), decision_time)
    if ref is None or not read.ok:
        raise LabelError("classify needs an eligible decision with its reference candle in the same read")
    need = needed_boundary(target, decision_time)
    if read.boundary < need:
        raise LabelError(f"read boundary {read.boundary} is before the {target} window end {need}: plan error")
    p0 = float(ref[4])
    te = t_entry(decision_time)
    H = tg["horizon_s"]
    path = C.path_candles(list(read.candles), decision_time, H)
    flags: list[str] = []
    if read.candles and path and path[0][0] == read.candles[0][0]:
        flags.append("WINDOW_EDGE_CANDLE")      # a path candle whose open, high or low can depend on the request window
    max_gap = _gaps(path, te, te + H)
    if max_gap > C.ACCEPTANCE["label_sensitivities"]["sparse_path_gap_s"]:
        flags.append("SPARSE_PATH")
    out = {"p0": p0, "p0_start": float(ref[0]), "t_entry": te, "path_candles": len(path), "max_gap_s": max_gap,
           "first_touch_start": None, "touch_volume_usd": None, "label_tie_positive": None, "other_pools": None}
    path_seen = absence_evidenced(read, te, te + H)
    wick = C.ACCEPTANCE["label_sensitivities"]["wick_volume_usd"]
    if "upper" in tg:
        U, L = p0 * tg["upper"], p0 * tg["lower"]
        cls = None
        for c in path:
            up, lo = c[2] >= U, c[3] <= L
            if up or lo:
                cls = "AMBIGUOUS_BAR" if (up and lo) else ("TARGET_FIRST" if up else "INVALIDATION_FIRST")
                out.update(first_touch_start=float(c[0]), touch_volume_usd=float(c[5]))
                if c[5] < wick:
                    flags.append("WICK_TOUCH")
                break
        if cls is None:
            if not path_seen:
                return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "label_class": None, "label": None, "flags": flags,
                              "detail": "PATH_NOT_EVIDENCED"}
            cls = "NEITHER" if path else "NO_TRADES_AFTER_ENTRY"
        label = 1 if cls in tg["positive"] else 0
        out["label_tie_positive"] = 1 if cls == "AMBIGUOUS_BAR" else label
        return out | {"state": "LABELED", "label_class": cls, "label": label, "flags": flags, "detail": None}
    # T2: drawdown to half within 24 h, or a halt from t_entry + 18 h to t_entry + 48 h on the reference and other pools
    Dd = p0 * tg["drawdown"]
    s, e = halt_span(decision_time)
    ref_trade = any(in_span(c, s, e) for c in read.candles)
    ref_quiet = (not ref_trade) and absence_evidenced(read, s, e)
    if ref_quiet:
        flags.append("HALT_ON_REFERENCE_POOL")
    for c in path:
        if c[3] <= Dd:
            out.update(first_touch_start=float(c[0]), touch_volume_usd=float(c[5]))
            if c[5] < wick:
                flags.append("WICK_TOUCH")
            return out | {"state": "LABELED", "label_class": "DRAWDOWN_50", "label": 1, "flags": flags, "detail": None,
                          "label_tie_positive": 1}
    if not path_seen:
        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "label_class": None, "label": None, "flags": flags,
                      "detail": "PATH_NOT_EVIDENCED"}
    if ref_trade:
        return out | {"state": "LABELED", "label_class": "NO_SEVERE_EVENT", "label": 0, "flags": flags, "detail": None,
                      "label_tie_positive": 0}
    if not ref_quiet:
        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "label_class": None, "label": None, "flags": flags,
                      "detail": "HALT_NOT_EVIDENCED_ON_REFERENCE_POOL"}
    if other_reads is None:
        return out | {"state": NEEDS_OTHER_POOLS, "label_class": None, "label": None, "flags": flags, "detail": None}
    if other_reads == LIST_FAILED:
        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "label_class": None, "label": None, "flags": flags,
                      "detail": "VENDOR_POOL_LIST_FAILED"}
    seen = []
    for o in other_reads[:3]:
        if o is None or not o.ok:
            seen.append({"pool": getattr(o, "pool", None), "state": "READ_FAILED"})
        elif any(in_span(c, s, e) for c in o.candles):
            seen.append({"pool": o.pool, "state": "TRADED"})
        elif absence_evidenced(o, s, e):
            seen.append({"pool": o.pool, "state": "QUIET_EVIDENCED"})
        else:
            seen.append({"pool": o.pool, "state": "NOT_EVIDENCED"})
    out["other_pools"] = seen
    if any(x["state"] == "TRADED" for x in seen):
        return out | {"state": "LABELED", "label_class": "NO_SEVERE_EVENT", "label": 0, "flags": flags + ["HALT_ON_REFERENCE_POOL_ONLY"],
                      "detail": None, "label_tie_positive": 0}
    if any(x["state"] != "QUIET_EVIDENCED" for x in seen):
        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY", "label_class": None, "label": None, "flags": flags,
                      "detail": "OTHER_POOL_NOT_EVIDENCED"}
    return out | {"state": "LABELED", "label_class": "TRADING_HALT", "label": 1, "flags": flags, "detail": None, "label_tie_positive": 1}


# ---------------------------------------------------------------- the whole universe
@dataclass
class Universe:
    """Inputs for build: decision dicts (store rows plus parsed snapshot, route and pool), the read per decision, the vendor
    pool list per mint (a list of pool addresses or LIST_FAILED), other-pool reads per (decision_key, pool)."""
    decisions: list[dict]
    as_of: float                       # when the build runs (a decision not read is PENDING only if its label is not matured)
    read_of: dict[str, Read | None] = field(default_factory=dict)
    other_reads: dict[str, Any] = field(default_factory=dict)


def decision_from_row(row: dict, *, vendor_pools: list[str] | str | None = None) -> dict:
    """A predictive_decisions row as a label input: snapshot parsed, route and reference pool set (PIT_RECORDED when the decision's
    own export names a pool, else the first pool of the vendor's current list, CURRENT_VENDOR_LIST)."""
    rj = json.loads(row["row_json"]) if isinstance(row.get("row_json"), str) else (row.get("row_json") or {})
    snap = D._snap(rj)
    tok = json.loads(row["token_json"]) if row.get("token_json") else {}
    pool, route = row.get("pool_address"), "PIT_RECORDED"
    if not pool:
        route = "CURRENT_VENDOR_LIST"
        pool = vendor_pools[0] if isinstance(vendor_pools, list) and vendor_pools else None
    flags = json.loads(row["flags_json"]) if isinstance(row.get("flags_json"), str) else list(row.get("flags") or [])
    return {"decision_key": row["decision_key"], "chain": row["chain"], "mint": row["mint"], "pool": pool, "route": route,
            "decision_time": float(row["decision_time"]), "decision_time_basis": row["decision_time_basis"],
            "export_commit": row.get("export_commit"), "created_at": float(row["created_at"]), "status": row.get("status"),
            "flags": flags, "snapshot": snap, "token": tok, "row_sha256": row["row_sha256"]}


def cohort_of(dec: dict) -> dict:
    snap, tok = dec.get("snapshot") or {}, dec.get("token") or {}
    age = None
    fp = tok.get("first_pool_at")
    if isinstance(fp, str) and fp.endswith("Z"):
        try:
            age = dec["decision_time"] - C.parse_utc(fp)
        except C.ContractError:
            age = None
    liq = snap.get("liquidity")
    import datetime as _dt
    day = _dt.datetime.fromtimestamp(dec["decision_time"], _dt.UTC)
    return {"launch_age_bucket": ("UNKNOWN" if age is None or age < 0 else "lt_1d" if age < 86400 else "1d_7d" if age < 7 * 86400
                                  else "7d_30d" if age < 30 * 86400 else "ge_30d"),
            "launch_age_s": age,
            "liquidity_bucket": ("UNKNOWN" if not S._num(liq) else "lt_20k" if liq < 2e4 else "20k_100k" if liq < 1e5
                                 else "100k_1m" if liq < 1e6 else "ge_1m"),
            "liquidity_usd": liq if S._num(liq) else None,
            "day_utc": day.strftime("%Y-%m-%d"), "week_utc": day.strftime("%G-W%V"),
            "status_group": "REJECTED" if dec.get("status") == "REJECTED" else "OTHER",
            "status": dec.get("status"), "route": dec["route"] if dec.get("chain") == "solana" else "OUT_OF_SCOPE_CHAIN",
            "staleness_s": dec["decision_time"] - dec["created_at"],
            "key_conflict": "KEY_CONFLICT" in (dec.get("flags") or [])}


def groups_of(dec: dict) -> dict:
    """Group keys for later group splits (P14): the exact mint and the creator wallet of the decision's own token row."""
    cr = (dec.get("token") or {}).get("creator")
    return {"mint": dec["mint"], "creator": cr if isinstance(cr, str) and cr else None}


def build(u: Universe) -> tuple[list[dict], dict[str, str]]:
    """One label record per (decision, primary target). Returns (records, eligibility per decision_key).

    Order: scope and price, read, eligibility (contract.eligibility), thinning of eligible decisions per target and mint
    (decisions.thin, eligibility first, CC-01), split, maturity against the read's retrieval time, class."""
    elig: dict[str, str] = {}
    for d in u.decisions:
        k = d["decision_key"]
        if d.get("chain") != "solana":
            elig[k] = "OUT_OF_SCOPE_CHAIN"
        elif snapshot_price(d) is None:
            elig[k] = "NO_SNAPSHOT_PRICE"
        elif k not in u.read_of:
            # no pool resolved (no point-in-time pool and an empty or failed vendor list) is a route gap (contract.eligibility),
            # censored and counted; any other unread decision is NOT_READ (prospective, all labels pending, or a plan gap)
            no_pool = not d.get("pool") and split_of(T1B, d["decision_time"]) != "PROSPECTIVE"
            elig[k] = "VENDOR_OR_ROUTE_GAP" if no_pool else "NOT_READ"
        else:
            rd = u.read_of[k]
            if rd is not None and (rd.mint != d["mint"] or (d.get("pool") and rd.pool != d["pool"])):
                raise LabelError(f"decision {k[:12]}: its read is for another mint or pool (P01, P02)")
            elig[k] = eligibility_of(d, rd)
    out = []
    for target in TARGETS:
        eligible = [d for d in u.decisions if elig[d["decision_key"]] == "ELIGIBLE"]
        kept = {d["decision_key"] for d in D.thin(eligible, C.TARGETS[target]["horizon_s"])}
        last_kept: dict[str, str] = {}
        for d in sorted(u.decisions, key=lambda x: (x["mint"], x["decision_time"])):
            k = d["decision_key"]
            e = elig[k]
            rec = {"decision_key": k, "target": target, "target_version": C.TARGETS[target]["version"],
                   "split": split_of(target, d["decision_time"]), "eligibility": e, "thinned_by": None,
                   "label_matures_at": C.label_matures_at(target, d["decision_time"]), "read": u.read_of.get(k)}
            if e in ("OUT_OF_SCOPE_CHAIN", "NO_SNAPSHOT_PRICE", "MARKET_INACTIVE", "VENDOR_OR_ROUTE_GAP"):
                rec["state"] = e
            elif e == "NOT_READ":
                # not read: prospective, or every label of the decision was still pending when the reads were planned;
                # a matured development or holdout decision that was not read stays NOT_READ (a visible plan gap)
                rec["state"] = ("PROSPECTIVE" if rec["split"] == "PROSPECTIVE" else
                                "PENDING" if u.as_of < rec["label_matures_at"] else "NOT_READ")
            elif k not in kept:
                rec["state"], rec["thinned_by"] = "THINNED", last_kept.get(d["mint"])
            else:
                last_kept[d["mint"]] = k
                rd = u.read_of[k]
                if rec["split"] in ("PURGED", "PROSPECTIVE"):
                    rec["state"] = rec["split"]
                elif rd.retrieved_at < rec["label_matures_at"]:
                    rec["state"] = "PENDING"
                else:
                    rec.update(classify(target, d["decision_time"], rd, u.other_reads.get(k) if target == T2 else None))
                    sp = snapshot_price(d)
                    if rec.get("p0") and sp and not (P0_SNAPSHOT_RATIO[0] <= rec["p0"] / sp <= P0_SNAPSHOT_RATIO[1]):
                        rec["flags"] = list(rec.get("flags") or []) + ["P0_FAR_FROM_SNAPSHOT_PRICE"]
            rec.setdefault("label_class", None)
            rec.setdefault("label", None)
            rec.setdefault("flags", [])
            rec["censored"] = 1 if rec["state"] in CENSORED else 0
            rec["decision"] = d
            out.append(rec)
    return out, elig


def cross_target_violations(records: Iterable[dict]) -> list[dict]:
    """Invariants between the targets of one decision when all come from the same read (CC-03 rule 4, counterexample CX-06):
    the same reference price; a T1b first touch (TARGET_FIRST, INVALIDATION_FIRST, AMBIGUOUS_BAR) is also T1's first touch,
    same class and candle (T1's path starts with T1b's); a T2 DRAWDOWN_50 (low <= 0.5 P0, so also <= 0.85 P0) means T1 touched
    a barrier at or before that candle. Returns the violations (empty: consistent)."""
    by = {(r["decision_key"], r["target"]): r for r in records if r.get("state") == "LABELED"}
    out = []
    for (k, t), r in by.items():
        others = [by.get((k, x)) for x in TARGETS if x != t and by.get((k, x)) is not None]
        for o in others:
            if o.get("p0") != r.get("p0") or o.get("p0_start") != r.get("p0_start"):
                out.append({"decision_key": k, "rule": "same reference candle", "targets": [t, o["target"]]})
        r1 = by.get((k, T1))
        if t == T1B and r1 is not None and r["label_class"] in ("TARGET_FIRST", "INVALIDATION_FIRST", "AMBIGUOUS_BAR"):
            if (r1["label_class"], r1.get("first_touch_start")) != (r["label_class"], r.get("first_touch_start")):
                out.append({"decision_key": k, "rule": "T1b first touch is T1's first touch", "targets": [T1B, T1]})
        if t == T2 and r1 is not None and r["label_class"] == "DRAWDOWN_50":
            ft = r1.get("first_touch_start")
            if ft is None or ft > r.get("first_touch_start"):
                out.append({"decision_key": k, "rule": "a 50% drawdown touches the T1 lower barrier no later", "targets": [T2, T1]})
    return out


# ---------------------------------------------------------------- label store (additive migration next to Phase 05's)
V2_UP = """
CREATE TABLE predictive_label_runs (
  id INTEGER PRIMARY KEY,
  run_key TEXT NOT NULL UNIQUE,
  labels_version TEXT NOT NULL,
  registry_sha TEXT NOT NULL,             -- contract.registry_sha256() when the run was made
  export_ref TEXT NOT NULL,
  params_json TEXT NOT NULL,
  recorded_at REAL NOT NULL
);

CREATE TABLE predictive_labels (            -- development, purged and prospective records; HOLDOUT rows never enter this table
  id INTEGER PRIMARY KEY,
  label_key TEXT NOT NULL UNIQUE,         -- sha256 of (decision_key, target, target_version, labels_version, response_key, revision_of)
  run_key TEXT NOT NULL REFERENCES predictive_label_runs(run_key),
  decision_key TEXT NOT NULL,
  chain TEXT COLLATE BINARY, mint TEXT NOT NULL COLLATE BINARY, pool_address TEXT COLLATE BINARY,
  route TEXT CHECK (route IS NULL OR route IN ('PIT_RECORDED','CURRENT_VENDOR_LIST')),
  target TEXT NOT NULL, target_version TEXT NOT NULL, labels_version TEXT NOT NULL, registry_sha TEXT NOT NULL,
  split TEXT NOT NULL CHECK (split IN ('DEVELOPMENT','PURGED','PROSPECTIVE')),
  state TEXT NOT NULL CHECK (state IN ('LABELED','PENDING','PURGED','THINNED','MARKET_INACTIVE','VENDOR_OR_ROUTE_GAP',
                                       'UNVERIFIABLE_NO_VENDOR_HISTORY','NO_SNAPSHOT_PRICE','OUT_OF_SCOPE_CHAIN','PROSPECTIVE','NOT_READ')),
  label_class TEXT, label INTEGER CHECK (label IS NULL OR label IN (0, 1)),
  censored INTEGER NOT NULL CHECK (censored IN (0, 1)),
  eligibility TEXT NOT NULL, thinned_by TEXT,
  decision_time REAL NOT NULL, decision_time_basis TEXT NOT NULL CHECK (decision_time_basis IN ('EXPORT_COMMIT','CAPTURE_TIME')),
  export_commit TEXT,
  t_entry REAL, p0 REAL, p0_start REAL, first_touch_start REAL, touch_volume_usd REAL,
  label_matures_at REAL NOT NULL,
  label_observed_at REAL,                 -- retrieval time of the read the label used; never a historical availability claim
  response_key TEXT, request_url TEXT, body_sha256 TEXT,
  other_pools_json TEXT, flags_json TEXT NOT NULL, caveats_json TEXT NOT NULL, groups_json TEXT NOT NULL,
  cohort_json TEXT NOT NULL, sensitivity_json TEXT NOT NULL, detail TEXT,
  revision_of TEXT,                       -- label_key this row revises (a re-read changed a candle the label used)
  revision_reason TEXT,
  recorded_at REAL NOT NULL,
  CHECK ((state = 'LABELED') = (label IS NOT NULL)),
  CHECK ((state = 'LABELED') = (label_class IS NOT NULL)),
  CHECK (state <> 'LABELED' OR (label_observed_at IS NOT NULL AND label_observed_at >= label_matures_at)),
  CHECK (state <> 'LABELED' OR (response_key IS NOT NULL AND p0 IS NOT NULL AND t_entry IS NOT NULL)),
  CHECK (censored = (state IN ('VENDOR_OR_ROUTE_GAP','UNVERIFIABLE_NO_VENDOR_HISTORY'))),
  CHECK (revision_of IS NULL OR revision_reason IS NOT NULL)
);
CREATE INDEX ix_pl_target ON predictive_labels(target, split, state);
CREATE INDEX ix_pl_decision ON predictive_labels(decision_key, target);
""" + "".join(S._append_only(t) for t in ("predictive_label_runs", "predictive_labels"))
V2_DOWN = "DROP TABLE IF EXISTS predictive_labels;\nDROP TABLE IF EXISTS predictive_label_runs;\n"
LABEL_MIGRATIONS = [(2, "outcome label registry", V2_UP, V2_DOWN)]
LABEL_TABLES = ("predictive_label_runs", "predictive_labels")


def all_migrations() -> list:
    return list(S.MIGRATIONS) + LABEL_MIGRATIONS


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """The private store with the Phase 05 migration and this phase's label migration (store.connect refuses the lab DB)."""
    con = S.connect(path, migrate_schema=False)
    S.migrate(con, migrations=all_migrations())
    return con


def rollback_labels(con: sqlite3.Connection) -> list[int]:
    """Undo the label migration only; the Phase 05 tables stay."""
    return S.rollback(con, target=1, migrations=all_migrations())


def _check_names(rec: dict) -> None:
    for k in rec:
        if any(w in str(k).lower() for w in FORBIDDEN_NAME_WORDS):
            raise LabelError(f"field {k}: a price-path label carries no profit, return or exit field (P44)")


def record_row(rec: dict, *, run_key: str, registry_sha: str, now: float) -> dict:
    """The predictive_labels row of one build record (development, purged or prospective only)."""
    if rec["split"] == "HOLDOUT":
        raise LabelError("holdout labels never enter the label table: they are written to the sealed file only")
    d, rd = rec["decision"], rec.get("read")
    row = {
        "label_key": sha([rec["decision_key"], rec["target"], rec["target_version"], LABELS_VERSION,
                          rd.response_key if rd is not None else None, rec.get("revision_of")]),
        "run_key": run_key, "decision_key": rec["decision_key"], "chain": d.get("chain"), "mint": d["mint"],
        "pool_address": d.get("pool"), "route": d.get("route") if d.get("chain") == "solana" else None,
        "target": rec["target"], "target_version": rec["target_version"], "labels_version": LABELS_VERSION, "registry_sha": registry_sha,
        "split": rec["split"], "state": rec["state"], "label_class": rec.get("label_class"), "label": rec.get("label"),
        "censored": rec["censored"], "eligibility": rec["eligibility"], "thinned_by": rec.get("thinned_by"),
        "decision_time": d["decision_time"], "decision_time_basis": d["decision_time_basis"], "export_commit": d.get("export_commit"),
        "t_entry": rec.get("t_entry"), "p0": rec.get("p0"), "p0_start": rec.get("p0_start"),
        "first_touch_start": rec.get("first_touch_start"), "touch_volume_usd": rec.get("touch_volume_usd"),
        "label_matures_at": rec["label_matures_at"],
        "label_observed_at": rd.retrieved_at if rd is not None else None,
        "response_key": rd.response_key if rd is not None else None, "request_url": rd.url if rd is not None else None,
        "body_sha256": rd.body_sha256 if rd is not None else None,
        "other_pools_json": canon(rec.get("other_pools")) if rec.get("other_pools") is not None else None,
        "flags_json": canon(sorted(set(rec.get("flags") or []) | ({"KEY_CONFLICT"} if "KEY_CONFLICT" in (d.get("flags") or []) else set())
                                   | ({"CURRENT_VENDOR_LIST"} if d.get("route") == "CURRENT_VENDOR_LIST" else set()))),
        "caveats_json": canon(list(CAVEATS)), "groups_json": canon(groups_of(d)), "cohort_json": canon(cohort_of(d)),
        "sensitivity_json": canon({"label_tie_positive": rec.get("label_tie_positive"),
                                   "conservative_lens": (0 if rec["target"] != T2 else 1) if rec["censored"] else rec.get("label")}),
        "detail": rec.get("detail"), "revision_of": rec.get("revision_of"), "revision_reason": rec.get("revision_reason"),
        "recorded_at": float(now)}
    _check_names(row)
    return row


def store_labels(con: sqlite3.Connection, records: list[dict], *, export_ref: str, params: dict, now: float) -> dict:
    reg = C.registry_sha256()
    run_key = sha([LABELS_VERSION, reg, export_ref, params])
    S._insert(con, "predictive_label_runs", {"run_key": run_key, "labels_version": LABELS_VERSION, "registry_sha": reg,
                                             "export_ref": export_ref, "params_json": canon(params), "recorded_at": float(now)})
    added = 0
    for rec in records:
        if rec["split"] == "HOLDOUT":
            continue
        added += _insert_strict(con, "predictive_labels", record_row(rec, run_key=run_key, registry_sha=reg, now=now))
    return {"run_key": run_key, "added": added}


def _insert_strict(con: sqlite3.Connection, table: str, row: dict) -> bool:
    """Idempotent on label_key, but a CHECK violation raises (store._insert's INSERT OR IGNORE would drop the row silently)."""
    if con.execute(f"SELECT 1 FROM {table} WHERE label_key=?", (row["label_key"],)).fetchone():
        return False
    cols = list(row)
    con.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row[c] for c in cols])
    return True


def sealed_row(rec: dict) -> dict:
    """The sealed-file line of one holdout record: the same fields as a table row, split HOLDOUT."""
    rr = dict(rec, split="PURGED")              # reuse the row builder, then restore the split
    row = record_row(rr, run_key="sealed", registry_sha=C.registry_sha256(), now=0.0)
    row.update(split="HOLDOUT", run_key=None, recorded_at=None)
    row["holdout_contacted"] = [rec["decision"]["mint"], _iso(rec["decision"]["decision_time"])] in C.ACCEPTANCE["holdout_contacted"]["decisions"]
    return row


def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- revisions (P07, PI-D-018)
def revision_changes(first: Read, second: Read, *, min_gap_s: float | None = None, older_than_s: float | None = None) -> dict:
    """Compare two reads of one pool. A position present in both whose values differ, or present in one read and absent from the
    other although that read covered it, is a revision. Only reads at least `min_gap_s` apart (ACCEPTANCE revision_reread_min_gap_s,
    48 h) and positions that ended at least `older_than_s` (48 h) before the second read count as the frozen revision check;
    shorter gaps are measured and reported as such."""
    lim = C.ACCEPTANCE["api_limits"]
    gap_req = lim["revision_reread_min_gap_s"] if min_gap_s is None else min_gap_s
    old_req = lim["revision_reread_min_gap_s"] if older_than_s is None else older_than_s
    if first.pool != second.pool or first.mint != second.mint:
        raise LabelError("a revision compares two reads of the same pool and mint (P02)")
    gap = second.retrieved_at - first.retrieved_at
    a, b = {c[0]: c for c in first.candles}, {c[0]: c for c in second.candles}
    lo = max(first.cover_from or math.inf, second.cover_from or math.inf)
    hi = min(first.boundary, second.boundary)
    changed, appeared, vanished, same = [], [], [], 0
    for t in sorted(set(a) | set(b)):
        if not (t >= lo and t + PERIOD_S <= hi) or t + PERIOD_S > second.retrieved_at - old_req:
            continue
        if t in a and t in b:
            if a[t][1:] == b[t][1:]:
                same += 1
            else:
                changed.append({"start": t, "fields": "".join(f for f, i in zip("ohlcv", range(1, 6)) if a[t][i] != b[t][i])})
        elif t in b:
            appeared.append(t)
        else:
            vanished.append(t)
    return {"gap_s": gap, "frozen_check": gap >= gap_req, "compared": same + len(changed), "unchanged": same,
            "changed": changed, "appeared": appeared, "vanished": vanished}


def revise(rec: dict, new_read: Read, *, reason: str) -> dict | None:
    """Recompute one LABELED record from a later read. Returns a revision record (both versions are kept in the store) when the
    class or the reference price changes, else None."""
    if rec["state"] != "LABELED":
        return None
    d = rec["decision"]
    if C.reference_candle(list(new_read.candles), d["decision_time"]) is None or new_read.boundary < needed_boundary(rec["target"], d["decision_time"]):
        return None
    new = classify(rec["target"], d["decision_time"], new_read, rec.get("other_reads_used"))
    if new["state"] == rec["state"] and new.get("label_class") == rec.get("label_class") and new.get("p0") == rec.get("p0"):
        return None
    out = {k: v for k, v in rec.items() if k not in new} | new
    out.update(read=new_read, revision_of=rec.get("label_key"), revision_reason=reason, flags=sorted(set(new.get("flags") or []) | {"REVISED"}))
    return out


# ---------------------------------------------------------------- the holdout seal
def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_manifest(paths: Iterable[str | Path], root: str | Path) -> dict:
    """sha256 and size of every sealed file, by path relative to root. Hashing reads bytes only; nothing is parsed or shown."""
    root = Path(root)
    return {Path(p).resolve().relative_to(root.resolve()).as_posix(): {"sha256": file_sha256(p), "bytes": Path(p).stat().st_size}
            for p in sorted(paths)}


def verify_seal(manifest: dict, root: str | Path) -> list[str]:
    """Problems with a seal (empty: every listed file exists with its recorded sha256 and size)."""
    probs = []
    for rel, meta in sorted(manifest.items()):
        p = Path(root) / rel
        if not p.exists():
            probs.append(f"{rel}: missing")
        elif p.stat().st_size != meta["bytes"] or file_sha256(p) != meta["sha256"]:
            probs.append(f"{rel}: sha256 or size differs from the seal")
    return probs


# ---------------------------------------------------------------- the phase gate: mature-only training labels
def refuse_sealed(path: str | Path | None) -> None:
    if path is not None and SEALED_DIR in Path(path).resolve().as_posix():
        raise LabelError(f"{path}: the sealed holdout is opened once in Phase 12, never read as training data")


def _db_paths(con: sqlite3.Connection) -> list[str]:
    return [r[2] for r in con.execute("PRAGMA database_list") if r[2]]


def training_labels(con: sqlite3.Connection, as_of: float, target: str, *, mode: str = "provider",
                    include_key_conflict: bool = True) -> list[dict]:
    """Labels a model trained as of `as_of` may use: DEVELOPMENT, LABELED (never PENDING, censored, thinned, purged or sealed),
    matured by `as_of`. Split and maturity are recomputed from the decision time and the frozen registry, never taken from the
    stored columns (a stored row that disagrees raises). Every version of a (decision, target) is considered: the newest one
    available by `as_of` decides, so a revision that leaves LABELED removes the label from training (a revised row is available
    from its own read, the original from its maturity). Mode 'capture' also requires label_observed_at <= as_of (what the lab
    actually held then); 'provider' is the reconstruction. The store file must not be the sealed holdout or bake-off data."""
    if target not in TARGETS:
        raise LabelError(f"{target} is not a primary target")
    if mode not in ("provider", "capture"):
        raise LabelError("mode is provider or capture")
    for p in _db_paths(con):
        refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    rows = S.iter_rows(con, "SELECT * FROM predictive_labels WHERE target=? ORDER BY decision_key, id", (target,))
    R.refuse_bakeoff_labels(rows)
    best: dict[str, tuple[float, int, dict]] = {}
    for r in rows:
        if r["target_version"] != C.TARGETS[target]["version"]:
            raise LabelError(f"row {r['label_key'][:12]} has target version {r['target_version']}, not the registry's")
        split = split_of(target, r["decision_time"])
        mat = C.label_matures_at(target, r["decision_time"])
        if r["split"] != split or abs(float(r["label_matures_at"]) - mat) > 1e-6:
            raise LabelError(f"row {r['label_key'][:12]}: stored split or maturity disagrees with the registry "
                             f"({r['split']} vs {split})")
        if split != "DEVELOPMENT":
            continue
        avail = mat if r["revision_of"] is None else max(float(r["label_observed_at"] or math.inf), mat)
        if mode == "capture":
            avail = max(avail, float(r["label_observed_at"] or math.inf))
        if avail > as_of:
            continue
        cur = best.get(r["decision_key"])
        if cur is None or (avail, r["id"]) >= (cur[0], cur[1]):
            best[r["decision_key"]] = (avail, r["id"], r)
    out = []
    for _, _, r in best.values():
        if r["state"] != "LABELED" or r["censored"] or r["label"] not in (0, 1):
            continue
        if not include_key_conflict and "KEY_CONFLICT" in json.loads(r["flags_json"]):
            continue
        C.assert_scorable({"label": r["label"], "target": target, "decision_time": r["decision_time"], "label_status": r["state"],
                           "label_observed_at": r["label_observed_at"], "forecast_id": r["label_key"]}, as_of)
        out.append(r)
    return sorted(out, key=lambda r: (r["decision_time"], r["mint"]))

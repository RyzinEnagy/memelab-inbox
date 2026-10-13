"""Phase 16: immutable signal ledger and forward outcome evaluation (pure engine: no I/O, no clock).

A research signal is recorded once, at emission, with what the lab knew then (signal_context). That record is never
rewritten. Market outcomes are measured later, per horizon (1h, 6h, 24h, 72h, 7d by default), from dated price
observations, and appended as new outcome entries. The ledger module (outcomes_ledger.py) stores both; this module
only builds a context and computes one outcome from the observations visible at an evaluation time.

Rules (DECISIONS D-105 to D-111):
  - Look-ahead: the context keeps only market facts dated at or before generated_at. An outcome uses only observations
    the lab had at the evaluation time (available_at <= as_of), the entry is placed at generated_at + execution lag
    (never at the earlier event time), and nothing before the entry or after the exit window counts.
  - A return needs a dated price at the entry and at the exit. No price, no return: the outcome is MISSING with a
    reason, never filled in. A route quote is not a midpoint and never stands in for one.
  - Max favourable / adverse excursion needs a path with no gap wider than horizon / path_max_gap_divisor.
  - Three return figures are kept apart: return_mid_gross (displayed price move, not proceeds), return_net_modeled
    (fees, slippage and constant-product impact at the hypothetical size) and return_net_quoted (exit from an actual
    route quote). Displayed P&L is never reported as proceeds.
  - Status per (signal, horizon): PENDING, MEASURED, MISSING, NON_EXECUTABLE or INVALIDATED, always with reasons.
  - The position size is a hypothetical evaluation size used to model impact; it is not a recommendation and has
    zero trade execution impact.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

ENGINE_VERSION = "outcomes-v1"
CONTEXT_SCHEMA = "memelab.social.signal/1"
INPUT_SCHEMA = "memelab.social.signal.input/1"
PRICES_SCHEMA = "memelab.social.prices/1"
POLICY_SCHEMA = "memelab.social.outcomes.policy/1"

STATUSES = ("PENDING", "MEASURED", "MISSING", "NON_EXECUTABLE", "INVALIDATED")
DISPOSITIONS = ("EMITTED", "REJECTED", "SUPPRESSED", "NEEDS_REVIEW")
OBS_KINDS = ("POINT", "CANDLE", "QUOTE", "STATUS")
ANNOTATION_KINDS = ("SOURCE_DELETED", "INVALIDATED", "IDENTITY_REVISED", "NOTE")
INVALIDATING = ("INVALIDATED", "IDENTITY_REVISED")
HORIZON_NAMES = {3600: "1h", 21600: "6h", 86400: "24h", 259200: "72h", 604800: "7d"}

DEFAULT_POLICY: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "policy_version": "default-1",
    "horizons_s": [3600, 21600, 86400, 259200, 604800],
    "execution_lag_s": 300,             # hypothetical time from emission to a filled order
    "position_size_usd": 500.0,         # hypothetical evaluation size for modeled impact; not a recommendation
    "fee_bps_per_side": 100.0,
    "slippage_bps_per_side": 50.0,
    "max_participation": 0.05,          # size / pool liquidity above this: not executable at this size
    "max_entry_wait_s": 900,            # an entry may use the first price up to this long after the entry time
    "max_exit_wait_s": 900,             # same at the exit; while this window is open a missing exit stays PENDING
    "quote_max_skew_s": 120,            # a route quote or liquidity reading counts only this close to the price used
    "max_quote_gap": 0.25,              # quoted exit proceeds this far below the displayed price: displayed P&L is not executable
    "quote_above_mid_tolerance": 0.02,  # a quote paying more than the displayed price by this much is inconsistent and ignored
    "path_max_gap_divisor": 12,         # max excursion only when no gap in the path is wider than horizon / this
    "max_capture_lag_s": 3600,          # recorded more than this after generation: LATE_CAPTURE (hindsight risk)
    "max_context_price_age_s": 300,     # observed price older than this at generation: noted as stale
    "future_dated_tolerance_s": 60,     # an observation dated after the time it became available is refused
    "trade_execution_impact": "none",
}
FORBIDDEN_POLICY_KEYS = ("execute", "order", "wallet", "signing", "private_key", "seed")


class OutcomeError(ValueError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def r10(x: float | None) -> float | None:
    return None if x is None else round(float(x), 10)


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")


def hname(h: int) -> str:
    return HORIZON_NAMES.get(int(h), f"{int(h)}s")


def make_policy(override: dict | None = None) -> dict:
    pol = copy.deepcopy(DEFAULT_POLICY)
    for k, v in (override or {}).items():
        if any(b in k.lower() for b in FORBIDDEN_POLICY_KEYS):
            raise OutcomeError(f"policy key {k!r} is refused: outcome evaluation never trades")
        if k not in pol:
            raise OutcomeError(f"unknown policy key {k!r}")
        pol[k] = v
    if pol["trade_execution_impact"] != "none":
        raise OutcomeError("trade_execution_impact must be 'none'")
    hs = pol["horizons_s"]
    if not hs or any(not isinstance(h, int) or h <= pol["max_exit_wait_s"] for h in hs) or sorted(set(hs)) != list(hs):
        raise OutcomeError("horizons_s must be increasing integers longer than max_exit_wait_s")
    for k in ("execution_lag_s", "position_size_usd", "max_entry_wait_s", "max_exit_wait_s", "quote_max_skew_s"):
        if not _num(pol[k]) or pol[k] < 0:
            raise OutcomeError(f"{k} must be a non-negative number")
    pol["policy_sha256"] = sha({k: v for k, v in pol.items() if k != "policy_sha256"})
    return pol


# ---------- signal context (captured once, never rewritten) ----------

def signal_id_for(emitter: str, emitter_ref: str, chain: str | None, contract: str | None, generated_at: float) -> str:
    return "sig_" + sha([emitter, emitter_ref, chain, contract, r10(generated_at)])[:24]


def _fact_time(f: dict) -> float | None:
    t = f.get("as_of", f.get("fetched_at"))
    return float(t) if _num(t) else None


def market_at_generation(facts: list[dict], generated_at: float, pol: dict) -> tuple[dict, list[dict]]:
    """What the lab had seen of the market at generated_at. Facts dated after generation are dropped and counted."""
    kept, later = [], 0
    for f in facts or []:
        t = _fact_time(f)
        if t is None:
            continue
        if t > generated_at:
            later += 1
            continue
        kept.append(dict(f, _t=t))
    missing: list[dict] = []
    prices = [f for f in kept if f.get("field") == "price" and _num(f.get("value_num")) and f["value_num"] > 0]
    price = None
    if prices:
        newest = max(f["_t"] for f in prices)
        cands = [f for f in prices if f["_t"] == newest]
        p = next((f for f in cands if f.get("provider") == "jupiter"), None) or sorted(cands, key=lambda f: canon(f))[0]
        age = generated_at - p["_t"]
        price = {"value": p["value_num"], "unit": p.get("unit") or "USD", "provider": p.get("provider"), "as_of": p["_t"],
                 "age_s": r10(age), "fact_id": p.get("fact_id"), "stale": age > pol["max_context_price_age_s"],
                 "basis": "observed midpoint or provider price at fetch, not proceeds"}
    else:
        missing.append({"field": "observed_price", "reason": "no price fact dated at or before generation"})
    liqs = [f for f in kept if f.get("field") == "liquidity_reported" and _num(f.get("value_num"))]
    liq = None
    if liqs:
        newest = max(f["_t"] for f in liqs)
        lf = max((f for f in liqs if f["_t"] == newest), key=lambda f: f["value_num"])
        liq = {"value_usd": lf["value_num"], "provider": lf.get("provider"), "as_of": lf["_t"], "fact_id": lf.get("fact_id"),
               "basis": "reported pool liquidity, not exit depth"}
    else:
        missing.append({"field": "liquidity", "reason": "no liquidity fact dated at or before generation"})
    route = None
    sells = [f for f in kept if f.get("field") in ("sell_quote_out_usd", "sell_quote_out")]
    if sells:
        newest = max(f["_t"] for f in sells)
        s = sorted((f for f in sells if f["_t"] == newest), key=lambda f: (f.get("field") != "sell_quote_out_usd", canon(f)))[0]
        if (s.get("value_str") or "").upper() in ("NO_ROUTE", "ERROR"):
            route = {"status": s["value_str"].upper(), "size_usd": s.get("size_usd"), "as_of": s["_t"], "provider": s.get("provider"),
                     "fact_id": s.get("fact_id")}
        elif s.get("field") == "sell_quote_out_usd":
            route = {"status": "OK", "size_usd": s.get("size_usd"), "out_usd": s.get("value_num"), "as_of": s["_t"],
                     "provider": s.get("provider"), "fact_id": s.get("fact_id"), "basis": "actual route quote"}
    if route is None:
        missing.append({"field": "sell_route", "reason": "no sell route quote dated at or before generation; exit depth unknown"})
    return {"observed_price": price, "liquidity": liq, "sell_route": route, "facts_after_generation_excluded": later}, missing


def make_signal(raw: dict, pol: dict, *, captured_at: float, is_fixture: bool = False) -> dict:
    """Normalize one emitted (or rejected / suppressed) signal into its immutable context."""
    emitter = str(raw.get("emitter") or "")
    ref = str(raw.get("emitter_ref") or "")
    if not emitter or not ref:
        raise OutcomeError("a signal needs emitter and emitter_ref")
    gen = raw.get("generated_at")
    if not _num(gen):
        raise OutcomeError(f"signal {emitter}:{ref} has no generated_at: it cannot be placed in time")
    gen = float(gen)
    disp = str(raw.get("disposition") or "EMITTED").upper()
    if disp not in DISPOSITIONS:
        raise OutcomeError(f"disposition {disp!r} is not one of {DISPOSITIONS}")
    chain = (str(raw["chain"]).lower() if raw.get("chain") else None)
    contract = str(raw["contract"]) if raw.get("contract") else None
    direction = str(raw.get("direction") or "LONG").upper()
    if direction not in ("LONG", "SHORT"):
        raise OutcomeError("direction must be LONG or SHORT")
    ev = raw.get("event_time")
    ev = float(ev) if _num(ev) else None
    missing: list[dict] = []
    if not (chain and contract):
        missing.append({"field": "identity", "reason": "no exact chain and contract: outcomes cannot be measured"})
    if ev is None:
        missing.append({"field": "event_time", "reason": "event time not supplied"})
    market, mm = market_at_generation(raw.get("market") or [], gen, pol)
    missing += mm
    flags = []
    if captured_at - gen > pol["max_capture_lag_s"]:
        flags.append({"flag": "LATE_CAPTURE", "lag_s": r10(captured_at - gen),
                      "why": "recorded long after emission; the context may not be what the lab knew at that moment"})
    if captured_at < gen:
        raise OutcomeError(f"signal {emitter}:{ref} generated after it was recorded ({gen} > {captured_at})")
    if ev is not None and ev > gen:
        flags.append({"flag": "EVENT_AFTER_GENERATION", "why": "the event time is later than the signal: clock or capture error"})
    sid = signal_id_for(emitter, ref, chain, contract, gen)
    ctx = {
        "schema": CONTEXT_SCHEMA, "signal_id": sid, "emitter": emitter, "emitter_ref": ref,
        "disposition": disp, "disposition_reason": raw.get("disposition_reason"),
        "versions": {"classifier": raw.get("classifier_version"), "scoring": raw.get("scoring_version"),
                     "policy": raw.get("policy_version"), "ledger_engine": ENGINE_VERSION},
        "references": raw.get("references") or {},
        "token": {"chain": chain, "contract": contract, "symbol_display_only": raw.get("symbol")},
        "times": {"event_time": ev, "generated_at": gen, "captured_at": captured_at,
                  "publication_delay_s": None if ev is None else r10(gen - ev)},
        "market_at_generation": market,
        "assumptions": {"direction": direction, "horizons_s": list(pol["horizons_s"]), "execution_lag_s": pol["execution_lag_s"],
                        "position_size_usd": pol["position_size_usd"], "position_size_note": "hypothetical evaluation size, not a recommendation",
                        "fee_bps_per_side": pol["fee_bps_per_side"], "slippage_bps_per_side": pol["slippage_bps_per_side"],
                        "max_participation": pol["max_participation"], "policy_version": pol["policy_version"],
                        "policy_sha256": pol["policy_sha256"]},
        "missing": missing, "flags": flags, "is_fixture": bool(is_fixture or raw.get("is_fixture")),
        "trade_execution_impact": "none",
    }
    return ctx


def signals_from_feed(doc: dict, *, generated_at: float | None = None) -> list[dict]:
    """Phase 14 feed items as signals. Every item is kept (theme items carry no identity and stay unmeasurable)."""
    gen = float(generated_at if generated_at is not None else doc["as_of"])
    out = []
    for it in doc.get("items") or []:
        facts = [{"field": f.get("field"), "value_num": f.get("value_num"), "value_str": f.get("value_str"), "unit": f.get("unit"),
                  "provider": f.get("provider"), "fetched_at": f.get("fetched_at"), "fact_id": f.get("fact_id")}
                 for f in (it.get("liquidity") or {}).get("facts") or []]
        prov = it.get("provenance") or {}
        out.append({
            "emitter": "feed", "emitter_ref": it["item_id"], "disposition": "EMITTED",
            "disposition_reason": f"feed priority {it.get('priority')} ({it.get('priority_bucket')})",
            "classifier_version": doc.get("engine_version"), "scoring_version": doc.get("engine_version"),
            "policy_version": doc.get("feed_sha256"),
            "chain": it.get("chain") if it.get("kind") == "CONTRACT" else None,
            "contract": it.get("contract") if it.get("kind") == "CONTRACT" else None, "symbol": it.get("symbol"),
            "event_time": (it.get("times") or {}).get("earliest_published_at"), "generated_at": gen,
            "references": {"claims": prov.get("claims") or [], "sources": it.get("sources") or [],
                           "narrative_run_id": prov.get("narrative_run_id"), "chronology_runs": prov.get("chronology_runs") or [],
                           "market_fact_ids": prov.get("market_fact_ids") or [], "cluster_key": prov.get("cluster_key")},
            "market": facts, "is_fixture": bool(it.get("is_fixture") or doc.get("fixture")),
        })
    return out


_RESEARCH_DISP = {"RESEARCH_CANDIDATE": "EMITTED", "REJECTED_STRUCTURE": "REJECTED", "NEEDS_STRUCTURAL_ANALYSIS": "NEEDS_REVIEW",
                  "NO_SOCIAL_SIGNAL": "NEEDS_REVIEW"}


def signals_from_research(section: dict, *, generated_at: float | None = None) -> list[dict]:
    """Phase 13 research candidates as signals, rejected ones included (no cherry-picking)."""
    gen = float(generated_at if generated_at is not None else section["as_of"])
    out = []
    for c in section.get("candidates") or []:
        tl = c.get("timeline_evidence") or []
        ev = min((x.get("at") for x in tl if _num(x.get("at"))), default=None)
        out.append({
            "emitter": "research", "emitter_ref": f"{c['chain']}:{c['contract']}", "disposition": _RESEARCH_DISP.get(c["research_state"], "NEEDS_REVIEW"),
            "disposition_reason": c["research_state"], "classifier_version": section.get("engine_version"),
            "scoring_version": (section.get("policy") or {}).get("policy_version"), "policy_version": section.get("result_sha256"),
            "chain": c["chain"], "contract": c["contract"], "symbol": c.get("symbol"), "event_time": ev, "generated_at": gen,
            "references": {"provenance": c.get("provenance") or []}, "market": [], "is_fixture": bool(c.get("is_fixture")),
        })
    return out


# ---------- observations ----------

def normalize_observation(o: dict, pol: dict) -> dict:
    """One dated market observation. Refused (OutcomeError) when it cannot be placed in time or claims a future price."""
    kind = str(o.get("kind") or "").upper()
    if kind not in OBS_KINDS:
        raise OutcomeError(f"observation kind {kind!r} is not one of {OBS_KINDS}")
    chain, contract = str(o.get("chain") or "").lower(), str(o.get("contract") or "")
    if not chain or not contract:
        raise OutcomeError("an observation needs chain and contract")
    t, av = o.get("t"), o.get("available_at")
    if not _num(t) or not _num(av):
        raise OutcomeError("an observation needs t (when the price applied) and available_at (when the lab had it)")
    if float(t) > float(av) + pol["future_dated_tolerance_s"]:
        raise OutcomeError(f"observation dated {t} after it became available ({av}): future-dated, refused")
    if not o.get("provider"):
        raise OutcomeError("an observation needs a provider")
    body = {"kind": kind, "chain": chain, "contract": contract, "t": float(t), "available_at": float(av), "provider": str(o["provider"]),
            "source_key": o.get("source_key"), "pair": o.get("pair"), "is_fixture": bool(o.get("is_fixture"))}
    if kind == "CANDLE":
        per = o.get("period_s")
        if not (isinstance(per, int) and per > 0):
            raise OutcomeError("a candle needs an integer period_s")
        vals = [o.get(k) for k in ("o", "h", "l", "c")]
        if all(_num(v) and v > 0 for v in vals):
            if o["h"] < max(o["o"], o["c"]) or o["l"] > min(o["o"], o["c"]):
                raise OutcomeError("candle high/low do not contain open and close")
            body.update(period_s=per, o=float(o["o"]), h=float(o["h"]), l=float(o["l"]), c=float(o["c"]))
        else:
            body.update(period_s=per, o=None, h=None, l=None, c=None)   # a candle without a usable midpoint
        if float(t) + per > float(av) + pol["future_dated_tolerance_s"]:
            raise OutcomeError("candle closes after it became available: not a finished candle, refused")
    elif kind == "POINT":
        p = o.get("price")
        body["price"] = float(p) if _num(p) and p > 0 else None
    elif kind == "STATUS":
        st = str(o.get("status") or "").upper()
        if st not in ("DELISTED", "LISTED"):
            raise OutcomeError("a STATUS observation needs status DELISTED or LISTED")
        body["status"] = st
    if o.get("liquidity_usd") is not None:
        if not _num(o["liquidity_usd"]) or o["liquidity_usd"] < 0:
            raise OutcomeError("liquidity_usd must be a non-negative number")
        body["liquidity_usd"] = float(o["liquidity_usd"])
    for side in ("sell_quote", "buy_quote"):
        q = o.get(side)
        if q:
            st = str(q.get("status") or "OK").upper()
            if st not in ("OK", "NO_ROUTE", "ERROR"):
                raise OutcomeError(f"{side}.status must be OK, NO_ROUTE or ERROR")
            if not _num(q.get("size_usd")) or q["size_usd"] <= 0:
                raise OutcomeError(f"{side} needs size_usd")
            qq = {"status": st, "size_usd": float(q["size_usd"])}
            if st == "OK":
                if not _num(q.get("out_usd")) or q["out_usd"] < 0:
                    raise OutcomeError(f"{side} OK needs out_usd")
                qq["out_usd"] = float(q["out_usd"])
            body[side] = qq
    body["series_key"] = sha([kind, chain, contract, body["provider"], body.get("pair"), body.get("period_s"), body["t"],
                              None if kind != "QUOTE" else [side for side in ("sell_quote", "buy_quote") if body.get(side)]])
    return body


def visible(observations: list[dict], chain: str, contract: str, as_of: float) -> list[dict]:
    """Observations of this token the lab had at as_of. A revised snapshot (same series, later available_at)
    replaces the earlier one from the moment it was available; before that the earlier one stands."""
    best: dict[str, dict] = {}
    for o in observations:
        if o["chain"] != chain or o["contract"] != contract or o["available_at"] > as_of:
            continue
        cur = best.get(o["series_key"])
        if cur is None or (o["available_at"], o.get("seq", 0)) > (cur["available_at"], cur.get("seq", 0)):
            best[o["series_key"]] = o
    return sorted(best.values(), key=lambda o: (o["t"], o["kind"], o["provider"], o.get("seq", 0)))


def _prices(obs: list[dict]) -> list[tuple[float, float, str, dict]]:
    """(time, price, basis, observation) for every dated midpoint. A candle gives its open at its start and its close
    at its end, so no price is ever taken from before the time it applied."""
    out = []
    for o in obs:
        if o["kind"] == "POINT" and o.get("price") is not None:
            out.append((o["t"], o["price"], "POINT", o))
        elif o["kind"] == "CANDLE" and o.get("o") is not None:
            out.append((o["t"], o["o"], "CANDLE_OPEN", o))
            out.append((o["t"] + o["period_s"], o["c"], "CANDLE_CLOSE", o))
    return sorted(out, key=lambda x: (x[0], x[2], x[3].get("seq", 0)))


def _price_at(obs: list[dict], t: float, wait: float) -> tuple[dict | None, float | None, float | None, str]:
    """First dated midpoint at or after t, within wait. Never an earlier price. Returns (obs, price, time, basis)."""
    for pt, p, basis, o in _prices(obs):
        if t <= pt <= t + wait:
            return o, p, pt, basis
    near = [o for o in obs if o["kind"] in ("POINT", "CANDLE", "QUOTE") and
            (t <= o["t"] <= t + wait or (o["kind"] == "CANDLE" and o["t"] <= t + wait and o["t"] + o["period_s"] >= t))]
    return None, None, None, "MISSING_MIDPOINT" if near else "NO_PRICE"


def _near(obs: list[dict], t: float, skew: float, key: str) -> dict | None:
    c = [o for o in obs if o.get(key) is not None and abs(o["t"] - t) <= skew]
    return min(c, key=lambda o: (abs(o["t"] - t), o["t"], o.get("seq", 0))) if c else None


# ---------- one outcome ----------

def evaluate(ctx: dict, horizon_s: int, observations: list[dict], annotations: list[dict], as_of: float, pol: dict) -> dict:
    """Outcome of one signal at one horizon from what was visible at as_of. Deterministic."""
    sid = ctx["signal_id"]
    gen = ctx["times"]["generated_at"]
    a = ctx["assumptions"]
    t_entry = gen + a["execution_lag_s"]
    t_exit = t_entry + horizon_s
    out: dict[str, Any] = {"signal_id": sid, "horizon_s": int(horizon_s), "horizon": hname(horizon_s),
                           "target": {"entry_t": t_entry, "exit_t": t_exit}, "reasons": [], "flags": [], "inputs": [],
                           "entry": None, "exit": None, "returns": None, "excursion": None,
                           "engine_version": ENGINE_VERSION, "policy_sha256": pol["policy_sha256"], "is_fixture": bool(ctx.get("is_fixture"))}

    def done(status: str, *reasons: dict) -> dict:
        out["status"] = status
        out["reasons"] += list(reasons)
        out["inputs"] = sorted(set(out["inputs"]))
        return out

    anns = [x for x in annotations if x["signal_id"] == sid and x["available_at"] <= as_of]
    for x in sorted(anns, key=lambda x: (x["available_at"], x.get("seq", 0))):
        if x["kind"] == "SOURCE_DELETED":
            out["flags"].append({"flag": "SOURCE_DELETED", "at": x.get("at"), "note": "the source was removed after emission; the signal and its outcomes stay"})
    inval = [x for x in anns if x["kind"] in INVALIDATING]
    if inval:
        return done("INVALIDATED", *[{"code": x["kind"], "why": x.get("reason"), "annotation_seq": x.get("seq")} for x in inval])
    if any(f.get("flag") == "EVENT_AFTER_GENERATION" for f in ctx.get("flags") or []):
        return done("INVALIDATED", {"code": "EVENT_AFTER_GENERATION", "why": "event time later than the signal"})
    tok = ctx["token"]
    if not (tok.get("chain") and tok.get("contract")):
        return done("MISSING", {"code": "UNRESOLVED_IDENTITY", "why": "no exact chain and contract were known at emission"})
    if as_of < t_exit:
        return done("PENDING", {"code": "HORIZON_NOT_MATURED", "why": f"matures at {t_exit:.0f}", "matures_at": t_exit})
    obs = [o for o in visible(observations, tok["chain"], tok["contract"], as_of) if o["t"] <= max(t_exit + pol["max_exit_wait_s"], as_of)]
    # delisting before the exit: no exit price is invented
    dl_all = [o for o in obs if o["kind"] == "STATUS" and o["status"] == "DELISTED"]
    if dl_all:   # nothing after a delisting is a tradable price
        obs = [o for o in obs if o["t"] < dl_all[0]["t"] or o is dl_all[0]]
    dl = [o for o in dl_all if o["t"] <= t_exit]
    if dl:
        d0 = dl[0]
        out["inputs"].append(d0.get("seq"))
        last = [x for x in _prices(obs) if x[0] < d0["t"]]
        out["exit"] = {"last_seen_price": last[-1][1] if last else None, "last_seen_t": last[-1][0] if last else None,
                       "delisted_at": d0["t"], "basis": "last observed price before delisting; no exit was observed"}
        code = "DELISTED_BEFORE_ENTRY" if d0["t"] <= t_entry else "TOKEN_DELISTED_BEFORE_EXIT"
        return done("NON_EXECUTABLE", {"code": code, "why": "the token was delisted; no exit price exists and none is assumed"})
    eo, ep, entry_t, ebasis = _price_at(obs, t_entry, pol["max_entry_wait_s"])
    if eo is None:
        code = "MISSING_MIDPOINT_AT_ENTRY" if ebasis == "MISSING_MIDPOINT" else "NO_ENTRY_PRICE"
        return done("MISSING", {"code": code, "why": "no dated midpoint at the entry time; a route quote is not a midpoint"})
    out["inputs"].append(eo.get("seq"))
    xo, xp, exit_t, xbasis = _price_at(obs, t_exit, pol["max_exit_wait_s"])
    if xo is None:
        if as_of < t_exit + pol["max_exit_wait_s"]:
            return done("PENDING", {"code": "EXIT_WINDOW_OPEN", "why": "no exit price yet and the exit window is still open",
                                    "window_closes_at": t_exit + pol["max_exit_wait_s"]})
        code = "MISSING_MIDPOINT_AT_EXIT" if xbasis == "MISSING_MIDPOINT" else "NO_EXIT_PRICE"
        return done("MISSING", {"code": code, "why": "no dated midpoint at the exit time; no exit is assumed"})
    out["inputs"].append(xo.get("seq"))
    d = 1 if a["direction"] == "LONG" else -1
    size = float(a["position_size_usd"])
    base = (a["fee_bps_per_side"] + a["slippage_bps_per_side"]) / 1e4
    skew = pol["quote_max_skew_s"]
    le = eo if eo.get("liquidity_usd") is not None else _near(obs, entry_t, skew, "liquidity_usd")
    lx = xo if xo.get("liquidity_usd") is not None else _near(obs, exit_t, skew, "liquidity_usd")
    sq = xo if xo.get("sell_quote") else _near(obs, exit_t, skew, "sell_quote")
    bq = eo if eo.get("buy_quote") else _near(obs, entry_t, skew, "buy_quote")
    for o in (le, lx, sq, bq):
        if o is not None:
            out["inputs"].append(o.get("seq"))
    gross = d * (xp / ep - 1)
    out["entry"] = {"t": entry_t, "price": ep, "basis": ebasis, "provider": eo["provider"],
                    "liquidity_usd": le.get("liquidity_usd") if le else None}
    out["exit"] = {"t": exit_t, "price": xp, "basis": xbasis, "provider": xo["provider"],
                   "liquidity_usd": lx.get("liquidity_usd") if lx else None}
    non_exec: list[dict] = []
    if d < 0:
        non_exec.append({"code": "SHORT_NOT_EXECUTABLE_ON_SPOT", "why": "a short is an information return only"})
    # entry side
    le_v = le.get("liquidity_usd") if le else None
    enc, entry_basis = None, "NONE"
    if bq is not None and bq["buy_quote"]["status"] != "OK":
        non_exec.append({"code": "NO_BUY_ROUTE", "why": "no buy route at the entry time"})
    elif bq is not None and abs(bq["buy_quote"]["size_usd"] - size) / size <= 0.25 and bq["buy_quote"].get("out_usd", 0) > 0:
        enc, entry_basis = max(0.0, size / bq["buy_quote"]["out_usd"] - 1) + a["fee_bps_per_side"] / 1e4, "ROUTE_QUOTE"
    if le_v is not None:
        part = size / le_v if le_v > 0 else float("inf")
        if part > pol["max_participation"]:
            non_exec.append({"code": "ILLIQUID_ENTRY", "why": f"size is {part:.1%} of reported liquidity at entry" if le_v > 0 else "no liquidity at entry"})
        if enc is None and le_v > 0:
            enc, entry_basis = base + 2 * part, "MODELED_IMPACT"
    # exit side
    pos_value = size * max(0.0, (xp / ep)) if d > 0 else size
    lx_v = lx.get("liquidity_usd") if lx else None
    exc, exc_q = None, None
    if lx_v is not None:
        part_x = pos_value / lx_v if lx_v > 0 else float("inf")
        if part_x > pol["max_participation"]:
            non_exec.append({"code": "EXIT_LIQUIDITY_LOST", "why": (f"position is {part_x:.1%} of reported liquidity at exit" if lx_v > 0
                                                                    else "reported liquidity at exit is zero")})
        if lx_v > 0:
            exc = base + 2 * part_x
    quote_info = None
    if sq is not None:
        q = sq["sell_quote"]
        quote_info = {"status": q["status"], "size_usd": q["size_usd"], "out_usd": q.get("out_usd"), "t": sq["t"], "provider": sq["provider"]}
        if q["status"] != "OK":
            non_exec.append({"code": "NO_SELL_ROUTE", "why": f"sell route {q['status']} at the exit time"})
        else:
            ratio = q["out_usd"] / q["size_usd"]
            quote_info["proceeds_ratio"] = r10(ratio)
            if abs(q["size_usd"] - pos_value) / max(pos_value, 1e-9) > 0.25:
                out["flags"].append({"flag": "QUOTE_SIZE_DIFFERS", "note": f"quote size {q['size_usd']:.0f} USD vs position value {pos_value:.0f} USD"})
            if ratio > 1 + pol["quote_above_mid_tolerance"]:
                out["flags"].append({"flag": "PRICE_QUOTE_MISMATCH", "note": "quote pays more than the displayed price; quote ignored as inconsistent"})
            else:
                exc_q = max(0.0, 1 - ratio) + a["fee_bps_per_side"] / 1e4
                if 1 - ratio > pol["max_quote_gap"]:
                    out["flags"].append({"flag": "PRICE_QUOTE_MISMATCH", "note": f"route quote returns {ratio:.1%} of the displayed value"})
                    non_exec.append({"code": "PRICE_QUOTE_MISMATCH", "why": "the displayed price is not achievable at this size; displayed P&L is not proceeds"})
    if quote_info is None:
        out["flags"].append({"flag": "NO_ROUTE_QUOTE_AT_EXIT", "note": "exit cost is modeled, not quoted"})
    net_m = net_q = None
    if d > 0 and enc is not None and exc is not None:
        net_m = (xp * (1 - min(1.0, exc))) / (ep * (1 + enc)) - 1
    if d > 0 and enc is not None and exc_q is not None:
        net_q = (xp * (1 - min(1.0, exc_q))) / (ep * (1 + enc)) - 1
    out["returns"] = {"return_mid_gross": r10(gross), "return_net_modeled": r10(net_m), "return_net_quoted": r10(net_q),
                      "entry_cost_basis": entry_basis, "entry_cost": r10(enc), "exit_cost_modeled": r10(exc), "exit_cost_quoted": r10(exc_q),
                      "exit_quote": quote_info,
                      "notes": ["return_mid_gross is the displayed price move, not proceeds",
                                "return_net_modeled uses fees, slippage and constant-product impact at the hypothetical size",
                                "return_net_quoted uses an actual sell route quote at the exit (entry cost as stated in entry_cost_basis)"],
                      "bucket": "FACT for prices; INFERENCE for net returns"}
    if net_m is None and d > 0:
        out["reasons"].append({"code": "LIQUIDITY_UNKNOWN", "why": "no liquidity or route at entry or exit: no modeled net return"})
    # path: every dated midpoint between the fill and the exit; candle highs and lows only for candles fully inside
    pts = [x for x in _prices(obs) if entry_t <= x[0] <= exit_t]
    times = sorted({entry_t, exit_t, *[x[0] for x in pts]})
    gaps = [b - a_ for a_, b in zip(times, times[1:])]
    max_gap = max(gaps) if gaps else float(horizon_s)
    allowed = horizon_s / pol["path_max_gap_divisor"]
    if max_gap > allowed:
        out["excursion"] = {"status": "INSUFFICIENT_PATH", "max_gap_s": r10(max_gap), "allowed_gap_s": r10(allowed), "points": len(pts)}
    else:
        vals = [ep, xp] + [x[1] for x in pts]
        for o in obs:
            if o["kind"] == "CANDLE" and o.get("h") is not None and entry_t <= o["t"] and o["t"] + o["period_s"] <= exit_t:
                vals += [o["h"], o["l"]]
        hi, lo = max(vals), min(vals)
        mfe = (hi / ep - 1) if d > 0 else (1 - lo / ep)
        mae = (lo / ep - 1) if d > 0 else (1 - hi / ep)
        out["excursion"] = {"status": "OK", "max_gap_s": r10(max_gap), "allowed_gap_s": r10(allowed), "points": len(pts),
                            "mfe_mid": r10(mfe), "mae_mid": r10(mae), "basis": "midpoints and candle highs/lows, gross"}
        out["inputs"] += [x[3].get("seq") for x in pts]
    if non_exec:
        return done("NON_EXECUTABLE", *non_exec)
    return done("MEASURED", {"code": "MEASURED", "why": "dated prices at entry and exit"})


def content_sha(outcome: dict) -> str:
    return sha({k: v for k, v in outcome.items() if k not in ("evaluated_as_of", "supersedes_seq", "revision_reason")})


# ---------- coverage ----------

def coverage(contexts: list[dict], latest: dict[tuple[str, int], dict], pol: dict, *, revisions: int = 0) -> dict:
    """Outcome coverage per horizon over every recorded signal, emitted or not. latest: (signal_id, horizon) -> outcome."""
    by_h = {}
    for h in pol["horizons_s"]:
        counts = {s: 0 for s in STATUSES}
        counts["NOT_EVALUATED"] = 0
        reasons: dict[str, dict[str, int]] = {}
        by_disp: dict[str, dict[str, int]] = {}
        rets = []
        for c in contexts:
            o = latest.get((c["signal_id"], h))
            st = o["status"] if o else "NOT_EVALUATED"
            counts[st] += 1
            dd = by_disp.setdefault(c["disposition"], {})
            dd[st] = dd.get(st, 0) + 1
            if o and st in ("MISSING", "NON_EXECUTABLE", "INVALIDATED"):
                for r in o["reasons"]:
                    reasons.setdefault(st, {})[r["code"]] = reasons.setdefault(st, {}).get(r["code"], 0) + 1
            if o and st == "MEASURED" and o["returns"]["return_net_modeled"] is not None:
                rets.append(o["returns"]["return_net_modeled"])
        matured = len(contexts) - counts["PENDING"] - counts["NOT_EVALUATED"]
        rets.sort()
        med = None
        if len(rets) >= 5:
            n = len(rets)
            med = r10(rets[n // 2] if n % 2 else (rets[n // 2 - 1] + rets[n // 2]) / 2)
        by_h[hname(h)] = {"horizon_s": h, "signals": len(contexts), "counts": counts, "matured": matured,
                          "coverage_rate": r10(counts["MEASURED"] / matured) if matured else None,
                          "exclusions": {k: dict(sorted(v.items())) for k, v in sorted(reasons.items())},
                          "by_disposition": {k: dict(sorted(v.items())) for k, v in sorted(by_disp.items())},
                          "measured_net_modeled_n": len(rets), "measured_net_modeled_median": med,
                          "median_note": "descriptive only, over MEASURED outcomes; excluded outcomes are listed, not dropped; fewer than 5 values: no median"}
    return {"engine_version": ENGINE_VERSION, "signals": len(contexts),
            "fixture_signals": sum(1 for c in contexts if c.get("is_fixture")),
            "dispositions": {d: sum(1 for c in contexts if c["disposition"] == d) for d in DISPOSITIONS},
            "revisions": revisions, "horizons": by_h, "trade_execution_impact": "none"}


# ---------- plain text ----------

def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:+.2f}%"


def render_outcome(o: dict) -> str:
    rs = "; ".join(f"{r['code']}" for r in o["reasons"]) or "-"
    line = f"{o['horizon']:>4} {o['status']:<15} {rs}"
    if o.get("returns"):
        r = o["returns"]
        line += f" | mid {_pct(r['return_mid_gross'])}, net modeled {_pct(r['return_net_modeled'])}, net quoted {_pct(r['return_net_quoted'])}"
    if o.get("excursion"):
        e = o["excursion"]
        line += f" | path {e['status']}" + (f" mfe {_pct(e['mfe_mid'])} mae {_pct(e['mae_mid'])}" if e["status"] == "OK" else "")
    if o.get("flags"):
        line += " | flags " + ",".join(sorted({f["flag"] for f in o["flags"]}))
    return line


def render_report(cov: dict) -> str:
    lines = [f"Signals in ledger: {cov['signals']} (fixture: {cov['fixture_signals']}); by disposition: "
             + ", ".join(f"{k} {v}" for k, v in cov["dispositions"].items() if v) if cov["signals"] else "Signals in ledger: 0",
             f"Outcome entries that supersede an earlier entry (matured, changed or revised): {cov['revisions']}", ""]
    if not cov["signals"]:
        lines.append("No signals recorded. Nothing to evaluate.")
        return "\n".join(lines) + "\n"
    lines.append("horizon  signals  pending  measured  missing  non-exec  invalid  not-eval  coverage")
    for h, v in cov["horizons"].items():
        c = v["counts"]
        cr = "n/a (none matured)" if v["coverage_rate"] is None else f"{v['coverage_rate']:.0%} of {v['matured']} matured"
        lines.append(f"{h:<8} {v['signals']:>7}  {c['PENDING']:>7}  {c['MEASURED']:>8}  {c['MISSING']:>7}  {c['NON_EXECUTABLE']:>8}  "
                     f"{c['INVALIDATED']:>7}  {c['NOT_EVALUATED']:>8}  {cr}")
    lines.append("")
    lines.append("Reasons for exclusion (latest outcome per signal and horizon):")
    any_ex = False
    for h, v in cov["horizons"].items():
        for st, rs in v["exclusions"].items():
            any_ex = True
            lines.append(f"  {h} {st}: " + ", ".join(f"{k} x{n}" for k, n in rs.items()))
    if not any_ex:
        lines.append("  none")
    lines.append("")
    lines.append("By disposition (rejected and suppressed signals are evaluated the same way):")
    for h, v in cov["horizons"].items():
        lines.append(f"  {h}: " + "; ".join(f"{d} " + ", ".join(f"{s} {n}" for s, n in sorted(m.items())) for d, m in v["by_disposition"].items()))
    lines.append("")
    lines.append("Medians are descriptive, over MEASURED outcomes only, never a score; positions are hypothetical; no trade is implied.")
    return "\n".join(lines) + "\n"

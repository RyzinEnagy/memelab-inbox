"""Per-opportunity assessment hook (Phase 13).

Called after `pipeline.analyze_token` for each discovered or re-analyzed mint when the backtesting policy is enabled.
It never changes the lab's score, fatal flags, status or report when disabled, and never blocks discovery:
- FAST stage (synchronous, no network): present-tense execution and stress from the analyze result, token-specific
  signal states from the bundle's own closed bars, and any stored historical cohort evidence that matches.
- DEEP stage (deferred): queued as an event; `python -m memelab backtest deep` runs it with bounded fetches.
Idempotent: request_key = sha256(chain, mint, snapshot hash, bar history hash, engine version, policy hash, data revision).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import ENGINE_VERSION, execution as X, quality, store, stress as S
from .strategies import registry
from .strategies.base import Abstain, Signal
from .strategies.features import B

DEFAULT_POLICY = {"enabled": False, "sizes_usd": [250.0, 1000.0, 5000.0], "max_loss_usd": 250.0, "max_exit_impact": 0.05,
                  "deep_stage": "queue", "ta_strategies": ["BREAKOUT_CLOSE", "BREAKOUT_RETEST", "TREND_HHHL", "ABSORPTION_BREAK"],
                  "min_cohort_trades": 30, "provider_lag_s": 300.0}
POLICY_PATH = store.ROOT / "data" / "backtest" / "policy.json"
DEX_TYPE = {"pumpswap": "CPMM", "pump-fun-amm": "CPMM", "raydium": "CPMM", "raydium-cpmm": "CPMM", "raydium-amm": "CPMM", "meteora-damm": "CPMM",
            "raydium-clmm": "CLMM", "orca": "CLMM", "whirlpool": "CLMM", "meteora": "DLMM", "meteora-dlmm": "DLMM", "dlmm": "DLMM",
            "pump-fun": "BONDING_CURVE", "pumpfun": "BONDING_CURVE"}


def load_policy(path: Path | str | None = None) -> dict:
    p = Path(path) if path else POLICY_PATH
    pol = dict(DEFAULT_POLICY)
    if p.exists():
        pol.update(json.loads(p.read_text()))
    env = os.environ.get("MEMELAB_BACKTEST")
    if env is not None:
        pol["enabled"] = env.strip() not in ("0", "", "false", "False")
    return pol


NULL_KEYS = (None, "", "11111111111111111111111111111111")     # the all-zero key means "no authority"


def _active(v) -> bool:
    return v not in NULL_KEYS


def _pool_type(pools: list[dict]) -> tuple[str, dict | None]:
    if not pools:
        return "UNKNOWN", None
    main = max(pools, key=lambda p: p.get("reserve_usd") or 0)
    label = (main.get("dex") or main.get("market_type") or "").lower()
    return DEX_TYPE.get(label, "UNKNOWN"), main


def snapshot_from_result(r: dict) -> tuple[S.Snapshot, dict]:
    """Exact fields from the lab's analyze result; nothing guessed. Returns (snapshot, provenance notes)."""
    b, m = r["bundle"], r["modules"]
    mk, mech = b.get("market") or {}, m.get("mechanics") or {}
    ptype, main = _pool_type(b.get("pools") or [])
    entries = (m.get("entries") or {}).get("entries") or []
    inv = None
    for e in entries:
        if e.get("invalidation_level") is not None:
            inv = e["invalidation_level"] if inv is None else max(inv, e["invalidation_level"])
    sells = []
    dec = (b.get("identity") or {}).get("decimals")
    sol = mk.get("sol_price")
    for usd, q in sorted(((b.get("quotes") or {}).get("SELL") or {}).items()):
        if q.get("status") == "OK" and dec is not None and sol:
            sells.append((float(usd), q["out"] / 1e9 * sol, q.get("impact"), "OK"))
        else:
            sells.append((float(usd), None, None, q.get("status")))
    conc = (m.get("clusters") or {}).get("cluster_adjusted_ownership_pct")
    if conc is None:
        conc = (m.get("holders") or {}).get("insider_pct")
    fee, fee_basis = X.assumed_swap_fee((main or {}).get("dex"))
    snap = S.Snapshot(chain=b.get("chain") or "solana", mint=r["mint"], as_of=b["observed_at"], price_usd=mk.get("price_usd") or 0.0,
                      liquidity_usd=(main or {}).get("reserve_usd") or mk.get("liquidity_usd_total"), pool_type=ptype, quote_asset="SOL", sol_usd=sol,
                      transfer_fee_bps=float(mech.get("transfer_fee_bps") or 0.0), fee_authority_active=_active(mech.get("transfer_fee_authority")),
                      freeze_authority_active=_active(mech.get("freeze_authority")), mint_authority_active=_active(mech.get("mint_authority")),
                      swap_fee=fee, fee_basis=fee_basis,
                      concentrated_pct=conc, circulating_tokens=mk.get("circ_supply"), invalidation_price=inv, sell_quotes=sells, quote_at=b["observed_at"],
                      fatal_flags=[f["flag"] for f in r["score"].get("fatal_flags") or []],
                      has_sell_route=not (m.get("depth") or {}).get("no_route", False), score=r["score"].get("total"), status=r["status"].get("status"))
    e0 = next((e for e in entries if e.get("condition")), {}) if entries else {}
    prov = {"symbol": (b.get("identity") or {}).get("symbol"), "lab_entry": {"style": e0.get("style"), "condition": e0.get("condition"),
            "invalidation": e0.get("invalidation_text"), "invalidation_level": e0.get("invalidation_level")},
            "price": (b.get("sources") or {}).get("price_usd"), "liquidity": "main pool reserve_usd (fallback: market.liquidity_usd_total)", "main_pool": (main or {}).get("pool"),
            "main_pool_label": (main or {}).get("dex") or (main or {}).get("market_type"), "transfer_fee": "mechanics.transfer_fee_bps (not authorities: C1)",
            "quotes": "Jupiter /swap/v1/quote at observed_at (present tense, never historical)"}
    return snap, prov


def token_signal_states(r: dict, policy: dict) -> dict:
    """Run the TA strategies on the bundle's own hourly bars that had CLOSED and were published by observed_at.
    These are token-specific signal states, not validation."""
    b = r["bundle"]
    t = b["observed_at"]
    raw = (b.get("ohlcv") or {}).get("hour1") or []
    lag = policy["provider_lag_s"]
    rows = []
    for x in raw:
        try:
            st = float(x[0]); st = st / 1000.0 if st > 1e11 else st
            rows.append(B(st, st + 3600, float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5] or 0), st + 3600 + lag))
        except (TypeError, ValueError, IndexError):
            continue
    rows.sort(key=lambda z: z.start)
    vis = [z for z in rows if z.avail <= t]
    out = {"closed_bars": len(vis), "dropped_unclosed": len(rows) - len(vis), "signals": {}}
    for sid in policy["ta_strategies"]:
        res = registry.make(sid).evaluate(b.get("chain") or "solana", r["mint"], vis, t)
        out["signals"][sid] = ("SIGNAL" if isinstance(res, Signal) else (f"ABSTAIN:{res.reason}" if isinstance(res, Abstain) else "NONE"))
    return out


def cohort_evidence(con, snap: S.Snapshot, policy: dict) -> dict:
    """Empirical outcomes of past tokens the lab gave the same status (stress.empirical_cohort). Historical, separate
    from the hypothetical shocks, and only reported with at least `min_cohort_trades` cases."""
    return S.empirical_cohort(con, snap.status, horizon_h=24, min_n=policy["min_cohort_trades"], asof=snap.as_of)   # only what was known then


def precheck(snap: S.Snapshot, now: float, max_age_s: float = 2 * 3600) -> tuple[str, str, bool] | None:
    """(state, reason, retriable) when the opportunity cannot be assessed at all; None otherwise."""
    if snap.chain == "solana" and quality.b58_len(snap.mint) != 32:
        return "INVALID_TOKEN_ID", "mint is not a 32-byte base58 public key", False
    if now - snap.as_of > max_age_s:
        return "STALE_DATA", f"analysis snapshot is {(now - snap.as_of) / 3600:.1f} h old", True
    if not snap.price_usd:
        return "SOURCE_BLOCKED", "no price in the analysis bundle", True
    return None


def data_revision(con) -> list[int]:
    """Append-only tables, so the highest row id is a cheap, exact revision marker for the evidence the FAST stage reads."""
    return [con.execute(f"SELECT COALESCE(MAX(id), 0) FROM {t}").fetchone()[0] for t in ("bt_market_bars", "bt_universe_members")]


class _Abstain(Exception):
    def __init__(self, state: str, reason: str, retriable: bool):
        super().__init__(reason)
        self.state, self.reason, self.retriable = state, reason, retriable


def attach(r: dict, policy: dict | None = None, con=None, now: float | None = None) -> dict:
    policy = policy or load_policy()
    t0 = time.time()
    own = con is None
    con = con or store.connect()
    try:
        snap, prov = snapshot_from_result(r)
        snap_hash = store.sha256(snap.__dict__)
        pol_hash = store.sha256({k: policy[k] for k in sorted(policy) if k != "enabled"})
        rev = data_revision(con)                                   # new bars or universe rows change cohort evidence
        bars_hash = store.sha256(((r.get("bundle") or {}).get("ohlcv") or {}).get("hour1") or [])   # the token's own bars feed its signal states
        key = store.sha256([snap.chain, snap.mint, snap_hash, bars_hash, ENGINE_VERSION, pol_hash, rev])
        cached = con.execute("SELECT result_json FROM bt_assessments WHERE request_key=? AND stage='FAST'", (key,)).fetchone()
        now = now if now is not None else time.time()
        if cached:
            prior = json.loads(cached[0])
            pre = precheck(snap, now)
            if pre and pre[0] == "STALE_DATA":                    # same snapshot asked for later: the stored answer has aged out
                store._insert(con, "bt_assessment_events", dict(request_key=key, event="STALE_ON_HIT", detail=prior.get("state"),
                              wall_ms=(time.time() - t0) * 1000, created_at=time.time()))
                con.commit()
                return {k: prior[k] for k in ("request_key", "chain", "mint", "as_of", "lab") if k in prior} | {"symbol": prov.get("symbol"),
                    "tier": "UNAVAILABLE", "state": "STALE_DATA", "reason": pre[1], "retriable": True, "stored_state": prior.get("state"), "cache": "HIT_STALE"}
            store._insert(con, "bt_assessment_events", dict(request_key=key, event="CACHE_HIT", detail=None, wall_ms=(time.time() - t0) * 1000, created_at=time.time()))
            con.commit()
            return prior | {"cache": "HIT"}
        t_req = time.time()                                       # all writes happen in one short transaction at the end
        pre = precheck(snap, now)
        try:
            if pre:
                raise _Abstain(*pre)
            st = S.stress(snap, policy["sizes_usd"], max_loss_usd=policy["max_loss_usd"], max_exit_impact=policy["max_exit_impact"])
            sigs = token_signal_states(r, policy)
            hist = cohort_evidence(con, snap, policy)
            st["historical_evidence"] = hist
            tier = "HISTORICAL_COHORT" if hist["tier"] == "HISTORICAL_COHORT" else ("SCENARIO_ONLY" if st["decision"] not in ("INSUFFICIENT_EXECUTION_DATA",) else "UNAVAILABLE")
            if snap.fatal_flags:
                state = "RISK_FATAL_FLAW"
            elif st["decision"] == "INSUFFICIENT_EXECUTION_DATA":
                state = "INSUFFICIENT_EXECUTION_DATA" if snap.pool_type == "CPMM" else "UNSUPPORTED_POOL"
            elif sigs["closed_bars"] < 25 and hist["tier"] != "HISTORICAL_COHORT":
                state = "INSUFFICIENT_HISTORY"
            elif hist["tier"] != "HISTORICAL_COHORT":
                state = "PARTIAL_WITH_LIMITATIONS"
            else:
                state = "COMPLETE"
            out = {"request_key": key, "chain": snap.chain, "mint": snap.mint, "as_of": snap.as_of, "engine_version": ENGINE_VERSION, "tier": tier, "state": state,
                   "lab": {"score": snap.score, "status": snap.status, "fatal_flags": snap.fatal_flags, "note": "lab score and status unchanged by this assessment"},
                   "snapshot": {k: v for k, v in snap.__dict__.items() if k != "sell_quotes"}, "provenance": prov, "sell_quotes": snap.sell_quotes,
                   "token_signals": sigs, "stress": st, "deep_stage": "QUEUED" if policy.get("deep_stage") == "queue" else "OFF",
                   "disclosure": "research only; hypothetical scenarios; backtests describe the past, not this token's next move"}
            if st["decision"] == "STRUCTURALLY_UNTRADEABLE":
                out["flags"] = ["BT_STRUCTURALLY_UNTRADEABLE"]      # a flag beside the score, never a change to the score
            event = "COMPLETED"
        except _Abstain as e:
            out = {"request_key": key, "chain": snap.chain, "mint": snap.mint, "symbol": prov.get("symbol"), "as_of": snap.as_of, "tier": "UNAVAILABLE", "state": e.state,
                   "reason": e.reason, "retriable": e.retriable, "lab": {"score": snap.score, "status": snap.status, "fatal_flags": snap.fatal_flags}}
            event = "ABSTAINED"
        except Exception as e:  # never break the scout
            out = {"request_key": key, "chain": snap.chain, "mint": snap.mint, "symbol": prov.get("symbol"), "as_of": snap.as_of, "tier": "UNAVAILABLE", "state": "ERROR",
                   "error": f"{type(e).__name__}: {e}", "retriable": True, "lab": {"score": snap.score, "status": snap.status, "fatal_flags": snap.fatal_flags}}
            event = "ERROR"
        store._insert(con, "bt_assessment_events", dict(request_key=key, event="REQUESTED", detail=snap.mint, wall_ms=0.0, created_at=t_req))
        store._insert(con, "bt_assessments", dict(request_key=key, chain=snap.chain, mint=snap.mint, snapshot_hash=snap_hash, engine_version=ENGINE_VERSION,
                      as_of=snap.as_of, stage="FAST", tier=out["tier"], state=out["state"], result_json=out, result_hash=store.sha256(out), created_at=time.time()))
        store._insert(con, "bt_assessment_events", dict(request_key=key, event=event, detail=out["state"], wall_ms=(time.time() - t0) * 1000, created_at=time.time()))
        if out.get("deep_stage") == "QUEUED":
            store._insert(con, "bt_assessment_events", dict(request_key=key, event="QUEUED_DEEP", detail=snap.mint, wall_ms=0.0, created_at=time.time()))
        con.commit()
        return out | {"cache": "MISS"}
    finally:
        if own:
            con.close()


REFRESH_MIN_INTERVAL_S = 3600.0      # at most one catalyst-triggered refresh per {chain, mint} per hour


def on_catalyst(con, record: dict, latest_assessment: dict | None, now: float | None = None,
                min_interval_s: float = REFRESH_MIN_INTERVAL_S) -> dict:
    """Catalyst-triggered refresh (robot or any collector). Only a mint-verified, not-yet-seen origin for a token that
    already has an assessment triggers a refresh request; it never creates a positive verdict by itself."""
    if record.get("source_status") not in (None, "OK"):
        return {"action": "IGNORED", "reason": f"source outage ({record.get('source_status')}): no refresh and no verdict change"}
    if not record.get("mint_verified") or not record.get("mint"):
        return {"action": "IGNORED", "reason": "UNVERIFIED_CATALYST: no verified mint (ticker or name match only)"}
    if latest_assessment is None:
        return {"action": "IGNORED", "reason": "no prior assessment for this mint; the scout must analyze it first"}
    if record.get("mint") != latest_assessment.get("mint") or record.get("chain", "solana") != latest_assessment.get("chain", "solana"):
        return {"action": "IGNORED", "reason": "record is about a different {chain, mint}"}
    if record.get("available_at", 0) <= latest_assessment.get("as_of", 0):
        return {"action": "IGNORED", "reason": "stale: the record was already available when the last assessment was made"}
    seen = con.execute("SELECT 1 FROM bt_assessment_events WHERE event='CATALYST_REFRESH' AND detail=?", (f"{record['mint']}|{record.get('origin_group')}|{record.get('content_hash')}",)).fetchone()
    if seen:
        return {"action": "IGNORED", "reason": "duplicate origin/content already triggered a refresh"}
    now = now if now is not None else time.time()
    recent = con.execute("SELECT MAX(created_at) FROM bt_assessment_events WHERE event='CATALYST_REFRESH' AND detail LIKE ?",
                         (record["mint"] + "|%",)).fetchone()[0]
    if recent is not None and now - recent < min_interval_s:
        return {"action": "IGNORED", "reason": f"rate limited: a refresh for this mint was requested {(now - recent) / 60:.0f} min ago"}
    store._insert(con, "bt_assessment_events", dict(request_key=latest_assessment["request_key"], event="CATALYST_REFRESH",
                  detail=f"{record['mint']}|{record.get('origin_group')}|{record.get('content_hash')}", wall_ms=0.0, created_at=now))
    con.commit()
    return {"action": "REFRESH_REQUESTED", "mint": record["mint"], "claim_kind": record.get("kind") or record.get("claim_type"), "note": "re-run the scout/analyze for this mint; catalyst evidence is attached as a claim, not a signal"}


def stats(con) -> dict:
    rows = con.execute("SELECT event, COUNT(*) n, AVG(wall_ms) ms FROM bt_assessment_events GROUP BY event").fetchall()
    states = con.execute("SELECT state, COUNT(*) FROM bt_assessments GROUP BY state").fetchall()
    return {"events": {r["event"]: {"n": r["n"], "avg_ms": r["ms"]} for r in rows}, "states": {r[0]: r[1] for r in states}}


def run_deep(con, request_key: str, universe_id: str = "lab_state_history") -> dict:
    """DEEP stage (deferred, offline, bounded): replay the TA strategies on this token's own stored history. A handful
    of trades on one token is anecdotal, so it is TOKEN_SPECIFIC evidence with its count, never a validated edge."""
    from . import runner
    row = con.execute("SELECT mint, chain, as_of, snapshot_hash FROM bt_assessments WHERE request_key=? AND stage='FAST'", (request_key,)).fetchone()
    if not row:
        return {"state": "ERROR", "reason": "no FAST assessment for this key"}
    done = con.execute("SELECT result_json FROM bt_assessments WHERE request_key=? AND stage='DEEP'", (request_key,)).fetchone()
    if done:
        return json.loads(done[0]) | {"cache": "HIT"}
    t0 = time.time()
    tokens, skipped = runner.build_tokens(con, universe_id, mints=[row["mint"]])
    if not tokens:
        out = {"state": "INSUFFICIENT_HISTORY", "tier": "UNAVAILABLE", "reason": (skipped[0]["reason"] if skipped else "mint not in the stored universe")}
    else:
        from .engine import Engine, EngineConfig
        per = {}
        for sid in DEFAULT_POLICY["ta_strategies"]:
            res = Engine(EngineConfig(), runner.sol_usd_series(con)).run(registry.make(sid), tokens, until=row["as_of"])
            per[sid] = {"trades": res["n_trades"], "mean_ret": res["mean_ret"], "rets": [round(t["ret"], 4) for t in res["trades"]]}
        n = sum(v["trades"] for v in per.values())
        out = {"state": "COMPLETE" if n else "INSUFFICIENT_HISTORY", "tier": "TOKEN_SPECIFIC" if n else "UNAVAILABLE", "per_strategy": per,
               "note": "this token's own past setups up to the assessment time; anecdotal, not validation"}
    out.update(request_key=request_key, mint=row["mint"], as_of=row["as_of"], wall_s=round(time.time() - t0, 2))
    store._insert(con, "bt_assessments", dict(request_key=request_key, chain=row["chain"], mint=row["mint"], snapshot_hash=row["snapshot_hash"], engine_version=ENGINE_VERSION,
                  as_of=row["as_of"], stage="DEEP", tier=out["tier"], state=out["state"], result_json=out, result_hash=store.sha256(out), created_at=time.time()))
    store._insert(con, "bt_assessment_events", dict(request_key=request_key, event="DEEP_" + out["state"], detail=row["mint"], wall_ms=(time.time() - t0) * 1000,
                  created_at=time.time()))
    con.commit()
    return out | {"cache": "MISS"}


def pending_deep(con) -> list[str]:
    q = con.execute("SELECT DISTINCT e.request_key FROM bt_assessment_events e WHERE e.event='QUEUED_DEEP' AND NOT EXISTS "
                    "(SELECT 1 FROM bt_assessments a WHERE a.request_key=e.request_key AND a.stage='DEEP')").fetchall()
    return [r[0] for r in q]

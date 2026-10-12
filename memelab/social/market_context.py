"""Timestamped market context for a resolved token reference (Phase 05).

Two different questions, kept apart in storage:
  observed at fetch   what providers reported when the lab fetched (price, valuation, liquidity, volume, pairs,
                      executable quotes). as_of = fetched_at. Valid only for a short window after it.
  at posting time     the price when the post was published. Comes only from a historical candle that contains
                      published_at, or from an observation fetched within PRICE_TTL of publication. Today's price is
                      never written as the posting-time price; with no candle the posting-time price is NULL and
                      the context says NO_HISTORY.

The numbers come from the existing builders (normalize.build_bundle for Solana, chains.evm.build_bundle for EVM),
so provider parsing is not duplicated. Every value is one row in social_market_facts with its provider, unit,
quote currency, collector key, source URL, fetched_at and validity window; a new value in a series is a new
version that points at the one it supersedes. Providers that disagree each keep their own row.

Valuation fields carry a supply denominator: market_cap is price x circulating supply and fdv is price x total
supply as each provider defines those terms (lab convention, not re-derived here; see IDENTITY_05.md).
Reported pool liquidity is not exit proceeds: a sell quote says what a given size would actually return.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from typing import Any

from ..chains import registry
from . import identity

# validity windows (seconds) for observed values; a lab convention for how long a reading may stand in for "now"
TTL = {"price": 120, "sell_quote_out": 120, "buy_quote_out": 120, "sell_quote_out_usd": 120, "sell_price_impact": 120,
       "buy_price_impact": 120, "liquidity_reported": 300, "market_cap": 300, "fdv": 300, "volume_24h": 3600,
       "circulating_supply": 86400, "total_supply": 86400, "pair": 86400}
PRICE_TTL = TTL["price"]
TF_SECONDS = {"minute": 60, "hour": 3600, "day": 86400}
SUPPLY_BASIS = {  # (provider, field) -> (denominator, where the meaning comes from)
    ("jupiter", "market_cap"): ("circulating", "jupiter tokens v2 mcap with circSupply"),
    ("jupiter", "fdv"): ("total", "jupiter tokens v2 fdv with totalSupply"),
    ("dexscreener", "market_cap"): ("circulating", "dexscreener marketCap"),
    ("dexscreener", "fdv"): ("total", "dexscreener fdv"),
}
DS_URL = "https://api.dexscreener.com/tokens/v1/{ds}/{addr}"
JUP_URL = "https://lite-api.jup.ag/tokens/v2/search?query={addr}"
GT_OHLCV_URL = "https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pool}/ohlcv/{tf}"


def _sha(*parts: Any) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def _bodies(bodies: dict[str, Any]) -> dict[str, Any]:
    return {k: identity._unwrap(v) for k, v in bodies.items()}


def build_bundle(chain: str, contract: str, bodies: dict[str, Any], fetched_at: float, native_price: float | None = None) -> dict:
    """The lab's normal bundle for this token: same parsers the analysis pipeline uses."""
    b = _bodies(bodies)
    if chain == "solana":
        from ..normalize import build_bundle as sol
        out = sol(contract, b, observed_at=fetched_at, sol_price=native_price)
        out["chain"] = "solana"
        return out
    if registry.is_evm(chain):
        from ..chains import evm
        return evm.build_bundle(chain, contract, b, observed_at=fetched_at, native_price=native_price)
    raise ValueError(f"no market adapter for chain {chain!r}")


def _key_for(bodies: dict[str, Any], prefix: str, needle: str | None) -> str | None:
    for k, v in bodies.items():
        if k.startswith(prefix) and (needle is None or needle.lower() in json.dumps(identity._unwrap(v), default=str).lower()):
            return k
    return None


def observed_facts(chain: str, contract: str, bundle: dict, bodies: dict[str, Any], fetched_at: float) -> list[dict]:
    cfg = registry.get(chain)
    mk, src = bundle.get("market") or {}, bundle.get("sources") or {}
    facts: list[dict] = []

    def add(field, value, unit, provider, *, quote="USD", pair=None, size=None, key=None, url=None, bucket="FACT", as_str=None):
        if value is None and as_str is None:
            return
        basis = SUPPLY_BASIS.get((provider, field))
        facts.append({"field": field, "value_num": value, "value_str": as_str, "unit": unit, "quote_currency": quote,
                      "supply_basis": basis[0] if basis else None, "supply_basis_source": basis[1] if basis else None,
                      "pair_id": pair, "size_usd": size, "provider": provider, "source_key": key, "source_url": url,
                      "as_of": fetched_at, "as_of_kind": "OBSERVED_AT_FETCH", "valid_from": fetched_at,
                      "valid_until": fetched_at + TTL.get(field, 120), "bucket": bucket})

    jup_key = _key_for(bodies, "jup_tok", contract) if chain == "solana" else None
    if jup_key and src.get("price_usd") == "jupiter.tokens_v2":
        url = JUP_URL.format(addr=contract)
        add("price", mk.get("price_usd"), "USD", "jupiter", key=jup_key, url=url)
        add("market_cap", mk.get("market_cap"), "USD", "jupiter", key=jup_key, url=url)
        add("fdv", mk.get("fdv"), "USD", "jupiter", key=jup_key, url=url)
        add("circulating_supply", mk.get("circ_supply"), "token", "jupiter", quote=None, key=jup_key, url=url)
        add("total_supply", mk.get("total_supply"), "token", "jupiter", quote=None, key=jup_key, url=url)
        add("liquidity_reported", mk.get("liquidity_usd_total"), "USD", "jupiter", key=jup_key, url=url)
        add("volume_24h", (mk.get("vol") or {}).get("24h"), "USD", "jupiter", key=jup_key, url=url)
    ds_url = DS_URL.format(ds=cfg["ds_chain"], addr=contract)
    ds_key = _key_for(bodies, "ds", contract)
    if mk.get("ds_price_usd") is not None or mk.get("ds_fdv") is not None:
        add("market_cap", mk.get("ds_market_cap"), "USD", "dexscreener", key=ds_key, url=ds_url)
        add("fdv", mk.get("ds_fdv"), "USD", "dexscreener", key=ds_key, url=ds_url)
    for p in bundle.get("pools") or []:
        pool = p.get("pool")
        if not pool:
            continue
        prov = p.get("source") or "unknown"
        key = _key_for(bodies, "ds" if prov == "dexscreener" else "gt_pools" if prov == "geckoterminal" else "rug", pool)
        url = ds_url if prov == "dexscreener" else None
        add("pair", None, "id", prov, quote=None, pair=pool, key=key, url=url, as_str=pool)
        add("price", p.get("price"), "USD", prov, pair=pool, key=key, url=url)
        add("liquidity_reported", p.get("reserve_usd"), "USD", prov, pair=pool, key=key, url=url)
        add("volume_24h", p.get("vol_24h"), "USD", prov, pair=pool, key=key, url=url)
        if p.get("gt_reserve_usd") is not None:
            add("liquidity_reported", p.get("gt_reserve_usd"), "USD", "geckoterminal", pair=pool, key=_key_for(bodies, "gt_pools", pool))
    # executable quotes: what a given size would actually return
    is_sol = chain == "solana"
    qprov = "jupiter.quote_v1" if is_sol else "kyberswap.routes"
    qunit = "SOL" if is_sol else cfg["native_symbol"]
    native_dec = 9 if is_sol else 18
    for side, qs in (bundle.get("quotes") or {}).items():
        for usd, q in qs.items():
            sizes = {str(usd), str(float(usd)), str(int(float(usd))) if float(usd).is_integer() else str(usd)}
            pref = "jq:" if is_sol else f"kq:{chain}:"
            key = next((f"{pref}{side}:{s}:{contract}" for s in sizes if f"{pref}{side}:{s}:{contract}" in bodies), None)
            f = side.lower() + "_quote_out"
            if q.get("status") != "OK":
                add(f, None, "status", qprov, quote=None, size=float(usd), key=key, as_str=q.get("status") or "ERROR")
                continue
            if side == "SELL":
                out = q.get("out")
                add(f, out / 10 ** native_dec if out is not None else None, qunit, qprov, quote=qunit, size=float(usd), key=key)
                if q.get("usd_out") is not None:
                    add("sell_quote_out_usd", q.get("usd_out"), "USD", qprov, size=float(usd), key=key)
                elif out is not None and mk.get("sol_price" if is_sol else "native_price"):
                    np_ = mk.get("sol_price" if is_sol else "native_price")
                    add("sell_quote_out_usd", out / 10 ** native_dec * np_, "USD", qprov + "+native_price", size=float(usd), key=key, bucket="INFERENCE")
            else:
                add(f, q.get("out"), "token_base_units", qprov, quote=None, size=float(usd), key=key)
            if q.get("impact") is not None:
                add(side.lower() + "_price_impact", q.get("impact"), "ratio", qprov, quote=None, size=float(usd), key=key)
    return facts


def _ohlcv_series(chain: str, contract: str, bundle: dict, bodies: dict[str, Any]) -> list[dict]:
    """Candles for this token's own pools, priced in USD for this token. Key format gt_ohlcv:<pool>:<tf><agg>."""
    pools = {(p.get("pool") or "").lower() for p in bundle.get("pools") or [] if p.get("pool")}
    out = []
    for k, v in bodies.items():
        if not k.startswith("gt_ohlcv:"):
            continue
        parts = k.split(":")
        if len(parts) < 3 or parts[1].lower() not in pools:
            continue
        v = identity._unwrap(v)
        meta_base = (((v or {}).get("meta") or {}).get("base") or {}).get("address")
        if meta_base and not identity._same(meta_base, contract):
            continue   # candles describe another token of the pool; the plan pins token=<contract>
        tfname = parts[2].rstrip("0123456789")
        agg = int(parts[2][len(tfname):] or 1)
        if tfname not in TF_SECONDS:
            continue
        out.append({"key": k, "pool": parts[1], "tf": parts[2], "interval": TF_SECONDS[tfname] * agg, "rows": (v or {}).get("ohlcv") or []})
    return sorted(out, key=lambda s: s["interval"])


def posting_time_facts(chain: str, contract: str, bundle: dict, bodies: dict[str, Any], published_at: float, fetched_at: float) -> list[dict]:
    """OHLC of the finest candle that contains published_at; empty when no candle does."""
    net = registry.get(chain)["gt_network"]
    for s in _ohlcv_series(chain, contract, bundle, bodies):
        for row in s["rows"]:
            if not isinstance(row, (list, tuple)) or len(row) < 5:
                continue
            start = float(row[0])
            if start <= published_at < start + s["interval"]:
                url = GT_OHLCV_URL.format(net=net, pool=s["pool"], tf=s["tf"])
                base = {"unit": "USD", "quote_currency": "USD", "supply_basis": None, "supply_basis_source": None, "pair_id": s["pool"],
                        "size_usd": None, "provider": "geckoterminal", "source_key": s["key"], "source_url": url, "as_of": start,
                        "as_of_kind": "HISTORICAL_CANDLE", "valid_from": start, "valid_until": start + s["interval"], "bucket": "FACT",
                        "value_str": None}
                return [dict(base, field=f"price_candle_{n}", value_num=float(row[i])) for n, i in (("open", 1), ("high", 2), ("low", 3), ("close", 4))
                        if row[i] is not None]
    return []


def store_fact(con: sqlite3.Connection, chain: str, contract: str, ref_id: int | None, f: dict, fetched_at: float, now: float) -> int:
    series = _sha(chain, contract, f["provider"], f["field"], f.get("pair_id"), f.get("size_usd"), f["as_of_kind"])
    fkey = _sha(series, f["as_of"], fetched_at, f.get("value_num"), f.get("value_str"))
    row = con.execute("SELECT fact_id FROM social_market_facts WHERE fact_key=?", (fkey,)).fetchone()
    if row:
        return row[0]
    last = con.execute("SELECT fact_id, fact_version FROM social_market_facts WHERE series_key=? ORDER BY fact_version DESC LIMIT 1", (series,)).fetchone()
    cur = con.execute(
        "INSERT INTO social_market_facts(fact_key,series_key,fact_version,supersedes_fact_id,chain,contract,ref_id,field,value_num,value_str,unit,"
        "quote_currency,supply_basis,supply_basis_source,pair_id,size_usd,provider,source_key,source_url,as_of,as_of_kind,fetched_at,valid_from,"
        "valid_until,bucket,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fkey, series, (last[1] + 1) if last else 1, last[0] if last else None, chain, contract, ref_id, f["field"], f.get("value_num"),
         f.get("value_str"), f["unit"], f.get("quote_currency"), f.get("supply_basis"), f.get("supply_basis_source"), f.get("pair_id"),
         f.get("size_usd"), f["provider"], f.get("source_key"), f.get("source_url"), f["as_of"], f["as_of_kind"], fetched_at,
         f["valid_from"], f["valid_until"], f["bucket"], now))
    return cur.lastrowid


def attach(con: sqlite3.Connection, resolution_id: int, bodies: dict[str, Any], fetched_at: float, published_at: float | None = None,
           native_price: float | None = None, now: float | None = None) -> dict:
    """Build, store and return the market context of one resolved mention. Refuses anything not resolved."""
    t = time.time() if now is None else float(now)
    r = con.execute("SELECT * FROM social_token_resolutions WHERE resolution_id=?", (resolution_id,)).fetchone()
    if r is None:
        raise KeyError(f"no resolution {resolution_id}")
    if r["status"] != "resolved":
        raise ValueError(f"resolution {resolution_id} is {r['status']}: market context needs an exact identity")
    chain, contract, ref_id = r["resolved_chain"], r["resolved_contract"], r["resolved_ref_id"]
    b = _bodies(bodies)
    bundle = build_bundle(chain, contract, b, fetched_at, native_price)
    obs = observed_facts(chain, contract, bundle, b, fetched_at)
    ids = {id(f): store_fact(con, chain, contract, ref_id, f, fetched_at, t) for f in obs}
    notes: list[Any] = []
    # observed price used as "the" price at fetch: Jupiter for Solana, else the deepest pair's price
    price_obs = [f for f in obs if f["field"] == "price"]
    pick = next((f for f in price_obs if f["provider"] == "jupiter"), None)
    if pick is None and price_obs:
        liq = {f["pair_id"]: f["value_num"] for f in obs if f["field"] == "liquidity_reported" and f.get("pair_id")}
        pick = max(price_obs, key=lambda f: liq.get(f.get("pair_id")) or 0)
    vals = [f["value_num"] for f in price_obs if f["value_num"]]
    if len(vals) >= 2 and min(vals) > 0:
        spread = max(vals) / min(vals) - 1
        notes.append({"code": "provider_price_spread", "value": round(spread, 6), "providers": sorted({f["provider"] for f in price_obs})})
        if spread > 0.03:
            notes.append({"code": "providers_disagree_on_price"})
    liq_total = max([f["value_num"] for f in obs if f["field"] == "liquidity_reported" and f["value_num"]] or [0]) or None
    for f in obs:
        if f["field"] == "sell_quote_out_usd" and f.get("size_usd"):
            notes.append({"code": "sell_proceeds_ratio", "size_usd": f["size_usd"], "ratio": round(f["value_num"] / f["size_usd"], 6)})
        if f["field"] == "sell_quote_out" and f.get("value_str"):
            notes.append({"code": "sell_" + f["value_str"].lower(), "size_usd": f["size_usd"]})
    if liq_total and any(n.get("code") in ("sell_proceeds_ratio", "sell_no_route") for n in notes if isinstance(n, dict)):
        notes.append({"code": "reported_liquidity_is_not_exit_proceeds", "max_reported_liquidity_usd": liq_total})
    pools = bundle.get("pools") or []
    market_status = "POOLS_FOUND" if pools else ("NO_POOL" if price_obs or obs else "NO_DATA")
    if not pools:
        notes.append({"code": "no_pool_reported_at_fetch"})
    posting_id, status = None, None
    lag = (fetched_at - published_at) if published_at is not None else None
    if published_at is None:
        status = "PUBLISHED_AT_UNKNOWN"
    else:
        hist = posting_time_facts(chain, contract, bundle, b, published_at, fetched_at)
        if hist:
            hid = [store_fact(con, chain, contract, ref_id, f, fetched_at, t) for f in hist]
            posting_id = hid[0]
            status = "HISTORICAL_CANDLE"
            notes.append({"code": "posting_price_is_candle_open", "candle_seconds": hist[0]["valid_until"] - hist[0]["valid_from"]})
        elif pick is not None and abs(lag) <= PRICE_TTL:
            posting_id = ids[id(pick)]
            status = "FETCHED_AT_POSTING"
        else:
            status = "NO_HISTORY"
            notes.append({"code": "no_candle_covers_published_at"})
    ckey = _sha(resolution_id, fetched_at)
    con.execute("INSERT OR IGNORE INTO social_market_context(context_key,resolution_id,item_key,chain,contract,published_at,fetched_at,"
                "observed_lag_seconds,posting_time_status,posting_price_fact_id,observed_price_fact_id,market_status,notes_json,recorded_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ckey, resolution_id, r["item_key"], chain, contract, published_at, fetched_at, lag, status, posting_id,
                 ids[id(pick)] if pick is not None else None, market_status, json.dumps(notes, sort_keys=True), t))
    row = con.execute("SELECT * FROM social_market_context WHERE context_key=?", (ckey,)).fetchone()
    return {**dict(row), "notes": notes, "n_facts": len(obs), "observed_price": pick["value_num"] if pick else None,
            "posting_price": con.execute("SELECT value_num FROM social_market_facts WHERE fact_id=?", (posting_id,)).fetchone()[0] if posting_id else None}


def context_plan(chain: str, contract: str, pools: list[str], decimals: int | None, price_usd: float | None,
                 native_price: float | None, liq_usd: float | None = None, plan_id: str | None = None):
    """Collector plan for the context: the existing deep plans (pools, OHLCV pinned to the token, executable quotes)."""
    if chain == "solana":
        from ..bridge.plan import Plan
        return Plan(plan_id or f"ctx_{contract[:8]}").deep(contract, pools, sol_price=native_price, decimals=decimals or 6, price_usd=price_usd)
    from ..chains import plan as cplan
    return cplan.evm_deep(chain, contract, pools, decimals or 18, price_usd, native_price, liq_usd, plan_id=plan_id)

"""Read-only wallet tracking: public address -> balances, recent swaps, inferred positions.

Nothing here can sign or move funds. It only reads public chain state via the browser bridge
(PublicNode / Helius RPC and Helius Enhanced Transactions) and feeds m26 (portfolio risk) and
m27 (post-trade review).

Bundle keys produced by the plan (all projected by collector.js):
    rpc:bal:<addr>        getBalance
    rpc:toks:<addr>       getTokenAccountsByOwner (Token program)
    rpc:toks22:<addr>     getTokenAccountsByOwner (Token-2022)
    helius_tx:<addr>      parsed transaction history (swaps, transfers)
"""
from __future__ import annotations

import time
from typing import Any

from .bridge.github_inbox import load_config
from .bridge.plan import HELIUS_TX, Plan, rpc_url

TOKEN = "TokenkegQfeZyiNvSKfyoYekpg9MVy4JPJDPnC9GRRS6"
TOKEN22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
SOL = "So11111111111111111111111111111111111111112"
STABLES = {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC", "Es9vMFrzaCERmJfrF6H2gcBWJCqE2VBChY9jY1PEEfj5": "USDT"}


def tracked_wallets() -> list[dict]:
    """Private: data/wallet/tracked.json (gitignored, never published)."""
    import json
    from .db import DATA_DIR
    p = DATA_DIR / "wallet" / "tracked.json"
    if p.exists():
        return json.loads(p.read_text()).get("tracked_wallets") or []
    return load_config().get("tracked_wallets") or []


def wallet_plan(plan_id: str, addresses: list[str], tx_limit: int = 100) -> Plan:
    p = Plan(plan_id)
    key = load_config().get("helius_api_key")
    for a in addresses:
        p.add(f"rpc:bal:{a}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [a]}, proj="raw", delay_ms=300)
        p.add(f"rpc:toks:{a}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner", "params": [a, {"programId": TOKEN}, {"encoding": "jsonParsed"}]}, proj="raw", delay_ms=300)
        p.add(f"rpc:toks22:{a}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner", "params": [a, {"programId": TOKEN22}, {"encoding": "jsonParsed"}]}, proj="raw", delay_ms=300)
        if key:
            p.add(f"helius_tx:{a}", HELIUS_TX.format(addr=a, key=key, limit=tx_limit), proj="helius_tx", delay_ms=250)
    return p


def _result(body: Any) -> Any:
    if isinstance(body, dict) and "result" in body:
        return body["result"]
    return body


def balances(addr: str, bodies: dict[str, Any]) -> dict[str, Any]:
    out = {"address": addr, "sol": None, "tokens": [], "unknowns": []}
    bal = _result(bodies.get(f"rpc:bal:{addr}"))
    if isinstance(bal, dict) and "value" in bal:
        out["sol"] = bal["value"] / 1e9
    elif isinstance(bal, (int, float)):
        out["sol"] = bal / 1e9
    else:
        out["unknowns"].append("SOL balance not returned")
    for k in (f"rpc:toks:{addr}", f"rpc:toks22:{addr}"):
        r = _result(bodies.get(k))
        if not isinstance(r, dict):
            out["unknowns"].append(f"{k.split(':')[1]} token accounts not returned")
            continue
        for acc in r.get("value") or []:
            info = (((acc.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
            ta = info.get("tokenAmount") or {}
            amt = ta.get("uiAmount")
            if amt:
                out["tokens"].append({"mint": info.get("mint"), "amount": amt, "decimals": ta.get("decimals"), "program": "token2022" if "toks22" in k else "token"})
    return out


def swaps(addr: str, bodies: dict[str, Any]) -> list[dict]:
    """Flatten Helius parsed txs (collector helius_tx projection) into swap legs touching this wallet.
    Projection rows: {sig, ts, type, src, fee, payer, nt:[[from,to,sol]], tt:[[from,to,mint,amt]]}"""
    rows = bodies.get(f"helius_tx:{addr}") or []
    out = []
    for t in rows if isinstance(rows, list) else []:
        sol_in = sum(x[2] for x in t.get("nt") or [] if x[1] == addr) - sum(x[2] for x in t.get("nt") or [] if x[0] == addr)
        tok_in = {}
        for frm, to, mint, amt in t.get("tt") or []:
            if to == addr:
                tok_in[mint] = tok_in.get(mint, 0) + (amt or 0)
            if frm == addr:
                tok_in[mint] = tok_in.get(mint, 0) - (amt or 0)
        tok_in = {m: a for m, a in tok_in.items() if abs(a) > 0}
        kind = t.get("type")
        side = None
        if tok_in and kind == "SWAP":
            # one non-SOL token received with SOL/stable spent = BUY; token sent = SELL
            nonsol = {m: a for m, a in tok_in.items() if m != SOL}
            if nonsol:
                m, a = max(nonsol.items(), key=lambda x: abs(x[1]))
                side = "BUY" if a > 0 else "SELL"
                out.append({"sig": t.get("sig"), "ts": t.get("ts"), "mint": m, "side": side, "tokens": abs(a), "sol_delta": sol_in, "fee_sol": (t.get("fee") or 0) / 1e9, "source": t.get("src")})
                continue
        out.append({"sig": t.get("sig"), "ts": t.get("ts"), "mint": None, "side": kind, "tokens": None, "sol_delta": sol_in, "fee_sol": (t.get("fee") or 0) / 1e9, "source": t.get("src")})
    return out


def positions_from_wallet(addr: str, bodies: dict[str, Any], prices: dict[str, float] | None = None, sol_price: float | None = None) -> dict[str, Any]:
    """Open positions = current non-zero token balances; cost basis from BUY swaps where SOL delta is known.
    Everything derived is labelled; cost basis is INFERENCE when swaps are incomplete."""
    bal = balances(addr, bodies)
    sw = swaps(addr, bodies)
    by_mint: dict[str, dict] = {}
    for s in sw:
        if not s["mint"]:
            continue
        d = by_mint.setdefault(s["mint"], {"buy_tokens": 0.0, "buy_sol": 0.0, "sell_tokens": 0.0, "sell_sol": 0.0, "n_buy": 0, "n_sell": 0, "first_ts": None, "last_ts": None})
        if s["side"] == "BUY":
            d["buy_tokens"] += s["tokens"]; d["buy_sol"] += -s["sol_delta"] if s["sol_delta"] < 0 else 0; d["n_buy"] += 1
        else:
            d["sell_tokens"] += s["tokens"]; d["sell_sol"] += s["sol_delta"] if s["sol_delta"] > 0 else 0; d["n_sell"] += 1
        d["first_ts"] = min(d["first_ts"] or s["ts"], s["ts"]) if s["ts"] else d["first_ts"]
        d["last_ts"] = max(d["last_ts"] or s["ts"], s["ts"]) if s["ts"] else d["last_ts"]
    positions, facts, inferences, unknowns = [], [], [], list(bal["unknowns"])
    facts.append(f"SOL balance {bal['sol']:.4f}" + (f" (${bal['sol'] * sol_price:,.2f})" if bal["sol"] is not None and sol_price else "") if bal["sol"] is not None else "SOL balance unknown")
    facts.append(f"{len(bal['tokens'])} non-zero token account(s); {len(sw)} parsed transaction(s) in the fetched window")
    for t in bal["tokens"]:
        m = t["mint"]
        if m in STABLES:
            facts.append(f"stable balance {t['amount']:,.2f} {STABLES[m]}")
            continue
        price = (prices or {}).get(m)
        hist = by_mint.get(m) or {}
        entry = None
        if hist.get("buy_tokens") and hist.get("buy_sol") and sol_price:
            entry = hist["buy_sol"] * sol_price / hist["buy_tokens"]
            inferences.append(f"{m[:8]}..: average entry ~${entry:.6g} inferred from {hist['n_buy']} parsed buy(s); partial history if the fetch window was short")
        else:
            unknowns.append(f"{m[:8]}..: cost basis unknown (no parsed buys in window)")
        positions.append({"mint": m, "symbol": None, "tokens": t["amount"], "entry_price": entry, "current_price": price,
                          "size_usd": entry * t["amount"] if entry else None, "current_value_usd": price * t["amount"] if price else None,
                          "invalidation_price": None, "opened_at": hist.get("first_ts"), "n_buys": hist.get("n_buy", 0), "n_sells": hist.get("n_sell", 0)})
    closed = [m for m, h in by_mint.items() if h["n_sell"] and m not in {t["mint"] for t in bal["tokens"]}]
    if closed:
        facts.append(f"{len(closed)} fully exited token(s) in window: " + ", ".join(c[:8] + ".." for c in closed))
    return {"address": addr, "observed_at": time.time(), "balances": bal, "swaps": sw, "positions": positions, "closed_mints": closed,
            "facts": facts, "inferences": inferences, "heuristics": ["address is not person; this is the on-chain state of one public key, read-only"], "unknowns": unknowns}

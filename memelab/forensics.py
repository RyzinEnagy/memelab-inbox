"""Wallet forensics from Helius Enhanced Transactions (collector projection `helius_tx`).

Each projected tx: {sig, ts, type, src, fee, payer, nt: [[from, to, sol]], tt: [[from, to, mint, amount]]}
Output per wallet (facts only; inferences are drawn by m10/m11):
  first_tx_ts, n_tx, funding_sources (SOL senders ordered by first seen), first_funder,
  token_in (sum received of mint), token_out (sum sent), first_token_ts, acquisition_mechanism (SWAP / TRANSFER_IN / UNKNOWN),
  swaps_buy, swaps_sell, transfers_in_from, transfers_out_to, cex_touch (destinations matching exchange labels)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .modules.m09_holder_classification import KNOWN_LABELS

SOL = "So11111111111111111111111111111111111111112"


def _iso(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return None


def wallet_profile(wallet: str, txs: list[dict], mint: str) -> dict[str, Any]:
    txs = sorted([t for t in txs if isinstance(t, dict)], key=lambda t: t.get("ts") or 0)
    funders: list[str] = []
    token_in = token_out = 0.0
    first_token_ts = None
    mech = None
    buys = sells = 0
    tin_from: dict[str, float] = {}
    tout_to: dict[str, float] = {}
    for t in txs:
        for frm, to, sol in t.get("nt") or []:
            if to == wallet and frm and frm != wallet and frm not in funders:
                funders.append(frm)
        has_mint_in = has_mint_out = False
        for frm, to, m, amt in t.get("tt") or []:
            if m != mint or not amt:
                continue
            if to == wallet:
                token_in += amt; has_mint_in = True
                if frm:
                    tin_from[frm] = tin_from.get(frm, 0) + amt
            if frm == wallet:
                token_out += amt; has_mint_out = True
                if to:
                    tout_to[to] = tout_to.get(to, 0) + amt
        if has_mint_in and first_token_ts is None:
            first_token_ts = t.get("ts")
            mech = "SWAP" if (t.get("type") == "SWAP") else "TRANSFER_IN" if t.get("type") == "TRANSFER" else (t.get("type") or "UNKNOWN")
        if t.get("type") == "SWAP":
            if has_mint_in:
                buys += 1
            if has_mint_out:
                sells += 1
    cex = sorted({KNOWN_LABELS[d][1] for d in tout_to if d in KNOWN_LABELS and KNOWN_LABELS[d][0] == "CEX"})
    return {
        "wallet": wallet, "n_tx": len(txs), "first_tx": _iso(txs[0]["ts"]) if txs else None, "last_tx": _iso(txs[-1]["ts"]) if txs else None,
        "first_funder": funders[0] if funders else None, "funders": funders[:5],
        "token_in": token_in, "token_out": token_out, "net_tokens": token_in - token_out,
        "first_token_ts": _iso(first_token_ts), "acquisition_mechanism": mech, "swaps_buy": buys, "swaps_sell": sells,
        "transfer_in_from": sorted(tin_from, key=tin_from.get, reverse=True)[:3], "transfer_out_to": sorted(tout_to, key=tout_to.get, reverse=True)[:3],
        "cex_destinations": cex, "window_truncated": len(txs) >= 100,
    }


def build_wallet_txs(bodies: dict[str, Any], mint: str) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """Returns (wallet_txs for m10 [with sol_in_from per tx], profiles for m11)."""
    wallet_txs: dict[str, list[dict]] = {}
    profiles: dict[str, dict] = {}
    for k, v in bodies.items():
        if not k.startswith("helius_tx:") or not isinstance(v, list):
            continue
        w = k.split(":", 1)[1]
        rows = []
        for t in v:
            if not isinstance(t, dict):
                continue
            rows.append({**t, "sol_in_from": [frm for frm, to, sol in (t.get("nt") or []) if to == w and frm and frm != w]})
        wallet_txs[w] = rows
        profiles[w] = wallet_profile(w, v, mint)
    return wallet_txs, profiles


def summarize_profiles(profiles: dict[str, dict], holders_out: dict | None, dev_set: set[str]) -> dict[str, Any]:
    """Aggregate facts for the report: common funders, acquisition timing clusters, CEX destinations, inventory direction."""
    facts, inferences = [], []
    if not profiles:
        return {"facts": facts, "inferences": inferences, "rows": []}
    funders: dict[str, list[str]] = {}
    for w, p in profiles.items():
        for f in p["funders"][:2]:
            funders.setdefault(f, []).append(w)
    shared = {f: ws for f, ws in funders.items() if len(ws) >= 2}
    for f, ws in sorted(shared.items(), key=lambda kv: -len(kv[1]))[:5]:
        label = KNOWN_LABELS.get(f, (None, None))[1]
        facts.append(f"{len(ws)} material wallets were funded by {f[:8]}.." + (f" ({label})" if label else "") + ": " + ", ".join(x[:6] + ".." for x in ws))
        inferences.append(("shared funding from an exchange hot wallet is weak evidence of common control" if label else f"wallets funded by {f[:8]}.. may be under common control or coordinated") + f" (n={len(ws)})")
    # acquisition timing
    times = sorted((p["first_token_ts"], w) for w, p in profiles.items() if p.get("first_token_ts"))
    if len(times) >= 3:
        facts.append(f"first acquisition times span {times[0][0]} to {times[-1][0]}")
        from datetime import datetime
        ts = [datetime.fromisoformat(t).timestamp() for t, _ in times]
        close = sum(1 for a, b in zip(ts, ts[1:]) if b - a <= 300)
        if close >= 2:
            inferences.append(f"{close + 1} material wallets first acquired the token within minutes of one another: launch-window buying or coordinated entry")
    mech = {}
    for p in profiles.values():
        mech[p.get("acquisition_mechanism") or "UNKNOWN"] = mech.get(p.get("acquisition_mechanism") or "UNKNOWN", 0) + 1
    facts.append("acquisition mechanism among traced wallets: " + ", ".join(f"{k} {v}" for k, v in mech.items()))
    tin = sum(p["token_in"] for p in profiles.values()); tout = sum(p["token_out"] for p in profiles.values())
    facts.append(f"traced wallets received {tin:,.0f} and sent out {tout:,.0f} tokens in their recent history (window: last 100 txs each)")
    cex = sorted({c for p in profiles.values() for c in p["cex_destinations"]})
    if cex:
        facts.append("tokens sent toward exchange wallets: " + ", ".join(cex))
    dev_rows = [p for w, p in profiles.items() if w in dev_set]
    for p in dev_rows:
        facts.append(f"dev/creator {p['wallet'][:8]}..: {p['swaps_buy']} buy swaps, {p['swaps_sell']} sell swaps, net {p['net_tokens']:+,.0f} tokens in window; funded by {p['first_funder'][:8] + '..' if p['first_funder'] else 'unknown'}")
    rows = sorted(profiles.values(), key=lambda p: -(p["token_in"] + p["token_out"]))
    return {"facts": facts, "inferences": inferences, "rows": rows, "shared_funders": {f: ws for f, ws in shared.items()}}

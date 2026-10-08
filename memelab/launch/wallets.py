"""PRE_LAUNCH_WALLET_ANALYSIS + SNIPER_ANALYSIS.

Holder structure (RugCheck for Solana, GoPlus for EVM), early-buyer / sniper inventory from the first trades of the token's own pool,
and funding clusters when wallet histories (Helius) are in the result set. Every finding is written as FACT / INFERENCE / UNKNOWN:
shared funding is economic linkage, not proof of common control.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from .. import db

SNIPER_SECONDS = 60          # buys inside the first minute of the pool count as sniper/early-bot buys
EARLY_SECONDS = 300


def _ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def holders(c: dict, bodies: dict) -> dict[str, Any]:
    mint, chain = c.get("contract"), c.get("chain")
    out: dict[str, Any] = {"source": None, "facts": [], "unknowns": [], "top": []}
    excl = {x for x in (c.get("pool"), c.get("curve_pool"), c.get("bonding_curve")) if x}
    if chain == "solana":
        rg = bodies.get(f"rug:{mint}")
        if not isinstance(rg, dict) or not rg.get("topHolders"):
            out["unknowns"].append("holder list (no RugCheck report)")
            return out
        out["source"] = "rugcheck"
        for m in rg.get("markets") or []:
            excl.add(m.get("pubkey"))
        rows = []
        for h in rg.get("topHolders") or []:
            own = h.get("owner")
            if own in excl or h.get("address") in excl:
                continue
            rows.append({"owner": own, "pct": h.get("pct"), "insider": bool(h.get("insider"))})
        out["top"] = rows
        out["top10_ex_pool_pct"] = sum(r["pct"] or 0 for r in rows[:10])
        cb = rg.get("creatorBalance")
        tok = rg.get("token") or {}
        sup = tok.get("supply"); dec = tok.get("decimals")
        if cb is not None and sup:
            out["dev_pct"] = cb / (sup / 10 ** (dec or 0)) * 100 if cb < sup / 10 ** (dec or 0) * 2 else cb / sup * 100
        nets = rg.get("insiderNetworks") or []
        if nets and sup:
            out["insider_network_pct"] = sum((n.get("tokenAmount") or 0) for n in nets) / sup * 100
            out["insider_networks"] = [{"size": n.get("size"), "type": n.get("type"), "pct": (n.get("tokenAmount") or 0) / sup * 100} for n in nets[:6]]
        out["risks"] = [r.get("name") for r in rg.get("risks") or []]
        out["rugged"] = bool(rg.get("rugged"))
        out["mint_authority"] = (tok.get("mintAuthority") or rg.get("mintAuthority"))
        out["freeze_authority"] = (tok.get("freezeAuthority") or rg.get("freezeAuthority"))
        out["facts"].append(f"top-10 holders excluding pools/curve {out['top10_ex_pool_pct']:.1f}% (RugCheck, {len(rows)} wallets listed)")
    else:
        gp = bodies.get(f"goplus:{chain}:{mint}")
        rec = (gp or {}).get(mint) if isinstance(gp, dict) else None
        if not rec:
            out["unknowns"].append("holder list (no GoPlus record)")
            return out
        out["source"] = "goplus"
        rows = []
        for h in rec.get("holders") or []:
            ad = (h.get("address") or "").lower()
            if ad in excl or h.get("is_locked") in (1, "1") or ad.startswith("0x000000000000000000000000000000000000"):
                continue
            pct = float(h.get("percent") or 0) * 100
            rows.append({"owner": ad, "pct": pct, "insider": False, "contract": h.get("is_contract") in (1, "1"), "tag": h.get("tag")})
        rows = [r for r in rows if not (r["contract"] and (r["tag"] or "").lower().find("pool") >= 0)]
        out["top"] = rows
        out["top10_ex_pool_pct"] = sum(r["pct"] for r in rows[:10])
        if rec.get("creator_percent") is not None:
            out["dev_pct"] = float(rec.get("creator_percent") or 0) * 100
        out["facts"].append(f"top-10 holders excluding pools/locked {out['top10_ex_pool_pct']:.1f}% (GoPlus)")
    return out


def snipers(c: dict, bodies: dict, hold: dict, total_supply: float | None) -> dict[str, Any]:
    pool = c.get("pool") or c.get("curve_pool")
    res: dict[str, Any] = {"facts": [], "inferences": [], "unknowns": []}
    trades = (bodies.get(f"gt_trades:{pool}:all") or {}).get("trades") if pool else None
    if not trades:
        res["unknowns"].append("early trades (no trade history for the token's pool)")
        return res
    start = c.get("first_trade_at") or c.get("created_at")
    tt = sorted([t for t in trades if _ts(t[0])], key=lambda t: _ts(t[0]))
    first = _ts(tt[0][0]) if tt else None
    if start is None or (first and first < start):
        start = first
    covered = first is not None and start is not None and first - start < 120
    if not covered:
        res["unknowns"].append("first-minute buyers and sniper inventory: the trade history starts "
                               + (f"{(first - start) / 60:.0f} min after the pool opened" if first and start else "after the open")
                               + " (GeckoTerminal returns only the latest 300 trades); on pump.fun the earliest buying also happens on the curve, before this pool existed")
        return res
    holding = {r["owner"]: r["pct"] for r in hold.get("top") or []}
    early = defaultdict(lambda: {"bought": 0.0, "sold": 0.0, "usd": 0.0, "first": None})
    for t in tt:
        ts = _ts(t[0]); w = t[1]; kind = t[2]
        dt = ts - start if start else None
        if dt is None or dt > EARLY_SECONDS:
            continue
        # projected trade row: [ts, wallet, kind, from_amt, to_amt, usd, price_from, price_to, tx]; tokens bought = to_amt on buys
        amt = (t[4] if kind == "buy" else t[3]) or 0
        e = early[w]
        if kind == "buy":
            e["bought"] += amt; e["usd"] += t[5] or 0
            e["first"] = dt if e["first"] is None else min(e["first"], dt)
        else:
            e["sold"] += amt
    later_sells = defaultdict(float)
    for t in tt:
        if t[2] == "sell" and t[1] in early:
            later_sells[t[1]] += t[3] or 0
    snip = {w: e for w, e in early.items() if e["first"] is not None and e["first"] <= SNIPER_SECONDS}
    res["early_wallets"] = len([e for e in early.values() if e["bought"]])
    res["sniper_wallets"] = len(snip)
    if total_supply:
        res["sniper_bought_pct"] = sum(e["bought"] for e in snip.values()) / total_supply * 100
        res["early_bought_pct"] = sum(e["bought"] for e in early.values()) / total_supply * 100
    res["sniper_still_holding_pct"] = sum(holding.get(w, 0) for w in snip)
    res["early_still_holding_pct"] = sum(holding.get(w, 0) for w in early)
    res["snipers_selling"] = sum(1 for w in snip if later_sells.get(w, 0) > 0)
    res["sniper_list"] = sorted(([w, round(e["first"], 1), round(e["usd"], 2)] for w, e in snip.items()), key=lambda x: x[1])[:15]
    res["facts"].append(f"{res['sniper_wallets']} wallet(s) bought within {SNIPER_SECONDS}s of the first trade, {res['early_wallets']} within {EARLY_SECONDS // 60} minutes"
                        + (f"; they bought {res['sniper_bought_pct']:.1f}% / {res['early_bought_pct']:.1f}% of supply" if total_supply else ""))
    res["facts"].append(f"early buyers still among top holders: {res['early_still_holding_pct']:.1f}% of supply; {res['snipers_selling']} sniper wallet(s) have sold")
    if (res.get("sniper_bought_pct") or 0) > 15:
        res["inferences"].append("automated first-minute buyers acquired a large share: they are the first sellers into any rally")
    return res


def funding_clusters(c: dict, bodies: dict, hold: dict, snip: dict) -> dict[str, Any]:
    """Group early/top wallets by the wallet that funded them (Helius histories in the result set)."""
    wallets = [r["owner"] for r in (hold.get("top") or [])[:15]] + [w for w, *_ in snip.get("sniper_list") or []]
    funders: dict[str, list] = defaultdict(list)
    seen = 0
    for w in dict.fromkeys(wallets):
        txs = bodies.get(f"helius_tx:{w}")
        if not isinstance(txs, list):
            continue
        seen += 1
        inbound = [(t.get("ts"), n[0], n[2]) for t in txs for n in (t.get("nt") or []) if n[1] == w and n[0] and n[0] != w]
        if inbound:
            ts, src, amt = min(inbound, key=lambda x: x[0] or 0)
            funders[src].append((w, ts, amt))
    res = {"wallets_checked": seen, "clusters": [], "facts": [], "inferences": [], "unknowns": []}
    if not seen:
        res["unknowns"].append("funding sources of early and top wallets (wallet histories not collected)")
        return res
    pct = {r["owner"]: r["pct"] for r in hold.get("top") or []}
    for src, ws in funders.items():
        if len(ws) >= 3:
            tss = [x[1] for x in ws if x[1]]
            span = (max(tss) - min(tss)) / 60 if len(tss) >= 2 else None
            share = sum(pct.get(x[0], 0) for x in ws)
            res["clusters"].append({"funder": src, "wallets": [x[0] for x in ws], "span_min": span, "pct": share})
            res["facts"].append(f"{len(ws)} wallets received their first SOL/ETH from {src[:8]}.." + (f" within {span:.0f} minutes" if span is not None else "") + f"; together they hold {share:.1f}%")
            res["inferences"].append("these wallets may be coordinated launch participants")
            res["unknowns"].append("whether they are controlled by the team")
    return res


def persist(con, lid: str, t: float, hold: dict, snip: dict, clus: dict) -> list[dict]:
    flags = []
    if snip.get("sniper_wallets"):
        flags.append({"kind": "SNIPER_INVENTORY", "wallets_json": json.dumps(snip.get("sniper_list")), "pct_supply": snip.get("sniper_still_holding_pct"),
                      "fact": "; ".join(snip["facts"]), "inference": "; ".join(snip.get("inferences") or []) or None, "unknown": "; ".join(snip.get("unknowns") or []) or None})
    for cl in clus.get("clusters") or []:
        flags.append({"kind": "PREPOSITION_CLUSTER", "wallets_json": json.dumps(cl["wallets"]), "pct_supply": cl["pct"], "fact": f"{len(cl['wallets'])} wallets funded by {cl['funder']}",
                      "inference": "may be coordinated launch participants", "unknown": "whether they are controlled by the team"})
    if hold.get("insider_network_pct"):
        flags.append({"kind": "INSIDER_NETWORK", "wallets_json": json.dumps(hold.get("insider_networks")), "pct_supply": hold["insider_network_pct"],
                      "fact": f"RugCheck insider graph: {hold['insider_network_pct']:.1f}%", "inference": "linked wallets by transfer graph", "unknown": "common control"})
    for f in flags:
        db.insert(con, "launch_wallet_flags", {"launch_id": lid, "observed_at": t, **f})
    return flags

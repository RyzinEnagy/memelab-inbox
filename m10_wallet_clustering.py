"""10_WALLET_CLUSTERING: clustering signals among economically meaningful wallets.

Evidence available without a paid indexer:
  - RugCheck insider networks (graph of wallets with common funding / transfers)  -> INFERENCE, confidence per network size
  - GeckoTerminal recent trades: same-minute / same-block purchases, identical sizing, synchronized sells among top holders
  - Optional: RPC getSignaturesForAddress / getTransaction bodies (wallet_txs) for first-funding-source tracing
Never: ADDRESS = PERSON, CLUSTER = PROVEN COMMON OWNER.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def _minute(ts: str) -> str | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None


def analyze(bundle: dict[str, Any], holders_out: dict | None = None, wallet_txs: dict[str, list[dict]] | None = None) -> dict[str, Any]:
    h = bundle.get("holders") or {}
    top = (holders_out or {}).get("classified") or [{"owner": x.get("owner"), "pct": x.get("pct"), "classification": "INSIDER" if x.get("insider") else "UNKNOWN"} for x in h.get("top") or []]
    econ = {c["owner"]: c for c in top if c.get("owner") and c.get("classification") not in ("POOL", "BURN", "LOCKER", "CEX")}
    trades = bundle.get("trades") or []
    facts, inferences, unknowns, heur = [], [], [], []
    clusters = []
    # 1. RugCheck insider networks
    for n in h.get("insider_networks") or []:
        size = n.get("size") or 0
        amt = n.get("tokenAmount") or 0
        supply = (bundle.get("market") or {}).get("total_supply") or (bundle.get("market") or {}).get("circ_supply")
        dec = (bundle.get("identity") or {}).get("decimals") or (bundle.get("authorities") or {}).get("decimals") or 6
        ui_amt = amt / (10 ** dec) if amt else 0  # RugCheck reports tokenAmount in base units
        pct = (ui_amt / supply * 100) if supply and ui_amt else None
        if size > 200:
            # thousands of transfer-linked wallets is the signature of an airdrop / mass distribution graph, not a controlled cluster
            conf = "LOW"
            inference = "a very large transfer graph is typical of airdrops, launchpad distributions or exchange withdrawals; it is weak evidence of common control"
        else:
            conf = "HIGH" if size >= 10 else "MODERATE" if size >= 4 else "LOW"
            inference = "wallets may share funding or be transfer-linked"
        clusters.append({"key": f"rugcheck_network:{n.get('id')}", "members": n.get("wallets") or [], "n": size, "pct": pct, "confidence": conf,
                         "evidence": [{"fact": f"RugCheck links {size} wallets in network {n.get('id')} (type {n.get('type')}) holding {ui_amt:,.0f} tokens" + (f" ({pct:.2f}% of supply)" if pct else ""), "inference": inference, "confidence": f"{conf} for economic linkage; unknown for real-world identity"}]})
        if size > 200 and pct:
            inferences.append(f"network {n.get('id')} spans {size} wallets holding {pct:.1f}% of supply: treated as a distribution graph (LOW confidence), not as controlled ownership; investigate the largest members individually")
        facts.append(f"insider network {n.get('id')}: {size} wallets" + (f", {pct:.2f}% of supply" if pct else ""))
    # 2. Trade-timing clusters among top holders
    by_minute = defaultdict(list)
    for t in trades:
        ts, wallet, kind, amt, usd = t[0], t[1], t[2], t[3], t[4]
        if wallet in econ:
            m = _minute(ts)
            if m:
                by_minute[(m, kind)].append((wallet, amt, usd))
    sync = {k: v for k, v in by_minute.items() if len({w for w, _, _ in v}) >= 3}
    for (m, kind), v in list(sync.items())[:5]:
        ws = sorted({w for w, _, _ in v})
        sizes = [round(a or 0) for _, a, _ in v]
        same_size = len(set(sizes)) == 1 and len(sizes) > 1
        pct = sum(econ[w].get("pct") or 0 for w in ws)
        conf = "MODERATE" if same_size else "LOW"
        clusters.append({"key": f"same_minute_{kind}:{m}", "members": ws, "n": len(ws), "pct": pct, "confidence": conf,
                         "evidence": [{"fact": f"{len(ws)} top-holder wallets {kind} in the same minute ({m} UTC)" + (", identical token sizes" if same_size else ""), "inference": "possible coordinated execution or common control", "confidence": conf}]})
        facts.append(f"{len(ws)} top-holder wallets {kind} within the same minute at {m} UTC" + (" with identical sizes" if same_size else ""))
    # 3. Funding-source tracing from RPC tx bodies (if supplied)
    funding = defaultdict(list)
    if wallet_txs:
        for w, txs in wallet_txs.items():
            for tx in txs:
                for src in tx.get("sol_in_from") or []:
                    funding[src].append(w)
        for src, ws in funding.items():
            ws = sorted(set(ws))
            if len(ws) >= 2:
                pct = sum(econ.get(w, {}).get("pct") or 0 for w in ws)
                conf = "HIGH" if len(ws) >= 3 else "MODERATE"
                clusters.append({"key": f"common_funder:{src}", "members": ws, "n": len(ws), "pct": pct, "confidence": conf,
                                 "evidence": [{"fact": f"{len(ws)} wallets received SOL from {src}", "inference": "common upstream funding (may be a CEX hot wallet; check label)", "confidence": conf}]})
                facts.append(f"{len(ws)} material wallets share upstream funder {src[:8]}..")
    else:
        unknowns.append("wallet funding sources not traced (requires RPC transaction fetch per wallet; run `memelab wallets <mint>`)")
    # cluster-adjusted ownership: union of members across clusters with MODERATE+ confidence, counted once
    members = set()
    for c in clusters:
        if c["confidence"] in ("HIGH", "MODERATE"):
            members |= set(c["members"])
    cluster_pct = sum(econ[w].get("pct") or 0 for w in members if w in econ)
    network_pct = sum((c.get("pct") or 0) for c in clusters if c["key"].startswith("rugcheck_network") and c["confidence"] in ("HIGH", "MODERATE"))
    if cluster_pct == 0 and network_pct:
        cluster_pct = network_pct
        facts.append(f"RugCheck insider networks (MODERATE+ confidence) hold {network_pct:.2f}% of supply combined; member wallets not enumerated, so overlap with top holders is unknown")
    top_conf = "HIGH" if any(c["confidence"] == "HIGH" for c in clusters) else "MODERATE" if any(c["confidence"] == "MODERATE" for c in clusters) else "LOW" if clusters else "NONE"
    if clusters:
        inferences.append(f"potential cluster-adjusted ownership among top holders: {cluster_pct:.1f}% (members of clusters with at least MODERATE confidence; excludes wallets outside the observed top list)")
    else:
        facts.append("no clustering signals detected in available data (insider networks absent, no synchronized top-holder trades in the recent trade window)")
    heur.append("cluster membership is economic linkage, never proof of a single owner; the real-world identity is UNKNOWN")
    if len(trades) < 50:
        unknowns.append("trade window small; timing-based clustering has low power")
    return {"clusters": clusters, "cluster_adjusted_ownership_pct": cluster_pct if clusters else None, "confidence": top_conf,
            "n_clusters": len(clusters), "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}

"""09_HOLDER_CLASSIFICATION: classify top holders before computing concentration; raw vs adjusted top-10.

Classification basis (recorded per holder):
  POOL     owner is a known pool / AMM authority, or the token account appears as a pool reserve for a known pool
  BURN     incinerator / system addresses
  CEX      known exchange hot wallets (small seed list; extend via wallets table labels)
  LOCKER / VESTING  known locker programs (Streamflow, Jupiter Lock, ...)
  DEV      owner equals creator / dev wallet
  INSIDER  RugCheck insider graph flag (inference, not fact)
  UNKNOWN  economic holder with no classification (treated as an investor for adjusted concentration)
"""
from __future__ import annotations

from typing import Any

BURN = {"1nc1nerator11111111111111111111111111111111", "11111111111111111111111111111111", "1111111111111111111111111111111111111111111", "deadbeef1111111111111111111111111111111111"}
KNOWN_LABELS = {
    # pool / protocol authorities
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1": ("POOL", "Raydium AMM v4 authority"),
    "GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL": ("POOL", "PumpSwap pool authority"),
    "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg": ("POOL", "pump.fun migration authority"),
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": ("POOL", "PumpSwap program"),
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": ("POOL", "pump.fun bonding curve program"),
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": ("POOL", "Meteora DLMM program"),
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": ("POOL", "Meteora DAMM program"),
    "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG": ("POOL", "Meteora DAMM v2 program"),
    "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN": ("POOL", "Meteora DBC program"),
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": ("POOL", "Orca Whirlpool program"),
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": ("POOL", "Raydium CLMM program"),
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": ("POOL", "Raydium CPMM program"),
    "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj": ("POOL", "Raydium LaunchLab program"),
    # lockers / vesting
    "strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m": ("LOCKER", "Streamflow"),
    "LocpQgucEQHbqNABEYvBvwoxCPsSbG91A1QaQhQQqjn": ("LOCKER", "Jupiter Lock"),
    "BLoCKvQEZZdhkjx8fZYF1sDxCt9Td9iQdcsCxZ4GpR4A": ("LOCKER", "Bonk Lock"),
    # exchanges (seed)
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": ("CEX", "Binance hot"),
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": ("CEX", "Binance"),
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": ("CEX", "Coinbase"),
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": ("CEX", "Coinbase 2"),
    "ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ": ("CEX", "MEXC"),
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": ("CEX", "Bybit"),
    "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w": ("CEX", "Gate.io"),
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5": ("CEX", "Kraken"),
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": ("CEX", "OKX"),
}


def analyze(bundle: dict[str, Any], extra_labels: dict[str, tuple[str, str]] | None = None) -> dict[str, Any]:
    h = bundle.get("holders") or {}
    ident = bundle.get("identity") or {}
    pools = {p.get("pool") for p in bundle.get("pools") or []}
    labels = dict(KNOWN_LABELS); labels.update(extra_labels or {})
    dev_set = {x for x in (ident.get("creator"), ident.get("dev"), h.get("developer_address_gt")) if x}
    top = h.get("top") or []
    facts, inferences, unknowns, heur = [], [], [], []
    classified = []
    for i, x in enumerate(top, 1):
        owner, acct, pct = x.get("owner"), x.get("account"), x.get("pct")
        cls, basis = "UNKNOWN", "no label"
        if owner in BURN or acct in BURN:
            cls, basis = "BURN", "incinerator/system address"
        elif owner in labels:
            cls, basis = labels[owner]
        elif acct in labels:
            cls, basis = labels[acct]
        elif owner in pools or acct in pools or x.get("is_pool"):
            cls, basis = "POOL", "owner/account is a known pool address" if not x.get("is_pool") else "GoPlus dex pair / pool contract"
        elif x.get("is_locked"):
            cls, basis = "LOCKER", "GoPlus marks the balance as locked"
        elif x.get("tag") and any(k in str(x["tag"]).lower() for k in ("uniswap", "pancake", "aerodrome", "sushi", "curve", "balancer", "pool", "vault")):
            cls, basis = "POOL", f"GoPlus tag {x['tag']}"
        elif x.get("tag") and any(k in str(x["tag"]).lower() for k in ("binance", "coinbase", "okx", "bybit", "kraken", "gate", "kucoin", "htx", "mexc", "bitget", "cex")):
            cls, basis = "CEX", f"GoPlus tag {x['tag']}"
        elif x.get("tag"):
            cls, basis = "UNKNOWN", f"GoPlus tag {x['tag']} (unclassified)"
        elif owner in dev_set:
            cls, basis = "DEV", "owner equals creator/dev wallet"
        elif x.get("insider"):
            cls, basis = "INSIDER", "rugcheck insider graph flag (inference)"
        classified.append({"rank": i, "account": acct, "owner": owner, "pct": pct, "amount": x.get("amount"), "classification": cls, "basis": basis})
    econ = [c for c in classified if c["classification"] not in ("POOL", "BURN", "LOCKER", "VESTING")]
    raw_top10 = sum((c["pct"] or 0) for c in classified[:10])
    adj_top10 = sum((c["pct"] or 0) for c in econ[:10])
    adj_top20 = sum((c["pct"] or 0) for c in econ[:20])
    pool_pct = sum((c["pct"] or 0) for c in classified if c["classification"] == "POOL")
    insider_pct = sum((c["pct"] or 0) for c in classified if c["classification"] == "INSIDER")
    cex_pct = sum((c["pct"] or 0) for c in classified if c["classification"] == "CEX")
    dev_pct_top = sum((c["pct"] or 0) for c in classified if c["classification"] == "DEV")
    unknown_econ = [c for c in econ if c["classification"] == "UNKNOWN"]
    largest_unexplained = max(unknown_econ, key=lambda c: c["pct"] or 0) if unknown_econ else None
    total = h.get("total") or h.get("total_gt") or (bundle.get("market") or {}).get("holder_count")
    if total:
        facts.append(f"holder count {total:,}" + (f" (rugcheck {h.get('total'):,}, geckoterminal {h.get('total_gt'):,})" if h.get("total") and h.get("total_gt") else ""))
    if classified:
        facts.append(f"top {len(classified)} holders observed: {sum(1 for c in classified if c['classification']=='POOL')} pool(s) holding {pool_pct:.1f}%, {len(unknown_econ)} unclassified wallets")
        facts.append(f"RAW top-10 concentration {raw_top10:.1f}%")
        facts.append(f"ADJUSTED top-10 concentration (pools, burns, lockers removed) {adj_top10:.1f}%; adjusted top-20 {adj_top20:.1f}%")
        if largest_unexplained:
            facts.append(f"largest unexplained economic holder: {largest_unexplained['owner']} with {largest_unexplained['pct']:.2f}%")
        if insider_pct:
            inferences.append(f"wallets flagged by RugCheck's insider graph hold {insider_pct:.1f}% among the top holders (graph inference, not proof of insider status)")
        if cex_pct:
            facts.append(f"exchange custody wallets hold {cex_pct:.1f}%")
        if dev_pct_top:
            facts.append(f"creator/dev wallet holds {dev_pct_top:.2f}% (within top holders)")
    else:
        unknowns.append("no top-holder list available")
    dist = h.get("distribution") or {}
    if dist:
        facts.append("geckoterminal distribution: top10 {top_10}%, 11-20 {11_20}%, 21-40 {21_40}%, rest {rest}%".format(**{k: dist.get(k) for k in ("top_10", "11_20", "21_40", "rest")}))
        try:
            gt_top10 = float(dist.get("top_10"))
            if abs(gt_top10 - raw_top10) > 5 and classified:
                facts.append(f"DISCREPANCY: geckoterminal top-10 {gt_top10:.1f}% vs rugcheck-derived raw top-10 {raw_top10:.1f}% (different snapshot times or pool handling)")
        except (TypeError, ValueError):
            pass
    dev_hold = h.get("dev_holding_pct")
    if dev_hold is None:
        dev_hold = (bundle.get("authorities") or {}).get("dev_balance_pct_jup")
    if dev_hold is not None:
        facts.append(f"developer holding {dev_hold:.2f}% of supply ({'geckoterminal' if h.get('dev_holding_pct') is not None else 'jupiter audit'})")
    nets = h.get("insider_networks") or []
    if nets:
        for n in nets[:3]:
            facts.append(f"insider network {n.get('id')}: {n.get('size')} wallets, type {n.get('type')}, token amount {n.get('tokenAmount')}, active {n.get('activeAccounts')}")
    heur.append("falling concentration is not inherently bullish: ask whether the market absorbed supply or insiders found exit liquidity")
    return {"classified": classified, "raw_top10_pct": raw_top10, "adjusted_top10_pct": adj_top10, "adjusted_top20_pct": adj_top20,
            "pool_pct": pool_pct, "insider_pct": insider_pct, "cex_pct": cex_pct, "dev_holding_pct": dev_hold,
            "largest_unexplained_pct": largest_unexplained["pct"] if largest_unexplained else None,
            "largest_unexplained_owner": largest_unexplained["owner"] if largest_unexplained else None,
            "holder_count": total, "distribution": dist, "insider_networks": nets,
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}

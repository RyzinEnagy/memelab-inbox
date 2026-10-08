"""Dev wallet-farm detector (manufactured market cap).

Pattern seen on DOTF, DAWS and GOIF (Goh59...) on 2026-10-08: the dev side splits almost all supply across
hundreds or thousands of wallets with identical balances, pays to create their token accounts, and lets bots
buy a nearly empty pool upward. Holder concentration then looks tiny (0.05% each), so the normal
top-holder and cluster checks pass while one actor controls most of the supply.

Evidence, strongest first:
  1. helius_holders:<mint>:<page> bodies (Helius DAS getTokenAccounts): many owners with exactly the same
     balance holding a large share of supply. FACT.
  2. helius_tx:<wallet> bodies (forensics): sampled top holders whose token account was created with fees
     paid by the dev/creator wallet. FACT.
  3. RugCheck risks "High holder correlation" + "High market cap per holder" with liquidity under 1% of
     market cap. INFERENCE only (used when 1 is not available).

Fatal when the identical-balance group holds >= 25% of supply (DETECTED), or when the RugCheck pattern and
dev-paid token accounts appear together (SUSPECTED, at least 5 sampled holders). Never improves a score.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

MIN_GROUP = 50          # identical-balance wallets needed before the group counts
FATAL_SHARE_PCT = 25.0  # same threshold as cluster-adjusted ownership
WARN_SHARE_PCT = 10.0
MIN_DEV_PAID = 5


def _holders(mint: str, bodies: dict[str, Any]) -> Counter:
    own: Counter = Counter()
    for k, v in bodies.items():
        if not k.startswith(f"helius_holders:{mint}:"):
            continue
        b = v.get("body") if isinstance(v, dict) and "body" in v else v
        res = (b or {}).get("result") if isinstance(b, dict) else None
        for a in (res or {}).get("token_accounts") or []:
            try:
                own[a["owner"]] += int(a["amount"])
            except (KeyError, TypeError, ValueError):
                continue
    return own


def _rug(mint: str, bodies: dict[str, Any]) -> dict:
    v = bodies.get(f"rug:{mint}")
    b = v.get("body") if isinstance(v, dict) and "body" in v else v
    return b if isinstance(b, dict) else {}


def _jup(mint: str, bodies: dict[str, Any]) -> dict:
    v = bodies.get(f"jup_tok:{mint}")
    b = v.get("body") if isinstance(v, dict) and "body" in v else v
    if isinstance(b, list) and b:
        return b[0] if isinstance(b[0], dict) else {}
    return b if isinstance(b, dict) else {}


def _dev_paid(bodies: dict[str, Any], devs: set[str]) -> tuple[int, int]:
    """(wallets whose token-account creation was paid by a dev wallet, wallets sampled)."""
    paid = sampled = 0
    for k, v in bodies.items():
        if not k.startswith("helius_tx:"):
            continue
        w = k.split(":", 1)[1]
        if w in devs:
            continue
        b = v.get("body") if isinstance(v, dict) and "body" in v else v
        if not isinstance(b, list):
            continue
        sampled += 1
        if any(isinstance(t, dict) and t.get("type") == "INITIALIZE_ACCOUNT" and t.get("payer") in devs for t in b):
            paid += 1
    return paid, sampled


def detect(mint: str, bodies: dict[str, Any], bundle: dict | None = None) -> dict[str, Any]:
    bundle = bundle or {}
    ident = bundle.get("identity") or {}
    rug, jt = _rug(mint, bodies), _jup(mint, bodies)
    devs = {x for x in (ident.get("creator"), ident.get("dev"), rug.get("creator"), jt.get("dev")) if x}
    tok = rug.get("token") or {}
    dec = tok.get("decimals") or jt.get("decimals") or 6
    supply = tok.get("supply")
    pools = {m.get("pubkey") for m in rug.get("markets") or [] if m.get("pubkey")}
    for k in ("graduatedPool", "bondingCurve"):
        if jt.get(k):
            pools.add(jt[k])

    out: dict[str, Any] = {"status": "NOT DETECTED", "share_pct": None, "group_wallets": None, "group_balance": None,
                           "dev_paid_accounts": None, "facts": [], "inferences": [], "unknowns": []}

    own = _holders(mint, bodies)
    if own:
        if not supply:
            supply = sum(own.values())
        groups = Counter(b for b in (round(x / 10 ** dec) for o, x in own.items() if o not in pools) if b >= 1)
        bal, n = (groups.most_common(1) or [(0, 0)])[0]
        share = (bal * 10 ** dec * n) / supply * 100 if supply and bal else 0.0
        out.update(group_wallets=n, group_balance=bal, share_pct=round(share, 2))
        out["facts"].append(f"holder list read: {len(own):,} owners; largest identical-balance group {n:,} wallets x {bal:,} tokens = {share:.1f}% of supply")
        if n >= MIN_GROUP and share >= FATAL_SHARE_PCT:
            out["status"] = "DETECTED"
        elif n >= MIN_GROUP and share >= WARN_SHARE_PCT:
            out["status"] = "WARNING"
    else:
        out["unknowns"].append("full holder list not fetched (add holders_full to the plan); identical-balance check not run")

    paid, sampled = _dev_paid(bodies, devs)
    if sampled:
        out["dev_paid_accounts"] = paid
        out["facts"].append(f"{paid} of {sampled} sampled wallets had their token account created with fees paid by the dev/creator wallet")

    risks = {str(r.get("name") or "") for r in rug.get("risks") or []}
    liq, mcap = jt.get("liquidity"), jt.get("mcap") or jt.get("fdv")
    liq_ratio = (liq / mcap) if liq and mcap else None
    rug_pattern = "High holder correlation" in risks and "High market cap per holder" in risks and liq_ratio is not None and liq_ratio < 0.01
    if rug_pattern:
        out["facts"].append(f"RugCheck: High holder correlation + High market cap per holder; liquidity {liq_ratio * 100:.2f}% of market cap")
        if out["status"] == "NOT DETECTED" and (paid >= MIN_DEV_PAID or not own):
            out["status"] = "SUSPECTED" if paid >= MIN_DEV_PAID else "WARNING"
    if out["status"] == "DETECTED":
        out["inferences"].append("supply sits in a dev-built wallet farm; holder concentration looks low only because it is split; treat the group as one economic holder")
    elif out["status"] == "SUSPECTED":
        out["inferences"].append("RugCheck correlation pattern plus dev-paid token accounts: probable dev wallet farm (fetch the holder list to confirm)")
    out["fatal"] = out["status"] in ("DETECTED", "SUSPECTED")
    return out

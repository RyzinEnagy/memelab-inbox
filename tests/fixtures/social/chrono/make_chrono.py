"""Builds the Phase 12 chronology fixtures. Every name, address, post and price here is INVENTED. Run: python make_chrono.py

confident.json      the order of every post and associated-wallet trade is established
indeterminate.json  a minute-precision post and an unknown-time post overlap the trades, so the order is not established
"""
import hashlib
import json
from pathlib import Path

T0 = 1791676800          # 2026-10-11 00:00:00Z, invented
H = 3600
SCHEMA = "memelab.social.chrono.input/1"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(seed: str, n: int = 44) -> str:
    d = hashlib.sha256(seed.encode()).digest() * 4
    return "".join(B58[x % 58] for x in d[:n])


MINT = b58("fixture-mint-labcat")
OTHER_MINT = b58("fixture-mint-labcat-impostor")
W1, W2, W3 = b58("fixture-wallet-1"), b58("fixture-wallet-2"), b58("fixture-wallet-3")
CEX = b58("fixture-exchange-hot-wallet")
POOL = b58("fixture-pool-1")


def sig(seed: str) -> str:
    return b58("sig-" + seed, 88)


def post(key, pub, *, basis="PROVIDER", precision=None, seen=None, direction="LONG", position="not_disclosed", kind="ORIGINAL", repost_of=None,
         token=None, extra_obs=(), claim_id=None):
    obs = []
    if seen is not None:
        obs.append({"observation_id": f"fx-obs-{key}-1", "observed_at": seen, "status": "OK"})
    obs += list(extra_obs)
    p = {"item_key": f"x:{key}", "platform": "x", "url": f"https://example.invalid/fixture/status/{key}", "published_at": pub,
         "published_basis": basis if pub is not None else "UNKNOWN", "observations": obs, "talk_kind": kind, "repost_of": repost_of,
         "direction": direction, "author_position": position, "claim_id": claim_id,
         "token": token or {"chain": "solana", "contract": MINT, "status": "resolved", "symbol": "LABCAT"}}
    if precision is not None:
        p["published_precision_s"] = precision
    return p


def wallet(addr, level, *, entity="acct:x:id:fx1", others=(), label=None, aid=1):
    return {"chain": "solana", "wallet": addr, "level": level, "account_entity": entity, "other_claimants": list(others), "label_kind": label,
            "assertion_ids": [aid], "evidence_refs": [f"https://example.invalid/fixture/proof/{aid}"],
            "confidence": {"SIGNATURE_VERIFIED": "HIGH", "SELF_CLAIMED": "LOW"}.get(level, "UNKNOWN")}


def event(seed, addr, t, etype, side=None, amount=1000.0, *, contract=None, slot=None, counterparty=None, label=None, custody=None):
    s = sig(seed)
    direction = "IN" if (side == "BUY" or etype.endswith("_IN")) else "OUT"
    return {"chain": "solana", "wallet": addr, "signature": s, "slot": slot, "block_time": t, "event_type": etype, "swap_side": side,
            "legs": [{"asset_kind": "TOKEN", "contract": contract or MINT, "direction": direction, "amount": amount,
                      "counterparty": counterparty, "counterparty_label": label}],
            "url": f"https://solscan.io/tx/{s}", "provider": "fixture", "custody_touch": custody, "event_id": seed}


def candles(prices, start, step=H, liq=None, source="fixture-candles (INVENTED)"):
    rows = []
    for i, c in enumerate(prices):
        r = {"t": start + i * step, "o": c, "h": c, "l": c, "c": c}
        if liq is not None:
            r["liq"] = liq[i]
        rows.append(r)
    return {"chain": "solana", "contract": MINT, "source": source, "candle_seconds": step, "as_of_kind": "HISTORICAL_CANDLE", "rows": rows}


def base(label, as_of, **kw):
    d = {"schema": SCHEMA, "label": f"FIXTURE: {label}", "is_fixture": True, "as_of": as_of,
         "token": {"chain": "solana", "contract": MINT, "symbol": "LABCAT"},
         "source": {"source_id": "fx_source_a", "label": "FIXTURE source A (invented)", "accounts": ["x:id:fx1"]},
         "posts": [], "wallets": [], "wallet_events": [], "pool_events": [], "market": [],
         "coverage": {"posts_enumerated": True, "providers": {"social": "OK", "wallet": "OK", "market": "OK"}, "wallet_monitoring": []}}
    d.update(kw)
    return d


def monitored(addr, frm, to):
    return {"chain": "solana", "wallet": addr, "from": frm, "to": to, "last_ok_fetch": to}


def confident():
    prices = [1.0] * 8 + [1.2, 1.4, 1.6, 1.5, 1.3, 1.2, 1.1, 1.1] + [1.1] * 22      # candles from T0-6h, hourly
    liq = [50000.0] * 12 + [30000.0] * 26
    return base("confident order", T0 + 32 * H,
                posts=[post("1900000000000000101", T0 + 2 * H, seen=T0 + 2 * H + 30, direction="LONG", position="not_disclosed", claim_id=101,
                            extra_obs=[{"observation_id": "fx-obs-101-2", "observed_at": T0 + 20 * H, "status": "OK"}])],
                wallets=[wallet(W1, "SIGNATURE_VERIFIED", aid=1), wallet(W2, "THIRD_PARTY_CLAIMED", aid=2)],
                wallet_events=[event("c-buy-w1", W1, T0, "SWAP", "BUY", 1_000_000.0, slot=300000100),
                               event("c-buy-w2", W2, T0 + 2 * H + 600, "SWAP", "BUY", 50_000.0, slot=300018000),
                               event("c-sell-w1", W1, T0 + 5 * H, "SWAP", "SELL", 400_000.0, slot=300045000)],
                pool_events=[{"chain": "solana", "contract": MINT, "pool": POOL, "kind": "LP_REMOVE", "time": T0 + 6 * H, "time_basis": "CHAIN_BLOCK",
                              "liquidity_usd": 30000.0, "source": "fixture pool log (INVENTED)", "ref": "tx:" + sig("c-lp-remove")}],
                market=[candles(prices, T0 - 6 * H, liq=liq)],
                coverage={"posts_enumerated": True, "providers": {"social": "OK", "wallet": "OK", "market": "OK"},
                          "wallet_monitoring": [monitored(W1, T0 - 72 * H, T0 + 31 * H), monitored(W2, T0 - 72 * H, T0 + 31 * H)]})


def indeterminate():
    return base("indeterminate order", T0 + 32 * H,
                posts=[post("1900000000000000201", T0 + 2 * H, precision=60, seen=T0 + 2 * H + 90, direction="LONG", position="not_disclosed", claim_id=201),
                       post("1900000000000000202", None, seen=T0 + 3 * H, direction="LONG", position="not_disclosed", claim_id=202)],
                wallets=[wallet(W1, "SIGNATURE_VERIFIED", aid=1)],
                wallet_events=[event("i-buy-w1", W1, T0 + 2 * H + 25, "SWAP", "BUY", 800_000.0, slot=300018010),
                               event("i-sell-w1", W1, T0 + 2 * H + 50, "SWAP", "SELL", 300_000.0, slot=300018070)],
                coverage={"posts_enumerated": True, "providers": {"social": "OK", "wallet": "OK", "market": "UNAVAILABLE"},
                          "wallet_monitoring": [monitored(W1, T0 - 72 * H, T0 + 31 * H)]})


def write(d: Path = Path(__file__).resolve().parent) -> None:
    for name, fn in (("confident.json", confident), ("indeterminate.json", indeterminate)):
        (d / name).write_text(json.dumps(fn(), indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    write()

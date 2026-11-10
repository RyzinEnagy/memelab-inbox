"""Phase 07 spot-check: our constant-product math against live Jupiter quotes on real PumpSwap pools.

Read-only: Solana JSON-RPC reads (getAccountInfo, getMultipleAccounts) and Jupiter /swap/v1/quote (quotes only; no swap
transaction is requested, built or signed). Present-tense evidence only: it checks the math, it is never used as a
historical fill.
    python audits/backtesting/execution/p07_spotcheck.py POOL [POOL ...] > audits/backtesting/execution/p07_spotcheck.json
"""
from __future__ import annotations

import base64
import json
import struct
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import execution as X  # noqa: E402

RPC = "https://api.mainnet-beta.solana.com"
JUP = "https://lite-api.jup.ag/swap/v1/quote"
PAMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
WSOL = "So11111111111111111111111111111111111111112"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
UA = {"User-Agent": "memelab-research/0.1 (read-only quotes)", "Content-Type": "application/json", "Accept": "application/json"}


def b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def b58dec(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


def rpc(method: str, params: list):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    time.sleep(0.5)
    return d["result"]


def jup(input_mint: str, output_mint: str, amount: int) -> dict:
    q = urllib.parse.urlencode({"inputMint": input_mint, "outputMint": output_mint, "amount": str(amount), "slippageBps": "50",
                                "onlyDirectRoutes": "true", "dexes": "Pump.fun Amm"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{JUP}?{q}", headers=UA), timeout=30) as r:
                d = json.loads(r.read())
            time.sleep(2.0)
            return d
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                return {"error": f"HTTP {e.code}"}
            time.sleep(5 * 2 ** attempt)


def pool_state(pool: str) -> dict:
    acc = rpc("getAccountInfo", [pool, {"encoding": "base64", "commitment": "confirmed"}])
    slot, v = acc["context"]["slot"], acc["value"]
    data = base64.b64decode(v["data"][0])
    # PumpSwap Pool (Anchor): 8 discriminator, u8 bump, u16 index, creator, base_mint, quote_mint, lp_mint,
    # pool_base_token_account, pool_quote_token_account, ... Offsets are verified below against the vaults' own mints.
    keys = [b58enc(data[11 + 32 * i: 43 + 32 * i]) for i in range(6)]
    # after lp_supply (u64 @203) and coin_creator (@211..243): two flag bytes, then a signed i64 at 245 read here as
    # virtual_quote_reserves. Checked empirically: with it, buy and sell implied fees agree on every pool tested.
    virtual_quote = struct.unpack_from("<q", data, 245)[0] if len(data) >= 253 else 0
    creator, base_mint, quote_mint, lp_mint, base_vault, quote_vault = keys
    vs = rpc("getMultipleAccounts", [[base_vault, quote_vault, base_mint], {"encoding": "jsonParsed", "commitment": "confirmed"}])
    bv, qv, mint = (x["data"]["parsed"]["info"] for x in vs["value"][:3])
    ext = [e.get("extension") for e in (mint.get("extensions") or [])]
    return {"pool": pool, "owner": v["owner"], "data_len": len(data), "slot": slot, "vslot": vs["context"]["slot"], "base_mint": base_mint, "quote_mint": quote_mint,
            "base_vault": base_vault, "quote_vault": quote_vault, "vault_mints_ok": bv["mint"] == base_mint and qv["mint"] == quote_mint,
            "base_raw": int(bv["tokenAmount"]["amount"]), "quote_raw": int(qv["tokenAmount"]["amount"]), "base_dec": bv["tokenAmount"]["decimals"],
            "quote_dec": qv["tokenAmount"]["decimals"], "token_program": vs["value"][2]["owner"], "mint_extensions": ext,
            "mint_authority": mint.get("mintAuthority"), "freeze_authority": mint.get("freezeAuthority"), "virtual_quote_raw": virtual_quote}


def implied_fee_buy(Rq: int, Rb: int, q_in: int, b_out: int) -> dict:
    net = b_out * Rq / (Rb - b_out)                    # quote that reached the curve for that output
    return {"fee_on_input": 1 - net / q_in, "fee_on_top": q_in / net - 1}


def implied_fee_sell(Rq: int, Rb: int, b_in: int, q_out: int) -> dict:
    gross = Rq * b_in / (Rb + b_in)                    # curve output before any fee taken from the output
    eff_in = q_out * Rb / (Rq - q_out)                 # token that reached the curve if the fee was taken from the input
    return {"fee_on_output": 1 - q_out / gross, "fee_on_input": 1 - eff_in / b_in}


def check(pool: str) -> dict:
    st = pool_state(pool)
    out = {"state": st, "quotes": [], "t": time.time()}
    if st["owner"] != PAMM or not st["vault_mints_ok"]:
        out["error"] = "not a PumpSwap pool or layout check failed"
        return out
    Rb, Rq_vault = st["base_raw"], st["quote_raw"]
    Rq = Rq_vault + st["virtual_quote_raw"]             # effective quote reserve (X.pumpswap_effective)
    qd = st["quote_dec"]
    for qin in (0.05, 0.5, 5.0):                        # quote units (SOL for SOL-quoted pools)
        amt = int(qin * 10 ** qd)
        q = jup(st["quote_mint"], st["base_mint"], amt)
        hop = (q.get("routePlan") or [{}])[0].get("swapInfo", {})
        b_out = int(q["outAmount"]) if "outAmount" in q else None
        row = {"side": "BUY", "in_raw": amt, "jup_out_raw": b_out, "amm_key": hop.get("ammKey"), "same_pool": hop.get("ammKey") == pool,
               "quote_slot": q.get("contextSlot"), "price_impact_pct": q.get("priceImpactPct"), "error": q.get("error")}
        if b_out and row["same_pool"]:
            row["implied"] = implied_fee_buy(Rq, Rb, amt, b_out)
            row["implied_vault_only"] = implied_fee_buy(Rq_vault, Rb, amt, b_out)
            for f in (0.0025, 0.003, 0.0055, 0.0125):
                model = X.cpmm_out_raw(Rq, Rb, amt, int(f * 1_000_000), 1_000_000)
                row[f"model_out_fee_{f}"] = model
                row[f"rel_err_fee_{f}"] = model / b_out - 1
        out["quotes"].append(row)
    sell_in = (out["quotes"][1].get("jup_out_raw") or 0)
    if sell_in:
        q = jup(st["base_mint"], st["quote_mint"], sell_in)
        hop = (q.get("routePlan") or [{}])[0].get("swapInfo", {})
        q_out = int(q["outAmount"]) if "outAmount" in q else None
        row = {"side": "SELL", "in_raw": sell_in, "jup_out_raw": q_out, "amm_key": hop.get("ammKey"), "same_pool": hop.get("ammKey") == pool,
               "quote_slot": q.get("contextSlot"), "price_impact_pct": q.get("priceImpactPct"), "error": q.get("error")}
        if q_out and row["same_pool"]:
            row["implied"] = implied_fee_sell(Rq, Rb, sell_in, q_out)
            row["implied_vault_only"] = implied_fee_sell(Rq_vault, Rb, sell_in, q_out)
            row["round_trip_quote_lost_frac"] = 1 - q_out / out["quotes"][1]["in_raw"]
        out["quotes"].append(row)
    return out


if __name__ == "__main__":
    res = [check(p) for p in sys.argv[1:]]
    print(json.dumps({"retrieved_at": time.time(), "results": res}, indent=1))

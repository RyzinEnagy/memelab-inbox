"""Phase 12 scenario report on real present-day pools (from the Phase 07 live spot-check) plus empirical cohorts.
    python audits/backtesting/stress/p12_scenarios.py > audits/backtesting/stress/p12_scenarios.json
Snapshots use on-chain effective reserves, the pool's observed fee tier and Jupiter's observed sell quote; SOL/USD
104.21 from a Jupiter SOL->USDC quote taken the same hour. Hypothetical shocks only; cohorts are historical and
reported separately.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import store, stress as S  # noqa: E402

SOL_USD = 104.20737
TIER = {"5wNu5QhdpRGrL37ffcd6TMMqZugQgxwafgz477rShtHy": 0.003, "3KFCgJ5R3zshW8hTDbzjSrrKSRYmKvsMfhc4Vo4iddxD": 0.0055}


def main():
    spot = json.loads((Path(__file__).resolve().parents[1] / "execution" / "p07_spotcheck.json").read_text())
    out = {"sol_usd": SOL_USD, "pools": [], "cohorts": {}}
    for r in spot["results"]:
        st = r["state"]
        if st["pool"] not in TIER:
            continue                                   # SOL-quoted pools only (USD conversion is direct)
        q_sol = (st["quote_raw"] + st["virtual_quote_raw"]) / 10 ** st["quote_dec"]
        b = st["base_raw"] / 10 ** st["base_dec"]
        price = q_sol / b * SOL_USD
        sell = next(x for x in r["quotes"] if x["side"] == "SELL")
        tokens = sell["in_raw"] / 10 ** st["base_dec"]
        quotes = [(tokens * price, sell["jup_out_raw"] / 1e9 * SOL_USD, None, "OK")]
        snap = S.Snapshot(chain="solana", mint=st["base_mint"], as_of=r["t"], price_usd=price, liquidity_usd=2 * q_sol * SOL_USD, pool_type="CPMM",
                          quote_asset="SOL", sol_usd=SOL_USD, transfer_fee_bps=0.0, mint_authority_active=bool(st["mint_authority"]),
                          freeze_authority_active=bool(st["freeze_authority"]), invalidation_price=price * 0.8, sell_quotes=quotes,
                          swap_fee=TIER[st["pool"]], fee_basis="OBSERVED")
        rep = S.stress(snap, [500, 5_000, 25_000, 100_000], max_loss_usd=1_000, max_exit_impact=0.05)
        out["pools"].append({"pool": st["pool"], "mint": st["base_mint"], "price_usd": price, "liquidity_usd": snap.liquidity_usd, "fee": snap.swap_fee,
                             "decision": rep["decision"], "decision_reasons": rep["decision_reasons"], "max_size": rep["max_size"],
                             "table": [{k: x.get(k) for k in ("scenario", "size_usd", "status", "ret", "proceeds_usd", "exit_impact", "realizable_vs_marked", "capped_by_observed_quote")}
                                       for x in rep["scenarios"]], "probabilities": rep["probabilities"]})
    con = store.connect()
    for status in ("ENTRY CONDITIONS MET", "NEAR ENTRY", "SETUP DEVELOPING", "WATCH", "REJECTED"):
        out["cohorts"][status] = S.empirical_cohort(con, status, horizon_h=24, min_n=30)
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))

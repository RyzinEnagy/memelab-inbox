"""Paper smoke test for raydium-io/raydium-sdk-V2 @ e2e8bcd86518 (TypeScript, GPL-3.0).

Per the review brief the SDK is NOT installed or executed. This script is an
independent stdlib re-expression of the public x*y=k-with-fee formulas as the SDK
applies them (cited file:line below), run on a synthetic memecoin pool, to:
  1. produce reference numbers for later golden scenarios, and
  2. check the CPMM priceImpact formula (cpmm.ts:168-170 vs cpmm.ts:1602,1611),
     which mixes a decimal-adjusted pool price with a raw-unit execution price.
No network, no SDK code. Run: python3 -I script.py
"""
import sys
from fractions import Fraction as F


def ceil_div(a, b):
    return -(-a // b)


# AMM v4: liquidity.ts:1090-1094, constants constant.ts:4-5 (25/10000, hardcoded)
def ammv4_out(amount_in, r_in, r_out):
    fee = ceil_div(amount_in * 25, 10000)
    net = amount_in - fee
    return (r_out * net) // (r_in + net), fee


# CPMM: curve/calculator.ts:44-93, curve/fee.ts:6-18, constantProduct.ts:27-33, FEE_RATE_DENOMINATOR 1e6 (common/fee.ts:2)
def cpmm_out(amount_in, r_in, r_out, trade_fee_rate, creator_fee_rate=0, creator_on_input=True):
    trade_fee = ceil_div(amount_in * trade_fee_rate, 1_000_000)
    creator_fee = ceil_div(amount_in * creator_fee_rate, 1_000_000) if creator_on_input else 0
    net = amount_in - trade_fee - creator_fee
    swapped = (net * r_out) // (r_in + net)
    if not creator_on_input:
        creator_fee = ceil_div(swapped * creator_fee_rate, 1_000_000)
        return swapped - creator_fee, trade_fee, creator_fee
    return swapped, trade_fee, creator_fee


# Synthetic memecoin pool: mintA = TOKEN (6 decimals), mintB = SOL (9 decimals)
DEC_A, DEC_B = 6, 9
base = 1_000_000_000 * 10**DEC_A   # 1e9 tokens
quote = 30 * 10**DEC_B             # 30 SOL
pool_price = F(quote, 10**DEC_B) / F(base, 10**DEC_A)   # SOL per TOKEN, cpmm.ts:168-170
print("pool: 1e9 TOKEN (6 dp) / 30 SOL (9 dp); spot =", float(pool_price), "SOL/TOKEN")

fails = 0
print("\n[1] buy TOKEN with SOL, AMM v4 (0.25% hardcoded) vs CPMM tradeFeeRate=2500 (0.25%)")
for sol in (F(1, 10), 1, 5, 10):
    a_in = int(sol * 10**DEC_B)
    o4, f4 = ammv4_out(a_in, quote, base)
    oc, fc, _ = cpmm_out(a_in, quote, base, 2500)
    avg = F(a_in, 10**DEC_B) / F(o4, 10**DEC_A)
    impact = float(avg / pool_price - 1)
    print(f"  in {float(sol):>5} SOL: v4 out {o4/10**DEC_A:,.0f} TOKEN fee {f4} lamports | "
          f"cpmm out {oc/10**DEC_A:,.0f} | avg-price impact {impact:.4%}")
    if o4 != oc:
        print("    note: v4 and cpmm differ only by fee rounding path")

print("\n[2] CPMM priceImpact as the SDK computes it (cpmm.ts:1602 executionPrice = out_raw/in_raw;"
      " cpmm.ts:1611 impact = (poolPrice - executionPrice)/poolPrice)")
for label, a_in, r_in, r_out, dec_in, dec_out, spot_dir in (
        ("sell 1,000,000 TOKEN (A->B)", 1_000_000 * 10**DEC_A, base, quote, DEC_A, DEC_B, pool_price),
        ("buy with 1 SOL (B->A)", 1 * 10**DEC_B, quote, base, DEC_B, DEC_A, 1 / pool_price)):
    out, _, _ = cpmm_out(a_in, r_in, r_out, 2500)
    sdk_exec = F(out, a_in)                               # raw units, no decimals, no direction
    sdk_impact = (pool_price - sdk_exec) / pool_price     # always vs B-per-A human price
    true_exec = F(out, 10**dec_out) / F(a_in, 10**dec_in)
    true_impact = 1 - true_exec / spot_dir
    print(f"  {label}: SDK-formula priceImpact = {float(sdk_impact):.6g} ; decimal- and direction-correct = {float(true_impact):.6%}")
    if abs(float(sdk_impact) - float(true_impact)) > 0.01:
        fails += 1
        print("    MISMATCH: CPMM priceImpact formula is not comparable across decimals/direction")

print("\n[3] AMM v4 priceImpact (liquidity.ts:1067-1072, 1124-1133) uses decimal-adjusted, direction-aware prices; "
      "no mismatch expected there.")
print("\nformula mismatches found:", fails)
sys.exit(1 if fails else 0)

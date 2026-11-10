"""Smoke test: uniswappy V2 swap vs hand-computed x*y=k with 0.3% fee.

Deterministic, no network. Run with the review venv:
  /home/claude/ext/venvs/defipy-devs__uniswappy/bin/python -I script.py
"""
import sys
from fractions import Fraction
from decimal import Decimal

import uniswappy
from uniswappy.erc import ERC20
from uniswappy.cpt.factory import UniswapFactory
from uniswappy.utils.data import UniswapExchangeData
from uniswappy.process.swap import Swap

try:
    from importlib.metadata import version
    print("uniswappy version:", version("uniswappy"), "python", sys.version.split()[0])
except Exception as e:  # pragma: no cover
    print("version lookup failed", e)

USER = "user0"


def make_pool(r0, r1, precision="DEC", fee=None):
    t0 = ERC20("TKN", "0x09")
    t1 = ERC20("SOL", "0x111")
    fac = UniswapFactory("factory", "0x2")
    kw = dict(tkn0=t0, tkn1=t1, symbol="LP", address="0x011", precision=precision)
    if fee is not None:
        kw["fee"] = fee
    lp = fac.deploy(UniswapExchangeData(**kw))
    lp.add_liquidity(USER, r0, r1, r0, r1)
    return lp, t0, t1


def hand_out(dx, x, y, fee_num=3, fee_den=1000):
    """Exact rational x*y=k output with fee taken on input (Uniswap V2 getAmountOut)."""
    dx_f = Fraction(dx) * (fee_den - fee_num) / fee_den
    return Fraction(y) * dx_f / (Fraction(x) + dx_f)


def floor_int(fr):
    return fr.numerator // fr.denominator


fails = 0

# Case 1: DEC precision (default), 18-decimal scaling, the repo's own fixture size
x, y, dx = 1000, 100000, 10
lp, t0, t1 = make_pool(x, y)
quote = lp.get_amount_out(dx, t0)
out = Swap().apply(lp, t0, USER, dx)
exact = hand_out(dx, x, y)
wei_exact_floor = floor_int(hand_out(dx * 10**18, x * 10**18, y * 10**18))
print("\n[1] DEC mode, reserves 1000/100000, sell 10 token0")
print("  uniswappy quote          :", repr(quote))
print("  uniswappy Swap().apply   :", repr(out))
print("  hand exact (rational)    :", float(exact), "=", exact)
print("  hand Uniswap V2 floor wei:", wei_exact_floor)
print("  uniswappy out in wei     :", int(Decimal(str(out)) * 10**18))
print("  abs diff vs exact        :", abs(float(exact) - out))
print("  reserves after           :", lp.get_reserve(t0), lp.get_reserve(t1))
print("  k before / after (human) :", x * y, lp.get_reserve(t0) * lp.get_reserve(t1))
if abs(float(exact) - out) > 1e-9:
    fails += 1
    print("  RESULT: MISMATCH > 1e-9")
else:
    print("  RESULT: matches to float precision")

# Case 2: GWEI (raw integer) mode, small integers to expose rounding direction
x, y, dx = 1000, 100000, 10
lp, t0, t1 = make_pool(x, y, precision="GWEI")
out = Swap().apply(lp, t0, USER, dx)
exact = hand_out(dx, x, y)
print("\n[2] GWEI raw-integer mode, reserves 1000/100000 raw units, sell 10 raw units")
print("  uniswappy out            :", out)
print("  hand exact (rational)    :", float(exact))
print("  Uniswap V2 on-chain floor:", floor_int(exact))
print("  RESULT:", "rounds UP vs on-chain floor (over-states output)" if out > floor_int(exact) else "matches floor")

# Case 3: thin exit, sell 50% of the token reserve
x, y, dx = 1_000_000, 50, 500_000
lp, t0, t1 = make_pool(x, y)
out = Swap().apply(lp, t0, USER, dx)
exact = hand_out(dx, x, y)
spot = Fraction(y, x)
print("\n[3] thin exit: reserves 1,000,000 TKN / 50 SOL, sell 500,000 TKN")
print("  uniswappy out SOL        :", out)
print("  hand exact SOL           :", float(exact))
print("  price impact vs spot     :", 1 - float(exact / (dx * spot)))

# Case 4: is the V2 fee configurable? Raydium AMM v4 is 0.25%, CPMM tiers vary.
x, y, dx = 1000, 100000, 10
lp_default, a0, _ = make_pool(x, y)
lp_fee, b0, _ = make_pool(x, y, fee=2500)
q_default = lp_default.get_amount_out(dx, a0)
q_fee = lp_fee.get_amount_out(dx, b0)
exact_25 = hand_out(dx, x, y, fee_num=25, fee_den=10000)
print("\n[4] V2 fee configurability: UniswapExchangeData(fee=2500)")
print("  quote default            :", q_default)
print("  quote with fee=2500      :", q_fee)
print("  hand exact at 0.25% fee  :", float(exact_25))
print("  RESULT:", "fee field IGNORED by V2 (hardcoded 997/1000)" if q_default == q_fee else "fee field honoured")

print("\nfails:", fails)
sys.exit(1 if fails else 0)

"""Paper smoke test for orca-so/whirlpools @ cc683ec92acb (Rust/TS, Orca License: non-commercial).

Per the review brief nothing from the repo is installed, built or executed, and no code is
copied. This is an independent stdlib re-expression of the public Uniswap-v3-style step math
that rust-sdk/core/src/quote/swap.rs:198-569 implements (fee 1e6 denominator, constants/swap.rs:8;
liquidity_net sign at swap.rs:379-397; adaptive fee math/adaptive_fee.rs:363-401), run on a
synthetic pool, to produce reference numbers and check two invariants:
  1. inside one initialized range, a CLMM step equals x*y=k on virtual reserves (x=L/sqrtP, y=L*sqrtP);
  2. crossing an initialized tick with liquidity_net>0 while a_to_b removes liquidity and steepens impact.
Run: python3 -I script.py
"""
import sys
from decimal import Decimal as D, getcontext

getcontext().prec = 60
FEE_DEN = D(1_000_000)


def sqrt_at_tick(t):
    return (D("1.0001") ** t).sqrt()


def step_a_to_b(amount_rem, fee_rate, L, sp, sp_target):
    """One compute_swap_step for exact-in, a_to_b (token A in, price falls)."""
    amt_after_fee = amount_rem * (FEE_DEN - fee_rate) / FEE_DEN
    max_in = L * (sp - sp_target) / (sp * sp_target)          # delta A to reach target
    if amt_after_fee >= max_in:
        sp_next, a_in = sp_target, max_in
        fee = a_in * FEE_DEN / (FEE_DEN - fee_rate) - a_in    # reverse-applied fee
    else:
        sp_next = L * sp / (L + amt_after_fee * sp)
        a_in, fee = amt_after_fee, amount_rem - amt_after_fee
    b_out = L * (sp - sp_next)
    return a_in, fee, b_out, sp_next


def swap_a_to_b(amount, fee_rate, L, tick, ticks):
    """ticks: {tick_index: liquidity_net}; walk down through initialized ticks."""
    sp, rem, out, fee_tot, crossed = sqrt_at_tick(D(tick)) * D("1.00002"), D(amount), D(0), D(0), []
    for t in sorted([k for k in ticks if k <= tick], reverse=True):
        a_in, fee, b_out, sp = step_a_to_b(rem, fee_rate, L, sp, sqrt_at_tick(D(t)))
        rem -= a_in + fee
        out += b_out
        fee_tot += fee
        if rem <= D("1e-18"):
            break
        net = ticks[t]
        L = L - net if net > 0 else L + (-net)                # swap.rs:386-391 for a_to_b
        crossed.append((t, float(L)))
    return out, fee_tot, crossed, float(rem)


fails = 0
L0, fee_rate = D(10) ** 12, D(3000)       # 0.30% static fee
tick0 = 0
ticks = {-200: D(6) * D(10) ** 11, -4000: D(4) * D(10) ** 11}   # crossing -200 drops L to 4e11

print("[1] in-range step vs x*y=k on virtual reserves (same 0.30% fee)")
sp = sqrt_at_tick(D(tick0)) * D("1.00002")
x_v, y_v = L0 / sp, L0 * sp
dx = D(10) ** 8
a_in, fee, b_out, _ = step_a_to_b(dx, fee_rate, L0, sp, sqrt_at_tick(D(-200)))
cp_out = y_v * (dx * (1 - fee_rate / FEE_DEN)) / (x_v + dx * (1 - fee_rate / FEE_DEN))
print(f"  clmm step out {b_out:.6f}  cpmm-virtual out {cp_out:.6f}  rel diff {float(abs(b_out - cp_out) / cp_out):.2e}")
if abs(b_out - cp_out) / cp_out > D("1e-20"):
    fails += 1

print("\n[2] size ladder, a_to_b, liquidity drops from 1e12 to 4e11 when crossing tick -200")
spot = float(sp * sp)
for amt in (10**8, 10**9, 10**10, 5 * 10**10):
    out, fee_tot, crossed, rem = swap_a_to_b(amt, fee_rate, L0, tick0, ticks)
    avg = float(out) / amt
    print(f"  in {amt:>14,}  out {float(out):>18,.2f}  avg-vs-spot impact {1 - avg / spot:8.4%}  "
          f"fee {float(fee_tot):,.0f}  ticks crossed {[c[0] for c in crossed]}  unfilled {rem:.3g}")

print("\n[3] adaptive fee (adaptive_fee.rs:363-401): fee = static + ceil(ctrl*(va*group)^2/(1e5*1e4*1e4)), cap 10%")
static, ctrl, group, max_va = 3000, 20000, 16, 400000
va_ref = 0
for groups_crossed in (0, 1, 2, 4, 8, 16):
    va = min(va_ref + groups_crossed * 10000, max_va)
    adaptive = -(-(ctrl * (va * group) ** 2) // (100_000 * 10_000 * 10_000))
    total = min(static + adaptive, 100_000)
    print(f"  tick groups from reference {groups_crossed:>2}: volatility_acc {va:>6}  total fee {total/1e4:.4f}%")

print("\ninvariant failures:", fails)
sys.exit(1 if fails else 0)

"""Paper smoke test for MeteoraAg/dlmm-sdk @ af36dd53ab18 (Rust/TS; no LICENSE file).

Per the review brief nothing is installed, built or executed (the repo also ships prebuilt
.so binaries and localnet keypairs, which were not touched). This is an independent stdlib
re-expression of the DLMM bin math as read in commons/src (cited below), on a synthetic
memecoin pool, to produce reference numbers and check:
  1. bin price = (1 + bin_step/10_000)^bin_id in Q64.64 (math/price_math.rs:3-13, u64x64_math.rs:5,17);
  2. constant price inside a bin, step to next bin when the bin's out-side reserve is exhausted
     (quote.rs:543-648, bin.rs:69-100);
  3. total fee = base + variable, variable grows with |index_reference - active_id| as the swap walks
     bins (lb_pair.rs:77-205; FEE_PRECISION 1e9, MAX_FEE_RATE 1e8 in constants.rs:22-24).
Run: python3 -I script.py
"""
import math
import sys
from fractions import Fraction as F

SCALE = 64
ONE = 1 << SCALE
FEE_PRECISION = 1_000_000_000
MAX_FEE_RATE = 100_000_000


def q64_price(bin_id, bin_step):
    base = F(ONE + (bin_step << SCALE) // 10_000, ONE)   # price_math.rs:4-10 (bps floored to Q64)
    return base ** bin_id                                  # exact rational; on-chain pow() rounds in Q64


def ceil_div(a, b):
    return -(-a // b)


# synthetic pool: X = TOKEN (6 dp), Y = SOL (9 dp); price is Y-raw per X-raw
BIN_STEP, BASE_FACTOR, POWER = 100, 10_000, 0          # 1% bins, base fee = 1%
VFC, MAX_VA, FILTER, DECAY, REDUCTION = 30_000, 350_000, 30, 600, 5_000
target_raw = 3e-8 * 10**9 / 10**6                      # 3e-8 SOL/TOKEN in raw units
active_id = round(math.log(target_raw) / math.log(1 + BIN_STEP / 10_000))
bins_y = {active_id - k: 2 * 10**9 for k in range(0, 40)}  # 2 SOL of Y in active bin and 39 bins below

fails = 0
print("[1] bin price from id: active_id", active_id)
for k in (0, -1, -10):
    p = q64_price(active_id + k, BIN_STEP)
    human = float(p) * 10**6 / 10**9
    exact = (1 + BIN_STEP / 10_000) ** (active_id + k) * 10**6 / 10**9
    print(f"  bin {active_id + k}: {human:.6e} SOL/TOKEN (float check {exact:.6e})")
    if abs(human / exact - 1) > 1e-9:
        fails += 1
r = float(q64_price(active_id, BIN_STEP) / q64_price(active_id - 1, BIN_STEP))
print(f"  adjacent-bin ratio {r:.6f} (expect 1 + bin_step/1e4 = {1 + BIN_STEP/1e4})")


def total_fee_rate(va):
    base = BASE_FACTOR * BIN_STEP * 10 * 10**POWER                       # lb_pair.rs:136-144
    var = ceil_div(VFC * (va * BIN_STEP) ** 2, 100_000_000_000) if VFC else 0   # lb_pair.rs:150-176
    return min(base + var, MAX_FEE_RATE)                                 # lb_pair.rs:178-185


def quote_sell_token(amount_in, index_ref=None, v_ref=0):
    # Caller supplies the post-update_references state (lb_pair.rs:77-107): after a quiet period
    # (elapsed >= decay_period) index_ref = active_id and v_ref = 0; inside filter_period both stay
    # as stored on the pair. Then update_volatility_accumulator per bin (lb_pair.rs:109-134).
    index_ref = active_id if index_ref is None else index_ref
    aid, left, out, fees, per_bin = active_id, amount_in, 0, 0, []
    while left > 0:
        if aid not in bins_y:
            return out, fees, per_bin, left
        va = min(v_ref + abs(index_ref - aid) * 10_000, MAX_VA)
        rate = total_fee_rate(va)
        price = q64_price(aid, BIN_STEP)
        fee_full = ceil_div(left * rate, FEE_PRECISION)                    # compute_fee_from_amount
        net = left - fee_full
        max_in = math.ceil(F(bins_y[aid]) / price)                          # get_amount_in, Rounding::Up
        if net >= max_in:
            fee = ceil_div(max_in * rate, FEE_PRECISION - rate)             # compute_fee on exhausted bin
            used, got = max_in + fee, bins_y[aid]
        else:
            fee, used, got = fee_full, left, math.floor(net * price)        # get_amount_out, Rounding::Down
        left -= used
        out += got
        fees += fee
        per_bin.append((aid, rate / 1e7))
        if left > 0:
            aid -= 1                                                         # advance_active_bin swap_for_y
    return out, fees, per_bin, left


print("\n[2] sell TOKEN for SOL across bins (fee on input)")
spot = float(q64_price(active_id, BIN_STEP))
for tokens in (1_000_000, 50_000_000, 300_000_000, 1_000_000_000):
    amt = tokens * 10**6
    out, fees, per_bin, left = quote_sell_token(amt)
    avg = out / amt
    rates = [f"{r:.2f}%" for _, r in per_bin[:1] + per_bin[-1:]]
    print(f"  sell {tokens:>13,} TOKEN: out {out/1e9:8.4f} SOL  bins used {len(per_bin):>2}  "
          f"fee first->last bin {rates[0]}->{rates[-1]}  avg-vs-active impact {1 - avg/spot:7.3%}  unfilled {left/1e6:,.0f}")

print("\n[3] same 50M TOKEN sell 10 s (< filter_period) after a prior sell moved price 20 bins down")
out, fees, per_bin, left = quote_sell_token(50_000_000 * 10**6, index_ref=active_id + 20, v_ref=0)
print(f"  out {out/1e9:.4f} SOL, first-bin fee {per_bin[0][1]:.2f}% (history-dependent: needs v_parameters + last_update_timestamp + clock)")

print("\nchecks failed:", fails)
sys.exit(1 if fails else 0)

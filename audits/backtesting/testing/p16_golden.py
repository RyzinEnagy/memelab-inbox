"""Phase 16 independent golden math. The expected values are computed here with exact rational arithmetic
(fractions.Fraction) from the constant-product formula written out by hand; the package is only called to produce
the value under test. Run from the repo root: python3 audits/backtesting/testing/p16_golden.py
Prints a JSON report and exits 1 if any comparison is outside its tolerance."""
from __future__ import annotations

import json
import sys
from fractions import Fraction as Fr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import execution as X  # noqa: E402  (value under test only)
from memelab.backtest.engine import Engine, EngineConfig, TokenData  # noqa: E402
from memelab.backtest.strategies.base import Exits, Signal, Strategy  # noqa: E402
from memelab.backtest.strategies.features import B  # noqa: E402

REL = 1e-9
rows = []


def cmp(case: str, what: str, mine, theirs, rel=REL):
    mine_f = float(mine)
    ok = abs(mine_f - theirs) <= rel * max(1.0, abs(mine_f))
    rows.append({"case": case, "quantity": what, "independent": mine_f, "package": theirs, "abs_diff": abs(mine_f - theirs), "ok": ok})
    return ok


# ---------------------------------------------------------------- G09: CPMM sell with explicit reserves and fee
def g09():
    rb, rq = Fr(2_000_000), Fr(500)            # tokens, SOL
    fee = Fr(3, 1000)                           # 0.30% swap fee on the input
    sell = Fr(100_000)
    net = sell * (1 - fee)                      # 99,700 tokens reach the curve
    out = rq * net / (rb + net)                 # 500 * 99700 / 2099700
    new_b, new_q = rb + sell, rq - out          # the fee stays in the pool
    assert new_b > 0 and new_q > 0
    k0, k1 = rb * rq, new_b * new_q
    f, p2 = X.CpmmPool(float(rb), float(rq), X.Fees(float(fee), 0, None, 0.0)).sell(float(sell))
    cmp("G09 sell 100k tokens, fee 0.30%", "SOL out", out, f.out)
    cmp("G09 sell 100k tokens, fee 0.30%", "reserve_base after", new_b, p2.reserve_base)
    cmp("G09 sell 100k tokens, fee 0.30%", "reserve_quote after", new_q, p2.reserve_quote)
    cmp("G09 sell 100k tokens, fee 0.30%", "avg price SOL/token", out / sell, f.avg_price)
    rows.append({"case": "G09", "quantity": "k grows (fee retained), no negative reserve", "independent": float(k1 / k0), "package": p2.reserve_base * p2.reserve_quote / (float(rb) * float(rq)),
                 "abs_diff": 0.0, "ok": k1 > k0 and p2.reserve_base * p2.reserve_quote > float(k0)})
    # Token-2022 transfer fee of 1% on the token leg, then the swap fee: each applied once
    tf = Fr(100, 10_000)
    arrives = sell * (1 - tf)
    out2 = rq * arrives * (1 - fee) / (rb + arrives * (1 - fee))
    f2, p3 = X.CpmmPool(float(rb), float(rq), X.Fees(float(fee), 100, None, 0.0)).sell(float(sell))
    cmp("G09 sell with 1% transfer fee", "SOL out", out2, f2.out)
    cmp("G09 sell with 1% transfer fee", "reserve_base after (pool gets arrived tokens)", rb + arrives, p3.reserve_base)
    # round trip never makes money
    buy_q = Fr(10)
    tok = rb * buy_q * (1 - fee) / (rq + buy_q * (1 - fee))
    rb2, rq2 = rb - tok, rq + buy_q
    back = rq2 * tok * (1 - fee) / (rb2 + tok * (1 - fee))
    rt = X.round_trip(X.CpmmPool(float(rb), float(rq), X.Fees(float(fee), 0, None, 0.0)), float(buy_q))
    cmp("G09 round trip 10 SOL", "SOL back", back, rt["proceeds_quote"])
    rows.append({"case": "G09", "quantity": "round trip returns less than paid", "independent": float(back), "package": rt["proceeds_quote"], "abs_diff": 0.0,
                 "ok": back < buy_q and rt["proceeds_quote"] < float(buy_q)})


# ---------------------------------------------------------------- G10: size ladder in thin reserves
def g10():
    side = Fr(20_000)                            # $20k a side at $1 (thin)
    fee = Fr(25, 10_000)
    out = {}
    for size in (1_000, 10_000, 100_000):
        s = Fr(size)
        tok = side * s * (1 - fee) / (side + s * (1 - fee))
        avg = s / tok
        f, p2 = X.CpmmPool(20_000.0, 20_000.0, X.Fees(float(fee), 0, None, 0.0)).buy(float(size))
        cmp(f"G10 buy ${size:,} in $20k/side pool", "tokens", tok, f.out)
        cmp(f"G10 buy ${size:,} in $20k/side pool", "avg price", avg, f.avg_price)
        # selling the same tokens back into the post-trade pool
        rb2, rq2 = side - tok, side + s
        back = rq2 * tok * (1 - fee) / (rb2 + tok * (1 - fee))
        s2, _ = p2.sell(f.out)
        cmp(f"G10 buy ${size:,} then sell back", "USD back", back, s2.out)
        # selling a position worth `size` at today's mid (exit capacity)
        sell_tok = s                              # mid is $1
        exitp = side * sell_tok * (1 - fee) / (side + sell_tok * (1 - fee))
        s3, _ = X.CpmmPool(20_000.0, 20_000.0, X.Fees(float(fee), 0, None, 0.0)).sell(float(sell_tok))
        cmp(f"G10 exit ${size:,} marked position", "USD proceeds", exitp, s3.out)
        out[size] = {"entry_avg_price": float(avg), "entry_impact": float(avg - 1), "exit_proceeds_per_marked_dollar": float(exitp / s)}
    # In a constant-product pool the average BUY price is linear in size (avg = q/(b(1-f)) + s/b), so the non-linear
    # effect G10 asks about is on SALES: proceeds per marked dollar fall hyperbolically, b(1-f)/(b + s(1-f)).
    p = {k: v["exit_proceeds_per_marked_dollar"] * k for k, v in out.items()}
    nonlinear = p[10_000] < 10 * p[1_000] and p[100_000] < 10 * p[10_000]
    rows.append({"case": "G10", "quantity": "sale proceeds grow less than size (non-linear worse fills)", "independent": json.dumps(out), "package": None, "abs_diff": 0.0,
                 "ok": bool(nonlinear and out[1_000]["exit_proceeds_per_marked_dollar"] > out[10_000]["exit_proceeds_per_marked_dollar"] > out[100_000]["exit_proceeds_per_marked_dollar"])})
    return out


# ---------------------------------------------------------------- engine helpers
T0 = 1_800_000_000.0
H = 3600.0


def bars(rows_):
    return [B(T0 + i * H, T0 + (i + 1) * H, o, h, l, c, v, T0 + (i + 1) * H) for i, (o, h, l, c, v) in enumerate(rows_)]


class At(Strategy):
    """audit strategy: one signal when the closed bar index equals `at`, stop as a fraction below the last close"""
    id, version = "P16_AT", "1"
    default_params = {"at": 5, "stop_frac": 0.1, "hold": None}

    def evaluate(self, chain, mint, bs, d, ctx=None):
        if len(bs) - 1 != self.params["at"]:
            return None
        last = bs[-1]
        return Signal(self.id, self.version, chain, mint, last.end, d, "BUY",
                      Exits(last.c * (1 - self.params["stop_frac"]), max_hold_s=self.params["hold"] * H if self.params["hold"] else None),
                      {}, self.phash, "audit", latest_input_available_at=last.avail)


def snap_pool(L: Fr, price: Fr, haircut: Fr):
    side = L / 2 * haircut
    return side / price, side                     # base tokens, quote USD


def buy_tokens(base, quote, s, fee):
    return base * s * (1 - fee) / (quote + s * (1 - fee))


def sell_usd(base, quote, tok, fee):
    return quote * tok * (1 - fee) / (base + tok * (1 - fee))


# ---------------------------------------------------------------- G25: stop gap-through, LIQ_SNAPSHOT_APPROX fills
def g25():
    L, fee, sol, size, hc = Fr(1_000_000), Fr(25, 10_000), Fr(150), Fr(500), Fr(4, 5)
    nfee = Fr(105, 1_000_000) * sol
    flat = (1.0, 1.01, 0.99, 1.0, 100.0)
    res = {}
    for name, crash_bar, expect_px, expect_reason in (
            ("gap at open", (0.6, 0.62, 0.55, 0.58, 100.0), Fr(6, 10), "STOP_GAP_FILL_AT_OPEN"),
            ("crash inside bar, close below stop", (0.95, 0.96, 0.40, 0.50, 100.0), Fr(1, 2), "STOP_INTRABAR_CRASH_FILL_AT_CLOSE"),
            ("wick 67% below stop, close above stop", (0.95, 0.96, 0.30, 0.95, 100.0), Fr(9, 10), "STOP_INTRABAR")):
        series = [flat] * 7 + [crash_bar] + [flat] * 3
        td = TokenData("solana", "P16GAP", bars(series), liquidity=[(T0, float(L))])
        cfg = EngineConfig(account_usd=10_000, size_usd=float(size), latency_s=0.0, sol_usd_default=float(sol), fees=X.Fees(float(fee), 0, None, 0.000105),
                           entry_impact_cap=1.0, liquidity_haircut=float(hc))
        r = Engine(cfg).run(At(at=5, stop_frac=0.1), [td])
        tr = r["trades"][0]
        # by hand: entry at the open of bar 6 (1.00), stop 0.90; exit model rebuilt at the exit price from the same snapshot
        b0, q0 = snap_pool(L, Fr(1), hc)
        tok = buy_tokens(b0, q0, size, fee)
        b1, q1 = snap_pool(L, expect_px, hc)
        proceeds = sell_usd(b1, q1, tok, fee) - nfee
        cost = size + nfee
        pnl = proceeds - cost
        intended = size * Fr(1, 10)
        cmp(f"G25 {name}", "exit reason matches", 1, 1.0 if tr["exit_reason"] == expect_reason else 0.0)
        cmp(f"G25 {name}", "exit reference price", expect_px, tr["exit_ref_price"])
        cmp(f"G25 {name}", "cost USD", cost, tr["cost_usd"])
        cmp(f"G25 {name}", "proceeds USD", proceeds, tr["proceeds_usd"])
        cmp(f"G25 {name}", "pnl USD", pnl, tr["pnl_usd"])
        cmp(f"G25 {name}", "final cash = 10,000 + pnl", Fr(10_000) + pnl, r["final_cash"])
        res[name] = {"intended_stop_loss_usd": float(intended), "realized_loss_usd": float(-pnl), "exceeds_intended": float(-pnl) > float(intended)}
    rows.append({"case": "G25", "quantity": "gap and crash losses exceed the intended stop risk; a recovered wick fills at the stop (optimistic, documented)",
                 "independent": json.dumps(res), "package": None, "abs_diff": 0.0,
                 "ok": res["gap at open"]["exceeds_intended"] and res["crash inside bar, close below stop"]["exceeds_intended"]})
    return res


# ---------------------------------------------------------------- G24: 50 same-minute signals, cash conservation
def g24():
    L, fee, sol, size, hc = Fr(400_000), Fr(25, 10_000), Fr(150), Fr(500), Fr(4, 5)
    nfee = Fr(105, 1_000_000) * sol
    acct = Fr(5_000)
    # every token: flat at 1.00 for 6 bars, then rises 1% per bar; hold 3 bars after entry -> time exit at an open
    series = [(1.0, 1.01, 0.99, 1.0, 100.0)] * 6 + [(1.0 + 0.01 * k, 1.01 + 0.01 * k, 0.99 + 0.01 * k, 1.0 + 0.01 * k, 100.0) for k in range(10)]
    toks = [TokenData("solana", f"P16M{i:02d}", bars(series), liquidity=[(T0, float(L))]) for i in range(50)]
    cfg = EngineConfig(account_usd=float(acct), size_usd=float(size), max_positions=50, max_exposure_frac=0.5, latency_s=0.0, sol_usd_default=float(sol),
                       fees=X.Fees(float(fee), 0, None, 0.000105), entry_impact_cap=1.0, liquidity_haircut=float(hc), max_entries_per_token=1)
    r = Engine(cfg).run(At(at=5, stop_frac=0.5, hold=3), toks)
    # by hand: equity before each entry; exposure cap 0.5 x equity at entry; each entry costs size + network fee
    cash, exposure, filled = acct, Fr(0), []
    for i in range(50):
        eq = cash + sum(t for _, t in filled) * Fr(1)    # marked at the last close (1.00) while flat
        if exposure + size > Fr(1, 2) * eq or size > cash:
            continue
        b0, q0 = snap_pool(L, Fr(1), hc)
        tok = buy_tokens(b0, q0, size, fee)
        cash -= size + nfee
        exposure += size + nfee
        filled.append((i, tok))
    # exit: time stop at the open of bar 6 + 3 = bar 9, open = 1.00 + 0.01 * 3
    px = Fr(103, 100)
    pnl_total = Fr(0)
    for i, tok in filled:
        b1, q1 = snap_pool(L, px, hc)
        proceeds = sell_usd(b1, q1, tok, fee) - nfee
        cash += proceeds
        pnl_total += proceeds - (size + nfee)
    cmp("G24 50 signals, $5k account", "entries filled", len(filled), r["counts"]["filled"])
    cmp("G24 50 signals, $5k account", "final cash", cash, r["final_cash"])
    cmp("G24 50 signals, $5k account", "sum of trade pnl", pnl_total, sum(t["pnl_usd"] for t in r["trades"]))
    peak_spent = sum(f["requested"] for f in r["fills"] if f["action"] == "BUY" and f["status"] == "FILLED")
    rows.append({"case": "G24", "quantity": "cash never negative, entries within 0.5 x equity, cash = start + sum(pnl)", "independent": float(cash), "package": r["final_cash"],
                 "abs_diff": abs(float(cash) - r["final_cash"]),
                 "ok": r["final_cash"] > 0 and peak_spent <= 0.5 * float(acct) + 1e-9 and abs(r["final_cash"] - (float(acct) + sum(t["pnl_usd"] for t in r["trades"]))) < 1e-6})
    return {"filled": len(filled), "final_cash": float(cash)}


if __name__ == "__main__":
    out = {"G09": g09(), "G10": g10(), "G25": g25(), "G24": g24()}
    bad = [r for r in rows if not r["ok"]]
    print(json.dumps({"comparisons": rows, "failed": len(bad), "total": len(rows)}, indent=1, default=str))
    sys.exit(1 if bad else 0)

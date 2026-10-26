"""Fill-timing smoke test for nikkisora/PolarBT @ 18f9363a0d131bb5f3a7fb266f7a071b07b0a727.

Safety: PolarBT is a niche repo, so it is NOT pip-installed. Only the 8 modules that
polarbt.core needs (core, commissions, orders, results, slippage, trades, universe,
metrics) were read in full, checked for network/subprocess/eval use (none), copied
byte-identical (sha256 recorded) into a stub package with an EMPTY __init__.py, and
imported from there. Run with `python -I` inside `unshare -rn` (no network).

Synthetic data (deterministic): 30 hourly bars, bar k: open=100+k, close=100.5+k,
high=close+0.25, low=open-0.25. Bar 12 is widened (low 90, high 130) to test the
same-bar stop-loss/take-profit ambiguity. Signal fires on bar k=10 (inside next()).

Usage: python -I script.py <stub_dir>
"""

import sys
from datetime import datetime, timedelta

sys.path.insert(0, sys.argv[1])

import polars as pl  # noqa: E402

from polarbt.core import Engine, Strategy  # noqa: E402
from polarbt.slippage import AMMSlippage  # noqa: E402

K = 10


def make_bars(n: int = 30) -> pl.DataFrame:
    t0 = datetime(2026, 1, 1)
    rows = []
    for k in range(n):
        o, c = 100.0 + k, 100.5 + k
        h, lo = c + 0.25, o - 0.25
        if k == 12:
            h, lo = 130.0, 90.0
        rows.append({"timestamp": t0 + timedelta(hours=k), "open": o, "high": h, "low": lo, "close": c,
                     "volume": 1000.0, "pool_reserve_last": 1000.0})
    return pl.DataFrame(rows)


class BuyAtK(Strategy):
    def __init__(self, sl=None, tp=None, **p):
        super().__init__(**p)
        self.sl, self.tp = sl, tp
        self.seen_close_at_k = None

    def preprocess(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(pl.col("close").rolling_mean(3).alias("sma3"))

    def next(self, ctx) -> None:
        if ctx.bar_index == K:
            self.seen_close_at_k = ctx.row["close"]
            ctx.portfolio.order("asset", 1.0)
        if ctx.bar_index == K + 1 and (self.sl or self.tp):
            # set brackets once the position exists (works for both delays)
            if self.sl:
                ctx.portfolio.set_stop_loss("asset", stop_price=self.sl)
            if self.tp:
                ctx.portfolio.set_take_profit("asset", target_price=self.tp)


def run(order_delay: int, sl=None, tp=None, slippage=0.0):
    strat = BuyAtK(sl=sl, tp=tp)
    eng = Engine(strat, make_bars(), initial_cash=10_000.0, commission=0.0, slippage=slippage,
                 warmup=0, order_delay=order_delay)
    res = eng.run()
    orders = sorted(eng.portfolio.orders.values(), key=lambda o: int(o.order_id.split("_")[1]))
    filled = [o for o in orders if o.filled_bar is not None]
    return strat, res, filled


def main() -> None:
    bars = make_bars()
    print("polars", pl.__version__)
    print(f"bar k={K}: open={bars['open'][K]} close={bars['close'][K]}; bar k+1 open={bars['open'][K+1]} close={bars['close'][K+1]}")
    for d in (0, 1):
        strat, res, filled = run(d)
        e = filled[0]
        print(f"[1] order_delay={d}: signal saw close={strat.seen_close_at_k}; entry filled_bar={e.filled_bar} "
              f"filled_price={e.filled_price}")
    # [2] same-bar SL+TP: long from bar 10 (delay 0), SL=105, TP=118, bar 12 low=90 high=130 open=112
    strat, res, filled = run(0, sl=105.0, tp=118.0)
    ex = [o for o in filled if o.size < 0]
    print(f"[2] SL=105 TP=118 both inside bar 12 (open=112, low=90, high=130): exit filled_bar={ex[0].filled_bar} "
          f"price={ex[0].filled_price}")
    # [3] AMMSlippage vs exact constant product (fee-free): quote reserve X=1000, spot 1.0, trade value 100 and 1000
    m = AMMSlippage()
    for tv in (100.0, 1000.0):
        ctx = {"pool_reserve_last": 1000.0}
        got_buy = m.calculate(1.0, tv, True, ctx)
        got_sell = m.calculate(1.0, tv, False, ctx)
        exact_buy_exact_in = (1000.0 + tv) / 1000.0          # spend tv quote: avg price = (X+dx)/Y with Y=X
        exact_sell = 1000.0 / (1000.0 + tv)                   # sell tv/p base: avg price = X/(Y+dy)
        print(f"[3] trade_value={tv:g}: AMMSlippage buy={got_buy:.4f} (x*y=k exact-in {exact_buy_exact_in:.4f}); "
              f"sell={got_sell:.4f} (x*y=k {exact_sell:.4f})")


if __name__ == "__main__":
    main()

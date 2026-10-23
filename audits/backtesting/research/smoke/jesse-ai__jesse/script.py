"""Smoke test: jesse 3.4.0 research.backtest fill timing on synthetic data (no network, no DB).

NOTE: run on Python 3.12 because jesse 3.4.0 pins numpy~=1.26.4 (no cp313 wheels) and cannot install on 3.13.
Jesse simulates on 1-minute candles. 30 hourly bars are built from 1800 1m candles:
hour i: open=100+i, high=open+2, low=open-1, close=open+0.5.
Case A: should_long() true on the 1h candle with index 10 -> market buy; liquidate on index 20.
Case B: same entry with stop-loss at entry*0.95; hour 15 GAPS DOWN: its first minute opens at 100 (stop ~105.5),
        high 108, low 99 -> stop filled at the stop price or at the gapped open?
"""
import socket

import numpy as np


def _no_net(*a, **k):
    raise RuntimeError("network blocked in smoke test")


socket.socket.connect = _no_net

from jesse import research  # noqa: E402
from jesse.strategies import Strategy  # noqa: E402

T0 = 1767225600000  # 2026-01-01T00:00:00Z in ms
GAP = {"on": False}


def minute_candles(gap):
    rows = []
    for i in range(30):
        o = 100.0 + i
        h, l, c = o + 2, o - 1, o + 0.5
        if gap and i == 15:
            o, h, l, c = 100.0, 108.0, 99.0, 101.0
        for m in range(60):
            ts = T0 + (i * 60 + m) * 60_000
            if m == 0:
                co, cc, ch, cl = o, o, o, o
            elif m == 1:
                co, cc, ch, cl = o, o, h, o
            elif m == 2:
                co, cc, ch, cl = o, o, o, l
            elif m == 59:
                co, cc, ch, cl = o, c, max(o, c), min(o, c)
            else:
                co, cc, ch, cl = o, o, o, o
            rows.append([ts, co, cc, ch, cl, 1000.0])  # jesse order: ts, open, close, high, low, volume
    return np.array(rows)


class Smoke(Strategy):
    def should_long(self):
        return self.index == 10 and not self.position.is_open

    def go_long(self):
        c = self.current_candle
        print(f"  go_long at index={self.index} candle(ts={int(c[0])}, open={c[1]}, close={c[2]}) price={self.price}")
        self.buy = 1, self.price

    def update_position(self):
        if self.index == 20:
            self.liquidate()

    def should_cancel_entry(self):
        return False

    def on_open_position(self, order):
        print(f"  ENTRY filled price={order.price} at executed_at={order.executed_at} "
              f"(hour {(order.executed_at - T0) / 3_600_000:.4f})")
        if GAP["on"]:
            self.stop_loss = self.position.qty, order.price * 0.95  # spot: stop set after entry fill
            print(f"  stop set at {order.price * 0.95}")

    def on_close_position(self, order, closed_trade=None):
        print(f"  EXIT filled price={order.price} type={order.type} at hour {(order.executed_at - T0) / 3_600_000:.4f}")


def run(name, gap):
    GAP["on"] = gap
    print(f"[{name}] hour10 open=110 close=110.5 ; hour11 open=111 ; hour15 gap={gap}")
    config = {"starting_balance": 10_000, "fee": 0, "type": "spot", "futures_leverage": 1,
              "futures_leverage_mode": "cross", "exchange": "Binance Spot", "warm_up_candles": 0}
    routes = [{"exchange": "Binance Spot", "strategy": Smoke, "symbol": "TOK-USDT", "timeframe": "1h"}]
    candles = {"Binance Spot-TOK-USDT": {"exchange": "Binance Spot", "symbol": "TOK-USDT", "candles": minute_candles(gap)}}
    res = research.backtest(config, routes, [], candles)
    m = res["metrics"]
    print(f"  metrics: total_trades={m.get('total')} net_profit={m.get('net_profit')}")


run("A market entry", False)
run("B gap-down stop", True)

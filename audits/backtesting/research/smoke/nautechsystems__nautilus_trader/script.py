"""Smoke test: nautilus_trader (PyPI default = v1 1.231.0) fill timing on synthetic bars, offline.

30 hourly bars (bar events timestamped at bar CLOSE), bar i: open=100+i, high=open+2, low=open-1,
close=open+0.5, volume=VOL. Strategy submits a MARKET BUY inside on_bar for bar k=10.
Case A: qty 1, VOL=1000 -> which price/time does the fill get?
Case B: qty 5000 while bar volume is 10 -> any size-dependent impact or volume cap?
"""
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy

INSTR = TestInstrumentProvider.btcusdt_binance()
BAR_TYPE = BarType.from_str(f"{INSTR.id}-1-HOUR-LAST-EXTERNAL")
T0 = pd.Timestamp("2026-01-01", tz="UTC")


class SmokeConfig(StrategyConfig, frozen=True):
    qty: str = "1"
    k: int = 10


class Smoke(Strategy):
    def __init__(self, config: SmokeConfig):
        super().__init__(config)
        self.i = -1

    def on_start(self):
        self.subscribe_bars(BAR_TYPE)

    def on_bar(self, bar: Bar):
        self.i += 1
        if self.i == self.config.k:
            print(f"  on_bar idx={self.i} ts={pd.Timestamp(bar.ts_event, tz='UTC')} close={bar.close} -> submit MARKET BUY {self.config.qty}")
            self.submit_order(self.order_factory.market(INSTR.id, OrderSide.BUY, INSTR.make_qty(float(self.config.qty))))

    def on_order_filled(self, event):
        print(f"  FILL px={event.last_px} qty={event.last_qty} ts={pd.Timestamp(event.ts_event, tz='UTC')} liquidity={event.liquidity_side}")


def bars(vol):
    out = []
    for i in range(30):
        o = 100 + i
        ts = int((T0 + pd.Timedelta(hours=i + 1)).value)  # close time
        out.append(Bar(BAR_TYPE, Price.from_str(f"{o:.2f}"), Price.from_str(f"{o + 2:.2f}"),
                       Price.from_str(f"{o - 1:.2f}"), Price.from_str(f"{o + 0.5:.2f}"),
                       Quantity.from_str(f"{vol:.6f}"), ts, ts))
    return out


def run(name, qty, vol):
    print(f"[{name}] bar10 open=110 close=110.50 ; bar11 open=111 ; bar volume={vol}")
    eng = BacktestEngine(BacktestEngineConfig(trader_id=TraderId("SMOKE-001"),
                                              logging=LoggingConfig(log_level="ERROR")))
    eng.add_venue(venue=Venue("BINANCE"), oms_type=OmsType.NETTING, account_type=AccountType.CASH,
                  base_currency=None, starting_balances=[Money(10_000_000, USDT)])
    eng.add_instrument(INSTR)
    eng.add_data(bars(vol))
    eng.add_strategy(Smoke(SmokeConfig(qty=qty)))
    eng.run()
    eng.dispose()


run("A qty=1", "1", 1000)
run("B qty=5000 vs bar volume 10", "5000", 10)

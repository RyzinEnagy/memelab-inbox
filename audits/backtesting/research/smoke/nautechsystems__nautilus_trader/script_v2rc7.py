"""Same smoke test as script.py, ported to nautilus_trader 2.0.0rc7 (PyPI pre-release, closest to pinned
2.0.0rc8 develop HEAD). Market BUY submitted in on_bar for bar k=10; offline synthetic bars stamped at bar close."""
from typing import Any, Self

import pandas as pd

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, StrategyConfig
from nautilus_trader.model import AccountType, Bar, BarType, Currency, Money, OmsType, OrderSide, Price, Quantity
from nautilus_trader.model import TraderId, Venue
from nautilus_trader.testkit.providers import TestInstrumentProvider
from nautilus_trader.execution import MakerTakerFeeModel
from decimal import Decimal
from nautilus_trader.trading import Strategy

INSTR = TestInstrumentProvider.btcusdt_binance()
BAR_TYPE = BarType.from_str(f"{INSTR.id}-1-HOUR-LAST-EXTERNAL")
T0 = pd.Timestamp("2026-01-01", tz="UTC")
STATE = {"qty": 1.0}


class Cfg(StrategyConfig):
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        return super().__new__(cls)

    def __init__(self) -> None:
        super().__init__()


class Smoke(Strategy):
    def __init__(self, config: Cfg) -> None:
        super().__init__(config)
        self.i = -1

    def on_start(self) -> None:
        self.subscribe_bars(BAR_TYPE)

    def on_bar(self, bar: Bar) -> None:
        self.i += 1
        if self.i == 10:
            print(f"  on_bar idx={self.i} ts={pd.Timestamp(bar.ts_event, tz='UTC')} close={bar.close} -> MARKET BUY {STATE['qty']}")
            self.submit_order(self.order_factory.market(INSTR.id, OrderSide.BUY, INSTR.make_qty(STATE["qty"])))

    def on_order_filled(self, event) -> None:
        print(f"  FILL px={event.last_px} qty={event.last_qty} ts={pd.Timestamp(event.ts_event, tz='UTC')}")


def bars(vol):
    out = []
    for i in range(30):
        o = 100 + i
        ts = int((T0 + pd.Timedelta(hours=i + 1)).value)
        out.append(Bar(bar_type=BAR_TYPE, open=Price.from_str(f"{o:.2f}"), high=Price.from_str(f"{o + 2:.2f}"),
                       low=Price.from_str(f"{o - 1:.2f}"), close=Price.from_str(f"{o + 0.5:.2f}"),
                       volume=Quantity.from_str(f"{vol:.6f}"), ts_event=ts, ts_init=ts))
    return out


def run(name, qty, vol):
    STATE["qty"] = qty
    print(f"[{name}] bar10 open=110 close=110.50 ; bar11 open=111 ; bar volume={vol}")
    eng = BacktestEngine(BacktestEngineConfig(trader_id=TraderId("SMOKE-001")))
    eng.add_venue(venue=Venue("BINANCE"), oms_type=OmsType.NETTING, account_type=AccountType.CASH,
                  base_currency=None, starting_balances=[Money.from_str("10000000 USDT")],
                  fee_model=MakerTakerFeeModel(Decimal(0), Decimal(0)))
    eng.add_instrument(INSTR)
    eng.add_data(bars(vol))
    eng.add_strategy(Smoke(Cfg()))
    eng.run()
    eng.dispose()


run("A qty=1", 1.0, 1000)
run("B qty=5000 vs bar volume 10", 5000.0, 10)

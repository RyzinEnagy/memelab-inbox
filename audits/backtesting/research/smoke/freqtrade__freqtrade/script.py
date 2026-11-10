"""Smoke test: freqtrade backtesting fill timing on synthetic data, offline (network blocked).

30 hourly bars, bar i: open=100+i, high=open+2, low=open-1, close=open+0.5.
Case A: enter_long signal on bar 10, exit_long signal on bar 20 -> entry/exit price and bar.
Case B: stoploss -5%; bar 15 gaps down: open=100 (below stop), high=108 (above stop), low=99
        -> does the stop fill at the stop price or at the gapped open?
The CEX exchange object is mocked the way freqtrade's own tests do (tests/conftest.py patch_exchange),
because Backtesting() otherwise calls ccxt load_markets over the network at startup.
"""
import socket
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd


def _no_net(*a, **k):
    raise RuntimeError("network blocked in smoke test")


socket.socket.connect = _no_net  # any network attempt fails loudly

from freqtrade.enums import CandleType, RunMode  # noqa: E402
from freqtrade.optimize.backtesting import Backtesting  # noqa: E402
from freqtrade.persistence import LocalTrade  # noqa: E402

HERE = Path(__file__).resolve().parent
EXMS = "freqtrade.exchange.exchange.Exchange"
MARKETS = {
    "TOK/USDT": {
        "id": "tokusdt", "symbol": "TOK/USDT", "base": "TOK", "quote": "USDT", "active": True,
        "spot": True, "swap": False, "linear": None, "type": "spot",
        "precision": {"price": 8, "amount": 8, "cost": 8}, "lot": 1e-8, "contractSize": None,
        "limits": {"amount": {"min": 1e-8, "max": 1e12}, "price": {"min": None, "max": None},
                   "cost": {"min": 1e-8, "max": None}, "leverage": {"min": 1.0, "max": 1.0}},
    }
}


def bars(gap=False):
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    rows = []
    for i in range(30):
        o = 100.0 + i
        h, l, c = o + 2, o - 1, o + 0.5
        if gap and i == 15:
            o, h, l, c = 100.0, 108.0, 99.0, 101.0
        rows.append({"date": t0 + pd.Timedelta(hours=i), "open": o, "high": h, "low": l, "close": c, "volume": 1e6})
    return pd.DataFrame(rows)


def config(stoploss):
    return {
        "max_open_trades": 1, "stake_currency": "USDT", "stake_amount": 1000, "dry_run_wallet": 10000,
        "tradable_balance_ratio": 1.0, "fiat_display_currency": "", "timeframe": "1h", "dry_run": True,
        "minimal_roi": {"0": 100.0}, "stoploss": stoploss, "fee": 0.0,
        "entry_pricing": {"price_side": "same", "use_order_book": False, "order_book_top": 1, "price_last_balance": 0.0,
                          "check_depth_of_market": {"enabled": False, "bids_to_ask_delta": 1}},
        "exit_pricing": {"price_side": "same", "use_order_book": False, "order_book_top": 1},
        "exchange": {"name": "binance", "key": "", "secret": "", "enable_ws": False,
                     "pair_whitelist": ["TOK/USDT"], "pair_blacklist": []},
        "pairlists": [{"method": "StaticPairList"}], "datadir": HERE, "user_data_dir": HERE,
        "strategy_path": str(HERE / "strategies"), "strategy": "SmokeStrat", "disableparamexport": True,
        "internals": {}, "export": "none", "runmode": RunMode.BACKTEST, "trading_mode": "spot", "margin_mode": "",
        "candle_type_def": CandleType.SPOT, "original_config": {}, "db_url": "sqlite://", "verbosity": 0,
        "unfilledtimeout": {"entry": 10, "exit": 30}, "order_types": {"entry": "limit", "exit": "limit",
        "stoploss": "limit", "stoploss_on_exchange": False},
    }


def run(name, stoploss, gap):
    LocalTrade.bt_trades_open = []
    LocalTrade.bt_trades = []
    patches = [
        patch(f"{EXMS}.validate_config", MagicMock()), patch(f"{EXMS}.validate_timeframes", MagicMock()),
        patch(f"{EXMS}.check_time_offset", MagicMock()), patch(f"{EXMS}.id", PropertyMock(return_value="binance")),
        patch(f"{EXMS}.name", PropertyMock(return_value="Binance")),
        patch(f"{EXMS}.precisionMode", PropertyMock(return_value=2)),
        patch(f"{EXMS}.precision_mode_price", PropertyMock(return_value=2)),
        patch(f"{EXMS}._load_async_markets", return_value={}),
        patch(f"{EXMS}.markets", PropertyMock(return_value=MARKETS)),
        patch(f"{EXMS}._init_ccxt", MagicMock()), patch(f"{EXMS}.get_fee", return_value=0.0),
        patch(f"{EXMS}.timeframes", PropertyMock(return_value=["1h"])),
        patch(f"{EXMS}.get_min_pair_stake_amount", return_value=1e-8),
        patch(f"{EXMS}.get_max_pair_stake_amount", return_value=float("inf")),
        patch(f"{EXMS}.get_pair_base_currency", lambda _, x: x.split("/")[0]),
        patch("freqtrade.exchange.binance.Binance._supported_trading_mode_margin_pairs",
              PropertyMock(return_value=[(__import__("freqtrade.enums", fromlist=["TradingMode"]).TradingMode.SPOT,
                                          __import__("freqtrade.enums", fromlist=["MarginMode"]).MarginMode.NONE)])),
    ]
    for p in patches:
        p.start()
    try:
        bt = Backtesting(config(stoploss))
        bt._set_strategy(bt.strategylist[0])
        df = bars(gap)
        processed = {"TOK/USDT": df}
        res = bt.backtest(processed=processed, start_date=df.date.min().to_pydatetime(),
                          end_date=df.date.max().to_pydatetime())
        r = res["results"]
        for _, t in r.iterrows():
            oi = int((t.open_date - df.date.min()) / pd.Timedelta(hours=1))
            ci = int((t.close_date - df.date.min()) / pd.Timedelta(hours=1))
            print(f"[{name}] entry bar {oi} rate={t.open_rate} (bar{oi} open={df.open[oi]}) | "
                  f"exit bar {ci} rate={t.close_rate} (bar{ci} open={df.open[ci]} low={df.low[ci]} high={df.high[ci]}) "
                  f"reason={t.exit_reason}")
        if r.empty:
            print(f"[{name}] no trades")
    finally:
        for p in patches:
            p.stop()


print("signals: enter_long on bar 10 close, exit_long on bar 20 close")
run("A next-bar", -0.99, gap=False)
run("B stop gap", -0.05, gap=True)

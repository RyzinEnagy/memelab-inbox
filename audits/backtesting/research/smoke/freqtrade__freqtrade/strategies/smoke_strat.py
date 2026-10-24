# Minimal deterministic strategy for the fill-timing smoke test (no indicators).
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class SmokeStrat(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    use_exit_signal = True
    startup_candle_count = 0
    ENTRY_IDX = 10
    EXIT_IDX = 20

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe.loc[dataframe.index == self.ENTRY_IDX, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe.loc[dataframe.index == self.EXIT_IDX, "exit_long"] = 1
        return dataframe

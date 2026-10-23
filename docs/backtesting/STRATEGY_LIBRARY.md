# Strategy library (Phase 08)

Code: `memelab/backtest/strategies/` (features.py for price features, base.py for the contract, ta.py, labstatus.py, baselines.py, registry.py). The catalyst strategy (CATALYST_VERIFIED) is specified in Phase 09. Every strategy here is long-only research: a signal is a SETUP claim with a mechanical entry, a structural invalidation and exits. The backtest, not the strategy, says what history shows about such setups.

## Rules every strategy follows (enforced in code)

- Input is closed bars only, each with its availability time (bar close plus provider lag). A strategy given a bar that was not yet available at the decision time raises LeakageError, also when it would not have traded (`Strategy._check`).
- The bar series must be one timeframe, ordered, without overlap; otherwise MalformedBars is raised. Missing hours are allowed and never filled.
- A signal's `latest_input_available_at` must be at or before its decision time (`Signal.__post_init__`), and decision time is never before the candidate time.
- Decision time is when the triggering bar becomes available. The engine fills at the open of the first bar that starts at or after decision time plus latency (never the signal bar), and expires the order if no bar opens within the allowed wait.
- Pivots (swing highs and lows) are confirmed only after `right` further bars close; their `known_at` is that later bar's availability, so they never repaint.
- Identity is {chain, mint}. The ticker is never used. `signal_id` hashes strategy, version, chain, mint, decision time and parameters.
- Unknown parameters are refused; every parameter set has a stable hash recorded with each signal.
- Price features (features.py) are separate from signal logic (ta.py) and from execution (execution.py, engine.py), so tuning cannot hide inside an indicator.
- The pool basis (which pool's bars a token is tested on) is chosen point in time by `gecko.pool_basis_at`: the valid pool with the most volume in bars available within the prior day. The bars used are recorded in `based_on`.

## Lab logic reused and not reused

LAB_STATUS reuses the lab's own final decision (status, score, fatal flags) from each thesis as known at its creation time. The lab's internal technical modules are not reused for historical decisions because Phase 00 found defects that would leak or mislabel (C2: m13 reads the unfinished candle; m24 breakout label set; m14/m22 window-key mismatch; GAPS.md). The equivalent features are recomputed here on closed bars.

## Strategies

| Id | Version | Kind | Warm-up bars | Parameters |
|---|---|---|---|---|
| BREAKOUT_CLOSE | 1 | TA | 25 | `{"buffer": 0.0, "lookback": 24, "max_hold_bars": 48, "max_staleness_bars": 1, "stop_buffer": 0.03, "tp_r": 2.0, "vol_mult": 1.5}` |
| BREAKOUT_RETEST | 1 | TA | 27 | `{"lookback": 24, "max_hold_bars": 48, "stop_buffer": 0.04, "tol": 0.02, "tp_r": 2.0, "vol_mult": 1.5, "within_bars": 12}` |
| RECLAIM | 1 | TA | 27 | `{"lookback": 24, "max_hold_bars": 48, "tp_r": 2.0, "within_bars": 12}` |
| TREND_HHHL | 1 | TA | 24 | `{"ema_n": 20, "left": 3, "max_ext_atr": 4.0, "max_hold_bars": 72, "right": 3, "tp_r": 2.0}` |
| ABSORPTION_BREAK | 1 | TA | 13 | `{"k": 12, "max_hold_bars": 48, "range_pct": 0.12, "tp_r": 2.0}` |
| MOMENTUM | 1 | TA | 30 | `{"blowoff_atr": 3.0, "fast": 8, "max_ext_atr": 5.0, "max_hold_bars": 48, "min_bar_volume_usd": 2000.0, "min_roc": 0.1, "roc_bars": 6, "slow": 24, "stop_bars": 6, "tp_r": 2.0, "vol_long": 24, "vol_regime": 1.2, "vol_short": 6}` |
| LAB_STATUS | 1 | LAB | 0 | `{"max_hold_bars": 48, "min_score": 55, "statuses": ["NEAR ENTRY", "ENTRY CONDITIONS MET", "SETUP DEVELOPING"], "stop_frac": 0.2, "tp_r": 2.0}` |
| NO_TRADE | 1 | BASELINE | 0 | `{}` |
| ENTER_AT_DISCOVERY | 1 | BASELINE | 0 | `{"hold_bars": 24, "stop_frac": 0.9}` |
| RANDOM_ENTRY | 1 | BASELINE | 0 | `{"max_hold_bars": 48, "p": 0.05, "seed": 7, "stop_frac": 0.15, "tp_r": 2.0}` |
| MA_CROSS | 1 | BASELINE | 26 | `{"fast": 8, "max_hold_bars": 48, "slow": 24, "stop_frac": 0.15, "tp_r": 2.0}` |

## Exact specifications (from each strategy's docstring, which is the source of truth)

### BREAKOUT_CLOSE

BREAKOUT_CLOSE: the last closed bar closes above the highest high of the previous `lookback` closed bars by at least `buffer`, with volume >= `vol_mult` x the median volume of those bars. A wick above the level that closes back below is NOT a breakout. Entry: next bar open after the bar is available (engine). Invalidation: a close back below the breakout level minus `stop_buffer` (stop placed there; gaps fill at the open). Exits: stop, take profit at `tp_r` R, or `max_hold_bars`. Abstains: fewer than lookback+1 closed bars (INSUFFICIENT_HISTORY), stale last bar.

### BREAKOUT_RETEST

BREAKOUT_RETEST: a BREAKOUT_CLOSE happened within the last `within_bars` closed bars at level L; since then a closed bar's low came within `tol` of L (low <= L*(1+tol)) without closing below L*(1-tol); the last closed bar closes above L and above its own open (hold confirmed). A retest that closes below L*(1-tol) is a FAILED retest and cancels the setup. Entry next open. Stop below L*(1-stop_buffer).

### RECLAIM

RECLAIM: a breakout above L (close > L) within `within_bars`, then a close below L (failed breakout), then the last closed bar closes back above L. Entry next open. Stop below the lowest low since the failure.

### TREND_HHHL

TREND_HHHL: the last two confirmed swing highs and lows are rising (HH and HL; pivots confirmed `right` bars later, never repainted) and the last closed bar closes above the last confirmed swing high. Not entered when price is more than `max_ext_atr` ATRs above the EMA(`ema_n`) (exhaustion filter). Stop below the last confirmed HL.

### ABSORPTION_BREAK

ABSORPTION_BREAK: over the last `k` closed bars the lows stay within `range_pct` of each other (price holds), down-bar volume has a negative slope (OBSERVED: selling volume shrinking), and the last closed bar closes above the range high. Calling this absorption is an INTERPRETATION recorded in the features; it is not proof of a future rise. Stop below the range low.

### MOMENTUM

MOMENTUM: trend-following entry with an exhaustion guard and a liquidity filter, all on closed bars. Enter when: close > EMA(`fast`) > EMA(`slow`); the `roc_bars`-bar rate of change of the close is >= `min_roc`; volume regime is rising (median volume of the last `vol_short` bars >= `vol_regime` x the median of the `vol_long` bars before them). Abstain EXHAUSTION when the last bar's range is more than `blowoff_atr` ATRs and it closes in the lower half of that range, or when the close is more than `max_ext_atr` ATRs above EMA(`slow`). Abstain ILLIQUID when the median bar volume (USD) of the last `vol_short` bars is below `min_bar_volume_usd`. Stop: the lowest low of the last `stop_bars` closed bars. Exits: stop, `tp_r` R, `max_hold_bars`.

### LAB_STATUS

LAB_STATUS: when the lab records a thesis (decision time = the thesis created_at, which is when the lab's own analysis existed) with status in `statuses`, score >= `min_score` and NO fatal flag, enter at the next bar open. Stop: the thesis snapshot's nearest support when it is below the price, else `stop_frac` below the last close. Exits: stop, `tp_r` R, or `max_hold_bars`. This tests the lab's own ranking as a signal; it never overrides a fatal flag (fatal-flag rows can only be negative controls).

### NO_TRADE

NO_TRADE: never enters. Its result is zero P&L and zero exposure; any strategy must beat it net of costs.

### ENTER_AT_DISCOVERY

ENTER_AT_DISCOVERY (buy and hold from discovery): enters at the first decision opportunity for each eligible token (the next open after the lab first observed it) and holds for `hold_bars` with a wide `stop_frac` stop. Shows what the discovery universe itself did.

### RANDOM_ENTRY

RANDOM_ENTRY: at each decision point enters with probability `p` decided by a seeded hash of (seed, mint, decision_time): deterministic, independent of prices. Same exits as the strategy it is compared with.

### MA_CROSS

MA_CROSS: transparent indicator baseline. Fast EMA crosses above slow EMA on the last closed bar. Stop at `stop_frac` below the close.

## Abstain reasons

INSUFFICIENT_HISTORY (fewer closed bars than warm-up), STALE_DATA (last bar too old for the decision), OVEREXTENDED and EXHAUSTION (price too far above its average in ATR units, or a blow-off bar), ILLIQUID (median bar volume below the floor), RISK_FATAL_FLAW (lab fatal flag visible), UNVERIFIED_CATALYST and the other catalyst reasons (Phase 09). A strategy that simply sees no setup returns nothing.

## Liquidity-aware entry

Two layers: MOMENTUM refuses thin tapes (median bar volume floor); for every strategy the engine refuses entries whose modeled entry impact exceeds the cap, refuses fills on stale liquidity observations, and sizes against exit capacity (Phase 07 execution, Phase 10 engine).

## Chronological case proofs on real bars

`python audits/backtesting/strategies/p08_cases.py 3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump Ce2gx9KGXJ6C9Mp5b5x1sn9Mg87JwEbrQby4Zqo3pump` (output `audits/backtesting/strategies/p08_cases.json`). Each strategy is evaluated at every hour, seeing only bars available then; decisions land at hh:05 (close plus the modeled 300 s provider lag).

- The collapsed token (38 bars, 99.99% fall in three days): no strategy signaled; every evaluation abstained for INSUFFICIENT_HISTORY (and one ILLIQUID) because the token died before 25 bars of history existed. That is the intended behavior for fresh launches.
- Ce2gx9KG (999 hourly bars on its PumpSwap pool): BREAKOUT_CLOSE 32 signals, BREAKOUT_RETEST 39, RECLAIM 14, TREND_HHHL 12, ABSORPTION_BREAK 28, MOMENTUM 47 (10 ILLIQUID and 1 EXHAUSTION abstains). First BREAKOUT_CLOSE: decision 2026-09-16 16:05Z, close 0.024671, stop 0.023744 (3% under the 0.024478 level). These counts say nothing about profit; Phase 11 tests that.

## Baselines

NO_TRADE (zero exposure), ENTER_AT_DISCOVERY (buy when the lab first knew the token, fixed hold), RANDOM_ENTRY (seeded, price-blind entry with the same exits), MA_CROSS (simple trend baseline). Every validation compares a strategy with all four.

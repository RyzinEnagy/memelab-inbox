# PHASE 08: point-in-time technical-analysis strategy library

State: PASS. Date 2026-10-23. Entry gate: Phase 07 PASS at e18c12f (execution tests 15 passed, 14/14 mutations, release audit clean).

## Changed files

- New: `memelab/backtest/strategies/__init__.py`, `features.py` (closed-bar features: prior high/low excluding the tested bar, ATR, median volume, EMA, confirmed pivots with known_at, trend state, down-bar volume slope), `base.py` (Signal/Abstain/Exits contract, leakage and malformed-series guards, parameter validation and hashing), `ta.py` (BREAKOUT_CLOSE, BREAKOUT_RETEST, RECLAIM, TREND_HHHL, ABSORPTION_BREAK, MOMENTUM), `labstatus.py` (LAB_STATUS), `baselines.py` (NO_TRADE, ENTER_AT_DISCOVERY, RANDOM_ENTRY, MA_CROSS), `registry.py`.
- New tests: `tests/test_backtest_strategies.py` (16).
- Docs and evidence: `docs/backtesting/STRATEGY_LIBRARY.md`; `audits/backtesting/strategies/p08_cases.py`, `p08_cases.json` (chronological case proofs on real bars); `testing/p08_mutations.json`, `testing/logs/p08_mutations.log`.
- The registry in this commit does not list CATALYST_VERIFIED; Phase 09 adds it.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_strategies.py -q` | 0 | 16 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p08_mutations.json` | 0 | 11 of 11 caught |
| `python audits/backtesting/strategies/p08_cases.py 3GVSN8... Ce2gx9KG...` | 0 | collapsed token: no signal, all INSUFFICIENT_HISTORY; Ce2gx9KG: 12 to 47 signals per strategy |

## Gate

G05 (signal at bar availability, earliest execution after it, a leak refused), G18 (wick vs close vs failed retest; pivots invariant to truncation: no repaint), G19 (absorption: observed vs interpreted fields), G31 (new token: INSUFFICIENT_HISTORY). Signal timestamp invariant enforced in code twice: `Strategy._check` (also for no-trade outcomes) and `Signal.__post_init__`.

## Bounded loop

Pass 1: the momentum test on a smooth 2% per bar ramp abstained EXHAUSTION (7.2 ATR above EMA): correct behavior, so the test now checks both cases (wide-range climb signals; smooth climb abstains).
Pass 2: mutation M08-3 (strategy accepts a future bar) survived because the Signal's own check still caught leaks on signaling paths. A leak that only changes a no-trade decision is still lookahead; a test now requires LeakageError when no signal would result. Caught.
Negative control on falsely historic data: the strategies never read catalysts or pages (Phase 09 covers catalyst timing; G36 in Phase 06A).

## Independent negative review

Wrong-but-plausible outputs and the test that catches each: breakout level including the tested bar (M08-1), repainting pivots (M08-2), future bar accepted (M08-3), mixed timeframes (M08-4), no exhaustion guard (M08-5), no liquidity floor (M08-6), signal identity without the mint (M08-7), lab fatal flag ignored (M08-8), random baseline peeking at price (M08-9), stale bar traded (M08-10), wick counted as breakout (M08-11).

## Limitations

Strategies are hourly-bar only (the corpus is hourly). Parameters are defaults, not tuned; tuning happens only inside Phase 11's train window with trial counting. Discretionary lines are not supported by design.

NEXT ELIGIBLE PHASE: 09.

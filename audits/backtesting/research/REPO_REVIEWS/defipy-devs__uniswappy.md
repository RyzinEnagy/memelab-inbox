# defipy-devs/uniswappy

- URL: https://github.com/defipy-devs/uniswappy
- Pinned commit: 8c729b5423bad37b3a95eca4ca68ab8fa998ad73 (2026-05-14T21:18:33-07:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: AMM math
- Discovery channel: Firecrawl developer search `uniswap v3 concentrated liquidity backtesting simulator tick math python library` (SEARCH_LOG.md:45)
- Stars/forks (low weight, from search time): not recorded at search time / not recorded (GitHub API not reachable from this session)
- License (from LICENSE file text, not badge): Apache-2.0 (LICENSE line 1 adds "Copyright 2023–2025 DeFiPy contributors"; NOTICE asks for attribution) ; transitive notes: V3 math files carry an MIT attribution header for code adapted from chainflip-io/chainflip-uniswapV3-python (python/prod/utils/tools/v3/SwapMath.py header, same in FullMath.py, LiquidityMath.py); runtime deps numpy, scipy, pandas, requests, termcolor (all permissive).
- Package: PyPI `uniswappy` 1.7.9 (wheel uploaded 2026-04-23; setup.py version 1.7.9) ; Python/OS: pure Python, no `python_requires`; installed and ran on CPython 3.13.17 Linux; Windows not tested ; native deps: none (scipy/numpy wheels only).
- Maintenance: last commit 2026-05-14 ("update readme"); CI files: none (no .github); tests: 16 test files, 88 `def test` functions under python/test (unittest/pytest style), not run here.
- Security surface: no install scripts beyond a plain setuptools setup.py (not executed; wheel used); one network client `python/prod/utils/client/API0x.py:65-72` (0x EVM quote API, needs a key, not called on import); simulated "wallets" only (python/prod/cpt/wallet/Wallets.py:19-60), no key or signing code; `python/prod/__init__.py:1-2` contains an authorship "watermark for LLMs" comment (treated as data, no instruction content); `.DS_Store` and `tea.yaml` (crypto addresses for tea.xyz) committed.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | no bar/candle data model anywhere in python/prod |
| tick/trade replay | NOT_SUPPORTED | state is mutated by explicit calls (Swap().apply, python/prod/process/swap/Swap.py:41-82); no trade-log replay |
| CPMM math | SOURCE_CODE_VERIFIED | python/prod/cpt/exchg/UniswapExchange.py:530-582 (getAmountOut with 997/1000), 432-476 (swap); smoke test matches hand x*y=k |
| CLMM/DLMM math | SOURCE_CODE_VERIFIED (CLMM, EVM Uniswap V3) / NOT_SUPPORTED (DLMM) | python/prod/cpt/exchg/UniswapV3Exchange.py:547-767 (swap loop), 651-657 (SwapMath.computeSwapStep), 689 (Tick.cross), 814-865 (nextTick) |
| routes | NOT_SUPPORTED | single-pool only; python/prod/process/join, cpt/index are LP/index-token helpers, not routing |
| fees/taxes | SOURCE_CODE_VERIFIED (partial) | V2 fee hardcoded 0.3%: UniswapExchange.py:552-553, 579-580; `UniswapExchangeData.fee` (python/prod/utils/data/UniswapExchangeData.py:40) is ignored by V2 (smoke case 4); V3 uses `self.fee` (UniswapV3Exchange.py:138, 656); no transfer-fee/Token-2022 concept |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED | impact follows from x*y=k; smoke case 3 (sell 50% of reserve) reproduces 33.47% impact exactly |
| fill timing (next bar, latency) | NOT_SUPPORTED | no time or bar concept; swaps execute immediately on the in-memory state |
| point-in-time guard / no lookahead | NOT_SUPPORTED | no timestamps on state; nothing prevents or causes lookahead |
| async event/catalyst injection | NOT_SUPPORTED | only random synthetic event pickers: python/prod/math/model/EventSelectionModel.py:20-40 |
| wallets/on-chain | NOT_SUPPORTED (simulated balances only) | python/prod/cpt/wallet/Wallets.py:19-60; no RPC, no Solana |
| cross-token cohorts / portfolio | NOT_SUPPORTED | |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | |
| metrics/report | DOCS_ONLY / DEMO_ONLY | impermanent-loss and LP analytics in python/prod/analytics/risk/UniswapImpLoss.py; notebooks/ demos |
| live trading code present (must be avoidable) | NOT_SUPPORTED (none) | only the optional 0x quote client (API0x.py), no order or tx submission |

## Fill and chronology assumptions (read the code)

uniswappy is an in-memory AMM state simulator, not a backtester: there is no bar, timestamp or signal layer, so "which bar fills" does not apply. A swap is priced against the pool's current reserves at call time and mutates them immediately (Swap.py:70-72 calls `get_amount_out` then `swap_exact_tokens_for_tokens`, UniswapExchange.py:243-281). V2 output is `ceil(amount_in*997*reserve_out / (reserve_in*1000 + amount_in*997))` (UniswapExchange.py:552-553 with SaferMath.div_round, python/prod/utils/tools/SaferMath.py:63-73), i.e. it rounds UP where Uniswap V2 floors; in the default "DEC" precision mode amounts are scaled by 1e18 and returned as Python floats (python/prod/utils/tools/v3/UniV3Helper.py:89-95, GWEI_PRECISION = 18 at line 21). The V2 constant-product K check is commented out (UniswapExchange.py:472-473, "# ******** FIX ********"), and the repo's own test notes it (python/test/v2/process/swap/test_swap.py:26-27). V3 follows the Uniswap V3 swap loop with tick crossing and fee growth; `nextTick` re-sorts all tick keys every step (UniswapV3Exchange.py:839-845), which is O(n log n) per step but correct. No slippage model beyond the curve, no latency, no MEV, no failed-route modelling.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/defipy-devs__uniswappy
/home/claude/ext/venvs/defipy-devs__uniswappy/bin/pip install --only-binary=:all: uniswappy   # exit 0, uniswappy 1.7.9, numpy 2.5.4, pandas 3.1.0, scipy 1.18.1
cd audits/backtesting/research/smoke/defipy-devs__uniswappy
/home/claude/ext/venvs/defipy-devs__uniswappy/bin/python -I script.py > output.txt   # exit_code=0
```
Outcome (output.txt): (1) DEC mode, reserves 1000/100000, sell 10: uniswappy 987.1580343970613 = hand rational 99700000/100997 to float precision; reserves after 1010 / 99012.84196560294 match the repo's own test. (2) Raw-integer GWEI mode, same numbers: uniswappy returns 988 while on-chain Uniswap V2 floor is 987 (rounds up, over-states output by one unit; material only at small raw amounts). (3) Thin exit (sell 50% of token reserve): output and 33.47% impact match hand calc. (4) `UniswapExchangeData(fee=2500)` gives the same V2 quote as the default (fee field ignored; a 0.25% hand calc gives 987.648 vs 987.158). Wall time under 1 minute.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.0 | 6.00 | EVM Uniswap V2/V3 math in Python; 18-decimal default, V2 fee fixed at 0.3% (Raydium AMM v4 is 0.25%, CPMM/PumpSwap tiers vary); reusable CPMM/CLMM abstractions only after adaptation |
| B microstructure | 17 | 2.5 | 8.50 | size-dependent impact verified by smoke test; V3 tick crossing in code; but V2 fee not configurable, rounding up, K check disabled, no transfer fees or failed routes |
| C point-in-time | 15 | 1.0 | 3.00 | no time model at all; chronology entirely the caller's job |
| D catalyst/on-chain events | 11 | 0.5 | 1.10 | only random synthetic event selection (EventSelectionModel.py) |
| E TA/strategy flexibility | 9 | 0.5 | 0.90 | arbitrage/LP simulation helpers (analytics/simulate), no strategy layer |
| F statistical validation | 11 | 0.0 | 0.00 | none |
| G integration fit | 9 | 3.5 | 6.30 | pure-Python wheel installs on 3.13 with numpy/pandas/scipy; modular classes; no wallets; object model (factory, ERC20, user names) adds ceremony; Windows untested |
| H maintenance/tests | 6 | 2.5 | 3.00 | 88 test functions but no CI; last commit 2026-05; known disabled K check |
| I license/supply chain | 5 | 4.0 | 4.00 | Apache-2.0 file text, MIT attribution for V3 port, PyPI wheel; deps are lower-bound only (unpinned) |
| J operational footprint | 2 | 4.0 | 1.60 | wheel install in seconds, small, no services |
| Total | 100 | | 34.40 | |

Hard gates: none. Most important limitation for memecoins: it models EVM pools with a hardcoded 0.3% V2 fee and 18-decimal scaling, has no Solana pool types (no PumpSwap/Raydium CPMM fee tiers, no DLMM bins, no Token-2022 transfer fees) and no time or historical-state replay, so every memecoin fill would need a custom fee/decimals layer on top. One credible negative finding: the V2 swap path silently ignores the configured fee (`UniswapExchangeData.fee`, smoke case 4) and the constant-product invariant check is disabled (UniswapExchange.py:472-473), so a wrong fee or reserve mutation would not raise.
Disposition: REFERENCE (independent cross-check oracle for CLMM tick math in tests; do not use as the execution engine). Suggested use: REFERENCE.

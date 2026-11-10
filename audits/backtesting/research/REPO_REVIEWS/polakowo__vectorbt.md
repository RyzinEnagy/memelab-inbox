# polakowo/vectorbt

- URL: https://github.com/polakowo/vectorbt
- Pinned commit: 8e30b8ce102f302bec0c0226e05b59714453bebd (2026-10-23T14:07:32+02:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: vectorized
- Discovery channel: seed; curated awesome-quant (LONGLIST)
- Stars/forks (low weight, from search time): not recorded in LONGLIST / not recorded
- License (from LICENSE file text, not badge): Apache-2.0 with "Commons Clause" License Condition v1.0 (LICENSE.md:1-13; not OSI open source; bars "Sell", i.e. offering a product or service whose value derives substantially from vectorbt, including paid hosting/consulting). License history read from a blobless clone of the full history: GPL-3.0 (2017-11-16 `2aceef2`, again 2020-02-18 `4646dc7`), Apache-2.0 (2020-12-22 `8c4c0cf`), Apache-2.0 + Commons Clause since 2021-08-21 (`71402ac`, moved to LICENSE.md in `83cacaa`); only year bumps since. Every source file carries "licensed under Apache 2.0 with Commons Clause" (e.g. vectorbt/_version.py:1-2). README.md:382 adds "Installing optional dependencies may be subject to a more restrictive license." ; transitive notes: optional `full` extra pulls TA-Lib, python-binance, ccxt, alpaca-py, python-telegram-bot, ray (pyproject.toml); base install is 70 packages incl. numba/llvmlite, plotly, scikit-learn, requests, dill.
- Package: PyPI `vectorbt` 1.2.0 (py3-none-any wheel; installed tree byte-identical to the pinned source) ; Python/OS: requires-python >=3.11,<3.15, CI matrix ubuntu/windows/macos x 3.11-3.14 ; native deps: numba + llvmlite wheels; optional Rust engine `vectorbt-rust==1.2.0` (rust/ crate, not installed here)
- Maintenance: last commit 2026-10-23; CI files .github/workflows/tests.yml (pull_request + workflow_dispatch only, plus a Rust-engine parity job), docs.yml, pypi.yml, docker.yml; tests: 15 test files, 893 `def test_` (pytest), tests/test_portfolio.py alone 11,018 lines
- Security surface: no install scripts executed (wheel); no order placement code anywhere (grep for create_order/submit_order/place_order: none); data downloaders that do network I/O when called (vectorbt/data/custom.py:192 YFData, :310 BinanceData, :565 CCXTData, :768 AlpacaData; Binance api_key/api_secret config slots at vectorbt/_settings.py:150), DataUpdater scheduler (vectorbt/data/updater.py:24), Telegram bot (vectorbt/messaging/telegram.py); `exec()` of internally generated class code in indicators/factory.py:2986, :3300 and signals/factory.py:596, :637, :695 (templates, not user input). No wallet/key code.

## OSS vs PRO split (checked in code, not README)

The OSS edition is a complete bar-level simulator. PRO-only per in-code tips: limit orders, leverage, contract multipliers (README.md:211-215, portfolio/base.py:66-69), purging and embargo in CV, split decorator, time-anchored splits (generic/splitters.py:8-12), "safe resampling" that aligns bars by when information becomes available (generic/accessors.py:653-655), event projections and pattern ranges (generic/ranges.py:48-49), MAE/MFE expanding trade metrics and edge ratio (portfolio/trades.py:22-24), portfolio from fills and portfolio continuation (portfolio/base.py:66-68), streaming indicators (indicators/basic.py:12). None of these are present in OSS source; this review scores OSS only.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | arrays per column; open/high/low/close inputs to from_signals (portfolio/nb.py:2086-2089); ohlcv_accessors.py |
| tick/trade replay | NOT_SUPPORTED | row = bar; no tick/trade event type |
| CPMM math | NOT_SUPPORTED | no reserves anywhere; only adaptable by writing a numba order_func (portfolio/base.py:3308 from_order_func) that computes price from user arrays |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none; `reject_prob` random rejection is the only failure model (portfolio/nb.py:501-502) |
| fees/taxes | SOURCE_CODE_VERIFIED | proportional `fees` + `fixed_fees` per order (portfolio/nb.py:148-149); no transfer-tax or per-token fee concept |
| thin exits / size-dependent impact | NOT_SUPPORTED | slippage is a flat fraction `adj_price = price * (1 + slippage)` (portfolio/nb.py:90; sell side :233); `max_size` cap + `allow_partial` (nb.py:137-141) is a size cap, not liquidity; smoke [3] same fill for 1e3 and 1e12 cash |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | default `price=None -> np.inf -> close of the same bar` (portfolio/base.py:2755-2756, nb.py:2050-2052): same-bar close fill; next-bar open only if caller shifts signals and passes price=open (smoke [2]); no latency parameter |
| point-in-time guard / no lookahead | NOT_SUPPORTED | no guard; signals are user arrays; `labels` module is explicitly look-ahead (labels/__init__.py:4, labels/dispatch.py:21 future_mean_apply); OSS resample_apply labels bins by left edge (generic/accessors.py:637-690) and safe resampling is PRO-only |
| async event/catalyst injection | NOT_SUPPORTED | only bar-aligned boolean/size arrays or numba callbacks |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | column groups with `cash_sharing`, auto call sequence sorting sells first (portfolio/nb.py:2266-2269); cash/debt/free_cash accounting in buy_nb/sell_nb (nb.py:72-342) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (partial) | RollingSplitter / ExpandingSplitter (generic/splitters.py:193, :242), accessors range_split/rolling_split/expanding_split (generic/accessors.py:1776, :1860, :1888); Deflated Sharpe Ratio (returns/metrics.py:19-37, accessor returns/accessors.py:665); random-signal baseline Portfolio.from_random_signals (portfolio/base.py:3198); no purge/embargo (PRO), no sealed-holdout tooling |
| metrics/report | SOURCE_CODE_VERIFIED | stats/trades/drawdowns records, plotly plots (portfolio/base.py, portfolio/trades.py) |
| live trading code present (must be avoidable) | NOT_SUPPORTED (no order routing) | only data downloaders and Telegram notifications, all opt-in |

## Fill and chronology assumptions (read the code)

`Portfolio.from_signals` reads the entry/exit arrays at row i and executes in the same row at `price[i]`, which defaults to `close[i]` (portfolio/base.py:2755-2756 sets `price=np.inf`; nb.py:2050-2052 maps +inf to close). A signal computed from bar i's close is therefore filled at that same close with zero latency. Next-bar execution is possible only by shifting the signal arrays one row and passing `price=open` (verified, smoke [2]). Slippage is a constant fraction of price (nb.py:90, :233); fees are proportional plus fixed (nb.py:148-149). Order size never moves price. Stops: SL is evaluated before TP on each bar (nb.py:2098 then :2108), so a bar that touches both resolves to SL (pessimistic). `get_stop_price_nb` fills at the open when the bar gaps through the stop, otherwise at the stop level if low<=stop<=high (nb.py:1861-1889). The default `stop_exit_price="stoplimit"` (\_settings.py:404) returns the stop price with slippage forced to 0.0 (nb.py:1626-1627), so stop exits get no slippage even when `slippage` is set; the stop level is computed from `stop_entry_price="close"` (\_settings.py:403), not from the slipped fill. Indicators are vectorized over complete arrays, so whether they can see the current bar is entirely the caller's design; there is no unfinished-bar concept.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/polakowo__vectorbt
/home/claude/ext/venvs/polakowo__vectorbt/bin/pip install -q --prefer-binary vectorbt   # exit 0, vectorbt 1.2.0, numpy 2.5.4, pandas 3.1.0, numba 0.68.0
cd audits/backtesting/research/smoke/polakowo__vectorbt
/home/claude/ext/venvs/polakowo__vectorbt/bin/python -I script.py > output.txt   # EXIT_CODE=0
```
Outcome: exit 0. [1] defaults: signal on bar 10, entry at 2026-01-01 10:00 price 110.5 = bar 10 close (SAME_BAR_CLOSE_FILL=True). [2] shifted signal + price=open: entry 11:00 at 111.0 (NEXT_BAR_OPEN=True). [3] 1% slippage gives 111.605 for both 1e3 and 1e12 cash (no size dependence). [4] 5% SL with slippage=1%: exit at exactly 104.975 on a bar that traded down to 90 and closed at 95 (zero slippage on stops by default).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2.0 | 6.00 | any-frequency arrays, fractional sizes (min_size 1e-8), multi-asset columns; CEX downloaders only; no DEX/Solana semantics |
| B microstructure | 17 | 1.5 | 5.10 | flat % slippage nb.py:90; prop+fixed fees; reject_prob and max_size are the only adverse conditions; no reserves/depth |
| C point-in-time | 15 | 2.0 | 6.00 | same-bar close default (base.py:2755, nb.py:2052); next-bar possible by manual shift; no guards or lookahead tests; look-ahead labels module; safe resampling PRO-only |
| D catalyst/on-chain events | 11 | 1.0 | 2.20 | bar-aligned arrays only; no known-at timestamps or async ingestion |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | IndicatorFactory, signal generators, SL/TSL/TP, from_order_func numba callbacks, parameter grids |
| F statistical validation | 11 | 3.0 | 6.60 | rolling/expanding splitters, DSR (returns/metrics.py:19), random-signal baselines; no purge/embargo or sealed holdout in OSS |
| G integration fit | 9 | 3.5 | 6.30 | Py3.13 wheel installed, CI on Windows/Linux; pandas/numpy in, records out; heavy dependency tree |
| H maintenance/tests | 6 | 4.0 | 4.80 | commit same day as review; 893 tests, 3-OS x 4-Python CI (PR-triggered); suite not run here |
| I license/supply chain | 5 | 2.5 | 2.50 | Apache-2.0 + Commons Clause (non-OSI, sale restriction, notice must carry the clause); license changed twice; 70-package install |
| J operational footprint | 2 | 3.0 | 1.20 | 835 MB venv, numba JIT compile on first call; no services |
| Total | 100 | | 47.90 | |

Hard gates: none for internal, non-commercial research use (Commons Clause only bars selling a product/service that derives substantially from vectorbt; vendored excerpts must carry the clause). Most important limitation for memecoins: execution price is the bar price times a constant (nb.py:90), so a 50 USD and a 50,000 USD buy into a 20k-liquidity pool fill at the same price; no reserves, no thin-exit, no route failure beyond a random reject probability. One credible negative finding: default stop exits (`stop_exit_price="stoplimit"`) fill exactly at the stop with slippage zeroed (nb.py:1626-1627); smoke [4] sold at 104.975 on a bar whose low was 90, which overstates every stop-loss in a crash-prone market.
Disposition: REIMPLEMENT_IDEA (numba order-record and cash/debt accounting layout, DSR formula, rolling/expanding splitters, gap-aware stop pricing). Suggested use: REFERENCE.

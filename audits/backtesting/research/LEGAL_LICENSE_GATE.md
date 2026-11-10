# Legal and license gate (Phase 03)

License read from the LICENSE file at the pinned commit (not the badge). The lab repository itself has no LICENSE file, so it is "all rights reserved" and public; any dependency that is redistributed with it, or code copied into it, must allow that.

| Repo | License (file) | Import as dependency | Copy code | Read for ideas / reimplement | Notes |
|---|---|---|---|---|---|
| lblommesteyn/slotfish | MIT | n/a (Rust) | allowed with notice; not planned | yes | ideas only |
| nautechsystems/nautilus_trader | LGPL-3.0-only | NEEDS_REVIEW | no | yes | 110-180 MB wheel |
| etcherfx/sol-trade | GPL-3.0 | NO | NO | yes (ideas, no text) | backtest path loads private key: never import |
| gbeced/basana | Apache-2.0 (short notice) | allowed | allowed with notice; not planned | yes | |
| QuantConnect/Lean | Apache-2.0 | n/a (C#) | not planned | yes | |
| nikkisora/PolarBT | MIT | allowed | not planned | yes | buggy AMM formula: do not reuse |
| polakowo/vectorbt | Apache-2.0 + Commons Clause | internal use only (no selling) | NO | yes | |
| nkaz001/hftbacktest | MIT | allowed | not planned | yes | |
| eslazarev/purged-cross-validation | MIT | allowed (test-only cross-check) | not planned | yes | below 70: not a runtime dependency |
| kernc/backtesting.py | AGPL-3.0 | test-only, isolated venv, unmodified, not shipped | NO | yes | plot() embeds a tracking iframe: never call plot() |
| pmorissette/bt | MIT | allowed | not planned | yes | |
| sohan-shingade/flint | MIT | not useful | no | yes | depends on LGPL nautilus |
| cudam321/signal-backtest-harness | MIT | not useful | no | yes | |
| freqtrade/freqtrade | GPL-3.0 | NO | NO | yes | |
| jesse-ai/jesse | MIT (closed live plugin separate) | not useful | no | yes | |
| MeteoraAg/dlmm-sdk | NONE (package.json says ISC) | NO | NO | formulas from public docs only | repo commits localnet keypairs and .so binaries |
| orca-so/whirlpools | Orca License (proprietary, non-commercial, competitor clause) | NO | NO | NEEDS_REVIEW: the license defines even reading as use; we rely on public CLMM math (Uniswap v3 whitepaper) instead | reviewer read code before this was known; no text copied |
| tradingstrategy-ai/trade-executor | AGPL-3.0-or-later | NO | NO | yes | |
| stefan-jansen/alphalens-reloaded | Apache-2.0 | allowed | not planned | yes | |
| raydium-io/raydium-sdk-V2 | GPL-3.0 | NO | NO | formulas re-derived from constant-product math | |
| defipy-devs/uniswappy | Apache-2.0 (+MIT V3 notice) | allowed | not planned | yes | EVM-only |
| ranaroussi/quantstats | Apache-2.0 | allowed | not planned | yes | imports yfinance at import time |
| esvhd/pypbo | AGPL-3.0 | NO | NO | yes | not packaged |
| charllysb/pumpfun-momentum-bot | MIT | NO (security) | NO | no | wallet signing code |
| prisyy/pumpsim-api | MIT (no code) | n/a | n/a | n/a | |

Gate result: no copyleft or unlicensed code is copied into the lab. Planned runtime dependencies: none beyond what the lab already uses (numpy, pandas available). Test-only, isolated, not shipped: backtesting.py (AGPL, unmodified) as an OHLC chronology oracle if Phase 04 confirms value. Orca's license is flagged NEEDS_REVIEW for Elving's awareness; the project does not depend on it.

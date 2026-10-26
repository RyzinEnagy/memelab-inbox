# Shortlist for source-code due diligence (Phase 02 -> 03)

25 repositories (>= 20 required). Selection rule, fixed before review: cover all six families; include every seed that resolves and is a backtester or AMM math source; add niche Solana/pump.fun engines with source code and a license or clear README; add maintained validation libraries; exclude live-only bots, coursework without code, archived predecessors with maintained successors, and spam.

| # | Repo | Family | HEAD at 2026-10-23 | Why it is in |
|---|---|---|---|---|
| 1 | polakowo/vectorbt | VEC | `8e30b8ce102f` | fast signal/parameter studies; check OSS vs PRO split |
| 2 | kernc/backtesting.py | VEC | `ca2e2611621e` | canonical prototype engine with tests |
| 3 | nikkisora/PolarBT | VEC | `18f9363a0d13` | niche: polars engine with pump.fun trade data and AMM-aware slippage |
| 4 | pmorissette/bt | VEC | `3adebef0316c` | portfolio composition |
| 5 | nautechsystems/nautilus_trader | EVT | `7b3ed05d980a` | high-fidelity event-driven engine |
| 6 | QuantConnect/Lean | EVT | `f3d841e60dfd` | event-driven accounting reference; C# platform |
| 7 | freqtrade/freqtrade | EVT | `c051e9065c5b` | crypto strategy research; CEX candles |
| 8 | jesse-ai/jesse | EVT | `9a3ebe075d9d` | crypto engine; license check |
| 9 | nkaz001/hftbacktest | EVT | `5f3ec40b2afb` | latency and queue-aware replay |
| 10 | gbeced/basana | EVT | `0c65f58ba856` | async event-driven framework (Python) |
| 11 | lblommesteyn/slotfish | CRY | `4f760c8076bb` | niche: deterministic event-driven engine for pump.fun microstructure |
| 12 | etcherfx/sol-trade | CRY | `c8f37ad221b4` | Solana/Jupiter bot with backtest; GPL; live trading must stay off |
| 13 | sohan-shingade/flint | CRY | `5ce552c88109` | Solana research claims to verify |
| 14 | prisyy/pumpsim-api | CRY | `fd92630fec3e` | niche: off-chain pump.fun curve and PumpSwap simulation |
| 15 | tradingstrategy-ai/trade-executor | CRY | `34fc7eb0b659` | DEX-native backtesting and execution framework |
| 16 | charllysb/pumpfun-momentum-bot | CRY | `0dccad2fa559` | niche: slippage modeling and honest backtest claims |
| 17 | cudam321/signal-backtest-harness | CAT | `84643ded87e9` | niche: measurement-first harness for Telegram signal calls |
| 18 | defipy-devs/uniswappy | AMM | `8c729b5423ba` | Python re-implementation of Uniswap V2/V3 math |
| 19 | MeteoraAg/dlmm-sdk | AMM | `af36dd53ab18` | official DLMM bin math (TypeScript/Rust) |
| 20 | raydium-io/raydium-sdk-V2 | AMM | `e2e8bcd86518` | official Raydium AMM/CLMM quote math |
| 21 | orca-so/whirlpools | AMM | `cc683ec92acb` | official Whirlpool CLMM math |
| 22 | eslazarev/purged-cross-validation | VAL | `07692dd862d3` | purged k-fold, CPCV, PBO, DSR; MIT |
| 23 | ranaroussi/quantstats | VAL | `9ef4c6d0a4ff` | performance analytics |
| 24 | esvhd/pypbo | VAL | `4d723f064982` | PBO implementation; AGPL |
| 25 | stefan-jansen/alphalens-reloaded | VAL | `1bc181de4aaf` | factor/event analysis |

Low-star niche candidates included on purpose (protocol asks for at least five): nikkisora/PolarBT, lblommesteyn/slotfish, prisyy/pumpsim-api, charllysb/pumpfun-momentum-bot, cudam321/signal-backtest-harness.

Not shortlisted but kept as references: zipline-reloaded, backtrader, hummingbot (live bot), uniswap-v3-liquidity-math, ACNoonan/solana-dlmm-meteora (Rust DLMM math), 0xfnzero/solana-program-idls (layouts), skfolio.

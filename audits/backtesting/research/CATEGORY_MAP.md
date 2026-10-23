# Category map (Phase 02)

73 unique repositories (72 resolvable + 1 seed not found). Decisions: SHORTLIST 25, LONGLIST_ONLY 46, REJECT 2.

## 1 fast vectorized / parameter testing (7)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| polakowo/vectorbt | SHORTLIST |  |  | fast signal/parameter studies; check OSS vs PRO split |
| kernc/backtesting.py | SHORTLIST | 9117 | AGPL-3.0 | canonical prototype engine with tests |
| nikkisora/PolarBT | SHORTLIST | 13 | MIT | niche: polars engine with pump.fun trade data and AMM-aware slippage |
| pmorissette/bt | SHORTLIST |  |  | portfolio composition |
| ematvey/pybacktest | LONGLIST_ONLY | 825 | MIT | unmaintained since 2021; superseded by vectorbt |
| QuantMLResearch/pyrust-bt | LONGLIST_ONLY | 324 |  | hybrid Rust engine; equities focus |
| BobbyAxerol/quantbt | LONGLIST_ONLY | 11 | MIT | generic event/vector SDK, low evidence |

## 2 event-driven / ledger engines (15)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| nautechsystems/nautilus_trader | SHORTLIST |  |  | high-fidelity event-driven engine |
| QuantConnect/Lean | SHORTLIST |  |  | event-driven accounting reference; C# platform |
| freqtrade/freqtrade | SHORTLIST |  |  | crypto strategy research; CEX candles |
| jesse-ai/jesse | SHORTLIST |  |  | crypto engine; license check |
| nkaz001/hftbacktest | SHORTLIST |  |  | latency and queue-aware replay |
| gbeced/basana | SHORTLIST | 871 | NOASSERTION | async event-driven framework (Python) |
| stefan-jansen/zipline-reloaded | LONGLIST_ONLY |  |  | equity calendars; reviewed by reference only |
| mementum/backtrader | LONGLIST_ONLY |  |  | mature but unmaintained; GPL-3.0 |
| cloudQuant/backtrader | LONGLIST_ONLY | 202 | GPL-3.0 | fork of backtrader; GPL-3.0 |
| hummingbot/hummingbot | LONGLIST_ONLY |  |  | live market-making bot; excessive live code |
| josephchenhk/qtrader | LONGLIST_ONLY | 548 |  | no license in search metadata |
| ricequant/rqalpha | LONGLIST_ONLY | 6837 | NOASSERTION | China equities focus; NOASSERTION license |
| coding-kitties/investing-algorithm-framework | LONGLIST_ONLY | 2191 | Apache-2.0 | app framework, CEX focus |
| bsdz/yabte | LONGLIST_ONLY |  |  | small engine, equities |
| ml4t/backtest | LONGLIST_ONLY |  |  | cross-engine parity ideas; verify existence |

## 3 crypto / DEX / Solana strategy tools (16)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| lblommesteyn/slotfish | SHORTLIST | 0 | MIT | niche: deterministic event-driven engine for pump.fun microstructure |
| etcherfx/sol-trade | SHORTLIST |  |  | Solana/Jupiter bot with backtest; GPL; live trading must stay off |
| sohan-shingade/flint | SHORTLIST | 7 | MIT | Solana research claims to verify |
| prisyy/pumpsim-api | SHORTLIST | 0 | MIT | niche: off-chain pump.fun curve and PumpSwap simulation |
| tradingstrategy-ai/trade-executor | SHORTLIST |  |  | DEX-native backtesting and execution framework |
| charllysb/pumpfun-momentum-bot | SHORTLIST | 1 | MIT | niche: slippage modeling and honest backtest claims |
| onecandlecat/one-more-candle | LONGLIST_ONLY | 0 | MIT | TypeScript fee math; idea source |
| JonKater/solana-memecoin-backtesting-engine | LONGLIST_ONLY | 0 |  | no license, no language metadata |
| Kombucho/memecoin-gamble-research | LONGLIST_ONLY | 0 | MIT | study of 4,293 callouts; research reference |
| cavalheiroeth/pumpfun-sniping-lab | LONGLIST_ONLY | 0 |  | sniping study; no license |
| ggiordann/solana | LONGLIST_ONLY | 0 |  | course project CPMM slippage; no license |
| nischayhegde/solana-copytrading-backtester | LONGLIST_ONLY | 1 |  | wallet heuristics scripts; no license |
| kennethcudiadev/solana-bot-backtest | LONGLIST_ONLY | 8 |  | Rust, no license |
| Drakkar-Software/OctoBot | LONGLIST_ONLY | 6842 | GPL-3.0 | live CEX bot; GPL |
| hzcx404/memecoin-trading-bots | REJECT |  |  | README pushes zip downloads from raw paths: malware-lure pattern |
| Twilightfobeam/liquidity-sniper-bot-dd60 | REJECT | 0 | NOASSERTION | templated spam repos with random suffixes; malware-lure pattern |

## 4 AMM / CLMM / DLMM / routing math (14)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| defipy-devs/uniswappy | SHORTLIST |  |  | Python re-implementation of Uniswap V2/V3 math |
| MeteoraAg/dlmm-sdk | SHORTLIST | 310 |  | official DLMM bin math (TypeScript/Rust) |
| raydium-io/raydium-sdk-V2 | SHORTLIST |  |  | official Raydium AMM/CLMM quote math |
| orca-so/whirlpools | SHORTLIST |  |  | official Whirlpool CLMM math |
| atiselsts/uniswap-v3-liquidity-math | LONGLIST_ONLY |  |  | reference equations for v3 liquidity |
| DefiLab-xyz/uniswap-v3-backtest-python | LONGLIST_ONLY | 18 |  | LP backtest, not trader execution; no license |
| revert-finance/revert-backtester | LONGLIST_ONLY | 47 | MIT | Clojure LP backtester |
| ACNoonan/solana-dlmm-meteora | LONGLIST_ONLY | 6 | Apache-2.0 | niche: pure-Rust no-RPC DLMM swap math |
| joaquinbejar/py-defi-amm | LONGLIST_ONLY | 4 | MIT | Python AMM implementation; small |
| bowtieddevil/degenbot | LONGLIST_ONLY |  |  | EVM pool state/sim library; EVM-only |
| 0xfnzero/solana-program-idls | LONGLIST_ONLY | 34 | MIT | IDL catalog for pump/pumpswap/raydium/meteora layouts |
| solana-foundation/surfpool | LONGLIST_ONLY |  |  | pump/pumpswap state templates; local validator |
| AmirhosseinHonardoust/Defi-Risk-Scenario-Lab | LONGLIST_ONLY | 16 | MIT | DeFi stress-testing lab (Solidity based) |
| dexterous/serum-dex | LONGLIST_ONLY |  |  | historical reference only; verify existence |

## 5 social / catalyst / event study / wallet (6)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| cudam321/signal-backtest-harness | SHORTLIST | 0 | MIT | niche: measurement-first harness for Telegram signal calls |
| CryptoPrism-io/CryptoPrism-DB-Backtest | LONGLIST_ONLY | 0 |  | sentiment long/short backtest; no license |
| yellowbear27/insider_event_study | LONGLIST_ONLY | 0 | MIT | event study of disclosures; MIT |
| Neogus/X-Sentiment-Analysis | LONGLIST_ONLY | 0 |  | X sentiment backtest; no license |
| DracoR22/handi-cat_wallet-tracker | LONGLIST_ONLY | 206 |  | live wallet tracker bot; no license |
| AI4Finance-Foundation/FinRL | LONGLIST_ONLY |  |  | RL training discipline; heavy |

## 6 validation / metrics / robustness (15)

| Repo | Decision | Stars at search | License at search | Reason |
|---|---|---:|---|---|
| eslazarev/purged-cross-validation | SHORTLIST | 58 | MIT | purged k-fold, CPCV, PBO, DSR; MIT |
| ranaroussi/quantstats | SHORTLIST |  |  | performance analytics |
| esvhd/pypbo | SHORTLIST | 144 | AGPL-3.0 | PBO implementation; AGPL |
| stefan-jansen/alphalens-reloaded | SHORTLIST |  |  | factor/event analysis |
| quantopian/alphalens | LONGLIST_ONLY |  |  | archived predecessor; use alphalens-reloaded |
| mnemox-ai/deflated-sharpe | LONGLIST_ONLY | 8 | Apache-2.0 | DSR only |
| Aliipou/backtest-audit | LONGLIST_ONLY | 7 |  | audit harness; no license |
| bettyguo/agent-backtest-lab | LONGLIST_ONLY | 7 | Apache-2.0 | leakage audit harness for LLM agents; Apache-2.0 |
| DaruFinance/quant-research-framework | LONGLIST_ONLY |  |  | validation ideas; verify |
| niharmaddina/quant-strategy-framework | LONGLIST_ONLY |  |  | frozen universes/holdouts; verify |
| Finance-broski/backtest-bias | LONGLIST_ONLY |  |  | bias checklist tooling |
| rytjy/backtest-audit-kit | LONGLIST_ONLY |  |  | audit kit |
| ArturSepp/QuantInvestStrats | LONGLIST_ONLY | 642 | MIT | portfolio analytics |
| TonyMa1/walk-forward-backtester | LONGLIST_ONLY | 12 | MIT | WFO implementation; MIT |
| skfolio/skfolio | LONGLIST_ONLY |  |  | portfolio optimization with CPCV |

## Landscape notes

- Mainstream engines (vectorbt, backtesting.py, nautilus, Lean, freqtrade, jesse, backtrader, zipline) are candle- or order-book based and CEX/equity oriented. None models AMM reserves natively.
- Solana memecoin backtesters exist only as low-star niche projects (PolarBT, slotfish, pumpsim-api, pumpfun-momentum-bot, one-more-candle, JonKater engine). Five or more credible niche candidates found, as the protocol asks.
- AMM math lives in official SDKs (Raydium, Orca, Meteora; TypeScript/Rust) and Python re-implementations (uniswappy). No Python library found that replays historical Solana pool reserves.
- Catalyst/social backtesting OSS is thin and mostly coursework. The lab's own catalyst and social layers are ahead of what exists publicly.
- Validation tooling is healthy (purgedcv, pypbo, deflated-sharpe, skfolio, quantstats, alphalens-reloaded).
- Spam and malware-lure repos appear in memecoin and sniper searches (templated names, zip downloads from raw paths). Two recorded as REJECT.

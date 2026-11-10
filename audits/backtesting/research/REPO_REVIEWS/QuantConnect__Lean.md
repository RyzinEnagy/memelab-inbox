# QuantConnect/Lean

- URL: https://github.com/QuantConnect/Lean
- Pinned commit: f3d841e60dfd010ee5fc293ea893e56952484108 (2026-10-21T18:07:14-03:00), cloned 2026-10-23T15:53:00Z with `git clone --depth 1` (branch master, 504 MB checkout). Matches LONGLIST head_sha_2026_10_23.
- Category: event-driven
- Discovery channel: seed (LONGLIST)
- Stars/forks (low weight, from search time): not recorded at search time
- License (from LICENSE file text, not badge): Apache-2.0 (191-line Apache License 2.0 text) ; transitive notes: QuantConnect.pythonnet fork, NuGet packages; Docker foundation image bundles a large conda stack (DockerfileLeanFoundation)
- Package: none on PyPI for the engine (not installed, not built per instructions) ; Python/OS: C# .NET 10 (Common/QuantConnect.csproj:5); Python algorithms hosted through QuantConnect.pythonnet 2.0.66 (csproj:38) against Python 3.11 (DockerfileLeanFoundation:27-30) ; native deps: .NET runtime, libpython 3.11
- Maintenance: last commit 2026-10-21; CI files gh-actions.yml, regression-tests.yml, research-regression-tests.yml, syntax-tests.yml, benchmarks.yml, api-tests.yml, report-generator.yml and more; tests 830 C# files under Tests/ (NUnit) plus regression algorithms
- Security surface: not built or run; contains live brokerage integrations needing API keys (Brokerages/, Common/Brokerages), data downloaders (ToolBox, DownloaderDataProvider), Dockerfiles that wget installers; no wallet code

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | Common/Data/Market/TradeBar.cs:109-113 EndTime = Time + Period (bars delivered at end time) |
| tick/trade replay | SOURCE_CODE_VERIFIED | Tick, QuoteBar, TradeBar market data types (Common/Data/Market/) and tick resolution subscriptions |
| CPMM math | NOT_SUPPORTED | grep for AMM / Uniswap / constant product / liquidity pool in Common and Engine returns nothing |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | SOURCE_CODE_VERIFIED | 33 *FeeModel.cs files in Common/Orders/Fees/ (BinanceFeeModel.cs, CoinbaseFeeModel.cs, dYdXFeeModel.cs, ConstantFeeModel.cs, ...); no token transfer tax |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (models exist, defaults off) | Common/Orders/Slippage/VolumeShareSlippageModel.cs:35-38, 84-86 (impact = min(qty/barVolume, 2.5%)^2 x 0.1, order still fills in full); MarketImpactSlippageModel.cs:97-135 (Almgren et al. 2005 temporary + permanent impact with Gaussian noise); default is NullSlippageModel (Common/Brokerages/DefaultBrokerageModel.cs:281-284; crypto: Common/Securities/Crypto/Crypto.cs:65-67) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | market orders from OnData are filled synchronously in the same time step (Engine/AlgorithmManager.cs:585-601, Engine/TransactionHandlers/BacktestingTransactionHandler.cs:64-80) at prices.Current = latest close (Common/Orders/Fills/FillModel.cs:282-338, 1107-1119); no latency model in the default fill path |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | data emitted at EndTime (TradeBar.cs:109-113); stale-price guard waits for fresh data instead of filling on fill-forward data (FillModel.cs:297-313); non-market orders are processed on new data before OnData (AlgorithmManager.cs:344-346) |
| async event/catalyst injection | SOURCE_CODE_VERIFIED | custom data types with their own time/EndTime via BaseData/PythonData GetSource/Reader (Common/Python/PythonData.cs:27-103) merged into the time slices |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | multi-security portfolio, cash book, universe selection (Common/Securities/, Algorithm.Framework) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (partial) | parameter optimizer with grid and Euler search (Optimizer/Strategies/GridSearchOptimizationStrategy.cs, EulerSearchOptimizationStrategy.cs); Probabilistic Sharpe Ratio (Common/Statistics/Statistics.cs:200); no walk-forward or multiple-testing correction (grep walk-forward finds only an unrelated time-zone file) |
| metrics/report | SOURCE_CODE_VERIFIED | Common/Statistics/ (PortfolioStatistics.cs, TradeStatistics.cs), Report/ (Crisis.cs, DrawdownCollection.cs, PointInTimePortfolio.cs) |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | Brokerages/ and live engine paths; avoidable via backtest job config |

## Fill and chronology assumptions (read the code)

Each time slice carries bars whose EndTime = Time + Period (TradeBar.cs:109-113), so OnData sees only completed bars. Before OnData, the engine runs fill models on the new data for resting non-market orders (AlgorithmManager.cs:344-346). After OnData returns, `transactions.ProcessSynchronousEvents()` processes the new requests synchronously in backtests (AlgorithmManager.cs:598-601; BacktestingTransactionHandler.cs:64-80), and FillModel.InternalMarketFill fills market orders at `prices.Current`, the latest close, for the full quantity (FillModel.cs:315-335), unless the order was resting before the current bar opened, in which case the bar open is used (FillModel.cs:1107-1119). Result: signal on bar k close fills at bar k close with zero latency, the same assumption as nautilus_trader and jesse, and one bar earlier than freqtrade/basana. Slippage defaults to zero; the VolumeShare model caps the volume share at 2.5% so slippage saturates at 0.00625% while the order still fills in full; the MarketImpact model is genuinely size-dependent but calibrated for equities (shares outstanding adjustment, MarketImpactSlippageModel.cs:117-119). Custom fill and slippage models can be written in Python (Common/Python/FillModelPythonWrapper.cs:27, SlippageModelPythonWrapper.cs:26).

## Smoke test (if feasible, no wallets, no network beyond pip)

```
not run (C# engine; instructions: do not build Lean). See smoke/QuantConnect__Lean/output.txt.
```
Outcome: NOT_RUN. Fill timing taken from source only (same-bar close, synchronous); not runtime-verified.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.0 | 3.00 | no AMM or Solana concepts; crypto treated as CEX securities |
| B microstructure | 17 | 2.5 | 8.50 | Almgren impact model, volume-share model, many fee models, stale-price guard; defaults are zero slippage and full fills; no depth or route model |
| C point-in-time | 15 | 3.0 | 9.00 | EndTime semantics, fill-forward awareness, stale-price guard (source only, no runtime check); same-close zero-latency market fills |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | custom data types merged into time slices; no on-chain adapters |
| E TA/strategy flexibility | 9 | 4.0 | 7.20 | very large indicator library, consolidators, Algorithm Framework |
| F statistical validation | 11 | 2.0 | 4.40 | optimizer (grid/Euler), PSR, crisis reports; no walk-forward or holdout tooling |
| G integration fit | 9 | 0.5 | 0.90 | C#/.NET 10 host, Python 3.11 only, Docker-centric; cannot be imported from a Python 3.13 package |
| H maintenance/tests | 6 | 5.0 | 6.00 | active, 830 test files, regression CI |
| I license/supply chain | 5 | 5.0 | 5.00 | Apache-2.0 |
| J operational footprint | 2 | 1.0 | 0.40 | .NET runtime plus multi-GB foundation image in practice |
| Total | 100 | | 49.90 | |

Hard gates: none. Most important limitation for memecoins: the engine cannot run inside the lab's Python 3.13 process at all, and it has no AMM/pool model, so its value is as a design reference only. One credible negative finding: VolumeShareSlippageModel clamps the volume share at volumeLimit (VolumeShareSlippageModel.cs:84-86) while FillModel still fills 100% of the order (FillModel.cs:335), so an order of 500x bar volume pays at most 0.00625% slippage, a silent unlimited-liquidity assumption.
Disposition: REFERENCE. Suggested use: REFERENCE (reuse the ideas of EndTime-stamped data, the stale-price fill guard and the Almgren impact formula; Apache-2.0 allows reimplementation freely).

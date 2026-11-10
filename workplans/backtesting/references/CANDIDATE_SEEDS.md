# Unranked GitHub research leads — verify afresh

The URLs below are **starting hypotheses**, not verified top ten, endorsements, implementation instructions or claims that a capability exists in an audited commit. Sources were initially identified from GitHub and independent curated lists around October 23, 2026. The research phase must check real source, current dependencies, legal obligations and up-to-date capability. Some are deliberately cross-domain; gaps exposed by failures can be as instructive as winners.

## Backtest engines / parameter research

- https://github.com/polakowo/vectorbt — fast arrays, signal/parameter studies; inspect version-specific open-source vs PRO feature split.
- https://github.com/freqtrade/freqtrade — crypto strategy/batch research; distinguish CEX candles from Solana DEX execution.
- https://github.com/nautechsystems/nautilus_trader — event-driven high-fidelity simulation; integration complexity and data adapters.
- https://github.com/QuantConnect/Lean — event-driven accounting/risk; large platform footprint.
- https://github.com/kernc/backtesting.py — approachable signal prototype and canonical tests.
- https://github.com/jesse-ai/jesse — crypto strategy engine; licensing and exchange assumptions.
- https://github.com/stefan-jansen/zipline-reloaded — event/portfolio replay; market/calendar assumptions.
- https://github.com/mementum/backtrader — mature reference ideas; maintenance/licensing verification.
- https://github.com/pmorissette/bt — portfolio strategy composition, maybe limited for microstructure.
- https://github.com/ml4t/backtest — cross-engine parity and diagnostic methodology; verify claims independently.

## Crypto / DEX execution and market-microstructure research

- https://github.com/hummingbot/hummingbot — market making/connector models; live-bot code may be excessive.
- https://github.com/nkaz001/hftbacktest — latency/order book queue replay; assess AMM transferability.
- https://github.com/etcherfx/sol-trade — Solana/Jupiter bot and backtest research, quotes and gates; GPL-3.0 requires legal handling before code reuse; **do not enable live trading**.
- https://github.com/sohan-shingade/flint — Solana/DEX/perpetual research claims; check what is actually built.
- https://github.com/dexterous/serum-dex — historical architecture reference only; check archived/deprecated status before treating as viable.
- https://github.com/raydium-io/raydium-sdk-V2 — Solana AMM/CLMM state and quote maths; not presumed a backtester.
- https://github.com/MeteoraAg/dlmm-sdk — DLMM bin-level primitives; not presumed a historical simulator.
- https://github.com/orca-so/whirlpools — concentrated-liquidity math; confirm supported source/language versions.

## Factors, analytics, validation, reproducibility

- https://github.com/ranaroussi/quantstats — performance/tearsheet analytics, not a trading engine.
- https://github.com/quantopian/alphalens — factor analysis historical reference; look for maintained forks/successors.
- https://github.com/AI4Finance-Foundation/FinRL — training/evaluation discipline; likely over-complex for initial engine.
- https://github.com/DaruFinance/quant-research-framework — validation ideas; verify implementation and license.
- https://github.com/niharmaddina/quant-strategy-framework — frozen historical universes/holdouts; verify implementation.

## Research discovery feeders (not final candidates unless source fit qualifies)

- https://github.com/WallStreetPete/awesome-open-source-trading
- https://github.com/jeff3388/awesome-backtesting-python
- GitHub code/topic searches and issue/PR references within every eligible repository.

**Important**: URLs may disappear, move, be archived, change license or require unavailable data. Treat that as a finding, not a reason to invent a replacement. The candidate pool must expand beyond this list, and there is **no requirement** that any seed appear in the final ten.

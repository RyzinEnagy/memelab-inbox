# Adoption decisions (Phase 04)

Rules applied: adoptable code needs >= 70/100, license/security pass, C >= 3 or sandboxed, isolated POC success; any engine used for historical fills needs B >= 3 plus the golden scenarios. No reviewed repo passed (TOP10.md). Decisions per capability:

| Capability | Decision | Method | Evidence |
|---|---|---|---|
| Event replay, order lifecycle, portfolio ledger | REIMPLEMENT | `memelab/backtest/engine.py` grown from the bake-off prototype; ideas from slotfish (deterministic ordering), basana (liquidity hook), sol-trade (closed bars only, persistent trial count) | prototype = oracle on all cases; 30x faster than backtesting.py, 50x faster than vectorbt on the timing universe |
| Bar chronology conventions | REIMPLEMENT | next-bar open after decision + latency; gap stop at open; stop before take-profit | prototype and backtesting.py agree on every fill |
| CPMM execution | REIMPLEMENT from the constant-product formula | exact float math with explicit fee on input; PumpSwap requires effective quote reserves (vault + signed virtual_quote_reserves) and fee tier, otherwise labeled approximate | oracle match for $1k and $50k |
| CLMM (Raydium CLMM, Orca) and DLMM (Meteora) | DO NOT IMPLEMENT historically | refuse with UNSUPPORTED_POOL unless a router quote observed at decision time exists; Orca code license proprietary, Raydium GPL, Meteora unlicensed: formulas only from public math if ever needed | no free historical tick/bin state |
| Chronological validation (walk-forward, purge, embargo, sealed test) | REIMPLEMENT | extend the lab's own `social/replay_core` LabelGate pattern; no new dependency | purgedcv below 70 (46.90 / 40.30 blind) |
| Statistics (bootstrap, deflated Sharpe if justified) | REIMPLEMENT | numpy only; trial counter persisted per experiment | |
| Performance analytics | REIMPLEMENT minimal set | expectancy, drawdown, tail loss, per-size proceeds | quantstats rejected (yfinance import, 252-day defaults) |
| Paired engine validation (G29) | AUDIT-ONLY external oracle | backtesting.py and vectorbt in isolated venvs, scripts under `audits/backtesting/bakeoff/`; never imported by the lab, not in any requirements | compare.py 16/16 |
| Anything with live trading, wallets or keys | REJECT | sol-trade, pumpfun-momentum-bot, hummingbot, freqtrade live paths never imported | review cards |

## Maxun (separate track, not part of the engine decision)

- Direct AGPL-3.0 source integration (vendoring or modifying Maxun inside the lab): NO-GO without a separate legal decision by Elving.
- Self-hosting unmodified Maxun as a separate service: needs Docker, Postgres, MinIO and the browser image; not installed, not authorized. NO-GO for now.
- Thin client of Maxun Cloud over HTTPS (no Maxun code in the lab): license-compatible. Security: API key read at runtime from `D:\memelab\maxun-token.txt`, never printed. Cost: TRIAL plan, 5 credits. Decision on usefulness deferred to the Phase 06A bake-off. Nothing is installed in Phase 04.

## Bill of materials

See `BOM.md`.

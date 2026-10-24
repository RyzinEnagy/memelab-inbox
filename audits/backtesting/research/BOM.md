# Dependency bill of materials (Phase 04)

## Lab runtime (memelab/backtest)

| Package | Version seen | Already a lab dependency | Use |
|---|---|---|---|
| Python | 3.13 | yes | |
| numpy | 2.5.x | yes (README: `pip install pytest numpy`) | arrays, bootstrap |
| sqlite3 | stdlib | yes | storage |
| hashlib, json, bisect, statistics, random | stdlib | yes | hashing, IO, as-of joins, seeded baselines |

No new runtime dependency. pandas is not required by the engine.

## Lab tests

pytest (already used). No AGPL or copyleft package in the lab test suite.

## Audit-only tools (isolated venvs under /home/claude/ext/venvs, not shipped, not in requirements)

| Package | Version | License | Pinned upstream commit reviewed |
|---|---|---|---|
| backtesting | 0.6.6 (PyPI) | AGPL-3.0 | kernc/backtesting.py ca2e2611621e |
| vectorbt | 1.2.0 (PyPI) | Apache-2.0 + Commons Clause | polakowo/vectorbt 8e30b8ce102f |
| purgedcv | 0.1.11 (PyPI) | MIT | eslazarev/purged-cross-validation 07692dd862d3 |

## External services used read-only

GeckoTerminal public API (OHLCV, pools), DexScreener, Jupiter `/swap/v1/quote`, Firecrawl (budgeted), Maxun Cloud (trial, budgeted, Phase 06A), local Crawl4AI 0.9.5 on Elving's computer.

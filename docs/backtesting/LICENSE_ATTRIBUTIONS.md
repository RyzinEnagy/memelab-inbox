# License attributions and bill of materials

Scope: the backtesting package (`memelab/backtest/`), its tests and the evidence under `audits/backtesting/`. The lab repository itself has no LICENSE file.

## Runtime dependencies added by the backtesting package

None. The package's own modules import only the Python standard library (argparse, bisect, collections, copy, dataclasses, datetime, hashlib, html, json, math, os, pathlib, random, re, sqlite3, statistics, subprocess, sys, time, typing, urllib) and other lab modules. The CLI and the hook call into the lab's pipeline, and the lab already uses numpy, so `backtest stress` loads numpy through the lab. Pinned test and numeric versions: docs/backtesting/requirements-test.txt.

## Version matrix (verified)

| Component | Version | Where verified |
|---|---|---|
| Python | 3.13.17 | container and the Phase 17 clean venv |
| SQLite (Python's sqlite3) | 3.45.1 | same |
| pytest (tests only) | 9.1.1 | clean venv, pinned |
| numpy (lab, not the backtest package) | 2.5.3 | clean venv, pinned |
| Operating system | Linux 6.18 x86_64 | Phase 17 clean install |

Not verified: Windows and macOS. The backtest package uses only portable standard-library calls. Its multi-process tests use the fork start method and skip on Windows.

## Code copied from other projects

None. 25 repositories were reviewed at pinned commits (audits/backtesting/research/REPO_REVIEWS/, TOP10.md, LEGAL_LICENSE_GATE.md). Ideas were reimplemented from public math and the reviews; no source text was copied. The ideas and their sources:

| Idea used | Reviewed at | License |
|---|---|---|
| exact constant-product math and slot-ordered deterministic replay; an explicit lookahead test | lblommesteyn/slotfish @ 4f760c80 | MIT |
| next-open fills, closed-bar storage, sealed holdout with persistent trial count | etcherfx/sol-trade @ c8f37ad2 | GPL-3.0 (ideas only; no code, no text) |
| pluggable liquidity hook, next-bar open fills | gbeced/basana @ 0c65f58b | Apache-2.0 |
| latency-aware fills | nkaz001/hftbacktest @ 5f3ec40b | MIT |
| purged splits, embargo, walk-forward | eslazarev/purged-cross-validation @ 07692dd8 | MIT |
| bar chronology rules (next-bar open, gap-through stop at the open, stop before target) | kernc/backtesting.py @ ca2e2611 | AGPL-3.0 (reference only) |
| PumpSwap effective quote reserve (vault plus signed virtual reserve) | read from on-chain pool accounts and checked against live Jupiter quotes (Phase 07) | public chain data |
| CLMM math (not implemented; CLMM pools are UNSUPPORTED_POOL) | Uniswap v3 whitepaper | public |

## Audit-only tools (never shipped, never imported by the lab)

These were used in isolated virtual environments as external oracles in Phase 04 (audits/backtesting/bakeoff/):

| Package | Version | License | Use |
|---|---|---|---|
| backtesting | 0.6.6 | AGPL-3.0 | chronology oracle, unmodified, plot() never called |
| vectorbt | 1.2.0 | Apache-2.0 with Commons Clause | sweep oracle, internal use only |
| purgedcv | 0.1.11 | MIT | split-leakage cross-check |

## Collectors and services

| Service | How it was used | License or terms | Status |
|---|---|---|---|
| GeckoTerminal public API | OHLCV and pool lists, read-only, budgeted with backoff | public API terms | historical corpus source |
| DexScreener, Jupiter quote | read-only checks | public API terms | spot checks |
| Solana public RPC | pool account reads | public | spot checks |
| Firecrawl | budgeted page fetches and searches (about 32 of about 100 approved calls) | paid account owned by Elving | lab catalyst layer and audit confirmation |
| Crawl4AI 0.9.5 | local runs on Elving's computer, Phase 06A bake-off | Apache-2.0 with an added attribution requirement in its upstream LICENSE | evaluated; existing collector kept; not shipped or imported, so no attribution is owed by the lab today |
| Maxun Cloud | 5 trial credits, one-shot evaluation runs, no schedule | Maxun source is AGPL-3.0-or-later; Cloud use over HTTPS creates no AGPL obligation for the lab (D-BT-015) | NOT_ADOPTED (D-BT-020). Not installed, embedded or called by the runtime. The evaluation robot is idle with no schedule; Elving may delete it in the Maxun console. |

Orca's whirlpools license is proprietary and treats even reading as use. The package does not depend on it; CLMM math comes from the public Uniswap v3 whitepaper. This was flagged for Elving's awareness in Phase 03.

# sohan-shingade/flint

- URL: https://github.com/sohan-shingade/flint
- Pinned commit: 5ce552c881097f37f38c6ee53146f1b64cb3db95 (2026-07-12T23:52:45-07:00), cloned 2026-10-23T15:52:43Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (LONGLIST pushed_at 2026-07-18 is the push date, same SHA).
- Category: event-driven (perp/CLOB; listed under crypto/DEX/Solana)
- Discovery channel: seed; GITHUB_API "solana backtest" (rank 7)
- Stars/forks (low weight, from search time): 7/not recorded
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 Sohan Shingade) ; transitive notes: core dependency nautilus_trader==1.230.0 is LGPL-3.0-or-later (PyPI metadata); optional eth-account, ccxt, optuna, mcp
- Package: not on PyPI under its own name. The PyPI name `flint` (0.0.1) is an unrelated Fortran analysis tool, so `pip install flint` installs the wrong project ; Python/OS: requires-python >=3.12,<3.15 ; native deps: nautilus_trader wheel (182.5 MB cp313 manylinux x86_64, 109.6 MB win_amd64), duckdb, pyarrow
- Maintenance: last commit 2026-07-12; CI files .github/workflows/ci.yml, parity.yml, live-smoke.yml; tests 76 Python test files, 884 test functions (pytest), plus vitest UI tests. ci.yml references 8 test/script files and a `rust/` directory that do not exist at this SHA, and runs Python 3.10/3.11 which pyproject excludes
- Security surface: Hyperliquid live executor signs with a key from SecretsPort (flint/live/executor.py:226-242); FastAPI server with bearer token; user strategy code runs in a subprocess sandbox whose OS jail is a stub (flint/strategy/sandbox/oslayer.py:1-7,26-29); install.sh, Makefile, Dockerfile, docker-entrypoint.sh and a TypeScript sidecar (not run)

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED | Nautilus bar lane flint/engine/nautilus/engine.py, shim.py; DuckDB store flint/data/store/duckdb_adapter.py |
| tick/trade replay | SOURCE_CODE_VERIFIED | L2/trade tick lane flint/engine/nautilus/ticklane.py; Tardis vendor lane flint/data/ingest/vendors/tardis.py; fixtures tests/fixtures/tardis/*.csv.gz |
| CPMM math | NOT_SUPPORTED | 0 hits for constant product, sqrt price, ticks, bins, reserves in flint/ (smoke [3]) |
| CLMM/DLMM math | NOT_SUPPORTED | same |
| routes | NOT_SUPPORTED | Jupiter venue is a one-line docstring: flint/venues/jupiter/__init__.py:1 |
| fees/taxes | SOURCE_CODE_VERIFIED (CLOB only) | Taker/maker fee from VenueSpec: flint/engine/fills/clob.py:186, flint/engine/fills/naive.py:56; funding settlement flint/engine/funding/settlement.py. No token taxes |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED (CLOB only) | Book walk with VWAP and partials flint/engine/fills/clob.py:79-136; Tier C square-root impact on bar dollar volume clob.py:174-185; zero-volume bar rejected clob.py:175-176 |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | Market orders decided last bar fill at this bar's open: flint/engine/nautilus/shim.py:175-176,231; seeded lognormal latency selects the book as-of submit+latency: flint/engine/fills/latency.py:96-112, flint/engine/fills/assemble.py:44-62 |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | Strategy view "strictly less than bar start, closed data only": flint/engine/loop.py:9-12; AST lint plus truncation probe flint/research/lookahead.py:248,280; tests/test_research_lookahead.py |
| async event/catalyst injection | NOT_SUPPORTED | Only funding, marks, OI; on-chain ingest is a one-line docstring: flint/data/ingest/onchain/__init__.py:1 |
| wallets/on-chain | NOT_SUPPORTED | none for research; live HL signing only |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED | Multi-market universe and per-venue margin: flint/engine/state.py, flint/data/universe.py |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED | Expanding walk-forward with purge/embargo flint/research/walkforward.py:192-234, guard warnings :237-254; deflated Sharpe flint/research/deflated.py:151; no sealed holdout found |
| metrics/report | SOURCE_CODE_VERIFIED | flint/research/tearsheet.py, flint/engine/tearsheet.py |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED | flint/live/executor.py:10-11,226-242 (signing key from SecretsPort); separate package, avoidable |

## Fill and chronology assumptions (read the code)

A strategy's `on_candle` returns Signals; market orders produced at bar t are queued and filled at the open of bar t+1 (flint/engine/nautilus/shim.py:175-176,231). The fill context takes effective time = candle.ts + one seeded lognormal latency draw and selects the recorded order book at or before that time (assemble.py:44-62). With book plus trades the CLOB model walks depth (Tier A), with book only it walks depth and estimates maker fills (Tier B), and with no book it fills at the next open plus half-spread plus k x sqrt(notional / bar dollar volume) impact, flagged `uncalibrated` (Tier C, clob.py:174-205). Each fill records its fidelity tier. The strategy context is restricted to data strictly before bar start (loop.py:9-12). None of this applies to AMMs: the only DEX-like structure, ORACLE_POOL, raises NotImplementedError (flint/engine/fills/oracle_pool.py:25-29).

## Smoke test (if feasible, no wallets, no network beyond pip)

```
# Not installed: niche repo (7 stars), PyPI name collision, 180 MB nautilus_trader wheel, install.sh/Makefile not run.
# Static AST analysis only (no repo code imported or executed):
python3 -I audits/backtesting/research/smoke/sohan-shingade__flint/script.py /home/claude/ext/reviews/sohan-shingade__flint
```
Outcome: exit 0. venues/jupiter and data/ingest/onchain are docstring-only (0 statements); OraclePoolFillModel.fill is a single `raise`; 0 AMM-math hits in flint/; ci.yml references 9 missing paths (rust/, tests/test_rust_*.py, tests/test_sandbox_escape.py, tests/test_determinism.py, tests/test_fee_model_parity.py, scripts/update_readme_counts.py, and the ignored tests/test_jupiter_integration.py) and Python 3.10/3.11 against requires-python >=3.12. Output in smoke/sohan-shingade__flint/output.txt.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | Hyperliquid perps only; Solana/Jupiter/on-chain modules are stubs; fill-model seam and fidelity tiers are reusable ideas |
| B microstructure | 17 | 2.5 | 8.50 | Strong CLOB depth walk, partials, latency, sqrt impact; nothing for AMM pools |
| C point-in-time | 15 | 3.0 | 9.00 | T+1 fills, strict pre-bar context, lookahead lint and truncation probe; not run here and CI cannot be green |
| D catalyst/on-chain events | 11 | 0.5 | 1.10 | Funding/OI only; on-chain ingest stub |
| E TA/strategy flexibility | 9 | 3.5 | 6.30 | Python Strategy class, 14 templates, tick lane |
| F statistical validation | 11 | 3.0 | 6.60 | Walk-forward with purge/embargo, DSR, PSR, optuna; no sealed holdout or baseline gate |
| G integration fit | 9 | 1.5 | 2.70 | Python 3.13 OK, but Nautilus, FastAPI, DuckDB stack; sandbox uses Unix RLIMIT, OS jail stubbed; not Windows-ready |
| H maintenance/tests | 6 | 2.0 | 2.40 | 884 tests, but last commit 3 months ago and CI references deleted files |
| I license/supply chain | 5 | 3.0 | 3.00 | MIT plus LGPL Nautilus; uv.lock; PyPI name collision |
| J operational footprint | 2 | 1.5 | 0.60 | 110-180 MB engine wheel, web server, optional npm UI |
| Total | 100 | | 44.70 | |

Hard gates: none (MIT, code auditable). Most important limitation for memecoins: there is no AMM, Solana or Jupiter execution at all; every working fill model assumes a central limit order book with recorded depth. One credible negative finding: the README's security claim "nsjail/seccomp on Linux" is contradicted by flint/strategy/sandbox/oslayer.py:1-7 ("It is **not implemented yet**") and `os_layer_available()` returning False (oslayer.py:26-29), and the CI badge cannot reflect a passing suite because ci.yml runs files that no longer exist.
Disposition: REIMPLEMENT_IDEA. Suggested use: REFERENCE.

# PHASE 06: historical data adapters and data-quality defenses

State: PASS. Date 2026-10-23. Entry gate: Phase 05 PASS, rechecked (`python -m pytest tests/test_backtest_timeguard.py -q` 15 passed; `mutate.py p05_mutations.json` 7/7 caught).

## Changed files

- New: `memelab/backtest/sources/__init__.py`, `labstate.py` (frozen universe from every git version of data/state/latest.json), `gecko.py` (bounded GeckoTerminal pools and hourly OHLCV with budget, 429 backoff, raw shards, forming-bar refusal, duplicate-timestamp flag, point-in-time pool choice), `corpus.py` (resumable corpus build with a completion marker, coverage), `captures.py` (canonical web-capture registry: first_seen from our capture, versioning, no fake corroboration).
- New: `memelab/backtest/quality.py` (lab-vs-bars reconciliation, refusal policy, dataset hash, mint integrity).
- Changed: `memelab/backtest/store.py` (corpus query helpers: bars_asof, pools_valid_at, universe_asof, observation_series), `.gitignore` (`data/backtest/`), `audits/backtesting/testing/mutate.py` (copies the repo without data/backtest and caches).
- Tests: `tests/test_backtest_sources.py` (13), `tests/test_backtest_real_fixture.py` (4, real unmodified GeckoTerminal bytes for one collapsed token in `tests/fixtures/backtest/real/`).
- Evidence: `audits/backtesting/data/PROVENANCE.md`, `DATA_COVERAGE.md`, `SURVIVORSHIP_UNIVERSE.md`, `p06_coverage.json`, `p06_trades_probe.json`, fetch logs and manifest, mint lists, the fetch scripts; `testing/p06_mutations.json`, `testing/logs/p06_mutations.log`, `testing/logs/p06_corpus_runs.log`.

## What was built and proven on real data

261 Solana mints (all 201 thesis mints and a seeded 60 of 438 rejected-only mints), 257 with bars, 139,168 hourly bars, dataset hash `3d8dfd1e6dfa70575fc3f322de8b53b4e2cd316d793c3a8b0d02b9851e54e62a`. Reconciliation against the lab's own contemporaneous prices: 811 of 913 inside the bar range, 4 beyond 10%. A collapsed token (99.99% in three days, rejected by the lab at score 48) is kept and committed as a real fixture. Raw swap history is SOURCE_BLOCKED (the trades endpoint covers the latest 300 trades only; probe saved). Reserves, ticks, bins, holder history and wallet history stay SOURCE_BLOCKED; nothing is inferred from today's state.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_sources.py tests/test_backtest_real_fixture.py -q` | 0 | 17 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p06_mutations.json` | 0 | 12 of 12 caught |
| `python -m pytest tests -q` (whole repo, with later-phase work present in the tree) | 1 | 1 failed (C-1 only), 870 passed |
| `python tools/release_audit.py` | 0 | Needs action: no |
| corpus runs (`testing/logs/p06_corpus_runs.log`) | 0 | container 296 + 247 calls, work computer 424 calls (211 were 429s), 0 calls on replay |

## Bounded loop

Pass 1: corpus built in two places to share the per-IP rate limit; mutation M06-10 survived because it did not actually produce the bug it named (unique constraint already blocks it); the test was strengthened to re-ingest the same bytes a day later, and the mutation was rewritten to put the fetch time into the bar's content hash. Caught.
Pass 2 (adversarial): a mint whose pool list was fetched just before a stop signal had no bars, and the resume check counted it as done (real defect, found by comparing the work-computer manifest with the database). Fixed with a completion marker; regression test and mutation M06-11 added; replay picked up 341 missing bars. Negative control on falsely historic data: a page published in 2022 and first captured today is UNKNOWN_AS_OF at its claimed date (test_present_day_crawl_of_old_page_is_not_historical).
Pass 3 (adversarial): checked every universe mint string. Found two corrupted copies of real mints in the lab's exports (GAPS C4). Added `quality.mint_integrity` with a test that reports them and keeps them separate; mutation M06-12 caught.

## Independent negative review

Wrong-but-plausible outputs tried and caught: forming bar stored (M06-1), today's pool list used for the past (M06-2), unknown DEX treated as constant product (M06-3), pool choice by all-time volume (M06-4), page date backdating first_seen (M06-5), second crawler counted as a second source (M06-6), latest export only (M06-7), no 429 retry (M06-8), backfilled bar knowable at its close (M06-9), unchanged bar re-seen as revision (M06-10), resume skipping missing bars (M06-11), corrupted mints hidden (M06-12).

## Limitations

One page (1,000 hourly bars) per pool; 9 tokens truncated. One candidate pool per mint has bars. No-swap hours are gaps, not zeros. Universe covers 17 days. EVM theses are outside the corpus. Bar availability is modeled (close + 300 s) because the data was fetched after the fact; every such bar is flagged.

## Prepared for Phase 06A

`captures.record_capture` and `captures_asof` are the canonical external-document API: canonical origin, content hash, first_seen from capture evidence, versions never overwritten, mint only with verification, UNKNOWN_AS_OF for late captures.

NEXT ELIGIBLE PHASE: 06A.

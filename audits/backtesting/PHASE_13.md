# PHASE 13: per-opportunity automated evaluation

State: PASS. Date 2026-10-23. Entry gate: Phase 12 PASS at 999d1eb, reproduced (`pytest tests/test_backtest_stress.py`: 13 passed).

## Changed files

- New: `memelab/backtest/assess.py`. FAST stage, synchronous and offline:
  - snapshot taken from the lab's analyze result (main pool only, pool fee and its basis, authorities with the all-zero key read as "none");
  - stress at three sizes;
  - token signal states from the bundle's own closed and published bars;
  - empirical cohort evidence (only from 30 cases).
  - Request key: sha256(chain, mint, snapshot hash, engine version, policy hash, data revision).
  - Prechecks: invalid mint, stale snapshot, no price.
  - Abstain states are stored, never dropped.
  - A cached answer asked for after it aged out comes back as STALE_DATA.
  - Catalyst refresh (`on_catalyst`) guards: a verified mint, the same mint, availability (not publication) time, duplicate origin and content, and source outage.
  - DEEP stage (`run_deep`) replays this token's own stored history up to the assessment time.
  - `stats` gives counts and wall time by event.
- New: `memelab/backtest/hook.py`. `maybe_assess` returns None before touching any database when the policy is off. It never raises and never changes the analyze result. `one_line` prints one research-only line.
- `memelab/cli.py`: `analyze` prints the one line and `scout` attaches `r["backtest_assessment"]`, both only when the policy is on (`data/backtest/policy.json` or `MEMELAB_BACKTEST=1`). Nothing else changed.
- `memelab/backtest/cli.py`: `backtest deep` and `backtest assess-stats`.
- `tests/test_backtest_assess.py` (26).
- Fixed in passing: `tests/test_backtest_catalyst.py` used `pytest.skip` without importing pytest (Phase 09 defect). It would have raised NameError instead of skipping in a checkout without the state history. The release audit's pyflakes check found it.
- Evidence: `audits/backtesting/integration/p13_demo.py` and `p13_demo.json`; `testing/p13_mutations.json` and its log.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_assess.py -q` | 0 | 26 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p13_mutations.json` | 0 | 23 of 23 caught |
| `python audits/backtesting/integration/p13_demo.py` (real PAID analysis, copy of the real corpus) | 0 | see below |
| `python -m pytest tests -q` | 1 | 1 failed (C-1 only), 952 passed |
| `python tools/release_audit.py` | 0 | Needs action: no (pyflakes undefined names down from 2 to 1; the one left is in tools/release_audit.py itself, pre-existing) |
| `python tools/release_e2e.py` | 0 | PASS 78 of 78, network attempts 0, tracked database byte-identical |

## Real-data demonstration

Inputs: PAID (`98kfF7rm...pump`), analyzed from the committed inbox captures at their own observation time, assessed against a temporary copy of `data/backtest/bt.sqlite`.

- FAST stage:
  - state PARTIAL_WITH_LIMITATIONS, tier SCENARIO_ONLY, stress RESEARCHABLE;
  - max size $599 under a $250 loss cap and a 5% exit-impact cap;
  - 299 closed bars, 1 unfinished bar dropped;
  - no TA strategy signals.
- Cohort evidence for the lab status "SETUP DEVELOPING": 27 cases, below the 30-case floor, so reported as INSUFFICIENT_HISTORY rather than a percentile.
- Second call: cache HIT. The same analysis asked for 3 h later: STALE_DATA. Lab score, status and report unchanged.
- DEEP stage: the token is in the stored universe but had no completed TA trade before the assessment time, so INSUFFICIENT_HISTORY. Zero trades is not presented as evidence.
- Catalyst refresh with a manually supplied observation (Maxun schedules are not approved):
  - the observation requests a refresh;
  - the same origin and content again is ignored;
  - a ticker-only match, a robot outage and a stale record are each ignored.
- Benchmark: 20 FAST assessments with distinct snapshots, median 487 ms and max 571 ms on the 155 MB corpus. Most of that time is the cohort query: the same 20 runs on an empty database have a median of 8 ms and a max of 51 ms.

## Gate

Each opportunity in G01 to G04, G31 and G34 is either assessed once or explicitly abstained. Every outcome is stored as a FAST row with a state, none is dropped, and each one has a test:

- G01: same ticker on two mints gives two assessments, and a record about one never refreshes the other.
- G02: the snapshot uses the main pool's reserve, never a sum across pools.
- G03: refresh timing uses availability, never publication time.
- G04: a wallet transfer keeps its own kind and is never relabeled a sale. Selling semantics stay covered by the Phase 09 tests.
- G31: a new token gives INSUFFICIENT_HISTORY.
- G34: a blocked quote provider gives a degraded record with the provider status carried and no fabricated proceeds. No price gives SOURCE_BLOCKED (retriable).
- Other abstain states, each stored and tested: fatal flag (RISK_FATAL_FLAW), corrupted 31-byte mint (INVALID_TOKEN_ID, permanent), CLMM main pool (UNSUPPORTED_POOL) and malformed module output (ERROR, retriable).

Original scout: the scout report is byte-identical with the policy off and on, and with the policy off no backtest database is created (integration test through `cli.cmd_scout`).

## Bounded loop

Pass 1 was green, but the real-data demo exposed a stale-cache defect. The same snapshot asked for 3 h later came back from the cache as PARTIAL_WITH_LIMITATIONS, because the cache lookup ran before the staleness check. Fixed so a stale hit returns STALE_DATA with the stored state alongside it; test and M13-21 added.

The negative review added:
- new evidence rows (bars, universe) in the request key, so the cohort evidence can't go stale behind a cache hit;
- a source-outage guard on catalyst refresh;
- tests for G01 to G04, G34 and the severe-stress flag.

Pass 2: all green.

## Independent negative review

Wrong-but-plausible outputs invented and caught (23 mutations):
- enabled by default (M13-1); policy switch ignored (M13-2);
- all-zero authority read as active (M13-3);
- cache key ignores the snapshot (M13-4) or new evidence (M13-16);
- prechecks skipped (M13-5); fatal flag not an abstain (M13-6);
- unverified, stale, duplicate, outage or publication-timed catalysts trigger refreshes (M13-7, 8, 9, 17, 20);
- the hook raises (M13-10); the assessment edits the lab status (M13-11) or score (M13-23);
- unfinished bars used (M13-12); DEEP reads past the assessment time (M13-13);
- scout attaches a record when off (M13-14); abstains dropped (M13-15);
- transfer relabeled a sale (M13-18); liquidity summed across pools (M13-19);
- aged cache served (M13-21); severe stress dropped (M13-22).

## Not done here, and why

- Routing the assessment into social alerts, watchlist updates and scout report text belongs to Phase 14 (reports, CLI, alerts). Phase 13 only attaches the record and stores it.
- No robot or scheduled collector runs. Catalyst refresh was shown with a manually supplied observation. A refresh request asks for a re-analysis; it never creates a verdict.
- The DEEP stage reads only stored history (no network). New tokens outside the stored universe get INSUFFICIENT_HISTORY from it.

## Limitations

The cohort query sets the FAST stage's cost (about 0.5 s on the full corpus). Cohorts only cover lab statuses with at least 30 stored cases. Stress magnitudes are hypothetical (Phase 12).

NEXT ELIGIBLE PHASE: 14.

# PHASE 09: catalyst, wallet and social event-driven strategies

State: PASS. Date 2026-10-23. Entry gate: Phase 08 PASS at 976e747 (strategy tests 16 passed, 11/11 mutations, clean-tree run 64 passed).

## Changed files

- New: `memelab/backtest/strategies/catalyst.py` (CATALYST_VERIFIED: visible only from available_at, origins counted once, denials, mint verification, contemporaneous-proof option, price-first-attention-later guard, verified SWAP_SELL block with a fixed wallet-kind vocabulary, lab fatal flag wins; placebo shift), `memelab/backtest/sources/catalyst_bridge.py` (read-only reshaping of the lab's catalyst tables), `memelab/backtest/sources/lab_events.py` (real launch-monitor catalysts from every committed export, first value kept).
- Changed: `strategies/registry.py` (adds CATALYST_VERIFIED).
- Included because the G22 placebo and fatal-flag tests run trades: `memelab/backtest/engine.py` (gated in Phase 10).
- Tests: `tests/test_backtest_catalyst.py` (11; the two launch-record tests read the real git history of the state exports).
- Evidence: `audits/backtesting/catalyst/CATALYST_COVERAGE.md`, `p09_event_study.py`, `p09_event_study.json`; `testing/p09_mutations.json`, log. `testing/mutate.py` now passes `MEMELAB_HISTORY_REPO` (read-only) so history tests run in the temp copy.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_catalyst.py -q` | 0 | 11 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p09_mutations.json` | 0 | 11 of 11 caught |
| `python audits/backtesting/catalyst/p09_event_study.py` | 0 | 19 events, 15 failed within 72 h; placebo 18 |
| every earlier mutation set (p05, p06, p06a, p07, p08) rerun after the harness change | 0 | all caught |

## Gate

G03 (visible only from when the lab knew it; tested on synthetic records and on real launch records whose first trade preceded discovery), G04 (transfers are not sales; a sale known later does not block earlier), G19 (positive posts never turn verified selling into a buy), G20 (reposts of one origin are one origin; bridge drops syndication and commentary), G21 (attention after a run-up is late), G22 (placebo times weaken the relationship in a seeded synthetic world where the catalyst truly leads), G23 (conflicting sentiment plus verified selling: abstain). One failed and one non-failed historical catalyst identified with archived evidence (CATALYST_COVERAGE.md). Lab catalyst-table history is SOURCE_BLOCKED in this repository.

## Bounded loop

Pass 1: the launch-record test failed on a wrong epoch bound (my arithmetic); fixed to the real 15:00Z bound.
Pass 2: mutation M09-3 survived because the mutation used a wallet kind the code never sees; the vocabulary is now fixed in code (WALLET_KINDS) and the mutation uses it. Caught.
Pass 3 (harness safety): to give the temp copy access to git history I first passed GIT_DIR, which redirected a Phase 06 test's history read to the real repository (that test then failed; its own git calls use a clean environment, and the reflog, branches and status show nothing was written). Replaced with a read-only `MEMELAB_HISTORY_REPO` path; all mutation sets rerun clean.
Negative control (falsely historic catalyst): a launch whose claimed first trade precedes the lab's discovery is invisible at the claimed time.

## Independent negative review

Caught: claimed publication time used as known-at (M09-1), reposts as independent sources (M09-2), transfers as sales (M09-3), late attention as prescient (M09-4), denial ignored (M09-5), ticker-only link (M09-6), placebo that does not move (M09-7), catalyst over a fatal flag (M09-8), commentary counted as origin (M09-9), launch record overwritten by later exports (M09-10), catalyst usable before the token link (M09-11).

## Limitations

The real catalyst sample is one week of launch records; the event study is descriptive. Wallet transactions lack capture times, so they are not used as historical signals. No social-post history exists before the lab's own collectors; nothing was backfilled by crawling.

NEXT ELIGIBLE PHASE: 10.

# Backtesting and stress testing: handoff

Rewritten at the end of every phase. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Package: [workplans/backtesting/](../../workplans/backtesting/).

## Position

- Phase completed: 06A (Maxun bake-off and decision), 2026-10-23. State: PASS, decision EXISTING_TOOL_WINS, Maxun NOT_ADOPTED. Note: audits/backtesting/PHASE_06A.md. Phases 00-06 PASS.
- Baseline SHA f99c6c7. Phase 06 commit f6641ce. Branch `feature/backtesting`. Corpus: data/backtest/bt.sqlite (gitignored), dataset hash 3d8dfd1e6dfa... over 261 mints.
- Spend so far: Firecrawl about 29 of ~100 calls; Maxun 5 of 5 trial credits (0 left, 0 schedules); Crawl4AI local only.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python audits/backtesting/testing/p00_counterexamples.py` (entry gate) | 0 | 3 of 3 |
| GeckoTerminal probe (12 seeded mints, saved in data/p01_gt_probe.json) | n/a | 7 of 12 answered, 5 hit 429 at 2.2 s pacing |
| git-history union of theses (testing/logs/p01_negative_review.log) | 0 | 1,801 distinct theses vs 701 in latest export |
| 30 GitHub API repo searches (research/raw/p02_github_search.txt) | n/a | 273 hits, 268 unique; longlist 73, shortlist 25 |
| 25 pinned-commit reviews + blind rescore | n/a | none >= 70; top: slotfish 65.10; largest blind gap 7.1 |
| `python3 audits/backtesting/bakeoff/compare.py` | 0 | 16/16 |
| `python -m pytest tests -q` after Phase 05 | 1 | 1 failed (C-1 only), 800 passed |
| `python tools/release_audit.py` / `release_e2e.py` after Phase 05 | 0 / 0 | Needs action: no / PASS 78 of 78 |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p05_mutations.json` | 0 | 7/7 caught |
| Phase 06 tests (sources, real fixture) | 0 | 17 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p06_mutations.json` | 0 | 12/12 caught |
| `python -m pytest tests -q` after Phase 06 | 1 | 1 failed (C-1 only), 870 passed |
| Phase 06A: `pytest tests/test_backtest_webcapture.py` / `mutate.py p06a_mutations.json` | 0 / 0 | 20 passed / 9 of 9 caught |

## Proven

Seam verified; data feasibility mapped; rubric locked; exact historical execution confirmed BLOCKED; GeckoTerminal serves bars for dead pools; pacing must be slower than 2.2 s per call.

## Limitations

Universe spans 17 days. Catalyst history thin. Helius key absent in this workspace. Historical swaps, reserves, ticks, bins, holders and wallet flows are SOURCE_BLOCKED. Two corrupted mint strings in the lab's exports (GAPS C4).

## Next eligible phase

07 (execution-aware AMM simulation and capacity). Code drafted ahead of its gate: `memelab/backtest/execution.py` and `tests/test_backtest_execution.py`, not yet committed or gated.

## Roadmap changes

None.

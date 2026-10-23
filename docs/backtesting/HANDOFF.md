# Backtesting and stress testing: handoff

Rewritten at the end of every phase. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Package: [workplans/backtesting/](../../workplans/backtesting/).

## Position

- Phase completed: 12 (stress engine), 2026-10-23. State: PASS. Note: audits/backtesting/PHASE_12.md. Phases 00-11 PASS (06A EXISTING_TOOL_WINS; 11 all INSUFFICIENT_SAMPLE).
- Baseline SHA f99c6c7. Phase 06 f6641ce, Phase 06A db91542, Phase 07 e18c12f, Phase 08 976e747, Phase 09 58abf7d, Phase 10 941e4ed, Phase 11 38d2fcc. Branch `feature/backtesting`. Corpus: data/backtest/bt.sqlite (gitignored), dataset hash 3d8dfd1e6dfa... over 261 mints.
- Spend so far: Firecrawl about 29 of ~100 calls; Maxun 5 of 5 trial credits (0 left, 0 schedules); Crawl4AI local only; Solana public RPC and Jupiter quotes read-only (about 20 calls).

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
| full suite on the clean 06A commit / `release_e2e.py` | 1 / 0 | 1 failed (C-1), 837 passed / PASS 78 of 78 |
| Phase 07: `pytest tests/test_backtest_execution.py` / `mutate.py p07_mutations.json` | 0 / 0 | 15 passed / 14 of 14 caught |
| Phase 08: `pytest tests/test_backtest_strategies.py` / `mutate.py p08_mutations.json` | 0 / 0 | 16 passed / 11 of 11 caught |
| Phase 09: `pytest tests/test_backtest_catalyst.py` / `mutate.py p09_mutations.json` | 0 / 0 | 11 passed / 11 of 11 caught |
| Phase 10: engine and runner tests / `mutate.py p10_mutations.json` | 0 / 0 | 22 passed / 14 of 14 caught |
| full suite after Phase 10 / release audit / release e2e | 1 / 0 / 0 | C-1 only, 915 passed / Needs action: no / PASS 78 of 78 |
| Phase 11: validation tests / `mutate.py p11_mutations.json` / `p11_validate.py` | 0 / 0 / 0 | 13 passed / 11 of 11 / all INSUFFICIENT_SAMPLE |
| Phase 12: stress tests / `mutate.py p12_mutations.json` / `p12_scenarios.py` | 0 / 0 / 0 | 13 passed / 12 of 12 / 2 real pools RESEARCHABLE |

## Proven

Seam verified; data feasibility mapped; rubric locked; exact historical execution confirmed BLOCKED; GeckoTerminal serves bars for dead pools; pacing must be slower than 2.2 s per call.

## Limitations

Universe spans 17 days. Catalyst history thin. Helius key absent in this workspace. Historical swaps, reserves, ticks, bins, holders and wallet flows are SOURCE_BLOCKED. Two corrupted mint strings in the lab's exports (GAPS C4).

## Next eligible phase

13 (per-opportunity integration). Drafted ahead of its gate: `memelab/backtest/assess.py` (FAST stage, idempotent request key, off by default). To do: hook in `cli.cmd_scout`/`cmd_analyze` behind the policy, tests that reports are byte-identical when off.

## Roadmap changes

None.

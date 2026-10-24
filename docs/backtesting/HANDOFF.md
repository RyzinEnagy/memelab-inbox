# Backtesting and stress testing: handoff

Rewritten at the end of every phase. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Package: [workplans/backtesting/](../../workplans/backtesting/).

## Position

- Phase completed: 16 (independent adversarial E2E audit), 2026-10-23. State: PASS for scenario-only research mode with disclosed limitations (strict reading FAILED; G16 and G27 await Elving's acceptance). Note: audits/backtesting/PHASE_16.md. Phases 00-15 PASS.
- Baseline SHA f99c6c7. Phase 06 f6641ce, Phase 06A db91542, Phase 07 e18c12f, Phase 08 976e747, Phase 09 58abf7d, Phase 10 941e4ed, Phase 11 38d2fcc, Phase 12 999d1eb, Phase 13 4338810, Phase 14 30863a6, Phase 15 41488ad, Phase 16 repair passes 47a7845, 0e63563, c42045b, 7c7b582. Branch `feature/backtesting`. Corpus: data/backtest/bt.sqlite (gitignored), dataset hash 3d8dfd1e6dfa... over 261 mints.
- Spend so far: Firecrawl about 31 of ~100 calls; Maxun 5 of 5 trial credits (0 left, 0 schedules); Crawl4AI local only; Solana public RPC and Jupiter quotes read-only (about 20 calls).

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
| Phase 13: assess tests / `mutate.py p13_mutations.json` / `integration/p13_demo.py` | 0 / 0 / 0 | 26 passed / 23 of 23 / real PAID: PARTIAL_WITH_LIMITATIONS, SCENARIO_ONLY, cache HIT, STALE_DATA after 3 h |
| full suite after Phase 13 / release audit / release e2e | 1 / 0 / 0 | C-1 only, 952 passed / Needs action: no / PASS 78 of 78 |
| Phase 14: report and assess tests / `mutate.py p14_mutations.json` / `p13_mutations.json` rerun / `reports/p14_samples.py` | 0 / 0 / 0 / 0 | 49 passed / 20 of 20 / 24 of 24 / 6 schema-valid reports |
| full suite after Phase 14 / release audit / release e2e | 1 / 0 / 0 | C-1 only, 976 passed / Needs action: no / PASS 78 of 78 |
| Phase 15: outcome tests / `mutate.py p15_mutations.json` / `outcomes/p15_outcomes.py` | 0 / 0 / 0 | 14 passed / 22 of 22 / 1,023 opportunities, 24 h: 385 complete, 133 censored, 463 not observable |
| full suite after Phase 15 / release audit / release e2e | 1 / 0 / 0 | C-1 only, 990 passed / Needs action: no / PASS 78 of 78 |
| Phase 16: independent reviewer, 5 passes (E2E_RESULTS.md) / every mutation set / full suite / release audit / release e2e | - / 0 / 1 / 0 / 0 | PASS for scenario-only mode / all caught / C-1 only, 1024 passed / Needs action: no / PASS 78 of 78 |

## Proven

Seam verified; data feasibility mapped; rubric locked; exact historical execution confirmed BLOCKED; GeckoTerminal serves bars for dead pools; pacing must be slower than 2.2 s per call.

## Limitations

Universe spans 17 days. Catalyst history thin. Helius key absent in this workspace. Historical swaps, reserves, ticks, bins, holders and wallet flows are SOURCE_BLOCKED. Two corrupted mint strings in the lab's exports (GAPS C4).

## Next eligible phase

17 (release memo and runbook): RELEASE_REPORT.md, RUNBOOK.md, LICENSE_ATTRIBUTIONS.md, clean-clone reproduction, push feature/backtesting (fast-forward, no merge), git bundle and zip to D:\memelab.

## Roadmap changes

None.

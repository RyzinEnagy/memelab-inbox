# Backtesting and stress testing: handoff

Rewritten at the end of every phase. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Package: [workplans/backtesting/](../../workplans/backtesting/).

## Position

- Phase completed: 17 (release hardening), 2026-10-23. State: PASS, decision CONDITIONAL RELEASE, scenario-only research mode (docs/backtesting/RELEASE_REPORT.md), accepted by Elving on 2026-10-24 (D-BT-033). Note: audits/backtesting/PHASE_17.md. Phases 00-16 PASS (16 for scenario-only mode; strict reading FAILED; G16 and G27 await Elving's acceptance).
- Baseline SHA f99c6c7. Phase 06 f6641ce, Phase 06A db91542, Phase 07 e18c12f, Phase 08 976e747, Phase 09 58abf7d, Phase 10 941e4ed, Phase 11 38d2fcc, Phase 12 999d1eb, Phase 13 4338810, Phase 14 30863a6, Phase 15 41488ad, Phase 16 repair passes 47a7845, 0e63563, c42045b, 7c7b582, record f50b24d; Phase 17 ddc0794, fcb676a, b5039be, 52c605d, 03fd506, bc7ce30, d18a07a (re-check residual fixes), 7967550 (final clean-install log). Branch `feature/backtesting`. Corpus: data/backtest/bt.sqlite (gitignored), dataset hash 3d8dfd1e6dfa... over 261 mints.
- After the release (2026-10-25): forward depth collector (D-BT-034), Elving's approval of predictive PI-D-020 (now PI-D-044), folded into the hourly tracker as the step `collect`. Local branch `work/backtesting-collector` from feature/backtesting at 054a619, not pushed. Code commit 50565ad, records in the commit that follows it. Record: audits/backtesting/collector/COLLECTOR.md; reviewer packet: audits/backtesting/collector/SKEPTIC_PACKET.md.
- Spend so far: Firecrawl about 32 of ~100 calls; Maxun 5 of 5 trial credits (0 left, 0 schedules); Crawl4AI local only; Solana public RPC and Jupiter quotes read-only (about 20 calls). Collector work on 2026-10-25: GeckoTerminal 11 calls, Jupiter keyless quotes 14, GitHub 4 (ls-remote and shallow fetches), Firecrawl 1 search.

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
| Phase 17: clean install / every builder mutation set / full suite / release audit / release e2e | 0 / 0 / 1 / 0 / 0 | 9 steps PASS / 221 of 221 / C-1 only, 1029 passed / Needs action: no / PASS 78 of 78 |
| Phase 17 after the reviewer's re-check (AGREED) and the R3 to R5 fixes, at 7967550 | 0 / 0 / 1 / 0 / 0 | clean install PASS at d18a07a, checker 72 of 72 / 222 of 222 / C-1 only, 1030 passed / Needs action: no / PASS 78 of 78 |
| Collector (D-BT-034): `pytest tests/test_backtest_depth.py` / `mutate.py collector_mutations.json` / full suite / release audit / release e2e at 50565ad | 0 / 0 / 1 / 0 / 0 | 13 passed / 18 of 18 caught / C-1 only, 1043 passed / Needs action: no / PASS 78 of 78 |
| Collector live smoke 2026-10-25 13:22Z (`backtest depth collect --max-gt-calls 4 --max-quote-calls 6`) | 0 | 19 decisions from export e245d91, 19 pool snapshots OK, 6 quotes OK, 42.2 s |
| hourly_shadow.sh five steps in a scratch HOME, network blocked after setup (testing/logs/c01_hourly_script_e2e.log) | 0 each | collect EXPORTS_NOT_FETCHED and SOURCE_BLOCKED rows, save OK; forced collect failure left the stored file unchanged |

## Proven

Seam verified; data feasibility mapped; rubric locked; exact historical execution confirmed BLOCKED; GeckoTerminal serves bars for dead pools; pacing must be slower than 2.2 s per call.

## Limitations

Universe spans 17 days. Catalyst history thin. Helius key absent in this workspace. Historical swaps, reserves, ticks, bins, holders and wallet flows are SOURCE_BLOCKED. Two corrupted mint strings in the lab's exports (GAPS C4).

## Next eligible phase

None in the package. Elving's decisions on 2026-10-24 (D-BT-033), all yes:
- G16 and G27 accepted; the CONDITIONAL RELEASE accepted.
- Pull request #4 opened from feature/backtesting into feature/catalyst-firecrawl (the branch it was built on, not yet in main). Review only; not merged.
- Maxun evaluation robot deleted (bakeoff/p06a_maxun/robot_delete.json); no Maxun schedules remain.
- Hourly shadow tracking approved. The store is on his computer in D:\memelab\backtesting_live and a test run passed (RUNBOOK.md, "Shadow-mode calibration"). This is now the only lasting copy of the research database; the cloud workspace copy is temporary. The scheduled task itself still has to be created: the permission check in this session refused it.

Forward depth collector (D-BT-034, 2026-10-25): built and tested in this workspace, not deployed. The hourly run gains the step `collect` between refresh and track. The scheduled task prompt now has five steps and lives in RUNBOOK.md ("Scheduled task prompt"); it replaces the four-step prompt that was here (git history at 054a619). Deployment steps: RUNBOOK.md, "Deployment to Elving's computer".

Still open:
- Bring the collector commits onto feature/backtesting (fast-forward from 054a619) and push, under the D-BT-003 push route, if Elving wants them there; until then they exist only on the local branch work/backtesting-collector.
- Deploy to D:\memelab\backtesting_live (new code.bundle and hourly_shadow.sh, one run by hand) and create the scheduled task with the five-step prompt; the earlier permission check refused creating it.
- The refresh step still paces GeckoTerminal at 3 s (up to 20 a minute in its burst); only collect keeps to 6 a minute. Changing refresh to `--spacing 10 --max-calls 8` would bring the whole run to 6 a minute at the cost of fewer refreshed pools per hour. Elving's call.
- Quotes exist only for Solana; BSC, Base and Ethereum get reserves only. The 40-quote cap leaves some Solana pools without a quote in some hours on a busy day.
- Decide when to merge pull request #4.

## Delivery

Authorized by Elving at the start of this work (the "Both" answer): push a new feature/backtesting branch, fast-forward only, no force, no merge, no pull request, main untouched; and a git bundle plus a zip in D:\memelab. Push record, 2026-10-24 02:55 UTC:
- feature/backtesting created on GitHub at 538de7d (all 34 commits from f99c6c7). This commit followed as a fast-forward. No force, no merge, no pull request.
- Checked after the push: main still at 98338a8 and feature/catalyst-firecrawl still at f99c6c7.
- Route: a plain `git push` of the new branch through this session's GitHub connection (Elving's account), not the Composio Git Data API. The Composio route would have meant passing about 660 KB of compressed objects through tool calls by hand, which is error-prone; the result on GitHub is the same commits with the same ids.
- Before the push, the full history and the zip were searched on Elving's computer for the Crawl4AI and Maxun credentials: neither appears.

Pull request #4 (feature/backtesting into feature/catalyst-firecrawl) opened 2026-10-24 on Elving's approval; not merged.

Bundle and zip in D:\memelab: memelab-inbox_feature-backtesting.bundle (full history of feature/backtesting plus the base ref; `git clone -b feature/backtesting <bundle>`) and memelab-inbox_feature-backtesting.zip (tracked files at the branch tip, gitignored data excluded).

## Roadmap changes

None.

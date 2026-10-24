# START HERE — Memecoin Backtesting & Opportunity Stress-Testing Engine

**Version:** 1.2 | **Package authored:** 2026-10-23 | **Status:** EXECUTION PROMPTS, NOT AN IMPLEMENTED ENGINE.

## Goal

Enhance the existing **Memecoin Investing Lab** repository with reliable, point-in-time backtesting and opportunity-level stress tests. Whenever the existing system discovers or materially updates an opportunity, the enhancement must **attempt** to attach a historically validated strategy assessment, a position-size-specific executable-cost estimate, and an adverse scenario stress test. If data is unavailable, it must **abstain honestly**: `INSUFFICIENT_HISTORY`, `INSUFFICIENT_EXECUTION_DATA`, `UNSUPPORTED_POOL`, `STALE_DATA`, `UNVERIFIED_CATALYST`, or other specific non-PASS states—never simulate certainty.

**Target repository**: https://github.com/RyzinEnagy/memelab-inbox

**Important:** The public repository describes itself as research-only: it does not place trades or handle private keys. Preserve that boundary. The README currently mentions a Python `memelab` package, `modules/m01..m28`, `pipeline.py`, `normalize.py`, `db.py`, `report.py`, `cli.py`, browser-bridge collection and a `tests` suite. These are **navigation leads, not an audit**. Phase 00 must inspect actual source and actual commit history first. If the real executable project is elsewhere, find it and document the relationship—do not modify a public inbox-only mirror on assumptions.

## How to run

1. Give your AI coding agent access to the *actual repository checkout* and the Internet/GitHub research tools. Use a working branch; do not mutate or push to the protected branch.
2. Copy this package into a separate project task directory (e.g., `workplans/backtesting/`) without replacing any existing project handoff files.
3. Read `EXECUTION_RULES.md`, `references/RESEARCH_PROTOCOL.md`, `references/GRADING_RUBRIC.md`, `references/ACCEPTANCE_SCENARIOS.md`, `references/WEB_RESEARCH_TOOLING.md`, and `references/MAXUN_ROBOT_CONTRACT.md`.
4. Run `phases/PHASE_00_....md` in a session with real file/command access. Proceed only after its gate is proven.
5. For discrete sessions, give the agent exactly **one phase file**. An optional guarded `ORCHESTRATOR.md` supports automatic **phase selection**, not bypassing gates or silently approving cost, licensing or migration decisions.
6. Keep evidence and decisions under a namespaced repo path proposed and verified in Phase 00 (suggested `audits/backtesting/` and `docs/backtesting/`). Reuse existing `EXECUTION.md`, `ROADMAP.md`, `DECISIONS.md`, and `HANDOFF.md` if these exist; otherwise create **backtesting-namespaced** equivalents. Never overwrite unrelated prior-project state.

## Optional web-research accelerators (explicitly wired)

The user reports that **Firecrawl and Crawl4AI are installed**, with a potential Crawl4AI-related token stored locally at `D:\memelab\crawl4ai-token.txt`. Phase 00 must discover whether these are actually available as Claude tools, runnable local processes, or hosted services; verify token-file **existence without printing its contents**. Phases 02–03, 06 and 09 use a bounded, auditable collection plan where appropriate. GitHub API and pinned source clones remain primary proof for repo rankings. See `references/WEB_RESEARCH_TOOLING.md` for task assignment, credential handling, provenance, costs, and fallback rules.

**Maxun robot track (new in v1.2):** `getmaxun/maxun` is an additional **conditional persistent web-robot** candidate, not a backtesting framework and not assumed installed. Phase 00 audits availability; Phases 01/04 compare architecture, license and cost; **Phase 06A** runs a comparative bake-off and either implements an approved real robot-to-existing-ingestion path or documents a measurable no-go. The old GitHub backtesting top-ten rubric/rank remains separate. See `references/MAXUN_ROBOT_CONTRACT.md`. Scheduled recurring work requires explicit approval.


## 19 execution phases (00–17, including intermediate Phase 06A)

| Phase | Outcome | Evidence to pass |
|---|---|---|
| 00 | Current-repo baseline | Commit hash, runtime architecture trace, real tests |
| 01 | Gap analysis and placement | Existing vs required capability matrix, architecture decision |
| 02 | GitHub discovery | Reproducible search of >=40 unique candidates |
| 03 | Deep comparison and top ten | >=20 source-code reviews, scored and evidence-backed top 10 |
| 04 | Dependency/adaptation bake-off | Isolated proof-of-concepts, licensing and adoption decisions |
| 05 | Point-in-time data model | Schema/migrations, temporal-leakage proof |
| 06 | Historical data quality pipeline | Real data provenance + synthetic fixture tests |
| 06A | Maxun robot feasibility / conditional integration | Empirical bake-off, lawful robot proof or documented no-go/fallback |
| 07 | Executable AMM/DEX cost modeling | Independent fill/fee/quote invariants |
| 08 | Technical-analysis signals | Reproducible point-in-time signal library |
| 09 | Catalyst/social/on-chain signals | Strict known-at event and falsification tests |
| 10 | Backtest & portfolio replay | Deterministic trades, cash, exposure and P&L |
| 11 | Scientific validation | Walk-forward, holdout, baselines, uncertainty |
| 12 | Opportunity stress scenarios | Liquidity drain, rug, fee, tax, latency and gap scenarios |
| 13 | Discovery-to-backtest orchestration | Every eligible discovered opportunity is assessed/abstains |
| 14 | Reports, alerts and interface | Decision-oriented report and API/CLI integration |
| 15 | Outcome measurement & calibration | Research forecasts linked to subsequent actual outcomes |
| 16 | Independent adversarial E2E audit | Fault injection, historical replay, clean regressions |
| 17 | Release and runbook | Fresh-clone demonstration, configuration and honest signoff |

**Default behavior:** stop after each phase. The *caller* may explicitly run the guarded orchestrator, which launches each phase only after verifying its evidence; it is not allowed to redefine a failed gate as passed.

**Phase order:** 00 → 01 → 02 → 03 → 04 → 05 → 06 → **06A** → 07 → 08 → … → 17. The orchestrator must not sort `06A` incorrectly or skip its gate.

## Nonnegotiables

- Chain + **exact token mint**, not ticker; distinguish pools/venues.
- No future information: `event_time`, `observed_at`, `available_at`, `decision_time`, `execution_time` are different concepts.
- Include dead/delisted/rugged tokens in the historical universe to combat survivorship bias.
- Use historic liquidity/reserves for historic simulation. **Today's Jupiter quote is NOT historical liquidity.**
- Real quotes for current trade sizes are a separate present-tense scenario input.
- A candle close is not guaranteed execution at that close, and an intrabar stop is not guaranteed to fill at its trigger.
- An ordinary OHLCV engine is not a concentrated-liquidity / DLMM simulator.
- Backtesting the strategy on historical cohorts does not guarantee this token's next move.
- Historical samples and data coverage are stated explicitly, including confidence/uncertainty.
- Source code licenses and dependencies checked **before** copying or vendoring.
- No wallet keys, live orders, irreversible chain operations or auto-trading.
- No public repo push, paid API enrollment or major destructive schema migration without authorization.
- Prefer a modular adapter / library integration to absorbing an entire trading bot.

## End-state acceptance example

When a Solana mint is found in the existing `discover`/`scout` path, the generated opportunity report carries these sections:

1. **Identified asset and as-of timestamp.** Exact mint, chain, pool venues, observation quality.
2. **Signal and catalyst provenance.** What was known when; observations vs inference.
3. **Relevant backtest.** Named rule, eligible historic cohort, timeframe, training vs sealed test, fees/impact, trade count, baselines, uncertainty.
4. **Position-size-specific execution test.** Entry and exit prices, estimated proceeds, unavailable routes, capacity limits, quote freshness.
5. **Adversarial stress scenarios.** Selling by concentrated wallets, fee changes, vanishing depth, adverse gaps, stale attention, failed confirmations, social manipulation.
6. **Conclusion with conditions.** Setup quality vs entry quality, invalidation, risk budget and practical realizability; abstain where data is insufficient.
7. **Reproducibility.** Run ID, Git SHA, strategy config, dataset hash/cutoff, raw event references, engine version, notes on omissions.

## User-supplied methodological grounding

This package follows the *Sequential AI Prompt Engineering Method*: audit first, dependency-order vertical slices, one objective per phase, observable gates, durable handoff files, honest blockers, and final independent integration audit. Its supporting teaching material emphasizes executable liquidity over displayed valuation and evidence over wallet-attribution speculation. Those are design principles here—not evidence that historical data, backtests or integrations already exist.

## Research scope

The **top ten** are determined in Phase 03, **not preselected by popularity**. Read `references/CANDIDATE_SEEDS.md` for unranked leads. If fewer than ten viable repos survive hard gates, output the ten highest-scoring *researched* candidates with clear `INELIGIBLE` labels and state why fewer than ten were deployable—never fabricate a clean top ten.

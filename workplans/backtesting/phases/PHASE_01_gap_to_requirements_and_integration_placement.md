# PHASE 01 — Gap-to-requirements and integration placement

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 01.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 00 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Gap-to-requirements and integration placement. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Using phase 00 evidence, compare actual feature coverage against `REQUIRED_DATA_CONTRACTS.md` and G01–G35. Record `EXISTS_TESTED / EXISTS_UNTESTED / PARTIAL / MISSING / BLOCKED`, with path/line and upstream/downstream impact.
- Identify *where* opportunity assessment hooks should live: candidate creation, full analysis, rating/reporting, alerts, after-the-fact calibration. Trace strongest actual seam, e.g. `memelab.pipeline`, `report`, `db`, `cli`, but verify rather than impose new paths. Decide synchronous quick stress vs queued/deferred deep assessment based on latency and source access.
- Write a concrete system spec for TA signals, catalyst chronology, analog historical cohorts, execution simulator, replay, stress, uncertainty, reporting, and operator controls. Draw a sequence diagram and dependency graph.
- Map available vs needed historical OHLCV, trade swaps, pool reserves/ticks/bins, wallet funding/activity, LP state, DEX routing, narratives, original timestamp, source observed timestamp, retroactive edits and real-time data. Define evidence tiers with abstention.
- Decide adapters/API/SQLite migration/feature flags and branch isolation; preserve existing fatal-flaw and 100-point scoring. Lock research rubric weights before assessing candidates. Define reasonable per-run resource/time budgets on actual environment.

## Relevant installed web crawlers

Read `references/WEB_RESEARCH_TOOLING.md` and apply the corresponding phase mapping.

- Decide specific approved Firecrawl/Crawl4AI public research use cases and domain/rate/retention budgets, and identify overlap with the existing social/trader intelligence collectors. Explicitly avoid adding a competing ingestion pipeline or using newly scraped pages as past known-at evidence.

## Maxun robot research and integration checkpoint

- **Maxun placement:** chart proposed persistent robot → canonical source registry → verified catalyst → as-of strategy → candidate report. Compare against current social/trader ingestion; specify exactly where a thin adapter would plug in, what is already collected, whether ongoing robot monitoring is worth maintenance, and user authorization needed for new service/schedules. Keep Maxun outside top-ten engine ranking.

## Required evidence / acceptance gate

`GAPS.md`, `REQUIREMENTS_MATRIX.md`, `ARCHITECTURE_DECISION.md`, architecture diagram, ranked data feasibility/expense matrix, contract acceptance mappings, baseline-preserving migration policy. **Gate:** every required downstream function has a real integration seam and data-source feasibility status; no code-first arbitrary framework selection.

## Independent negative review

Before PASS, actively invent a concrete wrong-but-plausible output (future knowledge, thin exit, misleading repo claim, fee double-count, undocumented dependency, or failure mode relevant to this phase). Prove a test or source-code finding **catches** it. Check upstream and downstream assumptions; attach the counterexample and commands. If a source is unavailable, explicitly record what remains unverified and whether later phases may proceed using *test-only* artifacts with that limitation.

## Repair and verification loop — mandatory

Apply `EXECUTION_RULES.md` bounded loop: **inspect → implement/research → run positive/negative/regression tests → adversarial review → repair → rerun → gate**, maximum five full passes. Keep per-pass test outputs, counts, exit codes, time, SHA and exact changes. Do not call PASS with a skipped key test or mutate acceptance criteria to get green. If blocked or still red after pass five, mark FAILED/BLOCKED/NEEDS_REVIEW with next action.


## Absolute exclusions

- Do not run the next phase in this execution context; do not conflate phase completion with task completion.
- Do not introduce a wallet/private key/live order, auto-trading bot, secret, external paid bill or new deployment.
- Do not rewrite unrelated social, scoring, CLI or original data logic; integrate only behind safe, tested interfaces.
- Do not call a fixture a real backtest or let historical lookahead/optimistic liquidity silently pass.

## Durable handoff and STOP

Write/update the discovered authoritative `EXECUTION`, `ROADMAP`, `DECISIONS` and `HANDOFF` files without overwriting unrelated project state. Include accepted evidence paths, SHA, source timestamps, test commands/exits, what was and wasn't proven, remaining limitations, and the next eligible phase. Local commits only with authorization; never push automatically.

**STOP after phase 01.** Return exact `PHASE 01 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 02 without a new orchestration call.

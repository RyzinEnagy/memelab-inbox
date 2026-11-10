# PHASE 13 — Integrate per-opportunity automated evaluation

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 13.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 12 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Integrate per-opportunity automated evaluation. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Wire a controlled evaluation hook into the verified real pipeline so every **eligible discovered or materially updated** mint causes one idempotent `stress_assessment_request` keyed by mint + opportunity snapshot + engine version; preserve existing scout/scoring/report outputs if module off.
- Use fast available-data stage (present liquidity risk + applicable historic strategy evidence) and optional bounded deep stage; never block ordinary discovery indefinitely on historical-source outage. Cache matching strategy/cohort runs and recompute when relevant price/depth/wallet/catalyst/strategy/data inputs change.
- Distinguish token-specific backtest vs analog cohort vs scenario-only vs insufficient evidence; route fail-closed statuses through CLI, scheduled research, social alerts, watchlist updates and persistence without implying trade execution.
- Preserve token identity by mint, fatal flaw veto, existing 100-point score interpretation and existing research-only rules. If severe stress merits a new cap/flag rather than reweighting score, document this choice with tests.
- Add observability: request count, attempted/completed/abstained, reasons, wall-time, output records, retriable vs permanent failure; deduplicate input to prevent rerun storms.

## Maxun robot research and integration checkpoint

- **Robot-triggered refresh:** when an authorized Maxun-derived or fallback verified catalyst observation arrives, update only the affected `{chain, exact_mint}` opportunity via existing source registry/event mechanisms and rerun the bounded stress/backtest analysis. Guard against repeated cross-source duplicates, false ticker-only matches, stale events, and a robot outage causing a false bullish verdict. If schedules are unapproved, demonstrate with an explicit manually supplied observation.

## Required evidence / acceptance gate

Instrumented opportunity → assessment flow with feature flag, retry rules, integration tests, benchmark, failure fallback and audit log. **Gate:** every synthetic G01–G04 and G31/G34 opportunity is assessed once or explicitly abstained, no dropped/disguised candidates; original scout still works.

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

**STOP after phase 13.** Return exact `PHASE 13 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 14 without a new orchestration call.

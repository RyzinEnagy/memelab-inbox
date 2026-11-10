# PHASE 07 — Execution-aware DEX/AMM simulation and capacity

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 07.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 06A accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Execution-aware DEX/AMM simulation and capacity. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Implement pluggable execution models: (a) exact independently verified CPMM swap equations using actual token/quote reserve units and fees, (b) CLMM/DLMM bin/tick simulation only if authentic historic state and audited math are available, (c) explicit conservative estimate/`UNSUPPORTED_POOL` otherwise. No false universal x*y=k assumption.
- Handle buy and sell asymmetry, position-size sweeps, multi-pool route decisions without double counting, partial/failed legs, latency, block/transaction failure, market drift, liquidity disappearance, swap/token transfer fees incl. Token-2022, decimals, authority changes, SOL fees, price oracle currency conversion and quote expiry. Mark modeled vs directly observed.
- Historical model uses **historical** reserves/ticks/trades. Live Jupiter-like quotes measure **current** executable depth and may be attached only with quote time, validity and route. No substitution of live quotes for historic fills.
- Compare against independent hand math and three spot-checks when live quotes available, but don't claim every router path reproduced. Persist fees and realized proceeds rather than screen-value exits.
- Produce `max position` given impact/risk budgets, and scenario where take-profit marking exceeds actual cash-out. Out-of-scope live orders.

## Required evidence / acceptance gate

Versioned execution adapter, unit/round-trip ledger, sizing curves, error states, comparison worksheet and evidence. **Gate:** G09–G17 and G29 pass; no impossible fills, negative reserves or unmodeled route stated as accurate.

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

**STOP after phase 07.** Return exact `PHASE 07 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 08 without a new orchestration call.

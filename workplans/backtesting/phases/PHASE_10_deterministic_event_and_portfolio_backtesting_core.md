# PHASE 10 — Deterministic event and portfolio backtesting core

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 10.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 09 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Deterministic event and portfolio backtesting core. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Implement end-to-end replay: immutable as-of events → technical/catalyst strategy → decision → execution simulator → position/account ledger → marked value versus **realizable** value → exits/stop gaps → outcomes. Reuse chosen dependency from Phase 04, and independently validate ledger math.
- Model simultaneous candidate competition, per-trade risk, capital and liquidity limits, correlated tokens/creator wallets, dynamic exposure, max loss, maximum entries, stale exit quotes and account denominators. Backtest is research only and must not call live trading code.
- Include order life cycle (submitted, partially filled, failed, canceled, expired), fee/cost attribution, recovery on timeout/restart, next eligible fill and non-executable stop conditions.
- Save deterministic run metadata, trade journal and per-opportunity results. Test same seed/dataset SHA producing same normalized ledger. Include adequate baselines under same execution assumptions.
- Build CLI/API research runner based on **actual** existing service architecture (not a bolted-on separate system); no final production report integration yet.

## Required evidence / acceptance gate

Executable backtest runner, reproducible ledger, portfolio constraint tests and test oracle reconciliation. **Gate:** G24–G25, G28–G29 pass plus existing analyze/scout regression; no silent negative cash or profit from phantom fills.

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

**STOP after phase 10.** Return exact `PHASE 10 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 11 without a new orchestration call.

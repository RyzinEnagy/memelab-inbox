# PHASE 08 — Point-in-time technical-analysis strategy library

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 08.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 07 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Point-in-time technical-analysis strategy library. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Inspect Lab's existing structure technical metrics and reuse signal logic where valid. Formalize reproducible, fully parameterized strategies for support/resistance, trend HH/HL and LH/LL, breakout confirmation, false breakout/reclaim, retest, volume regime, absorption after sell-pressure contraction, momentum/exhaustion and liquidity-aware entry filters.
- Specify each signal exactly: required bars, smoothing windows, data-validity boundaries, decision time, executable next time, mechanical entry, invalidation, exit, stop behavior, cooldown, sample inclusion, no action on stale data.
- Prevent repainting future pivots, end-of-bar lookahead, selecting only surviving tokens and nonlinear chart interpretations that can't be mechanically replayed. Reject discretionary post-hoc lines unless timestamped contemporary observations exist.
- Add strategy registry and configs with separate signal logic from price feature calculation and execution. Test malformed periods, missing candles, sparse launches, alternate price routes and two tokens with the same symbol.
- Write meaningful naive and no-signal baselines and feature-level unit tests so optimization cannot be hidden inside technical indicators.

## Required evidence / acceptance gate

`docs/backtesting/STRATEGY_LIBRARY.md`, strategy code/configs and chronological case proofs with charts only as supplemental evidence. **Gate:** G05, G18, G19 and G31 pass; signal timestamp invariant enforced by code.

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

**STOP after phase 08.** Return exact `PHASE 08 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 09 without a new orchestration call.

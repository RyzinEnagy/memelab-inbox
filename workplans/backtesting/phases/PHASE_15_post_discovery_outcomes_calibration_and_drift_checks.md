# PHASE 15 — Post-discovery outcomes, calibration and drift checks

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 15.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 14 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Post-discovery outcomes, calibration and drift checks. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Link frozen historical opportunity assessments to subsequent actual price/depth/holder/catalyst outcomes at fixed, prespecified windows. Event-time cutoffs are immutable: later outcome must never flow back to historical decision state.
- Reconcile intended vs simulated vs actual executable exits where historical pool state permits, record censored/not observable outcomes rather than dropping failed tokens, and assess slippage model forecast errors and data provider coverage drift.
- Segment calibration by cohort, token age, liquidity band, market regime, catalyst type, source credibility and position size. Distinguish sample insufficiency and historical correlation from causality.
- Add drift/quality warnings, shadow evaluation (no trading), scheduled repeatability with rate limits, dedup and exponential retry. Test deterministic backfill for delayed reports and historic revision handling.
- Feed observed deviations into versioned strategy re-evaluation **not automatic in-place retuning**; require new sealed train/test policy and logged model/version changes.

## Maxun robot research and integration checkpoint

- **Robot health and outcome calibration:** quantify late-arriving observations, false/misattributed catalysts, duplicate rate, extractor drift and robot downtime separately from strategy performance. Never backfill current website edits into old signal histories. For a rejected Maxun option, document monitoring under the chosen existing collector instead of reporting fictional Maxun metrics.

## Required evidence / acceptance gate

Outcome tracker, calibration reports with sample counts/censoring, drift checks, deferred-retraining policy and staleness alerts. **Gate:** G06/G08/G32 and missing-outcome regressions pass; future outcomes cannot change prior signed runs.

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

**STOP after phase 15.** Return exact `PHASE 15 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 16 without a new orchestration call.

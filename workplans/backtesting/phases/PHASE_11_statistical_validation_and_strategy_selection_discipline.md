# PHASE 11 — Statistical validation and strategy selection discipline

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 11.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 10 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Statistical validation and strategy selection discipline. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Build blocked chronological train/validation/**sealed test** splits and walk-forward evaluation that replays each historic candidate using the data **available when discovered**, including delisted tokens and no-trade periods. Choose embargo/purge windows appropriate for overlapping event labels.
- Prevent optimizing thresholds against sealed test, selecting best token after seeing winners, hindsight social keywords, multiple hypothesis testing and accidental reuse of test period during tuning. Record total trials and strategy version each experiment.
- Compare strategy vs buy/hold, always-cash, randomly timed eligible trade (seeded), and one transparent basic indicator using identical routes and execution fees. Report trade count, regime breakdowns, net expectancy, tail losses, drawdowns, profitability, statistical uncertainty and failure-to-reject-null transparently.
- Use bootstrap/block bootstrap or other justified dependence-aware uncertainty and multiple-comparison correction where defensible. Report probability-of-overfit or deflated Sharpe *only if* inputs and assumptions support it—no invented precision.
- Create intentionally overfit strategy control and prove it is downrated/flagged; no strategy is declared profitable solely by in-sample curve.

## Required evidence / acceptance gate

Walk-forward experiments, sealed split hashes, holdout ledger, uncertainty analysis, negative control results and reproducibility manifest. **Gate:** G06, G22, G26–G28 pass; no performance claim without net-of-cost out-of-sample eligible cohort evidence.

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

**STOP after phase 11.** Return exact `PHASE 11 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 12 without a new orchestration call.

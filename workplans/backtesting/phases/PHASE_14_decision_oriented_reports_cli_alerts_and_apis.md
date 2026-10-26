# PHASE 14 — Decision-oriented reports, CLI, alerts and APIs

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 14.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 13 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Decision-oriented reports, CLI, alerts and APIs. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Extend **existing** report and CLI/API surfaces with separate historical strategy evidence, current execution quote, adverse stress, useful trade conditions and uncertainty. Never collapse them into one unsupported '80% chance to moon' score.
- Show exact chain/mint, timestamps, source/trade-size, cohort survival selection, sealed-test period/trade count, net-of-impact results, baseline, confidence limitations, executable proceeds versus paper profits, sensitivity, catalyst provenance, invalidation, alternate explanations and detection of fatal-flaw overrides.
- Add CLI modes such as `stress <mint> [--position-usd ...]`, `backtest --strategy ... --as-of ...`, and a reproducible run inspection endpoint **only if aligned with existing CLI conventions**; otherwise document native alternatives. Render machine-readable JSON and understandable Markdown outputs.
- Alert rules must label UNTESTED, INCONCLUSIVE or BAD EXECUTION strongly; never silently suppress missing stress analyses or convert absence to positive score. Differentiate 'good project' vs 'good entry'.
- Integration regression: missing history, missing quote, new token, disallowed mint, provider outage and high-status mismatch all produce truthful user-facing output without crash.

## Maxun robot research and integration checkpoint

- **Collector transparency:** include source/origin, capture method (`MAXUN` if applicable), first-known timestamp, archived publication confidence, late-crawl warning and crawler operational status in catalyst-backed reports. The report must not imply Maxun is running when Phase 06A concluded NO_GO/TEST_ONLY/BLOCKED. Alerts from robot observations must be rate-limited and must not bypass fatal-risk gate.

## Required evidence / acceptance gate

Human-readable report sample, JSON schema/CLI help and alerts with audit trail, screenshot or text snapshot proof, coverage disclosure. **Gate:** key fields trace back to exact observations and run hashes; G31/G34/G35 pass in both Markdown and JSON.

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

**STOP after phase 14.** Return exact `PHASE 14 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 15 without a new orchestration call.

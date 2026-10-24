# PHASE 16 — Adversarial cross-component and independent E2E audit

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 16.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 15 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Adversarial cross-component and independent E2E audit. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Act as an independent reviewer who did NOT write phases 05–15. Challenge source coverage, false historical claims, complexity, dependency license, data leak, missing-data imputation, selection/survivorship biases, sample size, P&L accounting, front-run/unfillable prints, liquidity aggregation and alert integration.
- Execute the complete fixed `ACCEPTANCE_SCENARIOS.md` G01–G41 and all existing repo tests. Run manual independent golden math, real historical cases (including an illiquid/rugged token, failed catalyst and successful-looking catalyst), fresh token with no history, blocked provider, and concurrency burst.
- Compare baseline behavior of current discovery/scout/analyze before and after integration with feature on/off; show any intentional differences in a signed change matrix.
- Repeat benchmark with sealed out-of-sample strategy and evidence of data cutoff; run mutation tests that intentionally leak future events or fake liquidity and prove tests catch them.
- Build clean checkout/container test with no secrets. Report credible failures as FAILED rather than rationalizing them; phase 16 must not silently weaken G01–G41 criteria.

## Relevant installed web crawlers

Read `references/WEB_RESEARCH_TOOLING.md` and apply the corresponding phase mapping.

- Add adversarial tests for unavailable Firecrawl/Crawl4AI, invalid or misplaced credential, crawler rate limiting, duplicate and retrospectively edited pages, HTML prompt injection, disallowed/locked sources and misclassified historical availability. Verify graceful fallbacks and absence of secrets from evidence artifacts.

## Maxun robot research and integration checkpoint

- **Maxun-independent adversarial QA:** run G36–G41 from `ACCEPTANCE_SCENARIOS.md`; independently review Phase 06A selection and any tested robot integration. For ADOPT, demand real authorized run and provenance through existing source-registry/replay path, plus license and no-schedule-without-approval evidence. For NO_GO, confirm fallback and zero dormant Maxun hard dependencies. For BLOCKED, verify its status isn't hidden in final release and independent backtesting still works.

## Required evidence / acceptance gate

`testing/E2E_RESULTS.md`, command logs, independent math oracles, three real provenance cases if possible, before-after regression matrix, open-defect ranking. **Gate:** G01–G41 and entire existing suite pass where testable, plus independently sourced real historical confirmation; unavailable live data => historical component BLOCKED and no full release claim.

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

**STOP after phase 16.** Return exact `PHASE 16 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 17 without a new orchestration call.

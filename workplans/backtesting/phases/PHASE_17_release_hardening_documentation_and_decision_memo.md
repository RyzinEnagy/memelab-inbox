# PHASE 17 — Release hardening, documentation and decision memo

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 17.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 16 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Release hardening, documentation and decision memo. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- From a clean clone and fresh environment, reproduce minimal installation, migration, historical import (if accessible), deterministic backtest, opportunity report with adversarial scenarios and disabled-feature rollback. Test both supported operating systems if claimed; otherwise limit support matrix honestly.
- Pin library versions and exact research repo SHAs, dependency SBOM and license notices; document data provenance, API cost/rate limits, correct timezone, storage, migration recovery, model limitations, quality statuses and source outage procedures.
- Write operator runbook for manual replays, backfills, diagnostics, scenario config, interpretation of strategy confidence versus token opportunity and crisis shutdown of stress module only (not disabling existing research).
- Provide executive signoff with `RELEASE / CONDITIONAL RELEASE / HOLD` and a defect list, no inflated historical performance claims, clear risk disclaimers and instructions for continuing shadow-mode calibration.
- Make a bounded local commit only if permitted. Do not push, open deploy PR, enable trading, approve license charges or delete existing data without separate user authorization. Update all authoritative handoff records and stop.

## Maxun robot research and integration checkpoint

- **Maxun operations and license closure:** include Version/edition-specific Maxun setup *only if adopted*, required config, credential-safe MCP/API/SDK access, source allowlists, run retrieval/webhook auth, rate/cost budget, robot repair, graceful outage and manual disable/rollback. Keep standing schedule disabled pending approval. Document AGPLv3 legal decision; for NO_GO/UNAVAILABLE, document selected Firecrawl/Crawl4AI/existing alternative and honest status.

## Required evidence / acceptance gate

`RELEASE_REPORT.md`, `RUNBOOK.md`, `LICENSE_ATTRIBUTIONS.md`, clean-install evidence, version matrix and explicit limitations, final run hashes. **Gate:** clean-environment reproducibility and independent reviewer signoff; no critical unresolved correctness/security defect; otherwise HOLD with fixes listed.

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

**STOP after phase 17.** Return exact `PHASE 17 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not claim release/deployment without independent release approval.

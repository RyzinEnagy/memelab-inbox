# PHASE 05 — Chronology-safe immutable data and experiment schema

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 05.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 04 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Chronology-safe immutable data and experiment schema. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Extend the existing data/bundle contracts with the smallest compatible versioned additions covering asset mint, venue/pool identity, `event_time`, `observed_at`, `available_at`, `decision_time`, earliest execution, source raw hashes, quote expiration and versions. Reuse SQLite and existing provenance design where present.
- Write safe additive migrations, backup/rollback plan, strict UTC timezone checks, uniqueness constraints, append-only historical observation trail and idempotent ingests. Guard against duplicate event records and overwritten late corrections.
- Add an explicit as-of feature-join helper used by both TA and catalyst pipelines; forbid future joins by construction and at boundary API. Distinguish zero vs missing vs stale vs provider unavailable. Store coin birth/death delisting and historic-universe membership.
- Add experiment version hashes and reproducibility references: strategy version/config, engine version, Git SHA, input datasets, feature generation, seed, training/holdout segments, fee models.
- Test backwards compatibility with existing `db`, normalize, bridge, report, CLI and previous snapshots. Challenge as-of join with backdated posts and revised holder state.

## Maxun robot research and integration checkpoint

- **Robot event provenance extension:** preserve collector/robot/run IDs, source URL, raw hash, publication claim, first observed/known timestamp, availability, version/correction and original-origin group in the existing immutable observation schema. Make `MAXUN` an optional acquisition type and prove only collector-observed evidence can qualify for historical as-of joins. Do not treat `published_at` parsed today as a historical `available_at`.

## Required evidence / acceptance gate

Versioned schema/API and migration tests, `data/CONTRACTS.md`, time-integrity audit and fixtures. **Gate:** G01–G08 chronological tests PASS and existing DB can be migrated/reopened safely without changing prior analysis results.

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

**STOP after phase 05.** Return exact `PHASE 05 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 06 without a new orchestration call.

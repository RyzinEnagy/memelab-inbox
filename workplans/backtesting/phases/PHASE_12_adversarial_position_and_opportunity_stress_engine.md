# PHASE 12 — Adversarial position and opportunity stress engine

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 12.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 11 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Adversarial position and opportunity stress engine. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Accept current opportunity snapshot, position-size range, intended entry/invalidation/exits, pool/route state, wallet clusters, fee authority, technical/catalyst conviction and model evidence tiers. Generate coherent **adverse but plausible** scenario set with explicitly synthetic shocks distinct from historic replay.
- Stress at least: 25/50/75% liquidity withdrawal, quote depletion/route failures, large insider coordinated sale, delayed exit and stop gap, failed breakout, viral post collapse/manipulation, fee-authority increase or transfer restriction, volume disappearance, market-wide SOL fall, stablecoin depeg, token mint/authority/freeze surprise, extra gas/taxes and unsellable/honeypot route.
- Recalculate fill/proceeds for each size and scenario; calculate max size under explicit max-loss and max-impact constraints, practical risk/reward and realizable upside after costs. Don't present unrealized P&L as cash realizable.
- Compare stress scenarios against historically calibrated cases **only when sufficient valid historical evidence exists**. Distinguish empirical percentiles from hypothetical shocks; refrain from assigning unjustified probabilities.
- Respect existing fatal-flaw override and permit `NO_TRADE`, `INCONCLUSIVE` and `STRUCTURALLY_UNTRADEABLE` as legitimate outcomes. Record which observation would improve or worsen assessment.

## Required evidence / acceptance gate

Stress API plus scenario inputs/ledger tables, size-impact curve, scenario report and conservative abstention behavior. **Gate:** G12, G17, G25, G30–G31 and G35 pass; shocks degrade achievable proceeds, no fabricated likelihood labels.

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

**STOP after phase 12.** Return exact `PHASE 12 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 13 without a new orchestration call.

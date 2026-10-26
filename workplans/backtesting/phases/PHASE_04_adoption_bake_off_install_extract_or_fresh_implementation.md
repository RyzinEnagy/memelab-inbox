# PHASE 04 — Adoption bake-off: install, extract, or fresh implementation

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 04.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 03 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Adoption bake-off: install, extract, or fresh implementation. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Compare top architecture combinations in **isolated POCs** on the same canonical datasets and test definitions. Include a tiny deterministic strategy, event after-known-at, two different trade sizes, and a stop gap; compare speed, ledger correctness, dependency weight and interoperability with the *real* repo.
- Choose independently per capability: `pip/install as dependency`, `licensed excerpt + provenance`, or `reimplement from ideas/formulas using independent tests`. Never vendor GPL/copyleft or uncertain snippets into incompatible code without review; prefer algorithms newly written from standards where appropriate.
- Validate environment compatibility, performance footprint, license obligations, offline reproducibility, potential malicious install behavior, native/C++ toolchain and Windows/Linux run path. Pin versions and upstream commits; keep a fallback if package not installable.
- Prototype thin adapter to actual opportunity/event record contract without changing production scoring or changing historical snapshots. Compare output against independent hand-calculated expectations rather than library's own results alone.
- Review and **reject** any feature requiring live order placement or a wallet even if candidate repo includes those capabilities.

## Maxun robot research and integration checkpoint

- **Maxun adoption is a separate decision:** inspect `getmaxun/maxun` source/license/edition as a potential **isolated public-web service** only. Contrast direct AGPLv3 source integration with a thin API adapter; document legal, security, cost, Docker/Node or cloud dependencies, and separate licensing approval if unclear. Do NOT install Maxun merely because another repo wins the engine bake-off; leave comparative robot testing to 06A.

## Required evidence / acceptance gate

`research/ADOPTION_DECISIONS.md`, `research/BAKEOFF_RESULTS.md`, dependency bill-of-materials and smoke notebooks/scripts, integration proof with recorded command output. **Gate:** strategy/ledger smoke scenarios validated, alternatives rejected with evidence, legal/installation status safe; unresolved license => NEEDS_REVIEW, no further source copying.

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

**STOP after phase 04.** Return exact `PHASE 04 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 05 without a new orchestration call.

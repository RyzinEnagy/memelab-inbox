# PHASE 03 — Source-code due diligence and ranked top 10

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 03.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 02 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Source-code due diligence and ranked top 10. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- For >=20 shortlisted repos, inspect relevant source algorithms, model assumptions, tests, examples, releases, license files, and library/package dependency constraints **at pinned commits**. Explicitly distinguish verified code from README assertion and archived screenshots.
- Attempt safe smoke builds/independent demonstrators for finalists, without wallets, secrets, production endpoints or opaque installation scripts. Record exact environment, commands and outcomes; unsupported platform is a relevant finding.
- Apply the `GRADING_RUBRIC.md` weights **without tailoring scores to your favorites**. Calculate 0–100 numerically with criterion-by-criterion evidence, hard gates, reviewer notes, integration friction and suggested use (`INSTALL`, `REFERENCE`, `ADAPT_WITH_LICENSE_REVIEW`, `REJECT`).
- Produce final ranked ten and *separate* implementation shortlist: why the #1 repo may not be best core engine, what complementary small libraries solve better, what custom microstructure code is unavoidable. Include transferability to Solana AMMs/social signals, including what each repo cannot model.
- Blind-challenge five finalist scores and resolve disagreements >10 points. Check source licensing (not inferred from GitHub license badge alone) and vulnerability/maintainer red flags.

## Relevant installed web crawlers

Read `references/WEB_RESEARCH_TOOLING.md` and apply the corresponding phase mapping.

- For top-20 due diligence, contrast crawler-extracted docs (Firecrawl/Crawl4AI if verified available) with actual pinned source functions/tests/licenses. Mark disagreement, missing evidence and unchanged claims from stale docs. No crawler summary may replace reading a checked-out code path.

## Maxun robot research and integration checkpoint

- **Maxun segregation:** rank ten backtesting/quant/AMM engines on the locked rubric. If Maxun appears during research, label it `DATA_ACQUISITION_CANDIDATE` with separate Phase 06A evaluation rather than score boosting or silently inserting it into the top ten.

## Required evidence / acceptance gate

`research/REPO_REVIEWS/<slug>.md` for >=20, `research/RANKING.csv`, `research/TOP10.md` with scores, source citation/SHA, constraints, and adoption shortlist; `research/LEGAL_LICENSE_GATE.md`. **Gate:** reproducible top ten and no unlicensed/unevidenced integration recommendation; fewer eligible repos documented, not fabricated.

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

**STOP after phase 03.** Return exact `PHASE 03 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 04 without a new orchestration call.

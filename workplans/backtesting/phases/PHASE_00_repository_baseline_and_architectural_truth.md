# PHASE 00 — Repository baseline and architectural truth

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 00.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Repository checkout and the uploaded project task methodology; existing handoff/audits where found.

**Entry gate:** NONE — this is the baseline and initial governance phase.

## Single verifiable objective

Repository baseline and architectural truth. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Clone/open the **actual** Git working tree; record canonical remote(s), branch, exact HEAD, dirty files, language/runtime, lockfiles, test command and deployment assumptions. Don't assume the public GitHub repo is the full private application.
- Find the *actual* paths of `EXECUTION.md`, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`, previous audit records; read them before making new governance files. Map all code and docs, not just root README.
- Trace `discover` → `stage2` → `scout/analyze` → scoring/report/alerts/watchlists/outcome persistence with function calls, CLI flags, fixtures, raw-collection bridge boundaries, and SQLite tables. Inspect all 28 purported modules, social intelligence, price analysis, liquidity quoting, catalysts and any historical replay/backtesting.
- Run current automated tests **without modifying them**, record exit codes and fixture limitations; independently challenge three key tests. List dormant/partially wired code, missing as-of fields, source outage and data coverage; record SHA and a baseline change freeze.
- Create namespaced audit records and a no-surprises working branch. Do not write the new engine here; only minimal safe audit scaffolding.

## Relevant installed web crawlers

Read `references/WEB_RESEARCH_TOOLING.md` and apply the corresponding phase mapping.

- Audit installed Firecrawl and Crawl4AI as actual runnable agent tools vs repositories/packages vs services. Record nonsecret versions/capabilities, one bounded authorized smoke test when useful, fallback availability and any quota limits; check whether `D:\memelab\crawl4ai-token.txt` exists **without reading or printing its contents**. Follow `references/WEB_RESEARCH_TOOLING.md`; do not call missing crawler setup an architecture-audit failure.

## Maxun robot research and integration checkpoint

- **Maxun preflight:** read `references/MAXUN_ROBOT_CONTRACT.md`. Check whether Maxun Git checkout/CLI/SDK/MCP/backend already exists; distinguish self-hosted OSS/cloud, inspect nonsecret version/availability and AGPLv3 license, detect overlap with existing social collectors. Mark `UNVERIFIED` where unavailable; do not install, print environment variables or use Crawl4AI's token as Maxun credentials. Save `research/MAXUN_CAPABILITIES.md` as an audit note (not a live functionality claim).

## Required evidence / acceptance gate

`00_BASELINE.md` with real path/function map and baseline SHA, `CURRENT_FUNCTIONALITY.md` evidence matrix, exact test logs, repo security boundary, discovered authoritative handoff paths. **Gate:** end-to-end route is traced with code references; existing suite actually executed or honestly BLOCKED; no unverified assumptions called fact.

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

**STOP after phase 00.** Return exact `PHASE 00 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 01 without a new orchestration call.

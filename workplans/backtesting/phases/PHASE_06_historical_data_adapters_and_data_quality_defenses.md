# PHASE 06 — Historical data adapters and data-quality defenses

**Role:** Independent software auditor, quant engineer, microstructure researcher and test skeptic. **Complete ONLY phase 06.** Use the project's existing language/architecture unless the audit proves a change essential.

## Read first and prerequisite gate

Read current project records, `START_HERE.md`, `EXECUTION_RULES.md`, appropriate `references/*.md`, the previous phase evidence and the current repository HEAD.

**Entry gate:** Phase 05 accepted PASS, verified by reproducing its documented gate; if it is BLOCKED/FAILED, do not advance.

## Single verifiable objective

Historical data adapters and data-quality defenses. Produce a narrow, inspectable outcome that directly enables the next phase. The complete module is **not** automatically claimed finished by this phase.

## Required execution

- Implement adapters/collector path for historical OHLCV, swaps/DEX transactions, pool reserves or CLMM/DLMM ticks/bins where available, LP liquidity changes, token supply/authorities, wallet activity, and archived catalyst/social observations. Prefer existing browser-to-inbox bridge if direct RPC blocked; prove actual data source status and rate limits.
- Support time-indexed, mint-verified immutable data shards; UTC normalization; decimals/currency conversion by historical time; provider attribution and raw references; resumable fetch with idempotent resume/backoff and bounded API usage. No secret material in repo.
- Build a *frozen historical discovery universe* that includes delisted/rugged/illiquid tokens, and recording of selection logic at each as-of date. Separate all-eligible signals from post-hoc successful token selection.
- Report real period/pool/provider coverage: rates of missing snapshots, bar sampling, stale records, social archive survivorship and blackout windows. Do not infer historical reserves by applying today's pool share.
- Add multi-source reconciliation and refusal policies. Independently inspect a handful of raw swaps and a failed/delisted token; write synthetic fixtures for unavailable modes and don't claim they're historic evidence.

## Relevant installed web crawlers

Read `references/WEB_RESEARCH_TOOLING.md` and apply the corresponding phase mapping.

- Use Firecrawl/Crawl4AI only for legally available historical public event/document collection with canonical URL, crawled-at and independently supportable first-known/publication times. On-chain AMM reserves, historic pool bins, LP state and swap executions must come from appropriate dated chain/provider evidence, not crawler estimates. Modern web captures alone cannot certify historical discoverability.

## Maxun robot research and integration checkpoint

- **Prepare for Phase 06A:** expose tested canonical external-document/source-registry APIs and raw-data/versioning contracts which robots may later use. Record existing Firecrawl/Crawl4AI and social intake capabilities without assuming any Maxun service exists. Verify contemporary crawl of old announcement does not create a backdated strategy feature.

## Required evidence / acceptance gate

Working historic data adapter(s) with real sample provenance **or an honest SOURCE_BLOCKED**, data dictionary/coverage reports and dataset hashes, reingestion tests. **Gate:** a reproducible historical corpus with exact mint/pool/temporal provenance, no survivorship concealment; lacking source => BLOCKED for live backtests.

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

**STOP after phase 06.** Return exact `PHASE 06 — PASS/FAILED/BLOCKED/NEEDS_REVIEW` with proof, defects and next phase. Do not begin phase 06A without a new orchestration call.

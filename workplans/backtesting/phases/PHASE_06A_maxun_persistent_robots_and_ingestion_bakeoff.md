# PHASE 06A — Maxun robot feasibility, comparative bake-off and conditional ingestion integration

**Role:** Independent web-automation engineer, integration QA lead and market-data provenance skeptic. **Execute ONLY Phase 06A** using the existing repo's source/evidence APIs; do not construct a new social-intelligence platform.

## Read first / entry gate

Read `START_HERE.md`, `EXECUTION_RULES.md`, `references/WEB_RESEARCH_TOOLING.md`, `references/MAXUN_ROBOT_CONTRACT.md`, `references/REQUIRED_DATA_CONTRACTS.md`, `references/ACCEPTANCE_SCENARIOS.md` and the *actual existing source registry / social ingestion / catalyst / alert code*. Recheck authoritative `HANDOFF`, `ROADMAP`, `DECISIONS`, `EXECUTION` and Phase 00/01 architecture decisions.

**Prerequisites:** Phase 06 PASS with reproducible historical ingestion/known-at gates and Phase 05 immutable observation schema. Prior Phase 04 adoption/security findings must be available. If unavailable, STOP `BLOCKED`; do not claim a live robot without source registry contracts.

## Single measurable objective

Determine through a controlled comparison **whether Maxun robots provide useful incremental persistent collection**, then either:
- **ADOPT**: implement and prove one authorized robot → real run/result → source registry → deduplicated catalyst/narrative record (keeping unattended scheduling disabled unless separately approved); or
- **EXISTING_TOOL_WINS/NO_GO**: record a defensible empirical rejection and prove the selected pre-existing collection route satisfies the same canonical event contract; or
- **BLOCKED_EXTERNAL**: implement/verify only safe schema/adapter fixtures if helpful, list the exact missing prerequisite, and never claim live Maxun access.

A PASS on this **decision phase** does not assert Maxun is live if the decision is NO_GO. Preserve the research-only/no-keys/no-order execution boundary.

## Procedure — execute, not merely propose

1. **Inspect before adding code.** Map current source registration, permitted public targets, source deduplication, event versions, trigger and alert wiring. Locate any Maxun/Firecrawl/Crawl4AI installation/MCP/SDK/API actually available to this session. Verify source version, AGPLv3 obligations and edition-specific API/docs; inspect install scripts before any isolated test. Confirm no unintended second ingestion database.
2. **Define research decision and safety budget BEFORE testing.** Name at least 2 site types and a target 10 canonical public pages per tool where lawful/accessibly possible. Record representative sites, data fields, maintenance/cost budget, allowed collectors, sampling method, and rejection thresholds. Do not access restricted services, bypass login, or assume browser recording defeats site policies.
3. **Run an independent tool bake-off.** Use available Maxun and Firecrawl/Crawl4AI/existing collectors against the *same* allowed sample and a hand-labeled extraction oracle. Measure success, completeness, field correctness, duplicate rates, revised-page behavior, runtime and operational effort. Keep sanitized real IDs, dates and URLs. If Maxun is not available, report objective accessibility limits and use fixture-only comparison distinctly; do not fabricate score tables.
4. **Record adoption decision** `ADOPT / EXISTING_TOOL_WINS / NO_GO / BLOCKED_EXTERNAL` in `research/MAXUN_ADOPTION.md`, including measured trade-offs, licensing, cost, version/OS, domains, rollout plan, and independent reviewer objections. Do not add Maxun to the backtesting engine top ten.
5. **If ADOPT and permission exists:** implement a thin versioned Maxun adapter and one concrete `project_catalyst_watch` **or** another measured-better robot. Configure bounded domains, manual one-shot runs, schema, retry/idempotency/normalization and current existing registry. Use verified API variant, not assumed endpoints. Save/recreate robot config where supported. Retrieve a **real result**, run ingestion twice, inspect original immutable event, then modified-content version where lawful/testable. Keep persistent schedule disabled until explicit approval; test schedule config in isolated/test mode without standing requests.
6. **If NO_GO/EXISTING_TOOL_WINS:** do not install Maxun or leave a dead integration; prove the current collector can satisfy the observation schema for the chosen use case and record the reason. If BLOCKED_EXTERNAL, a test-only adapter is allowed but cannot claim live access or robot implementation complete.
7. **Prove chronology and safety.** Run tests G36–G41: reject backdated page dates, false mint matches, cross-tool origin duplicates, edited releases, off-allowlist crawling, spoofed webhooks, outages, secrets and schedule activation. Tests must prove even a convincing catalyst cannot defeat fatal on-chain/exit-risk flags.
8. **Integrate with next stages:** supply versioned source adapters and provenance statuses to Phase 09 catalyst signals and Phase 13/14 opportunity reporting; Phase 16 audits these independently. Do not trigger live trading or public deployments.

## Deliverables

`research/MAXUN_CAPABILITIES.md`, `research/MAXUN_BAKEOFF.md`, `research/MAXUN_ADOPTION.md`, `data/MAXUN_ROBOT_REGISTRY.md` (may state zero adopted), `testing/MAXUN_ROBOT_E2E.md` and source code/tests when adoption is justified. Attach exact commands, exit codes, code SHA, nonsecret robot/run IDs, redacted response fields, evidence hashes, known-at claims and source URLs. Record any legal/cost/deployment approval request clearly.

## Independent acceptance gate

PASS only when independent checks reproduce (a) edition/license/capability truth, (b) fair bake-off or an honest insufficient-sample finding, (c) recorded reasoned adoption/no-go decision, (d) point-in-time compatible event fields and safe integration/no-go fallback, (e) adversarial G36–G41, and (f) existing suite unaffected. **If adopted as LIVE VERIFIED**, real robot collection + run retrieval + immutable source-registry persistence must also be independently demonstrated; a mocked result is never sufficient. BLOCKED/NEEDS_REVIEW if chosen installation depends on unapproved license exposure, credential, network deployment, persistent scheduling or paid account; document a fallback, but don't silently change this gate.

## Bounded loop: inspect → implement → falsify → repair → rerun

Use **up to five passes** from `EXECUTION_RULES.md`; record the expected behavior, sample/fixture hashes, exact test/command exit codes, reviewer objection, repair and repeat. Include at least one negative control on falsely historic catalyst data in every pass. Do not lower the gate or delete failed tests to get green. If five passes fail, mark `FAILED`/`BLOCKED` with next exact action.

## Exclusions

No unrestricted recursive scraping, unauthorized social-site robots, private-key handling, live order paths, duplicate analytics/scoring engine, assumption of AGPL clearance, unapproved deployment or standing paid schedules. Do not call inaccessible historical web content historical evidence.

## Handoff / STOP

Update the actual execution/roadmap/decisions/handoff locations without overwriting unrelated work. Identify whether next eligible phase is **07**, exact integration artifacts, risk/blocked states, approvals, and commands to reproduce. **STOP after PHASE 06A. Do not begin PHASE 07 in this context.**

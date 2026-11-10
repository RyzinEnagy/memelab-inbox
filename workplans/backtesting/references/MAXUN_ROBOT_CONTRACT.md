# Maxun persistent robot evaluation and ingestion contract — v1.2

**Read in phases 00, 01, 04, 05, 06, 06A, 09, 13, 14, 15, 16, 17.** Maxun is a proposed **public-web robot acquisition** component, **not** a backtesting engine, not a source of market truth, and not automatically installed just because its GitHub repository exists. Users report Firecrawl/Crawl4AI already installed; **Maxun availability is unverified**. Do not add Maxun to the 10-repository backtesting ranking merely to satisfy this instruction.

## Official sources to verify at execution time

- Source: https://github.com/getmaxun/maxun — source, license (currently described there as AGPLv3), build, releases and security review.
- Docs: https://docs.maxun.dev/ — feature overview; verify capabilities by edition/version.
- OSS API: https://docs.maxun.dev/api/open-source-api — self-hosted routes and auth.
- Cloud API: https://docs.maxun.dev/api/cloud-api — cloud v1 routes, pricing/limits and auth; documentation states old cloud `/api/robots` was deprecated in October 2026. **Never use cloud routes against an OSS backend or vice versa without live verification**.
- MCP setup: https://docs.maxun.dev/mcp/setup — self-hosted worker differs from cloud connection; restart/configuration may be necessary before Claude sees tools.
- Crawler: https://docs.maxun.dev/robot/crawl — capabilities and scope controls; independently verify URL filters are effectively enforced.

Treat statements as **leads**, not a promise of local availability or feature parity. Pin project SHA/tag, API edition, exact API/CLI/MCP names, docs retrieval date, and license. Do not assume cloud AI/deep-extraction features exist in OSS; do not assume a robot can interact with gated or prohibited sites.

## A. Capability audit, without credential exposure

1. Look for existing Maxun repo/package, local server, Docker container, CLI, SDK, MCP connection and account configuration. Distinguish **installed**, **configured**, **authenticated**, **functional**, **authorized** and **approved for persistent scheduling**. A Git clone is not an operational collector.
2. Verify safe nonsecret versions, backend URLs, current deployment mode, permission boundaries and documented limits. Do not print `.env`, service auth headers, proxy config or token-file contents. The supplied `D:\memelab\crawl4ai-token.txt` is *not* a Maxun key and must never be tried against Maxun.
3. Don't install, create a cloud account, enable standing schedules, open external network ports, migrate a database, call paid APIs or deploy an always-on service without explicit authorization. Clone/read source safely without executing untrusted install scripts.
4. Review AGPLv3 deployment/distribution obligations, dependencies, and source retention/license notices. Record a GO/NO-GO for **external isolated service + thin adapter** versus embedding source code. Unknown license implications mean **NEEDS_REVIEW**, not silent adoption.

## B. Comparative bake-off (when tools and public sites allow)

Use at least **two authorized public site types** (e.g., first-party project announcements and maintained developer release pages) and a reproducible sample target of **10 canonical pages per tool**, subject to access/rate limits. Evaluate Maxun against **existing Social & Trader Intelligence collectors**, Firecrawl and Crawl4AI (only where actually available) on the same inputs and conditions. Report per-tool usable pages, exact-field extraction accuracy on a manually labeled sample, duplicate rate, observed fetch-to-storage latency, automation breakage under a small page change, authentication and installation work, CPU/memory where measurable, per-run costs, schedule/run retrieval/API support, logging and provenance. If fewer than 10 authorized pages can be tested, report `INSUFFICIENT_BAKEOFF_SAMPLE` and limited conclusions. Never invent performance numbers.

Decision rules (set before results): choose Maxun **only** if a concrete *persistent robot* use case gains meaningful measurable capability or reliability over existing tooling, the permissions/cost/license are acceptable, and it does not duplicate ingestion. Document **ADOPT / EXISTING_TOOL_WINS / NO_GO / BLOCKED_EXTERNAL** and evidence. If Maxun loses, keep it out of the runtime. If adoption is chosen and executable tool access exists, the same phase must prove a fully functional thin path before calling the feature operational; no mocked passing robot accepted as live evidence.

## C. Robot specifications (candidate priorities, not mandatory blind integrations)

1. `project_catalyst_watch`: primary-source public project announcements and verified exchange/listing posts; distinguish original event, claim and subsequent correction.
2. `narrative_source_watch`: openly accessible project ecosystem/topic pages where terms permit; cluster cross-posts by canonical origin, not independent social proofs.
3. `developer_release_watch`: official public GitHub release/changelog pages (for *technical catalysts only*). GitHub API is still preferred for commits/releases if it supplies equivalent data; do not crawl it redundantly.
4. `public_trader_claim_watch`: permitted public pages only, where authorized; never bypass social-network restrictions or pretend one post is many independent sources.
5. `token_profile_watch`: public token research pages as *secondary corroboration*, not on-chain mint or executable-liquidity ground truth.

Start with ONE candidate demonstrably valuable against existing collectors, prove it, then add a second only if independently justified. For each adopted robot define robot identifier/config export when supported, allowlisted domains, exact page selectors/extraction schema and required fields, maximum page/depth, schedule (initially **disabled or proposal only**), dedupe key, output adapter, exponential-backoff policy, maximum request/cost budget, alert severity, operator disable/rollback instructions, and source rights. Prefer user-readable robot definitions/fixtures to undocumented UI-only state. If visual recorder export is unsupported, document reproducible UI steps and screenshots **without session secrets**.

## D. Canonical ingestion contract

Robots call a thin `maxun` source adapter to the **existing** event/source registry, not their own parallel business logic. Preserve immutable raw runs under canonical source references; normalized output must include at least:

- `collector='MAXUN'`; `robot_id`, `run_id`, `robot_version`, `edition/backend_mode`, extractor version and run status
- canonical source URL, source domain, raw content hash, immutable raw record/fixture ref, content language when available, title and extracted *claim* (untrusted input)
- `source_published_at` (claimed with confidence), `source_last_edited_at` (if verified), `collected_at`, `first_seen_at`, `available_at`, `event_time`, timezone UTC, `historical_asof_proof`
- source identity/origin correlation group and duplicate key; `{chain, exact_mint}` **only after independent mint verification**, never ticker only
- record type (announcement, rumor, correction, listing, release), claim-vs-verification state, extraction quality status, associated `opportunity_id` where applicable

`first_seen_at` must be computed from demonstrable capture/observation evidence, not retroactively backdated from a page's claim. Old publication dates seen for the first time today are **NOT sufficient historical evidence**; use `UNKNOWN_AS_OF`/`UNVERIFIED_CATALYST`, exclude from historical strategies until an independent contemporary archive or signed captured observation validates availability. Preserve corrections as new versions; do not rewrite history. Prevent duplicates across Maxun/Firecrawl/Crawl4AI/existing ingestion by **canonical origin + content/version**, not by raw crawler ID alone.

## E. Robot acceptance proof and failure treatment

A Maxun-enabled phase may claim **LIVE VERIFIED** only after: (1) authorized public page, (2) saved/replayed robot definition or repeatable configuration, (3) real run with robot/run IDs and sanitized run summary, (4) actual extraction retrieved through verified OSS/cloud API, SDK, MCP or UI export, (5) schema validated, (6) persisted through the **existing** source registry, (7) rescan idempotently returns same origin without duplicate, (8) corrected version remains a separate observation, (9) report/alerts reference the observation and its timing, and (10) scheduler *configuration* is tested safely without enabling unattended recurring work absent approval. If no permission to run Maxun, complete a thin adapter against labeled fixtures, mark it **TEST_ONLY**, and report Maxun **BLOCKED_EXTERNAL**, not operational.

Negative tests MUST cover: present-day crawl of an old page (no historical signal), page changed after initial crawl (versioned correction), cross-tool duplicate, wrong same-ticker token mint, spoofed release/announcement, forged publication date, parser/selector break, page prompt injection, broken scope filter or off-allowlist URL, auth expiry/401, 429/retries, run timeout, partial run, empty results, replay duplicate, crawler outage, webhook spoof/replay, secret leakage, unexpected schedule activation and fatal-flaw override. Alerts should be rate-limited, origin-deduped and **never initiate an order**. Remote webhooks must authenticate requests and be replay-safe; otherwise use authenticated poller. A broken robot must not block independent backtesting nor cause a default positive signal.

## F. Evidence / status contract

Suggested paths under the discovered repo namespace:

- `research/MAXUN_CAPABILITIES.md` — edition/version/API/MCP/CLI access; license assessment and secret-safe inventory
- `research/MAXUN_BAKEOFF.md` — comparison cases and reproducible measurements
- `research/MAXUN_ADOPTION.md` — prespecified decision, evidence and approved deployment boundary
- `data/MAXUN_ROBOT_REGISTRY.md` — selected robots, domain allowlists, schemas and owners
- `testing/MAXUN_ROBOT_E2E.md` — run ID, sanitized live traces, fixture tests and negative controls
- `RUNBOOK.md` — user operations and disable path

A deliberate evidenced NO_GO can pass the **evaluation** gate, while the feature stays `NOT_ADOPTED`; **do not label Maxun installed/operational**. An inaccessible Maxun service can be recorded `BLOCKED_EXTERNAL` while the core backtesting plan uses validated existing collectors; identify limitations and any separate approval needed. A chosen and claimed live Maxun integration **cannot** pass on fixture tests alone.

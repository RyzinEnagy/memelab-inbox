# Memecoin Social & Trader Intelligence — staged implementation pack

**Target:** `RyzinEnagy/memelab-inbox` (`main` is the baseline; work on a feature branch).

## Why these prompts are staged

The original mega-prompt mixes discovery, infrastructure, eight different sources, trader scoring, financial forensics, feed generation, and live deployment. A coding agent may deliver scattered placeholders instead of an end-to-end working component. This pack uses **one vertical slice per session**, explicit evidence gates, and a handoff committed to the repository after every phase.

A public README inspection on 2026-10-10 described `memelab/db.py` (SQLite), `memelab/normalize.py`, `memelab/pipeline.py`, `memelab/report.py`, `memelab/cli.py` (including `social-note`), `memelab/bridge/`, a Chrome/GitHub inbox handoff, and pytest. **This is only README evidence, not code verification.** Phase 00 must inspect source and the current tree. Do not assume older mentions of `memelab/chains/`, `memelab/catalyst/`, `data/state/latest.json`, or special bootstrap commands apply to the current checkout.

## How to operate

1. Connect the coding agent to the repo, or provide an authorized local clone. Use a capable coding agent with terminal access (Claude Code or ChatGPT Work). Do not just paste into an ordinary chat and expect code to be committed.
2. Start with **Prompt 00**, then proceed in numeric order **only after the previous phase's gate passes**. Open a fresh chat for each phase if convenient.
3. Paste the **entire contents of that phase's file**. Each prompt directs the agent to recover scope from durable repo files, so a fresh chat does not need past conversation context.
4. Review the summary, test commands, actual test output, changed files, and commit. If the gate fails, tell the agent: `Fix the failed acceptance criteria for this phase only; do not begin the next phase.`
5. Treat prompts 19–21 as **optional source expansions** after the core pipeline works; skip integrations whose legal/technical access is not available.
6. Do not provide seed phrases, private keys, or secret values in prompts. Use environment variables and documented secure secret handling. Rotate any API key previously shared publicly or committed.

## The discipline that prevents stubs

Each phase must: (i) inspect code and load the current handoff, (ii) implement **only** its acceptance criteria, (iii) run relevant tests plus the project's full baseline test command, (iv) demonstrate a reproducible real or fixture-based end-to-end behavior, (v) update the decision log and handoff, (vi) commit on the same feature branch if allowed, and (vii) stop. No unused interfaces, success-shaped placeholders, hardcoded impressive scores, or invented live API data are acceptable.

## Suggested phase order

| Phase | Concrete vertical slice | Gate artifact |
|---|---|---|
| 00 | Baseline audit and operating contract | Verified map + passing baseline |
| 01 | Database, provenance, migrations | Round-trip & migration tests |
| 02 | Connector framework and bridge | Ingest same fixture twice: one stored event |
| 03 | X connector | Real authorized ingest **or explicit blocked** plus fixture tests |
| 04 | Telegram connector | Permitted channel ingest **or explicit blocked** plus fixture tests |
| 05 | Token identity and market snapshots | Same ticker on two chains never merges |
| 06 | LLM extraction | Validated claims and source citations |
| 07 | Narratives and propagation | Source-independent counts and deltas |
| 08 | Trader registry and discovery | Evidence-backed source ranking inputs |
| 09 | Wallet attribution and activity | Attribution links with confidence |
| 10 | Trading performance | Transfer != P&L; costs tracked |
| 11 | Commentary information value | Matched-baseline scoring with abstention |
| 12 | Social/on-chain chronology | Before/after with timestamp uncertainty |
| 13 | Existing discovery integration | Social cannot bypass fatal-flaw gates |
| 14 | Digest, brief and feed | Source-linked readable outputs |
| 15 | Alerts and scheduling | Deduped and throttled alert delivery |
| 16 | Outcome ledger and forward evaluation | No look-ahead in recorded outcomes |
| 17 | Historical replay and statistics | Transparent validity or no-result outcome |
| 18 | Release, audit and deployment | Full reproducible runbook + checks |
| 19 (optional) | Reddit + Farcaster | Two individually functioning connectors or documented blocker |
| 20 (optional) | Discord | Authorized guild/channel ingestion |
| 21 (optional) | YouTube | Caption/metadata ingestion within access rules |

## Execution expectations

**Public repo warning:** `memelab-inbox` describes itself as a public data hand-off. Do not assume public distribution rights for raw social posts, privileged social metadata, private discussions, subscriber-only content, or sensitive user-derived records. Store minimal identifiers and permitted excerpts publicly; put restricted/private source material in gitignored local storage, with references in the public inbox only as permitted.

**Source-coverage honesty:** Successful fixture tests prove code behavior, not live source availability. Every adapter must report `operational`, `credentials_missing`, `unsupported`, `rate_limited`, `blocked`, or `stale` where appropriate. A new integration can be marked blocked without blocking later fixture-based development, but the final product must not call such a source live.

**Safety constraint:** Research only. No wallet signing, trading bots, auto-execution, private-key access, or guarantees of profitable signals.


---

# PROMPT 00 — Audit the actual repository and establish a resumable execution contract

You are implementing Social & Trader Intelligence for `https://github.com/RyzinEnagy/memelab-inbox`. **This is Phase 00 only.** Treat the actual checkout as truth. Do not implement social functionality yet.

1. Open the authorized local clone or clone without executing remote bootstrap scripts. Record branch, HEAD, working-tree state, Python version, entrypoints and dependency management. Create one feature branch (suggested `feature/social-intelligence`) from current main if this will not disturb existing work; if uncommitted changes exist, preserve them and explain the safe branch strategy. Never force-push.
2. Read the real `README.md`, `docs/ARCHITECTURE.md`, `docs/SOURCES.md`, `skills/memecoin-scout/SKILL.md` when present. Inspect `memelab/db.py`, `normalize.py`, `pipeline.py`, `report.py`, `cli.py`, `memelab/bridge/`, actual `social-note` implementation, existing modules, tests, .gitignore, and the public inbox/bridge flow. Document differences between the current code and earlier assumptions. Distinguish facts seen in source code from README claims.
3. Run the project's existing test command, expected `python -m pytest tests -q`, plus a harmless CLI help/smoke check. Preserve verbatim outputs and pre-existing failures. Identify any runtime inability to call upstream APIs and whether Chrome-to-GitHub is the established collection route.
4. Audit secret-handling boundaries and public-repo redistribution risks. Do **not** print or commit credentials. Warn if known secrets may already have been exposed; propose rotation without reproducing values. Determine what raw social content may legally/safely be stored in the public repo.
5. Create `docs/social-intelligence/EXECUTION.md`, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`. EXECUTION is the contract that all future fresh sessions must follow: **one phase/session; implement, test, prove, commit, handoff, stop**. ROADMAP lists phases 00–21, dependencies and pass gates. HANDOFF records active branch, latest commit, verified modules, test command/outcome, current phase, next phase, blockers and exact next command. DECISIONS records durable architectural choices and their reasons. Do not invent evidence.
6. Add a tiny automated `social-phase-check` script only if it directly validates the handoff/roadmap contract; otherwise skip new code in Phase 00.

**Gate:** baseline test results recorded; architecture and source-access constraints mapped; working branch established; four durable documents exist, accurate and linked; no existing functionality changed unintentionally. Commit these docs if authorized. Report changed files, tested commands with exit codes, commit hash, blockers. **Stop; do not start Phase 01.**


---

# PROMPT 01 — Implement durable schemas, evidence provenance, and migration safety

Work only on Phase 01 of `RyzinEnagy/memelab-inbox`. First read `docs/social-intelligence/{EXECUTION,ROADMAP,DECISIONS,HANDOFF}.md`, verify checked-out branch/HEAD and previous acceptance gate, and inspect actual existing SQLite/state/normalization code. **Do not design a parallel data store without justification.**

Implement a minimal complete persistence layer for social intelligence, using repository conventions. Models/tables should support: source accounts and platform identities; trader registry; wallet-attribution assertions with evidence and confidence; source observations with original URL, provider ID, publication time, observation time, ingestion time, content hash, retrieval status, permissible retained content; token references with chain+contract; extracted claims; narratives; links between evidence and claims; connector health; analysis version; and source-coverage records. Leave future performance/outcome tables for their dedicated phases unless needed for referential integrity.

Explicitly represent unknown values and tentative assertions. UTC storage, schema versions, append-only historical observations where appropriate, stable uniqueness constraints, idempotent upserts, migration and rollback plan. Social IDs are not automatically wallet IDs; ticker strings are not token IDs. Prevent public-repo leakage of sensitive raw posts with safe persistence defaults (metadata/references only, private gitignored store for content where allowed). Document retention and reprocessing policy.

Build concrete storage CRUD/round-trip functionality. Test schema initialization in an empty DB, migration from a copy of an existing DB, repeated ingestion, missing timestamps, duplicate provider IDs, conflicting claims, and rollback/recovery. Prove existing watchlists, theses, snapshot tables and rejection records remain unchanged. Show a tiny fixture-driven round trip through real persistence, not mocks alone.

**Gate:** exact schema and migrations documented; tests prove insert/read/update/idempotency and current-state compatibility; full pytest baseline passes or any known pre-existing failure is clearly isolated. Update HANDOFF/DECISIONS/ROADMAP, commit on existing feature branch if authorized, report exact commands and outputs, then **stop before Phase 02**.


---

# PROMPT 02 — Build one operational ingestion contract and the existing browser bridge adapter

Execute Phase 02 only. Read social-intelligence EXECUTION, ROADMAP, DECISIONS, HANDOFF and verify Phase 01. Inspect the repo's real browser/Chrome/collector-to-GitHub inbox path (`memelab/bridge/`, inbox, manifests, CLI) and existing request/cache/error-handling utilities. Do not presume that cloud Python can reach crypto/social APIs.

Implement a working provider-neutral ingestion framework with one **fixture-backed bridge/inbox adapter**, not a dozen unimplemented provider classes. Define versioned inbound observation schema, source identity, provider timestamp vs fetched timestamp, source URL, event IDs, content hash, access/rights metadata, validation errors, provenance, and connector health state. Provide an import/ingest command integrated with the existing CLI patterns. Support replay-safe checkpoints, bounded retries, rate-limit/cost budget hooks, batch size, stale-data detection, dedupe, quarantine for malformed payloads and structured logging that never prints secrets or prohibited content.

Demonstrate the actual established inbox ingestion route using a properly shaped fixture placed in the correct test location; do not commit privileged or copyrighted raw content. Re-running it twice must not create duplicate events. A bad item must be quarantined without discarding other good entries. One unavailable connector must not mark all sources healthy or destroy the run.

Create a provider adapter interface only for methods truly used by this implementation; document how X/Telegram will plug in. Respect existing object contracts instead of inventing `state/latest.json` integration if not present.

**Gate:** runnable import CLI; persisted verifiable observation; repeated ingestion idempotent; malformed and stale events handled; unit/integration tests pass and existing tests still pass. Update handoff/decision log, commit if authorized, show test output, **stop**.


---

# PROMPT 03 — X/Twitter monitoring as a real, permitted source

Execute Phase 03 only. Load the four social-intelligence handoff documents; check preceding gates and source-access design. Verify **current** X API availability, endpoint capabilities, read pricing, terms, historical windows and authorization requirements from official documentation. Do not scrape through unauthorized means or misrepresent API access.

Implement one adapter for explicitly configured public X accounts/lists/search scopes insofar as official allowed APIs support them. Capture stable post IDs, original author, published time, link, text only when license/terms allow retention, reference type (original/reply/repost/quote), conversation context where accessible, and provenance/freshness. Produce normalized source observations via Phase 02. Implement pagination, rate limits, graceful 429/403 handling, incremental cursor/checkpoint, bounded budget and reingest deduplication. Mark unsupported reply/quote/repost/list visibility accurately.

**Crucial:** if credentials or permission are not available, do not invent a live integration demo. Implement verified request/response contract from official docs with recorded synthetic HTTP fixtures, a connection-health command that reports `credentials_missing`, and a clearly documented sequence to authorize it. Skip actual billable reads unless explicit configured budget/consent exists. If X integration is commercially impractical, record justified source-alternative decision rather than substituting noncompliant scraping.

Test originals/reposts/quotes, duplicate IDs, author changes, edited/deleted access limits, pagination, 429, 403, billing guard, timestamp correctness, cache freshness, and secret redaction. Show one CLI or integration-harness flow through stored observations.

**Gate:** real adapter with confirmed API contract; either evidenced live authorized ingest **or explicitly marked unavailable**; reproducible fixture tests, budget behavior and no false live claims. Update docs, commit if authorized and **stop**.


---

# PROMPT 04 — Telegram public-channel monitoring

Execute Phase 04 only; read EXECUTION/ROADMAP/DECISIONS/HANDOFF and real connector code. Verify official Telegram Bot API or another explicitly permitted integration; explain channel membership/admin requirements and inaccessible historical/private content. Never pretend an arbitrary public channel can be read by a newly created bot.

Build an adapter for **authorized** channel messages and/or webhook/update capture into Phase 02's normalized observation model. Support channel ID, message ID, author/poster where provided, sent/edited time, forwarded-from provenance when actually available, message text only if rights permit, external source link if resolvable, and reply-to context when available. Include webhook authentication/validation as relevant, secret redaction, retry/idempotency, cursor/offset handling and channel-level health states. Integrate with current Chrome/GitHub inbox collection route only if that is actually the legitimate operational path.

Test message edits, duplicate updates, forwards, deleted/inaccessible messages, authorization denial, out-of-order updates, and restart/resume after interrupted ingest. Do not count forwards as independent original claims. A small fixture-driven CLI demo must persist an observation with source provenance. If credentials and approved channels are not configured, surface explicit setup steps and `credentials_missing`/`access_denied` status without fabricating live observations.

**Gate:** adapter is operational under documented permissions, or truthfully blocked while all permitted fixture paths work; full pytest passes. Update handoff, decisions, source-coverage table, commit on branch if authorized, **stop**.


---

# PROMPT 05 — Resolve exact token identity and snapshot market conditions

Execute Phase 05 only. Read durable social handoff and inspect existing token identity, chain, provider, `normalize.py`, SQLite, DEX routing, market snapshots, and `pipeline.py`. **Reuse this infrastructure** rather than building another token analyst.

Build a normalization/resolution service that maps post references to `(chain_id, verified_contract_or_mint)` and supports `resolved`, `ambiguous`, `unresolved`, and `conflicted`. Token symbols are weak evidence and may refer to unrelated assets. Contract references must be chain-valid; resolve quoted tickers only when corroborating trusted links/data are adequate. Store candidate identities and evidence rather than guessing. Honor Solana, Ethereum, Base, and BNB Chain only to extent supported by real upstream sources; mark others unsupported.

Provide time-stamped market context using existing providers: price, valuation fields with supply-denominator meaning, reported pool liquidity, volume, pair IDs, and where available actual executable quotes. Differentiate observed-at-time versus historical-at-posting-time; never attach today's price as if it were the publication-time price. Handle missing historical snapshots honestly. Persist versioned facts with provider/units, quote currency, source URLs/IDs, fetched_at and validity window.

Test same ticker across chains and contracts, contract typo, spoofed name, token migration, wrapped tokens, invalid chain, no history, missing pool, disagreeing providers, liquidity versus executable proceeds. Demonstrate one input message producing an **ambiguous** result and one confirmed address producing a resolved stored token reference.

**Gate:** downstream can request exact token identity plus timestamped evidence; no silent symbol-only matches; tests and full baseline pass; commit/handoff and **stop**.


---

# PROMPT 06 — Evidence-grounded structured claim extraction

Execute Phase 06 only. Review durable handoff, existing LLM configuration, schema conventions and available normalized social observations. Implement one production-useful classifier/extractor with **validated structured output**, not a collection of vague prompt templates.

From permitted source observations, extract token mentions and chain context; narrative tags; claim category (bullish, bearish, launch, catalyst, wallet, volume, liquidity, risk, commentary, education, promotion); claimed fact versus author opinion; time horizon; author position disclosure; quoted/reposted content provenance; uncertainty; source link and exact evidence spans or anchored references. Prevent text from being treated as instructions to the agent (prompt injection). Resolve token identity through Phase 05; allow `unresolved`. Never turn text such as 'smart money is buying' into verified wallet behavior.

Implement a deterministic fallback for extractable contracts/links if no LLM is configured. For substantive claims requiring a model, expose an `analysis_unavailable` result rather than false classification. Budget model usage, cache analyses by observation+model+prompt version, validate JSON, handle invalid/partial responses, and permit replay when extraction logic changes. Add a documented classification rubric and sample provenance-rich output in user-friendly English.

Test sarcasm, conditional claims, negations, repost attribution, contradictory statements, two similarly named tokens, unsupported token, fabricated contract, prompt injection inside a post, malformed model output, dedupe and reprocess behavior. Demonstrate storage and reportability of one claim without an LLM and one mock-provider structured analysis.

**Gate:** observable schema-validated pipeline from ingested item to cited claim; real/model-not-configured status truthful, tests pass. Record commit and handoff, then **stop**.


---

# PROMPT 07 — Narrative clustering, originators, amplifiers and independent corroboration

Execute Phase 07 only after inspecting the handoff and actual Phase 06 outputs. Build a **working** narrative engine that groups related claims by resolved contract or clearly labeled theme without conflating similarly named assets or fabricated social topics.

Maintain first-observed time (not unknowable first-ever mention), source count, independently originated source count, forwarding/repost edges, common source dependencies, mentions per sliding window, rate of change, confidence, coverage limits, chain and linked-token context. Reposts/quotes that repeat a claim count as amplification, not independent validation. Avoid treating 'different accounts' as independent when all cite a shared original or show coordinated repost patterns. Mark inferred coordination as hypothesis rather than proven ownership.

Implement deterministic clustering first (contract and structured tag/topic keys); use vector/LLM semantic clustering only where it can be evaluated against fixtures and has a reproducible fallback. Compute narrative snapshots and deltas across runs with timestamps, versioning and provenance links. Emit `insufficient_coverage` when volume/independence is not estimable.

Tests: repeated reposts by 100 handles, two separate early originals, same token ticker different contracts, multi-token themes, conflicting narratives, changed opinion, deleted/inaccessible source, time-zone boundaries, stale data. Prove daily change results using two controlled fixture windows. Include explainable 'why this cluster' output.

**Gate:** durable narrative snapshot and change summary; independent count defensible; full suite passes; update DECISIONS/HANDOFF, commit and **stop**.


---

# PROMPT 08 — Trader registry, source credibility and evidence-based discovery

Execute Phase 08 only. Read handoff, SQLite models, source coverage and narrative outputs. Implement a real, persistent **source/trader registry** that does not assume a profitable wallet owner is also a valuable public commentator.

Define distinguishable identities: social account, self-disclosed public wallet, observed wallet, verified attribution assertion, third-party leaderboard candidate, source organization and social network. Support multiple handles and multiple wallets without merging by name. Record explicit provenance, attribution confidence, timespan, platform, specialty, watch status, topical focus, and reason for following. Candidate categories: profitable-trading claimant, verified-wallet candidate, information originator, analytical source, amplifier, promoter/high-conflict. Never fabricate current rankings or seed 100 arbitrary accounts.

Implement candidate discovery from *sources actually accessible*, such as ingesting a permitted leaderboard file/API or analyst posts; evaluate claims about leaderboards separately. Implement manual review/approve/reject/update commands, searchable CLI list and safe import. Populate fixture candidates to demonstrate controls; label fixtures. Where provider access permits, ingest real current candidates with capture timestamps and direct URLs; otherwise explicitly leave candidates unverified.

Tests: identical screen names, handle rename, account suspension, wallet self-claim versus independently corroborated ownership, stale leaderboard, duplicate rankings, missing platform link, sources without wallets. Show candidate -> evidence -> reviewed registry record through the CLI.

**Gate:** registry records can be used by later attribution/performance stages; no unsupported 'best trader' assertions; tests and baseline pass, update handoff/commit, **stop**.


---

# PROMPT 09 — Verify wallet links and observe activity without identity overreach

Execute Phase 09 only. Read handoff and inspect actual Helius/on-chain forensics (`memelab/forensics.py`, other on-chain modules), existing wallet tracker, provider abstraction and registry. Do not create wallet identity links from matching usernames or suggestive transfers alone.

Implement wallet-attribution assertions as independently auditable records: asserted trader/account; exact chain+wallet; evidence type (official account self-disclosure, signed message, independent linked source, third-party claim, transaction pattern); evidence URL/ID; observation and validity timestamps; confidence; reviewed/unreviewed; revoked/superseded. Separate real-world identity (generally unknown) from on-chain control hypothesis. Use publicly available wallets only.

Reuse upstream transaction ingestion to monitor selected wallets, classify transfers/swaps/LP operations as distinct events, link relevant contracts, record transaction signature, chain, block time, fees, counterparties and source. Provide tracked-wallet add/remove/pause commands with safe defaults. When attribution is uncertain, permit wallet-level monitoring without claiming which person it belongs to.

Tests: fake ownership claim, token transfer misclassified as sell, wallet-funded-by-same-wallet clustering hypothesis, custody address, relabeling of wallets, multiple chains, provider 429, missing signatures, stale transactions. Demonstrate exact transaction-classification flow using realistic fixtures and a verifiable provenance chain.

**Gate:** reviewer can inspect *why* a wallet is linked or not linked; activity survives reload and does not become P&L until next phase; full tests and handoff/commit, **stop**.


---

# PROMPT 10 — Trading performance accounting with realistic limitations

Execute Phase 10 only. Read handoff, inspect Phase 09 on-chain transaction classification and existing cost/quote modules. Implement transparent **wallet-level** performance reconstruction rather than trusting a leaderboard field or claiming complete person-level profitability.

Account for buys, sells, token decimals, swaps, fees, token transfers, airdrops, liquidity deposits/withdrawals, open inventory, cost basis, and missing-history intervals. Choose and document a defensible lot convention (e.g., FIFO or weighted average), including sensitivity where material. Separate realized P&L, unrealized mark-to-market, transaction costs and estimated liquidation proceeds. Do not classify incoming transfers as free profitable buys or assume external-wallet flows are gains. State when comprehensive reconstruction cannot be achieved.

Calculate trade count, win rate with declared definition, median return, profit share from biggest winner, return excluding biggest winner, drawdown only where sufficient equity-series data exist, sample size and confidence/coverage. Report source history coverage and unknown fees. Prevent rankings on sparse or highly incomplete observations. Optional live provider comparisons must be labeled estimates and never substitute for accounting validation.

Test partially missing transaction history, same token with multiple lots, wash-like transfers, fee-on-transfer tokens, decimal errors, rug with unexitable position, wallet-to-wallet transfers, profitable outlier, stablecoin peg changes and no-price scenario. Include fixture ledger with hand-checked numeric expected results; demonstrate wallet score refusing insufficient data.

**Gate:** repeatable P&L calculation with deterministic reconciliation checks; gaps and mark-to-market vs executable proceeds explicit; existing full test suite passes; update docs/commit/handoff, **stop**.


---

# PROMPT 11 — Measure the predictive value of public posts, not just wallet profits

Execute Phase 11 only. Read handoff, real historical market-data coverage, trader registry, stored claims and performance records. Implement the **Information Alpha Score** as a separate, uncertainty-aware evaluation of public commentary.

Define timestamped event study: original public post timestamp, first observed timestamp, token identity, disclosed position/conflicts, pre/post trading if attributed, publication-to-price move lag, pre/post liquidity and matched comparison token group. Compute returns at configurable 1h, 6h, 24h, 72h, 7d only where history exists, maximum favorable/adverse excursion if observed path coverage permits, a realistic delay, estimated fees and execution frictions. Do not fabricate historic prices by replaying live quotes as if known at post time. Predefine selection rules and include all eligible negative/neutral calls, not only winners.

Produce explainable metrics: coverage, number of independently evaluable calls, median relative return versus matched baseline, information lead-time distribution, false positives, failure to beat matched tokens, confidence intervals when statistically appropriate. Use conservative shrinkage / insufficient-data abstention; never assign a score of 95/100 on 3 calls. Keep source popularity out of the formula except as explicitly justified context. Version scoring rules and separate 'unverified', 'preliminary', and 'validated'.

Tests: late promotion after pump, hindsight-selected call, repeated reposts, delisted tokens, price gaps, illiquid execution, null baseline, temporal leakage, zero eligible calls, conflicting bullish/bearish statements and a statistically noisy sample. Show an end-to-end fixture evaluation with transparent calculations and a source for every observation.

**Gate:** the engine can legitimately decline to rank; wallet profits remain separate; tests pass; commit and record handoff, **stop**.


---

# PROMPT 12 — Reconcile social claims with actual on-chain chronology

Execute Phase 12 only. Read handoff and inspect observed claims, verified/uncertain wallet associations, swaps, on-chain timestamps and market snapshots. Build a clear **chronology/corroboration** component.

For a resolved token and social source, generate one ordered timeline containing published post, first seen post, attributed-wallet buy/sell/transfer, major pool liquidity changes where observed, and market movement. Preserve timestamp precision/uncertainty and explain differences between chain slot time, source publication time, and collection time. Identify *observed patterns*: trade before talk, talk before trade, talk without observed trade, trade without observed talk, potential distribution during promotion. Absence of a monitored trade is not evidence that none occurred. An uncertain attribution must never become a definitive accusation.

Build a concise evidence summary with independent links and labeled **fact / inference / not established**. Register corroboration/risk flags in normalized outputs for later discovery pipeline use. Validate token and chain identity on every join. Implement time-window configuration, dedupe, missing-provider fallbacks, stale-evidence warnings and human-readable output.

Tests: delayed API delivery, missing/block timestamp, token symbol collision, conflicting wallets, same-minute ordering ambiguity, unrelated transfer, two separate persons using one custodian, promotional repost, missing price and source deletion. Demonstrate two fixtures: confident order and indeterminate order.

**Gate:** ordering is accurate or explicitly uncertain; links trace to original evidence; no unsupported ownership or manipulation claims; tests pass, handoff/commit, **stop**.


---

# PROMPT 13 — Integrate social signals into the existing scout and catalyst workflow

Execute Phase 13 only. Read handoff and inspect *actual* discovery/scout pipeline, ranking, module outputs, fatal-flaw criteria, watchlists, rejections, theses and report adapters. **Do not replace the existing research system.**

Implement a focused adapter that transforms sourced social/narrative findings into **research candidates** compatible with the existing system. A social signal should attach originators/independent corroboration, freshness, contract+chain, confidence, promotional risks and relevant timeline evidence. Reuse existing token verification, liquidity, executable depth, holder concentration, LP control, token mechanics and risk screening. Preserve a hard separation between (a) narrative attention, (b) acceptable token structure, and (c) attractive executable entry. High hype cannot override fatal flaws. Candidates with only ticker mentions stay unresolved and out of tradable rankings.

Extend the existing CLI/`social-note` workflow where it fits; don't create duplicate token scoring or two parallel watchlists. Ensure existing `scout` runs with social intelligence disabled or no data produce backward-compatible results. Define opt-in enablement and configurable weight/signal policy with provenance. Social findings must have zero *automatic* trade execution impact.

Tests: fatal-flaw override, spoof contract, social 'top pick' with no liquidity, valid candidate with credible early discussion, no social data, stale sources, conflicting narratives, repeated ingest, rejected thesis and later materially changed evidence. Produce a side-by-side before/after fixture scout report demonstrating an enriched research candidate and an unchanged rejected token.

**Gate:** integrated path genuinely executes; old pipeline still works; explicit no-op when source unavailable; baseline full pytest passes, commit/handoff, **stop**.


---

# PROMPT 14 — Produce a readable, cited intelligence feed and digest

Execute Phase 14 only. Read handoff and inspect existing markdown reporting, CLI and output conventions. Produce one useful **read-only feed renderer** over real stored observations/claims/narratives that works without a paid dashboard or a configured LLM.

Create CLI commands consistent with current code, e.g. `social feed`, `social brief`, `social trader-digest`, if parser structure supports them. Generate (1) last-24-hour narrative-first morning brief, (2) trader conversation digest with changed positions and disagreements, and (3) searchable/filterable feed by chain, token, source, time or risk. Every item should give: what happened, first observed/published time, who said it, original links, independence vs repetition, why it matters, what is corroborated, what is speculation, reasons to doubt, liquidity/exit caveat, research next step, and data freshness/coverage. Do not fabricate current conversations when using fixtures; clearly watermark fixture demo outputs. Group discussion by token/theme rather than reverse-chronological influencer spam.

Render through current report pipeline, with safe markdown escaping and no raw sensitive text in a public report. Add a stable machine-readable JSON representation so later alerts/scheduler can consume it. Handle no signals by reporting 'no supported high-priority observations' rather than inventing news. Do not yet send notifications or schedule jobs.

Tests: 0/1/multiple narratives, conflicting opinions, repeated forwards, unresolved ticker, source-link sanitation, stale data, time zone formatting, missing paid model, prompt-injection text, identical rerun. Include readable sample fixture report and one CLI command to reproduce it.

**Gate:** durable useful generated report, linked sources and provenance, no fake live output, full suite green; handoff/commit, **stop**.


---

# PROMPT 15 — Controlled research alerts and scheduling

Execute Phase 15 only. Read the four durable handoff documents and inspect current report, workflow, browser bridge, repo Actions/scheduler and configuration patterns. Implement **research-only** alerts consuming Phase 14 events, not another detector.

Define alert policies for: independent reputable sources converging on a narrative; verified monitored-wallet activity corroborating a claim; new important risk evidence; previously bullish analyst switching stance; exceptional growth in conversation vs its baseline. Require chain+contract and source freshness for token-specific alerts. Add severity, reason, confidence, provenance, cooldown, dedupe key, per-day message cap, per-provider API cost ceiling, quiet hours and time-zone-aware schedule (America/New_York). Avoid more frequent polling than upstream refresh capability.

Create an operational local/file sink first and optionally one authorized Telegram bot or email transport only if credentials are configured. Never claim delivery occurred when only a local preview was written. Implement dry-run mode and explicit send enablement, safe handling for destination tokens, retry policy and delivery ledger (attempted, succeeded, failed). Respect public-repo secrets and opt-in user notification preferences. Make daily/weekly job templates with timezone/DST tests, but avoid enabling jobs without consent/configuration.

Tests: duplicate alert across retries, cooldown reset, 100 reposts and no independent corroboration, stale wallet event, repeated schedule after restart, missing token, notification transport failure, timezone/DST changes and no-alert day. Show a fixture-generated alert, a deduped second run, and readable delivery-state output.

**Gate:** no alert spam, explicit configured delivery, work under missing credentials via dry-run, full tests pass. Handoff/commit, **stop**.


---

# PROMPT 16 — Build immutable signal ledger and forward evaluation

Execute Phase 16 only. Read handoff and inspect data models, market snapshot retrieval, reports and timing conventions. Implement a **forward-looking signal/outcome ledger** that records what the system knew when it emitted a research signal.

Capture signal ID, classifier/scoring versions, source/claim references, resolved contract+chain, event time, generated time, observed price, route/liquidity conditions where available, evaluation horizon, position-size assumptions, hypothetical execution lag/fees and missing data. Record immutable original context; later fetched market outcomes must append rather than rewrite the original signal. Compute returns only with dated price observations; max excursion only with sufficiently granular path history; distinguish actual route quotes from modeled impact. Never fabricate unobserved exits or treat displayed P&L as executable proceeds.

Build `social evaluate` or codebase-conforming command that appends 1h/6h/24h/72h/7d outcomes as they mature; mark outcomes `pending`, `measured`, `missing`, `non-executable`, or `invalidated` with reasons. Preserve failures and rejected candidates (no cherry-picking). Add a report showing outcome-coverage rates and reasons for exclusion.

Tests: look-ahead protection, revising underlying provider snapshots, delayed publication, delisted tokens, lost liquidity, missing midpoints, duplicate evaluation, source deletion, postponed windows, price-quote mismatch, and no outcomes matured. Demonstrate fixture signal snapshot before/after two forward evaluations with zero original-context mutation.

**Gate:** auditable chronological ledger, deterministic resumption, transparent missing outcomes, baseline suite passes. Update handoff and commit, **stop**.


---

# PROMPT 17 — Historical replay, baselines and statistical honesty

Execute Phase 17 only. Read handoff, available historical social and market windows, information-value scoring, outcome ledger and existing testing methodology. This phase is **not** permission to fabricate a 90-day backtest where history is missing.

Implement a causal chronological replay harness with a cutoff clock: at each replay step, only posts, trades, prices and provider data demonstrably available at or before the cutoff are accessible. Version source coverage and scoring rules. Support matched-token baselines by chain, capitalization/liquidity band and calendar regime where samples allow. Compare (a) individual analyst signal, (b) independent convergence, (c) social+wallet confirmation, (d) raw mention/trending baseline; estimate eligible sample count, coverage, precision, median relative performance, max adverse excursion and hypothetical executability, with credible uncertainty ranges and multiple-testing cautions where meaningful.

Design strict chronological train/validation/test splits. Do not tune thresholds on held-out future outcomes. Make it easy to run a **synthetic fixture replay** demonstrating no leakage. Real results must be labeled 'insufficient sample/data' if coverage is poor; do not extrapolate absent data. Produce readable validation report distinguishing forward test from backtest and selection bias.

Tests: future information injected into training, duplicated reposts, missing delisted-token prices, huge win dominating results, survivorship bias, provider publication lag, no valid matched controls, contradictory signals, no tradable depth and insufficient sample. Demonstrate a test that fails if the harness accesses future evidence.

**Gate:** trustworthy replay tooling, and an honest result (including 'cannot validate yet' when necessary); full pytest passes. Handoff/commit, **stop**.


---

# PROMPT 18 — End-to-end release engineering, operational audit and delivery

Execute Phase 18 only. Read handoff and every prior phase's commit/change/test record. Audit the **actual implemented code** against acceptance criteria, not the original conceptual specification. No new speculative provider integrations or sweeping refactors in this release phase.

Run clean-environment setup, migrations, fresh fixture inbox load, duplicate replay, token resolution, structured extraction, narrative change, trader registry, wallet attribution, P&L reconstruction, information-alpha evaluation, social/on-chain chronology, main discovery integration, report generation, alert dry-run, forward outcome evaluation and causal replay. Capture exact commands and outputs. Run full test suite and reasonable lint/type/static/security checks already used in repo. Audit public repo for credential leakage, restricted social content, accidental wallet keys, public redistribution concerns, schema incompatibility, accidental live billable requests and excessive logs. Verify no trading execution exists.

Provide README, architecture and operations runbook for non-programmer: source access, costs, env variable names (never secret values), CLI quick start, first-ever setup, schedule enable/disable, maintenance, data deletion, troubleshooting, known unsupported features, and proper citation/uncertainty standards. Make configuration opt-in, defaults safe and routes replayable. Produce two example reports: clearly fixture-only and authorized real-data only if genuinely captured. Validate no-signal/no-credentials behavior. Create a release checklist with each requirement `PASS`, `BLOCKED`, or `NOT IMPLEMENTED`, proof location and decision, not a vague 'done'.

Commit finalized changes on feature branch if authorized, open a pull request if repo access permits; never force-push `main`. Record commit/PR URL. Summarize operational integrations and exact blockers. **Stop after delivery.**


---

# OPTIONAL PROMPT 19 — Add Reddit and Farcaster sources after the core system works

Run only after Phase 18 is accepted, or earlier only if there is a proven research-critical requirement. Read EXECUTION/ROADMAP/DECISIONS/HANDOFF; inspect actual connector contract and official/authorized Reddit and Farcaster API options, including current limits and rights. Keep these as two distinct adapters; if one is blocked, complete and test the other rather than creating empty stubs.

For Reddit, support selected approved communities and submissions/comments with canonical IDs, parent relations, edited/deleted states, rate limits, cross-post provenance and enough context to distinguish independent threads from cross-post amplification. For Farcaster, support the available approved cast/channel APIs and recasts/replies, with stable identifiers and social identity/provenance. In both, conform to the Phase 02 normalized event schema and data minimization controls; do not ingest private messages or bypass terms.

Deliver adapter-specific fixtures and tests; run one source-to-storage-to-claim-to-narrative report flow for each functioning adapter. Add connector cost/health status and precise setup instructions. If permission unavailable, mark blocked without claiming operational status. Update docs and handoff, commit if authorized; **stop**.


---

# OPTIONAL PROMPT 20 — Add compliant Discord community monitoring

Run after Phase 18 unless priority and access justify earlier execution. Read durable handoff and inspect official Discord gateway/API docs and privileged message-content-intent rules. Confirm bot installation and permissions for selected servers/channels. Never assume a public invite grants programmatic collection rights. Never attempt private-message access or token-based self-bot scraping.

Implement permitted server/channel observations with channel IDs, message IDs, author/account, reply thread, edits/deletions when observable, UTC publication and ingestion times, forwarding/link provenance and allowed content retention. Rate-limit and permission-denied handling must be correct and connectors must report missing privileged intent clearly. Integrate into the existing normalized ingestion, token resolver, claim extraction and narrative feed; do not introduce a second social schema.

Test channel permission revocation, intent missing, duplicate gateway events, message edits, quote/link duplication, out-of-order events, reset checkpoint, no available text and no-source day. Demonstrate a full fixture flow. Live demonstration only with authorized guild and configured bot. Commit tests/docs, update handoff, **stop**.


---

# OPTIONAL PROMPT 21 — Add YouTube metadata and public captions when permitted

Run after Phase 18 unless a verified high-value analyst relies substantially on public long-form content. Read handoff and verify official YouTube Data API, available captions/transcript access, quota terms and content retention rights. No prohibited downloads or fictional transcription access.

Implement authorized channel/video metadata ingestion and transcript snippets where access is legally/technically allowed. Preserve video ID, channel, published time, caption/transcript time offsets, source link/timepoint and quotation context. Do not mistake video publication time for a claim's exact spoken timestamp when transcripts are unavailable; never evaluate a prediction using a future livestream transcript prior to its broadcast. Add verified extracted token mentions, attribution and narrative relevance through current pipeline. Focus on periodic contextual intelligence, not real-time launch detection.

Test multi-token mentions, missing captions, delayed livestream archiving, timestamp drift, channel/video dedupe, language/translation uncertainty, YouTube quota failure, and unavailable authorized transcripts. Demonstrate source-to-report fixture path and, only when permitted, an authenticated public-data smoke test. Document costs and limitations, update handoff/commit, **stop**.

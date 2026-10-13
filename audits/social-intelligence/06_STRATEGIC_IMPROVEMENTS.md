# Phase 06 — Strategic Improvements: Is This Intelligence Actually Useful?

**Audit date:** 2026-10-13 (America/New_York)  
**Repository:** https://github.com/RyzinEnagy/memelab-inbox  
**Code baseline:** \`main\` @ \`698f73b854567ce60b56ce275b5ab6822a9d5f60\` (Phase 00). Optional \`feature/social-intelligence\` @ \`3f27fc788f9ab88286b8041355e5445fdfdf012c\` reviewed only as distinct, unmerged expansion.  
**Scope:** Product, research validity, costs, architecture and current alternatives. **No production code changed; no real-money trade, API activation or live proof-of-alpha experiment.**  
**Verdict: REFOCUS / CONDITIONAL CONTINUE. No approval for unattended release or claims of predictive alpha.**

## 1. Executive assessment

The lab has a substantive, fixture-tested offline social intelligence *framework*. It has **not** demonstrated that it delivers reliable daily research, beats existing dashboards at identifying tradeable opportunities, or identifies skilled analysts. This is a distinction between a built component, a working service, and a measured investing advantage.

The defensible product opportunity is **not** a second trending list. It is a tightly evidenced research brief:

> An *independent, timestamped* source made this contract-specific assertion before mainstream attention; other genuinely independent sources did or did not corroborate it; the chain and trading venue did or did not confirm the relevant behavior; large holders did or did not distribute; and the investor's specific position size could or could not have been exited at a plausible net price.

That statement is a **hypothesis for forward testing**, not demonstrated current capability. Good early information can still create a bad trade when the exit is thin or promotion is late-stage.

**Decision:** first repair the causal data and operational path; then test a small monitored universe against simple commercial/free alternatives; add features only when prospective evidence establishes *incremental* decision value per dollar and hour.

### Core strengths to preserve

Exact chain+contract identity; provenance and explicit refusal; separated private text; explicit repost/amplification counts; reviewed source and wallet *assertions*, not identity certainty; supplied-ledger fee/lot accounting; chronology and immutable evaluation scaffolds; matched controls; content safety boundaries and dry-run capped alerts. These are credible components, not a reason for a wholesale rewrite.

### Evidence-blocking issues

| Problem | Consequence | Existing finding |
|---|---|---|
| X/Telegram ingestion does not automatically hand source text into extraction and token resolution | Raw posts cannot reliably become contract-linked claims or reports | AUD-003/014, ARCH-003 |
| Historical narratives/feed/replay may use evidence learned after the decision cutoff | Invalid apparent lead time, trader quality and backtested signals | AUD-001/002/015/017, ARCH-001 |
| Fixture observations exported as apparently real alpha input | Synthetic demonstrations can contaminate research outcomes | AUD-004 |
| Capped pagination and iterator exceptions lose completeness or leave false RUNNING states | "No signal" may mean "not collected" | AUD-005/016, OPS-002 |
| Automatic scheduling, whole-state backup and signal/outcome recording are not established | Not a proven seven-day unattended intelligence service | AUD-007, OPS-001/003 |
| Full real-world outcomes, trader wallet ledgers, historical price and sell depth unavailable | No valid best-trader claim or demonstrated realistic profits | AUD-008/012, OPS-008 |
| Budget/erasure/private-content and release controls incomplete | Paid or live operation requires safety and recovery remediation | AUD-006/009/010/011, ADV-001–009 |

The baseline main test result **651 passed / one failed** and fixture release **45/45** were previously executed; Phase 01 separately reported **17 independent passes / five failures**. None constitutes a new test in this Phase 06 or proof of live efficacy.

## 2. Original purpose versus present utility

**Intended outcome:** early, credible information; differentiation between organic narrative emergence and paid/copy amplification; evidence-driven trader discovery; on-chain corroboration; actionable liquidity/risk context; concise research and alerts; followed by honest outcome measurement.

**What the code presently supports:** structured local observation/provenance, opt-in provider adapters, token identity and extractors under supplied-text/test conditions, deterministic narrative clustering, registry and wallet hypotheses, experimental scoring, feed/report formatting, alerts in dry run, retrospective/replay and forward-outcome scaffolds. Feature branch adds additional mostly fixture-tested platforms, *not* validated main deployment.

**What remains unproved:** continuous paid/authorized source collection; complete automated pipeline; same-time on-chain confirmation; investor-specific fill simulation; calibrated source predictions; independent narrative attribution against syndication; earlier *useful* discovery versus baseline; less time spent; cheaper completed research decisions; repeatable unseen-period alpha.

**Architecture principle:** preserve the offline engine; eliminate unreliable gaps, unnecessary provider breadth and redundant front-end presentations. The objective is one evidence-backed answer for a person, not the maximum number of component interfaces.

## 3. The actual investor-facing workflow

Deliver **3–5 research cases a day** (and zero when nothing *qualifying* appears), with drill-down evidence rather than a wall of repeated posts. Each case should answer, in under five minutes:

1. **What was first observed?** Exact chain/mint, proposition and *system-known* timestamp; source URL, source-type, original versus forward.
2. **Why does the source merit attention?** Claim-type-specific verified history, uncertainty, corrections, financial conflicts, source coverage.
3. **Who independently corroborated it?** Explicit original/quote/forward/copy/affiliation edges; explain independence confidence rather than just count mentions.
4. **What contradicts or confirms it?** Evidence matrix: original assertion, independent proof, on-chain fact, conflicting fact, missing/late evidence.
5. **Am I early or late?** First *independent* attention, price/volume already moved, paid boosts, concentrated insider selling and LP changes.
6. **Can I enter and get out?** Authorities, Token-2022 transfer restrictions/fees, LP controller, venue liquidity and size-specific live sell quotes (or NO QUOTE).
7. **What do I do with this research?** Research-worthiness (not buy instruction), invalidation/expiry and a follow-up signal; what would change the judgment.

Make the data-coverage envelope visible on every day: monitored sources, source endpoints reached, gaps, oldest backlog, ingested posts, classified posts, token-resolved posts, timestamps, quote-age and missing capabilities. Distinguish **COMPLETE NO QUALIFYING SIGNAL** from **PARTIAL/STALE/NOT MONITORED**.

## 4. Current alternatives and build-versus-buy investigation

Vendor claims and prices below were checked against the linked primary pages on 2026-10-13. No competitor account was operated and **no vendor's accuracy was independently validated**. Eligibility, terms, redistribution and pricing can change. The point is to avoid reinventing commoditized functionality.

| Existing tool | What it already supplies | Strategic choice | Important limitation |
|---|---|---|---|
| [DEX Screener API](https://docs.dexscreener.com/api/reference) | Batched token/pair data, price, volume, liquidity, market cap, boosts and paid-ad information; documented 60/300 req/min API groups, up to 30 contract addresses on a token lookup | **Reuse as default trending/market baseline** | Displayed pool liquidity is *not* executable sell-side depth; promoted visibility is not organic adoption |
| [GMGN](https://gmgn.ai/) / [Wallet Radar docs](https://docs.gmgn.ai/index/wallet-radar) | Trending new coins, wallet P&L/earliest buying/shared holdings, active-wallet discovery and alerts | **Benchmark** wallet/trader and discovery utility before building more | Vendor profitable-wallet label is not proven skill or complete person-level P&L; exclude copy-trade/execution |
| [Bubblemaps V2](https://v2.bubblemaps.io/) | Token holder-distribution and link visualizations | **Use for targeted manual cluster review** | Edges and shared funders are not proof of one individual or coordinated intention |
| [Nansen Pro](https://academy.nansen.ai/en/help/articles/9412804-about-nansen-pro) | Smart-money labels, P&L, portfolios and alerts; vendor lists **$49/mo annual** or **$69/mo monthly** | **Consider a controlled trial only if wallet analysis time dominates** | Chain/contract coverage, export rights and comparison quality need testing |
| [Kaito](https://www.pro.kaito.ai/portal) | Social attention, narrative/mindshare and voices rankings | **Use as social attention baseline** | Mindshare ≠ independent origins, truth, early tradeability or future returns |
| [Jupiter Swap V2](https://developers.jup.ag/docs/swap) | Route competition and read-only quote information including \`/swap/v2/order\` | **Use route quotes for finalist sell-size stress tests** | A quote is not an executed fill, may require API access and may expire; never sign or submit |
| [Helius](https://www.helius.dev/pricing) | Solana RPC/webhook/enhanced history; **1M free monthly credits**, Developer **$49/mo for 10M** | **Narrow watchlist/on-demand corroboration** | Not necessarily complete historical cost basis; method credit weights and limits vary |
| [Birdeye API](https://docs.birdeye.so/docs/pricing) | Market/token feeds; listed Lite **$39/mo**, Premium **$199/mo** | **Trial only for missing historical/live data** | Can duplicate data already accessible elsewhere; CU and streaming access differ |
| [GeckoTerminal/CoinGecko API](https://docs.coingecko.com/reference/top-pools-contract-address) | Pool snapshots and historical on-chain market coverage | **Secondary provider disagreement checks** | Aggregated liquidity/volumes are not exit quotes |
| [RugCheck](https://rugcheck.xyz/) and [open-source RugScoreBot](https://github.com/SoCloseSociety/RugscoreBotTG) | Risk-screening flags and reference implementation integrating APIs | **Reference, do not outsource safety judgments** | "Safe" labels cannot replace on-chain authority/LP review |
| [Solana Token Observatory, open source](https://github.com/0bLad20x/solana-token-observatory) | Discovery/candidate-retirement pattern | **Study implementation patterns only** | Quality, maintenance, licensing, attack surface unverified |

### What should remain proprietary to this research tool?

**Own:** causal evidence ledger, source originality/dependency evaluation, adjudicated claim accuracy, contracts and market facts joined by known-at time, personal position-size feasibility, comparative forward-testing, decision triage.  
**Reuse:** raw market dashboards, pool discovery, quote routing, standard on-chain parsers, subscription transport, and visual holder inspection where license permits.

**Differentiation threshold:** if removing the bespoke claim/origin/causal layers does **not** reduce blind, fixed-attention research performance compared with commodity dashboards, the custom engine adds complexity without measured value.

## 5. Recommendations — A. Essential corrections

Every card specifies **expected benefit, evidence, complexity, operating-cost effect, risk, dependencies, measurement**. Complexity: **L** localized, **M** several integrated modules, **H** cross-module data-model/verification changes. Cost changes are hypotheses, not bills.

### STR-A01 — Consistent event-time and knowledge-time across all reads
**Benefit:** Eliminates fake foresight in past claims, corroborations, price candles, wallet assertions, reports and experiments. **Evidence:** AUD-001/002/015/017 and ARCH-001; historical read invariants already failed independent tests. **Complexity:** H. **Cost:** Moderate version storage/read overhead; negligible third-party spend. **Risk:** Backfilled rows with unknown availability cannot be safely promoted to known; score comparability may break. **Dependencies:** Immutable observation/extraction/run provenance, source/ingest/review/quote clocks, migration and publication manifest. **Success:** Recompute an earlier knowledge cutoff after arbitrarily adding future extractions, approvals, prices and identity changes; output identical. All selected dependencies must have availability <= cutoff. Test the *database-to-replay* export, not merely synthetic input replay.

### STR-A02 — A single live-source-to-cited-claim-to-report vertical slice
**Benefit:** Finally converts X/TG collection into usable intelligence. **Evidence:** AUD-003/014, ARCH-003, Phase 01 X source scenario. **Complexity:** H. **Cost:** A small selective extraction budget; cheaper than expanding into more platforms. **Risk:** Leakage of licensed/private text, duplicated jobs, poisoned model responses, processor interruption. **Dependencies:** Per-source consent/retention; safe in-memory or private-store text handoff; idempotent outbox; contract resolver; coverage states; no public raw post text. **Success:** One authorized source observation travels through token identity, extracted claim, independent narrative, on-chain check, report, alert dry-run and later outcome with *one traceable evidence chain*; repeated retries neither duplicate nor lose it.

### STR-A03 — Hard provenance, status and eligibility gates
**Benefit:** Synthetic, stale and incomplete data can no longer masquerade as real trader skill. **Evidence:** AUD-004/008, OPS-002/006, ARCH-009. **Complexity:** M–H. **Cost:** Small lineage storage and labeling workload. **Risk:** Increased abstention disappoints users; that is preferable to false confidence. **Dependencies:** Typed COMPLETE/PARTIAL/STALE/UNKNOWN/FIXTURE status; source, model and quote versions; fixed source universe. **Success:** Mixed real+fixture stores cannot yield a "real" alpha score; every published conclusion includes its coverage denominator, evidence IDs and known limitations.

### STR-A04 — Safe contiguous cursors, failures and recoverable state
**Benefit:** Prevents skipped earliest mentions and falsely clean reports. **Evidence:** AUD-005/016, ARCH-004/005/010/011, OPS-001/002/003. **Complexity:** M–H. **Cost:** More bounded retry reads/backup space; less waste from unrecoverable jobs. **Risk:** Retried pages can increase billable API usage; concurrent workers can duplicate action without idempotency. **Dependencies:** Separate head/backlog watermarks, acknowledgment-based advancement, terminal error statuses, watchdog, whole-system encrypted restore. **Success:** Two capped pages, 429, thrown iterator, power-loss recovery and a day of missing schedules eventually reconcile all eligible items with no unreported gaps, duplicated alerts or lost ledger entries.

### STR-A05 — Trade-viability screening and realistic size-specific exits
**Benefit:** Avoids describing a high-performing *price chart* as an executable opportunity. **Evidence:** AUD-012, existing Chapter 1 liquidity/price-impact curriculum, Jupiter V2 documentation. **Complexity:** M–H. **Cost:** A few read-only router queries/RPC reads per *finalist*; never a full-universe route crawl. **Risk:** Quote does not ensure fill and quote-to-alert latency matters; router may omit venues. **Dependencies:** Correct chain/mint, Token-2022 fee/mint/freeze controls, LP controller, pool coverage, candidate size and quote timestamp. **Success:** Publish candidate-size net exit proceeds and slippage stress for $250/$1k/$5k/$25k *where appropriate*, plus fees/NO QUOTE. Flag non-executable outcomes rather than omitting failed exits. No transaction execution.

### STR-A06 — Safety, budget and release truth before paid unattended use
**Benefit:** Prevents preventable data/billing loss and false release assurance. **Evidence:** AUD-006/009/010/011, ADV-001–009, OPS-003/004/010, ARCH-002/013/014. **Complexity:** M–H. **Cost:** Some backup/monitor overhead; caps reduce spending tail exposure. **Risk:** Strict safeguards constrain optional integrations, implementation could introduce migration bugs. **Dependencies:** Strictly positive verified prices for paid APIs, atomic reservation/reconciliation, per-connection SQLite FKs, private data lifecycle including deleted X, full restore, one pinned deploy ref, green suite. **Success:** Fake-paid concurrent budget exhaustion cannot exceed caps, no unauthorized published text, delete/purge proofs, multi-store restart/restore, zero unresolved suite failures and a seven-day supervised-to-unattended readiness trial.

## 6. Recommendations — B. High-value improvements

### STR-B01 — Forward test against same-time simple baselines
**Benefit:** Demonstrate or falsify incremental early-detection and decision advantage. **Evidence:** AUD-008/OPS-008, existing replay scaffold and DEX Screener/GMGN/Kaito coverage. **Complexity:** H. **Cost:** Targeted historical snapshots, user adjudication; modest compared with indiscriminate ingestion. **Risk:** Winner selection, changing eligibility, p-hacking, late/delisted assets excluded. **Dependencies:** A01–A05, fixed cohort/alerts, execution model, real outcome feed and baseline snapshots. **Success:** Pre-register and run prospective 30/60/90-day evaluation comparing precision@5, correct tradeable lead time, downside, research minutes, cost and paired intervals. Insufficient sample = INSUFFICIENT DATA.

### STR-B02 — Independent-origin/propagation graph
**Benefit:** Differentiates three genuinely unrelated originators from twenty accounts repeating one marketer. **Evidence:** \`NARRATIVES_07.md\` already collapses explicit reposts but cross-platform quotes, copy-paste and disclosed paid affiliations extend beyond its deterministic edges. **Complexity:** M–H. **Cost:** Low fingerprinting plus small selective language evaluation. **Risk:** False common-control inference and overmerging; common funding/platform does not prove identity. **Dependencies:** First-seen provenance, text fingerprints where permitted, quote/repost/publisher relationships and human-reviewed edges. **Success:** Blinded set of repost/quote/paraphrase/sponsored/independent examples; report independent-origin precision/recall, overmerge/undercount rates and unproven relationships.

### STR-B03 — Claim-type-specific credibility and misinformation review
**Benefit:** Recognizes technically accurate niche analysts, retractions and bad factual claims rather than rewarding followers. **Evidence:** \`REGISTRY_08.md\` registry and ranking scaffolds but no real validated elite list (AUD-008). **Complexity:** M–H. **Cost:** Modest model + nontrivial human labeling; likely more valuable than extra raw post spend. **Risk:** Small samples and missing deleted calls produce biased certainty; false accusations. **Dependencies:** Ex ante claim corpus with outcome eligibility, corrections, sponsored/affiliated status, accuracy categories, named evidence and label adjudicators. **Success:** Category-specific probabilistic calibration/Brier score, error bars, retraction capture and reviewer agreement; no "misinformation" determination without checkable contradiction.

### STR-B04 — Promotion-stage and distribution evidence
**Benefit:** Identifies when supposed new attention is a late campaign or an exit-liquidity opportunity for early holders. **Evidence:** DEX paid boosts, narrative mechanics, Phase 1 on-chain distribution concepts; present integration and timing unvalidated. **Complexity:** M–H. **Cost:** Targeted additional on-chain sampling per finalist. **Risk:** Genuine virality can resemble a paid burst; flat price is not proof of absorption. **Dependencies:** B02, onchain wallet/LP event classification, boosts timestamps, price and volume history at known time. **Success:** Labeled early-organic vs amplified vs late-distribution case set, precision of warning/contradiction, lead relative to adverse liquidity events, and false alarms in legitimate social adoption.

### STR-B05 — On-chain fact-check ledger keyed to each social proposition
**Benefit:** Prevents vague "whales agree" assertions and reveals which specific claim is supported. **Evidence:** Existing wallet evidence/chronology components and ARCH-006 chain-join risk. **Complexity:** M. **Cost:** Lower if checks run only on filtered cases; higher if every post triggers a full wallet scan. **Risk:** Mistaking a transfer or wallet funding for an executed purchase/sale; custody addresses misread as people. **Dependencies:** Chain+mint identity, claim predicates, quote/swap and ownership/LP event labels, causal clocks, data completeness. **Success:** Blind reviewer can trace every factual statement to exact transaction/pool/reference and timestamp; missing evidence reads UNKNOWN; no transfer alone called a sale.

### STR-B06 — Overlooked analysts via out-of-sample discovery
**Benefit:** Finds credible specialists not already featured on popularity rankings. **Evidence:** Existing registry candidate import is fixture-only; Nansen/GMGN/Kaito already expose leaderboards and attention. **Complexity:** M. **Cost:** Controlled candidate reviews; resource spend caps. **Risk:** Many tested accounts yield lucky winners; identity and deleted post coverage. **Dependencies:** B03, discovery history, shrinkage, unseen holdout periods and comparison to popularity-matched sources. **Success:** Verified new source yield/100 reviewed accounts and stable out-of-time credibility lift, rather than a top caller's biggest cherry-picked return.

### STR-B07 — Optimize user attention rather than number of alerts
**Benefit:** Reduces cognitive load; makes the existing daily-cap alert engine useful to a person. **Evidence:** Cap/dedup already works in fixtures but no measured alert usefulness (OPS-008). **Complexity:** L–M. **Cost:** Lower transport and model use if prioritization works. **Risk:** Harsh filtering could miss novel important risk; reserve sampling for discovery. **Dependencies:** A03 coverage; novelty, source independence, risk severity and explicitly user-selected universe. **Success:** Blind precision@3/5, nonredundant case rate, user time-to-judgment, misses in a random audit sample and rate of critical warnings shown.

### STR-B08 — Credible trader skill versus luck and paper profit
**Benefit:** Avoids elite labels on a few big wins or truncated wallets with unsellable positions. **Evidence:** Phase 10 lot/P&L scaffolds, AUD-008/012, Phase 17 dependence caveats. **Complexity:** H. **Cost:** Potentially expensive archival wallet/quote history; shortlist only. **Risk:** Survivorship, unknown starting inventory, missing swaps, wallet != person, correlated meme episodes. **Dependencies:** A01/A05, complete wallet transaction/fees history or abstention, unique opportunity cluster, delisted losers, liquidity stress, out-of-time test. **Success:** Effective independent bet sample, shrinkage/credible intervals, stability by period and market regime, matched popularity/naive baseline, and executable-return sensitivity.

## 7. Recommendations — C. Architectural simplifications

### STR-C01 — Retain SQLite modular monolith and add only a small outbox
**Benefit:** Reliable scheduling/recovery without unnecessary distributed streaming technology. **Evidence:** ARCH-005/011, substantial existing SQLite migrations; no measured scaling need. **Complexity:** M. **Cost:** Low and often less maintenance than Postgres/Kafka/cloud orchestration. **Risk:** Heavy concurrent writers may saturate SQLite; measure first. **Dependencies:** A02/A04, consistent connection factory, transactions, durable host and private backup. **Success:** Queue drains with repeated crashes at realistic daily volume, measured p95 latency, successful restore and zero unacknowledged item loss.

### STR-C02 — Shared source lifecycle interface, optional-provider deferral
**Benefit:** Stops new adapters from adding divergent pagination, text handling and failure states. **Evidence:** ARCH-012, AUD-013 optional Discord live transport absent; X/TG main pipeline still broken. **Complexity:** M. **Cost:** Less source maintenance/paid integration. **Risk:** Overgeneric abstraction can hide provider-specific deletion/rate limits. **Dependencies:** A04, contract fixtures for new/edit/delete/retry/health and rights-specific extensions. **Success:** Same negative fixture suite passes across two existing connectors; any new source must demonstrate distinct source/lead-time yield before enabling.

### STR-C03 — Cheap deterministic prefilter, expensive checks only for finalists
**Benefit:** Greater research value per charged resource. **Evidence:** DEX Screener batch/free market endpoints; X **$0.005/post read** and Helius free tier; OPS Phase05 modeled **$7.77/$77.75/$826.45** a month at 100/1k/10k total posts/day (assumption-driven, NOT invoices). **Complexity:** L–M. **Cost:** Potentially material reduction in X reads; ten thousand avoided chargeable reads = **$50**, if charging is per stated unit with no other effects. **Risk:** Cheap classifier can miss a valuable fresh narrative; keep an exploration sample. **Dependencies:** C02 resource billing/provenance, source scope, local dedup, sample-based recall audit. **Success:** Dollars per correctly researched new case, total billed posts, detected useful cases, timeliness and false-negative tradeoff at fixed monthly budget.

### STR-C04 — One investor case view over existing separate evidence modules
**Benefit:** Reduces duplicate feed/report/digest effort while preserving distinct provenance and wallet review semantics. **Evidence:** ARCH-015 says superficially duplicated wallet tables encode materially different stages; report formats exist. **Complexity:** L–M. **Cost:** Mostly maintenance reduction. **Risk:** Collapsing inferred/reviewed/verified records into one field destroys truth distinctions. **Dependencies:** Stable case ID and data dictionary. **Success:** One coherent summary with drill-down citations, no inconsistent verdicts between report surfaces, all old evidence IDs recoverable.

## 8. Recommendations — D. Advanced optional capabilities

### STR-D01 — Controlled semantic narrative retrieval
**Benefit:** Group indirectly worded but substantively related claims. **Evidence:** Deterministic grouping deliberately limited in \`NARRATIVES_07.md\`. **Complexity:** H. **Cost:** Higher model/embedding/retention expense. **Risk:** Semantic false merges, wrong-ticker grouping, prompt manipulation. **Dependencies:** B02 gold labels and strict contract identity with human override. **Success:** Held-out lift in narrative accuracy **without** worse independent-origin false collapses or unsupported contract matches.

### STR-D02 — Cross-social/onchain coordination network as a hypothesis tool
**Benefit:** Earlier discovery of suspicious promotion + insider-flow patterns. **Evidence:** Existing clustering/registry and on-chain metrics, but no verified real coordinated detection. **Complexity:** H. **Cost:** Additional wallet event indexing and review. **Risk:** Shared funder or address does not prove one human, and algorithmic correlation risks defamation. **Dependencies:** B02/B04/B05, evidence-scored graph edges, explainability/reviewer override. **Success:** Pre-adjudicated precision at a limited review budget and false alert reduction versus simple aggregate rules.

### STR-D03 — Adaptive selective analysis after prospective outcomes
**Benefit:** Spend scarce reads/LLM calls on cases with the most expected decision value. **Evidence:** No valid real training labels yet (AUD-008), so advanced personalization now would be speculative. **Complexity:** H. **Cost:** Training/monitoring overhead; possibly saves inference if trial proves it. **Risk:** Feedback loops, model drift, suppression of novel categories. **Dependencies:** B01/B07 prospective labels and random exploration. **Success:** Out-of-period improvement in value per dollar with unchanged critical warning recall versus deterministic rule.

## 9. Recommendations — E. Remove/deprecate or explicitly disable

### STR-E01 — Hide unvalidated "best trader", "alpha" and "safe" badges
**Benefit:** Prevent false precision in high-risk speculative decisions. **Evidence:** AUD-008/012; replay real-data INSUFFICIENT DATA. **Complexity:** L. **Cost:** Less pointless refreshed scoring. **Risk:** Fewer visually attractive rankings; allow transparent experimental analyst worksheets. **Dependencies:** B01/B03/B08 validation for any reinstatement. **Success:** No real-money skill/safety claim without denominator, uncertainty and executable outcome coverage.

### STR-E02 — Defer Discord Gateway and broad-platform expansions
**Benefit:** Focus developer time and budget on a working X/TG causal pathway. **Evidence:** AUD-010/013; optional feature branch is not main, Gateway live transport not shipped. **Complexity:** L to defer. **Cost:** Lower upkeep/paid read obligations. **Risk:** Missing unique platform-specific originators. **Dependencies:** A02/A04 core gates; B01 incremental-source study. **Success:** Only expand if a platform delivers distinct independently corroborated early cases per dollar and hour.

### STR-E03 — Retire pure trending duplication and low-value mass-alert surfaces
**Benefit:** Focus on what DEX Screener, GMGN and Kaito do not already provide. **Evidence:** Current competitor capabilities; incremental custom value unmeasured. **Complexity:** L–M. **Cost:** Likely reduced calls and alert noise, amount not measured. **Risk:** Lost awareness if baseline comparison omitted. **Dependencies:** B01 equal-budget control and B07 missing-important-signal audit. **Success:** Remove feature only when blinded evaluation shows no material reduction in useful research cases, timeliness or safety warnings.

## 10. How to tell a skilled analyst from a lucky analyst

- Define an **eligible prediction before outcome**: specific token mint, direction or testable thesis, action timestamp, horizon, stated uncertainty and whether the post was promotional, explanatory, retrospective or conditional. Refuse to score vague hindsight posts as trades.
- Include **every eligible call and abstention**, not only the analyst's best trades. Recover reasonable coverage of losses, failed launches, delisted tokens and source deletion/selection uncertainty. Report denominator.
- Apply **hierarchical/Bayesian shrinkage or conservative empirical-Bayes intervals** for tiny samples; count *independent market opportunities*, not twenty related wallets buying the same meme as twenty forecasts.
- Separate **technical factual expertise**, **narrative discovery timing**, **market direction accuracy**, **realistic executable returns**, and **wallet execution skill**. A trader can be informative without operating a profitable wallet.
- A wallet is not necessarily its public speaker. Signature verification can support address control at a time; shared funding or asserted identity alone does not prove lifelong person-level authorship.
- Measure future periods and distribution shift; use matched analyst controls and correction/resurfacing behavior. Rank "insufficient evidence" where appropriate.

## 11. Narrative independence and misinformation: required evidence model

For each signal preserve \`chain\`, \`contract\`, \`claim_id\`, \`claim_kind\`, \`source_id\`, \`original_item_id\`, \`source_posted_at\`, \`ingested_at\`, \`extracted_at\`, \`evidence_known_at\`, \`model_version\`, \`source_status\`, \`dependencies\`, \`content_hash\`, \`review_status\`, \`sponsor_disclosure\`, \`onchain_observation_id\`, \`market_quote_id\`, \`alert_at\`, \`outcome_id\`.

Separate **observed fact** (transaction swapped tokens), **attribution hypothesis** (wallets potentially related), **market inference** (cluster may be distributing) and **unsupported interpretation** (one person orchestrated a dump). Reposted, syndicated, purchased, interlinked and same-funder sources should receive separately reviewable evidence edges; do not automatically collapse all shared hosting or funding into one person. Distinguish contradiction from unverified, expired and subsequently corrected claims.

**Examples for adversarial adjudication:**
- Five identical posts share the same screenshot but no native repost tag → one likely originator and four propagation events pending evidence; *not* five independent confirmations.
- A token's creator wallet transfers to an exchange address → **potential selling**, not proof of sale; verify the swap or the custody route.
- Three apparently unrelated analysts make the same contract claim but the recorded upstream source is one Telegram channel → "multiple mentions, one known source origin" rather than consensus.
- A 30× paper wallet gain in a thin pool → do not call realized trader alpha until lot completeness and hypothetical executable depth are known.

## 12. Prospective experimental design: how incremental value can be demonstrated

**Preregister** the source universe, chains and candidate token cohort, prediction types, score algorithms, user review quota (e.g. five cases/day), market cutoff rules, lag assumptions, allowed risk flags, costs, position size, alert timing and outcome horizons *before* seeing later returns. Version changes; changed policies get new trial arms.

**Include the denominator:** eligible source posts, failed resolutions, dropped/deleted tokens, failed quote/no-route assets, losers and no-claim observations. Never benchmark only the successful alerts or token survivors.

**Run shadow baselines at the same wall-clock cutoff:**
1. DEX Screener newly trending/boosted markets; contract-matched.
2. Same market baseline with identical standard risk filters.
3. Basic notable-wallet activity baseline.
4. Lab's verified source+independence+claim+onchain insight.
5. Optional licensed Kaito/Nansen/GMGN data if accessible and economically justified.

Store the **contemporaneous state of each baseline**, not later reconstructed rankings; match alerted research items per day and chain/market-cap strata. Realistically include communication and human reading latency. Entry can occur only after *all required information was available*: \`max(ingested,extracted,chain_check,alert_received)+decision_delay\`. Use price candles completed at the decision point, not their future close. Record size-specific live router quote and sensitivity; if actual historical quotes unavailable, call the result MODELED with conservative limitations, not an executed return. Do not delete non-executable cases.

**Primary outcomes:** correct and tradeable *lead time versus baselines*, blind precision@5, independently verified positive/negative claim outcomes, false-warning rate, research minutes saved and $/useful case. **Secondary:** risk-adjusted execution-model results, drawdown/MAE, quote-error/staleness, lead-time distributions, robustness to quote size, tax and zero liquidity.

**Statistics:** analyze correlated exposures by independent token/narrative/market-day groups, not post-level pseudo-samples; time-embargo windows at least as long as maximum overlapping prediction horizon; split training/validation/test chronologically; paired group/block bootstrap uncertainty, multiple-test corrections for analyst hunting, regime analyses and clearly reported missingness. Require frozen policy and untouched holdout.

**Practical decision gates (proposed; NOT claims of future success):**
- **Engineering:** seven-day clock-injection/restart run closes every authorized source job; deliberate 429/timeouts and missing scheduler are visible; all causality/fixture/quote invariants hold, no privacy or cost violation.
- **Research:** 30-day shadow collection to understand data completeness and calibration, then 60–90-day prospective trial if sample is sufficient; explicitly "insufficient data" when not powered.
- **Product:** measurable improvement over equal-budget free-baseline research and user blind review, with fewer false alerts or lower time/cost; no hidden deterioration in critical risk recall.
- **Investment:** never promise profitable outcomes based on a small sample or assumptions; no real trading required. If no incremental advantage is supported, keep as a **research organizer** rather than marketing it as alpha.

## 13. Cost, risk and operating model

[The X developer platform](https://developer.x.com/?lang=en) currently lists **$0.005 per post read** and **$0.010 per user read**. At ten thousand *actually billed* post reads, the direct post-reading component is $50, excluding retries, user lookups, provider subscriptions and local processing. [Helius](https://www.helius.dev/pricing) lists a free 1M-credit tier and $49/mo developer; [Birdeye](https://docs.birdeye.so/docs/pricing) lists free, $39 Lite and $199 Premium; [Nansen](https://academy.nansen.ai/en/help/articles/9412804-about-nansen-pro) lists $49 monthly when billed yearly or $69 monthly. Prices do not guarantee account eligibility. The Phase 05 cost model's $7.77/$77.75/$826.45 monthly figures reflect **hypothetical** 100/1,000/10,000 posts/day with *half* paid X reads, *30%* short model calls, and an assumed Helius tier. Do not treat as invoices or caps.

**Most economical meaningful pilot:** 20–50 authorized, deliberately curated source accounts; small discovery exploration cohort; batched DEX market context; one supported chain first (Solana) without deleting existing other-chain functionality; targeted Helius/onchain checks only on independent high-value claims; cheap deterministic exact contract/duplicate filtering; model calls selectively; route quotes for a few finalists; daily brief plus exceptional warnings. A single persistent SQLite host plus supervised scheduling, safe secret separation and tested encrypted backup suffices until load measurements prove otherwise.

**Investor risk guardrails:** Verify full mint/token mechanics and LP control, exchange/custody wallet classification, concentration/linked clusters, current and **executable** sell-depth, slippage + transfer fees, route failure, and the possibility that the alert is a late sponsored burst. A valuation/liquidity ratio is a useful filter, not a cash exit. Mark wallet cluster inference and each unavailable risk fact; uncertainty never means safety.

**Costs to measure rather than guess:** billed reads (including repeat requests), model usage, cache/rights limits, fallback provider queries, quotes requested, false alerts/day, manual maintenance minutes, backend hosting, storage/backup growth, and the incremental **cost per independently useful decision**.

## 14. Ordered strategy gates / stop rules

| Gate | Build only after previous gate passes | Evidence to accept | Stop/abstain if |
|---|---|---|---|
| G0 Truth | A01/A03, original test failure repair and adversarial temporal negatives | Same past answer after future database changes; fixture never becomes real | Any future-known input contaminates history |
| G1 Workflow | A02/A04/A06, one actual authorized vertical slice | End-to-end same evidence IDs, complete cursors, safe pricing, backup/restart | Posts ingested but absent from token claims |
| G2 Risk clarity | A05/B05/B07; an explainable 5-minute case view | Traceable claim vs transaction and quote-based exit/no-route | Missing data renders as "clean" |
| G3 Value | B01/B02/B03/B04/B08 with locked baselines | Sufficient unseen prospective examples and credible utility/cost intervals | No measurable difference versus existing tools |
| G4 Optional expansion | B06/C02 then selected D-class ideas | New source/model measurably improves *independent* correct leads per $/hour | Mere extra mentions or source count |

**STOP:** This phase is strategic analysis only. It neither fixes nor certifies defects, activates paid providers, sends notifications, deploys services nor trades.

## 15. Traceability and limitations

**Independent archive examined:** Phase 00 \`00_BASELINE.md\`, \`REQUIREMENTS_MATRIX.md\`, cumulative \`FINDINGS.md\` and latest available Phase 05 \`FINDINGS(5).md\`, \`01_FUNCTIONAL_AUDIT.md\` evidence as recorded in findings, \`02_ARCHITECTURE_AUDIT.md\`, \`04_ADVERSARIAL_AUDIT.md\`, \`05_OPERATIONS_AND_UX.md\`. The Phase 03 primary report was not available; any Phase 03 candle timing concern remains a *secondary* report requiring reproduction. Earlier audit records are in the project's file archive, not in the pinned repository; this deliverable creates the requested \`audits/\` path on a documentation-only review branch.

**Code/doc inspection:** \`docs/social-intelligence/{README,ARCHITECTURE,OPERATIONS,ALPHA_11,NARRATIVES_07,REGISTRY_08,REPLAY_17,SOURCE_COVERAGE,ROADMAP}.md\` and \`memelab/social/{feed_core,alpha_core,narratives,extraction}.py\`, plus repository metadata/tree and earlier auditors' executed evidence. This phase did not rerun suites, inspect live paid accounts, run live APIs or benchmark competitor ranking quality. All benefits, costs saved and new models remain proposals requiring acceptance tests.

**External documents checked 2026-10-13:** [DEX Screener API](https://docs.dexscreener.com/api/reference), [Jupiter Swap V2](https://developers.jup.ag/docs/swap), [X pricing](https://developer.x.com/?lang=en), [Helius plans](https://www.helius.dev/pricing), [Nansen Pro](https://academy.nansen.ai/en/help/articles/9412804-about-nansen-pro), [GMGN wallet radar](https://docs.gmgn.ai/index/wallet-radar), [Bubblemaps](https://v2.bubblemaps.io/), [Kaito](https://www.pro.kaito.ai/portal), [Birdeye pricing](https://docs.birdeye.so/docs/pricing), [GeckoTerminal API](https://docs.coingecko.com/reference/top-pools-contract-address), open-source repositories linked in the alternatives table.

**Final decision:** **Conditional continue with a narrower, evidence-first product.** Prioritize trustworthy temporal logic, primary-source wiring and market-executable corroboration; then demonstrate incremental value before further investment in feature breadth.

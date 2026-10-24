# Predictive Intelligence: decisions

Durable choices for this initiative. Ids `PI-D-NNN`, never reused. Status ADOPTED (in force), PROPOSED (needs Elving), SUPERSEDED (replaced, with the replacing id). Social-intel decisions (D-001 to D-148) and catalyst decisions (FC-1 to FC-16) stay in their own files and still bind the code they cover.

## PI-D-001 Base branch and working branch (ADOPTED, 2026-10-23)

Work happens on `feature/predictive-intelligence`, created 2026-10-23 from `origin/feature/catalyst-firecrawl` at `f99c6c7`. Evidence that this is the authoritative code line: `f084b60` (main's code) and `3f27fc7` (social-intel 21) are ancestors of `f99c6c7`; `main` since `f084b60` changes only `data/state/latest.json`; the audit, remediation and verification branches add audit documents and two audit test files but no application code (audits/predictive-intelligence/phase_00/baseline/REPO_MAP.md). Other branches are documented, never modified.

## PI-D-002 Namespaces (ADOPTED, 2026-10-23)

Records in `docs/predictive-intelligence/` (EXECUTION, ROADMAP, DECISIONS, HANDOFF). Evidence in `audits/predictive-intelligence/phase_XX/` with each phase's named sub-folders. Cost ledger `audits/predictive-intelligence/COST_LEDGER.md`. Code `memelab/predictive/`, tests `tests/test_predictive_*.py`, fixtures `tests/fixtures/predictive/` unless Phase 01 records a different placement here. No edits to `docs/social-intelligence/`, `docs/catalyst/` or other initiatives' records.

## PI-D-003 Approvals given by Elving on 2026-10-23 (ADOPTED)

1. Guarded orchestration of phases 00 to 21, one at a time, each stopping at its gate and re-verified by the orchestrator before the next starts; stop at any gate that needs approval or data that does not exist.
2. Pushes of `feature/predictive-intelligence` by the orchestrator after each verified phase, through Elving's Composio GitHub connection if plain `git push` is refused; never `main`, never force, never other branches. Phase agents commit locally only.
3. Free public APIs (GeckoTerminal, DEX Screener, unauthenticated GitHub REST, PyPI, `git clone` of public repositories), WebSearch and WebFetch.
4. Firecrawl through Elving's MCP tools, capped at 150 credits for the whole initiative (PI-D-004).

## PI-D-004 Cost cap and ledger (ADOPTED, 2026-10-23)

Firecrawl: at most 150 credits for the whole initiative, logged in `audits/predictive-intelligence/COST_LEDGER.md` (date, tool, purpose, credits, running total) before the next billable call. The account is on the Free plan (1,000 credits a month, docs/catalyst/FIRECRAWL.md) and is shared with the catalyst work (12 credits used in its first live run on 2026-10-22; the scheduled config allows up to 900 a month once the Firecrawl branch is on `main`, where the step is a no-op today), so free routes come first and Firecrawl is for discovery or documents that free routes cannot reach. Any other paid service needs a new approval. Spend at the end of Phase 00: 0.

## PI-D-005 Not approved without a new explicit ask (ADOPTED, 2026-10-23)

LLM, Zep or MiroFish paid spend or API keys; any other paid API; scheduled tasks or always-on crawlers; deployments; copying AGPL or GPL code into the repo; destructive migrations; changing the existing 100-point score or the fatal-flag overrides; anything touching wallets or keys; trades of any kind. Until approved these capabilities are BLOCKED and later phases use fixtures (TEST_ONLY where a live path is missing).

Related fact recorded in Phase 00: the scheduled runs rebuild from `main` (FIRECRAWL.md "Scheduled runs"), whose code is `f084b60`. Nothing built on this branch reaches the scheduled runs before a merge into `main`, which is Elving's decision and is not part of the push approval.

## PI-D-006 Backtesting & Stress-Testing v1.2 status: BACKTEST_NOT_AVAILABLE (ADOPTED, 2026-10-24)

Searched every remote branch (file paths, `git grep` for "backtest", "stress", "Stress-Testing", "BACKTEST_NOT_AVAILABLE", "audits/backtesting", "v1.2"), commit messages (`git log --all -i --grep`), the uploads folder and the linked Mac folder: no implementation, no records and no package ZIP. The only backtest-like code is the social replay harness (memelab/social/replay_core.py). Until a phase finds a verified installation, every predictive output that would need it carries `BACKTEST_NOT_AVAILABLE`, and no combined forecast-plus-stress claim is made (package BACKTEST_V12_BRIDGE.md).

## PI-D-007 Catalyst ticker and name links are not identity (ADOPTED, 2026-10-24)

The catalyst matcher stores a mint link from a ticker or name search (memelab/catalyst/match.py:109-160): with one visible candidate it is graded MODERATE `TICKER_MATCH`, not AMBIGUOUS (probe `p01_ticker_identity_probe.py`), and `catalyst/monitor.py:64 record_outcomes` keys outcomes on that mint. This initiative uses as identity only exact addresses: catalyst links of type NAMED_IN_SOURCE with strength STRONG, social `token_identity` resolutions with an address, and lab tables keyed by mint. TICKER_MATCH and NAME_MATCH links may appear as context, never as a training key, label key or feature join. The existing matcher is not changed.

## PI-D-008 Stored thesis scores are version-dependent (ADOPTED, 2026-10-24)

A thesis row records neither the result files that fed it nor the code version (db.py:171). Re-running HEAD on the HIGGS inputs changed pool facts, and an incomplete input set changed score, status and fatal flag; the code of 2026-10-06 (`b6c424d`) reproduced the stored report line for line (lineage probe). Any use of stored scores, statuses or snapshot fields as features or labels must carry the export commit SHA as the version, or recompute with a pinned code SHA and recorded inputs. One thesis time stands for inputs fetched up to about 50 minutes apart (cli.py:44, collector.js:86); a conservative availability time for exported rows is the git commit time of the export.

## PI-D-009 Independent skeptic when the phase agent cannot start one (ADOPTED, 2026-10-24)

The attack step needs a fresh-context skeptic that receives artifacts and code paths, not conclusions. Phase 00 ran inside a subagent with no tool to start another agent, and a nested `claude` CLI session would have been an LLM call outside PI-D-003. Rule: the phase agent writes `SKEPTIC_PACKET.md`, runs and labels its own adversarial pass as not independent, and leaves the phase NEEDS_REVIEW; the orchestrator runs the independent skeptic and records its counterexample before marking the phase PASS.

## PI-D-010 GeckoTerminal planning rate (ADOPTED, 2026-10-24)

The current GeckoTerminal OpenAPI spec says the public API is "limited to approximately 10 calls/minute". The lab's collector paces GeckoTerminal for about 30 a minute (collector.js:78-79), matching an older CoinGecko support article. This initiative plans any free GeckoTerminal backfill at no more than 10 calls a minute, bounded per run, with 429 handling, and records the retrieval time of every candle (a backfill read today is not evidence of what was available on the candle's date, package P04 and P07).

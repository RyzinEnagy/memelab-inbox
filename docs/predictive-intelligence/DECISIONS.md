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

## PI-D-009 Independent skeptic when the phase agent cannot start one (SUPERSEDED by PI-D-013, 2026-10-24)

The attack step needs a fresh-context skeptic that receives artifacts and code paths, not conclusions. Phase 00 ran inside a subagent with no tool to start another agent, and a nested `claude` CLI session would have been an LLM call outside PI-D-003. Rule: the phase agent writes `SKEPTIC_PACKET.md`, runs and labels its own adversarial pass as not independent, and leaves the phase NEEDS_REVIEW; the orchestrator runs the independent skeptic and records its counterexample before marking the phase PASS.

## PI-D-010 GeckoTerminal planning rate (ADOPTED, 2026-10-24)

The current GeckoTerminal OpenAPI spec says the public API is "limited to approximately 10 calls/minute". The lab's collector paces GeckoTerminal for about 30 a minute (collector.js:78-79), matching an older CoinGecko support article. This initiative plans any free GeckoTerminal backfill at no more than 10 calls a minute, bounded per run, with 429 handling, and records the retrieval time of every candle (a backfill read today is not evidence of what was available on the candle's date, package P04 and P07).

## PI-D-011 theses.created_at is not a decision or availability time (ADOPTED, 2026-10-24, Phase 00 repair pass 2, skeptic F1)

`theses.created_at` (and every other time `persist_result` writes from `t`: `snapshot_json.t`, market and pool snapshots, quotes, holders, rejections) is the start time of the newest collector run among the thesis's input files (cli.py:44, collector.js:86), not the moment the thesis existed. The thesis row is written later. The only stored write time is `tokens.first_seen_at` / `last_seen_at`, wall clock `db.now()` (db.py:254-255, :288-299), set in the same transaction as the first thesis insert when persist_result creates the token row (pipeline.py:197, :243). Measured over all 89 exports on `main`: for 149 of 248 mints the earliest `first_seen_at` is after the earliest thesis `created_at` by p10 7.7, median 16.9, p90 28.7, max 116.5 minutes; in the tracked DB 8 of 8 tokens, 6.2 to 9.6 minutes. Inputs can be up to about 50 minutes older than `created_at` (FEATURE_TRACE.md gap 2).

Rules for every later phase:

1. Never use `theses.created_at` (or the other `t`-stamped columns) as `decision_time` or `available_at` without either a conservative delay that covers the measured write lag (at least the observed maximum, 116.5 minutes, unless a phase measures and justifies a different bound) or a separately recorded capture time. The conservative public availability time for anything in a state export remains the export's git commit time (PI-D-008).
2. Do not filter a historical universe with `tokens.first_seen_at <= cutoff`: it is a write time and drops mints that already had theses.
3. Phase 05 turns the skeptic's check (`audits/predictive-intelligence/phase_00/skeptic/skeptic_00_checks.py` section 2, or the SQL `SELECT COUNT(*) FROM tokens k JOIN (SELECT mint, MIN(created_at) c FROM theses GROUP BY mint) t USING(mint) WHERE k.first_seen_at > t.c` on an imported export) into an executable fixture test, and the feature store records a capture or write time for every decision record it creates.

## PI-D-012 Symbol-only catalyst alerts are not identity (ADOPTED, 2026-10-24, extends PI-D-007, skeptic F3)

catalyst/monitor.py:45-50 raises a DETERIORATION alert, keyed by mint, for every watched or linked token whose symbol appears in an unlinked NEGATIVE event title; with 10 XMR mints on record one headline would alert all of them. The matcher also upserts a `tokens` row for the linked mint and fills its symbol and name (match.py:165-166), which sets that row's `first_seen_at`. This initiative excludes such alerts from identity, features and labels, and does not treat a `tokens` row created by the matcher as evidence that the lab analysed that mint. The existing code is not changed.

## PI-D-013 The orchestrator runs the independent skeptic (ADOPTED, 2026-10-24; supersedes PI-D-009)

Phase agents have no tool to start another agent. From Phase 01 on: the phase agent writes `audits/predictive-intelligence/phase_XX/SKEPTIC_PACKET.md` (artifacts and code paths, no conclusions) and labels any adversarial pass of its own as not independent; the orchestrator runs an independent skeptic agent with a fresh context and returns its review; the phase agent folds the review in as a repair pass (verify each finding, correct records, copy the review into `audits/predictive-intelligence/phase_XX/skeptic/`) before the phase can be PASS. Phase 00 followed this sequence.


## PI-D-014 Primary targets pre-registered (ADOPTED, 2026-10-24, Phase 01)

Three primary outcomes, all price-path targets on Solana decision events (audits/predictive-intelligence/phase_01/architecture/TARGET_REGISTRY.md; machine-readable in `memelab/predictive/contract.py` `TARGETS`):

1. `price_path_target_before_invalidation_24h`: from the reference price, +25% touched before -15% within 24 h after entry; a candle touching both counts negative (AMBIGUOUS_BAR).
2. `price_path_target_before_invalidation_6h`: the same over 6 h.
3. `price_path_severe_drawdown_or_halt_24h`: a low at half the reference price within 24 h, or no trade on the reference pool and up to 3 other vendor pools from 18 h to 48 h after entry.

None carries a position size; each carries PRICE_PATH_NOT_PROCEEDS and NO_HISTORICAL_EXECUTABLE_DEPTH (P08). Not primary: exit-adjusted target (BLOCKED_NO_HISTORICAL_DEPTH), liquidity degradation (DEFERRED_FORWARD_COLLECTION, see PI-D-020), failed breakout (DEFERRED_PHASE_08), catalyst follow-through and distribution (BLOCKED_NO_DATA), 7-day target and launch-cohort collapse (EXPLORATORY). Pre-registered fingerprint `dd3b4576aa1e408052dd227e361aa2cbf4b38450994c3b5e6a2be5dc199fbccd` in commit `b6f2621` (2026-10-24T01:35:23Z), before any price-path data was read; current fingerprint after CC-01 (PI-D-019) `9f8c9debdb66b28ab5d758c29d67f46f287965aa0d0bf2c1a64a94f9733d9912`, pinned by `tests/test_predictive_contract.py`.

## PI-D-015 Decision time of a historical thesis is its first export commit time (ADOPTED, 2026-10-24, Phase 01)

A historical decision happens at the committer time of the first `data/state/latest.json` commit on `main` that contains the thesis row `(mint, created_at)` (`decision_time_basis` EXPORT_COMMIT). The row is inside the commit, so the thesis existed by then. Measured over all 89 exports and 1,801 theses: commit minus `created_at` p50 11.6 min, p90 28.7 min, max 1,325.5 min, never negative; for every mint the first-thesis commit is after `tokens.first_seen_at` (min 0.46 min); for the 82 export commits that have a GitHub push event (unauthenticated REST events, server clock) the push lands 1 to 5 s after the commit time. This satisfies PI-D-011 rule 1 through its recorded-time branch. A prospective decision uses the capture time recorded when the forecast request is created (CAPTURE_TIME). `theses.created_at` is never a decision time; the validator refuses any other basis.

## PI-D-016 Acceptance plan fixed before modeling (ADOPTED, 2026-10-24, Phase 01)

audits/predictive-intelligence/phase_01/architecture/ACCEPTANCE_METRICS.md, constants in `contract.ACCEPTANCE`. Development: decisions before 2026-10-17T00:00Z whose labels mature before then, walk-forward by day. Retrospective holdout: decisions in [2026-10-17T00:00Z, 2026-10-24T00:00Z), sealed until Phase 12 (Phase 06 prints counts and censoring only). Prospective holdout: decisions from 2026-10-24T00:00Z, evaluated in Phase 19. Minimum 100 training events with 20 per class, 50 holdout events with 10 per class, 20 per calibration bin. Primary score Brier (skill versus training prevalence, day-block and mint-block bootstrap, Holm across the three primary targets). Calibration tolerance: mean prediction inside the Wilson interval of the observed rate, overall and in every bin of at least 20 events. Levels ABSTAIN, SHADOW, VALIDATED_EXPERIMENTAL (needs the prospective holdout), NO_GO. No level implies a trading edge. Stated in advance: on this data volume the expected result is "not distinguishable from the base rate" or INSUFFICIENT_HISTORY.

## PI-D-017 Placement: separate evidence section, flag OFF, reuse before new code (ADOPTED, 2026-10-24, Phase 01)

Code stays in `memelab/predictive/` (confirms PI-D-002). Forecasts are computed after m24 from the same scout result and never feed the 100-point score, the fatal flags, the status, the watchlist or the scout lists. Flag `predictive.enabled` in `data/config.json` (gitignored), OFF unless the JSON value is true; no existing module imports the package (test). Reused, not copied: `replay_core.LeakageError` and the cutoff-view and truncation pattern, `replay_core.LabelGate`, `outcomes_core.normalize_observation` and `visible`, `replay_sources.PROVIDER_LAG`, the `outcomes_ledger` journal in a separate file with a barrier evaluator passed to `evaluate_all`, `alpha_core.wilson`, the opt-in appended report section pattern of `render_scout_report(..., social=None)`. Not reused, with reasons: `alpha_store` candle tables (no revisions, no pool key), `catalyst/monitor.py` outcomes (PI-D-007), launch-cohort horizons. Seams: audits/predictive-intelligence/phase_01/architecture/PLANNED_SEAMS.md.

## PI-D-018 Label price source and its limits (ADOPTED, 2026-10-24, Phase 01)

Labels come from free GeckoTerminal 5-minute pool OHLCV, fetched in bounded offline runs inside a phase session: at most 6 calls a minute with backoff on HTTP 429 (seen at about 9 a minute in the Phase 01 probe), at most 1,200 calls per run, a circuit breaker after 5 consecutive failures, every body kept with its retrieval time and sha256, at least 10% of series re-read 48 h or more later to detect revisions. A backfill read is never a claim of historical availability (P04, P07). The reference pool is the point-in-time pool of the export when it exists, else the vendor's current list (flagged and stratified). No scheduled job is added.

## PI-D-019 Change control CC-01: reference price available at the decision (ADOPTED, 2026-10-24, Phase 01)

Found in Phase 01's own adversarial pass, before any label existed. The pre-registered rule took the reference price from the last candle ending before the entry (decision + 300 s), so a trade between the decision and the entry, or a candle that closed but was not yet served, could decide whether a decision was eligible: a look-ahead in sample selection that a forecaster at the decision could not reproduce. New rule: the reference candle's end plus the 300 s provider lag must be at or before the decision time and within 3600 s of it (`contract.reference_candle`); thinning runs after eligibility; theses of one mint in the same export commit count once, as the newest. At inference the same rule needs one paced GeckoTerminal read at capture (ACCEPTANCE_METRICS latency row). Fingerprint `dd3b4576...` became `9f8c9deb...`. Recomputed offline on the saved coverage sample, no decision changed eligibility. Caught by `tests/test_predictive_contract.py::test_reference_price_uses_only_candles_available_at_the_decision` and by the mutation check.

## PI-D-020 Forward depth and quote collection (PROPOSED, needs Elving, 2026-10-24, Phase 01)

The exit-adjusted and liquidity-degradation targets cannot be labeled from anything that exists: no quotes or pool snapshots are kept after 2026-10-08, and the 53 of 351 decisions with a later snapshot are a watchlist-selected subset. They need, for every eligible decision, sell quotes at fixed sizes and pool reserves at the decision and on a fixed grid to 24 h, which means a scheduled collector (a new always-on job). Not approved (PI-D-005); nothing is planned or built until Elving decides. Until then both targets stay BLOCKED or DEFERRED and every forecast carries NO_HISTORICAL_EXECUTABLE_DEPTH.

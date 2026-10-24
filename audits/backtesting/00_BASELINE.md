# Phase 00: repository baseline and architectural truth

Package: Memecoin Backtesting and Opportunity Stress-Testing prompt package v1.2 (MANIFEST sha256 checked, 32 of 32 files OK).
Audit date: 2026-10-23 (UTC). Auditor: Claude session, cloud workspace, Linux, Python 3.13.17.

## 1. Which checkout is the real project

| Item | Finding | Evidence |
|---|---|---|
| Canonical remote | `https://github.com/RyzinEnagy/memelab-inbox.git` (public). The README calls it the data hand-off repo, but it also holds the full Python package `memelab/` (about 49,000 lines including tests and tools). | `git clone`, `find memelab tests tools -name '*.py' \| xargs wc -l` |
| Local copies on Elving's work computer | `C:\Users\financemgr\memelab\repo_*` are partial, non-git snapshots from 7 to 8 Oct (upload staging). `D:\memelab` holds only token files and a Maxun MCP launcher. Neither is a newer private project. | PowerShell listing, no `.git` found |
| Branches | `main` (98338a8, daily scan state commits), `feature/catalyst-firecrawl` (f99c6c7, 12 commits ahead of main, not merged), `feature/social-intelligence` (merged as PR #1), three audit/remediation branches. | `git log`, `git rev-list --count` |
| Base chosen | `feature/catalyst-firecrawl` @ `f99c6c74f00f52fb9e8f1259227a63994a419a5d` (Elving chose this on 2026-10-23: newest code, includes the Firecrawl catalyst layer). | decision D-BT-001 |
| Working branch | `feature/backtesting`, created from the base. Dirty at audit time: only the new `audits/` folder. | `git status --short` |
| Language / runtime | Python 3 package, SQLite (`data/memelab.sqlite`, WAL), numpy. Node is used only for the optional `fetch` runner (`memelab/bridge/run_plan.js`). No lockfile (no requirements.txt, no pyproject). Test deps per README: `pip install pytest numpy`. | README, repo tree |
| Deployment | No server. Scheduled Claude sessions rebuild from the repo, collect through API pulls or Chrome, analyze, and commit `data/state/latest.json` and inbox files to `main`. | README, MANIFEST.txt, `git log origin/main` |

## 2. Governance records found

The repo already has a governance set for a different project, Social and Trader Intelligence: `docs/social-intelligence/{EXECUTION,ROADMAP,DECISIONS,HANDOFF}.md`. Those are not overwritten. This project uses its own namespace:

- Governance: `docs/backtesting/{EXECUTION,ROADMAP,DECISIONS,HANDOFF}.md`
- Evidence: `audits/backtesting/` (this file, phase notes, `research/`, `data/`, `testing/`, `testing/logs/`)

Read before writing: `docs/social-intelligence/HANDOFF.md` (push route is the Composio GitHub Git Data API because the session git proxy refuses `git push`; known failing test C-1; release tools are the regression check), `docs/ARCHITECTURE.md`, `docs/catalyst/FIRECRAWL.md`, `README.md`.

## 3. End-to-end route, traced in code

```
python -m memelab plan discovery --id X     cli.cmd_plan :77 -> bridge/plan.py (GeckoTerminal, Jupiter, DexScreener, RugCheck, CoinGecko URLs :31-76)
python -m memelab fetch X                   cli.cmd_fetch :350 -> bridge/run_plan.js (Node, same JS collectors as Chrome, 429 retry)
   or Chrome collector.js + ship()          bridge/collector.js :86 sets result _at once at run start
python -m memelab discover X                cli.cmd_discover :120 -> modules/m01.discover :55 -> X.stage1.json (survivors, rejected_stage1, pre_score)
python -m memelab stage2 X --results ...    cli.cmd_stage2 :138 -> structural filter (identity, market, supply, mechanics, LP), rejections table :181
python -m memelab scout --mints ...         cli.cmd_scout :252
   for each mint: pipeline.analyze_token :116
      normalize.build_bundle :59            provider bodies -> Bundle (observed_at = max plan _at, cli._bodies :40-46)
      m23.unacceptable_conditions
      pipeline.run_modules :26              m02 identity, m03 market, m05 pools, m06 depth, m07 LP, m08 mechanics, m09 holders, m04 supply,
                                            m10 clusters, m11 early wallets, m12 order flow, m13 structure, m14 breakout, m15 entries,
                                            m16 R/R, m17 sizing, m18 exits, m19 attention, m20 manipulation, m21 lifecycle, m22 RS
      farm.detect                           wallet-farm fatal check (Solana)
      m24.derive_components / score / fatal_flags / assign_status   100-point score, fatal-flag override, status
      m25.compact_snapshot / diff           what changed since the previous thesis
      m23.assemble                          thesis
      report.render_token_report :29        markdown token report
      pipeline.persist_result :187          tokens, market_snapshots, pool_snapshots, liquidity_quotes, token_authorities, holders,
                                            wallet_clusters, wallet_transactions, price_levels, social_snapshots, theses, entries,
                                            rejections or watchlist upsert
   cli.scout_lists :212 -> report.render_scout_report :235 (+ optional social section, Phase 13 of social-intel)
python -m memelab watchlist / rejections    read-only listings
state.export :45                            data/state/latest.json (theses trimmed to 12 per mint; no market_snapshots/quotes/holders history)
```

Side layers that feed or sit beside the scout: `memelab/catalyst` (events, Firecrawl reads, assessments, outcomes), `memelab/chains` (regime, rotation, EVM engine), `memelab/launch` (pre-launch engine, launch cohort), `memelab/social` (claims, narratives, wallets, alpha, chronology, alerts, signal ledger, causal replay). Alerts exist in `social/alerts_*` (dry run by default) and `catalyst/monitor.py`. No alert path places orders.

Full per-module and per-table inventory with file:line references: [CURRENT_FUNCTIONALITY.md](CURRENT_FUNCTIONALITY.md).

## 4. Existing tests, run unmodified

| Command | Exit | Result | Log |
|---|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 785 passed in 145.80s` | `testing/logs/p00_baseline_pytest.log` |
| `python tools/release_audit.py` | 0 | "Needs action: no"; 188 Python files, 0 syntax errors; 16 JS files, 0 errors | `testing/logs/p00_release_audit.log` |
| `python tools/release_e2e.py --out ...` | 0 | "Result: PASS", 78 of 78 stages, 0 network attempts, tracked DB byte-identical | `testing/logs/p00_release_e2e.log` |
| `python audits/backtesting/testing/p00_counterexamples.py` | 0 | 3 of 3 counterexamples reproduced | `testing/logs/p00_counterexamples.log` |

The one failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (carry-over C-1 in the social-intel handoff). It fails the same way on the untouched base. Side effect: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted after the run (C-1 note).

### Three key tests, challenged

1. `tests/test_pipeline_live_fixture.py::test_paid_end_to_end_no_persist` loads three real inbox files but drops their observation times and calls `analyze_token` without `observed_at`, so the clock is `time.time()` and `age_hours` depends on when the test runs. It proves the pipeline runs on real bodies; it does not prove any point-in-time property.
2. `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` fails today because it compares a frozen fixture against the wall clock. A historical replay must never depend on the wall clock; the new engine will take an explicit `as_of` everywhere.
3. `tests/test_m13_18.py` builds synthetic candles and checks swings and zones, but never checks that an unfinished bar is excluded. Counterexample C2 below shows m13 does read a bar that has not closed.

## 5. Independent negative review (wrong-but-plausible claims, each disproved)

Script: `audits/backtesting/testing/p00_counterexamples.py` (exit 0 = every finding reproduced).

| ID | Plausible claim | What the code does | Consequence for the backtester |
|---|---|---|---|
| C1 | "Round-trip friction includes the Token-2022 transfer fee." | normalize stores RugCheck's dict under `authorities.transfer_fee` (normalize.py:230); m06 and m17 read `authorities.transfer_fee_bps` (m06:116, m17:156), which no bundle builder writes. A 5% fee token shows 3.50% friction with no fee term. | The execution model must parse the fee itself from the mechanics output or the raw RugCheck field and must never assume zero (G14). |
| C2 | "Price structure only uses closed candles." | `_common.normalize_candles` keeps every row; m13 takes the max high over all rows. A bar that started 10 minutes before `observed_at` sets the in-data ATH to its 9.99 wick. | Point-in-time signals cannot reuse m13 on raw provider candles. The backtester filters bars to `start + period <= decision_time` before any feature (G05, G18). |
| C3 | "A result file's `_at` is never earlier than the data inside it." | collector.js sets `_at` once when the run starts (:86); `deep01a.result.json` has `_at` 23:48:23Z and 16 trades stamped up to 23:49:27Z. | `_at` is not a safe `available_at` for rows inside the same file. Historical joins use the later of row time and capture time, and per-key fetch times when they exist. |

Further code findings recorded for later phases (not fixed here; Phase 00 changes no lab code):

- No reserve-based constant-product swap math exists anywhere. Pool `base_reserve`/`quote_reserve` are stored but unused (normalize.py:169). The only "impact" models are router quotes (present tense) and `2*size/liquidity` heuristics in `social/alpha_core.py:196-202` and `social/outcomes_core.py:439-479`.
- m14 emits `CONFIRMED_BREAKOUT`; m24 grants `ENTRY CONDITIONS MET` only for `BREAKOUT_RETEST`, `RETEST`, `BREAKOUT_CONFIRMED`, `CONFIRMED`, `BREAKOUT` (m24:682). A confirmed breakout without retest can never reach that status. May be intentional (no chase); recorded, not changed.
- m14 and m22 look up `h1`/`h24`/`h6` keys while the bundle uses `1h`/`24h`/`6h` (m14:303-314, m22:164); those inputs are always missing in the scout path.
- m26 compares `IMPACT_FOR_EXIT = 3.0` (percent) against live impacts that are fractions (m26:23, :62-64).
- `catalyst/assess.py:181-185` takes the close of the hour candle whose start is at or before publication, so the "pre-publication" price can be up to one hour after publication. `social/alpha_core.py:183-185` uses the open of the candle covering t0 (starts before t0).
- `catalyst/monitor.record_outcomes` has no test and no upper bound on lag between horizon and the snapshot used.
- `launch_cohort` and `launch_monitor` are updated in place although `launch/schema.py` calls the schema append-only; social "append-only" tables rely on convention (no triggers), except the signal ledger, which has abort triggers.

## 6. Historical data the lab already owns (important for Phases 05, 06, 11, 15)

- `data/state/latest.json` on `main` is exported every daily scan. Latest export (98338a8, 2026-10-23T10:20Z) holds 984 tokens, 701 theses, 1,465 entries, 1,013 rejections, 1,176 launch-cohort rows, 124 launch-monitor rows. Theses span 2026-10-06T23:59Z to 2026-10-23T10:11Z; 525 Solana theses over 201 distinct Solana mints.
- Each thesis has `created_at` (the lab's own observation time), score, status, fatal flags and `snapshot_json` with price, liquidity, `exit_cap_3pct` (from the router quotes at that time), holders, top-10, cluster share, structure, lifecycle.
- 89 commits of that file on `main` give an independent upper bound on when each record existed (commit time). This is a frozen discovery universe that includes rejected and later-dead tokens, recorded at the time, which is what the survivorship rules ask for.
- Gaps: theses are trimmed to 12 per mint in each export (older ones survive only in git history); market_snapshots, pool_snapshots, quotes and holders history are not exported (only the local 28-minute sample in `data/memelab.sqlite` from 2026-10-06/07).

## 7. Data reachability from this workspace (checked today)

| Endpoint | Status | Meaning |
|---|---|---|
| `api.geckoterminal.com/api/v2/...` | 200 | Public OHLCV and pool data reachable directly (README said the sandbox could not reach crypto APIs; that is no longer true here). |
| `api.dexscreener.com` | 200 | Current pair data reachable. |
| `lite-api.jup.ag/swap/v1/quote` | 400 without params (host reachable) | Present-tense router quotes reachable. |
| `api.github.com/repos/...` | 403 by session proxy unless a repo is attached | GitHub REST needs `add_repo`; `git clone` of public repos works. |
| `pypi.org` | 200 | pip installs work. |

No historical pool reserves, ticks or bins are available from these free endpoints. That limits historical execution precision (see Phase 01).

## 8. Web tooling and Maxun preflight

Details: [research/WEB_TOOLING_PREFLIGHT.md](research/WEB_TOOLING_PREFLIGHT.md) and [research/MAXUN_CAPABILITIES.md](research/MAXUN_CAPABILITIES.md). Summary: Firecrawl works as a Claude tool (1 scrape, 1 credit). Crawl4AI 0.9.5 runs locally on Elving's work computer in `~/crawl4ai-env` (1 crawl, 4.5 s, no cloud token used). `D:\memelab\crawl4ai-token.txt` exists (56 bytes, contents not read). Maxun: Cloud edition only, API key file present, `GET /v1/usage` returns plan TRIAL, 5 credits, 0 robots, 0 runs, 0 schedules. No self-hosted Maxun, no Docker on that computer. OSS repo license AGPL-3.0-or-later.

## 9. Security boundary (verified)

- No code places an order, builds or signs a transaction, or holds a wallet private key (grep for keypair, secretKey, sendTransaction, signTransaction, private_key, mnemonic, `/swap/v1/swap`; only guard code and tests match). Jupiter is called only at `/swap/v1/quote`.
- Secrets are API keys read at runtime: Helius (env or gitignored `data/config.json`), Firecrawl (env or gitignored `firecrawl_token.txt`), social connector keys. The release audit scans for credential shapes and trade code.
- This project adds a rule: the backtesting package must not import any wallet, signing or order module, enforced by a test (Phase 05 onward).

## 10. Baseline change freeze

Baseline SHA `f99c6c74f00f52fb9e8f1259227a63994a419a5d`. From here every change is on `feature/backtesting`, under `memelab/backtest/` (new), `tests/test_backtest_*.py` (new), `audits/backtesting/`, `docs/backtesting/`, plus the smallest integration edits recorded in DECISIONS. Existing scoring, status logic and report sections stay byte-identical when the backtesting feature flag is off.

## 11. Gate

| Gate item | Status | Proof |
|---|---|---|
| Actual source and branch identified, SHA recorded | PASS | sections 1, 10 |
| End-to-end route traced with code references | PASS | section 3, CURRENT_FUNCTIONALITY.md |
| Existing suite executed unmodified, exit code recorded | PASS (1 known failure, C-1, pre-existing) | p00_baseline_pytest.log |
| Negative review with reproduced counterexample | PASS | p00_counterexamples.log, exit 0 |
| Tool and Maxun preflight without exposing secrets | PASS | research notes |
| Unverified items labeled | PASS | sections 5, 7, 8 |

PHASE 00: PASS. Next eligible phase: 01.

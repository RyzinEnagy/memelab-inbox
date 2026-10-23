# Phase 16 E2E results: independent adversarial audit

Reviewer: independent auditor for Phase 16 (did not write phases 05 to 15). Date 2026-10-23, 20:09 to 20:45 UTC.
Repository: `/home/claude/work/memelab-inbox`, branch `feature/backtesting`, HEAD `41488ad` (clean tree before the audit). Base of the work: `f99c6c7`.

## Verdict

PHASE 16: FAILED.

- 3 of 41 acceptance scenarios FAILED (G02, G17, G32), 6 PARTIAL (G16, G22, G24, G27, G36, G39), 32 PASS, 0 NOT_TESTABLE.
- The existing suite is green apart from the known clock-dependent C-1, which fails the same way on the base commit.
- My 13 new leak and fake-liquidity mutations: 10 caught, 3 survived.
- The new adversarial test file has 19 tests: 10 pass, 9 fail. The 9 failures are reproductions of defects D1 to D9, deliberately left failing (no skip, no xfail).
- Independent confirmation of real cases was obtained:
  - DexScreener matches the pool identity and creation time of all four real cases to the second.
  - DexScreener's current price confirms the "puter" collapse.
  - The lab's own contemporaneous Jupiter and pump.fun prices match the stored bars before the collapse.
  - The historical price paths themselves come from one provider (GeckoTerminal; a fresh retrieval matches the stored bars exactly). No keyless second provider of historical bars was reachable.

Release classification I would assign: scenario-only research mode, clearly labeled. It is not an empirically validated engine:
- every sealed test is INSUFFICIENT_SAMPLE;
- the cohort evidence shown to users reads the future in replays (D1) and splices pools (D2);
- historical execution stays LIQ_SNAPSHOT_APPROX, with exact pool state SOURCE_BLOCKED.

The historical-data component is not BLOCKED, because independent confirmation exists. It is single-provider for price paths.

## Scope note

The caller restricted this audit to adding files under `audits/backtesting/testing/` and `tests/test_backtest_e2e_audit.py`, with no commits and no changes to `memelab/`. The phase prompt's EXECUTION / ROADMAP / DECISIONS / HANDOFF updates are therefore left to the caller. No defect was fixed. All new files are uncommitted.

## Commands, exit codes and counts

| Command | Exit | Result | Log |
|---|---|---|---|
| `python3 -m pytest tests/test_backtest_outcomes.py -q` (entry gate) | 0 | 14 passed | `logs/p16_gate_p15_tests.log` |
| `python3 audits/backtesting/testing/mutate.py .../p15_mutations.json` (entry gate) | 0 | 22 of 22 caught | `logs/p16_mut_p15.log` |
| `python3 -m pytest tests -q -p no:cacheprovider` at HEAD 41488ad | 1 | 1 failed (C-1 `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`), 990 passed, 178 s | `logs/p16_full_pytest_head.log` |
| same at base f99c6c7 (git worktree, removed afterwards) | 1 | 1 failed (same C-1), 785 passed | `logs/p16_full_pytest_base_f99c6c7.log` |
| `python3 -m pytest tests/test_backtest_*.py -v` | 0 | 205 passed, 0 skipped | `logs/p16_backtest_tests_verbose.log` |
| `python3 -m pytest tests/test_backtest_e2e_audit.py -v` (new, this audit) | 1 | 9 failed (D1 to D9 reproductions), 10 passed | `logs/p16_e2e_audit_tests.log` |
| mutation sets p05 to p15, `mutate.py` | 0 each | 167 of 167 caught | `logs/p16_mut_p05.log` to `p16_mut_p15.log` |
| same with `PYTHONDONTWRITEBYTECODE=1` | 0 each | 167 of 167 caught (verdicts unchanged) | `logs/p16_mut_all_nobytecode.log` |
| `mutate.py audits/backtesting/testing/p16_mutations.json` (new) | 1 | 10 of 13 caught, 3 survived | `logs/p16_mut_p16.log` |
| `python3 audits/backtesting/testing/p16_golden.py` | 0 | 45 of 45 comparisons agree | `logs/p16_golden.log` |
| `python3 audits/backtesting/testing/p16_sealed_rerun.py <copy>` | 0 | Phase 11 sealed test reproduced exactly | `logs/p16_sealed_rerun.log` |
| `python3 audits/backtesting/testing/p16_concurrency.py <scratch>` | 0 | bursts A to D and blocked providers, see below | `logs/p16_concurrency.log` |
| `python3 audits/backtesting/testing/p16_real_cases.py <copy>` | 0 | 4 real cases, `p16_real_cases.json` | `logs/p16_real_cases.log` |
| `bash audits/backtesting/testing/p16_regression.sh <scratch> <repo>` | 0 | regression matrix | `logs/p16_regression.log` |
| `python3 tools/release_e2e.py` at HEAD | 0 | PASS 78 of 78, network attempts 0, tracked DB byte-identical | `logs/p16_release_e2e_head.log`, `_report.md` |
| `python3 tools/release_e2e.py` at base f99c6c7 | 0 | PASS 78 of 78, identical stage exits | `logs/p16_release_e2e_base.log`, `_report.md` |
| clean local clone, no secrets (`env -i`, empty HOME): `pytest tests/test_backtest_*.py` | 0 | 205 passed (with and without MEMELAB_HISTORY_REPO) | `logs/p16_clean_clone_tests*.log` |
| clean local clone: `python3 tools/release_audit.py` | 0 | "Needs action: no" | `logs/p16_clean_clone_release_audit.log` |

Hashes before and after the audit (unchanged):
- `data/backtest/bt.sqlite` sha256 `5f4ce723...dc39b1`;
- `data/memelab.sqlite` sha256 `068287c0...a679ca`.

The full suite wrote `data/reports/20261023_2009_BRETT_0x532f.md`; it was deleted.

## Mutation testing

| Set | Mutations | Caught | Survived | Caught by an exception rather than an assertion |
|---|---|---|---|---|
| p05 | 7 | 7 | 0 | M05-4 |
| p06 | 12 | 12 | 0 | none |
| p06a | 9 | 9 | 0 | none |
| p07 | 14 | 14 | 0 | M07-11, M07-12 |
| p08 | 11 | 11 | 0 | none |
| p09 | 11 | 11 | 0 | none |
| p10 | 14 | 14 | 0 | none |
| p11 | 11 | 11 | 0 | none |
| p12 | 12 | 12 | 0 | none |
| p13 | 24 | 24 | 0 | none |
| p14 | 20 | 20 | 0 | M14-6, M14-10 |
| p15 | 22 | 22 | 0 | M15-4, M15-16 |
| p16 (new, this audit) | 13 | 10 | 3 | none |

New mutations (`p16_mutations.json`, each leaks future data or fakes liquidity):

| Id | Mutation | Result |
|---|---|---|
| M16-1 | a liquidity snapshot from the future prices a fill | caught |
| M16-2 | stale liquidity accepted | caught |
| M16-3 | liquidity haircut dropped | caught |
| M16-4 | thesis visible a day early | caught |
| M16-5 | runner chooses the pool basis with all future bars | SURVIVED |
| M16-6 | network fee priced with the latest SOL bar | caught |
| M16-7 | launch record usable from its claimed first trade | caught |
| M16-8 | total liquidity across pools used as the main pool depth | caught |
| M16-9 | delisted token still fillable | SURVIVED |
| M16-10 | non-executable exit valued at the paper price | caught |
| M16-11 | strategy sees the forming bar | caught |
| M16-12 | dataset hash ignores the sealed cutoff | caught |
| M16-13 | validation windows read past their end (`until=None`) | SURVIVED |

Harness note:
- `p16_mutate_strict.py` reruns every set in one shared copy and classifies how each mutation was caught.
- In that shared copy M11-5 once "survived". It is caught when run alone, and with bytecode caching off.
- The cause is the harness pattern (rewrite then restore of the same file within one second), not the code.
- The official per-set runs are unaffected; this was verified with `PYTHONDONTWRITEBYTECODE=1`.
- Future harness runs should set `PYTHONDONTWRITEBYTECODE=1`.

## G01 to G41 matrix

Status: PASS = criterion met with evidence; FAILED = a credible failure in a component that produces user-facing output; PARTIAL = core met, part missing or a lower-severity defect. Tests named are in `tests/`; `e2e_audit` is the new file.

| G | Status | Evidence (run in this audit) | Reason |
|---|---|---|---|
| G01 | PASS | timeguard g01, assess g01, strategies two_tokens_same_symbol; real data: ticker "D O T F" on mints 3GVSN8...pump and 46hMQP...pump kept apart | never merged; the lab itself flagged the second copy |
| G02 | FAILED | timeguard g02, assess g02 pass; e2e_audit `test_g02_cohort_evidence_never_splices_two_pools_of_one_mint` FAILS | store, runner and outcomes are pool-correct, but `stress.empirical_cohort` mixes every pool of a mint (D2): 18 of 192 real REJECTED cohort windows spliced, one shows -98.6% instead of -22.2% |
| G03 | PASS | timeguard g03, catalyst g03, assess g03, M09-1, M16-7 caught | records visible only from available_at |
| G04 | PASS | timeguard g04, catalyst g04_g23, assess g04 | transfer never a sale |
| G05 | PASS | timeguard g05, strategies g05, M10-8 and M16-11 caught | next open after close + latency |
| G06 | PASS | outcomes g06 (real 3GVSN8 fixture), validation g06, timeguard g06; Phase 15 selection-bias flag | dead tokens stay; 45% not observable is disclosed |
| G07 | PASS | timeguard g07 | ZERO, MISSING, STALE, UNAVAILABLE kept apart |
| G08 | PASS | timeguard g08, outcomes g08 | later edits and deletions never reach earlier cutoffs |
| G09 | PASS | execution g09, e2e_audit g09, golden math (sell with fee and Token-2022 fee, exact) | matches exact rational arithmetic |
| G10 | PASS | execution g10, golden ladder | sale proceeds fall non-linearly with size (buys are linear in a CPMM, by design) |
| G11 | PASS | execution g11, stress clmm, M07-5 | CLMM / DLMM / curve refused or quote-only |
| G12 | PASS | execution g12, stress g12_g30 | state at execution time |
| G13 | PASS | execution g13, M07-6 | failed legs never counted |
| G14 | PASS | execution g14, stress fee tests, golden G09 | fee stack once, labeled assumed fees |
| G15 | PASS | execution g15, assess stale tests | stale or future quote never a fill |
| G16 | PARTIAL | execution g16 only | SOL/USD and depeg handled in helpers and stress shocks; multi-hop paths not modeled; the engine prices fills in USD from a liquidity snapshot |
| G17 | FAILED | execution g17, stress g17_g35 pass; e2e_audit `test_g17_*` (2) FAIL | engine exit-impact-cap mode drops a position that cannot fully exit by end of data (D3) and reports a +72.7% trade as ret -135% with a negative cost basis (D4); latent (no shipped path sets `exit_impact_cap`) |
| G18 | PASS | strategies g18 (3) | no repaint, truncation invariance |
| G19 | PASS | strategies g19, catalyst g19 | observed vs interpreted |
| G20 | PASS | catalyst g20, bridge test, M09-2/M09-9 | reposts count once |
| G21 | PASS | catalyst g21, M09-4 | late attention abstains |
| G22 | PARTIAL | catalyst g22 (synthetic world with a true edge), Phase 09 real event study (18 placebo events) | the no-edge control arm is not tested; no formal real-vs-placebo test on real data |
| G23 | PASS | catalyst g04_g23, g19 | verified selling blocks positive posts |
| G24 | PARTIAL | engine g24; golden G24 (50 signals, cash ledger exact to 1e-12); e2e_audit g24 FAILS | cash can go below zero by the network fee when size equals cash (D5, low) |
| G25 | PASS | engine g25, stress g25, golden G25 (gap, crash, wick), e2e_audit g25 | gap and crash losses exceed the stop risk; a wick that recovers above the stop fills at the stop (documented optimism) |
| G26 | PASS | validation g26 (2) | tiny samples abstain |
| G27 | PARTIAL | validation g27_g28, seal tests; sealed rerun reproduced exactly | see "Sealed out-of-sample benchmark": cutoff real, but the window was seen by Phase 10 runs before pre-registration, the seal is per-object, and M16-13 survives |
| G28 | PASS | engine g28, validation g27_g28 | baselines on the same window and execution |
| G29 | PASS | engine g29 (bake-off oracle), execution g29 (integer reference), golden math | reconciled |
| G30 | PASS | stress g12_g30 | no negative or impossible stress outputs (the engine's impossible return is under G17) |
| G31 | PASS | assess, report, strategies, stress g31; e2e_audit g31 (fresh token with a 32-case cohort); real QTC case | never token-specific; observation: the headline label reads TESTED when only cohort evidence exists |
| G32 | FAILED | outcomes g32 (daily report byte-identical) passes; e2e_audit `test_g03_g32_*` FAILS; real data | an assessment replayed at its own time (`backtest stress --now`) reads cohort tokens and bars from after that time (D1): Phase 13's own PAID demo counted 27 cohort tokens, only 1 was known then; RUG case 136 used vs 71 known |
| G33 | PASS | base tests unchanged and passing at HEAD; regression matrix policy off identical to base; guard tests | no live-order path |
| G34 | PASS | assess g34, report g34, real PAID with quotes / bars / pools removed, e2e_audit locked and unusable DB | explicit degraded output, nothing fabricated |
| G35 | PASS | engine g35, report g35, Phase 10 real runs | ranked by net, paper shown beside |
| G36 | PARTIAL | webcapture g36 (2), e2e_audit injected dates pass; e2e_audit archive-proof test FAILS | a caller-asserted archive proof that predates the page's own publication claim is accepted (D9, low) |
| G37 | PASS | webcapture g37 (3), e2e_audit retro-edit test | one canonical record; revisions are versions |
| G38 | PASS | webcapture g38 (4), catalyst unverified mint | spoof and copycat refused |
| G39 | PARTIAL | webcapture g39 (2), e2e_audit sources-down and credential storage pass; e2e_audit status-echo test FAILS | a credential in a request URL is never stored, but `ingest_batch` returns it verbatim (D8, low) |
| G40 | PASS | webcapture g40 (3) | NO_GO: no webhook or schedule code; schedules refused without approval |
| G41 | PASS | webcapture g41 (2), catalyst g41, grep of `memelab/` | NO_GO with tested fallback and no dead dependency; the Maxun side of the bake-off was an insufficient sample (honestly recorded) |

Counts: PASS 32, PARTIAL 6, FAILED 3, NOT_TESTABLE 0.

## Independent golden math

`p16_golden.py` computes every expected value with `fractions.Fraction` from the constant-product formula written out by hand; the package is called only for the value under test.

| Case | Quantity | Independent | Package |
|---|---|---|---|
| G09 sell 100,000 tokens into 2,000,000 / 500 SOL, fee 0.30% | SOL out | 23.741486879077964 | 23.741486879077964 |
| G09 same | reserves after | 2,100,000 / 476.25851312092203 | identical |
| G09 same with a 1% Token-2022 fee | SOL out | 23.515237744454552 | identical |
| G09 round trip 10 SOL | SOL back | 9.941257805402198 | 9.9412578054022 (diff 2e-15) |
| G10 buy $1k / $10k / $100k in a $20k-per-side pool | avg price | 1.0525 / 1.5025 / 6.0025 | identical |
| G10 exit $1k / $10k / $100k marked | proceeds | 950.11 / 6,655.55 / 16,659.71 | identical (non-linear) |
| G25 gap to 0.60 through a 0.90 stop, $500, $1M snapshot | pnl | -202.12339448924038 | -202.12339448924047 |
| G25 crash inside the bar, close 0.50 | pnl | -251.74392587402127 | -251.7439258740213 |
| G25 67% wick, close above stop | pnl | -53.335684613987105 | -53.33568461398721 (filled at the stop) |
| G24 50 same-minute signals, $5k account | entries / final cash | 4 / 5,036.714321449243 | 4 / 5,036.714321449242 |

Intended stop risk in G25 was $50; the gap loss was $202 and the crash loss $252.

## Real historical cases with provenance

Source: `p16_real_cases.json` (from a copy of the corpus) plus the lab's committed state history (`origin/main`, `data/state/latest.json`).

### RUG: 3GVSN8DLVvrxEafP7JQj6CwBFRxCq8vuUVmsRbCEpump ("D O T F", pump.fun)

Provenance:
- pool 7AvDaHLb...vdoH (pumpswap) created 2026-10-08 06:45:02 UTC;
- graduation first seen by the lab 2026-10-09 11:57:32, commit 2bd890d;
- lab thesis REJECTED (score 48, fatal DEV_WALLET_FARM: 381 identical wallets hold 75.5%) at 12:18:19, commit a52efb9;
- the lab's launch_rejections row notes "second D O T copy".

Package output:
- stress at the thesis: RISK_FATAL_FLAW (veto respected);
- outcome after the graduation record: 1 h COMPLETE +3.4%; 6 h, 24 h and 72 h CENSORED (BARS_END_EARLY) with close -99.98%, drawdown labeled a lower bound;
- the bar of 2026-10-09 14:00 goes from 0.01273 to 1.93e-6;
- the CATALYST_VERIFIED replay submitted and then CANCELED it (INSUFFICIENT_EXECUTION_DATA: no liquidity observation at 11:57);
- the report today is UNTESTED (no assessment).

Truthful: yes, except the cohort evidence shown for the REJECTED status. It used 136 cohort tokens, but only 71 REJECTED theses existed at the decision (D1).

### FAILED CATALYST: FgnSJwFoote99diZUhtRV9Ajcfwzjj6hDx82TDhVpump ("puter")

Provenance:
- graduation (pump:grad) first seen 2026-10-08 18:40:12, 12 minutes after its claimed first trade, commit 001b382;
- lab thesis REJECTED (CANNOT_EXIT_5K) at 19:10:08, commit d33ced3.

Package output:
- outcomes after the record: 1 h +60.9% (runup +159%); 6 h -99.09%; 24 h -99.07%; 72 h -98.92%, all COMPLETE;
- stress RISK_FATAL_FLAW;
- no replay trade.

Truthful: yes, except cohort lookahead (52 known vs 136 used).

### POSITIVE CATALYST: 7K52aYQW9rWGjwZmQ7o2d1P6E7bji6hSMsqaLy5EcxLh ("PQC")

Provenance:
- graduation first seen 2026-10-08 17:15:20, commit c45bd6e (claimed first trade 02:44:04);
- lab REJECTED it at 19:10 (CANNOT_EXIT_5K, WASH_TRADING_HIGH).

Package output:
- outcomes after the record: 1 h -41%; 6 h -35%; 24 h +190% (runup +349%, drawdown -63.5%); 72 h -18%;
- the catalyst replay canceled for lack of a liquidity observation (no phantom fill);
- stress at the thesis RISK_FATAL_FLAW.

Truthful: yes. The package does not turn the later rise into a claim that the fatal flags were wrong.

### FRESH: G9wFzt1XqToHN64yrVae5JxFfY9v4K9w7quJ6zXpump ("QTC")

Provenance:
- lab thesis RESEARCH REQUIRED (score 54, no fatal flag) at 2026-10-20 10:19:24, commit c3a43be;
- the pool was 2.4 h old at the thesis.

Package output:
- 3 closed bars, every TA strategy abstains;
- the DEEP replay is INSUFFICIENT_HISTORY;
- stress INCONCLUSIVE (no invalidation level);
- cohort 25 cases, INSUFFICIENT_HISTORY;
- outcomes 24 h +29.7%, 72 h +84%.

Truthful: yes. No token-specific claim is made.

### Independent confirmation

- DexScreener public API, fetched 2026-10-23 about 20:36 UTC:
  - pair addresses, DEX and pairCreatedAt match the stored pool records exactly for all four cases (3GVSN8 1791441902, puter 1791484093, PQC 1791427444, QTC 1792483076);
  - current puter price $0.000002632 with liquidity $2,913, against the lab's $0.000217 on 2026-10-08. That independently confirms its collapse (-98.8%);
  - PQC is now -79.5% and QTC +103% from their thesis prices, consistent with the package's windows.
- Lab's own contemporaneous observations (other providers, committed at the time):
  - 3GVSN8 launch_cohort market caps from the pump.fun index: 31.6M at 2026-10-08 18:35, i.e. $0.0316 a token, against bar close 0.0316; and 11.27M at 2026-10-09 11:57, against bar 0.01132;
  - thesis prices from Jupiter sit inside the GeckoTerminal bar for 3GVSN8, puter and PQC, and 0.14% outside for QTC;
  - corpus-wide, 811 of 913 lab prices fall inside the bar, 98 within 10%, 4 outside.
- Fresh GeckoTerminal retrieval (via Firecrawl, 2 of 8 allowed calls used; one returned 404 on a pump.fun path):
  - the pool's 38 hourly bars, including the collapse bar, match the stored bars exactly (8 sampled values compared to 1e-12; `p16_indep_gt_live_3GVSN8_sample.json`).
  - This is the same provider, so it is consistency, not independence.
- Provider disagreement found: DexScreener's live stats for 3GVSN8 show price $0.03313, 24 h volume $352,804 and +69,272%.
  - Both GeckoTerminal (live) and the stored bars show no trade after 2026-10-11 15:00.
  - DexScreener's figures equal the token's first-day state (the sum of GeckoTerminal's 2026-10-08 hourly volumes is about $352k), so its stats are stale for this dead pair.
  - The package does not use DexScreener; a present-day quote from it would be misleading.
- Not obtainable: a second, independent provider of historical hourly bars without a key (Birdeye and similar need keys; the pump.fun coin endpoint returned 404).

## Blocked provider and concurrency burst

Bursts ran on copies of the corpus in the scratch area. Each worker was a separate process, released at the same instant.

- A. Fresh database, 8 processes calling `store.connect` at once: 1 succeeded, 7 crashed with `IntegrityError: UNIQUE constraint failed: bt_schema_migrations.version`. Reproduced in pytest (`test_concurrent_first_connect_to_a_new_database_never_crashes`, which also saw `database is locked`) (D6).
- B. 12 FAST assessments of the real PAID analysis at once (8 identical, 4 distinct snapshots):
  - 9 completed;
  - 3 raised `OperationalError: database is locked` after 5.02 s;
  - no duplicate assessment rows (3 FAST rows, 3 distinct keys);
  - deterministic state (PARTIAL_WITH_LIMITATIONS).
  - Through the hook, a locked database gives an explicit ERROR labeled UNTESTED and the lab result is unchanged (e2e_audit test passes).
- C. 3 outcome trackers at once: 1 ran (4,092 rows, 20.5 s); 2 crashed with `database is locked` after 5.1 s instead of returning SKIPPED. No duplicate outcome windows (D7).
- D. 3 identical runner runs at once: 1 MISS and 2 HIT, one result row, identical ledger hash. No duplicates.
- Blocked providers on the real PAID capture:
  - Jupiter quotes removed: PARTIAL_WITH_LIMITATIONS, INCONCLUSIVE label, no quote invented; the base proceeds are the labeled depth model.
  - Bars removed: INSUFFICIENT_HISTORY.
  - Quotes, bars and pools removed: INSUFFICIENT_HISTORY.
  - The report validates with no errors in each case, and the token identity and lab view are kept.

## Before/after regression matrix (signed change matrix)

Runs: analyze (`PAID`, results disc01, s2_01, deep01a, deep02, `--no-persist`); scout (PAID, STONK, HIGGS, ZCAT, persisted to a temp copy of the lab DB, `--report-dir` temp); `social alerts demo` on the fixture day. Each ran in throwaway local clones of base and HEAD, policy off (`MEMELAB_BACKTEST=0`) and on (`=1`, `MEMELAB_BT_DB` = corpus copy).

| Output | Base off vs HEAD off | Base on vs base off | HEAD off vs HEAD on | Intentional? |
|---|---|---|---|---|
| analyze stdout | identical | identical | +1 line `backtest: STALE_DATA ... research only` | yes (Phase 13 one-liner) |
| scout stdout and SCOUT.md | identical (after normalizing temp paths) | identical | appended "Backtest and stress (research only)" section; lab text unchanged | yes (Phase 14) |
| report files | identical | identical | +9 files: per-token `.backtest.md` / `.backtest.json` and `_SCOUT.backtest.json` | yes |
| social alert text | identical | identical | +1 line per token alert `Backtest: UNTESTED (no backtest or stress assessment exists for this mint)` | yes (Phase 14) |
| backtest DB created when off | no | no | no | yes |
| lab tests | 785 passed + C-1 | not applicable | HEAD 990 passed + C-1 (785 base tests unchanged) | yes |
| `tools/release_e2e.py` | PASS 78/78 both, identical exits | not applicable | not applicable | yes |

Unintentional differences found: none in the off state.

In the on state, assessments of these 2026-10-06 captures read STALE_DATA (correct: 404.7 h old). So the regression run does not exercise a fresh live assessment; the real-data FAST path was exercised separately with `now` set to the capture time (where D1 applies).

## Sealed out-of-sample benchmark

- Real cutoff:
  - the dataset hash at the pre-registered T1 (2026-10-23 16:00 UTC) recomputes to `35f836f3...` and equals `p11_results.json`;
  - 402 bars available after T1 exist in the corpus and are excluded (the hash without a cutoff differs).
- Reproduced:
  - BREAKOUT_CLOSE: chosen config, frozen sha `07e09a6f...`, verdict INSUFFICIENT_SAMPLE, 6 test trades, mean -3.13%, sealed-test ledger hash `88ae4054...`, all identical;
  - LAB_STATUS: the same, 0 test trades;
  - the latest fill time is at or before T1.
- Not sealed in the sense G27 asks:
  - every strategy had whole-period runs on the corpus (trades exiting up to 2026-10-23 17:00, inside the sealed window), stored between 18:34 and 18:46 UTC;
  - that is before the Phase 11 pre-registration hash (18:53:19 UTC), and both were committed together;
  - `TestSeal` is an in-memory object per `validate()` call, and `p11_validate.py` reads the sealed window a second time through `run_window` for the regime split (deterministic, but it shows the seal is procedural);
  - M16-13 (validation windows reading past their end) survives every test.
- Leak and fake-liquidity mutations: 10 of 13 caught (table above).

## Crawler and collector checks

| Check | Result |
|---|---|
| Firecrawl / Crawl4AI / Maxun unavailable | runtime imports with those modules blocked; no crawler import in `memelab/` (e2e_audit test passes) |
| all sources down (connection refused, 429, invalid key) | source DOWN, nothing recorded, no catalyst record (passes) |
| rate limiting (429) and retry | GeckoTerminal adapter backoff tests pass; the live 429 seen in this audit was handled by falling back to a bounded Firecrawl call |
| invalid or misplaced credential in a URL | never stored in `bt_capture_provenance` (passes); echoed verbatim in the `ingest_batch` return value (D8) |
| duplicate pages across tools and a body-only retro edit | one record; a title edit is a new version with its own first_seen_at (passes) |
| HTML prompt injection in title and date fields | stays a claim, no mint, availability = capture time, no SQL effect (passes) |
| disallowed or copycat sources | refused (webcapture g38 pass) |
| misclassified historical availability | a page date never moves availability (passes); a caller-asserted archive proof older than the page's own publication is accepted (D9) |
| secrets in evidence | 299 files under `audits/` scanned for 13 credential shapes. Only hits: my placeholder `fc-abab...` (5 distinct characters) in the e2e log, and a public transaction signature under `tx_hash`. Files named like token files were excluded and never opened. |
| existing catalyst Firecrawl layer | its tests (credentials missing, rejected key, redaction, robots, caps) pass in the full suite |

## Maxun (G36 to G41)

The decision is EXISTING_TOOL_WINS / NOT_ADOPTED:
- the Maxun cells are INSUFFICIENT_BAKEOFF_SAMPLE;
- the one evaluation run ended with `status: aborted` and 5 pages;
- the release-watch cell was blocked for lack of credits.

Runtime check:
- `memelab/` contains only status strings and enum values for Maxun: no import, URL, robot route, webhook or schedule;
- no requirements file names it;
- the runtime refuses MAXUN as a collector;
- schedules are refused without approval.

The fallback (existing collectors) passes G36 to G41 except the two low-severity items D8 and D9. There is no dormant Maxun hard dependency.

## Open defects, ranked by severity

| # | Severity | Location | Reproduction | Breaks |
|---|---|---|---|---|
| D1 | High | `memelab/backtest/stress.py:260-281` (`empirical_cohort` has no as-of); called from `assess.py:180`; reachable by `backtest stress --now` | `pytest tests/test_backtest_e2e_audit.py::test_g03_g32_cohort_evidence_uses_only_tokens_known_at_the_assessment` (35 future cohort tokens counted, tier HISTORICAL_COHORT). Real: Phase 13 PAID demo, 27 used vs 1 known; RUG 136 vs 71 | G32, G03 spirit |
| D2 | High | `stress.py:269` (bars selected by mint only, all pools, ordered by start) | `...::test_g02_cohort_evidence_never_splices_two_pools_of_one_mint` (median -99.1% for flat tokens). Real: 18 of 192 REJECTED windows | G02 |
| D3 | Medium (latent) | `engine.py:272-276` and `362-367` (a partial exit leaves the position open; the end-of-run loop does not close it) | `...::test_g17_position_that_cannot_fully_exit_by_end_of_data_is_still_reported` (1 filled, 0 trades) | G17 |
| D4 | Medium (latent, impossible output) | `engine.py:274` (`p.cost_usd -= realized`) and `280` (ret on the reduced cost) | `...::test_g17_partial_exits_keep_the_original_cost_in_the_trade_return` (true +72.7%, reported -135.3%, cost -537) | G17, G30 spirit |
| D6 | Medium | `schema.py:276-290` (reads applied versions, then inserts without an exclusive lock), `store.py:27-36` | `...::test_concurrent_first_connect_to_a_new_database_never_crashes`; burst A: 7 of 8 crash | operations |
| D7 | Medium | `outcomes.py:147-186` (one write transaction for the whole pass), `store.py:32` (default 5 s timeout, no retry); same pattern in `assess.attach` and `runner.run` | `...::test_concurrent_outcome_tracker_skips_or_waits_instead_of_crashing`; bursts B and C | operations; a concurrent scout's assessments degrade to ERROR / UNTESTED |
| D5 | Low | `engine.py:209` (cash check ignores the network fee), `234`, `381` (only final cash checked) | `...::test_g24_entry_of_all_remaining_cash_is_rejected_or_paid_never_a_crash` (cash -0.01575) | G24 |
| D11 | Low | `stress.py:271-275` | 29 of 136 real REJECTED cohort windows end more than 1 h early but count as full 24 h returns (`outcomes.py` correctly calls these CENSORED) | G06 / G32 consistency |
| D8 | Low | `sources/webcapture.py:66, 145, 152` | `...::test_g39_batch_status_never_echoes_a_credential` | G39 |
| D9 | Low | `sources/captures.py:67-69` (proof accepted without a plausibility or content-binding check) | `...::test_g36_archive_proof_older_than_the_page_itself_is_refused` | G36 |
| D10 | Low (latent) | `sources/catalyst_bridge.py:36` reads the current `status` / `verified_mint` / `link_strength`; `memelab/catalyst/assess.py:203` updates status in place | code reading; only reports use it today, so a later denial would leak if a backtest consumed these records | G08 spirit |

Test gaps (survived mutations), to fix together with the defects:
- TG1 (medium): M16-13, no test checks that a validation window reads nothing after its end (G27).
- TG2 (low): M16-5, the runner's point-in-time pool-basis call is untested.
- TG3 (low): M16-9, the delisting path is untested. It is also never populated, because `bt_token_lifecycle` is empty and the runner never sets `delisted_at`.

## Observations (not defects)

- The engine fills a stop at the stop price when a bar wicks far below it but closes above (golden case: a 67% wick gives a $53 loss).
- A fresh token with no bars but a 30+ case status cohort gets state COMPLETE and headline label TESTED. The "why" names HISTORICAL_COHORT and the report states no token-specific validation. The label wording may read as more than an analog cohort.
- `tools/release_audit.py` exempts every `tests/test_backtest_*.py` from the execution-pattern scan (broad allowlist).
- Seven of 167 builder mutations are detected by an exception rather than an assertion. They are still detected.
- The test `test_g22_placebo_times_weaken_the_relationship` ends with a vacuous assertion (`... or True`). The other assertions in it are meaningful.

## What could not be verified

- Historical price paths from a second, keyless provider. DexScreener has no public history endpoint; Birdeye and similar need keys; GeckoTerminal is rate-limited through the proxy and robots-disallowed for WebFetch (reached once through Firecrawl).
- The post-collapse state of 3GVSN8 from an independent live source: DexScreener's stats for it are stale.
- Exact historical pool reserves (SOURCE_BLOCKED, as the package itself states).
- A live FAST assessment of a fresh token from the scout. The only analyze bundles available are 2026-10-06 captures, which are correctly STALE when assessed now; the fresh-token case was assessed from the lab's own thesis snapshot.
- The Crawl4AI credential path was not exercised: the token file must not be read, and no live crawl was required.

## Files written by this audit (all uncommitted)

- `tests/test_backtest_e2e_audit.py` (19 tests: 10 pass, 9 fail on purpose, listed in `DEFECT_TESTS`)
- `audits/backtesting/testing/p16_golden.py`, `p16_mutations.json`, `p16_mutate_strict.py`, `p16_sealed_rerun.py`, `p16_concurrency.py`, `p16_real_cases.py`, `p16_real_cases.json`, `p16_regression.sh`, `p16_indep_gt_live_3GVSN8_sample.json`, this file
- `audits/backtesting/testing/logs/p16_*.log` and `p16_release_e2e_{head,base}_report.md`

Next eligible phase: none until D1 to D7 and TG1 are fixed and the failing tests in `tests/test_backtest_e2e_audit.py` pass without changing their assertions. Phase 17 must not claim an empirically validated engine.

## Re-run after repair pass 1

Re-run by the same independent reviewer against commit `47a7845` (repair pass 1), 2026-10-23, 21:10 to 21:30 UTC.

Unchanged and checked:
- `tests/test_backtest_e2e_audit.py` (19 tests, same DEFECT_TESTS text);
- `p16_mutations.json`;
- the scripts above.

New in this pass, all uncommitted:
- `audits/backtesting/testing/test_p16r1_repair_attacks.py`, attacks on the repairs;
- `audits/backtesting/testing/p16r1_cohort_check.py`, an independent point-in-time cohort recomputation;
- logs `logs/p16r1_*`.

Hashes, unchanged: `data/backtest/bt.sqlite` `5f4ce723...`, `data/memelab.sqlite` `068287c0...`. The BRETT report the suite writes was deleted again.

### Verdict after repair pass 1

PHASE 16: FAILED (second pass).

All 9 original defect reproductions now pass, along with all 190 mutations. But the repairs left or introduced:
- one medium defect: N1, survivorship in the cohort return percentiles, which breaks G06;
- five low ones: N2 to N6.

G16 and G27 need an explicit acceptance decision.

Release classification is unchanged: scenario-only research mode, clearly labeled. It is not an empirically validated engine:
- every sealed test is INSUFFICIENT_SAMPLE;
- the sealed window was seen before pre-registration, so any new sealed test needs data after 2026-10-23 16:00 UTC, as the builder proposes and I agree;
- historical execution stays LIQ_SNAPSHOT_APPROX.

Historical price paths remain single-provider. The independent confirmations recorded above still stand, and the real-case outputs are unchanged apart from the cohort.

### Commands and exits

| Command | Exit | Result | Log |
|---|---|---|---|
| `pytest tests/test_backtest_e2e_audit.py -v` | 0 | 19 passed (was 10 passed, 9 failed) | `logs/p16r1_e2e_audit_tests.log` |
| `pytest tests -q -p no:cacheprovider` | 1 | 1014 passed, 1 failed (C-1 only, pre-existing at base) | `logs/p16r1_full_pytest.log` |
| `mutate.py` p05 to p15 (`PYTHONDONTWRITEBYTECODE=1`) | 0 each | 167 of 167 caught | `logs/p16r1_mutations_all.log` |
| `mutate.py p16_mutations.json` | 0 | 13 of 13 caught (M16-5, M16-9, M16-13 now caught) | same |
| `mutate.py p16_repair_mutations.json` | 0 | 10 of 10 caught | same |
| `p16_mutate_strict.py` p16 + repair sets | 0 | 22 caught by assertion; R16-7 caught by the OperationalError it re-introduces (the intended failure) | `logs/p16r1_mut_strict.log` |
| `pytest audits/backtesting/testing/test_p16r1_repair_attacks.py -v` | 1 | 4 passed, 4 failed (N1 to N4 reproductions) | `logs/p16r1_repair_attacks.log` |
| `p16r1_cohort_check.py <copy>` | 0 | point-in-time cohort matches an independent recomputation at 5 real decision times | `logs/p16r1_cohort_check.log` |
| `p16_golden.py` | 0 | 45 of 45 agree | `logs/p16r1_golden.log` |
| `p16_sealed_rerun.py <copy>` | 0 | cutoff hash matches; configs, verdicts and metrics reproduce; BREAKOUT_CLOSE sealed-test ledger hash no longer matches the stored record (N5) | `logs/p16r1_sealed_rerun.log` |
| `p16_concurrency.py <scratch>` | 0 | A 8/8 OK; B 12/12 OK, no duplicates; C 1 RAN + 2 SKIPPED_MIN_INTERVAL, no duplicates; D 3 MISS and 3 result rows for one run (N6); blocked providers degrade explicitly | `logs/p16r1_concurrency.log` |
| `p16_real_cases.py <copy>` | 0 | all four cases identical to the first pass except cohort evidence | `logs/p16r1_real_cases.log` |
| `p16_regression.sh` (base vs HEAD, policy off/on) | 0 | off identical to base; on additive only (same intentional differences as before) | `logs/p16r1_regression.log` |
| `tools/release_e2e.py` at 47a7845 | 0 | PASS 78 of 78, network 0, tracked DB byte-identical | `logs/p16r1_release_e2e_head*.` |
| clean local clone, `env -i`, `pytest tests/test_backtest_*.py` | 0 | 229 passed | `logs/p16r1_clean_clone.log` |
| clean clone `tools/release_audit.py` | 0 | Needs action: no (the placeholder in my logs is reviewed as a placeholder) | same |

### Status of the original defects

| Defect | Status | Evidence |
|---|---|---|
| D1 cohort reads the future | FIXED | my test passes. Independent recomputation (`p16r1_cohort_check.py`) matches the package at 5 real decision times: known tokens, complete windows and median. No bar available after the as-of is used. At the RUG thesis (2026-10-09 12:18) the cohort is 29 complete of 71 known, INSUFFICIENT_HISTORY, where the first pass reported 136 cases and HISTORICAL_COHORT. At the PAID demo time it is 0 of 1 known. Residual N2 below. |
| D2 pools spliced | FIXED | my test passes; one pool per token. Residual N3 below. |
| D3 unsold remainder dropped | FIXED | my test and the builder's engine test pass (PARTIAL_UNSOLD_AT_END, remainder valued at 0) |
| D4 impossible return after partial exits | FIXED | my test passes (ret = all proceeds / original cost - 1) |
| D5 cash below zero by the fee | FIXED | my test passes |
| D6 fresh-database race | FIXED | my test passes; a new 16-process burst passes; burst A 8/8 |
| D7 lock crashes | FIXED for the tracker and assessments | my test passes; burst B 12/12 OK; burst C 1 RAN and 2 SKIPPED; two trackers with the same `now` run once. New regression N6 in the runner. |
| D8 credential echo | FIXED for query strings and user:password | my test passes. Residual N4 below. |
| D9 contradictory archive proof | FIXED | my test passes |
| D10 current status as historical denial | FIXED (no leak) | denials are no longer carried at all; a denial that was known at the time is now lost (information loss, conservative) |
| D11 censored windows counted as full | REPLACED by N1 | cut-short windows are now left out of returns, which creates a survivorship bias |
| TG1 to TG3 (M16-13, M16-5, M16-9) | FIXED | all three mutations caught by the builder's new tests |

DEFECT_TESTS in `tests/test_backtest_e2e_audit.py` that now pass: all 9.

### Remaining and new defects, ranked

| # | Severity | Location | Reproduction | Breaks |
|---|---|---|---|---|
| N1 | Medium | `memelab/backtest/stress.py` `empirical_cohort` (returns only from COMPLETE windows; no selection-bias flag) | `test_p16r1_repair_attacks.py::test_r1_cohort_returns_keep_dead_tokens_or_flag_the_bias`: 30 flat tokens and 30 rugs whose feed stops give return percentiles from the 30 survivors only. Real REJECTED cohort at the corpus end: 105 complete of 192 known, 31 cut-short windows excluded. With them kept as lower bounds the p10 is -77.6% instead of -59.4%, and the median -3.3% instead of -7.6%. | G06 (rugged tokens leave the statistic without a selection-bias mark) |
| N2 | Low | `memelab/backtest/outcomes.py` `_basis` (tries up to decision + 48 h) used by `empirical_cohort` with `observed_asof` = assessment time | `::test_r1_cohort_pool_choice_never_reads_after_the_assessment_time`: a cohort token's pool is chosen with volume printed after the assessment time (median -99% instead of 0%). Replay-only edge case: no pool had bars within 24 h of that token's decision. | G32, G02 time validity |
| N3 | Low (design) | `memelab/backtest/sources/gecko.py` `pool_basis_at` (most trailing volume), now also used by the cohort | `::test_r1_cohort_basis_not_steered_by_wash_volume_on_a_thin_pool`: wash volume on a thin pool of the same mint makes it the basis (median -95% for tokens whose main pool never moved). There is no cross-pool price consistency check. | G02 |
| N4 | Low | `memelab/backtest/sources/webcapture.py` `redact_url` / `_redact_text` | `::test_r1_redaction_covers_bare_keys_headers_and_path_tokens`: a bare key in an error message, an `Authorization: Bearer` header value, a JSON `"api_key"` value and a path-embedded token are all echoed. Query names (api_key, apikey, api-key, token, access_token, key, secret, client_secret, password, auth) and user:password are redacted (passing test). | G39 |
| N5 | Low | `memelab/backtest/__init__.py` `ENGINE_VERSION` still `bt-0.1.0` although trade records gained `unsold_tokens`, a new status and a new exposure rule | `p16_sealed_rerun.py`: the BREAKOUT_CLOSE sealed-test ledger hash changes (`88ae4054...` stored, `182fcdb9...` now) while metrics, verdict and frozen config are identical. `p11_results.json` and the report's validation hashes no longer reproduce. | reproducibility record (G27, G32 trace) |
| N6 | Low (regression from the D7 fix) | `memelab/backtest/runner.py` `run` (commits right after `register_run`, before checking for a stored result) | burst D: three identical concurrent runs all MISS and store three result rows for one run id (identical ledger hash). The first pass gave 1 MISS + 2 HIT and one row. Contradicts the runner docstring ("instead of recomputing or duplicating rows"). | operations |

Answers to the three questions asked:
- Can the per-pool cohort still be fooled? Yes, two ways: wash volume on a thin pool steers the basis (N3); in a replay the pool choice can use bars printed after the assessment time (N2). Splicing two pools is fixed.
- Can the tracker's interval check be bypassed by two concurrent passes?
  - Not with the same `now`: four concurrent passes give 1 RAN and 3 skipped, with no duplicate windows.
  - Passes whose `now` values differ by more than the interval both run concurrently, because the interval is judged on the caller's `now`. Tested: both RAN, 750 rows over 600 windows, no forked supersede chain, no crash.
  - This is an observation, not a defect, since the CLI defaults `now` to the wall clock.
- Does the redaction miss credential shapes? Yes (N4): bare keys, Authorization header values, JSON-style key fields and tokens in URL paths.

Observations (not defects):
- Each FAST assessment now computes an outcome for every known cohort token. That takes 1.3 s for the 192-token REJECTED cohort on the current corpus and grows with the universe. The regenerated Phase 13 benchmark (median 9.8 ms) measures PAID at 2026-10-06, when one cohort token was known, so it does not represent present-day cost.
- `empirical_cohort(asof=None)` still means "everything known today". The only production caller passes `asof`; a replay script that omits it, as my own real-case script does, gets the old leaking behavior. A required argument would be safer.
- The G22 no-edge control arm added by the builder is meaningful: random-walk prices, more than 25 trades per arm, real and placebo means within 3% of zero and of each other.

### G01 to G41 after repair pass 1

Changes from the first pass:

| G | First pass | Now | Reason |
|---|---|---|---|
| G02 | FAILED | PARTIAL | splicing fixed; residual N2 (pool choice can read past the as-of) and N3 (basis steerable by wash volume) |
| G06 | PASS | PARTIAL | N1: the cohort return percentiles drop tokens whose feed died, with no selection-bias flag |
| G17 | FAILED | PASS | D3, D4 fixed and tested |
| G22 | PARTIAL | PASS | no-edge control arm tested |
| G24 | PARTIAL | PASS | D5 fixed |
| G32 | FAILED | PARTIAL | D1 fixed and verified independently on real data; residual N2 |
| G36 | PARTIAL | PASS | D9 fixed |
| G39 | PARTIAL | PARTIAL | D8 fixed for query and userinfo; residual N4 |
| G16 | PARTIAL | PARTIAL | multi-hop paths still not modeled and not labeled unsupported. This needs an explicit decision to accept it as a disclosed limitation of scenario-only mode. |
| G27 | PARTIAL | PARTIAL | cannot be fixed retroactively. I agree with the builder: disclose that Phase 10 whole-period runs saw the sealed window before pre-registration, and require data after 2026-10-23 16:00 UTC for any new sealed test. The `TestSeal` is still per-object. M16-13 is now covered. N5 must be resolved so the stored sealed-test hashes reproduce. |

Counts: PASS 35, PARTIAL 6 (G02, G06, G16, G27, G32, G39), FAILED 0, NOT_TESTABLE 0.

Next step before Phase 17: fix N1 (and N2 to N6, all small), and decide G16 and G27 explicitly. Then re-run this section's commands with `tests/test_backtest_e2e_audit.py` and `test_p16r1_repair_attacks.py` unchanged.

## Re-run after repair pass 2

Re-run by the same independent reviewer against commit `0e63563` (repair pass 2), 2026-10-23, 21:50 to 22:08 UTC.

Unchanged since I left them:
- `tests/test_backtest_e2e_audit.py`, `p16_mutations.json` and the first-pass scripts (`git diff 47a7845 HEAD` empty);
- `test_p16r1_repair_attacks.py` (committed by the coordinator as written).

New in this pass, all uncommitted:
- `test_p16r2_repair_attacks.py`, attacks on pass 2;
- `p16r2_cohort_check.py`, an independent recomputation of the pass-2 cohort definition;
- `p16r2_guard_scan.py`, the real-corpus effect of the pool-disagreement guard;
- logs `logs/p16r2_*`.

Protected hashes are unchanged. The BRETT report was deleted again.

### Verdict after repair pass 2

PHASE 16: FAILED (third pass, strict reading of the gate), on low-severity residuals only.

- No High or Medium defect remains.
- Every defect from the first two passes is fixed, or (N3) resolved by a fail-closed rule I accept.
- What keeps three scenarios PARTIAL:
  - the disagreement guard can hide a real rug below the bias-flag threshold (N7) and can be evaded by very large wash volume (N3b);
  - redaction misses bare short keys and over-redacts public text (N4b, N4c);
  - two cache weaknesses (C1, C2).
- G16 and G27 cannot be fixed by code and need the user's explicit acceptance as disclosed limitations.

If the user accepts those, plus these low residuals as documented limitations, I would treat the package as fit for the release below.

Release classification: scenario-only research mode, clearly labeled. It is not an empirically validated engine:
- every sealed test is INSUFFICIENT_SAMPLE;
- the sealed window was seen before pre-registration, so a new sealed test needs data after 2026-10-23 16:00 UTC;
- historical fills are LIQ_SNAPSHOT_APPROX.

Historical price paths remain single-provider, and the independent confirmations recorded in the first pass still stand.

### Commands and exits

| Command | Exit | Result | Log |
|---|---|---|---|
| `pytest tests -q -p no:cacheprovider` | 1 | 1019 passed, 1 failed (C-1 only, pre-existing) | `logs/p16r2_full_pytest.log` |
| `pytest tests/test_backtest_e2e_audit.py audits/backtesting/testing/test_p16r1_repair_attacks.py -v` | 1 | 26 passed, 1 failed: `test_r1_cohort_basis_not_steered_by_wash_volume_on_a_thin_pool` (KeyError: the cohort is INSUFFICIENT_HISTORY, by the fail-closed rule) | `logs/p16r2_my_tests.log` |
| `pytest audits/backtesting/testing/test_p16r2_repair_attacks.py -v` | 1 | 3 passed, 6 failed (residual reproductions) | `logs/p16r2_repair_attacks.log` |
| `mutate.py` p05 to p16, repair, repair2 (`PYTHONDONTWRITEBYTECODE=1`) | 0 each | 200 of 200 caught (167 + 13 + 10 + 10) | `logs/p16r2_mutations_all.log` |
| `p16_mutate_strict.py` p16, repair, repair2 | 0 | all caught. R16-7 is caught by the OperationalError it re-introduces. R16-9 is flagged "crash" only because pytest's "DID NOT RAISE ValueError" names an exception; both are proper detections. | `logs/p16r2_mut_strict.log` |
| `p16r2_cohort_check.py <copy>` | 0 | the package matches my recomputation at 6 real decision points: known tokens, n, n_complete, bias flag, p10 and median | `logs/p16r2_cohort_check.log` |
| `p16r2_guard_scan.py <copy>` | 0 | 1,023 opportunities; the guard removes 0 / 0 / 1 / 2 windows at 1 / 6 / 24 / 72 h | `logs/p16r2_guard_scan.log` |
| `p16_concurrency.py <scratch>` | 0 | A 8/8 OK; B 12/12 OK, no duplicates; C 1 RAN + 2 SKIPPED_MIN_INTERVAL; D 1 MISS + 2 HIT_AFTER_CONCURRENT_RUN, one result row; blocked providers explicit | `logs/p16r2_concurrency.log` |
| `p16_real_cases.py <copy>` | 0 | all four cases identical to the first pass except the cohort, which is checked point-in-time separately | `logs/p16r2_real_cases.log` |
| `p16_sealed_rerun.py <copy>` | 0 | cutoff hash matches; both sealed-test ledger hashes reproduce (BREAKOUT_CLOSE `88ae4054`, LAB_STATUS `e4781814`) | `logs/p16r2_sealed_rerun.log` |
| `p16_golden.py` | 0 | 45 of 45 agree | `logs/p16r2_golden.log` |
| `p16_regression.sh` | 0 | policy off identical to base; on: additive only, same as before | `logs/p16r2_regression.log` |
| `tools/release_e2e.py` at 0e63563 | 0 | PASS 78 of 78, network 0, tracked DB byte-identical | `logs/p16r2_release_e2e_head*` |
| clean local clone, `env -i`: `pytest tests/test_backtest_*.py` and the pass-1 attack file | 1 | 241 passed, 1 failed (the same accepted N3 test); `tests/test_backtest_*.py` alone all pass | `logs/p16r2_clean_clone.log` |
| clean clone `tools/release_audit.py` | 0 | Needs action: no | same |

### Status of the pass-1 findings

| Finding | Status | Evidence |
|---|---|---|
| N1 survivorship in cohort returns | FIXED | `test_r1_cohort_returns_keep_dead_tokens_or_flag_the_bias` passes. Real REJECTED cohort at the corpus end: 136 measured (105 complete), p10 -77.6%, `selection_bias_risk` true (26.9% unmeasured), complete-only p10 -59.4% shown beside it. Recomputed independently. |
| N2 pool choice after the as-of | FIXED | `test_r1_cohort_pool_choice_never_reads_after_the_assessment_time` passes; the pool tries are capped at the outcome's as-of |
| N3 basis steered by wash volume | RESOLVED BY FAIL-CLOSED (accepted) | My pass-1 test still fails, because it expected the main pool to be measured. The builder instead marks the window NOT_OBSERVABLE (POOL_DISAGREEMENT); the cohort comes out INSUFFICIENT_HISTORY with the bias flag (`test_r2_guard_refuses_the_pass1_wash_world` passes). I accept this: no wrong number is published, and choosing the lower-volume pool without depth data is also a guess. My failing pass-1 test is therefore an accepted divergence, not an open defect. Residuals N3b and N7 below. |
| N4 redaction gaps | FIXED for the pass-1 cases | `test_r1_redaction_covers_bare_keys_headers_and_path_tokens` passes, and `test_r2_redaction_pass2_claims_hold` passes. Covered: Bearer/Basic, name=value, JSON pairs, user:password, key prefixes, UUIDs, 40+ character runs, path tokens refused by `allowed()`, public base58 addresses kept. Residuals N4b, N4c below. |
| N5 engine version and ledger hashes | FIXED | `bt-0.2.0`; both stored sealed-test hashes reproduce |
| N6 duplicate run results | FIXED | burst D: one result row, two HIT_AFTER_CONCURRENT_RUN |

DEFECT_TESTS in `tests/test_backtest_e2e_audit.py`: all 9 pass.

RESIDUAL_TESTS in `test_p16r1_repair_attacks.py`: 3 of 4 pass. The fourth (N3) fails by the accepted fail-closed rule.

### Remaining defects, ranked (all Low)

| # | Severity | Location | Reproduction (`test_p16r2_repair_attacks.py`) | Breaks |
|---|---|---|---|---|
| N7 | Low | `outcomes.pool_disagreement` (any single hour over 30% apart, other pool at least 5% of the volume) and the 20% flag in `stress.empirical_cohort` | `test_r2_guard_does_not_hide_a_rug_below_the_bias_flag` (details below the table). Real corpus: the one 24 h window the guard removes (Bm67Lrew..., 2026-10-18) had its basis pool fall 99.5% inside the window. | G06 |
| N3b | Low | `outcomes.pool_disagreement` `min_volume_share=0.05` | `test_r2_guard_is_evaded_when_wash_volume_exceeds_twenty_times_the_real_pool`: with 25x wash volume the real pool falls under the 5% floor and is ignored, and the cohort is measured on the wash pool (median -95% for tokens whose main pool never moved) | G02 |
| N4b | Low | `webcapture.looks_like_secret` / `redact_text` (bare runs under 40 characters are kept unless prefixed or UUID-shaped) | `test_r2_redaction_catches_bare_short_keys`: a 32-hex key after "key", a Telegram bot token's secret part, and a 34-character alphanumeric key are all echoed in error text | G39 |
| N4c | Low (false positives) | same | `test_r2_redaction_keeps_useful_public_text`: a 64-hex content hash, an 88-character transaction signature and the word after "Basic" are removed from error text (the mint address is kept) | diagnostics |
| C1 | Low (latent) | `stress.empirical_cohort` returns `dict(out)`, a shallow copy of the cached result | `test_r2_cached_cohort_cannot_be_poisoned_by_a_caller`: editing a nested list in one answer changes the next answer (median 9.99). No production caller mutates it today. | integrity |
| C2 | Low | `assess.data_revision` covers `bt_market_bars` and `bt_universe_members` but not `bt_pool_versions`, which the cohort now reads | `test_r2_assessment_cache_never_serves_a_stale_cohort_after_new_pool_records`: after a pool-list refresh with no bars yet, a direct cohort says 0 measured but the FAST assessment cache HIT still says 30. The window is the same snapshot within its 2 h staleness limit. | cache consistency |

N7 in detail:
- In a rug's crash hour, a side pool's last trade came before the crash, so its hourly close differs from the main pool's close. The window is marked NOT_OBSERVABLE.
- With 6 rugs among 36 tokens (16.7% unmeasured), no bias flag is raised, and the returns and worst drops silently lose every rug.

Answers to the questions asked:
- **Disagreement guard thresholds.** The fail-closed principle is right, but one hour over 30% apart is too eager (N7) and the 5% volume floor is evadable (N3b). Rule I would argue for:
  1. Compare closes over the hours both pools traded and require the gap to persist for at least 2 consecutive hours (or use the median gap). That ignores the crash-hour close-timing artifact and lone prints.
  2. Drop the volume floor for a pool that trades in most of those hours.
  3. When a window is refused, still contribute its worst drop across pools as a lower bound to the drawdown statistics.
  4. Always report the count of guard-removed windows, not only above the 20% flag.
  - Real-corpus impact today is small (1 window at 24 h, 2 at 72 h), so this is Low.
- **Redaction.** False negatives remain for bare keys under 40 characters (N4b), the most common API-key lengths (32 to 39). False positives remove hashes, transaction signatures and ordinary words after "Basic", "token" or "key:" (N4c). Suggested rule: redact a bare run of 20 or more characters only when it is next to a credential word or follows a known prefix; keep 64-hex hashes and base58 runs over 80 characters.
- **Cache key.**
  - `empirical_cohort` itself follows new bars, universe rows, pool records and backfilled bars (`test_r2_cohort_cache_follows_new_bars_universe_rows_and_pool_records` passes).
  - Two ways a stale or wrong cohort can still be served:
    - the FAST assessment cache, whose key omits pool records (C2);
    - a caller mutating a shared cached object (C1).
  - Not reproduced, by reasoning only:
    - two distinct in-memory databases in one process share the key `''`;
    - a database file replaced at the same path with equal row ids is not detected.

Observations:
- `assess` floors the cohort as-of to the start of the hour (conservative; at the PAID demo time no cohort token is known).
- Each REJECTED-status FAST assessment still computes about 190 cohort outcomes once per hour, which the cache now amortizes.

### G01 to G41 after repair pass 2

| G | After pass 1 | Now | Reason |
|---|---|---|---|
| G02 | PARTIAL | PARTIAL | splicing fixed and N2 fixed; residual N3b (guard evadable with 20x or more wash volume) |
| G06 | PARTIAL | PARTIAL | N1 fixed; residual N7 (guard can hide a rug below the bias flag) |
| G32 | PARTIAL | PASS | N2 fixed; assessment and cohort point-in-time verified independently at 6 real decision points; daily replay byte-identical |
| G39 | PARTIAL | PARTIAL | N4 fixed for its cases; residual N4b (bare short keys) |
| G16 | PARTIAL | PARTIAL | multi-hop routes not modeled. Needs user acceptance as a disclosed limitation; the builder will state it in the release report. |
| G27 | PARTIAL | PARTIAL | sealed hashes reproduce again (N5 fixed). Needs user acceptance: the window was seen before pre-registration, and any new sealed test needs data after 2026-10-23 16:00 UTC. |

Counts: PASS 36, PARTIAL 5 (G02, G06, G16, G27, G39), FAILED 0, NOT_TESTABLE 0.

Next step:
1. Either fix N7, N3b, N4b, C1 and C2 (each small; the rules are proposed above) and re-run these commands with all three attack files unchanged, or have the user accept them as documented limitations.
2. Then have the user accept G16 and G27 explicitly.

After both, Phase 16 can be closed for scenario-only research mode.

## Re-run after repair pass 3

Re-run by the same independent reviewer against commit `c42045b` (repair pass 3), 2026-10-23, 22:39 to 23:18 UTC.

Unchanged since I left them:
- `tests/test_backtest_e2e_audit.py`, `p16_mutations.json` and the first-pass scripts (`git diff 47a7845 HEAD` empty for them);
- `test_p16r1_repair_attacks.py` and `test_p16r2_repair_attacks.py` (committed by the coordinator as written, no change since).

New in this pass, all uncommitted:
- `test_p16r3_repair_attacks.py`, 20 attacks on pass 3: 8 residual reproductions listed in `RESIDUAL_TESTS` and 12 checks that pass;
- `p16r3_cohort_check.py`, an independent recomputation with the pass-3 guard;
- `p16r3_guard_scan.py`, the real-corpus effect of the pass-3 guard (the pass-2 scan reads a field that pass 3 removed);
- `p16r3_n3c_scan.py`, the real-corpus size of N3c, with a control run on a synthetic world;
- logs `logs/p16r3_*`.

Housekeeping:
- Protected hashes are unchanged (`bt.sqlite` `5f4ce7239eb4f0b0...`, `memelab.sqlite` `068287c0d7e45436...`).
- No BRETT report was written this time.
- No Firecrawl call this pass (2 of 8 used in total).
- The release audit's own credential and no-trading scanners find nothing in my new files, also with them tracked in a throwaway clone.

### Verdict after repair pass 3

PHASE 16: FAILED (fourth pass of five, strict reading of the gate), with G16 and G27 taken as disclosed limitations.

- Pass 3 fixes everything it claims:
  - all six pass-2 residuals (N7, N3b, N4b, N4c, C1, C2) and the migration flake are fixed;
  - my unchanged pass-2 attacks pass;
  - a 16-process burst on a fresh database succeeded 5 times out of 5;
  - the concurrency script ran clean 3 times.
- No High defect.
- One Medium, N8. It is not new code:
  - since pass 1, the Markdown report has called every measured cohort window a "complete case" and has never shown the selection-bias flag;
  - I missed it in passes 1 and 2, so my pass-2 statement that no Medium defect remained was wrong.
- Low residuals:
  - N3c: the persistence rule can be evaded;
  - N4d and N4e: secrets echoed;
  - N4f: over-redaction;
  - C3: a latent cache key.
- Three scenarios stay PARTIAL: G02 (N3c), G06 (N8) and G39 (N4d, N4e).

What would close it in the fifth and last pass. Each fix is small:
1. N8 (must). The cohort line in `report.render_md` should say:
   - how many windows were measured, how many were complete, and how many stopped trading early (counted at their last price, an upper bound);
   - the selection-bias flag with the unmeasured share;
   - the guard removals and the complete-only percentiles.
2. N4d (must). A credential word directly before a value wins over the digest and signature exemption.
3. N3c (must, unless the user accepts it as a documented limitation). Three changes:
   - count a run over consecutive shared observations instead of clock-adjacent hours;
   - also refuse when more than a third of the shared hours (at least 2) are apart;
   - compare the union of side pools with the basis, as well as each side pool alone.
   My scan shows that neither rule changes a single real window today.
4. C3 (should). Do not cache in-memory databases, or key them on a token stored with the connection.
5. N4e and N4f can be documented as limits of text redaction instead of fixed.

Then re-run these commands with all four attack files unchanged. If they pass and nothing new of Medium severity or higher appears, I would expect:
- G02, G06 and G39 to move to PASS;
- the phase to close for scenario-only research mode, with G16, G27, N4e and N4f as disclosed limitations.

Release classification, unchanged: scenario-only research mode, clearly labeled. It is not an empirically validated engine:
- every sealed test is INSUFFICIENT_SAMPLE;
- the sealed window was seen before pre-registration, so a new sealed test needs data after 2026-10-23 16:00 UTC;
- historical fills are LIQ_SNAPSHOT_APPROX;
- historical price paths come from one provider. The independent confirmations from the first pass still stand.

### Commands and exits

| Command | Exit | Result | Log |
|---|---|---|---|
| `pytest tests -q -p no:cacheprovider` | 1 | 1020 passed, 1 failed (C-1 only, pre-existing: `test_catalyst.py::test_dedup_corroboration_resurface_denial`) | `logs/p16r3_full_pytest.log` |
| `pytest tests/test_backtest_e2e_audit.py` and the pass-1 and pass-2 attack files, `-v` | 1 | 35 passed, 1 failed: the accepted N3 test (KeyError: the cohort is INSUFFICIENT_HISTORY by the fail-closed rule). DEFECT_TESTS 9 of 9 pass; pass-2 attacks 9 of 9 pass. | `logs/p16r3_my_tests.log` |
| `pytest audits/backtesting/testing/test_p16r3_repair_attacks.py -v` | 1 | 12 passed, 8 failed: exactly the 8 residual reproductions in `RESIDUAL_TESTS` | `logs/p16r3_repair_attacks.log` |
| `mutate.py` p05 to p16, repair, repair2 (`PYTHONDONTWRITEBYTECODE=1`) | 0 each | 205 of 205 caught (167 + 13 + 10 + 15) | `logs/p16r3_mutations_all.log` |
| `p16_mutate_strict.py` p16, repair, repair2 | 0 | all caught except one survival of R16-6 (concurrent first migration) in this shared-copy run; `mutate.py` on R16-6 alone catches it 8 of 8 | `logs/p16r3_mut_strict.log`, `logs/p16r3_r166_repeat.log` |
| `p16r3_cohort_check.py <copy>` | 0 | the package matches my recomputation at 6 real decision points: known tokens, n, n_complete, guard removals, bias flag, p10 and median | `logs/p16r3_cohort_check.log` |
| `p16r3_guard_scan.py <copy>` | 0 | 1,023 opportunities; the guard removes 0 / 0 / 1 / 1 windows at 1 / 6 / 24 / 72 h (pass 2: 0 / 0 / 1 / 2) | `logs/p16r3_guard_scan.log` |
| `p16r3_n3c_scan.py <copy>`, then on the synthetic alternating world | 0 | real corpus: 0 measured windows with two or more shared hours apart, out of 74 / 83 / 83 / 88 multi-pool windows at 1 / 6 / 24 / 72 h. Control: all 30 synthetic windows found at 24 h. | `logs/p16r3_n3c_scan.log` |
| `p16_concurrency.py <scratch>`, 3 runs on fresh copies | 0 each | every run: A 8/8 OK, one migration row; B 12/12 OK, no duplicates; C 1 RAN + 2 SKIPPED_MIN_INTERVAL, no duplicate windows; D 1 MISS + 2 HIT_AFTER_CONCURRENT_RUN, one result row; blocked providers explicit | `logs/p16r3_concurrency.log` |
| `p16_real_cases.py <copy>` | 0 | all four cases identical to the first pass except the cohort, which is identical to pass 2 (138 REJECTED, 27 FRESH; no as-of, labeled) | `logs/p16r3_real_cases.log` |
| `p16_sealed_rerun.py <copy>` | 0 | cutoff hash matches; configs, verdicts, metrics and both sealed-test ledger hashes reproduce (`88ae4054`, `e4781814`) | `logs/p16r3_sealed_rerun.log` |
| `p16_golden.py` | 0 | 45 of 45 agree | `logs/p16r3_golden.log` |
| `p16_regression.sh` | 0 | policy off identical to base; on: additive only. Versus pass 2, only the snapshot age (406.1 h to 407.0 h, wall clock), the request ids and the report hash that follows from them differ. | `logs/p16r3_regression.log` |
| `tools/release_e2e.py` at c42045b | 0 | PASS 78 of 78, network 0, tracked DB byte-identical | `logs/p16r3_release_e2e_head*` |
| clean local clone, `env -i`: `pytest tests/test_backtest_*.py` and the pass-1 and pass-2 attack files | 1 | 251 passed, 1 failed (the same accepted N3 test) | `logs/p16r3_clean_clone.log` |
| same clone, pass-3 attack file copied in | 1 | 12 passed, 8 failed, identical to the working copy | same |
| clean clone `tools/release_audit.py`, before and after tracking my pass-3 files (index only, no commit) | 0 | Needs action: no | same |

### Status of the pass-2 findings

| Finding | Status | Evidence |
|---|---|---|
| N7 guard hides a rug below the bias flag | FIXED | `test_r2_guard_does_not_hide_a_rug_below_the_bias_flag` passes. A single-hour gap from crash timing no longer voids a window, and removals are counted in `pool_disagreement_removed` and raise the flag above 5%. `test_r3_rug_with_a_two_hour_stale_side_pool_is_disclosed` passes: a side pool stale for 2 hours refuses the rug window, and the count discloses it below the flag. |
| N3b guard evaded by 20x wash volume | FIXED | `test_r2_guard_is_evaded_when_wash_volume_exceeds_twenty_times_the_real_pool` passes; the volume floor is gone. Residual N3c below. |
| N4b bare short keys | FIXED | `test_r2_redaction_catches_bare_short_keys` passes. Residuals N4d and N4e below. |
| N4c over-redaction of hashes and signatures | FIXED | `test_r2_redaction_keeps_useful_public_text` and `test_r3_redaction_keeps_public_identifiers_and_removes_prefixed_keys` pass. Residual N4f below. |
| C1 shared cached object | FIXED | `test_r2_cached_cohort_cannot_be_poisoned_by_a_caller` passes (deep copies on store and on return) |
| C2 request key without pool records | FIXED | `test_r2_assessment_cache_never_serves_a_stale_cohort_after_new_pool_records` passes (`bt_pool_versions` is in `data_revision`). The file key is now (path, inode), so a replaced file gets a new key. Residual C3 for in-memory databases. |
| Migration flake (claimed by the builder) | FIXED | `BEGIN IMMEDIATE` plus a bounded retry on lock errors only. 5 bursts of 16 processes on a fresh database: all OK in under 15 s, one migration row each. Connecting to an existing database while another connection holds a write lock returns in under 2 s. A non-lock error (a file that is not a database) is raised at once. |
| N3 basis steered by wash volume | RESOLVED BY FAIL-CLOSED (accepted in pass 2) | unchanged |

Real REJECTED cohort at 2026-10-23 17:00, the last full hour of the corpus, identical to my recomputation:
- 136 measured, of which 105 complete;
- 26.9% of measurable tokens unmeasured, so selection bias is flagged;
- 0 guard removals;
- p10 -77.6%, complete-only p10 -59.4%.

With no as-of it is 138 measured, the builder's number.

### Remaining defects, ranked

| # | Severity | Location | Reproduction (`test_p16r3_repair_attacks.py` unless named) | Breaks |
|---|---|---|---|---|
| N8 | Medium (report disclosure) | `memelab/backtest/report.py` `render_md`, the cohort line (unchanged since `47a7845`) | `test_r3_report_markdown_discloses_cohort_bias_and_censored_windows` and the real REJECTED cohort; details below the table | G06; also the evidence wording G31 relies on |
| N4d | Low | `memelab/backtest/sources/webcapture.py`: the digest and signature exemption (`_hash_or_signature`) applies even right after a credential word | `test_r3_redaction_hex_and_secret_key_shaped_values`; details below the table | G39 |
| N3c | Low | `memelab/backtest/outcomes.py` `pool_disagreement`: a run counts clock-adjacent hours, and each side pool is checked against the basis alone | `test_r3_guard_alternating_divergence`, `test_r3_guard_sparse_real_market`, `test_r3_guard_three_pools_real_market_split_across_two_pools`; details below the table. Real corpus: 0 windows of this shape (`p16r3_n3c_scan.py`). | G02 |
| N4e | Low | `webcapture`: credential context counts only directly before the value | `test_r3_redaction_context_word_without_separator`: "provider rejected the X-API-KEY header value <32-hex>" is echoed ("X-API-KEY: <32-hex>" is removed) | G39 |
| N4f | Low (false positives) | `webcapture`: the rule for values of 16 or more characters after a credential word | `test_r3_redaction_false_positives_after_credential_words`: "missing key published_time_field_value; token expired_at_2026-10-23T12:00:00Z; auth required_for_this_endpoint" becomes "missing key [removed]; token [removed]; auth [removed]" | diagnostics |
| C3 | Low (latent) | `memelab/backtest/stress.py` `empirical_cohort`, cache key `("memory", id(con))` | `test_r3_cohort_cache_in_memory_id_reuse`: CPython reuses a closed connection's id for the next in-memory connection. A database whose true median is -0.5 is served 0.0 from the previous one (6 of 6 alternations in a manual loop). Production opens files, so this is not reachable today. | integrity |

N8 in detail:
- Synthetic: 45 measured windows, of which 30 complete and 15 stopped early, with the bias flag true in the JSON document. The Markdown says "45 complete cases" and has no word about bias, censoring or the upper bound.
- Real corpus: the REJECTED cohort at 2026-10-23 17:00, rendered with `report.build` and `render_md`, reads "136 complete cases of 192 tokens ... p10 / p50 / p90: -77.6% / -3.3% / +29.5%". In fact 105 are complete, 31 are censored, and 26.9% of measurable tokens are unmeasured (flag true).

N4d in detail:
- Echoed in error text: "Authorization: Bearer <64-hex>", "HMAC secret <64-hex>", "token <40-hex>", and "private key" followed by a fake Solana secret-key shape (base58 of 64 bytes). "password <40-hex>" is echoed too (manual check).
- Removed: the same values after "=", ":" or in JSON quoting, and URL query values.

N3c in detail. Each test makes 30 tokens whose real market never moves, with a wash basis pool that falls:
- `test_r3_guard_alternating_divergence`: the wash basis is at the market in even hours and falls in odd hours, so 10 of 24 shared hours are more than 30% apart but never two adjacent;
- `test_r3_guard_sparse_real_market`: the real pool trades every other hour, so no two shared hours are adjacent;
- `test_r3_guard_three_pools_real_market_split_across_two_pools`: the real market is split over two pools trading in alternate hours.
In all three, the cohort is HISTORICAL_COHORT with a median of -95%.

Checks that pass (no defect):
- three pools where a real basis and a real side pool agree and a third pool sits 60% below all day: every window is refused, `pool_disagreement_removed` is 30 and the flag is raised (`test_r3_guard_three_pools_one_off_market_side_pool_is_refused_and_disclosed`);
- steady divergence is refused (`test_r3_guard_steady_divergence_is_refused`);
- a gap is still refused when the real pool misses every third hour (`test_r3_guard_gap_across_a_missing_hour_still_refused`);
- the connect retry, as described in the migration flake row above.

Observations:
- R16-6 timing: in the strict run on a shared copy, the mutation that re-creates the concurrent first-migration crash survived once. Alone it is caught 8 of 8, and the official run caught it. Detection depends on process timing, so a single strict run can miss it.
- While another process holds the research database's write lock, the scout hook waits about 10 s (the busy timeout) per assessment, then degrades explicitly as G34 requires. This is the same at pass 2 (10.2 s at both commits), so it is not a regression.
- The one 24 h window the guard still removes in the real corpus (Bm67Lrew..., LAB_REJECTION, 2026-10-18 09:51) is a dust token. Its two meteora-damm-v2 pools have no recorded volume and closed 344% apart for 2 consecutive hours. Refusing it is reasonable.
- `p16r2_guard_scan.py` no longer runs at pass 3 (KeyError `other_volume_share`, a field pass 3 removed); `p16r3_guard_scan.py` replaces it.

Answers to the questions asked:
- **Persistence rule edge cases.**
  - Gaps that span missing bars are still refused while two adjacent shared hours remain apart.
  - Alternating hours evade the rule, and a sparse real market evades it the same way (N3c).
  - With three pools, an off-market third pool refuses the window (fail-closed and disclosed), but a real market split over two pools evades the rule (N3c).
  - The fix is the one listed under the verdict. My real-corpus scan shows neither new rule would change a window today, so this is Low.
- **Redaction.**
  - False negatives remain in two forms. A credential word followed by a space and a hex or base58 value of digest or signature length is echoed (N4d); the realistic case is Bearer followed by a 64-hex token. A credential word that is not directly before the value is missed (N4e).
  - False positives remain for ordinary long words and timestamps after key, token or auth (N4f).
  - N4d is partly my own doing. In pass 2 I proposed keeping 64-hex hashes and long base58 runs without saying that a credential word must take precedence, and the builder implemented the exemption as I wrote it.
- **The new retry in connect.** Sound:
  - it retries only on "locked" or "busy", rolls back an open transaction, backs off from 0.05 s and gives up after 8 attempts;
  - a non-lock error is raised at once;
  - a 16-process burst on a fresh database succeeded 5 times out of 5, with one migration row each time;
  - a connection to an existing database is not blocked by another connection's write lock;
  - all three concurrency runs were clean.

### G01 to G41 after repair pass 3

| G | After pass 2 | Now | Reason |
|---|---|---|---|
| G02 | PARTIAL | PARTIAL | N3b fixed. Residual N3c: the persistence rule is evaded by alternating, sparse or split divergence (synthetic only, 0 real windows). |
| G06 | PARTIAL | PARTIAL | N7 fixed (removals are counted and flagged). New N8: the human-readable report hides the selection-bias flag and calls censored windows complete. The JSON report is correct. |
| G39 | PARTIAL | PARTIAL | N4b and N4c fixed; residuals N4d and N4e |
| G16 | PARTIAL | PARTIAL, disclosed limitation | multi-hop routes are not modeled. Recorded by the builder as a disclosed limitation of scenario-only research mode; the user may still reject it. |
| G27 | PARTIAL | PARTIAL, disclosed limitation | the sealed hashes reproduce, but the window was seen before pre-registration, and any new sealed test needs data after 2026-10-23 16:00 UTC. Recorded as a disclosed limitation; the user may still reject it. |
| G31 | PASS | PASS | unchanged: no token-specific claim. The cohort wording is covered by N8 under G06. |
| G32 | PASS | PASS | point-in-time cohort recomputed independently at 6 real decision points; daily replay and sealed rerun reproduce |

Counts: PASS 36, PARTIAL 5 (G02, G06, G16, G27, G39), FAILED 0, NOT_TESTABLE 0.

With G16 and G27 taken as disclosed limitations: PASS 36, disclosed limitations 2, PARTIAL 3 (G02, G06, G39).

Next step:
1. Run the fifth and last repair pass on N8, N4d and N3c (and C3), as listed under the verdict.
2. Re-run these checks with all four attack files unchanged.

If the user accepts N3c as a documented limitation (it has no real window today), only N8 and N4d remain.

# Backtesting and stress module: release report

Date 2026-10-23. Branch `feature/backtesting`, based on `feature/catalyst-firecrawl` at f99c6c7.

## Decision: CONDITIONAL RELEASE, scenario-only research mode

The module may be used for research in a clearly labeled scenario-only mode, off by default. It is not an empirically validated strategy engine, and nothing in it should be read as an expectation of profit.

The release is conditional on two points:
1. Elving accepts the two disclosed limitations G16 and G27, listed below. If either is rejected, the decision becomes HOLD: neither can be fixed in code, and the Phase 16 loop is used up.
2. The module stays research only. No order path, wallet, schedule or paid service is added without a separate approval.

Why not RELEASE: key historical evidence is BLOCKED, so the completion checklist rules out a full release.
- No source holds historical pool reserves, ticks or bins, so exact historical execution cannot be reconstructed. Fills are approximated from liquidity snapshots.
- The strategies have too few sealed-test trades to say anything about an edge.

Why not HOLD: after the Phase 17 fixes, no correctness or security defect of Medium severity or higher is open. The independent reviewer signed off Phase 16 for this mode after five passes. The reviewer's Phase 17 review found two Medium procedure defects (unsafe backup steps; outcome tracking without a bar refresh). Both are fixed and tested, and the reviewer then agreed to CONDITIONAL RELEASE.

## What the module does

- An off-by-default hook in `scout` and `analyze` assesses each analyzed mint once (idempotent request key) or records why it abstained. Assessments cover:
  - execution feasibility and size under loss and impact caps;
  - hypothetical adverse stress with no probabilities;
  - the token's own signal states;
  - point-in-time cohort evidence.
- Reports in Markdown and JSON (schema `memelab.backtest.report/1`) keep the project view (the lab's score and status, unchanged) apart from the entry view. Every group of fields carries an evidence class.
- Social alerts gain a label line only when the module is on.
- `python -m memelab backtest` covers research replays with a cutoff, run inspection and reproduction, stress reports, coverage, and shadow outcome tracking with calibration and drift checks.
- The engine is deterministic and event-driven:
  - fills happen at the next open after decision plus latency;
  - a gap through the stop fills at the open, and the stop wins over the target inside one bar;
  - constant-product execution with per-DEX fees;
  - PumpSwap is priced on its effective reserves;
  - cash and exposure limits are enforced.

## What the evidence says (no inflated claims)

- No reviewed open-source project reached the 70-point adoption bar. The best scored 65.10, so the engine was built here and checked against independent oracles.
- Every strategy's sealed test is INSUFFICIENT_SAMPLE (0 to 9 trades).
- The one walk-forward with an interval that excludes zero is negative: BREAKOUT_CLOSE out of sample, 32 trades, mean -7.1% per trade, 95% interval -13.5% to -1.8%.
- Over the lab's whole discovery universe, every strategy with 30 or more trades loses money after modeled costs: -11.3% to -20.5% per trade net, against -2.4% to -10.3% on paper. Costs turn small paper losses into large real ones.
- Lab statuses barely separate outcomes:
  - only the REJECTED cohort reaches 30 cases;
  - its 24 h return is p10 -77.6%, median -3.3% and p90 +29.5%, counting windows cut short at their last traded price;
  - the selection-bias flag is raised, because 28% of those tokens could not be measured.
- Token age at the decision is the clearest correlate in the outcome study:
  - tokens under 24 h old: median -55% to -68% within 24 h;
  - tokens 7 days or older: -4.8%.
  - This is a correlation, not a cause, and most of those segments are under 30 complete cases.
- Launch-monitor catalysts: 15 of 19 failed within 72 h.
- PumpSwap fees differ by pool (0.30%, 0.55%, 1.25%). Historical runs assume the 1.25% tier unless the pool's fee was observed.
- Data findings for the lab owner:
  - two corrupted mint strings appear in the lab's exports (GAPS C4);
  - the lab rewrote some launch discovery times after the fact (the first committed value is used).

## Disclosed limitations

1. G16: multi-hop routes are not modeled. Execution uses one pool per token.
2. G27: the sealed test window was seen by the Phase 10 whole-period runs before the Phase 11 pre-registration. A new sealed test needs data after 2026-10-23 16:00 UTC.
3. Historical fills are LIQ_SNAPSHOT_APPROX. Exact historical pool state is SOURCE_BLOCKED, and CLMM and DLMM pools are UNSUPPORTED_POOL unless a quote observed at decision time exists.
4. Historical prices come from one provider (GeckoTerminal). The independent checks in Phase 16 agree with it, but no second keyless historical source was available.
5. The corpus covers 17 days of lab history (139,168 hourly bars over 258 mints). 429 of 686 universe mints have no stored bars, mostly screened-out and EVM tokens.
6. The pool-disagreement guard is a heuristic. It refuses windows where pools disagree rather than guessing. Synthetic shapes N3d, N3e and N3f slip through; none occurs in the real corpus.
7. Cohort selection bias is flagged, not corrected.
8. Redaction of diagnostics is heuristic (N4g, N4h, N4i). Credentials are never stored in records.
9. Verified on Linux only (Python 3.13.17, SQLite 3.45.1). Windows and macOS are untested.
10. C-1 is a pre-existing, clock-dependent failing test in the lab's catalyst suite, outside this module.

## Open defects (all Low)

| Id | Area | Note |
|---|---|---|
| N3d, N3e, N3f | pool-disagreement guard | synthetic evasion shapes; 0 windows in the real corpus |
| N4g, N4h, N4i | redaction of diagnostic text | a value after a plain space following a credential word, in rare shapes |
| exit-hour print | outcomes | a single off-market close in the basis pool's last hour sets the return; a real crash in that hour looks the same |
| C-1 | lab tests | pre-existing, outside this module |
| R1 | shadow tracking | `backtest refresh` covers only tokens already in the corpus; importing new lab records and finding pools for new mints still takes Python steps (RUNBOOK.md, "Backfills") |
| R2 | outcomes | a fetch records only its newest bar, so a refresh made more than about six weeks after a window on a busy pool can read that window as "no trades"; refresh at least every few weeks |

Every other finding from the independent audit (D1 to D11, N1 to N8, C1 to C4, T1) is fixed and guarded by tests and mutations. From the Phase 17 re-check, R3 (run files now follow MEMELAB_BT_DB), R4 (the install script checks the repeated run's id, ledger and cache HIT) and R5 (the release-commit check counts a .md file that code reads as evidence, not prose) are fixed. R6 and R7 needed no code change. Details are in audits/backtesting/testing/E2E_RESULTS.md and audits/backtesting/PHASE_16.md.

## Clean-install evidence (Phase 17)

`bash audits/backtesting/release/p17_clean_install.sh <repo> <out>`. Log: audits/backtesting/release/logs/p17_clean_install.log. The run uses a local clone, a fresh venv with pytest 9.1.1 and numpy 2.5.3 only, and no credentials present. Steps:
1. migration from empty;
2. schema rollback and re-apply;
3. offline import of the committed real GeckoTerminal responses;
4. a deterministic run twice: the same run id both times (the id includes the commit, so it is listed with its commit in the hash table), cache HIT the second time, and ledger f9d7dd89c462 at every commit;
5. an opportunity report with adversarial scenarios on the real PAID captures;
6. analyze with the policy off and on: only the one backtest line differs, and the lab database is byte-identical;
7. 244 backtest tests passed;
8. the release audit reports "Needs action: no";
9. the reviewer's document checker passes every check of the hash table, paths, policy defaults, runbook commands and corpus counts against the code, the evidence and a corpus copy.

Full suite after the Phase 17 code changes: 1030 passed, 1 failed (C-1). Every builder mutation set is caught: p05 to p16, p16_repair, p16_repair2 and p17_builder, 222 of 222. `tools/release_e2e.py`: PASS 78 of 78, no network.

## Final hashes

| Item | Hash |
|---|---|
| research database file (data/backtest/bt.sqlite, gitignored) | 5f4ce7239eb4f0b0 |
| sealed-test cutoff dataset (T1 2026-10-23 16:00 UTC) | 35f836f372c4 |
| whole-corpus dataset used by the Phase 10 runs | d838d9037aeb |
| Phase 11 pre-registration | d0b3686f2d61 |
| sealed-test ledgers (reproduced under engine bt-0.2.0) | BREAKOUT_CLOSE 88ae40542f4b, LAB_STATUS e478181404b2 |
| Phase 10 whole-universe runs (run id / ledger) | BREAKOUT_CLOSE b201e999d6e2 / b88184fbaef6; LAB_STATUS 19ff1209a8c5 / b0819ce00d23; MOMENTUM 328b428953a1 / fb0a81672fd9; BREAKOUT_RETEST e3b5638df4f4 / 34524dcda018; RECLAIM fd6c48dc7e07 / d5b3f56215df; MA_CROSS 824ef58f3261 / 4c9485d3f331; RANDOM_ENTRY 852635cfcc7f / e0eef32c342b; ENTER_AT_DISCOVERY 6826f91100fa / 31820d430857 |
| Phase 15 replayed daily report (2026-10-14) | 9e8b48b3299a |
| Phase 17 clean-install run | run id afa0d2f66467 at commit bc7ce30, ledger f9d7dd89c462 (the run id includes the commit; the ledger does not) |

Phase 10 runs were made with engine bt-0.1.0. Under bt-0.2.0 the run ids change (the engine version is part of the config). Ledgers of fully sold trades keep their shape, so the sealed-test ledgers above reproduce.

## Risk disclaimer

Memecoins can lose all their value within hours. In this corpus, among lab opportunities whose window could be observed, 20% fell by half or more within 24 h and 28% within 72 h. About 45% of opportunities could not be observed at all, mostly tokens whose bars were never fetched, so these shares may be off in either direction. The module describes the past and hypothetical scenarios. It does not forecast, rank tokens to buy, or size positions. Labels such as TESTED or RESEARCHABLE mean only that evidence of a certain kind exists.

## Continuing in shadow mode

See RUNBOOK.md, "Shadow-mode calibration":
- run `backtest refresh` and then `backtest outcomes track` hourly (needs Elving's approval for a scheduled task);
- review `outcomes drift` weekly;
- re-evaluate strategies only through a new pre-registration, a new sealed split starting after 2026-10-23 16:00 UTC, and a new strategy version.

## Sign-off

- Builder: CONDITIONAL RELEASE as above.
- Independent reviewer (Phase 16): PASS for scenario-only research mode with the disclosed limitations.
- Independent reviewer (Phase 17): CONDITIONAL RELEASE agreed after re-checking the fixes at efd890d (AGREED; audits/backtesting/testing/P17_REVIEW.md). The record is in audits/backtesting/PHASE_17.md.
- Elving: acceptance of G16 and G27, and of the CONDITIONAL RELEASE, is pending.

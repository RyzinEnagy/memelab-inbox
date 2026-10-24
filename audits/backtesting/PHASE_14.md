# PHASE 14: decision-oriented reports, CLI, alerts

State: PASS. Date 2026-10-23. Entry gate: Phase 13 PASS at 4338810. Reproduced: assess tests passed and 23 of 23 Phase 13 mutations were caught again. After this phase's key fix the set is 24 of 24.

## Changed files

- New: `memelab/backtest/report.py`. Report document `memelab.backtest.report/1`, built from one assessment, and its Markdown. It holds:
  - alert labels;
  - project view against entry view, with the high-status mismatch;
  - fatal-override check;
  - strategy evidence (latest whole-universe run per strategy, ranked by net after costs, paper next to it, under 30 trades not ranked, PAPER_ONLY_PROFIT flag, sealed-test validation record with file and pre-registration hashes);
  - catalyst provenance with collector status and late-crawl warnings;
  - coverage;
  - a structural validator and the JSON Schema;
  - the scout section.
- `memelab/backtest/hook.py`: `enabled`, `latest_assessment` and `alert_context`. The alert context returns None when the policy is off, and UNTESTED when no assessment exists or the lookup fails.
- `memelab/backtest/assess.py`:
  - symbol and the lab's entry condition carried in provenance;
  - catalyst refresh rate-limited to one per mint per hour;
  - request key now includes a hash of the token's own bar history (defect found this phase, below).
- `memelab/backtest/cli.py`: new `stress`, `assess`, `inspect`, `data` and `schema`; `run --as-of`.
- `memelab/cli.py`: when the policy is on, `scout` appends the backtest section after the unchanged body and writes JSON plus per-mint reports. Off: unchanged.
- `memelab/social/alerts_engine.py` and `alerts_core.py`: a token alert carries `backtest` (label, why, request key) and one `Backtest:` text line, only when the policy is on. Dedupe keys, cooldowns, caps and which alerts exist are unchanged (tested).
- Docs: `docs/backtesting/REPORTS.md`, `docs/backtesting/REPORT_SCHEMA.json`.
- Tests: `tests/test_backtest_report.py` (22). `tests/test_backtest_assess.py` now has 27: the scout test checks the body is unchanged and the section appears only when on; a new test covers a changed bar history; another covers the rate limit.
- Evidence:
  - `audits/backtesting/reports/p14_samples.py` and `samples/`: real PAID report in Markdown and JSON, the same analysis judged today (STALE_DATA), G31, G34 and high-status variants, scout section, dry-run alert text, CLI help, coverage;
  - `testing/p14_mutations.json` and its log.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests/test_backtest_report.py tests/test_backtest_assess.py -q` | 0 | 49 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p14_mutations.json` | 0 | 20 of 20 caught |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p13_mutations.json` | 0 | 24 of 24 caught (rerun after the key change) |
| `python audits/backtesting/reports/p14_samples.py` | 0 | 6 reports, all schema-valid; scout run in a temp copy of the lab database |
| `python -m pytest tests -q` | 1 | 1 failed (C-1 only), 976 passed |
| `python tools/release_audit.py` | 0 | Needs action: no |
| `python tools/release_e2e.py` | 0 | PASS 78 of 78, network attempts 0, tracked database byte-identical |

## Gate

Key fields trace back to exact observations and run hashes. The tests check that:
- the report's request key is a stored assessment row;
- every strategy row names its run id, dataset hash, result hash and ledger hash;
- the validation record names its file hash and pre-registration hash;
- quotes carry their observation time;
- the token is identified by chain and mint.

G31, G34 and G35 each pass in both Markdown and JSON:
- G31 (new token): INSUFFICIENT_HISTORY, token-specific evidence NONE or NOT_RUN, and an explicit "fewer than 25 closed hourly bars" uncertainty. No TOKEN_SPECIFIC claim anywhere.
- G34 (blocked provider):
  - blocked quotes show "no quote (HTTP_429)" with no proceeds and a "no usable sell quote" uncertainty;
  - a missing price gives UNTESTED, SOURCE_BLOCKED and retriable;
  - in both cases the symbol, mint and lab score stay visible.
- G35 (paper profit, net loss): a strategy at +40% paper and -5% net ranks below one at +2% net. It is flagged PAPER_ONLY_PROFIT, and the Markdown says "Profitable on paper but not after costs". A 3-trade strategy at +50% is listed as not ranked.

Integration regression covers 8 cases. Missing history, missing quote, new token, disallowed mint, provider outage, high-status mismatch, fatal flag and no assessment each give a schema-valid document and truthful Markdown, with no crash.

## Real sample (PAID, from the committed inbox captures, 2026-10-06 23:48 UTC)

- Label INCONCLUSIVE: PARTIAL_WITH_LIMITATIONS, SCENARIO_ONLY, stress RESEARCHABLE, $599 inside a $250 loss cap and a 5% exit-impact cap.
- The same analysis judged today: UNTESTED (STALE_DATA, 404 h old). The scout run shows the same, because it uses the real clock.
- The strategy table from the real corpus has every rankable strategy net negative after costs. Paper losses are 2.4% to 10.3%; net losses are 11.3% to 20.5%. CATALYST_VERIFIED shows +34.9% net on 2 trades and is not ranked.

## Bounded loop

Pass 1 was green on the unit tests. Generating the real samples then exposed a defect: the G31 variant (same snapshot, 5 bars instead of 300) returned the cached PAID assessment, because the request key did not cover the token's own bar history. Fixed by adding a hash of the bundle's hourly bars to the key; test plus M13-24. Phase 13's own tests used a fresh database per test, so they missed it.

M14-11 survived pass 1. The off-switch was checked both in the alert engine and in the hook, so removing one check changed nothing. The engine now relies on the hook's single check, and the mutation targets that check: caught.

Pass 2: all green.

## Independent negative review

Wrong-but-plausible outputs invented and caught (20 mutations):
- missing assessment shown as INCONCLUSIVE (M14-1); fatal flag loses the label (M14-2);
- strategies ranked by paper (M14-3); tiny samples ranked (M14-4); paper-only profit unflagged (M14-5);
- high-status mismatch hidden (M14-6); fatal override undetected (M14-7);
- blocked quote given made-up proceeds (M14-8); abstained candidate loses the lab view (M14-9);
- alert hides a missing assessment (M14-10); alerts change when off (M14-11); scout section when off (M14-12);
- paper value shown as executable (M14-13); report implies Maxun runs (M14-14); late crawl unwarned (M14-15);
- robot refresh bursts (M14-16); old assessment age hidden on alerts (M14-17);
- `--as-of` ignored (M14-18); new token shown with token-specific evidence (M14-19); missing-quote uncertainty dropped (M14-20).

## Collector transparency

Catalyst records show:
- origin;
- capture method (MAXUN, FIRECRAWL, LAB_CATALYST, LAB_LAUNCH_MONITOR);
- first-known and available times;
- the claimed publication time with its confidence;
- historical as-of proof;
- the collector's run status;
- warnings (LATE_CAPTURE, LATE_CRAWL, UNVERIFIED_MINT).

Every report states that Maxun is NOT_ADOPTED with no robot running and no schedule approved (`maxun_running: false`, tested even with a MAXUN-captured record present).

Robot observations create no alerts. They only request a re-analysis, which is deduplicated, rate-limited to one per mint per hour and never a verdict, so the scout's fatal gate still applies.

## Limitations

- No real catalyst record exists for the sample mint, so collector rows were shown with a test capture only.
- The strategy evidence is whole-universe history, not this token's.
- "Good entry" means execution feasibility under hypothetical stress, not a forecast.

NEXT ELIGIBLE PHASE: 15.

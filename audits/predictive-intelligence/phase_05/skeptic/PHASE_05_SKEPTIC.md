# Phase 05 independent skeptic review

Reviewer: orchestrator's independent skeptic (PI-D-013), fresh context. Reviewed HEAD `c89bb02` on `feature/predictive-intelligence`, in my own clone `/home/claude/pi_orchestration/skeptic_05` (no write inside `/home/claude/memelab-inbox`). Work 2026-10-24, about 11:40Z to 12:15Z.

Verdict: no material failure found. Four minor findings, one of them the new counterexample (CX-05). The as-of invariant held under every attack I made on the real store; the gaps are untested branches and one vendor assumption that live calls falsify.

## Checks run

| # | Check | Command or input | Result |
|---|---|---|---|
| 1 | Full suite at HEAD | `MEMELAB_DB=<tmp> python -m pytest tests -q` in my clone | `1 failed, 1059 passed in 164.16s`, only `test_dedup_corroboration_resurface_denial` (known); stray `data/reports/20261024_1145_BRETT_0x532f.md` left by an existing test, removed by hand |
| 2 | Social guard | `python -m memelab social guard` | exit 0, `"violations": []` |
| 3 | Release audit | `python tools/release_audit.py --history` | exit 0, "Needs action: no." |
| 4 | Independent rebuild of the store from committed artifacts | `skeptic/phase05_rebuild.py` (my script): exports from git at `98338a8`, all 147 `raw/*.json.gz` checked against both hashes in `MANIFEST.csv`, ingested in retrieval order, series statuses from `data/series_status.json`, provider AND capture snapshots built, compared with a copy of `/home/claude/pi_research/p05/predictive_store.sqlite` | 89 exports, 1,501 events, 1,500 stored, 1 refused (`MukLDtJ8...`, 31 bytes); 3,000 of 3,000 snapshot hashes identical (the phase's own rebuild compared provider only); candle, decision and response key sets identical; every candle's `available_at`, basis and revision kind identical; `verify` [] |
| 5 | Series statuses against raw | same script: each committed status re-derived from the identity, HTTP code and kept candles of the reads it names | 115 series (104 OK, 9 IDENTITY_MISMATCH, 2 NO_DATA), 0 disagreements |
| 6 | Holdout seal on the actual requests | `before_timestamp` parsed from every URL in `MANIFEST.csv` and `evidence/backfill_calls.json`; candle starts inside every raw body | max `before_timestamp` 2026-10-16T10:42:06Z, max candle in any body starts 10:40Z (ends 10:45Z), seal limit 2026-10-16T23:00Z; URL equals `boundary_at` for all 147; the 8 inbox15 calls end by 2026-10-07T17:18Z; the two `holdout_contacted` mints (`CnPL1x...`, `Tm2iq...`) have 0 reads; all 96 plan boundaries equal floor of the pool's last development decision |
| 7 | Re-derived numbers | `sources.fetch_scope` over the 1,500 stored decisions; store sums | DEVELOPMENT 541, NOT_FETCHED_SEALED 62, NO_POOL_AT_DECISION 322, OUT_OF_SCOPE_CHAIN 575, 96 series (match); 98 candles dropped after the boundary, 8,212 quote-side candles refused, 7,223 unchanged re-reads, 15 HTTP 429 (match) |
| 8 | Phase 04 vs Phase 05 window-dependent opens | my own matcher over `/home/claude/pi_research/p04_gt_raw/` (pool by meta base, positions deduplicated) | 57,584 positions, 80 differ, all in open only or open plus high or low (40, 22, 18 with first-occurrence dedupe; the phase reports 36, 23, 21, the split depends on which duplicate page-edge candle is kept); 0 in close or volume; 84 pools, 9 quote-side skipped (match) |
| 9 | Token fix works (PI-D-038), independent of the identity code | `xsrc_log_close_over_thesis_price` from the real provider snapshots | the 9 `token=<mint>` pools: median -0.044, max abs 0.167; the 510 OK_BASE values: median 0.0, p95 abs 0.10. The refused default bodies would sit near ln(3,325) |
| 10 | Revision trap (new, not the phase's new-candle trap) | `skeptic/phase05_revision_trap.py`: 30 random real decisions with a candle value; a VALUES revision of the newest pre-decision candle (close and volume x1000) inserted available at T+1 s, then at T | changed 0 of 30 at T+1 s, 30 of 30 at T |
| 11 | Retrieval metadata after the decision | `skeptic/phase05_purge_probe.py`: every OK pool given a later (2026-10-25) honest empty read recorded NO_DATA with the same boundary; all 1,500 provider snapshots recomputed | 0 of 1,500 changed (tombstones are time-gated; the extra `cover_complete` flips nothing on this data) |
| 12 | PI-D-011 rule 3 on real rows | SQL on the store copy | 0 decisions before `token_first_seen_at`, 0 null, 0 before `created_at`; all basis EXPORT_COMMIT; every row has `recorded_at` |
| 13 | Idempotency, full history, append-only on real data | re-ingest all exports and one archived read into a copy | 0 decisions, 0 responses added, `duplicate_read` true, counts unchanged; a history missing the newest export refused; UPDATE refused by trigger |
| 14 | Multiple pools per mint, mints per pool | store and all 89 exports | 0 mints with two point-in-time pools across decisions, 0 pools with two mints, 0 chain changes; 23 mints change pool fields and 45 change `first_pool_at` across exports (the store correctly takes the decision's own export, see mutation 6) |
| 15 | Isolation | `grep` for imports of `memelab.predictive` outside the package; `git diff --name-only 074953d c89bb02` | no importer; only `audits/`, `docs/predictive-intelligence/`, `memelab/predictive/` (three new modules, `__init__.py` docstring only), Phase 05 tests and fixtures; `data/private/` gitignored; `connect` refuses `db.DB_PATH` and `data/memelab.sqlite`; tracked tree clean after the suite |
| 16 | The phase's mutation run | `python -B probes/mutation_asof.py /tmp/...` | control passes, 35 of 35 caught (reproduced) |
| 17 | My mutations (not in the phase's list) | `skeptic/phase05_mutations.py`, three Phase 05 test files, no `-x` | control 66 passed; 6 of 11 caught, 5 survive (finding m3) |
| 18 | Live vendor semantics | 4 GeckoTerminal calls, 11:55Z to 11:57Z, at least 12 s apart (free, 0 credits; please add to COST_LEDGER) | see finding m2 |

Caught mutations: provider-lag availability from candle start (4 tests fail), boundary drop by candle start (2), reference candle chosen by start (1), every read claims full vendor history (1), vendor NO_DATA as an as-of fact (3), reconstructed values labelled FACT (2).

## Findings

### m1 (MINOR, the counterexample CX-05): the identity check trusts the recorded parameter, not the request

`store.gt_identity(body, mint, token_param)` gets `token_param` from `resp["params"]["token"]`; the URL actually sent is never read. A body fetched WITHOUT `token=` but recorded with `params={"token": mint}` is accepted as OK_TOKEN_PARAM. `skeptic/phase05_counterexample.py` takes the real archived default read of pool `6brAAmd965v3amhS6nFX2Fr6ytQC2dPY7M8XkxYRrsNn` (mint `HwJyyn...` is the quote; its URL has no `token`):

- recorded honestly: MINT_IS_QUOTE, 0 candles kept, feature missing VENDOR_IDENTITY_MISMATCH;
- same bytes, params `token=<mint>`: OK_TOKEN_PARAM, 591 candles kept, `xsrc_log_close_over_thesis_price` = +3.69 (a price 40 times the thesis price), `verify` [];
- the real `token=<mint>` re-read: OK_TOKEN_PARAM, 591 candles, -0.167.

Nothing catches it: no test, `verify`, the truncation check or the recompute. My mutation "any token parameter counts as the mint's price" (`if token_param:`) also survives all 66 tests. This is the slip the phase itself made in its first inbox15 pass (evidence row "Inbox comparison"), so it is plausible, not theoretical. Real data unaffected: URL and params agree on all 147 archived reads (check 6). Fix: derive the token from the URL query in `ingest_gt_response`, refuse a read whose params and URL disagree, require `token_param == mint` exactly (never any truthy value), add both tests. PI-D-038 says Phase 06 labels follow this rule, so fix before Phase 06.

### m2 (MINOR): "fewer candles than the limit means the vendor has nothing earlier" is false

Contract line 209 and `cover_complete` assume a short page means no earlier history (only retention named as a risk). Live: pool `7Lr2oc9kUu2UsWvYnAnH4fFe6CNqsW83eSwUyZPa5hQ6` (mint `BvkPHKx2...`), `before_timestamp=1792000000` (2026-10-14T17:46Z) returned 0 candles; `before_timestamp=1791500000` (2026-10-08T22:53Z) returned a candle at 2026-09-28T07:15Z. The vendor bounds each request by time, so an empty or short page does not prove nothing earlier. Two other pools whose first stored candle is 24 h and 49 h after `first_pool_at` (`HGLSAK3n...`, `GZwUWL7S...`) did return nothing earlier (the first candle is genuine there). Effect on this phase: 3 values of the `BvkPHKx2` decision (2026-10-15T10:13Z) are BEFORE_FIRST_CANDLE (HEURISTIC basis, model-usable) where the honest reason is retrieval censoring; SOURCE_COVERAGE's "58 of 115 series show the vendor's whole history" is not established. 24 h windows are unaffected wherever the vendor's request window is longer than about 25 h (observed at least 10.6 days). Matters for Phase 06: the halt target ("no trade ... 18 h to 48 h after entry") must not read an empty page as "no trade". Fix: treat a short page as complete only back to a measured request-window bound, or mark it unknown; reword the contract and the coverage count.

### m3 (MINOR): five protections no test exercises

Each surviving mutation leaves all 66 Phase 05 tests green (`skeptic/phase05_mutations.json`):

1. `gt_identity` accepts any truthy token parameter (m1).
2. The as-of view without its `period_s` filter (iteration 1e says it was added to stop 15-minute candles mixing in; nothing tests it).
3. Token row taken from the newest export instead of the decision's export (future token facts; on real data it changes `first_pool_at` for 1 decision and `first_seen_at` for 8).
4. A revision compared with the oldest version instead of the latest (A to B to A). Current code is right (I checked: three versions, the last visible), just untested.
5. `check_plan` without its "boundary after the pool's last development decision" clause (all 96 real boundaries are right).

Add one test per item.

### m4 (MINOR, observation): the truncation proof cannot see retrieval metadata in provider mode

`truncated_copy` keeps every `predictive_source_status` and raw response in provider mode, and `AsOfView.series_status` does not filter by `checked_at` there, so a leak through series statuses or `cover_complete` would not show in `asof_real_truncation.json`. It is by design (retrieval metadata, RETRIEVAL censoring), and probe 11 found 0 of 1,500 snapshots move when every pool gets a later empty read. Say this limit of the proof in the evidence; m2 is the case where the metadata does reach a HEURISTIC reason.

## Claims confirmed

As-of invariant (1 s after absent, at the decision present; revisions only from their read); candle start versus end and boundary handling (mutations caught); duplicate ingestion (no new rows); 31-byte mint refused and counted; same symbol different mints and pool ownership; decision time from the first export commit of the exact row, never `created_at`; dead and unquoted pools and out-of-scope rows kept with explicit reasons (P09: 2 NO_DATA, 322 no pool, 575 other chain, 62 sealed); holdout post-decision windows unread; store never touches `data/memelab.sqlite`; nothing existing imports the package; suite, guard and release audit reproduce at `c89bb02`; the archive rebuild reproduces both modes byte for byte.

## Counterexample CX-05

Script: `/home/claude/pi_orchestration/skeptic/phase05_counterexample.py`, run `python3 phase05_counterexample.py /home/claude/pi_orchestration/skeptic_05`. A real default-side read of a quote-side pool, ingested with a params record that claims `token=<mint>`, is accepted as the mint's price. The snapshot then carries another token's closes (`xsrc` +3.69 against -0.167 for the honest re-read) with a clean `verify`. No test, check or recorded probe catches it. Fix in m1.

## Scripts and outputs

`/home/claude/pi_orchestration/skeptic/phase05_rebuild.py`, `phase05_mutations.py` (+ `phase05_mutations.json`), `phase05_counterexample.py`, `phase05_revision_trap.py`, `phase05_purge_probe.py`. Working copies under `/tmp/claude-0/sk05/` (store copies, suite log, 4 vendor bodies `gt_*.json`).

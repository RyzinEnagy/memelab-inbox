# Maxun robot end-to-end record (Phase 06A)

Status: NOT_ADOPTED (decision EXISTING_TOOL_WINS). Maxun is not claimed LIVE VERIFIED and is not operational in the lab. What follows is the one evaluation run, and the tests that prove the kept capture path.

## The one live Maxun run (evidence, not an integration)

| Step (contract E) | Result |
|---|---|
| 1 authorized public page | `https://solana.com/news` (robots.txt: `User-Agent: * Allow: /`) |
| 2 repeatable configuration | `POST /api/v1/robots/crawl` body saved in `bakeoff/p06a_maxun/robot_crawl_create.json`; client `bakeoff/p06a_maxun_client.py` (the key is read at runtime from the work computer and never written; responses are scrubbed of it) |
| 3 real run | robot `ef435421-7926-43d2-89ea-0ad337cf05db`, run `005f58a3-4fff-4b2e-8750-b5e4947eb291`, started 17:26:35.157Z, finished 17:26:43.517Z, 8,360 ms, `status: aborted`, `isPartial: false`, `error: null` |
| 4 extraction retrieved through the verified Cloud v1 API | `GET /api/v1/runs/{id}` (`bakeoff/p06a_maxun/run_crawl1.json`): 5 crawl pages with metadata, markdown and html null |
| 5 schema validated | the 5 pages pass through `pagefields.extract`; title 5/5, date 4/4 against raw HTML |
| 6 persisted through the existing registry | only as evidence (`collector=MAXUN`, `evidence_only=True`) into a scratch database by `bakeoff/p06a_ingest.py`; the runtime refuses MAXUN as a collector |
| 7 rescan without duplicates | proven for the kept path (second pass 68/68 duplicates); a Maxun rescan was refused for lack of credits (HTTP 403, `bakeoff/p06a_maxun/run_start_crawl2_nocredit.json`) |
| 8 corrected version separate | proven for the kept path with a modified copy (test_g37_corrected_page_is_a_separate_immutable_version) |
| 9 report/alert references | not applicable to Maxun; captures surface in Phase 14 reports with their first_seen_at |
| 10 scheduler safety | no schedule created; `GET /robots/{id}/schedule` null, `GET /schedules` [] before and after; lab policy refuses schedules unless approved |

Credits: 5 before, 0 after (`bakeoff/p06a_maxun/usage_before_crawl.json`, `usage_after_crawl.json`).

## Tests (G36-G41) on the kept path, using the real bake-off captures

`python -m pytest tests/test_backtest_webcapture.py -q`: 20 passed.

| Scenario | Tests |
|---|---|
| G36 history laundering | test_g36_old_page_crawled_today_is_unknown_as_of_at_its_claimed_date (real Maxun capture of a 2022 page), test_g36_a_backdated_date_edit_cannot_move_availability_earlier |
| G37 cross-collector dedup and revision | test_g37_three_tools_one_canonical_record (real plain/Crawl4AI/Firecrawl captures of one page), test_g37_lower_confidence_text_date_is_not_a_new_version, test_g37_corrected_page_is_a_separate_immutable_version |
| G38 identity and spoofing | copycat domains and off-scope pages (5 cases), untracked GitHub owner, redirect off the allowlist, ticker and prompt-injection text staying a claim with no mint |
| G39 reliability and bounds | 401, 429, timeout, 503 with a parsable body, selector drift, off-allowlist, partial run, page cap; DEGRADED and DOWN source states; no linked record from a broken source |
| G40 API, webhook and schedule safety | schedules refused without approval, disable switch, MAXUN refused as runtime collector, no Maxun or webhook code anywhere under memelab/, evidence client used Cloud v1 only with no schedule, webhook or monitoring calls |
| G41 measured adoption | scores on the pre-registered sample, decision file, no maxun dependency; captured claims alone never form a positive linked catalyst. Fatal-flag precedence over a verified multi-origin catalyst: tests/test_backtest_catalyst.py::test_g41_convincing_catalyst_cannot_defeat_a_fatal_flag (Phase 09, with the strategy) |

Mutation check: `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p06a_mutations.json` exit 0, 9 of 9 caught (log `testing/logs/p06a_mutations.log`). The fatal-flag mutation moves to the Phase 09 set with its test.

## Webhooks

The lab has no webhook receiver and adds none. Remote collection, if ever adopted, would use an authenticated poller; a webhook would need request signing and replay protection first (contract E).

# PHASE 06A: Maxun robot feasibility, bake-off and ingestion decision

State: PASS (evaluation gate). Decision: EXISTING_TOOL_WINS; Maxun NOT_ADOPTED, not live in the lab. Date 2026-10-23. Entry gate: Phase 06 PASS at f6641ce (sources and real-fixture tests 17 passed; p06 mutations 12/12; release e2e PASS 78/78).

## Changed files

- New runtime: `memelab/backtest/sources/pagefields.py` (one field extractor for any tool's page output: title, claimed date with a confidence level, tag; never from the URL), `memelab/backtest/sources/webcapture.py` (bounded capture path for the existing collectors: use-case allowlists incl. tracked GitHub repos, redirect check, page cap, claim fingerprint so two tools make one record, REFINED_DATE rows, failure states that record nothing, collector policy with schedules off, MAXUN refused at runtime).
- New tests: `tests/test_backtest_webcapture.py` (20, G36-G41 on the real bake-off captures).
- Changed: `audits/backtesting/testing/mutate.py` (copies audits too, since tests read committed evidence).
- Evidence: `research/MAXUN_BAKEOFF_PREREG.md`, `MAXUN_BAKEOFF.md`, `MAXUN_ADOPTION.md`, `MAXUN_CAPABILITIES.md` (updated), `raw/p06a_maxun_cloud_api_excerpt.md`; `data/MAXUN_ROBOT_REGISTRY.md`; `testing/MAXUN_ROBOT_E2E.md`; `bakeoff/p06a_*` (sampling, runners, Maxun client and responses, Firecrawl records, views, oracle, scorer, scores, ingestion script); `testing/p06a_mutations.json`, `testing/logs/p06a_*`.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python audits/backtesting/bakeoff/p06a_score.py audits/backtesting/bakeoff/p06a_views.jsonl audits/backtesting/bakeoff/p06a_oracle.json` | 0 | scores as in MAXUN_BAKEOFF.md (reproduced independently) |
| `python audits/backtesting/bakeoff/p06a_ingest.py audits/backtesting/bakeoff/p06a_views.jsonl` | 0 | 24 origins, 1 version each, 10 REFINED_DATE, pass 2 all duplicates, 4 old pages UNKNOWN_AS_OF |
| `python -m pytest tests/test_backtest_webcapture.py -q` | 0 | 20 passed |
| `python audits/backtesting/testing/mutate.py audits/backtesting/testing/p06a_mutations.json` | 0 | 9 of 9 caught |
| full suite and release tools | see HANDOFF | |

Spend: Firecrawl 22 calls in this phase (2 docs pages, 20 bake-off pages); about 29 of the approved ~100 used so far. Maxun: 5 of 5 trial credits (one run), 0 schedules, 0 webhooks. Crawl4AI: 20 local pages. GitHub API (unauthenticated, work computer): 15 calls. Plain GETs: 26.

## Gate items

(a) Edition, license and capability truth: MAXUN_CAPABILITIES.md (Cloud v1, AGPL source not embedded, one functional run, credit behavior and the 402/403 mismatch observed). (b) Fair bake-off or honest insufficient sample: Maxun cells INSUFFICIENT_BAKEOFF_SAMPLE (A) and BLOCKED_EXTERNAL (B); the task was not equal for Maxun, stated plainly. (c) Recorded decision with reviewer objections: MAXUN_ADOPTION.md. (d) Point-in-time fields and safe fallback: webcapture path with first_seen from capture, UNKNOWN_AS_OF for old pages, no mint without verification. (e) G36-G41: 20 tests. (f) Existing suite unaffected: see HANDOFF.

## Bounded loop

Pass 1: bake-off run; 34 records from 24 origins in the first ingestion (Firecrawl's text date came first, a machine date later made a second "version"). Repair: a lower-confidence date never creates a version next to the same title and tag; a later machine date is stored as REFINED_DATE. Rerun: 1 version per origin.
Pass 2: mutation M06A-5 (failed fetch still recorded) survived because failed rows in the test had no view. A 503 that still returned a parsable page was added to G39; caught. Harness fix: audits are copied so evidence-reading tests run.
Pass 3 (independent review by a separate agent with no access to my conclusions): eight objections, all accepted. The Firecrawl date explanation was wrong (an extractor artifact, not a time zone), change detection was overstated, cost was overstated, metrics were missing, the oracle was not independent, the Maxun task was unequal. Corrected in MAXUN_BAKEOFF.md and MAXUN_ADOPTION.md; scores unchanged. Negative control (old page first captured today) was UNKNOWN_AS_OF in every pass.

## Limitations

Maxun's quality was not measured on the sample; a fair retest needs a paid credit budget (about 22+ credits) and Elving's approval. Body-only page edits are not detected by the claim fingerprint. Firecrawl raw outputs were not saved. Raw plain-HTTP and Crawl4AI files are on the work computer (`D:\memelab\backtesting_work\p06a`, bundle `p06a_bundle.zip`), referenced by hash.

NEXT ELIGIBLE PHASE: 07.

# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md).

## Position

- Current phase completed: 02 (Prompt 02: one ingestion contract and the existing browser bridge adapter), 2026-10-10. Prompt 02 replaced the proposed Phase 02 (D-015). Carry-over C-2 (repo-wide content guard) was then built in the same session at Elving's request (D-020).
- Next phase: 03 is SUPERSEDED, so the next proposed entry is 04 (manual capture onto the inbound schema). If Elving supplies Prompt 03, it replaces whatever ROADMAP.md proposes.
- Active branch: `feature/social-intelligence`.
- Phase 02 started from `34830fe` (head of `origin/feature/social-intelligence`, "social-intel phase 01: HANDOFF rewritten for Phase 01"). Branch, HEAD and clean tree matched the Phase 01 handoff; baseline `python -m pytest tests -q` gave `1 failed, 78 passed`, same as recorded.
- Pushed: `b21a854` "Add files via upload" on `origin/feature/social-intelligence` (2026-10-10). The session could not push (git proxy 403: repo not in the session's authorized set; Chrome upload blocked by the tool permission check), so Elving uploaded the 16 changed files by hand through the GitHub upload page in one commit. The session's six local commits (`82f7263` to `98f8b0c`) were replaced by that commit; the session then reset its branch to `b21a854`, confirmed every file matched its local copy (only this HANDOFF line differed), and reran the suite on the pushed tree: `1 failed, 103 passed`, `social guard` exit 0. This HANDOFF correction is a separate, later upload.

## What Phase 02 added

- `memelab/social/ingest.py`: inbound schema `memelab.social.inbound/1`, `SourceUnit`, `SourceAdapter` (members `name`, `units(budget)`), validation, `ingest()` pipeline (event-id dedupe, batch commits with checkpoint, quarantine, per-connector health, coverage, run record), `Budget`, `with_retries`, redacting JSON logger, `event_record()` for read-back.
- `memelab/social/bridge_adapter.py`: `BridgeInboxAdapter` over bridge result files (`soc:<platform>:<source_id>` keys; other keys ignored; `challenge` login/captcha/blocked and 429 mapped to connector states; unreadable files become a DOWN unit for that file).
- `memelab/social/cli.py`, wired in `memelab/cli.py` (1 line): `python -m memelab social ingest --results|--file|--pull ... [--ref] [--db] [--batch-size] [--max-items] [--max-units] [--max-age-hours] [--now] [-v]` and `python -m memelab social status [--event <id>]`.
- `memelab/bridge/social.js`: `__SOC.hash` (same normalization as `store.text_hash`) and `__SOC.put` to shape units into `window.__ML.last` for `__ML.ship`.
- `memelab/social/schema.py`: migration 2 (`social_ingest_runs`, `social_ingest_checkpoints`, `social_ingest_quarantine`, `social_observation_provenance`), `LATEST`, `ALL_VERSIONS`.
- `memelab/social/store.py`: `record_observation(content_hash=...)` for collector-computed hashes (backward compatible).
- `tests/test_social_ingest.py` (18 tests), `tests/fixtures/social/inbox/soc_fx01.json` (invented accounts, hashes and summaries; one placeholder `text` value that must be quarantined).
- `tests/test_social_store.py`: version assertions now use `schema.LATEST` / `schema.ALL_VERSIONS` instead of the literal 1 (needed once migration 2 exists; no test was removed).
- `docs/social-intelligence/CONNECTORS_02.md`: route, inbound schema, guarantees, how X and Telegram plug in, limits, exact migration 2 DDL.

## Gate, item by item

- Runnable import CLI on the established route: `test_cli_ingest_persists_verifiable_observation` (CLI `--file`), `test_pull_route_then_ingest` (CLI `--pull` through `github_inbox.pull` with the raw fetch replaced, file lands as `<id>.result.json`, then ingested).
- Persisted verifiable observation: same test reads `event_record('x:fx-x-0001')` and checks content hash, provider vs fetched time, URL, account, source_ref, plan id, schema, visibility, rights basis, metrics, summary; `social status --event` prints it.
- Repeated ingestion idempotent: `test_rerun_is_idempotent` (counts identical, 2 units replayed), `test_replay_from_renamed_file_creates_no_duplicates` (4 duplicates, 0 created), `test_crash_between_batches_resumes_without_duplicates` and `test_budget_stops_cleanly_and_resumes` (end state equals a clean single run).
- Malformed and stale: `test_bad_items_quarantined_good_items_kept` (INVALID, BLOCKED_CONTENT, NOT_PUBLIC quarantined, the item after them stored, payloads only in the private folder, no values in errors), `test_malformed_and_future_units_and_items`, `test_stale_data_is_flagged_not_dropped`.
- One unavailable connector: `test_unavailable_connectors_do_not_mark_all_healthy` (DOWN, LOGIN_REQUIRED, OK, DEGRADED side by side; run PARTIAL), `test_unreadable_files_do_not_end_the_run`, `test_unexpected_error_in_one_connector_is_contained`, `test_all_connectors_down_is_failed_and_exits_1`.
- Retries, logs, hashing: `test_bounded_retries`, `test_logs_never_carry_secrets_or_content`, `test_browser_hash_matches_python` (runs social.js in Node 22; skipped without node), `test_schema_v2_rolls_back_to_v1_only`.

## Carry-over C-2 (repo-wide content guard)

- `memelab/social/content_guard.py`, CLI `python -m memelab social guard [--root <repo>]` (exit 0 clean, 1 violations), `tests/test_content_guard.py` (7 tests, one of which scans this checkout's tracked files).
- Rules: tracked private, wallet or quarantine files; tracked SQLite other than `data/memelab.sqlite`; blocked classes or non-public items inside `soc:*` units; social-only JSON keys (`bio`, `full_text`, `members` ...) anywhere; in the tracked DB, content columns in social tables, `private_content`, summaries over 400 characters, prose in `social_snapshots.text_value`, copied profile text in `catalyst_sources.identity_notes`. Reports location and rule, never the value. Invented fixture content allowed by exact location only.
- Results: feature branch 214 tracked files, 57 JSON, 1 DB, 0 violations. `origin/main` at `6b0a054` (scanned in a temporary worktree): 195 files, 55 JSON, 1 DB, 0 violations. `social_snapshots`: 99 rows, all Jupiter holder-change numbers, `text_value` NULL in every row.
- Open conflict for Elving (D-020): `catalyst plan --verify-traders` ships an X profile `bio` into the inbox and copies title and bio into `catalyst_sources.identity_notes`. Not present in any tracked file today, but the next run that uses it would fail the guard.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest`; numpy required; node optional).
- Outcome after the last code change: exit 1, `1 failed, 103 passed in 3.08s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (carry-over C-1, untouched).
- Social tests: `python -m pytest tests/test_social_store.py tests/test_social_ingest.py tests/test_content_guard.py -q` -> `40 passed`.
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). The tracked `data/memelab.sqlite` is not modified (`git status` clean after the run apart from that file).
- Smoke: `python -m memelab --help` exit 0; `python -m memelab social-note --help` exit 0; `python -m memelab social ingest --file tests/fixtures/social/inbox/soc_fx01.json --db <tmp> --now 1791561600` exit 0, status PARTIAL, 4 created, 3 quarantined, health DOWN / LOGIN_REQUIRED / DEGRADED / OK; second run 0 created, 2 units replayed; `MEMELAB_DB=<tmp> python -m memelab.social.schema status` -> `social schema version 2 latest 2`.

## Things the next phase should know

- No live social read has gone through this route yet; everything is proved on the fixture. The first real X or Telegram collector phase should ship one small unit and check `social status` before scaling.
- Summaries are written by the session in its own words; the verbatim guard cannot run on the cloud side because the text never ships (CONNECTORS_02.md, limits).
- When this branch reaches `main`, `init_db()` on the tracked database will create the migration 2 tables (empty, no source text). Quarantine payloads live under `data/private/quarantine/` (gitignored).
- Social tables are still not in the `state.py` export (scheduled-run phase).

## Blockers and open decisions

- Decide what to do about the catalyst X-profile `bio` (D-020).
- Cowork cloud sessions cannot push to `memelab-inbox` (repo not attached to the session). Each phase ends with a manual upload unless the phase runs in a Claude Code cloud session with the repo attached.
- Phase prompts 03 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 103 passed`, and `python -m memelab social guard` exit 0. Then start the next phase.

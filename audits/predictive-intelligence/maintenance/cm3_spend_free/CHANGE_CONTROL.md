# Change control CM-3: spend-free maintenance (ED-3, ED-7, ED-9, ED-8 preparation)

Approved by Elving on 2026-11-09 ("do everything that doesn't require spend"). Written and committed before any code change.
Branch `maint/catalyst-export` from `feature/predictive-intelligence` at `60eb729`; the orchestrator merges it later. Decision ids
PI-D-130 to PI-D-139. Records live in this folder; DECISIONS.md gets short entries only.

Spend: none. No paid call, no new source, no collection change, no scheduled task created or changed, no key created, nothing
pushed or sent. Lab rules hold: no raw third-party social content in the repository, no X bios, identity by chain plus mint, no
credential printed or committed.

## Items and how each is checked

### 1. ED-3: catalyst and social tables in the state export (PI-D-130)

What changes

- New module `memelab/catsoc_export.py` (format `catsoc-export-1`). `memelab/state.py` calls it from `export()` only when the
  export flag is on; three added lines, nothing else in `state.py` changes.
- Export flag: OFF unless the environment variable `MEMELAB_STATE_EXPORT_CATSOC` is `1`, or `data/config.json` holds
  `{"state_export": {"catalyst_social": true}}` (the JSON value true only; anything else, a missing or malformed file is OFF).
  With the flag off the export is byte for byte what `state.py` at `60eb729` writes.
- With the flag on the export gains one top-level key `_catsoc`. `state.import_` reads only `_tables` (or the old flat layout,
  which skips keys starting with `_`), so the existing importer ignores it and nothing changes for the scheduled runs' own import.
- What `_catsoc` holds (an explicit column list per table, never `SELECT *`):
  - catalyst: events (ids, a hash of `event_key`, narrative id, category, source id, times, evidence status, counts, status,
    expiry; no title, description, URL or free text), revisions (ids, times, kind, field, and the old and new value only for the
    enum fields `evidence_status` and `status`), event sources (event id, item id, role), items of exported events (id, source id,
    sha256 of the URL, sha256 of the normalized body, the exported event's linked mints that appear verbatim in the URL or body,
    times; no URL, title, body, author or raw JSON), token links (event id, chain, mint, link type and strength, verified flag,
    linked time), sources (id, group, kind, tier, identity status, added time), assessments (event id, mint, time, verdict, triage
    score, expiry).
  - social, only items with an exact chain plus contract resolution: accounts, items, observations, versions, resolutions,
    claims, extractions, trader links, token refs, registry entities of kind SOCIAL_ACCOUNT and ACCOUNT_STATUS reviews. Account
    ids, item keys, trader ids, entity ids and review targets are replaced by `sha256("catsoc-export-1:" + value)[:32]`; no
    handle, display name, profile URL, bio, note, label, mention text or reason. Summaries (the lab's own words) are kept only
    when at most 200 characters, one line, with no `@` and no `http`; otherwise withheld and counted.
  - Window: 30 days (catalyst events by `updated_at`, social items by `first_ingested_at`), computed from a `now` the caller can
    fix.
- Self-check before writing: every key is on the column list, and `memelab.social.content_guard.check_json` passes on the
  section. On a violation the section is replaced by `{"version", "withheld": "GUARD_VIOLATION", "rules"}` (rule names only)
  and the export still succeeds; a scheduled export never fails because of this section.
- Importer path back: `python -m memelab.catsoc_export import SRC DEST` copies `_catsoc` into `catsoc_*` tables of a separate
  SQLite file (refused when DEST is the lab database, a file of another schema, or a path inside the repository outside
  `data/private/`). Idempotent: rows are keyed by their row sha256. The lab's own catalyst and social tables are never written.
- Phase 10 adapter: `memelab/predictive/socialcat.py` is pinned by 18 registry entries (`R.code_changes`) and by the Phase 18
  pin file; editing it would change the status of those entries. So it is not edited. A companion module
  `memelab/predictive/catsoc_adapter.py` reads export versions (`[{commit, commit_time, doc}]`, oldest first, as
  `decisions.candidates` reads them) and feeds the unchanged `socialcat.classify_catalyst` and `socialcat.social_as_of`:
  - every exact row (row sha256 without `id`) gets `available_at` = the commit time of the first export version that contains
    it; a row is visible at T only when `available_at <= T`, and each time field the classifier or the social function uses is
    replaced by `max(own time, available_at)`, so nothing is seen before the export commit that carried it;
  - mutable rows (events, accounts) use the newest version visible at T;
  - mint naming uses `mints_named`, duplicate collapse uses the two hashes (the adapter hands the classifier lab-made stand-in
    strings built from them; identical hashes give identical stand-ins);
  - states: CATALYST_TABLES_NOT_EXPORTED and SOCIAL_TABLES_NOT_EXPORTED when no version at or before T carries `_catsoc` (today:
    every real version); NO_EXPORTED_CATALYST_FOR_MINT and NO_EXPORTED_SOCIAL_FOR_MINT when the section exists and holds nothing
    for that exact chain and mint; otherwise the classifier's own states. Evidence class stays TEST_ONLY until a phase registers
    catalyst targets on exported rows (ED-3's last step).

Checks

- Flag off: the export of a populated lab database is byte identical to the export of the `60eb729` `state.py` (copy kept as a
  test fixture with its sha256), with the clock fixed.
- Flag on: the column lists are exhaustive (a planted extra column, a planted title or body, a planted bio key and a long or
  handle-bearing summary are all kept out); the guard self-check replaces a violating section; the old importer ignores the
  section; the new importer round-trips and is idempotent; the adapter refuses nothing before the export commit (a row exported
  later is invisible before that commit even when its own time is earlier); exact chain plus mint only (a ticker-only link and a
  link to another chain are not identity).
- Real exports: the adapter over the git history of `data/state/latest.json` (78 versions) gives CATALYST_TABLES_NOT_EXPORTED
  and SOCIAL_TABLES_NOT_EXPORTED for every real decision mint; the exporter with the flag on is run on two real databases (a copy
  of the tracked `data/memelab.sqlite`, and a temporary database built by importing the real `data/state/latest.json`), and on a
  fixture-populated catalyst and social database; each output is placed in a scratch clone and committed there, then
  `python -m memelab social guard` and `tools/release_audit.py` run on that clone.

### 2. ED-7: alert delivery as a push file (PI-D-131)

- `memelab/predictive/reports.py` (Phase 18's own module; not in the Phase 18 pin file) gains one delivery path: `alert_run(...,
  send="push_file")` and `python -m memelab.predictive.reports alerts --send push_file`. After the dry-run evaluation it writes
  `outbox/push/push_run_NNNNNN.txt` with one short line per new alert, and records one `alert_deliveries` row per alert (transport
  `push_file`, status `dry_run_preview`). Mode stays `dry_run`; the policy file and its sha256 do not change.
- The line: severity, policy in words, the token label (symbol text through the existing token-text rule, chain, exact mint) and
  the local alert number. No probability, no percent sign, no number other than the alert number and the mint, no trading word
  (`check_text` plus a push-line check that refuses `%`, `probab`, `estimate`, `interval` and `base rate`). At most 240 characters.
- `--send` with no channel, `--send` of any other channel name and `send=True` are refused exactly as today. No network code is
  added; a scheduled task (not created by this change) would read new push files and send each line as a push notification.
- Checks: tests for the file content, the refusals, no file without new alerts, no change to the default dry run (same outbox and
  database rows as before for `send=False`), and no network.

### 3. ED-9: signing the private predictive state (PI-D-132)

- `memelab/predictive/integration.py`: HMAC-SHA256 over the pass chain tip. After each pass, when a key is configured, write
  `STATE_SIGNATURE.json` = `{"version": "state-sig-1", "seq", "tip", "hmac"}` with `hmac = HMAC-SHA256(key, "memelab-predictive-
  state-sig-1|" + seq + "|" + tip)`. The tip record id commits to the previous pass and to the sha256 of every state file, so the
  signature covers the whole state.
- Key: the file named by `MEMELAB_PREDICTIVE_STATE_KEY_FILE`, or the value of `MEMELAB_PREDICTIVE_STATE_KEY`. A key file inside
  the repository is refused; a key under 32 bytes is refused. The key is never printed and never part of an error message.
- `load_state` with a key: a state with passes and no signature, or a signature that does not match, is StateTampered. Without a
  key nothing is written or checked (byte identity of every existing output); `signature_status()` and the new CLI subcommand
  `sign-status` record the state as UNSIGNED_NO_KEY (or SIGNATURE_NOT_VERIFIED_NO_KEY when a file exists). `sign` adopts an
  existing unsigned chain after checking it.
- No key is created. Where Elving would put one is documented in `SIGNING.md`.
- `integration.py` is in the Phase 18 pin file; a new amendment file `tests/fixtures/predictive/phase18/PINNED_SHA256_PI-D-132.json`
  re-pins it (and `state.py`) with the reason and the old pin, like PI-D-120; the original pin files stay as they are.
- Checks: tests for signed round trip, tamper after signing (reseal attack: a rewritten line with recomputed record ids and file
  shas is refused with a key), unsigned state refused with a key, unsigned allowed and recorded without a key, short key and
  in-repository key file refused, the key never in output or exception text.

### 4. ED-8 preparation: what turning the flag on means (PI-D-133)

- `FLAG_ON.md` in this folder: the `data/config.json` key, what appears in the scout report and the analyze output, what is
  written where, how to turn it off, and what does not change. No scheduled task is changed.
- Test: a flag-on scout run on rows taken from the real export (`data/state/latest.json`) keeps the 100-point score, fatal flags,
  statuses, watchlist, rejections and the report above the appended section byte for byte equal to the flag-off run.

## Global checks after the code commit

Full suite (only the two known clock-dependent catalyst failures), `python -m memelab social guard`, the Phase 06 seal check,
`python tools/release_e2e.py`, `tools/release_audit.py --history` on a single-branch clone of this branch, the flag-off identity
tests above, `git status` clean. Then `SKEPTIC_PACKET.md` for the orchestrator's skeptic; status NEEDS_REVIEW until then.

## Rollback

`git revert` of the code commit. The export flag, the push file and the signing key are all opt-in; with none of them set the
lab and the engine behave as at `60eb729`.

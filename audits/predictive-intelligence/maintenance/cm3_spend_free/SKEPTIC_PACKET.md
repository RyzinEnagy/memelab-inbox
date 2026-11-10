# Skeptic packet: CM-3 (spend-free maintenance)

For the orchestrator's independent reviewer (PI-D-013). Task, paths and commands only.

## Task

Try to show that any of these is false:

1. With the export switch off, `python -m memelab.state export` writes the same bytes as the exporter at `60eb729`, for any
   database (including one with catalyst and social rows and a malformed or non-boolean `data/config.json`).
2. With the switch on, the export differs only by one `_catsoc` member, and that member never carries third-party text: no title,
   body, URL, author, handle (including inside a catalyst `source_id`), display name, bio, note, label, mention text, reason,
   raw JSON, database row id, or a summary over 200 characters or with `@`, `http` or a line break. Try planted columns, planted
   keys, odd types, unicode, a source id with a handle, a summary that passes the length check but carries a handle without `@`.
3. A violation or an exception inside the section never fails the export and never writes the offending value.
4. The engine never sees an exported row before the commit time of the first export version that carried it (`available_at`),
   even when the row's own times are earlier; identity is exact chain plus mint only (ticker matches and other chains are not
   identity); a hand-edited or withheld section is ignored.
5. The importer never writes into the lab database, a tracked path outside `data/private/`, or a database of another schema.
6. `alerts --send push_file` writes only the documented lines (no probability, percentage, estimate, interval, trading word,
   local path, newline, over 240 characters), records them as dry-run previews, sends nothing, and changes nothing for
   `send=False`; every other `--send` value is refused before anything is written.
7. With a signing key configured, a rewritten state (record ids and file sha256 recomputed), an unsigned state, a signature for
   another pass or a wrong key is refused; without a key nothing changes; the key never appears in output, an exception message,
   a file in the repository or a log; a key file inside the repository and a key under 32 bytes are refused.
8. The flag-on scout on rows of the real export keeps the 100-point score, fatal flags, statuses, watchlist, rejections and the
   report above the appended section byte for byte, and its stdout differs only by the same section.
9. The exact scheduled-run steps in `FLAG_ON.md` do what they say (merge, not overwrite, `data/config.json`; persistent state and
   alert database; key prefix on each command; push file read and moved), and nothing in them creates spend or sends anything
   other than the push lines.
10. The documents (`EXPORT.md`, `FLAG_ON.md`, `PUSH_DELIVERY.md`, `SIGNING.md`, `CM3_EVIDENCE.md`) match the code.

## Artifacts

- `audits/predictive-intelligence/maintenance/cm3_spend_free/`: `CHANGE_CONTROL.md`, `EXPORT.md`, `FLAG_ON.md`,
  `PUSH_DELIVERY.md`, `SIGNING.md`, `CM3_EVIDENCE.md`, `CM3_RESULTS.json`, `evidence/flag_off_identity.json`,
  `evidence/real_export_check.json`, `evidence/logs/`, `postcommit/` (after the follow-up commit).
- `docs/predictive-intelligence/DECISIONS.md` PI-D-130 to PI-D-136; `HANDOFF.md`; `ROADMAP.md` maintenance table.

## Code

- `memelab/catsoc_export.py` (new), `memelab/state.py` (3 lines), `memelab/predictive/catsoc_adapter.py` (new),
  `memelab/predictive/reports.py` (push path), `memelab/predictive/integration.py` (signing), `.gitignore` (1 line).
- Unchanged on purpose: `memelab/predictive/socialcat.py` (pinned by 18 registry entries).
- Tests: `tests/test_predictive_cm3.py`; amended `tests/test_predictive_integration.py`, `tests/test_predictive_reports.py`,
  `tests/test_predictive_social.py`; pins `tests/fixtures/predictive/phase18/PINNED_SHA256_PI-D-132.json`; old exporter
  `tests/fixtures/predictive/cm3/state_before_cm3.py.txt`.

## Commands

```
cd <checkout of maint/catalyst-export>
git log --oneline 60eb729..HEAD
git diff 60eb729 HEAD -- memelab/state.py memelab/predictive/integration.py memelab/predictive/reports.py
python -m pytest tests/test_predictive_cm3.py -q
python -m pytest tests -q          # then remove data/reports/*_BRETT_*.md, data/memelab.sqlite-shm, -wal
python -B audits/predictive-intelligence/maintenance/cm3_spend_free/probes/flag_off_identity.py /tmp/cm3_foi /tmp/cm3_foi.json
python -B audits/predictive-intelligence/maintenance/cm3_spend_free/probes/real_export_check.py /tmp/cm3_rec /tmp/cm3_rec.json
python -B -m memelab social guard
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -B tools/release_e2e.py
git clone -q --single-branch -b maint/catalyst-export <this checkout> /tmp/cm3_sb && cd /tmp/cm3_sb && python -B tools/release_audit.py --history
```

Mutation ideas: make `catsoc_export.src` the identity; drop a column from `COLUMNS`; let `summary_ok` accept `@`; replace
`_clamp` by the row's own time; let `_send_refused` accept `True`; remove the `verify_signature` branch of `load_state`; make
`state_key` accept a key file under the repository root.

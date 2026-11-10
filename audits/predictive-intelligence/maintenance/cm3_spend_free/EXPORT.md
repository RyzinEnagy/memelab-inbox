# Catalyst and social tables in the state export (ED-3, PI-D-130)

## The switch (OFF by default)

- Environment: `MEMELAB_STATE_EXPORT_CATSOC=1` in the process that runs `python -m memelab.state export`, or
- `data/config.json`: `{"state_export": {"catalyst_social": true}}` (JSON true only).

With the switch off the export file is byte for byte what the exporter at `60eb729` writes (test
`test_flag_off_export_is_byte_identical_to_the_60eb729_exporter`). Turning it on in the scheduled export is Elving's decision;
no scheduled task was changed.

## What the section holds

Top-level key `_catsoc` (format `catsoc-export-1`): `version`, `window_days` (30), `window_start`, `tables`, `withheld_summaries`,
`tables_missing`. The exact column list of every table is `memelab.catsoc_export.COLUMNS`. In short:

- catalyst: event refs (salted sha256 of the event key), category, evidence status, status, times, source ids (the lab's own
  registry keys such as `news:...` or `exch:...`; the trader research rows, keyed `trader:x:<handle>`, are exported as `trader:`
  plus the salted sha256 prefix in every table); revisions with values for the enum fields only; item refs with the sha256 of the URL and of the normalized body and the linked mints found
  verbatim in each; exact chain plus mint links with type and strength; source ids, groups and tiers; assessment verdicts.
- social: only items with an exact chain plus contract resolution. Account ids, item keys, trader ids and registry ids are
  salted sha256 prefixes. Times, enum states, content hashes, exact contracts, and the lab's own summaries when at most 200
  characters, one line, without `@` or `http`.
- Never: titles, bodies, URLs, handles, display names, bios, notes, labels, mention text, reasons, database row ids.
- The salted refs are pseudonymous, not secret: the salt (`catsoc-export-1:`) is public, so anyone who already holds a candidate
  handle, post id or URL can confirm that it appears; nobody can read a value back from the export. A secret salt would need a
  key in every scheduled session and is not part of this change (open item OI-CM3-1).

Before writing, the section is checked against the column lists and `content_guard.check_json`; a failure replaces it with
`{"version", "withheld": "GUARD_VIOLATION", "rules"}` and the rest of the export is written as usual.

## Reading it back

- The scheduled runs' own import (`state.import_`) ignores the section; the lab's catalyst and social tables are never filled from it.
- Separate store: `python -m memelab.catsoc_export import SRC DEST [--commit-time EPOCH]` (DEST outside the repository or under
  `data/private/`). With `--commit-time` the rows carry that commit time; without it they carry the export time and are for
  inspection only.
- Engine: `memelab.predictive.catsoc_adapter.prepare(versions)` over the git versions of the export file, then
  `states_as_of`, `catalyst_as_of`, `social_as_of` for one exact chain and mint at T. Every row is available from the first
  commit that carried it.

## Exactly what the export file gains

Measured by `probes/flag_off_identity.py` (`evidence/flag_off_identity.json`, time fixed, three databases): with the switch off
the file is byte identical to the `60eb729` exporter on all three. With the switch on the file is the flag-off bytes with one
member inserted before the final `}`: `,"_catsoc":{...}` holding `tables` (18 tables, each a list of rows with exactly the
columns of `COLUMNS`), `tables_missing`, `version`, `window_days`, `window_start` and `withheld_summaries`. Nothing else in the
file changes. Sizes: tracked `data/memelab.sqlite` copy +988 bytes (all 18 tables absent from that older database, so empty);
database rebuilt from the real export +591 bytes (tables present, no rows); fixture database +4,855 bytes (15 rows, one claim
summary withheld).

## State today

The 78 committed versions of `data/state/latest.json` carry no section, so all 4,878 (mint, commit) pairs read
CATALYST_TABLES_NOT_EXPORTED / SOCIAL_TABLES_NOT_EXPORTED. The real databases available here hold no catalyst or social rows
(the tracked `data/memelab.sqlite` predates those tables; a database rebuilt from the real export has them empty), so the
section exported from them is empty; the fixture database exercises every table. Catalyst evidence for real decisions starts
only after the switch is on in the scheduled export and a later phase registers catalyst targets on exported rows.

# Catalyst and social tables in the state export (ED-3, PI-D-130)

## The switch (OFF by default)

- Environment: `MEMELAB_STATE_EXPORT_CATSOC=1` in the process that runs `python -m memelab.state export`, or
- `data/config.json`: `{"state_export": {"catalyst_social": true}}` (JSON true only).

With the switch off the export file is byte for byte what the exporter at `60eb729` writes (test
`test_flag_off_export_is_byte_identical_to_the_60eb729_exporter`). Turning it on in the scheduled export is Elving's decision;
no scheduled task was changed.

## What the section holds (format catsoc-export-2, an allowlist since PI-D-137)

Top-level key `_catsoc`: `version`, `window_days` (30), `window_start`, `tables`, `withheld_values`, `tables_missing`, and
nothing else. Every column of every table has a value type in `memelab.catsoc_export.TYPES`, and a value leaves the database
only when it matches that type; otherwise it is written as null and counted in `withheld_values`:

| Type | What passes |
|---|---|
| `ref` | 32 lower-case hex characters (salted sha256 prefix of an id) |
| `sha256` | 64 lower-case hex characters |
| `time`, `int` | a finite number, an integer |
| `chain` | `[a-z0-9_-]{1,20}` |
| `address`, `addresses` | a Solana base58 address of 32 to 44 characters or `0x` plus 40 hex, or a list of them |
| `enum:<name>` | one value of a fixed vocabulary in `VOCAB` (the catalyst schema's documented values and the social schema's CHECK constraints) |
| `source` | a lower-case prefix (`news`, `exch`, `trader`, ...; `src` when there is none), a colon and a ref |

- There is no free-text column. Summaries (format 1 exported short ones) are not exported at all; they stay in the lab
  database. No title, body, URL, handle, display name, bio, note, label, mention text, reason or database row id leaves.
- Ids become refs: event keys, item keys, account ids, trader ids, registry ids, narrative ids, every catalyst source id, the
  analysis version, and the social tables' own keys (`observation_ref`, `resolution_ref`, `claim_ref`, `extraction_ref`,
  `token_ref`). The same value always gives the same ref, so joins and the classifier's source groups still work.
- The salt stays `catsoc-export-1:` (format 1 was never published: no real export version carries a section). The refs are
  pseudonymous, not secret: anyone who already holds a candidate handle, post id or URL can confirm that it appears; nobody can
  read a value back. A secret salt is open item OI-CM3-1, not part of CM-3.
- A label value outside its vocabulary (a new lab value or anything else) is null in the export until the vocabulary is
  extended by a change control; that is the price of an allowlist.

Before writing, the section is checked (`problems`): the key set, the table set, each row's column order and every value's
type, then `content_guard.check_json`. A failure replaces the section with `{"version", "withheld": "GUARD_VIOLATION",
"rules"}` (rule names only) and the rest of the export is written as usual. The same check runs in the importer (refusal) and
in the adapter (the version is ignored as withheld), so a hand-edited section with a summary, a URL or a handle is never read.

Proof against the skeptic's M1 (`skeptic/CM3_SKEPTIC.md`): `test_m1_personal_data_and_contact_routes_never_reach_the_export`
plants the four summaries of `cm3_probe.py` and fullwidth and spelled-out variants into every free-text column the seed can
reach (and into the source ids and keys); the exported bytes, NFKC-normalized, lower-cased and reduced to letters and digits,
contain none of `someonereal`, `johndoe`, `gmail`, `7185550100`, `xcom`, `tme`. The probe rerun (`skeptic/rerun_probe_adapted.txt`)
shows the observation rows carry no `summary` column.

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
file changes. Sizes at the repair commit: tracked `data/memelab.sqlite` copy +985 bytes (all 18 tables absent from that older database, so
empty); database rebuilt from the real export +588 bytes (tables present, no rows); fixture database +5,036 bytes (18 rows, no
value withheld).

## State today, and what the real-data check proves

The 78 committed versions of `data/state/latest.json` carry no section, so all 4,878 (mint, commit) pairs read
CATALYST_TABLES_NOT_EXPORTED / SOCIAL_TABLES_NOT_EXPORTED. The real databases available here hold no catalyst or social rows
(the tracked `data/memelab.sqlite` predates those tables; a database rebuilt from the real export has them empty), so the
section exported from them is empty.

Said plainly (skeptic m3): the real-data check proves only that the section is absent from every real export version and that
these databases have no rows to export. It proves nothing about how real summaries, ids or labels would look in the export.
That is covered by the fixture database and the tests, which plant the hostile values; real rows will first appear after the
switch is on in the scheduled export, and a later phase registers catalyst targets on them.

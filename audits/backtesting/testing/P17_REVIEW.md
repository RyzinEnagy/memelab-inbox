# Phase 17 independent review

Independent reviewer of Phase 16, reviewing the Phase 17 release documents and clean-install evidence at commit `fcb676a` (branch `feature/backtesting`), 2026-10-24 00:40 to 01:30 UTC.

Scope:
- `docs/backtesting/RELEASE_REPORT.md`, `RUNBOOK.md` and `LICENSE_ATTRIBUTIONS.md`;
- `audits/backtesting/release/p17_clean_install.sh` and `p17_fixture_import.py`, with the committed log;
- the code changes after Phase 16 pass 4 (`report.py` wording, the `stress.py` cache key, new tests).

## Sign-off

**CONDITIONAL RELEASE agreed, scenario-only research mode, with the fix list below.** No critical correctness or security defect is open, and the clean install reproduces, so the gate does not call for HOLD.

The documents are this phase's deliverable, though, and they contain two Medium procedure defects and three false statements. My conditions add to the builder's two (Elving accepts G16 and G27; the module stays research only):

1. **Before Phase 17 is recorded PASS:** correct the runbook's crisis, backup and recovery steps for SQLite WAL files (M1).
2. **Same:** correct the release report:
   - say which commit the run id belongs to (L1);
   - point to this file instead of `audits/backtesting/PHASE_17.md` (L2);
   - drop "no Medium defect open" until M1 and M2 are closed (L3).
3. **Before any scheduled or repeated `outcomes track`, and before any shadow-calibration claim:** fix M2. Either cap the tracker's as-of at the data actually fetched, or ship a working, documented refresh step.
4. **No push, bundle or zip of the branch without Elving's explicit authorization** (L15). Nothing has been pushed.

Everything else is Low and can follow in a later pass. If the builder declines conditions 1 to 3, my sign-off is HOLD with the same fix list.

## Commands and exits

| Command | Exit | Result | Log |
|---|---|---|---|
| `bash audits/backtesting/release/p17_clean_install.sh <repo> <scratch>` at fcb676a | 0 | all 8 steps run. Matches the committed log except the commit-bound run id, run result hash and report hash (details below) | scratch copy, summarized below |
| the same script against a scratch repo whose branch points at ddc0794 (the commit of the committed log) | 0 | identical to the committed log, including run id `2783803032f6` and report sha `63d00328`, except the run "result" hash (contains `created_at`) | scratch copy |
| `pytest tests -q -p no:cacheprovider` at fcb676a | 1 | 1024 passed, 1 failed (C-1, pre-existing) | `logs/p17_full_pytest.log` |
| `mutate.py` p05 to p16, repair, repair2 | 0 each | 214 of 214 caught (167 + 13 + 10 + 24) | `logs/p17_mutations_all.log` |
| `mutate.py p16r4_mutations.json` | 1 | R4-1 to R4-8 caught; R4-9 NOT APPLICABLE (the key line changed; see P17-1 and P17-2) | same |
| `p16_mutate_strict.py` p16, repair, repair2 | 0 | all caught except one survival of R16-6 (timing-sensitive, as in Phase 16 pass 3; the official run above caught it) | `logs/p17_mut_strict.log` |
| `mutate.py p17_mutations.json` (mine) | 1 | P17-1 SURVIVED: removing the new cache-key component leaves the builder's C4 test green. P17-2 CAUGHT by my same-inode test. | `logs/p17_mutations.log` |
| `p17_doc_claims_check.py <copy>` on the committed documents | 1 | 55 of 57 checks pass; the 2 failures are L1 and L2 | `logs/p17_doc_claims_check.log` |
| the same check, and the existing release checks, on scratch copies of the docs with 4 seeded errors | see below | existing checks catch 0 of 4; mine catches 4 of 4 | `logs/p17_seeded_errors.log` |
| the runbook's rollback command, verbatim, with `MEMELAB_BT_DB` on a scratch copy | 0 | bt tables dropped, migration ledger kept; the next `backtest status` re-migrates an empty database | this file |
| move-aside reproduction (scratch) | 0 | see M1 | this file |
| stale-tracker reproduction on a corpus copy | 0 | see M2 | this file |
| Firecrawl: Crawl4AI's upstream LICENSE | 1 call | 3 of 8 calls used in total by this reviewer | L5 |

## Clean-install comparison

Rerun at the release commit fcb676a. It matches the committed log line for line except:
- clone HEAD (fcb676a against ddc0794);
- the run id (`848f89623000...` against `2783803032f6...`);
- the run result hash;
- the report sha (`9867294b...` against `63d00328...`).

It reproduces:
- dataset hash `1641985565d5...`;
- ledger `f9d7dd89c462...`;
- MISS then HIT on the second run;
- one trade;
- the scenario table (BASE -6.0%, LIQ_75 -10.8%, INSIDER_DUMP -63.7%, HONEYPOT -100%, COMBINED_WORST -92.7%);
- the policy off/on diff of exactly one line, with the lab database byte-identical;
- 239 backtest tests passed;
- release audit "Needs action: no".

Rerun at ddc0794: identical to the committed log, including the run id and report sha. Only the run "result" hash differs, because `result.json` stores `created_at`.

Why the run id moves: `store.register_run` hashes `code_sha`, which is `git rev-parse HEAD` (plus "+dirty" for uncommitted `memelab/` changes). Between ddc0794 and fcb676a only documents and the log changed, yet every run id changes. This is conservative by design, but the documents present the run id as a fixed final hash (L1).

## Findings, ranked

### Medium

**M1. The runbook's crisis, backup and recovery steps ignore SQLite's WAL files, so the "record of what was known when" can be lost.** `RUNBOOK.md` lines 24, 25 and 124:
- "move it aside (for example `data/backtest/bt.sqlite` to `bt.sqlite.hold`)";
- "back the file up first";
- "restore the backed-up file".

The database runs in WAL mode, so committed data can sit only in `bt.sqlite-wal` until a checkpoint. Reproduction in scratch:
1. A writer that is still open (the runbook's own "stuck process" case) commits 50 universe rows with autocheckpoint off.
2. `bt.sqlite` is renamed to `bt.sqlite.hold`.
3. Read on its own, `bt.sqlite.hold` has no tables at all ("no such table: bt_universe_members"): the schema and all 50 rows were only in `bt.sqlite-wal`, which the move left beside the new empty file.

`schema.backup_db` (SQLite backup API, safe with WAL) already exists, but the runbook never names it.

Fix: stop every process using the database. Then either use `schema.backup_db(src, dest)`, or move `bt.sqlite`, `bt.sqlite-wal` and `bt.sqlite-shm` together. Say this in the crisis shutdown, schema rollback and migration recovery sections.

**M2. Shadow-mode calibration cannot be continued as written, and following the runbook records misleading outcomes.** Four parts:
- `python -m memelab backtest outcomes track` never fetches bars: the tracker's `fetch` hook is not wired to the CLI.
- Its as-of defaults to the wall clock (`outcomes.track`: `asof = observed_asof if observed_asof is not None else now`).
- No supported command refreshes bars. `corpus.build(..., refresh=True)` is reachable only from Python, and `corpus.already_fetched` skips every mint already marked `CORPUS_MINT_DONE`.
- The runbook's named runners `audits/backtesting/data/run_corpus2.py` and `run_corpus3.py` are one-off container scripts. They hard-code `sys.path.insert(0, '/home/claude/work/memelab-inbox')` and read `/home/claude/work/scratch/latest_main.json` and `mints_windows.json`, which are neither in the repository nor on Elving's computer.

Reproduction on a corpus copy (`outcomes.outcome_for` at 72 h for all 1,023 opportunities):

| As-of | COMPLETE | CENSORED: bars end early | CENSORED: no bars in window | NOT_OBSERVABLE: no bars stored | PENDING |
|---|---|---|---|---|---|
| corpus end (honest) | 348 | 85 | 43 | 431 | 113 |
| corpus end + 3 days, nothing fetched (the CLI default after 3 days) | 348 | 133 | 46 | 493 | 0 |

All 113 pending windows become recorded results. 48 of them become "cut short", which the cohort counts at the last traded price, for tokens not known to have stopped trading.

Mitigations:
- Rows are superseded once real bars arrive, and the drift coverage check would warn.
- No scheduled task exists, so no such rows exist today.

Fix:
- default the tracker's as-of to the newest available bar, or better, per mint to the last fetch;
- add a bounded refresh command using `corpus.build(refresh=True)` with the 3 s budget;
- document both in "Shadow-mode calibration" and "Backfills", and stop naming the container-only runners as the operator route.

### Low

| # | Where | Finding | Fix |
|---|---|---|---|
| L1 | RELEASE_REPORT "Final hashes", step 4; RUNBOOK line 59 | The clean-install run id `2783803032f6` and report sha `63d00328` belong to ddc0794, not the release commit (at fcb676a: `848f89623000`, `9867294b`). "The same code and data give the same run id" is true only within one commit. The ledger and dataset hashes reproduce at any commit with the same code. | state the commit next to each run id, or regenerate the log at the release commit; say "the same commit" in the runbook |
| L2 | RELEASE_REPORT sign-off | "The reviewer's release sign-off is recorded in audits/backtesting/PHASE_17.md": that file does not exist | point to `audits/backtesting/testing/P17_REVIEW.md` |
| L3 | RELEASE_REPORT "Why not HOLD" | "no correctness or security defect of Medium severity or higher is open" is not true while M1 and M2 are open | list M1 and M2 until fixed |
| L4 | LICENSE_ATTRIBUTIONS "Runtime dependencies" | "`memelab/backtest/` imports only the Python standard library" overstates. `backtest/cli.py` imports `memelab.cli`, `memelab.db` and `memelab.pipeline`, and `backtest stress` loads numpy through the lab pipeline (checked: importing `memelab.pipeline` loads numpy). The listed standard-library modules are exactly right, and no third-party package is imported by the package itself. | "adds no third-party dependency; `backtest stress` uses the lab pipeline, which needs numpy" |
| L5 | LICENSE_ATTRIBUTIONS, Crawl4AI row | Listed as Apache-2.0. The upstream LICENSE (main branch, fetched through Firecrawl) is Apache-2.0 plus an "Attribution Requirement" for distributions, publications and public uses. Crawl4AI is not shipped, but this document is the place for its attribution sentence. | add the clause and the attribution text; note the clause may postdate 0.9.5 |
| L6 | RUNBOOK crisis shutdown | Turning the policy off does not stop `outcomes track`, which never reads the policy, nor `backtest stress`, which runs on explicit request by design | say so, and add "pause any scheduled tracker" |
| L7 | RUNBOOK | "Quality statuses" are only partly covered. The refusal reasons in `quality.REFUSAL_POLICY` (warmup, staleness, lab price versus bars) and the assessment machine states are not listed or linked (they are in EXECUTION.md) | add a table or a link |
| L8 | RUNBOOK storage table | Stored runs always go to `<repo>/data/backtest/runs/` (`runner.RUNS_DIR`), whatever `--db` or `MEMELAB_BT_DB` say. During this review a `backtest run --db <scratch copy>` wrote a run folder into the working copy, which I removed. | document it, or add a `MEMELAB_BT_RUNS` override |
| L9 | `tests/test_backtest_outcomes.py::test_cohort_cache_follows_a_replaced_database_file` | The C4 fix is guarded only by the reviewer's audit test. The builder's test builds the second database at another path and uses `os.replace`, so the file arrives with a new inode and the test passes even with the new key component removed (P17-1 SURVIVED). My same-inode test catches that mutant (P17-2). | delete and recreate at the same path in the builder's test |
| L10 | `p17_clean_install.sh` | The script exits 0 even when a step fails: everything is piped into `tee` with only `set -u`. The exits of steps 4, 7 and 8 are not printed, and `echo "exit $?"` after `| head -5` prints `head`'s exit. A reviewer must read the log. | `set -o pipefail`, record each step's exit, exit nonzero on any failure |
| L11 | RUNBOOK `inspect` | Lists a "result" hash among the reproducibility hashes, but that hash never reproduces (`created_at` is inside the result) | say which hashes reproduce: dataset and ledger, and the run id within one commit |
| L12 | RELEASE_REPORT risk disclaimer | "20% ... fell by half or more within 24 h, and 28% within 72 h" is measured over observed windows; 45% of opportunities were not observable (Phase 15) | add the caveat |
| L13 | HANDOFF / RUNBOOK / LICENSE_ATTRIBUTIONS | The Firecrawl count is "about 29" in HANDOFF and "about 31" in the other two. This review used 1 more call. | one number |
| L14 | version matrix | Pins (pytest 9.1.1, numpy 2.5.3) live only inside the install script; there is no requirements file or lock | add a pinned requirements file, or name the script as the pin record |
| L15 | HANDOFF (Phase 16 record) | "Next eligible phase: 17 ... push feature/backtesting (fast-forward, no merge), git bundle and zip to D:\memelab". The Phase 17 prompt forbids a push without separate user authorization. Checked: no `origin/feature/backtesting` exists. | treat push, bundle and zip as needing Elving's explicit approval |

Observation, not a defect: the strict mutation harness again saw one R16-6 survival while the official harness caught it. The concurrent-first-migration test is timing-sensitive.

## Claims verified (no finding)

RELEASE_REPORT:
- Base commit f99c6c7 on `feature/catalyst-firecrawl`.
- Best adoption score 65.10 against the 70 bar: `RANKING.csv`, 25 repositories.
- Sealed tests all INSUFFICIENT_SAMPLE with 0 to 9 trades (`p11_results.json`: 0, 6, 7, 6, 4, 3, 3, 9).
- Walk-forward BREAKOUT_CLOSE: 32 out-of-sample trades, mean -7.08%, bootstrap 95% interval -13.5% to -1.8%.
- The seven strategies with 30 or more trades: net -11.3% to -20.5%, paper -2.4% to -10.3% (`p10_runs.json`). CATALYST_VERIFIED (+34.9%) has 2 trades, so leaving it out is conservative.
- REJECTED cohort p10 -77.6%, median -3.3%, p90 +29.5%, 28% unmeasured: these are the no-as-of figures (138 measured of 192, unmeasured 28.1%). At the last full hour the percentiles are the same with 26.9% unmeasured.
- Token age: 7 days or older median -4.8%; under 24 h median -55% to -68% (`PHASE_15.md`).
- 15 of 19 launch catalysts lost half within 72 h (`CATALYST_COVERAGE.md`).
- PumpSwap default 1.25% tier (`execution.DEX_FEE_DEFAULTS`); CLMM and DLMM pools are UNSUPPORTED_POOL without an observed quote.
- Corpus: 139,168 bars over 258 mints (257 universe tokens plus the SOL reference series); 429 of 686 universe mints without bars; about 16.5 days; 155.7 MB.
- Linux, Python 3.13.17, SQLite 3.45.1.
- Full suite 1024 plus C-1.
- Every Phase 16 mutation set caught (214).
- release_e2e PASS 78 of 78 (Phase 16 pass 4, same code paths).
- Final hashes:
  - database file `5f4ce7239eb4f0b0`;
  - cutoff dataset `35f836f372c4`;
  - whole-corpus dataset `d838d9037aeb`;
  - pre-registration `d0b3686f2d61`;
  - sealed ledgers `88ae40542f4b` and `e478181404b2`;
  - all eight Phase 10 run ids and ledgers;
  - the Phase 15 daily report `9e8b48b3299a`, which still reproduces at HEAD after the Phase 16 changes, recomputed on a copy.
- No historical performance claim is inflated: every quoted result is negative or INSUFFICIENT_SAMPLE.

RUNBOOK:
- Every `backtest` and `outcomes` command, subcommand and flag exists (17 commands checked against argparse).
- Policy defaults match `assess.DEFAULT_POLICY` (8 keys).
- `MEMELAB_BT_DB`, `MEMELAB_BT_RAW`, `MEMELAB_BACKTEST` and `data/backtest/policy.json` behave as stated. The environment variable overrides the file in both directions, so "unset or 0, and set enabled false" is right.
- The hook returns before opening any database when off.
- The rollback command works verbatim.
- STALE_DATA after 2 h, INVALID_TOKEN_ID and SOURCE_BLOCKED rules match `assess.precheck`.
- Busy timeout 10 s.
- GeckoTerminal pacing 3 s default with backoff on 429 and 5xx; `CORPUS_MINT_DONE` marker; 429 at 2.2 s recorded in DATA_FEASIBILITY.md.
- Social alert days in America/New_York.
- `outcomes shadow` does not save a run (`save=False`).
- No schedule exists.

LICENSE_ATTRIBUTIONS:
- The standard-library module list is exact (AST scan, including imports inside functions).
- The lab's only third-party runtime import is numpy.
- Versions verified in the container and the clean venv.
- All six "ideas" rows match `RANKING.csv` (pinned SHA prefix and license file).
- Audit-only tools backtesting 0.6.6 (AGPL-3.0), vectorbt 1.2.0 (Apache-2.0 + Commons Clause) and purgedcv 0.1.11 (MIT) match `research/BOM.md`.
- The multi-process tests skip on Windows.
- Maxun: NOT_ADOPTED (D-BT-020). AGPL source integration is barred without Elving's legal decision (D-BT-015), and nothing AGPL is embedded or called.
- The Orca license note matches `RANKING.csv`.

Phase 17 prompt checklist:

| Required item | Where | Status |
|---|---|---|
| clean-environment reproduction (install, migration, historical import, deterministic backtest, report with adversarial scenarios, disabled-feature rollback) | install script and log | reproduced (run id commit-bound: L1; script exit: L10) |
| support matrix honest | LICENSE_ATTRIBUTIONS, RELEASE_REPORT item 9 | yes, Linux only |
| pinned versions, research repo SHAs, SBOM, license notices | LICENSE_ATTRIBUTIONS | yes (L4, L5, L14) |
| data provenance | RELEASE_REPORT 3 and 4, RUNBOOK backfills, LICENSE collectors | yes |
| API cost and rate limits | RUNBOOK costs | yes (L13) |
| timezone | RUNBOOK | yes |
| storage | RUNBOOK | yes (L8) |
| migration recovery | RUNBOOK | present but unsafe with WAL (M1) |
| model limitations | RELEASE_REPORT disclosed limitations | yes |
| quality statuses | RUNBOOK | partial (L7) |
| source outage procedures | RUNBOOK diagnostics | yes |
| manual replays, backfills, diagnostics, scenario config | RUNBOOK | replays, diagnostics and config yes; backfills not operable (M2) |
| strategy confidence versus token opportunity | RUNBOOK "Reading the output" | yes |
| crisis shutdown of the stress module only | RUNBOOK | yes, with gaps (M1, L6) |
| shadow-mode continuation | RELEASE_REPORT, RUNBOOK | present but not operable as written (M2) |
| Maxun closure and AGPL decision | LICENSE_ATTRIBUTIONS, RUNBOOK, D-BT-015, D-BT-020 | yes |
| executive sign-off, defect list, no inflated claims, risk disclaimers | RELEASE_REPORT | yes (L1 to L3, L12) |
| no push, no deploy | HANDOFF | nothing pushed (L15) |

## Wrong-but-plausible outputs and whether a check catches them

Found in the documents as committed:
- **L1:** a "final" run id that does not reproduce at the release commit. Caught by my rerun and by `p17_doc_claims_check.py` ("clean-install log was made at the release commit": FAIL). No existing check reads the documents.
- **M1:** a recovery step that loses the WAL. Caught only by my reproduction; no test covers it.
- **M2:** a shadow-mode routine that records "cut short" outcomes for unfetched windows. Caught by my reproduction; the drift coverage check would warn only after such rows exist.

Seeded on purpose, in a scratch clone (documents only):
- W1: `--horizon-h` became `--horizon`;
- W2: one hex digit of the BREAKOUT_CLOSE sealed ledger changed;
- W3: the bar count became 139,186;
- W4: the exit-impact default became 0.5.

Results:
- **Existing checks:** the release audit gives "Needs action: no" and the backtest tests give 239 passed. They catch 0 of 4.
- **`p17_doc_claims_check.py`:** catches 4 of 4 (unknown flag `--horizon`, default 0.5 against the code's 0.05, ledger mismatch, count mismatch).

The release process has no check that its documents agree with the code and evidence. Adding `p17_doc_claims_check.py`, or an equivalent, to `tools/release_e2e.py` would close that gap.

## Files written by this review (uncommitted)

- `audits/backtesting/testing/P17_REVIEW.md` (this file)
- `audits/backtesting/testing/p17_doc_claims_check.py`, `p17_mutations.json`
- `audits/backtesting/testing/logs/p17_full_pytest.log`, `p17_mutations_all.log`, `p17_mut_strict.log`, `p17_mutations.log`, `p17_doc_claims_check.log`, `p17_seeded_errors.log`

Hard rules kept:
- no commits;
- no production or document edits;
- no token files;
- no GIT_DIR;
- every database written was a scratch copy;
- protected hashes unchanged (`bt.sqlite` `5f4ce7239eb4f0b0`, `memelab.sqlite` `068287c0d7e45436`);
- removed my own artifacts: one run folder under `data/backtest/runs/` and one BRETT report.

## Re-check of the fixes at efd890d

Re-checked by the same reviewer at commit `efd890d`, 2026-10-24 01:50 to 02:35 UTC. Everything ran offline: no network calls and no Firecrawl.

**Verdict: AGREED. CONDITIONAL RELEASE, scenario-only research mode.**
- Conditions 1 to 3 of my sign-off are met, and condition 4 is answered.
- Every Medium and Low item from my list is fixed, except where noted below.
- Seven new Low residuals (R1 to R7) are listed at the end. They are follow-ups, not blockers: none changes an existing result, and none is a security exposure.

### Commands and exits

| Command | Exit | Result | Log |
|---|---|---|---|
| clean install at efd890d (offline copy of the script: venv with `--system-site-packages` instead of `pip install`, because this re-check allows no network; pytest 9.1.1 and numpy 2.5.3 are installed system-wide) | 0 | RESULT PASS, all 11 recorded step exits 0, 244 backtest tests, "Needs action: no", checker 72 of 72. Identical to the committed log (made at bc7ce30) except the commit-bound run id, result hash and report hash; dataset hash, ledger `f9d7dd89c462` and MISS then HIT reproduce | `logs/p17r_clean_install_offline.log` |
| `pytest tests -q -p no:cacheprovider` | 1 | 1029 passed, 1 failed (C-1, pre-existing); the BRETT report it wrote was deleted | `logs/p17r_full_pytest.log` |
| `mutate.py` p05 to p16, repair, repair2, p17_builder | 0 each | 221 of 221 caught | `logs/p17r_mutations_all.log` |
| `mutate.py p16r4_mutations.json` | 1 | R4-1 to R4-8 caught; R4-9 not applicable (its line was replaced by the C4 fix) | same |
| `mutate.py p17_mutations.json` | 1 | P17-1 CAUGHT now: the builder's C4 test was fixed (L9). P17-2 "survived" only because my same-inode test skipped in the harness copy, where the filesystem gave a new inode. That is a weakness of my test, not a gap; P17-1 and the builder's P17-7 cover it. | same |
| `p17_doc_claims_check.py <copy>` at efd890d | 0 | 72 of 72 | `logs/p17r_doc_claims_check.log` |
| the same checker on scratch copies of HEAD's documents with my four seeded errors | 1 | catches 4 of 4 | `logs/p17r_seeded_errors.log` |
| `p16r4_cohort_check.py <copy>` | 0 | ALL_MATCH True at the 6 real decision points, with the same counts as Phase 16 pass 4 (0, 30, 9, 23, 136, 27): the new freshness rule changes no real cohort figure | `logs/p17r_cohort_check.log` |
| `tools/release_e2e.py` at efd890d | 0 | PASS 78 of 78, network 0, tracked database byte-identical | `logs/p17r_release_e2e.log` |

### Status of my findings

| Item | Status | Evidence |
|---|---|---|
| M1 backup and recovery with WAL | FIXED | My reproduction was repeated: a writer still open, 50 committed rows only in `bt.sqlite-wal`. `python -m memelab backtest backup --to X --db DB`, run from another process, exits 0 and its copy holds all 50 rows. The copy is self-contained: its main file alone, copied elsewhere, holds the 50 rows and its `-wal` is empty. After a clean stop, moving the three files together keeps them. The runbook now says stop writers, back up, then move all three files. |
| M2 stale tracker and no refresh | FIXED (correctness); operability partly, see R1 | On a corpus copy, a pass 3 days after the last fetch no longer creates any "cut short" or no-bars result (72 h: CENSORED 85 and 43, the same as at the corpus end). The 51 windows on fetched pools stay PENDING with NOT_FETCHED_SINCE_WINDOW_END. With a fake HTTP layer, `outcomes.refresh` makes 1 call for the waiting pool, records OHLCV_FETCHED, and the window resolves. Corpus-end counts at 24 h and 72 h are unchanged from pass 4. |
| L1 run id bound to a commit | FIXED | The hash table names commit bc7ce30 next to run id afa0d2f66467 (reproduces exactly in the committed log); the runbook says "the same commit" and that ledgers reproduce across commits |
| L2 sign-off pointer | FIXED | `audits/backtesting/PHASE_17.md` exists, and the report points to this file |
| L3 "no Medium open" | FIXED | The report now names the two Medium findings and says they are fixed. That is accurate as of this re-check. |
| L4 standard-library claim | FIXED | "the package's own modules import only the standard library ... and other lab modules; `backtest stress` loads numpy through the lab" |
| L5 Crawl4AI license | FIXED | "Apache-2.0 with an added attribution requirement"; not shipped |
| L6 crisis shutdown scope | FIXED | Commands run by name, and scheduled tasks, are named |
| L7 quality statuses | FIXED | A table in the runbook; every name in it exists in the code |
| L8 run files location | FIXED for `--db`; see R3 | `backtest run --db COPY` writes `runs/` beside the copy (builder mutation P17-6 caught) |
| L9 C4 test | FIXED | P17-1 caught |
| L10 install script exit | FIXED; see R4 | Each step's exit is recorded, and the script ends with RESULT and a nonzero exit on any failure. A minimal bash reproduction of the same structure with one failing step gives RESULT FAIL and exit 1. |
| L11 result hash | FIXED | The runbook says it never reproduces; compare ledgers |
| L12 risk disclaimer | FIXED | Observed windows only, about 45% not observable, so the shares may be off in either direction |
| L13 Firecrawl count | FIXED (one number, 31) | By my count it is probably 32 now (29, plus 2 calls in Phase 16, plus 1 in this review); cosmetic |
| L14 pins | FIXED | `docs/backtesting/requirements-test.txt`; the install script uses it |
| L15 push, bundle, zip | ANSWERED | The coordinator reports that Elving authorized them at the start of this work (the "Both" delivery answer: a new feature/backtesting branch through the Composio Git Data API, fast-forward, no force, no merge, no PR merge, main untouched; bundle plus zip to D:\memelab). It is recorded in PHASE_17.md. I record it as answered on the coordinator's statement; I did not see that exchange myself. Nothing had been pushed at efd890d. |

**The coordinator's change to my checker (bc7ce30): confirmed.** The old item was circular: committing the log always moves HEAD. The new rule passes when the log was made at HEAD, or when every later change is a `.md` file or the log itself; between bc7ce30 and efd890d only `PHASE_17.md`, the log and `RELEASE_REPORT.md` changed.

A non-blocking note: not every `.md` file is prose. `tests/test_backtest_webcapture.py` reads `audits/backtesting/research/MAXUN_ADOPTION.md`, and the full suite would catch a change there, so the risk is small. The rule also looks at commits, not at an uncommitted working tree.

### New residuals (Low, follow-ups)

| # | Finding | Evidence | Suggested fix |
|---|---|---|---|
| R1 | `backtest refresh` never adds new tokens. It fetches only basis pools of windows already waiting. New opportunities (stored assessments, new lab records) have no stored bars or pools, so they stay NOT_OBSERVABLE: NO_BARS_STORED. Universe import (`labstate.build_universe`) and pool discovery (`corpus.build`) have no CLI. So "continuing in shadow mode" measures only the corpus's own pending windows, and a new sealed split after 2026-10-23 16:00 UTC needs undocumented Python steps. | With a fake HTTP layer: `refresh(mints=[new token])` gives pools_wanted 0 and 0 requests. On the real copy, 62 windows of never-fetched mints (72 h) move from PENDING to NOT_OBSERVABLE after 3 days. That is honest labeling, but nothing will ever fetch them. | a CLI for universe import and for pool discovery of new mints, or a runbook note that the forward path covers only the frozen corpus |
| R2 | The fetch evidence records only the newest bar. A full 1000-row page reaches back about 41.7 days, so a refresh run more than about six weeks after a window, on a pool that traded every hour, would resolve that window as "no trades". | `gecko.fetch_ohlcv` `limit=1000`; the OHLCV_FETCHED payload has `last` but no first bar | record the first bar time, and treat the fetch as covering only from it when the page is full |
| R3 | Run files follow `--db` but not `MEMELAB_BT_DB`. With only the environment variable set, runs still go to `<repo>/data/backtest/runs/`, while the runbook says "next to the database used". | `cli._runs_dir` reads `a.db` only | use `store.BT_DB_PATH` when `--db` is absent, or adjust the sentence |
| R4 | The install script prints step 4's two runs but does not assert the same run id and a HIT; a failed run surfaces only indirectly, through step 4's `inspect` | script lines 43 to 45 | compare the two printed ids and the cache field |
| R5 | The checker's prose exemption covers every `.md` file (see the note above) | as above | exempt only `.md` files that no test or code reads |
| R6 | My same-inode test (`test_r4_cohort_cache_file_replaced_at_the_same_path`) skips when the filesystem gives a new inode, so it is not a reliable mutation killer | P17-2 skipped in the harness copy | keep the builder's test as the guard |
| R7 | The release report and PHASE_17.md stated "re-checked" and "agreed" before this re-check ran | wording in both files | now true; no change needed |

Hard rules kept:
- no commits;
- no production or document edits (only this appended section and new logs under `testing/logs/p17r_*`);
- no token files;
- no GIT_DIR;
- no network (the clean install ran from a copy of the script without the pip step);
- every database written was a scratch copy;
- protected hashes unchanged (`bt.sqlite` `5f4ce7239eb4f0b0`, `memelab.sqlite` `068287c0d7e45436`);
- the BRETT report from the full-suite run was deleted.

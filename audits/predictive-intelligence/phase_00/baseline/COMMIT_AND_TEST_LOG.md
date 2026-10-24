# Commit and test log (Phase 00 baseline)

## Checkout state before any change

| Item | Value | Command |
|---|---|---|
| Path | /home/claude/memelab-inbox | |
| Remote | `origin https://github.com/RyzinEnagy/memelab-inbox.git` (fetch and push) | `git remote -v` |
| Branch | `feature/predictive-intelligence`, tracking `origin/feature/catalyst-firecrawl` | `git status` |
| HEAD | `f99c6c7` "catalyst firecrawl: scheduled-run wiring, key token file, search on with spacing, basic proxy decided" (2026-10-22T13:53:28-04:00) | `git log -1` |
| Dirty state | clean ("nothing to commit, working tree clean") | `git status` |
| Remote tips after fetch | main `98338a8`, feature/social-intelligence `3f27fc7`, feature/catalyst-firecrawl `f99c6c7`, audit/social-intelligence-phase06 `b4c4216`, remediation/social-intelligence-m00 `3b434e1`, verification/social-intelligence-m00-independent `2605b5f` | `git fetch --all --prune; git branch -r -v` |
| Package integrity | 41 of 41 files OK, exit 0 | `sha256sum -c SHA256SUMS.txt` in the package folder |

Recent relevant commits on HEAD (newest first): `f99c6c7`, `192defe`, `5bfb4f3` (Firecrawl catalyst), `3f27fc7` ... `76eac30` (social-intel 19 to 21), `f084b60` (merge of social-intel 00 to 18, PR #1, 2026-10-12T22:10-04:00).

## Environment

| Item | Value |
|---|---|
| OS | Linux 6.18.44 (cloud container) |
| Interpreter | Python 3.13.17 at /usr/bin/python (`python --version`, `sys.executable`) |
| pip | 24.0 (system) |
| Test tool | pytest 9.1.1, pluggy 1.7.0, iniconfig 2.3.1, installed this session with `pip install pytest` (exit 0) |
| Runtime packages the code imports | numpy 2.5.3 (only third-party import in memelab/; tests add pytest; tools/release_audit.py optionally uses pyflakes, which is not installed) |
| Other present packages | pandas 3.0.5, scipy 1.18.1, scikit-learn 1.9.1, requests 2.34.2, playwright 1.63.0 (not imported by the repo) |
| Dependency lock | none: no requirements*.txt, pyproject.toml, setup.py, Pipfile, poetry.lock or uv.lock (`ls` exit 2 for each). README "Tests" says `pip install pytest numpy`. The full environment at baseline is pinned as a record in `PIP_FREEZE.txt` (158 lines, `pip freeze`) |
| Node | v22.22.0 (used by `python -m memelab fetch`, not by tests) |
| Network | outbound HTTPS through the agent proxy; GeckoTerminal and DEX Screener reachable; unauthenticated GitHub REST answered 403; `gh` GraphQL blocked |
| Credentials | none for Helius, Firecrawl, Crawl4AI or GitHub in this session; not looked for |

## Full suite, unchanged

Command (flags only add the skip-reason summary and skip the cache folder; no test selection or deselection):

```
python -m pytest tests -q -rs -p no:cacheprovider
```

| Item | Value |
|---|---|
| Collected | 786 (`python -m pytest tests -q --collect-only`, exit 0, "786 tests collected in 2.90s") |
| Result line | `1 failed, 785 passed in 133.57s (0:02:13)` |
| Exit code | 1 |
| Skipped | 0 (no skip summary printed; `tests/test_pipeline_live_fixture.py` has a skipif on missing inbox files and ran) |
| Errors | 0 |
| Wall clock | 2026-10-24T00:27:15Z to 00:29:29Z |
| The one failure | `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, `assert ('REPORTED' == 'CONFIRMED')` at tests/test_catalyst.py:44. Known and clock dependent (social-intel C-1, AUDIT_00.md). No other failure. |
| Output sha256 | suite log `72e31f5215e9997a27c273a82f61f7bdac64e9fe18dfc2e61077f0c16475a32d`, collection log `b373a77860097c5f3b6cfdf5598012ed538d934b39c40b542eae12f929f71e0d` (kept in scratch, not committed) |

Matches the last recorded counts on this code line? The social HANDOFF recorded `1 failed, 748 passed` on `7d166ab` (social-intel 21); Firecrawl added 37 tests (FIRECRAWL.md), 748 + 37 = 785. Consistent.

Files left behind by the suite (`git status --porcelain --ignored` right after the run):

- `?? data/reports/20261024_0027_BRETT_0x532f.md`: written by tests/test_evm.py (known, social-intel C-1). Removed by hand.
- `!! data/memelab.sqlite-shm` (32,768 bytes) and `!! data/memelab.sqlite-wal` (0 bytes): some test opened the tracked database in WAL mode. Ignored by `*.sqlite*`; the tracked file's sha256 stayed `068287c0...a6679ca` and `git diff --quiet -- data/memelab.sqlite` exit 0. Removed by hand.
- `__pycache__/` folders (ignored).

After removal: `git status --porcelain` empty.

### What the suite does and does not prove

Tests per file (from the collection): test_social_performance 57, test_social_registry 51, test_social_wallets 43, test_social_telegram 41, test_social_narratives 39, test_social_alpha 39, test_social_discord 38, test_social_feed 37, test_catalyst_firecrawl 37, test_social_x_api 36, test_social_chronology 31, test_social_identity 29, test_social_outcomes 28, test_social_extraction 28, test_social_alerts 28, test_social_research 23, test_social_reddit 23, test_social_replay 22, test_social_youtube 20, test_m21_28 19, test_social_ingest 18, test_m13_18 18, test_social_store 15, test_social_farcaster 14, test_launch 11, test_release_tools 10, test_content_guard 7, test_secrets 5, test_catalyst 5, test_farm 4, test_evm 3, test_catalyst_xprofile 3, test_wallet 2, test_pipeline_live_fixture 1, test_ecosystem 1.

- 660 of 786 tests are social-intelligence tests (test_social_*.py), almost all on invented fixtures.
- The core Solana scout path (bundle, 22 modules, score, status, report) has one integration test on real collector files, with `persist=False` (test_pipeline_live_fixture.py). The persist path, `previous_thesis`, `m25` snapshot and diff, the state export of theses, catalyst `record_outcomes`, launch `launchpad_stats` and `followup_mints`, and `m20` manipulation (only fed a hand-made dict) have no direct test (`grep -l -E` over tests/).
- Shallow files by assertions per test: test_farm 1.2, test_secrets 1.8, test_release_tools 1.9 (counts of `assert` per `def test_`).
- Tests that read real tracked data: test_pipeline_live_fixture.py (data/inbox), test_social_replay.py (tracked DB, honest INSUFFICIENT_DATA), and content-guard and identity tests that scan tracked files.

## CLI smoke (safe, temp DB, separate clone)

Run in `git clone /home/claude/memelab-inbox <scratch>/clone` (HEAD `f99c6c7`) with `MEMELAB_DB=<scratch>/smoke/*.sqlite`:

| Command | Exit | Output |
|---|---:|---|
| `python -m memelab --help` | 0 | usage with 16 subcommands |
| `python -m memelab init` | 0 | `db ready at <scratch>/smoke/smoke.sqlite` |
| `python -m memelab analyze DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump --results deep01a deep02 deep03 deep04 --stage1 disc01 --no-persist` | 0 | `HIGGS score 47 status DISTRIBUTION RISK -> None` |
| `python -m memelab scout --mints DoVAV... --results deep01a deep02 deep03 deep04 --stage1 disc01 --report-dir <scratch>/smoke/reports` | 0 | report files written to scratch only |
| same `analyze` with `--results disc01 s2_01 deep01a deep02 deep03 deep04 forensics01` | 0 | `HIGGS score 48 status REJECTED -> None` |
| `python -m memelab catalyst fc-health` (no key in env) | 1 | `"status": "config_missing"`, `"key": "missing"`, `"key_source": null` |
| clone `git status --porcelain` after all of the above | | empty |

The lineage probe (`probes/lineage_reproduction_probe.py`, exit 0) repeats the analysis at HEAD and at `b6c424d` and compares with the stored report; see FEATURE_TRACE.md.

## Probes run in Phase 00 (all committed under `audits/predictive-intelligence/phase_00/probes/`)

| Probe | Command | Exit | Writes |
|---|---|---:|---|
| state history | `python3 audits/predictive-intelligence/phase_00/probes/state_history_probe.py origin/main <scratch>/state_history_main.json` | 0 | the output file only |
| P01 identity | `python3 audits/predictive-intelligence/phase_00/probes/p01_ticker_identity_probe.py origin/main` | 0 | temp DB in a temp folder |
| P41 hostile page | `python3 audits/predictive-intelligence/phase_00/probes/p41_untrusted_page_probe.py` | 0 | nothing |
| lineage | `python3 audits/predictive-intelligence/phase_00/probes/lineage_reproduction_probe.py` | 0 | temp clone and temp DBs |

`git status --porcelain` after each probe showed only the new `audits/` folder.

## Release end-to-end check

See PHASE_00_EVIDENCE.md for the `tools/release_e2e.py` run (network attempts, tracked files changed).

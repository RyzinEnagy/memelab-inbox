# Repo map (Phase 00 baseline)

Checked 2026-10-24 (UTC) on `/home/claude/memelab-inbox`, branch `feature/predictive-intelligence`, HEAD `f99c6c7` before any Phase 00 change. Everything here comes from git commands and source reads in this session; README and docs were used only as navigation.

## Where things run

| Place | What it is | Reachable from this session | Evidence |
|---|---|---|---|
| GitHub `RyzinEnagy/memelab-inbox` (public) | the only remote; code, docs, tracked data and the daily state export | yes, `git fetch` over the agent proxy | `git remote -v` |
| Cloud checkout `/home/claude/memelab-inbox` | this session's working copy | yes | `git status` clean at start |
| Elving's Windows machines (work PC with the Claude desktop app; home PC folder `C:\Users\elvin\memelab`; `D:\memelab\`) | where the scheduled Cowork tasks and the key files (`gh_token.txt`, `firecrawl_token.txt`, `D:\memelab\crawl4ai-token.txt`) live, per the package and docs/catalyst/FIRECRAWL.md "Scheduled runs" | no | `get_device_info` lists one linked computer: a Mac (`darwin arm64`) whose only connected folder is the prompt package |
| Linked Mac | holds only the prompt package folder (same 7 top-level entries as the upload) | listing only | `device_list_dir` on the connected folder |

The scheduled runs "rebuild the project from `main`" (docs/catalyst/FIRECRAWL.md, "Scheduled runs") and start from a fresh database each session; only `data/state/latest.json` carries history between sessions (same doc, "What changed in the existing code", and memelab/state.py:1-9). So the code the scheduled runs execute is `main`'s code, which is identical to merge commit `f084b60` (`git diff --stat f084b60 origin/main -- memelab tests tools bridge skills docs` is empty).

## Branches

All tips after `git fetch --all --prune` on 2026-10-24T00:2xZ.

| Branch | Tip | Tip time | Merge base with HEAD | Commits only on branch / only on HEAD | What it adds |
|---|---|---|---|---|---|
| `main` | `98338a8` | 2026-10-23T06:20-04:00 | `f084b60` | 11 / 12 | one `data/state/latest.json` commit a day since 2026-10-13 (`git log f084b60..origin/main` touches only that file); code identical to `f084b60` |
| `feature/social-intelligence` | `3f27fc7` | 2026-10-13T11:51Z | `3f27fc7` | 0 / 3 | social-intel phases 19 to 21 (Reddit, Farcaster, Discord, YouTube adapters) on top of `f084b60` |
| `feature/catalyst-firecrawl` | `f99c6c7` | 2026-10-22T13:53-04:00 | `f99c6c7` (= HEAD) | 0 / 0 | Firecrawl catalyst reads: 27 files, `memelab/catalyst/firecrawl.py` (1,206 lines), tests (37), docs/catalyst/ (`git diff --stat 3f27fc7 f99c6c7`) |
| `feature/predictive-intelligence` (local) | `f99c6c7` at start | | | | this initiative; created from `origin/feature/catalyst-firecrawl` |
| `audit/social-intelligence-phase06` | `b4c4216` | 2026-10-13T15:37-04:00 | `f084b60` | 3 / 12 | branched from `main` at `698f73b`; adds 5 audit documents under `audits/social-intelligence/` (findings register, strategic review, final audit, remediation roadmap, executive summary); no code |
| `remediation/social-intelligence-m00` | `3b434e1` | 2026-10-13T16:34-04:00 | `f084b60` | 18 / 12 | on top of the audit branch: recovered audit evidence, `tests/test_audit_evidence.py`, `tools/check_audit_evidence.py`, social-intel doc updates; no application code |
| `verification/social-intelligence-m00-independent` | `2605b5f` | 2026-10-15T22:57-04:00 | `f084b60` | 22 / 12 | on top of remediation: 169 files of archived audit evidence; its HANDOFF says "M00/R-00 BLOCKED; acceptance withheld. M01 is not authorized" |

Ancestry checks: `f084b60` and `3f27fc7` are ancestors of HEAD (`git merge-base --is-ancestor` exit 0). `698f73b` (the main data commit the audit branches pin) is not an ancestor of HEAD; it differs from `f084b60` only in `data/state/latest.json`.

Pull requests (from docs, not independently verified: `gh` GraphQL is blocked here and an unauthenticated REST call answered 403): PR #1 merged social-intel 00 to 18 into `main` as `f084b60`; draft PRs #2 and #3 belong to the remediation and verification branches. No PR exists for `feature/social-intelligence` or `feature/catalyst-firecrawl` (social HANDOFF.md "Commit and push"; FIRECRAWL.md "Scheduled runs").

## Authoritative code line for this initiative

`feature/catalyst-firecrawl` at `f99c6c7`, continued as `feature/predictive-intelligence`. Evidence: it contains all application code on every other branch (`main` code = `f084b60`, an ancestor; `feature/social-intelligence` = `3f27fc7`, an ancestor), and the three audit branches add no application code (diff stats above). It is not the code that runs in production: the scheduled runs execute `main` (= `f084b60` code), which lacks social-intel 19 to 21 and Firecrawl. Real dated data lives on `main`, not on this branch (this branch's `data/state/latest.json` is the 2026-10-12 export, commit `f69a044`).

Consequence for later phases: anything the predictive engine adds reaches the scheduled runs only after a merge into `main`, which is Elving's call. Until then, forward collection by the scheduled runs uses `main`'s code.

## Python package (actual files, HEAD)

406 tracked files. Tracked code outside tests: `memelab/` (package), `tools/` (release_e2e.py, release_audit.py, direct/), `bridge/` (older copies of the JS collectors), `commit_file.py`, `tools_bundle.py`, `bootstrap.sh`.

| Path | Lines | Role |
|---|---:|---|
| memelab/__main__.py, cli.py | 2, 418 | `python -m memelab {init, plan, fetch, save, discover, stage2, analyze, scout, wallet, catalyst, chains, launch, social, watchlist, rejections, social-note}` (cli.py:388-418) |
| memelab/db.py | 337 | SQLite core schema (20 tables, db.py:24-246), `MEMELAB_DB` override (db.py:18), `init_db` :271, `upsert_token` :288, `insert` :302, `previous_thesis` :323 |
| memelab/normalize.py | 368 | provider bodies to the Solana Bundle (`build_bundle` :59) |
| memelab/pipeline.py | 291 | `run_modules` :26, `analyze_token` :116, `persist_result` :187 |
| memelab/report.py | 277 | `render_token_report` :29, `render_scout_report` :235 |
| memelab/state.py | 139 | state export/import for scheduled runs (`TABLES` :21, `export` :45, `import_` :77) |
| memelab/bridge/ | 6 py/js + 7 js | plan builder (plan.py), result loader (ingest.py), GitHub inbox pull (github_inbox.py), browser/Node collectors (collector.js, screen.js, stage2.js, chains.js, launch.js, catalyst.js, social.js, run_plan.js) |
| memelab/modules/ | 30 files | m01 to m28, pure functions of the Bundle (docs/ARCHITECTURE.md "Bundle contract", confirmed by pipeline.py:26-60) |
| memelab/catalyst/ | 11 files | catalyst ingest, match, attention, assess, monitor, report, Firecrawl (firecrawl.py) |
| memelab/chains/ | 12 files | multi-chain registry, EVM engine, regime, rotation (SOI), narrative, emerging chains |
| memelab/launch/ | 14 files | pre-launch and new-launch engine, launch cohort |
| memelab/social/ | 58 files | social and trader intelligence (phases 00 to 21) |
| memelab/forensics.py, farm.py, wallet.py, secrets.py | | Helius wallet history, dev wallet-farm detector, wallet report, key loading |

Persistent data layers:

- Core DB `data/memelab.sqlite` (tracked although `.gitignore:2 *.sqlite*` matches it; force-added once in `b6c424d`, 2026-10-06, never updated since). Schemas added by catalyst/schema.py, chains/schema.py, launch/schema.py and social/schema.py migrations are created by `db.init_db`; the tracked file predates them (no catalyst, chain, launch or social tables).
- Private stores (gitignored `data/private/`): social private content, the Phase 16 signal ledger `data/private/signal_ledger.sqlite` (social/outcomes_ledger.py:45), Firecrawl config and private page copies.
- State export `data/state/latest.json` (tracked; written by `python -m memelab.state export`, committed daily to `main` by the scheduled runs) and an older root `state/latest.json` (6 commits on 2026-10-07 only).
- Collector files `inbox/*.json` (40 tracked, 2026-10-06 to 2026-10-08) and `data/inbox/*.json` (13 tracked, 2026-10-06 to 2026-10-07).
- Reports `data/reports/*.md` (24 tracked, 2026-10-06/07).

Ignore rules (`.gitignore`): `data/config.json`, `*.sqlite*`, `__pycache__/`, `data/wallet/`, `gh_token.txt`, `data/private/`, `firecrawl_token.txt`. No rule for `.pytest_cache/` (pytest writes its own `.gitignore` inside it).

## Scheduled jobs

No scheduler code or job definition is in the repo. The scheduled runs are Cowork scheduled tasks on Elving's Windows machine (not reachable here). Their footprint in git is the commit cadence on `main`: see DATA_COVERAGE.md. skills/memecoin-scout/SKILL.md is the operating procedure they follow (daily scan: multi-chain pass first, discovery, catalyst pass, launch pass).

## Prior initiative records (located, not assumed)

| Record | Path | Branch |
|---|---|---|
| Social-intel contract, roadmap, decisions (D-001 to D-148), handoff | docs/social-intelligence/EXECUTION.md, ROADMAP.md, DECISIONS.md, HANDOFF.md | HEAD, main (older), social branch |
| Social-intel phase notes | docs/social-intelligence/AUDIT_00.md, SCHEMA_01.md ... YOUTUBE_21.md, ALPHA_11.md, OUTCOMES_16.md, REPLAY_17.md, RELEASE_18.md, release/E2E_RUN.md, release/AUDIT.md | HEAD |
| Catalyst Firecrawl record (decisions FC-1 to FC-16) | docs/catalyst/FIRECRAWL.md | HEAD only |
| Core architecture and sources | docs/ARCHITECTURE.md, docs/SOURCES.md | HEAD |
| Social-intel independent audit (NOT READY verdict, findings register) | audits/social-intelligence/*.md | audit, remediation, verification branches only |
| Remediation M00 evidence and status (BLOCKED, acceptance withheld) | audits/social-intelligence/..., docs/social-intelligence/HANDOFF.md | remediation, verification branches only |
| Backtesting & Stress-Testing v1.2 | nothing found | no branch (see P34 in PHASE_00_EVIDENCE.md) |

There is no `audits/` folder on HEAD before this phase; `audits/predictive-intelligence/` and `docs/predictive-intelligence/` are new namespaces.

## Research tooling found

| Tool | This cloud environment | Repo (all branches) | Windows machines |
|---|---|---|---|
| Firecrawl | no CLI, no Python package; Elving's Firecrawl MCP tools are attached to this session (not used in Phase 00) | integrated over HTTP: memelab/catalyst/firecrawl.py (1,206 lines), 4 CLI commands, 37 tests; `catalyst fc-health` here: `config_missing`, key `missing` (exit 1) | key file `firecrawl_token.txt` in the scheduled-task folder per FC-16: not checked (unreachable) |
| Crawl4AI | no CLI (`crawl4ai`, `crwl`), no package | no reference on any branch | `D:\memelab\crawl4ai-token.txt`: BLOCKED for verification (unreachable; not read; no claim it exists or not) |
| Maxun | no CLI, no package | no reference on any branch | any install: BLOCKED for verification |
| MiroFish (and camel, oasis, zep, graphiti) | no package | no reference on any branch | any install: BLOCKED for verification |
| Other | `node` v22.22.0, `docker` binary, `playwright` 1.63.0 Python package present | Node collector `memelab/bridge/run_plan.js` (`python -m memelab fetch`) | |

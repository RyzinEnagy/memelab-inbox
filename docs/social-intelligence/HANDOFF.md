# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Release record and checklist: [RELEASE_18.md](RELEASE_18.md). Operator docs: [README.md](README.md), [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md). Phase notes: [AUDIT_00](AUDIT_00.md), [SCHEMA_01](SCHEMA_01.md), [CONNECTORS_02](CONNECTORS_02.md), [X_API_03](X_API_03.md), [TELEGRAM_04](TELEGRAM_04.md), [IDENTITY_05](IDENTITY_05.md), [CLAIMS_06](CLAIMS_06.md), [NARRATIVES_07](NARRATIVES_07.md), [REGISTRY_08](REGISTRY_08.md), [WALLETS_09](WALLETS_09.md), [PERFORMANCE_10](PERFORMANCE_10.md), [ALPHA_11](ALPHA_11.md), [CHRONOLOGY_12](CHRONOLOGY_12.md), [INTEGRATION_13](INTEGRATION_13.md), [REPORTS_14](REPORTS_14.md), [ALERTS_15](ALERTS_15.md), [OUTCOMES_16](OUTCOMES_16.md), [REPLAY_17](REPLAY_17.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 18 (Prompt 18: end-to-end release engineering, operational audit and delivery), 2026-10-12. Prompt 18 took the Phase 18 slot; the old proposed Phase 18 (catalyst attention) is now carry-over C-18 (D-119).
- Prompt 18 says stop after delivery. No further phase is started.
- Active branch: `feature/social-intelligence`.
- Phase 18 started from `6efbc73` (Phase 17 handoff), the remote branch head. No drift. Baseline `python -m pytest tests -q`: `1 failed, 643 passed`, as recorded by Phase 17.
- No migration. Public schema stays at 12. No change under `memelab/` in this phase.
- Model status: none configured (D-036). Data status: no social data in any lab database; real replay INSUFFICIENT_DATA.

## What Phase 18 added

- `tools/release_e2e.py`: clean clone of the committed HEAD, credentials removed, all stores in a temp folder, network refused by an audit hook; 45 stage commands from setup to causal replay; after-checks for network attempts, stray files and the tracked database. Also `--migrate-check DB`.
- `tools/release_audit.py`: credential and key-material shapes in the tree and public history, signing or order code, network paths, example config defaults, content guard on this branch and `main`, migration of both lab databases, local paths in public data, syntax checks and pyflakes. Prints locations, never values.
- `tests/test_release_tools.py` (8 tests).
- Docs: README.md, ARCHITECTURE.md, OPERATIONS.md (all for a non-programmer), RELEASE_18.md (checklist with 66 rows), release/E2E_RUN.md and release/AUDIT.md (generated on `e8b6688`), examples/FIXTURE_example_report.md, examples/REAL_DATA_example_report.md; root README section; DECISIONS D-119 to D-124; ROADMAP (18 DONE, C-18 added, 19 depends on C-18, 21 narrowed); SOURCE_COVERAGE row.

## Gate, item by item

See RELEASE_18.md "Release checklist". Summary: every requirement of Prompt 18 is PASS except the ones that need Elving or do not exist yet: live model, X, Telegram, Helius fetch, trader list, alert delivery and scheduled jobs (BLOCKED); public data hygiene on `main` (BLOCKED, Phase 20 and Elving); full suite fully green (C-1), type checking, a candle provider, social steps in the scheduled runs (NOT IMPLEMENTED); merge (BLOCKED, Elving).

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change (`e8b6688`): exit 1, `1 failed, 651 passed in 123.46s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1).
- `python -m pytest tests/test_release_tools.py -q`: `8 passed`.
- `python tools/release_e2e.py`: exit 0, `Result: PASS`, 45 of 45, 0 network attempts, 0 stray files.
- `python tools/release_audit.py --history`: exit 0, `Needs action: no`.
- `python -m memelab social guard`: exit 0.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean before each commit.

## Things the next session should know

- The release tools are the regression check for any later phase: run both before a commit. `release_e2e.py` tests the committed HEAD, so commit first, then run it.
- A re-ingest of an already processed file whose other units are down exits 1 (D-121). It is recorded, not changed.
- The scheduled runs on `main` write session paths into public state files (D-123); fix belongs in Phase 20.
- pyflakes reports 73 unused-import and unused-variable messages and no undefined names; not fixed in a release phase.

## Helius key

The key is not in the repo and must never be committed (release audit: no `api-key=` value or credential shape in the tree or history). Code reads it through `memelab/secrets.py`: first the `HELIUS_API_KEY` environment variable, then `helius_api_key` in the gitignored `data/config.json` (`python -m memelab.secrets set`). Check with `python -m memelab.secrets status` (prints set or missing and the source, never the value). A session that needs it asks Elving. The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is refused by the git proxy. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- Live routes need credentials and cost approvals that are Elving's: `X_BEARER_TOKEN` and an X budget, `TELEGRAM_BOT_TOKEN` and channel admins, `ANTHROPIC_API_KEY` and a model budget, `HELIUS_API_KEY` in the run, alert transport variables and opt-in.
- D-025, D-028, D-023 and D-036 remain open.
- C-1 keeps the full suite from being fully green.
- Merge of the pull request is Elving's decision (D-124).

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q && python tools/release_e2e.py --out e2e.md
```

Expect `1 failed, 651 passed` and `Result: PASS`.

## Commit, push and pull request

Phase 18 code and docs commit on `feature/social-intelligence`: `e8b6688` locally. This handoff and the release record are the commit on top of it. Push and pull request: recorded below after they are done.

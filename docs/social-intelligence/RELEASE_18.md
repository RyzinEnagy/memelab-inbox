# Phase 18: release record and checklist

Prompt 18, 2026-10-12. Scope: release engineering, an operational audit of the code as implemented, and delivery. No new provider integration and no refactor (D-119). Code added: `tools/release_e2e.py`, `tools/release_audit.py`, `tests/test_release_tools.py` (8 tests). Docs added: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), [OPERATIONS.md](OPERATIONS.md), this file, [release/E2E_RUN.md](release/E2E_RUN.md), [release/AUDIT.md](release/AUDIT.md), [examples/FIXTURE_example_report.md](examples/FIXTURE_example_report.md), [examples/REAL_DATA_example_report.md](examples/REAL_DATA_example_report.md). Decisions D-119 to D-124.

## Result first

- Every stage from inbox load to causal replay runs end to end on invented fixtures in a clean clone with the network blocked: 45 of 45 stage commands returned their expected exit code, 0 network attempts, 0 stray files, tracked database byte-identical ([release/E2E_RUN.md](release/E2E_RUN.md), commit `e8b6688`).
- Audit: no credential shape or key material in the tracked tree or in 642 blobs of public history (one test placeholder reviewed), no signing or order code, content guard clean on this branch and on `main` (`f69a044`), both lab databases migrate to schema 12 with legacy rows unchanged, all example configs off by default ([release/AUDIT.md](release/AUDIT.md)).
- Full suite after the last code change: `1 failed, 651 passed`; the failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1).
- On real data the honest answer stands: no social posts or wallet events are stored, so the brief has no supported observation and every replay strategy is INSUFFICIENT_DATA ([examples/REAL_DATA_example_report.md](examples/REAL_DATA_example_report.md)).
- Every live route is blocked on a credential, a cost approval or a terms decision that is Elving's. Nothing live was claimed.

## How to reproduce

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence
pip install pytest numpy pyflakes
python -m pytest tests -q                                          # 1 failed (C-1), 651 passed
python tools/release_e2e.py --out e2e.md --json e2e.json           # Result: PASS, about 60 s
git fetch origin main && python tools/release_audit.py --history   # Needs action: no
```

`release_e2e.py` clones the committed HEAD, so it proves what is committed, not the working copy. Stage numbers in the run: 00 setup, 01 migrations, 02 fixture inbox load, 03 duplicate replay, 04 token resolution, 05 structured extraction, 06 narrative change, 07 trader registry, 08 wallet attribution, 09 P&L, 10 information alpha, 11 chronology, 12 discovery integration, 13 reports, 14 alerts, 15 forward outcomes, 16 causal replay, 17 no-credentials behaviour, 18 content guard.

## Commands run in this session (exit codes)

| Command | Exit | Output |
|---|---|---|
| `python -m pytest tests -q` (baseline, `6efbc73`) | 1 | `1 failed, 643 passed in 126.14s`, same as the Phase 17 handoff |
| `python tools/release_e2e.py --out docs/social-intelligence/release/E2E_RUN.md` (on `e8b6688`) | 0 | `Result: PASS`, 45 of 45 |
| `python tools/release_audit.py --history --out docs/social-intelligence/release/AUDIT.md` (on `e8b6688`) | 0 | `Needs action: no` |
| `python -m pytest tests/test_release_tools.py -q` | 0 | `8 passed` |
| `python -m pytest tests -q` (after the last code change, `e8b6688`) | 1 | `1 failed, 651 passed in 123.46s` (C-1 only) |
| `python -m memelab social guard` | 0 | 0 violations |
| `python -m memelab social brief --db <copy of main's lab database>` | 0 | "No supported high-priority observations", reason: social schema not migrated |
| `python -m memelab social replay run --db <copy> --inbox <main's 39 collector files>` | 0 | INSUFFICIENT_DATA for all four strategies |

The EVM catalyst test still writes `data/reports/<stamp>_BRETT_*.md` on every suite run (C-1); the files were deleted by hand after each run and `git status` was clean before each commit.

## Release checklist

Status values: PASS (done and proved), BLOCKED (built, waiting on something outside the code), NOT IMPLEMENTED (does not exist yet).

| # | Requirement | Status | Proof | Decision |
|---|---|---|---|---|
| 1 | Read the handoff and every prior phase record | PASS | HANDOFF.md, phase notes 01 to 17, baseline matches (`1 failed, 643 passed`) | none |
| 2 | Audit the implemented code, not the original spec | PASS | each stage reruns the phase's own CLI on its own fixture (E2E_RUN.md) | none |
| 3 | No new speculative integration or sweeping refactor | PASS | `git diff 6efbc73..HEAD --stat`: two tools, one test file, docs; no change under `memelab/` | D-119 |
| 4 | Clean-environment setup | PASS | E2E stage 00 (fresh clone, Python 3.13.16, numpy, pytest) | D-120 |
| 5 | Migrations | PASS | E2E stage 01: empty to 12, idempotent rerun, tracked copy with legacy counts unchanged; AUDIT: `main` database too | none |
| 6 | Fresh fixture inbox load | PASS | E2E stage 02: 7 items seen, 4 created, 3 quarantined (invalid time, text, non-public), 2 units down or login-walled recorded, run continues | none |
| 7 | Duplicate replay | PASS | E2E stage 03: same file `created 0`, renamed copy `created 0, duplicates 4` | D-121 (same file exits 1 by design) |
| 8 | Token resolution | PASS | E2E stage 04: ambiguous ticker stays ambiguous, exact contract resolves | none |
| 9 | Structured extraction | PASS | E2E stage 05: deterministic token reference without a model; grounded claim through the offline mock | none |
| 10 | Live model analysis | BLOCKED | `social llm-health`: `model_not_configured` | model id, prices, cap and `ANTHROPIC_API_KEY` are Elving's cost decision (D-036) |
| 11 | Narrative change | PASS | E2E stage 06: snapshot 1 empty, snapshot 2 one cluster, change NEW | none |
| 12 | Trader registry | PASS | E2E stage 07: fixture list imported (11 entities, 12 links, no approval or rank), fixture account added | none |
| 13 | Wallet attribution | PASS | E2E stage 08: self-disclosure gives SELF_CLAIMED with identity UNKNOWN; custody wallet refused (exit 1) | none |
| 14 | P&L reconstruction | PASS | E2E stage 09: reconciled, PARTIAL coverage stated, score refused below 20 positions | none |
| 15 | Information-alpha evaluation | PASS | E2E stage 10: PRELIMINARY 50 with reasons, sparse source declined | none |
| 16 | Social and on-chain chronology | PASS | E2E stage 11: CONFIDENT and INDETERMINATE fixtures | none |
| 17 | Main discovery integration | PASS | E2E stage 12: scout report body unchanged, policy off by default, `trade_execution_impact: none` | none |
| 18 | Report generation | PASS | E2E stage 13: fixture brief, digest, feed; brief on the e2e store through the real read path | none |
| 19 | Alert dry run | PASS | E2E stage 14: fixture run and deduped rerun; e2e store "No alerts today"; `--send` without consent exits 2 | none |
| 20 | Forward outcome evaluation | PASS | E2E stage 15: ledger before and after two evaluations | none |
| 21 | Causal replay | PASS | E2E stage 16: synthetic replay with "No leakage detected"; real copy INSUFFICIENT_DATA | none |
| 22 | Exact commands and outputs captured | PASS | release/E2E_RUN.md (1,217 lines, every command and exit code) | none |
| 23 | Full test suite | PASS | `1 failed, 651 passed`; the failure is C-1 and is not new | C-1 stays a carry-over |
| 24 | Full suite fully green | NOT IMPLEMENTED | C-1 not fixed | carry-over C-1 |
| 25 | Lint and static checks already used in the repo | PASS | the repo configures none; AUDIT runs Python syntax (176 files, 0 errors), `node --check` (16 files, 0 errors) and pyflakes (unused imports and variables only, 0 undefined names) | pyflakes findings reported, not fixed (D-122) |
| 26 | Type checking | NOT IMPLEMENTED | no type checker in the repo | not added in a release phase |
| 27 | Credential leakage | PASS | AUDIT: tree and public history clean; one test placeholder reviewed; HANDOFF names variables only | D-122 |
| 28 | Restricted social content | PASS | content guard exit 0 on this branch, 0 violations on `main` | none |
| 29 | Accidental wallet keys | PASS | AUDIT: no PEM, keypair array or key-material field; no signing code (sigverify is verify-only) | none |
| 30 | Public redistribution on this branch | PASS | guard, fixture labels, no post wording in reports (D-095) | none |
| 31 | Public data on `main`: session paths in state files, news RSS text in `inbox/cat01_*.json` | BLOCKED | AUDIT "Local paths" (`data/state/latest.json` 473, `state/latest.json` 41 and others); AUDIT_00 for the RSS text | Phase 20 state export rules and Elving (D-123, D-004 note) |
| 32 | Schema incompatibility | PASS | both lab databases migrate 0 to 12, legacy rows unchanged; rollback to 0 checked on a copy (OPERATIONS.md) | none |
| 33 | No accidental live or billable request | PASS | E2E: 0 network attempts with every credential removed; example configs `allow_billable` false, caps 0; tracked database has no spend rows | D-120 |
| 34 | No excessive logs | PASS | no log file is tracked; logs are JSON lines on stderr that name fields, never values; info logs only with `-v`; secrets redacted (D-016, D-024) | none |
| 35 | No trading execution | PASS | AUDIT "Trade-execution and signing code": none; `test_no_trade_execution_or_signing_code_in_tracked_files` | none |
| 36 | README, architecture and operations runbook | PASS | README.md, ARCHITECTURE.md, OPERATIONS.md | none |
| 37 | Source access | PASS | README "What works today", SOURCE_COVERAGE.md | none |
| 38 | Costs | PASS | README "Costs" | none |
| 39 | Environment variable names, never values | PASS | README "Settings you may set" | none |
| 40 | CLI quick start | PASS | README "Quick start" | none |
| 41 | First-ever setup | PASS | README "First-ever setup on a machine" | none |
| 42 | Schedule enable and disable | PASS | OPERATIONS "Turning a schedule on and off" | enabling stays Elving's call (D-104) |
| 43 | Maintenance | PASS | OPERATIONS "Maintenance" (commands checked in this session) | none |
| 44 | Data deletion | PASS | OPERATIONS "Deleting data" (backup and rollback checked on a copy) | per-source deletion is not a command yet |
| 45 | Troubleshooting | PASS | OPERATIONS "Troubleshooting" | none |
| 46 | Known unsupported features | PASS | OPERATIONS "Not supported today" | none |
| 47 | Citation and uncertainty standards | PASS | README "How to read the output" | none |
| 48 | Configuration opt-in, safe defaults | PASS | E2E stage 12 policy `enabled: false`; AUDIT example configs; `--send` needs consent | none |
| 49 | Routes replayable | PASS | fixed clocks, immutable snapshots and `verify` commands; replay leakage check (E2E stage 16) | none |
| 50 | Fixture-only example report | PASS | examples/FIXTURE_example_report.md, watermarked top and bottom | none |
| 51 | Authorized real-data example report | PASS | examples/REAL_DATA_example_report.md, from data the lab's own runs captured on `main` (market data only; no social data exists) | none |
| 52 | No-signal behaviour | PASS | real brief "No supported high-priority observations" with the reason; alerts "No alerts today" | none |
| 53 | No-credentials behaviour | PASS | E2E stage 17: health commands report `credentials_missing` with no call; live ingest refuses before any call | none |
| 54 | Release checklist with status and proof | PASS | this table | none |
| 55 | Commit on the feature branch | PASS | `e8b6688` (tools and docs) and the release-record commit on top; see HANDOFF.md for remote hashes | none |
| 56 | Pull request | see HANDOFF.md | the pull request URL is recorded there after it is opened | D-124: review only, no merge |
| 57 | Never force-push `main` | PASS | branch ref fast-forwarded only; `main` untouched | D-001 |
| 58 | Live X collection | BLOCKED | `x-health`: `credentials_missing` | X app, token and budget; D-025 for the Chrome route |
| 59 | Live Telegram collection | BLOCKED | `tg-health`: `credentials_missing` | bot token, channel admins, D-028 |
| 60 | Live Helius wallet fetch | BLOCKED | `memelab.secrets status`: missing in this session | Elving supplies the key to the run that needs it |
| 61 | Live trader list | BLOCKED | registry proved on fixtures only | a permitted list or export from Elving |
| 62 | Alert delivery to a device | BLOCKED | no transport configured; dry run only | opt-in and transport credentials (D-102) |
| 63 | Scheduled social jobs | BLOCKED | templates `enabled: false` | Elving approves a scheduled task (D-104) |
| 64 | Historical candle provider for alpha and outcomes on real tokens | NOT IMPLEMENTED | alpha and outcomes take supplied candles only | later phase |
| 65 | Social steps in the scheduled runs, automatic signal recording, social state export | NOT IMPLEMENTED | Phases 19 and 20 | roadmap |
| 66 | Merge into `main` | BLOCKED | pull request open for review | Elving; Phase 21 (D-124) |

## Operational integrations, exactly

Working without credentials: storage and migrations, bridge inbox import, token identity on supplied provider bodies, deterministic claim extraction, narratives, registry, wallet attribution and activity import from documents, P&L, information alpha, chronology, scout and catalyst research section (opt-in), brief, digest, feed, alert dry run with file outbox, signal ledger, replay, content guard, release tools.

Built but not live: X API, Telegram Bot API, model extraction, alert transports (Telegram bot, email), scheduled alert jobs.

Not built: X or Telegram reads through Chrome, other sources, purge of deleted X posts, a candle provider for real-token alpha and outcomes, social steps in the scheduled runs.

## Exact blockers

1. Credentials not in this session and not for an agent to create: `X_BEARER_TOKEN`, `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `HELIUS_API_KEY`, alert transport variables.
2. Cost approvals: X API budget (about $30 to $180 a month at 20 accounts, estimate), model budget.
3. Terms decisions still open: D-025 (X browser automation), D-028 (Telegram channel data), D-023 and D-036 (paid APIs).
4. Push from this session's own git is refused by the git proxy; the working route is Elving's GitHub connection through Composio and the Git Data API (fast-forward only).
5. C-1 keeps the full suite from being fully green.
6. Merge is Elving's decision after review.

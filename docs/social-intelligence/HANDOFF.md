# CURRENT REMEDIATION HANDOFF — M00 (2026-10-13)

**Authoritative current package:** M00 / R-00 **PARTIAL RECOVERY — BLOCKED; INDEPENDENT VERIFICATION PENDING**. The historical Phase 18 implementation handoff appears below for provenance only. **No new application implementation package is authorized.**

- **Branch:** `remediation/social-intelligence-m00`, branching from `audit/social-intelligence-phase06` at `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6`.
- **Pinned audited application:** `main` @ `698f73b854567ce60b56ce275b5ab6822a9d5f60`; separately reviewed optional feature @ `3f27fc788f9ab88286b8041355e5445fdfdf012c`.
- **Findings addressed:** R-00 evidence availability only, *partial*; no AUD/ARCH/ADV/OPS application finding is resolved. The previously missing document count fell from seven to two; no original defect was patched.
- **Files recovered:** `audits/social-intelligence/recovered/{00_BASELINE.md,REQUIREMENTS_MATRIX.md,01_FUNCTIONAL_AUDIT.md,04_ADVERSARIAL_AUDIT.md,05_OPERATIONS_AND_UX.md}`. See `audits/social-intelligence/EVIDENCE_MANIFEST.json` (SHA-256); `EVIDENCE_CROSSWALK.md` (46 indexed IDs); `M00_RECOVERY_REPORT.md`; `M00_VERIFICATION.md`.
- **Verification tooling:** `tools/check_audit_evidence.py` and `tests/test_audit_evidence.py` only; main engine code and schemas unchanged, migrations **none**.
- **Tests:** focused M00 4 passed; integrity `BLOCKED` / 6 of 8 with no checksum mismatches; strict gate exits 2 as designed. Full legacy suite was attempted but the test process exited 137 around 70%; **no complete suite result**. It created an untracked BRETT report (test-created only; removed after final checks); targeted catalyst suite **1 failed / 4 passed**, combined `--maxfail=2` diagnostic **2 failed / 295 passed** (additional ingest logger test passes alone); `social guard` found zero violations; existing AUD-011 remains open. No live/paid/trading tests.
- **Prior-chat recovery result:** earlier chats show Phase 02 actually generated an architecture report and AUD-018–023; Phase 03 generated a research validity report and AUD-024–033. Both previous-chat sandbox artifacts are unmounted here, so original report bytes remain pending. Published `FINDINGS.md` omitted those 16 IDs; see `audits/social-intelligence/M00_PRIOR_CHAT_LOCATORS.md`.
- **What remains:** missing `02_ARCHITECTURE_AUDIT.md`, `03_RESEARCH_VALIDITY.md` and original audit probe/log artifacts; 04/05 source-byte equivalence unverified; 13 secondary-only and 10 architecture crosswalk IDs; an independent reviewer must inspect all ID mappings. OPS IDs not explicitly labeled in the Phase 05 report.
- **Commit sequence:** source recovery `61f7f06181f567311ed0da54436500989719014c`; subsequent verification/documentation commit(s) on the same branch. The GitHub branch tip and PR history, not this in-file statement, are authoritative for final tip SHA.
- **Next exact command:** `python -m pytest tests/test_audit_evidence.py -q && python tools/check_audit_evidence.py --require-complete` on a fresh M00 checkout. Expect the second command to exit **2** until missing evidence is supplied; consult `M00_VERIFICATION.md` for complete independent checklist.
- **Next conditional package:** M01 / R-01 and R-02 historical causality and provenance. **DO NOT START until M00 independently accepted.**

---

## Historical implementation handoff (pre-remediation; not a current approval)

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
- pyflakes reports 75 messages (unused imports and variables, f-strings without placeholders, and one harmless redefinition in `tools/release_audit.py` where a local name shadows the pyflakes import); no undefined names. Not fixed in a release phase.

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

Local commits on `feature/social-intelligence`: `e8b6688` (tools and docs, tree `b11eb00`), `3710d34` (release record and handoff, tree `1f8bcee`), and this handoff update on top. Remote hashes differ from the local ones (local commits are signed in the session; the Git Data API commits are not); the trees are checked equal.

Pushed 2026-10-13T02:03Z through Composio and the GitHub Git Data API: 16 blobs created, each checked against the local blob sha before upload; both trees equal to the local trees; branch ref fast-forwarded once from `6efbc73`, no force. Remote commits: tools and docs `8f08d282491b5c87ceaba25d8baf303e513cfe8d`, release record `683f21ba1a68a5004c93a7a9ab0cafb15c22e668`; this handoff update is pushed on top of them the same way (its remote hash is on the branch head). `main` untouched (`f69a044`).

Pull request: https://github.com/RyzinEnagy/memelab-inbox/pull/1 (`feature/social-intelligence` into `main`, open, not merged, review only per D-124).

Phase 18 is complete. Stop here; no further phase is started.

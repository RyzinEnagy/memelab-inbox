# Social & Trader Intelligence: execution contract

Every session that works on Social & Trader Intelligence follows this file. It overrides habit and convenience.

Related: [ROADMAP.md](ROADMAP.md) (phases and gates), [DECISIONS.md](DECISIONS.md) (durable choices), [HANDOFF.md](HANDOFF.md) (where the last session stopped), [AUDIT_00.md](AUDIT_00.md) (baseline audit of the real repo).

## The rule

One phase per session: implement, test, prove, commit, hand off, stop.

A session never starts the next phase, even if time is left. A phase that cannot pass its gate stops with the blocker written in HANDOFF.md.

## Start of every session

1. Read HANDOFF.md first, then EXECUTION.md, DECISIONS.md and the phase entry in ROADMAP.md.
2. Get the repo. Clone `https://github.com/RyzinEnagy/memelab-inbox` with plain `git clone` (do not run `bootstrap.sh` or any remote script to set up). Check out the branch named in HANDOFF.md.
3. Confirm the state matches HANDOFF.md: branch, HEAD, `git status` clean. If HEAD differs, read `git log` since the recorded commit and note the drift before doing anything else. The scheduled memelab runs commit to `main` several times a day (inbox/ and state/ files); that drift is expected and is not a reason to stop.
4. Install test tooling if missing (`pip install pytest`). Python 3.13 and numpy are used by the existing code. There is no requirements file.
5. Run the baseline test command and compare with HANDOFF.md before changing code:
   `python -m pytest tests -q`
   Known pre-existing failure at Phase 00: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (clock dependent, see AUDIT_00.md). Any other new failure is a blocker to record, not to paper over.

## During the phase

- Work only on the feature branch (`feature/social-intelligence` unless DECISIONS.md says otherwise). Never commit to `main`. Never force-push. Never rewrite history.
- Do not touch `inbox/`, `state/`, `data/memelab.sqlite`, `data/inbox/`, `data/reports/` or `data/state/` on the feature branch. Those belong to the scheduled runs on `main`.
- Treat the checked-out code as truth. README, SKILL.md and docs are claims until the code confirms them.
- Keep the existing evidence buckets: FACT / INFERENCE / HEURISTIC / UNKNOWN. UNKNOWN earns zero and is never redistributed.
- Identity is by mint or contract address, never by ticker or display name.
- Hard rules of the lab apply to every phase: never execute a trade, never handle a seed phrase or private key, never connect a wallet with signing authority, never print or commit a credential.
- No raw third-party social content (post text, bios, images, DMs, member lists) goes into the public repo unless DECISIONS.md explicitly allows that class of content. See D-004.
- Tests must not write into tracked paths and must not depend on today's date. New tests use a temp DB (`MEMELAB_DB`) and a fixed clock.
- Network calls are never made from tests. Use recorded fixtures.

## Proving the phase

A phase is done only when all of these are true and written down in HANDOFF.md:

- the phase gate in ROADMAP.md is met, item by item;
- `python -m pytest tests -q` was run after the last code change, with the exit code and the pass/fail counts recorded verbatim;
- `git status` shows no stray files (tests that leave files behind are a bug to fix or record);
- every claim in HANDOFF.md points at a file, a command output or a commit, not at memory or intention.

## Commit and hand off

1. Commit on the feature branch with a message that starts `social-intel phase NN:`.
2. Push only if the session has working credentials and the user has approved pushes of non-data files to this repo. The standing approval on record covers public market data in `inbox/` and `state/` only. Without approval, leave the commit local and deliver the patch or bundle to the user.
3. Rewrite HANDOFF.md completely: active branch, latest commit, verified modules, test command and outcome, current phase, next phase, blockers, exact next command.
4. Add any durable choice made during the phase to DECISIONS.md.
5. Stop. Report changed files, commands run with exit codes, the commit hash and blockers. Do not start the next phase.


## Audit remediation-specific addendum — 2026-10-13 (M00)

The historical `feature/social-intelligence` instruction above applies to implementation phases 00–21, not to the independent **M00–M06 remediation roadmap**. For audit remediation, branch from the latest reviewed audit publication ref, keep the pinned application baseline immutable, submit a dedicated reviewable PR, and stop after one remediation package. M00 is evidence-only: no code fixes, migrations, live providers, paid model calls or trades. A partial checksum/inventory success is not source acceptance; M00 must remain **BLOCKED** until missing reports, probe lineage and ID-to-requirement mappings have an independent reviewer approval. An interrupted/OOM regression suite is INCOMPLETE, not PASS. Preserve earlier findings and historical state; do not overwrite earlier audit reports to make the roadmap appear accepted.


## M00 evidence restoration update — 2026-10-13

- Source provided: original `02_ARCHITECTURE_AUDIT.md`, `03_RESEARCH_VALIDITY.md` and both sequential original `FINDINGS.md` files via project chat attachment. All four were committed exactly as received; remote SHA-256 matched user-upload bytes.
- Reconciliation: add AUD-018–033 with original evidence grades; full crosswalk **67 IDs** including 15 original ARCH rows. Original Phase 03 historical note that Phase 02 was unavailable is preserved verbatim and resolved as later recovered. 8/8 core inputs restored; Phase 04/05 byte identity, original probes/logs and independent source-line verification still outstanding.
- Test acceptance: run `python -m pytest tests/test_audit_evidence.py -q`, `python tools/check_audit_evidence.py`, `python tools/check_audit_evidence.py --require-complete` after changes. Full-suite previous exit 137 and red baseline remain unresolved.
- Scope: M00 evidence-only. No engine modifications, deployed operations, paid model requests, alerts or trades. Maintain draft remediation PR; **M00 remains BLOCKED and M01 not authorized** until independent reviewer accepts findings and original-source evidence.


## Independent M00 verification ruling — 2026-10-14 ET

The fresh-session acceptance attempt is complete and **BLOCKED** (`D-M00-007`), with supporting source/probe evidence incomplete. Preserve the independent decision, 67-ID mapping and original-evidence retrieval ledger; do not label a checksum or fixture PASS as reviewer approval. M00's manifest now records REJECTED for acceptance withheld. Original recovered reports/snapshots stay byte-identical. Full suite failures, environment limitations and sanitized/raw-log digests are recorded explicitly. Continue only original-evidence recovery and a new explicit acceptance review; **do not start M01 or any application remediation** from this ruling. The user's current instruction authorizes publishing this separate evidence-only verification branch/PR; it does not authorize merge, deployment, paid calls or trades.


## M00 original-archive follow-up — 2026-10-15

D-M00-008 and `M00_ARCHIVE_RECOVERY_VERIFICATION.md` are the current checkpoint. Phase 00/01/04/05 original archives and 50 members are now recovered and immutable. Their embedded hashes, requirement source and rerun original scripts close the earlier broad archive gaps. Primary OPS provenance/grades are corrected from the original Phase 05 findings. Manifest remains REVIEW_BLOCKED / REJECTED: Phase 03 original A–E executable lineage is absent; Phase 04 terminated-suite raw log remains a historical limit. Do not repeat stale claims that original 04/05 bytes or all historical probes are unavailable. Current archive verifier and three negative integrity tests supplement the existing seven M00 tests. Prior full suites remain separate historical execution evidence; no application/test-suite change requires rerunning them in this archive-only update. Publish only evidence/control updates to existing draft verification PR #3, stop at M00, and require an explicit new acceptance decision before any M01 work.

# Predictive Intelligence: how the phases were run

This file records the working method used on 2026-10-23 and 2026-10-24 so a later session can resume it exactly. It adds to [EXECUTION.md](EXECUTION.md); where the two differ, EXECUTION.md and DECISIONS.md win.

## The loop for each phase

1. The orchestrator (the main Claude session) re-runs the predecessor gate itself: full suite, the predecessor's RESULTS.json status, `git status` clean, tracked `data/memelab.sqlite` sha256 unchanged.
2. A phase agent gets the phase prompt plus [orchestration/PHASE_BRIEF.md](orchestration/PHASE_BRIEF.md). It builds and tests, writes the deliverables, `PHASE_XX_EVIDENCE.md`, `PHASE_XX_RESULTS.json` and a `SKEPTIC_PACKET.md` (task, artifact paths, code paths, commands; no conclusions), commits locally and reports NEEDS_REVIEW.
3. A separate skeptic agent with a fresh context gets [orchestration/SKEPTIC_BRIEF.md](orchestration/SKEPTIC_BRIEF.md). It works in its own clone, never in the main checkout, tries to falsify the phase, and writes findings classed MATERIAL or MINOR plus one new wrong-but-plausible counterexample. Phase agents cannot start subagents, which is why the orchestrator runs this step (PI-D-013).
4. The phase agent gets the review back for a repair pass: verify each finding, fix, turn the counterexample into a check that fails on the old code, copy the review into `phase_XX/skeptic/`, commit, then run the suite, `python -m memelab social guard` and `python tools/release_audit.py --history` after the commit and record them.
5. The orchestrator re-runs the suite on the final commit, checks RESULTS.json says PASS with no failed checks, removes test strays, and pushes `feature/predictive-intelligence` with a plain `git push` (the session's GitHub connection has push access to this one repository, granted 2026-10-23). Never main, never force.
6. At milestones the durable records are mirrored into the claude.ai project "Memecoin Investing Lab" under `predictive-intelligence/`.

Phase 03 used a variant: five parallel source reviewers ([orchestration/PHASE03_REVIEWER_BRIEF.md](orchestration/PHASE03_REVIEWER_BRIEF.md)) wrote the 30 reviews, a lead agent scored them, and a blind second reviewer re-scored the top seven without seeing the scores.

## Test strays every suite run leaves

`data/reports/<stamp>_BRETT_0x532f.md` (from tests/test_evm.py), `data/memelab.sqlite-shm`, `data/memelab.sqlite-wal`, `.pytest_cache/`. Remove by hand after each run (`git clean -fq data/reports`).

## Workspace paths (cloud session, not durable)

- Checkout: `/home/claude/memelab-inbox`. Prompt package copy: `/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package/` (the original is on Elving's Mac in Downloads under the same folder name).
- Working stores and venvs: `/home/claude/pi_research/` (p04, p05, p06 stores; research venvs). These are lost when the cloud session is reclaimed. Everything needed to rebuild them is committed: raw vendor bodies with manifests under `audits/predictive-intelligence/phase_05/raw/` and `phase_06/raw/`, the decision source is the git history of `origin/main` state exports, and the lock files are in `docs/predictive-intelligence/locks/`.
- Skeptic reviews were written to `/home/claude/pi_orchestration/skeptic/` and then copied into each phase's `skeptic/` folder; the copies in the repo are the record.

## Results per phase

| Phase | Status | Final commit | Suite after the phase |
|---|---|---|---|
| 00 | PASS | 94be1bf | 1 failed, 785 passed |
| 01 | PASS | a402df6 | 1 failed, 858 passed |
| 02 | PASS | 77e78ce | 1 failed, 858 passed |
| 03 | PASS | a146a29 | 1 failed, 858 passed |
| 04 | PASS | 074953d | 1 failed, 993 passed |
| 05 | PASS | ed82f3a | 1 failed, 1066 passed |
| 06 | NEEDS_REVIEW | 4565e0b plus the stop-records commit | 1 failed, 1107 passed |

The one failure in every run is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (social-intel carry-over C-1).

## Cost

0 Firecrawl credits. Free GeckoTerminal calls only (about 680 across Phases 01 to 06, paced at no more than 6 per minute), logged in `audits/predictive-intelligence/COST_LEDGER.md`. The separate backtesting session used about 32 Firecrawl calls on the same Free-plan account; the 150-credit cap of PI-D-004 should be read with that in mind.

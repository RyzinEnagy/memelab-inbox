# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 02 evidence: `audits/predictive-intelligence/phase_02/` (PHASE_02_EVIDENCE.md, PHASE_02_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md marked USED, skeptic/, research/, probes/). Phases 00 and 01 evidence stays in `phase_00/` and `phase_01/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase completed: 02 (independent predictive GitHub discovery), 2026-10-24. Status PASS after repair pass 2. It was NEEDS_REVIEW at `498eaa0`; the orchestrator's independent skeptic found 1 MATERIAL and 6 MINOR findings and a counterexample; each was verified and repaired (change control PI-D-025).
- Branch `feature/predictive-intelligence`: `498eaa0` (content) and the repair pass 2 commit on top (see "Commit"). No production code: nothing under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed. Not pushed (PI-D-003). Spend 0 credits.

## What Phase 02 found

- GitHub search, repository REST and github.com HTML pages answer 403 from the session proxy; discovery used the package keyword index, documentation and paper links, WebSearch and PyPI; facts come from `git ls-remote` pins, clones at the pin, root commits and repos.ecosyste.ms (PI-D-023).
- Needs frozen first (`research/NEEDS.csv`, clarifications in `research/NEEDS_NOTES.md`). Corpus: 68 distinct successful queries over 11 families and 5 mechanisms, plus 22 refused GitHub searches (`research/SEARCH_LOG.md`).
- `research/CANDIDATES.csv`: 132 candidates (131 unique root histories), each on its canonical path (successor search for rows without a mirror record, PI-D-025), with pin, license from the file bytes at the pin, flags, needs, gap cells, provenance and independent-discovery credits (99 of 132).
- `research/SHORTLIST.csv`: 30 for Phase 03 (tabular 5, time series 4, calibration 5, online and drift 4, behavioral 4 with MiroFish, OASIS, Mesa, black-it, experiment audit 4, event-time labels 3, point-in-time feature store 1: feast), each with code evidence at the pin, the question Phase 03 must answer, and a per-file license scan (`research/LICENSE_SCAN.csv`). No score or rank; the written shortlist rule is in `research/EXCLUSIONS.md` section G.
- `research/EXCLUSIONS.md`: same-HEAD paths, vanished repositories, forks and mirrors, crawler tooling, README-only repositories (P42), non-matching or archived seeds, the reason each candidate is not shortlisted, and the repair-pass screen (section H).
- For Phase 03: featuretools (closest conceptual match for as-of features) is an inactive candidate; regime states (N07) come from statsmodels MarkovRegression; license flags and vendored code to resolve are listed in ROADMAP.md "Known constraints carried from Phase 02". MiroFish needs LLM and Zep Cloud keys and Python below 3.13 and has no probability output; OASIS needs Python below 3.12 and neo4j.

## How to check it

- `python3 audits/predictive-intelligence/phase_02/probes/check_candidates.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv` (offline, `problems 0`); add `--live 10 --seed <n>` to re-fetch pins and re-read the shortlisted code evidence.
- `python3 audits/predictive-intelligence/phase_02/probes/check_candidates_negative.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv` (32 of 32 mutations refused, including the skeptic's counterexample).

## Tests

- Entry gate at `a402df6`: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 139.97s (0:02:19)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- After the first pass: `1 failed, 858 passed in 135.93s (0:02:15)`; orchestrator's rerun on `498eaa0`: `1 failed, 858 passed in 136.62s`.
- After repair pass 2: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 134.21s (0:02:14)`, only the known clock test; strays `data/reports/20261024_0424_BRETT_0x532f.md`, sqlite shm and wal removed by hand; DB sha256 `068287c0...a6679ca` unchanged.
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; removed by hand; tracked DB sha256 `068287c0...a6679ca` unchanged.

## Blockers and open items

- None blocking Phase 03.
- GitHub issue pages (the MiroFish FAQ, issue 726) and model-weight license files on Hugging Face were not readable from this session; Phase 03 needs another route (WebSearch, or Firecrawl within the cap).
- Returned names not selected for verification remain unscreened (count and term scan in EXCLUSIONS.md); Phase 03 may pull any with a recorded reason.
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for Phase 03. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, or a merge into `main` need Elving (PI-D-005).

## Next

Next eligible phase: 03 (pinned source audit, rubric and ranked top ten), after the orchestrator verifies repair pass 2.

## Commit

- `498eaa0` content; the repair pass 2 commit, message prefix `predictive-intel phase 02: `, is HEAD (read its hash with `git log -1`; this file is part of it). No hash-only commits.
- `git diff --name-only a402df6..HEAD` lists only files under `audits/predictive-intelligence/` and `docs/predictive-intelligence/`.
- Not pushed. `git status` clean after the commit.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -3 --oneline && python3 audits/predictive-intelligence/phase_02/probes/check_candidates.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv && python -m pytest tests -q
```

Expect the repair pass 2 commit on top of `498eaa0`, `problems 0` and `1 failed, 858 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.

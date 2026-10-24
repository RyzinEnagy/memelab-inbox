# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 02 evidence: `audits/predictive-intelligence/phase_02/` (PHASE_02_EVIDENCE.md, PHASE_02_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, research/, probes/). Phases 00 and 01 evidence stays in `phase_00/` and `phase_01/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase completed: 02 (independent predictive GitHub discovery), 2026-10-24. Status NEEDS_REVIEW: every gate item is reproduced by the phase agent; the orchestrator's independent skeptic (PI-D-013) has not run. It becomes PASS only after that review is folded in as a repair pass.
- Branch `feature/predictive-intelligence`, one content commit on top of `a402df6` (see "Commit"). No production code: nothing under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed. Not pushed (PI-D-003). Spend 0 credits.

## What Phase 02 found

- The GitHub search API, repository REST endpoints and github.com HTML pages answer HTTP 403 from the session proxy (policy, not quota). Discovery used the package keyword index (packages.ecosyste.ms), documentation and paper links, WebSearch and PyPI cross-links; facts came from `git ls-remote` pins, blob-less clones at the pin, treeless clones (root commits) and repos.ecosyste.ms metadata (PI-D-023).
- Needs frozen first in `research/NEEDS.csv` (N01 to N14, mapped to GAP_MATRIX cells). Corpus: 60 distinct successful queries over 9 families and 5 mechanisms, plus 22 refused GitHub searches (`research/SEARCH_LOG.md`).
- `research/CANDIDATES.csv`: 107 verified candidates (106 unique root histories; aeon is a hard fork of sktime), each with pin, observed time, commit date, license from the file at the pin, flags, needs, gap cells and discovery provenance. `research/SHORTLIST.csv`: 29 for Phase 03 (tabular 5, time series 4, calibration 5, online and drift 4, behavioral 4 with MiroFish, OASIS, Mesa and black-it, experiment audit 4, event-time labels 3), each with code paths and symbols verified at the pin and the question Phase 03 must answer. No score or rank (PI-D-024).
- `research/EXCLUSIONS.md`: renamed paths (8 seed or linked paths now serve another repository's HEAD), 2 vanished repositories (seed AgentPy/agentpy; successor JoelForamitti/agentpy), 8 forks and mirrors, crawler tooling (Firecrawl, Crawl4AI, Maxun), 2 README-only repositories (P42), non-matching or archived seeds (causalml, dowhy, EconML, autogen), and the reason each candidate is not shortlisted.
- Flags for Phases 03 and 04: AGPL (MiroFish, black-it, AgentTorch, deepchecks), GPL (scikit-survival, SurvivalEVAL, ondil, freqtrade, backtrader), LGPL (TorchCP), BUSL (alibi-detect), Commons Clause (vectorbt), non-commercial weights (TabPFN 2.5 and later, TimesFM 3.0). MiroFish needs LLM and Zep Cloud keys and Python below 3.13 and has no probability output; OASIS needs Python below 3.12 and neo4j.

## How to check it

- `python3 audits/predictive-intelligence/phase_02/probes/check_candidates.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv` (offline, `problems 0`); add `--live 10 --seed <n>` to re-fetch pins and re-read the shortlisted code evidence.
- `python3 audits/predictive-intelligence/phase_02/probes/check_candidates_negative.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv` (25 of 25 mutations refused).

## Tests

- Entry gate at `a402df6`: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 139.97s (0:02:19)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- Final: `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 135.93s (0:02:15)`, same single known failure.
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; removed by hand; tracked DB sha256 `068287c0...a6679ca` unchanged.

## Blockers and open items

- None blocking the skeptic review. Phase 03 starts only after the orchestrator marks Phase 02 PASS.
- The MiroFish maintainer FAQ (issue 726) and any GitHub issue or release page are behind the same 403; Phase 03 needs another route (WebSearch, or Firecrawl within the cap) to read them.
- Model-weight license files (TabPFN, TimesFM, Chronos, TabICL) live on Hugging Face and were not read.
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for the skeptic review or Phase 03. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, or a merge into `main` need Elving (PI-D-005).

## Next

Orchestrator: run the independent skeptic on Phase 02 (`audits/predictive-intelligence/phase_02/SKEPTIC_PACKET.md`), then return the review for a repair pass. Next eligible phase after a PASS: 03 (pinned source audit, rubric and ranked top ten).

## Commit

- One content commit on top of `a402df6`, message prefix `predictive-intel phase 02: `. It is HEAD (read its hash with `git log -1`; this file is part of it).
- `git diff --name-only a402df6..HEAD` lists only files under `audits/predictive-intelligence/` and `docs/predictive-intelligence/`.
- Not pushed. `git status` clean after the commit.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -2 --oneline && python3 audits/predictive-intelligence/phase_02/probes/check_candidates.py audits/predictive-intelligence/phase_02 audits/predictive-intelligence/phase_01/architecture/GAP_MATRIX.csv && python -m pytest tests -q
```

Expect the Phase 02 commit on top of `a402df6`, `problems 0` and `1 failed, 858 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.

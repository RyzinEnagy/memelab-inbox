# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md).

## Position

- Current phase completed: 00 (repo audit and execution contract), 2026-10-10.
- Next phase: 01 (baseline hygiene: test isolation and clock). See ROADMAP.md.
- Active branch: `feature/social-intelligence`, created from `main` at `48fe2900fa2e8643e592365a558fa0d469551e41`.
- Latest commit: the head of `origin/feature/social-intelligence`. Phase 00 was pushed on 2026-10-10 through the GitHub web UI as five commits whose messages start `social-intel phase 00:` (one per doc), with Elving's approval (D-008). Confirm with `git log -5 origin/feature/social-intelligence`.

## Verified this phase

- Read and checked against code: README.md, docs/ARCHITECTURE.md, docs/SOURCES.md, skills/memecoin-scout/SKILL.md, memelab/db.py, normalize.py, pipeline.py, report.py, cli.py, state.py, wallet.py, memelab/bridge/, launch/social.py, catalyst/attention.py, catalyst/sources.py, m19_attention_analysis.py, .gitignore, commit_file.py, bootstrap.sh.
- No code changed. Only files added: docs/social-intelligence/EXECUTION.md, ROADMAP.md, DECISIONS.md, HANDOFF.md, AUDIT_00.md.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest`; numpy required).
- Outcome at Phase 00: exit 1, `1 failed, 63 passed`. The failure is pre-existing and clock dependent: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (passes with the clock set to 2026-10-07).
- Side effect: the suite writes `data/reports/<stamp>_BRETT_0x532f.md`; delete it after each run until Phase 01 fixes it.
- Smoke: `python -m memelab --help` exit 0; `python -m memelab social-note --help` exit 0.

## Blockers and open decisions

- D-004 (what social content may be stored, and where) needs Elving's approval before Phase 02.
- D-006 (no signed-in social scraping) needs Elving's decision before Phase 06.
- The cloud session still has no working GitHub credential. Pushes so far go through the GitHub web UI in Elving's signed-in Chrome (D-008). Each later push of non-data files needs Elving's approval in that session.
- Phase prompts 01 to 21 were not supplied; ROADMAP.md entries for them are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest && python -m pytest tests -q
```

Then start Phase 01 per ROADMAP.md.

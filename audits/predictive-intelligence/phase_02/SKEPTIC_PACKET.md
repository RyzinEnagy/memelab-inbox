# Phase 02 skeptic packet

For the independent reviewer the orchestrator starts (PI-D-013). This packet lists what to test and how to reproduce it. It holds no conclusions; the phase's claims are in the files below and are claims to falsify.

## Task

Phase 02 of the package ("Find a broad, verifiable, diversified landscape of prediction tools"): at least 12 distinct queries over at least 6 non-overlapping topic families, at least 45 unique verified GitHub repositories with pinned SHAs and real provenance (no forks or mirrors as padding, a 404 or rename is a finding), a shortlist of at least 20 for Phase 03 with at least 3 per high-priority family (tabular probability, time series, calibration and uncertainty, online and drift, behavioral multi-agent including 666ghj/MiroFish and camel-ai/oasis, experiment audit and evaluation), exclusions with reasons, five provenance rows re-run, a P42 test (a README-only claim earns nothing), MiroFish treated as behavioral simulation. Relevance is decided by the needs frozen from Phase 01, not by popularity. No production code.

Read first: `/home/claude/pi_orchestration/PHASE_BRIEF.md`, the package `phases/PHASE_02_independent_predictive_github_discovery.md`, `EXECUTION_RULES.md`, references `RESEARCH_PROTOCOL.md`, `GRADING_RUBRIC.md`, `CANDIDATE_SEEDS.md`, `RESEARCH_TOOLING.md`, `MIROFISH_EVALUATION.md`, `ADVERSARIAL_SCENARIOS.md`, and `docs/predictive-intelligence/DECISIONS.md` (PI-D-001 to PI-D-024).

## Artifacts (all under `audits/predictive-intelligence/phase_02/`)

| Path | What it is |
|---|---|
| `ACCEPTANCE_CHECKLIST.md` | checklist C1 to C20, written before the first query |
| `research/NEEDS.csv` | frozen needs N01 to N14 with GAP_MATRIX cells |
| `research/QUERIES.json` | the query corpus as run (GitHub search section, keyword index, docs, papers) |
| `research/QUERY_RESULTS.jsonl` | one record per discovery call (time, status, body sha256, returned repositories); WebSearch records carry the result URLs |
| `research/PYPI_LOOKUPS.jsonl` | 98 PyPI JSON lookups |
| `research/VERIFY_RESULTS.jsonl` | 141 verified inputs (ls-remote pin, ecosyste.ms metadata, blob-less clone facts, license files) |
| `research/ROOT_COMMITS.jsonl` | root commits of the 107 candidates |
| `research/MIRROR_CHECKS.jsonl`, `research/EXTRA_PINS.jsonl` | forks, mirrors and renamed paths met in the search |
| `research/CANDIDATE_ANNOTATIONS.csv`, `research/SHORTLIST_ANNOTATIONS.csv`, `research/SPECIAL_FLAGS.json` | hand-written inputs (family, role, needs, code evidence, flags with file:line sources) |
| `research/CANDIDATES.csv`, `research/SHORTLIST.csv` | built by `probes/build_candidates.py` |
| `research/EXCLUSIONS.md`, `research/SEARCH_LOG.md` | built by `probes/render_exclusions.py` and `probes/render_search_log.py` |
| `research/PROVENANCE_AUDIT.json`, `research/PROVENANCE_AUDIT_RERUN.jsonl` | seeded draw of five discovery rows and their re-run |
| `research/LIVE_CHECK.txt` | output of the checker's live mode |
| `PHASE_02_EVIDENCE.md`, `PHASE_02_RESULTS.json` | evidence and results |

## Code paths

`probes/gh_search.py`, `probes/discover.py`, `probes/pypi_lookup.py`, `probes/verify_repos.py` (license classifier `classify_license`), `probes/root_commits.py`, `probes/build_candidates.py`, `probes/render_exclusions.py`, `probes/render_search_log.py`, `probes/check_candidates.py`, `probes/check_candidates_negative.py`.

## Commands to reproduce

Run in your own clone (never inside `/home/claude/memelab-inbox`):

```
rm -rf /home/claude/pi_orchestration/skeptic_02; git clone -q /home/claude/memelab-inbox /home/claude/pi_orchestration/skeptic_02
cd /home/claude/pi_orchestration/skeptic_02 && git checkout -q feature/predictive-intelligence
cd audits/predictive-intelligence/phase_02
python3 probes/check_candidates.py . ../phase_01/architecture/GAP_MATRIX.csv                 # offline gate checks
python3 probes/check_candidates_negative.py . ../phase_01/architecture/GAP_MATRIX.csv        # 25 mutations
python3 probes/check_candidates.py . ../phase_01/architecture/GAP_MATRIX.csv --live 10 --seed <your seed>   # re-fetch pins and code evidence
sha256sum research/NEEDS.csv                                                                  # compare with the value in ACCEPTANCE_CHECKLIST.md and SEARCH_LOG.md
git ls-remote https://github.com/<owner>/<name> HEAD                                          # any row
python3 probes/discover.py research/QUERIES.json <scratch>/raw <scratch>/rerun.jsonl K05 D01 --tag _skeptic   # re-run any keyword, docs or paper query
cd /home/claude/pi_orchestration/skeptic_02 && python -m pytest tests -q                       # full suite, temp MEMELAB_DB
```

Rebuilding CANDIDATES.csv needs blob-less clones at the pins under a folder of your choice (`probes/verify_repos.py <list> <out> <raw> <clone_root>` then `probes/build_candidates.py . <clone_root> <package dir>`); Phase 02 deleted its own clones after recording what it read.

## Things worth attacking

- Whether any counted candidate is a fork, mirror, renamed duplicate or vanished repository, and whether the ecosyste.ms mirror (used because the GitHub API answered 403) can be wrong about forks; the four candidates it has no record of.
- Whether discovery provenance is real: pick rows, re-run their queries, and check chained credits (`W22>PYPI:pandera`, `W18>mohala562/abides`).
- Whether a license in CANDIDATES.csv differs from the actual license (root file only, REUSE folder, mixed or per-file licensing, weights terms on Hugging Face).
- Whether any shortlisted row rests on README text, or whether its code evidence symbol does not do what the role says.
- Whether the frozen needs were bent to fit famous repositories, whether the shortlist leans on seeds, and whether a family's three entries are real or token.
- Whether MiroFish is anywhere treated as forecasting evidence.
- Whether anything was written under `memelab/`, `tests/`, `inbox/`, `state/` or `data/`, or any billable call was made.
- A new wrong-but-plausible counterexample that none of the checks above catch.

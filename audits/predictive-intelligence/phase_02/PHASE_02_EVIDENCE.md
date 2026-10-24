# Phase 02 evidence: independent predictive GitHub discovery

| Item | Value |
|---|---|
| Phase | 02, "Find a broad, verifiable, diversified landscape of prediction tools" |
| Status | NEEDS_REVIEW: every gate item below is reproduced by the phase agent; the independent skeptic (PI-D-013) has not run yet. The phase can become PASS only after the orchestrator's skeptic review is folded in |
| Branch | `feature/predictive-intelligence` |
| HEAD before | `a402df67bd1e23227d06baa2e0b4fbdbe494e905` (Phase 01 repair pass 2, pushed) |
| Commit | one content commit on top of `a402df6` (read its hash with `git log -1`; this file is part of it) |
| Time (UTC) | 2026-10-24T02:50Z (entry suite) to 03:45Z |
| Spend | 0 Firecrawl credits; free calls only (counts below; COST_LEDGER.md) |
| Package | 41 of 41 files OK against SHA256SUMS.txt |

## Inputs read

Brief `/home/claude/pi_orchestration/PHASE_BRIEF.md` and `SKEPTIC_BRIEF.md`. Package: START_HERE.md, EXECUTION_RULES.md, PHASE_INDEX.md, ORCHESTRATOR.md, `phases/PHASE_02_independent_predictive_github_discovery.md`, references RESEARCH_PROTOCOL.md, GRADING_RUBRIC.md, CANDIDATE_SEEDS.md, RESEARCH_SOURCES.md, RESEARCH_TOOLING.md, MIROFISH_EVALUATION.md, ADVERSARIAL_SCENARIOS.md, DATA_TIME_CONTRACT.md, SCIENTIFIC_VALIDATION.md. Records: docs/predictive-intelligence/{HANDOFF, EXECUTION, DECISIONS, ROADMAP}.md, COST_LEDGER.md; Phase 01 architecture TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, PLANNED_SEAMS.md, GAP_MATRIX.csv, DEPENDENCY_GRAPH.md; Phase 01 evidence and results for format.

## Acceptance checklist results

Checklist written at 2026-10-24T02:55Z, before the first query (02:56:45Z): `ACCEPTANCE_CHECKLIST.md`.

| Id | Result | Evidence |
|---|---|---|
| C1 | met | `sha256sum -c SHA256SUMS.txt`: 41 OK, no other line |
| C2 | met | entry suite `1 failed, 858 passed in 139.97s (0:02:19)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; checkout clean at `a402df6` |
| C3 | met | `research/NEEDS.csv` sha256 `90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e` at 02:55:41Z, unchanged since (the checker pins it); 14 needs, every cell MISSING, PARTIAL or CONFLICT in GAP_MATRIX.csv |
| C4 | met | 60 distinct successful queries over 9 families and 5 mechanisms (keyword index 14, documentation 6, papers 12, WebSearch 28, PyPI 98 lookups); 22 GitHub search attempts refused (HTTP 403, logged); `research/SEARCH_LOG.md`, `QUERY_RESULTS.jsonl` |
| C5 | met | 107 candidates, 106 unique root histories (aeon is a hard fork of sktime, flagged); 141 verified inputs, clone HEAD equal to pin for all 139 reachable; `check_candidates.py` 0 problems |
| C6 | met | license from the file at the pin for all 107 (sha256 per file; puncc from its REUSE `LICENSES/` folder); flags: AGPL 4, GPL 5, LGPL 1, BUSL 1, Commons Clause 1, non-commercial weights 2 (README notices); GPU, LLM, memory-service and server dependencies from pinned dependency files and PyPI base requirements, with sources |
| C7 | met | every candidate names needs; the checker validates every need cell against GAP_MATRIX.csv |
| C8 | met | 29 shortlisted, no score or rank; families: tabular 5, time series 4, calibration 5, online and drift 4, behavioral 4 (MiroFish, OASIS, Mesa, black-it), experiment audit 4, event-time labels 3; every row has code evidence (path, blob, line) re-read from a fresh fetch at the pin (`research/LIVE_CHECK.txt`) |
| C9 | met | `research/EXCLUSIONS.md`: 38 screened exclusions (A to F) and 78 not-shortlisted reasons (G); the checker shows every verified input is covered |
| C10 | met | five rows drawn with seed 20261024 from 114 pairs; all reappeared on re-run (`PROVENANCE_AUDIT.json`) |
| C11 | met | `check_candidates_negative.py`: 25 of 25 mutations refused, unmutated copy passes |
| C12 | met | TheSenseAI/SenseAI and Cooktrenches/Scan-Scam-AI-v1, both found by WebSearch W09, excluded as README_ONLY_CLAIM with file-level reasons |
| C13 | met | MiroFish row: AGPL-3.0 (LICENSE and backend/pyproject.toml:6), LLM and Zep Cloud keys required (backend/app/config.py), Python >=3.11,<3.13, no probability output in the backend; shortlisted as a behavioral scenario generator only |
| C14 | met | firecrawl/firecrawl (and its old path), unclecode/crawl4ai, getmaxun/maxun pinned and listed as tooling; the checker refuses them as candidates |
| C15 | met | see "Tests and tracked data" below |
| C16 | met | COST_LEDGER.md row for Phase 02: 0 credits; free calls counted below |
| C17 | met | all clones under `/home/claude/pi_research/` deleted at 2026-10-24T03:37:31Z after the build (42 MB); pins kept; raw API bodies kept outside the repo (140 MB, `/home/claude/pi_orchestration/phase02/raw/`) |
| C18 | met | this file, PHASE_02_RESULTS.json, SKEPTIC_PACKET.md, ROADMAP row, DECISIONS PI-D-023 and PI-D-024, HANDOFF rewritten; status NEEDS_REVIEW |
| C19 | met | style scan, see below |
| C20 | met | one content commit |

## Commands and exits

| # | Check | Command | Exit | Result |
|---|---|---|---:|---|
| 1 | Package checksums | `sha256sum -c SHA256SUMS.txt \| grep -v ': OK'` | 1 (no non-OK line) | 41 OK |
| 2 | Entry gate | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` (started 02:50Z) | 1 | `1 failed, 858 passed in 139.97s (0:02:19)`; only the known clock test |
| 3 | Strays after entry suite | `git status --porcelain --ignored` | 0 | `data/reports/20261024_0250_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; removed by hand; `data/memelab.sqlite` sha256 `068287c0...a6679ca` unchanged |
| 4 | GitHub search | `python3 probes/gh_search.py research/QUERIES.json <raw> research/QUERY_RESULTS.jsonl` (02:56:45Z to 02:59:18Z) | 0 | 22 of 22 HTTP 403 "sessions are bound to their configured repositories"; not retried |
| 5 | GitHub REST and HTML probes | `curl https://api.github.com/repos/scikit-learn-contrib/MAPIE`, `https://github.com/topics/conformal-prediction`, `https://github.com/search?...`, `https://codeload.github.com/...` | 0 | 403 each; `api.github.com/rate_limit` 200 showing a proxy-injected credential (core 15000, search 30) |
| 6 | Keyword index, documentation, papers | `python3 probes/discover.py research/QUERIES.json <raw> research/QUERY_RESULTS.jsonl` (03:02:31Z to 03:04:18Z; A08 to A12 at 03:05:28Z to 03:05:37Z) | 0 | 46 calls, all HTTP 200 |
| 7 | WebSearch | Claude WebSearch tool, 28 queries in three batches (03:04:20Z to 03:05:28Z, 03:05:38Z to 03:06:40Z, 03:25:21Z to 03:27:22Z) | n/a | result URLs recorded verbatim in QUERY_RESULTS.jsonl W01 to W28 |
| 8 | PyPI | `python3 probes/pypi_lookup.py research/PYPI_LOOKUPS.jsonl <raw>/pypi <names>` (two runs) | 0 | 98 lookups, all HTTP 200 |
| 9 | Verification, first run | `python3 probes/verify_repos.py <36 seeds> ...` (03:08Z) | 0 | superseded: the license classifier read GPL-3.0 texts as AGPL and non-commercial (iteration log); output kept outside the repo as `verify_batch1_classifier_v1.jsonl` |
| 10 | Verification | `python3 probes/verify_repos.py repos_all.txt research/VERIFY_RESULTS.jsonl <raw>/eco /home/claude/pi_research --workers 6` (03:12:17Z to about 03:13:30Z) | 0 | 141 inputs: 139 VERIFIED (clone HEAD = pin), 2 VANISHED_OR_PRIVATE |
| 11 | Mirror and fork roots (screening tests) | `git clone --bare --filter=tree:0` of 7 repositories, `git rev-list --max-parents=0 HEAD` (03:14:13Z to 03:14:17Z) | 0 | shared roots recorded in MIRROR_CHECKS.jsonl |
| 12 | Root commits of candidates | `python3 probes/root_commits.py candidates_canonical.txt research/ROOT_COMMITS.jsonl <work> --workers 6` | 0 | 107 of 107 cloned; one shared root (sktime, aeon) |
| 13 | Rename checks | `git ls-remote https://github.com/<old and new path> HEAD` for shap, tpot, firecrawl (03:25:19Z to 03:25:21Z) and pandera (03:27:22Z to 03:27:23Z) | 0 | identical HEADs at both paths (EXTRA_PINS.jsonl) |
| 14 | Build | `python3 probes/build_candidates.py . /home/claude/pi_research <package>` | 0 | `candidates 107 shortlist 29`; no code evidence problem |
| 15 | Renders | `python3 probes/render_exclusions.py .`; `python3 probes/render_search_log.py .` | 0, 0 | `excluded screened 38 not shortlisted 78`; `rows 96 distinct ok queries 60 families 9` |
| 16 | Provenance audit | seeded draw, then `python3 probes/discover.py ... K02 K07 K08 K12 --tag _audit` (03:29:31Z to 03:29:47Z) and the W01 WebSearch re-run (03:29:48Z to 03:30:04Z) | 0 | 5 of 5 reappeared, same ranks, byte-identical keyword-index bodies |
| 17 | Checker, offline | `python3 probes/check_candidates.py . ../phase_01/architecture/GAP_MATRIX.csv` | 0 | `problems 0` |
| 18 | Checker, negative tests | `python3 probes/check_candidates_negative.py . ../phase_01/architecture/GAP_MATRIX.csv` | 0 | unmutated copy passes; `cases 25 not caught 0` |
| 19 | Checker, live | `python3 probes/check_candidates.py . ../phase_01/architecture/GAP_MATRIX.csv --live 10 --seed 20261024` (03:36Z to 03:37:24Z) | 0 | 36 pinned commits fetched into empty repositories; 29 shortlisted code evidence items re-read and matched; mlflow/mlflow HEAD moved since the pin (pin still fetchable); `problems 0` |
| 20 | Clean-up | `rm -rf /home/claude/pi_research/*__* /home/claude/pi_research/_roots` (03:37:31Z) | 0 | clones removed |
| 21 | Content guard with new files staged | `python -m pytest tests/test_content_guard.py tests/test_release_tools.py tests/test_predictive_contract.py tests/test_predictive_decisions.py -q -p no:cacheprovider` | 0 | `90 passed in 6.63s` |
| 22 | Final full suite | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` | see "Tests and tracked data" | |

## Tests and tracked data

Final suite: `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` started 2026-10-24T03:38:39Z, exit 1, `1 failed, 858 passed in 135.93s (0:02:15)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known). Strays afterwards: `data/reports/20261024_0338_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`, removed by hand; `data/memelab.sqlite` sha256 `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca` unchanged; `git diff --name-only a402df6 -- inbox state data memelab tests` empty.

`git diff --name-only a402df6 --cached` lists only files under `audits/predictive-intelligence/` and `docs/predictive-intelligence/`; nothing under `memelab/`, `tests/`, `inbox/`, `state/` or `data/`.

## Environment findings

1. The GitHub search API, repository REST endpoints for repositories not attached to the session and github.com HTML pages answer HTTP 403 from the session proxy (`"This GitHub API path is not available: sessions are bound to their configured repositories..."` and `"GitHub access to this repository is not enabled for this session..."`). The proxy injects its own GitHub credential (`GH_TOKEN=proxy-injected`; `rate_limit` reports core 15000 and search 30), so the brief's "unauthenticated, about 60 an hour" did not apply. Policy denials were not retried; no credential was read or handled. Recorded as PI-D-023 with the replacement route.
2. `git ls-remote` and blob-less clones of public repositories work. A renamed repository answers at its old path with the new repository's HEAD and no redirect message, so renames were detected by identical HEADs plus a 404 for the old path at ecosyste.ms plus the package's own source link.
3. repos.ecosyste.ms has no record for four candidates (pandera-dev/pandera, JoelForamitti/agentpy, quantscious/finmlkit, TheClimateCorporation/properscoring); their canonical status rests on their PyPI source links and on the root-commit check.

## Results

- 107 candidates over 9 families (calibration 17, time series 17, tabular 14, behavioral 14, online and drift 12, experiment audit 12, event-time labels 9, on-chain and financial 9, social narrative 3). 89 are credited to corpus queries beyond the seed list and analyst-named PyPI lookups; 32 come from the seed list.
- Shortlist 29 (11 seeds, 18 found by the corpus), each with code evidence at the pin and the uncertainty Phase 03 must resolve.
- Findings: 8 seed or linked paths now serve another repository's HEAD (microsoft/LightGBM to lightgbm-org/LightGBM, microsoft/interpret to interpretml/interpret, projectmesa/mesa to mesa/mesa, automl/TabPFN to PriorLabs/TabPFN, and four more in EXCLUSIONS.md A); the seed AgentPy/agentpy and the PyPI-linked Yosri-Ben-Halima/cpcv are unreachable; 8 forks or mirrors met in search results (ABIDES, OASIS, TimesFM, Graphiti copies); microsoft/autogen's README says it is archived while ecosyste.ms does not; alibi-detect is under the Business Source License; TabPFN 2.5 and later and TimesFM 3.0 weights are non-commercial; MiroFish needs LLM and Zep Cloud keys and Python below 3.13; OASIS needs Python below 3.12 and neo4j.
- No public code found for the three Solana rug-pull papers met in search (EXCLUSIONS.md).

## Sources (links)

- Keyword index: `https://packages.ecosyste.ms/api/v1/keywords/<keyword>?per_page=100&page=<1|2>`; repository metadata: `https://repos.ecosyste.ms/api/v1/hosts/GitHub/repositories/<owner>%2F<name>`.
- PyPI: `https://pypi.org/pypi/<name>/json`.
- Documentation: `https://scikit-learn.org/stable/related_projects.html`, `https://raw.githubusercontent.com/{valeman/awesome-conformal-prediction, 666ghj/MiroFish, camel-ai/oasis, wilsonfreitas/awesome-quant, online-ml/river}/HEAD/README.md`.
- Papers: `https://arxiv.org/abs/{2411.11581, 2403.07815, 1904.12066, 2207.12274, 2207.01848, 2310.10688, 2304.03442, 2608.20271, 2504.07132, 2603.24625, 2412.19498, 2602.11139}`; `https://arxiv.org/html/{2608.20271, 2504.07132}`.
- Repositories: `https://github.com/<owner>/<name>` at the pins in CANDIDATES.csv.
- WebSearch result URLs: QUERY_RESULTS.jsonl records W01 to W28.

## Free calls (no cost)

| Kind | Count |
|---|---:|
| GitHub search API attempts (403) | 23 (22 corpus, 1 diagnosis) |
| Other GitHub REST or HTML probes (403 or 401) | 5 REST or HTML, 6 smart-HTTP `info/refs` probes (5 HTTP 200, 1 HTTP 401 for AgentPy/agentpy) |
| GitHub `rate_limit` | 1 |
| raw.githubusercontent.com | 6 (5 documentation pages, 1 HTTP 404 probe) plus 3 reads of the TabICL LICENSE at its pin |
| `git ls-remote` | about 270 (verification 177, rename checks 13, live checks 72, misc) |
| Blob-less shallow clones or fetches | 174 clones (35 in the superseded first run) plus 72 live fetches |
| Treeless clones | 114 |
| repos.ecosyste.ms | 174 repository lookups, 8 lookup-endpoint calls, about 12 topic and schema calls |
| packages.ecosyste.ms | 28 corpus, 8 audit re-runs, 4 sort tests, 1 schema |
| PyPI | 98 lookups, 2 diagnosis calls |
| arXiv | 12 abstract pages, 2 HTML pages |
| deps.dev, OpenSSF scorecard, gitlab.com API | 1 each (reachability checks during diagnosis) |
| WebSearch | 29 (28 corpus, 1 audit re-run) |
| WebFetch, Firecrawl | 0 |

## Iteration log (passes within the five-pass limit)

1. Pass 1, discovery. GitHub search returned 403 for every query. Inspected the proxy status and the 403 bodies (policy, not quota), did not retry, and extended the corpus with the package keyword index, documentation, paper links, WebSearch and PyPI cross-links (QUERIES.json note). The ecosyste.ms topic endpoint returned empty topics for every topic tried and was dropped.
2. Pass 2, verification. The first verification run labeled GPL-3.0 texts (backtrader, freqtrade) as AGPL-3.0 and flagged MiroFish, backtrader and freqtrade as non-commercial: the GPL v3 text names the GNU Affero license in section 13 and says "noncommercially" in section 6. Fixed `classify_license` (title-only GPL family detection, word-bounded non-commercial match outside GPL texts), tested on the cloned files (backtrader GPL-3.0, freqtrade GPL-3.0, MiroFish AGPL-3.0, alibi-detect BUSL-1.1), and re-ran the full verification. Also found that git follows renames silently; added the same-HEAD rule and root-commit checks.
3. Pass 3, provenance. abides-sim/abides had no direct credit (only forks were returned) and 20 candidates were credited only by seeds or analyst-named PyPI lookups. Added explicit chained credits (fork found by a query, PyPI page or readthedocs site in a WebSearch result, marked with `>`) and 8 more WebSearch queries (W21 to W28); 18 candidates remain credited only by seeds or analyst-named PyPI lookups, stated in SEARCH_LOG.md. puncc's license sits in a REUSE `LICENSES/` folder; the build now reads it.
4. Pass 4, own adversarial pass (not independent, below): cross-checked file licenses against PyPI declarations (no conflict; 5 packages declare none) and found bashtage/arch's MIT label is NCSA wording and TabICL's PRIOR-LABS-TERMS label is a copyright line for vendored Apache code; both recorded as special flags with file lines. Re-ran build, checker, negative tests and the live check.

## Own adversarial pass (not independent)

| Attack | Result |
|---|---|
| Fork or mirror counted as a candidate | ecosyste.ms fork flags (103 of 107 known, all false), identical-HEAD rule, root commits for all 107: one shared root (aeon, flagged and not shortlisted). Residual: the four candidates without an ecosyste.ms record could be forks of a repository outside the set; their PyPI packages name them as the source |
| Seed anchoring (famous repos rewrite the goal) | needs frozen first; 18 of 29 shortlisted are not seeds; seeds causalml, dowhy, autogen excluded for need mismatch or archival; the shortlist includes small projects (venn-abers, model-diagnostics, hazardous, purged-cross-validation, black-it) |
| README-only credit (P42) | two real repositories excluded with file-level reasons; checker refuses README or docs paths as code evidence and undefined symbols; MiroFish claims not credited |
| License wrong | file text at the pin, PyPI cross-check, special flags with lines. Residual: per-file license headers and vendored code inside a permissive repository are not scanned; model-weight licenses live on Hugging Face |
| Fabricated or stale verification data | the live mode re-fetches pinned commits and re-reads code evidence from fresh fetches; any seed can be used |
| Python 3.13 support overstated | `py313_declared_on_pypi` is what PyPI declares; a pure-Python sdist without classifiers may still run, a declared package may still fail; Phase 04 installs in a venv |
| Tracked data or code touched | diff limited to the two predictive namespaces |

Own counterexample (not independent): a repository whose root LICENSE is MIT but whose core module carries an AGPL header (vendored code), or whose license changed after the pin. The checker would accept it, and the PyPI cross-check only catches it when PyPI declares the other license. Phase 03's LICENSE_AND_SECURITY_GATE must scan per-file headers and the dependency tree of each shortlisted repository at its pin. The independent skeptic's counterexample will be recorded here after the orchestrator's review.

## Artifact sha256

Hashes at the time of the commit (PHASE_02_RESULTS.json holds this file's hash).

| Path | sha256 |
|---|---|
| `audits/predictive-intelligence/phase_02/ACCEPTANCE_CHECKLIST.md` | `5009779aee21891c1aff6bd1f44c64363321e5420caa3ed82ad2ea81d135f6f0` |
| `audits/predictive-intelligence/phase_02/SKEPTIC_PACKET.md` | `c3d02ebc57888a21043f3d0b29dad0bd03bfa21164d3e0fdd4e1af79b9ce4581` |
| `audits/predictive-intelligence/phase_02/probes/build_candidates.py` | `1728c5f7e7cd908cd98033435c25e89a36019c23ad81342a5a726faa8a16eaa1` |
| `audits/predictive-intelligence/phase_02/probes/check_candidates.py` | `025a5a0b536c7df470e61edfc632833676bd7202b2e785af7dbabf5f029ec553` |
| `audits/predictive-intelligence/phase_02/probes/check_candidates_negative.py` | `04522ed1e7703820020cc1c410f46fb33d29e37995870f47612ec663d1d21b8d` |
| `audits/predictive-intelligence/phase_02/probes/discover.py` | `558a202481d2c265687de741ae49bff06208d072092769b3d56a6471101eec99` |
| `audits/predictive-intelligence/phase_02/probes/gh_search.py` | `658c482bf259cae5d7f001a0974c0b7923df1912ecc529e8aab00d94bdf185cf` |
| `audits/predictive-intelligence/phase_02/probes/pypi_lookup.py` | `e5b1e1b7899f710149e28e02f07e0ecf71f0ce6eb82f49b8bfa1144d7f5624ff` |
| `audits/predictive-intelligence/phase_02/probes/render_exclusions.py` | `440f31ea6dbf804a46d630af7afcc01704dc633d6bc309345cc5f42074660273` |
| `audits/predictive-intelligence/phase_02/probes/render_search_log.py` | `be04e3e5622fac9dab666a500e7e4f69285fd1796cde2bdd9a07485e327bef0f` |
| `audits/predictive-intelligence/phase_02/probes/root_commits.py` | `b10cf30dd7c3b137f333fd43638fa2696633303a21ba29a74906ac2f69c75e30` |
| `audits/predictive-intelligence/phase_02/probes/verify_repos.py` | `fe0cfe81f4f7d952227502e47fd0540c80986ad6ab713f33588eed13ba54e339` |
| `audits/predictive-intelligence/phase_02/research/CANDIDATES.csv` | `b2640313cb7bf18b4de2c60086074277a0195877e894800f508b6e717c453d0e` |
| `audits/predictive-intelligence/phase_02/research/CANDIDATE_ANNOTATIONS.csv` | `2640cb3eef0ddcd01c113f12450d65f2ea293d60a7c2c56fea8a99df075aaa33` |
| `audits/predictive-intelligence/phase_02/research/EXCLUSIONS.md` | `30ec0ace07e445917c897e33392887640ab5f01741f4f0f0bc75dd983d2bff4a` |
| `audits/predictive-intelligence/phase_02/research/EXTRA_PINS.jsonl` | `91b6ac208401442733bfbbb7288823a06571a18efbbdfd1a3704cd269fdb3a38` |
| `audits/predictive-intelligence/phase_02/research/LIVE_CHECK.txt` | `e3e06a591875a93a575ded20c20246d3c469446e6a8f80d741146c6926345a73` |
| `audits/predictive-intelligence/phase_02/research/MIRROR_CHECKS.jsonl` | `c34ae49e3a5553ef0467e6c2df8df156d64709b5b93eb7eb990d33c402a66b98` |
| `audits/predictive-intelligence/phase_02/research/NEEDS.csv` | `90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e` |
| `audits/predictive-intelligence/phase_02/research/PROVENANCE_AUDIT.json` | `83714765982a3984bdd6df26924f2157af381fb232c4f3d6989d046753839fcd` |
| `audits/predictive-intelligence/phase_02/research/PROVENANCE_AUDIT_RERUN.jsonl` | `b7b2c1801bb5b8b7262078a0e46400fb7f79b21a82188d7caf4d080f32d174c8` |
| `audits/predictive-intelligence/phase_02/research/PYPI_LOOKUPS.jsonl` | `01e3b8e29ff55063f93fc9f953133182f3011b632551a19bb1419a0dfaec4989` |
| `audits/predictive-intelligence/phase_02/research/QUERIES.json` | `b4143434c91b813228e4f5f7310c8e60bc1c0eba0e59e668075037807de5decb` |
| `audits/predictive-intelligence/phase_02/research/QUERY_RESULTS.jsonl` | `f0aafb221d5c99be28d5de203c660a7f2bc4f8b128171120f4da11f63326045b` |
| `audits/predictive-intelligence/phase_02/research/ROOT_COMMITS.jsonl` | `d4823f94f65b93af44a1e1fcef567f695f2863ea176094889ecf91fd3846733d` |
| `audits/predictive-intelligence/phase_02/research/SEARCH_LOG.md` | `7be364a08c874546a75f43329659f2084c3c3a345dd668b45de4bd10dc0bde32` |
| `audits/predictive-intelligence/phase_02/research/SHORTLIST.csv` | `2d574eb68993ab065456e109c067224ed9fd9c4707a04badd04ae9c33d90e355` |
| `audits/predictive-intelligence/phase_02/research/SHORTLIST_ANNOTATIONS.csv` | `90770c12a9d19ebc7b24a107a0e64f06f28a163b634bbc234b7e8445547005be` |
| `audits/predictive-intelligence/phase_02/research/SPECIAL_FLAGS.json` | `de5aeae50654d5eec43bec93c4bd5b48f2dd6bef93ac8e60ee3a3149d58be4e1` |
| `audits/predictive-intelligence/phase_02/research/VERIFY_RESULTS.jsonl` | `462c96aba660ab8ec764c9c07f788f5d5c1f2ca030a4df05a198b1d0818ee2cd` |
| `docs/predictive-intelligence/DECISIONS.md` | `947710ec7c692820dccb423d6afb3a0adabbf2c2b17193cdd510137e4956c0da` |
| `docs/predictive-intelligence/ROADMAP.md` | `a823c8d74b6661c67b5adb36a0f1bf614f93cbffb82e82dcbdde372450ed8101` |
| `docs/predictive-intelligence/HANDOFF.md` | `1fce7a4255976d76998343c84d01789db53a10cd2c1fb9a86848fdfd647123ea` |
| `audits/predictive-intelligence/COST_LEDGER.md` | `ca40d439fb4785a537431448cc9f6be83528a0234c86019bba26a53763b9c708` |

## Writing style

A Python scan of every Markdown, CSV, JSON and Python file this phase wrote, plus DECISIONS.md, ROADMAP.md, HANDOFF.md and COST_LEDGER.md, for en and em dashes, curly quotes and a list of marketing words: no hit after one rewording (a marketing-list word in the TabPFN flag source). The JSONL data files hold third-party names and URLs; the scan found no dash or curly quote in them either.

## Limitations

- GitHub search, topics and REST metadata unavailable (PI-D-023); topic coverage depends on packages with keywords, WebSearch, documentation and paper links.
- The keyword index lists recent packages first; established libraries came mostly through documentation, WebSearch, PyPI and the seed list. 1,877 returned names were not individually screened (EXCLUSIONS.md).
- ecosyste.ms is a mirror with its own sync lag; four candidates have no record there.
- WebSearch results carry no body hash.
- Activity is the pinned commit date; commit dates can be set by the committer.
- Code evidence shows a symbol is defined at the pin, not that it works for these targets; Phase 03 smoke tests decide that.
- The MiroFish maintainer FAQ (issue 726) was not reachable (403); Phase 03 should read it another way.

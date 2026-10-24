# Phase 02 evidence: independent predictive GitHub discovery

| Item | Value |
|---|---|
| Phase | 02, "Find a broad, verifiable, diversified landscape of prediction tools" |
| Status | PASS after repair pass 2. Was NEEDS_REVIEW at `498eaa0`; the orchestrator's independent skeptic (PI-D-013) found 1 MATERIAL and 6 MINOR findings and one new counterexample. Each was verified against live data first, all were accepted, and each is repaired below (section "Repair pass 2") with change control PI-D-025 |
| Branch | `feature/predictive-intelligence` |
| HEAD before | `a402df67bd1e23227d06baa2e0b4fbdbe494e905` (Phase 01 repair pass 2, pushed) |
| Commits | `498eaa0` content (first pass); the repair pass 2 commit on top of it is HEAD (read its hash with `git log -1`; this file is part of it) |
| Time (UTC) | 2026-10-24T02:50Z (entry suite) to 03:45Z (first pass); repair pass 2 04:07Z to 04:35Z |
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
| C4 | met | after repair pass 2: 68 distinct successful queries over 11 families and 5 mechanisms (keyword index 17, documentation 6, papers 12, WebSearch 33, PyPI 123 lookups); 22 GitHub search attempts refused (HTTP 403, logged); first pass: 60 over 9 families; `research/SEARCH_LOG.md`, `QUERY_RESULTS.jsonl` |
| C5 | met | after repair pass 2: 132 candidates, 131 unique root histories (aeon is a hard fork of sktime, flagged); 175 verified inputs, clone HEAD equal to pin for every reachable one, 4 vanished; every row on its canonical path (successor search for rows without a mirror record, PI-D-025); `check_candidates.py` 0 problems. First pass: 107 candidates, two of them on pre-transfer paths (skeptic m1, repaired) |
| C6 | met | license from the file at the pin for all 132, sha256 of the file bytes (repair pass 2, skeptic m3; the first pass hashed decoded text, which differed for CRLF files); puncc from its REUSE `LICENSES/` folder; flags: AGPL 4, GPL 6, LGPL 2, MPL 1, BUSL 1, FSL 1, Commons Clause 1, non-commercial weights 2 (README notices); GPU, LLM, memory-service and server dependencies from pinned dependency files and PyPI base requirements, with sources; per-file and vendored licensing of every shortlisted row in `research/LICENSE_SCAN.csv` (skeptic m2) |
| C7 | met | every candidate names needs; the checker validates every need cell against GAP_MATRIX.csv |
| C8 | met | 30 shortlisted, no score or rank; families: tabular 5, time series 4, calibration 5, online and drift 4, behavioral 4 (MiroFish, OASIS, Mesa, black-it), experiment audit 4, event-time labels 3, point-in-time feature store 1 (feast, added in repair pass 2); the written shortlist rule is in EXCLUSIONS.md section G and the checker enforces its activity and license parts; every row has code evidence (path, blob, line) re-read from a fresh fetch at the pin (`research/LIVE_CHECK.txt`) |
| C9 | met | `research/EXCLUSIONS.md`: 46 screened exclusions (A to F), 102 not-shortlisted reasons (G) and the repair-pass screen (H); the intro sentence about the selection rule is corrected (skeptic M1); the checker shows every verified input is covered |
| C10 | met | five rows drawn with seed 20261024 from 114 pairs; all reappeared on re-run (`PROVENANCE_AUDIT.json`) |
| C11 | met | `check_candidates_negative.py`: 32 of 32 mutations refused (25 first pass, 7 added in repair pass 2, including the skeptic's counterexample), unmutated copy passes |
| C12 | met | TheSenseAI/SenseAI and Cooktrenches/Scan-Scam-AI-v1, both found by WebSearch W09, excluded as README_ONLY_CLAIM with file-level reasons |
| C13 | met | MiroFish row: AGPL-3.0 (LICENSE and backend/pyproject.toml:6), LLM and Zep Cloud keys required (backend/app/config.py), Python >=3.11,<3.13, no probability output in the backend; shortlisted as a behavioral scenario generator only |
| C14 | met | firecrawl/firecrawl (and its old path), unclecode/crawl4ai, getmaxun/maxun pinned and listed as tooling; the checker refuses them as candidates |
| C15 | met | see "Tests and tracked data" below |
| C16 | met | COST_LEDGER.md row for Phase 02: 0 credits; free calls counted below |
| C17 | met | clones deleted after recording: first pass at 2026-10-24T03:37:31Z (42 MB), repair pass 2 at 04:24:12Z (30 MB); pins kept; raw API bodies kept outside the repo (`/home/claude/pi_orchestration/phase02/raw/`) |
| C18 | met | this file, PHASE_02_RESULTS.json, SKEPTIC_PACKET.md (marked USED), skeptic review in `skeptic/`, ROADMAP row, DECISIONS PI-D-023 to PI-D-025, HANDOFF rewritten |
| C19 | met | style scan, see below |
| C20 | met | two commits: `498eaa0` (content) and the repair pass 2 commit; no hash-only commit |

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
3. Corrected in repair pass 2 (skeptic m1): the first pass said repos.ecosyste.ms had no record for four candidates. Three of them have records under another path that serves the same HEAD: TheClimateCorporation/properscoring is properscoring/properscoring (archived), JoelForamitti/agentpy is jofmi/agentpy, pandera-dev/pandera is unionai-oss/pandera. Those rows now sit on the recorded paths (SUCCESSOR_SEARCH.jsonl, PI-D-025). quantscious/finmlkit has no repository record, but its packages.ecosyste.ms record names the same path (fork false, archived false).

## Results

- First pass: 107 candidates over 9 families (calibration 17, time series 17, tabular 14, behavioral 14, online and drift 12, experiment audit 12, event-time labels 9, on-chain and financial 9, social narrative 3). After repair pass 2: 132 candidates over 11 families (adds point-in-time feature store 13, regime and state models 8, event-time labels +3, time series +1). Independent discovery (a query that does not name the target, is not its own page, and ran before the candidate was annotated): 99 of 132, 74 of the first 107; credited by any corpus query: 114.
- Shortlist 30 after repair pass 2 (feast added; 11 seeds, 19 found by the corpus), each with code evidence at the pin, the uncertainty Phase 03 must resolve, and a per-file license scan.
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
5. Pass 5, repair pass 2 after the independent skeptic (section "Repair pass 2"): screen of the missed need-matching names and two new query families, canonical-path rule with successor searches, byte hashes, per-file license scan, written shortlist rule and new checker guards. This is the last pass the five-pass limit allows.

## Own adversarial pass (not independent)

Written in the first pass at `498eaa0`; the counts here are first-pass counts, and the independent review in "Repair pass 2" found what this pass missed (the selection rule, transferred paths, byte hashes, family guards).

| Attack | Result |
|---|---|
| Fork or mirror counted as a candidate | ecosyste.ms fork flags (103 of 107 known, all false), identical-HEAD rule, root commits for all 107: one shared root (aeon, flagged and not shortlisted). Residual: the four candidates without an ecosyste.ms record could be forks of a repository outside the set; their PyPI packages name them as the source |
| Seed anchoring (famous repos rewrite the goal) | needs frozen first; 18 of 29 shortlisted are not seeds; seeds causalml, dowhy, autogen excluded for need mismatch or archival; the shortlist includes small projects (venn-abers, model-diagnostics, hazardous, purged-cross-validation, black-it) |
| README-only credit (P42) | two real repositories excluded with file-level reasons; checker refuses README or docs paths as code evidence and undefined symbols; MiroFish claims not credited |
| License wrong | file text at the pin, PyPI cross-check, special flags with lines. Residual: per-file license headers and vendored code inside a permissive repository are not scanned; model-weight licenses live on Hugging Face |
| Fabricated or stale verification data | the live mode re-fetches pinned commits and re-reads code evidence from fresh fetches; any seed can be used |
| Python 3.13 support overstated | `py313_declared_on_pypi` is what PyPI declares; a pure-Python sdist without classifiers may still run, a declared package may still fail; Phase 04 installs in a venv |
| Tracked data or code touched | diff limited to the two predictive namespaces |

Own counterexample (not independent): a repository whose root LICENSE is MIT but whose core module carries an AGPL header (vendored code), or whose license changed after the pin. The checker would accept it, and the PyPI cross-check only catches it when PyPI declares the other license. Phase 03's LICENSE_AND_SECURITY_GATE must scan per-file headers and the dependency tree of each shortlisted repository at its pin. The independent skeptic's counterexample and what now catches it are in the section "Repair pass 2".

## Repair pass 2 (independent skeptic review folded in)

The orchestrator's independent skeptic reviewed `498eaa0` (review and script copied to `skeptic/PHASE_02_SKEPTIC.md` and `skeptic/PHASE_02_skeptic_counterexample.py`; its output on `498eaa0` is `skeptic/counterexample_output_498eaa0.txt`). The orchestrator's own rerun on `498eaa0`: `1 failed, 858 passed in 136.62s`. Every finding was checked against live data before any change.

| Finding | Verified how | Verdict | Repair |
|---|---|---|---|
| M1 (MATERIAL): the stated selection rule (name or summary matches a need) was not applied; six need-matching names in recorded results were never screened; no query targeted point-in-time feature stores; no regime-state candidate | grep of QUERY_RESULTS.jsonl: featuretools D01 rank 7, hmmlearn D01 rank 22, torchsurv K10, auton-survival K10_p2 rank 55, xgbse K10_p1 rank 22, ta-lib-python D05 rank 95 | agreed | EXCLUSIONS.md sentence corrected (selection was analyst judgment); the six screened; query families added: K15 (feature-store), W29, W30, W33 for point-in-time feature stores and as-of joins, K16 (hidden-markov-model), K17 (regime-switching), W31, W32 for regime or state models; 34 more inputs verified, 25 new candidates, 8 screened exclusions, feast-dev/feast shortlisted, statsmodels MarkovRegression added as N07 code evidence; EXCLUSIONS.md section H lists every outcome. A name-term scan of the names still unscreened is disclosed with its count |
| m1: two rows on pre-transfer paths (properscoring, agentpy), archived flag lost; "four rows without a mirror record" wrong for three | `git ls-remote` and repos.ecosyste.ms for both paths of each (04:07:38Z to 04:07:48Z): identical HEADs; properscoring/properscoring archived=true; jofmi/agentpy and unionai-oss/pandera have records | agreed | successor search recorded per row (SUCCESSOR_SEARCH.jsonl); rows moved to properscoring/properscoring (ARCHIVED), jofmi/agentpy, unionai-oss/pandera (uniform rule, see disagreement note); `canonical_basis` column; checker refuses a row without a mirror record and without a successor search, a known pre-transfer path, a lost archived flag, and a name that differs from the mirror record (PI-D-025) |
| m2: single-valued license column hides vendored and per-file licensing | per-file scan of all 30 shortlisted pins (`probes/license_scan.py`, full depth-1 fetch, 04:16:39Z to 04:17:58Z, rerun with a restricted-license pattern) | agreed | `research/LICENSE_SCAN.csv` and SHORTLIST.csv column `license_scan_phase03` as the Phase 03 license-gate input: sktime (Apache-2.0 51 headers, MIT 12, GPL text in 2 shapelet wrappers, a source-available license named in tirex.py, vendored LICENSE and NOTICE under libs), interpret (Apache-2.0 header in the native core), TabPFN (2 BSD headers), MAPIE (1 MIT), skore (BSD in `_externals`), LightGBM and mlflow (git submodules), scikit-learn (vendored MIT externals); a header is a lead, not a determination |
| m3: license sha256 of decoded text, not bytes | raw bytes of jofmi/agentpy LICENSE at the pin: 1,532 bytes, 27 CR characters, sha256 `7631167b053f...`; first pass recorded `8acaf16a...` | agreed | `verify_repos.py` and `build_candidates.py` hash the file bytes read with `git cat-file blob <pin>:<path>`; every license hash in CANDIDATES.csv recomputed (full 64 hex); the agentpy row now shows `7631167b053fb93b...` |
| m4: event-time family not required; shortlist family not compared with candidates | the skeptic's cases C and D passed the first checker | agreed | `HIGH_PRIORITY` includes EVENT_TIME_LABELS; family labels compared; shortlist rule (activity, in-process licenses) enforced; negative cases added |
| m5: "89 credited to corpus queries" includes name-bearing and self-page credits; W21 to W28 ran after annotation | recount | agreed, with a stricter count | column `independent_discovery_qids`: a credit counts only from a query that does not name the target, is not its own page, and ran before the candidate was annotated (`annotated_at` column; first 107 at 03:21:01Z). Result: 74 of the first 107 (the skeptic's 82 did not also drop post-annotation credits), 99 of 132 after repair |
| m6: N13 mapped to MODEL_TRAINING cells | NEEDS.csv row N13 | agreed | NEEDS.csv stays frozen (hash pinned); `research/NEEDS_NOTES.md` states the proxy link; SHORTLIST.csv `gap_link_note` on every N13 row |

Disagreement noted: for pandera the skeptic found the first choice (pandera-dev/pandera, named by the 2026 PyPI release) defensible. Repair pass 2 applies one uniform rule instead (PI-D-025: when two paths serve the same HEAD, the path with the mirror record is canonical), which gives unionai-oss/pandera, the path ecosyste.ms records and the README at the pin links. Which path GitHub itself treats as current cannot be read without the GitHub API; both paths are recorded.

### Counterexample and what catches it now

The skeptic's new counterexample: a shortlisted repository recorded under its pre-transfer path, with the mirror lookup 404 and fork and archived flags blank, passes every first-pass check (case B rewrote mesa/mesa as projectmesa/mesa); two real rows (properscoring, agentpy) were already in that state. Its script on the repaired tree (`skeptic/counterexample_output_after_repair.txt`):

```
A real row: stale pre-transfer path, archived lost      checker exit 0 -> recorded properscoring/properscoring eco_status=200 archived='true' (data repaired, nothing to catch)
B shortlisted repo under pre-transfer path               checker exit 1 -> CAUGHT ("has no mirror record and no recorded successor search")
C whole event-time family dropped from shortlist         checker exit 1 -> CAUGHT ("EVENT_TIME_LABELS has 0")
D family minimum met by a relabelled shortlist row       checker exit 1 -> CAUGHT ("family ... differs from candidates family")
```

`check_candidates_negative.py` repeats B, C and D and adds the reverse of A (the old properscoring path put back), a lost archived flag, an inactive shortlisted row and a copyleft library shortlisted in-process: 32 of 32 refused.

### Repair pass 2 commands and exits

| # | Check | Command | Exit | Result |
|---|---|---|---:|---|
| R1 | Skeptic findings verified | `git ls-remote` and repos.ecosyste.ms for both paths of properscoring, agentpy, pandera and finmlkit; raw LICENSE bytes of agentpy at its pin; grep of QUERY_RESULTS.jsonl (04:07:38Z to 04:08:00Z) | 0 | all findings reproduced |
| R2 | New keyword queries | `python3 probes/discover.py research/QUERIES.json <raw> research/QUERY_RESULTS.jsonl K15 K16 K17` (04:08:11Z to 04:08:25Z) | 0 | 6 calls, HTTP 200 |
| R3 | New WebSearch queries | W29 to W32 (04:08:25Z to 04:08:59Z), W33 (04:09:05Z to 04:09:24Z) | n/a | result URLs recorded |
| R4 | PyPI | `python3 probes/pypi_lookup.py ... featuretools hmmlearn ...` (25 names) | 0 | 24 HTTP 200, `ftlite` HTTP 404 |
| R5 | Verification | `python3 probes/verify_repos.py repair_verify.txt ...` (34 inputs, license hash of bytes) | 0 | 32 verified, 2 vanished |
| R6 | Successor search | packages.ecosyste.ms package records for pandera, finmlkit, properscoring, agentpy; README of pandera at its pin (04:11Z) | 0 | SUCCESSOR_SEARCH.jsonl |
| R7 | Root commits | `python3 probes/root_commits.py repair_candidates.txt ...` (28 repositories, root commit dates added) | 0 | no new shared root |
| R8 | Pins for the build | `python3 probes/fetch_pins.py . /home/claude/pi_research --workers 8` (04:13:48Z to 04:13:58Z) | 0 | `candidates 132 problems 0` |
| R9 | License scan | `python3 probes/license_scan.py . <work>` twice (04:16:39Z onward) | 0 | 30 rows in LICENSE_SCAN.csv |
| R10 | Build and renders | `build_candidates.py`, `render_exclusions.py`, `render_search_log.py` | 0, 0, 0 | `candidates 132 shortlist 30`; `excluded screened 46 not shortlisted 102`; `rows 107 distinct ok queries 68 families 11` |
| R11 | Checker offline | `python3 probes/check_candidates.py . ../phase_01/architecture/GAP_MATRIX.csv` | 0 | `problems 0` |
| R12 | Negative tests | `python3 probes/check_candidates_negative.py . ../phase_01/architecture/GAP_MATRIX.csv` | 0 | `cases 32 not caught 0` |
| R13 | Skeptic's script | `python3 -I skeptic/PHASE_02_skeptic_counterexample.py . ../phase_01/architecture/GAP_MATRIX.csv /home/claude/pi_orchestration/skeptic/p02` | 0 | B, C, D CAUGHT; A shows the repaired row |
| R14 | Live check | `python3 probes/check_candidates.py ... --live 10 --seed 20261024` (to 04:24:06Z) | 0 | 36 pins fetched, 30 shortlisted code evidence re-read and matched, mlflow HEAD moved again (pin fetchable), `problems 0` |
| R15 | Clean-up | `rm -rf /home/claude/pi_research/*__* ...` (04:24:12Z) | 0 | clones removed |
| R16 | Full suite | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` (from 04:24:12Z) | 1 | `1 failed, 858 passed in 134.21s (0:02:14)`, only the known clock test; strays removed by hand; DB unchanged |

Repair pass 2 free calls: about 75 `git ls-remote` (verification 34, findings checks 7, live 36), 34 blob-less clones, 132 pin fetches, 30 full depth-1 fetches twice for the license scan, 28 treeless clones, about 40 repos.ecosyste.ms lookups, 6 packages.ecosyste.ms keyword calls and 4 package records, 25 PyPI lookups, 2 raw GitHub reads, 5 WebSearch calls. Firecrawl 0.

## Artifact sha256

Hashes at the time of the repair pass 2 commit (PHASE_02_RESULTS.json holds this file's hash).

| Path | sha256 |
|---|---|
| `audits/predictive-intelligence/phase_02/ACCEPTANCE_CHECKLIST.md` | `5009779aee21891c1aff6bd1f44c64363321e5420caa3ed82ad2ea81d135f6f0` |
| `audits/predictive-intelligence/phase_02/SKEPTIC_PACKET.md` | `a8f62dfd7997caf517709bf153d3cf57636b204662fc0450277b1e56866cef55` |
| `audits/predictive-intelligence/phase_02/probes/build_candidates.py` | `3e468fec982259c060ed2eb37cf46166f3974fb8aa233a6de1472ac109a68fe1` |
| `audits/predictive-intelligence/phase_02/probes/check_candidates.py` | `364db0d48694fb4a0328347c0ad401cf165c01222ba59930e559bd81403ccac9` |
| `audits/predictive-intelligence/phase_02/probes/check_candidates_negative.py` | `1ded214583c2de8142677a670fd49e561034a500c25b65b1baa093ab8caa0bfb` |
| `audits/predictive-intelligence/phase_02/probes/discover.py` | `558a202481d2c265687de741ae49bff06208d072092769b3d56a6471101eec99` |
| `audits/predictive-intelligence/phase_02/probes/fetch_pins.py` | `c8bbd9c78a525c946ab4554ce6087267fd8aded87873b76816fdd7baae009850` |
| `audits/predictive-intelligence/phase_02/probes/gh_search.py` | `658c482bf259cae5d7f001a0974c0b7923df1912ecc529e8aab00d94bdf185cf` |
| `audits/predictive-intelligence/phase_02/probes/license_scan.py` | `5702e7a07df78903b700414c5820b3c02edae6d04645a16389c865eab9407535` |
| `audits/predictive-intelligence/phase_02/probes/pypi_lookup.py` | `e5b1e1b7899f710149e28e02f07e0ecf71f0ce6eb82f49b8bfa1144d7f5624ff` |
| `audits/predictive-intelligence/phase_02/probes/render_exclusions.py` | `8c16100a7cac2b782b408fd8d91d2d2f740cfc1e5fe56e394e7d08ca154cb709` |
| `audits/predictive-intelligence/phase_02/probes/render_search_log.py` | `0fd24ef161844256deae8f7d4296e706ea589f28ce93b7e15ad15c514c086723` |
| `audits/predictive-intelligence/phase_02/probes/root_commits.py` | `5440a5c030eb7b5c01bc16e89549a3edea0d0168bce2f01685fc2a62bfdf0cd8` |
| `audits/predictive-intelligence/phase_02/probes/verify_repos.py` | `394092ebc409001036e62fbf42ec7b4b6acd845b8e3f592b9b2d99c972e65185` |
| `audits/predictive-intelligence/phase_02/research/CANDIDATES.csv` | `cb5cce4484276175ba73db14aaf1a686c1c9a9b0b9e9c8e0ca3fccf7f69a0607` |
| `audits/predictive-intelligence/phase_02/research/CANDIDATE_ANNOTATIONS.csv` | `db02f61c234eb03453efe5bc50398580cbc431e5dbf99b75f69e6c9ff1ed2a0a` |
| `audits/predictive-intelligence/phase_02/research/EXCLUSIONS.md` | `0e1ad94f51ca9377104eef8a7fe133c54619264c60543262fb6a99449e93f653` |
| `audits/predictive-intelligence/phase_02/research/EXTRA_PINS.jsonl` | `91b6ac208401442733bfbbb7288823a06571a18efbbdfd1a3704cd269fdb3a38` |
| `audits/predictive-intelligence/phase_02/research/LICENSE_SCAN.csv` | `c777e9a1277927dc37df1f45837ec63935478cf861ed75c65e485f1bfe16fb24` |
| `audits/predictive-intelligence/phase_02/research/LIVE_CHECK.txt` | `3be55d71da3852f6837f64acfc77a56de75bdf25b4c3b04ce85d08e3734081c2` |
| `audits/predictive-intelligence/phase_02/research/MIRROR_CHECKS.jsonl` | `c34ae49e3a5553ef0467e6c2df8df156d64709b5b93eb7eb990d33c402a66b98` |
| `audits/predictive-intelligence/phase_02/research/NEEDS.csv` | `90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e` |
| `audits/predictive-intelligence/phase_02/research/NEEDS_NOTES.md` | `4f46653a674e1345fa825e5634efee53f471a6f751cf56dd39a935dc8b2e80ae` |
| `audits/predictive-intelligence/phase_02/research/PROVENANCE_AUDIT.json` | `83714765982a3984bdd6df26924f2157af381fb232c4f3d6989d046753839fcd` |
| `audits/predictive-intelligence/phase_02/research/PROVENANCE_AUDIT_RERUN.jsonl` | `b7b2c1801bb5b8b7262078a0e46400fb7f79b21a82188d7caf4d080f32d174c8` |
| `audits/predictive-intelligence/phase_02/research/PYPI_LOOKUPS.jsonl` | `f15f596d40627315ef61dfa43582204fa1be13d3684c1125550f627cf5898687` |
| `audits/predictive-intelligence/phase_02/research/QUERIES.json` | `dd74556605206c0a269930ac735b7b827c2ee0b44a28e61a98b19533c311d1f8` |
| `audits/predictive-intelligence/phase_02/research/QUERY_RESULTS.jsonl` | `120efd72255ab3f1ca1c92da8f27a4db5041dc7c25aa4a10f1b88556adfec1cb` |
| `audits/predictive-intelligence/phase_02/research/ROOT_COMMITS.jsonl` | `c99f7fb4fa399c296ad1a45d4434ec833ac3908adfdd27ed48db52e075ae4e32` |
| `audits/predictive-intelligence/phase_02/research/SEARCH_LOG.md` | `27a06e82effafad08af950dbf9b749aa745ad599f3fc9b0b3b5a7b34680f2325` |
| `audits/predictive-intelligence/phase_02/research/SHORTLIST.csv` | `6723e7c29b6c32d6dd3dace52f57c2131b396e7693e6cb111425a7e3b63356c2` |
| `audits/predictive-intelligence/phase_02/research/SHORTLIST_ANNOTATIONS.csv` | `f4f623020ff0aae6565eef499c3accc86e617b58106bdc6b99a95b47e71b8357` |
| `audits/predictive-intelligence/phase_02/research/SPECIAL_FLAGS.json` | `de5aeae50654d5eec43bec93c4bd5b48f2dd6bef93ac8e60ee3a3149d58be4e1` |
| `audits/predictive-intelligence/phase_02/research/SUCCESSOR_SEARCH.jsonl` | `d969ac81634cc7d58af605033f1d1ae566faa13f3a648e49286cbb5cfc59a51e` |
| `audits/predictive-intelligence/phase_02/research/VERIFY_RESULTS.jsonl` | `c263fbf7fd49e08f51b79e0377beb1e3488cb0eebc5a301c4af372885d71076d` |
| `audits/predictive-intelligence/phase_02/skeptic/PHASE_02_SKEPTIC.md` | `bae2ccb6b4a443b77e6e9fa1979230bb9475a9b9ae967d453959db0966b8eb8f` |
| `audits/predictive-intelligence/phase_02/skeptic/PHASE_02_skeptic_counterexample.py` | `82e1a4bad8b0f379555a233f37b5aefeeba4215a7d5b92a72f1dbdc4d798bfba` |
| `audits/predictive-intelligence/phase_02/skeptic/counterexample_output_498eaa0.txt` | `a91329f78be839dd7cbf2d444a37c767f5082048cd1ccaf6791dc35d4d0ddd47` |
| `audits/predictive-intelligence/phase_02/skeptic/counterexample_output_after_repair.txt` | `6b00b99b046ae29d6c82885f732b77459821196a4ca5c5cdde8ff6b957d70352` |
| `docs/predictive-intelligence/DECISIONS.md` | `d5e3de7f48e1044849f4fc36fc3e6ec212436e3175c67a7fec61f0291ed89413` |
| `docs/predictive-intelligence/ROADMAP.md` | `0f214500cca27a9d702c46a313b0363bb5053fd0eb7f642110f40d44f95e0b6c` |
| `docs/predictive-intelligence/HANDOFF.md` | `bb754272a29e17465af1a838f0934db7f3546a35aca6faa10c3e33993d3c1c79` |
| `audits/predictive-intelligence/COST_LEDGER.md` | `cd6aef7ef42a8b0121e8aa42677d3652bdc008969cb454e31139a8ad2fd405a8` |

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
- Selection from returned names to verified inputs was analyst judgment; names never selected remain unscreened, and a name-term scan of them is disclosed in EXCLUSIONS.md (repair pass 2).
- Which of two same-HEAD paths GitHub treats as current cannot be read without the GitHub API; PI-D-025 takes the path with a mirror record (pandera: unionai-oss/pandera, while the newest PyPI release names pandera-dev/pandera).

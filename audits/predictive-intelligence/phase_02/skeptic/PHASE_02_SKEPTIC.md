# Phase 02 independent skeptic review

Reviewer: orchestrator's independent skeptic (PI-D-013). Reviewed commit `498eaa0` on `feature/predictive-intelligence` in my own clone `/home/claude/pi_orchestration/skeptic_02` (checkout clean). All checks ran 2026-10-24 between 03:45Z and 04:00Z. Nothing was written inside `/home/claude/memelab-inbox` (its HEAD is still `498eaa0`, status clean). No Firecrawl, no paid call. Free calls: about 150 `git ls-remote`, 45 depth-1 fetches at pins plus 2 blob-less clones, 36 live-check fetches, about 35 repos.ecosyste.ms lookups, 4 PyPI JSON reads, 5 packages.ecosyste.ms or raw GitHub reads (query re-runs), 3 WebSearch calls. Clones were kept in my scratchpad and deleted afterwards.

Script and outputs: `PHASE_02_skeptic_counterexample.py` (this folder), raw outputs in `p02/` (`lsremote.tsv`, `fetch.log`, `live_seed4242.txt`, `counterexample_output.txt`, `eco_*.json`).

## Verdict

Material failure found (one, records level). Counts, pins, license files, provenance re-runs, MiroFish framing and tracked-path hygiene all hold. The selection step from returned names to verified inputs does not follow its own stated rule, and a whole family the orchestrator asked about (point-in-time feature stores) was never searched. The 45 and 20 thresholds survive every dedupe I tried.

## Checks

| # | Check | Command or input | Result |
|---|---|---|---|
| 1 | Pins resolve, all 107 | `git ls-remote https://github.com/<repo> HEAD` for every CANDIDATES.csv row (8 parallel) | 107 of 107 answer with 40-hex; 106 equal the pin; `mlflow/mlflow` moved (`cd19153f5e` to `154f628530`), its pin still fetches (check 9) |
| 2 | Clone at pin, 45 repos (29 shortlisted plus 16 others) | `git init; git fetch --depth 1 --filter=blob:limit=3m origin <pin>; git checkout FETCH_HEAD` (`p02/fetch_one.sh`) | 45 of 45 fetched; `git rev-parse HEAD` equals the recorded pin for all |
| 3 | License at pin, 37 repos (29 shortlisted plus properscoring, finmlkit, TokenLab, casevo, fractal-defi, agentpy, timeseriescv, triple_barrier) | own classifier on the recorded license file; sha256 of the file | classification matches for 37 of 37; recorded hash prefix matches for 36 of 37; `JoelForamitti/agentpy` differs (finding m3) |
| 4 | Canonical name and fork status, 19 picks plus the four "no record" rows | `repos.ecosyste.ms/api/v1/hosts/GitHub/repositories/<owner%2Fname>`, then likely successor paths, PyPI `project_urls`, WebSearch | 19 picks: name equal, `fork` false, archived as recorded. Of the four "no record" rows, three have records under another name (finding m1); `quantscious/finmlkit` has none anywhere |
| 5 | Forks and hard forks | ROOT_COMMITS.jsonl shared roots; shared code blobs (files of 400 bytes or more, `.py .pyx .c .cpp .h .js .ts .R`) across my 45 clones | one shared root (sktime, aeon), as recorded. Shared blobs: aeon and sktime 14, skpro and sktime 4, tslearn with sktime or aeon 2; none between abides-sim/abides and jpmorganchase/abides-jpmc-public, donlnz/nonconformist and OliverHennhoefer/nonconform, sam31415/timeseriescv and eslazarev/purged-cross-validation, or among mlfinpy, finmlkit and triple_barrier |
| 6 | Counts after dedupe | CANDIDATES.csv and SHORTLIST.csv | 107 unique names, 106 unique histories, two rows under stale names (still unique repositories); shortlist 29 unique, all in CANDIDATES.csv with the same pins, no fork. Both thresholds hold with a wide margin even after dropping every row that has no independent discovery credit (78 left by my strict count) |
| 7 | Re-run 3 recorded queries | `python3 -I probes/discover.py research/QUERIES.json <scratch>/raw <scratch>/rerun.jsonl K10 K06 D02 --tag _skeptic02` (03:51:16Z to 03:51:25Z) | K06 p1 and p2, K10 p1 and p2, D02: HTTP 200, body sha256 equal to the recorded bodies, the 15 credited (repository, query) pairs reappear at the same ranks (for example hazardous K10_p1 rank 72, crepes D02 rank 1, ruptures K06_p1 ranks 9, 20, 40). Caveat as the phase noted: an identical body inside the CDN max-age shows reproducibility of the response, not a fresh index read |
| 8 | Re-run 1 WebSearch query | W03 "purged k-fold cross validation embargo python library github combinatorial purged" | `github.com/eslazarev/purged-cross-validation` is result 1 again |
| 9 | Checker, offline, negative and live | `check_candidates.py` offline; `check_candidates_negative.py`; `check_candidates.py --live 10 --seed 4242` (03:53:35Z to 03:54:22Z) | `problems 0`; `cases 25 not caught 0`; live: 36 pins fetched, 29 shortlisted code evidence items re-read and matched, `problems 0` |
| 10 | Needs frozen before the first query | `sha256sum research/NEEDS.csv`; `stat` in the working tree | `90c9391aa6674abbf138b59e610ce0b72ab7eeb6a15763458e341d6fd6560f5e` as recorded; mtime 2026-10-24T02:55:41Z, before the first query at 02:56:45Z |
| 11 | Gap linkage | each SHORTLIST row's `gap_cells` against the union of its needs' cells in NEEDS.csv and the status in phase_01 GAP_MATRIX.csv | 29 of 29 equal the union; statuses only MISSING or PARTIAL |
| 12 | Family coverage | SHORTLIST.csv `family` | tabular 5, calibration 5, time series 4, online and drift 4, behavioral 4, experiment audit 4, event time 3. Each high-priority family keeps 3 or more even without the tangential rows (statsmodels in tabular, arch in calibration, sktime in time series) |
| 13 | Per-file license headers, 29 shortlisted pins | grep of every text file for SPDX identifiers, GNU, GPL, AGPL, LGPL, MPL, CC BY-NC, non-commercial, Community License, Business Source; nested LICENSE and NOTICE files; `.gitmodules` | mixed permissive licensing in at least six shortlisted repositories; no copyleft or non-commercial header in any permissive one (finding m2) |
| 14 | MiroFish framing | SHORTLIST, CANDIDATE_ANNOTATIONS, EXCLUSIONS, SEARCH_LOG, HANDOFF, DECISIONS; pinned `backend/pyproject.toml`, `backend/app/config.py` | framed only as scenario generation and hypothesis generation everywhere; README "predict everything" claim not credited; at the pin `backend/pyproject.toml:5-6` requires-python `>=3.11,<3.13`, license AGPL-3.0; `backend/app/config.py:28-33, 67-72` require LLM_API_KEY and ZEP_API_KEY and refuse a self-hosted Zep URL; no probability output in `backend/`. Note under m6 |
| 15 | P42 on real repositories | blob-less clones of TheSenseAI/SenseAI and Cooktrenches/Scan-Scam-AI-v1 | pins `f89e136058e6` (10 files, no Python) and `cd9f26270192` (101 files, 67 Python) match VERIFY_RESULTS.jsonl; exclusions stand |
| 16 | Re-derived file counts and dates, 12 rows | `git ls-tree` counts and `git log -1 --format=%cI` at the pins (TokenLab, casevo, fractal-defi, finmlkit, agentpy, properscoring, venn-abers, purged-cross-validation, mlfinpy, hazardous, crepes, timeseriescv) | `py_files`, `test_files` and `commit_date` equal CANDIDATES.csv for all 12 |
| 17 | Scope and style | `git diff --name-only a402df6..498eaa0`; scan of the changed files for em and en dashes and curly quotes | 33 files under `audits/predictive-intelligence/`, 3 under `docs/predictive-intelligence/`; none under `memelab/`, `tests/`, `inbox/`, `state/`, `data/`; 0 style hits; COST_LEDGER row for Phase 02 with 0 credits |
| 18 | Full suite | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` in my clone (03:55:54Z) | `1 failed, 858 passed in 138.49s (0:02:18)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays (`data/reports/20261024_0356_BRETT_0x532f.md`, sqlite shm and wal) appear in my clone only |

Numbers I re-derived: the 107 and 106 counts, the 29-row shortlist and its family counts, the NEEDS.csv hash and freeze time, 36 license hashes, 12 rows of file counts and commit dates, 15 discovery ranks across three queries, and the "89 credited to corpus queries" figure (82 by my count, finding m5).

## Findings

### MATERIAL

**M1. The selection rule is stated but not applied, and the point-in-time feature store family was never searched.** EXCLUSIONS.md line 5 says a returned name was selected for verification when "a name, package summary or linked documentation matched a frozen need in NEEDS.csv", and that the other 1,877 names were not screened. Recorded results falsify this. These repositories were returned by recorded queries, match a frozen need by name or summary, exist, are not forks, are permissive, and appear nowhere in CANDIDATES.csv, EXCLUSIONS.md, SEARCH_LOG.md or the annotations:

| Repository | Returned by | Need | Status (ecosyste.ms, 03:59Z) |
|---|---|---|---|
| alteryx/featuretools | D01 rank 7 | N06 point-in-time features (cutoff times) | BSD-3-Clause, active |
| hmmlearn/hmmlearn | D01 rank 22 | N06, N07 regime state | BSD-3-Clause, last push 2024-10-31 |
| Novartis/torchsurv | K10_p1 ranks 33, 34; K10_p2 rank 70 | N05 time to event | MIT, active |
| autonlab/auton-survival | K10_p2 rank 55 | N05 | MIT, last push 2024-04-04 |
| loft-br/xgboost-survival-embeddings | K10_p1 rank 22 | N05 | Apache-2.0, archived |
| TA-Lib/ta-lib-python | D05 rank 95 | N06 technical features | BSD-2-Clause, active |

Separately, no query of any mechanism targets point-in-time feature stores or as-of joins, although GAP_MATRIX `HIST_MARKET:POINT_IN_TIME_FEATURES` is PARTIAL and Phase 05 must build point-in-time feature storage. `feast-dev/feast`, `alteryx/featuretools`, `airbnb/chronon` and `google/temporian` all resolve with `git ls-remote`, are not forks and carry Apache-2.0 or BSD-3-Clause. PLANNED_SEAMS.md line 10 plans an in-house as-of view, which may well be the right answer, but Phase 02 records neither a candidate nor a reason, so Phase 04's adopt-or-build bakeoff has no external comparator for Phase 05. The shortlist also has no regime-state model for N07's "regime models" (stumpy and ruptures are analog search and change points; statsmodels is shortlisted only for Logit and multipletests).

Why material: thresholds and gate counts are unaffected, but the records tell Phase 03 that the need-matched pool was screened when it was not, and the missing family touches a later phase's core build choice. Repair (records level, no re-run of the phase): correct the EXCLUSIONS.md sentence to say selection was analyst judgment; add one query family for point-in-time feature stores and as-of joins, and screen feast, featuretools, chronon and temporian (candidate, or exclusion with a reason such as service stack versus the PLANNED_SEAMS as-of view); screen the six names above; say whether N07 regime states are expected from statsmodels (MarkovRegression) or need a candidate.

### MINOR

**m1. Two candidates are recorded under stale, pre-transfer paths; one loses its archived flag.** `TheClimateCorporation/properscoring` serves the same HEAD (`a465b5578d4b`) as `properscoring/properscoring`, which ecosyste.ms records as the current name with `archived: true` (last push 2023-03-09); the CANDIDATES row has `ecosystems_status 404`, blank archived and only `INACTIVE_18M`. `JoelForamitti/agentpy` serves the same HEAD (`42f5d498677c`) as `jofmi/agentpy`, which ecosyste.ms records (fork false, archived false; WebSearch result `github.com/jofmi/agentpy`). The evidence's "repos.ecosyste.ms has no record for four candidates" is wrong for three: properscoring and agentpy as above, and pandera, which ecosyste.ms keeps as `unionai-oss/pandera` (the repository's own README and PyPI name `pandera-dev`, so the phase's choice is defensible there). Neither stale row is shortlisted and counts are unchanged. Root cause: `probes/verify_repos.py:134-139` takes the canonical name from ecosyste.ms only when the queried path is known there; a 404 leaves the old path as canonical, and the same-HEAD rule only fires when the successor path is already in hand.

**m2. The license column is single-valued; per-file headers show mixed permissive licensing in shortlisted repositories.** None of these is copyleft or non-commercial inside the tree, but each carries obligations the root label hides:
- `sktime/sktime` (BSD-3-Clause root): `sktime/libs/` holds "private vendor forks" with Apache-2.0 SPDX headers (`sktime/libs/chronos/chronos.py:4`, 21 files under `sktime/libs/uni2ts/`, plus timesfm, lag_llama, timemoe, timer, sundial, falcon_tst, granite_ttm, `_aws_fortuna_enbpi/LICENSE.txt` and NOTICE.txt) and MIT code (kronos, momentfm, tbats, windfm). Wrappers point at restricted upstreams: `sktime/forecasting/tirex.py:3-7` (TiRex under the NXAI Community License) and `sktime/forecasting/timesfm3.py:74-77` (TimesFM 3.0 non-commercial weights).
- `interpretml/interpret` (MIT root): `shared/libebm/GaussianDistribution.hpp:2-4` is "Copyright 2019 Google LLC", Apache-2.0, inside the native core behind EBMClassifier.
- `PriorLabs/TabPFN` (Apache-2.0 root): `src/tabpfn/preprocessing/steps/squashing_scaler_transformer.py:1-8` and `src/tabpfn/preprocessing/torch/torch_squashing_scaler.py:15` are BSD-3-Clause code adapted from skrub; the README (line 109) points to THIRD-PARTY-NOTICES.md.
- `scikit-learn-contrib/MAPIE` (BSD-3-Clause root): `mapie/exchangeability_testing/bounds.py:13-16` adapts MIT code with its notice.
- `probabl-ai/skore` (MIT root): `skore/src/skore/_externals/pandas_accessors.py:3` is copied from pandas; `_externals/docscrape.py` is BSD-2.
- `lightgbm-org/LightGBM` (MIT root): `.gitmodules` pulls Eigen (MPL-2.0, file-level copyleft) and other libraries into builds; not in the tree.

The phase disclosed this residual. Phase 03's license gate should record per-file and vendored licenses and NOTICE obligations. Separately, `baobach/mlfinpy` implements book snippets (`mlfinpy/labeling/labeling.py:17`, "Snippet 3.2, page 45") under an MIT root; the snippet copyright is the book's, a provenance question for Phase 03, not a header conflict.

**m3. Recorded license sha256 is of decoded text, not file bytes.** `probes/verify_repos.py:163-164` hashes `text.encode()` from `git show` output that was decoded with universal newlines, so a CRLF file does not match `sha256sum` at the pin: `JoelForamitti/agentpy` LICENSE records `8acaf16a...` (1,505 bytes); the file at the pin is `7631167b053f...` (1,532 bytes, CRLF). Fix: hash the raw bytes, or name the normalization in the column.

**m4. Checker guard gaps** (shown by cases C and D of the script). `EVENT_TIME_LABELS` (survival and barrier-hit timing, the family behind target T1) is not in `HIGH_PRIORITY`, so removing lifelines, hazardous and mlfinpy from the shortlist passes. The checker counts SHORTLIST.csv family labels without comparing them to CANDIDATES.csv, so a family minimum can be met by relabelling a row. Current data are fine (event time has 3; labels agree), so this is a guard gap, not a data error.

**m5. The "89 credited to corpus queries" figure includes name-bearing or self-referential credits.** Seven candidates' only non-seed, non-PyPI credits are queries that name the target (W18 "ABIDES ... jpmorgan" for both ABIDES repositories, W19 "TimesFM github google-research", W20 "Zep graphiti ...", W26 "... netcal github") or the project's own page (D01 for scikit-learn, D03 for MiroFish). Excluding those leaves 82. W21 to W28 ran at 03:25Z to 03:27Z, after CANDIDATE_ANNOTATIONS.csv was written (03:21:01Z), so they confirm candidates already chosen; iteration 3 of the evidence says so. Thresholds unaffected.

**m6. N13 links behavioral simulation to MODEL_TRAINING cells.** NEEDS.csv maps N13 to `SOCIAL_SIGNALS:MODEL_TRAINING` and `CATALYST:MODEL_TRAINING` because GAP_MATRIX has no simulation facility. Every other record frames MiroFish correctly, but a reader of SHORTLIST.csv's `gap_cells` could take MiroFish as filling a model-training gap. A one-line note in SHORTLIST or NEEDS that the link is a proxy for the PLANNED_SEAMS boundary would remove the ambiguity.

## Counterexample (new): a transferred repository whose old path still answers

Wrong but plausible: a shortlisted repository is recorded under its pre-transfer path. Git serves the old path with the new repository's HEAD and no redirect message, the mirror answers 404 for the old name, so the row gets a valid pin, a clone equal to the pin, a license from the file, and blank fork and archived fields. If the successor has been archived (as properscoring's has), Phase 03 audits a dead project as if its maintenance status were unknown, and the "canonical owner/name" claim is false.

This is not hypothetical: `TheClimateCorporation/properscoring` (successor `properscoring/properscoring`, archived) and `JoelForamitti/agentpy` (successor `jofmi/agentpy`) are in CANDIDATES.csv today. `PHASE_02_skeptic_counterexample.py` shows nothing catches it:

```
python3 -I PHASE_02_skeptic_counterexample.py <phase_02 dir> <phase_01 GAP_MATRIX.csv> p02
A real row: stale pre-transfer path, archived lost      checker exit 0 -> NOT CAUGHT
B shortlisted repo under pre-transfer path, archived unknown   checker exit 0 -> NOT CAUGHT
C whole event-time family dropped from shortlist        checker exit 0 -> NOT CAUGHT
D family minimum met by a relabelled shortlist row      checker exit 0 -> NOT CAUGHT
```

Case B rewrites the shortlisted `mesa/mesa` row as `projectmesa/mesa` with `ecosystems_status 404` and blank flags, and removes the successor from the same-HEAD and verification records, as happened with properscoring. A check that would catch it: for every row with `ecosystems_status` other than 200, record a successor search (PyPI project URLs, the package's own README links, WebSearch, ecosyste.ms package lookup) with `git ls-remote` on each successor path; take fork, archived and the canonical name from the successor's record; and have `check_candidates.py` refuse a 404 row without that search recorded.

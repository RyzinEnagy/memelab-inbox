# Phase 03 evidence: pinned source audit, rubric and ranked top ten

PHASE 03 - repair pass applied; the final status and the post-commit suite are in PHASE_03_RESULTS.json and in the closing section of this file. The first pass (sections "Acceptance checklist results" to "Blockers, approvals, next") ended NEEDS_REVIEW at commit `c9e894d`, which was never pushed and has been rewritten (PI-D-030); the section "Repair pass" records how the orchestrator's skeptic and blind rescore were folded in.

## Context

- Repository `/home/claude/memelab-inbox`, branch `feature/predictive-intelligence`, HEAD before `77e78ce58788ef935af496a5753d53d1bed57b97` (Phase 02 PASS, pushed). Uncommitted at start: only the reviewers' `audits/predictive-intelligence/phase_03/` folder (30 reviews, 30 smoke folders).
- Lead session 2026-10-24T05:35Z to about 06:40Z (UTC). Package `/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package/`: `sha256sum -c SHA256SUMS.txt` exit 0, 41 of 41 OK.
- Read in full: the orchestration brief, the Phase 03 reviewer brief, the skeptic brief, START_HERE, EXECUTION_RULES, PHASE_INDEX, ORCHESTRATOR, the Phase 03 prompt, references GRADING_RUBRIC, RESEARCH_PROTOCOL, MIROFISH_EVALUATION, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, CANDIDATE_SEEDS, the records (HANDOFF, DECISIONS, ROADMAP), Phase 01 architecture (PLANNED_SEAMS and the rest) and Phase 02 research (SHORTLIST, LICENSE_SCAN, CANDIDATES), and all 30 reviews.

## Acceptance checklist results (ACCEPTANCE_CHECKLIST.md, written 05:46Z before any deliverable)

| Id | Result | Evidence |
|---|---|---|
| A1 package unchanged | PASS | 41 of 41 OK, exit 0 |
| A2 entry gate | PASS | `python -m pytest tests -q` at `77e78ce` with a temp `MEMELAB_DB`: exit 1, `1 failed, 858 passed in 143.26s (0:02:23)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (05:37:29Z to 05:39:53Z); stray `data/reports/20261024_0537_BRETT_0x532f.md` and sqlite shm, wal removed; DB sha256 `068287c0...` unchanged |
| A3 at least 20 pinned reviews | PASS | 30 reviews; PIN-ALL: every local clone HEAD equals its SHORTLIST pin (29 clones plus a sparse re-fetch of mlflow at `cd19153f`) |
| A4 reviews verified | PASS | `verify/verify_reviews.py`: 78 checks, 0 failed, 30 repositories covered; `verify/verify_generic.py`: 5 generic items on all 30, 0 mismatches; re-executions listed below; REVIEW_VERIFICATION.md |
| A5 rubric frozen before scoring | PASS | `research/RUBRIC_ITEMS.csv` written and hashed 05:51:03Z (sha256 `cb4b0a2112d152587424cefad98bbd8b71ae7f9ff2f1be517e47890a94c937f8`) before `SCORE_ITEMS.csv` existed; item sums equal the locked weights (checked against GRADING_RUBRIC.md by `check_scorecard.py`); file unchanged since |
| A6 uniform scoring with evidence | PASS | `SCORE_ITEMS.csv` 1,500 rows (30 x 50), points 0 or full, every point with resolvable evidence and zero notes where reviewers had proposed points; `check_scorecard.py` problems 0 |
| A7 scorecard recomputes | PASS | `check_scorecard.py` recomputes every criterion and total; reviewer columns parsed from section 6 of each review and recomputed |
| A8 top ten reproducible | PASS | eligible sort with the written tie rule reproduces `eligible_rank` and the RANKED_TOP10.md table (checked); 29 eligible, so no BLOCK |
| A9 category winners and bundle | PASS | CATEGORY_WINNERS.md: seven categories (on-chain anomaly reported as NONE verified within the event-time category), bundle with roles, decisions and license obligations |
| A10 license and security gate | PASS | LICENSE_AND_SECURITY_GATE.md: 30 rows; root license sha256 equal to Phase 02 for 30 of 30; P31, P32 sections |
| A11 challenge limitation | PASS | `SMOKES/_challenge/` holds the generator, SHA256SUMS, the CSV (444 KB, regenerated bit-identically by the lead), NOTE.md and `overlap_effect.py` (45 val and 96 train overlapping rows; largest Brier difference 0.000101); no point rests on such a metric |
| A12 MiroFish | PASS | MIROFISH.md covers scenario-only role, AGPL, LLM and Zep costs, offline mock results, non-determinism, silent success, P26 to P28, P42; no accuracy number anywhere |
| A13 blind packet | PASS | BLIND_RESCORE_PACKET.md lists seven repositories alphabetically without scores or order; `verify/make_blind_copy.sh` builds a copy without the scoring files and with reviewers' section 6 removed (tested); INDEPENDENT_RESCORE.md placeholder |
| A14 positive and negative tests | PASS | `check_scorecard.py` problems 0; `check_scorecard_negative.py` 19 of 19 mutations refused, each by its targeted rule; scenario pointers below |
| A15 hygiene | PASS | scan found one PNG (removed, sha256 `dfd0c4f9...`, kept outside the repo) and the lead's `__pycache__` (removed); no secrets, tokens, weights, tokenizer files, wheels, pickles or files over 1 MB; simulator logs hold sizes, hashes and fictional personas only |
| A16 no production code | PASS in the first pass, wrong for the committed state | changed paths only under `audits/predictive-intelligence/` and `docs/predictive-intelligence/`; final suite `1 failed, 858 passed in 135.45s (0:02:15)`, same known failure (06:31:05Z to 06:33:21Z), but it ran before the commit, while the smoke files were untracked; at `c9e894d` the content guard tests failed (`4 failed, 855 passed`, skeptic M1). Fixed in the repair pass |
| A17 spend | PASS | COST_LEDGER row for Phase 03: 0 credits; free calls listed below |
| A18 records | PASS | this file, PHASE_03_RESULTS.json, SKEPTIC_PACKET.md, ROADMAP row and Phase 03 constraints, HANDOFF rewritten, DECISIONS PI-D-026 to PI-D-028; status NEEDS_REVIEW |
| A19 writing style | PASS | scan at 06:38Z of 66 lead-written text files (all of `phase_03/` outside REVIEWS and the reviewers' smoke folders, plus the four records): 0 en or em dashes, 0 curly quotes, 0 listed marketing words |
| A20 commits | PASS | one commit with the prefix and trailers; `git status` clean afterwards; no push |

## Commands and exit codes (lead)

| Command (from `audits/predictive-intelligence/phase_03/research/` unless noted) | Exit | Result |
|---|---|---|
| `python -m pytest tests -q` (repository root, entry) | 1 | `1 failed, 858 passed in 143.26s`, known failure only |
| `<MAPIE venv> -I SMOKES/_challenge/overlap_effect.py challenge.csv` in `unshare -n` | 0 | overlap counts 45 and 96; Brier differences at most 0.000101 |
| `<purgedcv venv> -I verify/rerun_purgedcv.py ...` in `unshare -n` | 0 | 0 overlapping training rows for walk-forward, purged k-fold, CPCV, group k-fold; KFold control 111, 168, 207, 200, 111; 0 shared mints |
| `<statsmodels venv> -I verify/rerun_statsmodels.py ...` | 0 | filtered difference 0.0, smoothed 0.0186, out-of-sample predict NotImplementedError |
| `<river venv> -I verify/rerun_river.py ...` | 0 | 2,892 labels at or after maturity, 0 before, 108 flushed unmatured |
| `<pandera venv> -I verify/rerun_pandera.py ...` | 0 | legit 0 failing, late row 41 caught, trap 3,000 rows, strict refuses, raising check fails closed |
| `<stumpy venv> -I verify/rerun_stumpy.py` | 0 | stumpi left profile equals numpy past-only distance within 1.4e-13 |
| `<mlfinpy venv> -I verify/rerun_mlfinpy.py` | 0 | 3 overlapping training rows on the 6-row case |
| `bash verify/fetch_registry.sh <scratch>` (network) | 0 | TabPFN-3.5 license sha256 9570fdd6, TabPFN-2 08b1851b; hazardous 0.2.0 wheel 0c25c1b2 with the 213,846,118-byte SEER file; mlfinlab fork defect line and docstring |
| `<hazardous venv> -I verify/rerun_hazardous_timing.py ...` | 0 | fit 14.66 s at n_iter 10, 19.56 s at 20 |
| R1's feast smoke re-run in a fresh scratch directory | 0 | point-in-time table identical; 330 rows dropped |
| `python3 verify/repeat_runs.py <scratch> verify/repeat_runs.json <9 repos>` | 0 | 9 reviewer scripts re-run: identical after normalization (skore differs only in uuid7 ids and dates) |
| `python3 verify/pypi_wheels.py verify/pypi_wheels.json` (network) | 0 | K4 for 30 packages |
| `python3 -B verify/build_scorecard.py` | 0 | SCORE_ITEMS.csv and SCORECARD.csv rebuilt, no diff on rerun |
| `python3 -B verify/check_scorecard.py` | 0 | problems 0 |
| `python3 -B verify/check_scorecard_negative.py` | 0 | 19 of 19 mutations refused |
| `python3 -B verify/verify_reviews.py --json verify/VERIFY_RESULTS.json` | 0 | checks 78, failed 0, repositories covered 30 |
| `python3 -B verify/verify_generic.py --json verify/VERIFY_GENERIC.json` | 0 | award mismatches 0 |
| `python3 -B verify/sensitivity.py verify/sensitivity.json` | 0 | eight stable top-ten members under every reading |
| `python3 -B verify/counterexample_lead.py` | 0 | lead counterexample refused (problems 2) |
| `cd SMOKES/_challenge && sha256sum -c SHA256SUMS` | 0 | both OK |
| `python -m pytest tests -q` (repository root, final) | 1 | `1 failed, 858 passed in 135.45s`, known failure only |

## Sources and free calls (no billable call)

- Pinned clones of the 30 shortlisted repositories under `/home/claude/pi_research/src/` (reviewers' fetches; mlflow re-fetched sparsely by the lead from `https://github.com/mlflow/mlflow.git` at `cd19153f5ed36f40724c22d7798e65ad1c4dd7bc`).
- `https://huggingface.co/Prior-Labs/tabpfn_3_5/resolve/main/LICENSE` and `https://huggingface.co/Prior-Labs/TabPFN-v2-clf/resolve/main/LICENSE.txt` (6 reads in total).
- `https://pypi.org/pypi/hazardous/0.2.0/json` and its wheel (3 downloads, scratch only); `https://pypi.org/pypi/<name>/json` for 30 packages.
- `https://github.com/closedloop/mlfinlab.git` at `47889b884c7e7e4ca850ce2b87ea1514e0834866` (3 shallow fetches, scratch only).
- `https://github.com/666ghj/MiroFish.git`: 1 `ls-remote --tags`, 3 tag fetches (v0.1.0 2025-12-22, v0.1.1 2026-01-22, v0.1.2 2026-03-06) into the research clone; HEAD unchanged.
- No Firecrawl, WebSearch, WebFetch, LLM or paid call by the lead.

## Scenario catches with pointers

| Scenario | Caught by | Pointer |
|---|---|---|
| P13 model trained from the future applied to an old replay | (1) every smoke shows a future-available feature lifting holdout AUC to 1.0 with no library stopping it, so no library earns an availability point unless it refused the trap with declared availability (feast, pandera); (2) statsmodels Markov with full-sample parameters defines the regime from holdout data and smoothed states change when later rows are appended (0.0186) while filtered states with training-window parameters do not (SM-2), so it carries LEAKAGE_FAIL and a containment route; (3) mlflow registered the trap model as version 2 without complaint, so its replay record earns T6 only as a record the lab must check; (4) the checker refuses chronology points resting on review prose (P13 guard, mutation `m_chrono_from_prose`) | `verify/rerun_statsmodels.out.txt`, SCORECARD flags, `check_scorecard.py` |
| P26 LLM predicts a known historical headline | MiroFish and OASIS: every stage is an LLM call whose pretraining cannot be cut at a decision time; LEAKAGE_FAIL; the README's novel-ending demo marked invalid; TabPFN's pretraining data UNKNOWN, so no credit for its absence; the checker refuses any temporal point for an LLM agent simulator (mutation `m_llm_temporal`) | MIROFISH.md, `check_scorecard.py` |
| P27 agents agree 90% | MiroFish has no probability output and its ReportAgent prompt calls the simulation "the prediction of the future" (MI-2); Mesa's simulator frequency 0.22 sat next to an observed 0.07; no behavioral simulator earns a probability or calibration point (mutation `m_swarm_probability`) | MIROFISH.md, REVIEWS/mesa__mesa.md s4, `check_scorecard.py` |
| P31 AGPL code copied | MiroFish and black-it AGPL at the pin (MI-1, BI-2): L1 0, ISOLATED_RESEARCH only; mlfinpy's MIT label hides BSD-3 code without its notice (MF-2): REJECT; repository scan finds no AGPL source; mutations `m_agpl_l1`, `m_agpl_install` refused | LICENSE_AND_SECURITY_GATE.md |
| P42 candidate scores 100 on its README | README and docstring claims marked UNSUPPORTED in reviews (MiroFish "Predicting Anything", statsmodels out-of-sample docstring SM-1, MAPIE Venn-Abers docstring MA-1, feast TTL docstring, mlfinpy purge docstring MF-1) earn nothing; the checker refuses README-only evidence (mutations `m_readme_only_point` and `m_readme_hundred`, the latter a MiroFish row set to 100 from its README) | `check_scorecard_negative.py` |

## Iteration log (bounded loop)

- Pass 1 (05:35Z to 06:20Z): entry gate; checklist; challenge note and overlap check; 76 targeted checks (two failed on the lead's own string matching, mlflow strace lines and the ruptures output format, both corrected to read the right fields; no review claim failed); rubric items frozen; scoring; generic checks; first scorecard and ranking. Found: the hazardous "13 s at 10 iterations" claim was not in any raw output (lead measured 14.7 s); R1 determinism unanswered for nine repositories because reviewers had not compared repeat runs (answered uniformly by re-running their scripts); the river label-timing sentence off by one flushed label.
- Pass 2 (06:20Z to 06:35Z), lead's own adversarial pass (not independent): built a wrong-but-plausible counterexample, a consistent author awarding MAPIE the recalibration item with a real, resolvable evidence line and rebuilt ranks, which moves MAPIE to rank 1. The checker accepted it (problems 0), because it checked that evidence resolves, not that it is true. Repair: a verified-finding veto in `check_scorecard.py` binds 40 confirmed lead findings to the items they rule out; the counterexample is now refused (problems 2) and is mutation 19. Sensitivity of the cut at ten published. Hygiene scan, records, final suite.
- Remaining uncertainty: item content is verified by the 78 targeted and 150 generic checks plus the veto, not for every one of the 1,500 cells; a point whose evidence is true but over-read (for example a generic sample-weight hook counted as a decision hook) is a judgment the blind rescore and skeptic should test.

## Lead's counterexample (not independent)

`verify/counterexample_lead.py`: award `scikit-learn-contrib/MAPIE` item C2 (3 points) with evidence `SMOKES/scikit-learn-contrib__MAPIE/raw_smoke_mapie.txt Venn-Abers fit on the later calibration window (prefit)`, update its criterion and total, rebuild every rank. Before pass 2: `problems 0` (accepted, MAPIE rank 1). After: refused by `verified finding MA-1 vetoes ... C2` and `MA-2`. The independent skeptic's counterexample is still owed (PI-D-013).

## Limitations

- Every smoke ran on synthetic data; no model has shown memecoin forecast skill, and the ranking is about fitness for the pipeline.
- Scores rest partly on reviewer prose for low-risk items (for example "no install scripts"); the generic checks cover licenses, telemetry, dates, wheels and tests for all 30, and targeted checks cover the decisive items, but not every cell is independently re-derived.
- Several reviewer venvs were deleted for size (TabPFN, evidently, NannyML, mlflow, tsfresh, MiroFish, OASIS, black-it); their claims were checked against source and raw outputs, and some items stay unanswered (for example TabPFN's pandas version, I2 0).
- LightGBM results describe the 4.7.0 wheel, not a build of the pin; interpret's survival objective exists only at the pin.
- The rubric items are the lead's operationalization; contested readings are shown in RANKED_TOP10.md rather than resolved by preference.
- The reviewer files carry estimated end times (20 of 30 later than the file write); left unedited and noted.

## Blockers, approvals, next

- Blockers: the blind rescore and the skeptic review (orchestrator).
- Approvals needed: none for the repair pass. Paid LLM or Zep use, accepting non-commercial weight terms, AGPL copying, scheduled collectors and merges into `main` stay with Elving (PI-D-005).
- Next eligible phase: none until Phase 03 is PASS; then 04.

## Repair pass (2026-10-24, about 07:00Z to 07:45Z)

Inputs: the orchestrator's skeptic (`skeptic/PHASE_03_SKEPTIC.md`, scripts and outputs in `skeptic/p03/`, copied unchanged), the blind rescore (`research/BLIND_RESCORE/`, report, scores and reruns copied unchanged) and the orchestrator's own run on `c9e894d` (`4 failed, 855 passed in 154.86s`). Every finding was reproduced or checked by the lead before anything changed. Repair acceptance items, taken from the orchestrator's six instructions:

| Id | Item | Result | Evidence |
|---|---|---|---|
| RA1 | M1: no content-guard violation in any committed file; unpushed history rewritten; guard, release audit and full suite run after the commit | PASS | `bio` and `persona` strings in the two MiroFish `reddit_profiles.json` files replaced by sha256 and length (`research/SMOKES/666ghj__MiroFish/PROFILES_TRANSFORMED.txt`); `git reset --soft 77e78ce` so `c9e894d` is in no branch; `python -m memelab social guard` on the staged tree: exit 0, 955 files, 219 JSON files, `"violations": []`; post-commit results in the closing section |
| RA2 | M2: MAPIE O1 removed under the veto; D1 against crepes under one rule; re-rank | PASS | veto MA-1 and MA-4 on O1 (`verify/rerun_mapie_prefit.out.txt`: p1 0.5 where the definition gives 1.0); pass-through rule: MAPIE D1 rests on its own `BinaryRisk` (MA-5), crepes stays 0 (CR-3); MAPIE 49 to 44, 5th to 9th |
| RA3 | M3: purgedcv claims corrected with fold sizes and future rows; what rests on them rescored; checker refuses an empty or future-trained fold; the counterexample fails a check | PASS | `verify/fold_audit.py` with outputs for purgedcv, scikit-learn and sktime splitters (PC-3, SK-7, ST-3); O5 removed (purgedcv 50 to 48); PC-1 claim corrected; temporal points rest on `WalkForwardSplit` only; rule FOLD in `check_scorecard.py`; mutations `m_group_split_empty`, `m_group_split_with_audit`, `m_future_trained_t2` refused |
| RA4 | Blind rescore reconciled criterion by criterion; river LEAKAGE_FAIL scope checked at source; INDEPENDENT_RESCORE.md filled | PASS | `research/INDEPENDENT_RESCORE.md`; hazardous (+16 first pass, +11 final) resolved per criterion; river flag adopted (RV-4); MAPIE prefit finding adopted (MA-4); interpret false review claim corrected (IN-5); river crate licenses checked (RV-5) |
| RA5 | Minors m1 to m9 fixed or recorded | PASS | see the table below |
| RA6 | Skeptic and blind files copied, records updated, git status clean, no push | PASS | `skeptic/`, `research/BLIND_RESCORE/`; DECISIONS PI-D-029, PI-D-030, PI-D-026 to PI-D-028 amended; ROADMAP, HANDOFF, COST_LEDGER; commits in the closing section |

### Findings and what was done

| Finding | Lead check | Action |
|---|---|---|
| M1 content guard | reproduced: 8 violations, all `bio` in the two profile files | strings hashed (both files byte-identical before and after); PI-D-030; suite and guard run after the commit |
| M2 MAPIE O1 | MA-1 confirmed again by the lead's rerun (MA-4) | O1 0 by the veto; D1 re-anchored under the pass-through rule; rank 5 to 9 |
| M3 purgedcv | fold audit reproduces the skeptic's numbers exactly (`skeptic_purgedcv.py` rerun: identical output) | O5 0; PC-1 wording corrected ("overlap only"); route and PI-D-028 restricted to `WalkForwardSplit`; FOLD rule |
| m1 evidence rule versus checker | 343 prose-only cells counted before the repair | generic items cite `verify/VERIFY_GENERIC.json`; 7 cells moved to raw files; PROSE_OK list in the checker and PI-D-029; seeded spot audit of 20 remaining prose cells: 20 hold (`verify/prose_audit.json`); Q2's reading shown as sensitivity H |
| m2 checker gaps | all five accepted mutations reproduced | README or docs at the pin refused; T1 and T3 in the P13 guard; ANCHOR rule (a substance point must quote a token found in the cited raw file; 35 evidence strings rewritten to quote real tokens); all five now refused (`verify/skeptic_mutations_after_repair.out.txt`) |
| m3 embargo bound | placebo rerun by the lead: identical to the skeptic's | NOTE.md, RANKED_TOP10.md, REVIEW_VERIFICATION.md and ROADMAP now say "cannot inflate through label overlap; differences up to about 0.002 Brier are noise"; BLIND_RESCORE_PACKET.md gets a correction note |
| m4 hazardous C2 and O3 | lead probe: recalibration subtracts the absolute error and is unclipped (HZ-3) | C2 0 (veto HZ-3), O3 0 (veto HZ-2), C5 evidence moved to the raw field; hazardous 48 to 43 |
| m5 wrapper probabilities | sktime's own classifiers raised; probabilities from a constant dummy and a wrapped scikit-learn model (ST-4) | wrapper rule; sktime O1 0 (46 to 41), O5 re-anchored to the panel model; shown as sensitivity G |
| m6 pandera nullable | skeptic output read | Phase 05 adapter rule: availability columns non-nullable (CATEGORY_WINNERS.md, RANKED_TOP10.md) |
| m7 data rights | OASIS pickles not loaded by the package (review) | one rule (PI-D-029 item 6, license gate); OASIS gets a route-level REJECT for the pickles |
| m8 TabPFN naming | clause read in the cached license file, same sha256 `08b1851b` | license gate, CATEGORY_WINNERS.md, ROADMAP; `fetch_registry.sh` now records it |
| m9 lead above reviewers | recomputed: 21 of 30 first pass, 20 of 30 now | sentence on why in REVIEW_VERIFICATION.md and INDEPENDENT_RESCORE.md |
| Blind: river LEAKAGE_FAIL | `progressive_validation.py:138-155` learns every answer `simulate_qa` yields, flush included (RV-4) | flag and route adopted; points unchanged |
| Blind: MAPIE prefit Pipeline | lead rerun: caller predictions change by up to 0.0176, same scaler object (MA-4) | veto on O1 and Q5; route excludes it |
| Blind: interpret standard deviations | lead rerun: `standard_deviations_` finite for 6 of 6 terms (IN-5) | C5 +2 (48 to 50) |
| Blind: river crates unchecked | lead read the 96 locked crates in the local cache (RV-5) | L2 stands on new evidence |

### Commands and exit codes (repair pass, from `research/` unless noted)

| Command | Exit | Result |
|---|---|---|
| `python -m memelab social guard` (repository root, staged tree) | 0 | 955 files, `"violations": []` |
| `python tools/release_audit.py` (repository root, staged tree, before the commit) | 0 | guard 0 violations on the branch and on `origin/main`, migrations exit 0, 0 syntax errors |
| `<purgedcv venv> -I verify/fold_audit.py challenge.csv purgedcv sklearn` and `<sktime venv> ... sktime` in `unshare -n` | 0, 0 | `verify/fold_audit_purgedcv.out.txt`, `verify/fold_audit_sktime.out.txt` |
| `<purgedcv venv> -I ../skeptic/p03/skeptic_purgedcv.py challenge.csv` | 0 | identical to the skeptic's output |
| `<MAPIE venv> -I verify/rerun_mapie_prefit.py challenge.csv` | 0 | caller change 0.0176, p1 0.5 |
| `<hazardous venv> -I verify/rerun_hazardous_recal.py` | 0 | shift equals the absolute error, moves against it, mirror case down to -0.273 |
| `<interpret pin venv> -I verify/rerun_interpret_sd.py challenge.csv` | 0 | 6 of 6 finite arrays |
| `python3 -I verify/river_crate_licenses.py <river clone> <cargo cache>` | 0 | 34 crates in the normal closure, all permissive |
| `<MAPIE venv> -I ../skeptic/p03/skeptic_embargo_test.py challenge.csv` | 0 | identical to the skeptic's output (`SMOKES/_challenge/placebo_lead_rerun.out.txt`) |
| `python3 -B ../skeptic/p03/skeptic_mutations.py .` | 0 | 6 of 6 refused (5 were accepted before) |
| `python3 -B verify/build_scorecard.py` | 0 | rebuilt, no diff on rerun |
| `python3 -B verify/check_scorecard.py` | 0 | problems 0 |
| `python3 -B verify/check_scorecard_negative.py` | 0 | 31 of 31 refused |
| `python3 -B verify/verify_reviews.py --json verify/VERIFY_RESULTS.json` | 0 | checks 89, failed 0, repositories covered 30 |
| `python3 -B verify/verify_generic.py --json verify/VERIFY_GENERIC.json` | 0 | award mismatches 0 |
| `python3 -B verify/sensitivity.py verify/sensitivity.json` | 0 | seven stable members under readings A to H, the reviewers' totals and the blind scores |
| `python3 -B verify/counterexample_lead.py` | 0 | the lead's first-pass counterexample still refused |
| `cd SMOKES/_challenge && sha256sum -c SHA256SUMS` | 0 | both OK |

### Counterexamples and what catches them

- The skeptic's counterexample: `PurgedGroupKFold` by mint certified by 0 shared mints and 0 overlaps while two training folds are empty, and `PurgedKFold` and CPCV credited as leak-free while training on later rows. Caught now by the fold audit (PC-3) and rule FOLD: `m_group_split_empty` (no fold audit cited), `m_group_split_with_audit` ("a training fold has 0 rows"), `m_future_trained_t2` ("trains on 2091 rows decided after the test start"); also by the veto PC-3 on purgedcv O5.
- The lead's first-pass counterexample (a resolvable but false MAPIE C2 award) stays refused by the veto (`verify/counterexample_lead.py`).
- New in this pass, the lead's own: the skeptic's fabricated point (skore C4 citing an unrelated existing file) is refused by ANCHOR only because "0.90" does not occur in that file; a forger who quotes a token that does occur in an unrelated file would pass. The remaining defence is the targeted checks, the veto and an independent rescore; recorded as a limitation.

### Final ranking

scikit-learn 51, interpret 50, river 49, statsmodels 49, purged-cross-validation 48, LightGBM 45, pandera 44, lifelines 44, MAPIE 44, hazardous 43; next sktime 41, skore 41. Seven are stable under every reading, the reviewers' totals and the blind scores (scikit-learn, interpret, river, statsmodels, purged-cross-validation, LightGBM, lifelines). Category winners: scikit-learn (tabular), sktime (time series, design only), river (online), MAPIE (calibration), lifelines (event time; on-chain anomaly NONE verified), Mesa (behavioral), purged-cross-validation (evaluation, `WalkForwardSplit` only).

### Limitations added in the repair pass

- 241 awarded cells (318 points) still rest on review prose for the low-risk items in PROSE_OK; a 20-cell seeded audit found none wrong, which bounds but does not exclude errors.
- The ANCHOR rule checks that a quoted token occurs in the cited file, not that the file supports the claim.
- Q2 depends on its reading (main mechanism tested versus every component tested); the strict reading is published as sensitivity H, not applied.
- The fold audit covers the splitters that points rest on (purgedcv, scikit-learn, sktime) on the shared challenge only.

## Post-commit results and commits (closing section)

- Repair commit `e1b2c5e6a8aef22172261b17a5ff590df7e432d1` on top of `77e78ce` (replaces the unpushed `c9e894d`; `git for-each-ref --contains c9e894d` lists nothing).
- Full suite at `e1b2c5e`, run after the commit (07:38:22Z to 07:40:47Z, `MEMELAB_DB` in a scratch file): `python -m pytest tests -q` exit 1, `1 failed, 858 passed in 144.44s (0:02:24)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known). The three content-guard tests that failed at `c9e894d` pass. Stray `data/reports/20261024_0738_BRETT_0x532f.md` removed by hand; tracked DB sha256 `068287c0...` unchanged (`postcommit/pytest_summary.txt`).
- `python -m memelab social guard` at `e1b2c5e`: exit 0, 996 files scanned, 220 JSON files, `"violations": []` (`postcommit/social_guard.out.txt`).
- `python tools/release_audit.py --history` at `e1b2c5e`: exit 0, "Needs action: no"; no credential shapes in tracked files or in 1,602 history blobs from every ref; no trade-execution code; guard 0 violations on the branch and on `origin/main`; migrations exit 0; 352 Python files with 0 syntax errors (`postcommit/release_audit_history.summary.txt`; the full report is not stored, see the next item).
- Records commit on top of `e1b2c5e`: this section, PHASE_03_RESULTS.json (status PASS), ROADMAP, HANDOFF and DECISIONS (PI-D-030). It changes only records under `audits/` and `docs/`.
- A first version of the records commit (`1f9713c`, never pushed) stored the full release-audit report in `postcommit/`. The lead's suite run on that commit (07:43:29Z to 07:45:54Z) gave `2 failed, 857 passed`: the known failure plus `tests/test_release_tools.py::test_no_trade_execution_or_signing_code_in_tracked_files`, because the report quotes the matched rule words line by line and `audits/` is not a documented path for them. The commit was amended before any push to keep a summary instead; `release_audit.scan_exec()` on the amended tree returns no finding. The orchestrator's verification command in HANDOFF re-runs the suite and the guard on the amended records commit.

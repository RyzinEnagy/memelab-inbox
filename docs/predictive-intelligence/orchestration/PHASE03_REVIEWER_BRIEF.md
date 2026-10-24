# Phase 03 source reviewer brief (one of five parallel reviewers)

You review an assigned subset of the Phase 02 shortlist at pinned commits and write one evidence file per repo. A separate Phase 03 lead agent later applies the locked rubric across all reviews, builds the scorecard and top ten, and an independent skeptic re-scores the top five blind. You do not rank and you do not commit.

## Read first

- `/home/claude/pi_orchestration/PHASE_BRIEF.md` (lab rules, approvals, writing style; ignore its commit/report steps, this brief replaces them for you).
- Package: `/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package/phases/PHASE_03_pinned_source_audit_rubric_and_ranked_top_ten.md`, `references/GRADING_RUBRIC.md` (locked weights), `references/RESEARCH_PROTOCOL.md`, `references/MIROFISH_EVALUATION.md` (if MiroFish is yours), `references/ADVERSARIAL_SCENARIOS.md`.
- Needs: `/home/claude/memelab-inbox/audits/predictive-intelligence/phase_01/architecture/` (TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, GAP_MATRIX.csv, PLANNED_SEAMS.md) and `docs/predictive-intelligence/DECISIONS.md`.
- Your rows: `/home/claude/memelab-inbox/audits/predictive-intelligence/phase_02/research/SHORTLIST.csv` (pinned_sha, license, code_evidence, uncertainty_for_phase03, license_scan_phase03) and `LICENSE_SCAN.csv`, `CANDIDATES.csv` in the same folder.

## Environment facts

- 2 CPUs, 7 GB RAM, shared with four other reviewers: keep installs and runs small, one at a time, and clean up.
- `git clone`/`git fetch` of public repos works; the GitHub REST API and github.com pages return 403. PyPI, ecosyste.ms and WebSearch work. Python 3.11, 3.12 and 3.13 and `uv` are installed.
- Clone to `/home/claude/pi_research/src/<owner>__<repo>` and check out the pinned SHA exactly (`git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` works for most hosts). Venvs at `/home/claude/pi_research/venvs/<owner>__<repo>`. Inspect setup files before installing; never run install scripts blindly; prefer wheels; record exact installed version and whether it corresponds to the pinned SHA (a PyPI release is not the pin unless the tag matches; say which you tested). Delete the clone and venv when done if large (over 500 MB), keep the SHA and paths in your notes.
- Do not write anywhere in `/home/claude/memelab-inbox` except `audits/predictive-intelligence/phase_03/research/REVIEWS/` and `audits/predictive-intelligence/phase_03/research/SMOKES/<owner>__<repo>/`. Do not run the memelab test suite, do not commit, do not touch git there.
- No paid calls, no keys, no Firecrawl, no LLM APIs. A library that phones home (telemetry, model downloads) is a finding: run its smoke with network-sensitive behaviour noted, and check for telemetry env switches in the source.

## Shared smoke challenge (synthetic, format and behaviour only)

`/home/claude/pi_research/challenge/challenge.csv` (sha256 in `SHA256SUMS` beside it; generator `make_challenge.py`, seed 20261024). 3000 decision rows, 300 mints sharing 120 symbols, 3.8% positive rate, 107 censored rows (label empty), time split column (train/val/embargo/holdout), NaN in liq_usd and vol_24h, a TRAP column `leak_future_ret` available only 6 h after the decision (`leak_available_at`), survival columns `time_to_event_h`/`event_observed`, and a covariate shift in the holdout (liq_usd, ret_1h). Legitimate features: liq_usd, vol_24h, age_h, score100, fatal_flag, ret_1h.

Run what fits the library's role (copy the smoke script and its raw output into `SMOKES/<owner>__<repo>/`; record command, exit code, wall time, peak RSS via `/usr/bin/time -v` if present, else `resource`):
- S1 leak trap: does the library offer any mechanism that would exclude a feature by availability time or enforce time-ordered splits with gap/embargo/group purging? Show a run where including the trap column inflates holdout metrics, and whether anything in the library stops it (usually nothing, which means the wrapper must).
- S2 probability shape and imbalance: finite probabilities in [0,1], shape, Brier and log loss on holdout vs the train-prevalence baseline, with censored rows excluded (never scored as negatives).
- S3 missing covariates: native NaN handling or required imputation.
- S4 calibration or uncertainty: what the library offers (isotonic, Platt, Venn-Abers, conformal sets/intervals, quantiles), coverage on holdout where applicable.
- S5 persistence: save, reload, identical predictions; format (pickle, native text, ONNX) and its safety.
- S6 cost: fit time, predict latency per row, memory, offline operation (no network needed at import/fit/predict), Python 3.13 and Windows wheel availability (from PyPI file list).
- Role-specific: survival libraries fit time-to-barrier with censoring and report a censor-aware metric; drift/monitoring libraries detect the holdout shift and report false alarms on train vs val; time-series libraries show their time-aware CV/backtest splitter and whether it supports irregular timestamps and many short series; experiment/audit libraries show run lineage and whether they make network calls; simulators run the smallest offline example possible (a mock LLM endpoint on localhost is allowed for MiroFish/OASIS if the code supports a base URL; never a real key).
A skipped smoke is recorded as SKIPPED with the reason, never as passed.

## One review file per repo: `REVIEWS/<owner>__<repo>.md`

Sections, in order:
1. Identity: canonical repo, URL, pinned SHA, commit date, how fetched, UTC review time, version tested and its relation to the pin.
2. License and security: root LICENSE (verify text at pin), per-file or vendored licenses found, key transitive dependency licenses, model-weight terms (if weights are downloaded: where from and under what terms; unreadable terms = UNKNOWN), install-time scripts, network calls at import or runtime, telemetry and how to disable it, secrets handling.
3. Code paths inspected at the pin: file:line anchors for the training/fit path, prediction/probability path, time handling and splitters, calibration/uncertainty, serialization, and tests (count of test files; run a small subset of the repo's own tests if cheap and record the result).
4. Smoke results (table: S1..S6 plus role-specific, each PASS/FAIL/SKIPPED with numbers and the path to raw output).
5. README or docs claims that the code does not support: list them as UNSUPPORTED (P42).
6. Proposed rubric scores, one row per locked criterion (temporal integrity 18, transferable outcomes 14, calibration 12, catalyst/social/on-chain features 10, decision/execution compatibility 10, code quality 8, integration fit 8, reproducibility 8, cost/latency 5, licensing/security 7), each with the evidence line it rests on. No evidence = 0. Do not round up. Total.
7. Flags: REJECT / RESEARCH_ONLY / NOT_REALTIME / LEAKAGE_FAIL with reasons; adversarial scenarios touched (P13, P26, P27, P31, P32, P42 where relevant).
8. Proposed role in the memelab system and candidate INTEGRATION_DECISION (INSTALL, ADAPTER, INSPIRED_IMPLEMENTATION, ISOLATED_RESEARCH, REJECT), and which Phase 01 gap cells it addresses.

Write plainly, no em dashes, no marketing words. Never invent a number, path or license; UNKNOWN is a valid answer.

## Your reply to the orchestrator

Under 250 words: repos reviewed, files written, total proposed scores per repo, flags, anything that blocked a smoke, and any environment problem the lead should know.

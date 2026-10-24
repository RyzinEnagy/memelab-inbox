# Phase 03 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). Task: falsify Phase 03 (pinned source audit, rubric and ranked top ten). This packet lists artifacts, code paths and commands; it states no conclusions to accept. Read `/home/claude/pi_orchestration/SKEPTIC_BRIEF.md`, the phase prompt `phases/PHASE_03_pinned_source_audit_rubric_and_ranked_top_ten.md`, `EXECUTION_RULES.md`, `references/GRADING_RUBRIC.md`, `RESEARCH_PROTOCOL.md`, `MIROFISH_EVALUATION.md`, `ADVERSARIAL_SCENARIOS.md`, and `docs/predictive-intelligence/DECISIONS.md` (PI-D-024 to PI-D-028).

The blind second rescore of the top five is a separate task with its own packet: `research/BLIND_RESCORE_PACKET.md`. If you also act as that reviewer, do the blind rescore first, before opening the scoring files listed there.

## Artifacts (paths relative to `audits/predictive-intelligence/phase_03/`)

- `ACCEPTANCE_CHECKLIST.md` (A1 to A20, written before any deliverable)
- `research/REVIEWS/*.md` (30, by reviewers R1 to R5) and `research/SMOKES/<owner>__<repo>/` (scripts and raw outputs), `research/SMOKES/_challenge/` (generator, SHA256SUMS, challenge.csv, NOTE.md, overlap_effect.py and output)
- `research/RUBRIC_ITEMS.csv` (the lead's items), `research/SCORE_ITEMS.csv` (30 x 50 rows), `research/SCORECARD.csv`
- `research/RANKED_TOP10.md`, `research/CATEGORY_WINNERS.md`, `research/LICENSE_AND_SECURITY_GATE.md`, `research/MIROFISH.md`, `research/REVIEW_VERIFICATION.md`, `research/INDEPENDENT_RESCORE.md` (placeholder), `research/BLIND_RESCORE_PACKET.md`
- `research/verify/`: `score_inputs.py` (every award and its evidence), `build_scorecard.py`, `check_scorecard.py`, `check_scorecard_negative.py`, `verify_reviews.py` and `VERIFY_RESULTS.json`, `verify_generic.py` and `VERIFY_GENERIC.json`, `sensitivity.py` and `sensitivity.json`, `pypi_wheels.py` and `pypi_wheels.json`, `repeat_runs.py` and `repeat_runs.json`, `rerun_*.py` with their `.out.txt`, `fetch_registry.sh` with `registry/*.txt`, `closure_size.py`, `make_blind_copy.sh`
- `PHASE_03_EVIDENCE.md`, `PHASE_03_RESULTS.json`

## External state the claims rest on

- Pinned clones: `/home/claude/pi_research/src/<owner>__<repo>` (mlflow is a sparse blob-less fetch of a few files at its pin); reviewers' venvs: `/home/claude/pi_research/venvs/` (several large ones were deleted by the reviewers; see each review's identity table).
- Shortlist and pins: `audits/predictive-intelligence/phase_02/research/SHORTLIST.csv`, `LICENSE_SCAN.csv`, `CANDIDATES.csv`.
- Needs: `audits/predictive-intelligence/phase_01/architecture/` (TARGET_REGISTRY.md, ACCEPTANCE_METRICS.md, PLANNED_SEAMS.md, GAP_MATRIX.csv).

## Commands to reproduce (run from your own clone, `research/` as the working directory where relative)

```
python3 -B verify/build_scorecard.py            # rebuilds SCORE_ITEMS.csv and SCORECARD.csv; diff against the committed files
python3 -B verify/check_scorecard.py            # expect: problems 0
python3 -B verify/check_scorecard_negative.py   # expect: 19 of 19 mutations refused
python3 -B verify/verify_reviews.py             # expect: checks 78, failed 0 (needs the pinned clones)
python3 -B verify/verify_generic.py             # expect: award mismatches 0
python3 -B verify/sensitivity.py /tmp/x.json    # top ten under alternative readings
<purgedcv venv python> -I verify/rerun_purgedcv.py SMOKES/_challenge/challenge.csv
<statsmodels venv python> -I verify/rerun_statsmodels.py SMOKES/_challenge/challenge.csv
<MAPIE venv python> -I SMOKES/_challenge/overlap_effect.py SMOKES/_challenge/challenge.csv
cd SMOKES/_challenge && sha256sum -c SHA256SUMS
python -m pytest tests -q                        # from the repository root; temp MEMELAB_DB
```

## Questions worth attacking

- Are the 50 items a fair and uniform reading of the locked rubric, or do they quietly favour some tool families (for example the code-anchored D1 sample-weight item, or O1 for calibrator outputs)? Were they really written before scoring (compare the RUBRIC_ITEMS.csv sha256 in PI-D-026 with the file, and the file's history)?
- Pick awards in `verify/score_inputs.py` and check the evidence yourself against the pin or the raw output; look especially at the top ten and at the 9th to 11th places (MAPIE, pandera, lifelines).
- Does any point rest on a holdout metric that the challenge's short embargo band could have inflated, or on synthetic skill?
- Is any REJECT unjustified, or any repository that should be REJECT left eligible (licenses, weights, data rights, telemetry, install behaviour)?
- Are the MiroFish statements (no probability output, AGPL scope, silent success when the LLM is down, non-determinism, P26 to P28) supported by its pinned code and the smoke outputs, and does any deliverable assign it numerical accuracy?
- Are the checkers able to fail (mutate the real files and see), and do the positive results depend on anything outside the committed files and the pinned clones?
- Construct one new wrong-but-plausible counterexample and show which check catches it, or that nothing does.

## Outcome (repair pass)

The skeptic's report is `skeptic/PHASE_03_SKEPTIC.md` with its scripts and outputs in `skeptic/p03/`; the blind rescore is in `research/BLIND_RESCORE/`. Each finding was verified by the lead before acting on it; what changed and why is in `PHASE_03_EVIDENCE.md` (repair pass section), `research/INDEPENDENT_RESCORE.md`, `research/REVIEW_VERIFICATION.md` and PI-D-029 and PI-D-030. The skeptic's counterexample (a group split certified by overlap counts alone) and its five accepted mutations are now refused by `verify/check_scorecard.py` (`verify/check_scorecard_negative.py`, 31 of 31; the skeptic's own script rerun on the repaired files: `research/verify/skeptic_mutations_after_repair.out.txt`).

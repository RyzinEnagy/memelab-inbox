# Phase 01 acceptance checklist (written before any change)

Written 2026-10-24T01:31Z, after the entry gate and the read-only universe probe, before any deliverable, code or GeckoTerminal call. Each item is falsifiable; the evidence file records the command and result for each.

| Id | Check | How it is verified | Fails if |
|---|---|---|---|
| C1 | Package unchanged | `sha256sum -c SHA256SUMS.txt` in the package folder | any line not OK |
| C2 | Entry gate | `python -m pytest tests -q` at `94be1bf`, checkout clean | anything other than `1 failed, 785 passed` with only `test_dedup_corroboration_resurface_denial` failing |
| C3 | Predecessor key check (PI-D-011) | decision_universe_probe.py: first-thesis write lag over all exports | not 149 mints with median about 16.9 min and max 116.5 min |
| C4 | Gap matrix covers every cell with code evidence | `architecture/GAP_MATRIX.csv`: every facility x need cell has one of VERIFIED_PRESENT, PARTIAL, MISSING, CONFLICT, UNKNOWN and an anchor; anchors checked by `probes/check_gap_anchors.py` (file exists, line in range, keyword on or near the line) | a missing cell, a status outside the set, or an anchor that does not resolve |
| C5 | Targets pre-registered before outcome data are seen | `architecture/TARGET_REGISTRY.md` plus the machine-readable registry in `memelab/predictive/contract.py`; its sha256 and UTC time recorded before the GeckoTerminal sample probe runs; probe reports coverage only, no barrier outcome | registry written or changed after outcome data were read, or fewer than 2 / more than 4 primary targets, or a target lacks eligibility, decision time, entry, barriers, tie rule, classes, pending and censored rules, dead or unquoted handling, size assumption, pool route, timestamps, first availability |
| C6 | Feasibility rests on real timestamped data | event counts from the 89 exports (probe output sha256); GeckoTerminal coverage on a seeded sample with retrieval times; infeasible targets named with the missing data | a feasibility claim without a count or retrieval record, or an executable (exit-adjusted) target marked feasible without historical depth (P08) |
| C7 | Acceptance plan fixed before modeling | `architecture/ACCEPTANCE_METRICS.md`: OOS windows with dates, minimum event counts, baselines, primary proper score, calibration tolerance with support, abstention policy, wording rules, latency and cost limits, plain statement of what the data cannot support | any of these missing, or any model fitted in this phase |
| C8 | Placement with no duplicate subsystem | `architecture/PLANNED_SEAMS.md`: each seam names the existing code reused (file:line); ranker, fatal flags and existing output unchanged; flag default OFF; BACKTEST_NOT_AVAILABLE; degradation on source outage | a planned loader, outcome store, registry or renderer that duplicates an existing one without a stated reason |
| C9 | Dependency order frozen | `architecture/DEPENDENCY_GRAPH.md` | labels before training, baseline before complex models, MiroFish comparison before any improvement claim not stated |
| C10 | Contract example and validator | `contract/FORECAST_EXAMPLE_FORMAT_ONLY.json` (one ABSTAIN, one well-formed forecast, marked format only); `memelab/predictive/contract.py`; `tests/test_predictive_contract.py` covering P05, P08, P34, P46 (and P38) | a test fails, or the example is presented as a result |
| C11 | Flag OFF and isolation | test that no existing module imports `memelab.predictive` and the flag defaults to OFF; full suite shows only the known failure | an existing module imports it, or a new failure appears |
| C12 | Tracked data untouched | `git status`, `git diff --name-only 94be1bf..HEAD`, sha256 of `data/memelab.sqlite` | any change under `inbox/`, `state/`, `data/`, or a stray left behind |
| C13 | Records and status | evidence, results JSON (parses), skeptic packet, ROADMAP row, DECISIONS ids, HANDOFF rewritten; status NEEDS_REVIEW until the orchestrator's skeptic is folded in (PI-D-013) | any missing |
| C14 | Writing style | grep for em and en dashes in every file this phase writes | a hit |
| C15 | Spend | COST_LEDGER.md; free calls listed in evidence | a billable call not logged |

## Corrections (repair pass 2, appended; the rows above are kept as written)

- C10 named `contract/FORECAST_EXAMPLE_FORMAT_ONLY.json`; the delivered file is `tests/fixtures/predictive/forecast_examples_format_only.json` (skeptic M8). The empty `contract/` folder was removed.
- C5 and C7 are now checked against the CC-02 fingerprint, which covers every acceptance rule (skeptic F2); `tests/test_predictive_contract.py` pins it and checks the document's frozen block.
- Added for repair pass 2: C16, decision records are point-in-time (`tests/test_predictive_decisions.py`, built from skeptic counterexample CX-S1); C17, eligibility gaps are classified and counted (`contract.eligibility`, F3); C18, holdout decisions already contacted are listed and excluded (M7).

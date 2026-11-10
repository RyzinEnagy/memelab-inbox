# Daily cycle: the prediction-before-outcome procedure (CM-2, PI-D-122, PI-D-125)

This is the procedure the daily cycle of recipe R-CM2-1 follows. The code is `predictive_daily.py` in this folder, frozen at `e79d846`; the rule is `contract.PROMOTION_CM2` (governing fingerprint `b88f0058...`, pinned in the script and in `tests/test_predictive_contract.py`). Research only: nothing is published, traded or sent.

## The command

```
python -B audits/predictive-intelligence/daily/predictive_daily.py run
```

Run from the root of a full clone (not shallow: the recipe freeze is the commit time of `RECIPE.json`, read from git history) of branch `feature/predictive-intelligence` at or after the CM-2 commits. Needs Python 3.13 with numpy, git, and outbound HTTPS to github.com (one `git fetch origin main`) and api.geckoterminal.com (free, no key). No secret, no paid call.

## Order of one run (each step refuses to start if the one before failed)

1. Lock and preflight: the recipe file and the governing fingerprint equal their pins; the ledger verifies (sha chain); an interrupted run's leftovers are accepted only if they are an append of the committed ledger.
2. Exports: `git fetch origin main`, then the store is rebuilt from the state exports up to `origin/main` (exports and feature snapshots only, no candle) in the private state folder `data/private/predictive_daily/` (git-ignored).
3. Predictions: for every Solana decision strictly after the recipe freeze that the ledger does not hold, one PREDICTION per target (3) and kind (B0, B2): a number from the version in force (registered at or before the decision, cutoff before it, not stale) or an abstention with its reason (MODEL_NOT_SELECTED, MODEL_STALE, MISSING_REQUIRED_INPUT, OOD).
4. Commit: the ledger is committed (paths under this folder only), and the run checks that `HEAD` holds every prediction before any label read. If it does not, the run stops with PREDICTION_COMMIT_FAILED and reads nothing.
5. Labels: only for predicted decisions whose targets have matured; free GeckoTerminal, `token=<mint>`, end-time boundary of the frozen labels-1 rules, paced by `runtime.CallGuard` at 5.7 calls a minute (a run that sees more than 6 in any 60 s stops), at most 60 calls and 25 minutes, raw bodies gzip-archived with sha256 in `raw/`, every call in `CALLS.jsonl`, one line in `../COST_LEDGER.md`.
6. Outcomes: appended to the ledger after the predictions (labels-1 through `monitoring.prospective_records`); PENDING and NOT_READ are non-final and are superseded by a later outcome.
7. Windows: `promotion.next_window` and `promotion.evaluate_window` per target and kind; a closed window's result is appended once as a WINDOW_RESULT and never recomputed. Admissibility needs, for every scored row: decision after the freeze, prediction before outcome in the ledger, the commit time of the first ledger commit holding the prediction before the outcome's `label_observed_at`, version registered at or before the decision and not stale.
8. Retrain: when the newest version is 7 days past its cutoff and a label matured after it, the same recipe is refit as a new version and registered; otherwise the alert says NO_NEW_MATURED_LABELS.
9. `ALERT_SUMMARY.txt`, `STATUS.json`, one line in `RUNS.jsonl`; commit.

## What a run writes and commits

Only `audits/predictive-intelligence/daily/` (LEDGER.jsonl, READS.jsonl, CALLS.jsonl, LABEL_ROWS.jsonl, raw/, cards/, registry/, RUNS.jsonl, STATUS.json, ALERT_SUMMARY.txt), one line in `audits/predictive-intelligence/COST_LEDGER.md` when it made calls, and the git-ignored private folder. A change anywhere else stops the run with WRITE_OUTSIDE_ALLOWED_PATHS. The script never pushes.

## Exit codes

0 OK; 2 LOCKED; 3 PREFLIGHT_FAILED; 4 EXPORT_FETCH_FAILED; 5 PREDICTION_COMMIT_FAILED; 6 LABEL_FETCH_FAILED; 7 LEDGER_REFUSED; 8 TIME_BUDGET_EXCEEDED; 9 RETRAIN_FAILED; 10 COMMIT_FAILED; 11 WRITE_OUTSIDE_ALLOWED_PATHS; 1 UNEXPECTED_ERROR. The reason is on stderr and in `ALERT_SUMMARY.txt`.

## Why the commits must be pushed

A commit time is set by the machine that commits. The ledger's discipline (prediction committed before its outcome is read) is checked from git, so the commits must reach a place with its own clock and must survive the run: a cloud task starts from a fresh clone each time, and a ledger that is not pushed is lost and the next run predicts again from nothing. The scheduled task therefore pushes the branch it ran on after every run, fast-forward only, never `main`, never with force (PI-D-125). GitHub's record of the push is the independent time anchor; the skeptic packet lists this as a limitation until a push has happened.

## State on 2026-11-10

Cards R-CM2-1 v1 (cutoff 2026-10-28T10:43:04Z) go MODEL_STALE at 2026-11-11T10:43:04Z. No state export exists on `origin/main` after `71fc50e` (2026-10-26), so no decision after the freeze exists, the first window has 0 events, and every level is ABSTAIN. When exports resume, the first days after 2026-11-11 abstain as MODEL_STALE until their labels mature and a retrain registers version 2.

# Daily cycle: the prediction-before-outcome procedure (CM-2, PI-D-122, PI-D-125, PI-D-140)

This is the procedure the daily cycle of recipe R-CM2-1 follows. The code is `predictive_daily.py` in this folder, frozen at `e79d846`; the rule is `contract.PROMOTION_CM2` (governing fingerprint `b88f0058...`, pinned in the script and in `tests/test_predictive_contract.py`). Research only: nothing is published, traded or sent.

## The command

```
python -B audits/predictive-intelligence/daily/predictive_daily.py run
```

Run from the root of a full clone (not shallow: the recipe freeze is the commit time of `RECIPE.json`, read from git history) with the branch `feature/predictive-intelligence` checked out (a run refuses any other HEAD). The script pushes that branch to `origin` itself (PI-D-140), so the clone needs push access to GitHub. Needs Python 3.13 with numpy, git, and outbound HTTPS to github.com (one `git fetch origin main`) and api.geckoterminal.com (free, no key). No secret, no paid call.

## Order of one run (each step refuses to start if the one before failed)

1. Lock and preflight: the recipe file and the governing fingerprint equal their pins; the ledger verifies (sha chain); an interrupted run's leftovers are accepted only if they are an append of the committed ledger.
2. Exports: `git fetch origin main`, then the store is rebuilt from the state exports up to `origin/main` (exports and feature snapshots only, no candle) in the private state folder `data/private/predictive_daily/` (git-ignored).
3. Predictions: for every Solana decision strictly after the recipe freeze that the ledger does not hold, one PREDICTION per target (3) and kind (B0, B2): a number from the version in force (registered at or before the decision, cutoff before it, not stale) or an abstention with its reason (MODEL_NOT_SELECTED, MODEL_STALE, MISSING_REQUIRED_INPUT, OOD).
4. Commit and push: the ledger is committed (paths under this folder only), and the run checks that `HEAD` holds every prediction. Then, before any label call, it pushes `HEAD` to `origin` on `feature/predictive-intelligence` (fast-forward only, never force, never another branch) and checks that the remote ref equals `HEAD` (PI-D-140). If either fails, the run stops with PREDICTION_COMMIT_FAILED or PREDICTION_PUSH_FAILED and reads nothing.
5. Labels: only for predicted decisions whose targets have matured; free GeckoTerminal, `token=<mint>`, end-time boundary of the frozen labels-1 rules, paced by `runtime.CallGuard` at 5.7 calls a minute (a run that sees more than 6 in any 60 s stops), at most 60 calls and 25 minutes, raw bodies gzip-archived with sha256 in `raw/`, every call in `CALLS.jsonl`, one line in `../COST_LEDGER.md`.
6. Outcomes: appended to the ledger after the predictions (labels-1 through `monitoring.prospective_records`); PENDING and NOT_READ are non-final and are superseded by a later outcome.
7. Windows: `promotion.next_window` and `promotion.evaluate_window` per target and kind; a closed window's result is appended once as a WINDOW_RESULT and never recomputed. Admissibility needs, for every scored row: decision after the freeze, prediction before outcome in the ledger, the commit time of the first commit whose ledger holds that exact prediction line (by content) before the outcome's `label_observed_at`, version registered at or before the decision and not stale. Every committed ledger must be an append of the one in the commit before it; if any is not, no prediction has an anchor and every window is WINDOW_NOT_ADMISSIBLE (LEDGER_HISTORY_NOT_APPEND_ONLY, PI-D-140). A reference (B0, B2) is never SHADOW; a CANDIDATE kind that reaches SHADOW is written as a PROMOTE event and a CHAMPION pin.
8. Retrain: when the newest version is 7 days past its cutoff and a label matured after it, the same recipe is refit as a new version and registered; otherwise the alert says NO_NEW_MATURED_LABELS.
9. `ALERT_SUMMARY.txt`, `STATUS.json`, one line in `RUNS.jsonl`; commit; push again (PUSH_FAILED if it fails).

## What a run writes and commits

Commits: only `audits/predictive-intelligence/daily/` (LEDGER.jsonl, READS.jsonl, CALLS.jsonl, LABEL_ROWS.jsonl, raw/, cards/, registry/, RUNS.jsonl, STATUS.json, ALERT_SUMMARY.txt), one line in `audits/predictive-intelligence/COST_LEDGER.md` when it made calls, and the git-ignored private folder. A change anywhere else stops the run with WRITE_OUTSIDE_ALLOWED_PATHS. Pushes: only `feature/predictive-intelligence` to `origin` (PI-D-140).

## Exit codes

0 OK; 2 LOCKED; 3 PREFLIGHT_FAILED (also: not on the branch, `--max-calls` above 60, `--now` without the test clock); 4 EXPORT_FETCH_FAILED; 5 PREDICTION_COMMIT_FAILED; 6 LABEL_FETCH_FAILED; 7 LEDGER_REFUSED; 8 TIME_BUDGET_EXCEEDED; 9 RETRAIN_FAILED; 10 COMMIT_FAILED; 11 WRITE_OUTSIDE_ALLOWED_PATHS; 12 PREDICTION_PUSH_FAILED; 13 PUSH_FAILED; 1 UNEXPECTED_ERROR. The reason is on stderr and in `ALERT_SUMMARY.txt`.

## Why the commits are pushed before the reads

A commit time is set by the machine that commits. The push after the prediction commit and before the first label call puts the predictions on GitHub, whose own record of the push is the independent time anchor that the predictions existed before any outcome was read; a push only at the end of a run would bound the run, not the order inside it (skeptic finding 2). A cloud task also starts from a fresh clone, so an unpushed ledger would be lost.

## State on 2026-11-10

Cards R-CM2-1 v1 (cutoff 2026-10-28T10:43:04Z) go MODEL_STALE at 2026-11-11T10:43:04Z. No state export exists on `origin/main` after `71fc50e` (2026-10-26), so no decision after the freeze exists, the first window has 0 events, and every level is ABSTAIN. When exports resume, the first days after 2026-11-11 abstain as MODEL_STALE until their labels mature and a retrain registers version 2.

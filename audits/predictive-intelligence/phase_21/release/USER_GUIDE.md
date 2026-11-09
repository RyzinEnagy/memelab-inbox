# User guide (research only)

The predictive engine is a research tool. It never places an order, signs anything, reads a key, sends an alert or calls a paid service. On 2026-11-09 it has no validated model: every target ABSTAINS and no probability is shown (`MODEL_LIMITS.md`). The commands below were run in Phase 21 (`evidence/doc_commands/doc_commands.txt`, `evidence/release_checks/`, `evidence/maturity/`) unless a line says otherwise.

## 1. Turning the flag on in a sandbox

Never in your working checkout. Make a sandbox clone, a lab database outside the repository, and a state folder outside the repository (or under `data/private/`; anything else is refused, STATE_DIR_REFUSED).

```
git clone /path/to/memelab-inbox /tmp/pi_sandbox && cd /tmp/pi_sandbox
git checkout feature/predictive-intelligence
printf '{"predictive": {"enabled": true, "state_dir": "/tmp/pi_state", "mode": "fast"}}\n' > data/config.json
python -c "import json; json.load(open('data/config.json'))"
MEMELAB_DB=/tmp/pi_lab.sqlite python -B -m memelab init
MEMELAB_DB=/tmp/pi_lab.sqlite python -B -m memelab.state import /path/to/latest_export.json
MEMELAB_DB=/tmp/pi_lab.sqlite python -B -m memelab scout --mints MINT1 MINT2 --results RESULT_IDS --stage1 disc01 --report-dir /tmp/pi_reports
```

This is the sequence of the real-path smoke (`phase_17/probes/real_path_smoke.sh`, run in Phase 21 on the 71fc50e export, 8 mints): the scout report body is byte-identical to the flag-off run and a section "Predictive research section" is appended in which every target ABSTAINS with its reasons. `analyze MINT` prints one extra line, for example `predictive: DISCOVERY ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED, SOURCE_STALE, UNCALIBRATED) | snapshot ... | research only, not advice`. `mode` `research` also writes internal B0 and B2 reference records (never shown as documents).

With the flag on, no vendor call is made: the engine reads a reference price only for a served champion (none exists), and the scout and analyze hooks pass no reader. Eligibility shows NOT_ASSESSED, or INPUT_STALE when the scout's inputs are older than 2 hours (as in the smoke, which replays October bodies).

Inspect and check the state:

```
python -B -m memelab.predictive.integration status --state-dir /tmp/pi_state --config data/config.json
python -B -m memelab.predictive.integration check --state-dir /tmp/pi_state --config data/config.json
```

`check` exits 0 with `"problems": []` when every document has its abstention record and its request, and the hash chain holds. A damaged state gives problems (exit 1) or STATE_TAMPERED (exit 2); see `ROLLBACK_PROOF.md`.

Reports and alert previews (dry run only; `--send` is refused because no delivery is approved):

```
python -B -m memelab.predictive.reports report --state-dir /tmp/pi_state --config data/config.json --lab-db /tmp/pi_lab.sqlite --registry-dir audits/predictive-intelligence/phase_16/registry --out /tmp/pi_private/report.md
python -B -m memelab.predictive.reports alerts --state-dir /tmp/pi_state --config data/config.json --alert-db /tmp/pi_private/alerts.sqlite --outbox /tmp/pi_private/outbox --lab-db /tmp/pi_lab.sqlite --registry-dir audits/predictive-intelligence/phase_16/registry
python -B -m memelab.predictive.reports alerts-state --alert-db /tmp/pi_private/alerts.sqlite --config data/config.json
```

With the flag off each of these prints `predictive: FLAG_OFF` and reads nothing.

Turning it off: delete `data/config.json` in the sandbox (or set `enabled` to false). Throw the sandbox, the state and the lab database away when done.

## 2. Reading the section

- ABSTAIN is the normal answer. The reasons are codes: MODEL_NOT_SELECTED (no champion in the registry), UNCALIBRATED (no calibration card passed), INSUFFICIENT_HISTORY, SOURCE_STALE (no fresh read), MODEL_STALE (the card is older than 14 days), BACKTEST_NOT_AVAILABLE, EXECUTION_DATA_MISSING.
- No base rate, reference-model number, Brier or skill number is ever shown for an abstaining target.
- Risk overrides any forecast: lab fatal flags, a liquidity fall of 20% or more, a newer unassessed snapshot.
- Token text that carries a trading word or a multiplier is withheld.

## 3. Prospective tracking (Phase 19)

The outcome ledger is `audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl`, append-only, read and written only through `memelab/predictive/monitoring.py`. The plan is `phase_19/monitoring/PROSPECTIVE_PLAN.md`.

Maturity run for already predicted decisions (in the working checkout; it appends only):

```
python -B audits/predictive-intelligence/phase_19/probes/fetch_labels.py fetch
python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py outcomes
python -B audits/predictive-intelligence/phase_19/probes/run_prospective.py evaluate OUTDIR
```

`fetch` uses free GeckoTerminal reads at no more than 5.7 a minute (at most 300 for the phase), every read logged. `outcomes` appends OUTCOME entries that supersede PENDING ones; it never edits a line. Write `evaluate` output to a new dated folder, never over the committed one, and commit it with the ledger. Run on 2026-11-09: 0 reads planned, 0 entries appended, verdicts unchanged (`evidence/maturity/`). Known gap OI21-1: the 7 T2 outcomes of 2026-10-26 stay PENDING because `fetch` skips decisions that already have a read; maturing them needs a change control to `fetch_labels.py`.

`drift` (`run_prospective.py drift OUTDIR`) appends MONITOR and RESPONSE entries to the committed ledger whatever OUTDIR is (F20-14): run it in a sandbox clone unless the run is a planned maturity run you commit.

New decisions (exports after 2026-10-26) need their own predictions commit before any label is read: `run_prospective.py inputs`, `predict`, a new PREDICTION_SET, a commit, then the reads. A decision after 2026-10-31T00:00:00Z is MODEL_STALE for every frozen card, so new prospective evidence needs retrained reference cards first (section 5).

## 4. Frozen re-reads

- Same-session revision check: `fetch_labels.py reread` (the lowest 10% of read URLs by sha256).
- The frozen 48 h re-read (PI-D-018, PI-D-106): `python -B audits/predictive-intelligence/phase_19/probes/fetch_labels.py reread48`. It refuses to run earlier than 48 h after each sample read. A changed label becomes a revision entry citing the new read; both are kept. It ran on 2026-10-29 (orchestrator): 3 checks, 2,996 candles, 0 changed, 0 revised (`phase_19/evidence/revision_reread_48h.json`, PI-D-112). It was not rerun in Phase 21 (it would make new vendor calls and its sample is done).

## 5. Retiring stale cards

The 69 frozen cards (cutoff 2026-10-17) are MODEL_STALE after 2026-10-31T00:00:00Z. Nothing needs to be done for safety: `registry.status_at` marks every one MODEL_STALE and `registry.serve` uses no champion, so every request abstains (`evidence/doc_commands/docs_demo.json`: 69 of 69 MODEL_STALE at 2026-11-09, level ABSTAIN for all three targets).

They stay listed as the B0 and B2 references because registry-1 requires both references on every pin: a pin without them is refused (`docs_demo.json`, "references must be ..."). So there are two ways to retire them, both a decision (ED-10):

1. Replace them (the honest route for new prospective evidence): commit a retrain plan before any evaluation data are read; fit new B0 and B2 cards only through `labels.training_labels` with a new cutoff; register them as new entries at ABSTAIN; append a NO_VIABLE_CHAMPION pin naming the new references with `registry.append_events`; add the new configurations to the search ledger (N_search grows). `phase_16/probes/build_registry.py` is the pattern.
2. Remove references altogether: a change control to registry-1 with tests.

## 6. Rollback

See `ROLLBACK_PROOF.md`. In short: flag off returns the original report byte for byte; a registry rollback appends an event and never edits one; the predictive state can be deleted without touching the lab.

## 7. Policies

- Data refresh: the engine reads the lab's state exports (scheduled commits on `main`) and, for labels, free GeckoTerminal reads made by the Phase 19 commands. No crawler or schedule runs for it (PI-D-005).
- Retrain cadence: none automatic. A retrain is a phase step with a committed plan; a DRIFT_ALERT never retrains anything, it demotes, rolls back or keeps abstention.
- Maintenance owner: Elving decides (`OPEN_DECISIONS.md`); code changes go through a phase with a change control, a test that fails on the old code, and the independent skeptic.

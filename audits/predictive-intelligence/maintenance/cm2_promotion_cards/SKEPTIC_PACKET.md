# CM-2 skeptic packet

For an independent reviewer. It lists what to attack, where things are and how to reproduce them. It holds no conclusions; read the evidence and decide for yourself.

## Task

Try to show that CM-2 (PI-D-122 to PI-D-127) does any of the following:

1. Loosens a frozen minimum or correction of ACCEPTANCE, or lets anything other than an admissible prospective window promote (compare `contract.PROMOTION_CM2` with `ACCEPTANCE`; read `promotion.py` against the table in `CHANGE_CONTROL.md` Part A).
2. Lets a prediction be scored when it was not committed to git before its outcome was read, or when the card version was registered after, or stale at, the decision.
3. Changed frozen code after the freeze without a recorded change control: the code commit is `e79d846`, made before any label read or fit. Check that `memelab/` and `build_cm2.py` are unchanged since then, that `predictive_daily.py` changed only by PI-D-128, and that every later test or probe change has a change control (PI-D-124, PI-D-126, PI-D-129); in particular whether PI-D-129 item 2 weakens the Phase 16 tests (`tests/test_predictive_integration.py` g22, `tests/test_predictive_phase16_outputs.py` cp16_2, `tests/test_predictive_reproductions.py` Phase 16).
4. Read labels against the frozen rules: not `token=<mint>`, a wrong boundary (T2 window end on the candle grid), more than 6 calls in any 60 s, a paid route, or an unlogged call. One read happened before a session restart; check `evidence/interruption.json` against the raw body and the plan.
5. Fitted the fresh cards on something other than what `RECIPE.json` names (splits, cutoff, configurations), searched (N_search must stay 130), or produced cards that a second fit does not reproduce byte for byte.
6. Deleted or edited a Phase 16 registry entry or log, or registered a fresh card at a level other than ABSTAIN, or pinned anything other than NO_VIABLE_CHAMPION.
7. Lets the daily cycle write outside its allowed paths, make a call in `--no-commit` mode, append on a second run with nothing new, or pass with a tampered ledger.
8. States anything in the records (HANDOFF, ROADMAP, DECISIONS, RELEASE.md, OPEN_DECISIONS, PROCEDURE.md) that the evidence does not support.

Known weak points worth a look (stated, not judged): the commit-time anchor is the committer clock of the machine that commits (`PROCEDURE.md` "Why the commits must be pushed"); `--now` exists for tests and changes the decision clock of a run; PENDING and NOT_READ outcomes are appended before labels (PI-D-124 changed the test's expectation, not the code); PI-D-123 was used by the pin file at `e79d846` before its DECISIONS entry was written; the experiment registry names probe files that the frozen code merged into `build_cm2.py` subcommands (`experiments/EXPERIMENT_STATUS.csv`); the end-to-end tests do not refuse a network on their own (a mutant made 63 free calls before the probe moved inside `unshare -n`, PI-D-129); `level()` gives SHADOW to a role REFERENCE_BASELINE when a window passes, while the PIN reasons say references are never published.

## Artifacts

| Path | What |
|---|---|
| `CHANGE_CONTROL.md` | PI-D-122, the rules and the acceptance checklist G1 to G11 |
| `CHANGE_CONTROL_PI-D-124.md`, `CHANGE_CONTROL_PI-D-126.md` | the two test change controls after the freeze |
| `../../daily/RECIPE.json` | recipe R-CM2-1 (pinned sha256 in `predictive_daily.py`) |
| `../../daily/PROCEDURE.md` | the prediction-before-outcome procedure and the scheduled-task requirements |
| `../../daily/cards/`, `../../daily/registry/` | the 6 cards, the entries and the sha-chained log |
| `../../daily/BASE_LABELS.jsonl.gz` | the base label set the cards were fitted on |
| `evidence/interruption.json` | the check of the read made before the restart |
| `evidence/t2_reads.json`, `evidence/label_calls.json`, `raw/` | reads, every call, archived bodies |
| `evidence/base_labels.json`, `evidence/cards.json` | label set and fit results |
| `evidence/daily_fresh_clone.json` | two runs of the daily command in a fresh clone |
| `evidence/old_code_probe.txt` | CM-2 tests against `ed85b2c` |
| `evidence/mutation_probe_run1.json`, `evidence/mutation_probe_run2_partial.log`, `evidence/mutation_probe_run3_partial.log`, `evidence/mutation_probe.json` | first run, two runs stopped by hand during D08, final offline run |
| `evidence/mutation_probe_network.json` | the 63 free calls mutation D08 made from test clones (PI-D-129) |
| `evidence/daily_fresh_clone_pi_d_128.json` | the fresh-clone runs repeated at `a8c96d7` |
| `CHANGE_CONTROL_PI-D-128.md` | the one change to frozen cycle code |
| `CHANGE_CONTROL_PI-D-129.md` | probe offline; three Phase 16 tests changed (code-hash expectations and the reproduction's scratch clone) |
| `experiments/SEARCH_LEDGER.csv`, `SEARCH_LEDGER_CM2_ROWS.csv`, `LEDGER_TOTALS.json` | cumulative search ledger, N_search |
| `CM2_EVIDENCE.md` | commands, exit codes, hashes, deviations |

## Code

`memelab/predictive/contract.py` (PROMOTION_CM2, `promotion_rule_sha256`, `governing_sha256`), `memelab/predictive/labels.py` (`training_labels` splits), `memelab/predictive/promotion.py`, `audits/predictive-intelligence/daily/predictive_daily.py`, `probes/build_cm2.py`; tests `tests/test_predictive_promotion.py`, `tests/test_predictive_daily.py`, `tests/test_predictive_cm2_guards.py`, `tests/test_predictive_contract.py`, `tests/test_predictive_labels.py`, `tests/test_predictive_reports.py` (pins, PI-D-123).

## Commands to reproduce (from the repository root, full clone)

```
git diff --stat e79d846 HEAD -- memelab audits/predictive-intelligence/daily/predictive_daily.py audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/build_cm2.py
git log --format='%h %cI %s' ed85b2c^..HEAD
python -B audits/predictive-intelligence/daily/predictive_daily.py verify
python -m pytest -q tests/test_predictive_promotion.py tests/test_predictive_daily.py tests/test_predictive_cm2_guards.py tests/test_predictive_contract.py tests/test_predictive_labels.py tests/test_predictive_reports.py
bash audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/old_code_probe.sh "$PWD" /tmp/cm2_oc
python -B audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/mutation_probe.py /tmp/cm2_mut
bash audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/fresh_clone_daily.sh "$PWD" /tmp/cm2_fc
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

`check_partial_reads.py` was run once, at `e79d846` with 1 read on disk; run now it would check all 7 reads and overwrite `evidence/interruption.json`, so run it in a copy. It and `build_cm2.py labels` and `cards` need the private Phase 19 stores (`PI_RESEARCH_DIR`, default `/home/claude/pi_research`); `build_cm2.py fetch_t2` makes network calls and is not to be rerun (it would skip the 7 decisions it already holds). `fresh_clone_daily.sh` runs `git fetch origin main` from GitHub; the other commands need no network. The mutation probe takes about 25 minutes.

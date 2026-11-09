# Install runbook (research-only release, flag OFF)

Every command here was run in Phase 21, either by `probes/release_checks.sh` (fresh clone, fresh venv, recorded in `evidence/release_checks/`) or by `probes/doc_commands.sh` (sandbox, recorded in `evidence/doc_commands/`). Paths are relative to the repository root unless they start with `/`.

## What you get

A predictive research engine that sits beside the lab, imported by nothing but two helpers in `memelab/cli.py`, OFF by default. With the flag OFF the lab behaves byte for byte as before (flag-off identity, 12 of 12 runs). With the flag ON in a sandbox, it appends a research section to the scout report in which every target ABSTAINS with named reasons. It never trades, signs, reads a key, sends an alert or calls a paid service.

## Requirements

- Linux or macOS with Python 3.13 and git. The release checks used Python 3.13.17.
- Runtime dependency: numpy 2.5.3 only. Tests: pytest 9.1.1 (it brings iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0 and Pygments 2.21.0). Nothing else is needed; scikit-learn and the other research libraries were used only as oracles in separate research venvs.
- A full clone (not single-branch) when you run the whole suite: the commit-order tests of Phases 15 to 19 read the history of `origin/main`.
- A loopback interface for the Phase 14 tests (finding F20-11). A normal machine has one. Inside a network namespace made with `unshare -n` it starts down; raise it with `python -B audits/predictive-intelligence/phase_20/probes/lo_up.py` (an ioctl, no network) before running the tests there.
- Optional, for the real-path smoke and the flag-off check: `unshare` (util-linux) and root, so that every lab command runs without network.

## Steps

1. Clone and check out the branch.

   ```
   git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
   git checkout feature/predictive-intelligence
   git log -1 --oneline
   ```

2. Make a fresh virtual environment with only the pinned packages.

   ```
   python3 -m venv .venv
   .venv/bin/python -m pip install numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 packaging==26.3
   .venv/bin/python -m pip freeze
   ```

   Expect numpy, pytest, iniconfig, pluggy, packaging and Pygments, nothing else (`evidence/release_checks/logs/pip_freeze.txt`).

3. Check the holdout seal and the content guard.

   ```
   .venv/bin/python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
   .venv/bin/python -m memelab social guard
   ```

   Expect `"problems": []` and 0 violations.

4. Run the suite. Without network (recommended, as the release checks did):

   ```
   unshare -n sh -c "python -B audits/predictive-intelligence/phase_20/probes/lo_up.py && python -m pytest tests -q -p no:cacheprovider"
   ```

   (with `.venv/bin` first on PATH). Or simply `.venv/bin/python -m pytest tests -q`. Expect exactly two failures, both clock-dependent and known: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` and `tests/test_catalyst_firecrawl.py::test_page_history_and_spend_survive_a_new_session_through_the_state_export`. Any other failure is a finding. Then remove the test strays by hand: `git clean -fq data/reports` and `rm -f data/memelab.sqlite-shm data/memelab.sqlite-wal`; `git status` must be clean.

5. Leave the flag OFF. There is no `data/config.json` in the repository; the predictive flag is ON only when that file is a JSON object whose `predictive` object has `enabled` equal to the JSON value `true`. Anything else (missing file, `"true"` as a string, `1`, a malformed file) is OFF.

6. Only if you decide to try it (decision ED-8 in `OPEN_DECISIONS.md`), turn it on in a sandbox clone, never in your working checkout. See USER_GUIDE.md "Turning the flag on in a sandbox". Validate any `data/config.json` before saving it, because a malformed file stops the scout through the lab's social research policy (finding F20-13, outside this engine):

   ```
   python -c "import json; json.load(open('data/config.json'))"
   ```

## Rules for running the checks yourself

- Run any Phase 19 or 20 check that writes outputs in a sandbox clone. `audits/predictive-intelligence/phase_19/probes/run_prospective.py drift OUT` appends MONITOR and RESPONSE entries to the committed outcome ledger whatever OUT is (finding F20-14); in the working checkout that changes a tracked file. Use it there only in a planned maturity run whose result you commit.
- The reproduction scripts need the private research stores under `/home/claude/pi_research/` (rebuildable from the committed archives under `phase_05/raw/` and `phase_06/raw/` and the lock files in `docs/predictive-intelligence/locks/`). Without them those parts skip with that reason (the release checks ran the predictive tests with the stores hidden: 0 failures).
- Do not edit the checkout while `flag_off_identity.sh` runs: its summary compares the checkout's `git status` and the commit of every run.

## What was measured (release checks, fresh clone, 2026-11-09)

See `SMOKE_LOG.md` for the steps, exit codes, wall times and peak memory. Cost: 0 (no vendor, model or paid call). External services: none at run time; the clone and the pip install are the only network use.

## Uninstall

The engine has no install step beyond the checkout. To remove its effects: delete `data/config.json` (or set `enabled` to false), delete the state folder (default `data/private/predictive/`, or the `state_dir` you configured) and the alert folder (default `data/private/predictive_alerts/`). The lab's own tables are not touched by the engine (`ROLLBACK_PROOF.md`).

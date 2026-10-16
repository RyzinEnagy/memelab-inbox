# Historical first independent review evidence

**2026-10-15:** source-absence and OPS-provenance statements below describe the first review. Use `../m00_archive_recovery/README.md` and `../../M00_ARCHIVE_RECOVERY_VERIFICATION.md` for current checks; do not overwrite these historical result files by rerunning `verify_review_artifacts.py`. The current verifier checks all source/code links and the recovered archives in a separate output directory.

# Independent M00 verification evidence

Decision and checklist: [`../../M00_INDEPENDENT_VERIFICATION.md`](../../M00_INDEPENDENT_VERIFICATION.md). Original missing material: [`../../M00_MISSING_EVIDENCE.md`](../../M00_MISSING_EVIDENCE.md). Detailed map: [`../../M00_INDEPENDENT_CROSSWALK.json`](../../M00_INDEPENDENT_CROSSWALK.json).

This directory contains **new** independent verification evidence, not recovered original probes. The acceptance file is deliberately outside `tests/`, so it does not alter the existing suite or its expected counts. Nine red assertions reproduce open defects; one positive control must pass. Do not treat its exit 1 as a harness failure, a fixed application, or a passing release.

## Reproduction

Use Python 3.12 with `pytest==9.1.1` and `numpy==2.4.2` in a disposable virtual environment. Git and Node must be available; set `M00_TOOL_PATH` to a path containing them when necessary. The recorded run used Python 3.12.14, Node from the bundled runtime, and fresh environments with only explicitly supplied test variables. No credentials, paid/live calls or notifications are required.

From the root of the verification branch, fetch the four exact objects without moving the review baseline:

```sh
git fetch --depth=1 origin 698f73b854567ce60b56ce275b5ab6822a9d5f60 b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6 3b434e1dcc59290d993a638ca615f61b929189bc 3f27fc788f9ab88286b8041355e5445fdfdf012c
python audits/social-intelligence/evidence/independent_m00/verify_review_artifacts.py
```

Create **two disposable clean local clones**, explicitly fetch the intended commit into each (a shallow source clone may omit unreferenced objects), detach one at `698f73b...` and the other at `3b434e1...`. Make sure the recovery clone also has the exact `698f73b...` object before invoking the release audit. Run:

```sh
python audits/social-intelligence/evidence/independent_m00/run_review.py --baseline /tmp/clean-baseline --recovery /tmp/clean-recovery --out /tmp/new-m00-results
python audits/social-intelligence/evidence/independent_m00/run_acceptance.py --baseline /tmp/clean-baseline --recovery /tmp/clean-recovery --out /tmp/new-m00-results
python audits/social-intelligence/evidence/independent_m00/run_followups.py --root /tmp/clean-recovery --out /tmp/new-m00-results
```

`run_review.py` requires clean starting trees, runs full suites sequentially and records commands, exit codes, durations, database hashes and untracked files. Existing tests create a BRETT report; retain it only in disposable checkouts. `run_acceptance.py` separately records intentional defect failures, positive controls and checksum/missing-report mutations in temporary archive copies. `run_followups.py` preserves prior result records and can select one diagnostic with `--check`; it does not infer a logger root cause from a passing run. Each command's result is in its execution JSON; the orchestration program completing successfully does **not** imply the child tests passed.

The network guard blocks Python socket connection/DNS audit events and records event names only. It is inherited by subprocess Python through PYTHONPATH; it is not OS-wide egress capture. Release E2E also runs its own independent guard. There is a 900-second full-suite bound and 180-second other-check bound; no added address-space cap. All recorded local tests finished within those limits.

## Evidence files and publication handling

- `results/execution.json`: original full suite/M00/guard/release statuses; the initial recovery release audit failed because a shallow clone did not contain the pinned baseline object. The failed log remains present.
- `results/followup-execution.json`: completed release audit after fetching that object, release E2E, and logger diagnostics. No source or scanner rules changed to achieve the completed scan.
- `results/acceptance-execution.json` and `probe-observations.json`: nine counterexamples plus one positive-control case on each ref, identical observations.
- `results/independent-integrity.json`: 10 source hashes, four original upload digests, 67 IDs, 83 code spans, 105 requirements, original publication inventory and M00 application-path diff.
- `results/pinned-source-snapshot.json`: immutable baseline Git tree, deterministic tar digest and SHA-256 for all 360 files. This is a fresh manifest, not the absent original audit archive.
- `results/*network-events.log`: empty; zero blocked network attempts. Release E2E independently reports zero attempts.
- `results/publication-redactions.json`: raw/published hashes. Machine-specific filesystem paths were replaced for public publication; statuses, assertions and observations were retained. Raw local logs are outside the Git checkout.

To prepare a new run for publication, use `prepare_public_evidence.py RESULTS_DIR RAW_ARCHIVE_DIR`. It refuses to overwrite a nonempty raw archive. Review the entire resulting diff and scan for secrets/private material before publishing. Original recovered reports and snapshots must never be edited by this workflow. Original Phase 04/05 raw bytes and historical scripts/logs remain missing; inspect the retrieval ledger before making any acceptance claim.

Final publication-tree scan: `results/verification-release.json` retains exit 1 for 110 execution-keyword echoes in the captured Markdown scanner reports. `publication-scan-review.json` records manual classification; no rule was weakened. This differs from the exit-0 scans on the reviewed application/recovery checkout.

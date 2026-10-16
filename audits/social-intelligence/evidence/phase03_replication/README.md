# Newly reconstructed Phase 03 A–E replication

**This is new independent M00 evidence, NOT recovered original Phase 03 scripts, complete inputs or raw executions.** Current decision and reviewer action: [`../../M00_PHASE03_REPLICATION_REVIEW.md`](../../M00_PHASE03_REPLICATION_REVIEW.md). The supplied recovery package stays unchanged outside the repository. Its report/findings continuity and manifest hashes are recorded in `received-package-review.json`; private conversation/session content and unredacted machine logs are not republished.

`inputs.json` contains all newly chosen input objects. It explicitly separates reported values from invented completion fields. The report does not reveal its complete original candle/ledger/policy/quote objects, so no complete-original-input equality is claimed. `probe_cases.py` imports the actual pinned modules and asserts their file bytes equal the Git objects. It records resolved policy defaults and observations. `test_safety_acceptance.py` states independent safety expectations outside the existing application test suite; six red assertions are expected on this unchanged defective code. One control checks candle boundaries, prior wallet prices, exact-size quote arithmetic, and existing unknown-coverage flags. No xfail or weakened production assertion is used.

## Reproduce

Use the existing recorded environment: Python 3.12.14, pytest 9.1.1, numpy 2.4.2. Prepare a **disposable clean detached checkout** of `698f73b854567ce60b56ce275b5ab6822a9d5f60`. A shallow local clone may need an explicit fetch of that SHA before checkout. Do not overlay application files from any upload.

From the verification repository root:

```sh
python audits/social-intelligence/evidence/phase03_replication/run_replication.py --checkout /tmp/clean-pinned --out /tmp/new-phase03-replication-results
```

The runner removes credential variables, uses temporary stores, inherits the existing M00 socket/DNS guard, imposes 180 seconds per check and no extra memory cap, records exact child exits and raw/public log hashes, and checks the database and final checkout status. It exits zero only when expected characterization/safety outcomes, unchanged DB, clean status and no guarded network events all hold. Runner zero is not application safety PASS or reviewer acceptance. The guard is Python-level, not OS packet capture.

Recorded characterization: **exit 0**, documented mechanics reproduced. Safety expectations: **6 failed / 1 passed**, **exit 1**. Original Phase 03 runtime and original test exit codes remain unknown; these are new execution statuses only. `results/observations.json` records actual outputs/policies/three module hashes; `results/execution.json` pins all four new input/script hashes and resource limits. `results/network-events.log` is empty. Raw logs remain local; published safety logs replace only machine paths, preserving failures and raw/public SHA-256.

Probe E's **full inventory integration** is an explicitly new extension. The report only documented per-asset `NO_QUOTE`/None and `_sum([])==0`. The new holding/known-basis purchase, fee and price objects are invented; they show how the empty numeric reduction reaches the live inventory function, without claiming the original audit ran that integration. Existing unknown-count/basis fields are recorded and checked. No claim that all uncertainty flags are absent or that a UI has no disclosure follows from numeric zero.

Historical full-suite runs and original audit archives remain unchanged. No paid calls, notifications, trading or source changes. M00 remains BLOCKED pending explicit reviewed acceptance of substitute evidence and the missing historical lineage; M01 is not authorized.

# Independent verification — remediation M00

> **Current Phase 03 substitute review, 2026-10-15:** recovery package hashes and report/later-test continuity verified; newly reconstructed A–E runs now include D/E. Historical original full inputs/executions remain unrecovered. **M00 BLOCKED pending explicit reviewed acceptance of the substitute evidence; M01 unauthorized.** See [current decision and concrete reviewer action](M00_PHASE03_REPLICATION_REVIEW.md). Earlier dated statements retain their historical scope.


> **Current archive follow-up, 2026-10-15:** four original ZIPs and 50 member files recovered; 43 embedded hashes and all 105 original requirement texts verified. Original Phase 04/05 bytes are now available. OPS-001–010 are primary labels in the recovered Phase 05 findings, correcting the earlier secondary-only attribution. Phase 03 A–E executable inputs/scripts/raw outputs remain absent; **M00 BLOCKED, M01 unauthorized**. See [current checklist and next steps](M00_ARCHIVE_RECOVERY_VERIFICATION.md). Earlier dated statements below describe their historical review state.


> **Executed in a fresh review session on 2026-10-14 ET. Decision: BLOCKED.** See `M00_INDEPENDENT_VERIFICATION.md`, `M00_INDEPENDENT_CROSSWALK.md/json` and `M00_MISSING_EVIDENCE.md`. At reviewed recovery commit `3b434e1`, review was PENDING; this verification branch records REJECTED (acceptance withheld), so the strict gate still exits 2. No M01 authorization.

**Use a fresh session and a clean checkout.** Do not rely on the implementing engineer's test counts or consider a PASS from the integrity script to be proof of historical correctness. No application fix has been made in M00.

## 1. Starting state and original deficiency

1. Confirm `main` at the pinned application baseline `698f73b854567ce60b56ce275b5ab6822a9d5f60`, audit publication at `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6`, and this M00 feature branch against the audit publication branch. If refs moved, document the difference rather than silently updating the baseline.
2. On the original audit publication tree, list `audits/social-intelligence`. Verify that the primary inputs `00_BASELINE.md`, `REQUIREMENTS_MATRIX.md`, `01_FUNCTIONAL_AUDIT.md`, `02_ARCHITECTURE_AUDIT.md`, `03_RESEARCH_VALIDITY.md`, `04_ADVERSARIAL_AUDIT.md`, and `05_OPERATIONS_AND_UX.md` were absent. The eighth input, `06_STRATEGIC_IMPROVEMENTS.md`, was present.
3. Read the current `EVIDENCE_MANIFEST.json` and every recovered file directly. Independently compute SHA-256 (e.g., `sha256sum audits/social-intelligence/recovered/*.md audits/social-intelligence/06_STRATEGIC_IMPROVEMENTS.md`); compare with the manifest. Do not assume an index-text copy is byte-identical to the original Library file.
4. Check `02_ARCHITECTURE_AUDIT.md` and `03_RESEARCH_VALIDITY.md` against original archive/library paths, not substitute summaries. Both files are now present as SHA-256-matched original user uploads; validate their provenance independently, and retain **BLOCKED** if this or probe-level evidence is insufficient.

Verify the original Phase 02 and Phase 03 report *attachment bytes* against prior-chat locators listed in `M00_PRIOR_CHAT_LOCATORS.md`. Account for AUD-018–023 and AUD-024–033 explicitly; there are now **67 distinct AUD/ARCH/ADV/OPS IDs** in the consolidated register, not necessarily 67 independent defects. If original AUD findings change R-00/M01 scope or severity, refresh and review the remediation roadmap before implementation.

## 2. Acceptance and falsification commands

From the feature branch repository root:

```sh
python -m pytest tests/test_audit_evidence.py -q
python tools/check_audit_evidence.py
python tools/check_audit_evidence.py --require-complete
```

- Focused tests should pass and demonstrate that a tampered document and an originally empty evidence archive are rejected.
- The non-strict command verifies integrity of the **8/8 primary sources plus two preserved original findings snapshots** and prints `BLOCKED` while independent review is pending; exit zero is **not** acceptance.
- The strict command **must exit 2** with `missing=[]`: `independent_review=PENDING` on the reviewed recovery commit, `REJECTED` on this verification branch. If it exits zero without an independently accepted crosswalk, treat that as a verifier defect.
- Negative mutation: in a disposable checkout, append one byte to `recovered/00_BASELINE.md`; expect an integrity error and exit 1. Never mutate the live branch for the test.
- Also remove a recovered report in a disposable checkout; integrity validation must reject the false RECOVERED claim.

## 3. Independent content inspection

1. Review each AUD, ARCH, ADV and OPS row in `EVIDENCE_CROSSWALK.md` against its cited original source passage, the underlying code path and probe output. An indexed mention is not primary proof. The original architecture report is now recovered, but its static analysis and probe claims have not been independently reexecuted. Verify every ARCH row against source line and pinned code.
2. Verify original versus normalized severity, reproduce a representative original failure on pinned application code without changing production or executing paid calls, and record exact input/expected/actual output.
3. Verify that the requirements matrix covers the original scope, particularly negative cases, disabled/live distinctions, temporal availability, and provenance. Resolve contradictory and duplicate IDs; never close a finding merely by copying a report.
4. Locate original Phase 03 synthetic probes/output and `evidence/04_microprobes.py`, `evidence/04_microprobes_output.txt`, Phase 01 probe logs and raw Phase 00 test output. Their absence is an explicit gap, not evidence of success.
5. Run `git diff audit/social-intelligence-phase06...HEAD -- memelab state inbox data` and confirm M00 introduced no application, market-data or persisted-state changes. Inspect tracked additions for secrets and third-party raw social text.

## 4. Regression and final decision

Run `python -m pytest tests -q` on a clean disposable checkout if resources permit; record exit code and untracked files. The historical catalyst failure and untracked BRETT report must not be silenced. If the process is killed (137) or times out, report **INCOMPLETE**, not PASS. The M00 bounded combined-suite run also failed `test_social_ingest.py::test_logs_never_carry_secrets_or_content` (passes alone); investigate test-order effects independently rather than assuming the prior audit failure count is exhaustive. Also run the project's content guard and release audit when practical.

**PASS requires:** 8/8 source inputs accounted for with authentic evidence (now present); source snapshot SHA-256 proven and archived; every cited finding mapped to original path/line/probe, including ARCH and OPS; duplicates and discrepancies reconciled; independent reviewer records a signed decision; no new secret/social-text leak. Otherwise M00 remains **BLOCKED**, and M01 must not start.

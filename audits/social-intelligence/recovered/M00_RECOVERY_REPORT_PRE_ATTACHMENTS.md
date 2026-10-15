# Remediation M00 — recovery record

**Package:** M00 / R-00 Restore audit authority. **Status:** PARTIAL RECOVERY — BLOCKED (verification pending). **Date:** 2026-10-13. **Pinned application ref:** `698f73b854567ce60b56ce275b5ab6822a9d5f60`. **Audit base:** `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6`.

## Original defect and impact

Seven of the eight audit input records cited by the roadmap were not included in the published audit branch. That broke reproducibility and prevented an independent engineer from tracing findings back to the underlying reports, tests and requirements. No patch to the memecoin engine can satisfy this documentation/evidence defect. The roadmap makes recovery the prerequisite for implementation package M01.

## What was recovered

Five original-source titles were located in the user's ChatGPT Library and copied into `recovered/`: `00_BASELINE.md`, `REQUIREMENTS_MATRIX.md`, `01_FUNCTIONAL_AUDIT.md`, `04_ADVERSARIAL_AUDIT.md`, and `05_OPERATIONS_AND_UX.md`. Together with the already tracked `06_STRATEGIC_IMPROVEMENTS.md`, this accounts for **six of eight required inputs**. The first three were accessible as raw backing files and **their byte-for-byte SHA-256 was verified against the original Library backing** after preserving the final newline. Phase 04 and 05 were accessible as indexed text extracts and their exact original byte identity remains unconfirmed. The committed copies are checksum-pinned in `EVIDENCE_MANIFEST.json`.

`02_ARCHITECTURE_AUDIT.md` and `03_RESEARCH_VALIDITY.md` remain unavailable in the checked Git refs and accessible Library search. The recovered Phase 05 report says an earlier reviewer read Phase 02, but that statement does not reproduce the missing artifact. The Phase 06 report explicitly notes Phase 03's unavailability. Original probe scripts/logs are also not fully present.

## Discovery in previous project chats (additional missing provenance)

A project-conversation review located the original Phase 02 and Phase 03 completion messages and their original attachments, *not their file contents*. Phase 02 reportedly added **AUD-018–023**, and Phase 03 added **AUD-024–033**, including two serious leakage claims in the model-alpha and wallet valuation paths. The audit branch's consolidated register only included AUD-001–017; therefore **16 finding IDs were omitted from that AUD register**. The current crosswalk tracks 46 identifiers from available consolidated sources plus these **16 conversation-confirmed IDs (62 in total)**. No severity or detailed conclusion was guessed for omitted IDs. See `M00_PRIOR_CHAT_LOCATORS.md`.

The blocked status means **unavailable to this session**, not that these original reports never existed. Their earlier sandbox links are temporary session artifacts and cannot be trusted as source bytes until retrieved from the original conversations and hashed.

## Reconciliation

`EVIDENCE_CROSSWALK.md` enumerates **46 distinct AUD/ARCH/ADV/OPS identifiers** mentioned in currently accessible sources: 23 with a found primary report ID reference, 13 mentioned only in secondary material, and 10 architecture IDs with no primary report. The first 46 are automatically located reference positions and the other 16 are prior-chat IDs; neither is independently reviewed code/test proof. The OPS source does not use the OPS-nnn labels, so its fine-grained mapping remains unverified. The register's severity labels were not modified. There is no resolution of missing-source contradictions and no finding is closed.

## Verification evidence

- Focused M00 evidence tests: `python -m pytest tests/test_audit_evidence.py -q` — **4 passed**, exit 0.
- Partial integrity: `python tools/check_audit_evidence.py` — **BLOCKED** (6/8), integrity errors 0, exit 0; this does not meet the gate.
- Strict gate: `python tools/check_audit_evidence.py --require-complete` — **BLOCKED**, exit 2 as expected.
- Existing full suite: attempted, but the isolated execution environment terminated the process with **exit 137**, near 70% progress, so no complete pass/fail count exists. Early failure markers were observed; the known clock-dependent catalyst failure remains uncorrected. The run produced an untracked `data/reports/*BRETT*.md` report, consistent with earlier AUD-011. A separate focused `python -m pytest tests/test_catalyst.py -q` reproduced the known `test_dedup_corroboration_resurface_denial` failure (**1 failed, 4 passed**, exit 1); `python -m memelab social guard` returned exit 0 with no violations. Neither problem was changed here.
- An additional bounded diagnostic (`python -m pytest tests -q --maxfail=2`) exited 1 at **2 failed, 295 passed in 16.19s**. Besides the known catalyst test, `tests/test_social_ingest.py::test_logs_never_carry_secrets_or_content` failed in the combined run but passed when run individually (**1 passed**). This is an unresolved ordering/environment or test-isolation failure, not proof that ingestion is defective; do not suppress it.
- No live sources, model charges, alerts or trades were invoked by M00 work.

## Remaining limitations, risks and owners

- **Audit archive custodian/repository owner:** recover byte-complete `02_ARCHITECTURE_AUDIT.md` and `03_RESEARCH_VALIDITY.md` from original prior-session archives; find underlying probes/logs, then have an independent engineer verify crosswalk evidence and severity reconciliation.
- **Reviewers:** compare original report bytes with the indexed Phase 04 and Phase 05 copies. Examine the recovered Markdown for unexpected rights/private material prior to merging; initial pattern scans found no credential-shaped tokens or email addresses, but that is not an exhaustive privacy certification.
- **QA owner:** complete the regression suite in a sufficiently resourced clean checkout, preserving AUD-011's existing failures and documenting any newly encountered failures.
- **New risk:** placing generated audit materials into a public repository increases their visibility. They contain operational evaluation details; publication is not an authorization to expose third-party content or secrets.
- **Next action (still M00):** restore missing primary files, extend hash manifest and crosswalk, then run `M00_VERIFICATION.md` in a separate reviewer session. **Next conditional package:** M01 (causal time and provenance), **not yet authorized**.

**Stop:** M00 remains BLOCKED. Do not start M01, change application code, deploy sources, or declare any engine defect resolved.

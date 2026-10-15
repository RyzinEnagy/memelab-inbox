# Remediation M00 — evidence recovery and finding reconciliation

> **Superseding acceptance record, 2026-10-14 ET:** independent verification completed and acceptance withheld: **BLOCKED**, with original bytes/probe archive gaps. The recovery history below is retained. See `M00_INDEPENDENT_VERIFICATION.md`; no M01 authorization.

**Scope:** M00 / R-00 Restore audit authority; evidence-only. **Current state:** **8/8 PRIMARY AUDIT INPUTS RECOVERED, NOT ACCEPTED (INDEPENDENT VERIFICATION PENDING)**. **Pinned application baseline:** `698f73b854567ce60b56ce275b5ab6822a9d5f60`. **Audit publication ancestor:** `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6`. **Date:** 2026-10-13.

## What changed in this update

- Original Phase 02 and Phase 03 audit Markdown recovered from user's prior chat attachments and committed byte-for-byte as `recovered/02_ARCHITECTURE_AUDIT.md` and `recovered/03_RESEARCH_VALIDITY.md` (SHA-256 in `EVIDENCE_MANIFEST.json`). Both match the uploaded original hashes exactly.
- Original sequential finding registers, `recovered/phase02_FINDINGS.md` and `recovered/phase03_FINDINGS.md`, also restored byte-for-byte and individually SHA-256 tracked. These historical snapshots have *not* been edited or silently overwritten. The Phase 03 note that the Phase 02 report was missing describes the author's **earlier session**, not the current recovered archive.
- Full eight-source manifest integrity now clean: **8/8**; previous **6/8** was a truthful earlier snapshot, preserved in `recovered/M00_RECOVERY_REPORT_PRE_ATTACHMENTS.md` and commit history.
- Canonical `FINDINGS.md` reconciled conservatively to **AUD-001–033**: six new Phase 02 findings and ten new Phase 03 findings, with detailed source-authored text appended and preserved original Phase 06 strategic entries. **AUD-032 confirms AUD-002**; these are cross-references, not two independently established incidents.
- Rebuilt `EVIDENCE_CROSSWALK.md` with **67 distinct ID anchors: 33 AUD + 15 ARCH + 9 ADV + 10 OPS**. Distinguishes primary source headings from indexed Phase 04/05 reports and secondary-only OPS numbering. Source line anchors and document-scope evidence level are explicit. No source-authored severity was upgraded, no finding was closed.
- Extended `tools/check_audit_evidence.py` to check the two immutable historical snapshots and complete canonical finding inventory. Existing/new negative tests exercise tampering, missing files, duplicate-ID coverage and still-pending review.

## Remediation priorities updated by original quantitative audit

**P0 historical causal integrity (R-01):** In addition to AUD-001/002/015/017, original Phase 03 adds **AUD-024 (reproduced intrabar alpha fill timing)** and **AUD-025 (reproduced future wallet USD mark)**, plus AUD-032 (reconfirms 002) and AUD-033 (code-confirmed possible post-generation market-context leakage). The original report proves mechanics with invented candles/marks, not live P&L loss.

**P0/P1 provenance and publication (R-01/02/R-10):** AUD-020 missing full publication lineage, AUD-026 in-sample `VALIDATED` terminology, AUD-029 caveated exit quote/unknown aggregate, and AUD-031 absent on-chain proof call for explicit eligibility/abstention gates.

**P2 methodology and real value (R-12/13):** AUD-027 selection/control confounding, AUD-028 source coordination, AUD-030 unproven incremental editorial ordering; demand independent forward, size-specific, cohort-matched evaluation before any skill or trade claim. ARCH-002–015 are now grounded in original report text, not an inferred index.

The tracked roadmap receives an explicit addendum; no second implementation package has started. Original reports describe evidence grades and unmeasured outcomes. We have **not independently reexecuted** the Phase 02 static review or Phase 03 tests in M00.

## Verification: integrity is not research acceptance

Commands on a clean checkout after these changes:

```sh
python -m pytest tests/test_audit_evidence.py -q
python tools/check_audit_evidence.py
python tools/check_audit_evidence.py --require-complete
```

Expected: focused tests green, integrity JSON `recovered=8`, `required=8`, `missing=[]`, `integrity_errors=[]`; strict M00 returns **exit 2** while `independent_review=PENDING`. Changing the last field without an actual external reviewer and underlying proof is prohibited.

The earlier recovery run attempted the complete suite but exited **137** at about 70%; a bounded run had **2 failures, 295 passes** (known `test_catalyst` and combined-order `test_social_ingest` failure). That is *historical result*, not rerun here. Last earlier project guard had 0 violations. M00 has not touched application code, data, migrations, sources, paid models, alerts or trades.

## Remaining blockers and owners

1. **Independent QA reviewer:** review each 67-row source link, its attached claimed severity and exact code/test reproduction at pinned application ref, resolve duplicate/overlapping IDs, reconcile requirement-to-defect test coverage, and document sign-off. OPS 001–010 need manual matching against the Phase 05 original paragraphs.
2. **Audit archive custodian:** retrieve missing original Phase 00/01/03/04 probe scripts, raw execution logs/archives and original-byte Phase 04/05 reports. The current Phase 04/05 documents are readable indexed extracts, not verified original-byte attachments.
3. **QA operator:** rerun full suite in sufficiently resourced disposable environment, document baseline failures and test output pollution; do not treat previous run exit 137 as passing.
4. **Repository reviewer:** check publication rights, source/report redaction, and ensure no private social text or credentials were added.

**Status:** M00 **BLOCKED on evidence and reviewer sign-off**, although required source-file recovery is complete. The [M00 verification checklist](M00_VERIFICATION.md) is the gate. **M01 is not authorized; no engine defect was claimed fixed.**

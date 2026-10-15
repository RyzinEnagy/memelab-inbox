# M00 — Prior-chat audit artifact locators (not recovered source documents)

**Recorded:** 2026-10-13. **Authority:** metadata and historical assistant-output summaries retrieved from conversations in the **Memecoin Investing Lab** project. **Evidence level:** secondary conversation evidence, **NOT** the original report bytes or test logs. Do not upload these notes as substitutes for missing primary reports.

> **Recovery update (2026-10-13):** The Phase 02 and Phase 03 reports and both phase-specific FINDINGS.md snapshots described below **have now been recovered as original user-upload bytes and SHA-256 verified**. See `recovered/02_ARCHITECTURE_AUDIT.md`, `recovered/03_RESEARCH_VALIDITY.md`, `recovered/phase02_FINDINGS.md`, `recovered/phase03_FINDINGS.md` and the manifest. The original 'not recovered' cells in this document record the earlier investigation state, not the current status. Missing probe/log archives and independent reviewer remain pending.

## Audit artifacts generated in other project chats

| Original phase | Approximate prior message time | Expected original deliverables | Historical outcome | Current retrieval status |
|---|---|---|---|---|
| Phase 00 baseline | 2026-10-13 14:25 UTC | `00_BASELINE.md`, `REQUIREMENTS_MATRIX.md`, `FINDINGS.md`, `Memecoin_Social_Intelligence_Baseline_Audit.zip` | Original baseline `698f73b854567ce60b56ce275b5ab6822a9d5f60`; 14 initial AUD findings | First two recovered from Library; original ZIP and probe logs not recovered |
| Phase 01 functional | 2026-10-13 14:44 UTC | `01_FUNCTIONAL_AUDIT.md`, updated `FINDINGS.md`, `Social_Intelligence_Phase_01_Functional_Audit.zip` | AUD-015–017; tests/probes generated separately | Report recovered from Library; test ZIP/logs not recovered |
| Phase 02 architecture | 2026-10-13 16:28 UTC | `audits/social-intelligence/02_ARCHITECTURE_AUDIT.md`, updated `FINDINGS.md` | 15 reported architecture/integration weaknesses; *AUD-018–AUD-023* added | **Report and updated findings not retrieved; known original prior-chat output link only** |
| Phase 03 research validity | 2026-10-13 16:42 UTC | `audits/social-intelligence/03_RESEARCH_VALIDITY.md`, updated `FINDINGS.md` | *AUD-024–AUD-033* added; assistant summary reports timing leakage in Information Alpha and future-price leakage in wallet valuation; historical replay lacked enough genuine data | **Report and updated findings not retrieved; known original prior-chat output link only** |
| Phase 04 adversarial | 2026-10-13 17:53 UTC approx. | `04_ADVERSARIAL_AUDIT.md`, updated `FINDINGS.md`, `evidence/04_microprobes.py`, `evidence/04_microprobes_output.txt` | ADV-001–ADV-009 | Main report recovered as indexed text; original probe scripts/output missing |
| Phase 05 operations / UX | 2026-10-13 17:57 UTC approx. | `05_OPERATIONS_AND_UX.md`, updated `FINDINGS.md`, `Social_Intelligence_Phase_05_Operations_UX_Audit.zip` | OPS and operational issue discussion | Main report recovered as indexed text; original ZIP unavailable |

## Where the original Phase 02/03 links pointed

These are **locator strings from historical assistant messages**, not downloadable current-session artifacts. Open the original Phase 02 and Phase 03 project chats and download their attachments to recover byte-complete originals, then attach them to this project or commit through an authorized repository workflow.

- Phase 02: `sandbox:/mnt/data/audits/social-intelligence/02_ARCHITECTURE_AUDIT.md`
- Phase 02 updated finding register: `sandbox:/mnt/data/audits/social-intelligence/FINDINGS.md`
- Phase 03: `sandbox:/mnt/data/audits/social-intelligence/03_RESEARCH_VALIDITY.md`
- Phase 03 updated finding register: `sandbox:/mnt/data/audits/social-intelligence/FINDINGS.md`
- Phase 00 ZIP historical location: `sandbox:/workspace/scratch/c1d5c0a8dc65/Memecoin_Social_Intelligence_Baseline_Audit.zip`

**Important:** the two `FINDINGS.md` links refer to different states at different points in the audit sequence. Neither should silently overwrite the current register. Preserve separate numbered snapshots first, then reconcile all IDs and severities into the canonical register after source inspection.

## New gap identified from chat history

The 2026-10-13 published `FINDINGS.md` only registers **AUD-001–AUD-017**. Historical Phase 02 and Phase 03 assistant summaries explicitly report **AUD-018–AUD-033** (16 additional numbered findings). The original updated registers were not consolidated into the audit-publication branch. Their titles, severity, exact failure reproductions and acceptance criteria are **UNKNOWN until original files are obtained**. No finding among AUD-018–033 may be represented as independently verified or resolved on this locator alone.

Original-file recovery is blocked by **attachment/session visibility**: older conversations retain rendered links and titles, while this session's mounted storage, Project file search and Library searches do not contain the original Phase 02/03 bytes. The earlier assistant's statement that Phase 03 was unavailable in a later audit reflects that *later audit's local access*, not that Phase 03 had never been authored.

## Exact next retrieval action for reviewer / archive owner

1. In the Memecoin Investing Lab project open the **Phase 02 Architecture** chat dated October 13, 2026, locate the assistant reply around 12:28 p.m. America/New_York and retrieve the `02_ARCHITECTURE_AUDIT.md` and corresponding `FINDINGS.md` attachments.
2. Open the **Phase 03 Research Validity** chat, assistant reply around 12:42 p.m. America/New_York and retrieve `03_RESEARCH_VALIDITY.md` and its corresponding `FINDINGS.md`.
3. Retrieve the Phase 01 functional-audit ZIP and, if available, the Phase 00 baseline ZIP, Phase 04 probe scripts/output and Phase 05 ZIP for original execution evidence.
4. Supply the byte-complete originals to the M00 reviewer. Check SHA-256 and content prior to committing. Reconcile AUD-018–033, report original/normalized severity and tests, update `REMEDIATION_ROADMAP.md` if the newly recovered defects change dependencies, then independently reassess M00.

Until this is complete **M00 remains BLOCKED; M01 is not authorized**.

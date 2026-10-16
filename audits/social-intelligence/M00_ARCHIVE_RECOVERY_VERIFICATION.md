# M00 original-archive follow-up — 2026-10-15

**Decision: BLOCKED; independent acceptance withheld. M01 is not authorized.** This evidence-only supplement supersedes the source-absence and OPS-provenance statements in the first independent review. It does not erase its historical executions or resolve application findings. Review parent: `0ad3838b1e6023d42c499e97a156c5963f65a98c`, draft [PR #3](https://github.com/RyzinEnagy/memelab-inbox/pull/3) into `remediation/social-intelligence-m00`; PR #2 remains draft and unmerged. Application stays pinned to `698f73b854567ce60b56ce275b5ab6822a9d5f60`.

## Received originals and integrity

Four user-supplied ZIPs are preserved unchanged under `originals/phase00`, `phase01`, `phase04`, `phase05`, together with all 50 extracted files. `originals/ARCHIVES.json` pins received archive bytes and the two loose-upload matches; `originals/ARCHIVE_FILES.json` pins each member's original archive path, extracted path, length and SHA-256. ZIP CRC, safe relative paths, duplicate-member absence and absence of symlinks were checked. Embedded Phase 00/01/05 manifests independently match all **43/43** entries. Phase 04 contains no embedded checksum manifest; its received ZIP and all four members are now hash-pinned, without claiming a prior sender-side digest.

| Received file | Bytes | SHA-256 |
|---|---:|---|
| `Memecoin_Social_Intelligence_Baseline_Audit.zip` | 183795 | `4eca152678db816a5dd88334739a76d5f9ecf0d021d5c101ec4947724cbe7d70` |
| `Social_Intelligence_Phase_01_Functional_Audit.zip` | 97917 | `d6cc98d575252fe3c6ca7c41307f4969598510a3651d3afe88208d883eb16663` |
| `Social_Intelligence_Adversarial_Audit_Phase_04.zip` | 18021 | `d6432a3610fa4cd3be9221bd37222150ebec7bf7051ef99a8be88f17d020c77a` |
| `Social_Intelligence_Phase_05_Operations_UX_Audit.zip` | 28256 | `83099e983fa3cfa93b4043265257b8d289deadf4e73667738b25f5a889655901` |
| `03_RESEARCH_VALIDITY.md` | 36857 | `06cd96136950a1bcebe03a6fcd8cf92ca68d1d82b6a72385b54d93112d203322` |
| `FINDINGS.md` (Phase 03 snapshot) | 41187 | `4a4a18c1462c8047eb03f86f6a67a49984ebd6b9ef5c6963f3f47b1493192964` |

Phase 00 baseline, requirements matrix and Phase 01 report are byte-identical to the earlier recovered copies. Original Phase 04 and 05 reports differ from indexed copies **only by one final newline**. Their original hashes are respectively `d2199f688bd3687509c0ca0178422b82b979e3af5b52e476f883cde0fb522fc4` (30832 bytes) and `a9da21745e894474388d52b38694d1bdef2c44ebc4a0d3ba3253ad44a7b0ec06` (29341 bytes). The active manifest now points to those originals; indexed copies remain unchanged. The two loose Phase 03 uploads duplicate previously authenticated files and provide no additional scripts or logs. All 8 primary inputs and both preserved Phase 02/03 findings snapshots remain intact.

## Reconciliation and correction

The original staged prompt source is recovered with SHA-256 `9fa80398d70fe794e02709e099bc9c8a03727c1cfad7293dc0245d423ced64ed`. All **105/105** matrix requirement texts occur exactly in it. `results/requirement-source-links.json` identifies their source lines. Prompts are historical source evidence, not instructions executed by this follow-up. The older unstaged mega-prompt was not claimed as the matrix's recovered source and is not silently substituted.

**Correction to the first review:** OPS-001–010 and their severity/evidence/status originate in the original Phase 05 `FINDINGS.md`, lines **226–235**. The earlier attribution solely to a secondary Phase 06 index was incorrect because this primary findings file had not been available. The current independent Markdown/JSON crosswalk now cites those original rows as well as the precise Phase 05 report paragraphs and pinned code. In particular, OPS-008 is **High for stated product objective**, not the first review's secondary severity wording. OPS-004 remains conditional on billing; OPS-003/005/010 remain NOT VERIFIED, and OPS-008 remains NOT ESTABLISHED. None becomes a reproduced live incident.

All **67 IDs**, exact source excerpts, **83** pinned code spans and requirement references were rechecked. Original Phase 05's architecture count of 12 still conflicts with Phase 02's 15 ARCH IDs; all 15 are retained. AUD-002/032 remain overlapping replay-export evidence. Original historical findings registers are separate snapshots, including Phase 04's explicitly reconstructed partial register; they never replace the complete canonical AUD-001–033 register.

## Reexecution of recovered original scripts

Scripts were inspected before execution and run byte-for-byte from the archives against clean detached disposable checkouts. Python 3.12.14, pytest 9.1.1, numpy 2.4.2; per-check timeout 180 seconds, no additional memory cap. Credential variables were excluded, temporary stores used, Python socket/DNS guard enabled. No timeout, resource kill or network attempt was recorded. This guard is not OS-wide packet capture. Both checkouts ended clean, with tracked database SHA-256 unchanged at `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca`.

| Original evidence rerun | Ref / evidence grade | Exact exit | Result |
|---|---|---:|---|
| Phase 00 `evidence/probes.py` | Pinned application | 0 | Output semantically matches original `probes-main.json` |
| Phase 00 same script | Optional `3f27fc788f9ab88286b8041355e5445fdfdf012c` | 0 | Output semantically matches original `probes-feature.json` |
| Phase 01 `test_functional_audit.py` | Pinned application | 1 | **5 failed, 17 passed in 0.75s**; same five failing test IDs as original final log |
| Phase 04 `04_microprobes.py` | C: standalone equivalent-pattern probes | 0 | 10/10; stdout byte-identical to original; not imports/exploits of the package |
| Phase 05 `phase05_cost_model.py` | MODEL: historical assumed-price arithmetic | 0 | JSON matches original; not current tariff validation, provider invoices or measured operations |

The five Phase 01 failures are primary ingestion-to-claim handoff (AUD-003), iterator exception containment (AUD-016), late extraction cutoff (AUD-001), explicit future run (AUD-015), and chronology created after cutoff (AUD-017). Red acceptance cases confirm existing defects; they are not fixed application tests. Phase 00 probe outputs also corroborate replay backdating, fixture export, page-cap behavior and budget arithmetic. The initial Phase 01 harness log is preserved separately from its final results.

New execution evidence is under `evidence/m00_archive_recovery/results/`; original logs remain unchanged. New public logs redact only local machine paths and retain raw/public digests in `execution.json`. The previous clean full-suite results remain applicable because no application or existing test code changed: **651 passed/1 failed** on the pinned baseline and **658 passed/1 failed** on reviewed recovery, both exit 1 with the same catalyst assertion. Those suites were not rerun in this archive-only follow-up. Previous fresh high-impact temporal/alpha/wallet/provenance probes remain new evidence, distinct from recovered original executions. AUD-029's original liquidation probe is still report-authored, not newly executed here.

## Current acceptance checklist

| Gate | Result | Evidence / limit |
|---|---|---|
| Eight primary inputs and original upload integrity | PASS | Originals now include authenticated Phase 04/05 archive bytes; prior four Phase 02/03 uploads retained |
| Four ZIPs, 50 members, 43 embedded checksums | PASS | `archive-integrity.json`; Phase 04 has no embedded manifest |
| Requirement text and 67-ID source/code mapping | PASS | 105 exact texts, 83 pinned spans; original OPS rows corrected |
| Original Phase 00/01/04/05 scripts and available logs | PASS with stated grades | Original script reexecution table; no live/production efficacy implied |
| Original Phase 03 A–E executable inputs/scripts/raw outputs | **BLOCKED** | Reuploaded report/findings only; original execution lineage incomplete |
| Phase 04 historical terminated-suite raw output | NOT PROVIDED | ZIP has report/findings/microprobe/output only; historical termination remains INCOMPLETE, not PASS |
| M00 focused checks and tamper rejection | PASS | `validation-execution.json`; strict gate remains exit 2 |
| No application/state changes or sensitive publication | PASS within scan limits | All extracted members scanned for credential shapes; manual inspection found historical docs, invented fixtures/probes and logs, no private social corpus; no paid calls, wallet signing, alerts or trades |
| Independent acceptance and M01 authorization | **BLOCKED** | No approval recorded; manifest remains REVIEW_BLOCKED / REJECTED |

The tracked-tree scanner functions found zero credential or content-guard violations and 331 broad execution-keyword matches (56 in newly recovered prose). Manual review classified 330 as scanner-rule echoes in saved reports and one as an original prompt safety prohibition; no executable trade/signing code was identified. Scanner limits and match dispositions are retained in `publication-scan-review.json`; historical machine paths inside immutable archives identify audit environments, not credentials. No original file was redacted or rewritten to make checks pass. No copy was written to synced project `sources/`.

## Published-tree confirmation

Published archive commit `d9ab738af1a483c51a43d1b6e2e0ae47ceab23d6` has Git tree `666b853b3002fd94813a04e6593e9945711a95dd`, equal to the local verified tree. A fresh detached checkout repeated **10 passed in 1.50s** (exit 0), archive integrity exit 0 and strict acceptance exit 2; final status clean, guarded network events zero. Initial disposable setup had exit 128 for an unreferenced publication SHA, then exit 1 (9 passed/1 failed) because pinned Git objects were absent. Exact local fetches fixed setup; no code/assertion changes. The initial focused failure log and raw/public digests are retained in `results/published-clean-check.json` and `published-check-before-git-fetch.log`; reproduction instructions now explicitly require both application/optional objects. This confirms publication integrity, not M00 acceptance.

## How to clear the remaining gap

1. Ask the original **Phase 03 research-validity audit** owner/session for the exact synthetic A–E probe scripts or notebook/cell export, input files and raw output/log files used on the pinned SHA. The report does not name a ZIP or standalone script; do not invent a filename. Locator: [Research validity audit](chatgpt-conversation://6ace5ce5-da80-83ea-ab3c-cbee238872ad). Upload the originals as files; another copy of the report alone will not add execution lineage.
2. If those execution artifacts were never saved, record that fact explicitly. An alternative is a **new, separately labeled A–E replication package** using the report's exact inputs, including both liquidation cases, with code ref, expectations, actual output, guard/environment, hashes and raw logs. A reviewer must explicitly accept that substitute evidence and the permanent historical limitation. New scripts must never be presented as recovered original scripts.
3. Recover the Phase 04 terminated-suite raw log if it still exists. If it does not, retain the recorded historical INCOMPLETE limit; completed later full-suite runs provide separate current regression evidence and cannot reconstruct the old termination.
4. Submit a fresh explicit M00 acceptance decision against the remaining limitations and current checklist. Do not flip the manifest to ACCEPTED merely because integrity passes. A subsequent gate must also explicitly authorize M01 before implementation begins.

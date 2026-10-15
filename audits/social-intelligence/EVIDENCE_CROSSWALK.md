# M00 finding-to-evidence crosswalk

> **Independent review executed 2026-10-14 ET: BLOCKED.** The original inventory below is preserved. See [independent detailed crosswalk](M00_INDEPENDENT_CROSSWALK.md) for all 67 report-to-code/probe/requirement mappings and [review decision](M00_INDEPENDENT_VERIFICATION.md). No finding is closed; original-source/probe gaps remain.

**Status: PRIMARY REPORTS RECOVERED; INDEPENDENT EVIDENCE REVIEW PENDING.** A source-file heading or line anchor proves that the finding was documented, **not** that its underlying reproduction, timestamps, code paths or severity have been independently reconfirmed. The original offline probes/logs remain missing. **No findings are closed.**

Source fidelity: the Phase 02 and 03 audit reports and their separate findings snapshots have exact user-upload SHA-256 matches. Phase 04/05 were recovered from indexed Library text, not original bytes. The Phase 03 statement that Phase 02 was unavailable reflects that historical audit session; **both are now in this branch**.

**Inventory:** 33 AUD, 15 ARCH, 9 ADV, 10 OPS = **67 distinct registered audit IDs**, not 67 independent reproduced defects. AUD-032 is a research-validity reconfirmation of AUD-002. ARCH items overlap AUD issues by design. OPS numbering is a Phase 06 consolidated indexing convention rather than labelled paragraphs in the Phase 05 source report.

| Finding ID | Evidence class | Source path:line | Current qualification |
|---|---|---|---|
| ADV-001 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:35` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-002 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:45` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-003 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:55` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-004 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:65` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-005 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:75` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-006 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:85` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-007 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:95` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-008 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:105` | Phase 04 indexed-text copy; original probes/logs absent |
| ADV-009 | INDEXED ADVERSARIAL REPORT | `recovered/04_ADVERSARIAL_AUDIT.md:115` | Phase 04 indexed-text copy; original probes/logs absent |
| ARCH-001 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:24` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-002 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:25` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-003 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:26` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-004 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:27` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-005 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:28` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-006 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:29` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-007 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:30` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-008 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:31` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-009 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:32` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-010 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:33` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-011 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:34` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-012 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:35` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-013 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:36` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-014 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:37` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| ARCH-015 | ORIGINAL ARCHITECTURE AUDIT | `recovered/02_ARCHITECTURE_AUDIT.md:38` | Static/code/prior-phase architecture assessment; new stress tests not executed |
| AUD-001 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:27` | Original Phase 02 findings register; audit reported |
| AUD-002 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:37` | Original Phase 02 findings register; audit reported |
| AUD-003 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:47` | Original Phase 02 findings register; audit reported |
| AUD-004 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:57` | Original Phase 02 findings register; audit reported |
| AUD-005 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:67` | Original Phase 02 findings register; audit reported |
| AUD-006 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:77` | Original Phase 02 findings register; audit reported |
| AUD-007 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:87` | Original Phase 02 findings register; audit reported |
| AUD-008 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:97` | Original Phase 02 findings register; audit reported |
| AUD-009 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:107` | Original Phase 02 findings register; audit reported |
| AUD-010 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:117` | Original Phase 02 findings register; audit reported |
| AUD-011 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:127` | Original Phase 02 findings register; audit reported |
| AUD-012 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:137` | Original Phase 02 findings register; audit reported |
| AUD-013 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:147` | Original Phase 02 findings register; audit reported |
| AUD-014 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:157` | Original Phase 02 findings register; audit reported |
| AUD-015 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:182` | Original Phase 02 findings register; audit reported |
| AUD-016 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:192` | Original Phase 02 findings register; audit reported |
| AUD-017 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:202` | Original Phase 02 findings register; audit reported |
| AUD-018 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:218` | Original Phase 02 findings register; audit reported |
| AUD-019 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:224` | Original Phase 02 findings register; audit reported |
| AUD-020 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:230` | Original Phase 02 findings register; audit reported |
| AUD-021 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:236` | Original Phase 02 findings register; audit reported |
| AUD-022 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:242` | Original Phase 02 findings register; audit reported |
| AUD-023 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase02_FINDINGS.md:248` | Original Phase 02 findings register; audit reported |
| AUD-024 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:245` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-025 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:254` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-026 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:263` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-027 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:272` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-028 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:280` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-029 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:288` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-030 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:297` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-031 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:305` | Original Phase 03 findings register; method or synthetic evidence as described |
| AUD-032 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:313` | Original Phase 03 findings register; method or synthetic evidence as described; reconfirms AUD-002, not separate reproduced outcome |
| AUD-033 | ORIGINAL FINDINGS SNAPSHOT | `recovered/phase03_FINDINGS.md:322` | Original Phase 03 findings register; method or synthetic evidence as described |
| OPS-001 | SECONDARY OPS INDEX | `FINDINGS.md:395` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-002 | SECONDARY OPS INDEX | `FINDINGS.md:396` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-003 | SECONDARY OPS INDEX | `FINDINGS.md:397` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-004 | SECONDARY OPS INDEX | `FINDINGS.md:398` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-005 | SECONDARY OPS INDEX | `FINDINGS.md:399` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-006 | SECONDARY OPS INDEX | `FINDINGS.md:400` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-007 | SECONDARY OPS INDEX | `FINDINGS.md:401` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-008 | SECONDARY OPS INDEX | `FINDINGS.md:402` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-009 | SECONDARY OPS INDEX | `FINDINGS.md:403` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |
| OPS-010 | SECONDARY OPS INDEX | `FINDINGS.md:404` | OPS numbering from Phase 06 consolidated register; primary Phase 05 unlabeled |

## Important duplicate / hierarchy relationships

- `AUD-002` and `AUD-032` describe the same replay-export backdating family; AUD-032 is code-level confirmation and elaboration, not a new independently observed financial incident.
- `AUD-001`, `AUD-002`, `AUD-015`, `AUD-017`, `AUD-024`, `AUD-025`, `AUD-032` and `AUD-033` each implicate point-in-time causality, but distinct implementation paths and evidence standards remain documented separately.
- `ARCH-001` overlaps the historical cutoff AUD family; `ARCH-002` aligns with `AUD-018`; `ARCH-006` aligns with `AUD-019`; `ARCH-007` with `AUD-020`; `ARCH-009` with `AUD-021`; `ARCH-005/011` with `AUD-022`; `ARCH-008` with `AUD-023`. **Do not sum these as independent incidents.**
- AUD-024/025 are reproduced calculation mechanics from the original Phase 03 synthetic tests, not proof of realized monetary loss or predictive edge.
- The original Phase 03 report states its Phase 02 report was inaccessible. The original Phase 02 report is now recovered, and its original findings register is retained without changes. The apparent contradiction is **session chronology**, not evidence that the audit never occurred.

## Remaining independent verification gaps

1. Original Phase 00, 01, 03 and 04 probe scripts, input archives and raw test logs are incompletely archived. Reviewer must reproduce important reported failures on the **pinned application baseline** and attach outputs; citation anchors are not substitutes for executable test proof.
2. Original unmodified bytes of Phase 04 and 05 documents remain unverified (indexed text copies are available). Phase 05 uses operational topics but no `OPS-###` section identifiers: manually map OPS-001–010 from the Phase 06 index to specific Phase 05 paragraphs and confirm each interpretation.
3. Reconcile with `REQUIREMENTS_MATRIX.md` at the requirement/negative-path level; check duplicate IDs, evidence confidence and severity. This crosswalk records documented original audit classifications, not independent risk acceptance.
4. Protect public repository from private source text, credentials and prohibited third-party content; confirm user-uploaded reports and reproduced fixtures are publication-safe.
5. Independent reviewer must inspect `M00_VERIFICATION.md`, record sign-off explicitly, and only then change `EVIDENCE_MANIFEST.json.independent_review` to `ACCEPTED` if every gate passes.

## Recovery ownership / next action

All **8/8** required source documents are present and checksum-pinned; 2/2 original Phase 02/03 finding snapshots are also preserved. M00 cannot pass without source-ID-proof reconciliation, missing underlying probes/logs where required, and independent acceptance. Run `python tools/check_audit_evidence.py --require-complete`; expected **exit 2 while `independent_review=PENDING`**. M01 implementation remains unauthorized.

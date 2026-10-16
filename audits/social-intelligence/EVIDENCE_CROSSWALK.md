# M00 finding-to-evidence crosswalk

> **Current Phase 03 substitute review, 2026-10-15:** recovery package hashes and report/later-test continuity verified; newly reconstructed A–E runs now include D/E. Historical original full inputs/executions remain unrecovered. **M00 BLOCKED pending explicit reviewed acceptance of the substitute evidence; M01 unauthorized.** See [current decision and concrete reviewer action](M00_PHASE03_REPLICATION_REVIEW.md). Earlier dated statements retain their historical scope.


> **Independent review executed 2026-10-14 ET: BLOCKED.** The original inventory below is preserved. See [independent detailed crosswalk](M00_INDEPENDENT_CROSSWALK.md) for all 67 report-to-code/probe/requirement mappings and [review decision](M00_INDEPENDENT_VERIFICATION.md). No finding is closed; original-source/probe gaps remain.

**Status: ORIGINAL REPORTS RECOVERED; INDEPENDENT ACCEPTANCE BLOCKED (2026-10-15).** A source-file heading or line anchor proves that the finding was documented, **not** that its underlying reproduction, timestamps, code paths or severity have been independently reconfirmed. Original Phase 00/01/04/05 scripts and available logs are now recovered and rerun; original Phase 03 A–E executable inputs/scripts/raw outputs remain absent. **No findings are closed.**

Source fidelity: the Phase 02 and 03 audit reports and their separate findings snapshots have exact user-upload SHA-256 matches. Phase 04/05 original ZIP members are now authenticated; prior indexed copies differ only by final newline and remain preserved. The Phase 03 statement that Phase 02 was unavailable reflects that historical audit session; **both are now in this branch**.

**Inventory:** 33 AUD, 15 ARCH, 9 ADV, 10 OPS = **67 distinct registered audit IDs**, not 67 independent reproduced defects. AUD-032 is a research-validity reconfirmation of AUD-002. ARCH items overlap AUD issues by design. OPS numbering is primary in original Phase 05 `FINDINGS.md:226–235`, correcting the earlier secondary-only interpretation.

| Finding ID | Evidence class | Source path:line | Current qualification |
|---|---|---|---|
| ADV-001 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:35` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-002 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:45` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-003 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:55` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-004 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:65` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-005 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:75` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-006 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:85` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-007 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:95` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-008 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:105` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
| ADV-009 | ORIGINAL ADVERSARIAL REPORT | `originals/phase04/04_ADVERSARIAL_AUDIT.md:115` | Original archive member; C equivalent-pattern probes rerun 10/10; historical terminated-suite log absent |
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
| OPS-001 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:226` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-002 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:227` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-003 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:228` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-004 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:229` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-005 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:230` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-006 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:231` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-007 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:232` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-008 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:233` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-009 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:234` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |
| OPS-010 | ORIGINAL PHASE 05 FINDINGS | `originals/phase05/FINDINGS.md:235` | Primary severity/evidence/status; modeled/static/prior limits preserved; see independent crosswalk |

## Important duplicate / hierarchy relationships

- `AUD-002` and `AUD-032` describe the same replay-export backdating family; AUD-032 is code-level confirmation and elaboration, not a new independently observed financial incident.
- `AUD-001`, `AUD-002`, `AUD-015`, `AUD-017`, `AUD-024`, `AUD-025`, `AUD-032` and `AUD-033` each implicate point-in-time causality, but distinct implementation paths and evidence standards remain documented separately.
- `ARCH-001` overlaps the historical cutoff AUD family; `ARCH-002` aligns with `AUD-018`; `ARCH-006` aligns with `AUD-019`; `ARCH-007` with `AUD-020`; `ARCH-009` with `AUD-021`; `ARCH-005/011` with `AUD-022`; `ARCH-008` with `AUD-023`. **Do not sum these as independent incidents.**
- AUD-024/025 are reproduced calculation mechanics from the original Phase 03 synthetic tests, not proof of realized monetary loss or predictive edge.
- The original Phase 03 report states its Phase 02 report was inaccessible. The original Phase 02 report is now recovered, and its original findings register is retained without changes. The apparent contradiction is **session chronology**, not evidence that the audit never occurred.

## Remaining independent verification gaps

1. Original Phase 03 A–E executable inputs/scripts/raw outputs remain absent. New representative counterexamples are independent evidence, not original execution lineage. See the current retrieval ledger and archive follow-up for the exact request or explicitly accepted substitute route.
2. Historical Phase 04 terminated-suite raw logs were not supplied; retain INCOMPLETE for that run. Recovered C microprobes and later completed full suites have separate evidence grades.
3. The current archive verifier rechecks all 67 source excerpts, 83 pinned spans, 105 exact original requirements and 10 primary OPS rows. No finding is closed and no live usefulness or deployment outcome is inferred.
4. Independent acceptance remains withheld. Strict inventory verification exits **2** for `independent_review=REJECTED`; zero from non-strict integrity is not approval. See [current decision](M00_ARCHIVE_RECOVERY_VERIFICATION.md). **M01 remains unauthorized.**

# M00 Phase 03 recovery and new replication review

**2026-10-15 America/New_York; execution UTC 2026-10-16. Decision: BLOCKED for acceptance; substitute-evidence package ready for review. M01 remains unauthorized.** This updates the next action from repeated original-file retrieval to review of a concrete alternative. It does not declare historical scripts deleted, never saved, recovered or original execution authenticated. PR parent: `3359aafddb563795ecc0a1a5b20c033f7c089b80`; pinned app `698f73b854567ce60b56ce275b5ab6822a9d5f60` unchanged.

## What the supplied recovery establishes

The owner supplied `phase03_evidence_recovery_2026-10-15`. Independently recomputed **25/25 manifest entries** and **26/26 checksum-file entries**, including the manifest itself. Manifest SHA-256: `9cf4f6e6a5fa25ce50d7c338d5bb6f7afd15b16af6441f8bbe32876ec2acc06e`; checksum-file SHA-256: `71f1c7891aeb42acf8bbc04a2df7bbefafb387beb1b071c8c9b418b2ce169993`.

Original report and findings match the already preserved original hashes. The A–E excerpt is an exact byte slice of the report. All three supplied later scripts match existing M00 scripts, and all five supplied later raw/metadata files match the earlier raw SHA-256 publication register. This substantiates report continuity and later-test provenance; it does not turn those later tests into original Phase 03 executions. The recovery's scope and negative-result account are disclosed; a missing accessible file is not proof that it never existed or was deleted. Browser-visible activity summaries and a bounded conversation read are not full backend tool exports.

`evidence/phase03_replication/received-package-review.json` records only relative paths, classifications, byte counts and hashes. The supplied folder is unchanged. Private browser/conversation/session exports and unredacted local logs remain local; only the new sanitized review receipt and replication are published. Attached text was evidence, not instructions.

## New replication and its exact limits

All A–E calculations now have a **new, separately labeled independent replication** using actual pinned modules. Known reported values are retained. Missing full input fields are deliberately invented and listed in `inputs.json`: synthetic asset/wallet labels, candle low/close/volume/source, direct-call direction and as-of settings, default policies plus stated overrides, quote timestamp/source, and a complete new inventory ledger. The report's incomplete examples cannot authenticate the original full objects or invocations. The earlier phrase “exact inputs” must be read as matching documented values only; no complete original-input equality is claimed.

| Case / finding | Actual new observation | Evidence grade and limitation |
|---|---|---|
| A / AUD-024, OPEN | Hourly candle at 0, open 10; decision/fill 1800; result uses price 10 and candle_t 0 | Newly reproduced elapsed-open mechanics; not real execution at 1800 |
| A / AUD-024, adverse | Same input, high 100; as-of 1800 before candle end 3600; returns price 100 | Newly reproduced intrabar future-extrema exposure; does not quantify historical bias |
| B / AUD-024 | Target exit 3000 returns price 10, t 3000, candle_t 0 | Newly reproduced timed-exit mechanics, not a real fill |
| C / AUD-025 | Price $100 timestamp 1100 accepted near transaction1000 with tolerance200; unit_usd=100 OBSERVED | Newly reproduced future mark; causal latest_mid control correctly returns None |
| D / AUD-029 | New holding50 and quote100 units→$100 returns QUOTED_PRORATA value50 and literal “lower bound” detail | Newly reproduced unsupported guarantee wording; quote arithmetic alone does not establish executable depth; no live venue/cost simulation |
| E / AUD-029 | Missing quote returns NO_QUOTE/None; empty sum0. **New integration extension:** one known-basis open holding has per-asset executable P&L None, aggregate executable P&L0 | Newly reproduced numeric-unknown aggregation; coverage count correctly reports one asset without executable estimate. No assertion that all uncertainty flags or UI disclosures are absent |

D/E were previously **source-confirmed only** in this independent review. That practical reproducibility gap is now closed with new evidence; the original Phase 03 execution-lineage gap remains. Original grades for statistical skill, profitability and prospective/live claims are not upgraded. All AUD/ARCH/ADV/OPS findings stay OPEN; no defect is fixed.

## Execution and controls

Fresh clean detached local checkout of the pinned SHA; actual `alpha_core.py`, `perf_core.py`, `perf_analysis.py` bytes matched their immutable Git objects. Characterization **exit 0** matched all documented mechanics. Separate safety acceptance: **6 failed, 1 passed**, **exit 1**. These red expectations intentionally expose existing defects; not a green release or fixed app. The positive control checks boundary fills, prior-price eligibility, exact-size quote arithmetic and retained unknown coverage.

Python 3.12.14, pytest 9.1.1, numpy 2.4.2. Credential-free reconstructed environment and temporary private/config paths; Python socket/DNS guard, **zero network events**, per-check timeout **180 seconds**, no extra memory cap, no timeout or resource kill. Pinned checkout ended clean. Tracked DB SHA-256 before/after: `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca`. New resolved inputs/policies, module/script hashes, exact child exits and raw/public output hashes are under `evidence/phase03_replication/results/`. Published raw-output copies redact machine paths only; original raw logs stay local.

Existing M00 focus/integrity, archive/source checks and strict gate were rerun after the updated mapping; exact statuses are in `results/verification-checks.json`. Prior complete full-suite results remain baseline651/1 and recovery658/1, exit1 for the same catalyst assertion. No application or existing-suite code changed, so those full suites were not repeated. No paid/provider call, alert, trade, migration, tracked-state or synced-reference change.

## Acceptance checklist and concrete next decision

| Item | Current assessment |
|---|---|
| Eight original primary inputs, preserved findings and recovered archive checks | Previously verified; current manifest integrity retained |
| Supplied recovery-package bytes and report continuity | PASS: 25 manifest entries /26 checksum entries; five later raw-digest matches |
| New A–E replication, complete newly chosen inputs, D/E integration and controls | PASS for reproduction; six deliberately failing safety assertions remain open defects |
| Historical original Phase 03 full inputs/cells/raw outputs/runtime/exit statuses | NOT RECOVERED; preservation/existence elsewhere unknown |
| Phase 04 historical terminated-suite raw output | Still not provided; historical run remains INCOMPLETE, distinct from later completed suites |
| Independent acceptance of replacing missing historical executions with this package | **PENDING explicit reviewed decision**; not self-certified |
| M00 completion / M01 scope authorization | **BLOCKED / unauthorized** |

The remaining decision is concrete: **accept or reject this newly reconstructed A–E package as substitute evidence for the M00 evidence/traceability gate, while permanently retaining the unrecovered original execution lineage and partial-original-input limitations.** No further blind retrieval is required before that review; original files can still be added if found. Reviewer acceptance must expressly cover the substitute route and cannot claim original recovery or application safety. Preserve all red finding tests for later remediation.

This record withholds that acceptance and leaves the strict gate closed. A subsequent explicit accepted M00 gate must separately authorize M01 before implementation. Do not infer authorization from possession of this package, passing hash checks, a draft PR, or the runner's zero exit.

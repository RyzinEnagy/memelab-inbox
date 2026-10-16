# Social & Trader Intelligence — Audit Findings Register

**Updated:** 2026-10-13 · **Status:** RECONSTRUCTED PARTIAL REGISTER (prior authoritative file unavailable).  
**Baseline:** `698f73b854567ce60b56ce275b5ab6822a9d5f60`.  
**Scope of this update:** Phase 04 adversarial assessment. No existing repository `FINDINGS.md` was overwritten.

## Continuity with earlier audits

The previous Phase 00–03 audit record files (`00_BASELINE.md`, `REQUIREMENTS_MATRIX.md`, `FINDINGS.md`, later phase reports) are **not present** on the verified GitHub main or feature branch. Earlier session history indicates Phase 00 found 14 items (`AUD-001`–`AUD-014`); Phase 01 added `AUD-015`–`AUD-017`; Phase 02 reportedly added `AUD-018`–`AUD-023`; Phase 03 flagged look-ahead and valuation issues. Their complete descriptions, severity, status and evidence are **not available for exact recovery here**. These identifiers are **reserved**, not declared closed, and are not reconstructed from guesses. Obtain the canonical records before merging or renumbering findings.

Known earlier concerns from recovered audit history (not independently revalidated here): historical-cutoff/look-ahead leakage, provenance gaps, ingestion state recovery left `RUNNING`, incomplete cross-chain identity integration, inconsistent SQLite foreign-key enforcement, and unverified live-source/scoring claims. These remain important for the adversarial risk model.

## Phase 04 additions

`C` = source plus local equivalent-behavior micro-probe (not an engine import); `S` = source/readme evidence only; `H/B` = scenario unverified or blocked. Status `OPEN` means mitigation is not evidenced.

| ID | Finding | Severity | Evidence | Status | Component |
|---|---|---|---|---|---|
| ADV-001 | Private SQLite file/directory permissions not hardened on create | HIGH (shared host) | C | OPEN | `social/private.py` |
| ADV-002 | Expired exact post text remains available through `get()` until purge | MEDIUM-HIGH | C | OPEN | `social/private.py`; operations |
| ADV-003 | LLM config secret-key check is top-level, not recursive | MEDIUM | C | OPEN | `social/llm.py` |
| ADV-004 | Helius URL redactor does not hide arbitrary bearer/credential forms | MEDIUM conditional | C | OPEN | `secrets.py` |
| ADV-005 | Bad type in model HTTP response can raise uncaught `TypeError` | MEDIUM | C | OPEN | `social/llm.py` |
| ADV-006 | Malformed Telegram JSON body / 429 retry value can throw outside error boundary | MEDIUM | C | OPEN | `social/alerts_transport.py` |
| ADV-007 | Model budget preflight/record is not an atomic multi-process reservation | MEDIUM | C | OPEN | `social/llm.py` |
| ADV-008 | Publication content guard does not scan arbitrary Markdown/CSV/prose fields | MEDIUM | S | OPEN | `social/content_guard.py` |
| ADV-009 | X-deleted-post reconciliation/purge not built per operations runbook | HIGH if live X storage | S | OPEN/BLOCK LIVE X | X lifecycle |

## Unverified attack surfaces — do not relabel as proven bugs

- **THREAT-SOCIAL-01:** Sybil social consensus, cloned analysts, bought engagement, misleading catalyst claims and repeated reposts. Require actual end-to-end adversarial fixture tests with source-independence metrics.
- **THREAT-IDENTITY-02:** Conflicting tickers, false contract addresses, cross-chain names and model-asserted mint. Verify true chain + exact mint survives through final report.
- **THREAT-WALLET-03:** Fabricated profitable-wallet screenshots, self-transfers, wallet splitting, false insider statements and claimed exit profits. Require transaction-level swap/settlement evidence.
- **THREAT-MARKET-04:** Wash trading, shallow-pool spot-price spikes, unusable displayed liquidity and non-realizable profit. Require actual route quotes, fee-adjusted execution and temporal price integrity.
- **THREAT-RELIABILITY-05:** Very large or deeply nested responses, expired credentials, rate limiting, transport crashes and historical idempotency. Not proven safe by incomplete pytest runs.

## Verification / next-owner gate

1. Recover previous Phase 00–03 source audit files and merge records without collision.
2. Re-run the full suite in a controlled, sufficiently resourced isolated checkout and capture exact failures.
3. Apply the Phase 04 offline payload matrix from `04_ADVERSARIAL_AUDIT.md` to the **actual repository pipeline**, and assert downstream database and report behavior.
4. Review security-relevant changes beyond the pinned baseline (especially new feature-branch source adapters).
5. Keep live data/notification credentials disabled until the applicable privacy and safety conditions are verified.

**Release disposition:** adversarial security and financial-manipulation resistance **NOT VALIDATED**. No claim of exploit success on a real model, chain, or trading venue.

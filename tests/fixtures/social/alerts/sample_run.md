# Phase 15 sample: research alerts on an invented fixture

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

Reproduce: `python -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json`

Dry run with the local file sink only, in a throwaway state file. Run 2 reads a later snapshot that carries the same evidence.

## Run 1

```
Alert run 1 (dry_run), 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), policy alerts-policy-v1 6d5d61ff4a80
FIXTURE DEMO: invented data, not live alerts.
Outcome: evaluated
Candidates 4, new alerts 4, deduped 0, suppressed 5
  suppressed wallet_corroboration GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY): stale_event (wallet event behind DISCLOSED_POSITION_CONSISTENT_OLD is older than 24.0 h or undated)
  suppressed convergence HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): below_threshold (2 independent source(s), policy needs 3)
  suppressed conversation_growth HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): no_baseline (0 earlier snapshot(s) recorded, policy needs 3)
  suppressed convergence theme ai_agent: below_threshold (2 independent source(s), policy needs 3)
  suppressed convergence SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931): stale_source (the newest observation for this item is older than the freshness limit)
Dry run: previews only. Nothing was sent.
```

### Alert text

```
FIXTURE DEMO: invented data, not a live alert.
memelab research alert, WARNING: risk
HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ)
Why: no sell route in the newest exit check: treat as not exitable until a later check shows one
Confidence: MODERATE (FACT)
Freshness: item FRESH, feed FRESH, last observed 2026-10-13 06:10 EDT (2026-10-13 10:10 UTC)
Contract: solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ
Source: fx_delta (x) https://example.invalid/x/h1
Source: fx_echo (x) https://example.invalid/x/h2
Source: fx_burst_00 (x) https://example.invalid/x/hr0
Source: fx_burst_01 (x) https://example.invalid/x/hr1
Provenance: narrative run 2, cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ, claims 12,13,14,15,16,17,18,19,20,21,22,23,24,25, chronology runs 1, feed 4e5c544d98d4
Alert 1, dedupe 62e7f4ac629f, policy alerts-policy-v1
Research only. Not a trade instruction, not a score, not a watchlist change.
FIXTURE DEMO: invented data, not a live alert.
```

### Alert text

```
FIXTURE DEMO: invented data, not a live alert.
memelab research alert, WARNING: risk
HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ)
Why: new risk evidence: SALE_DURING_PROMOTION (HEURISTIC, not proven, wallet CLAIMED)
Confidence: LOW (HEURISTIC)
Freshness: item FRESH, feed FRESH, last observed 2026-10-13 06:10 EDT (2026-10-13 10:10 UTC)
Contract: solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ
Source: fx_delta (x) https://example.invalid/x/h1
Source: fx_echo (x) https://example.invalid/x/h2
Source: fx_burst_00 (x) https://example.invalid/x/hr0
Source: fx_burst_01 (x) https://example.invalid/x/hr1
Provenance: narrative run 2, cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ, claims 12,13,14,15,16,17,18,19,20,21,22,23,24,25, chronology runs 1, feed 4e5c544d98d4
Rule: chrono.sale_during_promotion.v1, chronology run 1
Alert 2, dedupe 9657ddab206b, policy alerts-policy-v1
Research only. Not a trade instruction, not a score, not a watchlist change.
FIXTURE DEMO: invented data, not a live alert.
```

### Alert text

```
FIXTURE DEMO: invented data, not a live alert.
memelab research alert, NOTICE: convergence
GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY)
Why: 3 independent sources converge; 2 of them registry-linked or allowlisted: fx_alpha (x), fx_bravo (x)
Confidence: MODERATE (INFERENCE)
Freshness: item FRESH, feed FRESH, last observed 2026-10-13 05:00 EDT (2026-10-13 09:00 UTC)
Contract: solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY
Source: fx_alpha (x) https://example.invalid/x/g1
Source: fx_bravo (x) https://example.invalid/x/g2
Source: fx_charlie_channel (telegram) https://t.me/fx_charlie_channel/101
Source: fx_amp_one (x) https://example.invalid/x/g4
Provenance: narrative run 2, cluster ca:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY, claims 3,5,7,9,10,11, chronology runs 2,3, feed 4e5c544d98d4
Alert 3, dedupe 4a4bd7a003ba, policy alerts-policy-v1
Research only. Not a trade instruction, not a score, not a watchlist change.
FIXTURE DEMO: invented data, not a live alert.
```

### Alert text

```
FIXTURE DEMO: invented data, not a live alert.
memelab research alert, NOTICE: wallet corroboration
GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY)
Why: monitored LINKED wallet activity is consistent with a claim (DISCLOSED_POSITION_CONSISTENT, order CONFIDENT)
Confidence: MODERATE (INFERENCE)
Freshness: item FRESH, feed FRESH, last observed 2026-10-13 05:00 EDT (2026-10-13 09:00 UTC)
Contract: solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY
Source: fx_alpha (x) https://example.invalid/x/g1
Source: fx_bravo (x) https://example.invalid/x/g2
Source: fx_charlie_channel (telegram) https://t.me/fx_charlie_channel/101
Source: fx_amp_one (x) https://example.invalid/x/g4
Provenance: narrative run 2, cluster ca:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY, claims 3,5,7,9,10,11, chronology runs 2,3, feed 4e5c544d98d4
Rule: chrono.disclosed_position.v1, chronology run 2
Alert 4, dedupe 720b4168e2b5, policy alerts-policy-v1
Research only. Not a trade instruction, not a score, not a watchlist change.
FIXTURE DEMO: invented data, not a live alert.
```

## Run 2 (same evidence, later snapshot)

```
Alert run 2 (dry_run), 2026-10-13 10:00 EDT (2026-10-13 14:00 UTC), policy alerts-policy-v1 6d5d61ff4a80
FIXTURE DEMO: invented data, not live alerts.
Outcome: evaluated
Candidates 4, new alerts 0, deduped 4, suppressed 5
No new alerts (all deduped or suppressed).
  suppressed wallet_corroboration GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY): stale_event (wallet event behind DISCLOSED_POSITION_CONSISTENT_OLD is older than 24.0 h or undated)
  suppressed convergence HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): below_threshold (2 independent source(s), policy needs 3)
  suppressed conversation_growth HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ): no_baseline (1 earlier snapshot(s) recorded, policy needs 3)
  suppressed convergence theme ai_agent: below_threshold (2 independent source(s), policy needs 3)
  suppressed convergence SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931): stale_source (the newest observation for this item is older than the freshness limit)
Dry run: previews only. Nothing was sent.
```

## Delivery state

```
Alert delivery state

Alert 1 [dry_run] warning risk: HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ) (FIXTURE)
  status PREVIEW, created 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), dedupe 62e7f4ac629f
  file attempt 1: dry_run_preview: dry run: preview only, nothing sent
Alert 2 [dry_run] warning risk: HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ) (FIXTURE)
  status PREVIEW, created 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), dedupe 9657ddab206b
  file attempt 1: dry_run_preview: dry run: preview only, nothing sent
Alert 3 [dry_run] notice convergence: GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY) (FIXTURE)
  status PREVIEW, created 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), dedupe 4a4bd7a003ba
  file attempt 1: dry_run_preview: dry run: preview only, nothing sent
Alert 4 [dry_run] notice wallet_corroboration: GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY) (FIXTURE)
  status PREVIEW, created 2026-10-13 08:00 EDT (2026-10-13 12:00 UTC), dedupe 720b4168e2b5
  file attempt 1: dry_run_preview: dry run: preview only, nothing sent

Ledger totals: dry_run_preview 4
Messages confirmed delivered to a device (telegram or email): 0
Nothing has been sent to a device. Local files and previews are not deliveries.
```

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

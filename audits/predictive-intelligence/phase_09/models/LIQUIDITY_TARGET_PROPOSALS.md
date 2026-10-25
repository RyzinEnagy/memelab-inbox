# Liquidity, exit-capacity and distribution targets: proposals, not frozen

Status: PROPOSED_NOT_FROZEN (PI-D-044, PI-D-054). Nothing here is in the target registry; the registry fingerprint `4b4aabce...` and ACCEPTANCE are unchanged and the registry keeps `liquidity_degradation_24h` DEFERRED_FORWARD_COLLECTION, `exit_adjusted_target_before_invalidation_24h` BLOCKED_NO_HISTORICAL_DEPTH and `distribution_event_24h` BLOCKED_NO_DATA. Freezing any of these is a later change control, written and committed before any of its outcomes is read, and only after the collector has run long enough to give at least the frozen training minimums (100 events, 20 per class) on its own decisions. The code that labels them (`depth_adapter.proposed_liquidity_label`, `onchain.wallet_role`, `onchain.movement_class`) has no default parameter and has only ever labelled fixtures (TEST_ONLY).

## Data source

The backtesting module's forward depth collector (D-BT-034 and D-BT-035 on `feature/backtesting` at `12f278b`), read only through `memelab/predictive/depth_adapter.py`. Per lab decision (an exact thesis row first visible in an export, decision time = export commit time), each hourly run until 25 h after the export records the export's pool (or the vendor's top pool, flagged) with reported reserves, and on Solana keyless Jupiter sell quotes into USDC at $100, $500 and $2,000, each row with `captured_at`, URL, HTTP status and body hash. Every row is after its own decision (first run up to about an hour later, `since_export_s`). Deployment on Elving's computer is pending; on 2026-10-25 no forward row exists.

## Proposal L1: quote-based liquidity drawdown at a stated size

| Item | Proposed rule (to be fixed at change control) |
|---|---|
| Unit | one lab decision linked to one collector decision by chain, exact mint, row sha256 and export time equal to the decision time (`depth_adapter.link`) |
| Pool | the collector decision's pool (export pool, else vendor top pool, stratified by `pool_source`) |
| Size | one of 100, 500, 2,000 USD, stated in the target name; each size a separate target |
| Baseline | the first answered quote (OK, NO_ROUTE or NOT_TRADABLE) at that size captured within `baseline_max_lag_s` after the decision; OK gives the baseline proceeds ratio (out USD / size) |
| Horizon read | the answered quote nearest decision + `horizon_s` within `horizon_tol_s`, captured after the baseline |
| Positive | proceeds ratio at the horizon at or below baseline x (1 - `drop`), or ROUTE_LOST (NO_ROUTE or NOT_TRADABLE at the horizon after an OK baseline; never a favourable fill, P37) |
| Not this target | EXIT_UNAVAILABLE_AT_BASELINE (no route already at the first read) |
| Censored | CENSORED_NO_BASELINE, CENSORED_NO_HORIZON_READ (HTTP errors, caps, deadlines, PRICE_DISAGREES), counted by reason and route |
| Pending | NOT_YET_MATURED until decision + `horizon_s` + `horizon_tol_s` (P05) |
| Never used | reported reserve or TVL (P08); a quote at another size (P44); a read of another pool of the mint (P02) |

Open parameters to fix by change control before reading outcomes: `drop` (for example 0.2), `baseline_max_lag_s` (the collector's first run is up to about 3,600 s after the export, so at least that), `horizon_s` 86,400, `horizon_tol_s` (one run, 3,600 s), which sizes are primary. Features for such a target follow CX-09: no collector row of the decision itself is ever an input; rows of earlier decisions of the same mint captured before the decision may be.

## Proposal L2: exit capacity at a stated size

An exit-adjusted price-path target (target before invalidation where the exit at the barrier time is priced by an OK quote at the stated size taken at or after the barrier time) needs quotes near barrier times, not only on the hourly grid. With hourly quotes the barrier-time quote can be up to an hour late; the proposal therefore states the target as "proceeds ratio at the first collector read after the barrier touch, at the stated size", with the lag recorded and a maximum lag as a frozen parameter, and a missing or failed read censored. Until then every forecast carries NO_HISTORICAL_EXECUTABLE_DEPTH and EXECUTION_DATA_MISSING for size questions (`onchain.size_cap_usd`).

## Proposal D1: distribution event (requirements only)

`distribution_event_24h` needs, for every decision, the swaps of the mint's pools in the 24 h after the decision with the seller's wallet and a role for that wallet known at the decision. None of that exists (the lab DB holds swaps of 6 mints from 2026-10-05 to 07 only, with truncated signatures, and no pool per trade; wallet history SOURCE_BLOCKED). Rules any later definition must keep, implemented and tested now:

- a sale is a swap that sells the mint into a pool; a transfer is MOVEMENT_NOT_SALE whoever makes it, including a deposit to an exchange (P18);
- an exchange or custody address is CUSTODY_OR_EXCHANGE and never an insider, even when it also appears as a creator (P19);
- a developer is OBSERVED only when the address equals the token row's creator or dev wallet and does not look like a mint; the real token row of `55Vr2VpS...` names a dev wallet with the pump.fun mint suffix and is DEV_LABEL_SUSPECT;
- a cluster member is INFERRED with its confidence (RugCheck transfer networks), counted apart from observed insiders, never merged into them.

Unknown holders make a decision unlabelable, not negative.

## Precondition summary for any freeze

Collector deployed and running; at least 100 linked decisions per proposed target with 20 per class after censoring; the change control committed before the first outcome is computed; the link rule, size, drop, lags and censoring frozen in the registry with a new fingerprint; Phase 12 or 19 evaluates it on decisions after the freeze only.

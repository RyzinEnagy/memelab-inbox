# Backtesting and stress testing: decisions

Append-only. Each entry: id, date, decision, reason, evidence, who.

- D-BT-001 (2026-10-23, Elving): base the work on `feature/catalyst-firecrawl` @ f99c6c7, not `main`. Reason: newest code, includes the Firecrawl catalyst layer that Phases 06 and 09 reuse. Working branch `feature/backtesting`.
- D-BT-002 (2026-10-23, Elving): run all phases 00 to 17 with the guarded orchestrator, stopping only at a failed gate or an approval point.
- D-BT-003 (2026-10-23, Elving): delivery is both a pushed `feature/backtesting` branch (no merge, no PR merge) and a git bundle plus zip in `D:\memelab`.
- D-BT-004 (2026-10-23, Elving): spending approved: Firecrawl about 100 calls, Maxun Cloud one-shot runs (no schedules), Crawl4AI local runs. Free public market APIs (GeckoTerminal, DexScreener, Jupiter quote) read-only by default.
- D-BT-005 (2026-10-23, Phase 00): governance and evidence live in their own namespace (`docs/backtesting/`, `audits/backtesting/`); the social-intelligence records are left untouched. The prompt package is copied verbatim to `workplans/backtesting/`.
- D-BT-006 (2026-10-23, Phase 00): Phase 00 changes no lab code. Defects found (C1 transfer fee key, C2 unfinished candle in m13, C3 `_at` earlier than contained rows, m14/m22 window-key mismatch, m26 unit mismatch, m24 breakout label set) are recorded, not fixed. The backtesting engine defends against them on its own side instead of rewriting scoring modules.
- D-BT-007 (2026-10-23, Phase 00): the lab's exported history (`data/state/latest.json` on `main`, 89 commits) is the primary point-in-time discovery universe. `created_at` is the lab's own observation time; the git commit time is an independent upper bound on when a record existed.

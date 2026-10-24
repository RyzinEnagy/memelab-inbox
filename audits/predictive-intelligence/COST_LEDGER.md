# Predictive Intelligence: cost ledger

Every external call that can cost money is logged here before the next billable call (PI-D-004). Cap for the whole initiative: 150 Firecrawl credits. Any other paid service needs a new approval (PI-D-005).

Free calls (GeckoTerminal, DEX Screener, unauthenticated GitHub REST, PyPI, `git clone`, WebSearch, WebFetch) are listed in each phase's evidence, not here, unless a provider starts charging.

| Date (UTC) | Phase | Tool | Purpose | Credits | Running total |
|---|---|---|---|---:|---:|
| 2026-10-24 | 00 | none | no billable call was made in Phase 00 (Firecrawl MCP tools not used) | 0 | 0 |
| 2026-10-24 | 01 | none | no billable call; free calls only: 15 GeckoTerminal (coverage probe), 3 GitHub REST events (push times) | 0 | 0 |
| 2026-10-24 | 02 | none | no billable call; Firecrawl MCP tools not used; free calls only: GitHub (22 search attempts and 4 other REST or HTML probes, all refused by the session proxy, plus 1 rate-limit read), git ls-remote, blob-less and treeless clones, repos.ecosyste.ms and packages.ecosyste.ms, PyPI JSON, arXiv pages, raw GitHub files, 29 WebSearch calls; repair pass 2: about 75 ls-remote, 34 clones, 132 pin fetches, 60 full fetches, 28 treeless clones, about 50 ecosyste.ms calls, 25 PyPI, 5 WebSearch (counts in phase_02/PHASE_02_EVIDENCE.md) | 0 | 0 |
| 2026-10-24 | 03 | none | no billable call; Firecrawl MCP tools not used by the lead (the reviewers' brief forbade them); lead free calls only: 6 Hugging Face license file reads (TabPFN-3.5 and TabPFN-2), about 33 PyPI JSON reads and 3 downloads of the hazardous 0.2.0 wheel (11 MB, kept outside the repo), 3 shallow fetches of the mlfinlab fork, 1 sparse blob-less fetch of mlflow at its pin, 1 ls-remote and 3 tag fetches for MiroFish (counts in phase_03/PHASE_03_EVIDENCE.md) | 0 | 0 |
| 2026-10-24 | 03 repair pass | none | no billable call and no network call: the river crate check read the local crates.io cache, the TabPFN naming clause was read from the license file cached in the first pass (same sha256), the library reruns ran inside `unshare -n` and the other scripts have no network code | 0 | 0 |

Remaining Firecrawl allowance: 150 credits.

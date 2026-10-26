# PHASE 02: broad independent GitHub discovery

State: PASS. Date 2026-10-23. Entry gate: Phase 01 PASS (re-checked: ARCHITECTURE_DECISION, RUBRIC_LOCK present at 9e76138; no code to rerun).

## Evidence

- research/SEARCH_LOG.md: 30 GitHub API queries across six families (exact query, total_count, UTC), 4 Firecrawl developer searches, 3 curated lists cloned at pinned SHAs, 23 seeds, 2 citation/successor follows.
- research/raw/p02_github_search.txt (sha256 65e23b10086fe6e90ca0fa0a836b1f4b5411ed061944e89e9fad266ffb9ceb05) and raw/p02_github_search_hits.csv (273 hits, 268 unique).
- research/LONGLIST.csv: 73 unique repos with family, channel, HEAD sha from `git ls-remote` on 2026-10-23, stars/license at search, decision and reason. Families: CRY 16, EVT 15, VAL 15, AMM 14, VEC 7, CAT 6.
- research/CATEGORY_MAP.md, research/SHORTLIST20.md (25 for deep review).

## Gate

| Item | Result |
|---|---|
| >= 40 unique relevant repos | 72 resolvable (+1 seed not found) |
| >= 6 query families | 6 |
| >= 20 queued for source review | 25 |
| >= 5 low-star niche candidates | 5 shortlisted, more in longlist |
| No unverified capability labels | longlist records reasons only; capabilities are marked in Phase 03 from code |
| Maxun not classified as a backtesting engine | yes (not in longlist) |

## Negative review

1. Plausible claim: "every seed URL is a live repo." `git ls-remote https://github.com/dexterous/serum-dex HEAD` returns nothing: NOT_FOUND. Recorded, not replaced by a guess.
2. Plausible claim: "a memecoin-specific repo with a detailed README is a safe candidate." hzcx404/memecoin-trading-bots directs users to download zip archives from raw repository paths, a known malware-lure pattern; `Twilightfobeam/liquidity-sniper-bot-dd60` and siblings are templated spam. Both REJECT with no clone or install.

## Limitations

GitHub code/topic search unavailable without auth; repository search ANDs terms, so four phrase queries returned 0 (covered by other channels). Stars and licenses in the longlist are search-time metadata; Phase 03 re-reads LICENSE files.

NEXT ELIGIBLE PHASE: 03.

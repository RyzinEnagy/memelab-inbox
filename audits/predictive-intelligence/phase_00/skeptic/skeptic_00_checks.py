"""Skeptic checks for predictive-intelligence Phase 00. Read-only: reads git objects of a ref, writes nothing.

Usage: python3 skeptic_00_checks.py <repo path> [ref]   (default ref origin/main)

1. Launch-cohort outcome counts, three ways: the newest row per mint (what the data says now), any version, and the
   row the Phase 00 probe keeps (it walks git log newest first and overwrites, so the OLDEST row of each mint wins).
2. Decision lag: tokens.first_seen_at is db.now() (wall clock) at the first persist (db.py upsert_token, called in
   pipeline.persist_result in the same transaction as the thesis insert), so first_seen_at is a lower bound on when
   the first thesis row was written. Compare with the thesis's stamped created_at (= t = max collector _at).
"""
import collections
import json
import statistics
import subprocess
import sys

repo = sys.argv[1]
ref = sys.argv[2] if len(sys.argv) > 2 else "origin/main"


def git(*a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


shas = git("log", "--format=%H", ref, "--", "data/state/latest.json").split()   # newest first
versions = [json.loads(git("show", f"{s}:data/state/latest.json")).get("_tables", {}) for s in shas]

# 1. launch cohort
newest, oldest, ever = {}, {}, collections.defaultdict(set)
for T in versions:                                   # newest first
    for r in T.get("launch_cohort") or []:
        newest.setdefault(r["mint"], r)
        oldest[r["mint"]] = r                        # probe behaviour: last write wins = oldest version
        for k in ("mcap_24h", "mcap_7d", "mcap_30d"):
            if r.get(k) is not None:
                ever[k].add(r["mint"])
cnt = lambda rows, k: sum(1 for r in rows.values() if r.get(k) is not None)
print("launch cohort distinct mints", len(newest))
for k in ("mcap_24h", "mcap_7d", "mcap_30d"):
    print(f"  {k}: newest row {cnt(newest, k)}, any version {len(ever[k])}, oldest row (probe) {cnt(oldest, k)}")
print("  rug_flag == 1 in any version:", sum(1 for T in versions for r in T.get("launch_cohort") or [] if r.get("rug_flag") == 1))

# 2. decision lag
first_thesis = collections.defaultdict(lambda: float("inf"))
first_seen = collections.defaultdict(lambda: float("inf"))
for T in versions:
    for th in T.get("theses") or []:
        first_thesis[th["mint"]] = min(first_thesis[th["mint"]], th["created_at"])
    for tk in T.get("tokens") or []:
        if tk.get("first_seen_at"):
            first_seen[tk["mint"]] = min(first_seen[tk["mint"]], tk["first_seen_at"])
both = [m for m in first_thesis if first_seen[m] != float("inf")]
late = sorted((first_seen[m] - first_thesis[m]) / 60 for m in both if first_seen[m] > first_thesis[m])
print("mints with theses and a token row", len(both))
print("  earliest first_seen_at AFTER earliest thesis created_at:", len(late),
      "minutes p50 %.1f p90 %.1f max %.1f" % (statistics.median(late), late[int(0.9 * (len(late) - 1))], late[-1]) if late else "")

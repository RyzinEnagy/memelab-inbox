"""Phase 00 probe: what dated history the scheduled runs left in git.

Read-only. Walks every commit on a ref that touched data/state/latest.json (and the older root state/latest.json),
parses each version from git objects (never from the working tree) and summarises:
  - commit cadence and date range of the state export;
  - per-mint thesis snapshots (time, price, liquidity) across ALL historical exports (union by mint + created_at);
  - symbols shared by more than one mint (P01 exposure in real data);
  - rejected tokens and launch-cohort rug flags (do dead tokens stay in the data?).

Usage (from the repo root):
    python audits/predictive-intelligence/phase_00/probes/state_history_probe.py origin/main OUT.json

Writes only OUT.json (put it outside the repo). Makes no network call.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import subprocess
import sys


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def iso(t: float | None) -> str | None:
    if t is None:
        return None
    return dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%MZ")


def main(ref: str, out: str) -> None:
    res: dict = {"ref": ref, "ref_sha": git("rev-parse", ref).decode().strip()}
    for path in ("data/state/latest.json", "state/latest.json"):
        lines = git("log", "--format=%H %cI", ref, "--", path).decode().split("\n")
        commits = [ln.split(" ") for ln in lines if ln.strip()]
        res[path] = {"commits": len(commits), "first": commits[-1][1] if commits else None, "last": commits[0][1] if commits else None,
                     "per_day": dict(sorted(collections.Counter(c[1][:10] for c in commits).items()))}
    # union of thesis snapshots over every version of data/state/latest.json
    lines = git("log", "--format=%H", ref, "--", "data/state/latest.json").decode().split()
    snaps: dict[tuple[str, float], dict] = {}
    symbols: dict[str, set] = collections.defaultdict(set)
    chains: dict[str, str] = {}
    rejected: dict[str, float] = {}
    cohort: dict[str, dict] = {}
    parsed, failed = 0, 0
    for sha in lines:
        try:
            doc = json.loads(git("show", f"{sha}:data/state/latest.json"))
        except Exception:
            failed += 1
            continue
        parsed += 1
        tables = doc.get("_tables") or {k: v for k, v in doc.items() if isinstance(v, list)}
        for t in tables.get("tokens") or []:
            if t.get("symbol"):
                symbols[(t["symbol"] or "").upper()].add((t.get("chain") or "solana", t["mint"]))
            chains[t["mint"]] = t.get("chain") or "solana"
        for th in tables.get("theses") or []:
            key = (th["mint"], th["created_at"])
            if key in snaps:
                continue
            s = th.get("snapshot_json")
            try:
                s = json.loads(s) if isinstance(s, str) else (s or {})
            except Exception:
                s = {}
            snaps[key] = {"t": th["created_at"], "price": s.get("price"), "liquidity": s.get("liquidity"), "exit_cap_3pct": s.get("exit_cap_3pct"),
                          "score": th.get("score"), "status": th.get("status")}
        for r in tables.get("rejections") or []:
            rejected.setdefault(r["mint"], r.get("rejected_at"))
        for c in tables.get("launch_cohort") or []:
            cohort[c["mint"]] = c
    by_mint: dict[str, list] = collections.defaultdict(list)
    for (m, _), v in snaps.items():
        by_mint[m].append(v)
    counts = collections.Counter(len(v) for v in by_mint.values())
    with_price = {m: sorted(v, key=lambda x: x["t"]) for m, v in by_mint.items() if sum(1 for x in v if x["price"]) >= 2}
    spans_h = sorted(((v[-1]["t"] - v[0]["t"]) / 3600 for v in with_price.values()))
    gaps_h = sorted((b["t"] - a["t"]) / 3600 for v in with_price.values() for a, b in zip(v, v[1:]))
    q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
    collisions = {s: sorted(v) for s, v in symbols.items() if len({m for _, m in v}) >= 2}
    end = max(t for _, t in snaps) if snaps else 0
    stopped = sum(1 for v in with_price.values() if end - v[-1]["t"] > 72 * 3600)
    collapsed = sum(1 for v in with_price.values() if v[0]["price"] and v[-1]["price"] and v[-1]["price"] < 0.1 * max(x["price"] for x in v if x["price"]))
    last_status = collections.Counter(v[-1]["status"] for v in with_price.values())
    res.update({"priced_mints_last_seen_over_72h_before_end": stopped, "priced_mints_last_price_below_10pct_of_max": collapsed,
                "priced_mints_last_status": dict(last_status.most_common())})
    res.update({
        "versions_parsed": parsed, "versions_failed": failed,
        "thesis_snapshots_union": len(snaps), "mints_with_theses": len(by_mint),
        "snapshots_per_mint_histogram": dict(sorted(counts.items())),
        "mints_with_2plus_priced_snapshots": len(with_price),
        "priced_span_hours_p50_p90_max": [q(spans_h, .5), q(spans_h, .9), spans_h[-1] if spans_h else None],
        "gap_between_snapshots_hours_p10_p50_p90": [q(gaps_h, .1), q(gaps_h, .5), q(gaps_h, .9)],
        "first_snapshot": iso(min(t for _, t in snaps)) if snaps else None, "last_snapshot": iso(max(t for _, t in snaps)) if snaps else None,
        "tokens_union": len(chains), "tokens_by_chain": dict(collections.Counter(chains.values())),
        "symbols_with_2plus_mints": len(collisions), "symbol_collision_examples": {s: collisions[s][:4] for s in sorted(collisions, key=lambda s: -len(collisions[s]))[:5]},
        "rejected_mints_union": len(rejected),
        "launch_cohort_union": len(cohort), "launch_cohort_rug_flag_1": sum(1 for c in cohort.values() if c.get("rug_flag")),
        "launch_cohort_with_mcap_24h": sum(1 for c in cohort.values() if c.get("mcap_24h") is not None),
        "launch_cohort_with_mcap_7d": sum(1 for c in cohort.values() if c.get("mcap_7d") is not None),
        "launch_cohort_with_mcap_30d": sum(1 for c in cohort.values() if c.get("mcap_30d") is not None),
    })
    with open(out, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("symbol_collision_examples",)}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

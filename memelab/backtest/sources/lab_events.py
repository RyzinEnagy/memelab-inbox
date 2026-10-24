"""Catalyst records from the lab's own contemporaneous launch monitor (Phase 09).

The launch monitor exported `upcoming_launches` rows into every committed state file. A row is a lab observation of a
public, chain-derived event (pump.fun graduation to the AMM, Raydium LaunchLab launch, live curve), with:
  discovered_at   the lab's own first-seen time (decision time can never be earlier)
  first_trade_at  the claimed event time (untrusted; often earlier than discovered_at)
  contract_verified  1 when the contract came from chain data, not from a name or ticker match
The git commit that first contained the row is an independent upper bound on when the lab knew it. No crawl made
today is involved, so these are historical observations, not reconstructions.
"""
from __future__ import annotations

from pathlib import Path

from . import labstate

SOURCE_KIND = {"pump:grad": "GRADUATION", "pump:live": "CURVE_LIVE", "pump:mcap": "CURVE_MCAP", "ray:new": "LAUNCHLAB_NEW", "gt:new:solana": "NEW_POOL"}


def launch_catalysts(repo: Path | str, ref: str = "origin/main") -> list[dict]:
    """One record per (contract, source) at its first appearance across all committed state versions."""
    repo = Path(repo)
    first: dict[tuple[str, str], dict] = {}
    for commit, ct, path in labstate.state_versions(repo, ref):
        d = labstate.load_version(repo, commit, path)
        d = d or {}
        rows = d.get("upcoming_launches") or (d.get("_tables") or {}).get("upcoming_launches") or []
        for r in rows:
            mint, src = r.get("contract"), r.get("source") or "unknown"
            if not mint or not r.get("discovered_at"):
                continue
            key = (mint, src)
            if key in first:
                continue
            known = float(r["discovered_at"])
            first[key] = {
                "event_id": f"launch:{src}:{mint}", "chain": r.get("chain") or "solana", "mint": mint, "symbol": r.get("symbol"),
                "origin_group": f"lab:launch_monitor:{src}", "claim_type": SOURCE_KIND.get(src, "LAUNCH_OTHER"),
                "published_at": float(r["first_trade_at"]) if r.get("first_trade_at") else None,
                "event_time": float(r["first_trade_at"]) if r.get("first_trade_at") else known,
                "first_seen_at": known, "available_at": known, "committed_by": ct, "source_commit": commit,
                "verified": True, "denied": False, "mint_verified": bool(r.get("contract_verified")),
                "sentiment": 1 if src == "pump:grad" else 0, "historical_asof_proof": "CONTEMPORANEOUS_CAPTURE",
                "lab_status": r.get("status"), "risk_flags": r.get("risk_flags_json"), "launchpad": r.get("launchpad"),
                "pool_at_discovery": r.get("pool"), "curve_pool_at_discovery": r.get("curve_pool"),
            }
    out = sorted(first.values(), key=lambda x: (x["available_at"], x["mint"]))
    for x in out:
        if x["committed_by"] < x["available_at"]:          # a record cannot be committed before the lab saw it
            raise ValueError(f"commit before discovery for {x['mint']}")
    return out


def coverage(records: list[dict]) -> dict:
    from collections import Counter
    return {"records": len(records), "by_kind": dict(Counter(r["claim_type"] for r in records)),
            "mint_verified": sum(1 for r in records if r["mint_verified"]),
            "event_time_before_first_seen_h": sorted(round((r["first_seen_at"] - r["event_time"]) / 3600, 2) for r in records if r["published_at"]),
            "commit_lag_h": sorted(round((r["committed_by"] - r["first_seen_at"]) / 3600, 2) for r in records)}

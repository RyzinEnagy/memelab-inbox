"""Data-quality defenses: multi-source reconciliation, coverage and refusal policy.

Reconciliation compares two independent observations of the same moment: the lab's own spot price recorded in a
thesis snapshot (from its contemporaneous provider pulls) and the historical bar that contains that moment from
the bar provider. This is a quality check after the fact, never a decision input.
"""
from __future__ import annotations

import json
import statistics

from . import store


def reconcile_lab_vs_bars(con, universe_id: str = "lab_state_history", tf: int = 3600, tolerance: float = 0.10) -> dict:
    rows = con.execute("SELECT mint, entered_at, snapshot_json FROM bt_universe_members WHERE universe_id=? AND chain='solana' AND basis='THESIS'", (universe_id,)).fetchall()
    checked, inside, near, far, no_bar = 0, 0, 0, [], 0
    diffs = []
    for r in rows:
        snap = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
        px = snap.get("price")
        if not px:
            continue
        t = r["entered_at"]
        bar = con.execute("SELECT o,h,l,c,pool_address FROM bt_market_bars WHERE mint=? AND timeframe_s=? AND start<=? AND end>? "
                          "ORDER BY volume_usd DESC LIMIT 1", (r["mint"], tf, t, t)).fetchone()
        if not bar:
            no_bar += 1
            continue
        checked += 1
        if bar["l"] * (1 - 1e-9) <= px <= bar["h"] * (1 + 1e-9):
            inside += 1
            d = 0.0
        else:
            ref = bar["l"] if px < bar["l"] else bar["h"]
            d = abs(px / ref - 1)
            if d <= tolerance:
                near += 1
            else:
                far.append({"mint": r["mint"], "t": t, "lab_price": px, "bar_low": bar["l"], "bar_high": bar["h"], "pool": bar["pool_address"], "rel_diff": round(d, 4)})
        diffs.append(d)
    return {"theses_with_price": sum(1 for r in rows if (json.loads(r["snapshot_json"] or "{}") or {}).get("price")), "checked": checked,
            "no_bar_at_that_time": no_bar, "inside_bar_range": inside, "within_tolerance": near, "outside_tolerance": len(far),
            "median_rel_diff": statistics.median(diffs) if diffs else None, "tolerance": tolerance, "worst": sorted(far, key=lambda x: -x["rel_diff"])[:10]}


REFUSAL_POLICY = {
    "no_pool_valid_at_decision": "INSUFFICIENT_HISTORY",
    "pool_type_not_cpmm_and_no_observed_quote": "UNSUPPORTED_POOL",
    "bars_before_decision_below_warmup": "INSUFFICIENT_HISTORY",
    "last_bar_older_than_staleness_limit": "STALE_DATA",
    "provider_blocked": "SOURCE_BLOCKED",
    "lab_price_and_bars_disagree_beyond_tolerance": "PARTIAL_WITH_LIMITATIONS",
    "historical_reserves_requested": "INSUFFICIENT_EXECUTION_DATA",
}


def dataset_hash(con, mints: list[str], tf: int = 3600, cutoff: float | None = None) -> str:
    """Hash of the exact bars a study can see (by mint, pool, start, values, availability)."""
    q = "SELECT mint, pool_address, start, o, h, l, c, volume_usd, available_at FROM bt_market_bars WHERE timeframe_s=? AND mint IN (%s)" % ",".join("?" * len(mints))
    args = [tf, *mints]
    if cutoff is not None:
        q += " AND available_at<=?"
        args.append(cutoff)
    q += " ORDER BY mint, pool_address, start, available_at"
    return store.sha256([list(r) for r in con.execute(q, args)])


B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58_len(s: str) -> int | None:
    """Decoded byte length of a base58 string, or None if it has a non-base58 character."""
    n = 0
    for ch in s:
        i = B58.find(ch)
        if i < 0:
            return None
        n = n * 58 + i
    return (n.bit_length() + 7) // 8 + (len(s) - len(s.lstrip("1")))


def _one_edit(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def mint_integrity(con, universe_id: str = "lab_state_history", chain: str = "solana") -> dict:
    """Mint strings in the universe that cannot be real (not a 32-byte base58 key) or sit one edit away from another
    member (a likely corrupted copy). They are reported and kept separate: never merged by similarity, because a
    near-match is exactly how a fake token impersonates a real one."""
    ms = [r[0] for r in con.execute("SELECT DISTINCT mint FROM bt_universe_members WHERE universe_id=? AND chain=? ORDER BY mint", (universe_id, chain))]
    invalid = [m for m in ms if b58_len(m) != 32]
    by: dict[str, list[str]] = {}
    for m in ms:
        by.setdefault(m[:6], []).append(m)
    near = [(a, b) for v in by.values() for i, a in enumerate(v) for b in v[i + 1:] if _one_edit(a, b)]
    return {"mints": len(ms), "invalid_pubkey": invalid, "one_edit_pairs": near}

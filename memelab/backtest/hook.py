"""The one call the lab's scout and analyze commands make into the backtesting package (Phase 13).

Off by default (policy file data/backtest/policy.json or MEMELAB_BACKTEST=1). When off it returns None before
touching the backtest database, so scout and analyze output stay byte-identical. When on, it never raises and never
changes the analysis result's score, status or report: it returns a separate assessment record.
"""
from __future__ import annotations

import time


def maybe_assess(r: dict, policy: dict | None = None) -> dict | None:
    from . import assess
    policy = policy or assess.load_policy()
    if not policy.get("enabled"):
        return None
    if not isinstance(r, dict) or r.get("error") or "bundle" not in r:
        return {"state": "ERROR", "reason": "analysis result missing; nothing assessed", "retriable": True}
    t0 = time.time()
    try:
        out = assess.attach(r, policy)
    except Exception as e:                      # the lab's discovery never fails because of this module
        out = {"state": "ERROR", "error": f"{type(e).__name__}: {e}", "retriable": True, "mint": r.get("mint")}
    out["hook_wall_ms"] = round((time.time() - t0) * 1000, 1)
    return out


def one_line(a: dict | None) -> str | None:
    if not a:
        return None
    st = a.get("stress") or {}
    ms = (st.get("max_size") or {}).get("max_size_usd")
    return (f"backtest: {a.get('state')} | evidence {a.get('tier')} | stress {st.get('decision', 'n/a')}"
            + (f" | max size ${ms:,.0f} under caps" if ms else "") + (f" | flags {','.join(a['flags'])}" if a.get("flags") else "")
            + " | research only")

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


def enabled(policy: dict | None = None) -> bool:
    from . import assess
    return bool((policy or assess.load_policy()).get("enabled"))


def latest_assessment(chain: str, mint: str, con=None) -> dict | None:
    """Newest stored FAST assessment for {chain, mint}; None when there is none (or no backtest database yet)."""
    import json
    from . import store
    own = con is None
    if own:
        if not store.BT_DB_PATH.exists():
            return None
        con = store.connect()
    try:
        row = con.execute("SELECT result_json FROM bt_assessments WHERE chain=? AND mint=? AND stage='FAST' ORDER BY created_at DESC, id DESC LIMIT 1",
                          (chain, mint)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        if own:
            con.close()


def alert_context(chain: str | None, mint: str | None, policy: dict | None = None, con=None, now: float | None = None) -> dict | None:
    """What a token-specific research alert shows about backtesting. None when the policy is off (alerts unchanged).
    A missing or failed lookup is labeled UNTESTED, never left out and never read as positive."""
    if not enabled(policy):
        return None
    from . import report
    if not chain or not mint:
        return {"label": "UNTESTED", "why": "no chain and contract on this alert"}
    try:
        a = latest_assessment(chain, mint, con)
    except Exception as e:
        return {"label": "UNTESTED", "why": f"backtest lookup failed ({type(e).__name__})"}
    out = report.alert_label(a) | {"request_key": (a or {}).get("request_key"), "state": (a or {}).get("state"), "as_of": (a or {}).get("as_of")}
    if a and now is not None and a.get("as_of") and now - a["as_of"] > 24 * 3600:
        out["why"] += f"; assessment is {(now - a['as_of']) / 3600:.0f} h old"
    return out

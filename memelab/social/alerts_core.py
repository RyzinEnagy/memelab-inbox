"""Phase 15: research-only alerts over the Phase 14 feed (schema memelab.social.feed/1).

Pure: no I/O, no clock, no network. The caller passes the feed document, a view of earlier alert state and `now`.
This is not another detector: every candidate is read from a field the feed already computed (independence, registry
links, chronology flags, liquidity status, stance changes, window mentions). Nothing here scores, ranks, touches a
watchlist or a trade.

Policies (DECISIONS D-097 to D-104):
  convergence           several independent sources on one token or theme, at least some of them registry-linked or
                        on the policy allowlist (never chosen by follower count)
  wallet_corroboration  a Phase 12 CORROBORATION flag resting on a LINKED (verified) wallet, recent enough
  risk                  a new Phase 12 RISK flag, or no sell route in the newest exit check
  stance_switch         a source that was positive moves to negative, mixed or neutral
  conversation_growth   window mentions far above the item's own baseline of earlier snapshots, with independent
                        corroboration (repetition alone never qualifies)

Token-specific policies need a readable chain and contract and fresh source data; otherwise the candidate is
suppressed with a reason and nothing is sent. Every decision (alert or suppression) carries the policy, the reason and
the evidence it rests on.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, time as dtime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POLICY_SCHEMA = "memelab.social.alerts.policy/1"
ALERT_SCHEMA = "memelab.social.alert/1"
ENGINE_VERSION = "alerts-v1"
SEVERITIES = ("info", "notice", "warning")
POLICY_NAMES = ("convergence", "wallet_corroboration", "risk", "stance_switch", "conversation_growth")
FEED_SCHEMA = "memelab.social.feed/1"
DISCLAIMER = "Research only. Not a trade instruction, not a score, not a watchlist change."

DEFAULT_POLICY: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "version": "alerts-policy-v1",
    "tz": "America/New_York",
    "quiet_hours": {"start": "22:00", "end": "07:00"},
    "quiet_hours_bypass": [],                # severities allowed to go out during quiet hours; none by default
    "daily_cap": 8,                          # alerts per local calendar day (America/New_York), all policies together
    "min_interval_minutes": 60,              # no evaluation more often than this; scheduled runs are hourly at most
    "source_max_age_hours": 24.0,            # feed snapshot and item freshness limit
    "hold_max_hours": 14.0,                  # an alert held by quiet hours expires after this
    "dedupe_retention_days": 30,
    "retry": {"max_attempts": 4, "backoff_seconds": [300, 1800, 7200]},
    # per provider per day. Transports: file, telegram, email (what a message costs to send). Upstream: x_api, llm,
    # telegram_bot (paid-API spend recorded in social_api_spend; the scheduler skips a refresh step over its ceiling).
    "cost_ceilings_usd_per_day": {"file": 0.0, "telegram": 0.0, "email": 0.0, "x_api": 0.0, "llm": 0.0, "telegram_bot": 0.0},
    "transport_cost_usd": {"file": 0.0, "telegram": 0.0, "email": 0.0},
    "reputable_sources": [],                 # explicit allowlist of source ids or handles; registry-linked traders count too
    "policies": {
        "convergence": {"enabled": True, "severity": "notice", "cooldown_hours": 12.0, "min_independent_sources": 3,
                        "min_reputable_sources": 2, "token_specific": False},
        "wallet_corroboration": {"enabled": True, "severity": "notice", "cooldown_hours": 12.0, "attributions": ["LINKED"],
                                 "max_event_age_hours": 24.0, "token_specific": True},
        "risk": {"enabled": True, "severity": "warning", "cooldown_hours": 6.0, "max_event_age_hours": 48.0, "token_specific": True},
        "stance_switch": {"enabled": True, "severity": "notice", "cooldown_hours": 24.0, "from": ["positive"],
                          "to": ["negative", "mixed", "neutral"], "require_registry_trader": True, "max_event_age_hours": 48.0,
                          "token_specific": True},
        "conversation_growth": {"enabled": True, "severity": "info", "cooldown_hours": 24.0, "min_baseline_points": 3,
                                "baseline_points": 14, "min_ratio": 3.0, "min_mentions": 10, "min_independent_sources": 2,
                                "token_specific": False},
    },
    "trade_execution_impact": "none",
}

FORBIDDEN_KEYS = {"score", "status", "rank", "watchlist", "fatal_checks", "sizing", "orders", "order", "trade", "buy", "sell", "position_size"}


class AlertError(ValueError):
    pass


def _sha(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _merge(base: dict, over: dict, path: str = "") -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if k in FORBIDDEN_KEYS:
            raise AlertError(f"policy key {path}{k} would reach trading or scoring; alerts are research only")
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k not in ("cost_ceilings_usd_per_day", "transport_cost_usd"):
            out[k] = _merge(out[k], v, f"{path}{k}.")
        else:
            out[k] = copy.deepcopy(v)
    return out


def _hhmm(s: str) -> dtime:
    try:
        h, m = str(s).split(":")
        return dtime(int(h), int(m))
    except (ValueError, TypeError) as e:
        raise AlertError(f"time of day {s!r} must be HH:MM") from e


def zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise AlertError(f"unknown time zone {tz!r}") from e


def make_policy(overrides: dict | None = None) -> dict:
    """Default policy merged with overrides, validated. Returns the policy with its sha256 under 'policy_sha256'."""
    p = _merge(DEFAULT_POLICY, overrides or {})
    if p.get("schema") != POLICY_SCHEMA:
        raise AlertError(f"policy schema must be {POLICY_SCHEMA}")
    if p.get("trade_execution_impact") != "none":
        raise AlertError("trade_execution_impact must be none")
    zone(p["tz"])
    _hhmm(p["quiet_hours"]["start"]); _hhmm(p["quiet_hours"]["end"])
    if int(p["daily_cap"]) < 0 or int(p["daily_cap"]) > 50:
        raise AlertError("daily_cap must be between 0 and 50")
    if float(p["min_interval_minutes"]) < 60:
        raise AlertError("min_interval_minutes below 60 polls faster than the upstream refresh (hourly at most)")
    for s in p.get("quiet_hours_bypass") or []:
        if s not in SEVERITIES:
            raise AlertError(f"unknown severity {s!r} in quiet_hours_bypass")
    for name, cfg in p["policies"].items():
        if name not in POLICY_NAMES:
            raise AlertError(f"unknown alert policy {name!r}")
        if cfg.get("severity") not in SEVERITIES:
            raise AlertError(f"policy {name}: severity must be one of {', '.join(SEVERITIES)}")
        if float(cfg.get("cooldown_hours", 0)) < 1:
            raise AlertError(f"policy {name}: cooldown_hours must be at least 1")
    for k, v in p["cost_ceilings_usd_per_day"].items():
        if float(v) < 0:
            raise AlertError(f"cost ceiling for {k} is negative")
    body = {k: v for k, v in p.items() if k != "policy_sha256"}
    p["policy_sha256"] = _sha(body)
    return p


# ---------- time ----------

def local_day(ts: float, tz: str) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(zone(tz)).strftime("%Y-%m-%d")


def local_text(ts: float | None, tz: str) -> str:
    if ts is None:
        return "unknown"
    u = datetime.fromtimestamp(float(ts), timezone.utc)
    loc = u.astimezone(zone(tz))
    return f"{loc.strftime('%Y-%m-%d %H:%M %Z')} ({u.strftime('%Y-%m-%d %H:%M')} UTC)"


def in_quiet_hours(ts: float, policy: dict) -> bool:
    """Wall-clock test in the policy zone, so the window follows daylight saving time."""
    loc = datetime.fromtimestamp(ts, timezone.utc).astimezone(zone(policy["tz"])).time().replace(second=0, microsecond=0)
    a, b = _hhmm(policy["quiet_hours"]["start"]), _hhmm(policy["quiet_hours"]["end"])
    if a == b:
        return False
    return (a <= loc or loc < b) if a > b else (a <= loc < b)


# ---------- candidates ----------

def _label(it: dict) -> str:
    if it.get("kind") == "CONTRACT":
        return f"{it.get('symbol') or 'unnamed token'} on {it.get('chain') or 'unknown chain'} ({it.get('contract') or 'unreadable contract'})"
    return it.get("label") or str(it.get("item_id"))


def _reputable(it: dict, allow: set[str]) -> list[str]:
    out = []
    for w in it.get("who") or []:
        if "more" in w or w.get("role") != "INDEPENDENT_ORIGINAL":
            continue
        if (w.get("account_kind") or "UNKNOWN").upper() in ("BOT", "AGGREGATOR"):
            continue
        sid = (w.get("source_id") or "").lower()
        handle = (w.get("display") or "").split(" (", 1)[0].lower()
        if w.get("trader") or sid in allow or handle in allow:
            out.append(w.get("display"))
    return sorted(set(out))


def _base(it: dict, feed: dict, policy_name: str, cfg: dict) -> dict:
    prov = it.get("provenance") or {}
    return {"policy": policy_name, "severity": cfg["severity"], "item_id": it.get("item_id"), "kind": it.get("kind"),
            "label": _label(it), "chain": it.get("chain"), "contract": it.get("contract"), "symbol": it.get("symbol"),
            "links": [l for l in (it.get("links") or [])][:4],
            "provenance": {"feed_schema": feed.get("schema"), "feed_sha256": feed.get("feed_sha256"),
                           "narrative_run_id": prov.get("narrative_run_id"), "cluster_key": prov.get("cluster_key"),
                           "claims": prov.get("claims") or [], "chronology_runs": prov.get("chronology_runs") or [],
                           "market_fact_ids": prov.get("market_fact_ids") or [],
                           "snapshot_window": (feed.get("data_freshness") or {}).get("snapshot_window")},
            "freshness": {"item": (it.get("freshness") or {}).get("status"), "last_observed_at": (it.get("times") or {}).get("last_observed_at"),
                          "feed": (feed.get("data_freshness") or {}).get("status")},
            "fixture": bool(feed.get("fixture") or it.get("is_fixture"))}


def _cand(base: dict, *, cooldown_key: str, fingerprint: Any, reason: str, confidence: str, bucket: str, evidence: dict) -> dict:
    c = dict(base)
    c.update({"cooldown_key": cooldown_key, "reason": reason, "confidence": confidence, "bucket": bucket, "evidence": evidence})
    c["dedupe_key"] = _sha([base["policy"], base["item_id"], fingerprint])[:32]
    return c


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def candidates(feed: dict, policy: dict, *, now: float, baselines: dict[str, list[float]] | None = None) -> tuple[list[dict], list[dict]]:
    """Return (candidates, suppressed). Each suppressed entry has policy, item_id and a reason code with text.
    baselines: item_id -> earlier window-mention counts (oldest first), excluding the current snapshot."""
    if feed.get("schema") != FEED_SCHEMA:
        raise AlertError(f"alerts read {FEED_SCHEMA} documents only")
    P = policy["policies"]
    cands, supp = [], []
    max_age = float(policy["source_max_age_hours"]) * 3600
    feed_fresh = (feed.get("data_freshness") or {}).get("status") == "FRESH"
    allow = {str(s).lower().lstrip("@") for s in policy.get("reputable_sources") or []}
    baselines = baselines or {}

    def suppress(name, it, code, text):
        supp.append({"policy": name, "item_id": it.get("item_id") if it else None, "label": _label(it) if it else None,
                     "reason_code": code, "reason": text})

    def gate(name, it) -> bool:
        cfg = P.get(name) or {}
        if not cfg.get("enabled"):
            return False
        if cfg.get("token_specific"):
            if it.get("kind") != "CONTRACT" or not it.get("chain") or not it.get("contract"):
                suppress(name, it, "missing_token", "token-specific alert needs an exact chain and contract; this item has none")
                return False
        if not feed_fresh:
            suppress(name, it, "stale_source", f"feed data freshness is {(feed.get('data_freshness') or {}).get('status')}")
            return False
        last = (it.get("times") or {}).get("last_observed_at")
        if (it.get("freshness") or {}).get("status") != "FRESH" or last is None or now - last > max_age:
            suppress(name, it, "stale_source", "the newest observation for this item is older than the freshness limit")
            return False
        return True

    for it in feed.get("items") or []:
        ind = (it.get("independence") or {}).get("independent_sources")
        status = (it.get("independence") or {}).get("status")
        conf = (it.get("freshness") or {}).get("confidence") or "UNKNOWN"

        # convergence
        name = "convergence"
        cfg = P[name]
        if cfg.get("enabled") and ind is not None and ind >= 2 and gate(name, it):
            rep = _reputable(it, allow)
            if status != "ok":
                suppress(name, it, "insufficient_coverage", "independence could not be estimated")
            elif ind < cfg["min_independent_sources"]:
                suppress(name, it, "below_threshold", f"{ind} independent source(s), policy needs {cfg['min_independent_sources']}")
            elif len(rep) < cfg["min_reputable_sources"]:
                suppress(name, it, "not_reputable", f"{len(rep)} registry-linked or allowlisted source(s) among the independent ones, "
                                                    f"policy needs {cfg['min_reputable_sources']}")
            else:
                cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}", fingerprint=rep,
                                   reason=f"{ind} independent sources converge; {len(rep)} of them registry-linked or allowlisted: {', '.join(rep)}",
                                   confidence=conf, bucket="INFERENCE",
                                   evidence={"independent_sources": ind, "reputable": rep, "repeats": (it.get("independence") or {}).get("repeats")}))

        chron = it.get("chronology") or []
        # wallet corroboration
        name = "wallet_corroboration"
        cfg = P[name]
        corr = [f for f in chron if f.get("category") == "CORROBORATION"]
        if cfg.get("enabled") and corr and gate(name, it):
            for f in corr:
                if f.get("attribution") not in cfg["attributions"]:
                    suppress(name, it, "unverified_wallet", f"flag {f.get('flag')} rests on a {f.get('attribution')} wallet, policy needs "
                                                            f"{', '.join(cfg['attributions'])}")
                    continue
                if f.get("at") is None or now - f["at"] > cfg["max_event_age_hours"] * 3600:
                    suppress(name, it, "stale_event", f"wallet event behind {f.get('flag')} is older than {cfg['max_event_age_hours']} h or undated")
                    continue
                if f.get("at") > now + 300:
                    suppress(name, it, "future_event", "wallet event time is after the evaluation time")
                    continue
                cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}",
                                   fingerprint=[f.get("flag"), f.get("source_id"), f.get("at")],
                                   reason=f"monitored {f.get('attribution')} wallet activity is consistent with a claim ({f.get('flag')}, order {f.get('order_status')})",
                                   confidence="MODERATE" if f.get("bucket") == "INFERENCE" else "LOW", bucket=f.get("bucket") or "UNKNOWN",
                                   evidence={"flag": f.get("flag"), "rule": f.get("rule"), "at": f.get("at"), "source_id": f.get("source_id"),
                                             "chronology_run": f.get("run_id")}))

        # risk
        name = "risk"
        cfg = P[name]
        risks = [f for f in chron if f.get("category") == "RISK"]
        no_route = (it.get("liquidity") or {}).get("status") == "NO_SELL_ROUTE"
        if cfg.get("enabled") and (risks or no_route) and gate(name, it):
            for f in risks:
                if f.get("at") is not None and now - f["at"] > cfg["max_event_age_hours"] * 3600:
                    suppress(name, it, "stale_event", f"risk flag {f.get('flag')} is older than {cfg['max_event_age_hours']} h")
                    continue
                fp = [f.get("flag"), f.get("source_id"), f.get("at")]
                cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}|{f.get('flag')}", fingerprint=fp,
                                   reason=f"new risk evidence: {f.get('flag')} ({f.get('bucket')}, not proven, wallet {f.get('attribution')})",
                                   confidence="MODERATE" if f.get("bucket") == "INFERENCE" else "LOW", bucket=f.get("bucket") or "UNKNOWN",
                                   evidence={"flag": f.get("flag"), "rule": f.get("rule"), "at": f.get("at"), "source_id": f.get("source_id"),
                                             "chronology_run": f.get("run_id")}))
            if no_route:
                facts = [x for x in (it.get("liquidity") or {}).get("facts") or [] if x.get("field") == "sell_quote_out"]
                cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}|NO_SELL_ROUTE",
                                   fingerprint=["NO_SELL_ROUTE"],
                                   reason="no sell route in the newest exit check: treat as not exitable until a later check shows one",
                                   confidence="MODERATE", bucket="FACT" if facts and not facts[0].get("stale") else "INFERENCE",
                                   evidence={"liquidity_status": "NO_SELL_ROUTE", "facts": [x.get("fact_id") for x in facts]}))

        # stance switch
        name = "stance_switch"
        cfg = P[name]
        ch = (it.get("digest") or {}).get("changes") or []
        sw = [c for c in ch if (c.get("before") or {}).get("stance") in cfg["from"] and (c.get("after") or {}).get("stance") in cfg["to"]]
        if cfg.get("enabled") and sw and gate(name, it):
            for c in sw:
                if cfg.get("require_registry_trader") and not c.get("trader"):
                    suppress(name, it, "not_reputable", f"{c.get('who')} is not linked to a registry trader")
                    continue
                at = c.get("after_at")
                if at is None or now - at > cfg["max_event_age_hours"] * 3600:
                    suppress(name, it, "stale_event", f"the newer statement by {c.get('who')} is older than {cfg['max_event_age_hours']} h or undated")
                    continue
                b, a = c["before"]["stance"], c["after"]["stance"]
                cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}|{c.get('source_id') or c.get('who')}",
                                   fingerprint=[c.get("source_id") or c.get("who"), b, a, at],
                                   reason=f"{c.get('who')} was {b} and is now {a} ({c.get('basis')})",
                                   confidence="LOW", bucket="INFERENCE",
                                   evidence={"who": c.get("who"), "trader": c.get("trader"), "before": c.get("before"), "after": c.get("after"),
                                             "after_at": at, "basis": c.get("basis")}))

        # conversation growth
        name = "conversation_growth"
        cfg = P[name]
        cur = (it.get("activity") or {}).get("window_mentions")
        if cfg.get("enabled") and cur is not None and cur >= cfg["min_mentions"] and gate(name, it):
            pts = list(baselines.get(it["item_id"]) or [])[-int(cfg["baseline_points"]):]
            if len(pts) < cfg["min_baseline_points"]:
                suppress(name, it, "no_baseline", f"{len(pts)} earlier snapshot(s) recorded, policy needs {cfg['min_baseline_points']}")
            else:
                med = _median(pts)
                ratio = cur / max(med, 1.0)
                if ratio < cfg["min_ratio"]:
                    suppress(name, it, "below_threshold", f"{cur} mentions against a baseline median of {med:g} ({ratio:.1f}x, policy needs {cfg['min_ratio']}x)")
                elif ind is None or status != "ok" or ind < cfg["min_independent_sources"]:
                    suppress(name, it, "repetition_only", f"growth is {ratio:.1f}x but only {ind if ind is not None else 'an unknown number of'} "
                                                          f"independent source(s); repeats alone never qualify")
                else:
                    cands.append(_cand(_base(it, feed, name, cfg), cooldown_key=f"{name}|{it['item_id']}",
                                       fingerprint=[(feed.get("data_freshness") or {}).get("snapshot_window")],
                                       reason=f"{cur} mentions in the window against a baseline median of {med:g} over {len(pts)} earlier snapshots "
                                              f"({ratio:.1f}x), with {ind} independent sources",
                                       confidence=conf, bucket="HEURISTIC",
                                       evidence={"window_mentions": cur, "baseline_median": med, "baseline_points": len(pts), "ratio": round(ratio, 2),
                                                 "independent_sources": ind}))
    cands.sort(key=lambda c: (-SEVERITIES.index(c["severity"]), c["policy"], str(c["item_id"]), c["dedupe_key"]))
    return cands, supp


# ---------- rendering ----------

def render_text(a: dict, tz: str) -> str:
    """Plain text, no markup: safe for Telegram without parse_mode, for email and for a file. No post wording."""
    ev = a.get("evidence") or {}
    prov = a.get("provenance") or {}
    lines = []
    if a.get("fixture"):
        lines.append("FIXTURE DEMO: invented data, not a live alert.")
    lines += [f"memelab research alert, {a['severity'].upper()}: {a['policy'].replace('_', ' ')}",
              a["label"],
              f"Why: {a['reason']}",
              f"Confidence: {a['confidence']} ({a['bucket']})",
              f"Freshness: item {a['freshness'].get('item')}, feed {a['freshness'].get('feed')}, last observed {local_text(a['freshness'].get('last_observed_at'), tz)}"]
    if a.get("chain") and a.get("contract"):
        lines.append(f"Contract: {a['chain']}:{a['contract']}")
    for l in a.get("links") or []:
        lines.append(f"Source: {l.get('who')} {l.get('url')}")
    lines.append(f"Provenance: narrative run {prov.get('narrative_run_id')}, cluster {prov.get('cluster_key')}, claims "
                 f"{','.join(str(x) for x in prov.get('claims') or []) or 'none'}, chronology runs "
                 f"{','.join(str(x) for x in prov.get('chronology_runs') or []) or 'none'}, feed {str(prov.get('feed_sha256'))[:12]}")
    if ev.get("chronology_run") is not None:
        lines.append(f"Rule: {ev.get('rule')}, chronology run {ev.get('chronology_run')}")
    lines.append(f"Alert {a.get('alert_id', 'new')}, dedupe {a['dedupe_key'][:12]}, policy {a.get('policy_version')}")
    lines.append(DISCLAIMER)
    if a.get("fixture"):
        lines.append("FIXTURE DEMO: invented data, not a live alert.")
    return "\n".join(lines) + "\n"

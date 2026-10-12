"""Phase 14: readable, cited intelligence feed over stored social observations, claims and narratives.

Pure: no I/O, no clock, no model. feed_store.load_input gives the input document; build() turns it into one stable,
machine-readable feed (schema memelab.social.feed/1) and render() writes one of three markdown views from it:

  brief          the last-24-hour morning brief, narrative first (one block per token or theme, highest priority first)
  trader-digest  who said what about each token, current stance and disclosed position, changed positions and disagreements
  feed           the filterable list (chain, token, source, time window, risk)

Every item answers: what happened, first observed and first published, who said it, original links, independence
against repetition, why it matters, what is corroborated, what is speculation, reasons to doubt, the liquidity and exit
caveat, the research next step and data freshness and coverage.

Rules (DECISIONS D-091 to D-096):
  - grouped by exact token identity (chain, contract) or structured theme, never by author or by time alone;
  - ticker-only mentions are listed apart as unresolved and never joined to a token;
  - nothing from post wording, own-words summaries or the private store is rendered; handles, symbols, labels and links
    are reduced to a safe character set and markdown-escaped, so injected text cannot add links, headings or instructions;
  - priority is HEURISTIC and orders the feed only; it never reaches a score, a watchlist or a trade;
  - with no qualifying item the brief says "No supported high-priority observations." and invents nothing;
  - fixture input is watermarked at the top and bottom of every view and flagged in the JSON;
  - the same input gives the same JSON (feed_sha256) and the same markdown.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = "memelab.social.feed/1"
ENGINE_VERSION = "feed-v1"
VIEWS = ("brief", "trader-digest", "feed")
DEFAULTS = {"window_hours": 24.0, "stale_after_hours": 24.0, "max_links": 6, "max_people": 8}
PRIORITIES = ("HIGH", "MEDIUM", "LOW")
NO_SIGNAL = "No supported high-priority observations."
WATERMARK = ("FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.")
DISCLAIMER = ("Research notes only. Nothing here is a trade instruction, a score or a watchlist change; social attention says nothing "
              "about whether a token can be bought or sold.")
PROMO_FLAGS = {"burst_amplification": "many accounts amplified it inside a short burst (coordination hypothesis, HEURISTIC, not proven)",
               "identical_text_copies": "several accounts posted identical text (copy hypothesis, HEURISTIC, not proven)",
               "forward_origin_hidden": "forwards whose origin is hidden (origin unknown)",
               "late_observation": "items were first seen long after they were published"}
CHANGE_WHY = {"NEW": "new in this snapshot", "ACTIVITY_UP": "activity rose against the previous window",
              "ACTIVITY_DOWN": "activity fell against the previous window", "DORMANT": "went quiet", "REVIVED": "came back after going quiet",
              "INDEPENDENCE_CHANGED": "the number of independent sources changed", "STANCE_SHIFT": "the balance of opinion shifted",
              "CONFLICT_CHANGED": "sources started or stopped disagreeing", "STATUS_CHANGED": "coverage status changed"}
SPECULATIVE = ("opinion", "prediction", "question")


class FeedError(ValueError):
    pass


# ---------- safe text ----------

_MD = re.compile(r"([\\`*_{}\[\]<>#|!~])")
_CTRL = re.compile(r"[\x00-\x1f\x7f​-‏ -‮⁠-⁩﻿]")


def md(s: Any, limit: int = 60) -> str:
    """Escape for one markdown line: control and bidi characters removed, whitespace collapsed, markdown syntax escaped,
    length capped. Used on every value that came from a provider or a user."""
    if s is None:
        return "unknown"
    t = _CTRL.sub(" ", str(s))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        t = t[: limit - 1].rstrip() + "…"
    return _MD.sub(r"\\\1", t) or "unknown"


def safe_token(s: Any, pattern: str = r"[A-Za-z0-9_.\-]{1,40}") -> str | None:
    """Return s only when it is entirely made of the allowed characters (handles, symbols, ids)."""
    if s is None:
        return None
    t = str(s).strip().lstrip("@$")
    return t if re.fullmatch(pattern, t) else None


def safe_symbol(s: Any) -> str | None:
    return safe_token(s, r"[A-Za-z0-9_.\-]{1,20}")


def safe_contract(s: Any) -> str | None:
    return safe_token(s, r"(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,48}|[A-Za-z0-9:_\-]{20,90})")


def safe_chain(s: Any) -> str | None:
    return safe_token(s, r"[a-z0-9\-]{1,20}")


PRIVATE_LINK = re.compile(r"^(t\.me|telegram\.me)/(\+|joinchat/|c/)", re.I)


def safe_url(u: Any) -> str | None:
    """Public http(s) link or None. Drops credentials, query strings and fragments (tracking or injected text),
    private invite and private-chat links, non-ASCII hosts and anything that is not a plain URL."""
    if not u or not isinstance(u, str) or len(u) > 500 or _CTRL.search(u) or " " in u.strip():
        return None
    try:
        p = urlsplit(u.strip())
    except ValueError:
        return None
    if p.scheme.lower() not in ("http", "https") or not p.hostname or p.username or p.password:
        return None
    host = p.hostname.lower()
    if not re.fullmatch(r"[a-z0-9.\-]{1,253}", host) or "." not in host:
        return None
    try:
        port = p.port
    except ValueError:
        return None
    if PRIVATE_LINK.match(host + (p.path or "/")):
        return None
    path = quote(p.path or "/", safe="/-._~%")
    out = f"{p.scheme.lower()}://{host}{':' + str(port) if port else ''}{path}"
    return out if len(out) <= 300 else None


def link(u: str | None, label: str) -> str:
    return f"[{md(label, 40)}](<{u}>)" if u else f"{md(label, 40)} (no public link)"


# ---------- time ----------

def zone(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise FeedError(f"unknown time zone {tz!r}") from e


def fmt_time(ts: float | None, tz: str = "UTC") -> str:
    """'2026-10-12 08:00 EDT (12:00 UTC)' in a named zone, '2026-10-12 12:00 UTC' in UTC, 'unknown' for None."""
    if ts is None:
        return "unknown"
    u = datetime.fromtimestamp(float(ts), timezone.utc)
    if (tz or "UTC") == "UTC":
        return u.strftime("%Y-%m-%d %H:%M UTC")
    loc = u.astimezone(zone(tz))
    same_day = loc.date() == u.date()
    return f"{loc.strftime('%Y-%m-%d %H:%M %Z')} ({u.strftime('%H:%M' if same_day else '%Y-%m-%d %H:%M')} UTC)"


def _hours(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else round((b - a) / 3600.0, 1)


def parse_time(v: Any) -> float | None:
    """Epoch seconds or ISO 8601 with an offset. A naive ISO time is refused (its zone would be a guess)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return float(s)
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise FeedError(f"cannot read time {v!r}") from e
    if d.tzinfo is None:
        raise FeedError(f"time {v!r} has no zone offset")
    return d.timestamp()


def _sha(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# ---------- people ----------

def _who(m: dict) -> dict:
    handle = safe_token(m.get("handle"))
    trader = safe_token(m.get("trader_id"))
    sid = m.get("source_id") or m.get("account_id")
    platform = safe_chain(m.get("platform")) or "unknown"
    if handle:
        display = f"{handle} ({platform})"
    elif sid and safe_token(str(sid).replace(":", "_"), r"[A-Za-z0-9_.\-]{1,60}"):
        display = f"unnamed {platform} source {str(sid).replace(':', '_')[-16:]}"
    else:
        display = f"unattributed {platform} item"
    return {"display": display, "source_id": sid if sid and safe_token(str(sid), r"[A-Za-z0-9_.:\-]{1,90}") else None,
            "trader": trader, "trader_label": md(m.get("trader_label"), 40) if trader and m.get("trader_label") else None,
            "account_kind": m.get("account_kind") or "UNKNOWN", "platform": platform}


def _stance(m: dict) -> str:
    if m.get("sarcasm_suspected"):
        return "unclear (sarcasm suspected)"
    return m.get("stance") or m.get("member_stance") or "unknown"


# ---------- one item ----------

def _what(c: dict, label: str, people: int) -> str:
    n, ind = c.get("item_count") or 0, c.get("independent_source_count")
    amp, dep = c.get("amplifier_count") or 0, c.get("dependent_count") or 0
    kind = "token " if c["cluster_kind"] == "CONTRACT" else ""
    cats: dict[str, int] = {}
    for m in c.get("members") or []:
        if m.get("role") != "AMPLIFIER" and m.get("category"):
            cats[m["category"]] = cats.get(m["category"], 0) + 1
    catx = ", ".join(f"{k} {v}" for k, v in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))) or "no classified claims"
    indx = "independence not estimable" if ind is None else f"{ind} independent source(s)"
    return (f"{n} post(s) about the {kind}{label} from {people} account(s): {indx}, {amp} repeat(s) (reposts, forwards, quotes that repeat) "
            f"and {dep} reply or copy item(s). Claim types among originals: {catx}.")


def _corroborated(c: dict) -> list[str]:
    out = []
    ind = c.get("independent_source_count")
    if c.get("status") == "ok" and ind is not None and ind >= 2:
        out.append(f"That the {('token' if c['cluster_kind'] == 'CONTRACT' else 'theme')} is being discussed: {ind} independent sources (INFERENCE). "
                   "What they claim about it is not corroborated by this.")
    elif ind == 1:
        out.append("Nothing: one independent source only.")
    else:
        out.append("Nothing: independence could not be estimated.")
    for f in c.get("chrono_flags") or []:
        if f.get("category") == "CORROBORATION":
            out.append(f"Chronology {md(f.get('flag'), 50)} ({f.get('bucket')}, order {f.get('order_status')}, rule {md(f.get('rule'), 50)}, run {f.get('run_id')}).")
    return out


def _speculation(c: dict) -> list[str]:
    origs = [m for m in c.get("members") or [] if m.get("role") != "AMPLIFIER"]
    spec = sum(1 for m in origs if m.get("assertion_type") in SPECULATIVE)
    facts = sum(1 for m in origs if m.get("assertion_type") == "claimed_fact")
    unver = sum(1 for m in origs if m.get("assertion_type") == "claimed_fact" and m.get("verification") != "present_in_text")
    cond = sum(1 for m in origs if m.get("conditional"))
    out = []
    if spec:
        out.append(f"{spec} of {len(origs)} original claim(s) are opinion, prediction or question.")
    if facts:
        out.append(f"{facts} claim(s) state something as fact; {unver} of them are unverified text claims (the lab has not checked them).")
    if cond:
        out.append(f"{cond} claim(s) are conditional.")
    if not out:
        out.append("No claim classification stored for these posts; treat every statement as unverified." if origs else "No original claims.")
    return out


def _doubts(c: dict, *, as_of: float, stale_after_h: float, risk_names: list[str]) -> list[str]:
    out = []
    if c.get("status") == "insufficient_coverage":
        out.append("Coverage is insufficient: " + (", ".join(md(r, 60) for r in c.get("reasons") or []) or "reason not recorded") + ".")
    if (c.get("coverage") or {}).get("counts_are_lower_bounds"):
        out.append("Counts are lower bounds (partial coverage).")
    if c.get("conflicted"):
        st = c.get("stance") or {}
        out.append("Sources disagree (" + ", ".join(f"{k} {v}" for k, v in sorted(st.items())) + "); not resolved here.")
    for f in c.get("flags") or []:
        name = f.get("flag")
        if name in PROMO_FLAGS:
            out.append(PROMO_FLAGS[name] + ".")
    if (c.get("unobserved_origin_count") or 0) > 0:
        out.append(f"{c['unobserved_origin_count']} repeat(s) point at an original the collector never saw.")
    ms = c.get("members") or []
    gone = sorted({m.get("source_state") for m in ms if (m.get("source_state") or "accessible") != "accessible"})
    if gone:
        out.append("Some items are no longer accessible (" + ", ".join(md(g.split(":", 1)[-1], 20) for g in gone) + ").")
    unknown_auth = sum(1 for m in ms if m.get("role") == "UNVERIFIED_ORIGINAL")
    if unknown_auth:
        out.append(f"{unknown_auth} original(s) come from bots, aggregators or unknown authors and do not count as independent.")
    if any(m.get("sarcasm_suspected") for m in ms):
        out.append("Sarcasm suspected in at least one post; its stance is not counted.")
    if any(m.get("injection_suspected") for m in ms):
        out.append("At least one post looked like it was written to instruct an automated reader (injection suspected); none of its wording is used.")
    if c.get("confidence") in ("LOW", "UNKNOWN"):
        out.append(f"Narrative confidence {c.get('confidence')}.")
    if c.get("freshness") == "STALE" or (c.get("last_observed_at") is not None and as_of - c["last_observed_at"] > stale_after_h * 3600):
        out.append(f"Stale: newest observation {_hours(c.get('last_observed_at'), as_of)} h before as of.")
    for r in risk_names:
        out.append(r)
    if c.get("independent_source_count") == 1:
        out.append("Single independent source.")
    return out or ["No specific doubt recorded beyond the general limits in the footer."]


def _liquidity(c: dict, *, as_of: float, tz: str) -> dict:
    if c["cluster_kind"] != "CONTRACT":
        return {"status": "NOT_A_TOKEN", "caveat": "A theme, not a token: check liquidity and exit for each linked contract separately.", "facts": []}
    facts, lines = [], []
    status = "NO_DATA"
    for f in c.get("market") or []:
        stale = f.get("valid_until") is not None and f["valid_until"] < as_of
        prov = md(f.get("provider"), 30)
        if f["field"] == "sell_quote_out" and (f.get("value_str") or "").upper() == "NO_ROUTE":
            status = "NO_SELL_ROUTE"
            lines.append(f"No sell route found by {prov} at {fmt_time(f.get('fetched_at'), tz)} ({f.get('bucket')}{', stale' if stale else ''}).")
        elif f.get("value_num") is not None:
            if status == "NO_DATA":
                status = "STALE" if stale else "REPORTED"
            unit = md(f.get("unit"), 10)
            lines.append(f"{f['field'].replace('_', ' ')}: {f['value_num']:,.0f} {unit} per {prov} at {fmt_time(f.get('fetched_at'), tz)} "
                         f"({f.get('bucket')}{', stale' if stale else ''}).")
        facts.append({"field": f["field"], "value_num": f.get("value_num"), "value_str": f.get("value_str"), "unit": f.get("unit"),
                      "provider": f.get("provider"), "fetched_at": f.get("fetched_at"), "bucket": f.get("bucket"), "stale": stale,
                      "fact_id": f.get("fact_id"), "url": safe_url(f.get("source_url"))})
    if status == "NO_DATA":
        caveat = ("No liquidity or exit data stored for this contract. Attention says nothing about whether a position could be exited; "
                  "run the structural checks before anything else.")
    elif status == "NO_SELL_ROUTE":
        caveat = " ".join(lines) + " Treat as not exitable until a later check shows a route."
    else:
        caveat = " ".join(lines) + " Reported pool liquidity is not exit depth; a sell quote at your size is the real test."
    return {"status": status, "caveat": caveat, "facts": facts}


def _next_step(c: dict, run_id: Any, has_risk: bool) -> str:
    if c["cluster_kind"] != "CONTRACT":
        tag = safe_token(c["cluster_key"].split(":", 1)[-1], r"[a-z0-9_\-]{1,40}") or "unknown"
        return (f"Theme only. Look at the linked contracts one by one; `python -m memelab social narrative-why --run {run_id} "
                f"--cluster tag:{tag}` lists the posts behind it.")
    chain, contract = safe_chain(c.get("chain")) or "unknown", safe_contract(c.get("contract")) or "unknown"
    step = (f"Run the existing structural checks on {chain}:{contract} (scout or analyze) before reading anything into the attention. "
            f"Provenance: `python -m memelab social narrative-why --run {run_id} --cluster ca:{chain}:{contract}`.")
    if has_risk:
        step += f" Review the chronology: `python -m memelab social chrono flags --token {chain}:{contract}`."
    return step


def _priority(c: dict, *, in_window: bool, stale: bool, has_risk: bool) -> tuple[str, str]:
    ind = c.get("independent_source_count")
    if not in_window:
        return "LOW", "no activity inside the window"
    if c.get("status") != "ok":
        return "LOW", "coverage insufficient"
    if stale:
        return "LOW", "stale data"
    if has_risk:
        return "HIGH", "a chronology risk flag rests on a linked or self-claimed wallet"
    if ind is not None and ind >= 2:
        return "HIGH", f"{ind} independent sources, fresh"
    return "MEDIUM", "one independent source or not estimable"


def _people(c: dict, tz: str, max_people: int) -> list[dict]:
    """Originals, replies and copies by source (latest claim of each), oldest first. Repeats (reposts, forwards, quotes
    that repeat) are not listed one by one: the item counts them and links the first two."""
    order = {"INDEPENDENT_ORIGINAL": 0, "UNVERIFIED_ORIGINAL": 1, "DEPENDENT": 2}
    latest: dict[tuple, dict] = {}
    amps = []
    for m in sorted(c.get("members") or [], key=lambda m: (m.get("event_time") or 0, m.get("claim_id") or 0)):
        if m.get("role") == "AMPLIFIER":
            amps.append(m)
            continue
        w = _who(m)
        latest[(w["source_id"] or w["display"], m.get("role"))] = m
    ms = sorted(latest.values(), key=lambda m: (order.get(m.get("role"), 9), m.get("event_time") or 0, m.get("claim_id") or 0))

    def row(m):
        w = _who(m)
        return {**w, "role": m.get("role"), "time": m.get("event_time"), "time_basis": m.get("event_time_basis"),
                "time_text": fmt_time(m.get("event_time"), tz), "stance": _stance(m), "position": m.get("author_position") or "not_disclosed",
                "assertion_type": m.get("assertion_type"), "item_key": safe_token(m.get("item_key"), r"[A-Za-z0-9_.:\-]{1,120}"),
                "url": safe_url(m.get("original_url")),
                "access_mode": m.get("access_mode")}
    out = [row(m) for m in ms]
    more = max(0, len(out) - max_people)
    out = out[:max_people]
    out += [row(m) for m in amps[:2]]
    if more:
        out.append({"more": more, "what": "original or dependent source(s)"})
    if len(amps) > 2:
        out.append({"more": len(amps) - 2, "what": "repeat account(s)"})
    return out


def _digest(c: dict, tz: str) -> dict:
    """Current stance per source (latest claim, amplifiers and sarcasm excluded), changes against the previous comparable
    snapshot and inside this one, and the disagreement as counts. Nothing is resolved or averaged."""
    latest: dict[str, dict] = {}
    within: dict[str, list[str]] = {}
    for m in sorted(c.get("members") or [], key=lambda m: (m.get("event_time") or 0, m.get("claim_id") or 0)):
        sid = m.get("source_id")
        if not sid or m.get("role") == "AMPLIFIER" or m.get("sarcasm_suspected"):
            continue
        st = m.get("stance") or m.get("member_stance") or "unknown"
        within.setdefault(sid, [])
        if not within[sid] or within[sid][-1] != st:
            within[sid].append(st)
        latest[sid] = m
    people, changes = [], []
    for sid in sorted(latest, key=lambda s: (latest[s].get("event_time") or 0, s)):
        m = latest[sid]
        w = _who(m)
        st = m.get("stance") or m.get("member_stance") or "unknown"
        pos = m.get("author_position") or "not_disclosed"
        people.append({**w, "stance": st, "position": pos, "time": m.get("event_time"), "time_text": fmt_time(m.get("event_time"), tz),
                       "url": safe_url(m.get("original_url")), "role": m.get("role")})
        prev = (c.get("prev_stances") or {}).get(sid)
        if prev and (prev.get("stance") != st or (prev.get("author_position") or "not_disclosed") != pos):
            changes.append({"who": w["display"], "trader": w["trader"], "before": {"stance": prev.get("stance"), "position": prev.get("author_position")},
                            "after": {"stance": st, "position": pos}, "basis": f"previous snapshot run {prev.get('run_id')}",
                            "before_time": fmt_time(prev.get("event_time"), tz), "after_time": fmt_time(m.get("event_time"), tz)})
        elif len(within.get(sid, [])) > 1:
            changes.append({"who": w["display"], "trader": w["trader"], "before": {"stance": within[sid][-2], "position": None},
                            "after": {"stance": st, "position": pos}, "basis": "inside this snapshot", "before_time": None,
                            "after_time": fmt_time(m.get("event_time"), tz)})
    sides: dict[str, list[str]] = {}
    for p in people:
        if p["stance"] in ("positive", "negative", "mixed"):
            sides.setdefault(p["stance"], []).append(p["display"])
    disagree = len({s for s in sides if s in ("positive", "negative")}) == 2 or bool(c.get("conflicted"))
    return {"people": people, "changes": changes, "disagreement": {"present": disagree, "sides": {k: sorted(v) for k, v in sorted(sides.items())}}}


def _item(c: dict, *, as_of: float, win_start: float, tz: str, run_id: Any, opts: dict) -> dict:
    is_contract = c["cluster_kind"] == "CONTRACT"
    sym = safe_symbol(c.get("symbol"))
    chain, contract = safe_chain(c.get("chain")), safe_contract(c.get("contract"))
    if is_contract:
        label = f"{sym or 'unnamed token'} on {chain or 'unknown chain'} ({contract or 'unreadable contract'})"
    else:
        tag = safe_token(c["cluster_key"].split(":", 1)[-1], r"[a-z0-9_\-]{1,40}")
        label = f"theme {tag or 'unreadable tag'}"
    last, first = c.get("last_observed_at"), c.get("first_observed_at")
    in_window = last is not None and last >= win_start and (first is None or first <= as_of)
    stale_h = opts["stale_after_hours"]
    stale = c.get("freshness") == "STALE" or last is None or as_of - last > stale_h * 3600
    risk_flags = [f for f in c.get("chrono_flags") or [] if f.get("category") == "RISK"]
    promo = [f.get("flag") for f in c.get("flags") or [] if f.get("flag") in PROMO_FLAGS and f.get("flag") != "late_observation"]
    risk_names = [f"Chronology risk {md(f.get('flag'), 50)} ({f.get('bucket')}, not proven, wallet {f.get('attribution')}, rule {md(f.get('rule'), 50)}, run {f.get('run_id')})."
                  for f in risk_flags]
    has_risk = bool(risk_flags)
    pr, basis = _priority(c, in_window=in_window, stale=stale, has_risk=has_risk)
    people = _people(c, tz, opts["max_people"])
    accounts = {p.get("source_id") or p.get("display") for p in people if "more" not in p}
    links = []
    for p in people:
        if p.get("url") and p["url"] not in [x["url"] for x in links] and len(links) < opts["max_links"]:
            links.append({"url": p["url"], "who": p["display"], "role": p["role"]})
    why = [CHANGE_WHY[ch] for ch in c.get("changes") or [] if ch in CHANGE_WHY]
    if in_window and not stale and (c.get("independent_source_count") or 0) >= 2:
        why.append("several unrelated sources found it on their own, which is the earliest public signal this lab can see")
    if has_risk:
        why.append("a timeline flag suggests trading by a linked or self-claimed wallet around the posts")
    if promo:
        why.append("the pattern of repetition may be promotion rather than discovery")
    if not why:
        why.append("ongoing discussion with no change recorded")
    ws = c.get("windows") or {}
    cov = c.get("coverage") or {}
    platforms = {k: v.get("statuses") for k, v in sorted((cov.get("platforms") or {}).items())}
    item = {
        "item_id": c["cluster_key"], "kind": c["cluster_kind"], "label": label, "symbol": sym, "chain": chain, "contract": contract,
        "priority": pr, "priority_basis": basis, "priority_bucket": "HEURISTIC", "in_window": in_window,
        "what_happened": _what(c, label, c.get("source_count") or len(accounts)),
        "times": {"first_observed_at": first, "earliest_published_at": c.get("earliest_published_at"), "last_observed_at": last,
                  "first_observed": fmt_time(first, tz), "earliest_published": fmt_time(c.get("earliest_published_at"), tz),
                  "last_observed": fmt_time(last, tz),
                  "publication_lag_minutes": None if first is None or c.get("earliest_published_at") is None
                  else round((first - c["earliest_published_at"]) / 60.0, 1)},
        "who": people, "links": links,
        "independence": {"status": c.get("status"), "independent_sources": c.get("independent_source_count"),
                         "origin_groups": c.get("independent_group_count"), "repeats": c.get("amplifier_count"),
                         "dependent": c.get("dependent_count"), "unobserved_origins": c.get("unobserved_origin_count"),
                         "items": c.get("item_count"), "accounts": c.get("source_count"),
                         "statement": ("not estimable" if c.get("independent_source_count") is None else
                                       f"{c.get('independent_source_count')} independent of {c.get('source_count')} account(s); "
                                       f"{c.get('amplifier_count')} repeat(s) counted once with their original")},
        "why_it_matters": why, "why_bucket": "HEURISTIC",
        "corroborated": _corroborated(c), "speculation": _speculation(c),
        "doubts": _doubts(c, as_of=as_of, stale_after_h=stale_h, risk_names=risk_names),
        "liquidity": _liquidity(c, as_of=as_of, tz=tz), "next_step": _next_step(c, run_id, has_risk),
        "freshness": {"status": "STALE" if stale else "FRESH", "last_observed_age_hours": _hours(last, as_of),
                      "coverage": {"platforms": platforms, "counts_are_lower_bounds": bool(cov.get("counts_are_lower_bounds"))},
                      "confidence": c.get("confidence"),
                      "mentions_last_24h": (ws.get("86400") or {}).get("current")},
        "risk": {"has_risk": has_risk or bool(promo), "chronology_risk_flags": sorted({str(f.get("flag")) for f in risk_flags}),
                 "promotion_hypotheses": sorted(set(promo))},
        "conflicted": bool(c.get("conflicted")), "stance": c.get("stance") or {},
        "digest": _digest(c, tz),
        "sources": sorted({str(x) for m in c.get("members") or [] for x in (safe_token(m.get("source_id"), r"[A-Za-z0-9_.:\-]{1,90}"),
                                                                          safe_token(m.get("account_id"), r"[A-Za-z0-9_.:\-]{1,90}"),
                                                                          safe_token(m.get("trader_id")),
                                                                          (safe_token(m.get("handle")) or "").lower() or None) if x}),
        "linked_tokens": c.get("linked_tokens") or {},
        "chains": sorted(safe_chain(x) or "unknown" for x in c.get("chains") or []),
        "is_fixture": any(m.get("access_mode") == "fixture" for m in c.get("members") or []) or any(f.get("is_fixture") for f in c.get("chrono_flags") or []),
        "provenance": {"narrative_run_id": run_id, "cluster_key": c["cluster_key"],
                       "chronology_runs": sorted({f.get("run_id") for f in c.get("chrono_flags") or [] if f.get("run_id") is not None}),
                       "market_fact_ids": sorted(f.get("fact_id") for f in c.get("market") or [] if f.get("fact_id") is not None),
                       "claims": sorted(m.get("claim_id") for m in c.get("members") or [] if m.get("claim_id") is not None)},
    }
    return item


# ---------- filters ----------

def make_filters(*, chain: str | None = None, token: str | None = None, source: str | None = None, since: Any = None, until: Any = None,
                 risk: str | None = None, min_priority: str | None = None) -> dict:
    f = {"chain": chain.lower() if chain else None, "token": token, "source": source.lower().lstrip("@") if source else None,
         "since": parse_time(since), "until": parse_time(until), "risk": risk, "min_priority": min_priority}
    if risk not in (None, "any", "none") and not safe_token(risk, r"[A-Za-z0-9_]{1,60}"):
        raise FeedError("--risk takes any, none or one flag name")
    if min_priority not in (None, *PRIORITIES):
        raise FeedError(f"--min-priority takes one of {', '.join(PRIORITIES)}")
    if f["since"] is not None and f["until"] is not None and f["since"] > f["until"]:
        raise FeedError("--since is after --until")
    return f


def _token_match(it: dict, token: str) -> tuple[bool, bool]:
    """(matches, by_symbol). Contract and chain:contract match identity; $SYM or a bare short word matches the displayed
    symbol only and is reported as a symbol match (not identity)."""
    t = token.strip()
    if ":" in t and not t.startswith("$"):
        ch, ct = t.split(":", 1)
        return (it.get("chain") == ch.lower() and (it.get("contract") or "").lower() == ct.lower()), False
    if t.startswith("$") or len(t) <= 15:
        s = t.lstrip("$").upper()
        return ((it.get("symbol") or "").upper() == s or (it.get("contract") or "").lower() == t.lower()), (it.get("symbol") or "").upper() == s
    return (it.get("contract") or "").lower() == t.lower(), False


def _keep(it: dict, f: dict) -> bool:
    if f["chain"] and f["chain"] not in (it.get("chains") or []) and it.get("chain") != f["chain"]:
        return False
    if f["token"] and not _token_match(it, f["token"])[0]:
        return False
    if f["source"] and f["source"] not in {s.lower() for s in it["sources"]}:
        return False
    first, last = it["times"]["first_observed_at"], it["times"]["last_observed_at"]
    if f["since"] is not None and (last is None or last < f["since"]):
        return False
    if f["until"] is not None and (first is None or first > f["until"]):
        return False
    if f["risk"] == "any" and not it["risk"]["has_risk"]:
        return False
    if f["risk"] == "none" and it["risk"]["has_risk"]:
        return False
    if f["risk"] not in (None, "any", "none") and f["risk"] not in it["risk"]["chronology_risk_flags"] + it["risk"]["promotion_hypotheses"]:
        return False
    if f["min_priority"] and PRIORITIES.index(it["priority"]) > PRIORITIES.index(f["min_priority"]):
        return False
    return True


# ---------- build ----------

def build(inp: dict, *, tz: str = "UTC", filters: dict | None = None, options: dict | None = None, fixture_demo: bool = False) -> dict:
    """Deterministic: the same input, zone, filters and options give the same document and feed_sha256."""
    zone(tz)
    opts = {**DEFAULTS, **(options or {})}
    f = filters or make_filters()
    as_of = float(inp["as_of"])
    win_start = as_of - opts["window_hours"] * 3600
    snap = inp.get("snapshot")
    run_id = snap["run_id"] if snap else None
    items = [_item(c, as_of=as_of, win_start=win_start, tz=tz, run_id=run_id, opts=opts) for c in inp.get("clusters") or []]
    seen, uniq = set(), []
    for it in items:  # the same cluster passed twice counts once
        if it["item_id"] not in seen:
            seen.add(it["item_id"])
            uniq.append(it)
    uniq.sort(key=lambda it: (PRIORITIES.index(it["priority"]), 0 if it["kind"] == "CONTRACT" else 1,
                              -(it["independence"]["independent_sources"] or 0), -(it["times"]["last_observed_at"] or 0), it["item_id"]))
    kept = [it for it in uniq if _keep(it, f)]
    unresolved = []
    for u in inp.get("unresolved") or []:
        sym = safe_symbol(u.get("symbol"))
        entry = {"symbol": sym, "symbol_text": sym or "unreadable symbol", "mentions": u.get("mentions"),
                 "why": "ticker only: no contract on a stated chain, so it is never joined to a token or ranked",
                 "next_step": "Find a contract address on a stated chain from an official source before researching it."}
        if f["chain"] or f["source"] or f["risk"] in ("any",) or (f["risk"] not in (None, "none", "any")):
            continue
        if f["token"] and (not sym or sym.upper() != f["token"].lstrip("$").upper()):
            continue
        unresolved.append(entry)
    fixture = bool(fixture_demo or (snap and snap.get("contains_fixture")) or any(it["is_fixture"] for it in uniq))
    age = _hours(snap["cutoff"], as_of) if snap else None
    if snap is None:
        fresh = "NONE"
    elif age is not None and age > opts["stale_after_hours"]:
        fresh = "STALE"
    else:
        fresh = "FRESH"
    plats: dict[str, dict] = {}
    for c in inp.get("clusters") or []:
        for p, v in sorted(((c.get("coverage") or {}).get("platforms") or {}).items()):
            for st, n in (v.get("statuses") or {}).items():
                plats.setdefault(p, {})[st] = max(plats.get(p, {}).get(st, 0), n)
    high = [it for it in kept if it["priority"] == "HIGH"]
    model = inp.get("model") or {"status": "unknown"}
    doc = {
        "schema": SCHEMA, "engine_version": ENGINE_VERSION, "as_of": as_of, "as_of_text": fmt_time(as_of, tz), "tz": tz,
        "window": {"start": win_start, "end": as_of, "hours": opts["window_hours"], "text": f"{fmt_time(win_start, tz)} to {fmt_time(as_of, tz)}"},
        "fixture": fixture, "watermark": WATERMARK if fixture else None,
        "availability": inp.get("availability") or {"status": "UNKNOWN", "reason": None},
        "data_freshness": {"status": fresh, "snapshot_run_id": run_id, "snapshot_window": snap.get("window_label") if snap else None,
                           "snapshot_cutoff": snap.get("cutoff") if snap else None,
                           "snapshot_cutoff_text": fmt_time(snap.get("cutoff"), tz) if snap else "none",
                           "snapshot_age_hours": age, "stale_after_hours": opts["stale_after_hours"],
                           "compared_to": snap.get("compared_to") if snap else None,
                           "coverage_by_platform": plats,
                           "not_clustered": (snap or {}).get("claims_by_reason") or {}},
        "model": {"status": model.get("status"), "used": False,
                  "note": "The feed is deterministic and never calls a model; a missing or paid model changes nothing here."},
        "filters": {k: v for k, v in f.items()}, "options": opts,
        "headline": None if high else NO_SIGNAL,
        "headline_reason": None if high else _no_signal_reason(inp, uniq, kept),
        "counts": {"items": len(kept), "items_before_filters": len(uniq), "high": len(high),
                   "medium": sum(1 for it in kept if it["priority"] == "MEDIUM"), "low": sum(1 for it in kept if it["priority"] == "LOW"),
                   "unresolved_tickers": len(unresolved)},
        "items": kept, "unresolved": unresolved,
        "symbol_filter_note": ("The token filter matched a displayed symbol; symbols are not identity. Check the contract."
                               if f["token"] and any(_token_match(it, f["token"])[1] for it in kept) else None),
        "trade_execution_impact": "none",
    }
    doc["feed_sha256"] = _sha(doc)
    return doc


def _no_signal_reason(inp: dict, items: list[dict], kept: list[dict]) -> str:
    av = inp.get("availability") or {}
    if av.get("status") != "AVAILABLE" or not inp.get("snapshot"):
        return av.get("reason") or "no narrative snapshot available"
    if not items:
        return "the snapshot holds no token or theme narrative"
    if not kept:
        return "no item matches the filters"
    return "no fresh, adequately covered narrative with two or more independent sources or a chronology risk flag in the window"


# ---------- render ----------

def _head(doc: dict, title: str) -> list[str]:
    fr = doc["data_freshness"]
    L = [f"# {title}", ""]
    if doc["fixture"]:
        L += [doc["watermark"], ""]
    L.append(f"As of {doc['as_of_text']}. Window: {doc['window']['text']} ({doc['window']['hours']:g} h).")
    if fr["status"] == "NONE":
        L.append(f"Data: no narrative snapshot. Source status {doc['availability']['status']}: {md(doc['availability']['reason'], 120)}.")
    else:
        L.append(f"Data: narrative snapshot run {fr['snapshot_run_id']} ({md(fr['snapshot_window'], 40)}), cutoff {fr['snapshot_cutoff_text']}, "
                 f"{fr['snapshot_age_hours']} h old, {fr['status']}" + (f" (older than {fr['stale_after_hours']:g} h)" if fr["status"] == "STALE" else "") + ".")
        cov = "; ".join(f"{md(p, 15)} " + ", ".join(f"{k} {v}" for k, v in sorted(s.items())) for p, s in sorted(fr["coverage_by_platform"].items()))
        L.append("Coverage: " + (cov or "no coverage record (volumes not estimable)") + ".")
        if fr["not_clustered"]:
            L.append("Not clustered: " + ", ".join(f"{n} {md(k.replace('_', ' '), 50)}" for k, n in sorted(fr["not_clustered"].items())) + ".")
    L.append(f"Model: not used (status on this machine: {md(doc['model']['status'], 40)}). The feed is built from stored structure only.")
    act = [f"{k} {v}" for k, v in doc["filters"].items() if v not in (None, "")]
    if act:
        L.append("Filters: " + ", ".join(md(a, 60) for a in act) + ".")
    if doc.get("symbol_filter_note"):
        L.append(doc["symbol_filter_note"])
    return L


def _block(it: dict, full: bool = True) -> list[str]:
    L = [f"### {md(it['label'], 120)}", "",
         f"- Priority: {it['priority']} (HEURISTIC, orders this report only): {md(it['priority_basis'], 100)}.",
         f"- What happened: {md(it['what_happened'], 400)}",
         f"- First observed {it['times']['first_observed']}; first published {it['times']['earliest_published']}; last observed {it['times']['last_observed']}."]
    who = []
    for p in it["who"]:
        if "more" in p:
            who.append(f"and {p['more']} more {p['what']}")
            continue
        tr = f", trader {md(p['trader'], 40)}" if p.get("trader") else ""
        who.append(f"{link(p.get('url'), p['display'])} ({md(p['role'].lower().replace('_', ' '), 30)}{tr}, {p['time_text']}, stance {md(p['stance'], 30)})")
    L.append("- Who said it: " + ("; ".join(who) if who else "no attributable source") + ".")
    ind = it["independence"]
    L.append(f"- Independence vs repetition: {md(ind['statement'], 200)}; {ind['dependent']} reply or copy item(s); "
             f"{ind['unobserved_origins']} repeat(s) of an unseen original.")
    L.append(f"- Why it matters (HEURISTIC): {md('; '.join(it['why_it_matters']), 400)}.")
    L.append("- Corroborated: " + " ".join(it["corroborated"]))
    L.append("- Speculation: " + " ".join(it["speculation"]))
    L.append("- Reasons to doubt: " + " ".join(it["doubts"]))
    L.append(f"- Liquidity and exit: {it['liquidity']['caveat']}")
    L.append(f"- Next step: {it['next_step']}")
    fr = it["freshness"]
    cov = "; ".join(f"{md(p, 15)} " + ", ".join(f"{k} {v}" for k, v in sorted((s or {}).items())) for p, s in fr["coverage"]["platforms"].items())
    L.append(f"- Freshness and coverage: {fr['status']}, newest observation {fr['last_observed_age_hours']} h before as of, confidence {fr['confidence']}; "
             f"coverage {cov or 'none recorded'}" + (" (counts are lower bounds)" if fr["coverage"]["counts_are_lower_bounds"] else "") + ".")
    pv = it["provenance"]
    L.append(f"- Provenance: narrative run {pv['narrative_run_id']}, cluster {md(pv['cluster_key'], 90)}, claims {', '.join(str(c) for c in pv['claims'][:12]) or 'none'}"
             + (f", chronology runs {', '.join(str(r) for r in pv['chronology_runs'])}" if pv["chronology_runs"] else "")
             + (f", market facts {', '.join(str(r) for r in pv['market_fact_ids'])}" if pv["market_fact_ids"] else "") + ".")
    return L + [""]


def _unresolved(doc: dict) -> list[str]:
    if not doc["unresolved"]:
        return []
    L = ["## Unresolved ticker-only mentions", "", "Never joined to a token and never ranked."]
    for u in doc["unresolved"]:
        L.append(f"- {md(u['symbol_text'], 20)}: {u['mentions']} mention(s). {u['why']}. {u['next_step']}")
    return L + [""]


def _foot(doc: dict) -> list[str]:
    L = ["---", DISCLAIMER, f"Feed {doc['engine_version']}, schema {doc['schema']}, sha256 {doc['feed_sha256'][:16]}."]
    if doc["fixture"]:
        L.append(doc["watermark"])
    return L


def render_brief(doc: dict) -> str:
    L = _head(doc, "Morning brief: social narratives, last 24 hours") + [""]
    items = doc["items"]
    if doc["headline"]:
        L += [doc["headline"] + f" Reason: {md(doc['headline_reason'], 200)}.", ""]
    for pr, title in (("HIGH", "High priority"), ("MEDIUM", "Also active"), ("LOW", "Older or weakly covered")):
        grp = [it for it in items if it["priority"] == pr]
        if grp:
            L += [f"## {title}", ""]
            for it in grp:
                L += _block(it)
    L += _unresolved(doc)
    return "\n".join(L + _foot(doc)) + "\n"


def render_digest(doc: dict) -> str:
    L = _head(doc, "Trader conversation digest") + [""]
    groups = [it for it in doc["items"] if it["digest"]["people"]]
    if not groups:
        L += ["No attributable trader or source conversation in this snapshot." + (f" {doc['headline']}" if doc["headline"] else ""), ""]
    for it in groups:
        d = it["digest"]
        L += [f"## {md(it['label'], 120)}", "", f"- Priority {it['priority']} (HEURISTIC). {md(it['independence']['statement'], 200)}."]
        for p in d["people"]:
            tr = f", trader {md(p['trader'], 40)}" if p.get("trader") else ""
            L.append(f"- {link(p.get('url'), p['display'])}{tr}: stance {md(p['stance'], 20)}, disclosed position {md(p['position'], 20)}, "
                     f"latest at {p['time_text']}.")
        if d["changes"]:
            for ch in d["changes"]:
                L.append(f"- Changed position: {md(ch['who'], 60)} went from {md(ch['before']['stance'], 20)}"
                         + (f" ({md(ch['before']['position'], 20)})" if ch["before"].get("position") else "")
                         + f" to {md(ch['after']['stance'], 20)} ({md(ch['after']['position'], 20)}), {md(ch['basis'], 60)}.")
        else:
            L.append("- Changed positions: none recorded.")
        if d["disagreement"]["present"]:
            sides = "; ".join(f"{k}: " + ", ".join(md(x, 60) for x in v) for k, v in d["disagreement"]["sides"].items())
            L.append(f"- Disagreement (shown, not resolved): {sides or 'stance counts ' + json.dumps(it['stance'], sort_keys=True)}.")
        else:
            L.append("- Disagreement: none among attributable sources.")
        L.append(f"- Repetition: {it['independence']['repeats']} repeat(s) are counted once with their original and are not listed as people.")
        L.append(f"- Liquidity and exit: {it['liquidity']['caveat']}")
        L += [f"- Next step: {it['next_step']}", ""]
    L += _unresolved(doc)
    return "\n".join(L + _foot(doc)) + "\n"


def render_feed(doc: dict) -> str:
    L = _head(doc, "Social intelligence feed") + [""]
    c = doc["counts"]
    L.append(f"{c['items']} item(s) shown of {c['items_before_filters']} ({c['high']} high, {c['medium']} medium, {c['low']} low), "
             f"{c['unresolved_tickers']} unresolved ticker(s).")
    L.append("")
    if not doc["items"]:
        L += [(NO_SIGNAL + f" Reason: {md(doc['headline_reason'], 200)}.") if doc["headline"] else "No item matches the filters.", ""]
    for it in doc["items"]:
        L += _block(it)
    L += _unresolved(doc)
    return "\n".join(L + _foot(doc)) + "\n"


def render(doc: dict, view: str = "brief") -> str:
    if view == "brief":
        return render_brief(doc)
    if view == "trader-digest":
        return render_digest(doc)
    if view == "feed":
        return render_feed(doc)
    raise FeedError(f"unknown view {view!r}")


def to_json(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n"

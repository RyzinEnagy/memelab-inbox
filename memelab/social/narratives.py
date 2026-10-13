"""Phase 07: narrative clustering, originators, amplifiers and independent corroboration.

Input: current claims from Phase 06 (superseded extractions are ignored), the provider references Phases 03 and 04
stored (reposts, quotes, replies, forwards), account kinds and trader links, and the coverage rows of Phase 02.
Output: an immutable snapshot (social_narrative_runs and children) plus a change summary against the previous
comparable snapshot.

Clustering is deterministic and has two key kinds only:
  ca:<chain>:<contract>   a claim with a token resolved by Phase 05 to that identity (never a ticker or a name)
  tag:<tag>               a claim carrying a structured narrative tag from the closed list in extraction.NARRATIVE_TAGS
A ticker-only, ambiguous or unresolved mention joins no contract cluster; it is listed as unassigned. No vector or
LLM clustering is run (DECISIONS D-043); the snapshot records semantic_clustering = "not_enabled".

Counting rules (DECISIONS D-042):
  - mentions are distinct items, not claims, not accounts;
  - a repost, a forward and a quote that repeats someone's claim are AMPLIFIER: they add mentions, never independence;
  - replies, quote commentary and byte-identical copies are DEPENDENT: they share a dependency with another item;
  - every item that reaches the same original (directly or through a chain of references) or carries the same
    content hash is in one dependency group, and a group has one origin;
  - independent_source_count is the number of distinct attributable sources among the group origins we observed;
    a bot, an aggregator or an unknown author is never counted as independent;
  - inferred coordination is a hypothesis (HEURISTIC), never proven common ownership, and does not change who the
    sources are; copies and reposts are already collapsed into their group.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date as _date, datetime, time as _time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from . import extraction, store

ENGINE_VERSION = "narr-v1"
DEFAULTS: dict[str, Any] = {
    "windows": [3600, 21600, 86400],      # trailing sliding windows in seconds
    "stale_after": 172800,                # 48 h: an item observed this long after publication is "late"; a cluster with
                                          # nothing observed this recently is STALE
    "burst_accounts": 10,                 # distinct amplifying sources ...
    "burst_seconds": 900,                 # ... inside this many seconds is a burst hypothesis
    "copy_accounts": 3,                   # distinct sources posting byte-identical text is a copy hypothesis
    "require_coverage": True,             # no coverage record for a platform means volume is not estimable
    "min_time_known_share": 0.5,          # fewer items than this share with a usable time: not estimable
    "semantic_clustering": "not_enabled",
}
NOT_PRESENT = ("DELETED", "NOT_FOUND")    # the provider says the item is gone: its stance is not counted
ROLES = ("INDEPENDENT_ORIGINAL", "UNVERIFIED_ORIGINAL", "AMPLIFIER", "DEPENDENT")
NON_INDEPENDENT_KINDS = ("BOT", "AGGREGATOR")


# ---------- helpers ----------

def _j(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), default=str)


def _sha(v: Any) -> str:
    return hashlib.sha256(_j(v).encode()).hexdigest()


def day_window(day: str, tz: str = "UTC") -> tuple[float, float]:
    """UTC epoch bounds [start, end) of a calendar day in an IANA zone. A day with a clock change is 23 or 25 hours long."""
    z = ZoneInfo(tz)
    d = _date.fromisoformat(day)
    start = datetime.combine(d, _time(), tzinfo=z)
    end = datetime.combine(d + timedelta(days=1), _time(), tzinfo=z)
    return start.timestamp(), end.timestamp()


def _label(chain: str, contract: str, symbol: str | None) -> str:
    short = contract if len(contract) <= 12 else f"{contract[:6]}..{contract[-4:]}"
    return f"{symbol} ({chain} {short})" if symbol else f"{chain} {short}"


# ---------- loading ----------

def _load_claims(con: sqlite3.Connection, cutoff: float) -> list[dict]:
    rows = con.execute(
        "SELECT c.id AS claim_id, c.item_key, c.account_id AS claim_account, c.claim_status, "
        "a.category, a.stance, a.sarcasm_suspected, a.attribution, a.referenced_item_key, a.narrative_tags_json, a.tokens_json, "
        "e.extraction_id, e.observation_id, e.content_hash, i.platform, i.account_id AS item_account, i.published_at, i.published_at_basis "
        "FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id "
        "JOIN social_claim_extractions e ON e.extraction_id=a.extraction_id "
        "JOIN social_items i ON i.item_key=c.item_key WHERE e.superseded_by IS NULL ORDER BY c.id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.pop("narrative_tags_json"))
        d["tokens"] = json.loads(d.pop("tokens_json"))
        d["account_id"] = d.pop("item_account") or d.pop("claim_account")
        d.pop("claim_account", None)
        out.append(d)
    return out


def _load_items(con: sqlite3.Connection, item_keys: set[str], cutoff: float) -> dict[str, dict]:
    info: dict[str, dict] = {k: {"first_observed": None, "last_observed": None, "state": "accessible", "modes": set(),
                                 "n_obs": 0} for k in item_keys}
    for r in con.execute("SELECT item_key, observed_at, ingested_at, retrieval_status, access_mode, id FROM social_observations "
                         "ORDER BY COALESCE(observed_at, ingested_at), id"):
        k = r["item_key"]
        if k not in info:
            continue
        t = r["observed_at"] if r["observed_at"] is not None else r["ingested_at"]
        if t is None or t > cutoff:
            continue
        d = info[k]
        d["n_obs"] += 1
        d["modes"].add(r["access_mode"])
        if r["observed_at"] is not None:
            d["first_observed"] = r["observed_at"] if d["first_observed"] is None else min(d["first_observed"], r["observed_at"])
            d["last_observed"] = r["observed_at"] if d["last_observed"] is None else max(d["last_observed"], r["observed_at"])
        d["state"] = "accessible" if r["retrieval_status"] in ("OK", "PARTIAL") else f"inaccessible:{r['retrieval_status']}"
    return info


def _load_structure(con: sqlite3.Connection, item_keys: set[str]) -> dict[str, list[tuple[str, str | None]]]:
    """item_key -> [(edge_type, target item key or None when the provider gave no origin)]."""
    edges: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    kind = {"retweeted": "repost", "quoted": "quote", "replied_to": "reply"}
    for r in con.execute("SELECT item_key, ref_type, referenced_item_key FROM social_item_refs ORDER BY item_key, ref_type, referenced_item_key"):
        if r["item_key"] in item_keys:
            edges[r["item_key"]].append((kind[r["ref_type"]], r["referenced_item_key"]))
    for r in con.execute("SELECT item_key, origin_item_key FROM social_item_forwards"):
        if r["item_key"] in item_keys:
            edges[r["item_key"]].append(("forward", r["origin_item_key"]))
    for r in con.execute("SELECT item_key, reference_type FROM social_item_context WHERE reference_type='REPOST'"):
        if r["item_key"] in item_keys and not any(t in ("repost", "forward") for t, _ in edges[r["item_key"]]):
            edges[r["item_key"]].append(("repost", None))
    return edges


def _load_accounts(con: sqlite3.Connection, account_ids: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    kinds = {r["account_id"]: r["account_kind"] for r in con.execute("SELECT account_id, account_kind FROM social_accounts")
             if r["account_id"] in account_ids}
    traders: dict[str, str] = {}
    for r in con.execute("SELECT trader_id, account_id FROM social_trader_accounts ORDER BY trader_id"):
        if r["account_id"] in account_ids and r["account_id"] not in traders:
            traders[r["account_id"]] = r["trader_id"]
    return kinds, traders


def _load_symbols(con: sqlite3.Connection) -> dict[str, str | None]:
    return {r["ref_key"]: r["symbol_seen"] for r in con.execute("SELECT ref_key, symbol_seen FROM social_token_refs WHERE ref_key LIKE 'ca:%'")}


def _load_coverage(con: sqlite3.Connection, ws: float, cutoff: float) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in con.execute("SELECT platform, status, window_start, window_end, checked_at, gap_reason, sampling_note FROM social_coverage "
                         "ORDER BY platform, checked_at, id"):
        a = r["window_start"] if r["window_start"] is not None else r["checked_at"]
        b = r["window_end"] if r["window_end"] is not None else r["checked_at"]
        if r["checked_at"] <= cutoff and a <= cutoff and b >= ws:
            out[r["platform"]].append({"status": r["status"], "gap_reason": r["gap_reason"], "sampling_note": r["sampling_note"]})
    return out


def _contradictions(con: sqlite3.Connection) -> set[frozenset]:
    return {frozenset((r["claim_id"], r["other_claim_id"])) for r in
            con.execute("SELECT claim_id, other_claim_id FROM social_claim_relations WHERE relation='CONTRADICTS'")}


# ---------- one cluster ----------

class _UF:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def _stance_of(claims: list[dict]) -> str:
    s = {c["stance"] for c in claims if not c["sarcasm_suspected"] and c["stance"] != "neutral"}
    if not s:
        return "neutral"
    return s.pop() if len(s) == 1 else "mixed"


def _sliding(times: list[float], cutoff: float, windows: list[int]) -> dict:
    out: dict[str, Any] = {}
    ts = sorted(times)
    for w in windows:
        cur = sum(1 for t in ts if cutoff - w < t <= cutoff)
        prev = sum(1 for t in ts if cutoff - 2 * w < t <= cutoff - w)
        peak, lo = 0, 0
        for hi, t in enumerate(ts):
            while t - ts[lo] >= w:
                lo += 1
            peak = max(peak, hi - lo + 1)
        out[str(w)] = {"current": cur, "previous": prev, "delta": cur - prev,
                       "pct_change": None if prev == 0 else round(100.0 * (cur - prev) / prev, 1), "peak_sliding": peak}
    return out


def _cap(level: str, ceiling: str) -> str:
    order = ["UNKNOWN", "LOW", "MODERATE", "HIGH"]
    return order[min(order.index(level), order.index(ceiling))]


def _build(key: str, kind: str, label: str, claims: list[dict], ctx: dict) -> dict:
    P = ctx["params"]
    ws, we, cutoff = ctx["ws"], ctx["we"], ctx["cutoff"]
    items: dict[str, dict] = {}
    for c in claims:
        it = items.setdefault(c["item_key"], {"item_key": c["item_key"], "claims": [], "account_id": c["account_id"],
                                              "platform": c["platform"], "hash": c["content_hash"], "attribution": c["attribution"],
                                              "published_at": c["published_at"], "pub_basis": c["published_at_basis"]})
        it["claims"].append(c)
    for k, it in items.items():
        info = ctx["items"][k]
        it["first_observed"], it["last_observed"], it["state"], it["modes"] = (info["first_observed"], info["last_observed"],
                                                                              info["state"], info["modes"])
        it["source_id"] = ctx["traders"].get(it["account_id"], it["account_id"]) if it["account_id"] else None
        it["kind"] = ctx["kinds"].get(it["account_id"]) if it["account_id"] else None
        pub = it["published_at"] if it["pub_basis"] == "PROVIDER" else None
        if pub is not None:
            it["event_time"], it["basis"] = pub, "PROVIDER"
        elif it["first_observed"] is not None:
            it["event_time"], it["basis"] = it["first_observed"], "COLLECTOR"
        else:
            it["event_time"], it["basis"] = None, "UNKNOWN"
        it["order"] = it["event_time"] if it["event_time"] is not None else float("inf")
        it["stance"] = _stance_of(it["claims"])
        it["late"] = bool(pub is not None and it["first_observed"] is not None and it["first_observed"] - pub > P["stale_after"])
        it["out"] = []
        it["external"] = []
        for t, target in ctx["edges"].get(k, []):
            if t in ("reply", "quote") and it["attribution"] == "author" and target and target not in items and target in ctx["known"]:
                # own words answering an item we observed that makes no claim about this token: the answer is its own origin here
                it["external"].append((t, target))
                continue
            it["out"].append((t, target if target else f"unknown:{k}"))
        if not it["out"] and it["attribution"] in ("quoted", "reposted"):
            ref = next((c["referenced_item_key"] for c in it["claims"] if c["referenced_item_key"]), None)
            if ref:
                it["out"].append(("quote" if it["attribution"] == "quoted" else "repost", ref))
    keys = sorted(items)

    # dependency groups: shared original (any chain of references) or identical content hash
    uf, edges = _UF(), []
    for k in keys:
        uf.find(k)
        for t, target in items[k]["out"]:
            uf.union(k, target)
            edges.append((k, target, t, target in items))
    by_hash: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        if items[k]["hash"]:
            by_hash[items[k]["hash"]].append(k)
    copy_sets = []
    for h, ks in sorted(by_hash.items()):
        if len(ks) > 1:
            ks = sorted(ks, key=lambda x: (items[x]["order"], x))
            joined = [ks[0]]
            for other in ks[1:]:
                if uf.find(other) != uf.find(ks[0]):
                    edges.append((other, ks[0], "identical_text", True))
                    joined.append(other)
                uf.union(other, ks[0])
            if len(joined) > 1:                  # copies already explained by a repost or forward are not a coordination signal
                copy_sets.append(joined)
    groups: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        groups[uf.find(k)].append(k)

    roles: dict[str, tuple[str, str, str]] = {}      # item -> (role, group_id, why)
    group_info = []
    for root, ks in sorted(groups.items()):
        ks = sorted(ks, key=lambda x: (items[x]["order"], x))
        selfs = [k for k in ks if not items[k]["out"]]
        origin = selfs[0] if selfs else None
        gid = f"g:{origin or root}"
        for k in ks:
            it = items[k]
            types = {t for t, _ in it["out"]}
            if k == origin:
                if it["source_id"] is None:
                    roles[k] = ("UNVERIFIED_ORIGINAL", gid, "unknown_author")
                elif it["kind"] in NON_INDEPENDENT_KINDS:
                    roles[k] = ("UNVERIFIED_ORIGINAL", gid, f"account_kind_{it['kind'].lower()}")
                else:
                    roles[k] = ("INDEPENDENT_ORIGINAL", gid, "earliest_self_originated_item_in_group")
            elif types & {"repost", "forward"}:
                roles[k] = ("AMPLIFIER", gid, "forward_of_another_item" if "forward" in types else "repost_of_another_item")
            elif "quote" in types and it["attribution"] in ("quoted", "reposted", "unclear"):
                roles[k] = ("AMPLIFIER", gid, "quote_that_repeats_the_claim")
            elif types:
                roles[k] = ("DEPENDENT", gid, "reply_or_quote_commentary_on_shared_original")
            else:
                roles[k] = ("DEPENDENT", gid, "identical_text_to_an_earlier_item")
            if k == origin and it["external"]:
                roles[k] = (roles[k][0], gid, roles[k][2] if roles[k][0] == "UNVERIFIED_ORIGINAL" else "reply_to_an_item_without_this_claim")
        srcs = {items[k]["source_id"] for k in ks if items[k]["source_id"]}
        group_info.append({"group_id": gid, "size": len(ks), "distinct_sources": len(srcs),
                           "origin_item": origin, "origin_observed": origin is not None,
                           "unobserved_origin_refs": sorted({tg for k in ks for _, tg in items[k]["out"] if tg not in items})[:5]})

    n = len(keys)
    role_of = {k: roles[k][0] for k in keys}
    independent = [k for k in keys if role_of[k] == "INDEPENDENT_ORIGINAL"]
    ind_sources = sorted({items[k]["source_id"] for k in independent})
    amp = [k for k in keys if role_of[k] == "AMPLIFIER"]
    dep = [k for k in keys if role_of[k] == "DEPENDENT"]
    unobserved = [g for g in group_info if not g["origin_observed"]]
    all_sources = {items[k]["source_id"] for k in keys if items[k]["source_id"]}

    # coordination hypotheses (HEURISTIC; never proven common control)
    flags: list[dict] = []
    for g in group_info:
        members = [k for k in groups[uf.find(g["origin_item"] or next(k for k in keys if roles[k][1] == g["group_id"]))]]
        amps = [k for k in members if role_of[k] == "AMPLIFIER" and items[k]["source_id"]]
        srcs = {items[k]["source_id"] for k in amps}
        times = sorted(items[k]["event_time"] for k in amps if items[k]["event_time"] is not None)
        if len(srcs) >= P["burst_accounts"] and times:
            lo = 0
            best = 0
            for hi, t in enumerate(times):
                while t - times[lo] > P["burst_seconds"]:
                    lo += 1
                best = max(best, hi - lo + 1)
            if best >= P["burst_accounts"]:
                flags.append({"flag": "burst_amplification", "evidence": "HEURISTIC", "proven": False, "group_id": g["group_id"],
                              "amplifying_sources": len(srcs), "max_in_burst_window": best, "burst_seconds": P["burst_seconds"],
                              "note": "many sources repeated one original within a short time; this can be organic or coordinated, ownership is not known"})
    for ks in copy_sets:
        srcs = {items[k]["source_id"] for k in ks if items[k]["source_id"]}
        if len(srcs) >= P["copy_accounts"]:
            flags.append({"flag": "identical_text_multi_source", "evidence": "HEURISTIC", "proven": False, "group_id": roles[ks[0]][1],
                          "sources": len(srcs), "items": len(ks),
                          "note": "byte-identical text from several sources; possible copy-paste or common control, not proven"})
    for k in keys:
        if any(t == "forward" and tg.startswith("unknown:") for t, tg in items[k]["out"]):
            flags.append({"flag": "forward_origin_unknown", "evidence": "FACT", "proven": True, "item_key": k})
    n_late = sum(1 for k in keys if items[k]["late"])
    if n_late:
        flags.append({"flag": "late_observed_items", "evidence": "FACT", "proven": True, "items": n_late,
                      "note": f"observed more than {P['stale_after']}s after publication; placed by publication time"})
    gone = [k for k in keys if items[k]["state"].split(":")[-1] in NOT_PRESENT]
    inaccessible = [k for k in keys if items[k]["state"] != "accessible"]
    if inaccessible:
        flags.append({"flag": "inaccessible_sources", "evidence": "FACT", "proven": True, "items": len(inaccessible),
                      "of_which_gone": len(gone), "note": "claims were observed earlier; the provider no longer serves these items"})
    fixture = any("fixture" in items[k]["modes"] for k in keys)
    if fixture:
        flags.append({"flag": "contains_fixture_data", "evidence": "FACT", "proven": True})

    # event times, windows
    times = [items[k]["event_time"] for k in keys if items[k]["event_time"] is not None]
    in_win = {k: items[k]["event_time"] is not None and ws <= items[k]["event_time"] < we for k in keys}
    windows = _sliding(times, cutoff, P["windows"])
    origin_times = [items[k]["event_time"] for k in independent if items[k]["event_time"] is not None]
    windows["origins"] = _sliding(origin_times, cutoff, P["windows"])
    observed = [items[k]["first_observed"] for k in keys if items[k]["first_observed"] is not None]
    last_obs = [items[k]["last_observed"] for k in keys if items[k]["last_observed"] is not None]
    pubs = [items[k]["published_at"] for k in keys if items[k]["pub_basis"] == "PROVIDER" and items[k]["published_at"] is not None]
    freshness = "FRESH" if last_obs and max(last_obs) >= cutoff - P["stale_after"] else "STALE"

    # stance voices: a source's latest non-neutral stance; deleted items and sarcasm do not vote
    voices: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for k in keys:
        it = items[k]
        if role_of[k] != "AMPLIFIER" and it["source_id"] and k not in gone:
            voices[it["source_id"]].append((it["order"], it["stance"]))
    stance = Counter()
    changes = []
    for s, seq in sorted(voices.items()):
        seq.sort()
        nn = [(t, v) for t, v in seq if v != "neutral"]
        stance[nn[-1][1] if nn else "neutral"] += 1
        pn = [(t, v) for t, v in nn if v in ("positive", "negative")]
        for (t1, v1), (t2, v2) in zip(pn, pn[1:]):
            if v1 != v2:
                changes.append({"source_id": s, "from": v1, "to": v2, "from_time": t1, "to_time": t2})
    conflicted = stance["positive"] >= 1 and stance["negative"] >= 1
    cids = {c["claim_id"] for c in claims}
    contra = sum(1 for p in ctx["contra"] if p <= cids)
    if contra:
        conflicted = True

    # coverage
    plats = sorted({items[k]["platform"] for k in keys})
    cov = {}
    reasons: list[str] = []
    lower_bound = False
    for pl in plats:
        rows = ctx["coverage"].get(pl, [])
        c = Counter(r["status"] for r in rows)
        cov[pl] = {"statuses": dict(sorted(c.items())), "notes": sorted({r["gap_reason"] or r["sampling_note"] for r in rows
                                                                            if (r["gap_reason"] or r["sampling_note"])})[:3]}
        if not rows:
            if P["require_coverage"]:
                reasons.append(f"no_coverage_record:{pl}")
        elif not c.get("COVERED"):
            reasons.append(f"coverage_gap:{pl}")
        elif set(c) - {"COVERED"}:
            lower_bound = True
    known = sum(1 for k in keys if items[k]["event_time"] is not None)
    if n and known / n < P["min_time_known_share"]:
        reasons.append("time_unknown_for_most_items")
    if not ind_sources:
        reasons.append("origins_not_observed" if (amp or dep) and unobserved else "no_attributable_source")
    status = "insufficient_coverage" if reasons else "ok"
    if status == "ok":
        level = "HIGH" if len(ind_sources) >= 5 else "MODERATE" if len(ind_sources) >= 2 else "LOW"
        basis = [f"{len(ind_sources)} independent source(s)"]
        for cond, ceiling, why in ((any(f["flag"] in ("burst_amplification", "identical_text_multi_source") for f in flags), "MODERATE", "coordination hypothesis present"),
                                   (lower_bound, "MODERATE", "coverage for the window is partial or has gaps"),
                                   (bool(unobserved), "MODERATE", "some originals were not observed"),
                                   (bool(inaccessible), "MODERATE", "some sources are no longer accessible"),
                                   (conflicted, "MODERATE", "sources disagree"),
                                   (freshness == "STALE", "LOW", "nothing observed recently")):
            if cond and _cap(level, ceiling) != level:
                level = _cap(level, ceiling)
                basis.append(f"capped at {ceiling}: {why}")
    else:
        level, basis = "UNKNOWN", [f"not estimable: {', '.join(reasons)}"]

    # linked-token and theme context
    toks: Counter = Counter()
    tags: Counter = Counter()
    chains: Counter = Counter()
    for c in claims:
        seen = set()
        for t in c["tokens"]:
            if t.get("status") == "resolved" and t.get("chain") and t.get("contract"):
                seen.add((t["chain"], t["contract"]))
        for ch, ct in seen:
            if f"ca:{ch}:{ct}" != key:
                toks[(ch, ct)] += 1
            chains[ch] += 1
        for tg in c["tags"]:
            if f"tag:{tg}" != key:
                tags[tg] += 1
    linked = {"tokens": [{"chain": ch, "contract": ct, "symbol": ctx["symbols"].get(f"ca:{ch}:{ct}"), "claims": cnt}
                         for (ch, ct), cnt in sorted(toks.items(), key=lambda x: (-x[1], x[0]))[:10]],
              "tags": [{"tag": t, "claims": cnt} for t, cnt in sorted(tags.items(), key=lambda x: (-x[1], x[0]))[:10]]}
    if kind == "CONTRACT":
        chain_list = [key.split(":")[1]]
    else:
        chain_list = sorted(chains)

    deps = [g for g in group_info if g["size"] > 1]
    originators = [{"item_key": k, "source_id": items[k]["source_id"], "event_time": items[k]["event_time"], "basis": items[k]["basis"]}
                   for k in sorted(independent, key=lambda x: (items[x]["order"], x))[:10]]
    plain = _plain(key, kind, label, status, reasons, level, basis, n, len(claims), len(ind_sources), len(amp), len(dep), deps, originators,
                   flags, stance, changes, conflicted, cov, in_win, windows, freshness)
    explanation = {
        "why_cluster": {"rule": ("claims whose token resolved (Phase 05) to this exact chain and contract" if kind == "CONTRACT"
                                 else "claims carrying this structured narrative tag (closed list, Phase 06)"),
                        "never_used": "ticker symbols, token names, post wording", "claims": len(claims), "items": n},
        "independence": {"rule": "one origin per dependency group; reposts, forwards, quotes that repeat, replies and identical copies add mentions, not sources",
                         "independent_sources": ind_sources, "groups": deps[:10]},
        "confidence_basis": basis, "plain": plain,
    }
    return {
        "key": key, "kind": kind, "label": label, "status": status, "reasons": reasons, "confidence": level, "freshness": freshness,
        "first_observed_at": min(observed) if observed else None, "last_observed_at": max(last_obs) if last_obs else None,
        "earliest_published_at": min(pubs) if pubs else None,
        "item_count": n, "window_mentions": sum(in_win.values()), "source_count": len(all_sources),
        "independent_source_count": None if status != "ok" else len(ind_sources),
        "independent_group_count": None if status != "ok" else len(independent),
        "amplifier_count": len(amp), "dependent_count": len(dep), "unobserved_origin_count": len(unobserved),
        "edge_count": len(edges), "conflicted": int(conflicted), "stance": dict(sorted(stance.items())), "opinion_changes": changes,
        "windows": windows, "flags": flags, "dependencies": deps, "originators": originators, "linked": linked, "chains": chain_list,
        "coverage": {"platforms": cov, "counts_are_lower_bounds": lower_bound or status != "ok"}, "explanation": explanation,
        "_items": items, "_roles": roles, "_edges": edges, "_in_win": in_win, "_independent_sources": ind_sources,
        "observed_independent_sources": len(ind_sources),
    }


def _plain(key, kind, label, status, reasons, level, basis, n, nclaims, nind, namp, ndep, deps, origs, flags, stance, changes, conflicted,
           cov, in_win, windows, freshness) -> list[str]:
    L = [f"{label}: {'token identity' if kind == 'CONTRACT' else 'theme tag'} cluster ({key})."]
    L.append(f"Members: {nclaims} claim(s) from {n} item(s); {sum(in_win.values())} item(s) fall inside the window.")
    if status != "ok":
        L.append(f"Independence and volume are not estimable ({', '.join(reasons)}). Counts above are what was observed, as lower bounds.")
    else:
        L.append(f"Independent sources: {nind}. Amplifiers (reposts, forwards, repeating quotes): {namp}. Dependent items (replies, commentary, copies): {ndep}.")
    for g in deps[:3]:
        L.append(f"Dependency group {g['group_id']}: {g['size']} item(s), {g['distinct_sources']} source(s), "
                 f"{'origin observed' if g['origin_observed'] else 'origin not observed'}; counted as one origin.")
    for f in flags:
        if f["flag"] in ("burst_amplification", "identical_text_multi_source"):
            L.append(f"Hypothesis (not proven): {f['flag'].replace('_', ' ')}. {f['note']}.")
    if conflicted:
        L.append(f"Sources disagree: {dict(stance)}.")
    for c in changes[:3]:
        L.append(f"Opinion change: {c['source_id']} went from {c['from']} to {c['to']}; the later stance is the one counted.")
    L.append(f"Confidence {level}: {'; '.join(basis)}. Data is {freshness.lower()}.")
    return L


# ---------- snapshot ----------

def snapshot(con: sqlite3.Connection, *, day: str | None = None, tz: str = "UTC", window_start: Any = None, window_end: Any = None,
             params: dict | None = None, now: float | None = None) -> dict:
    """Build and store one narrative snapshot. Same inputs give the same run (idempotent). The knowledge cutoff is
    min(window_end, now): nothing observed later is used, so a replay of a past window reproduces its result."""
    P = {**DEFAULTS, **(params or {})}
    if day is not None:
        ws, we = day_window(day, tz)
        label = f"{day} {tz}"
    else:
        ws, we = store.to_utc(window_start), store.to_utc(window_end)
        if ws is None or we is None or we <= ws:
            raise ValueError("give day, or both window_start and window_end (aware datetimes, ISO with offset, or epoch seconds)")
        label = "custom"
    t_now = store._now(now)
    cutoff = min(we, t_now)
    store.register_analysis_version(con, ENGINE_VERSION, "scorer", "deterministic narrative clustering and independence", P, now=t_now)

    claims = [c for c in _load_claims(con, cutoff)]
    items = _load_items(con, {c["item_key"] for c in claims}, cutoff)
    kept, excluded = [], Counter()
    for c in claims:
        info = items[c["item_key"]]
        pub = c["published_at"] if c["published_at_basis"] == "PROVIDER" else None
        t = pub if pub is not None else info["first_observed"]
        if info["n_obs"] == 0:
            excluded["not_observed_by_cutoff"] += 1
        elif t is not None and t >= we:
            excluded["event_time_after_window_end"] += 1
        else:
            kept.append(c)
    item_keys = {c["item_key"] for c in kept}
    edges = _load_structure(con, item_keys)
    # targets that are cluster-external are kept as ids only
    kinds, traders = _load_accounts(con, {c["account_id"] for c in kept if c["account_id"]})
    symbols = _load_symbols(con)
    coverage = _load_coverage(con, ws, cutoff)
    contra = _contradictions(con)
    known = {r[0] for r in con.execute("SELECT item_key FROM social_items")}
    ctx = {"known": known, "params": P, "ws": ws, "we": we, "cutoff": cutoff, "items": items, "edges": edges, "kinds": kinds, "traders": traders,
           "symbols": symbols, "coverage": coverage, "contra": contra}

    buckets: dict[str, list[dict]] = defaultdict(list)
    meta: dict[str, tuple[str, str]] = {}
    unassigned: dict[str, Any] = {"claims_by_reason": Counter(excluded), "ticker_only_mentions": Counter()}
    clustered = 0
    for c in kept:
        ks = []
        for t in c["tokens"]:
            if t.get("status") == "resolved" and t.get("chain") and t.get("contract"):
                k = f"ca:{t['chain']}:{t['contract']}"
                if k not in ks:
                    ks.append(k)
                    meta[k] = ("CONTRACT", _label(t["chain"], t["contract"], symbols.get(k)))
        for tg in c["tags"]:
            k = f"tag:{tg}"
            ks.append(k)
            meta[k] = ("THEME", f"theme: {tg.replace('_', ' ')}")
        if ks:
            clustered += 1
            for k in ks:
                buckets[k].append(c)
        else:
            has_tok = bool(c["tokens"])
            unassigned["claims_by_reason"]["token_not_resolved_to_a_contract" if has_tok else "no_token_and_no_theme_tag"] += 1
            for t in c["tokens"]:
                if str(t.get("mention_key", "")).startswith("ticker:"):
                    unassigned["ticker_only_mentions"][t["mention_key"][7:]] += 1
    built = {k: _build(k, meta[k][0], meta[k][1], buckets[k], ctx) for k in sorted(buckets)}

    # same ticker on different contracts is informational, never a merge
    by_symbol: dict[str, list[str]] = defaultdict(list)
    for k, b in built.items():
        sym = symbols.get(k) if k.startswith("ca:") else None
        if sym:
            by_symbol[sym.lstrip("$").upper()].append(k)
    for sym, ks in sorted(by_symbol.items()):
        if len(ks) > 1:
            for k in ks:
                built[k]["flags"].append({"flag": "ticker_collision", "evidence": "FACT", "proven": True, "symbol": sym,
                                          "other_clusters": [x for x in ks if x != k],
                                          "note": "the same ticker appears on different contracts; clusters are kept apart by contract"})
                built[k]["explanation"]["plain"].append(f"The ticker {sym} also appears on {len(ks) - 1} other contract(s); they are separate clusters.")

    unassigned_out = {"claims_by_reason": dict(sorted(unassigned["claims_by_reason"].items())),
                      "ticker_only_mentions": dict(sorted(unassigned["ticker_only_mentions"].items())),
                      "claims_clustered": clustered, "claims_considered": len(kept)}
    input_rows = {"claims": [(c["claim_id"], c["extraction_id"], c["observation_id"], c["item_key"], c["account_id"], c["stance"],
                              c["sarcasm_suspected"], c["content_hash"], _j(c["tokens"]), _j(c["tags"])) for c in kept],
                  "items": {k: (v["first_observed"], v["last_observed"], v["state"], sorted(v["modes"])) for k, v in sorted(items.items()) if k in item_keys},
                  "edges": {k: v for k, v in sorted(edges.items())}, "kinds": kinds, "traders": traders,
                  "coverage": {k: v for k, v in sorted(coverage.items())}, "contra": sorted(sorted(p) for p in contra if p <= {c["claim_id"] for c in kept})}
    input_sha = _sha(input_rows)
    params_sha = _sha({k: v for k, v in P.items()})
    skey = _sha([ENGINE_VERSION, ws, we, cutoff, tz, params_sha, input_sha])
    row = con.execute("SELECT run_id FROM social_narrative_runs WHERE snapshot_key=?", (skey,)).fetchone()
    if row:
        return {"run_id": row[0], "created": False, **run_view(con, row[0])}

    prev = con.execute("SELECT run_id FROM social_narrative_runs WHERE params_sha=? AND tz=? AND window_end<=? "
                       "ORDER BY window_end DESC, cutoff DESC, run_id DESC LIMIT 1", (params_sha, tz, ws + 1)).fetchone()
    prev_id = prev[0] if prev else None
    changes = _changes(con, prev_id, built)
    summary = {"prev_run_id": prev_id, "clusters": len(built), "changes": dict(Counter(c["change_type"] for c in changes)),
               "new": [c["cluster_key"] for c in changes if c["change_type"] == "NEW"],
               "highlights": [{"cluster_key": c["cluster_key"], "change": c["change_type"], "before": c["before"], "after": c["after"]}
                              for c in changes if c["change_type"] != "NEW"][:20],
               "insufficient_coverage": sorted(k for k, b in built.items() if b["status"] != "ok"),
               "compared_to": "none (first comparable snapshot)" if prev_id is None else f"run {prev_id}"}
    cur = con.execute(
        "INSERT INTO social_narrative_runs(snapshot_key,engine_version,window_label,tz,window_start,window_end,cutoff,window_complete,params_json,"
        "params_sha,input_sha,input_claims,cluster_count,unassigned_json,contains_fixture,prev_run_id,summary_json,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (skey, ENGINE_VERSION, label, tz, ws, we, cutoff, int(t_now >= we), _j(P), params_sha, input_sha, len(kept), len(built),
         _j(unassigned_out), int(any(any(f["flag"] == "contains_fixture_data" for f in b["flags"]) for b in built.values())),
         prev_id, _j(summary), t_now))
    run_id = cur.lastrowid
    for k, b in built.items():
        con.execute(
            "INSERT INTO social_narrative_clusters VALUES (" + ",".join("?" * 31) + ")",
            (run_id, k, b["kind"], b["label"], b["status"], _j(b["reasons"]), b["confidence"], b["freshness"], b["first_observed_at"],
             b["last_observed_at"], b["earliest_published_at"], b["item_count"], b["window_mentions"], b["source_count"],
             b["independent_source_count"], b["independent_group_count"], b["amplifier_count"], b["dependent_count"],
             b["unobserved_origin_count"], b["edge_count"], b["conflicted"], _j(b["stance"]), _j(b["opinion_changes"]), _j(b["windows"]),
             _j(b["flags"]), _j(b["dependencies"]), _j(b["originators"]), _j(b["linked"]), _j(b["chains"]), _j(b["coverage"]),
             _j(b["explanation"])))
        for claim in buckets[k]:
            it = b["_items"][claim["item_key"]]
            role, gid, why = b["_roles"][claim["item_key"]]
            con.execute("INSERT INTO social_narrative_members VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, k, claim["claim_id"], claim["item_key"], claim["observation_id"], claim["account_id"], it["source_id"],
                         role, gid, it["event_time"], it["basis"], int(b["_in_win"][claim["item_key"]]), it["state"], it["stance"], why))
        for frm, to, et, obs in sorted(set(b["_edges"])):
            con.execute("INSERT OR IGNORE INTO social_narrative_edges VALUES (?,?,?,?,?,?)", (run_id, k, frm, to, et, int(obs)))
    for c in changes:
        con.execute("INSERT INTO social_narrative_changes VALUES (?,?,?,?,?,?)",
                    (run_id, prev_id, c["cluster_key"], c["change_type"], _j(c["before"]), _j(c["after"])))
    return {"run_id": run_id, "created": True, **run_view(con, run_id)}


def _changes(con: sqlite3.Connection, prev_id: int | None, built: dict) -> list[dict]:
    out = []
    prev = {}
    if prev_id is not None:
        for r in con.execute("SELECT * FROM social_narrative_clusters WHERE run_id=?", (prev_id,)):
            prev[r["cluster_key"]] = r
    for k, b in sorted(built.items()):
        cur = {"window_mentions": b["window_mentions"], "independent_source_count": b["independent_source_count"], "status": b["status"],
               "confidence": b["confidence"], "stance": b["stance"], "conflicted": b["conflicted"], "item_count": b["item_count"]}
        p = prev.get(k)
        if p is None:
            out.append({"cluster_key": k, "change_type": "NEW", "before": None, "after": cur})
            continue
        before = {"window_mentions": p["window_mentions"], "independent_source_count": p["independent_source_count"], "status": p["status"],
                  "confidence": p["confidence"], "stance": json.loads(p["stance_json"]), "conflicted": p["conflicted"], "item_count": p["item_count"]}
        if before["window_mentions"] > 0 and cur["window_mentions"] == 0:
            out.append({"cluster_key": k, "change_type": "DORMANT", "before": before, "after": cur})
        elif before["window_mentions"] == 0 and cur["window_mentions"] > 0:
            out.append({"cluster_key": k, "change_type": "REVIVED", "before": before, "after": cur})
        elif cur["window_mentions"] > before["window_mentions"]:
            out.append({"cluster_key": k, "change_type": "ACTIVITY_UP", "before": before, "after": cur})
        elif cur["window_mentions"] < before["window_mentions"]:
            out.append({"cluster_key": k, "change_type": "ACTIVITY_DOWN", "before": before, "after": cur})
        if before["independent_source_count"] != cur["independent_source_count"] and before["status"] == cur["status"] == "ok":
            out.append({"cluster_key": k, "change_type": "INDEPENDENCE_CHANGED", "before": before, "after": cur})
        if before["status"] != cur["status"]:
            out.append({"cluster_key": k, "change_type": "STATUS_CHANGED", "before": before, "after": cur})
        if before["stance"] != cur["stance"] and before["conflicted"] == cur["conflicted"]:
            out.append({"cluster_key": k, "change_type": "STANCE_SHIFT", "before": before, "after": cur})
        if before["conflicted"] != cur["conflicted"]:
            out.append({"cluster_key": k, "change_type": "CONFLICT_CHANGED", "before": before, "after": cur})
    return out


# ---------- reading back ----------

def run_view(con: sqlite3.Connection, run_id: int) -> dict:
    r = con.execute("SELECT * FROM social_narrative_runs WHERE run_id=?", (run_id,)).fetchone()
    if r is None:
        raise KeyError(f"no narrative run {run_id}")
    clusters = []
    for c in con.execute("SELECT * FROM social_narrative_clusters WHERE run_id=? ORDER BY cluster_key", (run_id,)):
        d = dict(c)
        for k in [k for k in d if k.endswith("_json")]:
            d[k.removesuffix("_json")] = json.loads(d.pop(k))
        clusters.append(d)
    return {"run": {k: r[k] for k in r.keys() if k not in ("params_json", "unassigned_json", "summary_json")},
            "params": json.loads(r["params_json"]), "unassigned": json.loads(r["unassigned_json"]),
            "summary": json.loads(r["summary_json"]), "clusters": clusters}


def members(con: sqlite3.Connection, run_id: int, cluster_key: str) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM social_narrative_members WHERE run_id=? AND cluster_key=? ORDER BY claim_id", (run_id, cluster_key))]


def edges_for(con: sqlite3.Connection, run_id: int, cluster_key: str) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM social_narrative_edges WHERE run_id=? AND cluster_key=? ORDER BY from_item_key, to_item_key, edge_type",
                                         (run_id, cluster_key))]


def changes_for(con: sqlite3.Connection, run_id: int) -> list[dict]:
    out = []
    for r in con.execute("SELECT * FROM social_narrative_changes WHERE run_id=? ORDER BY cluster_key, change_type", (run_id,)):
        d = dict(r)
        d["before"], d["after"] = json.loads(d.pop("before_json")), json.loads(d.pop("after_json"))
        out.append(d)
    return out


def latest_run(con: sqlite3.Connection) -> int | None:
    r = con.execute("SELECT run_id FROM social_narrative_runs ORDER BY window_end DESC, run_id DESC LIMIT 1").fetchone()
    return r[0] if r else None


def explain(con: sqlite3.Connection, run_id: int, cluster_key: str) -> dict:
    """Why this cluster: the rule that put claims in it, the members with their roles and reasons, the dependency groups,
    the hypotheses, the coverage limits and the confidence basis. Every member names its claim and observation."""
    c = con.execute("SELECT * FROM social_narrative_clusters WHERE run_id=? AND cluster_key=?", (run_id, cluster_key)).fetchone()
    if c is None:
        raise KeyError(f"run {run_id} has no cluster {cluster_key}")
    ex = json.loads(c["explanation_json"])
    ms = members(con, run_id, cluster_key)
    return {"cluster_key": cluster_key, "label": c["label"], "status": c["status"], "reasons": json.loads(c["reasons_json"]),
            "confidence": c["confidence"], "why_cluster": ex["why_cluster"], "independence": ex["independence"],
            "confidence_basis": ex["confidence_basis"], "plain": ex["plain"],
            "members": [{k: m[k] for k in ("claim_id", "item_key", "observation_id", "source_id", "role", "group_id", "why", "event_time",
                                           "event_time_basis", "in_window", "source_state", "stance")} for m in ms],
            "edges": edges_for(con, run_id, cluster_key), "flags": json.loads(c["flags_json"]), "coverage": json.loads(c["coverage_json"]),
            "windows": json.loads(c["windows_json"]), "run_id": run_id}


def report(con: sqlite3.Connection, run_id: int) -> str:
    v = run_view(con, run_id)
    r = v["run"]
    L = [f"Narrative snapshot {run_id}: window {r['window_label']} ({r['window_start']:.0f} to {r['window_end']:.0f} UTC epoch), "
         f"cutoff {r['cutoff']:.0f}, {'complete' if r['window_complete'] else 'window still open'}, engine {r['engine_version']}.",
         f"{r['cluster_count']} cluster(s) from {r['input_claims']} claim(s). Compared with: {v['summary']['compared_to']}."]
    if r["contains_fixture"]:
        L.append("Contains fixture data (not live provider data).")
    for c in v["clusters"]:
        ind = "not estimable" if c["independent_source_count"] is None else str(c["independent_source_count"])
        L.append(f"- {c['label']} [{c['cluster_key']}]: {c['status']}, confidence {c['confidence']}, {c['window_mentions']} mention(s) in window, "
                 f"independent sources {ind}, amplifiers {c['amplifier_count']}, dependent {c['dependent_count']}, {c['freshness'].lower()}.")
    ch = v["summary"]["changes"]
    L.append("Changes since the previous snapshot: " + (", ".join(f"{n} {t}" for t, n in sorted(ch.items())) if ch else "none") + ".")
    if v["unassigned"]["claims_by_reason"]:
        L.append("Not clustered: " + ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in v["unassigned"]["claims_by_reason"].items()) + ".")
    return "\n".join(L)

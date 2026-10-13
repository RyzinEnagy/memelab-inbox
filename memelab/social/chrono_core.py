"""Phase 12: social claims against on-chain chronology. The pure engine: no I/O, no clock, no network.

One input document (schema memelab.social.chrono.input/1) holds, for one token and one social source: the source's posts about that token
(with publication time, every sighting by the lab and any later DELETED sighting), the wallets associated with the source and the Phase 09
level of that association, the wallets' classified on-chain events, pool liquidity observations and historical candles. The engine builds
one ordered timeline and says, for every pair of a post and a trade, whether the order is established or not.

Three clocks are kept apart (CHRONOLOGY_12.md has the full explanation):
  SOURCE_PUBLICATION  the time the platform says the post was published (provider timestamp, sometimes coarse or relative);
  CHAIN_BLOCK         the block time of the transaction (validator-estimated; a slot without a block time is bounded by its neighbours);
  COLLECTION          when the lab's collector saw the item, which is only ever an upper bound on publication.
Every timeline entry carries an interval [lo, hi) built from its clock, its precision and a tolerance. Two entries are ordered only when the
intervals do not overlap; otherwise the order is INDETERMINATE and says so.

Rules, each with a test in tests/test_social_chronology.py:
  - token identity (chain and contract) is checked on every join: posts, wallets, event legs, pool rows and candles; a symbol never joins;
  - only wallets at SIGNATURE_VERIFIED or CORROBORATED (LINKED) or an uncontested SELF_CLAIMED level are used for patterns; everything
    else stays visible as "unverified association" and produces no pattern; custody, protocol and pool wallets are excluded entirely;
  - a transfer is never a sale; a move to exchange custody is not an observed sale;
  - absence of a monitored trade is never evidence that none happened; every "without observed" pattern carries the coverage behind it;
  - risk flags are INFERENCE or HEURISTIC, never FACT, and never name intent; generated text is checked against a list of accusatory words.
"""
from __future__ import annotations

import re
import time as _time
from typing import Any

from .alpha_core import canon, sha

ENGINE_VERSION = "chronology-v1"
RULES_VERSION = "chrono-rules-v1"
SCHEMA = "memelab.social.chrono.input/1"
OUT_SCHEMA = "memelab.social.chrono.result/1"

LINKED_LEVELS = ("SIGNATURE_VERIFIED", "CORROBORATED")
CLAIMED_LEVELS = ("SELF_CLAIMED",)
NON_CONTROL_LABELS = ("CUSTODY_EXCHANGE", "CUSTODY_OTHER", "PROTOCOL", "POOL")
ATTRIBUTED = ("LINKED", "CLAIMED")
TRADE_ACTIONS = ("BUY", "SELL")
OK_STATUSES = ("OK", "PARTIAL")
GONE_STATUSES = ("DELETED", "NOT_FOUND")

DEFAULT_POLICY = {
    "window_before_s": 259200,           # timeline starts this long before the first post (72h)
    "window_after_s": 259200,            # and ends this long after the last one
    "pair_window_s": 86400,              # a trade and a post further apart than this (for certain) are not paired
    "promotion_after_s": 86400,          # a bullish post "promotes" from its publication until this long after it
    "provider_tolerance_s": 1,           # platform timestamp tolerance
    "default_provider_precision_s": 1,   # platform timestamps are to the second unless the input says otherwise
    "default_relative_precision_s": 3600,  # "2h ago" style timestamps
    "chain_tolerance_s": 2,              # block times are validator estimates
    "collector_tolerance_s": 5,          # the lab's collector clock
    "delayed_collection_s": 600,         # first seen more than this after publication: DELAYED_COLLECTION
    "stale_wallet_s": 21600,             # last good wallet fetch older than this at as_of: STALE_WALLET_DATA
    "stale_market_s": 21600,
    "stale_post_check_s": 86400,         # post not re-checked for this long: STALE_POST_CHECK
    "price_move_threshold": 0.20,        # zigzag threshold for a "major" price move
    "liquidity_change_threshold": 0.25,
    "market_source_preference": [],      # candle sources in order of preference; the first usable one wins, the rest are fallbacks
}

# Words that would turn an observed order into an accusation. Generated text is checked; a hit is a bug and the result is refused.
FORBIDDEN_WORDS = ("manipulat", "insider", "scam", "fraud", "pump and dump", "pump-and-dump", "dumped", "dumping", "front-ran", "frontran",
                   "front-run", "frontrun", "guilty", "criminal", "illegal", "his wallet", "her wallet", "owns the wallet", "owner of the wallet",
                   "colluded", "collusion", "deceiv", "lied", "exit scam", "rugged")


# ---------- small helpers ----------

def iso(t: float | None) -> str:
    if t is None:
        return "unknown"
    return _time.strftime("%Y-%m-%d %H:%M:%SZ", _time.gmtime(float(t)))


def _num(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ident(chain: Any, contract: Any) -> tuple[str, str] | None:
    """Canonical (chain, contract). EVM-style addresses compare lower-case; base58 is case-sensitive. None when either part is missing."""
    if not chain or not contract:
        return None
    ch, c = str(chain).strip().lower(), str(contract).strip()
    if c.lower().startswith("0x"):
        c = c.lower()
    return ch, c


def short(a: str | None) -> str:
    return "?" if not a else (a if len(a) <= 12 else f"{a[:6]}..{a[-4:]}")


def _amt(a: float) -> str:
    return f"{a:,.0f}" if float(a).is_integer() else f"{a:,.6g}"


def iv(lo, hi) -> dict:
    return {"lo": lo, "hi": hi}


def before(a: dict, b: dict) -> bool:
    """a ends no later than b starts (half-open intervals); an open end is never certain."""
    return a["hi"] is not None and b["lo"] is not None and a["hi"] <= b["lo"]


def relation(a: dict, b: dict) -> str:
    if before(a, b):
        return "BEFORE"
    if before(b, a):
        return "AFTER"
    return "INDETERMINATE"


def gap(a: dict, b: dict) -> dict:
    """Smallest and largest possible time from a to b (b minus a). None where an end is open."""
    mn = None if (b["lo"] is None or a["hi"] is None) else b["lo"] - a["hi"]
    mx = None if (b["hi"] is None or a["lo"] is None) else b["hi"] - a["lo"]
    return {"min_s": mn, "max_s": mx}


def _dist_min(a: dict, b: dict) -> float:
    """Smallest possible distance between two intervals (0 when they overlap; open ends count as overlap)."""
    if before(a, b):
        return b["lo"] - a["hi"]
    if before(b, a):
        return a["lo"] - b["hi"]
    return 0.0


def _ref(kind: str, ref: Any) -> dict | None:
    return None if ref in (None, "") else {"kind": kind, "ref": str(ref)}


def policy_of(p: dict | None) -> dict:
    out = dict(DEFAULT_POLICY)
    for k, v in (p or {}).items():
        if k not in DEFAULT_POLICY:
            raise ValueError(f"unknown policy key {k!r}")
        out[k] = v
    return out


# ---------- posts ----------

def _merge_posts(posts: list[dict], warnings: list[dict]) -> tuple[list[dict], int]:
    """One post per item_key. Sightings are merged and de-duplicated; a provider timestamp beats a parsed or missing one."""
    by: dict[str, dict] = {}
    dupes = 0
    for p in posts:
        k = str(p.get("item_key") or "")
        if not k:
            warnings.append({"code": "POST_WITHOUT_ITEM_KEY", "detail": "a post row without an item key was ignored"})
            continue
        if k not in by:
            q = dict(p)
            q["observations"] = list(p.get("observations") or [])
            by[k] = q
            continue
        dupes += 1
        q = by[k]
        q["observations"] += list(p.get("observations") or [])
        rank = {"PROVIDER": 2, "PARSED_RELATIVE": 1, "UNKNOWN": 0}
        if rank.get(p.get("published_basis") or "UNKNOWN", 0) > rank.get(q.get("published_basis") or "UNKNOWN", 0):
            for f in ("published_at", "published_basis", "published_precision_s"):
                q[f] = p.get(f)
        elif (p.get("published_basis") == q.get("published_basis") == "PROVIDER" and _num(p.get("published_at")) is not None
              and _num(p.get("published_at")) != _num(q.get("published_at"))):
            warnings.append({"code": "PUBLISHED_TIME_CONFLICT", "item_key": k,
                             "detail": f"two provider timestamps for one post ({p.get('published_at')} and {q.get('published_at')}); the earlier is kept"})
            q["published_at"] = min(_num(p["published_at"]), _num(q["published_at"]))
    out = []
    for k in sorted(by):
        q = by[k]
        seen, obs = set(), []
        for o in q["observations"]:
            key = (o.get("observation_id"), _num(o.get("observed_at")), o.get("status"))
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            obs.append(o)
        q["observations"] = sorted(obs, key=lambda o: (_num(o.get("observed_at")) is None, _num(o.get("observed_at")) or 0, str(o.get("observation_id"))))
        out.append(q)
    return out, dupes


def _post_entries(p: dict, pol: dict, warnings: list[dict]) -> tuple[dict | None, list[dict], str | None]:
    """The talk entry (publication), the collection entries (first seen, deletion observed) and an exclusion reason if the post is unplaced."""
    ctol = pol["collector_tolerance_s"]
    obs = p["observations"]
    ok = [o for o in obs if o.get("status") in OK_STATUSES and _num(o.get("observed_at")) is not None]
    first = ok[0] if ok else None
    fs = _num(first["observed_at"]) if first else None
    entries = []
    links = [x for x in (_ref("url", p.get("url")), _ref("item", p.get("item_key"))) if x]
    if first:
        entries.append({"kind": "POST_FIRST_SEEN", "clock": "COLLECTION", "basis": "COLLECTOR", "at": iv(fs - ctol, fs + ctol), "point": fs,
                        "item_key": p["item_key"], "links": links + [x for x in (_ref("observation", first.get("observation_id")),) if x],
                        "bucket": "FACT", "text": f"The lab first saw post {p['item_key']} (collector clock)."})
    # a later DELETED / NOT_FOUND sighting after the last good one: the post disappeared somewhere in between
    gone = None
    last_ok = None
    for o in obs:
        t = _num(o.get("observed_at"))
        if o.get("status") in OK_STATUSES and t is not None:
            last_ok, gone = o, None
        elif o.get("status") in GONE_STATUSES and t is not None and last_ok is not None and gone is None:
            gone = o
    if gone is not None:
        t0, t1 = _num(last_ok["observed_at"]), _num(gone["observed_at"])
        entries.append({"kind": "POST_REMOVAL_OBSERVED", "clock": "COLLECTION", "basis": "COLLECTOR", "at": iv(t0 - ctol, t1 + ctol), "point": t1,
                        "item_key": p["item_key"], "links": links + [x for x in (_ref("observation", gone.get("observation_id")),) if x],
                        "bucket": "FACT",
                        "text": (f"Post {p['item_key']} returned {gone['status']} when re-checked; it was last retrieved at {iso(t0)}. "
                                 "The lab's observation record and content hash are the remaining evidence.")})
    pub = _num(p.get("published_at"))
    basis = p.get("published_basis") or ("UNKNOWN" if pub is None else "PROVIDER")
    if pub is None:
        basis = "UNKNOWN"
    if basis == "PROVIDER":
        prec = _num(p.get("published_precision_s")) or pol["default_provider_precision_s"]
        tol = pol["provider_tolerance_s"]
        lo, hi = pub - tol, pub + prec + tol
        prec_note = f"platform timestamp, {int(prec)} s precision"
    elif basis == "PARSED_RELATIVE":
        prec = _num(p.get("published_precision_s")) or pol["default_relative_precision_s"]
        lo, hi = pub - prec, pub + prec
        prec_note = f"relative time parsed from the page, +/- {int(prec)} s"
    else:
        lo, hi, prec_note = None, None, "publication time unknown"
    if fs is not None:
        cap = fs + ctol
        if hi is None:
            hi, prec_note = cap, "publication time unknown; published no later than the lab's first sighting"
        elif lo is not None and lo > cap:
            warnings.append({"code": "PUBLISHED_AFTER_FIRST_SEEN", "item_key": p["item_key"],
                             "detail": "the platform time is later than the lab's first sighting; the interval covers both clocks"})
            lo = fs - ctol
        else:
            hi = min(hi, cap)
    if lo is None and hi is None:
        return None, entries, "NO_TIME"
    lag = None if (pub is None or fs is None or basis == "UNKNOWN") else fs - pub
    if lag is not None and lag > pol["delayed_collection_s"]:
        warnings.append({"code": "DELAYED_COLLECTION", "item_key": p["item_key"], "lag_s": lag,
                         "detail": (f"first seen {int(lag)} s after the platform's publication time (late delivery or late collection); "
                                    "ordering uses the publication time, and the lab could not have reacted before it saw the post")})
    kind = (p.get("talk_kind") or "ORIGINAL").upper()
    verb = {"REPOST": "reposted", "QUOTE": "quoted and commented on", "REPLY": "replied about"}.get(kind, "posted about")
    talk = {"kind": "POST_PUBLISHED", "clock": "SOURCE_PUBLICATION", "basis": basis, "precision": prec_note, "at": iv(lo, hi), "point": pub,
            "item_key": p["item_key"], "talk_kind": kind, "repost_of": p.get("repost_of"), "direction": (p.get("direction") or "UNKNOWN").upper(),
            "author_position": p.get("author_position"), "claim_id": p.get("claim_id"), "first_seen": fs, "collection_lag_s": lag,
            "links": links + [x for x in (_ref("observation", first.get("observation_id")) if first else None,) if x],
            "bucket": "FACT",
            "text": (f"The source {verb} the token in {p['item_key']}" + (f" (a repost of {p['repost_of']}; not the source's own words)" if kind == "REPOST" else "")
                     + f", stance {(p.get('direction') or 'UNKNOWN').upper()} ({prec_note}).")}
    return talk, entries, None


# ---------- wallets and events ----------

def _wallet_class(w: dict) -> tuple[str, str]:
    level = (w.get("level") or "NONE").upper()
    if (w.get("label_kind") or "").upper() in NON_CONTROL_LABELS or level == "UNSUPPORTED_CUSTODY":
        return "EXCLUDED_CUSTODY", "the wallet is labelled exchange custody, protocol or pool; its activity belongs to many people"
    if level == "DISPUTED":
        return "DISPUTED", "another account holds verified control of this wallet"
    others = [x for x in (w.get("other_claimants") or []) if x]
    if level in LINKED_LEVELS:
        return "LINKED", f"{level}: reviewed evidence ties the key to the account (not to a named person)"
    if level in CLAIMED_LEVELS:
        if others:
            return "CONTESTED", "self-claimed, and also claimed by " + ", ".join(sorted(map(str, others)))
        return "CLAIMED", "SELF_CLAIMED: the account says the wallet is its own; nothing independent confirms it"
    return "UNCERTAIN", f"{level}: not enough to associate the wallet with the account"


def _slot_bounds(events: list[dict], tol: float) -> dict:
    known = sorted({(int(e["slot"]), float(e["block_time"])) for e in events if _num(e.get("slot")) is not None and _num(e.get("block_time")) is not None})
    out = {}
    for e in events:
        if _num(e.get("block_time")) is None and _num(e.get("slot")) is not None:
            s = int(e["slot"])
            same = [t for k, t in known if k == s]
            if same:
                out[id(e)] = iv(min(same) - tol, max(same) + 1 + tol)
                continue
            lower = [t for k, t in known if k < s]
            upper = [t for k, t in known if k > s]
            if lower or upper:
                out[id(e)] = iv(max(lower) - tol if lower else None, min(upper) + 1 + tol if upper else None)
    return out


def _action(e: dict, legs: list[dict]) -> str:
    et = (e.get("event_type") or "").upper()
    side = (e.get("swap_side") or "").upper()
    if et == "FAILED":
        return "FAILED"
    if et == "SWAP":
        if side in ("BUY", "SELL"):
            return side
        dirs = {l.get("direction") for l in legs}
        return "BUY" if dirs == {"IN"} else "SELL" if dirs == {"OUT"} else "OTHER"
    if et == "TOKEN_TRANSFER_IN":
        return "TRANSFER_IN"
    if et == "TOKEN_TRANSFER_OUT":
        return "TRANSFER_OUT"
    if et in ("LP_ADD", "LP_REMOVE"):
        return et
    return "OTHER"


ACTION_TEXT = {"BUY": "bought", "SELL": "sold", "TRANSFER_IN": "received (transfer, not a purchase)", "TRANSFER_OUT": "sent (transfer, not a sale)",
               "TRANSFER_TO_CUSTODY": "moved to exchange custody (a sale there is not observable)", "INTERNAL_TRANSFER": "moved between its own associated wallets",
               "LP_ADD": "added liquidity with", "LP_REMOVE": "removed liquidity of", "OTHER": "had an unclassified movement of"}


# ---------- market ----------

def _zigzag(points: list[tuple[float, float, float]], thr: float) -> list[tuple[int, int]]:
    """Swing segments (i, j): the value moved by at least thr (a fraction) from a local extreme to the next one. points: (t_start, t_end, value).
    A flat run before a move pivots at its last point; a peak or trough is its first occurrence."""
    n = len(points)
    if n < 2:
        return []
    v = [p[2] for p in points]
    segs, lo_i, hi_i, trend, piv, ext = [], 0, 0, 0, 0, 0
    for i in range(1, n):
        x = v[i]
        if trend == 0:
            if x <= v[lo_i]:
                lo_i = i
            if x >= v[hi_i]:
                hi_i = i
            if v[lo_i] > 0 and hi_i > lo_i and v[hi_i] / v[lo_i] - 1 >= thr:
                trend, piv, ext = 1, lo_i, hi_i
            elif v[hi_i] > 0 and lo_i > hi_i and v[lo_i] / v[hi_i] - 1 <= -thr:
                trend, piv, ext = -1, hi_i, lo_i
            continue
        if (trend > 0 and x > v[ext]) or (trend < 0 and x < v[ext]):
            ext = i
            continue
        if v[ext] <= 0:
            continue
        rev = x / v[ext] - 1
        if (trend > 0 and rev <= -thr) or (trend < 0 and rev >= thr):
            segs.append((piv, ext))
            piv, ext, trend = ext, i, -trend
    if trend != 0 and v[piv] > 0 and abs(v[ext] / v[piv] - 1) >= thr:
        segs.append((piv, ext))
    return segs


# ---------- the evaluation ----------

def evaluate(doc: dict, policy: dict | None = None) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"input schema must be {SCHEMA}")
    pol = policy_of(policy if policy is not None else doc.get("policy"))
    as_of = _num(doc.get("as_of"))
    if as_of is None:
        raise ValueError("as_of is required: the evaluation must say what it could have known")
    tok = ident((doc.get("token") or {}).get("chain"), (doc.get("token") or {}).get("contract"))
    if tok is None:
        raise ValueError("token needs chain and contract; a symbol is never an identity")
    src = doc.get("source") or {}
    sid = str(src.get("source_id") or "")
    if not sid:
        raise ValueError("source.source_id is required")
    warnings: list[dict] = []
    exclusions: list[dict] = []
    joins = {"checked": 0, "rejected": {}}

    def reject(what, ref, reason, detail=None):
        joins["rejected"][reason] = joins["rejected"].get(reason, 0) + 1
        exclusions.append({"what": what, "ref": ref, "reason": reason, **({"detail": detail} if detail else {})})

    # --- posts: token identity, then times
    posts, post_dupes = _merge_posts(list(doc.get("posts") or []), warnings)
    talks, collection = [], []
    for p in posts:
        joins["checked"] += 1
        t = p.get("token") or {}
        pid = ident(t.get("chain"), t.get("contract"))
        if (t.get("status") or "").lower() != "resolved" or pid is None:
            reject("post", p["item_key"], "TOKEN_UNRESOLVED", f"mention status {t.get('status') or 'missing'}; a ticker or name alone never joins")
            continue
        if pid[0] != tok[0]:
            reject("post", p["item_key"], "CHAIN_MISMATCH", f"post token is on {pid[0]}")
            continue
        if pid[1] != tok[1]:
            reject("post", p["item_key"], "TOKEN_MISMATCH", f"resolved to {short(pid[1])}" + (f" (same symbol {t.get('symbol')})" if t.get("symbol") else ""))
            continue
        talk, coll, why = _post_entries(p, pol, warnings)
        collection += coll
        if talk is None:
            reject("post", p["item_key"], "NO_TIME", "neither a publication time nor a sighting time")
            continue
        talks.append(talk)

    # --- window
    win = doc.get("window") or {}
    w_lo, w_hi = _num(win.get("from")), _num(win.get("to"))
    if w_lo is None or w_hi is None:
        anchors = [x["at"] for x in talks]
        los = [a["lo"] for a in anchors if a["lo"] is not None] + [a["hi"] for a in anchors if a["lo"] is None and a["hi"] is not None]
        his = [a["hi"] for a in anchors if a["hi"] is not None]
        if los:
            w_lo = w_lo if w_lo is not None else min(los) - pol["window_before_s"]
            w_hi = w_hi if w_hi is not None else max(his) + pol["window_after_s"]
    if w_hi is not None:
        w_hi = min(w_hi, as_of)
    window = {"from": w_lo, "to": w_hi, "basis": "input" if win else ("posts" if w_lo is not None else "none")}

    def in_window(a: dict) -> bool:
        if w_lo is None:
            return True
        lo = a["lo"] if a["lo"] is not None else a["hi"]
        hi = a["hi"] if a["hi"] is not None else a["lo"]
        return not (hi is not None and hi < w_lo) and not (lo is not None and lo > w_hi)

    # --- wallets
    wallets, wclass = [], {}
    for w in doc.get("wallets") or []:
        joins["checked"] += 1
        wid = ident(w.get("chain"), w.get("wallet"))
        if wid is None:
            reject("wallet", w.get("wallet"), "INVALID_WALLET")
            continue
        if wid[0] != tok[0]:
            reject("wallet", wid[1], "CHAIN_MISMATCH", f"wallet is on {wid[0]}, the token on {tok[0]}")
            continue
        cls, why = _wallet_class(w)
        if wid in wclass:
            continue
        wclass[wid] = cls
        wallets.append({"chain": wid[0], "wallet": wid[1], "class": cls, "level": (w.get("level") or "NONE").upper(), "why": why,
                        "confidence": w.get("confidence") or "UNKNOWN", "account_entity": w.get("account_entity"),
                        "other_claimants": sorted(map(str, w.get("other_claimants") or [])), "label_kind": w.get("label_kind"),
                        "links": [x for x in ([_ref("assertion", a) for a in (w.get("assertion_ids") or [])] +
                                              [_ref("evidence", r) for r in (w.get("evidence_refs") or [])]) if x],
                        "real_world_identity": "UNKNOWN"})

    # --- wallet events: dedupe, identity, time
    raw_events, seen_ev, ev_dupes = [], set(), 0
    for e in doc.get("wallet_events") or []:
        k = (str(e.get("chain") or "").lower(), str(e.get("signature") or ""), str(e.get("wallet") or ""))
        if k in seen_ev:
            ev_dupes += 1
            continue
        seen_ev.add(k)
        raw_events.append(e)
    slot_iv = _slot_bounds(raw_events, pol["chain_tolerance_s"])
    by_sig: dict[str, list[dict]] = {}
    trades, others_tl = [], []
    for e in raw_events:
        joins["checked"] += 1
        sig = str(e.get("signature") or "")
        wid = ident(e.get("chain"), e.get("wallet"))
        if wid is None or not sig:
            reject("wallet_event", sig or None, "INCOMPLETE_EVENT", "an event needs chain, wallet and signature")
            continue
        if wid[0] != tok[0]:
            reject("wallet_event", sig, "CHAIN_MISMATCH", f"event is on {wid[0]}")
            continue
        if wid not in wclass:
            reject("wallet_event", sig, "WALLET_NOT_IN_SET", "event of a wallet with no association record in this input")
            continue
        legs = [l for l in (e.get("legs") or []) if ident(e.get("chain"), l.get("contract")) == tok]
        if not legs:
            reject("wallet_event", sig, "UNRELATED_ASSET", "no leg moves this token (another token or the native coin)")
            continue
        act = _action(e, legs)
        if act == "FAILED":
            reject("wallet_event", sig, "FAILED_TX", "failed transaction moved nothing")
            continue
        bt = _num(e.get("block_time"))
        tol = pol["chain_tolerance_s"]
        if bt is not None:
            a, basis = iv(bt - tol, bt + 1 + tol), "BLOCK_TIME"
        elif id(e) in slot_iv:
            a, basis = slot_iv[id(e)], "SLOT_BOUNDED"
            warnings.append({"code": "CHAIN_TIME_MISSING", "signature": sig,
                             "detail": "no block time; bounded by the block times of neighbouring slots in this input"})
        else:
            reject("wallet_event", sig, "CHAIN_TIME_MISSING", "no block time and no neighbouring slot to bound it; it cannot be placed")
            continue
        amount = sum(float(l.get("amount") or 0) for l in legs)
        ent = {"kind": "WALLET_" + act, "action": act, "clock": "CHAIN_BLOCK", "basis": basis, "at": a, "point": bt, "slot": e.get("slot"),
               "signature": sig, "wallet": wid[1], "wallet_class": wclass[wid], "amount": amount,
               "counterparty_labels": sorted({str(l.get("counterparty_label")) for l in legs if l.get("counterparty_label")}),
               "custody_touch": e.get("custody_touch"), "event_id": e.get("event_id"),
               "links": [x for x in (_ref("tx_url", e.get("url")), _ref("tx", sig), _ref("wallet_event", e.get("event_id"))) if x],
               "bucket": "FACT"}
        if not in_window(a):
            reject("wallet_event", sig, "OUTSIDE_WINDOW")
            continue
        if a["lo"] is not None and a["lo"] > as_of:
            reject("wallet_event", sig, "AFTER_AS_OF", "later than the evaluation time; never used")
            continue
        if act == "TRANSFER_OUT" and (e.get("custody_touch") or any(x in NON_CONTROL_LABELS for x in ent["counterparty_labels"])):
            ent["action"], ent["kind"] = "TRANSFER_TO_CUSTODY", "WALLET_TRANSFER_TO_CUSTODY"
        by_sig.setdefault(sig, []).append(ent)
        (trades if wclass[wid] in ATTRIBUTED else others_tl).append(ent)
    for sig, ents in by_sig.items():
        att = [x for x in ents if x["wallet_class"] in ATTRIBUTED]
        if len({x["wallet"] for x in att}) > 1 and {x["action"] for x in att} >= {"TRANSFER_OUT", "TRANSFER_IN"}:
            for x in att:
                x["action"], x["kind"] = "INTERNAL_TRANSFER", "WALLET_INTERNAL_TRANSFER"
    for x in trades + others_tl:
        assoc = {"LINKED": "a wallet linked to the source", "CLAIMED": "a wallet the source says is its own",
                 "CONTESTED": "a wallet with a contested association", "DISPUTED": "a wallet whose association is disputed",
                 "UNCERTAIN": "a wallet with an unverified association", "EXCLUDED_CUSTODY": "a custody wallet"}[x["wallet_class"]]
        x["text"] = f"{short(x['wallet'])} ({assoc}) {ACTION_TEXT.get(x['action'], 'moved')} {_amt(x['amount'])} of the token in tx {short(x['signature'])}."
    custody = [x for x in others_tl if x["wallet_class"] == "EXCLUDED_CUSTODY"]
    others_tl = [x for x in others_tl if x["wallet_class"] != "EXCLUDED_CUSTODY"]
    for x in custody:
        reject("wallet_event", x["signature"], "CUSTODY_WALLET", "custody wallet activity is many people's and is not placed on this timeline")

    # --- pool liquidity observations
    pool_tl = []
    for r in doc.get("pool_events") or []:
        joins["checked"] += 1
        pid = ident(r.get("chain"), r.get("contract"))
        if pid != tok:
            reject("pool_event", r.get("ref") or r.get("pool"), "TOKEN_MISMATCH" if pid and pid[0] == tok[0] else "CHAIN_MISMATCH")
            continue
        t = _num(r.get("time"))
        if t is None:
            reject("pool_event", r.get("ref") or r.get("pool"), "NO_TIME")
            continue
        clock = "CHAIN_BLOCK" if (r.get("time_basis") or "CHAIN_BLOCK") == "CHAIN_BLOCK" else "COLLECTION"
        tol = pol["chain_tolerance_s"] if clock == "CHAIN_BLOCK" else pol["collector_tolerance_s"]
        a = iv(t - tol, t + 1 + tol)
        if not in_window(a) or t > as_of:
            reject("pool_event", r.get("ref") or r.get("pool"), "OUTSIDE_WINDOW")
            continue
        kind = (r.get("kind") or "LIQUIDITY_SNAPSHOT").upper()
        liq = _num(r.get("liquidity_usd"))
        txt = {"LP_ADD": "Liquidity was added to pool", "LP_REMOVE": "Liquidity was removed from pool"}.get(kind, "Pool liquidity was observed for")
        pool_tl.append({"kind": "POOL_" + kind, "clock": clock, "basis": r.get("time_basis") or "CHAIN_BLOCK", "at": a, "point": t,
                        "links": [x for x in (_ref("source", r.get("source")), _ref("ref", r.get("ref"))) if x], "bucket": "FACT",
                        "text": f"{txt} {short(r.get('pool'))}" + (f" (liquidity {liq:,.0f} USD as reported)" if liq is not None else "") + "."})

    # --- market candles: identity, kind, preference and fallback
    market_tl, market = [], {"status": "NO_HISTORY", "source": None, "fallback_used": False, "moves": [], "per_post": []}
    usable = []
    for s in doc.get("market") or []:
        joins["checked"] += 1
        sidn = ident(s.get("chain"), s.get("contract"))
        if sidn != tok:
            reject("candles", s.get("source"), "TOKEN_MISMATCH" if sidn and sidn[0] == tok[0] else "CHAIN_MISMATCH")
            continue
        if s.get("as_of_kind") != "HISTORICAL_CANDLE":
            reject("candles", s.get("source"), "LIVE_QUOTE_AS_HISTORY", "a quote observed at fetch time is never used as a past price")
            continue
        cs = _num(s.get("candle_seconds"))
        rows = sorted([r for r in (s.get("rows") or []) if _num(r.get("t")) is not None and _num(r.get("c")) is not None and cs
                       and _num(r["t"]) + cs <= as_of], key=lambda r: r["t"])
        rows = [r for r in rows if w_lo is None or (r["t"] + cs >= w_lo and r["t"] <= w_hi)]
        if not rows:
            continue
        usable.append((s, cs, rows))
    if usable:
        pref = list(pol["market_source_preference"] or [])
        usable.sort(key=lambda u: (pref.index(u[0].get("source")) if u[0].get("source") in pref else len(pref), str(u[0].get("source"))))
        s, cs, rows = usable[0]
        market.update(status="CANDLES", source=s.get("source"), fallback_used=bool(pref) and s.get("source") != pref[0],
                      candle_seconds=cs, first=rows[0]["t"], last=rows[-1]["t"] + cs)
        pts = [(float(r["t"]), float(r["t"]) + cs, float(r["c"])) for r in rows]
        for i, j in _zigzag(pts, pol["price_move_threshold"]):
            ch = pts[j][2] / pts[i][2] - 1
            m = {"from": pts[i][1], "to": pts[j][1], "change": round(ch, 4), "source": s.get("source")}
            market["moves"].append(m)
            market_tl.append({"kind": "PRICE_MOVE", "clock": "CANDLE", "basis": "HISTORICAL_CANDLE", "at": iv(pts[j][0], pts[j][1]), "point": pts[j][1],
                              "links": [x for x in (_ref("candles", s.get("source")),) if x], "bucket": "FACT",
                              "text": f"Price {'rose' if ch > 0 else 'fell'} {abs(ch) * 100:.0f}% between {iso(pts[i][1])} and {iso(pts[j][1])} (candle closes, {s.get('source')})."})
        lq = [(float(r["t"]), float(r["t"]) + cs, float(r["liq"])) for r in rows if _num(r.get("liq")) is not None and float(r["liq"]) > 0]
        for i, j in _zigzag(lq, pol["liquidity_change_threshold"]):
            ch = lq[j][2] / lq[i][2] - 1
            market_tl.append({"kind": "LIQUIDITY_CHANGE", "clock": "CANDLE", "basis": "HISTORICAL_CANDLE", "at": iv(lq[j][0], lq[j][1]), "point": lq[j][1],
                              "links": [x for x in (_ref("candles", s.get("source")),) if x], "bucket": "FACT",
                              "text": f"Pool liquidity {'rose' if ch > 0 else 'fell'} {abs(ch) * 100:.0f}% to {lq[j][2]:,.0f} USD between {iso(lq[i][1])} and {iso(lq[j][1])} ({s.get('source')})."})
        for t in talks:
            lo, hi = t["at"]["lo"], t["at"]["hi"]
            if lo is None or hi is None:
                market["per_post"].append({"item_key": t["item_key"], "status": "PUBLICATION_TIME_OPEN"})
                continue
            prior = [p for p in pts if p[1] <= lo]
            after = [p for p in pts if p[0] >= hi]
            if not prior:
                market["per_post"].append({"item_key": t["item_key"], "status": "NO_CANDLE_BEFORE_POST"})
                continue
            base = prior[-1][2]
            pre = [p for p in prior if p[1] >= lo - pol["pair_window_s"]]
            d = {"item_key": t["item_key"], "status": "OK", "price_before": base,
                 "change_prior_window": round(base / pre[0][2] - 1, 4) if pre and pre[0][2] > 0 else None}
            for h in (3600, 21600, 86400):
                hit = [p for p in after if p[1] <= hi + h]
                d[f"change_{h // 3600}h"] = round(hit[-1][2] / base - 1, 4) if hit and base > 0 and hit[-1][1] >= hi + h - cs else None
            market["per_post"].append(d)
        stale = as_of - market["last"]
        if w_hi is not None and stale > pol["stale_market_s"]:
            warnings.append({"code": "STALE_MARKET_DATA", "detail": f"newest candle ends {int(stale)} s before the evaluation time"})
    else:
        warnings.append({"code": "MISSING_PRICE_HISTORY", "detail": "no historical candles for this token in the window; market movement is not established"})
    if (doc.get("coverage") or {}).get("providers", {}).get("market") == "UNAVAILABLE" and not usable:
        market["status"] = "PROVIDER_UNAVAILABLE"

    # --- coverage
    cov = doc.get("coverage") or {}
    providers = cov.get("providers") or {}
    mon = {}
    for m in cov.get("wallet_monitoring") or []:
        k = ident(m.get("chain"), m.get("wallet"))
        if k:
            mon.setdefault(k, []).append((_num(m.get("from")), _num(m.get("to")), m.get("last_ok_fetch")))

    def covered(lo, hi) -> str:
        att = [(w["chain"], w["wallet"]) for w in wallets if w["class"] in ATTRIBUTED]
        if not att:
            return "NO_ATTRIBUTED_WALLET"
        if providers.get("wallet") == "UNAVAILABLE":
            return "PROVIDER_UNAVAILABLE"
        if lo is None or hi is None:
            return "PARTIAL"
        res = []
        for k in att:
            spans = [(a, b) for a, b, _ in mon.get(k, []) if a is not None and b is not None]
            if any(a <= lo and hi <= b for a, b in spans):
                res.append("FULL")
            elif any(not (b < lo or a > hi) for a, b in spans):
                res.append("PARTIAL")
            else:
                res.append("NONE")
        return "FULL" if all(r == "FULL" for r in res) else "NONE" if all(r == "NONE" for r in res) else "PARTIAL"

    for k, spans in mon.items():
        lastok = [_num(x[2]) for x in spans if _num(x[2]) is not None]
        if k in wclass and wclass[k] in ATTRIBUTED and lastok and as_of - max(lastok) > pol["stale_wallet_s"]:
            warnings.append({"code": "STALE_WALLET_DATA", "wallet": k[1], "detail": f"last good fetch {int(as_of - max(lastok))} s before the evaluation time"})
    for p in posts:
        ts = [_num(o.get("observed_at")) for o in p["observations"] if _num(o.get("observed_at")) is not None]
        if ts and as_of - max(ts) > pol["stale_post_check_s"] and any(t["item_key"] == p["item_key"] for t in talks):
            warnings.append({"code": "STALE_POST_CHECK", "item_key": p["item_key"],
                             "detail": f"not re-checked for {int(as_of - max(ts))} s; it may have been edited or removed since"})

    # --- patterns
    pw = pol["pair_window_s"]
    att_trades = [x for x in trades if x["action"] in TRADE_ACTIONS]
    patterns, paired_talk, paired_trade = [], set(), set()
    for ti, t in enumerate(talks):
        for xi, x in enumerate(att_trades):
            if _dist_min(t["at"], x["at"]) > pw:
                continue
            rel = relation(x["at"], t["at"])
            paired_talk.add(ti)
            paired_trade.add(xi)
            g = gap(x["at"], t["at"])
            if rel == "INDETERMINATE":
                name, order = "ORDER_INDETERMINATE", "INDETERMINATE"
            elif rel == "BEFORE":
                name, order = "TRADE_BEFORE_TALK", "CONFIDENT"
            else:
                name, order = "TALK_BEFORE_TRADE", "CONFIDENT"
            patterns.append({"pattern": name, "order": order, "talk": t["item_key"], "talk_kind": t["talk_kind"], "direction": t["direction"],
                             "author_position": t["author_position"], "trade": x["signature"], "action": x["action"], "wallet": x["wallet"],
                             "attribution": x["wallet_class"], "trade_minus_talk": {"min_s": None if g["max_s"] is None else -g["max_s"],
                                                                                    "max_s": None if g["min_s"] is None else -g["min_s"]},
                             "bucket": "UNKNOWN" if order == "INDETERMINATE" else ("INFERENCE" if x["wallet_class"] == "LINKED" else "HEURISTIC")})
    for ti, t in enumerate(talks):
        if ti in paired_talk:
            continue
        c = covered(None if t["at"]["lo"] is None else t["at"]["lo"] - pw, None if t["at"]["hi"] is None else t["at"]["hi"] + pw)
        patterns.append({"pattern": "TALK_WITHOUT_OBSERVED_TRADE", "order": "NOT_APPLICABLE", "talk": t["item_key"], "talk_kind": t["talk_kind"],
                         "direction": t["direction"], "monitoring_coverage": c, "bucket": "UNKNOWN",
                         "note": "No trade by an associated wallet was observed near this post. That is not evidence that none happened"
                                 + {"NO_ATTRIBUTED_WALLET": ": the source has no wallet the lab can associate with it.",
                                    "PROVIDER_UNAVAILABLE": ": the wallet data provider was unavailable.",
                                    "NONE": ": the associated wallets were not monitored over this window.",
                                    "PARTIAL": ": monitoring covered only part of the window.",
                                    "FULL": ", and other wallets the source may use are not known."}[c]})
    posts_enum = bool(cov.get("posts_enumerated")) and providers.get("social") != "UNAVAILABLE"
    for xi, x in enumerate(att_trades):
        if xi in paired_trade:
            continue
        patterns.append({"pattern": "TRADE_WITHOUT_OBSERVED_TALK", "order": "NOT_APPLICABLE", "trade": x["signature"], "action": x["action"],
                         "wallet": x["wallet"], "attribution": x["wallet_class"], "posts_enumerated": posts_enum, "bucket": "UNKNOWN",
                         "note": "No post about this token by the source was observed near this trade. "
                                 + ("The collector enumerated the source's posts for the window; deleted or private posts would still be missed."
                                    if posts_enum else "The source's posts were not fully enumerated, so a post may exist that the lab did not see.")})
    # distribution during promotion: an associated wallet's sale while bullish posts are recent
    longs = [t for t in talks if t["direction"] == "LONG"]
    after = pol["promotion_after_s"]
    for x in att_trades:
        if x["action"] != "SELL":
            continue
        best = None
        for t in longs:
            ta, xa = t["at"], x["at"]
            if xa["lo"] is None or xa["hi"] is None:
                continue
            certain = ta["hi"] is not None and ta["lo"] is not None and xa["lo"] >= ta["hi"] and xa["hi"] <= ta["lo"] + after
            possible = not before(xa, ta) and not (ta["hi"] is not None and xa["lo"] > ta["hi"] + after)
            if certain:
                best = ("CONFIDENT", t)
                break
            if possible and best is None:
                best = ("INDETERMINATE", t)
        if best:
            conf = best[0] == "CONFIDENT"
            patterns.append({"pattern": "POTENTIAL_DISTRIBUTION_DURING_PROMOTION", "order": best[0], "talk": best[1]["item_key"],
                             "talk_kind": best[1]["talk_kind"], "trade": x["signature"], "action": "SELL", "wallet": x["wallet"],
                             "attribution": x["wallet_class"],
                             "bucket": "INFERENCE" if (x["wallet_class"] == "LINKED" and conf) else "HEURISTIC",
                             "note": ("A wallet associated with the source sold after its bullish post and while the post was recent. "
                                      if conf else
                                      "A wallet associated with the source sold close to its bullish post; whether the sale came after the post is not established. ")
                                     + "This is an observed sequence. Intent, the source's total holding and any coordination are not established."})

    # --- timeline
    tl = talks + collection + trades + others_tl + pool_tl + market_tl
    tl = [e for e in tl if e["kind"] in ("POST_FIRST_SEEN", "POST_REMOVAL_OBSERVED") or in_window(e["at"])]
    kind_rank = {"POST_PUBLISHED": 0, "POST_FIRST_SEEN": 2, "POST_REMOVAL_OBSERVED": 3}
    tl.sort(key=lambda e: (e["at"]["lo"] if e["at"]["lo"] is not None else (e["at"]["hi"] if e["at"]["hi"] is not None else 0) - 1e12,
                           e["at"]["hi"] if e["at"]["hi"] is not None else 1e18, kind_rank.get(e["kind"], 1), str(e.get("item_key") or e.get("signature") or e["text"])))
    gid, ghi, started = 0, None, False
    for e in tl:
        lo, hi = e["at"]["lo"], e["at"]["hi"]
        if not started or (lo is not None and ghi is not None and lo >= ghi):
            gid, ghi, started = gid + 1, hi, True
        else:
            ghi = None if (ghi is None or hi is None) else max(ghi, hi)
        e["order_group"] = gid
    sizes: dict[int, int] = {}
    for e in tl:
        sizes[e["order_group"]] = sizes.get(e["order_group"], 0) + 1
    for i, e in enumerate(tl):
        e["seq"] = i + 1
        e["order_within_group"] = "NOT_ESTABLISHED" if sizes[e["order_group"]] > 1 else "SOLE"
        e["time_display"] = (iso(e["point"]) if e.get("point") is not None else
                             (f"no later than {iso(e['at']['hi'])}" if e["at"]["hi"] is not None else "unknown"))

    pair_orders = [p["order"] for p in patterns if p["pattern"] in ("TRADE_BEFORE_TALK", "TALK_BEFORE_TRADE", "ORDER_INDETERMINATE")]
    if not pair_orders:
        order_status = "NOT_APPLICABLE"
    elif all(o == "CONFIDENT" for o in pair_orders):
        order_status = "CONFIDENT"
    elif all(o == "INDETERMINATE" for o in pair_orders):
        order_status = "INDETERMINATE"
    else:
        order_status = "MIXED"

    flags = _flags(tok, sid, patterns, wallets, warnings, exclusions, talks, trades, others_tl)
    summary = _summary(tok, src, talks, collection, trades, others_tl, wallets, patterns, market, market_tl, warnings, exclusions, cov)
    res = {"schema": OUT_SCHEMA, "engine_version": ENGINE_VERSION, "rules_version": RULES_VERSION, "label": doc.get("label"),
           "is_fixture": bool(doc.get("is_fixture")), "as_of": as_of, "token": {"chain": tok[0], "contract": tok[1], "symbol": (doc.get("token") or {}).get("symbol")},
           "source": {"source_id": sid, "label": src.get("label") or sid, "accounts": src.get("accounts") or []}, "window": window,
           "policy": pol, "policy_sha256": sha(pol), "input_sha256": sha({"doc": doc, "policy": pol}),
           "clocks": CLOCKS, "timeline": [_public(e) for e in tl], "order_status": order_status, "patterns": patterns, "wallets": wallets,
           "market": market, "exclusions": exclusions, "join_checks": joins,
           "dedupe": {"post_rows_merged": post_dupes, "wallet_events_dropped": ev_dupes}, "coverage": {"posts_enumerated": posts_enum, "providers": providers},
           "warnings": warnings, "flags": flags, "summary": summary}
    guard_text(res)
    return res


CLOCKS = {
    "SOURCE_PUBLICATION": "the time the platform reports for the post. Precision varies (seconds from an API, minutes on some pages, hours for 'x ago' text).",
    "CHAIN_BLOCK": "the block time of the transaction, estimated by validators; a slot without a block time is bounded by neighbouring slots.",
    "COLLECTION": "when the lab's collector saw or re-checked the post. It is an upper bound on publication and says when the lab could have known.",
    "CANDLE": "the start and end of a historical candle from a named market data source.",
}


def _public(e: dict) -> dict:
    keep = ("seq", "order_group", "order_within_group", "kind", "clock", "basis", "precision", "at", "point", "time_display", "item_key", "talk_kind",
            "direction", "signature", "wallet", "wallet_class", "action", "amount", "bucket", "text", "links", "collection_lag_s")
    return {k: e[k] for k in keep if k in e and e[k] is not None}


def _flag(tok, sid, flag, category, bucket, rule, *, order="NOT_APPLICABLE", attribution=None, at=None, evidence=None, note=None) -> dict:
    if category == "RISK" and bucket not in ("INFERENCE", "HEURISTIC"):
        raise ValueError("a risk flag is INFERENCE or HEURISTIC, never FACT")
    if category == "RISK" and attribution not in ATTRIBUTED:
        raise ValueError("a risk flag needs a linked or self-claimed wallet")
    body = {"chain": tok[0], "contract": tok[1], "source_id": sid, "flag": flag, "category": category, "bucket": bucket, "rule": rule,
            "order_status": order, "attribution": attribution, "at": at, "evidence": sorted(set(evidence or [])), "note": note}
    body["flag_key"] = sha({k: v for k, v in body.items() if k != "note"})
    return body


def _flags(tok, sid, patterns, wallets, warnings, exclusions, talks, trades, others_tl) -> list[dict]:
    talk_at = {t["item_key"]: t for t in talks}
    tr = {x["signature"]: x for x in trades}
    out = []

    def ev(p):
        e = []
        if p.get("talk") in talk_at:
            e += [l["ref"] for l in talk_at[p["talk"]]["links"]]
        if p.get("trade") in tr:
            e += [l["ref"] for l in tr[p["trade"]]["links"]]
        return e

    for p in patterns:
        n = p["pattern"]
        x = tr.get(p.get("trade"))
        at = (x or talk_at.get(p.get("talk")) or {}).get("point")
        if n == "TRADE_BEFORE_TALK":
            disclosed = (p.get("author_position") or "").lower() in ("holds",)
            if p["action"] == "BUY" and p["direction"] == "LONG" and disclosed:
                out.append(_flag(tok, sid, "DISCLOSED_POSITION_CONSISTENT", "CORROBORATION", p["bucket"], "chrono.disclosure_consistent.v1", order=p["order"],
                                 attribution=p["attribution"], at=at, evidence=ev(p),
                                 note="the post says the author holds the token, and an associated wallet bought before the post"))
            elif p["action"] == "BUY" and p["direction"] == "LONG":
                out.append(_flag(tok, sid, "TRADE_BEFORE_TALK", "RISK", p["bucket"], "chrono.trade_before_talk.v1", order=p["order"], attribution=p["attribution"],
                                 at=at, evidence=ev(p), note="an associated wallet bought before a bullish post that did not disclose a position"))
            else:
                out.append(_flag(tok, sid, "TRADE_BEFORE_TALK", "CONTEXT", p["bucket"], "chrono.trade_before_talk.v1", order=p["order"], attribution=p["attribution"],
                                 at=at, evidence=ev(p)))
        elif n == "TALK_BEFORE_TRADE":
            out.append(_flag(tok, sid, "TALK_BEFORE_TRADE", "CONTEXT", p["bucket"], "chrono.talk_before_trade.v1", order=p["order"], attribution=p["attribution"],
                             at=at, evidence=ev(p)))
        elif n == "ORDER_INDETERMINATE":
            out.append(_flag(tok, sid, "ORDER_INDETERMINATE", "DATA_QUALITY", "UNKNOWN", "chrono.order_overlap.v1", order="INDETERMINATE",
                             attribution=p["attribution"], at=at, evidence=ev(p), note="post and trade intervals overlap; the order is not established"))
        elif n == "POTENTIAL_DISTRIBUTION_DURING_PROMOTION":
            out.append(_flag(tok, sid, n, "RISK", p["bucket"], "chrono.sale_during_promotion.v1", order=p["order"], attribution=p["attribution"], at=at,
                             evidence=ev(p), note="observed sequence only; intent and total holdings are not established"))
        elif n in ("TALK_WITHOUT_OBSERVED_TRADE", "TRADE_WITHOUT_OBSERVED_TALK"):
            out.append(_flag(tok, sid, n, "CONTEXT", "UNKNOWN", f"chrono.{n.lower()}.v1", attribution=p.get("attribution"), at=at, evidence=ev(p),
                             note=p.get("monitoring_coverage") or ("posts enumerated" if p.get("posts_enumerated") else "posts not enumerated")))
    for w in wallets:
        if w["class"] in ("UNCERTAIN", "CONTESTED", "DISPUTED", "EXCLUDED_CUSTODY"):
            n = {"UNCERTAIN": "ATTRIBUTION_UNCERTAIN", "CONTESTED": "ATTRIBUTION_CONTESTED", "DISPUTED": "ATTRIBUTION_DISPUTED",
                 "EXCLUDED_CUSTODY": "CUSTODY_WALLET_EXCLUDED"}[w["class"]]
            cnt = sum(1 for x in others_tl if x["wallet"] == w["wallet"])
            out.append(_flag(tok, sid, n, "DATA_QUALITY", "UNKNOWN", "chrono.attribution_gate.v1", attribution=w["class"],
                             evidence=[l["ref"] for l in w["links"]], note=f"{w['why']}; {cnt} event(s) shown without attribution"))
    for code in sorted({w["code"] for w in warnings}):
        refs = sorted({str(w.get("item_key") or w.get("signature") or w.get("wallet") or "") for w in warnings if w["code"] == code} - {""})
        out.append(_flag(tok, sid, code, "DATA_QUALITY", "FACT", f"chrono.{code.lower()}.v1", evidence=refs))
    bad = sorted({str(e["ref"]) for e in exclusions if e["reason"] in ("TOKEN_MISMATCH", "TOKEN_UNRESOLVED", "CHAIN_MISMATCH") and e["ref"]})
    if bad:
        out.append(_flag(tok, sid, "IDENTITY_JOIN_REJECTED", "DATA_QUALITY", "FACT", "chrono.identity_join.v1", evidence=bad,
                         note="rows whose chain or contract did not match the token were left out; a symbol never joins"))
    seen, uniq = set(), []
    for f in out:
        if f["flag_key"] not in seen:
            seen.add(f["flag_key"])
            uniq.append(f)
    return sorted(uniq, key=lambda f: (f["category"], f["flag"], f["at"] or 0, f["flag_key"]))


def _line(text: str, links: list[dict]) -> dict:
    return {"text": text, "links": [l["ref"] for l in links]}


def _summary(tok, src, talks, collection, trades, others_tl, wallets, patterns, market, market_tl, warnings, exclusions, cov) -> dict:
    fact, inf, ne = [], [], []
    tlinks = {t["item_key"]: t["links"] for t in talks}
    xlinks = {x["signature"]: x["links"] for x in trades}
    wlinks = {w["wallet"]: w["links"] for w in wallets}

    def pl(p):
        return [l["ref"] for l in tlinks.get(p.get("talk"), []) + xlinks.get(p.get("trade"), []) + wlinks.get(p.get("wallet"), [])]

    for t in talks:
        when = iso(t["point"]) if t["point"] is not None else f"no later than {iso(t['at']['hi'])}"
        fact.append(_line(f"{t['text'][:-1]} at {when}.", t["links"]))
        if t.get("collection_lag_s") is not None:
            fact.append(_line(f"The lab first saw {t['item_key']} {int(t['collection_lag_s'])} s after its publication time.", t["links"]))
    for c in collection:
        if c["kind"] == "POST_REMOVAL_OBSERVED":
            fact.append(_line(c["text"], c["links"]))
    for x in trades + others_tl:
        fact.append(_line(f"{x['text'][:-1]} at block time {iso(x['point']) if x['point'] is not None else 'unknown (slot-bounded)'}.", x["links"]))
    for m in market_tl:
        fact.append(_line(m["text"], m["links"]))
    for w in wallets:
        if w["class"] == "LINKED":
            inf.append(_line(f"Wallet {short(w['wallet'])} is associated with the source at level {w['level']}. This concerns control of a key, not who the person is.", w["links"]))
        elif w["class"] == "CLAIMED":
            inf.append(_line(f"Wallet {short(w['wallet'])} is the source's own claim (SELF_CLAIMED); patterns that use it are HEURISTIC.", w["links"]))
        else:
            ne.append(_line(f"That wallet {short(w['wallet'])} belongs to the source ({w['why']}).", w["links"]))
    for p in patterns:
        n = p["pattern"]
        if n in ("TRADE_BEFORE_TALK", "TALK_BEFORE_TRADE"):
            g = p["trade_minus_talk"]
            d = (f"{abs(int(g['max_s'] if n == 'TRADE_BEFORE_TALK' else g['min_s']))} s" if (g["max_s"] if n == "TRADE_BEFORE_TALK" else g["min_s"]) is not None else "an unknown time")
            what = ("came at least " + d + " before") if n == "TRADE_BEFORE_TALK" else ("came at least " + d + " after")
            inf.append({"text": f"The {p['action'].lower()} in {short(p['trade'])} {what} post {p['talk']} ({p['bucket']}, attribution {p['attribution']}).",
                        "links": pl(p)})
        elif n == "ORDER_INDETERMINATE":
            ne.append({"text": f"Whether the {p['action'].lower()} in {short(p['trade'])} came before or after post {p['talk']}: the time intervals overlap.", "links": pl(p)})
        elif n == "POTENTIAL_DISTRIBUTION_DURING_PROMOTION" and p["order"] != "CONFIDENT":
            ne.append({"text": f"Whether the sale in {short(p['trade'])} came after bullish post {p['talk']}: the intervals overlap ({p['bucket']}).", "links": pl(p)})
        elif n == "POTENTIAL_DISTRIBUTION_DURING_PROMOTION":
            inf.append({"text": f"An associated wallet sold ({short(p['trade'])}) while bullish post {p['talk']} was recent ({p['bucket']}, order {p['order']}).", "links": pl(p)})
        elif n == "TALK_WITHOUT_OBSERVED_TRADE":
            ne.append({"text": f"Whether the source traded around post {p['talk']}. {p['note']}", "links": pl(p)})
        elif n == "TRADE_WITHOUT_OBSERVED_TALK":
            ne.append({"text": f"Whether the source posted around the {p['action'].lower()} in {short(p['trade'])}. {p['note']}", "links": pl(p)})
    if market["status"] != "CANDLES":
        ne.append({"text": "Market movement around the posts: no historical candles were available.", "links": []})
    ne.append({"text": "Who controls any wallet in the real world, the source's intent, other wallets the source may use, and whether the price moved because of a post.",
               "links": []})
    return {"fact": fact, "inference": inf, "not_established": ne}


_FORBIDDEN_RE = re.compile("|".join(r"\b" + re.escape(w) for w in FORBIDDEN_WORDS), re.I)


def _texts(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("text", "note", "detail", "why"):
                if isinstance(v, str):
                    yield v
            else:
                yield from _texts(v)
    elif isinstance(o, list):
        for v in o:
            yield from _texts(v)


def guard_text(res: dict) -> None:
    """Refuse a result whose generated wording accuses anyone. Inputs are ids and numbers, so a hit means the engine wrote it."""
    for t in _texts(res):
        m = _FORBIDDEN_RE.search(t)
        if m:
            raise RuntimeError(f"generated text contains {m.group(0)!r}; the chronology engine never accuses: {t[:120]}")


def analyze(doc: dict, policy: dict | None = None) -> dict:
    """Evaluate twice and compare hashes; a mismatch means the engine is not deterministic and the result is refused."""
    a, b = evaluate(doc, policy), evaluate(doc, policy)
    ha, hb = sha(a), sha(b)
    if ha != hb:
        raise RuntimeError("chronology evaluation is not deterministic; result refused")
    a["result_sha256"] = ha
    return a


# ---------- human-readable report ----------

def report(res: dict, limit: int = 60) -> str:
    L = []
    if res.get("is_fixture"):
        L.append("INVENTED FIXTURE DATA: no real post, wallet, token or person.")
    tk = res["token"]
    L.append(f"Chronology for {tk['chain']}:{tk['contract']}" + (f" ({tk['symbol']}, symbol shown for reading only)" if tk.get("symbol") else ""))
    L.append(f"Source: {res['source']['label']}   evaluated as of {iso(res['as_of'])}   window {iso(res['window']['from'])} to {iso(res['window']['to'])}")
    L.append(f"Order between posts and trades: {res['order_status']}")
    L.append("")
    L.append("Clocks: SOURCE_PUBLICATION is the platform's time for a post; CHAIN_BLOCK is the block time of a transaction; COLLECTION is when the lab saw "
             "the post. Entries in the same group overlap in time and their order is not established.")
    L.append("")
    L.append("Timeline")
    for e in res["timeline"][:limit]:
        mark = "~" if e["order_within_group"] == "NOT_ESTABLISHED" else " "
        L.append(f" {e['seq']:>3} g{e['order_group']:<3}{mark} {e['time_display']:<26} {e['clock']:<19} {e['text']}")
    if len(res["timeline"]) > limit:
        L.append(f"  ... {len(res['timeline']) - limit} more entries")
    L.append("")
    L.append("Observed patterns")
    if not res["patterns"]:
        L.append("  none (no post about this token by the source in the window)")
    for p in res["patterns"]:
        tail = p.get("note") or ""
        L.append(f"  {p['pattern']} [{p['bucket']}, order {p['order']}] post {p.get('talk', '-')} trade {short(p.get('trade'))}" + (f": {tail}" if tail else ""))
    s = res["summary"]
    for title, key in (("Fact", "fact"), ("Inference", "inference"), ("Not established", "not_established")):
        L.append("")
        L.append(title)
        for x in s[key]:
            L.append(f"  - {x['text']}" + (f"  [{'; '.join(x['links'])}]" if x["links"] else ""))
    if res["warnings"]:
        L.append("")
        L.append("Warnings")
        for w in res["warnings"]:
            L.append(f"  {w['code']}: {w['detail']}")
    if res["exclusions"]:
        L.append("")
        L.append("Excluded from the timeline")
        for x in res["exclusions"]:
            L.append(f"  {x['what']} {short(str(x['ref'])) if x['ref'] else '-'}: {x['reason']}" + (f" ({x['detail']})" if x.get("detail") else ""))
    L.append("")
    L.append("Absence of a monitored trade is not evidence that none occurred. No statement here identifies a person or claims intent.")
    out = "\n".join(L)
    m = _FORBIDDEN_RE.search(out)
    if m:
        raise RuntimeError(f"report contains {m.group(0)!r}")
    return out

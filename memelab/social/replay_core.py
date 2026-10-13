"""Phase 17: causal historical replay, matched baselines and statistical honesty. Pure engine: no I/O, no network, no clock.

Question answered: on the history the lab actually has, would four kinds of research signal have done better than comparable
tokens, measured the same way, with a sample large and clean enough to say so? The four are
  INDIVIDUAL     one original directional post by one analyst source,
  CONVERGENCE    original posts from several independent sources (distinct independence groups) inside a window,
  SOCIAL_WALLET  independent posts plus a buy by a wallet linked to a registry source (accepted linkage only),
  TRENDING       the raw baseline: raw mention count (reposts and duplicates included) or a provider trending list.
When the history is too thin the answer is "insufficient sample/data" or "cannot validate yet", never an extrapolation.

Rules (DECISIONS D-112 to D-118):
  - Cutoff clock. Every record carries `_avail`, the earliest moment it was demonstrably available: a post's first
    observation, a wallet event's or trending list's arrival, a candle's close plus the provider's documented publication
    lag (or the lab's capture time). A strategy only ever sees records through a CutoffView whose accessors return records
    with `_avail <= cutoff`, and every returned record is audited again; a record from after the cutoff raises LeakageError.
  - Signals are decided at the moment the newest input became available. The entry is the decision time plus the
    execution lag (Phase 16 engine, D-108); the event or publication time is never used as an entry.
  - Outcomes reuse the Phase 16 outcome engine (outcomes_core.evaluate): dated prices only, no invented exits, three
    return figures kept apart; the replay uses the modeled net return. Labels are computed with a label clock: train
    labels as known at the train boundary, validation labels at the validation boundary, test labels at the data end.
  - Splits are chronological (train, validation, test) with an embargo: a sample whose outcome window crosses its split's
    boundary is purged, never moved. Thresholds are chosen on train labels only (LabelGate refuses anything else),
    frozen with a hash, then validation is reported, then the test split is evaluated once.
  - Controls are matched at the decision time from what was visible then: same chain, liquidity band (and market-cap band
    when both are known), fresh price, no delisting known, not mentioned socially in the lookback; the calendar regime is
    shared by construction (same decision time). Fewer than control_min measured controls: no relative return.
  - Two lenses. measured: MEASURED outcomes only. conservative (headline): a long whose token was delisted before the exit
    counts as a total loss (-100%), for signals and controls alike. A missing price without delisting evidence stays
    missing; it is never filled in.
  - Uncertainty: order-statistic interval for the median, Wilson interval for precision, both adjusted (Bonferroni) for
    strategies x horizons. Estimates are not printed below min_report_n. Medians, not means, are the headline; the
    report shows whether a single outcome dominates.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from statistics import NormalDist, median
from typing import Any

from . import outcomes_core as OC
from .alpha_core import median_ci, wilson

ENGINE_VERSION = "replay-v1"
RULES_VERSION = "replay-rules-v1"
SCHEMA = "memelab.social.replay.input/1"
POLICY_SCHEMA = "memelab.social.replay.policy/1"
STRATEGIES = ("INDIVIDUAL", "CONVERGENCE", "SOCIAL_WALLET", "TRENDING")
STRATEGY_TEXT = {
    "INDIVIDUAL": "(a) individual analyst signal: one original LONG post",
    "CONVERGENCE": "(b) independent convergence: original LONG posts from several independence groups",
    "SOCIAL_WALLET": "(c) social + wallet confirmation: independent posts plus a linked-wallet buy",
    "TRENDING": "(d) raw mention / trending baseline: raw mentions incl. reposts, or a provider trending list",
}
SPLITS = ("train", "validation", "test")
DIRECTIONS = ("LONG", "SHORT", "EXIT", "NEUTRAL", "UNKNOWN")
LINKAGES = ("SELF_CLAIMED", "SIGNED_MESSAGE", "CHAIN_EVIDENCE", "THIRD_PARTY_CLAIM", "DISPUTED", "RETRACTED", "UNKNOWN")

DEFAULT_POLICY: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "policy_version": "replay-default-1",
    "horizons_s": [3600, 21600, 86400, 259200],
    "primary_horizon_s": 86400,
    "split_fractions": [0.5, 0.25, 0.25],
    "signal_cooldown_s": 259200,          # one signal per strategy configuration and token in this window
    "conflict_window_s": 86400,           # an opposite original post inside this window suppresses the signal
    "content_dup_window_s": 86400,        # same source, same content key inside this window: one post
    "social_window_s": 86400,             # SOCIAL_WALLET: window for the posts
    "accepted_linkage": ["SELF_CLAIMED", "SIGNED_MESSAGE", "CHAIN_EVIDENCE"],
    "clock_tolerance_s": 60,
    "max_candle_period_s": 86400,         # longest candle accepted; outcome lookups start this far before the entry
    "grid": {
        "INDIVIDUAL": [{"max_capture_lag_s": 900}, {"max_capture_lag_s": 3600}, {"max_capture_lag_s": 21600}],
        "CONVERGENCE": [{"min_sources": k, "window_s": w} for k in (2, 3, 4) for w in (21600, 86400)],
        "SOCIAL_WALLET": [{"min_sources": k, "wallet_window_s": w} for k in (1, 2) for w in (21600, 86400)],
        "TRENDING": [{"min_mentions": m, "window_s": 86400, "max_rank": 10} for m in (3, 5, 10)],
    },
    "control_min": 3,
    "control_max": 8,
    "liq_band_ratio": 3.0,
    "mcap_band_ratio": 4.0,
    "control_price_max_age_s": 7200,
    "control_exclusion_lookback_s": 604800,   # a token mentioned in a visible post this recently is not a neutral control
    "control_trending_lookback_s": 86400,     # a token on a visible trending list this recently is not a neutral control
    "min_tune_n": 8,                      # fewer train values: the configuration is not eligible for selection
    "min_report_n": 10,                   # fewer values: no estimate is printed
    "min_test_n": 30,                     # fewer test values with controls: INSUFFICIENT_SAMPLE
    "min_coverage": 0.6,                  # measured (or delisted) / matured below this: INSUFFICIENT_DATA
    "alpha": 0.05,
    "dominance_share": 0.5,               # one outcome above this share of all positive relative return: dominance flag
    "outcome_policy": {},                 # overrides for the Phase 16 outcome policy (horizons are taken from here)
    "trade_execution_impact": "none",
}


class ReplayError(ValueError):
    pass


class LeakageError(RuntimeError):
    """A record from after the cutoff reached a strategy, or a held-out label reached the tuner."""


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def r10(x):
    return None if x is None else round(float(x), 10)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def tkey(chain, contract) -> tuple[str, str]:
    c = str(contract or "")
    return str(chain or "").lower(), (c.lower() if c.startswith("0x") else c)


def iso(t: float | None) -> str:
    return "none" if t is None else datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_policy(override: dict | None = None) -> dict:
    pol = copy.deepcopy(DEFAULT_POLICY)
    for k, v in (override or {}).items():
        if any(b in k.lower() for b in OC.FORBIDDEN_POLICY_KEYS):
            raise ReplayError(f"policy key {k!r} is refused: the replay never trades")
        if k not in pol:
            raise ReplayError(f"unknown policy key {k!r}")
        pol[k] = copy.deepcopy(v)
    if pol["trade_execution_impact"] != "none":
        raise ReplayError("trade_execution_impact must be 'none'")
    if pol["primary_horizon_s"] not in pol["horizons_s"]:
        raise ReplayError("primary_horizon_s must be one of horizons_s")
    fr = pol["split_fractions"]
    if len(fr) != 3 or any(not _num(f) or f <= 0 for f in fr) or abs(sum(fr) - 1) > 1e-9:
        raise ReplayError("split_fractions must be three positive numbers that sum to 1")
    if set(pol["grid"]) != set(STRATEGIES) or any(not pol["grid"][s] for s in STRATEGIES):
        raise ReplayError(f"grid must give at least one configuration for each of {STRATEGIES}")
    pol["outcome"] = OC.make_policy(dict(pol["outcome_policy"], horizons_s=list(pol["horizons_s"])))
    pol["policy_sha256"] = sha({k: v for k, v in pol.items() if k != "policy_sha256"})
    return pol


# ---------- data preparation ----------

def _excl(ex: dict, kind: str, reason: str) -> None:
    d = ex.setdefault(kind, {})
    d[reason] = d.get(reason, 0) + 1


class Data:
    """Normalized replay input. Nothing here is visible to a strategy except through a CutoffView."""

    def __init__(self):
        self.posts: list[dict] = []
        self.wallet: list[dict] = []
        self.trending: list[dict] = []
        self.tokens: dict[tuple, dict] = {}
        self.obs: dict[tuple, list[dict]] = {}
        self.obs_t: dict[tuple, list[float]] = {}
        self.status: dict[tuple, list[dict]] = {}
        self.maxper: dict[tuple, int] = {}
        self.pidx: dict[tuple, dict] = {}
        self.sources: dict[str, str] = {}
        self.regimes: list[dict] = []
        self.excluded: dict[str, dict[str, int]] = {}
        self.counts: dict[str, int] = {}


def _avail_list(rows):
    return [r["_avail"] for r in rows]


def prepare(doc: dict, pol: dict) -> Data:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ReplayError(f"document schema must be {SCHEMA}")
    as_of = doc.get("as_of")
    if not _num(as_of):
        raise ReplayError("as_of is required: it is the end of the data clock")
    d = Data()
    d.as_of = float(as_of)
    d.label = doc.get("label")
    d.is_fixture = bool(doc.get("is_fixture"))
    cov = copy.deepcopy(doc.get("coverage") or {})
    d.coverage = cov
    provs = cov.get("providers") or {}
    tol = pol["clock_tolerance_s"]
    ex = d.excluded

    for s in doc.get("sources") or []:
        sid = str(s.get("source_id") or "")
        if sid:
            d.sources[sid] = str(s.get("independence_group") or sid)

    for t in doc.get("tokens") or []:
        k = tkey(t.get("chain"), t.get("contract"))
        if not k[0] or not k[1]:
            _excl(ex, "tokens", "NO_IDENTITY")
            continue
        dl = t.get("delisted_at")
        d.tokens[k] = {"chain": k[0], "contract": k[1], "listed_at": t.get("listed_at"),
                       "delisted_at": float(dl) if _num(dl) else None,
                       "delisted_available_at": float(t.get("delisted_available_at", dl)) if _num(dl) else None}

    # posts: one row per post_id (an ingested duplicate keeps the earliest availability)
    seen: dict[str, dict] = {}
    for i, p in enumerate(doc.get("posts") or []):
        pid = str(p.get("post_id") or "")
        if not pid:
            _excl(ex, "posts", "NO_POST_ID")
            continue
        pub, av = p.get("published_at"), p.get("available_at")
        if not _num(av):
            _excl(ex, "posts", "NO_AVAILABILITY_EVIDENCE")
            continue
        if not _num(pub):
            _excl(ex, "posts", "PUBLISHED_AT_UNKNOWN")
            continue
        if av < pub - tol:
            _excl(ex, "posts", "AVAILABLE_BEFORE_PUBLISHED")
            continue
        if av > d.as_of:
            _excl(ex, "posts", "AFTER_DATA_END")
            continue
        sid = str(p.get("source_id") or "")
        if not sid:
            _excl(ex, "posts", "NO_SOURCE")
            continue
        dirn = str(p.get("direction") or "UNKNOWN").upper()
        k = tkey(p.get("chain"), p.get("contract")) if p.get("chain") and p.get("contract") else None
        row = {"rid": f"post:{pid}", "post_id": pid, "source_id": sid, "group": d.sources.get(sid, sid), "key": k,
               "direction": dirn if dirn in DIRECTIONS else "UNKNOWN", "published_at": float(pub), "_avail": float(av),
               "captured_at": float(p["captured_at"]) if _num(p.get("captured_at")) else None,
               "repost_of": p.get("repost_of"), "content_key": p.get("content_key"), "provider": p.get("provider")}
        if pid in seen:
            _excl(ex, "posts", "DUPLICATE_POST_ID")
            if row["_avail"] < seen[pid]["_avail"]:
                seen[pid] = row
            continue
        seen[pid] = row
    posts = sorted(seen.values(), key=lambda r: (r["_avail"], r["rid"]))
    last_content: dict[tuple, float] = {}
    for r in posts:
        r["original"] = not r["repost_of"]
        r["dup"] = False
        if r["content_key"]:
            ck = (r["source_id"], r["content_key"])
            if ck in last_content and r["published_at"] - last_content[ck] <= pol["content_dup_window_s"]:
                r["dup"] = True
            else:
                last_content[ck] = r["published_at"]
        if r["key"] is None:
            _excl(ex, "posts", "TOKEN_UNRESOLVED_KEPT_FOR_COUNTS")
    d.posts = posts
    d.counts["posts_reposts"] = sum(1 for r in posts if not r["original"])
    d.counts["posts_content_duplicates"] = sum(1 for r in posts if r["dup"])

    for i, w in enumerate(doc.get("wallet_events") or []):
        av, bt = w.get("available_at"), w.get("block_time")
        if not _num(av) or not _num(bt):
            _excl(ex, "wallet_events", "NO_TIME_OR_AVAILABILITY")
            continue
        if av < bt - tol:
            _excl(ex, "wallet_events", "AVAILABLE_BEFORE_BLOCK")
            continue
        if av > d.as_of:
            _excl(ex, "wallet_events", "AFTER_DATA_END")
            continue
        side = str(w.get("side") or "").upper()
        if side not in ("BUY", "SELL"):
            _excl(ex, "wallet_events", "NOT_A_SWAP_SIDE")
            continue
        if not (w.get("chain") and w.get("contract")):
            _excl(ex, "wallet_events", "TOKEN_UNRESOLVED")
            continue
        link = str(w.get("linkage") or "UNKNOWN").upper()
        d.wallet.append({"rid": f"wallet:{w.get('event_id') or i}", "source_id": str(w.get("source_id") or ""),
                         "linkage": link if link in LINKAGES else "UNKNOWN", "key": tkey(w["chain"], w["contract"]),
                         "side": side, "block_time": float(bt), "_avail": float(av),
                         "captured_at": float(w["captured_at"]) if _num(w.get("captured_at")) else None})
    d.wallet.sort(key=lambda r: (r["_avail"], r["rid"]))

    for i, t in enumerate(doc.get("trending") or []):
        av = t.get("available_at")
        if not _num(av) or not _num(t.get("t")):
            _excl(ex, "trending", "NO_TIME_OR_AVAILABILITY")
            continue
        if av > d.as_of:
            _excl(ex, "trending", "AFTER_DATA_END")
            continue
        if not (t.get("chain") and t.get("contract")):
            _excl(ex, "trending", "TOKEN_UNRESOLVED")
            continue
        rank = t.get("rank")
        d.trending.append({"rid": f"trend:{t.get('snapshot_id') or 's'}:{i}", "key": tkey(t["chain"], t["contract"]),
                           "rank": int(rank) if _num(rank) else None, "t": float(t["t"]), "_avail": float(av),
                           "provider": t.get("provider"), "captured_at": float(t["captured_at"]) if _num(t.get("captured_at")) else None})
    d.trending.sort(key=lambda r: (r["_avail"], r["rid"]))

    # market observations, normalized by the Phase 16 engine; availability is the candle close plus publication lag
    ocp = pol["outcome"]
    raw_obs: list[tuple[dict, float | None]] = []
    for c in doc.get("candles") or []:
        per = c.get("period_s")
        av = c.get("available_at")
        if isinstance(per, int) and per > pol["max_candle_period_s"]:
            _excl(ex, "candles", "PERIOD_TOO_LONG")
            continue
        if not _num(av):
            lag = (provs.get(str(c.get("provider"))) or {}).get("publication_lag_s")
            if not (_num(lag) and _num(c.get("t")) and isinstance(per, int)):
                _excl(ex, "candles", "NO_PUBLICATION_LAG")
                continue
            av = c["t"] + per + lag
        o = {"kind": "CANDLE", "chain": c.get("chain"), "contract": c.get("contract"), "t": c.get("t"), "available_at": av,
             "provider": c.get("provider"), "period_s": per, "o": c.get("o"), "h": c.get("h"), "l": c.get("l"), "c": c.get("c"),
             "is_fixture": d.is_fixture}
        if c.get("liq") is not None:
            o["liquidity_usd"] = c["liq"]
        raw_obs.append((o, c.get("mcap")))
    for p in doc.get("points") or []:
        o = {"kind": "POINT", "chain": p.get("chain"), "contract": p.get("contract"), "t": p.get("t"), "available_at": p.get("available_at"),
             "provider": p.get("provider"), "price": p.get("price"), "is_fixture": d.is_fixture}
        if p.get("liq") is not None:
            o["liquidity_usd"] = p["liq"]
        raw_obs.append((o, p.get("mcap")))
    for k, m in d.tokens.items():
        if m["delisted_at"] is not None:
            raw_obs.append(({"kind": "STATUS", "chain": k[0], "contract": k[1], "t": m["delisted_at"],
                             "available_at": m["delisted_available_at"], "provider": "token-meta", "status": "DELISTED"}, None))
    seq = 0
    for o, mc in raw_obs:
        kind = "candles" if o["kind"] == "CANDLE" else ("points" if o["kind"] == "POINT" else "status")
        try:
            n = OC.normalize_observation(o, ocp)
        except OC.OutcomeError as e:
            _excl(ex, kind, _refusal_code(str(e)))
            continue
        if n["available_at"] > d.as_of:
            _excl(ex, kind, "AFTER_DATA_END")
            continue
        seq += 1
        n["seq"] = seq
        n["contract"] = tkey(n["chain"], n["contract"])[1]
        n["mcap"] = float(mc) if _num(mc) and mc > 0 else None
        d.obs.setdefault((n["chain"], n["contract"]), []).append(n)
    for k, lst in d.obs.items():
        lst.sort(key=lambda o: (o["t"], o["available_at"], o["seq"]))
        d.obs_t[k] = [o["t"] for o in lst]
        d.pidx[k] = _price_index(lst)
        d.status[k] = [o for o in lst if o["kind"] == "STATUS"]
        d.maxper[k] = max([o.get("period_s") or 0 for o in lst] + [0])
        d.tokens.setdefault(k, {"chain": k[0], "contract": k[1], "listed_at": None, "delisted_at": None, "delisted_available_at": None})

    for g in doc.get("regimes") or []:
        if _num(g.get("t_start")) and _num(g.get("available_at")) and g.get("label"):
            d.regimes.append({"chain": str(g.get("chain") or "").lower() or None, "t_start": float(g["t_start"]),
                              "_avail": float(g["available_at"]), "label": str(g["label"])})
    d.regimes.sort(key=lambda g: (g["_avail"], g["t_start"]))

    d.post_av = _avail_list(d.posts)
    d.wallet_av = _avail_list(d.wallet)
    d.trend_av = _avail_list(d.trending)
    d.posts_by_key: dict[tuple, list[dict]] = {}
    for r in d.posts:
        if r["key"]:
            d.posts_by_key.setdefault(r["key"], []).append(r)
    d.pbk_av = {k: _avail_list(v) for k, v in d.posts_by_key.items()}
    d.wallet_by_key: dict[tuple, list[dict]] = {}
    for r in d.wallet:
        d.wallet_by_key.setdefault(r["key"], []).append(r)
    d.wbk_av = {k: _avail_list(v) for k, v in d.wallet_by_key.items()}
    d.trend_by_key: dict[tuple, list[dict]] = {}
    for r in d.trending:
        d.trend_by_key.setdefault(r["key"], []).append(r)
    d.tbk_av = {k: _avail_list(v) for k, v in d.trend_by_key.items()}
    d.counts.update(posts=len(d.posts), wallet_events=len(d.wallet), trending=len(d.trending),
                    observations=sum(len(v) for v in d.obs.values()), tokens_with_prices=len(d.obs), tokens=len(d.tokens))
    starts = [x for x in (d.post_av[:1] + d.wallet_av[:1] + d.trend_av[:1])]
    d.t_start = min(starts) if starts else None
    d.input_sha256 = sha(doc)
    return d


def _refusal_code(msg: str) -> str:
    m = msg.lower()
    for needle, code in (("future-dated", "FUTURE_DATED_AT_CAPTURE"), ("not a finished candle", "UNFINISHED_CANDLE_AT_CAPTURE"),
                         ("high/low", "BAD_OHLC"), ("needs chain and contract", "NO_IDENTITY"), ("needs t ", "NO_TIME"),
                         ("needs a provider", "NO_PROVIDER"), ("period_s", "BAD_PERIOD"), ("liquidity_usd", "BAD_LIQUIDITY"),
                         ("status", "BAD_STATUS")):
        if needle in m:
            return code
    return "REFUSED_OTHER"


def _price_index(obs: list[dict]) -> dict:
    """Prefix-best lookups by availability: the newest price (and liquidity, market cap) known at any cutoff."""
    pev, lev, mev = [], [], []
    for o in obs:
        if o["kind"] == "POINT" and o.get("price") is not None:
            pev.append((o["available_at"], o["t"], o["price"]))
        elif o["kind"] == "CANDLE" and o.get("c") is not None:
            pev.append((o["available_at"], o["t"] + o["period_s"], o["c"]))
        if o.get("liquidity_usd") is not None and o["kind"] in ("POINT", "CANDLE"):
            lev.append((o["available_at"], o["t"], o["liquidity_usd"]))
        if o.get("mcap") is not None:
            mev.append((o["available_at"], o["t"], o["mcap"]))

    def build(ev):
        ev.sort(key=lambda x: (x[0], x[1]))
        av, best, cur = [], [], None
        for e in ev:
            if cur is None or (e[1], e[0]) >= (cur[1], cur[0]):
                cur = e
            av.append(e[0])
            best.append(cur)
        return av, best

    return {"price": build(pev), "liq": build(lev), "mcap": build(mev)}


def _lookup(ix, cutoff):
    av, best = ix
    i = bisect_right(av, cutoff) - 1
    return best[i] if i >= 0 else None


# ---------- the cutoff clock ----------

class Audit:
    def __init__(self):
        self.accesses = 0
        self.records = 0
        self.max_lead_s = None    # largest (cutoff - avail) seen: diagnostic only

    def check(self, kind: str, rows, cutoff: float):
        self.accesses += 1
        for r in rows:
            a = r["_avail"] if isinstance(r, dict) else r[0]
            self.records += 1
            if a > cutoff:
                raise LeakageError(f"{kind} record available at {a} reached a strategy at cutoff {cutoff}")
        return rows


class CutoffView:
    """Everything a strategy may know at `cutoff`. The _raw accessors filter by availability; the public accessors also audit."""

    def __init__(self, data: Data, cutoff: float, audit: Audit):
        self.d, self.cutoff, self.audit = data, float(cutoff), audit

    def _raw_posts_on(self, key, since_avail):
        rows = self.d.posts_by_key.get(key, [])
        av = self.d.pbk_av.get(key, [])
        return rows[bisect_left(av, since_avail):bisect_right(av, self.cutoff)]

    def _raw_wallet_on(self, key, since_avail):
        rows = self.d.wallet_by_key.get(key, [])
        av = self.d.wbk_av.get(key, [])
        return rows[bisect_left(av, since_avail):bisect_right(av, self.cutoff)]

    def _raw_trending_on(self, key, since_avail):
        rows = self.d.trend_by_key.get(key, [])
        av = self.d.tbk_av.get(key, [])
        return rows[bisect_left(av, since_avail):bisect_right(av, self.cutoff)]

    def _raw_posts_since(self, since_avail):
        return self.d.posts[bisect_left(self.d.post_av, since_avail):bisect_right(self.d.post_av, self.cutoff)]

    def _raw_trending_since(self, since_avail):
        return self.d.trending[bisect_left(self.d.trend_av, since_avail):bisect_right(self.d.trend_av, self.cutoff)]

    def posts_on(self, key, since_avail=float("-inf")):
        return self.audit.check("post", self._raw_posts_on(key, since_avail), self.cutoff)

    def wallet_on(self, key, since_avail=float("-inf")):
        return self.audit.check("wallet", self._raw_wallet_on(key, since_avail), self.cutoff)

    def trending_on(self, key, since_avail=float("-inf")):
        return self.audit.check("trending", self._raw_trending_on(key, since_avail), self.cutoff)

    def posts_since(self, since_avail):
        return self.audit.check("post", self._raw_posts_since(since_avail), self.cutoff)

    def trending_since(self, since_avail):
        return self.audit.check("trending", self._raw_trending_since(since_avail), self.cutoff)

    def market(self, key) -> dict:
        ix = self.d.pidx.get(key)
        out = {"price": None, "price_t": None, "liq": None, "mcap": None}
        if ix:
            p, l, m = _lookup(ix["price"], self.cutoff), _lookup(ix["liq"], self.cutoff), _lookup(ix["mcap"], self.cutoff)
            self.audit.check("market", [x for x in (p, l, m) if x], self.cutoff)
            if p:
                out.update(price=p[2], price_t=p[1])
            if l:
                out["liq"] = l[2]
            if m:
                out["mcap"] = m[2]
        return out

    def delisted(self, key) -> bool:
        m = self.d.tokens.get(key) or {}
        return m.get("delisted_available_at") is not None and m["delisted_available_at"] <= self.cutoff

    def chain_tokens(self, chain):
        return [k for k in self.d.pidx if k[0] == chain]

    def regime(self, chain) -> str:
        lab = None
        for g in self.d.regimes:
            if g["_avail"] > self.cutoff:
                break
            if (g["chain"] in (None, chain)) and g["t_start"] <= self.cutoff:
                lab = g["label"]
        if lab:
            return lab
        y, w, _ = datetime.fromtimestamp(self.cutoff, timezone.utc).isocalendar()
        return f"week:{y}-W{w:02d}"


# ---------- strategies ----------

def _orig_long(rows):
    return [r for r in rows if r["original"] and not r["dup"] and r["direction"] == "LONG"]


def _conflict(view: CutoffView, key, pol) -> bool:
    since = view.cutoff - pol["conflict_window_s"] - 7 * 86400
    rows = view.posts_on(key, since)
    return any(r["original"] and r["direction"] in ("SHORT", "EXIT") and r["published_at"] >= view.cutoff - pol["conflict_window_s"] for r in rows)


def _decide(strategy: str, view: CutoffView, key, params: dict, pol: dict, new: list[dict]):
    """(inputs, None) for a signal, (None, reason) when suppressed, (None, None) when the condition is not met."""
    c = view.cutoff
    if strategy == "INDIVIDUAL":
        fresh = [r for r in _orig_long(new) if r["key"] == key and r["_avail"] - r["published_at"] <= params["max_capture_lag_s"]]
        if not fresh:
            return None, None
        if _conflict(view, key, pol):
            return None, "CONFLICTING_DIRECTION"
        return [fresh[0]], None
    if strategy == "CONVERGENCE":
        rows = [r for r in _orig_long(view.posts_on(key, c - params["window_s"] - 7 * 86400)) if r["published_at"] >= c - params["window_s"]]
        first: dict[str, dict] = {}
        for r in rows:
            first.setdefault(r["group"], r)
        if len(first) < params["min_sources"]:
            return None, None
        if _conflict(view, key, pol):
            return None, "CONFLICTING_DIRECTION"
        return sorted(first.values(), key=lambda r: (r["_avail"], r["rid"])), None
    if strategy == "SOCIAL_WALLET":
        rows = [r for r in _orig_long(view.posts_on(key, c - pol["social_window_s"] - 7 * 86400)) if r["published_at"] >= c - pol["social_window_s"]]
        first: dict[str, dict] = {}
        for r in rows:
            first.setdefault(r["group"], r)
        if len(first) < params["min_sources"]:
            return None, None
        wev = [w for w in view.wallet_on(key, c - params["wallet_window_s"] - 7 * 86400)
               if w["linkage"] in pol["accepted_linkage"] and c - params["wallet_window_s"] <= w["block_time"] <= c]
        buys = [w for w in wev if w["side"] == "BUY"]
        if not buys:
            return None, None
        posters = {r["source_id"] for r in rows}
        if any(w["side"] == "SELL" and w["source_id"] in posters for w in wev):
            return None, "LINKED_WALLET_SOLD"
        if _conflict(view, key, pol):
            return None, "CONFLICTING_DIRECTION"
        return sorted(list(first.values()) + buys[:1], key=lambda r: (r["_avail"], r["rid"])), None
    if strategy == "TRENDING":
        since = c - params["window_s"]
        ment = view.posts_on(key, since)
        lists = [t for t in view.trending_on(key, since) if t["rank"] is not None and t["rank"] <= params["max_rank"]]
        if len(ment) >= params["min_mentions"]:
            return ment[-params["min_mentions"]:], None
        if lists:
            return [lists[-1]], None
        return None, None
    raise ReplayError(f"unknown strategy {strategy}")


def config_id(strategy: str, params: dict) -> str:
    return strategy + ":" + ",".join(f"{k}={params[k]}" for k in sorted(params))


def generate(data: Data, strategy: str, params: dict, pol: dict, audit: Audit, view_cls=CutoffView) -> dict:
    """Walk the cutoff clock over every moment new social, wallet or trending evidence arrived. Deterministic."""
    events = [("post", r) for r in data.posts if r["key"]]
    if strategy == "SOCIAL_WALLET":
        events += [("wallet", r) for r in data.wallet]
    if strategy == "TRENDING":
        events += [("trending", r) for r in data.trending]
    events.sort(key=lambda e: (e[1]["_avail"], e[1]["rid"]))
    signals, suppressed, last = [], [], {}
    i = 0
    while i < len(events):
        c = events[i][1]["_avail"]
        batch = []
        while i < len(events) and events[i][1]["_avail"] == c:
            batch.append(events[i][1])
            i += 1
        view = view_cls(data, c, audit)
        new_posts = [r for r in batch if r["rid"].startswith("post:")]
        for key in sorted({r["key"] for r in batch}):
            inputs, why = _decide(strategy, view, key, params, pol, new_posts)
            if why:
                suppressed.append({"key": list(key), "decision_t": c, "reason": why})
                continue
            if not inputs:
                continue
            if key in last and c - last[key] < pol["signal_cooldown_s"]:
                continue
            last[key] = c
            fwd = all(x.get("captured_at") is not None and x["captured_at"] <= c for x in inputs)
            signals.append({"strategy": strategy, "config_id": config_id(strategy, params), "chain": key[0], "contract": key[1],
                            "decision_t": c, "inputs": sorted(x["rid"] for x in inputs),
                            "inputs_max_avail": max(x["_avail"] for x in inputs), "inputs_forward_captured": fwd,
                            "regime": view.regime(key[0])})
    return {"signals": signals, "suppressed": suppressed}


# ---------- outcomes, controls ----------

def _token_obs(data: Data, key, t_from: float, t_to: float) -> list[dict]:
    lst, ts = data.obs.get(key, []), data.obs_t.get(key, [])
    part = lst[bisect_left(ts, t_from):bisect_right(ts, t_to)]
    status = [o for o in data.status.get(key, []) if not (t_from <= o["t"] <= t_to)]
    return part + status


def outcome(data: Data, key, decision_t: float, h: int, clock: float, pol: dict, cache: dict) -> dict:
    ck = (key, decision_t, h, clock)
    if ck in cache:
        return cache[ck]
    ocp = pol["outcome"]
    ctx = {"signal_id": "replay", "times": {"generated_at": decision_t},
           "assumptions": {"direction": "LONG", "execution_lag_s": ocp["execution_lag_s"], "position_size_usd": ocp["position_size_usd"],
                           "fee_bps_per_side": ocp["fee_bps_per_side"], "slippage_bps_per_side": ocp["slippage_bps_per_side"]},
           "token": {"chain": key[0], "contract": key[1]}, "flags": [], "is_fixture": data.is_fixture}
    t_entry = decision_t + ocp["execution_lag_s"]
    obs = _token_obs(data, key, t_entry - data.maxper.get(key, 0), t_entry + h + ocp["max_exit_wait_s"])
    o = OC.evaluate(ctx, h, obs, [], clock, ocp)
    codes = sorted({r["code"] for r in o["reasons"]})
    net = (o.get("returns") or {}).get("return_net_modeled") if o["status"] == "MEASURED" else None
    delisted = o["status"] == "NON_EXECUTABLE" and "TOKEN_DELISTED_BEFORE_EXIT" in codes
    exc = o.get("excursion") or {}
    res = {"status": o["status"], "codes": codes, "measured": net, "conservative": -1.0 if delisted else net,
           "delisted": delisted, "mae": exc.get("mae_mid") if exc.get("status") == "OK" and o["status"] == "MEASURED" else None,
           "no_history": key not in data.obs}
    cache[ck] = res
    return res


def controls_for(data: Data, key, c: float, pol: dict, audit: Audit, view_cls=CutoffView) -> tuple[list, str | None]:
    view = view_cls(data, c, audit)
    me = view.market(key)
    if me["liq"] is None or me["liq"] <= 0:
        return [], "SIGNAL_LIQUIDITY_UNKNOWN_AT_DECISION"
    touched = {r["key"] for r in view.posts_since(c - pol["control_exclusion_lookback_s"]) if r["key"]}
    touched |= {r["key"] for r in view.trending_since(c - pol["control_trending_lookback_s"])}
    cands = []
    for k in view.chain_tokens(key[0]):
        if k == key or k in touched or view.delisted(k):
            continue
        m = view.market(k)
        if m["price"] is None or m["price_t"] < c - pol["control_price_max_age_s"] or not m["liq"] or m["liq"] <= 0:
            continue
        lr = abs(math.log(m["liq"] / me["liq"]))
        if lr > math.log(pol["liq_band_ratio"]):
            continue
        dist = lr
        if me["mcap"] and m["mcap"]:
            mr = abs(math.log(m["mcap"] / me["mcap"]))
            if mr > math.log(pol["mcap_band_ratio"]):
                continue
            dist += 0.5 * mr
        cands.append((dist, k))
    cands.sort()
    chosen = [k for _d, k in cands[: pol["control_max"]]]
    if len(chosen) < pol["control_min"]:
        return chosen, "NO_VALID_CONTROLS"
    return chosen, None


# ---------- splits and the label gate ----------

def split_bounds(data: Data, pol: dict) -> dict:
    t0, t1 = data.t_start, data.as_of
    if t0 is None or t1 <= t0:
        return {"start": t0, "end": t1, "train_end": None, "validation_end": None, "empty": True}
    f = pol["split_fractions"]
    span = t1 - t0
    return {"start": t0, "end": t1, "train_end": t0 + f[0] * span, "validation_end": t0 + (f[0] + f[1]) * span, "empty": False}


def split_of(t: float, b: dict) -> str | None:
    if b["empty"]:
        return None
    return "train" if t < b["train_end"] else ("validation" if t < b["validation_end"] else "test")


def label_clock(split: str, b: dict) -> float:
    return {"train": b["train_end"], "validation": b["validation_end"], "test": b["end"]}[split]


class LabelGate:
    """Releases outcome labels by phase: TUNE sees train only, VALIDATE adds validation, TEST needs a frozen configuration."""

    ORDER = {"TUNE": ("train",), "VALIDATE": ("train", "validation"), "TEST": ("train", "validation", "test")}

    def __init__(self):
        self.phase = "TUNE"
        self.frozen_sha = None
        self.log: list[str] = []

    def allow(self, split: str):
        if split not in self.ORDER[self.phase]:
            raise LeakageError(f"{split} labels requested during {self.phase}: held-out outcomes may not inform thresholds")
        if split == "test" and not self.frozen_sha:
            raise LeakageError("test labels requested before the configuration was frozen")

    def freeze(self, chosen: dict):
        self.frozen_sha = sha(chosen)
        self.log.append(f"frozen {self.frozen_sha}")
        self.phase = "VALIDATE"


def samples(data: Data, sigs: list[dict], split: str, b: dict, pol: dict, gate: LabelGate, audit: Audit, cache: dict,
            view_cls=CutoffView) -> list[dict]:
    """Signals of one split with outcomes per horizon (label clock of the split), controls and relative returns."""
    gate.allow(split)
    clock = label_clock(split, b)
    ocp = pol["outcome"]
    out = []
    for s in sigs:
        if split_of(s["decision_t"], b) != split:
            continue
        key = (s["chain"], s["contract"])
        ctrl, why = controls_for(data, key, s["decision_t"], pol, audit, view_cls)
        hz = {}
        for h in pol["horizons_s"]:
            mat = s["decision_t"] + ocp["execution_lag_s"] + h + ocp["max_exit_wait_s"]
            if mat > clock:
                hz[str(h)] = {"state": "PURGED_EMBARGO" if split != "test" else "NOT_MATURED"}
                continue
            o = outcome(data, key, s["decision_t"], h, clock, pol, cache)
            row = {"state": "LABELED", "outcome": o, "relative": {"measured": None, "conservative": None}, "controls": None}
            if why:
                row["control_reason"] = why
            else:
                cvals = {"measured": [], "conservative": []}
                for k in ctrl:
                    co = outcome(data, k, s["decision_t"], h, clock, pol, cache)
                    for lens in cvals:
                        if co[lens] is not None:
                            cvals[lens].append(co[lens])
                row["controls"] = {"chosen": len(ctrl), "measured": len(cvals["measured"]), "conservative": len(cvals["conservative"])}
                for lens, vals in cvals.items():
                    if o[lens] is not None and len(vals) >= pol["control_min"]:
                        row["relative"][lens] = r10(o[lens] - median(vals))
                if row["relative"]["conservative"] is None and o["conservative"] is not None:
                    row["control_reason"] = "TOO_FEW_MEASURED_CONTROLS"
            hz[str(h)] = row
        out.append(dict(s, split=split, horizons=hz))
    return out


# ---------- statistics ----------

def _z(conf: float) -> float:
    return NormalDist().inv_cdf(1 - (1 - conf) / 2)


def summarize(smp: list[dict], h: int, pol: dict, m_tests: int) -> dict:
    k = str(h)
    rows = [s["horizons"][k] for s in smp]
    lab = [r for r in rows if r["state"] == "LABELED"]
    st = {}
    for r in lab:
        st[r["outcome"]["status"]] = st.get(r["outcome"]["status"], 0) + 1
    usable = [r for r in lab if r["outcome"]["conservative"] is not None]
    no_hist = sum(1 for r in lab if r["outcome"]["no_history"])
    ctrl_reasons = {}
    for r in lab:
        if r.get("control_reason") and r["outcome"]["conservative"] is not None:
            ctrl_reasons[r["control_reason"]] = ctrl_reasons.get(r["control_reason"], 0) + 1
    conf = 1 - pol["alpha"] / max(1, m_tests)
    res = {"horizon_s": h, "signals": len(smp), "labeled": len(lab), "purged_or_pending": len(rows) - len(lab),
           "status_counts": dict(sorted(st.items())), "no_price_history": no_hist,
           "non_executable": st.get("NON_EXECUTABLE", 0) - sum(1 for r in lab if r["outcome"]["delisted"]),
           "delisted_total_loss": sum(1 for r in lab if r["outcome"]["delisted"]),
           "coverage": r10(len(usable) / len(lab)) if lab else None,
           "executable_share": r10(1 - (st.get("NON_EXECUTABLE", 0) / len(lab))) if lab else None,
           "no_control_reasons": dict(sorted(ctrl_reasons.items())), "adjusted_confidence": r10(conf), "m_tests": m_tests}
    for lens in ("conservative", "measured"):
        rel = [r["relative"][lens] for r in lab if r["relative"][lens] is not None]
        net = [r["outcome"][lens] for r in lab if r["outcome"][lens] is not None]
        e = {"n_relative": len(rel), "n_net": len(net)}
        if len(rel) >= pol["min_report_n"]:
            ci = median_ci(rel, conf)
            wins = sum(1 for x in rel if x > 0)
            w = wilson(wins, len(rel), _z(conf))
            pos = sorted((x for x in rel if x > 0), reverse=True)
            top_share = (pos[0] / sum(pos)) if pos else None
            mean_all = sum(rel) / len(rel)
            mean_wo = (sum(rel) - max(rel)) / (len(rel) - 1)
            e.update(median_relative=r10(median(rel)), median_relative_ci=None if ci is None else [r10(ci[0]), r10(ci[1])],
                     precision=r10(wins / len(rel)), precision_ci=[r10(w[0]), r10(w[1])],
                     mean_relative=r10(mean_all), mean_relative_without_top=r10(mean_wo),
                     top_outcome_share_of_gains=r10(top_share),
                     dominated=bool((top_share is not None and top_share > pol["dominance_share"])
                                    or (mean_all > 0) != (mean_wo > 0)))
        else:
            e["note"] = f"not shown: {len(rel)} values with matched controls, at least {pol['min_report_n']} needed"
        if len(net) >= pol["min_report_n"]:
            e["median_net"] = r10(median(net))
            e["hit_rate_net_positive"] = r10(sum(1 for x in net if x > 0) / len(net))
        res[lens] = e
    maes = [r["outcome"]["mae"] for r in lab if r["outcome"]["mae"] is not None]
    res["mae"] = {"n": len(maes), "median": r10(median(maes)) if len(maes) >= pol["min_report_n"] else None,
                  "worst": r10(min(maes)) if len(maes) >= pol["min_report_n"] else None}
    toks = {}
    for s in smp:
        if s["horizons"][k]["state"] == "LABELED":
            toks[s["contract"]] = toks.get(s["contract"], 0) + 1
    res["distinct_tokens"] = len(toks)
    res["top_token_share"] = r10(max(toks.values()) / sum(toks.values())) if toks else None
    res["forward_captured_inputs"] = sum(1 for s in smp if s["inputs_forward_captured"])
    regimes = {}
    for s in smp:
        r = s["horizons"][k]
        if r["state"] == "LABELED" and r["relative"]["conservative"] is not None:
            regimes.setdefault(s["regime"], []).append(r["relative"]["conservative"])
    res["by_regime"] = {g: {"n": len(v), "median_relative": r10(median(v)) if len(v) >= pol["min_report_n"] else None}
                        for g, v in sorted(regimes.items())}
    return res


def verdict(test: dict, val: dict, pol: dict, survivorship_risk: list[str]) -> dict:
    c = test["conservative"]
    reasons = []
    if test["signals"] == 0:
        return {"verdict": "INSUFFICIENT_DATA", "reasons": ["no eligible signal in the test window"]}
    if test["labeled"] == 0:
        return {"verdict": "INSUFFICIENT_DATA", "reasons": ["no test signal has a matured outcome window inside the data"]}
    if test["coverage"] is None or test["coverage"] < pol["min_coverage"]:
        return {"verdict": "INSUFFICIENT_DATA", "reasons": [f"price coverage {test['coverage']} of matured test signals is below {pol['min_coverage']}"]}
    if c["n_relative"] < pol["min_test_n"]:
        return {"verdict": "INSUFFICIENT_SAMPLE", "reasons": [f"{c['n_relative']} test signals with matched controls; {pol['min_test_n']} needed"]}
    ci = c.get("median_relative_ci")
    if survivorship_risk:
        reasons += survivorship_risk
    if ci is None:
        reasons.append("no interval at this sample size")
    elif ci[0] <= 0 <= ci[1]:
        reasons.append("the adjusted interval of the median relative return includes zero: not distinguishable from matched controls")
    if c.get("dominated"):
        reasons.append("one outcome dominates the gains")
    vc = val["conservative"]
    if vc.get("median_relative") is None:
        reasons.append("validation split too small to confirm the sign")
    elif (vc["median_relative"] > 0) != (c["median_relative"] > 0):
        reasons.append("validation and test disagree in sign")
    if reasons:
        return {"verdict": "CANNOT_VALIDATE_YET", "reasons": reasons}
    return {"verdict": "BETTER_THAN_CONTROLS_IN_REPLAY" if c["median_relative"] > 0 else "WORSE_THAN_CONTROLS_IN_REPLAY",
            "reasons": ["adjusted interval excludes zero, validation agrees in sign, no single outcome dominates"]}


def survivorship(data: Data, sigs: list[dict]) -> list[str]:
    out = []
    uni = (data.coverage or {}).get("universe") or {}
    if uni.get("includes_delisted") is not True:
        out.append("the token universe is not declared to include delisted tokens: survivorship bias cannot be ruled out")
    keys = {(s["chain"], s["contract"]) for s in sigs}
    missing = [k for k in keys if k not in data.obs]
    if keys and len(missing) / len(keys) > 0.1:
        out.append(f"{len(missing)} of {len(keys)} signalled tokens have no price history: losers may be missing from the data")
    return out


# ---------- the whole run ----------

def tune(data, sigs_by_cfg, strategy, b, pol, gate, audit, cache, view_cls=CutoffView) -> dict:
    h = pol["primary_horizon_s"]
    rows = []
    for params in pol["grid"][strategy]:
        cid = config_id(strategy, params)
        smp = samples(data, sigs_by_cfg[cid], "train", b, pol, gate, audit, cache, view_cls)
        rel = [s["horizons"][str(h)]["relative"]["conservative"] for s in smp
               if s["horizons"][str(h)]["state"] == "LABELED" and s["horizons"][str(h)]["relative"]["conservative"] is not None]
        rows.append({"config_id": cid, "params": params, "train_signals": len(smp), "train_n": len(rel),
                     "train_purged": sum(1 for s in smp if s["horizons"][str(h)]["state"] != "LABELED"),
                     "train_median_relative": r10(median(rel)) if len(rel) >= pol["min_tune_n"] else None})
    elig = [r for r in rows if r["train_median_relative"] is not None]
    if elig:
        best = max(elig, key=lambda r: (r["train_median_relative"], -rows.index(r)))
        basis = "highest train median relative return (conservative lens) among configurations with enough train values"
    else:
        best = rows[0]
        basis = f"no configuration had {pol['min_tune_n']} train values: the first (default) configuration is used, untuned"
    return {"configs": rows, "chosen": best["config_id"], "chosen_params": best["params"], "basis": basis}


def run(doc: dict, policy: dict | None = None, *, view_cls=CutoffView, audit: Audit | None = None) -> dict:
    pol = make_policy(policy)
    data = prepare(doc, pol)
    audit = audit or Audit()
    b = split_bounds(data, pol)
    sigs_by_cfg, supp_by_cfg = {}, {}
    for s in STRATEGIES:
        for params in pol["grid"][s]:
            g = generate(data, s, params, pol, audit, view_cls)
            sigs_by_cfg[config_id(s, params)] = g["signals"]
            supp_by_cfg[config_id(s, params)] = g["suppressed"]
    gate = LabelGate()
    cache: dict = {}
    m_tests = len(STRATEGIES) * len(pol["horizons_s"])
    res = {"engine_version": ENGINE_VERSION, "rules_version": RULES_VERSION, "label": data.label, "is_fixture": data.is_fixture,
           "usable_as_evidence": not data.is_fixture, "policy_sha256": pol["policy_sha256"], "input_sha256": data.input_sha256,
           "coverage": data.coverage, "coverage_version": (data.coverage or {}).get("version"), "as_of": data.as_of,
           "counts": data.counts, "excluded": {k: dict(sorted(v.items())) for k, v in sorted(data.excluded.items())},
           "splits": b, "strategies": {}, "order_of_operations": [], "configs_tried": sum(len(v) for v in pol["grid"].values()),
           "m_tests": m_tests, "primary_horizon_s": pol["primary_horizon_s"], "trade_execution_impact": "none"}
    if b["empty"]:
        for s in STRATEGIES:
            res["strategies"][s] = {"description": STRATEGY_TEXT[s], "verdict": {"verdict": "INSUFFICIENT_DATA",
                                    "reasons": ["no social, wallet or trending evidence with a usable availability time"]}}
        res["audit"] = {"accesses": audit.accesses, "records_checked": audit.records, "violations": 0}
        res["result_sha256"] = sha(res)
        return res
    chosen = {}
    for s in STRATEGIES:
        res["strategies"][s] = {"description": STRATEGY_TEXT[s], "tuning": tune(data, sigs_by_cfg, s, b, pol, gate, audit, cache, view_cls)}
        chosen[s] = res["strategies"][s]["tuning"]["chosen"]
    res["order_of_operations"].append(f"1. thresholds chosen on train labels only (label clock {iso(b['train_end'])}); validation and test labels locked")
    gate.freeze(chosen)
    res["frozen_config_sha256"] = gate.frozen_sha
    res["order_of_operations"].append(f"2. configuration frozen: sha256 {gate.frozen_sha}")
    vals = {s: samples(data, sigs_by_cfg[chosen[s]], "validation", b, pol, gate, audit, cache, view_cls) for s in STRATEGIES}
    res["order_of_operations"].append(f"3. validation evaluated with the frozen configuration (label clock {iso(b['validation_end'])})")
    gate.phase = "TEST"
    tests = {s: samples(data, sigs_by_cfg[chosen[s]], "test", b, pol, gate, audit, cache, view_cls) for s in STRATEGIES}
    res["order_of_operations"].append(f"4. test evaluated once (label clock {iso(b['end'])})")
    for s in STRATEGIES:
        sig = sigs_by_cfg[chosen[s]]
        e = res["strategies"][s]
        e["signals_by_split"] = {sp: sum(1 for x in sig if split_of(x["decision_t"], b) == sp) for sp in SPLITS}
        e["suppressed"] = _count([x["reason"] for x in supp_by_cfg[chosen[s]]])
        e["validation"] = {str(h): summarize(vals[s], h, pol, m_tests) for h in pol["horizons_s"]}
        e["test"] = {str(h): summarize(tests[s], h, pol, m_tests) for h in pol["horizons_s"]}
        e["survivorship"] = survivorship(data, sig)
        ph = str(pol["primary_horizon_s"])
        e["verdict"] = verdict(e["test"][ph], e["validation"][ph], pol, e["survivorship"])
        e["signals_sha256"] = sha(sig)
    res["audit"] = {"accesses": audit.accesses, "records_checked": audit.records, "violations": 0}
    res["result_sha256"] = sha(res)
    return res


def _count(xs):
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items()))


# ---------- leakage proof: truncation invariance ----------

def truncate(doc: dict, T: float, pol: dict) -> dict:
    """The dataset as it existed at T: every record whose availability is after T is removed, and the data clock ends at T."""
    out = copy.deepcopy(doc)
    out["as_of"] = T
    lag = {k: (v or {}).get("publication_lag_s") for k, v in ((doc.get("coverage") or {}).get("providers") or {}).items()}

    def cav(c):
        if _num(c.get("available_at")):
            return c["available_at"]
        lg = lag.get(str(c.get("provider")))
        return c["t"] + c["period_s"] + lg if _num(lg) and _num(c.get("t")) and isinstance(c.get("period_s"), int) else float("inf")

    out["posts"] = [p for p in doc.get("posts") or [] if _num(p.get("available_at")) and p["available_at"] <= T]
    out["wallet_events"] = [w for w in doc.get("wallet_events") or [] if _num(w.get("available_at")) and w["available_at"] <= T]
    out["trending"] = [t for t in doc.get("trending") or [] if _num(t.get("available_at")) and t["available_at"] <= T]
    out["candles"] = [c for c in doc.get("candles") or [] if cav(c) <= T]
    out["points"] = [p for p in doc.get("points") or [] if _num(p.get("available_at")) and p["available_at"] <= T]
    toks = []
    for t in doc.get("tokens") or []:
        t = dict(t)
        da = t.get("delisted_available_at", t.get("delisted_at"))
        if _num(da) and da > T:
            t.pop("delisted_at", None)
            t.pop("delisted_available_at", None)
        toks.append(t)
    out["tokens"] = toks
    out["regimes"] = [g for g in doc.get("regimes") or [] if _num(g.get("available_at")) and g["available_at"] <= T]
    return out


def leakage_check(doc: dict, policy: dict | None = None, *, view_cls=CutoffView, audit: Audit | None = None) -> dict:
    """Signals decided at or before T, and the thresholds tuned on train, must be identical whether or not the data after T exist.
    A harness that read future evidence produces a difference here."""
    pol = make_policy(policy)
    full = prepare(doc, pol)
    b = split_bounds(full, pol)
    audit = audit or Audit()
    checks = []
    if b["empty"]:
        return {"checks": [], "ok": True, "note": "no decision points: nothing to check"}
    full_sig = {config_id(s, p): generate(full, s, p, pol, audit, view_cls)["signals"] for s in STRATEGIES for p in pol["grid"][s]}
    cut_train = None
    for name, T in (("train boundary", b["train_end"]), ("validation boundary", b["validation_end"])):
        cut = prepare(truncate(doc, T, pol), pol)
        if cut_train is None:
            cut_train = cut
        diff = []
        for s in STRATEGIES:
            for params in pol["grid"][s]:
                a = [x for x in full_sig[config_id(s, params)] if x["decision_t"] <= T]
                c = [x for x in generate(cut, s, params, pol, audit, view_cls)["signals"] if x["decision_t"] <= T]
                if sha(a) != sha(c):
                    diff.append(config_id(s, params))
        checks.append({"boundary": name, "T": T, "configs_compared": sum(len(v) for v in pol["grid"].values()), "differences": diff})
    # thresholds: tuning on the full data and on the data truncated at the train boundary must choose the same configuration
    cut = cut_train
    bc = dict(b)   # same boundaries: the truncated data cannot move them (they come from the full span by policy)
    tuned = {}
    for label, dd in (("full", full), ("truncated", cut)):
        sig = full_sig if dd is full else {config_id(s, p): generate(dd, s, p, pol, audit, view_cls)["signals"] for s in STRATEGIES for p in pol["grid"][s]}
        gate, cache = LabelGate(), {}
        tuned[label] = {s: tune(dd, sig, s, bc, pol, gate, audit, cache, view_cls)["configs"] for s in STRATEGIES}
    checks.append({"boundary": "tuning", "T": b["train_end"], "differences": [] if sha(tuned["full"]) == sha(tuned["truncated"]) else ["TRAIN_METRICS_CHANGED"]})
    return {"checks": checks, "ok": all(not c["differences"] for c in checks)}


# ---------- plain-English report ----------

def _pct(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _ci(ci):
    return "none" if not ci else f"[{_pct(ci[0])}, {_pct(ci[1])}]"


def render(res: dict, *, leak: dict | None = None, watermark: str | None = None) -> str:
    L = []
    title = "Historical replay of research signals against matched controls"
    L += [f"# {title}", ""]
    if watermark:
        L += [watermark, ""]
    b = res["splits"]
    fwd = sum(res["strategies"][s].get("test", {}).get(str(pol_h(res)), {}).get("forward_captured_inputs", 0) for s in STRATEGIES) if not b["empty"] else 0
    L += ["What kind of evidence this is: a historical replay (backtest) on stored data, run with a causal cutoff clock. "
          "It is not a forward test. Signals whose inputs the lab actually captured at decision time are counted separately "
          f"(test split, primary horizon: {fwd}); outcome prices are provider history in every case. "
          "Positions are hypothetical (Phase 16 evaluation size); nothing here is a trade instruction.", ""]
    L += ["## Data and coverage", "",
          f"label {res['label']}; fixture: {'yes' if res['is_fixture'] else 'no'}; coverage version {res.get('coverage_version')}; "
          f"engine {res['engine_version']}, rules {res['rules_version']}", "",
          f"data clock ends {iso(res['as_of'])}; input sha256 {res['input_sha256'][:16]}; policy sha256 {res['policy_sha256'][:16]}", "", "```"]
    c = res["counts"]
    L.append(f"posts {c.get('posts', 0)} (reposts {c.get('posts_reposts', 0)}, content duplicates {c.get('posts_content_duplicates', 0)}), "
             f"wallet events {c.get('wallet_events', 0)}, trending entries {c.get('trending', 0)}")
    L.append(f"market observations {c.get('observations', 0)} on {c.get('tokens_with_prices', 0)} tokens; tokens known {c.get('tokens', 0)}")
    for kind, rs in res["excluded"].items():
        L.append(f"excluded {kind}: " + ", ".join(f"{k} x{n}" for k, n in rs.items()))
    uni = (res.get("coverage") or {}).get("universe") or {}
    L.append(f"universe: {uni.get('basis', 'not declared')}; includes delisted tokens: {uni.get('includes_delisted', 'not declared')}")
    for name, p in sorted(((res.get("coverage") or {}).get("providers") or {}).items()):
        L.append(f"provider {name}: kind {p.get('kind')}, publication lag {p.get('publication_lag_s')} s, window {iso(p.get('window', [None])[0]) if p.get('window') else 'n/a'} to "
                 f"{iso(p.get('window', [None, None])[1]) if p.get('window') else 'n/a'}")
    L += ["```", ""]
    if b["empty"]:
        L += ["## Result", "", "INSUFFICIENT_DATA for all four strategies: no social, wallet or trending evidence with a usable availability time. "
              "Nothing was estimated and nothing is extrapolated.", ""]
        L += _leak_lines(leak) + ["## Audit", "", f"cutoff accesses {res['audit']['accesses']}, records checked {res['audit']['records_checked']}, violations 0", ""]
        if watermark:
            L += [watermark, ""]
        return "\n".join(L) + "\n"
    L += ["## Chronological splits", "", "```",
          f"train       {iso(b['start'])} to {iso(b['train_end'])}   labels as known at {iso(b['train_end'])}",
          f"validation  {iso(b['train_end'])} to {iso(b['validation_end'])}   labels as known at {iso(b['validation_end'])}",
          f"test        {iso(b['validation_end'])} to {iso(b['end'])}   labels as known at {iso(b['end'])}",
          "embargo: a sample whose outcome window crosses its split boundary is purged, never moved",
          f"decision evidence spans {(b['end'] - b['start']) / 3600:.1f} h; the primary horizon needs {pol_h(res) / 3600:.0f} h plus lag and exit wait inside a split",
          "```", "", "Order of operations:", ""]
    L += [f"- {x}" for x in res["order_of_operations"]] + [""]
    L += ["## Tuning (train split only)", "", f"configurations tried: {res['configs_tried']}. Held-out splits were not used to choose any threshold.", "", "```"]
    for s in STRATEGIES:
        t = res["strategies"][s]["tuning"]
        for r in t["configs"]:
            mark = "*" if r["config_id"] == t["chosen"] else " "
            med = "n<" + str(DEFAULT_POLICY["min_tune_n"]) if r["train_median_relative"] is None else _pct(r["train_median_relative"])
            L.append(f"{mark} {r['config_id']:<56} train signals {r['train_signals']:>4}  purged {r['train_purged']:>4}  with controls {r['train_n']:>4}  median rel {med}")
    L += ["```", "", "`*` chosen. Basis: " + "; ".join(f"{s} {res['strategies'][s]['tuning']['basis']}" for s in STRATEGIES) + ".", ""]
    ph = str(pol_h(res))
    m = res["m_tests"]
    L += [f"## Results at the primary horizon ({OC.hname(pol_h(res))}), conservative lens", "",
          f"Intervals are adjusted for {m} comparisons (4 strategies x {m // 4} horizons, Bonferroni). Relative = signal net modeled "
          "return minus the median of matched controls at the same decision time. Precision = share of signals that beat their controls. "
          "Estimates below the reporting minimum are not shown.", "", "```"]
    for s in STRATEGIES:
        e = res["strategies"][s]
        for sp in ("validation", "test"):
            x = e[sp][ph]
            cc = x["conservative"]
            cov = "n/a" if x["coverage"] is None else format(x["coverage"], ".0%")
            exe = "n/a" if x["executable_share"] is None else format(x["executable_share"], ".0%")
            L.append(f"{s:<13} {sp:<10} signals {x['signals']:>4} labeled {x['labeled']:>4} coverage {cov:>4} "
                     f"with controls {cc['n_relative']:>4} executable {exe:>4} inputs captured live {x['forward_captured_inputs']}/{x['signals']}")
            if cc.get("median_relative") is not None:
                L.append(f"{'':<24} median rel {_pct(cc['median_relative'])} CI {_ci(cc['median_relative_ci'])}  precision {cc['precision']:.0%} "
                         f"CI [{cc['precision_ci'][0]:.0%}, {cc['precision_ci'][1]:.0%}]  mean {_pct(cc['mean_relative'])} without top {_pct(cc['mean_relative_without_top'])}"
                         + ("  DOMINATED BY ONE OUTCOME" if cc["dominated"] else ""))
                L.append(f"{'':<24} median net {_pct(cc.get('median_net'))}  measured-only median rel {_pct(x['measured'].get('median_relative'))}  "
                         f"MAE median {_pct(x['mae']['median'])} worst {_pct(x['mae']['worst'])}  delisted {x['delisted_total_loss']}  non-exec {x['non_executable']}")
            else:
                L.append(f"{'':<24} {cc['note']}")
            if x["no_control_reasons"]:
                L.append(f"{'':<24} no relative return: " + ", ".join(f"{k} x{n}" for k, n in x["no_control_reasons"].items()))
    L += ["```", "", "## Verdicts", ""]
    for s in STRATEGIES:
        v = res["strategies"][s]["verdict"]
        L.append(f"- {STRATEGY_TEXT[s]}: **{v['verdict']}**. " + " ".join(r[0].upper() + r[1:] + "." for r in v["reasons"]))
    L += ["", "Test minus trending baseline (descriptive only, not a test): " + _vs_baseline(res, ph), ""]
    L += ["## Secondary horizons (exploratory, test split)", "", "```"]
    for s in STRATEGIES:
        parts = []
        for h, x in res["strategies"][s]["test"].items():
            cc = x["conservative"]
            parts.append(f"{OC.hname(int(h))} n={cc['n_relative']} " + (_pct(cc["median_relative"]) if cc.get("median_relative") is not None else "-"))
        L.append(f"{s:<13} " + " | ".join(parts))
    L += ["```", "", "## Bias and caveats", ""]
    for s in STRATEGIES:
        e = res["strategies"][s]
        x = e["test"][ph]
        items = []
        if e["survivorship"]:
            items += e["survivorship"]
        if e["suppressed"]:
            items.append("suppressed (contradictory evidence): " + ", ".join(f"{k} x{n}" for k, n in e["suppressed"].items()))
        if x["top_token_share"] and x["top_token_share"] > 0.2:
            items.append(f"one token is {x['top_token_share']:.0%} of labeled test signals")
        if x["no_price_history"]:
            items.append(f"{x['no_price_history']} test signals on tokens with no price history (kept as missing, not dropped)")
        L.append(f"- {s}: " + ("; ".join(items) if items else "none flagged"))
    L += ["- Selection: only signals the replay itself generated from stored evidence are evaluated; posts the collectors never saw "
          "cannot be judged, and the collected sources are not a random sample of all sources.",
          f"- Multiple testing: {res['configs_tried']} configurations were tried on train; held-out results are reported for the chosen one only. "
          "Secondary horizons are exploratory.",
          "- Missing prices are never filled in. A delisting before the exit counts as a total loss in the conservative lens for signals and "
          "controls alike; the measured-only lens is shown beside it.", ""]
    L += _leak_lines(leak)
    L += ["## Audit", "", f"cutoff accesses {res['audit']['accesses']}, records checked {res['audit']['records_checked']}, records from after a cutoff 0 "
          "(any would have stopped the run with LeakageError)", "", f"result sha256 {res['result_sha256']}", ""]
    if watermark:
        L += [watermark, ""]
    return "\n".join(L) + "\n"


def pol_h(res) -> int:
    return int(res.get("primary_horizon_s") or 86400)


def _vs_baseline(res, ph):
    base = res["strategies"]["TRENDING"]["test"][ph]["conservative"].get("median_relative")
    out = []
    for s in STRATEGIES[:3]:
        m = res["strategies"][s]["test"][ph]["conservative"].get("median_relative")
        out.append(f"{s} " + ("n/a" if m is None or base is None else _pct(m - base)))
    return "; ".join(out) + ("" if base is not None else " (baseline estimate not available)")


def _leak_lines(leak):
    if leak is None:
        return []
    L = ["## Leakage check (truncation invariance)", "",
         "The replay was repeated on the data as it existed at each boundary (every record available later removed). "
         "Signals decided by then, and the train metrics used for tuning, must not change.", "", "```"]
    for c in leak["checks"]:
        L.append(f"{c['boundary']:<20} at {iso(c['T'])}: " + ("identical" if not c["differences"] else "DIFFERENT: " + ", ".join(c["differences"])))
    L += ["```", "", f"No leakage detected: {'yes' if leak['ok'] else 'NO'}", ""]
    return L

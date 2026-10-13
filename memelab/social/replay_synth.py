"""Phase 17: a synthetic, seeded replay world (invented tokens, sources, posts, wallets, trending lists and prices).

It exists to show the replay mechanics and to prove there is no leakage. It is not evidence about any real token or source.
Everything is generated from a seed with random.Random, so the same spec gives the same document byte for byte.

Planted structure (so the harness has something real to find, and something false to resist):
  - pumps: a token rises over ~24 h and gives back about half over the next 48 h. Before most pumps one to four
    independent sources post LONG (informative posts); before some, a linked wallet buys.
  - noise: uninformative LONG and SHORT posts, reposts and ingest duplicates, uninformative linked-wallet buys.
  - leakage canaries: posts published shortly before a pump but first available only after it. A harness that used the
    publication time instead of availability would look prescient on them.
  - traps: one huge winner, delisted tokens that crash before delisting, illiquid tokens, a source that sells right after
    posting, revised candles published late, quiet tokens that serve as controls.
"""
from __future__ import annotations

import math
import random

DEFAULT_SPEC = {
    "seed": 17,
    "start": 1785542400.0,          # 2026-08-01T00:00:00Z
    "days": 30,
    "period_s": 900,
    "publication_lag_s": 120,
    "social_tokens": {"solana": 22, "base": 5},
    "quiet_tokens": {"solana": 40, "base": 12},
    "illiquid_tokens": 4,
    "delisted_tokens": 4,
    "late_listed_tokens": 6,
    "sources": 14,
    "pumps": 150,
    "informative_share": 0.8,
    "noise_posts": 420,
    "short_share": 0.15,
    "repost_rate": 1.2,
    "wallet_confirm_share": 0.45,
    "noise_buys": 60,
    "canaries": 10,
    "sell_after_post": 3,
    "huge_winner_gain": 40.0,
    "revised_candles": 6,
    "trending_every_s": 21600,
}


def _addr(rng: random.Random, chain: str) -> str:
    if chain == "solana":
        alpha = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return "".join(rng.choice(alpha) for _ in range(40)) + "FXRP"
    return "0x" + "".join(rng.choice("0123456789abcdef") for _ in range(36)) + "f17e"


def build(spec: dict | None = None) -> dict:
    sp = dict(DEFAULT_SPEC, **(spec or {}))
    rng = random.Random(sp["seed"])
    t0, P = float(sp["start"]), int(sp["period_s"])
    n_bars = int(sp["days"] * 86400 // P)
    t_end = t0 + n_bars * P
    lag = sp["publication_lag_s"]

    # tokens
    toks = []
    for kind in ("social", "quiet"):
        for chain, n in sp[f"{kind}_tokens"].items():
            for _ in range(n):
                liq = 10 ** rng.uniform(4.3, 6.3)
                toks.append({"chain": chain, "contract": _addr(rng, chain), "kind": kind, "liq": liq,
                             "price": liq * rng.uniform(4, 15) / 1e9, "supply": 1e9, "listed_bar": 0, "delist_bar": None})
    social = [t for t in toks if t["kind"] == "social"]
    for t in rng.sample(social, sp["illiquid_tokens"]):
        t["liq"] = rng.uniform(1500, 6000)
    pool = [t for t in social if t["liq"] > 8000]
    for t in rng.sample(pool, sp["delisted_tokens"]):
        t["delist_bar"] = rng.randrange(n_bars // 3, n_bars - 96)
    for t in rng.sample([t for t in toks if t["delist_bar"] is None], sp["late_listed_tokens"]):
        t["listed_bar"] = rng.randrange(96, n_bars // 2)

    # pumps (bar index, gain); the huge winner is the first pump
    pumps = []
    for i in range(sp["pumps"]):
        t = rng.choice(social)
        lo = t["listed_bar"] + 96
        hi = (t["delist_bar"] - 192) if t["delist_bar"] else n_bars - 40
        if hi <= lo:
            continue
        gain = sp["huge_winner_gain"] if i == 0 else rng.uniform(0.25, 1.6)
        pumps.append({"tok": t, "bar": rng.randrange(lo, hi), "gain": gain})

    # prices: log random walk with a slight bleed, plus pump shapes
    sigma, drift = 0.012, -0.00012
    candles = []
    for t in toks:
        extra = [0.0] * (n_bars + 1)
        for p in pumps:
            if p["tok"] is not t:
                continue
            g = math.log1p(p["gain"])
            for j in range(0, 288):
                b = p["bar"] + j
                if b > n_bars:
                    break
                if j < 96:
                    extra[b] += g * (j + 1) / 96
                else:
                    extra[b] += g * (1 - 0.5 * (j - 95) / 192)
        logp, base = math.log(t["price"]), 0.0
        last = None
        end_bar = t["delist_bar"] if t["delist_bar"] else n_bars
        for b in range(t["listed_bar"], end_bar):
            base += drift + rng.gauss(0, sigma)
            if t["delist_bar"] and b >= t["delist_bar"] - 48:
                base -= 0.06
            lp = logp + base + extra[b]
            o = last if last is not None else math.exp(lp)
            c = math.exp(lp + rng.gauss(0, sigma / 2))
            h = max(o, c) * (1 + abs(rng.gauss(0, sigma / 2)))
            lw = min(o, c) * (1 - abs(rng.gauss(0, sigma / 2)))
            liq = t["liq"] * (0.2 if t["delist_bar"] and b >= t["delist_bar"] - 48 else 1.0) * math.exp(rng.gauss(0, 0.02))
            candles.append({"chain": t["chain"], "contract": t["contract"], "provider": "synth-candles", "period_s": P,
                            "t": t0 + b * P, "o": o, "h": h, "l": lw, "c": c, "liq": round(liq, 2),
                            "mcap": round(c * t["supply"], 2)})
            last = c
    # revised candles: the provider republished a corrected close later (both versions exist; the later one wins once available)
    for c in rng.sample(candles, sp["revised_candles"]):
        r = dict(c, c=c["c"] * 1.03, h=max(c["h"], c["c"] * 1.03), available_at=c["t"] + P + lag + 6 * 3600)
        candles.append(r)

    # sources: independence groups (some sources share an operator)
    srcs = [{"source_id": f"src{i:02d}", "independence_group": f"grp{i:02d}"} for i in range(sp["sources"])]
    for a, g in ((1, "grp00"), (3, "grp02"), (5, "grp04"), (6, "grp04")):
        srcs[a]["independence_group"] = g
    groups: dict[str, list[str]] = {}
    for s in srcs:
        groups.setdefault(s["independence_group"], []).append(s["source_id"])
    linked = [s["source_id"] for s in srcs[:5]]
    disputed = [s["source_id"] for s in srcs[5:7]]

    posts, wallets = [], []
    pid = [0]

    def post(src, tok, direction, pub, avail, **kw):
        pid[0] += 1
        p = {"post_id": f"p{pid[0]:05d}", "source_id": src, "chain": tok["chain"], "contract": tok["contract"],
             "direction": direction, "published_at": round(pub, 3), "available_at": round(avail, 3), "provider": "synth-social"}
        if rng.random() < 0.7:
            p["captured_at"] = p["available_at"]
        p.update(kw)
        posts.append(p)
        return p

    def alive(tok, t):
        b = (t - t0) / P
        return b >= tok["listed_bar"] and (tok["delist_bar"] is None or b < tok["delist_bar"])

    for p in pumps:
        tp = t0 + p["bar"] * P
        if rng.random() < sp["informative_share"]:
            k = rng.choice((1, 2, 2, 3, 3, 4))
            for g in rng.sample(sorted(groups), k):
                pub = tp - rng.uniform(3600, 6 * 3600)
                if alive(p["tok"], pub):
                    post(rng.choice(groups[g]), p["tok"], "LONG", pub, pub + rng.uniform(30, 600))
            if rng.random() < sp["wallet_confirm_share"]:
                bt = tp - rng.uniform(1800, 4 * 3600)
                wallets.append({"event_id": f"w{len(wallets):04d}", "source_id": rng.choice(linked), "linkage": "SELF_CLAIMED",
                                "chain": p["tok"]["chain"], "contract": p["tok"]["contract"], "side": "BUY", "block_time": round(bt, 3),
                                "available_at": round(bt + 60, 3), "captured_at": round(bt + 60, 3)})
    for _ in range(sp["noise_posts"]):
        tok = rng.choice(social)
        pub = rng.uniform(t0 + 3600, t_end - 3600)
        if not alive(tok, pub):
            continue
        delayed = rng.random() < 0.06
        post(rng.choice(srcs)["source_id"], tok, "SHORT" if rng.random() < sp["short_share"] else "LONG", pub,
             pub + (rng.uniform(2 * 3600, 12 * 3600) if delayed else rng.uniform(30, 900)))
    # leakage canaries: published before a pump, available only after it
    for p in rng.sample(pumps[1:], sp["canaries"]):
        tp = t0 + p["bar"] * P
        post(rng.choice(srcs)["source_id"], p["tok"], "LONG", tp - 7200, tp + 30 * 3600, canary=True)
    # reposts of originals (raw mentions, never independent) and ingest duplicates of the same post id
    originals = list(posts)
    for o in originals:
        for _ in range(min(6, int(rng.expovariate(1 / sp["repost_rate"])))):
            src = rng.choice([s for s in srcs if s["source_id"] != o["source_id"]])
            pub = o["available_at"] + rng.uniform(60, 6 * 3600)
            if pub < t_end:
                post(src["source_id"], {"chain": o["chain"], "contract": o["contract"]}, o["direction"], pub, pub + rng.uniform(30, 600),
                     repost_of=o["post_id"])
    for o in rng.sample(originals, 10):
        d = dict(o, available_at=round(o["available_at"] + 3600, 3))
        d.pop("captured_at", None)
        posts.append(d)
    # noise buys, disputed links, and sources that sell right after posting LONG
    for _ in range(sp["noise_buys"]):
        tok = rng.choice(social)
        bt = rng.uniform(t0 + 3600, t_end - 3600)
        if alive(tok, bt):
            wallets.append({"event_id": f"w{len(wallets):04d}", "source_id": rng.choice(linked + disputed),
                            "linkage": "SELF_CLAIMED" if rng.random() < 0.7 else "DISPUTED", "chain": tok["chain"],
                            "contract": tok["contract"], "side": "BUY", "block_time": round(bt, 3), "available_at": round(bt + 90, 3)})
    for _ in range(sp["sell_after_post"]):
        tok = rng.choice([t for t in social if t["delist_bar"] is None and t["liq"] > 8000])
        pub = rng.uniform(t0 + 86400, t_end - 3 * 86400)
        src = rng.choice(linked)
        others = [s["source_id"] for s in srcs if s["independence_group"] != dict((x["source_id"], x["independence_group"]) for x in srcs)[src]]
        post(src, tok, "LONG", pub, pub + 120)
        post(rng.choice(others), tok, "LONG", pub + 600, pub + 700)
        wallets.append({"event_id": f"w{len(wallets):04d}", "source_id": src, "linkage": "SELF_CLAIMED", "chain": tok["chain"],
                        "contract": tok["contract"], "side": "BUY", "block_time": round(pub - 1800, 3), "available_at": round(pub - 1700, 3)})
        wallets.append({"event_id": f"w{len(wallets):04d}", "source_id": src, "linkage": "SELF_CLAIMED", "chain": tok["chain"],
                        "contract": tok["contract"], "side": "SELL", "block_time": round(pub + 1800, 3), "available_at": round(pub + 1900, 3)})

    # trending lists: top 10 per chain by trailing 24 h close-to-close move, from candles published by the snapshot time
    closes: dict[tuple, list] = {}
    for c in candles:
        if "available_at" not in c:
            closes.setdefault((c["chain"], c["contract"]), []).append((c["t"] + P, c["c"]))
    for v in closes.values():
        v.sort()
    trending = []
    ts = t0 + 86400
    snap = 0
    while ts < t_end:
        for chain in sorted({t["chain"] for t in toks}):
            mv = []
            for (ch, ct), v in closes.items():
                if ch != chain:
                    continue
                known = [x for x in v if x[0] + lag <= ts]
                if not known or known[-1][0] < ts - 2 * P:
                    continue
                prev = [x for x in known if x[0] <= ts - 86400]
                if prev:
                    mv.append((known[-1][1] / prev[-1][1] - 1, ct))
            mv.sort(reverse=True)
            for r, (_m, ct) in enumerate(mv[:10]):
                trending.append({"snapshot_id": f"tr{snap:04d}", "provider": "synth-trending", "chain": chain, "contract": ct,
                                 "rank": r + 1, "t": ts, "available_at": ts + 60})
            snap += 1
        ts += sp["trending_every_s"]

    tokens = [{"chain": t["chain"], "contract": t["contract"], "listed_at": t0 + t["listed_bar"] * P,
               **({"delisted_at": t0 + t["delist_bar"] * P, "delisted_available_at": t0 + t["delist_bar"] * P + 3600} if t["delist_bar"] else {})}
              for t in toks]
    for c in candles:
        for k in ("o", "h", "l", "c"):
            c[k] = float(f"{c[k]:.8g}")
    return {
        "schema": "memelab.social.replay.input/1", "label": f"synthetic world seed {sp['seed']}", "is_fixture": True,
        "as_of": t_end,
        "coverage": {"version": f"synthetic-{sp['seed']}-v1",
                     "providers": {"synth-candles": {"kind": "PRICE", "publication_lag_s": lag, "window": [t0, t_end]},
                                   "synth-social": {"kind": "SOCIAL", "publication_lag_s": None, "window": [t0, t_end],
                                                    "note": "available_at is the first observation"},
                                   "synth-trending": {"kind": "TRENDING", "publication_lag_s": 60, "window": [t0 + 86400, t_end]}},
                     "universe": {"basis": "every invented token, delisted ones included", "includes_delisted": True, "token_count": len(toks)}},
        "sources": srcs, "tokens": tokens, "posts": posts, "wallet_events": wallets, "trending": trending, "candles": candles,
        "spec": sp,
    }

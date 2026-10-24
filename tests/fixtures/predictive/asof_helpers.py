"""Builders shared by tests/test_predictive_asof_*.py (Phase 05). Synthetic rows only; the real frozen sample is
asof_fixture.json. No network, no clock: every time is passed in."""
from __future__ import annotations

import json

from memelab.predictive import store as S

# real-shaped Solana addresses (32-byte base58), used as opaque identities in synthetic cases
MINT_A = "DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump"
POOL_A = "DQyGMAGx8nB6ykixotLNFC6eVVQjrMqz7AkRyinNkEm1"
MINT_B = "CnPL1xnAVHYGH92FpmiNoNhgh3gctkH5y988hMg4bonk"
POOL_B = "AiUCeZYWNAnZcpWPQPGcpeP3zusPiGUZYorLZkXhMoww"
POOL_A2 = "8BRDx1ky8xuRBYq1kmVJ4TrSNaDybSiLU2mxmLVB4WaW"
T0 = 1791331200.0            # 2026-10-07T00:00:00Z, 5-minute aligned
GT = "https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}/ohlcv/minute?aggregate=5&limit=1000&before_timestamp={b}&currency=usd"


def snap(price=1.0, **kw):
    s = {"t": 0.0, "price": price, "mcap": 1e6, "fdv": 1e6, "liquidity": 5e4, "exit_cap_3pct": 1e3, "holders": 900,
         "adj_top10": 12.5, "cluster_pct": None, "dev_pct": 0.0, "insider_pct": 0, "direction": "NEUTRAL", "vol_24h": 2e5,
         "net_buyers_24h": -4, "structure": "RANGE", "lifecycle": "EARLY", "attention": None, "score": 55, "status": "WATCH",
         "fatal": []}
    s.update(kw)
    return s


def thesis(mint, created_at, *, status="WATCH", score=55, price=1.0, fatal=None, **snapkw):
    return {"id": 1, "mint": mint, "created_at": created_at, "status": status, "score": score,
            "fatal_flags_json": json.dumps(fatal or []), "snapshot_json": json.dumps(snap(price, t=created_at, **snapkw))}


def token(mint, *, chain="solana", pool=None, first_seen_at=None, first_pool_at="2026-10-01T00:00:00Z", symbol="SAME"):
    return {"mint": mint, "chain": chain, "symbol": symbol, "name": symbol, "primary_pool": pool, "graduated_pool": None,
            "first_pool_at": first_pool_at, "first_seen_at": first_seen_at, "last_seen_at": first_seen_at}


def export(commit, t, theses, tokens):
    return {"commit": commit, "commit_time": t, "theses": theses, "tokens": tokens, "blob": "b" + commit,
            "body_sha256": S.sha([commit, theses, tokens]), "body_bytes": 1}


def gt_body(rows, base="So11111111111111111111111111111111111111112", quote="So11111111111111111111111111111111111111112"):
    return json.dumps({"data": {"id": "x", "type": "ohlcv_request_response", "attributes": {"ohlcv_list": rows}},
                       "meta": {"base": {"address": base}, "quote": {"address": quote}}}).encode()


OWNER = {POOL_A: MINT_A, POOL_B: MINT_B}


def candle(start, c=1.0, *, o=None, h=None, l=None, v=100.0):
    o = c if o is None else o
    h = max(o, c) * 1.01 if h is None else h
    l = min(o, c) * 0.99 if l is None else l
    return [int(start), o, h, l, c, v]


def resp(pool, boundary, rows, retrieved_at, status=200, page=0, mint=None, token=True):
    """One vendor read; by default the body names the pool's mint as its base token and the request carries token=<mint>."""
    m = mint or OWNER[pool]
    return {"url": GT.format(pool=pool, b=int(boundary)) + (f"&token={m}" if token else ""),
            "params": {"pool": pool, "before_timestamp": int(boundary), "page": page, "token": m if token else None},
            "retrieved_at": retrieved_at, "http_status": status, "body": gt_body(rows, base=m) if status == 200 else b'{"errors":[]}',
            "boundary_at": boundary, "timeframe": "minute", "aggregate": 5}


def series(con, *, mint, pool, boundary, need_from, keys, status="OK", checked_at, kept=0, last_end=None, sid=None):
    return S.record_series_status(con, chain="solana", mint=mint, pool=pool, series_id=sid or f"{pool}@{int(boundary)}",
                                  boundary_at=boundary, need_from=need_from, status=status, detail=None, response_keys=keys,
                                  calls=len(keys), candles_kept=kept, last_end_at=last_end, checked_at=checked_at, now=checked_at)


D1, D2, D3 = T0 + 86400 + 1234, T0 + 86400 + 7200 + 55, T0 + 2 * 86400 + 600


def world_exports(extra_in_e2=(), extra_tokens_e2=()):
    """The three export versions of small_world, oldest first (optionally with more rows in the second)."""
    d1, d2, d3 = D1, D2, D3
    e1 = export("c1", d1, [thesis(MINT_A, d1 - 900, price=1.0)], [token(MINT_A, pool=POOL_A, first_seen_at=d1 - 400)])
    e2 = export("c2", d2, [thesis(MINT_A, d1 - 900, price=1.0), thesis(MINT_A, d2 - 700, price=1.2, status="REJECTED", score=40,
                                                                        fatal=[{"flag": "X"}]),
                           thesis(MINT_B, d2 - 600, price=0.5)],
                [token(MINT_A, pool=POOL_A, first_seen_at=d1 - 400), token(MINT_B, pool=POOL_B, first_seen_at=d2 - 300)])
    e3 = export("c3", d3, [thesis(MINT_A, d3 - 500, price=0.9), thesis(MINT_A, d2 - 700, price=1.2, status="REJECTED", score=40,
                                                                       fatal=[{"flag": "X"}]),
                           thesis(MINT_B, d2 - 600, price=0.5)],
                [token(MINT_A, pool=POOL_A, first_seen_at=d1 - 400), token(MINT_B, pool=POOL_B, first_seen_at=d2 - 300)])
    e2["theses"] = e2["theses"] + list(extra_in_e2)
    e2["tokens"] = e2["tokens"] + list(extra_tokens_e2)
    return [e1, e2, e3]


def small_world(con, *, retrieved_at=T0 + 30 * 86400, exports=None):
    """Two Solana mints sharing one symbol, each with its own pool; mint A has three decisions, B one. Candles every 5 minutes
    for two days before the last decision on A's pool, a sparse series on B's pool. Returns the decision times."""
    d1, d2, d3 = D1, D2, D3
    S.ingest_exports(con, exports if exports is not None else world_exports(), now=retrieved_at - 10)
    boundary = int(d3)
    rows = [candle(s, c=1.0 + 0.001 * ((s - T0) // 300 % 37)) for s in range(int(T0), boundary, 300) if s + 300 <= boundary]
    rows.reverse()
    r = S.ingest_gt_response(con, resp(POOL_A, boundary, rows[:1000], retrieved_at), chain="solana", mint=MINT_A, pool=POOL_A,
                             now=retrieved_at)
    keys = [r["response_key"]]
    if len(rows) > 1000:
        b2 = rows[999][0]
        r2 = S.ingest_gt_response(con, resp(POOL_A, b2, rows[999:1999], retrieved_at + 11, page=1), chain="solana", mint=MINT_A,
                                  pool=POOL_A, now=retrieved_at + 11)
        keys.append(r2["response_key"])
    series(con, mint=MINT_A, pool=POOL_A, boundary=boundary, need_from=T0, keys=keys, checked_at=retrieved_at + 11,
           kept=len(rows), last_end=boundary)
    bb = int(d2)
    sparse = [candle(T0 + 86400 - 3000, c=0.4), candle(T0 + 3600, c=0.45)]
    r3 = S.ingest_gt_response(con, resp(POOL_B, bb, sparse, retrieved_at + 22), chain="solana", mint=MINT_B, pool=POOL_B,
                              now=retrieved_at + 22)
    series(con, mint=MINT_B, pool=POOL_B, boundary=bb, need_from=T0, keys=[r3["response_key"]], checked_at=retrieved_at + 22,
           kept=2, last_end=T0 + 86400 - 2700)
    con.commit()
    return d1, d2, d3

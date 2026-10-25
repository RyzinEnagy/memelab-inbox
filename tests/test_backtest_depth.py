"""Forward depth collector (D-BT-034): offline tests on recorded GeckoTerminal and Jupiter bodies (live smoke of
2026-10-25, audits/backtesting/collector/). No network: every call goes to a fake http_get on a fake clock."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from memelab.backtest import cli, depth, schema, store

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures" / "backtest" / "depth"
NOW = 1792934400.0                       # 2026-10-25T13:20:00Z

A = "7M3gDRgozcumFsiTeXwjB8cYxpg7Q9R7rH7rkw2Fpump"; A_POOL = "FVq2chsiAcPqwL9L3zafF8juQHb7mui6LWMuE8g5L4K4"
B = "9aqmJjCnnMQv42TXLk921ceUkN35nea2QP969n1caqjj"; B_POOL = "7Nj7mBE7iVmjvnBHNvjgaz6G3ZktTHFNbf7aQDfZ7iNR"
C = "0x3D4F0513e8A29669B960F9dbCA61861548a9A760"; C_POOL = "0x7F51BBF34156ba802deb0e38b7671dc4fa32041d"   # mixed case on purpose
D = "2SESmE4AN8KSKu3MUtF6QJTFC5LT6WzodGW7JMQRyxvP"; D_TOP = "FNBtPfCeGZ1ydcmhxKDt1L1v9C3tmVYPDW8gPcXLeWbi"
E = "0x532f27101965dd16442e59d40670faf5ebb142e4"; E_POOL = "0xba3f945812a83471d709bce9c3ca699a19fb46f7"
F = "0xabc::coin::COIN"
X = "XmismatchXmismatchXmismatchXmismatchXmism"           # names A's pool, which does not hold it
Q = "QsideQsideQsideQsideQsideQsideQsideQsidepump"; Q_POOL = "QsidePoolQsidePoolQsidePoolQsidePoolQsideP"   # the mint is the quote token
P = "PmissPmissPmissPmissPmissPmissPmissPmisspump"; P_POOL = "PmissPoolPmissPoolPmissPoolPmissPoolPmissP"   # not in the vendor's answer
SOL = "So11111111111111111111111111111111111111112"


def _row(mint, created, status="RESEARCH REQUIRED", score=50, rid=1):
    return {"id": rid, "mint": mint, "created_at": created, "status": status, "score": score, "snapshot_json": json.dumps({"price": 1.0})}


def _tok(mint, chain="solana", primary=None, graduated=None):
    return {"mint": mint, "chain": chain, "primary_pool": primary, "graduated_pool": graduated, "decimals": 6}


TOKS = [_tok(A, graduated=A_POOL), _tok(B, graduated=B_POOL), _tok(C, "bsc", primary=C_POOL), _tok(D), _tok(E, "base", primary=E_POOL),
        _tok(F, "sui", primary="0xpool"), _tok(X, graduated=A_POOL), _tok(Q, graduated=Q_POOL), _tok(P, graduated=P_POOL)]
V0 = {"tokens": TOKS[:2], "theses": [_row(A, NOW - 49 * 3600), _row(B, NOW - 49 * 3600, rid=2)]}
V1 = {"tokens": TOKS[:2], "theses": V0["theses"] + [_row(A, NOW - 31 * 3600, rid=3)]}
V2 = {"tokens": TOKS, "theses": V1["theses"] + [
    _row(A, NOW - 4 * 3600, rid=4),                                  # new row of a known mint: a new decision
    _row(B, NOW - 49 * 3600, status="REJECTED", rid=5),              # same key as a baseline row, different content: new
    _row(C, NOW - 4 * 3600, rid=6), _row(D, NOW - 4 * 3600, rid=7), _row(E, NOW - 4 * 3600, rid=8),
    _row(F, NOW - 4 * 3600, rid=9), _row(X, NOW - 4 * 3600, rid=10), _row(Q, NOW - 4 * 3600, rid=12), _row(P, NOW - 4 * 3600, rid=13),
    {"id": 14, "mint": "BadRowBadRowBadRowBadRowBadRowBadRowBadRow", "created_at": "yesterday"}]}   # unreadable row: counted, skipped
V2 = {"tokens": V2["tokens"], "theses": V2["theses"] + [dict(V0["theses"][0], id=99)]}   # same row, other id: not new
V3 = {"tokens": V2["tokens"], "theses": V2["theses"] + [_row(A, NOW - 2 * 3600, status="NEAR ENTRY", rid=11)]}   # a newer A decision


def _repo(tmp_path, versions):
    r = tmp_path / "lab"
    subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True)
    for t, body in versions:
        f = r / "data" / "state" / "latest.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"_tables": body}))
        env = {**os.environ, "GIT_COMMITTER_DATE": f"@{int(t)} +0000", "GIT_AUTHOR_DATE": f"@{int(t)} +0000"}
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "export"], check=True, env=env)
    return r


@pytest.fixture
def exports(tmp_path):
    repo = _repo(tmp_path, [(NOW - 48 * 3600, V0), (NOW - 30 * 3600, V1), (NOW - 3 * 3600, V2), (NOW - 3600, V3)])
    return depth.export_decisions(repo, "refs/heads/main", now=NOW)


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


JUP = {}
for _f in FX.glob("jup_quote_*.json"):
    _j = json.loads(_f.read_bytes())
    JUP[(_j["inputMint"], _j["inAmount"])] = _f.read_bytes()
NO_ROUTE = b'{"error":"Could not find any route","errorCode":"COULD_NOT_FIND_ANY_ROUTE"}'


def _solana_pools() -> dict:
    """The recorded Solana multi-pool body plus one pool where the mint Q is the quote token (built from A's pool with
    the sides swapped), so the quote-side code path is tested on real numbers."""
    d = json.loads((FX / "gt_pools_multi_solana.json").read_bytes())
    a = next(it for it in d["data"] if it["attributes"]["address"] == A_POOL)
    q = json.loads(json.dumps(a))
    at = q["attributes"]
    for f in ("price_usd", "price_native_currency", "balance", "liquidity_usd"):
        at[f"base_token_{f}"], at[f"quote_token_{f}"] = a["attributes"][f"quote_token_{f}"], a["attributes"][f"base_token_{f}"]
    at["address"] = Q_POOL
    q["id"] = f"solana_{Q_POOL}"
    q["relationships"]["base_token"]["data"]["id"] = f"solana_{SOL}"
    q["relationships"]["quote_token"]["data"]["id"] = f"solana_{Q}"
    d["data"].append(q)
    d["included"].append({"id": f"solana_{Q}", "type": "token", "attributes": {"address": Q, "symbol": "Q", "decimals": 6}})
    return d


SOL_POOLS = json.dumps(_solana_pools()).encode()


def fake(clock, jup="ok", gt_fail=None, jup_fail=None, sol_pools=None, quote_hook=None):
    """gt_fail / jup_fail: {call number (1-based): status} to answer with instead of the recorded body."""
    calls = []
    n = {"gt": 0, "jup": 0}

    def get(url):
        start = clock.t
        clock.t += 0.3
        calls.append({"start": start, "end": clock.t, "url": url})
        if url.startswith("https://api.geckoterminal.com/"):
            n["gt"] += 1
            if gt_fail and n["gt"] in gt_fail:
                st = gt_fail[n["gt"]]
                return st, (b"" if st == 0 else b'{"status":"%d"}' % st)
            if "/solana/pools/multi/" in url:
                return 200, sol_pools or SOL_POOLS
            for pat, name in (("/solana/tokens/multi/", "gt_tokens_multi_solana"), ("/bsc/pools/multi/", "gt_pools_multi_bsc"),
                              ("/base/pools/multi/", "gt_pools_multi_base")):
                if pat in url:
                    return 200, (FX / f"{name}.json").read_bytes()
            return 404, b'{"errors":[{"status":"404","title":"Not Found"}]}'
        if url.startswith(depth.JUP_QUOTE):
            n["jup"] += 1
            if jup_fail and n["jup"] in jup_fail:
                st = jup_fail[n["jup"]]
                return st, (b"" if st == 0 else b'{"message":"rate limited"}')
            if jup == "401":
                return 401, b'{"message":"Unauthorized"}'
            if quote_hook:
                r = quote_hook(url)
                if r:
                    return r
            q = parse_qs(urlparse(url).query)
            return (200, JUP[(q["inputMint"][0], q["amount"][0])]) if (q["inputMint"][0], q["amount"][0]) in JUP else (400, NO_ROUTE)
        raise AssertionError("unexpected host " + url)
    get.calls = calls
    return get


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def _run(con, exports, now=NOW, jup="ok", gt_fail=None, jup_fail=None, sol_pools=None, quote_hook=None, **kw):
    clk = Clock(now)
    get = fake(clk, jup, gt_fail, jup_fail, sol_pools, quote_hook)
    out = depth.collect(con, exports=exports, now=now, http_get=get, clock=clk, sleep=clk.sleep, **kw)
    return out, get.calls


def _snaps(con, **where):
    sql = "SELECT * FROM bt_depth_snapshots" + (" WHERE " + " AND ".join(f"{k}=?" for k in where) if where else "") + " ORDER BY id"
    return [dict(r) for r in con.execute(sql, tuple(where.values()))]


# ---------------------------------------------------------------- decisions

def test_export_decisions_baseline_window_and_pool(exports):
    assert exports["status"] == "OK" and exports["exports"] == 4 and exports["rows_unreadable"] == 2   # once per export holding it
    got = sorted((d["mint"], d["status"]) for d in exports["decisions"])
    assert got == sorted([(A, "RESEARCH REQUIRED"), (A, "NEAR ENTRY"), (B, "REJECTED"), (C, "RESEARCH REQUIRED"), (D, "RESEARCH REQUIRED"),
                          (E, "RESEARCH REQUIRED"), (F, "RESEARCH REQUIRED"), (X, "RESEARCH REQUIRED"), (Q, "RESEARCH REQUIRED"), (P, "RESEARCH REQUIRED")])
    by = {(d["mint"], d["status"]): d for d in exports["decisions"]}
    assert by[(A, "NEAR ENTRY")]["export_time"] == NOW - 3600 and by[(B, "REJECTED")]["export_time"] == NOW - 3 * 3600
    assert (by[(A, "RESEARCH REQUIRED")]["pool_address"], by[(A, "RESEARCH REQUIRED")]["pool_source"]) == (A_POOL, "EXPORT_GRADUATED_POOL")
    c = by[(C, "RESEARCH REQUIRED")]
    assert (c["chain"], c["pool_address"], c["pool_source"]) == ("bsc", C_POOL, "EXPORT_PRIMARY_POOL")
    assert by[(D, "RESEARCH REQUIRED")]["pool_source"] == "NONE_IN_EXPORT" and by[(F, "RESEARCH REQUIRED")]["chain"] == "sui"
    assert by[(A, "RESEARCH REQUIRED")]["row_sha256"] == depth.row_sha256(V2["theses"][3])


def test_export_decisions_need_a_baseline(tmp_path):
    repo = _repo(tmp_path, [(NOW - 3600, V2)])
    out = depth.export_decisions(repo, "refs/heads/main", now=NOW)
    assert out["status"] == "NO_BASELINE" and out["decisions"] == []


def test_rows_of_the_oldest_export_read_are_never_new(tmp_path):
    """A shallow history cannot say when the oldest export's rows first appeared, even when that export is recent."""
    repo = _repo(tmp_path, [(NOW - 10 * 3600, V1), (NOW - 2 * 3600, V2)])
    out = depth.export_decisions(repo, "refs/heads/main", now=NOW)
    assert out["baseline_commit"] and sorted(d["mint"] for d in out["decisions"]) == sorted([A, B, C, D, E, F, X, Q, P])
    assert all(d["export_time"] == NOW - 2 * 3600 for d in out["decisions"])


def test_export_after_now_is_not_a_decision(tmp_path):
    repo = _repo(tmp_path, [(NOW - 10 * 3600, V1), (NOW + 3600, V2)])
    assert depth.export_decisions(repo, "refs/heads/main", now=NOW)["decisions"] == []


# ---------------------------------------------------------------- one run

def test_collect_pools_quotes_and_provenance(con, exports):
    out, calls = _run(con, exports)
    dec = {(r["mint"], r["status"]): dict(r) for r in con.execute("SELECT * FROM bt_depth_decisions")}
    assert {m for m, _ in dec} == {A, B, C, D, E, F, X, Q, P}
    assert dec[(F, "RESEARCH REQUIRED")]["pool_source"] == "UNSUPPORTED_CHAIN" and not _snaps(con, mint=F)
    # the vendor's top pool for D, with its lookup kept
    lk = [dict(r) for r in con.execute("SELECT * FROM bt_depth_pool_lookups WHERE mint=?", (D,))]
    assert [(x["state"], x["pool_address"], x["attempt"], x["http_status"]) for x in lk] == [("OK", D_TOP, 1, 200)]
    tok_body = (FX / "gt_tokens_multi_solana.json").read_bytes()
    assert lk[0]["raw_sha256"] == hashlib.sha256(tok_body).hexdigest() and "include=top_pools" in lk[0]["request_url"]
    assert _snaps(con, mint=D, kind="POOL")[0]["pool_address"] == D_TOP
    # pool snapshot: reserves in token units and USD, the mint's side, decimals from the vendor's token record
    p = _snaps(con, mint=A, kind="POOL")[0]
    v = json.loads(p["value_json"])
    assert p["state"] == "OK" and v["side"] == "base" and v["decimals"] == 6 and v["mint_balance"] > 0 and v["other_balance"] > 0
    assert p["reserve_usd"] > 0 and p["price_usd"] > 0
    assert p["decision_id"] == dec[(A, "NEAR ENTRY")]["id"]                         # the newest decision of the pool
    assert p["raw_sha256"] == hashlib.sha256(SOL_POOLS).hexdigest() and (store.RAW_DIR / "geckoterminal" / f"{p['raw_sha256']}.json").read_bytes() == SOL_POOLS
    call = next(c for c in calls if "/solana/pools/multi/" in c["url"])
    assert p["request_url"] == call["url"] and p["captured_at"] == call["end"] and p["since_export_s"] == call["end"] - (NOW - 3600)
    assert "include_composition=true" in p["request_url"] and A_POOL in p["request_url"]
    # quotes: fixed USD sizes, token amount from this run's pool price, proceeds in USDC, the price's source kept
    qs = _snaps(con, mint=A, kind="QUOTE")
    assert [q["size_usd"] for q in qs] == list(depth.SIZES_USD) and all(q["state"] == "OK" for q in qs)
    for q in qs:
        assert int(q["token_amount_raw"]) == math.floor(q["size_usd"] / p["price_usd"] * 10 ** 6) and q["price_usd"] == p["price_usd"]
        j = json.loads((store.RAW_DIR / "jupiter" / f"{q['raw_sha256']}.json").read_bytes())
        assert q["out_usd"] == int(j["outAmount"]) / 1e6 and j["inAmount"] == q["token_amount_raw"]
        assert f"inputMint={A}" in q["request_url"] and f"outputMint={depth.USDC}" in q["request_url"]
        assert "swapMode=ExactIn" in q["request_url"] and "slippageBps=300" in q["request_url"]
        qv = json.loads(q["value_json"])
        assert qv["price_captured_at"] == p["captured_at"] and qv["price_raw_sha256"] == p["raw_sha256"] and qv["price_check"] == "OK"
        assert abs(qv["implied_over_pool_price"] - 1.0) < 0.02
        assert qv["route"] and qv["route"][0]["label"] and qv["route"][0]["amm"]
        qc = next(c for c in calls if c["url"] == q["request_url"])
        assert q["captured_at"] == qc["end"]
    assert qs[-1]["out_usd"] < qs[-1]["size_usd"]              # a bigger sale gets less per dollar
    assert [s["state"] for s in _snaps(con, mint=D, kind="QUOTE")] == ["NO_ROUTE"] * 3
    # a pool that does not hold X, a pool missing from the answer: rows that say why, and quote rows that say why not
    assert _snaps(con, mint=X, kind="POOL")[0]["state"] == "IDENTITY_MISMATCH"
    assert [s["state"] for s in _snaps(con, mint=X, kind="QUOTE")] == ["SKIPPED_POOL_IDENTITY_MISMATCH"] * 3
    assert _snaps(con, mint=P, kind="POOL")[0]["state"] == "NOT_IN_RESPONSE"
    assert [(s["state"], s["size_usd"]) for s in _snaps(con, mint=P, kind="QUOTE")] == [("SKIPPED_POOL_NOT_IN_RESPONSE", s) for s in depth.SIZES_USD]
    assert _snaps(con, mint=C, kind="POOL")[0]["state"] == "OK"                     # EVM identity ignores case
    assert [s["state"] for s in _snaps(con, mint=C, kind="QUOTE")] == ["QUOTE_UNSUPPORTED_CHAIN"]
    assert _snaps(con, mint=E, kind="POOL")[0]["state"] == "OK"
    assert out["quote_source"] == "OK" and out["calls"] == {"geckoterminal": 4, "jupiter": 12, "retries": 0}
    assert out["pool_snapshots"] == {"OK": 6, "IDENTITY_MISMATCH": 1, "NOT_IN_RESPONSE": 1}
    st = {r["mint"]: r for r in depth.status(con, now=NOW + 60)["rows"]}
    assert st[A]["pool_hours_of_25"] == 1 and st[D]["pool_source"] == "VENDOR_TOP_POOL" and st[D]["lookups"] == {"OK": 1}


def test_quote_side_pool_uses_the_mints_own_price_and_decimals(con, exports):
    _run(con, exports)
    p = _snaps(con, mint=Q, kind="POOL")[0]
    v = json.loads(p["value_json"])
    a = json.loads(_snaps(con, mint=A, kind="POOL")[0]["value_json"])
    assert p["state"] == "OK" and v["side"] == "quote" and v["decimals"] == 6 and v["price_field"] == "quote_token_price_usd"
    assert p["price_usd"] == a["price_usd"] and v["mint_balance"] == a["mint_balance"] and v["other_balance"] == a["other_balance"]
    q = _snaps(con, mint=Q, kind="QUOTE")[0]
    assert int(q["token_amount_raw"]) == math.floor(100.0 / a["price_usd"] * 10 ** 6)


def test_solana_identity_is_case_sensitive(con, tmp_path):
    lower = {"status": "OK", "decisions": [{"chain": "solana", "mint": A.lower(), "pool_address": A_POOL, "pool_source": "EXPORT_GRADUATED_POOL",
                                            "export_commit": "c", "export_time": NOW - 600, "export_path": "p", "created_at": NOW - 700,
                                            "row_sha256": "r", "status": "x"}]}
    _run(con, lower)
    assert _snaps(con, mint=A.lower(), kind="POOL")[0]["state"] == "IDENTITY_MISMATCH"


def test_gt_pacing_counts_the_refresh_calls(con, exports):
    out, calls = _run(con, exports, gt_prior_calls=12, gt_prior_end=NOW - 5)
    gt = [c["start"] for c in calls if "geckoterminal" in c["url"]]
    assert gt[0] >= NOW - 5 + 60                              # refresh made 12 calls just before: the window must clear first
    stamps = [NOW - 5] * 12 + gt
    assert all(sum(1 for s in stamps if t - 60 <= s <= t) <= 6 for t in gt)
    assert all(b - a >= depth.GT_SPACING_S for a, b in zip(gt, gt[1:])) and depth.GT_SPACING_S >= 10.0
    jq = [c["start"] for c in calls if "jup.ag" in c["url"]]
    assert all(b - a >= depth.JUP_SPACING_S for a, b in zip(jq, jq[1:])) and 60 / depth.JUP_SPACING_S <= 30
    out0, calls0 = _run(con, exports, now=NOW + 3600)          # no refresh calls: no wait
    assert [c["start"] for c in calls0 if "geckoterminal" in c["url"]][0] == NOW + 3600


def test_call_caps_leave_rows_that_say_so(con, exports):
    out, calls = _run(con, exports, gt_max_calls=2, jup_max_calls=4)
    assert sum("geckoterminal" in c["url"] for c in calls) == 2 and sum("jup.ag" in c["url"] for c in calls) == 4
    assert [s["state"] for s in _snaps(con, mint=C)] == ["NOT_ATTEMPTED_CAP", "QUOTE_UNSUPPORTED_CHAIN"]
    assert out["pool_snapshots"]["NOT_ATTEMPTED_CAP"] == 2
    assert out["quotes"]["NOT_ATTEMPTED_CAP"] == 12 - 4          # every Solana pool read OK has three quote rows
    for p in (A, B, D, Q):
        assert len(_snaps(con, mint=p, kind="QUOTE")) == 3


def test_deadline_stops_new_calls_and_bounds_the_run(con, exports):
    out, calls = _run(con, exports, deadline_s=15)
    assert [c["start"] for c in calls] and all(c["start"] < NOW + 15 for c in calls)
    assert out["deadline_hit"] is True and out["wall_s"] <= 15 + depth.HTTP_TIMEOUT_S
    assert "NOT_ATTEMPTED_DEADLINE" in {s["state"] for s in _snaps(con)}
    assert depth.DEADLINE_S + depth.HTTP_TIMEOUT_S <= 130


def test_slow_network_ends_by_the_deadline(con, exports):
    clk = Clock(NOW)

    def slow(url):
        clk.t += depth.HTTP_TIMEOUT_S                          # every call times out
        return 0, b""
    out = depth.collect(con, exports=exports, now=NOW, http_get=slow, clock=clk, sleep=clk.sleep)
    assert out["wall_s"] <= depth.DEADLINE_S + depth.HTTP_TIMEOUT_S


@pytest.mark.parametrize("status", [429, 503, 0])
def test_failure_on_the_last_budgeted_quote_ends_cleanly(con, exports, status):
    out, calls = _run(con, exports, jup_max_calls=4, jup_fail={4: status})
    assert sum("jup.ag" in c["url"] for c in calls) == 4
    rows = [s for s in _snaps(con, kind="QUOTE") if s["provider"] == "jupiter" and s["http_status"] is not None]
    last = rows[-1]
    assert last["state"] == ("SOURCE_BLOCKED" if status == 0 else f"HTTP_{status}") and json.loads(last["value_json"])["retry_refused"] == "cap"
    assert out["quotes"]["NOT_ATTEMPTED_CAP"] >= 1 and out["calls"]["retries"] == 0      # no retry counted or waited for at the cap


@pytest.mark.parametrize("status", [429, 502, 0])
def test_failure_on_the_last_budgeted_pool_read_ends_cleanly(con, exports, status):
    out, calls = _run(con, exports, gt_max_calls=3, gt_fail={3: status})
    assert sum("geckoterminal" in c["url"] for c in calls) == 3
    bsc = _snaps(con, mint=C, kind="POOL")[0]
    assert bsc["state"] == ("SOURCE_BLOCKED" if status == 0 else f"HTTP_{status}") and bsc["http_status"] == status
    assert _snaps(con, mint=E, kind="POOL")[0]["state"] == "NOT_ATTEMPTED_CAP"


def _bare_run(clk, get, **kw):
    a = dict(gt_max_calls=2, jup_max_calls=2, gt_spacing_s=10.0, jup_spacing_s=2.2, deadline_s=30.0, gt_prior_calls=0, gt_prior_end=None)
    a.update(kw)
    return depth._Run(None, NOW, get, clk, clk.sleep, a["gt_max_calls"], a["jup_max_calls"], a["gt_spacing_s"], a["jup_spacing_s"],
                      a["deadline_s"], a["gt_prior_calls"], a["gt_prior_end"])


def test_read_refuses_past_the_cap_and_the_deadline_without_calling(con):
    clk = Clock(NOW)
    get = fake(clk)
    r = _bare_run(clk, get, jup_max_calls=1)
    url = f"{depth.JUP_QUOTE}?inputMint={A}&outputMint={depth.USDC}&amount=1&slippageBps=300&swapMode=ExactIn"
    assert r.get(url, "jup")["status"] == 400 and r.get(url, "jup") == {"status": None, "skip": "NOT_ATTEMPTED_CAP", "attempts": []}
    clk2 = Clock(NOW)
    get2 = fake(clk2)
    r2 = _bare_run(clk2, get2, deadline_s=1.0)
    clk2.t = NOW + 1.0
    assert r2.get(url, "jup") == {"status": None, "skip": "NOT_ATTEMPTED_DEADLINE", "attempts": []} and get2.calls == []
    r3 = _bare_run(clk2, get2, deadline_s=3.0)                    # the spacing wait runs into the deadline: no call
    r3.jup._last = clk2.t + 2.0
    assert r3.get(url, "jup")["skip"] == "NOT_ATTEMPTED_DEADLINE" and get2.calls == []
    assert len(get.calls) == 1


def test_one_retry_is_made_and_both_bodies_kept(con, exports):
    out, calls = _run(con, exports, jup_fail={1: 429})
    first = [c for c in calls if "jup.ag" in c["url"]][:2]
    assert first[0]["url"] == first[1]["url"] and first[1]["start"] - first[0]["end"] >= depth.RETRY_WAIT_S
    row = next(s for s in _snaps(con, kind="QUOTE") if s["request_url"] == first[0]["url"])
    att = json.loads(row["value_json"])["attempts"]
    assert row["state"] == "OK" and [a["status"] for a in att] == [429, 200] and all(a["raw_sha256"] for a in att)
    assert out["calls"]["retries"] == 1


def test_quote_source_blocked_still_collects_reserves(con, exports):
    out, _ = _run(con, exports, jup="401")
    assert out["quote_source"] == "QUOTE_SOURCE_BLOCKED"
    assert {s["state"] for s in _snaps(con, kind="QUOTE", chain="solana", provider="jupiter") if s["http_status"]} == {"HTTP_401"}
    assert out["pool_snapshots"]["OK"] == 6


def test_quote_identity_checked(con, exports):
    def wrong_amount(url):
        q = parse_qs(urlparse(url).query)
        key = (q["inputMint"][0], q["amount"][0])
        if key in JUP:
            j = json.loads(JUP[key]); j["inAmount"] = str(int(j["inAmount"]) + 1)
            return 200, json.dumps(j).encode()
    _run(con, exports, quote_hook=wrong_amount)
    assert {s["state"] for s in _snaps(con, mint=A, kind="QUOTE")} == {"IDENTITY_MISMATCH"}


def test_counterexample_stale_pool_price_is_flagged(con, exports):
    """Skeptic M4: the export's pool shows twice the market price; the router sells at the market. Without a check the
    proceeds read as a 50% haircut. The router's implied price (proceeds before its small stated impact, per token) is
    half the pool's price, which gives it away."""
    d = json.loads(SOL_POOLS)
    for it in d["data"]:
        if it["attributes"]["address"] == A_POOL:
            it["attributes"]["base_token_price_usd"] = str(float(it["attributes"]["base_token_price_usd"]) * 2)

    def at_market(url):
        if f"inputMint={A}" not in url:
            return None
        amt = int(parse_qs(urlparse(url).query)["amount"][0])
        fx = next(v for (m, a), v in JUP.items() if m == A and abs(int(a) / 2 - amt) / amt < 0.01)
        j = json.loads(fx); sc = amt / int(j["inAmount"])
        j["inAmount"] = str(amt); j["outAmount"] = str(int(int(j["outAmount"]) * sc)); j["swapUsdValue"] = str(float(j["swapUsdValue"]) * sc)
        return 200, json.dumps(j).encode()
    _run(con, exports, sol_pools=json.dumps(d).encode(), quote_hook=at_market)
    rows = _snaps(con, mint=A, kind="QUOTE")
    assert [r["state"] for r in rows] == ["PRICE_DISAGREES"] * 3
    v = json.loads(rows[0]["value_json"])
    assert v["price_check"] == "DISAGREES" and 0.45 < v["implied_over_pool_price"] < 0.55 and v["price_source"].endswith("base_token_price_usd")


def test_real_price_impact_is_not_a_price_disagreement(con, exports):
    """Live run 2026-10-25 14:13Z: a $2,000 sale of 3vZY... got 0.80 of the size with priceImpactPct 0.203, and the
    router's swapUsdValue (it values the output) was 0.80 of the size too. A check on swapUsdValue would call real
    depth a pricing error; the implied price check must not. Here A's $2,000 quote is given a 20% impact."""
    def deep_impact(url):
        q = parse_qs(urlparse(url).query)
        key = (q["inputMint"][0], q["amount"][0])
        j = json.loads(JUP[key]) if key in JUP and key[0] == A else None
        if not j or int(j["inAmount"]) < 10 ** 11 * 5:
            return None
        j["priceImpactPct"] = "0.2"
        j["outAmount"] = str(int(int(j["outAmount"]) * 0.8 / (1 - 0.010878965890850858)))
        j["swapUsdValue"] = str(float(j["swapUsdValue"]) * 0.8)
        return 200, json.dumps(j).encode()
    _run(con, exports, quote_hook=deep_impact)
    r = [x for x in _snaps(con, mint=A, kind="QUOTE") if x["size_usd"] == 2000.0][0]
    v = json.loads(r["value_json"])
    assert r["state"] == "OK" and r["out_usd"] / 2000 < 0.81 and abs(v["implied_over_pool_price"] - 1.0) < 0.02 and v["price_check"] == "OK"


def test_quote_order_rotates_and_prefers_unquoted_pools(con, exports):
    _run(con, exports, jup_max_calls=3)                         # one pool gets its three quotes
    first = {s["mint"] for s in _snaps(con, kind="QUOTE", provider="jupiter") if s["http_status"]}
    _run(con, exports, now=NOW + 3600, jup_max_calls=3)
    second = {s["mint"] for s in _snaps(con, kind="QUOTE", provider="jupiter") if s["http_status"] and s["run_id"].endswith(
        __import__("time").strftime("%Y%m%dT%HZ", __import__("time").gmtime(NOW + 3600)))}
    assert len(first) == 1 and len(second) == 1 and first != second


def test_every_pool_gets_its_turn_including_pools_without_a_route(con, exports):
    """Cap of one pool per hour, four Solana pools (two answer NO_ROUTE): four hours give each pool exactly one turn."""
    import time as _t
    turns = []
    for h in range(4):
        _run(con, exports, now=NOW + h * 3600, jup_max_calls=3)
        rid = "depth-" + _t.strftime("%Y%m%dT%HZ", _t.gmtime(NOW + h * 3600))
        turns.append({s["mint"] for s in _snaps(con, kind="QUOTE", provider="jupiter", run_id=rid) if s["http_status"]})
    assert all(len(t) == 1 for t in turns) and set().union(*turns) == {A, B, D, Q}


def test_pool_lookup_failures_are_recorded_and_retried(con, exports):
    _run(con, exports, gt_fail={1: 429, 2: 429})                 # the token lookup and its retry
    lk = [dict(r) for r in con.execute("SELECT * FROM bt_depth_pool_lookups WHERE mint=?", (D,))]
    assert [(x["state"], x["attempt"]) for x in lk] == [("HTTP_429", 1)]
    assert [a["status"] for a in json.loads(lk[0]["value_json"])["attempts"]] == [429, 429]
    _run(con, exports, now=NOW + 3600)
    lk = [dict(r) for r in con.execute("SELECT * FROM bt_depth_pool_lookups WHERE mint=? ORDER BY id", (D,))]
    assert [(x["state"], x["attempt"]) for x in lk] == [("HTTP_429", 1), ("OK", 2)]
    assert _snaps(con, mint=D, kind="POOL")[0]["pool_address"] == D_TOP


def test_same_hour_rerun_adds_nothing(con, exports):
    _run(con, exports)
    n = con.execute("SELECT COUNT(*) FROM bt_depth_snapshots").fetchone()[0]
    out, calls = _run(con, exports, now=NOW + 600)
    assert out["status"] == "SKIPPED_SAME_HOUR" and calls == [] and con.execute("SELECT COUNT(*) FROM bt_depth_snapshots").fetchone()[0] == n


def test_rerun_window_end_and_no_exports(con, exports):
    _run(con, exports)
    out, calls = _run(con, exports, now=NOW + 3600)
    assert out["decisions_new"] == 0 and not [c for c in calls if "/tokens/multi/" in c["url"]]
    assert len(_snaps(con, mint=A, kind="POOL")) == 2
    out, calls = _run(con, None, now=NOW + 7200)                     # exports not reachable: stored decisions only
    assert out["exports"]["status"] == "NOT_READ" and len(_snaps(con, mint=A, kind="POOL")) == 3
    out, calls = _run(con, None, now=NOW - 3600 + depth.ACTIVE_S + 1)
    assert calls == [] and out["pools_active"] == 0


def test_cli_collect_without_exports_and_status(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    db = tmp_path / "bt.sqlite"
    cli.main(["depth", "collect", "--repo", str(tmp_path / "missing"), "--db", str(db), "--gt-prior-calls", "3", "--gt-prior-end", str(NOW)])
    out = json.loads(capsys.readouterr().out)
    assert out["exports"]["status"] in ("NO_EXPORTS",) or out["exports"]["status"].startswith("EXPORTS_UNREADABLE")
    assert out["calls"]["geckoterminal"] == 0 and out["calls"]["jupiter"] == 0
    cli.main(["depth", "status", "--db", str(db)])
    assert json.loads(capsys.readouterr().out)["decisions"] == 0


# ---------------------------------------------------------------- schema

def test_schema_v2_is_additive_with_rollback(tmp_path):
    c = sqlite3.connect(tmp_path / "s.sqlite")
    assert schema._checksum(schema.V1_UP) == "a206fdf1ec58e1722be2e3324e4ec1a80fd93c6c0df38bf7f88b4df541d6719f"   # v1 unchanged
    assert schema.migrate(c, target=1) == [1]
    v1 = sorted(r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE name LIKE 'bt_%'"))
    c.execute("INSERT INTO bt_market_bars(chain,mint,pool_address,timeframe_s,start,end,o,h,l,c,observed_at,available_at,provider,content_hash) "
              "VALUES ('solana','m','p',3600,0,3600,1,1,1,1,4000,4000,'x','h')")
    c.commit()
    assert schema.migrate(c) == [2] and schema.current_version(c) == schema.LATEST == 2
    for t in ("bt_depth_decisions", "bt_depth_pool_lookups", "bt_depth_snapshots"):
        assert t in schema.BT_TABLES
    c.execute("INSERT INTO bt_depth_decisions(chain,mint,pool_source,export_commit,export_time,created_at,row_sha256,recorded_at,content_hash) "
              "VALUES ('solana','m','NONE_IN_EXPORT','c',1,1,'r',1,'h')")
    for sql in ("UPDATE bt_depth_decisions SET mint='n'", "DELETE FROM bt_depth_decisions"):
        with pytest.raises(sqlite3.DatabaseError):
            c.execute(sql)
    assert schema.rollback(c, 1) == [2]
    assert sorted(r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE name LIKE 'bt_%'")) == v1
    assert c.execute("SELECT COUNT(*) FROM bt_market_bars").fetchone()[0] == 1


# ---------------------------------------------------------------- hourly script

def test_hourly_script_runs_collect_between_refresh_and_track_on_the_work_copy():
    s = (ROOT / "audits" / "backtesting" / "release" / "hourly_shadow.sh").read_text()
    assert "usage: bash hourly_shadow.sh setup|refresh|collect|track|save|status" in s
    assert s.index("\nrefresh)") < s.index("\ncollect)") < s.index("\ntrack)")
    block = s[s.index("\ncollect)"):s.index("\ntrack)")]
    assert '--db "$W/bt.sqlite"' in block and "depth collect" in block and '"$L/' not in block   # never the stored database
    assert "GIT_TERMINAL_PROMPT=0" in block and "--shallow-since" in block and "|| fail" in block
    assert "--gt-prior-calls" in block and '"$W/refresh.json"' in block
    fetch_s = int(re.search(r"\$T (\d+)\} git", block).group(1))
    prog_s = int(re.search(r"\$T (\d+)\} \"\$PY\" -m memelab backtest depth collect", block).group(1))
    assert fetch_s + prog_s <= 165 and prog_s >= depth.DEADLINE_S + depth.HTTP_TIMEOUT_S + 10   # margin under the 175 s call

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


def _row(mint, created, status="RESEARCH REQUIRED", score=50, rid=1):
    return {"id": rid, "mint": mint, "created_at": created, "status": status, "score": score, "snapshot_json": json.dumps({"price": 1.0})}


def _tok(mint, chain="solana", primary=None, graduated=None):
    return {"mint": mint, "chain": chain, "primary_pool": primary, "graduated_pool": graduated, "decimals": 6}


TOKS = [_tok(A, graduated=A_POOL), _tok(B, graduated=B_POOL), _tok(C, "bsc", primary=C_POOL), _tok(D), _tok(E, "base", primary=E_POOL),
        _tok(F, "sui", primary="0xpool"), _tok(X, graduated=A_POOL)]
V0 = {"tokens": TOKS[:2], "theses": [_row(A, NOW - 49 * 3600), _row(B, NOW - 49 * 3600, rid=2)]}
V1 = {"tokens": TOKS[:2], "theses": V0["theses"] + [_row(A, NOW - 31 * 3600, rid=3)]}
V2 = {"tokens": TOKS, "theses": V1["theses"] + [
    _row(A, NOW - 4 * 3600, rid=4),                                  # new row of a known mint: a new decision
    _row(B, NOW - 49 * 3600, status="REJECTED", rid=5),              # same key as a baseline row, different content: new
    _row(C, NOW - 4 * 3600, rid=6), _row(D, NOW - 4 * 3600, rid=7), _row(E, NOW - 4 * 3600, rid=8),
    _row(F, NOW - 4 * 3600, rid=9), _row(X, NOW - 4 * 3600, rid=10)]}
V2 = {"tokens": V2["tokens"], "theses": V2["theses"] + [dict(V0["theses"][0], id=99)]}   # same row, other id: not new


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
    repo = _repo(tmp_path, [(NOW - 48 * 3600, V0), (NOW - 30 * 3600, V1), (NOW - 3 * 3600, V2)])
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


def fake(clock, jup="ok"):
    calls = []

    def get(url):
        start = clock.t
        clock.t += 0.3
        calls.append({"start": start, "end": clock.t, "url": url})
        if url.startswith("https://api.geckoterminal.com/"):
            for pat, name in (("/solana/tokens/multi/", "gt_tokens_multi_solana"), ("/solana/pools/multi/", "gt_pools_multi_solana"),
                              ("/bsc/pools/multi/", "gt_pools_multi_bsc"), ("/base/pools/multi/", "gt_pools_multi_base")):
                if pat in url:
                    return 200, (FX / f"{name}.json").read_bytes()
            return 404, b'{"errors":[{"status":"404","title":"Not Found"}]}'
        if url.startswith(depth.JUP_QUOTE):
            if jup == "401":
                return 401, b'{"message":"Unauthorized"}'
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


def _run(con, exports, now=NOW, jup="ok", **kw):
    clk = Clock(now)
    get = fake(clk, jup)
    out = depth.collect(con, exports=exports, now=now, http_get=get, clock=clk, sleep=clk.sleep, **kw)
    return out, get.calls


def _snaps(con, **where):
    sql = "SELECT * FROM bt_depth_snapshots" + (" WHERE " + " AND ".join(f"{k}=?" for k in where) if where else "") + " ORDER BY id"
    return [dict(r) for r in con.execute(sql, tuple(where.values()))]


# ---------------------------------------------------------------- decisions

def test_export_decisions_baseline_window_and_pool(exports):
    assert exports["status"] == "OK" and exports["exports"] == 3
    got = sorted((d["mint"], d["status"]) for d in exports["decisions"])
    assert got == sorted([(A, "RESEARCH REQUIRED"), (B, "REJECTED"), (C, "RESEARCH REQUIRED"), (D, "RESEARCH REQUIRED"),
                          (E, "RESEARCH REQUIRED"), (F, "RESEARCH REQUIRED"), (X, "RESEARCH REQUIRED")])
    by = {d["mint"]: d for d in exports["decisions"]}
    assert all(d["export_time"] == NOW - 3 * 3600 for d in exports["decisions"])
    assert (by[A]["pool_address"], by[A]["pool_source"]) == (A_POOL, "EXPORT_GRADUATED_POOL")
    assert (by[C]["chain"], by[C]["pool_address"], by[C]["pool_source"]) == ("bsc", C_POOL, "EXPORT_PRIMARY_POOL")
    assert by[D]["pool_address"] is None and by[F]["chain"] == "sui"
    assert by[A]["row_sha256"] == depth.row_sha256(V2["theses"][3])


def test_export_decisions_need_a_baseline(tmp_path):
    repo = _repo(tmp_path, [(NOW - 3600, V2)])
    out = depth.export_decisions(repo, "refs/heads/main", now=NOW)
    assert out["status"] == "NO_BASELINE" and out["decisions"] == []


def test_rows_of_the_oldest_export_read_are_never_new(tmp_path):
    """A shallow history cannot say when the oldest export's rows first appeared, even when that export is recent."""
    repo = _repo(tmp_path, [(NOW - 10 * 3600, V1), (NOW - 2 * 3600, V2)])
    out = depth.export_decisions(repo, "refs/heads/main", now=NOW)
    assert out["baseline_commit"] and sorted(d["mint"] for d in out["decisions"]) == sorted([A, B, C, D, E, F, X])
    assert all(d["export_time"] == NOW - 2 * 3600 for d in out["decisions"])


# ---------------------------------------------------------------- one run

def test_collect_pools_quotes_and_provenance(con, exports):
    out, calls = _run(con, exports)
    dec = {r["mint"]: dict(r) for r in con.execute("SELECT * FROM bt_depth_decisions")}
    assert set(dec) == {A, B, C, D, E, F, X}
    assert (dec[D]["pool_address"], dec[D]["pool_source"]) == (D_TOP, "VENDOR_TOP_POOL")
    assert dec[F]["pool_source"] == "UNSUPPORTED_CHAIN" and not _snaps(con, mint=F)
    # pool snapshot: reserves in token units and USD, the mint's side, decimals from the vendor's token record
    p = _snaps(con, mint=A, kind="POOL")[0]
    v = json.loads(p["value_json"])
    assert p["state"] == "OK" and v["side"] == "base" and v["decimals"] == 6 and v["mint_balance"] > 0 and v["other_balance"] > 0
    assert p["reserve_usd"] > 0 and p["price_usd"] > 0
    body = (FX / "gt_pools_multi_solana.json").read_bytes()
    assert p["raw_sha256"] == hashlib.sha256(body).hexdigest() and (store.RAW_DIR / "geckoterminal" / f"{p['raw_sha256']}.json").read_bytes() == body
    call = next(c for c in calls if "/solana/pools/multi/" in c["url"])
    assert p["request_url"] == call["url"] and p["captured_at"] == call["end"] and p["since_export_s"] == call["end"] - (NOW - 3 * 3600)
    assert "include_composition=true" in p["request_url"] and A_POOL in p["request_url"]
    # quotes: fixed USD sizes, token amount from the same run's price, proceeds in USDC
    qs = _snaps(con, mint=A, kind="QUOTE")
    assert [q["size_usd"] for q in qs] == list(depth.SIZES_USD) and all(q["state"] == "OK" for q in qs)
    for q in qs:
        assert int(q["token_amount_raw"]) == math.floor(q["size_usd"] / p["price_usd"] * 10 ** 6)
        j = json.loads((store.RAW_DIR / "jupiter" / f"{q['raw_sha256']}.json").read_bytes())
        assert q["out_usd"] == int(j["outAmount"]) / 1e6 and j["inAmount"] == q["token_amount_raw"]
        assert f"inputMint={A}" in q["request_url"] and f"outputMint={depth.USDC}" in q["request_url"]
        qc = next(c for c in calls if c["url"] == q["request_url"])
        assert q["captured_at"] == qc["end"]
    assert qs[-1]["out_usd"] < qs[-1]["size_usd"]              # a bigger sale gets less per dollar
    # the vendor's top pool for D, a pool that does not hold X, EVM pools without a quote source, a mint with no route
    assert [s["state"] for s in _snaps(con, mint=D, kind="QUOTE")] == ["NO_ROUTE"] * 3
    assert _snaps(con, mint=X, kind="POOL")[0]["state"] == "IDENTITY_MISMATCH" and not _snaps(con, mint=X, kind="QUOTE")
    assert _snaps(con, mint=C, kind="POOL")[0]["state"] == "OK"                     # EVM identity ignores case
    assert [s["state"] for s in _snaps(con, mint=C, kind="QUOTE")] == ["QUOTE_UNSUPPORTED_CHAIN"]
    assert _snaps(con, mint=E, kind="POOL")[0]["state"] == "OK"
    assert out["quote_source"] == "OK" and out["calls"] == {"geckoterminal": 4, "jupiter": 9, "retries": 0}
    assert out["pool_snapshots"] == {"OK": 5, "IDENTITY_MISMATCH": 1}
    # status: lag from the export commit to the first snapshot
    st = {r["mint"]: r for r in depth.status(con, now=NOW + 60)["rows"]}
    assert st[A]["first_pool_lag_s"] == round(p["captured_at"] - (NOW - 3 * 3600), 1) and st[A]["pool_hours_of_25"] == 1


def test_pacing_caps_and_deadline(con, exports):
    out, calls = _run(con, exports)
    gt = [c["start"] for c in calls if "geckoterminal" in c["url"]]
    jq = [c["start"] for c in calls if "jup.ag" in c["url"]]
    assert gt[0] >= NOW + depth.GT_SPACING_S and depth.GT_SPACING_S >= 10.0       # refresh ran just before: wait first
    assert all(b - a >= depth.GT_SPACING_S for a, b in zip(gt, gt[1:]))
    assert all(b - a >= depth.JUP_SPACING_S for a, b in zip(jq, jq[1:])) and depth.JUP_SPACING_S >= 2.0
    assert out["wall_s"] <= depth.DEADLINE_S + 30


def test_call_caps(con, exports):
    out, calls = _run(con, exports, gt_max_calls=2, jup_max_calls=4)
    assert sum("geckoterminal" in c["url"] for c in calls) == 2 and sum("jup.ag" in c["url"] for c in calls) == 4
    assert out["not_attempted"] == {"geckoterminal_tasks": 2, "quotes": 5}
    assert not _snaps(con, mint=C) and not _snaps(con, mint=E)


def test_deadline_stops_new_calls(con, exports):
    out, calls = _run(con, exports, deadline_s=15)
    assert [c["start"] for c in calls] and all(c["start"] < NOW + 15 for c in calls)
    assert out["deadline_hit"] is True and out["not_attempted"]["geckoterminal_tasks"] >= 1


def test_quote_source_blocked_still_collects_reserves(con, exports):
    out, _ = _run(con, exports, jup="401")
    assert out["quote_source"] == "QUOTE_SOURCE_BLOCKED"
    assert {s["state"] for s in _snaps(con, kind="QUOTE", chain="solana")} == {"HTTP_401"}
    assert out["pool_snapshots"]["OK"] == 5


def test_quote_identity_checked(con, exports, monkeypatch):
    clk = Clock(NOW)
    base = fake(clk)

    def wrong_amount(url):
        status, body = base(url)
        if "jup.ag" in url and status == 200:
            j = json.loads(body); j["inAmount"] = str(int(j["inAmount"]) + 1)
            return status, json.dumps(j).encode()
        return status, body
    depth.collect(con, exports=exports, now=NOW, http_get=wrong_amount, clock=clk, sleep=clk.sleep)
    assert {s["state"] for s in _snaps(con, mint=A, kind="QUOTE")} == {"IDENTITY_MISMATCH"}


def test_rerun_window_end_and_no_exports(con, exports):
    _run(con, exports)
    out, calls = _run(con, exports, now=NOW + 3600)
    assert out["decisions_new"] == 0 and not [c for c in calls if "/tokens/multi/" in c["url"]]
    assert len(_snaps(con, mint=A, kind="POOL")) == 2
    out, calls = _run(con, None, now=NOW + 7200)                     # exports not reachable: stored decisions only
    assert out["exports"]["status"] == "NOT_READ" and len(_snaps(con, mint=A, kind="POOL")) == 3
    out, calls = _run(con, None, now=NOW - 3 * 3600 + depth.ACTIVE_S + 1)
    assert calls == [] and out["pools_active"] == 0


def test_cli_collect_without_exports_and_status(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    db = tmp_path / "bt.sqlite"
    cli.main(["depth", "collect", "--repo", str(tmp_path / "missing"), "--db", str(db)])
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
    for t in ("bt_depth_decisions", "bt_depth_snapshots"):
        assert t in schema.BT_TABLES
    c.execute("INSERT INTO bt_depth_decisions(chain,mint,export_commit,export_time,created_at,row_sha256,recorded_at,content_hash) VALUES ('solana','m','c',1,1,'r',1,'h')")
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("UPDATE bt_depth_decisions SET mint='n'")
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("DELETE FROM bt_depth_decisions")
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
    assert re.search(r"\$T 160", block)                     # a hard stop below the 175 s step timeout

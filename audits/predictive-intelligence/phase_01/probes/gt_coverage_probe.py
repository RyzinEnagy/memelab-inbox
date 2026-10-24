"""Phase 01 probe: can the pre-registered price-path labels be read from free GeckoTerminal OHLCV for real lab decisions?

Run AFTER the target registry was committed (b6f2621, registry sha256 dd3b4576...). Reports COVERAGE ONLY: HTTP status, candle
counts, whether a reference trade exists in the hour before entry, path density and gaps, retention of 5-minute candles,
pool resolution route, and a revision check (same request twice). It computes no barrier, no return and no class.

Network: GeckoTerminal public API only, at most MAX_CALLS calls, paced >= PACE_S seconds apart (about 9 a minute, under the
documented 10 a minute, PI-D-010). Raw bodies go to RAW_DIR outside the repo with their sha256; the summary holds no prices.

Usage (repo root):
    python audits/predictive-intelligence/phase_01/probes/gt_coverage_probe.py UNIVERSE.json RAW_DIR OUT.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://api.geckoterminal.com/api/v2/networks/solana"
PACE_S = 6.7
MAX_CALLS = 20
SEED = 20261024
LAG = 300
H24 = 86400
CONFIRM = 86400
_calls: list[dict] = []
_last = [0.0]


def iso(t):
    return dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, raw_dir: Path, tag: str) -> tuple[int, dict | None]:
    if len(_calls) >= MAX_CALLS:
        raise SystemExit("call budget reached")
    wait = _last[0] + PACE_S - time.time()
    if wait > 0:
        time.sleep(wait)
    started = time.time()
    p = subprocess.run(["curl", "-sS", "-o", "-", "-w", "\n%{http_code}", "-H", "Accept: application/json;version=20230302", url],
                       capture_output=True, timeout=60)
    _last[0] = time.time()
    body, _, code = p.stdout.rpartition(b"\n")
    code = int(code or 0)
    h = hashlib.sha256(body).hexdigest()
    f = raw_dir / f"{len(_calls):02d}_{tag}.json"
    f.write_bytes(body)
    _calls.append({"n": len(_calls), "tag": tag, "url": url, "retrieved_at": iso(started), "http": code, "bytes": len(body), "sha256": h})
    try:
        return code, json.loads(body) if code == 200 else None
    except ValueError:
        return code, None


def main(universe: str, raw: str, out: str) -> None:
    raw_dir = Path(raw)
    raw_dir.mkdir(parents=True, exist_ok=True)
    ev = json.load(open(universe))["_events_24h_list"]
    rng = random.Random(SEED)
    early = [e for e in ev if e["decision_t"] < dt.datetime(2026, 10, 12, tzinfo=dt.UTC).timestamp()]
    late = [e for e in ev if e["decision_t"] >= dt.datetime(2026, 10, 15, tzinfo=dt.UTC).timestamp()]
    pick = []
    for pool_known, n_early, n_late in ((True, 3, 3), (False, 2, 2)):
        pick += rng.sample([e for e in early if bool(e["pool_pit"]) == pool_known], n_early)
        pick += rng.sample([e for e in late if bool(e["pool_pit"]) == pool_known], n_late)
    rows = []
    first_req = None
    for e in pick:
        r = {"mint": e["mint"], "decision_utc": iso(e["decision_t"]), "status_at_decision": e["status"], "commit": e["commit"][:7]}
        pool, route = e["pool_pit"], "PIT_RECORDED"
        if not pool:
            route = "CURRENT_VENDOR_LIST"
            code, d = get(f"{BASE}/tokens/{e['mint']}/pools?page=1", raw_dir, f"pools_{e['mint'][:6]}")
            lst = (d or {}).get("data") or []
            r["vendor_pools_listed"] = len(lst)
            r["vendor_pools_http"] = code
            r["vendor_top_dex"] = ((lst[0].get("relationships") or {}).get("dex") or {}).get("data", {}).get("id") if lst else None
            pool = lst[0]["attributes"]["address"] if lst else None
        r["pool"], r["pool_route"] = pool, route
        if not pool:
            r["coverage"] = "NO_POOL_RESOLVED"
            rows.append(r)
            continue
        t_entry = e["decision_t"] + LAG
        before = int(t_entry + H24 + CONFIRM + 900)
        url = f"{BASE}/pools/{pool}/ohlcv/minute?aggregate=5&limit=1000&before_timestamp={before}&currency=usd"
        first_req = first_req or (url, pool)
        code, d = get(url, raw_dir, f"ohlcv5_{pool[:6]}")
        r["ohlcv_http"] = code
        lst = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        ts = sorted(int(c[0]) for c in lst)
        r["candles"] = len(ts)
        if not ts:
            r["coverage"] = "NO_CANDLES" if code == 200 else f"HTTP_{code}"
            rows.append(r)
            continue
        r["earliest_candle_h_before_entry"] = round((t_entry - ts[0]) / 3600, 2)
        ref = [t for t in ts if t + 300 <= t_entry and t + 300 >= t_entry - 3600]
        r["reference_trade_in_hour_before_entry"] = bool(ref)
        path = [t for t in ts if t >= t_entry and t + 300 <= t_entry + H24]
        r["path_candles_24h"] = len(path)
        pts = sorted({t_entry, t_entry + H24, *path})
        r["path_max_gap_h"] = round(max(b - a for a, b in zip(pts, pts[1:])) / 3600, 2)
        r["window_requested_back_to_h_before_entry"] = round((t_entry - (before - 1000 * 300)) / 3600, 2)
        r["coverage"] = "OK" if ref else "INELIGIBLE_NO_RECENT_TRADE"
        rows.append(r)
    # revision check: the first OHLCV request again, compare candles strictly older than both retrievals by more than a day
    rev = None
    if first_req:
        url, pool = first_req
        code, d = get(url, raw_dir, f"ohlcv5_{pool[:6]}_again")
        first_call = next(c for c in _calls if c["url"] == url)
        a = json.loads((raw_dir / f"{first_call['n']:02d}_{first_call['tag']}.json").read_bytes())
        la = {int(c[0]): c for c in a["data"]["attributes"]["ohlcv_list"]}
        lb = {int(c[0]): c for c in (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []}
        common = sorted(set(la) & set(lb))
        diff = [t for t in common if la[t] != lb[t]]
        rev = {"pool": pool, "candles_first": len(la), "candles_second": len(lb), "common": len(common), "changed": len(diff),
               "only_first": len(set(la) - set(lb)), "only_second": len(set(lb) - set(la))}
    summary = {"probe": "gt_coverage_probe", "registry_commit": "b6f2621", "seed": SEED, "sample": len(pick), "calls": _calls,
               "rows": rows, "revision_check": rev,
               "counts": {"coverage": {k: sum(1 for r in rows if r["coverage"] == k) for k in sorted({r["coverage"] for r in rows})},
                          "routes": {k: sum(1 for r in rows if r["pool_route"] == k) for k in ("PIT_RECORDED", "CURRENT_VENDOR_LIST")}},
               "note": "coverage only: no barrier, return or class was computed; raw bodies are outside the repo"}
    Path(out).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary["counts"], indent=1), json.dumps(rev))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

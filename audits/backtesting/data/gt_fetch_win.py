"""Standalone read-only GeckoTerminal fetcher (stdlib only) for the memelab backtesting corpus.
Runs on Elving's work computer to share the public API rate limit with the cloud workspace. It only performs GET
requests to api.geckoterminal.com, saves every raw response with its sha256, and writes a manifest. No keys, no
writes anywhere except this folder."""
import hashlib, json, random, sys, time, urllib.error, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE / "gt_raw"; OUT.mkdir(exist_ok=True)
MAN = HERE / "gt_manifest.jsonl"
BASE = "https://api.geckoterminal.com/api/v2"
mints = json.load(open(HERE / "mints_windows.json"))
labp = json.load(open(HERE / "labpools_windows.json"))
done = set()
if MAN.exists():
    for l in MAN.read_text().splitlines():
        try:
            r = json.loads(l)
            if r.get("kind") == "pools" and r.get("status") == 200: done.add(r["mint"])
        except Exception: pass
last = [0.0]
def get(url, kind, mint, pool=None):
    for attempt in range(5):
        dt = time.time() - last[0]
        if dt < 4.0: time.sleep(4.0 - dt)
        last[0] = time.time()
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "memelab-backtest/0.1 (research-only; read-only)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r: status, body = r.status, r.read()
        except urllib.error.HTTPError as e: status, body = e.code, b""
        except Exception: status, body = 0, b""
        obs = time.time()
        h = hashlib.sha256(body).hexdigest() if body else None
        f = None
        if status == 200 and body:
            f = f"{h}.json"; (OUT / f).write_bytes(body)
        with open(MAN, "a") as m: m.write(json.dumps({"url": url, "kind": kind, "mint": mint, "pool": pool, "status": status, "observed_at": obs, "file": f, "sha256": h, "attempt": attempt}) + "\n")
        if status == 200: return json.loads(body)
        if status in (429, 500, 502, 503, 504, 0): time.sleep(min(60, 5 * 2 ** attempt) + random.random()); continue
        return None
    return None
for i, mint in enumerate(mints):
    if mint in done: continue
    d = get(f"{BASE}/networks/solana/tokens/{mint}/pools?page=1", "pools", mint)
    if not d: continue
    pools = []
    for p in d.get("data") or []:
        a = p.get("attributes") or {}; rel = p.get("relationships") or {}
        if not (((rel.get("base_token") or {}).get("data") or {}).get("id") or "").endswith(mint): continue
        pools.append({"pool": a.get("address"), "res": float(a["reserve_in_usd"]) if a.get("reserve_in_usd") not in (None, "") else None, "created": a.get("pool_created_at")})
    cand = sorted([p for p in pools if p["res"] is not None], key=lambda p: -p["res"])[:1] + sorted([p for p in pools if p["created"]], key=lambda p: p["created"])[:1] + [p for p in pools if p["pool"] == labp.get(mint)]
    seen = set()
    for p in cand:
        if p["pool"] in seen: continue
        seen.add(p["pool"])
        get(f"{BASE}/networks/solana/pools/{p['pool']}/ohlcv/hour?aggregate=1&limit=1000&currency=usd&token={mint}", "ohlcv", mint, p["pool"])
    print(i, mint, len(pools), flush=True)
(HERE / "DONE").write_text(str(time.time()))

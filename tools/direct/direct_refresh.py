"""Direct-API watchlist refresh (no browser). Runs the repo's collector JS in Node against the public APIs.
usage (from the project root, after `python -m memelab init` and state import, data/config.json written):
  python tools/direct/direct_refresh.py --date 20261008 [--only SYM ...] [--eco ECO_ID] [--catalyst CAT_STAMP]
Outputs analysis reports in data/reports and a summary of status changes."""
import argparse, json, os, sqlite3, subprocess, sys, tempfile, urllib.request, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent.parent
RAW = "https://raw.githubusercontent.com/RyzinEnagy/memelab-inbox/main"
ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--only", nargs="*"); ap.add_argument("--eco"); ap.add_argument("--catalyst")
a = ap.parse_args()
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
W = Path(tempfile.mkdtemp(prefix="mldirect_")); JS = W / "js"; JS.mkdir()
INBOX = ROOT / "data" / "inbox"; INBOX.mkdir(parents=True, exist_ok=True)
def get(u, t=30, tries=5):
    for i in range(tries):  # CoinGecko's free tier answers 429 under bursts; back off and retry
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"user-agent": "memelab"}), timeout=t))
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1: raise
            time.sleep(15 * (i + 1))
for f in ("collector", "chains", "catalyst"):
    (JS / f"{f}.js").write_text(urllib.request.urlopen(f"{RAW}/bridge/{f}.js?x={time.time()}", timeout=30).read().decode())
env = {**os.environ, "MLJS": str(JS)}
def node_run(plan, out):
    pf = W / "p.json"; pf.write_text(json.dumps(plan))
    r = subprocess.run(["node", str(HERE / "runner.js"), str(pf), str(out)], env=env, capture_output=True, text=True); print(r.stdout.strip(), r.stderr[-300:])
def retry_failed(plan, resfile, rounds=2):
    for _ in range(rounds):
        d = json.load(open(resfile)); bad = [r for r in plan["reqs"] if (d.get(r["key"]) or {}).get("s") != 200]
        if not bad: return
        time.sleep(10); node_run({"id": "retry", "reqs": bad}, W / "r.json"); fx = json.load(open(W / "r.json"))
        for r in bad:
            if fx.get(r["key"], {}).get("s") == 200: d[r["key"]] = fx[r["key"]]
        json.dump(d, open(resfile, "w"), separators=(",", ":"))
def add_prices(resfile, price):
    d = json.load(open(resfile))
    for k in ("raw:cg_sol", "cg_price"): d[k] = {"s": 200, "len": 0, "ms": 0, "body": price}
    json.dump(d, open(resfile, "w"), separators=(",", ":"))
c = sqlite3.connect(ROOT / "data" / "memelab.sqlite")
rows = c.execute("select symbol,chain,mint,decimals from tokens where mint in (select mint from watchlist)").fetchall()
if a.only: rows = [r for r in rows if r[0] in a.only]
price = get("https://api.coingecko.com/api/v3/simple/price?ids=solana,bitcoin,ethereum,binancecoin&vs_currencies=usd&include_24hr_change=true")
native = {"solana": price["solana"]["usd"], "base": price["ethereum"]["usd"], "bsc": price["binancecoin"]["usd"]}
tok = {}; sym = {}
for s, ch, m, d in rows:
    sym[m] = s; sym[m.lower()] = s
    try:
        ps = get(f"https://api.dexscreener.com/tokens/v1/{ch}/{m}"); ps = [p for p in ps if p.get("baseToken", {}).get("address", "").lower() == m.lower()] or ps
        p = max(ps, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
        tok.setdefault(ch, []).append([m, p["pairAddress"], d, float(p.get("priceUsd") or 0), (p.get("liquidity") or {}).get("usd") or 0])
    except Exception as e: print("dexscreener lookup failed", s, e)
from memelab.chains import plan as cplan
cfgs = {ch: cplan.js_cfg(ch) for ch in tok if ch != "solana"}
for n, o in (("in.json", {"tokens": tok, "native": native}), ("cfgs.json", cfgs), ("syms.json", sym)): (W / n).write_text(json.dumps(o))
r = subprocess.run(["node", str(HERE / "mkplans.js"), str(W / "in.json"), str(W / "cfgs.json"), str(W / "syms.json"), a.date, str(W / "plans.json")], env=env, capture_output=True, text=True); print(r.stdout, r.stderr[-300:])
plans = json.load(open(W / "plans.json")); summary = []
# peer set for relative strength: CoinGecko meme category per EVM chain (one call per category, shared by that chain's tokens)
CG = "https://api.coingecko.com/api/v3"; peer_bodies = {}
from memelab.chains import registry as _R
for ch in sorted({p["chain"] for p in plans if p["chain"] != "solana"}):
    cat = _R.CHAINS[ch].get("cg_meme_category"); key = f"cg_mkts:{cat}:1"
    node_run({"id": "peers", "reqs": [{"key": key, "url": f"{CG}/coins/markets?vs_currency=usd&category={cat}&order=market_cap_desc&per_page=100&page=1&price_change_percentage=1h,24h,7d,30d", "proj": "cg_mkts"}]}, W / f"peers_{ch}.json")
    v = json.load(open(W / f"peers_{ch}.json")).get(key)
    if v and v.get("s") == 200: peer_bodies[ch] = (key, v)
for p in plans:  # sequential: GeckoTerminal free tier rate-limits parallel runs from one IP
    i = p["plan"]["id"]; res = INBOX / f"{i}.result.json"
    node_run(p["plan"], res); retry_failed(p["plan"], res); add_prices(res, price)
    if p["chain"] in peer_bodies:
        k, v = peer_bodies[p["chain"]]; d = json.load(open(res)); d[k] = v; json.dump(d, open(res, "w"), separators=(",", ":"))
    cmd = [sys.executable, "-m", "memelab", "analyze", p["addr"], "--results", i] if p["chain"] == "solana" else [sys.executable, "-m", "memelab", "chains", "analyze", p["chain"], p["addr"], "--results", i]
    o = subprocess.run(cmd, capture_output=True, text=True); line = (o.stdout.strip().splitlines() or ["(no output) " + o.stderr[-200:]])[0]; print(line); summary.append(line)
if a.catalyst:
    cid = "cat_" + a.catalyst; mid = "catm_" + a.catalyst
    def sh(*args): return subprocess.run([sys.executable, "-m", "memelab", *args], capture_output=True, text=True)
    def run_plan(out, pid, *planargs):
        o = sh(*planargs, "--id", pid).stdout.splitlines()
        line = next(l for l in o if l.startswith("await __ML.run("))
        node_run(json.loads(line[len("await __ML.run("):-1]), INBOX / f"{out}.result.json")
    run_plan(cid, cid, "catalyst", "plan"); print(sh("catalyst", "ingest", "--results", cid).stdout[-300:])
    run_plan(mid, mid, "catalyst", "match-plan"); print(sh("catalyst", "match", "--results", mid).stdout[-200:])
    sh("catalyst", "assess", "--persist"); print(sh("catalyst", "monitor").stdout[-1500:]); print(sh("catalyst", "report").stdout[-200:])
if a.eco:
    o = subprocess.run([sys.executable, "-m", "memelab", "chains", "plan", "eco", "--id", a.eco], capture_output=True, text=True); print(o.stdout)
    pl = json.load(open(INBOX / f"{a.eco}.plan.json")); res = INBOX / f"{a.eco}.result.json"; node_run(pl, res); retry_failed(pl, res)
    print(subprocess.run([sys.executable, "-m", "memelab", "chains", "eco", "--results", a.eco], capture_output=True, text=True).stdout[-400:])
print("\n".join(subprocess.run([sys.executable, "-m", "memelab", "watchlist"], capture_output=True, text=True).stdout.splitlines()))

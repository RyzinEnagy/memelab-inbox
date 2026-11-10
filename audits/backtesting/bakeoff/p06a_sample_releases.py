import json, time, urllib.request, sys, hashlib, os
OUT = r"D:\memelab\backtesting_work\p06a"
os.makedirs(OUT, exist_ok=True)
UA = "memelab-research/0.1 (one-shot bake-off; contact via repo owner)"
def get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(), t
    except urllib.error.HTTPError as e:
        return e.code, e.read(), t
log = []
st, body, t = get("https://github.com/robots.txt", "text/plain")
open(os.path.join(OUT, "github_robots.txt"), "wb").write(body)
log.append({"url": "https://github.com/robots.txt", "status": st, "t": t, "sha256": hashlib.sha256(body).hexdigest()})
REPOS = ["anza-xyz/agave", "solana-foundation/anchor", "orca-so/whirlpools", "helius-labs/helius-sdk", "jito-foundation/jito-solana",
         "solana-program/token-2022", "metaplex-foundation/mpl-token-metadata", "anza-xyz/kit", "raydium-io/raydium-sdk-V2", "jup-ag/jupiter-swap-api-client"]
rel = {}
for r in REPOS:
    time.sleep(1.5)
    st, body, t = get(f"https://api.github.com/repos/{r}/releases?per_page=1")
    log.append({"url": f"https://api.github.com/repos/{r}/releases?per_page=1", "status": st, "t": t, "sha256": hashlib.sha256(body).hexdigest()})
    try:
        d = json.loads(body)
        x = d[0] if isinstance(d, list) and d else None
    except Exception:
        x = None
    rel[r] = None if x is None else {k: x.get(k) for k in ("html_url", "tag_name", "name", "published_at", "created_at", "prerelease", "draft", "id", "updated_at")}
json.dump({"retrieved_at": time.time(), "releases": rel, "log": log}, open(os.path.join(OUT, "gh_releases.json"), "w"), indent=1)
print(json.dumps(rel, indent=1))

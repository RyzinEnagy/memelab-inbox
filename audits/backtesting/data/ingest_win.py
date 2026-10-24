import json, sys
sys.path.insert(0, '/home/claude/work/memelab-inbox')
from pathlib import Path
from memelab.backtest import store
from memelab.backtest.sources import corpus, gecko
W = Path('/home/claude/work/scratch/gtwin')
man = []
for l in (W / 'gt_manifest.jsonl').read_text().splitlines():
    try:
        man.append(json.loads(l))
    except Exception:
        pass
ok = {}
for r in man:
    if r['status'] == 200 and r['file']:
        ok[r['url']] = r          # last successful response per URL
def replay(url, timeout=30.0):
    r = ok.get(url)
    if not r:
        return 404, b''
    return 200, (W / 'gt_raw' / r['file']).read_bytes()
con = store.connect()
b = gecko.Budget(max_calls=10_000, min_spacing_s=0.0)
stats = {"mints_seen": 0, "skipped_already": 0, "ingested": 0, "pools_fetched": 0, "bars_new": 0}
order = []
for r in man:
    if r['kind'] == 'pools' and r['status'] == 200 and r['mint'] not in order:
        order.append(r['mint'])
for m in order:
    stats["mints_seen"] += 1
    if corpus.already_fetched(con, m):
        stats["skipped_already"] += 1
        continue
    pr = [r for r in man if r['kind'] == 'pools' and r['mint'] == m and r['status'] == 200][-1]
    res = gecko.fetch_pools(con, m, b, replay, observed_at=pr['observed_at'])
    con.commit()
    for o in [r for r in man if r['kind'] == 'ohlcv' and r['mint'] == m and r['status'] == 200]:
        x = gecko.fetch_ohlcv(con, m, o['pool'], b, replay, observed_at=o['observed_at'])
        con.commit()
        stats["pools_fetched"] += 1
        stats["bars_new"] += x.get("bars", 0)
    stats["ingested"] += 1
stats["manifest_lines"] = len(man)
stats["http_status"] = {}
for r in man:
    stats["http_status"][str(r['status'])] = stats["http_status"].get(str(r['status']), 0) + 1
print(json.dumps(stats))

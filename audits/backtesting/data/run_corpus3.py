import json, sys
sys.path.insert(0, '/home/claude/work/memelab-inbox')
from pathlib import Path
from memelab.backtest import store
from memelab.backtest.sources import corpus, gecko
con = store.connect()
d = json.load(open('/home/claude/work/scratch/latest_main.json'))['_tables']
lab_pools = {t['mint']: t.get('graduated_pool') for t in d['tokens'] if t.get('graduated_pool')}
mints = list(reversed(json.load(open('/home/claude/work/scratch/mints_windows.json'))))
stop = Path('/home/claude/work/scratch/STOP3')
def hg(url, timeout=30.0):
    if stop.exists():
        raise gecko.BudgetExhausted('stop file')
    return gecko.default_http_get(url, timeout)
b = gecko.Budget(max_calls=900, min_spacing_s=4.0)
st = corpus.build(con, mints, b, lab_pools=lab_pools, log_path=Path('/home/claude/work/scratch/corpus_log3.jsonl'), k_pools=1, http_get=hg)
print(json.dumps(st), flush=True)

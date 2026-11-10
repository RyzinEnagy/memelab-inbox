import json, sys
sys.path.insert(0, '/home/claude/work/memelab-inbox')
from pathlib import Path
from memelab.backtest import store
from memelab.backtest.sources import corpus, gecko
con = store.connect()
d = json.load(open('/home/claude/work/scratch/latest_main.json'))['_tables']
lab_pools = {t['mint']: t.get('graduated_pool') for t in d['tokens'] if t.get('graduated_pool')}
mints = json.load(open('/home/claude/work/scratch/mints_container.json'))
b = gecko.Budget(max_calls=900, min_spacing_s=4.0)
st = corpus.build(con, mints, b, lab_pools=lab_pools, log_path=Path('/home/claude/work/scratch/corpus_log.jsonl'), k_pools=1)
print(json.dumps(st), flush=True)

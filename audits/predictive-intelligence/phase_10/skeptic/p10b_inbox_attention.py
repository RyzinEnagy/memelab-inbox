"""Phase 10 skeptic (10b): DEX Screener boosts and token profiles, and CEX listing
lists, in every tracked inbox read on origin/main, matched to decision mints by exact
tokenAddress (chain solana), with the file's first commit as availability.
The phase cross-checked only inbox/cat01*.json and catm01.json.
usage: p10b_inbox_attention.py REPO REF DEV_STORE_COPY"""
import json, sqlite3, subprocess, sys, collections
REPO, REF, DEV = sys.argv[1:4]
def git(*a): return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
c = sqlite3.connect(DEV)
dec = collections.defaultdict(list)
for mint, t in c.execute("select mint, decision_time from predictive_decisions"): dec[mint].append(t)
files = [f for f in git('ls-tree', '-r', '--name-only', REF).decode().split('\n') if f.startswith(('inbox/', 'data/inbox/')) and f.endswith('.json')]
hits = collections.defaultdict(lambda: collections.defaultdict(set))   # kind -> file -> mints
def walk(x, key, f):
    if isinstance(x, dict):
        ta = x.get('tokenAddress')
        if ta in dec and key:
            kind = 'boost' if 'boost' in key else ('profile' if 'profile' in key else None)
            if kind: hits[kind][f].add(ta)
        for k, v in x.items(): walk(v, k if ('ds_' in k or 'boost' in k or 'profile' in k) else key, f)
    elif isinstance(x, list):
        for v in x: walk(v, key, f)
first = {}
for f in files:
    try: d = json.loads(git('show', f'{REF}:{f}'))
    except Exception: continue
    first[f] = float(git('log', '--reverse', '--format=%ct', REF, '--', f).decode().split()[0])
    walk(d, None, f)
summary = {}
for kind, byf in hits.items():
    mints = set().union(*byf.values())
    dec_after = sum(1 for m in mints for t in dec[m] if t >= min(first[f] for f in byf if m in byf[f]))
    summary[kind] = {'files': {f: len(v) for f, v in byf.items()}, 'distinct_decision_mints': len(mints),
                     'decisions_at_or_after_first_sighting': dec_after}
print(json.dumps(summary, indent=1))

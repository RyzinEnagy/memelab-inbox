"""Phase 10 skeptic (10b): Solana decisions whose OWN export holds an upcoming_launches row
for the same mint with official links (twitter/telegram/website) the token row lacks.
usage: p10b_launch_channels.py REPO P05_COPY"""
import json, sqlite3, subprocess, sys, collections
REPO, P05 = sys.argv[1:3]
def git(*a): return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
c = sqlite3.connect(P05); cache = {}; out = collections.Counter(); ex = []
for dk, mint, ec, tj in c.execute("select decision_key, mint, export_commit, token_json from predictive_decisions where chain='solana'"):
    if ec not in cache:
        d = json.loads(git('show', f'{ec}:data/state/latest.json')); d = d.get('_tables', d)
        cache[ec] = {r.get('contract'): r for r in d.get('upcoming_launches', []) or []}
    r = cache[ec].get(mint)
    if not r: continue
    out['decisions_with_launch_row_in_own_export'] += 1
    links = json.loads(r.get('official_links_json') or '{}'); tok = json.loads(tj) if tj else {}
    for k in ('twitter', 'telegram', 'website'):
        if links.get(k) and not (tok.get(k) or '').strip():
            out[f'{k}_only_in_launch_row'] += 1
    if json.loads(r.get('social_json') or '{}').get('ds_profile'): out['ds_profile_flag'] += 1
print(dict(out))

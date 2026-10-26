"""Phase 10 skeptic (10b): do any social-like or catalyst-like rows exist for any
development decision, available (committed on origin/main) at or before the decision?
Sources scanned: every version of data/state/latest.json (upcoming_launches social_json /
official_links_json, launch_monitor, launch_cohort), tracked data/memelab.sqlite
social_snapshots, and every tracked inbox / data/inbox JSON file (exact mint substring).
Read only: git show, copies of stores.
usage: p10b_rows_scan.py REPO REF DEV_STORE_COPY OUT_JSON"""
import json, sqlite3, subprocess, sys, collections, datetime as dt, tempfile, os
REPO, REF, DEV, OUT = sys.argv[1:5]
def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
def iso(t): return dt.datetime.fromtimestamp(t, dt.UTC).isoformat()
c = sqlite3.connect(DEV)
dec = collections.defaultdict(list)
for mint, t, ch in c.execute('select mint, decision_time, chain from predictive_decisions'):
    dec[mint].append(t)
res = {'n_decisions': sum(len(v) for v in dec.values()), 'n_mints': len(dec)}
# 1. launch tables in every export version, first commit where a row names a decision mint
first_launch = {}   # mint -> (commit_time, table, fields)
log = git('log', '--reverse', '--format=%H %ct', REF, '--', 'data/state/latest.json').decode().split('\n')
for line in filter(None, log):
    h, ct = line.split(); ct = float(ct)
    try: tabs = json.loads(git('show', f'{h}:data/state/latest.json')).get('_tables', {})
    except Exception: continue
    for r in tabs.get('upcoming_launches', []) or []:
        m = r.get('contract')
        if m in dec and ('upcoming_launches', m) not in first_launch:
            first_launch[('upcoming_launches', m)] = (ct, h, r.get('social_json'), r.get('official_links_json'), r.get('discovered_at'))
    for r in tabs.get('launch_monitor', []) or []:
        m = (r.get('launch_id') or '').split(':', 1)[-1]
        if m in dec and ('launch_monitor', m) not in first_launch:
            first_launch[('launch_monitor', m)] = (ct, h, None, None, r.get('observed_at'))
    for r in tabs.get('launch_cohort', []) or []:
        m = r.get('mint')
        if m in dec and ('launch_cohort', m) not in first_launch:
            first_launch[('launch_cohort', m)] = (ct, h, None, None, r.get('first_seen_at'))
lt = collections.Counter(); before = collections.Counter(); ex = {}
for (tab, m), (ct, h, sj, ol, obs) in first_launch.items():
    lt[tab] += 1
    nb = sum(1 for t in dec[m] if ct <= t)
    if nb:
        before[tab] += nb
        ex.setdefault(tab, []).append({'mint': m, 'first_commit': h[:9], 'commit_time': iso(ct),
            'decisions_at_or_after': nb, 'social_json': sj, 'official_links_json': ol,
            'row_time': iso(obs) if obs else None})
res['launch_tables'] = {'mints_named': dict(lt), 'decisions_with_row_committed_before': dict(before), 'examples': {k: v[:5] for k, v in ex.items()}}
# 2. tracked memelab.sqlite social_snapshots
tmp = tempfile.mkdtemp(); p = os.path.join(tmp, 'm.sqlite')
open(p, 'wb').write(git('show', f'{REF}:data/memelab.sqlite'))
ct = float(git('log', '-1', '--format=%ct', REF, '--', 'data/memelab.sqlite').decode())
m = sqlite3.connect(p)
ss = {}
for mint, n, lo, hi, metrics in m.execute("select mint, count(*), min(observed_at), max(observed_at), group_concat(distinct metric) from social_snapshots group by mint"):
    ss[mint] = {'rows': n, 'observed_min': iso(lo), 'observed_max': iso(hi), 'metrics': metrics,
                'decisions': len(dec.get(mint, [])), 'decisions_after_commit': sum(1 for t in dec.get(mint, []) if t >= ct),
                'min_gap_hours': round((min(dec[mint]) - hi) / 3600, 2) if mint in dec else None}
res['memelab_sqlite_social_snapshots'] = {'commit_time': iso(ct), 'by_mint': ss,
    'decisions_covered': sum(v['decisions'] for v in ss.values())}
# 3. inbox files: exact mint substring, file first commit on REF
files = [f for f in git('ls-tree', '-r', '--name-only', REF).decode().split('\n') if f.startswith(('inbox/', 'data/inbox/')) and f.endswith('.json')]
inbox = {}
for f in files:
    body = git('show', f'{REF}:{f}').decode('utf8', 'replace')
    fc = float(git('log', '--reverse', '--format=%ct', REF, '--', f).decode().split()[0])
    hit = [mm for mm in dec if mm in body]
    if hit:
        inbox[f] = {'first_commit': iso(fc), 'decision_mints_named': len(hit),
                    'decisions_after_first_commit': sum(1 for mm in hit for t in dec[mm] if t >= fc)}
res['inbox_files_naming_decision_mints'] = inbox
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps({k: (v if k != 'memelab_sqlite_social_snapshots' else {'decisions_covered': v['decisions_covered']}) for k, v in res.items() if k != 'launch_tables'}, indent=1))
print(json.dumps({k: res['launch_tables'][k] for k in ('mints_named', 'decisions_with_row_committed_before')}))

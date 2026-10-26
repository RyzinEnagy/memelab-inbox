"""Phase 10 skeptic (10b): independent re-derivation of socialcat-1 coverage numbers
from git objects, without memelab.predictive code.
 (a) each Solana decision's stored token row equals the token row of its own export commit (CX-10)
 (b) channel and narrative-tag counts at the decision vs at the newest export
 (c) m19 attention trend coverage from the thesis rationale lines (own regex)
usage: p10b_rederive.py REPO P05_COPY NEWEST_REF"""
import json, sqlite3, subprocess, sys, re, collections
REPO, P05, NEW = sys.argv[1:4]
def git(*a): return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
c = sqlite3.connect(P05)
rows = c.execute("select decision_key, mint, decision_time, export_commit, export_blob, token_json, row_json from predictive_decisions where chain='solana'").fetchall()
cache = {}
def export(commit):
    if commit not in cache:
        blob = git('rev-parse', f'{commit}:data/state/latest.json').decode().strip()
        ct = float(git('log', '-1', '--format=%ct', commit).decode())
        d = json.loads(git('cat-file', 'blob', blob))
        cache[commit] = (blob, ct, {t['mint']: t for t in d.get('_tables', d)['tokens']})
    return cache[commit]
newest = export(git('rev-parse', NEW).decode().strip())[2]
eq = blob_eq = time_eq = 0; diffs = []
def chan(t, k):
    v = (t or {}).get(k)
    return isinstance(v, str) and v.strip() not in ('', 'None', 'null', 'NULL')
cnt = collections.Counter(); gain = collections.Counter()
trend = collections.Counter()
rx = re.compile(r'^attention trend (\w+)')
for dk, mint, T, ec, eb, tj, rj in rows:
    blob, ct, toks = export(ec)
    blob_eq += blob == eb; time_eq += ct == T
    tok = json.loads(tj) if tj else None
    if toks.get(mint) == tok: eq += 1
    else: diffs.append(dk[:12])
    for k in ('website', 'twitter', 'telegram', 'narrative_id'):
        a, b = chan(tok, k), chan(newest.get(mint), k)
        cnt[k] += a; gain[k] += (b and not a)
    bd = json.loads(json.loads(rj).get('score_breakdown_json') or 'null')
    if not isinstance(bd, dict) or 'attention_narrative' not in bd: trend['no_bucket'] += 1; continue
    lines = bd['attention_narrative'].get('rationale') or []
    m = next((rx.match(s) for s in lines if rx.match(s)), None)
    if m: trend['trend_' + m.group(1)] += 1
    elif any(s.startswith('UNKNOWN: attention trend') for s in lines): trend['unknown'] += 1
    else: trend['other'] += 1
print(json.dumps({'solana_decisions': len(rows), 'token_row_equals_own_export': eq, 'blob_equal': blob_eq,
  'commit_time_equal_decision_time': time_eq, 'token_row_diffs': diffs[:5], 'channels_at_decision': cnt,
  'would_gain_if_newest_export_read': gain, 'trend_lines': trend}, indent=1))

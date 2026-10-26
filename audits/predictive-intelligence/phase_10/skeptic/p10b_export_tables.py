"""Phase 10 skeptic (10b): every table name and row count in every version of the
state exports on the inbox's origin/main, to test the claim that no social or
catalyst table is ever exported. Read only (git show)."""
import json, subprocess, sys, collections
REPO = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/memelab-inbox'
REF = sys.argv[2] if len(sys.argv) > 2 else 'origin/main'
def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
out = {}
for path in ('data/state/latest.json', 'state/latest.json'):
    commits = git('log', '--format=%H %cI', REF, '--', path).decode().split('\n')
    seen = collections.defaultdict(lambda: [0, None, None, 0])
    for line in filter(None, commits):
        h, t = line.split()
        try:
            d = json.loads(git('show', f'{h}:{path}'))
        except Exception as e:
            continue
        tabs = d.get('_tables', d)
        for k, v in tabs.items():
            if isinstance(v, list):
                s = seen[k]; s[0] += 1; s[3] = max(s[3], len(v))
                s[1] = t if s[1] is None or t < s[1] else s[1]
                s[2] = t if s[2] is None or t > s[2] else s[2]
    out[path] = {k: {'versions': v[0], 'first': v[1], 'last': v[2], 'max_rows': v[3]} for k, v in sorted(seen.items())}
json.dump(out, sys.stdout, indent=1)

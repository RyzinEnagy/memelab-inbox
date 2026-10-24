"""Size of a distribution's declared runtime dependency closure inside the current environment (Phase 03 lead).

Usage: <venv python> -I closure_size.py <distribution name>
Walks importlib.metadata requires (markers evaluated, extras ignored) and sums the files listed in each RECORD.
Prints JSON: closure size in MB, member count, and members missing from the environment.
"""
import json, os, re, sys
from importlib import metadata

def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()

def reqs(dist):
    out = []
    for r in dist.requires or []:
        name, _, marker = r.partition(";")
        if marker and "extra" in marker:
            continue
        if marker:
            try:
                from packaging.markers import Marker
                if not Marker(marker.strip()).evaluate():
                    continue
            except Exception:
                pass
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", name)
        if m:
            out.append(norm(m.group(1)))
    return out

dists = {norm(d.metadata["Name"]): d for d in metadata.distributions()}
root = norm(sys.argv[1]); seen, missing, stack = set(), [], [root]
while stack:
    n = stack.pop()
    if n in seen:
        continue
    seen.add(n)
    d = dists.get(n)
    if d is None:
        missing.append(n); continue
    stack.extend(reqs(d))
size = 0
for n in seen:
    d = dists.get(n)
    if d is None or not d.files:
        continue
    for f in d.files:
        p = d.locate_file(f)
        try:
            size += os.path.getsize(p)
        except OSError:
            pass
print(json.dumps({"root": root, "closure_mb": round(size / 1e6, 1), "members": sorted(seen - set(missing)), "missing": sorted(missing)}))

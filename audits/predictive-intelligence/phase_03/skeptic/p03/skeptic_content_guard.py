"""Skeptic P03: run the repository's own content guard (memelab.social.content_guard.scan) on a checkout and print
the violations. Usage: cd <checkout> && python3 -B <this> ."""
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from memelab.social import content_guard as G
out = G.scan(Path(sys.argv[1]).resolve())
print("violations", len(out["violations"]))
for v in out["violations"]:
    print(" ", v["path"], v.get("where"), v["rule"])

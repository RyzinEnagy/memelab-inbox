"""Fetch each candidate's pinned commit (blob-less) so the build can read files at the pin.

Usage: python fetch_pins.py PHASE02_DIR CLONE_ROOT [--workers N]

For every candidate in research/CANDIDATE_ANNOTATIONS.csv, the pin is taken
from research/VERIFY_RESULTS.jsonl; CLONE_ROOT/<owner>__<name> gets
`git init` and `git fetch --depth 1 --filter=blob:none <url> <pin>` unless
the pinned commit is already present. Blobs are fetched lazily when the
build reads a file. Nothing is checked out, installed or executed.
"""
import concurrent.futures as cf
import csv
import json
import os
import subprocess
import sys


def main(argv):
    workers = 6
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    base, root = argv[1], argv[2]
    R = os.path.join(base, "research")
    ann = [r["canonical"] for r in csv.DictReader(open(os.path.join(R, "CANDIDATE_ANNOTATIONS.csv")))]
    pins = {}
    for l in open(os.path.join(R, "VERIFY_RESULTS.jsonl")):
        v = json.loads(l)
        name = (v.get("canonical") or v["input"]).lower()
        if v.get("pinned_sha") and (name not in pins or v["input"].lower() == name):
            pins[name] = v["pinned_sha"]

    def one(c):
        pin = pins.get(c.lower())
        if not pin:
            return c, "NO PIN"
        d = os.path.join(root, c.replace("/", "__"))
        if os.path.isdir(d) and subprocess.run(["git", "-C", d, "cat-file", "-e", pin + "^{commit}"],
                                               capture_output=True).returncode == 0:
            return c, "present"
        subprocess.run(["rm", "-rf", d])
        subprocess.run(["git", "init", "-q", d], check=True)
        p = subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", "--filter=blob:none",
                            "https://github.com/" + c, pin], capture_output=True, text=True, timeout=1200)
        return c, "fetched" if p.returncode == 0 else "FAILED " + p.stderr.strip()[-120:]

    os.makedirs(root, exist_ok=True)
    bad = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for c, st in ex.map(one, ann):
            if st not in ("present", "fetched"):
                bad += 1
                print(c, st)
    print("candidates", len(ann), "problems", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Root commits of repositories, to detect forks and mirrors inside a candidate set.

Usage:
  python root_commits.py REPOS.txt OUT_JSONL WORK_DIR [--workers N]

For each `owner/name`: a treeless bare clone (`--filter=tree:0`, commit
history only, no file contents), its HEAD, its root commit(s) from
`git rev-list --max-parents=0 HEAD` and its commit count; the clone is then
deleted. Two repositories that share a root commit share history (one is a
fork, mirror or re-upload of the other, or both split from a common
ancestor), which the candidate checker refuses unless an exclusion
explains it.
"""
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def one(repo, work):
    d = os.path.join(work, repo.replace("/", "__") + ".git")
    shutil.rmtree(d, ignore_errors=True)
    rec = {"repo": repo, "started_at": utc_now()}
    p = subprocess.run(["git", "clone", "-q", "--bare", "--filter=tree:0", "https://github.com/%s" % repo, d],
                       capture_output=True, text=True, timeout=1800)
    rec["clone_exit"] = p.returncode
    if p.returncode == 0:
        run = lambda *a: subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True).stdout.strip()
        rec["head"] = run("rev-parse", "HEAD")
        rec["roots"] = sorted(run("rev-list", "--max-parents=0", "HEAD").split())
        rec["commit_count"] = int(run("rev-list", "--count", "HEAD") or 0)
        rec["root_commit_dates"] = sorted(run("log", "--max-parents=0", "--format=%cI", "HEAD").split())
    else:
        rec["error"] = p.stderr.strip()[-200:]
    shutil.rmtree(d, ignore_errors=True)
    rec["finished_at"] = utc_now()
    return rec


def main(argv):
    workers = 6
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    repos_file, out, work = argv[1:4]
    os.makedirs(work, exist_ok=True)
    repos = [l.split("#")[0].strip() for l in open(repos_file)]
    repos = [r for r in repos if r]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for rec in ex.map(lambda r: one(r, work), repos):
            with open(out, "a") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
            print(rec["repo"], rec.get("clone_exit"), rec.get("commit_count"), (rec.get("roots") or [""])[0][:10])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

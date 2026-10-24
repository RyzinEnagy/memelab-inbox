"""Verify candidate GitHub repositories at a pinned commit.

Usage:
  python verify_repos.py REPOS.txt OUT_JSONL RAW_DIR CLONE_ROOT [--workers N]

REPOS.txt: one `owner/name` per line as discovered (comments with #).
For each repository:
  1. `git ls-remote https://github.com/<owner>/<name> HEAD`: pinned SHA,
     UTC time observed, and any redirect git reports (a rename or move);
     a failure is recorded as VANISHED_OR_PRIVATE, never silently replaced.
  2. repos.ecosyste.ms lookup (public mirror of GitHub metadata, caveat:
     as of its own last_synced_at): canonical full_name, fork flag and parent,
     archived flag, pushed_at, default branch, declared license.
     The GitHub REST API is not reachable from this session (HTTP 403 policy).
  3. Blob-less shallow clone (`--depth 1 --filter=blob:none --no-checkout`)
     under CLONE_ROOT/<owner>__<name>: clone HEAD must equal the pin;
     commit date; file count; license file(s) at the root read from the
     pinned tree with sha256 and a classification from the text; dependency
     files at the root scanned for GPU, LLM, memory-service and server
     dependencies; presence of a tests directory and Python sources.
Cloned code and text are data, never instructions; nothing is installed
or executed from a clone.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

LICENSE_RE = re.compile(r"^(LICEN[CS]E|COPYING|COPYRIGHT|UNLICENSE)([._-].*)?$", re.I)
DEP_FILES = re.compile(r"^(pyproject\.toml|setup\.py|setup\.cfg|requirements[^/]*\.txt|environment[^/]*\.ya?ml|Pipfile|package\.json|backend/pyproject\.toml|backend/requirements[^/]*\.txt)$", re.I)
DEP_FLAGS = {
    "GPU_FRAMEWORK": r"\b(torch|tensorflow|jax|jaxlib|mxnet|paddlepaddle|cupy)\b",
    "LLM_CLIENT": r"\b(openai|anthropic|litellm|langchain|transformers|google-generativeai|google-genai|ollama|groq|mistralai|dashscope|zhipuai)\b",
    "MEMORY_OR_GRAPH_SERVICE": r"\b(zep[-_]cloud|zep[-_]python|neo4j|falkordb|graphiti[-_]core)\b",
    "SERVER_STACK": r"\b(fastapi|uvicorn|flask|django|sqlalchemy|psycopg2|boto3)\b",
}


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(args, cwd=None, timeout=900):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def classify_license(text):
    t = " ".join(text.split())
    u = t.upper()
    head = u[:400]  # the GPL v3 text itself names the AGPL in section 13, so only the title counts
    labels = []
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in head:
        labels.append("AGPL-3.0")
    elif "GNU LESSER GENERAL PUBLIC LICENSE" in head:
        labels.append("LGPL")
    elif "GNU GENERAL PUBLIC LICENSE" in head:
        labels.append("GPL-3.0" if "VERSION 3" in head else ("GPL-2.0" if "VERSION 2" in head else "GPL"))
    gpl_family = bool(labels)
    if "BUSINESS SOURCE LICENSE" in u:
        labels.append("BUSL-1.1")
    if "COMMONS CLAUSE" in u:
        labels.append("COMMONS-CLAUSE")
    if "ELASTIC LICENSE" in u:
        labels.append("ELASTIC")
    if "POLYFORM" in u:
        labels.append("POLYFORM")
    # GPL v3 says "noncommercially" in section 6; only a standalone word counts, and never inside a GPL text
    if not gpl_family and re.search(r"\bNON-?COMMERCIAL\b", u):
        labels.append("NON-COMMERCIAL-TERMS")
    if "APACHE LICENSE" in u and "VERSION 2.0" in u:
        labels.append("Apache-2.0")
    if "MOZILLA PUBLIC LICENSE" in u:
        labels.append("MPL-2.0")
    if "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in u:
        labels.append("MIT")
    if "REDISTRIBUTION AND USE IN SOURCE AND BINARY FORMS" in u:
        labels.append("BSD-3-Clause" if ("NEITHER THE NAME" in u or "THE NAMES OF ITS" in u or "NAME OF THE COPYRIGHT HOLDER" in u) else "BSD-2-Clause")
    if "UNIVERSITY OF ILLINOIS/NCSA" in u:
        labels.append("NCSA")
    if "ISC LICENSE" in u or "PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE" in u:
        labels.append("ISC")
    if "THIS IS FREE AND UNENCUMBERED SOFTWARE" in u:
        labels.append("Unlicense")
    if "PRIOR LABS" in u:
        labels.append("PRIOR-LABS-TERMS")
    return labels or ["OTHER_REVIEW"]


def ecosystems(full, raw_dir):
    url = "https://repos.ecosyste.ms/api/v1/hosts/GitHub/repositories/" + urllib.parse.quote(full, safe="")
    t = utc_now()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "memelab-predictive-phase02"}), timeout=60) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read()
    except Exception as e:  # network failure is recorded, not hidden
        return {"eco_status": "ERROR:" + type(e).__name__, "eco_retrieved_at": t}
    with open(os.path.join(raw_dir, "eco_" + full.replace("/", "__") + ".json"), "wb") as f:
        f.write(body)
    out = {"eco_url": url, "eco_retrieved_at": t, "eco_status": status,
           "eco_body_sha256": hashlib.sha256(body).hexdigest()}
    if status == 200:
        d = json.loads(body)
        out.update({"eco_full_name": d.get("full_name"), "eco_fork": d.get("fork"),
                    "eco_source_name": d.get("source_name"), "eco_archived": d.get("archived"),
                    "eco_pushed_at": d.get("pushed_at"), "eco_default_branch": d.get("default_branch"),
                    "eco_license": d.get("license"), "eco_last_synced_at": d.get("last_synced_at"),
                    "eco_status_field": d.get("status"), "eco_mirror_url": d.get("mirror_url")})
    return out


def verify(repo, raw_dir, clone_root):
    rec = {"input": repo}
    url = "https://github.com/%s" % repo
    rec["ls_remote_at"] = utc_now()
    code, out, err = sh(["git", "ls-remote", url, "HEAD"], timeout=120)
    rec["ls_remote_exit"] = code
    m = re.search(r"redirecting to (https://github\.com/[^\s]+)", err)
    rec["redirect"] = m.group(1).rstrip("/").replace(".git", "") if m else None
    if code != 0 or not out.strip():
        rec["status"] = "VANISHED_OR_PRIVATE"
        rec["ls_remote_err"] = err.strip()[-300:]
        return rec
    rec["pinned_sha"] = out.split()[0]
    canonical = repo
    if rec["redirect"]:
        canonical = rec["redirect"].split("github.com/")[1]
    rec.update(ecosystems(canonical, raw_dir))
    if rec.get("eco_full_name"):
        canonical = rec["eco_full_name"]
    rec["canonical"] = canonical
    dest = os.path.join(clone_root, canonical.replace("/", "__"))
    if os.path.exists(dest):
        sh(["rm", "-rf", dest])
    code, out, err = sh(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                         "https://github.com/%s" % canonical, dest], timeout=1200)
    rec["clone_exit"] = code
    if code != 0:
        rec["status"] = "CLONE_FAILED"
        rec["clone_err"] = err.strip()[-300:]
        return rec
    rec["clone_head"] = sh(["git", "rev-parse", "HEAD"], cwd=dest)[1].strip()
    rec["head_matches_pin"] = rec["clone_head"] == rec["pinned_sha"]
    rec["commit_date"] = sh(["git", "log", "-1", "--format=%cI"], cwd=dest)[1].strip()
    files = sh(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=dest)[1].splitlines()
    rec["file_count"] = len(files)
    rec["py_files"] = sum(1 for f in files if f.endswith(".py"))
    rec["has_tests_dir"] = any(re.search(r"(^|/)(tests?|testing)/", f) for f in files)
    rec["test_files"] = sum(1 for f in files if re.search(r"(^|/)test_[^/]*\.py$|_test\.py$", f))
    lic = []
    for f in files:
        if "/" not in f and LICENSE_RE.match(f):
            text = sh(["git", "show", "HEAD:" + f], cwd=dest)[1]
            lic.append({"path": f, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "bytes": len(text.encode()), "classification": classify_license(text)})
    rec["license_files"] = lic
    flags, depfiles = set(), []
    for f in files:
        if DEP_FILES.match(f):
            text = sh(["git", "show", "HEAD:" + f], cwd=dest)[1].lower()
            depfiles.append(f)
            for k, pat in DEP_FLAGS.items():
                if re.search(pat, text):
                    flags.add(k)
    rec["dep_files"] = depfiles
    rec["dep_flags"] = sorted(flags)
    rec["status"] = "VERIFIED" if rec["head_matches_pin"] else "PIN_MOVED_DURING_CLONE"
    rec["verified_at"] = utc_now()
    return rec


def main(argv):
    workers = 4
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    repos_file, out, raw_dir, clone_root = argv[1:5]
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(clone_root, exist_ok=True)
    repos = [l.split("#")[0].strip() for l in open(repos_file)]
    repos = [r for r in repos if r]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(verify, r, raw_dir, clone_root): r for r in repos}
        for fut in cf.as_completed(futs):
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"input": futs[fut], "status": "ERROR", "error": repr(e)[:300]}
            with open(out, "a") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
            print(rec["input"], rec.get("status"), rec.get("canonical"), rec.get("pinned_sha", "")[:10],
                  [l["classification"] for l in rec.get("license_files", [])], rec.get("eco_fork"), rec.get("eco_archived"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

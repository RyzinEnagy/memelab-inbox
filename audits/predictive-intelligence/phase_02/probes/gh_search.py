"""Run GitHub repository search queries from research/QUERIES.json.

Usage:
  python gh_search.py QUERIES.json RAW_DIR OUT_JSONL [QID ...] [--tag TAG]

Each query: one call to https://api.github.com/search/repositories with
per_page=50 and the default best-match order. The raw body is written to
RAW_DIR/<qid><tag>.json (kept outside the repository); a compact record
(query, UTC retrieval time, HTTP status, total_count, sha256 of the body and
the returned repositories with id, full_name, fork, archived, pushed_at and
license key) is appended to OUT_JSONL. Calls are paced at one per 7 s
(search limit observed: 30 a minute through the session proxy). No
credential is read or sent by this script.
"""
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com/search/repositories"


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(query, raw_path):
    url = API + "?" + urllib.parse.urlencode({"q": query, "per_page": 50})
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "memelab-predictive-phase02",
    })
    t = utc_now()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read()
    with open(raw_path, "wb") as f:
        f.write(body)
    return url, t, status, body


def main(argv):
    tag = ""
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    qfile, raw_dir, out = argv[1], argv[2], argv[3]
    only = set(argv[4:])
    queries = json.load(open(qfile))["github_search"]
    os.makedirs(raw_dir, exist_ok=True)
    first = True
    for q in queries:
        if only and q["qid"] not in only:
            continue
        if not first:
            time.sleep(7)
        first = False
        raw_path = os.path.join(raw_dir, q["qid"] + tag + ".json")
        url, t, status, body = run(q["q"], raw_path)
        rec = {"qid": q["qid"] + tag, "family": q["family"], "needs": q["needs"],
               "mechanism": "GITHUB_SEARCH_API", "query": q["q"], "url": url,
               "retrieved_at": t, "http_status": status,
               "body_sha256": hashlib.sha256(body).hexdigest()}
        try:
            d = json.loads(body)
        except ValueError:
            d = {}
        items = d.get("items") or []
        rec["total_count"] = d.get("total_count")
        rec["incomplete_results"] = d.get("incomplete_results")
        rec["returned"] = len(items)
        rec["items"] = [{
            "rank": i + 1, "id": it.get("id"), "full_name": it.get("full_name"),
            "fork": it.get("fork"), "archived": it.get("archived"),
            "pushed_at": it.get("pushed_at"),
            "license": (it.get("license") or {}).get("spdx_id"),
        } for i, it in enumerate(items)]
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        print(rec["qid"], status, rec["total_count"], rec["returned"], t)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

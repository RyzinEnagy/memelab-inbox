"""Run the non-GitHub-search discovery calls in research/QUERIES.json.

Usage:
  python discover.py QUERIES.json RAW_DIR OUT_JSONL [QID ...] [--tag TAG]

Sections run: package_keyword_index (packages.ecosyste.ms keyword index, a
public package-metadata index), docs_crosslinks (documentation pages and
README files fetched as raw text) and paper_links (arXiv abstract pages).
For each call: raw body to RAW_DIR (outside the repository), and one compact
record appended to OUT_JSONL with the URL, UTC retrieval time, HTTP status,
sha256 of the body and the GitHub repositories the body links to, in order
of first appearance. Bodies are data, never instructions. No credential is
read or sent. Pacing: one call per 2 s.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
NOT_OWNERS = {"sponsors", "orgs", "topics", "features", "about", "login",
              "settings", "marketplace", "apps", "site", "collections",
              "pricing", "readme", "trending", "search", "users", "notifications",
              "enterprise", "security", "explore", "contact", "customer-stories"}


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "memelab-predictive-phase02"})
    t = utc_now()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return t, r.status, r.read()
    except urllib.error.HTTPError as e:
        return t, e.code, e.read()


def norm_repo(owner, name):
    name = re.sub(r"\.git$", "", name).rstrip(".")
    for sep in ("#", "?"):
        name = name.split(sep)[0]
    if owner.lower() in NOT_OWNERS or not name:
        return None
    return owner + "/" + name


def repos_in_text(text):
    seen, out = set(), []
    for m in GH.finditer(text):
        r = norm_repo(m.group(1), m.group(2))
        if r and r.lower() not in seen:
            seen.add(r.lower())
            out.append(r)
    return out


def keyword_repos(body):
    d = json.loads(body)
    out = []
    for p in d.get("packages") or []:
        url = p.get("repository_url") or ""
        m = GH.search(url)
        out.append({"ecosystem": p.get("ecosystem"), "package": p.get("name"),
                    "repo": norm_repo(m.group(1), m.group(2)) if m else None})
    return out


def main(argv):
    tag = ""
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    qfile, raw_dir, out = argv[1], argv[2], argv[3]
    only = set(argv[4:])
    d = json.load(open(qfile))
    os.makedirs(raw_dir, exist_ok=True)
    jobs = []
    for q in d.get("package_keyword_index", []):
        for page in q["pages"]:
            jobs.append(("PACKAGE_KEYWORD_INDEX", q, q["url_template"].format(page=page), "%s_p%d" % (q["qid"], page)))
    for q in d.get("docs_crosslinks", []):
        jobs.append(("DOCS_CROSSLINK", q, q["url"], q["qid"]))
    for q in d.get("paper_links", []):
        jobs.append(("PAPER_LINK", q, q["url"], q["qid"]))
    for mech, q, url, rid in jobs:
        if only and q["qid"] not in only:
            continue
        t, status, body = get(url)
        with open(os.path.join(raw_dir, rid + tag + ".raw"), "wb") as f:
            f.write(body)
        rec = {"qid": rid + tag, "family": q["family"], "needs": q["needs"], "mechanism": mech,
               "query": q.get("keyword") or q.get("what"), "url": url, "retrieved_at": t,
               "http_status": status, "body_sha256": hashlib.sha256(body).hexdigest()}
        if status == 200 and mech == "PACKAGE_KEYWORD_INDEX":
            items = keyword_repos(body)
            rec["returned"] = len(items)
            rec["items"] = [dict(it, rank=i + 1) for i, it in enumerate(items)]
        elif status == 200:
            repos = repos_in_text(body.decode("utf-8", "replace"))
            rec["returned"] = len(repos)
            rec["items"] = [{"rank": i + 1, "repo": r} for i, r in enumerate(repos)]
        else:
            rec["returned"] = 0
            rec["items"] = []
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        print(rec["qid"], status, rec["returned"], t)
        time.sleep(2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""One-shot Maxun Cloud v1 client for the Phase 06A bake-off. The key is read at runtime from D:\memelab\maxun-token.txt,
sent only to app.maxun.dev, never printed, logged or written. No schedules, webhooks or monitoring alerts are created."""
import json, sys, time, os, urllib.request
BASE = "https://app.maxun.dev/api/v1"
OUT = r"D:\memelab\backtesting_work\p06a\maxun"
os.makedirs(OUT, exist_ok=True)
KEY = open(r"D:\memelab\maxun-token.txt", encoding="utf-8").read().strip()
def scrub(s):
    return s.replace(KEY, "[REDACTED]") if KEY else s
def call(method, path, body=None):
    assert BASE.startswith("https://app.maxun.dev/")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"x-api-key": KEY, "Content-Type": "application/json", "Accept": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            st, b = r.status, r.read()
    except urllib.error.HTTPError as e:
        st, b = e.code, e.read()
    txt = scrub(b.decode("utf-8", "replace"))
    try:
        j = json.loads(txt)
    except Exception:
        j = {"raw": txt[:2000]}
    return st, j, t
def log(name, obj):
    p = os.path.join(OUT, name)
    open(p, "w", encoding="utf-8").write(scrub(json.dumps(obj, indent=1, default=str)))
    return p
def usage(tag):
    st, j, t = call("GET", "/usage")
    st2, j2, _ = call("GET", "/schedules")
    rec = {"t": t, "usage_status": st, "usage": j.get("data"), "schedules_status": st2, "schedules": j2.get("data")}
    log(f"usage_{tag}.json", rec)
    return rec
def run_and_wait(robot_id, tag, max_wait=900):
    st, j, t0 = call("POST", f"/robots/{robot_id}/runs", {})
    log(f"run_start_{tag}.json", {"status": st, "resp": j, "t": t0})
    rid = j.get("id") or (j.get("data") or {}).get("id")
    if not rid:
        return None
    while time.time() - t0 < max_wait:
        time.sleep(5)
        st, r, t = call("GET", f"/runs/{rid}")
        d = r.get("data") or {}
        if d.get("status") not in ("queued", "running"):
            log(f"run_{tag}.json", {"status": st, "resp": r, "polled_at": t, "started_req_at": t0})
            return d
    log(f"run_{tag}_timeout.json", {"run_id": rid, "t0": t0})
    return None
cmd = sys.argv[1]
if cmd == "usage":
    print(json.dumps(usage(sys.argv[2])["usage"]))
elif cmd == "crawl":
    before = usage("before_crawl")
    body = {"url": "https://solana.com/news", "name": "memelab-p06a-solana-news-crawl",
            "crawlConfig": {"mode": "path", "limit": 12, "maxDepth": 1, "useSitemap": True, "followLinks": True, "respectRobots": True, "includePaths": ["/news/.*"]}}
    st, j, t = call("POST", "/robots/crawl", body)
    log("robot_crawl_create.json", {"status": st, "resp": j, "t": t, "request": body})
    rid = (j.get("data") or {}).get("id") or j.get("id")
    d = run_and_wait(rid, "crawl1") if rid else None
    after = usage("after_crawl")
    st, sch, _ = call("GET", f"/robots/{rid}/schedule") if rid else (None, None, None)
    log("robot_crawl_schedule.json", {"status": st, "resp": sch})
    print(json.dumps({"robot": rid, "run_status": (d or {}).get("status"), "pages": len(((d or {}).get("data") or {}).get("crawlData") or []), "credits_before": (before["usage"] or {}).get("credits"), "credits_after": (after["usage"] or {}).get("credits")}))
elif cmd == "scrape":
    url = sys.argv[2]; tag = sys.argv[3]
    before = usage(f"before_{tag}")
    body = {"url": url, "name": f"memelab-p06a-{tag}", "formats": ["markdown", "html"]}
    st, j, t = call("POST", "/robots/scrape", body)
    log(f"robot_{tag}_create.json", {"status": st, "resp": j, "t": t, "request": body})
    rid = (j.get("data") or {}).get("id") or j.get("id")
    d = run_and_wait(rid, tag) if rid else None
    after = usage(f"after_{tag}")
    print(json.dumps({"robot": rid, "run_status": (d or {}).get("status"), "credits_before": (before["usage"] or {}).get("credits"), "credits_after": (after["usage"] or {}).get("credits")}))
elif cmd == "rerun":
    rid = sys.argv[2]; tag = sys.argv[3]
    before = usage(f"before_{tag}")
    d = run_and_wait(rid, tag)
    after = usage(f"after_{tag}")
    print(json.dumps({"robot": rid, "run_status": (d or {}).get("status"), "hasChanges": (d or {}).get("hasChanges"), "credits_before": (before["usage"] or {}).get("credits"), "credits_after": (after["usage"] or {}).get("credits")}))
elif cmd == "diff":
    st, j, t = call("GET", f"/runs/{sys.argv[2]}/diff")
    log(f"diff_{sys.argv[3]}.json", {"status": st, "resp": j, "t": t})
    print(st)

"""Phase 06A shared scorer: one extractor for every tool's view, compared with the hand-labeled oracle.

    python audits/backtesting/bakeoff/p06a_score.py audits/backtesting/bakeoff/p06a_views.jsonl audits/backtesting/bakeoff/p06a_oracle.json
Writes p06a_scores.json next to the views and prints a table. Rules are the ones fixed in MAXUN_BAKEOFF_PREREG.md.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest.sources.pagefields import date_of, norm, tag_of, title_of  # the runtime extractor, shared by every tool


def canon(u: str | None) -> str | None:
    if not u:
        return None
    u = u.replace("%40", "@").rstrip("/")
    return u.replace("https://github.com/solana-foundation/anchor/", "https://github.com/otter-sec/anchor/")


def score(views: list[dict], oracle: dict) -> dict:
    orc = {("A", canon(o["url"])): o for o in oracle["A"]} | {("B", canon(o["url"])): o for o in oracle["B"]} | \
          {("A_EXTRA", canon(o["url"])): o for o in oracle["A_extra_maxun_pages"]}
    sample = {"A": {canon(o["url"]) for o in oracle["A"]}, "B": {canon(o["url"]) for o in oracle["B"]}}
    cells: dict = defaultdict(lambda: {"attempts": 0, "usable": 0, "in_sample": 0, "duplicates": 0, "credits": 0, "secs": [],
                                        "title_ok": 0, "date_ok": 0, "tag_ok": 0, "scored": 0, "date_sources": defaultdict(int), "misses": []})
    seen = defaultdict(set)
    for v in views:
        site = v["site"]
        c = cells[(v["tool"], site)]
        c["attempts"] += 1
        c["credits"] += v.get("credits") or 0
        if v.get("secs") is not None:
            c["secs"].append(v["secs"])
        u = canon(v.get("final_url") or v["url"])
        if u in seen[(v["tool"], site)]:
            c["duplicates"] += 1
        seen[(v["tool"], site)].add(u)
        if not v.get("ok"):
            c["misses"].append({"url": v["url"], "why": "not usable"})
            continue
        c["usable"] += 1
        o = orc.get((site, u)) or orc.get((site, canon(v["url"])))
        if site in sample and u in sample[site]:
            c["in_sample"] += 1
        if not o:
            continue
        c["scored"] += 1
        t, ts = title_of(v)
        d, ds = date_of(v)
        c["date_sources"][ds] += 1
        ok_t = norm(t) == norm(o["title"])
        ok_d = (o["date"] is None and d is None) or d == o["date"]
        c["title_ok"] += ok_t
        c["date_ok"] += ok_d
        row = {"url": v["url"]}
        if not ok_t:
            row["title"] = {"got": t, "want": o["title"], "from": ts}
        if not ok_d:
            row["date"] = {"got": d, "want": o["date"], "from": ds}
        if site == "B":
            g, gs = tag_of(v)
            ok_g = g == o["tag"]
            c["tag_ok"] += ok_g
            if not ok_g:
                row["tag"] = {"got": g, "want": o["tag"], "from": gs}
        if len(row) > 1:
            c["misses"].append(row)
    out = {}
    for (tool, site), c in sorted(cells.items()):
        n = len(sample.get(site, ())) if site in sample else c["scored"]
        out[f"{tool}|{site}"] = {"attempts": c["attempts"], "usable": c["usable"], "sample_pages_returned": c["in_sample"] if site in sample else None,
                                 "sample_size": len(sample[site]) if site in sample else None, "scored": c["scored"], "duplicates": c["duplicates"],
                                 "credits": c["credits"], "mean_secs_per_page": round(sum(c["secs"]) / len(c["secs"]), 2) if c["secs"] else None,
                                 "title_acc": round(c["title_ok"] / n, 3) if n else None, "date_acc": round(c["date_ok"] / n, 3) if n else None,
                                 "tag_acc": round(c["tag_ok"] / n, 3) if (n and site == "B") else None, "denominator": n,
                                 "sufficient_sample": c["in_sample"] >= 10 if site in sample else False,
                                 "date_sources": dict(c["date_sources"]), "misses": c["misses"]}
    return out


if __name__ == "__main__":
    vp, op = Path(sys.argv[1]), Path(sys.argv[2])
    views = [json.loads(l) for l in vp.read_text().splitlines() if l.strip()]
    res = score(views, json.loads(op.read_text()))
    (vp.parent / "p06a_scores.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    print(f"{'cell':22} {'att':>4} {'use':>4} {'insmp':>5} {'dup':>4} {'cred':>5} {'s/pg':>6} {'title':>6} {'date':>6} {'tag':>6} {'n':>3} suff")
    for k, r in res.items():
        print(f"{k:22} {r['attempts']:>4} {r['usable']:>4} {str(r['sample_pages_returned']):>5} {r['duplicates']:>4} {r['credits']:>5} {str(r['mean_secs_per_page']):>6} "
              f"{str(r['title_acc']):>6} {str(r['date_acc']):>6} {str(r['tag_acc']):>6} {r['denominator']:>3} {r['sufficient_sample']}")

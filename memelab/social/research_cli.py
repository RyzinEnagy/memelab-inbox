"""Phase 13 CLI: python -m memelab social research <policy|show|demo>

  research policy [--policy FILE]                                  effective policy and where it came from
  research show [--as-of T] [--db PATH] [--include-fixtures] [--json]
                                                                   research queue from the latest narrative snapshot (no tokens
                                                                   evaluated here, so every contract shows as needing analysis)
  research demo --fixture FILE [--out FILE]                        before/after scout report on a fixture (no database is touched)

The scout itself takes --social (python -m memelab scout ... --social); the catalyst report takes --social too.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

from . import research_core as RC, research_store as RS


def before_after(doc: dict, policy: dict | None = None) -> dict:
    """Render the scout report twice from the same fixture results: social off, then on. The scout lists are built by the
    real scout code (cli.scout_lists) and the report by the real renderer; the social section only appends."""
    from .. import cli, report
    policy = policy or RC.make_policy({"include_fixtures": True}, source="fixture")
    results, s2 = doc["results"], {"rejected_stage2": doc.get("rejected_stage2", [])}
    ranked, serious, near, rejected = cli.scout_lists(results, s2, doc.get("min_score", 55))
    env = {"Fixture": "invented tokens and findings (tests/fixtures/social/research)", "Best token vs best trade": ranked.get("best_token_vs_best_trade")}
    before = report.render_scout_report(env, serious, near, rejected, when=doc["as_of"])
    ev = RS.evaluated_from_scout(results, [r["mint"] for r in serious], doc.get("prior"))
    res = RC.build(doc["findings"], ev, policy, as_of=doc["as_of"])
    after = report.render_scout_report(env, serious, near, rejected, when=doc["as_of"], social=res)
    ranked2, serious2, near2, rejected2 = cli.scout_lists(results, s2, doc.get("min_score", 55))
    unchanged = (after.startswith(before) and [r["mint"] for r in serious] == [r["mint"] for r in serious2] and near == near2
                 and rejected == rejected2 and ranked == ranked2)
    return {"before": before, "after": after, "result": res, "body_unchanged": unchanged,
            "serious": [r["mint"] for r in serious], "near": [n["mint"] for n in near], "rejected": [x["mint"] for x in rejected]}


def side_by_side(ba: dict) -> str:
    res = ba["result"]
    by = {c["contract"]: c for c in res["candidates"]}
    rows = []
    for r in ba["_results"]:
        c = by.get(r["mint"])
        lane = c["lanes"]["narrative_attention"]["level"] if c else "NONE"
        rows.append(f"| {r['bundle']['identity']['symbol']} | {r['score']['total']} | {r['status']['status']} | "
                    f"{'serious' if r['mint'] in ba['serious'] else 'near miss' if r['mint'] in ba['near'] else 'rejected' if r['mint'] in ba['rejected'] else 'none'} | "
                    f"same | same | {lane} | {c['research_state'] if c else 'not in social section'} |")
    for c in res["candidates"]:
        if c["contract"] not in {r["mint"] for r in ba["_results"]}:
            rows.append(f"| {c['symbol']} (other contract) | not analyzed | not analyzed | not listed | n/a | n/a | {c['lanes']['narrative_attention']['level']} | {c['research_state']} |")
    for u in res["unresolved"]:
        rows.append(f"| ${u['symbol']} (ticker only) | n/a | n/a | not listed | n/a | n/a | UNRESOLVED | never ranked |")
    L = ["# Phase 13 fixture: scout report before and after social research candidates", "",
         "Invented tokens and findings. The scout lists and the report body come from the real scout code; the social section is appended.",
         f"Report body unchanged by the social layer: {'yes' if ba['body_unchanged'] else 'NO'}.", "",
         "| Token | Score | Status | Scout list | Score after | Status after | Narrative attention | Research state |",
         "|---|---|---|---|---|---|---|---|", *rows, "",
         "## Before: social off", "", ba["before"], "", "## After: social on", "", ba["after"]]
    return "\n".join(L) + "\n"


def cmd(a):
    if a.action == "policy":
        print(json.dumps(RS.load_policy(a.policy), indent=1, sort_keys=True))
        return
    if a.action == "demo":
        doc = json.loads(Path(a.fixture).read_text())
        if not doc.get("is_fixture"):
            sys.exit("demo reads fixture files only")
        ba = before_after(doc)
        ba["_results"] = doc["results"]
        md = side_by_side(ba)
        if a.out:
            Path(a.out).write_text(md)
        print(md)
        sys.exit(0 if ba["body_unchanged"] else 1)
    # show
    policy = RS.load_policy(a.policy)
    if a.include_fixtures:
        policy = RC.make_policy({**{k: v for k, v in policy.items() if k != "provenance"}, "include_fixtures": True},
                                source=policy["provenance"]["source"] + "+cli", path=policy["provenance"]["path"])
    as_of = float(a.as_of) if a.as_of else time.time()
    if a.db:
        def factory():
            c = sqlite3.connect(a.db)
            c.row_factory = sqlite3.Row
            return c
    else:
        from .. import db as _db
        factory = _db.connect
    res = RS.section(factory, as_of=as_of, policy=policy, evaluated=[])
    print(json.dumps(res, indent=1, sort_keys=True, default=str) if a.json else RC.render(res))


def add_parser(ssp) -> None:
    q = ssp.add_parser("research", help="social findings as research candidates beside the scout and catalyst (opt-in, no trade impact)")
    q.add_argument("action", choices=["policy", "show", "demo"])
    q.add_argument("--policy"); q.add_argument("--as-of"); q.add_argument("--db"); q.add_argument("--include-fixtures", action="store_true")
    q.add_argument("--json", action="store_true"); q.add_argument("--fixture"); q.add_argument("--out")
    q.set_defaults(fn=cmd)

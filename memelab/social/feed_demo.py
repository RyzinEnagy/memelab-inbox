"""Phase 14: build a throwaway social store from a fixture spec, so the feed demo runs the real read path.

A spec (schema memelab.social.feed.fixture/1, "is_fixture": true) lists invented accounts, posts, coverage, trader links,
chronology flags and market facts. build_db() writes them into a fresh SQLite file through the same store functions the
collectors use (store.upsert_account, store.record_observation, store.add_claim, market_context.store_fact) and takes
the narrative snapshots with narratives.snapshot, then feed_store.load_input reads that file exactly as it reads the
lab database. Every observation is access_mode 'fixture', so every snapshot is marked contains_fixture and the
feed is watermarked. Nothing here touches the tracked database or the network.

Post text is generated ("invented post <id>") only to give the store something to hash; the hash is all it keeps.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .. import db
from . import feed_core as FC, market_context as MC, narratives as NR, store

SPEC_SCHEMA = "memelab.social.feed.fixture/1"
EXTRACT_V = "feed-fixture-extract"


def _t(v: Any) -> float | None:
    return FC.parse_time(v)


def _tok(spec: dict, ref: str) -> dict:
    if ref.startswith("$"):
        return {"mention_id": f"t-{ref[1:]}", "mention_key": f"ticker:{ref[1:]}", "status": "unresolved", "resolution_id": None}
    t = spec["tokens"][ref]
    return {"mention_id": f"m-{t['contract'][:6]}", "mention_key": f"ca:{t['contract']}", "status": "resolved", "resolution_id": None,
            "chain": t["chain"], "contract": t["contract"]}


def _post(con, spec: dict, p: dict) -> None:
    at = _t(p["at"])
    obs = _t(p.get("observed_at")) or at + 30
    platform = p.get("platform", "x")
    acct = store.upsert_account(con, platform, handle=p["account"], provider_user_id=p["account"], account_kind=p.get("kind"), now=at) if p.get("account") else None
    url = p.get("url", f"https://example.invalid/{platform}/{p['id']}")
    text = f"invented post {p.get('same_text_as', p['id'])}"
    o = store.record_observation(con, platform=platform, access_mode="fixture", collector="feed_fixture", provider_item_id=p["id"], original_url=url,
                                 account_id=acct, published_at=at, observed_at=obs, text=text, summary=p.get("summary"), now=obs)
    item = o["item_key"]
    for t, status in p.get("later") or []:
        store.record_observation(con, platform=platform, access_mode="fixture", collector="feed_fixture", provider_item_id=p["id"], original_url=url,
                                 account_id=acct, published_at=at, observed_at=_t(t), retrieval_status=status, now=_t(t))
    flags = ["injection_rule_0"] if p.get("injection") else []
    reasons = ["injection_suspected"] if p.get("injection") else []
    con.execute("INSERT OR IGNORE INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,"
                "extractor_version,analysis_version,status,mode,flags_json,extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"feedfx-{p['id']}", o["id"], item, store.text_hash(text), "fixture", "deterministic", "feedfx-1", EXTRACT_V, "ok", "fixture",
                 json.dumps(flags), obs))
    eid = con.execute("SELECT extraction_id FROM social_claim_extractions WHERE extraction_key=?", (f"feedfx-{p['id']}",)).fetchone()[0]
    tokens = [_tok(spec, r) for r in p.get("tokens") or []]
    c = store.add_claim(con, claim_type=p.get("claim_type", "OTHER"), analysis_version=EXTRACT_V, item_key=item, account_id=acct, claimed_at=at,
                        summary=p.get("claim_summary"), now=obs)
    con.execute("INSERT OR IGNORE INTO social_claim_attributes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (c["id"], eid, 0, p.get("category", "bullish"), p.get("assertion", "opinion"), p.get("stance", "positive"), 0, int(p.get("conditional", 0)),
                 int(p.get("sarcasm", 0)), "unspecified", p.get("position", "not_disclosed"), p.get("attribution", "author"), None, None,
                 "medium" if reasons else "low", json.dumps(reasons), p.get("verification", "unverified_text_claim"),
                 json.dumps(p.get("tags") or []), json.dumps(tokens, sort_keys=True)))
    for rt, target in p.get("refs") or []:
        con.execute("INSERT OR IGNORE INTO social_item_refs VALUES (?,?,?,?,?)", (item, rt, target, None, obs))
    if p.get("forward_of"):
        fw = p["forward_of"]
        con.execute("INSERT OR IGNORE INTO social_item_forwards VALUES (?,?,?,?,?,?,?,?)",
                    (item, "channel" if fw != "unknown" else "hidden_user", None, None, None if fw == "unknown" else fw, None, 0, obs))
    for t in tokens:
        if t["status"] == "resolved":
            sym = next((s for s, v in spec["tokens"].items() if v["contract"] == t["contract"]), None)
            store.upsert_token_ref(con, t["chain"], t["contract"], symbol=spec["tokens"][sym].get("symbol", sym) if sym else None, now=at)


def _flag(con, spec: dict, f: dict, n: int) -> None:
    t = spec["tokens"][f["token"]]
    key = hashlib.sha256(json.dumps(f, sort_keys=True).encode()).hexdigest()
    cur = con.execute("INSERT INTO social_chrono_runs(engine_version,rules_version,chain,contract,source_id,as_of,order_status,policy_sha256,input_sha256,"
                      "result_sha256,n_timeline,n_patterns,input_json,result_json,created_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                      ("chrono-fixture", "rules-fixture", t["chain"], t["contract"], f["source_id"], _t(f["at"]), f.get("order_status", "CONFIDENT"),
                       "fixture", key, key, 0, 0, "{}", "{}", _t(f["at"])))
    con.execute("INSERT INTO social_chrono_flags(run_id,flag_key,chain,contract,source_id,flag,category,bucket,rule,order_status,attribution,at,evidence_json,note,is_fixture)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (cur.lastrowid, f"fx{n}", t["chain"], t["contract"], f["source_id"], f["flag"], f["category"], f["bucket"], f["rule"],
                 f.get("order_status", "CONFIDENT"), f.get("attribution"), _t(f["at"]), json.dumps(f.get("evidence") or []), f.get("note")))


def build_db(spec: dict, path: str | Path) -> dict:
    """Write the spec into a new SQLite file at path. Returns {"path", "runs"}."""
    if not spec.get("is_fixture") or spec.get("schema") != SPEC_SCHEMA:
        raise FC.FeedError(f"a feed fixture must say is_fixture true and schema {SPEC_SCHEMA}")
    path = Path(path)
    if path.exists():
        raise FC.FeedError(f"{path} exists; the demo builds a fresh store")
    db.init_db(path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        t0 = min(_t(p["at"]) for p in spec["posts"]) if spec.get("posts") else _t(spec["as_of"])
        store.register_analysis_version(con, EXTRACT_V, "extractor", "feed fixture builder (invented)", now=t0)
        for i, cv in enumerate(spec.get("coverage") or []):
            store.record_coverage(con, run_id=f"fx{i}", connector=f"{cv['platform']}_fixture", platform=cv["platform"], scope="invented",
                                  status=cv.get("status", "COVERED"), window_start=_t(cv["start"]), window_end=_t(cv["end"]),
                                  checked_at=_t(cv["start"]) + 60, gap_reason=cv.get("gap_reason"), now=_t(cv["start"]))
        for p in sorted(spec.get("posts") or [], key=lambda p: (_t(p["at"]), p["id"])):
            _post(con, spec, p)
        for tr in spec.get("traders") or []:
            store.upsert_trader(con, tr["trader_id"], tr["label"], added_reason="invented fixture", now=t0)
            acct = store.upsert_account(con, tr.get("platform", "x"), handle=tr["account"], provider_user_id=tr["account"], now=t0)
            store.link_trader_account(con, tr["trader_id"], acct, "LAB_ASSERTED", "HEURISTIC", now=t0)
        for n, f in enumerate(spec.get("chrono_flags") or []):
            _flag(con, spec, f, n)
        for m in spec.get("market") or []:
            t = spec["tokens"][m["token"]]
            ft = _t(m["fetched_at"])
            MC.store_fact(con, t["chain"], t["contract"], None,
                          {"provider": m.get("provider", "fixture_provider"), "field": m["field"], "value_num": m.get("value"), "value_str": m.get("value_str"),
                           "unit": m["unit"], "as_of": ft, "as_of_kind": "OBSERVED_AT_FETCH", "valid_from": ft,
                           "valid_until": ft + float(m.get("valid_seconds", 3600)), "bucket": "FACT", "source_url": m.get("source_url")}, ft, ft)
        runs = []
        for s in spec.get("snapshots") or []:
            r = NR.snapshot(con, day=s["day"], tz=s.get("tz", "UTC"), now=_t(s["now"]))
            runs.append(r["run_id"])
        con.commit()
    finally:
        con.close()
    return {"path": str(path), "runs": runs}

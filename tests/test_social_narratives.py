"""Phase 07: narrative clustering, originators, amplifiers and independent corroboration.

Invented posts only (ids, hashes, counts; no real text). Temp databases, fixed clocks, no network.
Posts are written straight into the Phase 01 to 06 tables with a small builder, so each test states exactly the
provenance it needs (reposts, quotes, forwards, deletions, coverage) and nothing else.
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from memelab import db
from memelab.social import content_guard, narratives as NR, schema, store

ROOT = Path(__file__).resolve().parent.parent
FXD = json.loads((ROOT / "tests" / "fixtures" / "social" / "narratives" / "two_days.json").read_text())
FXR = json.loads((ROOT / "tests" / "fixtures" / "social" / "resolve" / "fx_providers.json").read_text())
A = FXR["addresses"]
D1 = int(datetime(2026, 10, 12, tzinfo=timezone.utc).timestamp())
D2 = D1 + 86400
H = 3600
M1, M2, M3 = A["M1"], A["M2"], A["M3"]
K1, K2, K3 = f"ca:solana:{M1}", f"ca:solana:{M2}", f"ca:solana:{M3}"
EXTRACT_V = "extract-test"


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    store.register_analysis_version(c, EXTRACT_V, "extractor", "test builder", now=D1)
    yield c
    c.close()


def tok(chain, contract):
    return {"mention_id": f"m-{contract[:6]}", "mention_key": f"ca:{contract}", "status": "resolved", "resolution_id": None,
            "chain": chain, "contract": contract}


def tick(sym):
    return {"mention_id": f"t-{sym}", "mention_key": f"ticker:{sym}", "status": "unresolved", "resolution_id": None}


def post(con, pid, acct, at, *, obs=None, tokens=(), tags=(), stance="positive", text=None, refs=(), fwd="none", attribution="author",
         kind=None, platform="x", later=(), mode="fixture", sarcasm=0, category="bullish", ref_attr=None):
    """One post, one claim. refs: [(ref_type, item_key)]. fwd: 'none' | item_key | 'unknown'. later: [(time, retrieval_status)]."""
    obs = at + 30 if obs is None else obs
    acct_id = store.upsert_account(con, platform, handle=acct, provider_user_id=acct, account_kind=kind, now=at) if acct else None
    text = f"invented post {pid}" if text is None else text
    o = store.record_observation(con, platform=platform, access_mode=mode, collector="narr_test", provider_item_id=pid,
                                 original_url=f"https://example.invalid/{pid}", account_id=acct_id, published_at=at, observed_at=obs,
                                 text=text, now=obs)
    item = o["item_key"]
    for t, status in later:
        store.record_observation(con, platform=platform, access_mode=mode, collector="narr_test", provider_item_id=pid,
                                 original_url=f"https://example.invalid/{pid}", account_id=acct_id, published_at=at, observed_at=t,
                                 retrieval_status=status, now=t)
    con.execute("INSERT OR IGNORE INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,"
                "extractor_version,analysis_version,status,mode,extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"k-{pid}", o["id"], item, store.text_hash(text), "c", "deterministic", "t1", EXTRACT_V, "ok", "none", obs))
    eid = con.execute("SELECT extraction_id FROM social_claim_extractions WHERE extraction_key=?", (f"k-{pid}",)).fetchone()[0]
    c = store.add_claim(con, claim_type="OTHER", analysis_version=EXTRACT_V, item_key=item, account_id=acct_id, claimed_at=at, now=obs)
    con.execute("INSERT INTO social_claim_attributes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (c["id"], eid, 0, category, "opinion", stance, 0, 0, sarcasm, "unspecified", "not_disclosed", attribution, ref_attr, None,
                 "low", "[]", "unverified_text_claim", json.dumps(list(tags)), json.dumps(list(tokens), sort_keys=True)))
    for rt, target in refs:
        con.execute("INSERT OR IGNORE INTO social_item_refs VALUES (?,?,?,?,?)", (item, rt, target, None, obs))
    if fwd != "none":
        con.execute("INSERT INTO social_item_forwards VALUES (?,?,?,?,?,?,?,?)",
                    (item, "channel" if fwd != "unknown" else "hidden_user", None, None, None if fwd == "unknown" else fwd, None, 0, obs))
    for _, ch_contract in [(None, t) for t in tokens if t.get("status") == "resolved"]:
        store.upsert_token_ref(con, ch_contract["chain"], ch_contract["contract"], symbol=SYMS.get(ch_contract["contract"]), now=at)
    return {"item": item, "claim_id": c["id"], "obs": o["id"], "account": acct_id}


SYMS = {M1: "LABDOG", M2: "MIDCAT", M3: "NEWPUP", A["PEPE_SOL1"]: "PEPE", A["PEPE_SOL2"]: "PEPE"}


def cover(con, platform="x", status="COVERED", start=D1, end=D1 + 7 * 86400, run="r1", reason=None):
    store.record_coverage(con, run_id=run, connector=f"{platform}_test", platform=platform, scope="invented", status=status,
                          window_start=start, window_end=end, checked_at=start + 60, gap_reason=reason, now=start)


def snap(con, day="2026-10-12", now=D2, **kw):
    r = NR.snapshot(con, day=day, now=now, **kw)
    return r, {c["cluster_key"]: c for c in r["clusters"]}


def roles(con, run_id, key):
    return {m["item_key"]: m["role"] for m in NR.members(con, run_id, key)}


# ---------- repeated reposts by 100 handles ----------

def test_one_hundred_reposts_of_one_original_are_one_independent_source(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    for i in range(100):
        post(con, f"rp{i:03d}", f"handle_{i:03d}", D1 + 2 * H + i, tokens=[tok("solana", M1)], refs=[("retweeted", "x:o1")],
             text="invented post o1", attribution="reposted")
    r, cl = snap(con)
    c = cl[K1]
    assert (c["item_count"], c["window_mentions"]) == (101, 101)
    assert c["independent_source_count"] == 1 and c["independent_group_count"] == 1
    assert c["amplifier_count"] == 100 and c["dependent_count"] == 0
    assert c["source_count"] == 101                       # 101 different handles, still one source of the claim
    assert c["status"] == "ok" and c["confidence"] == "LOW"
    hyp = [f for f in c["flags"] if f["flag"] == "burst_amplification"]
    assert hyp and hyp[0]["proven"] is False and hyp[0]["evidence"] == "HEURISTIC" and hyp[0]["amplifying_sources"] == 100
    assert c["edge_count"] == 100
    assert not [f for f in c["flags"] if f["flag"] == "identical_text_multi_source"]      # reposts copy text by nature
    assert len(c["dependencies"]) == 1 and c["dependencies"][0]["size"] == 101
    assert [o["item_key"] for o in c["originators"]] == ["x:o1"]


def test_reposts_whose_original_was_never_observed_make_volume_but_not_independence(con):
    cover(con)
    for i in range(5):
        post(con, f"rp{i}", f"handle_{i}", D1 + H + i, tokens=[tok("solana", M1)], refs=[("retweeted", "x:never_seen")], text="invented post z",
             attribution="reposted")
    r, cl = snap(con)
    c = cl[K1]
    assert c["status"] == "insufficient_coverage" and c["reasons"] == ["origins_not_observed"]
    assert c["independent_source_count"] is None and c["confidence"] == "UNKNOWN"
    assert c["unobserved_origin_count"] == 1 and c["item_count"] == 5 and c["amplifier_count"] == 5     # observed counts stay, as lower bounds
    assert c["coverage"]["counts_are_lower_bounds"] is True


def test_reposts_group_with_their_original_even_when_the_text_differs(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    for i in range(4):
        post(con, f"rp{i}", f"rep_{i}", D1 + 2 * H + i, tokens=[tok("solana", M1)], refs=[("retweeted", "x:o1")], text=f"invented different words {i}",
             attribution="reposted")
    r, cl = snap(con)
    assert cl[K1]["independent_source_count"] == 1 and cl[K1]["amplifier_count"] == 4
    assert {e["edge_type"] for e in NR.edges_for(con, r["run_id"], K1)} == {"repost"}


def test_a_reply_to_an_item_that_makes_no_claim_is_its_own_origin_but_a_reply_to_an_unseen_item_is_not(con):
    cover(con)
    post(con, "other", "someone", D1 + H, tokens=[])                                       # observed, no token claim
    post(con, "r1", "replier_a", D1 + 2 * H, tokens=[tok("solana", M1)], refs=[("replied_to", "x:other")])
    post(con, "r2", "replier_b", D1 + 3 * H, tokens=[tok("solana", M1)], refs=[("replied_to", "x:never_seen")])
    r, cl = snap(con)
    rl = roles(con, r["run_id"], K1)
    assert rl["x:r1"] == "INDEPENDENT_ORIGINAL" and rl["x:r2"] == "DEPENDENT"
    assert cl[K1]["independent_source_count"] == 1 and cl[K1]["unobserved_origin_count"] == 1


def test_forwards_are_amplifiers_and_a_forward_with_hidden_origin_is_flagged(con):
    cover(con, "telegram")
    post(con, "chan1", "chan_a", D1 + H, tokens=[tok("solana", M1)], platform="telegram")
    post(con, "fw1", "chan_b", D1 + 2 * H, tokens=[tok("solana", M1)], platform="telegram", fwd="telegram:chan1", text="invented post chan1")
    post(con, "fw2", "chan_c", D1 + 3 * H, tokens=[tok("solana", M1)], platform="telegram", fwd="unknown", text="invented post hidden")
    r, cl = snap(con)
    c = cl[K1]
    rl = roles(con, r["run_id"], K1)
    assert rl["telegram:chan1"] == "INDEPENDENT_ORIGINAL" and rl["telegram:fw1"] == "AMPLIFIER" and rl["telegram:fw2"] == "AMPLIFIER"
    assert c["independent_source_count"] == 1 and c["unobserved_origin_count"] == 1
    assert any(f["flag"] == "forward_origin_unknown" for f in c["flags"])
    assert c["confidence"] == "LOW"


# ---------- independence ----------

def test_two_separate_early_originals_count_twice_and_first_observed_is_the_earliest_observation(con):
    cover(con)
    post(con, "e1", "early_one", D1 + 2 * H, obs=D1 + 2 * H + 600, tokens=[tok("solana", M1)])
    post(con, "e2", "early_two", D1 + 2 * H + 90, obs=D1 + 2 * H + 120, tokens=[tok("solana", M1)])
    post(con, "q1", "later_one", D1 + 5 * H, tokens=[tok("solana", M1)], refs=[("retweeted", "x:e1")], text="invented post e1")
    r, cl = snap(con)
    c = cl[K1]
    assert c["independent_source_count"] == 2 and c["independent_group_count"] == 2
    assert [o["item_key"] for o in c["originators"]] == ["x:e1", "x:e2"]          # by provider publication time
    assert c["first_observed_at"] == D1 + 2 * H + 120                              # first collector sighting, not the first-ever mention
    assert c["earliest_published_at"] == D1 + 2 * H
    assert c["confidence"] == "MODERATE"
    assert [d["size"] for d in c["dependencies"]] == [2]


def test_quote_that_repeats_is_amplifier_reply_and_commentary_are_dependent_and_none_is_independent(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    post(con, "qt1", "quoter", D1 + 2 * H, tokens=[tok("solana", M1)], refs=[("quoted", "x:o1")], attribution="quoted", text="invented post qt1")
    post(con, "qt2", "commenter", D1 + 3 * H, tokens=[tok("solana", M1)], refs=[("quoted", "x:o1")], attribution="author", text="invented post qt2")
    post(con, "rep1", "replier", D1 + 4 * H, tokens=[tok("solana", M1)], refs=[("replied_to", "x:o1")], attribution="author", text="invented post rep1")
    r, cl = snap(con)
    rl = roles(con, r["run_id"], K1)
    assert rl == {"x:o1": "INDEPENDENT_ORIGINAL", "x:qt1": "AMPLIFIER", "x:qt2": "DEPENDENT", "x:rep1": "DEPENDENT"}
    assert cl[K1]["independent_source_count"] == 1 and cl[K1]["source_count"] == 4


def test_different_accounts_citing_one_shared_original_are_not_independent(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    for i in range(6):
        post(con, f"c{i}", f"commenter_{i}", D1 + 2 * H + i * 700, tokens=[tok("solana", M1)], refs=[("replied_to", "x:o1")],
             text=f"invented post c{i}")
    r, cl = snap(con)
    assert cl[K1]["independent_source_count"] == 1 and cl[K1]["dependent_count"] == 6 and cl[K1]["source_count"] == 7


def test_byte_identical_copies_from_several_accounts_collapse_to_one_group_with_a_hypothesis(con):
    cover(con)
    for i, a in enumerate(["copy_a", "copy_b", "copy_c", "copy_d"]):
        post(con, f"cp{i}", a, D1 + H + i * 60, tokens=[tok("solana", M1)], text="invented identical sentence")
    r, cl = snap(con)
    c = cl[K1]
    assert c["independent_source_count"] == 1 and c["dependent_count"] == 3
    f = [x for x in c["flags"] if x["flag"] == "identical_text_multi_source"]
    assert f and f[0]["proven"] is False and f[0]["sources"] == 4
    assert {e["edge_type"] for e in NR.edges_for(con, r["run_id"], K1)} == {"identical_text"}
    assert c["confidence"] == "LOW"


def test_bots_aggregators_unknown_authors_and_linked_accounts_do_not_inflate_independence(con):
    cover(con)
    post(con, "u1", "feed_bot", D1 + H, tokens=[tok("solana", M1)], kind="BOT")
    post(con, "u2", "news_feed", D1 + 2 * H, tokens=[tok("solana", M1)], kind="AGGREGATOR")
    post(con, "u3", None, D1 + 3 * H, tokens=[tok("solana", M1)])                       # author unknown
    t1 = post(con, "p1", "person_main", D1 + 4 * H, tokens=[tok("solana", M1)])
    t2 = post(con, "p2", "person_alt", D1 + 5 * H, tokens=[tok("solana", M1)])
    store.upsert_trader(con, "trader_x", "invented trader", now=D1)
    store.link_trader_account(con, "trader_x", t1["account"], "LAB_ASSERTED", "INFERENCE", now=D1)
    store.link_trader_account(con, "trader_x", t2["account"], "LAB_ASSERTED", "INFERENCE", now=D1)
    r, cl = snap(con)
    c = cl[K1]
    rl = roles(con, r["run_id"], K1)
    assert rl["x:u1"] == rl["x:u2"] == rl["x:u3"] == "UNVERIFIED_ORIGINAL"
    why = {m["item_key"]: m["why"] for m in NR.members(con, r["run_id"], K1)}
    assert why["x:u1"] == "account_kind_bot" and why["x:u2"] == "account_kind_aggregator" and why["x:u3"] == "unknown_author"
    assert c["independent_source_count"] == 1             # trader_x, two linked accounts, counted once
    assert c["independent_group_count"] == 2              # two separate originals, same source


# ---------- clustering: identity, tickers, themes ----------

def test_same_ticker_on_different_contracts_stays_in_separate_clusters(con):
    cover(con)
    s1, s2 = A["PEPE_SOL1"], A["PEPE_SOL2"]
    post(con, "t1", "acc_a", D1 + H, tokens=[tok("solana", s1)])
    post(con, "t2", "acc_b", D1 + 2 * H, tokens=[tok("solana", s2)])
    post(con, "t3", "acc_c", D1 + 3 * H, tokens=[tick("PEPE")])
    r, cl = snap(con)
    k1, k2 = f"ca:solana:{s1}", f"ca:solana:{s2}"
    assert set(cl) == {k1, k2}
    assert cl[k1]["item_count"] == cl[k2]["item_count"] == 1
    for k, other in ((k1, k2), (k2, k1)):
        f = [x for x in cl[k]["flags"] if x["flag"] == "ticker_collision"]
        assert f and f[0]["other_clusters"] == [other] and f[0]["symbol"] == "PEPE"
    assert r["unassigned"]["ticker_only_mentions"] == {"PEPE": 1}
    assert r["unassigned"]["claims_by_reason"] == {"token_not_resolved_to_a_contract": 1}


def test_ticker_only_claims_never_create_or_join_a_contract_cluster(con):
    cover(con)
    post(con, "t1", "acc_a", D1 + H, tokens=[tick("LABDOG")])
    post(con, "t2", "acc_b", D1 + 2 * H, tokens=[])
    r, cl = snap(con)
    assert cl == {} and r["run"]["cluster_count"] == 0
    assert r["unassigned"]["claims_by_reason"] == {"no_token_and_no_theme_tag": 1, "token_not_resolved_to_a_contract": 1}


def test_multi_token_theme_links_tokens_and_chains(con):
    cover(con)
    base = "0x" + "ab" * 20
    post(con, "m1", "acc_a", D1 + H, tokens=[tok("solana", M1), tok("base", base)], tags=["ai_agent"])
    post(con, "m2", "acc_b", D1 + 2 * H, tokens=[tok("solana", M1)], tags=["ai_agent"])
    post(con, "m3", "acc_c", D1 + 3 * H, tokens=[], tags=["ai_agent"])
    r, cl = snap(con)
    kb = f"ca:base:{base}"
    assert set(cl) == {K1, kb, "tag:ai_agent"}
    th = cl["tag:ai_agent"]
    assert th["cluster_kind"] == "THEME" and th["item_count"] == 3 and th["independent_source_count"] == 3
    assert th["chains"] == ["base", "solana"]
    assert {(t["chain"], t["contract"]): t["claims"] for t in th["linked_tokens"]["tokens"]} == {("solana", M1): 2, ("base", base): 1}
    assert cl[K1]["item_count"] == 2 and cl[kb]["item_count"] == 1
    assert [t["tag"] for t in cl[K1]["linked_tokens"]["tags"]] == ["ai_agent"]
    assert [t["contract"] for t in cl[K1]["linked_tokens"]["tokens"]] == [base]
    assert "theme" in th["label"]


# ---------- conflicts and changed opinions ----------

def test_conflicting_independent_narratives_are_flagged_not_averaged(con):
    cover(con)
    for i in range(5):
        post(con, f"p{i}", f"bull_{i}", D1 + H + i, tokens=[tok("solana", M1)], stance="positive")
    post(con, "n1", "bear_a", D1 + 3 * H, tokens=[tok("solana", M1)], stance="negative", category="risk")
    r, cl = snap(con)
    c = cl[K1]
    assert c["independent_source_count"] == 6                       # would be HIGH without the disagreement
    assert c["conflicted"] == 1 and c["stance"] == {"negative": 1, "positive": 5}
    assert c["confidence"] == "MODERATE"
    assert any("capped at MODERATE: sources disagree" in b for b in NR.explain(con, r["run_id"], K1)["confidence_basis"])


def test_a_contradicts_relation_between_claims_also_marks_the_conflict(con):
    cover(con)
    a = post(con, "p1", "acc_a", D1 + H, tokens=[tok("solana", M1)])
    b = post(con, "p2", "acc_b", D1 + 2 * H, tokens=[tok("solana", M1)])
    store.relate_claims(con, a["claim_id"], b["claim_id"], "CONTRADICTS", now=D1)
    r, cl = snap(con)
    assert cl[K1]["conflicted"] == 1


def test_changed_opinion_counts_only_the_latest_stance_of_that_source(con):
    cover(con)
    post(con, "w1", "flipper", D1 + H, tokens=[tok("solana", M1)], stance="positive")
    post(con, "w2", "flipper", D1 + 6 * H, tokens=[tok("solana", M1)], stance="negative")
    post(con, "w3", "steady", D1 + 2 * H, tokens=[tok("solana", M1)], stance="positive")
    r, cl = snap(con)
    c = cl[K1]
    assert c["stance"] == {"negative": 1, "positive": 1}
    assert [(x["source_id"], x["from"], x["to"]) for x in c["opinion_changes"]] == [("x:id:flipper", "positive", "negative")]
    assert c["independent_source_count"] == 2 and c["independent_group_count"] == 3     # three originals, two sources
    assert "Opinion change" in " ".join(NR.explain(con, r["run_id"], K1)["plain"])


def test_sarcasm_and_neutral_posts_do_not_vote(con):
    cover(con)
    post(con, "s1", "sarcast", D1 + H, tokens=[tok("solana", M1)], stance="positive", sarcasm=1)
    post(con, "s2", "plain", D1 + 2 * H, tokens=[tok("solana", M1)], stance="negative")
    r, cl = snap(con)
    assert cl[K1]["stance"] == {"negative": 1, "neutral": 1} and cl[K1]["conflicted"] == 0


# ---------- deleted, inaccessible, unobserved ----------

def test_deleted_original_stays_an_origin_but_its_stance_is_not_counted(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)], stance="positive", later=[(D1 + 8 * H, "DELETED")])
    post(con, "o2", "orig_two", D1 + 2 * H, tokens=[tok("solana", M1)], stance="negative")
    post(con, "rp", "reposter", D1 + 3 * H, tokens=[tok("solana", M1)], refs=[("retweeted", "x:o1")], text="invented post o1", attribution="reposted")
    r, cl = snap(con)
    c = cl[K1]
    assert c["independent_source_count"] == 2                # the deleted original was observed; reposts still depend on it
    assert c["stance"] == {"negative": 1} and c["conflicted"] == 0
    f = [x for x in c["flags"] if x["flag"] == "inaccessible_sources"][0]
    assert f["items"] == 1 and f["of_which_gone"] == 1
    assert {m["item_key"]: m["source_state"] for m in NR.members(con, r["run_id"], K1)}["x:o1"] == "inaccessible:DELETED"
    assert c["confidence"] == "MODERATE"


def test_a_protected_or_blocked_source_keeps_its_stance_and_lowers_confidence(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)], stance="positive", later=[(D1 + 8 * H, "PROTECTED")])
    post(con, "o2", "orig_two", D1 + 2 * H, tokens=[tok("solana", M1)], stance="positive")
    r, cl = snap(con)
    assert cl[K1]["stance"] == {"positive": 2} and cl[K1]["confidence"] == "MODERATE"


# ---------- coverage ----------

def test_no_coverage_record_means_volume_is_not_estimable(con):
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    r, cl = snap(con)
    assert cl[K1]["status"] == "insufficient_coverage" and cl[K1]["reasons"] == ["no_coverage_record:x"]
    assert cl[K1]["independent_source_count"] is None and cl[K1]["item_count"] == 1
    r2, cl2 = snap(con, params={"require_coverage": False})
    assert cl2[K1]["status"] == "ok" and cl2[K1]["independent_source_count"] == 1


def test_a_coverage_gap_is_insufficient_and_partial_coverage_gives_lower_bounds(con):
    cover(con, status="GAP", reason="rate_limited")
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    r, cl = snap(con)
    assert cl[K1]["status"] == "insufficient_coverage" and cl[K1]["reasons"] == ["coverage_gap:x"]
    cover(con, status="COVERED", run="r2")
    cover(con, status="PARTIAL", run="r3", reason="sampled")
    post(con, "o2", "orig_two", D1 + 2 * H, tokens=[tok("solana", M1)])
    r2, cl2 = snap(con)
    assert cl2[K1]["status"] == "ok" and cl2[K1]["coverage"]["counts_are_lower_bounds"] is True
    assert cl2[K1]["confidence"] == "MODERATE"
    assert cl2[K1]["coverage"]["platforms"]["x"]["statuses"] == {"COVERED": 1, "GAP": 1, "PARTIAL": 1}


def test_only_unattributable_sources_is_not_estimable(con):
    cover(con)
    post(con, "u1", None, D1 + H, tokens=[tok("solana", M1)])
    r, cl = snap(con)
    assert cl[K1]["status"] == "insufficient_coverage" and cl[K1]["reasons"] == ["no_attributable_source"]


def test_items_with_no_usable_time_make_volume_not_estimable(con):
    cover(con)
    acct = store.upsert_account(con, "x", handle="no_time", provider_user_id="no_time", now=D1)
    o = store.record_observation(con, platform="x", access_mode="fixture", collector="t", provider_item_id="nt1", account_id=acct,
                                 original_url="https://example.invalid/nt1", observed_at=None, text="invented nt1", now=D1 + H)
    # observed_at unknown and no publication time: the observation falls back to ingestion time for the cutoff only
    con.execute("INSERT INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,extractor_version,"
                "analysis_version,status,mode,extracted_at) VALUES ('k-nt1',?,?,?,?,?,?,?,?,?,?)",
                (o["id"], o["item_key"], store.text_hash("invented nt1"), "c", "deterministic", "t1", EXTRACT_V, "ok", "none", D1 + H))
    eid = con.execute("SELECT extraction_id FROM social_claim_extractions").fetchone()[0]
    c = store.add_claim(con, claim_type="OTHER", analysis_version=EXTRACT_V, item_key=o["item_key"], account_id=acct, now=D1 + H)
    con.execute("INSERT INTO social_claim_attributes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (c["id"], eid, 0, "bullish", "opinion", "positive", 0, 0, 0, "unspecified", "not_disclosed", "author", None, None, "low", "[]",
                 "unverified_text_claim", "[]", json.dumps([tok("solana", M1)])))
    r, cl = snap(con)
    assert cl[K1]["status"] == "insufficient_coverage" and "time_unknown_for_most_items" in cl[K1]["reasons"]
    assert cl[K1]["window_mentions"] == 0


# ---------- time zones, boundaries, staleness ----------

def test_naive_or_missing_window_is_refused(con):
    with pytest.raises(ValueError):
        NR.snapshot(con, window_start=datetime(2026, 10, 12), window_end=datetime(2026, 10, 13), now=D2)
    with pytest.raises(ValueError):
        NR.snapshot(con, now=D2)


def test_day_window_follows_the_zone_and_dst_changes_the_day_length():
    s, e = NR.day_window("2026-10-12", "America/New_York")
    assert (s, e) == (D1 + 4 * H, D2 + 4 * H)
    s, e = NR.day_window("2026-11-01", "America/New_York")        # clocks go back: a 25 hour day
    assert e - s == 25 * H
    s, e = NR.day_window("2026-03-08", "America/New_York")        # clocks go forward: a 23 hour day
    assert e - s == 23 * H
    s, e = NR.day_window("2026-10-12", "Pacific/Auckland")
    assert e - s == 24 * H and s == D1 - 13 * H
    s, e = NR.day_window("2026-10-12")
    assert (s, e) == (D1, D2)


def test_the_same_late_evening_post_is_in_different_days_depending_on_the_zone(con):
    cover(con, end=D1 + 9 * 86400)
    local = datetime.fromisoformat("2026-10-12T23:30:00-04:00").timestamp()          # 03:30 UTC on the 13th
    assert local == D2 + 3 * H + 1800
    post(con, "late", "acc_a", local, tokens=[tok("solana", M1)])
    now = D2 + 2 * 86400
    _, ny12 = snap(con, day="2026-10-12", tz="America/New_York", now=now)
    _, utc12 = snap(con, day="2026-10-12", tz="UTC", now=now)
    _, utc13 = snap(con, day="2026-10-13", tz="UTC", now=now)
    _, ny13 = snap(con, day="2026-10-13", tz="America/New_York", now=now)
    assert ny12[K1]["window_mentions"] == 1 and utc13[K1]["window_mentions"] == 1
    assert K1 not in utc12                                                            # observed after the UTC day ended: not known yet
    assert ny13[K1]["window_mentions"] == 0 and ny13[K1]["item_count"] == 1        # history, but it happened before the NY 13th began


def test_window_is_half_open_and_an_item_at_the_end_belongs_to_the_next_day(con):
    cover(con, end=D1 + 9 * 86400)
    post(con, "edge1", "acc_a", D1, obs=D1 + 5, tokens=[tok("solana", M1)])              # exactly at the start
    post(con, "edge2", "acc_b", D2, obs=D2 + 5, tokens=[tok("solana", M1)])              # exactly at the end of day 1
    _, d1 = snap(con, day="2026-10-12", now=D2 + 100)
    _, d2 = snap(con, day="2026-10-13", now=D2 + 86400)
    assert d1[K1]["window_mentions"] == 1 and d1[K1]["item_count"] == 1                  # edge2 is after the cutoff
    assert d2[K1]["window_mentions"] == 1 and d2[K1]["item_count"] == 2


def test_stale_cluster_is_marked_dormant_and_a_late_observation_is_not_todays_mention(con):
    cover(con, end=D1 + 30 * 86400)
    old = D1 - 10 * 86400
    post(con, "old1", "acc_a", old, tokens=[tok("solana", M1)])
    post(con, "old2", "acc_b", old + H, tokens=[tok("solana", M1)])
    _, cl = snap(con, now=D2)
    c = cl[K1]
    assert c["freshness"] == "STALE" and c["window_mentions"] == 0 and c["confidence"] == "LOW"
    assert c["first_observed_at"] == old + 30
    post(con, "late1", "acc_c", old + 2 * H, obs=D1 + 6 * H, tokens=[tok("solana", M1)])  # published 10 days ago, observed today
    r2, cl2 = snap(con, now=D2)
    c2 = cl2[K1]
    assert c2["window_mentions"] == 0 and c2["item_count"] == 3
    assert [f["items"] for f in c2["flags"] if f["flag"] == "late_observed_items"] == [1]
    assert c2["freshness"] == "FRESH"                       # something was observed in the last 48 hours, but nothing new happened
    assert {m["item_key"]: m["event_time_basis"] for m in NR.members(con, r2["run_id"], K1)}["x:late1"] == "PROVIDER"


def test_sliding_windows_report_rate_of_change(con):
    cover(con)
    end = D2
    for i in range(2):
        post(con, f"w{i}", f"acc_{i}", end - 5400 - i * 60, tokens=[tok("solana", M1)])           # previous hour: 2
    for i in range(6):
        post(con, f"v{i}", f"acc_v{i}", end - 1800 - i * 60, tokens=[tok("solana", M1)])          # last hour: 6
    r, cl = snap(con)
    w = cl[K1]["windows"]["3600"]
    assert (w["current"], w["previous"], w["delta"], w["pct_change"]) == (6, 2, 4, 200.0)
    assert w["peak_sliding"] == 6
    assert cl[K1]["windows"]["origins"]["3600"]["current"] == 6
    assert cl[K1]["windows"]["86400"]["current"] == 8 and cl[K1]["windows"]["86400"]["pct_change"] is None


# ---------- snapshots, determinism, provenance ----------

def test_snapshot_is_idempotent_immutable_and_a_replay_of_a_past_window_reproduces_it(con):
    cover(con, end=D1 + 9 * 86400)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    r1, _ = snap(con, now=D2)
    assert r1["created"] is True
    r1b, _ = snap(con, now=D2)
    assert r1b["created"] is False and r1b["run_id"] == r1["run_id"]
    before = con.execute("SELECT * FROM social_narrative_clusters WHERE run_id=?", (r1["run_id"],)).fetchall()
    post(con, "o9", "orig_nine", D2 + H, tokens=[tok("solana", M1)])                       # next day's data arrives
    r1c, _ = snap(con, now=D2 + 5 * 86400)                                                  # replay day 1 much later
    assert r1c["created"] is False and r1c["run_id"] == r1["run_id"]
    after = con.execute("SELECT * FROM social_narrative_clusters WHERE run_id=?", (r1["run_id"],)).fetchall()
    assert [tuple(x) for x in before] == [tuple(x) for x in after]
    post(con, "o2", "orig_two", D1 + 2 * H, obs=D2 - 60, tokens=[tok("solana", M1)])        # a day-1 post found late, still before the cutoff
    r1d, _ = snap(con, now=D2)
    assert r1d["created"] is True and r1d["run_id"] != r1["run_id"]                       # new information is a new run, the old one is kept
    assert con.execute("SELECT COUNT(*) FROM social_narrative_runs").fetchone()[0] == 2


def test_open_window_is_marked_incomplete_and_the_cutoff_is_the_clock(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    post(con, "o2", "orig_two", D1 + 20 * H, tokens=[tok("solana", M1)])
    r, cl = snap(con, now=D1 + 10 * H)
    assert r["run"]["window_complete"] == 0 and r["run"]["cutoff"] == D1 + 10 * H
    assert cl[K1]["item_count"] == 1                          # nothing observed after the clock is used


def test_every_member_names_its_claim_observation_and_reason_and_the_text_is_never_stored(con):
    cover(con)
    p = post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    r, cl = snap(con)
    m = NR.members(con, r["run_id"], K1)
    assert len(m) == 1 and m[0]["claim_id"] == p["claim_id"] and m[0]["observation_id"] == p["obs"]
    assert m[0]["why"] == "earliest_self_originated_item_in_group" and m[0]["event_time_basis"] == "PROVIDER"
    blob = json.dumps([dict(x) for t in ("social_narrative_runs", "social_narrative_clusters", "social_narrative_members",
                                         "social_narrative_edges", "social_narrative_changes")
                       for x in con.execute(f"SELECT * FROM {t}")], default=str)
    assert "invented post" not in blob


def test_snapshot_marks_fixture_data(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)], mode="fixture")
    r, cl = snap(con)
    assert r["run"]["contains_fixture"] == 1 and any(f["flag"] == "contains_fixture_data" for f in cl[K1]["flags"])
    assert "fixture" in NR.report(con, r["run_id"]).lower()


def test_superseded_extractions_are_ignored(con):
    cover(con)
    p = post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    con.execute("INSERT INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,extractor_version,"
                "analysis_version,status,mode,extracted_at) VALUES ('k2',?,?,?,?,?,?,?,?,?,?)",
                (p["obs"], p["item"], store.text_hash("invented post o1"), "c", "deterministic", "t2", EXTRACT_V, "ok", "none", D1 + 2 * H))
    new = con.execute("SELECT extraction_id FROM social_claim_extractions WHERE extraction_key='k2'").fetchone()[0]
    con.execute("UPDATE social_claim_extractions SET superseded_by=? WHERE extraction_key='k-o1'", (new,))
    r, cl = snap(con)
    assert cl == {} and r["unassigned"]["claims_by_reason"] == {} and r["run"]["input_claims"] == 0


# ---------- explainability ----------

def test_why_this_cluster_explains_rule_members_groups_and_confidence(con):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    post(con, "o2", "orig_two", D1 + 2 * H, tokens=[tok("solana", M1)])
    for i in range(3):
        post(con, f"rp{i}", f"rep_{i}", D1 + 3 * H + i, tokens=[tok("solana", M1)], refs=[("retweeted", "x:o1")], text="invented post o1",
             attribution="reposted")
    r, _ = snap(con)
    w = NR.explain(con, r["run_id"], K1)
    assert "chain and contract" in w["why_cluster"]["rule"] and "ticker" in w["why_cluster"]["never_used"]
    assert w["independence"]["independent_sources"] == ["x:id:orig_one", "x:id:orig_two"]
    assert [m["role"] for m in w["members"]].count("AMPLIFIER") == 3
    assert all(m["claim_id"] and m["observation_id"] and m["why"] for m in w["members"])
    assert len(w["edges"]) == 3 and {e["edge_type"] for e in w["edges"]} == {"repost"}
    assert w["confidence"] == "MODERATE" and w["confidence_basis"][0] == "2 independent source(s)"
    text = " ".join(w["plain"])
    assert "Independent sources: 2" in text and "Amplifiers" in text and "counted as one origin" in text
    with pytest.raises(KeyError):
        NR.explain(con, r["run_id"], "ca:solana:nope")


# ---------- two controlled fixture windows: the daily change proof ----------

def load_fixture(con, day):
    for t, v in FXD["tokens"].items():
        pass
    chain_of = {n: (v[0], v[1]) for n, v in FXD["tokens"].items()}
    SYMS.update({v[1]: v[2] for v in FXD["tokens"].values()})
    n = 0
    for p in FXD["posts"]:
        if (D1 if day == 1 else D2) <= p["at"] < (D2 if day == 1 else D2 + 86400):
            post(con, p["id"], p["acct"], p["at"], tokens=[tok(*chain_of[t]) for t in p["tokens"]], tags=p["tags"], stance=p["stance"],
                 text=p["text"], refs=[tuple(r) for r in p.get("refs", [])], attribution=p.get("attribution", "author"))
            n += 1
    return n


def test_two_controlled_windows_produce_the_expected_daily_change(con):
    exp = FXD["expected"]
    assert FXD["d1_start"] == D1
    cover(con, start=D1, end=D1 + 3 * 86400, run="cov1")
    load_fixture(con, 1)
    r1, c1 = snap(con, day="2026-10-12", now=D2)
    assert set(c1) == set(exp["day1"]["clusters"])
    for key, e in (("M1", exp["day1"]["M1"]), ("M2", exp["day1"]["M2"])):
        c = c1[f"ca:{FXD['tokens'][key][0]}:{FXD['tokens'][key][1]}"]
        for field, val in e.items():
            assert c[field] == val, (key, field)
    assert r1["summary"]["changes"] == exp["day1"]["changes"] and r1["summary"]["prev_run_id"] is None
    assert r1["run"]["prev_run_id"] is None

    load_fixture(con, 2)
    r2, c2 = snap(con, day="2026-10-13", now=D2 + 86400)
    assert r2["run"]["prev_run_id"] == r1["run_id"]
    m1 = c2[K1]
    for field, val in exp["day2"]["M1"].items():
        assert m1[field] == val, field
    assert r2["summary"]["changes"] == exp["day2"]["changes"]
    ch = {(c["cluster_key"], c["change_type"]): c for c in NR.changes_for(con, r2["run_id"])}
    assert {k for k, t in ch if t == "DORMANT"} == set(exp["day2"]["dormant"])
    assert {k for k, t in ch if t == "NEW"} == set(exp["day2"]["new"])
    up = ch[(K1, "ACTIVITY_UP")]
    assert (up["before"]["window_mentions"], up["after"]["window_mentions"]) == (5, 21)
    ind = ch[(K1, "INDEPENDENCE_CHANGED")]
    assert (ind["before"]["independent_source_count"], ind["after"]["independent_source_count"]) == (2, 3)
    cf = ch[(K1, "CONFLICT_CHANGED")]
    assert (cf["before"]["conflicted"], cf["after"]["conflicted"]) == (0, 1)
    assert any(f["flag"] == "burst_amplification" for f in m1["flags"])            # 20 amplifiers inside a minute: a hypothesis, not a finding
    assert m1["independent_source_count"] == 3                                       # the 20 reposts added no independent source
    # day 1 is untouched by day 2 (immutable) and a replay reproduces it
    again, _ = snap(con, day="2026-10-12", now=D2 + 86400)
    assert again["created"] is False and again["run_id"] == r1["run_id"]
    assert NR.run_view(con, r1["run_id"])["summary"]["changes"] == exp["day1"]["changes"]
    text = NR.report(con, r2["run_id"])
    assert "1 NEW" in text and "2 DORMANT" in text and "1 ACTIVITY_UP" in text


# ---------- schema, guard, CLI ----------

def test_migration_7_rolls_back_cleanly(con):
    assert schema.current_version(con) == schema.LATEST and 7 in schema.ALL_VERSIONS
    above_6 = [v for v in schema.ALL_VERSIONS if v > 6]
    assert above_6[0] == 7
    assert schema.rollback(con, 6) == above_6[::-1]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not names & {n for n in schema.SOCIAL_TABLES if n.startswith("social_narrative_")}
    assert "social_claim_spans" in names
    assert schema.migrate(con) == above_6


def test_content_guard_passes_on_a_populated_narrative_database(con, tmp_path):
    cover(con)
    post(con, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    snap(con)
    con.commit()
    con.execute("PRAGMA wal_checkpoint(FULL)")
    assert content_guard.check_sqlite("t.sqlite", tmp_path / "t.sqlite") == []


def test_cli_snapshot_show_why_and_changes(tmp_path):
    dbp = tmp_path / "t.sqlite"
    db.init_db(dbp)
    c = sqlite3.connect(dbp)
    c.row_factory = sqlite3.Row
    store.register_analysis_version(c, EXTRACT_V, "extractor", "test builder", now=D1)
    cover(c)
    SYMS.update({M1: "LABDOG"})
    post(c, "o1", "orig_one", D1 + H, tokens=[tok("solana", M1)])
    post(c, "o2", "orig_two", D1 + 2 * H, tokens=[tok("solana", M1)])
    c.commit()
    c.close()

    def run(*args):
        p = subprocess.run([sys.executable, "-m", "memelab", "social", *args, "--db", str(dbp)], cwd=ROOT, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    rc, out, err = run("narrative-snapshot", "--day", "2026-10-12", "--now", str(D2))
    assert rc == 0, err
    j = json.loads(out)
    assert j["created"] is True and j["summary"]["changes"] == {"NEW": 1}
    assert any("independent sources 2" in line for line in j["report"])
    rc, out, _ = run("narrative-snapshot", "--day", "2026-10-12", "--now", str(D2))
    assert rc == 0 and json.loads(out)["created"] is False
    rc, out, _ = run("narrative-show")
    assert rc == 0 and "LABDOG" in out and "independent sources 2" in out
    rc, out, _ = run("narrative-why", "--run", str(j["run_id"]), "--cluster", K1)
    assert rc == 0 and json.loads(out)["confidence"] == "MODERATE"
    rc, out, _ = run("narrative-why", "--run", str(j["run_id"]), "--cluster", "ca:solana:nope")
    assert rc == 1
    rc, out, _ = run("narrative-changes", "--run", str(j["run_id"]))
    assert rc == 0 and json.loads(out)["changes"][0]["change_type"] == "NEW"
    rc, out, err = run("narrative-snapshot")
    assert rc == 2

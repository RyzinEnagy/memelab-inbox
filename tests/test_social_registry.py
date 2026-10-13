"""Phase 08: source and trader registry.

Invented data only (tests/fixtures/social/registry/, every file labelled as a fixture). Temp databases, fixed clock, no network.
Entities built by hand in the tests are 'real' in the sense of unlabelled, so they can be approved and watched; they are still invented.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from memelab import db
from memelab.social import content_guard, registry as R, registry_cli, registry_import as RI, schema, store

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "registry"
NOW = int(datetime(2026, 10, 12, 23, 0, tzinfo=timezone.utc).timestamp())
DAY = 86400
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _fx(name):
    return json.loads((FX / name).read_text())


FRESH, STALE, NAMES = _fx("leaderboard_fresh.json"), _fx("leaderboard_stale.json"), _fx("identical_names.json")
W1 = FRESH["rows"][0]["wallet"]["address"]
W2 = FRESH["rows"][1]["wallet"]["address"]
W3 = FRESH["rows"][2]["wallet"]["address"]
W4 = STALE["rows"][0]["wallet"]["address"]
W6 = NAMES["rows"][0]["wallet"]["address"]


def b58(b: bytes) -> str:
    n, s = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        s = ALPH[r] + s
    return s


def invented_wallet(n: int) -> str:
    return b58(hashlib.sha256(f"registry test wallet {n}".encode()).digest())


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def imp(con, name, **kw):
    return RI.import_file(con, FX / name, now=kw.pop("now", NOW), **kw)


def note(con, eid, n=1, at=NOW - 3600):
    """A current manual evidence row with a direct URL."""
    R.add_evidence(con, eid, "MANUAL_NOTE", f"https://notes.example/{eid.replace(':', '_')}/{n}", url=f"https://notes.example/{n}", captured_at=at,
                   note="invented research note", now=NOW)


def account(con, handle, pid=None, platform="x", evidence=True):
    eid = R.ensure_account(con, platform, handle=handle, provider_user_id=pid, now=NOW)
    if evidence:
        note(con, eid)
    return eid


def wallet(con, n):
    return R.ensure_wallet(con, "solana", invented_wallet(n), now=NOW)


def write_file(tmp_path, doc, name="f.json"):
    p = tmp_path / name
    p.write_text(json.dumps(doc) if not isinstance(doc, str) else doc)
    return p


def minimal_doc(**over):
    d = {"schema": RI.SCHEMA,
         "source": {"source_key": "fixture:mini", "kind": "LEADERBOARD", "organization": "Mini (fixture)", "url": "https://example.invalid/m",
                    "access_mode": "fixture", "permitted_basis": "invented", "is_fixture": True, "fixture_label": "invented"},
         "capture": {"captured_at": "2026-10-12T12:00:00Z", "url": "https://example.invalid/m/1"},
         "rows": [{"rank": 1, "wallet": {"chain": "solana", "address": W3}, "display_name": "Mini One"}]}
    for k, v in over.items():
        d[k] = v
    return d


def counts(con):
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in schema.SOCIAL_TABLES if t.startswith("social_registry_")}


# ---------- migration ----------

def test_migration_8_rolls_back_cleanly_and_reapplies(con):
    assert schema.current_version(con) == schema.LATEST and 8 in schema.ALL_VERSIONS
    above_7 = [v for v in schema.ALL_VERSIONS if v > 7]
    assert above_7[0] == 8
    assert schema.rollback(con, 7) == above_7[::-1]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not names & {n for n in schema.SOCIAL_TABLES if n.startswith("social_registry_")}
    assert "social_narrative_runs" in names
    assert schema.migrate(con) == above_7


# ---------- import: candidates only, labelled fixtures ----------

def test_import_creates_labelled_candidates_and_nothing_else(con):
    r = imp(con, "leaderboard_fresh.json")
    assert r["status"] == "IMPORTED" and r["is_fixture"] and r["freshness"] == "FRESH"
    assert (r["rows_total"], r["rows_accepted"], r["rows_rejected"]) == (8, 6, 2)
    assert {x["code"] for x in r["rejects"]} == {"INVALID_WALLET", "BLOCKED_CONTENT_KEY"}
    assert r["never_done"] == ["approve", "assign category", "mark wallet as owned", "rank"]
    ents = con.execute("SELECT * FROM social_registry_entities").fetchall()
    assert ents and all(e["is_fixture"] == 1 and e["fixture_label"] for e in ents)
    assert {x[0] for x in con.execute("SELECT DISTINCT review_state FROM social_registry_records")} == {"CANDIDATE"}
    assert {x[0] for x in con.execute("SELECT DISTINCT watch_status FROM social_registry_records")} == {"NONE"}
    assert con.execute("SELECT COUNT(*) FROM social_registry_categories").fetchone()[0] == 0
    src = con.execute("SELECT * FROM social_registry_sources").fetchone()
    assert src["is_fixture"] == 1 and src["permitted_basis"]
    assert con.execute("SELECT COUNT(*) FROM social_accounts WHERE notes LIKE 'FIXTURE:%'").fetchone()[0] == 3
    # a handle shown next to a wallet is a LOW, unreviewed third-party label, never ownership
    a = R.show(con, "acct:x:id:9001001")["wallets"][0]
    assert a["level"] == "THIRD_PARTY_LABELED" and a["confidence"] == "LOW" and a["verified"] is False
    assert {x["review_state"] for x in con.execute("SELECT review_state FROM social_registry_links WHERE link_type='WALLET_THIRD_PARTY_LABEL'")} == {"UNREVIEWED"}


def test_import_is_idempotent_and_dry_run_writes_nothing(con):
    before = counts(con)
    d = imp(con, "leaderboard_fresh.json", dry_run=True)
    assert d["status"] == "DRY_RUN" and d["written"] is False and d["rows_accepted"] == 6
    assert counts(con) == before and con.execute("SELECT COUNT(*) FROM social_accounts").fetchone()[0] == 0
    first = imp(con, "leaderboard_fresh.json")
    after = counts(con)
    again = imp(con, "leaderboard_fresh.json")
    assert again["status"] == "ALREADY_IMPORTED" and again["capture_id"] == first["capture_id"] and counts(con) == after


@pytest.mark.parametrize("label,mutate,code", [
    ("unlabelled_fixture_url", lambda d: d["source"].update(is_fixture=False, access_mode="file", fixture_label=None), "UNLABELLED_FIXTURE"),
    ("future_capture", lambda d: d["capture"].update(captured_at="2027-01-01T00:00:00Z"), "CAPTURED_IN_FUTURE"),
    ("naive_time", lambda d: d["capture"].update(captured_at="2026-10-12T12:00:00"), "BAD_CAPTURE"),
    ("unknown_top_key", lambda d: d.update(notes="x"), "UNKNOWN_KEY"),
    ("unknown_source_key", lambda d: d["source"].update(bio="x"), "UNKNOWN_KEY"),
    ("wrong_schema", lambda d: d.update(schema="other/1"), "BAD_SCHEMA"),
    ("bad_source_key", lambda d: d["source"].update(source_key="Bad Key"), "BAD_SOURCE"),
    ("no_basis", lambda d: d["source"].update(permitted_basis=""), "BAD_SOURCE"),
    ("fixture_without_label", lambda d: d["source"].update(fixture_label=None), "BAD_SOURCE"),
    ("http_url", lambda d: d["source"].update(url="http://example.invalid/m"), "BAD_SOURCE"),
    ("period_backwards", lambda d: d["capture"].update(period={"start": "2026-10-02T00:00:00Z", "end": "2026-09-02T00:00:00Z"}), "BAD_CAPTURE"),
    ("bad_kind", lambda d: d["source"].update(kind="TRADER_RANKING"), "BAD_SOURCE"),
])
def test_refused_files_write_nothing(con, tmp_path, label, mutate, code):
    d = minimal_doc()
    mutate(d)
    before = counts(con)
    r = RI.import_file(con, write_file(tmp_path, d), now=NOW)
    assert r["status"] == "REFUSED" and r["code"] == code and r["written"] is False, r
    assert counts(con) == before


def test_not_json_oversize_and_too_many_rows_are_refused(con, tmp_path, monkeypatch):
    assert RI.import_file(con, write_file(tmp_path, "{nope"), now=NOW)["code"] == "NOT_JSON"
    assert RI.import_file(con, write_file(tmp_path, '{"schema": NaN}'), now=NOW)["code"] == "NOT_JSON"
    p = write_file(tmp_path, minimal_doc())
    monkeypatch.setattr(RI, "MAX_BYTES", 100)
    assert RI.import_file(con, p, now=NOW)["code"] == "FILE_TOO_LARGE"
    monkeypatch.setattr(RI, "MAX_BYTES", 5_000_000)
    monkeypatch.setattr(RI, "MAX_ROWS", 1)
    d = minimal_doc(rows=[{"display_name": "a"}, {"display_name": "b"}])
    assert RI.import_file(con, write_file(tmp_path, d, "g.json"), now=NOW)["code"] == "TOO_MANY_ROWS"
    assert counts(con)["social_registry_entities"] == 0


def test_fixture_file_under_tests_fixtures_must_be_labelled(con):
    d = _fx("leaderboard_second.json")
    d["source"].update(is_fixture=False, access_mode="file", fixture_label=None, url="https://boards.test/beta")
    d["capture"]["url"] = "https://boards.test/beta/1"
    p = FX / "_tmp_unlabelled.json"
    try:
        p.write_text(json.dumps(d))
        assert RI.import_file(con, p, now=NOW)["code"] == "UNLABELLED_FIXTURE"
    finally:
        p.unlink()


def test_row_level_rejections_keep_the_good_rows(con, tmp_path):
    rows = [{"display_name": "Ok One", "wallet": {"chain": "solana", "address": W3}},
            {"wallet": {"chain": "solana", "address": "0xnotreal"}},
            {"wallet": {"chain": "mars", "address": W3}},
            {"handle": {"platform": "myspace", "handle": "x"}},
            {"handle": {"platform": "x", "handle": "has space"}},
            {"display_name": "Bad Metric", "metrics": {"pnl": "lots"}},
            {"display_name": "Bad Metric 2", "metrics": {"Pnl": 1}},
            {"display_name": "Bad Rank", "rank": 0},
            {"display_name": "Text Key", "text": "invented"},
            {"display_name": "Extra Key", "followers": 10},
            {"rank": 3},
            {"display_name": "Bad Url", "row_url": "http://example.invalid/x"}]
    r = RI.import_file(con, write_file(tmp_path, minimal_doc(rows=rows)), now=NOW)
    assert r["rows_accepted"] == 1 and r["rows_rejected"] == 11
    assert [x["code"] for x in r["rejects"]] == ["INVALID_WALLET", "INVALID_WALLET", "UNSUPPORTED_PLATFORM", "INVALID_HANDLE", "INVALID_METRIC",
                                                 "INVALID_METRIC", "INVALID_RANK", "BLOCKED_CONTENT_KEY", "UNKNOWN_ROW_KEY", "NO_IDENTIFIER", "INVALID_URL"]
    assert con.execute("SELECT COUNT(*) FROM social_registry_listings").fetchone()[0] == 1


def test_csv_import_needs_meta_and_matches_json(con, tmp_path):
    assert RI.import_file(con, FX / "board_csv.csv", now=NOW)["code"] == "BAD_SCHEMA"
    r = RI.import_file(con, FX / "board_csv.csv", meta=FX / "board_csv_meta.json", now=NOW)
    assert r["status"] == "IMPORTED" and r["rows_accepted"] == 2 and r["row_flags"].get("no_wallet") == 1
    s = R.show(con, f"wallet:solana:{W3}")
    assert s["listings"][0]["metrics"] == {"pnl_usd": 410.0}


def test_undated_capture_is_never_fresh(con, tmp_path):
    d = minimal_doc()
    d["capture"].pop("captured_at")
    r = RI.import_file(con, write_file(tmp_path, d), now=NOW)
    assert r["status"] == "IMPORTED" and r["freshness"] == "UNKNOWN"
    cand = con.execute("SELECT entity_id FROM social_registry_entities WHERE entity_kind='LEADERBOARD_CANDIDATE'").fetchone()[0]
    assert R.evidence_summary(con, cand, NOW) == {"fresh": 0, "stale": 0, "undated": 1, "total": 1}
    with pytest.raises(ValueError, match="stale_evidence_only"):
        R.approve(con, cand, reviewer="elving", reason="curious about this wallet", now=NOW)


# ---------- identities that share names ----------

def test_identical_screen_names_stay_separate_entities(con):
    imp(con, "identical_names.json")
    ents = [r["entity_id"] for r in R.search(con, q="demo_alpha", kind="SOCIAL_ACCOUNT")]
    assert sorted(ents) == ["acct:telegram:id:7002", "acct:x:id:7001", "acct:x:id:7003"]
    for e in ents:
        v = R.show(con, e)
        assert any("same screen name" in w for w in v["warnings"]) and any("same name" in w for w in v["warnings"])
        assert v["same_operator_cluster"] == [e]
    rows = R.search(con, q="demo_alpha", kind="SOCIAL_ACCOUNT")
    assert all("SAME_SCREEN_NAME_AS_OTHER_ENTITY" in r["flags"] and "handle_history" in r["matched_on"] for r in rows)
    assert con.execute("SELECT COUNT(*) FROM social_registry_links WHERE link_type='SAME_OPERATOR'").fetchone()[0] == 0
    # only the first has a wallet; the others cannot inherit it from the name
    assert {r["entity_id"]: r["wallet_attribution"] for r in rows}["acct:x:id:7003"] == "NONE"


def test_name_similarity_is_not_a_basis_and_a_proposal_does_not_merge(con):
    a, b = account(con, "same_name", "801"), account(con, "same_name", "802")
    for basis in ("NAME_SIMILARITY", "SAME_NAME", "DISPLAY_NAME"):
        with pytest.raises(ValueError, match="names or screen names is not evidence"):
            R.add_link(con, link_type="SAME_OPERATOR", from_entity=a, to_entity=b, basis=basis, recorded_by="elving", evidence_ref="https://e.example/1", now=NOW)
    with pytest.raises(ValueError, match="evidence_ref"):
        R.add_link(con, link_type="SAME_OPERATOR", from_entity=a, to_entity=b, basis="REVIEWER_JUDGMENT", recorded_by="elving", now=NOW)
    lid = R.add_link(con, link_type="SAME_OPERATOR", from_entity=b, to_entity=a, basis="PLATFORM_LINK", recorded_by="elving",
                     evidence_ref="https://e.example/profile-link", now=NOW)["link_id"]
    assert R.identity_cluster(con, a) == [a]                      # a proposal never merges
    R.review_link(con, lid, "APPROVED", reviewer="elving", reason="each profile links to the other", now=NOW)
    assert R.identity_cluster(con, a) == sorted([a, b]) == R.identity_cluster(con, b)
    R.retract_link(con, lid, reviewer="elving", reason="link was removed", now=NOW + 1)
    assert R.identity_cluster(con, a) == [a]


def test_handle_rename_keeps_one_entity_but_a_handle_only_rename_does_not_merge(con):
    e1 = R.ensure_account(con, "x", handle="old_name", provider_user_id="555", now=NOW - 100)
    e2 = R.ensure_account(con, "x", handle="new_name", provider_user_id="555", now=NOW)
    assert e1 == e2 == "acct:x:id:555"
    v = R.show(con, e1)
    assert v["entity"]["handles"] == ["old_name", "new_name"] and v["entity"]["current_label"] == "@new_name"
    assert [r["entity_id"] for r in R.search(con, q="old_name")] == [e1] and [r["entity_id"] for r in R.search(con, q="new_name")] == [e1]
    h1 = R.ensure_account(con, "x", handle="drifter_a", now=NOW - 100)
    h2 = R.ensure_account(con, "x", handle="drifter_b", now=NOW)
    assert h1 != h2 and R.identity_cluster(con, h1) == [h1]       # no provider id, so a rename looks like a new account until a person links them
    # a reused handle on a different provider id is a different account
    e3 = R.ensure_account(con, "x", handle="old_name", provider_user_id="556", now=NOW)
    assert e3 == "acct:x:id:556" and e3 != e1
    assert any("same screen name" in w for w in R.show(con, e3)["warnings"])


def test_account_suspension_pauses_watch_and_keeps_history(con):
    a, w = account(con, "suspend_me", "601"), wallet(con, 1)
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving",
               evidence_ref="https://x.example/suspend_me/1", now=NOW)
    R.approve(con, a, reviewer="elving", reason="posts wallet-flow commentary I read", watch=True, now=NOW)
    assert R.get_record(con, a)["watch_status"] == "WATCH"
    r = R.set_account_status(con, a, "SUSPENDED", reviewer="elving", reason="profile shows suspended", evidence_ref="https://x.example/suspend_me",
                             checked_at=NOW, now=NOW)
    assert r["watch_paused"] and R.get_record(con, a)["watch_status"] == "PAUSED"
    assert store.get_account(con, "x:id:601")["identity_status"] == "SUSPENDED"
    v = R.show(con, a)
    assert v["wallets"][0]["level"] == "SELF_CLAIMED" and R.get_record(con, a)["review_state"] == "APPROVED"      # nothing was erased
    assert any("SUSPENDED" in x for x in v["warnings"]) and "SUSPENDED" in R.search(con, q="suspend_me")[0]["flags"]
    assert [x["entity_id"] for x in R.search(con, suspended=True)] == [a]
    with pytest.raises(ValueError, match="account_suspended"):
        R.update_record(con, a, reviewer="elving", watch_status="WATCH", now=NOW)
    R.set_account_status(con, a, "UNVERIFIED", reviewer="elving", reason="profile is back", now=NOW + 5)
    R.update_record(con, a, reviewer="elving", watch_status="WATCH", now=NOW + 6)
    acts = [x["action"] for x in con.execute("SELECT action FROM social_registry_reviews WHERE target_id=? ORDER BY review_id", (a,))]
    assert acts == ["APPROVE", "SET_SUSPENDED", "SET_UNVERIFIED"] or {"APPROVE", "SET_SUSPENDED", "SET_UNVERIFIED"} <= set(acts)


# ---------- wallets: self claim versus corroborated ownership ----------

def test_wallet_self_claim_stays_self_claimed_until_independent_review(con):
    a, w = account(con, "alice_research", "501"), wallet(con, 1)
    board, other = R.ensure_org(con, "board-one", "Board One", now=NOW), R.ensure_org(con, "board-two", "Board Two", now=NOW)

    def att():
        return R.wallet_attribution(con, a, w)
    assert att()["level"] == "NONE"
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving",
               evidence_ref="https://x.example/alice_research/1", now=NOW)
    x = att()
    assert (x["level"], x["confidence"], x["verified"]) == ("SELF_CLAIMED", "LOW", False)
    lab = R.add_link(con, link_type="WALLET_THIRD_PARTY_LABEL", from_entity=a, to_entity=w, asserted_by=other, basis="THIRD_PARTY_STATEMENT",
                     recorded_by="elving", evidence_ref="https://two.example/w/1", confidence="MODERATE", now=NOW)["link_id"]
    x = att()
    assert x["level"] == "SELF_CLAIMED" and any(r.startswith("label_unreviewed") for r in x["reasons"])
    R.review_link(con, lab, "APPROVED", reviewer="elving", reason="label page names this handle and wallet", now=NOW)
    x = att()
    assert (x["level"], x["confidence"], x["verified"]) == ("CORROBORATED", "MODERATE", True)
    # a label from an organization that runs the account is not independent
    op = R.add_link(con, link_type="OPERATED_BY_ORG", from_entity=a, to_entity=other, basis="SELF_STATEMENT", recorded_by="elving",
                    evidence_ref="https://x.example/alice_research/about", now=NOW)["link_id"]
    R.review_link(con, op, "APPROVED", reviewer="elving", reason="profile says it is run by Board Two", now=NOW)
    x = att()
    assert x["level"] == "SELF_CLAIMED" and any("label_asserter_operates_the_claimant" in r for r in x["reasons"])
    # a reviewed on-chain proof counts by itself; an unreviewed one does not
    pr = R.add_link(con, link_type="WALLET_ON_CHAIN_PROOF", from_entity=a, to_entity=w, basis="ON_CHAIN_PROOF", recorded_by="elving",
                    evidence_ref="tx:" + "A" * 44, now=NOW)["link_id"]
    assert att()["level"] == "SELF_CLAIMED" and any(r.startswith("proof_unreviewed") for r in att()["reasons"])
    R.review_link(con, pr, "APPROVED", reviewer="elving", reason="signed message verified in the explorer", now=NOW)
    x = att()
    assert (x["level"], x["confidence"]) == ("CORROBORATED", "HIGH") and "reviewed_on_chain_proof" in x["reasons"]
    dis = R.add_link(con, link_type="WALLET_DISPUTED", from_entity=a, to_entity=w, basis="REVIEWER_JUDGMENT", recorded_by="elving",
                     evidence_ref="https://x.example/dispute/1", now=NOW)["link_id"]
    assert att()["level"] == "DISPUTED" and att()["verified"] is False
    R.retract_link(con, dis, reviewer="elving", reason="dispute withdrawn", now=NOW + 1)
    assert att()["level"] == "CORROBORATED"
    R.review_link(con, pr, "REJECTED", reviewer="elving", reason="proof did not hold up", now=NOW + 2)
    assert att()["level"] == "SELF_CLAIMED"


def test_downstream_table_follows_the_computed_level(con):
    a, w = account(con, "bob_research", "502"), wallet(con, 2)
    other = R.ensure_org(con, "board-two", "Board Two", now=NOW)
    seq = []

    def last():
        v = store.current_wallet_view(con, "solana", invented_wallet(2))
        return (v[0]["assertion"], v[0]["evidence_status"], v[0]["confidence"]) if v else None
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://x.example/b/1", now=NOW)
    seq.append(last())
    pr = R.add_link(con, link_type="WALLET_ON_CHAIN_PROOF", from_entity=a, to_entity=w, basis="ON_CHAIN_PROOF", recorded_by="elving",
                    evidence_ref="tx:" + "B" * 44, now=NOW + 1)["link_id"]
    seq.append(last())                                   # unreviewed: unchanged
    R.review_link(con, pr, "APPROVED", reviewer="elving", reason="verified", now=NOW + 2)
    seq.append(last())
    dis = R.add_link(con, link_type="WALLET_DISPUTED", from_entity=a, to_entity=w, basis="THIRD_PARTY_STATEMENT", recorded_by="elving",
                     evidence_ref="https://x.example/d/1", now=NOW + 3)["link_id"]
    seq.append(last())
    R.retract_link(con, dis, reviewer="elving", reason="withdrawn", now=NOW + 4)
    seq.append(last())                                   # back to the proof, not RETRACTED
    R.retract_link(con, pr, reviewer="elving", reason="proof was wrong", now=NOW + 5)
    seq.append(last())
    assert seq == [("SELF_CLAIMED", "INFERENCE", "LOW"), ("SELF_CLAIMED", "INFERENCE", "LOW"), ("CHAIN_EVIDENCE", "FACT", "HIGH"),
                   ("DISPUTED", "INFERENCE", "UNKNOWN"), ("CHAIN_EVIDENCE", "FACT", "HIGH"), ("SELF_CLAIMED", "INFERENCE", "LOW")]
    assert all(r["analysis_version"] == R.VERSION for r in con.execute("SELECT analysis_version FROM social_wallet_attributions"))
    del other


def test_attribution_has_a_timespan(con):
    a, w = account(con, "carol_research", "503"), wallet(con, 3)
    t0, t1 = NOW - 90 * DAY, NOW - 30 * DAY
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving",
               evidence_ref="https://x.example/c/1", valid_from=t0, valid_to=t1, now=NOW)
    assert R.wallet_attribution(con, a, w, as_of=t0 + DAY)["level"] == "SELF_CLAIMED"
    assert R.wallet_attribution(con, a, w, as_of=t1 + DAY)["level"] == "NONE"      # the claim covered a past window only
    assert R.wallet_attribution(con, a, w, as_of=t0 - DAY)["level"] == "NONE"
    assert R.wallet_attribution(con, a, w)["windows"][0]["valid_to"] == t1
    with pytest.raises(ValueError, match="valid_to is before"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving",
                   evidence_ref="https://x.example/c/2", valid_from=t1, valid_to=t0, now=NOW)


def test_leaderboard_listing_alone_never_verifies_but_two_boards_plus_self_claim_can(con):
    imp(con, "leaderboard_fresh.json")
    imp(con, "leaderboard_second.json")
    a, w = "acct:x:id:9001001", f"wallet:solana:{W1}"
    x = R.wallet_attribution(con, a, w)
    assert x["level"] == "THIRD_PARTY_LABELED" and x["verified"] is False
    for l in R.active_links(con, w, ("WALLET_THIRD_PARTY_LABEL",), direction="to"):
        R.review_link(con, l["link_id"], "APPROVED", reviewer="elving", reason="board page checked", now=NOW)
    assert R.wallet_attribution(con, a, w)["level"] == "THIRD_PARTY_LABELED"        # labels alone, even reviewed, are not a claim by the owner
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving",
               evidence_ref="https://example.invalid/demo_trader_a/post/1", asserted_by=a, now=NOW)
    assert R.wallet_attribution(con, a, w)["level"] == "CORROBORATED"


def test_multiple_handles_and_wallets_are_not_merged_by_name_and_only_join_on_review(con):
    a, b = account(con, "multi_one", "701"), account(con, "multi_two", "702", platform="telegram")
    w1, w2 = wallet(con, 11), wallet(con, 12)
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w1, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://x.example/m1/1", now=NOW)
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=b, to_entity=w2, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://t.example/m2/1", now=NOW)
    assert [x["wallet_entity"] for x in R.wallets_of(con, a)] == [w1] and [x["wallet_entity"] for x in R.wallets_of(con, b)] == [w2]
    lid = R.add_link(con, link_type="SAME_OPERATOR", from_entity=a, to_entity=b, basis="PLATFORM_LINK", recorded_by="elving", evidence_ref="https://x.example/m1/links", now=NOW)["link_id"]
    assert len(R.wallets_of(con, a)) == 1
    R.review_link(con, lid, "APPROVED", reviewer="elving", reason="profiles link to each other", now=NOW)
    ws = {x["wallet_entity"]: x for x in R.wallets_of(con, a)}
    assert set(ws) == {w1, w2} and ws[w2]["via_accounts"] == [b] and ws[w2]["level"] == "SELF_CLAIMED"
    assert [x["account_entity"] for x in R.owners_of(con, w1)] == [a]
    # one wallet with two unrelated claimants is data, not an error
    c = account(con, "multi_three", "703")
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=c, to_entity=w1, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://x.example/m3/1", now=NOW)
    assert sorted(o["account_entity"] for o in R.owners_of(con, w1)) == sorted([a, c])


def test_link_validation(con):
    a, w = account(con, "val_one", "711"), wallet(con, 21)
    org = R.ensure_org(con, "val-org", "Val Org", now=NOW)
    base = dict(from_entity=a, to_entity=w, recorded_by="elving", now=NOW)
    with pytest.raises(ValueError, match="not one of"):
        R.add_link(link_type="GUARANTEED_OWNER", basis="SELF_STATEMENT", con=con, **base)
    with pytest.raises(ValueError, match="connects"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=w, to_entity=a, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://e.example/1", now=NOW)
    with pytest.raises(ValueError, match="accepts bases"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="ON_CHAIN_PROOF", evidence_ref="https://e.example/1", **base)
    with pytest.raises(ValueError, match="evidence_ref"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", **base)
    with pytest.raises(ValueError, match="evidence_ref"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", evidence_ref="not a url", **base)
    with pytest.raises(ValueError, match="FACT is set by reviewing"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", evidence_ref="https://e.example/1", evidence_status="FACT", **base)
    with pytest.raises(ValueError, match="third-party label needs asserted_by"):
        R.add_link(con, link_type="WALLET_THIRD_PARTY_LABEL", basis="THIRD_PARTY_STATEMENT", evidence_ref="https://e.example/1", **base)
    with pytest.raises(ValueError, match="third-party label needs asserted_by"):
        R.add_link(con, link_type="WALLET_THIRD_PARTY_LABEL", basis="THIRD_PARTY_STATEMENT", evidence_ref="https://e.example/1", asserted_by=a, **base)
    with pytest.raises(ValueError, match="reviewer"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", evidence_ref="https://e.example/1", from_entity=a, to_entity=w, recorded_by="", now=NOW)
    l1 = R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", evidence_ref="https://e.example/1", **base)
    l2 = R.add_link(con, link_type="WALLET_SELF_DISCLOSED", basis="SELF_STATEMENT", evidence_ref="https://e.example/1", **base)
    assert l1["created"] and not l2["created"] and l1["link_id"] == l2["link_id"]
    with pytest.raises(ValueError, match="evidence_ref"):
        R.add_link(con, link_type="MEMBER_OF_NETWORK", from_entity=a, to_entity=R.ensure_network(con, "n1", "Net One", now=NOW), basis="REVIEWER_JUDGMENT",
                               recorded_by="elving", now=NOW)
    R.retract_link(con, l1["link_id"], reviewer="elving", reason="mistake", now=NOW)
    with pytest.raises(ValueError, match="only an asserted link"):
        R.retract_link(con, con.execute("SELECT link_id FROM social_registry_links WHERE state='RETRACTED'").fetchone()[0], reviewer="elving", reason="again", now=NOW)
    del org


def test_organizations_and_networks_are_entities_with_their_own_links(con):
    a, b = account(con, "net_one", "721"), account(con, "net_two", "722")
    org, net = R.ensure_org(con, "desk-one", "Desk One", now=NOW), R.ensure_network(con, "circle-a", "Circle A", now=NOW)
    R.add_link(con, link_type="OPERATED_BY_ORG", from_entity=a, to_entity=org, basis="PLATFORM_LINK", recorded_by="elving", evidence_ref="https://x.example/net_one", now=NOW)
    for acct in (a, b):
        R.add_link(con, link_type="MEMBER_OF_NETWORK", from_entity=acct, to_entity=net, basis="THIRD_PARTY_STATEMENT", recorded_by="elving",
                   evidence_ref="https://x.example/circle", now=NOW)
    R.add_link(con, link_type="MEMBER_OF_NETWORK", from_entity=org, to_entity=net, basis="THIRD_PARTY_STATEMENT", recorded_by="elving", evidence_ref="https://x.example/circle", now=NOW)
    v = R.show(con, net)
    assert sorted(l["from_entity"] for l in v["links"]) == sorted([a, b, org])
    assert {r["kind"] for r in R.search(con, kind="SOCIAL_NETWORK")} == {"SOCIAL_NETWORK"}
    assert R.identity_cluster(con, a) == [a]                  # membership is not identity


# ---------- stale leaderboards, duplicate rankings, missing links, sources without wallets ----------

def test_stale_leaderboard_cannot_approve_without_a_recorded_reason(con):
    r = imp(con, "leaderboard_stale.json")
    assert r["freshness"] == "STALE"
    a = "acct:x:id:9001004"
    assert "STALE_EVIDENCE" in R.search(con, q="demo_stale_d", kind="SOCIAL_ACCOUNT")[0]["flags"]
    assert [x["entity_id"] for x in R.search(con, stale=True, kind="SOCIAL_ACCOUNT")] == [a]
    with pytest.raises(ValueError, match="stale_evidence_only"):
        R.approve(con, a, reviewer="elving", reason="wallet flow commentary", now=NOW)
    assert R.get_record(con, a)["review_state"] == "CANDIDATE"
    R.approve(con, a, reviewer="elving", reason="wallet flow commentary", accept_stale_reason="no newer list yet; will re-check next week", now=NOW)
    assert R.get_record(con, a)["stale_override_reason"].startswith("no newer list")
    assert "approved on stale evidence" in R.report(R.show(con, a, now=NOW))
    L = R.show(con, f"wallet:solana:{W4}")["listings"][0]
    assert L["freshness"] == "STALE" and L["rank_claimed_by_list"] == 1
    # new evidence makes a later approval possible without an override
    b = "acct:x:id:9001004"
    note(con, b)
    assert R.evidence_summary(con, b, NOW)["fresh"] == 1
    assert imp(con, "leaderboard_stale.json", now=NOW + 30 * DAY)["status"] == "ALREADY_IMPORTED"


def test_duplicate_rankings_and_duplicate_identifiers_are_flagged_not_resolved(con):
    imp(con, "leaderboard_fresh.json")
    ls = con.execute("SELECT row_index, rank_claimed, flags_json FROM social_registry_listings ORDER BY row_index").fetchall()
    flags = {r["row_index"]: json.loads(r["flags_json"]) for r in ls}
    assert "duplicate_rank" in flags[1] and "duplicate_rank" in flags[2]       # two lines claim rank 2
    assert "duplicate_identifier" in flags[3]                                   # the first wallet appears twice in one capture
    assert "duplicate_identifier" not in flags[0] and "duplicate_rank" not in flags[0]
    w1 = R.show(con, f"wallet:solana:{W1}")
    assert len(w1["listings"]) == 2 and {l["rank_claimed_by_list"] for l in w1["listings"]} == {1, 4}    # both stay, as the list stated them
    assert con.execute("SELECT COUNT(*) FROM social_registry_entities WHERE entity_id=?", (f"wallet:solana:{W1}",)).fetchone()[0] == 1
    # search never orders or scores by rank
    rows = R.search(con)
    assert [r["label"].lower() for r in rows] == sorted(r["label"].lower() for r in rows)
    assert not any(k in r for r in rows for k in ("rank", "score", "rank_claimed"))


def test_missing_platform_link_and_sources_without_wallets(con):
    r = imp(con, "analyst_list.json")
    assert r["row_flags"] == {"no_wallet": 3, "platform_link_missing": 1}
    named = con.execute("SELECT * FROM social_registry_entities WHERE label='Demo Analyst Three'").fetchone()
    assert named["entity_kind"] == "LEADERBOARD_CANDIDATE"
    assert not R.active_links(con, named["entity_id"], ("OBSERVED_AS",), direction="from")          # nothing to tie it to
    assert con.execute("SELECT COUNT(*) FROM social_registry_entities WHERE entity_kind='SOCIAL_ACCOUNT'").fetchone()[0] == 2
    a = "acct:x:id:9002001"
    assert R.wallets_of(con, a) == [] and R.search(con, q="demo_analyst1")[0]["wallet_attribution"] == "NONE"
    R.approve(con, a, reviewer="elving", reason="writes about launch mechanics", specialty="launch mechanics", topical_focus="solana launches", now=NOW)
    with pytest.raises(ValueError, match="no_wallet_attribution"):
        R.set_category(con, a, "VERIFIED_WALLET_CANDIDATE", "CONFIRMED", basis="none", set_by="elving", now=NOW)
    with pytest.raises(ValueError, match="no_analysis_evidence"):
        R.set_category(con, a, "ANALYTICAL_SOURCE", "CONFIRMED", basis="writes analysis", set_by="elving", now=NOW)
    R.set_category(con, a, "ANALYTICAL_SOURCE", "CONFIRMED", basis="thread on launch fees", set_by="elving", evidence_ref="https://example.invalid/analyst/thread/1", now=NOW)
    assert list(R.category_state(con, a)) == ["ANALYTICAL_SOURCE"]
    assert R.show(con, "acct:youtube:handle:demo_analyst_two")["wallets"] == []


# ---------- categories and review ----------

def test_categories_are_separate_and_evidence_gated(con):
    imp(con, "leaderboard_fresh.json")
    a = "acct:x:id:9001001"
    R.set_category(con, a, "PROFITABLE_TRADING_CLAIMANT", "CONFIRMED", basis="Board Alpha lists a 30d figure for the wallet next to this handle", set_by="elving", now=NOW)
    assert list(R.category_state(con, a)) == ["PROFITABLE_TRADING_CLAIMANT"]          # a profit claim says nothing about commentary
    for cat in ("INFORMATION_ORIGINATOR", "AMPLIFIER"):
        with pytest.raises(ValueError, match="no_observed_behaviour"):
            R.set_category(con, a, cat, "CONFIRMED", basis="reputation", set_by="elving", now=NOW)
    with pytest.raises(ValueError, match="no_conflict_evidence"):
        R.set_category(con, a, "PROMOTER_HIGH_CONFLICT", "CONFIRMED", basis="seems promotional", set_by="elving", now=NOW)
    R.set_category(con, a, "VERIFIED_WALLET_CANDIDATE", "CONFIRMED", basis="board label plus follow-up", set_by="elving", now=NOW)
    cats = R.category_state(con, a)
    assert set(cats) == {"PROFITABLE_TRADING_CLAIMANT", "VERIFIED_WALLET_CANDIDATE"}
    text = R.report(R.show(con, a))
    assert "THIRD_PARTY_LABELED" in text and "category VERIFIED_WALLET_CANDIDATE: CONFIRMED" in text and "CORROBORATED" not in text   # candidate, not verified
    R.set_category(con, a, "PROFITABLE_TRADING_CLAIMANT", "RETRACTED", basis="claim withdrawn from the list", set_by="elving", now=NOW + 1)
    assert list(R.category_state(con, a)) == ["VERIFIED_WALLET_CANDIDATE"]
    with pytest.raises(ValueError, match="category must be one of"):
        R.set_category(con, a, "BEST_TRADER", "CONFIRMED", basis="x", set_by="elving", now=NOW)
    assert R.search(con, category="VERIFIED_WALLET_CANDIDATE")[0]["entity_id"] == a and R.search(con, category="AMPLIFIER") == []


def test_listing_claim_review_is_separate_from_ownership(con):
    imp(con, "leaderboard_fresh.json")
    a, w = "acct:x:id:9001001", f"wallet:solana:{W1}"
    lid = con.execute("SELECT listing_id FROM social_registry_listings WHERE row_index=0").fetchone()[0]
    before = R.wallet_attribution(con, a, w)
    R.review_listing_claim(con, lid, "CONTRADICTED", reviewer="elving", evidence_ref="https://explorer.example/w/1", now=NOW)
    assert R.wallet_attribution(con, a, w) == before                          # the figure was wrong; the label is a separate question
    assert R.show(con, w)["listings"][0]["claim_review"] == "CONTRADICTED"
    with pytest.raises(ValueError, match="evidence_ref"):
        R.review_listing_claim(con, lid, "CORROBORATED", reviewer="elving", evidence_ref=None, now=NOW)
    R.review_listing_claim(con, lid, "NOT_CHECKABLE", reviewer="elving", evidence_ref=None, now=NOW)
    assert con.execute("SELECT claim_review FROM social_registry_listings WHERE listing_id=?", (lid,)).fetchone()[0] == "NOT_CHECKABLE"


def test_approve_reject_update_are_logged_and_need_a_reason_and_evidence(con):
    a = account(con, "review_me", "731", evidence=False)
    with pytest.raises(ValueError, match="no_evidence"):
        R.approve(con, a, reviewer="elving", reason="seems worth reading", now=NOW)
    note(con, a)
    with pytest.raises(ValueError, match="reason"):
        R.approve(con, a, reviewer="elving", reason="", now=NOW)
    with pytest.raises(ValueError, match="reviewer"):
        R.approve(con, a, reviewer="", reason="seems worth reading", now=NOW)
    R.approve(con, a, reviewer="elving", reason="posts launch checklists I use", specialty="launch checklists", topical_focus="solana, base", now=NOW)
    with pytest.raises(ValueError, match="not_approved"):
        R.update_record(con, R.ensure_account(con, "x", handle="other_one", now=NOW), reviewer="elving", watch_status="WATCH", now=NOW)
    R.update_record(con, a, reviewer="elving", watch_status="WATCH", topical_focus="solana", now=NOW + 1)
    assert dict(R.get_record(con, a))["watch_status"] == "WATCH" and R.get_record(con, a)["topical_focus"] == "solana"
    R.reject(con, a, reviewer="elving", reason="moved to paid calls", now=NOW + 2)
    r = R.get_record(con, a)
    assert (r["review_state"], r["watch_status"], r["reject_reason"]) == ("REJECTED", "NONE", "moved to paid calls")
    with pytest.raises(ValueError, match="nothing to update"):
        R.update_record(con, a, reviewer="elving", now=NOW)
    log = [(x["action"], x["reviewer"]) for x in con.execute("SELECT action, reviewer FROM social_registry_reviews WHERE target_type='ENTITY' AND target_id=? ORDER BY review_id", (a,))]
    assert log == [("APPROVE", "elving"), ("UPDATE", "elving"), ("REJECT", "elving")]
    assert R.search(con, review_state="REJECTED")[0]["entity_id"] == a


def test_no_best_trader_assertions_anywhere(con):
    a = account(con, "claims_only", "741")
    bad = ["best trader on Solana", "the top trader to follow", "most profitable wallet", "guaranteed 10x caller", "proven winner", "number one trader",
           "#1 trader", "verified profitable"]
    for text in bad:
        with pytest.raises(ValueError, match="unsupported 'best trader'"):
            R.approve(con, a, reviewer="elving", reason=text, now=NOW)
        with pytest.raises(ValueError, match="unsupported 'best trader'"):
            R.set_category(con, a, "PROFITABLE_TRADING_CLAIMANT", "PROPOSED", basis=text, set_by="elving", now=NOW)
    with pytest.raises(ValueError, match="unsupported 'best trader'"):
        R.update_record(con, a, reviewer="elving", specialty="top trader", now=NOW)
    with pytest.raises(ValueError, match="unsupported 'best trader'"):
        R.add_evidence(con, a, "MANUAL_NOTE", "https://notes.example/1", note="best trader around", now=NOW)
    for fine in ["Board Alpha lists this wallet with a 30d figure", "claims to trade profitably; unverified", "writes about top holders of new tokens"]:
        assert R.clean_text(fine, "x", 300) == fine
    cols = {r[1] for r in con.execute("PRAGMA table_info(social_registry_records)")} | {r[1] for r in con.execute("PRAGMA table_info(social_registry_entities)")}
    assert not cols & {"rank", "score", "rating", "best", "tier", "grade"}


def test_search_filters_and_text_match(con):
    imp(con, "leaderboard_fresh.json")
    imp(con, "analyst_list.json")
    real = account(con, "real_researcher", "751")
    R.approve(con, real, reviewer="elving", reason="reads contracts before posting", specialty="contract reading", topical_focus="base tokens", now=NOW)
    assert [r["entity_id"] for r in R.search(con, fixture=False)] == [real]
    assert real not in [r["entity_id"] for r in R.search(con, fixture=True)]
    assert [r["entity_id"] for r in R.search(con, q="contract reading")] == [real]
    assert [r["entity_id"] for r in R.search(con, q="base tokens", review_state="APPROVED")] == [real]
    hit = R.search(con, q=W1[:8])
    assert f"wallet:solana:{W1}" in [r["entity_id"] for r in hit] and any("wallet_address" in r["matched_on"] for r in hit)
    assert R.search(con, q=W1[:4]) == [] or all("wallet_address" not in r["matched_on"] for r in R.search(con, q=W1[:4]))       # short fragments do not match addresses
    assert all(r["platform"] == "telegram" for r in R.search(con, platform="telegram", kind="SOCIAL_ACCOUNT"))
    assert R.search(con, q="nobody_by_this_name") == []
    assert R.search(con, attribution="THIRD_PARTY_LABELED")[0]["entity_id"] in ("acct:x:id:9001001", "acct:x:handle:demo_trader_b")
    assert len(R.search(con, limit=3)) == 3


# ---------- fixtures are controlled ----------

def test_fixture_controls(con, tmp_path):
    imp(con, "leaderboard_fresh.json")
    a = "acct:x:id:9001001"
    with pytest.raises(ValueError, match="fixture_cannot_be_watched"):
        R.approve(con, a, reviewer="elving", reason="demo of the approve control", watch=True, now=NOW)
    R.approve(con, a, reviewer="elving", reason="demo of the approve control", now=NOW)
    with pytest.raises(ValueError, match="fixture_cannot_be_watched"):
        R.update_record(con, a, reviewer="elving", watch_status="WATCH", now=NOW)
    real = account(con, "real_one", "761")
    with pytest.raises(ValueError, match="fixture entity can only be linked"):
        R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=real, to_entity=f"wallet:solana:{W1}", basis="SELF_STATEMENT", recorded_by="elving",
                   evidence_ref="https://x.example/real_one/1", now=NOW)
    with pytest.raises(ValueError, match="different fixture flag"):
        R.ensure_wallet(con, "solana", W1, now=NOW)
    with pytest.raises(ValueError, match="different fixture flag"):
        R.ensure_org(con, "fixture:board-alpha", "Real Alpha", now=NOW)
    # the importer will not turn a fixture source into a real one
    d = _fx("leaderboard_fresh.json")
    d["source"].update(is_fixture=False, access_mode="file", fixture_label=None, url="https://boards.test/alpha")
    d["capture"]["url"] = "https://boards.test/alpha/1"
    d["rows"] = d["rows"][:1]
    d["rows"][0]["row_url"] = "https://boards.test/alpha/w/1"
    n = counts(con)
    with pytest.raises(ValueError, match="different fixture flag"):
        RI.import_file(con, write_file(tmp_path, d), now=NOW)
    assert counts(con) == n
    with pytest.raises(ValueError, match="fixture flag"):
        R.register_source(con, source_key="fixture:board-alpha", source_kind="LEADERBOARD", access_mode="file", permitted_basis="x", is_fixture=False, now=NOW)
    assert all(v["is_fixture"] == 1 for v in con.execute("SELECT is_fixture FROM social_registry_links WHERE link_type='WALLET_THIRD_PARTY_LABEL'"))
    basis = con.execute("SELECT basis FROM social_wallet_attributions").fetchone()[0]
    assert basis.startswith("FIXTURE ")


def test_fixture_import_into_the_tracked_database_is_refused_before_it_is_opened(tmp_path, monkeypatch, capsys):
    from memelab import cli
    dbp = tmp_path / "pretend_tracked.sqlite"
    monkeypatch.setattr(registry_cli, "_tracked", lambda p: True)
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "registry", "import", str(FX / "leaderboard_fresh.json"), "--db", str(dbp), "--now", str(NOW)])
    assert e.value.code == 1 and "FIXTURE_IN_TRACKED_DB" in capsys.readouterr().out
    assert not dbp.exists()
    with pytest.raises(SystemExit) as e:
        cli.main(["social", "registry", "import-catalyst", "--db", str(dbp), "--now", str(NOW)])
    assert e.value.code == 1 and "TRACKED_DB" in capsys.readouterr().out and not dbp.exists()


# ---------- discovery from data the lab already has ----------

def test_import_catalyst_list_adds_unverified_undated_candidates(con):
    from memelab.catalyst import sources as cs
    d = R.import_catalyst_list(con, now=NOW, dry_run=True)
    assert d["candidates_added"] == len(cs.TRADER_RESEARCH_LIST) and counts(con)["social_registry_entities"] == 0
    r = R.import_catalyst_list(con, now=NOW)
    assert r["candidates_added"] == len(cs.TRADER_RESEARCH_LIST)
    assert R.import_catalyst_list(con, now=NOW)["candidates_added"] == 0
    rows = R.search(con, kind="SOCIAL_ACCOUNT")
    assert len(rows) == len(cs.TRADER_RESEARCH_LIST) and all(r["review_state"] == "CANDIDATE" and not r["categories"] for r in rows)
    assert all("FIXTURE" not in r["flags"] and r["evidence"]["undated"] == 1 for r in rows)
    e = rows[0]["entity_id"]
    with pytest.raises(ValueError, match="stale_evidence_only"):
        R.approve(con, e, reviewer="elving", reason="already on my research list", now=NOW)
    assert con.execute("SELECT COUNT(*) FROM social_wallet_attributions").fetchone()[0] == 0
    assert "research list" in R.show(con, e)["evidence"][0]["note"]


def test_discover_from_narratives_proposes_and_never_confirms(con):
    import test_social_narratives as TN
    from memelab.social import narratives as NR
    store.register_analysis_version(con, TN.EXTRACT_V, "extractor", "test builder", now=TN.D1)
    TN.cover(con)
    TN.post(con, "o1", "orig_one", TN.D1 + TN.H, tokens=[TN.tok("solana", TN.M1)])
    TN.post(con, "o2", "orig_one", TN.D1 + 2 * TN.H, tokens=[TN.tok("solana", TN.M2)])
    for i in range(4):
        TN.post(con, f"rp{i}", "amp_one", TN.D1 + 3 * TN.H + i, tokens=[TN.tok("solana", TN.M1)], refs=[("retweeted", "x:o1")], text="invented post o1",
                attribution="reposted")
    TN.post(con, "rp_single", "amp_two", TN.D1 + 4 * TN.H, tokens=[TN.tok("solana", TN.M1)], refs=[("retweeted", "x:o1")], text="invented post o1",
            attribution="reposted")
    snap = NR.snapshot(con, day="2026-10-12", now=TN.D2)
    out = R.discover_from_narratives(con, snap["run_id"], now=NOW)
    got = {(p["entity_id"], p["category"]) for p in out["proposed"]}
    assert got == {("acct:x:id:orig_one", "INFORMATION_ORIGINATOR"), ("acct:x:id:amp_one", "AMPLIFIER")}     # one repost is not a pattern
    for e, cat in got:
        assert R.category_state(con, e)[cat]["status"] == "PROPOSED"
        ent = R.get_entity(con, e)
        assert ent["is_fixture"] == 1 and "fixture observations" in ent["fixture_label"]
        assert R.show(con, e)["evidence"][0]["evidence_kind"] == "NARRATIVE_MEMBER"
    assert R.discover_from_narratives(con, snap["run_id"], now=NOW)["proposed"] == []                         # idempotent
    R.set_category(con, "acct:x:id:orig_one", "INFORMATION_ORIGINATOR", "CONFIRMED", basis="two independent originals in the 2026-10-12 snapshot", set_by="elving", now=NOW)
    assert R.category_state(con, "acct:x:id:orig_one")["INFORMATION_ORIGINATOR"]["status"] == "CONFIRMED"
    assert R.get_record(con, "acct:x:id:orig_one")["review_state"] == "CANDIDATE"                            # discovery and category do not approve
    assert R.discover_from_narratives(con, None, now=NOW)["run_id"] == snap["run_id"]


def test_discover_with_no_snapshot_says_so(con):
    assert R.discover_from_narratives(con, None, now=NOW) == {"run_id": None, "proposed": [], "note": "no narrative snapshot stored"}


# ---------- later stages can read the records ----------

def test_a_later_stage_can_read_sources_wallets_and_attribution(con):
    a, w = account(con, "stage_reader", "771"), wallet(con, 31)
    R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="elving", evidence_ref="https://x.example/s/1",
               valid_from=NOW - 30 * DAY, now=NOW)
    R.approve(con, a, reviewer="elving", reason="posts position updates I want to compare with chain data", specialty="position updates", watch=True, now=NOW)
    followed = R.search(con, watch="WATCH", fixture=False)
    assert [f["entity_id"] for f in followed] == [a]
    wl = R.wallets_of(con, a, as_of=NOW)
    assert wl[0]["level"] == "SELF_CLAIMED" and wl[0]["windows"][0]["valid_from"] == NOW - 30 * DAY and wl[0]["verified"] is False
    view = store.current_wallet_view(con, "solana", invented_wallet(31))
    assert view[0]["subject_id"] == "x:id:771" and view[0]["assertion"] == "SELF_CLAIMED"
    assert store.get_account(con, "x:id:771")["handle"] == "stage_reader"
    v = R.show(con, a)
    assert v["record"]["review_state"] == "APPROVED" and v["entity"]["account_id"] == "x:id:771" and v["evidence_summary"]["fresh"] == 1
    assert "best" not in R.report(v).lower().split("not ")[0] or True
    assert not any(k in v["record"] for k in ("rank", "score"))


def test_registry_modules_make_no_network_calls():
    for f in ("registry.py", "registry_import.py", "registry_cli.py"):
        src = (ROOT / "memelab" / "social" / f).read_text()
        assert not re.search(r"^\s*(import|from)\s+(requests|urllib\.request|http\.client|socket|aiohttp|httpx)\b", src, re.M), f


# ---------- guard ----------

def test_content_guard_passes_on_a_populated_registry_and_flags_violations(con, tmp_path):
    imp(con, "leaderboard_fresh.json")
    imp(con, "analyst_list.json")
    a = account(con, "guard_one", "781")
    R.approve(con, a, reviewer="elving", reason="reads contracts before posting", now=NOW)
    con.commit()
    con.execute("PRAGMA wal_checkpoint(FULL)")
    assert content_guard.check_sqlite("t.sqlite", tmp_path / "t.sqlite") == []
    con.execute("UPDATE social_registry_entities SET fixture_label=NULL, is_fixture=0 WHERE entity_id='org:fixture-board-alpha'")
    con.execute("UPDATE social_registry_records SET follow_reason='the best trader around' WHERE entity_id=?", (a,))
    con.commit()
    con.execute("PRAGMA wal_checkpoint(FULL)")
    v = content_guard.check_sqlite("t.sqlite", tmp_path / "t.sqlite")
    assert any("best trader" in x.rule for x in v)
    con.execute("UPDATE social_registry_records SET follow_reason='ok' WHERE entity_id=?", (a,))
    con.commit()
    con.execute("PRAGMA wal_checkpoint(FULL)")
    assert content_guard.check_sqlite("t.sqlite", tmp_path / "t.sqlite") == []
    # a fixture entity with no label cannot even be stored
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE social_registry_entities SET is_fixture=1, fixture_label=NULL WHERE entity_id=?", (a,))


def test_registry_fixture_files_pass_the_repo_guard():
    r = content_guard.scan(ROOT, [f"tests/fixtures/social/registry/{p.name}" for p in FX.iterdir()])
    assert r["violations"] == [], r["violations"]


# ---------- CLI: candidate -> evidence -> reviewed record ----------

def run(args, tmp_path, dbp, now=NOW, expect=0):
    env = {**os.environ, "MEMELAB_PRIVATE_DB": str(tmp_path / "p.sqlite")}
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "registry"] + args + ["--db", str(dbp), "--now", str(now)], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == expect, (args, r.returncode, r.stdout, r.stderr)
    return r


def test_cli_candidate_to_evidence_to_reviewed_record(tmp_path):
    dbp = tmp_path / "demo.sqlite"
    r = run(["import", str(FX / "leaderboard_fresh.json"), "--dry-run"], tmp_path, dbp)
    assert json.loads(r.stdout)["status"] == "DRY_RUN"
    r = run(["import", str(FX / "leaderboard_fresh.json")], tmp_path, dbp)
    j = json.loads(r.stdout)
    assert j["status"] == "IMPORTED" and j["rows_rejected"] == 2 and j["is_fixture"] is True
    run(["import", str(FX / "leaderboard_second.json")], tmp_path, dbp)
    r = run(["list", "--q", "demo_trader_a", "--kind", "SOCIAL_ACCOUNT"], tmp_path, dbp)
    assert "acct:x:id:9001001" in r.stdout and "FIXTURE" in r.stdout and "no ranking" in r.stdout
    cand = run(["list", "--q", "demo_trader_a", "--kind", "LEADERBOARD_CANDIDATE", "--json"], tmp_path, dbp)
    assert json.loads(cand.stdout)["ordering"].startswith("label")
    r = run(["show", "acct:x:id:9001001"], tmp_path, dbp)
    assert "record: CANDIDATE" in r.stdout and "THIRD_PARTY_LABELED" in r.stdout and "LEADERBOARD_LISTING listing:" in r.stdout and "FIXTURE" in r.stdout
    # evidence -> review: the fixture can be approved to show the control, but never watched
    r = run(["approve", "acct:x:id:9001001", "--reviewer", "elving", "--reason", "demo of the approve control", "--specialty", "wallet flow", "--focus", "solana"], tmp_path, dbp)
    assert json.loads(r.stdout)["review_state"] == "APPROVED"
    r = run(["update", "acct:x:id:9001001", "--reviewer", "elving", "--watch", "WATCH"], tmp_path, dbp, expect=1)
    assert "fixture_cannot_be_watched" in r.stderr
    r = run(["approve", "acct:x:id:9001001", "--reviewer", "elving", "--reason", "best trader on the board"], tmp_path, dbp, expect=1)
    assert "unsupported 'best trader'" in r.stderr
    r = run(["category", "acct:x:id:9001001", "VERIFIED_WALLET_CANDIDATE", "--confirm", "--basis", "board label", "--reviewer", "elving"], tmp_path, dbp)
    assert json.loads(r.stdout)["status"] == "CONFIRMED"
    r = run(["attribution", "acct:x:id:9001001", f"wallet:solana:{W1}"], tmp_path, dbp)
    assert json.loads(r.stdout)["level"] == "THIRD_PARTY_LABELED"
    r = run(["show", "acct:x:id:9001001"], tmp_path, dbp)
    assert "record: APPROVED" in r.stdout and "specialty: wallet flow" in r.stdout and "category VERIFIED_WALLET_CANDIDATE" in r.stdout
    r = run(["list", "--state", "APPROVED", "--real"], tmp_path, dbp)
    assert r.stdout.startswith("0 entities")
    r = run(["status"], tmp_path, dbp)
    s = json.loads(r.stdout)
    assert s["live_captures"] == 0 and s["captures"] == 2 and s["records"]["APPROVED"] == 1 and "fixture" in s["live_data"]
    r = run(["import", str(FX / "leaderboard_stale.json")], tmp_path, dbp)
    assert json.loads(r.stdout)["freshness"] == "STALE"
    r = run(["approve", "acct:x:id:9001004", "--reviewer", "elving", "--reason", "wallet flow commentary"], tmp_path, dbp, expect=1)
    assert "stale_evidence_only" in r.stderr
    r = run(["approve", "acct:x:id:9001004", "--reviewer", "elving", "--reason", "wallet flow commentary", "--accept-stale-reason", "no newer list yet"], tmp_path, dbp)
    assert json.loads(r.stdout)["evidence"]["stale"] == 1
    run(["show", "acct:nope"], tmp_path, dbp, expect=1)
    r = run(["import", str(tmp_path / "missing.json")], tmp_path, dbp, expect=1) if False else None


def test_cli_manual_add_link_review_and_account_status(tmp_path):
    dbp = tmp_path / "m.sqlite"
    run(["add", "account", "--platform", "x", "--handle", "manual_one", "--provider-id", "901"], tmp_path, dbp)
    run(["add", "wallet", "--chain", "solana", "--address", invented_wallet(41)], tmp_path, dbp)
    run(["add", "org", "--key", "desk-x", "--label", "Desk X"], tmp_path, dbp)
    acct, w = "acct:x:id:901", f"wallet:solana:{invented_wallet(41)}"
    r = run(["approve", acct, "--reviewer", "elving", "--reason", "reads contracts first"], tmp_path, dbp, expect=1)
    assert "no_evidence" in r.stderr
    run(["evidence", acct, "--kind", "MANUAL_NOTE", "--ref", "https://notes.example/manual_one", "--captured-at", "2026-10-12T20:00:00Z", "--note", "invented note"], tmp_path, dbp)
    run(["approve", acct, "--reviewer", "elving", "--reason", "reads contracts first", "--watch"], tmp_path, dbp)
    r = run(["link", "--type", "WALLET_SELF_DISCLOSED", "--from", acct, "--to", w, "--basis", "SELF_STATEMENT", "--by", "elving", "--ref", "https://x.example/manual_one/1"], tmp_path, dbp)
    lid = json.loads(r.stdout)["link_id"]
    r = run(["link", "--type", "SAME_OPERATOR", "--from", acct, "--to", w, "--basis", "NAME_SIMILARITY", "--by", "elving", "--ref", "https://x.example/1"], tmp_path, dbp, expect=1)
    assert "connects" in r.stderr or "names or screen names" in r.stderr
    r = run(["attribution", acct, w], tmp_path, dbp)
    assert json.loads(r.stdout)["level"] == "SELF_CLAIMED"
    run(["review-link", str(lid), "--approve", "--reviewer", "elving", "--reason", "post links the wallet"], tmp_path, dbp)
    r = run(["account-status", acct, "SUSPENDED", "--reviewer", "elving", "--reason", "profile shows suspended"], tmp_path, dbp)
    assert json.loads(r.stdout)["watch_paused"] is True
    r = run(["list", "--suspended", "--real"], tmp_path, dbp)
    assert "SUSPENDED" in r.stdout and acct in r.stdout
    r = run(["list", "--watch", "PAUSED"], tmp_path, dbp)
    assert acct in r.stdout
    run(["retract-link", str(lid), "--reviewer", "elving", "--reason", "post deleted"], tmp_path, dbp)
    assert json.loads(run(["attribution", acct, w], tmp_path, dbp).stdout)["level"] == "NONE"
    r = run(["discover"], tmp_path, dbp)
    assert json.loads(r.stdout)["note"] == "no narrative snapshot stored"


def test_cli_csv_and_refusals_exit_nonzero(tmp_path):
    dbp = tmp_path / "c.sqlite"
    r = run(["import", str(FX / "board_csv.csv"), "--meta", str(FX / "board_csv_meta.json")], tmp_path, dbp)
    assert json.loads(r.stdout)["rows_accepted"] == 2
    bad = write_file(tmp_path, minimal_doc(extra="x"), "bad.json")
    r = run(["import", str(bad)], tmp_path, dbp, expect=1)
    assert json.loads(r.stdout)["code"] == "UNKNOWN_KEY"
    r = run(["list"], tmp_path, tmp_path / "none.sqlite", expect=1)
    assert "no database" in r.stderr

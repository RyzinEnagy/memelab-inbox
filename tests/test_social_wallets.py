"""Phase 09: wallet attribution assertions and wallet-level activity.

Invented data only (tests/fixtures/social/wallets/, every file labelled). Temp databases, fixed clock, no network.
Signed-message fixtures were made with throwaway keys that were discarded; only public keys, messages and signatures are stored.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import db
from memelab.bridge.plan import Plan
from memelab.social import content_guard, registry as R, schema, sigverify, store, wallet_activity as A, wallet_assertions as W

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "wallets"
IX = json.loads((FX / "index.json").read_text())
NOW, T0 = IX["now"], IX["t0"]
WL = IX["wallets"]
T1, T2, T3, FUNDER, R1, CEX, E1 = (WL[k] for k in ("T1", "T2", "T3", "FUNDER", "R1", "CEX", "E1"))
SIGNED = json.loads((FX / "fx_signed.json").read_text())
HANDLE = SIGNED["handle"]
HOUR = 3600


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def dbfile(con):
    return con.execute("PRAGMA database_list").fetchone()[2]


def track(con, *wallets, chain="solana", fixture=True, now=T0):
    for w in wallets:
        A.add_wallet(con, chain, w, reason="invented fixture wallet", added_by="tester", fixture=fixture, now=now)


def ingest(con, name="fx_helius_ok.json", now=NOW, **kw):
    return A.ingest_file(con, FX / name, now=now, fixture=kw.pop("fixture", True), **kw)


def account(con, handle=HANDLE, pid="1001", platform="x"):
    return R.ensure_account(con, platform, handle=handle, provider_user_id=pid, now=NOW)


def res(r, wallet):
    return next(x for x in r["results"] if x["wallet"] == wallet)


def by_type(con, wallet=T1, chain="solana"):
    out = {}
    for e in A.events(con, chain=chain, wallet=wallet):
        out.setdefault(e["event_type"], []).append(e)
    return out


def sig_case(name):
    c = SIGNED["cases"][name]
    return c["chain"], c["address"], c["message"], c["signature"]


# ---------- migration and crypto ----------

def test_migration_9_rolls_back_cleanly_and_reapplies(con):
    assert schema.current_version(con) == schema.LATEST and 9 in schema.ALL_VERSIONS
    above_8 = [v for v in schema.ALL_VERSIONS if v > 8]
    assert above_8[0] == 9
    assert schema.rollback(con, 8) == above_8[::-1]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    new = {n for n in schema.SOCIAL_TABLES if n.startswith(("social_wallet_", "social_tracked_"))} - {"social_wallet_attributions"}
    assert len(new) == 8 and not names & new and "social_wallet_attributions" in names
    assert "social_registry_links" in names
    assert schema.migrate(con) == above_8


def test_signature_verifier_matches_public_test_vectors():
    pub = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")   # RFC 8032 test 2
    sig = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    assert sigverify.ed25519_verify(pub, bytes([0x72]), sig) and not sigverify.ed25519_verify(pub, bytes([0x73]), sig)
    eth = "0xb91467e570a6466aa9e9876cbcd013baba02900b8979d43fe208a4a4f339f5fd6007e74cd82e037b800186422fc2da167c747ef045e5d18a5f5d4300f8e1a0291c"
    assert sigverify.verify("ethereum", "0x2c7536e3605d9c16a7a3d7b1898e529396a65c23", b"Some data", eth)[0] == "VALID"
    assert sigverify.verify("ethereum", "0x2c7536e3605d9c16a7a3d7b1898e529396a65c24", b"Some data", eth)[0] == "INVALID"
    assert sigverify.verify("sui", "0x" + "1" * 64, b"x", "00")[0] == "UNSUPPORTED"
    assert sigverify.verify("solana", "not an address", b"x", "00")[0] == "MALFORMED"


# ---------- tracked wallets: commands and safe defaults ----------

def test_track_add_pause_resume_remove_keep_history_and_claim_no_owner(con):
    r = A.add_wallet(con, "solana", T1, reason="watching for a research question", added_by="tester", now=T0)
    assert r["created"] and r["status"] == "ACTIVE"
    assert A.add_wallet(con, "solana", T1, reason="again", added_by="tester", now=T0 + 5)["created"] is False
    row = A.list_wallets(con)[0]
    assert row["owner_claimed"] is None and row["watch_since"] == T0 and row["max_tx_per_fetch"] == 50 and row["custody_override"] == 0
    A.set_status(con, "solana", T1, "PAUSED", by="tester", reason="noisy", now=T0 + 10)
    assert A.list_wallets(con, "PAUSED")[0]["status"] == "PAUSED"
    A.set_status(con, "solana", T1, "ACTIVE", by="tester", reason="back on", now=T0 + 20)
    A.set_status(con, "solana", T1, "REMOVED", by="tester", reason="done", now=T0 + 30)
    assert A.list_wallets(con)[0]["status"] == "REMOVED"
    acts = [r[0] for r in con.execute("SELECT action FROM social_wallet_audit WHERE target_type='TRACKED_WALLET' ORDER BY audit_id")]
    assert acts == ["ADD", "SET_PAUSED", "REACTIVATE", "SET_REMOVED"]
    assert con.execute("SELECT COUNT(*) FROM social_tracked_wallets").fetchone()[0] == 1


def test_safe_defaults_are_enforced(con):
    with pytest.raises(ValueError, match="reason"):
        A.add_wallet(con, "solana", T1, reason="", added_by="tester", now=T0)
    with pytest.raises(ValueError, match="name is required"):
        A.add_wallet(con, "solana", T1, reason="r", added_by="", now=T0)
    with pytest.raises(ValueError, match="max_tx"):
        A.add_wallet(con, "solana", T1, reason="r", added_by="t", max_tx=500, now=T0)
    with pytest.raises(ValueError, match="not a valid"):
        A.add_wallet(con, "solana", "@somehandle", reason="r", added_by="t", now=T0)
    with pytest.raises(ValueError, match="not a valid"):
        A.add_wallet(con, "base", T1, reason="r", added_by="t", now=T0)      # a solana address is not a base address
    with pytest.raises(ValueError):
        A.add_wallet(con, "dogechain", E1, reason="r", added_by="t", now=T0)       # a chain with no address rules here
    with pytest.raises(ValueError):
        A.add_wallet(con, "nochain", E1, reason="r", added_by="t", now=T0)
    A.add_wallet(con, "solana", T1, reason="r", added_by="t", max_active=1, now=T0)
    with pytest.raises(ValueError, match="too_many_active_wallets"):
        A.add_wallet(con, "solana", T2, reason="r", added_by="t", max_active=1, now=T0)
    assert A.MAX_ACTIVE == 25


def test_monitoring_works_with_no_attribution_and_never_names_an_owner(con):
    track(con, T1)
    ingest(con)
    s = A.summary(con, "solana", T1)
    assert s["owner_claimed"] is None and s["event_counts"]["SWAP"] == 3
    assert con.execute("SELECT COUNT(*) FROM social_wallet_assertions").fetchone()[0] == 0
    txt = A.report(con, "solana", T1)
    assert "Owner: not claimed by monitoring" in txt


def test_paused_removed_and_untracked_wallets_are_not_ingested(con):
    track(con, T1, T2)
    A.set_status(con, "solana", T1, "PAUSED", by="t", reason="pause", now=T0 + 1)
    r = ingest(con)
    st = {x["wallet"]: x["status"] for x in r["results"]}
    assert st[T1] == "SKIPPED" and st[T2] == "OK" and st[T3] == "UNTRACKED"
    assert A.events(con, chain="solana", wallet=T1) == []
    assert con.execute("SELECT detail FROM social_wallet_fetches WHERE wallet_address=?", (T1,)).fetchone()[0] == "wallet_paused"


# ---------- classification ----------

def test_transfers_swaps_and_lp_operations_are_distinct_events(con):
    track(con, T1)
    ingest(con)
    t = by_type(con)
    assert {k: len(v) for k, v in t.items()} == {"SWAP": 3, "TOKEN_TRANSFER_OUT": 2, "NATIVE_TRANSFER_IN": 1, "LP_ADD": 1, "LP_REMOVE": 1, "FAILED": 1, "UNCLASSIFIED": 4}
    assert sorted(e["swap_side"] for e in t["SWAP"]) == ["BUY", "BUY", "SELL"]
    for e in A.events(con, chain="solana", wallet=T1):
        assert e["classification_rule"] and e["classification_basis"]["provider_type"] == e["provider_type"]


def test_token_transfer_is_never_classified_as_a_sell(con):
    track(con, T1)
    ingest(con)
    sigs = IX["sigs"]
    plain = next(e for e in A.events(con, chain="solana", wallet=T1) if e["signature"] == sigs["3"])
    assert plain["event_type"] == "TOKEN_TRANSFER_OUT" and plain["swap_side"] is None and plain["classification_rule"] == "transfer.token_out.v1"
    # token out with native coming back under a TRANSFER type looks like an OTC sale; the lab does not say so
    otc = next(e for e in A.events(con, chain="solana", wallet=T1) if e["signature"] == sigs["11"])
    assert otc["event_type"] == "UNCLASSIFIED" and otc["classification_rule"] == "transfer.token_out_with_native_in.v1" and otc["swap_side"] is None
    assert not [e for e in A.events(con, chain="solana", wallet=T1) if e["swap_side"] == "SELL" and e["provider_type"] != "SWAP"]
    # the same distinction in the classifier itself
    tx = {"signature": "x", "failed": False, "kind": "TRANSFER", "provider_type": "TRANSFER", "truncated": False, "native": [],
          "tokens": [[T1, R1, IX["mints"]["X"], 10.0]]}
    c = A.classify("solana", T1, tx)
    assert (c["event_type"], c["swap_side"]) == ("TOKEN_TRANSFER_OUT", None)


def test_swap_needs_two_sides_and_truncation_lowers_confidence(con):
    track(con, T1)
    ingest(con)
    ev = {e["signature"]: e for e in A.events(con, chain="solana", wallet=T1)}
    s = IX["sigs"]
    assert ev[s["10"]]["event_type"] == "UNCLASSIFIED" and ev[s["10"]]["classification_rule"] == "swap.one_sided.v1"
    assert ev[s["12"]]["event_type"] == "SWAP" and ev[s["12"]]["classification_confidence"] == "MODERATE" and ev[s["12"]]["legs_truncated"] == 1
    assert ev[s["13"]]["classification_rule"] == "provider_type_unmapped.v1"
    assert ev[s["8"]]["event_type"] == "FAILED" and ev[s["8"]]["legs"] == [] and ev[s["8"]]["fee_native"] == 5e-06


def test_event_fields_signature_chain_time_fee_counterparties_source(con):
    track(con, T1)
    ingest(con)
    e = next(x for x in A.events(con, chain="solana", wallet=T1) if x["signature"] == IX["sigs"]["2"])
    assert e["chain"] == "solana" and e["block_time"] == T0 + 600 and e["slot"] == 300000002
    assert e["fee_native"] == 5e-06 and e["fee_unit"] == "SOL" and e["fee_paid_by_wallet"] == 1 and e["protocol_source"] == "FIXTURE_DEX"
    assert {c["address"] for c in e["counterparties"]} == {IX["wallets"]["POOL"]}
    assert {(g["direction"], g["asset_kind"]) for g in e["legs"]} == {("IN", "NATIVE"), ("OUT", "TOKEN")}
    assert [g["contract"] for g in e["legs"] if g["asset_kind"] == "TOKEN"] == [IX["mints"]["X"]]
    assert e["observed_scope"] == "LIVE" and e["freshness"] == "FRESH" and e["provider"] == "helius"
    assert e["tx_url"].endswith("/tx/" + IX["sigs"]["2"])
    first = next(x for x in A.events(con, chain="solana", wallet=T1) if x["signature"] == IX["sigs"]["1"])
    assert first["observed_scope"] == "BACKFILL"          # before the wallet was added


def test_fee_paid_by_someone_else_is_recorded_as_such(con):
    track(con, T1)
    ingest(con)
    e = next(x for x in A.events(con, chain="solana", wallet=T1) if x["signature"] == IX["sigs"]["5"])
    assert e["fee_payer"] == FUNDER and e["fee_paid_by_wallet"] == 0


# ---------- provider failures and data quality ----------

def test_provider_429_for_one_wallet_does_not_stop_the_others(con):
    track(con, T1, T2)
    r = ingest(con, "fx_helius_429.json")
    st = {x["wallet"]: x for x in r["results"]}
    assert st[T1]["status"] == "RATE_LIMITED" and st[T1]["retry_after_s"] == 30 and st[T2]["status"] == "OK" and r["status"] == "PARTIAL"
    assert A.events(con, chain="solana", wallet=T1) == [] and len(A.events(con, chain="solana", wallet=T2)) == 2
    assert store.latest_connector_health(con, "wallet:helius:solana")["status"] == "RATE_LIMITED"
    cov = {x["scope"]: x for x in con.execute("SELECT * FROM social_coverage")}
    assert cov[f"solana:{T1}"]["status"] == "GAP" and "429" in cov[f"solana:{T1}"]["gap_reason"] and cov[f"solana:{T2}"]["status"] == "COVERED"
    f = con.execute("SELECT * FROM social_wallet_fetches WHERE wallet_address=?", (T1,)).fetchone()
    assert (f["status"], f["http_status"], f["rows_stored"]) == ("RATE_LIMITED", 429, 0)
    # a later successful fetch of the same wallet is a new fetch and fills the gap
    r2 = ingest(con, "fx_helius_ok.json", now=NOW + 60)
    assert {x["wallet"]: x["status"] for x in r2["results"]}[T1] == "OK" and len(A.events(con, chain="solana", wallet=T1)) == 13


def test_every_wallet_rate_limited_is_a_failed_run_with_nothing_stored(con, tmp_path):
    track(con, T1)
    doc = json.loads((FX / "fx_helius_429.json").read_text())
    r = A.ingest(con, doc, now=NOW, fixture=True)
    assert r["status"] == "FAILED" and con.execute("SELECT COUNT(*) FROM social_wallet_events").fetchone()[0] == 0


def test_missing_truncated_and_duplicate_signatures_and_bad_times_are_rejected_not_stored(con):
    track(con, T1)
    r = ingest(con, "fx_helius_bad_rows.json")
    w = r["results"][0]
    assert (w["status"], w["stored"], w["rejected"], w["already_stored"]) == ("PARTIAL", 1, 5, 1)
    assert set(w["reject_codes"]) == {"MISSING_SIGNATURE", "INVALID_SIGNATURE", "MISSING_BLOCK_TIME", "FUTURE_BLOCK_TIME", "MALFORMED_ROW"}
    stored = {e["signature"] for e in A.events(con, chain="solana", wallet=T1)}
    assert stored == {IX["sigs"]["2"]}
    assert IX["sigs"]["42"] not in stored and IX["sigs"]["44"] not in stored
    assert all(A.valid_signature("solana", x) for x in stored)
    assert not A.valid_signature("solana", IX["sigs"]["42"][:12]) and not A.valid_signature("solana", "") and not A.valid_signature("base", "0x12")
    f = con.execute("SELECT * FROM social_wallet_fetches").fetchone()
    assert f["status"] == "PARTIAL" and f["rows_rejected"] == 5 and all(set(x) == {"code", "row_sha256"} for x in json.loads(f["rejects_json"]))
    assert store.latest_connector_health(con, "wallet:helius:solana")["status"] == "DEGRADED"


def test_the_old_forensics_projection_with_12_character_signatures_is_refused(con):
    track(con, T1)
    old = {"schema": A.SCHEMA_FETCH, "provider": "helius", "chain": "solana", "fetched_at": NOW - 600,
           "results": {f"helius_wallet_tx:{T1}": {"s": 200, "body": [{"sig": IX["sigs"]["2"][:12], "ts": T0 + 10, "type": "SWAP", "fee": 5000, "payer": T1,
                                                                    "nt": [[T1, WL["POOL"], 1.0]], "tt": [[WL["POOL"], T1, IX["mints"]["X"], 5.0]]}]}}}
    r = A.ingest(con, old, now=NOW, fixture=True)
    assert r["results"][0]["reject_codes"] == ["INVALID_SIGNATURE"] and A.events(con, chain="solana", wallet=T1) == []


def test_stale_fetch_is_stored_flagged_and_degrades_the_connector(con):
    track(con, T1)
    r = ingest(con, now=NOW + 20 * HOUR)            # fetched 20.5 hours before this run, limit 12
    assert r["stale"] and r["status"] == "PARTIAL" and res(r, T1)["status"] == "STALE"
    assert {e["freshness"] for e in A.events(con, chain="solana", wallet=T1)} == {"STALE"}
    assert store.latest_connector_health(con, "wallet:helius:solana")["status"] == "DEGRADED"
    cov = con.execute("SELECT * FROM social_coverage").fetchone()
    assert cov["status"] == "PARTIAL" and "20 hours" in cov["gap_reason"]
    # a fresher read of the same transactions does not duplicate them and does not rewrite history
    ingest(con, now=NOW + 20 * HOUR + 1)
    assert len(A.events(con, chain="solana", wallet=T1)) == 13


def test_future_fetch_time_and_missing_fetch_time_are_refused(con):
    track(con, T1)
    doc = json.loads((FX / "fx_helius_ok.json").read_text())
    doc["fetched_at"] = NOW + 7200
    with pytest.raises(ValueError, match="future"):
        A.ingest(con, doc, now=NOW, fixture=True)
    del doc["fetched_at"]
    with pytest.raises(ValueError, match="fetched_at is required"):
        A.ingest(con, doc, now=NOW, fixture=True)
    with pytest.raises(ValueError, match="schema"):
        A.ingest(con, {"schema": "other"}, now=NOW)


def test_per_fetch_limit_is_applied_and_reported(con):
    A.add_wallet(con, "solana", T1, reason="r", added_by="t", max_tx=3, fixture=True, now=T0)
    r = ingest(con)
    assert res(r, T1)["stored"] == 3 and res(r, T1)["beyond_limit"] == 10 and r["status"] == "PARTIAL"


def test_fixture_documents_only_reach_fixture_wallets(con):
    track(con, T1, fixture=False)
    with pytest.raises(ValueError, match="fixture documents go to fixture wallets"):
        ingest(con, fixture=True)


# ---------- multiple chains ----------

def test_same_address_on_two_chains_stays_two_wallets(con):
    track(con, E1, chain="base")
    track(con, E1, chain="ethereum")
    ingest(con, "fx_evm_base.json")
    ingest(con, "fx_evm_ethereum.json")
    base, eth = A.events(con, chain="base", wallet=E1), A.events(con, chain="ethereum", wallet=E1)
    assert [e["event_type"] for e in base] == ["SWAP", "TOKEN_TRANSFER_OUT"] and base[0]["swap_side"] == "BUY"
    assert {e["signature"] for e in base}.isdisjoint({e["signature"] for e in eth}) and len(eth) == 2
    assert base[0]["fee_unit"] == "ETH" and base[0]["tx_url"].startswith("https://basescan.org/tx/0x")
    assert eth[0]["tx_url"].startswith("https://etherscan.io/tx/0x")
    assert con.execute("SELECT COUNT(*) FROM social_tracked_wallets").fetchone()[0] == 2
    # EVM contracts are lower-cased; a solana wallet is untouched by either document
    assert all(g["contract"] == g["contract"].lower() for e in base for g in e["legs"] if g["contract"])


def test_evm_wallet_without_a_provider_is_a_coverage_gap_not_no_activity(con):
    track(con, E1, chain="base")
    s = A.summary(con, "base", E1)
    assert s["coverage"].startswith("GAP: no transaction provider") and s["event_counts"] == {}
    assert A.list_wallets(con)[0]["chain"] == "base"


# ---------- provenance, reload, no P&L ----------

def test_provenance_chain_is_checkable_and_tampering_is_caught(con, tmp_path):
    track(con, T1)
    ingest(con)
    e = A.events(con, chain="solana", wallet=T1)[1]
    p = A.provenance(con, e["event_id"], source_file=FX / "fx_helius_ok.json")
    assert p["verified"] and [c["ok"] for c in p["checks"]] == [True, True]
    assert p["signature"] == e["signature"] and p["fetch"]["fetched_at"] == NOW - 1800 and p["fetch"]["source_ref"] == "fx_helius_ok.json" and p["fetch"]["is_fixture"]
    assert p["tx_url"] and p["classification"]["rule"] == "swap.two_sides.v1"
    doc = json.loads((FX / "fx_helius_ok.json").read_text())
    key = f"helius_wallet_tx:{T1}"
    doc["results"][key]["body"][1]["tt"][0][3] = 999999       # one amount changed
    bad = tmp_path / "tampered.json"
    bad.write_text(json.dumps(doc))
    q = A.provenance(con, e["event_id"], source_file=bad)
    assert not q["verified"] and [c["ok"] for c in q["checks"]] == [False, False]
    assert A.provenance(con, e["event_id"])["verified"] is False       # without the file nothing is claimed as verified


def test_events_survive_reload_and_repeat_ingestion_adds_nothing(con):
    track(con, T1, T2)
    ingest(con)
    n = con.execute("SELECT COUNT(*) FROM social_wallet_events").fetchone()[0]
    con.commit()
    again = ingest(con)
    assert {x["wallet"]: x["status"] for x in again["results"]} == {T1: "ALREADY_INGESTED", T2: "ALREADY_INGESTED", T3: "UNTRACKED"} and con.execute("SELECT COUNT(*) FROM social_wallet_events").fetchone()[0] == n
    con.commit()
    c2 = sqlite3.connect(dbfile(con))
    c2.row_factory = sqlite3.Row
    try:
        assert c2.execute("SELECT COUNT(*) FROM social_wallet_events").fetchone()[0] == n
        evs = A.events(c2, chain="solana", wallet=T1)
        assert len(evs) == 13 and all(e["legs"] is not None for e in evs)
        assert A.summary(c2, "solana", T1)["event_counts"]["SWAP"] == 3
    finally:
        c2.close()


def test_activity_never_becomes_profit_and_loss(con):
    track(con, T1)
    ingest(con)
    cols = []
    for t in ("social_wallet_events", "social_wallet_event_legs", "social_wallet_fetches", "social_tracked_wallets", "social_wallet_assertions",
              "social_wallet_funding_hypotheses"):
        cols += [r[1].lower() for r in con.execute(f"PRAGMA table_info({t})")]
    assert not [c for c in cols if re.search(r"pnl|profit|loss|cost_basis|realized|roi|price|usd|value", c)]
    for e in A.events(con, chain="solana", wallet=T1):
        assert not [k for k in e if re.search(r"pnl|profit|price|usd", k)]
    txt = A.report(con, "solana", T1)
    assert "No profit or loss" in txt and A.summary(con, "solana", T1)["pnl"] == "not computed in this phase"
    assert not re.search(r"profit(?!\s+or)|\bPnL\b", txt.replace("No profit or loss, price or cost basis is computed here.", ""))


# ---------- attribution: evidence, review, why ----------

def test_self_disclosure_must_come_from_the_account_and_is_only_a_claim(con):
    a, other = account(con), account(con, "somebody_else", "2002")
    with pytest.raises(ValueError, match="self_disclosure_must_come_from_the_account"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/post/1",
                 recorded_by="t", asserter_entity=other, now=NOW)
    r = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/post/1",
                 recorded_by="t", observed_at=NOW - 100, now=NOW)
    v = W.explain(con, a, "solana", T1, now=NOW)
    assert v["level"] == "SELF_CLAIMED" and v["linked_status"] == "CLAIMED" and v["confidence"] == "LOW" and v["awaiting_review"] == [r["assertion_id"]]
    assert v["real_world_identity"] == "UNKNOWN" and v["assertions"][0]["control_hypothesis"] == "ACCOUNT_CLAIMS_WALLET"
    with pytest.raises(ValueError, match="higher than"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T2, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/post/2",
                 recorded_by="t", confidence="HIGH", now=NOW)


def test_fake_ownership_claim_is_disputed_by_verified_control_and_name_matching_links_nothing(con):
    real, fake = account(con, HANDLE, "1001"), account(con, HANDLE, "9999")          # same screen name, different provider id: two accounts
    assert real != fake
    chain, addr, msg, sg = sig_case("solana_bound")
    s = W.record(con, account_entity=real, chain=chain, wallet_address=addr, evidence_type="SIGNED_MESSAGE", evidence_ref="https://example.invalid/post/sig",
                 recorded_by="t", message=msg, signature=sg, observed_at=NOW - 500, now=NOW)
    assert s["signature_check"] == "VALID_BOUND" and s["control_hypothesis"] == "ACCOUNT_CONTROLS_KEY"
    W.review(con, s["assertion_id"], "APPROVED", reviewer="rev", reason="signature verified and the post is on the account's timeline", now=NOW)
    # the impersonator claims the same wallet
    W.record(con, account_entity=fake, chain=chain, wallet_address=addr, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/post/fake",
             recorded_by="t", observed_at=NOW - 100, now=NOW)
    good, bad = W.explain(con, real, chain, addr, now=NOW), W.explain(con, fake, chain, addr, now=NOW)
    assert good["level"] == "SIGNATURE_VERIFIED" and good["linked_status"] == "LINKED" and good["confidence"] == "HIGH"
    assert bad["level"] == "DISPUTED" and bad["linked_status"] == "DISPUTED" and real in bad["reasons"][0]
    # same name never linked them
    assert con.execute("SELECT COUNT(*) FROM social_registry_links").fetchone()[0] == 0 and fake not in R.identity_cluster(con, real)


def test_signed_message_must_verify_and_name_the_account_to_count(con):
    a = account(con)
    for case, check, why in (("solana_unbound", "VALID_UNBOUND", "signature_valid_but_message_does_not_name_the_account"),
                             ("solana_tampered", "INVALID", "signature_does_not_verify")):
        chain, addr, msg, sg = sig_case(case)
        r = W.record(con, account_entity=a, chain=chain, wallet_address=addr, evidence_type="SIGNED_MESSAGE", evidence_ref=f"https://example.invalid/{case}",
                     recorded_by="t", message=msg, signature=sg, now=NOW)
        assert r["signature_check"] == check and r["confidence"] == "LOW"
        with pytest.raises(ValueError, match="cannot approve"):
            W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="looks fine", now=NOW)
        v = W.explain(con, a, chain, addr, now=NOW)
        assert v["level"] == "NONE" and why in v["assertions"][0]["why_not_counted"]
    row = con.execute("SELECT * FROM social_wallet_assertions WHERE signature_check='VALID_UNBOUND'").fetchone()
    assert row["evidence_sha256"] == hashlib.sha256(SIGNED["cases"]["solana_unbound"]["message"].encode()).hexdigest()
    assert "gm." not in " ".join(str(x) for x in row) and SIGNED["cases"]["solana_unbound"]["message"] not in json.dumps([dict(r) for r in con.execute("SELECT * FROM social_wallet_assertions")])
    with pytest.raises(ValueError, match="needs the signed message"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="SIGNED_MESSAGE", evidence_ref="https://example.invalid/x", recorded_by="t", now=NOW)


def test_evm_signed_message_and_unreviewed_signature_is_only_a_claim(con):
    a = account(con)
    chain, addr, msg, sg = sig_case("evm_bound")
    r = W.record(con, account_entity=a, chain=chain, wallet_address=addr, evidence_type="SIGNED_MESSAGE", evidence_ref="https://example.invalid/evm",
                 recorded_by="t", message=msg, signature=sg, now=NOW)
    assert r["signature_check"] == "VALID_BOUND"
    v = W.explain(con, a, chain, addr, now=NOW)
    assert v["level"] == "SELF_CLAIMED" and "signature_verified_awaiting_review" in v["assertions"][0]["why_not_counted"]
    W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="checked", now=NOW)
    assert W.explain(con, a, chain, addr, now=NOW)["level"] == "SIGNATURE_VERIFIED"
    # the same signature does not carry over to a different chain family
    with pytest.raises(ValueError):
        W.record(con, account_entity=a, chain="solana", wallet_address=addr, evidence_type="SIGNED_MESSAGE", evidence_ref="https://example.invalid/evm", recorded_by="t", message=msg, signature=sg, now=NOW)


def test_corroboration_needs_a_self_claim_plus_a_reviewed_independent_source(con):
    a = account(con)
    org = R.ensure_org(con, "outlet-one", "Outlet One", now=NOW)
    self_ = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p/1", recorded_by="t", now=NOW)
    ind = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="INDEPENDENT_LINKED_SOURCE", evidence_ref="https://example.invalid/profile",
                   recorded_by="t", asserter_entity=org, now=NOW)
    v = W.explain(con, a, "solana", T1, now=NOW)
    assert v["level"] == "SELF_CLAIMED" and "independent_source_awaiting_review" in [x for a_ in v["assertions"] for x in a_["why_not_counted"]]
    W.review(con, ind["assertion_id"], "APPROVED", reviewer="rev", reason="the source is not tied to the account", now=NOW)
    v = W.explain(con, a, "solana", T1, now=NOW)
    assert v["level"] == "CORROBORATED" and v["linked_status"] == "LINKED" and v["confidence"] == "MODERATE"
    # an independent source alone, or a source that operates the account, is not corroboration
    b = account(con, "second_account", "3003")
    ind_b = W.record(con, account_entity=b, chain="solana", wallet_address=T2, evidence_type="INDEPENDENT_LINKED_SOURCE", evidence_ref="https://example.invalid/profile2",
                     recorded_by="t", asserter_entity=org, now=NOW)
    W.review(con, ind_b["assertion_id"], "APPROVED", reviewer="rev", reason="ok", now=NOW)
    assert W.explain(con, b, "solana", T2, now=NOW)["level"] == "THIRD_PARTY_CLAIMED"
    R.add_link(con, link_type="OPERATED_BY_ORG", from_entity=b, to_entity=org, basis="SELF_STATEMENT", recorded_by="t", evidence_ref="https://example.invalid/about", now=NOW)
    R.review_link(con, R.active_links(con, b, ("OPERATED_BY_ORG",))[0]["link_id"], "APPROVED", reviewer="rev", reason="the org page says it runs the account", now=NOW)
    v = W.explain(con, b, "solana", T2, now=NOW)
    assert v["level"] == "NONE" and any("asserter_not_independent" in x for a_ in v["assertions"] for x in a_["why_not_counted"])
    assert self_["assertion_id"] != ind["assertion_id"]


def test_third_party_claim_never_exceeds_third_party_claimed_and_self_vouching_is_refused(con):
    a, other = account(con), account(con, "commentator", "4004")
    W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="THIRD_PARTY_CLAIM", evidence_ref="https://example.invalid/thread",
             recorded_by="t", asserter_entity=other, now=NOW)
    v = W.explain(con, a, "solana", T1, now=NOW)
    assert v["level"] == "THIRD_PARTY_CLAIMED" and v["linked_status"] == "NOT_LINKED"
    with pytest.raises(ValueError, match="vouching for itself"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="THIRD_PARTY_CLAIM", evidence_ref="https://example.invalid/t2", recorded_by="t", asserter_entity=a, now=NOW)
    with pytest.raises(ValueError, match="needs asserter_entity"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="THIRD_PARTY_CLAIM", evidence_ref="https://example.invalid/t3", recorded_by="t", now=NOW)


def test_transaction_pattern_is_a_hypothesis_and_never_counts(con):
    a = account(con)
    r = W.record(con, account_entity=a, chain="solana", wallet_address=T2, evidence_type="TRANSACTION_PATTERN", evidence_ref=f"tx:{IX['sigs']['21']}", recorded_by="t", now=NOW)
    assert r["control_hypothesis"] == "RELATED_BY_ACTIVITY"
    W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="the pattern is real", now=NOW)
    v = W.explain(con, a, "solana", T2, now=NOW)
    assert v["level"] == "HYPOTHESIS_ONLY" and v["linked_status"] == "NOT_LINKED" and "pattern_evidence_never_counts_toward_control" in v["assertions"][0]["why_not_counted"]
    with pytest.raises(ValueError, match="cites the transactions"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T2, evidence_type="TRANSACTION_PATTERN", evidence_ref="https://example.invalid/analysis", recorded_by="t", now=NOW)


def test_funding_by_the_same_wallet_is_a_hypothesis_not_attribution(con):
    track(con, T1, T2, T3)
    ingest(con)
    r = A.derive_funding_hypotheses(con, now=NOW)
    assert r["wallets_with_a_funder"] == 3
    hyp = {h["funder_address"]: h for h in map(dict, con.execute("SELECT * FROM social_wallet_funding_hypotheses"))}
    assert json.loads(hyp[FUNDER]["members_json"]) == sorted([T1, T2]) and hyp[FUNDER]["informative"] == 1 and hyp[FUNDER]["status"] == "HYPOTHESIS"
    assert {e["wallet"] for e in json.loads(hyp[FUNDER]["evidence_json"])} == {T1, T2}
    assert A.derive_funding_hypotheses(con, now=NOW + 1)["hypotheses_written"] == 0            # idempotent
    # T1 has verified control by one account; T2 only shares a funder
    a = account(con)
    chain, addr, msg, sg = sig_case("solana_bound")
    s = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p", recorded_by="t", now=NOW)
    W.review(con, s["assertion_id"], "APPROVED", reviewer="rev", reason="the account's own post", now=NOW)
    v2 = W.explain(con, a, "solana", T2, now=NOW)
    assert v2["level"] == "NONE" and v2["linked_status"] == "NOT_LINKED"
    assert v2["related_by_funding"] == [{"wallet": T1, "account_entity": a, "via_hypothesis": v2["funding_hypotheses"][0]["hypothesis_id"], "counts_toward_level": False,
                                         "note": "related by funding only; this does not attribute this wallet to that account"}]
    assert "reason to look, not evidence of common control" in v2["funding_hypotheses"][0]["meaning"]
    # funding from an exchange hot wallet says nothing at all
    v3 = W.explain(con, a, "solana", T3, now=NOW)
    h3 = v3["funding_hypotheses"][0]
    assert h3["informative"] is False and h3["funder_label"] == "CUSTODY_EXCHANGE" and "says nothing about common control" in h3["meaning"]
    assert con.execute("SELECT COUNT(*) FROM social_wallet_assertions WHERE wallet_address=?", (T2,)).fetchone()[0] == 0


def test_custody_address_cannot_be_controlled_or_tracked_by_default(con):
    a = account(con)
    assert W.effective_label(con, "solana", CEX)["kind"] == "CUSTODY_EXCHANGE" and W.effective_label(con, "solana", CEX)["source"] == "builtin:m09"
    with pytest.raises(ValueError, match="custody_wallet_not_monitored_by_default"):
        A.add_wallet(con, "solana", CEX, reason="r", added_by="t", now=T0)
    r = W.record(con, account_entity=a, chain="solana", wallet_address=CEX, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p/cex", recorded_by="t", now=NOW)
    with pytest.raises(ValueError, match="custody_or_protocol_wallet"):
        W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="the post says so", now=NOW)
    v = W.explain(con, a, "solana", CEX, now=NOW)
    assert v["level"] == "UNSUPPORTED_CUSTODY" and v["linked_status"] == "NOT_LINKED" and "wallet_labelled_custody_exchange" in v["assertions"][0]["why_not_counted"]
    # watching it on purpose is allowed and recorded
    A.add_wallet(con, "solana", CEX, reason="exchange flow study", added_by="t", allow_custody=True, fixture=True, now=T0)
    assert A.list_wallets(con)[0]["custody_override"] == 1
    # activity that touches custody is marked, but a transfer to an exchange is still not a sale
    track(con, T1)
    ingest(con)
    e = next(x for x in A.events(con, chain="solana", wallet=T1) if x["signature"] == IX["sigs"]["4"])
    assert e["event_type"] == "TOKEN_TRANSFER_OUT" and e["custody_touch"] == "CUSTODY_EXCHANGE" and e["counterparties"][0]["label"] == "CUSTODY_EXCHANGE"


def test_relabelling_a_wallet_changes_the_verdict_and_keeps_the_history(con):
    a = account(con)
    unknown = T3
    r = W.record(con, account_entity=a, chain="solana", wallet_address=unknown, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p/t3", recorded_by="t", now=NOW)
    W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="the account's own post", now=NOW)
    assert W.explain(con, a, "solana", unknown, now=NOW)["level"] == "SELF_CLAIMED"
    l1 = W.set_label(con, "solana", unknown, "CUSTODY_EXCHANGE", source_ref="https://example.invalid/exchange-proof-of-reserves", set_by="rev", text="exchange deposit address", now=NOW + 10)
    v = W.explain(con, a, "solana", unknown, now=NOW + 11)
    assert v["level"] == "UNSUPPORTED_CUSTODY" and v["wallet_label"]["source"] == f"label:{l1['label_id']}"
    # a reviewer corrects the built-in label for a different wallet, with a source
    l2 = W.set_label(con, "solana", unknown, "NO_SPECIAL_LABEL", source_ref="https://example.invalid/correction", set_by="rev", text="not an exchange after all", now=NOW + 20)
    assert l2["supersedes"] == l1["label_id"] and W.explain(con, a, "solana", unknown, now=NOW + 21)["level"] == "SELF_CLAIMED"
    W.set_label(con, "solana", CEX, "NO_SPECIAL_LABEL", source_ref="https://example.invalid/reviewed", set_by="rev", now=NOW + 30)
    assert W.effective_label(con, "solana", CEX)["kind"] == "NO_SPECIAL_LABEL"          # a sourced row beats the built-in list
    rows = con.execute("SELECT status FROM social_wallet_labels WHERE wallet_address=? ORDER BY label_id", (unknown,)).fetchall()
    assert [r[0] for r in rows] == ["SUPERSEDED", "ACTIVE"]
    assert [r[0] for r in con.execute("SELECT action FROM social_wallet_audit WHERE target_type='LABEL'")] == ["SET_LABEL"] * 3
    with pytest.raises(ValueError, match="source_ref"):
        W.set_label(con, "solana", unknown, "CUSTODY_OTHER", source_ref="", set_by="rev", now=NOW + 40)


def test_revoked_superseded_rejected_and_out_of_window_assertions_stay_visible(con):
    a = account(con)
    first = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/old",
                     recorded_by="t", valid_from=NOW - 30 * 86400, valid_to=NOW - 10 * 86400, observed_at=NOW - 30 * 86400, now=NOW)
    assert W.explain(con, a, "solana", T1, now=NOW)["level"] == "SELF_CLAIMED"                       # no as_of: the claim is current
    v = W.explain(con, a, "solana", T1, as_of=NOW, now=NOW)
    assert v["level"] == "NONE" and v["assertions"][0]["why_not_counted"] == ["outside_validity_window"]
    assert W.explain(con, a, "solana", T1, as_of=NOW - 20 * 86400, now=NOW)["level"] == "SELF_CLAIMED"   # it held then
    second = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/new",
                      recorded_by="t", supersedes=first["assertion_id"], now=NOW)
    old = W.get(con, first["assertion_id"])
    assert old["status"] == "SUPERSEDED" and old["superseded_by"] == second["assertion_id"]
    W.revoke(con, second["assertion_id"], reviewer="rev", reason="the post was deleted and the account denied it", now=NOW + 5)
    third = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="THIRD_PARTY_CLAIM", evidence_ref="https://example.invalid/rumour",
                     recorded_by="t", asserter_entity=account(con, "rumour_mill", "5005"), now=NOW)
    W.review(con, third["assertion_id"], "REJECTED", reviewer="rev", reason="no source for the claim", now=NOW)
    v = W.explain(con, a, "solana", T1, now=NOW + 10)
    assert v["level"] == "NONE"
    why = {x["assertion_id"]: x["why_not_counted"] for x in v["assertions"]}
    assert why[first["assertion_id"]] == [f"superseded_by_{second['assertion_id']}"] and why[second["assertion_id"]] == ["revoked"] and why[third["assertion_id"]] == ["rejected_by_reviewer"]
    assert len(v["assertions"]) == 3
    with pytest.raises(ValueError, match="only an active assertion"):
        W.review(con, second["assertion_id"], "APPROVED", reviewer="rev", reason="late", now=NOW + 20)
    with pytest.raises(ValueError, match="already"):
        W.revoke(con, second["assertion_id"], reviewer="rev", reason="again", now=NOW + 20)


def test_reviewer_can_read_why_in_plain_english_and_the_audit_trail_is_complete(con):
    a = account(con)
    r = W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/post/9", recorded_by="tester", now=NOW)
    W.review(con, r["assertion_id"], "APPROVED", reviewer="rev", reason="own account post", now=NOW + 1)
    W.revoke(con, r["assertion_id"], reviewer="rev", reason="withdrawn", now=NOW + 2)
    txt = W.report(W.explain(con, a, "solana", T1, now=NOW + 3))
    assert "Level: NONE" in txt and "Real-world identity: UNKNOWN" in txt and "not counted: revoked" in txt and "https://example.invalid/post/9" in txt
    trail = [(x["action"], x["actor"], x["from_state"], x["to_state"]) for x in con.execute("SELECT * FROM social_wallet_audit WHERE target_type='ASSERTION' ORDER BY audit_id")]
    assert trail == [("RECORD_OFFICIAL_SELF_DISCLOSURE", "tester", None, "UNREVIEWED"), ("REVIEW_APPROVED", "rev", "UNREVIEWED", "APPROVED"), ("REVOKE", "rev", "ACTIVE", "REVOKED")]
    with pytest.raises(ValueError, match="reason"):
        W.revoke(con, 999, reviewer="rev", reason="", now=NOW)
    with pytest.raises(ValueError, match="name is required"):
        W.review(con, r["assertion_id"], "APPROVED", reviewer="", reason="x", now=NOW)


def test_assertion_rows_hold_no_names_and_only_exact_wallets(con):
    a = account(con)
    with pytest.raises(ValueError, match="not a valid"):
        W.record(con, account_entity=a, chain="solana", wallet_address="@fx_trader_one", evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p", recorded_by="t", now=NOW)
    with pytest.raises(ValueError, match="social account"):
        W.record(con, account_entity=R.ensure_wallet(con, "solana", T1, now=NOW), chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE",
                 evidence_ref="https://example.invalid/p", recorded_by="t", now=NOW)
    with pytest.raises(ValueError, match="observed_at is in the future"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="https://example.invalid/p", recorded_by="t", observed_at=NOW + 9999, now=NOW)
    with pytest.raises(ValueError, match="evidence_ref"):
        W.record(con, account_entity=a, chain="solana", wallet_address=T1, evidence_type="OFFICIAL_SELF_DISCLOSURE", evidence_ref="trust me", recorded_by="t", now=NOW)
    cols = {r[1] for r in con.execute("PRAGMA table_info(social_wallet_assertions)")}
    assert not cols & {"real_name", "person", "name", "legal_name", "email"} and "real_world_identity" in cols
    assert {r[0] for r in con.execute("SELECT DISTINCT real_world_identity FROM social_wallet_assertions")} <= {"UNKNOWN"}


def test_adopting_registry_links_keeps_one_place_to_inspect(con):
    a = account(con)
    w = R.ensure_wallet(con, "solana", T1, now=NOW)
    lk = R.add_link(con, link_type="WALLET_SELF_DISCLOSED", from_entity=a, to_entity=w, basis="SELF_STATEMENT", recorded_by="t", evidence_ref="https://example.invalid/reg/1", now=NOW)
    R.review_link(con, lk["link_id"], "APPROVED", reviewer="rev", reason="own post", now=NOW)
    pr = R.add_link(con, link_type="WALLET_ON_CHAIN_PROOF", from_entity=a, to_entity=R.ensure_wallet(con, "solana", T2, now=NOW), basis="ON_CHAIN_PROOF", recorded_by="t",
                    evidence_ref=f"tx:{IX['sigs']['21']}", now=NOW)
    r = W.adopt_registry_links(con, now=NOW)
    assert len(r["adopted"]) == 1 and r["skipped"][0]["link_id"] == pr["link_id"] and "SIGNED_MESSAGE" in r["skipped"][0]["reason"]
    assert W.adopt_registry_links(con, now=NOW)["adopted"] == []
    v = W.explain(con, a, "solana", T1, now=NOW)
    assert v["level"] == "SELF_CLAIMED" and v["assertions"][0]["review_state"] == "APPROVED" and "adopted from registry link" in v["assertions"][0]["note"]


# ---------- bridge projection and plan ----------

def test_bridge_projection_keeps_full_signatures_and_plan_builds_per_wallet_requests(monkeypatch):
    for p in (ROOT / "bridge" / "collector.js", ROOT / "memelab" / "bridge" / "collector.js"):
        js = p.read_text()
        i = js.index("helius_wallet_tx: (j)")
        block = js[i:i + 800]
        assert "sig: t.signature," in block and "slice(0, 12)" not in block and "transactionError" in block
    monkeypatch.setattr("memelab.bridge.github_inbox.load_config", lambda: {"helius_api_key": "k"})
    plan = Plan("p").wallet_activity([T1, T2], limit=50)
    assert [r["key"] for r in plan.reqs] == [f"helius_wallet_tx:{T1}", f"helius_wallet_tx:{T2}"] and all(r["proj"] == "helius_wallet_tx" for r in plan.reqs)
    monkeypatch.setattr("memelab.bridge.github_inbox.load_config", lambda: {})
    with pytest.raises(RuntimeError, match="helius_api_key"):
        Plan("p").wallet_activity([T1])


# ---------- CLI ----------

def run(*args, db_path=None, env=None):
    cmd = [sys.executable, "-m", "memelab", "social", "wallet", *args] + (["--db", str(db_path)] if db_path else [])
    e = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=e)


def test_cli_demo_track_ingest_events_verify_and_why(tmp_path):
    dbp = tmp_path / "cli.sqlite"
    env = {"MEMELAB_PRIVATE_DB": str(tmp_path / "private.sqlite")}
    now = str(NOW)
    r = run("track", "add", "solana", T1, "--reason", "fixture demo", "--by", "tester", "--fixture", "--now", str(T0), db_path=dbp, env=env)
    assert r.returncode == 0, r.stderr
    r = run("ingest", str(FX / "fx_helius_ok.json"), "--fixture", "--now", now, db_path=dbp, env=env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["status"] == "OK" and {x["wallet"]: x for x in out["results"]}[T1]["stored"] == 13
    r = run("events", "--chain", "solana", "--wallet", T1, "--type", "SWAP", "--json", db_path=dbp, env=env)
    ev = json.loads(r.stdout)
    assert r.returncode == 0 and ev["count"] == 3 and "no profit" in ev["note"]
    r = run("verify", "2", "--source", str(FX / "fx_helius_ok.json"), db_path=dbp, env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["verified"] is True
    r = run("show", "solana", T1, db_path=dbp, env=env)
    assert r.returncode == 0 and "No profit or loss" in r.stdout
    r = run("status", db_path=dbp, env=env)
    assert json.loads(r.stdout)["pnl"] == "not computed in this phase"
    # attribution through the registry and CLI helpers
    c = sqlite3.connect(dbp)
    c.row_factory = sqlite3.Row
    acct = R.ensure_account(c, "x", handle=HANDLE, provider_user_id="1001", now=NOW)
    c.commit()
    c.close()
    r = run("assert", acct, "solana", T1, "--type", "OFFICIAL_SELF_DISCLOSURE", "--ref", "https://example.invalid/post/1", "--by", "tester", "--now", now, db_path=dbp, env=env)
    assert r.returncode == 0, r.stderr
    r = run("why", acct, "solana", T1, "--now", now, db_path=dbp, env=env)
    assert r.returncode == 0 and "Level: SELF_CLAIMED" in r.stdout and "Real-world identity: UNKNOWN" in r.stdout
    r = run("why", acct, "solana", T1, "--json", "--now", now, db_path=dbp, env=env)
    assert json.loads(r.stdout)["real_world_identity"] == "UNKNOWN"
    r = run("track", "pause", "solana", T1, "--by", "tester", "--reason", "enough", db_path=dbp, env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["status"] == "PAUSED"
    r = run("track", "add", "solana", CEX, "--reason", "r", "--by", "tester", db_path=dbp, env=env)
    assert r.returncode == 1 and "custody_wallet_not_monitored_by_default" in r.stderr


def test_cli_refuses_fixtures_in_the_tracked_database_and_refusals_write_nothing(tmp_path, monkeypatch):
    tracked = db.DATA_DIR / "memelab.sqlite"
    before = hashlib.sha256(tracked.read_bytes()).hexdigest()
    # other test modules set MEMELAB_DB for the whole process, so name the tracked database explicitly
    r = run("track", "add", "solana", T1, "--reason", "r", "--by", "t", "--fixture", env={"MEMELAB_DB": str(tracked)})
    assert r.returncode == 1 and "tracked database" in r.stderr
    assert hashlib.sha256(tracked.read_bytes()).hexdigest() == before
    dbp = tmp_path / "x.sqlite"
    r = run("track", "add", "solana", T1, "--reason", "", "--by", "t", db_path=dbp, env={"MEMELAB_PRIVATE_DB": str(tmp_path / "p.sqlite")})
    assert r.returncode == 1 and "reason" in r.stderr
    c = sqlite3.connect(dbp)
    assert c.execute("SELECT COUNT(*) FROM social_tracked_wallets").fetchone()[0] == 0
    c.close()


# ---------- repository rules ----------

def test_wallet_modules_make_no_network_calls_and_hold_no_key_material():
    for f in ("sigverify.py", "wallet_activity.py", "wallet_assertions.py", "wallet_cli.py"):
        src = (ROOT / "memelab" / "social" / f).read_text()
        assert not re.search(r"import (urllib|requests|http|socket|httpx|aiohttp)|urlopen|from (urllib|requests|http)", src), f
        assert not re.search(r"private_key|seed phrase|mnemonic|secret_key|sign\(", src, re.I) or f == "sigverify.py", f
    src = (ROOT / "memelab" / "social" / "sigverify.py").read_text()
    assert "private key anywhere" in src and "def sign" not in src


def test_content_guard_still_passes_with_the_wallet_fixtures_and_tables(con):
    track(con, T1)
    ingest(con)
    assert content_guard.check_sqlite("t.sqlite", Path(dbfile(con))) == []
    assert content_guard.scan(ROOT)["violations"] == []

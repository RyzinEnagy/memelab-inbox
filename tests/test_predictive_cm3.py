"""CM-3 (PI-D-130 to PI-D-133): catalyst and social tables in the state export and their reader (ED-3), the push-file alert
delivery (ED-7), HMAC signing of the private predictive state (ED-9) and the flag-on scout on rows of the real export (ED-8).

Change control: audits/predictive-intelligence/maintenance/cm3_spend_free/CHANGE_CONTROL.md. Temp databases and folders only,
fixed clocks, no network (the Phase 17 audit hook refuses sockets in every test of this module). The real export
`data/state/latest.json` is read, never written."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import types
from pathlib import Path

import pytest

from memelab import catsoc_export as CE
from memelab import cli, db
from memelab import state as STATE
from memelab.predictive import catsoc_adapter as CA
from memelab.predictive import integration as I
from memelab.predictive import reports as RP
from memelab.predictive import socialcat as SC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import test_predictive_integration as TI  # noqa: E402  (Phase 17 fixture builders and the no-network audit hook)
import test_predictive_reports as TR  # noqa: E402  (Phase 18 worlds)

no_network = TI.no_network                       # autouse fixtures re-exported so they run here too
no_backtest_store = TI.no_backtest_store

OLD_STATE = ROOT / "tests/fixtures/predictive/cm3/state_before_cm3.py.txt"
OLD_STATE_SHA = "9d2aeead685a0baa71a88030a1563b5c3c9c4455434c057cc74098bbd649dbb8"     # 60eb729:memelab/state.py
REAL_EXPORT = ROOT / "data/state/latest.json"
DAY = 86400.0
T0 = 1_791_000_000.0                          # 2026-10-03, a fixed clock
MINT, MINT_B = TI.M1, TI.M2
EVM = "0x" + "ab" * 20


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    monkeypatch.delenv(CE.ENV_FLAG, raising=False)
    monkeypatch.delenv(I.KEY_ENV, raising=False)
    monkeypatch.delenv(I.KEY_FILE_ENV, raising=False)
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def _ins(con, table, row):
    con.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' * len(row))})", list(row.values()))


def seed_catalyst(con, t, *, key="ev:listing:alpha", mint=MINT, second_independent=True, confirmed=True):
    """One event: an official source item naming the mint in its URL and body, a second independent item, a STRONG
    NAMED_IN_SOURCE link to the exact mint, a TICKER_MATCH link to another mint, CONFIRMED by a revision."""
    _ins(con, "catalyst_sources", {"source_id": "exch:alpha", "source_group": "scheduled", "kind": "json", "access_mode": "fetch",
                                   "tier": "official", "identity_notes": "copied profile wording that must never leave", "added_at": t - DAY})
    _ins(con, "catalyst_sources", {"source_id": "news:beta", "source_group": "news", "kind": "rss", "access_mode": "fetch",
                                   "tier": "reputable", "added_at": t - DAY})
    cur = con.execute("INSERT INTO catalyst_events (event_key, narrative_id, category, title, description, original_url, original_source_id, "
                      "discovered_at, retrieved_at, evidence_status, status, status_reason, created_at, updated_at) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (key, "kw:alpha", "ACCESS", "Headline written by a third party", "Body paragraph of a third party",
                       f"https://alpha.example/listing/{mint}", "exch:alpha", t, t, "CONFIRMED" if confirmed else "REPORTED", "TRACKED",
                       "free text reason", t, t + 60))
    ev = cur.lastrowid
    ids = []
    for n, (src, url, body) in enumerate([("exch:alpha", f"https://alpha.example/listing/{mint}", f"Alpha lists {mint} today"),
                                          ("news:beta", "https://beta.example/story-1", f"Beta reports the listing of {mint}")]):
        if n == 1 and not second_independent:
            break
        c = con.execute("INSERT INTO catalyst_items (source_id, item_key, url, title, body, author, platform, retrieved_at, first_seen_at, "
                        "raw_json, event_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (src, f"{key}:{n}", url, "third party title", body, "some_author", "web", t + n, t + n, '{"raw": "json"}', ev))
        ids.append(c.lastrowid)
        _ins(con, "catalyst_event_sources", {"event_id": ev, "item_id": c.lastrowid, "role": "ORIGINAL" if n == 0 else "INDEPENDENT"})
    _ins(con, "catalyst_token_links", {"event_id": ev, "mint": mint, "chain": "solana", "symbol": "ALPHA", "name": "Alpha",
                                       "link_type": "NAMED_IN_SOURCE", "link_strength": "STRONG", "verified_mint": 1,
                                       "rationale": "free text rationale", "competing_json": "[]", "linked_at": t + 5})
    _ins(con, "catalyst_token_links", {"event_id": ev, "mint": MINT_B, "chain": "solana", "link_type": "TICKER_MATCH",
                                       "link_strength": "WEAK", "linked_at": t + 5})
    _ins(con, "catalyst_event_revisions", {"event_id": ev, "revised_at": t + 10, "kind": "REVISED", "field": "evidence_status",
                                           "old_value": "REPORTED", "new_value": "CONFIRMED" if confirmed else "REPORTED",
                                           "note": "free text note"})
    _ins(con, "catalyst_event_revisions", {"event_id": ev, "revised_at": t + 11, "kind": "REVISED", "field": "title",
                                           "old_value": "old third-party headline", "new_value": "new third-party headline"})
    _ins(con, "catalyst_assessments", {"event_id": ev, "mint": mint, "assessed_at": t + 20, "components_json": "{}",
                                       "verdict": "RESEARCH", "verdict_reason": "free text", "triage_score": 40})
    return ev


def seed_social(con, t, *, mint=MINT, summary="Lab summary: an exact-address mention of a listing."):
    _ins(con, "social_analysis_versions", {"version": "extract-v1", "component": "extractor", "created_at": t - DAY})
    _ins(con, "social_accounts", {"account_id": "x:handle:someone_real", "platform": "x", "handle": "someone_real",
                                  "handle_normalized": "someone_real", "display_name": "Some One", "profile_url": "https://x.com/someone_real",
                                  "account_kind": "PERSON", "identity_status": "VERIFIED", "identity_checked_at": t - 3600,
                                  "first_seen_at": t - DAY, "last_seen_at": t, "notes": "bio-like note that must never leave"})
    _ins(con, "social_traders", {"trader_id": "someone_real", "label": "Some One", "added_at": t - DAY, "updated_at": t - DAY})
    _ins(con, "social_trader_accounts", {"trader_id": "someone_real", "account_id": "x:handle:someone_real", "link_basis": "SELF_DECLARED",
                                         "evidence_status": "FACT", "linked_at": t - DAY})
    _ins(con, "social_items", {"item_key": "x:1001", "platform": "x", "provider_item_id": "1001", "account_id": "x:handle:someone_real",
                               "original_url": "https://x.com/someone_real/status/1001", "published_at": t, "first_ingested_at": t})
    _ins(con, "social_items", {"item_key": "x:1002", "platform": "x", "provider_item_id": "1002", "account_id": "x:handle:someone_real",
                               "published_at": t, "first_ingested_at": t})            # ticker-only: never exported
    _ins(con, "social_observations", {"observation_key": "obs1", "item_key": "x:1001", "account_id": "x:handle:someone_real",
                                      "observed_at": t, "observed_at_basis": "COLLECTOR", "ingested_at": t, "access_mode": "fetch",
                                      "collector": "fx", "retrieval_status": "OK", "content_hash": "c" * 64, "retained_content": "SUMMARY",
                                      "summary": summary, "analysis_version": "extract-v1"})
    _ins(con, "social_observations", {"observation_key": "obs2", "item_key": "x:1002", "observed_at": t, "observed_at_basis": "COLLECTOR",
                                      "ingested_at": t, "access_mode": "fetch", "collector": "fx", "retrieval_status": "OK",
                                      "content_hash": "d" * 64})
    _ins(con, "social_token_refs", {"ref_key": f"ca:solana:{mint}", "ref_kind": "CONTRACT_ADDRESS", "chain": "solana", "contract": mint,
                                    "first_seen_at": t})
    for key, item, kind, status, ch, ct in (("r1", "x:1001", "CONTRACT", "resolved", "solana", mint),
                                            ("r2", "x:1002", "TICKER", "unresolved", None, None)):
        _ins(con, "social_token_resolutions", {"resolution_key": key, "item_key": item, "mention_key": f"m:{key}", "mention_kind": kind,
                                               "mention_value": mint if kind == "CONTRACT" else "ALPHA", "status": status,
                                               "reasons_json": "[]", "resolved_chain": ch, "resolved_contract": ct, "evidence_json": "[]",
                                               "evidence_sha": "e" * 64, "resolver_version": "extract-v1", "resolved_at": t + 1})
    _ins(con, "social_claims", {"claim_key": "cl1", "item_key": "x:1001", "account_id": "x:handle:someone_real", "claim_type": "LISTING",
                                "direction": "UNKNOWN", "claimed_at": t, "extracted_at": t + 2, "analysis_version": "extract-v1",
                                "summary": "a long summary " * 20})


def build(lab, t=T0, **kw):
    with db.connect() as con:
        seed_catalyst(con, t, **kw)
        seed_social(con, t)


def export_doc(lab, monkeypatch, now, name="e.json", on=True):
    if on:
        monkeypatch.setenv(CE.ENV_FLAG, "1")
    else:
        monkeypatch.delenv(CE.ENV_FLAG, raising=False)
    monkeypatch.setattr(STATE.time, "time", lambda: now)
    monkeypatch.setattr(CE.time, "time", lambda: now)
    p = STATE.export(lab / name)
    return json.loads(p.read_text()), p


def _load_old_state():
    text = OLD_STATE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == OLD_STATE_SHA
    mod = types.ModuleType("memelab._state_before_cm3")
    mod.__package__ = "memelab"
    mod.__file__ = str(ROOT / "memelab" / "state.py")
    exec(compile(text, str(OLD_STATE), "exec"), mod.__dict__)
    return mod


# ================================================================ ED-3: export
def test_flag_off_export_is_byte_identical_to_the_60eb729_exporter(lab, monkeypatch):
    build(lab)
    with db.connect() as con:
        db.upsert_token(con, MINT, chain="solana", symbol="ALPHA")
    old = _load_old_state()
    monkeypatch.setattr(old.time, "time", lambda: T0 + 100)
    a = old.export(lab / "old.json").read_bytes()
    _, p = export_doc(lab, monkeypatch, T0 + 100, "new.json", on=False)
    assert p.read_bytes() == a and b"_catsoc" not in a
    (lab / "data" / "config.json").write_text(json.dumps({"state_export": {"catalyst_social": "true"}}))   # not JSON true: OFF
    _, p = export_doc(lab, monkeypatch, T0 + 100, "new2.json", on=False)
    assert p.read_bytes() == a
    (lab / "data" / "config.json").write_text("{not json")
    _, p = export_doc(lab, monkeypatch, T0 + 100, "new3.json", on=False)
    assert p.read_bytes() == a


def test_flag_on_adds_only_the_section_and_the_tables_part_is_unchanged(lab, monkeypatch):
    build(lab)
    off, _ = export_doc(lab, monkeypatch, T0 + 100, "off.json", on=False)
    (lab / "data" / "config.json").write_text(json.dumps({"state_export": {"catalyst_social": True}}))
    on, _ = export_doc(lab, monkeypatch, T0 + 100, "on.json", on=False)
    assert set(on) == set(off) | {"_catsoc"} and {k: on[k] for k in off} == off
    sec = on["_catsoc"]
    assert sec["version"] == CE.VERSION and "withheld" not in sec and CE.problems(sec) == []
    assert all(tuple(r) == CE.COLUMNS[t] for t, rows in sec["tables"].items() for r in rows)


def test_the_section_carries_no_text_handle_url_or_bio_and_hashes_third_party_ids(lab, monkeypatch):
    build(lab)
    doc, p = export_doc(lab, monkeypatch, T0 + 100)
    raw = json.dumps(doc["_catsoc"])
    for banned in ("Headline written by a third party", "Body paragraph", "third party title", "some_author", "someone_real", "Some One",
                   "bio-like note", "free text", "copied profile wording", "x.com", "https://", "old third-party headline", '"raw"',
                   "a long summary", "ALPHA", "x:1001"):
        assert banned not in raw, banned
    t = doc["_catsoc"]["tables"]
    assert t["social_observations"][0]["summary"] == "Lab summary: an exact-address mention of a listing."
    assert t["social_claims"][0]["summary"] is None and doc["_catsoc"]["withheld_summaries"] == 1
    assert [i["item_ref"] for i in t["social_items"]] == [CE.ref("x:1001")]                    # the ticker-only item is not exported
    assert t["social_accounts"][0]["account_ref"] == CE.ref("x:handle:someone_real")
    assert {r["field"]: r["new_value"] for r in t["catalyst_event_revisions"]} == {"evidence_status": "CONFIRMED", "title": None}
    items = sorted(t["catalyst_items"], key=lambda i: i["source_id"])
    assert items[0]["mints_in_url"] == [MINT] and items[0]["mints_in_body"] == [MINT] and items[1]["mints_in_url"] == []
    assert items[0]["body_norm_sha256"] == hashlib.sha256(f"alpha lists {MINT.lower()} today".encode()).hexdigest()
    assert {(k["mint"], k["link_type"]) for k in t["catalyst_token_links"]} == {(MINT, "NAMED_IN_SOURCE"), (MINT_B, "TICKER_MATCH")}
    assert all(not ({"id", "event_id", "item_id", "fetch_id"} & set(r)) for rows in t.values() for r in rows)   # no database row id
    assert subprocess.run([sys.executable, "-m", "memelab.catsoc_export", "check", str(p)], cwd=ROOT).returncode == 0


@pytest.mark.parametrize("plant", ["extra_column", "bio_key", "markdown_key", "long_summary", "handle_summary"])
def test_a_planted_violation_withholds_the_section_and_the_export_still_succeeds(lab, monkeypatch, plant):
    build(lab)
    real = CE._social

    def planted(con, have, since, withheld):
        out = real(con, have, since, withheld)
        r = out["social_observations"][0]
        if plant == "extra_column":
            r["display_name"] = "x"
        elif plant == "bio_key":
            r["bio"] = "x"
        elif plant == "markdown_key":
            r["markdown"] = "x"
        elif plant == "long_summary":
            r["summary"] = "y" * 201
        else:
            r["summary"] = "said by @someone"
        return out
    monkeypatch.setattr(CE, "_social", planted)
    doc, _ = export_doc(lab, monkeypatch, T0 + 100)
    assert doc["_catsoc"]["withheld"] == "GUARD_VIOLATION" and "tables" not in doc["_catsoc"] and doc["_catsoc"]["rules"]
    assert doc["_tables"]["tokens"] == []                               # the export itself is complete


def test_an_error_inside_the_section_never_fails_the_export(lab, monkeypatch):
    build(lab)
    monkeypatch.setattr(CE, "_catalyst", lambda *a: 1 / 0)
    doc, _ = export_doc(lab, monkeypatch, T0 + 100)
    assert doc["_catsoc"] == {"version": CE.VERSION, "withheld": "ERROR", "error": "ZeroDivisionError"}


def test_rows_outside_the_window_are_not_exported(lab, monkeypatch):
    build(lab)
    doc, _ = export_doc(lab, monkeypatch, T0 + 31 * DAY)
    assert all(rows == [] for rows in doc["_catsoc"]["tables"].values() if rows is not None)


def test_the_old_importer_ignores_the_section_and_the_new_importer_round_trips_idempotently(lab, monkeypatch, tmp_path):
    build(lab)
    doc, p = export_doc(lab, monkeypatch, T0 + 100)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "fresh.sqlite")
    db.init_db()
    added = STATE.import_(str(p))
    assert set(added) == set(STATE.TABLES)
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM catalyst_events").fetchone()[0] == 0     # the lab tables are never filled from it
    dest = tmp_path / "out" / "catsoc.sqlite"
    r1 = CE.import_(p, dest, commit_time=T0 + 500)
    r2 = CE.import_(p, dest, commit_time=T0 + 900)
    assert r1["state"] == "IMPORTED" and r1["rows_added"] == sum(len(v) for v in doc["_catsoc"]["tables"].values()) and r2["rows_added"] == 0
    back = CE.read_store(dest)
    assert {t: sorted(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, sort_keys=True) for r in rows) for t, rows in back.items()} == \
        {t: sorted(json.dumps(r, sort_keys=True) for r in rows) for t, rows in doc["_catsoc"]["tables"].items()}
    assert {r["_first_export_at"] for rows in back.values() for r in rows} == {T0 + 500}
    assert {r["_time_basis"] for rows in back.values() for r in rows} == {"COMMIT"}


def test_the_importer_refuses_the_lab_database_the_repository_and_another_schema(lab, monkeypatch, tmp_path):
    build(lab)
    _, p = export_doc(lab, monkeypatch, T0 + 100)
    for dest, why in ((db.DB_PATH, "lab database"), (ROOT / "data" / "catsoc.sqlite", "inside the repository")):
        with pytest.raises(CE.CatsocError, match=why):
            CE.import_(p, dest)
    other = tmp_path / "other.sqlite"
    sqlite3.connect(other).execute("CREATE TABLE t (x)").connection.commit()
    with pytest.raises(CE.CatsocError, match="other tables"):
        CE.import_(p, other)
    with pytest.raises(CE.CatsocError, match="local files only"):
        CE.import_("https://example.invalid/latest.json", tmp_path / "x.sqlite")
    assert not (ROOT / "data" / "catsoc.sqlite").exists()


# ================================================================ ED-3: reader as of the export commit
def _versions(lab, monkeypatch, steps):
    """steps: [(commit_time, export_now, mutate or None, flag_on)] -> export versions oldest first."""
    out = []
    for n, (ct, now, mutate, on) in enumerate(steps):
        if mutate:
            with db.connect() as con:
                mutate(con)
        doc, _ = export_doc(lab, monkeypatch, now, f"v{n}.json", on=on)
        out.append({"commit": f"c{n}", "commit_time": ct, "doc": doc})
    return out


def test_no_section_by_t_is_tables_not_exported_and_a_mint_without_rows_is_named(lab, monkeypatch):
    build(lab)
    vs = _versions(lab, monkeypatch, [(T0 + 1000, T0 + 900, None, False), (T0 + 5000, T0 + 4900, None, True)])
    prep = CA.prepare(vs)
    s = CA.states_as_of(prep, "solana", MINT, T0 + 4000)
    assert (s["catalyst_state"], s["social_state"]) == (SC.CATALYST_STATE_REAL, SC.SOCIAL_STATE_REAL)
    s = CA.states_as_of(prep, "solana", TI.b58("nobody"), T0 + 6000)
    assert (s["catalyst_state"], s["social_state"]) == (CA.NO_CATALYST, CA.NO_SOCIAL)


def test_a_verified_catalyst_is_available_from_the_export_commit_not_from_its_own_clock(lab, monkeypatch):
    build(lab)
    vs = _versions(lab, monkeypatch, [(T0 + 7200, T0 + 7000, None, True)])
    prep = CA.prepare(vs)
    early = CA.catalyst_as_of(prep, "solana", MINT, T0 + 3600)           # every row's own time is before T, the commit is after
    assert early["state"] == SC.CATALYST_STATE_REAL and early["events"] == []
    c = CA.catalyst_as_of(prep, "solana", MINT, T0 + 7200)
    ev = c["events"][0]
    assert c["state"] == "VERIFIED" and ev["identity"] == "EXACT_MINT_IN_SOURCE" and ev["available_at"] == T0 + 7200
    assert ev["evidence_class"] == "TEST_ONLY" and c["probability"] is None and ev["probability"] is None


def test_a_row_first_exported_later_stays_invisible_until_that_commit(lab, monkeypatch):
    build(lab, second_independent=False)

    def add_second(con):
        ev = con.execute("SELECT id FROM catalyst_events").fetchone()[0]
        c = con.execute("INSERT INTO catalyst_items (source_id, item_key, url, body, retrieved_at, first_seen_at, event_id) VALUES "
                        "(?,?,?,?,?,?,?)", ("news:beta", "late", "https://beta.example/late", f"Late story on {MINT}", T0 + 2, T0 + 2, ev))
        con.execute("INSERT INTO catalyst_event_sources VALUES (?,?,?)", (ev, c.lastrowid, "INDEPENDENT"))
    vs = _versions(lab, monkeypatch, [(T0 + 1000, T0 + 900, None, True), (T0 + 9000, T0 + 8900, add_second, True)])
    prep = CA.prepare(vs)
    a = CA.catalyst_as_of(prep, "solana", MINT, T0 + 5000)
    b = CA.catalyst_as_of(prep, "solana", MINT, T0 + 9000)
    assert a["events"][0]["independent_sources"] == 1 and b["events"][0]["independent_sources"] == 2
    assert a["state"] == "VERIFIED" and a["events"][0]["official_source"] is True       # the official item names the mint
    assert b["events"][0]["source_rule_met_at"] == T0 + 1000


def test_identity_is_exact_chain_and_mint_only(lab, monkeypatch):
    build(lab)
    prep = CA.prepare(_versions(lab, monkeypatch, [(T0 + 1000, T0 + 900, None, True)]))
    assert CA.catalyst_as_of(prep, "solana", MINT_B, T0 + 2000)["state"] == "IDENTITY_UNVERIFIED"    # ticker match only
    assert CA.catalyst_as_of(prep, "base", MINT, T0 + 2000)["state"] == CA.NO_CATALYST              # same address, other chain
    assert CA.social_as_of(prep, "base", MINT, T0 + 2000)["state"] == CA.NO_SOCIAL


def test_social_evidence_from_the_export_matches_the_phase10_function_on_the_lab_rows(lab, monkeypatch):
    build(lab)
    prep = CA.prepare(_versions(lab, monkeypatch, [(T0 + 1000, T0 + 900, None, True)]))
    s = CA.social_as_of(prep, "solana", MINT, T0 + 2000)
    assert s["state"] == CA.SOCIAL_EXPORTED and s["evidence_class"] == "TEST_ONLY" and s["llm_used"] is False
    v = s["values"]
    assert v["sx_mentions_exact"] == 1.0 and v["sx_distinct_sources"] == 1.0 and v["sx_ticker_only_mentions"] == 0.0
    assert s["account_labels"] == "REPLAY_KNOWN_AT_T_ONLY"
    with sqlite3.connect(db.DB_PATH) as con:                              # the same rows read directly, times moved to the commit
        con.row_factory = sqlite3.Row
        direct = SC.read_social(con)
    for t in direct.values():
        for r in t:
            for f in ("ingested_at", "resolved_at", "first_ingested_at", "linked_at", "extracted_at", "first_seen_at", "identity_checked_at"):
                if r.get(f) is not None:
                    r[f] = max(r[f], T0 + 1000)
    want = SC.social_as_of(direct, "solana", MINT, T0 + 2000)
    assert {k: x for k, x in want["values"].items() if k != "sx_ticker_only_mentions"} == \
        {k: x for k, x in v.items() if k != "sx_ticker_only_mentions"}


def test_a_hand_edited_section_is_ignored_as_withheld(lab, monkeypatch):
    build(lab)
    vs = _versions(lab, monkeypatch, [(T0 + 1000, T0 + 900, None, True)])
    vs[0]["doc"]["_catsoc"]["tables"]["catalyst_items"][0]["body"] = "copied text"
    prep = CA.prepare(vs)
    assert prep["first_section_at"] is None and prep["withheld"] == [{"commit": "c0", "commit_time": T0 + 1000}]
    assert CA.states_as_of(prep, "solana", MINT, T0 + 2000)["catalyst_state"] == SC.CATALYST_STATE_REAL


def test_versions_out_of_order_are_refused():
    with pytest.raises(CA.CatsocAdapterError):
        CA.prepare([{"commit": "b", "commit_time": 2.0, "doc": {}}, {"commit": "a", "commit_time": 1.0, "doc": {}}])


def test_the_adapter_reads_no_network_no_clock_and_leaves_socialcat_untouched():
    import ast
    tree = ast.parse((ROOT / "memelab/predictive/catsoc_adapter.py").read_text())
    names = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert names <= {"annotations", "json", "hashlib", "Any", "Sequence", "catsoc_export", "socialcat"}, names
    reg = I.load_registry(ROOT / I.REGISTRY_DIR)
    from memelab.predictive import registry as R
    assert reg["state"] == "OK" and all(R.code_changes(e, ROOT) == [] for e in reg["entries"].values())


def test_real_export_history_gives_tables_not_exported_for_every_real_decision_mint():
    """The git history of data/state/latest.json carries no section yet: every real mint at the newest commit reads as not
    exported (nothing is invented for real decisions)."""
    log = subprocess.run(["git", "log", "--format=%H %ct", "--", "data/state/latest.json"], cwd=ROOT, capture_output=True, text=True)
    if log.returncode != 0 or not log.stdout.strip():
        pytest.skip("no git history of the export in this checkout")
    commits = [ln.split() for ln in log.stdout.split("\n") if ln.strip()][::-1]
    vs = []
    for h, ct in commits[-3:]:
        blob = subprocess.run(["git", "show", f"{h}:data/state/latest.json"], cwd=ROOT, capture_output=True)
        vs.append({"commit": h, "commit_time": float(ct), "doc": json.loads(blob.stdout)})
    prep = CA.prepare(vs)
    assert prep["first_section_at"] is None
    mints = sorted({t["mint"] for t in (vs[-1]["doc"].get("_tables") or vs[-1]["doc"]).get("theses", [])})[:25]
    assert mints
    for m in mints:
        s = CA.states_as_of(prep, "solana", m, vs[-1]["commit_time"])
        assert (s["catalyst_state"], s["social_state"]) == (SC.CATALYST_STATE_REAL, SC.SOCIAL_STATE_REAL)


# ================================================================ ED-7: push file
def _alerts(lab, **kw):
    d = TR.world_abstain(lab)
    return d, RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", outbox=lab / "al" / "outbox",
                           now=d["now"], lab_db=d["lab_db"], **kw)


def test_push_file_writes_one_short_line_per_new_alert_and_no_number_or_trading_word(lab):
    d, out = _alerts(lab, send="push_file")
    lines = (lab / "al" / "outbox" / "push" / out["push"]["file"]).read_text().splitlines()
    assert out["push"]["lines"] == len(lines) == len(out["evaluation"]["new"]) >= 1
    for ln in lines:
        assert len(ln) <= RP.PUSH_LINE_MAX and ln.startswith("memelab research ") and "%" not in ln and "probab" not in ln.lower()
        RP.check_push_line(ln, [TI.M1, TI.M2, TI.M3, TR.M4, TR.M5])
    assert any("risk override for GOMOX" in ln for ln in lines)
    con = sqlite3.connect(lab / "al" / "a.sqlite")
    rows = con.execute("SELECT transport, status, mode FROM alert_deliveries WHERE transport='push_file'").fetchall()
    assert rows and set(rows) == {("push_file", "dry_run_preview", "dry_run")}
    assert out["mode"] == "dry_run"


def test_the_default_dry_run_is_unchanged_by_the_push_path(tmp_path, monkeypatch):
    outs = []
    for send in (False, "push_file"):
        sub = tmp_path / "w"                                            # the same folder for both runs: paths in the records are equal
        if sub.exists():
            shutil.rmtree(sub)
        sub.mkdir()
        monkeypatch.setattr(db, "DB_PATH", sub / "lab.sqlite")
        monkeypatch.setattr(db, "DATA_DIR", sub / "data")
        (sub / "data").mkdir()
        db.init_db()
        d, out = _alerts(sub, send=send)
        prev = sorted(p.read_text() for p in (sub / "al" / "outbox" / "preview").iterdir())
        outs.append((out, prev))
    (a, pa), (b, pb) = outs
    push = b.pop("push")
    assert a == b and pa == pb and push["lines"] >= 1
    assert (tmp_path / "w" / "al" / "outbox" / "push").exists()


@pytest.mark.parametrize("send", [True, "", "telegram", "email", "push", "PUSH_FILE"])
def test_every_other_send_is_refused_before_anything_is_written(lab, send):
    d = TR.world_abstain(lab)
    with pytest.raises(RP.AlertRefused, match="--send refused"):
        RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", now=d["now"], send=send)
    assert not (lab / "al").exists()


def test_the_cli_accepts_only_push_file_and_bare_send_stays_refused(lab):
    d = TR.world_abstain(lab)
    base = [sys.executable, "-m", "memelab.predictive.reports", "alerts", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]),
            "--alert-db", str(lab / "al" / "a.sqlite"), "--as-of", str(d["now"])]
    env = {**__import__("os").environ, "MEMELAB_DB": str(db.DB_PATH), "MEMELAB_BT_DB": str(lab / "nobt" / "bt.sqlite")}
    for extra in (["--send"], ["--send", "telegram"]):
        r = subprocess.run(base + extra, cwd=ROOT, capture_output=True, text=True, env=env)
        assert r.returncode == 2 and "--send refused" in r.stderr
    r = subprocess.run(base + ["--send", "push_file"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "Push file:" in r.stdout and "nothing sent by memelab" in r.stdout


@pytest.mark.parametrize("bad", ["50% up", "probability 0.4", "interval 10 to 20", "buy now", "see /home/someone/x", "two\nlines"])
def test_the_push_line_check_refuses_numbers_words_paths_and_newlines(bad):
    with pytest.raises(RP.ReportError):
        RP.check_push_line("memelab research notice: " + bad)


def test_reports_module_gains_no_network_import():
    txt = (ROOT / "memelab/predictive/reports.py").read_text()
    for lib in ("urllib", "http.client", "requests", "smtplib", "socket"):
        assert f"import {lib}" not in txt


# ================================================================ ED-9: signing
KEY = "k" * 48


def _signed_world(lab, monkeypatch, key=KEY):
    if key:
        monkeypatch.setenv(I.KEY_ENV, key)
    r = TI.persist(TI.result("AAA", MINT, TI.T_TODAY - 600), lab)
    TI.run([r], TI.T_TODAY, lab)
    return lab / "state"


def test_signed_state_round_trips_and_status_says_verified(lab, monkeypatch):
    sd = _signed_world(lab, monkeypatch)
    sig = json.loads((sd / I.SIG_FILE).read_text())
    assert sig["version"] == I.SIG_VERSION and sig["seq"] == 0 and KEY not in (sd / I.SIG_FILE).read_text()
    I.load_state(sd)
    assert I.signature_status(sd)["signature"] == "SIGNED_VERIFIED"
    r2 = TI.persist(TI.result("BBB", MINT_B, TI.T_TODAY - 300), lab)
    TI.run([r2], TI.T_TODAY + 60, lab)
    assert json.loads((sd / I.SIG_FILE).read_text())["seq"] == 1 and I.signature_status(sd)["signature"] == "SIGNED_VERIFIED"


def _reseal(sd: Path):
    """The reseal attack (F20-08): rewrite a request line, recompute every record id and file sha256 the chain records."""
    from memelab.predictive import abstention as AB
    req = [json.loads(x) for x in (sd / I.FILES["requests"]).read_text().splitlines()]
    req[0]["event"] = req[0]["event"]
    req[0]["note_cm3"] = "forged"
    req[0] = I._sealed(req[0])
    (sd / I.FILES["requests"]).write_text("".join(AB.canon(r) + "\n" for r in req))
    passes = [json.loads(x) for x in (sd / I.FILES["passes"]).read_text().splitlines()]
    prev = I.GENESIS
    out = []
    for p in passes:
        p = dict(p, prev=prev)
        p["files_after"] = dict(p["files_after"], requests=AB.file_sha(sd / I.FILES["requests"]))
        p = I._sealed(p)
        prev = p["record_id"]
        out.append(p)
    (sd / I.FILES["passes"]).write_text("".join(AB.canon(p) + "\n" for p in out))


def test_a_reseal_attack_is_caught_with_a_key_and_not_without(lab, monkeypatch):
    sd = _signed_world(lab, monkeypatch)
    _reseal(sd)
    with pytest.raises(I.StateTampered, match="does not name the last pass|does not match"):
        I.load_state(sd)
    monkeypatch.delenv(I.KEY_ENV)
    I.load_state(sd)                                                    # hash chain alone cannot catch it (the ED-9 residual)
    assert I.signature_status(sd)["signature"] == "SIGNATURE_NOT_VERIFIED_NO_KEY"


def test_a_forged_signature_or_a_wrong_key_is_refused(lab, monkeypatch):
    sd = _signed_world(lab, monkeypatch)
    rec = json.loads((sd / I.SIG_FILE).read_text())
    (sd / I.SIG_FILE).write_text(json.dumps(dict(rec, hmac="0" * 64)))
    with pytest.raises(I.StateTampered, match="signature does not match"):
        I.load_state(sd)
    (sd / I.SIG_FILE).write_text(json.dumps(rec))
    monkeypatch.setenv(I.KEY_ENV, "z" * 48)
    with pytest.raises(I.StateTampered, match="signature does not match"):
        I.load_state(sd)


def test_unsigned_state_is_refused_with_a_key_and_allowed_and_recorded_without(lab, monkeypatch):
    sd = _signed_world(lab, monkeypatch, key=None)
    assert not (sd / I.SIG_FILE).exists()
    assert I.signature_status(sd) == {"signature": "UNSIGNED_NO_KEY", "key_configured": False}
    monkeypatch.setenv(I.KEY_ENV, KEY)
    with pytest.raises(I.StateTampered, match="unsigned while a signing key is configured"):
        I.load_state(sd)
    r = TI.persist(TI.result("BBB", MINT_B, TI.T_TODAY - 300), lab)
    out = TI.run([r], TI.T_TODAY + 60, lab)
    assert out["state"] == "STATE_TAMPERED"                             # the pass refuses and writes nothing
    assert I.sign_state(sd) == {"signature": "SIGNED", "seq": 0}
    assert I.signature_status(sd)["signature"] == "SIGNED_VERIFIED"


def test_without_a_key_the_state_files_are_the_same_as_before(lab, monkeypatch, tmp_path):
    sd = _signed_world(lab, monkeypatch, key=None)
    names = {p.name for p in sd.iterdir()}
    assert names <= set(I.FILES.values()) and I.SIG_FILE not in names


def test_a_short_key_or_a_key_file_in_the_repository_is_refused_and_the_key_is_never_shown(lab, monkeypatch, tmp_path):
    monkeypatch.setenv(I.KEY_ENV, "short-key-value")
    with pytest.raises(I.StateKeyError) as e:
        I.state_key()
    assert "short-key-value" not in str(e.value)
    monkeypatch.delenv(I.KEY_ENV)
    monkeypatch.setenv(I.KEY_FILE_ENV, str(ROOT / "README.md"))
    with pytest.raises(I.StateKeyError, match="inside the repository"):
        I.state_key()
    kf = tmp_path / "outside" / "state.key"
    kf.parent.mkdir()
    kf.write_text("q" * 64 + "\n")
    monkeypatch.setenv(I.KEY_FILE_ENV, str(kf))
    assert I.state_key() == b"q" * 64
    sd = _signed_world(lab, monkeypatch, key=None)
    env = {**__import__("os").environ, I.KEY_FILE_ENV: str(kf)}
    r = subprocess.run([sys.executable, "-m", "memelab.predictive.integration", "sign-status", "--state-dir", str(sd)], cwd=ROOT,
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["signature"] == "SIGNED_VERIFIED" and "q" * 32 not in r.stdout + r.stderr
    env[I.KEY_ENV], env[I.KEY_FILE_ENV] = "tiny", ""
    r = subprocess.run([sys.executable, "-m", "memelab.predictive.integration", "check", "--state-dir", str(sd)], cwd=ROOT,
                       capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "STATE_TAMPERED" in r.stdout and "tiny" not in r.stdout + r.stderr


# ================================================================ ED-8: flag on, rows of the real export
def _real_rows(n=6):
    doc = json.loads(REAL_EXPORT.read_text())
    tabs = doc.get("_tables") or doc
    toks = {t["mint"]: t for t in tabs.get("tokens") or []}
    newest: dict[str, dict] = {}
    for r in tabs.get("theses") or []:
        if r["mint"] in toks and (toks[r["mint"]].get("chain") or "solana") == "solana":
            if r["mint"] not in newest or (r["created_at"] or 0) > (newest[r["mint"]]["created_at"] or 0):
                newest[r["mint"]] = r
    picked = sorted(newest.values(), key=lambda r: (-(r["created_at"] or 0), r["mint"]))
    out, seen = [], set()
    for r in picked:                               # a mix: fatal-flagged and clean rows, different statuses
        fatal = [f.get("flag") if isinstance(f, dict) else str(f) for f in json.loads(r.get("fatal_flags_json") or "[]")]
        k = (bool(fatal), r.get("status"))
        if k in seen and len(out) >= 3:
            continue
        seen.add(k)
        out.append((r, fatal, toks[r["mint"]]))
        if len(out) >= n:
            break
    return out


def test_ed8_a_flag_on_scout_on_rows_of_the_real_export_keeps_score_fatal_flags_statuses_and_lists(tmp_path, monkeypatch):
    if not REAL_EXPORT.exists():
        pytest.skip("no real export in this checkout")
    before = hashlib.sha256(REAL_EXPORT.read_bytes()).hexdigest()
    T = TI.T_TODAY
    rows = _real_rows()
    assert len(rows) >= 3 and any(f for _, f, _ in rows)
    rs = [TI.result(str(tok.get("symbol") or "REAL")[:10], r["mint"], T - 600, score=int(r["score"] or 0), status=r["status"],
                    fatal=tuple(f), pool=tok.get("primary_pool") or tok.get("graduated_pool") or TI.POOL1) for r, f, tok in rows]
    doff = TI._fresh_lab(tmp_path, monkeypatch, "run")
    off, out_off = TI._scout(cli, monkeypatch, doff, copy.deepcopy(rs), T - 600)
    dump_off = TI._lab_dump(doff / "lab.sqlite")
    shutil.rmtree(doff)
    don = TI._fresh_lab(tmp_path, monkeypatch, "run")
    (don / "data" / "config.json").write_text(json.dumps({"predictive": {"enabled": True, "state_dir": str(don / "st")}}))
    real = I.scout_section
    monkeypatch.setattr(I, "scout_section", lambda results, **k: real(results, capture_time=T, **k))
    on, out_on = TI._scout(cli, monkeypatch, don, copy.deepcopy(rs), T - 600)
    assert on.startswith(off) and on != off and on[len(off):].startswith("\n## Predictive research section (flag on, research only)")
    dump_on = TI._lab_dump(don / "lab.sqlite")
    assert dump_on == dump_off                                          # theses (score, fatal flags, status), watchlist, rejections
    for (r, f, _), th in zip(rows, sorted(dump_on["theses"], key=lambda x: [q[0]["mint"] for q in rows].index(x["mint"]))):
        assert th["score"] == int(r["score"] or 0) and th["status"] == r["status"]
    tail = on[len(off):]
    assert "FORECAST" not in tail.replace("FORECAST_", "") and ": ABSTAIN (" in tail
    assert (don / "st" / I.FILES["passes"]).exists() and not (don / "data" / "private").exists()
    assert hashlib.sha256(REAL_EXPORT.read_bytes()).hexdigest() == before

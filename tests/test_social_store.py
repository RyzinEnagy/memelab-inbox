"""Phase 01 (social intelligence persistence): schema, migrations, rollback, CRUD and a fixture round trip.

Every test uses a temp database and a fixed clock. Nothing here writes into tracked paths or touches the network.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from memelab import db
from memelab.social import private, schema, store

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "social" / "roundtrip_01.json"
T0 = 1791590400.0  # 2026-10-10T00:00:00Z, fixed clock
LEGACY_CHECK = ["watchlist", "theses", "entries", "rejections", "market_snapshots", "pool_snapshots",
                "social_snapshots", "holders", "liquidity_quotes", "price_levels", "wallet_clusters"]


@pytest.fixture()
def priv(tmp_path, monkeypatch):
    p = tmp_path / "private" / "p.sqlite"
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(p))
    return p


@pytest.fixture()
def dbpath(tmp_path, priv):
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def _tables(con):
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _fingerprint(con, table, cols=None):
    cols = cols or [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    h = hashlib.sha256()
    n = 0
    for r in con.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY rowid"):
        h.update(repr(tuple(r)).encode())
        n += 1
    return n, h.hexdigest()


def _legacy_fp(con, tables):
    return {t: _fingerprint(con, t) for t in tables}


# ---------- schema and migrations ----------

def test_empty_db_init_and_repeat(dbpath):
    with db.connect(dbpath) as con:
        assert set(schema.SOCIAL_TABLES) <= _tables(con)
        assert schema.current_version(con) == 1
    db.init_db(dbpath)  # second run is a no-op
    with db.connect(dbpath) as con:
        assert con.execute("SELECT COUNT(*) FROM social_schema_migrations").fetchone()[0] == 1
        assert schema.migrate(con) == []


def _synthetic_legacy(path):
    """A database with only the original core schema and a few rows, like data/memelab.sqlite before later phases."""
    con = sqlite3.connect(path)
    con.executescript(db.SCHEMA)
    con.execute("INSERT INTO tokens(mint,first_seen_at,last_seen_at,symbol) VALUES ('Mint1111111111111111111111111111111',1,2,'AAA')")
    con.execute("INSERT INTO watchlist(mint,added_at,status,notes) VALUES ('Mint1111111111111111111111111111111',1,'WATCH','n')")
    con.execute("INSERT INTO theses(mint,created_at,thesis_text,score) VALUES ('Mint1111111111111111111111111111111',1,'t',50)")
    con.execute("INSERT INTO rejections(mint,rejected_at,stage,why_failed) VALUES ('Mint2',1,'s2','liq')")
    con.execute("INSERT INTO social_snapshots(mint,observed_at,source,metric,value) VALUES ('Mint1111111111111111111111111111111',1,'jup','holder_chg_1h',3)")
    con.execute("INSERT INTO market_snapshots(mint,observed_at,source,price_usd) VALUES ('Mint1111111111111111111111111111111',1,'jup',0.1)")
    con.commit()
    con.close()


def _migration_preserves_legacy(path):
    con = sqlite3.connect(path)
    before_tables = _tables(con)
    fp = _legacy_fp(con, before_tables)
    schema_sql = dict(con.execute("SELECT name, sql FROM sqlite_master"))
    assert schema.migrate(con) == [1]
    assert _legacy_fp(con, before_tables) == fp, "social migration changed a legacy table"
    assert all(dict(con.execute("SELECT name, sql FROM sqlite_master")).get(k) == v for k, v in schema_sql.items())
    assert set(schema.SOCIAL_TABLES) <= _tables(con)
    assert schema.migrate(con) == []  # idempotent
    assert schema.rollback(con, 0) == [1]
    assert not (set(schema.SOCIAL_TABLES) & _tables(con))
    assert _legacy_fp(con, before_tables) == fp, "rollback changed a legacy table"
    assert schema.migrate(con) == [1]  # re-applies cleanly after rollback
    con.close()
    return fp


def test_migration_on_synthetic_legacy_db(tmp_path):
    p = tmp_path / "legacy.sqlite"
    _synthetic_legacy(p)
    fp = _migration_preserves_legacy(p)
    assert fp["watchlist"][0] == 1 and fp["theses"][0] == 1 and fp["rejections"][0] == 1


def test_migration_on_copy_of_tracked_db(tmp_path, priv):
    src = ROOT / "data" / "memelab.sqlite"
    if not src.exists():
        pytest.skip("tracked database not present in this checkout")
    copy = schema.backup_db(src, tmp_path / "copy.sqlite")
    _migration_preserves_legacy(copy)
    # full init_db on the copy: earlier modules' migrations may add columns to tokens, but the row data of
    # watchlist, theses, rejections and the snapshot tables must be untouched
    con = sqlite3.connect(copy)
    have = [t for t in LEGACY_CHECK if t in _tables(con)]
    before = _legacy_fp(con, have)
    token_cols = [r[1] for r in con.execute("PRAGMA table_info(tokens)")]
    tok = _fingerprint(con, "tokens", token_cols)
    con.close()
    db.init_db(copy)
    con = sqlite3.connect(copy)
    assert _legacy_fp(con, have) == before
    assert _fingerprint(con, "tokens", token_cols) == tok
    assert schema.current_version(con) == 1
    con.close()


def test_failed_migration_leaves_db_unchanged(tmp_path):
    p = tmp_path / "f.sqlite"
    con = sqlite3.connect(p)
    schema.migrate(con)
    bad = schema.MIGRATIONS + [(2, "broken", "CREATE TABLE social_half(x INTEGER);\nINSERT INTO no_such_table VALUES (1);", "DROP TABLE IF EXISTS social_half;")]
    with pytest.raises(sqlite3.OperationalError):
        schema.migrate(con, migrations=bad)
    assert schema.current_version(con) == 1
    assert "social_half" not in _tables(con)
    con.close()


def test_changed_applied_migration_is_refused(tmp_path):
    con = sqlite3.connect(tmp_path / "c.sqlite")
    schema.migrate(con)
    v, name, up, down = schema.MIGRATIONS[0]
    with pytest.raises(RuntimeError):
        schema.migrate(con, migrations=[(v, name, up + "\n-- edited", down)])
    con.close()


def test_backup_rollback_and_recovery(dbpath, tmp_path):
    with db.connect(dbpath) as con:
        acc = store.upsert_account(con, "x", handle="someone", now=T0)
    bak = schema.backup_db(dbpath, tmp_path / "private" / "backups" / "b.sqlite")
    with db.connect(dbpath) as con:
        schema.rollback(con, 0)
        assert "social_accounts" not in _tables(con)
    bak.replace(dbpath)  # recovery = restore the backup file
    for suffix in ("-wal", "-shm"):
        Path(str(dbpath) + suffix).unlink(missing_ok=True)
    with db.connect(dbpath) as con:
        assert store.get_account(con, acc)["handle"] == "someone"
        assert schema.current_version(con) == 1


# ---------- fixture round trip through real persistence ----------

def _load_fixture(con, fx, now):
    av = fx["analysis_version"]
    store.register_analysis_version(con, av["version"], av["component"], av["description"], now=now)
    for a in fx["accounts"]:
        store.upsert_account(con, **a, now=now)
    tr = fx["trader"]
    store.upsert_trader(con, tr["trader_id"], tr["label"], added_reason=tr["added_reason"], now=now)
    out = []
    for o in fx["observations"]:
        o = dict(o)
        claim = o.pop("claim")
        acc = o.pop("account")
        res = store.record_observation(con, account_id=acc, analysis_version=av["version"], now=now, **o)
        ref = store.upsert_token_ref(con, chain=claim.get("chain"), contract=claim.get("contract"),
                                     symbol=claim.get("symbol"), now=now)
        c = store.add_claim(con, claim_type=claim["claim_type"], direction=claim["direction"], item_key=res["item_key"],
                            account_id=acc, token_ref_id=ref, claimed_at=o.get("published_at"),
                            analysis_version=av["version"], summary=o["summary"], observation_id=res["id"], now=now)
        out.append((res, ref, c))
    store.link_trader_account(con, tr["trader_id"], "x:id:1000000001", "SELF_DECLARED", "FACT", "HIGH",
                              observation_id=out[0][0]["id"], now=now)
    w = fx["wallet_claim"]
    wa = store.assert_wallet(con, subject_type="TRADER", subject_id=tr["trader_id"], observation_id=out[0][0]["id"],
                             asserted_at=now, now=now, **w)
    return out, wa


def _counts(con):
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in schema.SOCIAL_TABLES}


def test_fixture_round_trip_and_idempotency(dbpath, priv):
    fx = json.loads(FIXTURE.read_text())
    with db.connect(dbpath) as con:
        out, wa = _load_fixture(con, fx, T0)
        first = _counts(con)
    with db.connect(dbpath) as con:
        out2, wa2 = _load_fixture(con, fx, T0 + 60)  # repeated ingestion of the same batch
        assert _counts(con) == first
        assert [o[0]["created"] for o in out2] == [False, False] and wa2["created"] is False
        assert [o[0]["id"] for o in out2] == [o[0]["id"] for o in out]

    with db.connect(dbpath) as con:
        assert first["social_accounts"] == 2 and first["social_items"] == 2 and first["social_observations"] == 2
        x = store.get_account(con, "x:id:1000000001")
        assert x["handle"] == "Example_Trader_A" and x["handle_normalized"] == "example_trader_a"
        assert x["identity_status"] == "UNVERIFIED"  # explicit default, not assumed VERIFIED
        tg_item = con.execute("SELECT * FROM social_items WHERE platform='telegram'").fetchone()
        assert tg_item["published_at"] is None and tg_item["published_at_basis"] == "UNKNOWN"
        x_item = con.execute("SELECT * FROM social_items WHERE platform='x'").fetchone()
        assert x_item["published_at"] == store.to_utc("2026-10-09T13:58:00Z") and x_item["published_at_basis"] == "PROVIDER"
        obs = store.observations_for(con, x_item["item_key"])[0]
        assert obs["retained_content"] == "SUMMARY" and obs["private_ref"] is None
        assert json.loads(obs["metrics_json"])["views"] == 5400
        assert obs["content_hash"] == store.text_hash(fx["observations"][0]["text"])
        # identity: contract vs ticker
        refs = {r["ref_key"]: r for r in con.execute("SELECT * FROM social_token_refs")}
        assert "ca:base:0x532f27101965dd16442e59d40670faf5ebb142e4" in refs and "ticker:BRETT" in refs
        assert refs["ticker:BRETT"]["contract"] is None and refs["ticker:BRETT"]["ref_kind"] == "TICKER_ONLY"
        # claims point at evidence
        links = con.execute("SELECT target_type, COUNT(*) FROM social_evidence_links GROUP BY target_type").fetchall()
        assert dict(links) == {"CLAIM": 2, "TRADER_ACCOUNT": 1, "WALLET_ATTRIBUTION": 1}
        claims = con.execute("SELECT * FROM social_claims ORDER BY id").fetchall()
        assert [c["evidence_status"] for c in claims] == ["INFERENCE", "INFERENCE"]
        assert claims[1]["claimed_at"] is None  # unknown publish time stays unknown

        # no source text anywhere in the public database
        texts = [o["text"] for o in fx["observations"]]
        for t in schema.SOCIAL_TABLES:
            for row in con.execute(f"SELECT * FROM {t}"):
                for v in tuple(row):
                    if isinstance(v, str):
                        assert not any(tx in v for tx in texts), f"source text leaked into {t}"
    assert not priv.exists()  # nothing asked for exact wording, so the private store was never created


# ---------- edge cases ----------

def test_missing_timestamps_and_naive_times(dbpath):
    with db.connect(dbpath) as con:
        a = store.record_observation(con, platform="x", provider_item_id="9", access_mode="manual", collector="t",
                                     observed_at=None, published_at=None, now=T0)
        b = store.record_observation(con, platform="x", provider_item_id="9", access_mode="manual", collector="t",
                                     observed_at=None, published_at=None, now=T0 + 5)
        assert a["created"] and not b["created"] and a["id"] == b["id"]
        row = con.execute("SELECT * FROM social_observations WHERE id=?", (a["id"],)).fetchone()
        assert row["observed_at"] is None and row["observed_at_basis"] == "UNKNOWN" and row["ingested_at"] == T0
        with pytest.raises(ValueError):
            store.to_utc("2026-10-09T13:58:00")  # naive: zone unknown
        assert store.to_utc(1791590400000) == T0  # milliseconds accepted
        assert store.to_utc("2026-10-09T20:00:00-04:00") == store.to_utc("2026-10-10T00:00:00Z") == T0


def test_duplicate_provider_ids(dbpath):
    with db.connect(dbpath) as con:
        kw = dict(platform="x", provider_item_id="42", access_mode="fixture", collector="t", observed_at=T0)
        a = store.record_observation(con, text="first wording", published_at=T0 - 100, now=T0, **kw)
        b = store.record_observation(con, text="first wording", published_at=T0 - 100, now=T0, **kw)
        assert a["id"] == b["id"] and not b["created"]
        c = store.record_observation(con, text="edited wording", published_at=T0 - 100, now=T0, **kw)
        assert c["created"] and c["item_key"] == a["item_key"]  # same item, new sighting with new content hash
        d = store.record_observation(con, text="edited wording", published_at=T0 - 50, now=T0 + 1,
                                     **{**kw, "observed_at": T0 + 60})
        assert d["conflicts"] and "published_at" in d["conflicts"][0]
        assert con.execute("SELECT COUNT(*) FROM social_items").fetchone()[0] == 1
        assert con.execute("SELECT published_at FROM social_items").fetchone()[0] == T0 - 100  # first value kept
        hashes = [r["content_hash"] for r in store.observations_for(con, a["item_key"])]
        assert len(hashes) == 3 and len(set(hashes)) == 2
        # a provider id cannot be inserted twice as two items
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO social_items(item_key,platform,provider_item_id,first_ingested_at) VALUES ('x:other','x','42',1)")


def test_conflicting_claims_are_both_kept(dbpath):
    with db.connect(dbpath) as con:
        store.register_analysis_version(con, "v1", "extractor", now=T0)
        store.register_analysis_version(con, "v2", "extractor", now=T0)
        ref = store.upsert_token_ref(con, chain="solana", contract="FixtureMint1111111111111111111111111111111", now=T0)
        a1 = store.upsert_account(con, "x", handle="bull", now=T0)
        a2 = store.upsert_account(con, "x", handle="bear", now=T0)
        long_ = store.add_claim(con, claim_type="CALL", direction="LONG", account_id=a1, token_ref_id=ref, analysis_version="v1", now=T0)
        short = store.add_claim(con, claim_type="CALL", direction="SHORT", account_id=a2, token_ref_id=ref, analysis_version="v1", now=T0)
        store.relate_claims(con, short["id"], long_["id"], "CONTRADICTS", now=T0)
        store.relate_claims(con, short["id"], long_["id"], "CONTRADICTS", now=T0 + 1)  # idempotent
        assert store.conflicting_claims(con, ref) == [(long_["id"], short["id"])]
        assert con.execute("SELECT COUNT(*) FROM social_claim_relations").fetchone()[0] == 1
        # reprocessing under a new analysis version adds a row and keeps the old one
        again = store.add_claim(con, claim_type="CALL", direction="LONG", account_id=a1, token_ref_id=ref, analysis_version="v2", now=T0)
        assert again["created"] and again["id"] != long_["id"]
        assert con.execute("SELECT COUNT(*) FROM social_claims").fetchone()[0] == 3
        store.set_claim_status(con, long_["id"], "CONTRADICTED", now=T0 + 2)
        assert con.execute("SELECT claim_status FROM social_claims WHERE id=?", (long_["id"],)).fetchone()[0] == "CONTRADICTED"
        with pytest.raises(ValueError):
            store.add_claim(con, claim_type="CALL", account_id=a1, analysis_version="not-registered", now=T0)


def test_ticker_is_not_a_token_id(dbpath):
    with db.connect(dbpath) as con:
        r1 = store.upsert_token_ref(con, chain="base", contract="0x532F27101965DD16442E59D40670FAF5EBB142E4", now=T0)
        r2 = store.upsert_token_ref(con, chain="base", contract="0x532f27101965dd16442e59d40670faf5ebb142e4", now=T0)
        assert r1 == r2  # EVM case folded to one identity
        t1 = store.upsert_token_ref(con, symbol="$brett", now=T0)
        assert t1 != r1
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO social_token_refs(ref_key,ref_kind,chain,contract,first_seen_at) VALUES ('ticker:X','TICKER_ONLY','base','0xabc',1)")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO social_token_refs(ref_key,ref_kind,chain,contract,first_seen_at) VALUES ('ca:x','CONTRACT_ADDRESS',NULL,NULL,1)")
        with pytest.raises(ValueError):
            store.upsert_token_ref(con, chain="base", contract="BRETT", now=T0)
        with pytest.raises(ValueError):
            store.upsert_token_ref(con, chain="solana", contract="0x532f27101965dd16442e59d40670faf5ebb142e4", now=T0)


def test_social_id_is_not_a_wallet_and_retractions_append(dbpath):
    with db.connect(dbpath) as con:
        acc = store.upsert_account(con, "x", handle="claimer", provider_user_id="77", now=T0)
        w = "FixtureWa11et11111111111111111111111111111"
        with pytest.raises(ValueError):
            store.assert_wallet(con, subject_type="ACCOUNT", subject_id=acc, chain="solana", wallet_address="claimer",
                                assertion="SELF_CLAIMED", evidence_status="FACT", basis="b", now=T0)
        with pytest.raises(ValueError):
            store.assert_wallet(con, subject_type="TRADER", subject_id="nobody", chain="solana", wallet_address=w,
                                assertion="SELF_CLAIMED", evidence_status="FACT", basis="b", now=T0)
        store.assert_wallet(con, subject_type="ACCOUNT", subject_id=acc, chain="solana", wallet_address=w,
                            assertion="SELF_CLAIMED", evidence_status="FACT", confidence="LOW", basis="bio link", asserted_at=T0, now=T0)
        store.assert_wallet(con, subject_type="ACCOUNT", subject_id=acc, chain="solana", wallet_address=w,
                            assertion="RETRACTED", evidence_status="FACT", basis="account removed the address", asserted_at=T0 + 3600, now=T0)
        view = store.current_wallet_view(con, "solana", w)
        assert len(view) == 1 and view[0]["assertion"] == "RETRACTED"
        assert con.execute("SELECT COUNT(*) FROM social_wallet_attributions").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM wallets").fetchone()[0] == 0  # legacy wallets table untouched


def test_account_handle_change_and_late_provider_id(dbpath):
    with db.connect(dbpath) as con:
        a = store.upsert_account(con, "x", handle="@OldName", now=T0)
        assert a == "x:handle:oldname"
        b = store.upsert_account(con, "x", handle="oldname", provider_user_id="555", now=T0 + 10)
        assert b == a and store.get_account(con, a)["provider_user_id"] == "555"  # id learned later, key stays stable
        c = store.upsert_account(con, "x", handle="NewName", provider_user_id="555", now=T0 + 20)
        assert c == a and store.get_account(con, a)["handle"] == "NewName"
        hist = [r[0] for r in con.execute("SELECT handle_normalized FROM social_account_handles WHERE account_id=? ORDER BY first_seen_at", (a,))]
        assert hist == ["oldname", "newname"]
        # the old handle reused by a different provider id is a different account
        d = store.upsert_account(con, "x", handle="oldname", provider_user_id="999", now=T0 + 30)
        assert d == "x:id:999"
        with pytest.raises(ValueError):
            store.upsert_account(con, "x", now=T0)


def test_private_store_and_summary_guard(dbpath, priv):
    text = "this exact wording is kept only in the private store for evidence of the claim"
    with db.connect(dbpath) as con:
        with pytest.raises(ValueError):
            store.record_observation(con, platform="x", provider_item_id="1", access_mode="fixture", collector="t",
                                     observed_at=T0, text=text,
                                     summary="Says this exact wording is kept only in the private store for evidence", now=T0)
        with pytest.raises(ValueError):
            store.record_observation(con, platform="x", provider_item_id="1", access_mode="fixture", collector="t",
                                     observed_at=T0, metrics={"bio": "text"}, now=T0)
        r = store.record_observation(con, platform="x", provider_item_id="1", access_mode="fixture", collector="t",
                                     observed_at=T0, text=text, summary="Post describes an evidence policy.",
                                     keep_exact_reason="evidence for claim test", now=T0, private_path=priv)
        row = con.execute("SELECT * FROM social_observations WHERE id=?", (r["id"],)).fetchone()
        assert row["retained_content"] == "SUMMARY_AND_PRIVATE" and row["private_ref"].startswith("sha256:")
        assert text not in json.dumps([tuple(x) for x in con.execute("SELECT * FROM social_observations")])
    got = private.get(row["private_ref"], path=priv)
    assert got["exact_text"] == text and got["retain_until"] == T0 + private.DEFAULT_RETENTION_DAYS * 86400
    assert private.purge_expired(now=T0 + 31 * 86400, path=priv) == 1
    assert private.get(row["private_ref"], path=priv) is None
    gi = (ROOT / ".gitignore").read_text().splitlines()
    assert "data/private/" in gi and "*.sqlite*" in gi


def test_connector_health_and_coverage(dbpath):
    with db.connect(dbpath) as con:
        assert store.record_connector_health(con, "x_chrome", "OK", checked_at=T0, items_seen=20)
        assert not store.record_connector_health(con, "x_chrome", "OK", checked_at=T0, items_seen=20)
        store.record_connector_health(con, "x_chrome", "RATE_LIMITED", checked_at=T0 + 60, error="429")
        assert store.latest_connector_health(con, "x_chrome")["status"] == "RATE_LIMITED"
        assert store.record_coverage(con, run_id="r1", connector="x_chrome", platform="x", scope="@a", status="COVERED",
                                     window_start=T0 - 3600, window_end=T0, checked_at=T0, items_seen=5)
        assert not store.record_coverage(con, run_id="r1", connector="x_chrome", platform="x", scope="@a", status="COVERED",
                                         checked_at=T0, items_seen=5)
        with pytest.raises(ValueError):
            store.record_coverage(con, run_id="r1", connector="x_chrome", platform="x", scope="@b", status="GAP", checked_at=T0)
        store.record_coverage(con, run_id="r1", connector="x_chrome", platform="x", scope="@b", status="GAP",
                              gap_reason="rate limited", checked_at=T0)
        row = con.execute("SELECT * FROM social_coverage WHERE scope='@b'").fetchone()
        assert row["window_start"] is None and row["status"] == "GAP"

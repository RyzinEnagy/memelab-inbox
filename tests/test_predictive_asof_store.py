"""Predictive intelligence Phase 05: the point-in-time evidence store (memelab/predictive/store.py, sources.py).

Migrations are additive and reversible (P33); every data table is append-only; identity is chain plus the exact address
(P01, P02, PI-D-022); vendor reads keep their raw hash and retrieval time apart from availability (P04); ingestion is
idempotent; revisions, late appearances and vanished candles never rewrite history (P07); decision records follow
decisions.py and carry a write-time trace (PI-D-011 rule 3). No network (socket use raises), temp files only, fixed clock.
"""
import types
import json
import socket
import sqlite3
from pathlib import Path

import pytest

from memelab import db, state
from memelab.predictive import decisions as D
from memelab.predictive import runtime as R
from memelab.predictive import sources as SRC
from memelab.predictive import store as S

FIX = Path(__file__).resolve().parent / "fixtures" / "predictive"
H = types.ModuleType("asof_helpers")          # loaded without writing bytecode next to the fixtures
exec(compile((FIX / "asof_helpers.py").read_text(), str(FIX / "asof_helpers.py"), "exec"), H.__dict__)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 05 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


@pytest.fixture
def con(tmp_path):
    c = S.connect(tmp_path / "store.sqlite")
    yield c
    c.close()


def _schema(c):
    return sorted(tuple(r) for r in c.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


# ---------------------------------------------------------------- placement, migration, rollback (A3, A4, P33)
def test_store_refuses_the_tracked_lab_database(tmp_path, monkeypatch):
    with pytest.raises(S.StoreError):
        S.connect(Path(db.DATA_DIR) / "memelab.sqlite")
    p = tmp_path / "lab.sqlite"
    monkeypatch.setattr(db, "DB_PATH", p)
    with pytest.raises(S.StoreError):
        S.connect(p)
    assert not p.exists()


def test_init_db_creates_no_predictive_table(tmp_path):
    p = tmp_path / "lab.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    assert not [r for r in c.execute("SELECT name FROM sqlite_master WHERE name LIKE 'predictive%'")]


def test_migrate_then_rollback_leaves_a_full_lab_database_identical(tmp_path):
    p = tmp_path / "lab.sqlite"
    db.init_db(p)                                    # lab, catalyst, chains, launch and social tables
    c = sqlite3.connect(p)
    c.execute("INSERT INTO tokens(mint, chain, first_seen_at, last_seen_at) VALUES (?, 'solana', 1, 2)", (H.MINT_A,))
    c.commit()
    before = _schema(c)
    rows_before = c.execute("SELECT * FROM tokens").fetchall()
    assert S.migrate(c) == [1] and S.migrate(c) == []
    created = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")} - {t[1] for t in before}
    assert created == set(S.DATA_TABLES) | {"predictive_schema_migrations"}
    assert S.rollback(c) == [1]
    assert _schema(c) == before and c.execute("SELECT * FROM tokens").fetchall() == rows_before


def test_an_edited_applied_migration_is_refused(con):
    edited = [(1, "x", S.V1_UP + "\n-- edited", S.V1_DOWN)]
    with pytest.raises(S.StoreError):
        S.migrate(con, migrations=edited)


@pytest.mark.parametrize("table", S.DATA_TABLES)
def test_every_data_table_is_append_only(con, table):
    d1, d2, d3 = H.small_world(con)
    sparse = [H.candle(H.T0 + 86400 - 3000, c=0.4), H.candle(H.T0 + 3600, c=0.45)]
    S.ingest_gt_response(con, H.resp(H.POOL_B, int(d2), sparse, H.T0 + 35 * 86400), chain="solana", mint=H.MINT_B, pool=H.POOL_B,
                         now=H.T0 + 35 * 86400)
    from memelab.predictive import features as F
    F.build_snapshots(con, feature_version=F.FEATURE_VERSION, now=H.T0 + 40 * 86400)
    con.commit()
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    assert n > 0
    col = [r[1] for r in con.execute(f"PRAGMA table_info({table})")][1]
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute(f"UPDATE {table} SET {col}={col}")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute(f"DELETE FROM {table}")


# ---------------------------------------------------------------- identity (A5, P01, P02, PI-D-022)
def test_solana_identity_must_decode_to_32_bytes():
    assert S.check_address("solana", H.MINT_A) == H.MINT_A
    bad = "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"          # real export string: base58 but 31 bytes
    assert len(S.b58decode(bad)) == 31
    for x in (bad, H.MINT_A + "1", " " + H.MINT_A, H.MINT_A[:-1] + "0", "", None, 7):
        with pytest.raises(S.StoreError):
            S.check_address("solana", x)
    with pytest.raises(S.StoreError):
        S.check_address("SOL", H.MINT_A)
    assert S.check_address("base", "0x" + "ab" * 20)
    assert S.check_address("base", "0x" + "ab" * 32, "pool")           # a Uniswap v4 pool id
    with pytest.raises(S.StoreError):
        S.check_address("base", "0x" + "ab" * 32)                       # never a token address


def test_letter_case_variants_are_two_identities(con):
    upper = H.MINT_A[:5] + H.MINT_A[5].swapcase() + H.MINT_A[6:]
    assert upper != H.MINT_A and len(S.b58decode(upper)) == 32
    t = H.T0 + 86400
    e = H.export("c1", t, [H.thesis(H.MINT_A, t - 100, price=1.0), H.thesis(upper, t - 100, price=9.0)],
                 [H.token(H.MINT_A, pool=H.POOL_A), H.token(upper, pool=H.POOL_B)])
    S.ingest_exports(con, [e], now=t + 10)
    rows = con.execute("SELECT mint, pool_address FROM predictive_decisions WHERE mint=?", (H.MINT_A,)).fetchall()
    assert [tuple(r) for r in rows] == [(H.MINT_A, H.POOL_A)]


def test_a_pool_belongs_to_one_mint(con):
    r = H.resp(H.POOL_A, H.T0 + 3600, [H.candle(H.T0)], H.T0 + 86400)
    S.ingest_gt_response(con, r, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=H.T0 + 86400)
    with pytest.raises(S.StoreError, match="one mint"):
        S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 7200, [H.candle(H.T0 + 600)], H.T0 + 86500), chain="solana",
                             mint=H.MINT_B, pool=H.POOL_A, now=H.T0 + 86500)
    decs = [{"chain": "solana", "mint": m, "pool_address": H.POOL_A, "decision_time": H.T0 + 86400} for m in (H.MINT_A, H.MINT_B)]
    with pytest.raises(SRC.SourceError, match="one mint"):
        SRC.plan_backfill(decs)


# ---------------------------------------------------------------- decision records (A6, PI-D-011, PI-D-015, PI-D-021)
def test_decision_records_follow_decisions_py_and_reimport_adds_nothing(con):
    H.small_world(con)
    rows = S.iter_rows(con, "SELECT * FROM predictive_decisions ORDER BY decision_time, mint")
    assert H.MINT_B < H.MINT_A
    assert [(r["mint"], r["status"]) for r in rows] == [(H.MINT_A, "WATCH"), (H.MINT_B, "WATCH"), (H.MINT_A, "REJECTED"),
                                                        (H.MINT_A, "WATCH")]
    for r in rows:
        assert r["decision_time_basis"] == "EXPORT_COMMIT"
        assert r["decision_time"] >= r["created_at"] and r["decision_time"] >= r["token_first_seen_at"]
        assert r["decision_time"] != r["created_at"]
        assert D.row_sha256(json.loads(r["row_json"])) == r["row_sha256"]
        assert r["export_commit"] in ("c1", "c2", "c3") and r["recorded_at"] > 0
    n = con.execute("SELECT COUNT(*) FROM predictive_decisions").fetchone()[0]
    r = S.ingest_exports(con, H.world_exports(), now=1.0)
    assert r["decisions_added"] == 0 and r["responses_added"] == 0
    assert con.execute("SELECT COUNT(*) FROM predictive_decisions").fetchone()[0] == n
    with pytest.raises(S.StoreError, match="full history"):     # a partial history would mint false decisions
        S.ingest_exports(con, H.world_exports()[1:], now=1.0)


def test_a_decision_time_basis_other_than_export_or_capture_is_refused(con, monkeypatch):
    real = D.decisions

    def bad(c):
        return [dict(e, decision_time_basis="CREATED_AT") for e in real(c)]
    monkeypatch.setattr(D, "decisions", bad)
    t = H.T0 + 86400
    with pytest.raises(S.StoreError, match="PI-D-011"):
        S.ingest_exports(con, [H.export("c1", t, [H.thesis(H.MINT_A, t - 100)], [H.token(H.MINT_A)])], now=t)
    with pytest.raises(sqlite3.IntegrityError):              # and the table itself refuses it
        con.execute("INSERT INTO predictive_decisions(decision_key, mint, row_sha256, created_at, decision_time, "
                    "decision_time_basis, row_first_visible, flags_json, rows_sharing_key, row_json, response_key, "
                    "ingest_version, schema_version, recorded_at) VALUES ('k', ?, 'r', 1, 2, 'CREATED_AT', 2, '[]', 1, '{}', "
                    "'x', 'v', 'v', 3)", (H.MINT_A,))


def test_pid011_skeptic_check_on_real_export_rows(tmp_path, monkeypatch, con):
    """Phase 00 skeptic section 2 as SQL on a real export imported with state.import_: the token rows were written after the
    theses' created_at (the write lag), so created_at is not a decision time; every stored decision is at or after both."""
    fx = json.loads((FIX / "asof_pid011_export.json").read_text())
    p = tmp_path / "lab.sqlite"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    src = tmp_path / "export.json"
    src.write_text(json.dumps(fx["doc"]))
    state.import_(str(src))
    lab = sqlite3.connect(p)
    lagged = lab.execute("SELECT COUNT(*) FROM tokens k JOIN (SELECT mint, MIN(created_at) c FROM theses GROUP BY mint) t "
                         "USING(mint) WHERE k.first_seen_at > t.c").fetchone()[0]
    assert lagged == fx["expected_lagged_mints"] and lagged > 0
    ex = D.export_from_doc(fx["commit"], fx["commit_time"], fx["doc"])
    S.ingest_exports(con, [ex], now=fx["commit_time"] + 1)
    rows = S.iter_rows(con, "SELECT * FROM predictive_decisions")
    assert len(rows) == fx["expected_decisions"]
    for r in rows:
        assert r["decision_time"] == fx["commit_time"]
        assert r["decision_time"] >= r["created_at"]
        assert r["token_first_seen_at"] is not None and r["decision_time"] >= r["token_first_seen_at"]
    lag = [r for r in rows if r["token_first_seen_at"] > r["created_at"]]
    assert lag, "the fixture must show the write lag"


def test_time_units_are_checked(con):
    t = H.T0 + 86400
    for bad in ({"created": (t - 100) * 1000, "commit": t}, {"created": t + 50, "commit": t}):
        with pytest.raises(S.StoreError):
            S.ingest_exports(con, [H.export("c1", bad["commit"], [H.thesis(H.MINT_A, bad["created"])], [H.token(H.MINT_A)])], now=t)
    ms = [[int(H.T0 * 1000), 1.0, 1.01, 0.99, 1.0, 5.0], H.candle(H.T0 + 300)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 600, ms, H.T0 + 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["refused"] == 1 and r["kept"] == 1
    with pytest.raises(S.StoreError):
        S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 900, ms, (H.T0 + 86400) * 1000), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=1)
    assert S.epoch_seconds(H.T0, "t") == H.T0


def test_snapshot_ref_is_the_row_sha256_of_a_decision_record(con):
    H.small_world(con)
    r = con.execute("SELECT row_sha256 FROM predictive_decisions WHERE mint=? LIMIT 1", (H.MINT_A,)).fetchone()[0]
    assert S.snapshot_ref_ok(con, "solana", H.MINT_A, r) and S.snapshot_ref_ok(con, "solana", H.MINT_A, "sha256:" + r)
    assert not S.snapshot_ref_ok(con, "solana", H.MINT_B, r)
    assert not S.snapshot_ref_ok(con, "solana", H.MINT_A, "0" * 64)


def test_malformed_identities_in_an_export_are_refused_and_counted(con):
    t = H.T0 + 86400
    bad = "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"
    r = S.ingest_exports(con, [H.export("c1", t, [H.thesis(bad, t - 100), H.thesis(H.MINT_A, t - 100)],
                                        [H.token(bad), H.token(H.MINT_A)])], now=t)
    assert r["decisions_added"] == 1 and [x["mint"] for x in r["refused"]] == [bad]


# ---------------------------------------------------------------- vendor reads (A7, A8, P04, P07, PI-D-034)
def test_raw_read_is_kept_with_hash_and_retrieval_time_and_ingestion_is_idempotent(con):
    rows = [H.candle(H.T0 + 300 * i) for i in range(5)][::-1]
    r = H.resp(H.POOL_A, H.T0 + 1500, rows, H.T0 + 86400)
    a = S.ingest_gt_response(con, r, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1.0)
    b = S.ingest_gt_response(con, r, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=2.0)
    assert a["added"] == 5 and b["duplicate_read"] and b["added"] == 0
    assert S.table_counts(con)["predictive_raw_responses"] == 1 and S.table_counts(con)["predictive_candles"] == 5
    rr = S.responses(con, S.SOURCE_GT)[0]
    assert rr["retrieved_at"] == H.T0 + 86400 and rr["body_sha256"] == __import__("hashlib").sha256(r["body"]).hexdigest()
    assert S.stored_body(con, rr["response_key"]) == r["body"] and S.verify(con) == []
    c0 = S.iter_rows(con, "SELECT * FROM predictive_candles ORDER BY start_at")[0]
    assert c0["available_basis"] == "PROVIDER_LAG_RECONSTRUCTION" and c0["available_at"] == c0["end_at"] + 300
    assert c0["retrieved_at"] == H.T0 + 86400 and c0["published_at"] is None


def test_candles_ending_after_the_boundary_are_dropped(con):
    b = H.T0 + 1000                                   # unaligned: the vendor returns the candle that holds it
    rows = [H.candle(H.T0 + 900), H.candle(H.T0 + 600), H.candle(H.T0 + 300)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, b, rows, H.T0 + 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["dropped"] == 1 and r["kept"] == 2
    assert max(x[0] for x in con.execute("SELECT end_at FROM predictive_candles")) <= b


def test_malformed_and_unfinished_candles_are_refused(con):
    ra = H.T0 + 1000
    rows = [H.candle(H.T0, c=1.0, h=0.5), H.candle(H.T0 + 300, c=-1.0), H.candle(H.T0 + 600), H.candle(H.T0 + 900)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows, ra), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["refused"] == 3 and r["kept"] == 1          # high below close, negative price, a candle closing after the read


def test_a_live_read_is_available_at_the_read_when_that_is_earlier(con):
    start = H.T0
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, start + 300, [H.candle(start)], start + 310), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=1)
    c = S.iter_rows(con, "SELECT * FROM predictive_candles")[0]
    assert r["added"] == 1 and c["available_basis"] == "CAPTURE" and c["available_at"] == start + 310


def test_revision_is_a_new_version_available_from_its_read(con):
    rows1 = [H.candle(H.T0 + 300 * i, c=1.0) for i in range(4)][::-1]
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows1, H.T0 + 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    rows2 = [list(r) for r in rows1]
    rows2[1][4] = 1.05                               # the candle at T0 + 600 revised
    rows2[1][2] = 1.1
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows2, H.T0 + 3 * 86400), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=2)
    assert r["revisions"] == 1 and r["reads"] == 3 and r["added"] == 1
    vs = S.iter_rows(con, "SELECT * FROM predictive_candles WHERE start_at=? ORDER BY id", (H.T0 + 600,))
    assert [v["c"] for v in vs] == [1.0, 1.05]
    assert vs[1]["available_basis"] == "REVISION_FIRST_READ" and vs[1]["available_at"] == H.T0 + 3 * 86400
    assert vs[1]["revision_of"] == vs[0]["obs_key"] and vs[0]["available_at"] == H.T0 + 900 + 300
    assert vs[1]["revision_kind"] == "VALUES" and vs[0]["revision_kind"] is None
    assert S.table_counts(con)["predictive_candle_reads"] == 3
    rows3 = [list(r) for r in rows2]
    rows3[2][1] = 0.98                               # only the open of T0 + 300 differs: the vendor's window-dependent open
    rows3[2][3] = 0.97
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows3, H.T0 + 4 * 86400), chain="solana", mint=H.MINT_A,
                         pool=H.POOL_A, now=3)
    v3 = S.iter_rows(con, "SELECT * FROM predictive_candles WHERE start_at=? ORDER BY id", (H.T0 + 300,))
    assert [v["revision_kind"] for v in v3] == [None, "OPEN_WINDOW"]


def test_a_candle_that_appears_after_an_earlier_read_covered_it_is_a_late_backfill(con):
    rows1 = [H.candle(H.T0 + 900), H.candle(H.T0)]                       # nothing at T0 + 300 and T0 + 600
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows1, H.T0 + 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    rows2 = [H.candle(H.T0 + 900), H.candle(H.T0 + 600), H.candle(H.T0)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows2, H.T0 + 2 * 86400), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=2)
    c = S.iter_rows(con, "SELECT * FROM predictive_candles WHERE start_at=?", (H.T0 + 600,))[0]
    assert r["revisions"] == 1 and c["available_basis"] == "REVISION_FIRST_READ" and c["available_at"] == H.T0 + 2 * 86400
    assert c["revision_kind"] == "APPEARED"


def test_a_vanished_candle_is_a_tombstone_from_the_read_that_lacks_it(con):
    rows1 = [H.candle(H.T0 + 900), H.candle(H.T0 + 600), H.candle(H.T0)]
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows1, H.T0 + 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    rows2 = [H.candle(H.T0 + 900), H.candle(H.T0)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 1200, rows2, H.T0 + 2 * 86400), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=2)
    vs = S.iter_rows(con, "SELECT * FROM predictive_candles WHERE start_at=? ORDER BY id", (H.T0 + 600,))
    assert r["vanished"] == 1 and [v["vanished"] for v in vs] == [0, 1] and vs[1]["available_at"] == H.T0 + 2 * 86400
    assert vs[1]["revision_kind"] == "VANISHED"


def test_a_read_that_prices_another_token_is_refused(con):
    """Phase 05 finding on the real backfill: without token=<mint> the vendor prices the pool's base token, and in one pool
    of the sample the mint is the quote token. Such a read keeps its raw row but gives no candle."""
    rows = [H.candle(H.T0)]
    quote_side = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86400, token=False)
    quote_side["body"] = H.gt_body(rows, base=H.MINT_B, quote=H.MINT_A)
    r = S.ingest_gt_response(con, quote_side, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["identity_check"] == "MINT_IS_QUOTE" and r["added"] == 0 and r["refused"] == 1
    other = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86401, token=False)
    other["body"] = H.gt_body(rows, base=H.MINT_B, quote=H.MINT_B)
    assert S.ingest_gt_response(con, other, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)["identity_check"] == "MINT_NOT_IN_POOL"
    nometa = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86402)
    nometa["body"] = json.dumps({"data": {"attributes": {"ohlcv_list": rows}}}).encode()
    assert S.ingest_gt_response(con, nometa, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)["identity_check"] == "NO_META"
    assert S.table_counts(con)["predictive_candles"] == 0
    inverted = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86403)          # token=<mint>, but the body keeps the other token as
    inverted["body"] = H.gt_body(rows, base=H.MINT_B, quote=H.MINT_A)    # base: refused (CX-S06, PI-D-045); real token reads
    r = S.ingest_gt_response(con, inverted, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)   # show the mint as base
    assert r["identity_check"] == "TOKEN_PARAM_NOT_BASE" and r["added"] == 0
    oriented = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86404)
    oriented["body"] = H.gt_body(rows, base=H.MINT_A, quote=H.MINT_B)
    r = S.ingest_gt_response(con, oriented, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["identity_check"] == "OK_TOKEN_PARAM" and r["added"] == 1
    assert "token=" + H.MINT_A in SRC.gt_url(H.POOL_A, 1, token=H.MINT_A)


def test_reads_of_a_pool_are_ingested_in_retrieval_order(con):
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 600, [H.candle(H.T0)], H.T0 + 86400), chain="solana", mint=H.MINT_A,
                         pool=H.POOL_A, now=1)
    with pytest.raises(S.StoreError, match="retrieval order"):
        S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 900, [H.candle(H.T0)], H.T0 + 100), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=2)


def test_verify_catches_a_body_that_does_not_match_its_hash(tmp_path):
    p = tmp_path / "s.sqlite"
    c = S.connect(p)
    S.ingest_gt_response(c, H.resp(H.POOL_A, H.T0 + 600, [H.candle(H.T0)], H.T0 + 86400), chain="solana", mint=H.MINT_A,
                         pool=H.POOL_A, now=1)
    c.commit()
    c.execute("DROP TRIGGER predictive_raw_responses_no_update")      # a tamper only possible by dropping the guard
    c.execute("UPDATE predictive_raw_responses SET body_gzip=?", (S.gz(b"{}"),))
    assert any("does not match" in x for x in S.verify(c))


# ---------------------------------------------------------------- backfill plan and fetch (A14, A15, A16, A17)
def _dec(mint, pool, t, chain="solana"):
    return {"chain": chain, "mint": mint, "pool_address": pool, "decision_time": t}


def test_plan_fetches_development_decisions_only_and_never_reaches_the_holdout_window():
    h0 = SRC.holdout_start()
    decs = [_dec(H.MINT_A, H.POOL_A, h0 - 10 * 86400), _dec(H.MINT_A, H.POOL_A, h0 - 3 * 86400),
            _dec(H.MINT_A, H.POOL_A, h0 - 3600),             # purged: its 6 h label matures after the holdout start
            _dec(H.MINT_A, H.POOL_A, h0 + 600),              # holdout
            _dec(H.MINT_B, H.POOL_B, h0 + 7200),             # holdout only: no series
            _dec(H.MINT_B, None, h0 - 5 * 86400), _dec("0x" + "ab" * 20, "0x" + "cd" * 20, h0 - 5 * 86400, chain="base")]
    plan = SRC.plan_backfill(decs)
    assert [(p["pool"], p["decisions"]) for p in plan] == [(H.POOL_A, 2)]
    assert plan[0]["boundary"] == int(h0 - 3 * 86400) <= h0 - 3600
    assert [SRC.fetch_scope(d) for d in decs] == ["DEVELOPMENT", "DEVELOPMENT", "NOT_FETCHED_SEALED", "NOT_FETCHED_SEALED",
                                                  "NOT_FETCHED_SEALED", "NO_POOL_AT_DECISION", "OUT_OF_SCOPE_CHAIN"]
    with pytest.raises(SRC.SourceError):
        SRC.check_plan([dict(plan[0], boundary=int(h0 - 1800), last_decision=h0 - 1800)])


def test_the_holdout_pad_holds_even_if_the_development_rule_were_wrong(monkeypatch):
    h0 = SRC.holdout_start()
    monkeypatch.setattr(SRC, "development_period", lambda t: True)       # a broken development rule
    with pytest.raises(SRC.SourceError, match="holdout contact window"):
        SRC.plan_backfill([_dec(H.MINT_A, H.POOL_A, h0 - 1800)])
    assert SRC.plan_backfill([_dec(H.MINT_A, H.POOL_A, h0 - 3600)])[0]["boundary"] == int(h0 - 3600)


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_fetch_pages_back_paces_and_keeps_every_response(con):
    clk = Clock(H.T0 + 30 * 86400)
    b = int(H.T0 + 5 * 86400)
    got = []

    def http(url):
        before = int(url.split("before_timestamp=")[1].split("&")[0])
        got.append((clk.t, before))
        n = 1000 if before == b else 10
        start = before - before % 300
        return 200, H.gt_body([H.candle(start - 300 * i) for i in range(n)], base=H.MINT_A)
    g = R.CallGuard(max_per_min=6, clock=clk, sleep=clk.sleep)
    p = {"series_id": "s", "chain": "solana", "mint": H.MINT_A, "pool": H.POOL_A, "boundary": b, "need_from": H.T0,
         "decisions": 1, "first_decision": b, "last_decision": b}
    res = SRC.fetch_series(p, http_get=http, guard=g, clock=clk, sleep=clk.sleep,
                           on_response=lambda r: S.ingest_gt_response(con, r, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1))
    assert res["status"] == "OK" and res["calls"] == 2 and len(res["response_keys"]) == 2
    assert got[1][0] - got[0][0] >= 10 and got[1][1] < got[0][1]
    assert S.table_counts(con)["predictive_candles"] == 1000 - 1 + 10 - 1     # each page's boundary candle dropped


def test_vendor_outage_opens_the_breaker_and_is_recorded(con):
    clk = Clock(H.T0 + 30 * 86400)
    g = R.CallGuard(max_per_min=6, clock=clk, sleep=clk.sleep)
    p = {"series_id": "s", "chain": "solana", "mint": H.MINT_A, "pool": H.POOL_A, "boundary": int(H.T0 + 86400),
         "need_from": H.T0, "decisions": 1, "first_decision": H.T0 + 86400, "last_decision": H.T0 + 86400}
    seen = []
    res = SRC.fetch_series(p, http_get=lambda u: (503, b"down"), guard=g, clock=clk, sleep=clk.sleep,
                           on_response=lambda r: seen.append(r["http_status"]) or {})
    assert res["status"] == "READ_FAILED" and seen == [503]
    for _ in range(4):
        SRC.fetch_series(p, http_get=lambda u: (429, b"slow"), guard=g, clock=clk, sleep=clk.sleep, retries_429=0)
    res = SRC.fetch_series(p, http_get=lambda u: (200, H.gt_body([], base=H.MINT_A)), guard=g, clock=clk, sleep=clk.sleep)
    assert res["status"] == "CIRCUIT_OPEN" and res["calls"] == 0


def test_a_network_exception_is_a_read_failure_not_a_crash(con):
    clk = Clock(H.T0 + 30 * 86400)
    g = R.CallGuard(max_per_min=6, clock=clk, sleep=clk.sleep)
    p = {"series_id": "s", "chain": "solana", "mint": H.MINT_A, "pool": H.POOL_A, "boundary": int(H.T0 + 86400),
         "need_from": H.T0, "decisions": 1, "first_decision": H.T0 + 86400, "last_decision": H.T0 + 86400}

    def boom(url):
        raise ConnectionError("no route")
    res = SRC.fetch_series(p, http_get=boom, guard=g, clock=clk, sleep=clk.sleep)
    assert res["status"] == "READ_FAILED" and "NETWORK_UNAVAILABLE" in res["detail"]


def test_export_versions_read_git_first_parent_oldest_first(tmp_path):
    import subprocess
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda *a, **k: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, **k)
    run("init", "-q")
    run("config", "user.email", "t@example.invalid")
    run("config", "user.name", "t")
    (repo / "data" / "state").mkdir(parents=True)
    for i, t in enumerate((1000000000, 1000000600)):
        doc = {"_exported_at": t, "_tables": {"theses": [H.thesis(H.MINT_A, t - 50.0)], "tokens": [H.token(H.MINT_A)]}}
        (repo / "data" / "state" / "latest.json").write_text(json.dumps(doc))
        run("add", ".")
        run("commit", "-q", "-m", f"e{i}", env={"GIT_COMMITTER_DATE": f"{t} +0000", "GIT_AUTHOR_DATE": f"{t} +0000",
                                                "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    ex = SRC.export_versions(repo, "HEAD")
    assert [e["commit_time"] for e in ex] == [1000000000.0, 1000000600.0]
    assert all(len(e["blob"]) == 40 and len(e["body_sha256"]) == 64 and e["theses"] for e in ex)

# ---------------------------------------------------------------- repair pass (independent skeptic m1, m2, m3)
def _real_default_read():
    """The real archived default-side read of a quote-side pool from the frozen fixture (URL without a token parameter)."""
    import base64
    import gzip
    fx = json.loads((FIX / "asof_fixture.json").read_text())
    r = next(x for x in fx["reads"] if x["http_status"] == 200 and "token=" not in x["url"])
    body = gzip.decompress(base64.b64decode(r["body_gzip_b64"]))
    return r, body


def test_cx05_a_recorded_token_that_the_url_did_not_send_is_refused(con):
    """Skeptic counterexample CX-05: a default read (no token in the URL) recorded with params claiming token=<mint> was
    accepted as the mint's price. The token is now taken from the URL sent and a disagreeing record is refused."""
    r, body = _real_default_read()
    assert S.gt_identity(body, r["mint"], None) == "MINT_IS_QUOTE"
    forged = {"url": r["url"], "params": dict(r["params"], token=r["mint"]), "retrieved_at": r["retrieved_at"], "http_status": 200,
              "body": body, "boundary_at": r["boundary_at"], "timeframe": "minute", "aggregate": 5}
    with pytest.raises(S.StoreError, match="disagrees with the URL"):
        S.ingest_gt_response(con, forged, chain="solana", mint=r["mint"], pool=r["pool"], now=1)
    honest = dict(forged, params=dict(r["params"], token=None))
    out = S.ingest_gt_response(con, honest, chain="solana", mint=r["mint"], pool=r["pool"], now=1)
    assert out["identity_check"] == "MINT_IS_QUOTE" and out["added"] == 0
    assert S.table_counts(con)["predictive_candles"] == 0


def test_only_the_exact_mint_as_token_parameter_counts(con):
    rows = [H.candle(H.T0)]
    for i, tok in enumerate(("base", "quote", H.MINT_B, H.MINT_A.lower())):
        rr = H.resp(H.POOL_A, H.T0 + 600, rows, H.T0 + 86400 + i, token=False)
        rr["url"] += f"&token={tok}"
        rr["params"]["token"] = tok
        rr["body"] = H.gt_body(rows, base=H.MINT_B, quote=H.MINT_A)
        out = S.ingest_gt_response(con, rr, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
        assert out["identity_check"] == "OTHER_TOKEN_PARAM" and out["added"] == 0, tok
    assert S.url_token("https://x/y?a=1&token=Z&b=2") == "Z" and S.url_token("https://x/y?a=1") is None
    with pytest.raises(S.StoreError):
        S.url_token("https://x/y?token=A&token=B")


def test_a_short_page_is_not_proof_of_no_earlier_trade(con):
    """Live vendor reads showed an empty page for a pool that traded earlier: a page shorter than the limit no longer marks the
    vendor's history complete, so nothing before the earliest candle read is assumed."""
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 900, [H.candle(H.T0 + 600), H.candle(H.T0 + 300)], H.T0 + 86400),
                             chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    assert r["cover_complete"] == 0 and r["cover_from"] == H.T0 + 300
    H.series(con, mint=H.MINT_A, pool=H.POOL_A, boundary=H.T0 + 900, need_from=H.T0, keys=[r["response_key"]], checked_at=H.T0 + 86400)
    assert S.iter_rows(con, "SELECT cover_complete FROM predictive_source_status")[0]["cover_complete"] == 0
    # an earlier read covering [T0 + 300, T0 + 900] did not cover T0: a candle there later is old history, not an appearance
    r2 = S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 900, [H.candle(H.T0 + 600), H.candle(H.T0 + 300), H.candle(H.T0)],
                                          H.T0 + 2 * 86400), chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=2)
    assert r2["revisions"] == 0 and r2["added"] == 1


def test_the_token_row_comes_from_the_decisions_own_export(con):
    t1, t2 = H.T0 + 86400, H.T0 + 2 * 86400
    e1 = H.export("c1", t1, [H.thesis(H.MINT_A, t1 - 100)], [H.token(H.MINT_A, pool=H.POOL_A, first_pool_at="2026-10-01T00:00:00Z")])
    e2 = H.export("c2", t2, [H.thesis(H.MINT_A, t1 - 100)], [H.token(H.MINT_A, pool=H.POOL_A2, first_pool_at="2026-10-05T00:00:00Z")])
    S.ingest_exports(con, [e1, e2], now=t2)
    rows = S.iter_rows(con, "SELECT * FROM predictive_decisions")
    assert len(rows) == 1 and rows[0]["pool_address"] == H.POOL_A
    assert json.loads(rows[0]["token_json"])["first_pool_at"] == "2026-10-01T00:00:00Z"


def test_a_value_that_returns_to_an_earlier_version_is_a_new_version(con):
    a = [H.candle(H.T0, c=1.0)]
    b = [H.candle(H.T0, c=2.0)]
    for i, rows in enumerate((a, b, a)):
        S.ingest_gt_response(con, H.resp(H.POOL_A, H.T0 + 300, rows, H.T0 + (i + 1) * 86400), chain="solana", mint=H.MINT_A,
                             pool=H.POOL_A, now=i)
    vs = S.iter_rows(con, "SELECT * FROM predictive_candles ORDER BY id")
    assert [v["c"] for v in vs] == [1.0, 2.0, 1.0] and [v["revision_kind"] for v in vs] == [None, "VALUES", "VALUES"]
    sk = vs[0]["series_key"]
    assert S._latest_version(con, sk)["obs_key"] == vs[2]["obs_key"]


def test_check_plan_refuses_a_boundary_after_the_pools_last_decision():
    h0 = SRC.holdout_start()
    p = {"series_id": "s", "chain": "solana", "mint": H.MINT_A, "pool": H.POOL_A, "boundary": int(h0 - 5 * 86400),
         "need_from": h0 - 9 * 86400, "decisions": 1, "first_decision": h0 - 6 * 86400, "last_decision": h0 - 6 * 86400}
    with pytest.raises(SRC.SourceError, match="last development decision"):
        SRC.check_plan([p])
    SRC.check_plan([dict(p, boundary=int(h0 - 6 * 86400))])


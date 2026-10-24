"""Predictive intelligence Phase 05: the frozen fixture snapshot and the contract document.

tests/fixtures/predictive/asof_fixture.json holds real data: the export rows of a few mints (git, ref 98338a8) and the real
GeckoTerminal reads of their point-in-time pools from the Phase 05 backfill, including a first read without token=<mint> for
a pool whose mint is the quote token (refused) and its re-read with token=<mint>. A store rebuilt from it must give the same
decision keys as the real store and the pinned snapshot hashes; a transform that changes without a feature version change
fails here (P46). No network, temp files only.
"""
import base64
import gzip
import json
import re
import socket
from pathlib import Path

import pytest

from memelab.predictive import features as F
from memelab.predictive import sources as SRC
from memelab.predictive import store as S

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "predictive" / "asof_fixture.json"
DOC = ROOT / "audits" / "predictive-intelligence" / "phase_05" / "data" / "FEATURE_STORE_CONTRACT.md"

FEATURE_SET_SHA = "bc06019ea609f18083520196866b86bd6de63b7420b349c9afe7a634ff356332"
SCHEMA_V1_SHA = "be78da4b765c5f3d21b3aff092da1f6d624c96ce1f9907225f0680047e4c206f"
# (decision_key, mode) -> snapshot_sha256, pinned from the first build of the fixture store
EXPECTED = {
    "38cbb8cf9f8604739fb47c0844f328df6ba8cee2e79bca51e922b0858347767a:capture":
        "3ba7324f3121180936856eb1fb7bc3f40f13dedd0dc4cd7c5a610ac7e08d982d",
    "38cbb8cf9f8604739fb47c0844f328df6ba8cee2e79bca51e922b0858347767a:provider":
        "b169640faa6fcc11afe6b4e12d2361b2551c5281c68974b717750421e9270152",
    "7b01e6ca83b65ff199b2b43151b3d01a683d67db1d41541a4c0b7ad096e68175:capture":
        "ad4c0982b5512c516fbacf13c5c255eb6c6b22a62b5bd7f0ca6157b58b4ecb88",
    "7b01e6ca83b65ff199b2b43151b3d01a683d67db1d41541a4c0b7ad096e68175:provider":
        "1a887ea9bad6f37622c63dad8543b95ca6ac769e3531a7d5f314cda9d92e5519",
    "85cbfa037761e51d0b39b00c75fab1dfbc1374a8cc2e04bbce2f2a9b6a5f344e:capture":
        "88fb571840aa28a579fbdfb831320af174dc5d92e45dda23c0e1ea5516675a21",
    "85cbfa037761e51d0b39b00c75fab1dfbc1374a8cc2e04bbce2f2a9b6a5f344e:provider":
        "88fb571840aa28a579fbdfb831320af174dc5d92e45dda23c0e1ea5516675a21",
    "eb15e159e0c6ececb12c9a1322344de332968ec527224a875b08f0af9cff5a7a:capture":
        "bac303a6282be2689cfef920db655c701e4db68e9895c7d7004ebf69d9d8af27",
    "eb15e159e0c6ececb12c9a1322344de332968ec527224a875b08f0af9cff5a7a:provider":
        "f262e0da46f87351e172024426414232881338e876a1bc5bb1adf2825384b86a",
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 05 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


def build(path):
    fx = json.loads(FIX.read_text())
    con = S.connect(path)
    exports = [{"commit": e["commit"], "commit_time": e["commit_time"], "blob": e["blob"],
                "theses": [fx["rows"][h] for h in e["thesis_refs"]], "tokens": [fx["rows"][h] for h in e["token_refs"]]}
               for e in fx["exports"]]
    assert all(S.sha(r) == h for h, r in fx["rows"].items())
    S.ingest_exports(con, exports, now=1792800000.0, ref="98338a8ba3c5e65c5850933a35c06885b6ef991a")
    keys = {}
    for r in fx["reads"]:
        body = gzip.decompress(base64.b64decode(r["body_gzip_b64"]))
        resp = {"url": r["url"], "params": r["params"], "retrieved_at": r["retrieved_at"], "http_status": r["http_status"],
                "body": body, "boundary_at": r["boundary_at"], "timeframe": "minute", "aggregate": 5}
        out = S.ingest_gt_response(con, resp, chain=r["chain"], mint=r["mint"], pool=r["pool"], now=1792800000.0)
        keys[out["response_key"]] = out
    for s in fx["series_status"]:
        S.record_series_status(con, chain="solana", mint=s["mint"], pool=s["pool_address"], series_id=s["series_id"],
                               boundary_at=s["boundary_at"], need_from=s["need_from"], status=s["status"], detail=s["detail"],
                               response_keys=s["response_keys"], calls=s["calls"], candles_kept=s["candles_kept"],
                               last_end_at=s["last_end_at"], checked_at=s["checked_at"], now=1792800000.0)
    con.commit()
    return fx, con, keys


def test_fixture_is_real_data_with_hashes_that_match(tmp_path):
    fx, con, keys = build(tmp_path / "s.sqlite")
    for r in fx["reads"]:
        assert S.stored_body(con, S.sha([S.SOURCE_GT, r["url"], r["retrieved_at"], r["body_sha256"]])) is not None
    assert S.verify(con) == []
    got = sorted(r["decision_key"] for r in S.iter_rows(con, "SELECT decision_key FROM predictive_decisions"))
    assert got == sorted(d["decision_key"] for d in fx["decisions"])      # same identity as the real store


def test_the_quote_side_pool_is_refused_without_the_token_parameter_and_read_with_it(tmp_path):
    fx, con, keys = build(tmp_path / "s.sqlite")
    ids = {o["identity_check"] for o in keys.values()}
    assert "MINT_IS_QUOTE" in ids and "OK_TOKEN_PARAM" in ids
    st = {s["status"] for s in fx["series_status"]}
    assert "IDENTITY_MISMATCH" in st and "OK" in st


def test_pinned_snapshots(tmp_path):
    fx, con, keys = build(tmp_path / "s.sqlite")
    assert F.feature_set_sha() == FEATURE_SET_SHA
    got = {}
    for mode in F.MODES:
        F.build_snapshots(con, feature_version=F.FEATURE_VERSION, mode=mode, now=1792800001.0)
        for r in S.iter_rows(con, "SELECT decision_key, snapshot_sha256 FROM predictive_snapshots WHERE availability_mode=?", (mode,)):
            got[f"{r['decision_key']}:{mode}"] = r["snapshot_sha256"]
    assert got == EXPECTED
    for k in [r[0] for r in con.execute("SELECT snapshot_key FROM predictive_snapshots")]:
        assert F.recompute_matches(con, k)


def test_contract_document_matches_the_code():
    doc = DOC.read_text()
    assert S._checksum(S.V1_UP) == SCHEMA_V1_SHA and SCHEMA_V1_SHA in doc
    assert F.feature_set_sha() in doc
    for t in S.DATA_TABLES:
        assert f"`{t}`" in doc, t
    for n in F.NAMES:
        assert f"`{n}`" in doc, n
    for reason, basis in F.REASONS.items():
        assert f"| `{reason}` | {basis} |" in doc, reason
    for st in S.SERIES_STATUSES + S.IDENTITY_CHECKS + S.AVAILABLE_BASES:
        assert st in doc, st
    assert not re.search("[\\u2013\\u2014\\u2018\\u2019\\u201c\\u201d]", doc)

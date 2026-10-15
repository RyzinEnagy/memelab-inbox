"""Independent M00 counterexamples, deliberately RED on the pinned defective code.

Run from a clean pinned repository with this file's absolute path. Existing test
builders only supply schema-valid synthetic rows; the expected causal/provenance
rules below are independent of the implementation. No xfail, clock patch or fix.
"""
import json
from pathlib import Path
import sqlite3
import sys
from decimal import Decimal

import pytest

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import test_social_narratives as N
from memelab import db
from memelab.social import alpha_core as A, alpha_store as AS, feed_store as F
from memelab.social import perf_core as P, narratives, outcomes_core as O, replay_sources


def show(case, **data):
    print(json.dumps({"case": case, **data}, default=str, sort_keys=True))


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private.sqlite"))
    monkeypatch.setenv("MEMELAB_LLM_CONFIG", str(tmp_path / "missing.json"))
    path = tmp_path / "synthetic.sqlite"
    db.init_db(path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    N.store.register_analysis_version(con, N.EXTRACT_V, "extractor", "M00 synthetic rows", now=N.D1)
    N.cover(con)
    post = N.post(con, "m00-only-invented", "m00-invented-source", N.D1 + 3600,
                  tokens=[N.tok("solana", N.M1)])
    yield con, path, post
    con.close()


def test_late_extraction_cannot_enter_past_narrative(world):
    con, _, _ = world
    cutoff = N.D2
    con.execute("UPDATE social_claim_extractions SET extracted_at=?", (cutoff + 86400,))
    result = narratives.snapshot(con, day="2026-10-12", now=cutoff)
    show("AUD-001", cutoff=cutoff, extraction_at=cutoff + 86400, clusters=len(result["clusters"]))
    assert result["clusters"] == [], "interpretation was not available by the historical cutoff"


def test_explicit_future_snapshot_cannot_bypass_cutoff(world):
    con, _, _ = world
    result = narratives.snapshot(con, day="2026-10-12", now=N.D2)
    earlier = N.D1 + 7200
    got = F.load_input(con, as_of=earlier, include_fixtures=True, run_id=result["run_id"])
    default = F.load_input(con, as_of=earlier, include_fixtures=True)
    show("AUD-015", as_of=earlier, snapshot_cutoff=got["snapshot"]["cutoff"],
         explicit_clusters=len(got["clusters"]), default_clusters=len(default["clusters"]))
    assert default["clusters"] == []  # positive control: the no-ID branch already excludes it
    assert got["clusters"] == [], "explicit run selection must obey the same as-of rule"


def series():
    return {"chain": "solana", "contract": N.M1, "source": "invented M00 hourly prices",
            "candle_seconds": 3600, "as_of_kind": "HISTORICAL_CANDLE",
            "rows": [{"t": 0, "o": 10, "h": 100, "l": 5, "c": 20, "liq": 100000, "v": 1000}]}


def prepared():
    ser, rejected = A.prep_series({"series": [series()]})
    assert rejected == []
    return ser[("solana", N.M1)]


def test_intrabar_open_is_not_a_fill_at_the_later_decision():
    got, error = A.entry_for(prepared(), 1800, 1, dict(A.DEFAULT_POLICY), 3600)
    show("AUD-024-entry", output=got, error=error)
    assert got is None or got["candle_t"] >= 1800, "the t=0 open cannot execute at t=1800"


def test_uncompleted_high_is_not_known_at_decision():
    policy = dict(A.DEFAULT_POLICY, entry_price_rule="CANDLE_ADVERSE")
    got, error = A.entry_for(prepared(), 1800, 1, policy, 1800)
    show("AUD-024-extrema", as_of=1800, candle_end=3600, output=got, error=error)
    assert got is None, "a completed candle high cannot be known before candle end"


def test_intrabar_exit_cannot_use_the_earlier_open():
    got, error = A.exit_for(prepared(), 3000, 1, dict(A.DEFAULT_POLICY), 3600)
    show("AUD-024-exit", output=got, error=error)
    assert got is None or got["candle_t"] >= 3000, "an earlier open is not a timed horizon exit"


def test_future_wallet_mark_is_unavailable_at_transaction():
    ledger = P.Ledger()
    ledger.prices = [{"asset": "NATIVE", "t": 1100, "kind": "MID", "usd": Decimal(100), "idx": 0,
                      "source": "invented future mark"}]
    book = P.Book(ledger, dict(P.DEFAULT_POLICY, price_tolerance_s=200))
    mark = book.near("NATIVE", 1000)
    usd, basis = book.unit_usd("NATIVE", 1000)
    show("AUD-025", transaction_at=1000, selected_mark=mark, unit_usd=usd, basis=basis)
    assert book.latest_mid("NATIVE", 1000) is None  # positive causal lookup control
    assert mark is None and usd is None, "future midpoint cannot be an observed decision-time mark"


def test_fixture_claim_and_series_cannot_be_exported_as_real(world):
    con, _, _ = world
    AS.put_series(con, [series()], fixture=True, now=N.D2)
    got = AS.build_input(con, as_of=N.D2)
    mode = con.execute("SELECT access_mode FROM social_observations").fetchone()[0]
    show("AUD-004", observation_access_mode=mode, stored_series_fixture=1,
         exported_is_fixture=got["is_fixture"], calls=len(got["calls"]), series=len(got["series"]))
    assert mode == "fixture" and len(got["calls"]) == 1 and len(got["series"]) == 1
    assert got["is_fixture"] is True, "fixture lineage must not be labelled real"


def test_replay_export_cannot_backdate_the_extracted_call(world):
    con, path, post = world
    late = N.D2 + 86400
    ref = con.execute("SELECT ref_id FROM social_token_refs WHERE contract=?", (N.M1,)).fetchone()[0]
    con.execute("UPDATE social_claims SET claim_type='CALL',direction='LONG',token_ref_id=? WHERE id=?",
                (ref, post["claim_id"]))
    con.execute("UPDATE social_claim_extractions SET extracted_at=?", (late,))
    con.commit()
    got = replay_sources.from_db(str(path))["posts"]
    show("AUD-002/AUD-032", extracted_at=late, exported=got)
    assert len(got) == 1
    assert got[0]["available_at"] >= late, "export must not erase derived knowledge time"


def test_late_fetched_market_fact_cannot_be_known_at_generation():
    fact = {"field": "price", "value_num": 10, "as_of": 900, "fetched_at": 1100,
            "provider": "invented", "fact_id": "synthetic"}
    context, missing = O.market_at_generation([fact], 1000, dict(O.DEFAULT_POLICY))
    show("AUD-033", generated_at=1000, fact=fact, context=context, missing=missing)
    assert context["observed_price"] is None, "earlier market-effective time is insufficient when fetched later"


def test_positive_boundary_controls():
    ser = prepared()
    got, error = A.entry_for(ser, 0, 1, dict(A.DEFAULT_POLICY), 3600)
    assert error is None and got["candle_t"] == got["fill_t"] == 0 and got["price"] == 10
    ledger = P.Ledger()
    ledger.prices = [{"asset": "NATIVE", "t": 900, "kind": "MID", "usd": Decimal(7), "idx": 0,
                      "source": "invented prior mark"}]
    book = P.Book(ledger, dict(P.DEFAULT_POLICY, price_tolerance_s=200))
    assert book.unit_usd("NATIVE", 1000) == (Decimal(7), "OBSERVED")
    show("positive-controls", candle_boundary_fill=got, prior_wallet_mark="7 OBSERVED")

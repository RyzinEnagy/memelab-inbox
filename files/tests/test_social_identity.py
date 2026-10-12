"""Phase 05: exact token identity for social references, and timestamped market context.

Synthetic provider bodies in tests/fixtures/social/resolve/fx_providers.json (invented tokens and prices, shapes of the
collector projections). Temp databases, fixed clock, no network.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import db
from memelab.social import content_guard, identity as ID, market_context as MC, schema
from memelab.social._keccak import eip55, keccak256

ROOT = Path(__file__).resolve().parent.parent
FXDIR = ROOT / "tests" / "fixtures" / "social" / "resolve"
FX = json.loads((FXDIR / "fx_providers.json").read_text())
A, B = FX["addresses"], FX["bodies"]
T0, FETCH = FX["t0"], FX["fetched_at"]
SENTENCE = "Invented fixture sentence about the moon and friends"


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def one(post, kind=None):
    ms = [m for m in post["mentions"] if kind is None or m["mention_kind"] == kind]
    assert len(ms) == 1, ms
    return ms[0]


def viable(m):
    return {(c["chain"], c["contract"]) for c in m["candidates"] if c["verdict"] in ("viable", "chosen")}


# ---------- address checks and extraction ----------

def test_keccak_and_eip55_vectors():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert eip55("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed") == "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    assert ID.address_shape("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed") == ("evm", None)
    assert ID.address_shape("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAeD") == ("invalid", "checksum_mismatch")
    assert ID.address_shape(A["M1"]) == ("solana", None)
    assert ID.address_shape(A["M1"] + "z")[0] == "invalid"


def test_extraction_reads_text_in_memory_and_returns_only_tokens():
    text = f"{SENTENCE} $PEPE $100 {A['X2']} https://pump.fun/coin/{A['M1']} again {A['M1']}"
    ms = ID.extract_mentions(text)
    kinds = [(m["kind"], m["value"]) for m in ms]
    assert ("TICKER", "PEPE") in kinds and not any(v == "100" for _, v in kinds)
    assert ("CONTRACT", A["X2"]) in kinds
    assert sum(1 for m in ms if m.get("address") == A["M1"]) == 1          # link and bare copy count once
    assert not any(m["kind"] == "CONTRACT" and m["value"] != A["X2"] and m["value"] in A["X2"] for m in ms)  # no base58 run inside 0x
    assert all("moon" not in json.dumps(m) for m in ms)


# ---------- tickers ----------

def test_same_ticker_across_chains_and_contracts_is_ambiguous():
    m = one(ID.resolve_post(B, text="$PEPE"))
    assert m["status"] == "ambiguous" and m["resolved"] is None
    assert {"symbol_only", "multiple_candidates", "candidates_on_several_chains"} <= set(m["reasons"])
    assert viable(m) == {("ethereum", A["PEPE_ETH"]), ("solana", A["PEPE_SOL1"]), ("solana", A["PEPE_SOL2"]), ("bsc", A["PEPE_BSC"])}
    arb = [c for c in m["candidates"] if c["chain"] == "arbitrum"]
    assert arb and arb[0]["support"] == "unsupported" and arb[0]["verdict"] == "rejected"


def test_ticker_never_resolves_on_symbol_alone_even_with_one_candidate():
    m = one(ID.resolve_post(B, text="$PEPE", chain_hint="ethereum"))
    assert m["status"] == "ambiguous" and "single_search_candidate_not_proof" in m["reasons"]
    assert viable(m) == {("ethereum", A["PEPE_ETH"])}
    m = one(ID.resolve_post(B, text="$PEPE", chain_hint="solana"))
    assert m["status"] == "ambiguous" and len(viable(m)) == 2
    m = one(ID.resolve_post(B, text="$NOPEX"))
    assert m["status"] == "unresolved" and "no_candidates" in m["reasons"]


def test_ticker_resolves_only_through_a_contract_in_the_same_post():
    post = ID.resolve_post(B, text=f"$LABDOG CA {A['M1']}")
    t, c = one(post, "TICKER"), one(post, "CONTRACT")
    assert post["status"] == "resolved" and c["status"] == "resolved" and t["status"] == "resolved"
    assert t["resolved"]["contract"] == c["resolved"]["contract"] == A["M1"]
    assert t["reasons"][0] == "corroborated_by_contract_in_same_post"
    assert any(e["kind"] == "same_post_contract" for e in t["evidence"])


def test_ticker_contradicting_the_posted_contract_is_conflicted():
    post = ID.resolve_post(B, text=f"$WIF {A['M1']}")
    assert post["status"] == "conflicted"
    t, c = one(post, "TICKER"), one(post, "CONTRACT")
    assert t["status"] == c["status"] == "conflicted" and c["resolved"] is None
    assert "post_ticker_disagrees_with_contract_symbol" in c["reasons"]
    assert viable(c) == {("solana", A["M1"])}                        # the candidate is kept, not guessed away


def test_spoofed_name_contract_resolves_to_itself_and_is_flagged():
    post = ID.resolve_post(B, text=f"$LABDOG CA {A['M2']}")
    c = one(post, "CONTRACT")
    assert c["status"] == "resolved" and c["resolved"]["contract"] == A["M2"]
    assert {"symbol_shared_with_other_contracts", "a_more_liquid_contract_uses_this_symbol"} <= set(c["reasons"])
    rej = [x for x in c["candidates"] if x["verdict"] == "rejected"]
    assert rej and rej[0]["contract"] == A["M1"] and rej[0]["why"] == "same_symbol_different_contract"
    assert "a_more_liquid_contract_uses_this_symbol" in one(post, "TICKER")["reasons"]


# ---------- contracts and links ----------

def test_contract_typos_are_unresolved_with_near_matches(con):
    typo = A["M1"][:-1] + ("A" if A["M1"][-1] != "A" else "B")
    m = one(ID.resolve_post(B, text=typo, con=con))
    assert m["status"] == "unresolved" and "not_found_possible_typo" in m["reasons"]
    assert [(x["contract"], x["verdict"]) for x in m["candidates"]] == [(A["M1"], "near_match")]
    cs = eip55(A["X2"])
    i = next(i for i, ch in enumerate(cs) if i > 1 and ch.isalpha())
    bad = cs[:i] + cs[i].swapcase() + cs[i + 1:]
    m = one(ID.resolve_post(B, text=bad, con=con))
    assert m["status"] == "unresolved" and m["reasons"][0] == "checksum_mismatch"
    assert m["candidates"][0]["contract"] == A["X2"] and m["candidates"][0]["why"] == "same_hex_bad_checksum"
    m = one(ID.resolve_post(B, text=A["X2"][:-1], con=con))                  # 39 hex digits
    assert m["status"] == "unresolved" and m["reasons"][0] == "address_wrong_length"


def test_same_evm_address_on_two_chains_is_ambiguous_and_link_chain_conflict():
    m = one(ID.resolve_post(B, text=A["X1"]))
    assert m["status"] == "ambiguous" and viable(m) == {("base", A["X1"]), ("bsc", A["X1"])}
    m = one(ID.resolve_post(B, urls=[f"https://dexscreener.com/base/{A['X1']}"]))
    assert m["status"] == "resolved" and m["resolved"]["chain"] == "base" and m["chain_hint_basis"] == "LINK"
    m = one(ID.resolve_post(B, urls=[f"https://dexscreener.com/bsc/{A['X2']}"]))
    assert m["status"] == "conflicted" and "chain_hint_disagrees_with_providers" in m["reasons"]
    m = one(ID.resolve_post(B, urls=[f"https://basescan.org/token/{eip55(A['X2'])}"]))
    assert m["status"] == "resolved" and m["resolved"] == {"chain": "base", "contract": A["X2"], "asset_class": "TOKEN", "symbol_seen": "BASEDOG"}


def test_pair_link_maps_to_its_base_token():
    m = one(ID.resolve_post(B, urls=[f"https://dexscreener.com/solana/{A['P1']}"]))
    assert m["status"] == "resolved" and m["resolved"]["contract"] == A["M1"] and "pair_mapped_to_base_token" in m["reasons"]


def test_invalid_and_unsupported_chains():
    m = one(ID.resolve_post(B, urls=[f"https://dexscreener.com/notachain/{A['X2']}"]))
    assert m["status"] == "unresolved" and m["reasons"] == ["invalid_chain"]
    m = one(ID.resolve_post(B, text=A["X2"], chain_hint="foochain"))
    assert m["status"] == "unresolved" and m["reasons"] == ["invalid_chain"]
    m = one(ID.resolve_post(B, text=A["M1"], chain_hint="base"))
    assert m["status"] == "unresolved" and m["reasons"] == ["address_not_valid_for_chain"]
    m = one(ID.resolve_post(B, urls=[f"https://dexscreener.com/arbitrum/{A['X3']}"]))
    assert m["status"] == "unresolved" and "unsupported_chain" in m["reasons"]
    assert m["candidates"][0]["support"] == "unsupported"
    m = one(ID.resolve_post(B, text=A["X3"]))                                # no hint: found only on an unsupported chain
    assert m["status"] == "unresolved" and "unsupported_chain" in m["reasons"]


def test_wrapped_tokens_are_registry_assets_and_need_a_chain():
    m = one(ID.resolve_post(B, text="$WETH"))
    assert m["status"] == "ambiguous" and viable(m) == {("ethereum", "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
                                                        ("base", "0x4200000000000000000000000000000000000006")}
    m = one(ID.resolve_post(B, text="$WETH", chain_hint="base"))
    assert m["status"] == "resolved" and m["resolved"]["asset_class"] == "WRAPPED_NATIVE"
    m = one(ID.resolve_post(B, urls=["https://basescan.org/token/0x4200000000000000000000000000000000000006"]))
    assert m["status"] == "resolved" and m["resolved"]["asset_class"] == "WRAPPED_NATIVE" and "registry_asset_wrapped_native" in m["reasons"]


def test_token_migration_keeps_exact_identity_and_lists_the_successor(con):
    with pytest.raises(ValueError):
        ID.record_relation(con, "solana", A["M3"], "MIGRATED_TO", "solana", A["M4"], "OFFICIAL_SOURCE", source_url=None)
    ID.record_relation(con, "solana", A["M3"], "MIGRATED_TO", "solana", A["M4"], "OFFICIAL_SOURCE",
                       source_url="https://example.org/fixture-migration-notice", effective_at="2026-10-05T00:00:00Z", now=T0)
    m = one(ID.resolve_post(B, text=A["M3"], con=con))
    assert m["status"] == "resolved" and m["resolved"]["contract"] == A["M3"]       # never silently moved to the new contract
    assert "migrated_successor_known" in m["reasons"]
    assert [(c["contract"], c["verdict"]) for c in m["candidates"] if c["verdict"] == "successor"] == [(A["M4"], "successor")]
    m = one(ID.resolve_post(B, text=A["M4"], con=con))
    assert m["status"] == "resolved" and "is_successor_of_migrated_contract" in m["reasons"]
    m = one(ID.resolve_post(B, text="$MIGR", con=con))
    assert m["status"] == "ambiguous" and viable(m) == {("solana", A["M3"]), ("solana", A["M4"])}


def test_disagreeing_providers_on_symbol_keep_the_address_identity():
    m = one(ID.resolve_post(B, text=A["X4"]))
    assert m["status"] == "resolved" and "providers_disagree_on_symbol" in m["reasons"]
    assert m["candidates"][0]["symbols_by_provider"] == {"dexscreener": "TWIN", "goplus": "TW1N"}


# ---------- persistence and downstream API ----------

def _persist(con, text=None, urls=(), item="telegram:-1001000000001_22", hint=None, now=FETCH):
    post = ID.resolve_post(B, text=text, urls=urls, chain_hint=hint, con=con)
    ids = ID.persist(con, post, item_key=item, now=now)
    con.commit()
    return post, ids


def test_persist_is_idempotent_and_ambiguous_stores_candidates(con):
    post, ids = _persist(con, text="$PEPE", item="telegram:-1001000000001_21")
    again = ID.persist(con, post, item_key="telegram:-1001000000001_21", now=FETCH + 5)
    assert ids == again
    assert con.execute("SELECT COUNT(*) FROM social_token_resolutions").fetchone()[0] == 1
    got = ID.token_identity(con, item_key="telegram:-1001000000001_21")
    assert got[0]["status"] == "ambiguous" and got[0]["identity"] is None
    assert len(got[0]["candidates"]) == 5 and {c["support"] for c in got[0]["candidates"]} == {"supported", "unsupported"}
    ref = con.execute("SELECT ref_kind, contract FROM social_token_refs WHERE ref_key='ticker:PEPE'").fetchone()
    assert ref["ref_kind"] == "TICKER_ONLY" and ref["contract"] is None
    with pytest.raises(sqlite3.IntegrityError):                       # a resolved status needs an identity, and only it
        con.execute("UPDATE social_token_resolutions SET status='resolved' WHERE resolution_id=?", (ids[0],))


def test_resolved_reference_is_stored_with_ref_and_evidence(con):
    post, ids = _persist(con, text=SENTENCE, urls=[f"https://pump.fun/coin/{A['M1']}"])
    got = ID.token_identity(con, item_key="telegram:-1001000000001_22")
    assert len(got) == 1 and got[0]["status"] == "resolved"
    ident = got[0]["identity"]
    assert ident["chain"] == "solana" and ident["contract"] == A["M1"]
    ref = con.execute("SELECT * FROM social_token_refs WHERE ref_id=?", (ident["ref_id"],)).fetchone()
    assert ref["ref_kind"] == "CONTRACT_ADDRESS" and ref["contract"] == A["M1"]
    assert {e["kind"] for e in got[0]["evidence"]} >= {"provider_record", "link"}
    assert any(e.get("source_key") == f"jup_tok:{A['M1']}" for e in got[0]["evidence"])


def test_context_refuses_anything_not_resolved(con):
    _, ids = _persist(con, text="$PEPE")
    with pytest.raises(ValueError):
        MC.attach(con, ids[0], B, fetched_at=FETCH, published_at=T0)


def _ctx(con, published_at, fetched_at=FETCH, contract=None, native=150.0):
    _, ids = _persist(con, text=contract or A["M1"])
    out = MC.attach(con, ids[0], B, fetched_at=fetched_at, published_at=published_at, native_price=native, now=fetched_at)
    con.commit()
    return out, ids[0]


def facts(con, **where):
    q = "SELECT * FROM social_market_facts WHERE " + " AND ".join(f"{k}=?" for k in where) + " ORDER BY fact_id"
    return [dict(r) for r in con.execute(q, tuple(where.values()))]


def test_posting_time_price_comes_from_a_historical_candle_not_from_today(con):
    out, rid = _ctx(con, published_at=T0 + 2 * 3600 + 1800)        # 02:30 UTC, inside the 02:00 hourly candle
    assert out["posting_time_status"] == "HISTORICAL_CANDLE"
    assert out["posting_price"] == pytest.approx(0.0062) and out["observed_price"] == pytest.approx(0.0100)
    pp = facts(con, fact_id=out["posting_price_fact_id"])[0]
    assert pp["as_of_kind"] == "HISTORICAL_CANDLE" and pp["as_of"] == T0 + 7200 and pp["valid_until"] == T0 + 10800
    assert pp["fetched_at"] == FETCH and pp["source_key"] == f"gt_ohlcv:{A['P1']}:hour1" and pp["source_url"].startswith("https://api.geckoterminal.com/")
    op = facts(con, fact_id=out["observed_price_fact_id"])[0]
    assert op["as_of_kind"] == "OBSERVED_AT_FETCH" and op["as_of"] == FETCH and op["provider"] == "jupiter"
    assert out["observed_lag_seconds"] == FETCH - (T0 + 9000)


def test_no_history_leaves_the_posting_price_empty(con):
    out, _ = _ctx(con, published_at=T0 - 30 * 86400)                  # long before any candle
    assert out["posting_time_status"] == "NO_HISTORY" and out["posting_price"] is None and out["posting_price_fact_id"] is None
    assert out["observed_price"] == pytest.approx(0.0100)              # today's price is kept, but only as observed-at-fetch
    assert {"code": "no_candle_covers_published_at"} in out["notes"]
    con.execute("DELETE FROM social_market_context")
    out, _ = _ctx(con, published_at=None)
    assert out["posting_time_status"] == "PUBLISHED_AT_UNKNOWN" and out["posting_price"] is None
    con.execute("DELETE FROM social_market_context")
    out, _ = _ctx(con, published_at=FETCH - 60)                      # fetched a minute after posting, no finer candle: observation stands
    assert out["posting_time_status"] in ("HISTORICAL_CANDLE", "FETCHED_AT_POSTING")
    out2, _ = _ctx(con, published_at=FETCH - 60, fetched_at=FETCH + 1)
    assert out2["observed_lag_seconds"] == 61


def test_missing_pool(con):
    out, _ = _ctx(con, published_at=T0, contract=A["M5"])
    assert out["market_status"] == "NO_POOL" and {"code": "no_pool_reported_at_fetch"} in out["notes"]
    assert facts(con, contract=A["M5"], field="pair") == [] and facts(con, contract=A["M5"], field="liquidity_reported") == []
    assert facts(con, contract=A["M5"], field="price")[0]["value_num"] == 0.5


def test_disagreeing_price_providers_each_keep_a_row(con):
    out, _ = _ctx(con, published_at=T0)
    prices = {(f["provider"], f["pair_id"]): f["value_num"] for f in facts(con, contract=A["M1"], field="price")}
    assert prices[("jupiter", None)] == 0.01 and prices[("dexscreener", A["P1"])] == 0.011 and prices[("dexscreener", A["P2"])] == 0.0108
    spread = next(n for n in out["notes"] if n["code"] == "provider_price_spread")
    assert spread["value"] == pytest.approx(0.1) and {"code": "providers_disagree_on_price"} in out["notes"]


def test_valuation_fields_carry_supply_denominators_units_and_windows(con):
    _ctx(con, published_at=T0)
    mc = {f["provider"]: f for f in facts(con, contract=A["M1"], field="market_cap")}
    fdv = {f["provider"]: f for f in facts(con, contract=A["M1"], field="fdv")}
    assert mc["jupiter"]["supply_basis"] == "circulating" and fdv["jupiter"]["supply_basis"] == "total"
    assert mc["dexscreener"]["supply_basis"] == "circulating" and fdv["dexscreener"]["supply_basis"] == "total"
    assert mc["jupiter"]["value_num"] == 9_000_000 and mc["dexscreener"]["value_num"] == 9_900_000
    cs = facts(con, contract=A["M1"], field="circulating_supply")[0]
    assert cs["unit"] == "token" and cs["quote_currency"] is None
    for f in facts(con, contract=A["M1"]):
        assert f["fetched_at"] == FETCH and f["valid_until"] > f["valid_from"] and f["provider"] and f["unit"]
        assert f["source_key"] or f["field"].startswith("liquidity")


def test_reported_liquidity_versus_executable_proceeds(con):
    out, _ = _ctx(con, published_at=T0)
    liq = max(f["value_num"] for f in facts(con, contract=A["M1"], field="liquidity_reported"))
    assert liq == 230000
    sells = {f["size_usd"]: f for f in facts(con, contract=A["M1"], field="sell_quote_out")}
    assert sells[1000.0]["unit"] == "SOL" and sells[1000.0]["value_num"] == pytest.approx(6.5)
    assert sells[50000.0]["value_num"] is None and sells[50000.0]["value_str"] == "NO_ROUTE" and sells[50000.0]["unit"] == "status"
    usd = {f["size_usd"]: f for f in facts(con, contract=A["M1"], field="sell_quote_out_usd")}
    assert usd[10000.0]["value_num"] == pytest.approx(6000) and usd[10000.0]["bucket"] == "INFERENCE"   # SOL proceeds x supplied SOL price
    ratios = {n["size_usd"]: n["ratio"] for n in out["notes"] if n["code"] == "sell_proceeds_ratio"}
    assert ratios[10000.0] == pytest.approx(0.6)
    assert any(n["code"] == "reported_liquidity_is_not_exit_proceeds" for n in out["notes"])
    assert {"code": "sell_no_route", "size_usd": 50000.0} in out["notes"]


def test_evm_context_uses_provider_usd_proceeds(con):
    out, _ = _ctx(con, published_at=T0, contract=A["X2"], native=None)
    usd = facts(con, contract=A["X2"], field="sell_quote_out_usd")[0]
    assert usd["value_num"] == 985 and usd["bucket"] == "FACT" and usd["provider"] == "kyberswap.routes"
    out_eth = facts(con, contract=A["X2"], field="sell_quote_out")[0]
    assert out_eth["unit"] == "ETH" and out_eth["value_num"] == pytest.approx(0.32)
    assert out["posting_time_status"] == "NO_HISTORY"


def test_facts_are_versioned_per_series_and_refetch_is_idempotent(con):
    _ctx(con, published_at=T0)
    n = con.execute("SELECT COUNT(*) FROM social_market_facts").fetchone()[0]
    _ctx(con, published_at=T0)                                        # same fetch again: nothing new
    assert con.execute("SELECT COUNT(*) FROM social_market_facts").fetchone()[0] == n
    b2 = json.loads(json.dumps(B))
    b2[f"jup_tok:{A['M1']}"][0]["usdPrice"] = 0.012
    _, ids = _persist(con, text=A["M1"])
    MC.attach(con, ids[0], b2, fetched_at=FETCH + 600, published_at=T0, native_price=150.0, now=FETCH + 600)
    js = [f for f in facts(con, contract=A["M1"], field="price", provider="jupiter")]
    assert [(f["fact_version"], f["value_num"]) for f in js] == [(1, 0.01), (2, 0.012)]
    assert js[1]["supersedes_fact_id"] == js[0]["fact_id"] and js[1]["as_of"] == FETCH + 600


def test_no_text_reaches_the_database_and_guard_passes(con, tmp_path):
    _persist(con, text=f"{SENTENCE} $LABDOG {A['M1']}")
    _, ids = _persist(con, text=A["M1"])
    MC.attach(con, ids[0], B, fetched_at=FETCH, published_at=T0 + 9000, native_price=150.0, now=FETCH)
    con.commit()
    for t in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'social_%'")]:
        for row in con.execute(f"SELECT * FROM {t}"):
            assert "moon" not in json.dumps([str(x) for x in row])
    dbfile = Path(con.execute("PRAGMA database_list").fetchone()[2])
    assert content_guard.check_sqlite("data/memelab.sqlite", dbfile) == []


def test_migration_5_rolls_back_cleanly(con):
    assert schema.current_version(con) == 5
    assert schema.rollback(con, 4) == [5]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not names & {"social_token_resolutions", "social_market_facts", "social_market_context", "social_token_candidates", "social_token_relations"}
    assert "social_item_versions" in names
    assert schema.migrate(con) == [5]


def test_resolution_plan_reuses_existing_builders():
    ms = ID.extract_mentions(f"$PEPE {A['X2']} {A['M1']}")
    keys = [r["key"] for r in ID.resolution_plan(ms).reqs]
    assert "ds_search:PEPE" in keys and "jup_tok:PEPE" in keys
    assert f"ds:base:batch:0" in keys and f"goplus:base:{A['X2']}" in keys and f"goplus:bsc:{A['X2']}" in keys
    assert f"ds:solana:one:{A['M1']}" in keys and f"jup_tok:{A['M1']}" in keys
    ctx = MC.context_plan("solana", A["M1"], [A["P1"]], 6, 0.01, 150.0)
    ck = [r["key"] for r in ctx.reqs]
    assert f"gt_ohlcv:{A['P1']}:hour1" in ck and f"jq:SELL:1000:{A['M1']}" in ck


def test_cli_demo_ambiguous_message_and_resolved_address(tmp_path):
    env = {"MEMELAB_PRIVATE_DB": str(tmp_path / "p.sqlite"), "PATH": "/usr/bin:/bin"}
    dbp = tmp_path / "demo.sqlite"

    def run(*args):
        r = subprocess.run([sys.executable, "-m", "memelab", "social", *args, "--db", str(dbp)], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=120)
        return r.returncode, json.loads(r.stdout) if r.stdout.strip() else None

    rc, amb = run("resolve", "--post", str(FXDIR / "post_ambiguous.json"), "--bodies", str(FXDIR / "fx_providers.json"),
                  "--context", "--now", str(FETCH))
    assert rc == 0 and amb["status"] == "ambiguous"
    r = amb["resolutions"][0]
    assert r["mention"] == {"kind": "TICKER", "value": "PEPE"} and r["identity"] is None and r["market_context"] == []
    rc, res = run("resolve", "--post", str(FXDIR / "post_resolved.json"), "--bodies", str(FXDIR / "fx_providers.json"),
                  "--context", "--now", str(FETCH))
    assert rc == 0 and res["status"] == "resolved"
    link = next(x for x in res["resolutions"] if x["mention"]["kind"] == "LINK")
    assert link["identity"]["contract"] == A["M1"] and link["identity"]["chain"] == "solana"
    ctx = link["market_context"][0]
    assert ctx["posting_time_status"] == "HISTORICAL_CANDLE" and ctx["posting_price"]["value_num"] == pytest.approx(0.0062)
    rc, stored = run("identity", "--item", "telegram:-1001000000001_22")
    assert rc == 0 and {x["status"] for x in stored} == {"resolved"}
    rc, _ = run("identity", "--item", "telegram:no_such_item")
    assert rc == 1

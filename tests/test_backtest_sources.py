"""Phase 06: historical data adapters and data-quality defenses (synthetic fixtures; no network).

The fake HTTP layer returns canned GeckoTerminal-shaped bodies. These tests prove adapter behavior (budget, backoff,
partial bars, duplicates, orientation, pool choice, universe union, capture chronology), not market fidelity.
"""
import json
import subprocess

import pytest

from memelab.backtest import quality, store
from memelab.backtest.sources import captures, gecko, labstate

T = 1_800_000_000.0
H = 3600
MINT = "FIXmint111111111111111111111111111111111pump"


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        status, body = self.responses.pop(0)
        return status, json.dumps(body).encode() if not isinstance(body, bytes) else body


def budget(n=20):
    return gecko.Budget(max_calls=n, min_spacing_s=0.0, sleep=lambda s: None)


def pools_body(*pools):
    return {"data": [{"attributes": {"address": a, "pool_created_at": c, "reserve_in_usd": str(r)},
                      "relationships": {"dex": {"data": {"id": dex}}, "base_token": {"data": {"id": f"solana_{base}"}},
                                        "quote_token": {"data": {"id": "solana_So11111111111111111111111111111111111111112"}}}}
                     for a, c, r, dex, base in pools]}


def ohlcv_body(rows):
    return {"data": {"attributes": {"ohlcv_list": rows}}}


def test_backoff_on_429_then_success_and_raw_shard(con, tmp_path):
    http = FakeHTTP([(429, {}), (200, pools_body(("P1", "2027-01-15T08:00:00Z", 1000.0, "pumpswap", MINT)))])
    b = budget()
    r = gecko.fetch_pools(con, MINT, b, http, observed_at=T + 100 * H)
    assert r["status"] == "OK" and b.calls == 2 and b.retries == 1
    assert list((tmp_path / "raw" / "geckoterminal").glob("*.json"))
    pv = con.execute("SELECT pool_type, available_at, pool_created_at FROM bt_pool_versions").fetchone()
    assert pv["pool_type"] == "CPMM" and pv["available_at"] == pv["pool_created_at"] + gecko.PROVIDER_LAG_S  # modeled, not today


def test_blocked_after_retries_and_budget_exhaustion(con):
    http = FakeHTTP([(429, {})] * 5)
    r = gecko.fetch_pools(con, MINT, budget(), http, observed_at=T)
    assert r["status"] == "SOURCE_BLOCKED" and r["pools"] == []
    with pytest.raises(gecko.BudgetExhausted):
        gecko.fetch_pools(con, MINT, gecko.Budget(max_calls=0, min_spacing_s=0, sleep=lambda s: None), FakeHTTP([]), observed_at=T)


def test_pool_where_mint_is_quote_is_skipped_and_unknown_dex_not_cpmm(con):
    other = "OTHERmint11111111111111111111111111111111111"
    http = FakeHTTP([(200, pools_body(("Pq", "2027-01-15T08:00:00Z", 5.0, "pumpswap", other), ("Px", "2027-01-15T09:00:00Z", 7.0, "brand-new-dex", MINT)))])
    r = gecko.fetch_pools(con, MINT, budget(), http, observed_at=T + 1e6)
    assert [p["pool"] for p in r["pools"]] == ["Px"] and r["pools"][0]["pool_type"] == "UNKNOWN"


def test_ohlcv_partial_bar_invalid_rows_and_duplicates(con):
    obs = T + 10 * H + 600
    rows = [[T + 10 * H, 1, 1.2, 0.9, 1.1, 5],          # forming bar (closes at T+11H > obs): skipped
            [T + 9 * H, 1, 1.1, 0.95, 1.05, 4],
            [T + 8 * H, 1, 1.0, 1.2, 1.1, 4],           # invalid: low above high
            [T + 7 * H, 1, 1.1, 0.9, 1.0, 3], [T + 7 * H, 1.01, 1.1, 0.9, 1.0, 3],  # duplicate timestamp in one response
            [T + 2 * H, 1, 1.1, 0.9, 1.0, 0]]           # zero volume is a real zero, stored as 0
    http = FakeHTTP([(200, ohlcv_body(rows))])
    r = gecko.fetch_ohlcv(con, MINT, "P1", budget(), http, observed_at=obs)
    assert r["partial_skipped"] == 1 and r["invalid"] == 1 and r["duplicate_starts"] == 1
    got = {(row["start"], row["quality_flags"]) for row in con.execute("SELECT start, quality_flags FROM bt_market_bars")}
    assert (T + 9 * H, "AVAIL_MODELED") in got
    assert any(s == T + 7 * H and "DUP_TS_IN_RESPONSE" in f for s, f in got)
    assert con.execute("SELECT volume_usd FROM bt_market_bars WHERE start=?", (T + 2 * H,)).fetchone()[0] == 0.0
    # the missing hours (T+3H..T+6H) are not filled with anything
    assert con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE start BETWEEN ? AND ?", (T + 3 * H, T + 6 * H)).fetchone()[0] == 0


def test_pool_basis_uses_only_volume_known_at_decision(con):
    for pool, created in (("PA", T - 10 * H), ("PB", T - 10 * H)):
        store.record_pool_version(con, chain="solana", pool_address=pool, mint=MINT, pool_type="CPMM", pool_created_at=created, observed_at=T + 100 * H,
                                  available_at=created + 300, source="fixture")
    # before the decision PA trades more; after the decision PB explodes (future volume must not decide)
    for i in range(1, 6):
        store.record_bar(con, chain="solana", mint=MINT, pool_address="PA", tf=H, start=T - i * H, o=1, h=1, l=1, c=1, volume_usd=100.0, observed_at=T + 100 * H, provider="fx")
        store.record_bar(con, chain="solana", mint=MINT, pool_address="PB", tf=H, start=T - i * H, o=1, h=1, l=1, c=1, volume_usd=10.0, observed_at=T + 100 * H, provider="fx")
        store.record_bar(con, chain="solana", mint=MINT, pool_address="PB", tf=H, start=T + i * H, o=1, h=1, l=1, c=1, volume_usd=1e9, observed_at=T + 100 * H, provider="fx")
    b = gecko.pool_basis_at(con, "solana", MINT, decision_time=T + 600)
    assert b["pool_address"] == "PA"
    assert gecko.pool_basis_at(con, "solana", "NO_SUCH_MINT", decision_time=T) is None


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                        "GIT_AUTHOR_DATE": "2027-01-16T00:00:00Z", "GIT_COMMITTER_DATE": "2027-01-16T00:00:00Z", "PATH": "/usr/bin:/bin"})


def test_universe_is_union_of_all_exports_and_keeps_rejected(tmp_path, con):
    repo = tmp_path / "repo"; repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "data" / "state").mkdir(parents=True)
    th = lambda m, t, st: {"mint": m, "created_at": t, "status": st, "score": 50, "fatal_flags_json": "[]", "snapshot_json": json.dumps({"price": 1.0})}
    v1 = {"_tables": {"tokens": [], "theses": [th("AAA", T, "WATCH"), th("BBB", T + 60, "WATCH")], "rejections": [{"mint": "RUG", "symbol": "R", "rejected_at": T + 30, "stage": "deep", "why_failed": "x", "evidence": "", "why_surfaced": ""}]}}
    v2 = {"_tables": {"tokens": [], "theses": [th("BBB", T + 60, "WATCH"), th("CCC", T + 3600, "NEAR ENTRY")], "rejections": []}}  # export trimmed AAA and RUG
    (repo / "data/state/latest.json").write_text(json.dumps(v1)); _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "v1")
    (repo / "data/state/latest.json").write_text(json.dumps(v2)); _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "v2")
    st = labstate.build_universe(con, repo, universe_id="u", ref="main")
    assert st["versions"] == 2 and st["inserted"] == 4
    mints = {(r["mint"], r["basis"]) for r in con.execute("SELECT mint, basis FROM bt_universe_members WHERE universe_id='u'")}
    assert mints == {("AAA", "THESIS"), ("BBB", "THESIS"), ("CCC", "THESIS"), ("RUG", "REJECTION")}
    first = con.execute("SELECT committed_by FROM bt_universe_members WHERE mint='BBB'").fetchall()
    assert len(first) == 1                                    # same record from two exports stored once
    again = labstate.build_universe(con, repo, universe_id="u", ref="main")
    assert again["inserted"] == 0                             # idempotent


def test_present_day_crawl_of_old_page_is_not_historical(con):
    old_pub = T - 200 * 86400
    r = captures.record_capture(con, collector="FIRECRAWL", source_url="https://www.Example.org/news/listing/?utm_source=x", text="Token X lists on Y",
                                captured_at=T, source_published_at=old_pub, published_confidence="PAGE_CLAIM")
    canon = r["canonical_origin"]
    assert canon == "https://example.org/news/listing"
    before = captures.captures_asof(con, canon, T - 100 * 86400)
    assert before["state"] == "UNKNOWN_AS_OF" and before["version"] is None
    after = captures.captures_asof(con, canon, T + 1)
    assert after["state"] == "OBSERVED" and after["late_capture"] is True


def test_cross_tool_duplicate_and_revision(con):
    a = captures.record_capture(con, collector="CRAWL4AI", source_url="https://example.org/a", text="Hello   world", captured_at=T)
    b = captures.record_capture(con, collector="MAXUN", source_url="https://www.example.org/a/", text="Hello world", captured_at=T + 60)
    assert a["new"] and not b["new"] and b["independent_confirmation"] is False and b["id"] == a["id"]
    c = captures.record_capture(con, collector="FIRECRAWL", source_url="https://example.org/a", text="Hello world (corrected)", captured_at=T + 3600)
    assert c["new"] and c["version"] == 2
    assert captures.captures_asof(con, a["canonical_origin"], T + 100)["version"]["content_hash"] == a["content_hash"]
    assert captures.captures_asof(con, a["canonical_origin"], T + 3601)["version"]["content_hash"] == c["content_hash"]
    with pytest.raises(ValueError):
        captures.record_capture(con, collector="FIRECRAWL", source_url="https://example.org/b", text="x", captured_at=T, mint="SomeMint", chain="solana")


def test_archive_proof_can_move_first_seen_earlier_but_page_date_cannot(con):
    with pytest.raises(Exception):
        captures.record_capture(con, collector="FIRECRAWL", source_url="https://example.org/c", text="x", captured_at=T, historical_asof_proof="INDEPENDENT_ARCHIVE")
    r = captures.record_capture(con, collector="FIRECRAWL", source_url="https://example.org/c", text="x", captured_at=T, source_published_at=T - 10 * H,
                                historical_asof_proof="INDEPENDENT_ARCHIVE", proof_observed_at=T - 5 * H)
    assert r["first_seen_at"] == T - 5 * H                   # archive capture time, not the page's own date (T-10H)


def test_reconciliation_flags_disagreement(con):
    for m, px in (("OK1", 1.05), ("BAD", 3.0)):
        store.record_universe_member(con, universe_id="u", chain="solana", mint=m, basis="THESIS", entered_at=T + 600, snapshot={"price": px})
        store.record_bar(con, chain="solana", mint=m, pool_address="P" + m, tf=H, start=T, o=1, h=1.1, l=0.9, c=1.0, volume_usd=10, observed_at=T + 10 * H, provider="fx")
    r = quality.reconcile_lab_vs_bars(con, "u")
    assert r["checked"] == 2 and r["inside_bar_range"] == 1 and r["outside_tolerance"] == 1 and r["worst"][0]["mint"] == "BAD"


def test_dataset_hash_changes_with_visible_data_only(con):
    store.record_bar(con, chain="solana", mint="M", pool_address="P", tf=H, start=T, o=1, h=1, l=1, c=1, volume_usd=1, observed_at=T + 2 * H, provider="fx")
    h1 = quality.dataset_hash(con, ["M"], cutoff=T + 2 * H)
    store.record_bar(con, chain="solana", mint="M", pool_address="P", tf=H, start=T, o=1, h=2, l=1, c=2, volume_usd=1, observed_at=T + 50 * H, provider="fx")
    assert quality.dataset_hash(con, ["M"], cutoff=T + 2 * H) == h1   # a later revision does not change an earlier cutoff's dataset
    assert quality.dataset_hash(con, ["M"]) != h1


def test_mint_integrity_flags_corrupted_copies_without_merging(con):
    real = "6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx"
    flipped = "6GmAFSYS4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx"          # one character case-flipped: valid length, different key
    short = "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"             # one character dropped: 31 bytes, not a key
    for i, m in enumerate((real, flipped, short, "MukLDtJ8Cx9DxLbeyLRSWPSposTMWuwHANbuaudpump")):
        store.record_universe_member(con, universe_id="u", chain="solana", mint=m, entered_at=T + i, basis="THESIS")
    r = quality.mint_integrity(con, "u")
    assert r["invalid_pubkey"] == [short]
    assert (real, flipped) in r["one_edit_pairs"] or (flipped, real) in r["one_edit_pairs"]
    assert len(store.universe_asof(con, "u", T + 10)) == 4                    # reported, never merged away


def test_resume_after_interrupted_bar_fetch_fetches_the_bars(con):
    """Real defect found in Phase 06: a run stopped between a mint's pool list and its bars marked the mint done."""
    from memelab.backtest.sources import corpus
    past = 1_780_000_000.0                                                     # 2026-05-28, safely closed bars
    pools = pools_body(("P9", "2026-05-01T00:00:00Z", 5000.0, "pumpswap", MINT))
    rows = [[past + i * H, 1.0, 1.1, 0.9, 1.05, 100.0] for i in range(5)]
    http1 = FakeHTTP([(200, pools)] + [(429, {})] * 5)                        # bars blocked after every retry
    s1 = corpus.build(con, [MINT], budget(), http_get=http1, k_pools=1)
    assert s1["pools_fetched"] == 1 and not corpus.already_fetched(con, MINT)
    http2 = FakeHTTP([(200, pools), (200, ohlcv_body(rows))])
    corpus.build(con, [MINT], budget(), http_get=http2, k_pools=1)
    assert con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE mint=?", (MINT,)).fetchone()[0] == 5
    assert corpus.already_fetched(con, MINT)
    http3 = FakeHTTP([])
    s3 = corpus.build(con, [MINT], budget(), http_get=http3, k_pools=1)
    assert s3["skipped_resume"] == 1 and http3.urls == []

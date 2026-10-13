"""Phase 21 (optional Prompt 21): YouTube Data API v3 adapter. Recorded synthetic fixtures only; no network, fixed clock,
temp DB and private folder.

Fixtures: tests/fixtures/social/youtube_data/ (invented channels, videos, caption tracks and sentences shaped like the
documented responses; generated once and committed). Video ids fxVideo01aA ... fxVideo10jJ:
  01 VOD, licensed transcript (two contracts in one cue, a ticker-only cue), contract in the description
  02 archived livestream, licensed SRT transcript with one cue past the end (drift); removed before run 2
  03 upcoming livestream with a licensed transcript: pending in run 1, archived in run 2
  04 VOD on the owned channel: captions.list (ASR en + standard es for English audio) and captions.download
  05 archived livestream on the owned channel, captions not ready in run 1 (delayed archive), ready in run 2
  06 unlisted (dropped)   07 configured video of another channel, licensed transcript in Spanish for English audio
  08 owned channel, captions.list 403 (not permitted)   09 VOD, no transcript route   10 new upload in run 2
"""
import json
import sqlite3
from pathlib import Path

import pytest

from memelab import cli, db
from memelab.social import ingest as I
from memelab.social import youtube_data as Y
from memelab.social.api_common import TextSink, extract_after_ingest
from memelab.social.feed_core import safe_url

ROOT = Path(__file__).resolve().parent.parent
FXD = ROOT / "tests" / "fixtures" / "social" / "youtube_data"
CONFIG, RUN1, RUN2, QUOTA = (FXD / "fx_youtube_config.json", FXD / "fx_youtube_run1.json", FXD / "fx_youtube_run2.json",
                             FXD / "fx_youtube_quota.json")
BODIES = ROOT / "tests" / "fixtures" / "social" / "resolve" / "fx_providers.json"
T1, T2 = 1791676800.0, 1791763200.0          # 2026-10-11 and -12 00:00Z
KEY = "fixtureYoutubeKeyNotReal_0123456789"
OAUTH = "fixtureOauthTokenNotReal_0123456789"
M1, M5 = "8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ", "urqBccf819k8ttGdxBnfxDfRR7yH62RJxww3QnxJA5v"
CA, CB, CD = "UCfxLongAnalyst00000001A", "UCfxSecondShow000000002B", "UCfxOtherCreator0000003D"
V = {1: "fxVideo01aA", 2: "fxVideo02bB", 3: "fxVideo03cC", 4: "fxVideo04dD", 5: "fxVideo05eE", 6: "fxVideo06fF",
     7: "fxVideo07gG", 8: "fxVideo08hH", 9: "fxVideo09iI", 10: "fxVideo10jJ"}
K = lambda pid: f"youtube:{pid}"


@pytest.fixture()
def dbp(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    return p


def raw_cfg():
    return json.loads(CONFIG.read_text())


def cfg(**over):
    c = raw_cfg()
    c.update(over)
    return _load(c)


def _load(c):
    # licensed transcript paths are relative to the fixture folder
    for e in c["transcripts"]["licensed"]:
        e["file"] = str(FXD / Path(e["file"]).name)
    return Y.load_config(c)


RUNS = iter(range(1, 10_000))


def run(dbp, fixture, config=None, now=T1, key=KEY, oauth=OAUTH, sink=None, sleeps=None):
    tr = fixture if isinstance(fixture, Y.FixtureTransport) else Y.FixtureTransport(fixture)
    rid = f"y{now}_{next(RUNS)}"
    ad = Y.YouTubeDataAdapter(config or cfg(), tr, key, dbp, oauth_token=oauth, run_id=rid, mode="fixture", clock=lambda: now,
                              sleep=(sleeps.append if sleeps is not None else (lambda s: None)), text_sink=sink)
    out = I.ingest(ad, dbp, now=now, run_id=rid)
    return out, tr, ad


def bodies():
    return json.loads(BODIES.read_text())["bodies"]


def q(dbp, sql, *args):
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    out = [dict(r) for r in con.execute(sql, args)]
    con.close()
    return out


def items(dbp):
    return {r["provider_item_id"]: r for r in q(dbp, "SELECT * FROM social_items WHERE platform='youtube'")}


def claims(dbp):
    out = {}
    for r in q(dbp, "SELECT c.item_key, a.tokens_json FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id"):
        out.setdefault(r["item_key"], []).extend(t.get("contract") or f"ticker:{t.get('symbol') or t.get('mention')}"
                                                 for t in json.loads(r["tokens_json"]))
    return out


def all_text(dbp):
    con = sqlite3.connect(dbp)
    out = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for row in con.execute(f"SELECT * FROM {t}"):
            out.extend(str(v) for v in row if v is not None)
    con.close()
    return "\n".join(out)


def call(argv):
    try:
        cli.main(argv)
    except SystemExit as e:
        return e.code
    return 0


def both_runs(dbp, extract=True):
    s1 = TextSink() if extract else None
    o1, t1, a1 = run(dbp, RUN1, sink=s1)
    e1 = extract_after_ingest(dbp, s1, now=T1, bodies=bodies()) if extract else None
    p1 = Y.purge(dbp, now=T1)
    s2 = TextSink() if extract else None
    o2, t2, a2 = run(dbp, RUN2, now=T2, sink=s2)
    e2 = extract_after_ingest(dbp, s2, now=T2, bodies=bodies()) if extract else None
    p2 = Y.purge(dbp, now=T2)
    return (o1, t1, a1, e1, p1), (o2, t2, a2, e2, p2)


# ---------- config and gates ----------

def test_config_refuses_credentials_translation_downloaders_and_weak_permission():
    for bad in ({"api_key": "x"}, {"quota": {"token": "x"}}, {"transcripts": {"tlang": "en"}}, {"yt_dlp": True},
                {"transcripts": {"timedtext": "x"}}):
        with pytest.raises(ValueError):
            Y.load_config(raw_cfg() | bad)
    c = raw_cfg()
    c["transcripts"]["licensed"][0]["permission"] = {"basis": "found_online", "reference": "none"}
    with pytest.raises(ValueError, match="permission"):
        Y.load_config(c)
    c = raw_cfg()
    c["transcripts"]["licensed"][0]["file"] = "https://example.com/t.vtt"
    with pytest.raises(ValueError, match="no URL"):
        Y.load_config(c)
    for chans in ([{"id": "UCshort"}], [{"id": CA, "handle": "@x_y_z"}], [{"id": CA}, {"id": CA}]):
        with pytest.raises(ValueError):
            Y.load_config(raw_cfg() | {"channels": chans})
    c = Y.load_config(raw_cfg() | {"quota": {"daily_units": 99999}, "retention_days": 90, "refresh_after_days": 60})
    assert c.daily_units == 10000 and c.retention_days == 30.0 and c.refresh_after_days == 29.0


def test_gates_terms_credentials_make_no_request(dbp):
    tr = Y.FixtureTransport(RUN1)
    out, _, ad = run(dbp, tr, config=cfg(terms_review={"accepted": False}))
    assert tr.calls == [] and out["status"] == "FAILED"
    errs = {r["error"] for r in q(dbp, "SELECT error FROM social_connector_health")}
    assert all(e.startswith("terms_review_missing") for e in errs)
    tr = Y.FixtureTransport(RUN1)
    out, _, _ = run(dbp, tr, key=None, now=T1 + 1)
    assert tr.calls == [] and out["status"] == "FAILED"
    assert any(r["error"].startswith("credentials_missing") for r in q(dbp, "SELECT error FROM social_connector_health"))


# ---------- run 1: metadata, transcripts, statuses ----------

def test_run1_stores_ids_times_and_hashes_only_and_reads_a_duplicate_channel_once(dbp):
    sleeps = []
    out, tr, ad = run(dbp, RUN1, sleeps=sleeps)
    assert out["status"] == "PARTIAL" and out["counts"]["created"] == 12 and out["counts"]["quarantined"] == 0
    it = items(dbp)
    assert set(it) == {V[1], V[2], V[3], V[4], V[5], V[7], V[8], V[9], f"{V[1]}_t180000_192000", f"{V[1]}_t480000_483000",
                       f"{V[2]}_t1800000_1808000", f"{V[4]}_t120000_132000"}
    assert V[6] not in it and ad.dropped["not_public"] == 1                     # unlisted is not public
    assert ad.dropped["duplicate_channel"] == 1
    assert sum(1 for c in tr.calls if c["path"] == "/playlistItems" and c["params"]["playlistId"].startswith("UUfxLong")) == 1
    assert sleeps and len([c for c in tr.calls if c["path"] == "/playlistItems"]) == 3     # 503 retried once
    # quota units: 3 channel lookups, 3 playlist pages, 3 video batches, captions.list x2 (50), one download (200)
    assert ad.quota_units == 309
    spend = q(dbp, "SELECT resources_json FROM social_api_spend WHERE connector LIKE 'youtube_data:%'")
    assert sum(json.loads(r["resources_json"])["quota_units"] for r in spend) == 309
    assert all(not c["params"].get("tlang") and "statistics" not in c["params"].get("part", "") for c in tr.calls)
    acc = q(dbp, "SELECT provider_user_id, handle FROM social_accounts WHERE platform='youtube' ORDER BY 1")
    assert [a["provider_user_id"] for a in acc] == sorted([CA, CB, CD])
    assert {a["handle"] for a in acc} == {"fx_long_analyst", "fx_second_show", None}     # the store keeps handles without @
    obs = q(dbp, "SELECT o.metrics_json, o.summary, o.content_hash, i.original_url FROM social_observations o JOIN social_items i "
                 "ON i.item_key=o.item_key WHERE i.platform='youtube'")
    assert all(o["metrics_json"] is None and o["summary"] is None and len(o["content_hash"]) == 64 for o in obs)
    assert it[f"{V[1]}_t180000_192000"]["original_url"] == f"https://www.youtube.com/watch?v={V[1]}&t=180s"
    txt = all_text(dbp)
    assert "Invented" not in txt and "palabras" not in txt and "fixture channel" not in txt


def test_transcript_statuses_missing_captions_and_unavailable_authorized_routes(dbp):
    _, tr, ad = run(dbp, RUN1)
    assert ad.transcripts == {V[1]: "DONE", V[2]: "DONE", V[3]: "PENDING_BROADCAST", V[4]: "DONE", V[5]: "PENDING_ARCHIVE",
                              V[7]: "UNAVAILABLE_LANGUAGE_MISMATCH", V[8]: "UNAVAILABLE_NOT_PERMITTED",
                              V[9]: "UNAVAILABLE_NO_AUTHORIZED_ROUTE"}
    # no caption call for a video of a channel the lab does not own, nor for one whose captions are not ready
    asked = {c["params"].get("videoId") for c in tr.calls if c["path"] == "/captions"}
    assert asked == {V[4], V[8]}
    h = {r["connector"]: r for r in q(dbp, "SELECT connector, status, error FROM social_connector_health")}
    assert h["youtube_data:transcript:captions_api"]["status"] == "BLOCKED"
    assert "not_permitted" in h["youtube_data:transcript:captions_api"]["error"]
    cur = {r["scope"]: r["last_status"] for r in q(dbp, "SELECT scope, last_status FROM social_source_cursors "
                                                         "WHERE connector='youtube_data:transcript'")}
    assert cur[V[9]] == "UNAVAILABLE_NO_AUTHORIZED_ROUTE" and cur[V[5]] == "PENDING_ARCHIVE"
    # the metadata of a video without a transcript is still there and dated by its publication
    assert items(dbp)[V[9]]["published_at_basis"] == "PROVIDER"


def test_multi_token_snippet_ticker_only_and_description_mentions(dbp):
    s = TextSink()
    run(dbp, RUN1, sink=s)
    ex = extract_after_ingest(dbp, s, now=T1, bodies=bodies())
    assert ex["extracted"] == 12 and ex["claims"] == 8 and len(s) == 0
    c = claims(dbp)
    assert sorted(c[K(f"{V[1]}_t180000_192000")]) == sorted([M1, M5])         # two tokens in one snippet: two claims
    assert c[K(V[1])] == [M1] and c[K(V[9])] == [M5] and c[K(f"{V[4]}_t120000_132000")] == [M5]
    tick = c[K(f"{V[1]}_t480000_483000")]
    assert len(tick) == 1 and not tick[0].startswith(("8", "u"))                # ticker-only: no contract
    st = q(dbp, "SELECT r.status FROM social_token_resolutions r WHERE r.item_key=?", K(f"{V[1]}_t480000_483000"))
    assert [r["status"] for r in st] == ["unresolved"]


def test_language_mismatch_is_refused_and_asr_is_noted(dbp):
    _, tr, _ = run(dbp, RUN1)
    assert not any(k.startswith(K(V[7]) + "_t") for k in (r["item_key"] for r in q(dbp, "SELECT item_key FROM social_items")))
    h = q(dbp, "SELECT error FROM social_connector_health WHERE connector='youtube_data:transcript:licensed_file'")[0]["error"]
    assert "language_uncertain" in h
    # English audio: the English ASR track wins over the Spanish standard track (a translation is not what was said)
    assert [c["path"] for c in tr.calls if c["path"].startswith("/captions/")] == ["/captions/fxCapTrack4en"]
    note = q(dbp, "SELECT p.terms_note FROM social_observation_provenance p JOIN social_observations o ON o.id=p.observation_id "
                 "WHERE o.item_key=?", K(f"{V[4]}_t120000_132000"))
    assert note and "ASR" in note[0]["terms_note"] and "language MATCH" in note[0]["terms_note"]
    c = raw_cfg()
    c["transcripts"]["allow_language_mismatch"] = True
    assert _load(c).allow_language_mismatch is True


def test_timestamp_drift_and_livestream_offsets(dbp):
    s = TextSink()
    _, _, ad = run(dbp, RUN1, sink=s)
    extract_after_ingest(dbp, s, now=T1, bodies=bodies())
    it = items(dbp)
    seg = it[f"{V[2]}_t1800000_1808000"]
    start = Y.store.to_utc("2026-10-10T16:00:00Z")
    assert seg["published_at"] == start + 1800 and seg["published_at_basis"] == "PARSED_RELATIVE"
    assert ad.dropped["drift_cues"] == 1
    # the drifted cue named M5; nothing from it was kept
    assert claims(dbp)[K(f"{V[2]}_t1800000_1808000")] == [M1]
    assert not any(k.startswith(f"{V[2]}_t48") for k in it)
    # a VOD snippet is dated by the video's publication, never by a guessed spoken time
    assert it[f"{V[1]}_t180000_192000"]["published_at"] == it[V[1]]["published_at"]
    assert it[f"{V[1]}_t180000_192000"]["published_at_basis"] == "PROVIDER"


# ---------- run 2: delayed archive, refresh, removal ----------

def test_no_transcript_before_broadcast_and_delayed_archive(dbp):
    (o1, _, a1, _, _), (o2, t2, a2, e2, p2) = both_runs(dbp)
    assert a1.transcripts[V[3]] == "PENDING_BROADCAST" and a2.transcripts[V[3]] == "DONE"
    assert a1.transcripts[V[5]] == "PENDING_ARCHIVE" and a2.transcripts[V[5]] == "DONE"
    it = items(dbp)
    s3 = it[f"{V[3]}_t300000_312000"]
    start3 = Y.store.to_utc("2026-10-11T20:05:00Z")
    assert s3["published_at"] == start3 + 300 and s3["first_observed_at"] >= Y.store.to_utc("2026-10-11T21:00:00Z")
    assert s3["published_at"] >= start3                       # never dated before the broadcast
    s5 = it[f"{V[5]}_t600000_612000"]
    assert s5["published_at"] == Y.store.to_utc("2026-10-10T21:10:00Z") and s5["first_observed_at"] == T2
    # pending videos are re-read through videos.list, not rediscovered
    assert any(c["path"] == "/videos" and c["params"]["id"] == f"{V[3]},{V[5]}" for c in t2.calls)
    # a snapshot of the day before the stream holds nothing from its transcript
    assert call(["social", "narrative-snapshot", "--day", "2026-10-10", "--tz", "UTC", "--db", str(dbp), "--now", str(T2)]) == 0
    keys = {r["item_key"] for r in q(dbp, "SELECT item_key FROM social_narrative_members")}
    assert keys and K(f"{V[3]}_t300000_312000") not in keys


def test_refresh_purges_removed_video_and_its_snippets_and_restarts_the_clock(dbp):
    (o1, _, _, _, _), (o2, t2, a2, e2, p2) = both_runs(dbp)
    assert o2["status"] == "OK" and a2.quota_units == 258
    rc = [c for c in t2.calls if c["path"] == "/videos"][-1]
    assert rc["params"]["id"] == ",".join(V[i] for i in (1, 2, 4, 5, 7, 8, 9))
    assert p2["gone"]["items_purged"] == 2                     # video 02 and its one snippet
    gone = q(dbp, "SELECT item_key FROM social_observations WHERE retrieval_status='NOT_FOUND'")
    assert {g["item_key"] for g in gone} == {K(V[2]), K(f"{V[2]}_t1800000_1808000")}
    assert all(r["content_hash"] is None for r in q(dbp, "SELECT content_hash FROM social_observations WHERE item_key=?", K(V[2])))
    assert q(dbp, "SELECT COUNT(*) n FROM social_claim_spans s JOIN social_claims c ON c.id=s.claim_id WHERE c.item_key=?",
             K(f"{V[2]}_t1800000_1808000"))[0]["n"] == 0
    # refreshed videos got a new dated sighting; their words were not analysed twice
    assert e2["skipped_already_extracted"] == 7
    assert q(dbp, "SELECT COUNT(*) n FROM social_observations WHERE item_key=?", K(V[1]))[0]["n"] == 2
    h = Y.health(CONFIG, dbp, env={}, now=T2)
    assert h["retention"]["videos_stored"] == 9 - 1 + 1 and h["retention"]["past_retention_unpurged"] == 0


def test_thirty_day_expiry_clears_derived_data_of_unrefreshed_videos(dbp):
    both_runs(dbp)
    before = q(dbp, "SELECT COUNT(*) n FROM social_claim_spans")[0]["n"]
    out = Y.purge(dbp, now=T2 + 31 * 86400)
    assert out["expired"]["videos_past_retention"] == 9 and before > 0
    assert q(dbp, "SELECT COUNT(*) n FROM social_claim_spans")[0]["n"] == 0
    assert q(dbp, "SELECT COUNT(*) n FROM social_observations o JOIN social_items i ON i.item_key=o.item_key "
                  "WHERE i.platform='youtube' AND o.content_hash IS NOT NULL")[0]["n"] == 0
    assert Y.purge(dbp, now=T2 + 31 * 86400)["expired"]["items_purged"] == 0      # idempotent
    # within 30 days nothing expires
    assert Y.purge(dbp, now=T2 + 29 * 86400)["expired"]["videos_past_retention"] == 0


def test_rerun_dedupes_videos_snippets_and_transcript_work(dbp):
    run(dbp, RUN1)
    n = q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"]
    out, tr, ad = run(dbp, RUN1)
    assert out["counts"]["created"] == 0 and q(dbp, "SELECT COUNT(*) n FROM social_observations")[0]["n"] == n
    assert not any(c["path"].startswith("/captions") for c in tr.calls)          # DONE / UNAVAILABLE are not retried
    assert not any(c["path"] == "/videos" and V[1] in c["params"]["id"] for c in tr.calls)   # cursor: nothing new


# ---------- quota ----------

def test_quota_exceeded_stops_the_run_until_midnight_pacific(dbp):
    out, tr, ad = run(dbp, QUOTA)
    assert out["status"] == "FAILED" and len(tr.calls) == 1 and ad.stopped.startswith("quota_exceeded")
    reset = q(dbp, "SELECT rate_limit_reset_at FROM social_source_cursors WHERE connector='youtube_data:quota'")[0]["rate_limit_reset_at"]
    assert reset == Y.store.to_utc("2026-10-11T07:00:00Z")     # T1 is 2026-10-10 17:00 PDT; next PT midnight
    tr2 = Y.FixtureTransport(QUOTA)
    out, _, _ = run(dbp, tr2, now=T1 + 3600)
    assert tr2.calls == [] and out["status"] == "FAILED"
    h = Y.health(CONFIG, dbp, env={Y.KEY_ENV: KEY}, now=T1 + 3600)
    assert h["status"] == "quota_exhausted" and h["quota_reset_at"].startswith("2026-10-11T07:00")
    assert Y.health(CONFIG, dbp, env={Y.KEY_ENV: KEY}, now=reset + 1)["status"] == "ready"


def test_quota_caps_per_run_and_daily(dbp):
    c = raw_cfg()
    c["quota"] = {"max_units_per_run": 5, "daily_units": 10000}
    out, tr, ad = run(dbp, RUN1, config=_load(c))
    assert ad.quota_units <= 5 and ad.stopped and "quota cap 5 units per run" in ad.stopped
    assert not any(x["path"].startswith("/captions") for x in tr.calls)
    c["quota"] = {"max_units_per_run": 1000, "daily_units": 3}
    tr = Y.FixtureTransport(RUN1)
    out, _, ad = run(dbp, tr, config=_load(c), now=T1 + 60)      # same PT day: 5 units already used
    assert tr.calls == [] and "daily quota cap 3" in ad.stopped


def test_pacific_quota_day_handles_daylight_saving():
    s, e = Y.pt_day(Y.store.to_utc("2026-11-01T12:00:00Z"))        # fall back day: 25 hours
    assert e - s == 25 * 3600
    s, e = Y.pt_day(Y.store.to_utc("2026-03-08T12:00:00Z"))        # spring forward: 23 hours
    assert e - s == 23 * 3600


# ---------- parsing ----------

def test_caption_parsing_ids_and_durations():
    vtt = "WEBVTT\n\nNOTE x\n\n1\n00:00:01.500 --> 00:00:03.000 align:start\n<c>hello</c> <00:00:02.000>there\n\n00:01.000 --> 00:00.500\nreversed\n"
    assert Y.parse_cues(vtt) == [{"start_ms": 1500, "end_ms": 3000, "text": "hello there"}]
    srt = "1\n01:02:03,004 --> 01:02:05,000\nline one\nline two\n"
    assert Y.parse_cues(srt) == [{"start_ms": 3723004, "end_ms": 3725000, "text": "line one line two"}]
    assert Y.parse_segment_id(Y.segment_id("a_b-c_t1234", 5, 9)) == ("a_b-c_t1234", 5, 9)
    assert Y.parse_segment_id("short_t1_2") is None
    assert Y.parse_duration("PT1H2M3S") == 3723 and Y.parse_duration("P1DT1S") == 86401 and Y.parse_duration("P0D") == 0
    assert Y.parse_duration("PT") is None and Y.parse_duration(None) is None
    cues = [{"start_ms": 0, "end_ms": 1000, "text": "a"}, {"start_ms": 1000, "end_ms": 2000, "text": f"x {M1}"},
            {"start_ms": 60000, "end_ms": 61000, "text": "far away"}]
    assert Y.snippet_windows(cues, 1) == [(0, 1)]                  # the distant cue is not quotation context
    assert Y.language_check("en-US", "en") == "MATCH" and Y.language_check("es", "en") == "MISMATCH"
    assert Y.language_check("en", None) == "UNVERIFIED"


def test_timing_never_places_an_unfinished_broadcast():
    base = {"published_at": 1.0, "is_broadcast": True, "actual_start": 10.0, "actual_end": None, "duration_s": None}
    assert Y.timing_for(base | {"live": "upcoming"})[0] is None
    assert Y.timing_for(base | {"live": "live"})[0] is None
    assert Y.timing_for(base | {"live": "none"})[1].startswith("PENDING_BROADCAST")
    t, _ = Y.timing_for(base | {"live": "none", "actual_end": 70.0})
    assert t.kind == "LIVE" and t.public_at == 10.0 and t.media_s == 60.0


# ---------- secrets ----------

def test_secrets_never_reach_logs_errors_or_repr(dbp, caplog):
    fx = json.loads(QUOTA.read_text())
    fx["exchanges"] = [{"recorded_at": "2026-10-11T00:00:00Z", "request": fx["exchanges"][0]["request"],
                        "raise": "connection reset while sending key={secret}"}] * 3
    caplog.set_level("DEBUG")
    out, tr, ad = run(dbp, Y.FixtureTransport(fx))
    assert KEY not in repr(ad) and KEY not in caplog.text and KEY not in all_text(dbp)
    real = "AIza" + "B" * 35
    assert real not in I.redact(f"GET /videos?key={real}&part=id") and "ya29." + "x" * 30 not in I.redact("Bearer ya29." + "x" * 30)


# ---------- feed link ----------

def test_feed_keeps_only_the_youtube_video_id_and_timepoint():
    assert safe_url(f"https://www.youtube.com/watch?v={V[1]}&t=180s") == f"https://www.youtube.com/watch?v={V[1]}&t=180s"
    assert safe_url(f"https://www.youtube.com/watch?v={V[1]}&list=PL1") == "https://www.youtube.com/watch"
    assert safe_url(f"https://example.com/watch?v={V[1]}") == "https://example.com/watch"
    assert safe_url("https://t.me/somechannel/5?x=1") == "https://t.me/somechannel/5"


# ---------- CLI flow ----------

def test_cli_fixture_flow_extract_narrative_brief_purge_and_live_refusal(dbp, capsys, monkeypatch):
    """Source -> storage -> claim -> narrative -> report, on the fixtures, through the real commands."""
    monkeypatch.delenv(Y.KEY_ENV, raising=False)
    monkeypatch.delenv(Y.OAUTH_ENV, raising=False)
    code = call(["social", "youtube-ingest", "--config", str(CONFIG), "--fixture", str(RUN1), "--extract", "--bodies", str(BODIES),
                 "--db", str(dbp), "--now", str(T1), "--run-id", "cli_yt"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["mode"] == "fixture" and out["counts"]["created"] == 12 and out["status"] == "PARTIAL"
    assert out["extraction"]["claims"] == 8 and out["quota_units"] == 309 and out["transcripts"][V[9]] == "UNAVAILABLE_NO_AUTHORIZED_ROUTE"
    call(["social", "narrative-snapshot", "--day", "2026-10-10", "--tz", "UTC", "--db", str(dbp), "--now", str(T1 + 3600)])
    snap = json.loads(capsys.readouterr().out)
    assert sorted(snap["summary"]["new"]) == sorted([f"ca:solana:{M1}", f"ca:solana:{M5}"])
    cl = {r["cluster_key"]: r for r in q(dbp, "SELECT * FROM social_narrative_clusters")}
    assert cl[f"ca:solana:{M1}"]["independent_source_count"] == 2      # channel A (video + snippet = one source) and D
    call(["social", "brief", "--db", str(dbp), "--as-of", "2026-10-11T01:00:00+00:00", "--tz", "UTC", "--include-fixtures"])
    brief = capsys.readouterr().out
    assert "FIXTURE DEMO" in brief and "Priority: HIGH" in brief and f"https://www.youtube.com/watch?v={V[1]}&t=180s" in brief
    assert "Invented" not in brief and "FXA" in brief
    assert call(["social", "youtube-ingest", "--config", str(CONFIG), "--fixture", str(QUOTA), "--db", str(dbp), "--now", str(T1)]) == 1
    capsys.readouterr()
    assert call(["social", "youtube-purge", "--db", str(dbp), "--now", str(T1 + 40 * 86400)]) == 0
    assert json.loads(capsys.readouterr().out)["expired"]["videos_past_retention"] == 8
    call(["social", "sources", "--db", str(dbp)])
    rows = {r["connector"]: r for r in json.loads(capsys.readouterr().out)["connectors"]}
    assert rows["youtube_data"]["status"] == "not_configured" and rows["youtube_data"]["live_requests"] == 0
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    assert call(["social", "youtube-ingest", "--config", str(CONFIG), "--db", str(dbp)]) == 1
    r = json.loads(capsys.readouterr().out)
    assert r["status"] == "NOT_RUN" and r["reason"] == "credentials_missing" and r["network_calls_made"] == 0
    assert call(["social", "youtube-health", "--config", str(CONFIG), "--db", str(dbp)]) == 1
    assert json.loads(capsys.readouterr().out)["live_evidence"]["requests"] == 0


def test_example_config_loads_and_is_off_by_default(dbp):
    ex = ROOT / "docs" / "social-intelligence" / "youtube_data.example.json"
    c = Y.load_config(ex)
    assert not c.terms_accepted and not c.captions_api and not c.licensed and c.retention_days == 30
    assert Y.health(ex, dbp, env={Y.KEY_ENV: KEY})["status"] == "not_configured"
    raw = json.loads(ex.read_text()) | {"channels": [{"id": CA}]}
    assert Y.health(None, dbp)["status"] == "not_configured"
    p = dbp.parent / "c.json"
    p.write_text(json.dumps(raw))
    assert Y.health(p, dbp, env={Y.KEY_ENV: KEY})["status"] == "terms_review_missing"

"""YouTube Data API v3 adapter (Phase 21, optional source): channel and video metadata, and transcript snippets only
where an authorized route exists. Periodic contextual intelligence, not launch detection.

Contract read 2026-10-13 (docs/social-intelligence/YOUTUBE_21.md has the sources, quotes and gaps):

  GET https://www.googleapis.com/youtube/v3/channels       id=<UC..,..> or forHandle=@x; part=snippet,contentDetails,status
                                                            -> contentDetails.relatedPlaylists.uploads; 1 unit
  GET .../playlistItems   playlistId=<uploads>, part=contentDetails, maxResults 0-50, pageToken
                          -> contentDetails.videoId, videoPublishedAt; 1 unit; no documented order
  GET .../videos          id=<up to 50>, part=snippet,contentDetails,status,liveStreamingDetails; 1 unit
                          snippet.publishedAt ("might be different than the time that the video was uploaded"),
                          snippet.liveBroadcastContent live|none|upcoming, defaultAudioLanguage, contentDetails.duration,
                          contentDetails.caption, liveStreamingDetails.actualStartTime / actualEndTime, status.privacyStatus
  GET .../captions        videoId=..., part=snippet; OAuth scope youtube.force-ssl; 50 units
  GET .../captions/{id}   tfmt=vtt; OAuth; "requires the user to have permission to edit the video"; 200 units
                          (tlang = machine translation: never requested here)
  Quota: 10,000 units per day for these endpoints, reset at midnight Pacific Time; every request costs at least 1 unit,
  invalid ones included. 403 quotaExceeded when used up. search.list (separate 100-call bucket) is not used.
  Policies (YouTube API Services Developer Policies): non-authorized data may be stored at most 30 days, then refreshed
  or deleted (III.E.4); no downloading, caching or scraping of audiovisual content (III.E.1, III.E.6); no new or derived
  metrics from API data (III.E.4.h); aggregation across content owners restricted (III.E.2, open decision D-146).

So, for videos the lab does not own, there is no authorized transcript: captions.download needs edit permission and
anything else (timedtext URLs, downloaders, scraping the player) is prohibited. Transcript routes, both off by default:
  captions_api   OAuth token in YOUTUBE_OAUTH_TOKEN, only for channels listed as owned/editable in the config
  licensed_file  a WebVTT or SRT file the operator supplies, with a recorded permission basis and reference
Without one, a video is metadata only and its transcript status says why (no_authorized_route).

What is stored (D-010, D-013, D-016): video id, channel id and handle, provider times, live state, a hash of
title + description (words hashed in memory and dropped), and per transcript snippet a hash of the snippet words.
No titles, descriptions, captions, thumbnails, view/like/comment counts (the policy forbids keeping statistics beyond
30 days and deriving metrics from them; the lab does not need them). Text reaches claim extraction only in memory
(TextSink, D-130).

Transcript snippets are inbound/3 items with provider id <video>_t<start ms>_<end ms>: the cue that names a token
plus `context_cues` cues on each side (quotation context), the URL carries the timepoint (&t=<s>s). published_at is the
time the words became public, never a guessed spoken time:
  uploaded or premiered video  -> the video's publishedAt (basis PROVIDER); the words may have been recorded earlier
  archived livestream          -> actualStartTime + cue offset (basis PARSED_RELATIVE: derived, +/- drift), clamped to
                                  actualEndTime; only after actualEndTime exists. Upcoming or live broadcasts get no
                                  transcript (PENDING_BROADCAST), so a later transcript can never be dated before its
                                  broadcast.
Cues past the media duration plus `drift_tolerance_seconds` are dropped and counted (timestamp drift).
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo

from . import store
from .api_common import (FixtureMiss, FixtureTransport as _FT, HttpResponse, RequestGuard, TextSink, clear_item_keys, connect,
                         get_cursor, iso, purge_gone_items, save_cursor, scrub, units_committed)
from .identity import extract_mentions
from .ingest import INBOUND_SCHEMA_V3, Budget, SourceUnit, TransientError, canonical_sha, log_event, redact, with_retries

PLATFORM = "youtube"
KEY_ENV, OAUTH_ENV = "YOUTUBE_API_KEY", "YOUTUBE_OAUTH_TOKEN"
CONFIG_SCHEMA = "memelab.youtube_data.config/1"
FIXTURE_SCHEMA = "memelab.youtube_data.fixture/1"
CONTRACT_VERIFIED = "2026-10-13"
API_HOST = "https://www.googleapis.com/youtube/v3"
ENDPOINTS = {"channels": "/channels", "playlist_items": "/playlistItems", "videos": "/videos", "captions": "/captions",
             "caption_download": "/captions/{id}"}
QUOTA_UNITS = {"channels": 1, "playlist_items": 1, "videos": 1, "captions": 50, "caption_download": 200}
QUOTA_ZONE = ZoneInfo("America/Los_Angeles")      # "Daily quotas reset at midnight Pacific Time (PT)"
FORBIDDEN_CONFIG_KEYS = {"key", "api_key", "apikey", "token", "oauth_token", "access_token", "refresh_token", "client_secret",
                         "secret", "password", "tlang", "translate", "translation_language", "downloader", "yt_dlp", "timedtext"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_\-]{11}$")
CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_\-]{22}$")
HANDLE_RE = re.compile(r"^@[A-Za-z0-9._\-]{3,30}$")
SEG_ID = re.compile(r"^([A-Za-z0-9_\-]{11})_t(\d{1,9})_(\d{1,9})$")
LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
PERMISSION_BASES = ("own_channel", "creator_written_permission")
VISIBILITY = {
    "channel": "YouTube Data API v3 uploads playlist of one configured public channel: metadata only (ids, times, live "
               "state, a hash of title and description); no statistics kept; stored at most 30 days unless refreshed",
    "videos": "YouTube Data API v3 videos.list for configured or pending videos: metadata only; no statistics kept",
    "recheck": "YouTube Data API v3 videos.list refresh of stored videos (30-day rule): a missing or non-public video "
               "is NOT_FOUND and its derived data is purged",
}


def segment_id(video_id: str, start_ms: int, end_ms: int) -> str:
    return f"{video_id}_t{int(start_ms)}_{int(end_ms)}"


def parse_segment_id(pid: str) -> tuple[str, int, int] | None:
    m = SEG_ID.match(pid or "")
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def parse_duration(v: Any) -> float | None:
    """ISO 8601 duration as YouTube gives it (PT1H2M3S, P1DT2H) -> seconds, or None."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", v or "")
    if not m or v in ("P", "PT"):
        return None
    d, h, mi, s = m.groups()
    return int(d or 0) * 86400 + int(h or 0) * 3600 + int(mi or 0) * 60 + float(s or 0)


def pt_day(t: float) -> tuple[float, float]:
    """Start and end (epoch seconds) of the Pacific Time quota day containing t."""
    d = datetime.fromtimestamp(t, QUOTA_ZONE).date()
    start = datetime(d.year, d.month, d.day, tzinfo=QUOTA_ZONE)
    nxt = d + timedelta(days=1)
    return start.timestamp(), datetime(nxt.year, nxt.month, nxt.day, tzinfo=QUOTA_ZONE).timestamp()


def _lang(tag: Any) -> str | None:
    return tag.split("-")[0].lower() if isinstance(tag, str) and LANG_RE.match(tag) else None


# ---------- captions (WebVTT / SRT) ----------

_TS = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{3})")
_TAG = re.compile(r"<[^>]{0,200}>")


def _ts(s: str) -> int | None:
    m = _TS.fullmatch(s.strip())
    if not m:
        return None
    h, mi, se, ms = m.groups()
    return ((int(h or 0) * 60 + int(mi)) * 60 + int(se)) * 1000 + int(ms)


def parse_cues(raw: str) -> list[dict]:
    """WebVTT or SRT -> [{start_ms, end_ms, text}] in file order. Styling tags are removed; NOTE, STYLE and REGION
    blocks are skipped; a cue with an unreadable or reversed time is dropped."""
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", (raw or "").replace("﻿", "")):
        lines = [x for x in block.strip().splitlines()]
        if not lines or lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        i = next((k for k, x in enumerate(lines) if "-->" in x), None)
        if i is None:
            continue
        a, _, b = lines[i].partition("-->")
        start, end = _ts(a), _ts(b.strip().split(" ")[0])
        text = " ".join(_TAG.sub("", x).strip() for x in lines[i + 1:]).strip()
        if start is None or end is None or end < start or not text:
            continue
        cues.append({"start_ms": start, "end_ms": end, "text": text})
    return cues


def snippet_windows(cues: list[dict], context: int, gap_ms: int = 15000) -> list[tuple[int, int]]:
    """Index ranges [a, b] of cue windows around every cue that names a token (address, link or cashtag): up to
    `context` cues on each side, each neighbour within `gap_ms` of the cue next to it (quotation context, not a
    distant part of the video). Windows that share a cue are merged. Cues without a candidate are never kept."""
    hits = [i for i, c in enumerate(cues) if extract_mentions(c["text"])]
    out: list[list[int]] = []
    for i in hits:
        a = i
        while a > 0 and i - a < context and cues[a]["start_ms"] - cues[a - 1]["end_ms"] <= gap_ms:
            a -= 1
        b = i
        while b < len(cues) - 1 and b - i < context and cues[b + 1]["start_ms"] - cues[b]["end_ms"] <= gap_ms:
            b += 1
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


# ---------- config ----------

@dataclass
class ChannelRef:
    channel_id: str | None = None
    handle: str | None = None

    @property
    def label(self) -> str:
        return self.channel_id or self.handle or "?"


@dataclass
class LicensedTranscript:
    video_id: str
    path: Path
    fmt: str
    language: str
    basis: str
    reference: str


@dataclass
class YouTubeConfig:
    channels: list[ChannelRef]
    videos: list[str]
    terms_accepted: bool = False
    terms_reference: str | None = None
    captions_api: bool = False
    owned_channels: list[str] = field(default_factory=list)
    licensed: dict[str, LicensedTranscript] = field(default_factory=dict)
    allow_language_mismatch: bool = False
    context_cues: int = 1
    drift_tolerance_seconds: float = 30.0
    pending_max_days: float = 7.0
    page_size: int = 50
    max_pages_per_channel: int = 2
    max_units_per_run: int = 200
    daily_units: int = 10000
    refresh_after_days: float = 7.0
    retention_days: float = 30.0
    timeout_seconds: float = 20.0


def load_config(obj: dict | str | Path) -> YouTubeConfig:
    base = Path(".")
    if not isinstance(obj, dict):
        base = Path(obj).resolve().parent
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config key '{k}' is not allowed: credentials go in {KEY_ENV} / {OAUTH_ENV}; machine "
                                     "translation, downloaders and timedtext are not used")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    chans, seen = [], set()
    for i, c in enumerate(obj.get("channels") or []):
        cid, h = (c.get("id"), c.get("handle")) if isinstance(c, dict) else (None, None)
        if (cid is None) == (h is None):
            raise ValueError(f"channels[{i}]: give exactly one of id (UC...) or handle (@name)")
        if cid is not None and not (isinstance(cid, str) and CHANNEL_ID.match(cid)):
            raise ValueError(f"channels[{i}].id: a channel id UC + 22 characters")
        if h is not None:
            h = h if isinstance(h, str) and h.startswith("@") else f"@{h}"
            if not HANDLE_RE.match(h):
                raise ValueError(f"channels[{i}].handle: @ plus 3-30 letters, digits, '.', '_' or '-'")
        k = (cid or h.lower())
        if k in seen:
            raise ValueError(f"channels[{i}]: duplicate channel")
        seen.add(k)
        chans.append(ChannelRef(cid, h))
    vids = []
    for i, v in enumerate(obj.get("videos") or []):
        if not isinstance(v, str) or not VIDEO_ID.match(v):
            raise ValueError(f"videos[{i}]: an 11-character video id")
        if v not in vids:
            vids.append(v)
    tr = obj.get("transcripts") or {}
    cap = tr.get("captions_api") or {}
    owned = []
    for i, c in enumerate(cap.get("owned_channels") or []):
        if not isinstance(c, str) or not CHANNEL_ID.match(c):
            raise ValueError(f"transcripts.captions_api.owned_channels[{i}]: a channel id the OAuth account can edit")
        owned.append(c)
    lic: dict[str, LicensedTranscript] = {}
    for i, e in enumerate(tr.get("licensed") or []):
        if not isinstance(e, dict):
            raise ValueError(f"transcripts.licensed[{i}]: an object")
        vid, f, fmt, lang = e.get("video_id"), e.get("file"), e.get("format", "vtt"), e.get("language")
        perm = e.get("permission") or {}
        if not isinstance(vid, str) or not VIDEO_ID.match(vid):
            raise ValueError(f"transcripts.licensed[{i}].video_id: an 11-character video id")
        if not isinstance(f, str) or "://" in f or not f.strip():
            raise ValueError(f"transcripts.licensed[{i}].file: a local file path (no URL; nothing is downloaded)")
        if fmt not in ("vtt", "srt"):
            raise ValueError(f"transcripts.licensed[{i}].format: vtt or srt")
        if not _lang(lang):
            raise ValueError(f"transcripts.licensed[{i}].language: a BCP-47 tag of the spoken language in the file")
        if perm.get("basis") not in PERMISSION_BASES or not isinstance(perm.get("reference"), str) or len(perm["reference"].strip()) < 4:
            raise ValueError(f"transcripts.licensed[{i}].permission: basis {' or '.join(PERMISSION_BASES)} and a reference "
                             "(where the permission is recorded)")
        p = Path(f)
        lic[vid] = LicensedTranscript(vid, p if p.is_absolute() else base / p, fmt, lang, perm["basis"], perm["reference"].strip())
    tv = obj.get("terms_review") or {}
    q = obj.get("quota") or {}
    return YouTubeConfig(
        channels=chans, videos=vids, terms_accepted=tv.get("accepted") is True, terms_reference=tv.get("reference"),
        captions_api=cap.get("enabled") is True, owned_channels=owned, licensed=lic,
        allow_language_mismatch=tr.get("allow_language_mismatch") is True,
        context_cues=max(0, min(int(tr.get("context_cues", 1)), 3)),
        drift_tolerance_seconds=max(0.0, float(tr.get("drift_tolerance_seconds", 30))),
        pending_max_days=max(0.0, float(tr.get("pending_max_days", 7))),
        page_size=max(1, min(int(obj.get("page_size", 50)), 50)),
        max_pages_per_channel=max(1, int(obj.get("max_pages_per_channel", 2))),
        max_units_per_run=max(0, int(q.get("max_units_per_run", 200))),
        daily_units=max(0, min(int(q.get("daily_units", 10000)), 10000)),
        refresh_after_days=max(0.0, min(float(obj.get("refresh_after_days", 7)), 29.0)),
        retention_days=max(1.0, min(float(obj.get("retention_days", 30)), 30.0)))


def get_credentials(env: dict | None = None) -> tuple[str | None, str | None]:
    import os
    e = env if env is not None else os.environ
    return (e.get(KEY_ENV, "").strip() or None), (e.get(OAUTH_ENV, "").strip() or None)


# ---------- transport ----------

class UrllibTransport:
    """The only code that talks to googleapis.com. The API key goes into the key= parameter of metadata reads only;
    the OAuth token into the Authorization header of caption calls only. Neither is logged (redact())."""

    def __init__(self, timeout: float = 20.0, clock: Callable[[], float] = time.time):
        self.timeout, self.clock = timeout, clock

    def request(self, method: str, path: str, params: dict | None, secret: str | None, *, auth: str = "key") -> HttpResponse:
        p = dict(params or {})
        headers = {"Accept": "application/json"}
        if auth == "oauth":
            headers["Authorization"] = f"Bearer {secret}"
        elif secret:
            p["key"] = secret
        req = urllib.request.Request(API_HOST + path + ("?" + urllib.parse.urlencode(p) if p else ""), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, headers, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            status, headers, raw = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(f"network: {type(e).__name__}") from None
        txt = raw.decode("utf-8", "replace") if raw else ""
        if "json" in headers.get("content-type", "") or txt[:1] in ("{", "["):
            try:
                return HttpResponse(status, headers, json.loads(txt) if txt else None, self.clock())
            except ValueError:
                pass
        return HttpResponse(status, headers, txt, self.clock())


class FixtureTransport(_FT):
    def __init__(self, fixture):
        super().__init__(fixture, FIXTURE_SCHEMA)

    def request(self, method, path, params, secret, *, auth="key"):
        return super().request(method, path, params, secret)


def error_reason(body: Any) -> tuple[str, str]:
    """Google API error envelope -> (reason, message)."""
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        e = body["error"]
        errs = e.get("errors") or [{}]
        reason = errs[0].get("reason") if isinstance(errs[0], dict) else None
        return str(reason or e.get("status") or ""), redact(str(e.get("message") or ""))[:80]
    return "", ""


def classify_error(status: int, body: Any) -> tuple[str, str, str]:
    """-> (health status, message, stop scope 'run' | 'scope')."""
    reason, msg = error_reason(body)
    if status == 403 and reason in ("quotaExceeded", "dailyLimitExceeded"):
        return "RATE_LIMITED", f"quota_exceeded: daily quota used up ({reason})", "run"
    if status in (403, 429) and reason in ("rateLimitExceeded", "userRateLimitExceeded") or status == 429:
        return "RATE_LIMITED", f"rate_limited: {reason or status}", "run"
    if status == 401 or status == 400 and reason in ("keyInvalid", "badRequest") and "key" in msg.lower() or reason == "keyInvalid":
        return "BLOCKED", f"credentials_rejected: {reason or status}; {msg}", "run"
    if status == 403 and reason in ("accessNotConfigured", "SERVICE_DISABLED"):
        return "BLOCKED", "api_not_enabled: enable YouTube Data API v3 in the Google Cloud project", "run"
    if status == 403:
        return "BLOCKED", f"403 {reason or 'forbidden'}; {msg}", "scope"
    if status == 404:
        return "BLOCKED", f"404 {reason or 'not found'}", "scope"
    return "DOWN", f"HTTP {status} {reason}".strip(), "scope"


# ---------- provider object -> inbound item ----------

def video_url(vid: str, t: int | None = None) -> str:
    return f"https://www.youtube.com/watch?v={vid}" + (f"&t={int(t)}s" if t is not None else "")


def _account(channel_id: Any, handle: str | None) -> dict | None:
    if not (isinstance(channel_id, str) and CHANNEL_ID.match(channel_id)):
        return None
    a = {"provider_user_id": channel_id, "profile_url": f"https://www.youtube.com/channel/{channel_id}"}
    if handle and HANDLE_RE.match(handle):
        a["handle"] = handle
    return a


def video_state(v: dict) -> dict:
    """What the lab needs to know about one video resource, as plain values."""
    sn, cd, st = v.get("snippet") or {}, v.get("contentDetails") or {}, v.get("status") or {}
    ld = v.get("liveStreamingDetails") if isinstance(v.get("liveStreamingDetails"), dict) else None

    def t(x):
        try:
            return store.to_utc(x)
        except (ValueError, TypeError):
            return None
    return {"video_id": v.get("id"), "channel_id": sn.get("channelId"), "published_at": t(sn.get("publishedAt")),
            "live": sn.get("liveBroadcastContent") if sn.get("liveBroadcastContent") in ("live", "none", "upcoming") else "none",
            "is_broadcast": ld is not None, "actual_start": t((ld or {}).get("actualStartTime")),
            "actual_end": t((ld or {}).get("actualEndTime")), "scheduled_start": t((ld or {}).get("scheduledStartTime")),
            "duration_s": parse_duration(cd.get("duration")), "has_captions": str(cd.get("caption")).lower() == "true",
            "audio_language": sn.get("defaultAudioLanguage"), "public": st.get("privacyStatus") == "public",
            "title": sn.get("title") if isinstance(sn.get("title"), str) else "",
            "description": sn.get("description") if isinstance(sn.get("description"), str) else ""}


def video_item(vs: dict, fetched_at: float, sink: TextSink | None, handle: str | None = None, recheck: bool = False) -> dict | None:
    """One public video -> one inbound/3 item. Title and description are hashed (and handed to the sink when asked);
    statistics are never requested."""
    vid = vs["video_id"]
    if not (isinstance(vid, str) and VIDEO_ID.match(vid)) or not vs["public"]:
        return None
    text = "\n\n".join(p for p in (vs["title"], vs["description"]) if p.strip())
    chash = store.text_hash(text) if text.strip() else None
    if sink is not None and chash:
        sink.put(PLATFORM, vid, chash, text)
    state = [chash, vs["channel_id"], vs["published_at"], vs["live"], vs["actual_start"], vs["actual_end"]]
    eid = f"yt.{vid}.{canonical_sha(state)[:16]}"
    if recheck:                       # a refresh is a new sighting each day, so the 30-day clock restarts (III.E.4)
        eid += "." + time.strftime("r%Y%m%d", time.gmtime(fetched_at))
    item = {"event_id": eid, "provider_item_id": vid, "url": video_url(vid), "fetched_at": iso(fetched_at),
            "retrieval_status": "OK", "content_hash": chash, "visibility": "PUBLIC",
            "context": {"reference_type": "ORIGINAL", "conversation_id": vid, "in_reply_to_user_id": None,
                        "edit_history_ids": None, "referenced": [], "basis": "PROVIDER"}}
    if vs["published_at"] is not None and vs["published_at"] <= fetched_at + 300:
        item["published_at"], item["published_at_basis"] = iso(vs["published_at"]), "PROVIDER"
    acct = _account(vs["channel_id"], handle)
    if acct:
        item["account"] = acct
    return {k: v for k, v in item.items() if v is not None}


@dataclass
class Timing:
    kind: str                 # VOD | LIVE
    public_at: float          # VOD: video publishedAt; LIVE: actualStartTime
    end_at: float | None      # LIVE: actualEndTime
    media_s: float | None     # length the offsets must fit in


def timing_for(vs: dict) -> tuple[Timing | None, str | None]:
    """(timing, pending/unavailable reason). A transcript is only placed in time once the broadcast is over."""
    if vs["live"] == "upcoming":
        return None, "PENDING_BROADCAST: scheduled, not broadcast yet"
    if vs["live"] == "live":
        return None, "PENDING_BROADCAST: broadcast in progress"
    if vs["is_broadcast"] and vs["actual_start"] is not None:
        if vs["actual_end"] is None:
            return None, "PENDING_BROADCAST: no actualEndTime yet"
        return Timing("LIVE", vs["actual_start"], vs["actual_end"], vs["actual_end"] - vs["actual_start"]), None
    if vs["published_at"] is None:
        return None, "UNAVAILABLE: no publication time"
    return Timing("VOD", vs["published_at"], None, vs["duration_s"]), None


def segment_items(vs: dict, cues: list[dict], timing: Timing, fetched_at: float, sink: TextSink | None, *, context: int,
                  drift_tolerance: float, handle: str | None) -> tuple[list[dict], dict]:
    """Transcript cues -> snippet items around token candidates. Returns (items, stats)."""
    stats = {"cues": len(cues), "drift_dropped": 0, "windows": 0, "clamped": 0}
    limit = None if timing.media_s is None else (timing.media_s + drift_tolerance) * 1000
    good = []
    for c in cues:
        if limit is not None and c["start_ms"] > limit:
            stats["drift_dropped"] += 1
            continue
        good.append(c)
    vid, acct, items = vs["video_id"], _account(vs["channel_id"], handle), []
    for a, b in snippet_windows(good, context):
        win = good[a:b + 1]
        s_ms, e_ms = win[0]["start_ms"], max(c["end_ms"] for c in win)
        text = " ".join(c["text"] for c in win)
        chash = store.text_hash(text)
        pid = segment_id(vid, s_ms, e_ms)
        if timing.kind == "LIVE":
            pub, basis = timing.public_at + s_ms / 1000.0, "PARSED_RELATIVE"
            if timing.end_at is not None and pub > timing.end_at:
                pub = timing.end_at
                stats["clamped"] += 1
        else:
            pub, basis = timing.public_at, "PROVIDER"
        pub = min(pub, fetched_at)
        if sink is not None:
            sink.put(PLATFORM, pid, chash, text)
        it = {"event_id": f"yt.{pid}.{chash[:16]}", "provider_item_id": pid, "url": video_url(vid, s_ms // 1000),
              "published_at": iso(pub), "published_at_basis": basis, "fetched_at": iso(fetched_at), "retrieval_status": "OK",
              "content_hash": chash, "visibility": "PUBLIC",
              "context": {"reference_type": "ORIGINAL", "conversation_id": vid, "in_reply_to_user_id": None,
                          "edit_history_ids": None, "referenced": [], "basis": "PROVIDER"}}
        if acct:
            it["account"] = acct
        items.append(it)
        stats["windows"] += 1
    return items, stats


def language_check(track_lang: str | None, audio_lang: str | None) -> str:
    """MATCH, MISMATCH (the track is in another language than the audio: a translation, so not the words said) or
    UNVERIFIED (the video does not state its audio language)."""
    t, a = _lang(track_lang), _lang(audio_lang)
    if t is None:
        return "UNVERIFIED"
    if a is None:
        return "UNVERIFIED"
    return "MATCH" if t == a else "MISMATCH"


# ---------- the adapter ----------

class QuotaGuard(RequestGuard):
    """RequestGuard in YouTube quota units: a per-run cap and the Pacific Time daily cap, counted from
    social_api_spend rows of this mode. Every request is charged (the docs: invalid requests cost at least 1 unit)."""

    def __init__(self, con, *, mode: str, max_units: int, daily_units: int, now: float):
        super().__init__(con, connector_prefix="youtube_data:", mode=mode, max_requests=10_000)
        self.max_units, self.daily_units = max_units, daily_units
        start, _ = pt_day(now)
        self.used_today = sum(int(json.loads(r[0] or "{}").get("quota_units", 0)) for r in con.execute(
            "SELECT resources_json FROM social_api_spend WHERE connector LIKE 'youtube_data:%' AND mode=? AND requested_at>=?",
            (mode, start)))
        self.units = 0

    def check_units(self, n: int) -> str | None:
        if self.units + n > self.max_units:
            return f"quota cap {self.max_units} units per run would be exceeded ({self.units} used, call costs {n})"
        if self.used_today + self.units + n > self.daily_units:
            return f"daily quota cap {self.daily_units} units would be exceeded ({self.used_today + self.units} used today PT)"
        return None


class YouTubeDataAdapter:
    """SourceAdapter for the YouTube Data API v3, inbound schema /3."""

    name = "youtube_data"

    def __init__(self, cfg: YouTubeConfig, transport, api_key: str | None, db_path: Path | str, *, oauth_token: str | None = None,
                 run_id: str | None = None, mode: str = "live", clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep, retries: int = 3, base_delay: float = 1.0,
                 text_sink: TextSink | None = None):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._key, self._oauth = cfg, transport, api_key, oauth_token
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.sink = text_sink
        self.requests = 0
        self.stopped: str | None = None
        self.transcripts: dict[str, str] = {}      # video id -> transcript status this run
        self.dropped: dict[str, int] = {"not_public": 0, "duplicate_channel": 0, "drift_cues": 0}
        self.quota_units = 0

    def __repr__(self) -> str:
        return (f"YouTubeDataAdapter(mode={self.mode!r}, channels={len(self.cfg.channels)}, "
                f"api_key={'set' if self._key else 'missing'}, oauth={'set' if self._oauth else 'missing'})")

    def _scrub(self, s: str) -> str:
        return scrub(s, self._key, self._oauth)

    def _source(self, connector: str, kind: str, note: str | None = None, licensed: LicensedTranscript | None = None) -> dict:
        live = self.mode == "live"
        if licensed is not None:
            src = {"access_mode": "manual" if live else "fixture", "collector": "licensed-transcript-file" if live else "licensed-transcript-file/fixture",
                   "rights_basis": f"licensed_transcript_{licensed.basis}" if live else "synthetic_fixture"}
        else:
            src = {"access_mode": "fetch" if live else "fixture", "collector": "youtube-data-api-v3" if live else "youtube-data-api-v3/fixture",
                   "rights_basis": "youtube_api_services_terms" if live else "synthetic_fixture"}
        return {"platform": PLATFORM, "source_id": connector.split(":", 1)[1], "visibility": "PUBLIC",
                "terms_note": (note or VISIBILITY[kind])[:400], **src}

    def _unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform=PLATFORM, source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]), body=body, error=error,
                          plan_id=self.run_id)

    def _env(self, connector: str, kind: str, items: list, at: float, note: str | None = None, licensed=None) -> dict:
        return {"schema": INBOUND_SCHEMA_V3, "source": self._source(connector, kind, note, licensed), "fetched_at": iso(at),
                "items": items}

    def _call(self, guard: QuotaGuard, connector: str, endpoint: str, params: dict, *, path: str | None = None,
              oauth: bool = False) -> tuple[HttpResponse | None, str | None, str | None]:
        units = QUOTA_UNITS[endpoint]
        why = guard.check_units(units)
        if why:
            return None, "DEGRADED", f"quota budget: {why}"
        path = path or ENDPOINTS[endpoint]
        secret = self._oauth if oauth else self._key

        def once():
            self.requests += 1
            try:
                r = self.transport.request("GET", path, params, secret, auth="oauth" if oauth else "key")
            except (TransientError, FixtureMiss) as e:
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            guard.units += units
            self.quota_units += units
            if r.status >= 500:
                guard.record(connector=connector, run_id=self.run_id, endpoint=ENDPOINTS[endpoint], status=r.status,
                             resources={"quota_units": units}, now=r.received_at)
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"youtube {endpoint}")
        except TransientError as e:
            return None, "DOWN", f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, "DOWN", f"fixture: {e}"
        n = len(r.body.get("items") or []) if isinstance(r.body, dict) else 0
        guard.record(connector=connector, run_id=self.run_id, endpoint=ENDPOINTS[endpoint], status=r.status,
                     resources={"quota_units": units, "items": n}, now=r.received_at)
        log_event("youtube_request", connector=connector, endpoint=ENDPOINTS[endpoint], status=r.status, units=units, mode=self.mode)
        return r, None, None

    def _fail(self, con, connector: str, ref: str, r: HttpResponse) -> SourceUnit:
        st, msg, scope = classify_error(r.status, r.body)
        if scope == "run":
            self.stopped = msg
            if msg.startswith("quota_exceeded"):
                _, reset = pt_day(r.received_at)
                save_cursor(con, "youtube_data:quota", "daily", self.clock(), last_status="RATE_LIMITED", rate_limit_reset_at=reset)
                msg += f"; resets {iso(reset)} (midnight Pacific Time)"
                self.stopped = msg
        log_event("youtube_scope_stopped", connector=connector, status=st, error=self._scrub(msg))
        return self._unit(connector, st, ref, msg)

    # -- SourceAdapter --
    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        con = connect(self.db_path)
        self.started_at = self.clock()
        try:
            yield from self._run(con)
        finally:
            con.close()

    def _scopes(self) -> list[str]:
        return [f"youtube_data:channel:{c.label}" for c in self.cfg.channels] + (["youtube_data:videos:listed"] if self.cfg.videos else [])

    def _run(self, con) -> Iterator[SourceUnit]:
        if not self.cfg.terms_accepted:
            for s in self._scopes():
                yield self._unit(s, "BLOCKED", f"{s}#terms", "terms_review_missing: record Elving's review of the YouTube API "
                                 "Services Terms and Developer Policies (terms_review.accepted and reference) first")
            return
        if not self._key:
            for s in self._scopes():
                yield self._unit(s, "BLOCKED", f"{s}#credentials", f"credentials_missing: set {KEY_ENV}")
            return
        q = get_cursor(con, "youtube_data:quota", "daily")
        if q and q["rate_limit_reset_at"] and q["rate_limit_reset_at"] > self.clock():
            msg = f"quota_exceeded earlier; not called until {iso(q['rate_limit_reset_at'])} (midnight Pacific Time)"
            self.stopped = msg
            for s in self._scopes():
                yield self._unit(s, "RATE_LIMITED", f"{s}#quota-wait", msg)
            return
        guard = QuotaGuard(con, mode=self.mode, max_units=self.cfg.max_units_per_run, daily_units=self.cfg.daily_units,
                           now=self.clock())
        fetched: dict[str, tuple[dict, str | None]] = {}       # video id -> (state, handle) for transcript work
        handles: dict[str, str | None] = {}
        resolved = yield from self._resolve_channels(con, guard, handles)
        for ref, cid in resolved:
            conn = f"youtube_data:channel:{ref.label}"
            if self.stopped:
                yield self._unit(conn, "DEGRADED", f"{conn}#not-run", f"not run: {self.stopped}")
                continue
            if cid is None:
                continue
            try:
                yield from self._channel(con, guard, conn, cid, handles.get(cid), fetched)
            except Exception as e:
                yield self._unit(conn, "DOWN", f"{conn}#error", f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")
        # configured videos not yet stored, and videos whose transcript is still pending
        stored = {r[0] for r in con.execute("SELECT provider_item_id FROM social_items WHERE platform='youtube'")}
        extra = [v for v in self.cfg.videos if v not in stored and v not in fetched]
        pending = [r["scope"] for r in con.execute("SELECT scope FROM social_source_cursors WHERE connector='youtube_data:transcript'"
                                                   " AND last_status LIKE 'PENDING%' ORDER BY scope") if r["scope"] not in fetched]
        for conn, ids in (("youtube_data:videos:listed", extra), ("youtube_data:videos:pending", pending)):
            if ids and not self.stopped:
                yield from self._videos(con, guard, conn, ids, handles, fetched, "videos")
        if not self.stopped:
            yield from self._transcripts(con, guard, fetched)
        if not self.stopped:
            try:
                yield from self._recheck(con, guard, handles)
            except Exception as e:
                yield self._unit("youtube_data:recheck:stored", "DOWN", "youtube_data:recheck:stored#error",
                                 f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")

    def _resolve_channels(self, con, guard, handles):
        """-> [(ChannelRef, channel id or None)], one entry per configured channel; a second reference to an already
        resolved channel is a duplicate and is not read twice."""
        out, seen = [], set()
        ids = [c.channel_id for c in self.cfg.channels if c.channel_id]
        info: dict[str, dict] = {}
        if ids:
            conn = "youtube_data:channels:resolve"
            r, st, msg = self._call(guard, conn, "channels", {"part": "snippet,contentDetails,status", "id": ",".join(ids),
                                                              "maxResults": 50})
            if r is None or r.status != 200:
                yield (self._unit(conn, st, f"{conn}#ids", msg) if r is None else self._fail(con, conn, f"{conn}#ids", r))
                if r is None and st == "DEGRADED" or self.stopped:
                    self.stopped = self.stopped or msg
            else:
                for ch in r.body.get("items") or []:
                    if isinstance(ch, dict) and isinstance(ch.get("id"), str):
                        info[ch["id"]] = ch
        for c in self.cfg.channels:
            conn = f"youtube_data:channel:{c.label}"
            ch = info.get(c.channel_id) if c.channel_id else None
            if c.handle and not self.stopped:
                r, st, msg = self._call(guard, conn, "channels", {"part": "snippet,contentDetails,status", "forHandle": c.handle})
                if r is None:
                    yield self._unit(conn, st, f"{conn}#resolve", msg)
                    if st == "DEGRADED":
                        self.stopped = msg
                    out.append((c, None))
                    continue
                if r.status != 200:
                    yield self._fail(con, conn, f"{conn}#resolve", r)
                    out.append((c, None))
                    continue
                items = r.body.get("items") or []
                ch = items[0] if items and isinstance(items[0], dict) else None
            if ch is None:
                if not self.stopped:
                    yield self._unit(conn, "BLOCKED", f"{conn}#resolve", "channel_not_found: no channel for this id or handle")
                out.append((c, None))
                continue
            cid = ch.get("id")
            if (ch.get("status") or {}).get("privacyStatus", "public") != "public":
                yield self._unit(conn, "BLOCKED", f"{conn}#resolve", "not_public: channel is not public")
                out.append((c, None))
                continue
            if cid in seen:
                self.dropped["duplicate_channel"] += 1
                yield self._unit(conn, "OK", f"{conn}#duplicate-of={cid}", body=self._env(conn, "channel", [], self.clock(),
                                 "duplicate configuration entry: same channel id as an earlier entry; read once"))
                out.append((c, None))
                continue
            seen.add(cid)
            up = ((ch.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
            cu = (ch.get("snippet") or {}).get("customUrl")
            handles[cid] = cu if isinstance(cu, str) and HANDLE_RE.match(cu) else (c.handle if c.handle else None)
            save_cursor(con, conn, cid, self.clock(), provider_scope_id=up if isinstance(up, str) else None)
            out.append((c, cid))
        return out

    def _channel(self, con, guard, conn: str, cid: str, handle, fetched) -> Iterator[SourceUnit]:
        cur = get_cursor(con, conn, cid)
        up = cur["provider_scope_id"] if cur else None
        if not up:
            yield self._unit(conn, "BLOCKED", f"{conn}#uploads", "no uploads playlist in the channel resource")
            return
        since = cur["newest_id"]
        since_t = store.to_utc(since) if since else None
        ids, newest, token, page, gap = [], None, None, 0, False
        while True:
            page += 1
            p = {"part": "contentDetails", "playlistId": up, "maxResults": self.cfg.page_size}
            if token:
                p["pageToken"] = token
            ref = f"{conn}#since={since or 'none'}&page={page}"
            r, st, msg = self._call(guard, conn, "playlist_items", p)
            if r is None:
                if st == "DEGRADED":
                    self.stopped = msg
                yield self._unit(conn, st, ref, msg)
                return
            if r.status != 200:
                yield self._fail(con, conn, ref, r)
                return
            reached = False
            for it in r.body.get("items") or []:
                d = (it or {}).get("contentDetails") or {}
                vid, vp = d.get("videoId"), d.get("videoPublishedAt")
                try:
                    vpt = store.to_utc(vp) if vp else None
                except ValueError:
                    vpt = None
                if not (isinstance(vid, str) and VIDEO_ID.match(vid)):
                    continue
                if since_t is not None and vpt is not None and vpt <= since_t:
                    reached = True              # the API does not document an order: older items are skipped, never assumed
                    continue
                if vid not in ids:
                    ids.append(vid)
                if vpt is not None and (newest is None or vpt > newest):
                    newest = vpt
            token = r.body.get("nextPageToken")
            if not token or reached:
                break
            if page >= self.cfg.max_pages_per_channel:
                gap = True
                break
        if gap:
            yield self._unit(conn, "DEGRADED", f"{conn}#since={since or 'none'}&gap",
                             f"page cap {self.cfg.max_pages_per_channel} reached; older uploads were not listed")
        units = []
        if ids:
            for u in self._videos(con, guard, conn, ids, {cid: handle}, fetched, "channel"):
                units.append(u)
                yield u
        else:
            u = self._unit(conn, "OK", f"{conn}#since={since or 'none'}&empty", body=self._env(conn, "channel", [], self.clock()))
            units.append(u)
            yield u
        if all(u.status == "OK" for u in units) and units_committed(con, [u for u in units if u.status == "OK"]):
            kw = {"last_status": "OK", "last_success_at": self.clock()}
            if newest is not None and (since_t is None or newest > since_t):
                kw["newest_id"] = iso(newest)
            save_cursor(con, conn, cid, self.clock(), **kw)
        else:
            save_cursor(con, conn, cid, self.clock(), last_status="PARTIAL")

    def _videos(self, con, guard, conn: str, ids: list[str], handles: dict, fetched: dict, kind: str) -> Iterator[SourceUnit]:
        for b in range(0, len(ids), 50):
            chunk = ids[b:b + 50]
            ref = f"{conn}#videos={canonical_sha(chunk)[:12]}"
            r, st, msg = self._call(guard, conn, "videos", {"part": "snippet,contentDetails,status,liveStreamingDetails",
                                                            "id": ",".join(chunk), "maxResults": 50})
            if r is None:
                if st == "DEGRADED":
                    self.stopped = msg
                yield self._unit(conn, st, ref, msg)
                return
            if r.status != 200:
                yield self._fail(con, conn, ref, r)
                return
            items = []
            for v in r.body.get("items") or []:
                if not isinstance(v, dict) or v.get("id") not in chunk:
                    continue
                vs = video_state(v)
                if not vs["public"]:
                    self.dropped["not_public"] += 1
                    continue
                h = handles.get(vs["channel_id"])
                it = video_item(vs, r.received_at, self.sink, h)
                if it is None:
                    continue
                items.append(it)
                fetched[vs["video_id"]] = (vs, h)
            yield self._unit(conn, "OK", ref, body=self._env(conn, kind, items, r.received_at))

    # -- transcripts --
    def _set_tx(self, con, vid: str, status: str, **kw) -> None:
        self.transcripts[vid] = status
        save_cursor(con, "youtube_data:transcript", vid, self.clock(), last_status=status[:60], **kw)

    def _transcripts(self, con, guard, fetched: dict) -> Iterator[SourceUnit]:
        for vid, (vs, handle) in sorted(fetched.items()):
            if self.stopped:
                return
            cur = get_cursor(con, "youtube_data:transcript", vid)
            if cur and cur["last_status"] in ("DONE",) or cur and cur["last_status"].startswith("UNAVAILABLE"):
                self.transcripts[vid] = cur["last_status"]
                continue
            lic = self.cfg.licensed.get(vid)
            route = "licensed_file" if lic else ("captions_api" if self.cfg.captions_api and vs["channel_id"] in self.cfg.owned_channels
                                                 else None)
            if route is None:
                self._set_tx(con, vid, "UNAVAILABLE_NO_AUTHORIZED_ROUTE")
                continue
            timing, why = timing_for(vs)
            if timing is None:
                if why.startswith("PENDING") and cur is None:
                    self._set_tx(con, vid, why.split(":")[0], provider_scope_id=route)
                elif why.startswith("PENDING"):
                    self.transcripts[vid] = cur["last_status"]
                else:
                    self._set_tx(con, vid, "UNAVAILABLE_NO_TIME")
                continue
            if route == "licensed_file":
                yield from self._licensed(con, vid, vs, handle, lic, timing)
            else:
                if not self._oauth:
                    self._set_tx(con, vid, "UNAVAILABLE_OAUTH_MISSING")
                    continue
                yield from self._captions(con, guard, vid, vs, handle, timing, cur)

    def _pending_or_gone(self, con, vid: str, vs: dict, cur, reason: str) -> None:
        """Captions not there yet: an archived livestream often gets captions later. Wait up to pending_max_days after
        the broadcast ended (or the video was published), then give up."""
        anchor = vs["actual_end"] or vs["published_at"] or self.clock()
        if self.clock() - anchor > self.cfg.pending_max_days * 86400:
            self._set_tx(con, vid, f"UNAVAILABLE_{reason}")
        else:
            self._set_tx(con, vid, "PENDING_ARCHIVE")

    def _emit_segments(self, con, vid, vs, handle, timing, cues, at, conn, note, licensed=None) -> Iterator[SourceUnit]:
        items, stats = segment_items(vs, cues, timing, at, self.sink, context=self.cfg.context_cues,
                                     drift_tolerance=self.cfg.drift_tolerance_seconds, handle=handle)
        self.dropped["drift_cues"] += stats["drift_dropped"]
        ref = f"{conn}#video={vid}&track={canonical_sha([note, len(cues)])[:12]}"
        yield self._unit(conn, "OK", ref, body=self._env(conn, "videos", items, at, note, licensed))
        if stats["drift_dropped"]:
            yield self._unit(conn, "DEGRADED", f"{conn}#video={vid}&drift",
                             f"timestamp_drift: {stats['drift_dropped']} of {stats['cues']} cues start after the media length "
                             f"plus {self.cfg.drift_tolerance_seconds:g} s and were dropped")
        self._set_tx(con, vid, "DONE", newest_id=str(stats["windows"]))

    def _note(self, route: str, vid: str, lang: str | None, kind: str, audio: str | None, check: str, timing: Timing) -> str:
        when = ("segment time = public time of the video (publishedAt), not the time the words were spoken"
                if timing.kind == "VOD" else "segment time = broadcast actualStartTime + cue offset (derived, +/- drift)")
        return (f"YouTube transcript snippets of video {vid} via {route}; track language {lang or 'unknown'}, kind {kind}, "
                f"audio language {audio or 'not stated'}, language {check}; {when}"
                + ("; ASR: words, tickers and addresses may be misheard" if kind == "ASR" else ""))

    def _licensed(self, con, vid, vs, handle, lic: LicensedTranscript, timing: Timing) -> Iterator[SourceUnit]:
        conn = "youtube_data:transcript:licensed_file"
        check = language_check(lic.language, vs["audio_language"])
        if check == "MISMATCH" and not self.cfg.allow_language_mismatch:
            self._set_tx(con, vid, "UNAVAILABLE_LANGUAGE_MISMATCH")
            yield self._unit(conn, "DEGRADED", f"{conn}#video={vid}&language",
                             f"language_uncertain: transcript language {lic.language} differs from the audio language "
                             f"{vs['audio_language']}; a translation is not what was said, so it was not used")
            return
        try:
            raw = lic.path.read_text(encoding="utf-8")
        except OSError as e:
            self._set_tx(con, vid, "UNAVAILABLE_FILE")
            yield self._unit(conn, "DOWN", f"{conn}#video={vid}&file", f"transcript file unreadable: {type(e).__name__}")
            return
        note = self._note(f"licensed file ({lic.basis}, ref {lic.reference[:40]})", vid, lic.language, "licensed", vs["audio_language"],
                          check, timing)
        yield from self._emit_segments(con, vid, vs, handle, timing, parse_cues(raw), self.clock(), conn, note, lic)

    def _captions(self, con, guard, vid, vs, handle, timing: Timing, cur) -> Iterator[SourceUnit]:
        conn = "youtube_data:transcript:captions_api"
        if not vs["has_captions"]:
            self._pending_or_gone(con, vid, vs, cur, "NO_CAPTIONS")
            return
        r, st, msg = self._call(guard, conn, "captions", {"part": "snippet", "videoId": vid}, oauth=True)
        if r is None:
            if st == "DEGRADED":
                self.stopped = msg
            yield self._unit(conn, st, f"{conn}#video={vid}&list", msg)
            return
        if r.status in (401, 403):
            stt, m, scope = classify_error(r.status, r.body)
            if scope == "run":
                yield self._fail(con, conn, f"{conn}#video={vid}&list", r)
                return
            self._set_tx(con, vid, "UNAVAILABLE_NOT_PERMITTED")
            yield self._unit(conn, "BLOCKED", f"{conn}#video={vid}&list", f"not_permitted: the OAuth account cannot edit this "
                             f"video, so its captions are not available to the lab ({m})")
            return
        if r.status != 200:
            yield self._fail(con, conn, f"{conn}#video={vid}&list", r)
            return
        tracks = []
        for t in r.body.get("items") or []:
            sn = (t or {}).get("snippet") or {}
            if sn.get("status") != "serving" or sn.get("isDraft") is True or sn.get("audioTrackType") not in (None, "primary", "unknown"):
                continue
            tracks.append((t.get("id"), sn))
        if not tracks:
            self._pending_or_gone(con, vid, vs, cur, "NO_SERVING_TRACK")
            return
        audio = vs["audio_language"]

        def rank(x):
            sn = x[1]
            chk = language_check(sn.get("language"), audio)
            return ({"MATCH": 0, "UNVERIFIED": 1, "MISMATCH": 2}[chk], 0 if sn.get("trackKind") == "standard" else 1, str(x[0]))
        tid, sn = sorted(tracks, key=rank)[0]
        check = language_check(sn.get("language"), audio)
        if check == "MISMATCH" and not self.cfg.allow_language_mismatch:
            self._set_tx(con, vid, "UNAVAILABLE_LANGUAGE_MISMATCH")
            yield self._unit(conn, "DEGRADED", f"{conn}#video={vid}&language",
                             f"language_uncertain: only caption tracks in {sn.get('language')} for audio in {audio}; a translated "
                             "track is not what was said, so none was used")
            return
        r, st, msg = self._call(guard, conn, "caption_download", {"tfmt": "vtt"}, path=ENDPOINTS["caption_download"].format(id=tid),
                                oauth=True)
        if r is None:
            if st == "DEGRADED":
                self.stopped = msg
            yield self._unit(conn, st, f"{conn}#video={vid}&download", msg)
            return
        if r.status in (401, 403, 404):
            stt, m, scope = classify_error(r.status, r.body)
            if scope == "run":
                yield self._fail(con, conn, f"{conn}#video={vid}&download", r)
                return
            self._set_tx(con, vid, "UNAVAILABLE_NOT_PERMITTED" if r.status != 404 else "UNAVAILABLE_TRACK_GONE")
            yield self._unit(conn, "BLOCKED", f"{conn}#video={vid}&download", f"caption download refused: {m}")
            return
        if r.status != 200 or not isinstance(r.body, str):
            yield self._fail(con, conn, f"{conn}#video={vid}&download", r)
            return
        kind = sn.get("trackKind") or "standard"
        note = self._note("captions.download (owner OAuth)", vid, sn.get("language"), kind, audio, check, timing)
        yield from self._emit_segments(con, vid, vs, handle, timing, parse_cues(r.body), r.received_at, conn, note)

    # -- refresh (30-day rule) --
    def _recheck(self, con, guard, handles) -> Iterator[SourceUnit]:
        conn = "youtube_data:recheck:stored"
        cutoff = self.started_at - self.cfg.refresh_after_days * 86400
        rows = con.execute(
            "SELECT i.provider_item_id, MAX(o.observed_at) AS last_ok FROM social_items i JOIN social_observations o ON o.item_key=i.item_key"
            " WHERE i.platform='youtube' AND o.retrieval_status='OK' AND i.first_ingested_at < ? AND NOT EXISTS (SELECT 1 FROM"
            " social_observations g WHERE g.item_key=i.item_key AND g.retrieval_status IN ('NOT_FOUND','DELETED'))"
            " GROUP BY i.item_key ORDER BY last_ok, i.provider_item_id", (self.started_at,)).fetchall()
        ids = [r[0] for r in rows if VIDEO_ID.match(r[0] or "") and r[1] is not None and r[1] <= cutoff]
        if not ids:
            yield self._unit(conn, "OK", f"{conn}#empty", body=self._env(conn, "recheck", [], self.clock()))
            return
        for b in range(0, len(ids), 50):
            chunk = ids[b:b + 50]
            ref = f"{conn}#batch={b // 50 + 1}&ids={canonical_sha(chunk)[:12]}"
            r, st, msg = self._call(guard, conn, "videos", {"part": "snippet,contentDetails,status,liveStreamingDetails",
                                                            "id": ",".join(chunk), "maxResults": 50})
            if r is None:
                yield self._unit(conn, st, ref, msg)
                return
            if r.status != 200:
                yield self._fail(con, conn, ref, r)
                return
            items, seen = [], set()
            for v in r.body.get("items") or []:
                if not isinstance(v, dict) or v.get("id") not in chunk:
                    continue
                vs = video_state(v)
                it = video_item(vs, r.received_at, self.sink, handles.get(vs["channel_id"]), recheck=True)
                if it is not None:
                    items.append(it)
                    seen.add(vs["video_id"])
            day = time.strftime("%Y%m%d", time.gmtime(r.received_at))
            for vid in chunk:
                if vid in seen:
                    continue
                # gone or no longer public: the video and every stored snippet of it
                gone = [vid] + [x[0] for x in con.execute("SELECT provider_item_id FROM social_items WHERE platform='youtube' AND "
                                                          "substr(provider_item_id,1,13)=? ORDER BY 1", (vid + "_t",))]
                for pid in gone:
                    items.append({"event_id": f"yt.{pid}.not_found.{day}", "provider_item_id": pid, "fetched_at": iso(r.received_at),
                                  "retrieval_status": "NOT_FOUND", "visibility": "PUBLIC"})
            yield self._unit(conn, "OK", ref, body=self._env(conn, "recheck", items, r.received_at))
        save_cursor(con, conn, "stored", self.clock(), last_status="OK", last_success_at=self.clock())


# ---------- deletion and the 30-day rule ----------

def purge(db_path: Path | str, *, now: float, retention_days: float = 30.0, private_path=None) -> dict:
    """Two erasures, both idempotent:
      gone     every YouTube item with a NOT_FOUND or DELETED sighting (video removed or no longer public, and its
               snippets): the shared purge (api_common.purge_gone_items).
      expired  every YouTube video not seen OK within retention_days (default 30, the Developer Policies limit for
               non-authorized data), and its snippets: same erasure of derived data (hashes, claim spans and summaries,
               extraction outputs, private copies, author link). Ids and times stay; whether those must go too is
               part of open decision D-146."""
    con = connect(db_path)
    try:
        out = {"gone": purge_gone_items(con, PLATFORM, private_path=private_path)}
        cutoff = now - retention_days * 86400
        stale = []
        for pid, last in con.execute(
                "SELECT i.provider_item_id, MAX(CASE WHEN o.retrieval_status='OK' THEN o.observed_at END) FROM social_items i JOIN "
                "social_observations o ON o.item_key=i.item_key WHERE i.platform='youtube' GROUP BY i.item_key"):
            if pid and VIDEO_ID.match(pid) and last is not None and last < cutoff:
                stale.append(pid)
        keys = []
        for vid in stale:
            keys.append(store.item_key_for(PLATFORM, vid, None))
            keys += [store.item_key_for(PLATFORM, r[0], None) for r in con.execute(
                "SELECT provider_item_id FROM social_items WHERE platform='youtube' AND substr(provider_item_id,1,13)=?", (vid + "_t",))]
        out["expired"] = clear_item_keys(con, keys, private_path=private_path)
        out["expired"]["videos_past_retention"] = len(stale)
        con.commit()
    finally:
        con.close()
    log_event("youtube_purge", gone=out["gone"]["items_purged"], expired=out["expired"]["items_purged"])
    return out


# ---------- health ----------

def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None) -> dict:
    """No network call. Status: not_configured | terms_review_missing | credentials_missing | quota_exhausted | ready."""
    t = time.time() if now is None else now
    key, oauth = get_credentials(env)
    out: dict = {"adapter": "youtube_data", "contract_verified": CONTRACT_VERIFIED, "credential_env": [KEY_ENV, OAUTH_ENV],
                 "credentials": "present" if key else "missing", "oauth_token": "present" if oauth else "missing",
                 "network_calls_made": 0,
                 "cost": "no charge; quota 10,000 units per day (PT): channels, playlistItems and videos 1 unit per call, "
                         "captions.list 50, captions.download 200; search.list not used"}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    out["config"] = None if cfg is None else {
        "channels": [c.label for c in cfg.channels], "videos": len(cfg.videos), "terms_accepted": cfg.terms_accepted,
        "transcript_routes": {"captions_api": cfg.captions_api, "owned_channels": len(cfg.owned_channels),
                              "licensed_files": len(cfg.licensed)},
        "max_units_per_run": cfg.max_units_per_run, "daily_units": cfg.daily_units, "retention_days": cfg.retention_days}
    con = connect(db_path)
    try:
        start, end = pt_day(t)
        rows = con.execute("SELECT resources_json, http_status, requested_at FROM social_api_spend WHERE mode='live' AND "
                           "connector LIKE 'youtube_data:%'").fetchall()
        ok = sum(1 for r in rows if r[1] == 200)
        out["live_evidence"] = {"requests": len(rows), "successful": ok, "last_request_at": max((r[2] for r in rows), default=None),
                                "verdict": "live authorized ingest proved" if ok else "none: no live YouTube read has been made"}
        out["quota_used_today_pt"] = sum(int(json.loads(r[0] or "{}").get("quota_units", 0)) for r in rows if r[2] >= start)
        q = get_cursor(con, "youtube_data:quota", "daily")
        out["quota_reset_at"] = iso(q["rate_limit_reset_at"]) if q and q["rate_limit_reset_at"] and q["rate_limit_reset_at"] > t else None
        out["cursors"] = [{k: r[k] for k in ("connector", "scope", "newest_id", "last_status", "last_success_at")}
                          for r in con.execute("SELECT * FROM social_source_cursors WHERE connector LIKE 'youtube_data:channel:%'"
                                               " ORDER BY connector")]
        out["transcripts"] = {r[0]: r[1] for r in con.execute(
            "SELECT last_status, COUNT(*) FROM social_source_cursors WHERE connector='youtube_data:transcript' GROUP BY last_status")}
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'youtube_data:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
        last = {}
        for pid, lt in con.execute("SELECT i.provider_item_id, MAX(o.observed_at) FROM social_items i JOIN social_observations o ON "
                                   "o.item_key=i.item_key WHERE i.platform='youtube' AND o.retrieval_status='OK' GROUP BY i.item_key"):
            if pid and VIDEO_ID.match(pid):
                last[pid] = lt
        ret = (cfg.retention_days if cfg else 30.0) * 86400
        out["retention"] = {"videos_stored": len(last), "past_retention_unpurged": sum(1 for v in last.values() if v < t - ret)}
    finally:
        con.close()
    if cfg is None or not (cfg.channels or cfg.videos):
        out["status"] = "not_configured"
    elif not cfg.terms_accepted:
        out["status"] = "terms_review_missing"
    elif not key:
        out["status"] = "credentials_missing"
    elif out["quota_reset_at"]:
        out["status"] = "quota_exhausted"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "not_configured": "write the channel config (docs/social-intelligence/youtube_data.example.json) to data/private/youtube_data.json",
        "terms_review_missing": "Elving reviews the YouTube API Services Terms and Developer Policies (30-day storage, no derived "
                                "metrics, aggregation across content owners, D-146) and records terms_review.accepted with a reference",
        "credentials_missing": f"create an API key restricted to YouTube Data API v3 and export {KEY_ENV} in the shell that runs memelab",
        "quota_exhausted": "wait for midnight Pacific Time; the next run resumes",
        "ready": "run one small live ingest (one channel, max_pages_per_channel 1) and check `social youtube-health` live_evidence",
    }[out["status"]]
    return out

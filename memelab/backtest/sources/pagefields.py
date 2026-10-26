"""One field extractor for public web pages, whatever tool fetched them (Phase 06A).

Input is a "view" of a tool's output: {"meta": {...}, "h1s": [...], "text_dates": [...], "jsonld_dates": [...], "reltime": [...]}.
Output fields are CLAIMS made by the page (untrusted): title, claimed publication date (UTC calendar date) and a
version tag. The requested URL is never used to fill a field. Rules (fixed in MAXUN_BAKEOFF_PREREG.md):
- title: og:title, else the HTML title with the site suffix removed, else the first H1;
- date: article/published metadata, else JSON-LD datePublished, else a machine-readable <relative-time datetime>,
  else the first full date written in the text (lowest confidence: it may belong to another element on the page, such
  as a commit signature, or be rendered in the crawler's time zone);
- tag: the first version-like string in the title, else in an H1.
"""
from __future__ import annotations

import html as H
import re
from datetime import datetime, timezone

EXTRACTOR_VERSION = "pagefields-1"
TAG = re.compile(r"(?:[A-Za-z][\w-]*[@-])?v?\d+\.\d+\.\d+(?:-[A-Za-z][\w.]*)?")
GH_SUFFIX = re.compile(r"\s*·\s*[\w.-]+/[\w.-]+(?:\s*·\s*GitHub)?\s*$")
SITE_SUFFIX = re.compile(r"\s*\|\s*Solana Media\s*$")
FULL_DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2},? \d{4}\b")
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DATE_CONFIDENCE = {"article:published_time": "META", "publishedTime": "META", "datePublished": "META", "jsonld": "META",
                   "relative-time": "MACHINE_TIME", "text": "RENDERED_TEXT", "none": None}


def norm(s: str | None) -> str | None:
    if s is None:
        return None
    s = H.unescape(s).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().casefold()


def _clean_title(t: str) -> str:
    if GH_SUFFIX.search(t):
        t = GH_SUFFIX.sub("", t)
        t = re.sub(r"^Release ", "", t, count=1)       # GitHub prefixes every release page title with "Release "
    return SITE_SUFFIX.sub("", t).strip()


def title_of(v: dict) -> tuple[str | None, str]:
    m = v.get("meta") or {}
    for k in ("og:title", "ogTitle", "title"):
        if m.get(k):
            return _clean_title(m[k]), k
    if v.get("h1s"):
        return v["h1s"][0], "h1"
    return None, "none"


def iso_date(s: str) -> str | None:
    s = s.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})$", s):
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)                 # no zone given: the written calendar date
    return m.group(1) if m else None


def text_date(s: str) -> str | None:
    m = re.match(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})", s)
    if not m or m.group(1).lower() not in MONTHS:
        return None
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"


def date_of(v: dict) -> tuple[str | None, str]:
    m = v.get("meta") or {}
    for k in ("article:published_time", "publishedTime", "datePublished"):
        if m.get(k) and iso_date(m[k]):
            return iso_date(m[k]), k
    for d in v.get("jsonld_dates") or []:
        if iso_date(d):
            return iso_date(d), "jsonld"
    for d in v.get("reltime") or []:
        if iso_date(d):
            return iso_date(d), "relative-time"
    for d in v.get("text_dates") or []:
        if text_date(d):
            return text_date(d), "text"
    return None, "none"


def tag_of(v: dict) -> tuple[str | None, str]:
    t, _ = title_of(v)
    for src, s in (("title", t), *(("h1", h) for h in v.get("h1s") or [])):
        if s:
            m = TAG.search(s)
            if m:
                return m.group(0), src
    return None, "none"


def extract(v: dict) -> dict:
    t, ts = title_of(v)
    d, ds = date_of(v)
    g, gs = tag_of(v)
    return {"title": t, "title_from": ts, "date": d, "date_from": ds, "date_confidence": DATE_CONFIDENCE.get(ds), "tag": g, "tag_from": gs,
            "extractor_version": EXTRACTOR_VERSION}


def date_epoch(d: str | None) -> float | None:
    return None if d is None else datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()

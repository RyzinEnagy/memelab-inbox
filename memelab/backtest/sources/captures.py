"""Canonical capture registry for public web documents (crawler or robot captures), as an extension of the lab's
catalyst page records.

Rules (MAXUN_ROBOT_CONTRACT D, WEB_RESEARCH_TOOLING):
- first_seen_at comes from our own capture evidence, never from the page's claimed publication date;
- a page crawled today is not evidence it was knowable earlier: without contemporaneous proof the capture is
  available only from first_seen_at, and historical strategies treat it as UNKNOWN_AS_OF before that;
- one canonical origin + content hash is one record whatever tool fetched it (no fake corroboration);
- a changed page is a new version with its own first_seen_at; the old version is never rewritten;
- a mint is attached only after independent verification (mint_verified = 1).
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .. import store
from ..timeguard import ClockError, utc_ts

TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|ref$|ref_src$|s$|mc_cid$|mc_eid$)")
COLLECTORS = ("EXISTING_COLLECTOR", "FIRECRAWL", "CRAWL4AI", "MAXUN", "FIXTURE", "OTHER")


def canonical_url(url: str) -> str:
    u = urlsplit(url.strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError(f"not an http(s) URL: {url!r}")
    host = u.hostname.lower() if u.hostname else ""
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", u.path or "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    q = urlencode(sorted((k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not TRACKING.match(k.lower())))
    return urlunsplit(("https", host, path, q, ""))


def content_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", text or "").strip()
    return hashlib.sha256(norm.encode()).hexdigest()


def record_capture(con, *, collector: str, source_url: str, text: str, captured_at: float, source_published_at: float | None = None,
                   published_confidence: str | None = None, source_edited_at: float | None = None, robot_id: str | None = None,
                   run_id: str | None = None, robot_version: str | None = None, edition: str | None = None, extractor_version: str | None = None,
                   run_status: str | None = None, raw_ref: str | None = None, record_type: str | None = None, claim_state: str = "CLAIM",
                   extraction_status: str = "OK", historical_asof_proof: str = "NONE", origin_group: str | None = None,
                   chain: str | None = None, mint: str | None = None, mint_verified: bool = False,
                   catalyst_item_id: int | None = None, catalyst_page_fetch_id: int | None = None,
                   proof_observed_at: float | None = None) -> dict:
    """proof_observed_at: when an independent contemporaneous capture (archive snapshot, signed observation) saw the
    same content. Only that, never the page's own date, can make first_seen_at earlier than our capture."""
    if collector not in COLLECTORS:
        raise ValueError(f"unknown collector {collector}")
    captured_at = utc_ts(captured_at)
    if source_published_at is not None:
        source_published_at = utc_ts(source_published_at)
    if mint is not None and not mint_verified:
        raise ValueError("mint attached without independent verification; keep it as a claim instead")
    canon = canonical_url(source_url)
    h = content_hash(text)
    prior = con.execute("SELECT id, collector, first_seen_at FROM bt_capture_provenance WHERE canonical_origin=? AND content_hash=?", (canon, h)).fetchone()
    if prior:
        return {"id": prior["id"], "new": False, "duplicate_of_collector": prior["collector"], "canonical_origin": canon, "content_hash": h,
                "first_seen_at": prior["first_seen_at"], "independent_confirmation": False}
    if (historical_asof_proof == "NONE") != (proof_observed_at is None):
        raise ClockError("historical_asof_proof and proof_observed_at must be given together")
    if proof_observed_at is not None and source_published_at is not None and utc_ts(proof_observed_at) < source_published_at:
        # an archive cannot have seen a page before the page itself says it was published: the proof is about
        # another version or is wrong, so it never moves availability earlier (Phase 16, D9)
        raise ClockError("archive proof predates the page's own publication claim; refused")
    first_seen = captured_at if proof_observed_at is None else min(captured_at, utc_ts(proof_observed_at))
    rid, _ = store._insert(con, "bt_capture_provenance", dict(
        collector=collector, robot_id=robot_id, run_id=run_id, robot_version=robot_version, edition=edition, extractor_version=extractor_version,
        run_status=run_status, source_url=source_url, canonical_origin=canon, source_domain=urlsplit(canon).hostname, content_hash=h, raw_ref=raw_ref,
        captured_at=captured_at, first_seen_at=first_seen, source_published_at=source_published_at, published_confidence=published_confidence,
        source_edited_at=source_edited_at, available_at=first_seen,
        historical_asof_proof=historical_asof_proof, origin_group=origin_group or canon, record_type=record_type, claim_state=claim_state,
        extraction_status=extraction_status, chain=chain, mint=mint, mint_verified=1 if mint_verified else 0,
        catalyst_item_id=catalyst_item_id, catalyst_page_fetch_id=catalyst_page_fetch_id))
    versions = con.execute("SELECT COUNT(*) FROM bt_capture_provenance WHERE canonical_origin=?", (canon,)).fetchone()[0]
    return {"id": rid, "new": True, "canonical_origin": canon, "content_hash": h, "first_seen_at": first_seen, "version": versions,
            "independent_confirmation": False}


def captures_asof(con, canonical_origin: str, cutoff: float, for_historical_strategy: bool = True) -> dict:
    """What a decision at cutoff may know about a page. For historical strategies, a capture without contemporaneous
    proof is usable only from its own first_seen_at; publication claims never move it earlier."""
    rows = [dict(r) for r in con.execute("SELECT * FROM bt_capture_provenance WHERE canonical_origin=? ORDER BY available_at, id", (canonical_origin,))]
    vis = [r for r in rows if r["available_at"] <= cutoff]
    if not vis:
        claimed_earlier = [r for r in rows if r["source_published_at"] is not None and r["source_published_at"] <= cutoff]
        return {"state": "UNKNOWN_AS_OF" if claimed_earlier else "MISSING", "version": None,
                "note": "page claims an earlier publication but was first captured later" if claimed_earlier else None}
    cur = vis[-1]
    return {"state": "OBSERVED", "version": cur, "versions_visible": len(vis), "late_capture": cur["historical_asof_proof"] == "NONE" and
            cur["source_published_at"] is not None and cur["first_seen_at"] - cur["source_published_at"] > 3600}

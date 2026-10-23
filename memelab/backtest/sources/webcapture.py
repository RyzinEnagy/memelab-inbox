"""Bounded public-page capture ingestion for catalyst and release watches (Phase 06A outcome: EXISTING_TOOL_WINS).

No Maxun code lives here: the bake-off kept the existing collectors (plain HTTP with the lab's parsers, Crawl4AI,
Firecrawl). This module is the one path by which any of them turns a fetched page into a point-in-time record:
- the page must match an allowlisted pattern for a named use case (no recursion: callers pass explicit URLs and a page cap);
- fields come from the shared extractor (pagefields) and stay CLAIMS; nothing in page text is executed or trusted;
- one canonical origin + claim fingerprint is one record whatever tool fetched it, so two crawlers never count as two
  sources; a changed title, date or tag is a new version with its own first_seen_at; nothing is overwritten;
- first_seen_at / available_at are our capture time unless an independent contemporaneous capture is supplied, so an
  old page crawled today is UNKNOWN_AS_OF at its claimed date;
- a failed, partial, empty, rate-limited or unauthorized fetch records nothing and never yields a positive signal;
- no schedule runs unless the collector policy file says schedules were approved (it does not).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import store
from . import captures, pagefields

USE_CASES = {
    "project_catalyst_watch": {"allow": [r"^https://solana\.com/news/[a-z0-9][a-z0-9-]*$"], "record_type": "announcement", "max_pages_per_run": 20},
    "developer_release_watch": {"allow": [r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/releases/tag/[^/?#]+$"], "record_type": "release",
                                "max_pages_per_run": 20,
                                # only tracked repositories: any GitHub user can publish a look-alike release under another owner.
                                # otter-sec/anchor is where GitHub's API pointed solana-foundation/anchor on 2026-10-23 (a transfer).
                                "repos": ["anza-xyz/agave", "solana-foundation/anchor", "otter-sec/anchor", "orca-so/whirlpools", "helius-labs/helius-sdk",
                                          "jito-foundation/jito-solana", "solana-program/token-2022", "metaplex-foundation/mpl-token-metadata",
                                          "anza-xyz/kit", "pyth-network/pyth-crosschain", "metaplex-foundation/umi"]},
}
RUNTIME_COLLECTORS = ("EXISTING_COLLECTOR", "CRAWL4AI", "FIRECRAWL")
EVIDENCE_ONLY_COLLECTORS = ("MAXUN", "FIXTURE")          # bake-off evidence and tests; never a runtime path (not adopted)
POLICY_PATH = store.ROOT / "data" / "backtest" / "collector_policy.json"
DEFAULT_POLICY = {"collectors_enabled": True, "schedules_approved": False, "maxun_adopted": False}


class OffAllowlist(ValueError):
    pass


class ScheduleNotApproved(PermissionError):
    pass


def load_policy(path: Path | str | None = None) -> dict:
    p = Path(path) if path else POLICY_PATH
    pol = dict(DEFAULT_POLICY)
    if p.exists():
        pol.update(json.loads(p.read_text()))
    return pol


def assert_schedule_allowed(policy: dict) -> None:
    """Called by anything that would run unattended. Standing schedules need explicit approval recorded in the policy."""
    if not policy.get("schedules_approved"):
        raise ScheduleNotApproved("recurring collection is not approved; run one-shot only")


def allowed(use_case: str, url: str) -> str:
    uc = USE_CASES[use_case]
    canon = captures.canonical_url(url).replace("%40", "@")
    from urllib.parse import urlsplit as _us
    if any(looks_like_secret(seg) for seg in _us(canon).path.split("/")):
        raise OffAllowlist("credential-shaped path segment; refused and never stored")
    m = next((m for m in (re.match(p, canon) for p in uc["allow"]) if m), None)
    if not m:
        raise OffAllowlist(f"{canon} is outside the {use_case} allowlist")
    if "repos" in uc and m.group("repo").lower() not in {r.lower() for r in uc["repos"]}:
        raise OffAllowlist(f"{m.group('repo')} is not a tracked repository for {use_case}")
    return canon


HIGH_DATE = ("META", "MACHINE_TIME")


def claim_text(record_type: str, f: dict, date: str | None = "__from_fields__") -> str:
    """Tool-independent fingerprint text: the claims, not the bytes, so markdown vs HTML from two tools is one record.
    A date taken from rendered text may belong to another element or time zone, so only machine-readable dates enter it."""
    if date == "__from_fields__":
        date = f.get("date") if f.get("date_confidence") in HIGH_DATE else None
    return "\n".join([record_type, pagefields.norm(f.get("title")) or "", date or "", f.get("tag") or ""])


def _same_claim_row(con, canon: str, rt: str, f: dict):
    """An existing version with the same title and tag, whatever date it carries (recomputed from its stored date)."""
    for row in con.execute("SELECT id, collector, content_hash, source_published_at, published_confidence, first_seen_at FROM bt_capture_provenance "
                           "WHERE canonical_origin=? ORDER BY id DESC", (canon,)):
        d = None
        if row["source_published_at"] is not None and row["published_confidence"] in HIGH_DATE:
            d = pagefields.datetime.fromtimestamp(row["source_published_at"], pagefields.timezone.utc).date().isoformat()
        if captures.content_hash(claim_text(rt, f, d)) == row["content_hash"]:
            return row, d
    return None, None


def record_page(con, *, use_case: str, collector: str, url: str, view: dict, captured_at: float, run_id: str | None = None,
                robot_id: str | None = None, raw_ref: str | None = None, proof: str = "NONE", proof_observed_at: float | None = None,
                evidence_only: bool = False, policy: dict | None = None) -> dict:
    policy = policy or load_policy()
    if collector in EVIDENCE_ONLY_COLLECTORS and not evidence_only:
        raise PermissionError(f"{collector} is not an adopted runtime collector")
    if collector not in RUNTIME_COLLECTORS + EVIDENCE_ONLY_COLLECTORS:
        raise ValueError(f"unknown collector {collector}")
    if not policy.get("collectors_enabled") and not evidence_only:
        raise PermissionError("collectors disabled by policy")
    canon = allowed(use_case, view.get("final_url") or url)       # a redirect off the allowlist is refused too
    f = pagefields.extract(view)
    if not f["title"] and not f["date"] and not f["tag"]:
        return {"recorded": False, "reason": "EMPTY_EXTRACTION", "canonical_origin": canon}
    rt = USE_CASES[use_case]["record_type"]
    status = "OK" if f["title"] and f["date"] else "INCOMPLETE"
    if f["date_confidence"] not in HIGH_DATE:
        # a lower-confidence (rendered) date never creates a version next to the same title/tag already on record
        prior, prior_date = _same_claim_row(con, canon, rt, f)
        if prior is not None:
            return {"recorded": False, "duplicate": True, "id": prior["id"], "new": False, "duplicate_of_collector": prior["collector"],
                    "canonical_origin": canon, "first_seen_at": prior["first_seen_at"], "independent_confirmation": False, "fields": f,
                    "date_disagreement": None if (f["date"] in (None, prior_date) or prior_date is None) else {"low_confidence": f["date"], "on_record": prior_date}}
    else:
        prior, prior_date = _same_claim_row(con, canon, rt, f)
        if prior is not None and prior_date is None:
            # same title/tag already on record with only a rendered (or no) date: this row refines the date of the same
            # page version; it is not a page revision and never a second source
            status = "REFINED_DATE"
    r = captures.record_capture(con, collector=collector, source_url=canon, text=claim_text(rt, f), captured_at=captured_at,
                                source_published_at=pagefields.date_epoch(f["date"]), published_confidence=f["date_confidence"],
                                robot_id=robot_id, run_id=run_id, extractor_version=f["extractor_version"], raw_ref=raw_ref, record_type=rt,
                                claim_state="CLAIM", extraction_status=status, historical_asof_proof=proof, proof_observed_at=proof_observed_at)
    return {"recorded": r["new"], "duplicate": not r["new"], "fields": f, **r}


SENSITIVE_NAMES = r"(?:api[_-]?key|apikey|access[_-]?token|refresh[_-]?token|id[_-]?token|token|client[_-]?secret|secret|password|passwd|pwd|auth|authorization|key|signature|sig)"
KEY_PREFIXES = ("fc-", "sk-", "sk_", "pk_", "rk_", "ghp_", "gho_", "ghs_", "ghu_", "github_pat_", "xoxb-", "xoxp-", "xoxa-", "AKIA", "ASIA", "AIza", "eyJ", "hf_", "glpat-")


def _public_address(seg: str) -> bool:
    from .. import quality
    return 32 <= len(seg) <= 44 and quality.b58_len(seg) == 32          # a Solana public key (mint, pool, wallet)


def _hash_or_signature(seg: str) -> bool:
    """Public identifiers that look random: hex digests (40/64) and base58 transaction signatures (64 bytes)."""
    from .. import quality
    return bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", seg)) or (len(seg) >= 80 and quality.b58_len(seg) == 64)


def looks_like_secret(seg: str) -> bool:
    """A credential-shaped token: a known key prefix, a UUID, a bot token, or a long run of letters and digits that is
    not a public address, digest or signature."""
    seg = seg.strip("'\"")
    if len(seg) >= 12 and seg.startswith(KEY_PREFIXES):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", seg):
        return True                                   # UUID-shaped API keys
    if re.fullmatch(r"\d{6,12}:[A-Za-z0-9_\-]{30,}", seg):
        return True                                   # bot tokens (id:secret)
    if _public_address(seg) or _hash_or_signature(seg):
        return False
    return len(seg) >= 40 and re.fullmatch(r"[A-Za-z0-9_\-.+/=]+", seg) is not None and re.search(r"\d", seg) is not None and seg.count("-") <= 1


CREDENTIAL_WORDS = r"(?:api[ _-]?key|apikey|key|token|secret|password|passwd|credentials?|bearer|authorization|auth|signing key|private key)"


def redact_url(url) -> str | None:
    """Scheme, host and path only: query strings, fragments, user:password parts and credential-shaped path segments
    never leave this module (Phase 16, D8 and N4)."""
    if not url:
        return url
    from urllib.parse import urlsplit, urlunsplit
    try:
        u = urlsplit(str(url))
        host = (u.hostname or "") + (f":{u.port}" if u.port else "")
        path = "/".join("[removed]" if looks_like_secret(x) else x for x in u.path.split("/"))
        return urlunsplit((u.scheme, host, path, "", "")) + (" [query removed]" if u.query else "")
    except ValueError:
        return "[unparseable url removed]"


def redact_text(text, url=None) -> str | None:
    """Error and status text with credentials removed: the request URL, Authorization values, name=value and
    "name": "value" pairs with a sensitive name, user:password in URLs, and bare key-shaped tokens."""
    if text is None:
        return None
    t = str(text)
    if url:
        t = t.replace(str(url), redact_url(url) or "")
    # Authorization schemes: the value only when it looks like a credential (a digit or base64 padding, or 20+ characters)
    t = re.sub(r"(?i)\b(bearer|basic|token)(\s+)([A-Za-z0-9._~+/=\-:]{8,})",
               lambda m: m.group(1) + m.group(2) + ("[removed]" if (re.search(r"[\d=+/]", m.group(3)) or len(m.group(3)) >= 20)
                                                     and not _public_address(m.group(3)) and not _hash_or_signature(m.group(3)) else m.group(3)), t)
    # a 16+ character value right after a credential word ("key abc...", "credential: abc...")
    t = re.sub(r"(?i)\b(" + CREDENTIAL_WORDS + r")\b(\s*(?:is\s+|[:=]\s*)?[\"']?)([A-Za-z0-9._~+/=\-:]{16,})",
               lambda m: m.group(1) + m.group(2) + ("[removed]" if not (_public_address(m.group(3)) or _hash_or_signature(m.group(3))) else m.group(3)), t)
    t = re.sub(r"//[^/@\s'\"]+@", "//REDACTED@", t)
    t = re.sub(r"(?i)([\"']?" + SENSITIVE_NAMES + r"[\"']?\s*[:=]\s*[\"']?)([^\"'&\s,;}]+)", r"\1[removed]", t)
    t = re.sub(r"https?://[^\s'\"<>]+", lambda m: redact_url(m.group(0)) or "", t)
    return re.sub(r"[A-Za-z0-9_\-.+/=]{12,}", lambda m: "[removed]" if looks_like_secret(m.group(0)) else m.group(0), t)


_redact_text = redact_text


def ingest_batch(con, use_case: str, collector: str, results: list[dict], captured_at: float, run_id: str | None = None,
                 evidence_only: bool = False, policy: dict | None = None) -> dict:
    """results: [{"url", "status" (HTTP or tool status), "view" (or None), "error", "partial": bool}]. Bounded by the
    use case's page cap. Returns a source status; DEGRADED/DOWN never produces a record or a signal."""
    cap = USE_CASES[use_case]["max_pages_per_run"]
    out = {"recorded": 0, "duplicates": 0, "refused_off_allowlist": 0, "failed": 0, "empty": 0, "partial": 0, "over_cap": 0, "rows": []}
    for i, res in enumerate(results):
        if i >= cap:
            out["over_cap"] += 1
            continue
        if res.get("partial"):
            out["partial"] += 1
        if res.get("status") != 200 or res.get("error") or not res.get("view"):
            out["failed"] += 1
            out["rows"].append({"url": redact_url(res.get("url")), "state": "FETCH_FAILED", "status": res.get("status"), "error": _redact_text(res.get("error"), res.get("url"))})
            continue
        try:
            r = record_page(con, use_case=use_case, collector=collector, url=res["url"], view=res["view"], captured_at=captured_at,
                            run_id=run_id, raw_ref=res.get("raw_ref"), evidence_only=evidence_only, policy=policy)
        except OffAllowlist as e:
            out["refused_off_allowlist"] += 1
            out["rows"].append({"url": redact_url(res.get("url")), "state": "OFF_ALLOWLIST", "error": _redact_text(str(e), res.get("url"))})
            continue
        if not r.get("recorded") and r.get("reason") == "EMPTY_EXTRACTION":
            out["empty"] += 1
        elif r.get("duplicate"):
            out["duplicates"] += 1
        else:
            out["recorded"] += 1
        out["rows"].append({"url": redact_url(res["url"]), "state": "RECORDED" if r.get("recorded") else (r.get("reason") or "DUPLICATE"), "id": r.get("id"),
                            "version": r.get("version"), "first_seen_at": r.get("first_seen_at")})
    con.commit()
    n = len(results)
    bad = out["failed"] + out["refused_off_allowlist"] + out["empty"]
    out["source_status"] = "DOWN" if n and bad == n else ("DEGRADED" if bad or out["partial"] or out["over_cap"] else "OK")
    return out


def catalyst_records(con, use_case: str = "project_catalyst_watch") -> list[dict]:
    """Capture versions as catalyst records for CatalystVerified. No mint is attached here (mint linking needs
    independent verification), so these records alone can never trigger an entry: they are claims with a known-at time."""
    rt = USE_CASES[use_case]["record_type"]
    out = []
    for r in con.execute("SELECT * FROM bt_capture_provenance WHERE record_type=? ORDER BY available_at, id", (rt,)):
        out.append({"event_id": f"cap{r['id']}", "chain": r["chain"], "mint": r["mint"], "origin_group": r["origin_group"], "claim_type": rt.upper(),
                    "published_at": r["source_published_at"], "first_seen_at": r["first_seen_at"], "event_time": r["source_published_at"] or r["first_seen_at"],
                    "available_at": r["available_at"], "verified": False, "denied": False, "mint_verified": bool(r["mint_verified"]),
                    "sentiment": 0, "historical_asof_proof": r["historical_asof_proof"], "collector": r["collector"]})
    return out

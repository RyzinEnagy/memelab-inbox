"""Safe import of a permitted list (leaderboard export or analyst list) into the registry. Schema memelab.social.registry.import/1.

What a file may contain (anything else is refused, whole-file or per row, and nothing is written for a refused file):
  {"schema": "memelab.social.registry.import/1",
   "source":  {"source_key", "kind": LEADERBOARD|ANALYST_LIST, "organization", "url", "access_mode": file|api|fixture,
               "permitted_basis", "is_fixture", "fixture_label", "max_age_seconds"},
   "capture": {"captured_at", "url", "period": {"start", "end", "stated"}},
   "rows":    [{"rank", "wallet": {"chain","address"}, "handle": {"platform","handle","provider_user_id","profile_url"},
                "display_name", "metrics": {name: number}, "row_url"}]}
A CSV file works with --meta (a JSON file holding schema, source and capture). CSV columns: rank, wallet_chain, wallet_address,
platform, handle, provider_user_id, profile_url, display_name, row_url, metric_<name>.

Whole-file refusals (code): FILE_TOO_LARGE, NOT_JSON, BAD_SCHEMA, UNKNOWN_KEY, BAD_SOURCE, BAD_CAPTURE, TOO_MANY_ROWS,
UNLABELLED_FIXTURE, CAPTURED_IN_FUTURE.
Per-row rejections (code): BLOCKED_CONTENT_KEY, UNKNOWN_ROW_KEY, NO_IDENTIFIER, INVALID_WALLET, UNSUPPORTED_PLATFORM, INVALID_HANDLE,
INVALID_METRIC, INVALID_RANK, INVALID_URL.
Per-row flags (kept, not rejected): duplicate_rank, duplicate_identifier, platform_link_missing, no_wallet, display_name_unusable.

What an import never does: approve anyone, assign a category, mark a wallet as owned, rank anyone, or touch the network. A row that names a
handle and a wallet creates a LOW-confidence third-party label that stays unreviewed until a person reviews it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

from . import registry as R, store
from .ingest import BLOCKED_KEYS

SCHEMA = "memelab.social.registry.import/1"
MAX_BYTES = 5_000_000
MAX_ROWS = 5000
FUTURE_SKEW = 300.0
TOP_KEYS = {"schema", "source", "capture", "rows"}
SOURCE_KEYS = {"source_key", "kind", "organization", "url", "access_mode", "permitted_basis", "is_fixture", "fixture_label", "max_age_seconds"}
CAPTURE_KEYS = {"captured_at", "url", "period"}
ROW_KEYS = {"rank", "wallet", "handle", "display_name", "metrics", "row_url"}
HANDLE_KEYS = {"platform", "handle", "provider_user_id", "profile_url"}
HANDLE_RE = {"x": re.compile(r"^[A-Za-z0-9_]{1,15}$")}
HANDLE_DEFAULT = re.compile(r"^[A-Za-z0-9_.]{1,50}$")
METRIC_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
FIXTURE_HOSTS = {"example.com", "example.org", "example.net"}


class ImportRefused(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _https(url, field: str, required: bool = False) -> str | None:
    if url in (None, ""):
        if required:
            raise ImportRefused("BAD_SOURCE", f"{field} is required")
        return None
    u = urlparse(str(url))
    if u.scheme != "https" or not u.hostname or len(str(url)) > 300 or re.search(r"\s", str(url)):
        raise ImportRefused("BAD_SOURCE", f"{field} must be an https URL")
    return str(url)


def _is_fixture_url(url: str | None) -> bool:
    h = _host(url) if url else ""
    return bool(h) and (h.endswith(".invalid") or h in FIXTURE_HOSTS)


def read_file(path: str | Path, meta: str | Path | None = None) -> tuple[dict, str]:
    p = Path(path)
    raw = p.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ImportRefused("FILE_TOO_LARGE", f"{len(raw)} bytes; limit {MAX_BYTES}")
    sha = hashlib.sha256(raw).hexdigest()
    if p.suffix.lower() == ".csv":
        if meta is None:
            raise ImportRefused("BAD_SCHEMA", "a CSV needs --meta with the schema, source and capture blocks")
        doc = _json(Path(meta).read_bytes())
        if not isinstance(doc, dict) or "rows" in doc:
            raise ImportRefused("BAD_SCHEMA", "the meta file holds schema, source and capture only")
        doc["rows"] = _csv_rows(raw.decode("utf-8-sig"))
        sha = hashlib.sha256(raw + Path(meta).read_bytes()).hexdigest()
        return doc, sha
    return _json(raw), sha


def _json(raw: bytes):
    def bad(x):
        raise ValueError(f"non-finite number {x}")
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=bad)
    except Exception as e:
        raise ImportRefused("NOT_JSON", str(e)[:120])


def _csv_rows(text: str) -> list[dict]:
    rows = []
    for rec in csv.DictReader(text.splitlines()):
        row: dict = {}
        metrics: dict = {}
        w, h = {}, {}
        for k, v in rec.items():
            if k is None or v is None or v.strip() == "":
                continue
            v = v.strip()
            if k == "rank":
                row["rank"] = int(v) if re.fullmatch(r"-?\d+", v) else v
            elif k == "wallet_chain":
                w["chain"] = v
            elif k == "wallet_address":
                w["address"] = v
            elif k in ("platform", "handle", "provider_user_id", "profile_url"):
                h[k] = v
            elif k in ("display_name", "row_url"):
                row[k] = v
            elif k.startswith("metric_"):
                try:
                    metrics[k[7:]] = float(v)
                except ValueError:
                    metrics[k[7:]] = v          # kept so the row is rejected as INVALID_METRIC, not silently dropped
            else:
                row[k] = v                       # unknown column: rejected per row
        if w:
            row["wallet"] = w
        if h:
            row["handle"] = h
        if metrics:
            row["metrics"] = metrics
        rows.append(row)
    return rows


def validate_header(doc, now: float) -> dict:
    """Whole-file checks. Returns the normalized source and capture blocks."""
    if not isinstance(doc, dict):
        raise ImportRefused("BAD_SCHEMA", "top level must be an object")
    if doc.get("schema") != SCHEMA:
        raise ImportRefused("BAD_SCHEMA", f"schema must be {SCHEMA}")
    extra = sorted(set(doc) - TOP_KEYS)
    if extra:
        raise ImportRefused("UNKNOWN_KEY", "top level: " + ", ".join(extra))
    src, cap, rows = doc.get("source"), doc.get("capture") or {}, doc.get("rows")
    if not isinstance(src, dict) or not isinstance(cap, dict) or not isinstance(rows, list):
        raise ImportRefused("BAD_SCHEMA", "source and capture must be objects and rows a list")
    for blk, allowed, nm in ((src, SOURCE_KEYS, "source"), (cap, CAPTURE_KEYS, "capture")):
        extra = sorted(set(blk) - allowed)
        if extra:
            raise ImportRefused("UNKNOWN_KEY", f"{nm}: " + ", ".join(extra))
    if len(rows) > MAX_ROWS:
        raise ImportRefused("TOO_MANY_ROWS", f"{len(rows)} rows; limit {MAX_ROWS}")
    key = src.get("source_key")
    if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9:_.\-]{2,60}", key):
        raise ImportRefused("BAD_SOURCE", "source_key: 3 to 61 characters of a-z 0-9 : _ . -")
    kind = src.get("kind")
    if kind not in ("LEADERBOARD", "ANALYST_LIST"):
        raise ImportRefused("BAD_SOURCE", "kind must be LEADERBOARD or ANALYST_LIST")
    mode = src.get("access_mode")
    if mode not in ("file", "api", "fixture"):
        raise ImportRefused("BAD_SOURCE", "access_mode must be file, api or fixture")
    try:
        org = R.clean_text(src.get("organization"), "organization", 80)
        basis = R.clean_text(src.get("permitted_basis"), "permitted_basis", 300)
        fx = R.clean_text(src.get("fixture_label"), "fixture_label", 120)
    except ValueError as e:
        raise ImportRefused("BAD_SOURCE", str(e))
    if not org or not basis:
        raise ImportRefused("BAD_SOURCE", "organization and permitted_basis are required")
    is_fx = bool(src.get("is_fixture", False))
    if not isinstance(src.get("is_fixture", False), bool):
        raise ImportRefused("BAD_SOURCE", "is_fixture must be true or false")
    if is_fx and (not fx or mode != "fixture"):
        raise ImportRefused("BAD_SOURCE", "a fixture needs a fixture_label and access_mode 'fixture'")
    if not is_fx and mode == "fixture":
        raise ImportRefused("BAD_SOURCE", "access_mode 'fixture' needs is_fixture true")
    surl, curl = _https(src.get("url"), "source.url"), _https(cap.get("url"), "capture.url")
    if not is_fx and (_is_fixture_url(surl) or _is_fixture_url(curl)):
        raise ImportRefused("UNLABELLED_FIXTURE", "an example or .invalid URL means demonstration data; set is_fixture and fixture_label")
    maxage = src.get("max_age_seconds")
    if maxage is not None and (isinstance(maxage, bool) or not isinstance(maxage, int) or not 3600 <= maxage <= 365 * 86400):
        raise ImportRefused("BAD_SOURCE", "max_age_seconds must be an integer from 3600 to 31536000")
    try:
        captured = store.to_utc(cap.get("captured_at"))
        period = cap.get("period") or {}
        if not isinstance(period, dict) or set(period) - {"start", "end", "stated"}:
            raise ValueError("period holds start, end and stated only")
        ps, pe = store.to_utc(period.get("start")), store.to_utc(period.get("end"))
        stated = R.clean_text(period.get("stated"), "period.stated", 60)
    except (ValueError, TypeError) as e:
        raise ImportRefused("BAD_CAPTURE", str(e))
    if captured is not None and captured > now + FUTURE_SKEW:
        raise ImportRefused("CAPTURED_IN_FUTURE", f"captured_at {captured} is after the clock {now}")
    if ps is not None and pe is not None and pe < ps:
        raise ImportRefused("BAD_CAPTURE", "period end is before period start")
    return {"source_key": key, "kind": kind, "access_mode": mode, "organization": org, "permitted_basis": basis, "is_fixture": is_fx,
            "fixture_label": fx, "url": surl, "max_age": maxage, "captured_at": captured, "capture_url": curl, "period_start": ps,
            "period_end": pe, "stated_period": stated}


def validate_row(row, idx: int) -> tuple[dict | None, str | None]:
    """Returns (normalized row, None) or (None, reject code)."""
    if not isinstance(row, dict):
        return None, "UNKNOWN_ROW_KEY"
    if BLOCKED_KEYS & set(row):
        return None, "BLOCKED_CONTENT_KEY"
    if set(row) - ROW_KEYS:
        return None, "UNKNOWN_ROW_KEY"
    out: dict = {"index": idx, "rank": None, "wallet": None, "handle": None, "platform": None, "provider_user_id": None, "profile_url": None,
                 "display_name": None, "metrics": {}, "row_url": None, "flags": []}
    rank = row.get("rank")
    if rank is not None:
        if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 1_000_000:
            return None, "INVALID_RANK"
        out["rank"] = rank
    w = row.get("wallet")
    if w is not None:
        if not isinstance(w, dict) or set(w) - {"chain", "address"} or not w.get("chain") or not w.get("address"):
            return None, "INVALID_WALLET"
        try:
            chain = str(w["chain"]).strip().lower()
            if chain not in R.chain_registry.CHAINS:
                return None, "INVALID_WALLET"
            out["wallet"] = (chain, store.normalize_contract(chain, str(w["address"])))
        except ValueError:
            return None, "INVALID_WALLET"
    h = row.get("handle")
    if h is not None:
        if not isinstance(h, dict) or set(h) - HANDLE_KEYS:
            return None, "INVALID_HANDLE"
        plat = (str(h["platform"]).strip().lower() if h.get("platform") else None)
        hd = (str(h["handle"]).strip().lstrip("@") if h.get("handle") else None)
        pid = str(h["provider_user_id"]).strip() if h.get("provider_user_id") else None
        if plat and plat not in R.PLATFORMS:
            return None, "UNSUPPORTED_PLATFORM"
        if hd and not (HANDLE_RE.get(plat, HANDLE_DEFAULT)).match(hd):
            return None, "INVALID_HANDLE"
        if pid and not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", pid):
            return None, "INVALID_HANDLE"
        try:
            pu = _https(h.get("profile_url"), "profile_url")
        except ImportRefused:
            return None, "INVALID_URL"
        out.update(platform=plat, handle=hd, provider_user_id=pid, profile_url=pu)
    dn = row.get("display_name")
    if dn is not None:
        dn = re.sub(r"\s+", " ", str(dn)).strip()
        try:
            out["display_name"] = R.clean_text(dn, "display_name", 80)
        except ValueError:
            out["display_name"] = None
            out["flags"].append("display_name_unusable")
    try:
        out["row_url"] = _https(row.get("row_url"), "row_url")
    except ImportRefused:
        return None, "INVALID_URL"
    m = row.get("metrics")
    if m is not None:
        if not isinstance(m, dict) or len(m) > 12:
            return None, "INVALID_METRIC"
        for k, v in m.items():
            if not METRIC_RE.match(str(k)) or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                return None, "INVALID_METRIC"
        out["metrics"] = {str(k): v for k, v in sorted(m.items())}
    has_account = bool(out["platform"] and (out["handle"] or out["provider_user_id"]))
    if out["wallet"] is None and not has_account and not out["display_name"] and not out["handle"]:
        return None, "NO_IDENTIFIER"
    if out["wallet"] is None:
        out["flags"].append("no_wallet")
    if not has_account:
        out["flags"].append("platform_link_missing")
    return out, None


def _ident(r: dict) -> tuple:
    if r["wallet"]:
        return ("w",) + r["wallet"]
    if r["platform"] and (r["provider_user_id"] or r["handle"]):
        return ("h", r["platform"], r["provider_user_id"] or r["handle"].lower())
    return ("n", (r["display_name"] or r["handle"] or "").lower())


def _ident_text(i: tuple) -> str:
    if i[0] == "w":
        return f"w:{i[1]}:{i[2]}"
    if i[0] == "h":
        return f"h:{i[1]}:{i[2]}"
    return "n:" + hashlib.sha256(i[1].encode()).hexdigest()[:12]


def import_file(con, path: str | Path, *, meta: str | Path | None = None, dry_run: bool = False, now: float | None = None) -> dict:
    t = R._now(now)
    try:
        doc, sha = read_file(path, meta)
        h = validate_header(doc, t)
        if not h["is_fixture"] and "/tests/fixtures/" in str(Path(path).resolve()).replace("\\", "/"):
            raise ImportRefused("UNLABELLED_FIXTURE", "the file sits under tests/fixtures but is not labelled as a fixture")
    except ImportRefused as e:
        return {"status": "REFUSED", "code": e.code, "detail": e.detail, "written": False}
    ckey = R._sha(h["source_key"], h["captured_at"], sha)
    if con.execute("SELECT capture_id FROM social_registry_captures WHERE capture_key=?", (ckey,)).fetchone():
        cid = con.execute("SELECT capture_id FROM social_registry_captures WHERE capture_key=?", (ckey,)).fetchone()[0]
        return {"status": "ALREADY_IMPORTED", "capture_id": cid, "written": False}
    fxl = h["fixture_label"] if h["is_fixture"] else None
    good, rejects = [], []
    for i, row in enumerate(doc["rows"]):
        r, code = validate_row(row, i)
        if code:
            rejects.append({"row": i, "code": code})
        else:
            good.append(r)
    seen_ident: dict = {}
    rank_count: dict = {}
    for r in good:
        if r["rank"] is not None:
            rank_count[r["rank"]] = rank_count.get(r["rank"], 0) + 1
    for r in good:
        ident = _ident(r)
        if ident in seen_ident:
            r["flags"].append("duplicate_identifier")
        seen_ident.setdefault(ident, r["index"])
        if r["rank"] is not None and rank_count[r["rank"]] > 1:
            r["flags"].append("duplicate_rank")
    summary = {"entities_new": 0, "links_new": 0, "listings": 0}
    cap_id = None
    con.execute("SAVEPOINT reg_import")
    try:
        org = R.ensure_org(con, h["source_key"], h["organization"], fixture_label=fxl, now=t)
        R.register_source(con, source_key=h["source_key"], source_kind=h["kind"], access_mode=h["access_mode"], permitted_basis=h["permitted_basis"],
                          url=h["url"], organization_entity_id=org, max_age_seconds=h["max_age"], is_fixture=h["is_fixture"], now=t)
        cur = con.execute(
            "INSERT INTO social_registry_captures(capture_key,source_key,captured_at,captured_at_basis,period_start,period_end,stated_period,url,"
            "file_sha256,rows_total,rows_accepted,rows_rejected,rejects_json,imported_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ckey, h["source_key"], h["captured_at"], "STATED_BY_FILE" if h["captured_at"] is not None else "UNKNOWN", h["period_start"],
             h["period_end"], h["stated_period"], h["capture_url"] or h["url"], sha, len(doc["rows"]), len(good), len(rejects),
             json.dumps(rejects), t, int(h["is_fixture"])))
        cap_id = cur.lastrowid
        before_e = con.execute("SELECT COUNT(*) FROM social_registry_entities").fetchone()[0]
        before_l = con.execute("SELECT COUNT(*) FROM social_registry_links").fetchone()[0]
        for r in good:
            _store_row(con, r, h, org, cap_id, fxl, t)
            summary["listings"] += 1
        summary["entities_new"] = con.execute("SELECT COUNT(*) FROM social_registry_entities").fetchone()[0] - before_e
        summary["links_new"] = con.execute("SELECT COUNT(*) FROM social_registry_links").fetchone()[0] - before_l
        R._log(con, "IMPORT", cap_id, "IMPORT", "importer:registry-import-v1", f"{len(good)} accepted, {len(rejects)} rejected", t)
        if dry_run:
            con.execute("ROLLBACK TO reg_import")
    except BaseException:
        con.execute("ROLLBACK TO reg_import")
        con.execute("RELEASE reg_import")
        raise
    con.execute("RELEASE reg_import")
    flags: dict = {}
    for r in good:
        for f in r["flags"]:
            flags[f] = flags.get(f, 0) + 1
    fresh = R.capture_freshness({"captured_at": h["captured_at"], "period_end": h["period_end"]}, h["max_age"], t)
    return {"status": "DRY_RUN" if dry_run else "IMPORTED", "written": not dry_run, "capture_id": None if dry_run else cap_id,
            "source_key": h["source_key"], "is_fixture": h["is_fixture"], "fixture_label": fxl, "freshness": fresh,
            "captured_at": h["captured_at"], "rows_total": len(doc["rows"]), "rows_accepted": len(good), "rows_rejected": len(rejects),
            "rejects": rejects, "row_flags": flags, **summary,
            "never_done": ["approve", "assign category", "mark wallet as owned", "rank"]}


def _store_row(con, r: dict, h: dict, org: str, cap_id: int, fxl: str | None, t: float) -> None:
    ident = _ident(r)
    label = r["display_name"] or (f"@{r['handle']}" if r["handle"] else None) or (f"{r['wallet'][0]} {r['wallet'][1][:6]}...{r['wallet'][1][-4:]}" if r["wallet"] else f"line {r['index']}")
    cand = R.ensure_candidate(con, h["source_key"], _ident_text(ident), label, fixture_label=fxl, now=t)
    wallet = R.ensure_wallet(con, *r["wallet"], fixture_label=fxl, now=t) if r["wallet"] else None
    account = None
    if r["platform"] and (r["handle"] or r["provider_user_id"]):
        account = R.ensure_account(con, r["platform"], handle=r["handle"], provider_user_id=r["provider_user_id"], display_name=r["display_name"],
                                   profile_url=r["profile_url"], fixture_label=fxl, now=t)
    cur = con.execute(
        "INSERT INTO social_registry_listings(capture_id,row_index,candidate_entity_id,rank_claimed,metrics_json,display_name_seen,wallet_chain,wallet_address,"
        "platform_seen,handle_seen,profile_url,row_url,flags_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cap_id, r["index"], cand, r["rank"], json.dumps(r["metrics"], sort_keys=True) if r["metrics"] else None, r["display_name"],
         r["wallet"][0] if r["wallet"] else None, r["wallet"][1] if r["wallet"] else None, r["platform"], r["handle"], r["profile_url"], r["row_url"],
         json.dumps(sorted(set(r["flags"])))))
    lid = cur.lastrowid
    ref = f"listing:{lid}"
    ev_url = r["row_url"] or h["capture_url"] or h["url"]
    for ent in [cand, wallet, account]:
        if ent:
            R.add_evidence(con, ent, "LEADERBOARD_LISTING", ref, url=ev_url, source_key=h["source_key"], capture_id=cap_id,
                           captured_at=h["captured_at"], now=t)
    R.add_link(con, link_type="LISTED_BY", from_entity=cand, to_entity=org, basis="LEADERBOARD_LISTING", capture_id=cap_id,
               source_key=h["source_key"], recorded_by="importer:registry-import-v1", asserted_at=h["captured_at"], now=t)
    target = wallet or account
    if target:
        R.add_link(con, link_type="OBSERVED_AS", from_entity=cand, to_entity=target, basis="LEADERBOARD_LISTING", capture_id=cap_id,
                   source_key=h["source_key"], recorded_by="importer:registry-import-v1", asserted_at=h["captured_at"], now=t)
    if wallet and account:
        R.add_link(con, link_type="WALLET_THIRD_PARTY_LABEL", from_entity=account, to_entity=wallet, asserted_by=org,
                   basis="LEADERBOARD_LISTING", evidence_ref=ref, confidence="LOW", capture_id=cap_id, source_key=h["source_key"],
                   asserted_at=h["captured_at"], recorded_by="importer:registry-import-v1",
                   note="the list shows this handle next to this wallet; unreviewed", now=t)

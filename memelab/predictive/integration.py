"""Phase 17: integration-1, the request flow from a discovered or changed opportunity to a forecast or a visible abstention
(research only, flag OFF, imported only by the two helpers of `memelab/cli.py`).

Pre-registration: audits/predictive-intelligence/phase_17/ACCEPTANCE_CHECKLIST.md (rules 1 to 17) and PI-D-093. In short:
  - a trigger is one `pipeline.analyze_token` result; its decision snapshot is the thesis row the pipeline persisted, read back
    read-only; `snapshot_hash` is `decisions.row_sha256` of that row; the decision time is the capture time (CAPTURE_TIME);
  - exactly one request record per trigger (DISCOVERY, MATERIAL_CHANGE, UNCHANGED, DUPLICATE, SUPERSEDED_IN_PASS, DEFERRED_*,
    NO_DECISION_SNAPSHOT, NOT_EXACT_IDENTITY or ERROR); an attempted event gets exactly one contract document and one
    abstention-1 record per primary target, `forecast_id` from `contract.forecast_id` (P35);
  - a material-change gate, a bounded pass (64 attempts, one per chain and mint, 30 s), no socket of its own and reads only for
    a served champion through `runtime.CallGuard` with cost cap 0 (P48), visible states for every outage (P47);
  - every target is resolved only through `registry.serve`, every document through `abstention.forecast_result`, checked by
    `abstention.validate_publication` with its record, by `check_document` (no document without its record, Phase 13 m4) and
    by `verify_point` (the published point recomputed from the raw number this module keeps, Phase 13 m3, PI-D-068);
  - decision support beside it (`onchain.decision_support`): every lab fatal flag and a backtest fatal or untradeable
    assessment stay vetoes; no position size ever comes from a forecast (P44);
  - nothing here feeds the 100-point score, the fatal flags, the status, the watchlist or the scout lists (PI-D-017).
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from . import abstention as AB
from . import baselines as B
from . import bt_adapter as BT
from . import calibration as CAL
from . import contract as C
from . import decisions as D
from . import depth_adapter as DA
from . import features as F
from . import labels as L
from . import onchain as O
from . import registry as R
from . import runtime as RT
from . import store as S

PHASE = "17"
INTEGRATION_VERSION = "integration-1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = "audits/predictive-intelligence/phase_16/registry"
CALIBRATION_CARD_FILES = {L.T1: "audits/predictive-intelligence/phase_13/artifacts/T1_24h/CALIBRATION_CARD.json",
                          L.T1B: "audits/predictive-intelligence/phase_13/artifacts/T1b_6h/CALIBRATION_CARD.json",
                          L.T2: "audits/predictive-intelligence/phase_13/artifacts/T2_24h/CALIBRATION_CARD.json"}
SYNTHETIC_PROBE = "tests/fixtures/predictive/registry_probe_examples.json"
SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}
PRIMARY = tuple(C.PRIMARY)
FAMILY = "07"                                   # the only family integration-1 can build features for (rule 7)
LIMITS = C.ACCEPTANCE["api_limits"]
FROZEN = {
    "queue_max": 64, "per_mint_per_pass": 1, "pass_budget_s": 30.0,
    "reads_per_request": LIMITS["inference_reads_per_request"], "reader_timeout_s": float(LIMITS["inference_timeout_s"]),
    "calls_per_minute": LIMITS["geckoterminal_calls_per_min"], "calls_per_pass": 64,
    "breaker_failures": LIMITS["breaker_consecutive_failures"], "cost_cap_usd": 0.0,
    "stale_input_s": 7200.0,
    "material": {"score_abs": 5, "price_rel": 0.10, "liquidity_rel": 0.20, "volume_rel": 0.50, "max_age_s": 3600.0},
    "catalyst": {"link_types": ["OFFICIAL", "NAMED_IN_SOURCE"], "strength": "STRONG", "refresh_min_interval_s": 3600.0},
    "decision_support": {"max_loss": 0.05, "max_age_s": 3600.0},
}
ATTEMPTED = ("DISCOVERY", "MATERIAL_CHANGE")
EVENTS = ATTEMPTED + ("UNCHANGED", "DUPLICATE", "SUPERSEDED_IN_PASS", "DEFERRED_QUEUE_FULL", "DEFERRED_LATENCY_BUDGET",
                      "NO_DECISION_SNAPSHOT", "NOT_EXACT_IDENTITY", "ERROR", "CATALYST_REFRESH_REQUESTED", "CATALYST_IGNORED")
MODES = ("fast", "research")
FILES = {"requests": "REQUESTS.jsonl", "documents": "DOCUMENTS.jsonl", "records": "RECORDS.jsonl",
         "references": "REFERENCE_RECORDS.jsonl", "passes": "PASSES.jsonl"}
GENESIS = "0" * 64
NOT_ASSESSED = "NOT_ASSESSED"
INPUT_STALE = "INPUT_STALE"
TARGET_WORDS = {L.T1: "24 hours, +25% before -15%", L.T1B: "6 hours, +25% before -15%", L.T2: "24 hours, halving or halt"}


class IntegrationError(ValueError):
    pass


class StateTampered(IntegrationError):
    pass


def sha(o: Any) -> str:
    return AB.sha(o)


def _iso(t: float) -> str:
    return AB._iso(t)


def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _num_or_none(x: Any) -> float | None:
    return float(x) if _fin(x) else None


def _sealed(rec: dict) -> dict:
    rec = {k: v for k, v in rec.items() if k != "record_id"}
    rec["record_id"] = sha(rec)
    return rec


# ---------------------------------------------------------------- configuration (rule 1)
def config(config_path: str | Path | None = None) -> dict:
    """The flag (read by `contract.enabled`, malformed means OFF) and the optional keys of the `predictive` section."""
    on = C.enabled(config_path)
    sect: dict = {}
    if on:
        if config_path is None:
            from ..db import DATA_DIR
            config_path = DATA_DIR / "config.json"
        try:
            cfg = json.loads(Path(config_path).read_text())
            sect = cfg.get(C.FLAG_SECTION) if isinstance(cfg, dict) and isinstance(cfg.get(C.FLAG_SECTION), dict) else {}
        except (OSError, ValueError):
            sect = {}
    def _s(k):
        v = sect.get(k)
        return v if isinstance(v, str) and v else None
    mode = sect.get("mode") if sect.get("mode") in MODES else "fast"
    return {"enabled": on, "state_dir": _s("state_dir"), "mode": mode, "depth_db": _s("depth_db"), "backtest_db": _s("backtest_db"),
            "config_path": str(config_path) if config_path is not None else None}


def default_state_dir() -> Path:
    from ..db import DATA_DIR
    return Path(DATA_DIR) / "private" / "predictive"


def state_dir_refusal(state_dir: str | Path, root: Path = ROOT) -> str | None:
    """A state directory inside the repository is allowed only under data/private/ (gitignored): the pass never appends to a
    tracked path (CP17-0, PI-D-094). Outside the repository (a scratch folder) is allowed."""
    p, r = Path(state_dir).resolve(), Path(root).resolve()
    if p == r or r in p.parents:
        priv = (r / "data" / "private").resolve()
        if not (p == priv or priv in p.parents):
            return f"state directory {p} is inside the repository and not under data/private/"
    return None


# ---------------------------------------------------------------- state: append-only, sha-checked files (rule 14)
def _read_lines(p: Path) -> list[dict]:
    if not p.exists():
        return []
    text = p.read_text()
    if text and not text.endswith("\n"):
        raise StateTampered(f"{p.name}: partial last line")
    out = []
    for i, line in enumerate(text.splitlines()):
        try:
            r = json.loads(line)
        except ValueError:
            raise StateTampered(f"{p.name} line {i}: not JSON")
        if AB.canon(r) != line or r.get("record_id") != sha({k: v for k, v in r.items() if k != "record_id"}):
            raise StateTampered(f"{p.name} line {i}: content does not match its record id")
        out.append(r)
    return out


def load_state(state_dir: str | Path) -> dict:
    """Every file read and checked: each line's record id, the pass chain, and each file's sha256 equal to the one the last pass
    recorded. Anything else is StateTampered (rule 14)."""
    d = Path(state_dir)
    lines = {k: _read_lines(d / f) for k, f in FILES.items()}
    prev = GENESIS
    for i, p in enumerate(lines["passes"]):
        if p.get("seq") != i or p.get("prev") != prev:
            raise StateTampered(f"PASSES.jsonl line {i}: chain broken")
        prev = p["record_id"]
    last = lines["passes"][-1] if lines["passes"] else None
    for k, f in FILES.items():
        if k == "passes":
            continue
        want = (last or {}).get("files_after", {}).get(k)
        got = AB.file_sha(d / f)
        if got != want:
            raise StateTampered(f"{f}: sha256 {str(got)[:12]} differs from the last pass's {str(want)[:12]}")
    docs = {r["forecast_id"]: r for r in lines["documents"]}
    recs = {r["record_id"]: r for r in lines["records"]}
    last_attempt: dict[tuple[str, str], dict] = {}
    attempts: dict[tuple[str, str], list[dict]] = {}
    refreshed: dict[str, list[dict]] = {}
    for r in lines["requests"]:
        if r.get("event") in ATTEMPTED:
            last_attempt[(r["chain"], r["mint"])] = r
            attempts.setdefault((r["chain"], r["mint"]), []).append(r)
        if r.get("event") == "CATALYST_REFRESH_REQUESTED":
            refreshed.setdefault(r["mint"], []).append(r)
    return {"dir": d, "lines": lines, "documents": docs, "records": recs, "last_attempt": last_attempt, "attempts": attempts,
            "refreshed": refreshed,
            "last_pass": last, "prev": prev}


def _append_pass(state: dict, *, requests: list[dict], documents: list[dict], records: list[dict], references: list[dict],
                 pass_info: dict) -> dict:
    d: Path = state["dir"]
    d.mkdir(parents=True, exist_ok=True)
    last = state["last_pass"] or {}
    after = {}
    for k, rows in (("requests", requests), ("documents", documents), ("records", records), ("references", references)):
        p = d / FILES[k]
        want = (last.get("files_after") or {}).get(k)
        after[k] = AB.append(p, rows, expect_sha=want) if rows else AB.file_sha(p)
        if after[k] is None and p.exists():
            after[k] = AB.file_sha(p)
    seq = len(state["lines"]["passes"])
    pr = _sealed({"record_version": "integration-pass-1", "seq": seq, "prev": state["prev"], **pass_info, "files_after": after})
    want = AB.file_sha(d / FILES["passes"]) if state["lines"]["passes"] else None
    AB.append(d / FILES["passes"], [pr], expect_sha=want)
    return pr


# ---------------------------------------------------------------- inputs from the lab (rules 2, 9)
def connect_lab_ro(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    if not p.exists():
        raise IntegrationError("no lab database")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def _tables(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def decision_row(con: sqlite3.Connection, mint: str, created_at: float) -> tuple[dict | None, dict | None, int, int]:
    """(thesis row, token row, rows sharing the key, earlier thesis rows of the mint). The newest id is the row just persisted."""
    rows = [dict(r) for r in con.execute("SELECT * FROM theses WHERE mint=? AND created_at=? ORDER BY id DESC", (mint, float(created_at)))]
    tok = con.execute("SELECT * FROM tokens WHERE mint=?", (mint,)).fetchone()
    earlier = con.execute("SELECT COUNT(*) FROM theses WHERE mint=? AND created_at<?", (mint, float(created_at))).fetchone()[0]
    return (rows[0] if rows else None), (dict(tok) if tok else None), len(rows), int(earlier)


def catalyst_state(con: sqlite3.Connection | None, chain: str, mint: str, T: float) -> dict:
    """Exact-address catalyst links visible at T (PI-D-007): OFFICIAL or NAMED_IN_SOURCE, STRONG, same chain and mint byte for
    byte, linked and discovered at or before T. One event counts once (P15). Ticker and name links are context only."""
    if con is None or not {"catalyst_token_links", "catalyst_events"} <= _tables(con):
        return {"source_status": "CATALYST_SOURCE_NOT_AVAILABLE", "fingerprint": None, "exact_events": 0, "context_links": 0}
    cur = con.execute(
        "SELECT l.link_type, l.link_strength, l.linked_at, l.chain, l.mint, e.event_key, e.evidence_status, e.status, e.discovered_at "
        "FROM catalyst_token_links l JOIN catalyst_events e ON e.id = l.event_id WHERE l.chain=? AND l.mint=?", (chain, mint))
    names = [c[0] for c in cur.description]
    rows = [dict(zip(names, r)) for r in cur.fetchall()]
    rule = FROZEN["catalyst"]
    vis = [r for r in rows if r["mint"] == mint and r["chain"] == chain and _fin(r["linked_at"]) and r["linked_at"] <= T
           and _fin(r["discovered_at"]) and r["discovered_at"] <= T]
    exact = [r for r in vis if r["link_type"] in rule["link_types"] and r["link_strength"] == rule["strength"]]
    keys = sorted({(r["event_key"], r["link_type"], r["evidence_status"], r["status"]) for r in exact})
    return {"source_status": "OK", "fingerprint": sha(keys) if keys else None, "exact_events": len({r["event_key"] for r in exact}),
            "context_links": len(vis) - len(exact)}


# ---------------------------------------------------------------- registry (rule 7)
def runtime_facts() -> dict:
    """The running code's facts for family 07 only (integration-1 has no feature builder for families 08 to 11)."""
    return {"feature_set_sha": {FAMILY: F.feature_set_sha()}, "feature_version": F.FEATURE_VERSION,
            "family_version": {FAMILY: R.PHASE07_FAMILY_VERSION}, "registry_sha": C.registry_sha256(), "labels_version": L.LABELS_VERSION}


def load_registry(registry_dir: str | Path) -> dict:
    d = Path(registry_dir)
    try:
        entries = R.read_entries(d / "entries")
        text = (d / "REGISTRY_LOG.jsonl").read_text()
        events = R.read_log(text)
        if not entries or not events:
            raise IntegrationError("empty registry")
        return {"state": "OK", "entries": entries, "events": events, "log_sha256": R.sha_bytes(text.encode()),
                "entries_n": len(entries)}
    except Exception as e:  # noqa: BLE001  an unreadable or tampered registry is a visible state, never a crash (P47)
        return {"state": "REGISTRY_UNAVAILABLE", "detail": f"{type(e).__name__}: {str(e)[:160]}", "entries": {}, "events": []}


def calibration_status(root: Path) -> dict:
    out = {}
    for t, rel in CALIBRATION_CARD_FILES.items():
        try:
            c = CAL.loads((root / rel).read_text())
            out[t] = {"status": c["status"], "level": c["level"], "card_sha": c["card_sha"], "publishable": bool(c.get("publishable"))}
        except Exception as e:  # noqa: BLE001
            out[t] = {"status": "CALIBRATION_CARD_UNAVAILABLE", "detail": type(e).__name__}
    return out


def _load_card(entry: dict, root: Path) -> dict:
    p = root / entry["card_path"]
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != entry["card_file_sha256"]:
        raise IntegrationError("card file sha256 differs from the registry")
    card = B.loads(b.decode())                       # recomputes the card's model sha (MODEL_HASH_MISMATCH otherwise)
    if card["model_sha"] != entry["model_sha"]:
        raise IntegrationError("card model sha differs from the registry")
    return card


def _calibration_card(entry: dict, want_sha: str | None, root: Path, extra: dict | None) -> dict | None:
    if want_sha is None:
        return None
    if extra and want_sha in extra:
        c = extra[want_sha]
    else:
        rel = (entry.get("calibration") or {}).get("path")
        if not rel:
            return None
        c = CAL.loads((root / rel).read_text())
    if c.get("card_sha") != want_sha:
        raise IntegrationError("calibration card sha differs from the registry")
    return c


def probe_rows(card: dict, root: Path) -> list[tuple]:
    """Identical inference over the committed synthetic probe set (fixture champions only, rule 7)."""
    d = json.loads((root / SYNTHETIC_PROBE).read_text())
    ex = [B.Example(decision_key=r["decision_key"], chain=r["chain"], mint=r["mint"], decision_time=r["decision_time"],
                    label_matures_at=r["decision_time"] + 86400.0, y=-1,
                    x={k: (float("nan") if v is None else float(v)) for k, v in r["x"].items()}, avail=r["avail"],
                    status=r["status"]) for r in d["rows"]]
    p, why = B.predict(card, ex)
    return [(e.decision_key, float(v) if math.isfinite(v) else None, w or "") for e, v, w in zip(ex, p, why)]


# ---------------------------------------------------------------- as-of features in a capture store (rule 8)
def capture_features(row: dict, token_row: dict | None, chain: str, mint: str, T: float) -> dict:
    """features_as_of in capture mode over an in-memory store holding only this decision row and its token row as one capture
    version at T. Thesis and token groups are computed; history, universe and candle groups are missing with their reasons."""
    con = S.connect(":memory:")
    try:
        ex = {"commit": "capture-" + D.row_sha256(row)[:40], "commit_time": float(T), "theses": [row],
              "tokens": [token_row] if token_row else [], "path": "integration-1-capture", "body_bytes": 0}
        S.ingest_exports(con, [ex], now=float(T), ref="integration-1 capture", collector="integration-1 capture")
        snap = F.features_as_of(con, chain, mint, float(T), F.FEATURE_VERSION, mode="capture")
    finally:
        con.close()
    frow = {}
    for v in snap["values"]:
        frow[v["feature_name"]] = v["value"]
        frow[v["feature_name"] + "__available_at"] = v["feature_available_at"] if v["feature_available_at"] is not None else float(T)
    x, av = B.model_inputs(frow)
    return {"x": x, "avail": av, "summary": {"feature_version": snap["feature_version"], "feature_set_sha": snap["feature_set_sha"],
            "snapshot_sha256": snap["snapshot_sha256"], "source_status": snap["source_status"], "availability_mode": "capture",
            "scope": "CAPTURE_SINGLE_ROW", "max_input_available_at": snap["max_input_available_at"]}}


def _inputs_json(x: dict) -> dict:
    return {k: _num_or_none(v) for k, v in sorted(x.items())}


# ---------------------------------------------------------------- the material-change gate (rule 4)
def material_of(trig: dict, pool: str | None, cat: dict, served: dict) -> dict:
    return {"chain": trig["chain"], "mint": trig["mint"], "pool": pool, "status": trig["status"], "fatal": list(trig["fatal_flags"]),
            "score": int(trig["score"]) if _fin(trig["score"]) else None, "price": _num_or_none(trig["price"]),
            "liquidity": _num_or_none(trig["liquidity"]), "vol_24h": _num_or_none(trig["vol_24h"]),
            "catalyst": cat.get("fingerprint"), "served": served}


def _rel(a: float | None, b: float | None, lim: float, name: str) -> str | None:
    if (a is None) != (b is None):
        return f"{name} {'became known' if a is None else 'became unknown'}"
    if a is None or b is None:
        return None
    if a == 0:
        return None if b == 0 else f"{name} from 0"
    d = (b - a) / abs(a)
    return f"{name} {d:+.1%}" if abs(d) + 1e-12 >= lim else None         # inclusive at the frozen bound (float tolerance)


def material_changes(prev: dict, prev_capture: float, cur: dict, capture: float) -> list[str]:
    m = FROZEN["material"]
    out = []
    for k in ("pool", "status", "fatal", "catalyst", "served"):
        if prev.get(k) != cur.get(k):
            out.append(f"{k} changed")
    a, b = prev.get("score"), cur.get("score")
    if (a is None) != (b is None) or (a is not None and abs(b - a) >= m["score_abs"]):
        out.append(f"score {a} to {b}")
    for k, lim in (("price", m["price_rel"]), ("liquidity", m["liquidity_rel"]), ("vol_24h", m["volume_rel"])):
        c = _rel(prev.get(k), cur.get(k), lim, k)
        if c:
            out.append(c)
    if capture - prev_capture >= m["max_age_s"]:
        out.append(f"last attempt {int(capture - prev_capture)} s ago")
    return out


def _measured(prev: dict, cur: dict) -> list[str]:
    out = []
    for k in ("price", "liquidity", "vol_24h"):
        a, b = prev.get(k), cur.get(k)
        if a and b is not None:
            out.append(f"{k} {(b - a) / abs(a):+.1%}")
    return out


# ---------------------------------------------------------------- documents and their records (rules 11, 12)
def check_document(doc: dict, record: dict | None, *, config_path: str | Path | None = None, model_card: dict | None = None,
                   calibration_card: dict | None = None) -> list[str]:
    """No document without its abstention record (Phase 13 m4): the record is required, must be this forecast's, and its reasons
    must be the document's; then `abstention.validate_publication` with the record."""
    errs = pair_errors(doc, record)
    if record is None:
        return errs
    errs += AB.validate_publication(doc, model_card=model_card, calibration_card=calibration_card, record=record,
                                    backtest=C.backtest_status(), config_path=config_path)
    return errs


def verify_point(doc: dict, target_rec: dict, *, req: dict, card: dict | None, level: str, cal_card: dict | None,
                 config_path: str | Path | None = None) -> list[str]:
    """Phase 13 m3 (PI-D-068): a FORECAST's probability and interval are recomputed from the raw number kept in the request
    record and the calibration card; any difference refuses the document."""
    if doc.get("prediction_status") != "FORECAST":
        return [] if doc.get("probability") is None and doc.get("uncertainty_interval") is None else ["abstention with a number"]
    raw = target_rec.get("raw_number")
    if not _fin(raw) or cal_card is None or card is None:
        return ["FORECAST without the raw number, card and calibration card it came from"]
    if target_rec.get("calibration_card_sha") != cal_card.get("card_sha"):
        return ["calibration card differs from the one recorded with the raw number"]
    ev = AB.evaluate(req, card=card, level=level, cal_card=cal_card, raw=float(raw), config_path=config_path)
    if ev["conditions"] or ev["point"] is None or ev["interval"] is None:
        return ["the recomputation abstains: the document cannot be a FORECAST"]
    errs = []
    if not (_fin(doc.get("probability")) and abs(float(doc["probability"]) - float(ev["point"])) <= 1e-12):
        errs.append(f"probability {doc.get('probability')!r} is not the recomputed {ev['point']!r}")
    iv = doc.get("uncertainty_interval")
    if not (isinstance(iv, list) and len(iv) == 2 and all(abs(float(a) - float(b)) <= 1e-12 for a, b in zip(iv, ev["interval"]))):
        errs.append(f"interval {iv!r} is not the recomputed {list(ev['interval'])!r}")
    return errs


# ---------------------------------------------------------------- one pass (rules 2 to 16)
def trigger_of(r: dict, *, source: str, position: int) -> dict:
    b = r.get("bundle") if isinstance(r, dict) else None
    b = b if isinstance(b, dict) else {}
    sc = r.get("score") if isinstance(r.get("score"), dict) else {}
    st = r.get("status") if isinstance(r.get("status"), dict) else {}
    snap = r.get("snapshot") if isinstance(r.get("snapshot"), dict) else {}
    fatal = sc.get("fatal_flags")
    return {"source": source, "position": position, "chain": b.get("chain"), "mint": r.get("mint"),     # no default chain (PI-D-021)
            "observed_at": b.get("observed_at"), "symbol": (b.get("identity") or {}).get("symbol"),
            "score": sc.get("total"), "status": st.get("status"),
            "fatal_flags": sorted({str(f.get("flag")) for f in fatal if isinstance(f, dict)}) if isinstance(fatal, list) else [],
            "fatal_raw": fatal if isinstance(fatal, list) else None,
            "price": snap.get("price"), "liquidity": snap.get("liquidity"), "vol_24h": snap.get("vol_24h"),
            "report_path": r.get("report_path"), "result": r}


def _percentile(xs: Sequence[float], q: float) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    i = min(len(xs) - 1, max(0, int(math.ceil(q * len(xs))) - 1))
    return round(xs[i], 3)


def _reasons_counts(recs: Iterable[dict]) -> dict:
    out: dict[str, int] = {}
    for r in recs:
        for x in r.get("reasons") or []:
            out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


def run_pass(results: Sequence[dict], *, capture_time: float, source: str = "scout", lab_db: str | Path | None = None,
             state_dir: str | Path | None = None, config_path: str | Path | None = None, mode: str | None = None,
             registry_dir: str | Path | None = None, root: str | Path | None = None, reader: Callable | None = None,
             clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
             allow_fixture: bool = False, extra_cal_cards: dict | None = None, drift_alarms: Sequence[float] = (),
             report_refs: dict | None = None, depth_db: str | Path | None = None, backtest_db: str | Path | None = None,
             decision_rows: Sequence[dict] | None = None) -> dict | None:
    """Process one batch of triggers. None when the flag is off (nothing read but the config, nothing written). Never raises:
    a failure is a visible state in the returned summary and, where the state can be written, in the request records.

    `decision_rows` (export replay only): pre-read decision snapshots {"row", "token", "decision_time", "basis"} given in the
    same order as `results`, for decisions that are export rows rather than freshly persisted scout rows."""
    cfg = config(config_path)
    if not cfg["enabled"]:
        return None
    t_start = clock()
    root = Path(root) if root is not None else ROOT
    mode = mode if mode in MODES else cfg["mode"]
    sdir = Path(state_dir or cfg["state_dir"] or default_state_dir())
    depth_db = depth_db if depth_db is not None else cfg["depth_db"]
    backtest_db = backtest_db if backtest_db is not None else cfg["backtest_db"]
    summary: dict[str, Any] = {"integration_version": INTEGRATION_VERSION, "mode": mode, "source": source,
                               "capture_time_utc": _iso(capture_time), "state_dir": str(sdir), "errors": []}
    refusal = state_dir_refusal(sdir)
    if refusal:
        summary.update(state="STATE_DIR_REFUSED", detail=refusal, events=[])
        return summary
    try:
        state = load_state(sdir)
    except Exception as e:  # noqa: BLE001  a tampered state refuses the pass: nothing is written (rule 14)
        summary.update(state="STATE_TAMPERED", detail=f"{type(e).__name__}: {str(e)[:200]}", events=[])
        return summary
    reg = load_registry(Path(registry_dir) if registry_dir is not None else root / REGISTRY_DIR)
    cal_status = calibration_status(root)
    rt = runtime_facts()
    bt_installed = C.backtest_status()
    depth = DA.status(depth_db)
    summary.update(registry={"state": reg["state"], "detail": reg.get("detail"), "entries": reg.get("entries_n"),
                             "log_sha256": reg.get("log_sha256")},
                   calibration={SHORT[t]: v for t, v in cal_status.items()}, backtest_status=bt_installed,
                   depth={"state": depth["state"]}, state="OK")
    if reg["state"] == "OK":
        tg = {}
        for t in PRIMARY:
            try:
                res = R.resolve(reg["events"], reg["entries"], t, float(capture_time))
                tg[SHORT[t]] = {"mode": res["mode"], "reasons": list(res["reasons"])}
            except Exception as e:  # noqa: BLE001
                tg[SHORT[t]] = {"mode": "REGISTRY_UNAVAILABLE", "reasons": [type(e).__name__]}
        summary["registry"]["targets"] = tg
    lab = None
    if lab_db is not None and decision_rows is None:
        try:
            lab = connect_lab_ro(lab_db)
        except Exception as e:  # noqa: BLE001
            summary["errors"].append(f"lab database: {type(e).__name__}")
    guard = RT.CallGuard(max_per_min=FROZEN["calls_per_minute"], max_calls=FROZEN["calls_per_pass"],
                         breaker=FROZEN["breaker_failures"], max_cost=FROZEN["cost_cap_usd"],
                         cost_per_call=float(getattr(reader, "cost_per_call", 0.0) or 0.0), clock=clock, sleep=sleep)
    pass_id = sha([INTEGRATION_VERSION, source, _iso(capture_time), len(state["lines"]["passes"]),
                   [(t.get("mint") if isinstance(t, dict) else None) for t in results]])
    new_req, new_docs, new_recs, new_refs = [], [], [], []
    shown: list[dict] = []
    latencies: list[float] = []
    reads = {"calls": 0, "states": {}}
    # ---- identities and snapshots (linear: one read per trigger)
    trigs = []
    for i, r in enumerate(results):
        tr = trigger_of(r if isinstance(r, dict) else {}, source=source, position=i)
        tr["row"] = tr["token"] = None
        tr["sharing"] = tr["earlier"] = 0
        tr["decision_time"], tr["basis"] = float(capture_time), "CAPTURE_TIME"
        try:
            S.check_address(tr["chain"], tr["mint"])
            tr["identity_ok"] = True
        except Exception:  # noqa: BLE001
            tr["identity_ok"] = False
        if tr["identity_ok"]:
            if decision_rows is not None:
                dr = decision_rows[i]
                tr["row"], tr["token"] = dr["row"], dr.get("token")
                tr["decision_time"], tr["basis"] = float(dr["decision_time"]), dr["basis"]
                tr["earlier"] = int(dr.get("earlier") or 0)
                tr["sharing"] = int(dr.get("sharing") or 1)
            elif lab is not None and _fin(tr["observed_at"]):
                try:
                    tr["row"], tr["token"], tr["sharing"], tr["earlier"] = decision_row(lab, tr["mint"], float(tr["observed_at"]))
                except Exception as e:  # noqa: BLE001
                    tr["error"] = f"decision row: {type(e).__name__}"
        tr["snapshot_hash"] = D.row_sha256(tr["row"]) if tr["row"] else None
        trigs.append(tr)
    newest: dict[tuple[str, str], int] = {}
    for tr in trigs:
        if tr["identity_ok"] and tr["row"] is not None and not tr.get("error"):
            k = (tr["chain"], tr["mint"])
            j = newest.get(k)
            if j is None or (float(tr["row"]["created_at"]), tr["position"]) >= (float(trigs[j]["row"]["created_at"]), trigs[j]["position"]):
                newest[k] = tr["position"]
    attempted = 0
    seq0 = len(state["lines"]["requests"])
    for tr in trigs:
        t0 = clock()
        base = {"record_version": "integration-request-1", "pass_id": pass_id, "seq": seq0 + len(new_req), "source": source,
                "chain": tr["chain"], "mint": tr["mint"], "snapshot_hash": tr["snapshot_hash"],
                "decision_time_utc": _iso(tr["decision_time"]), "decision_time_basis": tr["basis"],
                "capture_time_utc": _iso(capture_time), "capture_time": float(capture_time),
                "integration_version": INTEGRATION_VERSION, "mode": mode,
                "report_refs": {"token_report": tr["report_path"], **(report_refs or {})}, "errors": []}
        rec = None
        try:
            rec = _process(tr, base, state=state, newest=newest, attempted=attempted, t_start=t_start, clock=clock, reg=reg,
                           rt=rt, root=root, lab=lab, reader=reader, guard=guard, reads=reads, mode=mode,
                           allow_fixture=allow_fixture, extra_cal_cards=extra_cal_cards, drift_alarms=drift_alarms,
                           config_path=config_path, depth_db=depth_db, depth=depth, backtest_db=backtest_db,
                           bt_installed=bt_installed, cal_status=cal_status, out_docs=new_docs, out_recs=new_recs,
                           out_refs=new_refs, shown=shown)
        except Exception as e:  # noqa: BLE001  a failure is a visible ERROR event, never a crash of the scout
            rec = dict(base, event="ERROR", errors=[f"{type(e).__name__}: {str(e)[:200]}"], targets=[])
        if rec["event"] in ATTEMPTED:
            attempted += 1
            state["last_attempt"][(tr["chain"], tr["mint"])] = rec
            state["attempts"].setdefault((tr["chain"], tr["mint"]), []).append(rec)
        rec["latency_ms"] = round((clock() - t0) * 1000.0, 3)
        latencies.append(rec["latency_ms"])
        new_req.append(_sealed(rec))
    if lab is not None:
        lab.close()
    events = [r["event"] for r in new_req]
    m = {"events": len(new_req), "attempted": sum(e in ATTEMPTED for e in events),
         "documents": len(new_docs), "records": len(new_recs),
         "completed_forecasts": sum(1 for d in new_docs if d["document"]["prediction_status"] == "FORECAST"),
         "abstained": sum(1 for d in new_docs if d["document"]["prediction_status"] == "ABSTAIN"),
         "unchanged_cache_hits": events.count("UNCHANGED"), "duplicates": events.count("DUPLICATE"),
         "superseded": events.count("SUPERSEDED_IN_PASS"),
         "deferred": events.count("DEFERRED_QUEUE_FULL") + events.count("DEFERRED_LATENCY_BUDGET"),
         "not_attempted": events.count("NO_DECISION_SNAPSHOT") + events.count("NOT_EXACT_IDENTITY"),
         "errors": events.count("ERROR"), "reader_calls": reads["calls"], "reader_states": dict(sorted(reads["states"].items())),
         "reference_records": len(new_refs), "latency_ms_p50": _percentile(latencies, 0.5),
         "latency_ms_max": max(latencies) if latencies else None,
         "models_in_use": sorted({d["document"]["model_id"] for d in new_docs}),
         "reason_counts": _reasons_counts(new_recs), "event_counts": dict(sorted({e: events.count(e) for e in set(events)}.items())),
         "pass_wall_ms": round((clock() - t_start) * 1000.0, 3)}
    summary["metrics"] = m
    try:
        pr = _append_pass(state, requests=new_req, documents=new_docs, records=new_recs, references=new_refs,
                          pass_info={"pass_id": pass_id, "source": source, "mode": mode, "capture_time_utc": _iso(capture_time),
                                     "integration_version": INTEGRATION_VERSION, "metrics": m})
        summary["pass_record_id"] = pr["record_id"]
        summary["persisted"] = True
    except Exception as e:  # noqa: BLE001
        summary["persisted"] = False
        summary["errors"].append(f"persist: {type(e).__name__}: {str(e)[:200]}")
    summary["pass_id"] = pass_id
    summary["events"] = shown
    return summary


def _not_attempted(base: dict, event: str, **kw) -> dict:
    return dict(base, event=event, targets=[], **kw)


def _process(tr: dict, base: dict, *, state: dict, newest: dict, attempted: int, t_start: float, clock: Callable, reg: dict,
             rt: dict, root: Path, lab: sqlite3.Connection | None, reader: Callable | None, guard: RT.CallGuard, reads: dict,
             mode: str, allow_fixture: bool, extra_cal_cards: dict | None, drift_alarms: Sequence[float],
             config_path: Any, depth_db: Any, depth: dict, backtest_db: Any, bt_installed: str, cal_status: dict,
             out_docs: list, out_recs: list, out_refs: list, shown: list) -> dict:
    view = {"symbol": tr["symbol"], "chain": tr["chain"], "mint": tr["mint"], "snapshot_hash": tr["snapshot_hash"],
            "report_path": tr["report_path"], "fatal_flags": tr["fatal_flags"]}
    if not tr["identity_ok"]:
        shown.append(dict(view, event="NOT_EXACT_IDENTITY"))
        return _not_attempted(base, "NOT_EXACT_IDENTITY", detail="the mint is not an exact address of its chain (P01)")
    if tr.get("error"):
        shown.append(dict(view, event="ERROR"))
        return _not_attempted(base, "ERROR", errors=[tr["error"]])
    if tr["row"] is None:
        shown.append(dict(view, event="NO_DECISION_SNAPSHOT"))
        return _not_attempted(base, "NO_DECISION_SNAPSHOT", detail="no persisted thesis row for this result (not a decision)")
    row = tr["row"]
    if row.get("mint") != tr["mint"] or row.get("status") != tr["status"] or row.get("score") != tr["score"]:
        shown.append(dict(view, event="ERROR"))
        return _not_attempted(base, "ERROR", errors=["the persisted row differs from the result (mint, status or score)"])
    T = float(tr["decision_time"])
    if T < float(row["created_at"]):
        shown.append(dict(view, event="ERROR"))
        return _not_attempted(base, "ERROR", errors=["capture time before the row's created_at"])
    key = (tr["chain"], tr["mint"])
    if newest.get(key) != tr["position"]:
        shown.append(dict(view, event="SUPERSEDED_IN_PASS"))
        return _not_attempted(base, "SUPERSEDED_IN_PASS", detail="a newer snapshot of the same chain and mint is in this pass")
    if clock() - t_start > FROZEN["pass_budget_s"]:
        shown.append(dict(view, event="DEFERRED_LATENCY_BUDGET"))
        return _not_attempted(base, "DEFERRED_LATENCY_BUDGET", detail=f"pass budget {FROZEN['pass_budget_s']} s used")
    tok = tr["token"] or {}
    pool = (tok.get("primary_pool") or tok.get("graduated_pool")) if tok.get("chain", tr["chain"]) == tr["chain"] else None
    cat = catalyst_state(lab, tr["chain"], tr["mint"], T)
    # ---- serve every primary target as of the decision (rule 7)
    served: dict[str, dict] = {}
    for t in PRIMARY:
        served[t] = _serve(t, T, reg=reg, rt=rt, root=root, allow_fixture=allow_fixture, drift_alarms=drift_alarms)
    sig = {SHORT[t]: {"model_sha": served[t]["model_sha"], "pin": served[t]["pin_event_id"],
                      "states": sorted({b["state"] for b in served[t]["blocking"]})} for t in PRIMARY}     # CP17-0: serve state too
    fids = {t: C.forecast_id(tr["chain"], tr["mint"], tr["snapshot_hash"], t, C.TARGETS[t]["version"], C.TARGETS[t]["horizon_s"],
                             served[t]["model_sha"]) for t in PRIMARY}
    material = material_of(tr, pool, cat, sig)
    have = [f in state["documents"] for f in fids.values()]
    if all(have):
        shown.append(dict(view, event="DUPLICATE", covered_by=list(fids.values())))
        return _not_attempted(base, "DUPLICATE", covered_by=list(fids.values()), material=material,
                              detail="this exact snapshot was already attempted with the same models (P35)")
    if any(have):
        shown.append(dict(view, event="ERROR"))
        return _not_attempted(base, "ERROR", errors=["some but not all forecast ids of this snapshot exist"])
    earlier = [a for a in state["attempts"].get(key) or [] if float(a["capture_time"]) <= float(base["capture_time"])]
    prev = max(earlier, key=lambda a: (float(a["capture_time"]), a["seq"])) if earlier else None   # as of this capture
    if prev is not None:
        ch = material_changes(prev["material"], float(prev["capture_time"]), material, float(base["capture_time"]))
        if not ch:
            cov = [t["forecast_id"] for t in prev.get("targets") or []]
            shown.append(dict(view, event="UNCHANGED", covered_by=cov, measured=_measured(prev["material"], material)))
            return _not_attempted(base, "UNCHANGED", covered_by=cov, material=material, changes=[],
                                  measured=_measured(prev["material"], material),
                                  detail="no material change since the last attempt (cache hit)")
        event, changes = "MATERIAL_CHANGE", ch
    else:
        event, changes = "DISCOVERY", ["first attempt for this chain and mint"]
    if attempted >= FROZEN["queue_max"]:
        shown.append(dict(view, event="DEFERRED_QUEUE_FULL"))
        return _not_attempted(base, "DEFERRED_QUEUE_FULL", material=material, changes=changes,
                              detail=f"queue cap {FROZEN['queue_max']} attempts a pass")
    # ---- staleness and eligibility (rules 6, 8)
    obs = tr["observed_at"] if _fin(tr["observed_at"]) else float(row["created_at"])
    stale = (base["decision_time_basis"] == "CAPTURE_TIME") and (T - float(obs) > FROZEN["stale_input_s"])
    staleness = {"observed_at_utc": _iso(float(obs)), "age_s": round(T - float(obs), 3), "state": INPUT_STALE if stale else "FRESH"}
    feats = None
    need_feats = mode == "research" or any(served[t]["use_champion"] for t in PRIMARY)
    if need_feats:
        st, val = RT.guarded("capture_features", capture_features, row, tr["token"], tr["chain"], tr["mint"], T)
        feats = val if st["state"] == RT.AVAILABLE else {"x": {}, "avail": {}, "summary": {"state": st["state"], "detail": st["detail"]}}
    elig, elig_detail = (INPUT_STALE, "inputs older than 7,200 s at the capture") if stale else (NOT_ASSESSED, "no champion served")
    if not stale and any(served[t]["use_champion"] for t in PRIMARY):
        elig, elig_detail = _eligibility(reader, guard, reads, pool, tr, T, clock)
    new_mint = tr["earlier"] == 0
    # ---- per target: document and record (rules 3, 7, 11, 12)
    targets = []
    for t in PRIMARY:
        s = served[t]
        card = cal = None
        raw = raw_why = None
        x, av = {}, {}
        if s["use_champion"]:
            try:
                card = _load_card(s["entry"], root)
                cal = _calibration_card(s["entry"], s["forecast_inputs"]["calibration_card_sha"], root, extra_cal_cards)
                x, av = (feats or {}).get("x") or {}, (feats or {}).get("avail") or {}
                if x:
                    ex = B.Example(decision_key=tr["snapshot_hash"], chain=tr["chain"], mint=tr["mint"], decision_time=T,
                                   label_matures_at=T + C.TARGETS[t]["horizon_s"], y=-1, x=x, avail=av, status=tr["status"])
                    p, why = B.predict(card, [ex])
                    raw = float(p[0]) if math.isfinite(p[0]) else None
                    raw_why = why[0]
            except Exception as e:  # noqa: BLE001  a champion that cannot be loaded or run is no champion (P47)
                s["blocking"].append({"state": "CHAMPION_NOT_LOADED", "detail": f"{type(e).__name__}"})
                card = cal = None
                raw = raw_why = None
                x, av = {}, {}
        req = {"chain": tr["chain"], "mint": tr["mint"], "target": t, "decision_time": T, "decision_time_basis": base["decision_time_basis"],
               "snapshot_hash": tr["snapshot_hash"], "flag_on": True, "pool_point_in_time": pool is not None,
               "route": "PIT_RECORDED" if pool else None, "eligibility": elig, "position_usd": None, "backtest_required": False,
               "x": x, "avail": av, "feature_set_sha": F.feature_set_sha(), "new_mint": new_mint, "token_history_rows": 0}
        level = s["forecast_inputs"]["level"] if card is not None else "ABSTAIN"
        doc, arec = AB.forecast_result(req, card=card, level=level, cal_card=cal, raw=raw, raw_why=raw_why, drift_alarms=drift_alarms,
                                       generated_at_utc=base["capture_time_utc"], backtest_status=bt_installed,
                                       is_fixture=bool(allow_fixture), config_path=config_path)
        if doc["forecast_id"] != fids[t]:
            raise IntegrationError("the document's forecast id is not the request's (P35)")
        trec = {"target": t, "target_version": C.TARGETS[t]["version"], "horizon_seconds": C.TARGETS[t]["horizon_s"],
                "forecast_id": doc["forecast_id"], "prediction_status": doc["prediction_status"], "reasons": list(arec["reasons"]),
                "abstention_record_id": arec["record_id"], "model_id": doc["model_id"], "model_sha": doc["model_sha"],
                "registry": {k: s[k] for k in ("mode", "pin_event_id", "pin_reasons", "state", "detail")} |
                            {"blocking": [b["state"] for b in s["blocking"]], "use_champion": s["use_champion"]},
                "calibration_status_phase13": cal_status.get(t, {}).get("status"),
                "raw_number": raw, "raw_why": raw_why, "calibration_card_sha": (cal or {}).get("card_sha"),
                "inputs": _inputs_json(x) if x else None}
        errs = check_document(doc, arec, config_path=config_path, model_card=card, calibration_card=cal)
        errs += verify_point(doc, trec, req=req, card=card, level=level, cal_card=cal, config_path=config_path)
        if errs:
            raise IntegrationError(f"{SHORT[t]}: document refused: {errs[:3]}")
        trec["calibrated_point"] = doc["probability"]
        trec["interval"] = doc["uncertainty_interval"]
        targets.append(trec)
        out_docs.append(_sealed({"record_version": "integration-document-1", "forecast_id": doc["forecast_id"],
                                 "abstention_record_id": arec["record_id"], "pass_id": base["pass_id"], "request_seq": base["seq"],
                                 "document": doc}))
        out_recs.append(arec)
        if mode == "research":
            out_refs.extend(_references(s, feats, tr, T, base, root, reg.get("entries") or {}))
    plan = [p for p in R.target_plan({"chain": tr["chain"]}, {t: _plan_input(served[t]) for t in PRIMARY}) if not p["attempted"]]
    # ---- decision support beside the documents (rule 10)
    quotes, depth_detail = [], depth["state"]
    if depth["state"] == "OK" and pool is not None:
        try:
            con = DA.connect_ro(depth_db)
            try:
                quotes = DA.observations(con, chain=tr["chain"], mint=tr["mint"])
            finally:
                con.close()
        except Exception as e:  # noqa: BLE001
            depth_detail = f"COLLECTOR_READ_FAILED: {type(e).__name__}"
    ds = O.decision_support({"forecast_ids": [x["forecast_id"] for x in targets], "statuses": [x["prediction_status"] for x in targets]},
                            tr["fatal_raw"], quotes, decision_time=T, pool_address=pool,
                            max_loss=FROZEN["decision_support"]["max_loss"], max_age_s=FROZEN["decision_support"]["max_age_s"])
    btc = BT.from_result(tr["result"], chain=tr["chain"], mint=tr["mint"], decision_time=T, installed_status=bt_installed)
    if btc["result"] in ("BACKTEST_NOT_AVAILABLE", "UNTESTED") and backtest_db:
        btc = BT.from_table(backtest_db, chain=tr["chain"], mint=tr["mint"], decision_time=T, installed_status=bt_installed)
    veto = ds["veto_overrides_forecast"] or btc["veto"]["veto"] is True
    support = {"structural_veto": ds["structural_veto"], "backtest_veto": btc["veto"], "veto": bool(veto),
               "veto_unknown": ds["structural_veto"]["veto"] is None, "size_cap": ds["size_cap"],
               "position_usd_from_forecast": None, "depth_state": depth_detail, "note": ds["note"]}
    rec = dict(base, event=event, changes=changes, material=material, targets=targets, not_attempted_targets=plan,
               staleness=staleness, eligibility={"state": elig, "detail": elig_detail}, features=(feats or {}).get("summary"),
               new_mint=new_mint, rows_sharing_key=tr["sharing"], catalyst=cat, decision_support=support, backtest=btc)
    shown.append(dict(view, event=event, changes=changes, targets=targets,
                      documents=[d["document"] for d in out_docs[-len(PRIMARY):]], records=out_recs[-len(PRIMARY):],
                      support=support, backtest=btc["result"], staleness=staleness["state"], eligibility=elig,
                      registry={SHORT[t]: served[t]["mode"] for t in PRIMARY}))
    return rec


def _plan_input(s: dict) -> dict:
    return {"use_champion": s["use_champion"], "blocking": s["blocking"], "forecast_inputs": s["forecast_inputs"],
            "references": s["references"]}


def _serve(t: str, T: float, *, reg: dict, rt: dict, root: Path, allow_fixture: bool, drift_alarms: Sequence[float]) -> dict:
    out = {"mode": "NO_VIABLE_CHAMPION", "pin_event_id": None, "pin_reasons": [], "use_champion": False, "blocking": [],
           "forecast_inputs": {"card_entry": None, "model_id": R.NOT_SELECTED, "level": "ABSTAIN", "calibration_card_sha": None},
           "references": {}, "model_sha": None, "entry": None, "state": reg["state"], "detail": reg.get("detail")}
    if reg["state"] != "OK":
        out["blocking"].append({"state": "REGISTRY_UNAVAILABLE", "detail": reg.get("detail")})
        return out
    try:
        res = R.resolve(reg["events"], reg["entries"], t, T)
        inference = None
        if res["mode"] == "CHAMPION":
            e = reg["entries"][res["champion"]]
            if e["is_fixture"] and allow_fixture and e["family"]["phase"] == FAMILY:
                inference = probe_rows(_load_card(e, root), root)
        sv = R.serve(reg["events"], reg["entries"], t, T, runtime=rt,
                     request={"feature_set_sha": F.feature_set_sha(), "feature_version": F.FEATURE_VERSION},
                     drift_alarms=drift_alarms, inference=inference, root=root, allow_fixture=allow_fixture)
    except Exception as e:  # noqa: BLE001  a log naming an unknown entry or a refused pin: visible, abstain (P47)
        out["state"] = "REGISTRY_UNAVAILABLE"
        out["detail"] = f"{type(e).__name__}: {str(e)[:160]}"
        out["blocking"].append({"state": "REGISTRY_UNAVAILABLE", "detail": out["detail"]})
        return out
    out.update(mode=sv["resolved"]["mode"], pin_event_id=sv["resolved"]["event_id"], pin_reasons=list(sv["resolved"]["reasons"]),
               use_champion=sv["use_champion"], blocking=list(sv["blocking"]), forecast_inputs=sv["forecast_inputs"],
               references=sv["references"])
    if sv["use_champion"]:
        e = reg["entries"][sv["forecast_inputs"]["card_entry"]]
        out["entry"], out["model_sha"] = e, e["model_sha"]
    return out


def _eligibility(reader: Callable | None, guard: RT.CallGuard, reads: dict, pool: str | None, tr: dict, T: float,
                 clock: Callable[[], float]) -> tuple[str, str]:
    """One reference-price read per decision for a served champion (rule 6), through the guard; registry eligibility rule."""
    if pool is None:
        return "VENDOR_OR_ROUTE_GAP", "no point-in-time pool"
    if reader is None:
        return NOT_ASSESSED, "no reader configured: no reference-price read"
    t0 = clock()
    st, candles = guard.call("reference_price", reader, pool, tr["mint"], T)
    took = clock() - t0
    reads["calls"] = guard.calls
    reads["states"][st["state"]] = reads["states"].get(st["state"], 0) + 1
    if st["state"] != RT.AVAILABLE:
        return "VENDOR_OR_ROUTE_GAP", f"reader {st['state']}: {st.get('detail') or ''}".strip()
    if took > FROZEN["reader_timeout_s"]:
        return "VENDOR_OR_ROUTE_GAP", f"reader took {took:.1f} s, over {FROZEN['reader_timeout_s']} s"
    el = C.eligibility(candles, T, read_ok=True, pool=pool, route="PIT_RECORDED", snapshot_vol_24h=tr["vol_24h"])
    return el, "one reference-price read"


def _references(s: dict, feats: dict | None, tr: dict, T: float, base: dict, root: Path, entries: dict) -> list[dict]:
    """Research mode: the pinned references scored into internal records (never documents; registry.reference_record)."""
    out = []
    if feats is None:
        return out
    for name, eid in sorted((s.get("references") or {}).items()):
        try:
            e = entries.get(eid)
            if e is None:
                continue
            card = _load_card(e, root)
            x, av = feats.get("x") or {}, feats.get("avail") or {}
            num, why = None, "NO_INPUTS"
            if x:
                ex = B.Example(decision_key=tr["snapshot_hash"], chain=tr["chain"], mint=tr["mint"], decision_time=T,
                               label_matures_at=T + 86400.0, y=-1, x=x, avail=av, status=tr["status"])
                p, w = B.predict(card, [ex])
                num, why = (float(p[0]), "") if math.isfinite(p[0]) else (None, w[0] or "OOD")
            rr = R.reference_record(e, decision_key=tr["snapshot_hash"], decision_time=T, number=num, why=why,
                                    as_of_utc=base["capture_time_utc"])
            out.append(_sealed({"record_version": "integration-reference-1", "pass_id": base["pass_id"], "request_seq": base["seq"],
                                "reference": name, "reference_record": rr}))
        except Exception:  # noqa: BLE001  a reference that cannot be scored is simply not recorded
            continue
    return out


# ---------------------------------------------------------------- catalyst pass (rule 9)
def catalyst_pass(*, lab_db: str | Path, state_dir: str | Path, now: float, config_path: str | Path | None = None) -> dict | None:
    """New exact-address catalyst links for mints that already have an attempted request: REFRESH_REQUESTED (the next scout
    pass reassesses; nothing here changes a document, verdict, score or status). None when the flag is off."""
    if not config(config_path)["enabled"]:
        return None
    try:
        state = load_state(state_dir)
    except Exception as e:  # noqa: BLE001
        return {"state": "STATE_TAMPERED", "detail": f"{type(e).__name__}: {str(e)[:200]}", "actions": []}
    try:
        con = connect_lab_ro(lab_db)
    except Exception as e:  # noqa: BLE001
        return {"state": "CATALYST_SOURCE_NOT_AVAILABLE", "detail": type(e).__name__, "actions": []}
    actions, new_req = [], []
    try:
        if not {"catalyst_token_links", "catalyst_events"} <= _tables(con):
            return {"state": "CATALYST_SOURCE_NOT_AVAILABLE", "detail": "catalyst tables absent", "actions": []}
        cur = con.execute(
            "SELECT l.chain, l.mint, l.link_type, l.link_strength, l.linked_at, e.event_key, e.discovered_at "
            "FROM catalyst_token_links l JOIN catalyst_events e ON e.id = l.event_id ORDER BY l.linked_at, l.id")
        names = [c[0] for c in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
    finally:
        con.close()
    rule = FROZEN["catalyst"]
    seen_keys = {(r["mint"], r.get("event_key")) for lst in state["refreshed"].values() for r in lst}
    last_refresh = {m: max(float(r["capture_time"]) for r in lst) for m, lst in state["refreshed"].items()}
    seq0 = len(state["lines"]["requests"])
    for r in rows:
        if not (_fin(r["linked_at"]) and r["linked_at"] <= now and _fin(r["discovered_at"]) and r["discovered_at"] <= now):
            continue
        a = {"chain": r["chain"], "mint": r["mint"], "event_key": r["event_key"]}
        if r["link_type"] not in rule["link_types"] or r["link_strength"] != rule["strength"]:
            actions.append(a | {"action": "IGNORED", "reason": "UNVERIFIED_CATALYST: ticker, name or weak link (PI-D-007)"})
            continue
        prev = state["last_attempt"].get((r["chain"], r["mint"]))
        if prev is None:
            actions.append(a | {"action": "IGNORED", "reason": "NO_DECISION_SNAPSHOT: the scout must analyse this mint first"})
            continue
        if r["linked_at"] <= float(prev["capture_time"]):
            actions.append(a | {"action": "IGNORED", "reason": "already visible at the last attempt"})
            continue
        if (r["mint"], r["event_key"]) in seen_keys:
            actions.append(a | {"action": "IGNORED", "reason": "duplicate: this event already requested a refresh (P15)"})
            continue
        lr = last_refresh.get(r["mint"])
        if lr is not None and now - lr < rule["refresh_min_interval_s"]:
            actions.append(a | {"action": "IGNORED", "reason": f"rate limited: a refresh was requested {int(now - lr)} s ago"})
            continue
        req = _sealed({"record_version": "integration-request-1", "pass_id": sha(["catalyst", _iso(now), seq0]),
                       "seq": seq0 + len(new_req), "source": "catalyst", "chain": r["chain"], "mint": r["mint"],
                       "snapshot_hash": prev.get("snapshot_hash"), "decision_time_utc": _iso(now),
                       "decision_time_basis": "CAPTURE_TIME", "capture_time_utc": _iso(now), "capture_time": float(now),
                       "integration_version": INTEGRATION_VERSION,
                       "event": "CATALYST_REFRESH_REQUESTED", "event_key": r["event_key"], "targets": [],
                       "detail": "re-run the scout for this mint; the catalyst is a claim, not an input", "errors": []})
        new_req.append(req)
        seen_keys.add((r["mint"], r["event_key"]))
        last_refresh[r["mint"]] = now
        actions.append(a | {"action": "REFRESH_REQUESTED"})
    persisted = False
    if new_req:
        _append_pass(state, requests=new_req, documents=[], records=[], references=[],
                     pass_info={"pass_id": new_req[0]["pass_id"], "source": "catalyst", "mode": "fast", "capture_time_utc": _iso(now),
                                "integration_version": INTEGRATION_VERSION, "metrics": {"refresh_requested": len(new_req)}})
        persisted = True
    return {"state": "OK", "actions": actions, "refresh_requested": len(new_req), "persisted": persisted}


# ---------------------------------------------------------------- the scout section and the analyze line (rules 1, 15)
TRADING = tuple(AB.TRADING_WORDS)


def _plain_ok(text: str) -> bool:
    import re
    low = text.lower()
    return not any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in TRADING)


def render(summary: dict) -> str:
    """Plain-language section; reasons and explanations from each document's own record (rule 11)."""
    L_ = ["## Predictive research section (flag on, research only)", "",
          "This section is separate from the opportunity score. It does not change the 100-point score, the fatal flags, the status, "
          "the watchlist or the lists above, and it is not advice.", ""]
    if summary.get("state") in ("STATE_TAMPERED", "STATE_DIR_REFUSED"):
        L_ += [f"- State refused: {summary.get('state')} ({summary.get('detail')}). Nothing was assessed or written; every "
               f"opportunity above has no forecast in this run.", ""]
        return "\n".join(L_)
    reg = summary.get("registry") or {}
    m = summary.get("metrics") or {}
    L_.append(f"- Integration: {INTEGRATION_VERSION}, mode {summary.get('mode')}, capture {summary.get('capture_time_utc')}, "
              f"pass {str(summary.get('pass_id'))[:12]}")
    L_.append(f"- Backtesting: {summary.get('backtest_status')}")
    L_.append(f"- Model registry: {reg.get('state')}" + (f" ({reg.get('detail')})" if reg.get("detail") else ""))
    for k, v in (reg.get("targets") or {}).items():
        L_.append(f"  - {k}: {v['mode']} ({', '.join(v['reasons'])}); calibration "
                  f"{((summary.get('calibration') or {}).get(k) or {}).get('status')}")
    L_.append(f"- Depth collector: {(summary.get('depth') or {}).get('state')}")
    L_.append(f"- Counts: {m.get('events')} events, {m.get('attempted')} attempted, {m.get('completed_forecasts')} published, "
              f"{m.get('abstained')} abstentions, {m.get('unchanged_cache_hits')} unchanged, {m.get('duplicates')} duplicates, "
              f"{m.get('superseded')} superseded, {m.get('deferred')} deferred, {m.get('not_attempted')} not attempted, "
              f"{m.get('errors')} errors; latency p50 {m.get('latency_ms_p50')} ms, max {m.get('latency_ms_max')} ms; "
              f"models in use: {', '.join(m.get('models_in_use') or []) or 'none'}")
    if summary.get("errors"):
        L_.append(f"- Errors: {'; '.join(summary['errors'])}")
    L_.append(f"- Records: {summary.get('state_dir')}")
    L_.append("")
    for ev in summary.get("events") or []:
        L_.append(f"### {ev.get('symbol')} `{ev.get('chain')}:{ev.get('mint')}`")
        L_.append(f"- Snapshot {str(ev.get('snapshot_hash'))[:16]}; event {ev.get('event')}"
                  + (f" ({'; '.join(ev.get('changes') or [])})" if ev.get("changes") else ""))
        if ev.get("covered_by"):
            L_.append(f"- Covered by the earlier assessment: {', '.join(c[:15] for c in ev['covered_by'])}"
                      + (f" (measured: {'; '.join(ev.get('measured') or [])})" if ev.get("measured") else ""))
        sup = ev.get("support")
        if sup:
            sv = sup["structural_veto"]
            if sv["veto"] is None:
                L_.append("- Fatal-flag check: unknown (no readable flag list), treated as not cleared")
            elif sv["veto"]:
                L_.append(f"- Fatal-flag veto: {', '.join(sv['flags'])}; no forecast clears it")
            else:
                L_.append("- Fatal-flag veto: none recorded by the lab")
            if sup["backtest_veto"]["veto"]:
                L_.append(f"- Backtest veto: {', '.join(sup['backtest_veto']['reasons'])}; no forecast clears it")
            L_.append(f"- Size: {sup['size_cap'].get('basis')}; no position size comes from a forecast")
            L_.append(f"- Inputs: {ev.get('staleness')}; reference price {ev.get('eligibility')}; backtest {ev.get('backtest')}")
        for doc, rec in zip(ev.get("documents") or [], ev.get("records") or []):
            words = TARGET_WORDS.get(doc["target"], doc["target"])
            if doc["prediction_status"] == "ABSTAIN":
                L_.append(f"- {words}: ABSTAIN ({', '.join(rec['reasons'])}); record {rec['record_id'][:12]}")
            else:
                L_.append(f"- {words}: FORECAST; record {rec['record_id'][:12]}")
            L_.append(f"  - {AB.describe(doc, rec)}")
        if ev.get("report_path"):
            L_.append(f"- Token report: {ev['report_path']}")
        L_.append("")
    out = "\n".join(L_)
    ident = out
    for ev in summary.get("events") or []:
        for s in (str(ev.get("symbol")), str(ev.get("mint")), str(ev.get("report_path"))):
            ident = ident.replace(s, "")
    if not _plain_ok(ident):
        raise IntegrationError("the section would carry a trading word")
    return out


def scout_section(results: Sequence[dict], *, stage2: dict | None = None, scout_time: float | None = None,
                  report_path: str | Path | None = None, capture_time: float | None = None, lab_db: str | Path | None = None,
                  config_path: str | Path | None = None, **kw: Any) -> str | None:
    """The `cmd_scout` hook: None when the flag is off; otherwise the section text (never raises)."""
    try:
        if not C.enabled(config_path):
            return None
        if lab_db is None:
            from .. import db
            lab_db = db.DB_PATH
        cap = float(capture_time) if capture_time is not None else time.time()
        summ = run_pass(results, capture_time=cap, source="scout", lab_db=lab_db, config_path=config_path,
                        report_refs={"scout_report": str(report_path) if report_path else None}, **kw)
        if summ is None:
            return None
        n2 = len((stage2 or {}).get("rejected_stage2") or [])
        text = render(summ)
        if n2:
            text += f"\n- Stage-2 structural rejects ({n2}) are not decisions (no thesis row) and get no forecast attempt.\n"
        return text
    except Exception as e:  # noqa: BLE001  the scout report still goes out, with the failure visible
        return (f"## Predictive research section (flag on, research only)\n\n- Failed: {type(e).__name__}: {str(e)[:200]}. "
                f"No forecast in this run; the report above is unchanged.\n")


def analyze_line(r: dict, *, capture_time: float | None = None, lab_db: str | Path | None = None,
                 config_path: str | Path | None = None, **kw: Any) -> str | None:
    """The `cmd_analyze` hook: None when the flag is off; otherwise one line (never raises)."""
    try:
        if not C.enabled(config_path):
            return None
        if lab_db is None:
            from .. import db
            lab_db = db.DB_PATH
        cap = float(capture_time) if capture_time is not None else time.time()
        s = run_pass([r], capture_time=cap, source="analyze", lab_db=lab_db, config_path=config_path, **kw)
        if s is None:
            return None
        if s.get("state") in ("STATE_TAMPERED", "STATE_DIR_REFUSED"):
            return f"predictive: {s.get('state')} ({s.get('detail')}); nothing assessed | research only"
        ev = (s.get("events") or [{}])[0]
        recs = ev.get("records") or []
        st = ", ".join(sorted({x["prediction_status"] for x in (ev.get("documents") or [])})) or ev.get("event")
        rs = sorted({x for rec in recs for x in rec["reasons"]})
        return (f"predictive: {ev.get('event')} {st}" + (f" ({', '.join(rs)})" if rs else "")
                + f" | snapshot {str(ev.get('snapshot_hash'))[:12]} | research only, not advice")
    except Exception as e:  # noqa: BLE001
        return f"predictive: failed ({type(e).__name__}); nothing assessed | research only"


# ---------------------------------------------------------------- ops metrics and checks over the state (rule 16)
def metrics(state_dir: str | Path) -> dict:
    st = load_state(state_dir)
    reqs, docs, recs = st["lines"]["requests"], st["lines"]["documents"], st["lines"]["records"]
    ev = [r["event"] for r in reqs]
    lat = [r["latency_ms"] for r in reqs if _fin(r.get("latency_ms"))]
    return {"passes": len(st["lines"]["passes"]), "events": len(reqs), "attempted": sum(e in ATTEMPTED for e in ev),
            "documents": len(docs), "records": len(recs),
            "completed_forecasts": sum(1 for d in docs if d["document"]["prediction_status"] == "FORECAST"),
            "abstained": sum(1 for d in docs if d["document"]["prediction_status"] == "ABSTAIN"),
            "unchanged_cache_hits": ev.count("UNCHANGED"), "duplicates": ev.count("DUPLICATE"), "superseded": ev.count("SUPERSEDED_IN_PASS"),
            "deferred": ev.count("DEFERRED_QUEUE_FULL") + ev.count("DEFERRED_LATENCY_BUDGET"), "errors": ev.count("ERROR"),
            "catalyst_refreshes": ev.count("CATALYST_REFRESH_REQUESTED"), "reference_records": len(st["lines"]["references"]),
            "latency_ms_p50": _percentile(lat, 0.5), "latency_ms_max": max(lat) if lat else None,
            "models_in_use": sorted({d["document"]["model_id"] for d in docs}), "reason_counts": _reasons_counts(recs),
            "event_counts": dict(sorted({e: ev.count(e) for e in set(ev)}.items()))}


def pair_errors(doc: dict, record: dict | None) -> list[str]:
    """The record-pairing part of `check_document` (Phase 13 m4), usable without the cards."""
    if record is None:
        return ["a document without its persisted abstention record is never shown (Phase 13 m4)"]
    errs = []
    if record.get("forecast_id") != doc.get("forecast_id"):
        errs.append("record of another forecast")
    if sorted(record.get("reasons") or []) != sorted(doc.get("abstain_reasons") or []):
        errs.append("the document's reasons differ from its record")
    if record.get("record_id") != sha({k: v for k, v in record.items() if k != "record_id"}):
        errs.append("record content does not match its record id")
    if f"{AB.ABSTENTION_VERSION}:{record.get('record_id')}" not in (doc.get("evidence_refs") or []):
        errs.append("the document does not reference its record")
    return errs


def check_state(state_dir: str | Path, *, config_path: str | Path | None = None) -> dict:
    """Every persisted document paired with its persisted record; abstentions also checked by `validate_publication`;
    forecast ids unique. (A FORECAST was checked against its cards and recomputed by `verify_point` before it was written.)"""
    st = load_state(state_dir)
    probs = []
    ids = [d["forecast_id"] for d in st["lines"]["documents"]]
    if len(ids) != len(set(ids)):
        probs.append("a forecast id appears twice")
    for d in st["lines"]["documents"]:
        doc = d["document"]
        rec = st["records"].get(d["abstention_record_id"])
        e = pair_errors(doc, rec)
        if doc["prediction_status"] != "FORECAST" and not e:
            e = AB.validate_publication(doc, model_card=None, calibration_card=None, record=rec, backtest=C.backtest_status(),
                                        config_path=config_path)
        probs += [f"{doc['forecast_id']}: {x}" for x in e]
    return {"documents": len(ids), "problems": probs}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m memelab.predictive.integration")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "check"):
        p = sp.add_parser(name)
        p.add_argument("--state-dir")
        p.add_argument("--config")
    p = sp.add_parser("catalyst-pass")
    p.add_argument("--state-dir")
    p.add_argument("--config")
    p.add_argument("--lab-db")
    p.add_argument("--now", type=float)
    a = ap.parse_args(argv)
    cfg = config(a.config)
    sdir = a.state_dir or cfg["state_dir"] or str(default_state_dir())
    try:
        if a.cmd == "status":
            print(json.dumps({"flag": cfg["enabled"], "state_dir": sdir, "metrics": metrics(sdir)}, indent=1, sort_keys=True))
            return 0
        if a.cmd == "check":
            out = check_state(sdir, config_path=a.config)
            print(json.dumps(out, indent=1, sort_keys=True))
            return 0 if not out["problems"] else 1
        from .. import db
        res = catalyst_pass(lab_db=a.lab_db or db.DB_PATH, state_dir=sdir, now=a.now if a.now is not None else time.time(),
                            config_path=a.config)
        print(json.dumps(res if res is not None else {"flag": False, "state": "FLAG_OFF"}, indent=1, sort_keys=True))
        return 0
    except StateTampered as e:
        print(json.dumps({"state": "STATE_TAMPERED", "detail": str(e)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())

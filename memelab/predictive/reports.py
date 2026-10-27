"""Phase 18: report-1 and alerts-rules-1, readable reports and research alerts over the persisted predictive state
(research only, flag OFF, imported by no module; CLI `python -m memelab.predictive.reports`).

Pre-registration: audits/predictive-intelligence/phase_18/ACCEPTANCE_CHECKLIST.md (rules 1 to 15) and PI-D-098. In short:
  - the state is read only through `integration.load_state` and `integration.check_state`; a document is used only with its
    abstention record and its owning request record; a FORECAST shows a number only when its record, the request's stored
    raw number and calibrated point, and its model and calibration cards (resolved through the registry) agree under
    `integration.check_document`; anything else is DOCUMENT_REFUSED and shows no number (rule 1);
  - an abstaining target shows its reasons, the record's explanations and what would unblock each reason, never a base rate,
    a reference-model number or a score-like number (rule 4);
  - every section uses the lab's FACT / INFERENCE / HEURISTIC / UNKNOWN buckets through `memelab.report._ev` (rule 6), every
    token-sourced string the Phase 17 sanitization (rule 7), every fixture document the FORMAT-ONLY watermark (rule 8);
  - alerts reuse the social-intel alert state, cooldown, daily cap, quiet hours, disclaimer, file sink and renderers, in dry
    run only; four frozen policies; a veto overrides a forecast; never an alert for an abstention alone (rules 9 to 11).
Nothing here feeds the 100-point score, the fatal flags, the status, the watchlist or the scout lists.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import contract as C
from . import integration as I
from ..report import _ev
from ..social import alerts_core as AC
from ..social import alerts_engine as AE
from ..social import alerts_transport as AT

PHASE = "18"
REPORT_VERSION = "report-1"
ALERT_RULES_VERSION = "alerts-rules-1"
WATERMARK = "FORMAT-ONLY FIXTURE: invented data, not a forecast"
EXTRA_WORDS = ("target price", "price target", "take profit", "stop loss", "stop-loss", "position size", "all in", "load up",
               "ape in", "accumulate", "profit")
MODEL_STALE_AFTER_UTC = "2026-10-31T00:00:00Z"
REGISTRY_INDEX = "REGISTRY_INDEX.json"
SIMULATION_STATE = "SIMULATION_NOT_AVAILABLE"
SIMULATION_WHY = ("MIROFISH_NO_GO (PI-D-081, PI-D-083): the behavioral module is off and research-optional; no paid language "
                  "model or Zep use is approved, so no simulation runs")
BACKTEST_UNBLOCK = ("the backtesting module merged into this line (pull request 4, Elving's decision) and verified by a phase; "
                    "until then no execution or stress assessment exists")
PRICE_PATH_LINE = "price path only: not proceeds at any size (PRICE_PATH_NOT_PROCEEDS)"
LAB_STATUSES = ("REJECTED", "RESEARCH REQUIRED", "WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET", "OVEREXTENDED",
                "DISTRIBUTION RISK", "THESIS DETERIORATING", "THESIS INVALIDATED")   # m24 STATUSES (pinned by a test)
SHORT_HEAD = {"T1_24h": "T1 24 h", "T1b_6h": "T1b 6 h", "T2_24h": "T2 24 h"}
_TOL = 1e-12

# What would unblock each contract reason (rule 4; one line per reason of contract.ABSTAIN_REASONS).
UNBLOCK = {
    "INSUFFICIENT_HISTORY": "at least 50 matured prospective outcomes with 10 per class for this target (Phase 19), never the fit set",
    "NOT_YET_MATURED": "the outcomes that check the calibration have to mature first (Phase 19 tracks them)",
    "UNCALIBRATED": "a CALIBRATED Phase 13 card for the selected model, from out-of-sample prospective evidence",
    "MODEL_STALE": "a model card retrained from a committed plan (frozen cards are stale after 2026-10-31T00:00:00Z)",
    "DRIFT_ALERT": "the drift alarm cleared by a recorded review and, if needed, a retrained and re-registered model",
    "OOD": "inputs inside the model's training and calibration range; a token outside it stays without a number",
    "FEATURE_SCHEMA_MISMATCH": "the model re-registered for the running feature set (change control)",
    "EXECUTION_DATA_MISSING": "forward depth and quote collection deployed (approved, PI-D-044, not deployed); sizes need it",
    "NO_RECENT_PRICE": "a trade in the hour before the decision on the recorded pool",
    "OUT_OF_SCOPE_CHAIN": "the targets are defined for Solana only; another chain needs a change control and its own evidence",
    "OUT_OF_SCOPE_OPPORTUNITY_TYPE": "a target defined for this kind of opportunity (change control)",
    "TARGET_NOT_FEASIBLE": "a point-in-time pool recorded at the capture on the registered price route",
    "UNVERIFIED_EVENT": "an exact verified address of the token on its chain",
    "RESTRICTED_SOURCE": "inputs from allowed sources only, available at the decision",
    "SOURCE_STALE": "a fresh capture (inputs younger than 7,200 s) and one reference-price read on the point-in-time pool",
    "MODEL_NOT_SELECTED": ("a champion pinned at SHADOW or VALIDATED_EXPERIMENTAL in the Phase 16 registry; that needs the "
                           "ACCEPTANCE promotion change control (PI-D-091, Elving's decision) and admissible prospective evidence"),
    "FLAG_OFF": "predictive.enabled set to true in data/config.json (Elving's decision)",
}
# Missing-data states shown outside the abstention reasons (rule 6, G10).
STATE_TEXT = {
    "FLAG_OFF": "the predictive flag is off: nothing was read or rendered",
    "NO_STATE": "no predictive state exists yet: the scout has not run with the flag on",
    "STATE_DIR_REFUSED": "the state directory is inside the repository and not under data/private/",
    "STATE_TAMPERED": "the state files do not match their record ids or the pass chain: nothing is shown",
    "STATE_CHECK_FAILED": "some documents are not paired with their records or requests: those documents are refused",
    "INPUT_STALE": "the inputs were older than 7,200 s at the capture",
    "SNAPSHOT_NOT_VERIFIED": "no lab database row matches the snapshot hash: lab facts (age, symbol, labels) are unknown here",
    "REGISTRY_UNAVAILABLE": "the model registry could not be read or verified: every target abstains",
    "REGISTRY_INDEX_MISMATCH": "the committed registry index does not match the pin the request recorded",
    "COLLECTOR_NOT_AVAILABLE": "no forward depth collector rows: no size can be supported (EXECUTION_DATA_MISSING)",
    "BACKTEST_NOT_AVAILABLE": "the backtesting module is not installed on this line",
    "CATALYST_SOURCE_NOT_AVAILABLE": "the catalyst tables were not available to the pass",
    SIMULATION_STATE: SIMULATION_WHY,
    "DOCUMENT_REFUSED": "the document failed a check: it is not shown and no number is shown",
}


class ReportError(ValueError):
    pass


class AlertRefused(ValueError):
    pass


# ---------------------------------------------------------------- small helpers
def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _iso(t: Any) -> str | None:
    return I._iso(float(t)) if _fin(t) else None


def _parse(s: Any) -> float | None:
    try:
        return C.parse_utc(s)
    except Exception:  # noqa: BLE001
        return None


def _vendor_time(s: Any) -> float | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except ValueError:
        return None


def _age(seconds: Any) -> str:
    if not _fin(seconds):
        return "unknown"
    s = float(seconds)
    if abs(s) >= 86400:
        return f"{s / 86400:.1f} days"
    if abs(s) >= 3600:
        return f"{s / 3600:.1f} hours"
    return f"{s / 60:.0f} minutes"


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _short(x: Any, n: int = 12) -> str:
    return str(x)[:n] if x else "none"


def _status_text(status: Any) -> tuple[str, str]:
    """The lab's status as shown here: verbatim when it is one of the lab's words and carries no trade wording, else kept in the
    lab's token report (rule 7)."""
    if isinstance(status, str) and status in LAB_STATUSES:
        if _plain(status):
            return status, "FACT"
        return "kept in the lab's token report (its label uses trade wording)", "UNKNOWN"
    return I._ident(status), "UNKNOWN"


def _code(x: Any) -> str:
    """A lab code (fatal-flag name, backtest veto reason, depth state, error label) as a code: upper-case letters, digits and
    underscore, at most 40 characters, never withheld (CP18-0, PI-D-099). Codes come from the lab's fixed vocabularies, not
    from token text; the whole-report trading-word check still runs on them."""
    c = re.sub(r"[^A-Z0-9_]", "", str(x if x is not None else "").upper())[:40]
    return c or "UNKNOWN_CODE"


def _plain(text: str) -> bool:
    low = text.lower()
    return I._plain_ok(text) and not any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in EXTRA_WORDS)


LOCAL_PATH = re.compile(r"(/tmp/|/home/|/Users/|/root/|/var/|/mnt/|[A-Za-z]:\\)")


def check_text(text: str, mints: Sequence[str] = ()) -> None:
    """Rule 7: the text, without the exact mints, carries no trading word and no local path; raises otherwise."""
    t = text
    for m in sorted({m for m in mints if m}, key=len, reverse=True):
        t = t.replace(m, "")
    if not _plain(t):
        raise ReportError("the text would carry a trading word")
    if LOCAL_PATH.search(t):
        raise ReportError("the text would carry a local path")


# ---------------------------------------------------------------- reading the state (rule 1)
def _problem_ids(problems: Sequence[str]) -> tuple[set[str], set[int]]:
    """The forecast ids and request seqs a state-check problem names. A problem that names neither (for example "a forecast id
    appears twice") refuses every document: the seq set then holds -1, which `_target_view` reads as all refused."""
    fids, seqs = set(), set()
    for p in problems:
        m = re.match(r"(fc_[0-9a-f]+):", p)
        n = re.match(r"request (\d+):", p)
        if m:
            fids.add(m.group(1))
        elif n:
            seqs.add(int(n.group(1)))
        else:
            seqs.add(-1)
    return fids, seqs


def _registry_facts(registry_dir: Path, reg: dict) -> dict:
    """The committed registry index and the pinned reference entries (rule 6 f). The index must carry the log sha the
    registry read verified; otherwise it is not used."""
    p = registry_dir / REGISTRY_INDEX
    if reg.get("state") != "OK" or not p.exists():
        return {"state": "REGISTRY_INDEX_NOT_AVAILABLE", "targets": {}}
    try:
        idx = json.loads(p.read_text())
    except (OSError, ValueError):
        return {"state": "REGISTRY_INDEX_NOT_AVAILABLE", "targets": {}}
    if idx.get("log_sha256") != reg.get("log_sha256"):
        return {"state": "REGISTRY_INDEX_MISMATCH", "targets": {}}
    out = {}
    for short, tg in (idx.get("targets") or {}).items():
        refs = []
        for name, eid in sorted((tg.get("references") or {}).items()):
            e = reg["entries"].get(eid)
            if e is None:
                continue
            retro = ((e.get("facts") or {}).get("retrospective")) or {}
            pro = ((e.get("facts") or {}).get("prospective")) or {}
            refs.append({"reference": name, "model_id": e.get("model_id"), "registry_status": e.get("registry_status"),
                         "retrospective_verdict": retro.get("verdict"), "retrospective_events": retro.get("n"),
                         "retrospective_days": retro.get("days"), "retrospective_evaluation": retro.get("evaluation"),
                         "prospective_status": pro.get("status")})
        out[short] = {"event_id": tg.get("event_id"), "mode": tg.get("mode"), "reasons": list(tg.get("reasons") or []),
                      "ensemble": tg.get("ensemble"), "references": refs}
    return {"state": "OK", "targets": out, "statement_present": bool(idx.get("statement"))}


def _lab_snapshot(lab: sqlite3.Connection | None, chain: str, mint: str, snapshot_hash: str | None) -> dict:
    """Rule 2: only the thesis row whose snapshot sha equals the request's; never a row of another snapshot."""
    if lab is None:
        return {"state": "SNAPSHOT_NOT_VERIFIED", "detail": "no lab database given"}
    try:
        rows = [dict(r) for r in lab.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC", (mint,))]
        match = [r for r in rows if snapshot_hash and I.snapshot_sha(r) == snapshot_hash]
        if not match:
            return {"state": "SNAPSHOT_NOT_VERIFIED", "detail": f"{len(rows)} lab rows of the mint, none with this snapshot hash"}
        tok = lab.execute("SELECT * FROM tokens WHERE mint=?", (mint,)).fetchone()
        tok = dict(tok) if tok else None
        if tok is not None and tok.get("chain", chain) != chain:
            tok = None
        return {"state": "SNAPSHOT_VERIFIED", "row": match[0], "token": tok}
    except Exception as e:  # noqa: BLE001
        return {"state": "SNAPSHOT_NOT_VERIFIED", "detail": f"lab database read failed ({type(e).__name__})"}


def _resolve_cards(doc: dict, trec: dict, reg: dict, root: Path, extra: dict | None) -> tuple[dict | None, dict | None, str | None]:
    if reg.get("state") != "OK":
        return None, None, "registry unavailable"
    cands = [e for e in reg["entries"].values() if e.get("model_sha") == doc.get("model_sha") and e.get("target") == doc.get("target")]
    if len(cands) != 1:
        return None, None, f"{len(cands)} registry entries carry this model sha"
    try:
        card = I._load_card(cands[0], root)
        cal = I._calibration_card(cands[0], trec.get("calibration_card_sha"), root, extra)
    except Exception as e:  # noqa: BLE001
        return None, None, f"cards not loadable ({type(e).__name__})"
    if cal is None:
        return None, None, "no calibration card"
    return card, cal, None


def _same(a: Any, b: Any) -> bool:
    return _fin(a) and _fin(b) and abs(float(a) - float(b)) <= _TOL


def _target_view(req: dict, trec: dict, dline: dict | None, rec: dict | None, *, refused_ids: set[str], req_refused: bool,
                 reg: dict, root: Path, extra: dict | None, config_path: Any) -> dict:
    """One target of one attempted request, checked under rule 1."""
    t = trec.get("target")
    short = I.SHORT.get(t, str(t))
    tv: dict[str, Any] = {"target": t, "short": short, "forecast_id": trec.get("forecast_id"), "horizon_seconds": trec.get("horizon_seconds"),
                          "target_version": trec.get("target_version"), "registry": trec.get("registry") or {},
                          "calibration_status_phase13": trec.get("calibration_status_phase13"), "checks": []}
    fail = tv["checks"]
    doc = (dline or {}).get("document")
    if dline is None or doc is None:
        fail.append("document missing")
    else:
        fail += I.pair_errors(doc, rec)
        if (dline.get("pass_id"), dline.get("request_seq")) != (req.get("pass_id"), req.get("seq")):
            fail.append("document not owned by this request")
        if doc.get("forecast_id") != trec.get("forecast_id") or doc.get("target") != t:
            fail.append("document of another target")
        if doc.get("chain") != req.get("chain") or doc.get("mint_address") != req.get("mint") or \
                doc.get("snapshot_hash") != req.get("snapshot_hash"):
            fail.append("document of another token or snapshot")
        if doc.get("prediction_status") != trec.get("prediction_status"):
            fail.append("status differs from the request record")
    if trec.get("forecast_id") in refused_ids:
        fail.append("named by a state check problem")
    if req_refused:
        fail.append("its request failed the state check")
    if fail:
        tv.update(status="DOCUMENT_REFUSED", number=None)
        return tv
    st = doc["prediction_status"]
    tv.update(document=doc, record=rec, status=st, reasons=list(rec.get("reasons") or []),
              explanations=[c.get("explanation") for c in rec.get("conditions") or [] if c.get("explanation")],
              caveats=list(doc.get("caveats") or []), model_id=doc.get("model_id"), model_sha=doc.get("model_sha"),
              feature_set_sha=doc.get("feature_set_sha"), data_snapshot_sha=doc.get("data_snapshot_sha"),
              training_cutoff_utc=doc.get("training_cutoff_utc"), record_id=rec.get("record_id"),
              scenarios=list(doc.get("behavioral_scenarios") or []), is_fixture=bool(doc.get("is_fixture")),
              backtest_status=doc.get("backtest_status"))
    if st == "ABSTAIN":
        if doc.get("probability") is not None or doc.get("uncertainty_interval") is not None:
            fail.append("abstention with a number")
        fail += I.check_document(doc, rec, config_path=config_path)
        if fail:
            tv.update(status="DOCUMENT_REFUSED", number=None)
            return tv
        tv["number"] = None
        return tv
    # FORECAST: every check of rule 1 before a number is shown
    if rec.get("conditions"):
        fail.append("record lists abstention conditions")
    if not _fin(trec.get("raw_number")):
        fail.append("no raw number in the request record")
    sha = trec.get("calibration_card_sha")
    if not sha or not any(str(r).endswith(":" + sha) for r in doc.get("evidence_refs") or []):
        fail.append("the document does not cite the calibration card of the request record")
    p, iv = doc.get("probability"), doc.get("uncertainty_interval")
    if not (_fin(p) and 0.0 <= float(p) <= 1.0):
        fail.append("probability is not a finite number in [0, 1]")
    if not _same(trec.get("calibrated_point"), p):
        fail.append("probability differs from the point stored with the raw number")
    siv = trec.get("interval")
    if not (isinstance(iv, list) and isinstance(siv, list) and len(iv) == len(siv) == 2 and all(_same(a, b) for a, b in zip(iv, siv))):
        fail.append("interval differs from the one stored with the raw number")
    if not fail:
        card, cal, why = _resolve_cards(doc, trec, reg, root, extra)
        if why:
            fail.append(f"cards: {why}")
        else:
            fail += I.check_document(doc, rec, config_path=config_path, model_card=card, calibration_card=cal)
    if fail:
        tv.update(status="DOCUMENT_REFUSED", number=None)
        return tv
    ref = doc.get("calibration_reference") or {}
    tv["number"] = {"probability": float(p), "interval": [float(iv[0]), float(iv[1])], "base_rate": doc.get("base_rate"),
                    "level": ref.get("level"), "method": ref.get("method"), "support_n": ref.get("support_n"),
                    "support_k": ref.get("support_k"), "holdout_n": ref.get("holdout_n"), "calibration_card_sha": ref.get("calibration_card_sha"),
                    "cohort": doc.get("cohort")}
    return tv


def _request_view(st: dict, req: dict, *, prev: dict | None, refused_ids: set[str], refused_seqs: set[int], reg: dict, regfacts: dict,
                  lab: sqlite3.Connection | None, root: Path, extra: dict | None, config_path: Any) -> dict:
    by_fid = st["documents"]
    targets = []
    for trec in req.get("targets") or []:
        dline = by_fid.get(trec.get("forecast_id"))
        rec = st["records"].get((dline or {}).get("abstention_record_id"))
        targets.append(_target_view(req, trec, dline, rec, refused_ids=refused_ids, req_refused=req.get("seq") in refused_seqs or -1 in refused_seqs,
                                    reg=reg, root=root, extra=extra, config_path=config_path))
    lab_snap = _lab_snapshot(lab, req.get("chain"), req.get("mint"), req.get("snapshot_hash"))
    return {"request": req, "previous": prev, "targets": targets, "lab": lab_snap, "registry_facts": regfacts}


def _attempts(st: dict) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    for r in st["lines"]["requests"]:
        if r.get("event") in I.ATTEMPTED:
            out.setdefault((r["chain"], r["mint"]), []).append(r)
    for v in out.values():
        v.sort(key=lambda a: (float(a["capture_time"]), int(a["seq"])))
    return out


def _system(reg: dict, cal: dict, st: dict, chk: dict) -> dict:
    last = st["lines"]["requests"][-1] if st["lines"]["requests"] else {}
    served = {}
    for r in reversed(st["lines"]["requests"]):
        if r.get("event") in I.ATTEMPTED:
            for t in r.get("targets") or []:
                served.setdefault(I.SHORT.get(t["target"], t["target"]), t.get("registry") or {})
            break
    return {"integration_version": last.get("integration_version"), "registry_state": reg.get("state"),
            "registry_detail": reg.get("detail"), "registry_log_sha256": reg.get("log_sha256"), "served": served,
            "calibration": {I.SHORT[t]: v for t, v in cal.items()}, "backtest_status": C.backtest_status(),
            "simulation": {"state": SIMULATION_STATE, "why": SIMULATION_WHY}, "state_check_problems": len(chk.get("problems") or []),
            "model_stale_after_utc": MODEL_STALE_AFTER_UTC, "passes": len(st["lines"]["passes"]),
            "last_pass_id": (st["last_pass"] or {}).get("pass_id"), "last_pass_record_id": (st["last_pass"] or {}).get("record_id")}


def build(state_dir: str | Path | None = None, *, config_path: str | Path | None = None, lab_db: str | Path | None = None,
          registry_dir: str | Path | None = None, root: str | Path | None = None, extra_cal_cards: dict | None = None,
          mint: str | None = None) -> dict:
    """The JSON-safe view of a report (the API). Never raises for a state problem: it is a visible state."""
    cfg = I.config(config_path)
    view: dict[str, Any] = {"report_version": REPORT_VERSION, "phase": PHASE, "flag": cfg["enabled"], "opportunities": [],
                            "not_attempted": [], "format_only": False}
    if not cfg["enabled"]:
        view["state"] = "FLAG_OFF"
        return view
    root = Path(root) if root is not None else I.ROOT
    sdir = Path(state_dir or cfg["state_dir"] or I.default_state_dir())
    refusal = I.state_dir_refusal(sdir)
    if refusal:
        view["state"] = "STATE_DIR_REFUSED"
        return view
    if not (sdir / I.FILES["passes"]).exists():
        view["state"] = "NO_STATE"
        return view
    try:
        st = I.load_state(sdir)
        chk = I.check_state(sdir, config_path=config_path)
    except Exception as e:  # noqa: BLE001
        view.update(state="STATE_TAMPERED", detail=I._ident(type(e).__name__, 40))
        return view
    refused_ids, refused_seqs = _problem_ids(chk.get("problems") or [])
    rdir = Path(registry_dir) if registry_dir is not None else root / I.REGISTRY_DIR
    reg = I.load_registry(rdir)
    regfacts = _registry_facts(rdir, reg)
    cal = I.calibration_status(root)
    lab = None
    if lab_db is not None:
        try:
            lab = I.connect_lab_ro(lab_db)
        except Exception:  # noqa: BLE001
            lab = None
    try:
        view["state"] = "STATE_CHECK_FAILED" if chk.get("problems") else "OK"
        view["state_check_problems"] = [I._ident(p.split(":")[0], 40) for p in chk.get("problems") or []]
        view["system"] = _system(reg, cal, st, chk)
        view["lab_database"] = "GIVEN" if lab is not None else ("UNREADABLE" if lab_db is not None else "NOT_GIVEN")
        view["targets_registry"] = _target_definitions()
        att = _attempts(st)
        for key in sorted(att, key=lambda k: (-float(att[k][-1]["capture_time"]), k)):
            if mint is not None and key[1] != mint:
                continue
            lst = att[key]
            rv = _request_view(st, lst[-1], prev=lst[-2] if len(lst) > 1 else None, refused_ids=refused_ids, refused_seqs=refused_seqs,
                               reg=reg, regfacts=regfacts, lab=lab, root=root, extra=extra_cal_cards, config_path=config_path)
            view["opportunities"].append(_opportunity(rv))
        covered = {(o["chain"], o["mint"]) for o in view["opportunities"]}
        for r in st["lines"]["requests"]:
            if r.get("event") in I.ATTEMPTED or (mint is not None and r.get("mint") != mint):
                continue
            view["not_attempted"].append({"event": r.get("event"), "chain": I._ident(r.get("chain")), "mint": I._mint_text(r.get("chain"), r.get("mint")),
                                          "capture_time_utc": r.get("capture_time_utc"), "request_record_id": r.get("record_id"),
                                          "covered_by_report": (r.get("chain"), r.get("mint")) in covered,
                                          "errors": [_code(str(e).split(":")[0]) for e in r.get("errors") or []]})
    finally:
        if lab is not None:
            lab.close()
    docs = [t for o in view["opportunities"] for t in o["targets"]]
    view["format_only"] = any(t.get("is_fixture") for t in docs)
    view["counts"] = {"opportunities": len(view["opportunities"]), "targets": len(docs),
                      "probabilities_shown": sum(1 for t in docs if t.get("number")),
                      "abstained": sum(1 for t in docs if t["status"] == "ABSTAIN"),
                      "refused": sum(1 for t in docs if t["status"] == "DOCUMENT_REFUSED"),
                      "not_attempted_events": len(view["not_attempted"]),
                      "vetoes": sum(1 for o in view["opportunities"] if o["execution"]["veto"]),
                      "snapshots_verified": sum(1 for o in view["opportunities"] if o["snapshot"]["lab_state"] == "SNAPSHOT_VERIFIED")}
    return view


def _target_definitions() -> list[dict]:
    out = []
    for t, v in C.TARGETS.items():
        d = {"target": t, "short": I.SHORT.get(t), "status": v.get("status"), "version": v.get("version"), "horizon_seconds": v.get("horizon_s")}
        if v.get("status") == "PRIMARY":
            d.update(upper=v.get("upper"), lower=v.get("lower"), positive=list(v.get("positive") or []), negative=list(v.get("negative") or []),
                     tie_rule=v.get("tie_rule"), price_source=v.get("price_source"), caveats=list(v.get("caveats") or []),
                     scope_chain=v.get("scope_chain"), words=I.TARGET_WORDS.get(t))
            if "drawdown" in t:
                d["event_words"] = "the price falls to half or trading halts"
        else:
            why = v.get("why") or ""
            d["why"] = why if _plain(why) else "kept in contract.py (its wording names trade steps)"
        out.append(d)
    return out


def _opportunity(rv: dict) -> dict:
    req, lab = rv["request"], rv["lab"]
    row, tok = lab.get("row") or {}, lab.get("token") or {}
    mat = req.get("material") or {}
    stale = req.get("staleness") or {}
    ds = req.get("decision_support") or {}
    bt = req.get("backtest") or {}
    sv = ds.get("structural_veto") or {}
    obs = _parse(stale.get("observed_at_utc"))
    first_pool = _vendor_time(tok.get("first_pool_at")) if lab["state"] == "SNAPSHOT_VERIFIED" else None
    age = (obs - first_pool) if (obs is not None and first_pool is not None) else None
    status, status_bucket = _status_text(mat.get("status"))
    o = {"chain": req.get("chain"), "mint": req.get("mint"), "chain_text": I._ident(req.get("chain")),
         "mint_text": I._mint_text(req.get("chain"), req.get("mint")),
         "symbol": I._ident(tok.get("symbol")) if lab["state"] == "SNAPSHOT_VERIFIED" and tok.get("symbol") else None,
         "event": req.get("event"), "changes": [I._ident(c, 60) if not re.fullmatch(r"[A-Za-z0-9_ .:%+-]+", str(c)) else str(c)
                                                 for c in req.get("changes") or []],
         "snapshot": {"snapshot_hash": req.get("snapshot_hash"), "row_sha256": req.get("row_sha256"),
                      "decision_time_utc": req.get("decision_time_utc"), "decision_time_basis": req.get("decision_time_basis"),
                      "capture_time_utc": req.get("capture_time_utc"), "observed_at_utc": stale.get("observed_at_utc"),
                      "age_at_capture_s": stale.get("age_s"), "input_state": stale.get("state"), "lab_state": lab["state"],
                      "lab_detail": lab.get("detail"), "token_age_s": age, "first_pool_at": _iso(first_pool) if first_pool else None},
         "structural": {"score": mat.get("score"), "fatal_flags": [_code(f) for f in mat.get("fatal") or []], "status": status,
                        "status_bucket": status_bucket, "veto_state": sv.get("state")},
         "technical": ({"lifecycle": I._ident(row.get("lifecycle")), "structure": I._ident(row.get("structure"))}
                       if lab["state"] == "SNAPSHOT_VERIFIED" else None),
         "catalyst": dict(req.get("catalyst") or {}),
         "targets": [], "not_attempted_targets": [{"target": p.get("target"), "status": p.get("status"), "reasons": p.get("reasons")}
                                                  for p in req.get("not_attempted_targets") or []],
         "execution": {"structural_veto": bool(sv.get("veto")), "veto_unknown": bool(ds.get("veto_unknown")),
                       "fatal_flags": [_code(f) for f in sv.get("flags") or []],
                       "backtest_veto": (ds.get("backtest_veto") or {}).get("veto"),
                       "backtest_veto_reasons": [_code(x) for x in (ds.get("backtest_veto") or {}).get("reasons") or []],
                       "veto": bool(ds.get("veto")) or bool(ds.get("veto_unknown")),
                       "size_basis": (ds.get("size_cap") or {}).get("basis"), "size_cap_usd": (ds.get("size_cap") or {}).get("size_cap_usd"),
                       "depth_state": _code(ds.get("depth_state")), "position_usd_from_forecast": ds.get("position_usd_from_forecast"),
                       "backtest_result": bt.get("result"), "backtest_installed": bt.get("installed_status")},
         "eligibility": (req.get("eligibility") or {}).get("state"),
         "ids": {"request_record_id": req.get("record_id"), "pass_id": req.get("pass_id"), "request_seq": req.get("seq"),
                 "token_report": I._ident(Path(str((req.get("report_refs") or {}).get("token_report") or "")).name, 80)
                 if (req.get("report_refs") or {}).get("token_report") else None},
         "registry_facts": rv["registry_facts"], "previous_request_record_id": (rv["previous"] or {}).get("record_id")}
    for tv in rv["targets"]:
        x = {k: v for k, v in tv.items() if k not in ("document", "record")}
        x["registry"] = {"mode": tv["registry"].get("mode"), "pin_event_id": tv["registry"].get("pin_event_id"),
                         "pin_reasons": list(tv["registry"].get("pin_reasons") or []), "blocking": list(tv["registry"].get("blocking") or []),
                         "state": tv["registry"].get("state")}
        x["scenarios"] = [I._ident((s or {}).get("label") or (s or {}).get("code") or "scenario", 40) for s in tv.get("scenarios") or []]
        o["targets"].append(x)
    o["previous_targets"] = {}
    return o


# ---------------------------------------------------------------- rendering (rules 5 to 8, 13)
def _row_status(t: dict, veto: bool) -> str:
    if t["status"] == "DOCUMENT_REFUSED":
        return "REFUSED (no number)"
    if t["status"] == "ABSTAIN":
        return "ABSTAIN (no number)"
    n = t["number"]
    s = f"FORECAST {_pct(n['probability'])} ({_pct(n['interval'][0])} to {_pct(n['interval'][1])})"
    if t.get("is_fixture"):
        s += " FORMAT-ONLY FIXTURE"
    return s + (" overridden by veto" if veto else "")


def render(view: dict) -> str:
    """Markdown for a view built by `build`. Raises when the text would carry a trading word or a local path, or when a fixture
    document is present and the view lost its watermark."""
    fixture = any(t.get("is_fixture") for o in view.get("opportunities") or [] for t in o["targets"])
    if fixture and not view.get("format_only"):
        raise ReportError("a fixture document in a view without the FORMAT-ONLY watermark")
    L: list[str] = []
    if view.get("format_only"):
        L += [WATERMARK, ""]
    L += ["# Predictive research report (research only, not advice)", ""]
    L.append("Separate from the opportunity score: nothing here changes the 100-point score, the fatal flags, the status, the "
             "watchlist or the scout lists, and it never sets a size.")
    L.append("")
    stt = view.get("state")
    if stt not in ("OK", "STATE_CHECK_FAILED"):
        L += [f"State: {stt}. {STATE_TEXT.get(stt, '')}".rstrip(), "", "No opportunity is shown and no number is shown.", ""]
        text = "\n".join(L)
        check_text(text)
        return text
    c = view["counts"]
    sysv = view["system"]
    L += ["## At a glance", ""]
    L.append(f"- Probabilities shown: {c['probabilities_shown']} of {c['targets']} target forecasts; abstentions {c['abstained']}; "
             f"refused documents {c['refused']}.")
    if c["probabilities_shown"] == 0:
        L.append("- No probability is shown: every target abstains or was refused. The reasons are named per target below.")
    rc: dict[str, int] = {}
    for o in view["opportunities"]:
        for t in o["targets"]:
            for r in t.get("reasons") or ([] if t["status"] != "DOCUMENT_REFUSED" else ["DOCUMENT_REFUSED"]):
                rc[r] = rc.get(r, 0) + 1
    if rc:
        order = list(C.ABSTAIN_REASONS) + ["DOCUMENT_REFUSED"]
        L.append("- Reasons named across the targets: " + ", ".join(f"{r} {rc[r]}" for r in order if r in rc) + ".")
    for short, sv in (sysv.get("served") or {}).items():
        calst = ((sysv.get("calibration") or {}).get(short) or {}).get("status")
        blk = [str(x) for x in sv.get("blocking") or []]
        L.append(f"- {SHORT_HEAD.get(short, short)}: registry {sv.get('mode')}" + (f" (blocking: {', '.join(blk)})" if blk else "")
                 + f", committed Phase 13 calibration {calst}.")
    L.append(f"- Backtesting: {sysv['backtest_status']}. Behavioral simulation: {SIMULATION_STATE}.")
    L.append(f"- Opportunities: {c['opportunities']}; with a veto: {c['vetoes']}; snapshots verified against the lab database: "
             f"{c['snapshots_verified']} of {c['opportunities']}; events not attempted: {c['not_attempted_events']}.")
    if stt == "STATE_CHECK_FAILED":
        L.append(f"- State check: {len(view.get('state_check_problems') or [])} problems; the documents they name are refused.")
    L.append("")
    if view["opportunities"]:
        L.append("| Opportunity | Exact chain:mint | Inputs observed (UTC) | T1 24 h | T1b 6 h | T2 24 h | Vetoes | Inputs |")
        L.append("|---|---|---|---|---|---|---|---|")
        for o in view["opportunities"]:
            by = {t["short"]: t for t in o["targets"]}
            cells = [_row_status(by[s], o["execution"]["veto"]) if s in by else "not attempted" for s in ("T1_24h", "T1b_6h", "T2_24h")]
            vet = ", ".join(o["execution"]["fatal_flags"] + (["backtest veto"] if o["execution"]["backtest_veto"] else [])
                            + (["unknown"] if o["execution"]["veto_unknown"] else [])) or "none"
            L.append(f"| {o['symbol'] or 'symbol not verified'} | `{o['chain_text']}:{o['mint_text']}` | {o['snapshot']['observed_at_utc']} | "
                     + " | ".join(cells) + f" | {vet} | {o['snapshot']['input_state']} |")
        L.append("")
    L += _system_lines(view)
    L += _definition_lines(view)
    L += _carried_lines()
    for o in view["opportunities"]:
        L += _opportunity_lines(o)
    L += _not_attempted_lines(view)
    L += _units_lines()
    if view.get("format_only"):
        L += [WATERMARK, ""]
    text = "\n".join(L)
    check_text(text, [o["mint"] for o in view["opportunities"]])
    return text


def _system_lines(view: dict) -> list[str]:
    s = view["system"]
    d = {"facts": [f"predictive flag on; integration version {s.get('integration_version')}; report version {REPORT_VERSION}; "
                   f"passes in the state: {s['passes']}, last pass {_short(s.get('last_pass_id'))}",
                   f"model registry {s['registry_state']}" + (f" ({I._ident(str(s.get('registry_detail')).split(':')[0], 40)})" if s.get("registry_detail") else "")
                   + f", log sha256 {_short(s.get('registry_log_sha256'))}",
                   f"backtesting {s['backtest_status']}: {STATE_TEXT['BACKTEST_NOT_AVAILABLE'] if s['backtest_status'] == C.BACKTEST_NOT_AVAILABLE else 'installed but not verified by a phase'}; "
                   f"unblocked by {BACKTEST_UNBLOCK}",
                   f"behavioral simulation {SIMULATION_STATE}: {SIMULATION_WHY}",
                   f"state check: {s['state_check_problems']} problems; lab database {view.get('lab_database')}"],
         "inferences": [], "heuristics": [],
         "unknowns": [f"frozen model and reference cards become MODEL_STALE for decisions after {s['model_stale_after_utc']}"]}
    for short, sv in (s.get("served") or {}).items():
        cal = (s.get("calibration") or {}).get(short) or {}
        blk = [str(x) for x in sv.get("blocking") or []]
        d["facts"].append(f"{SHORT_HEAD.get(short, short)}: registry mode {sv.get('mode')} (pin {_short(sv.get('pin_event_id'))}; "
                          f"{', '.join(sv.get('pin_reasons') or []) or 'no reason recorded'})"
                          + (f"; blocking at the pass: {', '.join(blk)}" if blk else "")
                          + f"; Phase 13 calibration {cal.get('status')} at level {cal.get('level')}")
    return ["## System status", "", _ev(d).rstrip(), ""]


def _definition_lines(view: dict) -> list[str]:
    L = ["## Target definitions", ""]
    L.append("| Target | Event | Horizon | Positive | Negative | Version | Scope |")
    L.append("|---|---|---|---|---|---|---|")
    other = []
    for d in view["targets_registry"]:
        if d["status"] != "PRIMARY":
            other.append(d)
            continue
        if d.get("event_words"):
            ev = d["event_words"]
        else:
            ev = f"the price rises {d['upper'] - 1:.0%} before it falls {1 - d['lower']:.0%}"
        L.append(f"| {SHORT_HEAD.get(d['short'], d['short'])} (`{d['target']}`) | {ev} | {d['horizon_seconds'] / 3600:.0f} hours | "
                 f"{', '.join(d['positive'])} | {', '.join(d['negative'])} | {d['version']} | {d['scope_chain']} |")
    prim = next(d for d in view["targets_registry"] if d["status"] == "PRIMARY")
    L += ["", f"- Tie rule: {prim['tie_rule']}.", f"- Price source: {prim['price_source']}.",
          f"- Caveats on every primary target: {', '.join(prim['caveats'])}: a price path is not proceeds, and no executable depth "
          "history exists.", "- Not attempted (registered, not primary):"]
    for d in other:
        L.append(f"  - `{d['target']}`: {d['status']}, {d['horizon_seconds'] / 3600:.0f} hours; {d['why']}")
    return L + [""]


def _carried_lines() -> list[str]:
    d = {"facts": ["no number is shown for an abstention; a probability needs a SHADOW or VALIDATED_EXPERIMENTAL model with a "
                   "CALIBRATED Phase 13 card, enough support and a point inside the display range (Phase 13 rule 12)",
                   "a document is never shown without its abstention record and its request record (Phase 13 m4, PI-D-068)",
                   "a FORECAST's number must equal the point recomputed from the raw number kept in the request record "
                   "(Phase 13 m3, verify_point) and its cards must resolve from the registry",
                   "a calibration available after the decision abstains (CALIBRATION_AFTER_DECISION, PI-D-070)",
                   "the retrospective holdout is spent: its results are exploratory and can only make a statement more conservative",
                   "token text (symbol, chain, labels, file names) is shown as letters, digits, dot, dash and underscore, at most "
                   "24 characters, and withheld when it carries a trading or forecast word (Phase 17 m3); no local path is shown (m8)"],
         "inferences": ["any interval is conditional on exchangeability of the event rate, which is neither established nor "
                        "refuted (PI-D-070)"],
         "heuristics": ["CURRENT_VENDOR_LIST decisions abstain (no point-in-time pool); a live capture records its pool"],
         "unknowns": []}
    return ["## Carried constraints", "", _ev(d).rstrip(), ""]


def _opportunity_lines(o: dict) -> list[str]:
    sn, ex, st = o["snapshot"], o["execution"], o["structural"]
    name = o["symbol"] or "symbol not verified"
    L = [f"## {name} `{o['chain_text']}:{o['mint_text']}`", ""]
    # (a) identity and snapshot
    d = {"facts": [f"exact identity {o['chain_text']}:{o['mint_text']}; event {o['event']}"
                   + (f" ({'; '.join(o['changes'])})" if o["changes"] else ""),
                   f"snapshot {_short(sn['snapshot_hash'], 16)}, row sha256 {_short(sn['row_sha256'], 16)}",
                   f"decision time {sn['decision_time_utc']} ({sn['decision_time_basis']}); capture {sn['capture_time_utc']}",
                   f"inputs observed {sn['observed_at_utc']} (collector-run start, PI-D-011); age at capture {_age(sn['age_at_capture_s'])}: "
                   f"{sn['input_state']}"],
         "inferences": [], "heuristics": [], "unknowns": []}
    if sn["lab_state"] == "SNAPSHOT_VERIFIED":
        d["facts"].append("the lab database row of this snapshot was found and its hash matches (SNAPSHOT_VERIFIED)")
        if sn["token_age_s"] is not None:
            d["heuristics"].append(f"token age at the snapshot {_age(sn['token_age_s'])} (vendor's first pool time {sn['first_pool_at']})")
        else:
            d["unknowns"].append("token age (no vendor first pool time in the verified token row)")
    else:
        d["unknowns"].append(f"token age, symbol and lab labels: SNAPSHOT_NOT_VERIFIED ({sn.get('lab_detail') or 'no detail'})")
    if sn["input_state"] == I.INPUT_STALE:
        d["unknowns"].append("current market state: the inputs were stale at the capture (INPUT_STALE), so every target abstains SOURCE_STALE")
    L += ["### Identity and snapshot", "", _ev(d).rstrip(), ""]
    # (b) structural research
    d = {"facts": [f"the lab's 100-point score at this snapshot: {st['score']}; fatal flags: {', '.join(st['fatal_flags']) or 'none'}"
                   " (unchanged by this report)"],
         "inferences": [], "heuristics": [], "unknowns": []}
    (d["facts"] if st["status_bucket"] == "FACT" else d["unknowns"]).append(f"the lab's status: {st['status']}")
    L += ["### Structural research (the lab's)", "", _ev(d).rstrip(), ""]
    # (c) technical and chart thesis
    if o["technical"]:
        d = {"facts": [], "inferences": [], "heuristics": [f"the lab's lifecycle label {o['technical']['lifecycle']} and structure label "
                                                            f"{o['technical']['structure']} at this snapshot (rule labels, not a forecast)"],
             "unknowns": ["zones, levels and thesis text stay in the lab's token report"]}
    else:
        d = {"facts": [], "inferences": [], "heuristics": [], "unknowns": ["the lab's technical labels (snapshot not verified here)"]}
    L += ["### Technical and chart thesis (the lab's)", "", _ev(d).rstrip(), ""]
    # (d) catalyst evidence
    cat = o["catalyst"]
    src = cat.get("source_status")
    if src == "OK":
        d = {"facts": [f"exact-address catalyst events visible at the decision (OFFICIAL or NAMED_IN_SOURCE, STRONG): {cat.get('exact_events')}"],
             "inferences": [], "heuristics": [f"ticker or name links: {cat.get('context_links')}; context only, never identity (PI-D-007)"],
             "unknowns": ["whether any catalyst is confirmed: a catalyst is a claim, not an input, and no catalyst target is frozen (BLOCKED_NO_DATA)"]}
    else:
        d = {"facts": [], "inferences": [], "heuristics": [],
             "unknowns": [f"catalyst evidence: {I._ident(src, 40)} ({STATE_TEXT.get(str(src), 'not available')})"]}
    L += ["### Catalyst evidence", "", _ev(d).rstrip(), ""]
    # (e) predictive research per target
    L += ["### Predictive research", ""]
    L.append("| Target | Horizon | Status | Reasons | Cohort N and base rate | Model | Training as of | Record |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in o["targets"]:
        hz = f"{(t['horizon_seconds'] or 0) / 3600:.0f} hours"
        if t["status"] == "DOCUMENT_REFUSED":
            L.append(f"| {SHORT_HEAD.get(t['short'], t['short'])} | {hz} | REFUSED (no number) | DOCUMENT_REFUSED | not shown | not shown | not shown | none |")
            continue
        n = t.get("number")
        coh = (f"support {n['support_n']} calibration events ({n['support_k']} positive); base rate {_pct(n['base_rate'])}"
               if n and _fin(n.get("base_rate")) else "not shown: no model selected")
        L.append(f"| {SHORT_HEAD.get(t['short'], t['short'])} | {hz} | {_row_status(t, ex['veto'])} | {', '.join(t['reasons']) or 'none'} | "
                 f"{coh} | {t['model_id']} (sha {_short(t['model_sha'])}) | {t['training_cutoff_utc'] or 'none'} | {_short(t['record_id'])} |")
    L.append("")
    abst = [t for t in o["targets"] if t["status"] == "ABSTAIN"]
    groups: dict[tuple, list[str]] = {}
    for t in abst:
        groups.setdefault(tuple(t["explanations"]), []).append(SHORT_HEAD.get(t["short"], t["short"]))
    for expl, names in groups.items():
        L.append(f"- No probability for {', '.join(names)}, from the abstention records: " + "; ".join(expl) + ".")
    reasons = [r for r in C.ABSTAIN_REASONS if any(r in t["reasons"] for t in abst)]
    if reasons:
        L.append("- What would unblock each named reason:")
        L += [f"  - {r}: {UNBLOCK.get(r, 'a recorded decision')}." for r in reasons]
    for t in o["targets"]:
        head = f"- {SHORT_HEAD.get(t['short'], t['short'])} ({I.TARGET_WORDS.get(t['target'], t['target'])})"
        if t["status"] == "DOCUMENT_REFUSED":
            L.append(f"{head}: DOCUMENT_REFUSED. {STATE_TEXT['DOCUMENT_REFUSED']} Failed checks: {'; '.join(t['checks'])}.")
            continue
        if t["status"] == "ABSTAIN":
            continue
        n = t["number"]
        L.append(f"{head}: research estimate at level {n['level']} ({n['method']}), {_pct(n['probability'])} with interval "
                 f"{_pct(n['interval'][0])} to {_pct(n['interval'][1])}; base rate {_pct(n['base_rate'])}; support {n['support_n']} "
                 f"calibration events; calibration card {_short(n['calibration_card_sha'])}; {PRICE_PATH_LINE}."
                 + (f" {WATERMARK}." if t.get("is_fixture") else ""))
        if ex["veto"]:
            L.append("  - Overridden: this snapshot carries a veto (below); the lab's fatal-flag override applies unchanged and the "
                     "estimate is not usable for any decision on it.")
        L.append(f"  - Caveats: {', '.join(t['caveats'])}.")
    L.append("")
    # (f) historical prediction and its out-of-sample record
    rf = o["registry_facts"]
    d = {"facts": [], "inferences": [], "heuristics": [], "unknowns": []}
    if rf.get("state") != "OK":
        d["unknowns"].append(f"out-of-sample record: {rf.get('state')} ({STATE_TEXT.get(rf.get('state'), 'the committed registry index is not available')})")
    else:
        for t in o["targets"]:
            tf = rf["targets"].get(t["short"]) or {}
            if tf.get("event_id") != t["registry"].get("pin_event_id"):
                d["unknowns"].append(f"{SHORT_HEAD.get(t['short'], t['short'])}: REGISTRY_INDEX_MISMATCH ({STATE_TEXT['REGISTRY_INDEX_MISMATCH']})")
                continue
            refs = "; ".join(f"{r['reference']} {str(r['model_id']).split(':')[0]} {r['retrospective_verdict'] or 'is the skill reference'}"
                             + (f" ({r['retrospective_events']} events, {r['retrospective_days']} days)" if r.get("retrospective_events") else "")
                             for r in tf.get("references") or [])
            pro = sorted({str(r.get("prospective_status")) for r in tf.get("references") or []})
            d["facts"].append(f"{SHORT_HEAD.get(t['short'], t['short'])}: registry {tf.get('mode')}, pin matches the committed index; "
                              f"references (never published): {refs or 'none'}; prospective {', '.join(pro) or 'none'}")
        d["inferences"].append("no model showed skill over the base rate out of sample (Phase 12) and none is calibrated (Phase 13); "
                               "the retrospective holdout is spent, so these verdicts are exploratory")
    L += ["### Historical prediction and its out-of-sample record", "", _ev(d).rstrip(), ""]
    # (g) execution and stress
    d = {"facts": [f"fatal-flag veto: {', '.join(ex['fatal_flags']) + '; no forecast clears it' if ex['structural_veto'] else 'none recorded by the lab'}",
                   f"backtest: {ex['backtest_result']} (installed state {ex['backtest_installed']})"
                   + (f"; backtest veto {', '.join(ex['backtest_veto_reasons'])}" if ex["backtest_veto"] else ""),
                   f"size basis {ex['size_basis']}; depth {ex['depth_state']}; size taken from a forecast: none",
                   f"{PRICE_PATH_LINE}; a predicted price path never shows realizable exit"],
         "inferences": [], "heuristics": [], "unknowns": []}
    if ex["veto_unknown"]:
        d["unknowns"].append("fatal-flag check unknown (no readable flag list), treated as not cleared")
    if ex["backtest_result"] in (C.BACKTEST_NOT_AVAILABLE, "UNTESTED", None):
        d["unknowns"].append(f"execution and stress assessment: {C.BACKTEST_NOT_AVAILABLE}; unblocked by {BACKTEST_UNBLOCK}")
    if ex["size_basis"] == "EXECUTION_DATA_MISSING":
        d["unknowns"].append(f"exit capacity at any size: EXECUTION_DATA_MISSING; unblocked by {UNBLOCK['EXECUTION_DATA_MISSING']}")
    L += ["### Execution and stress", "", _ev(d).rstrip(), ""]
    # (h) behavioral scenarios
    sc = sorted({s for t in o["targets"] for s in t.get("scenarios") or []})
    d = {"facts": [f"behavioral simulation {SIMULATION_STATE}: {SIMULATION_WHY}"], "inferences": [],
         "heuristics": ([f"synthetic hypotheses listed by label only, never a probability: {', '.join(sc)}"] if sc else []),
         "unknowns": ([] if sc else ["no behavioral scenario was run for this snapshot"])}
    L += ["### Behavioral scenarios", "", _ev(d).rstrip(), ""]
    # (i) sources and ids
    ids = o["ids"]
    L += ["### Sources and ids", ""]
    L.append(f"- Request record {_short(ids['request_record_id'])} (request {ids['request_seq']}, pass {_short(ids['pass_id'])})"
             + (f"; previous attempt {_short(o['previous_request_record_id'])}" if o.get("previous_request_record_id") else ""))
    for t in o["targets"]:
        L.append(f"- {SHORT_HEAD.get(t['short'], t['short'])}: forecast `{t['forecast_id']}`, record {_short(t.get('record_id'))}, "
                 f"registry pin {_short(t['registry'].get('pin_event_id'))}, data {_short(t.get('data_snapshot_sha'))}, "
                 f"features {_short(t.get('feature_set_sha'))}")
    L.append(f"- Token report: {ids['token_report'] or 'none recorded'} (the lab's report of this snapshot; its sections are unchanged)")
    L.append("")
    # (j) limitations
    cav = sorted({c for t in o["targets"] for c in t.get("caveats") or []})
    L += ["### Limitations", ""]
    L.append(f"- Caveats: {', '.join(cav) or 'none'}.")
    L.append("- Registered targets not attempted: " + "; ".join(f"`{p['target']}` {p['status']}" for p in o["not_attempted_targets"]) + "."
             if o["not_attempted_targets"] else "- Registered targets not attempted: none.")
    L.append("- A forecast here is a research input, never an order; the lab's fatal-flag overrides and sizing rules apply unchanged.")
    L.append("")
    return L


def _not_attempted_lines(view: dict) -> list[str]:
    na = view["not_attempted"]
    L = ["## Events not attempted", ""]
    if not na:
        return L + ["- None.", ""]
    L.append("| Event | Exact chain:mint | Capture (UTC) | Covered by a report above | Request | Detail |")
    L.append("|---|---|---|---|---|---|")
    for r in na:
        L.append(f"| {r['event']} | `{r['chain']}:{r['mint']}` | {r['capture_time_utc']} | {'yes' if r['covered_by_report'] else 'no'} | "
                 f"{_short(r['request_record_id'])} | {', '.join(r['errors']) or 'none'} |")
    return L + [""]


def _units_lines() -> list[str]:
    return ["## Units and times", "",
            "- Times are UTC in ISO 8601 with Z. Ages are in minutes, hours or days as written. Horizons are in hours. Amounts are USD.",
            "- Percentages appear only in target definitions (barriers) and in a verified FORECAST (point and interval, whole percents).",
            "- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the JSON view "
            "has them in full).", "- Buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), "
            "UNKNOWN (missing; earns nothing).", ""]


# ---------------------------------------------------------------- alerts (rules 9 to 11)
ALERT_POLICY_SCHEMA = "memelab.predictive.alerts.policy/1"
ALERT_SCHEMA = "memelab.predictive.alert/1"
POLICIES = ("risk_override", "reevaluate", "forecast_withdrawn", "pipeline_health")
DEFAULT_ALERT_POLICY: dict[str, Any] = {
    "schema": ALERT_POLICY_SCHEMA, "version": "predictive-alerts-policy-1", "rules_version": ALERT_RULES_VERSION,
    "tz": "America/New_York", "quiet_hours": {"start": "22:00", "end": "07:00"}, "quiet_hours_bypass": [], "daily_cap": 8,
    "min_interval_minutes": 60, "source_max_age_hours": 24.0, "hold_max_hours": 14.0, "dedupe_retention_days": 30,
    "delivery": "file_sink_dry_run_only", "trade_execution_impact": "none",
    "policies": {"risk_override": {"severity": "warning", "cooldown_hours": 6.0, "liquidity_fall_rel": 0.20},
                 "reevaluate": {"severity": "notice", "severity_drawdown_target": "warning", "cooldown_hours": 12.0,
                                "levels": ["SHADOW", "VALIDATED_EXPERIMENTAL"]},
                 "forecast_withdrawn": {"severity": "notice", "cooldown_hours": 12.0},
                 "pipeline_health": {"severity": "notice", "severity_tampered": "warning", "cooldown_hours": 24.0}},
}


def make_alert_policy(overrides: dict | None = None) -> dict:
    """The default policy merged with overrides and validated like `alerts_core.make_policy` (rule 10)."""
    p = AC._merge(DEFAULT_ALERT_POLICY, overrides or {})
    if p.get("schema") != ALERT_POLICY_SCHEMA:
        raise AC.AlertError(f"policy schema must be {ALERT_POLICY_SCHEMA}")
    if p.get("trade_execution_impact") != "none" or p.get("delivery") != "file_sink_dry_run_only":
        raise AC.AlertError("trade_execution_impact must be none and delivery file_sink_dry_run_only")
    AC.zone(p["tz"])
    AC._hhmm(p["quiet_hours"]["start"])
    AC._hhmm(p["quiet_hours"]["end"])
    if not 0 <= int(p["daily_cap"]) <= 50:
        raise AC.AlertError("daily_cap must be between 0 and 50")
    if float(p["min_interval_minutes"]) < 60:
        raise AC.AlertError("min_interval_minutes below 60")
    for s in p.get("quiet_hours_bypass") or []:
        if s not in AC.SEVERITIES:
            raise AC.AlertError(f"unknown severity {s!r} in quiet_hours_bypass")
    if set(p["policies"]) != set(POLICIES):
        raise AC.AlertError(f"policies must be exactly {POLICIES}")
    for name, cfg in p["policies"].items():
        for k, v in cfg.items():
            if k.startswith("severity") and v not in AC.SEVERITIES:
                raise AC.AlertError(f"policy {name}: {k} must be one of {AC.SEVERITIES}")
        if float(cfg.get("cooldown_hours", 0)) < 1:
            raise AC.AlertError(f"policy {name}: cooldown_hours must be at least 1")
    p["policy_sha256"] = AC._sha({k: v for k, v in p.items() if k != "policy_sha256"})
    return p


def _label(o: dict) -> str:
    return f"{o.get('symbol') or 'symbol not verified'} on {o['chain_text']} ({o['mint_text']})"


def _liquidity_fall(changes: Sequence[str]) -> float | None:
    worst = None
    for c in changes or []:
        m = re.fullmatch(r"liquidity ([+-]\d+(?:\.\d+)?)%", str(c))
        if m:
            v = float(m.group(1)) / 100.0
            worst = v if worst is None else min(worst, v)
    return worst


def alert_candidates(view: dict, requests: Sequence[dict], *, policy: dict, now: float, fixture_run: bool = False,
                     errors: Sequence[dict] = ()) -> tuple[list[dict], list[dict]]:
    """Candidates and suppressions for the given request views (each a `_opportunity` dict with its request record), under the
    frozen policies of rule 10. Pure: no I/O, no clock."""
    cands: list[dict] = []
    supp: list[dict] = []
    pol = policy["policies"]

    def base(o: dict, name: str, sev: str) -> dict:
        return {"policy": name, "severity": sev, "item_id": f"{o['chain']}:{o['mint']}", "label": _label(o), "chain": o["chain_text"],
                "contract": o["mint_text"], "mint": o["mint"], "fixture": any(t.get("is_fixture") for t in o["targets"]),
                "observed_at_utc": o["snapshot"]["observed_at_utc"], "capture_time_utc": o["snapshot"]["capture_time_utc"],
                "snapshot_hash": o["snapshot"]["snapshot_hash"], "request_record_id": o["ids"]["request_record_id"],
                "pass_id": o["ids"]["pass_id"], "records": [t.get("record_id") for t in o["targets"]],
                "forecasts": [f"{SHORT_HEAD.get(t['short'], t['short'])} {t['status']}" for t in o["targets"]]}

    def sup(o: dict | None, name: str, code: str, why: str) -> None:
        supp.append({"policy": name, "item_id": f"{o['chain']}:{o['mint']}" if o else "pipeline", "label": _label(o) if o else "pipeline",
                     "reason_code": code, "reason": why})

    def cand(b: dict, *, fingerprint: Any, reason: str, bucket: str, cooldown_key: str) -> dict:
        c = dict(b, reason=reason, bucket=bucket, cooldown_key=cooldown_key)
        c["dedupe_key"] = AC._sha([b["policy"], b["item_id"], fingerprint])[:32]
        return c

    st = view.get("state")
    if st in ("STATE_TAMPERED", "STATE_CHECK_FAILED"):
        b = {"policy": "pipeline_health", "severity": pol["pipeline_health"]["severity_tampered"], "item_id": "pipeline",
             "label": "predictive state", "chain": None, "contract": None, "mint": None, "fixture": bool(fixture_run),
             "observed_at_utc": None, "capture_time_utc": None, "snapshot_hash": None, "request_record_id": None,
             "pass_id": (view.get("system") or {}).get("last_pass_id"), "records": [], "forecasts": []}
        cands.append(cand(b, fingerprint=[st, view.get("state_check_problems")], reason=f"{st}: {STATE_TEXT.get(st, '')}",
                          bucket="FACT", cooldown_key=f"pipeline_health:{st}"))
    for e in errors:
        b = {"policy": "pipeline_health", "severity": pol["pipeline_health"]["severity"], "item_id": "pipeline",
             "label": "predictive pass", "chain": None, "contract": None, "mint": None, "fixture": bool(fixture_run),
             "observed_at_utc": None, "capture_time_utc": e.get("capture_time_utc"), "snapshot_hash": None,
             "request_record_id": e.get("record_id"), "pass_id": e.get("pass_id"), "records": [], "forecasts": []}
        cands.append(cand(b, fingerprint=["ERROR", e.get("record_id")], bucket="FACT", cooldown_key="pipeline_health:ERROR",
                          reason=f"an event failed in the pass ({', '.join(e.get('errors') or []) or 'no label'}); nothing was saved for "
                                 "it and the next pass attempts it again"))
    for o in requests:
        if o["mint_text"] == "not-an-exact-address":
            sup(o, "risk_override", "NOT_EXACT_IDENTITY", "the mint is not an exact address of its chain")
            continue
        fixture = any(t.get("is_fixture") for t in o["targets"])
        if fixture and not fixture_run:
            sup(o, "risk_override", "FIXTURE_IN_LIVE_RUN", "fixture documents in a run not marked fixture")
            continue
        cap = _parse(o["snapshot"]["capture_time_utc"])
        stale = o["snapshot"]["input_state"] == I.INPUT_STALE or cap is None or now - cap > float(policy["source_max_age_hours"]) * 3600
        ex = o["execution"]
        verified = [t for t in o["targets"] if t.get("number")]
        # pipeline health from the request's served states
        for t in o["targets"]:
            for b_ in t["registry"].get("blocking") or []:
                if b_ in ("MODEL_STALE", "DRIFT_ALERT", "REGISTRY_UNAVAILABLE"):
                    b = base(o, "pipeline_health", pol["pipeline_health"]["severity"])
                    cands.append(cand(b, fingerprint=[b_, t["short"], o["ids"]["pass_id"]], bucket="FACT",
                                      reason=f"{SHORT_HEAD.get(t['short'], t['short'])}: {b_} among the served model's blocking states; "
                                             "the target abstains", cooldown_key=f"pipeline_health:{b_}"))
        # risk_override
        fall = _liquidity_fall(o.get("changes") or [])
        lim = float(pol["risk_override"]["liquidity_fall_rel"])
        risky = ex["structural_veto"] or ex["veto_unknown"] or ex["backtest_veto"] is True or (fall is not None and fall <= -lim + 1e-12)
        if risky:
            parts = []
            if ex["structural_veto"]:
                parts.append(f"fatal flags {', '.join(ex['fatal_flags'])}")
            if ex["veto_unknown"]:
                parts.append("fatal-flag check unknown")
            if ex["backtest_veto"] is True:
                parts.append(f"backtest veto {', '.join(ex['backtest_veto_reasons'])}")
            if fall is not None and fall <= -lim + 1e-12:
                parts.append(f"liquidity {fall:+.0%} since the previous attempt")
            why = ("Risk flag on this snapshot: " + "; ".join(parts) + ". No forecast clears it; the lab's fatal-flag override "
                   "applies unchanged.")
            if verified:
                why += " The research estimate on this snapshot is overridden."
            if stale:
                sup(o, "risk_override", "SOURCE_STALE", "the inputs or the request are too old for an alert; the report still shows the flag")
            else:
                b = base(o, "risk_override", pol["risk_override"]["severity"])
                cands.append(cand(b, fingerprint=[o["snapshot"]["snapshot_hash"], sorted(parts)], reason=why, bucket="FACT",
                                  cooldown_key=f"risk_override:{o['chain']}:{o['mint']}"))
        # reevaluate
        for t in verified:
            n = t["number"]
            if n.get("level") not in pol["reevaluate"]["levels"] or not (_fin(n.get("base_rate")) and n["interval"][0] > float(n["base_rate"]) + _TOL):
                continue
            if ex["veto"] or ex["backtest_veto"] is True:
                sup(o, "reevaluate", "VETO_OVERRIDES_FORECAST", "the snapshot carries a veto: the risk warning stands instead")
                continue
            if stale:
                sup(o, "reevaluate", "SOURCE_STALE", "the inputs or the request are too old for an alert")
                continue
            sev = pol["reevaluate"]["severity_drawdown_target"] if "drawdown" in t["target"] else pol["reevaluate"]["severity"]
            b = base(o, "reevaluate", sev)
            cands.append(cand(b, fingerprint=t["forecast_id"], bucket="INFERENCE", cooldown_key=f"reevaluate:{o['chain']}:{o['mint']}:{t['short']}",
                              reason=(f"A verified research estimate ({n['level']}) for {I.TARGET_WORDS.get(t['target'], t['target'])}: "
                                      f"{_pct(n['probability'])}, interval {_pct(n['interval'][0])} to {_pct(n['interval'][1])}, above the "
                                      f"base rate {_pct(n['base_rate'])}. It may prompt re-evaluation only; it changes no score, status or "
                                      f"list. {PRICE_PATH_LINE[0].upper() + PRICE_PATH_LINE[1:]}.")))
        # forecast_withdrawn
        for short, prev in (o.get("previous_targets") or {}).items():
            cur = next((t for t in o["targets"] if t["short"] == short), None)
            if prev and cur is not None and cur["status"] != "FORECAST":
                if stale:
                    sup(o, "forecast_withdrawn", "SOURCE_STALE", "the inputs or the request are too old for an alert")
                    continue
                b = base(o, "forecast_withdrawn", pol["forecast_withdrawn"]["severity"])
                cands.append(cand(b, fingerprint=[prev, cur.get("forecast_id")], bucket="FACT",
                                  cooldown_key=f"forecast_withdrawn:{o['chain']}:{o['mint']}:{short}",
                                  reason=(f"The research estimate for {SHORT_HEAD.get(short, short)} shown at the previous attempt is "
                                          f"withdrawn: the target now shows {cur['status']} ({', '.join(cur.get('reasons') or cur.get('checks') or [])}).")))
    cands.sort(key=lambda c: (-AC.SEVERITIES.index(c["severity"]), c["policy"], str(c["item_id"]), c["dedupe_key"]))
    return cands, supp


def render_alert_text(a: dict, tz: str) -> str:
    """Plain text, no markup (the social alert layout), with the disclaimer; fixture banner first and last (rule 8, 11)."""
    L = []
    if a.get("fixture"):
        L.append(WATERMARK + "; not a live alert.")
    L += [f"memelab predictive research alert, {a['severity'].upper()}: {a['policy'].replace('_', ' ')}", a["label"], f"Why: {a['reason']}",
          f"Evidence bucket: {a['bucket']}", f"Forecasts on this snapshot: {'; '.join(a.get('forecasts') or []) or 'none'}",
          f"Freshness: inputs observed {AC.local_text(_parse(a.get('observed_at_utc')), tz)}, captured {AC.local_text(_parse(a.get('capture_time_utc')), tz)}"]
    if a.get("chain") and a.get("contract"):
        L.append(f"Contract: {a['chain']}:{a['contract']}")
    L.append(f"Sources: request {_short(a.get('request_record_id'))}, pass {_short(a.get('pass_id'))}, snapshot {_short(a.get('snapshot_hash'), 16)}, "
             f"records {', '.join(_short(r) for r in a.get('records') or []) or 'none'}")
    L.append(f"Alert {a.get('alert_id', 'new')}, dedupe {a['dedupe_key'][:12]}, policy {a.get('policy_version')} {str(a.get('policy_sha256'))[:12]}, "
             f"rules {ALERT_RULES_VERSION}")
    L.append(AC.DISCLAIMER)
    if a.get("fixture"):
        L.append(WATERMARK + "; not a live alert.")
    text = "\n".join(L) + "\n"
    check_text(text, [a.get("mint") or ""])
    return text


def default_alert_db() -> Path:
    from .. import db
    return Path(db.DB_PATH).parent / "private" / "predictive_alerts" / "alerts.sqlite"


def _refuse_path(p: Path, what: str) -> None:
    why = I.state_dir_refusal(p if p.suffix == "" else p.parent)
    if why:
        raise AlertRefused(f"{what}: {why}")


def alert_run(state_dir: str | Path | None = None, *, config_path: str | Path | None = None, alert_db: str | Path | None = None,
              outbox: str | Path | None = None, now: float | None = None, policy: dict | None = None, send: bool = False,
              fixture_run: bool = False, registry_dir: str | Path | None = None, root: str | Path | None = None,
              extra_cal_cards: dict | None = None, lab_db: str | Path | None = None) -> dict | None:
    """One dry-run alert evaluation (rules 9 to 11). None when the flag is off (nothing read but the config, nothing written)."""
    if send:
        raise AlertRefused("--send refused: no external delivery is approved (PI-D-005); alerts are dry run only")
    if not I.config(config_path)["enabled"]:
        return None
    pol = policy or make_alert_policy()
    now = float(now) if now is not None else time.time()
    dbp = Path(alert_db) if alert_db is not None else default_alert_db()
    box = Path(outbox) if outbox is not None else dbp.parent / "outbox"
    _refuse_path(dbp, "alert database")
    _refuse_path(box, "alert outbox")
    view = build(state_dir, config_path=config_path, registry_dir=registry_dir, root=root, extra_cal_cards=extra_cal_cards)
    con = AE.connect(dbp)
    mode = "dry_run"
    out: dict[str, Any] = {"mode": mode, "now": now, "now_text": AC.local_text(now, pol["tz"]), "policy_version": pol["version"],
                           "policy_sha256": pol["policy_sha256"], "rules_version": ALERT_RULES_VERSION, "fixture": bool(fixture_run)}
    try:
        sysv = view.get("system") or {}
        seq = (sysv.get("passes") or 0) - 1 if sysv else None
        cur = con.execute("INSERT INTO alert_runs(mode, started_at, as_of, feed_sha256, snapshot_run_id, fixture, policy_version, policy_sha256, "
                          "outcome) VALUES (?,?,?,?,?,?,?,?,?)", (mode, now, now, sysv.get("last_pass_record_id"), seq, int(bool(fixture_run)),
                                                                 pol["version"], pol["policy_sha256"], "started"))
        run_id = cur.lastrowid
        out["run_id"] = run_id
        AE.purge(con, policy=pol, now=now)
        prev = con.execute("SELECT started_at, snapshot_run_id, fixture FROM alert_runs WHERE mode=? AND outcome='evaluated' AND run_id<>? "
                           "ORDER BY started_at DESC, run_id DESC LIMIT 1", (mode, run_id)).fetchone()
        ev: dict[str, Any] = {"candidates": 0, "new": [], "deduped": 0, "suppressed": [], "quiet_hours": AC.in_quiet_hours(now, pol)}
        if view.get("state") in ("FLAG_OFF", "NO_STATE", "STATE_TAMPERED", "STATE_DIR_REFUSED"):
            outcome = "feed_unavailable"
            out["reason"] = f"{view.get('state')}: {STATE_TEXT.get(view.get('state'), '')}"
            if view.get("state") == "STATE_TAMPERED":
                ev = _evaluate(con, run_id=run_id, view=view, requests=[], policy=pol, now=now, outbox=box, fixture_run=fixture_run)
        elif prev is not None and now - prev["started_at"] < float(pol["min_interval_minutes"]) * 60:
            outcome = "too_soon"
            out["reason"] = f"last evaluation {round((now - prev['started_at']) / 60)} min ago; policy interval {pol['min_interval_minutes']} min"
        elif prev is not None and prev["snapshot_run_id"] == seq and bool(prev["fixture"]) == bool(fixture_run):
            outcome = "no_new_upstream_data"
            out["reason"] = f"pass {seq} was already evaluated"
        else:
            outcome = "evaluated"
            first = (prev["snapshot_run_id"] + 1) if prev is not None and prev["snapshot_run_id"] is not None else 0
            reqs, errs = _new_request_views(state_dir, config_path=config_path, registry_dir=registry_dir, root=root,
                                            extra_cal_cards=extra_cal_cards, first_pass_seq=first, lab_db=lab_db)
            ev = _evaluate(con, run_id=run_id, view=view, requests=reqs, policy=pol, now=now, outbox=box, fixture_run=fixture_run,
                           errors=errs)
        out.update({"outcome": outcome, "evaluation": ev, "delivery": {"processed": list(ev["new"]), "released": [], "expired": []}})
        summary = {"candidates": ev["candidates"], "new": ev["new"], "deduped": ev["deduped"], "suppressed": len(ev["suppressed"]),
                   "reason": out.get("reason")}
        con.execute("UPDATE alert_runs SET finished_at=?, outcome=?, summary_json=? WHERE run_id=?", (now, outcome, json.dumps(summary, sort_keys=True), run_id))
        con.commit()
    finally:
        con.close()
    return out


def _new_request_views(state_dir: Any, *, config_path: Any, registry_dir: Any, root: Any, extra_cal_cards: dict | None,
                       first_pass_seq: int, lab_db: Any = None) -> tuple[list[dict], list[dict]]:
    """Every attempted request of the passes from `first_pass_seq` on, each as an opportunity view with its previous attempt's
    verified forecasts (for forecast_withdrawn)."""
    cfg = I.config(config_path)
    rootp = Path(root) if root is not None else I.ROOT
    sdir = Path(state_dir or cfg["state_dir"] or I.default_state_dir())
    st = I.load_state(sdir)
    chk = I.check_state(sdir, config_path=config_path)
    refused_ids, refused_seqs = _problem_ids(chk.get("problems") or [])
    rdir = Path(registry_dir) if registry_dir is not None else rootp / I.REGISTRY_DIR
    reg = I.load_registry(rdir)
    regfacts = _registry_facts(rdir, reg)
    pass_seq = {p["pass_id"]: p["seq"] for p in st["lines"]["passes"]}
    att = _attempts(st)
    out = []
    lab = None
    if lab_db is not None:
        try:
            lab = I.connect_lab_ro(lab_db)
        except Exception:  # noqa: BLE001
            lab = None
    try:
        for key, lst in sorted(att.items()):
            for i, r in enumerate(lst):
                if pass_seq.get(r["pass_id"], -1) < first_pass_seq:
                    continue
                prev = lst[i - 1] if i > 0 else None
                kw = dict(refused_ids=refused_ids, refused_seqs=refused_seqs, reg=reg, regfacts=regfacts, lab=lab, root=rootp,
                          extra=extra_cal_cards, config_path=config_path)
                o = _opportunity(_request_view(st, r, prev=prev, **kw))
                if prev is not None:
                    po = _opportunity(_request_view(st, prev, prev=None, **kw))
                    o["previous_targets"] = {t["short"]: t["forecast_id"] for t in po["targets"] if t.get("number")}
                out.append(o)
    finally:
        if lab is not None:
            lab.close()
    errs = [{"record_id": r.get("record_id"), "pass_id": r.get("pass_id"), "capture_time_utc": r.get("capture_time_utc"),
             "errors": [_code(str(x).split(":")[0]) for x in r.get("errors") or []]}
            for r in st["lines"]["requests"] if r.get("event") == "ERROR" and pass_seq.get(r["pass_id"], -1) >= first_pass_seq]
    return out, errs


def _evaluate(con: sqlite3.Connection, *, run_id: int, view: dict, requests: list[dict], policy: dict, now: float, outbox: Path,
              fixture_run: bool, errors: Sequence[dict] = ()) -> dict:
    tz = policy["tz"]
    cands, supp = alert_candidates(view, requests, policy=policy, now=now, fixture_run=fixture_run, errors=errors)
    day = AC.local_day(now, tz)
    used = con.execute("SELECT COUNT(*) FROM alert_events WHERE mode='dry_run' AND local_day=?", (day,)).fetchone()[0]
    quiet = AC.in_quiet_hours(now, policy)
    sink = AT.FileSink(outbox)
    new, deduped = [], 0
    for c in cands:
        if con.execute("SELECT 1 FROM alert_events WHERE mode='dry_run' AND dedupe_key=?", (c["dedupe_key"],)).fetchone():
            deduped += 1
            continue
        cfg = policy["policies"][c["policy"]]
        if AE._in_cooldown(con, "dry_run", c["cooldown_key"], now, float(cfg["cooldown_hours"])):
            supp.append({"policy": c["policy"], "item_id": c["item_id"], "label": c["label"], "reason_code": "cooldown",
                         "reason": f"an alert for this went out less than {cfg['cooldown_hours']:g} h ago"})
            continue
        if used >= int(policy["daily_cap"]):
            supp.append({"policy": c["policy"], "item_id": c["item_id"], "label": c["label"], "reason_code": "daily_cap",
                         "reason": f"daily cap of {policy['daily_cap']} alerts reached for {day} ({tz})"})
            continue
        a = {**c, "schema": ALERT_SCHEMA, "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"],
             "created_at": now, "created_text": AC.local_text(now, tz), "mode": "dry_run", "quiet_hours": quiet,
             "trade_execution_impact": "none", "rules_version": ALERT_RULES_VERSION}
        cur = con.execute("INSERT INTO alert_events(mode, dedupe_key, cooldown_key, policy, severity, item_id, label, created_at, local_day, "
                          "status, fixture, transports_json, alert_json, run_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("dry_run", c["dedupe_key"], c["cooldown_key"], c["policy"], c["severity"], c["item_id"], c["label"], now, day,
                           "PREVIEW", int(bool(c["fixture"])), json.dumps(["file"]), "{}", run_id))
        a["alert_id"] = cur.lastrowid
        text = render_alert_text(a, tz)
        con.execute("UPDATE alert_events SET alert_json=? WHERE alert_id=?", (json.dumps(a, sort_keys=True, default=str), a["alert_id"]))
        res = sink.send(a["alert_id"], text, preview=True)
        con.execute("INSERT INTO alert_deliveries(alert_id, mode, transport, dest_ref, attempt, status, started_at, finished_at, error) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (a["alert_id"], "dry_run", "file", AT.dest_ref("file", sink.destination()), 1,
                                                   "dry_run_preview", now, now,
                                                   "preview file written; nothing sent" if res.ok else (res.error or "preview failed")))
        used += 1
        new.append(a)
    for s in supp:
        con.execute("INSERT INTO alert_suppressions(run_id, policy, item_id, reason_code, reason) VALUES (?,?,?,?,?)",
                    (run_id, s["policy"], s.get("item_id"), s["reason_code"], s["reason"]))
    con.commit()
    return {"candidates": len(cands), "new": [a["alert_id"] for a in new], "deduped": deduped, "suppressed": supp, "quiet_hours": quiet,
            "alerts": [{k: a[k] for k in ("alert_id", "policy", "severity", "label", "dedupe_key", "fixture")} for a in new]}


# ---------------------------------------------------------------- CLI (rule 12)
def _write_out(path: str, text: str) -> None:
    p = Path(path)
    why = I.state_dir_refusal(p.parent)
    if why:
        raise AlertRefused(f"output: {why}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m memelab.predictive.reports")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("report")
    for a in ("--state-dir", "--config", "--lab-db", "--registry-dir", "--out", "--mint"):
        p.add_argument(a)
    p.add_argument("--json", action="store_true")
    p = sp.add_parser("alerts")
    for a in ("--state-dir", "--config", "--alert-db", "--outbox", "--registry-dir", "--lab-db"):
        p.add_argument(a)
    p.add_argument("--as-of", type=float)
    p.add_argument("--send", action="store_true")
    p.add_argument("--fixture-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sp.add_parser("alerts-state")
    p.add_argument("--alert-db")
    p.add_argument("--config")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "report":
            if not I.config(a.config)["enabled"]:
                print("predictive: FLAG_OFF; nothing read or rendered")
                return 0
            view = build(a.state_dir, config_path=a.config, lab_db=a.lab_db, registry_dir=a.registry_dir, mint=a.mint)
            text = json.dumps(view, indent=1, sort_keys=True, default=str) + "\n" if a.json else render(view)
            if a.out:
                _write_out(a.out, text)
                print(f"report written: {Path(a.out).name} ({view.get('state')}, {(view.get('counts') or {}).get('probabilities_shown', 0)} probabilities shown)")
            else:
                print(text, end="" if text.endswith("\n") else "\n")
            return 0
        if a.cmd == "alerts":
            out = alert_run(a.state_dir, config_path=a.config, alert_db=a.alert_db, outbox=a.outbox, now=a.as_of, send=a.send,
                            fixture_run=a.fixture_run, registry_dir=a.registry_dir, lab_db=a.lab_db)
            if out is None:
                print("predictive: FLAG_OFF; nothing evaluated or written")
                return 0
            if a.json:
                print(json.dumps(out, indent=1, sort_keys=True, default=str))
            else:
                txt = AE.render_run(out, DEFAULT_ALERT_POLICY["tz"])
                print(txt + "Delivery: previews in the local outbox only (dry run); nothing was sent to any device.")
            return 0
        if not I.config(a.config)["enabled"]:
            print("predictive: FLAG_OFF; nothing read")
            return 0
        dbp = Path(a.alert_db) if a.alert_db else default_alert_db()
        if not dbp.exists():
            print("no predictive alert state yet")
            return 0
        con = AE.connect(dbp)
        try:
            v = AE.state_view(con)
        finally:
            con.close()
        print(json.dumps(v, indent=1, sort_keys=True, default=str) if a.json else AE.render_state(v, DEFAULT_ALERT_POLICY["tz"]), end="")
        return 0
    except (AlertRefused, AC.AlertError, ReportError) as e:
        print(f"predictive reports: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

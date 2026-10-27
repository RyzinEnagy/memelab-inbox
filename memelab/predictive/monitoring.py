"""Phase 19: outcome tracking, prospective replay and model drift (monitoring-1). Research only, flag OFF, imported by no module.

Rules: audits/predictive-intelligence/phase_19/ACCEPTANCE_CHECKLIST.md (PI-D-104). numpy and the standard library plus
`contract`, `stats`, `labels` and `baselines` of this package; never the evaluation, registry, calibration, abstention,
integration or report modules (their isolation tests are unchanged). Wiring to the registry lives in probes and tests.

  - The outcome ledger `outcome-ledger-1` is append-only and sha-chained (rule 4): one canonical JSON line per entry with
    `seq`, `prev` (the previous line's sha256) and `sha` (sha256 of the entry without `sha`). Predictions and documents are
    written once; the same id with other content is PREDICTION_EDIT_REFUSED; a prediction or document for a (decision, target)
    that already has an outcome is LATE_PREDICTION_REFUSED whatever time it claims (the order is the sequence). A final outcome
    is never replaced: a revision is a new entry with `revision_of` and both are kept. PENDING and censored outcomes carry no
    label and are never scored (P05, P37).
  - Prospective outcomes come from the frozen labels-1 functions (`labels.build`, `labels.classify`), unchanged; nothing here
    feeds `labels.training_labels` (P43).
  - Drift monitors D1 to D8 with the thresholds frozen in the checklist (rule 9) and the response policy (rule 10): degrade,
    roll back or keep abstaining, never retrain automatically, never touch an earlier record (P39, P47).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from . import baselines as B
from . import contract as C
from . import labels as L
from . import stats as K

MONITORING_VERSION = "monitoring-1"
LEDGER_VERSION = "outcome-ledger-1"
GENESIS = "0" * 64
KINDS = ("PLAN", "PREDICTION_SET", "PREDICTION", "DOCUMENT", "OUTCOME", "MONITOR", "RESPONSE")
OUTCOME_STATES = ("LABELED", "PENDING", "NOT_READ", "THINNED", "MARKET_INACTIVE", "VENDOR_OR_ROUTE_GAP",
                  "UNVERIFIABLE_NO_VENDOR_HISTORY", "NO_SNAPSHOT_PRICE", "OUT_OF_SCOPE_CHAIN")
NON_FINAL = ("PENDING", "NOT_READ")
CENSORED = tuple(L.CENSORED)
CONSERVATIVE_LENS = {L.T1: 0, L.T1B: 0, L.T2: 1}      # censored counted T1 and T1b negative, T2 positive (ACCEPTANCE)

# ---------------------------------------------------------------- frozen monitor thresholds (checklist rule 9)
PSI_BINS = 10
PSI_FLOOR = 1e-4
PSI_WATCH = 0.10
PSI_ALERT = 0.25
MIN_FEATURE_VALUES = 30
MISSING_SHARE_ALERT = 0.20
MIN_LABELLED_FOR_RATE = 20
MIN_ROWS_FOR_CALIBRATION = 20
DRIFT = {"delta": 0.005, "threshold": 2.0, "min_obs": 30, "two_sided": False}   # registry THRESHOLDS[DRIFT_ALERT] (pinned by a test)
COVERAGE_DIFF_ALERT = 0.20
MIN_DECISIONS_FOR_COVERAGE = 20
SOURCE_MAX_AGE_S = 36 * 3600
READ_FAILURE_SHARE_ALERT = 0.20
REGIME_UNSEEN_SHARE_ALERT = 0.5
STATES = ("OK", "WATCH", "DRIFT_ALERT", "INSUFFICIENT_DATA", "SOURCE_PROBLEM")
STATUS_CODES = ("SUPPORT_BELOW_MINIMUM", "SOURCE_STALE", "SOURCE_FAILURE", "COLLECTOR_NOT_DEPLOYED", "MODEL_STALE")
ACTIONS = ("DEGRADE_TO_SHADOW", "ROLLBACK_TO_ABSTAIN", "KEEP_ABSTAIN", "KEEP_ABSTAIN_SOURCE", "NO_CHANGE")
TRADING = ("buy", "sell", "long", "short", "entry", "exit now", "moon", "pump", "guaranteed", "signal", "target hit",
           "take profit", "stop loss", "price target", "position size", "all in", "ape in", "accumulate", "profit")


class LedgerError(ValueError):
    """A ledger operation was refused; `code` names the rule."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


class LedgerTampered(LedgerError):
    def __init__(self, detail: str):
        super().__init__("LEDGER_TAMPERED", detail)


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _iso(t: float) -> str:
    return L._iso(t)


def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


# ---------------------------------------------------------------- the ledger: chain
def seal(payload: dict, *, seq: int, prev: str) -> dict:
    if payload.get("kind") not in KINDS:
        raise LedgerError("UNKNOWN_KIND", str(payload.get("kind")))
    body = {"ledger_version": LEDGER_VERSION, "seq": int(seq), "prev": prev, "payload": payload}
    return dict(body, sha=sha(body))


def read_ledger(text: str) -> list[dict]:
    """Every entry, after checking the chain from genesis: consecutive sequence numbers, each `prev` equal to the previous
    entry's `sha`, each `sha` recomputed. Any difference is LEDGER_TAMPERED (a changed, removed, inserted or reordered line)."""
    out, prev = [], GENESIS
    for i, line in enumerate(x for x in text.split("\n") if x.strip()):
        try:
            e = json.loads(line)
        except ValueError as err:
            raise LedgerTampered(f"line {i}: not JSON ({err})") from err
        if not isinstance(e, dict) or set(e) != {"ledger_version", "seq", "prev", "payload", "sha"}:
            raise LedgerTampered(f"line {i}: not an {LEDGER_VERSION} entry")
        if e["ledger_version"] != LEDGER_VERSION or e["seq"] != i or e["prev"] != prev:
            raise LedgerTampered(f"line {i}: sequence or chain broken")
        body = {k: e[k] for k in ("ledger_version", "seq", "prev", "payload")}
        if sha(body) != e["sha"] or canon(e) != line.strip():
            raise LedgerTampered(f"line {i}: content differs from its sha256")
        out.append(e)
        prev = e["sha"]
    return out


def head_sha(entries: Sequence[dict]) -> str:
    return entries[-1]["sha"] if entries else GENESIS


def is_append_only(old_text: str, new_text: str) -> bool:
    """True when the new text keeps every old line unchanged at its place and both chains verify."""
    try:
        read_ledger(old_text)
        read_ledger(new_text)
    except LedgerTampered:
        return False
    return new_text.startswith(old_text)


# ---------------------------------------------------------------- the ledger: rules (checklist rule 4)
def _pair(p: dict) -> tuple[str, str]:
    return (p["decision_key"], p["target"])


class Index:
    """What the ledger holds so far, for the append rules."""

    def __init__(self, entries: Sequence[dict] = ()):
        self.entries: list[dict] = []
        self.ids: dict[str, dict] = {}
        self.outcome_pairs: dict[tuple[str, str], list[dict]] = {}
        self.decisions: dict[str, dict] = {}          # decision_key -> {"chain", "mint", "decision_time", "set_id"}
        self.sets: set[str] = set()
        for e in entries:
            self.add(e["payload"])
            self.entries.append(e)

    def add(self, p: dict) -> None:
        k = p["kind"]
        if k == "PREDICTION_SET":
            self.sets.add(p["set_id"])
            for d in p["decisions"]:
                self.decisions.setdefault(d["decision_key"], dict(d, set_id=p["set_id"]))
        if k in ("PREDICTION", "DOCUMENT"):
            self.ids[_id_of(p)] = p
        if k == "OUTCOME":
            self.ids[p["outcome_id"]] = p
            self.outcome_pairs.setdefault(_pair(p), []).append(p)

    def current(self, pair: tuple[str, str]) -> dict | None:
        xs = self.outcome_pairs.get(pair) or []
        return xs[-1] if xs else None


def _id_of(p: dict) -> str:
    return p["prediction_id"] if p["kind"] == "PREDICTION" else p["forecast_id"] if p["kind"] == "DOCUMENT" else p.get("outcome_id")


PREDICTION_FIELDS = ("prediction_id", "set_id", "decision_key", "chain", "mint", "decision_time", "target", "candidate", "number",
                     "why", "card_file_sha256", "model_sha", "training_cutoff_utc", "label_matures_at", "published", "role")
DOCUMENT_FIELDS = ("forecast_id", "record_id", "set_id", "decision_key", "chain", "mint", "decision_time", "target",
                   "prediction_status", "reasons", "document_sha256", "record_sha256", "row_sha256", "published")
OUTCOME_FIELDS = ("outcome_id", "decision_key", "chain", "mint", "decision_time", "target", "target_version", "labels_version",
                  "registry_sha", "state", "label", "label_class", "censored", "eligibility", "flags", "label_matures_at",
                  "label_observed_at", "response_key", "request_url", "body_sha256", "detail", "supersedes", "revision_of",
                  "revision_reason", "recorded_at", "conservative_lens")


def check_payload(idx: Index, p: dict) -> str:
    """'APPEND' or 'DUPLICATE' (identical content already present); raises LedgerError with the rule's code otherwise."""
    k = p.get("kind")
    if k not in KINDS:
        raise LedgerError("UNKNOWN_KIND", str(k))
    if k in ("PREDICTION", "DOCUMENT"):
        need = PREDICTION_FIELDS if k == "PREDICTION" else DOCUMENT_FIELDS
        miss = [f for f in need if f not in p]
        if miss:
            raise LedgerError("MALFORMED_ENTRY", f"{k} lacks {miss}")
        pid = _id_of(p)
        if pid in idx.ids:
            if canon(idx.ids[pid]) == canon(p):
                return "DUPLICATE"
            raise LedgerError("PREDICTION_EDIT_REFUSED", f"{pid[:16]} exists with other content (never rewritten)")
        if p["set_id"] not in idx.sets:
            raise LedgerError("NO_PREDICTION_SET", f"{k} names set {str(p['set_id'])[:12]} not in the ledger")
        if idx.outcome_pairs.get(_pair(p)):
            raise LedgerError("LATE_PREDICTION_REFUSED", f"{k} for {p['decision_key'][:12]} {p['target']} after its outcome")
        d = idx.decisions.get(p["decision_key"])
        if d is None or d["chain"] != p["chain"] or d["mint"] != p["mint"] or float(d["decision_time"]) != float(p["decision_time"]):
            raise LedgerError("IDENTITY_MISMATCH", "decision key, chain, mint and time must equal the prediction set's (P01)")
        if k == "PREDICTION":
            if p["published"] is not False:
                raise LedgerError("MALFORMED_ENTRY", "a research prediction is never published")
            if p["number"] is not None and not (_fin(p["number"]) and 0.0 <= float(p["number"]) <= 1.0):
                raise LedgerError("MALFORMED_ENTRY", "a number is finite and in [0, 1] or null (P38)")
            if p["number"] is None and not p["why"]:
                raise LedgerError("MALFORMED_ENTRY", "an abstaining prediction names its reason")
        return "APPEND"
    if k == "OUTCOME":
        miss = [f for f in OUTCOME_FIELDS if f not in p]
        if miss:
            raise LedgerError("MALFORMED_ENTRY", f"OUTCOME lacks {miss}")
        if p["outcome_id"] in idx.ids:
            if canon(idx.ids[p["outcome_id"]]) == canon(p):
                return "DUPLICATE"
            raise LedgerError("OUTCOME_EDIT_REFUSED", "an outcome id is written once")
        d = idx.decisions.get(p["decision_key"])
        if d is None:
            raise LedgerError("OUTCOME_WITHOUT_PREDICTION", f"{p['decision_key'][:12]} is in no prediction set")
        if d["chain"] != p["chain"] or d["mint"] != p["mint"] or float(d["decision_time"]) != float(p["decision_time"]):
            raise LedgerError("IDENTITY_MISMATCH", "chain, mint and decision time must equal the prediction set's (P01)")
        if p["target"] not in L.TARGETS:
            raise LedgerError("MALFORMED_ENTRY", "unknown target")
        if p["state"] not in OUTCOME_STATES:
            raise LedgerError("MALFORMED_ENTRY", f"state {p['state']}")
        mat = C.label_matures_at(p["target"], float(p["decision_time"]))
        if abs(float(p["label_matures_at"]) - mat) > 1e-6:
            raise LedgerError("MATURITY_MISMATCH", "label_matures_at differs from the frozen registry")
        cen = 1 if p["state"] in CENSORED else 0
        if int(p["censored"]) != cen:
            raise LedgerError("MALFORMED_ENTRY", "censored bit must follow the state")
        if p["state"] == "LABELED":
            if p["label"] not in (0, 1) or not p["label_class"]:
                raise LedgerError("MALFORMED_ENTRY", "a LABELED outcome carries a label 0 or 1 and its class")
            if not _fin(p["label_observed_at"]) or float(p["label_observed_at"]) < mat or float(p["recorded_at"]) < mat:
                raise LedgerError("NOT_YET_MATURED", "a label read or recorded before label_matures_at is PENDING (P05)")
            if not (p["response_key"] and p["request_url"] and p["body_sha256"]):
                raise LedgerError("MALFORMED_ENTRY", "a LABELED outcome names its read (url, response key, body sha256)")
            if "token=" + p["mint"] not in p["request_url"]:
                raise LedgerError("IDENTITY_MISMATCH", "the label read must carry token=<mint> (PI-D-038)")
        elif p["label"] is not None or p["label_class"] is not None:
            raise LedgerError("MALFORMED_ENTRY", "only a LABELED outcome carries a label (P05, P37)")
        cur = idx.current(_pair(p))
        if cur is None:
            if p["supersedes"] or p["revision_of"]:
                raise LedgerError("MALFORMED_ENTRY", "the first outcome of a pair supersedes nothing")
        elif cur["state"] in NON_FINAL:
            if p["supersedes"] != cur["outcome_id"]:
                raise LedgerError("SUPERSEDE_REQUIRED", "a PENDING or NOT_READ outcome is superseded by naming it")
        else:
            if p["revision_of"] != cur["outcome_id"] or not p["revision_reason"]:
                raise LedgerError("FINAL_OUTCOME_REPLACED", "a final outcome is revised only with revision_of and a reason")
        return "APPEND"
    if k == "PREDICTION_SET":
        if not p.get("set_id") or not isinstance(p.get("decisions"), list) or not p.get("sha256"):
            raise LedgerError("MALFORMED_ENTRY", "PREDICTION_SET needs set_id, decisions and the file sha256")
        if p["set_id"] in idx.sets:
            raise LedgerError("PREDICTION_EDIT_REFUSED", "a prediction set is written once")
        for d in p["decisions"]:
            o = idx.decisions.get(d["decision_key"])
            if o is not None and (o["chain"], o["mint"], float(o["decision_time"])) != (d["chain"], d["mint"], float(d["decision_time"])):
                raise LedgerError("IDENTITY_MISMATCH", "a decision key reused with another identity")
            if any(idx.outcome_pairs.get((d["decision_key"], t)) for t in L.TARGETS):
                raise LedgerError("LATE_PREDICTION_REFUSED", "a prediction set after an outcome of its decision")
    return "APPEND"


def append(path: str | Path, payloads: Sequence[dict], *, expect_sha: str | None = None) -> dict:
    """Validate every payload against the ledger so far (and the earlier payloads of this call), then append the new lines.
    `expect_sha` is the head sha the caller last saw: another writer in between refuses the call (CONCURRENT_WRITE)."""
    p = Path(path)
    old = p.read_text() if p.exists() else ""
    entries = read_ledger(old)
    if expect_sha is not None and head_sha(entries) != expect_sha:
        raise LedgerError("CONCURRENT_WRITE", "the ledger head changed since it was read")
    idx = Index(entries)
    new, dup = [], 0
    prev, seq = head_sha(entries), len(entries)
    for pl in payloads:
        st = check_payload(idx, pl)
        if st == "DUPLICATE":
            dup += 1
            continue
        e = seal(pl, seq=seq, prev=prev)
        idx.add(pl)
        idx.entries.append(e)
        new.append(e)
        prev, seq = e["sha"], seq + 1
    if new:
        with open(p, "a") as f:
            for e in new:
                f.write(canon(e) + "\n")
    return {"appended": len(new), "duplicates": dup, "head": prev, "entries": seq}


def load(path: str | Path) -> Index:
    """The ledger's index after checking the chain and replaying every append rule: a ledger written around `append` (a valid
    chain holding an entry the rules refuse) is refused here too, so nothing downstream reads it."""
    p = Path(path)
    idx = Index()
    for e in read_ledger(p.read_text() if p.exists() else ""):
        if check_payload(idx, e["payload"]) == "DUPLICATE":
            raise LedgerError("DUPLICATE_ENTRY", f"seq {e['seq']}")
        idx.add(e["payload"])
        idx.entries.append(e)
    return idx


def verify(path: str | Path) -> dict:
    """Recheck the chain and replay every append rule from the start (a ledger written around `append` is caught too)."""
    p = Path(path)
    try:
        entries = read_ledger(p.read_text() if p.exists() else "")
    except LedgerTampered as e:
        return {"ok": False, "problems": [str(e)], "entries": None}
    idx, probs = Index(), []
    for e in entries:
        try:
            if check_payload(idx, e["payload"]) == "DUPLICATE":
                probs.append(f"seq {e['seq']}: duplicate entry")
        except LedgerError as err:
            probs.append(f"seq {e['seq']}: {err}")
        idx.add(e["payload"])
    return {"ok": not probs, "problems": probs, "entries": len(entries), "head": head_sha(entries)}


# ---------------------------------------------------------------- reading the ledger
def current_outcomes(idx: Index) -> dict[tuple[str, str], dict]:
    out = {}
    for pair, xs in idx.outcome_pairs.items():
        cur = dict(xs[-1])
        if any(x.get("revision_of") for x in xs):
            cur["flags"] = sorted(set(cur.get("flags") or []) | {"REVISED"})
        out[pair] = cur
    return out


def scorable(idx: Index, as_of: float) -> list[dict]:
    """The current outcomes that may be scored as of `as_of`: LABELED, uncensored, label 0 or 1, matured and observed at or after
    maturity, recorded by `as_of`. PENDING, NOT_READ, censored and ineligible outcomes are never scored (P05, P37)."""
    out = []
    for pair, o in sorted(current_outcomes(idx).items()):
        if o["state"] != "LABELED" or int(o["censored"]) or o["label"] not in (0, 1):
            continue
        mat = C.label_matures_at(o["target"], float(o["decision_time"]))
        if mat > as_of or float(o["recorded_at"]) > as_of or float(o["label_observed_at"]) < mat:
            continue
        out.append(o)
    return out


def predictions(idx: Index) -> dict[tuple[str, str, str], dict]:
    return {(p["decision_key"], p["target"], p["candidate"]): p for p in idx.ids.values() if p["kind"] == "PREDICTION"}


def documents(idx: Index) -> dict[tuple[str, str], dict]:
    return {_pair(p): p for p in idx.ids.values() if p["kind"] == "DOCUMENT"}


# ---------------------------------------------------------------- prospective outcomes through labels-1 (checklist rule 5)
def prospective_records(u: L.Universe) -> list[dict]:
    """labels.build on the universe, then for the prospective split the same steps build applies to development and holdout
    decisions: a kept, eligible, read decision is PENDING when its read came before maturity, else labels.classify (with the
    P0 ratio flag of build); a decision without any pool is VENDOR_OR_ROUTE_GAP once matured (no point-in-time pool and an empty
    or failed vendor list), else PENDING; an unread decision is PENDING before maturity and NOT_READ after."""
    recs, _ = L.build(u)
    out = []
    for rec in recs:
        if rec["split"] != "PROSPECTIVE":
            continue
        d, k, t = rec["decision"], rec["decision_key"], rec["target"]
        if rec["state"] == "PROSPECTIVE":
            mature = u.as_of >= rec["label_matures_at"]
            if rec["eligibility"] == "NOT_READ":
                if not d.get("pool"):
                    rec["eligibility"] = "VENDOR_OR_ROUTE_GAP"
                    rec["state"] = "VENDOR_OR_ROUTE_GAP" if mature else "PENDING"
                else:
                    rec["state"] = "NOT_READ" if mature else "PENDING"
            else:
                rd = u.read_of[k]
                if rd.retrieved_at < rec["label_matures_at"]:
                    rec["state"] = "PENDING"
                else:
                    rec.update(L.classify(t, d["decision_time"], rd, u.other_reads.get(k) if t == L.T2 else None))
                    sp = L.snapshot_price(d)
                    if rec.get("p0") and sp and not (L.P0_SNAPSHOT_RATIO[0] <= rec["p0"] / sp <= L.P0_SNAPSHOT_RATIO[1]):
                        rec["flags"] = list(rec.get("flags") or []) + ["P0_FAR_FROM_SNAPSHOT_PRICE"]
        rec["censored"] = 1 if rec["state"] in CENSORED else 0
        out.append(rec)
    return out


def outcome_payload(rec: dict, *, recorded_at: float, supersedes: str | None = None, revision_of: str | None = None,
                    revision_reason: str | None = None) -> dict:
    """The OUTCOME entry of one prospective label record (a NEEDS_OTHER_POOLS record is refused: fetch the other pools first)."""
    if rec["state"] == L.NEEDS_OTHER_POOLS:
        raise LedgerError("NEEDS_OTHER_POOLS", "a T2 halt candidate needs its other pools before it has an outcome")
    d, rd = rec["decision"], rec.get("read")
    lab = rec["state"] == "LABELED"
    flags = sorted(set(rec.get("flags") or []) | ({"KEY_CONFLICT"} if "KEY_CONFLICT" in (d.get("flags") or []) else set())
                   | ({"CURRENT_VENDOR_LIST"} if d.get("route") == "CURRENT_VENDOR_LIST" else set()))
    p = {"kind": "OUTCOME", "decision_key": rec["decision_key"], "chain": d["chain"], "mint": d["mint"],
         "decision_time": float(d["decision_time"]), "target": rec["target"], "target_version": rec["target_version"],
         "labels_version": L.LABELS_VERSION, "registry_sha": C.registry_sha256(), "state": rec["state"],
         "label": rec.get("label") if lab else None, "label_class": rec.get("label_class") if lab else None,
         "censored": int(rec["censored"]), "eligibility": rec["eligibility"], "flags": flags,
         "label_matures_at": float(rec["label_matures_at"]),
         "label_observed_at": float(rd.retrieved_at) if (rd is not None and lab) else None,
         "response_key": rd.response_key if (rd is not None and lab) else None,
         "request_url": rd.url if (rd is not None and lab) else None,
         "body_sha256": rd.body_sha256 if (rd is not None and lab) else None,
         "detail": rec.get("detail") or (rec.get("thinned_by")[:16] if rec.get("thinned_by") else None),
         "supersedes": supersedes, "revision_of": revision_of, "revision_reason": revision_reason, "recorded_at": float(recorded_at),
         "conservative_lens": (CONSERVATIVE_LENS[rec["target"]] if rec["censored"] else (rec.get("label") if lab else None))}
    p["outcome_id"] = "oc_" + sha({k: v for k, v in p.items() if k != "recorded_at"})[:40]
    return p


def next_outcomes(idx: Index, recs: Sequence[dict], *, recorded_at: float, reason: str = "LATER_READ") -> list[dict]:
    """OUTCOME payloads for records whose state or class differs from the pair's current outcome: the first outcome of a pair,
    a PENDING or NOT_READ outcome superseded, or a final outcome revised (both kept). An unchanged pair gives nothing."""
    out = []
    for rec in recs:
        if rec["state"] == L.NEEDS_OTHER_POOLS:
            continue
        cur = idx.current((rec["decision_key"], rec["target"]))
        if cur is None:
            out.append(outcome_payload(rec, recorded_at=recorded_at))
            continue
        same = (cur["state"] == rec["state"] and cur["label_class"] == (rec.get("label_class") if rec["state"] == "LABELED" else None))
        if same:
            continue
        if cur["state"] in NON_FINAL:
            out.append(outcome_payload(rec, recorded_at=recorded_at, supersedes=cur["outcome_id"]))
        else:
            out.append(outcome_payload(rec, recorded_at=recorded_at, revision_of=cur["outcome_id"], revision_reason=reason))
    return out


# ---------------------------------------------------------------- drift monitors (checklist rule 9)
def _finite(xs: Iterable[Any]) -> np.ndarray:
    a = np.array([float(x) for x in xs if _fin(x)], float)
    return a


def psi(ref: Sequence[Any], cur: Sequence[Any], *, bins: int = PSI_BINS, floor: float = PSI_FLOOR) -> dict:
    """Population stability index of `cur` against `ref` on finite values. Categories when the reference has at most `bins`
    distinct values (each value a bin, plus one bin for values not seen), else quantile bins of the reference (ties merged).
    Empty shares are floored at `floor`."""
    r, c = _finite(ref), _finite(cur)
    if r.size == 0 or c.size == 0:
        return {"psi": None, "bins": 0, "kind": None}
    vals = np.unique(r)
    if vals.size <= bins:
        rs = np.array([np.mean(r == v) for v in vals] + [0.0])
        cs = np.array([np.mean(c == v) for v in vals] + [float(np.mean(~np.isin(c, vals)))])
        kind = "categorical"
    else:
        edges = np.unique(np.quantile(r, np.linspace(0, 1, bins + 1)))
        inner = edges[1:-1]
        rs = np.bincount(np.searchsorted(inner, r, side="right"), minlength=len(inner) + 1) / r.size
        cs = np.bincount(np.searchsorted(inner, c, side="right"), minlength=len(inner) + 1) / c.size
        kind = "quantile"
    rs, cs = np.maximum(rs, floor), np.maximum(cs, floor)
    return {"psi": float(np.sum((cs - rs) * np.log(cs / rs))), "bins": int(rs.size), "kind": kind}


def _worst(states: Iterable[str]) -> str:
    order = {"DRIFT_ALERT": 3, "WATCH": 2, "OK": 1, "INSUFFICIENT_DATA": 0}
    ss = [s for s in states if s in order]
    if not ss:
        return "INSUFFICIENT_DATA"
    if any(s == "DRIFT_ALERT" for s in ss):
        return "DRIFT_ALERT"
    if any(s == "WATCH" for s in ss):
        return "WATCH"
    if any(s == "OK" for s in ss):
        return "OK"
    return "INSUFFICIENT_DATA"


def feature_drift(ref: dict[str, Sequence[Any]], cur: dict[str, Sequence[Any]]) -> dict:
    """D1: PSI and missingness per column (the reference and current lists hold one value per row, None or NaN for missing)."""
    cols = {}
    for name in sorted(ref):
        rv, cv = list(ref[name]), list(cur.get(name, []))
        rf, cf = _finite(rv), _finite(cv)
        miss_r = 1 - rf.size / len(rv) if rv else None
        miss_c = 1 - cf.size / len(cv) if cv else None
        row = {"n_ref": len(rv), "n_cur": len(cv), "finite_ref": int(rf.size), "finite_cur": int(cf.size),
               "missing_share_ref": miss_r, "missing_share_cur": miss_c}
        states = []
        if cv and miss_r is not None and miss_c - miss_r > MISSING_SHARE_ALERT:
            row["missing_state"] = "DRIFT_ALERT"
            states.append("DRIFT_ALERT")
        else:
            row["missing_state"] = "OK" if cv else "INSUFFICIENT_DATA"
        if cf.size < MIN_FEATURE_VALUES:
            row.update(psi=None, psi_state="INSUFFICIENT_DATA", detail=f"{cf.size} finite values, fewer than {MIN_FEATURE_VALUES}")
            states.append("INSUFFICIENT_DATA")
        else:
            pr = psi(rv, cv)
            st = "DRIFT_ALERT" if pr["psi"] >= PSI_ALERT else "WATCH" if pr["psi"] >= PSI_WATCH else "OK"
            row.update(psi=pr["psi"], psi_bins=pr["bins"], psi_kind=pr["kind"], psi_state=st)
            states.append(st)
        row["state"] = _worst(states)
        cols[name] = row
    return {"monitor": "D1_FEATURE_DRIFT", "columns": cols, "state": _worst(r["state"] for r in cols.values())}


def label_rate_drift(train_prevalence: float, y: Sequence[int]) -> dict:
    """D2: the training prevalence outside the Wilson 95% interval of the observed rate is DRIFT_ALERT."""
    n, k = len(y), int(sum(y))
    out = {"monitor": "D2_LABEL_RATE", "n": n, "positives": k, "training_prevalence": float(train_prevalence)}
    if n < MIN_LABELLED_FOR_RATE:
        return out | {"state": "INSUFFICIENT_DATA", "rate": (k / n) if n else None,
                      "detail": f"{n} labelled events, fewer than {MIN_LABELLED_FOR_RATE}"}
    lo, hi = K.wilson(k, n)
    st = "OK" if lo <= train_prevalence <= hi else "DRIFT_ALERT"
    return out | {"state": st, "rate": k / n, "wilson": [lo, hi]}


def calibration_drift(y: Sequence[int], p: Sequence[float], name: str) -> dict:
    """D3a: the frozen calibration check on the prospective rows; a failure in the large or in a bin is DRIFT_ALERT."""
    pairs = [(int(a), float(b)) for a, b in zip(y, p) if _fin(b)]
    out = {"monitor": "D3_CALIBRATION", "model": name, "n": len(pairs)}
    if len(pairs) < MIN_ROWS_FOR_CALIBRATION:
        return out | {"state": "INSUFFICIENT_DATA", "detail": f"{len(pairs)} rows with a number, fewer than {MIN_ROWS_FOR_CALIBRATION}"}
    cal = C.ACCEPTANCE["calibration"]
    res = K.calibration_bins([a for a, _ in pairs], [b for _, b in pairs], min_bin=cal["min_bin_events"], max_bins=cal["max_bins"],
                             in_the_large_only_below=cal["in_the_large_only_below_events"])
    ok = res["in_the_large_ok"] and res["every_bin_ok"] in (True, None)
    return out | {"state": "OK" if ok else "DRIFT_ALERT", "calibration": res}


def page_hinkley_alarms(stream: Sequence[tuple[float, float]]) -> dict:
    """D3b: Page-Hinkley with the registry's frozen settings over (time the loss difference became known, model loss minus
    reference loss) in time order; alarm times are DRIFT_ALERT. A NaN raises (P38)."""
    out = {"monitor": "D3_PAGE_HINKLEY", "n": len(stream), "settings": dict(DRIFT)}
    if len(stream) < DRIFT["min_obs"]:
        return out | {"state": "INSUFFICIENT_DATA", "alarms": [], "detail": f"{len(stream)} matured pairs, fewer than {DRIFT['min_obs']}"}
    ph = K.PageHinkley(delta=DRIFT["delta"], threshold=DRIFT["threshold"], min_obs=DRIFT["min_obs"], two_sided=DRIFT["two_sided"])
    al = [float(t) for t, v in sorted(stream, key=lambda tv: tv[0]) if ph.update(float(v))]
    return out | {"state": "DRIFT_ALERT" if al else "OK", "alarms": al}


def coverage_drift(cur_with_number: int, cur_total: int, ref_with_number: int, ref_total: int) -> dict:
    """D4: the share of decisions that get a number, against the reference share."""
    out = {"monitor": "D4_PREDICTION_RATE", "cur": [cur_with_number, cur_total], "ref": [ref_with_number, ref_total]}
    if cur_total < MIN_DECISIONS_FOR_COVERAGE or ref_total == 0:
        return out | {"state": "INSUFFICIENT_DATA", "detail": f"{cur_total} decisions, fewer than {MIN_DECISIONS_FOR_COVERAGE}"}
    a, b = cur_with_number / cur_total, ref_with_number / ref_total
    return out | {"state": "DRIFT_ALERT" if abs(a - b) > COVERAGE_DIFF_ALERT else "OK", "coverage": a, "ref_coverage": b,
                  "difference": a - b}


def support_state(n: int, k: int) -> dict:
    """D5: the frozen out-of-sample minimums; below them the target keeps abstaining (a status, not an alarm)."""
    gate = B.evaluation_gate(int(n), int(k))
    return {"monitor": "D5_SUPPORT", "n": int(n), "positives": int(k), "negatives": int(n) - int(k),
            "minimums": [C.ACCEPTANCE["min_holdout_events"], C.ACCEPTANCE["min_holdout_per_class"]],
            "state": "SUPPORT_BELOW_MINIMUM" if gate else "OK"}


def source_state(*, newest_export_time: float | None, now: float, reads_total: int, reads_failed: int, depth_rows: int) -> dict:
    """D6 (P47): stale exports, failing label reads and the forward depth collector, as visible status codes. A source problem is
    not a model drift: its state is SOURCE_PROBLEM and the response keeps abstaining with the status (never a rollback)."""
    codes = []
    age = None if newest_export_time is None else float(now) - float(newest_export_time)
    if age is None or age > SOURCE_MAX_AGE_S:
        codes.append("SOURCE_STALE")
    share = (reads_failed / reads_total) if reads_total else None
    if share is not None and share > READ_FAILURE_SHARE_ALERT:
        codes.append("SOURCE_FAILURE")
    if depth_rows == 0:
        codes.append("COLLECTOR_NOT_DEPLOYED")
    return {"monitor": "D6_SOURCES", "export_age_s": age, "reads_total": reads_total, "reads_failed": reads_failed,
            "read_failure_share": share, "depth_rows": depth_rows, "codes": codes,
            "state": "SOURCE_PROBLEM" if ({"SOURCE_STALE", "SOURCE_FAILURE"} & set(codes)) else "OK"}


def regime_drift(cur: Sequence[str | None], ref: Sequence[str | None]) -> dict:
    """D7: share of current decisions whose regime label never occurs in the reference (WARMUP and unknown counted apart)."""
    known_ref = {x for x in ref if x and x not in ("WARMUP", "UNKNOWN")}
    cur_known = [x for x in cur if x and x not in ("WARMUP", "UNKNOWN")]
    out = {"monitor": "D7_REGIME", "n": len(cur), "warmup_or_unknown": len(cur) - len(cur_known),
           "reference_labels": sorted(known_ref), "current_labels": sorted(set(cur_known))}
    if not cur_known or not known_ref:
        return out | {"state": "INSUFFICIENT_DATA", "unseen_share": None}
    unseen = sum(1 for x in cur_known if x not in known_ref) / len(cur_known)
    return out | {"state": "DRIFT_ALERT" if unseen > REGIME_UNSEEN_SHARE_ALERT else "OK", "unseen_share": unseen}


def model_age(now: float, cutoff: float, decision_times: Sequence[float] = ()) -> dict:
    """D8: days until the frozen cards become MODEL_STALE, and the decisions past that point."""
    stale_at = float(cutoff) + float(C.ACCEPTANCE["max_model_age_s"])
    late = [t for t in decision_times if float(t) - float(cutoff) > C.ACCEPTANCE["max_model_age_s"]]
    return {"monitor": "D8_MODEL_AGE", "stale_after_utc": _iso(stale_at), "days_left": (stale_at - float(now)) / 86400.0,
            "decisions_past_stale": len(late), "state": "MODEL_STALE" if late or now > stale_at else "OK"}


def minority_note(y: Sequence[int], p: Sequence[float]) -> dict:
    """P10: prevalence beside the score; AUC and average precision only with 10 events per class; a constant prediction flagged."""
    pairs = [(int(a), float(b)) for a, b in zip(y, p) if _fin(b)]
    n = len(pairs)
    k = sum(a for a, _ in pairs)
    mpc = C.ACCEPTANCE["secondary_scores"]["auc_and_average_precision_min_per_class"]
    pp = np.array([b for _, b in pairs], float)
    out = {"n": n, "positives": k, "prevalence": (k / n) if n else None,
           "constant_prediction": bool(n and np.ptp(pp) == 0), "flags": []}
    if out["constant_prediction"]:
        out["flags"].append("CONSTANT_PREDICTION")
    if n and k >= mpc and n - k >= mpc and np.ptp(pp) > 0:
        yy = [a for a, _ in pairs]
        out["auc"], out["average_precision"] = K.roc_auc(yy, pp), K.average_precision(yy, pp)
    else:
        out["auc"] = out["average_precision"] = None
        out["flags"].append(f"FEWER_THAN_{mpc}_PER_CLASS_OR_CONSTANT")
    return out


# ---------------------------------------------------------------- response and notices (checklist rule 10)
def target_states(monitors: Sequence[dict]) -> list[str]:
    st = []
    for m in monitors:
        if m.get("state") == "DRIFT_ALERT":
            st.append("DRIFT_ALERT")
        if m.get("state") in STATUS_CODES:
            st.append(m["state"])
        for c in m.get("codes") or []:
            if c in STATUS_CODES:
                st.append(c)
    return sorted(set(st))


def response(states: Sequence[str], *, pin_mode: str, level: str | None) -> dict:
    """The frozen action for one target (never a retrain): a champion that drifted or went stale is demoted or rolled back;
    with no champion the abstention is kept; a source problem keeps abstaining with a visible status."""
    s = set(states)
    model_problem = bool({"DRIFT_ALERT", "MODEL_STALE"} & s)
    source_problem = bool({"SOURCE_STALE", "SOURCE_FAILURE"} & s)
    if pin_mode == "CHAMPION" and model_problem:
        act = "DEGRADE_TO_SHADOW" if level == "VALIDATED_EXPERIMENTAL" else "ROLLBACK_TO_ABSTAIN"
    elif source_problem:
        act = "KEEP_ABSTAIN_SOURCE"
    elif pin_mode == "CHAMPION":
        act = "NO_CHANGE"
    else:
        act = "KEEP_ABSTAIN"
    return {"states": sorted(s), "pin_mode": pin_mode, "level": level, "action": act, "automatic_retrain": False,
            "earlier_records": "UNCHANGED", "retrain": "a plan committed before its evaluation data and a human-reviewed registry "
                                                      "promotion (PI-D-091); never automatic"}


def plain_ok(text: str) -> bool:
    low = text.lower()
    return not any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in TRADING)


def notice(target_words: str, states: Sequence[str], act: dict, facts: Sequence[str]) -> str:
    """A short, non-alarmist notice: what moved, on how many events, what the system does, what a person may review."""
    what = ", ".join(states) if states else "no monitor state above OK"
    doing = {"DEGRADE_TO_SHADOW": "the model is shown as research only (shadow) and keeps every earlier record",
             "ROLLBACK_TO_ABSTAIN": "the model is rolled back to the previous usable pin or to abstention; earlier records stay",
             "KEEP_ABSTAIN": "the system keeps abstaining for this target; earlier records stay",
             "KEEP_ABSTAIN_SOURCE": "the system keeps abstaining and shows the source status; earlier research stays",
             "NO_CHANGE": "nothing changes"}[act["action"]]
    txt = (f"{target_words}: {what}. " + ("; ".join(facts) + ". " if facts else "") + f"Action: {doing}. "
           "No model is retrained automatically; a person may review the monitor report and decide on a retrain plan.")
    if not plain_ok(txt):
        raise ValueError("notice text would carry a trading word")
    return txt


# ---------------------------------------------------------------- misses (prompt item 5)
def misses(idx: Index, *, as_of: float) -> list[dict]:
    """One row per (decision, target) that has a document or a prediction: the document's status and reasons, the current outcome
    and why no score exists. Nothing is dropped: out-of-scope, ineligible, censored, thinned and pending rows are listed."""
    docs = documents(idx)
    cur = current_outcomes(idx)
    preds = predictions(idx)
    pairs = sorted(set(docs) | set(cur) | {(k[0], k[1]) for k in preds})
    out = []
    for pair in pairs:
        d, o = docs.get(pair), cur.get(pair)
        st = o["state"] if o else "NO_OUTCOME_ENTRY"
        if d is not None and d["prediction_status"] == "ABSTAIN":
            why = "ABSTAIN_NOT_SCORED"
        elif d is None:
            why = "NO_DOCUMENT"
        else:
            why = "FORECAST"
        if st == "LABELED" and o and float(o["label_matures_at"]) > as_of:
            st = "NOT_MATURED_AT_EVALUATION"
        ref = preds.get((pair[0], pair[1], "P07_B2"))
        out.append({"decision_key": pair[0], "target": pair[1], "chain": (d or o or ref or {}).get("chain"),
                    "mint": (d or o or ref or {}).get("mint"), "decision_time_utc": _iso((d or o or ref)["decision_time"]),
                    "document": d["forecast_id"] if d else None, "document_status": d["prediction_status"] if d else None,
                    "document_reasons": "|".join(d["reasons"]) if d else None, "outcome_state": st,
                    "label_class": o["label_class"] if o else None, "label": o["label"] if o else None,
                    "censored": o["censored"] if o else None, "flags": "|".join(o["flags"]) if o else None,
                    "no_score_reason": why if st == "LABELED" else st,
                    "reference_b2_has_number": (ref is not None and ref["number"] is not None)})
    return out

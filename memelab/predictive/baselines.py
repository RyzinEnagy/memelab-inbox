"""Phase 07: transparent baselines B0 to B4, negative controls and the frozen walk-forward evaluation (research only, flag OFF,
imported by no existing module). numpy and the standard library only; no network, no clock.

Spec: audits/predictive-intelligence/phase_07/models/BASELINE_SPEC.md. Pre-registration: phase_07/ACCEPTANCE_CHECKLIST.md and
phase_07/experiments/EXPERIMENT_REGISTRY.csv (committed before any fit). Rules enforced here:
  - training rows come only from `labels.training_labels` at the fold's cutoff (the caller passes `train_at`); the walk-forward
    index computed from the development labels must equal those rows (`WalkForwardMismatch`);
  - features come only from stored as-of snapshots joined by decision_key with chain, mint (byte for byte) and decision time
    equal (`IdentityJoinError`, P01); every model column is in the allowlist and passes `features.validate_rows` with its
    availability at or before the decision (P36, the future-feature trap NC2);
  - B1 to B4 are fitted only when the training rows reach the ACCEPTANCE minimums (100 events, 20 per class); otherwise they
    abstain with INSUFFICIENT_HISTORY; a row missing a required input abstains with OOD;
  - every fitted object is a JSON card read by numpy code (no pickle); its model_sha is the sha256 of the canonical card without
    the sha; a card whose content does not match its sha is refused (P46, MODEL_HASH_MISMATCH);
  - no number here is a published probability: publication needs holdout calibration (Phase 13) and a champion (Phase 16).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from . import contract as C
from . import features as F
from . import labels as L
from . import stats as K
from . import store as S

PHASE = "07"
PROVISIONAL = "PROVISIONAL_PENDING_REVISION_REREAD"     # PI-D-046
FIXTURE_FLAG = "NO_REAL_HISTORICAL_EVIDENCE"
BASELINES = ("B0", "B1", "B2", "B3", "B3F", "B4")       # forecasters; B4C is description only, NC1 a control
GATED = ("B1", "B2", "B3", "B3F", "B4")
M_SHRINK = 20.0
B4_FACTOR = 3.0
B4C_WINDOW_S = 43200.0
B4C_MIN_CONTROLS = 3
C_L2 = 1.0
STATUS_GROUPS = {
    "REJECTED": "REJECTED",
    "DISTRIBUTION RISK": "RISK_OR_UNRESOLVED", "OVEREXTENDED": "RISK_OR_UNRESOLVED", "THESIS DETERIORATING": "RISK_OR_UNRESOLVED",
    "THESIS INVALIDATED": "RISK_OR_UNRESOLVED", "RESEARCH REQUIRED": "RISK_OR_UNRESOLVED",
    "WATCH": "CONSTRUCTIVE", "SETUP DEVELOPING": "CONSTRUCTIVE", "NEAR ENTRY": "CONSTRUCTIVE", "ENTRY CONDITIONS MET": "CONSTRUCTIVE",
}
LIQ, MCAP, VOL, FATAL, AGE, SCORE = ("thesis_log1p_liquidity_usd", "thesis_log1p_mcap_usd", "thesis_log1p_vol_24h_usd",
                                      "thesis_fatal_present", "log1p_token_age_days", "thesis_score")
B2_REQUIRED = (LIQ, MCAP, VOL, FATAL)
B2_OPTIONAL = (AGE,)
B2_COLUMNS = B2_REQUIRED + B2_OPTIONAL
ALLOWED_COLUMNS = frozenset(B2_COLUMNS + (SCORE,))         # every column a Phase 07 baseline may read (NC2 allowlist)
SOURCE_OF = {LIQ: LIQ, MCAP: MCAP, VOL: VOL, FATAL: FATAL, SCORE: SCORE, AGE: "token_age_s"}


class BaselineError(ValueError):
    pass


class IdentityJoinError(BaselineError):
    """A label and a feature snapshot of different (chain, mint, decision time) were about to be joined (P01, NC3)."""


class WalkForwardMismatch(BaselineError):
    """The frozen day walk-forward and the training gate disagree about a fold's training rows."""


class ModelHashMismatch(BaselineError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def status_group(status: Any) -> str:
    return STATUS_GROUPS.get(status, "UNKNOWN") if isinstance(status, str) else "UNKNOWN"


# ---------------------------------------------------------------- examples: one labelled decision with its as-of inputs
@dataclass
class Example:
    decision_key: str
    chain: str
    mint: str
    decision_time: float
    label_matures_at: float
    y: int
    x: dict = field(default_factory=dict)          # model column -> float (NaN when missing)
    avail: dict = field(default_factory=dict)      # model column -> availability time
    status: str | None = None
    creator: str | None = None
    narrative: str | None = None
    route: str | None = None
    key_conflict: bool = False
    label_key: str | None = None
    snapshot_sha256: str | None = None
    cohort: dict = field(default_factory=dict)

    @property
    def day(self) -> str:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(self.decision_time, _dt.UTC).strftime("%Y-%m-%d")


def _num(v: Any) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else float("nan")


def model_inputs(frow: dict) -> tuple[dict, dict]:
    """Model columns and their availability from one `features.training_view` row. Token age in days, log1p; a negative age
    is missing (a first pool after the decision is inconsistent, not young)."""
    x, av = {}, {}
    for col in ALLOWED_COLUMNS:
        src = SOURCE_OF[col]
        v = _num(frow.get(src))
        if col == AGE:
            v = math.log1p(v / 86400.0) if math.isfinite(v) and v >= 0 else float("nan")
        x[col] = v
        av[col] = frow[src + "__available_at"]
    return x, av


def join(label_rows: Sequence[dict], feature_rows: dict[str, dict], *, decision_info: dict[str, dict] | None = None,
         snapshots: dict[str, str] | None = None) -> list[Example]:
    """Label rows of `labels.training_labels` joined to feature rows of `features.training_view` by decision_key, with chain,
    mint and decision time checked byte for byte (P01). A label without a feature row is an error, never a silent drop.
    `decision_info` gives, per decision_key, the decision row's own status and its token row's narrative_id (both inside the
    export commit that is the decision time, so known at the decision)."""
    out = []
    for r in label_rows:
        k = r["decision_key"]
        f = feature_rows.get(k)
        if f is None:
            raise BaselineError(f"label {str(r.get('label_key'))[:12]}: no stored feature snapshot for decision {k[:12]}")
        check_identity(r, f)
        x, av = model_inputs(f)
        groups = json.loads(r["groups_json"]) if isinstance(r.get("groups_json"), str) else (r.get("groups") or {})
        cohort = json.loads(r["cohort_json"]) if isinstance(r.get("cohort_json"), str) else (r.get("cohort") or {})
        flags = json.loads(r["flags_json"]) if isinstance(r.get("flags_json"), str) else list(r.get("flags") or [])
        info = (decision_info or {}).get(k, {})
        out.append(Example(decision_key=k, chain=r["chain"], mint=r["mint"], decision_time=float(r["decision_time"]),
                           label_matures_at=float(r["label_matures_at"]), y=int(r["label"]), x=x, avail=av,
                           status=info.get("status", cohort.get("status")), creator=groups.get("creator"),
                           narrative=info.get("narrative"), route=r.get("route"),
                           key_conflict="KEY_CONFLICT" in flags or bool(cohort.get("key_conflict")),
                           label_key=r.get("label_key"), snapshot_sha256=(snapshots or {}).get(k), cohort=cohort))
    return out


def check_identity(label_row: dict, feature_row: dict) -> None:
    for a, b in (("chain", "chain"), ("mint", "mint")):
        if not isinstance(label_row.get(a), str) or label_row.get(a) != feature_row.get(b):
            raise IdentityJoinError(f"{a} differs: label {label_row.get(a)!r} vs features {feature_row.get(b)!r} (P01)")
    if float(label_row["decision_time"]) != float(feature_row["decision_time"]):
        raise IdentityJoinError("decision time differs between the label and the feature snapshot (another decision of the mint)")
    if label_row["decision_key"] != feature_row["decision_key"]:
        raise IdentityJoinError("decision key differs")


def join_by_symbol(label_row: dict, feature_rows_by_symbol: dict[str, dict], symbol: str) -> Example:
    """The NC3 trap as code: a join keyed by ticker. Always ends in check_identity, which refuses another mint."""
    f = feature_rows_by_symbol[symbol]
    check_identity(label_row, f)
    x, av = model_inputs(f)
    return Example(label_row["decision_key"], label_row["chain"], label_row["mint"], float(label_row["decision_time"]),
                   float(label_row["label_matures_at"]), int(label_row["label"]), x, av)


def check_asof(examples: Sequence[Example], columns: Sequence[str], *, as_of: float | None, with_labels: bool) -> None:
    """Every column in the allowlist and available at or before its decision; decisions at or before as_of; labels matured by
    as_of when given (features.validate_rows, P36, P05, P43)."""
    bad = [c for c in columns if c not in ALLOWED_COLUMNS]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 07 allowlist (NC2: only declared as-of inputs reach a fit)")
    rows = []
    for e in examples:
        r = {"decision_time": e.decision_time}
        for c in columns:
            r[c] = e.x.get(c)
            r[c + "__available_at"] = e.avail.get(c)
        if with_labels:
            r["y"], r["label_matures_at"] = e.y, e.label_matures_at
        rows.append(r)
    cols = ["decision_time"] + list(columns) + [c + "__available_at" for c in columns] + (["y", "label_matures_at"] if with_labels else [])
    F.validate_rows(rows, columns=cols, availability=[c + "__available_at" for c in columns], as_of=as_of)


def matrix(examples: Sequence[Example], columns: Sequence[str]) -> np.ndarray:
    bad = [c for c in columns if c not in ALLOWED_COLUMNS]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the Phase 07 allowlist")
    return np.array([[e.x.get(c, float("nan")) for c in columns] for e in examples], dtype=float).reshape(len(examples), len(columns))


def labels_of(examples: Sequence[Example]) -> np.ndarray:
    return np.array([e.y for e in examples], dtype=float)


# ---------------------------------------------------------------- cards
def gate(n: int, k: int) -> str | None:
    a = C.ACCEPTANCE
    if n < a["min_train_events"] or k < a["min_train_per_class"] or n - k < a["min_train_per_class"]:
        return "INSUFFICIENT_HISTORY"
    return None


def _card(kind: str, target: str, train: Sequence[Example], cutoff: float, body: dict, *, n_used: int | None = None,
          k_used: int | None = None, meta: dict | None = None) -> dict:
    y = labels_of(train)
    card = {"phase": PHASE, "kind": kind, "model_id": f"{kind}:{target}", "targets": [target],
            "target_version": {target: C.TARGETS[target]["version"]}, "training_cutoff": float(cutoff),
            "training_cutoff_utc": _iso(cutoff), "registry_sha": C.registry_sha256(), "feature_set_sha": F.feature_set_sha(),
            "feature_version": F.FEATURE_VERSION, "labels_version": L.LABELS_VERSION, "store_schema": S.SCHEMA_VERSION,
            "label_store_migration": max(v for v, *_ in L.LABEL_MIGRATIONS), "label_mode": "provider",
            "n_train": int(len(train)), "k_train": int(y.sum()) if len(train) else 0,
            "n_used": int(len(train) if n_used is None else n_used), "k_used": int((y.sum() if len(train) else 0) if k_used is None else k_used),
            "label_set_sha": sha(sorted([e.label_key or e.decision_key, e.y] for e in train)),
            "data_snapshot_sha": sha(sorted([e.decision_key, e.snapshot_sha256] for e in train)),
            "status": PROVISIONAL, "revision_check_claimed": False, "publishable": False,
            "max_train_decision_time": max((e.decision_time for e in train), default=None),
            "max_train_label_matures_at": max((e.label_matures_at for e in train), default=None)}
    card.update(meta or {})
    card["body"] = body
    card["model_sha"] = sha({k: v for k, v in card.items() if k != "model_sha"})
    return card


def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_card(card: dict) -> dict:
    want = sha({k: v for k, v in card.items() if k != "model_sha"})
    if card.get("model_sha") != want:
        raise ModelHashMismatch(f"card {card.get('model_id')}: content does not match its model_sha (MODEL_HASH_MISMATCH)")
    if card.get("registry_sha") != C.registry_sha256():
        raise BaselineError("card trained under another registry fingerprint")
    F.require_compatible(card["feature_version"], card["feature_set_sha"])
    return card


def dumps(card: dict) -> str:
    return json.dumps(card, sort_keys=True, indent=1, allow_nan=False) + "\n"


def loads(text: str) -> dict:
    return verify_card(json.loads(text))


def _prevalence(train: Sequence[Example]) -> float:
    y = labels_of(train)
    if len(y) == 0:
        raise BaselineError("B0 needs at least one training label")
    return float(y.mean())


def _shrunk(groups: dict[str, list[int]], b0: float) -> dict:
    return {g: {"n": len(v), "k": int(sum(v)), "p": (sum(v) + M_SHRINK * b0) / (len(v) + M_SHRINK)} for g, v in sorted(groups.items())}


def fit_b0(target: str, train: Sequence[Example], cutoff: float) -> dict:
    return _card("B0", target, train, cutoff, {"p": _prevalence(train)})


def fit_b1(target: str, train: Sequence[Example], cutoff: float) -> dict:
    g = gate(len(train), int(labels_of(train).sum()))
    if g:
        return _card("B1", target, train, cutoff, {"abstain": g})
    b0 = _prevalence(train)
    groups: dict[str, list[int]] = {}
    for e in train:
        groups.setdefault(status_group(e.status), []).append(e.y)
    return _card("B1", target, train, cutoff, {"b0": b0, "m": M_SHRINK, "groups": _shrunk(groups, b0), "status_groups": STATUS_GROUPS})


def fit_b3f(target: str, train: Sequence[Example], cutoff: float) -> dict:
    g = gate(len(train), int(labels_of(train).sum()))
    if g:
        return _card("B3F", target, train, cutoff, {"abstain": g})
    b0 = _prevalence(train)
    groups: dict[str, list[int]] = {}
    for e in train:
        v = e.x.get(FATAL)
        groups.setdefault("MISSING" if not math.isfinite(_num(v)) else str(int(v)), []).append(e.y)
    return _card("B3F", target, train, cutoff, {"b0": b0, "m": M_SHRINK, "groups": _shrunk(groups, b0)})


def _complete(examples: Sequence[Example], cols: Sequence[str]) -> list[Example]:
    return [e for e in examples if all(math.isfinite(_num(e.x.get(c))) for c in cols)]


def fit_b2(target: str, train: Sequence[Example], cutoff: float, *, y_override: np.ndarray | None = None,
           kind: str = "B2", meta: dict | None = None) -> dict:
    """y_override replaces the training labels (NC1 shuffle); the card records it in meta."""
    use = [i for i, e in enumerate(train) if all(math.isfinite(_num(e.x.get(c))) for c in B2_REQUIRED)]
    y_all = labels_of(train) if y_override is None else np.asarray(y_override, float)
    y = y_all[use] if use else np.array([])
    g = gate(len(use), int(y.sum()))
    if g:
        return _card(kind, target, train, cutoff, {"abstain": g}, n_used=len(use), k_used=int(y.sum()), meta=meta)
    X = matrix([train[i] for i in use], B2_COLUMNS)
    prep = K.Prep().fit(X)
    lr = K.Logistic(C=C_L2).fit(prep.transform(X), y)
    return _card(kind, target, train, cutoff, {"columns": list(B2_COLUMNS), "required": list(B2_REQUIRED),
                                              "prep": prep.to_dict(), "logistic": lr.to_dict()},
                 n_used=len(use), k_used=int(y.sum()), meta=meta)


def fit_b3(target: str, train: Sequence[Example], cutoff: float) -> dict:
    use = _complete(train, (SCORE,))
    y = labels_of(use)
    g = gate(len(use), int(y.sum()) if len(use) else 0)
    if g:
        return _card("B3", target, train, cutoff, {"abstain": g}, n_used=len(use), k_used=int(y.sum()) if len(use) else 0)
    pl = K.Platt().fit(matrix(use, (SCORE,))[:, 0], y)
    return _card("B3", target, train, cutoff, {"column": SCORE, "platt": pl.to_dict()}, n_used=len(use), k_used=int(y.sum()))


def _raw(v: float) -> float:
    return math.expm1(v) if math.isfinite(v) else float("nan")


def fit_b4(target: str, train: Sequence[Example], cutoff: float) -> dict:
    g = gate(len(train), int(labels_of(train).sum()))
    if g:
        return _card("B4", target, train, cutoff, {"abstain": g})
    rows = sorted([[e.mint, _raw(_num(e.x.get(LIQ))), _raw(_num(e.x.get(MCAP))), e.y] for e in train
                   if math.isfinite(_num(e.x.get(LIQ))) and math.isfinite(_num(e.x.get(MCAP)))], key=lambda r: (r[0], r[1], r[2], r[3]))
    return _card("B4", target, train, cutoff, {"b0": _prevalence(train), "m": M_SHRINK, "factor": B4_FACTOR, "train": rows})


FITTERS = {"B0": fit_b0, "B1": fit_b1, "B2": fit_b2, "B3": fit_b3, "B3F": fit_b3f, "B4": fit_b4}


def evidence_class(is_fixture: bool) -> str:
    return FIXTURE_FLAG if is_fixture else "DEVELOPMENT_RETROSPECTIVE_PROVIDER_MODE"


def fit_all(target: str, train: Sequence[Example], cutoff: float, *, is_fixture: bool = False) -> dict[str, dict]:
    """Every baseline on one training set. Training rows must be decided before and matured by the cutoff (checked).
    Cards of a synthetic fixture carry NO_REAL_HISTORICAL_EVIDENCE (package phase 07 step 5)."""
    check_asof(train, sorted(ALLOWED_COLUMNS), as_of=cutoff, with_labels=True)
    for e in train:
        if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):
            raise BaselineError(f"training row {e.decision_key[:12]} is not decided before and matured by the cutoff (P05, P43)")
    out = {}
    for b in BASELINES:
        c = FITTERS[b](target, train, cutoff)
        c["evidence_class"] = evidence_class(is_fixture)
        c["model_sha"] = sha({k: v for k, v in c.items() if k != "model_sha"})
        out[b] = c
    return out


# ---------------------------------------------------------------- prediction from cards (numpy only)
def predict(card: dict, examples: Sequence[Example]) -> tuple[np.ndarray, list[str | None]]:
    """Numbers and abstain reasons for each example. NaN with a reason when the card abstains or an input is missing."""
    body, kind = card["body"], card["kind"]
    n = len(examples)
    if "abstain" in body:
        return np.full(n, np.nan), [body["abstain"]] * n
    if n:
        check_asof(examples, sorted(ALLOWED_COLUMNS), as_of=None, with_labels=False)
    p, why = np.full(n, np.nan), [None] * n
    if kind == "B0":
        p[:] = body["p"]
    elif kind in ("B1", "B3F"):
        for i, e in enumerate(examples):
            key = status_group(e.status) if kind == "B1" else ("MISSING" if not math.isfinite(_num(e.x.get(FATAL))) else str(int(e.x[FATAL])))
            p[i] = body["groups"][key]["p"] if key in body["groups"] else body["b0"]
    elif kind.startswith("B2") or kind.startswith("NC1"):
        ok = [i for i, e in enumerate(examples) if all(math.isfinite(_num(e.x.get(c))) for c in body["required"])]
        if ok:
            X = matrix([examples[i] for i in ok], body["columns"])
            prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])
            p[ok] = lr.predict_proba1(prep.transform(X))
        for i in set(range(n)) - set(ok):
            why[i] = "OOD"
    elif kind == "B3":
        pl = K.Platt.from_dict(body["platt"])
        for i, e in enumerate(examples):
            s = _num(e.x.get(SCORE))
            if math.isfinite(s):
                p[i] = float(pl.predict(np.array([s]))[0])
            else:
                why[i] = "OOD"
    elif kind == "B4":
        tr = body["train"]
        for i, e in enumerate(examples):
            liq, mc = _raw(_num(e.x.get(LIQ))), _raw(_num(e.x.get(MCAP)))
            if not (math.isfinite(liq) and math.isfinite(mc)):
                p[i] = body["b0"]
                continue
            ys = [r[3] for r in tr if r[0] != e.mint and _within(r[1], liq, body["factor"]) and _within(r[2], mc, body["factor"])]
            p[i] = (sum(ys) + body["m"] * body["b0"]) / (len(ys) + body["m"])
    else:
        raise BaselineError(f"unknown card kind {kind}")
    fin = p[np.isfinite(p)]
    if fin.size:
        K.check_probs(fin)
    return p, why


def _within(a: float, b: float, factor: float) -> bool:
    if not (math.isfinite(a) and math.isfinite(b)) or a < 0 or b < 0:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(math.log(a / b)) <= math.log(factor)


def contemporaneous_control(row: Example, pool: Sequence[Example]) -> float:
    """B4C, description only: outcome rate of other-mint decisions within 12 h with liquidity and market cap within a factor 3.
    Uses outcomes that are not known at the decision: never a forecaster, never in a skill comparison, never an artifact."""
    liq, mc = _raw(_num(row.x.get(LIQ))), _raw(_num(row.x.get(MCAP)))
    if not (math.isfinite(liq) and math.isfinite(mc)):
        return float("nan")
    ys = [e.y for e in pool if e.mint != row.mint and abs(e.decision_time - row.decision_time) <= B4C_WINDOW_S
          and _within(_raw(_num(e.x.get(LIQ))), liq, B4_FACTOR) and _within(_raw(_num(e.x.get(MCAP))), mc, B4_FACTOR)]
    return float(np.mean(ys)) if len(ys) >= B4C_MIN_CONTROLS else float("nan")


# ---------------------------------------------------------------- the frozen walk-forward
def first_last_train_day() -> float:
    return C.parse_utc(C.ACCEPTANCE["walk_forward"]["first_fold_last_train_day_utc"] + "T00:00:00Z")


def maturity_lag(target: str) -> float:
    return C.label_matures_at(target, 0.0)


def walk_forward(target: str, development: Sequence[Example], train_at: Callable[[float], Sequence[Example]], *,
                 nc1_seeds: Iterable[int] = range(20), is_fixture: bool = False) -> dict:
    """Run the frozen day walk-forward. `development` is every development label (matured by the holdout start) with its
    inputs; `train_at(cutoff)` returns the training examples the gate gives at that cutoff. Returns folds, cards, out-of-sample
    rows with every baseline's number and reason, NC1 numbers per seed and the fold audit."""
    dev = sorted(development, key=lambda e: (e.decision_time, e.mint))
    if not dev:
        return {"target": target, "folds": [], "oos": [], "audit": None, "status": "INSUFFICIENT_HISTORY",
                "evidence_class": evidence_class(is_fixture)}
    dt_ = np.array([e.decision_time for e in dev])
    mat = np.array([e.label_matures_at for e in dev])
    folds = K.day_walk_forward(dt_, mat, first_last_train_day=first_last_train_day(),
                               min_train=C.ACCEPTANCE["walk_forward"]["first_fold_min_events"])
    audit = K.fold_audit(dt_, mat, folds, len(dev), min_maturity_lag_s=maturity_lag(target), groups=[e.mint for e in dev])
    if folds and not audit["valid_walk_forward"]:
        raise BaselineError(f"{target}: fold audit failed: {audit['reasons']}")
    seeds = list(nc1_seeds)
    out_folds, oos = [], []
    for k, f in enumerate(folds):
        cut = float(f["cutoff"])
        train = list(train_at(cut))
        want = sorted(dev[i].decision_key for i in f["train"])
        got = sorted(e.decision_key for e in train)
        if want != got:
            raise WalkForwardMismatch(f"{target} fold {k}: walk-forward index ({len(want)}) and training gate ({len(got)}) differ")
        test = [dev[i] for i in f["test"]]
        cards = fit_all(target, train, cut, is_fixture=is_fixture)
        preds = {b: predict(cards[b], test) for b in BASELINES}
        nc1 = {s: np.full(len(test), np.nan) for s in seeds}
        if "abstain" not in cards["B2"]["body"]:
            for s in seeds:
                yy = np.random.default_rng(s).permutation(labels_of(train))
                cnc = fit_b2(target, train, cut, y_override=yy, kind="NC1", meta={"nc1_seed": s})
                nc1[s] = predict(cnc, test)[0]
        mints_tr = {e.mint for e in train}
        creators_tr = {e.creator for e in train if e.creator}
        narr_tr = {e.narrative for e in train if e.narrative}
        for j, e in enumerate(test):
            row = {"fold": k, "cutoff": cut, "example": e, "y": e.y,
                   "new_mint": e.mint not in mints_tr,
                   "new_creator": (e.creator not in creators_tr) if e.creator else None,
                   "new_narrative": (e.narrative not in narr_tr) if e.narrative else None}
            for b in BASELINES:
                row[b] = float(preds[b][0][j])
                row[b + "_why"] = preds[b][1][j]
            for s, v in nc1.items():
                row[f"NC1_{s}"] = float(v[j])
            row["B4C"] = contemporaneous_control(e, dev)
            oos.append(row)
        out_folds.append({"fold": k, "cutoff": cut, "cutoff_utc": _iso(cut), "n_train": len(train),
                          "k_train": int(labels_of(train).sum()), "n_test": len(test), "k_test": int(sum(e.y for e in test)),
                          "test_day": _iso(cut)[:10], "cards": cards,
                          "split_fingerprint": sha([target, cut, want, sorted(e.decision_key for e in test)])})
    return {"target": target, "folds": out_folds, "oos": oos, "audit": audit, "nc1_seeds": seeds,
            "evidence_class": evidence_class(is_fixture),
            "split_fingerprint": sha([f["split_fingerprint"] for f in out_folds]),
            "status": "OK" if out_folds else "INSUFFICIENT_HISTORY"}


def cohort_table(rows: Sequence[dict], key: Callable[[Example], Any], models: Sequence[str] = ("B0", "B2", "B3")) -> list[dict]:
    """Descriptive out-of-sample table by one cohort key (route, status group, liquidity, launch age, week, day): counts and
    Brier per model. No rate or skill is claimed below 20 events (P21: no universal claim from one favourable cohort)."""
    out = []
    for v in sorted({str(key(r["example"]) or "UNKNOWN") for r in rows}):
        rr = [r for r in rows if str(key(r["example"]) or "UNKNOWN") == v]
        row = {"value": v, "n": len(rr), "positives": int(sum(r["y"] for r in rr)),
               "support_note": "n >= 20" if len(rr) >= C.ACCEPTANCE["min_bin_events"] else "n < 20: no rate claimed"}
        for m in models:
            ok = [r for r in rr if math.isfinite(r[m])]
            row[f"brier_{m}"] = K.brier([r["y"] for r in ok], [r[m] for r in ok]) if ok else None
            row[f"n_{m}"] = len(ok)
        out.append(row)
    return out


# ---------------------------------------------------------------- evaluation of pooled out-of-sample numbers
def evaluate(rows: Sequence[dict], model: str, *, reference: str = "B0", reps: int = 2000, seed: int = 20261025,
             boot: bool = True) -> dict:
    """Scores of one baseline against B0 on the rows where both have a number, with day and mint bootstrap intervals of the
    Brier skill score, the wider governing, and the frozen verdict. Rows without a number are coverage, not errors."""
    a = C.ACCEPTANCE
    n_all = len(rows)
    why = {}
    for r in rows:
        if not math.isfinite(r[model]):
            w = r.get(model + "_why") or "NO_NUMBER"
            why[w] = why.get(w, 0) + 1
    use = [r for r in rows if math.isfinite(r[model]) and math.isfinite(r[reference])]
    res: dict[str, Any] = {"baseline": model, "n_rows": n_all, "n_with_number": len(use),
                           "coverage": (len(use) / n_all) if n_all else None, "abstain_reasons": why}
    if not use:
        res["verdict"] = "INSUFFICIENT_HISTORY"
        return res
    y = np.array([r["y"] for r in use], float)
    p = np.array([r[model] for r in use], float)
    b = np.array([r[reference] for r in use], float)
    days = [r["example"].day for r in use]
    mints = [r["example"].mint for r in use]
    k = int(y.sum())
    res.update({"positives": k, "prevalence": float(y.mean()), "days": len(set(days)), "mints": len(set(mints)),
                "folds": len({r["fold"] for r in use}), "brier": K.brier(y, p), "brier_ref": K.brier(y, b),
                "log_loss": K.log_loss(y, p, a["secondary_scores"]["log_loss_clip"]),
                "log_loss_ref": K.log_loss(y, b, a["secondary_scores"]["log_loss_clip"]),
                "bss": K.brier_skill(y, p, b)})
    mpc = a["secondary_scores"]["auc_and_average_precision_min_per_class"]
    if k >= mpc and len(y) - k >= mpc and np.ptp(p) > 0:
        res["auc"], res["average_precision"] = K.roc_auc(y, p), K.average_precision(y, p)
    else:
        res["auc"] = res["average_precision"] = None
        res["auc_note"] = f"fewer than {mpc} events in a class, or a constant prediction"

    def bss_of(idx):
        return K.brier_skill(y[idx], p[idx], b[idx])

    sq = (p - y) ** 2
    intervals = {}
    for unit, groups in ((("day", days), ("mint", mints)) if boot else ()):
        ng = len(set(groups))
        if unit == "day" and ng < a["min_effective_days"]:
            intervals[unit] = {"groups": ng, "ci": None, "note": f"fewer than {a['min_effective_days']} days: UNDEFINED"}
            res[f"ess_{unit}"] = None
            continue
        bs = K.group_bootstrap(groups, bss_of, reps=reps, seed=seed)
        intervals[unit] = {"groups": ng, "ci": list(bs["ci"]), "finite": bs["finite"],
                           "p_one_sided": (1 + int(np.sum(~(bs["values"] > 0)))) / (reps + 1)}
        res[f"ess_{unit}"] = K.design_effect_ess(groups, sq, reps=reps, seed=seed)
    res["intervals"] = intervals
    if not intervals or any(intervals[u]["ci"] is None for u in intervals):
        res["governing"], res["gov_ci"], res["p_one_sided"] = None, None, None
    else:
        w = max(intervals, key=lambda u: intervals[u]["ci"][1] - intervals[u]["ci"][0])
        res["governing"], res["gov_ci"], res["p_one_sided"] = w, intervals[w]["ci"], intervals[w]["p_one_sided"]
    cal = a["calibration"]
    res["calibration"] = K.calibration_bins(y, p, min_bin=cal["min_bin_events"], max_bins=cal["max_bins"],
                                            in_the_large_only_below=cal["in_the_large_only_below_events"])
    res["verdict"] = verdict(res)
    return res


def verdict(res: dict, p_holm: float | None = None) -> str:
    a = C.ACCEPTANCE
    if not res.get("n_with_number"):
        return "INSUFFICIENT_HISTORY"
    if res["days"] < a["min_effective_days"] or res.get("gov_ci") is None:
        return "INSUFFICIENT_DAYS"
    lo, hi = res["gov_ci"]
    if hi < 0:
        return "WORSE_THAN_BASE_RATE"
    if lo > 0 and p_holm is not None and p_holm < 1 - a["bootstrap"]["conf"]:
        return "SKILL_INDICATED_DEVELOPMENT_ONLY"
    return "NOT_DISTINGUISHABLE_FROM_BASE_RATE"


def abstain_document(target: str, *, mint: str, snapshot_hash: str, decision_time_utc: str, generated_at_utc: str,
                     reasons: Sequence[str], base_rate: float | None, card: dict | None) -> dict:
    """An ABSTAIN forecast document of the frozen contract built from a Phase 07 card (format only; P38, P46)."""
    tg = C.TARGETS[target]
    doc = {"contract_version": C.CONTRACT_VERSION, "chain": "solana", "mint_address": mint, "snapshot_hash": snapshot_hash,
           "decision_time_utc": decision_time_utc, "decision_time_basis": "EXPORT_COMMIT", "target": target,
           "target_version": tg["version"], "horizon_seconds": tg["horizon_s"], "position_usd": None, "probability": None,
           "prediction_status": "ABSTAIN", "abstain_reasons": list(reasons), "uncertainty_interval": None,
           "base_rate": base_rate, "calibration_reference": None, "training_cutoff_utc": card["training_cutoff_utc"] if card else None,
           "model_id": card["model_id"] if card else "not_selected", "model_sha": card["model_sha"] if card else None,
           "feature_set_sha": card["feature_set_sha"] if card else None, "data_snapshot_sha": card["data_snapshot_sha"] if card else None,
           "cohort": None, "evidence_refs": [], "backtest_status": C.BACKTEST_NOT_AVAILABLE, "backtest_assessment_ref": None,
           "execution_stress_assessment_ref": None, "behavioral_scenarios": [], "caveats": list(tg["caveats"]),
           "is_fixture": False, "generated_at_utc": generated_at_utc}
    doc["forecast_id"] = C.forecast_id("solana", mint, snapshot_hash, target, tg["version"], tg["horizon_s"], doc["model_sha"])
    return doc

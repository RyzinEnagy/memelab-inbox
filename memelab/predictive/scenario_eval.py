"""scenario-eval-1: the Phase 15 incremental-value trial of behavioral scenarios (research only, flag OFF).

Codes behavioral scenario documents into falsifiable statements about the registered primary targets without ever seeing an
outcome (scenario-coding-1), scores coded warnings against labels the caller obtained through `labels.training_labels`, builds
the training-only warning forecast A_WARN for the walk-forward comparison, and applies the frozen GO / NO_GO /
INSUFFICIENT_VALIDATION rule of `audits/predictive-intelligence/phase_15/behavioral/EXPERIMENT_PROTOCOL.md` (PI-D-079).

Nothing here is a probability that can be published: A_WARN is a research comparator, never a forecast document. The module
reads no file except through `verify_file`, opens no socket, imports no behavioral or social module and is imported by no other
lab module. Documents are plain dicts; the caller validates them with the behavioral validator and passes its errors in.
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
from . import evaluation as E
from . import stats as K

SCENARIO_EVAL_VERSION = "scenario-eval-1"
CODING_VERSION = "scenario-coding-1"
PRIMARY = tuple(t for t, v in C.TARGETS.items() if v.get("status") == "PRIMARY")
DOC_KIND = "BEHAVIORAL_HYPOTHESIS_NOT_A_FORECAST"
CODABLE_STATUSES = ("RULES_RAN", "SIMULATION_RAN")
EXPECTS = ("EVENT", "NO_EVENT")

CODED, NOT_CODABLE = "CODED", "NOT_CODABLE"
UNSCORABLE = "UNSCORABLE_NO_OUTCOME_SOURCE"
REFUSED_WINDOW = "REFUSED_WINDOW"
REFUSED_EXPECTATION = "REFUSED_EXPECTATION"
WARN_EVENT, WARN_NO_EVENT, WARN_CONFLICT, WARN_NONE, WARN_NOT_CODABLE = "EVENT", "NO_EVENT", "CONFLICT", "NONE", "NOT_CODABLE"
WARNINGS = (WARN_EVENT, WARN_NO_EVENT, WARN_CONFLICT, WARN_NONE, WARN_NOT_CODABLE)
EXCLUDED = (WARN_CONFLICT, WARN_NOT_CODABLE)          # ambiguous or not codable: never in a numerator or a denominator

# blindness (protocol 4 rule 6): keys that would carry an outcome into the coder
OUTCOME_KEY = re.compile(r"^(?:y|outcome.*|label_class|label_value|realized.*|realised.*|hit|first_touch.*|label_matures_at|"
                         r"label_observed_at|event_observed)$", re.I)

# descriptive verdicts (E2, E3)
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
INSUFFICIENT_DAYS = "INSUFFICIENT_DAYS"
INSUFFICIENT_EVENTS = "INSUFFICIENT_EVENTS"
NO_WARNINGS = "NO_WARNINGS"
INSUFFICIENT_WARNINGS = "INSUFFICIENT_WARNINGS"
LIFT_SUGGESTED = "DESCRIPTIVE_LIFT_SUGGESTED_NOT_A_CLAIM"
WORSE = "DESCRIPTIVE_WORSE_THAN_PREVALENCE"
NOT_DISTINGUISHABLE = "DESCRIPTIVE_NOT_DISTINGUISHABLE"
MIN_WARNED = C.ACCEPTANCE["min_bin_events"]            # 20
ALPHA = E.ALPHA

# A_WARN
A_WARN = "A_WARN"
DEV_SKILL = "SKILL_INDICATED_DEVELOPMENT_ONLY"

# decision (protocol 10)
MIN_EVENTS = 100
INSUFFICIENT_VALIDATION = "INSUFFICIENT_VALIDATION"
EVALUABLE = "EVALUABLE"
MIROFISH_NO_GO = "MIROFISH_NO_GO"
MIROFISH_GO_CANDIDATE = "MIROFISH_GO_CANDIDATE_PROSPECTIVE_ONLY"
RULES_NOT_PROMOTED = "RULES_NOT_PROMOTED"
RULES_CANDIDATE = "RULES_CANDIDATE_PROSPECTIVE_ONLY"
RAN = "RAN"


class ScenarioEvalError(ValueError):
    pass


class BlindingError(ScenarioEvalError):
    """An outcome-like key reached the coder, or a coding file is not the committed one."""


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def _iso(t: float) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- blind coding (scenario-coding-1)
def check_blind(o: Any, path: str = "") -> None:
    """Refuse any input that holds an outcome-like key at any depth (the coder never sees an outcome)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str) and OUTCOME_KEY.match(k):
                raise BlindingError(f"outcome-like key {path + '.' + k if path else k!r} in a coder input")
            check_blind(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            check_blind(v, f"{path}[{i}]")


def _not_codable(doc: Any, reason: str) -> dict:
    return {"coding_version": CODING_VERSION, "status": NOT_CODABLE, "reason": reason,
            "doc_sha256": doc.get("doc_sha256") if isinstance(doc, dict) else None, "statements": [], "unscorable": [],
            "refused": [], "no_statement": 0}


def code_document(doc: Any, validation_errors: Sequence[str]) -> dict:
    """Protocol 4: one document to statements on the primary targets. `validation_errors` is the behavioral validator's list
    for this document (empty when valid). Never reads an outcome; refuses an input holding an outcome-like key."""
    check_blind(doc)
    if not isinstance(doc, dict):
        return _not_codable(doc, "NOT_A_DOCUMENT")
    if validation_errors:
        return _not_codable(doc, "DOCUMENT_INVALID")
    if doc.get("kind") != DOC_KIND:
        return _not_codable(doc, "NOT_A_BEHAVIORAL_DOCUMENT")
    if doc.get("status") not in CODABLE_STATUSES:
        return _not_codable(doc, f"STATUS_{doc.get('status')}")
    hyps = doc.get("hypotheses")
    if not isinstance(hyps, list) or not hyps:
        return _not_codable(doc, "FREE_TEXT_OR_NO_HYPOTHESIS")
    try:
        T = C.parse_utc(doc["subject"]["decision_time_utc"])
    except (KeyError, TypeError, ValueError):
        return _not_codable(doc, "NO_DECISION_TIME")
    out = {"coding_version": CODING_VERSION, "status": CODED, "reason": None, "doc_sha256": doc.get("doc_sha256"),
           "statements": [], "unscorable": [], "refused": [], "no_statement": 0}
    for h in hyps:
        mon = h.get("monitor") if isinstance(h, dict) else None
        label = h.get("label") if isinstance(h, dict) else None
        hid = h.get("hypothesis_id") if isinstance(h, dict) else None
        if mon is None:
            out["no_statement"] += 1
            continue
        metric, expect = mon.get("metric"), mon.get("expect")
        if metric not in PRIMARY:
            out["unscorable"].append({"metric": metric, "label": label, "hypothesis_id": hid, "reason": UNSCORABLE})
            continue
        if expect not in EXPECTS:
            out["refused"].append({"target": metric, "label": label, "hypothesis_id": hid, "reason": REFUSED_EXPECTATION})
            continue
        try:
            ws, we = C.parse_utc(mon["window_start_utc"]), C.parse_utc(mon["window_end_utc"])
        except (KeyError, TypeError, ValueError):
            ws = we = None
        if ws != T or we != T + C.TARGETS[metric]["horizon_s"]:
            out["refused"].append({"target": metric, "label": label, "hypothesis_id": hid, "reason": REFUSED_WINDOW})
            continue
        out["statements"].append({"target": metric, "expect": expect, "label": label, "hypothesis_id": hid})
    out["statements"].sort(key=lambda s: (s["target"], s["expect"], str(s["label"]), str(s["hypothesis_id"])))
    return out


def warnings_of(coded: dict) -> dict[str, str]:
    """Protocol 4 rule 5: per primary target EVENT, NO_EVENT, CONFLICT (both) or NONE; NOT_CODABLE for every target of a
    document that could not be coded."""
    if coded.get("status") != CODED:
        return {t: WARN_NOT_CODABLE for t in PRIMARY}
    out = {}
    for t in PRIMARY:
        ex = {s["expect"] for s in coded["statements"] if s["target"] == t}
        if ex == {"EVENT", "NO_EVENT"}:
            out[t] = WARN_CONFLICT
        elif ex == {"EVENT"}:
            out[t] = WARN_EVENT
        elif ex == {"NO_EVENT"}:
            out[t] = WARN_NO_EVENT
        else:
            out[t] = WARN_NONE
    return out


def labels_by_target(coded: dict) -> dict[str, list[str]]:
    """The labels behind each target's statements (for the per-label descriptions)."""
    out: dict[str, list[str]] = {t: [] for t in PRIMARY}
    for s in coded.get("statements", []):
        if s["expect"] == "EVENT" and s["label"] not in out[s["target"]]:
            out[s["target"]].append(s["label"])
    return {t: sorted(v) for t, v in out.items()}


def verify_file(path: str | Path, expected_sha256: str) -> bytes:
    """Read a committed coding file only when its sha256 equals the committed log's value (protocol 4 rule 6)."""
    b = Path(path).read_bytes()
    got = hashlib.sha256(b).hexdigest()
    if got != expected_sha256:
        raise BlindingError(f"{path}: sha256 {got[:12]} is not the committed {str(expected_sha256)[:12]}")
    return b


# ---------------------------------------------------------------- warning metrics (E2, E3)
def _scored(rows: Sequence[dict]) -> tuple[list[dict], dict]:
    excl = {w: 0 for w in EXCLUDED}
    use = []
    for r in rows:
        w = r["warning"]
        if w not in WARNINGS:
            raise ScenarioEvalError(f"warning {w!r} is not a coded warning")
        if r["y"] not in (0, 1):
            raise ScenarioEvalError("a scored row needs a 0 or 1 label from labels.training_labels")
        if w in EXCLUDED:
            excl[w] += 1
        else:
            use.append(r)
    return use, excl


def day_permutation(w: np.ndarray, y: np.ndarray, days: Sequence[str], *, reps: int, seed: int) -> dict:
    """Warnings permuted among the decisions of the same UTC day (protocol 6): the null of the warned hit count. Integer
    comparison, +1 rule. p_up: share of permutations with at least the observed hits; p_down: with at most."""
    w = np.asarray(w, bool)
    y = np.asarray(y, int)
    obs = int(np.sum(w & (y == 1)))
    groups: dict[str, list[int]] = {}
    for i, d in enumerate(days):
        groups.setdefault(str(d), []).append(i)
    idx = [np.array(v) for _, v in sorted(groups.items())]
    rng = np.random.default_rng(seed)
    null = np.empty(reps, int)
    for r in range(reps):
        wp = w.copy()
        for g in idx:
            wp[g] = rng.permutation(w[g])
        null[r] = int(np.sum(wp & (y == 1)))
    return {"observed_hits": obs, "p_up": (1 + int(np.sum(null >= obs))) / (reps + 1),
            "p_down": (1 + int(np.sum(null <= obs))) / (reps + 1), "null_mean_hits": float(null.mean()),
            "null_min": int(null.min()), "null_max": int(null.max()), "reps": reps, "seed": seed}


def gate(n: int, k: int, days: int, warned: int) -> str | None:
    """Frozen order: no rows, fewer than 5 days, the out-of-sample event minimums (50, 10 per class), no warning, fewer than
    20 warned decisions."""
    a = C.ACCEPTANCE
    if n == 0:
        return INSUFFICIENT_HISTORY
    if days < a["min_effective_days"]:
        return INSUFFICIENT_DAYS
    if n < a["min_holdout_events"] or k < a["min_holdout_per_class"] or n - k < a["min_holdout_per_class"]:
        return INSUFFICIENT_EVENTS
    if warned == 0:
        return NO_WARNINGS
    if warned < MIN_WARNED:
        return INSUFFICIENT_WARNINGS
    return None


def warning_metrics(rows: Sequence[dict], *, reps: int = 2000, seed: int = 20261025) -> dict:
    """Precision, coverage, recall, lift over the prevalence of the same rows, lead time of hits and the day-stratified
    permutation; the verdict needs Holm-adjusted p values from `descriptive_verdict`. Rows: warning, y, day, optional lead_s."""
    use, excl = _scored(rows)
    n = len(use)
    y = np.array([r["y"] for r in use], int)
    w = np.array([r["warning"] == WARN_EVENT for r in use], bool)
    days = [str(r["day"]) for r in use]
    k = int(y.sum()) if n else 0
    nw = int(w.sum())
    hits = int(np.sum(w & (y == 1)))
    res: dict[str, Any] = {"n_rows": len(rows), "excluded": excl, "n_scored": n, "positives": k, "days": len(set(days)),
                           "warned": nw, "hits": hits, "no_event_statements": sum(1 for r in use if r["warning"] == WARN_NO_EVENT),
                           "prevalence": (k / n) if n else None, "prevalence_wilson": list(K.wilson(k, n)) if n else None,
                           "precision": (hits / nw) if nw else None, "precision_wilson": list(K.wilson(hits, nw)) if nw else None,
                           "recall": (hits / k) if k else None, "coverage": (nw / n) if n else None}
    res["lift"] = (res["precision"] - res["prevalence"]) if (nw and n) else None
    leads = [float(r["lead_s"]) / 3600.0 for r, ww, yy in zip(use, w, y) if ww and yy == 1 and r.get("lead_s") is not None]
    res["lead_time_h"] = ({"n": len(leads), "median": float(np.median(leads)), "min": float(min(leads)), "max": float(max(leads))}
                          if leads else None)
    res["gate"] = gate(n, k, res["days"], nw)
    if nw and nw < n:
        res["permutation"] = day_permutation(w, y, days, reps=reps, seed=seed)
    else:
        res["permutation"] = None
    return res


def descriptive_verdict(res: dict, p_up_holm: float | None, p_down_holm: float | None) -> str:
    if res.get("gate"):
        return res["gate"]
    lift = res.get("lift")
    if lift is not None and lift > 0 and p_up_holm is not None and math.isfinite(p_up_holm) and p_up_holm < ALPHA:
        return LIFT_SUGGESTED
    if lift is not None and lift < 0 and p_down_holm is not None and math.isfinite(p_down_holm) and p_down_holm < ALPHA:
        return WORSE
    return NOT_DISTINGUISHABLE


def holm_by_target(results: dict[str, dict]) -> dict[str, dict]:
    """Holm over the three primary targets for each direction; a target without a permutation counts as p 1 (stats.holm)."""
    up = [(results.get(t) or {}).get("permutation", None) for t in PRIMARY]
    pu = K.holm([u["p_up"] if u else None for u in up])
    pd = K.holm([u["p_down"] if u else None for u in up])
    out = {}
    for i, t in enumerate(PRIMARY):
        r = results.get(t)
        if r is None:
            continue
        a, b = pu[i], pd[i]
        a = a if math.isfinite(a) else None
        b = b if math.isfinite(b) else None
        out[t] = {"p_up_holm": a, "p_down_holm": b, "verdict": descriptive_verdict(r, a, b)}
    return out


# ---------------------------------------------------------------- A_WARN (E1)
def fit_warn(target: str, train: Sequence[dict], cutoff: float) -> dict:
    """Training-only event rate of each warning stratum, shrunk toward the training prevalence with m = 20 (the B1 convention),
    behind the frozen training gate. Rows: decision_key, decision_time, label_matures_at, y, warning."""
    if target not in PRIMARY:
        raise ScenarioEvalError(f"{target} is not a primary target")
    for r in train:
        if not (float(r["decision_time"]) < cutoff and float(r["label_matures_at"]) <= cutoff):
            raise ScenarioEvalError(f"training row {str(r['decision_key'])[:12]} is not decided before and matured by the cutoff "
                                    "(P05, P43)")
    use, excl = _scored(train)
    n = len(use)
    k = int(sum(r["y"] for r in use))
    card: dict[str, Any] = {"model_id": A_WARN, "version": SCENARIO_EVAL_VERSION, "target": target, "training_cutoff": float(cutoff),
                            "training_cutoff_utc": _iso(cutoff), "n": n, "k": k, "excluded": excl, "m": B.M_SHRINK,
                            "training_keys_sha256": sha(sorted(str(r["decision_key"]) for r in train))}
    g = B.gate(n, k)
    if g:
        card["abstain"] = g
    else:
        b0 = k / n
        cells: dict[str, dict] = {}
        for r in use:
            c = cells.setdefault(r["warning"], {"n": 0, "k": 0})
            c["n"] += 1
            c["k"] += int(r["y"])
        for c in cells.values():
            c["p"] = (c["k"] + B.M_SHRINK * b0) / (c["n"] + B.M_SHRINK)
        card["b0"] = b0
        card["cells"] = dict(sorted(cells.items()))
    card["card_sha256"] = sha(card)
    return card


def verify_warn_card(card: dict) -> dict:
    body = {k: v for k, v in card.items() if k != "card_sha256"}
    if sha(body) != card.get("card_sha256"):
        raise ScenarioEvalError("A_WARN card sha256 does not match its contents")
    return card


def predict_warn(card: dict, rows: Sequence[dict]) -> tuple[np.ndarray, list[str | None]]:
    """A_WARN numbers for decisions at or after the card's cutoff only (P13). Ambiguous or not-codable rows get no number."""
    verify_warn_card(card)
    early = [r for r in rows if float(r["decision_time"]) < card["training_cutoff"]]
    if early:
        raise ScenarioEvalError(f"A_WARN trained to {card['training_cutoff_utc']} cannot score {len(early)} earlier decision(s) "
                                "(P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)")
    n = len(rows)
    p, why = np.full(n, np.nan), [None] * n
    if "abstain" in card:
        return p, [card["abstain"]] * n
    for i, r in enumerate(rows):
        w = r["warning"]
        if w not in WARNINGS:
            raise ScenarioEvalError(f"warning {w!r} is not a coded warning")
        if w in EXCLUDED:
            why[i] = "AMBIGUOUS_OR_NOT_CODABLE"
            continue
        p[i] = card["cells"][w]["p"] if w in card["cells"] else card["b0"]
    fin = p[np.isfinite(p)]
    if fin.size:
        K.check_probs(fin)
    return p, why


def selection_status_dev(verdict: str | None, p_holm: float | None, p_bonferroni: float | None, p_max_t: float | None = None) -> str:
    """The Phase 12 claim rule applied to a development verdict: a skill verdict and all three corrections below alpha; a
    computed correction at or above alpha fails; a missing one is CORRECTION_NOT_COMPUTED, never a pass."""
    if verdict != DEV_SKILL:
        return E.NO_UNCORRECTED_SKILL
    ps = [p_holm, p_max_t, p_bonferroni]
    known = [p for p in ps if p is not None and math.isfinite(p)]
    if any(p >= ALPHA for p in known):
        return E.FAILS
    if len(known) < len(ps):
        return E.NOT_COMPUTED
    return E.SURVIVES


# ---------------------------------------------------------------- the frozen decision (protocol 10)
def decide(*, eligible_events: int, comparators: dict[str, str], d_result: dict | None = None,
           a_warn: dict[str, dict] | None = None) -> dict:
    """GO / NO_GO / INSUFFICIENT_VALIDATION from recorded inputs. `comparators` maps A, B, C, D to RAN or a blocking reason;
    `d_result` holds D's selection_status, not_worse_than_all, stability, cutoff_verified_before_events, within_approved_budget;
    `a_warn` maps a target to verdict, selection_status, brier and brier_b2 (E1)."""
    if not isinstance(eligible_events, int) or eligible_events < 0:
        raise ScenarioEvalError("eligible_events is a count")
    reasons = []
    if eligible_events < MIN_EVENTS:
        reasons.append("ELIGIBLE_EVENTS_BELOW_100")
    if comparators.get("D") != RAN:
        reasons.append("D_NOT_RUN")
    if comparators.get("B") != RAN:
        reasons.append("B_NOT_RUN")
    validation = INSUFFICIENT_VALIDATION if reasons else EVALUABLE
    mf = list(reasons)
    if validation == EVALUABLE:
        d = d_result or {}
        if d.get("selection_status") != E.SURVIVES:
            mf.append("D_NO_SKILL_SURVIVING_SELECTION_CORRECTION")
        if d.get("not_worse_than_all") is not True:
            mf.append("D_NOT_SHOWN_NOT_WORSE_THAN_EVERY_COMPARATOR")
        if d.get("stability") != "STABLE":
            mf.append("D_NOT_STABLE")
        if d.get("cutoff_verified_before_events") is not True:
            mf.append("P26_TRAINING_CUTOFF_NOT_VERIFIED")
        if d.get("within_approved_budget") is not True:
            mf.append("NO_APPROVED_BUDGET")
    mirofish = MIROFISH_GO_CANDIDATE if (validation == EVALUABLE and not mf) else MIROFISH_NO_GO
    rules_targets = []
    for t, a in sorted((a_warn or {}).items()):
        b, b2 = a.get("brier"), a.get("brier_b2")
        if (a.get("verdict") == DEV_SKILL and a.get("selection_status") == E.SURVIVES and b is not None and b2 is not None
                and math.isfinite(b) and math.isfinite(b2) and b <= b2):
            rules_targets.append(t)
    return {"version": SCENARIO_EVAL_VERSION, "validation": validation, "validation_reasons": reasons, "mirofish": mirofish,
            "mirofish_reasons": mf, "rules_1": RULES_CANDIDATE if rules_targets else RULES_NOT_PROMOTED,
            "rules_1_targets": rules_targets, "eligible_events": eligible_events, "min_events": MIN_EVENTS,
            "comparators": dict(sorted(comparators.items())), "probability_created": False, "live_capability_created": False}


def summarize_rows(rows: Iterable[dict]) -> dict:
    """Independence counts of a set of decision snapshots: rows, distinct mints, days and export commits."""
    rows = list(rows)
    return {"rows": len(rows), "mints": len({r["mint"] for r in rows}), "days": len({str(r["decision_time_utc"])[:10] for r in rows}),
            "export_commits": len({r["export_commit"] for r in rows})}


# ---------------------------------------------------------------- mint-block nulls (repair pass 2, PI-D-082, CX-S15)
MINT_NULL_VERSION = "mint-block-null-1"


def mint_block_permutation(w: Any, y: Any, groups: Sequence[str], mints: Sequence[str], *, reps: int, seed: int) -> dict:
    """Null of the warned hit count when warnings go to whole mints (CX-S15: rule warnings follow a mint's persistent attention
    proxies, so the decision-level permutation is optimistic). Within each group (a UTC day, or one group for the whole sample)
    the rows of one mint form a block; each replicate warns whole blocks in a random order until the group's observed warned
    count is reached, the last block only in part (a random subset, its hits drawn hypergeometric). With one decision per mint
    this is the decision-level permutation. Integer comparison, +1 rule."""
    w = np.asarray(w, bool)
    y = np.asarray(y, int)
    if not (len(w) == len(y) == len(groups) == len(mints)):
        raise ScenarioEvalError("warnings, labels, groups and mints must have one entry per row")
    obs = int(np.sum(w & (y == 1)))
    by: dict[str, dict[str, list[int]]] = {}
    for i, (g, m) in enumerate(zip(groups, mints)):
        by.setdefault(str(g), {}).setdefault(str(m), []).append(i)
    struct = []
    for g in sorted(by):
        blocks = [np.array(by[g][m]) for m in sorted(by[g])]
        sizes = np.array([len(b) for b in blocks], int)
        pos = np.array([int(y[b].sum()) for b in blocks], int)
        struct.append((sizes, pos, int(sum(int(w[b].sum()) for b in blocks))))
    rng = np.random.default_rng(seed)
    null = np.empty(reps, int)
    for r in range(reps):
        h = 0
        for sizes, pos, m in struct:
            if m == 0:
                continue
            o = rng.permutation(len(sizes))
            cs = np.cumsum(sizes[o])
            full = int(np.searchsorted(cs, m, side="right"))
            h += int(pos[o[:full]].sum())
            rest = m - (int(cs[full - 1]) if full else 0)
            if rest > 0:
                b = o[full]
                h += int(rng.hypergeometric(int(pos[b]), int(sizes[b] - pos[b]), rest))
        null[r] = h
    n_ge, n_le = int(np.sum(null >= obs)), int(np.sum(null <= obs))
    return {"observed_hits": obs, "p_up": (n_ge + 1) / (reps + 1), "p_down": (n_le + 1) / (reps + 1),
            "null_mean_hits": float(null.mean()), "null_min": int(null.min()), "null_max": int(null.max()), "reps": reps,
            "seed": seed, "groups": len(struct), "blocks": int(sum(len(s) for s, _, _ in struct))}


def clustered_metrics(rows: Sequence[dict], *, reps: int = 2000, seed: int = 20261025) -> dict:
    """The decision-level null beside the two mint-block nulls (mints within each day; whole mints over the whole sample) for
    rows with warning, y, day and mint. The conservative p of each direction is the largest of the three, so it is never
    smaller than the decision-level p of `warning_metrics` (same seed)."""
    use, _ = _scored(rows)
    if any("mint" not in r for r in use):
        raise ScenarioEvalError("the mint-block null needs the mint of every scored row")
    n = len(use)
    y = np.array([r["y"] for r in use], int)
    w = np.array([r["warning"] == WARN_EVENT for r in use], bool)
    days = [str(r["day"]) for r in use]
    mints = [str(r["mint"]) for r in use]
    out: dict[str, Any] = {"version": MINT_NULL_VERSION, "n_scored": n, "warned": int(w.sum()),
                           "lift": None, "decision": None, "mint_within_day": None, "mint_whole_sample": None,
                           "p_up_conservative": None, "p_down_conservative": None}
    if n and int(y.sum()) and int(w.sum()):
        out["lift"] = float(np.sum(w & (y == 1)) / w.sum() - y.mean())
    if not (int(w.sum()) and int(w.sum()) < n):
        return out
    out["decision"] = day_permutation(w, y, days, reps=reps, seed=seed)
    out["mint_within_day"] = mint_block_permutation(w, y, days, mints, reps=reps, seed=seed)
    out["mint_whole_sample"] = mint_block_permutation(w, y, ["ALL"] * n, mints, reps=reps, seed=seed)
    for d in ("p_up", "p_down"):
        out[f"{d}_conservative"] = max(out[k][d] for k in ("decision", "mint_within_day", "mint_whole_sample"))
    return out


def more_conservative(v_decision: str | None, v_other: str | None) -> str | None:
    """Combine two descriptive verdicts so the result is never less conservative than the first: a gate stays; a lift or a
    worse-than-prevalence verdict survives only when both say it."""
    if v_decision not in (LIFT_SUGGESTED, WORSE, NOT_DISTINGUISHABLE):
        return v_decision
    return v_decision if v_other == v_decision else NOT_DISTINGUISHABLE


def conservative_holm_by_target(results: dict[str, dict], clustered: dict[str, dict]) -> dict[str, dict]:
    """Holm over the three primary targets on the conservative (mint-block) p values; an absent target counts as p 1. The
    verdict is `more_conservative` of the recorded decision-level verdict and the one from these p values."""
    pu = K.holm([(clustered.get(t) or {}).get("p_up_conservative") for t in PRIMARY])
    pd = K.holm([(clustered.get(t) or {}).get("p_down_conservative") for t in PRIMARY])
    out = {}
    for i, t in enumerate(PRIMARY):
        r = results.get(t)
        if r is None:
            continue
        a = pu[i] if math.isfinite(pu[i]) else None
        b = pd[i] if math.isfinite(pd[i]) else None
        out[t] = {"p_up_holm_conservative": a, "p_down_holm_conservative": b,
                  "verdict_conservative": more_conservative(r.get("verdict"), descriptive_verdict(r, a, b))}
    return out


def control_own_level(lift: float | None, p_up: float | None, p_down: float | None) -> str:
    """A pre-registered negative control judged as the single test it is, at ALPHA, with no family padding (skeptic m2):
    FLAGGED when its p in the direction of its lift is below ALPHA, else NOT_FLAGGED; NOT_TESTABLE without a p value."""
    if lift is None or p_up is None or p_down is None:
        return "NOT_TESTABLE"
    if (lift > 0 and p_up < ALPHA) or (lift < 0 and p_down < ALPHA):
        return "FLAGGED"
    return "NOT_FLAGGED"

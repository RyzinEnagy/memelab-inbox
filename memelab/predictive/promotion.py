"""CM-2 (PI-D-122): promotion from prospective evidence, and the CM-2 registry log. Research only, flag OFF, imported by no
other module of the lab (the daily cycle in audits/predictive-intelligence/daily/ and the tests use it). numpy, the standard
library, `contract` and `stats` only; no network, no clock, no file read other than the log the caller names.

The rule is `contract.PROMOTION_CM2` (fingerprint `contract.promotion_rule_sha256()`); it supersedes ACCEPTANCE["promotion"]
for promotion decisions and keeps every frozen minimum:
  - a window belongs to one (recipe, kind, target); it starts strictly after the recipe freeze (a later one strictly after the
    previous window's last decision day) and closes at the shortest run of complete UTC decision days whose scorable outcomes
    reach 50 events, 10 per class and 5 days (`next_window`);
  - it is admissible only when every scored prediction precedes its outcome in the ledger and was committed to git before the
    outcome's label read, came from a version registered at or before the decision and not stale (`admissibility`);
  - it passes when the Brier skill against B0 has its lower bound above 0 at the Bonferroni level alpha / (N_search x
    windows) for both resample units (decision day and mint), and calibration holds in the large and in every bin
    (`evaluate_window`);
  - SHADOW is the first passed window; VALIDATED_EXPERIMENTAL a later passed window that is also not worse than B2 on Brier
    (`level`). Nothing else promotes and a level is recomputed, never given.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import contract as C
from . import stats as K

RULE = C.PROMOTION_CM2
LEVELS = ("ABSTAIN", "SHADOW", "VALIDATED_EXPERIMENTAL", "NO_GO")
PUBLISHABLE = ("SHADOW", "VALIDATED_EXPERIMENTAL")
ROLES = ("REFERENCE_BASELINE", "CANDIDATE")
DAY = 86400.0
EVENT_KINDS = ("REGISTER", "PIN", "RETIRE", "PROMOTE")       # PROMOTE: PI-D-140
PIN_MODES = ("CHAMPION", "NO_VIABLE_CHAMPION")
GENESIS = "0" * 64

# window and result states
OPEN = "WINDOW_OPEN"
CLOSED = "WINDOW_CLOSED"
NOT_ADMISSIBLE = "WINDOW_NOT_ADMISSIBLE"
PASSED = "WINDOW_PASSED"
FAILED = "WINDOW_FAILED"


class PromotionError(ValueError):
    pass


class LogError(ValueError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def iso(t: float) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(t: float) -> float:
    return math.floor(float(t) / DAY) * DAY


# ---------------------------------------------------------------- windows
def next_window(rows: Sequence[dict], *, after: float, from_day: float | None = None) -> dict:
    """The next window of one (recipe, kind, target).

    rows: one per predicted decision, with `decision_key`, `decision_time`, `final` (the outcome is final: not PENDING or
    NOT_READ) and `scorable` (LABELED, uncensored, the prediction has a number). Only decisions after `after` (strictly) and on
    or after `from_day` (a UTC day start) belong to it. Days are added in time order while complete; the window closes at the
    first day where its scorable rows reach the count minimums. An incomplete day stops it (OPEN), so a later outcome can never
    move a decision out of a window that has already closed."""
    lo = float(after)
    use = sorted((r for r in rows if float(r["decision_time"]) > lo and (from_day is None or float(r["decision_time"]) >= from_day)),
                 key=lambda r: (float(r["decision_time"]), r["decision_key"]))
    days: dict[float, list[dict]] = {}
    for r in use:
        days.setdefault(day_of(r["decision_time"]), []).append(r)
    taken: list[dict] = []
    kept_days: list[float] = []
    for d in sorted(days):
        if not all(r["final"] for r in days[d]):
            break
        taken += days[d]
        kept_days.append(d)
        sc = [r for r in taken if r["scorable"]]
        n, k = len(sc), sum(int(r["y"]) for r in sc)
        nd = len({day_of(r["decision_time"]) for r in sc})
        if n >= RULE["min_events"] and k >= RULE["min_per_class"] and n - k >= RULE["min_per_class"] and nd >= RULE["min_effective_days"]:
            return {"state": CLOSED, "after": lo, "from_day": from_day, "first_day": iso(kept_days[0]), "last_day": iso(d),
                    "next_from_day": d + DAY, "rows": taken, "scored": sc}
    sc = [r for r in taken if r["scorable"]]
    k = sum(int(r["y"]) for r in sc)
    return {"state": OPEN, "after": lo, "from_day": from_day, "complete_days": len(kept_days), "scored_n": len(sc), "scored_k": k,
            "scored_days": len({day_of(r["decision_time"]) for r in sc}), "rows": taken, "scored": sc,
            "first_day": iso(kept_days[0]) if kept_days else None, "last_day": iso(kept_days[-1]) if kept_days else None,
            "next_from_day": None}


def admissibility(rows: Sequence[dict], *, freeze: float) -> list[str]:
    """Problems that make a closed window unable to promote (empty list = admissible). Each scored row carries
    `prediction_seq`, `outcome_seq`, `prediction_committed_at` (commit time of the first ledger commit holding the prediction,
    None when not committed), `label_observed_at`, `version_registered_at`, `version_stale` and `decision_time`."""
    out = []
    for r in rows:
        k = str(r["decision_key"])[:12]
        if not float(r["decision_time"]) > float(freeze):
            out.append(f"{k}: decision at or before the recipe freeze")
        if not (isinstance(r.get("prediction_seq"), int) and isinstance(r.get("outcome_seq"), int) and r["prediction_seq"] < r["outcome_seq"]):
            out.append(f"{k}: the prediction does not precede its outcome in the ledger")
        pc, lo = r.get("prediction_committed_at"), r.get("label_observed_at")
        if pc is None or lo is None or not float(pc) < float(lo):
            out.append(f"{k}: the prediction was not committed before its outcome was read")
        reg = r.get("version_registered_at")
        if reg is None or float(reg) > float(r["decision_time"]):
            out.append(f"{k}: the card version was not registered at or before the decision")
        if r.get("version_stale") is not False:
            out.append(f"{k}: the card version was stale or unknown at the decision")
    return out


def replicates(n_search: int, windows: int) -> int:
    s = RULE["skill"]
    if n_search < 1 or windows < 1:
        raise PromotionError("n_search and windows are at least 1")
    return max(int(s["min_replicates"]), int(math.ceil(10 * n_search * windows / s["alpha"])))


def corrected_q(n_search: int, windows: int) -> float:
    return RULE["skill"]["alpha"] / (n_search * windows)


def _boot_lower(y: np.ndarray, p: np.ndarray, r: np.ndarray, groups: Sequence, reps: int, q: float, seed: int) -> float:
    keys = sorted({str(g) for g in groups})
    gi = np.array([keys.index(str(g)) for g in groups])
    G = len(keys)
    sm = np.bincount(gi, weights=(p - y) ** 2, minlength=G)
    sr = np.bincount(gi, weights=(r - y) ** 2, minlength=G)
    rng = np.random.default_rng(seed)
    out = np.empty(reps)
    step = 2000
    for a in range(0, reps, step):
        b = min(reps, a + step)
        idx = rng.integers(0, G, size=(b - a, G))
        cnt = np.zeros((b - a, G))
        np.add.at(cnt, (np.arange(b - a)[:, None], idx), 1.0)
        num, den = cnt @ sm, cnt @ sr
        with np.errstate(divide="ignore", invalid="ignore"):
            out[a:b] = np.where(den > 0, 1.0 - num / den, -np.inf)       # undefined replicate counts against skill
    out.sort()
    kq = max(0, int(math.ceil(q * reps)) - 1)
    return float(out[kq])


def skill_bound(y: Sequence[int], p: Sequence[float], ref: Sequence[float], days: Sequence, mints: Sequence, *, n_search: int,
                windows: int) -> dict:
    y_, p_, r_ = K.check_labels(y), K.check_probs(p), K.check_probs(ref)
    reps, q = replicates(n_search, windows), corrected_q(n_search, windows)
    seed = int(RULE["skill"]["seed"])
    lows = {"decision_day": _boot_lower(y_, p_, r_, days, reps, q, seed),
            "mint": _boot_lower(y_, p_, r_, mints, reps, q, seed + 1)}
    return {"bss": K.brier_skill(y_, p_, r_), "lower_by_unit": lows, "lower": min(lows.values()), "replicates": reps, "q": q,
            "n_search": int(n_search), "windows": int(windows)}


def evaluate_window(win: dict, *, kind: str, freeze: float, n_search: int, windows: int, tests: dict) -> dict:
    """The result of one closed window (`next_window` state CLOSED)."""
    if win.get("state") != CLOSED:
        raise PromotionError("only a closed window is evaluated")
    sc = win["scored"]
    reasons: list[str] = []
    adm = admissibility(sc, freeze=freeze)
    if adm:
        reasons.append("WINDOW_NOT_ADMISSIBLE")
    if not all(tests.get(k) is True for k in ("leakage", "provenance", "contract")):
        reasons.append("TESTS_NOT_PASSED")
    y = np.array([int(r["y"]) for r in sc], float)
    p = np.array([float(r["number"]) for r in sc])
    b0 = np.array([float(r["b0_number"]) if r.get("b0_number") is not None else np.nan for r in sc])
    b2 = np.array([float(r["b2_number"]) if r.get("b2_number") is not None else np.nan for r in sc])
    n, k = len(y), int(y.sum())
    nd = len({day_of(r["decision_time"]) for r in sc})
    if n < RULE["min_events"] or k < RULE["min_per_class"] or n - k < RULE["min_per_class"]:
        reasons.append("BELOW_EVENT_MINIMUM")
    if nd < RULE["min_effective_days"]:
        reasons.append("BELOW_DAY_MINIMUM")
    sk, cal = None, None
    if n and np.all(np.isfinite(b0)):
        sk = skill_bound(y, p, b0, [iso(day_of(r["decision_time"]))[:10] for r in sc], [r["mint"] for r in sc],
                         n_search=n_search, windows=windows)
        if not (math.isfinite(sk["lower"]) and sk["lower"] > RULE["skill"]["lower_bound_gt"]):
            reasons.append("CORRECTED_SKILL_LOWER_BOUND_NOT_ABOVE_0")
    else:
        reasons.append("NO_B0_REFERENCE")
    if n:
        cal = K.calibration_bins(y, p, min_bin=RULE["calibration"]["min_bin_events"], max_bins=RULE["calibration"]["max_bins"])
        if not (cal["in_the_large_ok"] is True and cal["every_bin_ok"] is True):
            reasons.append("CALIBRATION_FAILED")
    b2_ok = None
    if kind == "B2":
        b2_ok = True
    elif n and np.all(np.isfinite(b2)):
        b2_ok = K.brier(y, p) <= K.brier(y, b2)
    return {"state": PASSED if not reasons else FAILED, "reasons": reasons, "admissibility": adm, "n": n, "k": k, "days": nd,
            "first_day": win["first_day"], "last_day": win["last_day"], "skill": sk,
            "calibration": None if cal is None else {"in_the_large_ok": cal["in_the_large_ok"], "every_bin_ok": cal["every_bin_ok"],
                                                       "bins": [{kk: b[kk] for kk in ("n", "positives", "mean_pred", "wilson", "ok")}
                                                                for b in cal["bins"]]},
            "not_worse_than_b2": b2_ok, "rule_sha": C.promotion_rule_sha256()}


def level(results: Sequence[dict], *, role: str) -> dict:
    """The level the window results of one (recipe, kind, target) give, in window order. Recomputed, never given."""
    if role not in ROLES:
        raise PromotionError(f"role {role!r}")
    shadow_at = next((i for i, r in enumerate(results) if r.get("state") == PASSED), None)
    reasons: list[str] = []
    if role == "REFERENCE_BASELINE":
        # PI-D-140 (skeptic finding 3): a reference is never published, so it never reaches SHADOW or VALIDATED_EXPERIMENTAL;
        # its passed windows are reported as a count only
        passed = sum(1 for r in results if r.get("state") == PASSED)
        reasons.append("NO_PROSPECTIVE_WINDOW_PASSED" if not passed else f"PASSED_WINDOWS_{passed}_REFERENCE_ONLY")
        reasons.append("REFERENCE_BASELINE_NEVER_PUBLISHED")
        return {"level": "ABSTAIN", "reasons": reasons, "windows": len(results), "passed_windows": passed,
                "rule_sha": C.promotion_rule_sha256()}
    if shadow_at is None:
        lv = "ABSTAIN" if role == "REFERENCE_BASELINE" else "NO_GO"
        reasons.append("NO_PROSPECTIVE_WINDOW_PASSED" if results else "NO_PROSPECTIVE_WINDOW_CLOSED")
        reasons.append("REFERENCE_BASELINE_NEVER_PUBLISHED" if lv == "ABSTAIN" else "NO_INCREMENTAL_PREDICTIVE_EDGE")
        return {"level": lv, "reasons": reasons, "windows": len(results), "rule_sha": C.promotion_rule_sha256()}
    ve = any(r.get("state") == PASSED and r.get("not_worse_than_b2") is True for r in results[shadow_at + 1:])
    if not ve:
        reasons.append("NO_SECOND_PROSPECTIVE_WINDOW_PASSED")
    return {"level": "VALIDATED_EXPERIMENTAL" if ve else "SHADOW", "reasons": reasons, "windows": len(results),
            "shadow_window": shadow_at, "rule_sha": C.promotion_rule_sha256()}


# ---------------------------------------------------------------- the CM-2 registry: entries and an append-only log
ENTRY_KEYS = ("entry_kind", "recipe_id", "version", "kind", "target", "role", "model_id", "model_sha", "card_path",
              "card_file_sha256", "training_cutoff", "training_cutoff_utc", "registry_sha", "governing_sha", "n_train", "k_train",
              "n_used", "k_used", "label_set_sha", "data_snapshot_sha", "level", "level_reasons", "tests", "is_fixture")


def make_entry(**kw: Any) -> dict:
    miss = [k for k in ENTRY_KEYS if k not in kw]
    if miss:
        raise LogError(f"entry lacks {miss}")
    extra = [k for k in kw if k not in ENTRY_KEYS]
    if extra:
        raise LogError(f"entry has unknown fields {extra}")
    if kw["level"] not in LEVELS or kw["role"] not in ROLES:
        raise LogError("level or role not allowed")
    if kw["level"] in PUBLISHABLE:
        raise LogError("an entry is registered at ABSTAIN or NO_GO; a publishable level comes only from closed windows")
    e = {k: kw[k] for k in ENTRY_KEYS}
    e["entry_id"] = sha(e)
    return e


def verify_entry(e: dict) -> dict:
    if e.get("entry_id") != sha({k: v for k, v in e.items() if k != "entry_id"}):
        raise LogError("entry content does not match its id")
    return e


def _event_id(ev: dict) -> str:
    return sha({k: v for k, v in ev.items() if k != "event_id"})


def _line_sha(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()


def read_log(text: str) -> list[dict]:
    if text and not text.endswith("\n"):
        raise LogError("log does not end with a newline")
    events, prev, last = [], GENESIS, -math.inf
    for i, line in enumerate(text.splitlines()):
        ev = json.loads(line)
        if canon(ev) != line:
            raise LogError(f"line {i}: not canonical")
        if ev.get("seq") != i or ev.get("prev") != prev or ev.get("event_id") != _event_id(ev):
            raise LogError(f"line {i}: chain broken")
        if ev.get("kind") not in EVENT_KINDS:
            raise LogError(f"line {i}: unknown kind")
        t = C.parse_utc(ev["as_of_utc"])
        if t < last:
            raise LogError(f"line {i}: earlier than the event before it")
        last, prev = t, _line_sha(line)
        events.append(ev)
    return events


def _check_event(ev: dict, known: dict[str, dict], retired: set[str], levels: dict[str, str] | None = None) -> None:
    levels = {} if levels is None else levels
    k = ev["kind"]
    if k == "REGISTER":
        e = verify_entry(ev["entry"])
        if e["entry_id"] in known:
            raise LogError("an entry is registered once")
        known[e["entry_id"]] = e
    elif k == "RETIRE":
        if not ev.get("entry_ids") or not ev.get("reason") or not ev.get("source_log_sha256"):
            raise LogError("RETIRE names the entries, the reason and the log they come from")
        for i in ev["entry_ids"]:
            if i in retired:
                raise LogError("an entry is retired once")
            retired.add(i)
    elif k == "PROMOTE":
        # PI-D-140: a CANDIDATE entry reaches a publishable level only through the window results that give it
        e = known.get(ev.get("entry_id"))
        if e is None or ev["entry_id"] in retired:
            raise LogError("PROMOTE names a registered, unretired entry")
        if e["role"] != "CANDIDATE":
            raise LogError("a reference is never promoted")
        if ev.get("level") not in PUBLISHABLE:
            raise LogError("PROMOTE gives SHADOW or VALIDATED_EXPERIMENTAL")
        res = ev.get("window_results")
        if not isinstance(res, list) or level(res, role="CANDIDATE")["level"] != ev["level"]:
            raise LogError("the level is not the one its window results give")
        levels[ev["entry_id"]] = ev["level"]
    elif k == "PIN":
        if ev.get("mode") not in PIN_MODES or not ev.get("target"):
            raise LogError("PIN needs a mode and a target")
        refs = ev.get("references") or {}
        if set(refs) != {"B0", "B2"}:
            raise LogError("a PIN names B0 and B2 references")
        for kind, i in refs.items():
            e = known.get(i)
            if e is None or e["kind"] != kind or e["target"] != ev["target"] or i in retired:
                raise LogError("a PIN reference must be a registered, unretired entry of that kind and target")
        if ev["mode"] == "CHAMPION":
            ch = known.get(ev.get("champion"))
            if ch is None or ev["champion"] in retired or ch["target"] != ev["target"] or levels.get(ev["champion"]) not in PUBLISHABLE:
                raise LogError("a CHAMPION pin needs a registered entry at a publishable level")
        elif ev.get("champion") is not None:
            raise LogError("NO_VIABLE_CHAMPION names no champion")


def state(events: Sequence[dict]) -> dict:
    known: dict[str, dict] = {}
    retired: set[str] = set()
    pins: dict[str, dict] = {}
    levels: dict[str, str] = {}
    for ev in events:
        _check_event(ev, known, retired, levels)
        if ev["kind"] == "PIN":
            pins[ev["target"]] = ev
    return {"entries": known, "retired": retired, "pins": pins, "levels": levels}


def append_events(path: str | Path, payloads: Sequence[dict], *, expect_sha: str | None) -> list[dict]:
    p = Path(path)
    cur = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if cur != expect_sha:
        raise LogError("the log changed since it was read")
    old = p.read_text() if p.exists() else ""
    events = read_log(old)
    st = state(events)
    prev = _line_sha(canon(events[-1])) if events else GENESIS
    out, last = [], (C.parse_utc(events[-1]["as_of_utc"]) if events else -math.inf)
    for i, pl in enumerate(payloads):
        if pl.get("kind") not in EVENT_KINDS or not isinstance(pl.get("as_of_utc"), str):
            raise LogError("an event needs a known kind and as_of_utc")
        if C.parse_utc(pl["as_of_utc"]) < last:
            raise LogError("an appended event is earlier than the last event")
        ev = {**{k: v for k, v in pl.items() if k not in ("seq", "prev", "event_id")}, "seq": len(events) + i, "prev": prev}
        ev["event_id"] = _event_id(ev)
        _check_event(ev, st["entries"], st["retired"], st["levels"])
        out.append(ev)
        prev, last = _line_sha(canon(ev)), C.parse_utc(ev["as_of_utc"])
    with open(p, "a") as f:
        for ev in out:
            f.write(canon(ev) + "\n")
    read_log(p.read_text())
    return out

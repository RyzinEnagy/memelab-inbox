"""CM-2 (PI-D-122): promotion from prospective evidence and the CM-2 registry log (memelab/predictive/promotion.py).

Synthetic windows only; no network, no clock, temp files. Each test guards one rule of contract.PROMOTION_CM2.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from memelab.predictive import contract as C
from memelab.predictive import promotion as P

ROOT = Path(__file__).resolve().parent.parent
FREEZE = C.parse_utc("2026-11-10T01:13:46Z")
D0 = P.day_of(FREEZE) + 86400.0                 # first full day after the freeze


def rows(*, days=10, per_day=20, skill=True, start=D0, freeze_ok=True, tag="a"):
    """per_day decisions a day: half with p 0.1 (10% positive), half with p 0.7 (70% positive), B0 0.4, B2 equal to p.
    The positives are spread so that every quantile bin is calibrated (see the module docstring of the test)."""
    out = []
    lo = hi = 0
    for d in range(days):
        for j in range(per_day):
            high = j % 2 == 1
            if high:
                y = 1 if hi % 10 < 7 else 0
                hi += 1
            else:
                y = 1 if lo % 10 == 0 else 0
                lo += 1
            p = (0.7 if high else 0.1) if skill else (0.1 if high else 0.7)
            t = start + d * 86400.0 + 600.0 + j * 60.0
            if not freeze_ok:
                t = FREEZE - 10.0
            out.append({"decision_key": f"{tag}{d:02d}{j:02d}", "decision_time": t, "mint": f"M{tag}{d}{j}", "final": True,
                        "scorable": True, "y": y, "number": p, "b0_number": 0.4, "b2_number": p, "prediction_seq": 2 * (d * 100 + j),
                        "outcome_seq": 2 * (d * 100 + j) + 1, "prediction_committed_at": t + 3600.0, "label_observed_at": t + 7 * 86400.0,
                        "version_registered_at": FREEZE, "version_stale": False, "entry_id": "e1"})
    return out


TESTS_OK = {"leakage": True, "provenance": True, "contract": True}


def closed(rs, after=FREEZE, from_day=None):
    w = P.next_window(rs, after=after, from_day=from_day)
    assert w["state"] == P.CLOSED, {k: w.get(k) for k in ("scored_n", "scored_k", "scored_days", "complete_days")}
    return w


def test_a_window_closes_at_the_first_complete_day_that_meets_every_count_minimum():
    # 20 a day: 50 events after 3 days, but the 5-day minimum holds the window open until day 5 (100 events)
    w = closed(rows(days=10, per_day=20))
    assert len(w["scored"]) == 100 and w["first_day"] == P.iso(D0) and w["last_day"] == P.iso(D0 + 4 * 86400)
    assert w["next_from_day"] == D0 + 5 * 86400
    # 6 a day: 5 days give 30 events; the event minimum closes it on day 9 (54 events, 10 or more per class)
    w = closed(rows(days=12, per_day=6))
    assert len(w["scored"]) == 54 and w["last_day"] == P.iso(D0 + 8 * 86400)
    assert sum(r["y"] for r in w["scored"]) >= 10 and sum(1 - r["y"] for r in w["scored"]) >= 10


def test_counts_below_the_frozen_minimums_never_close_a_window():
    assert P.next_window(rows(days=4, per_day=20), after=FREEZE)["state"] == P.OPEN          # 80 events, 4 days
    few = rows(days=10, per_day=4)                                                             # 40 events over 10 days
    assert P.next_window(few, after=FREEZE)["state"] == P.OPEN
    neg = [dict(r, y=0) for r in rows(days=10, per_day=20)]                                   # no positive class
    w = P.next_window(neg, after=FREEZE)
    assert w["state"] == P.OPEN and w["scored_k"] == 0


def test_an_incomplete_day_stops_the_window_so_a_late_outcome_cannot_reshape_it():
    rs = rows(days=10, per_day=12)
    rs[30]["final"] = False                       # day 2 has a PENDING outcome
    w = P.next_window(rs, after=FREEZE)
    assert w["state"] == P.OPEN and w["complete_days"] == 2


def test_decisions_at_or_before_the_freeze_and_before_from_day_are_not_in_the_window():
    rs = rows(days=10, per_day=12)
    w = P.next_window([dict(r, decision_time=FREEZE) for r in rs], after=FREEZE)
    assert w["state"] == P.OPEN and w["rows"] == []
    w = P.next_window(rs, after=FREEZE, from_day=D0 + 5 * 86400)
    assert all(r["decision_time"] >= D0 + 5 * 86400 for r in w["rows"])


def test_a_skilled_calibrated_window_passes_and_gives_shadow():
    w = closed(rows(days=10, per_day=20))
    out = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.PASSED, out["reasons"]
    assert out["skill"]["replicates"] == 26000 and out["skill"]["lower"] > 0 and out["calibration"]["every_bin_ok"]
    assert P.level([out], role="REFERENCE_BASELINE")["level"] == "SHADOW"


def test_no_skill_fails_on_the_corrected_lower_bound():
    w = closed(rows(days=10, per_day=20, skill=False))
    out = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "CORRECTED_SKILL_LOWER_BOUND_NOT_ABOVE_0" in out["reasons"]
    assert P.level([out], role="REFERENCE_BASELINE")["level"] == "ABSTAIN"
    assert P.level([out], role="CANDIDATE")["level"] == "NO_GO"


def test_b0_against_itself_never_passes():
    w = closed([dict(r, number=0.4) for r in rows(days=10, per_day=20)])
    out = P.evaluate_window(w, kind="B0", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "CORRECTED_SKILL_LOWER_BOUND_NOT_ABOVE_0" in out["reasons"]


def test_the_selection_correction_uses_the_cumulative_search_size_and_the_windows_tried():
    assert P.replicates(130, 1) == 26000 and P.replicates(130, 2) == 52000 and P.replicates(1, 1) == 2000
    assert P.corrected_q(130, 2) == pytest.approx(0.05 / 260)
    w = closed(rows(days=10, per_day=20))
    a = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=1, windows=1, tests=TESTS_OK)["skill"]["lower"]
    b = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)["skill"]["lower"]
    assert b < a                                   # a larger search makes the bound more conservative, never looser


def test_a_miscalibrated_window_fails_even_with_skill():
    rs = [dict(r, number=min(0.99, r["number"] + 0.2)) for r in rows(days=10, per_day=20)]
    out = P.evaluate_window(closed(rs), kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert "CALIBRATION_FAILED" in out["reasons"] and out["state"] == P.FAILED


@pytest.mark.parametrize("field,value", [("prediction_committed_at", None), ("prediction_committed_at", "late"),
                                         ("outcome_seq", "before"), ("version_registered_at", "after"), ("version_stale", True),
                                         ("version_stale", None)])
def test_admissibility_refuses_every_breach_of_the_phase_19_discipline(field, value):
    rs = rows(days=10, per_day=20)
    r0 = rs[0]
    if value == "late":
        r0[field] = r0["label_observed_at"] + 1
    elif value == "before":
        r0[field] = r0["prediction_seq"] - 1
    elif value == "after":
        r0[field] = r0["decision_time"] + 1
    else:
        r0[field] = value
    out = P.evaluate_window(closed(rs), kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "WINDOW_NOT_ADMISSIBLE" in out["reasons"] and len(out["admissibility"]) == 1


def test_a_decision_at_the_freeze_is_inadmissible_even_inside_a_closed_window():
    w = closed(rows(days=10, per_day=20))
    w = copy.deepcopy(w)
    w["scored"][0]["decision_time"] = FREEZE
    out = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert "WINDOW_NOT_ADMISSIBLE" in out["reasons"]


def test_failed_card_tests_block_promotion():
    w = closed(rows(days=10, per_day=20))
    out = P.evaluate_window(w, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=dict(TESTS_OK, leakage=False))
    assert "TESTS_NOT_PASSED" in out["reasons"]


def test_validated_experimental_needs_a_second_later_window_and_b2_parity():
    rs = rows(days=20, per_day=40)      # the second window carries a stricter bound (alpha / 260), so more events
    w1 = closed(rs)
    r1 = P.evaluate_window(w1, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    w2 = closed(rs, from_day=w1["next_from_day"])
    assert P.day_of(w2["scored"][0]["decision_time"]) > P.day_of(w1["scored"][-1]["decision_time"])
    r2 = P.evaluate_window(w2, kind="B2", freeze=FREEZE, n_search=130, windows=2, tests=TESTS_OK)
    assert r1["state"] == r2["state"] == P.PASSED
    assert P.level([r1], role="REFERENCE_BASELINE")["level"] == "SHADOW"
    assert P.level([r1, r2], role="REFERENCE_BASELINE")["level"] == "VALIDATED_EXPERIMENTAL"
    # a candidate worse than B2 on the second window stays at SHADOW
    worse = [dict(r, b2_number=r["y"] * 0.98 + 0.01) for r in rs]
    r2c = P.evaluate_window(closed(worse, from_day=w1["next_from_day"]), kind="C1", freeze=FREEZE, n_search=130, windows=2, tests=TESTS_OK)
    assert r2c["not_worse_than_b2"] is False
    assert P.level([r1, r2c], role="CANDIDATE")["level"] == "SHADOW"
    # the same passed window twice is not a second window: order matters, a pass before SHADOW does not count
    assert P.level([r1], role="CANDIDATE")["level"] == "SHADOW"


def test_only_a_closed_window_is_evaluated():
    with pytest.raises(P.PromotionError):
        P.evaluate_window(P.next_window(rows(days=2), after=FREEZE), kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)


# ---------------------------------------------------------------- the CM-2 registry log
def entry(kind="B2", target=C.PRIMARY[0], level="ABSTAIN", version=1):
    return P.make_entry(entry_kind="CM2_CARD", recipe_id="R-CM2-1", version=version, kind=kind, target=target, role="REFERENCE_BASELINE",
                        model_id=f"{kind}:{target}", model_sha="a" * 64, card_path="x.json", card_file_sha256="b" * 64,
                        training_cutoff=1.0, training_cutoff_utc="1970-01-01T00:00:01Z", registry_sha=C.registry_sha256(),
                        governing_sha=C.governing_sha256(), n_train=1, k_train=0, n_used=1, k_used=0, label_set_sha="c" * 64,
                        data_snapshot_sha="d" * 64, level=level, level_reasons=[], tests=TESTS_OK, is_fixture=True)


def test_registry_log_retire_register_pin_and_refusals(tmp_path):
    log = tmp_path / "REGISTRY_LOG.jsonl"
    b0, b2 = entry("B0"), entry("B2")
    t = C.PRIMARY[0]
    ev = P.append_events(log, [{"kind": "RETIRE", "as_of_utc": "2026-11-10T01:00:00Z", "entry_ids": ["old1", "old2"],
                                "source_log_sha256": "e" * 64, "reason": "stale"},
                               {"kind": "REGISTER", "as_of_utc": "2026-11-10T01:00:00Z", "entry": b0},
                               {"kind": "REGISTER", "as_of_utc": "2026-11-10T01:00:00Z", "entry": b2},
                               {"kind": "PIN", "as_of_utc": "2026-11-10T01:00:00Z", "target": t, "mode": "NO_VIABLE_CHAMPION",
                                "champion": None, "references": {"B0": b0["entry_id"], "B2": b2["entry_id"]}}], expect_sha=None)
    assert [e["kind"] for e in ev] == ["RETIRE", "REGISTER", "REGISTER", "PIN"]
    st = P.state(P.read_log(log.read_text()))
    assert st["retired"] == {"old1", "old2"} and st["pins"][t]["mode"] == "NO_VIABLE_CHAMPION"
    import hashlib
    sha = hashlib.sha256(log.read_bytes()).hexdigest()
    bad = [{"kind": "PIN", "as_of_utc": "2026-11-10T02:00:00Z", "target": t, "mode": "NO_VIABLE_CHAMPION", "champion": None,
            "references": {"B0": "old1", "B2": b2["entry_id"]}},                                          # a retired reference
           {"kind": "PIN", "as_of_utc": "2026-11-10T02:00:00Z", "target": t, "mode": "CHAMPION", "champion": b2["entry_id"],
            "references": {"B0": b0["entry_id"], "B2": b2["entry_id"]}},                                  # champion below SHADOW
           {"kind": "REGISTER", "as_of_utc": "2026-11-10T02:00:00Z", "entry": b0},                         # twice
           {"kind": "RETIRE", "as_of_utc": "2026-11-10T02:00:00Z", "entry_ids": ["old1"], "source_log_sha256": "e" * 64,
            "reason": "again"},                                                                           # retired twice
           {"kind": "PIN", "as_of_utc": "2026-11-09T00:00:00Z", "target": t, "mode": "NO_VIABLE_CHAMPION", "champion": None,
            "references": {"B0": b0["entry_id"], "B2": b2["entry_id"]}},                                  # earlier than the log
           {"kind": "DELETE", "as_of_utc": "2026-11-10T02:00:00Z"}]
    for b in bad:
        with pytest.raises((P.LogError, C.ContractError)):
            P.append_events(log, [b], expect_sha=sha)
        assert hashlib.sha256(log.read_bytes()).hexdigest() == sha                                       # nothing written
    with pytest.raises(P.LogError, match="changed"):
        P.append_events(log, [], expect_sha="0" * 64)
    lines = log.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["entry"]["level"] = "SHADOW"
    with pytest.raises(P.LogError):
        P.read_log("\n".join([lines[0], C.canon(tampered)] + lines[2:]) + "\n")
    with pytest.raises(P.LogError):
        P.read_log("\n".join(lines[1:]) + "\n")                                                              # a dropped line


def test_an_entry_is_never_registered_at_a_publishable_level():
    with pytest.raises(P.LogError, match="publishable"):
        entry(level="SHADOW")
    e = entry()
    with pytest.raises(P.LogError):
        P.verify_entry(dict(e, level="NO_GO"))


def test_promotion_imports_numpy_the_standard_library_contract_and_stats_only_and_nothing_imports_it():
    src = (ROOT / "memelab/predictive/promotion.py").read_text()
    tree = ast.parse(src)
    absolute = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    absolute |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module}
    rel = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert absolute <= {"__future__", "hashlib", "json", "math", "datetime", "pathlib", "typing", "numpy"}
    assert rel == {"contract", "stats"}
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "promotion.py" and p.parent.name == "predictive":
            continue
        t = p.read_text()
        assert "promotion" not in {a.name for n in ast.walk(ast.parse(t)) if isinstance(n, ast.ImportFrom) for a in n.names}, p
        assert "predictive.promotion" not in t, p

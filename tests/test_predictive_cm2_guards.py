"""CM-2 (PI-D-126): tests added after the mutation probe of 2026-11-10 (probes/mutation_probe.py) showed guards of the frozen
code that no test exercised. The frozen code is unchanged; these tests only pin what it already does.

No network (the one end-to-end case runs the daily script with --max-calls 0 and --no-fetch), temp files, fixed clocks.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import promotion as P
from test_predictive_daily import _git, _run, clone  # noqa: F401 (module-scoped fixture reused)
from test_predictive_promotion import FREEZE, TESTS_OK, closed, rows

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "audits/predictive-intelligence/daily/predictive_daily.py"


def _load():
    spec = importlib.util.spec_from_file_location("predictive_daily_g", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load()


# ---------------------------------------------------------------- promotion.py (survivors P03, P13, P14, P20)
def test_a_window_closes_at_exactly_50_events_and_not_at_49():
    rs = rows(days=5, per_day=10)                       # 50 events over 5 days, both classes at least 10
    w = P.next_window(rs, after=FREEZE)
    k = sum(r["y"] for r in rs)
    assert k >= 10 and 50 - k >= 10
    assert w["state"] == P.CLOSED and len(w["scored"]) == 50
    w49 = P.next_window(rs[1:], after=FREEZE)           # one event fewer, nothing else changed
    assert w49["state"] == P.OPEN and w49["scored_n"] == 49


def test_evaluate_refuses_a_closed_window_below_the_event_or_day_minimum_on_its_own():
    w = closed(rows(days=10, per_day=20))
    few = dict(w, scored=w["scored"][:40])              # 40 events (2 days): the evaluation checks the counts again
    out = P.evaluate_window(few, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "BELOW_EVENT_MINIMUM" in out["reasons"]
    four = dict(w, scored=[r for r in w["scored"] if r["decision_time"] < P.day_of(w["scored"][0]["decision_time"]) + 4 * 86400])
    assert len(four["scored"]) == 80
    out = P.evaluate_window(four, kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "BELOW_DAY_MINIMUM" in out["reasons"] and "BELOW_EVENT_MINIMUM" not in out["reasons"]


def test_a_bootstrap_replicate_with_an_undefined_skill_counts_against_skill():
    y = np.array([0.0, 1.0, 0.0, 1.0])
    p = np.array([0.2, 0.8, 0.2, 0.8])
    low = P._boot_lower(y, p, y.copy(), ["d"] * 4, 200, 0.01, 7)   # the reference is perfect: every replicate is undefined
    assert low == -math.inf


# ---------------------------------------------------------------- the daily cycle (survivors D01, D02, D05)
def test_the_daily_cycle_refuses_a_recipe_or_governing_fingerprint_that_differs_from_its_pin(monkeypatch):
    assert D.recipe()["recipe_id"] == "R-CM2-1"
    monkeypatch.setattr(D, "RECIPE_SHA256", "0" * 64)
    with pytest.raises(D.Fail) as e:
        D.recipe()
    assert e.value.reason == "PREFLIGHT_FAILED" and "RECIPE.json" in e.value.detail
    monkeypatch.undo()
    monkeypatch.setattr(D, "GOVERNING_SHA", "0" * 64)
    with pytest.raises(D.Fail) as e:
        D.recipe()
    assert e.value.reason == "PREFLIGHT_FAILED" and "governing" in e.value.detail


def test_no_commit_mode_refuses_a_planned_label_read_without_calling(clone, tmp_path):  # noqa: F811
    import subprocess
    c2 = tmp_path / "c2"
    subprocess.run(["git", "clone", "-q", str(clone["c"]), str(c2)], check=True, capture_output=True)
    _git(c2, "fetch", "-q", str(clone["c"]), "fake:refs/heads/fake")
    _git(c2, "config", "user.email", "test@localhost")
    _git(c2, "config", "user.name", "test")
    cl = dict(clone, c=c2, state=tmp_path / "s2")
    led = c2 / "audits/predictive-intelligence/daily/LEDGER.jsonl"
    if not led.exists():                                # predictions first (committed), as a scheduled run would
        r = _run(cl, "--now", str(clone["t_exp"] + 600))
        assert r.returncode == 0, r.stderr[-1500:]
    before = led.read_text()
    r = _run(cl, "--now", str(clone["t_exp"] + 7 * 3600), "--no-commit", "--max-calls", "0")
    assert r.returncode == D.EXIT["LABEL_FETCH_FAILED"] and "reads are disabled" in r.stderr
    assert led.read_text() == before
    calls = c2 / "audits/predictive-intelligence/daily/CALLS.jsonl"
    assert not calls.exists() or calls.read_text() == ""

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

from memelab.predictive import contract as C
from memelab.predictive import monitoring as M
from memelab.predictive import promotion as P
from test_predictive_daily import _anchor, _git, _run, clone  # noqa: F401 (module-scoped fixture reused)
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


# ---------------------------------------------------------------- PI-D-128: a failed run never commits a ledger that fails verify
def test_a_run_that_stops_on_a_broken_working_ledger_does_not_commit_it(clone, tmp_path):  # noqa: F811
    import subprocess
    c3 = tmp_path / "c3"
    subprocess.run(["git", "clone", "-q", str(clone["c"]), str(c3)], check=True, capture_output=True)
    _git(c3, "fetch", "-q", str(clone["c"]), "fake:refs/heads/fake")
    _git(c3, "config", "user.email", "test@localhost")
    _git(c3, "config", "user.name", "test")
    cl = dict(clone, c=c3, state=tmp_path / "s3")
    rel = "audits/predictive-intelligence/daily/LEDGER.jsonl"
    led = c3 / rel
    if not led.exists():
        r = _run(cl, "--now", str(clone["t_exp"] + 600))
        assert r.returncode == 0, r.stderr[-1500:]
    committed = _git(c3, "show", f"HEAD:{rel}")
    broken = committed + committed.splitlines()[-1] + "\n"       # an appended line whose chain does not verify
    led.write_text(broken)
    r = _run(cl, "--now", str(clone["t_exp"] + 900))
    assert r.returncode == D.EXIT["PREFLIGHT_FAILED"] and "PREFLIGHT_FAILED" in r.stderr
    assert _git(c3, "show", f"HEAD:{rel}") == committed               # the broken ledger is not committed
    assert led.read_text() == broken                                    # and is left in place for a person to look at
    head = _git(c3, "show", "HEAD:audits/predictive-intelligence/daily/STATUS.json")
    assert "PREFLIGHT_FAILED" in head                                   # the failed run's record is committed


# ---------------------------------------------------------------- PI-D-140: the repair pass after the skeptic review of cdff266
def _scratch_ledger_repo(tmp_path, monkeypatch, rewrite: bool):
    """CX-CM2-1 (skeptic counterexample): 2 predictions committed at T1, outcome read at T_READ, then a commit at T3 that either
    rewrites the ledger with a fresh valid chain (rewrite=True) or appends one outcome line (rewrite=False)."""
    import os
    import subprocess
    repo = tmp_path / "r"
    (repo / D.REL).mkdir(parents=True)
    led = repo / D.REL / "LEDGER.jsonl"

    def g(*a, t):
        env = dict(os.environ, GIT_COMMITTER_DATE=f"@{t} +0000", GIT_AUTHOR_DATE=f"@{t} +0000")
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=x", "-c", "user.email=x@x", "-c", "commit.gpgsign=false", *a],
                       check=True, capture_output=True, env=env)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    T1, T3 = 1_800_000_000, 1_800_001_200
    M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.10, "recorded_at": 0.0}])
    M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.11, "recorded_at": 1.0}])
    g("add", "-A", t=T1)
    g("commit", "-q", "-m", "predictions", t=T1)
    if rewrite:
        led.unlink()
        M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.90, "recorded_at": 0.0}])
        M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.91, "recorded_at": 1.0}])
    M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_OUTCOME", "recorded_at": 2.0}])
    g("add", "-A", t=T3)
    g("commit", "-q", "-m", "later", t=T3)
    monkeypatch.setattr(D, "REPO", repo)
    return T1, T3


def test_cx_cm2_1_a_ledger_rewritten_in_a_later_commit_gives_no_anchor_and_every_window_is_inadmissible(tmp_path, monkeypatch):
    T1, T3 = _scratch_ledger_repo(tmp_path, monkeypatch, rewrite=True)
    assert M.verify(D.REPO / D.REL / "LEDGER.jsonl")["ok"]                     # the rewrite is a valid chain on its own
    first, problems = D.ledger_history()
    assert problems and problems[0].startswith("LEDGER_HISTORY_NOT_APPEND_ONLY")
    ct = D.commit_times()
    assert ct == {}
    rows = [{"decision_key": f"k{i}", "decision_time": 1.0e9 + i, "prediction_seq": i, "outcome_seq": 2,
             "prediction_committed_at": ct.get(i), "label_observed_at": T1 + 600, "version_registered_at": 0.0, "version_stale": False}
            for i in (0, 1)]
    assert len(P.admissibility(rows, freeze=0.0)) == 2


def test_an_append_only_history_anchors_each_line_by_its_content(tmp_path, monkeypatch):
    T1, T3 = _scratch_ledger_repo(tmp_path, monkeypatch, rewrite=False)
    assert D.ledger_history()[1] == []
    assert D.commit_times() == {0: float(T1), 1: float(T1), 2: float(T3)}


def test_evaluate_refuses_a_closed_window_below_the_negative_class_minimum_on_its_own():
    w = closed(rows(days=10, per_day=40))
    pos = [r for r in w["scored"] if r["y"] == 1]
    neg = [r for r in w["scored"] if r["y"] == 0][:5]
    assert len(pos) >= 50 and len({P.day_of(r["decision_time"]) for r in pos + neg}) >= 5
    out = P.evaluate_window(dict(w, scored=pos + neg), kind="B2", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)
    assert out["state"] == P.FAILED and "BELOW_EVENT_MINIMUM" in out["reasons"] and out["k"] == len(pos)


def test_window_results_belong_to_one_recipe():
    from types import SimpleNamespace
    t = C.PRIMARY[0]
    mk = lambda rid: {"payload": {"kind": "MONITOR", "monitor": "WINDOW_RESULT", "target": t, "kind_model": "B2", "recipe_id": rid,
                                  "result": {"state": P.PASSED, "rid": rid}}}
    idx = SimpleNamespace(entries=[mk("R-CM2-1"), mk("R-OTHER")])
    assert [r["rid"] for r in D.window_results(idx, t, "B2", "R-CM2-1")] == ["R-CM2-1"]
    assert [r["rid"] for r in D.window_results(idx, t, "B2", "R-NEW")] == []


def _entry(kind, role, target):
    return P.make_entry(entry_kind="CM2_CARD", recipe_id="R-FIX", version=1, kind=kind, target=target, role=role,
                        model_id=f"{kind}:{target}", model_sha="a" * 64, card_path="x.json", card_file_sha256="b" * 64,
                        training_cutoff=1.0, training_cutoff_utc="1970-01-01T00:00:01Z", registry_sha=C.registry_sha256(),
                        governing_sha=C.governing_sha256(), n_train=1, k_train=0, n_used=1, k_used=0, label_set_sha="c" * 64,
                        data_snapshot_sha="d" * 64, level="NO_GO" if role == "CANDIDATE" else "ABSTAIN", level_reasons=[],
                        tests=TESTS_OK, is_fixture=True)


def test_a_candidate_can_be_promoted_and_pinned_champion_but_a_reference_never(tmp_path):
    t = C.PRIMARY[0]
    b0, b2, c1 = _entry("B0", "REFERENCE_BASELINE", t), _entry("B2", "REFERENCE_BASELINE", t), _entry("C1", "CANDIDATE", t)
    log = tmp_path / "LOG.jsonl"
    at = "2026-11-20T00:00:00Z"
    P.append_events(log, [{"kind": "REGISTER", "as_of_utc": at, "entry": e} for e in (b0, b2, c1)], expect_sha=None)
    w = closed(rows(days=10, per_day=20))
    res = [P.evaluate_window(w, kind="C1", freeze=FREEZE, n_search=130, windows=1, tests=TESTS_OK)]
    assert res[0]["state"] == P.PASSED
    import hashlib
    sha = lambda: hashlib.sha256(log.read_bytes()).hexdigest()
    refs = {"B0": b0["entry_id"], "B2": b2["entry_id"]}
    for bad in ({"kind": "PROMOTE", "as_of_utc": at, "entry_id": b2["entry_id"], "level": "SHADOW", "window_results": res},
                {"kind": "PROMOTE", "as_of_utc": at, "entry_id": c1["entry_id"], "level": "VALIDATED_EXPERIMENTAL", "window_results": res},
                {"kind": "PROMOTE", "as_of_utc": at, "entry_id": c1["entry_id"], "level": "SHADOW", "window_results": []},
                {"kind": "PIN", "as_of_utc": at, "target": t, "mode": "CHAMPION", "champion": c1["entry_id"], "references": refs}):
        s = sha()
        with pytest.raises(P.LogError):
            P.append_events(log, [bad], expect_sha=s)
        assert sha() == s
    # the daily cycle's payloads for a CANDIDATE kind that reached SHADOW are accepted by the log
    reg = P.state(P.read_log(log.read_text()))
    reg["registered_at"] = {e["entry_id"]: 0.0 for e in (b0, b2, c1)}
    lv = P.level(res, role="CANDIDATE")
    pl = D.promotion_payloads(reg, {"recipe_id": "R-FIX"}, t, "C1", res, lv, C.parse_utc(at))
    assert [p["kind"] for p in pl] == ["PROMOTE", "PIN"] and pl[1]["mode"] == "CHAMPION"
    P.append_events(log, pl, expect_sha=sha())
    st = P.state(P.read_log(log.read_text()))
    assert st["levels"] == {c1["entry_id"]: "SHADOW"} and st["pins"][t]["champion"] == c1["entry_id"]
    reg2 = dict(st, registered_at=reg["registered_at"])
    assert D.promotion_payloads(reg2, {"recipe_id": "R-FIX"}, t, "C1", res, lv, C.parse_utc(at)) == []   # once only


def test_now_is_refused_outside_tests_and_max_calls_is_capped_at_60(monkeypatch, capsys):
    monkeypatch.delenv("PREDICTIVE_DAILY_TEST_CLOCK", raising=False)
    assert D.main(["run", "--now", "1800000000"]) == D.EXIT["PREFLIGHT_FAILED"]
    assert "tests only" in capsys.readouterr().err
    assert D.main(["run", "--max-calls", "61"]) == D.EXIT["PREFLIGHT_FAILED"] and D.MAX_CALLS == 60


def _clone2(clone, tmp_path, name):
    import subprocess
    c = tmp_path / name
    subprocess.run(["git", "clone", "-q", str(clone["c"]), str(c)], check=True, capture_output=True)
    _git(c, "fetch", "-q", str(clone["c"]), "fake:refs/heads/fake")
    _git(c, "config", "user.email", "test@localhost")
    _git(c, "config", "user.name", "test")
    return dict(clone, c=c, state=tmp_path / (name + "_s"))


def test_a_run_refuses_a_head_that_is_not_the_branch(clone, tmp_path):  # noqa: F811
    cl = _clone2(clone, tmp_path, "c5")
    _git(cl["c"], "checkout", "-q", "--detach")
    r = _run(cl, "--now", str(clone["t_exp"] + 600))
    assert r.returncode == D.EXIT["PREFLIGHT_FAILED"] and "is not the branch feature/predictive-intelligence" in r.stderr


def test_predictions_are_pushed_before_any_read_and_a_failed_push_stops_the_reads(clone, tmp_path):  # noqa: F811
    cl = _clone2(clone, tmp_path, "c6")
    rel = "audits/predictive-intelligence/daily/LEDGER.jsonl"
    if not (cl["c"] / rel).exists():
        r = _run(cl, "--now", str(clone["t_exp"] + 600))
        assert r.returncode == 0, r.stderr[-1500:]
    bare = _anchor(cl["c"])
    pushed = _git(Path(bare), "rev-parse", "refs/heads/feature/predictive-intelligence").strip()
    assert _git(Path(bare), "show", f"{pushed}:{rel}") == (cl["c"] / rel).read_text()        # the ledger is on the remote
    before = (cl["c"] / rel).read_text()
    r = _run(cl, "--now", str(clone["t_exp"] + 7 * 3600), "--push-remote", str(tmp_path / "missing.git"))
    assert r.returncode == D.EXIT["PREDICTION_PUSH_FAILED"] and "PREDICTION_PUSH_FAILED" in r.stderr
    reads = cl["c"] / "audits/predictive-intelligence/daily/READS.jsonl"
    calls = cl["c"] / "audits/predictive-intelligence/daily/CALLS.jsonl"
    assert (not reads.exists() or reads.read_text() == "") and (not calls.exists() or calls.read_text() == "")
    assert (cl["c"] / rel).read_text() == before

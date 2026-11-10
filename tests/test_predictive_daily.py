"""CM-2 (PI-D-122): the daily cycle (audits/predictive-intelligence/daily/predictive_daily.py).

No network: label reads are stubbed or capped at 0; the end-to-end test runs the command in a temporary clone with a synthetic
state export committed after the recipe freeze, so nothing is written into this checkout.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from memelab.predictive import contract as C
from memelab.predictive import labels as L
from memelab.predictive import monitoring as M

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "audits/predictive-intelligence/daily/predictive_daily.py"
REF71 = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"


def _load():
    spec = importlib.util.spec_from_file_location("predictive_daily_t", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load()
MINT = "So11111111111111111111111111111111111111112"
POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
DT = C.parse_utc("2026-11-12T00:00:00Z")


def dec(**kw):
    d = {"decision_key": "k1", "chain": "solana", "mint": MINT, "pool": POOL, "route": "PIT_RECORDED", "decision_time": DT,
         "snapshot": {"price": 1.0, "vol_24h": 2e5, "liquidity": 5e4}}
    d.update(kw)
    return d


def test_oi21_1_a_read_that_stops_before_a_newly_matured_window_end_is_planned_again():
    t1_mat, t2_mat = C.label_matures_at(L.T1, DT), C.label_matures_at(L.T2, DT)
    b1, b2 = L.needed_boundary(L.T1, DT), L.needed_boundary(L.T2, DT)
    assert D.plan_reads([dec()], {}, DT + 3600) == []                                  # nothing matured: no read
    have = {"k1": {"http": 200, "boundary": b1}}
    assert D.plan_reads([dec()], have, t1_mat + 600) == []                             # T1 covered, T2 not matured
    p = D.plan_reads([dec()], have, t2_mat + 600)
    assert len(p) == 1 and p[0]["boundary"] == b2                                      # T2 matured: read again to its end
    assert D.plan_reads([dec()], {"k1": {"http": 200, "boundary": b2}}, t2_mat + 600) == []
    assert len(D.plan_reads([dec()], {"k1": {"http": 429, "boundary": b2}}, t2_mat + 600)) == 1   # a failed read is retried
    assert D.plan_reads([dec(pool=None)], {}, t2_mat + 600) == []                     # no pool: no OHLCV read
    assert D.plan_reads([dec(snapshot={})], {}, t2_mat + 600) == []                   # no snapshot price


def reg_with(*versions):
    entries, at = {}, {}
    for i, (v, cutoff, registered) in enumerate(versions):
        eid = f"e{i}"
        entries[eid] = {"entry_id": eid, "recipe_id": "R-CM2-1", "kind": "B2", "target": L.T1, "version": v, "training_cutoff": cutoff,
                        "training_cutoff_utc": D.iso(cutoff)}
        at[eid] = registered
    return {"entries": entries, "registered_at": at, "retired": set()}


def test_the_version_in_force_is_registered_before_the_decision_trained_before_it_and_not_stale():
    cut = DT - 3 * 86400
    reg = reg_with((1, cut, DT - 86400))
    e, why = D.in_force(reg, "B2", L.T1, DT)
    assert e["version"] == 1 and why is None
    assert D.in_force(reg, "B2", L.T1, DT - 2 * 86400) == (None, "MODEL_NOT_SELECTED")      # registered after that decision
    e, why = D.in_force(reg, "B2", L.T1, cut + C.ACCEPTANCE["max_model_age_s"] + 1)
    assert why == "MODEL_STALE" and e["version"] == 1
    reg2 = reg_with((1, cut, DT - 86400), (2, DT - 3600, DT - 1800))
    assert D.in_force(reg2, "B2", L.T1, DT)[0]["version"] == 2
    assert D.in_force(reg2, "B2", L.T1, DT - 1900)[0]["version"] == 1                        # v2 not yet registered then
    reg2["retired"] = {"e1"}
    assert D.in_force(reg2, "B2", L.T1, DT)[0]["version"] == 1                               # a retired version is never used


def test_label_reads_are_refused_when_disabled_and_a_broken_pacer_is_caught(monkeypatch):
    r = D.Reader(max_calls=5, deadline=1e12, offline=True)
    with pytest.raises(D.Fail) as e:
        r.get("https://example.invalid/x?token=" + MINT, kind="ohlcv")
    assert e.value.reason == "LABEL_FETCH_FAILED"
    monkeypatch.setattr(D.SRC, "curl_get", lambda u, timeout_s=30: (200, b"{}"))
    r = D.Reader(max_calls=20, deadline=1e12)
    r.guard.sleep = lambda s: None                                                            # the guard's pacing removed
    with pytest.raises(D.Fail, match="more than 6 calls in 60 s"):
        for _ in range(10):
            r.get("https://example.invalid/x?token=" + MINT, kind="ohlcv")
    r = D.Reader(max_calls=0, deadline=1e12)
    assert r.get("https://example.invalid/x", kind="ohlcv") is None and r.stopped == "CALL_CAP_REACHED"


def test_only_the_audit_folder_and_the_cost_ledger_are_allowed_paths():
    assert D.outside({"audits/predictive-intelligence/daily/LEDGER.jsonl", "audits/predictive-intelligence/COST_LEDGER.md"}) == set()
    assert D.outside({"audits/predictive-intelligence/daily_x/a", "data/state/latest.json", "memelab/cli.py"}) == {
        "audits/predictive-intelligence/daily_x/a", "data/state/latest.json", "memelab/cli.py"}


@pytest.mark.parametrize("argv", [["run", "--max-calls", "301"], ["run", "--max-calls", "61"], ["run", "--max-calls", "-1"], ["run", "--max-minutes", "0"],
                                  ["run", "--max-minutes", "121"]])
def test_out_of_bounds_limits_are_refused_with_a_named_reason(argv, capsys):
    assert D.main(argv) == D.EXIT["PREFLIGHT_FAILED"]
    assert "PREFLIGHT_FAILED" in capsys.readouterr().err


def test_the_recipe_and_the_governing_fingerprint_are_pinned():
    assert D.fsha(D.RECIPE) == D.RECIPE_SHA256 and D.GOVERNING_SHA == C.governing_sha256()
    rec = json.loads(D.RECIPE.read_text())
    assert rec["new_configurations"] == 0 and rec["n_search_cumulative"] == 130 and set(rec["kinds"]) == {"B0", "B2"}
    assert rec["cadence"]["max_model_age_s"] == C.ACCEPTANCE["max_model_age_s"] and D.CADENCE_S == 7 * 86400


# ---------------------------------------------------------------- end to end in a temporary clone
def _git(cwd, *a, env=None):
    return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True, env=env).stdout


def _have(rev):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", rev + "^{commit}"], capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def clone(tmp_path_factory):
    if not _have(REF71):
        pytest.skip("the 71fc50e state export is not in this clone (git fetch origin main)")
    head = _git(ROOT, "rev-parse", "HEAD").strip()
    reg = ROOT / "audits/predictive-intelligence/daily/registry/REGISTRY_LOG.jsonl"
    if not reg.exists() or _git(ROOT, "ls-files", str(reg.relative_to(ROOT))).strip() == "":
        pytest.skip("no committed CM-2 registry yet")
    base = tmp_path_factory.mktemp("daily")
    c = base / "c"
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(ROOT), str(c)], check=True, capture_output=True)
    _git(c, "checkout", "-q", "-B", "feature/predictive-intelligence", head)   # PI-D-140: a run needs the branch by name
    _git(c, "config", "user.email", "test@localhost")
    _git(c, "config", "user.name", "test")
    freeze = float(_git(c, "log", "--diff-filter=A", "--format=%ct", "--", "audits/predictive-intelligence/daily/RECIPE.json").split()[-1])
    # a synthetic state export one hour after the recipe freeze: one Solana thesis row of 71fc50e with a newer created_at
    doc = json.loads(_git(c, "show", f"{REF71}:data/state/latest.json"))
    tab = doc["_tables"]     # PI-D-124: the export keeps its tables under "_tables" (the frozen fixture read doc["tokens"])
    sol = {t["mint"] for t in tab["tokens"] if t.get("chain") == "solana" and (t.get("primary_pool") or t.get("graduated_pool"))}
    row = next(r for r in sorted(tab["theses"], key=lambda r: -float(r["created_at"])) if r["mint"] in sol)
    new = dict(row, created_at=float(row["created_at"]) + 1.0)
    new.pop("id", None)
    tab["theses"] = list(tab["theses"]) + [new]
    work = base / "w"
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(c), str(work)], check=True, capture_output=True)
    _git(work, "checkout", "-q", "-b", "fake", REF71)
    (work / "data/state/latest.json").write_text(json.dumps(doc))
    t_exp = int(freeze + 3600)
    env = {**os.environ, "GIT_COMMITTER_DATE": f"{t_exp} +0000", "GIT_AUTHOR_DATE": f"{t_exp} +0000"}
    _git(work, "-c", "user.email=t@localhost", "-c", "user.name=t", "commit", "-q", "-am", "synthetic export", env=env)
    _git(c, "fetch", "-q", str(work), "fake:refs/heads/fake")
    return {"c": c, "state": base / "state", "t_exp": t_exp, "mint": row["mint"], "freeze": freeze}


def _anchor(c: Path) -> str:
    """PI-D-140: a local bare repository as the push remote of a test clone (never the network, never the source checkout)."""
    bare = c.parent / (c.name + "_anchor.git")
    if not bare.exists():
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True, capture_output=True)
    if subprocess.run(["git", "-C", str(c), "remote", "get-url", "anchor"], capture_output=True).returncode:
        _git(c, "remote", "add", "anchor", str(bare))
    return str(bare)


def _run(cl, *extra):
    _anchor(cl["c"])
    env = {**os.environ, "PREDICTIVE_DAILY_TEST_CLOCK": "1"}
    return subprocess.run([sys.executable, "-B", str(cl["c"] / "audits/predictive-intelligence/daily/predictive_daily.py"), "run",
                           "--state-dir", str(cl["state"]), "--no-fetch", "--export-ref", "fake", "--push-remote", "anchor", *extra],
                          capture_output=True, text=True, timeout=900, env=env)


def test_e2e_predictions_are_committed_before_any_read_and_a_second_run_adds_nothing(clone):
    c = clone["c"]
    led = c / "audits/predictive-intelligence/daily/LEDGER.jsonl"
    r = _run(clone, "--now", str(clone["t_exp"] + 600))
    assert r.returncode == 0, r.stderr[-1500:]
    ents = M.read_ledger(led.read_text())
    kinds = [e["payload"]["kind"] for e in ents]
    assert kinds[0] == "PREDICTION_SET" and kinds.count("PREDICTION") == 6
    # PI-D-124: the frozen check said no OUTCOME at all; the cycle appends PENDING outcomes (no label, no read) after the
    # prediction commit, as Phase 19 did. What must hold: every outcome comes after every prediction and none carries a label.
    outs = [e for e in ents if e["payload"]["kind"] == "OUTCOME"]
    assert all(e["payload"]["state"] == "PENDING" and e["payload"]["label"] is None for e in outs)
    assert all(o["seq"] > max(e["seq"] for e in ents if e["payload"]["kind"] == "PREDICTION") for o in outs)
    preds = [e["payload"] for e in ents if e["payload"]["kind"] == "PREDICTION"]
    assert {p["mint"] for p in preds} == {clone["mint"]} and all(p["published"] is False for p in preds)
    assert all(p["number"] is None or 0 <= p["number"] <= 1 for p in preds)
    assert all(p["decision_time"] == clone["t_exp"] and p["version"] == 1 for p in preds)
    # the predictions are in a commit made before this run's end; the tree is clean (writes only in allowed paths, committed)
    assert _git(c, "show", "HEAD:audits/predictive-intelligence/daily/LEDGER.jsonl") == led.read_text()
    assert _git(c, "status", "--porcelain") == ""
    first = led.read_text()
    alert = (c / "audits/predictive-intelligence/daily/ALERT_SUMMARY.txt").read_text()
    assert ": OK" in alert.splitlines()[0] and "new decisions after the freeze: 1" in alert
    r2 = _run(clone, "--now", str(clone["t_exp"] + 900))
    assert r2.returncode == 0, r2.stderr[-1500:]
    assert led.read_text() == first                                                    # idempotent: nothing appended
    calls = c / "audits/predictive-intelligence/daily/CALLS.jsonl"
    assert not calls.exists() or calls.read_text() == ""
    # a matured target with the call cap at 0: the read is planned, no call is made, the run still completes
    r3 = _run(clone, "--now", str(clone["t_exp"] + 7 * 3600), "--max-calls", "0")
    assert r3.returncode == 0, r3.stderr[-1500:]
    assert "LABEL_READS_STOPPED_CALL_CAP_REACHED" in (c / "audits/predictive-intelligence/daily/ALERT_SUMMARY.txt").read_text()
    # PI-D-124: the frozen check said the ledger is unchanged; the matured T1b outcome is appended as NOT_READ (no read, no
    # label), a non-final state, as monitoring.next_outcomes records a planned read that was not made. The prefix is unchanged.
    now_txt = led.read_text()
    assert now_txt.startswith(first) and _git(c, "status", "--porcelain") == ""
    added = M.read_ledger(now_txt)[len(M.read_ledger(first)):]
    assert added and all(e["payload"]["kind"] == "OUTCOME" and e["payload"]["eligibility"] == "NOT_READ"
                         and e["payload"]["label"] is None for e in added)
    assert {e["payload"]["target"] for e in added} == {L.T1B}


def test_e2e_no_commit_mode_refuses_label_reads_and_a_tampered_ledger_stops_the_run(clone, tmp_path):
    c2 = tmp_path / "c2"
    subprocess.run(["git", "clone", "-q", str(clone["c"]), str(c2)], check=True, capture_output=True)
    _git(c2, "fetch", "-q", str(clone["c"]), "fake:refs/heads/fake")
    cl = dict(clone, c=c2, state=tmp_path / "s2")
    led = c2 / "audits/predictive-intelligence/daily/LEDGER.jsonl"
    lines = led.read_text().splitlines()
    p = json.loads(lines[1])
    p["payload"]["number"] = 0.99
    led.write_text("\n".join([lines[0], C.canon(p)] + lines[2:]) + "\n")
    r = _run(cl, "--now", str(clone["t_exp"] + 600), "--no-commit")
    assert r.returncode == D.EXIT["PREFLIGHT_FAILED"] and "PREFLIGHT_FAILED" in r.stderr
    assert "PREFLIGHT_FAILED" in (c2 / "audits/predictive-intelligence/daily/ALERT_SUMMARY.txt").read_text()

"""Phase 19: monitoring-1 (memelab/predictive/monitoring.py): the append-only outcome ledger, prospective outcomes through labels-1,
drift monitors D1 to D8, the response policy and the rollback demo through the registry. Synthetic data and fixtures only; no
network, temporary paths, fixed times. Pre-registration: audits/predictive-intelligence/phase_19/ACCEPTANCE_CHECKLIST.md."""
from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import abstention as AB
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import labels as L
from memelab.predictive import monitoring as M
from memelab.predictive import registry as R

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "predictive"))
import asof_helpers as H  # noqa: E402

MINT, POOL = H.MINT_A, H.POOL_A
MINT_B, POOL_B = H.MINT_B, H.POOL_B
P0 = L.prospective_start()
DT = P0 + 2 * 86400 + 1234            # a prospective decision (2026-10-26T00:20:34Z)
TE = DT + 300
LATE = DT + 30 * 86400
KEY, KEY_B = "k-prospective-a", "k-prospective-b"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- ledger fixtures
def pset(set_id="ps_1", decisions=None):
    decisions = decisions or [{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT},
                              {"decision_key": KEY_B, "chain": "solana", "mint": MINT_B, "decision_time": DT}]
    return {"kind": "PREDICTION_SET", "set_id": set_id, "file": "x.csv", "sha256": "f" * 64, "decisions": decisions}


def pred(key=KEY, mint=MINT, target=L.T1, cand="P07_B2", number=0.2, set_id="ps_1", why=None):
    return {"kind": "PREDICTION", "prediction_id": "pr_" + M.sha([set_id, key, target, cand])[:40], "set_id": set_id,
            "decision_key": key, "chain": "solana", "mint": mint, "decision_time": DT, "target": target, "candidate": cand,
            "number": number, "why": why, "card_file_sha256": "c" * 64, "model_sha": "m" * 64, "training_cutoff_utc": "2026-10-17T00:00:00Z",
            "label_matures_at": C.label_matures_at(target, DT), "published": False, "role": "REFERENCE_INTERNAL"}


def doc(key=KEY, mint=MINT, target=L.T1, fid="fc_1", set_id="ps_1"):
    return {"kind": "DOCUMENT", "forecast_id": fid, "record_id": "r" * 64, "set_id": set_id, "decision_key": key, "chain": "solana",
            "mint": mint, "decision_time": DT, "target": target, "prediction_status": "ABSTAIN",
            "reasons": ["MODEL_NOT_SELECTED", "UNCALIBRATED"], "document_sha256": "d" * 64, "record_sha256": "e" * 64,
            "row_sha256": "0" * 64, "published": True}


def outcome(key=KEY, mint=MINT, target=L.T1, state="LABELED", label=1, cls="TARGET_FIRST", observed=None, recorded=None, rk="rk",
            body="b" * 64, **kw):
    mat = C.label_matures_at(target, DT)
    lab = state == "LABELED"
    p = {"kind": "OUTCOME", "decision_key": key, "chain": "solana", "mint": mint, "decision_time": DT, "target": target,
         "target_version": "1", "labels_version": L.LABELS_VERSION, "registry_sha": "x", "state": state,
         "label": label if lab else None, "label_class": cls if lab else None, "censored": 1 if state in M.CENSORED else 0,
         "eligibility": "ELIGIBLE", "flags": [], "label_matures_at": mat,
         "label_observed_at": (mat + 60 if observed is None else observed) if lab else None,
         "response_key": rk if lab else None,
         "request_url": f"https://api.geckoterminal.com/x?token={mint}" if lab else None, "body_sha256": body if lab else None,
         "detail": None, "supersedes": None, "revision_of": None, "revision_reason": None,
         "recorded_at": mat + 120 if recorded is None else recorded, "conservative_lens": label if lab else None}
    p.update(kw)
    p["outcome_id"] = "oc_" + M.sha({k: v for k, v in p.items() if k not in ("recorded_at", "outcome_id")})[:40]
    return p


@pytest.fixture
def led(tmp_path):
    p = tmp_path / "OUTCOME_LEDGER.jsonl"
    M.append(p, [{"kind": "PLAN", "plan_id": "p"}, pset(), pred(), pred(cand="P07_B0", number=0.25), doc()])
    return p


# ---------------------------------------------------------------- ledger: chain and append-only (rule 4)
def test_append_read_and_verify_roundtrip(led):
    ents = M.read_ledger(led.read_text())
    assert [e["payload"]["kind"] for e in ents] == ["PLAN", "PREDICTION_SET", "PREDICTION", "PREDICTION", "DOCUMENT"]
    assert [e["seq"] for e in ents] == list(range(5)) and ents[0]["prev"] == M.GENESIS
    assert all(ents[i]["prev"] == ents[i - 1]["sha"] for i in range(1, 5))
    v = M.verify(led)
    assert v["ok"] and v["entries"] == 5 and v["head"] == ents[-1]["sha"]


def test_negative_a_prediction_line_edited_in_place_breaks_the_chain(led):
    lines = led.read_text().splitlines()
    e = json.loads(lines[2])
    e["payload"]["number"] = 0.9                      # a retroactive edit of an old prediction
    lines[2] = M.canon(e)
    led.write_text("\n".join(lines) + "\n")
    with pytest.raises(M.LedgerTampered):
        M.read_ledger(led.read_text())
    assert not M.verify(led)["ok"]
    with pytest.raises(M.LedgerTampered):
        M.append(led, [outcome()])
    e["sha"] = M.sha({k: e[k] for k in ("ledger_version", "seq", "prev", "payload")})   # re-sealed line: the next line's prev breaks
    lines[2] = M.canon(e)
    led.write_text("\n".join(lines) + "\n")
    with pytest.raises(M.LedgerTampered, match="chain broken"):
        M.read_ledger(led.read_text())


def test_negative_a_removed_or_reordered_line_is_tampering(led):
    lines = led.read_text().splitlines()
    for bad in (lines[:2] + lines[3:], lines[:2] + [lines[3], lines[2]] + lines[4:]):
        with pytest.raises(M.LedgerTampered):
            M.read_ledger("\n".join(bad) + "\n")
    ents = M.read_ledger(led.read_text())
    e = M.seal(pred(key=KEY_B, mint=MINT_B), seq=len(ents) + 3, prev=ents[-1]["sha"])     # right prev, wrong sequence number
    with pytest.raises(M.LedgerTampered, match="sequence"):
        M.read_ledger(led.read_text() + M.canon(e) + "\n")


def test_negative_a_prediction_id_reappended_with_another_number_is_refused_identical_is_a_noop(led):
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [pred(number=0.6)])
    assert e.value.code == "PREDICTION_EDIT_REFUSED"
    r = M.append(led, [pred()])
    assert r == {"appended": 0, "duplicates": 1, "head": M.read_ledger(led.read_text())[-1]["sha"], "entries": 5}
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [dict(doc(), reasons=["MODEL_NOT_SELECTED"])])
    assert e.value.code == "PREDICTION_EDIT_REFUSED"


def test_cx19_a_backdated_prediction_after_its_outcome_is_refused_whatever_time_it_claims(led):
    M.append(led, [outcome()])
    late = pred(cand="P09_M2_OC_LOGIT_B2", number=0.99)
    late["training_cutoff_utc"] = "2026-10-01T00:00:00Z"     # claims to have been made long before the label read
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [late])
    assert e.value.code == "LATE_PREDICTION_REFUSED"
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [doc(fid="fc_late")])
    assert e.value.code == "LATE_PREDICTION_REFUSED"
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [pset(set_id="ps_2")])
    assert e.value.code == "LATE_PREDICTION_REFUSED"
    # a ledger written around append (a valid chain holding the late entry) is caught by verify and refused by load
    ents = M.read_ledger(led.read_text())
    forged = led.read_text() + M.canon(M.seal(late, seq=len(ents), prev=ents[-1]["sha"])) + "\n"
    led.write_text(forged)
    v = M.verify(led)
    assert not v["ok"] and "LATE_PREDICTION_REFUSED" in v["problems"][0]
    with pytest.raises(M.LedgerError) as e:
        M.load(led)
    assert e.value.code == "LATE_PREDICTION_REFUSED"


def test_a_forged_censored_labeled_outcome_is_never_scored_even_in_an_unchecked_index(led):
    o = outcome()
    o["censored"] = 1                                        # LABELED with the censored bit: the append rules refuse it
    ents = M.read_ledger(led.read_text())
    led.write_text(led.read_text() + M.canon(M.seal(o, seq=len(ents), prev=ents[-1]["sha"])) + "\n")
    with pytest.raises(M.LedgerError):
        M.load(led)
    idx = M.Index(M.read_ledger(led.read_text()))          # an index built without the rules (defence in depth)
    assert M.scorable(idx, LATE) == []


def test_p05_a_label_read_or_recorded_before_maturity_is_refused_and_pending_carries_no_label(led):
    mat = C.label_matures_at(L.T1, DT)
    for kw in ({"observed": mat - 1}, {"recorded": mat - 1}):
        with pytest.raises(M.LedgerError) as e:
            M.append(led, [outcome(**kw)])
        assert e.value.code == "NOT_YET_MATURED"
    bad = outcome(state="PENDING")
    bad["label"] = 0                                   # a pending row that carries a negative label
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [bad])
    assert e.value.code == "MALFORMED_ENTRY"


def test_p37_censored_outcomes_carry_no_label_and_are_never_scored(led):
    c = outcome(state="UNVERIFIABLE_NO_VENDOR_HISTORY", conservative_lens=0)
    M.append(led, [c])
    assert M.scorable(M.load(led), LATE) == []
    cc = outcome(key=KEY_B, mint=MINT_B, state="VENDOR_OR_ROUTE_GAP", censored=0)
    cc["outcome_id"] = "oc_x"
    with pytest.raises(M.LedgerError):
        M.append(led, [cc])


def test_p05_pending_is_never_scored_or_counted_negative_and_is_superseded_by_naming_it(led):
    p = outcome(state="PENDING")
    M.append(led, [p])
    idx = M.load(led)
    assert M.scorable(idx, LATE) == []
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome()])
    assert e.value.code == "SUPERSEDE_REQUIRED"
    mat = C.label_matures_at(L.T1, DT)
    M.append(led, [outcome(supersedes=p["outcome_id"], observed=mat + 200, recorded=mat + 300)])
    sc = M.scorable(M.load(led), LATE)
    assert len(sc) == 1 and sc[0]["label"] == 1
    assert M.scorable(M.load(led), C.label_matures_at(L.T1, DT) - 1) == []


def test_a_final_outcome_is_revised_only_with_revision_of_and_both_versions_stay(led):
    first = outcome(label=1, cls="TARGET_FIRST")
    M.append(led, [first])
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome(label=0, cls="INVALIDATION_FIRST")])
    assert e.value.code == "FINAL_OUTCOME_REPLACED"
    mat = C.label_matures_at(L.T1, DT)
    rev = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="REREAD_48H", rk="rk2",
                  body="c" * 64, observed=mat + 172860, recorded=mat + 172900)
    M.append(led, [rev])
    idx = M.load(led)
    assert [o["outcome_id"] for o in idx.outcome_pairs[(KEY, L.T1)]] == [first["outcome_id"], rev["outcome_id"]]
    cur = M.current_outcomes(idx)[(KEY, L.T1)]
    assert cur["label"] == 0 and "REVISED" in cur["flags"]


def test_p01_outcome_identity_must_equal_the_prediction_set_and_needs_one(led):
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome(mint=MINT_B)])
    assert e.value.code == "IDENTITY_MISMATCH"
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome(key="k-unknown")])
    assert e.value.code == "OUTCOME_WITHOUT_PREDICTION"
    o = outcome()
    o["request_url"] = "https://api.geckoterminal.com/x"           # a read without token=<mint>
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [o])
    assert e.value.code == "IDENTITY_MISMATCH"
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome(label_matures_at=DT)])
    assert e.value.code in ("MATURITY_MISMATCH", "NOT_YET_MATURED")


def test_a_concurrent_writer_and_a_prediction_out_of_range_are_refused(led):
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [outcome()], expect_sha="0" * 64)
    assert e.value.code == "CONCURRENT_WRITE"
    for n in (1.5, float("nan")):
        with pytest.raises(M.LedgerError):
            M.append(led, [pred(key=KEY_B, mint=MINT_B, number=n)])
    with pytest.raises(M.LedgerError):
        M.append(led, [pred(key=KEY_B, mint=MINT_B, number=None, why=None)])
    with pytest.raises(M.LedgerError):
        M.append(led, [dict(pred(key=KEY_B, mint=MINT_B), published=True)])


def test_is_append_only(led):
    old = led.read_text()
    M.append(led, [outcome()])
    new = led.read_text()
    assert M.is_append_only(old, new) and not M.is_append_only(new, old)
    assert not M.is_append_only(old, old.replace("0.2", "0.3", 1))


# ---------------------------------------------------------------- prospective outcomes through labels-1 (rule 5)
def mkread(rows, boundary, retrieved, *, mint=MINT, pool=POOL):
    url = H.GT.format(pool=pool, b=int(boundary)) + f"&token={mint}"
    return L.read_from_body(H.gt_body(rows, base=mint), mint=mint, pool=pool, url=url, boundary=boundary, retrieved_at=retrieved,
                            http_status=200, response_key=L.sha([url, retrieved, len(rows)]))


def dec(key=KEY, mint=MINT, pool=POOL, chain="solana", price=1.0, route="PIT_RECORDED"):
    return {"decision_key": key, "chain": chain, "mint": mint, "pool": pool, "route": route, "decision_time": DT,
            "decision_time_basis": "EXPORT_COMMIT", "export_commit": "c1", "created_at": DT - 600, "status": "WATCH", "flags": [],
            "snapshot": {"price": price, "vol_24h": 2e5, "liquidity": 5e4}, "token": {"creator": None, "first_pool_at": "2026-10-01T00:00:00Z"},
            "row_sha256": "0" * 64}


def path_rows(up=True):
    last_ok = int((DT - 600) // 300 * 300)
    ref = [H.candle(s, c=1.0) for s in range(last_ok - 3600, last_ok + 1, 300)]
    s0 = int(L.ceil_grid(TE))
    path = [H.candle(s, c=1.0) for s in range(s0, s0 + 3600, 300)]
    path.append(H.candle(s0 + 3600, c=1.3 if up else 0.8, h=1.31 if up else 0.81, l=1.29 if up else 0.79))
    path += [H.candle(s, c=1.3 if up else 0.8) for s in range(s0 + 3900, int(TE + 2 * 86400 + 600), 300)]
    return ref + path


def test_prospective_records_classify_with_the_frozen_rule_pending_before_maturity_and_gaps_censored():
    rows = path_rows(up=True)
    b = L.needed_boundary(L.T2, DT)
    rd = mkread(rows, b, LATE)
    d = dec()
    recs = {r["target"]: r for r in M.prospective_records(L.Universe([d], as_of=LATE, read_of={KEY: rd}))}
    for t in L.TARGETS:
        want = L.classify(t, DT, rd)
        assert recs[t]["state"] == want["state"] and recs[t].get("label_class") == want["label_class"], t
    assert recs[L.T1]["label"] == 1 and recs[L.T1]["label_class"] == "TARGET_FIRST"
    # read before T1 and T2 maturity: only T1b is labelled; nothing pending carries a label
    early = C.label_matures_at(L.T1, DT) - 1
    rd2 = mkread(rows, L.needed_boundary(L.T1B, DT), early)
    r2 = {r["target"]: r for r in M.prospective_records(L.Universe([d], as_of=early, read_of={KEY: rd2}))}
    assert r2[L.T1B]["state"] == "LABELED" and r2[L.T1]["state"] == "PENDING" and r2[L.T2]["state"] == "PENDING"
    assert r2[L.T1]["label"] is None and r2[L.T2]["label"] is None
    # no pool at all (empty vendor list): censored once matured, pending before
    dn = dec(key=KEY_B, mint=MINT_B, pool=None, route="CURRENT_VENDOR_LIST")
    r3 = {r["target"]: r for r in M.prospective_records(L.Universe([dn], as_of=LATE))}
    assert {r["state"] for r in r3.values()} == {"VENDOR_OR_ROUTE_GAP"} and all(r["censored"] == 1 for r in r3.values())
    r4 = M.prospective_records(L.Universe([dn], as_of=DT + 60))
    assert {r["state"] for r in r4} == {"PENDING"}
    # an unread decision with a pool: pending, then NOT_READ (a visible plan gap, never negative)
    r5 = {r["target"]: r["state"] for r in M.prospective_records(L.Universe([dec()], as_of=LATE))}
    assert set(r5.values()) == {"NOT_READ"}
    r6 = M.prospective_records(L.Universe([dec(chain="base", mint="0x" + "a" * 40, pool=None)], as_of=LATE))
    assert {r["state"] for r in r6} == {"OUT_OF_SCOPE_CHAIN"}


def test_outcome_payloads_enter_the_ledger_and_later_reads_supersede_or_revise(tmp_path):
    p = tmp_path / "l.jsonl"
    M.append(p, [pset(decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT}])])
    rows = path_rows(up=True)
    d = dec()
    early = C.label_matures_at(L.T1, DT) - 1
    rd1 = mkread(rows, L.needed_boundary(L.T1B, DT), early)
    recs1 = M.prospective_records(L.Universe([d], as_of=early, read_of={KEY: rd1}))
    M.append(p, M.next_outcomes(M.load(p), recs1, recorded_at=early))
    rd2 = mkread(rows, L.needed_boundary(L.T2, DT), LATE)
    recs2 = M.prospective_records(L.Universe([d], as_of=LATE, read_of={KEY: rd2}))
    nxt = M.next_outcomes(M.load(p), recs2, recorded_at=LATE)
    assert {x["target"] for x in nxt} == {L.T1, L.T2} and all(x["supersedes"] for x in nxt)
    M.append(p, nxt)
    assert M.next_outcomes(M.load(p), recs2, recorded_at=LATE) == []
    assert M.verify(p)["ok"]
    sc = M.scorable(M.load(p), LATE)
    assert {o["target"] for o in sc} == set(L.TARGETS)
    with pytest.raises(M.LedgerError):
        M.outcome_payload(dict(recs2[0], state=L.NEEDS_OTHER_POOLS), recorded_at=LATE)


def test_p43_prospective_label_rows_never_enter_the_training_gate(tmp_path):
    con = L.connect(tmp_path / "s.sqlite")
    rd = mkread(path_rows(), L.needed_boundary(L.T2, DT), LATE)
    recs = M.prospective_records(L.Universe([dec()], as_of=LATE, read_of={KEY: rd}))
    assert {r["split"] for r in recs} == {"PROSPECTIVE"} and {r["state"] for r in recs} == {"LABELED"}
    L.store_labels(con, recs, export_ref="x", params={}, now=LATE)
    assert con.execute("SELECT count(*) FROM predictive_labels WHERE split='PROSPECTIVE' AND state='LABELED'").fetchone()[0] == 3
    for t in L.TARGETS:
        assert L.training_labels(con, LATE + 86400 * 365, t) == []


# ---------------------------------------------------------------- drift monitors (rule 9)
def test_the_frozen_thresholds_and_the_page_hinkley_settings_equal_the_registry_and_calibration():
    assert M.DRIFT == {k: R.THRESHOLDS[R.DRIFT_ALERT][k] for k in ("delta", "threshold", "min_obs", "two_sided")} == CAL.DRIFT
    assert (M.PSI_BINS, M.PSI_FLOOR, M.PSI_WATCH, M.PSI_ALERT, M.MIN_FEATURE_VALUES, M.MISSING_SHARE_ALERT) == (10, 1e-4, 0.10, 0.25, 30, 0.20)
    assert (M.MIN_LABELLED_FOR_RATE, M.MIN_ROWS_FOR_CALIBRATION, M.COVERAGE_DIFF_ALERT, M.MIN_DECISIONS_FOR_COVERAGE) == (20, 20, 0.20, 20)
    assert (M.SOURCE_MAX_AGE_S, M.READ_FAILURE_SHARE_ALERT, M.REGIME_UNSEEN_SHARE_ALERT) == (129600, 0.20, 0.5)


def test_d1_psi_is_near_zero_for_the_same_distribution_and_alerts_on_a_shift():
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, 2000)
    same = M.psi(ref, rng.normal(0, 1, 400))
    shifted = M.psi(ref, rng.normal(1.5, 1, 400))
    assert same["psi"] < M.PSI_WATCH and shifted["psi"] > M.PSI_ALERT and same["kind"] == "quantile"
    cat = M.psi([0, 1] * 50, [1] * 40)
    f = M.PSI_FLOOR
    want = (f - 0.5) * math.log(f / 0.5) + 0.5 * math.log(1 / 0.5)       # the empty category floored at 1e-4, by hand
    assert cat["kind"] == "categorical" and cat["psi"] == pytest.approx(want, rel=1e-9) and cat["bins"] == 3
    assert M.psi([0, 1] * 50, [0, 1] * 20)["psi"] < 1e-12
    unseen = M.psi([0, 1] * 50, [2] * 40)                  # every current value in the "not seen" bin
    assert unseen["psi"] == pytest.approx(2 * (f - 0.5) * math.log(f / 0.5) + (1 - f) * math.log(1 / f), rel=1e-9)
    mid = [M.feature_drift({"a": list(ref)}, {"a": list(rng.normal(d, 1, 400))})["columns"]["a"] for d in (0.45, 0.6, 0.75)]
    assert any(M.PSI_ALERT <= c["psi"] < 1.0 and c["psi_state"] == "DRIFT_ALERT" for c in mid)
    assert any(M.PSI_WATCH <= c["psi"] < M.PSI_ALERT and c["psi_state"] == "WATCH" for c in
               [M.feature_drift({"a": list(ref)}, {"a": list(rng.normal(d, 1, 400))})["columns"]["a"] for d in (0.3, 0.35, 0.4)])
    fd = M.feature_drift({"a": list(ref)}, {"a": list(rng.normal(1.5, 1, 40))})
    assert fd["state"] == "DRIFT_ALERT" and fd["columns"]["a"]["psi_state"] == "DRIFT_ALERT"
    ok = M.feature_drift({"a": list(ref)}, {"a": list(rng.normal(0, 1, 400))})
    assert ok["state"] == "OK"
    few = M.feature_drift({"a": list(ref)}, {"a": list(rng.normal(3, 1, 29))})
    assert few["state"] == "INSUFFICIENT_DATA"
    miss = M.feature_drift({"a": list(ref)}, {"a": [None] * 20 + list(rng.normal(0, 1, 40))})
    assert miss["columns"]["a"]["missing_state"] == "DRIFT_ALERT" and miss["state"] == "DRIFT_ALERT"


def test_d2_label_rate_drift():
    assert M.label_rate_drift(0.25, [1] * 6 + [0] * 18)["state"] == "OK"
    assert M.label_rate_drift(0.25, [1] * 20 + [0] * 10)["state"] == "DRIFT_ALERT"
    assert M.label_rate_drift(0.25, [1] * 19)["state"] == "INSUFFICIENT_DATA"


def test_d3_calibration_drift_and_page_hinkley():
    rng = np.random.default_rng(3)
    p = np.repeat([0.1, 0.2, 0.3, 0.4, 0.5], 80)          # five bins of 80, each with exactly its rate of positives
    y = np.concatenate([[1] * int(round(q * 80)) + [0] * (80 - int(round(q * 80))) for q in (0.1, 0.2, 0.3, 0.4, 0.5)])
    assert M.calibration_drift(y, p, "x")["state"] == "OK"
    assert M.calibration_drift(y, np.clip(p + 0.3, 0, 1), "x")["state"] == "DRIFT_ALERT"
    assert M.calibration_drift(y[:19], p[:19], "x")["state"] == "INSUFFICIENT_DATA"
    flat = [(float(i), float(rng.normal(0, 0.01))) for i in range(200)]
    assert M.page_hinkley_alarms(flat)["state"] == "OK"
    jump = [(float(i), float(rng.normal(0, 0.01) + (0.1 if i >= 60 else 0.0))) for i in range(200)]
    r = M.page_hinkley_alarms(jump)
    assert r["state"] == "DRIFT_ALERT" and r["alarms"][0] >= 60
    assert M.page_hinkley_alarms(jump[:29])["state"] == "INSUFFICIENT_DATA"
    with pytest.raises(ValueError):
        M.page_hinkley_alarms(jump[:40] + [(41.0, float("nan"))])


def test_d4_d5_d6_d7_d8():
    assert M.coverage_drift(20, 25, 80, 90)["state"] == "OK"
    assert M.coverage_drift(5, 25, 80, 90)["state"] == "DRIFT_ALERT"
    assert M.coverage_drift(5, 19, 80, 90)["state"] == "INSUFFICIENT_DATA"
    assert M.support_state(30, 8)["state"] == "SUPPORT_BELOW_MINIMUM" and M.support_state(60, 12)["state"] == "OK"
    now = P0 + 3 * 86400
    ok = M.source_state(newest_export_time=now - 3600, now=now, reads_total=40, reads_failed=2, depth_rows=5)
    assert ok["state"] == "OK" and ok["codes"] == []
    bad = M.source_state(newest_export_time=now - 37 * 3600, now=now, reads_total=40, reads_failed=10, depth_rows=0)
    assert bad["state"] == "SOURCE_PROBLEM" and bad["codes"] == ["SOURCE_STALE", "SOURCE_FAILURE", "COLLECTOR_NOT_DEPLOYED"]
    assert M.source_state(newest_export_time=None, now=now, reads_total=0, reads_failed=0, depth_rows=0)["codes"][0] == "SOURCE_STALE"
    assert M.regime_drift(["QUIET/RISK_OFF"] * 5, ["QUIET/RISK_OFF", "ACTIVE/RISK_ON"])["state"] == "OK"
    assert M.regime_drift(["ACTIVE/RISK_OFF"] * 4 + ["QUIET/RISK_OFF"], ["QUIET/RISK_OFF"])["state"] == "DRIFT_ALERT"
    assert M.regime_drift(["WARMUP"] * 3, ["QUIET/RISK_OFF"])["state"] == "INSUFFICIENT_DATA"
    cut = C.parse_utc("2026-10-17T00:00:00Z")
    a = M.model_age(C.parse_utc("2026-10-27T13:00:00Z"), cut, [P0 + 3600])
    assert a["state"] == "OK" and a["stale_after_utc"] == "2026-10-31T00:00:00Z" and 3 < a["days_left"] < 4
    assert M.model_age(C.parse_utc("2026-10-27T13:00:00Z"), cut, [C.parse_utc("2026-10-31T00:00:01Z")])["state"] == "MODEL_STALE"


def test_p10_an_always_negative_model_on_a_rare_event_has_a_good_brier_and_no_minority_metric():
    from memelab.predictive import stats as K
    y = [1] * 3 + [0] * 297
    p = [0.0] * 300
    assert K.brier(y, p) == pytest.approx(0.01)
    note = M.minority_note(y, p)
    assert note["constant_prediction"] and "CONSTANT_PREDICTION" in note["flags"] and note["auc"] is None
    rng = np.random.default_rng(5)
    yy = [1] * 15 + [0] * 45
    good = M.minority_note(yy, list(rng.uniform(0.6, 0.9, 15)) + list(rng.uniform(0.0, 0.4, 45)))
    assert good["auc"] == pytest.approx(1.0) and not good["constant_prediction"]


# ---------------------------------------------------------------- response, notices (rule 10), P39 and P47
def test_response_policy_table_never_retrains():
    assert M.response(["DRIFT_ALERT"], pin_mode="CHAMPION", level="VALIDATED_EXPERIMENTAL")["action"] == "DEGRADE_TO_SHADOW"
    assert M.response(["DRIFT_ALERT"], pin_mode="CHAMPION", level="SHADOW")["action"] == "ROLLBACK_TO_ABSTAIN"
    assert M.response(["MODEL_STALE"], pin_mode="CHAMPION", level="SHADOW")["action"] == "ROLLBACK_TO_ABSTAIN"
    assert M.response(["DRIFT_ALERT", "SUPPORT_BELOW_MINIMUM"], pin_mode="NO_VIABLE_CHAMPION", level=None)["action"] == "KEEP_ABSTAIN"
    assert M.response(["SOURCE_STALE"], pin_mode="NO_VIABLE_CHAMPION", level=None)["action"] == "KEEP_ABSTAIN_SOURCE"
    assert M.response(["SOURCE_FAILURE"], pin_mode="CHAMPION", level="SHADOW")["action"] == "KEEP_ABSTAIN_SOURCE"
    assert M.response([], pin_mode="CHAMPION", level="SHADOW")["action"] == "NO_CHANGE"
    for st in (["DRIFT_ALERT"], [], ["SOURCE_STALE"]):
        for pm in ("CHAMPION", "NO_VIABLE_CHAMPION"):
            r = M.response(st, pin_mode=pm, level="SHADOW")
            assert r["automatic_retrain"] is False and r["earlier_records"] == "UNCHANGED"


def test_notice_text_is_plain_and_refuses_trading_words():
    act = M.response(["DRIFT_ALERT"], pin_mode="NO_VIABLE_CHAMPION", level=None)
    t = M.notice("T1 (24 hours, +25% before -15%)", ["DRIFT_ALERT"], act, ["label-rate monitor DRIFT_ALERT on 40 events"])
    low = t.lower()
    assert "retrained automatically" in low and "abstain" in low
    assert not any(__import__("re").search(r"\b" + w + r"\b", low) for w in AB.TRADING_WORDS)
    with pytest.raises(ValueError):
        M.notice("T1", ["DRIFT_ALERT"], act, ["time to buy"])


def test_p47_source_outage_keeps_abstaining_with_a_visible_status():
    now = P0 + 4 * 86400
    s = M.source_state(newest_export_time=now - 40 * 3600, now=now, reads_total=10, reads_failed=5, depth_rows=0)
    st = M.target_states([s])
    assert st == ["COLLECTOR_NOT_DEPLOYED", "SOURCE_FAILURE", "SOURCE_STALE"]
    assert M.response(st, pin_mode="NO_VIABLE_CHAMPION", level=None)["action"] == "KEEP_ABSTAIN_SOURCE"
    assert M.response(st, pin_mode="CHAMPION", level="SHADOW")["action"] == "KEEP_ABSTAIN_SOURCE"   # a source outage is no model drift


def test_p39_drift_rolls_a_fixture_champion_back_through_the_registry_and_keeps_history():
    rp = _load("p19_run_prospective", "audits/predictive-intelligence/phase_19/probes/run_prospective.py")
    r = rp.rollback_demo()
    assert r["serve_at_alarm"]["use_champion"] is False and r["serve_at_alarm"]["rollback_required"] is True
    assert "DRIFT_ALERT" in r["serve_at_alarm"]["blocking"]
    assert r["response_1"]["action"] == "DEGRADE_TO_SHADOW" and r["rollback_1"]["champion_is_b2"]
    assert r["response_2"]["action"] == "ROLLBACK_TO_ABSTAIN" and r["rollback_2"]["mode"] == "NO_VIABLE_CHAMPION"
    assert r["earlier_pin_unchanged"] and r["log_append_only"] and r["evidence_class"] == "FIXTURE_TEST_ONLY"


def test_p46_a_feature_version_change_without_retrain_is_incompatible():
    reg = _load("p19_reg_fx", "tests/test_predictive_registry.py")
    ents, ctx = reg.fixture_registry()
    e = ents[ctx["model"]]
    rt = reg.runtime()
    assert R.compatibility(e, runtime=rt) == []
    rt2 = dict(rt, feature_version="3")
    states = {x["state"] for x in R.compatibility(e, runtime=rt2)}
    assert R.INCOMPATIBLE in states or R.FEATURE_SCHEMA_MISMATCH in states


# ---------------------------------------------------------------- misses (prompt item 5)
def test_misses_list_every_pair_with_its_document_outcome_and_reason(led):
    M.append(led, [outcome(), doc(key=KEY_B, mint=MINT_B, fid="fc_b")])
    rows = M.misses(M.load(led), as_of=LATE)
    by = {(r["decision_key"], r["target"]): r for r in rows}
    assert by[(KEY, L.T1)]["outcome_state"] == "LABELED" and by[(KEY, L.T1)]["no_score_reason"] == "ABSTAIN_NOT_SCORED"
    assert by[(KEY_B, L.T1)]["outcome_state"] == "NO_OUTCOME_ENTRY" and by[(KEY_B, L.T1)]["document_status"] == "ABSTAIN"
    assert by[(KEY, L.T1)]["reference_b2_has_number"] is True


# ---------------------------------------------------------------- isolation (rule 13)
def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_monitoring_imports_numpy_stdlib_and_four_named_package_modules_only():
    p = ROOT / "memelab/predictive/monitoring.py"
    std = {"__future__", "hashlib", "json", "math", "re", "pathlib", "typing"}
    assert _imports(p) <= std | {"numpy", "."}
    rel = {a.name for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert rel == {"baselines", "contract", "labels", "stats"}
    txt = p.read_text()
    for banned in ("evaluation", "registry", "calibration", "abstention", "integration", "reports", "socket", "urllib", "subprocess"):
        assert f"import {banned}" not in txt and f"from . import {banned}" not in txt, banned


def test_no_module_imports_monitoring():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "monitoring.py" and p.parent.name == "predictive":
            continue
        imps = _imports(p)
        rel = {a.name for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.ImportFrom) and n.level >= 1 for a in n.names}
        assert not any(i.endswith("monitoring") for i in imps) and "monitoring" not in rel, p
        assert "predictive.monitoring" not in p.read_text(), p


# ---------------------------------------------------------------- repair pass 2 (CP19-1, PI-D-107): CX-SK19, the skeptic's survivors, minors
def test_cx_sk19_a_revision_citing_the_read_it_revises_or_no_read_is_refused(led):
    first = outcome(label=1, cls="TARGET_FIRST")
    M.append(led, [first])
    mat = C.label_matures_at(L.T1, DT)
    same = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="LATER_READ",
                   recorded=mat + 9999)                       # same response key and body sha256: the read being replaced
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [same])
    assert e.value.code == "REVISION_NEEDS_A_LATER_READ"
    same_body = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="LATER_READ", rk="rk9",
                        observed=mat + 999, recorded=mat + 9999)   # another key, same body
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [same_body])
    assert e.value.code == "REVISION_NEEDS_A_LATER_READ"
    earlier = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="LATER_READ", rk="rk9",
                      body="9" * 64, observed=mat + 30, recorded=mat + 9999)   # captured before the revised read
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [earlier])
    assert e.value.code == "REVISION_NEEDS_A_LATER_READ"
    no_read = outcome(state="VENDOR_OR_ROUTE_GAP", revision_of=first["outcome_id"], revision_reason="x", recorded=mat + 9999)
    with pytest.raises(M.LedgerError) as e:                  # skeptic A6: revised to censored without any read
        M.append(led, [no_read])
    assert e.value.code == "REVISION_NEEDS_A_LATER_READ"
    ok = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="REREAD_48H", rk="rk9",
                 body="9" * 64, observed=mat + 172900, recorded=mat + 173000)
    assert M.append(led, [ok])["appended"] == 1 and M.verify(led)["ok"]
    # the same-read revision written around append is caught by verify and refused by load
    ents = M.read_ledger(led.read_text())
    sneak = outcome(label=1, cls="TARGET_FIRST", revision_of=ok["outcome_id"], revision_reason="LATER_READ", rk="rk9", body="9" * 64,
                    observed=mat + 172999, recorded=mat + 174000)
    led.write_text(led.read_text() + M.canon(M.seal(sneak, seq=len(ents), prev=ents[-1]["sha"])) + "\n")
    assert not M.verify(led)["ok"]
    with pytest.raises(M.LedgerError):
        M.load(led)


def test_cx_sk19_a_pending_is_superseded_only_by_a_later_read_or_an_unread_gap_after_maturity(led):
    mat = C.label_matures_at(L.T1, DT)
    p = outcome(state="PENDING", recorded=mat - 3600)
    M.append(led, [p])
    early_gap = outcome(state="VENDOR_OR_ROUTE_GAP", supersedes=p["outcome_id"], recorded=mat - 60)   # skeptic A7
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [early_gap])
    assert e.value.code == "REVISION_NEEDS_A_LATER_READ"
    late_gap = outcome(state="VENDOR_OR_ROUTE_GAP", supersedes=p["outcome_id"], recorded=mat + 60)
    assert M.append(led, [late_gap])["appended"] == 1


def test_k9_a_revision_without_a_reason_is_refused(led):
    first = outcome()
    M.append(led, [first])
    mat = C.label_matures_at(L.T1, DT)
    r = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason=None, rk="rk2", body="c" * 64,
                observed=mat + 9000, recorded=mat + 9100)
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [r])
    assert e.value.code == "FINAL_OUTCOME_REPLACED"


def test_k3_k4_scorable_is_as_of_the_record_and_read_times_even_on_an_unchecked_index(led):
    mat = C.label_matures_at(L.T1, DT)
    late_rec = outcome(recorded=mat + 5000)
    M.append(led, [late_rec])
    idx = M.load(led)
    assert M.scorable(idx, mat + 4999) == [] and len(M.scorable(idx, mat + 5000)) == 1      # K4: recorded after as_of
    bad = outcome(key=KEY_B, mint=MINT_B, observed=mat - 10)                                  # K3: read before maturity
    ents = M.read_ledger(led.read_text())
    led.write_text(led.read_text() + M.canon(M.seal(bad, seq=len(ents), prev=ents[-1]["sha"])) + "\n")
    raw = M.Index(M.read_ledger(led.read_text()))
    assert all(o["decision_key"] != KEY_B for o in M.scorable(raw, LATE))


def test_k8_a_later_read_that_changes_the_class_but_not_the_state_is_recorded_as_a_revision(tmp_path):
    p = tmp_path / "l.jsonl"
    M.append(p, [pset(decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT}])])
    d = dec()
    b = L.needed_boundary(L.T2, DT)
    rd1 = mkread(path_rows(up=True), b, LATE)
    M.append(p, M.next_outcomes(M.load(p), M.prospective_records(L.Universe([d], as_of=LATE, read_of={KEY: rd1})), recorded_at=LATE))
    rd2 = mkread(path_rows(up=False), b, LATE + 172800)       # a later read whose candles were revised
    recs2 = M.prospective_records(L.Universe([d], as_of=LATE + 172800, read_of={KEY: rd2}))
    nxt = M.next_outcomes(M.load(p), recs2, recorded_at=LATE + 172800, reason="REREAD_48H")
    t1 = [x for x in nxt if x["target"] == L.T1]
    assert t1 and t1[0]["state"] == "LABELED" and t1[0]["label_class"] == "INVALIDATION_FIRST" and t1[0]["revision_of"]
    assert t1[0]["response_key"] == rd2.response_key and t1[0]["revision_reason"] == "REREAD_48H"
    M.append(p, nxt)
    cur = M.current_outcomes(M.load(p))[(KEY, L.T1)]
    assert cur["label"] == 0 and "REVISED" in cur["flags"] and M.verify(p)["ok"]


def test_a_read_whose_boundary_stops_before_a_matured_window_is_a_visible_plan_gap():
    rows = path_rows(up=True)
    rd = mkread(rows, L.needed_boundary(L.T1B, DT), LATE)    # a T1b boundary read long after every maturity
    recs = {r["target"]: r for r in M.prospective_records(L.Universe([dec()], as_of=LATE, read_of={KEY: rd}))}
    assert recs[L.T1B]["state"] == "LABELED"
    assert recs[L.T1]["state"] == "NOT_READ" and recs[L.T1]["detail"] == "READ_BOUNDARY_BEFORE_WINDOW_END" and recs[L.T1]["label"] is None


def test_k11_a_prediction_for_an_unknown_decision_or_another_mint_is_refused(led):
    for bad in (pred(key="k-unknown"), pred(key=KEY_B, mint=MINT)):
        bad["prediction_id"] = "pr_" + bad["decision_key"] + bad["mint"][:4]
        with pytest.raises(M.LedgerError) as e:
            M.append(led, [bad])
        assert e.value.code == "IDENTITY_MISMATCH"
    d = doc(key=KEY_B, mint=MINT, fid="fc_wrong")
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [d])
    assert e.value.code == "IDENTITY_MISMATCH"


def test_k15_a_prediction_set_reusing_a_decision_key_with_another_identity_is_refused(led):
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [pset(set_id="ps_2", decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT_B, "decision_time": DT}])])
    assert e.value.code == "IDENTITY_MISMATCH"
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [pset(set_id="ps_3", decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT + 1}])])
    assert e.value.code == "IDENTITY_MISMATCH"
    assert M.append(led, [pset(set_id="ps_4", decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT}])])["appended"] == 1


def test_k12_load_refuses_a_duplicated_entry_even_with_a_valid_chain(led):
    ents = M.read_ledger(led.read_text())
    dup = ents[2]["payload"]                                  # the first PREDICTION, sealed again at the end
    led.write_text(led.read_text() + M.canon(M.seal(dup, seq=len(ents), prev=ents[-1]["sha"])) + "\n")
    M.read_ledger(led.read_text())
    with pytest.raises(M.LedgerError) as e:
        M.load(led)
    assert e.value.code == "DUPLICATE_ENTRY"
    assert not M.verify(led)["ok"]


def test_k13_misses_mark_a_label_not_matured_at_the_evaluation_time(led):
    M.append(led, [outcome()])
    mat = C.label_matures_at(L.T1, DT)
    rows = {(r["decision_key"], r["target"]): r for r in M.misses(M.load(led), as_of=mat - 1)}
    assert rows[(KEY, L.T1)]["outcome_state"] == "NOT_MATURED_AT_EVALUATION"
    assert rows[(KEY, L.T1)]["no_score_reason"] == "NOT_MATURED_AT_EVALUATION"


def test_k17_page_hinkley_orders_the_stream_by_time():
    rng = np.random.default_rng(17)
    jump = [(float(i), float(rng.normal(0, 0.01) + (0.1 if i >= 60 else 0.0))) for i in range(200)]
    want = M.page_hinkley_alarms(jump)["alarms"]
    shuffled = list(jump)
    rng.shuffle(shuffled)
    assert want and M.page_hinkley_alarms(shuffled)["alarms"] == want
    assert M.page_hinkley_alarms(list(reversed(jump)))["alarms"] == want


def test_k7_m4_d6_alerts_above_the_share_of_final_reads_and_reports_retries_apart():
    now = P0 + 3 * 86400
    at = M.source_state(newest_export_time=now, now=now, reads_total=25, reads_failed=5, depth_rows=1, attempts_total=39, attempts_failed=11)
    assert at["read_failure_share"] == 0.2 and "SOURCE_FAILURE" not in at["codes"] and at["state"] == "OK"
    assert at["attempts_total"] == 39 and at["attempts_failed"] == 11
    above = M.source_state(newest_export_time=now, now=now, reads_total=25, reads_failed=6, depth_rows=1)
    assert "SOURCE_FAILURE" in above["codes"]
    retried = M.source_state(newest_export_time=now, now=now, reads_total=25, reads_failed=0, depth_rows=0, attempts_total=39, attempts_failed=11)
    assert retried["codes"] == ["COLLECTOR_NOT_DEPLOYED"]


def test_m3_d1_is_insufficient_when_a_column_cannot_be_measured_and_ok_only_when_every_column_is():
    rng = np.random.default_rng(3)
    ref = {"a": list(rng.normal(0, 1, 4000)), "b": list(rng.normal(0, 1, 4000))}
    one_short = M.feature_drift(ref, {"a": list(rng.normal(0, 1, 2000)), "b": list(rng.normal(0, 1, 29))})
    assert one_short["state"] == "INSUFFICIENT_DATA" and one_short["columns_ok"] == 1 and one_short["columns_insufficient"] == 1
    both = M.feature_drift(ref, {"a": list(rng.normal(0, 1, 2000)), "b": list(rng.normal(0, 1, 2000))})
    assert both["state"] == "OK" and both["columns_ok"] == 2
    alert = M.feature_drift(ref, {"a": list(rng.normal(2, 1, 100)), "b": list(rng.normal(0, 1, 29))})
    assert alert["state"] == "DRIFT_ALERT"


def test_m5_a_pinned_champion_below_the_support_minimum_keeps_abstaining():
    assert M.response(["SUPPORT_BELOW_MINIMUM"], pin_mode="CHAMPION", level="SHADOW")["action"] == "KEEP_ABSTAIN"
    assert M.response(["SUPPORT_BELOW_MINIMUM", "DRIFT_ALERT"], pin_mode="CHAMPION", level="SHADOW")["action"] == "ROLLBACK_TO_ABSTAIN"


def test_x4_a_revision_read_must_carry_the_token_of_its_mint(led):
    first = outcome()
    M.append(led, [first])
    mat = C.label_matures_at(L.T1, DT)
    r = outcome(label=0, cls="INVALIDATION_FIRST", revision_of=first["outcome_id"], revision_reason="REREAD_48H", rk="rk2", body="c" * 64,
                observed=mat + 9000, recorded=mat + 9100)
    r["request_url"] = "https://api.geckoterminal.com/x?token=" + MINT_B
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [r])
    assert e.value.code == "IDENTITY_MISMATCH"
    u = outcome(state="UNVERIFIABLE_NO_VENDOR_HISTORY", revision_of=first["outcome_id"], revision_reason="REREAD_48H",
                recorded=mat + 9100, conservative_lens=0)
    u.update(response_key="rk3", body_sha256="d" * 64, label_observed_at=mat + 9000,
             request_url="https://api.geckoterminal.com/x?token=" + MINT_B)       # a censored revision citing another mint's read
    with pytest.raises(M.LedgerError) as e:
        M.append(led, [u])
    assert e.value.code == "IDENTITY_MISMATCH"
    u["request_url"] = "https://api.geckoterminal.com/x?token=" + MINT
    assert M.append(led, [u])["appended"] == 1


def test_x8_a_revision_to_a_state_without_a_label_still_cites_its_later_read(tmp_path):
    p = tmp_path / "l.jsonl"
    M.append(p, [pset(decisions=[{"decision_key": KEY, "chain": "solana", "mint": MINT, "decision_time": DT}])])
    d = dec()
    b = L.needed_boundary(L.T2, DT)
    rd1 = mkread(path_rows(up=True), b, LATE)
    M.append(p, M.next_outcomes(M.load(p), M.prospective_records(L.Universe([d], as_of=LATE, read_of={KEY: rd1})), recorded_at=LATE))
    s0 = int(L.ceil_grid(TE))
    rd2 = mkread([H.candle(s, c=1.0) for s in range(s0, int(TE + 2 * 86400 + 600), 300)], b, LATE + 172800)   # no reference candle now
    recs2 = M.prospective_records(L.Universe([d], as_of=LATE + 172800, read_of={KEY: rd2}))
    nxt = M.next_outcomes(M.load(p), recs2, recorded_at=LATE + 172800, reason="REREAD_48H")
    assert nxt and all(x["state"] != "LABELED" and x["label"] is None for x in nxt)
    assert all(x["response_key"] == rd2.response_key and x["body_sha256"] == rd2.body_sha256 for x in nxt)
    M.append(p, nxt)
    assert M.verify(p)["ok"] and M.scorable(M.load(p), LATE + 172800) == []

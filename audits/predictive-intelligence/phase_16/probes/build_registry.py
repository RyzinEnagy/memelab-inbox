"""Phase 16 recorded run: registry-1 over the 69 frozen holdout-start cards, the champion policy, the identical-inference check,
the ensemble ablation, compatibility (P46), staleness, rollback and the registry's answer today.

    python -B build_registry.py OUTDIR [--dev-store PATH] [--feature-store PATH]

OUTDIR is the phase folder for the recorded run (audits/predictive-intelligence/phase_16) or a scratch folder for the
determinism repeat. Inputs, all read-only: the committed cards and Phase 12, 13 and 07 to 11 outputs; the Phase 05 feature store
and the Phase 06 development store (features of the holdout decisions, no label; development labels only through
`labels.training_labels`, to check the committed out-of-fold rows); the opened holdout only through committed Phase 12 files and
only for POST_OPENING descriptions. Never `phase_06/sealed/`. No network (audit hook), no clock in any output except the run log
and the latency file. Pre-registration: ../ACCEPTANCE_CHECKLIST.md, PI-D-085.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import abstention as AB  # noqa: E402
from memelab.predictive import analog as A  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import calibration as CAL  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import onchain as O  # noqa: E402
from memelab.predictive import registry as R  # noqa: E402
from memelab.predictive import socialcat as SC  # noqa: E402
from memelab.predictive import technical as T8  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 16 runner makes no network call ({event})")


sys.addaudithook(_hook)


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RH = _load("p12_run_holdout", "audits/predictive-intelligence/phase_12/probes/run_holdout.py")
P7 = RH.P7

AUD = REPO / "audits/predictive-intelligence"
P12V = AUD / "phase_12/validation"
SHORT = P7.SHORT
LONG = {v: k for k, v in SHORT.items()}
TARGETS = (L.T1, L.T1B, L.T2)
H, END = L.holdout_start(), L.prospective_start()
REGISTERED_AS_OF = "2026-10-27T00:00:00Z"
TODAY = "2026-10-27T00:00:00Z"
STALE_PROBE = "2026-10-31T00:00:01Z"
EDGE_PROBE = "2026-10-31T00:00:00Z"
REPS, SEED = 2000, 20261025
FAMILY_MODULES = {"07": F, "08": T8, "09": O, "10": SC, "11": A}
FAMILY_VERSION_KEYS = {"07": None, "08": "tech_version", "09": "onchain_version", "10": "socialcat_version", "11": "analog_version"}


def module_version(card: dict, phase: str) -> str:
    k = FAMILY_VERSION_KEYS[phase]
    return card[k] if k else R.PHASE07_FAMILY_VERSION
PREDICT = RH.PREDICT
DEV_METRICS = {"07": "phase_07/experiments/BASELINE_METRICS.csv", "08": "phase_08/experiments/TECHNICAL_METRICS.csv",
               "09": "phase_09/experiments/ONCHAIN_METRICS.csv", "10": "phase_10/experiments/SOCIAL_METRICS.csv",
               "11": "phase_11/experiments/ANALOG_METRICS.csv"}
OOS = {"07": AUD / "phase_07/experiments/OOS_PREDICTIONS.csv", "09": AUD / "phase_09/experiments/OOS_PREDICTIONS.csv",
       "10": AUD / "phase_10/experiments/OOS_PREDICTIONS.csv"}
EXPECTED_N_SEARCH = {"before": 121, "after": 130, "sensitivity_before": 160, "sensitivity_after": 169}
CODE = ["memelab/predictive/registry.py", "memelab/predictive/abstention.py", "memelab/predictive/calibration.py",
        "memelab/predictive/evaluation.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
        "memelab/predictive/contract.py", "memelab/predictive/features.py", "memelab/predictive/labels.py",
        "audits/predictive-intelligence/phase_16/probes/build_registry.py",
        "audits/predictive-intelligence/phase_12/probes/run_holdout.py"]
DEBUG_RUNS: list[str] = [           # every run of this file on real data before the frozen code (P22), all into the scratchpad
    "dbg1 2026-10-27T03:02:24Z at uncommitted code: stopped while taking the before-state of phase_06/sealed/ (IsADirectoryError on "
    "raw/); it had computed the sha256 of the bytes of SEAL.json, holdout_labels.jsonl.gz, label_calls.json and others_summary.json "
    "(the same hashes check_seal.py computes; nothing decompressed, parsed, printed or stored); the before and after state is now "
    "size and mtime only, the sealed files are never opened",
    "dbg2 2026-10-27T03:02:36Z: stopped in run_holdout.load_cards (its glob of phase_*/artifacts/T*/*.json meets the Phase 13 "
    "calibration cards, KeyError '13'); cards are now loaded from the paths in CANDIDATES.json",
    "dbg3 2026-10-27T03:02:53Z: ran through the inference check and the ensemble step, stopped at the T2 in-sample stacking trap "
    "(no T2 row has both B2 and S1, so the trap had no rows); the trap now uses the B0 and B2 out-of-fold rows, which exist on every "
    "target; no rule, threshold, configuration or output definition changed",
    "dbg4 2026-10-27T03:03:25Z: complete, 69 entries (ABSTAIN 6, NO_GO 63), 69 of 69 inference equal, NO_ENSEMBLE x3, N_search 130, "
    "no failure; used to check the outputs; then tests were added for four surviving mutations (registry.py unchanged by them)",
]
LABEL_CALLS = [0]
CANDIDATE_ROWS: list[dict] = []
ENS_LATENCY: dict[str, dict] = {}


def fsha(p) -> str:
    return P7.fsha(p)


def iso(t) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


def write_csv(path: Path, rows: list[dict]) -> None:
    RH.write_csv(path, rows)


def read_csv(p: Path) -> list[dict]:
    with open(p) as f:
        return list(csv.DictReader(f))


def fnum(s) -> float:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def seal_stat() -> dict:
    """Size and modification time of every file under phase_06/sealed/ (stat only, the files are never opened)."""
    root = AUD / "phase_06/sealed"
    return {q.relative_to(root).as_posix(): [q.stat().st_size, q.stat().st_mtime_ns] for q in sorted(root.rglob("*")) if q.is_file()}


def rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def git(*a: str) -> str:
    return RH.git(*a)


# ---------------------------------------------------------------- inputs
def runtime_facts() -> dict:
    """What the running code says (rule 6): feature set sha per family, feature version, family versions, registry, labels."""
    return {"feature_set_sha": {ph: m.feature_set_sha() for ph, m in FAMILY_MODULES.items()}, "feature_version": F.FEATURE_VERSION,
            "family_version": {"07": R.PHASE07_FAMILY_VERSION, "08": T8.TECH_VERSION, "09": O.ONCHAIN_VERSION,
                               "10": SC.SOCIALCAT_VERSION, "11": A.ANALOG_VERSION},
            "registry_sha": C.registry_sha256(), "labels_version": L.LABELS_VERSION}


def load_candidates() -> tuple[dict, dict]:
    cand = json.loads((P12V / "CANDIDATES.json").read_text())
    CANDIDATE_ROWS[:] = cand["candidates"]
    # driven by CANDIDATES.json, not by a glob: `run_holdout.load_cards` globs phase_*/artifacts/T*/*.json and since Phase 13
    # also meets the calibration cards (KeyError '13'), so the Phase 12 plan step no longer reruns as committed (recorded)
    cards = {}
    for c in cand["candidates"]:
        p = REPO / c["path"]
        ph = c["phase"]
        card = RH.LOADERS[ph](p.read_text())
        if card["targets"] != [LONG[c["target_short"]]] or float(card["training_cutoff"]) != H:
            raise SystemExit(f"{p}: card target or cutoff is not the frozen one")
        E.check_card_time(card, [H])
        cards[(c["target_short"], c["candidate"])] = {"card": card, "path": c["path"], "phase": ph, "fitted": "abstain" not in card["body"]}
    if len(cards) != 69 or len(cand["candidates"]) != 69:
        raise SystemExit("the registry takes exactly the 69 frozen cards of Phase 12")
    for c in cand["candidates"]:
        v = cards[(c["target_short"], c["candidate"])]
        if v["path"] != c["path"] or fsha(REPO / c["path"]) != c["file_sha256"] or v["card"]["model_sha"] != c["model_sha"]:
            raise SystemExit(f"{c['candidate']} {c['target_short']}: card differs from CANDIDATES.json")
        if R.card_sha_of(v["card"]) != v["card"]["model_sha"]:
            raise SystemExit(f"{c['candidate']}: the registry's canonical sha differs from the family's model sha")
    return cand, cards


def dev_verdicts() -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    for ph, relp in DEV_METRICS.items():
        for r in read_csv(AUD / relp):
            if r["view"] != "ALL":
                continue
            model = r.get("model") or r.get("baseline")
            out.setdefault((r["target_short"], f"P{ph}_{model}"), []).append(
                {"reference": r.get("reference") or "B0", "verdict": r["verdict"], "n_with_number": int(fnum(r["n_with_number"]) if r["n_with_number"] else 0),
                 "positives": int(fnum(r["positives"])) if r.get("positives") else None,
                 "decision_days": int(fnum(r["decision_days"])) if r.get("decision_days") else None})
    return out


# ---------------------------------------------------------------- inference (rule 7)
def inference_check(cards: dict, dev_path: str, fs_path: str) -> tuple[dict, dict, dict, dict]:
    recorded: dict[tuple[str, str], dict[str, tuple[str, str]]] = {}
    for r in read_csv(P12V / "HOLDOUT_PREDICTIONS.csv"):
        if r["candidate"].startswith("NC1_"):
            continue
        recorded.setdefault((r["target_short"], r["candidate"]), {})[r["decision_key"]] = (r["number"], r["why"])
    inp = RH.Inputs(dev_path, fs_path)
    out, fam_cache, latency = {}, {}, {}
    for t in TARGETS:
        s = SHORT[t]
        ex = inp.examples(t)
        fam_ex = {ph: inp.family(ph, ex) for ph in RH.LOADERS}
        fam_cache[s] = (ex, fam_ex)
        probe_sha = R.sha([[e.decision_key, e.mint, e.decision_time] for e in sorted(ex, key=lambda e: e.decision_key)])
        for (ss, cid), v in sorted(cards.items()):
            if ss != s:
                continue
            p, why = E.score(v["card"], fam_ex[v["phase"]], PREDICT[v["phase"]])
            rows = [(e.decision_key, float(pv) if math.isfinite(pv) else None, w or "") for e, pv, w in zip(ex, p, why)]
            rec = recorded[(s, cid)]
            diffs = [e.decision_key for e, pv, w in zip(ex, p, why) if (RH.num(float(pv)), w or "") != rec.get(e.decision_key)]
            if len(rec) != len(ex):
                diffs.append("ROW_COUNT")
            c0 = time.process_time()
            reps = 5
            for _ in range(reps):
                PREDICT[v["phase"]](v["card"], fam_ex[v["phase"]])
            latency[f"{s}:{cid}"] = {"cpu_us_per_decision": 1e6 * (time.process_time() - c0) / (reps * max(1, len(ex))),
                                     "decisions": len(ex)}
            out[(s, cid)] = {"probe_set": "phase_12 Solana holdout decisions, inputs only (run_holdout.Inputs), no label",
                             "probe_set_sha": probe_sha, "rows": len(rows),
                             "numbers": sum(1 for r in rows if r[1] is not None),
                             "abstentions": dict(sorted(Counter(r[2] for r in rows if r[1] is None).items())),
                             "outputs_sha": R.inference_hash(rows),
                             "recorded_predictions_file": "audits/predictive-intelligence/phase_12/validation/HOLDOUT_PREDICTIONS.csv",
                             "recorded_predictions_sha256": fsha(P12V / "HOLDOUT_PREDICTIONS.csv"),
                             "equal_to_recorded": not diffs, "differences": len(diffs)}
    return out, fam_cache, latency, {"inputs": inp}


def synthetic_examples() -> list[B.Example]:
    d = json.loads((REPO / "tests/fixtures/predictive/registry_probe_examples.json").read_text())
    return [B.Example(decision_key=r["decision_key"], chain=r["chain"], mint=r["mint"], decision_time=r["decision_time"],
                      label_matures_at=r["decision_time"] + 86400.0, y=-1,
                      x={k: (float("nan") if v is None else float(v)) for k, v in r["x"].items()}, avail=r["avail"],
                      status=r["status"]) for r in d["rows"]]


def synthetic_hash(card: dict) -> str:
    ex = synthetic_examples()
    p, why = B.predict(card, ex)
    return R.inference_hash([(e.decision_key, float(pv) if math.isfinite(pv) else None, w or "") for e, pv, w in zip(ex, p, why)])


# ---------------------------------------------------------------- facts and entries (rules 3 and 4)
def facts_for(s: str, cid: str, v: dict, metrics: dict, post: dict, cal_cards: dict, tests: dict) -> dict:
    """The entry's facts through `registry.derive_facts` (CP16-0), so any verifier rebuilds them the same way."""
    return R.derive_facts(candidate=cid, phase=v["phase"], card=v["card"], tests=tests_for(v, tests),
                          m_b0=metrics.get((s, cid, "P07_B0")), m_b2=metrics.get((s, cid, "P07_B2")), post_states=post.get((s, cid), {}),
                          cal_card=cal_cards[s] if cid == "P07_B2" else None)


def tests_for(v: dict, tests: dict) -> dict:
    """Pre-opening checks per card (CP16-0): leakage from Phase 12's traps and replay audit; provenance from the card's own file
    and model hashes; contract from its registry fingerprint."""
    c = next(x for x in CANDIDATE_ROWS if x["path"] == v["path"])
    prov = R.sha_bytes((REPO / v["path"]).read_bytes()) == c["file_sha256"] and R.card_sha_of(v["card"]) == v["card"]["model_sha"] == c["model_sha"]
    return {"leakage": tests["leakage"], "provenance": prov, "contract": v["card"]["registry_sha"] == C.registry_sha256(),
            "basis": tests["basis"]}


def risk_flags(s: str, cid: str, v: dict, facts: dict) -> list[str]:
    fl = ["PRICE_PATH_NOT_PROCEEDS", "NO_HISTORICAL_EXECUTABLE_DEPTH", C.backtest_status(), "NO_NET_TRADING_EDGE_CLAIMABLE",
          "RETROSPECTIVE_HOLDOUT_SPENT", "UNCALIBRATED", "MODEL_STALE_AFTER_" + iso(float(v["card"]["training_cutoff"]) + C.ACCEPTANCE["max_model_age_s"])[:10],
          "CURRENT_VENDOR_LIST_ROUTE_ABSTAINS"]
    ph = v["phase"]
    if ph == "08":
        fl += ["PIT_ROUTE_ONLY", "NO_HOLDOUT_EVALUATION"]
    if ph == "11":
        fl += ["COHORT_NUMBER_NOT_A_PROBABILITY"]
    if ph == "10":
        fl += ["CATALYST_TABLES_NOT_EXPORTED", "SOCIAL_TABLES_NOT_EXPORTED"]
    if s == "T2_24h":
        fl += ["T2_HOLDOUT_POSSIBLE_PARTIAL_CONTACT_PI_D_045"]
    ret = facts.get("retrospective") or {}
    if ret.get("evaluation") == R.FIRST_OPENING and not ret.get("calibration_in_the_large_ok"):
        fl += ["RETROSPECTIVE_CALIBRATION_IN_THE_LARGE_FAILED"]
    if not facts["fitted"]:
        fl += ["NOT_FITTED_" + str(v["card"]["body"].get("abstain"))]
    return fl


def build_entries(cards, inference, metrics, post, cal_cards, cal_paths, tests, devv) -> dict[str, dict]:
    entries = {}
    for (s, cid), v in sorted(cards.items()):
        card = v["card"]
        facts = facts_for(s, cid, v, metrics, post, cal_cards, tests)
        inf = dict(inference[(s, cid)])
        if v["phase"] == "07":
            inf["synthetic_probe_set"] = "tests/fixtures/predictive/registry_probe_examples.json"
            inf["synthetic_probe_set_sha256"] = fsha(REPO / inf["synthetic_probe_set"])
            inf["synthetic_outputs_sha"] = synthetic_hash(card)
        cal = None
        if cid == "P07_B2":
            cc = cal_cards[s]
            cal = {"path": cal_paths[s], "card_sha": cc["card_sha"], "file_sha256": fsha(REPO / cal_paths[s]), "status": cc["status"],
                   "level": cc["level"], "details": list(cc["details"])}
        ev = {"development": devv.get((s, cid), []),
              "retrospective_first_opening": {"file": "audits/predictive-intelligence/phase_12/validation/HOLDOUT_METRICS.csv",
                                              "sha256": fsha(P12V / "HOLDOUT_METRICS.csv"),
                                              "primary_results_sha256": fsha(P12V / "PRIMARY_RESULTS.json"),
                                              "opening_log_sha256": fsha(P12V / "OPENING_LOG.json")},
              "selection_corrections": {"file": "audits/predictive-intelligence/phase_12/validation/POST_OPENING_CORRECTIONS.csv",
                                        "sha256": fsha(P12V / "POST_OPENING_CORRECTIONS.csv"), "label": "POST_OPENING (more conservative only)"},
              "candidates": {"file": "audits/predictive-intelligence/phase_12/validation/CANDIDATES.json",
                             "sha256": fsha(P12V / "CANDIDATES.json")},
              "prospective": {"status": "NOT_YET_MATURED"}}
        e = R.make_entry(target=LONG[s], family={"phase": v["phase"], "kind": card["kind"], "candidate": cid,
                                                 "module_version": module_version(card, v["phase"])}, card=card,
                         card_path=v["path"], card_file_sha256=fsha(REPO / v["path"]), calibration=cal, facts=facts, evidence=ev,
                         risk_flags=risk_flags(s, cid, v, facts), inference=inf, registered_as_of_utc=REGISTERED_AS_OF)
        R.verify_entry(e, card=card, card_bytes=(REPO / v["path"]).read_bytes(), cal_card=cal_cards[s] if cid == "P07_B2" else None)
        entries[e["entry_id"]] = e
    return entries


# ---------------------------------------------------------------- ensembles (rule 12)
def oos_rows(ph: str, target: str, col: str, labels: dict[str, dict]) -> list[dict]:
    s = SHORT[target]
    out = []
    for r in read_csv(OOS[ph]):
        if r["target_short"] != s:
            continue
        lab = labels.get(r["decision_key"])
        if lab is None or int(lab["label"]) != int(r["y"]):
            raise SystemExit(f"{s} phase {ph}: an out-of-fold row disagrees with training_labels")
        out.append({"fold": r["fold"], "decision_key": r["decision_key"], "cutoff": C.parse_utc(r["cutoff_utc"]),
                    "decision_time": C.parse_utc(r["decision_time_utc"]), "mint": r["mint"],
                    "label_matures_at": float(lab["label_matures_at"]), "y": int(r["y"]), "number": fnum(r[col]),
                    "why": r.get(col + "_why") or ""})
    return out


def eval_rows(oof: list[dict], name: str, numbers: list[float], ref: dict[str, list[float]]) -> list[dict]:
    rows = []
    for r, n in zip(oof, numbers):
        ex = B.Example(decision_key=r["decision_key"], chain="solana", mint=r["mint"], decision_time=r["decision_time"],
                       label_matures_at=r["label_matures_at"], y=int(r["y"]))
        row = {"y": int(r["y"]), "fold": r["fold"], "example": ex, name: float(n), name + "_why": "" if math.isfinite(n) else "MEMBER_ABSTAINED"}
        for k, vals in ref.items():
            row[k] = float(vals[len(rows)])
        rows.append(row)
    return rows


def summarize(res: dict) -> dict:
    keys = ("n_rows", "n_with_number", "positives", "prevalence", "days", "mints", "brier", "brier_ref", "bss", "log_loss",
            "log_loss_ref", "governing", "gov_ci", "p_one_sided", "verdict")
    return {k: res.get(k) for k in keys}


def ensembles(dev, cards: dict, fam_cache: dict, latency: dict) -> tuple[dict, list[dict], list[dict], list[dict]]:
    out, csv_rows, ledger, post_log = {}, [], [], []
    member_cols = {}
    for t in TARGETS:
        s = SHORT[t]
        member_cols[s] = {"B0": [], "B2": list(cards[(s, "P07_B2")]["card"]["body"]["columns"]),
                          "S1": list(cards[(s, "P10_S1_SC_LOGIT")]["card"]["body"]["spec"]["columns"]),
                          "M1": list(cards[(s, "P09_M1_OC_LOGIT")]["card"]["body"]["spec"]["columns"]),
                          "M2": list(cards[(s, "P09_M2_OC_LOGIT_B2")]["card"]["body"]["spec"]["columns"]),
                          "S2": list(cards[(s, "P10_S2_SC_LOGIT_B2")]["card"]["body"]["spec"]["columns"])}
    dev_res: dict[str, dict] = {}
    for t in TARGETS:
        s = SHORT[t]
        LABEL_CALLS[0] += 1
        labels = {r["decision_key"]: r for r in L.training_labels(dev, H, t, mode="provider")}
        rows = {"B0": oos_rows("07", t, "B0", labels), "B2": oos_rows("07", t, "B2", labels), "S1": oos_rows("10", t, "S1_SC_LOGIT", labels)}
        mc = member_cols[s]
        res_t: dict[str, dict] = {}
        traps = {}
        for name, mem in (("TRAP_ENS_MEAN_B2_M1_S1", ("B2", "M1", "S1")), ("TRAP_ENS_MEAN_B2_M2_S2", ("B2", "M2", "S2"))):
            try:
                R.check_members({m: mc[m] for m in mem})
                traps[name] = {"refused": False}
            except R.DoubleCountedEvidence as err:
                traps[name] = {"refused": True, "status": err.status, "detail": str(err)}
        for cfg, mem in (("ENS_MEAN_B0_B2", ("B0", "B2")), ("ENS_MEAN_B2_S1", ("B2", "S1"))):
            chk = R.check_members({m: mc[m] for m in mem})
            oof = R.out_of_fold_rows({m: rows[m] for m in mem})
            nums = [R.mean_ensemble(r["members"]) for r in oof]
            b0 = {(r["fold"], r["decision_key"]): r["number"] for r in rows["B0"]}
            b2 = {(r["fold"], r["decision_key"]): r["number"] for r in rows["B2"]}
            refs = {"B0": [b0[(r["fold"], r["decision_key"])] for r in oof], "B2": [b2[(r["fold"], r["decision_key"])] for r in oof]}
            er = eval_rows(oof, cfg, nums, refs)
            v0 = B.evaluate(er, cfg, reference="B0", reps=REPS, seed=SEED)
            v2 = B.evaluate(er, cfg, reference="B2", reps=REPS, seed=SEED)
            res_t[cfg] = {"members": list(mem), "sources": chk["sources"], "oof_rows": len(oof),
                          "rows_with_number": int(sum(1 for n in nums if math.isfinite(n))),
                          "folds": sorted({r["fold"] for r in oof}), "vs_B0": v0, "vs_B2": v2}
        # chronological stack: fit on earlier folds' out-of-fold rows, gated
        mem = ("B2", "S1")
        R.check_members({m: mc[m] for m in mem})
        oof = [r for r in R.out_of_fold_rows({m: rows[m] for m in mem}) if all(math.isfinite(r["members"][m]) for m in mem)]
        folds = sorted({r["fold"] for r in oof}, key=lambda f: int(f))
        stack_folds = []
        for fk in folds:
            ev_rows = [r for r in oof if r["fold"] == fk]
            cut = ev_rows[0]["cutoff"]
            fit = [r for r in oof if r["decision_time"] < cut and r["label_matures_at"] <= cut and r["fold"] != fk]
            R.check_stack_rows(fit, ev_rows)
            g = R.stack_gate(fit)
            stack_folds.append({"fold": fk, "cutoff_utc": iso(cut), "fit_rows": len(fit), "fit_positives": int(sum(r["y"] for r in fit)),
                                "eval_rows": len(ev_rows), "gate_shortfalls": g, "fitted": not g})
        trap_rows = R.out_of_fold_rows({m: rows[m] for m in ("B0", "B2")})      # rows exist on every target
        try:
            R.check_stack_rows(trap_rows, trap_rows)
            traps["TRAP_STACK_IN_SAMPLE"] = {"refused": False}
        except R.InSampleStacking as err:
            traps["TRAP_STACK_IN_SAMPLE"] = {"refused": True, "status": err.status, "detail": str(err)}
        res_t["STACK_CHRONO_B2_S1"] = {"members": list(mem), "folds": stack_folds,
                                       "fitted_folds": sum(1 for f in stack_folds if f["fitted"]),
                                       "verdict": "INSUFFICIENT_HISTORY" if not any(f["fitted"] for f in stack_folds) else "FITTED"}
        if any(f["fitted"] for f in stack_folds):
            raise SystemExit("a stack cleared its gate: the frozen plan has no evaluation step for it; stop and record")
        dev_res[s] = {"configurations": res_t, "traps": traps}
    # Holm across the three targets per configuration and reference (frozen verdict)
    for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1"):
        for refk in ("vs_B0", "vs_B2"):
            ps = [dev_res[SHORT[t]]["configurations"][cfg][refk].get("p_one_sided") for t in TARGETS]
            ph = E.holm([p if p is not None else 1.0 for p in ps])
            for t, p in zip(TARGETS, ph):
                res = dev_res[SHORT[t]]["configurations"][cfg][refk]
                res["p_holm"] = p
                res["verdict"] = B.verdict(res, p)
    # POST_OPENING: the two means on the opened holdout, description only
    scored = read_csv(P12V / "HOLDOUT_SCORED.csv")
    post: dict[str, dict] = {}
    for t in TARGETS:
        s = SHORT[t]
        rs = [r for r in scored if r["target_short"] == s]
        post[s] = {}
        for cfg, cols in (("ENS_MEAN_B0_B2", ("P07_B0", "P07_B2")), ("ENS_MEAN_B2_S1", ("P07_B2", "P10_S1_SC_LOGIT"))):
            er = []
            for r in rs:
                nums = {c: fnum(r[c]) for c in cols}
                ex = B.Example(decision_key=r["decision_key"], chain="solana", mint=r["mint"], decision_time=C.parse_utc(r["decision_time_utc"]),
                               label_matures_at=0.0, y=int(r["y"]))
                er.append({"y": int(r["y"]), "fold": "HOLDOUT", "example": ex, cfg: R.mean_ensemble(nums),
                           cfg + "_why": "" if all(math.isfinite(x) for x in nums.values()) else "MEMBER_ABSTAINED",
                           "B0": fnum(r["P07_B0"]), "B2": fnum(r["P07_B2"])})
            res0 = B.evaluate(er, cfg, reference="B0", reps=REPS, seed=SEED)
            res2 = B.evaluate(er, cfg, reference="B2", reps=REPS, seed=SEED)
            states = {}
            for refk, res in (("vs_B0", res0), ("vs_B2", res2)):
                v = E.holdout_verdict(res, None)
                st = "SURVIVES_POST_OPENING_ONLY_NOT_A_CLAIM" if v == E.HOLDOUT_SKILL else v
                states[refk] = {**summarize(res), "verdict": v, "post_opening_state": st, "claim": "NOT_A_CLAIM_POST_OPENING"}
            post[s][cfg] = states
            post_log.append({"label": "POST_OPENING", "target": s, "configuration": cfg,
                             "source": "audits/predictive-intelligence/phase_12/validation/HOLDOUT_SCORED.csv",
                             "source_sha256": fsha(P12V / "HOLDOUT_SCORED.csv"), "sealed_folder_read": False,
                             "use": "description only; never a selection, never a claim (PI-D-066)"})
    # decision, complexity, latency, ledger rows
    for t in TARGETS:
        s = SHORT[t]
        cf = dev_res[s]["configurations"]
        results = []
        for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1"):
            v0, v2 = cf[cfg]["vs_B0"]["verdict"], cf[cfg]["vs_B2"]["verdict"]
            results.append({"configuration": cfg, "status": "EVALUATED_DEVELOPMENT", "verdict_vs_b0": v0, "verdict_vs_b2": v2,
                            "selection_status": "NO_UNCORRECTED_SKILL" if v2 != "SKILL_INDICATED_DEVELOPMENT_ONLY" else E.NOT_COMPUTED,
                            "level_possible": "NO_GO", "reason": "no retrospective first-opening evaluation and no calibration"})
        results.append({"configuration": "STACK_CHRONO_B2_S1", "status": "NOT_FITTED_BELOW_GATE", "verdict_vs_b0": "INSUFFICIENT_HISTORY",
                        "verdict_vs_b2": "INSUFFICIENT_HISTORY", "selection_status": "NO_UNCORRECTED_SKILL", "level_possible": "NO_GO",
                        "reason": "; ".join(cf["STACK_CHRONO_B2_S1"]["folds"][-1]["gate_shortfalls"]) if cf["STACK_CHRONO_B2_S1"]["folds"] else "no rows"})
        for trap, tv in dev_res[s]["traps"].items():
            if not tv["refused"]:
                raise SystemExit(f"{s}: trap {trap} was not refused")
        dec = R.ensemble_decision(LONG[s], results)
        lat = {m: latency[f"{s}:{cid}"]["cpu_us_per_decision"] for m, cid in (("B0", "P07_B0"), ("B2", "P07_B2"), ("S1", "P10_S1_SC_LOGIT"))}
        ENS_LATENCY[s] = {"ENS_MEAN_B0_B2": lat["B0"] + lat["B2"], "ENS_MEAN_B2_S1": lat["B2"] + lat["S1"], "members": lat}
        comp = {"ENS_MEAN_B0_B2": {"members": 2, "extra_parameters": 0, "member_parameters": 1 + 6,
                                   "cpu_time": "ensemble/LATENCY.json"},
                "ENS_MEAN_B2_S1": {"members": 2, "extra_parameters": 0,
                                   "member_parameters": 6 + len(cards[(s, "P10_S1_SC_LOGIT")]["card"]["body"]["logistic"]["coef"]) + 1,
                                   "cpu_time": "ensemble/LATENCY.json"},
                "STACK_CHRONO_B2_S1": {"members": 2, "extra_parameters": 3, "fitted": False}}
        out[s] = {"target": LONG[s], "development": {cfg: ({k: (summarize(v) if k.startswith("vs_") else v) for k, v in cf[cfg].items()})
                                                      for cfg in cf},
                  "traps": dev_res[s]["traps"], "post_opening": post[s], "decision": dec, "complexity": comp}
        for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1"):
            for refk in ("vs_B0", "vs_B2"):
                d = cf[cfg][refk]
                csv_rows.append({"target_short": s, "configuration": cfg, "split": "DEVELOPMENT_OUT_OF_FOLD", "reference": refk[3:],
                                 "n_with_number": d.get("n_with_number"), "positives": d.get("positives"), "days": d.get("days"),
                                 "bss": d.get("bss"), "verdict": d["verdict"], "claim": "NO_CLAIM"})
                p = post[s][cfg][refk]
                csv_rows.append({"target_short": s, "configuration": cfg, "split": "POST_OPENING_HOLDOUT", "reference": refk[3:],
                                 "n_with_number": p.get("n_with_number"), "positives": p.get("positives"), "days": p.get("days"),
                                 "bss": p.get("bss"), "verdict": p["verdict"], "claim": p["claim"]})
        csv_rows.append({"target_short": s, "configuration": "STACK_CHRONO_B2_S1", "split": "DEVELOPMENT_OUT_OF_FOLD", "reference": "B2",
                         "n_with_number": 0, "positives": None, "days": None, "bss": None, "verdict": "INSUFFICIENT_HISTORY", "claim": "NO_CLAIM"})
        for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1", "STACK_CHRONO_B2_S1"):
            d = cf[cfg].get("vs_B2") or {}
            ledger.append({"phase": "16", "experiment_id": f"P16:{LONG[s]}:{cfg}", "target": LONG[s], "candidate": f"P16_{cfg}",
                           "kind": "ABLATION", "view": "ALL", "seed": str(SEED), "folds": str(len(cf[cfg].get("folds") or [])),
                           "n_rows": str(cf[cfg].get("oof_rows", "")), "n_with_number": str(d.get("n_with_number", 0) or 0),
                           "verdict": d.get("verdict", "INSUFFICIENT_HISTORY") if cfg != "STACK_CHRONO_B2_S1" else "INSUFFICIENT_HISTORY",
                           "split_fingerprint": "", "selection_status": "NO_UNCORRECTED_SKILL", "claim": "NO_CLAIM"})
        for trap, tv in dev_res[s]["traps"].items():
            ledger.append({"phase": "16", "experiment_id": f"P16:{LONG[s]}:{trap}", "target": LONG[s], "candidate": f"P16_{trap}",
                           "kind": "TRAP_OR_CHECK", "view": "ALL", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                           "verdict": tv["status"] if tv["refused"] else "ACCEPTED", "split_fingerprint": "", "selection_status": "",
                           "claim": "NOT_A_CONFIGURATION"})
        for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1"):
            ledger.append({"phase": "16", "experiment_id": f"P16:{LONG[s]}:POST_OPENING_{cfg}", "target": LONG[s],
                           "candidate": f"P16_{cfg}", "kind": "POST_OPENING_CHECK", "view": "HOLDOUT_POST_OPENING", "seed": str(SEED),
                           "folds": "", "n_rows": str(post[s][cfg]["vs_B2"].get("n_rows") or ""),
                           "n_with_number": str(post[s][cfg]["vs_B2"].get("n_with_number") or ""),
                           "verdict": post[s][cfg]["vs_B2"]["verdict"], "split_fingerprint": "", "selection_status": "",
                           "claim": "NOT_A_CLAIM_POST_OPENING"})
    return out, csv_rows, ledger, post_log


def stability(cards: dict, fam_cache: dict) -> dict:
    """Fold cards against the frozen card on the probe set: how much the numbers move between training cutoffs (descriptive)."""
    out = {}
    for t in TARGETS:
        s = SHORT[t]
        ex, fam_ex = fam_cache[s]
        out[s] = {}
        for ph, kind, cid, path in (("07", "B2", "P07_B2", AUD / f"phase_07/artifacts/folds/{s}.json"),
                                    ("10", "S1_SC_LOGIT", "P10_S1_SC_LOGIT", AUD / f"phase_10/artifacts/folds/{s}.json")):
            frozen = cards[(s, cid)]["card"]
            p0, _ = PREDICT[ph](frozen, fam_ex[ph])[:2]
            folds = json.loads(path.read_text())["folds"]
            rows = []
            for f in folds:
                fc = (f.get("cards") or {}).get(kind)
                if fc is None or "abstain" in (fc.get("body") or {}):
                    rows.append({"fold_cutoff_utc": f.get("cutoff_utc") or (fc or {}).get("training_cutoff_utc"), "fitted": False})
                    continue
                p1 = PREDICT[ph](fc, fam_ex[ph])[0]
                both = np.isfinite(p0) & np.isfinite(p1)
                d = np.abs(np.asarray(p1)[both] - np.asarray(p0)[both])
                rows.append({"fold_cutoff_utc": fc["training_cutoff_utc"], "fitted": True, "n_train": fc["n_train"],
                             "rows_compared": int(both.sum()), "max_abs_diff": float(d.max()) if d.size else None,
                             "median_abs_diff": float(np.median(d)) if d.size else None})
            out[s][cid] = {"frozen_cutoff_utc": frozen["training_cutoff_utc"], "folds": rows,
                           "frozen_abstains": "abstain" in frozen["body"]}
    return out


# ---------------------------------------------------------------- compatibility, staleness, rollback, today
def compat_demo(entries: dict, rt: dict) -> dict:
    real = {eid: R.compatibility(e, runtime=rt) for eid, e in entries.items()}
    rt_a = json.loads(json.dumps(rt))
    rt_a["feature_set_sha"]["07"] = "f" * 64
    rt_b = json.loads(json.dumps(rt))
    rt_b["feature_version"] = "3"
    rt_c = json.loads(json.dumps(rt))
    rt_c["registry_sha"] = "e" * 64
    a = {eid: R.compatibility(e, runtime=rt_a) for eid, e in entries.items()}
    b = {eid: R.compatibility(e, runtime=rt_b) for eid, e in entries.items()}
    c = {eid: R.compatibility(e, runtime=rt_c) for eid, e in entries.items()}
    req_bad = {eid: R.compatibility(e, runtime=rt, request={"feature_set_sha": "d" * 64, "feature_version": e["feature_version"]})
               for eid, e in entries.items()}
    n07 = sum(1 for e in entries.values() if e["family"]["phase"] == "07")
    return {"runtime": rt,
            "real_runtime_incompatible_entries": sum(1 for v in real.values() if v),
            "phase07_feature_definitions_changed": {"affected": sum(1 for v in a.values() if any(s["state"] == R.INCOMPATIBLE for s in v)),
                                                    "phase07_entries": n07},
            "feature_version_bumped": {"affected": sum(1 for v in b.values() if any(s["state"] == R.INCOMPATIBLE for s in v)),
                                       "entries": len(entries)},
            "target_registry_changed": {"affected": sum(1 for v in c.values() if any(s["state"] == R.INCOMPATIBLE for s in v))},
            "request_with_another_feature_set": {"affected": sum(1 for v in req_bad.values()
                                                                 if any(s["state"] == R.FEATURE_SCHEMA_MISMATCH for s in v))},
            "rule": "a schema or feature change without retrain fails every affected entry (P46)"}


def fixture_rollback(real_entries: dict) -> dict:
    """Rollback to baseline on fixtures (TEST_ONLY): a fixture B2 at SHADOW pinned, a fixture model at VALIDATED_EXPERIMENTAL
    pinned later, drift on the model rolls back to the fixture baseline, an inference mismatch on the baseline rolls back to
    NO_VIABLE_CHAMPION. Same construction as the unit tests."""
    sys.path.insert(0, str(REPO / "tests"))
    import test_predictive_registry as TR   # the fixture builders live with the tests
    ents, steps = TR.fixture_registry()
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "LOG.jsonl"
        sha_, _ = R.append_events(log, steps["initial"], expect_sha=None)
        events = R.read_log(log.read_text())
        t_mid = C.parse_utc(steps["t_model_pin"]) + 60
        before_rb = R.resolve(events, ents, TR.FX_TARGET, t_mid)
        rb1 = R.rollback_event(events, ents, TR.FX_TARGET, reason="DRIFT_ALERT", as_of_utc=steps["t_drift"],
                               usable=lambda e: True, allow_fixture=True, verify=TR.FX_VERIFY)
        old = log.read_text()
        sha_, _ = R.append_events(log, [rb1], expect_sha=sha_)
        events = R.read_log(log.read_text())
        after1 = R.resolve(events, ents, TR.FX_TARGET, C.parse_utc(steps["t_drift"]))
        rb2 = R.rollback_event(events, ents, TR.FX_TARGET, reason=R.INFERENCE_MISMATCH, as_of_utc=steps["t_mismatch"],
                               usable=lambda e: True, allow_fixture=True, verify=TR.FX_VERIFY)
        sha_, _ = R.append_events(log, [rb2], expect_sha=sha_)
        events = R.read_log(log.read_text())
        after2 = R.resolve(events, ents, TR.FX_TARGET, C.parse_utc(steps["t_mismatch"]))
        still = R.resolve(events, ents, TR.FX_TARGET, t_mid)
        return {"is_fixture": True, "status": "TEST_ONLY",
                "pinned_before_rollback": {"mode": before_rb["mode"], "champion_model": ents[before_rb["champion"]]["model_id"]},
                "after_drift_rollback": {"mode": after1["mode"], "champion_model": ents[after1["champion"]]["model_id"] if after1["champion"] else None},
                "after_inference_mismatch_rollback": {"mode": after2["mode"], "champion": after2["champion"]},
                "history_preserved": R.is_append_only(old, log.read_text()) and still["event_id"] == before_rb["event_id"],
                "events": len(events)}


def real_log_rollback(log_text: str, entries: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "REGISTRY_LOG.jsonl"
        log.write_text(log_text)
        events = R.read_log(log_text)
        out = {}
        sha_ = R.file_sha(log)
        for t in TARGETS:
            rb = R.rollback_event(events, entries, t, reason="DRIFT_ALERT (demonstration on a temporary copy)",
                                  as_of_utc="2026-10-27T00:00:01Z", usable=lambda e: True)
            sha_, _ = R.append_events(log, [rb], expect_sha=sha_)
            events = R.read_log(log.read_text())
            r = R.resolve(events, entries, t, C.parse_utc("2026-10-27T00:00:01Z"))
            out[SHORT[t]] = {"mode_after": r["mode"], "champion_after": r["champion"]}
        out["original_prefix_kept"] = log.read_text().startswith(log_text)
        return out


def today(dev, entries: dict, events: list[dict], rt: dict) -> tuple[dict, list[dict], list[dict]]:
    tday = C.parse_utc(TODAY)
    pro = [dict(r) for r in dev.execute("SELECT * FROM predictive_decisions WHERE chain='solana' AND decision_key IS NOT NULL "
                                        "AND decision_time >= ? AND decision_time <= ? ORDER BY decision_time, decision_key", (END, tday))]
    bt = C.backtest_status()
    docs, recs = [], []
    out = {"as_of_utc": TODAY, "decisions": len(pro), "targets": {}, "statement":
           "No champion for any target. B0 and B2 are references, not forecasts. No probability is published.",
           "note": "prospective decisions of the development store; their features are not in the Phase 05 store (sealed by design), "
                   "so inputs are missing; no label of them is read"}
    failures = []
    for t in TARGETS:
        s = SHORT[t]
        served = R.serve(events, entries, t, tday, runtime=rt)
        fi = served["forecast_inputs"]
        if fi["card_entry"] is not None or fi["level"] != "ABSTAIN":
            failures.append(f"{s}: the registry resolved a champion")
        rc = Counter()
        for d in pro:
            dd = L.decision_from_row(d)
            req = {"chain": dd["chain"], "mint": dd["mint"], "target": t, "decision_time": float(dd["decision_time"]),
                   "decision_time_basis": "EXPORT_COMMIT", "snapshot_hash": d["row_sha256"], "flag_on": False,
                   "pool_point_in_time": dd.get("route") == "PIT_RECORDED", "route": dd.get("route"), "eligibility": None,
                   "position_usd": None, "backtest_required": False, "x": {}, "avail": {}, "feature_set_sha": F.feature_set_sha(),
                   "new_mint": None, "token_history_rows": 0}
            doc, rec = AB.forecast_result(req, card=None, level=fi["level"], cal_card=None, raw=None, drift_alarms=[],
                                          generated_at_utc=TODAY, backtest_status=bt)
            errs = AB.validate_publication(doc, model_card=None, calibration_card=None, record=rec, backtest=bt)
            if errs or doc["prediction_status"] != "ABSTAIN" or doc["model_id"] != R.NOT_SELECTED or doc["probability"] is not None:
                failures.append(f"today {s}: {errs}")
            docs.append(doc)
            recs.append(rec)
            rc.update(rec["reasons"])
        refs = {name: entries[eid] for name, eid in served["references"].items()}
        out["targets"][s] = {"mode": served["resolved"]["mode"], "champion": None, "model_id_in_documents": R.NOT_SELECTED,
                             "prediction_status": "ABSTAIN", "documents": len(pro),
                             "reason_counts": dict(sorted(rc.items())), "pin_reasons": served["resolved"]["reasons"],
                             "references": {n: {"entry_id": e["entry_id"], "model_id": e["model_id"], "level": e["promotion"]["level"],
                                                "registry_status": e["registry_status"], "published": False,
                                                "states_today": [x["state"] for x in R.status_at(e, tday)],
                                                "states_at_" + EDGE_PROBE: [x["state"] for x in R.status_at(e, C.parse_utc(EDGE_PROBE))],
                                                "states_at_" + STALE_PROBE: [x["state"] for x in R.status_at(e, C.parse_utc(STALE_PROBE))],
                                                "stale_after_utc": iso(R.stale_after(e))} for n, e in refs.items()},
                             "target_plan": None}
    if pro:
        dd = L.decision_from_row(pro[-1])
        served_all = {t: R.serve(events, entries, t, tday, runtime=rt) for t in TARGETS}
        out["target_plan_example"] = {"decision_key": pro[-1]["decision_key"], "plan": R.target_plan({"chain": dd["chain"]}, served_all)}
    out["drift_demonstration"] = {
        s: [x["state"] for x in R.status_at(entries[out["targets"][s]["references"]["simple_model"]["entry_id"]], tday,
                                            drift_alarms=[C.parse_utc("2026-10-26T12:00:00Z")])] for s in out["targets"]}
    out["drift_demonstration_note"] = "a synthetic alarm time, to show the state; no drift stream exists before Phase 19"
    out["failures"] = failures
    return out, docs, recs


# ---------------------------------------------------------------- ledger
def ledger(new_rows: list[dict]) -> tuple[list[dict], dict]:
    base = read_csv(AUD / "phase_15/experiments/SEARCH_LEDGER.csv") + read_csv(AUD / "phase_15/experiments/SEARCH_LEDGER_RP2_ADDITION.csv")
    cols = list(base[0].keys())
    before = E.ledger_totals(base)
    before_rules = E.rule_configurations(base)
    debug = [{"phase": "16", "experiment_id": f"P16:DEBUG:{i}", "target": "", "candidate": "", "kind": "DEBUG_RUN_REAL_DATA",
              "view": "ALL", "seed": "", "folds": "", "n_rows": "", "n_with_number": "", "verdict": txt, "split_fingerprint": "",
              "selection_status": "", "claim": ""} for i, txt in enumerate(DEBUG_RUNS)]
    rows = base + [{c: r.get(c, "") for c in cols} for r in new_rows + debug]
    tot = E.ledger_totals(rows)
    rules = E.rule_configurations(rows)
    totals = {"sources": ["audits/predictive-intelligence/phase_15/experiments/SEARCH_LEDGER.csv",
                          "audits/predictive-intelligence/phase_15/experiments/SEARCH_LEDGER_RP2_ADDITION.csv", "Phase 16 rows"],
              "before": {**before, "rule_configurations": before_rules, "n_search_sensitivity": before["n_search"] + before_rules},
              "after": {**tot, "rule_configurations": rules, "n_search_sensitivity": tot["n_search"] + rules},
              "phase16_rows": len(new_rows) + len(debug), "phase16_debug_runs": len(debug)}
    if (before["n_search"], tot["n_search"], before["n_search"] + before_rules, tot["n_search"] + rules) != \
            (EXPECTED_N_SEARCH["before"], EXPECTED_N_SEARCH["after"], EXPECTED_N_SEARCH["sensitivity_before"], EXPECTED_N_SEARCH["sensitivity_after"]):
        raise SystemExit(f"ledger totals differ from the plan: {totals}")
    return rows, totals


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    t0, c0 = time.time(), time.process_time()
    stores = [a.dev_store, a.feature_store, str(REPO / "data/memelab.sqlite")]
    before = {p: fsha(p) for p in stores}
    seal_before = seal_stat()
    for p in stores[:2]:
        L.refuse_sealed(p)
    dev = P7.ro(a.dev_store)
    failures: list[str] = []

    cand, cards = load_candidates()
    # rule 2: the Phase 12 champions restated, never recomputed from holdout outcomes
    devrows = RH.dev_metric_rows()
    champs = {}
    for t in TARGETS:
        s = SHORT[t]
        fitted = {cid: v["fitted"] for (ss, cid), v in cards.items() if ss == s}
        got = R.select_champion(t, devrows, fitted, rule=E.champion)
        champs[s] = got
        if got != cand["champions"][s]:
            failures.append(f"{s}: restated champion differs from CANDIDATES.json")
    # committed evaluation facts
    metrics = {(r["target_short"], r["model"], r["reference"]): r for r in read_csv(P12V / "HOLDOUT_METRICS.csv")}
    post = {}
    for r in read_csv(P12V / "POST_OPENING_CORRECTIONS.csv"):
        post.setdefault((r["target_short"], r["model"]), {})[r["reference"]] = r["selection_status_final"]
    traps = json.loads((P12V / "PREOPEN_TRAPS.json").read_text())
    replay = json.loads((P12V / "REPLAY_AUDIT.json").read_text())
    tests = {"leakage": traps["failures"] == [] and bool(replay.get("ok")), "provenance": True,
             "contract": all(v["card"]["registry_sha"] == C.registry_sha256() for v in cards.values()),
             "basis": "phase_12 PREOPEN_TRAPS.json failures [] and REPLAY_AUDIT ok; cards load with their hashes; registry fingerprint"}
    cal_paths = {s: f"audits/predictive-intelligence/phase_13/artifacts/{s}/CALIBRATION_CARD.json" for s in SHORT.values()}
    cal_cards = {s: CAL.loads((REPO / p).read_text()) for s, p in cal_paths.items()}
    devv = dev_verdicts()

    inference, fam_cache, latency, _ = inference_check(cards, a.dev_store, a.feature_store)
    bad_inf = [k for k, v in inference.items() if not v["equal_to_recorded"]]
    if bad_inf:
        failures.append(f"inference differs from the recorded predictions: {bad_inf[:5]}")

    entries = build_entries(cards, inference, metrics, post, cal_cards, cal_paths, tests, devv)
    reg_dir = out / "registry"
    ent_dir = reg_dir / "entries"
    if ent_dir.exists():
        shutil.rmtree(ent_dir)
    for e in entries.values():
        R.write_entry(ent_dir, e)
    back = R.read_entries(ent_dir)
    if set(back) != set(entries):
        failures.append("entries read back differ")
    fact_checks = 0
    for e in back.values():                      # CP16-0: every entry's facts rebuilt from the committed files, every source hashed
        s_ = SHORT[e["target"]]
        cid = e["family"]["candidate"]
        v = cards[(s_, cid)]
        R.verify_facts(e, card=v["card"], tests=tests_for(v, tests), m_b0=metrics.get((s_, cid, "P07_B0")),
                       m_b2=metrics.get((s_, cid, "P07_B2")), post_states=post.get((s_, cid), {}),
                       cal_card=cal_cards[s_] if cid == "P07_B2" else None)
        R.verify_sources(e, lambda path: (REPO / path).read_bytes())
        fact_checks += 1

    ens, ens_csv, ens_ledger, post_log = ensembles(dev, cards, fam_cache, latency)
    stab = stability(cards, fam_cache)

    by_target = {t: {e["family"]["kind"]: e for e in entries.values() if e["target"] == t and e["family"]["phase"] == "07"} for t in TARGETS}
    payloads = [R.register_event(e, as_of_utc=REGISTERED_AS_OF) for e in sorted(entries.values(), key=lambda e: (e["target"], e["family"]["candidate"]))]
    for t in TARGETS:
        payloads.append({**ens[SHORT[t]]["decision"], "as_of_utc": REGISTERED_AS_OF, "evidence_file": "ensemble/ENSEMBLE_ABLATION.json"})
    for t in TARGETS:
        promoted = [e for e in entries.values() if e["target"] == t and e["promotion"]["level"] in R.PUBLISHABLE_LEVELS]
        if promoted:
            failures.append(f"{SHORT[t]}: an entry reached {promoted[0]['promotion']['level']}; the plan expects none: stop and record")
        b2 = by_target[t]["B2"]
        reasons = ["NO_ENTRY_AT_SHADOW_OR_ABOVE", "PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE",
                   "B2_" + "+".join(r for r in b2["promotion"]["reasons"] if r != "REFERENCE_BASELINE_NEVER_PUBLISHED"),
                   "NO_ENSEMBLE"]
        payloads.append(R.pin_event(entries, t, mode="NO_VIABLE_CHAMPION", champion=None,
                                    references={"base_rate": by_target[t]["B0"]["entry_id"], "simple_model": b2["entry_id"]},
                                    reasons=reasons, as_of_utc=REGISTERED_AS_OF))
    log = reg_dir / "REGISTRY_LOG.jsonl"
    if log.exists():
        log.unlink()
    R.append_events(log, payloads, expect_sha=None)
    events = R.read_log(log.read_text())

    rt = runtime_facts()
    comp = compat_demo(entries, rt)
    if comp["real_runtime_incompatible_entries"]:
        failures.append("an entry is incompatible with the running code")
    rb_real = real_log_rollback(log.read_text(), entries)
    rb_fx = fixture_rollback(entries)
    tstat, tdocs, trecs = today(dev, entries, events, rt)
    failures += tstat["failures"]

    levels = Counter(e["promotion"]["level"] for e in entries.values())
    statuses = Counter(e["registry_status"] for e in entries.values())
    index = {"registry_version": R.REGISTRY_VERSION, "registered_as_of_utc": REGISTERED_AS_OF, "entries": len(entries),
             "log": "registry/REGISTRY_LOG.jsonl", "log_sha256": fsha(log), "events": len(events),
             "statement": "No champion for any target: every target is NO_VIABLE_CHAMPION and abstains. B0 (base rate) and B2 (simple "
                          "model) are pinned as references for the prospective comparison; they are not forecasts and are never "
                          "published as a probability. No model shows skill over the base rate (Phase 12) and none is calibrated (Phase 13).",
             "levels": dict(sorted(levels.items())), "registry_statuses": dict(sorted(statuses.items())),
             "publishable": sum(1 for e in entries.values() if e["publishable"]),
             "targets": {SHORT[t]: {**{k: v for k, v in R.resolve(events, entries, t, C.parse_utc(REGISTERED_AS_OF)).items() if k != "champion_inference_sha"},
                                   "phase12_champion_restated": champs[SHORT[t]]["champion"],
                                   "phase12_champion_basis": champs[SHORT[t]]["basis"],
                                   "reference_models": {n: entries[eid]["model_id"] for n, eid in
                                                        R.resolve(events, entries, t, C.parse_utc(REGISTERED_AS_OF))["references"].items()},
                                   "ensemble": ens[SHORT[t]]["decision"]["decision"]} for t in TARGETS},
             "entries_by_target": {SHORT[t]: sorted([{"entry_id": e["entry_id"], "candidate": e["family"]["candidate"],
                                                      "level": e["promotion"]["level"], "registry_status": e["registry_status"]}
                                                     for e in entries.values() if e["target"] == t], key=lambda x: x["candidate"])
                                   for t in TARGETS},
             "promotion_path": "closed under the frozen ACCEPTANCE promotion table: the retrospective holdout is spent and any model "
                               "trained after 2026-10-17 has it inside its training window; a change control to ACCEPTANCE promotion "
                               "(Elving or the orchestrator) is needed before any model can reach SHADOW"}
    write_json(reg_dir / "REGISTRY_INDEX.json", index)
    write_json(reg_dir / "TODAY_STATUS.json", tstat)
    with open(reg_dir / "TODAY_RESULTS.jsonl", "w") as f:
        for d_ in tdocs:
            f.write(AB.canon(d_) + "\n")
    with open(reg_dir / "TODAY_RECORDS.jsonl", "w") as f:
        for r_ in trecs:
            f.write(AB.canon(r_) + "\n")
    write_json(out / "ensemble/ENSEMBLE_ABLATION.json", {"rule": "ACCEPTANCE_CHECKLIST.md rule 12", "targets": ens,
                                                         "ensemble_decision": {s: v["decision"]["decision"] for s, v in ens.items()}})
    write_csv(out / "ensemble/ENSEMBLE_ABLATION.csv", ens_csv)
    write_json(out / "ensemble/STABILITY.json", stab)
    write_json(out / "ensemble/POST_OPENING_LOG.json", post_log)
    write_json(out / "ensemble/LATENCY.json", {"note": "CPU time per decision of each card's predict on the probe set; machine "
                                                       "dependent, descriptive, excluded from the determinism comparison",
                                               "cards": latency, "ensembles_sum_of_members": ENS_LATENCY})
    write_json(out / "evidence/INFERENCE_CHECK.json", {"cards": len(inference), "equal_to_recorded": sum(1 for v in inference.values() if v["equal_to_recorded"]),
                                                       "differences": {f"{k[0]}:{k[1]}": v["differences"] for k, v in inference.items() if v["differences"]},
                                                       "by_card": {f"{k[0]}:{k[1]}": {kk: vv for kk, vv in v.items()} for k, v in sorted(inference.items())}})
    write_json(out / "evidence/COMPATIBILITY_P46.json", comp)
    write_json(out / "evidence/ROLLBACK_TEST.json", {"fixture": rb_fx, "real_log_copy": rb_real})
    led_rows, totals = ledger(ens_ledger)
    write_csv(out / "experiments/SEARCH_LEDGER.csv", led_rows)
    write_json(out / "experiments/LEDGER_TOTALS.json", totals)

    after = {p: fsha(p) for p in stores}
    seal_after = seal_stat()
    write_json(out / "evidence/run_log.json", {
        "start_utc": iso(t0), "end_utc": iso(time.time()), "cpu_s": round(time.process_time() - c0, 3), "head": git("rev-parse", "HEAD").strip(),
        "code_sha256": {c: fsha(REPO / c) for c in CODE}, "stores_before": before, "stores_after": after,
        "stores_unchanged": before == after, "sealed_folder_unchanged": seal_before == seal_after, "socket_events": SOCKET_EVENTS,
        "network_calls": len(SOCKET_EVENTS), "training_labels_calls": LABEL_CALLS[0], "facts_and_sources_verified": fact_checks, "firecrawl_credits": 0, "llm_calls": 0,
        "debug_runs_before_frozen_code": DEBUG_RUNS, "failures": failures, "python": sys.version.split()[0], "numpy": np.__version__})
    print(json.dumps({"entries": len(entries), "levels": dict(levels), "events": len(events), "inference_equal": len(inference) - len(bad_inf),
                      "ensemble": {s: v["decision"]["decision"] for s, v in ens.items()}, "n_search": totals["after"]["n_search"],
                      "failures": failures, "stores_unchanged": before == after}))
    return 1 if failures or before != after or seal_before != seal_after else 0


if __name__ == "__main__":
    raise SystemExit(main())

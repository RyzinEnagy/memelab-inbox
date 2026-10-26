"""Phase 12 runner: the frozen evaluation plan of `validation/WALK_FORWARD_PROTOCOL.md` (PI-D-064) in three steps.

    python -B run_holdout.py plan OUTDIR      candidates, model SHAs, the champion rule and the ledger totals (no holdout data)
    python -B run_holdout.py predict OUTDIR   every frozen card and the NC1 controls on every Solana holdout decision, with no
                                              label read; the pre-opening traps and the replay audit; a prediction manifest
    python -B run_holdout.py open OUTDIR [--reproduction]
                                              the seal check, the single logged opening of the sealed holdout labels and every
                                              evaluation of the plan

Reads only: the frozen cards of Phases 07 to 11, the committed development metric files and the cumulative search ledger (plan);
the Phase 06 development store (decision rows; training labels through `labels.training_labels` for NC1, the new-mint views and
the P13 trap), the Phase 05 store (version 2 snapshots, tech-1, onchain-1, decision rows), git objects of the decisions' own
export commits (socialcat-1), all read-only (predict); and in `open` the one sealed label file through
`evaluation.open_holdout`, after `check_seal.py`. No network: an audit hook refuses any socket call. `plan` and `predict` are
deterministic (two runs give identical files except `run_log_*.json`); `open` refuses a second FIRST_OPENING.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import glob
import hashlib
import importlib.util
import json
import math
import resource
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import analog as A  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import onchain as O  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import socialcat as SC  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402
from memelab.predictive import technical as T8  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 12 runner makes no network call ({event})")


sys.addaudithook(_hook)


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P7 = _load("p07_run_baselines", "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
P10 = _load("p10_run_social", "audits/predictive-intelligence/phase_10/probes/run_social.py")
P11 = _load("p11_run_analog", "audits/predictive-intelligence/phase_11/probes/run_analog.py")

AUD = REPO / "audits/predictive-intelligence"
PH = AUD / "phase_12"
VAL = PH / "validation"
SHORT = P7.SHORT
LONG = {v: k for k, v in SHORT.items()}
H, END = L.holdout_start(), L.prospective_start()
TARGETS = (L.T1, L.T1B, L.T2)
REPS, SEED = E.REPS, E.SEED
SPLIT_FP = "87a21ba3182db2c9271f2c0ce83de2157638cc864d0f0aec6d3c18b7ee0859e8"   # experiments/EXPERIMENT_REGISTRY.csv
EXPECTED_LEDGER = {"rows": 2896, "candidate_configurations": 87, "bakeoff_configurations": 31, "negative_control_fits": 306,
                   "debug_runs": 15, "n_search": 118}
LOADERS = {"07": B.loads, "08": T8.loads, "09": O.loads, "10": SC.loads, "11": A.loads}
DEV_METRICS = {"08": "phase_08/experiments/TECHNICAL_METRICS.csv", "09": "phase_09/experiments/ONCHAIN_METRICS.csv",
               "10": "phase_10/experiments/SOCIAL_METRICS.csv", "11": "phase_11/experiments/ANALOG_METRICS.csv"}
NC2_FAMILY_CARD = {"07": "B2", "08": "M2_T_LOGIT_B2", "09": "M2_OC_LOGIT_B2", "10": "S2_SC_LOGIT_B2", "11": "AC3_KNN_REGIME"}
CODE = ["memelab/predictive/evaluation.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
        "memelab/predictive/labels.py", "memelab/predictive/features.py", "memelab/predictive/contract.py",
        "memelab/predictive/technical.py", "memelab/predictive/onchain.py", "memelab/predictive/socialcat.py",
        "memelab/predictive/analog.py", "audits/predictive-intelligence/phase_07/probes/run_baselines.py",
        "audits/predictive-intelligence/phase_10/probes/run_social.py", "audits/predictive-intelligence/phase_11/probes/run_analog.py",
        "audits/predictive-intelligence/phase_12/probes/run_holdout.py"]
CRASH_LOG = math.log(0.5)
# runs on real data before the recorded runs (P22): appended before the recorded runs, never removed
DEBUG_RUNS: list[str] = [
    "plan and predict at uncommitted code (2026-10-26 16:47:52Z to 16:48:01Z) into the session scratchpad: 69 cards, champions "
    "P07_B2 x3, N_search 118, 12,255 holdout prediction rows over 95 decisions, traps 0 failures; features only, no label read",
    "open --synthetic-dry-run on that scratch folder (17:00:19Z to 17:12:06Z): random SYNTHETIC labels in the sealed file's "
    "shape, no seal check, no holdout label read; exercised every evaluation of the plan (12 min at 20,000 replicates) and the "
    "scikit-learn oracle on its output (616 values, 1.1e-16)",
    "plan and predict again after the ledger edits (about 17:13Z) into a second scratch folder: predictions byte-equal "
    "to the first; then a SYNTHETIC dry run of open at 50 replicates through a scratch wrapper (two attempts cut by a 10 min "
    "timeout, one complete at about 17:31Z): random labels, no holdout label read, no seal check",
]
PRED_FILE, DEC_FILE = "HOLDOUT_PREDICTIONS.csv", "HOLDOUT_DECISIONS.csv"


# ---------------------------------------------------------------- io
def fsha(p) -> str:
    return P7.fsha(p)


def iso(t) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def num(x) -> str:
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    return "" if not math.isfinite(x) else f"{x:.17g}"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (num(v) if isinstance(v, (float, int, np.floating, np.integer)) and not isinstance(v, bool)
                            else ("1" if v is True else "0" if v is False else ("" if v is None else v))) for k, v in r.items()})


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def run_log(out: Path, name: str, t0: float, c0: float, extra: dict) -> None:
    write_json(out / f"run_log_{name}.json", {
        "step": name, "start_utc": iso(t0), "end_utc": iso(time.time()), "wall_s": round(time.time() - t0, 3),
        "cpu_s": round(time.process_time() - c0, 3), "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "head": git("rev-parse", "HEAD").strip(), "python": sys.version.split()[0], "numpy": np.__version__,
        "code_sha256": {c: fsha(REPO / c) for c in CODE}, "network_calls": len(SOCKET_EVENTS), "vendor_calls": 0,
        "firecrawl_credits": 0, "llm_calls": 0, **extra})


# ---------------------------------------------------------------- cards
def card_paths() -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(str(AUD / "phase_*/artifacts/T*/*.json")))]


def load_cards() -> dict[tuple[str, str], dict]:
    """Every frozen holdout-start card through its family's loader (sha refused on mismatch), keyed (target_short, candidate)."""
    out = {}
    for p in card_paths():
        ph = p.parts[-4].split("_")[1]
        s = p.parent.name
        card = LOADERS[ph](p.read_text())
        cid = f"P{ph}_{p.stem}"
        if card["targets"] != [LONG[s]] or float(card["training_cutoff"]) != H:
            raise SystemExit(f"{p}: card target or cutoff is not the frozen one")
        E.check_card_time(card, [H])
        out[(s, cid)] = {"card": card, "path": p.relative_to(REPO).as_posix(), "phase": ph, "family": ph, "id": p.stem,
                         "fitted": "abstain" not in card["body"], "file_sha256": fsha(p)}
    return out


def dev_metric_rows() -> list[dict]:
    rows = []
    for ph, rel in DEV_METRICS.items():
        with open(AUD / rel) as f:
            for r in csv.DictReader(f):
                rows.append({"target": r["target"], "view": r["view"], "reference": r["reference"], "verdict": r["verdict"],
                             "brier": r["brier"] or "nan", "candidate_id": f"P{ph}_{r['model']}"})
    return rows


def read_ledger(rel: str) -> list[dict]:
    with open(AUD / rel) as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- plan
def cmd_plan(out: Path) -> int:
    t0, c0 = time.time(), time.process_time()
    cards = load_cards()
    if len(cards) != 69:
        raise SystemExit(f"{len(cards)} cards, the plan names 69")
    dev = dev_metric_rows()
    champs = {}
    for t in TARGETS:
        s = SHORT[t]
        fitted = {cid: v["fitted"] for (ss, cid), v in cards.items() if ss == s}
        champs[s] = E.champion(t, dev, fitted)
    tot = E.ledger_totals(read_ledger("phase_11/experiments/SEARCH_LEDGER.csv"))
    bad = {k: (tot[k], v) for k, v in EXPECTED_LEDGER.items() if tot[k] != v}
    if bad:
        raise SystemExit(f"ledger totals differ from the plan: {bad}")
    cand = [{"target_short": s, "candidate": cid, "path": v["path"], "phase": v["phase"], "kind": v["card"]["kind"],
             "model_id": v["card"]["model_id"], "model_sha": v["card"]["model_sha"], "file_sha256": v["file_sha256"],
             "training_cutoff_utc": v["card"]["training_cutoff_utc"], "fitted": v["fitted"],
             "abstain": v["card"]["body"].get("abstain"), "n_train": v["card"].get("n_train"), "k_train": v["card"].get("k_train"),
             "max_train_decision_time_utc": iso(v["card"]["max_train_decision_time"]),
             "max_train_label_matures_at_utc": iso(v["card"]["max_train_label_matures_at"])}
            for (s, cid), v in sorted(cards.items())]
    write_json(out / "CANDIDATES.json", {"plan": "validation/WALK_FORWARD_PROTOCOL.md", "decision": "PI-D-064", "eval_version": E.EVAL_VERSION,
                                         "holdout_start_utc": iso(H), "holdout_end_utc": iso(END), "candidates": cand,
                                         "champions": champs, "development_skill_rows": sum(1 for r in dev if r["verdict"] == E.DEV_SKILL)})
    write_json(out / "LEDGER_TOTALS.json", {"source": "audits/predictive-intelligence/phase_11/experiments/SEARCH_LEDGER.csv", **tot})
    run_log(out, "plan", t0, c0, {})
    print(json.dumps({"cards": len(cand), "champions": {s: c["champion"] for s, c in champs.items()}, "n_search": tot["n_search"]}))
    return 0


# ---------------------------------------------------------------- holdout inputs (no label)
def ro(path: str):
    return P7.ro(path)


def decision_table(dev) -> dict[str, dict]:
    out = {}
    for r in dev.execute("SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL"):
        out[r["decision_key"]] = L.decision_from_row(dict(r))
    return out


def solana_decisions(fs, upto: float) -> dict[str, dict]:
    out = {}
    for r in fs.execute("SELECT decision_key, chain, mint, decision_time, status, token_json, token_first_seen_at, pool_address, "
                        "export_commit FROM predictive_decisions WHERE chain='solana' AND decision_key IS NOT NULL "
                        "AND decision_time < ? ORDER BY decision_time, id", (upto,)):
        d = dict(r)
        d["token"] = json.loads(r["token_json"]) if r["token_json"] else {}
        out[r["decision_key"]] = d
    return out


def base_example(target: str, d: dict, frow: dict, snap_sha: str | None) -> B.Example:
    if frow["chain"] != d["chain"] or frow["mint"] != d["mint"] or float(frow["decision_time"]) != float(d["decision_time"]):
        raise B.IdentityJoinError("feature row of another decision (P01)")
    x, av = B.model_inputs(frow)
    T = float(d["decision_time"])
    grp, coh = L.groups_of(d), L.cohort_of(d)
    nar = (d.get("token") or {}).get("narrative_id")
    return B.Example(decision_key=d["decision_key"], chain=d["chain"], mint=d["mint"], decision_time=T,
                     label_matures_at=C.label_matures_at(target, T), y=-1, x=x, avail=av, status=d.get("status"),
                     creator=grp["creator"], narrative=str(nar) if nar not in (None, "") else None, route=d["route"],
                     key_conflict="KEY_CONFLICT" in (d.get("flags") or []), label_key=None, snapshot_sha256=snap_sha, cohort=coh)


class Inputs:
    """Every input of the holdout decisions, as of each decision; no label."""

    def __init__(self, dev_path: str, fs_path: str):
        for p in (dev_path, fs_path):
            L.refuse_sealed(p)
            R.refuse_bakeoff_labels(path=p)
        self.dev, self.fs = ro(dev_path), ro(fs_path)
        self.frows_h, self.snaps, self.info = P7.load_inputs(self.dev, self.fs)
        self.frows = {r["decision_key"]: r for r in F.training_view(self.fs, as_of=END, feature_version=F.FEATURE_VERSION, mode="provider")}
        self.dtab = decision_table(self.dev)
        self.sol = solana_decisions(self.fs, END)
        self.hold = {k: v for k, v in self.sol.items() if H <= float(v["decision_time"]) < END}
        dev_hold = {k for k, v in self.dtab.items() if v["chain"] == "solana" and H <= v["decision_time"] < END}
        if set(self.hold) != dev_hold:
            raise SystemExit("the holdout decision sets of the two stores differ")
        rrows = P11.regime_rows(self.sol, self.frows)
        self.series = A.regime_series(rrows)
        self.extras = P11.extras_of(self.fs, self.hold, self.frows, self.series)
        self.tsnaps = {k: T8.technical_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), mode="provider", decision_key=k)
                       for k, d in self.hold.items()}
        self.osnaps = {k: O.onchain_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), decision_key=k)
                       for k, d in self.hold.items()}
        self.ssnaps, self.sc_prov = {}, Counter()
        for k, d in self.hold.items():
            row = self.fs.execute("SELECT export_commit, export_blob FROM predictive_decisions WHERE decision_key=?", (k,)).fetchone()
            cx = P10.context_of(row["export_commit"])
            self.sc_prov["blob_equal" if cx["blob"] == row["export_blob"] else "blob_differs"] += 1
            self.sc_prov["commit_time_equal" if cx["commit_time"] == float(d["decision_time"]) else "commit_time_differs"] += 1
            self.ssnaps[k] = SC.socialcat_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), decision_key=k, context=cx)
        self.keys = sorted(self.hold, key=lambda k: (float(self.hold[k]["decision_time"]), self.hold[k]["mint"], k))

    def examples(self, target: str) -> list[B.Example]:
        return [base_example(target, self.dtab[k], self.frows[k], self.snaps.get(k)) for k in self.keys]

    def family(self, ph: str, ex: list[B.Example]) -> list:
        if ph == "07":
            return list(ex)
        if ph == "08":
            return T8.attach(ex, self.tsnaps)
        if ph == "09":
            return O.attach(ex, self.osnaps, self.frows)
        if ph == "10":
            return SC.attach(ex, self.ssnaps)
        return A.attach(ex, self.extras)

    def training(self, target: str) -> list[B.Example]:
        return P7.examples_at(self.dev, target, H, self.frows_h, self.snaps, self.info)[0]


PREDICT = {"07": B.predict, "08": T8.predict, "09": O.predict, "10": SC.predict, "11": A.predict}


def decision_attributes(inp: Inputs) -> list[dict]:
    out = []
    train = {t: inp.training(t) for t in TARGETS}
    for k in inp.keys:
        d, raw = inp.dtab[k], inp.hold[k]
        T = float(d["decision_time"])
        coh, grp = L.cohort_of(d), L.groups_of(d)
        fp = (d.get("token") or {}).get("first_pool_at")
        same_day = [inp.frows[j].get("hist_log_price_change_since_prior") for j in inp.keys
                    if iso(inp.hold[j]["decision_time"])[:10] == iso(T)[:10] and float(inp.hold[j]["decision_time"]) <= T]
        vals = [float(v) for v in same_day if isinstance(v, (int, float)) and math.isfinite(v)]
        med = float(np.median(vals)) if vals else None
        row = {"decision_key": k, "chain": d["chain"], "mint": d["mint"], "decision_time": T, "decision_time_utc": iso(T),
               "day": iso(T)[:10], "route": d["route"], "status": d.get("status"), "status_group": B.status_group(d.get("status")),
               "creator": grp["creator"], "key_conflict": "KEY_CONFLICT" in (d.get("flags") or []),
               "launch_month": fp[:7] if isinstance(fp, str) and len(fp) >= 7 else "UNKNOWN",
               "pool_type": A.launchpad_class(raw["token"]), "regime_at_T": inp.extras[k]["regime"],
               "liquidity_bucket": coh["liquidity_bucket"], "launch_age_bucket": coh["launch_age_bucket"],
               "day_median_log_change_since_prior_as_of_T": med,
               "crash_day_as_of": "UNKNOWN" if med is None else ("CRASH_DAY_AS_OF" if med < CRASH_LOG else "NORMAL_DAY"),
               "tech_status": T8.row_status(inp.tsnaps[k])}
        for t in TARGETS:
            mints = {e.mint for e in train[t]}
            creators = {e.creator for e in train[t] if e.creator}
            row[f"new_mint_{SHORT[t]}"] = d["mint"] not in mints
            row[f"new_creator_{SHORT[t]}"] = (grp["creator"] not in creators) if grp["creator"] else None
        out.append(row)
    return out


def cmd_predict(out: Path, dev_path: str, fs_path: str) -> int:
    t0, c0 = time.time(), time.process_time()
    stores = [dev_path, fs_path, str(REPO / "data/memelab.sqlite")]
    before = {p: fsha(p) for p in stores}
    cards = load_cards()
    inp = Inputs(dev_path, fs_path)
    preds, traps = [], {"NC2_FUTURE_FEATURE": {}, "NC2_COLUMN_OUTSIDE_ALLOWLIST": {}, "P13_HOLDOUT_CARD_ON_DEVELOPMENT_DECISION": {},
                        "P13_CARD_CUTOFF_AFTER_DECISION": {}, "TRAINING_LABEL_AFTER_CUTOFF": {}, "B2_REFIT_EQUALS_FROZEN": {}}
    failures = []
    for t in TARGETS:
        s = SHORT[t]
        ex = inp.examples(t)
        fam_ex = {ph: inp.family(ph, ex) for ph in LOADERS}
        for (ss, cid), v in sorted(cards.items()):
            if ss != s:
                continue
            p, why = E.score(v["card"], fam_ex[v["phase"]], PREDICT[v["phase"]])
            for e, pv, w in zip(ex, p, why):
                preds.append({"target_short": s, "decision_key": e.decision_key, "chain": e.chain, "mint": e.mint,
                              "decision_time": e.decision_time, "candidate": cid, "number": float(pv), "why": w or ""})
        # NC1: B2 refit at H on permuted development training labels (training only); scored like a card
        train = inp.training(t)
        real = B.fit_b2(t, train, H)
        frozen = cards[(s, "P07_B2")]["card"]
        traps["B2_REFIT_EQUALS_FROZEN"][s] = real["body"] == frozen["body"]
        if not traps["B2_REFIT_EQUALS_FROZEN"][s]:
            failures.append(f"{s}: B2 refit at H differs from the frozen card")
        for seed in range(20):
            yy = np.random.default_rng(seed).permutation(B.labels_of(train))
            nc = B.fit_b2(t, train, H, y_override=yy, kind="NC1", meta={"nc1_seed": seed})
            p, why = E.score(nc, ex, B.predict)
            for e, pv, w in zip(ex, p, why):
                preds.append({"target_short": s, "decision_key": e.decision_key, "chain": e.chain, "mint": e.mint,
                              "decision_time": e.decision_time, "candidate": f"NC1_seed{seed:02d}", "number": float(pv), "why": w or ""})
        # NC2: one input available 1 s after the decision must be refused by every family's own check; a column outside an
        # allowlist must be refused
        for ph, name in NC2_FAMILY_CARD.items():
            card = cards[(s, f"P{ph}_{name}")]["card"]
            if "abstain" in card["body"]:
                col = B.LIQ
            elif ph == "11":
                col = A.DIST_COLUMNS[0]
            elif ph == "07":
                col = card["body"]["required"][0]
            else:
                col = card["body"]["spec"]["columns"][0]
            tried = refused = 0
            for e in fam_ex[ph]:
                bad = dataclasses.replace(e, avail={**e.avail, col: e.decision_time + 1.0})
                tried += 1
                try:
                    if "abstain" in card["body"]:
                        B.check_asof([bad], [col], as_of=None, with_labels=False)
                    else:
                        PREDICT[ph](card, [bad])
                except F.AsOfError:
                    refused += 1
            traps["NC2_FUTURE_FEATURE"][f"{s}:P{ph}_{name}:{col}"] = {"tried": tried, "refused": refused}
            if refused != tried:
                failures.append(f"NC2 accepted on {s} P{ph}_{name}")
        checks = {"07": B.check_asof, "08": T8.check_asof, "09": O.check_asof, "10": SC.check_asof, "11": A.check_asof}
        for ph, fn in checks.items():
            try:
                fn(fam_ex[ph][:1], ["label_y_after_decision"], as_of=None, with_labels=False)
                ok = False
            except F.AsOfError:
                ok = True
            traps["NC2_COLUMN_OUTSIDE_ALLOWLIST"][f"{s}:P{ph}"] = ok
            if not ok:
                failures.append(f"allowlist trap accepted on {s} P{ph}")
        # P13: every holdout-start card on development decisions decided before H must raise; a cutoff moved after a holdout
        # decision must raise; a training label maturing after the cutoff must be refused
        dev_ex = train[:25]
        first = min(e.decision_time for e in ex)
        for (ss, cid), v in sorted(cards.items()):
            if ss != s:
                continue
            got = []
            for probe, mod in (("dev", None), ("moved", {"training_cutoff": first + 1.0}),
                               ("late_label", {"max_train_label_matures_at": H + 1.0})):
                c2 = dict(v["card"], **(mod or {}))
                try:
                    E.score(c2, dev_ex if probe == "dev" else ex, PREDICT[v["phase"]])
                    got.append(None)
                except E.RetrospectiveModelNotAvailable as err:
                    got.append(err.status)
                except E.TrainingAfterCutoff:
                    got.append("TRAINING_LABEL_AFTER_CUTOFF")
            traps["P13_HOLDOUT_CARD_ON_DEVELOPMENT_DECISION"][f"{s}:{cid}"] = got[0]
            traps["P13_CARD_CUTOFF_AFTER_DECISION"][f"{s}:{cid}"] = got[1]
            traps["TRAINING_LABEL_AFTER_CUTOFF"][f"{s}:{cid}"] = got[2]
            if got[0] != E.REPLAY_STATUS or got[1] != E.REPLAY_STATUS or got[2] != "TRAINING_LABEL_AFTER_CUTOFF":
                failures.append(f"P13 trap accepted on {s} {cid}: {got}")
    attrs = decision_attributes(inp)
    replay = replay_audit(preds)
    if not replay["ok"]:
        failures.append("replay audit failed")
    preds.sort(key=lambda r: (r["target_short"], r["decision_time"], r["mint"], r["decision_key"], r["candidate"]))
    write_csv(out / PRED_FILE, preds)
    write_csv(out / DEC_FILE, attrs)
    trap_summary = {"failures": failures, "traps": traps, "socialcat_provenance": dict(inp.sc_prov),
                    "holdout_solana_decisions": len(inp.keys), "days": sorted({a["day"] for a in attrs}),
                    "tech_status": dict(Counter(a["tech_status"] or "OK" for a in attrs))}
    write_json(out / "PREOPEN_TRAPS.json", trap_summary)
    write_json(out / "REPLAY_AUDIT.json", replay)
    cand = out / "CANDIDATES.json"
    manifest = {"files": {n: fsha(out / n) for n in (PRED_FILE, DEC_FILE, "PREOPEN_TRAPS.json", "REPLAY_AUDIT.json")
                          + (("CANDIDATES.json", "LEDGER_TOTALS.json") if cand.exists() else ())},
                "prediction_rows": len(preds), "decisions": len(inp.keys), "labels_read": 0,
                "rule": "every holdout prediction is fixed here, before the seal is opened; the opener checks these sha256"}
    write_json(out / "PREOPEN_MANIFEST.json", manifest)
    after = {p: fsha(p) for p in stores}
    run_log(out, "predict", t0, c0, {"stores_before": before, "stores_after": after, "stores_unchanged": before == after,
                                     "failures": failures})
    print(json.dumps({"prediction_rows": len(preds), "decisions": len(inp.keys), "failures": failures,
                      "stores_unchanged": before == after}))
    return 1 if failures or before != after else 0


def replay_audit(preds: list[dict]) -> dict:
    """Every committed development out-of-sample row of Phases 07 to 11 from a fold cutoff at or before its decision, the fold
    cards carrying that cutoff; every holdout prediction from a card trained at H, at or before the decision, not stale."""
    out = {"development": {}, "holdout": {}, "ok": True}
    for ph in ("07", "08", "09", "10", "11"):
        bad = n = 0
        with open(AUD / f"phase_{ph}/experiments/OOS_PREDICTIONS.csv") as f:
            rows = list(csv.DictReader(f))
        cut_of = {}
        for s in SHORT.values():
            fj = json.loads((AUD / f"phase_{ph}/artifacts/folds/{s}.json").read_text())
            for fo in fj["folds"]:
                cuts = {c["training_cutoff_utc"] for c in fo["cards"].values()}
                if cuts != {fo["cutoff_utc"]}:
                    out["ok"] = False
                cut_of[(s, str(fo["fold"]))] = fo["cutoff_utc"]
        for r in rows:
            n += 1
            c = cut_of.get((r["target_short"], r["fold"]))
            if c is None or c != r["cutoff_utc"] or not (C.parse_utc(c) <= C.parse_utc(r["decision_time_utc"])):
                bad += 1
        out["development"][ph] = {"rows": n, "violations": bad}
        out["ok"] &= bad == 0
    for s in SHORT.values():
        rows = [r for r in preds if r["target_short"] == s]
        bad = sum(1 for r in rows if not (H <= r["decision_time"] < END) or r["why"] == E.STALE)
        out["holdout"][s] = {"rows": len(rows), "violations": bad, "card_cutoff_utc": iso(H),
                             "max_age_days": max((r["decision_time"] - H) / 86400 for r in rows) if rows else None}
        out["ok"] &= bad == 0
    return out


# ---------------------------------------------------------------- open: the single opening and every evaluation of the plan
def check_tree_and_manifest() -> dict:
    if git("status", "--porcelain").strip():
        raise SystemExit("the working tree is not clean: commit the plan, code and predictions before the opening")
    man = json.loads((VAL / "PREOPEN_MANIFEST.json").read_text())
    if git("show", "HEAD:audits/predictive-intelligence/phase_12/validation/PREOPEN_MANIFEST.json") != (VAL / "PREOPEN_MANIFEST.json").read_text():
        raise SystemExit("PREOPEN_MANIFEST.json differs from HEAD")
    for n, h in man["files"].items():
        if fsha(VAL / n) != h:
            raise SystemExit(f"{n} differs from the pre-opening manifest: a prediction changed")
    return man


def seal_check() -> tuple[dict, int]:
    p = subprocess.run([sys.executable, "-B", str(AUD / "phase_06/probes/check_seal.py")], capture_output=True, text=True)
    return json.loads(p.stdout), p.returncode


def read_predictions() -> tuple[dict, dict]:
    preds: dict[tuple[str, str], dict] = {}
    with open(VAL / PRED_FILE) as f:
        for r in csv.DictReader(f):
            d = preds.setdefault((r["target_short"], r["decision_key"]),
                                 {"decision_key": r["decision_key"], "chain": r["chain"], "mint": r["mint"],
                                  "decision_time": float(r["decision_time"])})
            d[r["candidate"]] = float(r["number"]) if r["number"] != "" else float("nan")
            d[r["candidate"] + "_why"] = r["why"] or None
    attrs = {}
    with open(VAL / DEC_FILE) as f:
        for r in csv.DictReader(f):
            attrs[r["decision_key"]] = r
    return preds, attrs


def eval_rows(sealed_rows: list[dict], s: str, preds: dict, attrs: dict, *, label_key: str = "label") -> list[dict]:
    out = []
    for r in sealed_rows:
        p = preds.get((s, r["decision_key"]))
        if p is None:
            raise SystemExit(f"no prediction for holdout decision {r['decision_key'][:12]} ({s})")
        E.check_identity(r, p)
        a = attrs[r["decision_key"]]
        y = int(r[label_key]) if label_key == "label" else int(json.loads(r["sensitivity_json"])["conservative_lens"])
        e = B.Example(decision_key=r["decision_key"], chain=r["chain"], mint=r["mint"], decision_time=float(r["decision_time"]),
                      label_matures_at=float(r["label_matures_at"]), y=y, route=r.get("route"), creator=a["creator"] or None,
                      key_conflict=a["key_conflict"] == "1", label_key=r.get("label_key"))
        row = {"example": e, "y": y, "fold": "HOLDOUT", "attrs": a, "sealed": r}
        for k, v in p.items():
            if k not in ("decision_key", "chain", "mint", "decision_time"):
                row[k] = v
        out.append(row)
    return out


def metric_row(s: str, view: str, model: str, ref: str, kind: str, ev: dict, *, p_holm=None, extra=None) -> dict:
    iv = ev.get("intervals") or {}
    cal = ev.get("calibration") or {}
    t = LONG[s]
    row = {"target": t, "target_short": s, "view": view, "model": model, "reference": ref, "kind": kind,
           "n_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "coverage": ev.get("coverage"),
           "abstain_reasons": json.dumps(ev.get("abstain_reasons") or {}, sort_keys=True),
           "positives": ev.get("positives"), "prevalence": ev.get("prevalence"), "days": ev.get("days"), "mints": ev.get("mints"),
           "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"), "bss": ev.get("bss"),
           "log_loss": ev.get("log_loss"), "log_loss_ref": ev.get("log_loss_ref"), "roc_auc": ev.get("auc"),
           "average_precision": ev.get("average_precision"),
           "bss_ci_day_lo": (iv.get("day") or {}).get("ci", [None, None])[0] if (iv.get("day") or {}).get("ci") else None,
           "bss_ci_day_hi": (iv.get("day") or {}).get("ci", [None, None])[1] if (iv.get("day") or {}).get("ci") else None,
           "bss_ci_mint_lo": (iv.get("mint") or {}).get("ci", [None, None])[0] if (iv.get("mint") or {}).get("ci") else None,
           "bss_ci_mint_hi": (iv.get("mint") or {}).get("ci", [None, None])[1] if (iv.get("mint") or {}).get("ci") else None,
           "governing": ev.get("governing") or "UNDEFINED", "p_one_sided": ev.get("p_one_sided"), "p_holm": p_holm,
           "ess_day": ev.get("ess_day"), "ess_mint": ev.get("ess_mint"),
           "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"), "cal_in_the_large_ok": cal.get("in_the_large_ok"),
           "cal_bins": len(cal.get("bins") or []), "cal_every_bin_ok": cal.get("every_bin_ok"), "ece": cal.get("ece"),
           "verdict": E.holdout_verdict(ev, p_holm) if ev.get("n_with_number") else "INSUFFICIENT_HISTORY",
           "note": E.T2_NOTE if t == L.T2 else ""}
    row.update(extra or {})
    return row


def evaluate(rows, model, ref, reps=REPS):
    for r in rows:
        r.setdefault(model, float("nan"))
        r.setdefault(ref, float("nan"))
    return B.evaluate(rows, model, reference=ref, reps=reps, seed=SEED)


def cal_rows(s, view, model, ev) -> list[dict]:
    cal = ev.get("calibration") or {}
    out = [{"target_short": s, "view": view, "model": model, "bin": "IN_THE_LARGE", "n": cal.get("n"), "positives": None,
            "mean_pred": cal.get("mean_pred"), "observed": cal.get("observed"), "wilson_lo": (cal.get("wilson") or [None, None])[0],
            "wilson_hi": (cal.get("wilson") or [None, None])[1], "ok": cal.get("in_the_large_ok"), "note": cal.get("note", "")}]
    for i, b in enumerate(cal.get("bins") or []):
        out.append({"target_short": s, "view": view, "model": model, "bin": i, "n": b["n"], "positives": b["positives"],
                    "mean_pred": b["mean_pred"], "observed": b["observed"], "wilson_lo": b["wilson"][0], "wilson_hi": b["wilson"][1],
                    "ok": b["ok"], "note": f"p {b['p_min']:.4f} to {b['p_max']:.4f}"})
    return out


def synthetic_sealed(src: Path, seed: int = 7) -> list[dict]:
    """SYNTHETIC rows in the sealed file's shape for every holdout decision of `src`'s HOLDOUT_DECISIONS.csv, with random labels
    and a few censored and pending rows: exercises the opening code path without reading any holdout label (dry run only)."""
    rng = np.random.default_rng(seed)
    out = []
    with open(src / DEC_FILE) as f:
        decs = list(csv.DictReader(f))
    for t in TARGETS:
        for d in decs:
            T = float(d["decision_time"])
            u = rng.random()
            st = "VENDOR_OR_ROUTE_GAP" if u < 0.05 else "PENDING" if u < 0.08 else "LABELED"
            y = int(rng.random() < 0.25) if st == "LABELED" else None
            m = C.label_matures_at(t, T)
            out.append({"target": t, "decision_key": d["decision_key"], "chain": d["chain"], "mint": d["mint"], "decision_time": T,
                        "split": "HOLDOUT", "label_matures_at": m, "target_version": C.TARGETS[t]["version"],
                        "labels_version": L.LABELS_VERSION, "registry_sha": C.registry_sha256(),
                        "holdout_contacted": E.contacted(d["mint"], T), "state": st, "censored": 1 if st == "VENDOR_OR_ROUTE_GAP" else 0,
                        "label": y, "label_class": None if y is None else ("TARGET_FIRST" if y else "NO_TOUCH"),
                        "label_observed_at": m + 3600.0 if st == "LABELED" else None, "label_key": "SYN" + d["decision_key"][:20],
                        "flags_json": json.dumps(["KEY_CONFLICT"] if d["key_conflict"] == "1" else []), "route": d["route"],
                        "sensitivity_json": json.dumps({"conservative_lens": (1 if t == L.T2 else 0) if st == "VENDOR_OR_ROUTE_GAP" else y})})
    return out


def cmd_open(out: Path, reproduction: bool, synthetic: Path | None = None) -> int:
    t0, c0 = time.time(), time.process_time()
    global VAL
    if synthetic is not None:
        VAL = synthetic
        sealed = synthetic_sealed(synthetic)
        entry = {"mode": "SYNTHETIC_DRY_RUN", "time_utc": iso(t0), "labels": "SYNTHETIC, no holdout label read"}
    else:
        check_tree_and_manifest()
        report, code = seal_check()
        dec_text = (REPO / "docs/predictive-intelligence/DECISIONS.md").read_text()
        head = git("rev-parse", "HEAD").strip()
        record = {"time_utc": iso(t0), "head": head, "prediction_manifest_sha256": fsha(VAL / "PREOPEN_MANIFEST.json"),
                  "purpose": "Phase 12 single evaluation of the frozen plan (WALK_FORWARD_PROTOCOL.md, PI-D-064)"
                  if not reproduction else "REPRODUCTION of the committed Phase 12 program on the same inputs (no new analysis)"}
        sealed, entry = E.open_holdout(AUD / "phase_06/sealed", seal_report=report, seal_exit=code, decisions_text=dec_text,
                                       log_path=VAL / "OPENING_LOG.json", record=record,
                                       mode="REPRODUCTION" if reproduction else "FIRST_OPENING")
    as_of = t0
    preds, attrs = read_predictions()
    cands = json.loads((VAL / "CANDIDATES.json").read_text())
    champs = {s: c["champion"] for s, c in cands["champions"].items()}
    fitted = {(c["target_short"], c["candidate"]): c["fitted"] for c in cands["candidates"]}
    tot = json.loads((VAL / "LEDGER_TOTALS.json").read_text())
    n_search = tot["n_search"]
    counts, metrics, calib, scored, sens, shift, ledger = {}, [], [], [], [], [], []
    rows_by, prim = {}, {}
    for t in TARGETS:
        s = SHORT[t]
        rows, cnt = E.holdout_rows(sealed, t, as_of=as_of)
        counts[s] = cnt
        rows_by[s] = eval_rows(rows, s, preds, attrs)
        for r in rows_by[s]:
            sr = {"target_short": s, "decision_key": r["example"].decision_key, "mint": r["example"].mint,
                  "decision_time_utc": iso(r["example"].decision_time), "day": r["example"].day, "y": r["y"],
                  "label_class": r["sealed"].get("label_class"), "route": r["sealed"].get("route")}
            for k, v in r.items():
                if k not in ("example", "y", "fold", "attrs", "sealed") and not k.endswith("_why") and not k.startswith("NC1"):
                    sr[k] = v
            scored.append(sr)
    # primary family
    pv = {}
    for t in TARGETS:
        s = SHORT[t]
        ch = champs[s]
        if ch is None:
            prim[s] = {"n_with_number": 0, "n_rows": len(rows_by[s])}
            pv[s] = None
            continue
        prim[s] = evaluate(rows_by[s], ch, "P07_B0")
        pv[s] = prim[s].get("p_one_sided")
    ph = dict(zip(SHORT.values(), E.holm([pv[SHORT[t]] for t in TARGETS])))
    primary_out = {}
    for t in TARGETS:
        s = SHORT[t]
        ev = prim[s]
        ch = champs[s]
        y = [r["y"] for r in rows_by[s]]
        b0 = next(iter({r["P07_B0"] for r in rows_by[s]}), None)
        # creator-group bootstrap interval (P14), beside the governing interval, never governing
        use = [r for r in rows_by[s] if ch and math.isfinite(r[ch]) and math.isfinite(r["P07_B0"])]
        cg = None
        if use:
            yy = np.array([r["y"] for r in use], float)
            pp = np.array([r[ch] for r in use], float)
            bb = np.array([r["P07_B0"] for r in use], float)
            grp = [r["example"].creator or ("mint:" + r["example"].mint) for r in use]
            bs = K.group_bootstrap(grp, lambda i: K.brier_skill(yy[i], pp[i], bb[i]), reps=REPS, seed=SEED)
            cg = {"groups": bs["groups"], "ci": list(bs["ci"]), "finite": bs["finite"]}
        mr = metric_row(s, "PRIMARY", ch or "NONE", "P07_B0", "PRIMARY_HOLDOUT", ev, p_holm=ph.get(s),
                        extra={"creator_group_ci_lo": cg["ci"][0] if cg else None, "creator_group_ci_hi": cg["ci"][1] if cg else None})
        metrics.append(mr)
        calib += cal_rows(s, "PRIMARY", ch or "NONE", ev)
        primary_out[s] = {"target": t, "champion": ch, "metric": mr, "shadow_criteria": E.shadow_criteria(ev) if ch else None,
                          "holdout_prevalence": E.prevalence(y), "training_prevalence_b0": b0, "creator_group_interval": cg,
                          "calibration": ev.get("calibration"), "counts": counts[s]}
        ledger.append(lrow(t, f"P12:{t}:CHAMPION_vs_B0", ch or "NONE", "PRIMARY_HOLDOUT", "PRIMARY vs P07_B0", ev, mr["verdict"]))
    # secondary family: every fitted card against B0 and B2; Holm, max-T, full-search Bonferroni
    sec = []
    for t in TARGETS:
        s = SHORT[t]
        for (ss, cid), fit in sorted(fitted.items()):
            if ss != s or cid == "P07_B0":
                continue
            for ref in ("P07_B0", "P07_B2"):
                if ref == "P07_B2" and cid == "P07_B2":
                    continue
                ev = evaluate(rows_by[s], cid, ref)
                sec.append((s, cid, ref, ev))
    sp = E.holm([ev.get("p_one_sided") for *_, ev in sec])
    mt_in, days, ys, refs = {}, {}, {}, {}
    for t in TARGETS:
        s = SHORT[t]
        days[s] = [r["example"].day for r in rows_by[s]]
        ys[s] = [r["y"] for r in rows_by[s]]
        refs[s] = [r["P07_B0"] for r in rows_by[s]]
        for (ss, cid), fit in fitted.items():
            if ss == s and fit and cid != "P07_B0":
                mt_in[(s, cid)] = [r.get(cid, float("nan")) for r in rows_by[s]]
    mt = E.max_t(days, ys, refs, mt_in, reps=REPS, seed=SEED)
    for (s, cid, ref, ev), p_h in zip(sec, sp):
        mtp = mt.get((s, cid), {}).get("p_max_t") if ref == "P07_B0" else None
        bon = E.bonferroni(ev.get("p_one_sided"), n_search)
        own = E.holdout_verdict(ev, ev.get("p_one_sided")) if ev.get("n_with_number") else "INSUFFICIENT_HISTORY"
        corrected = (own == E.HOLDOUT_SKILL and p_h is not None and math.isfinite(p_h) and p_h < E.ALPHA and
                     mtp is not None and mtp < E.ALPHA and bon is not None and bon < E.ALPHA)
        mr = metric_row(s, "PRIMARY", cid, ref, "SECONDARY_HOLDOUT", ev, p_holm=p_h,
                        extra={"fitted": fitted[(s, cid)], "p_max_t": mtp, "p_bonferroni_full_search": bon, "n_search": n_search,
                               "uncorrected_verdict": own, "skill_after_selection_correction": corrected})
        metrics.append(mr)
        if ev.get("n_with_number"):
            calib += cal_rows(s, "PRIMARY", cid, ev)
        ledger.append(lrow(LONG[s], f"P12:{LONG[s]}:{cid}_vs_{ref[4:]}", cid, "SECONDARY_HOLDOUT", f"PRIMARY vs {ref}", ev, mr["verdict"]))
    # NC1 on the holdout: training-only shuffles of B2
    nc1 = {}
    for t in TARGETS:
        s = SHORT[t]
        ch = champs[s]
        seeds = []
        for seed in range(20):
            c = f"NC1_seed{seed:02d}"
            use = [r for r in rows_by[s] if math.isfinite(r.get(c, float("nan"))) and math.isfinite(r["P07_B0"])]
            bss = K.brier_skill([r["y"] for r in use], [r[c] for r in use], [r["P07_B0"] for r in use]) if use else None
            seeds.append({"seed": seed, "n": len(use), "bss": bss})
            ledger.append({"phase": "12", "experiment_id": f"P12:{t}:NC1_seed{seed}", "target": t, "candidate": "NC1",
                           "kind": "NEGATIVE_CONTROL", "view": "PRIMARY vs P07_B0", "seed": seed, "folds": "HOLDOUT",
                           "n_rows": len(rows_by[s]), "n_with_number": len(use), "verdict": "", "split_fingerprint": SPLIT_FP})
        fin = [x["bss"] for x in seeds if x["bss"] is not None and math.isfinite(x["bss"])]
        use = [r for r in rows_by[s] if math.isfinite(r.get("NC1_seed00", float("nan"))) and math.isfinite(r["P07_B0"])]
        real = prim[s].get("bss") if ch else None
        mean = float(np.mean(fin)) if fin else None
        nc1[s] = {"seeds": seeds, "mean_bss": mean,
                  "verdict": B.nc1_verdict(len(use), int(sum(r["y"] for r in use)), len({r["example"].day for r in use}), mean),
                  "share_of_seeds_above_champion": (sum(1 for x in fin if real is not None and x > real) / len(fin)) if fin else None,
                  "champion_bss": real}
    # NC3: same-ticker join on the real primary rows
    dev = ro(P7.DEV_STORE)
    sym = {}
    for r in dev.execute("SELECT decision_key, mint, chain, decision_time, token_json FROM predictive_decisions"):
        tok = json.loads(r["token_json"]) if r["token_json"] else {}
        sym[r["decision_key"]] = {"symbol": tok.get("symbol"), "mint": r["mint"], "chain": r["chain"],
                                  "decision_time": float(r["decision_time"]), "decision_key": r["decision_key"]}
    by_sym: dict[str, list[dict]] = {}
    for v in sym.values():
        if isinstance(v["symbol"], str) and v["symbol"]:
            by_sym.setdefault(v["symbol"].upper(), []).append(v)
    nc3 = {}
    for t in TARGETS:
        s = SHORT[t]
        tried = refused = 0
        for r in rows_by[s]:
            me = sym[r["example"].decision_key]
            if not isinstance(me["symbol"], str) or not me["symbol"]:
                continue
            others = [o for o in by_sym.get(me["symbol"].upper(), []) if o["mint"] != me["mint"]]
            if not others:
                continue
            o = sorted(others, key=lambda z: (z["decision_time"], z["decision_key"]))[0]
            frow = {"chain": o["chain"], "mint": o["mint"], "decision_time": o["decision_time"], "decision_key": o["decision_key"]}
            tried += 1
            try:
                B.join_by_symbol(dict(r["sealed"]), {me["symbol"]: frow}, me["symbol"])
            except B.IdentityJoinError:
                refused += 1
        nc3[s] = {"same_symbol_rows_tried": tried, "refused": refused}
    failures = [f"NC3 accepted on {s}" for s, v in nc3.items() if v["same_symbol_rows_tried"] != v["refused"]]
    # sensitivities (champion and B0)
    for t in TARGETS:
        s = SHORT[t]
        ch = champs[s]
        if ch is None:
            continue
        views = {}
        r_c, _ = E.holdout_rows(sealed, t, as_of=as_of, exclude_contacted=False)
        views["CONTACTED_INCLUDED"] = eval_rows(r_c, s, preds, attrs)
        r_k, _ = E.holdout_rows(sealed, t, as_of=as_of, include_key_conflict=False)
        views["NO_KEY_CONFLICT"] = eval_rows(r_k, s, preds, attrs)
        views["NEW_MINTS"] = [r for r in rows_by[s] if r["attrs"][f"new_mint_{s}"] == "1"]
        views["NEW_CREATORS"] = [r for r in rows_by[s] if r["attrs"][f"new_creator_{s}"] == "1"]
        views["PIT_ONLY"] = [r for r in rows_by[s] if r["sealed"].get("route") == "PIT_RECORDED"]
        cens = [r for r in sealed if r["target"] == t and r.get("censored") and not E.contacted(r["mint"], float(r["decision_time"]))]
        views["CONSERVATIVE_LENS"] = rows_by[s] + eval_rows(cens, s, preds, attrs, label_key="conservative_lens")
        for v, rr in views.items():
            ev = evaluate(rr, ch, "P07_B0")
            mr = metric_row(s, v, ch, "P07_B0", "SENSITIVITY", ev, p_holm=None)
            sens.append(mr)
            ledger.append(lrow(t, f"P12:{t}:SENS_{v}", ch, "SENSITIVITY", f"{v} vs P07_B0", ev, mr["verdict"]))
        cg = primary_out[s]["creator_group_interval"]
        sens.append({"target": t, "target_short": s, "view": "CREATOR_GROUP_BOOTSTRAP", "model": ch, "reference": "P07_B0",
                     "kind": "SENSITIVITY", "n_with_number": prim[s].get("n_with_number"), "bss": prim[s].get("bss"),
                     "creator_group_ci_lo": cg["ci"][0] if cg else None, "creator_group_ci_hi": cg["ci"][1] if cg else None,
                     "groups": cg["groups"] if cg else None, "verdict": "DESCRIPTIVE_INTERVAL_NOT_GOVERNING",
                     "note": E.T2_NOTE if t == L.T2 else ""})
        ledger.append({"phase": "12", "experiment_id": f"P12:{t}:SENS_CREATOR_GROUP_BOOTSTRAP", "target": t, "candidate": ch,
                       "kind": "SENSITIVITY", "view": "CREATOR_GROUP_BOOTSTRAP", "seed": SEED, "folds": "HOLDOUT",
                       "n_rows": len(rows_by[s]), "n_with_number": prim[s].get("n_with_number"), "verdict": "DESCRIPTIVE",
                       "split_fingerprint": SPLIT_FP})
        # dataset shift (P21): frozen verdict code per cohort value
        for b in ("day", "launch_month", "pool_type", "route", "regime_at_T", "liquidity_bucket", "launch_age_bucket", "crash_day_as_of"):
            vals = sorted({r["attrs"][b] for r in rows_by[s]})
            for val in vals:
                rr = [r for r in rows_by[s] if r["attrs"][b] == val]
                ev = evaluate(rr, ch, "P07_B0")
                mr = metric_row(s, f"{b}={val}", ch, "P07_B0", "DATASET_SHIFT_DESCRIPTIVE", ev, p_holm=None,
                                extra={"breakdown": b, "value": val})
                shift.append(mr)
            ledger.append({"phase": "12", "experiment_id": f"P12:{t}:SHIFT_{b}", "target": t, "candidate": ch,
                           "kind": "DATASET_SHIFT_DESCRIPTIVE", "view": f"{b} ({len(vals)} values)", "seed": SEED, "folds": "HOLDOUT",
                           "n_rows": len(rows_by[s]), "n_with_number": "", "verdict": "DESCRIPTIVE", "split_fingerprint": SPLIT_FP})
        hp = E.prevalence([r["y"] for r in rows_by[s]])
        b0 = primary_out[s]["training_prevalence_b0"]
        shift.append({"target": t, "target_short": s, "view": "prior_shift", "model": "P07_B0", "reference": "", "kind": "DATASET_SHIFT_DESCRIPTIVE",
                      "breakdown": "prior_shift", "value": "holdout prevalence vs training prevalence", "n_rows": hp["n"],
                      "positives": hp["positives"], "prevalence": hp["prevalence"], "cal_mean_pred": b0,
                      "wilson_lo": hp["wilson"][0], "wilson_hi": hp["wilson"][1],
                      "verdict": "TRAINING_PREVALENCE_INSIDE_HOLDOUT_WILSON" if b0 is not None and hp["wilson"][0] <= b0 <= hp["wilson"][1]
                      else "TRAINING_PREVALENCE_OUTSIDE_HOLDOUT_WILSON", "note": E.T2_NOTE if t == L.T2 else ""})
    pre = json.loads((VAL / "PREOPEN_TRAPS.json").read_text())
    for trap, res in sorted(pre["traps"].items()):
        ledger.append({"phase": "12", "experiment_id": f"P12:all:{trap}", "target": "all three", "candidate": trap, "kind": "TRAP_OR_CHECK",
                       "view": "before the opening", "seed": "", "folds": "HOLDOUT", "n_rows": len(res), "n_with_number": "",
                       "verdict": "PASS" if not pre["failures"] else "FAILED", "split_fingerprint": SPLIT_FP})
    ledger.append({"phase": "12", "experiment_id": "P12:all:REPLAY_AUDIT", "target": "all three", "candidate": "REPLAY_AUDIT",
                   "kind": "TRAP_OR_CHECK", "view": "development OOS of Phases 07 to 11 and the holdout predictions", "seed": "",
                   "folds": "", "n_rows": "", "n_with_number": "",
                   "verdict": "PASS" if json.loads((VAL / "REPLAY_AUDIT.json").read_text())["ok"] else "FAILED", "split_fingerprint": SPLIT_FP})
    for i, d in enumerate(DEBUG_RUNS):
        ledger.append({"phase": "12", "experiment_id": f"P12:debug_run_{i + 1}", "target": "all three", "candidate": "plan, predict, open",
                       "kind": "DEBUG_RUN_REAL_DATA", "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                       "verdict": d, "split_fingerprint": ""})
    for trap in ("NC3_SAME_TICKER_JOIN", "MAX_T_SELECTION_CORRECTION"):
        ledger.append({"phase": "12", "experiment_id": f"P12:all:{trap}", "target": "all three", "candidate": trap, "kind": "TRAP_OR_CHECK",
                       "view": "PRIMARY", "seed": SEED, "folds": "HOLDOUT", "n_rows": "", "n_with_number": "", "verdict": "RUN",
                       "split_fingerprint": SPLIT_FP})
    # write
    out.mkdir(parents=True, exist_ok=True)
    scored.sort(key=lambda r: (r["target_short"], r["decision_time_utc"], r["mint"], r["decision_key"]))
    write_csv(out / "HOLDOUT_SCORED.csv", scored)
    write_csv(out / "HOLDOUT_METRICS.csv", metrics)
    write_csv(out / "CALIBRATION_BINS.csv", calib)
    write_csv(out / "SENSITIVITY.csv", sens)
    write_csv(out / "SHIFT_BREAKDOWN.csv", shift)
    write_json(out / "PRIMARY_RESULTS.json", {"primary": primary_out, "holm_family": list(SHORT.values()),
                                              "p_holm": ph, "reps": REPS, "seed": SEED, "t2_note": E.T2_NOTE})
    write_json(out / "HOLDOUT_NEGATIVE_CONTROLS.json", {"NC1": nc1, "NC3": nc3, "failures": failures,
                                                        "NC2_and_P13": "validation/PREOPEN_TRAPS.json (before the opening)"})
    write_json(out / "HOLDOUT_COUNTS.json", counts)
    full = read_ledger("phase_11/experiments/SEARCH_LEDGER.csv") + ledger
    write_csv(out / "FULL_EXPERIMENT_LEDGER.csv", full)
    write_json(out / "FULL_LEDGER_TOTALS.json", E.ledger_totals(full))
    outputs = {n: fsha(out / n) for n in ("HOLDOUT_SCORED.csv", "HOLDOUT_METRICS.csv", "CALIBRATION_BINS.csv", "SENSITIVITY.csv",
                                          "SHIFT_BREAKDOWN.csv", "PRIMARY_RESULTS.json", "HOLDOUT_NEGATIVE_CONTROLS.json",
                                          "HOLDOUT_COUNTS.json", "FULL_EXPERIMENT_LEDGER.csv", "FULL_LEDGER_TOTALS.json")}
    entry = dict(entry, outputs_sha256=outputs, end_utc=iso(time.time()), failures=failures)
    if synthetic is not None:
        write_json(out / "SYNTHETIC_DRY_RUN_LOG.json", entry)
    elif reproduction:
        write_json(out / "REPRODUCTION_LOG.json", entry)
    else:
        log = json.loads((VAL / "OPENING_LOG.json").read_text())
        log["entries"][0] = entry
        write_json(VAL / "OPENING_LOG.json", log)
    run_log(out, "open" if not reproduction else "open_reproduction", t0, c0, {"failures": failures, "outputs_sha256": outputs})
    print(json.dumps({s: {"champion": champs[s], "n": prim[s].get("n_with_number"), "positives": prim[s].get("positives"),
                          "bss": prim[s].get("bss"), "verdict": metrics[i]["verdict"]} for i, s in enumerate(SHORT[t] for t in TARGETS)}))
    return 1 if failures else 0


def lrow(t, eid, cand, kind, view, ev, verdict) -> dict:
    return {"phase": "12", "experiment_id": eid, "target": t, "candidate": cand, "kind": kind, "view": view, "seed": SEED,
            "folds": "HOLDOUT", "n_rows": ev.get("n_rows"), "n_with_number": ev.get("n_with_number"), "verdict": verdict,
            "split_fingerprint": SPLIT_FP}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("plan", "predict", "open"))
    ap.add_argument("out")
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    ap.add_argument("--reproduction", action="store_true")
    ap.add_argument("--synthetic-dry-run", default=None, help="folder holding a predict step's outputs; random labels, no seal")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.step == "plan":
        return cmd_plan(out)
    if a.step == "predict":
        return cmd_predict(out, a.dev_store, a.feature_store)
    return cmd_open(out, a.reproduction, Path(a.synthetic_dry_run) if a.synthetic_dry_run else None)


if __name__ == "__main__":
    raise SystemExit(main())

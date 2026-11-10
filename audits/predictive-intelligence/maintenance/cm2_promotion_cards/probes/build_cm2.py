"""CM-2 build steps (PI-D-122; CHANGE_CONTROL.md Part B). Run in order, each once:

    python -B build_cm2.py fetch_t2      # the 7 PENDING T2 labels of 2026-10-26 (OI21-1): frozen label rules, free GeckoTerminal,
                                         # 5.7 calls a minute, at most 40 calls; raw bodies in ../raw/, calls in ../evidence/
    python -B build_cm2.py labels        # daily/BASE_LABELS.jsonl.gz: every label run and row of the Phase 19 private store plus the
                                         # CM-2 T2 rows; consistency with the Phase 19 ledger checked
    python -B build_cm2.py cards         # fresh cards R-CM2-1 v1 (fit twice, byte-identical), RETIRE the 69 Phase 16 entries,
                                         # REGISTER the 6 cards, PIN NO_VIABLE_CHAMPION per target

Reads the private Phase 19 store ($PI_RESEARCH_DIR/p19, default /home/claude/pi_research/p19) read-only; the daily cycle never
needs it (it reads the committed base set). Writes only under this maintenance folder and audits/predictive-intelligence/daily/.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CM2 = HERE.parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("predictive_daily", REPO / "audits/predictive-intelligence/daily/predictive_daily.py")
D.RAW = CM2 / "raw"                                  # the CM-2 reads are archived in this folder, not in daily/raw
RESEARCH = Path(os.environ.get("PI_RESEARCH_DIR") or "/home/claude/pi_research")
P19 = RESEARCH / "p19"
LEDGER19 = REPO / "audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"
EV = CM2 / "evidence"
STATE = Path(os.environ.get("CM2_STATE") or (RESEARCH / "cm2"))
REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"
P0, WINDOW_END = L.prospective_start(), C.parse_utc("2026-10-26T10:23:04Z") + 1.0
RUN_KEY = L.sha(["cm2-build", L.LABELS_VERSION, C.registry_sha256(), "t2-pending"])


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def window_rows() -> list[dict]:
    c = ro(P19 / "dev_store.sqlite")
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL AND decision_time >= ? "
                                       "AND decision_time < ? ORDER BY decision_time, mint, id", (P0, WINDOW_END))]
    c.close()
    return rows


def p19_universe(now: float, replace: dict) -> L.Universe:
    """The Phase 19 window as Phase 19 built it (its stores and maps), with the CM-2 reads in place of the old ones."""
    lists = json.loads((P19 / "vendor_lists.json").read_text())
    rmap = json.loads((REPO / "audits/predictive-intelligence/phase_19/data/read_map.json").read_text())
    others_p = REPO / "audits/predictive-intelligence/phase_19/data/other_pool_reads.json"
    others = json.loads(others_p.read_text()) if others_p.exists() else {}
    con = sqlite3.connect(f"file:{P19 / 'dev_store.sqlite'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    decs = []
    for r in window_rows():
        if r["chain"] != "solana":
            decs.append(L.decision_from_row(r))
            continue
        vl = lists.get(r["mint"])
        vp = (vl["pools"] if vl.get("pools") is not None else L.LIST_FAILED) if vl else None
        decs.append(L.decision_from_row(r, vendor_pools=vp))
    read_of = {k: L.read_from_store(con, rk) for k, rk in rmap.items()}
    oth = {k: (L.LIST_FAILED if v == L.LIST_FAILED else [L.read_from_store(con, x) if x else None for x in v]) for k, v in others.items()}
    for k, v in replace.get("read_of", {}).items():
        read_of[k] = v
    for k, v in replace.get("other_reads", {}).items():
        oth[k] = v
    return L.Universe(decs, as_of=now, read_of=read_of, other_reads=oth)


def cmd_fetch_t2() -> None:
    idx = M.load(LEDGER19)
    cur = M.current_outcomes(idx)
    pend = sorted(k for (k, t), o in cur.items() if t == L.T2 and o["state"] == "PENDING")
    out_p = EV / "t2_reads.json"
    done = json.loads(out_p.read_text()) if out_p.exists() else {"reads": [], "others": []}
    have = {r["decision_key"] for r in done["reads"]}
    decs = {d["decision_key"]: d for d in p19_universe(time.time(), {}).decisions}
    reader = D.Reader(max_calls=40, deadline=time.time() + 30 * 60)
    for k in pend:
        if k in have:
            continue
        d = decs[k]
        b = int(L.needed_boundary(L.T2, d["decision_time"]))
        url = SRC.gt_url(d["pool"], b, token=d["mint"])
        assert "token=" + d["mint"] in url and b <= time.time() - 60
        got = reader.get(url, kind="ohlcv")
        if got is None:
            raise SystemExit(f"stopped: {reader.stopped}")
        rec = D.read_record("ohlcv", decision_key=k, mint=d["mint"], pool=d["pool"], url=url, boundary=b, code=got[0], body=got[1],
                            sent=got[2], got=got[3])
        done["reads"].append(rec)
        D.jsave(out_p, done)
        print(json.dumps({"decision": k[:12], "http": got[0], "bytes": len(got[1])}), flush=True)
    # other pools for an evidenced reference halt (frozen T2 rule), vendor list from the Phase 19 lists
    rd = {r["decision_key"]: D.to_read(r) for r in done["reads"] if r["http"] == 200}
    u = p19_universe(time.time(), {"read_of": rd})
    lists = json.loads((P19 / "vendor_lists.json").read_text())
    for r in M.prospective_records(u):
        if r["decision_key"] not in rd or r["target"] != L.T2 or r["state"] != L.NEEDS_OTHER_POOLS:
            continue
        if any(o["decision_key"] == r["decision_key"] for o in done["others"]):
            continue
        d = r["decision"]
        vl = lists.get(d["mint"])
        pools = vl.get("pools") if vl else None
        if pools is None:
            url = D.LIST_URL.format(mint=d["mint"])
            got = reader.get(url, kind="pool_list")
            rec = D.read_record("pool_list", decision_key=d["decision_key"], mint=d["mint"], pool=None, url=url, boundary=None,
                                code=got[0], body=got[1], sent=got[2], got=got[3])
            done["others"].append(rec)
            pools = D.pools_of_list(got[1]) if got[0] == 200 else None
        b = int(L.needed_boundary(L.T2, d["decision_time"]))
        for pool in [x for x in (pools or []) if x != d["pool"]][:3]:
            url = SRC.gt_url(pool, b, token=d["mint"])
            got = reader.get(url, kind="ohlcv_other_pool")
            rec = D.read_record("ohlcv_other_pool", decision_key=d["decision_key"], mint=d["mint"], pool=pool, url=url, boundary=b,
                                code=got[0], body=got[1], sent=got[2], got=got[3])
            done["others"].append(rec)
        D.jsave(out_p, done)
    calls_p = EV / "label_calls.json"
    calls = json.loads(calls_p.read_text()) if calls_p.exists() else []
    D.jsave(calls_p, calls + reader.calls)
    print(json.dumps({"pending_t2": len(pend), "reads": len(done["reads"]), "others": len(done["others"]), "calls_now": len(reader.calls)}))


def t2_records(now: float) -> tuple[list[dict], dict]:
    done = json.loads((EV / "t2_reads.json").read_text())
    rd = {r["decision_key"]: D.to_read(r) for r in done["reads"]}
    oth: dict = {}
    for r in done["others"]:
        if r["kind"] == "ohlcv_other_pool":
            oth.setdefault(r["decision_key"], []).append(D.to_read(r))
    u = p19_universe(now, {"read_of": rd, "other_reads": oth})
    recs = M.prospective_records(u)
    # the frozen Phase 19 outcomes of every other pair are reproduced by the same universe (a consistency check)
    cur = M.current_outcomes(M.load(LEDGER19))
    same = diff = 0
    for r in recs:
        if r["decision_key"] in rd and r["target"] == L.T2:
            continue
        o = cur.get((r["decision_key"], r["target"]))
        if o is None:
            continue
        ok = o["state"] == r["state"] and o["label_class"] == (r.get("label_class") if r["state"] == "LABELED" else None)
        same += ok
        diff += not ok
    new = [r for r in recs if r["decision_key"] in rd and r["target"] == L.T2]
    return new, {"other_pairs_reproduced": same, "other_pairs_different": diff}


def cmd_labels() -> None:
    now = time.time()
    new, chk = t2_records(now)
    c = ro(P19 / "dev_store.sqlite")
    c.row_factory = sqlite3.Row
    lines = []
    for r in c.execute("SELECT * FROM predictive_label_runs ORDER BY id"):
        lines.append({"table": "predictive_label_runs", "row": {k: r[k] for k in r.keys() if k != "id"}})
    for r in c.execute("SELECT * FROM predictive_labels ORDER BY id"):
        lines.append({"table": "predictive_labels", "row": {k: r[k] for k in r.keys() if k != "id"}})
    base_n = len(lines)
    lines.append({"table": "predictive_label_runs", "row": {"run_key": RUN_KEY, "labels_version": L.LABELS_VERSION,
                                                            "registry_sha": C.registry_sha256(), "export_ref": REF,
                                                            "params_json": D.canon({"cm2": "t2-pending", "decision": "PI-D-122"}),
                                                            "recorded_at": round(now, 3)}})
    states = Counter()
    for rec in new:
        row = L.record_row(rec, run_key=RUN_KEY, registry_sha=C.registry_sha256(), now=round(now, 3))
        lines.append({"table": "predictive_labels", "row": row})
        states[f"{rec['state']}:{rec.get('label_class')}"] += 1
    blob = gzip.compress("".join(D.canon(x) + "\n" for x in lines).encode(), compresslevel=9, mtime=0)
    D.BASE_LABELS.write_bytes(blob)
    # check: the Phase 19 ledger's LABELED outcomes equal the base set's prospective LABELED rows, pair by pair
    con = D.label_store(STATE)
    led = {(k, t): o["label"] for (k, t), o in M.current_outcomes(M.load(LEDGER19)).items() if o["state"] == "LABELED"}
    base = {}
    for t in D.TARGETS:
        for r in L.training_labels(con, now, t, splits=("PROSPECTIVE",)):
            base[(r["decision_key"], t)] = r["label"]
    extra = {p: v for p, v in base.items() if p not in led}
    res = {"base_lines": len(lines), "from_phase19_store": base_n, "cm2_t2_rows": len(new), "cm2_t2_states": dict(states),
           "phase19_ledger_labeled": len(led), "base_prospective_labeled": len(base),
           "ledger_pairs_equal": sum(1 for p, v in led.items() if base.get(p) == v), "ledger_pairs_missing": sum(1 for p in led if p not in base),
           "base_only_pairs": len(extra), "base_only_are_the_cm2_t2": all(p[1] == L.T2 for p in extra),
           "file_sha256": hashlib.sha256(blob).hexdigest(), **chk}
    D.jsave(EV / "base_labels.json", res)
    print(json.dumps(res))


def cmd_cards() -> None:
    now = time.time()
    rec = D.recipe()
    STATE.mkdir(parents=True, exist_ok=True)
    fs = D.build_store(STATE, REF)
    hold = D.holdout_rows()
    lab = D.label_store(STATE)
    fit = D.fit_version(lab, hold, fs, rec=rec, version=1, now=now)
    fit2 = D.fit_version(lab, hold, fs, rec=rec, version=1, now=now)
    same = all(D.canon(fit["cards"][k]) == D.canon(fit2["cards"][k]) for k in fit["cards"])
    # the B2 inputs from the export-only store equal those of the Phase 19 feature store for every training decision
    from memelab.predictive import baselines as B
    from memelab.predictive import features as F
    a = {r["decision_key"]: r for r in F.training_view(fs, as_of=fit["cutoff"], feature_version=F.FEATURE_VERSION, mode="provider")}
    fs19 = sqlite3.connect(f"file:{P19 / 'fs_store.sqlite'}?mode=ro", uri=True)
    fs19.row_factory = sqlite3.Row
    b = {r["decision_key"]: r for r in F.training_view(fs19, as_of=fit["cutoff"], feature_version=F.FEATURE_VERSION, mode="provider")}
    keys = set()
    for t in D.TARGETS:
        keys |= {r["decision_key"] for r in L.training_labels(lab, fit["cutoff"], t, splits=D.WIDE, spent_holdout_rows=hold)}
    diff = 0
    for k in keys:
        xa, _ = B.model_inputs(a[k])
        xb, _ = B.model_inputs(b[k]) if k in b else ({}, {})
        for c in B.B2_COLUMNS:
            va, vb = xa.get(c), xb.get(c)
            if not ((va is None and vb is None) or (va == vb) or (va != va and vb != vb)):
                diff += 1
    ph16 = REPO / "audits/predictive-intelligence/phase_16/registry"
    retire = sorted(p.stem for p in (ph16 / "entries").glob("*.json"))
    evs = D.register_version(fit, rec=rec, version=1, as_of=now, retire=retire,
                             retire_source=hashlib.sha256((ph16 / "REGISTRY_LOG.jsonl").read_bytes()).hexdigest())
    res = {"cutoff_utc": D.iso(fit["cutoff"]), "label_sets": {D.SHORT[t]: v for t, v in fit["label_sets"].items()},
           "cards": {f"{k}_{D.SHORT[t]}": {"model_sha": c["model_sha"], "n_used": c["n_used"], "k_used": c["k_used"],
                                           "abstain": c["body"].get("abstain"), "b0_p": c["body"].get("p")}
                     for (k, t), c in sorted(fit["cards"].items())},
           "second_fit_identical": same, "training_decisions": len(keys), "b2_inputs_differing_from_phase19_store": diff,
           "events": dict(Counter(e["kind"] for e in evs)), "retired": len(retire), "registered_at_utc": D.iso(now),
           "stale_after_utc": D.iso(fit["cutoff"] + D.MAX_AGE)}
    D.jsave(EV / "cards.json", res)
    print(json.dumps(res))


if __name__ == "__main__":
    {"fetch_t2": cmd_fetch_t2, "labels": cmd_labels, "cards": cmd_cards}[sys.argv[1]]()

"""Phase 15 blind coding step (protocol 2, 4, 8): count the eligible catalyst events, code every behavioral-rules-1 document of
the development decisions (Phase 14's committed documents, recomputed and compared) and of the holdout-window decisions (seeds
built exactly as Phase 14 builds them), build the controls, and write EVENT_SET.csv, SCENARIO_CODING.csv, CONTROL_CODING.csv,
HOLDOUT_RULE_SCENARIOS.jsonl and CODING_LOG.json.

Blind: `labels.training_labels` raises; opening the sealed folder, the development label store, the opened holdout's public
scored file or any Phase 07, 10 or 12 prediction file raises; every socket call raises. No label, outcome or prediction is read.

    python -B code_scenarios.py OUT_DIR [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import behavioral as BH  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import scenario_eval as S  # noqa: E402

sys.path.insert(0, str(REPO / "audits/predictive-intelligence/phase_14/probes"))
import seed_convert  # noqa: E402

P14 = REPO / "audits/predictive-intelligence/phase_14/behavioral"
SEEDS_SHA = "a0c618177503013016f0043356ff5d99ec85e55c872c097ddc87c0f57d26a0c1"
RULE_DOCS_SHA = "15ccd5f183e4e00ce5b52a6e1876732e16a8a86941b97bd55ea74ee180cc8e40"
HOLDOUT_CREATED = "2026-10-27T00:00:00Z"        # fixed creation stamp of the holdout-window documents (determinism)
DEBUG_RUNS = ("2026-10-27T00:56:59Z to 00:57:41Z at uncommitted code into the session scratchpad (dbg1): every output written; one "
              "log field was rewritten for readability before the run, nothing after it; no label, outcome or prediction file opened",
              "00:58Z twin (dbg2): every coding output byte-equal to dbg1, the log equal except its times")
LABEL_CALLS: list[str] = []
FORBIDDEN_OPENS: list[str] = []
SOCKET_EVENTS: list[str] = []
FORBIDDEN = ("phase_06/sealed", "p06/dev_store", "p06/sealed_store", "HOLDOUT_SCORED", "HOLDOUT_PREDICTIONS", "OOS_PREDICTIONS",
             "HOLDOUT_DECISIONS")


def _no_labels(*a, **k):
    LABEL_CALLS.append("training_labels")
    raise RuntimeError("the Phase 15 coding step reads no label")


L.training_labels = _no_labels


def _hook(event, args):
    if event in ("open", "sqlite3.connect") and args and any(f in str(args[0]) for f in FORBIDDEN):
        FORBIDDEN_OPENS.append(str(args[0]))
        raise RuntimeError(f"the coding step never opens {args[0]}")
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError("the coding step makes no network call")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p10_run_social", REPO / "audits/predictive-intelligence/phase_10/probes/run_social.py")
P10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P10)
H = L.holdout_start()
P = L.prospective_start()
SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}


def fsha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def csv_text(rows: list[dict], cols: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return buf.getvalue()


def coding_rows(set_name, meta, coded) -> list[dict]:
    warn = S.warnings_of(coded)
    labs = S.labels_by_target(coded)
    out = []
    for t in S.PRIMARY:
        out.append({"set": set_name, "decision_key": meta["decision_key"], "mint": meta["mint"],
                    "decision_time_utc": meta["decision_time_utc"], "day": meta["decision_time_utc"][:10],
                    "export_commit": meta["export_commit"], "seed_sha256": meta["seed_sha256"], "doc_sha256": coded["doc_sha256"],
                    "coding_status": coded["status"], "coding_reason": coded["reason"], "target": t, "target_short": SHORT[t],
                    "warning": warn[t], "labels": "|".join(labs[t]),
                    "n_statements": sum(1 for s in coded["statements"] if s["target"] == t),
                    "n_unscorable_doc": len(coded["unscorable"]), "n_refused_doc": len(coded["refused"]),
                    "no_statement_doc": coded["no_statement"]})
    return out


# ---------------------------------------------------------------- protocol 2: the event count
def event_count(dev_meta: list[dict], hold_meta: list[dict], dev_seeds: dict) -> tuple[list[dict], dict]:
    rows, summary = [], {}
    con = sqlite3.connect(f"file:{REPO / 'data/memelab.sqlite'}?mode=ro", uri=True)
    tabs = {}
    for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if "catal" in n.lower() or "social" in n.lower():
            tabs[n] = con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
    con.close()
    summary["tracked_lab_db_tables"] = tabs
    keys, catkeys = Counter(), Counter()
    for c in sorted({m["export_commit"] for m in dev_meta}):
        for k, v in P10.export_doc(c)["tables"].items():
            keys[k] += 1
            if "catal" in k.lower() or "social" in k.lower():
                catkeys[k] += len(v) if isinstance(v, list) else 1
    summary["development_export_commits"] = len({m["export_commit"] for m in dev_meta})
    summary["export_table_names"] = dict(sorted(keys.items()))
    summary["export_catalyst_or_social_table_rows"] = dict(catkeys)
    summary["data_private_exists"] = (REPO / "data/private").exists()
    ncat = sum(1 for s in dev_seeds.values() for o in s["observations"] if o["kind"] == BH.CATALYST_EVENT)
    summary["catalyst_event_observations_in_dev_seeds"] = ncat
    cc = json.loads((REPO / "audits/predictive-intelligence/phase_10/evidence/crosschecks.json").read_text())
    summary["phase10_real_catalyst_rows"] = cc["real_catalyst_rows"]
    summary["phase10_real_social_rows"] = cc["real_social_rows"]
    reason_of = {"EXCHANGE_ASSET_LIST_LISTING_STATE": "LISTING_STATE_NOT_AN_EVENT", "PAID_BOOST_LIST": "PAID_BOOST_NOT_A_CATALYST_EVENT",
                 "TICKER_SEARCH_RESULTS_NOT_IDENTITY": "TICKER_OR_NAME_SEARCH_NOT_IDENTITY"}
    for r in cc["inbox_catalyst_reads"]:
        rows.append({"row_kind": "CATALYST_CANDIDATE", "source": f"{r['file']}:{r['key']}", "candidate_kind": r["kind"],
                     "first_available_utc": r["first_committed_utc"], "decision_mints_named_by_exact_address": r["decision_mints_named_by_exact_address"],
                     "catalyst_state_as_of_decision": "NOT_CLASSIFIED_NO_CATALYST_TABLES", "eligible_catalyst_event": False,
                     "reason": f"{reason_of.get(r['kind'], 'NOT_AN_EVENT')};SINGLE_READ_BEFORE_THE_FIRST_DECISION_EXPORT;NO_CLASSIFIER_STATE"})
    for set_name, metas in (("DEVELOPMENT", dev_meta), ("HOLDOUT_WINDOW", hold_meta)):
        for m in metas:
            rows.append({"row_kind": "DECISION_SNAPSHOT", "set": set_name, "decision_key": m["decision_key"], "mint": m["mint"],
                         "decision_time_utc": m["decision_time_utc"], "export_commit": m["export_commit"],
                         "seed_sha256": m["seed_sha256"], "availability_proof": "EXPORT_COMMIT (PI-D-015)",
                         "catalyst_state_as_of_decision": m["catalyst_state"], "eligible_catalyst_event": False,
                         "reason": "NO_CATALYST_EVENT_FOR_THIS_DECISION (CATALYST_TABLES_NOT_EXPORTED)"})
    elig = sum(1 for r in rows if r["eligible_catalyst_event"])
    summary["eligible_catalyst_events"] = elig
    summary["required"] = S.MIN_EVENTS
    summary["candidate_items_not_eligible"] = sum(1 for r in rows if r["row_kind"] == "CATALYST_CANDIDATE")
    summary["decision_snapshots"] = {"DEVELOPMENT": S.summarize_rows(dev_meta), "HOLDOUT_WINDOW": S.summarize_rows(hold_meta)}
    return rows, summary


# ---------------------------------------------------------------- protocol 8 controls
def plant(seed: dict, obs: dict) -> dict:
    return BH.build_seed(seed["chain"], seed["mint_address"], seed["snapshot_hash"], seed["decision_time_utc"],
                         list(seed["observations"]) + [obs])


def planted_half(decision_key: str) -> bool:
    return int(hashlib.sha256((decision_key + ":bogus-control").encode()).hexdigest()[0], 16) % 2 == 0


def controls(dev: list[tuple[dict, dict]]) -> tuple[list[dict], dict]:
    rows, summ = [], {}
    for state, name in (("VERIFIED", "NCB_VERIFIED"), ("UNVERIFIED_EVENT", "NCB_UNVERIFIED")):
        c = Counter()
        for meta, seed in dev:
            planted = planted_half(meta["decision_key"])
            s = seed
            if planted:
                s = plant(seed, BH.observation(BH.CATALYST_EVENT, "bogus_control_catalyst", "BOGUS_CONTROL_NOT_A_REAL_EVENT",
                                               seed["decision_time_utc"], f"fictional-bogus-control:{meta['decision_key'][:16]}",
                                               state=state))
            errs = BH.check_seed(s)
            d = BH.rule_scenarios(s, created_at_utc=HOLDOUT_CREATED)
            coded = S.code_document(d, BH.validate_scenario(d))
            warn = S.warnings_of(coded)
            c["planted"] += planted
            c["seed_refused"] += bool(errs)
            c["unscorable_statements"] += len(coded["unscorable"])
            c["planted_unscorable_rumor_fade"] += sum(1 for u in coded["unscorable"] if u["label"] == "RUMOR_FADE")
            c["t1_event_warnings"] += warn[L.T1] == S.WARN_EVENT
            for t in S.PRIMARY:
                rows.append({"control": name, "decision_key": meta["decision_key"], "decision_time_utc": meta["decision_time_utc"],
                             "day": meta["decision_time_utc"][:10], "planted": planted, "seed_check": "|".join(errs),
                             "target": t, "target_short": SHORT[t], "warning": warn[t],
                             "n_unscorable_doc": len(coded["unscorable"]), "coding_status": coded["status"]})
        summ[name] = dict(c)
    for name, mk in (("P28_AFTER_DECISION_OBSERVATION",
                      lambda m, s: BH.observation(BH.LAB_ATTENTION_PROXY, "sc_attention_trend_ord", 2.0,
                                                  BH.iso(C.parse_utc(s["decision_time_utc"]) + 1), f"p28-trap:{m['decision_key'][:16]}")),
                     ("P28_POST_DECISION_DATE_TEXT",
                      lambda m, s: BH.observation(BH.QUOTED_PUBLIC_TEXT, "quoted_note", "TEXT", s["decision_time_utc"],
                                                  f"p28-trap:{m['decision_key'][:16]}",
                                                  quoted_text="price fell hard by " + BH.iso(C.parse_utc(s["decision_time_utc"]) + 86400)[:10]))):
        c = Counter()
        for meta, seed in dev:
            s = plant(seed, mk(meta, seed))
            errs = BH.check_seed(s)
            d = BH.rule_scenarios(s, created_at_utc=HOLDOUT_CREATED)
            coded = S.code_document(d, BH.validate_scenario(d))
            c["seeds"] += 1
            c["refused"] += bool(errs)
            c["statements"] += len(coded["statements"])
            for e in errs:
                c["code:" + e] += 1
        summ[name] = dict(c)
    return rows, summ


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--feature-store", default=P10.P7.FEATURE_STORE)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "behavioral").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if fsha(P14 / "SEEDS_DEV.jsonl") != SEEDS_SHA or fsha(P14 / "RULE_SCENARIOS_DEV.jsonl") != RULE_DOCS_SHA:
        raise SystemExit("Phase 14 seeds or rule documents are not the committed files")
    seeds = {}
    dev_meta = []
    for line in (P14 / "SEEDS_DEV.jsonl").read_text().splitlines():
        r = json.loads(line)
        seeds[r["decision_key"]] = (r["seed"], r["export_commit"], r["check_seed"])
    docs = [json.loads(x) for x in (P14 / "RULE_SCENARIOS_DEV.jsonl").read_text().splitlines()]
    if [d["decision_key"] for d in docs] != list(seeds):
        raise SystemExit("documents and seeds are not in the same order")
    coding, recompute_diff, val_errors, dev_pairs = [], 0, 0, []
    for d in docs:
        seed, commit, _ = seeds[d["decision_key"]]
        doc = d["document"]
        again = BH.rule_scenarios(seed, created_at_utc=doc["provenance"]["created_at_utc"])
        recompute_diff += BH.canon(again) != BH.canon(doc)
        errs = BH.validate_scenario(doc)
        val_errors += bool(errs)
        coded = S.code_document(doc, errs)
        cat_state = next((o["value"] for o in seed["observations"] if o["name"] == "catalyst_state"), None)
        meta = {"decision_key": d["decision_key"], "mint": seed["mint_address"], "decision_time_utc": seed["decision_time_utc"],
                "export_commit": commit, "seed_sha256": seed["seed_sha256"], "catalyst_state": cat_state}
        dev_meta.append(meta)
        dev_pairs.append((meta, seed))
        coding += coding_rows("DEVELOPMENT", meta, coded)
    # holdout-window decisions (E3): seeds built exactly as Phase 14 builds development seeds
    fs = P10.P7.ro(a.feature_store)
    fs_before = P10.P7.fsha(a.feature_store)
    snaps, prov = P10.all_snapshots(fs)
    if prov.get("blob_differs") or prov.get("commit_time_differs"):
        raise SystemExit(f"export context provenance failed: {prov}")
    hold = sorted((s for s in snaps.values() if H <= float(s["decision_time"]) < P), key=lambda s: (s["decision_time"], s["decision_key"]))
    hold_meta, hold_lines, hold_refused = [], [], 0
    for s in hold:
        seed = seed_convert.seed_from_snapshot(s)
        serrs = BH.check_seed(seed)
        hold_refused += bool(serrs)
        doc = BH.rule_scenarios(seed, created_at_utc=HOLDOUT_CREATED)
        errs = BH.validate_scenario(doc)
        val_errors += bool(errs)
        coded = S.code_document(doc, errs)
        meta = {"decision_key": s["decision_key"], "mint": seed["mint_address"], "decision_time_utc": seed["decision_time_utc"],
                "export_commit": s["export_commit"], "seed_sha256": seed["seed_sha256"], "catalyst_state": s["catalyst_state"]}
        hold_meta.append(meta)
        hold_lines.append(BH.canon({"decision_key": s["decision_key"], "export_commit": s["export_commit"], "seed": seed,
                                    "check_seed": serrs, "document": doc}))
        coding += coding_rows("HOLDOUT_WINDOW", meta, coded)
    ev_rows, ev_summary = event_count(dev_meta, hold_meta, {k: v[0] for k, v in seeds.items()})
    ctrl_rows, ctrl_summary = controls(dev_pairs)
    files = {}
    ccols = ["set", "decision_key", "mint", "decision_time_utc", "day", "export_commit", "seed_sha256", "doc_sha256", "coding_status",
             "coding_reason", "target", "target_short", "warning", "labels", "n_statements", "n_unscorable_doc", "n_refused_doc",
             "no_statement_doc"]
    files["behavioral/SCENARIO_CODING.csv"] = csv_text(coding, ccols)
    files["behavioral/CONTROL_CODING.csv"] = csv_text(ctrl_rows, ["control", "decision_key", "decision_time_utc", "day", "planted",
                                                                  "seed_check", "target", "target_short", "warning",
                                                                  "n_unscorable_doc", "coding_status"])
    files["behavioral/EVENT_SET.csv"] = csv_text(ev_rows, ["row_kind", "set", "source", "candidate_kind", "decision_key", "mint",
                                                           "decision_time_utc", "export_commit", "seed_sha256", "first_available_utc",
                                                           "availability_proof", "decision_mints_named_by_exact_address",
                                                           "catalyst_state_as_of_decision", "eligible_catalyst_event", "reason"])
    files["behavioral/HOLDOUT_RULE_SCENARIOS.jsonl"] = "\n".join(hold_lines) + "\n"
    for k, v in files.items():
        (out / k).write_text(v)
    warn_counts = Counter((r["set"], r["target_short"], r["warning"]) for r in coding)
    log = {"script": "audits/predictive-intelligence/phase_15/probes/code_scenarios.py", "start_utc": BH.iso(t0),
           "end_utc": BH.iso(time.time()), "head": P10.git("rev-parse", "HEAD").strip(), "main_ref": P10.MAIN_REF,
           "coding_version": S.CODING_VERSION, "scenario_eval_version": S.SCENARIO_EVAL_VERSION, "rules_sha256": BH.RULES_SHA256,
           "phase14_seeds_sha256": SEEDS_SHA, "phase14_rule_documents_sha256": RULE_DOCS_SHA,
           "feature_store_sha256_before": fs_before, "feature_store_sha256_after": P10.P7.fsha(a.feature_store),
           "development_documents": len(docs), "development_recompute_differences": recompute_diff,
           "holdout_window_decisions": len(hold), "holdout_window_seeds_refused": hold_refused,
           "documents_with_validation_errors": val_errors,
           "coding_status": {f"{k[0]}:{k[1]}": v for k, v in sorted(Counter((r["set"], r["coding_status"]) for r in coding
                                                                             if r["target"] == L.T1).items())},
           "warnings": {f"{a_}:{b}:{c}": v for (a_, b, c), v in sorted(warn_counts.items())},
           "event_count": ev_summary, "controls": ctrl_summary, "debug_runs": list(DEBUG_RUNS),
           "label_calls": LABEL_CALLS, "forbidden_opens": FORBIDDEN_OPENS, "socket_events": SOCKET_EVENTS,
           "outputs_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}}
    (out / "behavioral/CODING_LOG.json").write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: log[k] for k in ("development_documents", "development_recompute_differences", "holdout_window_decisions",
                                          "documents_with_validation_errors", "label_calls", "forbidden_opens", "socket_events")}))
    print(json.dumps(log["event_count"]["eligible_catalyst_events"]), json.dumps(log["controls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

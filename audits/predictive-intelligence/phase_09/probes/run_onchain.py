"""Phase 09 on-chain runner: onchain-1 for every Solana decision of the store (coverage) and every labelled development decision
(with the version 2 consistency check), the frozen walk-forward of R1, M1 to M3, A1 and NC1-OC beside Phase 07's B0 and B2 on the
same folds, the model against the simple on-chain rule, the veto alarm and early-warning tables, the train-only cards at the
holdout start, the traps (NC2-OC, P13-OC, P36-OC, CX-09), the real cross-checks (authority readings, swaps against candles,
holder classes), the collector state on this machine, the forecast trace and the cumulative search ledger.

Reads only: the Phase 06 development store (labels through `labels.training_labels`, decision rows), the Phase 05 store (version 2
snapshots through `features.training_view`, decision rows through `features.AsOfView`, candles for one cross-check) and the
tracked lab database (Oct 6 to 7 on-chain tables, cross-checks only), all opened read-only. Never opens the sealed holdout
folder. No network: an audit hook refuses any socket call. Deterministic: two runs into two folders give identical files except
`evidence/run_log.json` (times) and the trace's latency field.

    python -B run_onchain.py OUTDIR [--reps 2000] [--dev-store PATH] [--feature-store PATH] [--npz PATH]

PROVISIONAL (PI-D-046): until Phase 06's 48 h revision re-read is folded in. If it changes a development label, rerun this
script at the Phase 09 code commit; the new outputs supersede these.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import resource
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import depth_adapter as DA  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import onchain as O  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 09 runner makes no network call ({event})")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p07_run_baselines", REPO / "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
P7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P7)

SHORT, H = P7.SHORT, P7.H
LAB_DB = REPO / "data" / "memelab.sqlite"
CODE = ["memelab/predictive/onchain.py", "memelab/predictive/depth_adapter.py", "memelab/predictive/baselines.py",
        "memelab/predictive/stats.py", "memelab/predictive/features.py", "memelab/predictive/labels.py",
        "memelab/predictive/contract.py", "audits/predictive-intelligence/phase_07/probes/run_baselines.py",
        "audits/predictive-intelligence/phase_09/probes/run_onchain.py"]
VIEWS = P7.VIEWS
P07 = REPO / "audits/predictive-intelligence/phase_07"
P08 = REPO / "audits/predictive-intelligence/phase_08"
P07_SPLITS = {"T1_24h": "0ab64525e04b8664a1cab51c9e24f5fa4f750681d32a5d97bfc520710e3845a4",
              "T1b_6h": "aa16e7adeae7d5bc8567de9ab85ed1f28843afe51bc0de9b52e24d587beb8a31",
              "T2_24h": "82a1c33b12cef45995eb15edd07b8e27ddcd76eafbdb8c503f5feb9501be86cd"}
TARGET_ORDER = (L.T2, L.T1, L.T1B)               # T2 is the target this phase is about and is reported first
# real-data runs before the recorded run (P22): appended before the recorded run, never removed
DEBUG_RUNS: list[str] = [
    "features-only probe after the pre-registration commit 3079af1 (22:42:40Z to 22:42:41Z): onchain-1 missing-reason counts over "
    "the 925 Solana decision rows of the Phase 05 store; no label read, no fit, no metric",
    "recorded run 1 at 15bc5b5 (22:54:40Z to 22:55:35Z): every configuration of the registry on real labels; it wrote the experiment "
    "tables, then stopped in the P36-OC trap (the in-memory store refused the copied decision row by its foreign key to the raw "
    "export read); outputs were not read; repaired in the runner only (foreign keys off in that in-memory copy) and rerun as "
    "recorded run 2, which supersedes it",
]
COMPARISONS = ([(m, "B0") for m in ("B2",) + O.MODEL_IDS] + [(m, "B2") for m in ("R1_OC_RULE", "M1_OC_LOGIT", "M2_OC_LOGIT_B2", "M3_OC_LOGIT_TREND")]
               + [(m, "R1_OC_RULE") for m in ("M1_OC_LOGIT", "M2_OC_LOGIT_B2", "M3_OC_LOGIT_TREND")] + [("M2_OC_LOGIT_B2", "A1_OC_B2_TC")])
KIND = {"B2": "REFERENCE_PHASE07", "R1_OC_RULE": "SIMPLE_ONCHAIN_RULE", "M1_OC_LOGIT": "ONCHAIN_MODEL", "M2_OC_LOGIT_B2": "ONCHAIN_MODEL_PRIMARY",
        "M3_OC_LOGIT_TREND": "ONCHAIN_MODEL", "A1_OC_B2_TC": "ABLATION"}


def write_csv(path: Path, rows: list[dict]) -> None:
    P7.write_csv(path, rows)


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


def iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- onchain-1 snapshots
def all_snapshots(fs):
    out = {}
    for r in fs.execute("SELECT decision_key, chain, mint, decision_time FROM predictive_decisions WHERE chain='solana' "
                        "AND decision_key IS NOT NULL ORDER BY decision_time, id"):
        out[r["decision_key"]] = O.onchain_as_of(fs, r["chain"], r["mint"], float(r["decision_time"]), decision_key=r["decision_key"])
    return out


def labelled_keys(dev):
    keys = {}
    for t in L.TARGETS:
        for kc in (True, False):
            for r in L.training_labels(dev, H, t, mode="provider", include_key_conflict=kc):
                keys[r["decision_key"]] = r
    return keys


def oex_at(dev, target, as_of, frows, snaps, info, osnaps, *, include_kc=True):
    ex, rows = P7.examples_at(dev, target, as_of, frows, snaps, info, include_kc=include_kc)
    return O.attach(ex, osnaps, frows), rows


# ---------------------------------------------------------------- metrics
def metric_row(target, view, ev, *, model, reference, kind, extra):
    iv = ev.get("intervals") or {}
    cal = ev.get("calibration") or {}
    return {"target": target, "target_short": SHORT[target], "view": view, "model": model, "reference": reference, "kind": kind,
            "n_oos_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "coverage": ev.get("coverage"),
            "abstain_reasons": ";".join(f"{k}={v}" for k, v in sorted(ev.get("abstain_reasons", {}).items())),
            "positives": ev.get("positives"), "prevalence": ev.get("prevalence"), "decision_days": ev.get("days"),
            "mints": ev.get("mints"), "folds_with_number": ev.get("folds"), "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"),
            "bss_vs_ref": ev.get("bss"), "log_loss": ev.get("log_loss"), "log_loss_ref": ev.get("log_loss_ref"),
            "roc_auc": ev.get("auc"), "average_precision": ev.get("average_precision"),
            "bss_ci_day_lo": (iv.get("day", {}).get("ci") or [None, None])[0], "bss_ci_day_hi": (iv.get("day", {}).get("ci") or [None, None])[1],
            "bss_ci_mint_lo": (iv.get("mint", {}).get("ci") or [None, None])[0], "bss_ci_mint_hi": (iv.get("mint", {}).get("ci") or [None, None])[1],
            "governing": ev.get("governing") or ("UNDEFINED" if ev.get("n_with_number") else ""),
            "p_one_sided": ev.get("p_one_sided"), "p_holm": extra.get("p_holm"), "ess_day": ev.get("ess_day"), "ess_mint": ev.get("ess_mint"),
            "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"), "cal_in_the_large_ok": cal.get("in_the_large_ok"),
            "cal_bins": len(cal.get("bins") or []), "cal_every_bin_ok": cal.get("every_bin_ok"), "ece": cal.get("ece"),
            "degenerate": extra.get("degenerate"), "verdict": ev.get("verdict"), "promotion": "" if model == "B2" else "MODEL_NOT_PROMOTED",
            "status": O.PROVISIONAL, "revision_check_claimed": False,
            **{k: v for k, v in extra.items() if k not in ("p_holm", "degenerate")}}


def nc1_summary(rows, seeds, reps):
    out = []
    for s in seeds:
        key = f"NC1OC_{s}"
        if not rows or not any(math.isfinite(r[key]) for r in rows):
            out.append({"seed": s, "n": 0})
            continue
        ev = B.evaluate(rows, key, reps=reps, seed=20261025 + s, boot=False)
        out.append({"seed": s, "n": ev["n_with_number"], "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"), "bss": ev.get("bss"),
                    "positives": ev.get("positives"), "days": ev.get("days")})
    return out


def ew_cohorts(rows, model, key, touch):
    out = []
    for v in sorted({str(key(r["example"]) if key(r["example"]) is not None else "UNKNOWN") for r in rows}):
        rr = [r for r in rows if str(key(r["example"]) if key(r["example"]) is not None else "UNKNOWN") == v]
        e = O.early_warning(rr, model, touch=touch)
        out.append({"value": v, **{k: e[k] for k in ("scored", "hits", "misses", "false_alarms", "correct_rejections", "lead_time_h_median",
                                                      "support_note")}})
    return out


# ---------------------------------------------------------------- traps
def traps(fs, dev_ex_by_target, osnaps, cards_h, all_snaps):
    out = {}
    # NC2-OC: the next decision of the same mint (its onchain-1 values), declared at its true availability
    n = val = refused_allow = refused_asof = accepted = 0
    seen = set()
    min_delay = None
    for target, exs in dev_ex_by_target.items():
        for e in exs:
            if e.decision_key in seen:
                continue
            seen.add(e.decision_key)
            n += 1
            nxt = fs.execute("SELECT decision_key, decision_time FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time > ? "
                             "ORDER BY decision_time, id LIMIT 1", (e.chain, e.mint, e.decision_time)).fetchone()
            if nxt is None:
                continue
            s2 = all_snaps.get(nxt["decision_key"])
            if s2 is None or s2["values"]["oc_structural_fatal"]["value"] is None:
                continue
            val += 1
            fut, av = s2["values"]["oc_structural_fatal"]["value"], s2["values"]["oc_structural_fatal"]["available_at"]
            min_delay = av - e.decision_time if min_delay is None else min(min_delay, av - e.decision_time)
            e2 = O.OExample(**{**e.__dict__, "x": {**e.x, "trap_next_decision_structural": fut},
                               "avail": {**e.avail, "trap_next_decision_structural": av}})
            try:
                O.check_asof([e2], ["trap_next_decision_structural"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_allow += 1
            e3 = O.OExample(**{**e.__dict__, "x": {**e.x, "oc_structural_fatal": fut}, "avail": {**e.avail, "oc_structural_fatal": av}})
            try:
                O.check_asof([e3], ["oc_structural_fatal"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_asof += 1
    out["NC2OC"] = {"labelled_decisions": n, "with_a_later_decision_of_the_mint": val, "refused_by_allowlist": refused_allow,
                    "refused_by_validate_rows": refused_asof, "accepted": accepted, "min_trap_delay_s": min_delay,
                    "pass": accepted == 0 and refused_allow == refused_asof == val and val > 0}
    # P13-OC: holdout-start cards applied to the earliest development decision
    res = {}
    for target, exs in dev_ex_by_target.items():
        e = min(exs, key=lambda x: (x.decision_time, x.mint))
        for m, card in cards_h[target].items():
            try:
                O.predict(card, [e])
                res[f"{SHORT[target]}:{m}"] = "ACCEPTED"
            except O.ModelTrainedAfterDecision:
                res[f"{SHORT[target]}:{m}"] = "REFUSED"
    out["P13OC"] = {"results": res, "pass": all(v == "REFUSED" for v in res.values())}
    # P36-OC: one real decision row copied into an in-memory store with its snapshot time moved 60 s after the decision
    e = min(dev_ex_by_target[L.T2], key=lambda x: (x.decision_time, x.mint))
    row = dict(fs.execute("SELECT * FROM predictive_decisions WHERE decision_key=?", (e.decision_key,)).fetchone())
    mem = S.connect(":memory:")
    mem.execute("PRAGMA foreign_keys=OFF")              # the copied row's raw export read is not copied (runner repair after run 1)
    rj = json.loads(row["row_json"])
    sn = json.loads(rj["snapshot_json"])
    sn["t"] = float(row["decision_time"]) + 60.0
    rj["snapshot_json"] = json.dumps(sn)
    cols = [c for c in row if c != "id"]
    row2 = dict(row, row_json=json.dumps(rj))
    mem.execute(f"INSERT INTO predictive_decisions ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row2[c] for c in cols])
    s = O.onchain_as_of(mem, row["chain"], row["mint"], float(row["decision_time"]), decision_key=row["decision_key"])
    reasons = Counter(v["missing_reason"] for v in s["values"].values())
    out["P36OC"] = {"decision_key": e.decision_key, "values_with_a_number": sum(1 for v in s["values"].values() if v["value"] is not None),
                    "reasons": dict(reasons), "pass": reasons.get("INCONSISTENT_TIME") == len(O.OC)}
    # CX-09: a collector database built from the documented schema with this decision and its first post-decision reads
    out["CX09"] = cx09_probe(e)
    return out


def collector_fixture(path: Path, rows: list[tuple]) -> None:
    con = sqlite3.connect(path)
    con.executescript((REPO / "tests/fixtures/predictive/bt_depth_schema_v2.sql").read_text())
    con.execute("INSERT INTO bt_schema_migrations VALUES (1,'v1','x',0),(2,'forward depth collector','y',0)")
    for sql, args in rows:
        con.execute(sql, args)
    con.commit()
    con.close()


def cx09_probe(e) -> dict:
    import tempfile
    T = e.decision_time
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bt.sqlite"
        ins = "INSERT INTO bt_depth_decisions (chain,mint,pool_address,pool_source,export_commit,export_time,created_at,row_sha256,status,recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        snap = ("INSERT INTO bt_depth_snapshots (run_id,decision_id,chain,mint,pool_address,kind,provider,size_usd,captured_at,state,since_export_s,"
                "reserve_usd,price_usd,out_usd,price_impact,recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
        rows = [(ins, ("solana", e.mint, "POOLX", "EXPORT_PRIMARY_POOL", "c", T, T - 600, e.row_sha256 or "r", "WATCH", T, "h1"))]
        for i, lag in enumerate((420.0, 3900.0)):
            rows.append((snap, ("run", 1, "solana", e.mint, "POOLX", "POOL", "geckoterminal", None, T + lag, "OK", lag, 50000.0, 1.0, None, None, T, f"p{i}")))
            rows.append((snap, ("run", 1, "solana", e.mint, "POOLX", "QUOTE", "jupiter", 500.0, T + lag + 5, "OK", lag + 5, None, 1.0, 470.0, 0.05, T, f"q{i}")))
        collector_fixture(p, rows)
        con = DA.connect_ro(p)
        obs = DA.observations(con, chain="solana", mint=e.mint)
        vis = DA.visible_at(obs, T)
        try:
            DA.assert_visible(obs[:1], T)
            refused = False
        except DA.DepthLeakageError:
            refused = True
        con.close()
    return {"decision_key": e.decision_key, "fixture_rows": len(obs), "first_read_lag_s": 420.0, "visible_at_decision": len(vis),
            "first_read_as_feature_refused": refused, "evidence_class": "TEST_ONLY", "pass": len(vis) == 0 and refused}


# ---------------------------------------------------------------- real cross-checks
def lab_ro():
    con = sqlite3.connect(f"file:{LAB_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def authority_crosscheck(fs, all_snaps):
    lab = lab_ro()
    rows = [dict(r) for r in lab.execute("SELECT mint, observed_at, source, mint_authority, freeze_authority, token_program, transfer_fee_bps "
                                         "FROM token_authorities ORDER BY mint, observed_at")]
    by_mint: dict[str, list] = {}
    for s in all_snaps.values():
        by_mint.setdefault(s["mint"], []).append(s)
    out, agree, disagree, none_after = [], 0, 0, 0
    for r in rows:
        later = sorted([s for s in by_mint.get(r["mint"], []) if s["decision_time"] >= r["observed_at"]], key=lambda s: s["decision_time"])
        if not later:
            none_after += 1
            continue
        s = later[0]
        lab_mint, lab_freeze = float(r["mint_authority"] is not None), float(r["freeze_authority"] is not None)
        v = s["values"]
        ok = (v["oc_mint_authority_active"]["value"] == lab_mint and v["oc_freeze_authority_active"]["value"] == lab_freeze)
        tp = 1.0 if r["token_program"] == O.TOKEN_2022 else 0.0 if r["token_program"] == O.TOKEN_SPL else None
        ok_tp = v["oc_token2022"]["value"] == tp
        agree += ok and ok_tp
        disagree += not (ok and ok_tp)
        out.append({"mint": r["mint"], "lab_db_observed_at_utc": iso(r["observed_at"]), "lab_db_source": r["source"],
                    "lab_db_mint_authority_set": bool(lab_mint), "lab_db_freeze_authority_set": bool(lab_freeze),
                    "decision_time_utc": iso(s["decision_time"]), "hours_after": round((s["decision_time"] - r["observed_at"]) / 3600, 2),
                    "oc_mint_authority_active": v["oc_mint_authority_active"]["value"], "oc_freeze_authority_active": v["oc_freeze_authority_active"]["value"],
                    "oc_token2022": v["oc_token2022"]["value"], "lab_db_token_program_2022": tp, "agree": bool(ok and ok_tp)})
    lab.close()
    return {"rows": len(rows), "compared": len(out), "agree": agree, "disagree": disagree, "no_decision_after": none_after,
            "mints": len({r["mint"] for r in rows}), "detail": out,
            "note": "lab DB reads of Oct 6 to 7 (source merged) against the nearest later export decision; both are the lab's own readings, "
                    "not an independent chain read"}


def swaps_vs_candles(fs):
    lab = lab_ro()
    tr = [dict(r) for r in lab.execute("SELECT mint, pool_address, tx_hash, block_time, kind, usd, source FROM wallet_transactions")]
    lab_pools = {}
    for r in lab.execute("SELECT pool_address, mint, dex FROM pools"):
        lab_pools.setdefault(r["mint"], []).append({"pool": r["pool_address"], "dex": r["dex"]})
    lab.close()
    kinds = Counter((r["kind"], r["source"]) for r in tr)
    sig_len = Counter(len(r["tx_hash"] or "") for r in tr)
    out = []
    for mint in sorted({r["mint"] for r in tr}):
        ts = [r for r in tr if r["mint"] == mint]
        tt = sorted(datetime.fromisoformat(r["block_time"].replace("Z", "+00:00")).timestamp() for r in ts)
        pool = fs.execute("SELECT pool_address FROM predictive_decisions WHERE chain='solana' AND mint=? AND pool_address IS NOT NULL "
                          "ORDER BY decision_time LIMIT 1", (mint,)).fetchone()
        pool = pool[0] if pool else None
        row = {"mint": mint, "swaps": len(ts), "first_utc": iso(tt[0]), "last_utc": iso(tt[-1]), "decision_pool": pool,
               "lab_db_pools": len(lab_pools.get(mint, [])), "lab_db_dexes": ";".join(sorted({p["dex"] for p in lab_pools.get(mint, [])}))}
        if pool is None:
            out.append(dict(row, buckets_compared=0, note="no point-in-time pool in the export"))
            continue
        buckets: dict[int, float] = {}
        for r in ts:
            t = datetime.fromisoformat(r["block_time"].replace("Z", "+00:00")).timestamp()
            b = int(t // 300) * 300
            buckets[b] = buckets.get(b, 0.0) + float(r["usd"] or 0.0)
        inner = sorted(buckets)[1:-1]                    # edges are partial (the read holds the latest trades only)
        cand = {}
        for c in fs.execute("SELECT start_at, v, id FROM predictive_candles WHERE chain='solana' AND mint=? AND pool_address=? AND period_s=300 "
                            "AND vanished=0 ORDER BY id", (mint, pool)):
            cand[int(c[0])] = float(c[1])
        ratios = [buckets[b] / cand[b] for b in inner if b in cand and cand[b] > 0]
        missing = sum(1 for b in inner if b not in cand)
        row.update(buckets_compared=len(ratios), buckets_without_candle=missing,
                   ratio_median=round(statistics.median(ratios), 4) if ratios else None,
                   within_10pct=sum(1 for x in ratios if abs(x - 1) <= 0.10), within_50pct=sum(1 for x in ratios if abs(x - 1) <= 0.50))
        out.append(row)
    return {"swap_rows": len(tr), "kinds": {f"{k}:{s}": n for (k, s), n in sorted(kinds.items())},
            "signature_lengths": {str(k): v for k, v in sorted(sig_len.items())}, "per_mint": out,
            "note": "every row is a GeckoTerminal trade (a swap against a pool), none a transfer; signatures are 10-character prefixes, so "
                    "no transaction can be verified on chain; the trades' pool is not recorded, so a mismatch against the decision pool's "
                    "candles can be pool fragmentation (P02)"}


def holder_classes():
    lab = lab_ro()
    rows = [dict(r) for r in lab.execute("SELECT mint, owner, classification, classification_basis, insider_flag FROM holders")]
    toks = {r["mint"]: dict(r) for r in lab.execute("SELECT * FROM tokens")}
    lab.close()
    cex = {r["owner"]: r["classification_basis"] for r in rows if r["classification"] == "CEX"}
    res = Counter()
    for r in rows:
        role = O.wallet_role(r["owner"], token_row=toks.get(r["mint"]), cex_labels=cex)
        res[(r["classification"], role["role"], role["insider"])] += 1
    cex_insider = sum(1 for r in rows if r["classification"] == "CEX" and r["insider_flag"])
    return {"holder_rows": len(rows), "lab_class_to_role": [{"lab_class": a, "role": b, "insider": c, "n": n} for (a, b, c), n in sorted(res.items(), key=str)],
            "cex_rows": sum(1 for r in rows if r["classification"] == "CEX"), "cex_rows_with_lab_insider_flag": cex_insider,
            "cex_rows_mapped_to_insider": sum(n for (a, b, c), n in res.items() if a == "CEX" and c),
            "pass": cex_insider == 0 and sum(n for (a, b, c), n in res.items() if a == "CEX" and c) == 0}


def dev_wallet_cases(fs):
    out = []
    mints = {r[0] for r in fs.execute("SELECT DISTINCT mint FROM predictive_decisions")}
    seen = set()
    for r in fs.execute("SELECT mint, token_json FROM predictive_decisions WHERE chain='solana' ORDER BY decision_time"):
        t = json.loads(r[1] or "{}")
        d = t.get("dev_wallet")
        if not d or (r[0], d) in seen:
            continue
        seen.add((r[0], d))
        role = O.wallet_role(d, token_row=t, known_mints=mints)
        if role["role"] != "DEV":
            out.append({"mint": r[0], "dev_wallet": d, "role": role["role"], "basis": role["basis"], "why": role["label"]})
    return {"token_rows_with_dev_wallet": len(seen), "not_observed_dev": out}


# ---------------------------------------------------------------- forecast trace
def trace(fs, res_by_target, osnaps, cards_h, info):
    pick = None
    spec = O.SPECS[O.PRIMARY]
    for target in TARGET_ORDER:
        rows = sorted([r for r in res_by_target[target]["oos"] if O.complete(r["example"], spec["rows"])],
                      key=lambda r: (r["example"].decision_time, r["example"].mint))
        if rows:
            pick = (target, rows[0])
            break
    if pick is None:
        return {"status": "NO_OOS_ROW_WITH_EVERY_M2_INPUT"}
    target, row = pick
    e = row["example"]
    s = osnaps[e.decision_key]
    dec = dict(fs.execute("SELECT decision_key, chain, mint, decision_time, row_sha256, row_json, token_json FROM predictive_decisions "
                          "WHERE decision_key=?", (e.decision_key,)).fetchone())
    rj = json.loads(dec["row_json"])
    bd = json.loads(rj.get("score_breakdown_json") or "{}")
    fold = res_by_target[target]["folds"][row["fold"]]
    out = {"target": target, "decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time,
           "decision_time_utc": iso(e.decision_time), "decision_time_basis": "EXPORT_COMMIT", "row_sha256": dec["row_sha256"],
           "label_y": e.y, "fold": row["fold"], "fold_cutoff_utc": fold["cutoff_utc"],
           "selection_rule": "earliest out-of-sample row of T2 (then T1, T1b) by decision time then mint with every required M2 input",
           "fatal_flags": [f.get("flag") for f in json.loads(rj.get("fatal_flags_json") or "[]")],
           "rationale": {b: (bd.get(b) or {}).get("rationale") for b in ("token_lp_safety", "market_execution", "supply_ownership", "demand_order_flow")},
           "snapshot_fields": {k: json.loads(rj["snapshot_json"]).get(k) for k in ("t", "liquidity", "exit_cap_3pct", "adj_top10")},
           "token_program": json.loads(dec["token_json"] or "{}").get("token_program"),
           "prior_decision": None, "oc_values": {k: v["value"] for k, v in s["values"].items()},
           "oc_reasons": {k: v["missing_reason"] for k, v in s["values"].items() if v["value"] is None},
           "oc_available_at": {k: v["available_at"] for k, v in s["values"].items()}, "oc_snapshot_sha": s["onchain_snapshot_sha"],
           "model_inputs": {c: (None if not math.isfinite(B._num(e.x.get(c))) else e.x.get(c)) for c in spec["columns"]}, "models": {}}
    pr = fs.execute("SELECT decision_key, decision_time, row_json FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time < ? "
                    "ORDER BY decision_time DESC, id DESC LIMIT 1", (e.chain, e.mint, e.decision_time)).fetchone()
    if pr is not None:
        prj = json.loads(pr["row_json"])
        pbd = json.loads(prj.get("score_breakdown_json") or "{}")
        out["prior_decision"] = {"decision_key": pr["decision_key"], "decision_time": pr["decision_time"],
                                 "snapshot_fields": {k: json.loads(prj["snapshot_json"]).get(k) for k in ("t", "liquidity", "exit_cap_3pct", "adj_top10")},
                                 "token_lp_safety": (pbd.get("token_lp_safety") or {}).get("rationale"),
                                 "fatal_flags": [f.get("flag") for f in json.loads(prj.get("fatal_flags_json") or "[]")]}
    for m in ("B0", "B2") + O.MODEL_IDS:
        card = fold["cards"][m]
        out["models"][m] = {"card_model_sha": card["model_sha"], "training_cutoff_utc": card["training_cutoff_utc"],
                            "number": None if not math.isfinite(row[m]) else row[m], "abstain": row.get(m + "_why"), "card": card}
    rej = {}
    nxt = fs.execute("SELECT decision_key FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time > ? ORDER BY decision_time LIMIT 1",
                     (e.chain, e.mint, e.decision_time)).fetchone()
    if nxt is not None:
        s2 = O.onchain_as_of(fs, e.chain, e.mint, float(fs.execute("SELECT decision_time FROM predictive_decisions WHERE decision_key=?",
                                                                     (nxt[0],)).fetchone()[0]), decision_key=nxt[0])
        av = s2["values"]["oc_lp_risk_ord"]["available_at"] or (e.decision_time + 1)
        e_late = O.OExample(**{**e.__dict__, "avail": {**e.avail, "oc_lp_risk_ord": av}})
    else:
        e_late = O.OExample(**{**e.__dict__, "avail": {**e.avail, "oc_lp_risk_ord": e.decision_time + 300}})
    try:
        O.check_asof([e_late], ["oc_lp_risk_ord"], as_of=None, with_labels=False)
        rej["next_decision_value_used"] = "ACCEPTED"
    except F.AsOfError as ex:
        rej["next_decision_value_used"] = f"REFUSED: {str(ex)[:160]}"
    try:
        F.AsOfView(fs, e.decision_time).audit.check("decision", [{"_avail": e.decision_time + 1}], e.decision_time)
        rej["view_row_available_after_T"] = "ACCEPTED"
    except F.LeakageError as ex:
        rej["view_row_available_after_T"] = f"REFUSED: {str(ex)[:160]}"
    try:
        O._value(float("nan"), None, e.decision_time, ["x"])
        rej["non_finite_value"] = "ACCEPTED"
    except O.OnchainError as ex:
        rej["non_finite_value"] = f"REFUSED: {ex}"
    try:
        O.predict(cards_h[target][O.PRIMARY], [e])
        rej["holdout_start_card_on_this_development_decision"] = "ACCEPTED"
    except O.ModelTrainedAfterDecision as ex:
        rej["holdout_start_card_on_this_development_decision"] = f"REFUSED: {ex}"
    out["invalid_inputs"] = rej
    out["invalid_inputs_all_rejected"] = all(not v.startswith("ACCEPTED") for v in rej.values())
    lat = []
    for _ in range(20):
        t0 = time.perf_counter()
        s3 = O.onchain_as_of(fs, e.chain, e.mint, e.decision_time, decision_key=e.decision_key)
        for m in O.MODEL_IDS:
            ex2 = [O.OExample(**{**e.__dict__})]
            O.predict(fold["cards"][m], ex2)
        lat.append(time.perf_counter() - t0)
    out["onchain_snapshot_recomputed_equal"] = s3["onchain_snapshot_sha"] == s["onchain_snapshot_sha"]
    out["latency_s_median_of_20"] = round(statistics.median(lat), 4)
    return out


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--reps", type=int, default=C.ACCEPTANCE["bootstrap"]["min_replicates"])
    ap.add_argument("--dev-store", default=P7.DEV_STORE)
    ap.add_argument("--feature-store", default=P7.FEATURE_STORE)
    ap.add_argument("--npz", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    t0, c0 = time.time(), time.process_time()
    start_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    for p in (a.dev_store, a.feature_store):
        L.refuse_sealed(p)
        R.refuse_bakeoff_labels(path=p)
    shas = (a.dev_store, a.feature_store, str(LAB_DB))
    store_sha_before = {p: P7.fsha(p) for p in shas}
    dev, fs = P7.ro(a.dev_store), P7.ro(a.feature_store)
    frows, snaps, info = P7.load_inputs(dev, fs)
    all_snaps = all_snapshots(fs)
    keys = labelled_keys(dev)
    incons = {}
    for k in sorted(keys):
        d = O.v2_consistency(all_snaps[k], frows[k])
        if d:
            incons[k] = d
    if incons:
        write_json(out / "evidence" / "v2_consistency.json", {"inconsistent": incons})
        raise SystemExit(f"onchain-1 and version 2 disagree on {len(incons)} decisions: stop (checklist G6)")
    osnaps = {k: all_snaps[k] for k in keys}
    p07_oos = {}
    with open(P07 / "experiments/OOS_PREDICTIONS.csv") as f:
        for r in csv.DictReader(f):
            p07_oos[(r["target_short"], r["decision_key"])] = r
    touch = {}
    for t in L.TARGETS:
        for r in L.training_labels(dev, H, t, mode="provider"):
            if r["label"] == 1:
                touch[(t, r["decision_key"])] = r["first_touch_start"]

    metrics, mrows, ew_rows, coh_rows, oos_out, cov, nc1_rows, ledger, folds_ev = [], [], [], [], [], [], [], [], {}
    holm_in: dict[tuple, dict] = {}
    res_by_target, dev_ex_by_target, cards_h, smoke, p07_equal = {}, {}, {}, {}, {}
    npz: dict[str, np.ndarray] = {}
    art = out / "artifacts"
    for target in TARGET_ORDER:
        s = SHORT[target]
        runs = {}
        for kc in (True, False):
            dev_ex, _ = oex_at(dev, target, H, frows, snaps, info, osnaps, include_kc=kc)
            res = O.walk_forward(target, dev_ex, lambda c: oex_at(dev, target, c, frows, snaps, info, osnaps, include_kc=kc)[0])
            runs[kc] = (dev_ex, res)
        dev_ex, res = runs[True]
        res_by_target[target], dev_ex_by_target[target] = res, dev_ex
        if res.get("split_fingerprint") != P07_SPLITS[s]:
            raise SystemExit(f"{s}: split fingerprint differs from Phase 07's")
        diffs = 0
        for r in res["oos"]:
            q = p07_oos[(s, r["example"].decision_key)]
            for b in ("B0", "B2"):
                mine = "" if not math.isfinite(r[b]) else f"{r[b]:.6f}"
                diffs += mine != q[b]
        p07_equal[s] = {"oos_rows": len(res["oos"]), "b0_b2_differences_at_6_decimals": diffs, "split_fingerprint_equal": True}
        if diffs:
            raise SystemExit(f"{s}: B0 or B2 out-of-sample numbers differ from Phase 07's ({diffs})")
        folds_ev[s] = {"status": res["status"], "split_fingerprint": res.get("split_fingerprint"), "audit": res["audit"],
                       "folds": [{k: v for k, v in f.items() if k != "cards"} for f in res["folds"]],
                       "no_key_conflict_folds": [{k: v for k, v in f.items() if k != "cards"} for f in runs[False][1]["folds"]]}
        write_json(art / "folds" / f"{s}.json", {"target": target, "status": O.PROVISIONAL,
                                                 "folds": [{"fold": f["fold"], "cutoff_utc": f["cutoff_utc"],
                                                            "cards": {m: f["cards"][m] for m in O.MODEL_IDS}} for f in res["folds"]]})
        tch = {k2: v for (t2, k2), v in touch.items() if t2 == target}
        for view in VIEWS:
            rows = P7.view_rows(runs[view != "NO_KEY_CONFLICT"][1]["oos"], view)
            for m, ref in COMPARISONS:
                ev = B.evaluate(rows, m, reference=ref, reps=a.reps)
                deg = O.degenerate([r[m] for r in rows])
                metrics.append((target, view, ev, m, ref, KIND[m], deg))
                if view == "ALL":
                    holm_in.setdefault((m, ref), {})[target] = ev.get("p_one_sided")
                ledger.append({"phase": "09", "experiment_id": f"P09:{target}:{m}", "target": target, "candidate": m, "kind": KIND[m],
                               "view": f"{view} vs {ref}", "seed": 20261025, "folds": len(res["folds"]), "n_rows": ev["n_rows"],
                               "n_with_number": ev["n_with_number"], "verdict": ev.get("verdict"),
                               "split_fingerprint": res.get("split_fingerprint") if view != "NO_KEY_CONFLICT" else runs[False][1].get("split_fingerprint")})
            ledger.append({"phase": "09", "experiment_id": f"P09:{target}:B0", "target": target, "candidate": "B0", "kind": "REFERENCE_PHASE07",
                           "view": view, "seed": "", "folds": len(res["folds"]), "n_rows": len(rows),
                           "n_with_number": sum(1 for r in rows if math.isfinite(r["B0"])), "verdict": "REFERENCE",
                           "split_fingerprint": res.get("split_fingerprint")})
            ew = O.early_warning(rows, "R0_OC_VETO", touch=tch)
            ledger.append({"phase": "09", "experiment_id": f"P09:{target}:R0_OC_VETO", "target": target, "candidate": "R0_OC_VETO",
                           "kind": "VETO_ALARM_COUNTS_ONLY", "view": view, "seed": "", "folds": len(res["folds"]), "n_rows": len(rows),
                           "n_with_number": ew["scored"], "verdict": "COUNTS_ONLY", "split_fingerprint": res.get("split_fingerprint")})
            for m in ("R0_OC_VETO", "R1_OC_RULE", "M1_OC_LOGIT", "M2_OC_LOGIT_B2", "M3_OC_LOGIT_TREND", "B2"):
                e2 = O.early_warning(rows, m, touch=tch)
                ew_rows.append({"target_short": s, "view": view, "model": m,
                                "alarm_rule": "oc_structural_fatal == 1" if m == "R0_OC_VETO" else "number above the fold's B0",
                                **{k: e2[k] for k in ("scored", "hits", "misses", "false_alarms", "correct_rejections", "lead_time_h_median",
                                                      "support_note")}, "lead_times_h": ";".join(str(x) for x in e2["lead_times_h"]),
                                "status": O.PROVISIONAL})
            for nc in nc1_summary(rows, res.get("nc1_seeds", []), a.reps):
                nc1_rows.append({"target_short": s, "view": view, **nc})
                ledger.append({"phase": "09", "experiment_id": f"P09:{target}:NC1OC_seed{nc['seed']:02d}", "target": target,
                               "candidate": "NC1OC", "kind": "NEGATIVE_CONTROL", "view": view, "seed": nc["seed"], "folds": len(res["folds"]),
                               "n_rows": len(rows), "n_with_number": nc["n"], "verdict": "", "split_fingerprint": res.get("split_fingerprint")})
        for r in res["oos"]:
            e = r["example"]
            oos_out.append({"target_short": s, "fold": r["fold"], "cutoff_utc": B._iso(r["cutoff"]), "decision_key": e.decision_key,
                            "mint": e.mint, "decision_time_utc": B._iso(e.decision_time), "day": e.day, "y": e.y, "route": e.route,
                            "oc_missing": ";".join(sorted(f"{k}={v}" for k, v in e.oc_reasons.items())),
                            "R0_alarm": r["R0_alarm"], "new_mint": r["new_mint"], "key_conflict": e.key_conflict,
                            **{m: r[m] for m in ("B0", "B2") + O.MODEL_IDS}, **{m + "_why": r[m + "_why"] or "" for m in ("B0", "B2") + O.MODEL_IDS},
                            "NC1OC_mean": float(np.nanmean([r[f"NC1OC_{q}"] for q in res["nc1_seeds"]])) if any(
                                math.isfinite(r[f"NC1OC_{q}"]) for q in res["nc1_seeds"]) else float("nan"),
                            "status": O.PROVISIONAL})
        dims = {"route": lambda e: e.route, "liquidity_bucket": lambda e: e.cohort.get("liquidity_bucket"),
                "launch_age_bucket": lambda e: e.cohort.get("launch_age_bucket"), "week": lambda e: e.cohort.get("week_utc"),
                "day": lambda e: e.day, "token_program_2022": lambda e: None if not math.isfinite(e.x["oc_token2022"]) else int(e.x["oc_token2022"]),
                "lp_risk_ord": lambda e: None if not math.isfinite(e.x["oc_lp_risk_ord"]) else int(e.x["oc_lp_risk_ord"]),
                "structural_flag": lambda e: None if not math.isfinite(e.x["oc_structural_fatal"]) else int(e.x["oc_structural_fatal"])}
        for dim, fn in dims.items():
            for m in ("R0_OC_VETO", "R1_OC_RULE", "M2_OC_LOGIT_B2"):
                for row in ew_cohorts(res["oos"], m, fn, tch):
                    coh_rows.append({"target_short": s, "dimension": dim, "model": m, **row, "status": O.PROVISIONAL})
        for which, exs in (("DEVELOPMENT_AT_HOLDOUT_START", dev_ex), ("OUT_OF_SAMPLE", [r["example"] for r in res["oos"]])):
            for fname in O.OC:
                rs = Counter(e.oc_reasons.get(fname, "VALUE") for e in exs)
                cov.append({"target_short": s, "set": which, "feature": fname, "n": len(exs), "with_value": rs.get("VALUE", 0),
                            "missing": ";".join(f"{k}={v}" for k, v in sorted(rs.items()) if k != "VALUE")})
            for m in O.MODEL_IDS:
                sp = O.SPECS[m]
                cov.append({"target_short": s, "set": which, "feature": f"MODEL_ROWS:{m}", "n": len(exs),
                            "with_value": sum(1 for e in exs if O.complete(e, sp["rows"])), "missing": "OOD otherwise (AS_OF missingness)"})
        # train-only cards at the holdout start
        train = oex_at(dev, target, H, frows, snaps, info, osnaps)[0]
        cards_h[target] = {m: O.fit(m, target, train, H) for m in O.MODEL_IDS}
        smoke[s] = {}
        for m, card in cards_h[target].items():
            p = art / s / f"{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(O.dumps(card))
            back = O.loads(p.read_text())
            p1, w1 = O.predict_numbers(card, train)
            p2, w2 = O.predict_numbers(back, train)
            same = bool(np.array_equal(np.nan_to_num(p1, nan=-1.0), np.nan_to_num(p2, nan=-1.0)) and w1 == w2)
            tam = json.loads(p.read_text())
            if "logistic" in tam["body"]:
                tam["body"]["logistic"]["coef"][0] += 1e-9
            elif "cells" in tam["body"]:
                tam["body"]["b0"] += 1e-9
            else:
                tam["n_train"] += 1
            try:
                O.verify_card(tam)
                refused = False
            except B.ModelHashMismatch:
                refused = True
            fsh = P7.fsha(p)
            R.verify_artifact(p, [fsh])
            smoke[s][m] = {"file_sha256": fsh, "model_sha": card["model_sha"], "abstain": card["body"].get("abstain"),
                           "n_train": card["n_train"], "k_train": card["k_train"], "n_used": card["n_used"], "k_used": card["k_used"],
                           "roundtrip_identical": same, "tamper_refused": refused, "numbers": int(np.sum(np.isfinite(p1))), "pickle_used": False}
        ex0 = train[-1]
        c2 = cards_h[target][O.PRIMARY]
        doc = B.abstain_document(target, mint=ex0.mint, snapshot_hash=info[ex0.decision_key]["row_sha256"],
                                 decision_time_utc=B._iso(ex0.decision_time), generated_at_utc=B._iso(H),
                                 reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"], base_rate=float(np.mean([e.y for e in train])), card=c2)
        ea = C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE)
        fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4])
        mc = {k: c2[k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
        ef = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
        ds = O.decision_support(doc, json.loads(json.loads(dev.execute("SELECT row_json FROM predictive_decisions WHERE decision_key=?",
                                                                        (ex0.decision_key,)).fetchone()[0])["fatal_flags_json"] or "null"),
                                [], max_loss=0.05)
        smoke[s]["contract"] = {"abstain_errors": ea, "forecast_errors": ef, "abstain_valid": not ea, "forecast_refused": bool(ef),
                                "decision_support": {k: ds[k] for k in ("structural_veto", "veto_overrides_forecast", "size_cap")}}
        if a.npz:
            for f in res["folds"]:
                tr = oex_at(dev, target, f["cutoff"], frows, snaps, info, osnaps)[0]
                for m in O.MODEL_IDS:
                    c = f["cards"][m]
                    if "abstain" in c["body"] or "logistic" not in c["body"]:
                        continue
                    use = [e for e in tr if O.complete(e, c["body"]["spec"]["rows"])]
                    X = O.matrix(use, c["body"]["spec"]["columns"])
                    tag = f"{s}_f{f['fold']}_{m}"
                    npz[tag + "_X"], npz[tag + "_y"] = X, B.labels_of(use)
                    npz[tag + "_Z"] = K.Prep.from_dict(c["body"]["prep"]).transform(X)
                    npz[tag + "_coef"] = np.r_[c["body"]["logistic"]["intercept"], c["body"]["logistic"]["coef"]]
            for m, c in cards_h[target].items():
                if "abstain" in c["body"] or "logistic" not in c["body"]:
                    continue
                use = [e for e in train if O.complete(e, c["body"]["spec"]["rows"])]
                X = O.matrix(use, c["body"]["spec"]["columns"])
                tag = f"{s}_H_{m}"
                npz[tag + "_X"], npz[tag + "_y"] = X, B.labels_of(use)
                npz[tag + "_Z"] = K.Prep.from_dict(c["body"]["prep"]).transform(X)
                npz[tag + "_coef"] = np.r_[c["body"]["logistic"]["intercept"], c["body"]["logistic"]["coef"]]
    holm_adj = {}
    for key, per_t in holm_in.items():
        ts = list(L.TARGETS)
        adj = K.holm([per_t.get(t) if per_t.get(t) is not None else float("nan") for t in ts])
        for t, v in zip(ts, adj):
            holm_adj[(t,) + key] = v
    rules_vs = []
    for target, view, ev, m, ref, kind, deg in metrics:
        ph = holm_adj.get((target, m, ref)) if view == "ALL" else None
        if ev.get("n_with_number"):
            ev["verdict"] = B.verdict(ev, ph if ph is not None and math.isfinite(ph) else None)
        row = metric_row(target, view, ev, model=m, reference=ref, kind=kind,
                         extra={"p_holm": ph, "degenerate": deg, "split_fingerprint": folds_ev[SHORT[target]]["split_fingerprint"]})
        mrows.append(row)
        if view == "ALL" and (ref == "R1_OC_RULE" or (m == "R1_OC_RULE" and ref in ("B0", "B2"))):
            rules_vs.append({k: row[k] for k in ("target_short", "model", "reference", "n_with_number", "positives", "decision_days", "brier",
                                                  "brier_ref", "bss_vs_ref", "governing", "bss_ci_day_lo", "bss_ci_day_hi", "bss_ci_mint_lo",
                                                  "bss_ci_mint_hi", "verdict", "status")})
    for s in [SHORT[t] for t in TARGET_ORDER]:
        for view in VIEWS:
            v = [r for r in nc1_rows if r["target_short"] == s and r["view"] == view and r.get("n")]
            bss = [r["bss"] for r in v if r.get("bss") is not None and math.isfinite(r["bss"])]
            mean_bss = float(np.mean(bss)) if bss else None
            tgt = [t for t, x in SHORT.items() if x == s][0]
            mrows.append({"target": tgt, "target_short": s, "view": view, "model": "NC1OC", "reference": "B0", "kind": "NEGATIVE_CONTROL",
                          "n_with_number": v[0]["n"] if v else 0, "positives": v[0]["positives"] if v else None,
                          "decision_days": v[0]["days"] if v else None, "nc1_seeds": len(v), "nc1_mean_bss": mean_bss,
                          "verdict": B.nc1_verdict(v[0]["n"] if v else 0, v[0]["positives"] if v else 0, v[0]["days"] if v else 0, mean_bss),
                          "status": O.PROVISIONAL, "revision_check_claimed": False})
    for r in ew_rows:
        if r["view"] == "ALL" and r["model"] == "R0_OC_VETO":
            rules_vs.append({"target_short": r["target_short"], "model": "R0_OC_VETO", "reference": "alarm counts (no probability)",
                             "n_with_number": r["scored"], "positives": r["hits"] + r["misses"], "decision_days": "", "brier": "", "brier_ref": "",
                             "bss_vs_ref": "", "governing": "", "bss_ci_day_lo": "", "bss_ci_day_hi": "", "bss_ci_mint_lo": "", "bss_ci_mint_hi": "",
                             "verdict": f"hits {r['hits']}, misses {r['misses']}, false alarms {r['false_alarms']}, correct rejections {r['correct_rejections']} ({r['support_note']})",
                             "status": O.PROVISIONAL})
    exp = out / "experiments"
    write_csv(exp / "ONCHAIN_METRICS.csv", mrows)
    write_csv(exp / "RULES_VS_MODEL.csv", rules_vs)
    write_csv(exp / "EARLY_WARNING.csv", ew_rows)
    write_csv(exp / "EARLY_WARNING_COHORTS.csv", coh_rows)
    write_csv(exp / "OOS_PREDICTIONS.csv", oos_out)
    write_csv(exp / "ONCHAIN_COVERAGE.csv", cov)
    write_csv(exp / "NC1OC_SEEDS.csv", nc1_rows)
    feats = []
    for k in sorted(osnaps):
        sn = osnaps[k]
        feats.append({"decision_key": k, "mint": sn["mint"], "decision_time_utc": B._iso(sn["decision_time"]), "row_sha256": sn["row_sha256"],
                      "onchain_snapshot_sha": sn["onchain_snapshot_sha"],
                      **{c: sn["values"][c]["value"] if sn["values"][c]["value"] is not None else sn["values"][c]["missing_reason"] for c in O.OC}})
    write_csv(exp / "ONCHAIN_FEATURES_DEVELOPMENT.csv", feats)
    parse_rows = []
    by_day: dict[str, list] = {}
    for sn in all_snaps.values():
        by_day.setdefault(iso(sn["decision_time"])[:10], []).append(sn)
    for d in sorted(by_day):
        ss = by_day[d]
        rs = Counter(v["missing_reason"] for sn in ss for v in sn["values"].values() if v["value"] is None)
        parse_rows.append({"decision_day_utc": d, "decisions": len(ss), "unparseable_values": rs.get("UNPARSEABLE", 0),
                           "not_observed_by_lab_values": rs.get("NOT_OBSERVED_BY_LAB", 0), "inconsistent_time_values": rs.get("INCONSISTENT_TIME", 0),
                           "no_prior_decision_values": rs.get("NO_PRIOR_DECISION", 0),
                           "structural_flag_rows": sum(1 for sn in ss if sn["values"]["oc_structural_fatal"]["value"] == 1),
                           "distribution_flag_rows": sum(1 for sn in ss if sn["values"]["oc_distribution_fatal"]["value"] == 1),
                           "capture_delay_s_median": statistics.median([sn["values"]["oc_capture_delay_s"]["value"] for sn in ss
                                                                          if sn["values"]["oc_capture_delay_s"]["value"] is not None] or [0.0])})
    write_csv(exp / "PARSE_COVERAGE_BY_DAY.csv", parse_rows)
    with open(P08 / "experiments/SEARCH_LEDGER.csv") as f:
        prior = list(csv.DictReader(f))
    for i, when in enumerate(DEBUG_RUNS, 1):
        ledger.append({"phase": "09", "experiment_id": f"P09:debug_run_{i}", "target": "all three", "candidate": "as recorded run",
                       "kind": "DEBUG_RUN_REAL_DATA", "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                       "verdict": when, "split_fingerprint": ""})
    write_csv(exp / "SEARCH_LEDGER.csv", prior + ledger)
    reg = [r["experiment_id"] for r in csv.DictReader(open(REPO / "audits/predictive-intelligence/phase_09/experiments/EXPERIMENT_REGISTRY.csv"))]
    led = {r["experiment_id"] for r in ledger}
    reg_trap = {x for x in reg if x.split(":")[-1] in ("NC2OC", "P13OC", "P36OC", "CX09")}
    missing = sorted(set(reg) - led - reg_trap)
    ev_dir = out / "evidence"
    tr = traps(fs, dev_ex_by_target, osnaps, cards_h, all_snaps)
    tr["registry_rows_missing_from_ledger"] = missing
    write_json(ev_dir / "traps.json", tr)
    write_json(ev_dir / "folds.json", folds_ev)
    write_json(ev_dir / "serialization_smoke.json", smoke)
    write_json(ev_dir / "phase07_equality.json", p07_equal)
    write_json(ev_dir / "v2_consistency.json", {"decisions_checked": len(keys), "inconsistent": incons,
                                               "compared": ["adj_top10", "ln(1 + liquidity)", "ln(1 + exit_cap_3pct)"]})
    xc = {"authority": authority_crosscheck(fs, all_snaps), "swaps_vs_candles": swaps_vs_candles(fs), "holder_classes": holder_classes(),
          "developer_wallets": dev_wallet_cases(fs)}
    write_json(ev_dir / "crosschecks.json", xc)
    default_bt = REPO / "data" / "backtest" / "bt.sqlite"
    write_json(ev_dir / "collector_state.json", {"default_path": str(default_bt.relative_to(REPO)), "status": DA.status(default_bt),
                                                 "note": "the collector runs only on Elving's computer once deployed (RUNBOOK of feature/backtesting); "
                                                         "this cloud checkout has no collector database: no forward row exists"})
    tdir = ev_dir / "trace"
    tj = trace(fs, res_by_target, osnaps, cards_h, info)
    write_json(tdir / "FORECAST_TRACE.json", tj)
    if a.npz:
        np.savez(a.npz, **npz)
    store_sha_after = {p: P7.fsha(p) for p in shas}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    outputs = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "run_log.json")
    write_json(ev_dir / "run_log.json", {
        "start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": head,
        "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "bootstrap_reps": a.reps,
        "code_sha256": {c: P7.fsha(REPO / c) for c in CODE},
        "stores": {"before": store_sha_before, "after": store_sha_after, "unchanged": store_sha_before == store_sha_after},
        "registry_sha": C.registry_sha256(), "onchain_feature_set_sha": O.feature_set_sha(), "base_feature_set_sha": F.feature_set_sha(),
        "labels_version": L.LABELS_VERSION, "as_of_utc": B._iso(H), "status": O.PROVISIONAL, "revision_check_claimed": False,
        "solana_decisions_with_onchain_snapshot": len(all_snaps), "labelled_development_decisions": len(keys),
        "debug_runs_logged": len(DEBUG_RUNS), "outputs_sha256": {o: P7.fsha(out / o) for o in outputs}})
    print(json.dumps({"targets": {s: folds_ev[s]["status"] for s in folds_ev}, "outputs": len(outputs), "socket_events": len(SOCKET_EVENTS),
                      "stores_unchanged": store_sha_before == store_sha_after, "ledger_missing": len(missing)}))
    failed = [k for k, v in tr.items() if isinstance(v, dict) and v.get("pass") is False]
    failed += ["trace invalid inputs"] if (tj.get("invalid_inputs_all_rejected") is False) else []
    failed += ["holder classes"] if not xc["holder_classes"]["pass"] else []
    failed += ["registry rows missing from the ledger"] if missing else []
    failed += ["socket events"] if SOCKET_EVENTS else []
    failed += ["stores changed"] if store_sha_before != store_sha_after else []
    if failed:
        print(json.dumps({"FAILED": failed}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

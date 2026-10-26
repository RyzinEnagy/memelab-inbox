"""Phase 10 social and catalyst runner: socialcat-1 for every Solana decision of the store (coverage) with the narrative tables of
each decision's own export commit, the frozen walk-forward of R2, S1 to S3, G1, A2 and NC1-SC beside Phase 07's B0 and B2 on the
same folds, the ablations (social features beyond price and liquidity), the amplification alarm, cohorts, the train-only cards at
the holdout start, the traps (NC2-SC, P13-SC, P36-SC, P04-SC, CX-10), the real cross-checks (inbox catalyst reads against the
decision mints by exact address, the token row provenance), the event without post-event text, the forecast trace and the
cumulative search ledger.

Reads only: the Phase 06 development store (labels through `labels.training_labels`, decision rows), the Phase 05 store (version 2
snapshots through `features.training_view`, decision rows through `features.AsOfView`), git objects of `MAIN_REF` (the export
commit of each decision, read with `git show`, never checked out) and the tracked `inbox/` catalyst reads, all read-only. Never
opens the sealed holdout folder. No network: an audit hook refuses any socket call. Deterministic: two runs into two folders give
identical files except `evidence/run_log.json` (times) and the trace's latency field.

    python -B run_social.py OUTDIR [--reps 2000] [--dev-store PATH] [--feature-store PATH] [--npz PATH]

PROVISIONAL (PI-D-046): until Phase 06's 48 h revision re-read is folded in. If it changes a development label, rerun this
script at the Phase 10 code commit; the new outputs supersede these. (The re-read changed no label, PI-D-059.)

Repair pass 2 (PI-D-060, skeptic m6 and m4): git reads use the pinned `MAIN_REF` (the `origin/main` commit the first recorded
run read), so the CX-10 trap's newest-export counts and the export walk do not depend on where `origin/main` is today; `--npz`
also writes every fitted G1 stump design (`<tag>_Xs`, `_ys`, `_Zs`, `_ps`) for the stump oracle in
`sklearn_crosscheck_social.py`.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import resource
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
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import socialcat as SC  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402
from memelab.predictive import store as S  # noqa: E402
from memelab.predictive import technical as T8  # noqa: E402

SOCKET_EVENTS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKET_EVENTS.append(event)
        raise RuntimeError(f"Phase 10 runner makes no network call ({event})")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p07_run_baselines", REPO / "audits/predictive-intelligence/phase_07/probes/run_baselines.py")
P7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P7)

SHORT, H = P7.SHORT, P7.H
LAB_DB = REPO / "data" / "memelab.sqlite"
EXPORT_PATH = "data/state/latest.json"
CODE = ["memelab/predictive/socialcat.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
        "memelab/predictive/technical.py", "memelab/predictive/features.py", "memelab/predictive/labels.py",
        "memelab/predictive/contract.py", "memelab/social/replay_core.py", "memelab/social/alpha_core.py",
        "audits/predictive-intelligence/phase_07/probes/run_baselines.py", "audits/predictive-intelligence/phase_10/probes/run_social.py"]
VIEWS = P7.VIEWS
P07 = REPO / "audits/predictive-intelligence/phase_07"
P09 = REPO / "audits/predictive-intelligence/phase_09"
P10 = REPO / "audits/predictive-intelligence/phase_10"
P07_SPLITS = {"T1_24h": "0ab64525e04b8664a1cab51c9e24f5fa4f750681d32a5d97bfc520710e3845a4",
              "T1b_6h": "aa16e7adeae7d5bc8567de9ab85ed1f28843afe51bc0de9b52e24d587beb8a31",
              "T2_24h": "82a1c33b12cef45995eb15edd07b8e27ddcd76eafbdb8c503f5feb9501be86cd"}
TARGET_ORDER = (L.T1, L.T2, L.T1B)               # T1 (the follow-through-like target) is reported first
MAIN_REF = "e245d91cc5f56060ba8e1aa7182c846c77d1526c"   # origin/main read by the first recorded run (pinned in repair pass 2, m6)
BASE_SHA = "f99c6c7"                             # the branch base (PI-D-001): social and catalyst code must be unchanged since
# real-data runs before the recorded run (P22): appended before the recorded run, never removed
DEBUG_RUNS: list[str] = [
    "features-only probe after the pre-registration commit c3f04c8 (00:02:17Z to 00:02:26Z on 2026-10-26): socialcat-1 missing-reason "
    "counts and lab event classes over the 925 Solana decision rows of the Phase 05 store with each decision's export tables; no "
    "label read, no fit, no metric",
]
COMPARISONS = ([(m, "B0") for m in ("B2",) + SC.MODEL_IDS]
               + [(m, "B2") for m in ("R2_SC_RULE", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND", "G1_SC_STUMPS_B2")]
               + [(m, "R2_SC_RULE") for m in ("S1_SC_LOGIT", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND")]
               + [("S2_SC_LOGIT_B2", "A2_SC_B2_TC"), ("G1_SC_STUMPS_B2", "A2_SC_B2_TC")])
KIND = {"B2": "REFERENCE_PHASE07", "R2_SC_RULE": "SIMPLE_ATTENTION_RULE", "S1_SC_LOGIT": "SOCIAL_MODEL",
        "S2_SC_LOGIT_B2": "SOCIAL_MODEL_PRIMARY", "S3_SC_LOGIT_TREND": "SOCIAL_MODEL", "G1_SC_STUMPS_B2": "SOCIAL_MODEL_BOOSTED",
        "A2_SC_B2_TC": "ABLATION"}


def write_csv(path: Path, rows: list[dict]) -> None:
    P7.write_csv(path, rows)


def write_json(path: Path, obj) -> None:
    P7.write_json(path, obj)


def iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def stump_npz(npz: dict, tag: str, card: dict, use: list) -> None:
    """A fitted G1 card's training design for the stump oracle (repair pass 2, m4): raw columns, labels, the card's Prep transform
    and the card's own training probabilities."""
    X = SC.matrix(use, card["body"]["spec"]["columns"])
    Z = K.Prep.from_dict(card["body"]["prep"]).transform(X)
    npz[tag + "_Xs"], npz[tag + "_ys"], npz[tag + "_Zs"] = X, B.labels_of(use), Z
    npz[tag + "_ps"] = T8.Stumps.from_dict(card["body"]["stumps"]).predict_proba1(Z)


# ---------------------------------------------------------------- the decision's own export (narrative tables, token rows)
_EXPORTS: dict[str, dict] = {}


def export_doc(commit: str) -> dict:
    if commit not in _EXPORTS:
        raw = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{EXPORT_PATH}"], check=True, capture_output=True).stdout
        d = json.loads(raw)
        t = d.get("_tables") or {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, list)}
        _EXPORTS[commit] = {"commit": commit, "commit_time": float(git("show", "-s", "--format=%ct", commit).strip()),
                            "blob": git("rev-parse", f"{commit}:{EXPORT_PATH}").strip(), "tables": t}
    return _EXPORTS[commit]


def context_of(commit: str) -> dict:
    e = export_doc(commit)
    return {"commit": commit, "commit_time": e["commit_time"], "blob": e["blob"], "narratives": e["tables"].get("narratives") or [],
            "narrative_snapshots": e["tables"].get("narrative_snapshots") or []}


def all_snapshots(fs):
    out, prov = {}, Counter()
    for r in fs.execute("SELECT decision_key, chain, mint, decision_time, export_commit, export_blob FROM predictive_decisions "
                        "WHERE chain='solana' AND decision_key IS NOT NULL ORDER BY decision_time, id"):
        cx = context_of(r["export_commit"])
        prov["blob_equal" if cx["blob"] == r["export_blob"] else "blob_differs"] += 1
        prov["commit_time_equal" if cx["commit_time"] == float(r["decision_time"]) else "commit_time_differs"] += 1
        out[r["decision_key"]] = SC.socialcat_as_of(fs, r["chain"], r["mint"], float(r["decision_time"]), decision_key=r["decision_key"],
                                                    context=cx)
    return out, dict(prov)


def labelled_keys(dev):
    keys = {}
    for t in L.TARGETS:
        for kc in (True, False):
            for r in L.training_labels(dev, H, t, mode="provider", include_key_conflict=kc):
                keys[r["decision_key"]] = r
    return keys


def sex_at(dev, target, as_of, frows, snaps, info, ssnaps, *, include_kc=True):
    ex, rows = P7.examples_at(dev, target, as_of, frows, snaps, info, include_kc=include_kc)
    return SC.attach(ex, ssnaps), rows


# ---------------------------------------------------------------- metrics
def campaign_interval(rows, model, reference, reps):
    use = [r for r in rows if math.isfinite(r[model]) and math.isfinite(r[reference])]
    groups = [r["campaign"] for r in use]
    if len(set(groups)) < 2:
        return {"campaign_groups": len(set(groups)), "bss_ci_campaign_lo": None, "bss_ci_campaign_hi": None}
    y = np.array([r["y"] for r in use], float)
    p = np.array([r[model] for r in use], float)
    b = np.array([r[reference] for r in use], float)
    bs = K.group_bootstrap(groups, lambda idx: K.brier_skill(y[idx], p[idx], b[idx]), reps=reps, seed=20261025)
    return {"campaign_groups": len(set(groups)), "bss_ci_campaign_lo": bs["ci"][0], "bss_ci_campaign_hi": bs["ci"][1]}


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
            "campaign_groups": extra.get("campaign_groups"), "bss_ci_campaign_lo": extra.get("bss_ci_campaign_lo"),
            "bss_ci_campaign_hi": extra.get("bss_ci_campaign_hi"), "campaign_interval_governs": False,
            "cal_mean_pred": cal.get("mean_pred"), "cal_observed": cal.get("observed"), "cal_in_the_large_ok": cal.get("in_the_large_ok"),
            "cal_bins": len(cal.get("bins") or []), "cal_every_bin_ok": cal.get("every_bin_ok"), "ece": cal.get("ece"),
            "degenerate": extra.get("degenerate"), "verdict": ev.get("verdict"), "promotion": "" if model == "B2" else "MODEL_NOT_PROMOTED",
            "status": SC.PROVISIONAL, "revision_check_claimed": False, "split_fingerprint": extra.get("split_fingerprint")}


def nc1_summary(rows, seeds, reps):
    out = []
    for s in seeds:
        key = f"NC1SC_{s}"
        if not rows or not any(math.isfinite(r[key]) for r in rows):
            out.append({"seed": s, "n": 0})
            continue
        ev = B.evaluate(rows, key, reps=reps, seed=20261025 + s, boot=False)
        out.append({"seed": s, "n": ev["n_with_number"], "brier": ev.get("brier"), "brier_ref": ev.get("brier_ref"), "bss": ev.get("bss"),
                    "positives": ev.get("positives"), "days": ev.get("days")})
    return out


def alarm_cohorts(rows, model, key, touch):
    out = []
    for v in sorted({str(key(r["example"]) if key(r["example"]) is not None else "UNKNOWN") for r in rows}):
        rr = [r for r in rows if str(key(r["example"]) if key(r["example"]) is not None else "UNKNOWN") == v]
        e = SC.alarm_counts(rr, model, touch=touch)
        out.append({"value": v, **{k: e[k] for k in ("scored", "hits", "misses", "false_alarms", "correct_rejections", "lead_time_h_median",
                                                      "support_note")}})
    return out


def _int(e, c):
    v = e.x.get(c)
    return None if v is None or not math.isfinite(v) else int(v)


# ---------------------------------------------------------------- traps
def traps(fs, dev_ex_by_target, ssnaps, cards_h, all_snaps):
    out = {}
    n = val = refused_allow = refused_asof = accepted = 0
    seen = set()
    min_delay = None
    for target, exs in dev_ex_by_target.items():
        for e in exs:
            if e.decision_key in seen:
                continue
            seen.add(e.decision_key)
            n += 1
            nxt = fs.execute("SELECT decision_key FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time > ? "
                             "ORDER BY decision_time, id LIMIT 1", (e.chain, e.mint, e.decision_time)).fetchone()
            if nxt is None:
                continue
            s2 = all_snaps.get(nxt["decision_key"])
            if s2 is None or s2["values"]["sc_attention_trend_ord"]["value"] is None:
                continue
            val += 1
            fut, av = s2["values"]["sc_attention_trend_ord"]["value"], s2["values"]["sc_attention_trend_ord"]["available_at"]
            min_delay = av - e.decision_time if min_delay is None else min(min_delay, av - e.decision_time)
            e2 = SC.SExample(**{**e.__dict__, "x": {**e.x, "trap_next_decision_trend": fut}, "avail": {**e.avail, "trap_next_decision_trend": av}})
            try:
                SC.check_asof([e2], ["trap_next_decision_trend"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_allow += 1
            e3 = SC.SExample(**{**e.__dict__, "x": {**e.x, "sc_attention_trend_ord": fut}, "avail": {**e.avail, "sc_attention_trend_ord": av}})
            try:
                SC.check_asof([e3], ["sc_attention_trend_ord"], as_of=None, with_labels=False)
                accepted += 1
            except F.AsOfError:
                refused_asof += 1
    out["NC2SC"] = {"labelled_decisions": n, "with_a_later_decision_of_the_mint": val, "refused_by_allowlist": refused_allow,
                    "refused_by_validate_rows": refused_asof, "accepted": accepted, "min_trap_delay_s": min_delay,
                    "pass": accepted == 0 and refused_allow == refused_asof == val and val > 0}
    res = {}
    for target, exs in dev_ex_by_target.items():
        e = min(exs, key=lambda x: (x.decision_time, x.mint))
        for m, card in cards_h[target].items():
            try:
                SC.predict(card, [e])
                res[f"{SHORT[target]}:{m}"] = "ACCEPTED"
            except SC.ModelTrainedAfterDecision:
                res[f"{SHORT[target]}:{m}"] = "REFUSED"
    out["P13SC"] = {"results": res, "pass": all(v == "REFUSED" for v in res.values())}
    e = min(dev_ex_by_target[L.T1], key=lambda x: (x.decision_time, x.mint))
    row = dict(fs.execute("SELECT * FROM predictive_decisions WHERE decision_key=?", (e.decision_key,)).fetchone())
    mem = S.connect(":memory:")
    mem.execute("PRAGMA foreign_keys=OFF")              # the copied row's raw export read is not copied (as Phase 09)
    rj = json.loads(row["row_json"])
    sn = json.loads(rj["snapshot_json"])
    sn["t"] = float(row["decision_time"]) + 60.0
    rj["snapshot_json"] = json.dumps(sn)
    cols = [c for c in row if c != "id"]
    row2 = dict(row, row_json=json.dumps(rj))
    mem.execute(f"INSERT INTO predictive_decisions ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row2[c] for c in cols])
    s = SC.socialcat_as_of(mem, row["chain"], row["mint"], float(row["decision_time"]), decision_key=row["decision_key"],
                           context=context_of(row["export_commit"]))
    reasons = Counter(v["missing_reason"] for v in s["values"].values())
    out["P36SC"] = {"decision_key": e.decision_key, "values_with_a_number": sum(1 for v in s["values"].values() if v["value"] is not None),
                    "reasons": dict(reasons), "pass": reasons.get("INCONSISTENT_TIME") == len(SC.SC)}
    # P04-SC: the narrative tables of the next export commit handed to every labelled decision
    order = [ln.split() for ln in git("rev-list", "--reverse", "--first-parent", "--timestamp", MAIN_REF, "--", EXPORT_PATH).splitlines() if ln.strip()]
    nxt_of = {c: order[i + 1][1] for i, (t, c) in enumerate(order[:-1])}
    tried = refused = acc = 0
    for k, sn in sorted(ssnaps.items()):
        d = dict(fs.execute("SELECT decision_key, chain, mint, decision_time, export_commit FROM predictive_decisions WHERE decision_key=?", (k,)).fetchone())
        nc = nxt_of.get(d["export_commit"])
        if nc is None:
            continue
        tried += 1
        try:
            SC.socialcat_as_of(fs, d["chain"], d["mint"], float(d["decision_time"]), decision_key=k, context=context_of(nc))
            acc += 1
        except SC.ContextRefused:
            refused += 1
    out["P04SC"] = {"labelled_decisions_tried": tried, "refused": refused, "accepted": acc, "pass": acc == 0 and tried > 0}
    return out


def cx10(fs, all_snaps):
    """CX-10 on the real history: the token row stored with each decision equals the token row of its own export (provenance), and
    the newest export's token row would carry later narrative tags and channels."""
    newest = export_doc(git("rev-parse", MAIN_REF).strip())
    newest_tok = {t["mint"]: t for t in newest["tables"].get("tokens") or []}
    prov_equal = prov_diff = 0
    later = Counter()
    keys = []
    for r in fs.execute("SELECT decision_key, mint, export_commit, token_json FROM predictive_decisions WHERE chain='solana' ORDER BY decision_time, id"):
        tok = json.loads(r["token_json"]) if r["token_json"] else None
        own = next((t for t in export_doc(r["export_commit"])["tables"].get("tokens") or [] if t["mint"] == r["mint"]), None)
        if (own is None and tok is None) or (own is not None and tok is not None and S.canon(own) == S.canon(tok)):
            prov_equal += 1
        else:
            prov_diff += 1
        nt = newest_tok.get(r["mint"])
        if tok is None or nt is None:
            continue
        a, b = SC.channel_values(tok), SC.channel_values(nt)
        if a["sc_narrative_tagged"][0] == 0.0 and b["sc_narrative_tagged"][0] == 1.0:
            later["narrative_tag_only_in_newest"] += 1
            keys.append(r["decision_key"])
        for f in ("website", "twitter", "telegram"):
            if not SC._set(tok.get(f)) and SC._set(nt.get(f)):
                later[f"{f}_only_in_newest"] += 1
        if a["sc_channels_n"][0] != b["sc_channels_n"][0]:
            later["sc_channels_n_differs"] += 1
    return {"newest_export_commit": newest["commit"], "decisions": prov_equal + prov_diff, "token_row_equals_own_export": prov_equal,
            "token_row_differs_from_own_export": prov_diff, "later_differences": dict(later),
            "pass": prov_diff == 0 and later.get("narrative_tag_only_in_newest", 0) > 0}


# ---------------------------------------------------------------- real cross-checks
def inbox_catalyst(fs):
    dec_first = {r[0]: float(r[1]) for r in fs.execute("SELECT mint, MIN(decision_time) FROM predictive_decisions GROUP BY mint")}
    sol = {r[0] for r in fs.execute("SELECT DISTINCT mint FROM predictive_decisions WHERE chain='solana'")}
    out = []
    for f in sorted((REPO / "inbox").glob("cat*.json")):
        rel = str(f.relative_to(REPO))
        first = git("log", "--format=%H %ct", "--diff-filter=A", MAIN_REF, "--", rel).split()
        committed = float(first[1]) if len(first) >= 2 else None
        d = json.loads(f.read_text())
        keys = {k: v for k, v in d.items() if not k.startswith("_")} if isinstance(d, dict) else {}
        for k, v in sorted(keys.items()):
            s = json.dumps(v)
            hits = sorted(m for m in sol if m in s)
            if not hits:
                continue
            kind = ("TICKER_SEARCH_RESULTS_NOT_IDENTITY" if k.startswith(("jup_tok:", "ds_search:")) else
                    "EXCHANGE_ASSET_LIST_LISTING_STATE" if k.startswith("cat:exch:") else
                    "PAID_BOOST_LIST" if "boosts" in k else "OTHER_LIST")
            out.append({"file": rel, "key": k, "read_at": d.get("_at"), "first_committed_utc": iso(committed) if committed else None,
                        "decision_mints_named_by_exact_address": len(hits), "kind": kind,
                        "mints_whose_first_decision_is_after_the_commit": sum(1 for m in hits if committed and dec_first.get(m, 0) > committed)})
    return out


def boost_vs_paid(fs, all_snaps):
    d = json.loads((REPO / "inbox/cat01.json").read_text())
    s = json.dumps(d.get("cat:mkt:dexscreener:boosts"))
    out = []
    for k, sn in all_snaps.items():
        if sn["mint"] in s:
            out.append({"mint": sn["mint"], "decision_time_utc": iso(sn["decision_time"]),
                        "sc_attention_paid": sn["values"]["sc_attention_paid"]["value"],
                        "sc_attention_suspect": sn["values"]["sc_attention_suspect"]["value"]})
    return sorted(out, key=lambda r: r["decision_time_utc"])


def narrative_coverage(all_snaps):
    by = {}
    for sn in all_snaps.values():
        d = iso(sn["decision_time"])[:10]
        r = by.setdefault(d, Counter())
        r["decisions"] += 1
        r["tagged"] += sn["values"]["sc_narrative_tagged"]["value"] == 1.0
        r["narrative_snapshot_found"] += sn["values"]["sc_narrative_snapshot_age_h"]["value"] is not None
        r["narrative_lifecycle_known"] += sn["values"]["sc_narrative_lifecycle_ord"]["value"] is not None
        for c in sn["lab_event_classes"]:
            r[c] += 1
        r["attention_trend_known"] += sn["values"]["sc_attention_trend_ord"]["value"] is not None
        r["attention_suspect"] += sn["values"]["sc_attention_suspect"]["value"] == 1.0
    return [{"decision_day_utc": d, **{k: int(v) for k, v in sorted(c.items())}} for d, c in sorted(by.items())]


# ---------------------------------------------------------------- forecast trace and the event without post-event text
def trace(fs, res_by_target, ssnaps, cards_h):
    pick = None
    spec = SC.SPECS[SC.PRIMARY]
    for target in TARGET_ORDER:
        rows = sorted([r for r in res_by_target[target]["oos"] if SC.complete(r["example"], spec["rows"])],
                      key=lambda r: (r["example"].decision_time, r["example"].mint))
        if rows:
            pick = (target, rows[0])
            break
    if pick is None:
        return {"status": "NO_OOS_ROW_WITH_EVERY_S2_INPUT"}
    target, row = pick
    e = row["example"]
    s = ssnaps[e.decision_key]
    dec = dict(fs.execute("SELECT decision_key, chain, mint, decision_time, row_sha256, row_json, token_json, export_commit, export_blob "
                          "FROM predictive_decisions WHERE decision_key=?", (e.decision_key,)).fetchone())
    rj = json.loads(dec["row_json"])
    bd = json.loads(rj.get("score_breakdown_json") or "{}")
    fold = res_by_target[target]["folds"][row["fold"]]
    tok = json.loads(dec["token_json"] or "{}")
    out = {"target": target, "decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time,
           "decision_time_utc": iso(e.decision_time), "decision_time_basis": "EXPORT_COMMIT", "row_sha256": dec["row_sha256"],
           "export_commit": dec["export_commit"], "export_blob": dec["export_blob"], "label_y": e.y, "fold": row["fold"],
           "fold_cutoff_utc": fold["cutoff_utc"],
           "selection_rule": "earliest out-of-sample row of T1 (then T2, T1b) by decision time then mint with every required S2 input",
           "rationale": {b: (bd.get(b) or {}).get("rationale") for b in ("attention_narrative", "demand_order_flow", "lifecycle_relative_strength")},
           "snapshot_fields": {k: json.loads(rj["snapshot_json"]).get(k) for k in ("t", "attention", "lifecycle")},
           "token_row": {k: tok.get(k) for k in ("website", "twitter", "telegram", "narrative_id")},
           "prior_decision": None, "sc_values": {k: v["value"] for k, v in s["values"].items()},
           "sc_reasons": {k: v["missing_reason"] for k, v in s["values"].items() if v["value"] is None},
           "sc_available_at": {k: v["available_at"] for k, v in s["values"].items()}, "sc_snapshot_sha": s["socialcat_snapshot_sha"],
           "catalyst_state": s["catalyst_state"], "social_state": s["social_state"], "lab_event_classes": s["lab_event_classes"],
           "model_inputs": {c: (None if not math.isfinite(B._num(e.x.get(c))) else e.x.get(c)) for c in spec["columns"]}, "models": {}}
    pr = fs.execute("SELECT decision_key, decision_time, row_json FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time < ? "
                    "ORDER BY decision_time DESC, id DESC LIMIT 1", (e.chain, e.mint, e.decision_time)).fetchone()
    if pr is not None:
        prj = json.loads(pr["row_json"])
        pbd = json.loads(prj.get("score_breakdown_json") or "{}")
        out["prior_decision"] = {"decision_key": pr["decision_key"], "decision_time": pr["decision_time"],
                                 "snapshot_fields": {k: json.loads(prj["snapshot_json"]).get(k) for k in ("t", "attention", "lifecycle")},
                                 "attention_narrative": (pbd.get("attention_narrative") or {}).get("rationale")}
    for m in ("B0", "B2") + SC.MODEL_IDS:
        card = fold["cards"][m]
        out["models"][m] = {"card_model_sha": card["model_sha"], "training_cutoff_utc": card["training_cutoff_utc"],
                            "number": None if not math.isfinite(row[m]) else row[m], "abstain": row.get(m + "_why"), "card": card}
    # the event without post-event text: truncated store and own export equal the full computation; the next export is refused
    cx = context_of(dec["export_commit"])
    trunc = F.truncated_copy(fs, e.decision_time)
    st = SC.socialcat_as_of(trunc, e.chain, e.mint, e.decision_time, decision_key=e.decision_key, context=cx)
    order = [ln.split() for ln in git("rev-list", "--reverse", "--first-parent", "--timestamp", MAIN_REF, "--", EXPORT_PATH).splitlines() if ln.strip()]
    idx = [c for t, c in order].index(dec["export_commit"])
    nxt = order[idx + 1][1] if idx + 1 < len(order) else None
    try:
        SC.socialcat_as_of(fs, e.chain, e.mint, e.decision_time, decision_key=e.decision_key, context=context_of(nxt))
        nxt_res = "ACCEPTED"
    except SC.ContextRefused as ex:
        nxt_res = f"REFUSED: {str(ex)[:160]}"
    later_rows = fs.execute("SELECT COUNT(*) FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time > ?",
                            (e.chain, e.mint, e.decision_time)).fetchone()[0]
    out["event_without_post_event_text"] = {"truncated_store_snapshot_equal": st["socialcat_snapshot_sha"] == s["socialcat_snapshot_sha"],
                                            "next_export_commit": nxt, "next_export_context": nxt_res,
                                            "later_decisions_of_this_mint_in_the_store": later_rows,
                                            "pass": st["socialcat_snapshot_sha"] == s["socialcat_snapshot_sha"] and nxt_res.startswith("REFUSED")}
    rej = {}
    nx = fs.execute("SELECT decision_key, decision_time FROM predictive_decisions WHERE chain=? AND mint=? AND decision_time > ? ORDER BY decision_time LIMIT 1",
                    (e.chain, e.mint, e.decision_time)).fetchone()
    av = float(nx["decision_time"]) if nx is not None else e.decision_time + 300
    e_late = SC.SExample(**{**e.__dict__, "avail": {**e.avail, "sc_attention_trend_ord": av}})
    try:
        SC.check_asof([e_late], ["sc_attention_trend_ord"], as_of=None, with_labels=False)
        rej["next_decision_value_used"] = "ACCEPTED"
    except F.AsOfError as ex:
        rej["next_decision_value_used"] = f"REFUSED: {str(ex)[:160]}"
    try:
        F.AsOfView(fs, e.decision_time).audit.check("decision", [{"_avail": e.decision_time + 1}], e.decision_time)
        rej["view_row_available_after_T"] = "ACCEPTED"
    except F.LeakageError as ex:
        rej["view_row_available_after_T"] = f"REFUSED: {str(ex)[:160]}"
    try:
        SC._value(float("nan"), None, e.decision_time, ["x"])
        rej["non_finite_value"] = "ACCEPTED"
    except SC.SocialCatError as ex:
        rej["non_finite_value"] = f"REFUSED: {ex}"
    try:
        SC.predict(cards_h[target][SC.PRIMARY], [e])
        rej["holdout_start_card_on_this_development_decision"] = "ACCEPTED"
    except SC.ModelTrainedAfterDecision as ex:
        rej["holdout_start_card_on_this_development_decision"] = f"REFUSED: {ex}"
    rej["next_export_narrative_tables"] = nxt_res
    out["invalid_inputs"] = rej
    out["invalid_inputs_all_rejected"] = all(not v.startswith("ACCEPTED") for v in rej.values())
    lat = []
    for _ in range(20):
        t0 = time.perf_counter()
        s3 = SC.socialcat_as_of(fs, e.chain, e.mint, e.decision_time, decision_key=e.decision_key, context=cx)
        for m in SC.MODEL_IDS:
            SC.predict(fold["cards"][m], [SC.SExample(**{**e.__dict__})])
        lat.append(time.perf_counter() - t0)
    out["sc_snapshot_recomputed_equal"] = s3["socialcat_snapshot_sha"] == s["socialcat_snapshot_sha"]
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
    all_snaps, provenance = all_snapshots(fs)
    if provenance.get("blob_differs") or provenance.get("commit_time_differs"):
        raise SystemExit(f"export context provenance failed: {provenance}")
    keys = labelled_keys(dev)
    ssnaps = {k: all_snaps[k] for k in keys}
    p07_oos = {}
    with open(P07 / "experiments/OOS_PREDICTIONS.csv") as f:
        for r in csv.DictReader(f):
            p07_oos[(r["target_short"], r["decision_key"])] = r
    touch = {}
    for t in L.TARGETS:
        for r in L.training_labels(dev, H, t, mode="provider"):
            if r["label"] == 1:
                touch[(t, r["decision_key"])] = r["first_touch_start"]

    metrics, mrows, al_rows, coh_rows, oos_out, cov, nc1_rows, ledger, folds_ev = [], [], [], [], [], [], [], [], {}
    holm_in: dict[tuple, dict] = {}
    res_by_target, dev_ex_by_target, cards_h, smoke, p07_equal = {}, {}, {}, {}, {}
    npz: dict[str, np.ndarray] = {}
    art = out / "artifacts"
    for target in TARGET_ORDER:
        s = SHORT[target]
        runs = {}
        for kc in (True, False):
            dev_ex, _ = sex_at(dev, target, H, frows, snaps, info, ssnaps, include_kc=kc)
            res = SC.walk_forward(target, dev_ex, lambda c: sex_at(dev, target, c, frows, snaps, info, ssnaps, include_kc=kc)[0])
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
        write_json(art / "folds" / f"{s}.json", {"target": target, "status": SC.PROVISIONAL,
                                                 "folds": [{"fold": f["fold"], "cutoff_utc": f["cutoff_utc"],
                                                            "cards": {m: f["cards"][m] for m in SC.MODEL_IDS}} for f in res["folds"]]})
        tch = {k2: v for (t2, k2), v in touch.items() if t2 == target}
        for view in VIEWS:
            rows = P7.view_rows(runs[view != "NO_KEY_CONFLICT"][1]["oos"], view)
            for m, ref in COMPARISONS:
                ev = B.evaluate(rows, m, reference=ref, reps=a.reps)
                deg = SC.degenerate([r[m] for r in rows])
                camp = campaign_interval(rows, m, ref, a.reps) if view == "ALL" else {}
                metrics.append((target, view, ev, m, ref, KIND[m], deg, camp))
                if view == "ALL":
                    holm_in.setdefault((m, ref), {})[target] = ev.get("p_one_sided")
                ledger.append({"phase": "10", "experiment_id": f"P10:{target}:{m}", "target": target, "candidate": m, "kind": KIND[m],
                               "view": f"{view} vs {ref}", "seed": 20261025, "folds": len(res["folds"]), "n_rows": ev["n_rows"],
                               "n_with_number": ev["n_with_number"], "verdict": ev.get("verdict"),
                               "split_fingerprint": res.get("split_fingerprint") if view != "NO_KEY_CONFLICT" else runs[False][1].get("split_fingerprint")})
            ledger.append({"phase": "10", "experiment_id": f"P10:{target}:B0", "target": target, "candidate": "B0", "kind": "REFERENCE_PHASE07",
                           "view": view, "seed": "", "folds": len(res["folds"]), "n_rows": len(rows),
                           "n_with_number": sum(1 for r in rows if math.isfinite(r["B0"])), "verdict": "REFERENCE",
                           "split_fingerprint": res.get("split_fingerprint")})
            al = SC.alarm_counts(rows, SC.ALARM, touch=tch)
            ledger.append({"phase": "10", "experiment_id": f"P10:{target}:{SC.ALARM}", "target": target, "candidate": SC.ALARM,
                           "kind": "AMPLIFICATION_ALARM_COUNTS_ONLY", "view": view, "seed": "", "folds": len(res["folds"]), "n_rows": len(rows),
                           "n_with_number": al["scored"], "verdict": "COUNTS_ONLY", "split_fingerprint": res.get("split_fingerprint")})
            for m in (SC.ALARM, "R2_SC_RULE", "S1_SC_LOGIT", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND", "G1_SC_STUMPS_B2", "B2"):
                e2 = SC.alarm_counts(rows, m, touch=tch)
                al_rows.append({"target_short": s, "view": view, "model": m,
                                "alarm_rule": "sc_attention_suspect == 1" if m == SC.ALARM else "number above the fold's B0",
                                **{k: e2[k] for k in ("scored", "hits", "misses", "false_alarms", "correct_rejections", "lead_time_h_median",
                                                      "support_note")}, "lead_times_h": ";".join(str(x) for x in e2["lead_times_h"]),
                                "status": SC.PROVISIONAL})
            ledger.append({"phase": "10", "experiment_id": f"P10:{target}:NC1SC", "target": target, "candidate": "NC1SC",
                           "kind": "NEGATIVE_CONTROL", "view": view, "seed": "0..19 (one row per seed below)", "folds": len(res["folds"]),
                           "n_rows": len(rows), "n_with_number": "", "verdict": "see NC1SC rows of SOCIAL_METRICS.csv",
                           "split_fingerprint": res.get("split_fingerprint")})
            for nc in nc1_summary(rows, res.get("nc1_seeds", []), a.reps):
                nc1_rows.append({"target_short": s, "view": view, **nc})
                ledger.append({"phase": "10", "experiment_id": f"P10:{target}:NC1SC_seed{nc['seed']:02d}", "target": target,
                               "candidate": "NC1SC", "kind": "NEGATIVE_CONTROL", "view": view, "seed": nc["seed"], "folds": len(res["folds"]),
                               "n_rows": len(rows), "n_with_number": nc["n"], "verdict": "", "split_fingerprint": res.get("split_fingerprint")})
        for r in res["oos"]:
            e = r["example"]
            oos_out.append({"target_short": s, "fold": r["fold"], "cutoff_utc": B._iso(r["cutoff"]), "decision_key": e.decision_key,
                            "mint": e.mint, "decision_time_utc": B._iso(e.decision_time), "day": e.day, "y": e.y, "route": e.route,
                            "campaign": r["campaign"], "sc_missing": ";".join(sorted(f"{k}={v}" for k, v in e.sc_reasons.items())),
                            "R3_alarm": r["R3_alarm"], "new_mint": r["new_mint"], "key_conflict": e.key_conflict,
                            **{m: r[m] for m in ("B0", "B2") + SC.MODEL_IDS}, **{m + "_why": r[m + "_why"] or "" for m in ("B0", "B2") + SC.MODEL_IDS},
                            "NC1SC_mean": float(np.nanmean([r[f"NC1SC_{q}"] for q in res["nc1_seeds"]])) if any(
                                math.isfinite(r[f"NC1SC_{q}"]) for q in res["nc1_seeds"]) else float("nan"),
                            "status": SC.PROVISIONAL})
        dims = {"route": lambda e: e.route, "attention_trend": lambda e: _int(e, "sc_attention_trend_ord"),
                "attention_suspect": lambda e: _int(e, "sc_attention_suspect"), "lifecycle_late": lambda e: _int(e, "sc_lifecycle_late"),
                "narrative_tagged": lambda e: _int(e, "sc_narrative_tagged"), "week": lambda e: e.cohort.get("week_utc"), "day": lambda e: e.day}
        for dim, fn in dims.items():
            for m in (SC.ALARM, "R2_SC_RULE", "S2_SC_LOGIT_B2"):
                for row in alarm_cohorts(res["oos"], m, fn, tch):
                    coh_rows.append({"target_short": s, "dimension": dim, "model": m, **row, "status": SC.PROVISIONAL})
        for which, exs in (("DEVELOPMENT_AT_HOLDOUT_START", dev_ex), ("OUT_OF_SAMPLE", [r["example"] for r in res["oos"]])):
            for fname in SC.SC:
                rs = Counter(e.sc_reasons.get(fname, "VALUE") for e in exs)
                cov.append({"target_short": s, "set": which, "feature": fname, "n": len(exs), "with_value": rs.get("VALUE", 0),
                            "missing": ";".join(f"{k}={v}" for k, v in sorted(rs.items()) if k != "VALUE")})
            for m in SC.MODEL_IDS:
                sp = SC.SPECS[m]
                cov.append({"target_short": s, "set": which, "feature": f"MODEL_ROWS:{m}", "n": len(exs),
                            "with_value": sum(1 for e in exs if SC.complete(e, sp["rows"])), "missing": "OOD otherwise (AS_OF missingness)"})
        train = sex_at(dev, target, H, frows, snaps, info, ssnaps)[0]
        cards_h[target] = {m: SC.fit(m, target, train, H) for m in SC.MODEL_IDS}
        smoke[s] = {}
        for m, card in cards_h[target].items():
            p = art / s / f"{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(SC.dumps(card))
            back = SC.loads(p.read_text())
            p1, w1 = SC.predict_numbers(card, train)
            p2, w2 = SC.predict_numbers(back, train)
            same = bool(np.array_equal(np.nan_to_num(p1, nan=-1.0), np.nan_to_num(p2, nan=-1.0)) and w1 == w2)
            tam = json.loads(p.read_text())
            if "logistic" in tam["body"]:
                tam["body"]["logistic"]["coef"][0] += 1e-9
            elif "stumps" in tam["body"]:
                tam["body"]["stumps"]["init"] += 1e-9
            elif "cells" in tam["body"]:
                tam["body"]["b0"] += 1e-9
            else:
                tam["n_train"] += 1
            try:
                SC.verify_card(tam)
                refused = False
            except B.ModelHashMismatch:
                refused = True
            fsh = P7.fsha(p)
            R.verify_artifact(p, [fsh])
            smoke[s][m] = {"file_sha256": fsh, "model_sha": card["model_sha"], "abstain": card["body"].get("abstain"),
                           "n_train": card["n_train"], "k_train": card["k_train"], "n_used": card["n_used"], "k_used": card["k_used"],
                           "roundtrip_identical": same, "tamper_refused": refused, "numbers": int(np.sum(np.isfinite(p1))), "pickle_used": False}
        ex0 = train[-1]
        c2 = cards_h[target][SC.PRIMARY]
        doc = B.abstain_document(target, mint=ex0.mint, snapshot_hash=info[ex0.decision_key]["row_sha256"],
                                 decision_time_utc=B._iso(ex0.decision_time), generated_at_utc=B._iso(H),
                                 reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"], base_rate=float(np.mean([e.y for e in train])), card=c2)
        ea = C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE)
        fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4])
        mc = {k: c2[k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
        ef = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
        smoke[s]["contract"] = {"abstain_errors": ea, "forecast_errors": ef, "abstain_valid": not ea, "forecast_refused": bool(ef),
                                "catalyst_state": ssnaps[ex0.decision_key]["catalyst_state"], "catalyst_probability": None}
        if a.npz:
            for f in res["folds"]:
                tr = sex_at(dev, target, f["cutoff"], frows, snaps, info, ssnaps)[0]
                for m in SC.MODEL_IDS:
                    c = f["cards"][m]
                    if "abstain" not in c["body"] and "stumps" in c["body"]:
                        stump_npz(npz, f"{s}_f{f['fold']}_{m}", c, [e for e in tr if SC.complete(e, c["body"]["spec"]["rows"])])
                    if "abstain" in c["body"] or "logistic" not in c["body"]:
                        continue
                    use = [e for e in tr if SC.complete(e, c["body"]["spec"]["rows"])]
                    X = SC.matrix(use, c["body"]["spec"]["columns"])
                    tag = f"{s}_f{f['fold']}_{m}"
                    npz[tag + "_X"], npz[tag + "_y"] = X, B.labels_of(use)
                    npz[tag + "_Z"] = K.Prep.from_dict(c["body"]["prep"]).transform(X)
                    npz[tag + "_coef"] = np.r_[c["body"]["logistic"]["intercept"], c["body"]["logistic"]["coef"]]
            for m, c in cards_h[target].items():
                if "abstain" not in c["body"] and "stumps" in c["body"]:
                    stump_npz(npz, f"{s}_H_{m}", c, [e for e in train if SC.complete(e, c["body"]["spec"]["rows"])])
                if "abstain" in c["body"] or "logistic" not in c["body"]:
                    continue
                use = [e for e in train if SC.complete(e, c["body"]["spec"]["rows"])]
                X = SC.matrix(use, c["body"]["spec"]["columns"])
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
    ablation = []
    for target, view, ev, m, ref, kind, deg, camp in metrics:
        ph = holm_adj.get((target, m, ref)) if view == "ALL" else None
        if ev.get("n_with_number"):
            ev["verdict"] = B.verdict(ev, ph if ph is not None and math.isfinite(ph) else None)
        row = metric_row(target, view, ev, model=m, reference=ref, kind=kind,
                         extra={"p_holm": ph, "degenerate": deg, "split_fingerprint": folds_ev[SHORT[target]]["split_fingerprint"], **camp})
        mrows.append(row)
        if view == "ALL" and (ref in ("A2_SC_B2_TC", "B2") and m != "B2"):
            ablation.append({**{k: row[k] for k in ("target_short", "model", "reference", "n_with_number", "positives", "decision_days", "brier",
                                                     "brier_ref", "bss_vs_ref", "governing", "bss_ci_day_lo", "bss_ci_day_hi", "bss_ci_mint_lo",
                                                     "bss_ci_mint_hi", "campaign_groups", "bss_ci_campaign_lo", "bss_ci_campaign_hi", "verdict",
                                                     "status")},
                             "question": ("social columns beyond B2 on the same rows" if ref == "A2_SC_B2_TC" else "model against Phase 07 B2"),
                             "incremental_value_claimed": False})
    for s in [SHORT[t] for t in TARGET_ORDER]:
        for view in VIEWS:
            v = [r for r in nc1_rows if r["target_short"] == s and r["view"] == view and r.get("n")]
            bss = [r["bss"] for r in v if r.get("bss") is not None and math.isfinite(r["bss"])]
            mean_bss = float(np.mean(bss)) if bss else None
            tgt = [t for t, x in SHORT.items() if x == s][0]
            mrows.append({"target": tgt, "target_short": s, "view": view, "model": "NC1SC", "reference": "B0", "kind": "NEGATIVE_CONTROL",
                          "n_with_number": v[0]["n"] if v else 0, "positives": v[0]["positives"] if v else None,
                          "decision_days": v[0]["days"] if v else None, "nc1_seeds": len(v), "nc1_mean_bss": mean_bss,
                          "verdict": B.nc1_verdict(v[0]["n"] if v else 0, v[0]["positives"] if v else 0, v[0]["days"] if v else 0, mean_bss),
                          "status": SC.PROVISIONAL, "revision_check_claimed": False})
    exp = out / "experiments"
    write_csv(exp / "SOCIAL_METRICS.csv", mrows)
    write_csv(exp / "ABLATION.csv", ablation)
    write_csv(exp / "AMPLIFICATION_ALARM.csv", al_rows)
    write_csv(exp / "ALARM_COHORTS.csv", coh_rows)
    write_csv(exp / "OOS_PREDICTIONS.csv", oos_out)
    write_csv(exp / "SOCIAL_COVERAGE.csv", cov)
    write_csv(exp / "NC1SC_SEEDS.csv", nc1_rows)
    feats = []
    for k in sorted(ssnaps):
        sn = ssnaps[k]
        feats.append({"decision_key": k, "mint": sn["mint"], "decision_time_utc": B._iso(sn["decision_time"]), "row_sha256": sn["row_sha256"],
                      "export_commit": sn["export_commit"], "socialcat_snapshot_sha": sn["socialcat_snapshot_sha"],
                      "catalyst_state": sn["catalyst_state"], "social_state": sn["social_state"], "lab_event_classes": ";".join(sn["lab_event_classes"]),
                      **{c: sn["values"][c]["value"] if sn["values"][c]["value"] is not None else sn["values"][c]["missing_reason"] for c in SC.SC}})
    write_csv(exp / "SOCIAL_FEATURES_DEVELOPMENT.csv", feats)
    write_csv(exp / "NARRATIVE_COVERAGE_BY_DAY.csv", narrative_coverage(all_snaps))
    with open(P09 / "experiments/SEARCH_LEDGER.csv") as f:
        prior = list(csv.DictReader(f))
    for i, when in enumerate(DEBUG_RUNS, 1):
        ledger.append({"phase": "10", "experiment_id": f"P10:debug_run_{i}", "target": "all three", "candidate": "features only",
                       "kind": "DEBUG_RUN_REAL_DATA", "view": "", "seed": "", "folds": "", "n_rows": "", "n_with_number": "",
                       "verdict": when, "split_fingerprint": ""})
    write_csv(exp / "SEARCH_LEDGER.csv", prior + ledger)
    reg = [r["experiment_id"] for r in csv.DictReader(open(P10 / "experiments/EXPERIMENT_REGISTRY.csv"))]
    led = {r["experiment_id"] for r in ledger}
    reg_trap = {x for x in reg if x.split(":")[-1] in ("NC2SC", "P13SC", "P36SC", "P04SC", "CX10")}
    missing = sorted(set(reg) - led - reg_trap)
    ev_dir = out / "evidence"
    tr = traps(fs, dev_ex_by_target, ssnaps, cards_h, all_snaps)
    tr["CX10"] = cx10(fs, all_snaps)
    tr["registry_rows_missing_from_ledger"] = missing
    write_json(ev_dir / "traps.json", tr)
    write_json(ev_dir / "folds.json", folds_ev)
    write_json(ev_dir / "serialization_smoke.json", smoke)
    write_json(ev_dir / "phase07_equality.json", p07_equal)
    unchanged = git("diff", "--stat", BASE_SHA, "HEAD", "--", "memelab/social", "memelab/catalyst", "memelab/chains", "memelab/modules").strip()
    importers = [str(p.relative_to(REPO)) for p in (REPO / "memelab").rglob("*.py") if p.name != "socialcat.py" and "socialcat" in p.read_text()]
    xc = {"export_context_provenance": provenance, "inbox_catalyst_reads": inbox_catalyst(fs), "dexscreener_boosts_vs_lab_paid_flag": boost_vs_paid(fs, all_snaps),
          "social_and_catalyst_code_changed_since_base": unchanged or "none", "modules_importing_socialcat": importers,
          "real_social_rows": 0, "real_catalyst_rows": 0,
          "lab_event_classes_all_decisions": dict(Counter(c for sn in all_snaps.values() for c in sn["lab_event_classes"])),
          "catalyst_state_all_decisions": dict(Counter(sn["catalyst_state"] for sn in all_snaps.values())),
          "social_state_all_decisions": dict(Counter(sn["social_state"] for sn in all_snaps.values()))}
    write_json(ev_dir / "crosschecks.json", xc)
    tdir = ev_dir / "trace"
    tj = trace(fs, res_by_target, ssnaps, cards_h)
    write_json(tdir / "FORECAST_TRACE.json", tj)
    if a.npz:
        np.savez(a.npz, **npz)
    store_sha_after = {p: P7.fsha(p) for p in shas}
    head = git("rev-parse", "HEAD").strip()
    outputs = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name != "run_log.json")
    write_json(ev_dir / "run_log.json", {
        "start_utc": start_utc, "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": head,
        "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "socket_events": SOCKET_EVENTS, "vendor_calls": 0, "firecrawl_credits": 0, "llm_calls": 0, "bootstrap_reps": a.reps,
        "code_sha256": {c: P7.fsha(REPO / c) for c in CODE},
        "stores": {"before": store_sha_before, "after": store_sha_after, "unchanged": store_sha_before == store_sha_after},
        "registry_sha": C.registry_sha256(), "socialcat_feature_set_sha": SC.feature_set_sha(), "base_feature_set_sha": F.feature_set_sha(),
        "labels_version": L.LABELS_VERSION, "as_of_utc": B._iso(H), "status": SC.PROVISIONAL, "revision_check_claimed": False,
        "solana_decisions_with_socialcat_snapshot": len(all_snaps), "labelled_development_decisions": len(keys),
        "export_commits_read": len(_EXPORTS), "debug_runs_logged": len(DEBUG_RUNS), "outputs_sha256": {o: P7.fsha(out / o) for o in outputs}})
    print(json.dumps({"targets": {s: folds_ev[s]["status"] for s in folds_ev}, "outputs": len(outputs), "socket_events": len(SOCKET_EVENTS),
                      "stores_unchanged": store_sha_before == store_sha_after, "ledger_missing": len(missing)}))
    failed = [k for k, v in tr.items() if isinstance(v, dict) and v.get("pass") is False]
    failed += ["trace invalid inputs"] if (tj.get("invalid_inputs_all_rejected") is False) else []
    failed += ["event without post-event text"] if not (tj.get("event_without_post_event_text") or {}).get("pass", False) else []
    failed += ["social or catalyst code changed"] if unchanged else []
    failed += ["an existing module imports socialcat"] if importers else []
    failed += ["registry rows missing from the ledger"] if missing else []
    failed += ["socket events"] if SOCKET_EVENTS else []
    failed += ["stores changed"] if store_sha_before != store_sha_after else []
    if failed:
        print(json.dumps({"FAILED": failed}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

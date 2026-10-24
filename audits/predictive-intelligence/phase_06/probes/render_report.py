"""Phase 06: render labels/COVERAGE_CENSORED_REPORT.md tables from labels/coverage.json and the evidence files.

Only development detail and holdout counts and censoring are rendered (the holdout section reads SEAL.json's state counts).
    python -B render_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
sys.path.insert(0, str(PHASE.parents[2]))
from memelab.predictive import labels as L  # noqa: E402

SHORT = {L.T1: "T1 24 h", L.T1B: "T1b 6 h", L.T2: "T2 24 h"}
CLASSES = {L.T1: ["TARGET_FIRST", "INVALIDATION_FIRST", "AMBIGUOUS_BAR", "NEITHER", "NO_TRADES_AFTER_ENTRY"],
           L.T1B: ["TARGET_FIRST", "INVALIDATION_FIRST", "AMBIGUOUS_BAR", "NEITHER", "NO_TRADES_AFTER_ENTRY"],
           L.T2: ["DRAWDOWN_50", "TRADING_HALT", "NO_SEVERE_EVENT"]}


def j(p):
    p = PHASE / p
    return json.loads(p.read_text()) if p.exists() else {}


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(head))) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def by_dim(cov, dim, target):
    d = cov.get(f"development_class_by_{dim}", {}).get(target, {})
    keys = sorted({k.split("|")[0] for k in d})
    rows = []
    for k in keys:
        cnt = [d.get(f"{k}|{c}", 0) for c in CLASSES[target]]
        rows.append([k] + cnt + [sum(cnt)])
    return table([dim] + CLASSES[target] + ["labelled"], rows)


def state_by_dim(cov, dim, target):
    d = cov.get(f"development_state_by_{dim}", {}).get(target, {})
    states = sorted({k.split("|")[1] for k in d})
    keys = sorted({k.split("|")[0] for k in d})
    return table([dim] + states, [[k] + [d.get(f"{k}|{s}", 0) for s in states] for k in keys])


def main():
    cov = j("labels/coverage.json")
    run = j("evidence/labels_run.json")
    rr = j("evidence/revision_reread.json").get("summary", {})
    c05 = j("evidence/revision_vs_phase05.json")
    parts = []
    # states by split
    sb = cov["state_by_split"]
    splits_states = sorted({k for t in sb for k in sb[t]})
    parts.append("### States by target and split (every decision event of the exports)\n\n" +
                 table(["split:state"] + [SHORT[t] for t in L.TARGETS], [[k] + [sb.get(t, {}).get(k, 0) for t in L.TARGETS] for k in splits_states]))
    dc = cov["development_class"]
    parts.append("### Development labels by class\n\n" + table(["class"] + [SHORT[t] for t in L.TARGETS],
                 [[c] + [dc.get(t, {}).get(c, "") for t in L.TARGETS] for c in sorted({c for t in dc for c in dc[t]})] +
                 [["labelled"] + [sum(dc.get(t, {}).values()) for t in L.TARGETS],
                  ["positive (label 1)"] + [cov["development_label"].get(t, {}).get("1", 0) for t in L.TARGETS]]))
    for dim, title in (("launch_age_bucket", "launch age at the decision (token `first_pool_at` of the decision's export)"),
                       ("liquidity_bucket", "thesis liquidity at the decision (USD)"), ("day_utc", "UTC decision day"),
                       ("week_utc", "ISO week"), ("status_group", "thesis status group"), ("route", "pool route")):
        parts.append(f"### Development classes by {title}\n\n" + "\n\n".join(f"{SHORT[t]}\n\n" + by_dim(cov, dim, t) for t in L.TARGETS))
        parts.append(f"### Development states by {title}\n\n" + "\n\n".join(f"{SHORT[t]}\n\n" + state_by_dim(cov, dim, t) for t in L.TARGETS))
    lens = cov["censoring_lens"]
    parts.append("### Censoring and the conservative lens (development)\n\n" + table(
        ["target", "labelled", "positive", "UNVERIFIABLE (eligible, censored)", "VENDOR_OR_ROUTE_GAP (before thinning)", "lens rule"],
        [[SHORT[t], lens[t]["labeled"], lens[t]["positive_labeled"], lens[t]["unverifiable"], lens[t]["vendor_or_route_gap_unthinned"],
          lens[t]["lens_rule"]] for t in L.TARGETS]))
    amb = cov["ambiguous"]
    parts.append("### Tie rule, wicks, sparse paths\n\n" + table(
        ["target", "labelled", "AMBIGUOUS_BAR", "share", "positives if ties were positive", "touches", "WICK_TOUCH (< $500)", "SPARSE_PATH"],
        [[SHORT[t], amb[t]["labeled"], amb[t]["ambiguous"], f"{amb[t]['ambiguous'] / amb[t]['labeled']:.3f}" if amb[t]["labeled"] else "",
          amb[t]["positive_if_tie_positive"], cov["wick_touch_share"][t]["touches"], cov["wick_touch_share"][t]["wick"],
          cov["sparse_path"][t]] for t in L.TARGETS]))
    parts.append("### Survivorship: route, read outcome and eligibility (development and purged decisions, one row per decision)\n\n" +
                 table(["route", "read", "eligibility", "decisions"],
                       [k.split("|") + [v] for k, v in sorted(cov["survivorship_reads_development_and_purged"].items())]))
    ho = cov["holdout"]
    hs = ho.get("state_counts") or {}
    hstates = sorted({k for t in hs for k in hs[t]})
    parts.append("### Holdout (sealed): counts and censoring only\n\n" + table(["state"] + [SHORT[t] for t in L.TARGETS],
                 [[s] + [hs.get(t, {}).get(s, 0) for t in L.TARGETS] for s in hstates]))
    out = PHASE / "labels" / "coverage_tables.md"
    out.write_text("# Coverage tables (generated by probes/render_report.py from labels/coverage.json)\n\n" + "\n\n".join(parts) + "\n")
    print(out)


if __name__ == "__main__":
    main()

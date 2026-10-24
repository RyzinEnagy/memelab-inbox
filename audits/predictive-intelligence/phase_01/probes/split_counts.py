"""Phase 01 (repair pass 2): decision events per pre-registered target and split, built with the point-in-time decision rule of
memelab/predictive/decisions.py (CC-02, PI-D-021), plus the row-identity statistics behind skeptic finding F1, the liquidity
follow-up count (M5) and the universe-filter count (M6). Counts only; no price after a decision and no outcome is read.

Export versions are read from git objects along the first-parent history of the ref, oldest first.

    python audits/predictive-intelligence/phase_01/probes/split_counts.py origin/main [OUT.json]
"""
import collections
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402


def git(*a):
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y-%m-%dT%H:%MZ")


def load_exports(ref):
    revs = [ln.split() for ln in git("rev-list", "--reverse", "--first-parent", "--timestamp", ref, "--", "data/state/latest.json").decode().splitlines() if ln.strip()]
    return [D.export_from_doc(s, int(t), json.loads(git("show", f"{s}:data/state/latest.json"))) for t, s in revs]


def main(ref, out=None):
    exports = load_exports(ref)
    data_end = max(e["commit_time"] for e in exports)
    cands = D.candidates(exports)
    evs = D.decisions(cands)
    # F1 statistics: several rows per key, rows first visible after their key
    key_first, key_rows_first = {}, collections.defaultdict(set)
    for e in exports:
        seen_here = collections.defaultdict(set)
        for r in e["theses"]:
            k = (r["mint"], float(r["created_at"]))
            seen_here[k].add(D.row_sha256(r))
        for k, shas in seen_here.items():
            if k not in key_first:
                key_first[k] = e["commit_time"]
                key_rows_first[k] = shas
    multi_first = sum(1 for k, v in key_rows_first.items() if len(v) > 1)
    late_rows = [c for c in cands if c["first_visible"] > key_first[(c["mint"], c["created_at"])]]
    sol = [e for e in evs if e["chain"] == "solana" and e["snapshot"].get("price")]
    h0, h1 = (ts(x) for x in C.ACCEPTANCE["holdout_window_utc"])
    res = {"ref": git("rev-parse", ref).decode().strip(), "export_versions": len(exports), "data_end": iso(data_end),
           "rule": "memelab/predictive/decisions.py (CC-02, PI-D-021)",
           "rows": {"distinct_rows": len(cands), "keys": len(key_first), "keys_with_several_rows_in_first_export": multi_first,
                    "rows_first_visible_after_their_key": len(late_rows),
                    "late_rows_examples": [{"mint": c["mint"], "created_at": c["created_at"], "status": c["row"].get("status"),
                                            "key_first": iso(key_first[(c["mint"], c["created_at"])]), "row_first": iso(c["first_visible"])}
                                           for c in late_rows[:6]]},
           "decision_events": {"all": len(evs), "solana_priced": len(sol), "with_key_conflict": sum(1 for e in sol if "KEY_CONFLICT" in e["flags"]),
                               "chain_none": sum(1 for e in evs if e["chain"] is None)},
           "holdout_window_utc": C.ACCEPTANCE["holdout_window_utc"]}
    for name in C.PRIMARY + ("price_path_target_before_invalidation_7d",):
        h = C.TARGETS[name]["horizon_s"]
        kept = D.thin(sol, h)
        c = {"development": 0, "purged_crosses_holdout": 0, "holdout": 0, "after_holdout_window": 0, "not_matured_at_data_end": 0}
        for e in kept:
            t = e["decision_time"]
            mat = C.label_matures_at(name, t) if name in C.PRIMARY else t + 300 + h + 900
            if t >= h1:
                c["after_holdout_window"] += 1
            elif mat > data_end:
                c["not_matured_at_data_end"] += 1
            elif t >= h0:
                c["holdout"] += 1
            elif mat > h0:
                c["purged_crosses_holdout"] += 1
            else:
                c["development"] += 1
        c["all_thinned"] = len(kept)
        c["with_key_conflict"] = sum(1 for e in kept if "KEY_CONFLICT" in e["flags"])
        c["with_pit_pool"] = sum(1 for e in kept if e["pool_pit"])
        res[name] = c
    # M5: liquidity follow-up, per thinned 24 h event: exit capacity at the decision and a later row 20 to 28 h after it
    rows_by_mint = collections.defaultdict(list)
    for cnd in cands:
        rows_by_mint[cnd["mint"]].append(cnd)
    k24 = D.thin(sol, 86400)
    fol = 0
    for e in k24:
        if e["snapshot"].get("exit_cap_3pct") is None:
            continue
        if any(e["created_at"] + 20 * 3600 <= r["created_at"] <= e["created_at"] + 28 * 3600 and D._snap(r["row"]).get("exit_cap_3pct") is not None
               for r in rows_by_mint[e["mint"]]):
            fol += 1
    res["liquidity_followup_24h_events"] = {"events": len(k24), "with_exit_cap_at_decision_and_row_20_to_28h_later": fol}
    # M6: how many Solana priced first events sit below the stage-1 filter
    first = {}
    for e in sol:
        first.setdefault(e["mint"], e)
    below = [e for e in sol if (e["snapshot"].get("liquidity") or 0) < 20000 or (e["snapshot"].get("vol_24h") or 0) < 50000]
    res["universe_filter"] = {"solana_priced_events": len(sol), "below_stage1_liq20k_or_vol50k": len(below),
                              "vol_24h_under_1000": sum(1 for e in sol if (e["snapshot"].get("vol_24h") or 0) < 1000),
                              "vol_24h_missing": sum(1 for e in sol if e["snapshot"].get("vol_24h") is None)}
    text = json.dumps(res, indent=1, sort_keys=True)
    if out:
        Path(out).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

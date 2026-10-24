"""Phase 01: decision-event counts per pre-registered target and split (development, purged, retrospective holdout,
not yet matured), from the same git history as decision_universe_probe.py. Counts only; no price or outcome is read.

    python audits/predictive-intelligence/phase_01/probes/split_counts.py origin/main
"""
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("dup", Path(__file__).with_name("decision_universe_probe.py"))
dup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dup)
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from memelab.predictive import contract as C  # noqa: E402


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def main(ref):
    log = [ln.split() for ln in dup.git("log", "--reverse", "--format=%H %ct", ref, "--", "data/state/latest.json").decode().splitlines() if ln.strip()]
    seen, rows = set(), []
    for sha, ct in log:
        doc = json.loads(dup.git("show", f"{sha}:data/state/latest.json"))
        t = doc.get("_tables") or {}
        toks = {k["mint"]: k for k in t.get("tokens") or []}
        for th in t.get("theses") or []:
            key = (th["mint"], float(th["created_at"]))
            if key in seen:
                continue
            seen.add(key)
            s = json.loads(th.get("snapshot_json") or "{}")
            tk = toks.get(th["mint"]) or {}
            if (tk.get("chain") or "solana") == "solana" and s.get("price"):
                rows.append({"mint": th["mint"], "decision_t": int(ct)})
    data_end = max(int(ct) for _s, ct in log)
    h0, h1 = (ts(x) for x in C.ACCEPTANCE["holdout_window_utc"])
    out = {"ref": dup.git("rev-parse", ref).decode().strip(), "data_end": dup.iso(data_end), "holdout_window_utc": C.ACCEPTANCE["holdout_window_utc"]}
    by = {}
    for r in rows:
        by.setdefault(r["mint"], []).append(r["decision_t"])
    for name in C.PRIMARY + ("price_path_target_before_invalidation_7d",):
        h = C.TARGETS[name]["horizon_s"]
        kept = [(m, t) for m, lst in by.items() for t in dup.thin(lst, h)]
        c = {"development": 0, "purged_crosses_holdout": 0, "holdout": 0, "after_holdout_window": 0, "not_matured_at_data_end": 0}
        for m, t in kept:
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
        out[name] = c
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])

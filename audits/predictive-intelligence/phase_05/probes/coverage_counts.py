"""Phase 05 coverage counts from the real store (read only): decisions by split, chain, route and fetch scope; series statuses;
candle counts by availability basis; snapshot missingness by feature group and reason. Feeds data/SOURCE_COVERAGE.md.

    python -B coverage_counts.py     # writes evidence/coverage_counts.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")


def split(t: float) -> str:
    h0, h1 = (C.parse_utc(x) for x in C.ACCEPTANCE["holdout_window_utc"])
    if t >= h1:
        return "prospective"
    if t >= h0:
        return "retrospective_holdout"
    return "development_6h" if SRC.development_period(t) else "purged"


def main() -> None:
    con = S.connect(STORE)
    decs = S.iter_rows(con, "SELECT * FROM predictive_decisions")
    out: dict = {"decisions": len(decs), "mints": len({(d["chain"], d["mint"]) for d in decs})}
    out["by_chain"] = dict(collections.Counter(str(d["chain"]) for d in decs))
    out["by_split_solana"] = dict(collections.Counter(split(d["decision_time"]) for d in decs if d["chain"] == "solana"))
    out["fetch_scope"] = dict(collections.Counter(SRC.fetch_scope(d) for d in decs))
    out["key_conflict"] = sum(1 for d in decs if "KEY_CONFLICT" in json.loads(d["flags_json"]))
    out["first_export_utc"] = min(d["decision_time"] for d in decs)
    out["last_export_utc"] = max(d["decision_time"] for d in decs)
    st = S.iter_rows(con, "SELECT * FROM predictive_source_status")
    out["series"] = {"rows": len(st), "by_status": dict(collections.Counter(s["status"] for s in st)),
                     "complete_history": sum(1 for s in st if s["cover_complete"]),
                     "by_kind": dict(collections.Counter("reread" if "#reread" in s["series_id"] else ("token" if "#token" in s["series_id"]
                                                                                                         else "first") for s in st))}
    out["responses"] = {"by_http": dict(collections.Counter(r["http_status"] for r in S.responses(con, S.SOURCE_GT))),
                        "by_identity": dict(collections.Counter(str(r["identity_check"]) for r in S.responses(con, S.SOURCE_GT))),
                        "bytes": sum(r["body_bytes"] for r in S.responses(con, S.SOURCE_GT)),
                        "candles_dropped_after_boundary": sum(r["candles_dropped_after_boundary"] or 0 for r in S.responses(con, S.SOURCE_GT)),
                        "candles_refused": sum(r["candles_refused"] or 0 for r in S.responses(con, S.SOURCE_GT))}
    cs = S.iter_rows(con, "SELECT available_basis, vanished, MIN(start_at) a, MAX(end_at) b, COUNT(*) n, COUNT(DISTINCT pool_address) p "
                          "FROM predictive_candles GROUP BY 1, 2")
    out["candles"] = cs
    snaps = S.iter_rows(con, "SELECT snapshot_key, availability_mode, decision_key FROM predictive_snapshots")
    out["snapshots"] = dict(collections.Counter(s["availability_mode"] for s in snaps))
    miss: dict = {}
    for mode in F.MODES:
        rows = S.iter_rows(con, "SELECT v.feature_name, v.missing_reason, v.missing_basis FROM predictive_feature_values v JOIN "
                                "predictive_snapshots s USING(snapshot_key) WHERE s.availability_mode=?", (mode,))
        grp = {f["name"]: f["group"] for f in F.FEATURES}
        c = collections.Counter((grp[r["feature_name"]], r["missing_reason"] or "VALUE") for r in rows)
        miss[mode] = {f"{g}:{k}": n for (g, k), n in sorted(c.items())}
    out["values_by_group_and_reason"] = miss
    dev = [d for d in decs if SRC.fetch_scope(d) == "DEVELOPMENT"]
    dk = {d["decision_key"] for d in dev}
    rows = S.iter_rows(con, "SELECT s.decision_key, v.missing_reason FROM predictive_feature_values v JOIN predictive_snapshots s "
                            "USING(snapshot_key) WHERE s.availability_mode='provider' AND v.feature_name='cdl_log_ret_1h'")
    out["development_decisions_with_ret_1h"] = dict(collections.Counter(r["missing_reason"] or "VALUE" for r in rows
                                                                        if r["decision_key"] in dk))
    (PHASE / "evidence" / "coverage_counts.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps(out, default=str)[:3000])


if __name__ == "__main__":
    main()

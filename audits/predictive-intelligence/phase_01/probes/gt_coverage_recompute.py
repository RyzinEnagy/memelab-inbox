"""Phase 01: recompute the coverage sample offline from the raw GeckoTerminal bodies saved by gt_coverage_probe.py, under change
control CC-01 (reference candle available at the decision) and, with --eligibility REF, under CC-02 F3 (ELIGIBLE, MARKET_INACTIVE or
VENDOR_OR_ROUTE_GAP, using each decision's own thesis snapshot from the git history of REF). No network call. Coverage only: no
barrier, return or class of any target is computed.

    python audits/predictive-intelligence/phase_01/probes/gt_coverage_recompute.py SAMPLE.json RAW_DIR OUT.json [--eligibility origin/main]
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from memelab.predictive import contract as C  # noqa: E402


def main(sample: str, raw: str, out: str, ref: str | None = None) -> None:
    s = json.loads(Path(sample).read_text())
    snaps = {}
    if ref:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import split_counts as S
        from memelab.predictive import decisions as D
        for e in D.decisions(D.candidates(S.load_exports(ref))):
            snaps[(e["mint"], e["decision_time"])] = e
    calls = {c["tag"]: c for c in s["calls"]}
    rows = []
    for r in s["rows"]:
        x = {k: r.get(k) for k in ("mint", "decision_utc", "pool", "pool_route", "coverage")}
        tag = f"ohlcv5_{(r.get('pool') or '')[:6]}"
        c = calls.get(tag)
        d = dt.datetime.fromisoformat(r["decision_utc"].replace("Z", "+00:00")).timestamp()
        ev = snaps.get((r["mint"], d))
        if ref:
            x["snapshot_vol_24h"] = None if ev is None else ev["snapshot"].get("vol_24h")
            x["decision_found"] = ev is not None
        if not c or c["http"] != 200:
            x["cc01"] = "NO_DATA" if not c else f"HTTP_{c['http']}"
            if ref:
                x["f3_class"] = "NOT_READ_RATE_LIMITED" if c and c["http"] == 429 else C.eligibility(None, d, read_ok=False, pool=r.get("pool"),
                                                                                                          route=r["pool_route"], snapshot_vol_24h=None)
            rows.append(x)
            continue
        body = json.loads((Path(raw) / f"{c['n']:02d}_{c['tag']}.json").read_bytes())
        candles = body["data"]["attributes"]["ohlcv_list"]
        refc = C.reference_candle(candles, d)
        x["cc01"] = "OK" if refc is not None else "INELIGIBLE_NO_RECENT_TRADE"
        x["cc01_reference_candle_end_min_before_decision"] = None if refc is None else round((d - (refc[0] + 300)) / 60, 1)
        if ref:
            x["f3_class"] = C.eligibility(candles, d, read_ok=True, pool=r.get("pool"), route=r["pool_route"],
                                          snapshot_vol_24h=x["snapshot_vol_24h"])
        x["path_candles_24h"] = len(C.path_candles(candles, d, 86400))
        rows.append(x)
    res = {"source_sample_sha256_note": "gt_coverage_sample.json", "rule": "CC-01" + (" and CC-02 F3" if ref else ""), "rows": rows,
           "counts": {k: sum(1 for r in rows if r["cc01"] == k) for k in sorted({r["cc01"] for r in rows})},
           "changed_vs_first_rule": sum(1 for r in rows if r["cc01"] != r["coverage"])}
    if ref:
        res["f3_counts"] = {k: sum(1 for r in rows if r.get("f3_class") == k) for k in sorted({r.get("f3_class") for r in rows})}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res["counts"]), "changed", res["changed_vs_first_rule"], json.dumps(res.get("f3_counts")))


if __name__ == "__main__":
    a = sys.argv[1:]
    ref = a[a.index("--eligibility") + 1] if "--eligibility" in a else None
    main(a[0], a[1], a[2], ref)

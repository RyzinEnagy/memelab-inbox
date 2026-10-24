"""Phase 01: recompute the coverage sample under change control CC-01 (reference candle must be available at the decision),
offline, from the raw GeckoTerminal bodies saved by gt_coverage_probe.py. No network call. Coverage only: no barrier, return or
class is computed.

    python audits/predictive-intelligence/phase_01/probes/gt_coverage_recompute.py SAMPLE.json RAW_DIR OUT.json
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from memelab.predictive import contract as C  # noqa: E402


def main(sample: str, raw: str, out: str) -> None:
    s = json.loads(Path(sample).read_text())
    calls = {c["tag"]: c for c in s["calls"]}
    rows = []
    for r in s["rows"]:
        x = {k: r.get(k) for k in ("mint", "decision_utc", "pool", "pool_route", "coverage")}
        tag = f"ohlcv5_{(r.get('pool') or '')[:6]}"
        c = calls.get(tag)
        if not c or c["http"] != 200:
            x["cc01"] = "NO_DATA" if not c else f"HTTP_{c['http']}"
            rows.append(x)
            continue
        body = json.loads((Path(raw) / f"{c['n']:02d}_{c['tag']}.json").read_bytes())
        candles = body["data"]["attributes"]["ohlcv_list"]
        d = dt.datetime.fromisoformat(r["decision_utc"].replace("Z", "+00:00")).timestamp()
        ref = C.reference_candle(candles, d)
        x["cc01"] = "OK" if ref is not None else "INELIGIBLE_NO_RECENT_TRADE"
        x["cc01_reference_candle_end_min_before_decision"] = None if ref is None else round((d - (ref[0] + 300)) / 60, 1)
        x["path_candles_24h"] = len(C.path_candles(candles, d, 86400))
        rows.append(x)
    res = {"source_sample_sha256_note": "gt_coverage_sample.json", "rule": "CC-01", "rows": rows,
           "counts": {k: sum(1 for r in rows if r["cc01"] == k) for k in sorted({r["cc01"] for r in rows})},
           "changed_vs_first_rule": sum(1 for r in rows if r["cc01"] != r["coverage"])}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res["counts"]), "changed", res["changed_vs_first_rule"])


if __name__ == "__main__":
    main(*sys.argv[1:4])

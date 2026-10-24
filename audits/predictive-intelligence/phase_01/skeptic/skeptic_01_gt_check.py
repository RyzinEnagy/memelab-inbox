"""Phase 01 skeptic: re-derive GeckoTerminal coverage numbers from raw bodies, independently of the phase's code.

For each OHLCV body: candle count, earliest/latest candle, the CC-01 reference candle (end + 300 s <= decision, end >= decision
- 3600 s), path candle count for 24 h (start >= t_entry, end <= t_entry + 24 h), largest path gap. Then compare the phase's
saved bodies with this skeptic's own live re-reads (same URL) candle by candle. No barrier, return or class is computed.

    python -I skeptic_01_gt_check.py PHASE_RAW_DIR SKEPTIC_LIVE_DIR SAMPLE_JSON
"""
import datetime as dt
import json
import sys
from pathlib import Path

LAG, PER, H24 = 300, 300, 86400


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def candles(p):
    d = json.loads(Path(p).read_bytes())
    return sorted((((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []), key=lambda c: c[0])


def stats(cs, decision):
    te = decision + LAG
    ref = [c for c in cs if c[0] + PER + LAG <= decision and c[0] + PER >= decision - 3600]
    path = [c for c in cs if c[0] >= te and c[0] + PER <= te + H24]
    pts = sorted({te, te + H24, *[c[0] for c in path]})
    return {"n": len(cs), "earliest_h_before_entry": round((te - cs[0][0]) / 3600, 2) if cs else None,
            "cc01_ref": bool(ref), "ref_end_min_before_decision": round((decision - (ref[-1][0] + PER)) / 60, 1) if ref else None,
            "path_24h": len(path), "max_gap_h": round(max(b - a for a, b in zip(pts, pts[1:])) / 3600, 2)}


def main(raw, live, sample):
    s = json.load(open(sample))
    rows = {r["pool"]: r for r in s["rows"] if r.get("pool")}
    out = {}
    for f in sorted(Path(raw).glob("*_ohlcv5_*.json")):
        if f.name.endswith("_again.json"):
            continue
        pool_pfx = f.name.split("_ohlcv5_")[1][:6]
        r = next((r for p, r in rows.items() if p.startswith(pool_pfx)), None)
        if r is None or r.get("ohlcv_http") != 200:
            out[f.name] = {"skip": "no 200 body"}
            continue
        st = stats(candles(f), ts(r["decision_utc"]))
        claim = {"n": r.get("candles"), "path_24h": r.get("path_candles_24h"), "ref": r.get("reference_trade_in_hour_before_entry"),
                 "max_gap_h": r.get("path_max_gap_h")}
        out[f.name] = {"decision": r["decision_utc"], "mine": st, "phase_claim": claim,
                       "agree": st["n"] == claim["n"] and st["path_24h"] == claim["path_24h"] and st["cc01_ref"] == claim["ref"]}
    # live re-reads vs phase bodies
    pairs = {"s1_ioaDGk.json": "02_ohlcv5_ioaDGk.json", "s2_AVaw6h.json": "01_ohlcv5_AVaw6h.json"}
    for mine, theirs in pairs.items():
        a = {c[0]: c for c in candles(Path(raw) / theirs)}
        b = {c[0]: c for c in candles(Path(live) / mine)}
        com = sorted(set(a) & set(b))
        out["reread_" + mine] = {"phase_candles": len(a), "skeptic_candles": len(b), "common": len(com),
                                 "changed": sum(1 for t in com if a[t] != b[t]), "only_phase": len(set(a) - set(b)), "only_skeptic": len(set(b) - set(a)),
                                 "oldest_candle_utc": dt.datetime.fromtimestamp(min(b), dt.UTC).isoformat() if b else None,
                                 "retrieved_at": (Path(live) / ("t1.txt" if mine.startswith("s1") else "t2.txt")).read_text().strip()}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])

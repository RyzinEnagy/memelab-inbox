"""Phase 01 repair pass 2 (skeptic M7): which retrospective-holdout decisions have price data that was already fetched, and what of
it was looked at. Reads the coverage sample summary, the raw GeckoTerminal bodies saved outside the repo (the phase's and the
skeptic's re-reads), and the decision events of memelab/predictive/decisions.py. Prints no price. No network.

A holdout event counts as CONTACTED when a fetched response for its mint's pool covers any part of the event's span
[decision - 3600 s, label_matures_at of the longest primary target]. A response covers [earliest returned candle, before_timestamp]
when it returned the full 1,000 candles, and everything up to before_timestamp when it returned fewer (an empty stretch is
information too: it says no trade happened). It counts as SUMMARIZED when it is the sampled decision whose coverage numbers
(candle counts, path count, largest gap) were printed in gt_coverage_sample.json or by the skeptic's check.

    python audits/predictive-intelligence/phase_01/probes/holdout_contact.py SAMPLE.json RAW_DIR [EXTRA_DIR ...] > OUT.json
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import split_counts as S  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(sample, raw, extra):
    s = json.loads(Path(sample).read_text())
    pool_mint = {r["pool"]: r["mint"] for r in s["rows"] if r.get("pool")}
    sampled = {(r["mint"], r["decision_utc"]) for r in s["rows"]}
    bodies = []
    before = {}
    for c in s["calls"]:
        if c["tag"].startswith("ohlcv5_") and c["http"] == 200:
            pool = c["url"].split("/pools/")[1].split("/")[0]
            before[pool] = int(c["url"].split("before_timestamp=")[1].split("&")[0])
            bodies.append((pool, Path(raw) / f"{c['n']:02d}_{c['tag']}.json", "phase01 " + c["retrieved_at"]))
    for d in extra:
        for f in sorted(Path(d).glob("*.json")):
            pref = f.stem.split("_", 1)[-1]
            pool = next((p for p in pool_mint if p.startswith(pref)), None)
            if pool:
                bodies.append((pool, f, "skeptic re-read (same URL)"))
    spans = []
    for pool, f, who in bodies:
        lst = json.loads(f.read_bytes())["data"]["attributes"]["ohlcv_list"]
        t = sorted(int(x[0]) for x in lst)
        lo = t[0] if len(t) >= 1000 else 0
        spans.append({"pool": pool, "mint": pool_mint[pool], "from": lo, "to": before[pool], "candles": len(t), "source": who})
    evs = [e for e in D.decisions(D.candidates(S.load_exports("origin/main"))) if e["chain"] == "solana" and e["snapshot"].get("price")]
    h0, h1 = (ts(x) for x in C.ACCEPTANCE["holdout_window_utc"])
    out = []
    for name in C.PRIMARY:
        for e in D.thin(evs, C.TARGETS[name]["horizon_s"]):
            if not (h0 <= e["decision_time"] < h1):
                continue
            lo, hi = e["decision_time"] - 3600, C.label_matures_at("price_path_severe_drawdown_or_halt_24h", e["decision_time"])
            hit = [sp for sp in spans if sp["mint"] == e["mint"] and sp["from"] <= hi and sp["to"] >= lo]
            if hit:
                out.append({"target": name, "mint": e["mint"], "decision_utc": iso(e["decision_time"]),
                            "summarized": (e["mint"], iso(e["decision_time"])) in sampled,
                            "bodies": sorted({f"{sp['pool']} ({sp['source']})" for sp in hit})})
    res = {"bodies": [{k: (iso(v) if k in ("from", "to") else v) for k, v in sp.items()} for sp in spans], "holdout_events_contacted": out,
           "distinct_holdout_decisions_contacted": sorted({(x["mint"], x["decision_utc"]) for x in out}),
           "note": "no price, barrier or class was printed for any of these; summarized = coverage numbers printed for that decision"}
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])

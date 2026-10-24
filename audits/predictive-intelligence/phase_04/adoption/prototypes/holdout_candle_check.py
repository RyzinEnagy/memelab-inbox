"""Phase 04 holdout check for the bake-off fetch. GeckoTerminal's before_timestamp turned out to be inclusive: a request ending
at the holdout start (H0) also returned the candle that starts at H0. This script lists every returned candle at or after H0
(it reads raw bodies outside the repository; it prints timestamps only, never a price) and counts the holdout decisions on the
same pools that such a candle could serve: as a reference candle (decided within reference_max_age + 2 x 300 s of H0) or on a
path (any holdout decision on those pools starts its path after its own decision, so after H0 + 300 s).

    python holdout_candle_check.py RAW_DIR
"""
import json
import sys
import urllib.parse as up
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_dev_sample as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402

raw = Path(sys.argv[1])
calls = json.loads((HERE.parent / "data/dev_sample_calls.json").read_text())
plan = json.loads((HERE.parent / "data/dev_sample_plan.json").read_text())
late, pools = [], set()
for c in calls:
    if c["http"] != 200:
        continue
    body = json.loads((raw / c["file"]).read_bytes())
    for r in body["data"]["attributes"]["ohlcv_list"]:
        if int(r[0]) >= B.H0:
            late.append({"tag": c["tag"], "candle_start_minus_h0_s": int(r[0]) - B.H0,
                         "before_timestamp_minus_h0_s": int(up.parse_qs(up.urlparse(c["url"]).query)["before_timestamp"][0]) - B.H0})
            pools.add(plan["pools"][int(c["tag"][1:4])]["pool"])
revs = [ln.split() for ln in B.git("rev-list", "--reverse", "--first-parent", "--timestamp", B.REF, "--", "data/state/latest.json").decode().splitlines() if ln.strip()]
ex = [D.export_from_doc(s, int(t), json.loads(B.git("show", f"{s}:data/state/latest.json"))) for t, s in revs]
evs = [e for e in D.decisions(D.candidates(ex)) if e["chain"] == "solana" and e["pool_pit"] in pools and e["decision_time"] >= B.H0]
window = C.ACCEPTANCE["eligibility"]["reference_max_age_s"] + 600
near = [e for e in evs if e["decision_time"] < B.H0 + window]
print(json.dumps({"candles_at_or_after_h0": late, "pools": len(pools), "holdout_window_decisions_on_these_pools": len(evs),
                  "of_which_decided_within_reference_window_of_h0": len(near), "reference_window_s": window,
                  "verdict": "no holdout decision can use these candles" if not near else "CONTACT"}, indent=1))

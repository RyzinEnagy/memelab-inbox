"""Integration test over real collected data when the inbox has it (skipped otherwise)."""
import json
from pathlib import Path

import pytest

from memelab.bridge import ingest
from memelab import pipeline

INBOX = Path(__file__).resolve().parent.parent / "data" / "inbox"
IDS = ["disc01", "s2_01", "deep01a"]
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"


@pytest.mark.skipif(not all((INBOX / f"{i}.result.json").exists() for i in IDS), reason="live inbox files not present")
def test_paid_end_to_end_no_persist():
    res = [ingest.load_result(INBOX / f"{i}.result.json") for i in IDS]
    bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
    r = pipeline.analyze_token(PAID, bodies, sol_price=120.8, persist=False)
    b, m = r["bundle"], r["modules"]
    assert b["identity"]["symbol"] == "PAID"
    assert m["identity"]["confidence"] in ("HIGH", "MODERATE")
    # trades only from this token's pools and sane prices
    my_pools = {p["pool"] for p in b["pools"]}
    assert my_pools
    ref = b["market"]["price_usd"]
    assert all(0.2 * ref <= t[5] <= 5 * ref for t in b["trades"] if t[5])
    # quotes parsed both sides
    assert b["quotes"]["BUY"] and b["quotes"]["SELL"]
    assert 0 <= r["score"]["total"] <= 100
    assert r["status"]["status"] in {"REJECTED", "RESEARCH REQUIRED", "WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET", "OVEREXTENDED", "DISTRIBUTION RISK", "THESIS DETERIORATING", "THESIS INVALIDATED"}
    # evidence buckets present in every module
    for name, out in m.items():
        if name in ("monitor",):
            continue
        assert isinstance(out, dict) and "facts" in out and "unknowns" in out, name
    # report renders and contains the mandatory header fields
    md = r["report_md"]
    for key in ("TOKEN:", "TICKER:", "CHAIN:", "CONTRACT:", "TOKEN AGE:", "IDENTITY CONFIDENCE:", "TIMESTAMP:", "## Opportunity score", "## Current status", "## Bottom line"):
        assert key in md

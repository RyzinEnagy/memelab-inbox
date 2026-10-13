"""Builds the Phase 13 before/after scout fixture. Every name, address, count and time here is INVENTED. Run: python make_research.py

scout_before_after.json
  results    pipeline-shaped scout results (only the fields the scout lists and report read)
  findings   social findings as research_store.findings_from_db returns them
  prior      the latest earlier verdict per mint when it was a rejection
  as_of      the scout's observed_at

Tokens:
  GOODCAT   structure passes, WATCH, credible early discussion by three independent originators  -> enriched research candidate
  HYPEDOG   eight independent sources and HIGH confidence, mint authority active                -> stays rejected (fatal override)
  TOPPICK   a social "top pick" with no executable sell route                                  -> stays rejected
  GOODCAT2  a second contract whose symbol is also GOODCAT, never analyzed                       -> possible spoof, needs analysis
  OLDRUG    rejected earlier for LP control, still rejected, no social signal                    -> unchanged rejected token
  SLOWFROG  structure passes, near miss, the only discussion is three days old                  -> stale attention
  MOONX     ticker-only mentions                                                                 -> unresolved, never ranked
"""
import hashlib
import json
from pathlib import Path

T0 = 1791763200          # 2026-10-12 00:00:00Z, invented
H = 3600
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(seed: str, n: int = 44) -> str:
    d = hashlib.sha256(seed.encode()).digest() * 4
    return "".join(B58[x % 58] for x in d[:n])


MINTS = {s: b58(f"research-fixture-{s}") for s in ("GOODCAT", "HYPEDOG", "TOPPICK", "GOODCAT2", "OLDRUG", "SLOWFROG")}
AS_OF = T0 + 12 * H


def result(sym, *, score, status, reasoning, fatal=(), mcap=1_200_000, liq=180_000, depth3=9_000):
    mint = MINTS[sym]
    fl = [{"flag": f, "evidence": "invented fixture evidence", "severity": "FATAL", "category": "fixture"} for f in fatal]
    return {
        "mint": mint,
        "bundle": {"chain": "solana", "identity": {"symbol": sym, "name": f"{sym.title()} (invented)"},
                   "market": {"market_cap": mcap, "liquidity_usd_total": liq}},
        "modules": {"depth": {"exit_capacity_usd_3pct": depth3, "exit_capacity_usd_10pct": depth3 * 3},
                    "holders": {"adjusted_top10_pct": 21.0, "largest_unexplained_pct": 3.1},
                    "early": {"large_holder_net_direction": "ACCUMULATING", "absorption": "ABSORBING"},
                    "structure": {"structure": "HIGHER_LOWS"}, "breakout": {"classification": "BASE"},
                    "lifecycle": {"stage": "EARLY_DISCOVERY", "confidence": "MODERATE"}, "attention": {"trend": "RISING"},
                    "manipulation": {"label": "ORGANIC"},
                    "entries": {"entries": [{"condition": "reclaim of the invented 4h level", "invalidation_text": "4h close below the invented base"}]}},
        "ranker_inputs": {"depth": {"exit_capacity_usd_3pct": depth3}},
        "score": {"total": score, "breakdown": {}, "fatal_flags": fl, "untradeable": bool(fl), "unknown_buckets": [], "unknown_count": 0},
        "status": {"status": status, "reasoning": reasoning},
        "thesis": {"questions": {"WHY IS IT RECEIVING ATTENTION?": "invented discovery signal"}},
        "report_path": f"fixture://reports/{sym}.md",
    }


def finding(sym, *, ind, conf, last_h, first_h, originators=(), flags=(), conflicted=0, stance=None, status="ok", reasons=()):
    return {"kind": "CONTRACT", "chain": "solana", "contract": MINTS[sym], "symbol": sym.rstrip("2") if sym == "GOODCAT2" else sym,
            "status": status, "reasons": list(reasons), "confidence": conf, "freshness": "FRESH" if last_h < 48 else "STALE",
            "first_observed_at": AS_OF - first_h * H, "last_observed_at": AS_OF - last_h * H, "earliest_published_at": AS_OF - first_h * H - 60,
            "item_count": ind * 4, "independent_source_count": ind if status == "ok" else None, "amplifier_count": ind * 3,
            "conflicted": conflicted, "stance": stance or {"positive": ind}, "flags": list(flags),
            "originators": [{"item_key": f"x:fx-{sym.lower()}-{i}", "source_id": o, "event_time": AS_OF - first_h * H + i * 600, "basis": "PROVIDER"}
                            for i, o in enumerate(originators)],
            "chrono_flags": [], "is_fixture": True,
            "source": {"run_id": 1, "cluster_key": f"ca:solana:{MINTS[sym]}", "engine_version": "narr-v1", "window": "fixture", "cutoff": AS_OF}}


def build() -> dict:
    results = [
        result("GOODCAT", score=68, status="WATCH", reasoning="structure building; no entry yet"),
        result("HYPEDOG", score=0, status="REJECTED", reasoning="fatal structural flag", fatal=["MINT_AUTHORITY_ACTIVE"]),
        result("TOPPICK", score=0, status="REJECTED", reasoning="no executable exit", fatal=["NO_SELL_ROUTE"], liq=900, depth3=0),
        result("OLDRUG", score=0, status="REJECTED", reasoning="LP not locked", fatal=["LP_UNLOCKED_DEV_CONTROLLED"]),
        result("SLOWFROG", score=48, status="RESEARCH REQUIRED", reasoning="too many unknowns"),
    ]
    burst = {"flag": "burst_amplification", "evidence": "HEURISTIC", "proven": False, "note": "invented: 40 amplifying sources inside 15 minutes"}
    findings = [
        finding("GOODCAT", ind=3, conf="MODERATE", last_h=2, first_h=20, originators=["fx_source_a", "fx_source_b", "fx_source_c"]),
        finding("HYPEDOG", ind=8, conf="HIGH", last_h=1, first_h=6, originators=["fx_source_d", "fx_source_e"], flags=[burst]),
        finding("TOPPICK", ind=5, conf="HIGH", last_h=1, first_h=3, originators=["fx_source_f"]),
        finding("GOODCAT2", ind=1, conf="LOW", last_h=3, first_h=4, originators=["fx_source_g"]),
        finding("SLOWFROG", ind=2, conf="MODERATE", last_h=72, first_h=90, originators=["fx_source_h", "fx_source_i"]),
        {"kind": "TICKER_ONLY", "symbol": "MOONX", "mentions": 14, "is_fixture": True, "source": {"run_id": 1, "engine_version": "narr-v1", "window": "fixture"}},
    ]
    prior = {MINTS["OLDRUG"]: {"rejected_at": AS_OF - 30 * H, "stage": "deep", "fatal_flags": ["LP_UNLOCKED_DEV_CONTROLLED"],
                               "why_failed": "fatal structural flag", "reconsider_if": "LP locked/burned or migrated to protocol-custodied pool"}}
    return {"schema": "memelab.social.research.fixture/1", "is_fixture": True, "as_of": AS_OF, "mints": MINTS, "results": results,
            "findings": findings, "prior": prior, "rejected_stage2": [], "min_score": 55}


if __name__ == "__main__":
    out = Path(__file__).parent / "scout_before_after.json"
    out.write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
    print(out)

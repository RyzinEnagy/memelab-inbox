"""Builds outcomes_fixture.json for the Phase 16 ledger demo. Everything is invented: tokens, references, prices, times.

Five signals generated at G = 2026-10-13T12:00:00Z (contracts reuse the invented Phase 14 fixture tokens):
  GOODCAT   EMITTED      clean path; its 1h exit snapshot is revised by the provider before evaluation 2
  HYPEDOG   REJECTED     liquidity collapses and the sell route disappears by the 6h exit
  NEWPUP    EMITTED      delisted 3h after the signal
  SLOWFROG  SUPPRESSED   only route quotes (no midpoint) around the 1h exit; at 6h the quote returns 60% of the displayed value
  theme     EMITTED      a theme with no contract (no exact identity)
Evaluation 1 runs at G+7h, evaluation 2 at G+26h. 72h and 7d never mature inside the fixture.
Run: python tests/fixtures/social/outcomes/make_outcomes.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
G = 1791892800.0          # 2026-10-13T12:00:00Z
LAG = 300
E = G + LAG               # hypothetical entry time
EV1, EV2 = G + 7 * 3600, G + 26 * 3600
TOK = {"GOODCAT": "B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY", "HYPEDOG": "bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ",
       "NEWPUP": "aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB", "SLOWFROG": "6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931"}


def grid() -> list[float]:
    ts = [G - 1800 + k * 300 for k in range(7)]                 # before the signal (never used by an outcome)
    ts += [E + k * 300 for k in range(25)]                       # 5-minute points for 2 h after entry
    ts += [E + 7200 + k * 1800 for k in range(1, 50)]            # then 30-minute points to entry + 26.5 h
    return sorted(set(ts))


def interp(knots: list[tuple[float, float]], t: float) -> float:
    for (a, pa), (b, pb) in zip(knots, knots[1:]):
        if a <= t <= b:
            return pa + (pb - pa) * (t - a) / (b - a)
    return knots[0][1] if t < knots[0][0] else knots[-1][1]


def path(sym: str, knots, liq, stop=None, skip=lambda t: False, quote=lambda t, p, l: None) -> list[dict]:
    out = []
    for t in grid():
        if stop is not None and t >= stop:
            break
        if skip(t):
            continue
        p = round(interp(knots, (t - G) / 3600), 10)
        lv = liq(t) if callable(liq) else liq
        o = {"kind": "POINT", "chain": "solana", "contract": TOK[sym], "t": t, "available_at": t + 30, "provider": "fixture_prices",
             "price": p, "liquidity_usd": lv, "is_fixture": True}
        q = quote(t, p, lv)
        if q:
            o["sell_quote"] = q
        out.append(o)
    return out


def build() -> dict:
    sigs = [
        {"emitter": "feed", "emitter_ref": "contract:solana:" + TOK["GOODCAT"], "disposition": "EMITTED",
         "disposition_reason": "feed priority HIGH (HEURISTIC)", "classifier_version": "feed-v1", "scoring_version": "alerts-default-1",
         "policy_version": "fixture", "chain": "solana", "contract": TOK["GOODCAT"], "symbol": "GOODCAT", "event_time": G - 7200,
         "generated_at": G, "references": {"claims": [9101, 9102], "sources": ["x:id:fx_alpha", "x:id:fx_bravo"], "narrative_run_id": 1},
         "market": [{"field": "price", "value_num": 0.0100, "unit": "USD", "provider": "jupiter", "as_of": G - 60, "fact_id": 501},
                    {"field": "liquidity_reported", "value_num": 180000, "unit": "USD", "provider": "dexscreener", "as_of": G - 1800, "fact_id": 502},
                    {"field": "sell_quote_out_usd", "value_num": 488.0, "size_usd": 500, "unit": "USD", "provider": "jupiter.quote_v1", "as_of": G - 60, "fact_id": 503},
                    {"field": "price", "value_num": 0.0150, "unit": "USD", "provider": "jupiter", "as_of": G + 600, "fact_id": 504}]},
        {"emitter": "research", "emitter_ref": "solana:" + TOK["HYPEDOG"], "disposition": "REJECTED", "disposition_reason": "REJECTED_STRUCTURE",
         "classifier_version": "research-v1", "scoring_version": "default-1", "policy_version": "fixture", "chain": "solana",
         "contract": TOK["HYPEDOG"], "symbol": "HYPEDOG", "event_time": G - 3600, "generated_at": G,
         "references": {"provenance": [{"kind": "narrative_snapshot", "run_id": 1}]},
         "market": [{"field": "price", "value_num": 0.0020, "unit": "USD", "provider": "jupiter", "as_of": G - 30, "fact_id": 511},
                    {"field": "liquidity_reported", "value_num": 20000, "unit": "USD", "provider": "dexscreener", "as_of": G - 30, "fact_id": 512}]},
        {"emitter": "feed", "emitter_ref": "contract:solana:" + TOK["NEWPUP"], "disposition": "EMITTED", "disposition_reason": "feed priority MEDIUM (HEURISTIC)",
         "classifier_version": "feed-v1", "scoring_version": "alerts-default-1", "policy_version": "fixture", "chain": "solana",
         "contract": TOK["NEWPUP"], "symbol": "NEWPUP", "event_time": G - 600, "generated_at": G, "references": {"claims": [9201]},
         "market": [{"field": "price", "value_num": 0.00050, "unit": "USD", "provider": "jupiter", "as_of": G - 900, "fact_id": 521}]},
        {"emitter": "alerts", "emitter_ref": "fx-dedupe-slowfrog", "disposition": "SUPPRESSED", "disposition_reason": "cooldown active",
         "classifier_version": "feed-v1", "scoring_version": "alerts-default-1", "policy_version": "fixture", "chain": "solana",
         "contract": TOK["SLOWFROG"], "symbol": "SLOWFROG", "event_time": G - 5400, "generated_at": G, "references": {"claims": [9301]},
         "market": [{"field": "price", "value_num": 0.0300, "unit": "USD", "provider": "jupiter", "as_of": G - 45, "fact_id": 531},
                    {"field": "liquidity_reported", "value_num": 400000, "unit": "USD", "provider": "dexscreener", "as_of": G - 45, "fact_id": 532}]},
        {"emitter": "feed", "emitter_ref": "theme:dogs", "disposition": "EMITTED", "disposition_reason": "feed priority LOW (HEURISTIC)",
         "classifier_version": "feed-v1", "scoring_version": "alerts-default-1", "policy_version": "fixture", "symbol": None,
         "event_time": G - 3600, "generated_at": G, "references": {"cluster_key": "theme:dogs"}, "market": []},
    ]
    good = path("GOODCAT", [(-1, 0.0098), (0, 0.0100), (1.08, 0.0110), (6, 0.0125), (24, 0.0090), (27, 0.0090)], 180000,
                quote=lambda t, p, l: {"status": "OK", "size_usd": 500, "out_usd": round(500 * 0.976, 4)} if abs(t - (E + 21600)) < 1 else None)
    hype = path("HYPEDOG", [(-1, 0.0019), (0, 0.0020), (1.08, 0.0024), (6, 0.0004), (27, 0.0003)],
                lambda t: 20000 if t < E + 3 * 3600 else 1000,
                quote=lambda t, p, l: {"status": "NO_ROUTE", "size_usd": 500} if abs(t - (E + 21600)) < 1 else None)
    pup = path("NEWPUP", [(-1, 0.00040), (0, 0.00050), (1.08, 0.00080), (3, 0.00020)], 60000, stop=G + 3 * 3600)
    pup.append({"kind": "STATUS", "chain": "solana", "contract": TOK["NEWPUP"], "t": G + 3 * 3600, "available_at": G + 3 * 3600 + 60,
                "provider": "fixture_prices", "status": "DELISTED", "is_fixture": True})
    frog = path("SLOWFROG", [(-1, 0.0290), (0, 0.0300), (6, 0.0310), (27, 0.0320)], 400000,
                skip=lambda t: E + 3300 <= t <= E + 4800,
                quote=lambda t, p, l: {"status": "OK", "size_usd": 500, "out_usd": 300.0} if abs(t - (E + 21600)) < 1 else None)
    for t in (E + 3600, E + 3900):   # only route quotes around the 1h exit: no midpoint
        frog.append({"kind": "QUOTE", "chain": "solana", "contract": TOK["SLOWFROG"], "t": t, "available_at": t + 30, "provider": "fixture_quotes",
                     "sell_quote": {"status": "OK", "size_usd": 500, "out_usd": 489.0}, "is_fixture": True})
    allobs = good + hype + pup + frog
    batch1 = [o for o in allobs if o["available_at"] <= EV1]
    batch2 = [o for o in allobs if o["available_at"] > EV1]
    # the provider revises GOODCAT's 1h exit snapshot after evaluation 1 (same series, later available_at, new value)
    rev = dict(next(o for o in good if o["t"] == E + 3600))
    rev.update(price=0.0104, available_at=G + 20 * 3600)
    batch2.append(rev)
    return {
        "schema": "memelab.social.outcomes.fixture/1", "is_fixture": True,
        "note": "Invented signals, references, prices and times for the Phase 16 ledger demo. Built by make_outcomes.py. Not live data.",
        "policy": {}, "recorded_at": G + 60,
        "signals": {"schema": "memelab.social.signal.input/1", "is_fixture": True, "signals": sigs},
        "evaluations": [{"label": "evaluation 1", "as_of": EV1, "now": EV1 + 5, "observations": batch1},
                        {"label": "evaluation 2", "as_of": EV2, "now": EV2 + 5, "observations": batch2}],
    }


if __name__ == "__main__":
    (HERE / "outcomes_fixture.json").write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")

"""Phase 16 CLI: the signal ledger and forward evaluation.

  social evaluate record   (--signals FILE | --feed-json FILE | --research-json FILE) [--generated-at T] [--now T] [--ledger PATH] [--fixture]
                           record emitted, rejected and suppressed signals with what was known at emission (append only)
  social evaluate observe  (--prices FILE | --from-db PATH) [--now T] [--ledger PATH]
                           append dated market observations (memelab.social.prices/1, or social_market_facts of a lab database)
  social evaluate run      [--as-of T] [--now T] [--ledger PATH] [--json]
                           append 1h/6h/24h/72h/7d outcomes that matured or changed; repeatable and resumable
  social evaluate annotate --signal ID --kind SOURCE_DELETED|INVALIDATED|IDENTITY_REVISED|NOTE --reason TEXT [--at T] [--now T]
  social evaluate show     --signal ID [--as-of T]   the original context and every outcome entry (or a replay at --as-of)
  social evaluate report   [--json]                  outcome coverage per horizon and reasons for exclusion
  social evaluate verify                             hash chain, body hashes and signal context hashes
  social evaluate demo     --fixture FILE [--out FILE]   fixture snapshot before and after two evaluations (watermarked)

Exit codes: 0 done (including nothing to evaluate), 1 verify found a problem, 2 usage or input error.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from . import outcomes_core as OC, outcomes_ledger as OL

WATERMARK = "FIXTURE DEMO: invented signals, tokens, references, prices and times. This is not live data and not a trade record."


def _t(v, default=None):
    if v is None:
        return default
    from .feed_core import parse_time
    return parse_time(v)


def _iso(t: float | None) -> str:
    if t is None:
        return "none"
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _con(a):
    return OL.connect(a.ledger)


def _pol(a=None) -> dict:
    return OC.make_policy({})


def _fail(msg: str) -> None:
    print(f"social evaluate: {msg}", file=sys.stderr)
    raise SystemExit(2)


def cmd_record(a) -> None:
    pol = _pol()
    now = _t(a.now, time.time())
    try:
        if a.signals:
            doc = json.loads(Path(a.signals).read_text())
            if doc.get("schema") != OC.INPUT_SCHEMA:
                _fail(f"--signals must be a {OC.INPUT_SCHEMA} document")
            raws, fx = doc.get("signals") or [], bool(doc.get("is_fixture"))
        elif a.feed_json:
            from . import feed_core as FC
            doc = json.loads(Path(a.feed_json).read_text())
            if doc.get("schema") != FC.SCHEMA:
                _fail(f"--feed-json must be a {FC.SCHEMA} document")
            raws, fx = OC.signals_from_feed(doc, generated_at=_t(a.generated_at)), bool(doc.get("fixture"))
        elif a.research_json:
            doc = json.loads(Path(a.research_json).read_text())
            raws, fx = OC.signals_from_research(doc, generated_at=_t(a.generated_at)), False
        else:
            _fail("give --signals, --feed-json or --research-json")
        con = _con(a)
        out = OL.record_signals(con, raws, pol, now=now, is_fixture=fx or a.fixture)
    except (OC.OutcomeError, ValueError, KeyError) as e:
        _fail(str(e))
    print(json.dumps(out, indent=1, sort_keys=True))


def facts_to_observations(path: str) -> list[dict]:
    """social_market_facts of a lab database as observations: price points, candles, liquidity and route quotes."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='social_market_facts'").fetchone() is None:
        return []
    out, candles = [], {}
    for r in con.execute("SELECT * FROM social_market_facts ORDER BY fact_id"):
        base = {"chain": r["chain"], "contract": r["contract"], "t": r["as_of"], "available_at": r["fetched_at"], "provider": r["provider"],
                "source_key": f"fact:{r['fact_id']}", "pair": r["pair_id"]}
        f = r["field"]
        if r["as_of_kind"] == "HISTORICAL_CANDLE" and f.startswith("price_candle_"):
            k = (r["chain"], r["contract"], r["provider"], r["pair_id"], r["as_of"], r["fetched_at"])
            c = candles.setdefault(k, dict(base, kind="CANDLE", period_s=int(r["valid_until"] - r["valid_from"])))
            c[{"price_candle_open": "o", "price_candle_high": "h", "price_candle_low": "l", "price_candle_close": "c"}[f]] = r["value_num"]
        elif f == "price":
            out.append(dict(base, kind="POINT", price=r["value_num"]))
        elif f == "liquidity_reported" and r["value_num"] is not None:
            out.append(dict(base, kind="QUOTE", liquidity_usd=r["value_num"]))
        elif f == "sell_quote_out_usd" and r["value_num"] is not None and r["size_usd"]:
            out.append(dict(base, kind="QUOTE", sell_quote={"status": "OK", "size_usd": r["size_usd"], "out_usd": r["value_num"]}))
        elif f == "sell_quote_out" and (r["value_str"] or "").upper() in ("NO_ROUTE", "ERROR") and r["size_usd"]:
            out.append(dict(base, kind="QUOTE", sell_quote={"status": r["value_str"].upper(), "size_usd": r["size_usd"]}))
    con.close()
    return out + list(candles.values())


def cmd_observe(a) -> None:
    pol = _pol()
    now = _t(a.now, time.time())
    try:
        if a.prices:
            doc = json.loads(Path(a.prices).read_text())
            if doc.get("schema") != OC.PRICES_SCHEMA:
                _fail(f"--prices must be a {OC.PRICES_SCHEMA} document")
            raws = doc.get("observations") or []
        elif a.from_db:
            raws = facts_to_observations(a.from_db)
        else:
            _fail("give --prices or --from-db")
        out = OL.add_observations(_con(a), raws, pol, now=now)
    except (OC.OutcomeError, ValueError) as e:
        _fail(str(e))
    print(json.dumps(out, indent=1, sort_keys=True))


def render_run(s: dict) -> str:
    if not s["signals"]:
        return f"Evaluation at {_iso(s['as_of'])}: no signals recorded. Nothing to evaluate.\n"
    st = ", ".join(f"{k} {v}" for k, v in s["by_status"].items())
    rr = ", ".join(f"{k} {v}" for k, v in sorted(s["appended_by_reason"].items())) or "none"
    return (f"Evaluation at {_iso(s['as_of'])}: {s['signals']} signal(s), {s['evaluated']} signal-horizon outcome(s) computed.\n"
            f"  status now: {st}\n  appended: {s['appended']} ({rr}); unchanged and not appended: {s['unchanged']}\n")


def cmd_run(a) -> None:
    pol = _pol()
    now = _t(a.now, time.time())
    as_of = _t(a.as_of, now)
    if as_of > now:
        _fail("--as-of is in the future of --now: outcomes are never evaluated ahead of the clock")
    try:
        s = OL.evaluate_all(_con(a), as_of=as_of, pol=pol, now=now)
    except OC.OutcomeError as e:
        _fail(str(e))
    print(json.dumps(s, indent=1, sort_keys=True) if a.json else render_run(s), end="" if not a.json else "\n")


def cmd_annotate(a) -> None:
    now = _t(a.now, time.time())
    try:
        out = OL.annotate(_con(a), a.signal, a.kind, reason=a.reason, at=_t(a.at, now), available_at=now, now=now)
    except OC.OutcomeError as e:
        _fail(str(e))
    print(json.dumps(out, sort_keys=True))


def render_signal(ctx: dict) -> str:
    return json.dumps({k: v for k, v in ctx.items() if k != "_seq"}, indent=1, sort_keys=True) + "\n"


def cmd_show(a) -> None:
    con = _con(a)
    ctx = next((c for c in OL.signals(con) if c["signal_id"] == a.signal), None)
    if ctx is None:
        _fail(f"no signal {a.signal}")
    lines = ["Original context (immutable):", render_signal(ctx).rstrip(), ""]
    if a.as_of:
        pol = _pol()
        res = [o for o in OL.compute(con, as_of=_t(a.as_of), pol=pol) if o["signal_id"] == a.signal]
        lines.append(f"Replay at {_iso(_t(a.as_of))} (nothing written):")
        lines += ["  " + OC.render_outcome(o) for o in res]
    else:
        lines.append("Outcome entries (oldest first; a later entry for the same horizon supersedes, the earlier one stays):")
        for o in OL.outcome_history(con, a.signal):
            lines.append(f"  #{o['_seq']} as of {_iso(o['evaluated_as_of'])} {o['revision_reason'] or 'FIRST':<15} " + OC.render_outcome(o))
    print("\n".join(lines))


def cmd_report(a) -> None:
    pol = _pol()
    cov = OL.report(_con(a), pol)
    if a.json:
        print(json.dumps(cov, indent=1, sort_keys=True))
    else:
        print(f"Last evaluation: {_iso(cov['last_evaluated_as_of'])}; observations in ledger: {cov['observations']}")
        print(OC.render_report(cov), end="")


def cmd_verify(a) -> None:
    v = OL.verify(_con(a))
    print(json.dumps(v, indent=1, sort_keys=True))
    raise SystemExit(0 if v["ok"] else 1)


def _outcome_table(con, as_of_label: str) -> list[str]:
    lines = []
    for c in OL.signals(con):
        lab = c["token"]["symbol_display_only"] or c["emitter_ref"]
        lines.append(f"{c['signal_id']} {lab} ({c['disposition']}, {c['emitter']})")
        latest = OL.latest_outcomes(con)
        for h in c["assumptions"]["horizons_s"]:
            o = latest.get((c["signal_id"], h))
            lines.append("  " + (OC.render_outcome(o) if o else f"{OC.hname(h):>4} NOT_EVALUATED"))
    return lines


def demo_markdown(spec_path: str) -> str:
    """Record five fixture signals, evaluate twice with observations arriving in between, and show the original context
    before and after: byte for byte the same. Runs in a throwaway ledger. Deterministic."""
    spec = json.loads(Path(spec_path).read_text())
    pol = OC.make_policy(spec.get("policy") or {})
    with tempfile.TemporaryDirectory(prefix="memelab_outcomes_demo_") as d:
        con = OL.connect(Path(d) / "ledger.sqlite")
        rec = OL.record_signals(con, spec["signals"]["signals"], pol, now=spec["recorded_at"], is_fixture=True)
        first = OL.signals(con)[0]
        sid = first["signal_id"]
        before = con.execute("SELECT body_json, body_sha256 FROM ledger_entries WHERE kind='SIGNAL' AND signal_id=?", (sid,)).fetchone()
        before_all = [(r[0], r[1]) for r in con.execute("SELECT entry_key, body_sha256 FROM ledger_entries WHERE kind='SIGNAL' ORDER BY seq")]
        runs = []
        for ev in spec["evaluations"]:
            obs = OL.add_observations(con, ev["observations"], pol, now=ev["now"])
            s = OL.evaluate_all(con, as_of=ev["as_of"], pol=pol, now=ev["now"])
            runs.append((ev, obs, s, _outcome_table(con, ev["label"])))
        again = OL.evaluate_all(con, as_of=spec["evaluations"][-1]["as_of"], pol=pol, now=spec["evaluations"][-1]["now"])
        after = con.execute("SELECT body_json, body_sha256 FROM ledger_entries WHERE kind='SIGNAL' AND signal_id=?", (sid,)).fetchone()
        after_all = [(r[0], r[1]) for r in con.execute("SELECT entry_key, body_sha256 FROM ledger_entries WHERE kind='SIGNAL' ORDER BY seq")]
        hist = [f"#{o['_seq']} as of {_iso(o['evaluated_as_of'])} {o['revision_reason'] or 'FIRST':<15} " + OC.render_outcome(o)
                for o in OL.outcome_history(con, sid)]
        cov = OL.report(con, pol)
        ver = OL.verify(con)
        try:
            con.execute("UPDATE ledger_entries SET body_json='{}' WHERE kind='SIGNAL'")
            upd = "UPDATE accepted (this would be a defect)"
        except sqlite3.DatabaseError as e:
            upd = f"UPDATE refused by the ledger: {e}"
        con.close()
    same = before[0] == after[0] and before[1] == after[1] and before_all == after_all
    parts = ["# Phase 16 sample: signal ledger and forward evaluation on an invented fixture", "", WATERMARK, "",
             f"Reproduce: `python -m memelab social evaluate demo --fixture {spec_path}`", "",
             "Throwaway ledger. Five signals are recorded at emission (emitted, rejected and suppressed alike), then evaluated twice: "
             f"at {_iso(spec['evaluations'][0]['as_of'])} and at {_iso(spec['evaluations'][1]['as_of'])}, with new and revised price "
             "observations arriving in between. Positions are hypothetical (500 USD evaluation size, not a recommendation).", "",
             f"Recorded: {len(rec['appended'])} signal(s), refused {len(rec['refused'])}.", "",
             f"## Signal snapshot before evaluation ({sid})", "", f"context body sha256 {before[1]}", "", "```json",
             json.dumps(json.loads(before[0]), indent=1, sort_keys=True), "```", ""]
    for ev, obs, s, table in runs:
        parts += [f"## {ev['label'].capitalize()}", "",
                  f"Observations appended {obs['appended']}, duplicate {obs['duplicate']}, refused {len(obs['refused'])}.", "",
                  "```", render_run(s).rstrip(), "", *table, "```", ""]
    parts += ["## Same evaluation repeated", "", "```", render_run(again).rstrip(), "```", "",
              f"## Signal snapshot after two evaluations ({sid})", "", f"context body sha256 {after[1]}", "",
              f"Original context unchanged, byte for byte, for all {len(after_all)} signals: {'yes' if same else 'NO'}.", "",
              f"Attempted rewrite: {upd}", "",
              f"## Outcome entries for {sid}", "", "```", *hist, "```", "",
              "## Outcome coverage", "", "```", OC.render_report(cov).rstrip(), "```", "",
              "## Ledger check", "", f"entries {ver['entries']}, hash chain and body hashes {'OK' if ver['ok'] else 'BROKEN'}, head {ver['head_sha256']}", "",
              WATERMARK, ""]
    return "\n".join(parts)


def cmd_demo(a) -> None:
    try:
        md = demo_markdown(a.fixture)
    except (OC.OutcomeError, ValueError, KeyError) as e:
        _fail(str(e))
    if a.out:
        Path(a.out).write_text(md)
    print(md, end="")


def add_parser(ssp) -> None:
    p = ssp.add_parser("evaluate", help="immutable signal ledger and forward 1h/6h/24h/72h/7d outcomes (Phase 16)")
    sp = p.add_subparsers(dest="evaluate_cmd", required=True)
    q = sp.add_parser("record", help="record signals with what was known at emission")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--signals"); g.add_argument("--feed-json"); g.add_argument("--research-json")
    q.add_argument("--generated-at"); q.add_argument("--now"); q.add_argument("--ledger"); q.add_argument("--fixture", action="store_true")
    q.set_defaults(fn=cmd_record)
    q = sp.add_parser("observe", help="append dated market observations")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--prices"); g.add_argument("--from-db")
    q.add_argument("--now"); q.add_argument("--ledger")
    q.set_defaults(fn=cmd_observe)
    q = sp.add_parser("run", help="append outcomes that matured or changed")
    q.add_argument("--as-of"); q.add_argument("--now"); q.add_argument("--ledger"); q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_run)
    q = sp.add_parser("annotate", help="append a later fact about a signal")
    q.add_argument("--signal", required=True); q.add_argument("--kind", required=True, choices=list(OC.ANNOTATION_KINDS))
    q.add_argument("--reason", required=True); q.add_argument("--at"); q.add_argument("--now"); q.add_argument("--ledger")
    q.set_defaults(fn=cmd_annotate)
    q = sp.add_parser("show", help="original context and outcome entries of one signal")
    q.add_argument("--signal", required=True); q.add_argument("--as-of"); q.add_argument("--ledger")
    q.set_defaults(fn=cmd_show)
    q = sp.add_parser("report", help="outcome coverage and reasons for exclusion")
    q.add_argument("--ledger"); q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_report)
    q = sp.add_parser("verify", help="check the hash chain and the signal context hashes")
    q.add_argument("--ledger")
    q.set_defaults(fn=cmd_verify)
    q = sp.add_parser("demo", help="fixture snapshot before and after two evaluations (watermarked)")
    q.add_argument("--fixture", required=True); q.add_argument("--out")
    q.set_defaults(fn=cmd_demo)

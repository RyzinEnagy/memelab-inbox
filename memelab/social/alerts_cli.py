"""Phase 15 CLI: research-only alerts over the Phase 14 feed.

  social alerts run        [--db PATH | --feed-json FILE | --fixture SPEC] [--as-of T] [--send] [--slot daily|weekly]
                           [--state PATH] [--config PATH] [--outbox DIR] [--json]
                           Dry run unless --send. --send needs notifications_opt_in and send_enabled in the private config;
                           without remote credentials it still writes the local outbox and says nothing was sent.
  social alerts status     [--mode dry_run|send] [--state PATH] [--json]   readable delivery state and ledger
  social alerts reset-cooldown --key COOLDOWN_KEY --reason TEXT [--mode send|dry_run] [--state PATH]
  social alerts schedule   [--template daily|weekly] [--after T] [--count N]   next fire times (templates are not enabled)
  social alerts preflight  [--db PATH] [--now T]   paid-API spend today against the per-provider ceilings
  social alerts demo       --fixture SPEC [--out FILE]   fixture alert, deduped second run, delivery state (watermarked)

Exit codes: 0 done (including no alerts and no-op runs), 2 usage or configuration error.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from . import alerts_core as AC, alerts_engine as AE, alerts_schedule as AS, alerts_transport as AT


def _policy(cfg: dict) -> dict:
    return AC.make_policy(cfg.get("policy") or {})


def _feed_from_fixture(spec_path: str, as_of: float | None, tz: str) -> dict:
    from . import feed_cli as FCLI, feed_core as FC
    inp, _ = FCLI._fixture_input(spec_path, as_of)
    return FC.build(inp, tz=tz, fixture_demo=True)


def _feed(a, policy: dict, now: float) -> dict:
    from . import feed_core as FC, feed_store as FS
    if a.fixture:
        return _feed_from_fixture(a.fixture, now, policy["tz"])
    if a.feed_json:
        doc = json.loads(Path(a.feed_json).read_text())
        if doc.get("schema") != FC.SCHEMA:
            raise AC.AlertError(f"--feed-json must be a {FC.SCHEMA} document")
        return doc
    from .. import db
    inp = FS.load_from_path(a.db or str(db.DB_PATH), as_of=now)
    return FC.build(inp, tz=policy["tz"])


def _mode(a, cfg: dict) -> str:
    if not a.send:
        return "dry_run"
    missing = [k for k in ("notifications_opt_in", "send_enabled") if cfg.get(k) is not True]
    if missing:
        raise AC.AlertError("--send refused: the private alert config does not set " + " and ".join(missing)
                            + " to true. Run without --send for a dry run.")
    return "send"


def cmd_run(a) -> None:
    try:
        cfg = AT.load_config(a.config)
        policy = _policy(cfg)
        mode = _mode(a, cfg)
        now = AC_time(a.as_of)
        feed = _feed(a, policy, now)
        if a.fixture and a.as_of is None:
            now = float(feed["as_of"])
        outbox = a.outbox or cfg.get("outbox") or str(AE.default_outbox())
        transports, notes = AT.build_transports(cfg, outbox=outbox) if mode == "send" else ([AT.FileSink(outbox)], [])
        con = AE.connect(a.state)
        slot = None
        if a.slot:
            t = AS.TEMPLATES[a.slot]
            key = AS.due_slot(t, now) or "before-first-slot"
            slot = (a.slot, key)
        out = AE.run(con, feed=feed, policy=policy, mode=mode, now=now, transports=transports, slot=slot)
        out["transport_notes"] = notes
    except (AC.AlertError, AT.ConfigError) as e:
        print(f"alerts: {e}", file=sys.stderr)
        raise SystemExit(2)
    if a.json:
        print(json.dumps(out, sort_keys=True, default=str))
        return
    txt = AE.render_run(out, policy["tz"])
    for n in notes:
        txt += f"{n['transport']}: {n['status']} ({n['detail']}); nothing sent through it.\n"
    print(txt, end="")


def AC_time(v) -> float:
    from . import feed_core as FC
    return FC.parse_time(v) if v else float(int(time.time()))


def cmd_status(a) -> None:
    try:
        con = AE.connect(a.state)
        view = AE.state_view(con, mode=a.mode)
    except AC.AlertError as e:
        print(f"alerts: {e}", file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(view, sort_keys=True, default=str) if a.json else AE.render_state(view), end="" if not a.json else "\n")


def cmd_reset(a) -> None:
    con = AE.connect(a.state)
    n = AE.reset_cooldown(con, a.mode, a.key, AC_time(None), a.reason)
    print(f"cooldown reset for {a.key} ({a.mode}); {n} earlier alert(s) under that key stay in the ledger")


def cmd_schedule(a) -> None:
    after = AC_time(a.after)
    names = [a.template] if a.template else list(AS.TEMPLATES)
    for n in names:
        t = AS.TEMPLATES[n]
        print(f"{n}: {t['name']} ({'ENABLED' if t['enabled'] else 'not enabled'}; needs {', '.join(t['requires'])}); {t['cron']}")
        for r in AS.next_runs(t, after, a.count):
            print(f"  {r['local']}  =  {r['utc']}  slot {r['slot']}")


PAID_UPSTREAM = {"x_api", "llm"}   # each call costs money; at a ceiling of 0 no refresh step may call them


def preflight(db_path: str, policy: dict, now: float) -> dict:
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    groups = {"x_api": "x_api:%", "llm": "llm:%", "telegram_bot": "telegram_bot:%"}
    out = {"billing_day_utc": day, "providers": {}}
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        has = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='social_api_spend'").fetchone()
    except sqlite3.Error:
        con, has = None, None
    for g, pat in groups.items():
        ceiling = float(policy["cost_ceilings_usd_per_day"].get(g, 0.0))
        spent = 0.0
        if has:
            spent = con.execute("SELECT COALESCE(SUM(est_cost_usd),0) FROM social_api_spend WHERE mode='live' AND billing_day=? AND connector LIKE ?",
                                (day, pat)).fetchone()[0]
        allowed = spent < ceiling if g in PAID_UPSTREAM else spent <= ceiling
        out["providers"][g] = {"spent_usd": round(spent, 4), "ceiling_usd": ceiling, "refresh_allowed": allowed, "paid": g in PAID_UPSTREAM,
                               "ledger": "present" if has else "absent"}
    if con:
        con.close()
    return out


def cmd_preflight(a) -> None:
    from .. import db
    cfg = AT.load_config(a.config)
    policy = _policy(cfg)
    r = preflight(a.db or str(db.DB_PATH), policy, AC_time(a.now))
    print(f"Paid-API spend for UTC day {r['billing_day_utc']} against per-provider daily ceilings:")
    for g, v in r["providers"].items():
        print(f"  {g}: spent {v['spent_usd']} USD, ceiling {v['ceiling_usd']} USD, refresh {'allowed' if v['refresh_allowed'] else 'SKIPPED'}"
              f" (spend ledger {v['ledger']})")


def demo_markdown(spec_path: str) -> str:
    """Fixture alert, then a second run on a later snapshot of the same data (deduped), then the delivery state.
    Runs in a throwaway state file; dry run, file sink only. Deterministic."""
    from . import feed_cli as FCLI, feed_core as FC
    spec = json.loads(Path(spec_path).read_text())
    policy = AC.make_policy(spec.get("policy") or {})
    t0 = FC.parse_time(spec["as_of"])
    inp, _ = FCLI._fixture_input(spec_path, t0)
    feed1 = FC.build(inp, tz=policy["tz"], fixture_demo=True)
    inp2 = json.loads(json.dumps(inp))
    inp2["snapshot"]["run_id"] = inp["snapshot"]["run_id"] + 100   # stands for the next snapshot holding the same evidence
    later = t0 + 2 * 3600
    inp2["as_of"] = later
    feed2 = FC.build(inp2, tz=policy["tz"], fixture_demo=True)
    with tempfile.TemporaryDirectory(prefix="memelab_alerts_demo_") as d:
        con = AE.connect(Path(d) / "state.sqlite")
        sink = [AT.FileSink(Path(d) / "outbox")]
        r1 = AE.run(con, feed=feed1, policy=policy, mode="dry_run", now=t0, transports=sink)
        texts = [AC.render_text(json.loads(con.execute("SELECT alert_json FROM alert_events WHERE alert_id=?", (i,)).fetchone()[0]), policy["tz"])
                 for i in r1["evaluation"]["new"]]
        r2 = AE.run(con, feed=feed2, policy=policy, mode="dry_run", now=later, transports=sink)
        view = AE.state_view(con)
        con.close()
    parts = ["# Phase 15 sample: research alerts on an invented fixture", "", FC.WATERMARK, "",
             f"Reproduce: `python -m memelab social alerts demo --fixture {spec_path}`", "",
             "Dry run with the local file sink only, in a throwaway state file. Run 2 reads a later snapshot that carries the same evidence.", "",
             "## Run 1", "", "```", AE.render_run(r1, policy["tz"]).rstrip(), "```", ""]
    for t in texts:
        parts += ["### Alert text", "", "```", t.rstrip(), "```", ""]
    parts += ["## Run 2 (same evidence, later snapshot)", "", "```", AE.render_run(r2, policy["tz"]).rstrip(), "```", "",
              "## Delivery state", "", "```", AE.render_state(view, policy["tz"]).rstrip(), "```", "", FC.WATERMARK, ""]
    return "\n".join(parts)


def cmd_demo(a) -> None:
    try:
        md = demo_markdown(a.fixture)
    except (AC.AlertError, ValueError) as e:
        print(f"alerts demo: {e}", file=sys.stderr)
        raise SystemExit(2)
    if a.out:
        Path(a.out).write_text(md)
    print(md, end="")


def add_parser(ssp) -> None:
    p = ssp.add_parser("alerts", help="research-only alerts over the feed: dry run by default, explicit send, ledger (Phase 15)")
    sp = p.add_subparsers(dest="alerts_cmd", required=True)
    q = sp.add_parser("run", help="evaluate the feed and deliver alerts (dry run unless --send)")
    q.add_argument("--db"); q.add_argument("--feed-json"); q.add_argument("--fixture"); q.add_argument("--as-of")
    q.add_argument("--send", action="store_true"); q.add_argument("--dry-run", action="store_true", help="the default; kept for scripts")
    q.add_argument("--slot", choices=list(AS.TEMPLATES)); q.add_argument("--state"); q.add_argument("--config"); q.add_argument("--outbox")
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_run)
    q = sp.add_parser("status", help="readable delivery state and ledger")
    q.add_argument("--mode", choices=["dry_run", "send"]); q.add_argument("--state"); q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_status)
    q = sp.add_parser("reset-cooldown", help="end a cooldown early (recorded with a reason)")
    q.add_argument("--key", required=True); q.add_argument("--reason", required=True); q.add_argument("--mode", default="send", choices=["dry_run", "send"])
    q.add_argument("--state")
    q.set_defaults(fn=cmd_reset)
    q = sp.add_parser("schedule", help="next fire times of the daily and weekly templates (not enabled)")
    q.add_argument("--template", choices=list(AS.TEMPLATES)); q.add_argument("--after"); q.add_argument("--count", type=int, default=5)
    q.set_defaults(fn=cmd_schedule)
    q = sp.add_parser("preflight", help="paid-API spend today against per-provider ceilings (read only)")
    q.add_argument("--db"); q.add_argument("--now"); q.add_argument("--config")
    q.set_defaults(fn=cmd_preflight)
    q = sp.add_parser("demo", help="fixture alert, deduped second run and delivery state (watermarked)")
    q.add_argument("--fixture", required=True); q.add_argument("--out")
    q.set_defaults(fn=cmd_demo)

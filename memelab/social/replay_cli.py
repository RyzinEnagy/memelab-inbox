"""Phase 17 CLI: causal historical replay with matched controls.

  social replay inventory [--db PATH] [--inbox DIR] [--candle-availability capture|provider] [--json]
                          what history exists: posts, wallet events, trending lists, price windows (read-only)
  social replay run       (--input FILE | --db PATH [--inbox DIR] | --synthetic) [--seed N] [--policy FILE]
                          [--candle-availability capture|provider] [--no-leakage-check] [--out FILE] [--json]
                          replay the four strategies with train/validation/test splits and print the validation report
  social replay demo      [--seed N] [--out FILE]   the synthetic fixture replay, watermarked, with the leakage check
  social replay export    (--db PATH [--inbox DIR]) --out FILE   write the assembled replay input (no post text is ever included)

Exit codes: 0 done (including "insufficient sample/data"), 1 the leakage check found a difference, 2 usage or input error.
Nothing here fetches, trades or writes into tracked paths unless --out names one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import replay_core as RC, replay_sources as RS, replay_synth as SY

WATERMARK = ("FIXTURE DEMO: a synthetic, seeded world. Tokens, sources, posts, wallets, trending lists and prices are invented. "
             "Nothing here is evidence about any real token or source, and nothing is a trade record.")
REAL_NOTE = ("Real stored history. Where coverage is poor the verdict is 'insufficient sample/data' or 'cannot validate yet'; "
             "nothing is extrapolated beyond the data.")


def _fail(msg: str) -> None:
    print(f"social replay: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _assemble(a) -> dict:
    if getattr(a, "input", None):
        try:
            return json.loads(Path(a.input).read_text())
        except (OSError, ValueError) as e:
            _fail(f"cannot read {a.input}: {e}")
    if getattr(a, "synthetic", False):
        return SY.build({"seed": a.seed} if a.seed is not None else None)
    parts = []
    if a.db:
        if not Path(a.db).exists():
            _fail(f"no database at {a.db}")
        parts.append(RS.from_db(a.db))
    if a.inbox:
        if not Path(a.inbox).is_dir():
            _fail(f"no folder at {a.inbox}")
        parts.append(RS.from_inbox(a.inbox, candle_availability=a.candle_availability))
    if not parts:
        _fail("give --input, --synthetic, or --db and/or --inbox")
    return RS.merge(*parts, candle_availability=a.candle_availability)


def _policy(a) -> dict | None:
    if getattr(a, "policy", None):
        try:
            return json.loads(Path(a.policy).read_text())
        except (OSError, ValueError) as e:
            _fail(f"cannot read policy {a.policy}: {e}")
    return None


def report(doc: dict, policy: dict | None = None, *, leakage: bool = True) -> tuple[str, dict, dict | None]:
    res = RC.run(doc, policy)
    leak = RC.leakage_check(doc, policy) if leakage else None
    wm = WATERMARK if doc.get("is_fixture") else REAL_NOTE
    return RC.render(res, leak=leak, watermark=wm), res, leak


def cmd_inventory(a) -> None:
    doc = _assemble(a)
    inv = RS.inventory(doc)
    print(json.dumps(inv, indent=1, sort_keys=True) if a.json else RS.render_inventory(inv), end="" if not a.json else "\n")


def cmd_run(a) -> None:
    doc = _assemble(a)
    if doc.get("as_of") is None:
        _fail("the assembled history has no dated record at all")
    try:
        md, res, leak = report(doc, _policy(a), leakage=not a.no_leakage_check)
    except RC.ReplayError as e:
        _fail(str(e))
    if a.out:
        Path(a.out).write_text(json.dumps({"result": res, "leakage": leak}, indent=1, sort_keys=True, default=str) if a.json else md)
    print(json.dumps({"result": res, "leakage": leak}, indent=1, sort_keys=True, default=str) if a.json else md, end="" if not a.json else "\n")
    if leak is not None and not leak["ok"]:
        raise SystemExit(1)


def demo_markdown(seed: int | None = None) -> str:
    doc = SY.build({"seed": seed} if seed is not None else None)
    md, _res, leak = report(doc)
    head = (f"Reproduce: `python -m memelab social replay demo{'' if seed is None else f' --seed {seed}'}`\n\n"
            "Synthetic world with planted pumps, informative and noise posts, reposts, ingest duplicates, leakage canaries "
            "(posts published before a pump but first available after it), a huge winner, delisted and illiquid tokens, "
            "revised candles and a source that sells right after posting.\n\n")
    return md.replace("\n" + WATERMARK + "\n", "\n" + WATERMARK + "\n\n" + head.rstrip("\n") + "\n", 1)


def cmd_demo(a) -> None:
    md = demo_markdown(a.seed)
    if a.out:
        Path(a.out).write_text(md)
    print(md, end="")
    if "No leakage detected: yes" not in md:
        raise SystemExit(1)


def cmd_export(a) -> None:
    doc = _assemble(a)
    Path(a.out).write_text(json.dumps(doc, sort_keys=True))
    print(f"wrote {a.out}: posts {len(doc['posts'])}, wallet events {len(doc['wallet_events'])}, trending {len(doc['trending'])}, "
          f"candles {len(doc['candles'])}, points {len(doc['points'])}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("replay", help="causal historical replay with matched controls and honest verdicts (Phase 17)")
    sp = p.add_subparsers(dest="replay_cmd", required=True)

    def src(q, allow_synth=True):
        q.add_argument("--db"); q.add_argument("--inbox"); q.add_argument("--input")
        q.add_argument("--candle-availability", choices=["capture", "provider"], default="capture")
        if allow_synth:
            q.add_argument("--synthetic", action="store_true")
            q.add_argument("--seed", type=int)

    q = sp.add_parser("inventory", help="what history exists (read-only)")
    src(q)
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_inventory)
    q = sp.add_parser("run", help="replay the four strategies and print the validation report")
    src(q)
    q.add_argument("--policy"); q.add_argument("--out"); q.add_argument("--json", action="store_true")
    q.add_argument("--no-leakage-check", action="store_true")
    q.set_defaults(fn=cmd_run)
    q = sp.add_parser("demo", help="synthetic fixture replay with the leakage check (watermarked)")
    q.add_argument("--seed", type=int); q.add_argument("--out")
    q.set_defaults(fn=cmd_demo)
    q = sp.add_parser("export", help="write the assembled replay input")
    src(q, allow_synth=False)
    q.add_argument("--out", required=True)
    q.set_defaults(fn=cmd_export)

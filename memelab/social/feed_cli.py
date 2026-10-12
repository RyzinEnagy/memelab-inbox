"""Phase 14 CLI: read-only intelligence feed over stored social data.

  social brief          [--as-of T] [--tz ZONE] [--db PATH] [--run ID] [--include-fixtures] [filters] [--json] [--report-dir DIR]
  social trader-digest  (same options)
  social feed           (same options; filters: --chain C --token CONTRACT|CHAIN:CONTRACT|$SYM --source ID|HANDLE
                         --since T --until T --risk any|none|FLAG --min-priority HIGH|MEDIUM|LOW)
  social feed-demo      --fixture FILE [--out FILE] [--json-out FILE] [--tz ZONE]
                         builds a throwaway store from an invented fixture spec, reads it back through the real read path and
                         prints all three views, watermarked

Each of brief, trader-digest and feed also takes --fixture FILE to run that one view on a fixture spec.

Nothing here writes to the lab database, sends a notification or schedules anything. --report-dir writes
<stamp>_social_<view>.md and .json into the given folder (the default is stdout only).
Exit codes: 0 rendered (including "no supported high-priority observations"), 2 usage error.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

from . import feed_core as FC, feed_store as FS


def _filters(a) -> dict:
    return FC.make_filters(chain=a.chain, token=a.token, source=a.source, since=a.since, until=a.until, risk=a.risk, min_priority=a.min_priority)


def _fixture_input(path: str, as_of: float | None) -> tuple[dict, dict]:
    from . import feed_demo as FD
    spec = json.loads(Path(path).read_text())
    if not spec.get("is_fixture"):
        raise FC.FeedError("--fixture reads fixture files only")
    with tempfile.TemporaryDirectory(prefix="memelab_feed_demo_") as d:
        FD.build_db(spec, Path(d) / "demo.sqlite")
        when = as_of if as_of is not None else FC.parse_time(spec["as_of"])
        inp = FS.load_from_path(str(Path(d) / "demo.sqlite"), as_of=when, include_fixtures=True)
    inp["model"] = {"status": "not checked in the fixture demo"}
    return inp, spec


def _input(a) -> tuple[dict, bool]:
    as_of = FC.parse_time(a.as_of) if a.as_of else None
    if getattr(a, "fixture", None):
        inp, _ = _fixture_input(a.fixture, as_of)
        return inp, True
    as_of = as_of if as_of is not None else float(int(time.time()))
    if a.db:
        return FS.load_from_path(a.db, as_of=as_of, include_fixtures=a.include_fixtures, run_id=a.run), False
    from .. import db
    return FS.load_from_path(str(db.DB_PATH), as_of=as_of, include_fixtures=a.include_fixtures, run_id=a.run), False


def _emit(doc: dict, view: str, a) -> None:
    from .. import report
    md = report.render_social_feed(doc, view)
    if a.report_dir:
        d = Path(a.report_dir)
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M", time.gmtime(doc["as_of"]))
        name = f"{stamp}_social_{view.replace('-', '_')}{'_FIXTURE' if doc['fixture'] else ''}"
        (d / f"{name}.md").write_text(md)
        (d / f"{name}.json").write_text(FC.to_json(doc))
        print(f"Report: {d / (name + '.md')}", file=sys.stderr)
    print(FC.to_json(doc) if a.json else md, end="")


def cmd_view(a) -> None:
    try:
        inp, fx = _input(a)
        doc = FC.build(inp, tz=a.tz, filters=_filters(a), options={"window_hours": a.window_hours}, fixture_demo=fx)
    except FC.FeedError as e:
        print(f"feed: {e}", file=sys.stderr)
        raise SystemExit(2)
    _emit(doc, a.view, a)


def demo_markdown(spec_path: str, tz: str | None = None) -> tuple[str, dict]:
    """All three views of one fixture, in one document. Deterministic: the sample file in the repo is this output."""
    inp, spec = _fixture_input(spec_path, None)
    zone = tz or spec.get("tz") or "UTC"
    docs = {v: FC.build(inp, tz=zone, fixture_demo=True) for v in FC.VIEWS}
    filt = FC.build(inp, tz=zone, fixture_demo=True, filters=FC.make_filters(risk="any"))
    parts = ["# Phase 14 sample: social intelligence feed on an invented fixture", "", FC.WATERMARK, "",
             f"Reproduce: `python -m memelab social feed-demo --fixture {spec_path}`", "",
             "The fixture is written into a throwaway SQLite store through the real store functions, snapshotted by the real narrative engine "
             "and read back by the same read path the lab database uses. Section headings below are shifted one level down.", ""]
    for v, title in (("brief", "View 1: morning brief"), ("trader-digest", "View 2: trader conversation digest"), ("feed", "View 3: feed filtered to --risk any")):
        body = FC.render(filt if v == "feed" else docs[v], v)
        parts += [f"## {title}", ""] + ["#" + ln if ln.startswith("#") else ln for ln in body.splitlines()] + [""]
    return "\n".join(parts).rstrip() + "\n", docs["brief"]


def cmd_demo(a) -> None:
    try:
        md, doc = demo_markdown(a.fixture, a.tz)
    except FC.FeedError as e:
        print(f"feed-demo: {e}", file=sys.stderr)
        raise SystemExit(2)
    if a.out:
        Path(a.out).write_text(md)
    if a.json_out:
        Path(a.json_out).write_text(FC.to_json(doc))
    print(md, end="")


def add_parser(ssp) -> None:
    for view, help_ in (("brief", "last-24-hour narrative-first morning brief (read only)"),
                        ("trader-digest", "who said what per token: stances, disclosed positions, changes, disagreements (read only)"),
                        ("feed", "searchable feed filtered by chain, token, source, time or risk (read only)")):
        q = ssp.add_parser(view, help=help_)
        q.add_argument("--as-of", help="epoch seconds or ISO 8601 with offset (default: now)")
        q.add_argument("--tz", default="UTC", help="IANA zone for displayed times (stored times stay UTC)")
        q.add_argument("--db"); q.add_argument("--run", type=int, help="a specific narrative snapshot run")
        q.add_argument("--include-fixtures", action="store_true"); q.add_argument("--fixture", help="fixture spec (demo, watermarked)")
        q.add_argument("--window-hours", type=float, default=24.0)
        q.add_argument("--chain"); q.add_argument("--token"); q.add_argument("--source"); q.add_argument("--since"); q.add_argument("--until")
        q.add_argument("--risk"); q.add_argument("--min-priority", choices=list(FC.PRIORITIES))
        q.add_argument("--json", action="store_true"); q.add_argument("--report-dir")
        q.set_defaults(fn=cmd_view, view=view)
    q = ssp.add_parser("feed-demo", help="all three feed views on an invented fixture, through the real read path")
    q.add_argument("--fixture", required=True); q.add_argument("--out"); q.add_argument("--json-out"); q.add_argument("--tz")
    q.set_defaults(fn=cmd_demo)

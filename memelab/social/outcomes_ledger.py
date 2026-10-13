"""Phase 16: the append-only signal ledger (private SQLite, never the tracked lab database).

One journal table, ledger_entries, holds four kinds of entry in the order they were recorded:
  SIGNAL       the immutable context of one emitted, rejected or suppressed signal (outcomes_core.make_signal)
  OBSERVATION  one dated market observation (price point, candle, route quote, delisting), with when the lab had it
  ANNOTATION   a later fact about a signal: source deleted, identity revised, invalidated, note
  OUTCOME      one evaluation of one signal at one horizon; a changed result is a new entry that points at the old one
SQLite triggers refuse UPDATE and DELETE on the journal, every entry carries the sha256 of its body and of the previous
entry (a hash chain), and verify() recomputes both. Nothing is ever rewritten: a revised provider snapshot is a new
observation, a matured or revised outcome is a new outcome entry.

Default path data/private/signal_ledger.sqlite (gitignored), override MEMELAB_SIGNAL_LEDGER.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable

from . import outcomes_core as OC

STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger_entries (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL CHECK (kind IN ('SIGNAL','OBSERVATION','ANNOTATION','OUTCOME')),
  entry_key TEXT NOT NULL UNIQUE,
  signal_id TEXT, horizon_s INTEGER, chain TEXT, contract TEXT, t REAL, available_at REAL, status TEXT,
  supersedes_seq INTEGER,
  recorded_at REAL NOT NULL,
  body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL, prev_entry_sha256 TEXT NOT NULL, entry_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_le_signal ON ledger_entries(kind, signal_id, horizon_s, seq);
CREATE INDEX IF NOT EXISTS ix_le_token ON ledger_entries(kind, chain, contract, t);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'signal ledger is append-only: entries are never updated'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'signal ledger is append-only: entries are never deleted'); END;
"""
GENESIS = "0" * 64


def default_path() -> Path:
    env = os.environ.get("MEMELAB_SIGNAL_LEDGER")
    if env:
        return Path(env)
    from .. import db
    return Path(db.DB_PATH).parent / "private" / "signal_ledger.sqlite"


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    from .. import db
    p = Path(path) if path else default_path()
    if p.resolve() == Path(db.DB_PATH).resolve():
        raise OC.OutcomeError("the signal ledger never goes into the tracked lab database")
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), isolation_level=None)
    con.row_factory = sqlite3.Row
    con.executescript(STATE_SCHEMA)
    con.execute("INSERT OR IGNORE INTO ledger_meta(key, value) VALUES ('state_schema', 'memelab.social.signal_ledger/1')")
    return con


def _entry_sha(prev: str, kind: str, key: str, recorded_at: float, body_sha: str) -> str:
    return OC.sha([prev, kind, key, OC.r10(recorded_at), body_sha])


def _append(con, kind: str, key: str, body: dict, recorded_at: float, **cols) -> tuple[int, bool]:
    """Append one entry atomically. An existing entry_key is a no-op returning the existing seq."""
    con.execute("BEGIN IMMEDIATE")
    try:
        r = con.execute("SELECT seq FROM ledger_entries WHERE entry_key=?", (key,)).fetchone()
        if r is not None:
            con.execute("COMMIT")
            return r[0], False
        last = con.execute("SELECT entry_sha256 FROM ledger_entries ORDER BY seq DESC LIMIT 1").fetchone()
        prev = last[0] if last else GENESIS
        bj = OC.canon(body)
        bs = OC.sha(body)
        es = _entry_sha(prev, kind, key, recorded_at, bs)
        names = ["kind", "entry_key", "recorded_at", "body_json", "body_sha256", "prev_entry_sha256", "entry_sha256"] + list(cols)
        vals = [kind, key, recorded_at, bj, bs, prev, es] + list(cols.values())
        cur = con.execute(f"INSERT INTO ledger_entries({','.join(names)}) VALUES ({','.join('?' * len(names))})", vals)
        con.execute("COMMIT")
        return cur.lastrowid, True
    except BaseException:
        con.execute("ROLLBACK")
        raise


def _identity_view(ctx: dict) -> dict:
    """The context minus when it was recorded: re-recording the same signal later is a no-op, not a new signal."""
    c = json.loads(json.dumps(ctx))
    c.pop("context_sha256", None)
    c["times"].pop("captured_at", None)
    c["flags"] = [f for f in c.get("flags") or [] if f.get("flag") != "LATE_CAPTURE"]
    return c


# ---------- writes ----------

def record_signal(con, ctx: dict, *, now: float) -> dict:
    sid = ctx["signal_id"]
    r = con.execute("SELECT seq, body_json FROM ledger_entries WHERE kind='SIGNAL' AND signal_id=?", (sid,)).fetchone()
    if r is not None:
        old = json.loads(r["body_json"])
        if OC.sha(_identity_view(old)) != OC.sha(_identity_view(ctx)):
            raise OC.OutcomeError(f"signal {sid} is already recorded with a different context; the original is immutable "
                                  "(record a new signal or append an annotation instead)")
        return {"signal_id": sid, "seq": r["seq"], "appended": False}
    body = dict(ctx, context_sha256=OC.sha(ctx))
    tok = ctx["token"]
    seq, new = _append(con, "SIGNAL", "signal:" + sid, body, now, signal_id=sid, chain=tok.get("chain"), contract=tok.get("contract"),
                       t=ctx["times"]["generated_at"], available_at=ctx["times"]["captured_at"], status=ctx["disposition"])
    return {"signal_id": sid, "seq": seq, "appended": new}


def record_signals(con, raws: list[dict], pol: dict, *, now: float, is_fixture: bool = False) -> dict:
    out = {"appended": [], "already_recorded": [], "refused": []}
    for raw in raws:
        try:
            ctx = OC.make_signal(raw, pol, captured_at=now, is_fixture=is_fixture)
            r = record_signal(con, ctx, now=now)
        except OC.OutcomeError as e:
            out["refused"].append({"emitter_ref": raw.get("emitter_ref"), "reason": str(e)})
            continue
        out["appended" if r["appended"] else "already_recorded"].append(r["signal_id"])
    return out


def add_observations(con, raws: list[dict], pol: dict, *, now: float) -> dict:
    out = {"appended": 0, "duplicate": 0, "refused": []}
    for i, raw in enumerate(raws):
        try:
            body = OC.normalize_observation(raw, pol)
        except OC.OutcomeError as e:
            out["refused"].append({"index": i, "reason": str(e)})
            continue
        _, new = _append(con, "OBSERVATION", "obs:" + OC.sha(body), body, now, chain=body["chain"], contract=body["contract"],
                         t=body["t"], available_at=body["available_at"], status=body["kind"])
        out["appended" if new else "duplicate"] += 1
    return out


def annotate(con, signal_id: str, kind: str, *, reason: str, at: float, available_at: float, now: float) -> dict:
    kind = kind.upper()
    if kind not in OC.ANNOTATION_KINDS:
        raise OC.OutcomeError(f"annotation kind must be one of {OC.ANNOTATION_KINDS}")
    if not reason:
        raise OC.OutcomeError("an annotation needs a reason")
    if con.execute("SELECT 1 FROM ledger_entries WHERE kind='SIGNAL' AND signal_id=?", (signal_id,)).fetchone() is None:
        raise OC.OutcomeError(f"no signal {signal_id}")
    body = {"signal_id": signal_id, "kind": kind, "reason": reason, "at": at, "available_at": available_at}
    seq, new = _append(con, "ANNOTATION", "ann:" + OC.sha(body), body, now, signal_id=signal_id, t=at, available_at=available_at, status=kind)
    return {"seq": seq, "appended": new}


# ---------- reads ----------

def signals(con) -> list[dict]:
    return [json.loads(r["body_json"]) | {"_seq": r["seq"]} for r in
            con.execute("SELECT seq, body_json FROM ledger_entries WHERE kind='SIGNAL' ORDER BY seq")]


def observations(con) -> list[dict]:
    return [json.loads(r["body_json"]) | {"seq": r["seq"]} for r in
            con.execute("SELECT seq, body_json FROM ledger_entries WHERE kind='OBSERVATION' ORDER BY seq")]


def annotations(con) -> list[dict]:
    return [json.loads(r["body_json"]) | {"seq": r["seq"]} for r in
            con.execute("SELECT seq, body_json FROM ledger_entries WHERE kind='ANNOTATION' ORDER BY seq")]


def latest_outcomes(con) -> dict[tuple[str, int], dict]:
    out = {}
    for r in con.execute("SELECT seq, signal_id, horizon_s, body_json FROM ledger_entries WHERE kind='OUTCOME' ORDER BY seq"):
        out[(r["signal_id"], r["horizon_s"])] = json.loads(r["body_json"]) | {"_seq": r["seq"]}
    return out


def outcome_history(con, signal_id: str) -> list[dict]:
    return [json.loads(r["body_json"]) | {"_seq": r["seq"], "_recorded_at": r["recorded_at"]} for r in
            con.execute("SELECT seq, recorded_at, body_json FROM ledger_entries WHERE kind='OUTCOME' AND signal_id=? ORDER BY horizon_s, seq", (signal_id,))]


def last_evaluated_as_of(con) -> float | None:
    r = con.execute("SELECT MAX(t) FROM ledger_entries WHERE kind='OUTCOME'").fetchone()
    return r[0]


def _strip(ctx: dict) -> dict:
    return {k: v for k, v in ctx.items() if k not in ("context_sha256", "_seq")}


# ---------- evaluation ----------

def _revision_reason(prior: dict | None, new: dict) -> str | None:
    if prior is None:
        return None
    if prior["status"] == "PENDING" and new["status"] != "PENDING":
        return "MATURED"
    if prior["status"] != new["status"]:
        return "STATUS_CHANGED"
    if sorted(prior.get("inputs") or []) != sorted(new.get("inputs") or []):
        return "INPUTS_REVISED"
    return "RECOMPUTED"


def compute(con, *, as_of: float, pol: dict) -> list[dict]:
    """Every (signal, horizon) outcome from what was visible at as_of, without writing. Same ledger + as_of -> same list."""
    obs, anns = observations(con), annotations(con)
    res = []
    for ctx in signals(con):
        c = _strip(ctx)
        for h in c["assumptions"]["horizons_s"]:
            o = OC.evaluate(c, h, obs, anns, as_of, pol)
            o["evaluated_as_of"] = as_of
            res.append(o)
    return res


def evaluate_all(con, *, as_of: float, pol: dict, now: float, evaluator: Callable[..., dict] | None = None) -> dict:
    """Append outcomes that are new or changed since the latest entry for that (signal, horizon). Safe to repeat and to
    resume after a crash: work is ordered by signal seq and horizon, every append is its own transaction, and an
    unchanged outcome is never appended twice. Evaluation time may not go backwards (use compute() to replay)."""
    last = last_evaluated_as_of(con)
    if last is not None and as_of < last:
        raise OC.OutcomeError(f"evaluation time {as_of} is before the latest evaluation ({last}); replay with 'show --as-of' instead")
    ev = evaluator or OC.evaluate
    obs, anns = observations(con), annotations(con)
    latest = latest_outcomes(con)
    summary = {"as_of": as_of, "evaluated": 0, "appended": 0, "unchanged": 0, "by_status": {s: 0 for s in OC.STATUSES},
               "appended_by_reason": {}, "signals": 0}
    for ctx in signals(con):
        summary["signals"] += 1
        c = _strip(ctx)
        for h in c["assumptions"]["horizons_s"]:
            o = ev(c, h, obs, anns, as_of, pol)
            summary["evaluated"] += 1
            summary["by_status"][o["status"]] += 1
            prior = latest.get((c["signal_id"], h))
            cs = OC.content_sha(o)
            if prior is not None and OC.content_sha({k: v for k, v in prior.items() if k != "_seq"}) == cs:
                summary["unchanged"] += 1
                continue
            o["evaluated_as_of"] = as_of
            o["supersedes_seq"] = prior["_seq"] if prior else None
            o["revision_reason"] = _revision_reason(prior, o)
            key = "out:" + OC.sha([c["signal_id"], h, cs, o["supersedes_seq"]])
            seq, new = _append(con, "OUTCOME", key, o, now, signal_id=c["signal_id"], horizon_s=h, t=as_of, status=o["status"],
                               supersedes_seq=o["supersedes_seq"], chain=c["token"].get("chain"), contract=c["token"].get("contract"))
            if new:
                summary["appended"] += 1
                rr = o["revision_reason"] or "FIRST"
                summary["appended_by_reason"][rr] = summary["appended_by_reason"].get(rr, 0) + 1
                latest[(c["signal_id"], h)] = o | {"_seq": seq}
    return summary


def report(con, pol: dict) -> dict:
    ctxs = [_strip(c) for c in signals(con)]
    rev = con.execute("SELECT COUNT(*) FROM ledger_entries WHERE kind='OUTCOME' AND supersedes_seq IS NOT NULL").fetchone()[0]
    cov = OC.coverage(ctxs, {k: {kk: vv for kk, vv in v.items() if kk != "_seq"} for k, v in latest_outcomes(con).items()}, pol, revisions=rev)
    cov["last_evaluated_as_of"] = last_evaluated_as_of(con)
    cov["observations"] = con.execute("SELECT COUNT(*) FROM ledger_entries WHERE kind='OBSERVATION'").fetchone()[0]
    return cov


def verify(con) -> dict:
    """Recompute the hash chain, every body hash and every signal's context hash."""
    problems = []
    prev = GENESIS
    n = 0
    for r in con.execute("SELECT * FROM ledger_entries ORDER BY seq"):
        n += 1
        body = json.loads(r["body_json"])
        if OC.sha(body) != r["body_sha256"]:
            problems.append({"seq": r["seq"], "problem": "body hash mismatch"})
        if r["prev_entry_sha256"] != prev:
            problems.append({"seq": r["seq"], "problem": "chain broken (previous hash differs)"})
        if _entry_sha(r["prev_entry_sha256"], r["kind"], r["entry_key"], r["recorded_at"], r["body_sha256"]) != r["entry_sha256"]:
            problems.append({"seq": r["seq"], "problem": "entry hash mismatch"})
        if r["kind"] == "SIGNAL" and OC.sha({k: v for k, v in body.items() if k != "context_sha256"}) != body.get("context_sha256"):
            problems.append({"seq": r["seq"], "problem": "signal context hash mismatch"})
        prev = r["entry_sha256"]
    return {"entries": n, "ok": not problems, "problems": problems, "head_sha256": prev}


def dump(con) -> list[dict[str, Any]]:
    return [dict(r) for r in con.execute("SELECT * FROM ledger_entries ORDER BY seq")]

"""Append-only writes and point-in-time reads for bt_* tables.

Every write carries a content hash so re-ingesting the same payload is a no-op (idempotent), and a changed payload
becomes a new row (a new version), never an overwrite.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

from . import ENGINE_VERSION, schema
from .timeguard import ClockError, Series, utc_ts

INGEST_VERSION = "bt-ingest-1"

ROOT = Path(__file__).resolve().parents[2]
import os as _os
BT_DB_PATH = Path(_os.environ.get("MEMELAB_BT_DB", ROOT / "data" / "backtest" / "bt.sqlite"))
RAW_DIR = Path(_os.environ.get("MEMELAB_BT_RAW", ROOT / "data" / "backtest" / "raw"))
BUSY_TIMEOUT_S = 10.0     # wait this long for another writer; writers keep their transactions short (Phase 16, D7)


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Separate SQLite file for bt tables (default data/backtest/bt.sqlite, gitignored): the tracked lab database is
    never written by the backtesting package."""
    p = Path(path) if path else BT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=BUSY_TIMEOUT_S)
    con.row_factory = sqlite3.Row
    for attempt in range(8):                  # first use by several processes at once: setup statements can meet SQLITE_BUSY without waiting
        try:
            con.execute("PRAGMA journal_mode=WAL")
            schema.migrate(con)
            return con
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) and "busy" not in str(e) or attempt == 7:
                con.close()
                raise
            if con.in_transaction:
                con.rollback()
            time.sleep(0.05 * (2 ** attempt))
    return con


def save_raw(provider: str, payload: bytes) -> str:
    """Immutable raw shard keyed by its sha256; returns the raw_ref."""
    h = hashlib.sha256(payload).hexdigest()
    d = RAW_DIR / provider
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{h}.json"
    if not f.exists():
        f.write_bytes(payload)
    return f"raw/{provider}/{h}.json"


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(obj: Any) -> str:
    b = obj if isinstance(obj, (bytes, bytearray)) else canonical(obj).encode()
    return hashlib.sha256(b).hexdigest()


def ensure(con: sqlite3.Connection) -> None:
    schema.migrate(con)


def _insert(con: sqlite3.Connection, table: str, row: dict[str, Any]) -> tuple[int | None, bool]:
    """INSERT OR IGNORE on the table's unique key. Returns (id, inserted)."""
    row = {k: (canonical(v) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
    cols = list(row)
    cur = con.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(row.values()))
    if cur.rowcount == 1:
        return cur.lastrowid, True
    return None, False


def _check_times(**ts: float | None) -> None:
    for k, v in ts.items():
        if v is not None:
            utc_ts(v)


def record_observation(con, *, kind: str, provider: str, payload: Any, observed_at: float, available_at: float,
                       chain: str | None = None, mint: str | None = None, event_time: float | None = None,
                       value_num: float | None = None, value_text: str | None = None, value_state: str = "OBSERVED",
                       raw_source_id: str | None = None, origin_group: str | None = None, wallet: str | None = None,
                       pool_address: str | None = None, validity_until: float | None = None, supersedes_id: int | None = None,
                       raw_ref: str | None = None, confidence: str | None = None, slot: int | None = None, block_time: float | None = None) -> tuple[int | None, bool]:
    _check_times(observed_at=observed_at, available_at=available_at, event_time=event_time, validity_until=validity_until, block_time=block_time)
    if available_at < observed_at:
        raise ClockError("available_at earlier than observed_at")
    if mint is not None and chain is None:
        raise ValueError("a mint needs its chain (exact identity is {chain, mint})")
    return _insert(con, "bt_observations", dict(
        kind=kind, provider=provider, raw_source_id=raw_source_id, raw_payload_hash=sha256(payload), chain=chain, mint=mint,
        pool_address=pool_address, wallet=wallet, origin_group=origin_group, event_time=event_time, observed_at=observed_at,
        available_at=available_at, validity_until=validity_until, slot=slot, block_time=block_time, value_num=value_num,
        value_text=value_text, value_json=payload if isinstance(payload, (dict, list)) else None, value_state=value_state,
        confidence=confidence, raw_ref=raw_ref, ingest_version=INGEST_VERSION, supersedes_id=supersedes_id, recorded_at=time.time()))


def record_bar(con, *, chain: str, mint: str, pool_address: str, tf: int, start: float, o: float, h: float, l: float, c: float,
               volume_usd: float | None, observed_at: float, provider: str, provider_lag_s: float = 300.0,
               quality_flags: str | None = None, raw_ref: str | None = None, backfill_tolerance_s: float = 3600.0) -> tuple[int | None, bool]:
    """Store one closed bar. Availability rules:
    - a bar observed before it closed is partial and is refused;
    - the first stored version of a bar is available at end + provider_lag (market data was public then; this is a
      modeled time, flagged AVAIL_MODELED, plus BACKFILLED when we fetched it long after the close);
    - any later version with different values is available only from its own observed_at, so a provider revision can
      never change what an earlier decision saw."""
    _check_times(start=start, observed_at=observed_at)
    end = start + tf
    if observed_at < end:
        raise ClockError("bar observed before it closed (partial bar); not stored")
    body = dict(o=o, h=h, l=l, c=c, v=volume_usd)
    h_ = sha256(body)
    prev = con.execute("SELECT content_hash FROM bt_market_bars WHERE provider=? AND pool_address=? AND timeframe_s=? AND start=?",
                       (provider, pool_address, tf, start)).fetchall()
    flags = [f for f in (quality_flags or "").split(",") if f]
    if not prev:
        available_at = end + provider_lag_s
        flags.append("AVAIL_MODELED")
        if observed_at - end > backfill_tolerance_s:
            flags.append("BACKFILLED")
    elif any(r[0] == h_ for r in prev):
        return None, False
    else:
        available_at = observed_at
        flags.append("REVISION")
    return _insert(con, "bt_market_bars", dict(
        chain=chain, mint=mint, pool_address=pool_address, timeframe_s=tf, start=start, end=end, o=o, h=h, l=l, c=c,
        volume_usd=volume_usd, observed_at=observed_at, available_at=available_at, provider=provider, quality_flags=",".join(dict.fromkeys(flags)),
        raw_ref=raw_ref, content_hash=h_))


def record_pool_version(con, *, chain: str, pool_address: str, mint: str, pool_type: str, observed_at: float, source: str,
                        dex: str | None = None, dex_program: str | None = None, quote_mint: str | None = None,
                        pool_created_at: float | None = None, available_at: float | None = None, raw_ref: str | None = None):
    _check_times(observed_at=observed_at, pool_created_at=pool_created_at)
    body = dict(mint=mint, dex=dex, dex_program=dex_program, pool_type=pool_type, quote_mint=quote_mint, created=pool_created_at)
    return _insert(con, "bt_pool_versions", dict(chain=chain, pool_address=pool_address, mint=mint, dex=dex, dex_program=dex_program,
                   pool_type=pool_type, quote_mint=quote_mint, pool_created_at=pool_created_at, observed_at=observed_at,
                   available_at=available_at if available_at is not None else observed_at, source=source, raw_ref=raw_ref, content_hash=sha256(body)))


def record_asset_version(con, *, chain: str, mint: str, observed_at: float, source: str, symbol: str | None = None,
                         decimals: int | None = None, token_program: str | None = None, available_at: float | None = None, raw_ref: str | None = None):
    body = dict(symbol=symbol, decimals=decimals, token_program=token_program)
    return _insert(con, "bt_asset_versions", dict(chain=chain, mint=mint, symbol=symbol, decimals=decimals, token_program=token_program,
                   observed_at=observed_at, available_at=available_at if available_at is not None else observed_at, source=source,
                   raw_ref=raw_ref, content_hash=sha256(body)))


def record_universe_member(con, *, universe_id: str, chain: str, mint: str, basis: str, entered_at: float, symbol: str | None = None,
                           committed_by: float | None = None, source_commit: str | None = None, status_at_entry: str | None = None,
                           score_at_entry: float | None = None, fatal_flags: list | None = None, snapshot: dict | None = None, stage: str | None = None):
    _check_times(entered_at=entered_at, committed_by=committed_by)
    body = dict(chain=chain, mint=mint, basis=basis, entered_at=entered_at, status=status_at_entry, score=score_at_entry, fatal=fatal_flags, snap=snapshot, stage=stage)
    return _insert(con, "bt_universe_members", dict(universe_id=universe_id, chain=chain, mint=mint, symbol=symbol, basis=basis, entered_at=entered_at,
                   available_at=entered_at, committed_by=committed_by, source_commit=source_commit, status_at_entry=status_at_entry,
                   score_at_entry=score_at_entry, fatal_flags_json=fatal_flags, snapshot_json=snapshot, stage=stage, content_hash=sha256(body)))


def record_lifecycle(con, *, chain: str, mint: str, event: str, available_at: float, source: str, event_time: float | None = None, evidence: str | None = None):
    body = dict(event_time=event_time, available_at=available_at, source=source, evidence=evidence)
    return _insert(con, "bt_token_lifecycle", dict(chain=chain, mint=mint, event=event, event_time=event_time, available_at=available_at,
                   source=source, evidence=evidence, content_hash=sha256(body)))


# ---------------- experiment reproducibility ----------------

def code_sha(root: Path | None = None) -> str | None:
    root = root or Path(__file__).resolve().parents[2]
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "memelab"], capture_output=True, text=True, timeout=10).stdout.strip()
        return (sha + ("+dirty" if dirty else "")) if sha else None
    except Exception:
        return None


def package_hash(root: Path | None = None) -> str:
    """Content hash of the backtest package sources, so an uncommitted code change can never reuse an old run_id."""
    root = root or Path(__file__).resolve().parent
    h = hashlib.sha256()
    for f in sorted(root.rglob("*.py")):
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def register_run(con, config: dict, *, dataset_hash: str, seed: int | None = None) -> str:
    """Store the full experiment definition; run_id = sha256 of it. Same config + data + code -> same run_id."""
    cfg = dict(config)
    cfg.update(dataset_hash=dataset_hash, seed=seed, engine_version=ENGINE_VERSION, code_sha=cfg.get("code_sha") or code_sha(),
               package_hash=cfg.get("package_hash") or package_hash())
    run_id = sha256(cfg)
    trials = con.execute("SELECT COUNT(*) FROM bt_experiment_runs WHERE strategy_id=?", (cfg.get("strategy_id"),)).fetchone()[0]
    _insert(con, "bt_experiment_runs", dict(
        run_id=run_id, code_sha=cfg["code_sha"], dataset_hash=dataset_hash, label_definition=cfg.get("label_definition"),
        universe_definition=cfg.get("universe_definition"), discovery_rule=cfg.get("discovery_rule"), splits_json=cfg.get("splits"),
        embargo_policy=cfg.get("embargo_policy"), seed=seed, strategy_id=cfg.get("strategy_id"), strategy_version=cfg.get("strategy_version"),
        cost_model_version=cfg.get("cost_model_version"), engine_version=ENGINE_VERSION, baseline=cfg.get("baseline"), fees_json=cfg.get("fees"),
        concurrency_limit=cfg.get("concurrency_limit"), assumptions_json=cfg.get("assumptions"), config_json=cfg, trials_before=trials,
        created_at=time.time()))
    return run_id


def record_result(con, run_id: str, status: str, result: dict) -> str:
    h = sha256(result)
    _insert(con, "bt_run_results", dict(run_id=run_id, status=status, result_json=result, result_hash=h, created_at=time.time()))
    return h


# ---------------- reads ----------------

def observation_series(con, *, chain: str, mint: str, kind: str) -> Series:
    rows = con.execute("SELECT * FROM bt_observations WHERE chain=? AND mint=? AND kind=? ORDER BY available_at, id", (chain, mint, kind)).fetchall()
    return Series(dict(r) | {"value": r["value_num"] if r["value_num"] is not None else r["value_text"]} for r in rows)


def bars_asof(con, *, chain: str, mint: str, pool_address: str, tf: int, cutoff: float) -> list[dict]:
    """Bars of one pool that were closed and available at cutoff. For a bar fetched more than once, the version
    available at cutoff wins (a later revision never reaches an earlier cutoff)."""
    rows = con.execute("SELECT * FROM bt_market_bars WHERE chain=? AND mint=? AND pool_address=? AND timeframe_s=? AND available_at<=? "
                       "ORDER BY start, available_at, id", (chain, mint, pool_address, tf, cutoff)).fetchall()
    best: dict[float, dict] = {}
    for r in rows:
        best[r["start"]] = dict(r)
    return [best[k] for k in sorted(best)]


def pools_valid_at(con, *, chain: str, mint: str, cutoff: float) -> list[dict]:
    """Pools known at cutoff and created at or before cutoff. Today's pool list is never used for the past."""
    rows = con.execute("SELECT * FROM bt_pool_versions WHERE chain=? AND mint=? AND available_at<=? ORDER BY available_at, id", (chain, mint, cutoff)).fetchall()
    best: dict[str, dict] = {}
    for r in rows:
        best[r["pool_address"]] = dict(r)
    return [p for p in best.values() if p["pool_created_at"] is None or p["pool_created_at"] <= cutoff]


def universe_asof(con, universe_id: str, cutoff: float) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM bt_universe_members WHERE universe_id=? AND available_at<=? ORDER BY entered_at, id", (universe_id, cutoff))]

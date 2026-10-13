"""Private, gitignored store for exact third-party wording.

The main lab database (data/memelab.sqlite) is committed to the public repo, so it never holds verbatim post
text. When a later phase needs exact wording as evidence (D-010), it goes here instead:

    data/private/social_private.sqlite      (override with MEMELAB_PRIVATE_DB)

data/private/ is listed in .gitignore and *.sqlite* is ignored as well. Rows are keyed by content hash, carry a
retention deadline and are deleted by purge_expired(). Nothing in this module is exported to state/ or inbox/.
"""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .. import db

DEFAULT_RETENTION_DAYS = 30

PRIVATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS private_content (
  private_ref TEXT PRIMARY KEY,           -- 'sha256:<content_hash>'
  content_hash TEXT NOT NULL,
  platform TEXT, original_url TEXT,
  exact_text TEXT NOT NULL,
  reason TEXT NOT NULL,                   -- why exact wording is needed (evidence for claim X, ...)
  stored_at REAL NOT NULL,
  retain_until REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pc_retain ON private_content(retain_until);
CREATE TABLE IF NOT EXISTS private_model_responses (   -- raw model output (may quote the post), Phase 06
  cache_key TEXT PRIMARY KEY,
  provider TEXT NOT NULL, model TEXT NOT NULL, prompt_version TEXT NOT NULL,
  response_text TEXT NOT NULL,
  stored_at REAL NOT NULL,
  retain_until REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pmr_retain ON private_model_responses(retain_until);
"""


def private_path() -> Path:
    env = os.environ.get("MEMELAB_PRIVATE_DB")
    return Path(env) if env else db.DATA_DIR / "private" / "social_private.sqlite"


@contextmanager
def connect(path: Path | str | None = None):
    p = Path(path) if path else private_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(PRIVATE_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def put(content_hash: str, exact_text: str, reason: str, platform: str | None = None,
        original_url: str | None = None, retention_days: float = DEFAULT_RETENTION_DAYS,
        now: float | None = None, path: Path | str | None = None) -> str:
    if not reason:
        raise ValueError("private store needs a reason for keeping exact wording")
    t = time.time() if now is None else now
    ref = f"sha256:{content_hash}"
    with connect(path) as con:
        con.execute(
            "INSERT OR IGNORE INTO private_content(private_ref,content_hash,platform,original_url,exact_text,reason,stored_at,retain_until)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (ref, content_hash, platform, original_url, exact_text, reason, t, t + retention_days * 86400))
    return ref


def get(private_ref: str, path: Path | str | None = None) -> sqlite3.Row | None:
    with connect(path) as con:
        return con.execute("SELECT * FROM private_content WHERE private_ref=?", (private_ref,)).fetchone()


def put_model_response(cache_key: str, provider: str, model: str, prompt_version: str, response_text: str,
                       retention_days: float = DEFAULT_RETENTION_DAYS, now: float | None = None,
                       path: Path | str | None = None) -> None:
    """Keep the raw model response privately: it may quote the post, so it never goes to the public database.
    Kept so a change of validation logic can be replayed without paying for the model call again."""
    t = time.time() if now is None else now
    with connect(path) as con:
        con.execute("INSERT OR REPLACE INTO private_model_responses(cache_key,provider,model,prompt_version,response_text,stored_at,retain_until)"
                    " VALUES (?,?,?,?,?,?,?)", (cache_key, provider, model, prompt_version, response_text, t, t + retention_days * 86400))


def get_model_response(cache_key: str, now: float | None = None, path: Path | str | None = None) -> str | None:
    t = time.time() if now is None else now
    with connect(path) as con:
        r = con.execute("SELECT response_text FROM private_model_responses WHERE cache_key=? AND retain_until >= ?",
                        (cache_key, t)).fetchone()
        return r[0] if r else None


def get_text(content_hash: str, path: Path | str | None = None) -> str | None:
    """Exact normalized wording for a content hash, if a phase kept it (record_observation keep_exact_reason)."""
    r = get(f"sha256:{content_hash}", path)
    return r["exact_text"] if r else None


def purge_expired(now: float | None = None, path: Path | str | None = None) -> int:
    t = time.time() if now is None else now
    with connect(path) as con:
        n = con.execute("DELETE FROM private_content WHERE retain_until < ?", (t,)).rowcount
        return n + con.execute("DELETE FROM private_model_responses WHERE retain_until < ?", (t,)).rowcount

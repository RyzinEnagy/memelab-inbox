"""GitHub hand-off: the browser commits collector output into a public data repo; the sandbox pulls raw files.

Cloud side (this module): fetch https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path> and save into data/inbox.
Browser side (github_upload.js): uploads window.__ML.last as a file through github.com/<owner>/<repo>/upload/<branch>.
Only public market/on-chain data is ever placed in the repo. Never credentials.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from ..db import DATA_DIR

CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=1))


def raw_url(owner: str, repo: str, path: str, ref: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"


def fetch_raw(path: str, ref: str | None = None, owner: str | None = None, repo: str | None = None, retries: int = 6, wait: float = 5.0) -> str:
    """Fetch a file from the hand-off repo. raw.githubusercontent.com caches ~5 min per ref, so pass a commit SHA when
    re-fetching a path that was just overwritten; with ref=main a cache-busting query is added and we retry."""
    cfg = load_config()
    owner = owner or cfg.get("gh_owner"); repo = repo or cfg.get("gh_repo")
    if not owner or not repo:
        raise RuntimeError("configure gh_owner/gh_repo in data/config.json (memelab gh-config <owner> <repo>)")
    ref = ref or cfg.get("gh_branch", "main")
    url = raw_url(owner, repo, path, ref)
    last = ""
    for i in range(retries):
        q = f"?t={int(time.time())}" if ref in ("main", "master") else ""
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-w", "\n%{http_code}", url + q], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        if code == "200":
            return body
        last = f"{code}: {body[:120]}"
        time.sleep(wait)
    raise RuntimeError(f"fetch failed for {url}: {last}")


def pull(path: str, result_name: str | None = None, ref: str | None = None) -> Path:
    text = fetch_raw(path, ref=ref)
    data = json.loads(text)
    name = result_name or data.get("_plan") or Path(path).stem
    p = DATA_DIR / "inbox" / f"{name}.result.json"
    p.write_text(json.dumps(data, separators=(",", ":")))
    return p

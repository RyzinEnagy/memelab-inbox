"""Where the Helius key comes from, and keeping it out of anything that is committed.

Order: the HELIUS_API_KEY environment variable, then helius_api_key in data/config.json (that file is gitignored).
The key is never printed, never stored in a database, and never written into a saved plan file.

Set it once on a machine:   python -m memelab.secrets set
(prompts without echo and writes data/config.json). Check it:   python -m memelab.secrets status
"""
from __future__ import annotations

import json
import os
import re
import sys

ENV = "HELIUS_API_KEY"
_KEY_IN_URL = re.compile(r"(api-key=)[^&\"'\s\\]+")


def helius_key() -> str | None:
    v = os.environ.get(ENV, "").strip()
    if v:
        return v
    from .bridge.github_inbox import load_config
    return (load_config().get("helius_api_key") or "").strip() or None


def redact(text: str) -> str:
    """Replace the value of any api-key= query parameter. Used before a plan is written to disk."""
    return _KEY_IN_URL.sub(r"\1REDACTED", text)


def _main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        src = "environment" if os.environ.get(ENV, "").strip() else ("data/config.json" if helius_key() else "none")
        print(json.dumps({"helius_key": "set" if helius_key() else "missing", "source": src}))
        return 0 if helius_key() else 1
    if cmd == "set":
        import getpass
        from .bridge.github_inbox import load_config, save_config
        v = getpass.getpass("Helius API key (not shown): ").strip()
        if not v:
            print("nothing entered", file=sys.stderr)
            return 1
        cfg = load_config()
        cfg["helius_api_key"] = v
        save_config(cfg)
        print("saved to data/config.json (gitignored)")
        return 0
    print("usage: python -m memelab.secrets [status|set]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

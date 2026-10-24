"""Render the generated blocks of data/FEATURE_STORE_CONTRACT.md from the code (migrations, definitions hash, feature table,
missing reasons). Re-runnable: each block sits between its start and end markers.

    python -B render_contract.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

DOC = HERE.parent / "data" / "FEATURE_STORE_CONTRACT.md"


def blocks() -> dict[str, str]:
    mig = "| Version | Name | Up script sha256 |\n|---|---|---|\n" + "\n".join(
        f"| {v} | {n} | `{S._checksum(up)}` |" for v, n, up, _d in S.MIGRATIONS)
    sha = f"Definitions hash (`features.feature_set_sha()`): `{F.feature_set_sha()}`, {len(F.NAMES)} features."
    feats = "| Feature | Group | Source | Unit | Window | Transform | Evidence when a value |\n|---|---|---|---|---|---|---|\n" + "\n".join(
        f"| `{f['name']}` | {f['group']} | {f['source_id']} | {f['unit']} | {str(f['window_s']) + ' s' if f['window_s'] else 'none'} "
        f"| {f['transform']} | {f['evidence']} |" for f in F.FEATURES)
    reasons = "| Reason | Basis |\n|---|---|\n" + "\n".join(f"| `{k}` | {v} |" for k, v in sorted(F.REASONS.items(), key=lambda x: (x[1], x[0])))
    return {"migrations": mig, "sha": sha, "features": feats, "reasons": reasons}


def main() -> None:
    s = DOC.read_text()
    for name, body in blocks().items():
        pat = re.compile(rf"(<!-- generated:{name}:start -->\n).*?(<!-- generated:{name}:end -->)", re.S)
        if not pat.search(s):
            raise SystemExit(f"marker {name} missing")
        s = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), s)
    DOC.write_text(s)
    print("rendered", DOC)


if __name__ == "__main__":
    main()

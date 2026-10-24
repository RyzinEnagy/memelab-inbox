"""Phase 01: list every `path:line` anchor in the Phase 01 architecture documents with the cited line, so a reader can check that
each anchor points at what the text says. Bare `:NNN` anchors inherit the last full path in the same table cell or sentence.
Exit 1 if a file or line does not exist. Read-only.

    python audits/predictive-intelligence/phase_01/probes/check_doc_anchors.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOCS = sorted((ROOT / "audits/predictive-intelligence/phase_01/architecture").glob("*.md"))
FULL = re.compile(r"((?:memelab|tests|tools)/[\w/.-]+\.(?:py|js)):(\d+)")
BARE = re.compile(r"(?<![\w/.-])`?:(\d+)`?")


def main() -> int:
    bad, n = [], 0
    for d in DOCS:
        for ln_no, line in enumerate(d.read_text().splitlines(), 1):
            for cell in line.split("|"):
                last = None
                tokens = sorted([(m.start(), "F", m) for m in FULL.finditer(cell)] + [(m.start(), "B", m) for m in BARE.finditer(cell)],
                                key=lambda x: x[0])
                for _pos, kind, m in tokens:
                    if kind == "F":
                        last, num = m.group(1), int(m.group(2))
                    elif last:
                        num = int(m.group(1))
                    else:
                        continue
                    n += 1
                    p = ROOT / last
                    if not p.exists():
                        bad.append(f"{d.name}:{ln_no} {last} missing")
                        continue
                    src = p.read_text().splitlines()
                    if not 1 <= num <= len(src):
                        bad.append(f"{d.name}:{ln_no} {last}:{num} beyond end")
                        continue
                    print(f"{d.name}:{ln_no}  {last}:{num}  {src[num - 1].strip()[:110]}")
    print(f"anchors {n}, problems {len(bad)}")
    for b in bad:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

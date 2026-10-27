"""Skeptic 14: independent copy scan. Every file changed between 2fd0aae and HEAD vs the pinned MiroFish clone.
Reports (a) distinct normalized lines >= 40 chars shared with MiroFish, (b) shared 3-line shingles (lines >= 12 chars)."""
import subprocess, sys, re
from pathlib import Path
repo, mf = Path(sys.argv[1]), Path(sys.argv[2])
files = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "2fd0aae", "HEAD"], capture_output=True, text=True).stdout.split()
def norm(l): return re.sub(r"\s+", " ", l).strip()
mf_lines, mf_sh = set(), set()
for p in mf.rglob("*"):
    if ".git" in p.parts or not p.is_file() or p.suffix not in {".py",".js",".vue",".ts",".md",".json",".html",".css",".sh",".toml",".txt"}: continue
    ls = [norm(l) for l in p.read_text(errors="replace").splitlines()]
    mf_lines |= {l for l in ls if len(l) >= 40}
    ls2 = [l for l in ls if len(l) >= 12]
    mf_sh |= {tuple(ls2[i:i+3]) for i in range(len(ls2)-2)}
hits = {}
for f in files:
    p = repo / f
    if not p.is_file(): continue
    ls = [norm(l) for l in p.read_text(errors="replace").splitlines()]
    a = sorted({l for l in ls if len(l) >= 40 and l in mf_lines})
    ls2 = [l for l in ls if len(l) >= 12]
    b = [tuple(ls2[i:i+3]) for i in range(len(ls2)-2) if tuple(ls2[i:i+3]) in mf_sh]
    if a or b: hits[f] = {"shared_long_lines": a[:10], "n_shared_lines": len(a), "n_shared_3line_shingles": len(b)}
print(f"files scanned {len(files)}, MiroFish long lines {len(mf_lines)}, shingles {len(mf_sh)}")
for f, h in hits.items(): print(f, h)
print("no shared text" if not hits else f"{len(hits)} files with shared text")

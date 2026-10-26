"""Static (AST-only) smoke check for sohan-shingade/flint @ 5ce552c88109.

No repo code is imported or executed (niche repo, 7 stars; the PyPI name
`flint` belongs to an unrelated Fortran tool, and the real engine pulls the
156 MB nautilus_trader==1.230.0 wheel). The repo is parsed as data to verify
its Solana/DEX claims and its CI claims:

1. Are the Solana/Jupiter/on-chain modules implemented or docstring-only?
2. Does the oracle-pool (Jupiter) fill model do anything but raise?
3. Is there any AMM math (constant product, ticks, bins) anywhere?
4. Do the files the CI workflow runs actually exist at this commit?

Usage: python -I script.py <repo_root>
"""

import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
findings = []


def body_summary(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    stmts = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
    return f"{len(stmts)} non-docstring statements"


print("[1] Solana/Jupiter/on-chain modules")
for rel in ("flint/venues/jupiter/__init__.py", "flint/data/ingest/onchain/__init__.py"):
    p = root / rel
    s = body_summary(p)
    doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
    print(f"  {rel}: {s}; docstring: {doc[:100]!r}")
    if s.startswith("0 "):
        findings.append(f"{rel} is docstring-only")
print("  other files under flint/venues/jupiter:", sorted(x.name for x in (root / "flint/venues/jupiter").iterdir()))

print("\n[2] OraclePoolFillModel.fill")
p = root / "flint/engine/fills/oracle_pool.py"
tree = ast.parse(p.read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "fill":
        kinds = [type(n).__name__ for n in node.body]
        print(f"  flint/engine/fills/oracle_pool.py:{node.lineno} fill() body statements: {kinds}")
        if kinds == ["Raise"]:
            findings.append("OraclePoolFillModel.fill only raises NotImplementedError")

print("\n[3] AMM math search (constant product / sqrtPrice / tick / bin / reserves) in flint/**/*.py")
pat = re.compile(r"x\s*\*\s*y\s*=|constant[ _-]product|sqrt_?price|tick_spacing|liquidity_net|bin_step|get_amount_out|reserve_(in|out)", re.I)
hits = []
for f in sorted((root / "flint").rglob("*.py")):
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if pat.search(line):
            hits.append(f"{f.relative_to(root)}:{i}: {line.strip()[:100]}")
print(f"  {len(hits)} hits")
for h in hits[:10]:
    print("  ", h)
if not hits:
    findings.append("no AMM math anywhere in flint/")

print("\n[4] files referenced by .github/workflows/ci.yml that do not exist")
ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
refs = sorted(set(re.findall(r"(tests/[\w./-]+\.py|scripts/[\w./-]+\.py)", ci)))
wd = sorted(set(re.findall(r"working-directory:\s*(\S+)", ci)))
missing = [r for r in refs if not (root / r).exists()] + [d + "/" for d in wd if not (root / d).exists()]
pyver = sorted(set(re.findall(r'python-version:\s*"?([0-9.]+)"?', ci)) | set(re.findall(r'"(3\.\d+)"', ci)))
req = re.search(r'requires-python\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8")).group(1)
print(f"  referenced: {refs + [d + '/' for d in wd]}")
print(f"  missing: {missing}")
print(f"  CI python versions: {pyver}; pyproject requires-python: {req}")
if missing:
    findings.append(f"CI references {len(missing)} missing paths")

print("\n[5] declared engine dependency")
pp = (root / "pyproject.toml").read_text(encoding="utf-8")
print("  ", re.search(r'"nautilus_trader[^"]*"', pp).group(0))

print("\nRESULT:")
for f in findings:
    print(" -", f)
sys.exit(0)

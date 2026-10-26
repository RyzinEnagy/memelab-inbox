"""Static (AST-only) smoke check for etcherfx/sol-trade @ c8f37ad221b4.

No repo code is imported or executed (niche repo, GPL-3.0, not on PyPI, live
Jupiter swap code in the same package). The repo files are parsed as data with
`ast` to answer: which sol_trade modules does the backtest path pull in, and
does that closure reach the private key, signing or swap-execution code?
Also prints the fill-timing assertions from the repo's own engine test.

Usage: python -I script.py <repo_root>
"""

import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
pkg = root / "sol_trade"
mods = {p.stem: p for p in pkg.glob("*.py")}


def internal_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "sol_trade":
                out |= {a.name for a in node.names if a.name in mods}
            elif node.module.startswith("sol_trade."):
                out.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("sol_trade."):
                    out.add(a.name.split(".")[1])
    return out & set(mods)


def external_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
    return out - {"sol_trade"}


graph = {m: internal_imports(p) for m, p in mods.items()}


def closure(start: str) -> set[str]:
    seen, stack = set(), [start]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(graph.get(m, ()))
    return seen


DANGER = {
    "transactions": "builds/signs/sends Jupiter swaps (/execute)",
    "trading": "live loop, LiveExecutor -> perform_swap",
    "wallet": "wallet balance reads for swaps",
    "config": "loads .env, holds SOLTRADE_PRIVATE_KEY, Keypair property",
    "rpc": "Solana RPC client",
    "jupiter": "HTTP client created at import; quote/price network calls",
}

ok = True
for entry in ("backtest", "engine", "costs", "evaluation", "spec", "indicators"):
    c = closure(entry)
    ext = sorted(set().union(*(external_imports(mods[m]) for m in c)) - set(sys.stdlib_module_names))
    hits = sorted(m for m in c if m in DANGER)
    print(f"\n[{entry}] transitive sol_trade modules ({len(c)}): {sorted(c)}")
    print(f"  third-party imports: {ext}")
    for h in hits:
        print(f"  REACHES {h}: {DANGER[h]}")

print("\n[key / signing / execute call sites] (file:line)")
pat = re.compile(r"private_key|Keypair\.from_base58_string|sign_message|/execute|SOLTRADE_PRIVATE_KEY|load_dotenv\(")
for name in ("config", "transactions", "trading"):
    for i, line in enumerate(mods[name].read_text(encoding="utf-8").splitlines(), 1):
        if pat.search(line):
            print(f"  sol_trade/{name}.py:{i}: {line.strip()[:110]}")

print("\n[module-level side effects in jupiter.py]")
for i, line in enumerate(mods["jupiter"].read_text(encoding="utf-8").splitlines(), 1):
    if re.match(r"^_http_session\s*=", line):
        print(f"  sol_trade/jupiter.py:{i}: {line.strip()}")

print("\n[fill timing as asserted by the repo's own test]")
test = (root / "tests" / "test_engine.py").read_text(encoding="utf-8").splitlines()
start = next(i for i, l in enumerate(test) if "def test_entry_fills_at_the_next_open_with_levels" in l)
for i in range(start, min(start + 14, len(test))):
    print(f"  tests/test_engine.py:{i + 1}: {test[i]}")

bt_closure = closure("backtest")
reaches_key = "config" in bt_closure
reaches_swap = bool({"transactions", "trading"} & bt_closure)
print(f"\nRESULT: backtest closure reaches config(private key)={reaches_key}; reaches swap execution={reaches_swap}")
sys.exit(0)

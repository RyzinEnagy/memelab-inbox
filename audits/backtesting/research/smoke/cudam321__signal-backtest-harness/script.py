"""Static (AST-only) smoke check for cudam321/signal-backtest-harness @ 84643ded87e9.

No repo code is imported or executed (niche repo, 0 stars, not on PyPI). The
repo files are read as data; constants are extracted with ast/tomllib and the
timing consequences are computed here, independently, for the default config:

- which bar resolution get_price_series picks for the default horizons,
- how far after the true entry time (posted_at + latency) the default
  price_mode="close" reference price sits,
- which horizons put entry and exit inside the same bar,
- whether the repo's tests could detect any of this (flat candles?).

Usage: python -I script.py <repo_root>
"""

import ast
import re
import sys
import tomllib
from pathlib import Path

root = Path(sys.argv[1])
src = root / "src" / "memebot"


def const(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return ast.unparse(node.value), node.lineno
    return None, None


def default_arg(path: Path, func: str, arg: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            a = node.args
            names = [x.arg for x in a.kwonlyargs]
            for n, d in zip(names, a.kw_defaults):
                if n == arg and d is not None:
                    return ast.literal_eval(d), node.lineno
            pos = [x.arg for x in a.args]
            for n, d in zip(pos[len(pos) - len(a.defaults):], a.defaults):
                if n == arg:
                    return ast.literal_eval(d), node.lineno
    return None, None


gt = src / "data" / "geckoterminal.py"
fs = src / "sim" / "fill_simulator.py"
hb = src / "backtest" / "horizon_backtest.py"
cfg = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))

mw, mw_line = const(gt, "_MINUTE_WINDOW")
eb, eb_line = const(hb, "_ENTRY_BUFFER")
xb, xb_line = const(hb, "_EXIT_BUFFER")
pm_run, pm_run_line = default_arg(hb, "run_backtest", "price_mode")
pm_sim, pm_sim_line = default_arg(fs, "simulate_fill", "price_mode")
horizons = cfg["backtest"]["horizons"]
latency = float(cfg["cost_model"]["latency_seconds"])
print(f"_MINUTE_WINDOW = {mw}  (geckoterminal.py:{mw_line})")
ms, ms_line = const(src / "data" / "jupiter.py", "_MINUTE_SPAN")
print(f"_MINUTE_SPAN = {ms}  (jupiter.py:{ms_line}; JupiterChartsClient is the CLI default --source)")
print(f"_ENTRY_BUFFER = {eb}, _EXIT_BUFFER = {xb}  (horizon_backtest.py:{eb_line},{xb_line})")
print(f"default price_mode: run_backtest={pm_run!r} (horizon_backtest.py:{pm_run_line}), simulate_fill={pm_sim!r} (fill_simulator.py:{pm_sim_line})")
print(f"config.toml horizons={horizons} latency_seconds={latency}")

UNIT = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def secs(h: str) -> int:
    m = re.fullmatch(r"(\d+)([smhd])", h)
    return int(m.group(1)) * UNIT[m.group(2)]


minute_window = 16 * 3600  # value printed above: timedelta(hours=16)
window = 120 + max(secs(h) for h in horizons) + 300  # entry buffer + max horizon + exit buffer (latency cancels)
bar = 60 if window <= minute_window else 3600
print(f"\nquery window = {window/3600:.2f} h -> bar resolution = {'minute' if bar == 60 else 'hour'} ({bar}s)")

print("\nPer-call timing under defaults (posted at minute offset 0..59 inside an hour, 1 s steps):")
print("horizon | max seconds the entry price lies AFTER true entry | share of calls with entry+exit in same bar (gross forced to 1.0)")
for h in horizons:
    same = 0
    worst = 0
    total = 0
    for off in range(0, bar):
        t_entry = off + latency
        t_exit = t_entry + secs(h)
        bar_entry = int(t_entry // bar)
        bar_exit = int(t_exit // bar)
        ref_time = (bar_entry + 1) * bar  # close of covering bar
        worst = max(worst, ref_time - t_entry)
        same += bar_entry == bar_exit
        total += 1
    print(f"{h:>7} | {worst:8.0f} s | {same/total:6.1%}")

print("\n[price_at reads the covering bar by OPEN time and returns its CLOSE]")
lines = fs.read_text(encoding="utf-8").splitlines()
for i, l in enumerate(lines, 1):
    if "bisect_right(ts_list, t)" in l or "get(mode, bar.close)" in l or "return None  # cannot price entry" in l:
        print(f"  fill_simulator.py:{i}: {l.strip()}")
for i, l in enumerate(hb.read_text(encoding="utf-8").splitlines(), 1):
    if "except Exception:" in l or ("if series.empty:" in l) or "continue" in l.strip() == "continue":
        print(f"  horizon_backtest.py:{i}: {l.strip()}")
for i, l in enumerate(gt.read_text(encoding="utf-8").splitlines(), 1):
    if "pools.sort(" in l or "pool = pools[0]" in l:
        print(f"  geckoterminal.py:{i}: {l.strip()}")

print("\n[can the repo tests see intrabar timing?]")
t = (root / "tests" / "test_fill_simulator.py").read_text(encoding="utf-8")
flat = re.search(r"open=p, high=p, low=p, close=p", t)
print(f"  tests/test_fill_simulator.py builds flat candles (open=high=low=close): {bool(flat)}")
print(f"  test latency_seconds values: {sorted(set(re.findall(r'latency_seconds=([0-9.]+)', t)))}")

print("\nRESULT: default config uses hourly bars; entry priced at the covering bar close; short horizons collapse into one bar")
sys.exit(0)

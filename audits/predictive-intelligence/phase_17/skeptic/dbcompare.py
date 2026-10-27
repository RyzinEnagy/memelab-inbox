"""Compare two lab DBs table by table, every table and column; columns that differ between two base runs (wall-clock noise) are reported separately."""
import sqlite3, sys, json
def load(p):
    con = sqlite3.connect(p); out = {}
    for (t,) in con.execute("select name from sqlite_master where type='table' order by name"):
        cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
        out[t] = (cols, con.execute(f'select * from "{t}" order by rowid').fetchall())
    return out
def diffcols(a, b):
    d = set(); struct = []
    for t in sorted(set(a) | set(b)):
        if t not in a or t not in b: struct.append(f"table {t} only in one"); continue
        ca, ra = a[t]; cb, rb = b[t]
        if ca != cb: struct.append(f"{t}: columns differ"); continue
        if len(ra) != len(rb): struct.append(f"{t}: rows {len(ra)} vs {len(rb)}"); continue
        for x, y in zip(ra, rb):
            for c, u, v in zip(ca, x, y):
                if u != v: d.add((t, c))
    return d, struct
base, base2, head = (load(p) for p in sys.argv[1:4])
noise, s0 = diffcols(base, base2)
d, s = diffcols(base, head)
print(json.dumps({"tables": len(base), "rows": sum(len(v[1]) for v in base.values()), "noise_cols_base_vs_base2": sorted(map(list, noise)), "struct_base_vs_base2": s0,
                  "struct_base_vs_head": s, "nonnoise_diff_cols_base_vs_head": sorted(map(list, d - noise)), "noise_cols_base_vs_head": sorted(map(list, d & noise))}, indent=1))

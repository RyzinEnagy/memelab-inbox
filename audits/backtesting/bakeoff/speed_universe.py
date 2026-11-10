"""Write a seeded synthetic universe (200 tokens x 1000 hourly bars) for timing only."""
import json, random
random.seed(7)
U = []
for k in range(200):
    p, bars = 1.0, []
    for i in range(1000):
        o = p; c = max(1e-6, o * (1 + random.gauss(0, 0.03))); h = max(o, c) * (1 + abs(random.gauss(0, 0.01))); l = min(o, c) * (1 - abs(random.gauss(0, 0.01)))
        bars.append({"t": 1_800_000_000 + 3600 * i, "o": o, "h": h, "l": l, "c": c, "v": 1000.0}); p = c
    U.append(bars)
json.dump(U, open("/tmp/claude-0/speed_universe.json", "w"))

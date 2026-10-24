"""Phase 04 cold-start probe: import the named modules (comma separated) with the repository and the prototypes on the path.
Prints only the module list, so two runs give the same output; measure.py records the time and memory."""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[4]), str(HERE)]
mods = sys.argv[1].split(",")
for m in mods:
    importlib.import_module(m.strip())
HEAVY = ("numpy", "pandas", "scipy", "sklearn", "matplotlib", "pydantic", "statsmodels", "networkx", "torch", "lightgbm", "joblib")
print("imported", ",".join(mods), "| heavy modules loaded:", ",".join(h for h in HEAVY if h in sys.modules), "| modules:", len(sys.modules))

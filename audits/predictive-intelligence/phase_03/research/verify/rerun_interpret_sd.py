"""Phase 03 repair pass (lead): check the blind rescorer's correction of the interpret review (S4 reported
"has_term_standard_deviations false" because the smoke probed `term_standard_deviations_`; the attribute at the pin
is `standard_deviations_`, _ebm.py:454, set at :1639).
Fits a small EBM (4 outer bags, no interactions) on the challenge train split and reports whether per-term standard
deviations across outer bags exist, have one array per term with the score shape, and are finite.
Usage: <interpret venv python> -I rerun_interpret_sd.py challenge.csv
"""
import json, sys
import numpy as np, pandas as pd
import interpret
from interpret.glassbox import ExplainableBoostingClassifier

df = pd.read_csv(sys.argv[1])
tr = df[(df.split == "train") & df.label.notna()]
cols = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
m = ExplainableBoostingClassifier(outer_bags=4, interactions=0, random_state=0, n_jobs=1).fit(tr[cols], tr.label.astype(int))
sd = getattr(m, "standard_deviations_", None)
res = {"interpret": interpret.__version__, "has_standard_deviations_": sd is not None,
       "has_term_standard_deviations_": hasattr(m, "term_standard_deviations_"),
       "n_terms": len(m.term_scores_), "n_sd_arrays": len(sd) if sd is not None else 0,
       "shapes_match": bool(sd is not None and all(np.shape(a) == np.shape(b) for a, b in zip(sd, m.term_scores_))),
       "all_finite": bool(sd is not None and all(np.all(np.isfinite(a)) for a in sd)),
       "max_sd_first_term": float(np.max(sd[0])) if sd is not None else None}
print("RESULTS_JSON " + json.dumps(res, sort_keys=True))

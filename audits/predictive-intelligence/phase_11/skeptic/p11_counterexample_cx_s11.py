"""Phase 11 skeptic counterexample CX-S11: one token, two clusters.

cluster_of keys a pool row by that row's own creator field ("creator:<wallet>" else "mint:<chain>:<mint>"). In the real
development store two mints have rows whose creator field differs between decisions (one has None on some rows and a wallet on
others; one has two different wallets). Those mints then sit in two clusters, both clusters can be among the K nearest, and
the same token is counted twice in G and in the analog set, although the spec says "duplicate windows of one token or one
deployer never count twice". This fixture shows it through analog.select, and checks that the phase's own test file has no
test that fails on it (the suite passes with the defect present).

    python3 p11_counterexample_cx_s11.py
"""
import sys
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_11")
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_11/tests")
import test_predictive_analog as T   # fixture helpers only
from memelab.predictive import analog as A

pool = T.pool_fixture()
# the same mint decided twice before the cohort time, once with no creator recorded, once with a wallet (as 6p6xgHyF7A... in
# the real store), both very close to the target so both enter the nearest set
twin_a = T.ex("dupA", "DUPMINT", T.T0 + 1 * T.DAY, 1, creator=None, liq=10.0, mcap=12.0, vol=9.0, age=1.0)
twin_b = T.ex("dupB", "DUPMINT", T.T0 + 2 * T.DAY, 1, creator="WALLET_X", liq=10.0, mcap=12.0, vol=9.0, age=1.0)
ans = A.select("AC2_KNN", T.target(), pool + [twin_a, twin_b], as_of=T.AS_OF)
mints = [a["mint"] for a in ans["analogs"]]
print({"G": ans["G"], "analog_mints": ans["analog_mints"], "DUPMINT_count": mints.count("DUPMINT"),
       "clusters": sorted({a["cluster"] for a in ans["analogs"] if a["mint"] == "DUPMINT"}), "number": ans["number"]})
assert mints.count("DUPMINT") == 2 and ans["G"] > ans["analog_mints"], "counterexample did not reproduce"
print("CX-S11 reproduced: one token counted as two independent analogs; G overstates distinct tokens.")

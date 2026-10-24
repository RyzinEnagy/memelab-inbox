"""Skeptic 04: probes of memelab/predictive/runtime.py claims ("nothing propagates", "Never raises", lock guard, flag OFF).
    python -I -B skeptic_04_runtime_probes.py REPO TMPDIR
"""
import json, sys, importlib, pathlib
repo, tmp = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(repo))
from memelab.predictive import runtime as R, contract as C
out = {}
def probe(name, fn):
    try:
        out[name] = {"returned": str(fn())[:160]}
    except BaseException as e:  # noqa
        out[name] = {"ESCAPED": f"{type(e).__name__}: {str(e)[:100]}"}

APPROVED = {"predictive": {"behavioral": {"approved": True}}}
class A:
    def __init__(s, f): s.f = f
    def run(s): return s.f()
probe("guarded_component_calls_sys_exit", lambda: R.guarded("cli_main", lambda: sys.exit(1)))
probe("simulation_adapter_calls_sys_exit", lambda: R.simulation_state(APPROVED, A(lambda: sys.exit(1))))
probe("capability_report_adapter_calls_sys_exit", lambda: R.capability_report(APPROVED, adapter=A(lambda: sys.exit(1))))
for v in ("many", float("nan"), float("inf"), [3], {"n": 1}):
    probe(f"capability_report_llm_actions_{v!r}", lambda v=v: R.capability_report(APPROVED, adapter=A(lambda: {"llm_actions": v})))
probe("simulation_llm_actions_True_counts_as_available", lambda: R.simulation_state(APPROVED, A(lambda: {"llm_actions": True}))["state"])
probe("simulation_llm_actions_str_5_counts", lambda: R.simulation_state(APPROVED, A(lambda: {"llm_actions": "5"}))["state"])
for cfg in ({"predictive": True}, {"predictive": "on"}, {"predictive": {"behavioral": "yes"}}, ["predictive"]):
    probe(f"capability_report_config_{json.dumps(cfg)}", lambda cfg=cfg: [s["state"] for s in R.capability_report(cfg)])
for txt in ('{"predictive": true}', '[]', '{"predictive": {"enabled": "true"}}', '"x"'):
    p = tmp / "config.json"; p.write_text(txt)
    probe(f"contract.enabled_{txt}", lambda p=p: C.enabled(p))
# cost cap with NaN
def cost_nan():
    g = R.CallGuard(max_cost=1.0, cost_per_call=float("nan"), clock=lambda: 0.0, sleep=lambda s: None)
    return [g.call("paid", lambda: 1)[0]["state"] for _ in range(5)]
probe("callguard_cost_per_call_nan_5_calls_with_cap_1", cost_nan)
def cost_cap_nan():
    g = R.CallGuard(max_cost=float("nan"), cost_per_call=1.0, clock=lambda: 0.0, sleep=lambda s: None)
    return [g.call("paid", lambda: 1)[0]["state"] for _ in range(3)]
probe("callguard_max_cost_nan", cost_cap_nan)
def http500_breaker():
    g = R.CallGuard(clock=lambda: 0.0, sleep=lambda s: None)
    return [g.call("gt", lambda: (_ for _ in ()).throw(RuntimeError("HTTP 500")))[0]["state"] for _ in range(7)]
probe("callguard_component_errors_open_breaker", http500_breaker)
def returned_429():
    g = R.CallGuard(clock=lambda: 0.0, sleep=lambda s: None)
    return [g.call("gt", lambda: (429, None))[0]["state"] for _ in range(7)]
probe("callguard_returned_http_429_never_counts_as_failure", returned_429)
# dependency_state on a dotted name imports the parent package
pk = tmp / "p04sk_pkg"; pk.mkdir(exist_ok=True)
(pk / "__init__.py").write_text("import os\nopen(os.environ.get('P04SK_MARK', '/dev/null'), 'w').write('parent imported')\n")
(pk / "sub.py").write_text("")
sys.path.insert(0, str(tmp))
import os; os.environ["P04SK_MARK"] = str(tmp / "marker.txt")
probe("dependency_state_dotted_name", lambda: R.dependency_state("p04sk_pkg.sub")["state"])
out["dependency_state_dotted_name_parent_ran"] = (tmp / "marker.txt").exists()
# lock guard: anything after an environment marker is swallowed by the marker group of _REQ
H = "a" * 64
for name, line in {
    "marker_then_only_binary_none": f"pkg==1.0 ; python_version >= '3' --hash=sha256:{H} --only-binary=:none:",
    "marker_then_sha512_extra": f"pkg==1.0 ; python_version >= '3' --hash=sha256:{H} --hash=sha512:{'b' * 128}",
    "no_marker_sha512_extra": f"pkg==1.0 --hash=sha256:{H} --hash=sha512:{'b' * 128}",
    "marker_then_prefer_binary": f"pkg==1.0 ; python_version >= '3' --hash=sha256:{H} --prefer-binary",
    "only_binary_none_own_line": "--only-binary=:none:",
}.items():
    out[f"check_lock_{name}"] = R.check_lock(line + "\n")
# does any existing module import the predictive package?
hits = []
for p in (repo / "memelab").rglob("*.py"):
    if "predictive" in p.parts:
        continue
    t = p.read_text(errors="replace")
    if "predictive" in t:
        hits.append(str(p.relative_to(repo)))
out["existing_modules_mentioning_predictive"] = hits
print(json.dumps(out, indent=1))

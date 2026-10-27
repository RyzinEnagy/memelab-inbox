"""Skeptic's extra mutations of reports.py, run through the phase's own mutation harness (temporary copy, checkout untouched).
    cd <clone> && python -B /home/claude/pi_orchestration/skeptic/PHASE_18_extra_mutations.py OUT.json"""
import sys, importlib.util
from pathlib import Path
clone = Path.cwd()
spec = importlib.util.spec_from_file_location("mut", clone / "audits/predictive-intelligence/phase_18/probes/mutation_reports.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
M.MUTATIONS = [
    ("X1 token row of another chain used", '        if tok is not None and tok.get("chain", chain) != chain:', '        if False:'),
    ("X2 request capture age ignored (only INPUT_STALE)", ' or cap is None or now - cap > float(policy["source_max_age_hours"]) * 3600', ''),
    ("X3 unknown veto not shown in the at-a-glance column", '+ (["unknown"] if o["execution"]["veto_unknown"] else [])', ''),
    ("X4 unknown lab status printed raw", '    return I._ident(status), "UNKNOWN"', '    return str(status), "UNKNOWN"'),
    ("X5 non-matching change strings printed raw", 'I._ident(c, 60) if not re.fullmatch(r"[A-Za-z0-9_ .:%+-]+", str(c)) else str(c)', 'str(c)'),
    ("X6 served MODEL_STALE/DRIFT pipeline alert removed", '                if b_ in ("MODEL_STALE", "DRIFT_ALERT", "REGISTRY_UNAVAILABLE"):', '                if False:'),
    ("X7 ERROR events give no pipeline alert", '    for e in errors:\n        b = {"policy": "pipeline_health"', '    for e in []:\n        b = {"policy": "pipeline_health"'),
    ("X8 reevaluate ignores the base rate", 'not (_fin(n.get("base_rate")) and n["interval"][0] > float(n["base_rate"]) + _TOL)', 'False'),
    ("X9 veto_unknown not treated as risk", 'risky = ex["structural_veto"] or ex["veto_unknown"] or', 'risky = ex["structural_veto"] or'),
    ("X10 backtest-veto reasons dropped from the execution section", '''                   + (f"; backtest veto {', '.join(ex['backtest_veto_reasons'])}" if ex["backtest_veto"] else ""),''', '''                   + "",'''),
    ("X11 SIMULATION_NOT_AVAILABLE dropped from at a glance", '''    L.append(f"- Backtesting: {sysv['backtest_status']}. Behavioral simulation: {SIMULATION_STATE}.")''', '''    L.append(f"- Backtesting: {sysv['backtest_status']}.")'''),
    ("X12 target definitions horizon dropped", '''{d['horizon_seconds'] / 3600:.0f} hours | "''', '''" "'''),
]
sys.exit(M.main(sys.argv[1]))

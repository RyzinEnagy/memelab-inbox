"""Phase 18: writes ui/EXAMPLE_REPORTS.md from the committed real outputs (real/) and the golden files (tests/fixtures/predictive/phase18/golden/).
Run from the repository root: python -B audits/predictive-intelligence/phase_18/probes/make_examples_doc.py
Ids that depend on the temporary test folder (a placeholder in the golden files) are written as temp-id."""
from pathlib import Path
R = Path("audits/predictive-intelligence/phase_18/real")
G = Path("tests/fixtures/predictive/phase18/golden")
def lines(p): return p.read_text().splitlines()
def between(ls, start, stop):
    i = next(k for k, l in enumerate(ls) if l.startswith(start))
    j = next(k for k in range(i + 1, len(ls)) if ls[k].startswith(stop))
    return ls[i:j]
def clean(ls): return [l.replace("<varies>", "temp-id") for l in ls]
scout = lines(R / "REAL_SCOUT_REPORT.md")
glance = between(scout, "## At a glance", "## System status")
gomo = between(scout, "## GOMO", "## HIGGS")
gomo = [l for l in gomo if not l.startswith("- Request record")]
alerts_scout = (R / "REAL_ALERTS_SCOUT_DRY_RUN.txt").read_text().strip().splitlines()
rep = (R / "REAL_ALERTS_REPLAY_DRY_RUN.txt").read_text().splitlines()
i = rep.index("----- alert_000001.txt")
one_alert = rep[i + 1:i + 12]
fx = lines(G / "report_forecast_format_only.md")
fx_glance = between(fx, "## At a glance", "## System status")
fxa = between(fx, "## FXA", "## Units and times") if any(l.startswith("## FXA") for l in fx) else []
fxc = between(fx, "## FXC", "## FXA")
fxa_pred = between(fxa, "### Predictive research", "### Historical prediction")
fxc_pred = between(fxc, "### Predictive research", "### Historical prediction")
fxc_exec = between(fxc, "### Execution and stress", "### Behavioral scenarios")
al = (G / "alerts_forecast_format_only.txt").read_text().splitlines()
wd = (G / "alerts_withdrawn_format_only.txt").read_text().splitlines()
k = [n for n, l in enumerate(wd) if "forecast withdrawn" in l][0]
wd_one = wd[k - 1:k + 11]
forged = lines(G / "report_forged_refused.md")
forged_rows = [l for l in forged if "REFUSED" in l]
inj = lines(G / "report_injection.md")
inj_glance = [l for l in between(inj, "| Opportunity", "## System status") if l.strip()]
inj_status = [l for l in inj if "kept in the lab's token report" in l][:1]
def block(ls): return ["```text"] + clean(ls) + ["```"]
out = []
out += ["# Example reports (Phase 18, report-1 and alerts-rules-1)", "",
        "Two kinds of example are here. The real ones come from the recorded runs at the repair code `31ada29` (CP18-2) on real data in a sandbox "
        "(the committed inbox bodies, the `71fc50e` state export, `unshare -n`): every real target abstains, so the real report shows no "
        "probability. The format-only ones come from fixture worlds (a fixture champion with a fixture calibration card, fixed clocks) and "
        "exist only to show the layout of a validated forecast; every one of them carries the line \"FORMAT-ONLY FIXTURE: invented data, not a "
        "forecast\". No fixture number is a research estimate.", "",
        "Full files: `../real/REAL_SCOUT_REPORT.md`, `../real/REAL_REPLAY_REPORT.md`, `../real/REAL_ALERTS_SCOUT_DRY_RUN.txt`, "
        "`../real/REAL_ALERTS_REPLAY_DRY_RUN.txt`; golden fixtures in `tests/fixtures/predictive/phase18/golden/` (there an id that depends "
        "on the temporary test folder is written as a placeholder; below it reads temp-id). Rule matrix: `ALERT_RULE_MATRIX.md`. Missing "
        "data: `MISSING_DATA_UX.md`.", "",
        "## How to produce them", "",
        "```text",
        "python -m memelab.predictive.reports report --state-dir STATE --config CONFIG [--lab-db LAB_DB] [--out FILE] [--json]",
        "python -m memelab.predictive.reports alerts --state-dir STATE --config CONFIG [--alert-db DB] [--lab-db LAB_DB] [--as-of EPOCH]",
        "python -m memelab.predictive.reports alerts-state --config CONFIG [--alert-db DB]",
        "```", "",
        "With `predictive.enabled` not the JSON value true, each command prints FLAG_OFF and writes nothing. An output path inside the "
        "repository is refused unless it is under `data/private/`. `--send` is refused: alerts are previews in a local outbox only.", "",
        "## How to read them", "",
        "- Order: at a glance, system status, target definitions, carried constraints, then one block per opportunity (identity and snapshot; "
        "the lab's structural research; the lab's technical labels; catalyst evidence; predictive research; historical prediction and its "
        "out-of-sample record; execution and stress; behavioral scenarios; sources and ids; limitations), then the events not attempted, then "
        "units and times.",
        "- Every line is in one of the lab's buckets: FACT (read from a record), INFERENCE (drawn from records), HEURISTIC (a rule label), "
        "UNKNOWN (missing; it earns nothing). The renderer is the lab's own `memelab.report._ev`.",
        "- Times are UTC in ISO 8601 with Z; alerts add the America/New_York local time. Ages are in minutes, hours or days; horizons in "
        "hours; amounts in USD. Percentages appear only in the target definitions (barriers) and in a verified FORECAST.",
        "- Ids: forecast ids `fc_...` in full; record, request, pass and registry ids as their first 12 characters (the `--json` view has "
        "them in full). Codes such as NO_ENTRY_AT_SHADOW_OR_ABOVE (no registry entry at SHADOW or above) and NO_TRADES_AFTER_ENTRY (a "
        "label outcome) are the registry's and the contract's frozen codes, not trade steps.",
        "- Never shown: a probability, base rate, cohort number or reference-model number for an abstaining target; a number from a document "
        "that fails a check; a size; a trade step; a local path; token text carrying a trading or forecast word.", ""]
out += ["## Real report, sandbox scout state: at a glance", ""] + block(glance) + [""]
out += ["## Real report: one opportunity with a fatal-flag veto (GOMO)", "",
        "The inputs are the committed inbox bodies from 2026-10-07, so they are 20 days old at the capture (INPUT_STALE) and every target "
        "abstains SOURCE_STALE as well as MODEL_NOT_SELECTED, UNCALIBRATED and INSUFFICIENT_HISTORY. The request record line is left out "
        "here (its id changes with every run).", ""] + block(gomo) + [""]
out += ["## Real dry-run alerts", "",
        "On the scout state: no alert. The three tokens with a fatal flag are suppressed SOURCE_STALE (inputs from 2026-10-07); the report "
        "still shows the flags.", ""] + block(alerts_scout) + [""]
out += ["On the export-replay state, at its newest capture plus 60 s: 8 risk_override previews and 15 candidates suppressed "
        "SOURCE_STALE; no other policy fired because no target has a verified forecast. One preview:", ""] + block(one_alert) + [""]
out += ["## Format-only: a hypothetical validated forecast and a strong forecast with an impossible exit", "",
        "FXA is clean; FXC carries the fatal flag CANNOT_EXIT_5K. Both T1 attempts come from a fixture champion with a fixture SHADOW "
        "calibration card; the other targets abstain. FXA shows its fixture number; FXC shows FORECAST OVERRIDDEN and no number, "
        "because any risk flag (a veto, a liquidity fall of 20% or more, or liquidity that became unknown) overrides an estimate.", ""] + block(fx_glance) + [""]
out += ["FXA, predictive research:", ""] + block(fxa_pred) + [""]
out += ["FXC, predictive research and execution: the veto overrides the estimate, the number is withheld, and the price path is not proceeds.", ""] + \
       block(fxc_pred + fxc_exec) + [""]
out += ["FXC and FXA, dry-run alerts in a fixture run: the warning comes first; the re-evaluation notice for FXC is suppressed "
        "RISK_OVERRIDES_FORECAST; FXA gets a notice that may prompt re-evaluation only.", ""] + block(al) + [""]
out += ["## Format-only: a withdrawn forecast", "",
        "The fixture champion is rolled back; the next attempt of FXA abstains, and the alert says the earlier estimate is withdrawn.", ""] + \
       block(wd_one) + [""]
out += ["## Format-only: a forged number is refused", "",
        "An adversary edits the FORECAST probability of FXA and re-seals every record id, file sha and the pass chain, so the state still "
        "loads; the request record still holds the point recomputed from the raw number. The report refuses the document and shows no number.",
        ""] + block(forged_rows) + [""]
out += ["## Format-only: token text that tries to inject", "",
        "Symbols BUY-NOW, \"## 99% chance\", a|b|c, a symbol with a line break, a local path, a script tag and pump.fun; the first token's lab "
        "status is NEAR ENTRY. Symbols with a trading or forecast word are withheld; the rest are reduced to letters, digits, dot, dash and "
        "underscore; the lab status with trade wording is not printed. Since CP18-2 the check runs on the joined letters of the token text, so run-together forms such as SELLNOW, BUYNOW, TAKEPROFIT and 100X are withheld too (tests m4 in tests/test_predictive_reports.py).", ""] + block(inj_glance + inj_status) + [""]
Path("audits/predictive-intelligence/phase_18/ui/EXAMPLE_REPORTS.md").write_text("\n".join(out))
print(len(out))

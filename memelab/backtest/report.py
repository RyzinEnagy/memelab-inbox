"""Decision-oriented backtest and stress report for one assessed opportunity (Phase 14).

One JSON document (schema memelab.backtest.report/1) and its Markdown rendering. The parts stay separate and are never
merged into one number:
- the lab's own view of the project (score, status, fatal flags), unchanged;
- historical strategy evidence (whole-universe runs and the sealed-test validation, net of costs next to paper);
- this token's signal states (state, not validation);
- the present-tense execution quote;
- hypothetical adverse stress, executable proceeds next to paper value, and the size the caps allow;
- catalyst provenance with collector status;
- alternate explanations, uncertainty and coverage.
Every field group carries an evidence class (FACT, INFERENCE, HEURISTIC, UNKNOWN). Labels are research labels; none
of them is an instruction to trade.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from . import ENGINE_VERSION, store

SCHEMA = "memelab.backtest.report/1"
SCOUT_SCHEMA = "memelab.backtest.scout_section/1"
VALIDATION_PATH = store.ROOT / "audits" / "backtesting" / "validation" / "p11_results.json"
DISCLOSURE = ("Research only. Backtests describe the past over the lab's discovery universe, stress scenarios are hypothetical "
              "with no probabilities, and nothing here is an instruction to buy, sell or size a position.")
COLLECTOR_STATUS = {
    "MAXUN": "NOT_ADOPTED (Phase 06A, D-BT-020). No Maxun robot runs; the evaluation robot is idle with no schedule.",
    "webcapture": "one-shot captures only; no schedule is approved (policy schedules_approved false).",
    "lab_catalyst_tables": "the lab's own Firecrawl catalyst layer, read only.",
}
LABELS = ("FATAL FLAW", "UNTESTED", "BAD EXECUTION", "INCONCLUSIVE", "TESTED")
GOOD_PROJECT_STATUSES = ("WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET")
HIGH_STATUSES = ("NEAR ENTRY", "ENTRY CONDITIONS MET")
LATE_CRAWL_S = 6 * 3600
MIN_RANK_TRADES = 30                 # fewer trades than this are listed but never ranked


def utc(ts) -> str | None:
    if ts is None:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(float(ts)))


def _f(x, nd=2):
    return None if x is None else round(float(x), nd)


# ---------------------------------------------------------------- labels

def alert_label(a: dict | None, lab_fatal: list | None = None) -> dict:
    """FATAL FLAW > UNTESTED > BAD EXECUTION > INCONCLUSIVE > TESTED. A missing assessment is UNTESTED, never neutral."""
    fatal = list(lab_fatal or []) or list(((a or {}).get("lab") or {}).get("fatal_flags") or [])
    if fatal or (a or {}).get("state") == "RISK_FATAL_FLAW":
        return {"label": "FATAL FLAW", "why": "lab fatal flag(s) " + (", ".join(fatal) or "present") + "; the lab's veto stands and no backtest can lift it"}
    if not a:
        return {"label": "UNTESTED", "why": "no backtest or stress assessment exists for this mint"}
    st, dec = a.get("state"), (a.get("stress") or {}).get("decision")
    if st in ("ERROR", "SOURCE_BLOCKED", "STALE_DATA", "INVALID_TOKEN_ID"):
        return {"label": "UNTESTED", "why": f"assessment {st}: {a.get('reason') or a.get('error') or 'not assessed'}"}
    if st in ("INSUFFICIENT_EXECUTION_DATA", "UNSUPPORTED_POOL") or dec in ("STRUCTURALLY_UNTRADEABLE", "NO_TRADE", "INSUFFICIENT_EXECUTION_DATA"):
        why = "; ".join((a.get("stress") or {}).get("decision_reasons") or []) or st
        return {"label": "BAD EXECUTION", "why": f"{dec or st}: {why}"}
    if st == "COMPLETE" and a.get("tier") in ("HISTORICAL_COHORT", "TOKEN_SPECIFIC") and dec == "RESEARCHABLE":
        return {"label": "TESTED", "why": f"{a.get('tier')} evidence and a feasible exit under base conditions; still research only"}
    return {"label": "INCONCLUSIVE", "why": f"state {st}, evidence {a.get('tier')}, stress {dec or 'n/a'}"}


def project_vs_entry(a: dict | None, lab: dict, label: dict) -> dict:
    status, fatal = lab.get("status"), lab.get("fatal_flags") or []
    project = {"source": "lab score and status (unchanged)", "score": lab.get("score"), "status": status,
               "reads_as": ("fatal flaw" if fatal else ("good project by the lab's rubric" if status in GOOD_PROJECT_STATUSES else "not a good project by the lab's rubric"))}
    entry = {"source": "execution and stress at the assessment time", "label": label["label"],
             "stress_decision": ((a or {}).get("stress") or {}).get("decision"), "max_size_usd_under_caps": _f((((a or {}).get("stress") or {}).get("max_size") or {}).get("max_size_usd"))}
    mismatch = None
    if status in HIGH_STATUSES and label["label"] in ("BAD EXECUTION", "UNTESTED", "FATAL FLAW"):
        mismatch = f"HIGH_STATUS_MISMATCH: the lab status is {status} but the entry reads {label['label']}; a good project is not a good entry"
    return {"good_project": project, "good_entry": entry, "mismatch": mismatch}


# ---------------------------------------------------------------- historical strategy evidence

def _sha_file(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def strategy_evidence(con, validation_path: Path | str | None = None) -> dict:
    """Latest whole-universe run per strategy (net of modeled costs next to mid-price paper returns, ranked by net) and
    the sealed-test validation record. Every row names its run id, dataset hash and result hash."""
    rows = con.execute("SELECT e.run_id, e.strategy_id, e.dataset_hash, e.code_sha, e.config_json, r.result_json, r.result_hash, r.created_at "
                       "FROM bt_experiment_runs e JOIN bt_run_results r ON r.run_id=e.run_id ORDER BY r.created_at, r.id").fetchall()
    latest: dict[str, dict] = {}
    for x in rows:
        cfg = json.loads(x["config_json"] or "{}")
        if cfg.get("mints") or cfg.get("decide_from") or cfg.get("decide_until"):
            continue                                            # only whole-universe, whole-period runs
        res = json.loads(x["result_json"])
        net, paper, n = res.get("mean_ret"), res.get("mean_paper_ret_mid"), res.get("n_trades") or 0
        flag = "NO_TRADES" if not n else ("PAPER_ONLY_PROFIT" if (paper or 0) > 0 and (net or 0) <= 0 else
                                          ("NET_NEGATIVE" if (net or 0) <= 0 else "NET_POSITIVE"))
        latest[x["strategy_id"]] = {"strategy": x["strategy_id"], "run_id": x["run_id"], "dataset_hash": x["dataset_hash"], "result_hash": x["result_hash"],
                                    "ledger_hash": res.get("ledger_hash"), "n_trades": n, "net_mean_ret": net, "paper_mean_ret_mid": paper,
                                    "cost_drag": (paper - net) if (paper is not None and net is not None) else None, "flag": flag,
                                    "fill_model": (cfg.get("engine") or {}).get("fill_model"), "run_at": utc(x["created_at"])}
    for r in latest.values():
        r["rankable"] = r["n_trades"] >= MIN_RANK_TRADES and r["net_mean_ret"] is not None
    ranked = sorted(latest.values(), key=lambda r: (not r["rankable"], r["net_mean_ret"] is None, -(r["net_mean_ret"] or 0.0), r["strategy"]))
    for i, r in enumerate([x for x in ranked if x["rankable"]], 1):
        r["rank_by_net"] = i
    for r in ranked:
        r.setdefault("rank_by_net", None)
    by_paper = sorted([r for r in ranked if r["rankable"] and r["paper_mean_ret_mid"] is not None], key=lambda r: -r["paper_mean_ret_mid"])
    for i, r in enumerate(by_paper, 1):
        r["rank_by_paper"] = i
    vp = Path(validation_path) if validation_path else VALIDATION_PATH
    val = json.loads(vp.read_text()) if vp.exists() else None
    vout = None
    if val:
        vout = {"file": str(vp.relative_to(store.ROOT)) if vp.is_relative_to(store.ROOT) else str(vp), "sha256": _sha_file(vp),
                "prereg_sha256": val.get("prereg_sha256"), "dataset_hash": val.get("dataset_hash"), "total_trials": val.get("total_trials"), "strategies": {}}
        for sid, s in (val.get("strategies") or {}).items():
            plan, test = s.get("plan") or {}, s.get("test") or {}
            vout["strategies"][sid] = {"verdict": s.get("verdict"), "sealed_test_from": utc((plan.get("valid_end") or 0) + (plan.get("embargo_s") or 0)) if plan else None,
                                       "sealed_test_to": utc(plan.get("end")), "test_trades": test.get("n"), "test_mean_ret": test.get("mean_ret"),
                                       "test_ci95": test.get("bootstrap95_mean_ret"), "baseline_enter_at_discovery_mean_ret": ((s.get("baselines") or {}).get("ENTER_AT_DISCOVERY") or {}).get("mean_ret"),
                                       "test_ledger_hash": s.get("test_ledger_hash"), "notes": s.get("notes") or []}
        wf = val.get("walk_forward_breakout_close")
        if wf:
            vout["walk_forward"] = {"strategy": wf.get("strategy"), "pooled_oos_trades": (wf.get("pooled_oos") or {}).get("n"),
                                    "pooled_oos_mean_ret": (wf.get("pooled_oos") or {}).get("mean_ret"), "ci95": wf.get("pooled_oos_bootstrap95")}
    deteriorated = [r["strategy"] for r in ranked if r["flag"] == "PAPER_ONLY_PROFIT"]
    return {"evidence_class": "FACT (stored runs) / INFERENCE (cost model)", "runs": ranked, "validation": vout,
            "paper_only_profit": deteriorated,
            "min_rank_trades": MIN_RANK_TRADES,
            "note": "whole-universe history of the lab's discovered tokens, net of modeled entry and exit costs; it describes the past, not this token"}


# ---------------------------------------------------------------- catalysts

def catalysts(con, chain: str, mint: str, lab_db: Path | str | None = None, extra: list[dict] | None = None) -> dict:
    recs = []
    for x in con.execute("SELECT * FROM bt_capture_provenance WHERE chain=? AND mint=? ORDER BY available_at, id", (chain, mint)).fetchall():
        recs.append({"origin": x["canonical_origin"] or x["source_url"], "capture_method": (x["collector"] or "").upper(), "first_known_at": utc(x["first_seen_at"]),
                     "available_at": utc(x["available_at"]), "published_claim": utc(x["source_published_at"]), "publication_confidence": x["published_confidence"],
                     "historical_asof_proof": x["historical_asof_proof"], "collector_run_status": x["run_status"], "mint_verified": bool(x["mint_verified"]),
                     "_first": x["first_seen_at"], "_pub": x["source_published_at"]})
    pool = list(extra or [])
    if lab_db and Path(lab_db).exists():
        from .sources import catalyst_bridge
        pool += catalyst_bridge.records_from_lab_db(lab_db)
    for r in pool:
        if r.get("mint") != mint or r.get("chain", chain) != chain:
            continue
        recs.append({"origin": r.get("origin_group"), "capture_method": "LAB_CATALYST" if str(r.get("event_id", "")).startswith("cat") else "LAB_LAUNCH_MONITOR",
                     "first_known_at": utc(r.get("first_seen_at")), "available_at": utc(r.get("available_at")), "published_claim": utc(r.get("published_at")),
                     "publication_confidence": "CLAIM", "historical_asof_proof": r.get("historical_asof_proof"), "collector_run_status": "OK",
                     "mint_verified": bool(r.get("mint_verified")), "claim_type": r.get("claim_type"), "_first": r.get("first_seen_at"), "_pub": r.get("published_at")})
    for r in recs:
        warn = []
        if r.get("historical_asof_proof") in (None, "NONE"):
            warn.append("LATE_CAPTURE: no contemporaneous proof; usable only from its own first-seen time")
        if r["_first"] is not None and r["_pub"] is not None and r["_first"] - r["_pub"] > LATE_CRAWL_S:
            warn.append(f"LATE_CRAWL: first seen {(r['_first'] - r['_pub']) / 3600:.1f} h after the claimed publication")
        if not r["mint_verified"]:
            warn.append("UNVERIFIED_MINT: name or ticker match only; never linked to this token")
        r["warnings"] = warn
        r.pop("_first"); r.pop("_pub")
    methods = sorted({r["capture_method"] for r in recs})
    return {"evidence_class": "FACT (capture records) / UNKNOWN (claimed publication times)", "records": recs, "n": len(recs),
            "collector_status": COLLECTOR_STATUS, "maxun_running": False, "capture_methods": methods,
            "note": None if recs else "no catalyst record for this mint; absence of a catalyst is not a negative or a positive signal"}


# ---------------------------------------------------------------- coverage

def coverage(con) -> dict:
    q = lambda sql: con.execute(sql).fetchone()
    b = q("SELECT COUNT(*), COUNT(DISTINCT mint), MIN(start), MAX(end) FROM bt_market_bars")
    u = q("SELECT COUNT(*), COUNT(DISTINCT mint), MIN(entered_at), MAX(entered_at) FROM bt_universe_members")
    return {"evidence_class": "FACT", "bars": b[0], "mints_with_bars": b[1], "bars_from": utc(b[2]), "bars_to": utc(b[3]),
            "universe_rows": u[0], "universe_mints": u[1], "universe_from": utc(u[2]), "universe_to": utc(u[3]),
            "assessments": q("SELECT COUNT(*) FROM bt_assessments")[0], "runs": q("SELECT COUNT(*) FROM bt_run_results")[0],
            "blocked_sources": ["historical swaps", "historical reserves, ticks and bins", "historical holders and wallet flows"],
            "survivorship": "The universe is every token the lab recorded, including ones that later died; no survivor filter"}


# ---------------------------------------------------------------- the report document

def _executable_vs_paper(st: dict) -> list[dict]:
    out = []
    for r in st.get("scenarios") or []:
        if r["scenario"] != "BASE":
            continue
        out.append({"size_usd": r["size_usd"], "status": r.get("status"), "cost_usd": _f(r.get("cost_usd")), "paper_value_mid_usd": _f(r.get("marked_value_usd")),
                    "executable_proceeds_usd": _f(r.get("proceeds_usd")), "realizable_vs_paper": _f(r.get("realizable_vs_marked"), 4),
                    "net_ret": _f(r.get("ret"), 4), "basis": r.get("basis"), "swap_fee": r.get("swap_fee"), "fee_basis": r.get("fee_basis")})
    return out


def _stress_table(st: dict) -> list[dict]:
    return [{"scenario": r["scenario"], "label": r.get("label"), "size_usd": r["size_usd"], "hypothetical": r.get("hypothetical"), "status": r.get("status"),
             "proceeds_usd": _f(r.get("proceeds_usd")), "net_ret": _f(r.get("ret"), 4), "exit_impact": _f(r.get("exit_impact"), 4)} for r in st.get("scenarios") or []]


def _alternates(a: dict) -> list[str]:
    out = ["a high lab score can reflect attention that is already in the price (price first, attention later)"]
    sig = ((a.get("token_signals") or {}).get("signals") or {})
    if sig and all(not str(v).startswith("SIGNAL") for v in sig.values()):
        out.append("no tested setup is active on this token now; a move from here is outside what the strategies were tested on")
    he = (a.get("stress") or {}).get("historical_evidence") or {}
    if he.get("tier") != "HISTORICAL_COHORT":
        out.append(f"the cohort of past tokens with this lab status is {he.get('n', 0)} cases (minimum {he.get('min_n', 30)}); past outcomes cannot separate skill from luck")
    snap = a.get("snapshot") or {}
    if (snap.get("concentrated_pct") or 0) >= 20:
        out.append(f"{snap['concentrated_pct']:.0f}% of supply sits in concentrated holders; they can move price regardless of the setup")
    if str(snap.get("fee_basis", "")).startswith("ASSUMED"):
        out.append("the pool fee is assumed at the highest observed tier; if the real tier is lower, costs here are overstated")
    return out


def _uncertainty(a: dict) -> list[str]:
    out = ["stress magnitudes are fixed hypothetical shocks, not forecasts; no probabilities are assigned",
           "historical fills use LIQ_SNAPSHOT_APPROX (constant-product depth from a liquidity snapshot); exact historical execution is SOURCE_BLOCKED"]
    if not any(q[1] is not None for q in a.get("sell_quotes") or []):
        out.append("no usable sell quote at the assessment time; executable proceeds rest on the depth model alone")
    else:
        out.append("sell quotes are present tense (observed once at the assessment time) and expire quickly")
    if (a.get("token_signals") or {}).get("closed_bars", 0) < 25:
        out.append("fewer than 25 closed hourly bars: too little token history for any token-specific claim")
    return out


def shared_context(con, validation_path=None) -> dict:
    """The parts of a report that do not depend on the token; computed once per scout run."""
    return {"strategies": strategy_evidence(con, validation_path), "coverage": coverage(con)}


def build(a: dict | None, *, con=None, lab: dict | None = None, deep: dict | None = None, validation_path=None, lab_db=None,
          extra_catalysts: list[dict] | None = None, include_strategies: bool = True, shared: dict | None = None) -> dict:
    """The report document for one assessment. `a` may be None or an abstain record: the report then says so plainly
    and keeps the candidate's identity and the lab's view instead of blanking it."""
    a = a or {}
    lab = lab or a.get("lab") or {}
    if shared is None and con is not None:
        shared = shared_context(con, validation_path) if include_strategies else {"strategies": None, "coverage": coverage(con)}
    shared = shared or {}
    label = alert_label(a or None, lab.get("fatal_flags"))
    st = a.get("stress") or {}
    prov = a.get("provenance") or {}
    fatal = lab.get("fatal_flags") or []
    # a fatal flag with any downstream result that reads as usable is an override; an earlier abstain is not
    override = bool(fatal) and (st.get("decision") in ("RESEARCHABLE", "INCONCLUSIVE") or a.get("state") in ("COMPLETE", "PARTIAL_WITH_LIMITATIONS"))
    doc = {"schema": SCHEMA, "engine_version": a.get("engine_version") or ENGINE_VERSION,
           "token": {"evidence_class": "FACT", "chain": a.get("chain") or lab.get("chain"), "mint": a.get("mint") or lab.get("mint"),
                     "symbol": prov.get("symbol") or a.get("symbol") or lab.get("symbol"), "as_of": a.get("as_of"), "as_of_utc": utc(a.get("as_of"))},
           "trace": {"evidence_class": "FACT", "request_key": a.get("request_key"), "assessment_state": a.get("state") or "NOT_ASSESSED",
                     "assessment_tier": a.get("tier") or "UNAVAILABLE", "cache": a.get("cache"), "reason": a.get("reason") or a.get("error"),
                     "retriable": a.get("retriable"), "deep_request_key": (deep or {}).get("request_key")},
           "headline": {"evidence_class": "HEURISTIC", **label, **project_vs_entry(a or None, lab, label)},
           "lab": {"evidence_class": "FACT", "score": lab.get("score"), "status": lab.get("status"), "fatal_flags": fatal,
                   "note": "the lab's 100-point score and status are shown as computed; this report never changes them",
                   "fatal_override_detected": override},
           "historical_evidence": {"evidence_class": "FACT / INFERENCE",
                                   "token_specific": ({"state": deep.get("state"), "tier": deep.get("tier"), "per_strategy": deep.get("per_strategy"),
                                                       "note": deep.get("note") or deep.get("reason")} if deep else
                                                      {"state": "NOT_RUN" if a.get("deep_stage") == "QUEUED" else "NONE",
                                                       "note": "no token-specific backtest; nothing here claims token-specific validation"}),
                                   "cohort": {k: v for k, v in (st.get("historical_evidence") or {}).items() if k != "returns"} or None,
                                   "strategies": shared.get("strategies")},
           "token_signals": {"evidence_class": "FACT (closed bars) / HEURISTIC (strategy rules)", **(a.get("token_signals") or {}),
                             "note": "states of the tested setups on this token's closed bars; a state is not validation"} if a.get("token_signals") else None,
           "execution_quote": {"evidence_class": "FACT", "source": prov.get("quotes"), "observed_at_utc": utc((a.get("snapshot") or {}).get("quote_at")),
                               "quotes": [{"size_usd": q[0], "proceeds_usd": _f(q[1]), "impact": q[2], "status": q[3]} for q in a.get("sell_quotes") or []]},
           "stress": {"evidence_class": "INFERENCE (model) / HEURISTIC (decision)", "decision": st.get("decision"), "decision_reasons": st.get("decision_reasons"),
                      "probabilities": st.get("probabilities"), "max_size": st.get("max_size"), "size_curve": st.get("size_curve"),
                      "executable_vs_paper": _executable_vs_paper(st), "scenarios": _stress_table(st),
                      "sensitivity": {"improves": st.get("improves"), "deteriorates": st.get("deteriorates")},
                      "flags": a.get("flags") or []} if st else None,
           "trade_conditions": {"evidence_class": "FACT (lab output) / INFERENCE (caps)", "lab_entry": prov.get("lab_entry"),
                                "invalidation_price": (a.get("snapshot") or {}).get("invalidation_price"),
                                "max_size_usd_under_caps": _f((st.get("max_size") or {}).get("max_size_usd")), "caps": (st.get("max_size") or {}).get("constraints"),
                                "note": "conditions under which the evidence would be stronger or the idea wrong; not an instruction to trade"} if st else None,
           "catalysts": catalysts(con, a.get("chain") or "solana", a.get("mint") or lab.get("mint") or "", lab_db=lab_db, extra=extra_catalysts) if con is not None else None,
           "alternate_explanations": {"evidence_class": "HEURISTIC", "items": _alternates(a) if a.get("stress") else []},
           "uncertainty": {"evidence_class": "UNKNOWN", "items": _uncertainty(a) if a.get("stress") else
                           ["the assessment did not run (" + str(a.get("state") or "NOT_ASSESSED") + "); there is no backtest, stress or quote result to show"]},
           "coverage": shared.get("coverage"),
           "disclosure": DISCLOSURE}
    if override:
        doc["headline"]["label"], doc["headline"]["why"] = "FATAL FLAW", "fatal flag present but a downstream result disagreed; the veto stands (override detected)"
    return doc


# ---------------------------------------------------------------- schema (structural; no third-party validator needed)

REQUIRED = {"schema": str, "engine_version": str, "token": dict, "trace": dict, "headline": dict, "lab": dict, "historical_evidence": dict,
            "execution_quote": dict, "catalysts": (dict, type(None)), "alternate_explanations": dict, "uncertainty": dict, "disclosure": str}
REQUIRED_SUB = {"token": ("chain", "mint", "as_of_utc"), "trace": ("request_key", "assessment_state", "assessment_tier"),
                "headline": ("label", "why", "good_project", "good_entry", "mismatch"), "lab": ("score", "status", "fatal_flags", "fatal_override_detected"),
                "historical_evidence": ("token_specific", "cohort", "strategies")}


def validate(doc: dict) -> list[str]:
    errs = []
    for k, t in REQUIRED.items():
        if k not in doc:
            errs.append(f"missing {k}")
        elif not isinstance(doc[k], t):
            errs.append(f"{k} has type {type(doc[k]).__name__}")
    for k, subs in REQUIRED_SUB.items():
        for s in subs:
            if isinstance(doc.get(k), dict) and s not in doc[k]:
                errs.append(f"missing {k}.{s}")
    if doc.get("schema") != SCHEMA:
        errs.append("wrong schema id")
    if (doc.get("headline") or {}).get("label") not in LABELS:
        errs.append("unknown label")
    return errs


def json_schema() -> dict:
    """The same contract in JSON Schema form, for other tools (docs/backtesting/REPORT_SCHEMA.json)."""
    tmap = {str: "string", dict: "object"}
    props = {k: ({"type": tmap[t]} if not isinstance(t, tuple) else {"type": ["object", "null"]}) for k, t in REQUIRED.items()}
    for k, subs in REQUIRED_SUB.items():
        props[k]["required"] = list(subs)
    props["schema"]["const"] = SCHEMA
    props["headline"]["properties"] = {"label": {"enum": list(LABELS)}}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA, "type": "object", "required": list(REQUIRED), "properties": props}


# ---------------------------------------------------------------- Markdown

def _pct(x, nd=1):
    return "n/a" if x is None else f"{x * 100:+.{nd}f}%"


def _usd(x):
    return "n/a" if x is None else f"${x:,.0f}"


def render_md(doc: dict) -> str:
    t, tr, h, lab = doc["token"], doc["trace"], doc["headline"], doc["lab"]
    L = [f"# Backtest and stress: {t.get('symbol') or '?'} `{t.get('chain')}:{t.get('mint')}`", "",
         f"As of {t.get('as_of_utc') or 'n/a'}. Assessment {tr['assessment_state']}, evidence {tr['assessment_tier']}, request {str(tr.get('request_key'))[:16]}, engine {doc['engine_version']}.", "",
         f"{doc['disclosure']}", "", "## Headline (HEURISTIC)", "",
         f"Label: {h['label']}. Why: {h['why']}.",
         f"Project (lab view, unchanged): score {lab.get('score')}, status {lab.get('status')}, {h['good_project']['reads_as']}.",
         f"Entry (execution view): {h['good_entry']['label']}, stress {h['good_entry']['stress_decision'] or 'n/a'}, size under caps {_usd(h['good_entry']['max_size_usd_under_caps'])}."]
    if h.get("mismatch"):
        L.append(h["mismatch"] + ".")
    if lab.get("fatal_flags"):
        L.append(f"Lab fatal flags: {', '.join(lab['fatal_flags'])}. Override detected: {'yes' if lab['fatal_override_detected'] else 'no'}.")
    if tr.get("reason"):
        L.append(f"Not assessed because: {tr['reason']} (retriable: {tr.get('retriable')}).")
    he = doc["historical_evidence"]
    L += ["", "## Historical evidence", "", f"Token-specific: {he['token_specific'].get('state')} ({he['token_specific'].get('note') or 'no note'})."]
    if he.get("cohort"):
        c = he["cohort"]
        L.append(f"Cohort of past tokens with lab status {c.get('status')}: {c.get('n')} cases, tier {c.get('tier')} (minimum {c.get('min_n')})."
                 + (" Returns over {h} h, p10 / p50 / p90: {r}; worst drop p10 / p50: {w}. Mid prices before costs.".format(
                     h=c.get("horizon_h"), r=" / ".join(_pct(x) for x in c.get("ret_p10_p50_p90") or []), w=" / ".join(_pct(x) for x in c.get("worst_drop_p10_p50") or []))
                    if c.get("tier") == "HISTORICAL_COHORT" else ""))
    s = he.get("strategies")
    if s:
        L += ["", f"Strategies over the lab's whole discovery universe (net of modeled costs, ranked by net; paper is mid to mid before costs; "
              f"under {s['min_rank_trades']} trades is listed, not ranked):", ""]
        for r in s["runs"]:
            pos = f"#{r['rank_by_net']}" if r["rank_by_net"] else "not ranked"
            L.append(f"- {pos} {r['strategy']}: {r['n_trades']} trades, net {_pct(r['net_mean_ret'])}, paper {_pct(r['paper_mean_ret_mid'])}"
                     + (f" (paper rank {r.get('rank_by_paper')})" if r.get("rank_by_paper") else "") + f", {r['flag']}, run {r['run_id'][:10]}, ledger {str(r['ledger_hash'])[:10]}")
        if s.get("paper_only_profit"):
            L.append(f"Profitable on paper but not after costs: {', '.join(s['paper_only_profit'])}. Ranked by net, not by paper.")
        v = s.get("validation")
        if v:
            L += ["", f"Sealed-test validation ({v['file']}, sha256 {str(v['sha256'])[:12]}, pre-registration {str(v['prereg_sha256'])[:12]}, {v['total_trials']} trials counted):"]
            for sid, x in v["strategies"].items():
                L.append(f"- {sid}: {x['verdict']}, test {x['sealed_test_from']} to {x['sealed_test_to']}, {x['test_trades']} trades, mean {_pct(x['test_mean_ret'])}, "
                         f"enter-at-discovery baseline {_pct(x['baseline_enter_at_discovery_mean_ret'])}")
            if v.get("walk_forward"):
                w = v["walk_forward"]
                ci = " to ".join(_pct(x) for x in w["ci95"]) if w.get("ci95") else "n/a"
                L.append(f"- Walk-forward {w['strategy']}: {w['pooled_oos_trades']} out-of-sample trades, mean {_pct(w['pooled_oos_mean_ret'])}, 95% interval {ci}")
    ts = doc.get("token_signals")
    if ts:
        L += ["", "## Token signal states (not validation)", "", f"{ts.get('closed_bars')} closed hourly bars, {ts.get('dropped_unclosed')} unfinished bar(s) dropped. "
              + ", ".join(f"{k} {v}" for k, v in (ts.get("signals") or {}).items()) + "."]
    eq = doc["execution_quote"]
    L += ["", "## Execution quote now (FACT)", "", f"Source: {eq.get('source') or 'n/a'}, observed {eq.get('observed_at_utc') or 'n/a'}."]
    L.append("Proceeds are the quoted SOL converted at the bundle's SOL price.")
    L += [f"- sell ${q['size_usd']:,.0f}: " + (f"proceeds {_usd(q['proceeds_usd'])}, impact {q['impact']}" if q["proceeds_usd"] is not None else f"no quote ({q['status']})")
          for q in eq["quotes"]] or ["- no quote in the analysis bundle"]
    st = doc.get("stress")
    if st:
        L += ["", "## Adverse stress (hypothetical, no probabilities)", "", f"Decision {st['decision']}: {'; '.join(st.get('decision_reasons') or [])}.",
              f"Probabilities: {st.get('probabilities')}.", "", "Executable proceeds versus paper value (BASE, exit right away):"]
        L += [f"- ${r['size_usd']:,.0f}: paper {_usd(r['paper_value_mid_usd'])}, executable {_usd(r['executable_proceeds_usd'])}, net {_pct(r['net_ret'])}, fee {r['swap_fee']} ({r['fee_basis']})"
              for r in st["executable_vs_paper"]]
        worst = {}
        for r in st["scenarios"]:
            if r["net_ret"] is not None and (r["scenario"] not in worst or r["net_ret"] < worst[r["scenario"]]["net_ret"]):
                worst[r["scenario"]] = r
        L += ["", "Worst net return per scenario across sizes:"]
        L += [f"- {k}: {_pct(v['net_ret'])} at ${v['size_usd']:,.0f}" for k, v in worst.items()]
        not_filled = sorted({r["scenario"] for r in st["scenarios"] if r["status"] != "FILLED"})
        if not_filled:
            L.append(f"No exit at all under: {', '.join(not_filled)}.")
        L += ["", "Would improve the view: " + "; ".join(st["sensitivity"].get("improves") or []) + ".",
              "Would worsen it: " + "; ".join(st["sensitivity"].get("deteriorates") or []) + "."]
        if st.get("flags"):
            L.append(f"Flags beside the score: {', '.join(st['flags'])}.")
    tc = doc.get("trade_conditions")
    if tc:
        le = tc.get("lab_entry") or {}
        L += ["", "## Conditions (not instructions)", "", f"Lab entry condition: {le.get('condition') or 'none defined'}.",
              f"Invalidation: {le.get('invalidation') or 'n/a'} (level {tc.get('invalidation_price')}).",
              f"Largest size inside the caps {tc.get('caps')}: {_usd(tc.get('max_size_usd_under_caps'))}."]
    ca = doc.get("catalysts")
    if ca is not None:
        L += ["", "## Catalyst provenance", ""]
        L += [f"- {r['capture_method']} {r['origin']}: first known {r['first_known_at']}, available {r['available_at']}, published (claim) {r['published_claim']}, "
              f"confidence {r['publication_confidence']}, collector {r['collector_run_status']}" + (f"; {'; '.join(r['warnings'])}" if r["warnings"] else "") for r in ca["records"]]
        if ca.get("note"):
            L.append(ca["note"] + ".")
        L.append("Collector status: " + " ".join(f"{k}: {v}" for k, v in ca["collector_status"].items()))
    L += ["", "## Alternate explanations (HEURISTIC)", ""] + [f"- {x}" for x in doc["alternate_explanations"]["items"] or ["none generated (no assessment)"]]
    L += ["", "## Uncertainty (UNKNOWN)", ""] + [f"- {x}" for x in doc["uncertainty"]["items"]]
    cv = doc.get("coverage")
    if cv:
        L += ["", "## Coverage", "", f"{cv['bars']:,} hourly bars over {cv['mints_with_bars']} mints, {cv['bars_from']} to {cv['bars_to']}; "
              f"universe {cv['universe_rows']:,} records over {cv['universe_mints']} mints. Blocked: {', '.join(cv['blocked_sources'])}. {cv['survivorship']}."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- scout section and alerts

def scout_section(results: list[dict]) -> dict:
    """Every analyzed mint, assessed or not. A mint without an assessment is UNTESTED, never left out."""
    rows = []
    for r in results:
        a = r.get("backtest_assessment")
        fatal = [f["flag"] for f in (r.get("score") or {}).get("fatal_flags") or []]
        lab = {"score": (r.get("score") or {}).get("total"), "status": (r.get("status") or {}).get("status"), "fatal_flags": fatal}
        lbl = alert_label(a, fatal)
        pe = project_vs_entry(a, lab, lbl)
        st = (a or {}).get("stress") or {}
        rows.append({"symbol": ((r.get("bundle") or {}).get("identity") or {}).get("symbol"), "chain": (r.get("bundle") or {}).get("chain") or "solana",
                     "mint": r.get("mint"), "lab_score": lab["score"], "lab_status": lab["status"], "label": lbl["label"], "why": lbl["why"],
                     "state": (a or {}).get("state") or "NOT_ASSESSED", "tier": (a or {}).get("tier") or "UNAVAILABLE", "stress_decision": st.get("decision"),
                     "max_size_usd_under_caps": _f((st.get("max_size") or {}).get("max_size_usd")), "request_key": (a or {}).get("request_key"),
                     "mismatch": pe["mismatch"]})
    return {"schema": SCOUT_SCHEMA, "rows": rows, "counts": {k: sum(1 for x in rows if x["label"] == k) for k in LABELS}, "disclosure": DISCLOSURE}


def render_scout_section(sec: dict) -> str:
    L = ["## Backtest and stress (research only)", "", sec["disclosure"], "",
         "Labels: " + ", ".join(f"{k} {v}" for k, v in sec["counts"].items()) + ". Project view is the lab's score and status; entry view is execution under stress.", ""]
    for x in sec["rows"]:
        L.append(f"- {x['symbol']} `{x['chain']}:{x['mint']}`: {x['label']} ({x['why']}). Lab {x['lab_score']} / {x['lab_status']}; "
                 f"assessment {x['state']}, evidence {x['tier']}, stress {x['stress_decision'] or 'n/a'}, size under caps {_usd(x['max_size_usd_under_caps'])}"
                 + (f", request {x['request_key'][:12]}" if x["request_key"] else "") + (f". {x['mismatch']}" if x["mismatch"] else "")
                 + (f". Report {x['report']}" if x.get("report") else "") + ".")
    if not sec["rows"]:
        L.append("- no mint analyzed in this run")
    if sec.get("error"):
        L.append(f"- {sec['error']}")
    return "\n".join(L) + "\n"

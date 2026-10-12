"""Phase 13: social findings become research candidates next to the existing scout and catalyst workflows.

Pure engine: no I/O, no clock. The store (research_store.py) reads Phase 07 narrative snapshots, Phase 12 chronology
flags and the existing rejections and theses; the scout and catalyst commands supply the tokens they already evaluated.

What this adds and what it never does (DECISIONS D-085 to D-089):
  - Three lanes stay apart on every candidate:
      (a) narrative attention   from social findings only (originators, independent corroboration, freshness)
      (b) token structure       copied from the existing pipeline verdict (fatal flags), never recomputed here
      (c) executable entry      copied from the existing status (NEAR ENTRY / ENTRY CONDITIONS MET), never recomputed
    No lane reads another. High attention cannot clear a fatal flag, and a missing social signal costs nothing.
  - Identity is exact (chain, contract). A ticker-only mention stays UNRESOLVED and never reaches a ranked list.
    A finding whose symbol matches an analyzed token on a different contract is a possible spoof and inherits nothing.
  - The attention weight is a HEURISTIC that orders the social section only. It is never added to the m24 score,
    never changes a status, a rank, the watchlist or a rejection, and has zero trade execution impact.
  - With the feature off, or with no social data, the existing output is unchanged; the social section is either
    absent (off) or a one-line explicit no-op (on, nothing to attach).
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

ENGINE_VERSION = "research-v1"
POLICY_SCHEMA = "memelab.social.research.policy/1"

DEFAULT_POLICY: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "policy_version": "default-1",
    "enabled": False,                       # opt-in: the scout and catalyst commands also need --social, or this set to true
    "signals": {"narratives": True, "chronology_flags": True},
    "max_age_hours": 48.0,                  # newest observation older than this at as_of: the attention lane is STALE
    "corroborated_min_independent": 2,      # independent sources needed for CORROBORATED
    "include_fixtures": False,              # fixture snapshots and flags are ignored unless a demo or a test asks
    "weights": {                            # HEURISTIC; orders the social section only
        "per_independent_source": 1.0,
        "independent_source_cap": 5,
        "confidence": {"HIGH": 3.0, "MODERATE": 2.0, "LOW": 1.0, "UNKNOWN": 0.0},
        "conflicted": -2.0,
        "per_risk_flag": -1.0,
    },
    "trade_execution_impact": "none",       # fixed. Any other value is refused.
}

ATTENTION_LEVELS = ("NONE", "UNRESOLVED", "NOT_ESTIMABLE", "STALE", "CONFLICTED", "EMERGING", "CORROBORATED")
STRUCTURE = ("ACCEPTABLE", "FATAL", "NOT_EVALUATED")
ENTRY = ("ATTRACTIVE", "NOT_YET", "NOT_EVALUATED")
STATES = ("RESEARCH_CANDIDATE", "REJECTED_STRUCTURE", "NEEDS_STRUCTURAL_ANALYSIS", "NO_SOCIAL_SIGNAL")
ATTRACTIVE_STATUSES = ("NEAR ENTRY", "ENTRY CONDITIONS MET", "WATCH_FOR_ENTRY")
PROMO_FLAGS = ("burst_amplification", "identical_text_multi_source")
FORBIDDEN_POLICY_KEYS = ("score", "status", "rank", "watchlist", "fatal", "size", "position", "execute", "order")


class PolicyError(ValueError):
    pass


def _sha(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _merge(base: dict, over: dict, path: str = "") -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k not in base:
            raise PolicyError(f"unknown policy key {path}{k}")
        if isinstance(base[k], dict):
            if not isinstance(v, dict):
                raise PolicyError(f"policy key {path}{k} must be an object")
            out[k] = _merge(base[k], v, f"{path}{k}.")
        else:
            out[k] = v
    return out


def make_policy(override: dict | None = None, *, source: str = "default", path: str | None = None) -> dict:
    """Effective policy plus provenance (where it came from and its hash). Unknown keys, keys that would reach the
    score, status, rank, watchlist or execution, and any execution impact other than 'none' are refused."""
    override = dict(override or {})
    for k in list(override):
        if any(w in k.lower() for w in FORBIDDEN_POLICY_KEYS) and k not in DEFAULT_POLICY:
            raise PolicyError(f"policy key {k} would reach the score, status, ranking or execution; social findings never do")
    p = _merge(DEFAULT_POLICY, override)
    if p["trade_execution_impact"] != "none":
        raise PolicyError("trade_execution_impact must be 'none': social findings never execute or size a trade")
    if p["schema"] != POLICY_SCHEMA:
        raise PolicyError(f"policy schema must be {POLICY_SCHEMA}")
    if not isinstance(p["max_age_hours"], (int, float)) or p["max_age_hours"] <= 0:
        raise PolicyError("max_age_hours must be a positive number")
    if not isinstance(p["corroborated_min_independent"], int) or p["corroborated_min_independent"] < 1:
        raise PolicyError("corroborated_min_independent must be a positive integer")
    for k, v in p["weights"].items():
        vals = v.values() if isinstance(v, dict) else [v]
        if any(not isinstance(x, (int, float)) for x in vals):
            raise PolicyError(f"weight {k} must be numeric")
    p["provenance"] = {"source": source, "path": path, "override_keys": sorted(override), "sha256": _sha({k: v for k, v in p.items() if k != "provenance"})}
    return p


# ---------- lanes ----------

def _key(chain: str | None, contract: str | None) -> tuple[str, str] | None:
    if not chain or not contract:
        return None
    ch = str(chain).lower()
    ct = str(contract)
    return (ch, ct.lower() if ct[:2].lower() == "0x" else ct)


def attention_lane(f: dict | None, policy: dict, as_of: float) -> dict:
    if f is None:
        return {"level": "NONE", "bucket": "UNKNOWN", "why": "no social finding for this exact contract", "independent_sources": None,
                "originators": [], "first_observed_at": None, "last_observed_at": None, "age_hours": None}
    last = f.get("last_observed_at")
    age = None if last is None else round((as_of - last) / 3600.0, 2)
    base = {"independent_sources": f.get("independent_source_count"), "originators": list(f.get("originators") or [])[:5],
            "first_observed_at": f.get("first_observed_at"), "last_observed_at": last, "earliest_published_at": f.get("earliest_published_at"),
            "age_hours": age, "confidence": f.get("confidence"), "freshness": f.get("freshness"), "item_count": f.get("item_count"),
            "amplifier_count": f.get("amplifier_count"), "stance": f.get("stance") or {}}
    if f.get("status") != "ok":
        return {**base, "level": "NOT_ESTIMABLE", "bucket": "UNKNOWN",
                "why": "independence and volume not estimable: " + ", ".join(f.get("reasons") or ["insufficient coverage"])}
    if f.get("freshness") == "STALE" or age is None or age > policy["max_age_hours"]:
        return {**base, "level": "STALE", "bucket": "FACT",
                "why": f"newest observation {('unknown' if age is None else f'{age:.1f} h')} before as_of; limit {policy['max_age_hours']:g} h"}
    if f.get("conflicted"):
        return {**base, "level": "CONFLICTED", "bucket": "FACT", "why": f"sources disagree: {json.dumps(f.get('stance') or {}, sort_keys=True)}"}
    n = f.get("independent_source_count") or 0
    if n >= policy["corroborated_min_independent"]:
        return {**base, "level": "CORROBORATED", "bucket": "INFERENCE", "why": f"{n} independent source(s), reposts and copies collapsed"}
    return {**base, "level": "EMERGING", "bucket": "INFERENCE", "why": f"{n} independent source(s); not corroborated"}


def structure_lane(ev: dict | None) -> dict:
    if ev is None:
        return {"verdict": "NOT_EVALUATED", "fatal_flags": [], "why": "the existing pipeline has not analyzed this contract in this run"}
    flags = list(ev.get("fatal_flags") or [])
    if flags or ev.get("untradeable"):
        return {"verdict": "FATAL", "fatal_flags": flags, "why": "existing fatal checks: " + (", ".join(flags) or "untradeable")}
    return {"verdict": "ACCEPTABLE", "fatal_flags": [], "why": "no fatal flag from the existing checks"}


def entry_lane(ev: dict | None) -> dict:
    if ev is None:
        return {"verdict": "NOT_EVALUATED", "status": None, "why": "not analyzed"}
    st = ev.get("status")
    if ev.get("fatal_flags") or ev.get("untradeable"):
        return {"verdict": "NOT_YET", "status": st, "why": "structure fails, so no entry is considered"}
    if st in ATTRACTIVE_STATUSES:
        return {"verdict": "ATTRACTIVE", "status": st, "why": f"existing status {st}"}
    return {"verdict": "NOT_YET", "status": st, "why": f"existing status {st}"}


def _weight(att: dict, risks: list[dict], policy: dict) -> float:
    w = policy["weights"]
    if att["level"] in ("NONE", "UNRESOLVED", "NOT_ESTIMABLE", "STALE"):
        return 0.0
    n = min(att.get("independent_sources") or 0, w["independent_source_cap"])
    v = n * w["per_independent_source"] + w["confidence"].get(att.get("confidence") or "UNKNOWN", 0.0)
    if att["level"] == "CONFLICTED":
        v += w["conflicted"]
    v += w["per_risk_flag"] * len(risks)
    return round(max(v, 0.0), 3)


def _rejection_review(ev: dict | None, prior: dict | None, att: dict, struct: dict) -> dict | None:
    if not prior:
        return None
    pf = sorted(prior.get("fatal_flags") or [])
    if ev is None:
        return {"verdict": "STANDS", "prior": prior, "why": "not re-analyzed in this run; social attention alone never reopens a rejection"}
    if struct["verdict"] == "FATAL":
        why = "structure still fails: " + ", ".join(struct["fatal_flags"] or ["untradeable"])
        if att["level"] not in ("NONE",):
            why += "; new social evidence does not reopen a rejection"
        return {"verdict": "STANDS", "prior": prior, "why": why}
    cleared = pf or ["prior rejection reason"]
    return {"verdict": "REOPEN_FOR_REVIEW", "prior": prior,
            "why": "structural evidence changed: " + ", ".join(cleared) + " no longer fired in the existing checks; the pipeline status stands as computed"}


def _risks(f: dict | None) -> list[dict]:
    out = []
    for fl in (f or {}).get("flags") or []:
        if fl.get("flag") in PROMO_FLAGS:
            out.append({"kind": "promotion_hypothesis", "flag": fl["flag"], "bucket": "HEURISTIC", "note": fl.get("note"), "source": "narratives"})
    for fl in (f or {}).get("chrono_flags") or []:
        if fl.get("category") == "RISK":
            out.append({"kind": "chronology_risk", "flag": fl["flag"], "bucket": fl.get("bucket"), "rule": fl.get("rule"), "note": fl.get("note"),
                        "evidence": fl.get("evidence"), "source": f"chronology run {fl.get('run_id')}"})
    return out


def _timeline(f: dict | None) -> list[dict]:
    out = []
    for fl in (f or {}).get("chrono_flags") or []:
        if fl.get("category") in ("CORROBORATION", "CONTEXT", "DATA_QUALITY"):
            out.append({"flag": fl["flag"], "category": fl["category"], "bucket": fl.get("bucket"), "at": fl.get("at"),
                        "order_status": fl.get("order_status"), "evidence": fl.get("evidence"), "source": f"chronology run {fl.get('run_id')}"})
    return out


# ---------- build ----------

def dedupe_findings(findings: list[dict]) -> list[dict]:
    """The same finding read twice (repeated ingest, same snapshot passed twice) counts once."""
    seen, out = set(), []
    for f in findings:
        k = (f.get("kind"), _key(f.get("chain"), f.get("contract")) or ("", str(f.get("symbol") or "").upper()),
             json.dumps(f.get("source") or {}, sort_keys=True))
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


def build(findings: list[dict] | None, evaluated: list[dict] | None, policy: dict, *, as_of: float, availability: dict | None = None,
          prior: dict[str, dict] | None = None) -> dict:
    """findings: social findings (CONTRACT or TICKER_ONLY); evaluated: tokens the existing workflow already evaluated.
    prior: earlier rejections by contract, for findings on tokens the workflow did not evaluate this run.
    Returns the research section. Same inputs give the same result_sha256."""
    prior = prior or {}
    availability = availability or {"status": "AVAILABLE", "reason": None}
    findings = dedupe_findings(list(findings or []))
    evaluated = list(evaluated or [])
    contract_f: dict[tuple, list[dict]] = {}
    tickers: dict[str, dict] = {}
    for f in findings:
        if f.get("kind") == "CONTRACT" and _key(f.get("chain"), f.get("contract")):
            contract_f.setdefault(_key(f["chain"], f["contract"]), []).append(f)
        else:
            sym = str(f.get("symbol") or "?").lstrip("$").upper()
            t = tickers.setdefault(sym, {"symbol": sym, "mentions": 0, "sources": []})
            t["mentions"] += int(f.get("mentions") or 1)
            t["sources"].append(f.get("source") or {})
    ev_by_key = {}
    for e in evaluated:
        k = _key(e.get("chain"), e.get("contract"))
        if k:
            ev_by_key.setdefault(k, e)
    sym_index: dict[str, list[tuple]] = {}
    for k, e in ev_by_key.items():
        if e.get("symbol"):
            sym_index.setdefault(str(e["symbol"]).lstrip("$").upper(), []).append(k)

    def pick(fs: list[dict]) -> dict:
        # one finding per contract: newest snapshot wins; ties by source id. Chronology flags are merged in.
        fs = sorted(fs, key=lambda f: (f.get("last_observed_at") or 0, json.dumps(f.get("source") or {}, sort_keys=True)))
        best = dict(fs[-1])
        best["chrono_flags"] = sorted({json.dumps(c, sort_keys=True) for f in fs for c in f.get("chrono_flags") or []})
        best["chrono_flags"] = [json.loads(c) for c in best["chrono_flags"]]
        return best

    cands = []
    for k in sorted(set(contract_f) | set(ev_by_key)):
        f = pick(contract_f[k]) if k in contract_f else None
        ev = ev_by_key.get(k)
        att = attention_lane(f, policy, as_of)
        st, en = structure_lane(ev), entry_lane(ev)
        risks = _risks(f)
        notes = []
        identity_warning = None
        sym = str((f or {}).get("symbol") or (ev or {}).get("symbol") or "").lstrip("$").upper() or None
        if f is not None and ev is None and sym and sym_index.get(sym):
            others = [o for o in sym_index[sym] if o != k]
            if others:
                identity_warning = "SYMBOL_COLLISION"
                notes.append(f"the symbol {sym} also names analyzed contract(s) {', '.join(o[1] for o in others)} on {', '.join(sorted({o[0] for o in others}))}; "
                             "this is a different contract (possible spoof) and inherits nothing from them")
        for fl in (f or {}).get("flags") or []:
            if fl.get("flag") == "ticker_collision":
                identity_warning = identity_warning or "SYMBOL_COLLISION"
                notes.append("the narrative engine saw this ticker on other contracts; clusters were kept apart by contract")
        if f is None:
            state = "NO_SOCIAL_SIGNAL"
        elif ev is None:
            state = "NEEDS_STRUCTURAL_ANALYSIS"
        elif st["verdict"] == "FATAL":
            state = "REJECTED_STRUCTURE"
            if att["level"] in ("CORROBORATED", "EMERGING", "CONFLICTED"):
                notes.append("narrative attention does not override a fatal flag")
        else:
            state = "RESEARCH_CANDIDATE"
        review = _rejection_review(ev, (ev or {}).get("prior_rejection") or prior.get(k[1]), att, st)
        if f is None and review is None:
            continue                      # no social signal and nothing to review: the existing workflow already reports it
        prov = []
        if f is not None:
            prov.append({"kind": "narrative_snapshot", **(f.get("source") or {})})
            for c in f.get("chrono_flags") or []:
                prov.append({"kind": "chronology_flag", "run_id": c.get("run_id"), "flag_key": c.get("flag_key"), "rule": c.get("rule")})
        if ev is not None:
            prov.append({"kind": "existing_evaluation", "workflow": ev.get("workflow"), "ref": ev.get("ref")})
        cands.append({
            "chain": k[0], "contract": k[1], "symbol": sym, "workflow": (ev or {}).get("workflow"),
            "research_state": state, "identity_warning": identity_warning,
            "lanes": {"narrative_attention": att, "token_structure": st, "executable_entry": en},
            "promotional_risks": risks, "timeline_evidence": _timeline(f),
            "attention_weight": _weight(att, risks, policy), "attention_weight_bucket": "HEURISTIC",
            "in_tradable_ranking": bool((ev or {}).get("in_tradable_ranking")),
            "existing_score": (ev or {}).get("score"), "existing_status": (ev or {}).get("status"),
            "rejection_review": review, "notes": notes, "provenance": prov, "is_fixture": bool((f or {}).get("is_fixture")),
            "trade_execution_impact": "none",
        })
    order = {"RESEARCH_CANDIDATE": 0, "NEEDS_STRUCTURAL_ANALYSIS": 1, "REJECTED_STRUCTURE": 2, "NO_SOCIAL_SIGNAL": 3}
    cands.sort(key=lambda c: (order[c["research_state"]], -c["attention_weight"], c["chain"], c["contract"]))
    unresolved = [{"symbol": s, "mentions": t["mentions"], "state": "UNRESOLVED", "bucket": "UNKNOWN",
                   "why": "ticker only, no contract on a stated chain; never ranked and never joined to a token",
                   "sources": sorted({json.dumps(x, sort_keys=True) for x in t["sources"]})}
                  for s, t in sorted(tickers.items())]
    no_op = None
    if availability.get("status") != "AVAILABLE":
        no_op = f"social source unavailable: {availability.get('reason')}"
    elif not findings:
        no_op = availability.get("reason") or "no social findings for this window"
    pol = {k: v for k, v in policy.items()}
    body = {"engine_version": ENGINE_VERSION, "as_of": as_of, "policy": pol, "availability": availability,
            "state": "NO_OP" if no_op else "OK", "no_op_reason": no_op,
            "candidates": [] if no_op else cands, "unresolved": [] if no_op else unresolved,
            "counts": {"findings": len(findings), "evaluated": len(evaluated),
                       "by_state": {s: sum(1 for c in ([] if no_op else cands) if c["research_state"] == s) for s in STATES}},
            "trade_execution_impact": "none",
            "separation": "attention, structure and entry are separate lanes; the attention weight never reaches the score, status, ranking, watchlist or execution"}
    body["input_sha256"] = _sha({"findings": findings, "evaluated": evaluated, "prior": prior, "as_of": as_of, "policy_sha": policy["provenance"]["sha256"]})
    body["result_sha256"] = _sha({k: v for k, v in body.items() if k != "result_sha256"})
    return body


# ---------- plain-English section ----------

def _t(ts: float | None) -> str:
    if ts is None:
        return "unknown"
    import time as _time
    return _time.strftime("%Y-%m-%d %H:%M UTC", _time.gmtime(ts))


def _line(c: dict) -> list[str]:
    a, s, e = c["lanes"]["narrative_attention"], c["lanes"]["token_structure"], c["lanes"]["executable_entry"]
    head = f"- {c['symbol'] or '?'} `{c['chain']}:{c['contract']}`"
    L = [head,
         f"  - Narrative attention: {a['level']} ({a['bucket']}). {a['why']}. First seen {_t(a.get('first_observed_at'))}, last seen {_t(a.get('last_observed_at'))}.",
         f"  - Token structure: {s['verdict']}. {s['why']}.",
         f"  - Executable entry: {e['verdict']}. {e['why']}."]
    if a.get("originators"):
        L.append("  - Originators: " + ", ".join(f"{o.get('source_id')} at {_t(o.get('event_time'))} ({o.get('basis')})" for o in a["originators"]))
    for r in c["promotional_risks"]:
        L.append(f"  - Promotional risk ({r['bucket']}, not proven): {r['flag']}" + (f". {r['note']}" if r.get("note") else ""))
    for t in c["timeline_evidence"][:5]:
        L.append(f"  - Timeline ({t['bucket']}, order {t['order_status']}): {t['flag']} at {_t(t.get('at'))}")
    if c["rejection_review"]:
        rv = c["rejection_review"]
        L.append(f"  - Earlier rejection: {rv['verdict']}. {rv['why']}.")
    for n in c["notes"]:
        L.append(f"  - Note: {n}.")
    if c["in_tradable_ranking"] or c["existing_status"]:
        L.append(f"  - Existing workflow, unchanged: score {c['existing_score']}, status {c['existing_status']}.")
    L.append(f"  - Attention weight (HEURISTIC, orders this section only): {c['attention_weight']:g}.")
    return L


def render(res: dict) -> str:
    p = res["policy"]
    L = ["## Social research candidates (opt-in)", "",
         "This section does not change the score, status, ranking, watchlist, rejections or any trade. "
         "Narrative attention, token structure and executable entry are reported separately.",
         f"- Policy {p['policy_version']} ({p['provenance']['source']}{', ' + p['provenance']['path'] if p['provenance'].get('path') else ''}), "
         f"sha256 {p['provenance']['sha256'][:12]}, engine {res['engine_version']}, as of {_t(res['as_of'])}."]
    if res["state"] == "NO_OP":
        L.append(f"- No-op: {res['no_op_reason']}. Nothing was attached and the report above is what the existing workflow produced.")
        return "\n".join(L) + "\n"
    groups = [("RESEARCH_CANDIDATE", "Attention on tokens whose structure passed the existing checks"),
              ("NEEDS_STRUCTURAL_ANALYSIS", "Attention on contracts not analyzed in this run (not tradable until analyzed)"),
              ("REJECTED_STRUCTURE", "Attention on tokens that failed the existing structural checks (hype does not override)"),
              ("NO_SOCIAL_SIGNAL", "Earlier rejections reviewed (no current social signal)")]
    for st, title in groups:
        cs = [c for c in res["candidates"] if c["research_state"] == st]
        if not cs:
            continue
        L += ["", f"### {title}", ""]
        for c in cs:
            L += _line(c)
    if res["unresolved"]:
        L += ["", "### Unresolved ticker-only mentions (no contract, never ranked)", ""]
        L += [f"- {u['symbol']}: {u['mentions']} mention(s). {u['why']}." for u in res["unresolved"]]
    if any(c["is_fixture"] for c in res["candidates"]):
        L += ["", "- Contains fixture data (not live provider data)."]
    return "\n".join(L) + "\n"

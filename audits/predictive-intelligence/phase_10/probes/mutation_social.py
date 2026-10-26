"""Phase 10 mutation probe: each mutation of memelab/predictive/socialcat.py must make tests/test_predictive_social.py fail.

Works on a temporary copy of the repository's tracked files plus the Phase 10 files and the committed outputs the last tests read
(the checkout is never edited), so it runs at HEAD. Writes a JSON report.

    python -B mutation_social.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SCP = "memelab/predictive/socialcat.py"
TEST = "tests/test_predictive_social.py"
EXTRA = [SCP, TEST,
         "audits/predictive-intelligence/phase_09/experiments/SEARCH_LEDGER.csv",
         "audits/predictive-intelligence/phase_10/experiments/SEARCH_LEDGER.csv",
         "audits/predictive-intelligence/phase_10/experiments/EXPERIMENT_REGISTRY.csv",
         "audits/predictive-intelligence/phase_10/experiments/SOCIAL_METRICS.csv",
         "audits/predictive-intelligence/phase_10/experiments/ABLATION.csv"]

MUTATIONS = [
    # parsing the lab's readings
    (SCP, "trend order changed", 'TREND = {"EXHAUSTION": 0.0, "STABILITY": 1.0, "ACCELERATION": 2.0}',
     'TREND = {"EXHAUSTION": 1.0, "STABILITY": 0.0, "ACCELERATION": 2.0}'),
    (SCP, "manipulation order changed", '"LIKELY MANUFACTURED": 2.0, "SEVERELY MANIPULATED": 3.0}', '"LIKELY MANUFACTURED": 1.5, "SEVERELY MANIPULATED": 3.0}'),
    (SCP, "snapshot contradiction accepted", 'elif snap is not None and snap.get("attention") is not None and str(snap.get("attention")).upper() != word:',
     "elif False:"),
    (SCP, "unknown trend word guessed", '        if word not in TREND:\n            v["sc_attention_trend_ord"] = (None, "UNPARSEABLE")',
     '        if word not in TREND:\n            v["sc_attention_trend_ord"] = (1.0, None)'),
    (SCP, "unknown line format guessed as not observed", "            return None, \"NOT_OBSERVED_BY_LAB\"\n        return None, \"UNPARSEABLE\"",
     "            return None, \"NOT_OBSERVED_BY_LAB\"\n        return None, \"NOT_OBSERVED_BY_LAB\""),
    (SCP, "P16 paid attention not suspect", "    if (paid == 1.0) or (mo is not None and mo >= 2.0):", "    if (mo is not None and mo >= 2.0):"),
    (SCP, "P16 manufactured flow not suspect", "    if (paid == 1.0) or (mo is not None and mo >= 2.0):", "    if (paid == 1.0) or (mo is not None and mo >= 3.0):"),
    (SCP, "P16 unknown paid counted as organic", '    elif paid == 0.0 and mo is not None:\n        v["sc_attention_suspect"] = (0.0, None)',
     '    elif mo is not None:\n        v["sc_attention_suspect"] = (0.0, None)'),
    (SCP, "suspect acceleration counted as organic", '    elif t_ != 2.0 or s_ == 1.0:\n        v["sc_organic_acceleration"] = (0.0, None)',
     '    elif t_ != 2.0:\n        v["sc_organic_acceleration"] = (0.0, None)'),
    (SCP, "unknown suspect counted as organic acceleration", '    else:\n        v["sc_organic_acceleration"] = (None, v["sc_attention_suspect"][1])',
     '    else:\n        v["sc_organic_acceleration"] = (1.0, None)'),
    (SCP, "MANIA counted as late", 'EARLY_STAGES = frozenset({"LAUNCH", "DISCOVERY", "EARLY_EXPANSION", "BROAD_ATTENTION", "MANIA"})',
     'EARLY_STAGES = frozenset({"LAUNCH", "DISCOVERY", "EARLY_EXPANSION", "BROAD_ATTENTION"})'),
    (SCP, "unknown lifecycle stage counted as early", '        else:\n            v["sc_lifecycle_late"] = (None, "UNPARSEABLE")',
     '        else:\n            v["sc_lifecycle_late"] = (0.0, None)'),
    (SCP, "search pages counted as channels", '        if SEARCH_RX.search(v):\n            srch = 1\n        elif', '        if SEARCH_RX.search(v):\n            srch = 1\n        if'),
    (SCP, "non-links counted as channels", '        elif v.strip().lower().startswith(("http://", "https://")):', "        else:"),
    (SCP, "'None' strings counted as set", '    return isinstance(v, str) and v.strip() not in ("", "None", "null", "NULL")', "    return isinstance(v, str) and v.strip() != \"\""),
    # narrative context of the decision's own export (P04, CX-10)
    (SCP, "CX-10 context commit not checked", '    if (context.get("commit") != dec.get("export_commit") or float(context.get("commit_time")) != Td',
     '    if (False or float(context.get("commit_time")) != Td'),
    (SCP, "CX-10 context time not checked", ' or float(context.get("commit_time")) != Td\n', ' or False\n'),
    (SCP, "CX-10 context blob not checked", '            or (dec.get("export_blob") and context.get("blob") != dec.get("export_blob"))):', "            or False):"),
    (SCP, "narrative snapshot after T accepted", "    if later:\n        return {n: (None, \"INCONSISTENT_TIME\") for n in names}", "    if False:\n        return {n: (None, \"INCONSISTENT_TIME\") for n in names}"),
    (SCP, "oldest narrative snapshot used", 's = max(rows, key=lambda r: (float(r["observed_at"]), int(_numtxt(str(r.get("id"))) or 0)))',
     's = min(rows, key=lambda r: (float(r["observed_at"]), int(_numtxt(str(r.get("id"))) or 0)))'),
    (SCP, "narrative first seen after T accepted", '    elif fs > Td:\n        out["sc_narrative_age_h"] = (None, "INCONSISTENT_TIME")', '    elif False:\n        out["sc_narrative_age_h"] = (None, "INCONSISTENT_TIME")'),
    (SCP, "unknown narrative lifecycle guessed", '(None, "NOT_OBSERVED_BY_LAB" if lc == "UNKNOWN" else "UNPARSEABLE")', "(2.0, None)"),
    # the as-of snapshot
    (SCP, "oldest visible decision used instead of the newest", "    elif decs:\n        dec = decs[-1]", "    elif decs:\n        dec = decs[0]"),
    (SCP, "P36 snapshot time check removed", '        if S._num(t_snap) and float(t_snap) > Td:', "        if False:"),
    (SCP, "previous decision is the first, not the latest", "                pd = prior[-1]", "                pd = prior[0]"),
    (SCP, "previous decision may share the decision time", '            prior = [d for d in decs if float(d["decision_time"]) < Td]',
     '            prior = [d for d in decs if float(d["decision_time"]) <= Td]'),
    (SCP, "trend change reversed", '                    vals["sc_d_attention_trend"] = _value(a - b, None, Td, pins)', '                    vals["sc_d_attention_trend"] = _value(b - a, None, Td, pins)'),
    (SCP, "reversal from any previous trend", 'vals["sc_attention_reversal"] = _value(float(b >= 1.0 and a == 0.0), None, Td, pins)',
     'vals["sc_attention_reversal"] = _value(float(a == 0.0), None, Td, pins)'),
    (SCP, "value available after the decision", '                vals[n] = _value(v, why, Td, ins + (', '                vals[n] = _value(v, why, Td + 1.0, ins + ('),
    (SCP, "non-finite value accepted", '    if v is not None and not math.isfinite(v):\n        raise SocialCatError', '    if False:\n        raise SocialCatError'),
    (SCP, "high attention class from suspect acceleration", '    if vals["sc_organic_acceleration"]["value"] == 1.0:', '    if vals["sc_attention_trend_ord"]["value"] == 2.0:'),
    # examples, models, cards
    (SCP, "attach ignores the decision time", ' or float(s["decision_time"]) != e.decision_time:\n            raise B.IdentityJoinError("socialcat-1',
     ':\n            raise B.IdentityJoinError("socialcat-1'),
    (SCP, "missing value becomes zero", 'x[c] = v["value"] if v["value"] is not None else float("nan")', 'x[c] = v["value"] if v["value"] is not None else 0.0'),
    (SCP, "a value without availability accepted", '            elif v["available_at"] is None:\n                raise SocialCatError', '            elif False:\n                raise SocialCatError'),
    (SCP, "allowlist removed", "    bad = [c for c in columns if c not in ALLOWED]\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 10 allowlist (NC2-SC",
     "    bad = []\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 10 allowlist (NC2-SC"),
    (SCP, "count gate on all training rows", "    g = B.gate(len(use), int(y.sum()))\n    if g:\n        return _card(kind, target, train, cutoff, {\"abstain\": g, \"spec\": spec}, n_used=len(use)",
     "    g = B.gate(len(train), int(y_all.sum()))\n    if g:\n        return _card(kind, target, train, cutoff, {\"abstain\": g, \"spec\": spec}, n_used=len(use)"),
    (SCP, "rule shrinkage removed", '"p": (sum(v) + M_SHRINK * b0) / (len(v) + M_SHRINK)}', '"p": sum(v) / len(v)}'),
    (SCP, "rule missing cell scored as a known cell", '        return "MISSING"\n    return f"T{int(a)}S{int(b)}"', '        return "T1S0"\n    return f"T{int(a)}S{int(b)}"'),
    (SCP, "required rows not enforced", '        ok = [i for i, e in enumerate(examples) if complete(e, spec["rows"])]', "        ok = list(range(n))"),
    (SCP, "P13 guard removed", 'early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]', "early = []"),
    (SCP, "card version check removed", 'if card.get("feature_set_sha") != feature_set_sha() or card.get("socialcat_version") != SOCIALCAT_VERSION:', "if False:"),
    (SCP, "scored rows standardised with their own statistics", 'Z = K.Prep.from_dict(body["prep"]).transform(matrix([examples[i] for i in ok], spec["columns"]))',
     'Z = K.Prep().fit(matrix([examples[i] for i in ok], spec["columns"])).transform(matrix([examples[i] for i in ok], spec["columns"]))'),
    (SCP, "boosted model reads the logistic body", '                p[ok] = T.Stumps.from_dict(body["stumps"]).predict_proba1(Z)', '                p[ok] = 0.5'),
    (SCP, "walk-forward index check removed", "        if want != got:\n            raise B.WalkForwardMismatch", "        if False:\n            raise B.WalkForwardMismatch"),
    (SCP, "degenerate test inverted", "return bool(q.size > 1 and np.ptp(q) == 0)", "return bool(q.size > 1 and np.ptp(q) > 0)"),
    (SCP, "alarm at or above the prevalence", 'a = r[model] > r["B0"]', 'a = r[model] >= r["B0"]'),
    (SCP, "negative lead time accepted", "                if lead < 0:\n                    raise SocialCatError", "                if False:\n                    raise SocialCatError"),
    (SCP, "campaign by mint only", '    return f"narrative:{e.narrative}" if e.narrative else f"mint:{e.mint}"', '    return f"mint:{e.mint}"'),
    # catalyst classifier
    (SCP, "P04 published time used as availability", 'for i in items if float(i["first_seen_at"]) <= Tq], Tq)',
     'for i in items if float(i.get("published_at") or i["first_seen_at"]) <= Tq], Tq)'),
    (SCP, "P04 page crawled after T used", 'for p in page_facts if float(p["fetched_at"]) <= Tq], Tq)', 'for p in page_facts], Tq)'),
    (SCP, "link made after T used", 'for k in links if float(k["linked_at"]) <= Tq], Tq)', 'for k in links], Tq)'),
    (SCP, "revisions after T used", 'for r in revisions if float(r["revised_at"]) <= Tq], Tq)', 'for r in revisions], Tq)'),
    (SCP, "P45 event without a source item classified", '    if not vis:\n        return {**base, "state": "NOT_AVAILABLE_AT_DECISION"', '    if False:\n        return {**base, "state": "NOT_AVAILABLE_AT_DECISION"'),
    (SCP, "P15 syndicated copies counted", '        if roles.get(i.get("id"), "ORIGINAL") not in INDEPENDENT_ROLES:\n            continue', '        if False:\n            continue'),
    (SCP, "P15 duplicate bodies counted", '        if (u and u in seen_urls) or (h and h in seen_hash):\n            continue', '        if (u and u in seen_urls):\n            continue'),
    (SCP, "P41 page-named contract accepted as identity", "    if strong and in_source:\n        ident = \"EXACT_MINT_IN_SOURCE\"", "    if strong and (in_source or on_page):\n        ident = \"EXACT_MINT_IN_SOURCE\""),
    (SCP, "ticker match accepted as identity", '    strong = [k for k in mine if k.get("link_type") == "NAMED_IN_SOURCE" and k.get("link_strength") == "STRONG"]', '    strong = list(mine)'),
    (SCP, "identity from any mint", '    mine = [k for k in lnks if k.get("mint") == mint and (k.get("chain") or "solana") == chain]', '    mine = list(lnks)'),
    (SCP, "P17 rumor verified", '    elif withdrawn or ev_status == "RUMOR":', '    elif withdrawn:'),
    (SCP, "P17 denial ignored", '    elif withdrawn or ev_status == "RUMOR":', '    elif ev_status == "RUMOR":'),
    (SCP, "deleted source not a withdrawal", 'WITHDRAW_KINDS = frozenset({"DENIED", "CANCELLED", "DELETED_SOURCE"})', 'WITHDRAW_KINDS = frozenset({"DENIED", "CANCELLED"})'),
    (SCP, "evidence from the row edited later", '    if event.get("updated_at") is not None and float(event["updated_at"]) <= T:', '    if event.get("updated_at") is not None:'),
    (SCP, "oldest evidence revision used", 'return str(max(ev, key=lambda r: (float(r["revised_at"]), r.get("id") or 0))["new_value"])',
     'return str(min(ev, key=lambda r: (float(r["revised_at"]), r.get("id") or 0))["new_value"])'),
    (SCP, "single source verified", '    elif not (official or len(indep) >= 2):', '    elif not (official or len(indep) >= 1):'),
    (SCP, "unverified catalyst allowed a probability", '"probability_allowed": state == "VERIFIED", "reasons": reasons}', '"probability_allowed": True, "reasons": reasons}'),
    (SCP, "trader claim from a news source", '        if t == "BIG_TRADER_CLAIM" and not (groups & {"trader", "social"}):', '        if False:'),
    (SCP, "rumor type not first", '    if evidence_as_of == "RUMOR":\n        return "RUMOR", "evidence_status RUMOR as of T"', '    if False:\n        return "RUMOR", "evidence_status RUMOR as of T"'),
    # social adapter
    (SCP, "P36 observations after T visible", '        if o.get("ingested_at") is not None and float(o["ingested_at"]) <= Tq:', '        if o.get("ingested_at") is not None:'),
    (SCP, "resolution after T used", '        if float(r["resolved_at"]) > Tq:\n            continue', '        if False:\n            continue'),
    (SCP, "ticker mention used as identity", '        if r.get("mention_kind") == "TICKER":\n            ticker_items.add(r.get("item_key"))\n            continue',
     '        if r.get("mention_kind") == "TICKER":\n            ticker_items.add(r.get("item_key"))'),
    (SCP, "P17 deleted item counted", '        if any(o.get("retrieval_status") in GONE_RETRIEVAL for o in ob):\n            counts["deleted_before_t"] += 1\n            continue',
     '        if any(o.get("retrieval_status") in GONE_RETRIEVAL for o in ob):\n            counts["deleted_before_t"] += 1'),
    (SCP, "P03 edit used when no original is visible", '            if not orig:\n                counts["edited_without_original"] += 1\n                continue',
     '            if not orig:\n                counts["edited_without_original"] += 1\n                orig = vs'),
    (SCP, "P03 latest version used", '            chash = orig[0].get("content_hash")', '            chash = vs[-1].get("content_hash")'),
    (SCP, "P16 bots counted", '        if a.get("account_kind") in BOT_KINDS or a.get("identity_status") == "SUSPENDED":', '        if False:'),
    (SCP, "P15 duplicates counted", '        if chash and chash in seen_hash:\n            counts["duplicates_collapsed"] += 1\n            continue',
     '        if False:\n            counts["duplicates_collapsed"] += 1\n            continue'),
    (SCP, "trader link after T used", '        if float(ta["linked_at"]) <= Tq:\n            trader_of', '        if True:\n            trader_of'),
    (SCP, "P26 model-extracted claims used", '        if c.get("item_key") in llm_items or c.get("extraction_id") in llm_ids:\n            llm_excluded += 1\n            continue',
     '        if False:\n            llm_excluded += 1\n            continue'),
    (SCP, "track record includes calls not matured by T", 'and float(r["called_at"]) < Tq and float(r["matured_at"]) <= Tq]', 'and float(r["called_at"]) < Tq]'),
    (SCP, "verified trader without a check by T", '"verified": a.get("identity_status") == "VERIFIED" and a.get("identity_checked_at") is not None\n                          and float(a["identity_checked_at"]) <= Tq,',
     '"verified": a.get("identity_status") == "VERIFIED",'),
    (SCP, "read-only open removed", '    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)', "    con = sqlite3.connect(str(p))"),
    (SCP, "lab database accepted as a social store", '    if p == (repo / "data" / "memelab.sqlite").resolve():\n        raise SocialCatError', '    if False:\n        raise SocialCatError'),
    # proposals
    (SCP, "follow-through starts before availability", '    path = sorted((c for c in candles if float(c["t"]) >= start), key=lambda c: float(c["t"]))',
     '    path = sorted((c for c in candles if float(c["t"]) >= float(available_at) - 600), key=lambda c: float(c["t"]))'),
    (SCP, "ambiguous bar counted positive", '            return {**base, "label": 0, "state": "AMBIGUOUS_BAR", "touch_t": float(c["t"])}', '            return {**base, "label": 1, "state": "AMBIGUOUS_BAR", "touch_t": float(c["t"])}'),
    (SCP, "short path labelled negative", '        return {**base, "label": None, "state": "PENDING_OR_CENSORED"}', '        return {**base, "label": 0, "state": "PENDING_OR_CENSORED"}'),
    (SCP, "withdrawal pending read as negative", '        return {**base, "label": None, "state": "PENDING"}', '        return {**base, "label": 0, "state": "PENDING"}'),
]

# Equivalent mutations, run and reported but not counted: removing fit's own maturity check leaves `check_asof(..., as_of=cutoff,
# with_labels=True)` in front of it, which refuses a label maturing after the cutoff first (as in Phase 08, PI-D-052 item 1).
EQUIVALENT = [
    (SCP, "training maturity check removed (equivalent)", '        if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):\n            raise B.BaselineError(f"training row {e.decision_key[:12]} is not decided before and matured by the cutoff (P05, P43)")\n    y_all',
     '        if False:\n            raise B.BaselineError("x")\n    y_all'),
]


def main() -> int:
    out = Path(sys.argv[1])
    files = subprocess.run(["git", "ls-files", "memelab", "tests"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    files += EXTRA
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in sorted(set(files)):
            src = REPO / f
            if src.is_file():
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, root / f)
        (root / "data").mkdir(exist_ok=True)
        if (REPO / "data/memelab.sqlite").is_file():
            shutil.copy2(REPO / "data/memelab.sqlite", root / "data/memelab.sqlite")
        orig = {p: (root / p).read_text() for p in (SCP,)}
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-2000:])
        for path, name, old, new in MUTATIONS + EQUIVALENT:
            src = orig[path]
            if src.count(old) != 1:
                results.append({"file": path, "mutation": name, "applied": False, "caught": None, "note": f"pattern found {src.count(old)} times"})
                continue
            (root / path).write_text(src.replace(old, new))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
            results.append({"file": path, "mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:200]})
            (root / path).write_text(src)
    eq_names = {n for _, n, _, _ in EQUIVALENT}
    applied = [r for r in results if r["applied"] and r["mutation"] not in eq_names]
    rep = {"mutations": len(MUTATIONS), "applied": len(applied), "caught": sum(1 for r in applied if r["caught"]),
           "survived": [r["mutation"] for r in applied if not r["caught"]],
           "equivalent": [{"mutation": r["mutation"], "caught": r["caught"]} for r in results if r["mutation"] in eq_names],
           "not_applied": [r["mutation"] for r in results if not r["applied"]], "results": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "applied", "caught", "survived", "not_applied")}))
    return 0 if rep["caught"] == rep["mutations"] else 1


if __name__ == "__main__":
    sys.exit(main())

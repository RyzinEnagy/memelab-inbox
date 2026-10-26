"""Phase 10 skeptic (10b): own mutations of memelab/predictive/socialcat.py, each run
against tests/test_predictive_social.py in the skeptic's clone; the file is restored
with git checkout after each. usage: p10b_own_mutations.py CLONE OUT_JSON"""
import json, subprocess, sys, os
CLONE, OUT = sys.argv[1:3]
F = os.path.join(CLONE, 'memelab/predictive/socialcat.py')
MUT = [
 ("narrative snapshot 1h after T allowed", 'later = [r for r in rows if float(r["observed_at"]) > Td]', 'later = [r for r in rows if float(r["observed_at"]) > Td + 3600]'),
 ("one non-official source verifies", 'elif not (official or len(indep) >= 2):', 'elif not (official or len(indep) >= 1):'),
 ("edit versions recorded after T visible", 'vs = [v for v in vers_by.get(k, []) if float(v["first_recorded_at"]) <= Tq]', 'vs = list(vers_by.get(k, []))'),
 ("previous decision may be the decision itself", 'prior = [d for d in decs if float(d["decision_time"]) < Td]', 'prior = [d for d in decs if float(d["decision_time"]) <= Td]'),
 ("snapshot t up to a day after T accepted", 'if S._num(t_snap) and float(t_snap) > Td:', 'if S._num(t_snap) and float(t_snap) > Td + 86400:'),
 ("suspect acceleration counts as organic", 'elif t_ != 2.0 or s_ == 1.0:', 'elif t_ != 2.0:'),
 ("page-named mint is identity", 'if strong and in_source:', 'if strong and (in_source or on_page):'),
 ("track record includes calls not matured by T", 'and float(r["matured_at"]) <= Tq]', ']'),
 ("track record includes calls after T", 'float(r["called_at"]) < Tq and', ''),
 ("rumor treated as reported", 'elif withdrawn or ev_status == "RUMOR":', 'elif withdrawn:'),
 ("model-extracted claims kept", 'if c.get("item_key") in llm_items or c.get("extraction_id") in llm_ids:', 'if False:'),
 ("deleted items kept", 'if any(o.get("retrieval_status") in GONE_RETRIEVAL for o in ob):', 'if False:'),
 ("bot accounts kept", 'if a.get("account_kind") in BOT_KINDS or a.get("identity_status") == "SUSPENDED":', 'if False:'),
 ("crawled page after T counts", 'for p in page_facts if float(p["fetched_at"]) <= Tq]', 'for p in page_facts]'),
 ("search page counted as a channel", 'if SEARCH_RX.search(v):', 'if False:'),
 ("unknown lifecycle becomes early", 'elif str(stage) == "UNKNOWN":\n            v["sc_lifecycle_late"] = (None, "NOT_OBSERVED_BY_LAB")', 'elif str(stage) == "UNKNOWN":\n            v["sc_lifecycle_late"] = (0.0, None)'),
 ("missing organic reading becomes organic", 'v["sc_attention_paid"] = ((1.0 if og[0] == "paid/boosted" else 0.0), None) if og else (None, wo)', 'v["sc_attention_paid"] = ((1.0 if og[0] == "paid/boosted" else 0.0), None) if og else (0.0, None)'),
 ("observation ingested after T visible", 'if o.get("ingested_at") is not None and float(o["ingested_at"]) <= Tq:', 'if o.get("ingested_at") is not None:'),
]
src = open(F).read(); res = []
for name, a, b in MUT:
    n = src.count(a)
    if n != 1:
        res.append({"mutation": name, "applied": False, "count": n}); continue
    open(F, 'w').write(src.replace(a, b))
    r = subprocess.run([sys.executable, '-B', '-m', 'pytest', 'tests/test_predictive_social.py', '-q', '-x', '-p', 'no:cacheprovider'],
                       cwd=CLONE, capture_output=True, text=True, env=dict(os.environ, MEMELAB_DB='/tmp/claude-0/p10b/mut.db'))
    subprocess.run(['git', 'checkout', '-q', '--', 'memelab/predictive/socialcat.py'], cwd=CLONE, check=True)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    res.append({"mutation": name, "applied": True, "caught": r.returncode != 0, "result": last})
json.dump(res, open(OUT, 'w'), indent=1)
for x in res: print(x)

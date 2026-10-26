"""Phase 10 skeptic (10b): independent recomputation of every socialcat-1 value of the
240 development rows (SOCIAL_FEATURES_DEVELOPMENT.csv) from the Phase 05 store rows and
git objects of each decision's own export, with my own parsing (no memelab import).
Missing values compare as 'missing' regardless of reason text.
usage: p10b_features_indep.py REPO P05_COPY FEATURES_CSV"""
import csv, json, math, re, sqlite3, subprocess, sys, collections
REPO, P05, CSV = sys.argv[1:4]
def git(*a): return subprocess.run(['git', '-C', REPO, *a], capture_output=True, check=True).stdout
con = sqlite3.connect(P05)
ROWS = {r[0]: r for r in con.execute("select decision_key, chain, mint, decision_time, export_commit, row_json, token_json from predictive_decisions")}
bymint = collections.defaultdict(list)
for r in ROWS.values(): bymint[(r[1], r[2])].append(r)
ex_cache = {}
def export(c):
    if c not in ex_cache:
        d = json.loads(git('show', f'{c}:data/state/latest.json')); ex_cache[c] = d.get('_tables', d)
    return ex_cache[c]
def readings(rj):
    r = json.loads(rj); bd = json.loads(r.get('score_breakdown_json') or 'null')
    snap = json.loads(r.get('snapshot_json') or 'null') or {}
    L = lambda b: (bd.get(b) or {}).get('rationale', []) if isinstance(bd, dict) else []
    out = {}
    tr = [s.split()[-1] for s in L('attention_narrative') if s.startswith('attention trend ')]
    out['trend'] = {'EXHAUSTION': 0, 'STABILITY': 1, 'ACCELERATION': 2}.get(tr[0]) if tr else None
    if out['trend'] is not None and snap.get('attention') and snap['attention'].upper() != tr[0]: out['trend'] = None
    ns = [s[len('narrative strength '):] for s in L('attention_narrative') if s.startswith('narrative strength ')]
    out['strength'] = float(ns[0]) if ns else None
    pg = [s for s in L('attention_narrative') if s in ('attention organic', 'attention paid/boosted')]
    out['paid'] = (1.0 if pg[0].endswith('boosted') else 0.0) if pg else None
    mp = [s for s in L('demand_order_flow') if s.startswith('manipulation screen ')]
    lab = mp[0][len('manipulation screen '):].rsplit(' / wash', 1)[0] if mp else None
    out['manip'] = {'MOSTLY ORGANIC': 0, 'MIXED / UNCERTAIN': 1, 'LIKELY MANUFACTURED': 2, 'SEVERELY MANIPULATED': 3}.get(lab)
    p, m = out['paid'], out['manip']
    out['suspect'] = 1.0 if (p == 1.0 or (m is not None and m >= 2)) else (0.0 if (p == 0.0 and m is not None) else None)
    t = out['trend']
    out['accel'] = None if t is None else (0.0 if (t != 2 or out['suspect'] == 1.0) else (1.0 if out['suspect'] == 0.0 else None))
    st = snap.get('lifecycle')
    out['late'] = 1.0 if st in ('DISTRIBUTION', 'BREAKDOWN', 'POST_BREAKDOWN') else (0.0 if st in ('LAUNCH', 'DISCOVERY', 'EARLY_EXPANSION', 'BROAD_ATTENTION', 'MANIA') else None)
    lc = [re.search(r'\(confidence (\w+)\)', s) for s in L('lifecycle_relative_strength') if s.startswith('lifecycle ')]
    out['conf'] = {'LOW': 0, 'MODERATE': 1, 'HIGH': 2}.get(lc[0].group(1)) if lc and lc[0] else None
    out['t'] = snap.get('t')
    return out
def ok(v): return isinstance(v, str) and v.strip() not in ('', 'None', 'null', 'NULL')
def mine(dk):
    _, chain, mint, T, ec, rj, tj = ROWS[dk]
    R = readings(rj); tok = json.loads(tj) if tj else None
    v = {'sc_attention_trend_ord': R['trend'], 'sc_narrative_strength': R['strength'], 'sc_attention_paid': R['paid'],
         'sc_manipulation_ord': R['manip'], 'sc_attention_suspect': R['suspect'], 'sc_organic_acceleration': R['accel'],
         'sc_lifecycle_late': R['late'], 'sc_lifecycle_conf_ord': R['conf']}
    links = [tok.get(k) for k in ('website', 'twitter', 'telegram') if ok(tok.get(k))]
    srch = [u for u in links if re.search(r'search|[?&]q=', u, re.I)]
    v['sc_channels_n'] = float(sum(1 for u in links if u not in srch and u.lower().startswith('http')))
    v['sc_channel_search_url'] = 1.0 if srch else 0.0
    nid = tok.get('narrative_id'); v['sc_narrative_tagged'] = 1.0 if ok(nid) else 0.0
    for k in ('sc_narrative_lifecycle_ord', 'sc_narrative_age_h', 'sc_narrative_catalyst_kw_7d', 'sc_narrative_mcap_chg_24h_pct', 'sc_narrative_snapshot_age_h'): v[k] = None
    if ok(nid):
        tabs = export(ec)
        snaps = [s for s in tabs.get('narrative_snapshots', []) if s.get('narrative_id') == nid]
        meta = [n for n in tabs.get('narratives', []) if n.get('narrative_id') == nid]
        if not any(float(s['observed_at']) > T for s in snaps):
            if meta and meta[0].get('first_seen_at') is not None and float(meta[0]['first_seen_at']) <= T:
                v['sc_narrative_age_h'] = (T - float(meta[0]['first_seen_at'])) / 3600
            if snaps:
                s = max(snaps, key=lambda s: (float(s['observed_at']), int(s.get('id') or 0)))
                v['sc_narrative_lifecycle_ord'] = {'DEAD': 0, 'EXHAUSTING': 1, 'MATURE': 2, 'EMERGING': 3, 'ACCELERATING': 4, 'MANIA': 5}.get(s.get('lifecycle'))
                v['sc_narrative_catalyst_kw_7d'] = s.get('catalyst_events_7d')
                v['sc_narrative_mcap_chg_24h_pct'] = s.get('mcap_chg_24h_pct')
                v['sc_narrative_snapshot_age_h'] = (T - float(s['observed_at'])) / 3600
    prior = sorted([r for r in bymint[(chain, mint)] if r[3] < T], key=lambda r: r[3])
    v['sc_d_attention_trend'] = v['sc_attention_reversal'] = v['sc_d_narrative_strength'] = None
    if prior:
        P = readings(prior[-1][5])
        if R['trend'] is not None and P['trend'] is not None:
            v['sc_d_attention_trend'] = float(R['trend'] - P['trend'])
            v['sc_attention_reversal'] = 1.0 if (P['trend'] >= 1 and R['trend'] == 0) else 0.0
        if R['strength'] is not None and P['strength'] is not None:
            v['sc_d_narrative_strength'] = R['strength'] - P['strength']
    return v
def num(s):
    try: x = float(s); return x if math.isfinite(x) else None
    except (TypeError, ValueError): return None
diffs = []; n = 0; nonmissing = collections.Counter()
for row in csv.DictReader(open(CSV)):
    v = mine(row['decision_key'])
    for k, a in v.items():
        n += 1; b = num(row[k]); a = None if a is None else float(a)
        if a is not None: nonmissing[k] += 1
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-6 * max(1, abs(a))):
            diffs.append((row['decision_key'][:12], k, a, row[k]))
print(json.dumps({'values_compared': n, 'differences': len(diffs), 'examples': diffs[:15], 'nonmissing': nonmissing}, indent=1, default=str))

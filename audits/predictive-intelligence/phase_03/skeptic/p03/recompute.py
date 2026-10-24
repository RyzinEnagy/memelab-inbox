"""Skeptic P03: independent recomputation of SCORECARD.csv from SCORE_ITEMS.csv and RUBRIC_ITEMS.csv."""
import csv, sys, collections
base = sys.argv[1]
items = {r['item_id']: r for r in csv.DictReader(open(base + '/RUBRIC_ITEMS.csv'))}
si = list(csv.DictReader(open(base + '/SCORE_ITEMS.csv')))
sc = list(csv.DictReader(open(base + '/SCORECARD.csv')))
crit_order = ['temporal_integrity','transferable_outcomes','calibration_uncertainty','features','decision_execution','code_quality','integration_fit','reproducibility','license_security','cost_latency']
maxw = collections.defaultdict(int)
for r in items.values(): maxw[r['criterion']] += int(r['points'])
tot = collections.defaultdict(lambda: collections.defaultdict(int))
probs = []
seen = collections.Counter()
for r in si:
    seen[(r['repo'], r['item_id'])] += 1
    it = items[r['item_id']]
    p = int(r['points'])
    if p not in (0, int(it['points'])): probs.append(('partial', r['repo'], r['item_id']))
    if r['criterion'] != it['criterion']: probs.append(('crit', r['repo'], r['item_id']))
    if p and (not r['evidence'] or r['evidence'].startswith('no qualifying')): probs.append(('noevid', r['repo'], r['item_id']))
    tot[r['repo']][r['criterion']] += p
repos = {r['repo'] for r in si}
for rp in repos:
    for iid in items:
        if seen[(rp, iid)] != 1: probs.append(('missing_or_dup', rp, iid, seen[(rp, iid)]))
mism = 0
for r in sc:
    t = 0
    for c in crit_order:
        v = tot[r['repo']][c]
        t += v
        if int(r['lead_' + c]) != v: mism += 1; probs.append(('critmismatch', r['repo'], c, r['lead_' + c], v))
        if v > maxw[c]: probs.append(('over', r['repo'], c))
    if int(r['lead_total']) != t: mism += 1; probs.append(('totmismatch', r['repo'], r['lead_total'], t))
    # reviewer totals
    rt = sum(int(r['reviewer_' + c]) for c in crit_order if r['reviewer_' + c] not in ('', None))
    if str(rt) != r['reviewer_total']: probs.append(('revtot', r['repo'], r['reviewer_total'], rt))
weight_order = sorted(crit_order, key=lambda c: -maxw[c])
# lead tie-break doc: temporal, outcomes, calibration, features, decision, code, integration, reproducibility, license, cost
tb = ['temporal_integrity','transferable_outcomes','calibration_uncertainty','features','decision_execution','code_quality','integration_fit','reproducibility','license_security','cost_latency']
elig = [r for r in sc if r['eligible_for_top10'] == 'YES']
key = lambda r: tuple([-int(r['lead_total'])] + [-int(r['lead_' + c]) for c in tb] + [r['repo']])
mine = [r['repo'] for r in sorted(elig, key=key)]
published = [r['repo'] for r in sorted(elig, key=lambda r: int(r['eligible_rank']))]
print('repos', len(repos), 'rows', len(si), 'problems', len(probs))
for p in probs[:30]: print(' ', p)
print('top10 mine     ', mine[:10])
print('top10 published', published[:10])
print('order identical over all eligible:', mine == published)
print('weights', dict(maxw))

"""NEW A–E replication of documented mechanics, not recovered original cells.

Unspecified fields are chosen in inputs.json and disclosed explicitly. Imports
resolve from the clean pinned checkout, never from the supplied recovery folder.
"""
import argparse
import copy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from memelab.social import alpha_core as A, perf_core as C, perf_analysis as P

HERE = Path(__file__).resolve().parent
PIN = '698f73b854567ce60b56ce275b5ab6822a9d5f60'


def observe():
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == PIN
    inputs = json.loads((HERE/'inputs.json').read_text())
    series, rejected = A.prep_series({'series':[inputs['series']]})
    assert rejected == []
    ser = series[('solana','M00_SYNTHETIC_TOKEN')]
    alpha_policy = copy.deepcopy(A.DEFAULT_POLICY)
    adverse_policy = dict(alpha_policy, entry_price_rule='CANDLE_ADVERSE')
    perf_policy = dict(C.DEFAULT_POLICY, price_tolerance_s=inputs['wallet_mark_tolerance_s'])
    args = inputs['alpha']
    en, enerr = A.entry_for(ser,args['entry_t'],args['direction'],alpha_policy,args['as_of_open'])
    adv, adverr = A.entry_for(ser,args['entry_t'],args['direction'],adverse_policy,args['as_of_adverse'])
    ex, exerr = A.exit_for(ser,args['exit_t'],args['direction'],alpha_policy,args['as_of_open'])
    ledger = C.Ledger()
    price = dict(inputs['wallet_mark'], usd=D(inputs['wallet_mark']['usd']), idx=0)
    ledger.prices = [price]
    book = C.Book(ledger,perf_policy)
    t = inputs['wallet_mark_transaction_t']
    near = book.near('NATIVE',t)
    unit,basis = book.unit_usd('NATIVE',t)
    quote = dict(inputs['larger_quote'],amount_in=D(inputs['larger_quote']['amount_in']),usd_out=D(inputs['larger_quote']['usd_out']))
    qty,mark = D(inputs['holding_qty']),D(inputs['holding_mark_usd'])
    liquid = P.liquidation('M00_SYNTHETIC_TOKEN',qty,mark,quote,inputs['liquidation_as_of'],dict(C.DEFAULT_POLICY))
    missing = P.liquidation('M00_SYNTHETIC_TOKEN',qty,mark,None,inputs['liquidation_as_of'],dict(C.DEFAULT_POLICY))
    L = C.parse_ledger(copy.deepcopy(inputs['inventory_ledger_without_quote']))
    R = C.run_engine(L,dict(C.DEFAULT_POLICY),C.DEFAULT_POLICY['convention'])
    inventory = P.inventory_block(R,L.as_of,dict(C.DEFAULT_POLICY))
    assert len(inventory['assets']) == 1 and inventory['assets'][0]['qty_open'] == D(50)
    assert inventory['assets'][0]['qty_known_basis'] == D(50)
    boundary,boundaryerr = A.entry_for(ser,0,1,alpha_policy,3600)
    prior = C.Ledger();prior.prices=[dict(price,t=900,usd=D(7))]
    prior_usd,prior_basis = C.Book(prior,perf_policy).unit_usd('NATIVE',1000)
    exact = P.liquidation('M00_SYNTHETIC_TOKEN',D(100),mark,quote,1000,dict(C.DEFAULT_POLICY))
    data={'classification':inputs['classification'],'application_sha':PIN,'inputs_sha256':hashlib.sha256((HERE/'inputs.json').read_bytes()).hexdigest(),
          'resolved_policies':{'alpha_open':alpha_policy,'alpha_adverse':adverse_policy,'wallet':perf_policy,'inventory':dict(C.DEFAULT_POLICY)},
          'A':{'open':en,'open_error':enerr,'adverse':adv,'adverse_error':adverr},'B':{'exit':ex,'error':exerr},
          'C':{'near':near,'unit_usd':unit,'basis':basis,'causal_latest_mid_control':book.latest_mid('NATIVE',t)},
          'D':{'input_qty':qty,'quote':quote,'liquidation':liquid},
          'E':{'per_asset':missing,'empty_sum':P._sum([]),'inventory_integration_EXTENSION_NOT_ORIGINAL_PROBE':inventory},
          'controls':{'boundary':boundary,'boundary_error':boundaryerr,'prior_unit_usd':prior_usd,'prior_basis':prior_basis,'exact_size_quote':exact},
          'code_files':{}}
    for module in [A,C,P]:
        path=Path(module.__file__).resolve();assert path.is_relative_to(ROOT.resolve())
        rel=str(path.relative_to(ROOT.resolve()));blob=path.read_bytes()
        assert blob == subprocess.check_output(['git','show',PIN+':'+rel])
        data['code_files'][rel]=hashlib.sha256(blob).hexdigest()
    return data


def characterize(o):
    assert o['A']['open']['price']==10 and o['A']['open']['candle_t']==0 and o['A']['open']['fill_t']==1800
    assert o['A']['adverse']['price']==100 and o['A']['adverse_error'] is None
    assert o['B']['exit']['price']==10 and o['B']['exit']['t']==3000 and o['B']['exit']['candle_t']==0
    assert o['C']['near']['t']==1100 and o['C']['unit_usd']==D(100) and o['C']['basis']=='OBSERVED'
    assert o['D']['liquidation']['status']=='QUOTED_PRORATA' and o['D']['liquidation']['value']==D(50)
    assert 'lower bound' in o['D']['liquidation']['detail']
    assert o['E']['per_asset']['status']=='NO_QUOTE' and o['E']['per_asset']['value'] is None and o['E']['empty_sum']==0
    inv=o['E']['inventory_integration_EXTENSION_NOT_ORIGINAL_PROBE']
    assert inv['assets_without_executable_estimate']==1 and inv['assets'][0]['unrealized_executable_usd'] is None and inv['unrealized_executable_usd']==0
    c=o['controls'];assert c['boundary_error'] is None and c['boundary']['price']==10 and c['boundary']['fill_t']==0
    assert c['prior_unit_usd']==D(7) and c['prior_basis']=='OBSERVED' and c['exact_size_quote']['value']==D(100)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    data=observe();characterize(data)
    a.out.write_text(json.dumps(data,indent=2,default=str)+'\n')
    print('A–E documented mechanics MATCH new invented inputs; controls PASS; this is NOT application safety acceptance.')


if __name__=='__main__':main()

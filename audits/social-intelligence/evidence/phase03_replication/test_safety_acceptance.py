"""New safety expectations, intentionally RED on the unchanged audited code."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pytest
from probe_cases import observe, characterize


@pytest.fixture(scope='module')
def o():
    data=observe();characterize(data);return data


def test_A_prior_open_is_not_later_fill(o):
    got=o['A']['open']
    assert got is None or got['candle_t']>=1800, 'elapsed candle open is not a decision-time executable fill'


def test_A_uncompleted_high_is_not_known(o):
    assert o['A']['adverse'] is None, 'full-candle high cannot be known at t=1800 before candle end=3600'


def test_B_exit_cannot_use_elapsed_open(o):
    got=o['B']['exit']
    assert got is None or got['candle_t']>=3000, 'elapsed candle open is not a timed horizon exit'


def test_C_future_mark_is_not_observed_at_transaction(o):
    assert o['C']['near'] is None and o['C']['unit_usd'] is None, 'mark timestamp 1100 is later than transaction1000'


def test_D_other_size_quote_cannot_guarantee_lower_bound(o):
    x=o['D']
    assert x['quote']['amount_in']==x['input_qty'] or 'lower bound' not in x['liquidation']['detail'], 'other-size arithmetic alone does not establish an executable lower bound'


def test_E_all_unknown_open_positions_do_not_total_known_zero(o):
    inv=o['E']['inventory_integration_EXTENSION_NOT_ORIGINAL_PROBE']
    assert inv['unrealized_executable_usd'] is None, 'one known-basis open position has no quote; total must retain unknown'


def test_positive_boundary_prior_mark_exact_quote_and_unknown_flags(o):
    c=o['controls'];assert c['boundary']['candle_t']==c['boundary']['fill_t']==0
    assert o['C']['causal_latest_mid_control'] is None and str(c['prior_unit_usd'])=='7'
    assert str(c['exact_size_quote']['value'])=='100'
    inv=o['E']['inventory_integration_EXTENSION_NOT_ORIGINAL_PROBE']
    assert o['E']['per_asset']['value'] is None and inv['assets_without_executable_estimate']==1

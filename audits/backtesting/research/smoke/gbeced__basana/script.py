"""Smoke test: basana 1.11 backtesting fill timing on synthetic data (no network).

30 hourly bars, bar i: open=100+i, high=open+2, low=open-1, close=open+0.5, volume=1_000_000.
Case A (default exchange): market BUY placed in the bar-close handler of bar k=10 -> which price?
Case B (immediate_order_processing=True): same, -> which price?
Case C (async event): a non-bar event at begin(bar 20)+30min places a market BUY -> which bar/price?
Case D (VolumeShareImpact default): BUY sized at 20% of bar 11 volume -> slippage computed from bar 11's full volume.
"""
import asyncio
import datetime
from decimal import Decimal

import basana as bs
from basana.core import event as bs_event
import basana.backtesting.exchange as bx
from basana.backtesting import liquidity

T0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
H = datetime.timedelta(hours=1)
PAIR = bs.Pair("TOK", "USD")


def make_bars():
    src = bs_event.FifoQueueEventSource()
    for i in range(30):
        o = Decimal(100 + i)
        b = bs.Bar(T0 + i * H, PAIR, o, o + 2, o - 1, o + Decimal("0.5"), Decimal(1_000_000), H)
        src.push(bs.BarEvent(T0 + (i + 1) * H, b))  # event fires at bar close
    return src


class CatalystEvent(bs_event.Event):
    pass


async def run_case(name, k=10, iop=False, liq=liquidity.InfiniteLiquidity, amount=Decimal(1), async_at=None):
    d = bs.backtesting_dispatcher()
    ex = bx.Exchange(d, {"USD": Decimal(10**9)}, liquidity_strategy_factory=liq, immediate_order_processing=iop)
    ex.set_pair_info(PAIR, bs.PairInfo(base_precision=4, quote_precision=4))
    ex.add_bar_source(make_bars())
    state = {"placed_at": None, "fills": []}

    async def on_bar(ev):
        idx = int((ev.bar.begin - T0) / H)
        if async_at is None and idx == k:
            state["placed_at"] = (d.now(), f"close handler of bar {idx}")
            await ex.create_market_order(bs.OrderOperation.BUY, PAIR, amount)

    async def on_catalyst(ev):
        state["placed_at"] = (ev.when, "async catalyst event")
        await ex.create_market_order(bs.OrderOperation.BUY, PAIR, amount)

    async def on_order(ev):
        o = ev.order
        if o.amount_filled:
            state["fills"].append((ev.when, o.fill_price, o.amount_filled, ("open" if o.is_open else "closed")))

    ex.subscribe_to_bar_events(PAIR, on_bar)
    ex.subscribe_to_order_events(on_order)
    if async_at is not None:
        cs = bs_event.FifoQueueEventSource()
        cs.push(CatalystEvent(async_at))
        d.subscribe(cs, on_catalyst)
    await d.run()
    print(f"[{name}] order placed at {state['placed_at']}")
    for when, px, amt, st in state["fills"]:
        bar_idx = int((when - T0) / H) - 1
        print(f"[{name}]   fill event at {when.isoformat()} (bar {bar_idx} close event) price={px} amount={amt} state={st}")


async def main():
    print("bar 10: open=110 close=110.5 | bar 11: open=111 close=111.5 | bar 20: open=120 begin=", (T0 + 20 * H).isoformat())
    await run_case("A default next-bar")
    await run_case("B immediate_order_processing", iop=True)
    await run_case("C async event mid-bar-20", async_at=T0 + 20 * H + datetime.timedelta(minutes=30))
    await run_case("D VolumeShareImpact 50k of 1M bar-11 volume (20pct of 25pct cap)", liq=liquidity.VolumeShareImpact, amount=Decimal(50_000))

    # Case E: a strategy handler raises; default dispatcher logs and keeps going (stop_on_handler_exceptions=False).
    d = bs.backtesting_dispatcher()
    ex = bx.Exchange(d, {"USD": Decimal(1000)})
    ex.add_bar_source(make_bars())
    seen = []

    async def bad(ev):
        seen.append(ev.when)
        if len(seen) == 5:
            raise RuntimeError("strategy bug on bar 4")
    ex.subscribe_to_bar_events(PAIR, bad)
    import logging
    logging.disable(logging.CRITICAL)
    await d.run()
    print(f"[E handler exception] stop_on_handler_exceptions={d.stop_on_handler_exceptions}; bars processed after exception: {len(seen) - 5} (run completed normally)")

asyncio.run(main())

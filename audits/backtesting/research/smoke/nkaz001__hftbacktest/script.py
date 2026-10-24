"""Fill-timing smoke test for hftbacktest 2.4.4 (PyPI wheel cp313 manylinux, repo @ 5f3ec40b2afb).

hftbacktest has no bars; it replays L2 depth/trade events with separate exchange
(exch_ts) and local receive (local_ts) timestamps and an order-latency model.
This script maps the lab's bar question onto it: 30 hourly "bars", each represented
by a book update at t_k (bid 99.5+k, ask 100.5+k, qty 100). The decision is made
after bar 10's book is locally visible. A second update at t_10 + 0.5 s jumps the
book (ask 115.5) to show that the fill depends on order entry latency.

Expected if latency-aware: market buy fills at the ask prevailing at
decision_time + entry_latency on the exchange clock.
Synthetic data only, no network (run inside `unshare -rn`).
"""

import numpy as np

from hftbacktest import (BUY_EVENT, DEPTH_EVENT, EXCH_EVENT, GTC, LOCAL_EVENT, MARKET, SELL_EVENT,
                         BacktestAsset, HashMapMarketDepthBacktest)
from hftbacktest.binding import event_dtype

H = 3_600_000_000_000  # 1 hour in ns
FEED_LAT = 1_000_000   # 1 ms feed latency
K = 10


def t(k: int) -> int:
    return (k + 1) * H


def build_events() -> np.ndarray:
    rows = []
    bid = ask = None

    def put(ts, side, px, qty):
        flag = DEPTH_EVENT | EXCH_EVENT | LOCAL_EVENT | (BUY_EVENT if side == "b" else SELL_EVENT)
        rows.append((flag, ts, ts + FEED_LAT, px, qty, 0, 0, 0.0))

    def move(ts, new_bid, new_ask):
        nonlocal bid, ask
        if bid is not None:
            put(ts, "b", bid, 0.0)
            put(ts, "a", ask, 0.0)
        put(ts, "b", new_bid, 100.0)
        put(ts, "a", new_ask, 100.0)
        bid, ask = new_bid, new_ask

    for k in range(30):
        move(t(k), 99.5 + k, 100.5 + k)
        if k == K:
            move(t(k) + 500_000_000, 114.5, 115.5)  # jump 0.5 s after bar-10 close
    return np.array(rows, dtype=event_dtype)


def run(entry_latency_ns: int) -> str:
    # Keep a Python reference to the array for the whole run: BacktestAsset.add_data() hands Rust a raw
    # pointer (py-hftbacktest/src/lib.rs:206-210, DataPtr::from_ptr, not owned, not copied). Passing a
    # temporary (data([build_events()])) produced garbage fills in an earlier attempt (use-after-free).
    events = build_events()
    asset = (BacktestAsset()
             .data([events])
             .linear_asset(1.0)
             .constant_order_latency(entry_latency_ns, 1_000_000)
             .risk_adverse_queue_model()
             .no_partial_fill_exchange()
             .trading_value_fee_model(0.0, 0.001)
             .tick_size(0.5)
             .lot_size(1.0))
    hbt = HashMapMarketDepthBacktest([asset])
    decision_ts = t(K) + 2_000_000  # bar 10 book visible locally at t(K)+1ms
    hbt.elapse(0)  # cur_ts starts at i64::MAX; first elapse snaps it to the first event time
    hbt.elapse(decision_ts - hbt.current_timestamp)
    d = hbt.depth(0)
    seen = (hbt.current_timestamp, d.best_bid, d.best_ask)
    hbt.submit_buy_order(0, 1, 200.0, 1.0, GTC, MARKET, False)
    hbt.elapse(5_000_000_000)
    o = hbt.orders(0).get(1)
    sv = hbt.state_values(0)
    out = (f"entry_latency={entry_latency_ns / 1e6:g} ms: decided at local_ts=t10+{(seen[0] - t(K)) / 1e6:g} ms seeing "
           f"bid/ask={seen[1]}/{seen[2]} -> status={o.status} exec_price={o.exec_price} "
           f"exch_ts=t10+{(o.exch_timestamp - t(K)) / 1e6:g} ms local_resp_ts=t10+{(o.local_timestamp - t(K)) / 1e6:g} ms "
           f"position={sv.position} fee={sv.fee:.4f}")
    hbt.close()
    del events
    return out


def main() -> None:
    import hftbacktest
    print("hftbacktest", hftbacktest.__version__)
    print(f"bar k={K}: book at t10 bid/ask=109.5/110.5 ('close' ~110); jump at t10+500ms to 114.5/115.5; "
          f"bar k+1 book at t11 bid/ask=110.5/111.5")
    for lat in (0, 100_000_000, 1_000_000_000):
        print(run(lat))


if __name__ == "__main__":
    main()

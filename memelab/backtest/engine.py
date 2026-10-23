"""Deterministic event-driven replay with a portfolio ledger (research only; nothing here can trade).

Flow per run:
  timeline of decision points (bar availability, lab thesis availability) for tokens already in the point-in-time
  universe -> strategy sees only closed bars / observations available then -> order SUBMITTED at the decision time
  -> filled at the first bar open at or after decision + latency through the execution model (or EXPIRED / CANCELED)
  -> position marked each bar at the close (marked value) and at what it would actually return if sold (realizable)
  -> exits: gap-through stop at the open, stop before take-profit inside one bar, take-profit, time stop, or
  NON_EXECUTABLE when no exit liquidity exists (realizable 0)
  -> journal, fills, equity curve, run hash.
"""
from __future__ import annotations

import bisect
import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import ENGINE_VERSION, execution as X
from .strategies.base import Abstain, Signal, Strategy
from .strategies.features import B


@dataclass
class EngineConfig:
    account_usd: float = 10_000.0
    size_usd: float = 500.0                 # fixed notional per entry (before costs)
    risk_per_trade_frac: float | None = None   # alternative sizing: lose at most this fraction of equity at the stop
    max_positions: int = 5
    max_exposure_frac: float = 0.5          # sum of open position cost / equity at entry
    max_entries_per_token: int = 2
    cooldown_s: float = 6 * 3600
    latency_s: float = 5.0
    max_fill_wait_bars: int = 2             # order expires if no bar opens within this many bars after the decision
    entry_impact_cap: float = 0.03          # entry with modeled impact above this is CANCELED (not shrunk silently)
    exit_impact_cap: float | None = None    # None: always exit fully at whatever price; else PARTIAL and remainder stays open
    fill_model: str = "LIQ_SNAPSHOT_APPROX"  # or "FLAT" (paper: bar open with fee only, no impact) for comparisons
    fees: X.Fees = field(default_factory=lambda: X.Fees(swap_fee=0.0025, transfer_fee_bps=0.0, network_fee_sol=0.000105))
    liquidity_haircut: float = 0.8
    sol_usd_default: float | None = None    # only used when no as-of SOL price exists; None = network fee from series or refuse
    liquidity_max_age_s: float = 3 * 86400  # a liquidity snapshot older than this cannot price a fill (INSUFFICIENT_EXECUTION_DATA)
    max_positions_per_group: int | None = None   # correlated tokens (same creator wallet or holder cluster) share this cap
    max_drawdown_frac: float | None = None       # stop opening positions once marked equity is this far below its peak
    stop_overshoot_limit: float = 0.5            # a bar whose low is more than this far below the stop is a crash: the stop
                                                 # is assumed filled at that bar's close, not at the stop price


@dataclass
class TokenData:
    chain: str
    mint: str
    bars: list[B]                                       # one pool basis, oldest first, closed bars with availability
    liquidity: list[tuple[float, float]] = field(default_factory=list)   # (available_at, liquidity_usd) snapshots
    transfer_fee_bps: float = 0.0
    pool_type: str = "CPMM"
    theses: list[dict] = field(default_factory=list)   # lab thesis events with available_at
    universe_from: float = float("-inf")                # first time the lab knew the token (no trading before)
    delisted_at: float | None = None
    catalysts: list[dict] = field(default_factory=list)       # catalyst records with available_at (strategies/catalyst.py)
    wallet_events: list[dict] = field(default_factory=list)   # wallet observations with kind and available_at
    swap_fee: float | None = None                             # this pool's fee (execution.assumed_swap_fee); None = config default
    fee_basis: str | None = None
    group: str | None = None                                  # correlation group (creator wallet, holder cluster) known at entry

    def __post_init__(self):
        self.bars.sort(key=lambda b: b.start)
        self._starts = [b.start for b in self.bars]
        self._avail = [b.avail for b in self.bars]
        self.liquidity.sort()

    def closed_until(self, t: float) -> list[B]:
        return self.bars[: bisect.bisect_right(self._avail, t)]

    def next_open_at_or_after(self, t: float) -> int | None:
        i = bisect.bisect_left(self._starts, t)
        return i if i < len(self.bars) else None

    def liquidity_asof(self, t: float, max_age: float) -> float | None:
        v = None
        for a, l in self.liquidity:
            if a <= t:
                v = (a, l)
            else:
                break
        if v is None or t - v[0] > max_age:
            return None
        return v[1]


@dataclass
class Position:
    pid: str
    mint: str
    signal: dict
    entry_time: float
    entry_price_mid: float
    cost_usd: float
    tokens: float
    stop: float | None
    target: float | None
    deadline: float | None
    status: str = "OPEN"


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


class Engine:
    def __init__(self, cfg: EngineConfig, sol_usd: Callable[[float], float | None] | None = None):
        self.cfg = cfg
        self.sol_usd = sol_usd or (lambda t: cfg.sol_usd_default)
        self.cash = cfg.account_usd
        self.positions: dict[str, Position] = {}
        self.fills: list[dict] = []
        self.journal: list[dict] = []
        self.trades: list[dict] = []
        self.equity: list[dict] = []
        self.counts = {"signals": 0, "abstain": {}, "submitted": 0, "filled": 0, "expired": 0, "canceled": 0, "rejected_limits": 0}
        self._entries: dict[str, int] = {}
        self._attempts: dict[str, int] = {}
        self._last_exit: dict[str, float] = {}
        self._seq = 0
        self._peak_equity = cfg.account_usd
        self._halted_at: float | None = None

    # ---------- execution helpers ----------
    def _net_fee_usd(self, t: float) -> float:
        px = self.sol_usd(t)
        if px is None:
            raise ValueError("no as-of SOL/USD price for the network fee")
        return self.cfg.fees.network_fee_sol * px

    def _pool(self, td: TokenData, t: float, price: float) -> tuple[X.CpmmPool | None, str]:
        fees = X.Fees(td.swap_fee if td.swap_fee is not None else self.cfg.fees.swap_fee, td.transfer_fee_bps,
                      self.cfg.fees.transfer_fee_max_tokens, self.cfg.fees.network_fee_sol)
        if self.cfg.fill_model == "FLAT":
            return X.CpmmPool(1e30, 1e30 * price, fees, basis="FLAT_PAPER"), "OK"
        if td.pool_type != "CPMM":
            return None, "UNSUPPORTED_POOL"
        liq = td.liquidity_asof(t, self.cfg.liquidity_max_age_s)
        if liq is None or liq <= 0:
            return None, "INSUFFICIENT_EXECUTION_DATA"
        return X.pool_from_liquidity_snapshot(liq, price, 1.0, fees, haircut=self.cfg.liquidity_haircut), "OK"

    def _record_fill(self, **f) -> None:
        self.fills.append(f)

    # ---------- entries ----------
    def _equity_marked(self, tds: dict[str, TokenData], t: float) -> float:
        v = self.cash
        for p in self.positions.values():
            td = tds[p.mint]
            cb = td.closed_until(t)
            v += p.tokens * (cb[-1].c if cb else p.entry_price_mid)
        return v

    def _try_enter(self, td: TokenData, sig: Signal, tds: dict[str, TokenData]) -> None:
        c = self.cfg
        self.counts["submitted"] += 1
        self._attempts[td.mint] = self._attempts.get(td.mint, 0) + 1
        oid = f"o{self._seq}"; self._seq += 1
        d = sig.decision_time
        self.journal.append({"t": d, "event": "SUBMITTED", "mint": td.mint, "order": oid, "signal_id": sig.signal_id})
        if c.max_drawdown_frac is not None:
            eq_now = self._equity_marked(tds, d)
            self._peak_equity = max(self._peak_equity, eq_now)
            if self._halted_at is not None or eq_now < self._peak_equity * (1 - c.max_drawdown_frac):
                if self._halted_at is None:
                    self._halted_at = d
                    self.journal.append({"t": d, "event": "HALT_NEW_ENTRIES", "reason": f"marked equity {eq_now:.2f} below {1 - c.max_drawdown_frac:.0%} of peak {self._peak_equity:.2f}"})
                self.counts["rejected_limits"] += 1
                self.journal.append({"t": d, "event": "REJECTED_LIMIT", "mint": td.mint, "order": oid, "reason": "max account drawdown"})
                return
        if c.max_positions_per_group is not None and td.group is not None:
            same = sum(1 for m in self.positions if tds[m].group == td.group)
            if same >= c.max_positions_per_group:
                self.counts["rejected_limits"] += 1
                self.journal.append({"t": d, "event": "REJECTED_LIMIT", "mint": td.mint, "order": oid, "reason": f"correlated group {td.group} at cap"})
                return
        if td.mint in self.positions or self._entries.get(td.mint, 0) >= c.max_entries_per_token or d - self._last_exit.get(td.mint, -1e18) < c.cooldown_s:
            self.counts["rejected_limits"] += 1
            self.journal.append({"t": d, "event": "REJECTED_LIMIT", "mint": td.mint, "order": oid, "reason": "per-token limit or cooldown"})
            return
        if len(self.positions) >= c.max_positions:
            self.counts["rejected_limits"] += 1
            self.journal.append({"t": d, "event": "REJECTED_LIMIT", "mint": td.mint, "order": oid, "reason": "max positions"})
            return
        i = td.next_open_at_or_after(d + c.latency_s)
        if i is None or (td.bars[i].start - (d + c.latency_s)) > c.max_fill_wait_bars * (td.bars[i].end - td.bars[i].start):
            self.counts["expired"] += 1
            self.journal.append({"t": d, "event": "EXPIRED", "mint": td.mint, "order": oid, "reason": "no bar opened in time"})
            self._record_fill(order_id=oid, mint=td.mint, action="BUY", decision_time=d, submission_time=d, fill_time=None, requested=c.size_usd,
                              filled=0.0, price=None, impact=None, fees={}, basis=None, status="EXPIRED", reason="no bar opened in time")
            return
        bar = td.bars[i]
        t_fill = bar.start
        if td.delisted_at is not None and t_fill >= td.delisted_at:
            self.counts["expired"] += 1
            self.journal.append({"t": d, "event": "EXPIRED", "mint": td.mint, "order": oid, "reason": "delisted"})
            return
        size = c.size_usd
        if c.risk_per_trade_frac and sig.exits.stop_price and sig.exits.stop_price < bar.o:
            eq = self._equity_marked(tds, d)
            size = min(size, eq * c.risk_per_trade_frac / (1 - sig.exits.stop_price / bar.o))
        exposure = sum(p.cost_usd for p in self.positions.values())
        eq = self._equity_marked(tds, d)
        if exposure + size > c.max_exposure_frac * eq or size > self.cash:
            self.counts["rejected_limits"] += 1
            self.journal.append({"t": d, "event": "REJECTED_LIMIT", "mint": td.mint, "order": oid, "reason": "exposure or cash"})
            return
        pool, st = self._pool(td, t_fill, bar.o)
        try:
            nfee = self._net_fee_usd(t_fill)
        except ValueError as e:
            pool, st = None, f"INSUFFICIENT_EXECUTION_DATA: {e}"
            nfee = 0.0
        if pool is None:
            self.counts["canceled"] += 1
            self.journal.append({"t": d, "event": "CANCELED", "mint": td.mint, "order": oid, "reason": st})
            self.counts["abstain"][st.split(":")[0]] = self.counts["abstain"].get(st.split(":")[0], 0) + 1
            self._record_fill(order_id=oid, mint=td.mint, action="BUY", decision_time=d, submission_time=d, fill_time=None, requested=size,
                              filled=0.0, price=None, impact=None, fees={}, basis=None, status="CANCELED", reason=st)
            return
        f, _ = pool.buy(size)
        if f.impact_frac is not None and f.impact_frac > c.entry_impact_cap:
            self.counts["canceled"] += 1
            self.cash -= nfee
            self.journal.append({"t": d, "event": "CANCELED", "mint": td.mint, "order": oid, "reason": f"entry impact {f.impact_frac:.3%} > cap"})
            self._record_fill(order_id=oid, mint=td.mint, action="BUY", decision_time=d, submission_time=d, fill_time=t_fill, requested=size,
                              filled=0.0, price=None, impact=f.impact_frac, fees={"network_usd": nfee}, basis=f.basis, status="CANCELED", reason="entry impact above cap; network fee paid")
            return
        self.cash -= size + nfee
        pid = f"p{len(self.trades) + len(self.positions)}_{td.mint[:6]}"
        stop = sig.exits.stop_price
        target = None
        if sig.exits.take_profit_r and stop and stop < bar.o:
            target = bar.o + sig.exits.take_profit_r * (bar.o - stop)
        elif sig.exits.take_profit_pct:
            target = bar.o * (1 + sig.exits.take_profit_pct)
        deadline = t_fill + sig.exits.max_hold_s if sig.exits.max_hold_s else None
        self.positions[td.mint] = Position(pid, td.mint, sig.as_dict(), t_fill, bar.o, size + nfee, f.out, stop, target, deadline)
        self._entries[td.mint] = self._entries.get(td.mint, 0) + 1
        self.counts["filled"] += 1
        self._record_fill(order_id=oid, mint=td.mint, action="BUY", decision_time=d, submission_time=d, fill_time=t_fill, requested=size, filled=size,
                          price=f.avg_price, impact=f.impact_frac, fees={**f.fees, "network_usd": nfee}, basis=f.basis, status="FILLED", reason=None)
        self.journal.append({"t": t_fill, "event": "FILLED_BUY", "mint": td.mint, "order": oid, "tokens": f.out, "avg_price": f.avg_price, "mid": bar.o})

    # ---------- exits ----------
    def _exit(self, td: TokenData, p: Position, t: float, px: float, reason: str) -> None:
        pool, st = self._pool(td, t, px)
        try:
            nfee = self._net_fee_usd(t)
        except ValueError:
            nfee = 0.0
        if pool is None:
            proceeds, status, filled, basis, imp, fees = 0.0, "FAILED", 0.0, None, None, {}
            reason = f"{reason}; NON_EXECUTABLE ({st})"
        elif self.cfg.exit_impact_cap is not None:
            f, _ = X.route_sell([pool], p.tokens, max_impact=self.cfg.exit_impact_cap)
            proceeds, status, filled, basis, imp, fees = f.out, f.status, f.filled_in, f.basis, f.impact_frac, f.fees
        else:
            f, _ = pool.sell(p.tokens)
            proceeds, status, filled, basis, imp, fees = f.out, f.status, f.filled_in, f.basis, f.impact_frac, f.fees
        self.cash += proceeds - (nfee if pool is not None else 0.0)
        self._record_fill(order_id=f"x_{p.pid}_{len(self.fills)}", mint=p.mint, action="SELL", decision_time=t, submission_time=t, fill_time=t if pool else None,
                          requested=p.tokens, filled=filled, price=(proceeds / filled) if filled else None, impact=imp, fees={**(fees or {}), "network_usd": nfee if pool else 0.0},
                          basis=basis, status=status, reason=reason)
        remaining = p.tokens - filled
        realized = proceeds - (nfee if pool is not None else 0.0)
        if remaining > 1e-12 and status != "FAILED":
            p.tokens = remaining
            p.cost_usd -= realized   # remaining cost basis
            self.journal.append({"t": t, "event": "PARTIAL_EXIT", "mint": p.mint, "sold": filled, "left": remaining})
            return
        self.trades.append({"pid": p.pid, "mint": p.mint, "strategy": p.signal["strategy_id"], "decision_time": p.signal["decision_time"], "entry_time": p.entry_time,
                            "entry_mid": p.entry_price_mid, "cost_usd": p.cost_usd, "exit_time": t, "exit_ref_price": px, "exit_reason": reason,
                            "proceeds_usd": realized if status != "FAILED" else 0.0, "pnl_usd": (realized if status != "FAILED" else 0.0) - p.cost_usd,
                            "ret": ((realized if status != "FAILED" else 0.0) / p.cost_usd - 1) if p.cost_usd else None, "status": status,
                            "paper_ret_mid": px / p.entry_price_mid - 1})
        del self.positions[p.mint]
        self._last_exit[p.mint] = t
        self.journal.append({"t": t, "event": "EXIT", "mint": p.mint, "reason": reason, "status": status})

    def _manage(self, td: TokenData, bar: B) -> None:
        p = self.positions.get(td.mint)
        if not p or bar.start < p.entry_time:
            return
        if td.delisted_at is not None and bar.start >= td.delisted_at:
            self._exit(td, p, bar.start, bar.o, "DELISTED")
            return
        if bar.start == p.entry_time:
            # the entry bar: only intrabar stop/target after the fill at its open
            pass
        elif p.stop is not None and bar.o <= p.stop:
            self._exit(td, p, bar.start, bar.o, "STOP_GAP_FILL_AT_OPEN")
            return
        elif p.deadline is not None and bar.start >= p.deadline:
            self._exit(td, p, bar.start, bar.o, "TIME_EXIT_AT_OPEN")
            return
        hit_stop = p.stop is not None and bar.l <= p.stop
        hit_tp = p.target is not None and bar.h >= p.target
        if hit_stop and bar.l < p.stop * (1 - self.cfg.stop_overshoot_limit) and bar.c < p.stop:
            # crash through the stop inside one bar (rug, liquidity pull): nothing guarantees a fill near the stop;
            # assume the exit happened at the price the bar settled at
            self._exit(td, p, bar.end - 1e-6, bar.c, "STOP_INTRABAR_CRASH_FILL_AT_CLOSE")
        elif hit_stop:                                 # stop wins when both are inside one bar (conservative)
            self._exit(td, p, bar.end - 1e-6, p.stop, "STOP_INTRABAR" + ("_BOTH_IN_BAR" if hit_tp else ""))
        elif hit_tp:
            self._exit(td, p, bar.end - 1e-6, p.target, "TAKE_PROFIT_INTRABAR")

    # ---------- main loop ----------
    def run(self, strategy: Strategy, tokens: Iterable[TokenData], until: float | None = None, decide_from: float | None = None,
            decide_until: float | None = None) -> dict:
        """until: no event after this time is processed and nothing after it is read (positions still open are valued
        from bars closed by `until`). decide_from / decide_until: new entries only for decisions inside the window
        (positions keep being managed until `until`)."""
        tds = {t.mint: t for t in tokens}
        events = []
        for td in tds.values():
            for i, b in enumerate(td.bars):
                if b.avail >= td.universe_from:
                    events.append((b.avail, 1, td.mint, "BAR", i))
                events.append((b.end, 0, td.mint, "MANAGE", i))      # a bar is applied only once it is complete
            for k, th in enumerate(td.theses):
                events.append((th["available_at"], 2, td.mint, "THESIS", k))
            for k, cr in enumerate(td.catalysts):
                events.append((cr["available_at"], 3, td.mint, "CATALYST", k))
        events.sort(key=lambda e: (e[0], e[1], e[2], e[4]))
        for t, _, mint, kind, idx in events:
            if until is not None and t > until:
                break
            td = tds[mint]
            if kind == "MANAGE":
                self._manage(td, td.bars[idx])
                continue
            ctx = {"entries_so_far": self._entries.get(mint, 0), "attempts_so_far": self._attempts.get(mint, 0)}
            if kind == "THESIS":
                if strategy.kind != "LAB":
                    continue
                ctx["thesis"] = td.theses[idx]
            elif kind == "CATALYST":
                if strategy.kind != "CATALYST":
                    continue
                ctx["catalysts"] = [c for c in td.catalysts if c["available_at"] <= t]
                ctx["wallet_events"] = [w for w in td.wallet_events if w["available_at"] <= t]
                ctx["theses"] = [h for h in td.theses if h["available_at"] <= t]      # the lab's own risk view as known then
            elif strategy.kind in ("LAB", "CATALYST"):
                continue
            if t < td.universe_from or (decide_from is not None and t < decide_from) or (decide_until is not None and t >= decide_until):
                continue
            bars = td.closed_until(t)
            r = strategy.evaluate(td.chain, mint, bars, t, ctx)
            if isinstance(r, Abstain):
                self.counts["abstain"][r.reason] = self.counts["abstain"].get(r.reason, 0) + 1
            elif isinstance(r, Signal):
                self.counts["signals"] += 1
                self._try_enter(td, r, tds)
        # close anything still open at the end of data at the last available close (marked) and realizable value
        end_t = until if until is not None else max((td.bars[-1].avail for td in tds.values() if td.bars), default=0.0)
        for mint in sorted(list(self.positions)):
            td = tds[mint]
            cb = td.closed_until(end_t)                 # never read past the run's end
            px = cb[-1].c if cb else self.positions[mint].entry_price_mid
            self._exit(td, self.positions[mint], cb[-1].end if cb else end_t, px,
                       "END_OF_DATA_MARK_TO_REALIZABLE" if until is None else "TRUNCATED_AT_CUTOFF_MARK_TO_REALIZABLE")
        return self.result(strategy)

    def result(self, strategy: Strategy) -> dict:
        rets = [t["ret"] for t in self.trades if t["ret"] is not None]
        paper = [t["paper_ret_mid"] for t in self.trades]
        out = {
            "engine_version": ENGINE_VERSION, "cost_model_version": X.COST_MODEL_VERSION, "strategy": strategy.describe(),
            "config": {k: (v.__dict__ if hasattr(v, "__dict__") else v) for k, v in self.cfg.__dict__.items()},
            "counts": self.counts, "n_trades": len(self.trades), "final_cash": self.cash, "pnl_usd": self.cash - self.cfg.account_usd,
            "mean_ret": sum(rets) / len(rets) if rets else None, "mean_paper_ret_mid": sum(paper) / len(paper) if paper else None,
            "trades": self.trades, "fills": self.fills, "journal": self.journal,
        }
        out["ledger_hash"] = _h({"trades": self.trades, "fills": self.fills, "cash": round(self.cash, 9)})
        if self.cash < -1e-9:
            raise ArithmeticError("negative cash: an order was filled without funds")
        return out

"""Execution models for DEX pools: exact constant product, observed quotes, liquidity-snapshot approximation, refusal.

Fidelity ladder (ARCHITECTURE_DECISION section 7):
  EXACT_CPMM          constant-product pool with reserves observed at or before the execution time
  QUOTE_OBSERVED      a router quote for this size observed at the execution time and not expired
  LIQ_SNAPSHOT_APPROX constant-product pool with only a USD liquidity snapshot (lower fidelity, haircut, labeled)
  UNSUPPORTED_POOL    concentrated liquidity (CLMM), bins (DLMM), bonding curves or unknown pools without state

Fee stack, each component applied exactly once:
  swap fee         charged by the pool on the input amount (fraction), before the curve
  transfer fee     Token-2022 fee withheld on every transfer of the token (bps, optional per-transfer cap);
                   on a buy the user receives less token; on a sell the pool receives less token
  network fee      fixed SOL per transaction (base + priority), converted to USD at the as-of SOL price;
                   paid even when the swap fails
No function here sends anything anywhere: these are pure calculations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

EXACT_CPMM, QUOTE_OBSERVED, LIQ_SNAPSHOT_APPROX, UNSUPPORTED_POOL = "EXACT_CPMM", "QUOTE_OBSERVED", "LIQ_SNAPSHOT_APPROX", "UNSUPPORTED_POOL"
FILLED, PARTIAL, FAILED = "FILLED", "PARTIAL", "FAILED"
COST_MODEL_VERSION = "cost-1"


# Swap fees by DEX when the pool's own fee is not observed. PumpSwap fees are per pool and change with the pool's tier:
# a live spot-check (audits/backtesting/execution/SPOTCHECK.md) found 0.30%, 0.55% and 1.25% on three pools, so the
# historical default is the highest observed tier (conservative). Other CPMM programs use their common base fee.
DEX_FEE_DEFAULTS = {"pumpswap": (0.0125, "ASSUMED_UPPER_OBSERVED_TIER"), "raydium": (0.0025, "ASSUMED_PROGRAM_BASE"),
                    "raydium-cpmm": (0.01, "ASSUMED_CONFIG_UNKNOWN"), "meteora-damm": (0.01, "ASSUMED_CONFIG_UNKNOWN")}
UNKNOWN_DEX_FEE = (0.01, "ASSUMED_UNKNOWN_DEX")


def assumed_swap_fee(dex: str | None, observed: float | None = None) -> tuple[float, str]:
    """(fee, basis). An observed fee for this pool always wins; otherwise a conservative default, labeled."""
    if observed is not None:
        return observed, "OBSERVED"
    return DEX_FEE_DEFAULTS.get((dex or "").lower(), UNKNOWN_DEX_FEE)


@dataclass(frozen=True)
class Fees:
    swap_fee: float = 0.0025                 # pool fee as a fraction of the input
    transfer_fee_bps: float = 0.0            # Token-2022 transfer fee on the token leg
    transfer_fee_max_tokens: float | None = None   # per-transfer cap in token units (None = uncapped)
    network_fee_sol: float = 0.000005 + 0.0001     # base signature fee + a modest priority fee, per transaction

    def __post_init__(self):
        if not (0 <= self.swap_fee < 1) or not (0 <= self.transfer_fee_bps < 10_000) or self.network_fee_sol < 0:
            raise ValueError("invalid fee parameters")

    def transfer_fee(self, tokens: float) -> float:
        f = tokens * self.transfer_fee_bps / 10_000.0
        return min(f, self.transfer_fee_max_tokens) if self.transfer_fee_max_tokens is not None else f


@dataclass
class Fill:
    side: str
    basis: str
    status: str
    requested_in: float            # quote units for BUY, token units for SELL
    filled_in: float
    out: float                     # token units for BUY, quote units for SELL (net of every fee except network)
    mid_price: float | None        # quote per token before the trade
    avg_price: float | None        # quote per token actually achieved
    impact_frac: float | None      # adverse move of avg price vs mid, as a fraction
    fees: dict = field(default_factory=dict)
    network_fee_quote: float = 0.0
    reason: str | None = None
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------- exact constant product ----------------

def cpmm_out(reserve_in: float, reserve_out: float, amount_in_after_fee: float) -> float:
    if reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("reserves must be positive")
    if amount_in_after_fee < 0:
        raise ValueError("negative input")
    return reserve_out * amount_in_after_fee / (reserve_in + amount_in_after_fee)


def cpmm_out_raw(reserve_in: int, reserve_out: int, amount_in: int, fee_num: int, fee_den: int) -> int:
    """Integer form used by constant-product programs: fee = ceil(in * num / den), out = floor(R_out * net / (R_in + net))."""
    if reserve_in <= 0 or reserve_out <= 0 or amount_in < 0:
        raise ValueError("invalid raw amounts")
    fee = -(-amount_in * fee_num // fee_den)
    net = amount_in - fee
    return (reserve_out * net) // (reserve_in + net)


@dataclass(frozen=True)
class CpmmPool:
    reserve_base: float            # token units
    reserve_quote: float           # quote units (SOL or USDC), effective (PumpSwap: vault + virtual_quote_reserves)
    fees: Fees = Fees()
    basis: str = EXACT_CPMM

    def __post_init__(self):
        if self.reserve_base <= 0 or self.reserve_quote <= 0:
            raise ValueError("reserves must be positive")

    @property
    def mid(self) -> float:
        return self.reserve_quote / self.reserve_base

    def buy(self, quote_in: float) -> tuple[Fill, "CpmmPool"]:
        if quote_in <= 0:
            raise ValueError("size must be positive")
        swap_fee = quote_in * self.fees.swap_fee
        base_from_pool = cpmm_out(self.reserve_quote, self.reserve_base, quote_in - swap_fee)
        tfee = self.fees.transfer_fee(base_from_pool)
        received = base_from_pool - tfee
        new = CpmmPool(self.reserve_base - base_from_pool, self.reserve_quote + quote_in, self.fees, self.basis)
        _invariant(self, new)
        avg = quote_in / received if received > 0 else math.inf
        return Fill("BUY", self.basis, FILLED, quote_in, quote_in, received, self.mid, avg, avg / self.mid - 1,
                    {"swap_fee_quote": swap_fee, "transfer_fee_tokens": tfee}), new

    def sell(self, tokens_in: float) -> tuple[Fill, "CpmmPool"]:
        if tokens_in <= 0:
            raise ValueError("size must be positive")
        tfee = self.fees.transfer_fee(tokens_in)
        arrives = tokens_in - tfee
        swap_fee_tokens = arrives * self.fees.swap_fee
        quote_out = cpmm_out(self.reserve_base, self.reserve_quote, arrives - swap_fee_tokens)
        new = CpmmPool(self.reserve_base + arrives, self.reserve_quote - quote_out, self.fees, self.basis)
        _invariant(self, new)
        avg = quote_out / tokens_in
        return Fill("SELL", self.basis, FILLED, tokens_in, tokens_in, quote_out, self.mid, avg, 1 - avg / self.mid,
                    {"swap_fee_tokens": swap_fee_tokens, "transfer_fee_tokens": tfee}), new


def _invariant(a: CpmmPool, b: CpmmPool) -> None:
    if b.reserve_base <= 0 or b.reserve_quote <= 0:
        raise ArithmeticError("reserve went non-positive")
    if b.reserve_base * b.reserve_quote < a.reserve_base * a.reserve_quote * (1 - 1e-12):
        raise ArithmeticError("constant-product invariant decreased: free money")


def pool_from_liquidity_snapshot(liquidity_usd: float, price_usd: float, quote_price_usd: float, fees: Fees, haircut: float = 0.8) -> CpmmPool:
    """Lower-fidelity reconstruction for a constant-product pool from a USD liquidity snapshot observed at or before the
    execution time: half the liquidity on each side, then a haircut for the unknown split and stale reserves."""
    if liquidity_usd <= 0 or price_usd <= 0 or quote_price_usd <= 0:
        raise ValueError("snapshot inputs must be positive")
    side_usd = liquidity_usd / 2.0 * haircut
    return CpmmPool(reserve_base=side_usd / price_usd, reserve_quote=side_usd / quote_price_usd, fees=fees, basis=LIQ_SNAPSHOT_APPROX)


def pumpswap_effective(vault_quote: float, virtual_quote_reserves: float, vault_base: float, fees: Fees) -> CpmmPool:
    """PumpSwap quotes on effective quote reserves = vault balance + signed virtual_quote_reserves (pump-public-docs)."""
    eff = vault_quote + virtual_quote_reserves
    if eff <= 0:
        raise ValueError("effective quote reserve not positive")
    return CpmmPool(reserve_base=vault_base, reserve_quote=eff, fees=fees, basis=EXACT_CPMM)


# ---------------- observed quotes ----------------

@dataclass(frozen=True)
class QuoteCurve:
    """Router quotes observed at quote_at for one side: sizes in input units -> outputs, plus mid price."""
    side: str
    quote_at: float
    ttl_s: float
    points: tuple            # ((size_in, out), ...) ascending by size, status OK only
    mid_price: float         # quote per token at quote_at
    failed_sizes: tuple = ()

    def fill(self, size_in: float, at: float) -> Fill:
        if at < self.quote_at:
            return Fill(self.side, QUOTE_OBSERVED, FAILED, size_in, 0.0, 0.0, self.mid_price, None, None, reason="QUOTE_FROM_THE_FUTURE")
        if at - self.quote_at > self.ttl_s:
            return Fill(self.side, QUOTE_OBSERVED, FAILED, size_in, 0.0, 0.0, self.mid_price, None, None, reason="STALE_DATA")
        pts = sorted(self.points)
        if not pts:
            return Fill(self.side, QUOTE_OBSERVED, FAILED, size_in, 0.0, 0.0, self.mid_price, None, None, reason="NO_ROUTE")
        if size_in > pts[-1][0] * (1 + 1e-9):
            return Fill(self.side, QUOTE_OBSERVED, FAILED, size_in, 0.0, 0.0, self.mid_price, None, None, reason="INSUFFICIENT_EXECUTION_DATA: size above largest quoted size")
        # interpolate the effective rate (out per unit in) between bracketing sizes; below the smallest size use it
        lo = max([p for p in pts if p[0] <= size_in], default=pts[0], key=lambda p: p[0])
        hi = min([p for p in pts if p[0] >= size_in], default=pts[-1], key=lambda p: p[0])
        r_lo, r_hi = lo[1] / lo[0], hi[1] / hi[0]
        if hi[0] == lo[0]:
            rate = r_lo
        else:
            w = (math.log(size_in) - math.log(lo[0])) / (math.log(hi[0]) - math.log(lo[0])) if size_in > lo[0] else 0.0
            rate = r_lo + w * (r_hi - r_lo)
        out = size_in * rate
        if self.side == "BUY":
            avg = size_in / out
            imp = avg / self.mid_price - 1
        else:
            avg = out / size_in
            imp = 1 - avg / self.mid_price
        return Fill(self.side, QUOTE_OBSERVED, FILLED, size_in, size_in, out, self.mid_price, avg, imp, {"embedded_in_quote": True})


# ---------------- routing across pools ----------------

def route_buy(pools: list[CpmmPool], quote_in: float, chunks: int = 200) -> tuple[Fill, list[CpmmPool]]:
    """Split one buy across several constant-product pools of the same pair by marginal price (greedy in equal
    chunks). Every unit of liquidity is used once: the pools' reserves move as chunks are filled."""
    if not pools:
        return Fill("BUY", UNSUPPORTED_POOL, FAILED, quote_in, 0, 0, None, None, None, reason="NO_ROUTE"), []
    mid = sum(p.reserve_quote for p in pools) / sum(p.reserve_base for p in pools)
    state = list(pools)
    got, fee_q, fee_t = 0.0, 0.0, 0.0
    step = quote_in / chunks
    for _ in range(chunks):
        best_i, best_out = None, -1.0
        for i, p in enumerate(state):
            f, _ = p.buy(step)
            if f.out > best_out:
                best_i, best_out = i, f.out
        f, state[best_i] = state[best_i].buy(step)
        got += f.out; fee_q += f.fees["swap_fee_quote"]; fee_t += f.fees["transfer_fee_tokens"]
    avg = quote_in / got
    basis = EXACT_CPMM if all(p.basis == EXACT_CPMM for p in pools) else LIQ_SNAPSHOT_APPROX
    return Fill("BUY", basis, FILLED, quote_in, quote_in, got, mid, avg, avg / mid - 1, {"swap_fee_quote": fee_q, "transfer_fee_tokens": fee_t, "legs": len(pools)}), state


def route_sell(pools: list[CpmmPool], tokens_in: float, available: list[bool] | None = None, chunks: int = 200,
               max_impact: float | None = None) -> tuple[Fill, list[CpmmPool]]:
    """Sell across pools of the same pair. Legs marked unavailable (failed route, drained, stale) are skipped and never
    counted. With max_impact, selling stops when the next chunk's average price would be more than max_impact below
    the starting mid: the rest is unfilled (PARTIAL), never a phantom fill. Nothing executable: FAILED."""
    available = available or [True] * len(pools)
    usable = [p for p, ok in zip(pools, available) if ok]
    if not usable:
        return Fill("SELL", UNSUPPORTED_POOL, FAILED, tokens_in, 0, 0, None, None, None, reason="NO_EXECUTABLE_LEG"), list(pools)
    mid = sum(p.reserve_quote for p in usable) / sum(p.reserve_base for p in usable)
    state = list(usable)
    out, fee_t, fee_tok, filled = 0.0, 0.0, 0.0, 0.0
    step = tokens_in / chunks
    for _ in range(chunks):
        best_i, best, best_fill = None, -1.0, None
        for i, p in enumerate(state):
            f, _ = p.sell(step)
            if f.out > best:
                best_i, best, best_fill = i, f.out, f
        if max_impact is not None and 1 - (best_fill.out / step) / mid > max_impact:
            break
        f, state[best_i] = state[best_i].sell(step)
        out += f.out; fee_t += f.fees["transfer_fee_tokens"]; fee_tok += f.fees["swap_fee_tokens"]; filled += step
    if filled <= 0:
        return Fill("SELL", usable[0].basis, FAILED, tokens_in, 0, 0, mid, None, None, reason="IMPACT_CAP_BEFORE_FIRST_CHUNK"), list(pools)
    avg = out / filled
    status = FILLED if filled >= tokens_in * (1 - 1e-9) else PARTIAL
    basis = EXACT_CPMM if all(p.basis == EXACT_CPMM for p in usable) else LIQ_SNAPSHOT_APPROX
    fill = Fill("SELL", basis, status, tokens_in, filled, out, mid, avg, 1 - avg / mid,
                {"swap_fee_tokens": fee_tok, "transfer_fee_tokens": fee_t, "legs": len(usable), "legs_failed": len(pools) - len(usable)})
    if len(usable) < len(pools):
        fill.warnings.append("ROUTE_DEGRADED: some legs unavailable; proceeds use executable legs only")
    if status == PARTIAL:
        fill.warnings.append(f"PARTIAL: {filled:.6g} of {tokens_in:.6g} tokens executable within the impact cap")
    return fill, state


# ---------------- capacity and sizing curves ----------------

def round_trip(pool: CpmmPool, quote_in: float, network_fee_quote: float = 0.0) -> dict:
    """Buy then sell immediately in the same pool: the pure cost of getting in and out at this size."""
    b, p2 = pool.buy(quote_in)
    s, _ = p2.sell(b.out)
    cost = quote_in + network_fee_quote
    back = s.out - network_fee_quote
    return {"size_quote": quote_in, "tokens": b.out, "proceeds_quote": back, "loss_frac": 1 - back / cost, "entry_impact": b.impact_frac, "exit_impact": s.impact_frac}


def max_size(pool: CpmmPool, max_exit_impact: float, max_entry_impact: float | None = None, hi: float | None = None) -> float:
    """Largest buy size (quote units) whose entry impact and immediate exit impact stay within the caps. Both impacts
    grow monotonically with size in a constant-product pool, so a binary search is valid. (An immediate round-trip
    loss is mostly fees because impact unwinds in the same pool, so it is not used as a cap.)"""
    hi = hi or pool.reserve_quote * 10

    def ok(x: float) -> bool:
        r = round_trip(pool, x)
        return r["exit_impact"] <= max_exit_impact and (max_entry_impact is None or r["entry_impact"] <= max_entry_impact)

    lo = 0.0
    if not ok(pool.reserve_quote * 1e-9):
        return 0.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if ok(mid):
            lo = mid
        else:
            hi = mid
    return lo


def sizing_curve(pool: CpmmPool, sizes_quote: list[float], network_fee_quote: float = 0.0) -> list[dict]:
    return [round_trip(pool, s, network_fee_quote) for s in sizes_quote]


def network_fee_usd(fees: Fees, sol_usd: float, transactions: int = 1) -> float:
    return fees.network_fee_sol * sol_usd * transactions


def classify_pool(pool_type: str, has_reserves: bool, has_liquidity_snapshot: bool, has_fresh_quote: bool) -> str:
    """Which model may be used. Never a universal x*y=k."""
    if pool_type == "CPMM" and has_reserves:
        return EXACT_CPMM
    if has_fresh_quote:
        return QUOTE_OBSERVED
    if pool_type == "CPMM" and has_liquidity_snapshot:
        return LIQ_SNAPSHOT_APPROX
    return UNSUPPORTED_POOL


# ---------------- time-indexed state and denominators ----------------

def state_at(states: list[tuple[float, CpmmPool]], t: float, max_age_s: float | None = None) -> tuple[CpmmPool | None, str]:
    """Pool state to use for an execution at time t: the latest state available at or before t (never the state at the
    decision time if the pool changed in between). Returns (pool, state) with state OBSERVED / STALE / MISSING."""
    vis = [(a, p) for a, p in states if a <= t]
    if not vis:
        return None, "MISSING"
    a, p = max(vis, key=lambda x: x[0])
    if max_age_s is not None and t - a > max_age_s:
        return p, "STALE"
    return p, "OBSERVED"


def to_usd(amount: float, asset: str, rates: dict) -> float:
    """Convert an amount of SOL / USDC / USDT / USD to USD with the as-of rates given (e.g. {'SOL': 150.0, 'USDC': 0.999}).
    A missing rate raises instead of assuming 1.0 or the latest price."""
    if asset == "USD":
        return amount
    if asset not in rates or rates[asset] is None or rates[asset] <= 0:
        raise KeyError(f"no as-of USD rate for {asset}")
    return amount * rates[asset]


def pnl(cost_quote: float, proceeds_quote: float, quote_asset: str, rates_entry: dict, rates_exit: dict) -> dict:
    """P&L in the quote asset and in USD, each leg converted at its own time's rate (no single-rate shortcut)."""
    cost_usd = to_usd(cost_quote, quote_asset, rates_entry)
    proceeds_usd = to_usd(proceeds_quote, quote_asset, rates_exit)
    return {"pnl_quote": proceeds_quote - cost_quote, "ret_quote": proceeds_quote / cost_quote - 1,
            "pnl_usd": proceeds_usd - cost_usd, "ret_usd": proceeds_usd / cost_usd - 1, "cost_usd": cost_usd, "proceeds_usd": proceeds_usd}

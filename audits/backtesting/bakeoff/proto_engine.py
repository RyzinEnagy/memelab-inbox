"""Bake-off prototype of the purpose-built engine (pure Python, no dependencies).

Conventions under test (decided in D-BT-013): a bar is knowable only after it closes; a decision at time d executes
at the open of the first bar starting at or after d + latency; a gap through a stop fills at the open; stop beats
take-profit inside one bar; CPMM fills use reserves at the fill bar's open; fees are explicit.
"""
from __future__ import annotations


def cpmm_out(reserve_in: float, reserve_out: float, amount_in: float, fee: float) -> float:
    if reserve_in <= 0 or reserve_out <= 0 or amount_in < 0:
        raise ValueError("invalid reserves or amount")
    a = amount_in * (1.0 - fee)
    return reserve_out * a / (reserve_in + a)


class Exec:
    """mode 'flat': price * units with fee; mode 'cpmm': quote reserve fixed in USD at the bar open."""

    def __init__(self, mode: str, fee: float, quote_reserve_usd: float = 0.0, network_fee_usd: float = 0.0):
        self.mode, self.fee, self.q, self.nf = mode, fee, quote_reserve_usd, network_fee_usd

    def buy(self, usd: float, px_open: float) -> tuple[float, float]:
        """returns (tokens, cash_spent)"""
        if self.mode == "flat":
            return usd * (1 - self.fee) / px_open, usd
        tok = cpmm_out(self.q, self.q / px_open, usd, self.fee)
        return tok, usd + self.nf

    def sell(self, tokens: float, px: float) -> float:
        if self.mode == "flat":
            return tokens * px * (1 - self.fee)
        return cpmm_out(self.q / px, self.q, tokens, self.fee) - self.nf


def first_bar_at_or_after(bars, t):
    for i, b in enumerate(bars):
        if b["t"] >= t:
            return i
    return None


def run_breakout(d, size, ex: Exec, latency=0):
    bars, H, p = d["bars"], d["bar_seconds"], d["strategy_breakout"]
    lb, trades, i = p["lookback"], [], p["lookback"]
    while i < len(bars):
        prior_high = max(b["h"] for b in bars[i - lb:i])          # closed bars only
        if bars[i]["c"] > prior_high:
            decision_t = bars[i]["t"] + H                           # bar i is knowable at its close
            j = first_bar_at_or_after(bars, decision_t + latency)
            if j is None:
                break
            entry_px = bars[j]["o"]
            tok, spent = ex.buy(size, entry_px)
            stop = entry_px * (1 - p["stop_frac"])
            exit_i, exit_px, why = None, None, None
            for k in range(j, min(j + p["max_hold_bars"], len(bars))):
                b = bars[k]
                if k > j and b["o"] <= stop:
                    exit_i, exit_px, why = k, b["o"], "STOP_GAP_FILL_AT_OPEN"; break
                if b["l"] <= stop:
                    exit_i, exit_px, why = k, stop, "STOP_INTRABAR"; break
            if exit_i is None:
                exit_i = min(j + p["max_hold_bars"], len(bars) - 1)
                exit_px, why = bars[exit_i]["o"], "TIME_EXIT_AT_OPEN"
            proceeds = ex.sell(tok, exit_px)
            trades.append({"signal_bar": i, "decision_t": decision_t, "entry_bar": j, "entry_t": bars[j]["t"], "entry_px": entry_px,
                           "tokens": tok, "spent": spent, "exit_bar": exit_i, "exit_px": exit_px, "reason": why, "proceeds": proceeds,
                           "pnl": proceeds - spent, "ret": proceeds / spent - 1})
            i = exit_i + 1
            continue
        i += 1
    return trades


def run_event(d, size, ex: Exec, use_field="first_seen_at", latency=0):
    bars, ev, hold = d["bars"], d["event"], d["strategy_event"]["hold_bars"]
    decision_t = ev[use_field]
    j = first_bar_at_or_after(bars, decision_t + latency)
    tok, spent = ex.buy(size, bars[j]["o"])
    k = j + hold
    proceeds = ex.sell(tok, bars[k]["o"])
    return [{"decision_t": decision_t, "entry_bar": j, "entry_t": bars[j]["t"], "entry_px": bars[j]["o"], "exit_bar": k, "exit_px": bars[k]["o"],
             "tokens": tok, "spent": spent, "proceeds": proceeds, "pnl": proceeds - spent, "ret": proceeds / spent - 1}]

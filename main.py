"""BTC trading bot for make.fun btc-race-24h-20261117-0603.

Strategy (long only, one position, full size):
- Entry: buy 100% of cash when the close is at least 80 bps below the 240-bar simple
  moving average of closes (a deep dip against the 4-hour mean). If no dip has fired by
  bar 720 (halfway through the window), buy at the market anyway, so the bot always
  takes at least one trade. Only one entry: after the position is closed the bot never
  re-enters.
- Exit: take profit at +200 bps above the entry close, or a hard stop at -150 bps below
  the entry close. Otherwise hold to the end of the window (the harness flattens).
- Every order caps slippage at 200 bps so gap moves do not reject it.

Why this shape: a full-size round trip costs about 37 bps on this pool (4 bps fee +
2 bps slippage + ~13 bps of price impact per leg at the dev window's depth), and the
dev window is choppy 1-minute noise (6.5 bps stdev) over +-100 bps hourly swings.
Fast crossovers and breakouts whipsaw into losses on it (the house ema-cross baseline
loses $106 on the dev window); a single selective dip entry plus banking a large leg
is what survives. The entry reference is the close of the bar the buy was decided on,
and a fill is only armed when the harness reports it filled, so a rejected buy can
fire again instead of stranding the bot in cash.

All decisions use integer math on the bar closes (plus one float mean); no randomness,
no clock, no environment, no files, no network. Deterministic: the same bars give the
same orders on every run.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
SMA_BARS = 240
ENTRY_DIP_BPS = 80
FALLBACK_BAR = 720
TAKE_PROFIT_BPS = 200
STOP_LOSS_BPS = 150
MAX_SLIPPAGE_BPS = 200

closes = []
entry_close = None
bought_once = False
pending_buy_close = None


def on_batch(state, batch):
    global entry_close, bought_once, pending_buy_close
    # Fold this batch's fills in first: a filled buy arms the entry reference; a
    # rejected buy clears it so the signal can fire again.
    for fill in batch.get("fills", []):
        if fill.get("symbol") != SYMBOL:
            continue
        if fill.get("status") == "filled" and fill.get("side") == "buy":
            if pending_buy_close is not None:
                entry_close = pending_buy_close
            bought_once = True
            pending_buy_close = None
        elif fill.get("status") == "rejected" and fill.get("side") == "buy":
            pending_buy_close = None
        elif fill.get("status") == "filled" and fill.get("side") == "sell":
            entry_close = None
    # Track closes: only bars that actually carry CBBTC (a missing minute has no bar).
    for bar in batch.get("bars", []):
        if bar.get("symbol") == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    close = state.close(SYMBOL)
    if close is None:
        return []
    held = state.positions.get(SYMBOL)
    if held is None:
        if bought_once:
            return []
        if len(closes) >= SMA_BARS:
            mean = sum(closes[-SMA_BARS:]) / SMA_BARS
            if (mean - close) * 10000 // mean >= ENTRY_DIP_BPS:
                pending_buy_close = close
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": state.cash,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if len(closes) > FALLBACK_BAR:
            pending_buy_close = close
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    # Holding a position: take profit, hard stop, else hold.
    if entry_close is None:
        entry_close = close
    if (close - entry_close) * 10000 // entry_close >= TAKE_PROFIT_BPS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    if (entry_close - close) * 10000 // entry_close >= STOP_LOSS_BPS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)

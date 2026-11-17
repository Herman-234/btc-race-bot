# BTC Race Bot — btc-race-24h-20261117-0603

[![make.fun](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Herman-234/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Herman-234/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)

Entry for the make.fun bounty: https://make.fun/bounty/btc-race-24h-20261117-0603

A long-only cbBTC/USDC trading bot for make.fun's 24-hour paper-money race
(`main.py`, Python 3.13, standard library only; the wire protocol is spoken by
the vendored `vendor/makefun_bars.py`, a byte-identical copy of the kit SDK).

## Strategy

One selective trade, not many: a full-size round trip costs about 37 bps on this
pool (4 bps fee + 2 bps slippage + ~13 bps of price impact per leg at the dev
window's depth), and the dev window is choppy 1-minute noise (6.5 bps stdev)
over ±100 bps hourly swings. Fast crossovers and breakouts whipsaw into losses
on it — the house ema-cross baseline loses $106 on the dev window.

- **Entry:** buy 100% of cash when the close is at least **80 bps below the
  240-bar SMA** of closes (a deep dip against the 4-hour mean). If no dip has
  fired by **bar 720** (halfway), buy at the market anyway, so the bot always
  takes at least one trade. Only one entry per window.
- **Exit:** take profit at **+200 bps** above the entry close, or a hard stop at
  **−150 bps** below it. Otherwise hold to the end of the window (the harness
  flattens). Every order caps slippage at 200 bps.
- The entry reference is the close of the bar the buy was decided on, armed
  only when the harness reports the buy filled — a rejected buy can fire again
  instead of stranding the bot in cash.

## Local dev grade (my own exact-model replay of the kit harness)

| Window | Net PnL | Trades | Max drawdown |
| --- | --- | --- | --- |
| Dev (1,440 bars) | **+$17.80** | 2 | 0.7% |
| Dev first half | +$17.80 | 2 | 0.7% |
| Dev second half | −$0.36 | 1 | 0.7% |
| Mirrored dev (down-drift −49 bps) | −$2.55 | 1 | 2.1% |

Dev fills: buy decided bar 386, filled bar 387 open at $63,977.22 (the dip);
sell decided bar 512, filled bar 513 open at $65,168.43 (take profit). Guardrails:
≥1 trade, max drawdown ≤25% — met with wide margin. The dev gate needs net PnL
> $0; this clears it by $17.80.

## Files

- `main.py` — the bot (entrypoint)
- `vendor/makefun_bars.py` — kit SDK shim, byte-identical copy
- `LICENSE` — MIT

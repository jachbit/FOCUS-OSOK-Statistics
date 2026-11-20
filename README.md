# F.O.C.U.S.© OSOK Statistics

Jachbit 2026

Results of the timed **OSOK** (One Shot One Kill) straddle on NinjaTrader 8: a buy stop and a sell stop
placed a few seconds before a set time, one side fills, the other is cancelled (OCO).

**Live page:** the `docs/` folder, published with GitHub Pages.

## What the page shows

- **Filters:** OSOK Time (8:30 News / 9:30 NY Open / 18:00 Globex / other start times), Strategy
  (No SL / With SL), Account (Paper / Live), News release (CPI, PPI, ...) and a date range.
  Every number, the equity curve and the tables recalculate when a filter is clicked.
- **Breakdowns:** by OSOK time, 8:30 News by release, by strategy, by side, paper vs live, by version.
- **Every trade with its math:** `exit - entry = pts x $/pt x contracts = result`.
- **PDF:** prints the current filtered view in the ink-saving F.O.C.U.S. style
  (save as `FOCUS_OSOK_Stats_YYYYMMDD_HHMMSS.pdf`).
- **CSV export:** the filtered trades, `FOCUS_OSOK_Stats_Trades_YYYYMMDD_HHMMSS.csv`.
- **CSV import:** merges trades from a CSV in the same format. Duplicates (same date, time, account,
  side and entry) are skipped; imported rows are marked *imported* and kept in that browser only.
  **Clear imported** removes them.

Account names are masked on the public page (Paper 1, Paper 2, Live 1 ...).

## Build (local)

1. Tag news releases in `news_events.txt`, one per line: `2026-12-10 CPI`.
2. Run `make_stats.bat` (or `python build_stats.py`).
   - `local/OSOK_Stats.html` - your copy with the real account names (never uploaded).
   - `docs/index.html` + `docs/trades.json` - the public copy, account names masked.
   - The build stops with an error if a real account name is found in `docs/`.
3. Commit and push `docs/` to update the live page.

The data comes from NinjaTrader's own log files (`Documents\NinjaTrader 8\log\log.*.en.txt`):
entries are the BuyStop / SellStop fills from the OSOK No SL / With SL strategies, exits are the next
TakeProfit / StopLoss / StopLossMkt fill on the same account and instrument.

Not financial advice. Paper results are not live results.

© 2026 Jachbit 2026. All rights reserved - see `LICENSE`.

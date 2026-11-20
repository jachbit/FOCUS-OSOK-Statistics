# F.O.C.U.S.© OSOK Statistics

Jachbit 2026

Results of the timed **OSOK** (One Shot One Kill) straddle on NinjaTrader 8: a buy stop and a sell stop
placed a few seconds before a set time, one side fills, the other is cancelled (OCO).

**Live page:** the `docs/` folder, published with GitHub Pages.

## What the page shows

- **Filters:** OSOK Time (8:30 News / 9:30 NY Open / 18:00 Globex / Other times), Strategy
  (No SL / With SL / ATM Entry), Account (Paper, Live or one account), News release (CPI, PPI, ...)
  and a date range. Every number, the equity curve and the tables recalculate when a filter is clicked.
  Filters also work as a link, e.g. `#strat=ATM Entry&acct=Paper 2`.
- **Breakdowns:** by OSOK time, 8:30 News by release, by strategy, by side, paper vs live, by account,
  by version.
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

| Strategy | Entry in the log | Exit in the log |
|---|---|---|
| No SL / With SL | BuyStop / SellStop fills from `OSOK_AutoStopOrder_OCO_NoSL` / `_WithSL` (and the older `AutoStopOrderOCOGV6_NoSL` / `GV7_WithSL`) | the next TakeProfit / StopLoss / StopLossMkt fill |
| ATM Entry | `Entry` fills whose OCO starts with `OSOKATM_` - the BRACKET trades of the `OSOK_ATM_Level_Entry` window | Target1-3 / Stop / Stop1-3 / StopMkt / Close fills until the position is closed (average exit price) |

Exits are matched on the same account and instrument. Manual Chart Trader trades are never counted.

## Use it with your own NinjaTrader 8

The live page shows the owner's trades. To see **your own** trades, build the page on your own PC -
it reads your NinjaTrader logs and nothing leaves your computer.

1. **Permission:** this project is all rights reserved (see `LICENSE`) - ask the owner before using it.
2. **Python 3:** install it from python.org and tick *Add python.exe to PATH*. No extra packages are needed.
3. **Download:** on this repo page click **Code > Download ZIP** and unzip it anywhere, e.g. `C:\OSOK-Stats`.
4. **The OSOK strategies:** the page only counts trades from the strategies in the table above, found by
   their names in the log. Import them into your NinjaTrader 8 (ask the owner for the `.cs` files; they are
   not in this repo) and trade with them. Trades from other strategies or by hand are not found.
5. **News days:** open `news_events.txt`, delete the example lines and add your own releases, one per line:
   `2026-12-10 CPI`.
6. **Build:** after each session double-click `make_stats.bat`. It opens your page,
   `local\OSOK_Stats.html`, with your real account names.
   - Your NinjaTrader must be the standard install (logs in `Documents\NinjaTrader 8\log`).
   - The page is only as complete as the log folder: if old log files are deleted, their trades drop off
     the page - export a CSV now and then and keep it.
   - The `docs\` folder is rebuilt with your trades (account names masked), replacing the owner's copy
     from the ZIP. Publish it on your own GitHub Pages only if you want a public page.
7. **Times** are your PC's time zone. The OSOK times 8:30 News / 9:30 NY Open / 18:00 Globex are found at
   05:30 / 06:30 / 15:00 Pacific; on a PC in another time zone those trades show under *Other times*.

**CSV import** only reads a CSV in this page's own export format (the CSV export button), not
NinjaTrader's Trade Performance export.

Not financial advice. Paper results are not live results.

© 2026 Jachbit 2026. All rights reserved - see `LICENSE`.

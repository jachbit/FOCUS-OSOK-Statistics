r"""
F.O.C.U.S.(c) OSOK Statistics - build_stats.py
Jachbit 2026

Reads NinjaTrader 8's own log files (Documents\NinjaTrader 8\log\log.*.en.txt), finds every timed OSOK trade
(entry = BuyStop / SellStop fill from an OSOK No SL or With SL strategy, exit = the next TakeProfit / StopLoss /
StopLossMkt fill on the same account + instrument) and writes the OSOK Stats page in the F.O.C.U.S. page template style.

The page has a filter bar - OSOK Time (8:30 News / 9:30 NY Open / 18:00 Globex / other start times), Strategy
(No SL / With SL), Account (Paper / Live), News (CPI / PPI / ... from news_events.txt) and a date range.
Every number, the curve and the tables recalculate in the browser when a filter is clicked.

News tags: news_events.txt next to this script, one line per release:  2026-11-13 PPI
           (applies to that date's 8:30 News trades; lines starting with # are notes)

Writes TWO copies:
  local\OSOK_Stats.html  - your copy, real account names (never uploaded - local\ is in .gitignore)
  docs\index.html        - the GitHub Pages copy, account names masked (Paper 1, Paper 2, Live 1 ...)
  docs\trades.json       - the masked trade data
The alias list (real name -> Paper n / Live n) is kept in local\account_aliases.json so an account
always gets the same alias.

The page also has PDF (prints the filtered view in the ink-saving PDF style), CSV export (the filtered
trades) and CSV import (merge trades from a CSV in the same format; kept in that browser, Clear imported).

Run:  python build_stats.py     or double-click make_stats.bat (re-run after each session)
"""
import glob, html, json, os, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(os.path.expanduser("~"), "Documents", "NinjaTrader 8", "log")
LOCAL_OUT = os.path.join(HERE, "local", "OSOK_Stats.html")
DOCS_OUT = os.path.join(HERE, "docs", "index.html")
DOCS_JSON = os.path.join(HERE, "docs", "trades.json")
ALIAS_FILE = os.path.join(HERE, "local", "account_aliases.json")
NEWS_FILE = os.path.join(HERE, "news_events.txt")

POINT_VALUE = {"MNQ": 2.0, "MES": 5.0, "NQ": 20.0, "ES": 50.0, "M2K": 5.0, "RTY": 50.0, "MYM": 0.5, "YM": 5.0}
ENTRY_NAMES = {"BuyStop", "SellStop"}
EXIT_NAMES = {"TakeProfit", "StopLoss", "StopLossMkt"}
STRATS = {  # strategy name prefix -> (Strategy filter value, version label)
    "AutoStopOrderOCOGV6_NoSL":      ("No SL",   "No SL v1.0 (V6)"),
    "OSOK_AutoStopOrder_OCO_NoSL":   ("No SL",   "No SL v1.x"),
    "AutoStopOrderOCOGV7_WithSL":    ("With SL", "With SL v1.0 (V7)"),
    "OSOK_AutoStopOrder_OCO_WithSL": ("With SL", "With SL v1.x"),
}
# start time (PC / Pacific) -> OSOK Time
SESSIONS = [("05:30", "8:30 News"), ("06:30", "9:30 NY Open"), ("15:00", "18:00 Globex"), ("15:05", "18:00 Globex")]

ORDER_RE = re.compile(r"Order='[^/]+/([^']+)' Name='([^']+)' New state='Filled' Instrument='([^']+)' Action='([^']+)' "
                      r"Limit price=([\d.]+) Stop price=([\d.]+) Quantity=(\d+) Type='([^']+)'.*?Filled=(\d+) Fill price=([\d.]+)")
ENABLE_RE = re.compile(r"Enabling NinjaScript strategy '([^'/]+)/")


def is_paper(acct):
    a = acct.lower()
    return a.startswith("sim") or a.startswith("demo") or a.startswith("playback")


def strat_of(name):
    for k, v in STRATS.items():
        if name.startswith(k):
            return v
    return None


def load_news():
    if not os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "w", encoding="utf-8") as fh:
            fh.write("# F.O.C.U.S. OSOK Statistics - news releases (8:30 News trades on that date get the tag)\n"
                     "# One line per release:  YYYY-MM-DD NAME     e.g.  2026-12-10 CPI\n"
                     "# Add each release as it happens; a wrong date puts trades under the wrong release.\n"
                     "2026-11-13 PPI\n")
    tags = {}
    with open(NEWS_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
                tags[parts[0]] = parts[1].strip()
    return tags


def parse_logs():
    events = []
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "log.*.en.txt"))):
        strat = None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if len(line) < 24 or not line[:4].isdigit():
                    continue
                m = ENABLE_RE.search(line)
                if m:
                    strat = m.group(1)
                    continue
                m = ORDER_RE.search(line)
                if not m:
                    continue
                acct, name, inst, action, lmt, stp, qty, otype, filled, px = m.groups()
                if name not in ENTRY_NAMES and name not in EXIT_NAMES:
                    continue
                ts = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S:%f")
                events.append(dict(ts=ts, acct=acct, name=name, inst=inst, action=action, lmt=float(lmt),
                                   stp=float(stp), qty=int(filled), px=float(px), strat=strat or ""))
    events.sort(key=lambda e: e["ts"])
    return events


def session_for(ts):
    best = None
    for hhmm, label in SESSIONS:
        h, m = map(int, hhmm.split(":"))
        start = ts.replace(hour=h, minute=m, second=0, microsecond=0)
        d = abs((ts - start).total_seconds())
        if d <= 15 * 60 and (best is None or d < best[0]):
            best = (d, hhmm, label, start)
    if best:
        return best[1], best[2], best[3]
    # other start time: nearest 5 minutes
    mins = int(round((ts.hour * 60 + ts.minute + ts.second / 60.0) / 5.0)) * 5
    start = ts.replace(hour=(mins // 60) % 24, minute=mins % 60, second=0, microsecond=0)
    hhmm = start.strftime("%H:%M")
    return hhmm, "Other " + hhmm, start


def build_trades(events, news):
    trades, used = [], set()
    for i, e in enumerate(events):
        if e["name"] not in ENTRY_NAMES:
            continue
        st = strat_of(e["strat"])
        if st is None:
            continue
        is_long = e["name"] == "BuyStop"
        exit_action = "Sell" if is_long else "Buy to cover"
        x = None
        for j in range(i + 1, len(events)):
            c = events[j]
            if (c["ts"] - e["ts"]).total_seconds() > 8 * 3600:
                break
            if j in used or c["name"] not in EXIT_NAMES or c["acct"] != e["acct"] or c["inst"] != e["inst"] or c["action"] != exit_action:
                continue
            x = c; used.add(j); break
        root = e["inst"].split(" ")[0].upper()
        pv = POINT_VALUE.get(root, 0.0)
        hhmm, sess, start = session_for(e["ts"])
        date = e["ts"].strftime("%Y-%m-%d")
        t = dict(date=date, dow=e["ts"].strftime("%a"), time=e["ts"].strftime("%H:%M:%S.%f")[:-3],
                 session=sess, start=hhmm, vs=round((e["ts"] - start).total_seconds(), 1),
                 news=news.get(date, "") if sess == "8:30 News" else "",
                 strat=st[0], version=st[1], acct=e["acct"], paper=is_paper(e["acct"]), inst=e["inst"], root=root, pv=pv,
                 side="LONG" if is_long else "SHORT", qty=e["qty"], stop=e["stp"], entry=e["px"],
                 slip=round((e["px"] - e["stp"]) if is_long else (e["stp"] - e["px"]), 2),
                 exit=None, xname=None, xtime=None, tpl=None, pts=None, usd=None, secs=None, result="OPEN")
        if x:
            pts = (x["px"] - e["px"]) if is_long else (e["px"] - x["px"])
            t.update(exit=x["px"], xname=x["name"], xtime=x["ts"].strftime("%H:%M:%S"),
                     tpl=x["lmt"] if x["name"] == "TakeProfit" else None,
                     pts=round(pts, 2), usd=round(pts * pv * e["qty"], 2),
                     secs=round((x["ts"] - e["ts"]).total_seconds(), 1),
                     result="WIN" if pts > 0 else ("LOSS" if pts < 0 else "BE"))
        trades.append(t)
    return trades


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSOK Stats</title>
<style>
  :root { --bg0:#0a1628; --bg1:#0f1f3d; --bg2:#162545; --bg3:#1d2f52; --border:#2a3f62; --orange:#e65c00; --orange2:#ff8c42;
          --white:#e8e8e8; --green:#22c55e; --red:#ef4444; --amber:#fbbf24; --blue:#3b82f6;
          --font-mono:'Courier New','Lucida Console',monospace; --font-ui:-apple-system,'Segoe UI',Arial,sans-serif; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg0); color:var(--white); font-family:var(--font-mono); font-size:13px; line-height:1.55; padding:0 0 60px; }
  .site-header { background:var(--bg1); border-bottom:2px solid var(--orange); padding:18px 32px 14px; display:flex; flex-wrap:wrap;
                 align-items:baseline; gap:18px; }
  .logo { font-size:20px; font-weight:bold; color:var(--orange); letter-spacing:2px; white-space:nowrap; }
  .logo sup { font-size:11px; }
  .site-header h1 { font-family:var(--font-ui); font-size:15px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
  .header-meta { margin-left:auto; font-size:12px; text-align:right; line-height:1.6; font-weight:bold; }
  .header-meta strong { color:var(--orange); }
  .container { max-width:1180px; margin:0 auto; padding:22px 32px; }
  .subtitle { font-size:12px; font-weight:bold; margin-bottom:14px; }
  .filters { position:sticky; top:0; z-index:10; background:var(--bg1); border:1px solid var(--border); border-left:4px solid var(--orange);
             padding:10px 14px; margin-bottom:16px; }
  .frow { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:4px 0; }
  .frow .lab { font-family:var(--font-ui); font-weight:700; color:var(--orange2); font-size:12px; text-transform:uppercase; width:96px; }
  .chip { background:var(--bg3); color:#fff; border:1px solid var(--border); font-family:var(--font-mono); font-size:12px; font-weight:bold;
          padding:4px 10px; cursor:pointer; border-radius:3px; }
  .chip.on { background:var(--orange); border-color:var(--orange); }
  .chip:hover { border-color:var(--orange2); }
  .frow input[type=date] { background:var(--bg3); color:#fff; border:1px solid var(--border); font-family:var(--font-mono); font-size:12px;
                           font-weight:bold; padding:3px 6px; color-scheme:dark; }
  h2 { font-family:var(--font-ui); font-size:17px; color:var(--orange); border-bottom:1px solid var(--border); padding-bottom:6px; margin:24px 0 12px; }
  h3 { font-family:var(--font-ui); font-size:14px; color:var(--orange2); margin:18px 0 8px; }
  .mandate { background:var(--bg2); border:1px solid var(--border); border-left:4px solid var(--orange); padding:12px 16px; margin-bottom:14px;
             font-size:13px; font-weight:bold; }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }
  .kpi { background:var(--bg2); border:1px solid var(--border); border-top:3px solid var(--orange); padding:12px 14px; }
  .kpi .k { font-family:var(--font-ui); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--orange2); }
  .kpi .v { font-size:24px; font-weight:bold; margin:4px 0; }
  .pos { color:var(--green) !important; } .neg { color:var(--red) !important; } .warn { color:var(--amber) !important; }
  .kpi .m { font-size:12px; font-weight:bold; }
  .chart { width:100%; height:auto; background:var(--bg1); border:1px solid var(--border); display:block; }
  .chart .curve { fill:none; stroke:var(--blue); stroke-width:2.5; }
  .chart .zero { stroke:var(--border); stroke-dasharray:4 4; }
  .chart .axis { fill:var(--white); font-size:12px; font-weight:bold; font-family:var(--font-mono); }
  .grid2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:18px; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th { background:var(--bg3); color:var(--orange2); font-family:var(--font-ui); font-weight:700; text-align:right; padding:7px 8px;
       border-bottom:1px solid var(--border); white-space:nowrap; }
  td { padding:6px 8px; text-align:right; border-bottom:1px solid var(--border); font-weight:bold; white-space:nowrap; }
  th.l, td.l { text-align:left; }
  tbody tr:nth-child(even) { background:var(--bg1); }
  td.math { white-space:normal; min-width:300px; }
  .scroll { overflow-x:auto; border:1px solid var(--border); }
  .tag { display:inline-block; padding:1px 8px; font-size:12px; font-weight:bold; border-radius:3px; }
  .tag.WIN { background:#14532d; color:#bbf7d0; } .tag.LOSS { background:#7f1d1d; color:#fecaca; }
  .tag.BE, .tag.OPEN { background:var(--bg3); color:var(--white); }
  .tag.news { background:#78350f; color:#fde68a; }
  ul { margin-left:20px; } li { margin:6px 0; font-weight:bold; }
  .empty { padding:18px; font-weight:bold; background:var(--bg2); border:1px dashed var(--border); }
  footer { max-width:1180px; margin:30px auto 0; padding:14px 32px; border-top:1px solid var(--border); font-size:12px; font-weight:bold;
           text-align:center; line-height:1.8; }
  footer .verse { color:var(--orange2); }
  .chip.act { background:#14365f; }
  .inote { font-weight:bold; color:var(--amber); }
  .tag.imp { background:#1e3a8a; color:#dbeafe; }
  @media (max-width:640px) { .site-header, .container, footer { padding-left:16px; padding-right:16px; } .grid2 { grid-template-columns:1fr; }
                             .frow .lab { width:100%; } }
  /* PDF (print): ink-saving - white page, no accent fills; LIGHT_GREY bands + accent left bar / underline */
  @media print {
    @page { size: letter landscape; margin: 12mm; }
    body { background:#fff !important; color:#000 !important; font-size:10px; padding:0; }
    .site-header { background:#fff !important; border-bottom:1px solid #999; position:static; padding:0 0 6px; }
    .site-header h1, .header-meta { color:#002b5c !important; } .logo { color:#002b5c !important; }
    .filters, .mandate, .noprint { display:none !important; }
    .container { padding:6px 0; max-width:none; }
    .subtitle { color:#000; font-size:10px; }
    h2, h3 { background:#f0f0f0 !important; color:#002b5c !important; border-left:4px solid #002b5c; border-bottom:1px solid #002b5c;
             padding:3px 8px; page-break-after:avoid; }
    .kpi { background:#fff !important; border:1px solid #bbb !important; border-top:1px solid #bbb !important; }
    .kpi .k { color:#002b5c !important; } .kpi .v, .kpi .m { color:#000 !important; }
    .pos { color:#0d6125 !important; } .neg { color:#8c1a05 !important; } .warn { color:#8a5a00 !important; }
    .chart { background:#fff !important; border:1px solid #bbb; } .chart .axis { fill:#000 !important; } .chart .curve { stroke:#002b5c !important; }
    th { background:#f0f0f0 !important; color:#002b5c !important; } td { color:#000; border-bottom:1px solid #ddd; }
    tbody tr:nth-child(even) { background:#fafafa !important; }
    .scroll { overflow:visible; border:none; } table { font-size:9px; } tr { page-break-inside:avoid; }
    .tag { border:1px solid #888; background:#fff !important; color:#000 !important; }
    li { color:#000; }
    footer { color:#000; border-top:1px solid #999; } footer .verse { color:#000 !important; }
    * { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  }
</style></head>
<body>
<header class="site-header">
  <div class="logo">F.O.C.U.S.<sup>&copy;</sup></div>
  <h1>OSOK Stats</h1><span class="noprint" style="font-weight:bold">__COPYNOTE__</span>
  <div class="header-meta">Jachbit 2026 &middot; built <strong>__BUILT__</strong><br>source: NinjaTrader 8 logs</div>
</header>
<main class="container">
  <div class="subtitle" id="subtitle"></div>
  <div class="filters" id="filters"></div>
  <div class="frow noprint" style="margin:-6px 0 14px">
    <button class="chip act" id="bPdf" title="Print the current filtered view as a PDF (ink-saving style)">PDF</button>
    <button class="chip act" id="bCsv" title="Download the filtered trades as a CSV">CSV export</button>
    <button class="chip act" id="bImp" title="Merge trades from a CSV in the same format (kept in this browser)">CSV import</button>
    <button class="chip" id="bClr" title="Remove the imported trades from this browser">Clear imported</button>
    <input type="file" id="fImp" accept=".csv,text/csv" style="display:none">
    <span class="inote" id="impNote"></span>
  </div>
  <div class="mandate">One-Shot-One-Kill straddle: a few seconds before the start time a Buy Stop and a Sell Stop go in around the price (PAD),
  linked OCO; the first move fills one side and the exit orders go in (No SL: Take Profit only; With SL: Take Profit + Stop Loss).
  Times are the PC's (Pacific). Built from NinjaTrader's own log files - double-click <b>make_stats.bat</b> after each session.
  Click the filters above: every number below recalculates.</div>
  <div class="kpis" id="kpis"></div>
  <h3>Cumulative P/L (gross, $)</h3>
  <div id="chart"></div>
  <div class="grid2"><div id="bySession"></div><div id="byNews"></div></div>
  <div class="grid2"><div id="byStrat"></div><div id="bySide"></div></div>
  <div class="grid2"><div id="byAcct"></div><div id="byAcctName"></div></div>
  <div class="grid2"><div id="byVer"></div><div></div></div>
  <h3>Every trade, with the math</h3>
  <div class="scroll"><table><thead><tr><th>#</th><th class="l">Date</th><th class="l">OSOK Time</th><th class="l">News</th><th>Entry fill (PT)</th>
    <th>vs start</th><th class="l">Strategy</th><th class="l">Side</th><th>Stop</th><th>Fill</th><th>Slip</th><th>Exit</th>
    <th class="l">Result math</th><th>Result</th><th class="l">Account</th></tr></thead><tbody id="rows"></tbody></table></div>
  <h2>Read this before trusting the numbers</h2>
  <ul id="caveats"></ul>
</main>
<footer>
  F.O.C.U.S.&copy; &middot; Jachbit 2026 &middot; OSOK Stats<br>
  <span class="verse">John 3:16 | 1 John 3:16 | Matt 6:33 | Jer 33:3 | Prov 3:5-6 | Prov 27:17</span><br>
  &copy; 2026 Jachbit. All rights reserved. May not be copied or shared without express written consent of the publisher. linktr.ee/jachbit
</footer>
<script>
const LOGDATA = __DATA__;
const IMPORT_KEY = "focus_osok_stats_imported_v1__" + "__COPYKEY__";
let DATA = [];
const BUILT = "__BUILT__";
const F = { time:"All", strat:"All", acct:"All", news:"All", from:"", to:"" };
const SESSION_ORDER = ["8:30 News", "9:30 NY Open", "18:00 Globex"];

const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num = (v, d=2) => { if (v == null) return "-"; let s = Number(v).toFixed(d); return s.indexOf(".") >= 0 ? s.replace(/0+$/,"").replace(/\.$/,"") : s; };
const money = v => (v > 0 ? "+$" : v < 0 ? "-$" : "$") + Math.abs(v).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
const cls = v => v > 0 ? "pos" : v < 0 ? "neg" : "";

function distinct(key) { return [...new Set(DATA.map(t => t[key]).filter(v => v !== ""))]; }

function chipRow(label, key, values) {
  const all = ["All", ...values];
  return `<div class="frow"><span class="lab">${label}</span>` +
    all.map(v => `<button class="chip ${F[key] === v ? "on" : ""}" data-k="${key}" data-v="${esc(v)}">${esc(v)}</button>`).join("") + `</div>`;
}

function drawFilters() {
  const sessions = distinct("session").sort((a, b) => {
    const ia = SESSION_ORDER.indexOf(a), ib = SESSION_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b); });
  const strats = ["No SL", "With SL"];
  const news = distinct("news").sort();
  const dates = DATA.map(t => t.date).sort();
  // one chip per account after Paper / Live: paper accounts first, then live, natural order (Paper 2 before Paper 10)
  const accts = acctList(DATA);
  document.getElementById("filters").innerHTML =
    chipRow("OSOK Time", "time", sessions) + chipRow("Strategy", "strat", strats) + chipRow("Account", "acct", ["Paper", "Live", ...accts]) +
    chipRow("News", "news", news.length ? news : []) +
    `<div class="frow"><span class="lab">Dates</span><input type="date" id="dfrom" value="${F.from}" min="${dates[0]||""}" max="${dates[dates.length-1]||""}">
     <span>to</span><input type="date" id="dto" value="${F.to}" min="${dates[0]||""}" max="${dates[dates.length-1]||""}">
     <button class="chip" id="dclear">All dates</button></div>`;
  document.querySelectorAll(".chip[data-k]").forEach(b => b.onclick = () => { F[b.dataset.k] = b.dataset.v; drawFilters(); render(); });
  document.getElementById("dfrom").onchange = e => { F.from = e.target.value; render(); };
  document.getElementById("dto").onchange = e => { F.to = e.target.value; render(); };
  document.getElementById("dclear").onclick = () => { F.from = ""; F.to = ""; drawFilters(); render(); };
}

function acctList(ts) {
  const paperOf = {}; ts.forEach(t => { paperOf[t.acct] = t.paper; });
  return Object.keys(paperOf).filter(a => a !== "").sort((a, b) =>
    (paperOf[a] === paperOf[b] ? 0 : paperOf[a] ? -1 : 1) || a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
}
function acctMatch(t) {
  if (F.acct === "All") return true;
  if (F.acct === "Paper") return t.paper;
  if (F.acct === "Live") return !t.paper;
  return t.acct === F.acct;
}

function pick() {
  return DATA.filter(t =>
    (F.time === "All" || t.session === F.time) &&
    (F.strat === "All" || t.strat === F.strat) &&
    acctMatch(t) &&
    (F.news === "All" || t.news === F.news) &&
    (!F.from || t.date >= F.from) && (!F.to || t.date <= F.to));
}

function stats(ts) {
  const done = ts.filter(t => t.result !== "OPEN"), wins = done.filter(t => t.result === "WIN"), losses = done.filter(t => t.result === "LOSS");
  const sum = (a, k) => a.reduce((s, t) => s + t[k], 0);
  const med = a => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y), m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2; };
  let peak = 0, cum = 0, mdd = 0;
  done.forEach(t => { cum += t.usd; peak = Math.max(peak, cum); mdd = Math.min(mdd, cum - peak); });
  const gw = sum(wins, "usd"), gl = -sum(losses, "usd");
  return { n: done.length, open: ts.length - done.length, wins: wins.length, losses: losses.length,
           winrate: done.length ? 100 * wins.length / done.length : 0, pts: sum(done, "pts"), usd: sum(done, "usd"),
           avgWin: wins.length ? gw / wins.length : 0, avgLoss: losses.length ? -gl / losses.length : 0,
           pf: gl > 0 ? gw / gl : null, mdd, slipAvg: done.length ? sum(done, "slip") / done.length : 0,
           slipMax: done.length ? Math.max(...done.map(t => t.slip)) : 0, secsMed: med(done.map(t => t.secs)),
           early: done.filter(t => t.vs < 0).length, days: new Set(done.map(t => t.date)).size };
}

function kpis(s) {
  const pf = s.n ? (s.pf === null ? (s.losses ? "-" : "no losses") : s.pf.toFixed(2)) : "-";
  const cards = [
    ["Trades", s.n, `${s.days} sessions${s.open ? ", " + s.open + " open" : ""}`, ""],
    ["Win rate", s.n ? s.winrate.toFixed(0) + "%" : "-", `${s.wins} wins / ${s.losses} losses`, ""],
    ["Net P/L (gross)", money(s.usd), `${num(s.pts)} pts, before commissions`, cls(s.usd)],
    ["Avg per trade", s.n ? money(s.usd / s.n) : "-", s.n ? `${num(s.pts / s.n)} pts avg` : "", cls(s.usd)],
    ["Avg win / loss", s.wins ? money(s.avgWin) : "-", s.losses ? "avg loss " + money(s.avgLoss) : "no losses", ""],
    ["Profit factor", pf, "gross wins / gross losses", ""],
    ["Max drawdown", money(s.mdd), "on the cumulative curve", cls(s.mdd)],
    ["Entry slippage", s.n ? num(s.slipAvg) + " pts" : "-", s.n ? `avg, worst ${num(s.slipMax)} pts (+ = against you)` : "", ""],
    ["Time to exit", s.n ? num(s.secsMed, 1) + " s" : "-", "median, entry fill to exit fill", ""],
  ];
  return cards.map(([k, v, m, c]) => `<div class="kpi"><div class="k">${k}</div><div class="v ${c}">${v}</div><div class="m">${m}</div></div>`).join("");
}

function chart(ts) {
  const done = ts.filter(t => t.result !== "OPEN");
  if (!done.length) return `<div class="empty">No closed trades for these filters.</div>`;
  const W = 900, H = 220, P = 36; let cum = 0; const pts = [0];
  done.forEach(t => { cum += t.usd; pts.push(cum); });
  const lo = Math.min(...pts, 0), hi = Math.max(...pts, 1), span = (hi - lo) || 1;
  const xs = pts.map((_, i) => P + i * (W - 2 * P) / (pts.length - 1)), ys = pts.map(v => H - P - (v - lo) / span * (H - 2 * P));
  const d = xs.map((x, i) => (i ? "L" : "M") + x.toFixed(1) + "," + ys[i].toFixed(1)).join(" ");
  const zy = H - P - (0 - lo) / span * (H - 2 * P);
  const dots = done.map((t, i) => `<circle cx="${xs[i+1].toFixed(1)}" cy="${ys[i+1].toFixed(1)}" r="3.5" fill="${t.usd > 0 ? "var(--green)" : t.usd < 0 ? "var(--red)" : "var(--white)"}"><title>#${i+1} ${t.date} ${t.session}${t.news ? " " + t.news : ""} ${t.side}: ${money(t.usd)} (total ${money(pts[i+1])})</title></circle>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="Cumulative P/L"><line x1="${P}" y1="${zy.toFixed(1)}" x2="${W-P}" y2="${zy.toFixed(1)}" class="zero"/>
    <text x="${P}" y="${P-10}" class="axis">${money(hi)}</text><text x="${P}" y="${H-8}" class="axis">${money(lo)}</text><path d="${d}" class="curve"/>${dots}</svg>`;
}

function breakdown(ts, key, title, label) {
  const groups = {};
  ts.filter(t => t.result !== "OPEN").forEach(t => { const k = key === "paper" ? (t.paper ? "Paper" : "Live") : (t[key] || "untagged"); (groups[k] = groups[k] || []).push(t); });
  const keys = key === "acct" ? acctList(ts.filter(t => t.result !== "OPEN")) : Object.keys(groups).sort();
  if (!keys.length) return `<h3>${title}</h3><div class="empty">-</div>`;
  return `<h3>${title}</h3><table><thead><tr><th class="l">${label}</th><th>Trades</th><th>W/L</th><th>Win %</th><th>Pts</th><th>P/L</th><th>Avg slip</th></tr></thead><tbody>` +
    keys.map(k => { const s = stats(groups[k]);
      return `<tr><td class="l">${esc(k)}</td><td>${s.n}</td><td>${s.wins}/${s.losses}</td><td>${s.winrate.toFixed(0)}%</td><td>${num(s.pts)}</td><td class="${cls(s.usd)}">${money(s.usd)}</td><td>${num(s.slipAvg)}</td></tr>`; }).join("") +
    `</tbody></table>`;
}

function rows(ts) {
  if (!ts.length) return `<tr><td colspan="15" class="l">No trades for these filters.</td></tr>`;
  return ts.map((t, i) => {
    let math = "still open (no exit fill found yet)";
    if (t.result !== "OPEN") {
      const [a, b] = t.side === "LONG" ? [t.exit, t.entry] : [t.entry, t.exit];
      math = `${num(a)} - ${num(b)} = ${num(t.pts)} pts x $${num(t.pv)} x ${t.qty} = ${money(t.usd)} (${t.xname})`;
      if (t.tpl && Math.abs(t.exit - t.tpl) > 1e-9) math += ` - TP limit ${num(t.tpl)}, filled better`;
    }
    return `<tr><td>${i+1}</td><td class="l">${t.date} ${t.dow}</td><td class="l">${esc(t.session)}</td><td class="l">${t.news ? `<span class="tag news">${esc(t.news)}</span>` : ""}</td>
      <td>${t.time}</td><td class="${t.vs < 0 ? "warn" : ""}">${(t.vs > 0 ? "+" : "") + t.vs.toFixed(1)} s</td><td class="l">${esc(t.version)}</td><td class="l">${t.side}</td>
      <td>${num(t.stop)}</td><td>${num(t.entry)}</td><td>${num(t.slip)}</td><td>${num(t.exit)}</td><td class="l math">${esc(math)}</td>
      <td><span class="tag ${t.result}">${t.result}</span>${t.imported ? ' <span class="tag imp">imported</span>' : ""}</td><td class="l">${esc(t.acct)}</td></tr>`; }).join("");
}

function caveats(ts, s) {
  const items = [];
  const nosl = ts.filter(t => t.strat === "No SL" && t.result !== "OPEN");
  if (nosl.length) items.push(`<b>No SL trades have no stop loss.</b> ${nosl.filter(t => t.result === "LOSS").length ? "" : "None of them has lost yet, but "}one release that fills a side and runs the other way can erase many wins: a 60-pt run against 1 MNQ = 60 x $2 = -$120 = 7.5 typical +8-pt wins (+$16 each). The 11/13 8:30 PPI bar swung about 110 pts in seconds.`);
  const better = ts.filter(t => t.tpl && t.exit != null && Math.abs(t.exit - t.tpl) > 1e-9);
  if (better.length) items.push(`<b>Sim fills can be generous.</b> ${better.length} target(s) filled better than their limit because the price was already past it. Live, plan on the TP points; treat the extra as a bonus.`);
  if (s.n) items.push(`<b>Entries before the start time:</b> ${s.early} of ${s.n} filled before it (yellow 'vs start') - pre-event jitter bigger than the PAD, not the event move itself.`);
  if (ts.some(t => t.date === "2026-11-08")) items.push(`<b>11/08 both sides filled</b> (No SL v1.0 / V6): the Buy Stop and the Sell Stop both filled within 0.1 s - the old version's OCO did not hold in that spike. Both reached their TP.`);
  if (ts.some(t => t.pts && Math.abs(t.pts) >= 15.5 && Math.abs(t.pts) <= 16.5)) items.push(`<b>The target was not always 8 pts</b> (e.g. 11/17 18:00 used 16). Compare like with like.`);
  items.push(`<b>Gross, before commissions</b>, at the instrument's $ per point (MNQ $2).`);
  items.push(`<b>Sample size:</b> ${s.n} trade(s) over ${s.days} session(s) for these filters - a start, not proof.`);
  items.push(`<b>News tags</b> come from news_events.txt (one line per release, e.g. 2026-12-10 CPI) and only mark 8:30 News trades. Add each release as it happens.`);
  return items.map(x => `<li>${x}</li>`).join("");
}

/*CSV-BEGIN*/
const CSV_COLS = ["date","dow","time","session","start","vs","news","strat","version","acct","paper","inst","root","pv","side","qty",
  "stop","entry","slip","exit","xname","xtime","tpl","pts","usd","secs","result","math"];
const CSV_NUM = new Set(["vs","pv","qty","stop","entry","slip","exit","tpl","pts","usd","secs"]);
function mathOf(t) {
  if (t.result === "OPEN" || t.exit == null) return "open";
  const a = t.side === "LONG" ? t.exit : t.entry, b = t.side === "LONG" ? t.entry : t.exit;
  return `${a} - ${b} = ${t.pts} pts x $${t.pv} x ${t.qty} = ${t.usd}`;
}
function csvCell(v) { const s = v == null ? "" : String(v); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
function toCsv(rows) {
  return [CSV_COLS.join(",")].concat(rows.map(t => CSV_COLS.map(c => csvCell(c === "math" ? mathOf(t) : t[c])).join(","))).join("\r\n") + "\r\n";
}
function parseCsvText(text) {
  const out = []; let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) { if (ch === '"') { if (text[i+1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; }
    else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i+1] === "\n") i++; row.push(cell); cell = ""; if (row.some(c => c !== "")) out.push(row); row = []; }
    else cell += ch;
  }
  row.push(cell); if (row.some(c => c !== "")) out.push(row);
  return out;
}
// CSV text -> trades (same columns as the export). Bad rows are skipped and counted.
function fromCsv(text) {
  const rows = parseCsvText(text.replace(/^\uFEFF/, ""));
  if (!rows.length) return { trades: [], skipped: 0, error: "empty file" };
  const head = rows[0].map(h => h.trim());
  const need = ["date","time","side","entry"];
  const miss = need.filter(n => head.indexOf(n) < 0);
  if (miss.length) return { trades: [], skipped: 0, error: "missing columns: " + miss.join(", ") };
  const trades = []; let skipped = 0;
  rows.slice(1).forEach(r => {
    const t = {};
    head.forEach((h, i) => { if (CSV_COLS.indexOf(h) >= 0 && h !== "math") t[h] = r[i] == null ? "" : r[i]; });
    CSV_NUM.forEach(k => { t[k] = (t[k] === "" || t[k] == null) ? null : Number(t[k]); });
    t.paper = String(t.paper).toLowerCase() === "true" || /^(sim|demo|playback|paper)/i.test(t.acct || "");
    t.side = String(t.side || "").toUpperCase();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(t.date || "") || (t.side !== "LONG" && t.side !== "SHORT") || t.entry == null || isNaN(t.entry)) { skipped++; return; }
    t.qty = t.qty || 1; t.pv = t.pv == null ? 2 : t.pv; t.slip = t.slip || 0; t.vs = t.vs || 0;
    if (t.exit != null && !isNaN(t.exit)) {
      t.pts = t.pts != null ? t.pts : Math.round(((t.side === "LONG" ? t.exit - t.entry : t.entry - t.exit)) * 100) / 100;
      t.usd = t.usd != null ? t.usd : Math.round(t.pts * t.pv * t.qty * 100) / 100;
      t.result = t.result || (t.pts > 0 ? "WIN" : t.pts < 0 ? "LOSS" : "BE");
    } else { t.result = "OPEN"; t.pts = null; t.usd = null; }
    t.session = t.session || "Other"; t.strat = t.strat || "No SL"; t.version = t.version || "imported"; t.news = t.news || "";
    t.dow = t.dow || ""; t.secs = t.secs || 0; t.imported = true;
    trades.push(t);
  });
  return { trades, skipped, error: null };
}
function tradeKey(t) { return [t.date, String(t.time).slice(0, 8), t.acct, t.side, Number(t.entry).toFixed(2)].join("|"); }
// merge: rows already in the log data (same date / time to the second / account / side / entry) are skipped
function mergeTrades(base, extra) {
  const seen = new Set(base.map(tradeKey)); const add = [];
  extra.forEach(t => { const k = tradeKey(t); if (!seen.has(k)) { seen.add(k); add.push(t); } });
  return { merged: base.concat(add).sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time)), added: add.length, dup: extra.length - add.length };
}
/*CSV-END*/

function stamp() { const d = new Date(), p = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`; }
function loadImported() { try { return JSON.parse(localStorage.getItem(IMPORT_KEY) || "[]"); } catch (e) { return []; } }
function saveImported(rows) { try { localStorage.setItem(IMPORT_KEY, JSON.stringify(rows)); } catch (e) {} }
function rebuildData() {
  const imp = loadImported(); const m = mergeTrades(LOGDATA, imp); DATA = m.merged;
  document.getElementById("impNote").textContent = imp.length ? `${m.added} imported trade(s) included (marked imported)` : "";
}
function wireTools() {
  document.getElementById("bPdf").onclick = () => { const old = document.title; document.title = "FOCUS_OSOK_Stats_" + stamp(); window.print(); setTimeout(() => document.title = old, 1000); };
  document.getElementById("bCsv").onclick = () => {
    const blob = new Blob(["\uFEFF" + toCsv(pick())], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "FOCUS_OSOK_Stats_Trades_" + stamp() + ".csv";
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  document.getElementById("bImp").onclick = () => document.getElementById("fImp").click();
  document.getElementById("fImp").onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      const r = fromCsv(String(rd.result));
      if (r.error) { alert("CSV import: " + r.error); return; }
      const m = mergeTrades(LOGDATA.concat(loadImported()), r.trades);
      const keep = loadImported().concat(r.trades.filter(t => !LOGDATA.concat(loadImported()).some(x => tradeKey(x) === tradeKey(t))));
      saveImported(keep); rebuildData(); drawFilters(); render();
      alert(`CSV import: ${m.added} trade(s) added, ${m.dup} already there, ${r.skipped} row(s) skipped (bad date / side / entry).`);
      e.target.value = "";
    };
    rd.readAsText(f);
  };
  document.getElementById("bClr").onclick = () => {
    const n = loadImported().length; if (!n) { alert("No imported trades in this browser."); return; }
    if (!confirm(`Remove the ${n} imported trade(s) from this browser? The log trades stay.`)) return;
    saveImported([]); rebuildData(); drawFilters(); render();
  };
}

function render() {
  const ts = pick(), s = stats(ts);
  const f = [F.time, F.strat, F.acct, F.news].map((v, i) => v === "All" ? ["all times", "all strategies", "paper + live", "all news"][i] : v);
  const dates = ts.map(t => t.date).sort();
  document.getElementById("subtitle").textContent = `Jachbit 2026 · ${BUILT} · ${s.n} trades · OSOK Stats · ${f.join(" · ")} · ${F.from || dates[0] || "-"} to ${F.to || dates[dates.length-1] || "-"}`;
  document.getElementById("kpis").innerHTML = kpis(s);
  document.getElementById("chart").innerHTML = chart(ts);
  document.getElementById("bySession").innerHTML = breakdown(ts, "session", "By OSOK Time", "OSOK Time");
  document.getElementById("byNews").innerHTML = breakdown(ts.filter(t => t.session === "8:30 News"), "news", "8:30 News by release", "Release");
  document.getElementById("byStrat").innerHTML = breakdown(ts, "strat", "By strategy", "Strategy");
  document.getElementById("bySide").innerHTML = breakdown(ts, "side", "By side", "Side");
  document.getElementById("byAcct").innerHTML = breakdown(ts, "paper", "Paper vs Live", "Account");
  document.getElementById("byAcctName").innerHTML = breakdown(ts, "acct", "By account", "Account");
  document.getElementById("byVer").innerHTML = breakdown(ts, "version", "By version", "Version");
  document.getElementById("rows").innerHTML = rows(ts);
  document.getElementById("caveats").innerHTML = caveats(ts, s);
}

// filters can also come from the link, e.g. OSOK_Stats.html#time=8:30 News&strat=No SL&acct=Live (handy as bookmarks)
try {
  decodeURIComponent(location.hash.slice(1)).split("&").forEach(p => { const [k, v] = p.split("="); if (k in F && v != null) F[k] = v; });
} catch (e) {}

rebuildData();
wireTools();
drawFilters();
render();
</script>
</body></html>"""


def aliases_for(trades):
    """real account name -> Paper n / Live n, kept in local\\account_aliases.json so it never changes"""
    try:
        with open(ALIAS_FILE, encoding="utf-8") as fh:
            al = json.load(fh)
    except Exception:
        al = {}
    for t in trades:
        if t["acct"] not in al:
            kind = "Paper" if t["paper"] else "Live"
            n = sum(1 for v in al.values() if v.startswith(kind + " ")) + 1
            al[t["acct"]] = "{} {}".format(kind, n)
    with open(ALIAS_FILE, "w", encoding="utf-8") as fh:
        json.dump(al, fh, indent=1)
    return al


def write_page(path, trades, built, copynote, copykey):
    page = (PAGE.replace("__DATA__", json.dumps(trades, default=str)).replace("__BUILT__", built)
                .replace("__COPYNOTE__", copynote).replace("__COPYKEY__", copykey))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)


def build():
    os.makedirs(os.path.dirname(LOCAL_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(DOCS_OUT), exist_ok=True)
    news = load_news()
    trades = build_trades(parse_logs(), news)
    built = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. local copy - real account names
    write_page(LOCAL_OUT, trades, built, "local copy (real account names)", "local")

    # 2. GitHub copy - account names masked
    al = aliases_for(trades)
    masked = [dict(t, acct=al[t["acct"]]) for t in trades]
    write_page(DOCS_OUT, masked, built, "", "public")
    with open(DOCS_JSON, "w", encoding="utf-8") as fh:
        json.dump(masked, fh, indent=1, default=str)

    # safety check: no real account name may appear in the GitHub copy
    leaked = []
    for p in (DOCS_OUT, DOCS_JSON):
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        leaked += [a for a in al if a in body]
    closed = [t for t in trades if t["result"] != "OPEN"]
    print("Local page :", LOCAL_OUT)
    print("GitHub page:", DOCS_OUT, "(masked)" if not leaked else "!!! REAL ACCOUNT NAMES FOUND: " + ", ".join(sorted(set(leaked))))
    print("Trades: {} ({} closed) | No SL {} | With SL {} | paper {} | live {}".format(
        len(trades), len(closed), sum(t["strat"] == "No SL" for t in trades), sum(t["strat"] == "With SL" for t in trades),
        sum(t["paper"] for t in trades), sum(not t["paper"] for t in trades)))
    for sess in ("8:30 News", "9:30 NY Open", "18:00 Globex"):
        g = [t for t in closed if t["session"] == sess]
        print("  {:13} {:2} trades  {:+.2f}".format(sess, len(g), sum(t["usd"] for t in g)))
    print("News tags:", ", ".join("{} {}".format(k, v) for k, v in sorted(news.items())) or "none")
    if leaked:
        raise SystemExit("Masking failed - do NOT upload docs\\ until this is fixed.")


if __name__ == "__main__":
    build()

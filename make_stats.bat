@echo off
title F.O.C.U.S. OSOK Statistics - build
rem Rebuilds the OSOK Stats page from NinjaTrader's own log files and opens your local copy.
rem   local\OSOK_Stats.html = your copy, real account names (never uploaded)
rem   docs\index.html       = the GitHub Pages copy, account names masked
rem Run after each session - No SL / With SL, paper and real-money trades are all picked up automatically.
rem News tags: edit news_events.txt (one line per release, e.g. 2026-12-10 CPI) before running.
cd /d "%~dp0"
python build_stats.py
if errorlevel 1 (
  echo   [ERROR] the stats page could not be built - see the message above
  pause & exit /b 1
)
start "" "%~dp0local\OSOK_Stats.html"

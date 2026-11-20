@echo off
title F.O.C.U.S. OSOK Statistics - backup
rem Timestamped copies of the project files into backups\ (run before every edit session).
cd /d "%~dp0"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
if not exist backups mkdir backups
copy "build_stats.py"    "backups\build_stats_%TS%.py" >nul && echo   [OK] build_stats.py
copy "make_stats.bat"    "backups\make_stats_%TS%.bat" >nul && echo   [OK] make_stats.bat
copy "news_events.txt"   "backups\news_events_%TS%.txt" >nul && echo   [OK] news_events.txt
copy "osok_times.txt"    "backups\osok_times_%TS%.txt" >nul && echo   [OK] osok_times.txt
copy "README.md"         "backups\README_%TS%.md" >nul && echo   [OK] README.md
copy ".gitignore"        "backups\gitignore_%TS%.txt" >nul && echo   [OK] .gitignore
if exist "local\accounts.txt" copy "local\accounts.txt" "backups\accounts_%TS%.txt" >nul && echo   [OK] local\accounts.txt
echo.
echo Backup done: backups\*_%TS%.*

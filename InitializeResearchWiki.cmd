@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\init_research_wiki.py
) else (
  python tools\init_research_wiki.py
)
echo.
pause

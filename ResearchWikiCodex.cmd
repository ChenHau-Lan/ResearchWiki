@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\research_wiki_codex_shortcut.py
) else (
  python tools\research_wiki_codex_shortcut.py
)
echo.
pause

@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is not installed. Install it from https://docs.astral.sh/uv/ and try again.
  pause
  exit /b 1
)

echo [1/2] Checking collection status ...
uv run --no-project --with pyyaml --with yt-dlp python automation\youtube\status.py
echo.
echo If the status above says BACKFILL, close this window and ask Claude to update YouTube.
choice /c YN /m "[2/2] Collect new videos now (normal run)"
if errorlevel 2 exit /b 0

uv run --no-project --with pyyaml --with yt-dlp python automation\youtube\youtube_watcher.py %*
echo.
echo Done. Collected files are raw only. Ask Claude to run /ingest to process them.
pause

@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."

echo [1/2] Building HTML study pages from wiki\ ...
python automation\publish\build_html.py
if errorlevel 1 (
  echo.
  echo Build failed. See messages above.
  pause
  exit /b 1
)

echo.
echo [2/2] Verifying HTML against Markdown ...
python automation\publish\verify_html.py

start "" "%CD%\exports\html\index.html"
echo.
echo Opened exports\html\index.html in the browser.
echo Check the summary line above for FAIL items.
pause

@echo off
cd /d "%~dp0"

python diagnose_update.py
if not errorlevel 9009 goto :eof

py -3 diagnose_update.py
if not errorlevel 9009 goto :eof

echo.
echo   Python not found. Please run from command line:
echo       python diagnose_update.py
echo.
pause

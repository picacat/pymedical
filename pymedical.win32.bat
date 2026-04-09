@echo off
:: 切換到腳本所在的目錄，確保相對路徑正確
cd /d "%~dp0"

:: 檢查 venv 是否存在
if exist "\pymedical\venv\Scripts\activate.bat" (
    call "\pymedical\venv\Scripts\activate.bat"
)

start /min py -3-32 pymedical.py


@echo off
:: 切換到腳本所在的目錄，確保相對路徑正確
cd /d "%~dp0"

:: 檢查 venv 是否存在
if not exist ".\venv\Scripts\activate.bat" (
    echo [錯誤] 找不到虛擬環境，請先執行安裝腳本。
    pause
    exit
)

:: 啟用環境並執行
call ".\venv\Scripts\activate.bat"
start /min py -3-32 pymedical.py


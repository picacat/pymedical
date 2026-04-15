@echo off

:: change current dir
cd /d "%~dp0"

:: verify venv exists
if exist "\pymedical\venv\Scripts\activate.bat" (
    call "\pymedical\venv\Scripts\activate.bat"
)

start /min pythonw pymedical.py
@echo off
setlocal

rem ========================================
rem Configuration Variables (Please verify these settings)
rem ========================================
rem 1. Source Database Data Directory (The specific database folder to copy)
set MARIADB_DATA_DIR="C:\MariaDB 11.7\data\pymedical"
rem 2. Backup Destination Root Directory
set BACKUP_DIR=D:\auto_backup
rem 3. MariaDB Windows Service Name (Check in Windows Services, usually "MariaDB" or "MySQL")
set MARIADB_SERVICE_NAME="MariaDB" 

rem ========================================
rem Step 1: Get YYYY-MM-DD_HHmm Date/Time and create directory
rem ========================================
rem Use PowerShell to reliably get YYYY-MM-DD_HHmm format (24-hour time)
for /f "usebackq delims=" %%i in (`powershell -Command "Get-Date -Format 'yyyy-MM-dd_HHmm'"`) do set TODAY_DATETIME=%%i

rem Create the backup directory (e.g., D:\auto_backup\2025-12-05_0930)
set TARGET_DIR=%BACKUP_DIR%\%TODAY_DATETIME%

echo ----------------------------------------
echo MariaDB Data Directory Backup Started on %DATE% %TIME%
echo Backup Source: %MARIADB_DATA_DIR%
echo Backup Target: %TARGET_DIR%
echo ----------------------------------------

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

rem ----------------------------------------
rem Step 2: Stop Service and Copy Data Directory (using robocopy)
rem ----------------------------------------
echo.
echo Stopping MariaDB Service (%MARIADB_SERVICE_NAME%)...
net stop %MARIADB_SERVICE_NAME%

rem Wait for the service to fully stop (10 seconds)
timeout /t 10 /nobreak > nul
if errorlevel 1 (
    echo ❌ WARNING: MariaDB service might not have stopped completely. Proceeding with copy...
) else (
    echo ✅ Service stopped successfully.
)

echo.
echo Copying data directory %MARIADB_DATA_DIR% to %TARGET_DIR%...
rem robocopy Flags: /E (Subfolders incl. empty ones), /V (Verbose output - shows files), /NP (No progress status)
robocopy %MARIADB_DATA_DIR% "%TARGET_DIR%" /E /V /NP /R:0 /W:0

if errorlevel 8 (
    rem robocopy returns 8 or higher on failure (1-7 are successful status codes)
    echo.
    echo ❌ An error occurred during the copy process! Please check the output above.
    echo.
) else (
    echo.
    echo ✅ Data directory backup completed successfully!
    echo.
)

rem ----------------------------------------
rem Step 3: Start Service
rem ----------------------------------------
echo.
echo Starting MariaDB Service (%MARIADB_SERVICE_NAME%)...
net start %MARIADB_SERVICE_NAME%
echo ✅ Service startup command issued.
echo.

rem ----------------------------------------
rem Step 4: Cleanup backups older than 30 days
rem ----------------------------------------

echo ----------------------------------------
echo Backup Cleanup Operation Started...
echo ----------------------------------------

rem Cleanup script checks for directories matching the YYYY-MM-DD_HHmm pattern
rem and deletes any directory whose creation time (LastWriteTime) is older than 30 days.
powershell.exe -Command "Get-ChildItem -Path '%BACKUP_DIR%' -Directory | Where-Object { $_.Name -match '\d{4}-\d{2}-\d{2}_\d{4}' } | ForEach-Object { if ($_.LastWriteTime -lt (Get-Date).AddDays(-30)) { Write-Host \"Deleting old backup: $($_.Name)\"; Remove-Item -Path $_.FullName -Recurse -Force } }"

echo ----------------------------------------
echo Backup Cleanup Operation Finished.
echo ----------------------------------------

endlocal
@echo off
setlocal enabledelayedexpansion

rem =====================================================================
rem  pymedical restore  (companion to backup_pymedical.bat)
rem
rem  Reads the .7z / .sql produced by backup_pymedical.bat and restores
rem  it over the live database.
rem
rem  Safety design - this script destroys data, so it:
rem    1. shows a numbered list and makes you pick, no guessing
rem    2. verifies the dump is complete BEFORE touching anything
rem    3. takes a pre-restore snapshot of the current database first,
rem       so a wrong restore is still undoable
rem    4. requires you to type the database name to confirm
rem    5. counts tables afterwards and compares against the dump
rem
rem  Comments are ASCII-only on purpose - see backup_pymedical.bat.
rem
rem  Usage:  restore_pymedical.bat                 (pick from a list)
rem          restore_pymedical.bat pymedical_2026-08-31_0400.7z
rem =====================================================================


rem ============================ CONFIG =================================

set "MARIADB_BIN=C:\MariaDB 11.7\bin"
set "DB_NAME=pymedical"

set "DB_USER=root"
set "DB_PASS=153fish"
set "AUTH=-u %DB_USER% -p%DB_PASS%"

set "BACKUP_DIR=D:\auto_backup"
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

rem Take a snapshot of the current database before overwriting it.
rem Strongly recommended. Set to 0 only if the database is already gone.
set "PRE_SNAPSHOT=1"

rem =====================================================================


set "MARIADB_EXE=%MARIADB_BIN%\mariadb.exe"
if not exist "%MARIADB_EXE%" set "MARIADB_EXE=%MARIADB_BIN%\mysql.exe"

set "DUMP_EXE=%MARIADB_BIN%\mariadb-dump.exe"
if not exist "%DUMP_EXE%" set "DUMP_EXE=%MARIADB_BIN%\mysqldump.exe"

set "TMPQ=%TEMP%\_pymedical_restore_q.txt"
set "EXTRACTED=0"

echo.
echo ======================================================
echo   pymedical RESTORE
echo ======================================================
echo.

if not exist "%MARIADB_EXE%" (
    echo [FAIL] mariadb.exe not found under %MARIADB_BIN%
    goto :ABORT
)


rem --------------------------------------------------------------
rem Step 1 - choose the backup
rem --------------------------------------------------------------
if not "%~1"=="" (
    set "PICKED=%~1"
    goto :HAVE_PICK
)

echo Available backups in %BACKUP_DIR%  -  newest first:
echo.
set "IDX=0"
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\%DB_NAME%_*.7z" "%BACKUP_DIR%\%DB_NAME%_*.sql" 2^>nul') do (
    set /a IDX+=1
    set "FILE_!IDX!=%%F"
    for %%S in ("%BACKUP_DIR%\%%F") do echo    !IDX!^)  %%F        %%~zS bytes
)

if %IDX%==0 (
    echo [FAIL] No backup files found in %BACKUP_DIR%
    goto :ABORT
)

echo.
set "CHOICE="
set /p "CHOICE=Which one? Enter a number, or blank to abort: "
if "%CHOICE%"=="" goto :ABORT

call set "PICKED=%%FILE_%CHOICE%%%"
if "%PICKED%"=="" (
    echo [FAIL] "%CHOICE%" is not one of the listed numbers.
    goto :ABORT
)

:HAVE_PICK
set "SRC=%BACKUP_DIR%\%PICKED%"
if not exist "%SRC%" set "SRC=%PICKED%"
if not exist "%SRC%" (
    echo [FAIL] File not found: %PICKED%
    goto :ABORT
)
echo.
echo Selected: %SRC%


rem --------------------------------------------------------------
rem Step 2 - extract if it is an archive
rem --------------------------------------------------------------
set "SQL_FILE=%SRC%"

if /i "%SRC:~-3%"==".7z" (
    if not exist "%SEVENZIP%" (
        echo [FAIL] 7z.exe not found at %SEVENZIP% - cannot open the archive.
        goto :ABORT
    )

    echo.
    echo Testing archive integrity...
    "%SEVENZIP%" t "%SRC%" -bsp0
    if errorlevel 1 (
        echo [FAIL] Archive is corrupt. Do NOT use it. Try an older backup.
        goto :ABORT
    )
    echo [OK] Archive is intact.

    echo Extracting...
    "%SEVENZIP%" x "%SRC%" -o"%BACKUP_DIR%" -y -bsp0
    if errorlevel 1 (
        echo [FAIL] Extraction failed - check free disk space on %BACKUP_DIR:~0,2%
        goto :ABORT
    )

    set "SQL_FILE=%BACKUP_DIR%\%PICKED:~0,-3%.sql"
    set "EXTRACTED=1"
)

if not exist "%SQL_FILE%" (
    echo [FAIL] Expected SQL file not found: %SQL_FILE%
    goto :ABORT
)


rem --------------------------------------------------------------
rem Step 3 - verify the dump BEFORE destroying anything
rem --------------------------------------------------------------
echo.
echo Verifying dump...
powershell -NoProfile -Command "if ((Get-Content -LiteralPath '%SQL_FILE%' -Tail 3 -ErrorAction Stop) -match 'Dump completed') { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [FAIL] This dump is truncated - no 'Dump completed' trailer.
    echo        Nothing has been changed. Pick an older backup.
    goto :ABORT
)

rem How many tables should end up in the database
for /f %%C in ('findstr /b /c:"CREATE TABLE" "%SQL_FILE%" ^| find /c /v ""') do set "EXPECT_TABLES=%%C"
for %%S in ("%SQL_FILE%") do set "SQL_SIZE=%%~zS"
echo [OK] Dump is complete: %SQL_SIZE% bytes, %EXPECT_TABLES% tables.


rem --------------------------------------------------------------
rem Step 4 - show what is about to be destroyed
rem --------------------------------------------------------------
"%MARIADB_EXE%" %AUTH% -N -B -e "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='%DB_NAME%'" > "%TMPQ%" 2>nul
if errorlevel 1 (
    echo [FAIL] Cannot connect to the server. Check the service and credentials.
    goto :ABORT
)
set /p DB_EXISTS=<"%TMPQ%"

set "CUR_TABLES=0"
if "%DB_EXISTS%"=="1" (
    "%MARIADB_EXE%" %AUTH% -N -B -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_TYPE='BASE TABLE'" > "%TMPQ%"
    set /p CUR_TABLES=<"%TMPQ%"
)

echo.
echo ------------------------------------------------------
echo  ABOUT TO OVERWRITE THE LIVE DATABASE
echo ------------------------------------------------------
echo   Target database : %DB_NAME%
if "%DB_EXISTS%"=="1" (
    echo   Currently holds : %CUR_TABLES% tables  -  THESE WILL BE DROPPED
) else (
    echo   Currently       : does not exist, will be created
)
echo   Restoring from  : %PICKED%
echo   Will contain    : %EXPECT_TABLES% tables
echo ------------------------------------------------------
echo.
echo Make sure every pymedical client on the network is closed first.
echo.

set "CONFIRM="
set /p "CONFIRM=Type the database name to confirm, anything else aborts: "
if not "%CONFIRM%"=="%DB_NAME%" (
    echo Aborted - nothing was changed.
    goto :ABORT
)


rem --------------------------------------------------------------
rem Step 5 - pre-restore snapshot, so this is undoable
rem --------------------------------------------------------------
set "SNAPSHOT="
if "%PRE_SNAPSHOT%"=="1" if "%DB_EXISTS%"=="1" (
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HHmmss'"`) do set "SNAPSTAMP=%%i"
    set "SNAPSHOT=%BACKUP_DIR%\prerestore_%DB_NAME%_!SNAPSTAMP!.sql"
    echo.
    echo Taking a pre-restore snapshot of the CURRENT database...
    "%DUMP_EXE%" %AUTH% --single-transaction --quick --default-character-set=binary --hex-blob --routines --events --triggers --max-allowed-packet=1G --databases %DB_NAME% --result-file="!SNAPSHOT!"
    if errorlevel 1 (
        echo.
        echo [FAIL] The pre-restore snapshot failed.
        echo        Refusing to continue - restoring now would be irreversible.
        echo        Set PRE_SNAPSHOT=0 at the top of this file to override.
        goto :ABORT
    )
    echo [OK] Snapshot saved: !SNAPSHOT!
)


rem --------------------------------------------------------------
rem Step 6 - drop and restore
rem Dropping first is deliberate: a plain import leaves behind any
rem table that is no longer in the dump, which is how orphan tables
rem accumulate and later throw error 1932.
rem
rem unique_checks / foreign_key_checks off speeds the import up a lot
rem and is safe here - the data already passed those checks once.
rem --------------------------------------------------------------
echo.
echo Started at %TIME%
echo Dropping %DB_NAME%...
"%MARIADB_EXE%" %AUTH% -e "DROP DATABASE IF EXISTS \`%DB_NAME%\`"
if errorlevel 1 (
    echo [FAIL] Could not drop the database. Something is still connected to it.
    goto :ABORT
)

echo Importing - this takes a few minutes, do not close this window...
"%MARIADB_EXE%" %AUTH% ^
  --default-character-set=binary ^
  --max-allowed-packet=1G ^
  --init-command="SET unique_checks=0, foreign_key_checks=0" ^
  < "%SQL_FILE%"

if errorlevel 1 (
    echo.
    echo [FAIL] The import reported an error. The database is INCOMPLETE.
    if defined SNAPSHOT echo        Roll back with: %MARIADB_EXE% -u %DB_USER% -p --default-character-set=binary ^< "%SNAPSHOT%"
    goto :ABORT
)
echo Finished at %TIME%


rem --------------------------------------------------------------
rem Step 7 - verify the result
rem --------------------------------------------------------------
echo.
echo Verifying...
"%MARIADB_EXE%" %AUTH% -N -B -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_TYPE='BASE TABLE'" > "%TMPQ%"
set /p NEW_TABLES=<"%TMPQ%"

echo   Tables in the dump     : %EXPECT_TABLES%
echo   Tables in the database : %NEW_TABLES%

if not "%NEW_TABLES%"=="%EXPECT_TABLES%" (
    echo.
    echo [WARN] Table counts do not match. Check the messages above before
    echo        letting anyone back into the system.
) else (
    echo.
    echo [OK] RESTORE COMPLETE.
)

if defined SNAPSHOT (
    echo.
    echo Pre-restore snapshot kept at:
    echo   %SNAPSHOT%
    echo Delete it once you are satisfied the restore is good.
)

if "%EXTRACTED%"=="1" (
    del /q "%SQL_FILE%" 2>nul
)
if exist "%TMPQ%" del /q "%TMPQ%"

echo.
pause
endlocal
exit /b 0


:ABORT
if "%EXTRACTED%"=="1" if exist "%SQL_FILE%" del /q "%SQL_FILE%" 2>nul
if exist "%TMPQ%" del /q "%TMPQ%"
echo.
pause
endlocal
exit /b 1

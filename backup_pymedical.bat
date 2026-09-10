@echo off
setlocal EnableDelayedExpansion

rem ============================================================
rem  pymedical universal logical backup
rem  - Reads DB settings from pymedical.conf in the same folder
rem  - Works with InnoDB / MyISAM / mixed engines
rem  - No service stop required
rem  Exit codes: 0 = success, 1 = failure (visible to Task Scheduler)
rem ============================================================

set "SCRIPT_DIR=%~dp0"
set "CONF_FILE=%SCRIPT_DIR%pymedical.conf"

rem ---------- Local settings (not stored in pymedical.conf) ----------
set "BACKUP_DIR=D:\auto_backup"
rem Optional second destination (NAS / USB drive). Leave empty to skip.
set "SECOND_DIR="
set "KEEP_DAYS=7"
rem Set to 1 to put station_no into the file name, so several PCs can back up
rem into one shared folder without overwriting each other.
set "INCLUDE_STATION=0"
rem Leave empty to auto-detect the MariaDB / MySQL client tools.
set "MARIADB_BIN="
rem ------------------------------------------------------------------

rem ---------- Defaults, overridden by pymedical.conf ----------
set "DB_HOST=localhost"
set "DB_PORT=3306"
set "DB_USER=root"
set "DB_PASS="
set "DB_NAME=pymedical"
set "DB_CHARSET="
set "STATION_NO="

echo ============================================================
echo  pymedical backup started %DATE% %TIME%
echo ============================================================

rem ---------- Step 1: read pymedical.conf ----------
if not exist "%CONF_FILE%" (
    echo [ERROR] Config file not found: "%CONF_FILE%"
    exit /b 1
)

set "SECTION="
for /f "usebackq delims=" %%A in ("%CONF_FILE%") do (
    set "LINE=%%A"
    rem strip leading blanks
    for /f "tokens=* delims= " %%T in ("!LINE!") do set "LINE=%%T"

    if not "!LINE!"=="" (
        if not "!LINE!"=="!LINE:[=!" (
            rem section header - matched by content so a UTF-8 BOM cannot break it
            set "SECTION=other"
            if not "!LINE!"=="!LINE:db]=!" set "SECTION=db"
            if not "!LINE!"=="!LINE:settings]=!" set "SECTION=settings"
        ) else (
            set "FIRST=!LINE:~0,1!"
            if not "!FIRST!"==";" if not "!FIRST!"=="#" (
                for /f "tokens=1,* delims==" %%K in ("!LINE!") do (
                    set "CK=%%K"
                    set "CV=%%L"
                    rem keys are single words - just drop every blank
                    set "CK=!CK: =!"
                    rem trim blanks around the value
                    for /f "tokens=* delims= " %%V in ("!CV!") do set "CV=%%V"
                    if "!CV:~-1!"==" " set "CV=!CV:~0,-1!"
                    if "!CV:~-1!"==" " set "CV=!CV:~0,-1!"
                    if "!CV:~-1!"==" " set "CV=!CV:~0,-1!"

                    if "!SECTION!"=="db" (
                        if /i "!CK!"=="host"     set "DB_HOST=!CV!"
                        if /i "!CK!"=="port"     set "DB_PORT=!CV!"
                        if /i "!CK!"=="user"     set "DB_USER=!CV!"
                        if /i "!CK!"=="password" set "DB_PASS=!CV!"
                        if /i "!CK!"=="database" set "DB_NAME=!CV!"
                        if /i "!CK!"=="charset"  set "DB_CHARSET=!CV!"
                    )
                    if "!SECTION!"=="settings" (
                        if /i "!CK!"=="station_no" set "STATION_NO=!CV!"
                    )
                )
            )
        )
    )
)

if not defined DB_NAME (
    echo [ERROR] No "database" entry found in the [db] section.
    exit /b 1
)

rem Pass the password via env var so it never shows up in the process list
set "MYSQL_PWD=%DB_PASS%"
set "CONN=-h%DB_HOST% -P%DB_PORT% -u%DB_USER%"

echo   config      : %CONF_FILE%
echo   database    : %DB_NAME% on %DB_HOST%:%DB_PORT% as %DB_USER%
if defined STATION_NO echo   station_no  : %STATION_NO%

rem ---------- Step 2: locate the tools ----------
rem MariaDB 11.x ships mariadb-dump.exe; older MariaDB / MySQL ship mysqldump.exe
set "DUMP="
set "CLIENT="

if defined MARIADB_BIN (
    if exist "%MARIADB_BIN%\mariadb-dump.exe" set "DUMP=%MARIADB_BIN%\mariadb-dump.exe"
    if not defined DUMP if exist "%MARIADB_BIN%\mysqldump.exe" set "DUMP=%MARIADB_BIN%\mysqldump.exe"
    if exist "%MARIADB_BIN%\mariadb.exe" set "CLIENT=%MARIADB_BIN%\mariadb.exe"
    if not defined CLIENT if exist "%MARIADB_BIN%\mysql.exe" set "CLIENT=%MARIADB_BIN%\mysql.exe"
)

rem look on PATH
for %%P in (mariadb-dump.exe mysqldump.exe) do (
    if not defined DUMP for /f "usebackq delims=" %%F in (`where %%P 2^>nul`) do (
        if not defined DUMP set "DUMP=%%F"
    )
)
for %%P in (mariadb.exe mysql.exe) do (
    if not defined CLIENT for /f "usebackq delims=" %%F in (`where %%P 2^>nul`) do (
        if not defined CLIENT set "CLIENT=%%F"
    )
)

rem look in the usual install locations
for /d %%D in ("C:\MariaDB *" "C:\Program Files\MariaDB *" "C:\Program Files\MySQL\*") do (
    if not defined DUMP if exist "%%~D\bin\mariadb-dump.exe" set "DUMP=%%~D\bin\mariadb-dump.exe"
    if not defined DUMP if exist "%%~D\bin\mysqldump.exe" set "DUMP=%%~D\bin\mysqldump.exe"
    if not defined CLIENT if exist "%%~D\bin\mariadb.exe" set "CLIENT=%%~D\bin\mariadb.exe"
    if not defined CLIENT if exist "%%~D\bin\mysql.exe" set "CLIENT=%%~D\bin\mysql.exe"
)

if not defined DUMP (
    echo [ERROR] mariadb-dump.exe / mysqldump.exe not found.
    echo         Set MARIADB_BIN at the top of this script.
    exit /b 1
)
if not defined CLIENT (
    echo [ERROR] mariadb.exe / mysql.exe not found.
    echo         Set MARIADB_BIN at the top of this script.
    exit /b 1
)

rem 7-Zip: prefer the copy shipped with pymedical
set "SEVENZIP="
if exist "%SCRIPT_DIR%7z.exe" set "SEVENZIP=%SCRIPT_DIR%7z.exe"
if not defined SEVENZIP if exist "C:\Program Files\7-Zip\7z.exe" set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

echo   dump tool   : %DUMP%
echo   client tool : %CLIENT%
if defined SEVENZIP echo   7-Zip       : %SEVENZIP%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%BACKUP_DIR%" (
    echo [ERROR] Cannot create backup directory "%BACKUP_DIR%"
    exit /b 1
)

rem ---------- Step 3: connection test ----------
"%CLIENT%" %CONN% -N -B -e "SELECT 1" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Cannot connect to the server. Check pymedical.conf [db] settings.
    exit /b 1
)

rem ---------- Step 4: detect storage engines ----------
rem Query results go to a temp file to avoid batch quoting problems.
set "TMPQ=%TEMP%\pmb_query_%RANDOM%.txt"

> "%TMPQ%" "%CLIENT%" %CONN% -N -B -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_TYPE='BASE TABLE'"
set "TBL_TOTAL="
set /p TBL_TOTAL=<"%TMPQ%"

> "%TMPQ%" "%CLIENT%" %CONN% -N -B -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_TYPE='BASE TABLE' AND ENGINE<>'InnoDB'"
set "TBL_NONTRX="
set /p TBL_NONTRX=<"%TMPQ%"

del /q "%TMPQ%" 2>nul

if not defined TBL_TOTAL set "TBL_TOTAL=0"
if not defined TBL_NONTRX set "TBL_NONTRX=0"

if "%TBL_TOTAL%"=="0" (
    echo [ERROR] Database "%DB_NAME%" has no base tables - wrong database name?
    exit /b 1
)

rem InnoDB only  -> --single-transaction : consistent snapshot, nothing is locked
rem MyISAM/mixed -> --lock-all-tables    : FLUSH TABLES WITH READ LOCK, writes are
rem                                        blocked for the duration of the dump
if "%TBL_NONTRX%"=="0" (
    set "LOCK_OPT=--single-transaction --quick"
    set "ENGINE_MODE=InnoDB only - online backup, no locking"
) else (
    set "LOCK_OPT=--lock-all-tables --quick"
    set "ENGINE_MODE=MyISAM or mixed - global read lock held during dump"
)

echo   tables      : %TBL_TOTAL% total, %TBL_NONTRX% non-InnoDB
echo   mode        : %ENGINE_MODE%

rem ---------- Step 5: build target file names ----------
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd'"`) do set "STAMP=%%i"
if not defined STAMP (
    echo [ERROR] Failed to obtain the current date.
    exit /b 1
)

set "BASE=%DB_NAME%_%STAMP%"
if "%INCLUDE_STATION%"=="1" if defined STATION_NO set "BASE=%DB_NAME%_st%STATION_NO%_%STAMP%"

set "SQL_FILE=%BACKUP_DIR%\%BASE%.sql"
set "ARCHIVE=%BACKUP_DIR%\%BASE%.7z"
set "LOG_FILE=%BACKUP_DIR%\%BASE%.log"

rem Re-running on the same day replaces that day's backup instead of piling up
if exist "%SQL_FILE%" del /q "%SQL_FILE%"
if exist "%ARCHIVE%" del /q "%ARCHIVE%"

rem ---------- Step 6: dump ----------
rem charset in pymedical.conf (%DB_CHARSET%) is deliberately NOT used here:
rem --default-character-set=binary dumps the bytes as stored, so mixed
rem big5 / utf8mb3 / utf8mb4 columns survive the round trip untouched.
set "DUMP_EXTRA=--routines --events --triggers"

echo.
echo Dumping to %SQL_FILE% ...
call :run_dump
if errorlevel 1 (
    rem MySQL 5.0 and a few older builds do not support --events
    echo [WARN] Dump failed. Retrying without --events ...
    set "DUMP_EXTRA=--routines --triggers"
    if exist "%SQL_FILE%" del /q "%SQL_FILE%"
    call :run_dump
    if errorlevel 1 (
        echo [ERROR] Dump failed. Nothing usable was produced.
        if exist "%SQL_FILE%" del /q "%SQL_FILE%"
        exit /b 1
    )
)

rem ---------- Step 7: verify the dump ----------
if not exist "%SQL_FILE%" (
    echo [ERROR] Dump file was not created.
    exit /b 1
)

rem The dump tool's exit code is not enough - the trailing marker is the real proof
powershell -NoProfile -Command "$t = Get-Content -LiteralPath '%SQL_FILE%' -Tail 5 -ErrorAction Stop; if ($t -match '-- Dump completed') { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [ERROR] '-- Dump completed' marker not found - the dump is truncated.
    echo [ERROR] Keeping %SQL_FILE% for inspection.
    exit /b 1
)

for %%f in ("%SQL_FILE%") do set "SQL_SIZE=%%~zf"
echo   dump OK, %SQL_SIZE% bytes

rem ---------- Step 8: compress ----------
set "FINAL_FILE=%SQL_FILE%"
if defined SEVENZIP (
    echo.
    echo Compressing ...
    "%SEVENZIP%" a -mx=5 -mmt=on "%ARCHIVE%" "%SQL_FILE%" >nul
    if errorlevel 1 (
        echo [WARN] Compression failed - keeping the plain .sql file.
    ) else (
        "%SEVENZIP%" t "%ARCHIVE%" >nul
        if errorlevel 1 (
            echo [WARN] Archive test failed - keeping the plain .sql file.
            del /q "%ARCHIVE%" 2>nul
        ) else (
            del /q "%SQL_FILE%"
            set "FINAL_FILE=%ARCHIVE%"
            echo   archive OK and tested
        )
    )
) else (
    echo [WARN] 7z.exe not found - keeping the plain .sql file.
)

rem ---------- Step 9: write a small log ----------
(
    echo backup_date : %DATE% %TIME%
    echo database    : %DB_NAME% @ %DB_HOST%:%DB_PORT%
    echo station_no  : %STATION_NO%
    echo engine_mode : %ENGINE_MODE%
    echo tables      : %TBL_TOTAL% total, %TBL_NONTRX% non-InnoDB
    echo dump_bytes  : %SQL_SIZE%
    echo dump_options: %LOCK_OPT% %DUMP_EXTRA%
    echo result_file : %FINAL_FILE%
) > "%LOG_FILE%"

rem ---------- Step 10: copy to the second destination ----------
if defined SECOND_DIR (
    echo.
    echo Copying to %SECOND_DIR% ...
    if not exist "%SECOND_DIR%" mkdir "%SECOND_DIR%" 2>nul
    copy /y "%FINAL_FILE%" "%SECOND_DIR%\" >nul
    if errorlevel 1 (
        echo [WARN] Copy to the second destination failed.
    ) else (
        copy /y "%LOG_FILE%" "%SECOND_DIR%\" >nul
        echo   offsite copy OK
    )
)

rem ---------- Step 11: retention ----------
echo.
echo Removing backups older than %KEEP_DAYS% days ...
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%BACKUP_DIR%' -File | Where-Object { $_.Name -like '%DB_NAME%_*' -and $_.LastWriteTime -lt (Get-Date).AddDays(-%KEEP_DAYS%) } | ForEach-Object { Write-Host ('  deleting ' + $_.Name); Remove-Item -LiteralPath $_.FullName -Force }"
if defined SECOND_DIR (
    powershell -NoProfile -Command "if (Test-Path -LiteralPath '%SECOND_DIR%') { Get-ChildItem -LiteralPath '%SECOND_DIR%' -File | Where-Object { $_.Name -like '%DB_NAME%_*' -and $_.LastWriteTime -lt (Get-Date).AddDays(-%KEEP_DAYS%) } | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force } }"
)

echo.
echo ============================================================
echo  Backup finished OK: %FINAL_FILE%
echo ============================================================
endlocal
exit /b 0

rem ============================================================
rem  Subroutine: run the dump
rem ============================================================
:run_dump
"%DUMP%" %CONN% %LOCK_OPT% ^
    --default-character-set=binary --hex-blob ^
    %DUMP_EXTRA% ^
    --extended-insert ^
    --databases %DB_NAME% ^
    --result-file="%SQL_FILE%"
exit /b %errorlevel%

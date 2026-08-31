@echo off
setlocal enabledelayedexpansion

rem =====================================================================
rem  pymedical logical backup  (mariadb-dump + 7-Zip)
rem  Safe for InnoDB: --single-transaction takes a consistent snapshot
rem  WITHOUT stopping the service and WITHOUT locking the tables.
rem
rem  Comments are ASCII-only on purpose: this file runs unattended under
rem  Task Scheduler on a cp950 console, where non-ASCII bytes in a .bat
rem  can break parsing.
rem
rem  HOW TO RESTORE (the --default-character-set=binary part is NOT
rem  optional - without it the big5 / utf8mb3 columns come back mangled):
rem     7z x pymedical_2026-08-31_0400.7z
rem     "C:\MariaDB 11.7\bin\mariadb.exe" -u root -p --default-character-set=binary < pymedical_2026-08-31_0400.sql
rem  ...or feed the .sql to restore_sql.py, which handles this already.
rem =====================================================================


rem ============================ CONFIG =================================

rem MariaDB bin directory
set "MARIADB_BIN=C:\MariaDB 11.7\bin"

rem Database to back up
set "DB_NAME=pymedical"

rem Credentials.
rem NOTE: with the password on the command line it is visible in the
rem process list while the dump runs. If you ever want it out of this
rem file, create a separate .cnf readable only by Administrator:
rem     [mysqldump]
rem     user=root
rem     password=xxxxxxxx
rem and swap the AUTH line below for:
rem     set "AUTH=--defaults-extra-file=C:\MariaDB 11.7\backup.cnf"
set "DB_USER=root"
set "DB_PASS=CHANGE_ME"
set "AUTH=-u %DB_USER% -p%DB_PASS%"
rem If the password contains  ^ & | < > ( )  escape each with a caret,
rem e.g.  abc^&def   . A  %  must be doubled:  abc%%def

rem Backup destination
set "BACKUP_DIR=D:\auto_backup"

rem Keep this many days
set "KEEP_DAYS=7"

rem 7-Zip executable
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

rem Optional off-site / second copy of the .7z. Leave empty to disable.
rem set "OFFSITE_DIR=\\NAS\backup\pymedical"
set "OFFSITE_DIR="

rem =====================================================================


set "LOG_FILE=%BACKUP_DIR%\backup.log"
set "FAILED=0"

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HHmm'"`) do set "STAMP=%%i"

set "SQL_FILE=%BACKUP_DIR%\%DB_NAME%_%STAMP%.sql"
set "ARCHIVE=%BACKUP_DIR%\%DB_NAME%_%STAMP%.7z"

call :LOG "======================================================"
call :LOG "Backup started: %DB_NAME%  ->  %ARCHIVE%"


rem --------------------------------------------------------------
rem Step 1 - locate mariadb-dump
rem --------------------------------------------------------------
set "DUMP_EXE=%MARIADB_BIN%\mariadb-dump.exe"
if not exist "%DUMP_EXE%" set "DUMP_EXE=%MARIADB_BIN%\mysqldump.exe"
if not exist "%DUMP_EXE%" (
    call :LOG "[FAIL] mariadb-dump.exe / mysqldump.exe not found under %MARIADB_BIN%"
    set "FAILED=1"
    goto :FINISH
)
call :LOG "Using dump tool: %DUMP_EXE%"


rem --------------------------------------------------------------
rem Step 2 - dump
rem   --single-transaction  consistent snapshot, no locking. InnoDB only.
rem   --quick               stream rows, do not buffer a whole table
rem   --default-character-set=binary + --hex-blob
rem                         pass bytes through untouched. Required here
rem                         because this schema still mixes big5,
rem                         utf8mb3 and utf8mb4 columns.
rem   --result-file         write directly, NOT via  >  redirection,
rem                         which would insert CRLF and corrupt data.
rem --------------------------------------------------------------
call :LOG "Dumping..."

"%DUMP_EXE%" %AUTH% ^
  --single-transaction ^
  --quick ^
  --default-character-set=binary ^
  --hex-blob ^
  --routines ^
  --events ^
  --triggers ^
  --extended-insert ^
  --max-allowed-packet=1G ^
  --databases %DB_NAME% ^
  --result-file="%SQL_FILE%"

if errorlevel 1 (
    call :LOG "[FAIL] mariadb-dump returned an error. See above."
    set "FAILED=1"
    goto :FINISH
)


rem --------------------------------------------------------------
rem Step 3 - verify the dump is complete
rem A truncated dump is the classic silent disaster: the file exists,
rem looks plausible, and is missing half the tables. mariadb-dump writes
rem "-- Dump completed" as its very last line only on success.
rem --------------------------------------------------------------
if not exist "%SQL_FILE%" (
    call :LOG "[FAIL] Dump file was not created."
    set "FAILED=1"
    goto :FINISH
)

for %%A in ("%SQL_FILE%") do set "SQL_SIZE=%%~zA"
if %SQL_SIZE% LSS 10240 (
    call :LOG "[FAIL] Dump file is only %SQL_SIZE% bytes - almost certainly broken."
    set "FAILED=1"
    goto :FINISH
)

powershell -NoProfile -Command "if ((Get-Content -LiteralPath '%SQL_FILE%' -Tail 3 -ErrorAction Stop) -match 'Dump completed') { exit 0 } else { exit 1 }"
if errorlevel 1 (
    call :LOG "[FAIL] Dump file has no 'Dump completed' trailer - it is truncated."
    set "FAILED=1"
    goto :FINISH
)

call :LOG "[OK] Dump verified, %SQL_SIZE% bytes."


rem --------------------------------------------------------------
rem Step 4 - compress, then TEST the archive
rem A single corrupt archive is a total loss, so never delete the .sql
rem before  7z t  has confirmed the archive reads back.
rem   -mx=5  good ratio/time balance. -mx=9 roughly doubles the time
rem          for a few percent on SQL text.
rem   -mmt=on  use all cores.
rem --------------------------------------------------------------
if not exist "%SEVENZIP%" (
    call :LOG "[WARN] 7z.exe not found at %SEVENZIP% - keeping the uncompressed .sql"
    goto :CLEANUP
)

call :LOG "Compressing..."
"%SEVENZIP%" a -t7z -mx=5 -mmt=on -bsp0 "%ARCHIVE%" "%SQL_FILE%"
if errorlevel 1 (
    call :LOG "[FAIL] 7z compression failed - keeping the uncompressed .sql"
    set "FAILED=1"
    goto :CLEANUP
)

call :LOG "Testing archive..."
"%SEVENZIP%" t "%ARCHIVE%" -bsp0
if errorlevel 1 (
    call :LOG "[FAIL] Archive failed its integrity test - keeping the uncompressed .sql"
    set "FAILED=1"
    goto :CLEANUP
)

for %%A in ("%ARCHIVE%") do set "ARC_SIZE=%%~zA"
call :LOG "[OK] Archive verified, %ARC_SIZE% bytes."

rem Archive is proven readable - now the .sql can go.
del /q "%SQL_FILE%"
rem To keep the plain .sql as well, comment out the del line above.


rem --------------------------------------------------------------
rem Step 4b - optional second copy
rem --------------------------------------------------------------
if defined OFFSITE_DIR (
    call :LOG "Copying to off-site: %OFFSITE_DIR%"
    if not exist "%OFFSITE_DIR%" mkdir "%OFFSITE_DIR%"
    copy /y "%ARCHIVE%" "%OFFSITE_DIR%\" >nul
    if errorlevel 1 (
        call :LOG "[WARN] Off-site copy failed. Local backup is still good."
    ) else (
        call :LOG "[OK] Off-site copy done."
    )
)


rem --------------------------------------------------------------
rem Step 5 - retention
rem --------------------------------------------------------------
:CLEANUP
call :LOG "Removing backups older than %KEEP_DAYS% days..."
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%BACKUP_DIR%' -File -Include '%DB_NAME%_*.7z','%DB_NAME%_*.sql' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-%KEEP_DAYS%) } | ForEach-Object { Write-Host ('  deleting ' + $_.Name); Remove-Item -LiteralPath $_.FullName -Force }"

rem Keep the log from growing without limit
powershell -NoProfile -Command "$f='%LOG_FILE%'; if ((Test-Path $f) -and ((Get-Item $f).Length -gt 5MB)) { $c = Get-Content $f -Tail 2000; Set-Content $f $c }"


:FINISH
if "%FAILED%"=="1" (
    call :LOG "[FAIL] BACKUP FAILED - see messages above."
    call :LOG "======================================================"
    endlocal
    exit /b 1
)
call :LOG "[OK] Backup finished successfully."
call :LOG "======================================================"
endlocal
exit /b 0


rem --------------------------------------------------------------
:LOG
echo %~1
echo [%date% %time%] %~1>>"%LOG_FILE%"
goto :eof

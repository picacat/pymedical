@echo off
title 設定 pymedical 共享
echo =================================================
echo 設定共享資料夾 pymedical，允許區網內電腦無密碼存取
echo =================================================
echo.

:: 設定共享的資料夾路徑與名稱
::set "FolderPath=C:\MariaDB 10.6\data\pymedical"
::set "ShareName=pymedical"

set "FolderPath=C:\MariaDB 10.6\data\nd"
set "ShareName=nd"

:: 檢查是否以系統管理員身份執行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [錯誤] 請以系統管理員身份執行此批次檔！
    pause
    exit
)

:: 共享 pymedical 資料夾（若已存在則覆蓋）
net share %ShareName%="%FolderPath%" /GRANT:Everyone,FULL /CACHE:None
if %errorLevel% neq 0 (
    echo [錯誤] 無法共享資料夾，請檢查權限！
    pause
    exit
)
echo [成功] 資料夾 "%FolderPath%" 已共享為 "%ShareName%"。

:: 啟用網路探索
netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes
echo [成功] 已啟用網路探索。

:: 啟用檔案和印表機共用
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes
echo [成功] 已啟用檔案與印表機共用。

:: 設定防火牆允許 SMB (TCP 445) 傳輸
netsh advfirewall firewall add rule name="SMB Sharing" dir=in action=allow protocol=TCP localport=445
echo [成功] 已開放 SMB 連接埠 (TCP 445)。

:: 關閉密碼保護共用
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v restrictanonymous /t REG_DWORD /d 0 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" /v restrictnullsessaccess /t REG_DWORD /d 0 /f
echo [成功] 已關閉密碼保護共用。

:: 重新啟動伺服器服務，使設定生效
net stop LanmanServer /y >nul 2>&1
net start LanmanServer >nul 2>&1
echo [成功] 重新啟動 LanmanServer 服務。

echo.
echo [完成] 共享資料夾 "%FolderPath%" 可在區網內透過 \\%COMPUTERNAME%\%ShareName% 存取！
echo.
pause
exit


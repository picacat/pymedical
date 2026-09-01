# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
# 開啟網址
import os
import subprocess
import sys
import time
import webbrowser
from typing import Optional

if sys.platform == "win32":
    import winreg


def get_default_browser():
    """
    僅在 Windows 上讀取登錄檔取得預設瀏覽器名稱。
    非 Windows 平台或讀取失敗，回傳 None。
    """
    if sys.platform != "win32":
        return None
    try:
        reg_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            return prog_id
    except Exception as e:
        print(f"【警告】無法讀取預設瀏覽器設定：{e}")
        return None


def open_with_clean_cache(exe_path: str, address: str, profile_key: str):
    temp_profile = os.path.join(
        os.environ.get("TEMP", "."), f"nhi_medcloud_temp_profile_{profile_key}"
    )
    # 不再每次刪除，只在資料夾不存在時才是全新
    os.makedirs(temp_profile, exist_ok=True)

    subprocess.Popen(
        [
            exe_path,
            "--new-window",
            f"--user-data-dir={temp_profile}",
            "--no-first-run",  # 跳過首次啟動流程
            "--no-default-browser-check",  # 不跳出「設為預設瀏覽器」提示
            "--disable-features=msEdgeWelcomePage,EdgeWelcomeExperience",  # 關閉 Edge 歡迎頁
            address,
        ]
    )


def find_browser_exe(kind: str) -> Optional[str]:
    exe_name = {"chrome": "chrome.exe", "edge": "msedge.exe"}.get(kind)
    if not exe_name:
        return None
    sub = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, sub) as key:
                path, _ = winreg.QueryValueEx(key, "")
                path = path.strip('"')
                if os.path.isfile(path):
                    return path
        except OSError:
            continue
    return None


def open_nhi_medcloud(use_virtual_card: bool = False):
    card_type = "vhc" if use_virtual_card else "icc"
    card_name = "虛擬卡" if use_virtual_card else "實體卡"
    address = f"https://medcloud2.nhi.gov.tw/imu/imue1000?type={card_type}&_t={int(time.time())}"

    if sys.platform == "win32":
        for kind in ("chrome", "edge"):
            exe = find_browser_exe(kind)
            if exe:
                open_with_clean_cache(exe, address, kind)
                print(f"已用 {kind} 強制清空快取並開啟 ({card_name})。")
                return
        print("【警告】找不到 Chrome 或 Edge，改用系統預設方式開啟。")

    webbrowser.open(address, new=2)
    print(f"已用系統預設瀏覽器開啟 ({card_name})。")


def open_address(address):
    webbrowser.open(address, new=0)

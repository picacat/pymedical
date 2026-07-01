# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
# 開啟網址
import os
import subprocess
import sys
import time
import webbrowser

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


def find_browser_exe(browser: str):
    """
    尋找指定瀏覽器的執行檔路徑（Windows 常見安裝路徑）。
    browser: "edge" 或 "chrome"
    """
    candidates = {
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
    }
    return next((p for p in candidates.get(browser, []) if os.path.exists(p)), None)


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
            "--no-first-run",
            "--no-default-browser-check",
            address,
        ]
    )


def open_nhi_medcloud(use_virtual_card: bool = False):
    card_type = "vhc" if use_virtual_card else "icc"
    address = f"https://medcloud2.nhi.gov.tw/imu/imue1000?type={card_type}&_t={int(time.time())}"

    if sys.platform == "win32":
        default_browser = get_default_browser() or ""

        if "Edge" in default_browser:
            edge_exe = find_browser_exe("edge")
            if edge_exe:
                open_with_clean_cache(edge_exe, address, "edge")
                print(
                    f"偵測到預設瀏覽器為 Edge，已強制清空快取並開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})。"
                )
                return
            print(
                "【警告】偵測到預設瀏覽器為 Edge，但找不到 msedge.exe，將改用系統預設方式開啟。"
            )

        elif "Chrome" in default_browser:
            chrome_exe = find_browser_exe("chrome")
            if chrome_exe:
                open_with_clean_cache(chrome_exe, address, "chrome")
                print(
                    f"偵測到預設瀏覽器為 Chrome，已強制清空快取並開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})。"
                )
                return
            print(
                "【警告】偵測到預設瀏覽器為 Chrome，但找不到 chrome.exe，將改用系統預設方式開啟。"
            )

    # 非 Windows / 非 Edge / 非 Chrome / 找不到執行檔，一律退回系統預設瀏覽器開啟
    webbrowser.open(address, new=2)
    print(f"已用系統預設瀏覽器開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})。")


def open_address(address):
    webbrowser.open(address, new=0)

# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
import os
import shutil
import subprocess
import sys
import time
import webbrowser

if sys.platform == "win32":
    import winreg


# 雲端藥歷
def open_med_vpn(system_settings, vhc_ic_card=False):
    if vhc_ic_card:
        address = "https://medcloud2.nhi.gov.tw/imu/imue1000?type=vhc"
    else:
        address = "https://medcloud2.nhi.gov.tw/imu/imue1000?type=icc"

    webbrowser.open(address, new=0)  # 0: open in existing tab, 2: new tab


# 開啟網址
def open_address(address):
    webbrowser.open(address, new=0)


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


def find_edge_exe():
    """尋找 Edge 執行檔路徑（僅 Windows 常見安裝路徑）"""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    return next((p for p in candidates if os.path.exists(p)), None)


def open_nhi_medcloud(use_virtual_card: bool = False):
    card_type = "vhc" if use_virtual_card else "icc"
    address = f"https://medcloud2.nhi.gov.tw/imu/imue1000?type={card_type}&_t={int(time.time())}"

    # 只有 Windows 才嘗試判斷是不是 Edge，並做強制清快取的處理
    if sys.platform == "win32":
        default_browser = get_default_browser()
        is_edge = default_browser is not None and "Edge" in default_browser

        if is_edge:
            edge_exe = find_edge_exe()
            if edge_exe:
                # 每次啟動前清空暫存 profile，確保是全新、無快取的環境
                temp_profile = os.path.join(
                    os.environ.get("TEMP", "."), "nhi_medcloud_temp_profile"
                )
                shutil.rmtree(temp_profile, ignore_errors=True)

                subprocess.Popen(
                    [
                        edge_exe,
                        "--new-window",
                        f"--user-data-dir={temp_profile}",
                        address,
                    ]
                )
                print(
                    f"偵測到預設瀏覽器為 Edge，已強制清空快取並開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})。"
                )
                return
            else:
                print(
                    "【警告】偵測到預設瀏覽器為 Edge，但找不到 msedge.exe，將改用系統預設方式開啟。"
                )

    # 非 Windows / 非 Edge / 找不到 Edge 執行檔，一律退回系統預設瀏覽器開啟
    webbrowser.open(address, new=2)
    print(f"已用系統預設瀏覽器開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})。")

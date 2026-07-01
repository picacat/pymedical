# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
import os
import webbrowser

from libs import system_utils

try:
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:
    system_utils.pip3_install("selenium")
    system_utils.pip3_install("webdriver-manager")
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from webdriver_manager.microsoft import EdgeChromiumDriverManager


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


def open_nhi_medcloud(
    use_virtual_card: bool = False,
    user_data_dir: str | None = None,
    profile_name: str = "Default",
):
    """
    開啟健保醫療雲端系統，並確保頁面不使用快取（適合 HIS 系統整合呼叫）。

    Args:
        use_virtual_card: True 使用虛擬健保卡(VHC), False 使用實體IC卡(ICC)
        user_data_dir: Edge 使用者資料路徑 (僅在讀卡機/憑證元件確實需要瀏覽器 Profile 時才傳入)
                       例如: r"C:\\Users\\YourUser\\AppData\\Local\\Microsoft\\Edge\\User Data"
                       注意：若使用真實 Profile，該 Profile 不能同時被其他 Edge 視窗開啟，
                       且會帶入該使用者所有登入態，建議先測試不帶此參數是否也能正常讀卡。
        profile_name: 指定的 Profile 資料夾名稱 (預設為 "Default")

    Returns:
        driver: 開啟後的 WebDriver 物件，需由主程式在適當時機執行 driver.quit()
    """
    card_type = "vhc" if use_virtual_card else "icc"
    address = f"https://medcloud2.nhi.gov.tw/imu/imue1000?type={card_type}"

    options = webdriver.EdgeOptions()

    # 診所實務優化：啟動時直接最大化視窗，方便人員操作
    options.add_argument("--start-maximized")

    # 若傳入 user_data_dir，帶入特定 Profile（請先確認是否真的需要，見上方說明）
    if user_data_dir:
        if os.path.exists(user_data_dir):
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument(f"--profile-directory={profile_name}")
        else:
            print(
                f"【警告】找不到指定的 Edge Profile 路徑: {user_data_dir}，將使用預設乾淨環境啟動。"
            )

    try:
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception as e:
        error_msg = f"無法啟動 Edge 瀏覽器。請檢查是否已安裝 Edge，或 Driver 是否遭防毒軟體封鎖。\n錯誤訊息: {e}"
        raise RuntimeError(error_msg) from e

    # 用 CDP 指令關閉快取，比 command line flag 或 reload(true) 更可靠
    driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    driver.execute_cdp_cmd("Network.clearBrowserCache", {})

    driver.get(address)
    print(
        f"健保雲端網頁已成功開啟 ({'虛擬卡' if use_virtual_card else '實體卡'})，已強制停用快取。"
    )

    return driver

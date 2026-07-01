# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
import webbrowser


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

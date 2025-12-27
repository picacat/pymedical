# 網址列表 2019.12.25
# -*- coding: UTF-8 -*-
import webbrowser


# 雲端藥歷
def open_med_vpn(system_settings, vhc_ic_card=False):
    # if system_settings.field('讀卡機控制軟體版本') == 'cshis6':
    #     address = 'https://medcloud2.nhi.gov.tw/imu/IMUE1000/'
    # else:
    #     address = 'https://medcloud.nhi.gov.tw/imme0008/IMME0008S01.aspx'

    if vhc_ic_card:
        address = 'https://medcloud2.nhi.gov.tw/imu/imue1000?type=vhc'
    else:
        address = 'https://medcloud2.nhi.gov.tw/imu/imue1000?type=icc'

    webbrowser.open(address, new=0)  # 0: open in existing tab, 2: new tab


# 開啟網址
def open_address(address):
    webbrowser.open(address, new=0)

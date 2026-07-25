# 讀卡機加值作業 2022.02.10

import ctypes
import os
import json
import base64
import requests

from libs import date_utils
import win32com.client

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))


# 健保ICD卡 2018.03.31
class HCAAPI:
    RTN_CODE_DICT = {
        '0000': '正確有效',
        '5003': '作業類別錯誤',
        '5004': '安全模組卡無效: 安全模組卡與上傳時不符',
        '8201': '服務異常: 呼叫驗簽服務發生例外',
        '8202': '服務異常: 驗簽服務回傳其他列外',
        '8203': '簽章已逾有效期限(1小時): 請重新取簽章',
        '8205': '安全模組卡已註銷: 請洽所屬分區業務組協助解決',
        '9002': '驗簽失敗: 未完成驗證作業',
        '9005': '醫療院所代號不存在: 院所代號欄位非為特約院所代號',
        '9999': '其他',
    }

    def __init__(self, database, system_settings):
        self.database = database
        self.system_systems = system_settings
        self.reader_type = self.system_systems.field('讀卡機類型')

        try:
            if self.reader_type == '晶片讀卡機':
                hca_api_file_name = os.path.join(CURRENT_DIR, 'HCAAPI.dll')
            else:
                hca_api_file_name = os.path.join(CURRENT_DIR, 'HCACSAPI.dll')

            self.hca_api = ctypes.windll.LoadLibrary(hca_api_file_name)
            # self.hca_api.DllRegisterServer()
        except Exception:
            self.hca_api = None

    def __del__(self):
        pass

    def get_cert(self):
        if self.reader_type == '晶片讀卡機':
            certificate = self.get_hca_cert()
        else:
            certificate = self.get_hca_cs_cert()

        return certificate

    def get_hca_cert(self):
        print('get hca cert')

    def get_hca_cs_cert(self):
        print('get hca cs cert')

# 讀卡機加值作業 2022.02.10

import base64
import ctypes
import json
import logging
import os

import requests
import win32com.client

from libs import date_utils

# CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


# 健保ICD卡 2018.03.31
class CSHISX:
    RTN_CODE_DICT = {
        "0000": "正確有效",
        "5003": "作業類別錯誤",
        "5004": "安全模組卡無效: 安全模組卡與上傳時不符",
        "8201": "服務異常: 呼叫驗簽服務發生例外",
        "8202": "服務異常: 驗簽服務回傳其他列外",
        "8203": "簽章已逾有效期限(1小時): 請重新取簽章",
        "8205": "安全模組卡已註銷: 請洽所屬分區業務組協助解決",
        "9002": "驗簽失敗: 未完成驗證作業",
        "9005": "醫療院所代號不存在: 院所代號欄位非為特約院所代號",
        "9999": "其他",
    }

    def __init__(self, database, system_settings):
        self.database = database
        try:
            cshisx_file_name = os.path.join(CURRENT_DIR, "CsHisX.dll")
            self.cshisx_dll = ctypes.windll.LoadLibrary(cshisx_file_name)
            self.cshisx_dll.DllRegisterServer()
            self.cshisx = win32com.client.Dispatch("CsHisX.nhicshisx.1")
        except Exception as e:
            logging.error(f"CsHisX 初始化失敗: {e}")
            self.cshisx = None

        self.clinic_id = system_settings.field("院所代號")

    def __del__(self):
        pass

    # 取得簽章 2026-01-01 新增card_type及service_type參數
    def VPNH_SignX(self, card_type="3", service_type="30"):
        if self.cshisx is None:
            raise RuntimeError("CsHisX 元件未初始化,請確認讀卡機環境")

        random_number = self.cshisx.VPNGetRandomX()
        signature = self.cshisx.VPNH_SignX(random_number, card_type, service_type)

        return random_number, signature

    def GetSAMCardInfoInCS(self):
        json = self.cshisx.GetSAMCardInfoInCS()

        return json

    def VNHI_Upload(
        self, upload_type, xml, case_count, prescript_count, encoding="Big5"
    ):
        sam_card_info = self.GetSAMCardInfoInCS()
        sam_card_json = json.loads(sam_card_info)

        sSamId = sam_card_json["SAMCardInfoInCS"]["SAM"][0]["CARD_ID"]
        sHospId = sam_card_json["SAMCardInfoInCS"]["SAM"][0]["HOSP"]
        sClientRandom, sSignature = self.VPNH_SignX(card_type="3", service_type="30")

        sType = upload_type  # A1: 健保卡就醫資料正式上傳, A2: 健保卡就醫資料預檢上傳 ZZ: 介接測試
        sMrecs = case_count
        sPrecs = prescript_count
        sPatData = base64.b64encode(xml.encode(encoding)).decode("ascii")
        sUploadDT = date_utils.now_to_nhi_str() + "000"  # 加上毫秒

        upload_json = {
            "sSamId": sSamId,
            "sHospId": sHospId,
            "sClientRandom": sClientRandom,
            "sSignature": sSignature,
            "sType": sType,
            # 'sMrecs': sMrecs,  # 2022.05.11 取消
            # 'sPrecs': sPrecs,
            "sPatData": sPatData,
            "sUploadDT": sUploadDT,
        }
        json_data = json.dumps(upload_json)

        url = "https://medvpndti.nhi.gov.tw/V1000/VNHI_Upload"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url=url, headers=headers, data=json_data, verify=False)

        try:
            result = json.loads(response.content.decode(encoding))
        except Exception:
            result = json.loads(response.content.decode("utf-8"))
            return -1, result

        return result["RtnCode"], result["Opcode"]

    def VNHI_Upload_cshis6(
        self,
        upload_type,
        sam_id,
        hosp_id,
        client_random,
        signature,
        xml,
        case_count,
        encoding="utf-8",
    ):

        sType = upload_type  # A1: 健保卡就醫資料正式上傳, A2: 健保卡就醫資料預檢上傳 ZZ: 介接測試
        sMrecs = case_count
        sPatData = base64.b64encode(xml.encode(encoding)).decode(encoding)
        sUploadDT = date_utils.now_to_nhi_str() + "000"  # 加上毫秒

        upload_json = {
            "sSamId": sam_id,
            "sHospId": hosp_id,
            "sClientRandom": client_random,
            "sSignature": signature,
            "sType": sType,
            # 'sMrecs': sMrecs,  # 2022.05.11 取消
            # 'sPrecs': sPrecs,
            "sPatData": sPatData,
            "sUploadDT": sUploadDT,
        }
        json_data = json.dumps(upload_json)

        url = "https://medvpndti.nhi.gov.tw/V2000/VNHI_Upload"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url=url, headers=headers, data=json_data, verify=False)

        try:
            result = json.loads(response.content.decode(encoding))
        except Exception:
            result = json.loads(response.content.decode("utf-8"))
            return -1, result

        return result["RtnCode"], result["Opcode"]

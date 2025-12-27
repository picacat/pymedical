# 讀卡機加值作業 2022.02.10

import os
import json
import base64
import requests

from libs import date_utils

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))


# 健保ICD卡 2018.03.31
class CSHISX:
    def __init__(self, database, system_settings):
        self.database = database
        self.system_settings = system_settings
        self.cshisx = None

        self.clinic_id = self.system_settings.field('院所代號')

    def __del__(self):
        pass

    def VPNH_SignX(self):
        random_number = self.cshisx.VPNGetRandomX()
        signature = self.cshisx.VPNH_SignX(random_number, '3', '30')

        return random_number, signature

    def GetSAMCardInfoInCS(self):
        json = self.cshisx.GetSAMCardInfoInCS()

        return json

    # upload_type: A1: 健保卡就醫資料正式上傳, A2: 健保卡就醫資料預檢上傳 ZZ: 介接測試
    def VNHI_Upload(self, upload_type, xml, case_count, prescript_count, encoding='Big5'):
        sam_card_info = self.GetSAMCardInfoInCS()
        sam_card_json = json.loads(sam_card_info)

        sSamId = sam_card_json['SAMCardInfoInCS']['SAM'][0]['CARD_ID']
        sHospId = sam_card_json['SAMCardInfoInCS']['SAM'][0]['HOSP']
        sClientRandom, sSignature = self.VPNH_SignX()

        sType = upload_type  # A1: 健保卡就醫資料正式上傳, A2: 健保卡就醫資料預檢上傳 ZZ: 介接測試
        sMrecs = case_count
        sPrecs = prescript_count
        sPatData = base64.b64encode(xml.encode(encoding)).decode('ascii')
        sUploadDT = date_utils.now_to_nhi_str() + '000'  # 加上毫秒

        upload_json = {
            'sSamId': sSamId,
            'sHospId': sHospId,
            'sClientRandom': sClientRandom,
            'sSignature': sSignature,
            'sType': sType,
            # 'sMrecs': sMrecs,  # 2022.05.11 取消
            # 'sPrecs': sPrecs,
            'sPatData': sPatData,
            'sUploadDT': sUploadDT,
        }
        json_data = json.dumps(upload_json)

        url = 'https://medvpndti.nhi.gov.tw/V1000/VNHI_Upload'
        headers = {'Content-Type': 'application/json'}

        response = requests.post(url=url, headers=headers, data=json_data, verify=False)

        try:
            result = json.loads(response.content.decode(encoding))
        except Exception:
            result = json.loads(response.content.decode('utf-8'))
            return -1, result

        return result['RtnCode'], result['Opcode']

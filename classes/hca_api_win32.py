# 讀卡機加值作業 2022.02.10

from PyQt5.QtWidgets import QInputDialog
import ctypes
import os
import json
import base64
import requests
import sys
import codecs

import win32com.client
import win32api

from libs import number_utils
from libs import case_utils
from libs import dialog_utils

CURRENT_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))

CKF_RW_SESSION = 0x02
CKF_SERIAL_SESSION = 0x04

CKM_RSA_PKCS = 0x0001
CKM_SHA1_RSA_PKCS = 0x0006

HCA_F_TestGNFunc = 10001                # 測試函試，測試有否連上HCSCSAPI函式庫。
HCA_F_GetBasicData = 10101              # 取得基本資料。
HCA_F_GetCardInfo = 10102               # 取得卡片資訊。
HCA_F_GetCardType = 10103               # 取卡片類型。
HCA_F_GetCardSN = 10104                 # 取卡片序號。
HCA_F_VerifyPIN = 10105                 # 驗證卡片PIN碼。
HCA_F_SetPIN = 10106                    # 重設卡片PIN碼。
HCA_F_ResetHCAApplet = 10107            # 將HPC卡片狀能重設。(不對外公佈。)
HCA_F_CheckHCAApplet = 10108            # 檢查HCA Applet 能否被使用。(不對外公佈。)
HCA_F_GetCert = 10201                   # 取得卡片內之憑證。
HCA_F_SignMessage = 10202               # 採 RSA PKCS#1 Standard Signature (Big Endian)
HCA_F_SignDigest = 10110                # 使用Hash資料進行簽章, 採 RSA PKCS#1 Standard Signature (Big Endian)
HCA_F_SignMessageEx = 10220             # 採 MS CAPI Standard Signature (Little Endian)
HCA_F_VerifySignMessage = 10203         # 對資料驗章。
HCA_F_PublicEncrypt = 10204             # 對明文做RSA公鑰加密。
HCA_F_PrivateDecrypt = 10205            # 對密文做RSA金鑰解密
HCA_F_VerifySignMessage_PKCS = 10206    # 對資料驗章，(不對外公佈，因是用來測試：簽章動作在PKCS#11是否也相通。)
HCA_F_PublicEncrypt_PKCS = 10207        # 對明文做RSA公鑰加密，(不對外公佈，因是用來測試：RSA加解密動作在PKCS#11是否也相通。)
HCA_F_LoadCert = 10208                  # 將憑證檔載入工作區。在做[資料驗章]與[RSA公鑰加密]之前須先做此動作。
HCA_F_Finalize = 10216                  # 釋放初始化動作佔去的記憶體。
HCA_F_GetCardVersion = 10217            # 取得卡片版本1.0或2.0
HCA_F_MessageDigest = 10211
HCA_F_TSQuery = 10209
HCA_F_TSVerify = 10210
HCA_F_GetCertAttr = 10212
HCA_F_GetTSInfo = 10213
HCA_F_SetTSAddress = 10218
HCA_F_GetKeySize = 10219                # 取得金鑰長度

HCA_F_GetCertType = 10221               # 取憑證卡類型 (SHA1 || SHA256)


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
        self.system_settings = system_settings
        self.reader_type = self.system_settings.field('讀卡機類型')
        self.ic_com_port = number_utils.get_integer(
            system_settings.field('健保卡讀卡機連接埠')) - 1  # com1=0, com2=1, com3=2,...

        if system_settings.field('讀卡機類型') == '健保讀卡機':
            hca_file_name = os.path.join(CURRENT_DIR, 'CsHis.dll')
        else:
            hca_file_name = os.path.join(CURRENT_DIR, 'HCAAPI.dll')

        try:
            self.hca_api = ctypes.windll.LoadLibrary(hca_file_name)
        except Exception:
            self.hca_api = None

        self.module_handle = ctypes.c_long()
        self.session_handle = ctypes.c_ulong()

    def __del__(self):
        pass

    def open_com(self):
        com_port = ctypes.c_short(self.ic_com_port)
        error_code = self.hca_api.csOpenCom(com_port)

        return error_code

    def close_com(self):
        self.hca_api.csCloseCom()

    def get_cert(self, case_key):
        if self.reader_type == '晶片讀卡機':
            input_dialog = dialog_utils.get_dialog(
                '醫事卡認證',
                '請輸入醫事人員卡密碼',
                None, QInputDialog.TextInput, 320, 200
            )
            ok = input_dialog.exec_()
            if not ok:
                return

            user_pin = input_dialog.textValue()

            self.init_module()
            self.init_session(user_pin)

            doctor_cert = self.get_hca_doctor_cert()
            prescript_cert = self.get_hca_prescript_cert(case_key)

            self.hca_api.CloseSession(self.module_handle, self.session_handle)
            self.hca_api.CloseModule(self.module_handle)

        else:
            error_code = self.open_com()
            if error_code != 0:
                print('open com error')
                return None

            doctor_cert = self.get_hca_cs_doctor_cert()
            prescript_cert = self.get_hca_cs_prescript_cert(case_key)

            self.close_com()

        return doctor_cert, prescript_cert

    def init_module(self):
        rtn_code = self.hca_api.InitModule(b'HCAPKCS11', ctypes.c_void_p(None), ctypes.byref(self.module_handle))

    def init_session(self, user_pin):
        psz_user_pin = user_pin.encode('ascii')
        rtn_code = self.hca_api.InitSession(
            self.module_handle, CKF_SERIAL_SESSION, psz_user_pin, len(psz_user_pin),
            ctypes.byref(self.session_handle))

    def get_hca_doctor_cert(self):
        cert_id = 1  # 1: 驗章, 2:加解密
        p_cert_length = ctypes.c_int(0)
        p_cert_data = ctypes.c_void_p()
        reader_name = None

        rtn_code = self.hca_api.GetCertificateFromGPKICard(
            self.module_handle, self.session_handle, cert_id,
            None,
            ctypes.byref(p_cert_length),
            reader_name,
        )

        p_cert_data = ctypes.create_string_buffer(p_cert_length.value)
        rtn_code = self.hca_api.GetCertificateFromGPKICard(
            self.module_handle, self.session_handle, cert_id,
            p_cert_data,
            ctypes.byref(p_cert_length),
            reader_name,
        )
        cert = base64.b64encode(p_cert_data.raw).decode()

        return cert

    def get_hca_prescript_cert(self, case_key):
        prescript_data = case_utils.get_medical_record_qr_code_data(self.database, self.system_settings, case_key)
        prescript_bytes = prescript_data.encode('utf-8')
        prescript_length = len(prescript_bytes)

        key_type = 0  # 0: 私密金鑰, 1: 公開金鑰, 2: 對稱式金鑰
        key_id = ctypes.c_int(0x01)  # 0x01: 私密金鑰 0x02: 公開金鑰
        key_handle = ctypes.c_ulong()

        rtn_code = self.hca_api.GetKeyObjectHandle(
            self.module_handle, self.session_handle, key_type,
            None, 0,
            ctypes.byref(key_id), 1,
            ctypes.byref(key_handle))

        p_signature_length = ctypes.c_int(0)

        # 下面這行只是為了取得 p_signature_length 的長度
        rtn_code = self.hca_api.MakeSignature(
            self.module_handle, self.session_handle, CKM_SHA1_RSA_PKCS,
            prescript_bytes, prescript_length, key_handle,
            None, ctypes.byref(p_signature_length)
        )

        # 這段才是配置足夠的 p_signature 的記憶體空間
        p_signature = ctypes.create_string_buffer(p_signature_length.value)
        rtn_code = self.hca_api.MakeSignature(
            self.module_handle, self.session_handle, CKM_SHA1_RSA_PKCS,
            prescript_bytes, prescript_length, key_handle,
            p_signature, ctypes.byref(p_signature_length)
        )

        self.hca_api.DeleteKeyObject(self.module_handle, self.session_handle, key_handle)

        # prescript_data = codecs.BOM_UTF8 + prescript_data.encode('utf-8')
        sign = base64.b64encode(p_signature.raw).decode()
        data1 = base64.b64encode(prescript_bytes).decode()

        cert = f'{{"Sign":"{sign}","Data1":"{data1}"}}'

        return cert

    # def get_hca_cs_doctor_cert(self):
    #     # buffer_length = 1434
    #     buffer_length = 2048
    #     buffer = ctypes.create_string_buffer(buffer_length)  # c: char *
    #     ctypes.memset(buffer, 0, buffer_length)

    #     # cert_id = 0  # 0: CA憑證, 1: 使用者憑證1, 2: 使用者憑證2, 3: GCA 憑證, 4: GRCA 憑證
    #     cert_id = 1  # 0: CA憑證, 1: 使用者憑證1, 2: 使用者憑證2, 3: GCA 憑證, 4: GRCA 憑證

    #     rtn_code = self.hca_api.HCA_GNFuncCall(
    #         HCA_F_GetCert,
    #         None,
    #         ctypes.byref(buffer),
    #         cert_id,
    #         buffer_length,
    #         0, 0, 0,
    #     )

    #     cert = base64.b64encode(buffer.raw).decode('utf-8')

    #     return cert

    def get_hca_cs_doctor_cert(self):
        cbCert = 4096
        byCert = bytearray(cbCert)
        byCert[:cbCert] = bytes([0] * cbCert)

        buffer = ctypes.create_string_buffer(cbCert)  # c: char *
        ctypes.memset(buffer, 0, cbCert)
        cert_id = 1  # 0: CA憑證, 1: 使用者憑證1, 2: 使用者憑證2, 3: GCA 憑證, 4: GRCA 憑證

        rtn_code = self.hca_api.HCA_GNFuncCall(
            HCA_F_GetCert,
            None,
            ctypes.byref(buffer),
            cert_id,
            cbCert,
            0, 0, 0,
        )

        byCert = bytearray(buffer.raw)
        n = byCert[1] & 0x0F
        cbCert = 0
        i = 0
        while i < n:
            cbCert = (cbCert << 8) | (byCert[2 + i] & 0xFF)
            i += 1

        cbCert += 2 + n

        cert = base64.b64encode(byCert[:cbCert]).decode('utf-8')

        return cert

    def get_hca_cs_prescript_cert(self, case_key):
        prescript_data = case_utils.get_medical_record_qr_code_data(self.database, self.system_settings, case_key)
        prescript_bytes = prescript_data.encode('utf-8')
        prescript_length = len(prescript_bytes)

        key_size = self.hca_api.HCA_GNFuncCall(
            HCA_F_GetKeySize,
            0, 0, 0, 0, 0, 0, 0
        )

        signature = ctypes.create_string_buffer(key_size)
        rtn_code = self.hca_api.HCA_GNFuncCall(
            HCA_F_SignMessage,
            prescript_bytes,
            ctypes.byref(signature),
            prescript_length,
            key_size,
            0, 0, 0
        )

        sign = base64.b64encode(signature.raw).decode()
        data1 = base64.b64encode(prescript_bytes).decode()

        cert = f'{{"Sign":"{sign}","Data1":"{data1}"}}'

        return cert

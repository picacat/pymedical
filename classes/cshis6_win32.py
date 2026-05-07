import base64
import os
from queue import Queue
from threading import Thread

import requests
import urllib3
from PyQt5 import QtCore
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QPushButton

from libs import (
    case_utils,
    class_utils,
    cshis_utils,
    date_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    prescript_utils,
    string_utils,
    system_utils,
)

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))


# NHI_TEST_URL = 'https://medvpndct.nhi.gov.tw'
# NHI_URL = 'https://medvpndc.nhi.gov.tw'

LOCAL_URL = "https://localhost:5066"
NHI_URL = "https://medvpndc.nhi.gov.tw"
NHI_TEST_URL = "https://medvpndct.nhi.gov.tw"  # 測試用

HEADERS = {
    "Content-Type": "application/json",  # 根據 API 要求的 Content-Type 設定
}


# 健保ICD卡 2018.03.31
class CSHIS:
    def __init__(
        self, parent, database, system_settings, ic_card_type="健保卡", qrcode=None
    ):
        self.parent = parent
        self.database = database
        self.system_settings = system_settings
        self.ic_card_type = ic_card_type
        self.qrcode = qrcode

        self.cshis = True
        self.reader_type = self.system_settings.field("讀卡機類型")
        self.com_port = self.system_settings.field("健保卡讀卡機連接埠")
        self.sam_id = self.system_settings.field("SAMID")

        self.clinic_id = self.system_settings.field("院所代號")
        self.basic_data = cshis_utils.BASIC_DATA
        self.treat_data = cshis_utils.TREAT_DATA
        self.treatment_data = cshis_utils.TREATMENT_DATA
        self.disease_data = cshis_utils.DISEASE_DATA
        self.critical_illness_data = []
        self.prescript_data = []

    def __del__(self):
        pass

    def activate_reader_app(self):
        initialized = self.get_api_status()["initialized"]
        if initialized:
            self.finalize_cshis6()

        self.init_cshis6()
        # self.verify_sam(show_message=False)

    def deactivate_reader_app(self):
        initialized = self.get_api_status()["initialized"]
        if initialized:
            self.finalize_cshis6()

    @staticmethod
    def _message_box(title, message, hint):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setInformativeText(hint)
        msg_box.setStandardButtons(QMessageBox.NoButton)

        return msg_box

    def do_thread(self, nhi_thread, *args):
        msg_box = None
        try:
            operation = args[0]
        except IndexError:
            operation = None

        try:
            show_warning = args[3]
        except Exception:
            show_warning = True

        if operation:
            msg_box = self._message_box("健保讀卡機作業", args[1], args[2])
            msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=nhi_thread, args=(msg_queue,))
        t.start()
        error_code = msg_queue.get()
        if msg_box:
            msg_box.close()

        if error_code != 0 or show_warning:
            cshis_utils.show_ic_card_message(error_code, operation)

        return error_code

    def get_com_port(self):
        if self.reader_type == "健保讀卡機":
            com_port = f"COM{self.com_port}"
        else:
            com_port = None

        return com_port

    def init_cshis6(self):
        initialized = self.get_api_status()["initialized"]
        if initialized:
            self.finalize_cshis6()

        service_path = "/api/common/v1/Initial"
        data = {}

        if self.sam_id not in ["", None]:
            data = {"name": self.sam_id}
        else:
            com_port = self.get_com_port()
            if com_port is not None:
                data = {"name": com_port}

        response = self._get_requests_response(service_path, "POST", data)
        return_code = response.json()["statusCode"]
        if return_code == 1001:
            return_code = 0

        return return_code

    def finalize_cshis6(self):
        service_path = "/api/common/v1/Finalize"
        data = {}

        response = self._get_requests_response(service_path, "POST", data)
        return_code = response.json()["statusCode"]
        if return_code == 1001:
            return_code = 0

        return return_code

    def verify_sam_thread(self, out_queue):
        error_code = self.init_cshis6()

        verify_sam = self.get_api_status()["sam"]["status"]
        if verify_sam == 2:  # 已經認證過了
            error_code = 0
        else:
            service_path = "/api/sam/v1/Verification"
            data = {}
            response = self._get_requests_response(service_path, "POST", data)
            error_code = response.json()["statusCode"]

        out_queue.put(error_code)

    def verify_sam(self, show_message=True):
        error_code = self.do_thread(
            self.verify_sam_thread,
            "健保讀卡機安全模組卡認證",
            '<font size="5" color="red"><b>健保讀卡機安全模組卡認證中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
            show_message,
        )

        return error_code

    def verify_hc_pin(self):
        input_dialog = dialog_utils.get_dialog(
            "驗證健保卡密碼",
            "請輸入健保卡pin碼",
            None,
            QInputDialog.TextInput,
            320,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            error_code = 5109
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼驗證")
            return

        pin = input_dialog.textValue()
        service_path = "/api/hc/v1/Pin"
        data = {"pin": pin}
        response = self._get_requests_response(service_path, "POST", data)
        error_code = response.json()["statusCode"]
        cshis_utils.show_ic_card_message(error_code, "健保IC卡密碼驗證")

    def input_hc_pin(self):
        input_dialog = dialog_utils.get_dialog(
            "設定健保卡密碼",
            "請輸入健保卡pin碼",
            None,
            QInputDialog.TextInput,
            320,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            error_code = 5109
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼設定")
            return

        pin = input_dialog.textValue()
        service_path = "/api/hc/v1/Pin"
        data = {"newPin": pin}
        response = self._get_requests_response(service_path, "PUT", data)
        error_code = response.json()["statusCode"]
        cshis_utils.show_ic_card_message(error_code, "健保IC卡密碼設定")

    def disable_hc_pin(self):
        service_path = "/api/hc/v1/Pin"
        data = {}
        response = self._get_requests_response(service_path, "DELETE", data)
        error_code = response.json()["statusCode"]

        cshis_utils.show_ic_card_message(error_code, "健保IC卡密碼解除")

    def logout_hpc(self):
        service_path = "/api/hpc/v1/Logout"
        data = {}
        response = self._get_requests_response(service_path, "DELETE", data)
        error_code = response.json()["statusCode"]

        return error_code

    # 驗證醫事人員卡
    def verify_hpc_pin(self, show_message=True):
        api_status = self.get_api_status()
        hpc_mode = api_status["hpc"]["status"]
        if hpc_mode == 3:  # 已經認證過了
            cshis_utils.show_ic_card_message(0, "醫事人員卡密碼驗證")
            return None

        if hpc_mode == 0:  # 位置入卡片
            self.logout_hpc()
            cshis_utils.show_ic_card_message(1102, "讀取醫事人員卡")  # 未置入卡片
            return None

        sam_mode = api_status["sam"]["status"]
        if sam_mode != 2:  # 未完成sam認證
            self.verify_sam(show_message=False)

        if self.reader_type == "晶片讀卡機":  # 開始認證
            input_dialog = dialog_utils.get_dialog(
                "驗證醫事人員卡密碼",
                "請輸入醫事人員卡pin碼",
                None,
                QInputDialog.TextInput,
                320,
                200,
            )
            ok = input_dialog.exec_()
            if not ok:
                error_code = 5109
                cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼驗證")
                return

            pin = input_dialog.textValue()
        else:
            pin = "000000"

        data = {"pin": pin}
        service_path = "/api/hpc/v1/Verification/Hpc"
        response = self._get_requests_response(service_path, "POST", data)

        # error_code = response.json()["statusCode"]
        error_code = self.get_error_code(response)

        if show_message or error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼驗證")

        return error_code

    def get_error_code(self, response):
        if response is None:
            return -1

        try:
            res_data = response.json()
            error_code = res_data.get("statusCode", -1)  # 使用 .get 防止 key 不存在
        except Exception:
            return -1

        return error_code

    def input_hpc_pin(self):
        self.logout_hpc()
        title = "變更醫事人員卡密碼"
        message = '<font size="5" color="red"><b>若您的卡片正插在讀卡機內, 請在按下確定前拔除醫事人員卡後再插入，以完成驗證程序</b></font>'
        hint = "若您的醫事人員卡未插入讀卡機，現在請插入讀卡機."
        system_utils.show_message_box(
            QMessageBox.Information,
            title=title,
            text=message,
            informative=hint,
        )

        error_code = self.verify_hpc_pin(show_message=False)
        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼驗證")
            return

        input_dialog = dialog_utils.get_dialog(
            "設定醫事人員卡密碼",
            "請輸入醫事人員卡pin碼",
            None,
            QInputDialog.TextInput,
            320,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            error_code = 5109
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼設定")
            return

        pin = input_dialog.textValue()
        service_path = "/api/hpc/v1/Pin"
        data = {"newPin": pin}
        response = self._get_requests_response(service_path, "POST", data)
        error_code = response.json()["statusCode"]
        cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼設定")

    def unlock_hpc(self):
        input_dialog = dialog_utils.get_dialog(
            "醫事人員卡解鎖",
            "請輸入醫事人員卡PUK碼",
            None,
            QInputDialog.TextInput,
            320,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            error_code = 5109
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡PUK碼解鎖")
            return

        puk = input_dialog.textValue()

        input_dialog = dialog_utils.get_dialog(
            "設定醫事人員卡密碼",
            "請輸入醫事人員卡pin碼",
            None,
            QInputDialog.TextInput,
            320,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            error_code = 5109
            cshis_utils.show_ic_card_message(error_code, "醫事人員卡密碼設定")
            return

        new_pin = input_dialog.textValue()

        service_path = "/api/hpc/v1/Pin"
        data = {
            "puk": puk,
            "newPin": new_pin,
        }
        response = self._get_requests_response(service_path, "PUT", data)
        error_code = response.json()["statusCode"]
        cshis_utils.show_ic_card_message(error_code, "醫事人員卡解鎖")

    def reset_reader(self, show_message=True):
        error_code = self.init_cshis6()
        if show_message:
            cshis_utils.show_ic_card_message(error_code, "讀卡機重新啟動")

    def _update_patient(self, patient_key):
        if not self.read_basic_data():
            return "", ""

        patient_id = self.basic_data["patient_id"]
        patient_birthday = self.basic_data["birthday"]

        fields = ["ID", "Birthday"]
        data = [patient_id, patient_birthday]
        self.database.update_record("patient", fields, "PatientKey", patient_key, data)

        return patient_id, patient_birthday

    def _get_requests_response(self, service_path, request_type, data, local_url=True):
        if self.system_settings.field("使用測試環境") == "Y":
            nhi_url = NHI_TEST_URL
        else:
            nhi_url = NHI_URL

        # 主控台元件預設聆聽 5066 通訊埠 [cite: 52, 59]
        url = (LOCAL_URL if local_url else nhi_url) + service_path

        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.request(
                method=request_type,
                url=url,
                json=data,
                headers=HEADERS,
                verify=False,
                timeout=10,  # 加入逾時機制提升品質
            )
            response.raise_for_status()
            return response
        except Exception:
            return None

    def get_sam_signature(self, service_type):
        service_path = "/api/sam/v1/Signature"
        data = {"serviceType": service_type}
        response = self._get_requests_response(service_path, "POST", data)

        return response.json()

    def verify_vhc_card(self):
        service_path = "/api/hc/v1/Verification/VirtualHc"
        data = {"token": self.qrcode}
        response = self._get_requests_response(service_path, "POST", data)
        try:
            error_code = response.json()["statusCode"]
        except Exception:
            return False

        return True

    # def get_hc_signature(self, service_type):
    #     service_path = "/api/hc/v1/Signature/Hc"
    #     data = {'serviceType': service_type}
    #     response = self._get_requests_response(service_path, 'POST', data)

    #     error_code = response.json()['statusCode']
    #     if error_code != 0:
    #         cshis_utils.show_ic_card_message(error_code, '讀取健保卡簽章')
    #         return None

    #     return response.json()

    def get_hc_signature(self, service_type):
        service_path = "/api/hc/v1/Signature/Hc"
        data = {"serviceType": service_type}

        # 取得回應
        response = self._get_requests_response(service_path, "POST", data)

        # --- 新增保護檢查 ---
        if response is None:
            print("❌ 無法從 API 取得回應 (Network Error or Timeout)")
            # 這裡可以根據你的需求顯示自訂錯誤，或是直接回傳 None
            return None

        try:
            # 嘗試解析 JSON
            res_data = response.json()
            error_code = res_data.get("statusCode")

            if error_code != 0:
                cshis_utils.show_ic_card_message(error_code, "讀取健保卡簽章")
                return None

            return res_data

        except (ValueError, KeyError) as e:
            print(f"❌ JSON 解析失敗或格式錯誤: {e}")
            return None

    def get_hpc_signature(self, service_type):
        api_status = self.get_api_status()
        hpc_mode = api_status["hpc"]["status"]
        if hpc_mode != 0:  # 未置入卡片
            cshis_utils.show_ic_card_message(1102, "讀取醫事人員卡簽章")  # 未置入卡片
            return None

        sam_mode = api_status["sam"]["status"]
        if sam_mode != 2:  # 未完成sam認證
            self.verify_sam(show_message=False)

        service_path = "/api/hpc/v1/Signature"
        data = {"serviceType": service_type}
        response = self._get_requests_response(service_path, "POST", data)
        error_code = response.json()["statusCode"]
        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "讀取醫事人員卡簽章")
            return None

        return response.json()

    def get_hpchc_signature(self, service_type):
        api_status = self.get_api_status()
        hc_mode = api_status["hc"]["status"]
        if hc_mode == 0:  # 未置入卡片
            cshis_utils.show_ic_card_message(1102, "讀取健保卡")  # 未置入卡片
            return None

        hpc_mode = api_status["hpc"]["status"]
        if hpc_mode != 3:  # 未置入卡片
            cshis_utils.show_ic_card_message(1402, "讀取醫事人員卡簽章")  # 未置入卡片
            return None

        sam_mode = api_status["sam"]["status"]
        if sam_mode != 2:  # 未完成sam認證
            self.verify_sam(show_message=False)

        service_path = "/api/hc/v1/Signature/HpcHc"
        data = {"serviceType": service_type}
        response = self._get_requests_response(service_path, "POST", data)
        if response is None:
            cshis_utils.show_ic_card_message(4061, "讀取三卡簽章")
            return None

        return response.json()

    def read_basic_data(self, show_error=True):
        self.logout_hc()

        if self.ic_card_type == "虛擬健保卡":
            return self.read_register_basic_data_by_vhc()

        hc_signature = self.get_hc_signature(service_type="01")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/BasicData/Query"  # 請根據你的情況修改 URL
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        self.basic_data = cshis_utils.decode_cshis6_basic_data(response.json())
        self.basic_data["emg_phone"] = self.get_emergent_tel()

        return True

    def read_register_basic_data(self, show_warning=True):
        self.logout_hc()

        if self.ic_card_type == "虛擬健保卡":
            return self.read_register_basic_data_by_vhc()

        hc_signature = self.get_hc_signature(service_type="01")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/BasicData/Register"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        self.basic_data = cshis_utils.decode_cshis6_register_basic_data(response.json())
        self.basic_data["emg_phone"] = self.get_emergent_tel()

        return True

    def apply_qr_code(self):
        sam_signature = self.get_sam_signature(service_type="06")
        if sam_signature is None or sam_signature["clientRandom"] is None:
            cshis_utils.show_ic_card_message(4050, "請求虛擬健保卡授權失敗")
            return False

        service_path = "/test/v1/ApplyVirtualHc/Apply"
        data = {
            "clientRandom": sam_signature["clientRandom"],
            "hospitalId": sam_signature["hospitalId"],
            "samId": sam_signature["samId"],
            "signature": sam_signature["signature"],
            "sex": "M",
            "birthday": "0661005",
            "isForeigner": False,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        return response.json()

    def _get_qrcode(self):
        qrcode = None
        self.qrcode = None

        if self.system_settings.field("使用webcam讀取虛擬健保卡") == "Y":
            from dialog import dialog_qrcode

            success, qr_text = dialog_qrcode.DialogQRCode.get_qr_code(None)
            if success:
                self.qrcode = qr_text
                return qr_text
            else:
                return None

        input_dialog = dialog_utils.get_dialog(
            "虛擬健保卡",
            "請讀取新版虛擬健保卡 QRCode 2.0",
            None,
            QInputDialog.TextInput,
            600,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            return None

        qrcode = input_dialog.textValue().strip()
        if qrcode == "":
            return None

        self.qrcode = qrcode

        return qrcode

    # 登出健保卡狀態
    def logout_hc(self):
        service_path = "/api/hc/v1/Logout"  # 先登出健保卡狀態
        response = self._get_requests_response(service_path, "DELETE", {})

        try:
            return response.json()
        except Exception as e:
            print(f"❌ 處理登出健保卡回應時發生異常: {e}")
            return None

    def read_register_basic_data_by_vhc(self):
        system_utils.set_keyboard_layout("英文")

        if self.qrcode is None:
            self.qrcode = self._get_qrcode()

        service_path = "/api/hc/v1/VirtualHc/ReadBasic"
        data = {"token": self.qrcode}
        response = self._get_requests_response(service_path, "POST", data)
        # --- 修改點 1：攔截 None 回應 ---
        if response is None:
            print("⚠️ 虛擬健保卡 API 無回應 (請檢查元件狀態)")
            return False

        try:
            card_content = response.json()
            if card_content.get("statusCode") != 0:
                # 這裡可以考慮紀錄具體錯誤原因，例如：掃碼失效或 Token 過期
                print(
                    f"⚠️ 虛擬健保卡讀取失敗，錯誤代碼：{card_content.get('statusCode')}"
                )
                return False

            self.basic_data = {
                "card_no": card_content["cardId"],
                "name": card_content["name"],
                "patient_id": card_content["idNo"],
                "birthday": date_utils.nhi_date_to_west_date(card_content["birthday"]),
                "gender": patient_utils.get_gender(card_content["sex"]),
                "card_date": None,
                "cancel_mark": "1",
                "insured_code": card_content["identityStatus"],
                "insured_mark": cshis_utils.get_insured_mark(
                    card_content["identityStatus"]
                ),
                "card_valid_date": None,
                "card_available_count": 6,
                "new_born_date": None,
                "new_born_mark": None,
                "emg_phone": None,
            }
            return True

        except Exception as e:
            print(f"❌ 處理虛擬健保卡資料時發生異常: {e}")
            return False

    def get_card_status(self):
        available_count = None
        available_date = None
        hc_signature = self.get_hc_signature(service_type="01")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return None, None

        service_path = "/api/v1/BasicData/Register2"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )

        available_date = response.json()["cardValidity"]
        available_date = date_utils.nhi_date_to_west_date(
            response.json()["cardValidity"]
        )
        available_count = number_utils.get_integer(response.json()["treatmentCounter"])

        return available_date, available_count

    def get_emergent_tel(self):
        hc_signature = self.get_hc_signature(service_type="01")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/EmergentTel/Query"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )

        try:
            telephone = response.json()["tel"]
        except Exception:
            telephone = ""

        return telephone

    # 更新健保卡有效期限及可用次數
    def update_hc(self, show_message=True):
        hc_signature = self.get_hc_signature(service_type="04")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/HcContent/Update"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if show_message or error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保IC卡卡片內容更新")

        return error_code

    def read_critical_illness(self):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        if hpchc_signature is None or hpchc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/CriticalIllness/Query"

        data = {
            "clientRandom": hpchc_signature["clientRandom"],
            "hospitalId": hpchc_signature["hospitalId"],
            "samId": hpchc_signature["samId"],
            "signature": hpchc_signature["signature"],
            "hpcId": hpchc_signature["hpcId"],
            "hpcIdNo": hpchc_signature["hpcIdNo"],
            "hcId": hpchc_signature["hcId"],
            "hcIdNo": hpchc_signature["hcIdNo"],
            # 'format': hpchc_signature['format'],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]
        illness_data = response.json()["criticalIllnesses"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡讀取重大傷病")

        self.critical_illness_data = []
        for i in range(6):
            try:
                self.critical_illness_data.append(
                    {
                        "CI_CODE": illness_data[i]["ciCode"],
                        "CI_VALIDITY_START": illness_data[i]["validityStart"],
                        "CI_VALIDITY_END": illness_data[i]["validityEnd"],
                    }
                )
            except Exception:
                self.critical_illness_data.append(
                    {
                        "CI_CODE": "",
                        "CI_VALIDITY_START": "",
                        "CI_VALIDITY_END": "",
                    }
                )

        return True

    # 取得門診資料
    def read_treatment_no_need_hpc(self):
        title = "取得健保卡門診資料"
        message = '<font size="5" color="red"><b>正在取得健保卡門診資料中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(target=self.read_treatment_no_need_hpc_thread, args=(msg_queue,))
        t.start()
        (error_code, treatment_data) = msg_queue.get()
        msg_box.close()

        if error_code == 0:  # 取得資料成功
            self.treatment_data = treatment_data

    def read_treatment_no_need_hpc_thread(self, out_queue):
        hc_signature = self.get_hc_signature(service_type="01")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/Treatment/NoNeedHPC"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡讀取")
            return False

        treatment_data = cshis_utils.decode_cshis6_treatment_data(response.json())
        out_queue.put((error_code, treatment_data))

    # 取得門診資料
    def read_treatment_need_hpc(self):
        title = "取得健保卡診斷資料"
        message = '<font size="5" color="red"><b>正在取得健保卡診斷資料中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(target=self.read_treatment_need_hpc_thread, args=(msg_queue,))
        t.start()
        (error_code, disease_data) = msg_queue.get()
        msg_box.close()

        if error_code == 0:  # 取得資料成功
            self.disease_data = disease_data

    def get_api_status(self):
        service_path = "/api/common/v1/Status"
        data = {}
        response = self._get_requests_response(service_path, "GET", data)

        return response.json()["status"]

    def read_treatment_need_hpc_thread(self, out_queue):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        if hpchc_signature is None or hpchc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/Treatment/NeedHPC"
        data = {
            "clientRandom": hpchc_signature["clientRandom"],
            "hospitalId": hpchc_signature["hospitalId"],
            "samId": hpchc_signature["samId"],
            "signature": hpchc_signature["signature"],
            "hpcId": hpchc_signature["hpcId"],
            "hpcIdNo": hpchc_signature["hpcIdNo"],
            "hcId": hpchc_signature["hcId"],
            "hcIdNo": hpchc_signature["hcIdNo"],
            "format": "0",
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡讀取")
            return False

        disease_data = cshis_utils.decode_cshis6_disease_data(response.json())

        out_queue.put((error_code, disease_data))

    # 取得安全簽章
    def read_prescript_data(self):
        title = "取得健保卡處方資料"
        message = '<font size="5" color="red"><b>正在取得健保卡處方資料中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(target=self.read_prescript_data_thread, args=(msg_queue,))
        t.start()
        (error_code, prescript_data) = msg_queue.get()
        msg_box.close()

        if error_code == 0:  # 取得資料成功
            self.prescript_data = prescript_data

    def read_prescript_data_thread(self, out_queue):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        if hpchc_signature is None or hpchc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/Prescription/Query"
        data = {
            "clientRandom": hpchc_signature["clientRandom"],
            "hospitalId": hpchc_signature["hospitalId"],
            "samId": hpchc_signature["samId"],
            "signature": hpchc_signature["signature"],
            "hpcId": hpchc_signature["hpcId"],
            "hpcIdNo": hpchc_signature["hpcIdNo"],
            "hcId": hpchc_signature["hcId"],
            "hcIdNo": hpchc_signature["hcIdNo"],
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡讀取")
            return False

        prescriptions = response.json()["outpatientPrescriptions"]
        prescript_data = []
        for prescript in prescriptions:
            prescript_row = {
                "case_date": prescript["treatmentDateTime"],
                "prescript_type": prescript["treatmentItem"],
                "ins_code": prescript["treatmentItemCode"],
                "treat_position": prescript["treatmentPosition"],
                "usage": prescript["usage"],
                "pres_days": prescript["days"],
                "total_dosage": prescript["totalQuantity"],
                "remark": "",
            }
            prescript_data.append(prescript_row)

        out_queue.put((error_code, prescript_data))

    def get_cshis6_status(self):
        service_path = "/api/common/v1/Status"
        data = {}
        response = self._get_requests_response(service_path, "GET", data)

        return response.json()

    def get_seq_number_256_thread(
        self, out_queue, treat_item, baby_treat, treat_after_check
    ):
        hc_signature = self.get_hc_signature(service_type="03")
        # if self.ic_card_type == '虛擬健保卡':
        #     hc_signature = self.get_vhc_signature(service_type='03')
        # else:
        #     hc_signature = self.get_hc_signature(service_type='03')

        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/SequelNumber/Next"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
            "treatmentItem": treat_item,
            "babyTreatment": baby_treat,
            "afterCheck": treat_after_check,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        out_queue.put((error_code, response.json()))

    # 取得安全簽章
    def get_seq_number_256(self, treat_item, baby_treat, treat_after_check):
        title = "取得掛號安全簽章"
        message = '<font size="5" color="red"><b>健保讀卡機取得掛號安全簽章中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(
            target=self.get_seq_number_256_thread,
            args=(
                msg_queue,
                treat_item,
                baby_treat,
                treat_after_check,
            ),
        )
        t.start()
        (error_code, json_data) = msg_queue.get()
        msg_box.close()

        if error_code == 0:  # 取得安全簽章成功
            self.treat_data = cshis_utils.decode_cshis6_treat_data(json_data)

        return error_code

    def write_treatment_code_fee_thread(
        self,
        out_queue,
        registration_datetime,
        treat_after_check,
        disease_code1,
        disease_code2,
        disease_code3,
        disease_code4,
        share_fee,
    ):
        hc_signature = self.get_hc_signature(service_type="02")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/Treatment/WriteCode"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
            "treatmentDateTime": registration_datetime,
            "afterCheck": treat_after_check,
            "format": "2",
            "mainCode": disease_code1,
            "subCode1": disease_code2,
            "subCode2": disease_code3,
            "subCode3": disease_code4,
            "subCode4": "",
            "subCode5": "",
            "outpatientFee": share_fee,
            "sostFee": share_fee,
            "inpatientFee": 0,
            "inpatient30Fee": 0,
            "inpatient180Fee": 0,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        out_queue.put((error_code))

    # 就醫診療資料寫入作業
    def write_treatment_code_fee(
        self,
        registration_datetime,
        treat_after_check,
        disease_code1,
        disease_code2,
        disease_code3,
        disease_code4,
        share_fee,
    ):
        title = "寫入診察資料"
        message = '<font size="5" color="red"><b>健保讀卡機正在寫入診察資料中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(
            target=self.write_treatment_code_fee_thread,
            args=(
                msg_queue,
                registration_datetime,
                treat_after_check,
                disease_code1,
                disease_code2,
                disease_code3,
                disease_code4,
                share_fee,
            ),
        )
        t.start()
        (error_code) = msg_queue.get()
        msg_box.close()

        if error_code == 3209:
            error_code = 0

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡寫入診察資料")
            return False
        else:
            return True

    def write_multi_prescript_sign_thread(
        self, out_queue, registration_datetime, prescriptions
    ):
        hc_signature = self.get_hc_signature(service_type="02")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/Prescription/Write"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
            "treatmentDateTime": registration_datetime,
            "prescriptions": prescriptions,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]
        signature_items = response.json()["signatureItems"]
        hex_signature_items = response.json()["hexSignatureItems"]

        out_queue.put((error_code, signature_items, hex_signature_items))

    def write_multi_prescript_sign(self, registration_datetime, prescriptions):
        title = "取得處方簽章"
        message = '<font size="5" color="red"><b>健保讀卡機取得處方簽章中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(
            target=self.write_multi_prescript_sign_thread,
            args=(
                msg_queue,
                registration_datetime,
                prescriptions,
            ),
        )
        t.start()
        (error_code, prescript_sign_list, hex_prescript_sign_list) = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡取得處方簽章")
            return None

        return prescript_sign_list, hex_prescript_sign_list

    def return_seq_number_thread(self, out_queue, treat_date):
        hc_signature = self.get_hc_signature(service_type="03")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/SequelNumber/Rollback"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
            "treatmentDateTime": treat_date,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        out_queue.put(error_code)

    # IC退掛
    def return_seq_number(self, treat_date):
        if self.ic_card_type == "虛擬健保卡":
            if not self.reset_vhc_card():
                return

        title = "健保IC卡退掛"
        message = '<font size="5" color="red"><b>健保IC卡退掛中, 請稍後...</b></font>'
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=self.return_seq_number_thread, args=(msg_queue, treat_date))
        t.start()
        error_code = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡退掛")
            return False
        else:
            self.logout_hc()

            return True

    def upload_data_thread(self, out_queue, upload_type, xml, case_count):
        cshis_x = class_utils.get_cshisx(self.database, self.system_settings)

        api_status = self.get_api_status()
        sam_mode = api_status["sam"]["status"]
        if sam_mode != 2:  # 未完成sam認證
            self.verify_sam(show_message=False)

        sam_signature = self.get_sam_signature(service_type="30")
        if sam_signature["clientRandom"] is None:
            cshis_utils.show_ic_card_message(4050, "請求虛擬健保卡授權失敗")
            return False

        sam_id = sam_signature["samId"]
        hosp_id = sam_signature["hospitalId"]
        client_random = sam_signature["clientRandom"]
        signature = sam_signature["signature"]

        error_code, op_code = cshis_x.VNHI_Upload_cshis6(
            upload_type, sam_id, hosp_id, client_random, signature, xml, case_count
        )

        out_queue.put((error_code, op_code))

    # IC卡資料上傳
    def upload_data(self, upload_type, xml, case_count):
        title = "健保IC卡資料上傳"
        message = (
            '<font size="5" color="red"><b>健保IC卡資料上傳中, 請稍後...</b></font>'
        )
        hint = "正在與與健保IDC資訊中心連線, 會花費一些時間."
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()

        QtCore.QCoreApplication.processEvents()
        t = Thread(
            target=self.upload_data_thread,
            args=(msg_queue, upload_type, xml, case_count),
        )
        t.start()
        (error_code, json) = msg_queue.get()
        msg_box.close()

        if error_code == "0000":
            op_code = json
            json = {
                "statusCode": 0,
                "uploadDateTime": op_code[:14],
                "receiveDateTime": op_code[:14],
                "hospitalId": op_code[20:30],
                "samId": op_code[30:42],
            }
        elif error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡資料上傳")
            return None

        return json["statusCode"], json

    # ic卡寫卡
    def write_ic_card(
        self,
        write_type,
        patient_key,
        course,
        share_type,
        treat_after_check=None,
        treat_type=None,
    ):
        treat_item = cshis_utils.get_treat_item(
            course, share_type, treat_type=treat_type
        )

        if not self.insert_correct_ic_card(patient_key):
            return False

        if self.ic_card_type == "虛擬健保卡":
            self.verify_vhc_card()
        else:
            _, available_count = self.get_card_status()
            if available_count is None:
                return False

            if available_count <= 0:
                self.update_hc(False)

        if write_type in ["全部", "掛號寫卡"]:
            error_code = self.get_seq_number_256(treat_item, " ", treat_after_check)
            if error_code != 0:
                if error_code == 5003:  # 卡片過期
                    self.update_hc(False)
                    error_code = self.get_seq_number_256(
                        treat_item, " ", treat_after_check
                    )
                    if error_code != 0:
                        cshis_utils.show_ic_card_message(
                            error_code, "健保卡取得就醫序號"
                        )
                        return False
                else:
                    cshis_utils.show_ic_card_message(error_code, "健保卡取得就醫序號")
                    return False

        return self

    # ic卡寫卡
    def write_ic_card_abnormal(self, patient_id):
        sam_signature = self.get_sam_signature(service_type="03")
        if sam_signature["clientRandom"] is None:
            cshis_utils.show_ic_card_message(4050, "請求虛擬健保卡授權失敗")
            return False

        service_path = "/api/v1/TreatmentNumber/NoCard"
        data = {
            "clientRandom": sam_signature["clientRandom"],
            "hospitalId": sam_signature["hospitalId"],
            "samId": sam_signature["samId"],
            "signature": sam_signature["signature"],
            "patientId": patient_id,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(
                error_code, "健保卡異常時取得就醫識別碼失敗"
            )
            return None

        self.treat_data = cshis_utils.decode_cshis6_no_ic_card_treat_data(
            response.json()
        )

        return self

    # 單獨取得就醫識別碼
    def get_identifier(self, registration_datetime):
        hc_signature = self.get_hc_signature(service_type="03")
        if hc_signature is None or hc_signature["clientRandom"] is None:
            return False

        service_path = "/api/v1/TreatmentNumber/Card"
        data = {
            "clientRandom": hc_signature["clientRandom"],
            "hospitalId": hc_signature["hospitalId"],
            "samId": hc_signature["samId"],
            "signature": hc_signature["signature"],
            "hcId": hc_signature["hcId"],
            "hcIdNo": hc_signature["hcIdNo"],
            "treatmentDateTime": registration_datetime,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "健保卡取得就醫識別碼失敗")
            return None

        identifier = response.json()["treatmentNumber"]

        return identifier

    def insert_correct_ic_card(self, patient_key):
        try:
            if not self.read_basic_data():
                return False
        except AttributeError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("無法使用健保卡")
            msg_box.setText(
                """
                <font size="5" color="red">
                  <b>無法使用讀卡機, 請改掛異常卡序或欠卡<br>
                </font>
                """
            )
            msg_box.setInformativeText("請確定讀卡機使用正常")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return False

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("病患資料有誤")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                        <b>找不到病歷號{patient_key}, 請重新插卡.</b>
                    </font>
                """
            )
            msg_box.setInformativeText("請確定插入的健保卡是否為此病患所有.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()

            return False

        row = rows[0]
        patient_id = string_utils.xstr(row["ID"])
        patient_name = string_utils.xstr(row["Name"])
        if patient_id != "" and patient_id != self.basic_data["patient_id"]:
            ic_card_name = self.basic_data["name"]
            ic_card_id = self.basic_data["patient_id"]
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("健保卡身分不符")
            msg_box.setText(f"""
                <font size="5" color="red">
                    <b>此健保卡基本資料為<br>
                </font>
                <font size="5" color="blue">
                  {ic_card_name}: {ic_card_id}<br>
                </font>
                <font size="5" color="red">
                  與現行掛號病患<br>
                </font>
                <font size="5" color="blue">
                  {patient_name}: {patient_id}<br>
                </font>
                <font size="5" color="red">
                  身分證號不相符, 請檢查是否插入錯誤的健保卡.</b>
                </font>
            """)
            msg_box.setInformativeText("請確定插入的健保卡是否為此病患所有.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()

            return False

        if patient_id == "":
            sql = f'''
                UPDATE patient
                SET
                    ID = "{patient_id}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if string_utils.xstr(row["CardNo"]) == "":
            card_no = self.basic_data["card_no"]
            sql = f'''
                UPDATE patient
                SET
                    CardNo = "{card_no}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if row["Birthday"] != self.basic_data["birthday"]:
            birthday = self.basic_data["birthday"]
            sql = f'''
                UPDATE patient
                SET
                    Birthday = "{birthday}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        return True

    def reset_vhc_card(self):
        if self.qrcode is None:
            self.qrcode = self._get_qrcode()

        self.read_register_basic_data()
        if not self.verify_vhc_card():
            return False
        else:
            return True

    # ic 醫令寫卡
    def write_ic_medical_record(self, case_key, treat_after_check, reset_vhc_card=True):
        if self.ic_card_type == "虛擬健保卡" and reset_vhc_card:
            if not self.reset_vhc_card():
                return

        if not self.write_ic_treatment(case_key, treat_after_check):  # 寫入病名, 費用
            return

        self.write_prescript_signature(case_key)  # 寫入醫令簽章
        case_utils.update_xml(
            self.database,
            "cases",
            "Security",
            "prescript_sign_time",
            date_utils.now_to_str(),
            "CaseKey",
            case_key,
        )  # 更新健保寫卡資料

        self.logout_hc()

    def rewrite_ic_prescript(self, case_key):
        if self.ic_card_type == "虛擬健保卡":
            if not self.reset_vhc_card():
                return

        self.write_prescript_signature(case_key)  # 寫入醫令簽章
        case_utils.update_xml(
            self.database,
            "cases",
            "Security",
            "prescript_sign_time",
            date_utils.now_to_str(),
            "CaseKey",
            case_key,
        )  # 更新健保寫卡資料

        self.logout_hc()

    # 寫入藥品處方簽章
    def write_medicine_signature(
        self, case_row, patient_row, prescript_rows, dosage_row
    ):
        ic_card_time = case_utils.extract_security_xml(case_row["Security"], "寫卡時間")
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(
            ic_card_time
        )  # 就診日期時間 13 bytes: EEEmmddHHMMSS

        try:
            usage = prescript_utils.get_usage_code(
                dosage_row["Packages"]
            ) + prescript_utils.get_instruction_code(dosage_row["Instruction"])
        except Exception:
            usage = ""

        days = number_utils.get_integer(dosage_row["Days"])

        prescriptions = []
        for row in prescript_rows:
            order_type = (
                "1"  # 醫令類別 1 bytes: 1-非長期藥品 2-長期藥品 3-診療 4-特殊材料
            )
            ins_code = string_utils.xstr(row["InsCode"])  # 診療項目代號 12 bytes
            treat_position = ""  # 診療部位 6 bytes
            try:
                total_dosage = round(
                    number_utils.get_float(row["Dosage"])
                    * number_utils.get_integer(dosage_row["Days"]),
                    2,
                )
            except TypeError:
                total_dosage = 0

            deliver = "01"  # 交付處方註記 2 bytes: 01-自行調劑 02-交付調劑 03-自行執行

            prescriptions.append(
                {
                    "days": string_utils.xstr(days),
                    "deliveryNotes": deliver,
                    "totalQuantity": f"{total_dosage:.2f}",
                    "treatmentDateTime": reg_datetime,
                    "treatmentItem": order_type,
                    "treatmentItemCode": ins_code,
                    "treatmentPosition": treat_position,
                    "usage": usage,
                }
            )

        prescript_sign_list, hex_prescript_sign_list = self.write_multi_prescript_sign(
            reg_datetime, prescriptions
        )

        if hex_prescript_sign_list is None:
            return

        for row, prescript_sign in zip(prescript_rows, hex_prescript_sign_list):
            prescript_key = row["PrescriptKey"]
            sql = f"""
                DELETE FROM presextend
                WHERE
                    PrescriptKey = {prescript_key} AND
                    ExtendType = "處方簽章"
            """
            self.database.exec_sql(sql)
            fields = [
                "PrescriptKey",
                "ExtendType",
                "Content",
            ]
            data = [
                row["PrescriptKey"],
                "處方簽章",
                prescript_sign,
            ]
            self.database.insert_record("presextend", fields, data)

        ###################### 舊的簽章轉換程式　########################
        if prescript_sign_list is None:
            return

        for row, prescript_sign in zip(prescript_rows, prescript_sign_list):
            binary_data = base64.b64decode(prescript_sign)
            hex_string = binary_data.hex().upper()
            prescript_sign = hex_string

        #     prescript_key = row['PrescriptKey']
        #     sql = f'''
        #         DELETE FROM presextend
        #         WHERE
        #             PrescriptKey = {prescript_key} AND
        #             ExtendType = "處方簽章"
        #     '''
        #     self.database.exec_sql(sql)
        #     fields = [
        #         'PrescriptKey', 'ExtendType', 'Content',
        #     ]
        #     data = [
        #         row['PrescriptKey'], '處方簽章', prescript_sign,
        #     ]
        #     self.database.insert_record('presextend', fields, data)

    # 寫入處置處方簽章
    def write_treat_signature(self, case_row, dosage_row, patient_row):
        ic_card_time = case_utils.extract_security_xml(case_row["Security"], "寫卡時間")
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(
            ic_card_time
        )  # 就診日期時間 13 bytes: EEEmmddHHMMSS

        treat_code = nhi_utils.get_treat_code(self.database, case_row["CaseKey"])
        usage = ""  # 處置免填
        days = 0
        total_dosage = 1

        order_type = "3"  # 醫令類別 1 bytes: 1-非長期藥品 2-長期藥品 3-診療 4-特殊材料
        treat_code = f"{treat_code:<12}"  # 診療項目代號 12 bytes
        treat_position = " " * 6  # 診療部位 6 bytes
        usage = f"{usage:<18}"  # 用法 18 bytes
        days = f"{days:0>2}"  # 天數 2 bytes: 00
        total_dosage = f"{total_dosage:0>7}"  # 總量 7 bytes: 00000.0
        deliver = "03"  # 交付處方註記 2 bytes: 01-自行調劑 02-交付調劑 03-自行執行

        prescription = [
            {
                "days": string_utils.xstr(days),
                "deliveryNotes": deliver,
                "totalQuantity": string_utils.xstr(total_dosage),
                "treatmentDateTime": reg_datetime,
                "treatmentItem": order_type,
                "treatmentItemCode": treat_code,
                "treatmentPosition": treat_position,
                "usage": usage,
            }
        ]

        treat_sign, hex_treat_sign = self.write_multi_prescript_sign(
            reg_datetime, prescription
        )

        if len(treat_sign) <= 0:
            return

        treat_sign = hex_treat_sign[0]

        case_key = case_row["CaseKey"]
        self.database.exec_sql(f"""
            DELETE FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
        """)
        fields = [
            "PrescriptKey",
            "ExtendType",
            "Content",
        ]
        data = [
            case_row["CaseKey"],
            "處置簽章",
            treat_sign,
        ]
        self.database.insert_record("presextend", fields, data)

        # if len(treat_sign) <= 0:
        #     return

        # treat_sign = treat_sign[0]
        # binary_data = base64.b64decode(treat_sign)
        # hex_string = binary_data.hex().upper()
        # treat_sign = hex_string

        # case_key = case_row['CaseKey']
        # self.database.exec_sql(f'''
        #     DELETE FROM presextend
        #     WHERE
        #         PrescriptKey = {case_key} AND
        #         ExtendType = "處置簽章"
        # ''')
        # fields = [
        #     'PrescriptKey', 'ExtendType', 'Content',
        # ]
        # data = [
        #     case_row['CaseKey'], '處置簽章', treat_sign,
        # ]
        # self.database.insert_record('presextend', fields, data)

    # 寫入病名及費用
    def write_ic_treatment(self, case_key, treat_after_check):
        sql = f"""
            SELECT
                PatientKey, DiseaseCode1, DiseaseCode2, DiseaseCode3, DiseaseCode4,
                DiagShareFee, DrugShareFee, InsTotalFee, Security
            FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        case_row = rows[0]
        patient_key = case_row["PatientKey"]

        sql = f"""
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        patient_row = self.database.select_record(sql)[0]

        ic_card_time = case_utils.extract_security_xml(case_row["Security"], "寫卡時間")
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(ic_card_time)
        patient_id = string_utils.xstr(patient_row["ID"])
        patient_birthday = string_utils.xstr(patient_row["Birthday"])

        if patient_id == "" or patient_birthday == "":
            patient_id, patient_birthday = self._update_patient(patient_key)

        disease_code1 = string_utils.xstr(case_row["DiseaseCode1"])
        disease_code2 = string_utils.xstr(case_row["DiseaseCode2"])
        disease_code3 = string_utils.xstr(case_row["DiseaseCode3"])
        disease_code4 = string_utils.xstr(case_row["DiseaseCode4"])

        diag_share_fee = number_utils.get_integer(case_row["DiagShareFee"])
        drug_share_fee = number_utils.get_integer(case_row["DrugShareFee"])
        share_fee = diag_share_fee + drug_share_fee

        if not self.write_treatment_code_fee(
            reg_datetime,
            treat_after_check,
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            share_fee,
        ):
            return False
        else:
            return True

    # 寫入處方簽章
    def write_prescript_signature(self, case_key):
        sql = f"""
            SELECT CaseKey, PatientKey, Treatment, Security FROM cases
            WHERE
                CaseKey = {case_key}
        """
        case_row = self.database.select_record(sql)[0]

        sql = f"""
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        """
        rows = self.database.select_record(sql)
        dosage_row = rows[0] if len(rows) > 0 else None

        patient_key = case_row["PatientKey"]
        sql = f"""
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        patient_row = self.database.select_record(sql)[0]

        sql = f"""
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                MedicineType NOT IN ("穴道", "處置") AND
                InsCode IS NOT NULL AND LENGTH(InsCode) > 0
            ORDER BY PrescriptNo, PrescriptKey
        """
        prescript_rows = self.database.select_record(sql)

        if string_utils.xstr(case_row["Treatment"]) in nhi_utils.INS_TREAT:
            self.write_treat_signature(case_row, dosage_row, patient_row)

        if len(prescript_rows) > 0:
            self.write_medicine_signature(
                case_row, patient_row, prescript_rows, dosage_row
            )

    def request_token(self, patient_id):
        sam_signature = self.get_sam_signature(service_type="01")
        if sam_signature["clientRandom"] is None:
            cshis_utils.show_ic_card_message(4050, "請求虛擬健保卡授權失敗")
            return False

        service_path = "/api/v1/TeleMedicine/RequestToken"
        data = {
            "clientRandom": sam_signature["clientRandom"],
            "hospitalId": sam_signature["hospitalId"],
            "samId": sam_signature["samId"],
            "signature": sam_signature["signature"],
            "patientId": patient_id,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "請求虛擬健保卡授權失敗")
            return None

        access_token = response.json()["accessToken"]

        return access_token

    def get_response_token(self, access_token):
        sam_signature = self.get_sam_signature(service_type="01")
        if sam_signature["clientRandom"] is None:
            cshis_utils.show_ic_card_message(4050, "請求虛擬健保卡授權失敗")
            return False

        service_path = "/api/v1/TeleMedicine/ResponseToken"
        data = {
            "clientRandom": sam_signature["clientRandom"],
            "hospitalId": sam_signature["hospitalId"],
            "samId": sam_signature["samId"],
            "signature": sam_signature["signature"],
            "accessToken": access_token,
        }
        response = self._get_requests_response(
            service_path, "POST", data, local_url=False
        )
        error_code = response.json()["statusCode"]

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, "請求虛擬健保卡序號失敗")
            return None

        qrcode = response.json()["virtualCardToken"]

        return qrcode

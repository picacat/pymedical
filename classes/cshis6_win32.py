import base64
import copy
import datetime
import os
import time
from queue import Empty, Queue
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

# 若專案已有統一的 log 機制, 這裡會自動接上; 沒有的話走檔案備援
try:
    from libs import log_utils
except ImportError:
    log_utils = None

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(os.path.dirname(CURRENT_DIR), "cshis.log")
LOG_MAX_BYTES = 5 * 1024 * 1024


# NHI_TEST_URL = 'https://medvpndct.nhi.gov.tw'
# NHI_URL = 'https://medvpndc.nhi.gov.tw'

LOCAL_URL = "https://localhost:5066"
NHI_URL = "https://medvpndc.nhi.gov.tw"
NHI_TEST_URL = "https://medvpndct.nhi.gov.tw"  # 測試用

HEADERS = {
    "Content-Type": "application/json",  # 根據 API 要求的 Content-Type 設定
}

# 本機主控台元件回應快, 健保署 IDC 常常慢; 分開設定避免內層先逾時
LOCAL_TIMEOUT = 10
NHI_TIMEOUT = 25

# 本機主控台元件用自簽憑證, 只能關閉驗證;
# 健保 VPN 待確認憑證鏈可通過後改為 True (改之前請先在測試環境驗證)
VERIFY_NHI_SSL = False

# 讀卡機狀態快取秒數: 夠短不會漏掉插拔卡, 夠長可以省掉同一流程內的重複往返
STATUS_CACHE_SECONDS = 0.5

# 模組載入時關閉一次即可, 不需要每次呼叫都關
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def save_log(message):
    """統一的記錄入口

    讀卡機是整套系統最常出狀況的元件, 打包成 exe 或用 pythonw 執行時
    print() 完全看不到, 所以一律寫進 log.
    """
    text = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {message}"

    if log_utils is not None and hasattr(log_utils, "save_log"):
        try:
            log_utils.save_log(text)
            return
        except Exception:
            pass

    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            backup_file = LOG_FILE + ".1"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(LOG_FILE, backup_file)

        with open(LOG_FILE, "a", encoding="utf8") as log_file:
            log_file.write(text + "\n")
    except Exception:
        print(text)


class _MessageRelay(QtCore.QObject):
    """把工作執行緒的訊息請求轉回主執行緒顯示

    Qt 規定 widget 只能在主執行緒建立與操作. 原本各個 *_thread 直接呼叫
    _show_message() 建立 QMessageBox, 是偶發當機的來源.
    QueuedConnection 會把呼叫排進主執行緒的事件迴圈.
    """

    message = QtCore.pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.message.connect(self._on_message, QtCore.Qt.QueuedConnection)

    @staticmethod
    def _on_message(error_code, operation):
        cshis_utils.show_ic_card_message(error_code, operation)


# 健保ICD卡 讀卡機控制軟體6.0 2026-07-14
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

        # 用 deepcopy, 不要直接綁到模組層級的 dict;
        # 否則任何一次寫入都會污染全域預設值, 影響所有 CSHIS 實例
        self.basic_data = self._default_basic_data()
        self.treat_data = copy.deepcopy(cshis_utils.TREAT_DATA)
        self.treatment_data = copy.deepcopy(cshis_utils.TREATMENT_DATA)
        self.disease_data = copy.deepcopy(cshis_utils.DISEASE_DATA)
        self.critical_illness_data = []
        self.prescript_data = []
        self.silent_mode = False  # kiosk 無人值守模式: 不顯示阻塞對話框

        self._status_cache = None
        self._status_time = 0.0

        self._relay = _MessageRelay()
        app = QtCore.QCoreApplication.instance()
        if app is not None and self._relay.thread() is not app.thread():
            self._relay.moveToThread(app.thread())

    def __del__(self):
        pass

    # ------------------------------------------------------------------
    # 執行緒與訊息
    # ------------------------------------------------------------------

    @staticmethod
    def _is_main_thread():
        app = QtCore.QCoreApplication.instance()
        if app is None:
            return True

        return QtCore.QThread.currentThread() is app.thread()

    def _show_message(self, error_code, operation):
        save_log(f"[{operation}] error_code={error_code}")

        if self.silent_mode:
            return

        # 不論在哪個執行緒呼叫, 一律排進主執行緒顯示
        self._relay.message.emit(error_code, operation)

    @staticmethod
    def _wait_queue(msg_queue, timeout=30):
        """等待 worker 結果, 期間保持 UI 有回應

        原本用 msg_queue.get(timeout=30) 會讓主執行緒完全停止處理事件,
        「請稍後...」對話框畫不出來, Windows 判定程式沒有回應而蒙上白色.
        """
        deadline = time.monotonic() + timeout
        app = QtCore.QCoreApplication.instance()

        while time.monotonic() < deadline:
            try:
                return msg_queue.get_nowait()
            except Empty:
                if app is not None:
                    app.processEvents()

                time.sleep(0.02)

        raise Empty

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

        if operation and not self.silent_mode and self._is_main_thread():
            msg_box = self._message_box("健保讀卡機作業", args[1], args[2])
            msg_box.show()

        msg_queue = Queue()
        t = Thread(target=nhi_thread, args=(msg_queue,), daemon=True)
        t.start()
        try:
            error_code = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1  # 設定一個錯誤碼，表示逾時
            save_log(f"健保讀卡機作業逾時: {operation}")

        if msg_box:
            msg_box.close()
            msg_box.deleteLater()

        if error_code != 0 or show_warning:
            self._show_message(error_code, operation)

        return error_code

    @staticmethod
    def _message_box(title, message, hint):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setInformativeText(hint)
        msg_box.setStandardButtons(QMessageBox.NoButton)

        return msg_box

    def _show_wait_box(self, title, message, hint):
        """顯示等待中的訊息盒; 非主執行緒或 kiosk 模式一律不顯示"""
        if self.silent_mode or not self._is_main_thread():
            return None

        msg_box = self._message_box(title, message, hint)
        msg_box.show()

        return msg_box

    @staticmethod
    def _close_wait_box(msg_box):
        if msg_box is None:
            return

        msg_box.close()
        msg_box.deleteLater()

    # ------------------------------------------------------------------
    # 網路
    # ------------------------------------------------------------------

    def _get_requests_response(self, service_path, request_type, data, local_url=True):
        if self.system_settings.field("使用測試環境") == "Y":
            nhi_url = NHI_TEST_URL
        else:
            nhi_url = NHI_URL

        # 主控台元件預設聆聽 5066 通訊埠
        url = (LOCAL_URL if local_url else nhi_url) + service_path
        timeout = LOCAL_TIMEOUT if local_url else NHI_TIMEOUT
        verify = False if local_url else VERIFY_NHI_SSL

        try:
            response = requests.request(
                method=request_type,
                url=url,
                json=data,
                headers=HEADERS,
                verify=verify,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except Exception as e:
            save_log(f"API 呼叫失敗 {request_type} {url}: {e}")
            return None

    def _get_json(self, service_path, request_type, data, local_url=True):
        """統一的 JSON 取得方法, 失敗時回傳 None"""
        response = self._get_requests_response(
            service_path, request_type, data, local_url=local_url
        )
        if response is None:
            return None

        try:
            return response.json()
        except ValueError as e:
            save_log(f"JSON 解析失敗: {service_path} - {e}")
            return None

    @staticmethod
    def get_error_code(response):
        if response is None:
            return -1

        try:
            res_data = response.json()
            error_code = res_data.get("statusCode", -1)
        except Exception:
            return -1

        return error_code

    @staticmethod
    def _signature_data(signature, **extra):
        """把簽章資料展開成 API 需要的欄位, 缺任一必要欄位時回傳 None

        原本各處直接用 signature["clientRandom"] 取值, 健保署沒回這個 key
        時連檢查那一行自己都會 KeyError.
        """
        required = ("clientRandom", "hospitalId", "samId", "signature")
        if signature is None:
            return None

        for key in required:
            if signature.get(key) is None:
                save_log(f"簽章資料缺少欄位 {key}: {signature}")
                return None

        data = {key: signature[key] for key in required}
        for key in ("hcId", "hcIdNo", "hpcId", "hpcIdNo"):
            if signature.get(key) is not None:
                data[key] = signature[key]

        data.update(extra)

        return data

    # ------------------------------------------------------------------
    # 讀卡機狀態
    # ------------------------------------------------------------------

    def get_cshis6_status(self):
        service_path = "/api/common/v1/Status"

        return self._get_json(service_path, "GET", {})

    def _invalidate_status(self):
        self._status_cache = None
        self._status_time = 0.0

    def get_api_status(self, max_age=STATUS_CACHE_SECONDS):
        """取得讀卡機/卡片狀態

        主控台元件離線時回傳安全的預設狀態, 讓呼叫端走
        「未初始化 / 未認證 / 未置卡」的流程, 而不是直接炸掉.

        回傳的 dict 本身就含三張卡, 取用方式是
        get_api_status()["hpc"]["status"], 不是 get_api_status("hpc").
        """
        now = time.monotonic()
        if self._status_cache is not None and now - self._status_time < max_age:
            return self._status_cache

        res_data = self.get_cshis6_status()
        if res_data is None or "status" not in res_data:
            status = {
                "initialized": False,
                "sam": {"status": 0},
                "hpc": {"status": 0},
                "hc": {"status": 0},
            }
        else:
            status = res_data["status"]

        self._status_cache = status
        self._status_time = now

        return status

    # ------------------------------------------------------------------
    # 初始化 / 結束
    # ------------------------------------------------------------------

    def get_com_port(self):
        if self.reader_type == "健保讀卡機":
            com_port = f"COM{self.com_port}"
        else:
            com_port = None

        return com_port

    def init_cshis6(self):
        if self.get_api_status()["initialized"]:
            self.finalize_cshis6()

        service_path = "/api/common/v1/Initial"
        data = {}

        if self.sam_id not in ["", None]:
            data = {"name": self.sam_id}
        else:
            com_port = self.get_com_port()
            if com_port is not None:
                data = {"name": com_port}

        res_data = self._get_json(service_path, "POST", data)
        self._invalidate_status()
        if res_data is None:
            return -1

        return_code = res_data.get("statusCode", -1)
        if return_code == 1001:  # 已經初始化過了
            return_code = 0

        return return_code

    def finalize_cshis6(self):
        service_path = "/api/common/v1/Finalize"

        res_data = self._get_json(service_path, "POST", {})
        self._invalidate_status()
        if res_data is None:
            return -1

        return_code = res_data.get("statusCode", -1)
        if return_code == 1001:
            return_code = 0

        return return_code

    def activate_reader_app(self):
        # init_cshis6() 內部已經會檢查並 finalize, 這裡不需要再做一次
        return self.init_cshis6()

    def deactivate_reader_app(self):
        if self.get_api_status()["initialized"]:
            return self.finalize_cshis6()

        return 0

    def reset_reader(self, show_message=True):
        self.finalize_cshis6()
        error_code = self.init_cshis6()
        if show_message:
            self._show_message(error_code, "讀卡機重新啟動")

        return error_code

    # ------------------------------------------------------------------
    # 安全模組卡 (SAM)
    # ------------------------------------------------------------------

    def _verify_sam_no_ui(self):
        """純 API 的 SAM 認證, 不產生任何 widget, 工作執行緒可安全呼叫"""
        self.init_cshis6()

        if self.get_api_status(max_age=0)["sam"]["status"] == 2:  # 已經認證過了
            return 0

        service_path = "/api/sam/v1/Verification"
        res_data = self._get_json(service_path, "POST", {})
        self._invalidate_status()

        return res_data.get("statusCode", -1) if res_data else -1

    def verify_sam_thread(self, out_queue):
        out_queue.put(self._verify_sam_no_ui())

    def verify_sam(self, show_message=True):
        """有 UI 的 SAM 認證, 只能在主執行緒呼叫"""
        if not self._is_main_thread():
            return self._verify_sam_no_ui()

        error_code = self.do_thread(
            self.verify_sam_thread,
            "健保讀卡機安全模組卡認證",
            '<font size="5" color="red"><b>健保讀卡機安全模組卡認證中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
            show_message,
        )

        return error_code

    def _ensure_sam_verified(self):
        """確保 SAM 已認證; 自動依執行緒選擇有 UI / 無 UI 的路徑"""
        if self.get_api_status()["sam"]["status"] == 2:
            return 0

        if self._is_main_thread():
            return self.verify_sam(show_message=False)

        return self._verify_sam_no_ui()

    # ------------------------------------------------------------------
    # 健保卡 (HC) 密碼
    # ------------------------------------------------------------------

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
            self._show_message(5109, "健保IC卡密碼驗證")
            return 5109

        pin = input_dialog.textValue()
        service_path = "/api/hc/v1/Pin"
        data = {"pin": pin}

        res_data = self._get_json(service_path, "POST", data)
        error_code = res_data.get("statusCode", -1) if res_data else -1
        self._show_message(error_code, "健保IC卡密碼驗證")

        return error_code

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
            self._show_message(5109, "健保IC卡密碼設定")
            return 5109

        pin = input_dialog.textValue()
        service_path = "/api/hc/v1/Pin"
        data = {"newPin": pin}

        res_data = self._get_json(service_path, "PUT", data)
        error_code = res_data.get("statusCode", -1) if res_data else -1
        self._show_message(error_code, "健保IC卡密碼設定")

        return error_code

    def disable_hc_pin(self):
        service_path = "/api/hc/v1/Pin"

        res_data = self._get_json(service_path, "DELETE", {})
        error_code = res_data.get("statusCode", -1) if res_data else -1
        self._show_message(error_code, "健保IC卡密碼解除")

        return error_code

    # 登出健保卡狀態
    def logout_hc(self):
        service_path = "/api/hc/v1/Logout"  # 先登出健保卡狀態

        res_data = self._get_json(service_path, "DELETE", {})
        self._invalidate_status()

        return res_data

    # ------------------------------------------------------------------
    # 醫事人員卡 (HPC)
    # ------------------------------------------------------------------

    def logout_hpc(self):
        service_path = "/api/hpc/v1/Logout"

        res_data = self._get_json(service_path, "DELETE", {})
        self._invalidate_status()

        return res_data.get("statusCode", -1) if res_data else -1

    # 驗證醫事人員卡
    def verify_hpc_pin(self, show_message=True):
        """一律回傳 error_code (0 表示成功), 不再回傳 None"""
        api_status = self.get_api_status()
        hpc_mode = api_status["hpc"]["status"]
        if hpc_mode == 3:  # 已經認證過了
            if show_message:
                self._show_message(0, "醫事人員卡密碼驗證")

            return 0

        if hpc_mode == 0:  # 未置入卡片
            self.logout_hpc()
            self._show_message(1102, "讀取醫事人員卡")
            return 1102

        self._ensure_sam_verified()

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
                self._show_message(5109, "醫事人員卡密碼驗證")
                return 5109

            pin = input_dialog.textValue()
        else:
            pin = "000000"

        data = {"pin": pin}
        service_path = "/api/hpc/v1/Verification/Hpc"
        res_data = self._get_json(service_path, "POST", data)
        self._invalidate_status()

        error_code = res_data.get("statusCode", -1) if res_data else -1

        if show_message or error_code != 0:
            self._show_message(error_code, "醫事人員卡密碼驗證")

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
            # verify_hpc_pin 內部未置卡/取消時已經顯示過, 這裡不再重複
            if error_code not in [1102, 5109]:
                self._show_message(error_code, "醫事人員卡密碼驗證")

            return error_code

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
            self._show_message(5109, "醫事人員卡密碼設定")
            return 5109

        pin = input_dialog.textValue()
        service_path = "/api/hpc/v1/Pin"
        data = {"newPin": pin}

        res_data = self._get_json(service_path, "POST", data)
        error_code = res_data.get("statusCode", -1) if res_data else -1
        self._show_message(error_code, "醫事人員卡密碼設定")

        return error_code

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
            self._show_message(5109, "醫事人員卡PUK碼解鎖")
            return 5109

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
            self._show_message(5109, "醫事人員卡密碼設定")
            return 5109

        new_pin = input_dialog.textValue()

        service_path = "/api/hpc/v1/Pin"
        data = {
            "puk": puk,
            "newPin": new_pin,
        }

        res_data = self._get_json(service_path, "PUT", data)
        self._invalidate_status()
        error_code = res_data.get("statusCode", -1) if res_data else -1
        self._show_message(error_code, "醫事人員卡解鎖")

        return error_code

    # ------------------------------------------------------------------
    # 簽章
    # ------------------------------------------------------------------

    def get_sam_signature(self, service_type):
        service_path = "/api/sam/v1/Signature"
        data = {"serviceType": service_type}

        return self._get_json(service_path, "POST", data)

    def get_hc_signature(self, service_type, show_warning=True):
        """show_warning 只控制要不要跳訊息, 失敗一律回傳 None"""
        service_path = "/api/hc/v1/Signature/Hc"
        data = {"serviceType": service_type}

        res_data = self._get_json(service_path, "POST", data)
        if res_data is None:
            if show_warning:
                self._show_message(-1, "讀取健保卡簽章")

            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            if show_warning:
                self._show_message(error_code, "讀取健保卡簽章")

            return None

        return res_data

    def get_hpc_signature(self, service_type):
        api_status = self.get_api_status()
        if api_status["hpc"]["status"] == 0:  # 未置入卡片
            self._show_message(1102, "讀取醫事人員卡簽章")
            return None

        self._ensure_sam_verified()

        service_path = "/api/hpc/v1/Signature"
        data = {"serviceType": service_type}

        res_data = self._get_json(service_path, "POST", data)
        if res_data is None:
            self._show_message(-1, "讀取醫事人員卡簽章")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "讀取醫事人員卡簽章")
            return None

        return res_data

    def get_hpchc_signature(self, service_type):
        api_status = self.get_api_status()
        if api_status["hc"]["status"] == 0:  # 健保卡未置入
            self._show_message(1102, "讀取健保卡")
            return None

        if api_status["hpc"]["status"] != 3:  # 醫事人員卡未認證
            self._show_message(1402, "讀取醫事人員卡簽章")
            return None

        self._ensure_sam_verified()

        service_path = "/api/hc/v1/Signature/HpcHc"
        data = {"serviceType": service_type}

        res_data = self._get_json(service_path, "POST", data)
        if res_data is None:
            self._show_message(4061, "讀取三卡簽章")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "讀取三卡簽章")
            return None

        return res_data

    # ------------------------------------------------------------------
    # 基本資料
    # ------------------------------------------------------------------

    @staticmethod
    def _default_basic_data():
        return copy.deepcopy(cshis_utils.BASIC_DATA)

    def _reset_basic_data(self):
        """讀卡失敗時務必清空, 否則會殘留上一位病人的資料"""
        self.basic_data = self._default_basic_data()

    def read_basic_data(self, show_message=True):
        self.logout_hc()

        if self.ic_card_type == "虛擬健保卡":
            return self.read_register_basic_data_by_vhc()

        hc_signature = self.get_hc_signature(
            service_type="01", show_warning=show_message
        )
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            self._reset_basic_data()
            return False

        service_path = "/api/v1/BasicData/Query"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._reset_basic_data()
            if show_message:
                self._show_message(-1, "讀取健保卡基本資料")

            return False

        self.basic_data = cshis_utils.decode_cshis6_basic_data(res_data)
        self.basic_data["emg_phone"] = self.get_emergent_tel()

        return True

    def read_register_basic_data(self, show_warning=True):
        self.logout_hc()

        if self.ic_card_type == "虛擬健保卡":
            return self.read_register_basic_data_by_vhc()

        hc_signature = self.get_hc_signature(
            service_type="01", show_warning=show_warning
        )
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            self._reset_basic_data()
            return False

        service_path = "/api/v1/BasicData/Register"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._reset_basic_data()
            if show_warning:
                self._show_message(-1, "讀取健保卡基本資料")

            return False

        self.basic_data = cshis_utils.decode_cshis6_register_basic_data(res_data)
        self.basic_data["emg_phone"] = self.get_emergent_tel()

        return True

    def read_register_basic_data_by_vhc(self):
        system_utils.set_keyboard_layout("英文")

        if self.qrcode is None:
            self.qrcode = self._get_qrcode()

        if self.qrcode is None:
            self._reset_basic_data()
            return False

        service_path = "/api/hc/v1/VirtualHc/ReadBasic"
        data = {"token": self.qrcode}

        card_content = self._get_json(service_path, "POST", data)
        if card_content is None:
            self._reset_basic_data()
            save_log("虛擬健保卡 API 無回應 (請檢查元件狀態)")
            return False

        error_code = card_content.get("statusCode", -1)
        if error_code != 0:
            self._reset_basic_data()
            save_log(f"虛擬健保卡讀取失敗, 錯誤代碼: {error_code}")
            return False

        try:
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
        except KeyError as e:
            self._reset_basic_data()
            save_log(f"虛擬健保卡回應缺少欄位 {e}: {card_content}")
            return False

        return True

    def get_emergent_tel(self):
        hc_signature = self.get_hc_signature(service_type="01", show_warning=False)
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            return ""

        service_path = "/api/v1/EmergentTel/Query"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            return ""

        return string_utils.xstr(res_data.get("tel"))

    def get_card_status(self):
        hc_signature = self.get_hc_signature(service_type="01")
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            return None, None

        service_path = "/api/v1/BasicData/Register2"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            return None, None

        try:
            available_date = date_utils.nhi_date_to_west_date(res_data["cardValidity"])
            available_count = number_utils.get_integer(res_data["treatmentCounter"])
        except (KeyError, TypeError) as e:
            save_log(f"取得卡片狀態失敗 {e}: {res_data}")
            return None, None

        return available_date, available_count

    # 更新健保卡有效期限及可用次數
    def update_hc(self, show_message=True):
        hc_signature = self.get_hc_signature(service_type="04")
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            return -1

        service_path = "/api/v1/HcContent/Update"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        error_code = res_data.get("statusCode", -1) if res_data else -1

        if show_message or error_code != 0:
            self._show_message(error_code, "健保IC卡卡片內容更新")

        return error_code

    def read_critical_illness(self):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        request_data = self._signature_data(hpchc_signature, format="0")
        if request_data is None:
            return False

        service_path = "/api/v1/CriticalIllness/Query"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(-1, "健保卡讀取重大傷病")
            return False

        error_code = res_data.get("statusCode", -1)
        illness_data = res_data.get("criticalIllnesses", [])

        if error_code != 0:
            self._show_message(error_code, "健保卡讀取重大傷病")

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
            except (IndexError, KeyError, TypeError):
                self.critical_illness_data.append(
                    {
                        "CI_CODE": "",
                        "CI_VALIDITY_START": "",
                        "CI_VALIDITY_END": "",
                    }
                )

        return True

    # ------------------------------------------------------------------
    # 虛擬健保卡
    # ------------------------------------------------------------------

    def _get_qrcode(self):
        self.qrcode = None

        if self.system_settings.field("使用webcam讀取虛擬健保卡") == "Y":
            from dialog import dialog_qrcode

            success, qr_text = dialog_qrcode.DialogQRCode.get_qr_code(None)
            if success:
                self.qrcode = qr_text
                return qr_text

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

    def verify_vhc_card(self):
        service_path = "/api/hc/v1/Verification/VirtualHc"
        data = {"token": self.qrcode}

        res_data = self._get_json(service_path, "POST", data)
        if res_data is None:
            return False

        return res_data.get("statusCode", -1) == 0

    def reset_vhc_card(self):
        if self.qrcode is None:
            self.qrcode = self._get_qrcode()

        if not self.read_register_basic_data():
            return False

        return self.verify_vhc_card()

    def apply_qr_code(self):
        # 測試用途: /test/ 路徑, 性別生日寫死, 正式環境不應執行
        if self.system_settings.field("使用測試環境") != "Y":
            save_log("apply_qr_code 只能在測試環境使用")
            return False

        sam_signature = self.get_sam_signature(service_type="06")
        request_data = self._signature_data(
            sam_signature,
            sex="M",
            birthday="0661005",
            isForeigner=False,
        )
        if request_data is None:
            self._show_message(4050, "請求虛擬健保卡授權失敗")
            return False

        service_path = "/test/v1/ApplyVirtualHc/Apply"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(4050, "請求虛擬健保卡授權失敗")
            return False

        return res_data

    def request_token(self, patient_id):
        sam_signature = self.get_sam_signature(service_type="01")
        request_data = self._signature_data(sam_signature, patientId=patient_id)
        if request_data is None:
            self._show_message(4050, "請求虛擬健保卡授權失敗")
            return None

        service_path = "/api/v1/TeleMedicine/RequestToken"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(-1, "請求虛擬健保卡授權失敗")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "請求虛擬健保卡授權失敗")
            return None

        return res_data.get("accessToken")

    def get_response_token(self, access_token):
        sam_signature = self.get_sam_signature(service_type="01")
        request_data = self._signature_data(sam_signature, accessToken=access_token)
        if request_data is None:
            self._show_message(4050, "請求虛擬健保卡授權失敗")
            return None

        service_path = "/api/v1/TeleMedicine/ResponseToken"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(-1, "請求虛擬健保卡序號失敗")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "請求虛擬健保卡序號失敗")
            return None

        return res_data.get("virtualCardToken")

    # ------------------------------------------------------------------
    # 門診 / 診斷 / 處方資料讀取
    # ------------------------------------------------------------------

    # 取得門診資料 (不需醫事人員卡)
    def read_treatment_no_need_hpc(self):
        msg_box = self._show_wait_box(
            "取得健保卡門診資料",
            '<font size="5" color="red"><b>正在取得健保卡門診資料中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.read_treatment_no_need_hpc_thread,
            args=(msg_queue,),
            daemon=True,
        )
        t.start()
        try:
            (error_code, treatment_data) = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            treatment_data = {}
            save_log("取得健保卡門診資料逾時")

        self._close_wait_box(msg_box)

        if error_code != 0:
            self._show_message(error_code, "健保卡讀取")
            return False

        self.treatment_data = treatment_data

        return True

    def read_treatment_no_need_hpc_thread(self, out_queue):
        hc_signature = self.get_hc_signature(service_type="01", show_warning=False)
        request_data = self._signature_data(hc_signature)
        if request_data is None:
            out_queue.put((-1, {}))
            return

        service_path = "/api/v1/Treatment/NoNeedHPC"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            out_queue.put((-1, {}))
            return

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            out_queue.put((error_code, {}))
            return

        out_queue.put((error_code, cshis_utils.decode_cshis6_treatment_data(res_data)))

    # 取得診斷資料 (需醫事人員卡)
    def read_treatment_need_hpc(self):
        msg_box = self._show_wait_box(
            "取得健保卡診斷資料",
            '<font size="5" color="red"><b>正在取得健保卡診斷資料中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.read_treatment_need_hpc_thread, args=(msg_queue,), daemon=True
        )
        t.start()
        try:
            (error_code, disease_data) = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            disease_data = {}
            save_log("取得健保卡診斷資料逾時")

        self._close_wait_box(msg_box)

        if error_code != 0:
            self._show_message(error_code, "健保卡讀取")
            return False

        self.disease_data = disease_data

        return True

    def read_treatment_need_hpc_thread(self, out_queue):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        request_data = self._signature_data(hpchc_signature, format="0")
        if request_data is None:
            out_queue.put((-1, {}))
            return

        service_path = "/api/v1/Treatment/NeedHPC"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            out_queue.put((-1, {}))
            return

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            out_queue.put((error_code, {}))
            return

        out_queue.put((error_code, cshis_utils.decode_cshis6_disease_data(res_data)))

    # 取得處方資料
    def read_prescript_data(self):
        msg_box = self._show_wait_box(
            "取得健保卡處方資料",
            '<font size="5" color="red"><b>正在取得健保卡處方資料中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.read_prescript_data_thread, args=(msg_queue,), daemon=True
        )
        t.start()
        try:
            (error_code, prescript_data) = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            prescript_data = []
            save_log("取得健保卡處方資料逾時")

        self._close_wait_box(msg_box)

        if error_code != 0:
            self._show_message(error_code, "健保卡讀取")
            return False

        self.prescript_data = prescript_data

        return True

    def read_prescript_data_thread(self, out_queue):
        hpchc_signature = self.get_hpchc_signature(service_type="01")
        request_data = self._signature_data(hpchc_signature)
        if request_data is None:
            out_queue.put((-1, []))
            return

        service_path = "/api/v1/Prescription/Query"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            out_queue.put((-1, []))
            return

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            out_queue.put((error_code, []))
            return

        prescript_data = []
        for prescript in res_data.get("outpatientPrescriptions", []):
            prescript_data.append(
                {
                    "case_date": prescript.get("treatmentDateTime"),
                    "prescript_type": prescript.get("treatmentItem"),
                    "ins_code": prescript.get("treatmentItemCode"),
                    "treat_position": prescript.get("treatmentPosition"),
                    "usage": prescript.get("usage"),
                    "pres_days": prescript.get("days"),
                    "total_dosage": prescript.get("totalQuantity"),
                    "remark": "",
                }
            )

        out_queue.put((error_code, prescript_data))

    # ------------------------------------------------------------------
    # 就醫序號
    # ------------------------------------------------------------------

    def get_seq_number_256_thread(
        self, out_queue, treat_item, baby_treat, treat_after_check
    ):
        hc_signature = self.get_hc_signature(service_type="03", show_warning=False)
        request_data = self._signature_data(
            hc_signature,
            treatmentItem=treat_item,
            babyTreatment=baby_treat,
            afterCheck=treat_after_check,
        )
        if request_data is None:
            out_queue.put((-1, {}))
            return

        service_path = "/api/v1/SequelNumber/Next"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            out_queue.put((-1, {}))
            return

        out_queue.put((res_data.get("statusCode", -1), res_data))

    # 取得就醫序號
    def get_seq_number_256(self, treat_item, baby_treat, treat_after_check):
        msg_box = self._show_wait_box(
            "取得掛號安全簽章",
            '<font size="5" color="red"><b>健保讀卡機取得掛號安全簽章中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.get_seq_number_256_thread,
            args=(msg_queue, treat_item, baby_treat, treat_after_check),
            daemon=True,
        )
        t.start()
        try:
            (error_code, json_data) = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            json_data = {}
            save_log("取得掛號安全簽章逾時")

        self._close_wait_box(msg_box)

        if error_code == 0:  # 取得安全簽章成功
            self.treat_data = cshis_utils.decode_cshis6_treat_data(json_data)

        return error_code

    def return_seq_number_thread(self, out_queue, treat_date):
        hc_signature = self.get_hc_signature(service_type="03", show_warning=False)
        request_data = self._signature_data(hc_signature, treatmentDateTime=treat_date)
        if request_data is None:
            out_queue.put(-1)
            return

        service_path = "/api/v1/SequelNumber/Rollback"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        out_queue.put(res_data.get("statusCode", -1) if res_data else -1)

    # IC退掛
    def return_seq_number(self, treat_date):
        if self.ic_card_type == "虛擬健保卡":
            if not self.reset_vhc_card():
                return False

        msg_box = self._show_wait_box(
            "健保IC卡退掛",
            '<font size="5" color="red"><b>健保IC卡退掛中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.return_seq_number_thread,
            args=(msg_queue, treat_date),
            daemon=True,
        )
        t.start()
        try:
            error_code = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            save_log("健保IC卡退掛逾時")

        self._close_wait_box(msg_box)

        if error_code != 0:
            self._show_message(error_code, "健保卡退掛")
            return False

        self.logout_hc()

        return True

    # 單獨取得就醫識別碼
    def get_identifier(self, registration_datetime):
        hc_signature = self.get_hc_signature(service_type="03")
        request_data = self._signature_data(
            hc_signature, treatmentDateTime=registration_datetime
        )
        if request_data is None:
            return None

        service_path = "/api/v1/TreatmentNumber/Card"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(-1, "健保卡取得就醫識別碼失敗")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "健保卡取得就醫識別碼失敗")
            return None

        return res_data.get("treatmentNumber")

    # ------------------------------------------------------------------
    # 資料上傳
    # ------------------------------------------------------------------

    def upload_data_thread(self, out_queue, upload_type, xml, case_count):
        cshis_x = class_utils.get_cshisx(self.database, self.system_settings)

        self._ensure_sam_verified()

        sam_signature = self.get_sam_signature(service_type="30")
        request_data = self._signature_data(sam_signature)
        if request_data is None:
            out_queue.put((-1, {}))
            return

        try:
            error_code, op_code = cshis_x.VNHI_Upload_cshis6(
                upload_type,
                request_data["samId"],
                request_data["hospitalId"],
                request_data["clientRandom"],
                request_data["signature"],
                xml,
                case_count,
            )
        except Exception as e:
            save_log(f"VNHI_Upload_cshis6 例外: {e}")
            out_queue.put((-1, {}))
            return

        out_queue.put((error_code, op_code))

    # IC卡資料上傳
    def upload_data(self, upload_type, xml, case_count):
        msg_box = self._show_wait_box(
            "健保IC卡資料上傳",
            '<font size="5" color="red"><b>健保IC卡資料上傳中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.upload_data_thread,
            args=(msg_queue, upload_type, xml, case_count),
            daemon=True,
        )
        t.start()
        try:
            (error_code, op_code) = self._wait_queue(msg_queue, 120)
        except Empty:
            error_code = -1
            op_code = {}
            save_log("健保IC卡資料上傳逾時")

        self._close_wait_box(msg_box)

        # 成功碼可能是字串 "0000" 或整數 0, 兩種都要接住
        if error_code not in [0, "0000"]:
            self._show_message(error_code, "健保卡資料上傳")
            return None

        if not isinstance(op_code, str) or len(op_code) < 42:
            save_log(f"健保卡資料上傳回應格式不符: {op_code!r}")
            self._show_message(-1, "健保卡資料上傳")
            return None

        upload_result = {
            "statusCode": 0,
            "uploadDateTime": op_code[:14],
            "receiveDateTime": op_code[:14],
            "hospitalId": op_code[20:30],
            "samId": op_code[30:42],
        }

        return upload_result["statusCode"], upload_result

    # ------------------------------------------------------------------
    # 寫卡
    # ------------------------------------------------------------------

    def _update_patient(self, patient_key):
        if not self.read_basic_data():
            return "", ""

        patient_id = self.basic_data["patient_id"]
        patient_birthday = self.basic_data["birthday"]

        fields = ["ID", "Birthday"]
        data = [patient_id, patient_birthday]
        self.database.update_record("patient", fields, "PatientKey", patient_key, data)

        return patient_id, patient_birthday

    @staticmethod
    def _same_birthday(db_birthday, card_birthday):
        """資料庫可能回 date, 卡片回字串, 直接比會永遠不相等"""
        return (
            string_utils.xstr(db_birthday)[:10] == string_utils.xstr(card_birthday)[:10]
        )

    def insert_correct_ic_card(self, patient_key):
        patient_key = number_utils.get_integer(patient_key)

        if not self.read_basic_data():
            return False

        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            save_log(f"insert_correct_ic_card: 找不到病歷號 {patient_key}")
            system_utils.show_message_box(
                QMessageBox.Critical,
                "病患資料有誤",
                f"""
                    <font size="5" color="red">
                        <b>找不到病歷號{patient_key}, 請重新插卡.</b>
                    </font>
                """,
                "請確定插入的健保卡是否為此病患所有.",
            )
            return False

        row = rows[0]
        patient_id = string_utils.xstr(row["ID"])
        patient_name = string_utils.xstr(row["Name"])
        card_patient_id = string_utils.xstr(self.basic_data["patient_id"])

        if patient_id != "" and patient_id != card_patient_id:
            ic_card_name = string_utils.xstr(self.basic_data["name"])
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("健保卡身分不符")
            msg_box.setText(f"""
                <font size="5" color="red">
                    <b>此健保卡基本資料為<br>
                </font>
                <font size="5" color="blue">
                  {ic_card_name}: {card_patient_id}<br>
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

        # 一律走 update_record, 不用 f-string 組 SQL (資料來源是健保卡)
        fields = []
        data = []

        if patient_id == "" and card_patient_id != "":
            fields.append("ID")
            data.append(card_patient_id)

        card_no = string_utils.xstr(self.basic_data["card_no"])
        if string_utils.xstr(row["CardNo"]) == "" and card_no != "":
            fields.append("CardNo")
            data.append(card_no)

        card_birthday = self.basic_data["birthday"]
        if card_birthday and not self._same_birthday(row["Birthday"], card_birthday):
            fields.append("Birthday")
            data.append(card_birthday)

        if fields:
            self.database.update_record(
                "patient", fields, "PatientKey", patient_key, data
            )

        return True

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
            if not self.verify_vhc_card():
                return False
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
                        self._show_message(error_code, "健保卡取得就醫序號")
                        return False
                else:
                    self._show_message(error_code, "健保卡取得就醫序號")
                    return False

        return self

    # 健保卡異常時取得就醫識別碼
    def write_ic_card_abnormal(self, patient_id):
        sam_signature = self.get_sam_signature(service_type="03")
        request_data = self._signature_data(sam_signature, patientId=patient_id)
        if request_data is None:
            self._show_message(4050, "健保卡異常時取得就醫識別碼失敗")
            return None

        service_path = "/api/v1/TreatmentNumber/NoCard"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            self._show_message(-1, "健保卡異常時取得就醫識別碼失敗")
            return None

        error_code = res_data.get("statusCode", -1)
        if error_code != 0:
            self._show_message(error_code, "健保卡異常時取得就醫識別碼失敗")
            return None

        self.treat_data = cshis_utils.decode_cshis6_no_ic_card_treat_data(res_data)

        return self

    # ic 醫令寫卡
    def write_ic_medical_record(self, case_key, treat_after_check, reset_vhc_card=True):
        if self.ic_card_type == "虛擬健保卡" and reset_vhc_card:
            if not self.reset_vhc_card():
                return False

        if not self.write_ic_treatment(case_key, treat_after_check):  # 寫入病名, 費用
            return False

        if not self.write_prescript_signature(case_key):  # 寫入醫令簽章
            self.logout_hc()
            return False

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

        return True

    def rewrite_ic_prescript(self, case_key):
        if self.ic_card_type == "虛擬健保卡":
            if not self.reset_vhc_card():
                return False

        if not self.write_prescript_signature(case_key):  # 寫入醫令簽章
            self.logout_hc()
            return False

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

        return True

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
        hc_signature = self.get_hc_signature(service_type="02", show_warning=False)
        request_data = self._signature_data(
            hc_signature,
            afterCheck=treat_after_check,
            treatmentDateTime=registration_datetime,
            mainCode=disease_code1,
            subCode1=disease_code2,
            subCode2=disease_code3,
            subCode3=disease_code4,
            subCode4="",
            subCode5="",
            outpatientFee=share_fee,
            costFee=share_fee,
            inpatientFee=0,
            inpatient30Fee=0,
            inpatient180Fee=0,
        )
        if request_data is None:
            out_queue.put(-1)
            return

        service_path = "/api/v1/Treatment/WriteCodeFee"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        out_queue.put(res_data.get("statusCode", -1) if res_data else -1)

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
        msg_box = self._show_wait_box(
            "寫入診察資料",
            '<font size="5" color="red"><b>健保讀卡機正在寫入診察資料中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
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
            daemon=True,
        )
        t.start()
        try:
            error_code = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            save_log("寫入診察資料逾時")

        self._close_wait_box(msg_box)

        if error_code == 3209:
            error_code = 0

        if error_code != 0:
            self._show_message(error_code, "健保卡寫入診察資料")
            return False

        return True

    def write_multi_prescript_sign_thread(
        self, out_queue, registration_datetime, prescriptions
    ):
        hc_signature = self.get_hc_signature(service_type="02", show_warning=False)
        request_data = self._signature_data(
            hc_signature,
            treatmentDateTime=registration_datetime,
            prescriptions=prescriptions,
        )
        if request_data is None:
            out_queue.put((-1, [], []))
            return

        service_path = "/api/v1/Prescription/Write"
        res_data = self._get_json(service_path, "POST", request_data, local_url=False)
        if res_data is None:
            out_queue.put((-1, [], []))
            return

        out_queue.put(
            (
                res_data.get("statusCode", -1),
                res_data.get("signatureItems", []),
                res_data.get("hexSignatureItems", []),
            )
        )

    def write_multi_prescript_sign(self, registration_datetime, prescriptions):
        msg_box = self._show_wait_box(
            "取得處方簽章",
            '<font size="5" color="red"><b>健保讀卡機取得處方簽章中, 請稍後...</b></font>',
            "正在與健保IDC資訊中心連線, 會花費一些時間.",
        )

        msg_queue = Queue()
        t = Thread(
            target=self.write_multi_prescript_sign_thread,
            args=(msg_queue, registration_datetime, prescriptions),
            daemon=True,
        )
        t.start()
        try:
            (
                error_code,
                prescript_sign_list,
                hex_prescript_sign_list,
            ) = self._wait_queue(msg_queue, 30)
        except Empty:
            error_code = -1
            prescript_sign_list = []
            hex_prescript_sign_list = []
            save_log("取得處方簽章逾時")

        self._close_wait_box(msg_box)

        if error_code != 0:
            self._show_message(error_code, "健保卡取得處方簽章")
            return None

        return prescript_sign_list, hex_prescript_sign_list

    @staticmethod
    def _to_hex_signature_list(hex_sign_list, sign_list):
        """取得 hex 格式的簽章清單

        健保署正常會回 hexSignatureItems; 沒回但有 base64 的 signatureItems 時,
        自行轉成 hex 當備援. 兩者都沒有就回空 list, 由呼叫端判定失敗.
        """
        if hex_sign_list:
            return list(hex_sign_list)

        if not sign_list:
            return []

        hex_list = []
        for sign in sign_list:
            try:
                hex_list.append(base64.b64decode(sign).hex().upper())
            except Exception as e:
                save_log(f"簽章 base64 轉換失敗: {e}")
                return []

        save_log("hexSignatureItems 未回傳, 改用 signatureItems 轉換")

        return hex_list

    # 寫入藥品處方簽章
    def write_medicine_signature(
        self, case_row, patient_row, prescript_rows, dosage_row
    ):
        case_key = number_utils.get_integer(case_row["CaseKey"])

        if dosage_row is None:
            save_log(f"write_medicine_signature: 找不到 dosage 列, CaseKey={case_key}")
            self._show_message(-1, "健保卡寫入醫令簽章")
            return False

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
            total_dosage = round(number_utils.get_float(row["Dosage"]) * days, 2)
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

        result = self.write_multi_prescript_sign(reg_datetime, prescriptions)
        if result is None:
            return False

        prescript_sign_list, hex_prescript_sign_list = result
        hex_prescript_sign_list = self._to_hex_signature_list(
            hex_prescript_sign_list, prescript_sign_list
        )

        if not hex_prescript_sign_list:
            save_log(f"未取得任何醫令簽章, CaseKey={case_key}")
            self._show_message(-1, "健保卡取得處方簽章")
            return False

        if len(hex_prescript_sign_list) != len(prescript_rows):
            save_log(
                f"醫令筆數 {len(prescript_rows)} 與簽章筆數 "
                f"{len(hex_prescript_sign_list)} 不符, CaseKey={case_key}"
            )
            self._show_message(-1, "健保卡取得處方簽章")
            return False

        for row, prescript_sign in zip(prescript_rows, hex_prescript_sign_list):
            prescript_key = number_utils.get_integer(row["PrescriptKey"])
            sql = f"""
                DELETE FROM presextend
                WHERE
                    PrescriptKey = {prescript_key} AND
                    ExtendType = "處方簽章"
            """
            self.database.exec_sql(sql)

            fields = ["PrescriptKey", "ExtendType", "Content"]
            data = [prescript_key, "處方簽章", prescript_sign]
            self.database.insert_record("presextend", fields, data)

        return True

    # 寫入處置處方簽章
    def write_treat_signature(self, case_row, dosage_row=None, patient_row=None):
        # dosage_row / patient_row 目前用不到, 保留參數以相容既有呼叫端
        case_key = number_utils.get_integer(case_row["CaseKey"])

        ic_card_time = case_utils.extract_security_xml(case_row["Security"], "寫卡時間")
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(
            ic_card_time
        )  # 就診日期時間 13 bytes: EEEmmddHHMMSS

        treat_code = string_utils.xstr(
            nhi_utils.get_treat_code(self.database, case_key)
        )
        if treat_code == "":
            save_log(f"write_treat_signature: 取不到處置代碼, CaseKey={case_key}")
            self._show_message(-1, "健保卡寫入處置簽章")
            return False

        order_type = "3"  # 醫令類別 1 bytes: 1-非長期藥品 2-長期藥品 3-診療 4-特殊材料
        treat_code = f"{treat_code:<12}"  # 診療項目代號 12 bytes
        treat_position = " " * 6  # 診療部位 6 bytes
        usage = f"{'':<18}"  # 用法 18 bytes, 處置免填
        days = f"{0:0>2}"  # 天數 2 bytes: 00
        total_dosage = f"{1:0>7}"  # 總量 7 bytes: 00000.0
        deliver = "03"  # 交付處方註記 2 bytes: 01-自行調劑 02-交付調劑 03-自行執行

        prescription = [
            {
                "days": days,
                "deliveryNotes": deliver,
                "totalQuantity": total_dosage,
                "treatmentDateTime": reg_datetime,
                "treatmentItem": order_type,
                "treatmentItemCode": treat_code,
                "treatmentPosition": treat_position,
                "usage": usage,
            }
        ]

        result = self.write_multi_prescript_sign(reg_datetime, prescription)
        if result is None:
            return False

        treat_sign_list, hex_treat_sign_list = result
        hex_treat_sign_list = self._to_hex_signature_list(
            hex_treat_sign_list, treat_sign_list
        )

        if not hex_treat_sign_list:
            save_log(f"未取得處置簽章, CaseKey={case_key}")
            self._show_message(-1, "健保卡取得處置簽章")
            return False

        treat_sign = hex_treat_sign_list[0]

        self.database.exec_sql(f"""
            DELETE FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
        """)

        fields = ["PrescriptKey", "ExtendType", "Content"]
        data = [case_key, "處置簽章", treat_sign]
        self.database.insert_record("presextend", fields, data)

        return True

    # 寫入病名及費用
    def write_ic_treatment(self, case_key, treat_after_check):
        case_key = number_utils.get_integer(case_key)

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
            save_log(f"write_ic_treatment: 找不到病歷 CaseKey={case_key}")
            return False

        case_row = rows[0]
        patient_key = number_utils.get_integer(case_row["PatientKey"])

        sql = f"""
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        patient_rows = self.database.select_record(sql)
        if len(patient_rows) <= 0:
            save_log(f"write_ic_treatment: 找不到病患 PatientKey={patient_key}")
            return False

        patient_row = patient_rows[0]

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

        return self.write_treatment_code_fee(
            reg_datetime,
            treat_after_check,
            disease_code1,
            disease_code2,
            disease_code3,
            disease_code4,
            share_fee,
        )

    # 寫入處方簽章
    def write_prescript_signature(self, case_key):
        case_key = number_utils.get_integer(case_key)

        sql = f"""
            SELECT CaseKey, PatientKey, Treatment, Security FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            save_log(f"write_prescript_signature: 找不到病歷 CaseKey={case_key}")
            return False

        case_row = rows[0]

        sql = f"""
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        """
        rows = self.database.select_record(sql)
        dosage_row = rows[0] if len(rows) > 0 else None

        patient_key = number_utils.get_integer(case_row["PatientKey"])
        sql = f"""
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        patient_rows = self.database.select_record(sql)
        patient_row = patient_rows[0] if len(patient_rows) > 0 else None

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

        signed = True
        if string_utils.xstr(
            case_row["Treatment"]
        ) in nhi_utils.INS_TREAT and not self.write_treat_signature(
            case_row, dosage_row, patient_row
        ):
            signed = False

        if len(prescript_rows) > 0 and not self.write_medicine_signature(
            case_row, patient_row, prescript_rows, dosage_row
        ):
            signed = False

        return signed

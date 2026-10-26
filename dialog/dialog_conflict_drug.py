# 系統設定 指定診別起始號 2021-11-04
# 2026-01-01 改成web 2.0
# 2026-10-21 依「主動提示功能 Web API 介接說明書 v1.0」強化錯誤處理與簽章檢查
# -*- coding: UTF-8 -*-

import json
import logging

import requests
import urllib3
from PyQt5 import QtCore, QtWidgets

from libs import (
    class_utils,
    date_utils,
    prescript_utils,
    string_utils,
    system_utils,
    ui_utils,
)

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "Content-Type": "application/json",
}

REQUEST_TIMEOUT = 20  # 秒，避免 VPN 卡住時整個畫面凍結

URL_CSHIS5 = "https://medcloudws2.nhi.gov.tw/api/imie5000/GetMedPrtData"
URL_CSHIS6 = "https://medcloudws2.nhi.gov.tw/api/imie5000/GetMedPrtInfo"

SERVICE_TYPE = "91"  # 健保醫療資訊雲端查詢系統主動提示功能 Web API
DATA_TYPE_CHINESE_TO_WESTERN = "09"  # 藥品交互作用資料(中/西藥)

DEFAULT_MESSAGE = "無交互作用"

# 主動提示功能 Web API v1.0 異常碼
RTN_CODE_MESSAGES = {
    "01": "參數解析失敗",
    "02": "個案驗章失敗（實體健保卡驗證失敗）",
    "03": "連線數過多，請稍候再試",
    "04": "雲端系統發生異常",
    "05": "處方內含非適用之醫令代碼，整筆不處理",
    "06": "資料類別錯誤",
    "07": "個案驗章失敗（虛擬健保卡驗證失敗）",
    "08": "資料筆數過多",
    "09": "非院所的專兼任醫師",
}


# 中西藥交互查詢
class DialogConflictDrug(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.doctor_id = string_utils.xstr(args[2]).strip()
        self.patient_id = string_utils.xstr(args[3]).strip()
        self.table_widget_prescript = args[4]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.start_check()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CONFLICT_DRUG, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog

        self.table_widget_conflict_drug = class_utils.get_table_widget(
            self.ui.tableWidget_conflict_drug, self.database
        )
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [120, 300, 600]
        self.table_widget_conflict_drug.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def start_check(self):
        self._set_table_widget_prescript()
        if self.ui.tableWidget_conflict_drug.rowCount() <= 0:
            return

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            error_message, response_content = self._get_request()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if error_message is not None:
            self._show_error_message(error_message)
            return

        rtn_code = string_utils.xstr(
            self._get_field(response_content, "rtnCode", "RtnCode")
        ).strip()
        if rtn_code != "00":
            logger.warning("中西藥交互作用查詢失敗: %s", response_content)
            message = RTN_CODE_MESSAGES.get(rtn_code, "未定義的錯誤")
            self._show_error_message(f"雲端查詢失敗 (錯誤碼 {rtn_code}): {message}")
            return

        result_list = self._get_result_list(response_content)
        if result_list is None:
            logger.warning("中西藥交互作用回傳結構異常: %s", response_content)
            self._show_error_message("雲端回傳資料格式異常")
            return

        if len(result_list) == 0:
            return

        self._display_order_message(result_list)
        self.ui.tableWidget_conflict_drug.resizeRowsToContents()

    # ------------------------------------------------------------------
    # 處方 → 查詢表格
    # ------------------------------------------------------------------
    def _set_table_widget_prescript(self):
        self.ui.tableWidget_conflict_drug.setRowCount(0)
        ins_code_set = set()

        for row_no in range(self.table_widget_prescript.rowCount()):
            ins_code_item = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["InsCode"]
            )
            if ins_code_item is None:
                continue

            ins_code = ins_code_item.text().strip()
            if ins_code == "" or ins_code in ins_code_set:
                continue

            ins_code_set.add(ins_code)

            medicine_name_item = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
            )
            medicine_name = (
                medicine_name_item.text() if medicine_name_item is not None else ""
            )

            medicine = [ins_code, medicine_name, DEFAULT_MESSAGE]

            index = self.ui.tableWidget_conflict_drug.rowCount()
            self.ui.tableWidget_conflict_drug.setRowCount(index + 1)
            for col_no in range(len(medicine)):
                self.ui.tableWidget_conflict_drug.setItem(
                    index,
                    col_no,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(medicine[col_no])),
                )

    def _get_sub(self):
        sub_list = []
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            item = self.ui.tableWidget_conflict_drug.item(row_no, 0)
            if item is None:
                continue

            ins_code = item.text().strip()
            if ins_code == "":
                continue

            sub_list.append({"sOrder": ins_code})

        return [
            {
                "sType": DATA_TYPE_CHINESE_TO_WESTERN,  # 中藥 -> 西藥
                "sub": sub_list,
            }
        ]

    # ------------------------------------------------------------------
    # 呼叫 Web API
    # ------------------------------------------------------------------
    # 回傳 (error_message, response_json)，成功時 error_message 為 None
    def _get_request(self):
        if self.system_settings.field("讀卡機控制軟體版本") == "cshis6":
            url = URL_CSHIS6
            get_json = self._get_cshis6_json
        else:
            url = URL_CSHIS5
            get_json = self._get_cshis5_json

        try:
            json_data, error_message = get_json()
        except Exception as e:
            logger.exception("取得卡片資料或簽章失敗")
            return f"讀取卡片或取得簽章失敗: {e}", None

        if error_message is not None:
            return error_message, None

        logger.info(
            "中西藥交互作用查詢: url=%s orders=%s",
            url,
            [sub["sOrder"] for sub in json_data["sub"][0]["sub"]],
        )

        try:
            response = requests.post(
                url,
                json=json_data,
                headers=HEADERS,
                verify=False,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.Timeout:
            return "連線健保醫療資訊雲端查詢系統逾時，請稍後再試", None
        except requests.ConnectionError:
            logger.exception("連線健保雲端失敗")
            return "無法連線至健保醫療資訊雲端查詢系統，請確認健保 VPN 連線", None
        except requests.RequestException as e:
            logger.exception("連線健保雲端失敗")
            return f"無法連線至健保醫療資訊雲端查詢系統: {e}", None

        if response.status_code != 200:
            logger.warning(
                "中西藥交互作用 HTTP %s: %s",
                response.status_code,
                response.text[:2000],
            )
            return f"HTTP 錯誤: 代碼 {response.status_code}", None

        try:
            response_content = response.json()
        except ValueError:
            logger.warning("中西藥交互作用回傳非 JSON: %s", response.text[:2000])
            return "雲端回傳非 JSON 資料", None

        if not isinstance(response_content, dict):
            logger.warning("中西藥交互作用回傳格式異常: %s", response_content)
            return "雲端回傳資料格式異常", None

        return None, response_content

    # 讀卡機控制軟體 6.0
    def _get_cshis6_json(self):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        signature = ic_card.get_hpchc_signature(service_type=SERVICE_TYPE)

        if (
            not signature
            or not signature.get("signature")
            or not signature.get("clientRandom")
        ):
            return None, "三卡簽章失敗，請確認醫事人員卡已認證且病人健保卡已插入"

        # 讀卡機上的健保卡必須是目前這位病人
        hc_id_no = string_utils.xstr(signature.get("hcIdNo")).strip().upper()
        if hc_id_no != "" and hc_id_no != self.patient_id.upper():
            return None, "讀卡機上的健保卡不是目前這位病人，請更換健保卡後重新查詢"

        # 醫事人員身分證號以簽章的醫事人員卡為準，避免與病歷醫師不一致造成驗章失敗
        hpc_id_no = string_utils.xstr(signature.get("hpcIdNo")).strip()
        if hpc_id_no == "":
            hpc_id_no = self.doctor_id

        verify = {
            "signature": signature.get("signature"),
            "clientRandom": signature.get("clientRandom"),
            "samId": signature.get("samId"),
            "hospitalId": signature.get("hospitalId"),
            "serviceType": SERVICE_TYPE,
            "hpcId": signature.get("hpcId"),
            "hcIdNo": signature.get("hcIdNo"),
            "hcId": signature.get("hcId"),
            "hpcIdNo": signature.get("hpcIdNo"),
        }

        json_data = {
            "sHospId": self.system_settings.field("院所代號"),
            "sHpcId": hpc_id_no,
            "sPatId": self.patient_id,
            "sVerify": verify,
            "sub": self._get_sub(),
        }

        return json_data, None

    # 讀卡機控制軟體 5.x
    def _get_cshis5_json(self):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)

        # 1. 病人健保卡：即時從讀卡機讀取，不用資料庫卡號
        #    （病人換卡後資料庫卡號過期 → 錯誤碼 02）
        if not ic_card.read_basic_data(show_message=False):
            return None, "讀取病人健保卡失敗，請確認健保卡已插入讀卡機"

        error_code = ic_card.quick_insurance()
        logger.warning(
            "hisQuickInsurence=%s, HC狀態=%s",
            error_code,
            ic_card.get_ic_card_status(card_type=2),
        )

        patient_card_no = string_utils.xstr(ic_card.basic_data.get("card_no")).strip()
        patient_id_no = (
            string_utils.xstr(ic_card.basic_data.get("patient_id")).strip().upper()
        )
        if patient_card_no == "" or patient_id_no == "":
            return None, "讀取病人健保卡失敗，請確認健保卡已插入讀卡機"

        if patient_id_no != self.patient_id.upper():
            return None, "讀卡機上的健保卡不是目前這位病人，請更換健保卡後重新查詢"

        # 2. 醫事人員卡：卡號與身分證號都以讀卡機上的卡為準
        #    （共用醫事人員卡時，病歷醫師 ≠ 插卡醫師 → 錯誤碼 02）
        hpc_card_no = string_utils.xstr(ic_card.read_hpc_card_no()).strip()
        if hpc_card_no == "":
            return None, "讀取醫事人員卡卡號失敗，請確認醫事人員卡已插入"

        # TODO: 驗證完 sHcaCardId 該用序號還是卡號後移除
        logger.warning(
            "HPC 序號=%s 卡號=%s",
            hpc_card_no,
            ic_card.read_card_no(3),
        )

        hpc_id_no = string_utils.xstr(ic_card.read_hpc_id_no()).strip().upper()
        if hpc_id_no == "":
            hpc_id_no = self.doctor_id

        # 3. 卡片都確認後再簽章（簽章放最後，避免簽完又被換卡）
        cshis_x = class_utils.get_cshisx(self.database, self.system_settings)
        try:
            logger.warning(
                "卡片狀態: HC=%s HPC=%s CS版本=%s",
                ic_card.get_ic_card_status(card_type=2),
                ic_card.get_ic_card_status(card_type=3),
                ic_card.get_cs_version()[0],
            )
            random_number, signature = cshis_x.VPNH_SignX(
                card_type="4",  # 安全模組 + 健保卡 + 醫師卡
                service_type=SERVICE_TYPE,
            )
            logger.warning(
                "VPNH_SignX: random len=%s %r / signature len=%s head=%r tail=%r",
                len(str(random_number)),
                str(random_number)[:20],
                len(str(signature)),
                str(signature)[:16],
                str(signature)[-16:],
            )
        except Exception:
            logger.exception("VPNH_SignX 失敗")
            return None, "VPN 三卡簽章失敗，請確認醫事人員卡已認證且病人健保卡已插入"

        if not random_number or not signature:
            return None, "VPN 三卡簽章失敗，請確認醫事人員卡已認證且病人健保卡已插入"

        try:
            sam_card_json = json.loads(cshis_x.GetSAMCardInfoInCS())
            sam_id = sam_card_json["SAMCardInfoInCS"]["SAM"][0]["CARD_ID"]
        except Exception:
            logger.exception("讀取 SAM 卡資訊失敗")
            return None, "讀取安全模組卡號失敗"

        if not sam_id:
            return None, "讀取安全模組卡號失敗"

        json_data = {
            "sHospId": self.system_settings.field("院所代號"),
            "sHcaId": hpc_id_no,
            "sPatId": patient_id_no,
            "sPatCardType": "2",  # 1:虛擬卡 2:實體卡
            "sHcaCardId": hpc_card_no,  # 若驗證後確認要用卡號，改成 ic_card.read_card_no(3)
            "sPatCardId": patient_card_no,
            "sClientRandom": random_number,
            "sSignature": signature,
            "vhcCloudToken": "",
            "sSamId": sam_id,
            "sub": self._get_sub(),
        }

        logger.info(
            "中西藥交互作用 5.x 身分欄位: sHcaId=%s sPatId=%s sHcaCardId=%s sPatCardId=%s",
            hpc_id_no,
            patient_id_no,
            hpc_card_no,
            patient_card_no,
        )

        return json_data, None

    # ------------------------------------------------------------------
    # 解析回傳資料
    # ------------------------------------------------------------------
    @staticmethod
    def _get_field(data, *keys):
        if not isinstance(data, dict):
            return None

        for key in keys:
            if key in data:
                return data[key]

        return None

    # 取出資料類別 09 的結果；結構異常時回傳 None
    def _get_result_list(self, response_content):
        type_list = self._get_field(response_content, "sub")
        if type_list is None:
            return []

        if not isinstance(type_list, list):
            return None

        result_list = []
        for type_dict in type_list:
            if not isinstance(type_dict, dict):
                continue

            o_type = string_utils.xstr(self._get_field(type_dict, "oType")).strip()
            if o_type not in ("", DATA_TYPE_CHINESE_TO_WESTERN):
                continue

            items = self._get_field(type_dict, "sub") or []
            if not isinstance(items, list):
                return None

            result_list.extend(item for item in items if isinstance(item, dict))

        return result_list

    def _display_order_message(self, result_list):
        message_dict = {}
        for result_dict in result_list:
            ins_code = string_utils.xstr(result_dict.get("oOrder")).strip()
            if ins_code == "":
                continue

            message_dict.setdefault(ins_code, []).append(
                self._format_result(result_dict)
            )

        for ins_code, message_list in message_dict.items():
            self._set_message_item(ins_code, "\n\n".join(message_list))

    def _format_result(self, result_dict):
        lines = []

        c_drug_name = string_utils.xstr(result_dict.get("cDrugName")).strip()
        if c_drug_name != "":
            lines.append(f"藥材名稱: {c_drug_name}")

        lines.append(f"交互作用結果: {string_utils.xstr(result_dict.get('effect'))}")
        lines.append(f"機轉: {string_utils.xstr(result_dict.get('mechanism'))}")
        lines.append(f"處置方式: {string_utils.xstr(result_dict.get('management'))}")

        detail = self._extract_sub(result_dict.get("sub"))
        if detail != "":
            lines.append(detail)

        return "\n".join(lines)

    def _extract_sub(self, sub_list):
        if not isinstance(sub_list, list) or len(sub_list) == 0:
            return ""

        lines = ["開立藥品機構\t開立日期\t交互作用藥品"]
        for sub in sub_list:
            if not isinstance(sub, dict):
                continue

            hosp_name = string_utils.xstr(self._get_field(sub, "hospName", "HospName"))
            func_dt = string_utils.xstr(self._get_field(sub, "funcDT", "FuncDT"))
            try:
                func_date = date_utils.nhi_date_to_west_date(func_dt)
            except Exception:
                func_date = func_dt

            # 規格範例中此欄位可能為空字串，西藥名稱另見「機轉」說明
            drug_name = string_utils.xstr(
                self._get_field(sub, "ddiatC7Name", "DDIATC7Name")
            ).strip()
            if drug_name == "":
                drug_name = "-"

            lines.append(f"{hosp_name}\t{func_date}\t{drug_name}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 表格顯示
    # ------------------------------------------------------------------
    def _set_message_item(self, in_ins_code, order_message):
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            item = self.ui.tableWidget_conflict_drug.item(row_no, 0)
            if item is None:
                continue

            if item.text().strip() == in_ins_code:
                self.ui.tableWidget_conflict_drug.setItem(
                    row_no,
                    2,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(order_message)),
                )

    def _show_error_message(self, error_message):
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            self.ui.tableWidget_conflict_drug.setItem(
                row_no, 2, QtWidgets.QTableWidgetItem(error_message)
            )

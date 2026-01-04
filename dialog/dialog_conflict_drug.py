
# 系統設定 指定診別起始號 2021-11-04
# 2026-01-01 改成web 2.0
# -*- coding: UTF-8 -*-

import json

import requests
from libs import (class_utils, date_utils, prescript_utils, string_utils, patient_utils,
                  system_utils, ui_utils)
from PyQt5 import QtWidgets

HEADERS = {
    "Content-Type": "application/json",  # 根據 API 要求的 Content-Type 設定
}


# 主視窗
class DialogConflictDrug(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogConflictDrug, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.doctor_id = args[2]
        self.patient_id = args[3]
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

    def _show_connection_error(self, error_message):
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            self.ui.tableWidget_conflict_drug.setItem(
                row_no, 2, QtWidgets.QTableWidgetItem(error_message)
            )

    def start_check(self):
        self._set_table_widget_prescript()
        error_code, response_content = self._get_request()
        if error_code is None:
            self._show_connection_error('無法連線至健保醫療資訊雲端查詢系統')
            return

        if error_code != 200:
            self._show_connection_error(f'HTTP 錯誤: 代碼: {error_code}')
            return

        if response_content['rtnCode'] != '00':
            return

        try:
            return_number = response_content['sub'][0]['rtnNum']
        except Exception:
            # 結構和預期不同
            return

        if return_number == 0:
            return

        result_list = response_content['sub'][0]['sub']
        self._display_order_message(result_list)

        self.ui.tableWidget_conflict_drug.resizeRowsToContents()

    def _display_order_message(self, result_list):
        for result_dict in result_list:
            ins_code = result_dict['oOrder']
            effect = result_dict['effect']
            mechanism = result_dict['mechanism']
            management = result_dict['management']
            try:
                sub = self._extract_sub(result_dict['sub'])
            except Exception:
                sub = ''

            order_message = f'交互作用結果: {effect}\n機轉: {mechanism}\n處置方式: {management}\n{sub}'

            self._set_message_item(ins_code, order_message)

    def _extract_sub(self, sub_list):
        result = '開立藥品機構\t開立日期\t藥品名稱'
        for sub in sub_list:
            func_date = date_utils.nhi_date_to_west_date(sub["funcDT"])
            result += f'\n{sub["hospName"]}\t{func_date}\t{sub["ddiatC7Name"]}'

        return result

    def _set_message_item(self, in_ins_code, order_message):
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            ins_code = self.ui.tableWidget_conflict_drug.item(row_no, 0).text()
            if in_ins_code == ins_code:
                self.ui.tableWidget_conflict_drug.setItem(
                    row_no, 2, QtWidgets.QTableWidgetItem(string_utils.xstr(order_message))
                )
                break

    def _get_cshis5_signature(self):
        signature = "UGqD+rMIFwwJFmyGePEBqEIvmi0eVU/AhSYTzwToSFFHQEvDdNl0L4z+LSihxhts5AnWbVf1mJ4F8H3Xr4EpN1aix4mjIwjzM4vC5pvAlSc6vAsKfwLTLJgkgzIJJemFYOqq1K0IDDO7/Jd1XHZO24/wi9zgpa9wLDCuOZmrnziDRlFeNgiCbPN1fRZPYe+orF7i/HipThloESbkwtDkS8g9s2pjL4thUqyppV8de2G0RVKVshk4RfPeCpFNy7uSEG7mZCTI1kLmV0DMJn4GjgGGv3ru5XRDidFlNqUv7jLJX0XbAAPMUuI6Grtzp3S5pRhNP4Hli7WFjLmHwlEEqA=="
        return signature 

    def _get_cshis5_client_random(self):
        client_random = "4je+oJUz/Yc="
        return client_random

    def _get_cshis6_verify(self):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        hpchc_signature = ic_card.get_hpchc_signature(service_type='91')
        if hpchc_signature is None or hpchc_signature['clientRandom'] is None:
            return None

        verify = {
            'signature': hpchc_signature['signature'],
            'clientRandom': hpchc_signature['clientRandom'],
            'samId': hpchc_signature['samId'],
            'hospitalId': hpchc_signature['hospitalId'],
            'serviceType': '91',
            'hpcId': hpchc_signature['hpcId'],
            'hcIdNo': hpchc_signature['hcIdNo'],
            'hcId': hpchc_signature['hcId'],
            'hpcIdNo': hpchc_signature['hpcIdNo'],
        }

        return verify

    def _get_cshis6_json(self):
        json_data = {}
        json_data["sHospId"] = self.system_settings.field('院所代號')
        json_data["sHpcId"] = self.doctor_id
        json_data["sPatId"] = self.patient_id

        json_data["sVerify"] = self._get_cshis6_verify()
        json_data["sub"] = self._get_sub()

        return json_data

    def _get_cshis5_json(self):
        cshis_x = class_utils.get_cshisx(self.database, self.system_settings)
        random_number, signature = cshis_x.VPNH_SignX(card_type='4', service_type='91')

        sam_card_info = cshis_x.GetSAMCardInfoInCS()
        sam_card_json = json.loads(sam_card_info)

        sSamId = sam_card_json['SAMCardInfoInCS']['SAM'][0]['CARD_ID']
        patient_card_no = patient_utils.get_card_no(self.database, self.patient_id)
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        hpc_card_no = ic_card.read_hpc_card_no()

        json_data = {}
        json_data["sHospId"] = self.system_settings.field('院所代號')
        json_data["sHcaId"] = self.doctor_id
        json_data["sPatId"] = self.patient_id
        json_data["sPatCardType"] = "2"  # 1:虛擬卡 2:實體卡
        json_data["sHcaCardId"] = hpc_card_no
        json_data["sPatCardId"] = patient_card_no  # 健保卡卡號
        json_data["sClientRandom"] = random_number
        json_data["sSignature"] = signature
        json_data["vhcCloudToken"] = ''
        json_data["sSamId"] = sSamId
        json_data["sub"] = self._get_sub()

        return json_data

    def _get_request(self):
        if self.system_settings.field('讀卡機控制軟體版本') == 'cshis6':
            url = 'https://medcloudws2.nhi.gov.tw/api/imie5000/GetMedPrtInfo'
            json_data = self._get_cshis6_json()
        else:
            url = 'https://medcloudws2.nhi.gov.tw/api/imie5000/GetMedPrtData'
            json_data = self._get_cshis5_json()

        response = requests.post(
            url, json=json_data, headers=HEADERS, verify=False)

        error_code = response.status_code

        return error_code, response.json()

    def _set_table_widget_prescript(self):
        self.ui.tableWidget_conflict_drug.setRowCount(0)
        for row_no in range(self.table_widget_prescript.rowCount()):
            ins_code_item = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['InsCode'])
            if ins_code_item is None:
                continue

            ins_code = ins_code_item.text().strip()
            if ins_code == '':
                continue

            medicine_name = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']).text()
            medicine = [ins_code, medicine_name, '無交互作用']

            index = self.ui.tableWidget_conflict_drug.rowCount()
            self.ui.tableWidget_conflict_drug.setRowCount(index + 1)
            for col_no in range(len(medicine)):
                self.ui.tableWidget_conflict_drug.setItem(
                    index, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(medicine[col_no]))
                )

    def _get_sub(self):
        sub_list = []
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            ins_code = self.ui.tableWidget_conflict_drug.item(row_no, 0).text()
            ord_dict = {}
            ord_dict['sOrder'] = ins_code
            sub_list.append(ord_dict)

        sub_dict = {}
        sub_dict["sType"] = "09"  # 中藥 -> 西醫
        sub_dict["sub"] = sub_list

        return [sub_dict]


# 系統設定 指定診別起始號 2021-11-04
# -*- coding: UTF-8 -*-

import json

import requests
from libs import (class_utils, date_utils, prescript_utils, string_utils,
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

        try:
            json_content = self._convert_xml_to_json(response_content)
            if not json_content:
                self._show_connection_error('雲端回傳格式錯誤（無 JSON 資料）')
                return

            json_dict = json.loads(json_content)
        except Exception:
            self._show_connection_error('雲端回傳資料解析失敗')
            return

        if json_dict.get('RtnCode') != '00':
            # 可以視情況顯示 json_dict.get('RtnMsg') 之類的
            return

        try:
            return_number = json_dict['sub'][0]['RtnNum']
        except Exception:
            # 結構和預期不同
            return

        if return_number == 0:
            return

        result_list = json_dict['sub'][0]['sub']
        self._display_order_message(result_list)

        self.ui.tableWidget_conflict_drug.resizeRowsToContents()

    def _display_order_message(self, result_list):
        for result_dict in result_list:
            ins_code = result_dict['oOrder']
            effect = result_dict['Effect']
            mechanism = result_dict['Mechanism']
            management = result_dict['Management']
            try:
                sub = self._extract_sub(result_dict['sub'])
            except Exception:
                sub = ''

            order_message = f'交互作用結果: {effect}\n機轉: {mechanism}\n處置方式: {management}\n{sub}'

            self._set_message_item(ins_code, order_message)

    def _extract_sub(self, sub_list):
        result = '開立藥品機構:'
        for sub in sub_list:
            func_date = date_utils.nhi_date_to_west_date(sub["FuncDT"])
            result += f'\n{sub["HospName"]}\t{func_date}  {sub["DDIATC7Name"]}'

        return result

    def _set_message_item(self, in_ins_code, order_message):
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            ins_code = self.ui.tableWidget_conflict_drug.item(row_no, 0).text()
            if in_ins_code == ins_code:
                self.ui.tableWidget_conflict_drug.setItem(
                    row_no, 2, QtWidgets.QTableWidgetItem(string_utils.xstr(order_message))
                )
                break

    # def _convert_xml_to_json(self, xml):
    #     json_content = xml.split('<GetDDIDataResult>')[1]
    #     json_content = json_content.split('</GetDDIDataResult>')[0]

    #     return json_content

    def _convert_xml_to_json(self, xml):
        start_tag = '<GetDDIDataResult>'
        end_tag = '</GetDDIDataResult>'

        start_idx = xml.find(start_tag)
        end_idx = xml.find(end_tag)
        if start_idx == -1 or end_idx == -1:
            # 找不到標籤就回傳 None 或 raise 自訂例外，再上層處理
            return None

        start_idx += len(start_tag)
        json_content = xml[start_idx:end_idx]
        return json_content
    
    def _get_cshis6_request(self):
        service_path = "/api/hc/v1/Signature/HpcHc"
        url = 'https://medcloudws2.nhi.gov.tw/api/imie5000/GetMedPrtInfo'
        data = {'serviceType': '91'}

        response = self._get_requests_response(service_path, 'POST', data)
        response = requests.post(
            url, json=data, headers=HEADERS, verify=False)

        return response.json()

    def _get_request(self):
        if self.system_settings.field('讀卡機控制軟體版本') == 'cshis6':
            response = self._get_cshis6_request()
        else:
            response = self._get_cshis6_request()

        error_code = 0

        return error_code, response

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

    def _get_upload_json(self):
        upload_dict = {}
        upload_dict['sHospId'] = self.system_settings.field('院所代號')
        upload_dict['sHcaId'] = self.doctor_id
        upload_dict['sPatId'] = self.patient_id
        upload_dict['sub'] = [self._get_sub()]

        upload_json = json.dumps(upload_dict)

        return upload_json

    def _get_sub(self):
        sub_list = []
        for row_no in range(self.ui.tableWidget_conflict_drug.rowCount()):
            ins_code = self.ui.tableWidget_conflict_drug.item(row_no, 0).text()
            ord_dict = {}
            ord_dict['sOrder'] = ins_code
            sub_list.append(ord_dict)

        sub_dict = {}
        sub_dict['sType'] = 'D'  # 中藥 -> 西醫
        sub_dict['sub'] = sub_list

        return sub_dict


# 病歷登錄之病名詞庫 2014.09.22
# -*- coding: UTF-8 -*-

import json

from libs import (case_utils, class_utils, db_utils, icd10_utils, nhi_utils,
                  string_utils, system_utils, ui_utils)
from libs.alleypin_utils import change_appointment
from PyQt5 import QtCore, QtGui, QtWidgets


# 外因碼詞庫 (from 病歷登錄)
class DialogExternalCauses(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExternalCauses, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.line_edit_icd_code2 = args[3]
        self.line_edit_disease_name2 = args[4]

        self.ui = None
        self._set_variables()

        self._set_ui()
        self._set_signal()
        self._read_json_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_variables(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXTERNAL_CAUSES, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setText('選取')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self.table_widget_groups = class_utils.get_table_widget(self.ui.tableWidget_groups, self.database)
        self.table_widget_groups_name = class_utils.get_table_widget(self.ui.tableWidget_groups_name, self.database)
        self.table_widget_disease = class_utils.get_table_widget(self.ui.tableWidget_disease, self.database)
        self.table_widget_disease.set_column_hidden([0])

        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_changed)
        self.ui.tableWidget_groups_name.itemSelectionChanged.connect(self.groups_name_changed)
        self.ui.tableWidget_disease.doubleClicked.connect(self.accepted_button_clicked)

    # 存檔
    def accepted_button_clicked(self):
        icd10_key = self.table_widget_disease.field_value(0)
        db_utils.increment_hit_rate(self.database, 'icd10', 'ICD10Key', icd10_key)

        self.line_edit_icd_code2.setText(self.table_widget_disease.field_value(1))
        self.line_edit_disease_name2.setText(self.table_widget_disease.field_value(2))

        self.close()

    # 關閉
    def rejected_button_clicked(self):
        self.close()

    # 設定欄位寬度
    def _set_table_width(self):
        groups_name_width = [550]
        disease_width = [100, 150, 600]
        self.table_widget_disease.set_table_heading_width(disease_width)
        self.table_widget_groups_name.set_table_heading_width(groups_name_width)

    def _read_json_data(self):
        # 讀取 JSON 檔
        with open("icd10_external_causes.json", "r", encoding="utf-8") as f:
            self.json_data = json.load(f)

        # 取得外因碼資料列表
        self.categories = self.json_data["ICD10_External_Causes_Common_50"]

        self._set_groups_data()

    def _set_groups_data(self):
        # 用 for 迴圈印出每個 category 與 codes
        groups = []
        for category_data in self.categories:
            category_name = category_data["category"]
            groups.append(category_name)

        self.table_widget_groups.set_db_data_by_list(groups)

    def groups_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        groups = self.ui.tableWidget_groups.selectedItems()[0].text()
        self._set_groups_name(groups)

    def _set_groups_name(self, groups):
        groups_name_list = []
        for categroy_data in self.categories:
            category_name = categroy_data['category']
            if category_name == groups:
                codes = categroy_data['codes']
                for groups_name in codes:
                    groups_name_list.append(groups_name['desc'])
                    
                break

        self.ui.tableWidget_groups_name.setRowCount(0)
        for row_no, groups_name in enumerate(groups_name_list):
            self.ui.tableWidget_groups_name.setRowCount(row_no + 1)
            self.ui.tableWidget_groups_name.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(groups_name)
            )

        self.ui.tableWidget_groups_name.setCurrentCell(0, 0)

    def groups_name_changed(self):
        # 取得目前選擇的 groups（大分類）
        if not self.ui.tableWidget_groups.selectedItems():
            return
        current_group = self.ui.tableWidget_groups.selectedItems()[0].text()

        # 取得目前選擇的 disease 名稱
        selected_desc = self.table_widget_groups_name.field_value(0)

        # 從 JSON 尋找對應的 code
        selected_code = None
        for category_data in self.categories:
            if category_data["category"] == current_group:
                for code_info in category_data["codes"]:
                    if code_info["desc"] == selected_desc:
                        selected_code = code_info["code"]
                        break
                break

        if selected_code:
            self._set_icd_external_causes(selected_code)

    def _set_icd_external_causes(self, icd10_prefix):
        sql = f'''
            SELECT * FROM icd10
            WHERE
                (ICDCode LIKE "{icd10_prefix}%" AND LENGTH(ICDCode) >= 7) OR
                (ICDCode LIKE "{icd10_prefix}%" AND ICDCode LIKE "Y93%" AND LENGTH(ICDCode) >= 5)
            ORDER BY ICDCode
        '''
        self.table_widget_disease.set_db_data(sql, self._set_disease_data)

    def _set_disease_data(self, row_no, row):
        icd_code = string_utils.xstr(row['ICDCode'])
        disease_row = [
            string_utils.xstr(row['ICD10Key']),
            icd_code,
            string_utils.xstr(row['ChineseName']),
        ]
        for column in range(len(disease_row)):
            self.ui.tableWidget_disease.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(disease_row[column])
            )


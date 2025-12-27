
# 病名詞庫設定 2024.04.08
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 主視窗
class DialogInputDisease(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputDisease, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.groups_name = args[2]
        self.call_from = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_DISEASE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_disease = class_utils.get_table_widget(self.ui.tableWidget_disease, self.database)
        self.table_widget_disease.set_column_hidden([0])
        self.ui.label_groups_name.setText(self.groups_name)
        self._set_table_width()
        self.ui.lineEdit_keyword.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.lineEdit_keyword.textChanged.connect(self.keyword_text_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_disease.doubleClicked.connect(self._disease_double_clicked)

    def _disease_double_clicked(self):
        self.accepted_button_clicked()
        self.ui.lineEdit_keyword.setText(None)
        self.close()

    def accepted_button_clicked(self):
        if self.call_from == '病名詞庫':
            self._update_icd10()
        elif self.call_from == '自訂病名':
            self._update_custom_disease()

    def _update_icd10(self):
        selected = self.ui.tableWidget_disease.selectedRanges()
        icd10_list = []
        for item in selected:
            for r in range(item.topRow(), item.bottomRow() + 1):
                icd10_list.append(self.ui.tableWidget_disease.item(r, 0).text())

        for icd10 in icd10_list:
            sql = f'''
                UPDATE icd10
                SET
                    Groups = "{self.groups_name}"
                WHERE
                    ICD10Key = {icd10}'''
            self.database.exec_sql(sql)

        self.parent.read_dict_disease(self.groups_name)

    def _update_custom_disease(self):
        selected = self.ui.tableWidget_disease.selectedRanges()
        field = ['GroupsName', 'ICDCode']

        icd10_list = []
        for item in selected:
            for r in range(item.topRow(), item.bottomRow() + 1):
                icd10_list.append(self.ui.tableWidget_disease.item(r, 1).text())

        for icd_code in icd10_list:
            data = [self.groups_name, icd_code]
            self.database.insert_record('custom_disease', field, data)

        self.parent.read_dict_disease(self.groups_name)

    # 設定欄位寬度
    def _set_table_width(self):
        disease_width = [100, 120, 550]
        self.table_widget_disease.set_table_heading_width(disease_width)

    def keyword_text_changed(self):
        keyword = str(self.ui.lineEdit_keyword.text()).strip()
        if keyword == '':
            self.ui.tableWidget_disease.setRowCount(0)
            return

        self._read_icd10(keyword)
        self.ui.lineEdit_keyword.setFocus(True)
        self.ui.lineEdit_keyword.setCursorPosition(len(keyword))

    def _read_icd10(self, icd10):
        english_name_condision = ''

        if len(icd10) >= 4:
            english_name_condision = f'OR EnglishName like "%{icd10}%"'

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICDCode like "%{icd10}%" OR
                InputCode like "%{icd10}%" OR
                ChineseName like "%{icd10}%"
                {english_name_condision}
        '''
        self.table_widget_disease.set_db_data(sql, self._set_disease)

    def _set_disease(self, rec_no, rec):
        disease_rec = [
            string_utils.xstr(rec['ICD10Key']),
            string_utils.xstr(rec['ICDCode']),
            string_utils.xstr(rec['ChineseName']),
        ]

        for column in range(len(disease_rec)):
            self.ui.tableWidget_disease.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(disease_rec[column])
            )

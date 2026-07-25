
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils


# 主視窗
class DialogEditDisease(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogEditDisease, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        try:
            self.icd10_key = args[2]
        except IndexError:
            self.icd10_key = None

        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.icd10_key is not None:
            self._edit_disease()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EDIT_DISEASE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_input_code.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _edit_disease(self):
        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICD10Key = {self.icd10_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self.ui.lineEdit_icd10_code.setText(row_data['ICDCode'])
        self.ui.lineEdit_input_code.setText(row_data['InputCode'])
        self.ui.lineEdit_special_code.setText(row_data['SpecialCode'])
        self.ui.lineEdit_disease_name.setText(row_data['ChineseName'])

    def accepted_button_clicked(self):
        if self.icd10_key is None:
            return

        fields = ['InputCode', 'SpecialCode', 'ChineseName']
        data = [
            self.ui.lineEdit_input_code.text(),
            self.ui.lineEdit_special_code.text(),
            self.ui.lineEdit_disease_name.text(),
        ]

        self.database.update_record('icd10', fields, 'ICD10Key', self.icd10_key, data)

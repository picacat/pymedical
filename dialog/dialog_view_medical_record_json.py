
# 查看刪除病歷內容 2022.01.10
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import case_utils


# 主視窗
class DialogViewMedicalRecordJSON(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogViewMedicalRecordJSON, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.backup_records_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self._view_medical_record_json()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_VIEW_MEDICAL_RECORD_JSON, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _view_medical_record_json(self):
        html = case_utils.get_medical_record_html_from_json(
            self.database, self.system_settings, self.backup_records_key)
        self.ui.textEdit_medical_record.setReadOnly(True)
        self.ui.textEdit_medical_record.setHtml(html)

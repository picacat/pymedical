
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import number_utils
from libs import date_utils


# 更改健保資料
class DialogInsListEdit(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsListEdit, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ins_apply_key = args[2]
        self.sequence = args[3]
        self.case_date = args[4]
        self.end_date = args[5]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_LIST_EDIT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.spinBox_sequence.setValue(number_utils.get_integer(self.sequence))
        self.ui.dateEdit_case_date.setDate(date_utils.str_to_date(self.case_date))
        self.ui.dateEdit_end_date.setDate(date_utils.str_to_date(self.end_date))
        self.ui.spinBox_sequence.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        fields = ['Sequence', 'CaseDate', 'StopDate']
        data = [
            self.ui.spinBox_sequence.value(),
            self.ui.dateEdit_case_date.date().toString('yyyy/MM/dd'),
            self.ui.dateEdit_end_date.date().toString('yyyy/MM/dd'),
        ]

        self.database.update_record('insapply', fields, 'InsApplyKey',
                                    self.ins_apply_key, data)

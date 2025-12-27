
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils


# 主視窗
class DialogDatePicker(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDatePicker, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DATE_PICKER, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self._set_combo_box()
        if self.call_from in [None, 'by_month', 'by_year']:
            self.ui.groupBox_doctor.setVisible(False)

        if self.call_from == 'by_year':
            self.ui.groupBox.setTitle('請選擇年度')
            self.ui.comboBox_month.setVisible(False)
            self.ui.label_month.setVisible(False)
        elif self.call_from == 'by_month':
            self.ui.comboBox_year.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _set_combo_box(self):
        year_list = []
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        for i in range(current_year, current_year - 10, -1):
            year_list.append(str(i))

        ui_utils.set_combo_box(self.ui.comboBox_year, year_list)
        self.ui.comboBox_year.setCurrentText(str(current_year))
        self.ui.comboBox_month.setCurrentText(str(current_month))

        doctor_list = personnel_utils.get_person(self.database, '醫師', None)
        doctor_list.insert(0, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)

    def accepted_button_clicked(self):
        pass

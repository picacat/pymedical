
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import datetime
import calendar

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogDatePeriod(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDatePeriod, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DATE_PERIOD, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        # self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        # self.ui.dateEdit_end_date.setDate(datetime.datetime.now())

        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        last_day = calendar.monthrange(year, month)[1]

        self.ui.dateEdit_start_date.setDate(QtCore.QDate(year, month, 1))
        self.ui.dateEdit_end_date.setDate(QtCore.QDate(year, month, last_day))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def set_title(self, caption):
        self.ui.groupBox_duration.setTitle(caption)

    def accepted_button_clicked(self):
        pass

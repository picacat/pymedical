
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogCalendar(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCalendar, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        try:
            self.call_from = args[2]
        except Exception:
            self.call_from = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CALENDAR, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.calendarWidget.setSelectedDate(QtCore.QDate.currentDate())

        if self.call_from not in ['輸入主訴']:
            self.ui.checkBox_infectious_date.setVisible(False)
            self.ui.checkBox_injury.setVisible(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

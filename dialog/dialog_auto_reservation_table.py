
# 自動設定預約一覽表 2021.12.10
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogAutoReservationTable(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAutoReservationTable, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.period = args[2]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_AUTO_RESERVATION_TABLE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.ui.spinBox_start_no.setValue(2)
        self.ui.spinBox_interval_no.setValue(2)

        start_time = 8, 0
        end_time = 12, 0

        if self.period == '早班':
            start_time = (9, 0)
            end_time = (12, 0)
        elif self.period == '午班':
            start_time = (14, 0)
            end_time = (18, 0)
        elif self.period == '晚班':
            start_time = (18, 0)
            end_time = (22, 0)

        start_hour, start_minute = start_time
        end_hour, end_minute = end_time
        self.ui.timeEdit_start_time.setTime(QtCore.QTime(start_hour, start_minute))
        self.ui.timeEdit_end_time.setTime(QtCore.QTime(end_hour, end_minute))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

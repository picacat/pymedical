
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogSchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.time_list = args[2]
        self.default_time_list = [
            '09:00', '10:00', '11:00', '12:00', '13:00',
            '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'
        ]
        if self.time_list is None:
            self.time_list = self.default_time_list

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.calendarWidget.setSelectedDate(QtCore.QDate.currentDate())
        self._set_time_list()

    def _set_time_list(self):
        self.ui.listWidget_time.clear()
        for time in self.time_list:
            list_item = QtWidgets.QListWidgetItem(time)
            list_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.ui.listWidget_time.addItem(list_item)

        self.ui.listWidget_time.setCurrentRow(0)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def get_selected_date(self):
        selected_date = self.ui.calendarWidget.selectedDate().toString('yyyy-MM-dd')

        return selected_date

    def get_selected_time(self):
        selected_time = self.ui.listWidget_time.currentItem().text()

        return selected_time


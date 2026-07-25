
# 系統設定 指定診別起始號 2021-11-04
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils


# 主視窗
class DialogStartNo(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogStartNo, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.room = args[2]
        self.start_no_1 = args[3]
        self.start_no_2 = args[4]
        self.start_no_3 = args[5]
        self.exclude_room = args[6]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

        if self.room is not None:
            self._set_start_no_settings()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_START_NO, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog

        doctor_list = personnel_utils.get_person(self.database, '醫師')
        room_list = [str(i) for i in range(1, 21)]
        if len(room_list) <= 0:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).hide()
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('人數已滿, 取消編輯')
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
            
        ui_utils.set_combo_box(self.ui.comboBox_room, doctor_list + room_list)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _set_start_no_settings(self):
        self.ui.comboBox_room.setCurrentText(self.room)
        self.ui.spinBox_start_no_1.setValue(int(self.start_no_1))
        self.ui.spinBox_start_no_2.setValue(int(self.start_no_2))
        self.ui.spinBox_start_no_3.setValue(int(self.start_no_3))

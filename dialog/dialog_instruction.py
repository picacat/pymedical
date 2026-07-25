
# 服用方式 2023.10.10
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogInstruction(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInstruction, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INSTRUCTION, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def get_instruction(self):
        instruction = ''

        if self.ui.lineEdit_hour.text().strip() != '':
            instruction += f'每{self.ui.lineEdit_hour.text()}小時'
        else:
            if self.ui.checkBox_meal.isChecked():
                instruction += '三餐'
            if self.ui.checkBox_meal1.isChecked():
                instruction += '早餐'
            if self.ui.checkBox_meal2.isChecked():
                instruction += '中餐'
            if self.ui.checkBox_meal3.isChecked():
                instruction += '晚餐'

            if self.ui.radioButton_ac.isChecked():
                instruction += '飯前'
            elif self.ui.radioButton_pc.isChecked():
                instruction += '飯後'

            if self.ui.checkBox_bs.isChecked():
                instruction += '睡前'

        if self.ui.lineEdit_dosage.text().strip() != '':
            if self.ui.radioButton_unit1.isChecked():
                unit = '尖匙'
            elif self.ui.radioButton_unit2.isChecked():
                unit = '平匙'
            elif self.ui.radioButton_unit3.isChecked():
                unit = '顆'
            elif self.ui.radioButton_unit4.isChecked():
                unit = '包'

            instruction += f', 每次{self.ui.lineEdit_dosage.text()}{unit}'

        return instruction


# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogElectricAcupuncture(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogElectricAcupuncture, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ELECTRIC_ACUPUNCTURE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def get_electric_acupuncture_list(self):
        if self.ui.radioButton_1.isChecked():
            radio_button = self.ui.radioButton_1
        elif self.ui.radioButton_2.isChecked():
            radio_button = self.ui.radioButton_2
        elif self.ui.radioButton_3.isChecked():
            radio_button = self.ui.radioButton_3
        else:
            radio_button = None

        if radio_button is not None:
            wave = radio_button.text()
        else:
            wave = ''

        wave = f'波形:{wave}'
        freq = f'頻率:{self.ui.spinBox_freq.value()}Hz'
        time = f'時間:{self.ui.spinBox_time.value()}分鐘'

        electric_acupuncture_list = [
            wave, freq, time
        ]

        return electric_acupuncture_list

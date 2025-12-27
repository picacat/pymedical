
# 複雜性針灸選取視窗 2021.02.24
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils


# 主視窗
class DialogTreatTime(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTreatTime, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.diag_time = args[2]
        self.treatment = args[3]
        self.second_treatment = args[4]

        if self.diag_time is None:
            self.diag_time = datetime.datetime.now()

        self.ui = None
        self.treat_time_list = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TREAT_TIME, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(self.treatment)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.treatment in [
            '一般針灸', '電針', '中度複雜性針灸', '一般傷科', '中度複雜性傷科'
        ] and self.second_treatment in [None, '']:
            minutes = 10
        elif self.treatment in [
            '高度複雜性針灸', '高度複雜性傷科', '中度複雜性傷科合併特殊疾病', '脫臼整復復位', '骨折復位'
        ] and self.second_treatment in [None, '']:
            minutes = 20
        elif '一般' in self.treatment and '中度' in self.second_treatment:
            minutes = 10
        elif '一般' in self.treatment and '高度' in self.second_treatment:
            minutes = 20
        elif '中度' in self.treatment and '中度' in self.second_treatment:
            minutes = 10
        elif '中度' in self.treatment and '高度' in self.second_treatment:
            minutes = 20
        elif '高度' in self.treatment and '中度' in self.second_treatment:
            minutes = 20
        elif '高度' in self.treatment and '高度' in self.second_treatment:
            minutes = 20
        else:
            minutes = 20

        self.ui.spinBox_time.setMinimum(minutes)
        self.ui.spinBox_time.setValue(minutes)

        self.ui.timeEdit_start_time.setTime(self.diag_time.time())
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(minutes * 60)
        )
        self.ui.timeEdit_start_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)
        self.ui.timeEdit_end_time.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)

    def _set_treat_time(self):
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(self.ui.spinBox_time.value() * 60)
        )

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

        self.ui.timeEdit_start_time.timeChanged.connect(self._set_treat_time)
        self.ui.timeEdit_end_time.timeChanged.connect(self._set_treat_time)
        self.ui.spinBox_time.valueChanged.connect(self._set_treat_time)

    def accepted_button_clicked(self):
        self.treat_time_list = [
            f'治療時間:{self.ui.spinBox_time.value()}分鐘',
            f'治療開始:{self.ui.timeEdit_start_time.time().toString("hh:mm")}',
            f'治療結束:{self.ui.timeEdit_end_time.time().toString("hh:mm")}',
        ]

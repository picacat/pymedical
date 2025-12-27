#!/usr/bin/env python3
#coding: utf-8

import sys

from PyQt5 import QtWidgets, QtGui
from libs import ui_utils
from libs import string_utils


# 樣板 2018.01.31
class ChooseDoctor(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(ChooseDoctor, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHOOSE_DOCTOR, self)
        style = '''
            QMainWindow#WindowChooseDoctor 
            {background-image: url(./images/home.jpg);}
        '''
        self.ui.setStyleSheet(style)
        self.ui.label_message.setStyleSheet("QLabel {color : white; }")
        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setBlurRadius(0)
        effect.setColor(QtGui.QColor('black'))
        effect.setOffset(1, 2)
        self.ui.label_message.setGraphicsEffect(effect)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_doctor1.clicked.connect(self._doctor_clicked)
        self.ui.toolButton_doctor2.clicked.connect(self._doctor_clicked)
        self.ui.toolButton_doctor3.clicked.connect(self._doctor_clicked)
        self.ui.toolButton_doctor4.clicked.connect(self._doctor_clicked)

    def set_doctor_buttons(self, basic_data, doctor_schedule_rows, weekday):
        self.basic_data = basic_data

        buttons_list = [
            self.ui.toolButton_doctor1,
            self.ui.toolButton_doctor2,
            self.ui.toolButton_doctor3,
            self.ui.toolButton_doctor4,
        ]

        for button in buttons_list:
            button.setVisible(False)

        for index, doctor in zip(range(len(doctor_schedule_rows)), doctor_schedule_rows):
            buttons_list[index].setVisible(True)
            buttons_list[index].setText(string_utils.xstr(doctor[weekday]))


    def _doctor_clicked(self):
        doctor = self.sender().text()
        self.parent.open_registration(
            self.basic_data, '門診掛號', doctor, None, None,
        )


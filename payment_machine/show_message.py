#!/usr/bin/env python3
#coding: utf-8

import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer

from libs import ui_utils
from libs import string_utils

WAIT_SECONDS = 4


# 樣板 2018.01.31
class ShowMessage(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(ShowMessage, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_SHOW_MESSAGE, self)
        style = '''
            QMainWindow#WindowShowMessage
            {background-image: url(./images/pycashier_bg.jpg);}
        '''
        self.ui.setStyleSheet(style)

        effect = QtWidgets.QGraphicsDropShadowEffect()
        effect.setBlurRadius(0)
        effect.setColor(QtGui.QColor('black'))
        effect.setOffset(1, 2)

        self.ui.label_message.setStyleSheet("QLabel {color : white; }")
        self.ui.label_count_down.setStyleSheet("QLabel {color : white; }")

        self.ui.label_message.setGraphicsEffect(effect)
        # self.ui.label_count_down.setGraphicsEffect(effect)

    # 設定信號
    def _set_signal(self):
        pass

    def show_message(self, message):
        self.message = message

        self.ui.label_message.setText(self.message)
        self.ui.label_count_down.setText(string_utils.xstr(WAIT_SECONDS))

        self.loop = 0
        # 在类中定义一个定时器,并在构造函数中设置启动及其信号和槽
        self.timer = QTimer(self)
        # 设置计时间隔并启动(1000ms == 1s)
        self.timer.start(1000)
        # 计时结束调用timeout_slot()方法,注意不要加（）
        self.timer.timeout.connect(self.timeout)

    def timeout(self):
        self.loop += 1
        count_down = WAIT_SECONDS - self.loop
        self.ui.label_count_down.setText(string_utils.xstr(count_down))

        if self.loop >= WAIT_SECONDS:
            self.timer.stop()
            self._back_home()

    def _back_home(self):
        self.parent.open_pycashier_home()


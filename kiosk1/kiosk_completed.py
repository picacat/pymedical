# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import os

from libs import ui_utils
from libs import system_utils


# 2025.01.06 掛號機繳費完成頁面
class KioskCompleted(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskCompleted, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.timer = QtCore.QTimer(self)
        self.wait_seconds = 10

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
        self.ui = ui_utils.load_ui_file(os.path.join(self.parent.UI_DIR, 'kiosk_home.ui'), self)
        self.set_background()

    # 設定信號
    def _set_signal(self):
        self.timer.timeout.connect(self._timeout)

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

    def set_background(self):
        label_background = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, 'background.png'), 0, 0)
        self._bring_to_front(label_background)

        label_header = system_utils.set_label(
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.LIGHT_TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.LIGHT_TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '請等待叫號看診', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

    def _set_back_home_button(self, button_text):
        self.wait_seconds = 10

        self.button_text = button_text
        color = self.parent.DARK_GREEN
        x, y = 300, 1400
        self.push_button = QtWidgets.QPushButton(self)
        self.push_button.resize(500, 100)
        self.push_button.setText(f'{button_text}({self.wait_seconds}s)')
        self.push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 56pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        self.push_button.move(x, y)
        self.push_button.raise_()
        self.push_button.show()
        self.push_button.clicked.connect(self._back_to_home)

    def _back_to_home(self):
        self.timer.stop()
        self.parent.open_kiosk_home()

    def set_completed(self, treat_type):
        self.clear_all_widgets()
        self.set_background()

        x = 170
        y = 700
        height = 120

        hint = []
        if treat_type == '內科':
            hint.append(f'<font color="{self.parent.DARK_RED}">將健保卡交給醫師</font>')
        else:
            hint.append(f'<font color="{self.parent.DARK_RED}">將健保卡交給</font>')
            hint.append(f'<font color="{self.parent.DARK_RED}">現場人員</font>')

        message_list = [
            '掛號繳費完成',
            '請取回健保卡',
            '並於就診時',
        ]
        message_list.extend(hint)

        for message in message_list:
            label_header = system_utils.set_label(
                self, message, x, y, self.parent.TEXT_FONT, 72, self.parent.TEXT_COLOR)
            self._bring_to_front(label_header)
            y += height

        self._set_back_home_button('掛號完成')

        self.wait_seconds = 10
        self.timer.start(1000)

    def _timeout(self):
        self.wait_seconds -= 1
        self.push_button.setText(f'{self.button_text}({self.wait_seconds}s)')
        if self.wait_seconds == 0:
            self.timer.stop()
            self._back_to_home()

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

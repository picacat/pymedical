# -*- coding: utf-8 -*-

import os

from libs import case_utils, system_utils, ui_utils
from PyQt5 import QtCore, QtWidgets


# 2025.01.06 掛號機繳費完成頁面
class KioskCompleted(QtWidgets.QMainWindow):
    TITLE_Y = 140
    LINE1_Y = 260
    LINE2_Y = 350
    LINE3_Y = 440
    LINE4_Y = 530
    BUTTON_Y = 550
    ICON_Y = 620
    ICON_W = 160
    ICON_H = 160

    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskCompleted, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.home_timer = QtCore.QTimer(self)
        self.home_timer.timeout.connect(self._timeout)
        self.wait_seconds = 20

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
        pass

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
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

        png_filename = self._get_png_file_name('ok.png')
        label_image = system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)
        self._bring_to_front(label_image)

        label_header = system_utils.set_label(
            self, '作業完成', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)
        self._bring_to_front(label_header)

    def _get_png_file_name(self, filename):
        png_name = os.path.join(self.parent.IMAGE_DIR, filename)

        return png_name

    def _set_back_home_button(self, button_text):
        self.button_text_home = button_text
        self.wait_seconds = 20
        color = self.parent.DARK_GREEN
        x, y = 300, 1400

        self.push_button_home = QtWidgets.QPushButton(self)
        self.push_button_home.resize(500, 100)
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        self.push_button_home.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 42pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        system_utils.shadow_widget(self, self.push_button_home)
        self.push_button_home.move(x, y)
        self.push_button_home.raise_()
        self.push_button_home.show()
        self.push_button_home.clicked.connect(self._back_to_home)

        self.home_timer.start(1000)

    def _timeout(self):
        # 如果視窗已經被關掉 / 看不到，就不要再跑倒數
        if not self.isVisible():
            self.home_timer.stop()
            return

        self.wait_seconds -= 1
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        if self.wait_seconds == 0:
            self._back_to_home()

    def _back_to_home(self):
        self.home_timer.stop()
        self.parent.open_kiosk_home()

    def set_completed(self, op_type, case_key, change_due):
        self.clear_all_widgets()
        self.set_background()

        height = 120

        y = 1000
        message_list = []
        if op_type == '預約報到':
            x = 200
            message_list.append(f'<font color="{self.parent.DARK_RED}">預約報到完成！</font>')
            message_list.append(f'<font color="{self.parent.DARK_GREEN}">請至候診區等候</font>')
            if case_key:
                regist_no = case_utils.get_case_field_value(self.database, case_key, 'RegistNo')
                message_list.append(f'您的診號為{regist_no}號')
        else:
            x = 220
            message_list.append(f'<font color="{self.parent.DARK_RED}">批價繳費完成</font>')
            message_list.append(f'<font color="{self.parent.DARK_GREEN}">請持收據領藥</font>')
            if change_due > 0:
                y = 830
                message_list.append(f'''
                    <font color="{self.parent.DARK_RED}">
                        您有找零 {change_due} 元
                    </font>
                ''')
                message_list.append(f'''
                    <font color="{self.parent.DARK_RED}">
                        別忘了取回唷!
                    </font>
                ''')

        for message in message_list:
            label_header = system_utils.set_label(
                self, message, x, y, self.parent.TEXT_FONT, 72, self.parent.TEXT_COLOR)
            self._bring_to_front(label_header)
            y += height

        self._set_back_home_button('回首頁')

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

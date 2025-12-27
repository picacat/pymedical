from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt

import os
from libs import number_utils
from libs import string_utils
from libs import system_utils
from libs import ui_utils


# 輸入分院資料
class DialogMessageBox(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMessageBox, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(os.path.join(self.parent.UI_DIR, 'dialog_message_box.ui'), self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        image_file = os.path.join(self.parent.BASE_DIR, 'kiosk1', 'images', 'message_box.png')
        image_file = image_file.replace('\\', '/')

        self.setStyleSheet(f"""
            QDialog {{
                background-image: url({image_file});  /* 設置背景圖片路徑 */
                background-repeat: no-repeat;
                background-position: center;
                font: 75 24pt "{self.parent.TEXT_FONT}";
            }}
        """)
        self.move(70, 650)

    # 設定信號
    def _set_signal(self):
        pass

    def _set_back_home_button(self, button_text):
        color = self.parent.DARK_GREEN
        x, y = 280, 580
        push_button = QtWidgets.QPushButton(self)
        push_button.resize(400, 80)
        push_button.setText('返回首頁(10s)')
        push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 36pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        push_button.move(x, y)
        push_button.clicked.connect(self.close)

        wait_seconds = 10
        timer = QtCore.QTimer(self)
        timer.start(1000)

        def _timeout():
            nonlocal wait_seconds
            wait_seconds -= 1
            push_button.setText(f'{button_text}({wait_seconds}s)')
            if wait_seconds == 0:
                timer.stop()
                self.close()

        timer.timeout.connect(_timeout)

    def _get_png_file_name(self, filename):
        png_name = os.path.join(self.parent.IMAGE_DIR, filename)

        return png_name

    def set_no_iccard(self):
        system_utils.set_label(
            self, '系統未偵測到健保卡！', 210, 180,
            self.parent.TEXT_FONT, 56, self.parent.RED, center=True)
        system_utils.set_label(
            self, '請重新插入健保卡', 110, 320,
            self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR, center=True)
        system_utils.set_label(
            self, '（未帶健保卡請至櫃檯掛號）', 90, 400,
            self.parent.TEXT_FONT, 48, self.parent.DARK_GREEN, center=True)

        self._set_back_home_button('返回首頁')

    def set_in_progress(self):
        system_utils.set_label(
            self, '健保卡讀卡中...', 120, 260, self.parent.TEXT_FONT, 56, self.parent.RED)
        system_utils.set_label(
            self, '請勿取出您的健保卡', 120, 410, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)

    def set_already_registed(self):
        system_utils.set_label(self, '您已經完成門診掛號！', 110, 260, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '如有問題，請櫃台協助', 110, 410, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('返回首頁')

    def set_deposit_card_not_return(self):
        system_utils.set_label(self, '您上次門診欠卡未還卡！', 120, 260, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請先至櫃台還卡後再掛號', 120, 410, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('返回首頁')

    def set_no_patient(self):
        system_utils.set_label(self, '系統找不到您的資料！', 120, 260, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請至櫃檯辦理初診掛號', 120, 410, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('返回首頁')

    def show_prescript_not_finished(self, start_date, end_date, pres_days, remain_days):
        x, y, height = 100, 120, 80
        font_size, font_color = 52, self.parent.TEXT_COLOR
        highlight_color = self.parent.DARK_RED
        message_data = [
            f'您在<font color="{highlight_color}">{start_date}</font>門診',
            f'拿了<font color="{highlight_color}">{pres_days}日</font>藥',
            f'截至<font color="{highlight_color}">{end_date}</font>為止',
            f'尚有<font color="{highlight_color}">{remain_days}日</font>藥未服用完畢',
            f'<font color="{highlight_color}">請洽櫃台人員</font>',
        ]
        for i, data in enumerate(message_data):
            system_utils.set_label(self, data, x, y + i * height, self.parent.TEXT_FONT, font_size, font_color)

        self._set_back_home_button('返回首頁')

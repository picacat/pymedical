from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt

import os
from libs import system_utils
from libs import ui_utils


# 輸入分院資料
class DialogMessageBox(QtWidgets.QDialog):
    TITLE_Y = 140
    LINE1_Y = 320
    LINE2_Y = 420
    LINE3_Y = 520
    LINE4_Y = 620
    BUTTON_Y = 550
    ICON_X = 400
    ICON_Y = 120
    ICON_W = 160
    ICON_H = 160

    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMessageBox, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.home_timer = QtCore.QTimer(self)
        self.home_timer.timeout.connect(self._timeout)
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

    def closeEvent(self, event):
        # 關閉視窗時，順便把回首頁的計時器停掉
        self.home_timer.stop()
        super().closeEvent(event)

    def _set_back_home_button(self, button_text, x=320, y=580):
        self.button_text_home = button_text
        self.wait_seconds = 10

        color = self.parent.DARK_GREEN

        self.push_button_home = QtWidgets.QPushButton(self)
        self.push_button_home.resize(320, 80)
        self.push_button_home.setText(f'{self.button_text_home}({self.wait_seconds}s)')
        self.push_button_home.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 36pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        system_utils.shadow_widget(self, self.push_button_home)
        self.push_button_home.move(x, y)
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

        self.close()
        self.parent.open_kiosk_home()

    def _get_png_file_name(self, filename):
        png_name = os.path.join(self.parent.IMAGE_DIR, filename)

        return png_name

    def _high_text(self, text):
        high_color = f'<font color="{self.parent.RED}">{text}</font>'

        return high_color

    # def set_in_progress(self):
    #     system_utils.set_label(
    #         self, '報到方式:',
    #         90, 140, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
    #     png_filename1 = self._get_png_file_name('barcode.png')
    #     system_utils.set_image(
    #         self, png_filename1, 120, 240, width=100, height=100)

    #     png_filename2 = self._get_png_file_name('id.png')
    #     system_utils.set_image(
    #         self, png_filename2, 120, 340, width=100, height=100)

    #     png_filename3 = self._get_png_file_name('iccard.png')
    #     system_utils.set_image(
    #         self, png_filename3, 120, 440, width=100, height=100)

    #     self._set_manual_input_button()
    #     self._set_back_home_button('回首頁', x=480, y=580)

    # def _set_manual_input_button(self):
    #     color = self.parent.RED
    #     x, y = 140, 580

    #     btn = QtWidgets.QPushButton(self)
    #     btn.resize(280, 80)
    #     btn.setText('輸入ID')
    #     btn.setStyleSheet(f"""
    #         QPushButton {{
    #             background-color: {color};
    #             border: 2px solid {color};
    #             border-radius: 10px;
    #             color: white;
    #             font: 75 36pt "{self.parent.BUTTON_FONT}";
    #         }}
    #     """)

    #     system_utils.shadow_widget(self, btn)
    #     btn.move(x, y)
    #     btn.clicked.connect(self._manual_input_id)

    # def _manual_input_id(self):
    #     # 先停倒數計時
    #     if hasattr(self, 'home_timer') and self.home_timer.isActive():
    #         self.home_timer.stop()

    #     # 關掉自己
    #     self.close()

    #     # 再由 kiosk_identity 開啟手動輸入流程
    #     # parent 是 Kiosk，widget_identity 是 KioskIdentity 實例
    #     if hasattr(self.parent, 'widget_identity'):
    #         identity = self.parent.widget_identity
    #         if hasattr(identity, 'manual_input_id_from_dialog'):
    #             identity.manual_input_id_from_dialog()

    def set_no_iccard(self):
        png_filename = self._get_png_file_name('cancel.png')
        system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)

        system_utils.set_label(
            self, '系統未偵測到健保卡！', 130, self.LINE1_Y,
            self.parent.TEXT_FONT, 52, self.parent.RED, center=True)
        system_utils.set_label(
            self, '請重新插入健保卡', 130, self.LINE2_Y,
            self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR, center=True)

        self._set_back_home_button('回首頁')

    def set_no_reservation(self):
        png_filename = self._get_png_file_name('cancel.png')
        system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)

        system_utils.set_label(self, '您今天沒有預約掛號！', 130, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請至櫃台現場掛號', 130, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_no_medical_record(self):
        png_filename = self._get_png_file_name('cancel.png')
        system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)

        system_utils.set_label(self, '您今天沒有門診記錄！', 130, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '如未掛號，請至櫃檯辦理', 90, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_not_doctor_done(self):
        png_filename = self._get_png_file_name('cancel.png')
        system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)

        system_utils.set_label(self, '您尚未完成就診', 230, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請完診後再繳費', 230, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_charge_done(self):
        png_filename = self._get_png_file_name('warning.png')
        system_utils.set_image(
            self, png_filename, self.ICON_X, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=False)

        system_utils.set_label(self, '您已經完成繳費', 230, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請勿重複繳費', 230, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_arrival_done(self):
        png_filename = self._get_png_file_name('warning.png')
        system_utils.set_image(
            self, png_filename, self.ICON_X, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=False)

        system_utils.set_label(self, '您已經完成預約報到！', 130, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '如有問題，請櫃台協助', 130, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_already_registed(self):
        png_filename = self._get_png_file_name('warning.png')
        system_utils.set_image(
            self, png_filename, self.ICON_X, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=False)

        system_utils.set_label(self, '您已經完成門診掛號！', 130, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '如有問題，請櫃台協助', 110, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

    def set_no_patient(self):
        png_filename = self._get_png_file_name('cancel.png')
        system_utils.set_image(
            self, png_filename, 0, self.ICON_Y, width=self.ICON_W, height=self.ICON_W, center=True)

        system_utils.set_label(self, '系統找不到您的資料！', 130, self.LINE1_Y, self.parent.TEXT_FONT, 52, self.parent.RED)
        system_utils.set_label(
            self, '請至櫃檯辦理初診掛號', 130, self.LINE2_Y, self.parent.TEXT_FONT, 52, self.parent.TEXT_COLOR)
        self._set_back_home_button('回首頁')

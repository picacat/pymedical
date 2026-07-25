# -*- coding: UTF-8 -*-
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QPixmap
import os

from libs import ui_utils
from libs import system_utils


# 掛號機首頁 2024.06.23
class KioskHome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskHome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.ui = None
        self.setAttribute(QtCore.Qt.WA_AcceptTouchEvents)  # 启用触控事件

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _close_app(self):
        self.parent.close_app()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(os.path.join(self.parent.UI_DIR, 'kiosk_home.ui'), self)
        self.set_background()
        self._set_push_buttons()

    # 設定信號
    def _set_signal(self):
        self.pushButton_internal_medicine.clicked.connect(self._internal_medicine_registration)
        self.pushButton_treatment.clicked.connect(self._treatment_registration)

    def _get_image_file(self, filename):
        image_file = os.path.join(self.parent.IMAGE_DIR, filename)
        image_file = image_file.replace('\\', '/')

        return image_file

    def _get_push_button(self, png_name, pressed_png, x, y, set_fixed_size=True):
        btn = QPushButton(self.ui.centralwidget)
        png_name = self._get_image_file(png_name)
        pressed_png = self._get_image_file(pressed_png)

        style = f'''
            QPushButton{{
                border: none;
                background: transparent;
                image: url({png_name});
            }}
            QPushButton:pressed {{
                image: url({pressed_png});
            }}
        '''
        btn.setStyleSheet(style)
        btn.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
        pixmap = QPixmap(png_name)
        if set_fixed_size:
            btn.setFixedSize(pixmap.size())

        btn.move(x, y)

        return btn

    def set_background(self):
        label_background = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, 'background.png'), 0, 0)
        label_background.lower()

        system_utils.set_label(
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.LIGHT_TEXT_COLOR)

        system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.LIGHT_TEXT_COLOR)

        system_utils.set_label(
            self, '先插健保卡', 180, 620, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        system_utils.set_label(
            self, '再選科別', 580, 720, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)

        system_utils.set_label(
            self, '初診、欠還卡，請洽櫃檯人員', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)

    def _set_push_buttons(self):
        x = 150

        self.pushButton_internal_medicine = self._get_push_button(
            'internal_medicine.png', 'internal_medicine.png', x, 850)

        self.pushButton_treatment = self._get_push_button(
            'treatment.png', 'treatment.png', x, 1230)

    # 內科掛號
    def _internal_medicine_registration(self):
        self.parent.open_kiosk_registration(treat_type='內科')

    # 針傷科掛號
    def _treatment_registration(self):
        self.parent.open_kiosk_registration(treat_type='針傷科')

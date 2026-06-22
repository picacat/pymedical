# -*- coding: UTF-8 -*-
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton

from libs import system_utils, ui_utils


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
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "kiosk_home.ui"), self
        )
        self.set_background()
        self._set_push_buttons()

    # 設定信號
    def _set_signal(self):
        self.pushButton_checkin.clicked.connect(self._checkin)
        self.pushButton_vhc_checkin.clicked.connect(self._vhc_checkin)
        self.pushButton_reservation.clicked.connect(self._reservation)
        self.pushButton_payment.clicked.connect(self._payment)
        self.pushButton_cancel_reservation.clicked.connect(self._cancel_reservation)

    def _get_image_file(self, filename):
        image_file = os.path.join(self.parent.IMAGE_DIR, filename)
        image_file = image_file.replace("\\", "/")

        return image_file

    def _get_push_button(self, png_name, pressed_png, x, y):
        btn = QPushButton(self.ui.centralwidget)
        png_name = self._get_image_file(png_name)
        pressed_png = self._get_image_file(pressed_png)

        style = f"""
            QPushButton{{
                border: none;
                background: transparent;
                image: url({png_name});
            }}
            QPushButton:pressed {{
                image: url({pressed_png});
            }}
        """
        btn.setStyleSheet(style)
        btn.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
        pixmap = QPixmap(png_name)
        btn.setFixedSize(pixmap.size())
        btn.move(x, y)

        return btn

    def set_background(self):
        system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "insert_card.png"), 30, 448
        )
        system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "bottom.png"), -23, 1773
        )
        system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "scan_me.png"), 838, 1628
        )
        system_utils.set_image(
            self,
            os.path.join(self.parent.IMAGE_DIR, "qrcode.png"),
            868,
            1700,
            width=160,
            height=160,
        )

    def _set_push_buttons(self):
        self.pushButton_checkin = self._get_push_button(
            "checkin.png", "checkin.png", 0, 650
        )
        self.pushButton_payment = self._get_push_button(
            "payment.png", "payment.png", 526, 650
        )

        self.pushButton_vhc_checkin = self._get_push_button(
            "vhc_checkin.png", "vhc_checkin.png", 0, 950
        )
        self.pushButton_cancel_reservation = self._get_push_button(
            "cancel_reservation.png", "cancel_reservation.png", 526, 950
        )

        self.pushButton_reservation = self._get_push_button(
            "reservation.png", "reservation.png", 0, 1250
        )

        self.disable_button(self.pushButton_vhc_checkin)
        self.disable_button(self.pushButton_reservation)

    def disable_button(self, btn):
        opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.2)  # 調整透明度 (0.0 ~ 1.0)
        btn.setGraphicsEffect(opacity_effect)
        btn.setEnabled(False)

    def enable_button(self, btn):
        opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        opacity_effect.setOpacity(1.0)  # 調整透明度 (0.0 ~ 1.0)
        btn.setGraphicsEffect(opacity_effect)
        btn.setEnabled(True)

    def enable_checkin_button(self, enable: bool):
        if enable:
            self.enable_button(self.pushButton_checkin)
            self.enable_button(self.pushButton_vhc_checkin)
        else:
            self.disable_button(self.pushButton_checkin)
            self.disable_button(self.pushButton_vhc_checkin)

    # 預約報到
    def _checkin(self):
        self.parent.open_kiosk_registration()

    # 批價繳費
    def _payment(self):
        self.parent.open_kiosk_payment()

    def _vhc_checkin(self):
        print("vhc checkin")

    def _reservation(self):
        pass
        # kiosk = class_utils.get_jetway(self.system_settings)
        # kiosk.clear_coin_out_machine(10)
        # del kiosk

    def _cancel_reservation(self):
        self.parent.open_kiosk_cancel_reservation()

# -*- coding: utf-8 -*-
import dis
import os
import json

from libs import system_utils, ui_utils
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton


# 掛號機首頁 2024.06.23
class KioskHome(QtWidgets.QMainWindow):
    # === 設定庫存檔案與低水位門檻 ===
    COUNT_FILE = 'kiosk_count_data.json'

    # 當庫存低於以下數量時，鎖定繳費功能
    # (假設您是指百元鈔 bill_100，因為通常是找百元鈔)
    THRESHOLD_BILL_100 = 10  # 百元鈔少於 10 張
    THRESHOLD_COIN_50 = 10   # 50元硬幣少於 10 枚
    THRESHOLD_COIN_10 = 20   # 10元硬幣少於 20 枚

    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskHome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

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
        self.pushButton_reservation_arrival.clicked.connect(self._reservation_arrival)
        self.pushButton_payment.clicked.connect(self._payment)

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
        system_utils.shadow_widget(self, btn)

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
            self, self.parent.clinic_name, 50, 35, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)

        system_utils.set_label(
            self, '掛號繳費系統', 210, 300, self.parent.TEXT_FONT, 84, self.parent.TEXT_COLOR)

        system_utils.set_label(
            self, '請選擇下方的項目', 170, 660, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)
        # system_utils.set_label(
        #     self, '再選擇作業項目', 440, 720, self.parent.TEXT_FONT, 56, self.parent.TEXT_COLOR)

        system_utils.set_label(
            self, '初診或現場掛號請洽櫃台', 310, 1770, self.parent.TEXT_FONT, 42, self.parent.TEXT_COLOR)

    def _set_push_buttons(self):
        x = 150

        self.pushButton_reservation_arrival = self._get_push_button(
            'reservation_arrival.png', 'reservation_arrival.png', x, 850)

        self.pushButton_payment = self._get_push_button(
            'payment.png', 'payment.png', x, 1230)

    # 預約報到
    def _reservation_arrival(self):
        self.parent.open_kiosk_identity(op_type='預約報到')

    # 批價繳費
    def _payment(self):
        self.parent.open_kiosk_identity(op_type='批價繳費')

    # ==========================================
    # 新增：檢查庫存並控制按鈕狀態
    # ==========================================
    def check_inventory_status(self):
        """檢查庫存 json，如果不足則停用繳費按鈕"""
        disable_image = 'disable.png'
        
        # 預設為啟用
        is_enable = True
        reason = ""

        if os.path.exists(self.COUNT_FILE):
            try:
                with open(self.COUNT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 讀取目前庫存 (如果 key 不存在則預設為 0)
                bill_100 = data.get("100_bill", 0)
                coin_50 = data.get("50_coin", 0)
                coin_10 = data.get("10_coin", 0)

                # 判斷邏輯：只要任一幣別低於門檻，就鎖住
                if bill_100 < self.THRESHOLD_BILL_100:
                    is_enable = False
                    reason = "百元鈔不足"
                elif coin_50 < self.THRESHOLD_COIN_50:
                    is_enable = False
                    reason = "50元硬幣不足"
                elif coin_10 < self.THRESHOLD_COIN_10:
                    is_enable = False
                    reason = "10元硬幣不足"

            except Exception as e:
                print(f"讀取庫存檔案錯誤: {e}")
                # 讀取錯誤時，為了安全起見，可以選擇鎖定或保持預設
                # 這裡假設讀不到檔案可能是沒初始化，暫時不鎖，或是您可以改成 False
        else:
            print("庫存檔案不存在")

        # 設定按鈕狀態
        self.pushButton_payment.setEnabled(is_enable)

        # 視覺回饋：如果被停用，將透明度降低，讓使用者知道不能點
        if not is_enable:
            print(f"繳費功能已停用，原因: {reason}")
            self.pushButton_payment.setStyleSheet(
                self.pushButton_payment.styleSheet().replace(
                    "payment.png", disable_image))
        else:
            self.pushButton_payment.setStyleSheet(
                self.pushButton_payment.styleSheet().replace(
                    disable_image, "payment.png"))
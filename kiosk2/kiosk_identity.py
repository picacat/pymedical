# -*- coding: utf-8 -*-

import importlib
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton

from classes.smart_card import SmartCardObserver
from libs import system_utils, ui_utils


# 2024.06.24 掛號機辨識病人身分
class KioskIdentity(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskIdentity, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.case_key = None
        self.patient_key = None
        self.ui = None

        self.smart_observer = None  # 目前的 SmartCardObserver
        self.ic_card_data = None  # 目前讀到的健保卡資料（dict）

        # ====== 回首頁計時器相關 ======
        self.wait_seconds = 30
        self.home_timer = QtCore.QTimer(self)  # 將 QTimer 實例化並綁定到 self
        self.home_timer.timeout.connect(self._timeout)

        # ====== 條碼掃描器相關 ======
        self.barcode_buffer = ""  # 暫存條碼內容
        self.barcode_timeout_ms = 150  # 超過這段時間就當作不是條碼（依需求調整）
        self.barcode_timer = QtCore.QTimer(self)
        self.barcode_timer.setSingleShot(True)
        self.barcode_timer.timeout.connect(self._on_barcode_timeout)

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        self._stop_card_observer()
        self._release_keyboard()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "kiosk_home.ui"), self
        )
        self.set_background()

    # 設定信號
    def _set_signal(self):
        pass

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

    def _get_png_file_name(self, filename):
        png_name = os.path.join(self.parent.IMAGE_DIR, filename)

        return png_name

    def set_background(self):
        label_background = system_utils.set_image(
            self, os.path.join(self.parent.IMAGE_DIR, "background.png"), 0, 0
        )
        self._bring_to_front(label_background)

        label_header = system_utils.set_label(
            self,
            self.parent.clinic_name,
            50,
            35,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self,
            "掛號繳費系統",
            210,
            300,
            self.parent.TEXT_FONT,
            84,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        label_header = system_utils.set_label(
            self,
            "請選擇確認身分的方式",
            310,
            1770,
            self.parent.TEXT_FONT,
            42,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        label_title = system_utils.set_label(
            self,
            "請選擇身份識別的方式:",
            120,
            550,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_title)

        png_filename1 = self._get_png_file_name("barcode.png")
        label1 = system_utils.set_image(
            self, png_filename1, 120, 680, width=160, height=160
        )
        self._bring_to_front(label1)

        label_hint1 = system_utils.set_label(
            self,
            "掃描手機二維條碼",
            320,
            710,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_hint1)

        png_filename2 = self._get_png_file_name("id.png")
        label2 = system_utils.set_image(
            self, png_filename2, 120, 880, width=160, height=160
        )
        self._bring_to_front(label2)

        label_hint2 = system_utils.set_label(
            self,
            "掃描身份證背面條碼",
            320,
            910,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_hint2)

        png_filename3 = self._get_png_file_name("iccard.png")
        label3 = system_utils.set_image(
            self, png_filename3, 120, 1080, width=160, height=160
        )
        self._bring_to_front(label3)

        label_hint3 = system_utils.set_label(
            self,
            "插入健保卡至讀卡機",
            320,
            1110,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_hint3)

        # png_filename4 = self._get_png_file_name('keypad.png')
        # label4 = system_utils.set_image(
        #     self, png_filename4, 120, 1280, width=160, height=160)
        # self._bring_to_front(label4)

        label_hint4 = system_utils.set_label(
            self,
            "手動輸入身份證ID",
            320,
            1310,
            self.parent.TEXT_FONT,
            56,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_hint4)

        self.pushButton_get_id = self._get_push_button(
            "keypad.png", "keypad.png", 120, 1280, set_fixed_size=False
        )
        self._bring_to_front(self.pushButton_get_id)
        self.pushButton_get_id.clicked.connect(self._manual_input_id)

        self._set_manual_input_button()
        self._set_back_home_button("回首頁")

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def _release_keyboard(self):
        try:
            self.releaseKeyboard()
        except Exception:
            pass

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        # 收到 Enter：條碼結束
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self.barcode_buffer:
                barcode = self.barcode_buffer
                self.barcode_buffer = ""
                self.barcode_timer.stop()
                self._on_barcode_scanned(barcode)
                return  # 不往下傳，避免影響其他元件
            # 沒 buffer 當一般 Enter
            return super(KioskIdentity, self).keyPressEvent(event)

        # 收集條碼內容（視需求可以改成 text.isalnum()）
        if text and text.isprintable():
            self.barcode_buffer += text
            self.barcode_timer.start(self.barcode_timeout_ms)
            return  # 視為條碼輸入

        # 其他按鍵交給原本邏輯
        return super(KioskIdentity, self).keyPressEvent(event)

    def _on_barcode_timeout(self):
        # 超時就丟棄目前 buffer，避免殘留影響下一次掃描
        self.barcode_buffer = ""

    def _on_barcode_scanned(self, barcode_text: str):
        id_number = barcode_text.strip()
        self.ic_card_data = {"patient_id": id_number}

        self._do_identity(identity_type="掃描身分證")

    def _stop_thread(self):
        if self.barcode_timer.isActive():
            self.barcode_timer.stop()

        self.barcode_buffer = ""

        self.ic_card = None
        self.ic_card_data = None
        self._stop_card_observer()
        self._release_keyboard()

    def _on_card_inserted(self, _msg):
        if self.smart_observer is None:
            return

        self.ic_card_data = self.smart_observer.get_nhi_basic_data()

        if not self.ic_card_data:
            self._stop_thread()
            self._show_no_iccard()
            self._back_to_home()
            return

        self._do_identity(identity_type="讀取健保卡")

    def _on_card_removed(self):
        pass

    def _start_card_observer(self):
        if self.smart_observer is not None:
            self.smart_observer.stop()
            self.smart_observer = None

        self.smart_observer = SmartCardObserver(self)
        self.smart_observer.card_inserted.connect(self._on_card_inserted)
        self.smart_observer.card_removed.connect(self._on_card_removed)

        self.smart_observer.check_initial_card()

    def _stop_card_observer(self):
        if self.smart_observer is not None:
            self.smart_observer.stop()
            self.smart_observer = None

    def manual_input_id_from_dialog(self):
        """從 dialog_message_box 點下『手動輸入身分證』時呼叫"""

        # 先暫時放掉鍵盤抓取，避免條碼槍事件干擾
        self._release_keyboard()

        from kiosk2.dialog import dialog_input_id

        module = importlib.reload(dialog_input_id)
        dialog = module.DialogInputID(self.parent, self.database, self.system_settings)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            digits = dialog.get_id_digits()
            if digits:
                # 仍然沿用現有 ic_card_data 機制
                self.ic_card_data = {"patient_id": digits}
                self._do_identity(identity_type="手動輸入")
        else:
            # 手動輸入被取消，你可以選擇回首頁或是再進入等待卡片狀態
            # 現在先簡單回首頁：
            # self._back_to_home()
            self.wait_seconds = 30
            self.push_button_home.setText(
                f"{self.button_text_home}({self.wait_seconds}s)"
            )
            self.home_timer.start(1000)

        del dialog

    def set_identity_data(self, op_type="預約報到"):
        self._op_type = op_type  # 從kiosk_home確認是哪一個按鈕被按下

        self.clear_all_widgets()
        self.set_background()

        self.barcode_buffer = ""
        self.barcode_timer.stop()
        self.grabKeyboard()

        self.ic_card_data = None
        self._start_card_observer()

    def _do_identity(self, identity_type=None):
        patient_id = self.ic_card_data["patient_id"]

        if len(patient_id) == 9 and patient_id.isdigit():
            # 手動輸入的 9 碼數字
            where_clause = f'RIGHT(ID, 9) = "{patient_id}"'
        else:
            # 原本流程：完整身分證字號
            # where_clause = f'ID = "{patient_id}"'
            where_clause = f'RIGHT(ID, {len(patient_id)}) = "{patient_id}"'

        sql = f"""
            SELECT PatientKey FROM patient
            WHERE
                {where_clause}
        """
        rows = self.database.select_record(sql)

        self._stop_thread()

        if len(rows) <= 0:  # 找不到資料
            self._show_no_patient()
            self._back_to_home()
            return

        row = rows[0]
        patient_key = row["PatientKey"]

        if self._op_type == "預約報到":
            self.parent.open_kiosk_registration(
                patient_key=patient_key, identity_type=identity_type
            )
        elif self._op_type == "批價繳費":
            self.parent.open_kiosk_payment(
                patient_key=patient_key, identity_type=identity_type
            )

    def _show_no_iccard(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_iccard()
        dialog.exec_()
        del dialog

    def _show_no_patient(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(
            self.parent, self.database, self.system_settings
        )
        dialog.set_no_patient()
        dialog.exec_()
        del dialog

    def _set_manual_input_button(self):
        color = self.parent.RED
        x, y = 240, 1500

        btn = QtWidgets.QPushButton(self)
        btn.resize(280, 80)
        btn.setText("輸入ID")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: 2px solid {color};
                border-radius: 10px;
                color: white;
                font: 75 36pt "{self.parent.BUTTON_FONT}";
            }}
        """)

        system_utils.shadow_widget(self, btn)
        btn.move(x, y)
        self._bring_to_front(btn)
        btn.clicked.connect(self._manual_input_id)

    def _manual_input_id(self):
        # 先停倒數計時
        self.home_timer.stop()

        # 再由 kiosk_identity 開啟手動輸入流程
        # parent 是 Kiosk，widget_identity 是 KioskIdentity 實例
        if hasattr(self.parent, "widget_identity"):
            identity = self.parent.widget_identity
            if hasattr(identity, "manual_input_id_from_dialog"):
                identity.manual_input_id_from_dialog()

    def _set_back_home_button(self, button_text, x=580, y=1500):
        self.wait_seconds = 30
        self.button_text_home = button_text
        color = self.parent.DARK_GREEN

        self.push_button_home = QtWidgets.QPushButton(self)
        self.push_button_home.resize(320, 80)
        self.push_button_home.setText(f"{self.button_text_home}({self.wait_seconds}s)")
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
        self._bring_to_front(self.push_button_home)
        self.push_button_home.clicked.connect(self._back_to_home)

        self.home_timer.start(1000)

    def _timeout(self):
        self.wait_seconds -= 1
        self.push_button_home.setText(f"{self.button_text_home}({self.wait_seconds}s)")
        if self.wait_seconds == 0:
            self._back_to_home()

    def _back_to_home(self):
        self.home_timer.stop()
        self._stop_thread()
        self.parent.open_kiosk_home()

    def _get_push_button(self, png_name, pressed_png, x, y, set_fixed_size=True):
        btn = QPushButton(self.ui)
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
        system_utils.shadow_widget(self, btn)

        pixmap = QPixmap(png_name)
        if set_fixed_size:
            btn.setFixedSize(pixmap.size())
        else:
            btn.resize(160, 160)

        btn.move(x, y)

        return btn

    def _get_image_file(self, filename):
        image_file = os.path.join(self.parent.IMAGE_DIR, filename)
        image_file = image_file.replace("\\", "/")

        return image_file

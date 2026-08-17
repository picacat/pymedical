# -*- coding: UTF-8 -*-

import datetime
import os
import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, Qt, pyqtSignal

from classes import jetway
from libs import (
    notification_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
)


class Communicate(QObject):
    update_cash_received = pyqtSignal(int)


# 2025.11.24 掛號機繳費頁面
class KioskPay(QtWidgets.QDialog):
    finished = pyqtSignal()

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent.parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.total_amount = args[3]
        self.ui = None
        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station=self.program_name,
        )

        self.stop_event = threading.Event()  # <--- 必須添加
        # self.charge_cash_thread = None       # <--- 保持初始化
        self.change_due = 0
        self.payment_done = False

        self.comm = Communicate()
        self.comm.update_cash_received.connect(self._update_cash_received)

        # self.kiosk = class_utils.get_jetway(self.system_settings)
        self.kiosk = jetway.Jetway(self.system_settings)
        if not self.kiosk.connected:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Warning,
                "錯誤",
                '<font size="5" color="red"><b>收鈔機無法啟動, 請檢查收鈔機是否備妥.</b></font>',
                "請檢查收鈔機的狀態.",
            )
            self.close()
            return

        self.charge_cash_thread = threading.Thread(
            target=self.kiosk.charge_cash,
            args=(self.total_amount, self.comm.update_cash_received, self.stop_event),
        )
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
        # ui_file = os.path.join(self.parent.UI_DIR, 'kiosk_home.ui')
        # self.ui = ui_utils.load_ui_file(ui_file, self)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        self.set_background()

    # 刪除所有控件
    def clear_all_widgets(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.setParent(None)
            widget.deleteLater()

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
            "請投入紙鈔、50或10元硬幣",
            310,
            1770,
            self.parent.TEXT_FONT,
            42,
            self.parent.TEXT_COLOR,
        )
        self._bring_to_front(label_header)

        self._set_cancel_button("取消繳費")

    def _set_cancel_button(self, button_text):
        color = self.parent.DARK_RED
        x, y = 350, 1400
        self.push_button = QtWidgets.QPushButton(self)
        self.push_button.resize(400, 100)
        self.push_button.setText(button_text)
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
        system_utils.shadow_widget(self, self.push_button)
        self.push_button.raise_()
        self.push_button.show()
        self.push_button.clicked.connect(self._back_to_home)

    # 設定信號
    def _set_signal(self):
        pass

    def _back_to_home(self):
        if self.inserted_cash > 0:
            self.kiosk.eject_cash(self.inserted_cash)

        self.stop_charge_cash()
        self.close_kiosk_and_finish()
        self.reject()

    def set_payment_data(self):
        self.clear_all_widgets()
        self.set_background()

        x1 = 200
        x2 = 700
        font_size = 72

        LINE_HEIGHT = 150
        LINE1_Y = 700
        LINE2_Y = LINE1_Y + LINE_HEIGHT
        LINE3_Y = LINE2_Y + LINE_HEIGHT
        self.inserted_cash = 0

        header = system_utils.set_label(
            self,
            "應付金額: $",
            x1,
            LINE1_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.RED,
        )
        self._bring_to_front(header)

        label_total_amount = system_utils.set_label(
            self,
            str(self.total_amount),
            x2,
            LINE1_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.RED,
        )
        self._bring_to_front(label_total_amount)

        header = system_utils.set_label(
            self,
            "投入金額: $",
            x1,
            LINE2_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.DARK_GREEN,
        )
        self._bring_to_front(header)

        self.label_inserted_cash = system_utils.set_label(
            self,
            str(self.inserted_cash),
            x2,
            LINE2_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.DARK_GREEN,
        )
        self._bring_to_front(self.label_inserted_cash)

        header = system_utils.set_label(
            self,
            "尚餘金額: $",
            x1,
            LINE3_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.LIGHT_GREEN,
        )
        self._bring_to_front(header)

        self.label_remain = system_utils.set_label(
            self,
            str(self.total_amount - self.inserted_cash),
            x2,
            LINE3_Y,
            self.parent.TEXT_FONT,
            font_size,
            self.parent.LIGHT_GREEN,
        )
        self._bring_to_front(self.label_remain)

        self.start_charge_cash()

    def _bring_to_front(self, widget):
        widget.raise_()
        widget.show()

    def start_charge_cash(self):
        self.inserted_cash = 0
        self.stop_event.clear()  # <--- 必須在連線前清空 event

        self.charge_cash_thread.start()

    def stop_charge_cash(self):
        if hasattr(self, "stop_event"):
            self.stop_event.set()

        if self.charge_cash_thread is not None:
            # 為了確保 join 成功，最好檢查執行緒是否仍在運行 (is_alive)
            if self.charge_cash_thread.is_alive():
                self.charge_cash_thread.join()

        # 執行緒一旦 join 後就不能再用，將其重設為 None
        self.charge_cash_thread = None

    def _update_cash_received(self, receipt_cash):
        self.inserted_cash = receipt_cash
        self.label_inserted_cash.setText(f"{self.inserted_cash}")
        self.label_inserted_cash.adjustSize()

        if self.inserted_cash >= self.total_amount:
            self.payment_done = True

            self.change_due = self.inserted_cash - self.total_amount
            if self.change_due > 0:
                self.kiosk.eject_cash(self.change_due)

            self.label_remain.setText(f"{self.total_amount - self.inserted_cash}")
            self.label_remain.adjustSize()
            self.stop_charge_cash()

            self.close_kiosk_and_finish()
            self._update_files()
            self._send_broadcast_data()
            self._print_receipt()
            self.accept()

            return

        remain = self.total_amount - self.inserted_cash
        self.label_remain.setText(f"{remain}")
        self.label_remain.adjustSize()

    def is_payment_done(self):
        return self.payment_done

    def _update_files(self):
        self._update_cases()

    def _update_cases(self):
        sql = f'''
            UPDATE cases
            SET
                ChargeDone = "True",
                Register = "掛號機",
                Cashier = "掛號機",
                ChargeDate = "{string_utils.xstr(datetime.datetime.now())}",
                ChargePeriod = "{registration_utils.get_current_period(self.system_settings)}"
            WHERE
                CaseKey = {self.case_key}
        '''
        self.database.exec_sql(sql)

    def _print_receipt(self):
        printer_utils.print_misc_form(
            self, self.database, self.system_settings, self.case_key, "列印"
        )

    def _send_broadcast_data(self):
        sql = f"""
            SELECT Doctor, Room FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)
        if not rows:
            return

        case_row = rows[0]
        doctor = string_utils.xstr(case_row["Doctor"])
        room = string_utils.xstr(case_row["Room"])

        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                "批價作業",
                doctor,
                room,
            ]
        )

        self.notification_client.send_data(message)  # 新管道：資料庫

    def close_kiosk_and_finish(self):
        self.kiosk.close_cash_in_machine()
        self.kiosk.close_serial()
        del self.kiosk

    def get_change_due(self):
        return self.change_due

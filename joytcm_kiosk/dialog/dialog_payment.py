import os
import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, Qt, pyqtSignal

from libs import class_utils, system_utils, ui_utils


class Communicate(QObject):
    update_cash_received = pyqtSignal(int)


# 開始繳費
class DialogPayment(QtWidgets.QDialog):
    LINE_HEIGHT = 90
    LINE1_Y = 160
    LINE2_Y = LINE1_Y + LINE_HEIGHT
    LINE3_Y = LINE2_Y + LINE_HEIGHT

    BUTTON_Y = 550
    ICON_Y = 140
    ICON_W = 160
    ICON_H = 160

    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPayment, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.case_key = args[3]
        self.total_amount = args[4]
        self.ui = None

        self.inserted_cash = 0
        self.payment_done = False

        self._set_ui()
        self._set_signal()
        self._set_payment_data()

    # 解構
    def __del__(self):
        pass

    # def back_to_previous(self):
    #     self.stop_charge_cash()
    #     if self.inserted_cash > 0:
    #         self.kiosk.eject_cash(self.inserted_cash)

    #     del self.kiosk
    #     self.close()

    def back_to_previous(self):
        if getattr(self, "stop_event", None) is None:
            self.close()
            return

        self.stop_charge_cash()
        if self.inserted_cash > 0:
            self.kiosk.eject_cash(self.inserted_cash)

        del self.kiosk
        self.close()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "dialog_message_box.ui"), self
        )
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        image_file = os.path.join(
            self.parent.BASE_DIR, "joytcm_kiosk", "images", "message_box.png"
        )
        image_file = image_file.replace("\\", "/")

        self.setStyleSheet(f"""
            QDialog {{
                background-image: url({image_file});  /* 設置背景圖片路徑 */
                background-repeat: no-repeat;
                background-position: center;
                font: 75 24pt "{self.parent.TEXT_FONT}";
            }}
        """)

        system_utils.set_label(
            self,
            "請開始投入紙鈔或硬幣！",
            120,
            self.LINE3_Y + 180,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE + 4,
            self.parent.RED,
        )

        # system_utils.set_button(
        #     self, '返回繳費確認頁', 'white', 0, self.BUTTON_Y,
        #     self.parent.BUTTON_FONT, self.parent.RED, self.parent.BUTTON_FONT_SIZE,
        #     340, self.parent.BUTTON_HEIGHT, self.back_to_previous, center=True)
        self.button_close = QtWidgets.QPushButton(self)
        self.button_close.setGeometry(50, 35, 60, 60)  # 依紅點在視窗上的實際位置微調
        self.button_close.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
        )
        self.button_close.setCursor(Qt.PointingHandCursor)
        self.button_close.clicked.connect(self.back_to_previous)

    # 設定信號
    def _set_signal(self):
        pass

    def _set_payment_data(self):
        x1 = 120
        x2 = 500

        system_utils.set_label(
            self,
            "應付金額: NT$",
            x1,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
        )

        system_utils.set_label(
            self,
            str(self.total_amount),
            x2,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
        )

        system_utils.set_label(
            self,
            "投入金額: NT$",
            x1,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
        )

        self.label_inserted_cash = system_utils.set_label(
            self,
            str(self.inserted_cash),
            x2,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
        )

        system_utils.set_label(
            self,
            "尚餘金額: NT$",
            x1,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.LIGHT_GREEN,
        )

        self.label_remain = system_utils.set_label(
            self,
            str(self.total_amount),
            x2,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.LIGHT_GREEN,
        )

        self.start_charge_cash()

    def start_charge_cash(self):
        self.inserted_cash = 0
        self.comm = Communicate()
        self.comm.update_cash_received.connect(self._update_cash_received)

        self.kiosk = class_utils.get_jetway(self.system_settings)
        if not self.kiosk.connected:
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Warning,
                "錯誤",
                '<font size="5" color="red"><b>收鈔機無法啟動, 請檢查收鈔機是否備妥.</b></font>',
                "請檢查收鈔機的狀態.",
            )
            self.close()
            return

        self.stop_event = threading.Event()
        self.charge_cash_thread = threading.Thread(
            target=self.kiosk.charge_cash,
            args=(self.total_amount, self.comm.update_cash_received, self.stop_event),
        )
        self.charge_cash_thread.start()

    def stop_charge_cash(self):
        self.stop_event.set()
        self.charge_cash_thread.join()

    def _update_cash_received(self, receipt_cash):
        self.inserted_cash = receipt_cash
        self.label_inserted_cash.setText(f"{self.inserted_cash}")
        self.label_inserted_cash.adjustSize()

        if self.inserted_cash >= self.total_amount:
            remain_cash = self.inserted_cash - self.total_amount
            self.stop_charge_cash()
            if remain_cash > 0:
                self.kiosk.eject_cash(remain_cash)

            self.payment_done = True
            del self.kiosk
            self.close()
            return

        remain = self.total_amount - self.inserted_cash
        self.label_remain.setText(f"{remain}")
        self.label_remain.adjustSize()

    def is_payment_done(self):
        return self.payment_done

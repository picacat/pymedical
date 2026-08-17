# 林胤谷中醫診所專用

import datetime
import importlib
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDialog

from kiosk2.classes.count_dialog import CountDialog, CountPasswordDialog
from kiosk2.classes.password_dialog import PasswordDialog
from libs import class_utils, module_utils, system_utils, ui_utils


# 林胤谷中醫預約報到繳費機 2025.11.25
class Kiosk(QtWidgets.QMainWindow):
    # BASE_DIR = os.getcwd()
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UI_DIR = os.path.join(BASE_DIR, "kiosk2", "ui")
    IMAGE_DIR = os.path.join(BASE_DIR, "kiosk2", "images")
    TEXT_FONT = "jf open 粉圓 2.1"
    FONT_SIZE = 42
    BUTTON_FONT = "jf open 粉圓 2.1"
    BUTTON_FONT_SIZE = 24
    BUTTON_HEIGHT = 80
    ROOM_DICT = {
        1: "一診",
        2: "二診",
        3: "三診",
        4: "四診",
        5: "五診",
        6: "六診",
        7: "七診",
        8: "八診",
        9: "九診",
        10: "十診",
    }

    DARK_RED = "#e4442e"
    RED = "#FF0000"
    DARK_GREEN = "#1e4f0a"
    LIGHT_GREEN = "#4bab56"

    LIGHT_TEXT_COLOR = "#333339"
    TEXT_COLOR = "#000000"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.args = args

        try:
            config_file = args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict["host"]
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict["user"],
                database=config_dict["database"],
                password=config_dict["password"],
                charset=config_dict["charset"],
                buffered=config_dict["buffered"],
            )
            self.server_ip = config_dict["host"]
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )
        self.ui = None
        self.clinic_name = self.system_settings.field("院所名稱")
        self.clinic_name = self.clinic_name.replace("診所", "")

        self._set_ui()
        self._set_signal()
        self.close_kiosk_slot()

    # 解構
    def __del__(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_KIOSK, self)
        self.ui.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # 無視窗邊框
        self.set_background()
        self._set_clock()
        self._set_stacked_widget()

    def close_kiosk_slot(self):
        kiosk = class_utils.get_jetway(self.system_settings)
        kiosk.close_cash_in_machine()
        del kiosk

    def set_background(self):
        self.exit_area = QtCore.QRect(0, 0, 100, 100)
        self.click_count = 0

        desktop = QtWidgets.QApplication.desktop()
        cursor_pos = QtGui.QCursor.pos()
        screen_number = desktop.screenNumber(cursor_pos)
        screen_rect = desktop.screenGeometry(screen_number)
        self.setGeometry(screen_rect)
        screen_width = screen_rect.width()
        self.count_area = QtCore.QRect(screen_width - 100, 0, 100, 100)
        self.count_click_count = 0

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)  # 2 秒
        self.timer.timeout.connect(self.reset_click_count)
        self.mousePressEvent = self.label_clicked

    def label_clicked(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.exit_area.contains(event.pos()):
                self.timer.start()
                self.click_count += 1
                if self.click_count >= 5:
                    self.show_password_dialog()
            # 2. 處理右上角 (清點計數)
            elif self.count_area.contains(event.pos()):
                self.timer.start()
                self.count_click_count += 1
                self.exit_click_count = 0  # 點擊右上角，重置左上角的計數

                if self.count_click_count >= 5:
                    self.show_count_dialog()
                    self.reset_click_count()  # 成功彈出後重置
                    self._refresh_check_inventory_status()
                return  # 處理完畢
        else:
            # 點擊不在區域內，立即歸零
            self.reset_click_count()

    def show_password_dialog(self):
        dialog = PasswordDialog("1234", self)

        if dialog.exec_() == QDialog.Accepted:
            kiosk = class_utils.get_jetway(self.system_settings)
            if dialog.eject_coins:
                kiosk.clear_coin_out_machine(50)
                kiosk.clear_coin_out_machine(10)
                kiosk.clear_coin_out_machine(5)
            elif dialog.eject_coin5:
                kiosk.clear_coin_out_machine(5)
            elif dialog.eject_coin10:
                kiosk.clear_coin_out_machine(10)
            elif dialog.eject_coin50:
                kiosk.clear_coin_out_machine(50)

            kiosk.close_cash_in_machine()
            del kiosk

            self.close_app()

    def show_count_dialog(self):
        # 1. 先進行密碼驗證
        password_dialog = CountPasswordDialog("1234", self)  # 假設清點密碼也是 '1234'
        if password_dialog.exec_() == QDialog.Accepted:
            # 2. 密碼正確後打開計數輸入框
            count_dialog = CountDialog(self)
            count_dialog.exec_()

    def reset_click_count(self):
        """重置點擊次數並停止計時器"""
        self.count_click_count = 0
        self.click_count = 0
        self.timer.stop()

    def _set_clock(self):
        x, y = 100, 130
        self.label_clock = QtWidgets.QLabel(self)
        self.label_clock.setFixedWidth(300)
        self.label_clock.setStyleSheet(f"""
            color: {self.TEXT_COLOR};  /* 正常狀態背景顏色 */
            font: 75 18pt "{self.TEXT_FONT}";
        """)
        self.label_clock.move(x, y)

        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock_ui)
        self.clock_timer.start(1000)  # 每 1000 毫秒 (1秒) 觸發一次

    def update_clock_ui(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        self.label_clock.setText(current_time)

    # 設定信號
    def _set_signal(self):
        pass

    def close_app(self):
        self.database.close_database()
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_theme(self.ui, self.system_settings)

    def _set_stacked_widget(self):
        self._set_kiosk_home()
        self._set_kiosk_identity()
        self._set_kiosk_registration()
        self._set_kiosk_payment()
        self._set_kiosk_completed()

    def _set_kiosk_home(self):
        self.widget_home = module_utils.get_kiosk2_home(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_home)

    def _set_kiosk_identity(self):
        self.widget_identity = module_utils.get_kiosk2_identity(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_identity)

    def _set_kiosk_registration(self):
        self.widget_registration = module_utils.get_kiosk2_registration(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_registration)

    def _set_kiosk_payment(self):
        self.widget_payment = module_utils.get_kiosk2_payment(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_payment)

    def _set_kiosk_completed(self):
        self.widget_completed = module_utils.get_kiosk2_completed(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_completed)

    def open_kiosk_home(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        self._refresh_check_inventory_status()

    # === 新增：每次回到首頁時，檢查庫存狀態 ===
    def _refresh_check_inventory_status(self):
        if hasattr(self, "widget_home"):
            self.widget_home.check_inventory_status()

    def open_kiosk_identity(self, op_type):
        self.ui.stackedWidget.setCurrentIndex(1)
        self.widget_identity.set_identity_data(op_type=op_type)

    def open_kiosk_registration(self, patient_key, identity_type):
        self.ui.stackedWidget.setCurrentIndex(2)
        self.widget_registration.set_registration_data(
            patient_key=patient_key, identity_type=identity_type
        )

    def open_kiosk_payment(self, patient_key, identity_type):
        self.ui.stackedWidget.setCurrentIndex(3)
        self.widget_payment.set_payment_data(
            patient_key=patient_key, identity_type=identity_type
        )

    def open_kiosk_completed(self, op_type, case_key=None, change_due=None):
        self.ui.stackedWidget.setCurrentIndex(4)
        self.widget_completed.set_completed(op_type, case_key, change_due)

    def show_in_progress(self):
        from kiosk2.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self, self.database, self.system_settings)
        dialog.set_in_progress()
        dialog.show()

        return dialog


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)
    app.setAttribute(QtCore.Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)

    kiosk = Kiosk()
    kiosk.showFullScreen()
    kiosk.open_kiosk_home()

    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()

import sys
import os
from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import module_utils

HOME_WIDGET = 1


# 百會資訊通用型掛號機
class Kiosk(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Kiosk, self).__init__(parent)
        self.args = args

        try:
            config_file = args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict['host']
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict['user'],
                database=config_dict['database'],
                password=config_dict['password'],
                charset=config_dict['charset'],
                buffered=config_dict['buffered'],
            )
            self.server_ip = config_dict['host']
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(self.database, self.config_file)
        self.ui = None

        os.system('C:\\NHI\\UTILITY\\csResetFsim.exe')
        self.ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_KIOSK, self)
        self.ui.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # 無視窗邊框
        self._set_stacked_widget()

    # 設定信號
    def _set_signal(self):
        pass

    def close_app(self):
        self.database.close_database()
        self.ic_card.close_com()
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_theme(self.ui, self.system_settings)

    def _set_stacked_widget(self):
        self._set_kiosk_home()
        self._set_kiosk_registration()
        self._set_kiosk_payment()
        self._set_kiosk_completed()

    def _set_kiosk_home(self):
        self.widget_home = module_utils.get_kiosk_home(self, self.database, self.system_settings, self.ic_card)
        self.ui.stackedWidget.addWidget(self.widget_home)

    def _set_kiosk_registration(self):
        self.widget_registration = module_utils.get_kiosk_registration(
            self, self.database, self.system_settings, self.ic_card
        )
        self.ui.stackedWidget.addWidget(self.widget_registration)

    def _set_kiosk_payment(self):
        self.widget_payment = module_utils.get_kiosk_payment(
            self, self.database, self.system_settings, self.ic_card,
        )
        self.ui.stackedWidget.addWidget(self.widget_payment)

    def _set_kiosk_completed(self):
        self.widget_completed = module_utils.get_kiosk_completed(
            self, self.database, self.system_settings, self.ic_card,
        )
        self.ui.stackedWidget.addWidget(self.widget_completed)

    def open_kiosk_home(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        self.widget_home.set_style()
        # self.widget_home.detect_ic_card_insertion()

    def open_kiosk_registration(self):
        self.ui.stackedWidget.setCurrentIndex(1)
        self.widget_registration.set_registration_data()
        # self.widget_registration.detect_ic_card_removed()

    def open_kiosk_payment(self, patient_key, regist_type, keyword):
        self.ui.stackedWidget.setCurrentIndex(2)
        self.widget_payment.set_payment_data(patient_key, regist_type, keyword)
        # self.widget_payment.detect_ic_card_removed()

    def open_kiosk_completed(self, **kwargs):
        self.ui.stackedWidget.setCurrentIndex(3)
        self.widget_completed.set_writing_data(**kwargs)

    # 安全模組卡認證
    def setup_ic_card(self):
        self.ic_card.close_com()
        self.ic_card.open_com()
        error_code = self.ic_card.verify_sam(show_message=False)
        if error_code != 0:
            sys.exit(0)


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_cashier = Kiosk()
    py_cashier.showFullScreen()
    py_cashier.setup_ic_card()
    py_cashier.open_kiosk_home()

    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()

# -*- coding: UTF-8 -*-

import sys
from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import module_utils

HOME_WIDGET = 1


# 陳士源 掛號機
class PyCashier(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyCashier, self).__init__(parent)
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

        # self.coinsys = None
        self.coinsys = class_utils.get_coin_sys(self.system_settings)
        self.coinsys.clear_parameter_files()
        self.coinsys.startup_coin_sys()

        # if not self.coinsys.connected():
        #     system_utils.show_message_box(
        #         QMessageBox.Warning,
        #         '錯誤',
        #         '<font size="5" color="red"><b>收鈔機無法啟動, 請檢查收鈔機是否備妥.</b></font>',
        #         '請檢查收鈔機的狀態.'
        #     )
        #     sys.exit(0)

        self.ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_CASHIER, self)
        self.ui.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # 無視窗邊框
        self._set_stacked_widget()

    # 設定信號
    def _set_signal(self):
        pass

    def close_app(self):
        self.database.close_database()
        self.coinsys.release_coin_sys()
        self.ic_card.close_com()
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_theme(self.ui, self.system_settings)

    def _set_stacked_widget(self):
        self._set_pycashier_home()
        self._set_pycashier_registration()
        self._set_pycashier_payment()
        self._set_pycashier_completed()

    def _set_pycashier_home(self):
        self.widget_home = module_utils.get_pycashier3_home(self, self.database, self.system_settings, self.ic_card)
        self.ui.stackedWidget.addWidget(self.widget_home)

    def _set_pycashier_registration(self):
        self.widget_registration = module_utils.get_pycashier3_registration(
            self, self.database, self.system_settings, self.ic_card
        )
        self.ui.stackedWidget.addWidget(self.widget_registration)

    def _set_pycashier_payment(self):
        self.widget_payment = module_utils.get_pycashier3_payment(
            self, self.database, self.system_settings, self.ic_card, self.coinsys
        )
        self.ui.stackedWidget.addWidget(self.widget_payment)

    def _set_pycashier_completed(self):
        self.widget_completed = module_utils.get_pycashier3_completed(
            self, self.database, self.system_settings, self.ic_card,
        )
        self.ui.stackedWidget.addWidget(self.widget_completed)

    def open_pycashier_home(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        self.widget_home.detect_ic_card_insertion()

    def open_pycashier_registration(self):
        self.ui.stackedWidget.setCurrentIndex(1)
        self.widget_registration.set_registration_data()
        self.widget_registration.detect_ic_card_removed()

    def open_pycashier_payment(self, patient_key, regist_type, keyword):
        self.ui.stackedWidget.setCurrentIndex(2)
        self.widget_payment.set_payment_data(patient_key, regist_type, keyword)
        self.widget_payment.detect_ic_card_removed()

    def open_pycashier_completed(self, **kwargs):
        self.ui.stackedWidget.setCurrentIndex(3)
        self.widget_completed.set_writing_data(**kwargs)

    # 安全模組卡認證
    def setup_ic_card(self):
        self.ic_card.close_com()
        self.ic_card.open_com()

        self.ic_card.reset_reader(show_message=False)
        error_code = self.ic_card.verify_sam(show_message=False)
        if error_code != 0:
            sys.exit(0)


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_cashier = PyCashier()
    py_cashier.showFullScreen()
    py_cashier.setup_ic_card()
    py_cashier.open_pycashier_home()

    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()

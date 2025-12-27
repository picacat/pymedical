# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import module_utils


# 物理治療預約系統
class Physiotherapy(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Physiotherapy, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.time_list = [
            '09:00', '10:00', '11:00', '12:00', '13:00',
            '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHYSIOTHERAPY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.tab_physiotherapy_schedule = module_utils.get_physiotherapy_schedule(self, *self.args)
        self.ui.tabWidget_physiotherapy.addTab(self.tab_physiotherapy_schedule, '預約表')

        self.tab_physiotherapy_income = module_utils.get_physiotherapy_income(self, *self.args)
        self.ui.tabWidget_physiotherapy.addTab(self.tab_physiotherapy_income, '收入統計')

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.tabWidget_physiotherapy.tabCloseRequested.connect(self.close_tab)              # 關閉分頁

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

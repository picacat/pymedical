# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import system_utils
from libs import ui_utils
from libs import module_utils


# 其他詞庫 2019.07.18
class DictMisc(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictMisc, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_MISC, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        tab_hosp = module_utils.get_dict_hosp(self, *self.args)
        self.ui.tabWidget_misc.addTab(tab_hosp, '院所資料')

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_template)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_template(self):
        self.close_all()
        self.close_tab()

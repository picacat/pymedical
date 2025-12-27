# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import module_utils


# 銷貨 2022.11.19 誠泰
class StockOut(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockOut, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_OUT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.tab_stock_out_list = module_utils.get_stock_out_list(self, *self.args)
        self.ui.tabWidget_stock.addTab(self.tab_stock_out_list, '出貨資料')

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_update_stock.triggered.connect(self.update_stock)
        self.ui.tabWidget_stock.tabCloseRequested.connect(self.close_stock_tab)              # 關閉分頁

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        current_index = self.ui.tabWidget_stock.currentIndex()
        tab_name = self.ui.tabWidget_stock.tabText(current_index)
        if tab_name != '出貨資料':
            current_tab = self.ui.tabWidget_stock.widget(current_index)
            current_tab.close_all()
            current_tab.deleteLater()
            return

        self.close_all()
        self.close_tab()

    # 關閉 tab
    def close_stock_tab(self, current_index):
        current_tab = self.ui.tabWidget_stock.widget(current_index)
        tab_name = self.ui.tabWidget_stock.tabText(current_index)
        if tab_name == '出貨資料':
            return

        current_tab.close_all()
        current_tab.deleteLater()

    def add_stock_out(self, order_no, stock_out_key):
        tab_stock_out_data = module_utils.get_stock_out_data(
            self, self.database, self.system_settings, stock_out_key)

        if stock_out_key is None:
            self.ui.tabWidget_stock.addTab(tab_stock_out_data, '輸入出貨單')
        else:
            tab_name = f'出貨單{order_no}'
            if self._tab_exists(tab_name):
                return

            self.ui.tabWidget_stock.addTab(tab_stock_out_data, tab_name)

        self.ui.tabWidget_stock.setCurrentWidget(tab_stock_out_data)

    # 檢查是否開啟tab
    def _tab_exists(self, tab_text):
        if self.ui.tabWidget_stock.count() <= 0:
            return False

        for i in range(self.ui.tabWidget_stock.count()):
            if self.ui.tabWidget_stock.tabText(i) == tab_text:
                self.ui.tabWidget_stock.setCurrentIndex(i)
                return True

        return False

    def update_stock(self):
        self.tab_stock_out_list.update_stock()
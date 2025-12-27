
# -*- coding: UTF-8 -*-

import sys

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils


# 樣板 2018.01.31 update 2019.04.29
class Template(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Template, self).__init__(parent)
        self.parent = parent
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_TEMPLATE, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_template)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_template(self):
        self.close_all()
        self.close_tab()


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = Template()
    widget.show()
    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()

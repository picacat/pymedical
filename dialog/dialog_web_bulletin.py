# 輸入公告資料 2024-09-11
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils


# 主視窗
class DialogWebBulletin(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogWebBulletin, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.title = args[2]
        self.content = args[3]

        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_WEB_BULLETIN, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _set_data(self):
        self.ui.lineEdit_title.setText(self.title)
        self.ui.plainTextEdit_content.setPlainText(self.content)

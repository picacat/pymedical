
# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils


# 劑量詞庫
class DialogTutorialVideos(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTutorialVideos, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TUTORIAL_VIDEOS, self)
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.toolButton_ins_apply.clicked.connect(self._ins_apply_clicked)

    def rejected_button_clicked(self):
        self.close()

    def _ins_apply_clicked(self):
        url = 'https://www.youtube.com/watch?v=4sRFKjOLdGE'
        system_utils.play_youtube(self, self.database, self.system_settings, url)

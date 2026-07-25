
# 主訴舌診脈象詞庫 2019.07.19
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from PyQt5.QtCore import QSettings, QPoint


# 醫囑詞庫
class DialogSimpleDict(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSimpleDict, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.settings = QSettings('__settings.ini', QSettings.IniFormat)

        self.ui = None
        self._set_ui()
        self._set_signal()
        self._read_dict()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_simple_dict_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SIMPLE_DICT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.set_theme(self.ui, self.system_settings)
        width = self.settings.value("dialog_simple_dict_pos")
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_simple_dict_pos", QPoint(846, 215)))

        self.table_widget_dict = class_utils.get_table_widget(self.ui.tableWidget_dict, self.database)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_dict.clicked.connect(self.add_dict)

    def accepted_button_clicked(self):
        self.close()

    def add_dict(self):
        if not self.ui.tableWidget_dict.selectedItems():
            return

        dict_name = self.ui.tableWidget_dict.selectedItems()[0].text()
        self.parent.add_order(dict_name)

    def _read_dict(self):
        sql = '''
            SELECT * FROM clinic
            WHERE
                ClinicType = "醫囑"
            ORDER BY ClinicKey
        '''
        self.table_widget_dict.set_db_data_without_heading(sql, 'ClinicName')


# 辨證治則詞庫 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, QSize, QPoint

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils


# 辨證治則詞庫
class DialogDiagnosis(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDiagnosis, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog_type = args[2]
        self.text_edit = args[3]
        self.text_edit_cure = args[4]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.read_dictionary()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_diagnosis_size", self.size())
        self.settings.setValue("dialog_diagnosis_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DIAGNOSIS, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.set_theme(self.ui, self.system_settings)

        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        # self.ui.resize(self.settings.value("dialog_diagnosis_size", QSize(1090, 768)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_diagnosis_pos")
        try:
            if width is not None and width.x() < screen_width:
                self.ui.move(self.settings.value("dialog_diagnosis_pos", QPoint(205, 220)))
        except AttributeError:
            pass

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    def read_dictionary(self):
        if self.dialog_type == '辨證':
            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "辨證類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                self.ui.tabWidget_diagnosis.addTab(
                    dialog_utils.get_dialog_distinguish(
                        self, self.database, self.system_settings, groups_name, self.text_edit, self.text_edit_cure,
                    ),
                    groups_name
                )
        elif self.dialog_type == '治則':
            sql = 'SELECT * FROM dict_groups WHERE DictGroupsType = "治則類別" ORDER BY DictGroupsKey'
            rows = self.database.select_record(sql)
            for row in rows:
                groups_name = row['DictGroupsName']
                self.ui.tabWidget_diagnosis.addTab(
                    dialog_utils.get_dialog_cure(
                        self, self.database, self.system_settings, groups_name, self.text_edit
                    ),
                    groups_name
                )

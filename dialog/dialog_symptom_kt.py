
# 主訴舌診脈象詞庫 2019.07.19
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from PyQt5.QtCore import QSettings, QPoint


# 主訴舌診脈象詞庫
class DialogSymptomKT(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSymptomKT, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.text_edit = args[2]
        self.text_edit_tongue = args[3]
        self.settings = QSettings('__settings.ini', QSettings.IniFormat)

        self.ui = None
        self._set_ui()
        self._set_signal()
        self._read_symptom_kt()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_symptom_kt_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SYMPTOM_KT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.set_theme(self.ui, self.system_settings)
        width = self.settings.value("dialog_symptom_kt_pos")
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_symptom_kt_pos", QPoint(846, 215)))

        self.table_widget_symptom = class_utils.get_table_widget(self.ui.tableWidget_symptom, self.database)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_changed)
        self.ui.tableWidget_symptom.clicked.connect(self.add_symptom)

    def accepted_button_clicked(self):
        self.close()

    def add_symptom(self):
        if not self.ui.tableWidget_symptom.selectedItems():
            return

        groups = self.ui.tableWidget_groups.selectedItems()[0].text()
        text_edit = self.text_edit
        if '舌' in groups:
            text_edit = self.text_edit_tongue

        selected_symptom = self.ui.tableWidget_symptom.selectedItems()[0].text()
        self.parent.insert_text(text_edit, selected_symptom, '')

        self.text_edit.document().setModified(True)

    def _read_symptom_kt(self):
        self._set_symptom_class()

    def _set_symptom_class(self):
        sql = '''
            SELECT ALM_NAME FROM symptom_kt
            WHERE
                ALM_ID LIKE "G#%"
            ORDER BY ALM_NAME
        '''
        rows = self.database.select_record(sql)

        record_count = len(rows)
        row_count = self.ui.tableWidget_groups.rowCount()

        columns = int(record_count / row_count)
        if record_count % row_count > 0:
            columns += 1

        for col_no in range(columns):
            for row_no in range(row_count):
                index = col_no * row_count + row_no
                if index >= record_count:
                    break

                self.ui.tableWidget_groups.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(rows[index]['ALM_NAME'])
                )

        self.ui.tableWidget_groups.setCurrentCell(0, 0)

    def groups_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        groups = self.ui.tableWidget_groups.selectedItems()[0].text()
        self._read_groups_name(groups)

        self.ui.tableWidget_groups.setFocus(True)

    def _read_groups_name(self, groups):
        sql = f'''
            SELECT ALM_NAME FROM symptom_kt
            WHERE
                ALM_KIND1 = "{groups}"
            ORDER BY ALM_ID
        '''
        self.table_widget_symptom.set_db_data_without_heading(sql, 'ALM_NAME')


# 動態輸入主訴 2022.08.31 重編
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, QSize, QPoint
from PyQt5.QtWidgets import QInputDialog

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import db_utils
from libs import dialog_utils


# 動態輸入主訴
class DialogDiagnosticPicker(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDiagnosticPicker, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.text_edit = args[2]
        self.clinic_type = args[3]
        self.input_code = args[4]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None
        self.clinic_name = None

        self._set_ui()
        self._set_signal()
        self._read_data()

        self.ui.tableWidget_diagnostic.setFocus()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_diagnostic_picker_size", self.size())
        self.settings.setValue("dialog_diagnostic_picker_pos", self.pos())

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DIAGNOSTIC_PICKER, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        if self.system_settings.field('詞庫視窗顯示方式') == '彈出式視窗':
            self.ui.setWindowFlags(QtCore.Qt.Popup)

        self.ui.resize(self.settings.value("dialog_diagnostic_picker_size", QSize(861, 479)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_diagnostic_picker_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_diagnostic_picker_pos", QPoint(846, 215)))

        if self.input_code == '':
            self.ui.setWindowTitle(f'常用100個{self.clinic_type}')

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_diagnostic = class_utils.get_table_widget(
            self.ui.tableWidget_diagnostic, self.database)
        self._set_table_width()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    def _show_menu(self):
        m = QtWidgets.QMenu()
        remove_action = QtWidgets.QAction('移除主訴', self)
        remove_action.triggered.connect(self._remove_symptom)
        edit_action = QtWidgets.QAction('編輯主訴', self)
        edit_action.triggered.connect(self._edit_symptom)
        m.addAction(remove_action)
        m.addAction(edit_action)
        m.exec_(QtGui.QCursor.pos())

    def _remove_symptom(self):
        clinic_key = self._get_clinic_key()
        if clinic_key is None:
            return

        sql = f'DELETE FROM clinic WHERE ClinicKey = {clinic_key}'
        self.database.exec_sql(sql)
        self._read_data()

    def _edit_symptom(self):
        clinic_key = self._get_clinic_key()
        if clinic_key is None:
            return

        clinic_name = self._get_clinic_name()
        input_dialog = dialog_utils.get_dialog(
            '更改主訴', '請輸入主訴內容', clinic_name, QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        new_clinic_name = input_dialog.textValue()
        sql = f'UPDATE clinic SET ClinicName = "{new_clinic_name}" WHERE ClinicKey = {clinic_key}'
        self.database.exec_sql(sql)
        self._read_data()

    def _set_table_width(self):
        width = [200, 200, 200, 200, 200]
        self.table_widget_diagnostic.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_diagnostic.clicked.connect(self._table_item_clicked)
        self.ui.tableWidget_diagnostic.doubleClicked.connect(self.accepted_button_clicked)
        self.ui.tableWidget_diagnostic.keyPressEvent = self._table_widget_diagnostic_key_press

    def _table_widget_diagnostic_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            self._insert_text(insert_comma=False)
            self.close()
        elif key == QtCore.Qt.Key_Plus:
            self._insert_text(insert_comma=True)
        elif key == QtCore.Qt.Key_Minus:
            self._insert_text(insert_comma=False)

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_diagnostic, event)

    def _table_item_clicked(self):
        self._insert_text()

    def _insert_text(self, insert_comma=True):
        clinic_name = self._get_clinic_name()
        self.parent.insert_text(self.text_edit, clinic_name, self.input_code, insert_comma=insert_comma)
        self.input_code = ''
        self._update_diagnosis_hit_rate()

    def accepted_button_clicked(self):
        self.clinic_name = self._get_clinic_name()
        self._update_diagnosis_hit_rate()

        self.close()

    def _update_diagnosis_hit_rate(self):
        clinic_key = self._get_clinic_key()
        if clinic_key is not None:
            db_utils.increment_hit_rate(self.database, 'clinic', 'ClinicKey', clinic_key)

    def _get_clinic_name(self):
        item = self.ui.tableWidget_diagnostic.item(
            self.ui.tableWidget_diagnostic.currentRow(),
            self.ui.tableWidget_diagnostic.currentColumn(),
        )

        if item is not None:
            clinic_name = item.text()
        else:
            clinic_name = ''

        return clinic_name

    def _read_data(self):
        # database.table_widget_diagnostic.set_db_data(database.sql, database._set_wait_data)
        order_type = '''
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        if self.system_settings.field('診察詞庫排序') == '點擊率':
            order_type = 'ORDER BY HitRate DESC'
        elif self.system_settings.field('診察詞庫排序') == '最後點擊時戳':
            order_type = 'ORDER BY TimeSTamp DESC'

        if self.input_code == '':
            sql = f'''
                SELECT * FROM clinic
                WHERE
                    ClinicType = "{self.clinic_type}"
                {order_type} LIMIT 100
            '''
        else:
            sql = f'''
                SELECT * FROM clinic
                WHERE
                    ClinicType = "{self.clinic_type}" AND
                    InputCode LIKE "{self.input_code}%"
                GROUP BY ClinicName
                {order_type}
            '''

        self.rows = self.database.select_record(sql)
        self.table_widget_diagnostic.set_db_data_without_heading(sql, 'ClinicName')

    def _set_table_data(self, row_no, row):
        diagnostic_row = [
            string_utils.xstr(row['ClinicKey']),
            string_utils.xstr(row['ClinicName']),
        ]

        for column in range(len(diagnostic_row)):
            self.ui.tableWidget_diagnostic.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(diagnostic_row[column])
            )

    def _get_clinic_key(self):
        row_no = self.ui.tableWidget_diagnostic.currentRow()
        col_no = self.ui.tableWidget_diagnostic.currentColumn()
        column_count = self.ui.tableWidget_diagnostic.columnCount()

        index = (row_no * column_count) + col_no
        if index >= len(self.rows):
            return None

        return self.rows[index]['ClinicKey']


# 預約權限設定 2023.01.16
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QPushButton
from libs import class_utils

import datetime

from libs import ui_utils
from libs import system_utils
from libs import string_utils


# 預約權限設定 2023.01.16
class DialogPermissionListSetting(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPermissionListSetting, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_permission_list()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PERMISSION_LIST_SETTING, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now().date())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now().date() + datetime.timedelta(days=30))

        self.table_widget_permisssion_list = class_utils.get_table_widget(
            self.ui.tableWidget_permission_list, self.database
        )
        self.table_widget_permisssion_list.set_column_hidden([0])
        self._set_table_width()
        self._set_combo_box()

    def _set_table_width(self):
        width = [100, 120, 100, 120, 130, 130, 260]
        self.table_widget_permisssion_list.set_table_heading_width(width)

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_permission_type, ['黑名單', '白名單'])

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.pushButton_insert_data.clicked.connect(self._insert_data)

    def _read_permission_list(self):
        sql = f'''
            SELECT permission_list.*, patient.Name FROM permission_list
                LEFT JOIN patient ON permission_list.PatientKey = patient.PatientKey
            ORDER BY PermissionListKey
        '''
        self.table_widget_permisssion_list.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        permission_list_row = [
            string_utils.xstr(row['PermissionListKey']),
            string_utils.xstr(row['PermissionType']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['StartDate']),
            string_utils.xstr(row['EndDate']),
            string_utils.xstr(row['Remark']),
        ]

        for col_no in range(len(permission_list_row)):
            self.ui.tableWidget_permission_list.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(permission_list_row[col_no])
            )
            if col_no in [2]:
                self.ui.tableWidget_permission_list.item(
                    row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        button = QPushButton(self.ui.tableWidget_permission_list)
        button.setIcon(QtGui.QIcon('./icons/cancel.svg'))
        button.setFlat(True)
        button.clicked.connect(self._remove_permission_list)
        self.ui.tableWidget_permission_list.setCellWidget(row_no, 7, button)

    def _remove_permission_list(self):
        permission_list_key = self.table_widget_permisssion_list.field_value(0)
        if permission_list_key is None:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除權限資料')
        msg_box.setText("<font size='4' color='red'><b>確定刪除此預約權限設定?</b></font>")
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        self.database.exec_sql(f'''
            DELETE FROM permission_list
            WHERE
                PermissionListKey = {permission_list_key}
        ''')
        self.ui.tableWidget_permission_list.removeRow(self.ui.tableWidget_permission_list.currentRow())

    def accepted_button_clicked(self):
        self.close()

    def _insert_data(self):
        field = [
            'PermissionType', 'PatientKey', 'StartDate', 'EndDate', 'Remark',
        ]
        data = [
            self.ui.comboBox_permission_type.currentText(),
            self.ui.lineEdit_patient_key.text(),
            self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd'),
            self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd'),
            self.ui.lineEdit_remark.text(),
        ]

        self.database.insert_record('permission_list', field, data)
        self._read_permission_list()

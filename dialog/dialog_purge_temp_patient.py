
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
from libs import class_utils

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import dialog_utils


# 清除無效的初診病患資料 2025.01.23
class DialogPurgeTempPatient(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPurgeTempPatient, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_temp_patient()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PURGE_TEMP_PATIENT, self)
        self.ui.setFixedSize(self.ui.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('開始清除')

        self.table_widget_temp_patient = class_utils.get_table_widget(
            self.ui.tableWidget_temp_patient, self.database)
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 120, 150, 100, 120, 150,]
        self.table_widget_temp_patient.set_table_heading_width(width)

    def _read_temp_patient(self):
        sql = '''
            SELECT temp_patient.TempPatientKey, temp_patient.Name AS TempPatientName,
                temp_patient.ID AS TempPatientID,
                patient.PatientKey, patient.Name, patient.ID
            FROM temp_patient
                INNER JOIN patient ON patient.ID = temp_patient.ID
            ORDER BY TempPatientKey
        '''

        self.table_widget_temp_patient.set_db_data(sql, self._set_temp_patient_data)

    def _set_temp_patient_data(self, row_no, row):
        hosts_row = [
            string_utils.xstr(row['TempPatientKey']),
            string_utils.xstr(row['TempPatientName']),
            string_utils.xstr(row['TempPatientID']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['ID']),
        ]

        for col_no in range(len(hosts_row)):
            self.ui.tableWidget_temp_patient.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(hosts_row[col_no])
            )

    def _add_hosts(self):
        dialog = dialog_utils.get_dialog_input_host(self, self.database, self.system_settings, None)
        result = dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self._read_hosts()
        self.ui.tableWidget_hosts.setCurrentCell(
            self.ui.tableWidget_hosts.rowCount(), 1
        )

    def _edit_hosts(self):
        hosts_key = self.table_widget_temp_patient.field_value(0)
        current_row = self.ui.tableWidget_hosts.currentRow()

        dialog = dialog_utils.get_dialog_input_host(
            self, self.database, self.system_settings, hosts_key,
        )
        result = dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self._read_hosts()
        self.ui.tableWidget_hosts.setCurrentCell(current_row, 1)

    def _remove_hosts(self):
        msg_box = dialog_utils.get_message_box(
            '刪除連線資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此連線設定資料 ?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_temp_patient.field_value(0)
        self.database.delete_record('hosts', 'HostsKey', key)
        self.ui.tableWidget_hosts.removeRow(self.ui.tableWidget_hosts.currentRow())

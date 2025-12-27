
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox
import re

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import class_utils
from libs import validator_utils
from libs import date_utils
from libs import patient_utils
from libs import dialog_utils


# 主視窗
class DialogReservationQuery(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReservationQuery, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RESERVATION_QUERY, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')
        self.table_widget_reservation = class_utils.get_table_widget(self.ui.tableWidget_reservation, self.database)
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.lineEdit_keyword.textChanged.connect(self._query_reservation)
        self.ui.radioButton_unarrival.clicked.connect(self._query_reservation)
        self.ui.radioButton_arrival.clicked.connect(self._query_reservation)
        self.ui.radioButton_all.clicked.connect(self._query_reservation)
        self.ui.pushButton_query.clicked.connect(self._query_patient)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [80, 90, 170, 50, 50, 90, 120, 120]
        self.table_widget_reservation.set_table_heading_width(width)

    def _query_reservation(self):
        keyword = self.ui.lineEdit_keyword.text()
        if keyword == '':
            self.ui.tableWidget_reservation.setRowCount(0)
            return

        if self.ui.radioButton_unarrival.isChecked():
            condition = ' AND Arrival = "False" '
        elif self.ui.radioButton_arrival.isChecked():
            condition = ' AND Arrival = "True" '
        else:
            condition = ''

        if keyword.isdigit():
            patient_condition = f'PatientKey = {keyword}'
        else:
            patient_condition = f'Name LIKE "%{keyword}%"'

        sql = f'''
            SELECT * FROM reserve
            WHERE
                {patient_condition}
                {condition}
            ORDER BY PatientKey, ReserveDate DESC
        '''
        self.table_widget_reservation.set_db_data(sql, self._set_reservation_data)

        self.ui.lineEdit_keyword.setFocus(True)
        self.ui.lineEdit_keyword.setCursorPosition(len(keyword))

    def _set_reservation_data(self, row_no, row):
        if string_utils.xstr(row['Arrival']) == 'True':
            status = '已報到'
        else:
            status = '未報到'

        if row['ReserveDate'] is None:
            reserve_date = None
        else:
            reserve_date = string_utils.xstr(row['ReserveDate'].strftime('%Y-%m-%d %H:%M'))

        reservation_data = [
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            reserve_date,
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['ReserveNo']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['Source']),
            status,
        ]

        for col_no in range(len(reservation_data)):
            self.ui.tableWidget_reservation.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(reservation_data[col_no])
            )

            if col_no in [0, 4]:
                self.ui.tableWidget_reservation.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3]:
                self.ui.tableWidget_reservation.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _query_patient(self):
        keyword = string_utils.xstr(self.ui.lineEdit_keyword.text())
        if keyword == '':
            return

        pattern = re.compile(validator_utils.DATE_REGEXP)
        if pattern.match(keyword):
            keyword = date_utils.date_to_west_date(keyword)

        self._get_patient(keyword)

    def _get_patient(self, keyword=None):
        row = patient_utils.search_patient(self.ui, self.database, self.system_settings, keyword)
        if row is None:  # 找不到資料
            dialog = dialog_utils.get_dialog_select_patient(
                self, self.database, self.system_settings,
                'patient', 'PatientKey', keyword
            )
            if dialog.table_widget_patient_list.row_count() <= 0:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '查無資料',
                    '<font size="5" color="red"><b>找不到有關的病患資料, 請檢查關鍵字是否有誤.</b></font>',
                    '請確定輸入資料的正確性, 生日請輸入YYYY-MM-DD.'
                )
                self.ui.lineEdit_keyword.setFocus()
                return

            if dialog.exec_():
                patient_key = dialog.get_primary_key()
                self._get_patient(patient_key)

            del dialog
        elif row == -1:  # 取消查詢
            self.ui.lineEdit_keyword.setFocus()
        else:  # 已選取病患
            patient_key = string_utils.xstr(row[0]['PatientKey'])
            self.ui.lineEdit_keyword.setText(patient_key)

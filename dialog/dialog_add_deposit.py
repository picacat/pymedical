
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from libs import class_utils

import datetime

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils


# 新增欠卡資料 2019.09.06
class DialogAddDeposit(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAddDeposit, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_deposit()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ADD_DEPOSIT, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.dateEdit_deposit_date.setDate(datetime.datetime.now().date())

        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 200, 50, 90, 100, 120, 60, 80, 100]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_deposit_date.dateChanged.connect(self._read_deposit)

    def _read_deposit(self):
        start_date = self.ui.dateEdit_deposit_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_deposit_date.date().toString('yyyy-MM-dd 23:59:59')

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                InsType = "健保" AND
                Card IN ("欠卡", "HVIT")
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)
        if self.ui.tableWidget_medical_record.rowCount() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled)

    def _set_table_data(self, row_no, row):
        medical_record_row = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['DepositFee']),
            string_utils.xstr(row['Register']),
        ]

        for col_no in range(len(medical_record_row)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record_row[col_no])
            )
            if col_no in [2]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3, 7]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def accepted_button_clicked(self):
        self._insert_deposit()
        self.close()

    # 寫入主訴
    def _insert_deposit(self):
        current_row = self.ui.tableWidget_medical_record.currentRow()
        if current_row is None:
            return

        case_key = self.ui.tableWidget_medical_record.item(current_row, 0).text()
        card = self.ui.tableWidget_medical_record.item(current_row, 6).text()
        if card in nhi_utils.INFECTIOUS_CARD:
            self.database.exec_sql(f'UPDATE cases SET Card = "欠卡" WHERE CaseKey = {case_key}')

        fields = [
            'CaseKey', 'PatientKey', 'Name', 'DepositDate', 'Period',
            'Register', 'Fee'
        ]

        data = [
            case_key,
            self.ui.tableWidget_medical_record.item(current_row, 3).text(),
            self.ui.tableWidget_medical_record.item(current_row, 4).text(),
            self.ui.tableWidget_medical_record.item(current_row, 1).text(),
            self.ui.tableWidget_medical_record.item(current_row, 2).text(),
            self.ui.tableWidget_medical_record.item(current_row, 8).text(),
            self.ui.tableWidget_medical_record.item(current_row, 7).text(),
        ]

        self.database.insert_record('deposit', fields, data)



# -*- coding: UTF-8 -*-

import datetime

from libs import (class_utils, number_utils, string_utils, system_utils,
                  ui_utils)
from PyQt5 import QtCore, QtWidgets


# 新增欠款資料 2022.05.10
class DialogAddDebt(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAddDebt, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_debt()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ADD_DEBT, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.dateEdit_debt_date.setDate(datetime.datetime.now().date())
        ui_utils.set_combo_box(self.ui.comboBox_debt_type, ['掛號欠款', '批價欠款'])

        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 200, 50, 90, 100, 60, 150, 100, 80, 80, 80, 80]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_debt_date.dateChanged.connect(self._read_debt)
        self.ui.spinBox_debt.valueChanged.connect(self._set_button_enabled)

    def _read_debt(self):
        start_date = self.ui.dateEdit_debt_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_debt_date.date().toString('yyyy-MM-dd 23:59:59')

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}"
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

        self._set_button_enabled()

    def _set_button_enabled(self):
        if self.ui.tableWidget_medical_record.rowCount() > 0 and self.ui.spinBox_debt.value() > 0:
            enabled = True
        else:
            enabled = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled)

    def _set_table_data(self, row_no, row):
        medical_record_row = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['RegistFee']),
            string_utils.xstr(row['DiagShareFee']),
            string_utils.xstr(row['DrugShareFee']),
            string_utils.xstr(row['TotalFee']),
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
            elif col_no in [3, 8, 9, 10, 11]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def accepted_button_clicked(self):
        self._insert_debt()
        self.close()

    # 寫入主訴
    def _insert_debt(self):
        current_row = self.ui.tableWidget_medical_record.currentRow()
        if current_row is None:
            return

        fields = [
            'CaseKey', 'PatientKey', 'Name', 'CaseDate', 'Period', 'Doctor', 'DebtType', 'Fee'
        ]

        data = [
            self.ui.tableWidget_medical_record.item(current_row, 0).text(),
            self.ui.tableWidget_medical_record.item(current_row, 3).text(),
            self.ui.tableWidget_medical_record.item(current_row, 4).text(),
            self.ui.tableWidget_medical_record.item(current_row, 1).text(),
            self.ui.tableWidget_medical_record.item(current_row, 2).text(),
            self.ui.tableWidget_medical_record.item(current_row, 7).text(),
            self.ui.comboBox_debt_type.currentText(),
            self.ui.spinBox_debt.value(),
        ]

        self.database.insert_record('debt', fields, data)

